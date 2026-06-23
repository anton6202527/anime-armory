#!/usr/bin/env python3
"""Shared spectacle/action contracts for n2d.

This module is the single n2d-line source for high-dynamic and large-scale
shot contracts.  Script audits, review gates, and model routing should import
these fields instead of drifting separate fight/chase/flight definitions.
"""
from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from n2d_const import SHOT_TYPE_KEYWORDS
except ImportError:  # pragma: no cover - package import fallback
    from .n2d_const import SHOT_TYPE_KEYWORDS

TEMPLATE_BASE_FIELDS: Tuple[str, ...] = (
    "template_id",
    "beats",
    "blocking",
    "camera_rule",
    "continuity_must",
    "negative",
)

ACTION_CHOREOGRAPHY_SHOT_TYPES: Tuple[str, ...] = ("fight_exchange", "chase", "flight")
ACTION_CHOREOGRAPHY_COMMON_FIELDS: Tuple[str, ...] = (
    "beats",
    "speed_curve",
    "spatial_path",
    "camera_path",
    "readability_beats",
    "degrade_plan",
)
ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS: Dict[str, Tuple[str, ...]] = {
    "fight_exchange": (
        "attack_path",
        "impact_frame",
        "contact_points",
        "force_direction",
        "recovery_beat",
    ),
    "chase": (
        "screen_direction",
        "distance_curve",
        "obstacle_beats",
        "parallax_layers",
        "overtake_or_escape_beat",
    ),
    "flight": (
        "flight_path",
        "altitude_curve",
        "pose_lock",
        "parallax_layers",
        "mount_or_cloud_lock",
    ),
}

SPECTACLE_TEMPLATE_FIELDS: Dict[str, Tuple[str, ...]] = {
    "fight_exchange": TEMPLATE_BASE_FIELDS + (
        "attack_path",
        "impact_frame",
        "action_scope",
        "contact_points",
        "force_direction",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "readability_beats",
        "recovery_beat",
        "degrade_plan",
    ),
    "chase": TEMPLATE_BASE_FIELDS + (
        "screen_direction",
        "distance_curve",
        "obstacle_beats",
        "speed_curve",
        "spatial_path",
        "camera_path",
        "parallax_layers",
        "readability_beats",
        "overtake_or_escape_beat",
        "degrade_plan",
    ),
    "flight": TEMPLATE_BASE_FIELDS + (
        "pose_lock",
        "background_motion",
        "altitude_path",
        "speed_curve",
        "flight_path",
        "altitude_curve",
        "camera_path",
        "spatial_path",
        "parallax_layers",
        "mount_or_cloud_lock",
        "readability_beats",
        "degrade_plan",
    ),
}

LARGE_ESTABLISHING_FIELDS: Tuple[str, ...] = (
    "geography_map",
    "scale_reference",
    "parallax_planes",
    "landmark_anchor",
    "camera_path",
    "establishing_progression",
    "reuse_asset_id",
)

SPECTACLE_KINDS: Tuple[str, ...] = (
    "fight_exchange",
    "chase",
    "flight",
    "large_establishing",
)

SPECTACLE_PLAN_KIND = "n2d_spectacle_plan"
SPECTACLE_SEQUENCE_PLAN_KIND = "n2d_spectacle_sequence_plan"
SPECTACLE_PROBE_PACK_KIND = "n2d_spectacle_probe_pack"
SPECTACLE_BACKEND_BENCHMARK_KIND = "n2d_spectacle_backend_benchmark"
ACTION_EDIT_CUES_KIND = "n2d_action_edit_cues"
SPECTACLE_VIDEO_QC_KIND = "n2d_spectacle_video_qc"
MOTION_REFERENCE_LIBRARY_KIND = "n2d_motion_reference_library"
SCENE_LAYER_PACK_KIND = "n2d_scene_layer_pack"
TRAJECTORY_CONTROLLER_PLAN_KIND = "n2d_trajectory_controller_plan"

LARGE_ESTABLISHING_RE = re.compile(
    r"(大场景|大场面|宏大|全景|全貌|鸟瞰|航拍|俯瞰|广角远景|万人|千军|战场|城池|城门|"
    r"宗门大殿|山门全景|云海|秘境|仙宫|天宫|巨型|wide establishing|epic|vast|aerial)",
    re.I,
)


def field_missing(value: Any) -> bool:
    if value in (None, ""):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, tuple, dict, set)) and not value:
        return True
    return False


def clip_blob(clip: Mapping[str, Any]) -> str:
    return json.dumps(clip, ensure_ascii=False, sort_keys=True)


def _has_any(text: str, words: Iterable[str]) -> bool:
    low = text.lower()
    return any(str(w).strip().lower() in low for w in words if str(w).strip())


def infer_spectacle_type(clip: Mapping[str, Any]) -> Optional[str]:
    """Return fight/chase/flight/large_establishing when a clip needs spectacle handling."""
    template = str(clip.get("template") or "").strip()
    if template in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        return template
    if template in {"large_establishing", "epic_establishing"}:
        return "large_establishing"

    text = clip_blob(clip)
    for shot_type, keywords in SHOT_TYPE_KEYWORDS:
        if shot_type in ACTION_CHOREOGRAPHY_SHOT_TYPES and _has_any(text, keywords):
            return shot_type
    if LARGE_ESTABLISHING_RE.search(text):
        return "large_establishing"
    return None


def action_choreography_required_fields(shot_type: str) -> Tuple[str, ...]:
    if shot_type not in ACTION_CHOREOGRAPHY_SHOT_TYPES:
        return ()
    return ACTION_CHOREOGRAPHY_COMMON_FIELDS + ACTION_CHOREOGRAPHY_SPECIFIC_FIELDS[shot_type]


def spectacle_required_fields(kind: str) -> Tuple[str, ...]:
    if kind in SPECTACLE_TEMPLATE_FIELDS:
        return SPECTACLE_TEMPLATE_FIELDS[kind]
    if kind == "large_establishing":
        return LARGE_ESTABLISHING_FIELDS
    return ()


def missing_fields(record: Mapping[str, Any], fields: Iterable[str]) -> List[str]:
    return [field for field in fields if field_missing(record.get(field))]


def motion_control_inputs_for_spectacle(kind: str) -> Tuple[str, ...]:
    if kind == "fight_exchange":
        return ("pose_sequence", "depth_sequence", "instance_masks", "contact_map", "camera_path")
    if kind == "chase":
        return ("pose_sequence", "depth_sequence", "camera_path", "spatial_path", "parallax_layers")
    if kind == "flight":
        return ("pose_sequence", "depth_sequence", "camera_path", "spatial_path", "parallax_layers")
    if kind == "large_establishing":
        return ("camera_path", "depth_sequence", "parallax_layers")
    return ()


# ── 动作节拍预算（Veo「一 clip 一主导动作」+ 打斗拆 2–3 拍）────────────────────────────────
# 高动态镜最常见的崩法是「一镜塞完整攻防回合」：模型把攻击+格挡+反击+命中挤进一条 clip，
# 物理引擎会乱（多个冲突动作同时发生）。把动作文字归到几个互斥的「节拍类别」，一镜跨越的类别越多，
# 越该按 beat 拆镜。词典是启发式（中英关键词），消费方应以 warn 为主、production 交付边界再升 block。
ACTION_BEAT_LEXICON: Dict[str, Tuple[str, ...]] = {
    "attack": (
        "出拳", "挥拳", "挥剑", "挥刀", "劈", "斩", "刺", "踢出", "扫腿", "突进", "冲撞", "进攻", "攻击",
        "出招", "施法", "射出", "掷出", "扑向", "punch", "strike", "slash", "kick", "lunge", "thrust", "swing",
    ),
    "block": (
        "格挡", "招架", "格开", "架住", "举盾", "护住", "闪避", "侧闪", "后撤", "躲开", "翻滚避开",
        "block", "parry", "guard", "dodge", "evade", "deflect",
    ),
    "counter": (
        "反击", "回击", "反打", "还击", "借力反", "顺势反", "反手", "counter", "riposte", "counterattack",
    ),
    "impact": (
        "命中", "击中", "打中", "劈中", "斩中", "踢中", "砸中", "撞上", "击飞", "打飞", "踢飞", "贯穿",
        "破防", "倒地", "吐血", "hit", "impact", "land the", "knock", "smash",
    ),
}

# 单个动作节拍可读下限（秒）：低于此，命中帧/受力方向来不及读清（启发式·env/选择点可调）。
MIN_ACTION_BEAT_SECONDS = 1.2
# 一镜跨越的节拍类别数达到此值，视为「一镜塞了完整攻防回合」，应拆 beat。
ACTION_BEAT_CATEGORY_SPLIT_THRESHOLD = 3


def action_beat_categories(text: str) -> List[str]:
    """文字命中了哪些互斥动作节拍类别（attack/block/counter/impact）。纯函数·可测。"""
    low = str(text or "").lower()
    hits: List[str] = []
    for cat, words in ACTION_BEAT_LEXICON.items():
        if any(str(w).strip().lower() in low for w in words if str(w).strip()):
            hits.append(cat)
    return hits


def beat_decomposition(kind: str) -> List[Dict[str, Any]]:
    """该奇观类型推荐的逐拍拆镜（一拍一 clip，相机简单）。供 sequence_plan/gate/script 共用。"""
    plans = {
        "fight_exchange": [
            {"beat": "setup_attack", "intent": "起手/突进，锁攻击方向与力的来源", "camera": "简单跟随，勿叠运镜"},
            {"beat": "impact", "intent": "命中帧硬约束：接触点+受力方向可读，hit_stop 2 帧", "camera": "稳定，留命中帧"},
            {"beat": "react_recover", "intent": "受击反应/收招，交代攻防转换", "camera": "反打或反应特写"},
        ],
        "chase": [
            {"beat": "approach", "intent": "追逃距离曲线起点，锁 screen_direction", "camera": "跟拍同一主方向"},
            {"beat": "obstacle", "intent": "障碍/变向一个结果，速度交给前景与视差", "camera": "加速后切"},
            {"beat": "overtake_or_escape", "intent": "拉开或逼近的结算拍", "camera": "cut_on_motion"},
        ],
        "flight": [
            {"beat": "takeoff", "intent": "起飞/腾空，锁 pose 与御剑/云形", "camera": "仰角起势"},
            {"beat": "cruise", "intent": "巡航，速度交给云层/山体视差", "camera": "侧向横移"},
            {"beat": "arrive_or_maneuver", "intent": "抵达或变向一个机动", "camera": "推进或环绕一次"},
        ],
    }
    return plans.get(kind, [])


def default_degrade_plan(kind: str) -> str:
    plans = {
        "fight_exchange": "拆成起手/命中/反应三镜；命中帧做尾帧硬约束，接触失败则改手部特写+反打。",
        "chase": "拆成追方/逃方/障碍结果三镜；保持同一 screen_direction，用前景遮挡和反打表达速度。",
        "flight": "拆成起飞/巡航/机动/抵达；人物姿态锁定，把速度交给云层、山体和镜头路径。",
        "large_establishing": "先出静态全景关键帧，再做慢推/横移/分层 parallax；复杂人群改剪影或分层合成。",
    }
    return plans.get(kind, "失败两次后拆镜、降运动量，并回到 storyboard 补契约。")


def spectacle_recommendations(kind: str) -> List[str]:
    recs = {
        "fight_exchange": [
            "每个 Clip 只保留一次攻击意图：setup -> attack -> impact -> reaction -> recovery。",
            "必须写 impact_frame/contact_points/force_direction，命中帧可读性优先于花哨运镜。",
            "准备 pose/depth/instance/contact_map；缺控制资产时不要进付费视频，先拆镜或 degrade_only。",
        ],
        "chase": [
            "screen_direction 只允许一条主方向；distance_curve 只能收近或拉远，不在同镜来回重置。",
            "速度交给 parallax_layers、前景遮挡、衣摆发丝和跟拍，主体姿态变化要少。",
            "准备 camera_path/spatial_path/parallax_layers，障碍点要有 obstacle_beats。",
        ],
        "flight": [
            "锁 pose_lock 和 mount_or_cloud_lock；腾云/御剑形状不能边飞边变。",
            "altitude_curve 与 flight_path 分开写，云海/山体作为 parallax 层运动。",
            "大机动拆成巡航和变向两镜；缺控制资产时用背景动、人物少动。",
        ],
        "large_establishing": [
            "先写 geography_map/landmark_anchor/scale_reference，避免大场景只剩氛围词。",
            "把远中近 parallax_planes 分层，慢推/横移优先，少做自由旋转航拍。",
            "可复用 LOC/asset_registry 的场景资产，复杂人群用剪影/雾化/后期层而不是清晰逐人生成。",
        ],
    }
    return list(recs.get(kind, []))


# ── 动作镜成片 QC 八维（VBench + GenVID artifact eval 拆解）────────────────────────────────
# 一个生成的动作镜「成功与否」可拆成这 8 个可机检维度。多数已有专用 runner（标 runner），少数是
# 本轮要补的新维度（标 new）。spectacle_video_qc 据此逐镜汇总「哪几维已被实测证据覆盖、哪几维还空」，
# 把 SPECV 从「只看 contract_only」升级成「八维证据聚合器」。evidence_keys=外部 runner 写进 sidecar
# 的实测字段名（任一命中即视为该维已实测）。重活仍在 out-of-repo conda（见 references/动作镜QC机检.md）。
SPECTACLE_QC_DIMENSIONS: Tuple[Dict[str, Any], ...] = (
    {"key": "optical_flow_direction", "label": "光流方向↔意图对账",
     "proves": "成片实际运动/运镜方向与 prompt 声明的 camera_path/动作方向一致（Kling 笔刷方向≠prompt 必崩的机检版）",
     "evidence_keys": ("optical_flow_direction", "flow_intent_match", "flow_direction_error"),
     "runner": "new", "sample": "high_flow"},
    {"key": "limb_artifact", "label": "肢体畸变/多手多脚",
     "proves": "无异常肢体/多手多脚/穿插畸形（HADM 类，动作峰值帧最易崩）",
     "evidence_keys": ("limb_artifact_score", "extra_limbs", "deformation_score"),
     "runner": "new", "sample": "high_flow"},
    {"key": "motion_smoothness", "label": "运动平滑/动作完成度",
     "proves": "运动平滑、动态程度合理、无冻结帧/异常 jerk、动作有头有尾完成",
     "evidence_keys": ("motion_smoothness", "jerk", "dynamic_degree", "action_completion", "freeze_frame"),
     "runner": "motion_quality_consistency", "sample": "uniform"},
    {"key": "motion_blur_plausibility", "label": "运动模糊合理性",
     "proves": "该糊的高速段糊、不该糊的清楚（区分意图性运动模糊 vs 画质崩坏）",
     "evidence_keys": ("motion_blur_plausibility", "imaging_quality", "blur_score"),
     "runner": "new", "sample": "high_flow"},
    {"key": "endframe_match", "label": "首尾 match-on-action 衔接",
     "proves": "本镜首/尾帧与相邻 clip 末/首帧的动作/视觉衔接（动作匹配剪辑成立）",
     "evidence_keys": ("endframe_match", "seam_action_match", "match_on_action"),
     "runner": "temporal_consistency", "sample": "boundary"},
    {"key": "axis_continuity", "label": "跨镜动作连续+180°轴线",
     "proves": "相机轨迹稳、不越轴(180°线)、方向不跳变、视差合理",
     "evidence_keys": ("trajectory_error", "axis_consistency", "crossing_line", "parallax_flow_score"),
     "runner": "camera_trajectory_consistency", "sample": "uniform"},
    {"key": "subject_identity", "label": "主体身份保持",
     "proves": "运动中脸/服装/主体不漂、多主体不串换",
     "evidence_keys": ("subject_fidelity", "identity_drift", "subject_swap"),
     "runner": "subject_video_consistency", "sample": "high_flow"},
    {"key": "temporal_flicker", "label": "时序闪烁",
     "proves": "相邻帧无闪烁/抖动/背景跳变（TCI）",
     "evidence_keys": ("temporal_flicker", "tci", "flicker_score"),
     "runner": "temporal_consistency", "sample": "uniform"},
)


def spectacle_qc_dimension_status(external: Mapping[str, Any]) -> Dict[str, str]:
    """逐镜八维核验状态：external sidecar 命中该维任一 evidence_key → verified，否则 unverified。纯函数·可测。"""
    out: Dict[str, str] = {}
    for dim in SPECTACLE_QC_DIMENSIONS:
        keys = dim["evidence_keys"]  # type: ignore[index]
        verified = any(
            str(k) in external and external.get(str(k)) not in (None, "", [], {})
            for k in keys
        )
        out[str(dim["key"])] = "verified" if verified else "unverified"
    return out


def high_flow_sampling_plan(kind: str, duration: float = 0.0) -> Dict[str, Any]:
    """高光流帧重点采样策略：动作峰值处(高光流)最易出 artifact，重模型 runner 应在此加密采样。

    返回供外部 runner 消费的采样契约——FMG-DFS 思路：先用光流定位 motion-salient 段，再在峰值帧
    加密抽帧检肢体畸变/身份漂/模糊。纯函数·可测；duration<=0 时给默认密度。
    """
    try:
        dur = float(duration)
    except (TypeError, ValueError):
        dur = 0.0
    base = max(6, int(round(dur))) if dur > 0 else 6
    peak = "高光流(动作峰值)段每 0.2s 一帧" if kind in ACTION_CHOREOGRAPHY_SHOT_TYPES else "运动显著段加密"
    return {
        "strategy": "optical_flow_guided",
        "base_uniform_frames": min(base, 24),
        "peak_density": peak,
        "boundary_frames": ["first", "last"],
        "note": "FMG-DFS：光流定位 motion-salient 片段→峰值帧加密采样检肢体畸变/身份漂/运动模糊。",
    }


def edit_cues_for_spectacle(kind: str, contract: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    contract = contract or {}
    if kind == "fight_exchange":
        impact = str(contract.get("impact_frame") or "impact")
        return [
            {"cue": "hit_stop", "when": impact, "duration_frames": 2, "purpose": "make impact readable"},
            {"cue": "speed_ramp", "when": "attack_path before impact", "curve": "fast_in_slow_on_hit"},
            {"cue": "screen_shake", "when": impact, "strength": "low", "purpose": "sell force without hiding contact"},
            {"cue": "impact_sfx", "when": impact, "layer": "weapon_or_body_hit"},
        ]
    if kind == "chase":
        return [
            {"cue": "speed_ramp", "when": "obstacle_beats", "curve": "accelerate_then_cut"},
            {"cue": "foreground_whoosh", "when": "parallax layer crosses frame"},
            {"cue": "cut_on_motion", "when": "overtake_or_escape_beat"},
            {"cue": "breath_or_footstep_sfx", "when": "distance_curve changes"},
        ]
    if kind == "flight":
        return [
            {"cue": "wind_whoosh", "when": "flight_path begins"},
            {"cue": "cloud_pass", "when": "altitude_curve changes"},
            {"cue": "parallax_swell", "when": "camera_path pushes through clouds"},
            {"cue": "altitude_music_lift", "when": "arrival or reveal beat"},
        ]
    if kind == "large_establishing":
        return [
            {"cue": "slow_push", "when": "establishing_progression starts"},
            {"cue": "scale_reveal_sfx", "when": "landmark_anchor appears"},
            {"cue": "ambient_bed", "when": "full clip", "layer": "wind/crowd/temple"},
            {"cue": "title_or_locator_hold", "when": "scale_reference is readable"},
        ]
    return []
