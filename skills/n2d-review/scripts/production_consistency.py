#!/usr/bin/env python3
"""生产一致性补强检查器。

本脚本补足一致性审计里仍偏松的低成本维度：

* O3 物件常驻/对象持久性
* X2 视线轴线与视觉状态的可回读证据
* I1 交互/接触/持有因果图
* C1 成片统一证据（响度、混剪色彩、BGM/room tone）
* RCP 生成配方 hash
* PKG 系列包装一致性
* D1 台词语域一致性
* FP1 场景平面图/区域一致性
* K1 成本、后端、重试口径一致性
* ST1 状态转场视频证据
* POS 道具/资产跨镜持有账本
* I2 结构化交互图谱 schema
* FT1 成片时间线探针
* RCP2 强配方 schema
* CAL 人审校准集
* PROBE 项目一致性探针包
* EMB 实体视觉记忆库（accepted-shot entity memory）
* EVID 视频证据完整性（manifest → sidecar 闭环）
* PHY 可归因物理事件图

原则：纯标准库；有显式契约时硬验，缺契约先 WARN；能从 production_events 推导的
生成配方会落 `生产数据/generation_recipe_<集>.json`，作为后续复跑/审计的稳定证据。
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from image_evidence import (
    PNG_DECODED_PIXEL_FINGERPRINT_KIND,
    png_decoded_pixel_fingerprint,
    png_evidence_errors,
)

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
try:
    from n2d_contract import (  # noqa: E402
        CHARACTER_LIBRARY_TIER_CORE,
        IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND,
        character_library_tier_for_record,
        identity_review_binding_fingerprint,
        identity_review_contract_for_view,
        identity_review_required_criteria,
        identity_reviewed_at_errors,
        identity_reviewer_appears_automated,
        production_dir,
    )
    CONTRACT_IMPORT_ERROR = ""
except Exception:  # pragma: no cover - standalone fallback
    CONTRACT_IMPORT_ERROR = "n2d_contract import failed"
    CHARACTER_LIBRARY_TIER_CORE = "core_full"
    def character_library_tier_for_record(
        record: Mapping[str, Any], *, observed_episode_count: int = 0
    ) -> str:
        return (
            CHARACTER_LIBRARY_TIER_CORE
            if record.get("core") or observed_episode_count >= 10
            else "named_minimal"
        )
    def production_dir(root: str) -> str:
        return os.path.join(root, "生产数据")
    IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND = (
        "sha256:canonical-json(char,form,tier,view,path,png_sha256)"
    )
    def identity_review_contract_for_view(view: object) -> str:
        return "n2d_expression_review_v1" if view == "expression" else "n2d_turnaround_view_review_v1"
    def identity_review_required_criteria(view: object) -> frozenset[str]:
        return frozenset()
    def identity_reviewed_at_errors(value: object) -> Tuple[str, ...]:
        return ("reviewed_at_missing",) if not str(value or "").strip() else ()
    def identity_reviewer_appears_automated(value: object) -> bool:
        return not bool(str(value or "").strip())
    def identity_review_binding_fingerprint(**kwargs: object) -> str:
        return ""

try:
    # MVIEW must use the exact same independent, structured storyboard
    # presence evidence as the pre-spend identity gate.  Keeping one parser
    # prevents review from trusting a registry's self-reported lower tier
    # after the identity gate has already promoted the same character.
    from gate_core import _storyboard_character_appearance_evidence  # noqa: E402
    STORYBOARD_APPEARANCE_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - fail-closed runtime guard
    STORYBOARD_APPEARANCE_IMPORT_ERROR = (
        f"storyboard appearance evidence import failed: {type(exc).__name__}: {exc}"
    )
    def _storyboard_character_appearance_evidence(root: str) -> Dict[str, Dict[str, Any]]:
        return {}


ASSET_RE = re.compile(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX)_[\w\-\u4e00-\u9fff]+\b")
CHAR_RE = re.compile(r"\bCHAR_[\w\-\u4e00-\u9fff]+\b")
CLIP_RE = re.compile(r"(?i)(?:Clip|镜头|镜)\s*[_ -]?0*([0-9]+)")
CONTACT_WORDS = (
    "手持", "握", "拿", "抓", "递", "接过", "交给", "拉住", "拉扯", "扶", "搀扶", "抱",
    "拥抱", "按住", "碰", "触碰", "推开", "击中", "刺中", "格挡", "戴上", "摘下", "放下",
    "掉落", "松开", "hold", "grab", "touch", "hand", "give", "take", "push", "hit",
)
RELEASE_WORDS = ("放下", "丢下", "掉落", "松开", "收起", "消失", "脱手", "release", "drop")
TRANSFER_WORDS = ("递给", "交给", "给了", "递向", "移交", "hand over", "give")
AXIS_WORDS = ("视线", "轴线", "eyeline", "gaze", "看向", "画左", "画右", "正反打", "反打", "过肩")
STATE_WORDS = ("状态", "伤", "血", "泪", "湿", "破", "乱发", "持有", "获得", "丢失", "state", "status")
EXEMPT_WORDS = ("特写", "极近", "ECU", "CU", "细节", "局部", "空镜", "不入画", "画外", "遮挡", "虚焦")
REGISTER_WORDS = ("本宫", "朕", "臣妾", "妾身", "老子", "俺", "人家", "属下", "小的", "奴婢", "为师", "徒儿")
STATE_TRANSITION_WORDS = (
    "变成", "转为", "化作", "出现", "消失", "破裂", "碎裂", "断裂", "燃起", "熄灭", "点燃",
    "流血", "受伤", "愈合", "湿透", "觉醒", "变色", "打开", "关闭", "掉落", "拾起",
    "state_change", "transition", "becomes", "turns into", "appears", "disappears",
)
HIGH_RISK_INTERACTION_WORDS = (
    "打斗", "命中", "刺中", "格挡", "拥抱", "抓腕", "拉扯", "搀扶", "推开", "击中",
    "亲密互动", "physical_interaction", "contact_motion", "feature_melting_risk",
)
REVIEW_LABELS = {"true_positive", "false_positive", "accepted_intentional", "missed_by_machine"}
PROBE_SCENARIOS = (
    "character_turnaround",
    "core_prop_transfer",
    "same_scene_multiview",
    "physical_interaction",
    "state_transition",
    "native_av_dialogue",
)
PHYSICAL_LAWS = {
    "object_permanence",
    "identity_conservation",
    "mass_conservation",
    "size_conservation",
    "gravity_support",
    "impenetrability",
    "momentum_conservation",
    "collision",
    "gravity_drop",
    "fracture",
    "combustion",
    "liquid",
    "contact_continuity",
    "state_conservation",
}
TRUTH_MAP_REQUIRED = {
    "character_identity": {
        "source": "出图/共享/identity_registry.json",
        "wins_over": ("角色圣经/自然语言描述", "generation_recipe"),
        "purpose": "角色 DNA、形态、身份锚和后端主体绑定的最高真值源",
    },
    "visual_state": {
        "source": "storyboard.visual_contract + 出图/共享/visual_state_ledger.json",
        "wins_over": ("逐镜 prompt", "generation_recipe"),
        "purpose": "伤/泪/觉醒/服装破损等视觉状态区间与转场",
    },
    "scene_space": {
        "source": "设定库/scene_floorplan.json + location_spatial_memory.json",
        "wins_over": ("逐镜背景自由描述",),
        "purpose": "门窗、固定物、光源、合法机位和区域关系",
    },
    "generation_recipe": {
        "source": "生产数据/generation_recipe_第N集.json",
        "evidence_only": True,
        "purpose": "复现和归因证据，不覆盖身份/状态/空间设定",
    },
    "intentional_exception": {
        "source": "生产数据/consistency_advisory_signoff_第N集.json",
        "expires_required": True,
        "purpose": "导演有意越轴/风格变化/状态重置等例外的有期限签收",
    },
}
MULTIVIEW_BUCKETS = (
    "front",
    "three_quarter",
    "profile_or_side",
    "rear_three_quarter",
    "back",
    "expression",
    "turnaround",
)
MULTIVIEW_PASS_STATUSES = {"pass", "passed", "ready", "approved", "accepted", "green"}
MULTIVIEW_FAIL_STATUSES = {"block", "fail", "failed", "rejected", "red"}
MULTIVIEW_HARD_EVIDENCE_KINDS = {
    "structured_human_review",
    "calibrated_embedding",
    "deterministic_geometry",
    "hybrid_human_calibrated",
}
WORLD_SCORE_COMPONENTS = ("object_permanence", "relation_stability", "causal_compliance", "flicker_penalty")
ASSET_TAIL_ACTIONS = (
    "逼近", "走来", "走近", "转身", "冲向", "看向", "递给", "交给", "刺向", "砍向", "挥向",
    "靠近", "离开", "退到", "退后", "藏到", "藏入", "站起", "坐下", "跪下", "倒下", "落地", "入画", "出画",
)


def _load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _load_first_json(root: str, rels: Sequence[str]) -> Tuple[Optional[Any], str]:
    for rel in rels:
        path = rel if os.path.isabs(rel) else os.path.join(root, rel)
        data = _load_json(path)
        if data is not None:
            return data, os.path.relpath(path, root)
    return None, ""


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def _write_json(path: str, payload: Mapping[str, Any]) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value or "")


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    if value in (None, ""):
        return []
    return [value]


def _unique(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _clip_label(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("id") or clip.get("clip_id") or clip.get("label") or "").strip()
    if raw:
        m = CLIP_RE.search(raw)
        if m:
            return f"Clip_{int(m.group(1)):02d}"
        return raw
    return f"Clip_{idx:02d}"


def _clip_num(label: str) -> str:
    m = CLIP_RE.search(label)
    return f"Clip_{int(m.group(1)):02d}" if m else label


def _clip_index(label: str) -> int:
    m = CLIP_RE.search(label)
    return int(m.group(1)) if m else 10**9


def _storyboard(root: str, ep: str) -> Tuple[Optional[dict], List[dict]]:
    data = _load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    if not isinstance(data, dict):
        return None, []
    clips = data.get("clips") or data.get("shots") or []
    return data, [c for c in clips if isinstance(c, dict)]


def _sections_by_clip(text: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not text:
        return out
    blocks = re.split(r"(?m)(?=^#{1,4}\s+)", text)
    for block in blocks:
        head = block.splitlines()[0] if block.splitlines() else ""
        labels = _unique(_clip_num(f"Clip_{int(m.group(1)):02d}") for m in CLIP_RE.finditer(head + "\n" + block[:300]))
        for label in labels:
            out[label] = out.get(label, "") + "\n" + block
    return out


def _prompt_sections(root: str, ep: str) -> Dict[str, str]:
    merged: Dict[str, str] = defaultdict(str)
    for rel in (
        os.path.join("出图", ep, "prompt", "01_分镜出图.md"),
        os.path.join("出视频", ep, "prompt", "01_clips.md"),
    ):
        for clip, text in _sections_by_clip(_read(os.path.join(root, rel))).items():
            merged[clip] += "\n" + text
    return dict(merged)


def _clip_text(clip: Mapping[str, Any], label: str, prompt_sections: Mapping[str, str]) -> str:
    return _json_text(clip) + "\n" + str(prompt_sections.get(label) or "")


def _asset_ids(text: str) -> List[str]:
    def trim(raw: str) -> str:
        for marker in ASSET_TAIL_ACTIONS:
            pos = raw.find(marker)
            if pos > len("PROP_"):
                return raw[:pos]
        return raw
    return _unique(trim(m.group(0)) for m in ASSET_RE.finditer(text or ""))


def _char_ids(text: str) -> List[str]:
    return _unique(m.group(0) for m in CHAR_RE.finditer(text or ""))


def _loc_of(clip: Mapping[str, Any], text: str) -> str:
    for key in ("loc", "location", "scene_id", "scene"):
        raw = str(clip.get(key) or "").strip()
        if raw:
            loc = raw.split("/")[0].strip()
            if loc:
                return loc
    ids = [x for x in _asset_ids(text) if x.startswith("LOC_")]
    return ids[0] if ids else ""


def _is_exempt_view(text: str) -> bool:
    return any(w.lower() in (text or "").lower() for w in EXEMPT_WORDS)


def _artifact_exists(root: str, value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if re.match(r"^(?:https?|s3|gs)://", text):
        return True
    path = text if os.path.isabs(text) else os.path.join(root, text)
    return os.path.exists(path)


def _has_any_field(value: Mapping[str, Any], *keys: str) -> bool:
    return any(value.get(key) not in (None, "", [], {}) for key in keys)


def _normalise_bucket(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "side": "profile_or_side",
        "profile": "profile_or_side",
        "left_profile": "profile_or_side",
        "right_profile": "profile_or_side",
        "45": "three_quarter",
        "three_quarters": "three_quarter",
        "3_4": "three_quarter",
        "rear_45": "rear_three_quarter",
        "rear45": "rear_three_quarter",
        "back_three_quarter": "rear_three_quarter",
        "rear_three_quarters": "rear_three_quarter",
        "emotion": "expression",
        "expressions": "expression",
    }
    return aliases.get(text, text)


def _setting_text(root: str) -> str:
    return _read(os.path.join(root, "_设置.md"))


def _native_av_project(root: str) -> bool:
    text = _setting_text(root)
    return bool(re.search(r"制作模式\s*[:：]\s*原生音画", text)) or "native_av" in text.lower()


def _finding_hash(row: Mapping[str, Any]) -> str:
    stable = {
        "dimension": row.get("dimension") or row.get("dim") or "",
        "message": row.get("message") or row.get("msg") or row.get("reason") or "",
        "affected_shots": row.get("affected_shots") if isinstance(row.get("affected_shots"), list) else [],
        "affected_artifacts": row.get("affected_artifacts") if isinstance(row.get("affected_artifacts"), list) else [],
        "loc": row.get("loc") or row.get("path") or "",
    }
    blob = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _registry_assets(root: str) -> List[dict]:
    data = _load_json(os.path.join(root, "出图", "共享", "asset_registry.json"))
    if isinstance(data, dict):
        raw = data.get("assets") or data.get("items") or data.get("registry") or []
        if isinstance(raw, dict):
            raw = [{**(v if isinstance(v, dict) else {}), "id": k} for k, v in raw.items()]
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    return [a for a in raw if isinstance(a, dict)]


def _registry_characters(root: str) -> List[dict]:
    data = _load_json(os.path.join(root, "出图", "共享", "identity_registry.json"))
    if isinstance(data, dict):
        raw = data.get("characters") or data.get("identities") or []
        if isinstance(raw, dict):
            raw = [{**(v if isinstance(v, dict) else {}), "id": k} for k, v in raw.items()]
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    return [c for c in raw if isinstance(c, dict)]


def _persistent_assets(root: str) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for asset in _registry_assets(root):
        aid = str(asset.get("id") or asset.get("asset_id") or "").strip()
        if not aid or not (aid.startswith("PROP_") or aid.startswith("WEAPON_") or aid.startswith("VFX_") or aid.startswith("OUTFIT_")):
            continue
        blob = _json_text(asset).lower()
        persistent = (
            asset.get("persistent") is True
            or asset.get("always_present") is True
            or asset.get("must_appear") is True
            or any(k in blob for k in ("常驻", "恒存", "不得丢", "drift_forbidden", "always_present", "persistent"))
        )
        if persistent:
            out[aid] = asset
    return out


def _schedule_values(schedule: Any, *keys: str) -> List[str]:
    if not isinstance(schedule, Mapping):
        return []
    vals: List[str] = []
    for key in keys:
        vals.extend(str(x).strip() for x in _as_list(schedule.get(key)) if str(x).strip())
    return _unique(vals)


def _entity_appearances(root: str, ep: str) -> Dict[str, dict]:
    """Collect per-episode entity appearances from entity_schedule and storyboard text."""
    _sb, clips = _storyboard(root, ep)
    prompts = _prompt_sections(root, ep)
    out: Dict[str, dict] = {}
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        schedule = clip.get("entity_schedule") or clip.get("实体排程")
        chars = _unique(_schedule_values(schedule, "characters", "character_ids", "角色") + _char_ids(text))
        objects = _unique(
            _schedule_values(schedule, "objects", "object_ids", "props", "weapons", "道具", "物件")
            + [aid for aid in _asset_ids(text) if aid.startswith(("PROP_", "WEAPON_", "OUTFIT_", "VFX_"))]
        )
        locs = _unique(_schedule_values(schedule, "locations", "location_ids", "scene_id", "场景", "地点"))
        loc = _loc_of(clip, text)
        if loc:
            locs = _unique(locs + [loc])
        for kind, values in (("character", chars), ("object", objects), ("location", locs)):
            for entity_id in values:
                row = out.setdefault(entity_id, {"entity_id": entity_id, "kind": kind, "clips": []})
                row["clips"].append(label)
                if kind == "character":
                    row["kind"] = "character"
                elif row.get("kind") not in {"character", "object"}:
                    row["kind"] = kind
    for row in out.values():
        row["clips"] = _unique(row.get("clips") or [])
    return out


def _entity_memory_bank(root: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", "entity_memory_bank.json"),
        os.path.join("出图", "共享", "entity_memory_bank.json"),
        os.path.join("设定库", "entity_memory_bank.json"),
    ))


def _entity_memory_entries(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("entries") or data.get("memory") or data.get("items") or data.get("entities") or []
        if isinstance(raw, dict):
            rows = []
            for key, value in raw.items():
                if isinstance(value, list):
                    rows.extend({**(item if isinstance(item, dict) else {}), "entity_id": key} for item in value)
                elif isinstance(value, dict):
                    rows.append({"entity_id": key, **value})
                else:
                    rows.append({"entity_id": key, "value": value})
            raw = rows
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _entry_entity(row: Mapping[str, Any]) -> str:
    return str(row.get("entity_id") or row.get("id") or row.get("character_id") or row.get("asset_id") or row.get("location_id") or "").strip()


def _entry_media(row: Mapping[str, Any]) -> str:
    return str(row.get("crop_path") or row.get("media_path") or row.get("reference_path") or row.get("image") or row.get("frame") or "").strip()


def _entry_used_for_generation(row: Mapping[str, Any]) -> bool:
    return bool(
        row.get("used_for_generation") is True
        or row.get("retrieved_for")
        or row.get("retrieval_log")
        or row.get("last_retrieved_at")
        or row.get("reference_plan")
    )


def _core_character_ids(root: str) -> List[str]:
    out: List[str] = []
    for char in _registry_characters(root):
        cid = str(char.get("id") or char.get("character_id") or char.get("name") or "").strip()
        core = character_library_tier_for_record(char) == CHARACTER_LIBRARY_TIER_CORE
        if cid and core:
            out.append(cid)
    return _unique(out)


def _truth_map(root: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("设定库", "consistency_truth_map.json"),
        os.path.join("生产数据", "consistency_truth_map.json"),
        os.path.join("设定库", "truth_source_rank.json"),
    ))


def _project_has_multiple_truth_sources(root: str, ep: str) -> bool:
    candidates = (
        os.path.join(root, "出图", "共享", "identity_registry.json"),
        os.path.join(root, "出图", "共享", "asset_registry.json"),
        os.path.join(root, "脚本", ep, "storyboard.json"),
        os.path.join(root, "出图", "共享", "visual_state_ledger.json"),
        os.path.join(root, "设定库", "scene_floorplan.json"),
        os.path.join(production_dir(root), f"generation_recipe_{ep}.json"),
    )
    return sum(1 for path in candidates if os.path.exists(path)) >= 3


def _truth_entries(data: Any) -> Dict[str, Mapping[str, Any]]:
    if isinstance(data, Mapping):
        raw = data.get("truth_sources") or data.get("sources") or data.get("precedence") or data
    else:
        raw = data
    out: Dict[str, Mapping[str, Any]] = {}
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            if isinstance(value, Mapping):
                out[str(key)] = value
            else:
                out[str(key)] = {"source": value}
    elif isinstance(raw, list):
        for item in raw:
            if isinstance(item, Mapping):
                key = str(item.get("key") or item.get("name") or item.get("domain") or "").strip()
                if key:
                    out[key] = item
    return out


def check_consistency_truth_map(root: str, ep: str) -> dict:
    """Precedence map for conflicting identity/state/scene/recipe truth sources."""
    res = {"available": True, "findings": [], "notes": []}
    data, rel = _truth_map(root)
    if data is None:
        if _project_has_multiple_truth_sources(root, ep):
            res["findings"].append(_row(
                "warn",
                "项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，"
                "但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。",
                stage="review",
                artifacts=("设定库/consistency_truth_map.json",),
                evidence_family="text_contract",
            ))
        else:
            res["notes"].append("真值源尚少，TRUTH 暂不强制。")
        return res
    entries = _truth_entries(data)
    for key, spec in TRUTH_MAP_REQUIRED.items():
        if key not in entries:
            res["findings"].append(_row(
                "warn",
                f"consistency_truth_map 缺 {key}；建议 source={spec['source']}。",
                stage="review",
                artifacts=(rel,),
                evidence_family="text_contract",
            ))
            continue
        row = entries[key]
        if not _has_any_field(row, "source", "canonical_source", "path"):
            res["findings"].append(_row(
                "warn",
                f"truth source {key} 缺 source/canonical_source/path。",
                stage="review",
                artifacts=(rel,),
                evidence_family="text_contract",
            ))
        if key == "generation_recipe" and row.get("evidence_only") is not True:
            res["findings"].append(_row(
                "warn",
                "generation_recipe 应标 evidence_only=true；它只能证明生成过程，不能覆盖角色/状态/空间设定。",
                stage="review",
                artifacts=(rel,),
                evidence_family="text_contract",
            ))
        if key == "intentional_exception" and row.get("expires_required") is not True:
            res["findings"].append(_row(
                "warn",
                "intentional_exception 应标 expires_required=true；例外签收不能无限期吞掉后续集一致性问题。",
                stage="review",
                artifacts=(rel,),
                evidence_family="text_contract",
            ))
    return res


def _character_forms(char: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    forms = char.get("forms")
    if isinstance(forms, list) and forms:
        return [f for f in forms if isinstance(f, Mapping)]
    return [char]


def _expression_anchor_count(form: Mapping[str, Any]) -> int:
    raw = form.get("expression_anchors") or form.get("expressions") or form.get("表情锚")
    if not raw and isinstance(form.get("reference_group"), Mapping):
        ref = form.get("reference_group")
        raw = ref.get("expression_anchors") or ref.get("expressions") or ref.get("表情锚")
    if isinstance(raw, Mapping):
        return len(raw)
    if isinstance(raw, list):
        return len([x for x in raw if x])
    return 0


def _has_performance_signature(form: Mapping[str, Any]) -> bool:
    return bool(
        form.get("performance_signature")
        or form.get("表演签名")
        or form.get("gesture_signature")
        or form.get("stance")
        or form.get("gaze")
    )


def _identity_eval_pack(root: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", "identity_eval_pack.json"),
        os.path.join("设定库", "identity_eval_pack.json"),
        os.path.join("生产数据", "multiview_identity_pack.json"),
        os.path.join("设定库", "multiview_identity_pack.json"),
    ))


def _identity_eval_rows(data: Any) -> List[dict]:
    if isinstance(data, Mapping):
        raw = data.get("characters") or data.get("rows") or data.get("items") or data.get("tests") or []
        if isinstance(raw, Mapping):
            rows = []
            for key, value in raw.items():
                if isinstance(value, Mapping):
                    rows.append({"character_id": key, **value})
                else:
                    rows.append({"character_id": key, "value": value})
            raw = rows
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _eval_row_buckets(row: Mapping[str, Any]) -> set:
    raw = row.get("buckets") or row.get("views") or row.get("tests") or row.get("yaw_buckets") or []
    buckets = set()
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            if value in (None, "", [], {}) or (isinstance(value, Mapping) and str(value.get("status") or "").lower() in {"missing", "planned"}):
                continue
            buckets.add(_normalise_bucket(key))
    else:
        for item in _as_list(raw):
            if isinstance(item, Mapping):
                buckets.add(_normalise_bucket(item.get("bucket") or item.get("view") or item.get("name") or item.get("type")))
            else:
                buckets.add(_normalise_bucket(item))
    return {b for b in buckets if b}


def _eval_bucket_map(row: Mapping[str, Any]) -> Dict[str, Any]:
    raw = row.get("buckets") or row.get("views") or row.get("tests") or row.get("yaw_buckets") or {}
    out: Dict[str, Any] = {}
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            bucket = _normalise_bucket(key)
            if bucket:
                out[bucket] = value
    else:
        for item in _as_list(raw):
            if not isinstance(item, Mapping):
                continue
            bucket = _normalise_bucket(item.get("bucket") or item.get("view") or item.get("name") or item.get("type"))
            if bucket:
                out[bucket] = item
    return out


def _eval_row_form(row: Mapping[str, Any]) -> str:
    return str(row.get("form") or row.get("form_name") or row.get("variant") or "").strip()


def _sha256_path(path: str) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _registry_sha256(root: str) -> str:
    return _sha256_path(os.path.join(root, "出图", "共享", "identity_registry.json"))


def _bucket_status(value: Any) -> str:
    if isinstance(value, Mapping):
        return str(value.get("verdict") or value.get("status") or value.get("result") or "").strip().lower()
    return str(value or "").strip().lower()


def _multiview_binding_fingerprint(
    *,
    character_id: str,
    form: str,
    library_tier: str,
    view: str,
    path: str,
    png_sha256: str,
) -> str:
    """Independent verifier for identity_eval_pack registry bindings."""
    return identity_review_binding_fingerprint(
        character_id=character_id,
        form=form,
        library_tier=library_tier,
        view=view,
        path=path,
        png_sha256=png_sha256,
    )


def _multiview_reference_path(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get("path") or "").strip()
    return ""


def _multiview_looks_absolute_path(value: str) -> bool:
    path = str(value or "").strip()
    return bool(
        os.path.isabs(path)
        or (len(path) >= 3 and path[1] == ":" and path[2] in {"/", "\\"})
        or path.startswith("\\\\")
    )


def _resolve_multiview_evidence_path(
    root: str,
    value: str,
    *,
    source: str,
) -> Tuple[str, str, List[str]]:
    """Resolve relative evidence under the real project root, following links."""
    raw = str(value or "").strip()
    if not raw:
        return "", "", [f"{source}_path_missing"]
    if "\x00" in raw:
        return "", "", [f"{source}_path_invalid_nul"]
    if _multiview_looks_absolute_path(raw):
        return "", "", [f"{source}_absolute_path_not_allowed"]
    root_real = os.path.realpath(os.path.abspath(root))
    resolved = os.path.realpath(os.path.join(root_real, raw))
    try:
        if os.path.commonpath((root_real, resolved)) != root_real:
            return "", "", [f"{source}_path_outside_project_root"]
    except ValueError:
        return "", "", [f"{source}_path_outside_project_root"]
    normalized = os.path.relpath(resolved, root_real).replace(os.sep, "/")
    if normalized in {"", "."} or normalized == ".." or normalized.startswith("../"):
        return "", "", [f"{source}_path_outside_project_root"]
    return normalized, resolved, []


def _multiview_registry_nodes(form: Mapping[str, Any], bucket: str) -> List[Mapping[str, Any]]:
    group = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    base = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
    view = "side" if bucket == "profile_or_side" else bucket
    if view == "expression":
        values: List[Any] = []
        for raw in (
            group.get("expressions"),
            group.get("face_anchor_refs"),
            atlas.get("expression_refs"),
            atlas.get("face_anchor_refs"),
        ):
            if isinstance(raw, list):
                values.extend(raw)
        return [item for item in values if isinstance(item, Mapping)]
    node = group.get(view)
    if node in (None, "", [], {}):
        node = base.get(view)
    return [node] if isinstance(node, Mapping) else []


def _multiview_executor_visual_authorized(root: str) -> bool:
    try:
        text = Path(os.path.join(root, "_设置.md")).read_text(encoding="utf-8")
    except OSError:
        return False
    return (
        "执行者实际像素目视" in text
        and ("用户明确" in text or "source=explicit_user" in text)
    )


def _multiview_review_receipt(node: Mapping[str, Any], expected_sha: str = "") -> Tuple[str, Mapping[str, Any]]:
    candidates: List[Tuple[int, str, Mapping[str, Any]]] = []
    for fallback_kind, key in (("human", "human_review"), ("executor_visual", "visual_review")):
        review = node.get(key)
        if not isinstance(review, Mapping):
            continue
        score = 8 if expected_sha and str(review.get("png_sha256") or "").strip() == expected_sha else 0
        score += 4 if str(review.get("verdict") or review.get("status") or "").strip().lower() in MULTIVIEW_PASS_STATUSES else 0
        score += 2 if str(review.get("reviewer") or "").strip() else 0
        score += 1 if fallback_kind == "human" else 0
        candidates.append((score, fallback_kind, review))
    if not candidates:
        return "", {}
    _score, fallback_kind, review = max(candidates, key=lambda row: row[0])
    return str(review.get("review_kind") or fallback_kind).strip().lower(), review


def _multiview_registry_form_index(
    root: str,
) -> Dict[Tuple[str, str], Tuple[Mapping[str, Any], Mapping[str, Any], str]]:
    out: Dict[Tuple[str, str], Tuple[Mapping[str, Any], Mapping[str, Any], str]] = {}
    for char in _registry_characters(root):
        cid = str(char.get("id") or char.get("character_id") or char.get("name") or "").strip()
        if not cid:
            continue
        tier = character_library_tier_for_record(char)
        for form in _character_forms(char):
            form_name = str(form.get("form") or form.get("form_name") or "default").strip() or "default"
            out[(cid, form_name)] = (char, form, tier)
    return out


def _bucket_evidence_errors(
    root: str,
    value: Any,
    *,
    character_id: str,
    form_name: str,
    library_tier: str,
    bucket: str,
    registry_form: Mapping[str, Any],
) -> List[str]:
    if not isinstance(value, Mapping):
        return ["bucket_not_structured"]
    errors: List[str] = []
    status = _bucket_status(value)
    if status not in MULTIVIEW_PASS_STATUSES:
        errors.append(f"status={status or 'missing'}")
    declared_statuses = {
        str(value.get(key) or "").strip().lower()
        for key in ("verdict", "status", "result")
        if str(value.get(key) or "").strip()
    }
    if declared_statuses & MULTIVIEW_FAIL_STATUSES:
        errors.append("conflicting_or_failed_declared_status")
    kind = str(value.get("evidence_kind") or value.get("review_kind") or "").strip()
    # v2 pack currently has one implemented, reproducible evidence route.  Do
    # not let an arbitrary file self-label as calibrated_embedding/geometry.
    if kind not in {"structured_human_review", "structured_executor_visual_review"}:
        errors.append(f"evidence_kind={kind or 'missing'}")
    expected_view = "side" if bucket == "profile_or_side" else bucket
    expected_fields = {
        "character_id": character_id,
        "form": form_name,
        "library_tier": library_tier,
        "view": expected_view,
    }
    for key, expected in expected_fields.items():
        if str(value.get(key) or "").strip() != expected:
            errors.append(f"{key}_mismatch")
    raw_rel = str(
        value.get("path")
        or value.get("artifact_path")
        or value.get("image_path")
        or value.get("reference_path")
        or ""
    ).strip()
    if not raw_rel:
        errors.append("path_missing")
        return errors
    rel, path, path_errors = _resolve_multiview_evidence_path(
        root, raw_rel, source="pack_evidence"
    )
    errors.extend(path_errors)
    if path_errors:
        return sorted(set(errors))
    if raw_rel.replace("\\", "/") != rel:
        errors.append("pack_path_not_canonical_project_relative")
    if not os.path.isfile(path):
        errors.append("path_not_found")
        return sorted(set(errors))
    # ``png_evidence_errors`` includes not_valid_png_container plus complete
    # chunk CRC, IDAT decompression and scanline-layout validation.
    png_errors = png_evidence_errors(path)
    errors.extend(png_errors)
    actual_pixel_fingerprint = ""
    if not png_errors:
        actual_pixel_fingerprint, fingerprint_errors = png_decoded_pixel_fingerprint(path)
        errors.extend(fingerprint_errors)
        if not actual_pixel_fingerprint and not fingerprint_errors:
            errors.append("png_pixel_fingerprint_unavailable")
    declared_pixel_fingerprint = str(
        value.get("decoded_pixel_fingerprint") or ""
    ).strip()
    if not declared_pixel_fingerprint:
        errors.append("decoded_pixel_fingerprint_missing")
    elif declared_pixel_fingerprint != actual_pixel_fingerprint:
        errors.append("decoded_pixel_fingerprint_mismatch")
    if (
        str(value.get("decoded_pixel_fingerprint_kind") or "").strip()
        != PNG_DECODED_PIXEL_FINGERPRINT_KIND
    ):
        errors.append("decoded_pixel_fingerprint_kind_invalid")
    declared_sha = str(value.get("sha256") or value.get("artifact_sha256") or "").strip()
    actual_sha = _sha256_path(path)
    if not declared_sha:
        errors.append("sha256_missing")
    elif actual_sha != declared_sha:
        errors.append("sha256_mismatch")
    expected_binding = _multiview_binding_fingerprint(
        character_id=character_id,
        form=form_name,
        library_tier=library_tier,
        view=expected_view,
        path=rel,
        png_sha256=actual_sha,
    )
    if str(value.get("registry_binding_fingerprint_kind") or "") != IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND:
        errors.append("registry_binding_fingerprint_kind_invalid")
    if str(value.get("registry_binding_fingerprint") or "") != expected_binding:
        errors.append("registry_binding_fingerprint_mismatch")
    expected_contract = identity_review_contract_for_view(expected_view)
    if str(value.get("review_contract") or "") != expected_contract:
        errors.append("review_contract_invalid_for_view")
    reviewer = str(value.get("reviewer") or "").strip()
    review_kind = str(value.get("review_kind") or ("executor_visual" if kind == "structured_visual_review" else "human")).strip().lower()
    if not reviewer:
        errors.append("reviewer_missing")
    elif review_kind == "human" and identity_reviewer_appears_automated(reviewer):
        errors.append("reviewer_appears_automated")
    elif review_kind == "executor_visual":
        if str(value.get("reviewer_role") or "") != "ai_visual_executor":
            errors.append("executor_visual_reviewer_role_missing_or_mismatch")
        if value.get("human_signoff") is not False:
            errors.append("executor_visual_human_signoff_must_be_false")
        if not _multiview_executor_visual_authorized(root):
            errors.append("executor_visual_review_not_authorized_by_project_setting")
    elif review_kind not in {"human", "executor_visual"}:
        errors.append("review_kind_missing_or_invalid")
    errors.extend(identity_reviewed_at_errors(value.get("reviewed_at")))
    criteria = {str(item) for item in (value.get("criteria") or []) if str(item)}
    if not set(identity_review_required_criteria(expected_view)).issubset(criteria):
        errors.append("criteria_incomplete")
    confirmation = value.get("confirmation") if isinstance(value.get("confirmation"), Mapping) else {}
    if (
        confirmation.get("kind") != "explicit_current_pixels_acceptance"
        or confirmation.get("accepted_current_pixels") is not True
    ):
        errors.append("explicit_current_pixels_confirmation_missing")

    # Bind the pack back to the *current inline registry receipt*, not merely
    # to a path and hash supplied by the pack itself.
    matching_node: Optional[Mapping[str, Any]] = None
    for node in _multiview_registry_nodes(registry_form, bucket):
        registry_raw = _multiview_reference_path(node)
        registry_rel, _registry_realpath, registry_path_errors = _resolve_multiview_evidence_path(
            root, registry_raw, source="registry_evidence"
        )
        errors.extend(registry_path_errors)
        if (
            not registry_path_errors
            and registry_raw.replace("\\", "/") != registry_rel
        ):
            errors.append("registry_evidence_path_not_canonical_project_relative")
        if not registry_path_errors and registry_rel == rel:
            matching_node = node
            break
    if matching_node is None:
        errors.append("registry_node_missing_or_path_mismatch")
    else:
        node_status = str(matching_node.get("status") or "").strip().lower()
        if node_status not in {"ready", "registered"}:
            errors.append(f"registry_node_status={node_status or 'missing'}")
        registry_review_kind, review = _multiview_review_receipt(matching_node, actual_sha)
        if not review:
            errors.append("registry_review_receipt_missing")
        else:
            if str(review.get("status") or "").strip().lower() != "accepted":
                errors.append("registry_review_not_accepted")
            if str(review.get("verdict") or "").strip().lower() != "pass":
                errors.append("registry_review_not_pass")
            for key, expected in {
                **expected_fields,
                "path": rel,
                "png_sha256": actual_sha,
                "registry_binding_fingerprint": expected_binding,
            }.items():
                if str(review.get(key) or "").strip() != expected:
                    errors.append(f"registry_review_{key}_mismatch")
            if str(review.get("registry_binding_fingerprint_kind") or "") != IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND:
                errors.append("registry_review_binding_kind_invalid")
            if str(review.get("review_contract") or "") != expected_contract:
                errors.append("registry_review_contract_invalid_for_view")
            if str(review.get("review_contract") or "") != str(value.get("review_contract") or ""):
                errors.append("registry_review_contract_mismatch")
            registry_reviewer = str(review.get("reviewer") or "").strip()
            if registry_review_kind == "human" and identity_reviewer_appears_automated(registry_reviewer):
                errors.append("registry_reviewer_appears_automated")
            elif registry_review_kind == "executor_visual":
                if str(review.get("reviewer_role") or "") != "ai_visual_executor":
                    errors.append("registry_executor_visual_role_invalid")
                if review.get("human_signoff") is not False:
                    errors.append("registry_executor_visual_human_signoff_invalid")
                if not _multiview_executor_visual_authorized(root):
                    errors.append("registry_executor_visual_not_authorized")
            if registry_review_kind != review_kind:
                errors.append("registry_review_kind_mismatch")
            if registry_reviewer != str(value.get("reviewer") or "").strip():
                errors.append("registry_reviewer_mismatch")
            registry_reviewed_at = str(review.get("reviewed_at") or "").strip()
            errors.extend(
                f"registry_{error}" for error in identity_reviewed_at_errors(registry_reviewed_at)
            )
            if registry_reviewed_at != str(value.get("reviewed_at") or "").strip():
                errors.append("registry_reviewed_at_mismatch")
            registry_criteria = {
                str(item) for item in (review.get("criteria") or []) if str(item)
            }
            if not set(identity_review_required_criteria(expected_view)).issubset(registry_criteria):
                errors.append("registry_criteria_incomplete")
            registry_confirmation = (
                review.get("confirmation")
                if isinstance(review.get("confirmation"), Mapping)
                else {}
            )
            if (
                registry_confirmation.get("kind") != "explicit_current_pixels_acceptance"
                or registry_confirmation.get("accepted_current_pixels") is not True
            ):
                errors.append("registry_explicit_current_pixels_confirmation_missing")
    return sorted(set(errors))


def _core_character_forms(root: str) -> List[Tuple[str, str]]:
    storyboard_appearances = _storyboard_character_appearance_evidence(root)
    required: List[Tuple[str, str]] = []
    for char in _registry_characters(root):
        cid = str(char.get("id") or char.get("character_id") or char.get("name") or "").strip()
        if not cid:
            continue
        evidence = storyboard_appearances.get(cid, {})
        try:
            observed_episode_count = max(0, int(evidence.get("episode_count") or 0))
        except (TypeError, ValueError):
            observed_episode_count = 0
        if character_library_tier_for_record(
            char,
            observed_episode_count=observed_episode_count,
        ) != CHARACTER_LIBRARY_TIER_CORE:
            continue
        forms = _character_forms(char)
        for form in forms:
            form_name = str(form.get("form") or form.get("form_name") or "default").strip() or "default"
            required.append((cid, form_name))
    return required


def _eval_row_character(row: Mapping[str, Any]) -> str:
    return str(row.get("character_id") or row.get("id") or row.get("entity_id") or row.get("char") or "").strip()


def check_multiview_identity_pack(root: str, ep: str) -> dict:
    """Core-character identity should be tested across yaw/expression buckets."""
    res = {"available": True, "findings": [], "notes": []}
    if CONTRACT_IMPORT_ERROR:
        res["findings"].append(_row(
            "block",
            "核心人物档位契约 n2d_contract 无法导入；为避免漏掉 scope 推导出的主角，多视图 gate 按 fail-closed 阻断。",
            stage="image",
            artifacts=("skills/n2d/_lib/n2d_contract.py",),
            evidence_family="artifact_integrity",
        ))
        return res
    if STORYBOARD_APPEARANCE_IMPORT_ERROR:
        res["findings"].append(_row(
            "block",
            "MVIEW 无法加载与 identity gate 同源的结构化 storyboard 出场索引；"
            "为避免审查仅信 registry 自报档位而漏掉跨十集角色，已 fail-closed 阻断。",
            stage="image",
            artifacts=("skills/n2d-review/scripts/gate_core.py",),
            evidence_family="artifact_integrity",
        ))
        return res
    required_forms = _core_character_forms(root)
    core = _unique(cid for cid, _form in required_forms)
    if not required_forms:
        res["notes"].append("无核心/长线角色登记，MVIEW 暂不强制。")
        return res
    data, rel = _identity_eval_pack(root)
    if data is None:
        res["findings"].append(_row(
            "block",
            f"核心/长线角色 {', '.join(core[:6])} 缺 identity_eval_pack / multiview_identity_pack；"
            "未完成正面/前3/4/侧面/后3/4/背面五角 + turnaround + 表情/脸锚桶的固定身份验收，"
            "不得进入分镜出图。",
            stage="image",
            artifacts=("设定库/identity_eval_pack.json", "生产数据/identity_eval_pack.json"),
            evidence_family="text_contract",
        ))
        return res
    if not isinstance(data, Mapping) or data.get("kind") != "n2d_identity_eval_pack" or data.get("version") != 3:
        res["findings"].append(_row(
            "block",
            "identity_eval_pack 必须是 kind=n2d_identity_eval_pack、version=3；旧版或自定义 JSON 不能作为核心人物多视图放行证据。",
            stage="image",
            artifacts=(rel,),
            evidence_family="artifact_integrity",
        ))
    declared_registry_sha = ""
    if isinstance(data, Mapping):
        source_fp = data.get("source_fingerprint") if isinstance(data.get("source_fingerprint"), Mapping) else {}
        declared_registry_sha = str(
            data.get("identity_registry_sha256") or source_fp.get("identity_registry_sha256") or ""
        ).strip()
    current_registry_sha = _registry_sha256(root)
    if not declared_registry_sha or not current_registry_sha or declared_registry_sha != current_registry_sha:
        res["findings"].append(_row(
            "block",
            "identity_eval_pack 缺当前 identity_registry_sha256 或指纹已过期；定妆/形态/档位改动后必须重建验收包。",
            stage="image",
            artifacts=(rel, "出图/共享/identity_registry.json"),
            evidence_family="artifact_integrity",
        ))
    rows = _identity_eval_rows(data)
    by_key: Dict[Tuple[str, str], Mapping[str, Any]] = {}
    duplicate_keys: set[Tuple[str, str]] = set()
    for row in rows:
        cid = _eval_row_character(row)
        if cid:
            key = (cid, _eval_row_form(row) or "default")
            if key in by_key:
                duplicate_keys.add(key)
            else:
                by_key[key] = row
        verdict = str(row.get("verdict") or row.get("status") or row.get("result") or "").lower()
        declared_row_statuses = {
            str(row.get(key) or "").strip().lower()
            for key in ("verdict", "status", "result")
            if str(row.get(key) or "").strip()
        }
        bucket_failures = [
            bucket for bucket, value in _eval_bucket_map(row).items()
            if _bucket_status(value) in MULTIVIEW_FAIL_STATUSES
        ]
        if declared_row_statuses & MULTIVIEW_FAIL_STATUSES or bucket_failures:
            res["findings"].append(_row(
                "block",
                f"多视角身份测试未通过：{cid or '(unknown)'}"
                f"{('/' + _eval_row_form(row)) if _eval_row_form(row) else ''} "
                f"verdict={verdict or 'missing'}"
                f"{f'; failed_buckets={','.join(bucket_failures)}' if bucket_failures else ''}。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="face_embedding",
            ))
    for cid, form_name in sorted(duplicate_keys):
        res["findings"].append(_row(
            "block",
            f"identity_eval_pack 对 {cid}/{form_name} 存在重复测试行；无法确定哪条是有效放行证据。",
            stage="image",
            artifacts=(rel,),
            entity_id=cid,
            evidence_family="artifact_integrity",
        ))
    registry_forms = _multiview_registry_form_index(root)
    for cid, form_name in required_forms:
        row = by_key.get((cid, form_name))
        if not row:
            res["findings"].append(_row(
                "block",
                f"identity_eval_pack 缺核心角色形态 {cid}/{form_name} 的测试行。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="text_contract",
            ))
            continue
        registry_entry = registry_forms.get((cid, form_name))
        if not registry_entry:
            res["findings"].append(_row(
                "block",
                f"当前 identity_registry 无法精确解析 {cid}/{form_name}；多视图证据不可绑定。",
                stage="image",
                artifacts=(rel, "出图/共享/identity_registry.json"),
                entity_id=cid,
                evidence_family="artifact_integrity",
            ))
            continue
        _registry_char, registry_form, expected_tier = registry_entry
        if str(row.get("library_tier") or "").strip() != expected_tier:
            res["findings"].append(_row(
                "block",
                f"{cid}/{form_name} 多视图验收行 library_tier 与当前剧情推导档位不一致（应为 {expected_tier}）。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="artifact_integrity",
            ))
        row_verdict = str(row.get("verdict") or row.get("status") or row.get("result") or "").strip().lower()
        if row_verdict not in MULTIVIEW_PASS_STATUSES:
            res["findings"].append(_row(
                "block",
                f"{cid}/{form_name} 多视图验收行缺显式 pass 结论（当前 {row_verdict or 'missing'}）。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="structured_review",
            ))
        bucket_map = _eval_bucket_map(row)
        path_groups: Dict[str, List[str]] = defaultdict(list)
        realpath_groups: Dict[str, List[str]] = defaultdict(list)
        current_sha_groups: Dict[str, List[str]] = defaultdict(list)
        decoded_pixel_fingerprint_groups: Dict[str, List[str]] = defaultdict(list)
        for bucket_name in MULTIVIEW_BUCKETS:
            value = bucket_map.get(bucket_name)
            if not isinstance(value, Mapping):
                continue
            raw_path = str(
                value.get("path") or value.get("artifact_path") or value.get("image_path") or ""
            ).strip()
            if not raw_path:
                continue
            path_groups[raw_path].append(bucket_name)
            _canonical_rel, realpath, path_errors = _resolve_multiview_evidence_path(
                root, raw_path, source="pack_evidence"
            )
            if path_errors:
                continue
            realpath_groups[realpath].append(bucket_name)
            current_sha = _sha256_path(realpath)
            if current_sha:
                current_sha_groups[current_sha].append(bucket_name)
            current_pixel_fingerprint, fingerprint_errors = png_decoded_pixel_fingerprint(
                realpath
            )
            if current_pixel_fingerprint and not fingerprint_errors:
                decoded_pixel_fingerprint_groups[current_pixel_fingerprint].append(bucket_name)
        duplicate_paths = sorted(path for path, names in path_groups.items() if len(names) > 1)
        duplicate_realpaths = sorted(
            names for names in realpath_groups.values() if len(names) > 1
        )
        duplicate_png_sha = sorted(
            names for names in current_sha_groups.values() if len(names) > 1
        )
        duplicate_decoded_pixel_fingerprint = sorted(
            names
            for names in decoded_pixel_fingerprint_groups.values()
            if len(names) > 1
        )
        if duplicate_paths:
            res["findings"].append(_row(
                "block",
                f"{cid}/{form_name} 多视图验收复用了同一图像路径：{', '.join(duplicate_paths)}；"
                "核心人物必须是独立可投喂的五角、表情与 turnaround 资产。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="artifact_integrity",
            ))
        if duplicate_realpaths:
            res["findings"].append(_row(
                "block",
                f"{cid}/{form_name} duplicate_canonical_realpath："
                f"{'; '.join('/'.join(names) for names in duplicate_realpaths)}；"
                "软链、a/../b 或其他路径别名不能伪装成独立多视图资产。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="artifact_integrity",
            ))
        if duplicate_png_sha:
            res["findings"].append(_row(
                "block",
                f"{cid}/{form_name} duplicate_png_sha："
                f"{'; '.join('/'.join(names) for names in duplicate_png_sha)}；"
                "复制同一像素到不同文件名仍不是独立视角。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="artifact_integrity",
            ))
        if duplicate_decoded_pixel_fingerprint:
            res["findings"].append(_row(
                "block",
                f"{cid}/{form_name} duplicate_decoded_pixel_fingerprint："
                f"{'; '.join('/'.join(names) for names in duplicate_decoded_pixel_fingerprint)}；"
                "改变 PNG 压缩、过滤器或 metadata 不会把同一解码像素变成独立视角。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="artifact_integrity",
            ))
        missing = [bucket for bucket in MULTIVIEW_BUCKETS if bucket not in bucket_map]
        if missing:
            res["findings"].append(_row(
                "block",
                f"{cid}/{form_name} 多视角身份测试桶缺失：{', '.join(missing)}；"
                "必须覆盖正脸/前45度/侧脸/后45度/背影/表情，不能只在正脸上看起来一致。",
                stage="image",
                artifacts=(rel,),
                entity_id=cid,
                evidence_family="face_embedding",
            ))
        for bucket in MULTIVIEW_BUCKETS:
            if bucket not in bucket_map:
                continue
            errors = _bucket_evidence_errors(
                root,
                bucket_map[bucket],
                character_id=cid,
                form_name=form_name,
                library_tier=expected_tier,
                bucket=bucket,
                registry_form=registry_form,
            )
            if errors:
                res["findings"].append(_row(
                    "block",
                    f"{cid}/{form_name} 多视图桶 {bucket} 缺可核验通过证据：{', '.join(errors)}。"
                    "identity_eval_pack v2 当前只接受绑定 current PNG SHA 的结构化人审收据；"
                    "embedding/几何证据在校准 schema 与独立回归落地前不得自报放行。",
                    stage="image",
                    artifacts=(rel,),
                    entity_id=cid,
                    evidence_family="artifact_integrity",
                ))
    return res


def check_entity_memory_bank(root: str, ep: str) -> dict:
    """Long-range entity memory closure.

    The bank is a quality-gated memory of accepted shots/crops, keyed by entity.
    It lets later episodes retrieve canonical/supplementary references by entity,
    view, expression, location, and reliability rather than relying only on a
    static launch-day reference group.
    """
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，实体记忆库检查跳过。")
        return res
    appearances = _entity_appearances(root, ep)
    recurrent = {
        eid: row for eid, row in appearances.items()
        if len(row.get("clips") or []) >= 2 or eid in _core_character_ids(root)
    }
    if not recurrent:
        res["notes"].append("本集没有重复出现实体或核心角色，EMB 不强制。")
    data, rel = _entity_memory_bank(root)
    if data is None:
        if recurrent:
            sample = ", ".join(sorted(recurrent)[:6])
            res["findings"].append(_row(
                "warn",
                f"本集有重复/核心实体（{sample}）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。",
                stage="image",
                artifacts=("生产数据/entity_memory_bank.json", "出图/共享/entity_memory_bank.json", f"脚本/{ep}/storyboard.json"),
            ))
        return res

    entries = _entity_memory_entries(data)
    by_entity: Dict[str, List[dict]] = defaultdict(list)
    for entry in entries:
        eid = _entry_entity(entry)
        if eid:
            by_entity[eid].append(entry)
        missing = []
        if not eid:
            missing.append("entity_id")
        if not (entry.get("source_shot") or entry.get("source_clip") or entry.get("source_episode")):
            missing.append("source_shot/source_episode")
        media = _entry_media(entry)
        if not media:
            missing.append("crop_path/media_path")
        if entry.get("reliability") in (None, "") and entry.get("quality_score") in (None, ""):
            missing.append("reliability/quality_score")
        if not (entry.get("qc_verdict") or entry.get("verdict") or entry.get("accepted")):
            missing.append("qc_verdict/accepted")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"entity_memory_bank 条目缺字段：{', '.join(missing)}。",
                stage="image",
                artifacts=(rel,),
                entity_id=eid,
            ))
        if media and not _artifact_exists(root, media):
            res["findings"].append(_row(
                "warn",
                f"实体记忆条目引用的媒体不存在：{media}。",
                stage="image",
                artifacts=(rel,),
                entity_id=eid,
            ))
        verdict = str(entry.get("qc_verdict") or entry.get("verdict") or "").lower()
        accepted = entry.get("accepted")
        quality = _num(entry.get("reliability") if entry.get("reliability") not in (None, "") else entry.get("quality_score"))
        if verdict in {"block", "fail", "failed", "reject", "rejected"} or accepted is False:
            res["findings"].append(_row(
                "block",
                f"{eid or '(unknown)'} 的实体记忆条目标记为未通过/未接受，不能作为后续参考源。",
                stage="image",
                artifacts=(rel,),
                entity_id=eid,
            ))
        elif quality is not None and quality < 0.70:
            res["findings"].append(_row(
                "warn",
                f"{eid or '(unknown)'} 的实体记忆 reliability={quality:.2f} 偏低；不要把低置信截图当长线参考。",
                stage="image",
                artifacts=(rel,),
                entity_id=eid,
            ))
    for eid, row in recurrent.items():
        if not by_entity.get(eid):
            res["findings"].append(_row(
                "warn",
                f"重复/核心实体 {eid} 出现于 {len(row.get('clips') or [])} 镜，但 entity_memory_bank 没有已验收记忆条目。",
                stage="image",
                artifacts=(rel, f"脚本/{ep}/storyboard.json"),
                entity_id=eid,
            ))
        elif not any(_entry_used_for_generation(entry) for entry in by_entity.get(eid, [])):
            res["findings"].append(_row(
                "warn",
                f"重复/核心实体 {eid} 有实体记忆，但缺 retrieved_for/used_for_generation/reference_plan；"
                "记忆库若只在审计后沉淀、未在生成前检索，长程身份证据不会真正影响本集出图/出视频。",
                stage="image",
                artifacts=(rel, f"脚本/{ep}/storyboard.json"),
                entity_id=eid,
                evidence_family="text_contract",
            ))

    for char in _registry_characters(root):
        cid = str(char.get("id") or char.get("character_id") or char.get("name") or "").strip()
        if cid not in _core_character_ids(root):
            continue
        for form in _character_forms(char):
            form_name = str(form.get("form") or "常态")
            if _expression_anchor_count(form) < 3:
                res["findings"].append(_row(
                    "warn",
                    f"核心/长线角色 {cid}/{form_name} 表情锚点少于 3 个；情绪近景长期复用时容易表演漂移。",
                    stage="image",
                    artifacts=("出图/共享/identity_registry.json",),
                    entity_id=cid,
                ))
            if not _has_performance_signature(form):
                res["findings"].append(_row(
                    "warn",
                    f"核心/长线角色 {cid}/{form_name} 缺 performance_signature（站姿/眼神/惯用手势）；脸像但演法漂时难复核。",
                    stage="image",
                    artifacts=("出图/共享/identity_registry.json",),
                    entity_id=cid,
                ))
    res["notes"].append(f"entity_memory_bank 条目 {len(entries)}，本集实体 {len(appearances)}，重复/核心实体 {len(recurrent)}。")
    return res


def _row(verdict: str, message: str, *, shot: str = "", stage: str = "image",
         artifacts: Sequence[str] = (), **extra: Any) -> dict:
    row = {
        "verdict": verdict,
        "message": message,
        "return_to_stage": stage,
        "affected_shots": [shot] if shot else [],
        "affected_artifacts": list(artifacts),
    }
    row.update(extra)
    return row


def check_object_permanence(root: str, ep: str) -> dict:
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，物件常驻检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    persistent = _persistent_assets(root)
    expected_by_loc: Dict[str, Dict[str, bool]] = defaultdict(dict)
    for aid, asset in persistent.items():
        loc = str(asset.get("location") or asset.get("loc") or asset.get("scene") or "").split("/")[0].strip()
        if loc:
            expected_by_loc[loc][aid] = True
    if persistent:
        res["notes"].append(f"asset_registry 登记常驻资产 {len(persistent)} 个，缺席按违锁检查。")

    seen_any = False
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        loc = _loc_of(clip, text)
        ids = [aid for aid in _asset_ids(text) if aid.startswith(("PROP_", "WEAPON_", "OUTFIT_", "VFX_"))]
        if ids:
            seen_any = True
        expected = expected_by_loc.get(loc, {}) if loc else {}
        missing = [aid for aid in expected if aid not in ids]
        if missing and not _is_exempt_view(text):
            for aid in missing:
                sev = "block" if expected.get(aid) else "warn"
                res["findings"].append(_row(
                    sev,
                    f"{loc or '同场景'} 常驻物件 {aid} 已建立但本镜未回读；若确实画外/被遮挡，请写明豁免原因。",
                    shot=label,
                    stage="image",
                    artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md", "出图/共享/asset_registry.json"),
                    asset=aid,
                    loc=loc,
                ))
        if loc:
            for aid in ids:
                expected_by_loc[loc].setdefault(aid, aid in persistent)
    if not seen_any and not persistent:
        res["notes"].append("未检测到 PROP/WEAPON/OUTFIT/VFX 资产 ID；物件常驻只能做人审，建议给常驻道具/武器补 asset_registry id。")
    return res


def _visual_state_contract_text(sb: Optional[dict]) -> str:
    vc = (sb or {}).get("visual_contract") if isinstance(sb, dict) else {}
    if not isinstance(vc, dict):
        return ""
    return _json_text(vc.get("角色状态演进") or vc.get("character_state_progression") or "")


def _image_qc_precision(root: str, ep: str) -> str:
    data = _load_json(os.path.join(root, "生产数据", "image_qc", ep, f"image_qc_{ep}.json"))
    if not isinstance(data, dict):
        return ""
    env = data.get("qc_environment") if isinstance(data.get("qc_environment"), dict) else {}
    return str(data.get("precision_level") or env.get("precision_level") or data.get("precision") or "").strip()


def check_axis_state_readback(root: str, ep: str) -> dict:
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，视线/状态回读检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    state_contract = _visual_state_contract_text(sb)
    high_risk = 0
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        char_count = len(_char_ids(text))
        needs_axis = char_count >= 2 or any(w in text for w in ("对话", "反打", "过肩", "看向", "凝视"))
        needs_state = bool(state_contract) and char_count >= 1
        if needs_axis:
            high_risk += 1
            if not any(w.lower() in text.lower() for w in AXIS_WORDS):
                res["findings"].append(_row(
                    "warn",
                    "多人/对话镜缺视线/轴线可回读字段；像素 X1 误报或缺库时无法复核该镜越轴风险。",
                    shot=label,
                    stage="image",
                    artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md"),
                ))
        if needs_state and not any(w.lower() in text.lower() for w in STATE_WORDS):
            res["findings"].append(_row(
                "warn",
                "本集有角色状态演进契约，但该角色镜缺状态回读词；容易出现伤/泪/战损提前泄露或自愈。",
                shot=label,
                stage="image",
                artifacts=(f"脚本/{ep}/storyboard.json", f"出图/{ep}/prompt/01_分镜出图.md"),
            ))
    precision = _image_qc_precision(root, ep)
    if high_risk and precision and precision != "full":
        res["findings"].append(_row(
            "warn",
            f"{high_risk} 个视线/状态高风险镜当前 image_qc 精度为 {precision}；需要 full QC 或人审签收，不能把降级绿灯当作像素一致已验证。",
            stage="review",
            artifacts=(f"生产数据/image_qc/{ep}/image_qc_{ep}.json",),
        ))
    return res


def _state_transition_manifest(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"state_transition_event_{ep}.json"),
        os.path.join("生产数据", f"state_transition_manifest_{ep}.json"),
        os.path.join("生产数据", f"state_transition_{ep}.json"),
        os.path.join("脚本", ep, "state_transition_manifest.json"),
        os.path.join("设定库", "state_transition_manifest.json"),
    ))


def _transition_entries(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("transitions") or data.get("state_transitions") or data.get("items") or []
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _clip_has_state_transition(text: str, clip: Mapping[str, Any]) -> bool:
    if isinstance(clip.get("state_transition"), (dict, list)):
        return True
    cont = clip.get("continuity")
    if isinstance(cont, Mapping) and isinstance(cont.get("state_transition"), (dict, list)):
        return True
    low = (text or "").lower()
    return any(w.lower() in low for w in STATE_TRANSITION_WORDS)


def _entry_clip(entry: Mapping[str, Any]) -> str:
    return _clip_num(str(
        entry.get("clip")
        or entry.get("clip_id")
        or entry.get("shot")
        or entry.get("from_clip")
        or ""
    ))


def _entry_frames(entry: Mapping[str, Any]) -> List[Any]:
    frames: List[Any] = []
    for key in ("before_frame", "after_frame", "start_frame", "end_frame"):
        if entry.get(key):
            frames.append(entry.get(key))
    for item in _as_list(entry.get("evidence_frames") or entry.get("frames")):
        if isinstance(item, Mapping):
            frames.append(item.get("path") or item.get("frame") or item.get("image"))
        else:
            frames.append(item)
    return [f for f in frames if f]


def check_state_transition_verification(root: str, ep: str) -> dict:
    """状态变化从“prompt 写了”升级为“视频/帧证据能证明前后状态”的审计入口。"""
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，状态转场验证跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    candidate_clips: List[str] = []
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        if _clip_has_state_transition(text, clip):
            candidate_clips.append(label)
    data, manifest_rel = _state_transition_manifest(root, ep)
    if not candidate_clips and data is None:
        res["notes"].append("未检测到显式状态变化镜，ST1 跳过。")
        return res
    if data is None:
        res["findings"].append(_row(
            "warn",
            f"检测到 {len(candidate_clips)} 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。",
            stage="script_stage2",
            artifacts=(f"脚本/{ep}/storyboard.json", f"生产数据/state_transition_manifest_{ep}.json"),
        ))
        return res

    entries = _transition_entries(data)
    by_clip = {_entry_clip(e): e for e in entries if _entry_clip(e)}
    for label in candidate_clips:
        if label not in by_clip:
            res["findings"].append(_row(
                "warn",
                "本镜含状态变化语义，但 state_transition_manifest 未登记该 Clip 的 before/after 验证项。",
                shot=label,
                stage="script_stage2",
                artifacts=(manifest_rel, f"脚本/{ep}/storyboard.json"),
            ))
    for entry in entries:
        label = _entry_clip(entry)
        missing = []
        if not (entry.get("subject") or entry.get("asset") or entry.get("entity") or entry.get("character")):
            missing.append("subject/entity")
        if not (entry.get("from_state") or entry.get("before") or entry.get("initial_state")):
            missing.append("from_state")
        if not (entry.get("to_state") or entry.get("after") or entry.get("target_state")):
            missing.append("to_state")
        if not (entry.get("cause") or entry.get("trigger") or entry.get("reason")):
            missing.append("cause/trigger")
        if not (entry.get("visual_evidence_due") or entry.get("evidence_due_stage") or entry.get("evidence_due")):
            missing.append("visual_evidence_due")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"状态转场条目缺字段：{', '.join(missing)}。",
                shot=label,
                stage="script_stage2",
                artifacts=(manifest_rel,),
            ))
        if entry.get("legal_reset") is True and not (entry.get("reset_reason") or entry.get("cause") or entry.get("trigger")):
            res["findings"].append(_row(
                "warn",
                "状态转场标 legal_reset=true 但缺 reset_reason/cause；无法区分有意治愈/伪装解除/时间跳跃与非法状态回退。",
                shot=label,
                stage="script_stage2",
                artifacts=(manifest_rel,),
                evidence_family="text_contract",
            ))
        elif entry.get("legal_reset") is None and any(
            token in _json_text(entry)
            for token in ("愈合", "消失", "复原", "解除", "重置", "梦境", "time skip", "reset", "heal")
        ):
            res["findings"].append(_row(
                "warn",
                "本状态转场看起来像合法重置/复原，但缺 legal_reset=true/false；gate 只能按普通状态变化处理，容易误判非法自愈或提前泄露。",
                shot=label,
                stage="script_stage2",
                artifacts=(manifest_rel,),
                evidence_family="text_contract",
            ))
        frames = _entry_frames(entry)
        if len(frames) < 2:
            res["findings"].append(_row(
                "warn",
                "状态转场缺 before/after 证据帧；只靠文字无法证明视频完成了变化。",
                shot=label,
                stage="video",
                artifacts=(manifest_rel,),
            ))
        else:
            missing_frames = [str(f) for f in frames if not _artifact_exists(root, f)]
            if missing_frames:
                res["findings"].append(_row(
                    "warn",
                    f"状态转场证据帧不存在：{', '.join(missing_frames[:4])}。",
                    shot=label,
                    stage="video",
                    artifacts=(manifest_rel,),
                ))
        questions = entry.get("vqa_questions") or entry.get("checks") or entry.get("questions")
        if not _as_list(questions):
            res["findings"].append(_row(
                "warn",
                "状态转场缺 VQA/人审判断题；建议至少写“初始是否为 A / 最终是否为 B / 是否完成变化”。",
                shot=label,
                stage="review",
                artifacts=(manifest_rel,),
            ))
        if _final_cuts(root, ep) and str(entry.get("status") or entry.get("verdict") or "").lower() not in {"pass", "ok", "verified"} and entry.get("verified") is not True:
            res["findings"].append(_row(
                "warn",
                "成片已存在，但该状态转场尚未标记 verified/pass；交付前需要抽帧或人审签收。",
                shot=label,
                stage="review",
                artifacts=(manifest_rel, f"合成/{ep}"),
            ))
    return res


def _possession_ledger(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"possession_ledger_{ep}.json"),
        os.path.join("生产数据", f"asset_possession_{ep}.json"),
        os.path.join("脚本", ep, "possession_ledger.json"),
        os.path.join("设定库", "possession_ledger.json"),
    ))


def _possession_events(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("events") or data.get("possessions") or data.get("transfers") or data.get("items") or []
        if isinstance(raw, dict):
            rows = []
            for key, value in raw.items():
                if isinstance(value, dict):
                    rows.append({"asset": key, **value})
                else:
                    rows.append({"asset": key, "holder": value})
            raw = rows
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _pos_event_clip(event: Mapping[str, Any]) -> str:
    return _clip_num(str(event.get("clip") or event.get("clip_id") or event.get("shot") or ""))


def _pos_event_asset(event: Mapping[str, Any]) -> str:
    return str(event.get("asset") or event.get("prop") or event.get("item") or event.get("asset_id") or "").strip()


def _pos_event_action(event: Mapping[str, Any]) -> str:
    return str(event.get("action") or event.get("event") or event.get("type") or "").strip().lower()


def _pos_event_holder(event: Mapping[str, Any]) -> str:
    return str(event.get("holder") or event.get("owner") or event.get("to_holder") or event.get("to") or "").strip()


def check_possession_ledger(root: str, ep: str) -> dict:
    """跨镜/跨场跟踪道具持有状态，避免“道具瞬移”只被同镜交互规则偶然抓到。"""
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，持有账本检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    mentions: List[dict] = []
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        for asset, holder in _holder_mentions(text):
            if asset.startswith("PROP_"):
                mentions.append({"clip": label, "asset": asset, "holder": holder, "text": text})
    if not mentions:
        res["notes"].append("未检测到显式 PROP_ 持有描述，POS 跳过。")
        return res

    data, ledger_rel = _possession_ledger(root, ep)
    if data is None:
        res["findings"].append(_row(
            "warn",
            "本集存在道具持有镜，但缺 possession_ledger；跨场持有/交接/丢失只能靠上下文记忆，建议落持有账本。",
            stage="script_stage2",
            artifacts=(f"脚本/{ep}/storyboard.json", f"生产数据/possession_ledger_{ep}.json"),
        ))

    by_prop: Dict[str, List[dict]] = defaultdict(list)
    for item in mentions:
        by_prop[item["asset"]].append(item)
    transfer_events: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    if data is not None:
        for event in _possession_events(data):
            asset = _pos_event_asset(event)
            clip = _pos_event_clip(event)
            missing = []
            if not asset:
                missing.append("asset/prop")
            if not clip:
                missing.append("clip")
            if not (_pos_event_action(event) or _pos_event_holder(event)):
                missing.append("action/holder")
            if missing:
                res["findings"].append(_row(
                    "warn",
                    f"持有账本条目缺字段：{', '.join(missing)}。",
                    shot=clip,
                    stage="script_stage2",
                    artifacts=(ledger_rel,),
                ))
            if asset and clip:
                transfer_events[(asset, clip)].append(event)

    for asset, rows in by_prop.items():
        rows.sort(key=lambda r: _clip_index(r["clip"]))
        prev: Optional[dict] = None
        for row in rows:
            if data is not None and not transfer_events.get((asset, row["clip"])):
                res["findings"].append(_row(
                    "warn",
                    f"{asset} 在 {row['clip']} 有持有状态，但 possession_ledger 未登记本镜状态。",
                    shot=row["clip"],
                    stage="script_stage2",
                    artifacts=(ledger_rel, f"脚本/{ep}/storyboard.json"),
                    asset=asset,
                ))
            if prev and row["holder"] != prev["holder"]:
                text = row.get("text") or ""
                events = transfer_events.get((asset, row["clip"]), [])
                declared_transfer = any(_pos_event_action(e) in {"transfer", "handoff", "release", "drop", "pickup", "acquire", "move"} for e in events)
                if not declared_transfer and not any(w.lower() in text.lower() for w in TRANSFER_WORDS + RELEASE_WORDS):
                    res["findings"].append(_row(
                        "block",
                        f"{asset} 持有者从 {prev['holder']} 跳到 {row['holder']}，但缺 transfer/release/pickup 账本事件。",
                        shot=row["clip"],
                        stage="script_stage2",
                        artifacts=(ledger_rel or f"脚本/{ep}/storyboard.json",),
                        asset=asset,
                    ))
            prev = row
    return res


def _has_contact(text: str) -> bool:
    low = (text or "").lower()
    return any(w.lower() in low for w in CONTACT_WORDS)


def _has_interaction_graph(clip: Mapping[str, Any], text: str) -> bool:
    if isinstance(clip.get("interaction_graph"), (dict, list)):
        return True
    tc = clip.get("template_contract")
    if isinstance(tc, Mapping) and isinstance(tc.get("interaction_graph"), (dict, list)):
        return True
    return any(token in text for token in ("interaction_graph", "contact_graph", "接触图", "接触点", "持有状态", "左右手", "left_hand", "right_hand"))


def _holder_mentions(text: str) -> List[Tuple[str, str]]:
    mentions: List[Tuple[str, str]] = []
    direct = list(re.finditer(
        r"([一-龥A-Za-z0-9_]{2,12})(?:正|在|仍|依旧|双手|单手|左手|右手)?"
        r"(?:手持|握|拿|抓|举|抱着|持有|holds?|grabs?)\s*"
        r"(PROP_[\w\-\u4e00-\u9fff]+?)(?=$|[\"'，。；,;\s}]|"
        + "|".join(re.escape(x) for x in ASSET_TAIL_ACTIONS) + r")",
        text or "",
        re.I,
    ))
    for m in direct:
        mentions.append((_asset_ids(m.group(2))[0], m.group(1)))
    if mentions:
        return mentions
    for aid in _asset_ids(text):
        if not aid.startswith("PROP_"):
            continue
        before = text[: max(0, text.find(aid))]
        matches = list(re.finditer(
            r"([一-龥A-Za-z0-9_]{2,12})(?:正|在|仍|依旧|双手|单手|左手|右手)?"
            r"(?:手持|握|拿|抓|举|抱着|持有|holds?|grabs?)",
            before[-80:],
            re.I,
        ))
        if matches:
            mentions.append((aid, matches[-1].group(1)))
    return mentions


def _load_routes(root: str, ep: str) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for rel in (
        os.path.join("生产数据", "video_model_routes.json"),
        os.path.join("出视频", ep, "prompt", "video_model_routes.json"),
    ):
        data = _load_json(os.path.join(root, rel))
        if isinstance(data, dict):
            routes = data.get("routes") or data.get("clips") or []
            if isinstance(routes, dict):
                routes = [{**(v if isinstance(v, dict) else {}), "clip_id": k} for k, v in routes.items()]
        elif isinstance(data, list):
            routes = data
        else:
            routes = []
        for route in routes or []:
            if not isinstance(route, dict):
                continue
            cid = _clip_num(str(route.get("clip_id") or route.get("id") or route.get("clip") or ""))
            if cid:
                out[cid] = route
    return out


def check_interaction_graph(root: str, ep: str) -> dict:
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，交互接触检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    routes = _load_routes(root, ep)
    holder_by_prop: Dict[str, str] = {}
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        if not _has_contact(text):
            continue
        if not _has_interaction_graph(clip, text):
            res["findings"].append(_row(
                "warn",
                "物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。",
                shot=label,
                stage="script_stage2",
                artifacts=(f"脚本/{ep}/storyboard.json",),
            ))
        route = routes.get(label)
        motion = route.get("motion_control") if isinstance(route, dict) else None
        if route and not isinstance(motion, Mapping):
            res["findings"].append(_row(
                "warn",
                "接触镜已有视频路由但缺 motion_control 契约；出视频 fallback 时接触/遮挡稳定性不可审计。",
                shot=label,
                stage="video_prompt",
                artifacts=(f"出视频/{ep}/prompt/video_model_routes.json",),
            ))
        releasing = any(w in text for w in RELEASE_WORDS)
        transfer = any(w in text for w in TRANSFER_WORDS)
        for aid, holder in _holder_mentions(text):
            prev = holder_by_prop.get(aid)
            if prev and holder != prev and not transfer:
                res["findings"].append(_row(
                    "block",
                    f"{aid} 持有者从 {prev} 变成 {holder}，但本镜缺递交/掉落/拾取因果；会造成道具瞬移。",
                    shot=label,
                    stage="script_stage2",
                    artifacts=(f"脚本/{ep}/storyboard.json",),
                    asset=aid,
                ))
            holder_by_prop[aid] = "" if releasing else holder
    return res


def _interaction_graphs(clip: Mapping[str, Any]) -> List[dict]:
    raw = clip.get("interaction_graph") or clip.get("contact_graph")
    tc = clip.get("template_contract")
    if raw in (None, "") and isinstance(tc, Mapping):
        raw = tc.get("interaction_graph") or tc.get("contact_graph")
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _graph_has(graphs: Sequence[Mapping[str, Any]], *keys: str) -> bool:
    for graph in graphs:
        for key in keys:
            value = graph.get(key)
            if value not in (None, "", [], {}):
                return True
    return False


def check_interaction_schema(root: str, ep: str) -> dict:
    """把 I1 的自由文本 contact_graph 升级为可机器校验的交互图谱 schema。"""
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，结构化交互图谱检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        if not _has_contact(text):
            continue
        high_risk = any(w.lower() in text.lower() for w in HIGH_RISK_INTERACTION_WORDS)
        graphs = _interaction_graphs(clip)
        if not graphs:
            res["findings"].append(_row(
                "block" if high_risk else "warn",
                "接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。",
                shot=label,
                stage="script_stage2",
                artifacts=(f"脚本/{ep}/storyboard.json",),
            ))
            continue
        missing = []
        if len(_char_ids(text)) >= 2 and not _graph_has(graphs, "participants", "actors", "entities"):
            missing.append("participants")
        if not _graph_has(graphs, "contact_points", "contact_point", "body_contact", "touch_points"):
            missing.append("contact_points")
        if not _graph_has(graphs, "body_part_ownership", "body_parts", "left_hand", "right_hand", "holder_state"):
            missing.append("body_part_ownership/holder_state")
        if high_risk and not _graph_has(graphs, "occlusion_order", "depth_order", "layer_order"):
            missing.append("occlusion_order")
        if any(w in text for w in ("打斗", "命中", "刺中", "格挡", "推开", "击中")) and not _graph_has(graphs, "force_direction", "motion_vector", "impact_direction"):
            missing.append("force_direction")
        if any(w in text for w in TRANSFER_WORDS + RELEASE_WORDS) and not _graph_has(graphs, "transfer_event", "release_frame", "handoff", "pickup_frame"):
            missing.append("transfer_event/release_frame")
        if missing:
            res["findings"].append(_row(
                "block" if high_risk else "warn",
                f"interaction_graph 缺 schema 字段：{', '.join(missing)}。",
                shot=label,
                stage="script_stage2",
                artifacts=(f"脚本/{ep}/storyboard.json",),
            ))
    return res


def _final_cuts(root: str, ep: str) -> List[str]:
    import glob
    return sorted(glob.glob(os.path.join(root, "合成", ep, "成片_*.mp4")))


def _target_platform(root: str) -> str:
    settings = _read(os.path.join(root, "_设置.md"))
    m = re.search(r"(?m)^[\s\-*>|]*目标平台\s*[:：]\s*(.+?)\s*$", settings)
    return (m.group(1).strip().split("|")[0] if m else "default").lower()


def _run_loudness(root: str, ep: str) -> Optional[dict]:
    script_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d-compose"))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    try:
        import loudness_conform  # type: ignore
        return loudness_conform.analyze(root, ep, platform=_target_platform(root))
    except Exception as exc:
        return {"available": False, "verdict": "ok", "notes": [f"响度检查调用失败：{exc}"]}


def _rhythm_variety(sb: Optional[dict]) -> bool:
    clips = (sb or {}).get("clips") or []
    values = {str(c.get("rhythm") or c.get("节奏") or "") for c in clips if isinstance(c, dict)}
    return len([v for v in values if v]) >= 2


def check_final_composite(root: str, ep: str) -> dict:
    sb, _ = _storyboard(root, ep)
    res = {"available": bool(_final_cuts(root, ep)), "findings": [], "notes": []}
    if not res["available"]:
        res["notes"].append("未检测到成片，成片统一检查等待 compose/review 阶段。")
        return res
    loud = _run_loudness(root, ep)
    if loud:
        for note in loud.get("notes", []) or []:
            res["notes"].append(str(note))
        verdict = str(loud.get("verdict") or "ok")
        if verdict in {"warn", "block"}:
            res["findings"].append(_row(
                verdict,
                f"成片响度不贴目标：LUFS={loud.get('measured_lufs')} target={loud.get('target')} true_peak={loud.get('true_peak')}",
                stage="compose",
                artifacts=(f"合成/{ep}",),
            ))
    routes = _load_routes(root, ep)
    providers = {str(r.get("primary_backend") or "") for r in routes.values() if r.get("primary_backend")}
    if len(providers) >= 2:
        evidence = any(os.path.isfile(os.path.join(root, rel)) for rel in (
            os.path.join("生产数据", f"color_match_{ep}.json"),
            os.path.join("合成", ep, "color_match_report.json"),
        ))
        if not evidence:
            res["findings"].append(_row(
                "warn",
                f"本集视频混用了 {len(providers)} 个 primary 后端，但缺色彩匹配报告；混剪易出现亮度/色温跳。",
                stage="compose",
                artifacts=(f"出视频/{ep}/prompt/video_model_routes.json", f"合成/{ep}"),
            ))
    if _rhythm_variety(sb) and not os.path.isfile(os.path.join(root, "生产数据", f"tension_mix_{ep}.json")):
        res["findings"].append(_row(
            "warn",
            "storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。",
            stage="compose",
            artifacts=(f"脚本/{ep}/storyboard.json", f"合成/{ep}"),
        ))
    if not any(os.path.isfile(os.path.join(root, rel)) for rel in (
        os.path.join("生产数据", f"room_tone_{ep}.json"),
        os.path.join("合成", ep, "room_tone.json"),
        os.path.join("生产数据", f"foley_{ep}.json"),
    )):
        res["findings"].append(_row(
            "warn",
            "缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。",
            stage="compose",
            artifacts=(f"合成/{ep}",),
        ))
    return res


def _native_av_physics(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"native_av_physics_{ep}.json"),
        os.path.join("出视频", ep, "native_av_physics.json"),
    ))


def _acoustic_space(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"acoustic_space_{ep}.json"),
        os.path.join("生产数据", f"room_tone_{ep}.json"),
        os.path.join("设定库", "ambient_map.json"),
        os.path.join("合成", ep, "room_tone.json"),
    ))


def _acoustic_rows(data: Any) -> List[dict]:
    if isinstance(data, Mapping):
        raw = data.get("clips") or data.get("locations") or data.get("rooms") or data.get("rows") or data.get("items") or []
        if isinstance(raw, Mapping):
            rows = []
            for key, value in raw.items():
                if isinstance(value, Mapping):
                    rows.append({"location": key, **value})
                else:
                    rows.append({"location": key, "value": value})
            raw = rows
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def check_acoustic_space(root: str, ep: str) -> dict:
    """Room tone / ambience / reverb continuity for native AV and composed audio."""
    final_media = bool(_final_cuts(root, ep))
    nav, nav_rel = _native_av_physics(root, ep)
    data, rel = _acoustic_space(root, ep)
    needed = _native_av_project(root) or nav is not None or final_media or data is not None
    res = {"available": needed, "findings": [], "notes": []}
    if not needed:
        res["notes"].append("非原生音画且未检测到成片，声音空间暂不强制。")
        return res
    if data is None:
        res["findings"].append(_row(
            "warn",
            "缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。",
            stage="compose",
            artifacts=(f"生产数据/acoustic_space_{ep}.json", f"生产数据/room_tone_{ep}.json", "设定库/ambient_map.json", nav_rel),
            evidence_family="audio_sync",
        ))
        return res
    rows = _acoustic_rows(data)
    if not rows and isinstance(data, Mapping):
        rows = [data]
    for idx, row in enumerate(rows, 1):
        label = str(row.get("clip") or row.get("clip_id") or row.get("location") or f"row_{idx}")
        missing = []
        if not _has_any_field(row, "location", "scene", "loc"):
            missing.append("location")
        if not _has_any_field(row, "room_tone", "ambient_bed", "ambience", "noise_floor"):
            missing.append("room_tone/ambient_bed")
        if not _has_any_field(row, "reverb_profile", "room_size", "decay", "space_type"):
            missing.append("reverb_profile")
        if not _has_any_field(row, "distance_perspective", "occlusion_policy", "spatial_perspective", "perspective_policy"):
            missing.append("distance_perspective/occlusion_policy")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"声音空间条目 {label} 缺字段：{', '.join(missing)}。",
                stage="compose",
                artifacts=(rel,),
                evidence_family="audio_sync",
            ))
        verdict = str(row.get("verdict") or row.get("status") or "").lower()
        if verdict in {"block", "fail", "failed", "red"}:
            res["findings"].append(_row(
                "block",
                f"声音空间检查未通过：{label} verdict={verdict}。",
                stage="compose",
                artifacts=(rel,),
                evidence_family="audio_sync",
            ))
    if nav is not None and isinstance(nav, Mapping) and not any("native" in str(row).lower() or row.get("source") for row in rows):
        res["findings"].append(_row(
            "warn",
            "原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。",
            stage="compose",
            artifacts=(rel, nav_rel),
            evidence_family="audio_sync",
        ))
    return res


def _final_timeline_probe(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"final_timeline_probe_{ep}.json"),
        os.path.join("合成", ep, "final_timeline_probe.json"),
        os.path.join("合成", ep, f"final_timeline_probe_{ep}.json"),
    ))


def _probe_rows(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("findings") or data.get("segments") or data.get("cuts") or data.get("scenarios") or data.get("rows") or data.get("items") or []
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _num(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def check_final_timeline_probe(root: str, ep: str) -> dict:
    """直接量成片时间线，补足“报告存在”但没量亮度/音量/静音缝的松动点。"""
    cuts = _final_cuts(root, ep)
    res = {"available": bool(cuts), "findings": [], "notes": []}
    if not cuts:
        res["notes"].append("未检测到成片，final timeline probe 等待 compose 阶段。")
        return res
    data, rel = _final_timeline_probe(root, ep)
    if data is None:
        res["findings"].append(_row(
            "warn",
            "成片已存在但缺 final_timeline_probe；无法直接量片确认剪点亮度/色温跳、静音缝、响度突变。",
            stage="compose",
            artifacts=(f"合成/{ep}/final_timeline_probe.json", f"合成/{ep}"),
        ))
        return res
    rows = _probe_rows(data)
    if not rows:
        res["findings"].append(_row(
            "warn",
            "final_timeline_probe 缺 segments/cuts/findings 明细；只有总览无法定位具体剪点。",
            stage="compose",
            artifacts=(rel,),
        ))
        return res
    for row in rows:
        verdict = str(row.get("verdict") or row.get("severity") or "").lower()
        label = str(row.get("cut") or row.get("segment") or row.get("timecode") or row.get("clip") or "")
        if verdict in {"block", "fail", "red"}:
            res["findings"].append(_row("block", str(row.get("message") or "成片时间线探针发现阻断项。"), shot=label, stage="compose", artifacts=(rel,)))
            continue
        if verdict in {"warn", "yellow"}:
            res["findings"].append(_row("warn", str(row.get("message") or "成片时间线探针发现建议项。"), shot=label, stage="compose", artifacts=(rel,)))
        luma = _num(row.get("luma_delta") or row.get("brightness_delta"))
        color = _num(row.get("color_delta") or row.get("hue_delta") or row.get("temperature_delta"))
        lufs = _num(row.get("lufs_delta") or row.get("loudness_delta"))
        rms = _num(row.get("rms_delta_db") or row.get("volume_delta_db"))
        silence = _num(row.get("silence_gap_ms") or row.get("audio_gap_ms"))
        if luma is not None and luma > 0.18:
            res["findings"].append(_row("warn", f"剪点亮度跳变 luma_delta={luma:.3f}，需要色彩/曝光匹配。", shot=label, stage="compose", artifacts=(rel,)))
        if color is not None and color > 0.20:
            res["findings"].append(_row("warn", f"剪点色彩跳变 color_delta={color:.3f}，需要混剪色彩统一。", shot=label, stage="compose", artifacts=(rel,)))
        if lufs is not None and abs(lufs) > 3.0:
            res["findings"].append(_row("warn", f"剪点响度突变 lufs_delta={lufs:.1f}dB。", shot=label, stage="compose", artifacts=(rel,)))
        if rms is not None and abs(rms) > 6.0:
            res["findings"].append(_row("warn", f"剪点 RMS 音量突变 {rms:.1f}dB。", shot=label, stage="compose", artifacts=(rel,)))
        if silence is not None and silence > 250:
            res["findings"].append(_row("warn", f"剪点存在 {silence:.0f}ms 静音/空缝。", shot=label, stage="compose", artifacts=(rel,)))
    return res


def _video_eval_manifest(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"video_eval_manifest_{ep}.json"),
        os.path.join("出视频", ep, "video_eval_manifest.json"),
    ))


def _manifest_risk_kinds(data: Any) -> set:
    kinds = set()
    if not isinstance(data, Mapping):
        return kinds
    for task in _as_list(data.get("tasks")):
        if not isinstance(task, Mapping):
            continue
        kinds.update(str(k).strip() for k in _as_list(task.get("risk_kinds")) if str(k).strip())
    return kinds


def _target_required_by_risk(key: str, kinds: set) -> bool:
    if key in {"video_vlm", "video_semantic", "subject_video"}:
        return bool(kinds)
    return {
        "dialogue_av": "dialogue",
        "causal_event": "physics",
        "physical_event": "physics",
        "camera": "camera",
        "motion": "action",
    }.get(key) in kinds


def _sidecar_has_rows(data: Any) -> bool:
    if isinstance(data, list):
        return bool(data)
    if not isinstance(data, Mapping):
        return False
    for key in ("findings", "checks", "shots", "segments", "events", "turns", "subjects", "judgements", "rows", "items"):
        if _as_list(data.get(key)):
            return True
    return any(k in data for k in ("summary", "judge_model", "frame_sample_manifest"))


def check_video_evidence_completeness(root: str, ep: str) -> dict:
    """Ensure video_eval_runner manifest has been followed by evidence sidecars."""
    media = _existing_media(root, ep) + [os.path.relpath(p, root) for p in _final_cuts(root, ep)]
    res = {"available": bool(media), "findings": [], "notes": []}
    if not media:
        res["notes"].append("未检测到本集媒体，视频证据完整性等待 image/video/compose 阶段。")
        return res
    data, rel = _video_eval_manifest(root, ep)
    if data is None:
        res["findings"].append(_row(
            "warn",
            "本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。",
            stage="review",
            artifacts=(f"生产数据/video_eval_manifest_{ep}.json", f"出视频/{ep}", f"合成/{ep}"),
        ))
        return res
    targets = data.get("sidecar_targets") if isinstance(data, Mapping) else {}
    if not isinstance(targets, Mapping) or not targets:
        res["findings"].append(_row(
            "warn",
            "video_eval_manifest 缺 sidecar_targets；重模型/人工 runner 无法知道标准报告写回位置。",
            stage="review",
            artifacts=(rel,),
        ))
        return res
    kinds = _manifest_risk_kinds(data)
    missing: List[str] = []
    empty: List[str] = []
    for key, target in sorted(targets.items()):
        if not _target_required_by_risk(str(key), kinds):
            continue
        path = str(target or "")
        if not path:
            missing.append(str(key))
            continue
        full = path if os.path.isabs(path) else os.path.join(root, path)
        payload = _load_json(full)
        if payload is None:
            missing.append(f"{key}:{path}")
        elif not _sidecar_has_rows(payload):
            empty.append(f"{key}:{path}")
    if missing:
        res["findings"].append(_row(
            "warn",
            "video_eval_manifest 已建立，但这些风险 sidecar 尚未写回：" + "；".join(missing[:8]),
            stage="review",
            artifacts=(rel,),
        ))
    if empty:
        res["findings"].append(_row(
            "warn",
            "这些视频证据 sidecar 存在但缺明细/判题结果：" + "；".join(empty[:8]),
            stage="review",
            artifacts=(rel,),
        ))
    total_required = sum(1 for key in targets if _target_required_by_risk(str(key), kinds))
    present = total_required - len(missing)
    res["notes"].append(f"视频证据 sidecar 完整度：{present}/{total_required}（按 manifest risk_kinds 计算）。")
    return res


def _physical_event_graph(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"physical_event_graph_{ep}.json"),
        os.path.join("生产数据", f"causal_event_graph_{ep}.json"),
        os.path.join("出视频", ep, "physical_event_graph.json"),
        os.path.join("脚本", ep, "physical_event_graph.json"),
    ))


def _physical_rows(data: Any) -> List[dict]:
    if isinstance(data, Mapping):
        raw = data.get("events") or data.get("physical_events") or data.get("checks") or data.get("findings") or data.get("items") or []
    else:
        raw = data
    return [x for x in _as_list(raw) if isinstance(x, dict)]


def _physical_laws(row: Mapping[str, Any]) -> List[str]:
    raw = row.get("law") or row.get("physical_law") or row.get("physical_rule") or row.get("rules")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    if raw:
        return [str(raw).strip()]
    return []


def _physical_objects(row: Mapping[str, Any]) -> List[str]:
    raw = row.get("object_ids") or row.get("objects") or row.get("entities") or row.get("affected_objects")
    return _unique(str(x).strip() for x in _as_list(raw) if str(x).strip())


def _physical_frames(row: Mapping[str, Any]) -> List[Any]:
    frames: List[Any] = []
    for key in ("frame_range", "evidence_frame_range", "frames", "evidence_frames", "frame_span"):
        frames.extend(_as_list(row.get(key)))
    for key in ("cause_frame", "effect_frame", "start_frame", "end_frame"):
        if row.get(key):
            frames.append(row.get(key))
    return [f for f in frames if f not in (None, "", [], {})]


def _has_physics_risk(root: str, ep: str) -> bool:
    _sb, clips = _storyboard(root, ep)
    prompts = _prompt_sections(root, ep)
    tokens = (
        "击中", "命中", "刺中", "砍中", "撞", "摔", "掉落", "落地", "破裂", "碎裂", "燃起", "熄灭",
        "爆炸", "流血", "推倒", "抓", "拉", "递", "collision", "fall", "physics", "shatter", "explode",
    )
    for idx, clip in enumerate(clips, 1):
        text = _clip_text(clip, _clip_label(clip, idx), prompts)
        if any(t.lower() in text.lower() for t in tokens):
            return True
    return False


def check_physical_event_graph(root: str, ep: str) -> dict:
    """Attributable physical consistency: law + object + frame + violation type."""
    media = _existing_media(root, ep) + [os.path.relpath(p, root) for p in _final_cuts(root, ep)]
    res = {"available": bool(media) or _has_physics_risk(root, ep), "findings": [], "notes": []}
    data, rel = _physical_event_graph(root, ep)
    if data is None:
        if _has_physics_risk(root, ep) and media:
            res["findings"].append(_row(
                "warn",
                "本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。",
                stage="review",
                artifacts=(f"生产数据/physical_event_graph_{ep}.json", f"脚本/{ep}/storyboard.json", f"出视频/{ep}"),
            ))
        else:
            res["notes"].append("无明显物理风险或尚无媒体，PHY 不强制。")
        return res
    rows = _physical_rows(data)
    if not rows:
        res["findings"].append(_row(
            "warn",
            "physical_event_graph 存在但缺 events/checks 明细；只有总览无法定位物理违例。",
            stage="review",
            artifacts=(rel,),
        ))
        return res
    for idx, row in enumerate(rows, 1):
        eid = str(row.get("event_id") or row.get("id") or f"event_{idx}").strip()
        shot = str(row.get("clip") or row.get("clip_id") or row.get("shot") or "")
        laws = _physical_laws(row)
        objects = _physical_objects(row)
        frames = _physical_frames(row)
        missing = []
        if not eid:
            missing.append("event_id")
        if not laws:
            missing.append("law")
        if not objects:
            missing.append("object_ids")
        if not frames:
            missing.append("frame_range/evidence_frames")
        if not (row.get("expected_state_delta") or row.get("expected_delta") or row.get("expected_after")):
            missing.append("expected_state_delta")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"物理事件 {eid} 缺可归因字段：{', '.join(missing)}。",
                shot=shot,
                stage="review",
                artifacts=(rel,),
                event_id=eid,
            ))
        unknown = [law for law in laws if law not in PHYSICAL_LAWS]
        if unknown:
            res["findings"].append(_row(
                "warn",
                f"物理事件 {eid} 使用未登记 law：{', '.join(unknown)}；请归一到物理法则表或补扩展说明。",
                shot=shot,
                stage="script_stage2",
                artifacts=(rel,),
                event_id=eid,
            ))
        verdict = str(row.get("verdict") or row.get("severity") or row.get("status") or "").lower()
        pass_value = row.get("rule_pass") if "rule_pass" in row else row.get("physics_pass")
        failed = verdict in {"block", "fail", "failed", "red"} or str(pass_value).lower() in {"false", "0", "no", "fail", "failed"}
        if failed:
            vtype = str(row.get("violation_type") or row.get("violation") or "").strip()
            if not vtype:
                res["findings"].append(_row(
                    "warn",
                    f"物理事件 {eid} 判失败但缺 violation_type；修复方无法区分穿模/重力/质量守恒/动量问题。",
                    shot=shot,
                    stage="review",
                    artifacts=(rel,),
                    event_id=eid,
                ))
            res["findings"].append(_row(
                "block",
                f"物理事件 {eid} 违例：law={','.join(laws) or '(unknown)'} objects={','.join(objects) or '(unknown)'} frames={frames[:3]} violation={vtype or '(unspecified)'}。",
                shot=shot,
                stage="video",
                artifacts=(rel,),
                event_id=eid,
            ))
    return res


def _world_consistency_score(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"world_consistency_score_{ep}.json"),
        os.path.join("生产数据", f"world_consistency_{ep}.json"),
        os.path.join("生产数据", f"wcs_{ep}.json"),
    ))


def _has_world_sidecars(root: str, ep: str) -> bool:
    rels = (
        os.path.join("生产数据", f"scene_world_ledger_{ep}.json"),
        os.path.join("生产数据", f"object_presence_{ep}.json"),
        os.path.join("生产数据", f"physical_event_graph_{ep}.json"),
        os.path.join("生产数据", f"causal_event_graph_{ep}.json"),
        os.path.join("生产数据", f"temporal_consistency_{ep}.json"),
        os.path.join("生产数据", f"motion_quality_{ep}.json"),
    )
    return any(os.path.exists(os.path.join(root, rel)) for rel in rels)


def _score_value(data: Any) -> Optional[float]:
    if not isinstance(data, Mapping):
        return None
    for key in ("world_consistency_score", "wcs", "score", "overall", "overall_score"):
        num = _num(data.get(key))
        if num is not None:
            return num
    summary = data.get("summary") if isinstance(data.get("summary"), Mapping) else {}
    for key in ("world_consistency_score", "wcs", "score", "overall"):
        num = _num(summary.get(key))
        if num is not None:
            return num
    return None


def check_world_consistency_score(root: str, ep: str) -> dict:
    """WCS-style episode rollup: object permanence + relations + causal + flicker."""
    media = _existing_media(root, ep) + [os.path.relpath(p, root) for p in _final_cuts(root, ep)]
    res = {"available": bool(media) or _has_world_sidecars(root, ep), "findings": [], "notes": []}
    data, rel = _world_consistency_score(root, ep)
    if data is None:
        if media or _has_world_sidecars(root, ep):
            res["findings"].append(_row(
                "warn",
                "已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；"
                "对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。",
                stage="review",
                artifacts=(f"生产数据/world_consistency_score_{ep}.json",),
                evidence_family="motion_physics",
            ))
        else:
            res["notes"].append("尚无媒体/世界 sidecar，WCS 暂不强制。")
        return res
    score = _score_value(data)
    if score is None:
        res["findings"].append(_row(
            "warn",
            "world_consistency_score 缺 overall/world_consistency_score 数值。",
            stage="review",
            artifacts=(rel,),
            evidence_family="motion_physics",
        ))
    else:
        sev = "block" if score < 0.72 else "warn" if score < 0.82 else ""
        if sev:
            res["findings"].append(_row(
                sev,
                f"世界一致性总分偏低：{score:.3f}（block<0.72, warn<0.82）；优先看 object permanence / relation stability / causal compliance / flicker 分项。",
                stage="video" if sev == "block" else "review",
                artifacts=(rel,),
                evidence_family="motion_physics",
            ))
    components = data.get("components") if isinstance(data, Mapping) and isinstance(data.get("components"), Mapping) else data if isinstance(data, Mapping) else {}
    missing = [key for key in WORLD_SCORE_COMPONENTS if key not in components]
    if missing:
        res["findings"].append(_row(
            "warn",
            f"world_consistency_score 缺分项：{', '.join(missing)}；总分无法解释到对象/关系/因果/flicker 根因。",
            stage="review",
            artifacts=(rel,),
            evidence_family="motion_physics",
        ))
    return res


def _load_events(root: str) -> List[dict]:
    path = os.path.join(production_dir(root), "production_events.jsonl")
    out: List[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    out.append(item)
    except FileNotFoundError:
        pass
    return out


def _event_asset(event: Mapping[str, Any]) -> str:
    gen = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    return str(gen.get("asset") or event.get("asset") or "").strip()


def _canonical_asset(root: str, asset: str) -> str:
    raw = str(asset or "").strip()
    if not raw:
        return ""
    path = os.path.normpath(raw)
    root_path = os.path.normpath(root)
    try:
        if os.path.isabs(path) and os.path.commonpath([path, root_path]) == root_path:
            return os.path.relpath(path, root_path)
    except ValueError:
        pass
    root_name = os.path.basename(root_path)
    parts = path.split(os.sep)
    if root_name and root_name in parts:
        idx = len(parts) - 1 - list(reversed(parts)).index(root_name)
        tail = parts[idx + 1:]
        if tail:
            return os.path.join(*tail)
    return path


def _event_provider(event: Mapping[str, Any]) -> str:
    gen = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    cost = event.get("cost") if isinstance(event.get("cost"), Mapping) else {}
    return str(cost.get("provider") or gen.get("provider") or event.get("provider") or "").strip()


def _event_meta(event: Mapping[str, Any]) -> Mapping[str, Any]:
    return event.get("meta") if isinstance(event.get("meta"), Mapping) else {}


def _event_value(event: Mapping[str, Any], *keys: str) -> Any:
    gen = event.get("generation") if isinstance(event.get("generation"), Mapping) else {}
    meta = _event_meta(event)
    cost = event.get("cost") if isinstance(event.get("cost"), Mapping) else {}
    for key in keys:
        for source in (event, gen, meta, cost):
            value = source.get(key) if isinstance(source, Mapping) else None
            if value not in (None, ""):
                return value
    return ""


def recipe_fingerprint(event: Mapping[str, Any]) -> str:
    meta = dict(_event_meta(event))
    gen = dict(event.get("generation") if isinstance(event.get("generation"), Mapping) else {})
    keys = (
        "stage", "event", "source",
        "provider", "asset", "status",
        "mode", "task", "shot", "codex_model", "model", "model_version", "model_id", "backend",
        "logical_seed", "requested_seed", "effective_seed", "seed_effective", "seed_strategy", "seed_support",
        "reference_manifest", "reference_bundle", "reference_bundle_sha256", "reference_input_count", "reference_input_paths",
        "prompt_hash", "prompt_sha256", "prompt_source_path", "negative_prompt_sha256",
        "adapter_version", "qc_version", "route_hash", "input_fingerprint",
        "resolution", "aspect_ratio", "duration_s", "fps", "scheduler", "steps", "cfg_scale",
        "submit_id",
    )
    stable: Dict[str, Any] = {}
    for key in keys:
        value = event.get(key)
        if value in (None, ""):
            value = gen.get(key)
        if value in (None, ""):
            value = meta.get(key)
        if value not in (None, ""):
            stable[key] = value
    blob = json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def build_recipe_ledger(root: str, ep: str) -> dict:
    latest_by_asset: Dict[str, Tuple[int, dict]] = {}
    for event in _load_events(root):
        if str(event.get("episode") or "") != ep:
            continue
        if str(event.get("event") or "") not in {"generation", "redraw"}:
            continue
        asset = _canonical_asset(root, _event_asset(event))
        if not asset:
            continue
        meta = _event_meta(event)
        row = {
            "stage": event.get("stage"),
            "event": event.get("event"),
            "asset": asset,
            "provider": _event_provider(event),
            "status": (event.get("generation") or {}).get("status") if isinstance(event.get("generation"), Mapping) else "",
            "recipe_hash": str(meta.get("recipe_hash") or recipe_fingerprint(event)),
            "declared_recipe_hash": bool(meta.get("recipe_hash")),
            "backend": _event_value(event, "backend", "primary_backend", "provider"),
            "backend_version": _event_value(event, "backend_version", "backend_rev", "backend_release", "api_version"),
            "model_version": _event_value(event, "model_version", "model_id", "model", "model_name"),
            "seed": meta.get("logical_seed") or meta.get("requested_seed") or meta.get("effective_seed") or "",
            "seed_effective": _event_value(event, "seed_effective", "effective_seed"),
            "seed_support": _event_value(event, "seed_support", "seed_capability"),
            "seed_strategy": _event_value(event, "seed_strategy", "seed_policy", "seed_degrade"),
            "mode": meta.get("mode") or "",
            "retry_attempt": _event_value(event, "retry_attempt", "attempt", "attempt_no"),
            "redraw_reason": _event_value(event, "redraw_reason", "retry_reason", "failure_reason"),
            "reference_manifest": meta.get("reference_manifest") or meta.get("reference_bundle") or "",
            "reference_bundle_sha256": _event_value(event, "reference_bundle_sha256", "reference_sha256", "reference_digest"),
            "prompt_sha256": _event_value(event, "prompt_sha256", "prompt_hash", "prompt_digest"),
            "route_hash": _event_value(event, "route_hash"),
            "input_fingerprint": _event_value(event, "input_fingerprint", "pre_submit_fingerprint", "recipe_input_hash"),
            "settings_sha256": _event_value(event, "settings_sha256", "settings_hash"),
            "identity_registry_sha256": _event_value(event, "identity_registry_sha256", "identity_registry_hash"),
            "asset_registry_sha256": _event_value(event, "asset_registry_sha256", "asset_registry_hash"),
            "artifact_sha256": _event_value(event, "artifact_sha256", "output_sha256", "media_sha256"),
            "adapter_version": _event_value(event, "adapter_version", "adapter_commit", "adapter_rev"),
            "qc_version": _event_value(event, "qc_version", "qc_schema_version", "review_schema_version"),
        }
        latest_by_asset[asset] = (len(latest_by_asset), row)
    rows = [item[1] for _, item in sorted(latest_by_asset.items(), key=lambda pair: pair[1][0])]
    return {
        "kind": "n2d_generation_recipe_ledger",
        "version": 1,
        "root": root,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "rows": rows,
        "summary": {"count": len(rows), "declared_hash": sum(1 for r in rows if r.get("declared_recipe_hash"))},
    }


def write_recipe_ledger(root: str, ep: str) -> str:
    return _write_json(os.path.join(production_dir(root), f"generation_recipe_{ep}.json"), build_recipe_ledger(root, ep))


def _existing_media(root: str, ep: str) -> List[str]:
    import glob
    out = []
    for pattern in (
        os.path.join(root, "出图", ep, "图片", "*.png"),
        os.path.join(root, "出视频", ep, "视频", "*.mp4"),
    ):
        out.extend(os.path.relpath(p, root) for p in glob.glob(pattern))
    return sorted(out)


def check_generation_recipe(root: str, ep: str) -> dict:
    res = {"available": True, "findings": [], "notes": []}
    ledger = build_recipe_ledger(root, ep)
    rows = ledger.get("rows", [])
    if not rows and _existing_media(root, ep):
        res["findings"].append(_row(
            "warn",
            "本集已有媒体文件但 production_events 无 generation/redraw 记录；无法复算后端、参考图、seed 与配方 hash。",
            stage="review",
            artifacts=("生产数据/production_events.jsonl", f"出图/{ep}", f"出视频/{ep}"),
        ))
        return res
    for row in rows:
        missing = []
        if not row.get("provider"):
            missing.append("provider")
        if not row.get("mode"):
            missing.append("mode")
        if not row.get("seed"):
            missing.append("seed/seed_degrade")
        if not (row.get("backend_version") or row.get("model_version")):
            missing.append("backend_version/model_version")
        if not row.get("declared_recipe_hash"):
            missing.append("declared_recipe_hash")
        if row.get("event") == "redraw" and not (row.get("redraw_reason") or row.get("retry_attempt")):
            missing.append("redraw_reason/retry_attempt")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"{row.get('asset')} 生成事件缺配方字段：{', '.join(missing)}；已可推导 hash={row.get('recipe_hash')}，但复跑审计证据不完整。",
                stage="image" if row.get("stage") == "image" else "video",
                artifacts=("生产数据/production_events.jsonl",),
            ))
    return res


def check_recipe_schema(root: str, ep: str) -> dict:
    res = {"available": True, "findings": [], "notes": []}
    ledger = build_recipe_ledger(root, ep)
    rows = ledger.get("rows", [])
    if not rows and _existing_media(root, ep):
        res["findings"].append(_row(
            "warn",
            "本集已有媒体但缺 generation recipe rows；强配方 schema 无法校验 prompt/reference/route 指纹。",
            stage="review",
            artifacts=("生产数据/production_events.jsonl", f"出图/{ep}", f"出视频/{ep}"),
        ))
        return res
    for row in rows:
        missing = []
        if not row.get("prompt_sha256"):
            missing.append("prompt_sha256")
        if not (row.get("reference_bundle_sha256") or row.get("reference_manifest")):
            missing.append("reference_bundle_sha256/reference_manifest")
        if str(row.get("stage") or "") == "video" and not row.get("route_hash"):
            missing.append("route_hash")
        if not row.get("input_fingerprint"):
            missing.append("input_fingerprint")
        if not row.get("settings_sha256"):
            missing.append("settings_sha256")
        if str(row.get("stage") or "") in {"image", "video"} and not row.get("identity_registry_sha256"):
            missing.append("identity_registry_sha256")
        if str(row.get("stage") or "") in {"image", "video"} and not row.get("asset_registry_sha256"):
            missing.append("asset_registry_sha256")
        if not row.get("artifact_sha256"):
            missing.append("artifact_sha256")
        if not row.get("adapter_version"):
            missing.append("adapter_version")
        if not row.get("qc_version"):
            missing.append("qc_version")
        if not (row.get("backend_version") or row.get("model_version")):
            missing.append("backend_version/model_version")
        if not (row.get("seed") or row.get("seed_effective") or row.get("seed_support") in {"unsupported", "none", "not_supported"}):
            missing.append("seed_effective_or_unsupported")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"{row.get('asset')} 强配方 schema 缺字段：{', '.join(missing)}；recipe_hash 已有但还不能完整复现/归因。",
                stage="image" if row.get("stage") == "image" else "video",
                artifacts=("生产数据/production_events.jsonl", f"生产数据/generation_recipe_{ep}.json"),
            ))
    return res


def check_series_packaging(root: str, ep: str) -> dict:
    paths = [
        os.path.join(root, "设定库", "series_packaging.json"),
        os.path.join(root, "设定库", "包装规范.json"),
        os.path.join(root, "合成", "交付", "series_packaging.json"),
    ]
    data = next((x for x in (_load_json(p) for p in paths) if isinstance(x, dict)), None)
    res = {"available": data is not None, "findings": [], "notes": []}
    if data is None:
        res["findings"].append(_row(
            "warn",
            "缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。",
            stage="compose",
            artifacts=("设定库/series_packaging.json", "合成/交付"),
        ))
        return res
    required = {
        "title_treatment": ("title_treatment", "标题字", "title"),
        "subtitle_style": ("subtitle_style", "subtitle_font", "字幕字体", "font"),
        "cover": ("cover", "封面", "thumbnail"),
        "episode_card": ("episode_card", "分集封面", "episode_thumbnail", "title_card"),
        "platform_specs": ("platform_specs", "平台规格", "delivery_matrix", "aspect_ratio_matrix"),
        "brand_visual": ("brand_visual", "品牌视觉", "series_brand", "logo_lockup"),
        "intro": ("intro", "片头"),
        "outro": ("outro", "片尾"),
        "transition_sfx": ("transition_sfx", "转场音效", "sfx"),
    }
    blob = _json_text(data)
    for key, aliases in required.items():
        if not any(alias in data or alias in blob for alias in aliases):
            res["findings"].append(_row(
                "warn",
                f"系列包装规范缺 {key}；建议在设定库/series_packaging.json 固化。",
                stage="compose",
                artifacts=("设定库/series_packaging.json",),
            ))
    return res


def _voice_lines(root: str, ep: str) -> List[Tuple[str, str]]:
    text = _read(os.path.join(root, "脚本", ep, "voiceover.txt"))
    rows = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        m = re.match(r"^([^:：]{1,24})[:：]\s*(.+)$", raw)
        if m:
            rows.append((m.group(1).strip(), m.group(2).strip()))
    return rows


# 语域统计漂移（G-S2·2026-06-24 流程自审落地）：脸/服装/发型/称谓锁住后，台词「语域」漂移
# 是 AI 改写最隐蔽的塌人设，且全行业无机检（红果「台词须符身份/杜绝水台词」仍是 craft 级，无 checker）。
# A1(称谓) 只查称呼/口头禅在场，D1 此前只查 forbidden/must_use token 在场——都不看「文白/正式度/句长」这条
# 真正的语域轴。这里补三类纯文本统计型 first-pass（启发式·全部 warn·交人判，绝不臆造 block）：
#   ① 文白横跳——同角色同集既用文言/书面标记又用市井口语标记（非自称词，补 REGISTER_WORDS 盲区）；
#   ② 正式度冲突——spec 声明 formality=formal 却出现口语标记（或声明 colloquial 却满口文言）；
#   ③ 句长失稳——超 spec.sentence_len_max 软上限（惜字如金的角色突然长篇大论=口吻漂）。
# 文言/书面标记取多字·辨识度高的词（避开「之/也/者」单字高频词的误报）。
FORMAL_MARKERS = (
    "岂能", "岂敢", "焉能", "怎敢", "莫非", "何故", "何须", "休得", "且慢", "在下", "鄙人",
    "阁下", "失礼", "告辞", "承蒙", "甚是", "倒也", "无妨", "此乃", "实乃", "之事", "不才",
    "敢问", "见谅", "恕我", "未尝", "断不可", "切莫",
)
COLLOQUIAL_MARKERS = (
    "啥", "咋", "呗", "嘛", "咯", "整啥", "搞啥", "玩意", "牛逼", "扯淡", "没辙", "咋整",
    "干啥", "这事儿", "得了吧", "拉倒", "够呛", "瞎", "唠", "麻溜", "费劲", "墨迹",
)


def register_marker_hits(lines: Sequence[str]) -> Tuple[List[str], List[str]]:
    """同角色台词命中的文言/书面标记、市井口语标记（去重排序）。纯函数·可测。"""
    blob = "".join(lines)
    formal = sorted({m for m in FORMAL_MARKERS if m in blob})
    colloq = sorted({m for m in COLLOQUIAL_MARKERS if m in blob})
    return formal, colloq


def register_mix_flagged(formal_hits: Sequence[str], colloquial_hits: Sequence[str]) -> bool:
    """文白横跳：同时出现文言/书面与市井口语标记。纯函数·可测。"""
    return bool(formal_hits) and bool(colloquial_hits)


def overlong_lines(lines: Sequence[str], cap: int) -> List[str]:
    """超句长软上限的台词（cap≤0 视为未设上限，返回空）。纯函数·可测。"""
    if not cap or cap <= 0:
        return []
    return [ln for ln in lines if len(ln) > cap]


def _declared_formality(spec: Mapping[str, Any]) -> str:
    """归一 spec 的正式度声明 → 'formal' | 'colloquial' | ''。纯函数·可测。"""
    raw = str(spec.get("formality") or spec.get("正式度") or spec.get("vocab_tier") or spec.get("语域") or "").strip().lower()
    if raw in ("formal", "文言", "书面", "尊", "雅", "正式"):
        return "formal"
    if raw in ("colloquial", "口语", "市井", "俗", "casual", "vulgar", "粗"):
        return "colloquial"
    return ""


def check_dialogue_register(root: str, ep: str) -> dict:
    rows = _voice_lines(root, ep)
    paths = [
        os.path.join(root, "设定库", "dialogue_register.json"),
        os.path.join(root, "设定库", "voice_register.json"),
        os.path.join(root, "设定库", "语域表.json"),
    ]
    data = next((x for x in (_load_json(p) for p in paths) if isinstance(x, dict)), None)
    res = {"available": bool(rows), "findings": [], "notes": []}
    if not rows:
        res["notes"].append("缺 voiceover 台词行，语域一致性跳过。")
        return res
    by_role: Dict[str, List[str]] = defaultdict(list)
    for role, text in rows:
        by_role[role].append(text)
    arts = (f"脚本/{ep}/voiceover.txt", "设定库/dialogue_register.json")

    # ① 文白横跳——dictionary-less，对所有角色恒跑（脸锁住后语域漂移无人看守的盲区）。
    for role, lines in by_role.items():
        formal, colloq = register_marker_hits(lines)
        if register_mix_flagged(formal, colloq):
            res["findings"].append(_row(
                "warn",
                f"角色「{role}」疑似文白/语域横跳：同集既用文言/书面词 {formal[:3]} 又用市井口语 {colloq[:3]}，"
                "若非有意（装腔/穿越者吐槽）请核对是否塌人设。",
                stage="script_stage1", artifacts=arts,
            ))

    if data is None:
        for role, lines in by_role.items():
            used = sorted({w for w in REGISTER_WORDS if any(w in line for line in lines)})
            if len(used) >= 2:
                res["findings"].append(_row(
                    "warn",
                    f"角色「{role}」自称/语气词混用 {', '.join(used)}，但缺语域表判定是否合理。",
                    stage="script_stage1", artifacts=arts,
                ))
        if not res["findings"]:
            res["findings"].append(_row(
                "warn",
                "缺 dialogue_register/语域表；目前只能查称谓 + 文白横跳启发式，"
                "无法约束角色正式度、句长上限和禁用词。建议补 formality/sentence_len_max/forbidden/口癖。",
                stage="script_stage1", artifacts=("设定库/dialogue_register.json",),
            ))
        return res

    for role, lines in by_role.items():
        spec = data.get(role) or data.get(str(role).strip()) or {}
        if not isinstance(spec, dict):
            continue
        forbidden = spec.get("forbidden") or spec.get("禁用") or []
        must = spec.get("must_use") or spec.get("must") or spec.get("口癖") or []
        for token in forbidden if isinstance(forbidden, list) else [forbidden]:
            if token and any(str(token) in line for line in lines):
                res["findings"].append(_row(
                    "warn",
                    f"角色「{role}」台词出现语域禁用词「{token}」。",
                    stage="script_stage1", artifacts=arts,
                ))
        if must:
            tokens = must if isinstance(must, list) else [must]
            if not any(str(t) in line for t in tokens for line in lines):
                res["findings"].append(_row(
                    "warn",
                    f"角色「{role}」本集没有回读语域锚点 {tokens[:3]}；若本集戏份较多，可能口吻漂移。",
                    stage="script_stage1", artifacts=arts,
                ))
        # ② 正式度冲突——声明正式度与实际市井/文言标记打架。
        declared = _declared_formality(spec)
        formal, colloq = register_marker_hits(lines)
        if declared == "formal" and colloq:
            res["findings"].append(_row(
                "warn",
                f"角色「{role}」声明 formality=formal（文言/书面），台词却出现市井口语 {colloq[:3]}——正式度漂移。",
                stage="script_stage1", artifacts=arts,
            ))
        elif declared == "colloquial" and formal:
            res["findings"].append(_row(
                "warn",
                f"角色「{role}」声明 formality=colloquial（口语/市井），台词却满口文言/书面 {formal[:3]}——正式度漂移。",
                stage="script_stage1", artifacts=arts,
            ))
        # ③ 句长失稳——超声明的软上限（惜字如金的角色突然长篇大论）。
        try:
            cap = int(spec.get("sentence_len_max") or spec.get("句长上限") or 0)
        except (TypeError, ValueError):
            cap = 0
        over = overlong_lines(lines, cap)
        if over:
            res["findings"].append(_row(
                "warn",
                f"角色「{role}」有 {len(over)} 句超句长上限 {cap} 字（如「{over[0][:18]}…」）；"
                "话风从短促变长篇可能口吻漂移，核对是否符合人设。",
                stage="script_stage1", artifacts=arts,
            ))
    return res


def _floorplan_data(root: str) -> Optional[dict]:
    for rel in (
        os.path.join("设定库", "scene_floorplan.json"),
        os.path.join("设定库", "场景平面图.json"),
        os.path.join("出图", "共享", "scene_floorplan.json"),
    ):
        data = _load_json(os.path.join(root, rel))
        if isinstance(data, dict):
            return data
    return None


def _spatial_memory_data(root: str) -> Optional[dict]:
    for rel in (
        os.path.join("设定库", "location_spatial_memory.json"),
        os.path.join("设定库", "scene_spatial_memory.json"),
        os.path.join("出图", "共享", "location_spatial_memory.json"),
        os.path.join("设定库", "scene_floorplan.json"),
    ):
        data = _load_json(os.path.join(root, rel))
        if isinstance(data, dict):
            return data
    return None


def check_floorplan(root: str, ep: str) -> dict:
    sb, clips = _storyboard(root, ep)
    res = {"available": sb is not None, "findings": [], "notes": []}
    if not clips:
        res["notes"].append("缺 storyboard clips[]，场景平面图检查跳过。")
        return res
    prompts = _prompt_sections(root, ep)
    counts: Dict[str, int] = defaultdict(int)
    clip_texts: List[Tuple[str, str, str]] = []
    for idx, clip in enumerate(clips, 1):
        label = _clip_label(clip, idx)
        text = _clip_text(clip, label, prompts)
        loc = _loc_of(clip, text)
        if loc:
            counts[loc] += 1
            clip_texts.append((label, loc, text))
    fp = _floorplan_data(root)
    if fp is None:
        for loc, n in counts.items():
            if n >= 3:
                res["findings"].append(_row(
                    "warn",
                    f"场景 {loc} 本集出现 {n} 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。",
                    stage="script_stage2",
                    artifacts=(f"脚本/{ep}/storyboard.json", "设定库/scene_floorplan.json"),
                ))
        return res
    spatial = _spatial_memory_data(root)
    scenes = fp.get("scenes") if isinstance(fp.get("scenes"), dict) else fp
    spatial_scenes = spatial.get("scenes") if isinstance(spatial, dict) and isinstance(spatial.get("scenes"), dict) else spatial
    for label, loc, text in clip_texts:
        spec = scenes.get(loc) if isinstance(scenes, dict) else None
        if not isinstance(spec, dict):
            continue
        zones = spec.get("zones") or spec.get("区域") or []
        if isinstance(zones, dict):
            zones = list(zones.keys())
        if zones:
            zone_tokens = [str(z) for z in zones if z]
            if not any(z in text for z in zone_tokens) and not _is_exempt_view(text):
                res["findings"].append(_row(
                    "warn",
                    f"{loc} 有平面图区域 {zone_tokens[:5]}，但 {label} 未声明角色/机位所在区域；空间连续性难复核。",
                    shot=label,
                    stage="script_stage2",
                    artifacts=(f"脚本/{ep}/storyboard.json", "设定库/scene_floorplan.json"),
                ))
    for loc, n in counts.items():
        if n < 2:
            continue
        spec = spatial_scenes.get(loc) if isinstance(spatial_scenes, dict) else None
        if not isinstance(spec, dict):
            res["findings"].append(_row(
                "warn",
                f"场景 {loc} 本集复用 {n} 镜但缺 location_spatial_memory 条目；多视角/反打时门窗、固定物、光源和合法机位只靠文字记忆。",
                stage="script_stage2",
                artifacts=("设定库/location_spatial_memory.json", "设定库/scene_floorplan.json"),
            ))
            continue
        required = {
            "fixed_objects": ("fixed_objects", "default_objects", "常驻物", "固定物", "anchors"),
            "entrances": ("entrances", "doors", "windows", "门", "窗", "出入口"),
            "light_sources": ("light_sources", "光源", "主光", "practical_lights"),
            "camera_arcs": ("camera_arcs", "legal_camera_arcs", "机位弧线", "axis"),
        }
        blob = _json_text(spec)
        missing = [name for name, aliases in required.items() if not any(alias in spec or alias in blob for alias in aliases)]
        if missing:
            res["findings"].append(_row(
                "warn",
                f"场景 {loc} 的空间记忆缺字段：{', '.join(missing)}；同一地点跨镜容易出现门窗/光源/机位漂移。",
                stage="script_stage2",
                artifacts=("设定库/location_spatial_memory.json", "设定库/scene_floorplan.json"),
            ))
    return res


def _finding_files(root: str, ep: str) -> List[str]:
    import glob
    paths = [
        os.path.join(root, "生产数据", f"consistency_findings_{ep}.json"),
        os.path.join(root, "生产数据", f"review_ui_findings_{ep}.json"),
    ]
    paths.extend(glob.glob(os.path.join(root, "生产数据", f"gate_findings_*_{ep}.json")))
    return [p for p in paths if os.path.isfile(p)]


def _active_finding_rows(data: Any) -> List[dict]:
    if isinstance(data, dict):
        raw = data.get("findings") or data.get("details") or data.get("items") or []
    else:
        raw = data
    rows = []
    for item in _as_list(raw):
        if isinstance(item, dict) and str(item.get("verdict") or item.get("severity") or "").lower() in {"block", "warn", "red", "yellow"}:
            rows.append(item)
    return rows


def _jsonl_rows(path: str) -> List[dict]:
    rows: List[dict] = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(item, dict):
                    rows.append(item)
    except FileNotFoundError:
        pass
    return rows


def _calibration_path(root: str) -> str:
    for rel in (
        os.path.join("生产数据", "consistency_calibration.jsonl"),
        os.path.join("设定库", "consistency_calibration.jsonl"),
    ):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return os.path.join(root, "生产数据", "consistency_calibration.jsonl")


def _threshold_path(root: str) -> str:
    for rel in (
        os.path.join("生产数据", "consistency_threshold_registry.json"),
        os.path.join("设定库", "consistency_threshold_registry.json"),
        os.path.join("生产数据", "consistency_threshold_recommendations.json"),
        os.path.join("设定库", "consistency_threshold_recommendations.json"),
        os.path.join("生产数据", "consistency_thresholds.json"),
        os.path.join("设定库", "consistency_thresholds.json"),
    ):
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            return path
    return ""


def _row_has_threshold_advice(row: Mapping[str, Any]) -> bool:
    return any(row.get(key) not in (None, "", [], {}) for key in (
        "threshold_recommendation",
        "threshold_delta",
        "new_threshold",
        "suggested_threshold",
        "detector_patch",
        "rule_patch",
    ))


def _calibration_threshold_needs(rows: Sequence[Mapping[str, Any]]) -> List[Tuple[str, int, int]]:
    by_dim: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        label = str(row.get("label") or row.get("review_label") or "").strip()
        dim = str(row.get("dimension") or row.get("dim") or "(unknown)").strip()
        if label:
            by_dim[dim][label] += 1
    needs: List[Tuple[str, int, int]] = []
    for dim, counts in by_dim.items():
        false_positive = counts.get("false_positive", 0)
        missed = counts.get("missed_by_machine", 0)
        if false_positive >= 2 or missed >= 1:
            needs.append((dim, false_positive, missed))
    return needs


def check_review_calibration(root: str, ep: str) -> dict:
    """把一次性人审签收沉淀为全局校准集，供后续误报/漏报回归使用。"""
    res = {"available": True, "findings": [], "notes": []}
    # P4：阈值注册表此前只判存在性、从不读内容（掣肘四）。后端 floor 无标定背书地放松（低于
    # 全局 floor）会静默削弱该后端闸门——读 registry 的 coherence_issues，block 级不连贯→warn finding。
    reg_path = os.path.join(root, "生产数据", "consistency_threshold_registry.json")
    reg_data = _load_json(reg_path) or {}
    for issue in reg_data.get("coherence_issues", []):
        if isinstance(issue, dict) and issue.get("severity") == "block":
            res["findings"].append(_row(
                "warn",
                f"阈值注册表不连贯：{issue.get('message')}",
                stage="review",
                artifacts=(os.path.relpath(reg_path, root),),
            ))
    finding_rows: List[dict] = []
    for path in _finding_files(root, ep):
        finding_rows.extend(_active_finding_rows(_load_json(path)))
    signoff_data, signoff_rel = _load_first_json(root, (
        os.path.join("生产数据", f"human_review_signoff_{ep}.json"),
        os.path.join("生产数据", f"review_signoff_{ep}.json"),
        os.path.join("质检", f"review_signoff_{ep}.json"),
    ))
    overrides = [
        e for e in _load_events(root)
        if str(e.get("episode") or "") == ep
        and (
            str(e.get("event") or "") in {"human_override", "review_signoff", "consistency_label"}
            or isinstance(e.get("review"), Mapping)
        )
    ]
    if not finding_rows and signoff_data is None and not overrides:
        res["notes"].append("未检测到人审签收/覆盖记录，CAL 跳过。")
        return res
    cal_path = _calibration_path(root)
    rows = _jsonl_rows(cal_path)
    if not rows:
        res["findings"].append(_row(
            "warn",
            "检测到人审签收/覆盖记录，但缺 consistency_calibration.jsonl；误报/漏报没有进入全局校准集。",
            stage="review",
            artifacts=(os.path.relpath(cal_path, root), signoff_rel or "生产数据/consistency_findings_*.json"),
        ))
        return res
    covered_hashes = {str(r.get("finding_hash") or r.get("source_hash") or "") for r in rows if r.get("finding_hash") or r.get("source_hash")}
    for row in rows:
        label = str(row.get("label") or row.get("review_label") or "").strip()
        missing = []
        if label not in REVIEW_LABELS:
            missing.append("label")
        if label in {"false_positive", "accepted_intentional", "missed_by_machine"} and not row.get("reviewer"):
            missing.append("reviewer")
        if label in {"false_positive", "accepted_intentional", "missed_by_machine"} and not row.get("reason"):
            missing.append("reason")
        if not (row.get("dimension") or row.get("dim")):
            missing.append("dimension")
        if missing:
            res["findings"].append(_row(
                "warn",
                f"校准集条目缺字段：{', '.join(missing)}。",
                stage="review",
                artifacts=(os.path.relpath(cal_path, root),),
            ))
    reviewed = [r for r in finding_rows if r.get("review_label") or r.get("human_verdict") or r.get("accepted_intentional")]
    for row in reviewed:
        h = str(row.get("finding_hash") or _finding_hash(row))
        if h not in covered_hashes:
            res["findings"].append(_row(
                "warn",
                f"已人审标注的 finding 未进入校准集：hash={h}。",
                stage="review",
                artifacts=(os.path.relpath(cal_path, root),),
            ))
    threshold_needs = _calibration_threshold_needs(rows)
    if threshold_needs:
        threshold_path = _threshold_path(root)
        embedded_advice = any(_row_has_threshold_advice(row) for row in rows)
        summary = "；".join(
            f"{dim}: false_positive={fp}, missed_by_machine={missed}"
            for dim, fp, missed in threshold_needs[:6]
        )
        if not threshold_path and not embedded_advice:
            res["findings"].append(_row(
                "warn",
                "校准集已有稳定误报/漏报样本，但缺 consistency_thresholds 或 threshold_recommendations；"
                f"阈值/规则没有形成可复跑学习闭环（{summary}）。可运行 calibrate_thresholds.py --write 生成建议。",
                stage="review",
                artifacts=(os.path.relpath(cal_path, root), "生产数据/consistency_threshold_recommendations.json"),
            ))
        else:
            rel = os.path.relpath(threshold_path, root) if threshold_path else os.path.relpath(cal_path, root)
            res["notes"].append(f"CAL 阈值学习样本：{summary}；已检测到阈值建议/配置 {rel}。")
    return res


def _episode_count(root: str) -> int:
    import glob
    return len([p for p in glob.glob(os.path.join(root, "脚本", "第*集")) if os.path.isdir(p)])


def _probe_pack(root: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", "consistency_probe_pack.json"),
        os.path.join("设定库", "consistency_probe_pack.json"),
        os.path.join("生产数据", "probe_pack", "consistency_probe_pack.json"),
    ))


def _probe_route_recommendations(root: str, ep: str) -> Tuple[Optional[Any], str]:
    return _load_first_json(root, (
        os.path.join("生产数据", f"video_route_recommendations_{ep}.json"),
        os.path.join("生产数据", "video_route_recommendations.json"),
        os.path.join("设定库", "video_route_recommendations.json"),
    ))


def _probe_scenario_name(row: Mapping[str, Any]) -> str:
    return str(row.get("scenario") or row.get("name") or row.get("id") or "").strip()


def _backend_score_value(row: Mapping[str, Any]) -> Optional[float]:
    for key in ("consistency_score", "score", "avg_score", "mean_score", "pass_rate", "quality_score"):
        num = _num(row.get(key))
        if num is not None:
            return num
    return None


def _backend_name(value: Mapping[str, Any]) -> str:
    for key in ("backend", "provider", "model", "model_id", "primary_backend", "selected_backend", "name"):
        text = str(value.get(key) or "").strip()
        if text:
            return text
    return ""


def _looks_like_backend_score(value: Mapping[str, Any]) -> bool:
    return bool(_backend_name(value)) or any(key in value for key in (
        "score", "consistency_score", "avg_score", "pass_rate", "passed", "verdict", "status",
    ))


def _collect_backend_scores(value: Any, *, scenario: str = "", backend: str = "") -> List[dict]:
    rows: List[dict] = []
    if isinstance(value, list):
        for item in value:
            rows.extend(_collect_backend_scores(item, scenario=scenario, backend=backend))
        return rows
    if not isinstance(value, dict):
        return rows
    current_scenario = str(value.get("scenario") or value.get("name") or value.get("id") or scenario or "").strip()
    current_backend = _backend_name(value) or backend
    if _looks_like_backend_score(value) and current_backend:
        row = dict(value)
        row.setdefault("scenario", current_scenario)
        row.setdefault("backend", current_backend)
        rows.append(row)
    for key, child in value.items():
        if key in {"scenario", "name", "id", "backend", "provider", "model", "model_id"}:
            continue
        if isinstance(child, dict):
            next_scenario = current_scenario
            next_backend = current_backend
            if key not in {"backend_scores", "backend_results", "scores", "results", "route_scores"}:
                if _looks_like_backend_score(child):
                    next_backend = key
                elif not next_scenario:
                    next_scenario = key
            rows.extend(_collect_backend_scores(child, scenario=next_scenario, backend=next_backend))
        elif isinstance(child, list):
            next_scenario = current_scenario if key in {"backend_scores", "backend_results", "scores", "results", "route_scores"} else (current_scenario or key)
            rows.extend(_collect_backend_scores(child, scenario=next_scenario, backend=current_backend))
    return rows


def _probe_backend_scores(data: Any, scenarios: Sequence[Mapping[str, Any]]) -> List[dict]:
    rows: List[dict] = []
    if isinstance(data, dict):
        for key in ("backend_scores", "backend_results", "route_scores", "model_scores", "results"):
            if key in data:
                rows.extend(_collect_backend_scores(data.get(key)))
    for scenario in scenarios:
        name = _probe_scenario_name(scenario)
        for key in ("backend_scores", "backend_results", "route_scores", "model_scores", "results"):
            if key in scenario:
                rows.extend(_collect_backend_scores(scenario.get(key), scenario=name))
    dedup: List[dict] = []
    seen = set()
    for row in rows:
        sig = (
            str(row.get("scenario") or ""),
            str(row.get("backend") or ""),
            str(_backend_score_value(row)),
            str(row.get("verdict") or row.get("status") or ""),
        )
        if sig in seen:
            continue
        seen.add(sig)
        dedup.append(row)
    return dedup


def _route_primary_backends(routes: Mapping[str, Mapping[str, Any]]) -> List[str]:
    names: List[str] = []
    for route in routes.values():
        if not isinstance(route, Mapping):
            continue
        name = _backend_name(route)
        if name:
            names.append(name)
    return _unique(names)


def _backend_match(a: str, b: str) -> bool:
    aa = re.sub(r"\s+", "", str(a or "").lower())
    bb = re.sub(r"\s+", "", str(b or "").lower())
    return bool(aa and bb and (aa in bb or bb in aa))


def check_probe_pack(root: str, ep: str) -> dict:
    """项目级哨兵小样：用固定 probe 保护后端/提示词/模板升级不把一致性打穿。"""
    res = {"available": True, "findings": [], "notes": []}
    data, rel = _probe_pack(root)
    should_have = _episode_count(root) >= 2 or bool(_load_events(root)) or bool(_existing_media(root, ep))
    if data is None:
        if should_have:
            res["findings"].append(_row(
                "warn",
                "项目已有多集或媒体产物，但缺 consistency_probe_pack；后端/模板升级没有固定哨兵小样。",
                stage="review",
                artifacts=("生产数据/consistency_probe_pack.json", "设定库/consistency_probe_pack.json"),
            ))
        else:
            res["notes"].append("项目尚未形成多集/媒体产物，PROBE 暂不强制。")
        return res
    scenarios = _probe_rows(data)
    names = {
        str(s.get("scenario") or s.get("name") or s.get("id") or "").strip()
        for s in scenarios
        if isinstance(s, dict)
    }
    missing = [name for name in PROBE_SCENARIOS if name not in names]
    if missing:
        res["findings"].append(_row(
            "warn",
            f"consistency_probe_pack 缺哨兵场景：{', '.join(missing)}。",
            stage="review",
            artifacts=(rel,),
        ))
    for row in scenarios:
        verdict = str(row.get("verdict") or row.get("status") or row.get("result") or "").lower()
        name = str(row.get("scenario") or row.get("name") or row.get("id") or "")
        if verdict in {"block", "fail", "failed", "red"}:
            res["findings"].append(_row(
                "block",
                f"一致性 probe 场景 {name or '(unknown)'} 未通过；升级/发布前需先修复哨兵小样。",
                stage="review",
                artifacts=(rel,),
            ))
        if not (row.get("input_fingerprint") or row.get("recipe_hash") or row.get("baseline_hash")):
            res["findings"].append(_row(
                "warn",
                f"一致性 probe 场景 {name or '(unknown)'} 缺 baseline/input 指纹，无法做升级前后对比。",
                stage="review",
                artifacts=(rel,),
            ))
    if isinstance(data, dict) and not (data.get("latest_result") or data.get("run_id") or data.get("last_run_at")):
        res["findings"].append(_row(
            "warn",
            "consistency_probe_pack 缺 latest_result/run_id；无法确认当前后端组合是否跑过哨兵。",
            stage="review",
            artifacts=(rel,),
        ))
    routes = _load_routes(root, ep)
    primary_backends = _route_primary_backends(routes)
    backend_rows = _probe_backend_scores(data, scenarios)
    if primary_backends and not backend_rows:
        res["findings"].append(_row(
            "warn",
            "项目已有视频模型路由，但 consistency_probe_pack 缺 backend_scores/backend_results；"
            "probe 仍停留在场景小样，未形成后端选择基准。",
            stage="review",
            artifacts=(rel, f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/video_model_routes.json"),
        ))
    elif backend_rows:
        measured_backends = _unique(str(row.get("backend") or "") for row in backend_rows)
        for backend in primary_backends:
            if not any(_backend_match(backend, measured) for measured in measured_backends):
                res["findings"].append(_row(
                    "warn",
                    f"当前 route.primary_backend={backend} 未出现在 probe backend_scores；路由没有哨兵基准兜底。",
                    stage="review",
                    artifacts=(rel, f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/video_model_routes.json"),
                ))
        scored: Dict[str, List[float]] = defaultdict(list)
        for row in backend_rows:
            backend = str(row.get("backend") or "").strip()
            score = _backend_score_value(row)
            if backend and score is not None:
                scored[backend].append(score)
        averages = {backend: sum(values) / len(values) for backend, values in scored.items() if values}
        if averages:
            best_backend, best_score = max(averages.items(), key=lambda item: item[1])
            allowed_delta = 0.05
            if isinstance(data, dict):
                allowed_delta = _num(data.get("route_score_delta_tolerance")) or allowed_delta
            route_blob = _json_text(routes)
            route_rec, route_rec_rel = _probe_route_recommendations(root, ep)
            has_selection_reason = bool(isinstance(data, dict) and (
                data.get("route_recommendations") or data.get("selected_backend") or data.get("selection_reason") or data.get("fallback_reason")
            )) or bool(route_rec) or any(token in route_blob for token in ("selection_reason", "fallback_reason", "fallback_allowed", "route_recommendation"))
            for backend in primary_backends:
                matched = next((name for name in averages if _backend_match(backend, name)), "")
                if not matched:
                    continue
                delta = best_score - averages[matched]
                if best_backend != matched and delta > allowed_delta and not has_selection_reason:
                    res["findings"].append(_row(
                        "warn",
                        f"probe benchmark 显示 {best_backend} 平均一致性分 {best_score:.3f} 高于当前路由 {backend} "
                        f"{delta:.3f}，但缺 selection_reason/fallback_reason；确认是否为成本/速度的显式取舍。"
                        "可运行 probe_route_recommend.py --write 生成路由建议。",
                        stage="review",
                        artifacts=(rel, f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/video_model_routes.json", route_rec_rel or f"生产数据/video_route_recommendations_{ep}.json"),
                    ))
        failing_backend = [
            row for row in backend_rows
            if str(row.get("verdict") or row.get("status") or row.get("result") or "").lower() in {"block", "fail", "failed", "red"}
        ]
        for row in failing_backend[:8]:
            res["findings"].append(_row(
                "block",
                f"probe 后端基准未通过：scenario={row.get('scenario') or '(unknown)'} backend={row.get('backend') or '(unknown)'}。",
                stage="review",
                artifacts=(rel,),
            ))
    return res


def check_cost_route(root: str, ep: str) -> dict:
    res = {"available": True, "findings": [], "notes": []}
    events = [e for e in _load_events(root) if str(e.get("episode") or "") == ep and str(e.get("event") or "") in {"generation", "redraw"}]
    by_asset: Dict[str, List[dict]] = defaultdict(list)
    for e in events:
        asset = _event_asset(e)
        if asset:
            by_asset[asset].append(e)
        if e.get("event") in {"generation", "redraw"} and not isinstance(e.get("cost"), Mapping):
            res["findings"].append(_row(
                "warn",
                f"{asset or '(unknown asset)'} 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。",
                stage=str(e.get("stage") or "review"),
                artifacts=("生产数据/production_events.jsonl",),
            ))
    for asset, rows in by_asset.items():
        providers = _unique(_event_provider(e) for e in rows)
        if len(providers) > 1:
            allowed = any(str((e.get("generation") or {}).get("redraw_category") or "").strip() in {"backend_migration", "face_consistency"} for e in rows)
            if allowed:
                continue
            res["findings"].append(_row(
                "block",
                f"{asset} 同一资产生成跨 provider：{providers}；未声明 backend_migration 会造成一致性和成本归因混乱。",
                stage="image" if asset.lower().endswith(".png") else "video",
                artifacts=("生产数据/production_events.jsonl",),
            ))
        passes = [e for e in rows if str((e.get("generation") or {}).get("status") or "").lower() == "pass"]
        if len(passes) > 1 and not any((e.get("generation") or {}).get("redraw_reason") for e in rows):
            res["findings"].append(_row(
                "warn",
                f"{asset} 有多次 pass 记录但缺 redraw_reason/验收选择原因；后续无法判断哪版是正片依据。",
                stage="review",
                artifacts=("生产数据/production_events.jsonl",),
            ))
    routes = _load_routes(root, ep)
    if routes:
        for asset, rows in by_asset.items():
            latest = rows[-1]
            stage = str(latest.get("stage") or "").lower()
            # Video routes describe MP4 generation backends. Image keyframes and
            # compose/final-master events can share Clip_XX filenames but should
            # not be compared against route.primary_backend.
            if stage != "video" and not str(asset).lower().endswith(".mp4"):
                continue
            clip = _clip_num(os.path.splitext(os.path.basename(asset))[0])
            route = routes.get(clip)
            if not route:
                continue
            primary = str(route.get("primary_backend") or "").lower()
            provider = _event_provider(latest).lower()
            fallback_raw = route.get("fallback_backends") or route.get("fallback_backend") or []
            fallback_backends = [str(x).lower() for x in _as_list(fallback_raw)]
            fallback_allowed = any(
                fb and (fb in provider or provider in fb)
                for fb in fallback_backends
            )
            if primary and provider and primary not in provider and provider not in primary:
                if fallback_allowed:
                    continue
                res["findings"].append(_row(
                    "warn",
                    f"{clip} 最新生成 provider={provider} 与 route.primary_backend={primary} 不一致；确认是合法 fallback 还是路由漂移。",
                    shot=clip,
                    stage="video_prompt",
                    artifacts=(f"出视频/{ep}/prompt/video_model_routes.json", "生产数据/production_events.jsonl"),
                ))
    return res


def analyze(root: str, ep: str) -> dict:
    sections = {
        "真值源(TRUTH)": check_consistency_truth_map(root, ep),
        "多视角身份包(MVIEW)": check_multiview_identity_pack(root, ep),
        "实体记忆(EMB)": check_entity_memory_bank(root, ep),
        "物件常驻(O3)": check_object_permanence(root, ep),
        "持有账本(POS)": check_possession_ledger(root, ep),
        "视线状态回读(X2)": check_axis_state_readback(root, ep),
        "状态转场视频证据(ST1)": check_state_transition_verification(root, ep),
        "交互接触(I1)": check_interaction_graph(root, ep),
        "结构化交互图谱(I2)": check_interaction_schema(root, ep),
        "物理事件图(PHY)": check_physical_event_graph(root, ep),
        "世界一致性(WCS)": check_world_consistency_score(root, ep),
        "视频证据完整性(EVID)": check_video_evidence_completeness(root, ep),
        "成片统一(C1)": check_final_composite(root, ep),
        "声音空间(ASP)": check_acoustic_space(root, ep),
        "成片时间线探针(FT1)": check_final_timeline_probe(root, ep),
        "生成配方(RCP)": check_generation_recipe(root, ep),
        "强配方Schema(RCP2)": check_recipe_schema(root, ep),
        "系列包装(PKG)": check_series_packaging(root, ep),
        "台词语域(D1)": check_dialogue_register(root, ep),
        "场景平面(FP1)": check_floorplan(root, ep),
        "成本路由(K1)": check_cost_route(root, ep),
        "人审校准集(CAL)": check_review_calibration(root, ep),
        "一致性探针包(PROBE)": check_probe_pack(root, ep),
    }
    return {"available": True, "sections": sections}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write-recipe", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.write_recipe:
        res["recipe_path"] = write_recipe_ledger(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        for dim, sec in res["sections"].items():
            active = [r for r in sec.get("findings", []) if r.get("verdict") in {"block", "warn"}]
            print(f"{dim}: {len(active)} finding(s)")
            for row in active[:5]:
                print(f"  - {row.get('verdict')} {row.get('message')}")
    total_block = sum(1 for sec in res["sections"].values() for r in sec.get("findings", []) if r.get("verdict") == "block")
    return 1 if total_block else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
