#!/usr/bin/env python3
"""Shot split decision planner for n2d storyboard clips.

This converts story/grammar/generation-risk signals into a pre-cost decision
artifact: keep a clip as-is, split it, require a template, add anchors, or defer
fragile pieces to compositing. It is report-first; hard blocking remains in the
existing contract/risk gates.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import shot_risk_audit as sra  # noqa: E402
try:
    import story_economy_audit as sea  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover - planner still works without advisory layer
    sea = None  # type: ignore

N2D_LIB = Path(__file__).resolve().parents[2] / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
try:  # 单拍多镜合并上限：后端能力感知（同线 _lib）；不可用时回落历史 15s。
    from n2d_platform_profiles import single_take_merge_ceiling_seconds  # type: ignore  # noqa: E402
    from n2d_settings import get_setting  # type: ignore  # noqa: E402
except Exception:  # pragma: no cover
    single_take_merge_ceiling_seconds = None  # type: ignore
    get_setting = None  # type: ignore

KIND = "n2d_shot_split_decision_plan"
VIDEO_SHOT_PLAN_THRESHOLD_SEC = 12.0
VIDEO_SHOT_HARD_MAX_SEC = 15.0
VIDEO_SHOT_TARGET_SEC = 6.0

# 拆镜经济性（2026-07-22 clip 经济性回修·第二阶段）：治「简单叙事拆成太多付费 take」。
# 低风险、纯镜位覆盖、跨度 ≤ 硬上限的多镜位 Clip 默认合并为一次多镜生成（single_take_multishot），
# 不再要求 storyboard 显式声明；奇观/大表情/高生成风险/需锚帧链/需模板的镜头仍强制安全拆分。
# storyboard 仍可显式 take_policy=single_take_multishot 覆盖，或用下列关键字显式要求逐镜独立付费 take。
TAKE_POLICY_OPT_OUT = {"split_each", "multi_take", "multitake", "independent_takes", "force_split"}
# 只要出现任一「因剧情/风险而拆」的动作，就不自动合并（仅镜位覆盖导致的 split_video_shots 可合并）。
SAFETY_SPLIT_ACTIONS = {
    "split_reaction",
    "split_establish_detail_reaction",
    "template_required",
    "add_mid_or_multi_anchor",
    "defer_to_composite",
    "compress_before_video",
}

NARRATIVE_RE = re.compile(
    r"(选择|决定|代价|后果|真相|揭示|反转|爽点|打脸|觉醒|危机|集尾|钩|兑现|承诺|目标|动机|杀局|赴险)"
)
PEAK_RE = re.compile(r"(爽点|反转|觉醒|高光|集尾|CU硬切|真相|揭示|危机)")
ESTABLISH_RE = re.compile(r"(ELS|LS|大全景|大远景|全景|远景|establish|定场)", re.I)
CLOSE_RE = re.compile(r"(CU|ECU|MCU|特写|近景|大特写|反打|正反打)")
COMPOSITE_RE = re.compile(
    r"(overlay|系统面板|屏幕|文字|字幕|妖纹|证据|光幕|法阵|阵法|阵图|剪影|长安气象|VFX_|EVIDENCE_|特效)"
)
def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(flatten(v) for v in value.values())
    return str(value or "")


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def load_storyboard(root: Path, ep: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    path = root / "脚本" / ep / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        return [], f"缺 {path}"
    except json.JSONDecodeError as exc:
        return [], f"storyboard.json 不可解析：{exc}"
    clips = data.get("clips") if isinstance(data, dict) else None
    if not isinstance(clips, list) or not clips:
        return [], "storyboard.json 缺非空 clips[]"
    return [c for c in clips if isinstance(c, dict)], None


def _shot_size(clip: Mapping[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    return str(cont.get("shot_size") or clip.get("shot_size") or "")


def _has_anchor(clip: Mapping[str, Any]) -> bool:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    return bool(cont.get("midframe") or cont.get("anchors") or cont.get("midframe_exempt_reason"))


def duration_of(clip: Mapping[str, Any]) -> Optional[float]:
    for key in ("duration", "duration_sec", "story_duration", "seconds", "时长"):
        value = clip.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            if match:
                return float(match.group(0))
    return None


def _segment_id(parent: str, index: int) -> str:
    return f"{parent}_shot{index:02d}"


def _shot_range(value: Any) -> Optional[Tuple[float, float]]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except (TypeError, ValueError):
            return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:s|秒)?\s*[-~—–至]\s*([0-9]+(?:\.[0-9]+)?)", str(value or ""))
    if not match:
        return None
    return float(match.group(1)), float(match.group(2))


def plan_video_shot_segments(
    parent: str,
    duration: Optional[float],
    shots: Optional[Sequence[Mapping[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Plan physical takes from editorial shot grammar, then duration fallback.

    Two storyboard shots are two editorial takes even when the parent Clip is
    shorter than 12s. Backend minimums are handled later by duration
    quantization + tail trim; they must not stretch the edit beat.
    """
    if duration is None:
        return []
    explicit: List[Tuple[float, float, Mapping[str, Any]]] = []
    for shot in shots or []:
        if not isinstance(shot, Mapping):
            continue
        timing = _shot_range(shot.get("t") or shot.get("time") or shot.get("range"))
        if timing and 0 <= timing[0] < timing[1] <= float(duration) + 0.05:
            explicit.append((timing[0], timing[1], shot))
    explicit.sort(key=lambda row: row[0])
    has_editorial_coverage = len(explicit) > 1 and any(
        any(row[2].get(key) for key in ("lens", "camera", "shot_size")) for row in explicit
    )
    if has_editorial_coverage:
        boundaries = [0.0] + [row[0] for row in explicit[1:]] + [float(duration)]
        rows: List[Dict[str, Any]] = []
        for idx, (start, end) in enumerate(zip(boundaries, boundaries[1:]), 1):
            source = explicit[min(idx - 1, len(explicit) - 1)][2]
            rows.append({
                "video_shot_id": _segment_id(parent, idx),
                "parent_story_clip": parent,
                "index": idx,
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "duration_sec": round(end - start, 3),
                "reason": "storyboard_editorial_cut",
                "shot_description": str(source.get("description") or source.get("visual") or source.get("action") or ""),
                "shot_lens": str(source.get("lens") or source.get("shot_size") or source.get("camera") or ""),
            })
        return rows
    if duration <= VIDEO_SHOT_PLAN_THRESHOLD_SEC:
        return []
    count = max(2, int(math.ceil(float(duration) / VIDEO_SHOT_TARGET_SEC)))
    seg = float(duration) / count
    rows: List[Dict[str, Any]] = []
    cursor = 0.0
    for idx in range(count):
        start = cursor
        end = float(duration) if idx == count - 1 else round((idx + 1) * seg, 3)
        rows.append({
            "video_shot_id": _segment_id(parent, idx + 1),
            "parent_story_clip": parent,
            "index": idx + 1,
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "duration_sec": round(end - start, 3),
            "target_duration_sec": VIDEO_SHOT_TARGET_SEC,
            "reason": "continuous_take_exceeds_generation_window",
        })
        cursor = end
    return rows


def narrative_weight(clip: Mapping[str, Any], idx: int) -> int:
    """0-3: how much story value would be harmed by deleting/flattening this clip."""
    blob = " ".join(str(clip.get(k) or "") for k in ("rhythm", "narrative_function", "native_speech", "visual", "label"))
    score = 0
    if idx == 1 or "first_3s" in blob or "开场" in blob:
        score += 1
    if NARRATIVE_RE.search(blob):
        score += 1
    if PEAK_RE.search(blob) or clip.get("causal_bridge") or clip.get("template") == "reveal_reaction_chain":
        score += 1
    return min(3, score)


def grammar_need(clip: Mapping[str, Any], idx: int) -> int:
    """0-3: how much film grammar suggests an explicit split/shot pattern."""
    blob = flatten(clip)
    shot_size = _shot_size(clip)
    tags = []
    if idx == 1 or ESTABLISH_RE.search(shot_size):
        tags.append("establish")
    if CLOSE_RE.search(shot_size) and PEAK_RE.search(blob):
        tags.append("reaction_or_peak_closeup")
    if str(clip.get("template") or "") in {"dialogue_shot_reverse", "reveal_reaction_chain", "public_confrontation"}:
        tags.append("structured_chain")
    if "multi_character" in blob or "character_slots" in blob or "same_frame_policy" in blob:
        tags.append("multi_subject_blocking")
    return min(3, len(tags))


def generation_risk_bucket(risk_row: Mapping[str, Any]) -> int:
    """0-5 bucket from shot_risk_audit's numeric score."""
    score = int(risk_row.get("score") or 0)
    if score <= 0:
        return 0
    if score <= 3:
        return 1
    if score <= 5:
        return 2
    if score <= 8:
        return 3
    if score <= 11:
        return 4
    return 5


def decide_actions(
    clip: Mapping[str, Any],
    risk_row: Mapping[str, Any],
    idx: int,
    economy_row: Optional[Mapping[str, Any]] = None,
) -> List[str]:
    tags = set(risk_row.get("tags") or [])
    findings = risk_row.get("findings") or []
    score = int(risk_row.get("score") or 0)
    template = str(clip.get("template") or "")
    shot_size = _shot_size(clip)
    blob = flatten(clip)
    duration = duration_of(clip)
    actions: List[str] = []

    def add(action: str) -> None:
        if action not in actions:
            actions.append(action)

    if any(isinstance(f, Mapping) and f.get("severity") == "must" for f in findings):
        add("template_required")
    if risk_row.get("spectacle_type") or template or "many_named_characters" in tags:
        add("template_required")
    if ("multi_character" in tags or "many_named_characters" in tags) and ("mouth_visible" in tags or CLOSE_RE.search(shot_size)):
        add("split_reaction")
    if template == "reveal_reaction_chain" or ("reveal" in blob.lower() and "急报" in blob):
        add("split_establish_detail_reaction")
    if ("large_expression_span" in tags or "long_clip_8s" in tags or score >= 8) and not _has_anchor(clip):
        add("add_mid_or_multi_anchor")
    if "vfx_or_asset" in tags and COMPOSITE_RE.search(blob) and not (template or risk_row.get("spectacle_type")):
        add("defer_to_composite")
    if score >= 11 and ("vfx_or_asset" in tags or "multi_character" in tags or risk_row.get("spectacle_type")):
        add("defer_to_composite")
    if duration is not None and duration > VIDEO_SHOT_PLAN_THRESHOLD_SEC:
        add("split_video_shots")
    shot_rows = clip.get("shots") if isinstance(clip.get("shots"), list) else []
    if len(shot_rows) > 1 and any(
        isinstance(row, Mapping) and any(row.get(key) for key in ("lens", "camera", "shot_size"))
        for row in shot_rows
    ):
        add("split_video_shots")
    if economy_row:
        over_budget = economy_row.get("over_budget_sec")
        try:
            over = float(over_budget or 0.0)
        except (TypeError, ValueError):
            over = 0.0
        if over > 0 and not economy_row.get("detail_allowed"):
            add("compress_before_video")
    if not actions:
        add("keep_single")
    return actions


def clip_take_policy(clip: Mapping[str, Any]) -> str:
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    return str(clip.get("take_policy") or cont.get("take_policy") or "").strip().lower()


def _has_editorial_lens_coverage(clip: Mapping[str, Any]) -> bool:
    """本 Clip 是否是「一个 story clip 内多个镜位覆盖」——合并的前提。"""
    shot_rows = clip.get("shots") if isinstance(clip.get("shots"), list) else []
    lensed = [
        r for r in shot_rows
        if isinstance(r, Mapping) and any(r.get(k) for k in ("lens", "camera", "shot_size"))
    ]
    return len(lensed) > 1


def project_single_take_ceiling(root: Path) -> float:
    """本项目的单拍多镜合并上限（秒）：读 `_设置.md` 生视频模型（旧键 生视频AI 兼容）→
    后端能力表；未设/未知/查询失败 → 历史 15s。下限钳 VIDEO_SHOT_HARD_MAX_SEC，
    只会随已验后端单段上限升高（如 Seedance 2.5 验到 30s）而放大合并机会，绝不倒退。"""
    if single_take_merge_ceiling_seconds is None or get_setting is None:
        return VIDEO_SHOT_HARD_MAX_SEC
    try:
        backend = get_setting(str(root), "生视频模型", "") or get_setting(str(root), "生视频AI", "")
        return float(single_take_merge_ceiling_seconds(backend, floor=VIDEO_SHOT_HARD_MAX_SEC))
    except Exception:
        return VIDEO_SHOT_HARD_MAX_SEC


def single_take_policy_verdict(
    clip: Mapping[str, Any],
    risk_row: Mapping[str, Any],
    actions: Sequence[str],
    ceiling_seconds: Optional[float] = None,
) -> Tuple[bool, str, str]:
    """本 Clip 是否用一次多镜生成（single_take_multishot），及其来源。

    返回 (single_take, ignored_reason, source)：
      - source="storyboard_take_policy"：storyboard 显式声明。
      - source="auto_low_risk_editorial"：低风险纯镜位覆盖镜，默认自动合并。
      - source=""：不合并（保持逐镜/逐段付费 take）。
    生效条件：叙事跨度 ≤ 单次生成硬上限，且不属于高生成风险/大表情/奇观/需锚帧链/需模板镜。
    安全拆分与锚帧链永远优先于省生成次数。"""
    policy = clip_take_policy(clip)
    explicit = policy == "single_take_multishot"
    if policy in TAKE_POLICY_OPT_OUT:
        # storyboard 显式要求逐镜独立付费 take：尊重，不自动合并。
        return False, "", ""
    limit = float(ceiling_seconds) if ceiling_seconds and ceiling_seconds > 0 else VIDEO_SHOT_HARD_MAX_SEC
    duration = duration_of(clip)
    if duration is None or duration > limit:
        if explicit:
            return False, (
                f"take_policy 忽略：叙事跨度 {duration if duration is not None else '未知'}s 超过单次生成上限 "
                f"{limit:g}s（后端能力感知），仍按镜位/生成窗口拆 take"
            ), ""
        return False, "", ""
    # 真高风险才否决（多镜后端在内部镜位切换处自带再锚定，单纯「长于 8s」不算）：
    # 大表情跨度、奇观镜、高生成风险桶（score>=9）。与 anchor_planner「R1/R3 才回锚帧链」同口径。
    tags = set(risk_row.get("tags") or [])
    if risk_row.get("spectacle_type") or "large_expression_span" in tags or generation_risk_bucket(risk_row) >= 4:
        if explicit:
            return False, "take_policy 忽略：大表情/奇观/高生成风险镜，安全拆分与锚帧链优先于省生成次数", ""
        return False, "", ""
    if explicit:
        return True, "", "storyboard_take_policy"
    # 默认自动合并（不需显式声明）：只对「纯镜位覆盖、无任何剧情/风险拆分动作」的多镜位 Clip 生效。
    # 出现 split_reaction / template_required / add_mid_or_multi_anchor / defer_to_composite / compress 等
    # 有意义的拆分理由时，保持安全拆分。
    if any(a in SAFETY_SPLIT_ACTIONS for a in actions):
        return False, "", ""
    if _has_editorial_lens_coverage(clip):
        return True, "", "auto_low_risk_editorial"
    return False, "", ""


def primary_action(actions: Sequence[str]) -> str:
    priority = [
        "compress_before_video",
        "single_take_multishot",
        "split_video_shots",
        "template_required",
        "split_establish_detail_reaction",
        "split_reaction",
        "add_mid_or_multi_anchor",
        "defer_to_composite",
        "keep_single",
    ]
    for item in priority:
        if item in actions:
            return item
    return actions[0] if actions else "keep_single"


def action_note(action: str) -> str:
    notes = {
        "keep_single": "低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。",
        "split_reaction": "把说话/多人/强表情镜拆成单人 CU、反打、听者反应，减少同框脸漂和口型压力。",
        "split_establish_detail_reaction": "按建制/证据细节/人物反应拆链，尤其适合真相揭示、搜证、关系翻转。",
        "template_required": "复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。",
        "add_mid_or_multi_anchor": "高风险长镜或大表情镜补中段锚帧/多锚/豁免说明。",
        "defer_to_composite": "把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。",
        "split_video_shots": "按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。",
        "compress_before_video": "剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。",
        "single_take_multishot": "一次多镜生成：内部镜位由 multishot-native 后端一次生成（Seedance/Kling 多镜叙事口径），不拆独立付费 take。来源可为 storyboard 显式 take_policy，或低风险纯镜位覆盖镜的默认自动合并（single_take_source=auto_low_risk_editorial）。后端不支持或跨度超窗时由出视频阶段回落 edit_cut 拆 take；奇观/大表情/高风险/需锚帧链镜不自动合并。",
    }
    return notes.get(action, "")


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    clips, err = load_storyboard(root, ep)
    if err:
        return {"kind": KIND, "episode": ep, "ok": False, "findings": [
            {"severity": "must", "code": "missing_storyboard", "message": err}
        ], "decisions": []}

    risk = sra.audit(str(root), ep)
    risk_rows = risk.get("clips") or []
    by_id = {str(row.get("id")): row for row in risk_rows if isinstance(row, Mapping)}
    economy_report: Mapping[str, Any] = {}
    economy_rows: Dict[str, Mapping[str, Any]] = {}
    if sea is not None:
        try:
            economy_report = sea.build_report(root, ep)
            economy_rows = {
                str(row.get("clip")): row
                for row in economy_report.get("clips") or []
                if isinstance(row, Mapping)
            }
        except Exception:
            economy_report = {}
            economy_rows = {}
    single_take_ceiling = project_single_take_ceiling(root)
    decisions: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        row = by_id.get(cid)
        if row is None and idx - 1 < len(risk_rows) and isinstance(risk_rows[idx - 1], Mapping):
            row = risk_rows[idx - 1]
        if row is None:
            row = {}
        economy_row = economy_rows.get(cid, {})
        actions = decide_actions(clip, row, idx, economy_row)
        single_take, policy_ignored_reason, single_take_source = single_take_policy_verdict(
            clip, row, actions, ceiling_seconds=single_take_ceiling)
        if single_take:
            actions = [a for a in actions if a != "split_video_shots"]
            actions.insert(0, "single_take_multishot")
        primary = primary_action(actions)
        tags = list(row.get("tags") or [])
        duration = duration_of(clip)
        video_segments = plan_video_shot_segments(cid, duration, clip.get("shots") if isinstance(clip.get("shots"), list) else None)
        if single_take:
            # 内部镜位保留为「一次生成内的镜头阶梯」信息，不再是独立付费 take。
            for seg in video_segments:
                seg["reason"] = "single_take_multishot_internal_shot"
                seg["physical_take"] = False
        decisions.append({
            "clip": cid,
            "label": clip.get("label", ""),
            "duration_sec": duration,
            "primary_action": primary,
            "actions": actions,
            "narrative_weight": narrative_weight(clip, idx),
            "grammar_need": grammar_need(clip, idx),
            "generation_risk": generation_risk_bucket(row),
            "risk_score": row.get("score", 0),
            "risk_tags": tags,
            "reason": action_note(primary),
            "pilot_candidate": cid in {str(p.get("id")) for p in risk.get("pilot_candidates") or [] if isinstance(p, Mapping)},
            "story_economy": {
                "economy_class": economy_row.get("economy_class"),
                "detail_allowed": economy_row.get("detail_allowed"),
                "target_story_clip_sec": economy_row.get("target_story_clip_sec"),
                "recommended_action": economy_row.get("recommended_action"),
                "over_budget_sec": economy_row.get("over_budget_sec"),
                "rewrite_demo": economy_row.get("rewrite_demo"),
            } if economy_row else {},
            "take_policy": clip_take_policy(clip),
            "single_take_multishot": single_take,
            **({"single_take_source": single_take_source} if single_take else {}),
            **({"take_policy_ignored_reason": policy_ignored_reason} if policy_ignored_reason else {}),
            "video_shot_policy": {
                "story_clip_plan_threshold_sec": VIDEO_SHOT_PLAN_THRESHOLD_SEC,
                "video_shot_hard_max_sec": VIDEO_SHOT_HARD_MAX_SEC,
                "target_video_shot_sec": VIDEO_SHOT_TARGET_SEC,
                "direct_submit_allowed": (single_take or not video_segments) and not (duration is not None and duration > VIDEO_SHOT_HARD_MAX_SEC),
            },
            "video_shot_segments": video_segments,
        })

    must_findings = [
        {**f, "source": "shot_risk_audit"}
        for f in risk.get("findings") or []
        if isinstance(f, Mapping) and f.get("severity") == "must"
    ]
    summary = {
        "clips": len(decisions),
        "keep_single": sum(1 for d in decisions if d["primary_action"] == "keep_single"),
        "split_or_template": sum(1 for d in decisions if d["primary_action"] != "keep_single"),
        "template_required": sum(1 for d in decisions if "template_required" in d["actions"]),
        "add_anchor": sum(1 for d in decisions if "add_mid_or_multi_anchor" in d["actions"]),
        "defer_to_composite": sum(1 for d in decisions if "defer_to_composite" in d["actions"]),
        "video_shot_split": sum(1 for d in decisions if "split_video_shots" in d["actions"]),
        "single_take_multishot": sum(1 for d in decisions if d.get("single_take_multishot")),
        "single_take_auto": sum(1 for d in decisions if d.get("single_take_source") == "auto_low_risk_editorial"),
        "take_policy_ignored": sum(1 for d in decisions if d.get("take_policy_ignored_reason")),
        "compress_before_video": sum(1 for d in decisions if "compress_before_video" in d["actions"]),
        "direct_submit_blocked": sum(1 for d in decisions if not d["video_shot_policy"]["direct_submit_allowed"]),
        "story_economy_over_budget": sum(1 for d in decisions if float((d.get("story_economy") or {}).get("over_budget_sec") or 0.0) > 0.0),
    }
    return {
        "kind": KIND,
        "episode": ep,
        "ok": not must_findings,
        "summary": summary,
        "decisions": decisions,
        "findings": must_findings,
        "notes": [
            "report-first；真正硬阻塞仍由 validate_storyboard_contract / shot_risk_audit / spectacle_contract_audit 执行。",
            "本计划用于把拆镜理由提前落盘，避免出图/出视频阶段临场重判。",
            "compress_before_video 表示先改编剧表达，不应把啰嗦剧情直接切成多个付费视频段。",
        ],
    }


def render_md(plan: Mapping[str, Any]) -> str:
    lines = [
        "# 镜头拆分决策计划",
        "",
        f"- episode: {plan.get('episode')}",
        f"- ok: {plan.get('ok')}",
        "",
        "| Clip | Dur | Action | Economy | Target | Video Shots | N | G | R | Risk Tags | Reason |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in plan.get("decisions") or []:
        seg_count = len(row.get("video_shot_segments") or [])
        dur = row.get("duration_sec")
        dur_text = f"{float(dur):.3f}s" if isinstance(dur, (int, float)) else ""
        economy = row.get("story_economy") or {}
        target = economy.get("target_story_clip_sec") or {}
        target_text = f"{target.get('min', '')}-{target.get('max', '')}s" if target else ""
        lines.append(
            f"| {row.get('clip')} | {dur_text} | {row.get('primary_action')} | "
            f"{economy.get('economy_class') or ''} | {target_text} | {seg_count or ''} | "
            f"{row.get('narrative_weight')} | {row.get('grammar_need')} | {row.get('generation_risk')} | "
            f"{'、'.join(row.get('risk_tags') or [])} | {row.get('reason')} |"
        )
    lines.append("")
    lines.append("N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。Economy 来自 story_economy_audit；Video Shots 先按明确景别/机位切换拆物理 take，连续长 take 再适配后端窗口；story_clip >15s 不允许未拆直提。")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, plan: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"shot_split_plan_{ep}.json"
    md_path = out / f"shot_split_plan_{ep}.md"
    tmp = json_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, json_path)
    tmp_md = md_path.with_suffix(".md.tmp")
    tmp_md.write_text(render_md(plan) + "\n", encoding="utf-8")
    os.replace(tmp_md, md_path)
    return json_path, md_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d shot split decision planner")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 if inherited risk audit has must findings")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    plan = build_plan(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, plan)
        plan = {**plan, "outputs": {"json": str(jp), "markdown": str(mp)}}
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(render_md(plan))
    if ns.strict and not plan.get("ok", False):
        return 1
    return 0 if plan.get("ok", False) else 1


if __name__ == "__main__":
    raise SystemExit(main())
