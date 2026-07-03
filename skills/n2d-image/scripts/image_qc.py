#!/usr/bin/env python3
"""出图落档机检 image_qc —— 把 n2d-review 家族的一致性机检**前移到出图落档**。

设计同 n2d-video 的 video_qc.py：复用 n2d-review/scripts 的已校准纯函数与阈值
（单一真值源，本文件不重复定义阈值），让一致性漂移在**刚出完一批图、还没继续**的
最便宜的点被机检初筛，而不是等整集出完进 n2d-review 审片才发现 → 省大量返工。

四项像素机检（全部读 `出图/第N集/图片/*.png`，Pillow-or-fallback，缺料必须在报告中明示，不臆造通过）：
- 崩脸 G1   ← face_consistency.analyze（insightface 优先，无则 Pillow 查分辨率/清晰度）
- 发型 H1   ← hair_consistency.analyze（Pillow 头部发色+发型轮廓指纹）
- 服装 N1   ← outfit_consistency.analyze（Pillow 调色板直方图）
- 场景 O2   ← scene_consistency.analyze（Pillow dHash 结构 + 色调指纹离群）
- 接缝接力  ← temporal_consistency.seam_analyze（镜头N_end.png vs 下镜首帧 dHash）
- 锚点门 N3 ← face_consistency.audit_anchors（定妆主参考恰好 1 张清晰正脸）

一项执行层 lint（读 `出图/第N集/prompt/01_分镜出图.md` 逐镜块，治人工誊抄漏）：
- 角色镜是否有参考图块（禁纯文生图）/ 视线方向字段 / 锚点句 / 身份锁定句
- 打斗/动作/追逐/法术/强互动镜不得直视主镜头：镜头是旁观者，不是对手 POV；必须把视线锁到对手/武器来路/命中点
- **CHAR_xx/形态 是否在 identity_registry 合法存在**（gate.py 不查这条——它只查"写了 CHAR_xx"，
  不验 ID 真的在 registry 里，写错 CHAR_99 出图阶段无人拦）
- 尾帧/下一镜入点若切到非主镜身份，必须有 `尾帧专用重抽提示`，并写目标 `CHAR_xx/形态`
  或 `定妆_<角色>_<形态>` 脸部参考，防止局部修复把接力角色美化成通用脸
- 角色镜落档后必须逐张有 full 精度脸部参考比对证据：缺 insightface、缺比对行、比对 warn/noface
  都不允许进入 video。

落档判定：block=必须重抽/修复，warn=人判二次，ok=放行。退出码恒 0（建议性闸门，
由出图落档工作流/人决定是否放行误报，同 video_qc 的 --allow-qc-block 哲学）。

`--strict` 给 n2d-update「严审刷新」使用：block/warn/降级都进入候选重出清单，
除非已有明确人工判定可沿用；不把旧图默认为受保护资产。

用法：
  python3 image_qc.py <作品根> 第N集 [--json]
  python3 image_qc.py <作品根> 第N集 --no-pixel   # 只跑 prompt lint（无 Pillow 时）
  python3 image_qc.py <作品根> 第N集 --face-confirm-ok all
  python3 image_qc.py <作品根> 第N集 --prop-shape-report / --prop-shape-vlm-confirm / --prop-shape-confirm-ok all

完整视觉质检推荐在可装重依赖的 conda env 跑：Pillow + cv2 + insightface + onnxruntime + buffalo_l model。
报告会写 `qc_environment.precision_level=full|degraded|none`，
缺依赖时应停在 image/image_qc setup 补装并重跑，不应直接跳 video。

测试（从本目录跑）：
  cd skills/n2d-image/scripts && python3 -m pytest test_image_qc.py
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

# 同家族复用：一致性机检的阈值与数学只在 n2d-review/scripts 维护一份。
REVIEW_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "n2d-review" / "scripts"

# 一致性 lint 共享词表单一真值源（n2d_const）：强情绪/表情库/多主体放行集只此一份，
# 本文件禁止再用字面量重定义同名集合（test_marker_single_source.py 守护）。纯 stdlib 常量，import 安全。
_LIB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)
from n2d_const import (  # noqa: E402
    STRONG_EMOTION_MARKERS,
    EXPRESSION_LIB_MARKERS,
    MULTI_SUBJECT_ACCEPTING_MARKERS,
)
# 多主体「已登记执行策略」放行集 —— 与 review gate 的 _has_native_multi_subject_strategy 同源。
MULTI_SUBJECT_STRATEGY_MARKERS = MULTI_SUBJECT_ACCEPTING_MARKERS

# verdict 严重度（与 n2d-review/face_consistency._sev 同序；noface=图里没脸，介于 ok 与 warn）
SEVERITY = {"ok": 0, "info": 0, "noface": 1, "warn": 2, "block": 3}


def _load_review_module(name: str):
    """惰性加载 n2d-review 的一致性模块；不可用（缺依赖/旧解释器语法/缺文件）时返回 None。
    与 video_qc._load_temporal_module 同策略：宁可降级交人判，不让整个落档机检崩。"""
    if str(REVIEW_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(REVIEW_SCRIPTS_DIR))
    try:
        return __import__(name)
    except Exception:
        return None


def _backend_identity_profile(root: Path) -> Optional[Dict[str, Any]]:
    """读 _设置.md『生图AI』→ IMAGE_IDENTITY_PROFILES（含 persistent_subject）。
    读不到/lib 不可用 → None（保持现状，不改变默认 lint 行为）。best-effort I/O。"""
    lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
    if lib not in sys.path:
        sys.path.insert(0, lib)
    try:
        from n2d_contract import classify_image_backend, image_identity_profile  # type: ignore
    except Exception:
        return None
    raw = ""
    try:
        m = re.search(r"生图AI[：:]\s*([^\n（(]+)", (root / "_设置.md").read_text(encoding="utf-8"))
        if m:
            raw = m.group(1).strip()
    except Exception:
        return None
    try:
        canon, kind = classify_image_backend(raw)
        if kind != "approved" or not canon:
            return None
        return image_identity_profile(canon)
    except Exception:
        return None


def _load_sibling(name: str):
    """惰性加载本 skill scripts 目录下的同级模块（如 asset_lifecycle）；不可用返回 None。"""
    d = str(Path(__file__).resolve().parent)
    if d not in sys.path:
        sys.path.insert(0, d)
    try:
        return __import__(name)
    except Exception:
        return None


def worst_verdict(verdicts: Iterable[str]) -> str:
    """一组 verdict 取最重者；空集 → ok。纯函数·可测。"""
    worst = "ok"
    for v in verdicts:
        if SEVERITY.get(v, 0) > SEVERITY.get(worst, 0):
            worst = v
    return worst


def count_verdicts(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """从 review analyze 返回的 shots[]/seams[] 统一数 verdict（不同模块语义不同，
    有的只塞离群项、有的全塞，但都带 verdict 字段——按出现次数数即可）。纯函数·可测。"""
    out = {"block": 0, "warn": 0, "noface": 0, "ok": 0}
    for r in rows or []:
        v = r.get("verdict")
        if v in out:
            out[v] += 1
    return out


# ── registry 合法 ID 集（prompt lint 用） ───────────────────────────────────────

def load_registry_ids(root: Path) -> Optional[Set[str]]:
    """identity_registry.json → 合法身份键集合：{'CHAR_01', 'CHAR_SHEN', 'CHAR_01/常态', ...}。
    registry 缺失/损坏 → None（lint 跳过 ID 合法性，记 note，不误报）。"""
    path = root / "出图" / "共享" / "identity_registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    ids: Set[str] = set()
    for ch in (data.get("characters") or []):
        cid = str(ch.get("id") or "").strip()
        if not cid:
            continue
        ids.add(cid)
        for form in (ch.get("forms") or []):
            fm = str(form.get("form") or "").strip()
            if fm:
                ids.add(f"{cid}/{fm}")
    return ids


def load_asset_index(root: Path) -> Optional[Dict[str, Any]]:
    """asset_registry.json → {ids, name_to_id, prefix_of}，供逐镜资产 id lint（A·把 CHAR_xx 那套对称到
    LOC/PROP/WEAPON/OUTFIT/VFX）。缺/损坏 → None（lint 跳过资产合法性，记 note，不误报）。

    name_to_id 把每个资产的 `name` 和 reference_group 文件名 stem（剥 `定妆_`/`_侧`等）映到其 id，
    用来抓「用了 `定妆_<资产>` 却没绑 `PROP_xx/LOC_xx/WEAPON_xx`」——执行端缺 id 就取不到 constraints/drift_forbidden。
    asset_registry 只含非角色资产（场景/道具/武器/服装/特效），角色在 identity_registry，二者不串。
    """
    path = root / "出图" / "共享" / "asset_registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    ids: Set[str] = set()
    name_to_id: Dict[str, str] = {}
    prefix_of: Dict[str, str] = {}
    entries: Dict[str, Dict[str, Any]] = {}
    for a in (data.get("assets") or []):
        aid = str(a.get("id") or "").strip()
        if not aid:
            continue
        ids.add(aid)
        entries[aid] = {
            "name": str(a.get("name") or "").strip(),
            "type": str(a.get("type") or "").strip(),
            "reference_group": a.get("reference_group") if isinstance(a.get("reference_group"), Mapping) else {},
            "scale": str((a.get("constraints") or {}).get("scale") if isinstance(a.get("constraints"), Mapping) else a.get("scale") or "").strip(),
            "must_not_have": _asset_must_not_have_terms(a),
        }
        m = re.match(r"([A-Za-z]+_)", aid)
        if m:
            prefix_of[aid] = m.group(1)
        name = str(a.get("name") or "").strip()
        if len(name) >= 2:
            name_to_id.setdefault(name, aid)
        for ref in _flatten_reference_paths(a.get("reference_group") or {}):
            stem = Path(ref).stem
            if stem.startswith("定妆_"):
                stem = stem[len("定妆_"):]
            stem = re.sub(r"_(侧|半身|全身|背|三视图|四视图|设定表)$", "", stem)
            if len(stem) >= 2:
                name_to_id.setdefault(stem, aid)
    return {"ids": ids, "name_to_id": name_to_id, "prefix_of": prefix_of, "entries": entries}


def _flatten_terms(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [p.strip() for p in re.split(r"[,，、/；;\n]+", value) if p.strip()]
    if isinstance(value, Mapping):
        terms: List[str] = []
        for v in value.values():
            terms.extend(_flatten_terms(v))
        return terms
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        terms = []
        for v in value:
            terms.extend(_flatten_terms(v))
        return terms
    text = str(value).strip()
    return [text] if text else []


def _asset_must_not_have_terms(asset: Mapping[str, Any]) -> List[str]:
    constraints = asset.get("constraints") if isinstance(asset.get("constraints"), Mapping) else {}
    terms: List[str] = []
    for key in ("must_not_have", "forbidden_parts", "negative_structure", "negative"):
        terms.extend(_flatten_terms(asset.get(key)))
        if isinstance(constraints, Mapping):
            terms.extend(_flatten_terms(constraints.get(key)))
    out: List[str] = []
    seen: Set[str] = set()
    for term in terms:
        t = str(term).strip(" `。，；;、")
        if len(t) < 1 or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


# 资产 id 引用（场景/道具/武器/服装/特效）+ 定妆资产名（用于抓"用了定妆却没绑 id"）。
ASSET_ID_RE = re.compile(r"`?((?:LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_\u4e00-\u9fff]+)`?")
DEFINING_ASSET_RE = re.compile(r"定妆_([^\s`，。、）)/]+)")
_ASSET_NAME_SUFFIX_RE = re.compile(r"_(侧|半身|全身|背|三视图|四视图|设定表|脸部特写|表情)$")


def _lint_asset_binding(label: str, body: str, asset_index: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """资产 id lint（A，所有镜都跑，不限角色镜）：
    - 写了 `LOC/PROP/WEAPON/OUTFIT/VFX_xx` 但 registry 没有 → block `unknown_asset_id`（对称 unknown_char_id）；
    - 用了 `定妆_<已登记资产>` 却没绑对应 id → warn `asset_ref_without_id`（执行端取不到 constraints/drift_forbidden）。
    纯函数·可测。asset_index=None（registry 缺）→ 跳过。"""
    findings: List[Dict[str, str]] = []
    if not asset_index:
        return findings
    text = str(body or "")
    ids: Set[str] = asset_index.get("ids") or set()
    name_to_id: Dict[str, str] = asset_index.get("name_to_id") or {}
    prefix_of: Dict[str, str] = asset_index.get("prefix_of") or {}
    entries: Dict[str, Dict[str, Any]] = asset_index.get("entries") or {}
    body_ids = set(ASSET_ID_RE.findall(text))
    for rid in sorted(body_ids):
        if rid not in ids:
            findings.append({"level": "block", "code": "unknown_asset_id",
                             "msg": f"{label}：资产引用 `{rid}` 在 asset_registry 不存在（场景/道具/武器/服装/特效 id 写错或未登记）"})
            continue
        must_not = [t for t in (entries.get(rid) or {}).get("must_not_have", []) if t]
        missing_terms = [t for t in must_not if t not in text]
        if missing_terms:
            findings.append({
                "level": "block",
                "code": "asset_must_not_have_not_propagated",
                "msg": (
                    f"{label}：资产 `{rid}` 在 asset_registry 登记了 must_not_have={must_not}，"
                    f"但本镜 prompt 未继承禁项 {missing_terms}；关键道具禁形必须写进负向/结构约束。"
                ),
            })
    flagged: Set[str] = set()
    for raw in DEFINING_ASSET_RE.findall(text):
        stem = raw[:-4] if raw.endswith(".png") else raw
        name = _ASSET_NAME_SUFFIX_RE.sub("", stem)
        aid = name_to_id.get(name) or name_to_id.get(stem) or name_to_id.get(raw)
        if aid and aid not in body_ids and aid not in flagged:
            flagged.add(aid)
            kind = {"LOC_": "场景", "PROP_": "道具", "WEAPON_": "武器", "OUTFIT_": "服装", "VFX_": "特效"}.get(prefix_of.get(aid, ""), "资产")
            findings.append({"level": "warn", "code": "asset_ref_without_id",
                             "msg": f"{label}：用了 `定妆_{raw}`({kind}) 但未绑 `{aid}`；写上资产 id 执行端才会自动取 "
                                    "reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移）"})
    return findings


def audit_carried_identity_anchors(root: Path) -> Dict[str, Any]:
    """承载角色脸的资产（VFX/海报/关系图等画面里出具名角色脸）是否有 ready 脸锚——落档机检版。

    `carries_identity`（治定妆脸漂的真因）此前只在 codex/dreamina runner 的出图前 spend 闸门
    enforced；非 runner 路径（手工出图/其它后端/旧图）绕过即漏检。本函数把同一条铁律前移到
    **后端无关的落档机检**：对 `asset_registry.json` 每个承载角色身份的资产，按 `identity_registry`
    静态核验承载角色至少有 1 张 ready 脸锚可注入——0 张 ready 锚 = 该资产每镜必无锚渲染新脸
    （万妖血脉 VFX vs 沈念基础包正是此坑）。

    复用 runner 的 `_asset_carried_identities`（含显式字段 + 类型/上下文推断单一真值源）和
    `_collect_ready_image_paths`（ready 状态语义同源），绝不另起一套 fork。runner 不可加载
    （缺依赖/旧解释器）→ available=False 优雅跳过，不臆造 block。逃生口同 runner:
    `N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1`（显式豁免，留痕自负）。
    """
    res: Dict[str, Any] = {"available": True, "findings": [], "notes": []}
    base = _load_sibling("codex_image_runner")
    if base is None or not hasattr(base, "_asset_carried_identities") \
            or not hasattr(base, "_collect_ready_image_paths"):
        res["available"] = False
        res["notes"].append("codex_image_runner 不可用——承载角色脸锚机检跳过，交人判/runner 闸门。")
        return res
    try:
        assets = json.loads((root / "出图" / "共享" / "asset_registry.json").read_text(encoding="utf-8"))
    except Exception:
        res["notes"].append("asset_registry.json 缺失/损坏——承载角色脸锚机检跳过。")
        return res
    try:
        identity = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    except Exception:
        identity = {}
    chars = {str(c.get("id") or "").strip(): c
             for c in (identity.get("characters") or []) if isinstance(c, dict)}

    def _ready_anchor_paths(ref: str) -> List[str]:
        """ref=`CHAR_xx` 或 `CHAR_xx/形态` → 该（形态级更精准）承载角色可注入的 ready 脸锚路径。"""
        cid = ref.split("/", 1)[0]
        ch = chars.get(cid)
        if not isinstance(ch, dict):
            return []
        paths: List[str] = []
        seen: Set[str] = set()
        base._collect_ready_image_paths(
            ch.get("external_visual_references"), root, paths, seen,
            allow_non_shared=True, allow_pending_user_reference=True)
        bare = "/" not in ref  # 裸 CHAR_xx 命中全形态；形态级只命中该形态（同 runner 解析）
        for form in ch.get("forms") or []:
            if not isinstance(form, dict):
                continue
            fname = str(form.get("form") or "常态").strip()
            if not (bare or f"{cid}/{fname}" == ref):
                continue
            base._collect_ready_image_paths(form.get("reference_group"), root, paths, seen)
            base._collect_ready_image_paths(form.get("reference_atlas"), root, paths, seen)
        return paths

    exempt = os.environ.get("N2D_ALLOW_UNANCHORED_IDENTITY_PLATE") == "1"
    for asset in assets.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        carried = base._asset_carried_identities(asset)
        if not carried:
            continue
        aid = str(asset.get("id") or asset.get("name") or "?").strip()
        anchorable = [ref for ref in carried if _ready_anchor_paths(ref)]
        if anchorable:
            continue
        carried_txt = "、".join(str(c) for c in carried)
        unknown = [ref for ref in carried if ref.split("/", 1)[0] not in chars]
        if unknown and len(unknown) == len(carried):
            code, why = "carried_identity_unknown", \
                f"承载角色 {carried_txt} 在 identity_registry 不存在——无脸锚可注入"
        else:
            code, why = "unanchored_identity_plate", \
                f"承载角色 {carried_txt} 在 identity_registry 无任何 ready 脸锚——出图会另画新脸"
        if exempt:
            res["findings"].append({"level": "warn", "code": code + "_exempted",
                                    "msg": f"资产 {aid}：{why}（N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1 显式豁免·留痕）"})
            continue
        res["findings"].append({"level": "block", "code": code,
                                "msg": f"资产 {aid}：{why}。先把承载角色脸部特写/正面参考置 ready"
                                       "（形态级 `CHAR_xx/形态` 更精准），或显式豁免 "
                                       "N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1。"})
    return res


def _resolve_shared_png(root: Path, rel: str) -> Optional[Path]:
    """资产 reference_group 里的 png 相对路径 → 实际文件（兼容 作品根相对 / 共享相对 / 仅文件名）。"""
    rel = str(rel or "").strip()
    if not rel.lower().endswith(".png"):
        return None
    for cand in (root / rel, root / "出图" / "共享" / rel,
                 root / "出图" / "共享" / "图片" / Path(rel).name):
        if cand.exists():
            return cand
    return None


def _asset_face_pngs(asset: Dict[str, Any]) -> List[str]:
    """资产 reference_group / scale_reference 里所有 png 相对路径（faceless 像素核验目标）。"""
    rg = asset.get("reference_group")
    out: List[str] = []
    def walk(node: Any) -> None:
        if isinstance(node, str):
            if node.lower().endswith(".png"):
                out.append(node)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(rg)
    return out


def audit_asset_face_policy(root: Path) -> Dict[str, Any]:
    """人物脸一致性铁律（A·face_policy 落档机检）：含人脸资产定妆绝不放任自由生成脸。

    对 asset_registry 每个资产解析 face_policy（codex_image_runner.resolve_face_policy 单一真值源）：
      - face_locked：必须能折入 owner/承载角色脸锚——无任何承载角色 = `asset_face_locked_no_owner` 硬拦
        （脸锚 ready 与否另由 audit_carried_identity_anchors 核，二者互补）。
      - faceless：对已生成的 PNG **实时像素核验**（face_consistency.verify_faceless），检出清晰脸
        = `asset_faceless_face_detected` 硬拦（握持比例镜画出可辨识脸=脸漂真因）。**不信任**资产里手写的
        face_consistency.verdict（证现实不证声明）——一律重新像素核验；缺 insightface 则降级人审 advisory。
    none（无人物）跳过。runner/face_consistency 不可加载 → available=False 优雅跳过。"""
    res: Dict[str, Any] = {"available": True, "findings": [], "notes": []}
    base = _load_sibling("codex_image_runner")
    if base is None or not hasattr(base, "resolve_face_policy"):
        res["available"] = False
        res["notes"].append("codex_image_runner.resolve_face_policy 不可用——face_policy 机检跳过。")
        return res
    fc = _load_review_module("face_consistency")
    try:
        assets = json.loads((root / "出图" / "共享" / "asset_registry.json").read_text(encoding="utf-8"))
    except Exception:
        res["notes"].append("asset_registry.json 缺失/损坏——face_policy 机检跳过。")
        return res
    for asset in assets.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        aid = str(asset.get("id") or asset.get("name") or "?").strip()
        policy = base.resolve_face_policy(asset)
        if policy == "none":
            continue
        if policy == "face_locked":
            carried = base._asset_carried_identities(asset) if hasattr(base, "_asset_carried_identities") else []
            if not carried:
                res["findings"].append({"level": "block", "code": "asset_face_locked_no_owner",
                    "msg": f"资产 {aid}：脸策略=face_locked（画面有具名角色脸）却无 owner/carries_identity 可折脸锚"
                           "——会自画新脸。补 `owner: CHAR_xx` 或 `carries_identity`，或改 `face_policy: faceless`。"})
            continue
        # faceless：优先信任**持久机器证据**（asset.face_consistency·source=machine_pixel 且 png_sha256 新鲜
        # ·record_faceless_evidence 写入）；缺/陈旧/手写 → 实时像素核验（证现实不证声明·绝不信手写 verdict）。
        pngs = _asset_face_pngs(asset)
        checked = False
        for rel in pngs:
            full = _resolve_shared_png(root, rel)
            if full is None:
                continue  # 尚未生成 → 出图时由 faceless prompt note 约束，生成后再核
            current_sha = _sha256_file(full)
            fresh = _faceless_fresh_record(asset, rel, current_sha) if current_sha else None
            if fresh is not None:
                checked = True
                if fresh.get("verdict") == "block":
                    res["findings"].append({"level": "block", "code": "asset_faceless_face_detected",
                        "msg": f"资产 {aid}：faceless 脸策略，登记的机器证据（png_sha256 新鲜）记 {rel} 检出 "
                               f"{fresh.get('clear_faces')} 张清晰脸——脸漂。重出为背身/裁脸/无脸中性人台，或改 face_locked 折 owner 脸锚。"})
                continue  # ok 的新鲜机器证据 → 放行，不必重跑 insightface
            if fc is None or not hasattr(fc, "verify_faceless"):
                res["notes"].append(f"资产 {aid}：{rel} 无新鲜机器证据且 verify_faceless 不可用——faceless 像素核验跳过（人审）。")
                continue
            v = fc.verify_faceless(str(full))
            checked = True
            if v.get("verdict") == "block":
                res["findings"].append({"level": "block", "code": "asset_faceless_face_detected",
                    "msg": f"资产 {aid}：faceless 脸策略，但 {rel} 像素核验检出 {v.get('clear_faces')} 张清晰脸"
                           f"（max_ratio={v.get('max_ratio')}）——握持比例/尺度参考画出了可辨识人脸=脸漂。"
                           "重出为背身/裁到下巴以下/无脸中性人台，或改 `face_policy: face_locked` 并折入 owner 脸锚。"})
            elif v.get("verdict") == "unavailable":
                res["findings"].append({"level": "warn", "code": "asset_faceless_unverified_degraded",
                    "msg": f"资产 {aid}：{rel} faceless 像素核验降级（{v.get('reason','无 insightface')}）——"
                           "跑 `image_qc --record-faceless` 在有 insightface 处登记机器证据，或人审确认无清晰脸。"})
        if pngs and not checked:
            res["notes"].append(f"资产 {aid}：faceless PNG 尚未生成，出图时按 faceless 约束生成后再核。")
    return res


def _faceless_fresh_record(asset: Dict[str, Any], rel: str, current_sha: Optional[str]):
    """取该 faceless PNG 的**新鲜机器证据**：asset.face_consistency.source==machine_pixel 且某 record 的
    png==rel 且 png_sha256==当前 PNG sha。手写/无机器源/陈旧(sha 不匹配) → None（不信任·走实时重验）。"""
    if not current_sha:
        return None
    rec = asset.get("face_consistency")
    if not isinstance(rec, dict) or rec.get("source") != "machine_pixel":
        return None
    for r in rec.get("records") or []:
        if isinstance(r, dict) and r.get("png") == rel and r.get("png_sha256") and r.get("png_sha256") == current_sha:
            return r
    return None


def record_faceless_evidence(root: Path, *, write: bool = True) -> Dict[str, Any]:
    """faceless 像素核验**产出端**：跑 verify_faceless 把结果（含 png_sha256 指纹）写回 asset_registry 的
    `asset.face_consistency`（source=machine_pixel），当**持久机器证据**——替换手写自断言 verdict，闭合
    "证现实不证声明"（gate 据 png_sha256 新鲜度信任，图一重出即陈旧失效→重验）。

    只对 faceless 资产、已生成且能核验（有 insightface）的 PNG 写记录；unavailable 不写假证据。
    需要 insightface；缺则 available=False 不写。返回 {available, recorded, notes}。"""
    out: Dict[str, Any] = {"available": True, "recorded": [], "notes": []}
    base = _load_sibling("codex_image_runner")
    fc = _load_review_module("face_consistency")
    if base is None or not hasattr(base, "resolve_face_policy"):
        out["available"] = False
        out["notes"].append("codex_image_runner.resolve_face_policy 不可用——无法登记 faceless 证据。")
        return out
    if fc is None or not hasattr(fc, "verify_faceless"):
        out["available"] = False
        out["notes"].append("face_consistency.verify_faceless 不可用（缺 insightface）——无法登记 faceless 证据。")
        return out
    reg_path = root / "出图" / "共享" / "asset_registry.json"
    try:
        assets = json.loads(reg_path.read_text(encoding="utf-8"))
    except Exception as exc:
        out["available"] = False
        out["notes"].append(f"asset_registry.json 读取失败：{exc}")
        return out
    changed = False
    attempted = 0
    unavailable = 0
    for asset in assets.get("assets") or []:
        if not isinstance(asset, dict) or base.resolve_face_policy(asset) != "faceless":
            continue
        aid = str(asset.get("id") or asset.get("name") or "?").strip()
        recs: List[Dict[str, Any]] = []
        for rel in _asset_face_pngs(asset):
            full = _resolve_shared_png(root, rel)
            if full is None:
                continue
            sha = _sha256_file(full)
            v = fc.verify_faceless(str(full))
            attempted += 1
            if v.get("verdict") == "unavailable" or not sha:
                unavailable += 1
                out["notes"].append(f"资产 {aid}：{rel} 无法核验（{v.get('reason','')}）——不写假证据。")
                continue
            recs.append({"png": rel, "png_sha256": sha, "verdict": v.get("verdict"),
                         "clear_faces": v.get("clear_faces"), "max_ratio": v.get("max_ratio")})
        if recs:
            asset["face_consistency"] = {"source": "machine_pixel",
                                         "checker": "face_consistency.verify_faceless", "records": recs}
            changed = True
            out["recorded"].append({"asset": aid, "records": recs})
    if changed and write:
        reg_path.write_text(json.dumps(assets, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if attempted and unavailable == attempted and not out["recorded"]:
        out["available"] = False
    return out


def _registry_path() -> Path:
    return Path("出图") / "共享" / "identity_registry.json"


def _split_character_names(raw: str) -> Set[str]:
    names: Set[str] = set()
    for part in re.split(r"[/／、,，|]+", str(raw or "")):
        name = part.strip()
        if len(name) >= 2:
            names.add(name)
    return names


def _flatten_reference_paths(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            out.extend(_flatten_reference_paths(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(_flatten_reference_paths(item))
        return out
    return []


def _add_alias(out: Set[str], raw: Any) -> None:
    alias = str(raw or "").strip()
    if len(alias) < 2:
        return
    out.add(alias)
    if "_" in alias:
        out.add(alias.replace("_", ""))


def _character_dna_text(*values: Any) -> str:
    parts: List[str] = []
    keys = ("face", "hair", "outfit", "accessories", "texture")
    for value in values:
        if isinstance(value, dict):
            parts.extend(str(value.get(k) or "").strip() for k in keys)
        elif isinstance(value, str):
            parts.append(value.strip())
    return " ".join(p for p in parts if p)


def _flatten_text_atoms(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: List[str] = []
        for item in value.values():
            out.extend(_flatten_text_atoms(item))
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            out.extend(_flatten_text_atoms(item))
        return out
    return []


OUTFIT_SIGNAL_KEYWORDS = (
    "衣", "袍", "装", "裙", "甲", "铠", "盔", "护", "披风", "斗篷", "披帛",
    "腰封", "腰带", "袖", "领", "衣摆", "裙摆", "襟", "纹", "绣", "甲片",
)
OUTFIT_SKIP_TERMS = {"服装", "衣服", "衣着", "外衣", "造型", "妆造", "穿着", "无"}
OUTFIT_SPLIT_RE = re.compile(r"[\s,，;；、/|·:：()（）\[\]【】{}<>《》\"'`]+")
OUTFIT_NORM_RE = re.compile(r"[\s_.,，;；、/|·:：()（）\[\]【】{}<>《》\"'`-]+")


def _normalize_outfit_match(raw: Any) -> str:
    return OUTFIT_NORM_RE.sub("", str(raw or "").strip())


def _looks_like_outfit_term(term: str) -> bool:
    if len(term) < 2 or term in OUTFIT_SKIP_TERMS:
        return False
    return any(k in term for k in OUTFIT_SIGNAL_KEYWORDS)


def _extract_outfit_terms(value: Any) -> Set[str]:
    """Extract durable costume/garment tokens from registry prose.

    This intentionally ignores generic identity/name aliases unless they contain a
    garment signal. Costume lint can then be registry-driven without treating a
    character name as an outfit claim.
    """
    terms: Set[str] = set()
    for atom in _flatten_text_atoms(value):
        raw = str(atom or "").strip()
        if not raw:
            continue
        pieces = OUTFIT_SPLIT_RE.split(raw)
        if len(_normalize_outfit_match(raw)) <= 28:
            pieces.append(raw)
        for piece in pieces:
            norm = _normalize_outfit_match(piece)
            if _looks_like_outfit_term(norm):
                terms.add(norm)
    return terms


def _outfit_terms_from_form(form: Dict[str, Any]) -> Set[str]:
    sources: List[Any] = [
        form.get("form"),
        form.get("asset_key"),
        form.get("display"),
        form.get("anchor_phrase"),
        form.get("character_dna_text"),
        form.get("wardrobe_profile"),
        form.get("wardrobe_profile_text"),
        form.get("outfit_aliases"),
        form.get("wardrobe_aliases"),
        form.get("outfit_terms"),
        form.get("reference_stems"),
        form.get("strong_aliases"),
        form.get("weak_aliases"),
    ]
    return _extract_outfit_terms(sources)


def load_registry_forms(root: Path) -> Optional[List[Dict[str, Any]]]:
    """identity_registry.json → 角色形态元数据（prompt 交接 lint 用）。

    返回 None 表示 registry 缺失/损坏，此时跳过交接身份 lint，避免误报。
    """
    path = root / _registry_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    forms: List[Dict[str, Any]] = []
    for ch in (data.get("characters") or []):
        cid = str(ch.get("id") or "").strip()
        if not cid:
            continue
        name_aliases = _split_character_names(str(ch.get("name") or ""))
        for form in (ch.get("forms") or []):
            fm = str(form.get("form") or "").strip()
            asset_key = str(form.get("asset_key") or "").strip()
            if not fm:
                continue
            key = f"{cid}/{fm}"
            wardrobe_profile = form.get("wardrobe_profile") if isinstance(form.get("wardrobe_profile"), dict) else {}
            strong_aliases: Set[str] = {cid, key}
            weak_aliases: Set[str] = set(name_aliases)
            reference_stems: Set[str] = set()
            if asset_key:
                _add_alias(strong_aliases, asset_key)
                _add_alias(strong_aliases, f"定妆_{asset_key}")
                _add_alias(weak_aliases, asset_key.split("_", 1)[0])
            for ref_path in _flatten_reference_paths(form.get("reference_group") or {}):
                stem = Path(ref_path).stem
                if ".png" in str(ref_path).lower():
                    reference_stems.add(stem)
                _add_alias(strong_aliases, stem)
                if stem.startswith("定妆_"):
                    _add_alias(strong_aliases, stem.removeprefix("定妆_"))
                    parts = stem.removeprefix("定妆_").split("_")
                    if parts and len(parts[0]) >= 2:
                        weak_aliases.add(parts[0])
            display = asset_key or "/".join([cid, fm])
            ref_count = len({Path(p).stem for p in _flatten_reference_paths(form.get("reference_group") or {})})
            forms.append({
                "id": cid,
                "form": fm,
                "key": key,
                "asset_key": asset_key,
                "scope": str(ch.get("scope") or "").strip(),  # 核心/长线/全篇只用于提示文案；④ 表情库硬闸对所有人物生效
                "anchor_phrase": str(form.get("anchor_phrase") or ""),
                "character_dna_text": _character_dna_text(ch.get("character_dna"), form.get("character_dna")),
                "wardrobe_profile": wardrobe_profile,
                "wardrobe_profile_text": " ".join(_flatten_text_atoms(wardrobe_profile)),
                "outfit_aliases": sorted(_extract_outfit_terms([
                    form.get("character_dna", {}).get("outfit") if isinstance(form.get("character_dna"), dict) else "",
                    wardrobe_profile,
                    form.get("outfit_aliases"),
                    form.get("wardrobe_aliases"),
                ])),
                "display": display,
                "ref_count": ref_count,  # 该形态 reference_group 的多角度参考张数（C4：喂全角度组给多参考后端）
                "reference_stems": reference_stems,
                "strong_aliases": strong_aliases,
                "weak_aliases": weak_aliases,
                # 辨识标记（MK1·疤痕/胎记/纹身/异瞳…）出图前文本预检；与 n2d-review marks_consistency 同义，
                # 但本 skill 自留一份不跨 import（独立性铁律）。
                "identity_marks": [m for m in (_normalize_identity_mark(r)
                                               for r in (form.get("identity_marks") or [])) if m],
            })
    return forms


def registry_ref_counts(forms: Optional[List[Dict[str, Any]]]) -> Dict[str, int]:
    """角色 base id → 其各形态 reference_group 的最大多角度张数。纯函数·可测（C4 用）。"""
    out: Dict[str, int] = {}
    for f in forms or []:
        cid = str(f.get("id") or "")
        if cid:
            out[cid] = max(out.get(cid, 0), int(f.get("ref_count") or 0))
    return out


# 逐镜块里 `资产身份注册层` 行引用的身份键，形如 `CHAR_01/常态`、`CHAR_SHEN/常态`
# （反引号包裹）或裸 CHAR_SHEN。多人同框的主角星标（CHAR_SHEN* / CHAR_SHEN/常态*）
# 是调度标记，不属于 registry id，比较前需剥掉。
IDENTITY_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_])`?(CHAR_[A-Za-z0-9_]*[A-Za-z0-9]\*?(?:/[^`\s，；、*]+)?\*?)`?"
    r"(?![A-Za-z0-9_\u4e00-\u9fff.-])"
)
TAIL_HANDOFF_FIELDS = ("近景/反打身份锁定", "近景身份锁定", "反打身份锁定", "细粒度身份锁定",
                       "尾帧接力生成方式", "尾帧专用", "尾帧身份", "尾帧重抽提示",
                       "接力身份", "尾帧锁脸")
TAIL_LOCK_MARKERS = ("尾帧专用", "尾帧身份", "尾帧重抽提示", "接力身份", "尾帧锁脸")


def normalize_identity_ref(ref: str) -> str:
    """Prompt identity ref → registry lookup key.

    Accepts canonical `CHAR_01/常态*` and legacy hand-written `CHAR_01*/常态`.
    """
    return str(ref or "").strip().replace("*/", "/").rstrip("*")


def split_shot_blocks(md_text: str) -> List[Dict[str, str]]:
    """01_分镜出图.md → 逐镜块 [{label, body}]，按 `## ` 标题切。纯函数·可测。"""
    blocks: List[Dict[str, str]] = []
    cur_label: Optional[str] = None
    cur: List[str] = []
    for line in md_text.splitlines():
        if line.startswith("## "):
            if cur_label is not None:
                blocks.append({"label": cur_label, "body": "\n".join(cur)})
            cur_label = line[3:].strip()
            cur = []
        elif cur_label is not None:
            cur.append(line)
    if cur_label is not None:
        blocks.append({"label": cur_label, "body": "\n".join(cur)})
    return blocks


def _identity_layer_text(body: str) -> str:
    return "\n".join(
        line for line in str(body or "").splitlines()
        if "资产身份注册层" in line or "身份注册层" in line
    )


def _is_character_shot_body(body: str, id_refs: Optional[Sequence[str]] = None) -> bool:
    """角色镜判定的单一口径：有身份注册层 CHAR 引用，或身份层绑定了定妆角色参考。"""
    text = str(body or "")
    identity_layer = _identity_layer_text(text)
    if _declares_no_face_coverage(text):
        return False
    refs = list(id_refs) if id_refs is not None else IDENTITY_REF_RE.findall(text)
    if not refs and re.search(r"无人物|人物不露脸|无角色", identity_layer):
        return False
    has_identity = bool(refs) and bool(identity_layer)
    has_makeup_ref = bool(re.search(r"定妆_[^_\s`，；]+", identity_layer))
    return has_identity or has_makeup_ref


def _declares_no_face_coverage(body: str) -> bool:
    text = str(body or "")
    return bool(re.search(r"脸部覆盖豁免|无可比对人脸|人物不露脸|不露正脸|只拍手|只拍腕|手腕特写|物件特写", text))


PNG_TOKEN_RE = re.compile(r"`([^`]+\.png)`|([^\s`，；。)）]+\.png)")
TARGET_PNG_LINE_MARKERS = ("目标", "输出", "落档", "存档", "首帧", "本镜")


def _png_tokens(text: str) -> List[str]:
    out: List[str] = []
    for m in PNG_TOKEN_RE.finditer(str(text or "")):
        raw = next((g for g in m.groups() if g), "")
        token = raw.strip().strip("`'\"，。；、:：)）]")
        if token:
            out.append(token)
    return out


def _is_reference_png(path: str) -> bool:
    s = str(path or "")
    stem = Path(s).stem
    return bool(
        stem.startswith("定妆_")
        or stem.startswith(("CHAR_", "LOC_", "PROP_", "OUTFIT_", "VFX_"))
        or "/共享/" in s
        or "出图/共享/" in s
    )


def _extract_target_pngs(body: str) -> List[str]:
    """从逐镜 prompt 提取本镜全部落档 PNG。优先目标/落档行，排除定妆/共享参考图。"""
    fallback: List[str] = []
    for line in str(body or "").splitlines():
        tokens = [p for p in _png_tokens(line) if not _is_reference_png(p)]
        if not tokens:
            continue
        if any(marker in line for marker in TARGET_PNG_LINE_MARKERS):
            return tokens
        fallback.extend(tokens)
    return fallback


def _extract_target_png(body: str) -> Optional[str]:
    """从逐镜 prompt 提取本镜首个落档 PNG。保留给旧调用点使用。"""
    targets = _extract_target_pngs(body)
    return targets[0] if targets else None


def _primary_slot_identity_refs(body: str) -> List[str]:
    """逐镜多人槽位里显式标为 primary/主检/星标 的身份引用。

    Dialogue/reverse shots often register both participants for continuity, but
    only one face is intended as the primary comparable identity.  Without this
    slot hint, coverage can require the off-screen/reacting character on every
    frame and produce false hard blocks.
    """
    refs: List[str] = []
    seen: Set[str] = set()
    for line in str(body or "").splitlines():
        if "SLOT_" not in line or not any(token in line for token in ("primary", "主检", "星标")):
            continue
        for fragment in re.split(r"(?=SLOT_\d+\s*[:：])", line):
            if not fragment.strip() or not any(token in fragment for token in ("primary", "主检", "星标")):
                continue
            match = IDENTITY_REF_RE.search(fragment)
            if not match:
                continue
            raw = match.group(1)
            norm = normalize_identity_ref(raw)
            if norm and norm not in seen:
                seen.add(norm)
                refs.append(raw)
    return refs


def character_shot_manifests(block: Dict[str, str]) -> List[Dict[str, Any]]:
    """逐镜 prompt → 角色镜覆盖清单项。

    该清单是后续 full 精度脸部参考覆盖闸门的输入，不依赖像素引擎。
    """
    body = block.get("body", "")
    label = block.get("label", "")
    raw_refs = IDENTITY_REF_RE.findall(body)
    all_refs = [normalize_identity_ref(ref) for ref in raw_refs]
    if not _is_character_shot_body(body, all_refs):
        return []
    starred_refs = [normalize_identity_ref(ref) for ref in raw_refs if "*" in ref]
    primary_refs = [normalize_identity_ref(ref) for ref in _primary_slot_identity_refs(body)]
    id_refs = starred_refs or primary_refs or all_refs
    targets = _extract_target_pngs(body) or [None]
    out: List[Dict[str, Any]] = []
    for png in targets:
        shot = _shot_key(png) or _shot_key(label) or label
        out.append({
            "label": label,
            "shot": shot,
            "png": png,
            "identity_refs": sorted(set(id_refs)),
        })
    return out


def character_shot_manifest(block: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """Backward-compatible first manifest for tests and older callers."""
    manifests = character_shot_manifests(block)
    return manifests[0] if manifests else None


def _declares_no_tail_frame(body: str) -> bool:
    text = str(body or "")
    return bool(
        re.search(r"尾帧(?:接力生成方式|专用重抽提示)?(?:\*\*)?\s*[：:]\s*[`]*无[`]*", text)
        or re.search(r"最终镜[，,、；;\s]*无尾帧", text)
        or re.search(r"end_state\s*交尾帧\s*[`]*无[`]*", text)
    )


def _tail_handoff_text(body: str) -> str:
    lines: List[str] = []
    for line in str(body or "").splitlines():
        if any(field in line for field in TAIL_HANDOFF_FIELDS):
            lines.append(line)
            continue
        # 兼容手写 prompt：没有字段名，但明确写了某个 *_end.png 的主体/入点。
        if re.search(r"(?:_end\.png|镜头\d+_end|Clip_\d+_end).*(?:主体|服务|承担|入点|出现)", line):
            lines.append(line)
    return "\n".join(lines)


def _tail_lock_text(body: str) -> str:
    return "\n".join(
        line for line in str(body or "").splitlines()
        if any(marker in line for marker in TAIL_LOCK_MARKERS)
    )


def _matches_alias(text: str, aliases: Set[str]) -> bool:
    return any(alias and alias in text for alias in aliases)


def _mentioned_handoff_forms(body: str, registry_forms: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not registry_forms:
        return []
    if _declares_no_tail_frame(body):
        return []
    identity_text = _identity_layer_text(body)
    current_refs = {normalize_identity_ref(ref) for ref in IDENTITY_REF_RE.findall(identity_text)}
    if not current_refs:
        return []
    tail_text = _tail_handoff_text(body)
    if not tail_text:
        return []
    current_base_ids = {ref.split("/", 1)[0] for ref in current_refs}
    candidates: List[Dict[str, Any]] = []
    for form in registry_forms:
        key = str(form.get("key") or "")
        cid = str(form.get("id") or "")
        if key in current_refs or cid in current_refs:
            continue
        strong_hit = _matches_alias(tail_text, form.get("strong_aliases") or set())
        weak_hit = _matches_alias(tail_text, form.get("weak_aliases") or set())
        if not (strong_hit or weak_hit):
            continue
        # 同一角色多形态只按强别名判交接，避免"沈念"同时命中沈念所有形态。
        if cid in current_base_ids and not strong_hit:
            continue
        if key:
            candidates.append({**form, "_strong_hit": strong_hit})
    strong_cids = {str(f.get("id") or "") for f in candidates if f.get("_strong_hit")}
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for form in candidates:
        key = str(form.get("key") or "")
        cid = str(form.get("id") or "")
        if cid in strong_cids and not form.get("_strong_hit"):
            continue
        if key not in seen:
            out.append(form)
            seen.add(key)
    return out


def _tail_lock_mentions_form(tail_lock_text: str, form: Dict[str, Any]) -> bool:
    # 专用锁定提示必须落到可执行锚点：CHAR_xx/形态、asset_key 或定妆文件名；只写中文名不够。
    strong_aliases = set(form.get("strong_aliases") or set())
    return _matches_alias(tail_lock_text, strong_aliases)


def _lint_tail_identity_handoff(
    label: str,
    body: str,
    registry_forms: Optional[List[Dict[str, Any]]],
) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    if _declares_no_tail_frame(body):
        return findings
    handoff_forms = _mentioned_handoff_forms(body, registry_forms)
    if not handoff_forms:
        return findings
    tail_lock = _tail_lock_text(body)
    names = "、".join(f"{f.get('key')}({f.get('display')})" for f in handoff_forms)
    if not tail_lock:
        findings.append({
            "level": "block",
            "code": "tail_identity_handoff_missing_prompt",
            "msg": (
                f"{label}：尾帧/下一镜入点出现 {names}，但当前资产身份注册层未绑定该身份；"
                "缺『尾帧专用重抽提示』，容易用主镜角色 prompt 重画接力角色脸。"
            ),
        })
        return findings
    unlocked = [f for f in handoff_forms if not _tail_lock_mentions_form(tail_lock, f)]
    if unlocked:
        names = "、".join(f"{f.get('key')}({f.get('display')})" for f in unlocked)
        findings.append({
            "level": "block",
            "code": "tail_identity_handoff_unlocked",
            "msg": (
                f"{label}：尾帧专用提示提到交接身份 {names}，但未写目标 `CHAR_xx/形态`、"
                "`asset_key` 或 `定妆_<角色>_<形态>` 脸部参考；只靠中文名会被局部修复美化成通用脸。"
            ),
        })
    return findings


def _lint_tail_relay_method(label: str, body: str) -> List[Dict[str, str]]:
    """尾帧锁脸铁律（防尾帧脸漂的**生成侧硬闸**）：本镜若产出尾帧/接力素材，必须声明
    『以本镜首帧 image2image/图生图 为母图、只改表情/微动作、不重画脸』。缺声明=纯文生图
    兜底会生出新脸（最常见的同角色尾帧漂，handoff lint 抓不到，因为没换角色）。
    仅角色镜调用；本镜明确『尾帧：无』时跳过。纯函数·可测。"""
    if _declares_no_tail_frame(body):
        return []
    has_tail = bool(re.search(r"尾帧|_end\.png|镜头\d+_end|Clip_\d+_end|接力", body))
    if not has_tail:
        return []
    relay_ok = bool(re.search(r"image2image|图生图|i2i|母图|以.{0,16}首帧.{0,8}为母", body, re.I))
    text2img = _has_unnegated_text2img(body)
    if relay_ok and not text2img:
        return []
    return [{"level": "block", "code": "tail_relay_not_image2image",
             "msg": f"{label}：本镜产出尾帧但未声明『以首帧 image2image 为母图、只改表情不重画脸』"
                    "（缺锁脸接力 → 纯文生图兜底 → 尾帧脸漂）"}]


def _has_unnegated_text2img(text: str) -> bool:
    """Return true only when text2image appears as an allowed fallback, not as a ban."""
    pattern = re.compile(r"纯文生图|text2image|t2i|文生图", re.I)
    negation = re.compile(
        r"(禁|禁止|严禁|不得|不许|不要|不能|不可|避免|无|no|not|never)"
        r"[\s`*_（(]*[^\n。；;，,、]{0,14}$",
        re.I,
    )
    for match in pattern.finditer(str(text or "")):
        before = text[max(0, match.start() - 32):match.start()]
        if negation.search(before):
            continue
        return True
    return False


# 近景大表情脸锚 gate（④ 治表情镜脸漂）：近景/特写/反打 + 强情绪的角色镜，若 prompt
# 未引用同源『基础脸锚 face_anchor_refs / 表情库 expressions / 脸部特写』参考，AI 会为大表情重画整张脸 → 表情镜脸漂。
# 2026-06：基础定妆包不再按主配角放松；所有人物近景大表情都 hard block，角色体量只影响 LoRA/主体库升档。
# STRONG_EMOTION_MARKERS / EXPRESSION_LIB_MARKERS 已上提 n2d_const 单一真值源（见文件顶部 import）。
# 近景识别：仅认中文近景词 + 作为整 token 的英文景别码，避免 "CU" 子串误命中正文。
_CLOSEUP_LINT_RE = re.compile(r"特写|近景|反打|过肩|ECU|BCU|MCU|(?<![A-Za-z])CU(?![A-Za-z])")


def _has_strong_emotion(body: str) -> bool:
    return any(m in str(body or "") for m in STRONG_EMOTION_MARKERS)


def _references_expression_lib(body: str) -> bool:
    return any(m in str(body or "") for m in EXPRESSION_LIB_MARKERS)


# ④ 表情库硬闸对所有人物生效；核心/长线还用于脸锚质量和跨集退化升硬闸。
CORE_SCOPES = ("全篇", "长线", "核心")


def is_core_scope(scope: str) -> bool:
    """Free-text scope matcher for core/long-running characters."""
    return any(marker in str(scope or "") for marker in CORE_SCOPES)


def core_char_ids(registry_forms: Optional[Sequence[Mapping[str, Any]]]) -> Set[str]:
    """registry_forms → 核心角色 base id 集合（scope ∈ 核心/长线/全篇）。纯函数·可测。"""
    return {str(f.get("id") or "").strip()
            for f in (registry_forms or [])
            if is_core_scope(str(f.get("scope") or "")) and f.get("id")}


def _lint_closeup_expression_lib(label: str, body: str,
                                 id_refs: Optional[Sequence[str]] = None,
                                 core_ids: Optional[Set[str]] = None) -> List[Dict[str, str]]:
    """近景大表情脸锚 gate（仅角色镜调用）：近景/特写/反打 + 强情绪角色镜须引用同源基础脸锚/表情库/脸部特写参考，
    否则大表情让 AI 自由重画整张脸 → 表情镜脸漂。纯函数·可测。

    ④ 分档更新：所有人物 → **block**。核心/长线只决定是否升 LoRA/原生主体 ID，不决定基础表情参考是否可省。"""
    text = str(body or "")
    if not _CLOSEUP_LINT_RE.search(text):
        return []
    # 只在正向段扫强情绪：负向 prompt 里 ban 哭/崩溃 不是要画大表情，扫全文会误判硬拦（同 _lint_outfit_form_binding）。
    if not _has_strong_emotion(_positive_prompt_text(text)):
        return []
    if _references_expression_lib(text):
        return []
    refs = {normalize_identity_ref(r).split("/")[0] for r in (id_refs or []) if r}
    hit_core = sorted(refs & set(core_ids or set()))
    scope_hint = f"（命中核心/长线：{'、'.join(hit_core)}）" if hit_core else ""
    return [{"level": "block", "code": "no_expression_lib_ref",
             "msg": f"{label}：近景/特写大表情角色镜{scope_hint}未引用『基础脸锚 face_anchor_refs / 表情库 expressions / 脸部特写参考』"
                    "——大表情让 AI 重画整张脸=脸漂高发；所有人物（含短线/功能角色）都必须先建同源表情库"
                    "或脸部特写参考，并在本镜引用，首尾双帧只插值。"}]


# C3 多主体空间绑定：同框 ≥2 角色需逐角色绑画面站位，否则多主体易串脸。
SPATIAL_POSITION_MARKERS = ("画左", "画右", "画中", "靠左", "靠右", "左侧", "右侧", "居中",
                            "前景", "后景", "背景", "中景", "近端", "远端", "左", "右",
                            "left", "right", "center", "foreground", "background")
BLOCKING_FIELD_MARKERS = ("blocking", "站位", "走位", "机位站位")
# 多人同框分层合成/原生主体执行策略放行集 —— 已上提 n2d_const.MULTI_SUBJECT_ACCEPTING_MARKERS，
# 本文件顶部 alias 为 MULTI_SUBJECT_STRATEGY_MARKERS，与 gate.py / shot_risk_audit.py 同源，
# 使本 lint 的 block ⊆ review 的同框 block（登记了这些策略 review 放行的镜，这里也放行，不误挡）。
def _distinct_char_bases(id_refs: Sequence[str]) -> Set[str]:
    """身份引用集合 → 去掉形态/星标后的角色 base id 集合（判多人同框）。"""
    return {normalize_identity_ref(r).split("/")[0] for r in (id_refs or []) if r}


OUTFIT_TOKEN_GROUPS: Dict[str, Tuple[str, ...]] = {
    "红衣": ("红衣", "红袍", "赤衣", "绯衣", "朱红宫装", "深红宫装", "红色宫装", "红色破旧宫装"),
    "白衣": ("白衣", "素衣", "月白", "素白", "白色宫装", "月白旧宫装", "灰白宫装"),
    "黑衣": ("黑衣", "玄衣", "黑袍", "玄色长袍"),
    "战甲": ("战甲", "甲胄", "盔甲", "铠甲", "护甲"),
}


def _positive_prompt_text(body: str) -> str:
    """Strip negative prompt sections before semantic outfit matching."""
    text = str(body or "")
    return re.split(r"\*\*?负向\s*prompt|\bnegative\s*prompt", text, maxsplit=1, flags=re.I)[0]


def _outfit_claims_in_text(text: str) -> Dict[str, Set[str]]:
    found: Dict[str, Set[str]] = {}
    src = str(text or "")
    for group, tokens in OUTFIT_TOKEN_GROUPS.items():
        if any(token and token in src for token in tokens):
            found[group] = set(tokens)
    return found


def _add_registry_outfit_claims(text: str, registry_forms: Optional[Sequence[Dict[str, Any]]]) -> Dict[str, Set[str]]:
    claims = _outfit_claims_in_text(text)
    src_norm = _normalize_outfit_match(text)
    for form in registry_forms or []:
        terms = _outfit_terms_from_form(form)
        hits = {term for term in terms if term and term in src_norm}
        if not hits:
            continue
        key = str(form.get("key") or form.get("form") or "registry")
        label = f"registry:{key}"
        claims.setdefault(label, set()).update(hits)
    return claims


def _outfit_claim_display(group: str, tokens: Set[str]) -> str:
    if not group.startswith("registry:"):
        return group
    return " / ".join(sorted(tokens, key=lambda s: (len(s), s), reverse=True)[:3])


def _form_advertises_outfit_claim(form: Dict[str, Any], tokens: Set[str]) -> bool:
    aliases = sorted((form.get("strong_aliases") or set()) | (form.get("weak_aliases") or set()))
    haystack = " ".join([
        str(form.get("form") or ""),
        str(form.get("asset_key") or ""),
        str(form.get("anchor_phrase") or ""),
        str(form.get("character_dna_text") or ""),
        str(form.get("wardrobe_profile_text") or ""),
        str(form.get("display") or ""),
        " ".join(str(s) for s in form.get("reference_stems") or []),
        " ".join(str(a) for a in aliases),
        " ".join(str(a) for a in form.get("outfit_aliases") or []),
    ])
    haystack_norm = _normalize_outfit_match(haystack)
    own_terms = _outfit_terms_from_form(form)
    claim_terms = {_normalize_outfit_match(t) for t in tokens if t}
    return bool(own_terms & claim_terms) or any(term and term in haystack_norm for term in claim_terms)


def _lint_outfit_form_binding(label: str, body: str, id_refs: Sequence[str],
                              registry_forms: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """Single-character costume/form guard.

    If a shot explicitly asks for a durable outfit form (红衣/白衣/战甲..., or a
    wardrobe_profile/character_dna.outfit term from registry) it must bind the
    matching CHAR_xx/形态, not a nearby identity state with another costume.
    Multi-character shots are left to human review to avoid assigning a costume token to
    the wrong person.
    """
    if not registry_forms:
        return []
    normalized = [normalize_identity_ref(ref) for ref in (id_refs or [])]
    if len(_distinct_char_bases(normalized)) != 1:
        return []
    exact_refs = sorted({ref for ref in normalized if "/" in ref})
    if not exact_refs:
        return []
    claims = _add_registry_outfit_claims(_positive_prompt_text(body), registry_forms)
    if not claims:
        return []

    by_key = {str(form.get("key") or ""): form for form in registry_forms}
    findings: List[Dict[str, str]] = []
    for rid in exact_refs:
        form = by_key.get(rid)
        if not form:
            continue
        for group, tokens in sorted(claims.items()):
            if _form_advertises_outfit_claim(form, tokens):
                continue
            display = _outfit_claim_display(group, tokens)
            findings.append({
                "level": "block",
                "code": "outfit_form_mismatch",
                "msg": (
                    f"{label}：正向 prompt 写了「{display}」类服饰/形态，但资产身份注册层绑定 `{rid}` "
                    f"（asset_key={form.get('asset_key') or '-'}）没有对应服饰定妆。"
                    "换装/形态变体必须新建独立 `CHAR_xx/形态`、wardrobe_profile 和 reference_group，禁止复用其它服饰状态参考。"
                ),
            })
    return findings


def _lint_multi_subject_spatial_binding(label: str, body: str,
                                        id_refs: Sequence[str]) -> List[Dict[str, str]]:
    """多人同框防串脸（C3·生成端预防）：≥2 具名角色同框却没声明逐角色空间站位/分层合成执行策略时 block。

    2026 研究：多主体身份混淆随参考数上升（DreamO/UMO）。Seedream4.5 / Nano Banana2 已支持多主体
    空间区域绑定——把每个角色绑到画面位置（画左/画右/前景）可在生成端按位锁主体、显著降串脸。
    2026-06 起空间绑定对所有后端 **block**，与 n2d-review gate 的 ≥2 同框 block、n2d-script shot_risk
    的 multi_subject must 同口径（不再「降级为建议」——那是已退役的执行时松动）。逃生口与 review 对齐：
    声明 blocking/站位、≥2 空间位置标记（画左/画右/前后景，LEFT/RIGHT/FOREGROUND/BACKGROUND_SLOT 子串亦计）、
    或登记 分别出图+合成/原生主体执行策略 任一即放行——使本 block ⊆ review 同框 block，不误挡 review 会放行的镜。
    纯函数·可测。"""
    if len(_distinct_char_bases(id_refs)) < 2:
        return []
    low = str(body or "").lower()
    if any(m.lower() in low for m in BLOCKING_FIELD_MARKERS):
        return []
    if sum(1 for m in SPATIAL_POSITION_MARKERS if m.lower() in low) >= 2:
        return []
    if any(m.lower() in low for m in MULTI_SUBJECT_STRATEGY_MARKERS):
        return []
    return [{"level": "block", "code": "multi_person_no_spatial_binding",
             "msg": f"{label}：多人同框但未声明逐角色空间站位（blocking / 画左·画右 / 前后景）"
                    "或分层合成/原生主体执行策略——多主体单帧 co-gen 必相互渗透串脸，2026-06 起对所有后端 block"
                    "（与 review 同框 gate、script 分镜 must 同口径）：补逐角色画面位置，或登记 分别出图+合成 / 原生主体策略。"}]


def _lint_native_multiref_coverage(label: str, body: str, id_refs: Sequence[str],
                                   form_ref_counts: Optional[Dict[str, int]],
                                   persistent_subject: Optional[bool] = None) -> List[Dict[str, str]]:
    """多角度参考喂养充分性（C4·advisory）：定妆库有多角度组、本镜却只引用了 1 张时提示喂全组。

    2026 原生多参考已 table-stakes（Seedream≤14 / 可灵 Elements≤4 张锁主体）。定妆库建了正/侧/背
    多角度组，却只把正面喂进去 = 没吃满后端锁主体能力。只在 registry 确有多角度组(≥3)时才 info，
    不噪；单参考后端可忽略。纯函数·可测。

    **后端分层（④）**：`persistent_subject=True`（Seedream/可灵/Sora）逐镜应按已注册主体 ID 引用 +
    单张干净强锚即可，2026 实践「单强锚 > 弱参考拼盘」——不必每镜堆全角度组（多样集只在*注册*环节喂）。
    所以对持久主体后端把「喂全组」的 nudge 换成「ID+单强锚」口径，不再误导其堆图；只有多参考后端
    （persistent_subject False/未知）才提示喂满全角度组。"""
    if not form_ref_counts:
        return []
    avail = max((form_ref_counts.get(b, 0) for b in _distinct_char_bases(id_refs)), default=0)
    if avail < 3:
        return []  # 没有多角度组可喂，免谈
    refd = len({
        t for t in _png_tokens(body)
        if "定妆_" in t or Path(str(t)).stem.startswith("CHAR_")
    })
    if refd >= min(avail, 3):
        return []  # 已喂≥3张（或全部）→ 充分
    if persistent_subject:
        return [{"level": "info", "code": "native_subject_anchor_ok",
                 "msg": f"{label}：持久主体后端(Seedream/可灵/Sora)逐镜按已注册主体 ID + 单张干净强锚引用即可"
                        f"（2026：单强锚 > 弱参考拼盘），不必每镜堆全角度组——多样集只在注册主体时喂；"
                        f"若该角色尚未注册主体，则回退多参考后端口径喂全组({avail} 张可喂，本镜 {refd})"}]
    return [{"level": "info", "code": "native_multiref_underfed",
             "msg": f"{label}：定妆库有 {avail} 张多角度参考，本镜参考图块只引用了 {refd} 张——"
                    "多参考后端(Seedream≤14 / 可灵Elements≤4)喂全角度组(正/侧/背)锁主体更稳；单参考后端可忽略"}]


def _lint_physical_lens_parameters(label: str, body: str) -> List[Dict[str, str]]:
    """物理镜头参数（advisory）：近景/特写镜头如果没有物理焦段/光圈参数，提示增强电影感。"""
    is_closeup = re.search(r'\b(CU|ECU|特写|近景|大特写)\b', body, re.IGNORECASE)
    
    if is_closeup:
        has_physical_params = re.search(r'\b(\d{2,3}mm|f/\d\.?\d?|焦段|光圈)\b', body, re.IGNORECASE)
        if not has_physical_params:
            return [{"level": "warn", "code": "missing_physical_lens_params",
                     "msg": f"{label}：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。"}]
    
    return []


def _lint_semantic_conflict(label: str, body: str) -> List[Dict[str, str]]:
    """语义冲突（advisory）：简单的文本级语义冲突排查（如白天与黑夜同现）。"""
    findings = []
    text = body.lower()
    if re.search(r"深夜|夜晚|夜间|黑夜", text) and re.search(r"阳光|明媚|白昼|正午", text):
         findings.append({"level": "warn", "code": "semantic_conflict",
                          "msg": f"{label}：提示词语义冲突（同时存在“夜晚”和“白昼/阳光”相关描述），易导致 AI 光影错乱。"})
    # 极简色温冲突
    if re.search(r"5600k", text) and re.search(r"3200k", text):
         findings.append({"level": "warn", "code": "semantic_conflict",
                          "msg": f"{label}：色温锚点冲突（同时存在 5600K 与 3200K 主光描述）。"})
    return findings


ACTION_EYELINE_MARKERS = (
    "fight_exchange", "magic_burst", "chase", "battle", "combat", "action keyframe",
    "打斗", "武打", "拆招", "交锋", "对打", "攻防", "追逐", "爆冲", "斜劈", "劈", "斩",
    "刺", "挥", "命中", "受击", "撞击", "投掷", "施法", "法术", "斗法", "枪线", "戟刃",
    "spear", "slash", "strike", "impact", "attack", "burst",
)
CAMERA_GAZE_EXCEPTION_MARKERS = (
    "opponent pov", "camera-as-opponent", "first-person pov", "pov shot", "direct address",
    "fourth wall", "主观镜头", "镜头代表对手", "镜头=对手", "第一人称", "破第四墙",
    "直视镜头=导演意图", "看镜头=导演意图",
)
CAMERA_EYE_CONTACT_RE = re.compile(
    r"(看向?镜头|望向?镜头|直视镜头|盯(?:着)?镜头|对(?:着)?镜头|看向?观众|直视观众|"
    r"looking\s+at\s+(?:the\s+)?viewer|look(?:s|ing)?\s+at\s+(?:the\s+)?viewer|"
    r"eye\s+contact\s+with\s+(?:the\s+)?camera|staring\s+at\s+(?:the\s+)?camera|"
    r"look(?:s|ing)?\s+into\s+(?:the\s+)?camera|gaze\s+into\s+(?:the\s+)?camera)",
    re.I,
)
FRONTAL_PORTRAIT_BIAS_RE = re.compile(
    r"(清晰正脸|主检清晰正脸|唯一清晰正脸|正脸特写|正面肖像|"
    r"clear\s+frontal\s+face|frontal\s+face|front-facing\s+face|portrait\s+pose|portrait-facing)",
    re.I,
)
ANTI_CAMERA_EYELINE_RE = re.compile(
    r"(不看镜头|不直视镜头|不与镜头对视|镜头是旁观者|镜头为旁观者|镜头是观察者|镜头为观察者|"
    r"视线锁定|锁定对手|看向(?!镜头|观众)|望向(?!镜头|观众)|瞄准|"
    r"not\s+looking\s+at\s+(?:the\s+)?camera|no\s+eye\s+contact\s+with\s+(?:the\s+)?camera|"
    r"camera\s+is\s+(?:an?\s+)?observer|gaze\s+locked\s+on|eyes\s+locked\s+on|"
    r"look(?:s|ing)?\s+toward|eyes?\s+(?:lift|lifting|turn|turning)\s+toward)",
    re.I,
)


def _is_action_eyeline_shot(body: str) -> bool:
    text = _positive_prompt_text(body).lower()
    return any(str(marker).lower() in text for marker in ACTION_EYELINE_MARKERS)


def _has_camera_gaze_exception(body: str) -> bool:
    text = _positive_prompt_text(body).lower()
    return any(str(marker).lower() in text for marker in CAMERA_GAZE_EXCEPTION_MARKERS)


def _frontal_match_is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 36):start].lower()
    return any(token in prefix for token in (
        "no ", "not ", "without ", "禁止", "不得", "不要", "不许", "不能", "不允许", "不生成", "无",
    ))


def _camera_gaze_match_is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 18):start].lower()
    return any(token in prefix for token in (
        "no ", "not ", "without ", "禁止", "不得", "不要", "不许", "不能", "不允许", "无", "不",
    ))


def _lint_action_eyeline(label: str, body: str) -> List[Dict[str, str]]:
    """动作/打斗镜视线铁律：镜头是旁观者，角色视线锁对手/武器/命中点，不能看主镜头。"""
    findings: List[Dict[str, str]] = []
    if not _is_action_eyeline_shot(body) or _has_camera_gaze_exception(body):
        return findings
    positive = _positive_prompt_text(body)
    if any(not _camera_gaze_match_is_negated(positive, m.start()) for m in CAMERA_EYE_CONTACT_RE.finditer(positive)):
        findings.append({
            "level": "block",
            "code": "combat_camera_eye_contact",
            "msg": f"{label}：打斗/动作/强互动镜写了直视主镜头/看观众；除非明确 opponent POV 或破第四墙，"
                   "镜头必须是旁观者，角色视线应锁定对手、武器来路或命中点。",
        })
    if any(not _frontal_match_is_negated(positive, m.start()) for m in FRONTAL_PORTRAIT_BIAS_RE.finditer(positive)):
        findings.append({
            "level": "block",
            "code": "combat_frontal_portrait_bias",
            "msg": f"{label}：打斗/动作镜含清晰正脸/frontal portrait 倾向，容易把拆招拍成看镜头摆拍；"
                   "改为可辨三分之二侧脸/侧脸/背身侧轮廓，并明确不与主镜头对视。",
        })
    if not ANTI_CAMERA_EYELINE_RE.search(positive):
        findings.append({
            "level": "warn",
            "code": "combat_eyeline_guard_missing",
            "msg": f"{label}：打斗/动作镜缺“不看镜头/镜头是旁观者/视线锁对手或命中点”的视线防呆句；"
                   "容易被脸部清晰约束带成 portrait pose。",
        })
    return findings


def _lint_camera_gaze_general(label: str, body: str) -> List[Dict[str, str]]:
    """镜头不是对视对象铁律·全场景版（非动作镜也查）：任何含人物镜，除非显式 POV/破第四墙/对观众特写，
    写了直视镜头/清晰正脸肖像倾向却无「不看镜头/视线锁场内目标」防呆句 → WARN（动作镜已由 _lint_action_eyeline
    升 block，本函数只补非动作镜的 advisory，治"角色摆拍宣传照、总看镜头"普遍隐患）。"""
    findings: List[Dict[str, str]] = []
    if _is_action_eyeline_shot(body) or _has_camera_gaze_exception(body):
        return findings  # 动作镜走 block 路径；POV 豁免
    positive = _positive_prompt_text(body)
    eye = any(not _camera_gaze_match_is_negated(positive, m.start()) for m in CAMERA_EYE_CONTACT_RE.finditer(positive))
    frontal = any(not _frontal_match_is_negated(positive, m.start()) for m in FRONTAL_PORTRAIT_BIAS_RE.finditer(positive))
    if (eye or frontal) and not ANTI_CAMERA_EYELINE_RE.search(positive):
        findings.append({
            "level": "warn",
            "code": "camera_gaze_portrait_bias",
            "msg": f"{label}：本镜含{'直视镜头' if eye else ''}{'/' if eye and frontal else ''}{'清晰正脸肖像' if frontal else ''}"
                   "倾向却无视线防呆句——除非是 POV/对观众特写，角色不应正对镜头摆拍/对视；"
                   "改可辨侧脸/过肩/三分之二，视线锁场内目标（对手/对话对象/所视之物）。",
        })
    return findings


# ── 辨识标记（MK1）出图前文本预检 · vendored 纯函数（不跨 import n2d-review·独立性铁律） ──────

def _mk_episode_num(ep: str) -> Optional[int]:
    m = re.search(r"(\d+)", str(ep or ""))
    return int(m.group(1)) if m else None


def _normalize_identity_mark(raw: Any) -> Optional[Dict[str, Any]]:
    """单条 identity_marks 归一：persistence → ('permanent',None) 或 ('acquired',集号)；
    无任何可机检搜索词 → None。纯函数·可测。"""
    if not isinstance(raw, Mapping):
        return None
    mark = {
        "mark_id": str(raw.get("mark_id") or raw.get("id") or "").strip(),
        "type": str(raw.get("type") or "").strip(),
        "region": str(raw.get("region") or "").strip(),
        "color": str(raw.get("color") or "").strip(),
        "plot_load": bool(raw.get("plot_load", False)),
        "keywords": [str(k).strip() for k in (raw.get("keywords") or []) if str(k).strip()],
        "persistence": "permanent", "acquired_ep": None,
    }
    pers = raw.get("persistence", "permanent")
    n = None
    if isinstance(pers, Mapping):
        n = _mk_episode_num(str(pers.get("acquired_at") or ""))
        if n is None and isinstance(pers.get("acquired_at"), (int, float)):
            n = int(pers["acquired_at"])
    elif isinstance(pers, str) and pers.strip() and pers.strip() != "permanent":
        n = _mk_episode_num(pers)
    if n is not None:
        mark["persistence"], mark["acquired_ep"] = "acquired", n
    return mark if _mark_tokens(mark) else None


def _mark_tokens(mark: Mapping[str, Any]) -> Set[str]:
    """该标记的搜索词：keywords ∪ 部位+类型 ∪ 类型 ∪ 部位 ∪ 颜色 ∪ mark_id 去前缀（≥2 字）。纯函数·可测。"""
    toks: Set[str] = set(k for k in (mark.get("keywords") or []) if len(str(k)) >= 2)
    region, mtype, color = (str(mark.get(k) or "").strip() for k in ("region", "type", "color"))
    if region and mtype:
        toks.add(region + mtype)
    for v in (mtype, region, color):
        if len(v) >= 2:
            toks.add(v)
    mid = str(mark.get("mark_id") or "").strip()
    if mid.upper().startswith("MARK_"):
        mid = mid[5:]
    for part in re.split(r"[_\-\s]+", mid):
        if len(part) >= 2 and not part.isdigit():
            toks.add(part)
    return toks


def _mark_desc(mark: Mapping[str, Any]) -> str:
    label = "".join(str(mark.get(k) or "") for k in ("color", "region", "type")).strip()
    return label or str(mark.get("mark_id") or "标记")


def _lint_identity_marks(label: str, body: str, id_refs: Sequence[str],
                         registry_forms: Optional[Sequence[Mapping[str, Any]]],
                         ep_num: Optional[int]) -> List[Dict[str, str]]:
    """出图前辨识标记预检（MK1 的 image_qc 侧·治"prompt 漏写标记锁→纯文生图丢标记"）。

    本镜在场角色（id/key 命中 id_refs，或强别名命中 body）的每条标记：
      - 永久 / 已获得标记未写进本镜 prompt → warn（疑似漂移/丢失或合理遮挡，人核对补回）；
      - 未获得标记（本集 < acquired_at）却写进 prompt → block（时间线穿帮）。
    纯函数·可测。"""
    findings: List[Dict[str, str]] = []
    if not registry_forms:
        return findings
    ref_set = {normalize_identity_ref(r) for r in (id_refs or [])}
    base_set = {r.split("/", 1)[0] for r in ref_set}
    for form in registry_forms:
        marks = form.get("identity_marks") or []
        if not marks:
            continue
        key = str(form.get("key") or "")
        cid = str(form.get("id") or "")
        present = (key in ref_set or cid in ref_set or cid in base_set
                   or _matches_alias(body, set(form.get("strong_aliases") or set())))
        if not present:
            continue
        for mark in marks:
            desc = _mark_desc(mark)
            acq = mark.get("acquired_ep")
            not_yet = (mark.get("persistence") == "acquired" and ep_num is not None
                       and acq is not None and ep_num < acq)
            referenced = any(tok in body for tok in _mark_tokens(mark))
            if not_yet:
                if referenced:
                    findings.append({"level": "block", "code": "identity_mark_anachronism",
                                     "msg": f"{label}：{form.get('display') or cid} 的辨识标记『{desc}』"
                                            f"在获得集第{acq}集之前就写进出图 prompt——时间线穿帮，删除或核对获得集。"})
            elif not referenced:
                load = "（载剧情）" if mark.get("plot_load") else ""
                findings.append({"level": "warn", "code": "identity_mark_missing",
                                 "msg": f"{label}：角色 {form.get('display') or cid} 的辨识标记『{desc}』{load}"
                                        f"未写进本镜出图 prompt——纯文生图会丢，补进资产身份注册层的标记锁，"
                                        f"或确认本镜该部位被遮挡/不入画。"})
    return findings


def lint_shot_block(
    block: Dict[str, str],
    valid_ids: Optional[Set[str]],
    registry_forms: Optional[List[Dict[str, Any]]] = None,
    asset_index: Optional[Dict[str, Any]] = None,
    form_ref_counts: Optional[Dict[str, int]] = None,
    persistent_subject: Optional[bool] = None,
    ep_num: Optional[int] = None,
) -> List[Dict[str, str]]:
    """单镜块执行层 lint：返回 findings [{level, code, msg}]。纯函数·可测（不读盘）。

    block/warn 取舍：
    - block：含角色却无参考图块（纯文生图风险）、引用了 registry 里不存在的 CHAR_xx / LOC·PROP·OUTFIT·VFX_xx
    - warn ：角色镜漏 视线方向/锚点句/身份锁定句；用了定妆资产却没绑资产 id
    """
    body = block.get("body", "")
    label = block.get("label", "")
    findings: List[Dict[str, str]] = []

    # 资产 id lint（A）：场景/道具/服装/特效，所有镜都跑（含纯场景/道具空镜），先于角色镜早返回。
    findings.extend(_lint_asset_binding(label, body, asset_index))
    findings.extend(_lint_physical_lens_parameters(label, body))
    findings.extend(_lint_semantic_conflict(label, body))
    findings.extend(_lint_action_eyeline(label, body))
    findings.extend(_lint_camera_gaze_general(label, body))

    id_refs = IDENTITY_REF_RE.findall(body)
    ref_block_present = "参考图" in body and "定妆_" in body
    is_char_shot = _is_character_shot_body(body, id_refs)

    if not is_char_shot:
        return findings  # 空镜/纯场景镜不强求身份字段（但上面的资产 id lint 已对它生效）

    if not ref_block_present:
        findings.append({"level": "block", "code": "no_reference_block",
                         "msg": f"{label}：角色镜缺『参考图』多图派生块（纯文生图风险，跨镜必漂）"})
    # CHAR_xx 合法性（gate 盲区）
    if valid_ids is not None:
        for raw in id_refs:
            rid = normalize_identity_ref(raw)
            if rid not in valid_ids:
                base = rid.split("/")[0]
                hint = "（形态名对不上 registry）" if base in valid_ids else "（registry 无此角色 ID）"
                findings.append({"level": "block", "code": "unknown_char_id",
                                 "msg": f"{label}：身份引用 `{rid}` 在 identity_registry 不存在{hint}"})
    findings.extend(_lint_outfit_form_binding(label, body, id_refs, registry_forms))
    if "视线方向" not in body:
        findings.append({"level": "warn", "code": "no_eyeline",
                         "msg": f"{label}：角色镜缺『视线方向』字段（轴线靠它焊进首帧，出视频救不回）"})
    if "锚点句" not in body:
        findings.append({"level": "warn", "code": "no_anchor_phrase",
                         "msg": f"{label}：缺『锚点句』（锁特征词，比单纯调参考图强度更稳）"})
    if "身份锁定句" not in body:
        findings.append({"level": "warn", "code": "no_identity_lock_phrase",
                         "msg": f"{label}：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）"})
    findings.extend(_lint_identity_marks(label, body, id_refs, registry_forms, ep_num))
    findings.extend(_lint_tail_identity_handoff(label, body, registry_forms))
    findings.extend(_lint_tail_relay_method(label, body))
    findings.extend(_lint_closeup_expression_lib(label, body, id_refs, core_char_ids(registry_forms)))
    findings.extend(_lint_multi_subject_spatial_binding(label, body, id_refs))      # C3
    findings.extend(_lint_native_multiref_coverage(label, body, id_refs, form_ref_counts, persistent_subject))  # C4
    return findings


def lint_prompts(root: Path, ep: str) -> Dict[str, Any]:
    """读 01_分镜出图.md 跑逐镜 lint。缺文件 → 记 note。"""
    res: Dict[str, Any] = {
        "available": True,
        "findings": [],
        "shots_linted": 0,
        "character_shots": [],
        "notes": [],
    }
    path = root / "出图" / ep / "prompt" / "01_分镜出图.md"
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        res["available"] = False
        res["notes"].append(f"无 {path}——出图 prompt 写完后再 lint。")
        return res
    valid_ids = load_registry_ids(root)
    if valid_ids is None:
        res["notes"].append("identity_registry.json 缺失/损坏——跳过 CHAR_xx 合法性校验。")
    registry_forms = load_registry_forms(root)
    if registry_forms is None:
        res["notes"].append("identity_registry.json 缺失/损坏——跳过尾帧身份交接校验。")
    form_ref_counts = registry_ref_counts(registry_forms)  # C4：角色→多角度参考张数
    profile = _backend_identity_profile(root)  # ④ 后端身份能力档（persistent_subject 决定多参考 nudge 口径）
    persistent_subject = bool(profile.get("persistent_subject")) if profile else None
    asset_index = load_asset_index(root)
    if asset_index is None:
        res["notes"].append("asset_registry.json 缺失/损坏——跳过 LOC/PROP/WEAPON/OUTFIT/VFX_xx 资产 id 合法性校验。")
    ep_num = _mk_episode_num(ep)  # 辨识标记获得型 anachronism 判定用
    blocks = split_shot_blocks(text)
    for blk in blocks:
        res["shots_linted"] += 1
        for manifest in character_shot_manifests(blk):
            res["character_shots"].append(manifest)
        res["findings"].extend(lint_shot_block(blk, valid_ids, registry_forms, asset_index,
                                               form_ref_counts, persistent_subject, ep_num))
    return res


# ── 像素机检（复用 n2d-review 纯函数） ──────────────────────────────────────────

def run_pixel_checks(root: Path, ep: str) -> Dict[str, Any]:
    """崩脸 G1 / 发型 H1 / 服装 N1 / 场景 O2 / 接缝接力 / 锚点门 N3，复用 n2d-review analyze。
    每模块独立 try——某项不可用只影响该项，其余照跑。"""
    r = str(root)
    checks: Dict[str, Any] = {}

    fc = _load_review_module("face_consistency")
    if fc is not None:
        try:
            checks["face"] = fc.analyze(r, ep)
        except Exception as exc:
            checks["face"] = {"available": False, "notes": [f"face_consistency.analyze 失败：{exc}"]}
        try:
            checks["anchors"] = fc.audit_anchors(r)
        except Exception as exc:
            checks["anchors"] = {"available": False, "notes": [f"audit_anchors 失败：{exc}"]}
    else:
        checks["face"] = {"available": False, "notes": ["face_consistency 不可用——崩脸机检跳过，交人判。"]}

    hc = _load_review_module("hair_consistency")
    if hc is not None:
        try:
            checks["hair"] = hc.analyze(r, ep)
        except Exception as exc:
            checks["hair"] = {"available": False, "notes": [f"hair_consistency.analyze 失败：{exc}"]}
    else:
        checks["hair"] = {"available": False, "notes": ["hair_consistency 不可用——发型机检跳过。"]}

    oc = _load_review_module("outfit_consistency")
    if oc is not None:
        try:
            checks["outfit"] = oc.analyze(r, ep)
        except Exception as exc:
            checks["outfit"] = {"available": False, "notes": [f"outfit_consistency.analyze 失败：{exc}"]}
    else:
        checks["outfit"] = {"available": False, "notes": ["outfit_consistency 不可用——服装机检跳过。"]}

    sc = _load_review_module("scene_consistency")
    if sc is not None:
        try:
            checks["scene"] = sc.analyze(r, ep)
        except Exception as exc:
            checks["scene"] = {"available": False, "notes": [f"scene_consistency.analyze 失败：{exc}"]}
    else:
        checks["scene"] = {"available": False, "notes": ["scene_consistency 不可用——场景机检跳过。"]}

    # 道具/法宝/特效 P2（B）：按 asset_registry 分组的 RGB+dHash 组内离群，前移到出图落档当初筛项
    # （与 outfit/scene 同级 advisory，不阻断），让道具/特效漂移在出图就被抓，而非等审片。
    mc = _load_review_module("multimodal_consistency")
    if mc is not None:
        try:
            checks["multimodal"] = mc.analyze(r, ep)
        except Exception as exc:
            checks["multimodal"] = {"available": False, "notes": [f"multimodal_consistency.analyze 失败：{exc}"]}
    else:
        checks["multimodal"] = {"available": False, "notes": ["multimodal_consistency 不可用——道具/特效机检跳过。"]}

    tc = _load_review_module("temporal_consistency")
    if tc is not None:
        try:
            checks["seam"] = _normalize_seam_availability(tc.seam_analyze(r, ep), r, ep)
        except Exception as exc:
            checks["seam"] = {"available": False, "notes": [f"temporal_consistency.seam_analyze 失败：{exc}"]}
    else:
        checks["seam"] = {"available": False, "notes": ["temporal_consistency 不可用——接缝机检跳过。"]}

    return checks


def _seam_image_dir_has_pngs(root: str, ep: str) -> bool:
    """seam_analyze 读 出图/<ep>/图片/*.png；目录缺失或无 PNG = 接缝 0 覆盖。"""
    d = Path(root) / "出图" / ep / "图片"
    try:
        return d.is_dir() and any(d.glob("*.png"))
    except OSError:
        return False


def _normalize_seam_availability(res: Dict[str, Any], root: str, ep: str) -> Dict[str, Any]:
    """seam_analyze 在缺/空 图片目录时只回 {"seams":[], "notes":[...]} 无 available 键，
    HARD 路径会把"零覆盖"误判成 ok。这里补 available：有真实 PNG 可比对才 True，否则 False（=未验，走 review）。
    seam_analyze 自己已置 available（如失败/缺依赖）时尊重原值不覆盖。"""
    if not isinstance(res, dict) or res.get("available") is not None:
        return res if isinstance(res, dict) else {"available": False, "notes": ["seam_analyze 返回非 dict——接缝机检跳过。"]}
    res["available"] = _seam_image_dir_has_pngs(root, ep)
    return res


EPISODE_CLIP_IMAGE_RE = re.compile(r"^Clip_?\d{2}_.+\.(?:png|jpg|jpeg|webp)$", re.I)
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _rel_to_episode_image(raw: str, ep: str) -> str:
    text = str(raw or "").strip().strip("`")
    if not text:
        return text
    if text.startswith("出图/"):
        return text
    if "/" in text:
        return text
    return str(Path("出图") / ep / "图片" / text)


def current_episode_prompt_targets(root: Path, ep: str) -> Set[str]:
    """Current `01_分镜出图.md` target PNGs for this episode."""
    prompt = root / "出图" / ep / "prompt" / "01_分镜出图.md"
    try:
        text = prompt.read_text(encoding="utf-8")
    except OSError:
        return set()
    targets: Set[str] = set()
    prefix = f"出图/{ep}/图片/"
    for line in re.findall(r"^\*\*(?:目标|目标落档|本镜出图张数)\*\*：([^\n]+)$", text, re.M):
        for raw in re.findall(r"`([^`]+)`", line):
            rel = _rel_to_episode_image(raw, ep)
            if rel.startswith(prefix) and Path(rel).suffix.lower() in IMAGE_SUFFIXES:
                targets.add(rel)
    return targets


def audit_artifact_namespace(root: Path, ep: str) -> Dict[str, Any]:
    """Block stale Clip PNGs that are not declared by the current image prompt."""
    targets = current_episode_prompt_targets(root, ep)
    prompt = root / "出图" / ep / "prompt" / "01_分镜出图.md"
    image_dir = root / "出图" / ep / "图片"
    out: Dict[str, Any] = {
        "available": bool(targets),
        "prompt": str(prompt),
        "declared_targets": len(targets),
        "stale": [],
        "notes": [],
    }
    if not prompt.is_file():
        out["notes"].append("缺少本集出图 prompt，无法审计图片命名空间。")
        return out
    if not targets:
        out["notes"].append("本集出图 prompt 未声明目标 PNG，跳过图片命名空间审计。")
        return out
    if not image_dir.is_dir():
        out["notes"].append("本集图片目录不存在。")
        return out
    stale: List[Dict[str, Any]] = []
    for path in sorted(image_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        if not EPISODE_CLIP_IMAGE_RE.fullmatch(path.name):
            continue
        rel = str(path.relative_to(root))
        if rel not in targets:
            stale.append({
                "path": rel,
                "reason": "live 图片目录中的 Clip PNG 未被当前 01_分镜出图.md 目标集声明",
            })
    out["stale"] = stale
    return out


# ── 汇总 ───────────────────────────────────────────────────────────────────────

# 落档闸门分级（关键设计）：
# - HARD（必须修才能继续）：高精度、无歧义的硬伤——崩脸、纯文生图、引用了 registry 不存在的 CHAR_id。
# - ADVISORY（非阻断初筛）：像素直方图/dHash 初筛——outfit/scene/seam/锚点门/lint 漏字段。
#   n2d-review 把这几项自己就定位成"机检初筛交人判"（全画面调色板会被跨场景灯光天然触发），
#   一律当硬阻断会让闸门被噪声淹没。它们的 block/warn 照样汇报，只是不强制重抽。
HARD_CHECKS = ("face", "seam")                # 崩脸：insightface 模式高精度，Pillow 模式=图损坏/过小，都该修。
                                              # 接缝：seam_analyze 仅在 _end.png 接力对触发、设计切镜已降 info，
                                              # 故 block=真接力断；断=出视频必跳切，与崩脸同级硬伤前移到落档拦截
HARD_LINT_CODES = (
    "unknown_char_id",
    "no_reference_block",
    "outfit_form_mismatch",
    "tail_identity_handoff_missing_prompt",
    "tail_identity_handoff_unlocked",
    "tail_relay_not_image2image",
    "unknown_asset_id",
    "asset_must_not_have_not_propagated",
    "lifecycle_regression",
    "lifecycle_unknown_from_state",
    "lifecycle_unknown_to_state",
    "no_expression_lib_ref",  # ④ 所有人物近景大表情无表情库/脸部特写 = 脸漂高发，硬拦
    "closeup_core_no_expression_lib",  # 旧报告码兼容；新报告统一用 no_expression_lib_ref
    "weak_face_anchor_core",
    "unanchored_identity_plate",  # 承载角色脸的资产无 ready 脸锚（定妆脸漂真因·后端无关落档版）
    "carried_identity_unknown",   # 承载角色在 identity_registry 不存在——无锚可注入
    "asset_faceless_face_detected",  # faceless 脸策略资产（握持比例/尺度参考）像素核验检出清晰脸=脸漂
    "asset_face_locked_no_owner",    # face_locked 资产无 owner/承载角色可折脸锚——会自画新脸
    "combat_camera_eye_contact",
    "combat_frontal_portrait_bias",
)
VISUAL_CHECK_LABELS = {
    "face": "崩脸 G1",
    "hair": "发型 H1",
    "outfit": "服装 N1",
    "scene": "场景 O2",
    "multimodal": "道具/特效 P2",
    "seam": "接缝接力",
    "anchors": "锚点门 N3",
}
VISUAL_CHECK_DIMS = {
    "face": "character_consistency",
    "hair": "character_consistency",
    "outfit": "outfit_consistency",
    "scene": "scene_consistency",
    "multimodal": "multimodal_continuity",
    "seam": "scene_consistency",
    "anchors": "character_consistency",
}
QC_INSTALL_RECOMMENDATION = (
    "优先用 facefusion conda env："
    "/opt/homebrew/Caskroom/miniforge/base/envs/facefusion/bin/python -m pip install "
    "pillow opencv-python onnxruntime insightface scikit-image；首次跑 FaceAnalysis(name='buffalo_l') "
    "预热/下载模型。若无该 env，用 Python 3.10-3.12 conda env；系统 Python 3.14 不作为重视觉依赖首选。"
)
PROHIBITED_FACE_PATCH_LABEL = "本地贴脸修复产物禁用"
PROHIBITED_FACE_PATCH_STRONG_TOKENS = (
    "local_face_patch",
    "face_patch",
    "face-patch",
    "facepaste",
    "face_paste",
    "face paste",
    "faceswap",
    "face_swap",
    "face-swap",
    "facefix",
    "face_fix",
    "inswapper",
    "facefusion",
    "roop",
)
PROHIBITED_FACE_PATCH_OPERATION_TOKENS = (
    "crop_resize_color_match",
    "alpha_blend",
    "poisson_clone",
    "seamless_clone",
)


def _notes_say_unavailable(res: Mapping[str, Any]) -> bool:
    notes = "；".join(str(n) for n in (res.get("notes") or []))
    return any(word in notes for word in ("不可用", "跳过", "未装", "缺依赖"))


def unavailable_visual_checks(payload: Dict[str, Any]) -> List[str]:
    """Pixel/visual checks that were requested but unavailable.

    These are not hard failures by themselves, but they must make the QC result
    visible as degraded/review instead of silently reporting ok.
    """
    checks = payload.get("checks", {}) or {}
    out: List[str] = []
    for key in VISUAL_CHECK_LABELS:
        res = checks.get(key)
        if isinstance(res, dict) and (res.get("available") is False or _notes_say_unavailable(res)):
            out.append(key)
    return out


# 近景景别标记（与 n2d-video/video_qc.CLOSEUP_MARKERS 同义；本 skill 独立留一份）。
CLOSEUP_MARKERS = ("ECU", "MCU", "BCU", "CU", "OTS", "反打", "特写", "近景", "过肩")
FACE_DEGRADED_MODES = ("pillow_fallback",)


def _lens_is_closeup(lens: str) -> bool:
    s = str(lens or "").upper()
    return any(m.upper() in s for m in CLOSEUP_MARKERS)


def closeup_shot_nums(root: Path, ep: str) -> set:
    """storyboard.json 里近景/特写/反打镜号集合（驱动「降级精度近景铁律」）。读不到→空集（不臆造近景）。"""
    out: set = set()
    try:
        data = json.loads((Path(root) / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
    except Exception:
        return out
    for clip in (data.get("clips") or data.get("shots") or []):
        if not isinstance(clip, dict):
            continue
        m = _REGEN_CLIP_RE.search(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if not m:
            continue
        lenses = " ".join(str((s or {}).get("lens", "")) for s in (clip.get("shots") or []))
        if _lens_is_closeup(lenses):
            out.add(int(m.group(1)))
    return out


def multi_person_shot_nums(root: Path, ep: str) -> set:
    """storyboard.json 里同框 ≥2 具名角色的镜号集合（驱动「降级精度多人同框铁律」A）。

    降级精度下 detect_face_swaps（多人串脸检测）整组失效——次要角色脸无人核验。读不到→空集。"""
    out: set = set()
    try:
        data = json.loads((Path(root) / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
    except Exception:
        return out
    for clip in (data.get("clips") or data.get("shots") or []):
        if not isinstance(clip, dict):
            continue
        m = _REGEN_CLIP_RE.search(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if not m:
            continue
        cids = {str(c) for c in (clip.get("character_ids") or []) if c}
        if len(cids) >= 2:
            out.add(int(m.group(1)))
    return out


def annotate_degraded_closeups(payload: Dict[str, Any], root: Path, ep: str) -> None:
    """降级精度近景/多人同框铁律：insightface 缺席时崩脸机检降到 Pillow（只验图损坏/分辨率，不验真脸相似度）。
    ① 近景/特写/反打镜在降级下放行 = 脸是否同人无人核验；② 多人同框在降级下 detect_face_swaps 整组失效=
    次要角色脸无人核验。给这两类 face shot 打 `degraded_face` + `closeup`/`multi_person`，
    summarize / to_findings 据此升为 hard block（普通单人景别仍只 review，不误杀远景）。"""
    face = (payload.get("checks") or {}).get("face") or {}
    if face.get("mode") not in FACE_DEGRADED_MODES:
        return
    closeups = closeup_shot_nums(root, ep)
    multi = multi_person_shot_nums(root, ep)
    for s in face.get("shots", []):
        m = _REGEN_CLIP_RE.search(str(s.get("png") or ""))
        idx = int(m.group(1)) if m else None
        s["degraded_face"] = True
        s["closeup"] = bool(idx is not None and idx in closeups)
        s["multi_person"] = bool(idx is not None and idx in multi)


def _degraded_closeup_face_shots(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """降级精度下、景别为近景、且基础质量未单独 block 的 face shot（这些是「无法验同人的近景脸」）。"""
    face = (payload.get("checks") or {}).get("face") or {}
    return [s for s in face.get("shots", [])
            if s.get("degraded_face") and s.get("closeup") and s.get("verdict") != "block"]


def _degraded_multi_person_face_shots(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """降级精度下、多人同框、非近景（近景已被 closeup 规则覆盖，避免重复计）、且未单独 block 的 face shot。

    这些是 A 补的洞：双人/多人中景在降级精度下既不触发近景铁律、又没 embedding 做串脸检测，
    次要角色脸完全无验证。比照近景处理：不 auto-pass，升 hard、落人审队列。"""
    face = (payload.get("checks") or {}).get("face") or {}
    return [s for s in face.get("shots", [])
            if s.get("degraded_face") and s.get("multi_person") and not s.get("closeup")
            and s.get("verdict") != "block"]


def _degraded_unverifiable_face_shots(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """降级精度下无法验同人的 face shot 合集（近景 ∪ 多人同框），供人审队列用。"""
    return _degraded_closeup_face_shots(payload) + _degraded_multi_person_face_shots(payload)


# ── 状态账本启发式（advisory）：把「这剧状态简不简单、要不要强制 visual_state_ledger」从人脑
#    豁免决策挪成机检提醒。累积状态(伤口/流血/泪痕/脏污/破损/升级…)出现却无账本 → info 级提示，
#    永不进 summarize 的 hard/advisory、永不翻 verdict。去掉裸「伤/血」避免悲伤/热血等情绪词误报。──
CUMULATIVE_STATE_MARKERS = (
    "伤口", "受伤", "流血", "血迹", "血污", "染血", "淤青", "泪痕", "脏污", "污渍",
    "破损", "撕裂", "裂痕", "烧痕", "灼伤", "绷带", "包扎", "升级", "进化", "觉醒", "消耗",
)


def _ledger_present(root: Path) -> bool:
    """visual_state_ledger.json 是否已建（复用 visual_state_manager 的路径约定，缺则直接拼路径）。"""
    vsm = _load_sibling("visual_state_manager")
    if vsm is not None and hasattr(vsm, "get_ledger_path"):
        try:
            return os.path.exists(vsm.get_ledger_path(root))
        except Exception:
            pass
    return (Path(root) / "出图" / "共享" / "visual_state_ledger.json").exists()


# ── B 定妆库两层：中性锚（锁身份·平光纯背景）/ 风格氛围（锁调性·戏剧光）。脸锚若用戏剧光板，
#    会把光当身份烤进脸——业界做定妆铁律是平光中性背景。这里把它做成可机检的 advisory。 ──
_DRAMATIC_LIGHT_TOKENS = (
    "氛围", "暗调", "戏剧光", "烛光", "逆光", "侧逆", "夜景", "暗光", "低调光", "霓虹", "顶光",
    "candle", "backlit", "backlight", "moody", "dramatic", "lowkey", "low_key", "rim",
)


def reference_layer(entry: Any) -> str:
    """把一条参考登记归类为 'identity'(中性锚) / 'atmosphere'(风格氛围) / ''(未知)。

    显式 `layer` / `lighting` 标签优先；否则按文件名里的戏剧光关键词启发。纯函数·可测。"""
    path = ""
    if isinstance(entry, Mapping):
        lay = str(entry.get("layer") or "").strip().lower()
        if lay in {"atmosphere", "style", "氛围", "风格"}:
            return "atmosphere"
        if lay in {"identity", "anchor", "identity_anchor", "中性", "锚", "中性锚"}:
            return "identity"
        lit = str(entry.get("lighting") or "").strip().lower()
        if lit in {"dramatic", "moody", "low_key", "lowkey", "戏剧光", "暗调"}:
            return "atmosphere"
        if lit in {"neutral", "flat", "even", "中性", "平光"}:
            return "identity"
        path = str(entry.get("path") or "")
    else:
        path = str(entry or "")
    name = Path(path).stem.lower()
    if any(tok.lower() in name for tok in _DRAMATIC_LIGHT_TOKENS):
        return "atmosphere"
    return ""


def face_anchor_lighting_audit(root: Path, ep: str) -> Dict[str, Any]:
    """脸锚两层体检：identity_registry 各 form 的 face_anchor_refs 若是戏剧光/氛围板 → flag。

    脸锚应是中性平光板（锁身份）；戏剧光板留作 atmosphere 层锁调性，不可当身份锚。advisory·纯路径。"""
    res: Dict[str, Any] = {"available": False, "flagged": []}
    try:
        reg = json.loads((Path(root) / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    except Exception:
        return res
    res["available"] = True
    for ch in reg.get("characters") or []:
        if not isinstance(ch, Mapping):
            continue
        cid = str(ch.get("id") or "")
        for form in ch.get("forms") or []:
            if not isinstance(form, Mapping):
                continue
            fname = str(form.get("form") or "")
            rg = form.get("reference_group") or {}
            atlas = form.get("reference_atlas") or {}
            anchors = []
            for src in (rg.get("face_anchor_refs"), atlas.get("face_anchor_refs")):
                if isinstance(src, list):
                    anchors.extend(src)
            for entry in anchors:
                if reference_layer(entry) == "atmosphere":
                    p = entry.get("path") if isinstance(entry, Mapping) else entry
                    res["flagged"].append({"char": cid, "form": fname, "path": str(p or "")})
    return res


def audit_state_ledger(root: Path, ep: str) -> Dict[str, Any]:
    """状态账本启发式（advisory）：扫 storyboard 角色状态演进 + 本集出图 prompt 找累积状态关键词；
    命中且无 visual_state_ledger.json → advise=True（建议跑 visual_state_manager --audit）。
    永不 block——只把「简单/复杂」的人脑豁免决策挪到机检提醒。读不到源 → available=False。纯函数·可测。"""
    res: Dict[str, Any] = {"available": False, "markers": [], "ledger_present": False,
                           "advise": False, "not_injected_markers": []}
    sb_text = ""
    prompt_text = ""
    try:
        sb = json.loads((Path(root) / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
        vc = sb.get("visual_contract") if isinstance(sb.get("visual_contract"), dict) else {}
        sb_text = str(vc.get("角色状态演进", ""))
        res["available"] = True
    except Exception:
        pass
    try:
        prompt_text = (Path(root) / "出图" / ep / "prompt" / "01_分镜出图.md").read_text(encoding="utf-8")
        res["available"] = True
    except Exception:
        pass
    if not res["available"]:
        return res
    blob = f"{sb_text}\n{prompt_text}"
    res["markers"] = sorted({m for m in CUMULATIVE_STATE_MARKERS if m in blob})
    # 状态演进声明了累积状态，但本集出图 prompt 没注入 = 账本/演进写了却没进生成（runner 照画干净衣服）。
    sb_markers = {m for m in CUMULATIVE_STATE_MARKERS if m in sb_text}
    prompt_markers = {m for m in CUMULATIVE_STATE_MARKERS if m in prompt_text}
    res["not_injected_markers"] = sorted(sb_markers - prompt_markers)
    res["ledger_present"] = _ledger_present(root)
    # advise：① 有累积状态却没建账本；② 状态演进声明了累积状态，但出图 prompt 没注入（视觉状态漏进生成）。
    res["advise"] = (bool(res["markers"]) and not res["ledger_present"]) or bool(res["not_injected_markers"])
    return res


# ── ① 降级近景人审队列：拼『定妆主参考 ↔ 本镜脸』并排图，让人眼在 degraded 精度下秒判同人 ──

def face_review_targets(payload: Dict[str, Any], root: Path, ep: str) -> List[Dict[str, Any]]:
    """降级近景脸 → 人审拼图目标（纯路径计算，不写盘·可测）。

    每项 {shot, png, png_abs, char, ref, stitch}：ref=该角色定妆主参考，stitch=并排图落点。
    """
    out: List[Dict[str, Any]] = []
    for s in _degraded_unverifiable_face_shots(payload):
        png = s.get("png")
        chars = s.get("chars") or []
        char = chars[0] if chars else None
        key = _shot_key(png) or "shot"
        ref = str(Path("出图") / "共享" / "图片" / f"定妆_{char}.png") if char else None
        png_abs = str(Path(root) / "出图" / ep / png) if png else None
        stitch = str(production_dir(Path(root)) / "image_qc" / ep / "face_review" / f"{key}_compare.png")
        out.append({"shot": key, "png": png, "png_abs": png_abs, "char": char, "ref": ref, "stitch": stitch})
    return out


def build_face_review_queue(payload: Dict[str, Any], root: Path, ep: str) -> List[Dict[str, Any]]:
    """为降级近景脸生成并排对比图 + Haar 几何粗筛，写 payload['face_human_review']。best-effort，never crash。"""
    targets = face_review_targets(payload, root, ep)
    if not targets:
        payload["face_human_review"] = []
        return []
    stitch_mod = _load_review_module("face_compare_stitch")
    face_mod = _load_review_module("face_consistency")
    for t in targets:
        # 几何粗筛：Haar 人脸数（仅作人审优先级，不下 verdict；漫剧脸漏检率高，None=没检测能力）。
        t["haar_faces"] = None
        if face_mod is not None and hasattr(face_mod, "cv2_face_boxes") and t.get("png_abs"):
            try:
                boxes = face_mod.cv2_face_boxes(t["png_abs"])
                t["haar_faces"] = None if boxes is None else len(boxes)
            except Exception:
                t["haar_faces"] = None
        if t["haar_faces"] == 0:
            t["priority_note"] = "Haar 未检出人脸——疑崩脸/遮挡，优先人审"
        elif isinstance(t["haar_faces"], int) and t["haar_faces"] >= 2:
            t["priority_note"] = f"Haar 检出 {t['haar_faces']} 张脸——疑串入他人，优先人审"
        # 并排对比图（degraded 精度下人眼判同人的唯一可靠兜底）。
        t["stitched"] = False
        if stitch_mod is not None and t.get("ref") and t.get("png_abs"):
            ref_abs = os.path.join(str(root), t["ref"])
            try:
                t["stitched"] = bool(stitch_mod.build_comparison(
                    [(f"参考·定妆_{t['char']}", ref_abs), (f"本镜·{t['shot']}", t["png_abs"])],
                    t["stitch"]))
            except Exception:
                t["stitched"] = False
    payload["face_human_review"] = targets
    return targets


# ── D 漂移人审拼图扩展：场景 O2 / 道具·特效 P2 漂移也拼「资产参考 ↔ 本镜」并排图 ──────────

def _asset_primary_map(root: Path) -> Dict[str, str]:
    """asset_registry.json → {id / name / 定妆stem: reference_group.primary 相对路径}，给漂移人审找参考面板。"""
    out: Dict[str, str] = {}
    try:
        data = json.loads((Path(root) / "出图" / "共享" / "asset_registry.json").read_text(encoding="utf-8"))
    except Exception:
        return out
    for a in (data.get("assets") or []):
        rg = a.get("reference_group") or {}
        primary = ""
        if isinstance(rg, Mapping):
            raw = rg.get("primary") or rg.get("main") or rg.get("front")
            if isinstance(raw, Mapping):
                primary = str(raw.get("path") or "").strip()
            else:
                primary = str(raw or "").strip()
        elif isinstance(rg, list):
            for item in rg:
                if isinstance(item, Mapping):
                    status = str(item.get("status") or "").strip().lower()
                    candidate = str(item.get("path") or "").strip()
                    if candidate and (not status or status in {"ready", "accepted", "ok", "pass"}):
                        primary = candidate
                        break
                elif isinstance(item, str) and item.strip():
                    primary = item.strip()
                    break
        if not primary:
            continue
        aid = str(a.get("id") or "").strip()
        name = str(a.get("name") or "").strip()
        stem = Path(primary).stem
        if stem.startswith("定妆_"):
            stem = stem[len("定妆_"):]
        for k in (aid, name, stem):
            if len(k) >= 2:
                out.setdefault(k, primary)
    return out


def _resolve_asset_ref(root: Path, primary_map: Dict[str, str], hint: str) -> Optional[str]:
    """资产名/id/group → 参考图相对路径。先查 asset_registry primary，再兜底 出图/共享/图片/定妆_<hint>.png。"""
    h = str(hint or "").strip()
    if h.endswith(".png"):
        h = h[:-4]
    if not h:
        return None
    if h in primary_map:
        return primary_map[h]
    cand = Path("出图") / "共享" / "图片" / f"定妆_{h}.png"
    if (Path(root) / cand).exists():
        return str(cand)
    return primary_map.get(h)


def asset_review_targets(payload: Dict[str, Any], root: Path, ep: str,
                         primary_map: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """场景 O2 / 道具·特效 P2 报漂移(block/warn)的镜 → 人审拼图目标（纯路径计算·可测）。

    每项 {kind, asset, shot, png, png_abs, ref, stitch}。primary_map 缺时用 {}（ref 走兜底解析）。
    """
    pm = primary_map if primary_map is not None else {}
    checks = payload.get("checks", {}) or {}
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def _add(kind: str, png: Optional[str], hint: str) -> None:
        if not png:
            return
        key = (_shot_key(png) or "shot")
        uid = f"{kind}:{key}:{png}"
        if uid in seen:
            return
        seen.add(uid)
        ref = _resolve_asset_ref(Path(root), pm, hint)
        png_abs = str(Path(root) / "出图" / ep / png)
        stitch = str(production_dir(Path(root)) / "image_qc" / ep / "asset_review" / f"{kind}_{key}_compare.png")
        out.append({"kind": kind, "asset": hint, "shot": key, "png": png, "png_abs": png_abs,
                    "ref": ref, "stitch": stitch})

    for s in (checks.get("scene") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            _add("scene", s.get("png"), str(s.get("scene") or s.get("group") or ""))
    for s in (checks.get("multimodal") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            _add("asset", s.get("png"), str(s.get("asset") or s.get("group") or s.get("scene") or ""))
    return out


def build_asset_review_queue(payload: Dict[str, Any], root: Path, ep: str) -> List[Dict[str, Any]]:
    """为 场景/道具/特效 漂移镜生成「资产参考 ↔ 本镜」并排图（D）。best-effort，never crash。"""
    targets = asset_review_targets(payload, root, ep, _asset_primary_map(root))
    if not targets:
        payload["asset_human_review"] = []
        return []
    stitch_mod = _load_review_module("face_compare_stitch")  # 通用拼图模块，不限脸
    label = {"scene": "场景", "asset": "道具/特效"}
    for t in targets:
        t["stitched"] = False
        if stitch_mod is not None and t.get("ref") and t.get("png_abs"):
            ref_abs = os.path.join(str(root), t["ref"])
            try:
                t["stitched"] = bool(stitch_mod.build_comparison(
                    [(f"参考·{t.get('asset') or t['kind']}", ref_abs),
                     (f"本镜·{t['shot']}", t["png_abs"])],
                    t["stitch"]))
            except Exception:
                t["stitched"] = False
    payload["asset_human_review"] = targets
    return targets


def _prop_shape_confirmation_path(root: Path, ep: str) -> Path:
    return production_dir(root) / "image_qc" / ep / "prop_shape_confirmations.json"


def _face_confirmation_path(root: Path, ep: str) -> Path:
    return production_dir(root) / "image_qc" / ep / "face_confirmations.json"


def _prop_shape_png_path(root: Path, ep: str, png: str) -> Path:
    p = Path(str(png))
    if p.is_absolute():
        return p
    s = p.as_posix()
    if s.startswith("出图/"):
        return root / p
    return root / "出图" / ep / p


def _episode_png_sha(root: Path, ep: str, png: Any) -> Optional[str]:
    png_s = str(png or "").strip()
    if not png_s:
        return None
    return _sha256_file(_prop_shape_png_path(root, ep, png_s))


def _prop_shape_png_sha(root: Path, ep: str, png: Any) -> Optional[str]:
    return _episode_png_sha(root, ep, png)


def load_prop_shape_confirmations(root: Path, ep: str) -> Set[Tuple[str, str]]:
    """读高风险道具禁形逐图人工确认。

    文件格式（人工/agent 复核后可写）：
      {"confirmations": [{"asset": "PROP_01", "png": "图片/Clip_01_x.png", "verdict": "ok", "png_sha256": "..."}]}

    只接受 verdict=ok/pass/confirmed/通过/合格，且 png_sha256 必须匹配当前 PNG。
    这样同名 PNG 重出后旧确认会自动失效；缺文件 = 空集。
    """
    path = _prop_shape_confirmation_path(root, ep)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    rows = data.get("confirmations") if isinstance(data, Mapping) else None
    if rows is None and isinstance(data, list):
        rows = data
    out: Set[Tuple[str, str]] = set()
    ok_values = {"ok", "pass", "confirmed", "true", "yes", "通过", "合格", "确认"}
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        asset = str(row.get("asset") or row.get("id") or "").strip()
        png = str(row.get("png") or row.get("image") or "").strip()
        verdict = str(row.get("verdict") or row.get("status") or "").strip().lower()
        row_sha = str(row.get("png_sha256") or row.get("png_sha") or row.get("sha256") or "").strip()
        current_sha = _prop_shape_png_sha(root, ep, png)
        if asset and png and verdict in ok_values and row_sha and current_sha and row_sha == current_sha:
            out.add((asset, png))
    return out


def _clip_pngs_on_disk(root: Path, ep: str, shot: Optional[str], fallback: Optional[str] = None) -> List[str]:
    """返回某 Clip 已落档 PNG（相对 出图/<ep>），用于道具逐图复核。"""
    img_dir = root / "出图" / ep / "图片"
    out: List[str] = []
    if shot and img_dir.is_dir():
        for p in sorted(img_dir.glob(f"{shot}*.png")):
            out.append((Path("图片") / p.name).as_posix())
    if not out and fallback:
        f = str(fallback)
        if f.startswith(f"出图/{ep}/"):
            f = f[len(f"出图/{ep}/"):]
        elif f.startswith("出图/"):
            parts = Path(f).parts
            if len(parts) >= 4:
                f = str(Path(*parts[2:]))
        if _prop_shape_png_path(root, ep, f).is_file():
            out.append(f)
    return sorted(dict.fromkeys(out))


def prop_shape_review_targets(root: Path, ep: str,
                              asset_index: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """高风险道具（PROP + must_not_have）逐图禁形/尺寸复核目标。

    文字/registry 只能防止继续把“壶嘴”写进 prompt，不能证明既有 PNG 没长出禁形。
    同理，scale 约束只能说明设计尺寸，不能证明既有 PNG 没被画成大酒坛/大罐。
    因此凡镜头引用了带 must_not_have 的 PROP，并且对应 PNG 已存在，就进入硬复核队列；
    只有确认文件里逐图标 ok 才代表禁形和尺寸都人工/视觉模型确认通过。
    """
    idx = asset_index if asset_index is not None else load_asset_index(root)
    if not idx:
        return []
    entries: Dict[str, Dict[str, Any]] = idx.get("entries") or {}
    try:
        text = (root / "出图" / ep / "prompt" / "01_分镜出图.md").read_text(encoding="utf-8")
    except Exception:
        return []
    confirmations = load_prop_shape_confirmations(root, ep)
    pm = _asset_primary_map(root)
    out: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    for blk in split_shot_blocks(text):
        body = str(blk.get("body") or "")
        label = str(blk.get("label") or "")
        shot = _shot_key(label)
        fallback_png = _extract_target_png(body)
        for aid in sorted(set(ASSET_ID_RE.findall(body))):
            entry = entries.get(aid) or {}
            if str(entry.get("type") or "").strip().lower() != "prop":
                continue
            must_not = [str(t).strip() for t in (entry.get("must_not_have") or []) if str(t).strip()]
            if not must_not:
                continue
            ref = _resolve_asset_ref(root, pm, aid) or _resolve_asset_ref(root, pm, str(entry.get("name") or ""))
            for png in _clip_pngs_on_disk(root, ep, shot, fallback_png):
                key = (aid, png)
                if key in seen:
                    continue
                seen.add(key)
                confirmed = key in confirmations
                out.append({
                    "asset": aid,
                    "asset_name": entry.get("name") or aid,
                    "shot": shot or _shot_key(png) or label,
                    "label": label,
                    "png": png,
                    "png_abs": str(root / "出图" / ep / png),
                    "ref": ref,
                    "must_not_have": must_not,
                    "scale": entry.get("scale") or "",
                    "confirmed": confirmed,
                    "confirmation_path": str(_prop_shape_confirmation_path(root, ep)),
                    "reason": "registered_prop_must_not_have",
                })
    return out


def build_prop_shape_review_queue(payload: Dict[str, Any], root: Path, ep: str) -> List[Dict[str, Any]]:
    """为高风险道具禁形/尺寸生成逐图复核队列 + 参考并排图。best-effort，never crash。"""
    targets = prop_shape_review_targets(root, ep, load_asset_index(root))
    stitch_mod = _load_review_module("face_compare_stitch")
    for t in targets:
        t["stitched"] = False
        if stitch_mod is not None and t.get("ref") and t.get("png_abs"):
            ref_abs = os.path.join(str(root), str(t["ref"]))
            try:
                t["stitch"] = str(production_dir(root) / "image_qc" / ep / "prop_shape_review" /
                                  f"{t.get('asset')}_{t.get('shot')}_{Path(str(t.get('png'))).stem}_compare.png")
                t["stitched"] = bool(stitch_mod.build_comparison(
                    [(f"参考·{t.get('asset_name') or t.get('asset')}", ref_abs),
                     (f"本镜·{t.get('shot')}", t["png_abs"])],
                    t["stitch"]))
            except Exception:
                t["stitched"] = False
    pending = [t for t in targets if not t.get("confirmed")]
    payload["prop_shape_review"] = {
        "available": True,
        "confirmation_path": str(_prop_shape_confirmation_path(root, ep)),
        "total": len(targets),
        "pending": len(pending),
        "confirmed": len(targets) - len(pending),
        "targets": targets,
    }
    return targets


def _prop_shape_target_id(target: Mapping[str, Any]) -> str:
    return f"{target.get('asset')}::{target.get('png')}"


def _load_prop_shape_confirmation_doc(root: Path, ep: str) -> Dict[str, Any]:
    path = _prop_shape_confirmation_path(root, ep)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    if isinstance(data, list):
        data = {"confirmations": data}
    if not isinstance(data, dict):
        data = {}
    rows = data.get("confirmations")
    if not isinstance(rows, list):
        rows = []
    data["kind"] = data.get("kind") or "n2d_prop_shape_confirmations"
    data["version"] = data.get("version") or 1
    data["confirmations"] = rows
    return data


def _save_prop_shape_confirmation_doc(root: Path, ep: str, data: Mapping[str, Any]) -> Path:
    path = _prop_shape_confirmation_path(root, ep)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = dict(data)
    out["updated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _upsert_prop_shape_rows(root: Path, ep: str, rows: Sequence[Mapping[str, Any]],
                            *, overwrite: bool = True) -> Dict[str, Any]:
    data = _load_prop_shape_confirmation_doc(root, ep)
    existing: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in data.get("confirmations") or []:
        if not isinstance(row, Mapping):
            continue
        key = (str(row.get("asset") or row.get("id") or "").strip(),
               str(row.get("png") or row.get("image") or "").strip())
        if key[0] and key[1]:
            existing[key] = dict(row)
    changed = 0
    for row in rows:
        asset = str(row.get("asset") or row.get("id") or "").strip()
        png = str(row.get("png") or row.get("image") or "").strip()
        if not asset or not png:
            continue
        key = (asset, png)
        if key in existing and not overwrite:
            continue
        new_row = dict(existing.get(key, {}))
        new_row.update({k: v for k, v in row.items() if v is not None})
        new_row["asset"] = asset
        new_row["png"] = png
        existing[key] = new_row
        changed += 1
    data["confirmations"] = sorted(existing.values(), key=lambda r: (str(r.get("asset")), str(r.get("png"))))
    path = _save_prop_shape_confirmation_doc(root, ep, data)
    return {"ok": True, "path": str(path), "changed": changed, "total": len(data["confirmations"])}


def prop_shape_review_report(root: Path, ep: str, *, build_stitches: bool = True) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if build_stitches:
        build_prop_shape_review_queue(payload, root, ep)
        review = payload.get("prop_shape_review") or {}
        targets = review.get("targets") or []
        confirmation_path = review.get("confirmation_path") or str(_prop_shape_confirmation_path(root, ep))
    else:
        targets = prop_shape_review_targets(root, ep, load_asset_index(root))
        confirmation_path = str(_prop_shape_confirmation_path(root, ep))
    pending = [t for t in targets if not t.get("confirmed")]
    rerun_shots = sorted({str(t.get("shot") or "").strip() for t in pending if str(t.get("shot") or "").strip()})
    return {
        "kind": "n2d_prop_shape_review",
        "version": 1,
        "episode": ep,
        "confirmation_path": confirmation_path,
        "total": len(targets),
        "pending": len(pending),
        "confirmed": len(targets) - len(pending),
        "targets": targets,
        "rerun_plan": {
            "stage": "image",
            "affected_shots": rerun_shots,
            "command": " ".join(f"--affected-shot {s}" for s in rerun_shots),
            "scope": "高风险道具禁形/尺寸未确认，需确认或重出受影响镜头",
        },
    }


def write_prop_shape_skeleton(root: Path, ep: str, *, include_confirmed: bool = False) -> Dict[str, Any]:
    report = prop_shape_review_report(root, ep, build_stitches=True)
    rows: List[Dict[str, Any]] = []
    for t in report.get("targets") or []:
        if t.get("confirmed") and not include_confirmed:
            continue
        rows.append({
            "asset": t.get("asset"),
            "asset_name": t.get("asset_name"),
            "png": t.get("png"),
            "png_sha256": _prop_shape_png_sha(root, ep, t.get("png")),
            "shot": t.get("shot"),
            "verdict": "review",
            "source": "image_qc:prop_shape_skeleton",
            "reason": "待人工或 VLM 确认：禁形/尺寸是否符合 asset_registry",
            "must_not_have": t.get("must_not_have") or [],
            "scale": t.get("scale") or "",
            "stitch": t.get("stitch") or "",
        })
    res = _upsert_prop_shape_rows(root, ep, rows, overwrite=False)
    res["report"] = report
    return res


def confirm_prop_shape_targets(root: Path, ep: str, selector: str,
                               *, reviewer: str = "manual", reason: str = "") -> Dict[str, Any]:
    report = prop_shape_review_report(root, ep, build_stitches=True)
    selector = str(selector or "").strip()
    targets = report.get("targets") or []
    if selector.lower() in {"all", "*", "pending"}:
        chosen = [t for t in targets if not t.get("confirmed")]
    else:
        wanted = {s.strip() for s in re.split(r"[,;]", selector) if s.strip()}
        chosen = [
            t for t in targets
            if str(t.get("asset")) in wanted
            or str(t.get("png")) in wanted
            or str(t.get("shot")) in wanted
            or _prop_shape_target_id(t) in wanted
        ]
    rows: List[Dict[str, Any]] = []
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    for t in chosen:
        rows.append({
            "asset": t.get("asset"),
            "asset_name": t.get("asset_name"),
            "png": t.get("png"),
            "png_sha256": _prop_shape_png_sha(root, ep, t.get("png")),
            "shot": t.get("shot"),
            "verdict": "ok",
            "reviewer": reviewer,
            "source": "image_qc:manual_prop_shape_confirm",
            "confirmed_at": now,
            "reason": reason or "人工确认无禁形且尺寸符合设定",
            "must_not_have": t.get("must_not_have") or [],
            "scale": t.get("scale") or "",
            "stitch": t.get("stitch") or "",
        })
    res = _upsert_prop_shape_rows(root, ep, rows, overwrite=True)
    res.update({"selected": len(chosen), "pending_before": report.get("pending", 0)})
    return res


def _prop_shape_vlm_prompt(target: Mapping[str, Any]) -> str:
    must_not = "、".join(str(x) for x in (target.get("must_not_have") or []) if str(x).strip())
    scale = str(target.get("scale") or "").strip()
    asset = str(target.get("asset_name") or target.get("asset") or "关键道具")
    return (
        f"{asset} 是关键剧情道具。请判定图中该道具是否满足设定："
        f"不得出现以下禁形：{must_not or '无'}。"
        f"{'尺寸/比例要求：' + scale + '。' if scale else ''}"
        "如果看不清该道具、存在任一禁形、或尺寸明显不符，match=false；"
        "只有清晰可见且无禁形并符合尺寸时 match=true。"
    )


def vlm_confirm_prop_shape_targets(root: Path, ep: str, *,
                                   block_floor: float = 0.6,
                                   reviewer: str = "vlm") -> Dict[str, Any]:
    vv = _load_sibling("vlm_verify")
    if vv is None or not hasattr(vv, "load_judge"):
        return {"ok": False, "available": False, "reason": "vlm_verify 不可用"}
    judge = vv.load_judge()
    if judge is None:
        return {"ok": False, "available": False, "reason": "未配置 N2D_VLM_CMD"}
    report = prop_shape_review_report(root, ep, build_stitches=True)
    rows: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    reviewed = 0
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    for t in report.get("targets") or []:
        if t.get("confirmed"):
            continue
        image = str(t.get("png_abs") or "")
        if not image or not os.path.isfile(image):
            continue
        prompt = _prop_shape_vlm_prompt(t)
        try:
            verdict = vv.parse_verdict(judge(image, prompt, "asset"))
        except Exception:
            verdict = None
        if verdict is None:
            continue
        reviewed += 1
        conf = float(verdict.get("confidence") or 0.0)
        if verdict.get("match") and conf >= block_floor:
            rows.append({
                "asset": t.get("asset"),
                "asset_name": t.get("asset_name"),
                "png": t.get("png"),
                "png_sha256": _prop_shape_png_sha(root, ep, t.get("png")),
                "shot": t.get("shot"),
                "verdict": "ok",
                "reviewer": reviewer,
                "source": "image_qc:vlm_prop_shape_confirm",
                "confirmed_at": now,
                "confidence": conf,
                "reason": verdict.get("reason") or "VLM 高置信确认无禁形且尺寸符合设定",
                "must_not_have": t.get("must_not_have") or [],
                "scale": t.get("scale") or "",
                "stitch": t.get("stitch") or "",
            })
        else:
            rejected.append({
                "asset": t.get("asset"),
                "png": t.get("png"),
                "shot": t.get("shot"),
                "confidence": conf,
                "mismatches": verdict.get("mismatches") or [],
                "reason": verdict.get("reason") or "",
            })
    res = _upsert_prop_shape_rows(root, ep, rows, overwrite=True)
    res.update({
        "available": True,
        "reviewed": reviewed,
        "confirmed": len(rows),
        "rejected_or_review": rejected,
        "block_floor": block_floor,
    })
    return res


def _load_face_confirmation_doc(root: Path, ep: str) -> Dict[str, Any]:
    path = _face_confirmation_path(root, ep)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    if isinstance(data, list):
        data = {"confirmations": data}
    if not isinstance(data, dict):
        data = {}
    rows = data.get("confirmations")
    if not isinstance(rows, list):
        rows = []
    data["kind"] = data.get("kind") or "n2d_face_confirmations"
    data["version"] = data.get("version") or 1
    data["confirmations"] = rows
    return data


def _save_face_confirmation_doc(root: Path, ep: str, data: Mapping[str, Any]) -> Path:
    path = _face_confirmation_path(root, ep)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = dict(data)
    out["updated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _face_confirmation_key(char: Any, png: Any) -> Tuple[str, str]:
    return (str(char or "").strip(), _coverage_png_key(png))


def load_face_confirmations(root: Path, ep: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """读逐图脸部人工确认。

    只接受 verdict=ok/pass/confirmed/通过/合格，且 png_sha256 必须匹配当前 PNG。
    同名 PNG 一旦重出，旧确认自动失效。
    """
    data = _load_face_confirmation_doc(root, ep)
    ok_values = {"ok", "pass", "confirmed", "true", "yes", "通过", "合格", "确认"}
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in data.get("confirmations") or []:
        if not isinstance(row, Mapping):
            continue
        char = str(row.get("char") or row.get("character") or row.get("id") or "").strip()
        png = _coverage_png_key(row.get("png") or row.get("image"))
        verdict = str(row.get("verdict") or row.get("status") or "").strip().lower()
        row_sha = str(row.get("png_sha256") or row.get("png_sha") or row.get("sha256") or "").strip()
        current_sha = _episode_png_sha(root, ep, png)
        if char and png and verdict in ok_values and row_sha and current_sha and row_sha == current_sha:
            out[(char, png)] = dict(row)
    return out


def apply_face_confirmations(payload: Dict[str, Any], root: Path, ep: str) -> Dict[str, Any]:
    """把已审通过的 face warn/block 行改为 ok，并保留原判定字段供审计。"""
    confirmations = load_face_confirmations(root, ep)
    rows = ((payload.get("checks") or {}).get("face") or {}).get("shots") or []
    applied: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        original_verdict = str(row.get("verdict") or "")
        if original_verdict not in {"block", "warn"}:
            continue
        char = str(row.get("char") or "").strip()
        png = _coverage_png_key(row.get("png"))
        confirm = confirmations.get((char, png))
        if not confirm:
            continue
        row["manual_confirmed"] = True
        row["manual_original_verdict"] = original_verdict
        row["manual_confirmation_path"] = str(_face_confirmation_path(root, ep))
        row["manual_reason"] = confirm.get("reason") or ""
        row["manual_reviewer"] = confirm.get("reviewer") or ""
        row["manual_confirmed_at"] = confirm.get("confirmed_at") or confirm.get("updated_at") or ""
        row["verdict"] = "ok"
        applied.append({
            "char": char,
            "png": png,
            "original_verdict": original_verdict,
            "score": row.get("score"),
            "reviewer": row.get("manual_reviewer"),
            "reason": row.get("manual_reason"),
        })
    payload["face_manual_confirmations"] = {
        "available": True,
        "confirmation_path": str(_face_confirmation_path(root, ep)),
        "configured": len(confirmations),
        "applied": len(applied),
        "rows": applied,
    }
    return payload["face_manual_confirmations"]


def _load_latest_qc_payload(root: Path, ep: str) -> Dict[str, Any]:
    path = production_dir(root) / "image_qc" / ep / f"image_qc_{ep}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def face_confirmation_targets(root: Path, ep: str,
                              payload: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """当前 face warn/block 行 → 可人工确认目标。依赖最新 QC 报告，不自行重跑像素机检。"""
    data = payload if payload is not None else _load_latest_qc_payload(root, ep)
    face = ((data.get("checks") or {}).get("face") or {}) if isinstance(data, Mapping) else {}
    confirmations = load_face_confirmations(root, ep)
    out: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    for row in face.get("shots") or []:
        if not isinstance(row, Mapping):
            continue
        verdict = str(row.get("manual_original_verdict") or row.get("verdict") or "")
        if verdict not in {"block", "warn"}:
            continue
        char = str(row.get("char") or "").strip()
        png = _coverage_png_key(row.get("png"))
        if not char or not png:
            continue
        key = (char, png)
        if key in seen:
            continue
        seen.add(key)
        confirm = confirmations.get(key)
        out.append({
            "char": char,
            "shot": _shot_key(png),
            "png": png,
            "png_abs": str(_prop_shape_png_path(root, ep, png)),
            "score": row.get("score"),
            "score_vs_main": row.get("score_vs_main"),
            "floor": row.get("floor"),
            "original_verdict": verdict,
            "confirmed": bool(confirm),
            "confirmation_path": str(_face_confirmation_path(root, ep)),
            "reason": "face_embedding_warn_or_block",
        })
    return out


def face_confirmation_report(root: Path, ep: str,
                             payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    targets = face_confirmation_targets(root, ep, payload=payload)
    pending = [t for t in targets if not t.get("confirmed")]
    rerun_shots = sorted({str(t.get("shot") or "").strip() for t in pending if str(t.get("shot") or "").strip()})
    return {
        "kind": "n2d_face_review",
        "version": 1,
        "episode": ep,
        "confirmation_path": str(_face_confirmation_path(root, ep)),
        "total": len(targets),
        "pending": len(pending),
        "confirmed": len(targets) - len(pending),
        "targets": targets,
        "rerun_plan": {
            "stage": "image",
            "affected_shots": rerun_shots,
            "command": " ".join(f"--affected-shot {s}" for s in rerun_shots),
            "scope": "脸部 embedding warn/block 未人工确认，需确认或重出受影响镜头",
        },
    }


def _upsert_face_rows(root: Path, ep: str, rows: Sequence[Mapping[str, Any]],
                      *, overwrite: bool = True) -> Dict[str, Any]:
    data = _load_face_confirmation_doc(root, ep)
    existing: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in data.get("confirmations") or []:
        if not isinstance(row, Mapping):
            continue
        key = _face_confirmation_key(row.get("char") or row.get("character") or row.get("id"),
                                     row.get("png") or row.get("image"))
        if key[0] and key[1]:
            existing[key] = dict(row)
    changed = 0
    for row in rows:
        key = _face_confirmation_key(row.get("char") or row.get("character") or row.get("id"),
                                     row.get("png") or row.get("image"))
        if not key[0] or not key[1]:
            continue
        if key in existing and not overwrite:
            continue
        new_row = dict(existing.get(key, {}))
        new_row.update({k: v for k, v in row.items() if v is not None})
        new_row["char"] = key[0]
        new_row["png"] = key[1]
        existing[key] = new_row
        changed += 1
    data["confirmations"] = sorted(existing.values(), key=lambda r: (str(r.get("char")), str(r.get("png"))))
    path = _save_face_confirmation_doc(root, ep, data)
    return {"ok": True, "path": str(path), "changed": changed, "total": len(data["confirmations"])}


def confirm_face_targets(root: Path, ep: str, selector: str,
                         *, reviewer: str = "manual", reason: str = "") -> Dict[str, Any]:
    report = face_confirmation_report(root, ep)
    selector = str(selector or "").strip()
    targets = report.get("targets") or []
    if selector.lower() in {"all", "*", "pending"}:
        chosen = [t for t in targets if not t.get("confirmed")]
    else:
        wanted = {s.strip() for s in re.split(r"[,;]", selector) if s.strip()}
        chosen = [
            t for t in targets
            if str(t.get("char")) in wanted
            or str(t.get("png")) in wanted
            or str(t.get("shot")) in wanted
            or f"{t.get('char')}::{t.get('png')}" in wanted
        ]
    rows: List[Dict[str, Any]] = []
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    for t in chosen:
        rows.append({
            "char": t.get("char"),
            "png": t.get("png"),
            "png_sha256": _episode_png_sha(root, ep, t.get("png")),
            "shot": t.get("shot"),
            "verdict": "ok",
            "reviewer": reviewer,
            "source": "image_qc:manual_face_confirm",
            "confirmed_at": now,
            "reason": reason or "人工确认与角色定妆一致，embedding 低分为角度/暗光/侧背等误报",
            "original_verdict": t.get("original_verdict"),
            "score": t.get("score"),
            "score_vs_main": t.get("score_vs_main"),
            "floor": t.get("floor"),
        })
    res = _upsert_face_rows(root, ep, rows, overwrite=True)
    res.update({"selected": len(chosen), "pending_before": report.get("pending", 0)})
    return res


def _stitch_for_png(payload: Dict[str, Any], png: Optional[str]) -> Optional[str]:
    for t in payload.get("face_human_review") or []:
        if t.get("png") == png and t.get("stitched"):
            return t.get("stitch")
    return None


def _episode_rel_path(root: Path, ep: str, path: Path) -> str:
    try:
        return path.relative_to(Path(root) / "出图" / ep).as_posix()
    except Exception:
        try:
            return path.relative_to(Path(root)).as_posix()
        except Exception:
            return path.as_posix()


def _resolve_existing_character_png(root: Path, ep: str, rec: Mapping[str, Any]) -> Optional[str]:
    """角色镜 manifest → 已落档 PNG（相对 `出图/<ep>`）。未出图返回 None。"""
    root = Path(root)
    png = str(rec.get("png") or "").strip()
    candidates: List[Path] = []
    if png:
        p = Path(png)
        if p.is_absolute():
            candidates.append(p)
        candidates.extend([
            root / png,
            root / "出图" / ep / png,
            root / "出图" / ep / "图片" / png,
        ])
    for cand in candidates:
        if cand.exists() and cand.is_file():
            return _episode_rel_path(root, ep, cand)

    shot = str(rec.get("shot") or "")
    if not shot:
        return None
    img_dir = root / "出图" / ep / "图片"
    if not img_dir.exists():
        return None
    for cand in sorted(img_dir.glob("*.png")):
        if re.search(r"_(?:end|mid|a\d+)\.png$", cand.name):
            continue
        if _shot_key(cand.name) == shot:
            return _episode_rel_path(root, ep, cand)
    return None


def _face_full_precision(face: Mapping[str, Any]) -> bool:
    mode = str(face.get("mode") or "")
    precision = str(face.get("precision_level") or "")
    if face.get("available") is False:
        return False
    if mode in FACE_DEGRADED_MODES or precision in ("degraded", "none", "insufficient_precision"):
        return False
    return mode not in ("", "None", "none", "null")


def face_reference_coverage(payload: Dict[str, Any], root: Path, ep: str) -> Dict[str, Any]:
    """铁律：每张已落档角色 PNG 必须有 full 精度定妆/身份主参考脸部比对证据。

    - prompt 阶段尚未出图的角色镜只列入 pending，不阻断。
    - 一旦 PNG 已存在，缺 full 精度、缺 face row、face row=warn/noface 都是 hard block。
    - face row=block 已由 G1 硬伤本身阻断，这里只视为“有比对证据”，避免重复计数。
    """
    lint = payload.get("lint") or {}
    manifest = [r for r in (lint.get("character_shots") or []) if isinstance(r, Mapping)]
    face = (payload.get("checks") or {}).get("face") or {}
    notes: List[str] = []
    required: List[Dict[str, Any]] = []
    pending: List[Dict[str, Any]] = []

    if not lint.get("available", True):
        png_dir = Path(root) / "出图" / ep / "图片"
        landed = sorted(png_dir.glob("*.png")) if png_dir.exists() else []
        missing = []
        if landed:
            missing.append({
                "shot": "unknown",
                "png": None,
                "label": "prompt_missing",
                "reason": "no_character_manifest",
            })
        return {
            "available": False,
            "required": len(landed),
            "covered": 0,
            "missing": missing,
            "pending": [],
            "precision_level": "unknown",
            "face_mode": face.get("mode"),
            "verdict": "block" if missing else "ok",
            "notes": ["缺出图 prompt lint，无法建立角色镜覆盖清单；已有落档 PNG 时不得进入 video。"],
        }

    for raw in manifest:
        rec = dict(raw)
        resolved = _resolve_existing_character_png(Path(root), ep, rec)
        if resolved:
            rec["png"] = resolved
            rec["shot"] = rec.get("shot") or _shot_key(resolved)
            required.append(rec)
        else:
            pending.append(rec)

    full = _face_full_precision(face)
    rows_by_shot: Dict[str, List[Dict[str, Any]]] = {}
    rows_by_png: Dict[str, Dict[str, Any]] = {}
    for row in (face.get("shots") or []):
        if not isinstance(row, dict):
            continue
        png_key = _coverage_png_key(row.get("png"))
        if png_key:
            rows_by_png[png_key] = row
        key = _shot_key(row.get("png"))
        if key:
            rows_by_shot.setdefault(key, []).append(row)

    missing: List[Dict[str, Any]] = []
    covered: List[Dict[str, Any]] = []
    if required and not full:
        missing = [{**rec, "reason": "face_precision_not_full"} for rec in required]
        notes.append("已落档角色 PNG 存在，但 face_consistency 不是 full 精度；不能证明与定妆照同人。")
    elif required:
        for rec in required:
            exact = rows_by_png.get(_coverage_png_key(rec.get("png")))
            rows = [exact] if exact else rows_by_shot.get(str(rec.get("shot") or ""))
            if not rows:
                missing.append({**rec, "reason": "no_face_comparison"})
                continue
            row = max(rows, key=lambda r: SEVERITY.get(str(r.get("verdict") or ""), 0))
            verdict = str(row.get("verdict") or "")
            if verdict in ("warn", "noface"):
                missing.append({**rec, "reason": f"face_verdict_{verdict}", "face_verdict": verdict})
            else:
                covered.append({**rec, "face_verdict": verdict or "unknown"})

    # disk-scoped 兜底：lint 跑了但漏分类的角色镜。required 只来自 character_shots 清单，
    # 若某张已落档 PNG 被 lint 漏判为角色镜，它永远进不了 required、永不与定妆比对。
    # 以「face_consistency 在该 PNG 实检出人脸」为证据（noface/场景镜天然排除，低误报），
    # 把不在 required 的有脸镜列为 advisory「待人工确认是否角色镜」——不硬拦，但不再静默漏检。
    # 仅在 full 精度下信任「检出人脸」这一信号；非 full 时 required 已整组 missing 硬拦，无需再列。
    unclassified: List[Dict[str, Any]] = []
    if full:
        required_keys = {str(rec.get("shot") or "") for rec in required}
        for key, rows in rows_by_shot.items():
            if not key or key in required_keys:
                continue
            row = max(rows, key=lambda r: SEVERITY.get(str(r.get("verdict") or ""), 0))
            verdict = str(row.get("verdict") or "")
            if verdict in ("ok", "warn"):  # 检出人脸；block 已由 G1 硬阻断，noface=无脸不计
                unclassified.append({
                    "shot": key,
                    "png": row.get("png"),
                    "label": "lint_unclassified",
                    "reason": "unclassified_face_shot",
                    "face_verdict": verdict,
                })

    return {
        "available": True,
        "required": len(required),
        "covered": len(covered),
        "missing": missing,
        "unclassified": unclassified,
        "pending": pending,
        "precision_level": "full" if full else ("degraded" if face else "none"),
        "face_mode": face.get("mode"),
        "verdict": "block" if missing else "ok",
        "notes": notes,
    }


def _coverage_png_key(value: Any) -> str:
    """Normalize episode image paths for exact face-coverage matching."""
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    marker = "/图片/"
    if marker in text:
        return "图片/" + text.rsplit(marker, 1)[-1]
    if text.startswith("图片/"):
        return text
    if text.endswith(".png") and "/" not in text:
        return "图片/" + text
    return text


def _production_events_path(root: Path) -> Path:
    return Path(root) / "生产数据" / "production_events.jsonl"


def _load_production_events(root: Path) -> List[Dict[str, Any]]:
    path = _production_events_path(root)
    if not path.exists():
        return []
    events: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                events.append(item)
    except Exception:
        return []
    return events


def _event_generation(event: Mapping[str, Any]) -> Mapping[str, Any]:
    return event.get("generation") if isinstance(event.get("generation"), Mapping) else {}


def _event_meta(event: Mapping[str, Any]) -> Mapping[str, Any]:
    return event.get("meta") if isinstance(event.get("meta"), Mapping) else {}


def _event_cost(event: Mapping[str, Any]) -> Mapping[str, Any]:
    return event.get("cost") if isinstance(event.get("cost"), Mapping) else {}


def _event_asset_rel(root: Path, event: Mapping[str, Any]) -> Optional[str]:
    generation = _event_generation(event)
    asset = generation.get("asset") or event.get("asset")
    if not asset:
        return None
    raw = str(asset).strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(Path(root).resolve()).as_posix()
        except Exception:
            return p.as_posix()
    return p.as_posix()


def _is_prohibited_face_patch_event(event: Mapping[str, Any]) -> bool:
    generation = _event_generation(event)
    meta = _event_meta(event)
    cost = _event_cost(event)
    fields = [
        event.get("provider"),
        event.get("source"),
        event.get("method"),
        cost.get("provider"),
        cost.get("method"),
        generation.get("provider"),
        generation.get("method"),
        generation.get("redraw_category"),
        generation.get("redraw_reason"),
        meta.get("provider"),
        meta.get("method"),
    ]
    text = " ".join(str(v) for v in fields if v is not None).lower()
    if any(token in text for token in PROHIBITED_FACE_PATCH_STRONG_TOKENS):
        return True
    return ("face" in text or "脸" in text) and any(
        token in text for token in PROHIBITED_FACE_PATCH_OPERATION_TOKENS
    )


def prohibited_face_patch_outputs(root: Path, ep: str) -> Dict[str, Any]:
    """查生产事件账本：最新落档事件若来自本地贴脸/换脸/alpha blend，则该 PNG 永久不得进 video。

    这是比 embedding 分数更高优先级的事实闸门：embedding 只能说明相似，不能把本地裁脸贴回画面的
    产物洗成合格出图。后续只有真实重抽 / 官方 image2image 落一条新的 pass 事件，才能覆盖旧事件。
    """
    latest: Dict[str, tuple[int, Dict[str, Any]]] = {}
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        rel = _event_asset_rel(root, event)
        if not rel or not rel.endswith(".png"):
            continue
        latest[rel] = (idx, event)

    outputs: List[Dict[str, Any]] = []
    for rel, (line_no, event) in latest.items():
        if not _is_prohibited_face_patch_event(event):
            continue
        generation = _event_generation(event)
        meta = _event_meta(event)
        cost = _event_cost(event)
        provider = (
            cost.get("provider")
            or generation.get("provider")
            or event.get("provider")
            or event.get("source")
            or ""
        )
        method = meta.get("method") or generation.get("method") or cost.get("method") or event.get("method") or ""
        outputs.append({
            "png": rel,
            "shot": _shot_key(rel),
            "line": line_no,
            "provider": str(provider),
            "method": str(method),
            "status": str(generation.get("status") or event.get("status") or ""),
            "reason": str(generation.get("redraw_reason") or ""),
            "verdict": "block",
        })

    outputs.sort(key=lambda r: (str(r.get("shot") or ""), str(r.get("png") or "")))
    return {
        "available": True,
        "outputs": outputs,
        "verdict": "block" if outputs else "ok",
        "notes": [] if outputs else ["未发现最新落档事件来自本地贴脸修复。"],
    }


def semantic_embedding_required(payload: Mapping[str, Any]) -> List[str]:
    """Registered scene/asset pairs exist but DINO/CLIP semantic drift did not run.

    Scene/multimodal checks are only produced for registered LOC_/PROP_/OUTFIT_/VFX-like assets.
    If the semantic drift sidecar explicitly says unavailable, palette/dHash alone is too weak for
    key non-face asset identity, so image_qc should stop before video.

    Robustness（堵静默消失洞）：sidecar **整段缺席**（semantic_drift.py 加载/执行异常被 run_qc 吞掉，
    payload 里根本没有 "semantic_drift" 键）与 available=False 等价处理——否则一次模块加载失败就让非脸
    关键资产的 hard 兜底无声蒸发。只有 sidecar **确实跑通**（available is True）才不在此升 hard（改由
    findings 表达）。
    """
    sd = payload.get("semantic_drift")
    ran_ok = isinstance(sd, Mapping) and sd.get("available") is True
    if ran_ok:
        return []
    checks = payload.get("checks") or {}
    out: List[str] = []
    for key, asset_keys in (
        ("scene", ("scene", "group", "asset")),
        ("multimodal", ("asset", "group", "scene")),
    ):
        for item in ((checks.get(key) or {}).get("shots") or []):
            if not isinstance(item, Mapping) or not item.get("png"):
                continue
            hint = next((str(item.get(k) or "").strip() for k in asset_keys if str(item.get(k) or "").strip()), "")
            if hint:
                out.append(f"{hint}:{item.get('png')}")
    return sorted(set(out))


def summarize(payload: Dict[str, Any], *, strict_pixel: bool = False) -> Dict[str, Any]:
    """汇总各项机检 + lint，区分 hard（必须修）与 advisory（非阻断初筛）。

    strict_pixel（默认 off，保留现行宽松判定）：把任何像素机检的 block 升为 hard
    （服装换装/场景换景/道具特效漂移=真硬伤而非初筛噪声）→ verdict=block。"""
    hard = advisory = 0
    rows_by_check: Dict[str, Dict[str, int]] = {}
    for key, shots_key in (("face", "shots"), ("hair", "shots"), ("outfit", "shots"),
                           ("scene", "shots"), ("multimodal", "shots"), ("seam", "seams")):
        res = payload.get("checks", {}).get(key) or {}
        cnt = count_verdicts(res.get(shots_key) or [])
        rows_by_check[key] = cnt
        if key in HARD_CHECKS or strict_pixel:
            hard += cnt["block"]
            advisory += cnt["warn"]
        else:
            advisory += cnt["block"] + cnt["warn"]   # 初筛项的 block 也只算人判
    # anchors（锚点门 N3）：非阻断初筛
    anchors = payload.get("checks", {}).get("anchors") or {}
    a_block = sum(1 for a in (anchors.get("anchors") or [])
                  if a.get("verdict") == "block" or a.get("level") == "block")
    rows_by_check["anchors"] = {"block": a_block, "warn": 0, "noface": 0, "ok": 0}
    advisory += a_block
    # lint：硬码项（非法 ID / 纯文生图）入 hard，其余 warn 入 advisory
    # 降级精度近景铁律：insightface 缺席→近景/特写脸无法验同人，升 hard（普通景别仍走 unavailable→review）。
    degraded_cu = len(_degraded_closeup_face_shots(payload))
    if degraded_cu:
        rows_by_check["face_degraded_closeup"] = {"block": degraded_cu, "warn": 0, "noface": 0, "ok": 0}
        hard += degraded_cu
    # A 降级精度多人同框：detect_face_swaps 失效，次要角色脸无人核验 → 比照近景升 hard（去重近景，不双计）。
    degraded_multi = len(_degraded_multi_person_face_shots(payload))
    if degraded_multi:
        rows_by_check["face_degraded_multi_person"] = {"block": degraded_multi, "warn": 0, "noface": 0, "ok": 0}
        hard += degraded_multi
    coverage = payload.get("face_reference_coverage") or {}
    coverage_missing = coverage.get("missing") or []
    if coverage_missing:
        rows_by_check["face_reference_coverage"] = {
            "block": len(coverage_missing), "warn": 0, "noface": 0, "ok": int(coverage.get("covered") or 0)
        }
        hard += len(coverage_missing)
    # 漏分类有脸镜（disk-scoped 兜底）：advisory，不入 hard——交人判是否角色镜
    coverage_unclassified = coverage.get("unclassified") or []
    if coverage_unclassified:
        rows_by_check["face_reference_coverage_unclassified"] = {
            "block": 0, "warn": len(coverage_unclassified), "noface": 0, "ok": 0
        }
        advisory += len(coverage_unclassified)
    prohibited = (payload.get("prohibited_face_patch") or {}).get("outputs") or []
    rows_by_check["prohibited_face_patch"] = {
        "block": len(prohibited), "warn": 0, "noface": 0, "ok": 0
    }
    hard += len(prohibited)
    # 跨集脸漂移趋势（B）：high = 系统性退化，下一批必须停下修锚/主体库/重抽；medium 仍 advisory。
    drift_entries = (payload.get("cross_episode_face_drift") or {}).get("entries") or []
    if drift_entries:
        drift_high = sum(1 for e in drift_entries if e.get("severity") == "high")
        drift_warn = len(drift_entries) - drift_high
        rows_by_check["cross_episode_face_drift"] = {
            "block": drift_high, "warn": drift_warn, "noface": 0, "ok": 0
        }
        hard += drift_high
        advisory += drift_warn
    semantic_missing = semantic_embedding_required(payload)
    if semantic_missing:
        rows_by_check["semantic_drift_embedding"] = {
            "block": len(semantic_missing), "warn": 0, "noface": 0, "ok": 0
        }
        hard += len(semantic_missing)
    semantic_findings = (payload.get("semantic_drift") or {}).get("findings") or []
    if semantic_findings:
        sd_warn = sum(1 for f in semantic_findings if f.get("level") == "warn")
        rows_by_check["semantic_drift"] = {
            "block": 0, "warn": sd_warn, "noface": 0,
            "ok": max(0, len(semantic_findings) - sd_warn),
        }
        advisory += sd_warn
    # 契约像素兜底（色调/光位）：暖冷·明暗矛盾=advisory（WARN·人判，色调模糊不升 hard 避免误杀）。
    tone_findings_list = (payload.get("tone_light_contract") or {}).get("findings") or []
    if tone_findings_list:
        tl_warn = sum(1 for f in tone_findings_list if f.get("level") == "warn")
        rows_by_check["tone_light_contract"] = {
            "block": 0, "warn": tl_warn, "noface": 0,
            "ok": max(0, len(tone_findings_list) - tl_warn),
        }
        advisory += tl_warn
    # 契约像素兜底（景别阶梯）：声明景别 vs 实测脸占比矛盾=advisory（WARN·人判）。
    scale_findings_list = (payload.get("shot_scale_contract") or {}).get("findings") or []
    if scale_findings_list:
        ss_warn = sum(1 for f in scale_findings_list if f.get("level") == "warn")
        rows_by_check["shot_scale_contract"] = {
            "block": 0, "warn": ss_warn, "noface": 0,
            "ok": max(0, len(scale_findings_list) - ss_warn),
        }
        advisory += ss_warn
    # ④ VLM 语义判定：关键资产 VLM 判崩设定=hard（既成语义崩，不是预测）；低置信/非关键=warn advisory。
    vlm = payload.get("vlm_consistency") or {}
    vlm_findings = vlm.get("findings") or []
    if vlm_findings:
        vlm_block = sum(1 for f in vlm_findings if f.get("level") == "block")
        vlm_warn = len(vlm_findings) - vlm_block
        rows_by_check["vlm_semantic"] = {"block": vlm_block, "warn": vlm_warn, "noface": 0, "ok": 0}
        hard += vlm_block
        advisory += vlm_warn
    prop_shape = payload.get("prop_shape_review") or {}
    prop_pending = [t for t in (prop_shape.get("targets") or []) if not t.get("confirmed")]
    if prop_pending:
        rows_by_check["prop_shape_review"] = {"block": len(prop_pending), "warn": 0, "noface": 0, "ok": 0}
        hard += len(prop_pending)
    stale_artifacts = (payload.get("artifact_namespace") or {}).get("stale") or []
    if stale_artifacts:
        rows_by_check["artifact_namespace"] = {
            "block": len(stale_artifacts), "warn": 0, "noface": 0, "ok": 0
        }
        hard += len(stale_artifacts)
    lint = payload.get("lint") or {}
    l_hard = sum(1 for f in lint.get("findings", [])
                 if f.get("level") == "block" and f.get("code") in HARD_LINT_CODES)
    l_block = sum(1 for f in lint.get("findings", []) if f.get("level") == "block")
    l_warn = sum(1 for f in lint.get("findings", []) if f.get("level") == "warn")
    rows_by_check["lint"] = {"block": l_block, "warn": l_warn, "noface": 0, "ok": 0}
    hard += l_hard
    advisory += (l_block - l_hard) + l_warn
    unavailable = unavailable_visual_checks(payload)
    face_mode = str((payload.get("checks", {}).get("face") or {}).get("mode") or "")
    degraded = bool(unavailable) or face_mode in FACE_DEGRADED_MODES
    return {"hard_blocks": hard, "advisory": advisory, "by_check": rows_by_check,
            "unavailable_visual_checks": unavailable,
            "degraded": degraded,
            "verdict": "block" if hard else ("review" if advisory or degraded else "ok")}


def qc_environment(payload: Dict[str, Any], *, with_pixel: bool = True) -> Dict[str, Any]:
    """User-facing capability banner for image QC.

    full: face embedding + pixel checks available.
    degraded: some visual checks unavailable, or face falls back to Pillow quality-only mode.
    none: no pixel checks were requested, or every declared core visual check is unavailable.
    """
    checks = payload.get("checks", {}) or {}
    unavailable = unavailable_visual_checks(payload)
    core_checks = {"face", "hair", "outfit", "scene", "seam"}
    declared_core_checks = {k for k in core_checks if k in checks}
    face_mode = str((checks.get("face") or {}).get("mode") or "")
    degraded_face = face_mode in FACE_DEGRADED_MODES
    missing: List[str] = []

    if not with_pixel:
        level = "none"
        missing.append("pixel checks disabled by --no-pixel")
    elif not declared_core_checks or declared_core_checks.issubset(set(unavailable)):
        level = "none"
        missing.extend(VISUAL_CHECK_LABELS.get(k, k) for k in unavailable)
    elif unavailable or degraded_face:
        level = "degraded"
        missing.extend(VISUAL_CHECK_LABELS.get(k, k) for k in unavailable)
        if degraded_face:
            missing.append("insightface/onnxruntime/buffalo_l face embedding")
    else:
        level = "full"

    verdict = (payload.get("summary") or {}).get("verdict")
    if level == "none":
        jump_to = "image_qc_setup"
        reason = "像素质检不可用，不能把图片视为机检通过"
    elif level == "degraded":
        jump_to = "image"
        reason = "视觉质检为降级结果，正式进 video 前需补依赖重跑到 full 精度"
    elif verdict == "block":
        jump_to = "image"
        reason = "image_qc 有硬阻断，需修复/重抽受影响镜头后重跑"
    elif verdict == "review":
        jump_to = "video"
        reason = "full image_qc 仅有非阻断初筛项，已作为 gate warn 入账；不阻断进入 video"
    else:
        jump_to = "video"
        reason = "full QC 未见阻断"

    install = QC_INSTALL_RECOMMENDATION if level != "full" else ""
    return {
        "precision_level": level,
        "python": sys.executable,
        "face_mode": face_mode or None,
        "missing_or_degraded": sorted(set(missing)),
        "recommended_install": install,
        "jump_to_stage": jump_to,
        "jump_reason": reason,
        "user_notice": (
            f"图片质检环境：{level}；当前解释器：{sys.executable}；"
            f"建议安装：{install or '无需补装'}；"
            f"当前应停在/回退：{jump_to}；原因：{reason}"
        ),
    }


# ── 转 gate 同形 findings（dashboard gate --stage image_preflight/image 接入用） ─────────

def _qc_finding(sev: str, dim: str, loc: Optional[str], msg: str) -> Dict[str, Any]:
    return {"sev": sev, "dim": dim, "loc": loc, "msg": msg, "return_to_stage": "image"}


def to_findings(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把 image_qc payload 转成与 n2d-review/gate.py 同形的 findings 列表，供
    dashboard gate --stage image_preflight/image 合并入账。sev 沿用 summarize 的 hard/advisory 哲学：
    硬阻断（崩脸 / 纯文生图 / 非法 CHAR_id）= block，像素初筛 = warn。纯函数·可测。"""
    out: List[Dict[str, Any]] = []
    checks = payload.get("checks", {}) or {}
    env = payload.get("qc_environment") or {}
    precision = str(env.get("precision_level") or "").strip().lower()
    if precision == "none":
        out.append(_qc_finding(
            "block",
            "image_qc_precision",
            None,
            "image_qc 精度为 none：像素质检不可用，不能把图片视为机检通过；"
            "先按 image_qc_setup 补 Pillow/cv2/insightface/onnxruntime 等依赖后重跑 image_qc。",
        ))
    elif precision == "degraded":
        out.append(_qc_finding(
            "warn",
            "image_qc_precision",
            None,
            "image_qc 精度为 degraded：正式进 video 前需补依赖重跑到 full 精度；"
            "普通人审记录只能辅助定位，不能替代 video/compose 前的 full QC gate。",
        ))
    for key in unavailable_visual_checks(payload):
        res = checks.get(key) or {}
        note = "；".join(res.get("notes", [])) if isinstance(res, dict) else ""
        out.append(_qc_finding(
            "warn",
            VISUAL_CHECK_DIMS.get(key, "image_qc"),
            None,
            f"{VISUAL_CHECK_LABELS.get(key, key)} 未执行：{note or '视觉机检不可用'}；本轮图片一致性为降级判定，需补依赖后重跑或人工复核。",
        ))
    for item in (payload.get("artifact_namespace") or {}).get("stale") or []:
        rel = item.get("path")
        out.append(_qc_finding(
            "block",
            "image_artifact_namespace",
            rel,
            f"本集 live 图片目录存在当前 `01_分镜出图.md` 未声明的旧/旁路 Clip PNG：{rel}。"
            "先移入 `废料/出图/第N集/...`，并同步 storyboard/video prompt 到当前目标集后重跑 image_qc。",
        ))
    # 崩脸 G1（hard）：block→block / warn→warn
    for s in (checks.get("face") or {}).get("shots", []):
        v = s.get("verdict")
        if v in ("block", "warn"):
            out.append(_qc_finding(v, "character_consistency", s.get("png"),
                                   f"崩脸 G1 {v}：{s.get('png')}（脸/身份漂移机检）"))
    # 降级精度近景（hard）：Pillow 模式无法验同人，近景/特写镜硬拦——装 insightface 重跑或人工逐帧确认前不放行。
    # 附并排对比图路径（①），让人审一屏秒判同人，而非硬拦后无从复核。
    for s in _degraded_closeup_face_shots(payload):
        stitch = _stitch_for_png(payload, s.get("png"))
        aid = f"；人审并排图：{stitch}" if stitch else ""
        out.append(_qc_finding("block", "character_consistency", s.get("png"),
                               f"降级精度近景：{s.get('png')} 在 Pillow 降级模式下无法验脸（无 insightface）；"
                               f"近景/特写脸是否同人未经核验，不放行{aid}"))
    # A 降级精度多人同框（hard）：detect_face_swaps 整组失效，次要角色脸无人核验——比照近景不放行。
    for s in _degraded_multi_person_face_shots(payload):
        stitch = _stitch_for_png(payload, s.get("png"))
        aid = f"；人审并排图：{stitch}" if stitch else ""
        out.append(_qc_finding("block", "character_consistency", s.get("png"),
                               f"降级精度多人同框：{s.get('png')} 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；"
                               f"同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行{aid}"))
    for s in (payload.get("prohibited_face_patch") or {}).get("outputs", []):
        out.append(_qc_finding(
            "block",
            "character_consistency",
            s.get("png"),
            f"{PROHIBITED_FACE_PATCH_LABEL}：{s.get('png')} 最新落档事件来自 `{s.get('provider') or 'unknown'}`"
            f" / `{s.get('method') or 'unknown'}`。embedding 分数不是合格目标，不能用裁脸/贴脸/换脸"
            "把定妆照盖到镜头上骗过 QC；必须回 n2d-image 用真实重抽或官方 image2image 派生替换。",
        ))
    for e in (payload.get("cross_episode_face_drift") or {}).get("entries", []):
        sev = "block" if e.get("severity") == "high" else "warn"
        out.append(_qc_finding(
            sev,
            "character_consistency",
            e.get("char") or e.get("episode_to"),
            f"跨集脸漂移趋势 {e.get('severity')}：{e.get('char') or '角色'} "
            f"{e.get('episode_from')}→{e.get('episode_to')} mean {e.get('from_mean')}→{e.get('to_mean')} "
            f"drop={e.get('drop')}。high 级系统性退化必须先回 n2d-image 补主体库/参考包/重抽并重跑 identity/image_qc。",
        ))
    semantic_missing = semantic_embedding_required(payload)
    if semantic_missing:
        sample = "、".join(semantic_missing[:6]) + ("…" if len(semantic_missing) > 6 else "")
        out.append(_qc_finding(
            "block",
            "multimodal_continuity",
            None,
            "关键场景/道具/服装/VFX 已进入 scene/multimodal QC，但 DINO/CLIP 语义漂移嵌入后端不可用；"
            f"palette/dHash 只能做初筛，不能证明非脸资产身份稳定。先在 full QC 环境补 torch+transformers/open_clip "
            f"后重跑。样例：{sample}",
        ))
    for f in (payload.get("semantic_drift") or {}).get("findings", []):
        level = str(f.get("level") or "warn")
        sev = "warn" if level == "warn" else "info"
        out.append(_qc_finding(sev, "multimodal_continuity", None, f.get("msg", "")))
    # 契约像素兜底（色调/光位）→ style_consistency（色调/光位属基础视觉风格契约，回 n2d-image/契约）。
    for f in (payload.get("tone_light_contract") or {}).get("findings", []):
        level = str(f.get("level") or "warn")
        sev = "warn" if level == "warn" else "info"
        out.append(_qc_finding(sev, "style_consistency", None, f.get("msg", "")))
    # 契约像素兜底（景别阶梯）→ style_consistency（构图/景别 → 重出该镜，return_to_stage=image）。
    for f in (payload.get("shot_scale_contract") or {}).get("findings", []):
        level = str(f.get("level") or "warn")
        sev = "warn" if level == "warn" else "info"
        out.append(_qc_finding(sev, "style_consistency", None, f.get("msg", "")))
    # 风格归属佐证（⑤·选定风格 vs 实际渲染）→ style_consistency（整集风格指纹偏离风格锚/未登记锚 → 回 n2d-image）。
    for f in (payload.get("style_attribution") or {}).get("findings", []):
        level = str(f.get("level") or "warn")
        sev = "warn" if level == "warn" else ("block" if level == "block" else "info")
        out.append(_qc_finding(sev, "style_consistency", None, f.get("msg", "")))
    # ④ VLM 语义判定（描述↔渲染图）：关键资产判崩设定=block，低置信/非关键=warn 人判。
    for f in (payload.get("vlm_consistency") or {}).get("findings", []):
        dim = "character_consistency" if f.get("code") == "vlm_semantic_mismatch" and "角色「" in str(f.get("msg")) else "multimodal_continuity"
        out.append(_qc_finding(f.get("level", "warn"), dim, None, f.get("msg", "")))
    for t in (payload.get("prop_shape_review") or {}).get("targets", []):
        if t.get("confirmed"):
            continue
        stitch = f"；并排复核图：{t.get('stitch')}" if t.get("stitched") and t.get("stitch") else ""
        terms = "、".join(str(x) for x in (t.get("must_not_have") or [])[:12])
        out.append(_qc_finding(
            "block",
            "multimodal_continuity",
            t.get("png"),
            f"高风险道具禁形/尺寸未逐图确认：{t.get('label') or t.get('shot')} 的 `{t.get('asset')}`"
            f"（{t.get('asset_name') or ''}）登记了 must_not_have={terms}"
            f"{'；scale=' + str(t.get('scale')) if t.get('scale') else ''}。"
            f"文字约束不能证明既有 PNG 没长出禁形或尺寸没漂，需人工/视觉模型确认 `{t.get('png')}`"
            f" 无这些禁形且大小符合道具设定，或重出该图；确认文件：{t.get('confirmation_path')}{stitch}",
        ))
    reason_text = {
        "face_precision_not_full": "缺 full 精度脸部 embedding 比对",
        "no_face_comparison": "缺逐镜脸部参考比对记录",
        "face_verdict_warn": "脸部比对为 warn，疑似身份漂移",
        "face_verdict_noface": "本镜未检出可比对人脸",
        "no_character_manifest": "缺角色镜覆盖清单",
    }
    for s in (payload.get("face_reference_coverage") or {}).get("missing", []):
        reason = str(s.get("reason") or "")
        label = s.get("label") or s.get("shot") or "角色镜"
        out.append(_qc_finding(
            "block",
            "character_consistency",
            s.get("png") or label,
            f"角色脸定妆比对覆盖缺口：{label} {s.get('png') or ''}；"
            f"{reason_text.get(reason, reason or '未通过')}。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。",
        ))
    # 漏分类有脸镜（advisory）：lint 没把它当角色镜，但 face 检出人脸 → 提示人工确认，不硬拦
    for s in (payload.get("face_reference_coverage") or {}).get("unclassified", []):
        out.append(_qc_finding(
            "warn",
            "character_consistency",
            s.get("png") or s.get("shot"),
            f"疑似漏分类角色镜：{s.get('png') or s.get('shot')} 检出人脸但不在出图 prompt 角色镜清单（character_shots）→ 未纳入定妆覆盖比对。"
            "确认是否角色镜：是则回 n2d-image 在 prompt 标注该镜角色身份后重跑 image_qc；否（路人/群像背景脸）可忽略。",
        ))
    # 发型 H1 / 服装 N1 / 场景 O2 / 锚点门 N3（advisory）：即便 block 也降 warn 作为非阻断初筛入账
    for s in (checks.get("hair") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            out.append(_qc_finding("warn", "character_consistency", s.get("png"),
                                   f"发型 H1 初筛：{s.get('png')}（发色/发型轮廓离群，非阻断）"))
    for s in (checks.get("outfit") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            out.append(_qc_finding("warn", "outfit_consistency", s.get("png"),
                                   f"服装 N1 初筛：{s.get('png')}（调色板离群，非阻断）"))
    for s in (checks.get("scene") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            out.append(_qc_finding("warn", "scene_consistency", s.get("png"),
                                   f"场景 O2 初筛：{s.get('png')} {s.get('kind', '')}（非阻断）"))
    # 道具/特效 P2（advisory·B）：按 asset_registry 分组的组内离群，初筛交人判（武器/法宝/特效漂移早抓）
    for s in (checks.get("multimodal") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            out.append(_qc_finding("warn", "multimodal_continuity", s.get("png"),
                                   f"道具/特效 P2 初筛：{s.get('png')} {s.get('asset') or s.get('group') or ''}"
                                   "（资产组内离群，非阻断）"))
    # 接缝接力（hard·与崩脸同级）：block 原样上报，gate 据此硬拦——尾帧没接上下镜首帧出视频必跳切
    for s in (checks.get("seam") or {}).get("seams", []):
        v = s.get("verdict")
        if v in ("block", "warn"):
            out.append(_qc_finding(v, "scene_consistency", s.get("tail"),
                                   f"接缝接力 {v}：{s.get('tail')}→{s.get('next_first')} dist={s.get('dist')}"
                                   f"（尾帧没接上下镜首帧，出视频会跳切）"))
    for a in (checks.get("anchors") or {}).get("anchors", []):
        if a.get("verdict") in ("block", "warn"):
            out.append(_qc_finding("warn", "character_consistency", a.get("char"),
                                   f"锚点门 N3：{a.get('char')} {a.get('reason', '主参考非单张清晰正脸')}（非阻断）"))
    # 执行层 lint：硬码项（非法 ID / 纯文生图）→ block，info 级（如多参考喂养建议）保 info，其余 → warn
    for f in (payload.get("lint", {}) or {}).get("findings", []):
        hard = f.get("level") == "block" and f.get("code") in HARD_LINT_CODES
        sev = "block" if hard else ("info" if f.get("level") == "info" else "warn")
        out.append(_qc_finding(sev, "image_prompt_lint", None, f.get("msg")))
    # B 定妆两层：脸锚用了戏剧光/氛围板 → warn（会把光当身份烤进脸，应换中性平光板锁身份）
    for fl in (payload.get("face_anchor_lighting") or {}).get("flagged", []):
        out.append(_qc_finding(
            "warn", "character_consistency", fl.get("char"),
            f"{fl.get('char')}/{fl.get('form')} 脸锚疑似戏剧光/氛围板（{Path(str(fl.get('path'))).name}）——"
            "定妆脸锚应是中性平光纯背景板锁身份，戏剧光会把光当身份烤进脸；氛围图请归 atmosphere 层只锁调性。"))
    # 状态账本启发式（advisory，永不翻 verdict）
    sl = payload.get("state_ledger") or {}
    not_injected = sl.get("not_injected_markers") or []
    if not_injected:
        # 状态演进声明了累积状态，但本集出图 prompt 没注入 → warn（比"没建账本"更实锤的漏注入）。
        out.append(_qc_finding(
            "warn", "state_continuity", None,
            f"状态演进声明了累积状态（{'/'.join(not_injected)[:60]}）但本集出图 prompt 未注入——"
            "runner 会照画干净/无伤状态，跨镜/跨集视觉状态漏进生成。"
            "跑 `python3 skills/n2d-image/scripts/visual_state_manager.py <作品根> --inject` 注入后重出受影响镜。"))
    elif sl.get("advise"):
        out.append(_qc_finding(
            "info", "state_continuity", None,
            f"本集出现累积状态关键词（{'/'.join(sl.get('markers', []))[:60]}）但无 visual_state_ledger.json——"
            "状态可能跨镜/跨集演进，建议跑 `python3 skills/n2d-image/scripts/visual_state_manager.py <作品根> --audit` "
            "建账本锁状态（简单剧确认后可忽略；本提示不阻断）。"))
    return out


# ── 重生成清单（update 刷新模式用） ───────────────────────────────────────────

_REGEN_CLIP_RE = re.compile(r"(?:Clip[_\-\s]?|镜头\s*)(\d+)", re.IGNORECASE)


def _shot_key(name: Optional[str]) -> Optional[str]:
    """从 PNG 名 / lint msg 提取镜号 → `Clip_NN`。提不出返回原串（裁掉路径）。纯函数·可测。"""
    if not name:
        return None
    m = _REGEN_CLIP_RE.search(str(name))
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return str(name).split("/")[-1] or None


def to_regen_list(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """返回"不能用、要重生成"的镜（普通落档 QC 消费）：
      硬伤（崩脸 / 纯文生图 / 非法 CHAR_id）+ **校准后**的像素 block（服装 N1 / 接缝）。
    每项 `{shot, png, reasons[]}`。只命中 review/warn（服装/场景调色板初筛、漏字段）的镜**不在内**——
    能用就用，不重生成。场景 O2 只产 warn（设计上不下 block），故不进重生成线。纯函数·可测。"""
    by_shot: Dict[str, Dict[str, Any]] = {}

    def add(name: Optional[str], reason: str) -> None:
        key = _shot_key(name)
        if key is None:
            return
        d = by_shot.setdefault(key, {"shot": key, "png": None, "reasons": []})
        if name and ".png" in str(name):
            current = str(d["png"] or "")
            preferred_prohibited = (
                PROHIBITED_FACE_PATCH_LABEL in reason
                and current.endswith("_end.png")
                and not str(name).endswith("_end.png")
            )
            if not d["png"] or preferred_prohibited:
                d["png"] = name
        if reason not in d["reasons"]:
            d["reasons"].append(reason)

    checks = payload.get("checks", {}) or {}
    for s in (checks.get("face") or {}).get("shots", []):
        if s.get("verdict") == "block":
            add(s.get("png"), "崩脸 G1")
    for s in (checks.get("outfit") or {}).get("shots", []):
        if s.get("verdict") == "block":          # outfit 已相对校准，block 可信
            add(s.get("png"), "服装漂 N1(校准后)")
    for s in (checks.get("scene") or {}).get("shots", []):
        if s.get("verdict") == "block":          # scene 设计上只产 warn；留此分支防未来改动
            add(s.get("png"), "场景漂 O2")
    for s in (checks.get("seam") or {}).get("seams", []):
        if s.get("verdict") == "block":
            add(s.get("tail"), "接缝断")
    for f in (payload.get("lint", {}) or {}).get("findings", []):
        if f.get("level") == "block" and f.get("code") in HARD_LINT_CODES:
            add(f.get("msg"), f"prompt:{f.get('code')}")
    for s in (payload.get("face_reference_coverage") or {}).get("missing", []):
        add(s.get("png") or s.get("label") or s.get("shot"), f"脸部定妆比对覆盖:{s.get('reason')}")
    for s in (payload.get("prohibited_face_patch") or {}).get("outputs", []):
        add(s.get("png") or s.get("shot"), PROHIBITED_FACE_PATCH_LABEL)
    for t in (payload.get("prop_shape_review") or {}).get("targets", []):
        if not t.get("confirmed"):
            add(t.get("png") or t.get("shot"), f"高风险道具禁形/尺寸未确认:{t.get('asset')}")
    return sorted(by_shot.values(), key=lambda d: d["shot"])


def to_strict_regen_list(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """返回 n2d-update「严审刷新」候选重出清单。

    与普通落档 QC 不同，本模式服务于"skill/prompt 更新后重新判断旧图是否仍符合最新标准"：
    - block 必重出；
    - warn / advisory / 降级命中不默认保留旧图，先进入候选重出清单；
    - 只有已有人工判定明确说明该镜可沿用时，执行者才可从候选清单剔除。
    """
    by_shot: Dict[str, Dict[str, Any]] = {}

    def add(name: Optional[str], reason: str) -> None:
        key = _shot_key(name)
        if key is None:
            return
        d = by_shot.setdefault(key, {"shot": key, "png": None, "reasons": []})
        if name and ".png" in str(name):
            current = str(d["png"] or "")
            preferred_prohibited = (
                PROHIBITED_FACE_PATCH_LABEL in reason
                and current.endswith("_end.png")
                and not str(name).endswith("_end.png")
            )
            if not d["png"] or preferred_prohibited:
                d["png"] = name
        if reason not in d["reasons"]:
            d["reasons"].append(reason)

    checks = payload.get("checks", {}) or {}
    for s in (checks.get("face") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn", "noface"):
            add(s.get("png"), f"strict:崩脸/身份 {s.get('verdict')}")
    for s in (checks.get("outfit") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            add(s.get("png"), f"strict:角色DNA服装 {s.get('verdict')}")
    for s in (checks.get("scene") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            add(s.get("png"), f"strict:场景/光色 {s.get('verdict')}")
    for s in (checks.get("seam") or {}).get("seams", []):
        if s.get("verdict") in ("block", "warn"):
            add(s.get("tail"), f"strict:接缝 {s.get('verdict')}")
    for a in (checks.get("anchors") or {}).get("anchors", []):
        if a.get("verdict") in ("block", "warn") or a.get("level") in ("block", "warn"):
            add(a.get("shot") or a.get("png") or a.get("loc") or a.get("char"),
                "strict:锚点门需复核")
    for f in (payload.get("lint", {}) or {}).get("findings", []):
        if f.get("level") in ("block", "warn"):
            add(f.get("msg"), f"strict:prompt:{f.get('code') or f.get('level')}")
    for key in unavailable_visual_checks(payload):
        res = checks.get(key) or {}
        for s in (res.get("shots") or res.get("seams") or []):
            add(s.get("png") or s.get("tail") or s.get("loc"),
                f"strict:{VISUAL_CHECK_LABELS.get(key, key)} 降级未完整校验")
    for s in (payload.get("face_reference_coverage") or {}).get("missing", []):
        add(s.get("png") or s.get("label") or s.get("shot"), f"strict:脸部定妆比对覆盖 {s.get('reason')}")
    for s in (payload.get("prohibited_face_patch") or {}).get("outputs", []):
        add(s.get("png") or s.get("shot"), f"strict:{PROHIBITED_FACE_PATCH_LABEL}")
    for t in (payload.get("prop_shape_review") or {}).get("targets", []):
        if not t.get("confirmed"):
            add(t.get("png") or t.get("shot"), f"strict:高风险道具禁形/尺寸未确认:{t.get('asset')}")
    return sorted(by_shot.values(), key=lambda d: d["shot"])


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def json_safe(value: Any) -> Any:
    """Recursively convert optional numpy/scikit values into JSON primitives."""
    if isinstance(value, Mapping):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass
    if hasattr(value, "tolist") and callable(value.tolist):
        try:
            return json_safe(value.tolist())
        except Exception:
            pass
    return value


FACE_DRIFT_HISTORY_KIND = "n2d_face_drift_history"


def _ep_num(ep: Any) -> int:
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else 0


def _face_drift_history_path(root: Path) -> Path:
    return production_dir(root) / "face_drift_history.json"


def update_face_drift_history(root: Path, ep: str, payload: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    """把本集每角色 `ep_mean_score`（脸 vs 共享定妆主参考均值）落进跨集历史侧车（幂等覆盖本集条目）。

    只在 **full 精度**（insightface）且本集有均值时写——降级精度的均值不可比，写进去会污染漂移基线。
    返回更新后的历史 dict；无可写均值时返回 None。
    """
    face = (payload.get("checks") or {}).get("face") or {}
    chars = face.get("characters") or {}
    means = {c: v.get("ep_mean_score") for c, v in chars.items()
             if isinstance(v, Mapping) and v.get("ep_mean_score") is not None}
    if not _face_full_precision(face) or not means:
        return None
    path = _face_drift_history_path(root)
    data: Dict[str, Any] = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    chars_hist = data.get("characters") if isinstance(data, dict) else None
    if not isinstance(chars_hist, dict):
        chars_hist = {}
    for c, m in means.items():
        rec = chars_hist.setdefault(c, {})
        if isinstance(rec, dict):
            rec[ep] = round(float(m), 4)
    out = {"kind": FACE_DRIFT_HISTORY_KIND, "version": 1, "characters": chars_hist}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def cross_episode_face_drift(root: Path, ep: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
    """跨集脸 embedding **趋势**漂移（治"每集各自过 floor、但整体逐集偏离锚点"的慢性漂移）。

    单帧 G1 只看本集 vs 定妆；这条把历年 `ep_mean_score` 串成时间序，调 face_consistency.cross_episode_drift
    抓相对基线集的系统性掉幅。增量、便宜：本集已由 analyze 嵌入，历史只读侧车，趋势判定是纯数学。
    high 级会在 summarize/to_findings 升 hard block；medium 仍作为趋势预警。
    """
    fc = _load_review_module("face_consistency")
    if fc is None or not hasattr(fc, "cross_episode_drift"):
        return {"available": False, "entries": [], "notes": ["face_consistency.cross_episode_drift 不可用"]}
    hist = update_face_drift_history(root, ep, payload)
    if hist is None:
        # 降级精度 / 本集无均值：用已落档历史只读评估（不含本集）
        path = _face_drift_history_path(root)
        if path.exists():
            try:
                hist = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                hist = None
    chars_hist = (hist or {}).get("characters") if isinstance(hist, dict) else None
    if not isinstance(chars_hist, dict) or not chars_hist:
        return {"available": True, "entries": [], "history_chars": 0,
                "notes": ["无跨集历史（首集或降级精度未累积均值）"]}
    cur_n = _ep_num(ep)
    entries: List[Dict[str, Any]] = []
    for c, rec in chars_hist.items():
        if not isinstance(rec, dict):
            continue
        seq = sorted(((e, m) for e, m in rec.items()
                      if isinstance(m, (int, float)) and _ep_num(e) <= cur_n),
                     key=lambda x: _ep_num(x[0]))
        for d in fc.cross_episode_drift(seq):
            entries.append({"char": c, **d})
    return {"available": True, "entries": entries, "history_chars": len(chars_hist)}


# ── ① 参考图脸部信噪比门（reference quality floor，治「脸太小/低分辨率 → 弱身份锚」） ──────────
#
# 2026 锁脸教头（Nano Banana Pro / Seedream 4.5）一致结论：脸部参考应 ≥1024px、脸占画面 30–50%；
# 脸太小=身份信号弱，喂给下游每一镜都把脸漂带进去。项目已把「人物在画面太小」列为公认崩脸带，但只
# 约束镜头，不约束**参考图本身**。这里只校验 face_anchor_refs / 表情库 / 脸部特写这类**应当紧裁**的脸锚
# （不碰「双手可见」的宽身位主参考——那张本就该脸小）。只拦明显过弱，不追 30–50% 理想值，避免误杀。
WEAK_FACE_RATIO_FLOOR = 0.12   # 脸 bbox 占整图面积低于此 = 脸太小、身份信号弱
WEAK_FACE_CROP_MIN_PX = 768    # 脸部锚裁切短边低于此 = 分辨率不足以锁五官


def weak_face_anchor_reason(face_area_ratio: Optional[float], min_dim: Optional[int]) -> Optional[str]:
    """脸部锚质量判定：脸占比太小 / 裁切分辨率不足 → 返回人读原因；合格 → None。纯函数·可测。

    `face_area_ratio=None`（检测器缺席/Haar 漏检风格化脸）时**不据占比误判**，只用分辨率判。
    `min_dim=None`（读不到尺寸）时跳过分辨率判。两者皆 None → None（不报）。"""
    reasons: List[str] = []
    if face_area_ratio is not None and face_area_ratio < WEAK_FACE_RATIO_FLOOR:
        reasons.append(f"脸占画面仅 {face_area_ratio * 100:.0f}%（建议 ≥30%，至少 ≥{int(WEAK_FACE_RATIO_FLOOR * 100)}%）")
    if min_dim is not None and min_dim < WEAK_FACE_CROP_MIN_PX:
        reasons.append(f"裁切短边 {min_dim}px（建议 ≥1024px，至少 ≥{WEAK_FACE_CROP_MIN_PX}px）")
    return "；".join(reasons) or None


def _face_anchor_ref_items(form: Mapping[str, Any]) -> List[Tuple[str, str]]:
    """收集本形态**应紧裁的脸锚**参考：reference_group.face_anchor_refs、
    reference_atlas.face_anchor_refs / expression_refs。返回 [(label, rel_path)]。纯函数·可测。
    （不收 reference_group.front/half/full——那些是宽身位主参考/服装参考，本就脸小，不该被本门误判。）"""
    out: List[Tuple[str, str]] = []
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    sources = [("face_anchor", rg.get("face_anchor_refs")),
               ("face_anchor", atlas.get("face_anchor_refs")),
               ("expression", atlas.get("expression_refs"))]
    for kind, coll in sources:
        if not coll:
            continue
        items = coll.values() if isinstance(coll, Mapping) else (coll if isinstance(coll, list) else [coll])
        for item in items:
            path = item
            label = kind
            if isinstance(item, Mapping):
                path = item.get("path") or item.get("ref") or item.get("file")
                label = str(item.get("label") or item.get("emotion") or kind)
            rel = str(path or "").strip()
            if rel and rel.lower().endswith(".png"):
                out.append((label, rel))
    return out


def _png_face_ratio_and_size(face_mod: Any, abspath: str) -> Tuple[Optional[float], Optional[int]]:
    """(最大脸 bbox 占整图面积比, 短边像素)。检测器缺席/漏检 → ratio=None；读不到尺寸 → min_dim=None。"""
    size: Optional[Tuple[int, int]] = None
    try:
        from PIL import Image  # type: ignore
        with Image.open(abspath) as im:
            size = im.size
    except Exception:
        size = None
    if size is None:
        return None, None
    w, h = size
    min_dim = min(int(w), int(h)) if w and h else None
    ratio: Optional[float] = None
    if face_mod is not None and hasattr(face_mod, "cv2_face_boxes") and w and h:
        try:
            boxes = face_mod.cv2_face_boxes(abspath)
        except Exception:
            boxes = None
        if boxes:  # 非空=真检到脸；[]=检测器跑了但 0 脸（风格化脸常漏）→ 不据占比判
            bx = max(boxes, key=lambda b: int(b[2]) * int(b[3]))
            ratio = (int(bx[2]) * int(bx[3])) / float(int(w) * int(h))
    return ratio, min_dim


def audit_face_anchor_quality(root: Path, ep: str) -> Dict[str, Any]:
    """① 脸部锚信噪比门：对已落档的 face_anchor/表情/脸部特写参考，校验脸占比 + 裁切分辨率。
    核心/长线角色 findings=block，普通角色 warn。缺图不报（那是 gate/coverage 的事，本门只判**已存在图**的质量）。"""
    res: Dict[str, Any] = {"available": True, "findings": [], "notes": [], "checked": 0}
    try:
        data = json.loads((root / _registry_path()).read_text(encoding="utf-8"))
    except Exception:
        res["available"] = False
        res["notes"].append("identity_registry.json 缺失/损坏——脸部锚信噪比门跳过。")
        return res
    face_mod = _load_review_module("face_consistency")
    if face_mod is None or not hasattr(face_mod, "cv2_face_boxes"):
        res["notes"].append("cv2_face_boxes 不可用——脸占比项降级跳过，仅按分辨率判（装 opencv 后复检脸占比）。")
    for ch in (data.get("characters") or []):
        cid = str(ch.get("id") or "").strip()
        core = is_core_scope(str(ch.get("scope") or ""))
        for form in (ch.get("forms") or []):
            if not isinstance(form, Mapping):
                continue
            fm = str(form.get("form") or "").strip()
            for label, rel in _face_anchor_ref_items(form):
                abspath = rel if os.path.isabs(rel) else str(root / rel)
                if not os.path.isfile(abspath):
                    continue  # 缺图非本门职责
                res["checked"] += 1
                ratio, min_dim = _png_face_ratio_and_size(face_mod, abspath)
                reason = weak_face_anchor_reason(ratio, min_dim)
                if reason:
                    level = "block" if core else "warn"
                    code = "weak_face_anchor_core" if core else "weak_face_anchor"
                    res["findings"].append({
                        "level": level, "code": code,
                        "msg": f"脸部锚弱信噪比 {cid}/{fm}「{label}」（{rel}）：{reason}"
                               "——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写"
                               "（脸占 30–50%、≥1024px）后再放行。",
                        "asset": rel,
                    })
    return res


def _qc_inputs_fingerprint(root: Path, ep: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Best-effort content fingerprint of the files this QC verdict rests on.

    Stamps the prompt sources + every judged PNG so n2d-update can tell whether a
    later 出图 regen has made this report stale (fresh/stale) instead of trusting a
    report that predates the current images. Fully guarded — if the snapshot helper
    is unavailable, return None and n2d-update treats freshness as unknown (safe)."""
    try:
        lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
        if lib not in sys.path:
            sys.path.insert(0, lib)
        from skill_snapshot import artifact_fingerprint  # type: ignore
    except Exception:
        return None
    base = str(root)
    rels: Set[str] = {
        os.path.join("出图", ep, "prompt", "00_总览.md"),
        os.path.join("出图", ep, "prompt", "01_分镜出图.md"),
        os.path.join("出图", "共享", "identity_registry.json"),
        os.path.join("出图", "共享", "asset_registry.json"),
        os.path.join("生产数据", "image_qc", ep, "face_confirmations.json"),
        os.path.join("生产数据", "image_qc", ep, "prop_shape_confirmations.json"),
    }

    def _normalize_png_rel(value: str) -> str:
        rel = str(value or "").strip().replace("\\", "/")
        if not rel:
            return rel
        if os.path.isabs(rel):
            rel = os.path.relpath(rel, base).replace("\\", "/")
        if rel.startswith("图片/"):
            return f"出图/{ep}/{rel}"
        return rel

    def _walk(obj: Any, path: tuple[str, ...] = ()) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "png" and isinstance(v, str) and v.strip():
                    rel = _normalize_png_rel(v)
                    # face_reference_coverage.pending enumerates planned character PNGs
                    # before they exist. It is useful as a to-do list, but the
                    # freshness fingerprint must cover only evidence this QC
                    # actually judged; otherwise batch generation is blocked by
                    # not-yet-generated frames.
                    if rel.startswith(f"出图/{ep}/图片/") and not (root / rel).is_file():
                        continue
                    rels.add(rel)
                else:
                    _walk(v, path + (str(k),))
        elif isinstance(obj, list):
            for x in obj:
                _walk(x, path)

    _walk(payload)
    norm = {r if not os.path.isabs(r) else os.path.relpath(r, base) for r in rels}
    try:
        return artifact_fingerprint(base, norm)
    except Exception:
        return None


def run_qc(root: Path, ep: str, with_pixel: bool = True, strict_pixel: bool = False) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "kind": "n2d_image_qc", "version": 1, "root": str(root), "episode": ep,
        "checks": {}, "lint": {},
    }
    if with_pixel:
        with contextlib.redirect_stdout(sys.stderr):
            payload["checks"] = run_pixel_checks(root, ep)
            annotate_degraded_closeups(payload, root, ep)
            # ① 降级近景脸：拼并排对比图 + Haar 粗筛，落人审队列（stdout 噪声重定向到 stderr）。
            build_face_review_queue(payload, root, ep)
            # D 场景/道具/特效漂移：同样拼「资产参考 ↔ 本镜」并排图，落资产人审队列。
            build_asset_review_queue(payload, root, ep)
            # ③ 语义漂移信号（DINO/CLIP-I）：有已登记关键资产时，无嵌入后端会在 summarize/to_findings 升 hard；
            #    跑通后 palette 漏报但语义低 → warn 人判。
            sd = _load_sibling("semantic_drift")
            if sd is not None:
                try:
                    sdr = sd.analyze(root, ep, payload)
                    payload["semantic_drift"] = sdr
                except Exception as exc:
                    payload["semantic_drift"] = {"available": False, "notes": [f"semantic_drift 失败：{exc}"], "findings": []}
            # 契约像素兜底（④·色调/光位）：把 00_总览 契约的暖冷·明暗意图量到实际帧像素上对照——
            # 补「色调基线/光位锚 声称焊像素却只验文本誊抄」这道洞。纯 Pillow·默认环境可跑·WARN 人判。
            tl = _load_sibling("tone_light_contract")
            if tl is not None:
                try:
                    payload["tone_light_contract"] = tl.analyze(root, ep)
                except Exception as exc:
                    payload["tone_light_contract"] = {"available": False, "notes": [f"tone_light_contract 失败：{exc}"], "findings": []}
            # 契约像素兜底（④·景别阶梯）：storyboard 声明景别 × 实测脸占比对照——补「景别只查文本标签、不看 PNG 实际景别」。
            ssc = _load_sibling("shot_scale_contract")
            if ssc is not None:
                try:
                    payload["shot_scale_contract"] = ssc.analyze(root, ep)
                except Exception as exc:
                    payload["shot_scale_contract"] = {"available": False, "notes": [f"shot_scale_contract 失败：{exc}"], "findings": []}
            # 风格归属佐证（⑤·选定风格 vs 实际渲染）：以 style_contract.style_anchor 为基准，量本集帧的风格指纹
            # （饱和/对比/线条边缘）对照——补「风格名/风格禁忌只当存在性+负面词、出图后无正面归属机检」这道洞。
            # 纯 Pillow·默认环境可跑·WARN 人判·未登记锚则降级人判清单。
            sa = _load_sibling("style_attribution")
            if sa is not None:
                try:
                    payload["style_attribution"] = sa.analyze(root, ep)
                except Exception as exc:
                    payload["style_attribution"] = {"available": False, "notes": [f"style_attribution 失败：{exc}"], "findings": []}
    payload["lint"] = lint_prompts(root, ep)
    payload["artifact_namespace"] = audit_artifact_namespace(root, ep)
    # 高风险道具禁形/尺寸逐图复核：prompt/registry 只能约束未来生成，不能证明既有 PNG 没有禁形或尺寸漂移。
    # 这道门在 lint 之后跑，读取逐镜 PROP_xx 绑定和已落档 PNG；未确认则 summarize/to_findings 硬阻断。
    build_prop_shape_review_queue(payload, root, ep)
    # F 资产状态机校验（registry 级，与逐镜 prompt 无关）：状态回退/未知态=hard，其余 warn 并入 lint 管道，
    # 自由文本 lifecycle 的 info 提示只留在 asset_lifecycle 专段、不污染 lint。
    al = _load_sibling("asset_lifecycle")
    if al is not None:
        try:
            lc = al.validate_registry(root)
            for f in lc.get("findings", []):
                if f.get("level") in ("block", "warn"):
                    payload["lint"].setdefault("findings", []).append(
                        {"level": f["level"], "code": f["code"], "msg": f["msg"]})
            payload["asset_lifecycle"] = lc
        except Exception as exc:
            payload["asset_lifecycle"] = {"available": False, "notes": [f"asset_lifecycle 校验失败：{exc}"]}
    # ① 脸部锚信噪比门（registry 级，与逐镜 prompt 无关）：核心/长线弱脸锚 block，其余 warn，并入 lint 管道。
    fa = audit_face_anchor_quality(root, ep)
    for f in fa.get("findings", []):
        payload["lint"].setdefault("findings", []).append(
            {"level": f["level"], "code": f["code"], "msg": f["msg"]})
    payload["face_anchor_quality"] = fa
    # 承载角色脸锚（registry 级·后端无关·治定妆脸漂真因）：含具名角色脸的 VFX/海报/关系图资产
    # 必须有 ready 脸锚可注入，否则每镜无锚渲染新脸。runner spend 闸门只拦 codex/dreamina 出图路径，
    # 此处把同一铁律前移到落档机检，覆盖手工/其它后端/旧图。block 码进 HARD_LINT_CODES → hard_blocks。
    ci = audit_carried_identity_anchors(root)
    for f in ci.get("findings", []):
        if f.get("level") in ("block", "warn"):
            payload["lint"].setdefault("findings", []).append(
                {"level": f["level"], "code": f["code"], "msg": f["msg"]})
    payload["carried_identity_anchors"] = ci
    # 人物脸一致性铁律（A·face_policy）：含人脸资产定妆必须 faceless（像素核验 0 清晰脸）或
    # face_locked（折 owner/承载角色脸锚）——绝不放任自由生成脸（武器握持比例脸漂结构性真因）。
    fp = audit_asset_face_policy(root)
    for f in fp.get("findings", []):
        if f.get("level") in ("block", "warn"):
            payload["lint"].setdefault("findings", []).append(
                {"level": f["level"], "code": f["code"], "msg": f["msg"]})
    payload["asset_face_policy"] = fp
    # ④ VLM 语义判定（描述↔渲染图·opt-in）：关键注册角色/资产 VLM 判崩设定（剪裁/配饰/识别特征违反 canonical）
    #    → block；走专属 payload key（不塞 lint，避免被 lint_prompts 覆盖+不依赖 HARD_LINT_CODES），summarize/to_findings 直接读。
    #    无 N2D_VLM_CMD 后端 → available=False 整段跳过，绝不阻断默认无依赖产线。
    vv = _load_sibling("vlm_verify")
    if vv is not None:
        try:
            payload["vlm_consistency"] = vv.analyze(root, ep, payload)
        except Exception as exc:
            payload["vlm_consistency"] = {"available": False, "notes": [f"vlm_verify 失败：{exc}"],
                                          "block": 0, "findings": []}
    # VLM 设定核验没真正跑（未配置 N2D_VLM_CMD / 加载失败）但有注册关键角色/资产进了 QC：
    # 过去 available=False 整段静默空过——剪裁/配饰/识别特征(缺左腕疤、月白窄袖→交领)这类设定漂移没机检过。
    # 升一条 advisory warn（不硬拦无依赖产线，守"不强制装依赖"原则；production 由 gate 据精度/profile 决定升级）。
    _vlm = payload.get("vlm_consistency") or {}
    if _vlm.get("available") is not True:
        _checks = payload.get("checks") or {}
        if any((_checks.get(k) or {}).get("shots") for k in ("face", "scene", "multimodal")):
            payload.setdefault("lint", {}).setdefault("findings", []).append({
                "level": "warn", "code": "vlm_setting_check_skipped",
                "msg": "VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical "
                       "设定未机检，缺左腕疤、月白窄袖画成交领这类设定漂移可能漏过；正式定稿前在 full+VLM 环境复跑。"})
    # 人工确认只可覆盖当前 PNG 哈希匹配的 face warn/block 行；覆盖后再计算 face_reference_coverage，
    # 否则 coverage 会把已目检合格的侧脸/暗光/背身误报继续计为硬阻断。
    apply_face_confirmations(payload, root, ep)
    payload["face_reference_coverage"] = face_reference_coverage(payload, root, ep)
    payload["cross_episode_face_drift"] = cross_episode_face_drift(root, ep, payload)
    payload["prohibited_face_patch"] = prohibited_face_patch_outputs(root, ep)
    payload["face_anchor_lighting"] = face_anchor_lighting_audit(root, ep)
    payload["state_ledger"] = audit_state_ledger(root, ep)
    payload["summary"] = summarize(payload, strict_pixel=strict_pixel)
    payload["qc_environment"] = qc_environment(payload, with_pixel=with_pixel)
    payload["inputs_fingerprint"] = _qc_inputs_fingerprint(root, ep, payload)
    payload = json_safe(payload)
    out_dir = production_dir(root) / "image_qc" / ep
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"image_qc_{ep}.json"
    md_path = out_dir / f"image_qc_{ep}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(md_path)
    return payload


def _check_line(label: str, res: Dict[str, Any], cnt: Dict[str, int]) -> str:
    if not res or res.get("available") is False:
        note = "；".join(res.get("notes", [])) if res else "未跑"
        return f"- {label}: ⏭ 跳过（{note or '不可用'}）"
    flag = "🔴" if cnt["block"] else ("🟡" if cnt["warn"] else "🟢")
    return f"- {label}: {flag} block {cnt['block']} · warn {cnt['warn']}"


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    by = summary.get("by_check", {})
    checks = payload.get("checks", {})
    lines = [
        "# n2d Image QC（出图落档机检）",
        "",
        f"- episode: {payload['episode']}",
        f"- 总判定: **{summary.get('verdict', 'ok')}** · 硬阻断 {summary.get('hard_blocks', 0)}（必须修）"
        f" · 非阻断初筛 {summary.get('advisory', 0)}"
        f" · 视觉降级 {len(summary.get('unavailable_visual_checks') or [])}",
    ]
    env = payload.get("qc_environment", {}) or {}
    if env:
        lines.extend([
            f"- 机检能力: **{env.get('precision_level')}** · 当前解释器: `{env.get('python')}`",
            f"- 阶段跳转: **{env.get('jump_to_stage')}** · {env.get('jump_reason')}",
        ])
        missing = env.get("missing_or_degraded") or []
        if missing:
            lines.append(f"- 缺失/降级: {', '.join(str(x) for x in missing)}")
        if env.get("recommended_install"):
            lines.append(f"- 建议安装: {env.get('recommended_install')}")
    artifact_namespace = payload.get("artifact_namespace") or {}
    if artifact_namespace:
        stale = artifact_namespace.get("stale") or []
        mark = "🔴" if stale else "🟢"
        lines.extend([
            "",
            "## 本集图片命名空间（硬闸）",
            f"- {mark} 当前 prompt 声明目标 {artifact_namespace.get('declared_targets', 0)} 张；"
            f"未声明 live Clip PNG {len(stale)} 张",
        ])
        for item in stale:
            lines.append(f"  - 🔴 {item.get('path')}：{item.get('reason')}")
        for note in artifact_namespace.get("notes", []):
            lines.append(f"- note: {note}")
    lines.extend([
        "",
        "## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）",
        _check_line("崩脸 G1", checks.get("face"), by.get("face", {})),
        _check_line("发型 H1", checks.get("hair"), by.get("hair", {})),
        _check_line("服装 N1", checks.get("outfit"), by.get("outfit", {})),
        _check_line("场景 O2", checks.get("scene"), by.get("scene", {})),
        _check_line("道具/特效 P2", checks.get("multimodal"), by.get("multimodal", {})),
        _check_line("接缝接力", checks.get("seam"), by.get("seam", {})),
        _check_line("锚点门 N3", checks.get("anchors"), by.get("anchors", {})),
        "",
        "## 角色脸定妆比对覆盖（硬闸）",
    ])
    coverage = payload.get("face_reference_coverage") or {}
    if coverage:
        missing = coverage.get("missing") or []
        pending = coverage.get("pending") or []
        flag = "🔴" if missing else "🟢"
        lines.append(
            f"- {flag} 已落档角色图 required {coverage.get('required', 0)} · "
            f"covered {coverage.get('covered', 0)} · missing {len(missing)} · "
            f"pending {len(pending)} · precision {coverage.get('precision_level')}"
        )
        for s in missing:
            lines.append(f"  - 🔴 {s.get('label') or s.get('shot')} {s.get('png') or ''}：{s.get('reason')}")
        for s in coverage.get("unclassified", []):
            lines.append(f"  - 🟡 漏分类有脸镜 {s.get('shot')} {s.get('png') or ''}：未在 character_shots 清单，待人工确认是否角色镜（非阻断）")
        for note in coverage.get("notes", []):
            lines.append(f"- note: {note}")
        face_confirm = payload.get("face_manual_confirmations") or {}
        if face_confirm.get("applied"):
            lines.append(
                f"- 人工脸部确认: applied {face_confirm.get('applied')} · "
                f"确认文件 `{face_confirm.get('confirmation_path')}`"
            )
    else:
        lines.append("- ⏭ 未生成覆盖结果（旧版 image_qc 或未执行 lint）")
    drift = payload.get("cross_episode_face_drift") or {}
    drift_entries = drift.get("entries") or []
    if drift.get("available") and (drift_entries or drift.get("history_chars")):
        lines.extend(["", "## 跨集脸漂移趋势（B·治每集过floor但逐集偏离·advisory）"])
        if drift_entries:
            for e in drift_entries:
                icon = "🔴" if e.get("severity") == "high" else "🟡"
                tail = "（跌破绝对下限）" if e.get("below_abs_low") else ""
                lines.append(
                    f"- {icon} {e.get('char')}：{e.get('episode_from')}→{e.get('episode_to')} "
                    f"均值 {e.get('from_mean')}→{e.get('to_mean')}（掉幅 {e.get('drop')}）{tail}"
                )
            lines.append("- 处置：以基线集为准重审该角色定妆继承链，或确认是有意的成长态(evolution_profile)；趋势性掉幅在硬伤前就该收。")
        else:
            lines.append(f"- 🟢 已累积 {drift.get('history_chars')} 个角色历史，暂无趋势性漂移。")
    lines.extend([
        "",
        "## 本地贴脸修复禁用（硬闸）",
    ])
    prohibited = payload.get("prohibited_face_patch") or {}
    prohibited_outputs = prohibited.get("outputs") or []
    if prohibited_outputs:
        lines.append(f"- 🔴 {len(prohibited_outputs)} 张最新落档事件来自本地贴脸/换脸/裁脸贴回画面，不能作为最终图进 video。")
        lines.append("- 原则：embedding 分数只是证据，不是目标；不能为了过脸部 embedding QC 把定妆脸贴到镜头上。")
        for s in prohibited_outputs:
            lines.append(
                f"  - 🔴 {s.get('png')}：provider `{s.get('provider') or 'unknown'}`；"
                f"method `{s.get('method') or 'unknown'}`；event line {s.get('line')}"
            )
    else:
        lines.append("- 🟢 未发现最新落档事件来自本地贴脸修复。")
    lines.extend([
        "",
        "## 执行层 lint（逐镜 prompt）",
    ])
    lint = payload.get("lint", {})
    lcnt = by.get("lint", {})
    if not lint.get("available"):
        lines.append(f"- ⏭ 跳过（{'；'.join(lint.get('notes', [])) or '无 prompt'}）")
    else:
        flag = "🔴" if lcnt.get("block") else ("🟡" if lcnt.get("warn") else "🟢")
        lines.append(f"- {flag} {lint.get('shots_linted', 0)} 镜已 lint · block {lcnt.get('block', 0)} · warn {lcnt.get('warn', 0)}")
        for f in lint.get("findings", []):
            mark = "🔴" if f.get("level") == "block" else "🟡"
            lines.append(f"  - {mark} {f.get('msg')}")
    for note in lint.get("notes", []):
        lines.append(f"- note: {note}")
    review = payload.get("face_human_review") or []
    if review:
        lines.extend(["", "## 降级近景人审队列（无 insightface 时人眼判同人 ①）",
                      f"- {len(review)} 个近景脸需人审：开并排对比图『定妆主参考 ↔ 本镜脸』秒判同不同人"])
        for t in review:
            stitch = t.get("stitch") if t.get("stitched") else "(拼图未生成·缺 Pillow/参考图)"
            pn = f"；{t['priority_note']}" if t.get("priority_note") else ""
            lines.append(f"  - {t.get('shot')}（{t.get('char') or '?'}）：{stitch}{pn}")
    asset_review = payload.get("asset_human_review") or []
    if asset_review:
        lines.extend(["", "## 场景/道具/特效漂移人审队列（D）",
                      f"- {len(asset_review)} 个资产漂移镜需人审：开并排对比图『资产参考 ↔ 本镜』判是否漂"])
        for t in asset_review:
            stitch = t.get("stitch") if t.get("stitched") else "(拼图未生成·缺 Pillow/参考图)"
            lines.append(f"  - {t.get('kind')} {t.get('shot')}（{t.get('asset') or '?'}）：{stitch}")
    prop_shape = payload.get("prop_shape_review") or {}
    prop_targets = prop_shape.get("targets") or []
    if prop_targets:
        pending = [t for t in prop_targets if not t.get("confirmed")]
        lines.extend(["", "## 高风险道具禁形/尺寸逐图复核（硬闸）",
                      f"- total {len(prop_targets)} · pending {len(pending)} · confirmed {len(prop_targets) - len(pending)}",
                      f"- 确认文件: `{prop_shape.get('confirmation_path')}`"])
        for t in prop_targets:
            mark = "🟢" if t.get("confirmed") else "🔴"
            stitch = t.get("stitch") if t.get("stitched") else "(拼图未生成·缺 Pillow/参考图)"
            terms = "、".join(str(x) for x in (t.get("must_not_have") or [])[:8])
            lines.append(
                f"  - {mark} {t.get('shot')} {t.get('png')}（{t.get('asset')} {t.get('asset_name')}）"
                f" 禁形={terms}{'；尺寸=' + str(t.get('scale')) if t.get('scale') else ''}；{stitch}"
            )
    lines.append("")
    lines.append("落档判定：**verdict=block** → 有硬阻断（崩脸/纯文生图/非法 CHAR_id），必须修复后重跑；"
                 "**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；"
                 "**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。"
                 "初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。")
    return "\n".join(lines) + "\n"


def mark_finalized(root: Path, target: str, value: bool = True, auto_pin: bool = True) -> Dict[str, Any]:
    """把共享定妆/资产的机器可读 finalize 真值 `self_check_passed` 置位（补 `00_索引.md` 人读 ✅）。

    target：角色 `CHAR_xx/形态` 或单形态时裸 `CHAR_xx`；资产 `LOC/PROP/WEAPON/OUTFIT/VFX_xx`。
    人工/AI 过落档自检后调用，让 `gate` 的 `check_referenced_assets_finalized` 能机检"引用必须 finalized"。

    `auto_pin=True`（默认）：对**角色 form** 落档自检时顺带把 front 主参考的 sha256 钉进 `anchor_sha`
    （等价于自动 `--pin-anchor`），治"锚点静默漂移"结构根因——过自检的脸即刻被锚点指纹保护，gate
    `check_anchor_fingerprints` 立即生效，不再依赖人手记得单独跑一遍 pin。front 锚点图缺失时优雅跳过
    （不阻断落档，回执提示补图后手动 pin）。`auto_pin=False`（`--no-auto-pin`）保留旧的纯 opt-in 行为。
    资产（LOC/PROP/WEAPON/…）无锚点概念，不受 auto_pin 影响。"""
    root = Path(root)
    t = str(target or "").strip()
    if t.split("/")[0].startswith(("LOC_", "PROP_", "WEAPON_", "OUTFIT_", "VFX_")):
        p = root / "出图" / "共享" / "asset_registry.json"
        try:
            reg = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            return {"ok": False, "msg": f"读 asset_registry 失败：{exc}"}
        for a in (reg.get("assets") or []):
            if isinstance(a, dict) and str(a.get("id") or "").strip() == t:
                a["self_check_passed"] = bool(value)
                p.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return {"ok": True, "target": t, "value": bool(value), "msg": f"{t}.self_check_passed={value}"}
        return {"ok": False, "msg": f"asset_registry 无资产 `{t}`"}
    # 角色 form
    p = root / "出图" / "共享" / "identity_registry.json"
    try:
        reg = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "msg": f"读 identity_registry 失败：{exc}"}
    cid, _, form_name = t.partition("/")
    for c in (reg.get("characters") or []):
        if str(c.get("id") or "").strip() != cid:
            continue
        forms = c.get("forms") or []
        if form_name:
            matches = [fm for fm in forms if str(fm.get("form") or "").strip() == form_name]
        elif len(forms) == 1:
            matches = forms
        else:
            return {"ok": False, "msg": f"`{cid}` 有多个形态，请指明 `CHAR_xx/形态`"}
        if not matches:
            return {"ok": False, "msg": f"`{cid}` 无形态 `{form_name}`"}
        auto_pinned: List[str] = []
        anchor_missing = False
        for fm in matches:
            fm["self_check_passed"] = bool(value)
            if value:
                _mark_front_reference_ready(root, fm)
            if value and auto_pin:
                rel = _anchor_relpath(fm)
                sha = _sha256_file(root / rel) if rel else None
                if sha:
                    fm["anchor_sha"] = sha
                    auto_pinned.append(sha)
                else:
                    anchor_missing = True
        p.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        msg = f"{t}.self_check_passed={value}"
        if value and auto_pin:
            if auto_pinned:
                msg += f" + anchor_sha 自动钉死={auto_pinned[0][:12]}…"
            elif anchor_missing:
                msg += "（front 锚点图缺失，未自动钉死——补图后跑 --pin-anchor）"
        return {"ok": True, "target": t, "value": bool(value),
                "auto_pinned": bool(auto_pinned), "msg": msg}
    return {"ok": False, "msg": f"identity_registry 无角色 `{cid}`"}


def _mark_front_reference_ready(root: Path, form: Dict[str, Any]) -> bool:
    """Promote reviewed base-view slots from review_pending to ready.

    `mark_finalized` is the structured human/AI review receipt for a shared
    character form.  Keeping generated base views such as
    `reference_group.side.status=review_pending` after this receipt makes the
    registry contradict itself and leaves image_preflight blocked even though
    the view image was accepted.
    """
    changed = False
    base_view_keys = ("front", "three_quarter", "side", "back", "half_body", "turnaround")

    def promote_slot(container: Dict[str, Any], slot_key: str) -> bool:
        slot = container.get(slot_key)
        review = {
            "status": "accepted",
            "reviewer": "image_qc.mark_finalized",
            "reason": f"shared {slot_key} reference passed finalized review",
            "reviewed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        if isinstance(slot, dict):
            rel = str(slot.get("path") or "").strip()
            if rel and (root / rel).is_file():
                slot["status"] = "ready"
                slot["human_review"] = dict(review)
                return True
        elif isinstance(slot, str) and slot and (root / slot).is_file():
            container[slot_key] = {
                "path": slot,
                "status": "ready",
                "human_review": dict(review),
            }
            return True
        return False

    for container_key, path_prefix in (
        ("reference_group", ()),
        ("reference_atlas", ("base_views",)),
    ):
        node: Any = form.get(container_key)
        if not isinstance(node, dict):
            continue
        for key in path_prefix:
            node = node.get(key)
            if not isinstance(node, dict):
                break
        else:
            for slot_key in base_view_keys:
                changed = promote_slot(node, slot_key) or changed
    return changed


def _anchor_relpath(form: Mapping[str, Any]) -> str:
    """form 锚点定妆图（front 主参考）项目相对路径；缺 front 回退第一张可用视图。
    与 gate.py `_form_anchor_relpath` 同口径。"""
    rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}

    def item_path(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, Mapping):
            path = value.get("path")
            return path.strip() if isinstance(path, str) else ""
        if isinstance(value, list):
            for item in value:
                path = item_path(item)
                if path:
                    return path
        return ""

    front = rg.get("front")
    front_path = item_path(front)
    if front_path:
        return front_path
    for v in rg.values():
        path = item_path(v)
        if path:
            return path
    return ""


def _sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def pin_anchor(root: Path, target: str, unpin: bool = False) -> Dict[str, Any]:
    """把共享定妆锚点（form 的 front 主参考定妆图）的内容 sha256 钉进 identity_registry 的 `anchor_sha`。

    钉死后 `gate check_anchor_fingerprints` 会校验磁盘 sha 不变；锚点被悄改/丢失即 BLOCK，治跨集脸漂的
    结构根因（锚点静默漂移）。target：`CHAR_xx/形态`（多形态必须指明）或单形态时裸 `CHAR_xx`。
    `unpin=True` 删除 anchor_sha（停用钉死）。出锚点定妆图、过自检后调用。"""
    root = Path(root)
    t = str(target or "").strip()
    p = root / "出图" / "共享" / "identity_registry.json"
    try:
        reg = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "msg": f"读 identity_registry 失败：{exc}"}
    cid, _, form_name = t.partition("/")
    for c in (reg.get("characters") or []):
        if str(c.get("id") or "").strip() != cid:
            continue
        forms = c.get("forms") or []
        if form_name:
            matches = [fm for fm in forms if str(fm.get("form") or "").strip() == form_name]
        elif len(forms) == 1:
            matches = forms
        else:
            return {"ok": False, "msg": f"`{cid}` 有多个形态，请指明 `CHAR_xx/形态`"}
        if not matches:
            return {"ok": False, "msg": f"`{cid}` 无形态 `{form_name}`"}
        for fm in matches:
            if unpin:
                fm.pop("anchor_sha", None)
                continue
            rel = _anchor_relpath(fm)
            if not rel:
                return {"ok": False, "msg": f"`{t}` 的 reference_group 缺 front 主参考，无法钉锚点"}
            sha = _sha256_file(root / rel)
            if not sha:
                return {"ok": False, "msg": f"锚点定妆图不存在或不可读：{rel}（先出 front 定妆照）"}
            fm["anchor_sha"] = sha
        p.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if unpin:
            return {"ok": True, "target": t, "msg": f"{t}.anchor_sha 已移除（停用钉死）"}
        return {"ok": True, "target": t, "msg": f"{t}.anchor_sha={matches[0].get('anchor_sha', '')[:12]}…（{_anchor_relpath(matches[0])}）"}
    return {"ok": False, "msg": f"identity_registry 无角色 `{cid}`"}


def finalize_expression(root: Path, target: str, value: bool = True) -> Dict[str, Any]:
    """把表情库锚（form 的某情绪脸部特写）落档为跨集共享锁定资产：置 self_check_passed 并钉 anchor_sha。

    target=`CHAR_xx/形态/情绪`（单形态时可 `CHAR_xx//情绪`）。form 的 `expression_anchors` 是
    `[{emotion, path, self_check_passed, anchor_sha}]`；缺该情绪条目时报错（先在 registry 登记 path）。
    `value=False` 标脏（gate 引用即 block）。让 `gate check_expression_anchors` 能机检同情绪近景跨集同源。"""
    root = Path(root)
    t = str(target or "").strip()
    parts = t.split("/")
    if len(parts) != 3:
        return {"ok": False, "msg": "target 需为 `CHAR_xx/形态/情绪`（单形态用 `CHAR_xx//情绪`）"}
    cid, form_name, emotion = (p.strip() for p in parts)
    if not cid or not emotion:
        return {"ok": False, "msg": "缺角色 ID 或情绪"}
    p = root / "出图" / "共享" / "identity_registry.json"
    try:
        reg = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "msg": f"读 identity_registry 失败：{exc}"}
    for c in (reg.get("characters") or []):
        if str(c.get("id") or "").strip() != cid:
            continue
        forms = c.get("forms") or []
        if form_name:
            matches = [fm for fm in forms if str(fm.get("form") or "").strip() == form_name]
        elif len(forms) == 1:
            matches = forms
        else:
            return {"ok": False, "msg": f"`{cid}` 有多个形态，请指明 `CHAR_xx/形态/情绪`"}
        if not matches:
            return {"ok": False, "msg": f"`{cid}` 无形态 `{form_name}`"}
        fm = matches[0]
        expression_sources: List[Tuple[str, List[Dict[str, Any]]]] = []
        anchors = fm.get("expression_anchors")
        if isinstance(anchors, list):
            expression_sources.append(("expression_anchors", [a for a in anchors if isinstance(a, dict)]))
        rg = fm.get("reference_group") if isinstance(fm.get("reference_group"), dict) else {}
        rg_exprs = rg.get("expressions") if isinstance(rg, dict) else None
        if isinstance(rg_exprs, list):
            expression_sources.append(("reference_group.expressions", [a for a in rg_exprs if isinstance(a, dict)]))
        atlas = fm.get("reference_atlas") if isinstance(fm.get("reference_atlas"), dict) else {}
        atlas_exprs = atlas.get("expression_refs") if isinstance(atlas, dict) else None
        if isinstance(atlas_exprs, list):
            expression_sources.append(("reference_atlas.expression_refs", [a for a in atlas_exprs if isinstance(a, dict)]))
        if not expression_sources:
            return {"ok": False, "msg": f"`{cid}/{form_name}` 未登记 expression_anchors / reference_group.expressions / reference_atlas.expression_refs；先在 registry 加 `{{emotion, path}}`"}
        hit = None
        anchor_source = ""
        for source, anchors_list in expression_sources:
            hit = next((a for a in anchors_list if str(a.get("emotion") or "").strip() == emotion), None)
            if hit is not None:
                anchor_source = source
                break
        if hit is None:
            return {"ok": False, "msg": f"`{cid}/{form_name}` 无情绪锚 `{emotion}`；先登记其 path"}
        if value:
            rel = str(hit.get("path") or "").strip()
            sha = _sha256_file(root / rel) if rel else None
            if not sha:
                return {"ok": False, "msg": f"情绪锚图不存在或不可读：{rel}（先出该情绪脸部特写）"}
            matching = [
                a
                for _, anchors_list in expression_sources
                for a in anchors_list
                if str(a.get("emotion") or "").strip() == emotion
            ]
            for item in matching:
                item["self_check_passed"] = True
                item["anchor_sha"] = sha
                item["status"] = "ready"
                human_review = item.get("human_review") if isinstance(item.get("human_review"), dict) else {}
                human_review.update({
                    "status": "pass",
                    "reviewed_by": "image_qc --finalize-expr",
                    "reviewed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "reason": f"expression anchor finalized from {anchor_source}",
                })
                item["human_review"] = human_review
        else:
            for item in [
                a
                for _, anchors_list in expression_sources
                for a in anchors_list
                if str(a.get("emotion") or "").strip() == emotion
            ]:
                item["self_check_passed"] = False
                item.pop("anchor_sha", None)
                item["status"] = "review_pending"
        p.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "target": t, "value": bool(value),
                "msg": f"{t}.self_check_passed={value}" + (f" anchor_sha={hit.get('anchor_sha','')[:12]}…" if value else "")}
    return {"ok": False, "msg": f"identity_registry 无角色 `{cid}`"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--mark-finalized", metavar="TARGET",
                    help="把共享定妆/资产 `self_check_passed` 置 true（过落档自检后调用）：CHAR_xx/形态 或 LOC/PROP/WEAPON/OUTFIT/VFX_xx")
    ap.add_argument("--unfinalize", action="store_true",
                    help="与 --mark-finalized 连用：改置 false（标记脏定妆，gate 引用即 block）")
    ap.add_argument("--no-auto-pin", action="store_true",
                    help="与 --mark-finalized 连用：落档时不自动钉死 anchor_sha（保留旧的纯 opt-in pin 行为）")
    ap.add_argument("--pin-anchor", metavar="TARGET",
                    help="把共享定妆锚点 front 主参考的内容 sha256 钉进 identity_registry `anchor_sha`（gate 校验锚点不被悄改）：CHAR_xx/形态")
    ap.add_argument("--unpin-anchor", action="store_true",
                    help="与 --pin-anchor 连用：删除 anchor_sha（停用锚点钉死）")
    ap.add_argument("--finalize-expr", metavar="TARGET",
                    help="把表情库锚落档为跨集共享锁定（self_check_passed=true + 钉 sha）：CHAR_xx/形态/情绪")
    ap.add_argument("--unfinalize-expr", action="store_true",
                    help="与 --finalize-expr 连用：标脏（self_check_passed=false，gate 引用即 block）")
    ap.add_argument("--record-faceless", action="store_true",
                    help="对 faceless 资产跑 verify_faceless，把结果+png_sha256 写回 asset_registry 当持久机器证据（registry 级·需 insightface）")
    ap.add_argument("--no-pixel", action="store_true", help="只跑 prompt lint，不跑像素机检")
    ap.add_argument("--json", action="store_true", help="打印机器可读 payload")
    ap.add_argument("--findings", action="store_true",
                    help="打印与 gate.py 同形的 findings 列表（dashboard gate --stage image_preflight/image 接入用）")
    ap.add_argument("--regen-list", action="store_true",
                    help="打印「不能用、要重生成」的镜列表（普通落档 QC；warn 不默认进重出）")
    ap.add_argument("--affected-shots", action="store_true",
                    help="打印 regen 镜的 `--affected-shot Clip_NN ...` 串（直接喂 n2d-batch；无则空）")
    ap.add_argument("--strict", action="store_true",
                    help="严审刷新：block/warn/降级命中都进入候选重出清单，供 n2d-update 使用")
    ap.add_argument("--strict-pixel", action="store_true",
                    help="把像素机检 block（服装换装/场景换景/道具特效漂移）升为 hard → verdict=block（默认 off 保留宽松判定）")
    ap.add_argument("--face-report", action="store_true",
                    help="只输出当前 face warn/block 人工复核队列与最小重出范围，不重跑完整 QC")
    ap.add_argument("--face-confirm-ok", metavar="SELECTOR",
                    help="把指定 face warn/block 复核项标 ok；SELECTOR=all/pending 或 char/png/shot/id 列表。需人工已看过图片")
    ap.add_argument("--face-reviewer", default="manual",
                    help="与 --face-confirm-ok 连用，写入 reviewer 字段")
    ap.add_argument("--face-reason", default="",
                    help="与 --face-confirm-ok 连用，写入人工确认原因")
    ap.add_argument("--prop-shape-report", action="store_true",
                    help="只输出高风险 PROP 禁形/尺寸逐图复核队列与最小重出范围，不重跑完整 QC")
    ap.add_argument("--prop-shape-write-skeleton", action="store_true",
                    help="把当前高风险 PROP 复核队列写入 prop_shape_confirmations.json，verdict=review（不放行）")
    ap.add_argument("--prop-shape-confirm-ok", metavar="SELECTOR",
                    help="把指定高风险 PROP 复核项标 ok；SELECTOR=all/pending 或 asset/png/shot/id 列表。需人工已看过并排图")
    ap.add_argument("--prop-shape-reviewer", default="manual",
                    help="与 --prop-shape-confirm-ok 连用，写入 reviewer 字段")
    ap.add_argument("--prop-shape-reason", default="",
                    help="与 --prop-shape-confirm-ok 连用，写入人工确认原因")
    ap.add_argument("--prop-shape-vlm-confirm", action="store_true",
                    help="用 N2D_VLM_CMD 对 pending 逐图判定；高置信 match 才写 ok，其余保留复核/重出")
    ap.add_argument("--prop-shape-vlm-floor", type=float, default=0.6,
                    help="VLM 写 ok 的最低置信度；默认 0.6")
    ap.add_argument("--prop-shape-affected-shots", action="store_true",
                    help="只打印 pending 高风险 PROP 的 `--affected-shot ...` 串，便于 n2d-batch 最小重出")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    if ns.mark_finalized:
        r = mark_finalized(root, ns.mark_finalized, value=not ns.unfinalize, auto_pin=not ns.no_auto_pin)
        print(("✅ " if r.get("ok") else "⛔ ") + r.get("msg", ""))
        return 0 if r.get("ok") else 1
    if ns.pin_anchor:
        r = pin_anchor(root, ns.pin_anchor, unpin=ns.unpin_anchor)
        print(("✅ " if r.get("ok") else "⛔ ") + r.get("msg", ""))
        return 0 if r.get("ok") else 1
    if ns.finalize_expr:
        r = finalize_expression(root, ns.finalize_expr, value=not ns.unfinalize_expr)
        print(("✅ " if r.get("ok") else "⛔ ") + r.get("msg", ""))
        return 0 if r.get("ok") else 1
    if ns.record_faceless:
        r = record_faceless_evidence(root)
        print(json.dumps(r, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if r.get("available") else 1
    if not ns.episode:
        ap.error("episode 必填（除非用 --mark-finalized / --pin-anchor / --finalize-expr / --record-faceless 写 registry）")
    if ns.face_report:
        report = face_confirmation_report(root, ns.episode)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.face_confirm_ok:
        res = confirm_face_targets(
            root,
            ns.episode,
            ns.face_confirm_ok,
            reviewer=ns.face_reviewer,
            reason=ns.face_reason,
        )
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if res.get("ok") else 1
    if ns.prop_shape_report or ns.prop_shape_affected_shots:
        report = prop_shape_review_report(root, ns.episode, build_stitches=True)
        if ns.prop_shape_affected_shots:
            print(report.get("rerun_plan", {}).get("command", ""))
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.prop_shape_write_skeleton:
        res = write_prop_shape_skeleton(root, ns.episode)
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if ns.prop_shape_confirm_ok:
        res = confirm_prop_shape_targets(
            root,
            ns.episode,
            ns.prop_shape_confirm_ok,
            reviewer=ns.prop_shape_reviewer,
            reason=ns.prop_shape_reason,
        )
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if res.get("ok") else 1
    if ns.prop_shape_vlm_confirm:
        res = vlm_confirm_prop_shape_targets(
            root,
            ns.episode,
            block_floor=ns.prop_shape_vlm_floor,
            reviewer="vlm",
        )
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if res.get("ok") else 2
    payload = run_qc(root, ns.episode, with_pixel=not ns.no_pixel, strict_pixel=ns.strict_pixel)
    regen = to_strict_regen_list(payload) if ns.strict else to_regen_list(payload)
    if ns.affected_shots:
        print(" ".join(f"--affected-shot {s['shot']}" for s in regen))
    elif ns.regen_list:
        print(json.dumps(regen, ensure_ascii=False))
    elif ns.findings:
        print(json.dumps(to_findings(payload), ensure_ascii=False))
    elif ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(payload["markdown_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
