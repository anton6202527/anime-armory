#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# mv-beat：librosa 检测 BPM/beats/downbeats/energy/sections → 节拍/beatgrid.json（卡点网格）。
# 用法: beat_detect.py <制MV作品根> [--meter 4]
# 依赖: pip install librosa soundfile  （Mac 友好，纯 CPU 可跑）
import sys, os, json, argparse


def load_meta(root):
    path = os.path.join(root, "_meta.json")
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def default_sections(meta, duration):
    structure = meta.get("structure") if isinstance(meta, dict) else None
    if not isinstance(structure, list) or not structure or not duration:
        return []
    step = duration / len(structure)
    rows = []
    for i, name in enumerate(structure):
        rows.append({
            "section": str(name),
            "start": round(i * step, 3),
            "end": round((i + 1) * step if i + 1 < len(structure) else duration, 3),
            "source": "meta_even_split",
        })
    return rows


def tempo_candidates(bpm):
    rows = [{"bpm": round(bpm, 2), "label": "detected"}]
    if bpm < 100:
        rows.append({"bpm": round(bpm * 2, 2), "label": "double_time_candidate"})
    if bpm > 100:
        rows.append({"bpm": round(bpm / 2, 2), "label": "half_time_candidate"})
    return rows


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
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env)
    bpm = float(tempo if not hasattr(tempo, "__len__") else tempo[0])
    beats = [round(float(t), 3) for t in librosa.frames_to_time(beat_frames, sr=sr)]
    # downbeat 近似：每 meter 拍取一个（4/4 → 每 4 拍一个小节首）
    downbeats = beats[::args.meter] if beats else []
    rms = librosa.feature.rms(y=y)[0]
    rms_times = librosa.frames_to_time(range(len(rms)), sr=sr)
    onset_times = librosa.frames_to_time(range(len(onset_env)), sr=sr)
    energy_map = []
    step = max(1, int(round(sr / 512)))  # roughly 1s at default hop length
    for i in range(0, len(rms), step):
        onset_i = min(i, len(onset_env) - 1)
        energy_map.append({
            "time": round(float(rms_times[i]), 3),
            "rms": round(float(rms[i]), 6),
            "onset": round(float(onset_env[onset_i]), 6) if len(onset_env) else 0.0,
        })

    out_dir = os.path.join(args.root, "节拍"); os.makedirs(out_dir, exist_ok=True)
    meta = load_meta(args.root)
    grid = {
        "song": os.path.relpath(song, args.root),
        "duration": round(dur, 3),
        "bpm": round(bpm, 2),
        "tempo_candidates": tempo_candidates(bpm),
        "meter": args.meter,
        "beats": beats,                 # 每拍时间戳（秒）
        "downbeats": downbeats,         # 小节首（卡大点用）
        "energy_map": energy_map,        # 粗能量曲线：mv-plan / 人工校正用
        "sections": default_sections(meta, dur),  # 初始段落；人工校正后可覆盖
        "section_source": "meta_even_split" if meta.get("structure") else "empty",
        "note": "副歌踩 downbeats 切；verse 缓。tempo_candidates 用于半/倍速人工校正；energy_map 用于段落/高潮校正。",
    }
    out = os.path.join(out_dir, "beatgrid.json")
    json.dump(grid, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[ok] BPM={grid['bpm']} 拍数={len(beats)} 小节首={len(downbeats)} 时长={grid['duration']}s → {out}")
    print("[next] mv-image 按段落出图；mv-video 出 clip 时长对齐 downbeats；mv-compose 卡点合成")


if __name__ == "__main__":
    main()
