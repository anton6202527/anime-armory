#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 出图前·逐镜参考处方 reference_planner（一致性轴的**事前**层）。

为什么存在：
    `product_qc.py` 是**事后**的——图已经出完（钱已经花了）才量产品/logo/品牌色漂没漂。
    ad 线缺的是**事前**：出图前按「这一镜相对定妆照变了多少」× 「所选后端真实够得着哪一档」，
    开出"该喂哪些参考图 + 要不要控制网 + 要不要升档"的处方。

治什么根因：
    单张定妆照对 AI 只是个「固定板式」，身份判别细节不足；一旦换景别/角度/光线/表情/包装角度，
    模型就在新条件下**重画**，逐镜累积成漂移。广告线的致命处在于——**产品才是最严格的"角色"**：
    包装文字/logo/品牌色漂了整片报废、重抽花真钱。而现状 `plan_prompts.py` 的 `reference_paths()`
    只是把 registry 里**静态登记**的 reference_images 原样列出：不看这一镜变化量，也不看后端能力。
    本脚本就是补上那层处方（与 `product_qc.py` 的事后机检互补·升档口径同源 `ad/_lib/image_backend_adapter`）。

广告特有加权（**别按通用漫剧版理解**）：
    `PROD_*` / `BRAND_*` 的变化量权重被放大（PRODUCT_DELTA_MULTIPLIER），参考预算下限更高、
    升档阈值更低——产品镜比 CHAR_/LOC_ 更激进是**故意的**。产品镜识别复用同目录 sibling
    `product_qc.product_shots()`（含「产品语义镜逃逸拦截」：storyboard 忘写 assets 也按语义纳管），
    不另抄一套语义表以免两处漂移。

诚实边界（缺料一律明示降级，绝不臆造通过）：
    - **advisory，不是门**：这是"审"不是"闸"。变化量是脆弱的关键词启发式，默认 **exit 0**；
      只有 `--strict` 且 `summary.block>0` 才 exit 1。JSON 里的 severity=block 供未来 gate 接线用，
      且只发给**确定性**缺口（结构化 ID 没登记 / 登记了却没参考图），启发式判定一律 ≤ warn。
    - 缺 storyboard / 缺 registry → 报告里 `inputs.*.available=false` + finding，**不抛异常崩溃**。
    - 后端认不出 → 保守 profile（只有 reference、预算 1）+ `backend.known=false`，不猜能力。
    - 所有阈值是模块级常量 + `thresholds.provenance="internal-heuristic·confidence=low"`——
      内部启发式，**不冒充行业标准**。
    - registry fallback 顺序：**`设定库/asset_registry.json` → `出图/共享/asset_registry.json`**
      （与 `plan_prompts.run()` 一致；仓内 5 个消费方顺序不统一，本脚本显式选前者优先——
      `设定库/` 是人写的源，`出图/共享/` 是 plan_prompts 落的副本）。

产物：`生产数据/ad_reference_plan.json` + `.md`（原子写：同盘 temp + os.replace）。
     findings 用 **`msg`** 不是 `message`（对齐 `ad-craft/scripts/gate.py` 的 finding schema）。

用法（**广告不拆集，粒度是"镜头 shot"，无集/话参数**）：
    python3 reference_planner.py <作品根> [--write] [--json] [--strict]

测试（从本目录跑）：
    cd skills/ad-image/scripts && python3 -m pytest test_reference_planner.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# 同目录 sibling（同属 ad-image/scripts）：复用产品语义纳管与 registry 消费，避免两套表漂移。
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import plan_prompts  # noqa: E402
import product_qc  # noqa: E402

# ad 线自己的 _lib（本线内，非跨线 import）。
_AD_LIB = Path(__file__).resolve().parents[2] / "ad" / "_lib"
if str(_AD_LIB) not in sys.path:
    sys.path.insert(0, str(_AD_LIB))
import image_backend_adapter as adapter  # noqa: E402
import settings as ad_settings  # noqa: E402

SCHEMA_VERSION = 1
KIND = "ad_reference_plan"
PROVENANCE = "internal-heuristic·confidence=low"

# ── 变化量权重（模块级常量·**内部启发式**，非行业标准） ──────────────────────────
# provenance: internal-heuristic·confidence=low
# 来源：ad-image/SKILL.md「产品定妆 = 最严一致性」+ 常见 AI 生图失效模式（近景/极端角度暴露
# 判别细节、包装文字与 logo 是最易崩处）。权重只用来排序「哪镜更该多喂参考」，不是物理量。
DELTA_WEIGHTS: Dict[str, float] = {
    "closeup": 2.0,                    # 近景/特写：定妆照的板式细节被放大，模型最爱重画。
    "wide_full_frame": 1.0,            # 远景/全景：主体变小，身份细节被压没。
    "extreme_angle": 2.0,              # 极端角度：定妆照没有的视角 = 模型只能靠猜。
    "strong_emotion": 1.0,             # 强表情：只对人脸有意义，产品镜基本不触发。
    "outfit_or_packaging_change": 2.0,  # 换装/换包装：锁脸锁不住领型；锁产品锁不住新包装版式。
    "lighting_change": 1.0,            # 光线变化：广告线品牌色被环境光染偏的主因。
    "action_motion": 1.0,              # 手持/倾倒/开箱等动作：产品形变高发。
    "multi_asset_frame": 1.0,          # 多资产同框：注意力被摊薄，易串特征。
    "text_surface": 2.0,               # 包装文字/logo/UI 文字露出（仅产品/品牌资产计入）。
}
# 广告特有：产品/品牌资产的变化量放大——产品漂了整片报废，宁可多喂参考也不省这点输入。
PRODUCT_DELTA_MULTIPLIER = 1.5
# 「大变化量」判定阈：产品/品牌线更低（更容易被判为大变化 → 更早升档）。
BIG_DELTA_SCORE = 3.0
PRODUCT_BIG_DELTA_SCORE = 2.0
# 参考张数下限：产品/品牌比 CHAR_/LOC_ 更激进（单张定妆照对产品身份**必然不够**）。
MIN_REFERENCES: Dict[str, int] = {
    "default": 1,
    "big_delta": 2,
    "product": 2,
    "product_big_delta": 3,
}

_PRODUCTISH = (adapter.ASSET_KIND_PRODUCT, adapter.ASSET_KIND_BRAND)

# ── 变化量抽取（从 shot 文本 + 结构化字段）·脆弱启发式，判定只配 warn/info ──────────
CLOSEUP_RE = re.compile(r"特写|近景|微距|大特|ECU|BCU|\bCU\b|close-?up|macro", re.I)
WIDE_RE = re.compile(r"远景|大远景|全景|大全|全身|wide shot|\bWS\b|\bEWS\b|establishing", re.I)
ANGLE_RE = re.compile(r"俯视|仰视|鸟瞰|顶视|大俯|大仰|极端角度|低角度|荷兰角|dutch|top-?down|worm", re.I)
EMOTION_RE = re.compile(r"大笑|微笑|哭|泪|惊讶|震惊|皱眉|怒|狂喜|表情|情绪|愁|痛", re.I)
CHANGE_RE = re.compile(r"换装|换衣|换包装|新包装|限定版|新版本|不同服装|不同包装|礼盒|repack|new package", re.I)
LIGHT_RE = re.compile(r"逆光|夜景|夜晚|霓虹|强反光|高光|暗调|低照度|烛光|色光|彩光|阴影|顶光|侧光|backlit|neon", re.I)
ACTION_RE = re.compile(r"手持|拿起|倾倒|倒出|开箱|拆封|使用|挤压|滑动|点击|抛|旋转|摇|动作|运动|pour|unbox", re.I)
# 文字面：只对产品/品牌资产计入（包装文字/logo/UI/CTA/end card 是 AI 生图最易崩处）。
TEXT_SURFACE_RE = re.compile(r"包装文字|文案|标签|logo|界面|\bUI\b|屏幕|slogan|\bCTA\b|end ?card|片尾|二维码|扫码", re.I)

_SHOT_TEXT_KEYS = (
    "scene", "shot", "frame", "prompt", "desc", "description", "product_lock",
    "camera", "lighting", "light", "光位", "景别", "镜头", "subtitle", "vo", "note",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def shot_text(shot: Mapping[str, Any]) -> str:
    """参与变化量判定的镜头文本（结构化字段扁平化）。纯函数·可测。"""
    parts: List[str] = []
    for key in _SHOT_TEXT_KEYS:
        value = shot.get(key) if isinstance(shot, Mapping) else None
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, (list, tuple)):
            parts.extend(str(v) for v in value)
        elif isinstance(value, Mapping):
            parts.extend(f"{k}={v}" for k, v in value.items())
    return " ".join(p for p in parts if p)


def variation_deltas(shot: Mapping[str, Any], asset_kind: str, multi_asset: bool) -> List[str]:
    """单镜单资产相对定妆照的变化量标签。**关键词启发式**（confidence=low）。纯函数·可测。"""
    text = shot_text(shot)
    deltas: List[str] = []
    if CLOSEUP_RE.search(text) or str(shot.get("shot_size") or "") in ("特写", "近景", "CU", "ECU"):
        deltas.append("closeup")
    if WIDE_RE.search(text):
        deltas.append("wide_full_frame")
    if ANGLE_RE.search(text):
        deltas.append("extreme_angle")
    if asset_kind == adapter.ASSET_KIND_CHARACTER and EMOTION_RE.search(text):
        deltas.append("strong_emotion")
    if CHANGE_RE.search(text):
        deltas.append("outfit_or_packaging_change")
    if LIGHT_RE.search(text):
        deltas.append("lighting_change")
    if ACTION_RE.search(text):
        deltas.append("action_motion")
    if multi_asset:
        deltas.append("multi_asset_frame")
    if asset_kind in _PRODUCTISH and TEXT_SURFACE_RE.search(text):
        deltas.append("text_surface")
    return deltas


def delta_score(deltas: Sequence[str], asset_kind: str) -> float:
    """变化量总分。产品/品牌乘 PRODUCT_DELTA_MULTIPLIER（广告特有加权）。纯函数·可测。"""
    score = sum(DELTA_WEIGHTS.get(d, 0.0) for d in deltas)
    if asset_kind in _PRODUCTISH:
        score *= PRODUCT_DELTA_MULTIPLIER
    return round(score, 2)


def is_big_delta(score: float, asset_kind: str) -> bool:
    """产品/品牌用更低的阈（更早判为大变化 → 更早升档）。纯函数·可测。"""
    threshold = PRODUCT_BIG_DELTA_SCORE if asset_kind in _PRODUCTISH else BIG_DELTA_SCORE
    return score >= threshold


def min_references_for(asset_kind: str, big_delta: bool) -> int:
    """本镜本资产至少该喂几张参考。产品/品牌下限更高。纯函数·可测。"""
    if asset_kind in _PRODUCTISH:
        return MIN_REFERENCES["product_big_delta"] if big_delta else MIN_REFERENCES["product"]
    return MIN_REFERENCES["big_delta"] if big_delta else MIN_REFERENCES["default"]


def recommended_tier_for(asset_kind: str, big_delta: bool) -> str:
    """本镜本资产**建议**达到的一致性档位（不看后端；后端能不能够得着由 adapter 回答）。

    产品/品牌更激进：平时就要多参考，大变化直接建议第②档原生主体库
    （ad-image/SKILL.md：「产品/logo 用后端原生主体库或多参考最稳」）。纯函数·可测。
    """
    if asset_kind in _PRODUCTISH:
        return adapter.TIER_SUBJECT_LIBRARY if big_delta else adapter.TIER_DIRECTED_REFERENCE
    if asset_kind == adapter.ASSET_KIND_CHARACTER:
        return adapter.TIER_DIRECTED_REFERENCE if big_delta else adapter.TIER_SHARED_KIT
    return adapter.TIER_SHARED_KIT


def plan_controls(profile: Mapping[str, Any], deltas: Sequence[str], asset_kind: str) -> List[Dict[str, Any]]:
    """按变化量提控制网/保护区需求，并**如实标注后端该能力是否未知**。纯函数·可测。"""
    controls: List[Dict[str, Any]] = []
    if asset_kind in _PRODUCTISH and ("closeup" in deltas or "extreme_angle" in deltas):
        controls.append({
            "type": "controlnet_structure",
            "state": adapter.capability_state(profile, adapter.CAP_CONTROLNET),
            "reason": "产品近景/极端角度：包装轮廓与比例最易被重画，能用结构控制网就锁边缘。",
        })
    if asset_kind in _PRODUCTISH and "text_surface" in deltas:
        controls.append({
            "type": "logo_protect_mask",
            "state": adapter.capability_state(profile, adapter.CAP_MASK_INPAINT),
            "reason": "本镜露包装文字/logo/UI：优先用 mask 保护区限制重绘范围（注意：真 logo 贴图属 ad-compose，"
                      "不得用本地贴图伪造出图阶段一致性）。",
        })
    return controls


# ── 资产 ID 抽取 ─────────────────────────────────────────────────────────────
_CHAR_RE = re.compile(r"\bCHAR_[A-Za-z0-9_]*\b")
_LOC_RE = re.compile(r"\bLOC_[A-Za-z0-9_]*\b")
_PROP_RE = re.compile(r"\bPROP_[A-Za-z0-9_]*\b")


def _ids_by_regex(shot: Mapping[str, Any], pattern: re.Pattern) -> List[str]:
    ids = set()
    assets = shot.get("assets") if isinstance(shot, Mapping) else None
    if isinstance(assets, Mapping):
        ids.update(str(k) for k, v in assets.items() if v and pattern.fullmatch(str(k)))
    elif isinstance(assets, (list, tuple)):
        ids.update(str(a) for a in assets if pattern.fullmatch(str(a)))
    ids.update(pattern.findall(shot_text(shot)))
    return sorted(ids)


def shot_asset_ids(shot: Mapping[str, Any]) -> List[str]:
    """一镜涉及的全部资产 ID，**产品/品牌优先**（参考预算按这个顺序分配）。纯函数·可测。

    PROD_/BRAND_ 复用 sibling `product_qc` 的抽取器，保证与产品机检同口径。
    """
    ordered: List[str] = []
    for group in (product_qc.product_asset_ids(shot), product_qc.brand_asset_ids(shot),
                  _ids_by_regex(shot, _CHAR_RE), _ids_by_regex(shot, _LOC_RE),
                  _ids_by_regex(shot, _PROP_RE)):
        for aid in group:
            if aid not in ordered:
                ordered.append(aid)
    return ordered


# ── 参考预算分配（产品优先·溢出显式记账，不静默吞参考） ──────────────────────────

def allocate_references(asset_refs: Sequence[Tuple[str, Sequence[str]]], limit: int) -> Dict[str, Any]:
    """把各资产的候选参考图按后端上限分配：**每个资产先保底一张**（产品/品牌在最前，
    所以后端预算紧时先保产品），再轮转补足。溢出的显式记进 `dropped`。纯函数·可测。

    asset_refs: [(asset_id, [path, ...]), ...]，顺序即优先级。
    """
    limit = max(0, int(limit))
    selected: List[Dict[str, str]] = []
    seen: set = set()
    queues: List[Tuple[str, List[str]]] = [(aid, [p for p in paths]) for aid, paths in asset_refs]
    dropped: List[Dict[str, str]] = []

    # 第一轮：每个资产保底一张。
    for aid, paths in queues:
        while paths and paths[0] in seen:
            paths.pop(0)
        if not paths:
            continue
        if len(selected) < limit:
            path = paths.pop(0)
            selected.append({"asset_id": aid, "path": path})
            seen.add(path)
    # 第二轮起：轮转补足到上限。
    progressed = True
    while len(selected) < limit and progressed:
        progressed = False
        for aid, paths in queues:
            while paths and paths[0] in seen:
                paths.pop(0)
            if paths and len(selected) < limit:
                path = paths.pop(0)
                selected.append({"asset_id": aid, "path": path})
                seen.add(path)
                progressed = True
    # 没塞进去的显式记账。
    for aid, paths in queues:
        for path in paths:
            if path not in seen:
                dropped.append({"asset_id": aid, "path": path})
                seen.add(path)
    requested = len(selected) + len(dropped)
    return {"limit": limit, "requested": requested, "selected": selected,
            "selected_count": len(selected), "dropped": dropped}


# ── IO ───────────────────────────────────────────────────────────────────────

def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def _atomic_write(path: Path, text: str) -> None:
    """同盘 temp + os.replace：写一半被打断也不会留下半个报告。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def resolve_registry(root: Path) -> Tuple[Dict[str, Any], Optional[str]]:
    """registry fallback 顺序：设定库/ → 出图/共享/（与 plan_prompts.run() 一致·见文件头）。"""
    for rel in ("设定库/asset_registry.json", "出图/共享/asset_registry.json"):
        data = load_json(root / rel)
        if isinstance(data, Mapping) and data:
            return dict(data), rel
    return {}, None


def finding(severity: str, code: str, msg: str, shot: Optional[str] = None,
            **extra: Any) -> Dict[str, Any]:
    """ad gate 的 finding schema：`msg`（不是 message）——见 ad-craft/scripts/gate.py。"""
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    if shot:
        out["shot"] = shot
    out.update(extra)
    return out


def _reference_exists(root: Path, rel: str) -> bool:
    path = Path(rel)
    return (path if path.is_absolute() else root / path).is_file()


# ── 主装配 ───────────────────────────────────────────────────────────────────

def build_plan(root: Path) -> Dict[str, Any]:
    """出图前逐镜参考处方。缺料只降级不抛异常。"""
    root = Path(root).resolve()
    storyboard_rel = "脚本/storyboard.json"
    storyboard = load_json(root / storyboard_rel, {}) or {}
    registry, registry_rel = resolve_registry(root)

    image_model = ad_settings.get_setting(str(root), "生图模型", "")
    image_channel = ad_settings.get_setting(str(root), "生图渠道", "")
    consistency = ad_settings.get_setting(str(root), "一致性增强", "")
    profile = adapter.profile_for(image_model, image_channel)

    findings: List[Dict[str, Any]] = []
    inputs = {
        "storyboard": {"path": storyboard_rel, "available": bool(storyboard)},
        "asset_registry": {"path": registry_rel or "设定库/asset_registry.json",
                           "available": bool(registry),
                           "fallback_order": ["设定库/asset_registry.json", "出图/共享/asset_registry.json"]},
        "settings": {"path": "_设置.md",
                     "生图模型": image_model, "生图渠道": image_channel, "一致性增强": consistency},
    }

    if not storyboard:
        findings.append(finding(
            "warn", "storyboard_unavailable",
            f"缺 {storyboard_rel}（或不可解析）：无镜头可规划，参考处方降级为空——先跑 ad-script 出分镜再规划。"))
    if not registry:
        findings.append(finding(
            "warn", "registry_unavailable",
            "缺 设定库/asset_registry.json 与 出图/共享/asset_registry.json：无法知道任何资产登记了哪些参考图，"
            "本报告只能给变化量，不能给参考处方——先建三层定妆库并登记 reference_images。"))
    if not profile.get("known"):
        findings.append(finding(
            "warn", "backend_unknown_capability",
            f"生图后端未登记在能力档表（生图模型={image_model or '未声明'}／生图渠道={image_channel or '未声明'}）："
            f"按最保守能力规划（仅单张参考图、参考预算 {adapter.reference_limit_for(profile)}），"
            "未假装支持多参考/主体库；要按真实能力规划请先把它登记进 skills/ad/_lib/image_backend_adapter.py。"))
    if "主体库" in str(consistency) and not adapter.has_capability(profile, adapter.CAP_SUBJECT_LIBRARY):
        findings.append(finding(
            "warn", "consistency_setting_unsupported",
            f"_设置.md 的 `一致性增强={consistency}` 要求后端主体库，但 {profile.get('label')} 的 subject_library "
            f"能力为 {adapter.capability_state(profile, adapter.CAP_SUBJECT_LIBRARY)}：实际只能走多参考兜底，"
            "别把设置当成已经锁住了产品身份。"))

    entries = plan_prompts.registry_entry_map(registry) if registry else {}
    shot_map = product_qc.storyboard_shot_by_label(storyboard)
    product_labels = set(product_qc.product_shots(storyboard)) if storyboard else set()
    limit = adapter.reference_limit_for(profile)

    shots: List[Dict[str, Any]] = []
    for label, shot in shot_map.items():
        asset_ids = shot_asset_ids(shot)
        is_product_shot = label in product_labels
        semantic_only = is_product_shot and not product_qc.product_asset_ids(shot)
        multi_asset = len(asset_ids) >= 2

        if semantic_only:
            findings.append(finding(
                "warn", "product_shot_missing_asset_id",
                f"{label} 按镜头语义是产品/包装/logo/UI/CTA 镜，但 storyboard.assets 没有结构化 `PROD_*`："
                "无法规划该喂哪张产品参考（语义纳管属启发式判定，故只 warn；product_qc 会在出图后按 block 处理）。",
                shot=label))

        # 候选参考（registry 静态登记的 reference_images）→ 按产品优先排序供预算分配。
        candidates: List[Tuple[str, List[str]]] = []
        asset_records: List[Dict[str, Any]] = []
        for aid in asset_ids:
            kind = adapter.asset_kind_for_id(aid)
            entry = entries.get(aid)
            refs = plan_prompts.reference_paths(entry) if isinstance(entry, Mapping) else []
            candidates.append((aid, list(refs)))
            asset_records.append({"asset_id": aid, "kind": kind, "registered": entry is not None,
                                  "candidate_references": list(refs)})

        allocation = allocate_references(candidates, limit)
        selected_by_asset: Dict[str, List[str]] = {}
        for row in allocation["selected"]:
            selected_by_asset.setdefault(row["asset_id"], []).append(row["path"])

        if allocation["dropped"]:
            findings.append(finding(
                "warn", "reference_budget_overflow",
                f"{label} 需要 {allocation['requested']} 张参考，后端 {profile.get('label')} 上限 {limit} 张，"
                f"已丢 {len(allocation['dropped'])} 张（{'、'.join(r['path'] for r in allocation['dropped'])}）："
                "拆镜 / 精选参考包 / 换支持更大参考预算的后端；不要以为它们被喂进去了。",
                shot=label))

        asset_plans: List[Dict[str, Any]] = []
        for record in asset_records:
            aid, kind = record["asset_id"], record["kind"]
            deltas = variation_deltas(shot, kind, multi_asset)
            score = delta_score(deltas, kind)
            big = is_big_delta(score, kind)
            refs = selected_by_asset.get(aid, [])
            required = min_references_for(kind, big)
            achievable = adapter.lock_tier_for(profile, kind)
            recommended = recommended_tier_for(kind, big)
            controls = plan_controls(profile, deltas, kind)

            references = [{"path": p, "exists": _reference_exists(root, p)} for p in refs]
            missing_files = [r["path"] for r in references if not r["exists"]]

            # —— 确定性缺口（可 block）：ID 没登记 / 登记了却没参考图 —— #
            if registry and not record["registered"]:
                findings.append(finding(
                    "block" if kind in _PRODUCTISH else "warn", "registry_asset_missing",
                    f"{label}·{aid} 在 storyboard 声明了，但 asset_registry 里没有这个资产："
                    "参考处方无从下手（产品/品牌资产缺登记 = 只能文生图 = 必漂）。",
                    shot=label, asset_id=aid))
            elif not refs:
                if not registry:
                    pass  # 缺 registry 已在报告顶层降级，不逐资产刷屏。
                else:
                    findings.append(finding(
                        "block" if kind in _PRODUCTISH else "warn", "asset_reference_unregistered",
                        f"{label}·{aid} 已登记但 reference_images 为空："
                        f"本镜{'（产品/品牌镜）' if kind in _PRODUCTISH else ''}将退化为纯文生图。"
                        "先补真实定妆参考图再出图。",
                        shot=label, asset_id=aid))
            elif kind in _PRODUCTISH and len(refs) == 1 and required > 1:
                # 产品镜单参考 = 最危险：单张定妆照只是「板式」，换角度/景别必重画包装。
                # 结构化登记过的产品 ID → 确定性缺口，可 block；语义纳管镜属启发式 → 降 warn。
                findings.append(finding(
                    "warn" if semantic_only else "block", "product_shot_single_reference",
                    f"{label}·{aid} 只有 1 张参考图（本镜变化量 {score}·需 ≥{required} 张）："
                    f"产品/品牌是最严格的“角色”，单张定妆照对 AI 只是固定板式——"
                    f"补包装正/侧/背 + logo 特写 + 材质细节；变化量={'、'.join(deltas) or '无'}。",
                    shot=label, asset_id=aid))
            elif len(refs) < required:
                findings.append(finding(
                    "warn", "reference_plan_underfed",
                    f"{label}·{aid} 参考不足：本镜变化量 {score}（{'、'.join(deltas) or '无'}）需 ≥{required} 张，"
                    f"实际 {len(refs)} 张——变化量按关键词启发式估计（confidence=low），请人工确认。",
                    shot=label, asset_id=aid))

            if missing_files:
                findings.append(finding(
                    "warn", "reference_file_missing",
                    f"{label}·{aid} registry 登记的参考图在磁盘上不存在：{'、'.join(missing_files)}——"
                    "登记不等于有图，正式跑前必须落真实文件。",
                    shot=label, asset_id=aid))

            if adapter.tier_rank(achievable) < adapter.tier_rank(recommended):
                findings.append(finding(
                    "warn" if kind in _PRODUCTISH else "info", "tier_below_recommended",
                    f"{label}·{aid} 建议档位 {recommended}，但 {profile.get('label')} 对 {kind} 只够得着 "
                    f"{achievable}：{'产品/品牌大变化镜' if kind in _PRODUCTISH else '本镜'}靠多参考硬堆有漂移风险——"
                    "考虑换支持原生主体库的后端登记 ID，或拆镜降变化量；LoRA 只留给核心长线代言人。",
                    shot=label, asset_id=aid))

            for control in controls:
                if control["state"] == adapter.CAP_UNKNOWN:
                    findings.append(finding(
                        "info", "backend_unknown_capability",
                        f"{label}·{aid} 建议用 {control['type']}，但 {profile.get('label')} 的该能力状态未知："
                        "不据此下计划，也不谎称不支持——请人工确认渠道是否可用。",
                        shot=label, asset_id=aid))

            asset_plans.append({
                "asset_id": aid,
                "kind": kind,
                "registered": record["registered"],
                "variation_delta": deltas,
                "delta_score": score,
                "big_delta": big,
                "references": references,
                "reference_count": len(refs),
                "min_references": required,
                "recommended_tier": recommended,
                "achievable_tier": achievable,
                "tier_gap": adapter.tier_rank(achievable) < adapter.tier_rank(recommended),
                "controls": controls,
            })

        shot_findings = [f for f in findings if f.get("shot") == label]
        shots.append({
            "shot": label,
            "is_product_shot": is_product_shot,
            "product_semantic_only": semantic_only,
            "assets": asset_plans,
            "reference_budget": {"limit": allocation["limit"], "requested": allocation["requested"],
                                 "selected": allocation["selected_count"],
                                 "dropped": allocation["dropped"]},
            "references": [row["path"] for row in allocation["selected"]],
            "controls": [c for plan in asset_plans for c in plan["controls"]],
            "recommended_tier": max((p["recommended_tier"] for p in asset_plans),
                                    key=adapter.tier_rank, default=adapter.TIER_SHARED_KIT),
            "needs_action": bool(shot_findings),
        })

    summary = {
        "block": sum(1 for f in findings if f["severity"] == "block"),
        "warn": sum(1 for f in findings if f["severity"] == "warn"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
        "shots": len(shots),
        "product_shots": sum(1 for s in shots if s["is_product_shot"]),
        "shots_needing_action": sum(1 for s in shots if s["needs_action"]),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "generated_at": now_iso(),
        "project_root": str(root),
        "backend": profile,
        "inputs": inputs,
        "thresholds": {
            "delta_weights": DELTA_WEIGHTS,
            "product_delta_multiplier": PRODUCT_DELTA_MULTIPLIER,
            "big_delta_score": BIG_DELTA_SCORE,
            "product_big_delta_score": PRODUCT_BIG_DELTA_SCORE,
            "min_references": MIN_REFERENCES,
            "provenance": PROVENANCE,
        },
        "advisory": "事前处方·advisory：变化量为关键词启发式，默认不阻断（exit 0）；只有 --strict 且 block>0 才非零退出。",
        "summary": summary,
        "shots": shots,
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    backend = report.get("backend") or {}
    inputs = report.get("inputs") or {}
    lines = [
        "# 出图前·逐镜参考处方（ad_reference_plan）",
        "",
        f"- 后端：{adapter.describe(backend)}",
        f"- 镜头 {s.get('shots')}（产品镜 {s.get('product_shots')}）· 需处理 {s.get('shots_needing_action')}",
        f"- block {s.get('block')} · warn {s.get('warn')} · info {s.get('info')}"
        "　（advisory：默认不阻断，`--strict` 才据 block 退出非零）",
        f"- 输入：storyboard available={str(inputs.get('storyboard', {}).get('available')).lower()}"
        f" · asset_registry available={str(inputs.get('asset_registry', {}).get('available')).lower()}",
        f"- 阈值 provenance：{(report.get('thresholds') or {}).get('provenance')}",
        "",
        "## findings",
        "",
    ]
    for f in report.get("findings") or []:
        icon = {"block": "⛔", "warn": "🟡", "info": "ℹ️"}.get(f["severity"], "·")
        where = f" [{f['shot']}]" if f.get("shot") else ""
        lines.append(f"- {icon} `{f['code']}`{where} {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 逐镜参考处方无缺口（现有定妆参考足以覆盖各镜变化量）")
    lines += ["", "## 逐镜处方", ""]
    for shot in report.get("shots") or []:
        tag = "产品镜" if shot["is_product_shot"] else "普通镜"
        lines.append(f"### {shot['shot']}（{tag}·建议档位 {shot['recommended_tier']}）")
        for plan in shot["assets"]:
            refs = "、".join(r["path"] for r in plan["references"]) or "无"
            lines.append(
                f"- `{plan['asset_id']}`（{plan['kind']}）变化量 {plan['delta_score']}"
                f"（{'、'.join(plan['variation_delta']) or '无'}）· 参考 {plan['reference_count']}/"
                f"{plan['min_references']} → {refs}"
                f" · 可达 {plan['achievable_tier']}{'（低于建议）' if plan['tier_gap'] else ''}")
            for control in plan["controls"]:
                lines.append(f"  - 控制：{control['type']}（后端状态 {control['state']}）—— {control['reason']}")
        if not shot["assets"]:
            lines.append("- （本镜未声明任何资产 ID）")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> Dict[str, str]:
    out_dir = Path(root) / "生产数据"
    json_path = out_dir / "ad_reference_plan.json"
    md_path = out_dir / "ad_reference_plan.md"
    _atomic_write(json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(md_path, render_markdown(report))
    return {"json": str(json_path), "md": str(md_path)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", help="作品根（拍广告不拆集，粒度是镜头 shot，无集/话参数）")
    ap.add_argument("--write", action="store_true", help="写 生产数据/ad_reference_plan.{json,md}")
    ap.add_argument("--json", action="store_true", help="stdout 打 JSON 而非 markdown")
    ap.add_argument("--strict", action="store_true",
                    help="严审：summary.block>0 时退出码 1（默认 advisory，恒 0）")
    ns = ap.parse_args(argv)

    report = build_plan(Path(ns.root))
    if ns.write:
        write_report(Path(ns.root), report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    if ns.strict and report["summary"]["block"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
