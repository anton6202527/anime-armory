#!/usr/bin/env python3
"""动作镜成片 artifact 实测桥接（out-of-repo conda·光流方向/运动模糊/肢体畸变）。

与 lipsync_measure.py 同构：重模型只能在装好的 conda 环境跑（本机 = facefusion），消费端
（spectacle_video_qc.py）纯标准库无依赖。本脚本读每条高动态 Clip 的成片，按 sampling_plan
在动作峰值帧加密抽帧，量三个「之前流水线没有」的新维：
  · optical_flow_direction  成片实际运动/运镜方向 vs storyboard camera_path（Kling 笔刷方向≠prompt 必崩的机检版）
  · motion_blur_plausibility 该糊的高速段糊、不该糊的清楚
  · limb_artifact_score      肢体畸变/多手多脚（需 pose 检测器；缺则该维留空=unverified，绝不臆造）
写 生产数据/spectacle_motion_artifacts_第N集.json，spectacle_video_qc 自动并入动作 QC 核验。

依赖（在 facefusion 环境跑）：cv2(+numpy) 必需（光流/锐度）；mediapipe 可选（肢体/人数）。
  conda run -n facefusion python spectacle_motion_measure.py <作品根> 第N集 [--json]

纯逻辑函数（dominant_flow_direction / parse_camera_path_direction / flow_intent_match /
motion_blur_plausibility / limb_artifact / sample_frame_indices）无重依赖，可 pytest 直跑。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import (  # noqa: E402
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    high_flow_sampling_plan,
    infer_spectacle_type,
)

ACTION_KINDS = set(ACTION_CHOREOGRAPHY_SHOT_TYPES)
SPECTACLE_MOTION_ARTIFACTS_KIND = "n2d_spectacle_motion_artifacts"

# 运动近静止阈：平均光流幅度（像素/帧）低于此视为基本静止（运镜方向判 static）。
STATIC_FLOW_MAG = 0.6
# 锐度（Laplacian 方差）相对本镜中位数的「明显偏低」比例——低于中位数×此值算"糊"。
BLUR_LOW_RATIO = 0.5


# ──────────────────────────── 纯逻辑（pytest 覆盖·无 cv2/numpy） ────────────────────────────

def dominant_flow_direction(mean_dx: float, mean_dy: float, divergence: float,
                            magnitude: float, static_thresh: float = STATIC_FLOW_MAG) -> str:
    """从平均光流矢量 + 散度判主运动方向。纯函数·可测。

    magnitude<阈 → static；散度主导 → zoom_in(扩张)/zoom_out(收缩)；否则按 dx/dy 较大轴判
    left/right/up/down（图像坐标 y 向下，dy>0=画面内容下移=相机上移，这里只报内容运动方向）。
    """
    mag = float(magnitude)
    if mag < float(static_thresh):
        return "static"
    dx, dy, div = float(mean_dx), float(mean_dy), float(divergence)
    # 散度（径向膨胀）显著强于平移 → 推/拉镜。
    if abs(div) >= max(abs(dx), abs(dy)) and abs(div) > static_thresh:
        return "zoom_in" if div > 0 else "zoom_out"
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "down" if dy > 0 else "up"


# camera_path 文字 → 期望的内容运动方向标签集合（中英）。
_CAMERA_DIRECTION_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("zoom_in", ("推镜", "推进", "dolly in", "push in", "crash zoom", "zoom in", "拉近", "怼脸")),
    ("zoom_out", ("拉镜", "拉远", "dolly out", "pull out", "zoom out", "后拉")),
    ("left", ("左摇", "左移", "向左", "pan left", "left to right 反", "move left")),
    ("right", ("右摇", "右移", "向右", "pan right", "left to right", "move right", "left_to_right")),
    ("up", ("上摇", "上升", "升镜", "crane up", "tilt up", "ascend", "无人机升起", "仰")),
    ("down", ("下摇", "下降", "降镜", "crane down", "tilt down", "descend", "俯冲")),
)


def parse_camera_path_direction(text: str) -> List[str]:
    """从 camera_path/运镜文字解析期望的内容运动方向标签。纯函数·可测。无方向词→空。"""
    low = str(text or "").lower()
    out: List[str] = []
    for label, kws in _CAMERA_DIRECTION_KEYWORDS:
        if any(k.lower() in low for k in kws):
            if label not in out:
                out.append(label)
    return out


def flow_intent_match(flow_label: str, camera_path_text: str) -> Optional[bool]:
    """实测主运动方向是否落在 camera_path 声明的期望方向内。纯函数·可测。

    无声明方向 → None（无法判，不罚）；static 实测 vs 有方向声明 → False（声明动了但没动）。
    """
    expected = parse_camera_path_direction(camera_path_text)
    if not expected:
        return None
    if flow_label == "static":
        return False
    return flow_label in expected


def motion_blur_plausibility(samples: Sequence[Tuple[float, float]],
                             low_ratio: float = BLUR_LOW_RATIO) -> Optional[float]:
    """运动模糊合理性 0..1：该糊(高光流)的糊、不该糊(低光流)的清楚。纯函数·可测。

    samples=[(flow_mag, sharpness), ...]。以本镜锐度中位数为基线，把每帧分四象限，
    「低光流 + 锐度远低于中位」= 不该糊却糊（实锤崩坏）；其余视为合理。返回合理帧占比。
    样本<2 → None（证据不足，不臆造）。
    """
    rows = [(float(m), float(s)) for m, s in samples if s is not None]
    if len(rows) < 2:
        return None
    sharps = sorted(s for _, s in rows)
    mid = sharps[len(sharps) // 2] or 1.0
    flows = sorted(m for m, _ in rows)
    flow_mid = flows[len(flows) // 2]
    plausible = 0
    for mag, sharp in rows:
        low_flow = mag <= flow_mid
        blurry = sharp < mid * low_ratio
        # 唯一明确不合理：基本不动却很糊（静帧发虚 = 画质崩，不是运动模糊）。
        if low_flow and blurry:
            continue
        plausible += 1
    return round(plausible / len(rows), 4)


def limb_artifact(person_counts: Sequence[int], expected_persons: int) -> Optional[Dict[str, float]]:
    """肢体/人数异常代理：检出人数稳定超过应在场人数 → 多人/多肢畸变嫌疑。纯函数·可测。

    person_counts=每采样帧检出的人数（来自 pose/检测器）。expected_persons<=0 或无样本→None
    （没有检测器结果就不报，绝不臆造）。返回 {score:超额帧占比, extra:最大超额数}。
    """
    counts = [int(c) for c in person_counts if c is not None]
    if not counts or expected_persons <= 0:
        return None
    over = [c - expected_persons for c in counts if c > expected_persons]
    score = round(len(over) / len(counts), 4)
    return {"score": score, "extra": max(over) if over else 0}


def sample_frame_indices(total_frames: int, plan: Mapping[str, Any]) -> List[int]:
    """按 sampling_plan 选要抽的帧序号（均匀基底 + 首尾边界，升序去重）。纯函数·可测。

    峰值加密在光流主循环里按实测光流做（这里只给基底+边界，避免无依赖时也能算采样表）。
    """
    if total_frames <= 0:
        return []
    base = int(plan.get("base_uniform_frames") or 6) if isinstance(plan, Mapping) else 6
    base = max(2, min(base, total_frames))
    idxs = {0, total_frames - 1}
    if base > 1:
        step = (total_frames - 1) / (base - 1)
        for i in range(base):
            idxs.add(int(round(i * step)))
    return sorted(j for j in idxs if 0 <= j < total_frames)


# ──────────────────────────── 重模型编排（cv2/numpy·懒加载·优雅降级） ────────────────────────────

def _check_env() -> List[str]:
    missing: List[str] = []
    for mod in ("cv2", "numpy"):
        try:
            __import__(mod)
        except Exception:
            missing.append(f"python 包 {mod}（在 facefusion 环境装：必需，做光流/锐度）")
    return missing


def _pose_counter():
    """可选 mediapipe pose 检测器；不可用→None（肢体维留空=unverified，不臆造）。"""
    try:
        import mediapipe as mp  # type: ignore
    except Exception:
        return None
    pose_mod = getattr(getattr(mp, "solutions", None), "pose", None)
    if pose_mod is None:
        try:
            from mediapipe.python.solutions import pose as pose_mod  # type: ignore
        except Exception:
            return None
    try:
        return pose_mod.Pose(static_image_mode=True, model_complexity=1)
    except Exception:
        return None


def _story_clip_id(raw: object, fallback_idx: int) -> str:
    text = str(raw or "")
    match = re.search(r"CLIP[_\-\s]?0*([0-9]+)\b", text, re.IGNORECASE)
    if not match:
        match = re.search(r"Clip[_\-\s]?0*([0-9]+)\b", text, re.IGNORECASE)
    if not match:
        match = re.search(r"0*([0-9]+)", text)
    return f"Clip_{int(match.group(1)):02d}" if match else f"Clip_{fallback_idx:02d}"


def _clip_media(root: str, ep: str, clip_id: str) -> Optional[str]:
    match = re.search(r"Clip[_\-\s]?0*([0-9]+)", clip_id, re.IGNORECASE)
    if not match:
        return None
    digits = f"{int(match.group(1)):02d}"
    strict_patterns = (
        os.path.join(root, "出视频", ep, "视频", f"Clip_{digits}*.mp4"),
        os.path.join(root, "出视频", ep, "视频", f"Clip{digits}*.mp4"),
    )
    for pat in strict_patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    for pat in (
        os.path.join(root, "出视频", ep, "video", f"Clip_{digits}*.mp4"),
        os.path.join(root, "出视频", ep, "video", f"Clip{digits}*.mp4"),
        os.path.join(root, "出视频", ep, "*", f"Clip_{digits}*.mp4"),
        os.path.join(root, "出视频", ep, "*", f"Clip{digits}*.mp4"),
    ):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    return None


def _measure_clip(path: str, plan: Mapping[str, Any], camera_path: str,
                  expected_persons: int, pose) -> Dict[str, Any]:
    """读一条 clip → 光流方向/模糊合理性/(可选)肢体。重依赖在此，外层已 _check_env。"""
    import cv2  # type: ignore
    import numpy as np  # type: ignore

    cap = cv2.VideoCapture(path)
    frames: List[Any] = []
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    pick = set(sample_frame_indices(total, plan)) if total > 0 else None
    idx = 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if pick is None or idx in pick or idx % 3 == 0:  # total 未知时退化为每3帧
            frames.append(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY))
        idx += 1
    cap.release()
    if len(frames) < 2:
        return {"insufficient_frames": True}

    h, w = frames[0].shape[:2]
    cx, cy = w / 2.0, h / 2.0
    dxs: List[float] = []
    dys: List[float] = []
    divs: List[float] = []
    mags: List[float] = []
    samples: List[Tuple[float, float]] = []
    person_counts: List[int] = []
    prev = frames[0]
    for cur in frames[1:]:
        flow = cv2.calcOpticalFlowFarneback(prev, cur, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        fx, fy = flow[..., 0], flow[..., 1]
        mean_dx = float(np.mean(fx)); mean_dy = float(np.mean(fy))
        mag = float(np.mean(np.sqrt(fx * fx + fy * fy)))
        # 散度代理：径向分量平均（像素相对中心的外扩量）。
        ys, xs = np.mgrid[0:h, 0:w]
        rx = (xs - cx); ry = (ys - cy)
        norm = np.sqrt(rx * rx + ry * ry) + 1e-6
        div = float(np.mean((fx * rx + fy * ry) / norm))
        dxs.append(mean_dx); dys.append(mean_dy); divs.append(div); mags.append(mag)
        sharp = float(cv2.Laplacian(cur, cv2.CV_64F).var())
        samples.append((mag, sharp))
        prev = cur

    if pose is not None:
        try:
            import cv2 as _cv2  # noqa: F811
            for gray in frames:
                rgb = _cv2.cvtColor(gray, _cv2.COLOR_GRAY2RGB)
                res = pose.process(rgb)
                person_counts.append(1 if getattr(res, "pose_landmarks", None) else 0)
        except Exception:
            person_counts = []

    mean_mag = sum(mags) / len(mags) if mags else 0.0
    flow_label = dominant_flow_direction(
        sum(dxs) / len(dxs), sum(dys) / len(dys), sum(divs) / len(divs), mean_mag)
    match = flow_intent_match(flow_label, camera_path)
    out: Dict[str, Any] = {
        "optical_flow_direction": flow_label,
        "flow_magnitude": round(mean_mag, 3),
        "frames_sampled": len(frames),
    }
    if match is not None:
        out["flow_intent_match"] = match
        out["flow_direction_error"] = 0.0 if match else 1.0
    blur = motion_blur_plausibility(samples)
    if blur is not None:
        out["motion_blur_plausibility"] = blur
    limb = limb_artifact(person_counts, expected_persons) if person_counts else None
    if limb is not None:
        out["limb_artifact_score"] = limb["score"]
        out["extra_limbs"] = limb["extra"]
    return out


def measure(root: str, ep: str) -> Dict[str, Any]:
    res: Dict[str, Any] = {"ok": False, "checks": [], "notes": []}
    missing = _check_env()
    if missing:
        res["notes"].append("动作-artifact 环境未就绪，缺：" + "；".join(missing)
                             + "。在 facefusion 环境跑：conda run -n facefusion python spectacle_motion_measure.py ...")
        return res
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    try:
        sb = json.load(open(sb_path, encoding="utf-8"))
    except Exception:
        res["notes"].append(f"读不到 {sb_path}")
        return res
    clips = sb.get("clips") if isinstance(sb, dict) else None
    if not isinstance(clips, list):
        res["notes"].append("storyboard.json 缺 clips[]")
        return res

    import re as _re
    pose = _pose_counter()
    if pose is None:
        res["notes"].append(
            "当前环境未提供 mediapipe legacy Pose solutions API → 肢体畸变维留空(unverified)，"
            "只测光流方向/运动模糊；如需该维度，配置 legacy solutions 或接入 tasks pose 模型。"
        )
    measured = 0
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        kind = infer_spectacle_type(clip)
        if kind not in ACTION_KINDS:
            continue
        clip_id = _story_clip_id(clip.get("id") or clip.get("clip_id"), idx)
        media = _clip_media(root, ep, clip_id)
        if not media:
            res["checks"].append({"clip": clip_id, "spectacle_type": kind, "no_media": True})
            continue
        contract = clip.get("template_contract") if isinstance(clip.get("template_contract"), dict) else {}
        camera_path = str(contract.get("camera_path") or clip.get("camera_path") or "")
        expected = len(set(_re.findall(r"CHAR_[A-Za-z0-9_]+", json.dumps(clip, ensure_ascii=False))))
        plan = high_flow_sampling_plan(kind, clip.get("duration") or 0)
        try:
            row = _measure_clip(media, plan, camera_path, expected, pose)
        except Exception as exc:  # 单条失败不拖垮整集
            res["checks"].append({"clip": clip_id, "spectacle_type": kind,
                                  "error": f"{type(exc).__name__}: {exc}"})
            continue
        row.update({"clip": clip_id, "spectacle_type": kind,
                    "media": os.path.relpath(media, root)})
        res["checks"].append(row)
        measured += 1
    res["ok"] = measured > 0
    res["notes"].append(f"实测 {measured} 条高动态 Clip 的动作 artifact。")
    return res


def write_report(root: str, ep: str, res: Mapping[str, Any]) -> str:
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"spectacle_motion_artifacts_{ep}.json")
    payload = {
        "kind": SPECTACLE_MOTION_ARTIFACTS_KIND,
        "version": 1,
        "generated_by": "n2d-review/scripts/spectacle_motion_measure.py",
        "episode": ep,
        "checks": list(res.get("checks", [])),
        "notes": list(res.get("notes", [])),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="measure spectacle motion artifacts (optical flow / blur / limb)")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(list(argv) if argv is not None else None)
    ep = ns.episode if ns.episode.startswith("第") else f"第{ns.episode}集"
    res = measure(ns.root.rstrip("/"), ep)
    if res["ok"] and os.path.isdir(ns.root):
        res["report"] = write_report(ns.root.rstrip("/"), ep, res)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["ok"] else 2
    print(f"=== 动作 artifact 实测（光流方向/运动模糊/肢体）：{ns.root} {ep} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    for c in res.get("checks", []):
        print(f"  {c.get('clip')}: {json.dumps({k: v for k, v in c.items() if k not in ('clip','spectacle_type')}, ensure_ascii=False)}")
    if res["ok"]:
        print(f"\n已写 {res.get('report')}（spectacle_video_qc 自动并入动作 QC 核验）")
    return 0 if res["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
