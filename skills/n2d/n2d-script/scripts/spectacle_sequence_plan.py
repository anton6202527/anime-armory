#!/usr/bin/env python3
"""Build sequence-level continuity plans for n2d spectacle scenes.

Per-clip spectacle contracts keep individual fight/chase/flight/mount/vehicle/large shots
from becoming free-form prompt prose.  This script adds the missing layer above
them: a contiguous action/large-scene ledger that locks handoff state, screen
direction, path curves, persistent subjects/assets, and reference policy across
clips.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import (  # noqa: E402
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    IDENTITY_LOCK_NEGATIVE_TERMS,
    MOTION_INTENSITY_BY_TEMPLATE,
    SPECTACLE_SEQUENCE_PLAN_KIND,
    action_beat_categories,
    beat_decomposition,
    default_degrade_plan,
    infer_spectacle_type,
    motion_control_inputs_for_spectacle,
    premium_spectacle_passes,
)

# 多角色同框上限：各家图生视频对多主体串脸基本不正面解决——同框具名脸 >2 显著抬升串脸风险，建议拆镜。
SAME_FRAME_CHARACTER_CAP = 2


ACTION_KINDS = set(ACTION_CHOREOGRAPHY_SHOT_TYPES)
ASSET_RE = re.compile(r"\b(?:CHAR|LOC|PROP|WEAPON|OUTFIT|VFX|BEAST|MOUNT|VEHICLE)_[A-Za-z0-9_]+\b")
CHAR_RE = re.compile(r"\bCHAR_[A-Za-z0-9_]+\b")
LOC_RE = re.compile(r"\bLOC_[A-Za-z0-9_]+\b")


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def storyboard_path(root: Path, ep: str) -> Path:
    return root / "脚本" / ep / "storyboard.json"


def output_json_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"spectacle_sequence_plan_{ep}.json"


def output_md_path(root: Path, ep: str) -> Path:
    return root / "生产数据" / f"spectacle_sequence_plan_{ep}.md"


def make_clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("clip_id") or clip.get("id") or clip.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{idx:02d}"


def load_storyboard(root: Path, ep: str) -> Dict[str, Any]:
    path = storyboard_path(root, ep)
    if not path.is_file():
        raise FileNotFoundError(f"storyboard not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("storyboard.json top-level must be an object")
    return data


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return " ".join(_flatten_text(v) for v in value)
    return str(value)


def clip_blob(clip: Mapping[str, Any]) -> str:
    return json.dumps(clip, ensure_ascii=False, sort_keys=True)


def contract_for(clip: Mapping[str, Any], kind: str) -> Dict[str, Any]:
    if kind == "large_establishing":
        for key in ("large_scene_contract", "spectacle_contract", "template_contract"):
            value = clip.get(key)
            if isinstance(value, dict):
                return dict(value)
        return {}
    value = clip.get("template_contract")
    return dict(value) if isinstance(value, dict) else {}


def first_text(record: Mapping[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return _flatten_text(value).strip()
    return ""


def clip_characters(clip: Mapping[str, Any]) -> List[str]:
    chars = sorted(set(CHAR_RE.findall(clip_blob(clip))))
    return chars


def clip_loc(clip: Mapping[str, Any]) -> str:
    for key in ("loc", "location", "scene_id", "location_id"):
        value = str(clip.get(key) or "").strip()
        if value.startswith("LOC_"):
            return value
    found = LOC_RE.findall(clip_blob(clip))
    return found[0] if found else ""


def clip_assets(clip: Mapping[str, Any]) -> List[str]:
    return sorted(set(ASSET_RE.findall(clip_blob(clip))))


def _same_action_sequence(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> bool:
    prev_kind = str(prev.get("spectacle_type") or "")
    cur_kind = str(cur.get("spectacle_type") or "")
    if prev_kind == cur_kind:
        return True
    if prev_kind in ACTION_KINDS and cur_kind in ACTION_KINDS:
        prev_chars = set(prev.get("characters") or [])
        cur_chars = set(cur.get("characters") or [])
        return bool(prev_chars & cur_chars) or not (prev_chars or cur_chars)
    return False


def _same_large_sequence(prev: Mapping[str, Any], cur: Mapping[str, Any]) -> bool:
    if prev.get("spectacle_type") != "large_establishing" or cur.get("spectacle_type") != "large_establishing":
        return False
    return bool(prev.get("loc") and prev.get("loc") == cur.get("loc")) or bool(
        set(prev.get("assets") or []) & set(cur.get("assets") or [])
    )


def _sequence_type(items: Sequence[Mapping[str, Any]]) -> str:
    kinds = {str(item.get("spectacle_type") or "") for item in items}
    if len(kinds) == 1:
        return next(iter(kinds))
    if kinds <= ACTION_KINDS:
        return "mixed_action"
    return "mixed_spectacle"


def _sequence_id(seq_type: str, index: int) -> str:
    if seq_type == "large_establishing":
        prefix = "SQ_LARGE"
    elif seq_type in ACTION_KINDS or seq_type == "mixed_action":
        prefix = "SQ_ACTION"
    else:
        prefix = "SQ_SPECTACLE"
    return f"{prefix}_{index:02d}"


def _merge_texts(items: Sequence[Mapping[str, Any]], key: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item.get(key) or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _reference_policy(seq_type: str) -> Dict[str, Any]:
    if seq_type == "large_establishing":
        return {
            "policy": "scene_layer_pack_required",
            "source": "设定库/scene_layers/LOC_xx/scene_layer_pack.json",
            "use": "大场景同 LOC 复用地标、景深层、parallax 层和调色，不逐镜重想象背景。",
        }
    return {
        "policy": "first_passed_clip_becomes_motion_reference",
        "source": "生产数据/motion_reference_library.json",
        "use": "本序列第一条通过 QC 的 clip 登记为 reference_video_motion/camera_motion_reference，后续同序列优先引用。",
    }


def _split_degrade_plan(seq_type: str) -> str:
    if seq_type == "mixed_action":
        return "按动作目标拆成起势/追击/命中或抵达段；每段只保留一个方向与一个动作结果，保持 handoff_state。"
    return default_degrade_plan(seq_type)


def _build_sequence(items: Sequence[Mapping[str, Any]], index: int) -> Dict[str, Any]:
    seq_type = _sequence_type(items)
    clips = [str(item["clip_id"]) for item in items]
    controls = sorted(set(x for item in items for x in item.get("control_inputs_required", [])))
    characters = sorted(set(x for item in items for x in item.get("characters", [])))
    assets = sorted(set(x for item in items for x in item.get("assets", [])))
    locs = sorted(set(str(item.get("loc") or "") for item in items if item.get("loc")))
    premium_qc = sorted(set(
        dim
        for item in items
        for dim in ((item.get("premium_passes") or {}).get("qc_dimensions") or [])
    ))
    return {
        "sequence_id": _sequence_id(seq_type, index),
        "sequence_type": seq_type,
        "clip_order": clips,
        "spectacle_types": [item.get("spectacle_type") for item in items],
        "subject_slots": {
            "characters": characters,
            "slot_policy": "keep each registered character id in the same screen role across this sequence; do not swap pursuer/target or attacker/defender without an explicit handoff_state.",
        },
        "asset_persistence": {
            "assets": assets,
            "locs": locs,
            "policy": "all listed LOC/PROP/WEAPON/OUTFIT/VFX ids must persist unless a clip handoff_state explicitly changes them.",
        },
        "path_lock": {
            "screen_direction": _merge_texts(items, "screen_direction"),
            "spatial_path_global": _merge_texts(items, "spatial_path"),
            "distance_curve_global": _merge_texts(items, "distance_curve"),
            "altitude_curve_global": _merge_texts(items, "altitude_curve"),
            "camera_path_global": _merge_texts(items, "camera_path"),
        },
        "handoff_states": [
            {
                "clip_id": item["clip_id"],
                "in": item.get("in_state") or "",
                "out": item.get("out_state") or "",
                "continuity": item.get("continuity_text") or "",
            }
            for item in items
        ],
        "required_controls": controls,
        "reference_clip_policy": _reference_policy(seq_type),
        "premium_coverage_policy": {
            "required": bool(premium_qc),
            "qc_dimensions": premium_qc,
            "keyframe_rule": "每条高光动作/奇观 clip 必须有 start→intent_mid→impact/apex→result/end 的关键帧或拆段锚。",
            "post_rule": "action_edit_cues 中的 hit-stop/速度坡/闪白/震屏/SFX 峰值必须和 impact/apex 对齐"
                         "（由 combat_cue_apex_audit.py 机检兑现：impact_frame 须带 `<秒>s` → anchor_planner "
                         "把该秒落成 keyframe 锚 → 剪辑峰值钉同秒；缺一即 warn，核心打斗镜可升 BLOCK）。",
            "review_rule": "SPECV 未覆盖 keyframe_coverage、impact_apex_readability、edit_sfx_sync 时，production 交付边界不可静默签收。",
        },
        "split_degrade_plan": _split_degrade_plan(seq_type),
        # 动作镜 prompt 注入项（prompt 生成器消费）：负向身份锁词钉死脸/服装/配饰/年龄漂移 + 背景闪烁。
        "negative_identity_lock": list(IDENTITY_LOCK_NEGATIVE_TERMS),
        # 多角色同框：≥2 具名脸必须有槽位+执行策略；>2 具名脸建议拆正反打/分组。
        "same_frame_policy": {
            "cap": SAME_FRAME_CHARACTER_CAP,
            "over_cap_clips": [str(item["clip_id"]) for item in items if item.get("same_frame_over_cap")],
            "advice": "同框具名脸 ≥2 必须登记身份槽位+执行策略；>2 的镜建议拆成正反打/分组逐一绑定主体，或压低优先级脸为侧/背/虚焦。",
        },
        # 吃身份的动作角色定妆库建议 3–4 角度参考图建 Visual DNA（正/侧/3⁄4），强动作下脸更稳。
        "identity_reference_advice": "为本序列吃身份的核心角色准备 3–4 角度定妆参考（正/侧/3⁄4），强动作镜降 motion strength/cfg 换脸稳。",
        "gate_policy": "video_preflight blocks if this sequence plan is missing for high-dynamic/large-scene clips.",
    }


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    storyboard = load_storyboard(root, ep)
    clips = storyboard.get("clips") or []
    if not isinstance(clips, list):
        raise ValueError("storyboard.json clips must be a list")
    rows: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        kind = infer_spectacle_type(clip)
        if not kind:
            continue
        contract = contract_for(clip, kind)
        continuity = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        beat_cats = action_beat_categories(clip_blob(clip)) if kind in ACTION_KINDS else []
        chars = clip_characters(clip)
        rows.append({
            "clip_id": make_clip_id(clip, idx),
            "source_id": str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}"),
            "spectacle_type": kind,
            "beat_categories": beat_cats,
            "beat_decomposition": beat_decomposition(kind),
            "motion_intensity": MOTION_INTENSITY_BY_TEMPLATE.get(kind, 2),
            "same_frame_characters": len(chars),
            "same_frame_over_cap": len(chars) > SAME_FRAME_CHARACTER_CAP,
            "characters": clip_characters(clip),
            "loc": clip_loc(clip),
            "assets": clip_assets(clip),
            "screen_direction": first_text(contract, ("screen_direction", "direction", "axis")),
            "spatial_path": first_text(contract, ("spatial_path", "flight_path", "path")),
            "distance_curve": first_text(contract, ("distance_curve",)),
            "altitude_curve": first_text(contract, ("altitude_curve", "altitude_path")),
            "camera_path": first_text(contract, ("camera_path",)),
            "in_state": first_text(continuity, ("in", "entry", "start_state", "入点")),
            "out_state": first_text(continuity, ("out", "exit", "end_state", "出点")),
            "continuity_text": _flatten_text(continuity),
            "control_inputs_required": list(motion_control_inputs_for_spectacle(kind)),
            "premium_passes": premium_spectacle_passes(kind),
        })

    sequences_raw: List[List[Dict[str, Any]]] = []
    current: List[Dict[str, Any]] = []
    for row in rows:
        if not current:
            current = [row]
            continue
        prev = current[-1]
        if _same_action_sequence(prev, row) or _same_large_sequence(prev, row):
            current.append(row)
        else:
            sequences_raw.append(current)
            current = [row]
    if current:
        sequences_raw.append(current)

    sequences = [_build_sequence(seq, i) for i, seq in enumerate(sequences_raw, 1)]
    return {
        "kind": SPECTACLE_SEQUENCE_PLAN_KIND,
        "version": 1,
        "root": str(root),
        "episode": ep,
        "clips": rows,
        "sequences": sequences,
        "summary": {
            "spectacle_clips": len(rows),
            "sequences": len(sequences),
            "action_sequences": sum(1 for s in sequences if s["sequence_type"] in ACTION_KINDS or s["sequence_type"] == "mixed_action"),
            "large_scene_sequences": sum(1 for s in sequences if s["sequence_type"] == "large_establishing"),
            "multi_clip_sequences": sum(1 for s in sequences if len(s.get("clip_order") or []) >= 2),
        },
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 高动态/大场景序列连续性总账",
        "",
        f"- episode: {plan.get('episode')}",
        f"- spectacle_clips: {(plan.get('summary') or {}).get('spectacle_clips', 0)}",
        f"- sequences: {(plan.get('summary') or {}).get('sequences', 0)}",
        "",
        "| Sequence | 类型 | Clips | 主体 | 资产/场景 | 控制输入 | 引用策略 |",
        "|---|---|---|---|---|---|---|",
    ]
    for seq in plan.get("sequences") or []:
        subjects = ", ".join(((seq.get("subject_slots") or {}).get("characters") or [])) or "-"
        assets = ", ".join(((seq.get("asset_persistence") or {}).get("assets") or [])) or "-"
        controls = ", ".join(seq.get("required_controls") or []) or "-"
        ref = (seq.get("reference_clip_policy") or {}).get("policy", "-")
        lines.append(
            "| {sid} | {typ} | {clips} | {subjects} | {assets} | {controls} | {ref} |".format(
                sid=seq.get("sequence_id", ""),
                typ=seq.get("sequence_type", ""),
                clips=", ".join(seq.get("clip_order") or []),
                subjects=subjects,
                assets=assets,
                controls=controls,
                ref=ref,
            )
        )
    return "\n".join(lines)


def write_plan(plan: Mapping[str, Any], root: Path, ep: str) -> Dict[str, Path]:
    out_json = output_json_path(root, ep)
    out_md = output_md_path(root, ep)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    return {"json": out_json, "markdown": out_md}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build n2d sequence-level spectacle continuity plan")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    plan = build_plan(root, ep)
    if ns.write:
        paths = write_plan(plan, root, ep)
        plan["written"] = {k: str(v) for k, v in paths.items()}
    if ns.markdown:
        print(render_markdown(plan))
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
