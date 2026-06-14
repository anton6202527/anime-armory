#!/usr/bin/env python3
"""出图落档机检 image_qc —— 把 n2d-review 家族的一致性机检**前移到出图落档**。

设计同 n2d-video 的 video_qc.py：复用 n2d-review/scripts 的已校准纯函数与阈值
（单一真值源，本文件不重复定义阈值），让一致性漂移在**刚出完一批图、还没继续**的
最便宜的点被机检初筛，而不是等整集出完进 n2d-review 审片才发现 → 省大量返工。

四项像素机检（全部读 `出图/第N集/图片/*.png`，Pillow-or-fallback，缺料必须在报告中明示，不臆造通过）：
- 崩脸 G1   ← face_consistency.analyze（insightface 优先，无则 Pillow 查分辨率/清晰度）
- 服装 N1   ← outfit_consistency.analyze（Pillow 调色板直方图）
- 场景 O2   ← scene_consistency.analyze（Pillow dHash 结构 + 色调指纹离群）
- 接缝接力  ← temporal_consistency.seam_analyze（镜头N_end.png vs 下镜首帧 dHash）
- 锚点门 N3 ← face_consistency.audit_anchors（定妆主参考恰好 1 张清晰正脸）

一项执行层 lint（读 `出图/第N集/prompt/01_分镜出图.md` 逐镜块，治人工誊抄漏）：
- 角色镜是否有参考图块（禁纯文生图）/ 视线方向字段 / 锚点句 / 身份锁定句
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

完整视觉质检推荐在可装重依赖的 conda env 跑：Pillow + cv2 + insightface + onnxruntime + buffalo_l model。
报告会写 `qc_environment.precision_level=full|degraded|none`，
缺依赖时应停在 image/image_qc setup 补装并重跑，不应直接跳 video。

测试（从本目录跑）：
  cd skills/n2d-image/scripts && python3 -m pytest test_image_qc.py
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

# 同家族复用：一致性机检的阈值与数学只在 n2d-review/scripts 维护一份。
REVIEW_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "n2d-review" / "scripts"

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
    LOC/PROP/OUTFIT/VFX）。缺/损坏 → None（lint 跳过资产合法性，记 note，不误报）。

    name_to_id 把每个资产的 `name` 和 reference_group 文件名 stem（剥 `定妆_`/`_侧`等）映到其 id，
    用来抓「用了 `定妆_<资产>` 却没绑 `PROP_xx/LOC_xx`」——执行端缺 id 就取不到 constraints/drift_forbidden。
    asset_registry 只含非角色资产（场景/道具/服装/特效），角色在 identity_registry，二者不串。
    """
    path = root / "出图" / "共享" / "asset_registry.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    ids: Set[str] = set()
    name_to_id: Dict[str, str] = {}
    prefix_of: Dict[str, str] = {}
    for a in (data.get("assets") or []):
        aid = str(a.get("id") or "").strip()
        if not aid:
            continue
        ids.add(aid)
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
    return {"ids": ids, "name_to_id": name_to_id, "prefix_of": prefix_of}


# 资产 id 引用（场景/道具/服装/特效）+ 定妆资产名（用于抓"用了定妆却没绑 id"）。
ASSET_ID_RE = re.compile(r"`?((?:LOC|PROP|OUTFIT|VFX)_[A-Za-z0-9_]+)`?")
DEFINING_ASSET_RE = re.compile(r"定妆_([^\s`，。、）)/]+)")
_ASSET_NAME_SUFFIX_RE = re.compile(r"_(侧|半身|全身|背|三视图|四视图|设定表|脸部特写|表情)$")


def _lint_asset_binding(label: str, body: str, asset_index: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
    """资产 id lint（A，所有镜都跑，不限角色镜）：
    - 写了 `LOC/PROP/OUTFIT/VFX_xx` 但 registry 没有 → block `unknown_asset_id`（对称 unknown_char_id）；
    - 用了 `定妆_<已登记资产>` 却没绑对应 id → warn `asset_ref_without_id`（执行端取不到 constraints/drift_forbidden）。
    纯函数·可测。asset_index=None（registry 缺）→ 跳过。"""
    findings: List[Dict[str, str]] = []
    if not asset_index:
        return findings
    text = str(body or "")
    ids: Set[str] = asset_index.get("ids") or set()
    name_to_id: Dict[str, str] = asset_index.get("name_to_id") or {}
    prefix_of: Dict[str, str] = asset_index.get("prefix_of") or {}
    body_ids = set(ASSET_ID_RE.findall(text))
    for rid in sorted(body_ids):
        if rid not in ids:
            findings.append({"level": "block", "code": "unknown_asset_id",
                             "msg": f"{label}：资产引用 `{rid}` 在 asset_registry 不存在（场景/道具/服装/特效 id 写错或未登记）"})
    flagged: Set[str] = set()
    for raw in DEFINING_ASSET_RE.findall(text):
        stem = raw[:-4] if raw.endswith(".png") else raw
        name = _ASSET_NAME_SUFFIX_RE.sub("", stem)
        aid = name_to_id.get(name) or name_to_id.get(stem) or name_to_id.get(raw)
        if aid and aid not in body_ids and aid not in flagged:
            flagged.add(aid)
            kind = {"LOC_": "场景", "PROP_": "道具", "OUTFIT_": "服装", "VFX_": "特效"}.get(prefix_of.get(aid, ""), "资产")
            findings.append({"level": "warn", "code": "asset_ref_without_id",
                             "msg": f"{label}：用了 `定妆_{raw}`({kind}) 但未绑 `{aid}`；写上资产 id 执行端才会自动取 "
                                    "reference_group/constraints/drift_forbidden（防场景/道具/特效跨镜漂移）"})
    return findings


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
                "display": display,
                "ref_count": ref_count,  # 该形态 reference_group 的多角度参考张数（C4：喂全角度组给多参考后端）
                "reference_stems": reference_stems,
                "strong_aliases": strong_aliases,
                "weak_aliases": weak_aliases,
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
IDENTITY_REF_RE = re.compile(r"`?(CHAR_[A-Za-z0-9_]+\*?(?:/[^`\s，；、*]+)?\*?)`?")
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
    return bool(stem.startswith("定妆_") or "/共享/" in s or "出图/共享/" in s)


def _extract_target_png(body: str) -> Optional[str]:
    """从逐镜 prompt 提取本镜落档 PNG。优先目标/落档行，排除定妆/共享参考图。"""
    fallback: List[str] = []
    for line in str(body or "").splitlines():
        tokens = [p for p in _png_tokens(line) if not _is_reference_png(p)]
        if not tokens:
            continue
        if any(marker in line for marker in TARGET_PNG_LINE_MARKERS):
            return tokens[0]
        fallback.extend(tokens)
    return fallback[0] if fallback else None


def character_shot_manifest(block: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """逐镜 prompt → 角色镜覆盖清单项。

    该清单是后续 full 精度脸部参考覆盖闸门的输入，不依赖像素引擎。
    """
    body = block.get("body", "")
    label = block.get("label", "")
    id_refs = [normalize_identity_ref(ref) for ref in IDENTITY_REF_RE.findall(body)]
    if not _is_character_shot_body(body, id_refs):
        return None
    png = _extract_target_png(body)
    shot = _shot_key(png) or _shot_key(label) or label
    return {
        "label": label,
        "shot": shot,
        "png": png,
        "identity_refs": sorted(set(id_refs)),
    }


def _declares_no_tail_frame(body: str) -> bool:
    text = str(body or "")
    return bool(
        re.search(r"尾帧[：:]\s*[`]*无[`]*", text)
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


# 近景大表情表情库 gate（④ 治表情镜脸漂）：近景/特写/反打 + 强情绪的角色镜，若 prompt
# 未引用同源『表情库 expressions / 脸部特写』参考，AI 会为大表情重画整张脸 → 表情镜脸漂。
# 软约束（warn，非 hard）：表情库是降风险强手段，但主参考+锚点句仍可能够用，故标 warn 交人判，
# 不当 hard 拦（与本文件 hard-block 仅留高精度无歧义硬伤的哲学一致；不进 HARD_LINT_CODES）。
STRONG_EMOTION_MARKERS = (
    "哭", "泣", "落泪", "含泪", "泪", "怒", "愤", "暴怒", "狂怒", "震惊", "惊恐", "恐惧",
    "狂喜", "大笑", "狂笑", "嘶吼", "咆哮", "嚎", "痛苦", "崩溃", "狰狞", "扭曲", "癫狂",
    "失控", "绝望", "悲恸", "惊愕", "狂怒",
)
EXPRESSION_LIB_MARKERS = ("表情库", "expressions", "脸部特写", "表情_", "_表情", "情绪库", "微表情参考")
# 近景识别：仅认中文近景词 + 作为整 token 的英文景别码，避免 "CU" 子串误命中正文。
_CLOSEUP_LINT_RE = re.compile(r"特写|近景|反打|过肩|ECU|BCU|MCU|(?<![A-Za-z])CU(?![A-Za-z])")


def _has_strong_emotion(body: str) -> bool:
    return any(m in str(body or "") for m in STRONG_EMOTION_MARKERS)


def _references_expression_lib(body: str) -> bool:
    return any(m in str(body or "") for m in EXPRESSION_LIB_MARKERS)


def _lint_closeup_expression_lib(label: str, body: str) -> List[Dict[str, str]]:
    """近景大表情表情库 gate（仅角色镜调用）：近景/特写/反打 + 强情绪角色镜须引用同源表情库/
    脸部特写参考，否则大表情让 AI 自由重画整张脸 → 表情镜脸漂。warn 级·纯函数·可测。"""
    text = str(body or "")
    if not _CLOSEUP_LINT_RE.search(text):
        return []
    if not _has_strong_emotion(text):
        return []
    if _references_expression_lib(text):
        return []
    return [{"level": "warn", "code": "no_expression_lib_ref",
             "msg": f"{label}：近景/特写大表情角色镜未引用『表情库 expressions / 脸部特写参考』"
                    "（大表情会让 AI 重画整张脸 → 表情镜脸漂；建议引同源表情库，首尾双帧只插值）"}]


# C3 多主体空间绑定：同框 ≥2 角色需逐角色绑画面站位，否则多主体易串脸。
SPATIAL_POSITION_MARKERS = ("画左", "画右", "画中", "靠左", "靠右", "左侧", "右侧", "居中",
                            "前景", "后景", "背景", "中景", "近端", "远端", "左", "右",
                            "left", "right", "center", "foreground", "background")
BLOCKING_FIELD_MARKERS = ("blocking", "站位", "走位", "机位站位")


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


def _outfit_groups_in_text(text: str) -> Set[str]:
    found: Set[str] = set()
    src = str(text or "")
    for group, tokens in OUTFIT_TOKEN_GROUPS.items():
        if any(token and token in src for token in tokens):
            found.add(group)
    return found


def _form_advertises_outfit_group(form: Dict[str, Any], group: str) -> bool:
    tokens = OUTFIT_TOKEN_GROUPS.get(group) or ()
    aliases = sorted((form.get("strong_aliases") or set()) | (form.get("weak_aliases") or set()))
    haystack = " ".join([
        str(form.get("form") or ""),
        str(form.get("asset_key") or ""),
        str(form.get("display") or ""),
        " ".join(str(s) for s in form.get("reference_stems") or []),
        " ".join(str(a) for a in aliases),
    ])
    return any(token and token in haystack for token in tokens)


def _lint_outfit_form_binding(label: str, body: str, id_refs: Sequence[str],
                              registry_forms: Optional[List[Dict[str, Any]]]) -> List[Dict[str, str]]:
    """Single-character costume/form guard.

    If a shot explicitly asks for a durable outfit form (红衣/白衣/战甲...) it must bind
    the matching CHAR_xx/形态, not a nearby identity state with another costume.
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
    groups = _outfit_groups_in_text(_positive_prompt_text(body))
    if not groups:
        return []

    by_key = {str(form.get("key") or ""): form for form in registry_forms}
    findings: List[Dict[str, str]] = []
    for rid in exact_refs:
        form = by_key.get(rid)
        if not form:
            continue
        for group in sorted(groups):
            if _form_advertises_outfit_group(form, group):
                continue
            findings.append({
                "level": "block",
                "code": "outfit_form_mismatch",
                "msg": (
                    f"{label}：正向 prompt 写了「{group}」类服饰/形态，但资产身份注册层绑定 `{rid}` "
                    f"（asset_key={form.get('asset_key') or '-'}）没有对应服饰定妆。"
                    "换装/形态变体必须新建独立 `CHAR_xx/形态` 和 reference_group，禁止复用其它服饰状态参考。"
                ),
            })
    return findings


def _lint_multi_subject_spatial_binding(label: str, body: str,
                                        id_refs: Sequence[str]) -> List[Dict[str, str]]:
    """多人同框防串脸（C3·生成端预防）：≥2 具名角色同框却没声明逐角色空间站位时 warn。

    2026 研究：多主体身份混淆随参考数上升（DreamO/UMO）。Seedream4.5 / Nano Banana2 已支持多主体
    空间区域绑定——把每个角色绑到画面位置（画左/画右/前景）可在生成端按位锁主体、显著降串脸。
    这里只在出图前 lint「多人同框是否声明了空间站位」，缺则 warn（不阻断，交人补 blocking）。纯函数·可测。"""
    if len(_distinct_char_bases(id_refs)) < 2:
        return []
    low = str(body or "").lower()
    if any(m.lower() in low for m in BLOCKING_FIELD_MARKERS):
        return []
    if sum(1 for m in SPATIAL_POSITION_MARKERS if m.lower() in low) >= 2:
        return []
    return [{"level": "warn", "code": "multi_person_no_spatial_binding",
             "msg": f"{label}：多人同框但未声明逐角色空间站位（blocking / 画左·画右 / 前后景）"
                    "——多主体易串脸，给每角色绑画面位置喂多主体后端可在生成端按位锁主体防串脸"}]


def _lint_native_multiref_coverage(label: str, body: str, id_refs: Sequence[str],
                                   form_ref_counts: Optional[Dict[str, int]]) -> List[Dict[str, str]]:
    """多角度参考喂养充分性（C4·advisory）：定妆库有多角度组、本镜却只引用了 1 张时提示喂全组。

    2026 原生多参考已 table-stakes（Seedream≤14 / 可灵 Elements≤4 张锁主体）。定妆库建了正/侧/背
    多角度组，却只把正面喂进去 = 没吃满后端锁主体能力。只在 registry 确有多角度组(≥3)时才 info，
    不噪；单参考后端可忽略。纯函数·可测。"""
    if not form_ref_counts:
        return []
    avail = max((form_ref_counts.get(b, 0) for b in _distinct_char_bases(id_refs)), default=0)
    if avail < 3:
        return []  # 没有多角度组可喂，免谈
    refd = len({t for t in _png_tokens(body) if "定妆_" in t})
    if refd >= min(avail, 3):
        return []  # 已喂≥3张（或全部）→ 充分
    return [{"level": "info", "code": "native_multiref_underfed",
             "msg": f"{label}：定妆库有 {avail} 张多角度参考，本镜参考图块只引用了 {refd} 张——"
                    "多参考后端(Seedream≤14 / 可灵Elements≤4)喂全角度组(正/侧/背)锁主体更稳；单参考后端可忽略"}]


def lint_shot_block(
    block: Dict[str, str],
    valid_ids: Optional[Set[str]],
    registry_forms: Optional[List[Dict[str, Any]]] = None,
    asset_index: Optional[Dict[str, Any]] = None,
    form_ref_counts: Optional[Dict[str, int]] = None,
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
    findings.extend(_lint_tail_identity_handoff(label, body, registry_forms))
    findings.extend(_lint_tail_relay_method(label, body))
    findings.extend(_lint_closeup_expression_lib(label, body))
    findings.extend(_lint_multi_subject_spatial_binding(label, body, id_refs))      # C3
    findings.extend(_lint_native_multiref_coverage(label, body, id_refs, form_ref_counts))  # C4
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
    asset_index = load_asset_index(root)
    if asset_index is None:
        res["notes"].append("asset_registry.json 缺失/损坏——跳过 LOC/PROP/OUTFIT/VFX_xx 资产 id 合法性校验。")
    blocks = split_shot_blocks(text)
    for blk in blocks:
        res["shots_linted"] += 1
        manifest = character_shot_manifest(blk)
        if manifest:
            res["character_shots"].append(manifest)
        res["findings"].extend(lint_shot_block(blk, valid_ids, registry_forms, asset_index, form_ref_counts))
    return res


# ── 像素机检（复用 n2d-review 纯函数） ──────────────────────────────────────────

def run_pixel_checks(root: Path, ep: str) -> Dict[str, Any]:
    """崩脸 G1 / 服装 N1 / 场景 O2 / 接缝接力 / 锚点门 N3，复用 n2d-review analyze。
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
            checks["seam"] = tc.seam_analyze(r, ep)
        except Exception as exc:
            checks["seam"] = {"available": False, "notes": [f"temporal_consistency.seam_analyze 失败：{exc}"]}
    else:
        checks["seam"] = {"available": False, "notes": ["temporal_consistency 不可用——接缝机检跳过。"]}

    return checks


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
    "lifecycle_regression",
    "lifecycle_unknown_from_state",
    "lifecycle_unknown_to_state",
)
VISUAL_CHECK_LABELS = {
    "face": "崩脸 G1",
    "outfit": "服装 N1",
    "scene": "场景 O2",
    "multimodal": "道具/特效 P2",
    "seam": "接缝接力",
    "anchors": "锚点门 N3",
}
VISUAL_CHECK_DIMS = {
    "face": "character_consistency",
    "outfit": "outfit_consistency",
    "scene": "scene_consistency",
    "multimodal": "asset_consistency",
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


# 近景景别标记（与 n2d-video/video_qc.CLOSEUP_MARKERS 同义；ad-* 不跨 import，本 skill 独立留一份）。
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


def annotate_degraded_closeups(payload: Dict[str, Any], root: Path, ep: str) -> None:
    """降级精度近景铁律：insightface 缺席时崩脸机检降到 Pillow（只验图损坏/分辨率，不验真脸相似度）。
    近景/特写/反打镜在降级下放行 = 脸是否同人无人核验——给这些 face shot 打 `degraded_face` + `closeup`，
    summarize / to_findings 据此把「降级近景」升为 hard block（普通景别仍只 review，不误杀远景）。"""
    face = (payload.get("checks") or {}).get("face") or {}
    if face.get("mode") not in FACE_DEGRADED_MODES:
        return
    closeups = closeup_shot_nums(root, ep)
    for s in face.get("shots", []):
        m = _REGEN_CLIP_RE.search(str(s.get("png") or ""))
        idx = int(m.group(1)) if m else None
        s["degraded_face"] = True
        s["closeup"] = bool(idx is not None and idx in closeups)


def _degraded_closeup_face_shots(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """降级精度下、景别为近景、且基础质量未单独 block 的 face shot（这些是「无法验同人的近景脸」）。"""
    face = (payload.get("checks") or {}).get("face") or {}
    return [s for s in face.get("shots", [])
            if s.get("degraded_face") and s.get("closeup") and s.get("verdict") != "block"]


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


def audit_state_ledger(root: Path, ep: str) -> Dict[str, Any]:
    """状态账本启发式（advisory）：扫 storyboard 角色状态演进 + 本集出图 prompt 找累积状态关键词；
    命中且无 visual_state_ledger.json → advise=True（建议跑 visual_state_manager --audit）。
    永不 block——只把「简单/复杂」的人脑豁免决策挪到机检提醒。读不到源 → available=False。纯函数·可测。"""
    res: Dict[str, Any] = {"available": False, "markers": [], "ledger_present": False, "advise": False}
    texts: List[str] = []
    try:
        sb = json.loads((Path(root) / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
        vc = sb.get("visual_contract") if isinstance(sb.get("visual_contract"), dict) else {}
        texts.append(str(vc.get("角色状态演进", "")))
        res["available"] = True
    except Exception:
        pass
    try:
        texts.append((Path(root) / "出图" / ep / "prompt" / "01_分镜出图.md").read_text(encoding="utf-8"))
        res["available"] = True
    except Exception:
        pass
    if not res["available"]:
        return res
    blob = "\n".join(texts)
    res["markers"] = sorted({m for m in CUMULATIVE_STATE_MARKERS if m in blob})
    res["ledger_present"] = _ledger_present(root)
    res["advise"] = bool(res["markers"]) and not res["ledger_present"]
    return res


# ── ① 降级近景人审队列：拼『定妆主参考 ↔ 本镜脸』并排图，让人眼在 degraded 精度下秒判同人 ──

def face_review_targets(payload: Dict[str, Any], root: Path, ep: str) -> List[Dict[str, Any]]:
    """降级近景脸 → 人审拼图目标（纯路径计算，不写盘·可测）。

    每项 {shot, png, png_abs, char, ref, stitch}：ref=该角色定妆主参考，stitch=并排图落点。
    """
    out: List[Dict[str, Any]] = []
    for s in _degraded_closeup_face_shots(payload):
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
        primary = ((a.get("reference_group") or {}).get("primary") or "").strip()
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
    for row in (face.get("shots") or []):
        if not isinstance(row, dict):
            continue
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
            rows = rows_by_shot.get(str(rec.get("shot") or ""))
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


def summarize(payload: Dict[str, Any]) -> Dict[str, Any]:
    """汇总各项机检 + lint，区分 hard（必须修）与 advisory（非阻断初筛）。"""
    hard = advisory = 0
    rows_by_check: Dict[str, Dict[str, int]] = {}
    for key, shots_key in (("face", "shots"), ("outfit", "shots"),
                           ("scene", "shots"), ("multimodal", "shots"), ("seam", "seams")):
        res = payload.get("checks", {}).get(key) or {}
        cnt = count_verdicts(res.get(shots_key) or [])
        rows_by_check[key] = cnt
        if key in HARD_CHECKS:
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
    none: no pixel checks were requested, or every core visual check is unavailable.
    """
    checks = payload.get("checks", {}) or {}
    unavailable = unavailable_visual_checks(payload)
    core_checks = {"face", "outfit", "scene", "seam"}
    face_mode = str((checks.get("face") or {}).get("mode") or "")
    degraded_face = face_mode in FACE_DEGRADED_MODES
    missing: List[str] = []

    if not with_pixel:
        level = "none"
        missing.append("pixel checks disabled by --no-pixel")
    elif core_checks.issubset(set(unavailable)):
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
        reason = "视觉质检为降级结果，正式进 video 前需补依赖重跑或逐项人审确认"
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
    for key in unavailable_visual_checks(payload):
        res = checks.get(key) or {}
        note = "；".join(res.get("notes", [])) if isinstance(res, dict) else ""
        out.append(_qc_finding(
            "warn",
            VISUAL_CHECK_DIMS.get(key, "image_qc"),
            None,
            f"{VISUAL_CHECK_LABELS.get(key, key)} 未执行：{note or '视觉机检不可用'}；本轮图片一致性为降级判定，需补依赖后重跑或人工复核。",
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
    for s in (payload.get("prohibited_face_patch") or {}).get("outputs", []):
        out.append(_qc_finding(
            "block",
            "character_consistency",
            s.get("png"),
            f"{PROHIBITED_FACE_PATCH_LABEL}：{s.get('png')} 最新落档事件来自 `{s.get('provider') or 'unknown'}`"
            f" / `{s.get('method') or 'unknown'}`。embedding 分数不是合格目标，不能用裁脸/贴脸/换脸"
            "把定妆照盖到镜头上骗过 QC；必须回 n2d-image 用真实重抽或官方 image2image 派生替换。",
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
    # 服装 N1 / 场景 O2 / 锚点门 N3（advisory）：即便 block 也降 warn 作为非阻断初筛入账
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
            out.append(_qc_finding("warn", "asset_consistency", s.get("png"),
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
    # 状态账本启发式（advisory·info，永不翻 verdict）：累积状态出现却无 ledger → 提醒建账本
    sl = payload.get("state_ledger") or {}
    if sl.get("advise"):
        out.append(_qc_finding(
            "info", "state_continuity", None,
            f"本集出现累积状态关键词（{'/'.join(sl.get('markers', []))[:60]}）但无 visual_state_ledger.json——"
            "状态可能跨镜/跨集演进，建议跑 `python3 skills/n2d-image/scripts/visual_state_manager.py <作品根> --audit` "
            "建账本锁状态（简单剧确认后可忽略；本提示不阻断）。"))
    return out


# ── 重生成清单（update 刷新模式用） ───────────────────────────────────────────

_REGEN_CLIP_RE = re.compile(r"(?:Clip[_\-\s]?|镜头)(\d+)")


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
            add(s.get("png"), f"strict:服装一致性 {s.get('verdict')}")
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


def run_qc(root: Path, ep: str, with_pixel: bool = True) -> Dict[str, Any]:
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
    payload["lint"] = lint_prompts(root, ep)
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
    payload["face_reference_coverage"] = face_reference_coverage(payload, root, ep)
    payload["prohibited_face_patch"] = prohibited_face_patch_outputs(root, ep)
    payload["state_ledger"] = audit_state_ledger(root, ep)
    payload["summary"] = summarize(payload)
    payload["qc_environment"] = qc_environment(payload, with_pixel=with_pixel)
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
    lines.extend([
        "",
        "## 一致性机检（复用 n2d-review 阈值，单一真值源；崩脸=硬阻断，其余=非阻断初筛）",
        _check_line("崩脸 G1", checks.get("face"), by.get("face", {})),
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
    else:
        lines.append("- ⏭ 未生成覆盖结果（旧版 image_qc 或未执行 lint）")
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
    lines.append("")
    lines.append("落档判定：**verdict=block** → 有硬阻断（崩脸/纯文生图/非法 CHAR_id），必须修复后重跑；"
                 "**verdict=review** → 只有非阻断初筛时不挡 video；若是视觉机检降级/依赖缺失，按阶段跳转先补依赖或复核；"
                 "**verdict=ok** → 放行。本地贴脸/换脸/裁脸贴回画面是独立硬禁项，不能靠 embedding 分数洗白。"
                 "初筛项是像素直方图/dHash 机检初筛，非硬失败（同 video_qc 哲学）。")
    return "\n".join(lines) + "\n"


def mark_finalized(root: Path, target: str, value: bool = True) -> Dict[str, Any]:
    """把共享定妆/资产的机器可读 finalize 真值 `self_check_passed` 置位（补 `00_索引.md` 人读 ✅）。

    target：角色 `CHAR_xx/形态` 或单形态时裸 `CHAR_xx`；资产 `LOC/PROP/OUTFIT/VFX_xx`。
    人工/AI 过落档自检后调用，让 `gate` 的 `check_referenced_assets_finalized` 能机检"引用必须 finalized"。"""
    root = Path(root)
    t = str(target or "").strip()
    if t.split("/")[0].startswith(("LOC_", "PROP_", "OUTFIT_", "VFX_")):
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
        for fm in matches:
            fm["self_check_passed"] = bool(value)
        p.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"ok": True, "target": t, "value": bool(value), "msg": f"{t}.self_check_passed={value}"}
    return {"ok": False, "msg": f"identity_registry 无角色 `{cid}`"}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--mark-finalized", metavar="TARGET",
                    help="把共享定妆/资产 `self_check_passed` 置 true（过落档自检后调用）：CHAR_xx/形态 或 LOC/PROP/OUTFIT/VFX_xx")
    ap.add_argument("--unfinalize", action="store_true",
                    help="与 --mark-finalized 连用：改置 false（标记脏定妆，gate 引用即 block）")
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
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    if ns.mark_finalized:
        r = mark_finalized(root, ns.mark_finalized, value=not ns.unfinalize)
        print(("✅ " if r.get("ok") else "⛔ ") + r.get("msg", ""))
        return 0 if r.get("ok") else 1
    if not ns.episode:
        ap.error("episode 必填（除非用 --mark-finalized 写 registry）")
    payload = run_qc(root, ns.episode, with_pixel=not ns.no_pixel)
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
