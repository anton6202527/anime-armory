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
锚点放置：优先吸附 shots[] 的分镜边界（自然换拍点，焊点不切在动作进行中），
吸不上才均分；每段 ≥ min_segment（默认 4s，对齐 video_runner.submit_duration 下限）。

默认 dry-run：只写 生产数据/anchor_plan_第N集.json/.md（含成本增量：多 K 张出图 +
视频从 1 段变 K+1 段），给人确认。--write 才把 continuity.anchors 注回
storyboard.json；已手动声明 midframe/anchors 的 Clip 一律跳过（人工优先）。

--default-midframe（三帧契约铁律·选择点「中段锚帧默认」=开启时用）：
未命中 R1/R2/R3 的普通镜也默认规划一张中段锚帧（命名=首帧名+`_mid`，内容=表演节拍
中间拍），按时长分级用法 `use`：
  · split（duration ≥ 2×min_segment）——拆两段 frames2video 接力（真锚定）
  · qc（更短镜）——不拆段；中帧作出视频验收的中段一致性基准 + 后端多参考输入
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
from typing import Any, Dict, List, Optional

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
try:
    from n2d_settings import get_setting  # 读「中段锚帧默认」选择点（全局默认=开启）
except Exception:  # 退化：settings 不可用时按全局默认（开启）走，不阻断规划
    def get_setting(root, key, default=None):  # type: ignore
        return default
try:
    from n2d_platform_profiles import backend_supports_three_plus_frames
except Exception:  # 退化：能力档不可用时按"支持"（向前看·强制三帧）走
    def backend_supports_three_plus_frames(backend, channel=None):  # type: ignore
        return True
try:
    from n2d_const import HIGH_MOTION_TEMPLATES  # 单一真值源（gate 帧能力闸门共用同一份）
except Exception:  # 退化：常量不可用时本地兜底，保持与 n2d_const 同步
    HIGH_MOTION_TEMPLATES = frozenset({
        "fight_exchange", "chase", "magic_burst", "flight",
        "hug_or_pull", "intimate_interaction",
    })
DRIFT_REASON_RE = re.compile(r"漂|drift|中段|动作崩|路径", re.I)
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


def anchor_png_name(clip: Dict[str, Any], ep: str, index: int, k: int) -> str:
    first = str(clip.get("firstframe_png") or "")
    if first.endswith(".png"):
        return f"{first[:-4]}_a{k}.png"
    return f"出图/{ep}/图片/Clip_{index:02d}_a{k}.png"


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
    if drift_hits > 0:
        return f"R3 漂移实证（redraw×{drift_hits}，{duration}s）"
    if duration >= long_shot_threshold and beats >= 3:
        return f"R2 普通长镜（{duration}s/{beats}拍）"
    return None


def midframe_png_name(clip: Dict[str, Any], ep: str, index: int) -> str:
    first = str(clip.get("firstframe_png") or "")
    if first.endswith(".png"):
        return f"{first[:-4]}_mid.png"
    return f"出图/{ep}/图片/Clip_{index:02d}_mid.png"


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
    # 长镜盲区（#5·已被三帧契约默认覆盖）：≥8s 但 <3 拍且非打斗的镜不命中 R1/R2/R3；当
    #    `中段锚帧默认=开启`（现为全局默认）时这类镜走 D0 仍稳拿 1 个 _mid（3 帧），盲区闭合；
    #    只有显式 `关闭` 三帧契约时才回到"长简单镜只 2 帧"，那是 opt-in 用户的自觉选择。
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
        if cont.get("midframe") is not None or cont.get("anchors") is not None:
            skipped.append({"clip": cid, "why": "已手动声明 midframe/anchors，人工优先"})
            continue
        duration = clip.get("duration")
        drift = redraw_drift_hits(events, ep, i)
        rule = classify_clip(clip, min_seg=min_seg,
                             long_shot_threshold=long_shot_threshold, drift_hits=drift)
        if rule:
            template = str(clip.get("template") or "")
            seg = fight_target if template in HIGH_MOTION_TEMPLATES else target_seg
            # R1/R2/R3 锚帧排给 multiframe2video（首选执行路径）→ 用 multiframe 段密度地板，
            # 让 10s 打斗出 2 锚(4帧)、15s 出 3 锚(5帧)，而非被 4s relay 地板卡成 1 锚。
            times = plan_anchor_times(float(duration), parse_shot_boundaries(clip),
                                      seg, multiframe_seg_min, snap_tolerance)
            if times:
                anchors = [{
                    "anchor_png": anchor_png_name(clip, ep, i, k),
                    "at_sec": t,
                    "use": "split",
                    "reason": f"auto: {rule}",
                } for k, t in enumerate(times, 1)]
                planned.append({
                    "clip_index": i, "clip_id": cid, "duration": duration,
                    "rule": rule, "anchors": anchors,
                    "added_cost": {"images": len(anchors), "video_segments": len(anchors)},
                })
                continue
        if not default_midframe:
            continue
        # 三帧契约默认中锚：未命中规则的普通镜也出一张 _mid
        if not isinstance(duration, (int, float)) or duration < midframe_exempt_below:
            exempted.append({
                "clip_index": i, "clip": cid, "duration": duration,
                "reason": f"极短镜 <{midframe_exempt_below}s，中帧与首尾几乎重合（三帧契约豁免）",
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
            "rule": f"D0 三帧契约默认中锚（use={use}）",
            "anchors": [{
                "anchor_png": midframe_png_name(clip, ep, i),
                "at_sec": at,
                "use": use,
                "reason": f"default: 三帧契约（use={use}" + (f"；中间拍：{hint}" if hint else "") + "）",
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


def write_back(root: str, ep: str, plan: Dict[str, Any]) -> int:
    """把 plan 注回 storyboard.json 的 continuity.anchors（原子写）；返回写入 Clip 数。
    default_midframe 模式下同时写 policy.midframe_default=true 和豁免镜的
    continuity.midframe_exempt_reason（gate 据此强制三帧契约）；关闭模式写
    policy.midframe_default=false 作为逃生舱（gate 默认铁律据此跳过本剧的三帧强制）。"""
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
        if cont.get("midframe") is not None or cont.get("anchors") is not None:
            continue  # 写回前再护一次：人工声明优先
        p = by_index.get(i)
        if p:
            cont["anchors"] = p["anchors"]
            written += 1
        elif default_mode and i in exempt_by_index and not cont.get("midframe_exempt_reason"):
            cont["midframe_exempt_reason"] = exempt_by_index[i]["reason"]
    if default_mode:
        sb.setdefault("policy", {})["midframe_default"] = True
    else:
        # 三帧契约默认铁律下，gate 缺 policy=按强制；选择点「中段锚帧默认=关闭」是逃生舱，
        # 必须把 false 显式写进 storyboard，否则只规划了 R1/R2/R3 锚的镜外其余镜会被 gate 拦。
        sb.setdefault("policy", {})["midframe_default"] = False
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(sb, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return written


def render_md(plan: Dict[str, Any]) -> str:
    lines = [f"# 中段锚帧规划 — {plan['episode']}", ""]
    s = plan["summary"]
    lines.append(f"- 命中 Clip：{s['clips_planned']} 个；新增锚帧 {s['total_anchors']} 张")
    lines.append(
        f"- **成本增量**：多出图 **{s['added_images']} 张**（便宜）。视频成本看执行后端："
        f"**multiframe2video（即梦，首选）= 仍 1 次调用/Clip，不翻倍**；"
        f"仅 frames2video-only 后端才退化为 K+1 段（共 {s['added_video_segments']} 段）。")
    lines.append("- 确认后用 `--write` 注回 storyboard.json，再走 n2d-image 出 `_aK`/`_mid` 锚帧")
    lines.append("")
    for p in plan["planned"]:
        # 不显示 use 字段：multiframe2video 执行器对所有锚帧一视同仁（段只需 ≥0.5s），
        # use=split/qc 仅是 frames2video-only 兜底的 advisory，显示出来反而误导"qc 不进时间轴"。
        anchors = "、".join(
            f"{a['at_sec']}s→{os.path.basename(a['anchor_png'])}" for a in p["anchors"])
        lines.append(f"## {p['clip_id']}（{p['duration']}s）— {p['rule']}")
        lines.append(f"- 锚点：{anchors}")
        lines.append("")
    if plan.get("exempted"):
        lines.append("## 三帧契约豁免（极短镜）")
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
    """三帧契约默认开关解析（能力门控铁律）。优先级：
      1. CLI --default-midframe → True；--no-default-midframe → False（dev/临时覆盖）。
      2. 路由后端支持 ≥3 帧（backend_capable=True）→ True：能力门控铁律，不因 cost/风格关闭，
         覆盖项目设置「中段锚帧默认=关闭」。
      3. 否则（后端不支持 ≥3 帧 / 未传能力）→ 按 `_设置.md` 值，缺省=开启。
    纯函数·可测。"""
    if force_on:
        return True
    if force_off:
        return False
    if backend_capable:
        return True
    return "关闭" not in str("开启" if setting_value is None else setting_value)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="中段锚帧自动规划器")
    ap.add_argument("project_root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true", help="把规划注回 storyboard.json（默认只出报告）")
    ap.add_argument("--default-midframe", action="store_true",
                    help="强制开启三帧契约（覆盖选择点）：普通镜也规划中段锚帧，极短镜豁免")
    ap.add_argument("--no-default-midframe", action="store_true",
                    help="强制关闭三帧契约（覆盖选择点），回到只对 R1/R2/R3 命中镜加锚的 opt-in")
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
    # 三帧契约能力门控：路由视频后端支持 ≥3 帧时强制开（覆盖设置关闭，不因 cost）；CLI 标志最高优先。
    backend_capable = backend_supports_three_plus_frames(get_setting(root, "生视频AI", "") or None)
    default_mid = resolve_default_midframe(
        args.default_midframe, args.no_default_midframe,
        get_setting(root, "中段锚帧默认", "开启"), backend_capable)
    plan = plan_episode(root, args.episode, min_seg=args.min_segment,
                        target_seg=args.target_segment, fight_target=args.fight_target,
                        long_shot_threshold=args.long_shot_threshold,
                        snap_tolerance=args.snap_tolerance,
                        default_midframe=default_mid,
                        midframe_exempt_below=args.midframe_exempt_below,
                        multiframe_seg_min=args.multiframe_min_segment)
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
          f"（多 {s['added_images']} 张出图；视频走 multiframe2video 仍 1 次/Clip 不翻倍，"
          f"仅 frames2video-only 后端才 +{s['added_video_segments']} 段）")
    if args.write:
        n = write_back(root, args.episode, plan)
        print(f"[ok] 已注回 storyboard.json：{n} 个 Clip 的 continuity.anchors")
    elif plan["planned"]:
        print("     （dry-run：确认成本后加 --write 注回 storyboard.json）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
