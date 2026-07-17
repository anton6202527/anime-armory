#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告 animatic 预演——传统 PPM/制前会纪律的 AI 等价物（本线自包含）。

传统 TVC 在开机烧钱前必开 PPM（制前会）：客户/导演对着 storyboard + **animatic**
（配好 VO 的动态分镜预演）签核节奏与叙事，才允许进拍摄。AI 流水线里最贵的一步是
image2video 逐镜生成——本工具在这一步之前，用**已经存在的免费材料**拼出可看的预演：

    首帧 PNG（出图/分镜/图片/<clip>.png） × 实测镜头时长（脚本/镜头时长.json） + VO（配音/vo.wav）
    → 合成/animatic.mp4 + 生产数据/ad_animatic_manifest.json（输入 SHA + 时长对账）

看完 animatic 再去生视频：节奏塌/镜序错/VO 对不上，在这里改是免费的，生完视频再改是重烧。
manifest 供 gate 以 advisory 侧车并入（"审"不是"门"：animatic 好不好看归人判，工具只保证
可看、可追溯、时长诚实）。

用法：
    python3 animatic.py <作品根> [--out 合成/animatic.mp4] [--fps 24] [--no-audio]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

KIND = "ad_animatic_manifest"
MANIFEST_REL = os.path.join("生产数据", "ad_animatic_manifest.json")
DEFAULT_OUT_REL = os.path.join("合成", "animatic.mp4")
FRAME_DIR_REL = os.path.join("出图", "分镜", "图片")
DURATIONS_REL = os.path.join("脚本", "镜头时长.json")
VO_REL = os.path.join("配音", "vo.wav")
MIN_SHOT_SECONDS = 0.2
# VO 与画面总长对账容差：animatic 是节奏预演，超过这个差就不是"预演"而是"错觉"。
AV_MISMATCH_WARN = 1.0


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def shot_rows(root: Path) -> List[Dict[str, Any]]:
    """镜头时长.json（finalize_storyboard 实测产物）为时长单一真值源；缺则回退 storyboard。"""
    durations = load_json(root / DURATIONS_REL, {}) or {}
    rows = durations.get("shots") or durations.get("clips") or []
    if isinstance(rows, list) and rows:
        return [r for r in rows if isinstance(r, dict)]
    sb = load_json(root / "脚本" / "storyboard.json", {}) or {}
    return [r for r in (sb.get("shots") or sb.get("clips") or []) if isinstance(r, dict)]


def shot_id(row: Mapping[str, Any], idx: int) -> str:
    return str(row.get("clip_id") or row.get("shot_id") or row.get("id") or f"镜头{idx + 1:02d}")


def shot_seconds(row: Mapping[str, Any]) -> Optional[float]:
    for key in ("duration", "时长", "duration_sec", "seconds", "measured_seconds"):
        if row.get(key) is not None:
            try:
                value = float(row.get(key))
                return value if value > 0 else None
            except (TypeError, ValueError):
                return None
    return None


def frame_path(root: Path, sid: str) -> Path:
    return root / FRAME_DIR_REL / f"{sid}.png"


def build_plan(root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """逐镜 (帧, 时长) 计划 + findings。缺帧/缺时长是硬错误——预演不能拿空画面凑。"""
    rows = shot_rows(root)
    plan: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    if not rows:
        findings.append({"severity": "block", "code": "no_shots",
                         "msg": f"缺 {DURATIONS_REL}（或 storyboard）——没有镜头可预演；先跑 finalize_storyboard.py"})
        return plan, findings
    for idx, row in enumerate(rows):
        sid = shot_id(row, idx)
        secs = shot_seconds(row)
        frame = frame_path(root, sid)
        if secs is None:
            findings.append({"severity": "block", "code": "shot_duration_missing",
                             "msg": f"{sid} 无可解析时长——animatic 的意义就是节奏，时长不实测就没意义", "shot": sid})
            continue
        if not frame.is_file():
            findings.append({"severity": "block", "code": "first_frame_missing",
                             "msg": f"{sid} 缺首帧 {frame.relative_to(root)}——先出图再拼预演（传统流程里没画完分镜不开 PPM）",
                             "shot": sid})
            continue
        plan.append({"shot": sid, "frame": str(frame.relative_to(root)),
                     "seconds": max(MIN_SHOT_SECONDS, round(secs, 3)),
                     "sha256": sha256_file(frame)})
    return plan, findings


def concat_spec(root: Path, plan: Sequence[Mapping[str, Any]]) -> str:
    """ffmpeg concat demuxer 清单（每帧按实测时长停留；末帧补一行是 concat 语法要求）。"""
    lines = []
    for item in plan:
        path = (root / str(item["frame"])).resolve()
        lines.append(f"file '{path}'")
        lines.append(f"duration {item['seconds']}")
    if plan:
        lines.append(f"file '{(root / str(plan[-1]['frame'])).resolve()}'")
    return "\n".join(lines) + "\n"


def vo_duration(root: Path) -> Optional[float]:
    vo = root / VO_REL
    if not vo.is_file() or not shutil.which("ffprobe"):
        return None
    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(vo)],
        capture_output=True, text=True, check=False)
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def render(root: Path, plan: Sequence[Mapping[str, Any]], out_rel: str,
           fps: int, with_audio: bool) -> None:
    spec = concat_spec(root, plan)
    spec_path = root / "生产数据" / "animatic_concat.txt"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(spec, encoding="utf-8")
    out = root / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(spec_path)]
    vo = root / VO_REL
    use_audio = with_audio and vo.is_file()
    if use_audio:
        cmd += ["-i", str(vo)]
    cmd += ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=%d" % fps,
            "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast"]
    if use_audio:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += [str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0 or not out.is_file():
        raise RuntimeError(f"ffmpeg 拼 animatic 失败：{(proc.stderr or '').strip()[-400:]}")


def build_manifest(root: Path, plan: Sequence[Mapping[str, Any]],
                   findings: List[Dict[str, Any]], out_rel: str, rendered: bool) -> Dict[str, Any]:
    total = round(sum(float(item["seconds"]) for item in plan), 3)
    vo_secs = vo_duration(root)
    if rendered and vo_secs is not None and abs(vo_secs - total) > AV_MISMATCH_WARN:
        findings.append({"severity": "warn", "code": "animatic_av_mismatch",
                         "msg": f"画面总长 {total:.1f}s 与 VO {vo_secs:.1f}s 差 {abs(vo_secs - total):.1f}s"
                                f"（>{AV_MISMATCH_WARN:g}s）——预演节奏不诚实；回 finalize_storyboard 对齐"})
    vo = root / VO_REL
    return {
        "schema_version": 1, "kind": KIND, "project_root": str(root), "generated_at": now_iso(),
        "output": out_rel if rendered else None,
        "rendered": rendered,
        "shots": list(plan),
        "total_seconds": total,
        "vo": ({"path": VO_REL, "sha256": sha256_file(vo), "seconds": vo_secs} if vo.is_file() else None),
        "note": "传统 PPM 纪律：先对着 animatic 签核节奏/镜序/VO 贴合，再进付费 image2video；"
                "首帧或时长任何一处变更后本预演即过期，须重拼。",
        "summary": {"block": sum(1 for f in findings if f["severity"] == "block"),
                    "warn": sum(1 for f in findings if f["severity"] == "warn"),
                    "info": sum(1 for f in findings if f["severity"] == "info")},
        "findings": findings,
    }


def write_manifest(root: Path, manifest: Mapping[str, Any]) -> Path:
    path = root / MANIFEST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--out", default=DEFAULT_OUT_REL)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--no-audio", action="store_true", help="不合 VO（只看画面节奏）")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    plan, findings = build_plan(root)
    rendered = False
    if plan and not any(f["severity"] == "block" for f in findings):
        if not shutil.which("ffmpeg"):
            findings.append({"severity": "block", "code": "ffmpeg_missing",
                             "msg": "缺 ffmpeg——animatic 是视频预演，没有像素就没有预演，不做降级假装"})
        else:
            try:
                render(root, plan, ns.out, ns.fps, with_audio=not ns.no_audio)
                rendered = True
            except RuntimeError as exc:
                findings.append({"severity": "block", "code": "render_failed", "msg": str(exc)})
    manifest = build_manifest(root, plan, findings, ns.out, rendered)
    path = write_manifest(root, manifest)
    s = manifest["summary"]
    print(f"# animatic rendered={rendered} shots={len(plan)} total={manifest['total_seconds']}s "
          f"block={s['block']} warn={s['warn']}")
    for f in manifest["findings"]:
        icon = "⛔" if f["severity"] == "block" else ("⚠️" if f["severity"] == "warn" else "ℹ️")
        print(f"{icon} [{f['code']}] {f['msg']}")
    print(f"[ok] {path}")
    return 1 if s["block"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
