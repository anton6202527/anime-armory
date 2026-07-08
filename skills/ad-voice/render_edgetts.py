#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate external per-line VO wavs with edge-tts for ad-voice registration.

This is a non-clone synthetic TTS adapter. It writes line_01.wav..line_NN.wav
to an output directory, then render_voice.py registers those files through
--from-dir so the manifest/timing schema remains single-sourced.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


def _load_local_module(name: str):
    path = Path(__file__).resolve().with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


voice_manifest = _load_local_module("voice_manifest")
render_voice = _load_local_module("render_voice")


def run(cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(cmd), capture_output=True, text=True)


def require_tools() -> None:
    missing = [name for name in ("uvx", "ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise RuntimeError("缺工具：" + ", ".join(missing))


def synth_line(text: str, voice: str, rate: str, out_wav: Path) -> float:
    tmp_mp3 = out_wav.with_suffix(".mp3")
    edge_cmd = [
        "uvx", "edge-tts",
        "--voice", voice,
        "--rate", rate,
        "--text", text,
        "--write-media", str(tmp_mp3),
    ]
    edge = run(edge_cmd)
    if edge.returncode != 0:
        raise RuntimeError(edge.stderr.strip() or edge.stdout.strip() or "edge-tts failed")
    ff = run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(tmp_mp3),
        "-ar", "44100", "-ac", "1",
        str(out_wav),
    ])
    if tmp_mp3.exists():
        tmp_mp3.unlink()
    if ff.returncode != 0:
        raise RuntimeError(ff.stderr.strip() or "ffmpeg convert failed")
    dur = render_voice.probe_duration(str(out_wav))
    if dur is None or dur <= 0.05:
        raise RuntimeError(f"生成音频无有效时长：{out_wav}")
    return float(dur)


def render(project_root: Path, out_dir: Path, voice: str, rate: str) -> dict:
    vo_txt = project_root / "脚本" / "voiceover.txt"
    if not vo_txt.is_file():
        raise FileNotFoundError(f"缺 {vo_txt}")
    lines = voice_manifest.parse_voiceover(vo_txt.read_text(encoding="utf-8"))
    if not lines:
        raise RuntimeError(f"{vo_txt} 没有可配音文本")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, (role, text) in enumerate(lines, 1):
        out_wav = out_dir / f"line_{idx:02d}.wav"
        dur = synth_line(text, voice, rate, out_wav)
        rows.append({
            "idx": idx,
            "role": role,
            "text": text,
            "line_wav": out_wav.name,
            "seconds": round(dur, 3),
        })
        print(f"[ok] {out_wav} {dur:.2f}s")
    payload = {
        "schema_version": 1,
        "kind": "ad_external_voice_lines",
        "provider": "edge-tts",
        "voice": voice,
        "rate": rate,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lines": rows,
    }
    (out_dir / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="edge-tts 生成广告逐句真实 VO WAV（供 render_voice --from-dir 登记）")
    ap.add_argument("project_root")
    ap.add_argument("--out-dir", default=None, help="默认 <作品根>/配音/edgetts_lines")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--rate", default="+0%")
    ns = ap.parse_args(argv)

    try:
        require_tools()
        root = Path(ns.project_root).resolve()
        out_dir = Path(ns.out_dir).resolve() if ns.out_dir else root / "配音" / "edgetts_lines"
        payload = render(root, out_dir, ns.voice, ns.rate)
    except Exception as exc:
        print(f"[block] {exc}", file=sys.stderr)
        return 2
    print(f"[ok] edge-tts 逐句 WAV: {out_dir} lines={len(payload['lines'])} voice={ns.voice}")
    print("     下一步：python3 skills/ad-voice/render_voice.py <作品根> --backend EdgeTTS --from-dir " + str(out_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
