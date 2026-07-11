#!/usr/bin/env python3
"""Render a reviewable still animatic against the locked master song."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

import mv_utils


ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}


def render(root, output=None):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("缺 ffmpeg，无法渲染真实 animatic")
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    plan = mv_utils.load_json(plan_path, {}) or {}
    song = mv_utils.find_song(root)
    if not song:
        raise RuntimeError("缺 歌/song.*")
    clips = plan.get("clips") or []
    missing = [c.get("image_path") for c in clips if not c.get("image_path") or not os.path.exists(os.path.join(root, c.get("image_path", "")))]
    if missing:
        raise RuntimeError(f"缺 {len(missing)} 张 animatic 首帧，例：{missing[0]}")
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    aspect = meta.get("aspect") or mv_utils.parse_settings(root).get("合成画幅") or "16:9"
    width, height = ASPECTS.get(aspect, ASPECTS["16:9"])
    output = output or os.path.join(root, "分镜", "animatic.mp4")
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mv-animatic-") as temp:
        concat_path = os.path.join(temp, "concat.txt")
        parts = []
        for index, clip in enumerate(clips):
            duration = float(clip.get("duration") or 0)
            part = os.path.join(temp, f"part-{index:04d}.mp4")
            command = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", os.path.join(root, clip["image_path"]),
                       "-t", f"{duration:.3f}", "-vf",
                       f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,fps=24,format=yuv420p",
                       "-an", "-c:v", "libx264", "-crf", "18", part]
            subprocess.run(command, check=True)
            parts.append(part)
        with open(concat_path, "w", encoding="utf-8") as handle:
            for part in parts:
                handle.write(f"file '{part}'\n")
        silent = os.path.join(temp, "silent.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", concat_path, "-c", "copy", silent], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", silent, "-i", song, "-map", "0:v", "-map", "1:a",
                        "-shortest", "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-b:a", "256k", "-movflags", "+faststart", output], check=True)
    report = {
        "schema_version": 1, "kind": "mv_animatic_render", "generated_at": date.today().isoformat(),
        "output": mv_utils.relpath(root, output), "aspect": aspect,
        "inputs_sha256": {"分镜/clip_plan.json": mv_utils.content_hash(plan_path),
                          mv_utils.relpath(root, song): mv_utils.content_hash(song),
                          **{c["image_path"]: mv_utils.content_hash(os.path.join(root, c["image_path"])) for c in clips}},
    }
    mv_utils.write_json(os.path.join(root, "生产数据", "animatic", "animatic.json"), report)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    args = parser.parse_args()
    try:
        output = render(os.path.abspath(args.project_root))
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 1
    print(f"[ok] animatic → {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
