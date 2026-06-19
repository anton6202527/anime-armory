#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MV 出视频两轴标记（纯函数·可测·mv 线自包含）。

本模块**不路由后端**——mv-video 是「全程同一后端」设计（防跨 clip 风格跳变），
所以这里只做两件不改后端的事，借鉴 n2d-model-router 思路但**结合 MV 特有场景**
重写，绝不 import n2d-*/别线脚本：

1. quality_tier_for_clip(clip, backend):
   副歌高光镜/卡点爽点镜（对齐 beatgrid downbeat 的强拍 clip、副歌/桥段段 clip、
   高能量 clip）→ "high"（值后端 pro/高质量档把脸和运动钉稳）；verse 空镜/铺垫镜
   → "fast"（量产省成本）。只表达质量档**意图**，不写死 model_version——落档侧
   把 high→pro、fast→fast 解析成实际档位。后端无 fast/pro 档 → "n/a"。

2. motion_reference_plan(clip, backend):
   舞蹈镜/副歌环绕运镜镜 → 可把前一段已通过的 clip 当运动/风格视频参考喂进去锁
   运镜节奏（仅当所选后端支持 reference_video_motion，如 Seedance/可灵）。只提示
   （advisory），不强制；后端不支持/非适用镜返回 applicable=False。

判据全部走 clip 字段 + 后端能力表，不 hardcode 厂商分支。判据来源（mv-plan
plan_clips.py 写入 分镜/clip_plan.json 的字段）：
  - clip["beat_role"]   "key"=副歌/桥段/高能量(energy_level>=8)，"normal"=其余
  - clip["section"]     段落名，含 chorus/副歌/drop/hook/refrain → 副歌；含
                        bridge/桥/drop → 桥段
  - clip["energy_level"] "Level N"（或纯数字）能量
  - clip["transition"]  "卡点硬切" = 对齐 downbeat 的强拍卡点切（爽点镜）
  - clip["action_family"] 含 dance/环绕/orbit/circle 等 → 舞蹈/环绕运镜镜
缺字段时优雅降级为 fast / 不臆造（不把缺信息当副歌）。
"""
import re


# ── 后端能力表（mv 线自持，独立于 contract 的渠道清单）───────────────────────
# 只用规范化后的关键词匹配，避免对 contract.MV_VIDEO_CHANNELS 的字面值产生硬耦合。
# quality_tier：后端是否有 fast/pro（或 lite/标准/高保真）质量档可路由。
# motion_reference：后端是否支持 reference_video_motion（视频片段作运动/风格参考）。
_QUALITY_TIER_BACKENDS = {"seedance", "kling", "veo", "hailuo", "runway", "luma"}
_MOTION_REFERENCE_BACKENDS = {"seedance", "kling"}

# section / action_family 关键词
_CHORUS_KEYWORDS = ("chorus", "副歌", "drop", "hook", "refrain")
_BRIDGE_KEYWORDS = ("bridge", "桥", "间奏", "pre", "drop")
_DANCE_KEYWORDS = ("dance", "舞", "choreo", "choreography")
_ORBIT_KEYWORDS = ("环绕", "orbit", "circle", "arc", "绕", "whip", "甩")
_HIT_TRANSITIONS = ("卡点硬切", "卡点切", "硬切")
_HIGH_ENERGY_THRESHOLD = 8


def _normalize_backend(raw):
    return str(raw or "").strip().lower()


def _backend_keyword_hit(raw, keywords):
    text = _normalize_backend(raw)
    return any(k in text for k in keywords)


def backend_supports_quality_tier(backend):
    """该后端是否有可路由的质量档（fast/pro 等）。纯函数·可测。"""
    return _backend_keyword_hit(backend, _QUALITY_TIER_BACKENDS)


def backend_supports_motion_reference(backend):
    """该后端是否支持视频片段运动/风格参考（reference_video_motion）。纯函数·可测。"""
    return _backend_keyword_hit(backend, _MOTION_REFERENCE_BACKENDS)


def _section_text(clip):
    return str(clip.get("section") or "").strip().lower()


def _is_chorus_section(clip):
    return any(k in _section_text(clip) for k in _CHORUS_KEYWORDS)


def _is_bridge_section(clip):
    return any(k in _section_text(clip) for k in _BRIDGE_KEYWORDS)


def _energy_value(clip):
    """从 'Level 8' / 8 / '8' 取出能量数值；缺/不可解析 → None（不臆造）。"""
    raw = clip.get("energy_level")
    if isinstance(raw, (int, float)):
        return int(raw)
    if isinstance(raw, str):
        m = re.search(r"\d+", raw)
        if m:
            return int(m.group(0))
    return None


def _is_beat_hit_clip(clip):
    """对齐 downbeat 的强拍卡点切（爽点镜）。mv-plan 把这类标成 transition='卡点硬切'。"""
    trans = str(clip.get("transition") or "").strip()
    return any(k in trans for k in _HIT_TRANSITIONS)


def _is_dance_or_orbit_clip(clip):
    """舞蹈镜 / 副歌环绕运镜镜——motion_reference 的适用镜型。"""
    fam = str(clip.get("action_family") or "").strip().lower()
    if any(k in fam for k in _DANCE_KEYWORDS):
        return True
    if any(k in fam for k in _ORBIT_KEYWORDS):
        return True
    # 副歌段的环绕/甩运镜也可能写在 transition_motif（如 'whip pan'）里
    motif = str(clip.get("transition_motif") or "").strip().lower()
    if any(k in motif for k in _ORBIT_KEYWORDS):
        return True
    return False


def is_high_tier_clip(clip):
    """本 clip 是否属副歌高光/卡点爽点/高能量镜（值高质量档）。纯函数·可测。

    判据（任一命中即 high）：
      - beat_role == 'key'（mv-plan：副歌/桥段/energy>=8 已聚成 key）
      - section 命中副歌/桥段关键词
      - transition 为对齐 downbeat 的强拍卡点切（爽点镜）
      - energy_level 数值 >= 8
    缺这些信号 → 普通镜（不臆造）。"""
    if str(clip.get("beat_role") or "").strip().lower() == "key":
        return True
    if _is_chorus_section(clip) or _is_bridge_section(clip):
        return True
    if _is_beat_hit_clip(clip):
        return True
    energy = _energy_value(clip)
    if energy is not None and energy >= _HIGH_ENERGY_THRESHOLD:
        return True
    return False


def quality_tier_for_clip(clip, backend):
    """本 clip 质量档路由意图。纯函数·可测。后端无 fast/pro 档 → 'n/a'。

    high = 副歌高光镜/卡点爽点镜/高能量镜（值后端 pro/高质量档把脸和运动钉稳）；
    fast = verse 空镜/铺垫镜（量产省成本）。**只给意图，不写死 model_version**——
    落档侧把 high→pro、fast→fast 解析成实际档位。**不改后端选择**（mv 全程同一后端）。"""
    if not backend_supports_quality_tier(backend):
        return "n/a"
    return "high" if is_high_tier_clip(clip) else "fast"


def motion_reference_plan(clip, backend):
    """舞蹈镜/副歌环绕运镜镜的视频运动参考计划（advisory）。纯函数·可测。

    applicable=True 仅当：镜型是舞蹈/环绕运镜镜 **且** 后端支持 reference_video_motion
    （Seedance/可灵）。把同段前一条已通过的 clip 作运动/风格参考喂进去锁运镜节奏。
    只提示不强制——首条镜无前序参考时下游自然跳过；非适用镜返回 applicable=False。
    **不改后端选择**（与 mv 同后端铁律不冲突）。"""
    applicable = _is_dance_or_orbit_clip(clip) and backend_supports_motion_reference(backend)
    plan = {"applicable": applicable}
    if applicable:
        plan["use"] = "prior_approved_clip_as_video_reference"
        plan["note"] = (
            f"{backend} 支持视频片段参考（reference_video_motion）：把同段前一条已通过的 clip 作"
            "运动/风格参考喂进去，锁运镜节奏与运动风格（舞蹈/环绕运镜镜的跨镜运动连续性轴，"
            "与图身份锁正交）。advisory：首条镜或无前序参考时跳过，不强制、不换后端。"
        )
    return plan
