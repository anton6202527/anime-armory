#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拍广告 VO 配音：voiceover.txt → 逐句音频 + 整轨 vo.wav + 时长清单.json（实测时长驱动镜头）。

多后端可插拔；本脚本内置 **macOS say 占位** 与 **estimate 静音占位**（无凭证时也能把时长跑出来）。
真后端（CosyVoice / MiniMax / 火山 / 克隆）由各自 CLI 产 wav 后用 --from-dir 登记。

克隆真人嗓 = 合规硬闸门：需 VOICE_CLONE_AUTHORIZED=1，否则拒做（2026 opt-in）。

用法：
    python3 render_voice.py <作品根> --backend say        # macOS 占位
    python3 render_voice.py <作品根> --backend estimate    # 跨平台静音占位（按字数估时）
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import voice_manifest as vm

CLONE_BACKENDS = {"cosyvoice", "gpt-sovits", "minimax", "clone", "火山"}
CN_CHARS_PER_SEC = 4.5   # 中文播报约每秒 4–5 字，用于 estimate 占位估时


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def probe_duration(path):
    """ffprobe 读时长（秒）。失败返回 None。"""
    if not shutil.which("ffprobe"):
        return None
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def synth_say(text, out_wav, voice="Tingting"):
    """macOS say → aiff → wav。返回是否成功。"""
    if not shutil.which("say"):
        return False
    aiff = out_wav + ".aiff"
    if run(["say", "-v", voice, "-o", aiff, text]).returncode != 0:
        # 某些中文环境 say 中文会空音频；交给上层降级
        return False
    if not shutil.which("ffmpeg"):
        return False
    ok = run(["ffmpeg", "-y", "-i", aiff, "-ar", "44100", "-ac", "1", out_wav]).returncode == 0
    if os.path.exists(aiff):
        os.remove(aiff)
    return ok and os.path.exists(out_wav) and (probe_duration(out_wav) or 0) > 0.05


def synth_silence(out_wav, seconds):
    """生成指定秒数静音 wav（estimate 占位 / say 降级）。"""
    if not shutil.which("ffmpeg"):
        return False
    return run(["ffmpeg", "-y", "-f", "lavfi", "-t", f"{seconds:.3f}",
                "-i", "anullsrc=r=44100:cl=mono", out_wav]).returncode == 0


def est_seconds(text):
    return max(0.6, len(text.strip()) / CN_CHARS_PER_SEC)


def main():
    ap = argparse.ArgumentParser(description="拍广告 VO 配音 + 时长清单")
    ap.add_argument("project_root")
    ap.add_argument("--backend", default="say", help="say | estimate | <真后端名>")
    ap.add_argument("--gap", type=float, default=0.25, help="句间停顿秒")
    ap.add_argument("--placeholder-voice", default="Tingting")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    vo_txt = os.path.join(root, "脚本", "voiceover.txt")
    if not os.path.isfile(vo_txt):
        print(f"[err] 缺 {vo_txt}（先跑 ad-script 脚本 pass）", file=sys.stderr)
        sys.exit(2)

    backend = args.backend.strip().lower()
    if backend in CLONE_BACKENDS and os.environ.get("VOICE_CLONE_AUTHORIZED") != "1":
        print("[block] 克隆真人嗓需 VOICE_CLONE_AUTHORIZED=1（肖像/声音授权）。"
              "未授权拒做——可改用 --backend say 占位先把时长跑出来。", file=sys.stderr)
        sys.exit(3)

    voicemap = {}
    vmap_path = os.path.join(root, "设定库", "voicemap.json")
    if os.path.isfile(vmap_path):
        with open(vmap_path, encoding="utf-8") as f:
            voicemap = json.load(f)

    out_dir = os.path.join(root, "配音")
    os.makedirs(out_dir, exist_ok=True)
    with open(vo_txt, encoding="utf-8") as f:
        lines = vm.parse_voiceover(f.read())

    real_backend = backend not in ("say", "estimate")
    entries, wavs, cursor = [], [], 0.0
    for idx, (role, text) in enumerate(lines, 1):
        line_wav = os.path.join(out_dir, f"line_{idx:02d}.wav")
        placeholder = backend in ("say", "estimate")
        ok = False
        if backend == "say":
            ok = synth_say(text, line_wav, args.placeholder_voice)
        if not ok:  # estimate 后端 / say 降级
            placeholder = True
            ok = synth_silence(line_wav, est_seconds(text))
        dur = probe_duration(line_wav) or est_seconds(text)
        start, end = cursor, cursor + dur
        entries.append(vm.manifest_entry(
            idx, role, text, dur, start, end, args.gap, os.path.basename(line_wav),
            voicemap, real_backend, placeholder, args.placeholder_voice))
        wavs.append(line_wav)
        cursor = end + args.gap

    # 拼整轨 vo.wav（句间补静音 gap）
    vo_wav = os.path.join(out_dir, "vo.wav")
    if shutil.which("ffmpeg") and wavs:
        concat_list = os.path.join(out_dir, "_concat.txt")
        silence = os.path.join(out_dir, "_gap.wav")
        synth_silence(silence, args.gap)
        with open(concat_list, "w", encoding="utf-8") as f:
            for i, w in enumerate(wavs):
                f.write(f"file '{w}'\n")
                if i < len(wavs) - 1:
                    f.write(f"file '{silence}'\n")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", vo_wav])
        for tmp in (concat_list, silence):
            if os.path.exists(tmp):
                os.remove(tmp)

    manifest = {"schema_version": 1, "kind": "ad_voice_manifest",
                "backend": backend, "total_seconds": round(cursor, 3),
                "has_placeholder": any(e.get("占位") for e in entries), "lines": entries}
    with open(os.path.join(out_dir, "时长清单.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"[ok] 配音 {len(entries)} 句  总时长≈{cursor:.2f}s  后端={backend}"
          + ("  ⏳占位（正式定稿前需真配音复跑）" if manifest["has_placeholder"] else ""))
    print(f"     时长清单：{os.path.join(out_dir, '时长清单.json')}")


if __name__ == "__main__":
    main()
