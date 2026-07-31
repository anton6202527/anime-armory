#!/usr/bin/env python3
"""SyncNet 桥接：成片/视频 → 逐 Clip 口型↔配音偏移 → 生产数据/syncnet_raw_<集>.json。

这是 Gap A（音画同步 AV1）的「重活执行端」。`lipsync_consistency.py` 是消费端（读偏移→定档），
本脚本是生产端：跑 SyncNet 真实测出 AV offset，写成 `lipsync_consistency` 认的外部偏移报告。

为什么分两个脚本：SyncNet 需 torch + s3fd + 模型权重，是 out-of-repo 重活（同 CLAUDE.md 的
~/CosyVoice 等），只能在装好的 conda 环境跑；而消费端纯数学要能进 gate/CI 无依赖跑。分开后
消费端永远轻量可测，重活按需在 syncnet 环境跑完喂回 JSON。

依赖（必须在装好的环境跑，本机 = syncnet conda env）：
  torch + cv2 + scipy + numpy + scenedetect + python_speech_features + ffmpeg + SyncNet 仓库&权重。
  仓库默认 ~/syncnet_python（可 env SYNCNET_HOME / --syncnet-home 覆盖），权重 data/syncnet_v2.model
  + detectors/s3fd/weights/sfd_face.pth（download_model.sh 下）。

输入视频：口型↔配音偏移只在**音画已合到一起**的视频上有意义（per-clip 出视频是静音的）。
  默认取 合成/<集>/成片_*.mp4；可 --video 显式指定（如某条已混音的 clip）。

流程：run_pipeline.py（场景切+人脸追踪+裁脸轨）→ SyncNetInstance.evaluate 逐轨出 (offset帧, 置信) →
  按轨起始时间映射到 storyboard 的 Clip（累计时长定位）→ 每 Clip 取最高置信轨 → 写 JSON。

用法（务必在 syncnet 环境）：
  conda run -n syncnet python lipsync_measure.py <作品根> 第N集 [--video PATH]
                              [--syncnet-home ~/syncnet_python] [--fps 25] [--keep-work] [--json]
退出码：0 成功写报告 / 2 环境或输入缺失（不臆造，给安装提示）。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import pickle
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_FPS = 25.0  # SyncNet 标准工作帧率（run_pipeline 会把视频重采到 25fps）


def _syncnet_home(arg: Optional[str]) -> str:
    return os.path.expanduser(
        arg or os.environ.get("SYNCNET_HOME") or "~/syncnet_python")


def _check_env(home: str) -> List[str]:
    """返回缺失项清单（空=就绪）。不抛异常，给可读安装提示。"""
    missing: List[str] = []
    if not os.path.isdir(home):
        missing.append(f"SyncNet 仓库目录 {home}（git clone joonson/syncnet_python）")
        return missing
    if not os.path.isfile(os.path.join(home, "data", "syncnet_v2.model")):
        missing.append("data/syncnet_v2.model（跑仓库 download_model.sh）")
    if not os.path.isfile(os.path.join(home, "detectors", "s3fd", "weights", "sfd_face.pth")):
        missing.append("detectors/s3fd/weights/sfd_face.pth（download_model.sh）")
    for mod in ("torch", "cv2", "scipy", "scenedetect", "python_speech_features"):
        try:
            __import__(mod)
        except Exception:
            missing.append(f"python 包 {mod}（在 syncnet 环境 pip/conda 装）")
    return missing


def _resolve_video(root: str, ep: str, explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    # 默认成片（已混音）。合成线产物在 合成/<集>/成片_*.mp4。
    for pat in (
        os.path.join(root, "合成", ep, "成片_*.mp4"),
        os.path.join(root, "合成", ep, "*成片*.mp4"),
    ):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    return None


def _clip_durations(root: str, ep: str) -> List[Tuple[str, float]]:
    """从 storyboard.json 取 [(clip_label, duration_sec), ...]（顺序）。读不到→空。"""
    path = os.path.join(root, "脚本", ep, "storyboard.json")
    try:
        sb = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    out: List[Tuple[str, float]] = []
    for i, c in enumerate(sb.get("clips", []) if isinstance(sb, dict) else [], 1):
        if not isinstance(c, dict):
            continue
        label = str(c.get("id") or c.get("label") or f"Clip_{i:02d}")
        try:
            dur = float(c.get("duration") or 0)
        except Exception:
            dur = 0.0
        out.append((label, dur))
    return out


def clip_at(durations: List[Tuple[str, float]], at_sec: float) -> Optional[str]:
    """累计时长定位：at_sec 落在哪个 Clip 区间。纯函数·可测。durations 空或越界→None。"""
    if not durations:
        return None
    acc = 0.0
    for label, dur in durations:
        if dur <= 0:
            continue
        if at_sec < acc + dur:
            return label
        acc += dur
    return durations[-1][0] if durations else None


def fold_best_by_clip(rows: List[dict]) -> List[dict]:
    """同一 Clip 多条人脸轨 → 取最高置信那条（最可靠）。纯函数·可测。"""
    best: Dict[str, dict] = {}
    for r in rows:
        key = str(r.get("clip"))
        if key not in best or float(r.get("confidence", 0)) > float(best[key].get("confidence", 0)):
            best[key] = r
    # 按 at_sec 排序输出
    return sorted(best.values(), key=lambda r: float(r.get("at_sec", 0)))


def _run_pipeline(home: str, video: str, ref: str, data_dir: str) -> None:
    subprocess.run(
        [sys.executable, "run_pipeline.py", "--videofile", video,
         "--reference", ref, "--data_dir", data_dir],
        cwd=home, check=True,
    )


def _evaluate_tracks(home: str, ref: str, data_dir: str, fps: float) -> List[dict]:
    """逐裁脸轨跑 SyncNetInstance.evaluate → [{track, at_sec, offset_frames, confidence}]。"""
    if home not in sys.path:
        sys.path.insert(0, home)
    from SyncNetInstance import SyncNetInstance  # type: ignore

    tracks_pkl = os.path.join(data_dir, "pywork", ref, "tracks.pckl")
    tracks = pickle.load(open(tracks_pkl, "rb")) if os.path.isfile(tracks_pkl) else []
    crops = sorted(glob.glob(os.path.join(data_dir, "pycrop", ref, "0*.avi")))

    inst = SyncNetInstance()
    inst.loadParameters(os.path.join(home, "data", "syncnet_v2.model"))

    rows: List[dict] = []
    tmp_dir = os.path.join(data_dir, "pytmp")
    for idx, crop in enumerate(crops):
        start_frame = 0
        if idx < len(tracks):
            fr = tracks[idx].get("track", {}).get("frame")
            if fr is not None and len(fr):
                start_frame = int(fr[0])
        opt = SimpleNamespace(tmp_dir=tmp_dir, reference=f"{ref}_t{idx:03d}",
                              batch_size=20, vshift=15)
        offset, conf, _ = inst.evaluate(opt, videofile=crop)
        rows.append({
            "track": idx,
            "at_sec": round(start_frame / fps, 2),
            "offset_frames": int(offset),
            "confidence": round(float(conf), 3),
        })
    return rows


def measure(root: str, ep: str, video: Optional[str] = None, home: Optional[str] = None,
            fps: float = DEFAULT_FPS, keep_work: bool = False) -> dict:
    home = _syncnet_home(home)
    res: dict = {"ok": False, "fps": fps, "clips": [], "notes": [], "source_video": None}

    missing = _check_env(home)
    if missing:
        res["notes"].append("SyncNet 环境未就绪，缺：" + "；".join(missing)
                             + "。务必在 syncnet 环境跑：conda run -n syncnet python lipsync_measure.py ...")
        return res

    vid = _resolve_video(root, ep, video)
    if not vid:
        res["notes"].append(
            f"找不到可测视频：默认取 合成/{ep}/成片_*.mp4（须已混音）；或 --video 指定。"
            "per-clip 出视频是静音的，口型↔配音偏移测不了。")
        return res
    res["source_video"] = vid

    work_parent = tempfile.mkdtemp(prefix="n2d_syncnet_")
    data_dir = os.path.join(work_parent, "work")
    ref = "n2d"
    try:
        _run_pipeline(home, vid, ref, data_dir)
        track_rows = _evaluate_tracks(home, ref, data_dir, fps)
    except subprocess.CalledProcessError as exc:
        res["notes"].append(f"SyncNet pipeline 失败（exit {exc.returncode}）：{exc}")
        return res
    except Exception as exc:
        res["notes"].append(f"SyncNet 评估失败：{type(exc).__name__}: {exc}")
        return res
    finally:
        if not keep_work:
            import shutil
            shutil.rmtree(work_parent, ignore_errors=True)

    durations = _clip_durations(root, ep)
    for r in track_rows:
        r["clip"] = clip_at(durations, r["at_sec"]) or f"t{r['at_sec']:.0f}s"
    res["clips"] = fold_best_by_clip(track_rows)
    res["ok"] = True
    if not durations:
        res["notes"].append("无 storyboard 时长 → 人脸轨按起始秒标 tNNs，未映射到具体 Clip。")
    res["notes"].append(f"测得 {len(track_rows)} 条人脸轨 → {len(res['clips'])} 个 Clip 偏移。")
    return res


def write_report(root: str, ep: str, res: dict) -> str:
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"syncnet_raw_{ep}.json")
    payload = {
        "kind": "n2d_syncnet_raw",
        "fps": res.get("fps", DEFAULT_FPS),
        "source_video": res.get("source_video"),
        "generated_by": "n2d-review/scripts/lipsync_measure.py",
        "clips": [
            {"clip": c["clip"], "offset_frames": c["offset_frames"],
             "confidence": c["confidence"], "at_sec": c.get("at_sec")}
            for c in res.get("clips", [])
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--video", default=None, help="显式指定已混音视频；默认取 合成/<集>/成片_*.mp4")
    ap.add_argument("--syncnet-home", default=None, help="SyncNet 仓库目录（默认 env SYNCNET_HOME 或 ~/syncnet_python）")
    ap.add_argument("--fps", type=float, default=DEFAULT_FPS)
    ap.add_argument("--keep-work", action="store_true", help="保留临时 pipeline 工作目录（调试）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = measure(ns.root.rstrip("/"), ns.episode, ns.video, ns.syncnet_home, ns.fps, ns.keep_work)
    if res["ok"] and os.path.isdir(ns.root):
        path = write_report(ns.root.rstrip("/"), ns.episode, res)
        res["report"] = path
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0 if res["ok"] else 2
    print(f"=== SyncNet 桥接·口型↔配音偏移实测：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["ok"]:
        return 2
    print(f"源视频：{res['source_video']}")
    for c in res["clips"]:
        print(f"  {c['clip']} @{c.get('at_sec')}s: offset={c['offset_frames']}帧 conf={c['confidence']}")
    print(f"\n已写 {res.get('report')}（lipsync_consistency 会自动消费 → 音画同步 AV1 实测档）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
