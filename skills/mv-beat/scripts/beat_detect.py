#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# mv-beat：librosa 检测 BPM/beats/downbeats → 节拍/beatgrid.json（卡点网格）。
# 用法: beat_detect.py <制MV作品根> [--meter 4]
# 依赖: pip install librosa soundfile  （Mac 友好，纯 CPU 可跑）
import sys, os, json, argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="制MV/<曲名>/ 作品根")
    ap.add_argument("--meter", type=int, default=4, help="每小节拍数（4/4 默认 4）")
    args = ap.parse_args()

    song = None
    for ext in (".wav", ".mp3", ".m4a", ".flac"):
        p = os.path.join(args.root, "歌", f"song{ext}")
        if os.path.exists(p): song = p; break
    if not song:
        sys.exit(f"找不到 {args.root}/歌/song.*（先放入成品歌）")

    try:
        import librosa
    except ImportError:
        sys.exit("缺依赖：pip install librosa soundfile")

    y, sr = librosa.load(song, mono=True)
    dur = float(librosa.get_duration(y=y, sr=sr))
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(tempo if not hasattr(tempo, "__len__") else tempo[0])
    beats = [round(float(t), 3) for t in librosa.frames_to_time(beat_frames, sr=sr)]
    # downbeat 近似：每 meter 拍取一个（4/4 → 每 4 拍一个小节首）
    downbeats = beats[::args.meter] if beats else []

    out_dir = os.path.join(args.root, "节拍"); os.makedirs(out_dir, exist_ok=True)
    grid = {
        "song": os.path.relpath(song, args.root),
        "duration": round(dur, 3),
        "bpm": round(bpm, 2),
        "meter": args.meter,
        "beats": beats,                 # 每拍时间戳（秒）
        "downbeats": downbeats,         # 小节首（卡大点用）
        "sections": [],                 # 段落[verse/chorus...]+起始秒；由 mv-lyric-sync 或人工填
        "note": "副歌踩 downbeats 切；verse 缓。爽点对齐某个 downbeat。mv-video 出 clip 时长按相邻卡点定。",
    }
    out = os.path.join(out_dir, "beatgrid.json")
    json.dump(grid, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[ok] BPM={grid['bpm']} 拍数={len(beats)} 小节首={len(downbeats)} 时长={grid['duration']}s → {out}")
    print("[next] mv-image 按段落出图；mv-video 出 clip 时长对齐 downbeats；mv-compose 卡点合成")


if __name__ == "__main__":
    main()
