#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""foley_agent.py — V2A 视觉拟音（可插拔后端 · G5）

分析故事板，识别视觉动因（拔剑/脚步/雨/门/爆炸…）→ 产**带绝对时间戳的拟音计划**，再交给
拟音后端合成 SFX 轨。**拟音后端是选择点**（不写死）：

- 默认：**静音占位**轨（诚实标注·不假装有真音效）——保持向后兼容，compose 仍能拿到一条等长轨。
- 真 V2A 后端：设环境变量 `N2D_FOLEY_CMD` 命令模板（与 vlm_verify 的 `N2D_VLM_CMD` 同套路·厂商无关），
  用 `{plan}` `{out}` `{duration}` 占位，stdout/退出码表示成功；可包装 Sony Woosh(本地公版权重)、
  Mirelo SFX V1 / WaveSpeed(云 V2A API)、Video-Foley 等。例：
    export N2D_FOLEY_CMD='conda run -n woosh python ~/bin/woosh_v2a.py --plan {plan} --out {out} --dur {duration}'

对齐粒度从「clip 起点」细化到 **storyboard 动作时间戳**：环境/天气类铺满整 clip；冲击/动作类
（拔剑/关门/爆炸）落在 clip 内估计的动作时刻（默认 clip 中点，或读 clip 的 `动作时刻`/`action_at`
秒偏移）。诚实边界：无更细数据时是**估计**、已标 `aligned="estimated"`，不臆造精确踩点。

原生音画后端去双层（2026-06-30）：Veo 3.1 / Kling 3.0 / Vidu Q3 等原生音画后端单次出片自带
同步 foley/SFX/环境声。当这类 clip 的原生音轨被保留（视频原生音轨≠丢弃）时，再叠 compose 侧
V2A foley = 重复打击声、糊。`foley_render_policy` 纯函数据此决定 full / suppress；suppress 时只留
foley_plan.json 留档、渲染静音轨让模型原生音效站台。选择点 `后期拟音策略=自动|强制叠加|关闭`
控制默认分支；逃生口 `FORCE_COMPOSE_FOLEY=1` 临时强制叠加。

纯函数（extract_sfx_events / build_foley_plan / load_foley_backend / total_duration /
foley_render_policy）无依赖、有 pytest；ffmpeg/后端·设置读取 I/O best-effort。
退出码：产出 foley_mix.wav=0；未产出=非0（compose 据此回退自造静音轨）。

用法：python3 foley_agent.py <root> <episode>
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

# 视觉动因 → SFX 标签 + 类别（impact=点状落在动作时刻；ambience=铺满整 clip）。
# 关键词可扩展；类别决定对齐策略。顺序即匹配优先级。
SFX_RULES = (
    ("sword_whoosh", "impact", ("剑", "刀", "武器", "兵器", "挥舞", "拔剑", "出鞘", "格挡", "刀光", "剑气")),
    ("body_hit", "impact", ("击打", "命中", "受击", "撞击", "拳", "踢", "摔", "砸")),
    ("explosion", "impact", ("爆炸", "爆裂", "炸开", "轰", "崩塌", "塌")),
    ("magic_cast", "impact", ("法术", "符阵", "灵光", "雷劫", "雷落", "光束", "护盾", "阵法", "施法")),
    ("door", "impact", ("门", "开门", "关门", "推门")),
    ("glass_break", "impact", ("碎裂", "破碎", "玻璃", "瓷碎")),
    ("footsteps", "ambience", ("脚步", "走", "跑", "奔", "踱步")),
    ("weather", "ambience", ("雨", "雷雨", "风", "暴风", "雪", "雷鸣")),
    ("water", "ambience", ("流水", "溪", "河", "瀑布", "水声", "波涛")),
    ("crowd", "ambience", ("人群", "喧闹", "集市", "议论", "围观")),
    ("fire", "ambience", ("火", "篝火", "燃烧", "火焰", "炉火")),
)

DEFAULT_ACTION_FRACTION = 0.5  # impact 类无任何拍点数据时，落在 clip 中点（最后兜底·估计）

# 命中/撞点秒抽取（治"打斗 SFX 落 clip 中点估计、对不上画面命中帧"）——与
# anchor_planner.apex_anchor_seconds 同口径（vendored 保 n2d-compose 自包含·跨 skill 不 import）。
_HIT_SEC_RE = re.compile(r"(\d+(?:\.\d+)?)\s*s")
_HIT_CUE_RE = re.compile(r"命中|impact|peak|撞点|撞击|爆发|apex|hit|collision|砸落|斩落|交击", re.I)


def clip_body(clip: Mapping[str, Any]) -> str:
    """汇总一条 clip 里用于识别音效的文本（prompt + 导演意图 + 描述）。纯函数。"""
    parts = [str(clip.get(k) or "") for k in ("prompt", "导演意图", "description", "描述", "镜头内容")]
    return " ".join(p for p in parts if p)


def _action_offset(clip: Mapping[str, Any], duration: float) -> Optional[float]:
    """读 clip 显式动作时刻（秒偏移）；缺则 None（调用方再退 apex / 估计中点）。纯函数。"""
    for key in ("动作时刻", "action_at", "impact_at", "sfx_at"):
        v = clip.get(key)
        if isinstance(v, (int, float)) and 0 <= float(v) <= max(0.0, duration):
            return float(v)
    return None


def impact_seconds_from_clip(clip: Mapping[str, Any], duration: float) -> List[float]:
    """从 storyboard clip 抽**命中/撞点秒**（打斗 SFX 该踩的真实拍点）。纯函数·可测。

    治"SFX 落 clip 中点估计、对不上画面命中"——命中秒其实早被上游算好(anchor_planner apex-aware /
    combat_cue_apex)，只是从没交给 foley。源（与 anchor_planner.apex_anchor_seconds 同口径）：
      · template_contract.{impact_frame, collision_or_apex_frame}：字段本身即命中帧·直接取 `<秒>s`；
      · template_contract.{post_cue_points, keyframe_plan}：含命中类关键词且带 `<秒>s` 的 cue；
      · continuity.anchors 里 use==keyframe 的 at_sec（apex-aware 注回的真关键帧）。
    返回 (0,duration) 内升序去重。无任何命中秒 → []（调用方退显式字段/估计中点）。"""
    if not isinstance(duration, (int, float)) or duration <= 0:
        return []
    secs: set = set()

    def _add(raw: Any) -> None:
        try:
            s = round(float(raw), 2)
        except (TypeError, ValueError):
            return
        if 0.0 < s < float(duration):
            secs.add(s)

    tc = clip.get("template_contract") if isinstance(clip.get("template_contract"), dict) else {}
    for key in ("impact_frame", "collision_or_apex_frame"):
        v = tc.get(key)
        if isinstance(v, str):
            m = _HIT_SEC_RE.search(v)
            if m:
                _add(m.group(1))
    items: List[str] = []
    cues = tc.get("post_cue_points")
    items += [str(x) for x in cues] if isinstance(cues, list) else ([str(cues)] if cues else [])
    kp = tc.get("keyframe_plan")
    if isinstance(kp, dict):
        items += [str(x) for x in kp.values()]
    elif isinstance(kp, str):
        items.append(kp)
    for it in items:
        if _HIT_CUE_RE.search(it):
            m = _HIT_SEC_RE.search(it)
            if m:
                _add(m.group(1))
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    for a in cont.get("anchors") or []:
        if isinstance(a, dict) and str(a.get("use") or "") == "keyframe":
            _add(a.get("at_sec"))
    return sorted(secs)


def extract_sfx_events(clip: Mapping[str, Any], clip_start: float) -> List[Dict[str, Any]]:
    """单 clip → SFX 事件列表（带绝对时间戳）。纯函数·可测。
    - ambience：start=clip 起点，span=整 clip（铺底）。
    - impact：踩拍优先级 = **storyboard 命中/撞点秒（每个命中各一击·aligned=apex）** > 显式 `动作时刻/sfx_at`
      字段（aligned=explicit）> clip 中点估计（aligned=estimated）。治打斗 SFX 对不上命中帧。"""
    body = clip_body(clip)
    if not body.strip():
        return []
    try:
        duration = max(0.0, float(clip.get("duration") or 0.0))
    except (TypeError, ValueError):
        duration = 0.0
    explicit = _action_offset(clip, duration)
    apex_secs = impact_seconds_from_clip(clip, duration)
    events: List[Dict[str, Any]] = []
    seen = set()
    for tag, kind, words in SFX_RULES:
        if tag in seen or not any(w in body for w in words):
            continue
        seen.add(tag)
        if kind == "ambience":
            events.append({"clip_id": clip.get("id"), "tag": tag, "kind": kind,
                           "start": round(clip_start, 3), "duration": round(duration, 3),
                           "aligned": "span"})
        elif apex_secs:
            # 多回合打斗：命中各一击，SFX 踩在真命中帧（而非 clip 中点）。
            for sec in apex_secs:
                events.append({"clip_id": clip.get("id"), "tag": tag, "kind": kind,
                               "start": round(clip_start + sec, 3), "duration": 0.0,
                               "aligned": "apex"})
        else:
            off = explicit if explicit is not None else round(duration * DEFAULT_ACTION_FRACTION, 3)
            events.append({"clip_id": clip.get("id"), "tag": tag, "kind": kind,
                           "start": round(clip_start + off, 3), "duration": 0.0,
                           "aligned": "explicit" if explicit is not None else "estimated"})
    return events


def build_foley_plan(clips: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """整集 clips → 拟音事件计划（绝对时间轴）。纯函数·可测。"""
    plan: List[Dict[str, Any]] = []
    t = 0.0
    for clip in clips:
        plan.extend(extract_sfx_events(clip, t))
        try:
            t += max(0.0, float(clip.get("duration") or 0.0))
        except (TypeError, ValueError):
            pass
    return plan


def total_duration(clips: Sequence[Mapping[str, Any]]) -> float:
    """整集时长（拟音轨总长）。纯函数。"""
    t = 0.0
    for clip in clips:
        try:
            t += max(0.0, float(clip.get("duration") or 0.0))
        except (TypeError, ValueError):
            pass
    return round(t, 3)


def load_foley_backend() -> Optional[Callable[[str, str, float], bool]]:
    """从 `N2D_FOLEY_CMD` 命令模板构造真 V2A 后端；未配置 → None（用静音占位）。纯函数（不执行）。
    模板用 {plan} {out} {duration} 占位；后端读 plan.json 合成 SFX 轨写 out，退出码 0=成功。"""
    tmpl = os.environ.get("N2D_FOLEY_CMD", "").strip()
    if not tmpl or "{out}" not in tmpl:
        return None

    def _backend(plan_path: str, out_wav: str, duration: float) -> bool:
        cmd = (tmpl.replace("{plan}", shlex.quote(plan_path))
                   .replace("{out}", shlex.quote(out_wav))
                   .replace("{duration}", str(duration)))
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=1800)
        except Exception:
            return False
        return res.returncode == 0 and os.path.exists(out_wav)

    return _backend


def foley_render_policy(
    *,
    clip_audio_preserved: bool,
    backend_native_av: Optional[bool],
    native_av_mode_intended: bool = False,
    force_compose_foley: bool = False,
    foley_strategy: str = "自动",
) -> Dict[str, str]:
    """决定 compose 侧 V2A foley 该不该叠（治原生音画后端双层音效）。纯函数·可测。

    2026 原生音画后端（Veo 3.1 / Kling 3.0 / Vidu Q3）单次出片自带同步 foley/SFX/环境声；
    当这类 clip 的原生音轨被保留（视频原生音轨≠丢弃）时，再叠 compose 侧 V2A foley =
    重复打击声、糊。判定优先级：
      · force=1 → full（原生 foley 不满意时人工补，永远放行）；
      · clip 原生音轨被丢弃（discard）→ full（clip 没声，compose foley 是唯一 SFX 源）；
      · clip 原生音轨保留 且（后端原生音画 / 能力未知但项目制作模式=原生音画）→ suppress
        （让模型原生音效站台，避免双层）；
      · 其余（普通静默后端 / 配音先行）→ full（维持现状）。
    backend_native_av=None 表示后端能力未知 → 回退用 native_av_mode_intended 判定。
    返回 {"mode": "full"|"suppress", "reason": ...}。"""
    strategy = str(foley_strategy or "自动").strip().lower()
    if strategy in {"关闭", "off", "disable", "disabled", "none", "无"}:
        return {"mode": "suppress", "reason": "disabled:后期拟音策略"}
    if force_compose_foley or strategy in {"强制叠加", "force", "forced", "full", "always"}:
        return {"mode": "full", "reason": "forced:FORCE_COMPOSE_FOLEY"}
    if not clip_audio_preserved:
        return {"mode": "full", "reason": "clip_audio_discarded:compose_foley_is_only_sfx_source"}
    native = backend_native_av if backend_native_av is not None else native_av_mode_intended
    if native:
        why = "backend_native_av" if backend_native_av else "native_av_mode_intended"
        return {"mode": "suppress", "reason": f"native_audio_present:{why}"}
    return {"mode": "full", "reason": "silent_backend:compose_foley_provides_sfx"}


def _truthy_env(name: str) -> Optional[bool]:
    """读布尔环境变量；未设/空 → None（让上层回退到自推导）。"""
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return None
    return v.strip().lower() in {"1", "true", "yes", "on", "是"}


_N2D_LIB = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "n2d", "_lib"))


def _get_setting(root: str, key: str, default: str = "") -> str:
    """best-effort 读 _设置.md（走 n2d 线 vendored 单一真值源）。缺库/缺文件 → default。"""
    try:
        if _N2D_LIB not in sys.path:
            sys.path.insert(0, _N2D_LIB)
        from n2d_settings import get_setting  # type: ignore
        return str(get_setting(root, key, default) or default)
    except Exception:
        return default


def _resolve_backend_native_av(root: str, ep: str = "") -> Optional[bool]:
    """从本集路由优先查 native_audio 能力。缺路由/缺 adapter → None（policy 回退 intended）。"""
    try:
        if _N2D_LIB not in sys.path:
            sys.path.insert(0, _N2D_LIB)
        import video_backend_adapter  # type: ignore
        channel = _get_setting(root, "生视频渠道", "").strip()
        if ep:
            routed = video_backend_adapter.route_native_audio_profile(root, ep, channel=channel)
            if routed.get("hits"):
                return bool(routed.get("native_audio"))
        backend = (_get_setting(root, "生视频模型", "") or _get_setting(root, "生视频AI", "")).strip()
        channel_or_legacy = channel or _get_setting(root, "生视频AI", "").strip()
        if not backend and not channel_or_legacy:
            return None
        return bool(video_backend_adapter.backend_adapter(backend or channel_or_legacy, channel_or_legacy).get("native_audio"))
    except Exception:
        return None


def _native_av_mode_intended(root: str) -> bool:
    """制作模式=原生音画 → True（clip 自带原生音轨，含模型 foley）。"""
    mode = _get_setting(root, "制作模式", "").lower()
    return "原生音画" in _get_setting(root, "制作模式", "") or "native_av" in mode


def _clip_audio_preserved(root: str) -> bool:
    """clip 原生音轨是否被保留：env 优先；缺则从 视频原生音轨 + 制作模式 自推导（原生音画 compose 自动保留）。"""
    env = _truthy_env("N2D_FOLEY_CLIP_AUDIO_PRESERVED")
    if env is not None:
        return env
    policy = _get_setting(root, "视频原生音轨", "丢弃").strip().lower()
    discarded = policy in {"丢弃", "discard", "none", ""}
    return (not discarded) or _native_av_mode_intended(root)


def _foley_strategy(root: str) -> str:
    return _get_setting(root, "后期拟音策略", "自动").strip() or "自动"


def _resolve_foley_policy(root: str, ep: str = "") -> Dict[str, str]:
    """汇总信号（env 优先·设置兜底）→ 调纯函数 foley_render_policy。best-effort，绝不抛。"""
    intended_env = _truthy_env("N2D_FOLEY_NATIVE_AV_INTENDED")
    intended = intended_env if intended_env is not None else _native_av_mode_intended(root)
    return foley_render_policy(
        clip_audio_preserved=_clip_audio_preserved(root),
        backend_native_av=_resolve_backend_native_av(root, ep),
        native_av_mode_intended=intended,
        force_compose_foley=bool(_truthy_env("FORCE_COMPOSE_FOLEY")),
        foley_strategy=_foley_strategy(root),
    )


def _render_silent(out_wav: str, duration: float) -> bool:
    """静音占位轨（诚实默认·不假装有真音效）。ffmpeg 缺则 False。"""
    dur = max(0.1, float(duration or 0.1))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
           "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{dur}", out_wav]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=300).returncode == 0 and os.path.exists(out_wav)
    except Exception:
        return False


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if len(argv) < 2:
        print("Usage: foley_agent.py <root> <episode>", file=sys.stderr)
        return 2
    root, ep = argv[0], argv[1]
    storyboard_path = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.exists(storyboard_path):
        return 1  # 无 storyboard：交回 compose 自造静音轨（退出码非0）
    try:
        sb = json.load(open(storyboard_path, encoding="utf-8"))
    except Exception:
        return 1
    clips = sb.get("clips", []) or []
    plan = build_foley_plan(clips)
    dur = total_duration(clips)

    work = os.path.join(root, "合成", ep, "_work")
    os.makedirs(work, exist_ok=True)
    plan_path = os.path.join(work, "foley_plan.json")
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    out_wav = os.path.join(work, "foley_mix.wav")

    # 原生音画后端去双层：clip 自带模型同步音效且被保留时，抑制 compose 侧 V2A foley（只留计划档）。
    policy = _resolve_foley_policy(root, ep)
    policy_path = os.path.join(work, "foley_render_policy.json")
    with open(policy_path, "w", encoding="utf-8") as f:
        json.dump({
            "kind": "n2d_foley_render_policy",
            "episode": ep,
            "mode": policy.get("mode"),
            "reason": policy.get("reason"),
            "strategy": _foley_strategy(root),
            "force_compose_foley": bool(_truthy_env("FORCE_COMPOSE_FOLEY")),
            "clip_audio_preserved": _clip_audio_preserved(root),
            "backend_native_av": _resolve_backend_native_av(root, ep),
            "native_av_mode_intended": _native_av_mode_intended(root),
        }, f, ensure_ascii=False, indent=2)
        f.write("\n")
    if policy["mode"] == "suppress":
        if _render_silent(out_wav, dur):
            print(f"原生音画后端自带同步音效（{policy['reason']}）→ compose 侧 V2A foley 已抑制，"
                  f"避免双层打击声/糊。拟音计划 {len(plan)} 事件仅留档 foley_plan.json；"
                  "如需强制叠加 compose foley：FORCE_COMPOSE_FOLEY=1。")
            return 0
        return 1  # 连静音轨都没产出 → compose 回退自造

    backend = load_foley_backend()
    if backend is not None and backend(plan_path, out_wav, dur):
        print(f"✓ 拟音：真 V2A 后端合成 {len(plan)} 个 SFX 事件（N2D_FOLEY_CMD）。")
        return 0
    if backend is not None:
        print("⚠️ N2D_FOLEY_CMD 后端执行失败 → 回退静音占位轨。", file=sys.stderr)
    # 默认/回退：静音占位（诚实——计划已产，真音效需配 N2D_FOLEY_CMD 后端）
    if _render_silent(out_wav, dur):
        print(f"拟音计划 {len(plan)} 个事件已产；当前为**静音占位轨**（配 N2D_FOLEY_CMD 接 Woosh/Mirelo 等 V2A 后端出真音效）。")
        return 0
    return 1  # 连静音轨都没产出 → compose 回退自造


if __name__ == "__main__":
    raise SystemExit(main())
