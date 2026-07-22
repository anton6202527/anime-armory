#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中段锚帧自动规划器 — 扫 storyboard.json 自动识别需要多锚帧的镜头，规划锚帧链。

哪些镜头需要更多关键帧（规则确定性、逐条可解释，报告里写明命中哪条）：
  R1 高运动模板镜：template ∈ {fight_exchange, chase, magic_burst, flight,
     hug_or_pull, intimate_interaction}，duration ≥ 2×min_segment 且 节拍 ≥ 2
     （目标段长更短：fight_target，默认 3.5s——一拍一段贴打斗换招；锚帧密度按
      multiframe_seg_min(1.5s) 排，10s 打斗出 2 锚=4帧、15s 出 3 锚=5帧）
  R2 普通长镜：duration ≥ long_shot_threshold（默认 8s）且 节拍 ≥ 3
  R3 漂移实证镜：生产数据/production_events.jsonl 里该 Clip 有 redraw_reason
     命中漂移关键词（漂/drift/中段/动作崩/路径），duration ≥ 2×min_segment 即命中

节拍数 = len(template_contract.beats)，缺则 len(shots)。
锚点放置：显式 `lens/camera/shot_size` 变化先生成 `use=edit_cut` 边界图；
连续动作锚优先吸附 shots[] 节拍边界，吸不上才均分。`min_segment` 只给 split-relay
兼容路径使用；实际请求下限由后端 duration profile 量化，不能反向拉长剪辑节拍。

默认 dry-run：只写 生产数据/anchor_plan_第N集.json/.md（含成本增量：多 K 张出图 +
视频从 1 段变 K+1 段），给人确认。--write 才把 continuity.anchors 注回
storyboard.json；已手动声明且时间仍落在当前 duration 内的 midframe/anchors 跳过（人工优先），
越界旧锚帧按当前 duration 重算或写豁免。

--default-midframe（普通镜显式 opt-in·选择点「中段锚帧默认」=开启且后端原生支持时用）：
未命中 E1/R1/R2/R3 的普通镜额外规划一张中段锚帧（命名=首帧名+`_mid`，内容=表演节拍
中间拍），按时长分级用法 `use`：
  · split（duration ≥ 2×min_segment）——拆两段 frames2video 接力（真锚定）
  · qc（更短镜或视频后端不原生吃中帧）——不拆段；中帧作出视频验收的中段一致性基准 + 后端多参考输入
  · duration < --midframe-exempt-below（默认 3s）——豁免（中帧与首尾几乎重合），
    write 时写 continuity.midframe_exempt_reason；同时把 policy.midframe_default=true
    写进 storyboard.json，gate 据此强制每镜有 midframe/anchors 或豁免原因。

用法:
  python3 anchor_planner.py <作品根> <第N集> [--write] [--default-midframe]
      [--min-segment 4.0] [--target-segment 5.0] [--fight-target 3.5]
      [--long-shot-threshold 8.0] [--snap-tolerance 1.5] [--midframe-exempt-below 3.0]

测试: cd skills/n2d-script/scripts && python -m pytest test_anchor_planner.py
"""
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
try:
    from n2d_settings import get_setting  # 读「中段锚帧默认」选择点（全局默认=关闭）
except Exception:  # 退化：settings 不可用时按 risk-only 默认走，不阻断规划
    def get_setting(root, key, default=None):  # type: ignore
        return default
try:
    from n2d_platform_profiles import anchor_consumption_plan, backend_supports_three_plus_frames
except Exception:  # 退化：能力档不可用时不假定原生三帧，付费前再要求能力证据
    def backend_supports_three_plus_frames(backend, channel=None):  # type: ignore
        return False
    def anchor_consumption_plan(backend, channel=None, *, anchor_count=0, need_end=False):  # type: ignore
        return {
            "backend": backend or "",
            "execution_backend": backend or "",
            "consumption_mode": "unknown_manual_confirm",
            "action": "manual confirmation required before paid generation",
        }
try:
    from n2d_const import HIGH_MOTION_TEMPLATES  # 单一真值源（gate 帧能力闸门共用同一份）
except Exception:  # 退化：常量不可用时本地兜底，保持与 n2d_const 同步
    HIGH_MOTION_TEMPLATES = frozenset({
        "fight_exchange", "chase", "magic_burst", "flight",
        "hug_or_pull", "intimate_interaction",
    })
DRIFT_REASON_RE = re.compile(r"漂|drift|中段|动作崩|路径", re.I)
# 运动幅度信号（P1a·关键帧密度自适应）：让「描述很激烈/运镜大但没标正式高运动模板」的镜
# 也拿到 R1 级密锚帧，而不是掉到 D0 单中锚。高速动作 + 大幅运镜词。
MOTION_SIGNAL_RE = re.compile(
    r"疾驰|狂奔|奔跑|飞奔|快跑|冲刺|翻滚|腾空|跃起|起跳|跳跃|俯冲|急速|高速|快速|迅猛|猛地|"
    r"激烈|扑向|扑倒|冲撞|撞飞|追逐|追击|逃窜|逃命|坠落|跌落|摔|甩出|挥砍|劈砍|横扫|连击|"
    r"急转|急停|急刹|甩镜|快摇|快切|快速运镜|镜头疾|镜头猛|翻身|旋身|缠斗|扭打|爆冲|疾",
    re.I)


def clip_motion_text(clip: Dict[str, Any]) -> str:
    """聚合 clip 的描述/运镜/状态文本，用于运动幅度判定。纯函数·可测。"""
    parts: List[str] = [str(clip.get("label") or ""), str(clip.get("scene") or "")]
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    parts += [str(cont.get("start_state") or ""), str(cont.get("end_state") or ""),
              str(cont.get("camera") or ""), str(cont.get("motion") or "")]
    for s in clip.get("shots") or []:
        if isinstance(s, dict):
            parts.append(str(s.get("desc") or ""))
            parts.append(str(s.get("camera") or s.get("运镜") or ""))
    return " ".join(parts)


def high_motion_signal(clip: Dict[str, Any]) -> bool:
    """非正式高运动模板镜的运动幅度信号：文本/运镜命中高速动作词，或 `expression_span=大`
    （大表情峰值值得插一张中段锚帧捕捉峰值）。让这类镜也走 R1 级密锚帧。纯函数·可测。"""
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    if str(cont.get("expression_span") or "").strip() == "大":
        return True
    return bool(MOTION_SIGNAL_RE.search(clip_motion_text(clip)))
ASSET_CLIP_RE = re.compile(r"(?i)clip[_\s]*0*(\d+)")
SHOT_T_RE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*s")


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def events_path(root: str) -> str:
    return os.path.join(root, "生产数据", "production_events.jsonl")


def load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def parse_shot_boundaries(clip: Dict[str, Any]) -> List[float]:
    """shots[].t（如 "0-4s" / "4-7s"）→ Clip 内部分镜边界秒数（不含 0 和总时长）。"""
    edges: List[float] = []
    for shot in clip.get("shots") or []:
        if not isinstance(shot, dict):
            continue
        m = SHOT_T_RE.search(str(shot.get("t") or ""))
        if m:
            edges.append(float(m.group(2)))
    duration = clip.get("duration")
    inner = [e for e in sorted(set(edges))
             if e > 0 and (not isinstance(duration, (int, float)) or e < duration)]
    return inner


def beats_count(clip: Dict[str, Any]) -> int:
    tc = clip.get("template_contract")
    if isinstance(tc, dict) and isinstance(tc.get("beats"), list) and tc["beats"]:
        return len(tc["beats"])
    shots = clip.get("shots")
    return len(shots) if isinstance(shots, list) else 0


def redraw_drift_hits(events: List[Dict[str, Any]], ep: str, clip_num: int) -> int:
    """数该 Clip 在出视频阶段命中漂移关键词的重抽事件（R3 实证信号）。"""
    hits = 0
    for ev in events:
        if not isinstance(ev, dict) or ev.get("episode") != ep or ev.get("stage") != "video":
            continue
        gen = ev.get("generation") if isinstance(ev.get("generation"), dict) else {}
        reason = str(gen.get("redraw_reason") or ev.get("redraw_reason") or "")
        if not DRIFT_REASON_RE.search(reason):
            continue
        asset = str(gen.get("asset") or ev.get("asset") or "")
        m = ASSET_CLIP_RE.search(asset)
        if m and int(m.group(1)) == clip_num:
            hits += 1
    return hits


def load_events(root: str) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    path = events_path(root)
    if not os.path.isfile(path):
        return events
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except ValueError:
                continue
            if isinstance(item, dict):
                events.append(item)
    return events


_APEX_CUE_RE = re.compile(r"命中|impact|peak|撞点|撞击|爆发|apex|砸落|hit\b|collision", re.IGNORECASE)
_APEX_SEC_RE = re.compile(r"(\d+(?:\.\d+)?)\s*s")


def apex_anchor_seconds(clip: Dict[str, Any], duration: float) -> List[float]:
    """从契约的命中/爆发节拍抽 apex 秒数（post_cue_points / keyframe_plan / impact_frame / collision_or_apex_frame）。

    高速动作的**命中帧必须落成一张真关键帧**，不能只靠均分锚帧——否则 impact_frame 只是声明字符串、
    韦尔德链里没有离散命中帧（脸/运镜/光/表情四轴无处撞点）。只抽含命中类关键词且带 `<秒>s` 的 cue。纯函数·可测。"""
    c = clip.get("template_contract") if isinstance(clip.get("template_contract"), dict) else {}
    if not c or not isinstance(duration, (int, float)) or duration <= 0:
        return []
    items: List[str] = []
    cues = c.get("post_cue_points")
    items += [str(x) for x in cues] if isinstance(cues, list) else ([str(cues)] if cues else [])
    for key in ("keyframe_plan", "impact_frame", "collision_or_apex_frame"):
        v = c.get(key)
        if isinstance(v, str):
            items.append(v)
        elif isinstance(v, dict):
            items += [str(x) for x in v.values()]
    secs = set()
    for it in items:
        s = str(it or "")
        if not _APEX_CUE_RE.search(s):
            continue
        m = _APEX_SEC_RE.search(s)
        if not m:
            continue
        try:
            sec = float(m.group(1))
        except ValueError:
            continue
        if 0.0 < sec < float(duration):
            secs.add(round(sec, 2))
    return sorted(secs)


def plan_anchor_times(duration: float, boundaries: List[float],
                      target_seg: float, min_seg: float,
                      snap_tolerance: float = 1.5) -> List[float]:
    """规划锚点秒数：段数 = clamp(round(duration/target_seg), 2, floor(duration/min_seg))，
    理想均分点逐个吸附最近的分镜边界（容差内且不破 min_seg），保证严格递增、每段 ≥ min_seg。
    不满足两段（duration < 2×min_seg）返回 []。"""
    if not isinstance(duration, (int, float)) or duration < 2 * min_seg:
        return []
    n_max = int(duration // min_seg)
    n = max(2, round(duration / target_seg))
    n = min(n, n_max)
    if n < 2:
        return []
    anchors: List[float] = []
    prev = 0.0
    for i in range(1, n):
        ideal = duration * i / n
        remaining = n - i  # 锚点之后还要容纳 remaining 段
        lo = prev + min_seg
        hi = duration - min_seg * remaining
        if lo > hi:
            break
        at = min(max(ideal, lo), hi)
        # 吸附最近分镜边界（自然换拍点）；吸不进 [lo,hi] 或超容差则用均分点
        best = None
        for edge in boundaries:
            if lo <= edge <= hi and abs(edge - ideal) <= snap_tolerance:
                if best is None or abs(edge - ideal) < abs(best - ideal):
                    best = edge
        if best is not None:
            at = best
        anchors.append(round(at, 2))
        prev = at
    return anchors


def clip_asset_stem(clip: Dict[str, Any], index: int) -> str:
    """Keep anchor filenames aligned with the storyboard's canonical Clip ID."""
    raw = str(clip.get("id") or clip.get("clip_id") or "").strip()
    safe = re.sub(r"[^\w.-]+", "_", raw, flags=re.UNICODE).strip("._")
    return safe or f"Clip_{index:02d}"


def anchor_png_name(clip: Dict[str, Any], ep: str, index: int, k: int) -> str:
    first = str(clip.get("firstframe_png") or "")
    if first.endswith(".png"):
        return f"{first[:-4]}_a{k}.png"
    return f"出图/{ep}/图片/{clip_asset_stem(clip, index)}_a{k}.png"


def classify_clip(clip: Dict[str, Any], *, min_seg: float, long_shot_threshold: float,
                  drift_hits: int) -> Optional[str]:
    """返回命中的规则描述；不命中返回 None。"""
    duration = clip.get("duration")
    if not isinstance(duration, (int, float)) or duration < 2 * min_seg:
        return None
    beats = beats_count(clip)
    template = str(clip.get("template") or "")
    if template in HIGH_MOTION_TEMPLATES and beats >= 2:
        return f"R1 高运动模板 {template}（{duration}s/{beats}拍）"
    if high_motion_signal(clip):
        # P1a：文本/运镜高速动作 或 大表情峰值 → R1 级密锚帧（即便没标正式高运动模板）
        return f"R1 高运动信号（文本/运镜或大表情，{duration}s）"
    if drift_hits > 0:
        return f"R3 漂移实证（redraw×{drift_hits}，{duration}s）"
    if duration >= long_shot_threshold and beats >= 3:
        return f"R2 普通长镜（{duration}s/{beats}拍）"
    return None


def midframe_png_name(clip: Dict[str, Any], ep: str, index: int) -> str:
    first = str(clip.get("firstframe_png") or "")
    if first.endswith(".png"):
        return f"{first[:-4]}_mid.png"
    return f"出图/{ep}/图片/{clip_asset_stem(clip, index)}_mid.png"


def _duration_matches(value: Any, duration: Any) -> bool:
    try:
        return abs(float(value) - float(duration)) < 0.001
    except (TypeError, ValueError):
        return False


def _generated_anchor_reason(text: Any) -> bool:
    raw = str(text or "").strip()
    return raw.startswith("auto:") or raw.startswith("default:") or raw.startswith("edit_cut:")


def anchors_cover_boundaries(cont: Mapping[str, Any], boundaries: Sequence[float], tolerance: float = 0.35) -> bool:
    anchors = cont.get("anchors") if isinstance(cont, Mapping) else None
    if not isinstance(anchors, list):
        return False
    times: List[float] = []
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            continue
        try:
            times.append(float(anchor.get("at_sec")))
        except (TypeError, ValueError):
            continue
    return all(any(abs(value - boundary) <= tolerance for value in times) for boundary in boundaries)


def generated_anchor_contract_stale(cont: Dict[str, Any], duration: Any) -> bool:
    """Generated anchors should be refreshed when source duration changed or is absent.

    Hand-authored anchors remain protected by existing_anchor_contract_valid().
    """
    if not isinstance(cont, dict):
        return False
    anchors = cont.get("anchors")
    if isinstance(anchors, list) and anchors:
        generated = [a for a in anchors if isinstance(a, dict) and _generated_anchor_reason(a.get("reason"))]
        if not generated:
            return False
        return any(not _duration_matches(a.get("source_duration"), duration) for a in generated)
    mid = cont.get("midframe")
    if isinstance(mid, dict) and _generated_anchor_reason(mid.get("reason")):
        return not _duration_matches(mid.get("source_duration"), duration)
    return False


def middle_beat_hint(clip: Dict[str, Any]) -> str:
    """中段锚帧的内容提示 = 表演节拍中间拍（template_contract.beats 中位项）。"""
    tc = clip.get("template_contract")
    beats = tc.get("beats") if isinstance(tc, dict) else None
    if isinstance(beats, list) and beats:
        return str(beats[len(beats) // 2])
    return ""


def plan_episode(root: str, ep: str, *, min_seg: float = 4.0, target_seg: float = 5.0,
                 fight_target: float = 3.5, long_shot_threshold: float = 8.0,
                 snap_tolerance: float = 1.5, default_midframe: bool = False,
                 midframe_exempt_below: float = 3.0,
                 multiframe_seg_min: float = 1.5) -> Dict[str, Any]:
    # 两个"最短段"地板，别混：
    #   min_seg(4.0)           = relay 拆段地板——每段当独立 frames2video clip 时的下限；
    #                            用于 classify 触发门槛(2×=多长才值得加锚) + D0 的 use=split/qc 判定。
    #   multiframe_seg_min(1.5) = multiframe2video 段密度地板（CLI 实际下限 0.5s + 余量）——
    #                            R1/R2/R3 给后端排锚帧密度用它，让打斗/长镜真正出多锚(>3帧)，
    #                            不再被旧 relay 地板架空 fight_target=3.5。
    # ⚠️ 后端能力假设（记录在案，#8）：multiframe_seg_min=1.5 假设执行后端支持原生多关键帧
    #    （目前只接了即梦/Dreamina multiframe2video=Seedance，段下限 0.5s）。将来接可灵/Veo 等后端时，
    #    必须复核它们的多关键帧 API 段下限/最大帧数，按后端调 multiframe_seg_min（理想是按 _设置.md
    #    生视频渠道 的 capability profile 取，而非硬编码）。frames2video-only 后端应传 multiframe_seg_min=4.0。
    # 长镜盲区：≥8s 但 <3 拍且非打斗的镜不命中 R1/R2/R3；默认仍走 D0 拿 1 个 _mid
    # （3 帧图片契约）。视频后端若不能原生消费中帧，后续在 consumption_plan 里降为 QC/参考/改路由；
    # 不再因为 first-frame-only 或 ROI/速度选择而少产中帧图片。
    # 高动作/长镜多拍/漂移实证/R1-R3 不受 D0 开关影响。
    sb = load_json(storyboard_path(root, ep))
    if not isinstance(sb, dict) or not isinstance(sb.get("clips"), list):
        raise SystemExit(f"[err] 缺少或损坏：{storyboard_path(root, ep)}")
    events = load_events(root)
    planned, skipped, exempted = [], [], []
    for i, clip in enumerate(sb["clips"], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        cid = clip.get("id") or f"clip#{i}"
        duration = clip.get("duration")
        if not isinstance(duration, (int, float)):
            try:
                duration = float(duration)
            except (TypeError, ValueError):
                duration = clip.get("duration")
        if not isinstance(duration, (int, float)):
            continue
        drift = redraw_drift_hits(events, ep, i)
        rule = classify_clip(clip, min_seg=min_seg,
                             long_shot_threshold=long_shot_threshold, drift_hits=drift)
        shot_rows = clip.get("shots") if isinstance(clip.get("shots"), list) else []
        has_explicit_editorial_coverage = len(shot_rows) > 1 and any(
            isinstance(row, Mapping) and any(row.get(key) for key in ("lens", "camera", "shot_size"))
            for row in shot_rows
        )
        editorial_boundaries = parse_shot_boundaries(clip) if has_explicit_editorial_coverage else []
        has_mid = cont.get("midframe") is not None
        has_anchors = cont.get("anchors") is not None
        valid_existing = False
        generated_stale = False
        if has_mid or has_anchors:
            valid_existing = existing_anchor_contract_valid(cont, duration)
            generated_stale = generated_anchor_contract_stale(cont, duration)
            if valid_existing and has_anchors and not generated_stale and (
                not editorial_boundaries or anchors_cover_boundaries(cont, editorial_boundaries)
            ):
                skipped.append({"clip": cid, "why": "已手动声明 anchors，人工优先"})
                continue
            if valid_existing and has_anchors and generated_stale:
                skipped.append({"clip": cid, "why": "已有自动 anchors 但源时长已变或缺 source_duration，按当前 duration 重算"})
            if valid_existing and has_mid and not rule and not editorial_boundaries:
                skipped.append({"clip": cid, "why": "已手动声明 midframe，且未命中多锚规则，人工优先"})
                continue
            if valid_existing and has_mid and rule:
                skipped.append({"clip": cid, "why": f"已有单 midframe，但命中 {rule}，升级为 continuity.anchors[]"})
            else:
                skipped.append({"clip": cid, "why": "已有 midframe/anchors 但时间越界或不可解析，按当前 duration 重算"})
        take_policy = str(clip.get("take_policy") or cont.get("take_policy") or "").strip().lower()
        if editorial_boundaries and take_policy == "single_take_multishot" and (
            rule is None or rule.startswith("R2")
        ):
            # 单拍多镜：镜位切换由 multishot-native 后端在一次生成内部完成，不需要 edit_cut 边界图，
            # 也不新增付费视频段；后端能力复核与回落在出视频阶段执行。R2「普通长镜」的中段漂移
            # 前提是连续单拍，多镜后端在内部镜位切换处自带再锚定，故 R2 不否决该策略；
            # R1 高运动/大表情与 R3 漂移实证仍安全优先，保留锚帧链。
            skipped.append({
                "clip": cid,
                "why": "take_policy=single_take_multishot：内部镜位一次生成，不产 edit_cut 边界锚；R1 高运动/R3 漂移实证时才回到锚帧链",
            })
            continue
        if editorial_boundaries:
            anchors = [{
                "anchor_png": anchor_png_name(clip, ep, i, k),
                "at_sec": round(t, 2),
                "use": "edit_cut",
                "reason": "edit_cut: storyboard 镜位切换边界，作为前一 take 尾帧与后一 take 首帧",
                "source_duration": round(float(duration), 3),
            } for k, t in enumerate(editorial_boundaries, 1) if 0 < t < float(duration)]
            if anchors:
                planned.append({
                    "clip_index": i, "clip_id": cid, "duration": duration,
                    "rule": "E1 storyboard 多镜位硬切边界",
                    "anchors": anchors,
                    "added_cost": {"images": len(anchors), "video_segments": len(anchors)},
                })
                continue
        if rule:
            template = str(clip.get("template") or "")
            # R1（正式高运动模板）与 R1b（文本/运镜运动信号·大表情）都用更短 fight_target → 更密锚帧。
            seg = fight_target if (template in HIGH_MOTION_TEMPLATES or rule.startswith("R1")) else target_seg
            # R1/R2/R3 锚帧排给 multiframe2video（首选执行路径）→ 用 multiframe 段密度地板，
            # 让 10s 打斗出 2 锚(4帧)、15s 出 3 锚(5帧)，而非被 4s relay 地板卡成 1 锚。
            times = plan_anchor_times(float(duration), parse_shot_boundaries(clip),
                                      seg, multiframe_seg_min, snap_tolerance)
            # apex-aware：高速动作镜把契约声明的命中/爆发帧强制落成一张真关键帧（治 impact_frame 只是字符串、
            # 韦尔德链无离散命中帧）。命中帧 = 动作(hit-stop)/运镜(推镜震屏)/光(闪光轮廓)/表情(狰狞峰) 四轴撞点。
            apexes = apex_anchor_seconds(clip, float(duration))
            merged = list(times)
            for a in apexes:
                if not any(abs(a - t) <= 0.4 for t in merged):
                    merged.append(a)
            merged = sorted({round(x, 2) for x in merged})

            def _is_apex(t: float) -> bool:
                return any(abs(t - a) <= 0.4 for a in apexes)
            if merged:
                anchors = [{
                    "anchor_png": anchor_png_name(clip, ep, i, k),
                    "at_sec": t,
                    "use": "keyframe" if _is_apex(t) else "split",
                    "reason": ("apex: 命中/爆发帧（强制关键帧·动作/运镜/光/表情四轴撞点）"
                               if _is_apex(t) else f"auto: {rule}"),
                    "source_duration": round(float(duration), 3),
                } for k, t in enumerate(merged, 1)]
                planned.append({
                    "clip_index": i, "clip_id": cid, "duration": duration,
                    "rule": rule, "anchors": anchors,
                    "added_cost": {"images": len(anchors), "video_segments": len(anchors)},
                })
                continue
        if not default_midframe:
            continue
        # 显式 D0 opt-in：未命中规则的普通镜额外出一张 _mid
        if not isinstance(duration, (int, float)) or duration < midframe_exempt_below:
            exempted.append({
                "clip_index": i, "clip": cid, "duration": duration,
                "reason": f"显式 D0 opt-in 下极短镜 <{midframe_exempt_below}s，中帧与首尾几乎重合",
            })
            continue
        use = "split" if duration >= 2 * min_seg else "qc"
        ideal = duration / 2
        times = (plan_anchor_times(float(duration), parse_shot_boundaries(clip),
                                   ideal, min_seg, snap_tolerance) if use == "split" else [])
        at = times[0] if times else round(ideal, 2)
        hint = middle_beat_hint(clip)
        planned.append({
            "clip_index": i, "clip_id": cid, "duration": duration,
            "rule": f"D0 显式 opt-in 中锚（use={use}）",
            "anchors": [{
                "anchor_png": midframe_png_name(clip, ep, i),
                "at_sec": at,
                "use": use,
                "reason": f"default: explicit D0 midframe（use={use}" + (f"；中间拍：{hint}" if hint else "") + "）",
                "source_duration": round(float(duration), 3),
            }],
            "added_cost": {"images": 1, "video_segments": 1 if use == "split" else 0},
        })
    total_anchors = sum(len(p["anchors"]) for p in planned)
    added_segments = sum(p["added_cost"]["video_segments"] for p in planned)
    return {
        "schema_version": 1,
        "kind": "n2d_anchor_plan",
        "episode": ep,
        "params": {"min_segment": min_seg, "target_segment": target_seg,
                   "fight_target": fight_target,
                   "long_shot_threshold": long_shot_threshold,
                   "snap_tolerance": snap_tolerance,
                   "default_midframe": default_midframe,
                   "midframe_exempt_below": midframe_exempt_below},
        "planned": planned,
        "skipped": skipped,
        "exempted": exempted,
        "summary": {"clips_planned": len(planned), "total_anchors": total_anchors,
                    "added_images": total_anchors, "added_video_segments": added_segments,
                    "exempted_clips": len(exempted)},
    }


def _time_in_duration(value: Any, duration: Any) -> bool:
    if not isinstance(duration, (int, float)) or duration <= 0:
        return False
    try:
        t = float(value)
    except (TypeError, ValueError):
        return False
    return 0 < t < float(duration)


def existing_anchor_contract_valid(cont: Dict[str, Any], duration: Any) -> bool:
    """Existing manual anchor is valid only if its timing still fits current duration."""
    if not isinstance(cont, dict):
        return False
    mid = cont.get("midframe")
    if isinstance(mid, dict):
        for key in ("split_at_sec", "at_sec", "time_sec"):
            if key in mid:
                return _time_in_duration(mid.get(key), duration)
        return False
    anchors = cont.get("anchors")
    if isinstance(anchors, list) and anchors:
        for anchor in anchors:
            if not isinstance(anchor, dict) or not _time_in_duration(anchor.get("at_sec"), duration):
                return False
        return True
    return False


def write_back(root: str, ep: str, plan: Dict[str, Any]) -> int:
    """把 plan 注回 storyboard.json 的 continuity.anchors（原子写）；返回写入 Clip 数。
    default_midframe 是普通 D0 镜的显式 opt-in；R1/R2/R3 高风险规划始终生效。
    关闭时保留已有人工锚帧，但不再为普通镜新增 `_mid`。"""
    path = storyboard_path(root, ep)
    sb = load_json(path)
    if not isinstance(sb, dict):
        raise SystemExit(f"[err] 缺少或损坏：{path}")
    by_index = {p["clip_index"]: p for p in plan["planned"]}
    exempt_by_index = {e["clip_index"]: e for e in plan.get("exempted") or []}
    default_mode = bool((plan.get("params") or {}).get("default_midframe"))
    written = 0
    for i, clip in enumerate(sb.get("clips") or [], 1):
        if not isinstance(clip, dict):
            continue
        cont = clip.setdefault("continuity", {})
        has_existing = cont.get("midframe") is not None or cont.get("anchors") is not None
        p = by_index.get(i)
        valid_existing = existing_anchor_contract_valid(cont, clip.get("duration")) if has_existing else False
        generated_stale = generated_anchor_contract_stale(cont, clip.get("duration")) if has_existing else False
        if has_existing and valid_existing and cont.get("anchors") is not None and not generated_stale and not p:
            continue  # 写回前再护一次：有效手动 anchors 优先
        if has_existing and valid_existing and cont.get("midframe") is not None and not p:
            continue  # 普通镜有效手动 midframe 优先；命中多锚规则时 p 会覆盖
        preserved_anchors = []
        if p and valid_existing and str(p.get("rule") or "").startswith("E1") and isinstance(cont.get("anchors"), list):
            preserved_anchors = [dict(row) for row in cont["anchors"] if isinstance(row, dict)]
        if has_existing:
            cont.pop("midframe", None)
            cont.pop("anchors", None)
        if p:
            merged = preserved_anchors + [dict(row) for row in p["anchors"]]
            deduped: List[Dict[str, Any]] = []
            for row in sorted(merged, key=lambda value: float(value.get("at_sec") or 0)):
                try:
                    at = float(row.get("at_sec"))
                except (TypeError, ValueError):
                    continue
                if any(abs(float(existing.get("at_sec") or 0) - at) <= 0.35 for existing in deduped):
                    continue
                deduped.append(row)
            cont["anchors"] = deduped
            written += 1
        elif default_mode and i in exempt_by_index and not cont.get("midframe_exempt_reason"):
            cont["midframe_exempt_reason"] = exempt_by_index[i]["reason"]
    if default_mode:
        sb.setdefault("policy", {})["midframe_default"] = True
        sb.setdefault("policy", {})["midframe_default_mode"] = "explicit_opt_in"
    else:
        sb.setdefault("policy", {})["midframe_default"] = False
        sb.setdefault("policy", {})["midframe_default_mode"] = "risk_only"
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return written


def render_md(plan: Dict[str, Any]) -> str:
    lines = [f"# 中段锚帧规划 — {plan['episode']}", ""]
    s = plan["summary"]
    backend = plan.get("backend_selection") if isinstance(plan.get("backend_selection"), dict) else {}
    consumption = backend.get("anchor_consumption_plan") if isinstance(backend.get("anchor_consumption_plan"), dict) else {}
    if backend:
        lines.append(
            f"- **视频后端消费计划**：backend={backend.get('backend') or '未固定'}；"
            f"channel={backend.get('channel') or '未固定'}；"
            f"execution={consumption.get('execution_backend') or 'unknown'}；"
            f"mode={consumption.get('consumption_mode') or 'unknown'}；"
            f"action={consumption.get('action') or 'manual confirmation required'}"
        )
    lines.append(f"- 命中 Clip：{s['clips_planned']} 个；新增锚帧 {s['total_anchors']} 张")
    lines.append(
        f"- **成本增量**：多出图 **{s['added_images']} 张**（便宜）。视频成本看执行后端："
        f"连续动作可用 native multiframe 保持 1 次调用，或用 split relay 变 K+1 段；"
        f"E1 编辑切点本来就是独立 take，不得为省调用合回一条。当前新增物理边界/分段计数 {s['added_video_segments']}。")
    lines.append("- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧")
    lines.append("")
    for p in plan["planned"]:
        # 显示时刻即可；runner 会严格排除 use=qc/reference，避免验收图改变执行时间轴。
        anchors = "、".join(
            f"{a['at_sec']}s→{os.path.basename(a['anchor_png'])}" for a in p["anchors"])
        lines.append(f"## {p['clip_id']}（{p['duration']}s）— {p['rule']}")
        lines.append(f"- 锚点：{anchors}")
        lines.append("")
    if plan.get("exempted"):
        lines.append("## 显式 D0 中锚豁免（极短镜）")
        for item in plan["exempted"]:
            lines.append(f"- {item['clip']}（{item['duration']}s）：{item['reason']}")
        lines.append("")
    if plan["skipped"]:
        lines.append("## 跳过")
        for item in plan["skipped"]:
            lines.append(f"- {item['clip']}：{item['why']}")
    return "\n".join(lines) + "\n"


def resolve_default_midframe(force_on: bool, force_off: bool, setting_value: Optional[str],
                             backend_capable: Optional[bool] = None) -> bool:
    """普通镜 D0 中段锚帧 opt-in 解析。

    R1/R2/R3 高风险锚帧不走这个开关，始终按规则规划。这里仅决定未命中高风险规则的普通镜
    是否补 `_mid`。普通镜只有用户开启且后端可在一次请求中原生消费 3+ 时间轴帧时才补；
    首尾帧后端的 split relay 不算原生三帧能力。

    优先级：
      1. CLI --default-midframe → True；--no-default-midframe → False（dev/临时覆盖）。
      2. 其余按 `setting_value=开启` 且 `backend_capable=True`。
    纯函数·可测。"""
    if force_on:
        return True
    if force_off:
        return False
    return str(setting_value or "").strip() == "开启" and bool(backend_capable)


def video_backend_selection(root: str) -> Dict[str, Any]:
    backend = (
        get_setting(root, "生视频模型", "")
        or get_setting(root, "生视频AI", "")
        or ""
    )
    channel = get_setting(root, "生视频渠道", "") or ""
    capable = backend_supports_three_plus_frames(backend or None, channel or None)
    consumption = anchor_consumption_plan(backend or None, channel or None, anchor_count=1, need_end=True)
    return {
        "backend": backend,
        "channel": channel,
        "supports_three_plus_frames": bool(capable),
        "anchor_consumption_plan": consumption,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="中段锚帧自动规划器")
    ap.add_argument("project_root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true", help="把规划注回 storyboard.json（默认只出报告）")
    ap.add_argument("--default-midframe", action="store_true",
                    help="强制开启普通镜 D0 中锚（覆盖选择点）：仅用于显式试验/迁移，极短镜豁免")
    ap.add_argument("--no-default-midframe", action="store_true",
                    help="强制关闭普通镜 D0 中锚（覆盖选择点），仍保留 E1/R1/R2/R3 必需锚")
    ap.add_argument("--min-segment", type=float, default=4.0,
                    help="relay 拆段地板(独立 frames2video 段下限)；管 R1/R3 触发门槛与 D0 use 判定")
    ap.add_argument("--multiframe-min-segment", type=float, default=1.5,
                    help="multiframe2video 段密度地板(CLI 下限 0.5s+余量)；管 R1/R2/R3 锚帧密度——打斗/长镜出多锚")
    ap.add_argument("--target-segment", type=float, default=5.0)
    ap.add_argument("--fight-target", type=float, default=3.5)
    ap.add_argument("--long-shot-threshold", type=float, default=8.0)
    ap.add_argument("--snap-tolerance", type=float, default=1.5)
    ap.add_argument("--midframe-exempt-below", type=float, default=3.0)
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    # 风险分层：R1/R2/R3 强制多锚；普通镜 D0 仅显式 opt-in 且后端原生支持时补 `_mid`。
    backend_selection = video_backend_selection(root)
    backend_capable = bool(backend_selection["supports_three_plus_frames"])
    default_mid = resolve_default_midframe(
        args.default_midframe, args.no_default_midframe,
        get_setting(root, "中段锚帧默认", "关闭"), backend_capable)
    plan = plan_episode(root, args.episode, min_seg=args.min_segment,
                        target_seg=args.target_segment, fight_target=args.fight_target,
                        long_shot_threshold=args.long_shot_threshold,
                        snap_tolerance=args.snap_tolerance,
                        default_midframe=default_mid,
                        midframe_exempt_below=args.midframe_exempt_below,
                        multiframe_seg_min=args.multiframe_min_segment)
    plan["backend_selection"] = backend_selection
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"anchor_plan_{args.episode}.json")
    md_path = os.path.join(out_dir, f"anchor_plan_{args.episode}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_md(plan))
    print(f"[ok] 锚帧规划 → {json_path}")
    print(f"[ok] 人读报告 → {md_path}")
    s = plan["summary"]
    print(f"     命中 {s['clips_planned']} Clip / 新增锚帧 {s['total_anchors']} 张"
          f"（多 {s['added_images']} 张出图；连续动作由后端选择 native multiframe/split relay，"
          f"明确镜位切换保留独立 take；边界/分段计数 {s['added_video_segments']}）")
    if args.write:
        n = write_back(root, args.episode, plan)
        print(f"[ok] 已注回 storyboard.json：{n} 个 Clip 的 continuity.anchors")
    elif plan["planned"]:
        print("     （dry-run：确认成本后加 --write 注回 storyboard.json）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
