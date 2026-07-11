#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# mv-beat：librosa 检测 BPM/beats/downbeats/energy/sections → 节拍/beatgrid.json（卡点网格）。
# 用法: beat_detect.py <制MV作品根> [--meter 4]
# 依赖: pip install librosa soundfile  （Mac 友好，纯 CPU 可跑）
import sys, os, json, argparse, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "mv_utils.py")


def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv_utils = load_mv_utils()


def load_meta(root):
    path = os.path.join(root, "_meta.json")
    if not os.path.exists(path):
        return {}
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


def declared_sections(meta, duration):
    rows = meta.get("section_timings") if isinstance(meta, dict) else None
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            start, end = float(row["start"]), float(row["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if 0 <= start < end <= duration + 0.1:
            out.append({"section": str(row.get("section") or row.get("name") or "section"),
                        "start": round(start, 3), "end": round(end, 3), "source": "meta_section_timings"})
    return sorted(out, key=lambda row: row["start"])


def estimate_bar_phase(beat_frames, onset_env, meter, forced=None):
    if not len(beat_frames):
        return 0, 0.0, []
    scores = []
    for phase in range(meter):
        frames = beat_frames[phase::meter]
        scores.append(float(sum(float(onset_env[min(int(frame), len(onset_env) - 1)]) for frame in frames)))
    phase = int(forced) if forced is not None else max(range(meter), key=lambda idx: scores[idx])
    ordered = sorted(scores, reverse=True)
    confidence = 1.0 if len(ordered) == 1 else max(0.0, min(1.0, (ordered[0] - ordered[1]) / (ordered[0] or 1.0)))
    return phase, round(confidence, 4), [round(x, 4) for x in scores]


def tempo_candidates(bpm):
    rows = [{"bpm": round(bpm, 2), "label": "detected"}]
    if bpm < 100:
        rows.append({"bpm": round(bpm * 2, 2), "label": "double_time_candidate"})
    if bpm > 100:
        rows.append({"bpm": round(bpm / 2, 2), "label": "half_time_candidate"})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", help="创作区/制MV/<曲名>/ 作品根")
    ap.add_argument("--meter", type=int, default=4, help="每小节拍数（4/4 默认 4）")
    ap.add_argument("--downbeat-phase", type=int, help="人工指定 beat 序列中第几拍为小节首，0-based")
    ap.add_argument("--confirm-timing", action="store_true", help="确认拍号、小节相位和 section_timings 已人工复核")
    args = ap.parse_args()

    song = mv_utils.find_song(args.root)
    if not song:
        meta = load_meta(args.root)
        if meta.get("song_timing") == "后配歌曲":
            sys.exit(f"找不到 {args.root}/歌/song.*（后配歌曲路线需先补入最终成品歌）")
        sys.exit(f"找不到 {args.root}/歌/song.*（先放入成品歌）")

    try:
        import librosa
    except ImportError:
        sys.exit("缺依赖：pip install librosa soundfile")

    y, sr = librosa.load(song, mono=True)
    dur = float(librosa.get_duration(y=y, sr=sr))
    _harmonic, percussive = librosa.effects.hpss(y)
    onset_env = librosa.onset.onset_strength(y=percussive, sr=sr)
    tempo, beat_frames = librosa.beat.beat_track(y=percussive, sr=sr, onset_envelope=onset_env)
    bpm = float(tempo if not hasattr(tempo, "__len__") else tempo[0])
    beats = [round(float(t), 3) for t in librosa.frames_to_time(beat_frames, sr=sr)]
    if args.downbeat_phase is not None and not 0 <= args.downbeat_phase < args.meter:
        sys.exit(f"--downbeat-phase 必须在 0..{args.meter - 1}")
    phase, phase_confidence, phase_scores = estimate_bar_phase(
        beat_frames, onset_env, args.meter, args.downbeat_phase)
    downbeats = beats[phase::args.meter] if beats else []
    local_tempo = librosa.feature.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
    tempo_curve = []
    curve_times = librosa.frames_to_time(range(len(local_tempo)), sr=sr)
    curve_step = max(1, int(round(sr / 512)))
    for i in range(0, len(local_tempo), curve_step):
        tempo_curve.append({"time": round(float(curve_times[i]), 3), "bpm": round(float(local_tempo[i]), 2)})
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
        "downbeats": downbeats,
        "downbeat_method": "manual_phase" if args.downbeat_phase is not None else "onset_phase_estimate",
        "downbeat_phase": phase,
        "downbeat_phase_confidence": phase_confidence,
        "downbeat_phase_scores": phase_scores,
        "tempo_curve": tempo_curve,
        "energy_map": energy_map,        # 粗能量曲线：mv-plan / 人工校正用
        "sections": declared_sections(meta, dur),
        "section_source": "meta_section_timings" if declared_sections(meta, dur) else "unconfirmed",
        "timing_verified": bool(args.confirm_timing and (args.downbeat_phase is not None or phase_confidence >= 0.15)),
        "note": "downbeats 默认仅为 onset 相位估算，不等于人工确认的小节首；正式规划前确认拍号/相位/段落边界。",
    }
    out = os.path.join(out_dir, "beatgrid.json")
    json.dump(grid, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    mv_utils.update_meta_flags(args.root)
    # 只盖 beat 阶段；song_ingest（歌曲入库/定稿）由 song/用户上传线拥有，
    # 卡点检测对占位/真歌都会跑，不能据此判定"歌曲已正式入库"（否则后配歌曲模式状态机失真）。
    mv_utils.update_progress_stage(args.root, "beat")
    print(f"[ok] BPM={grid['bpm']} 拍数={len(beats)} 小节首={len(downbeats)} 时长={grid['duration']}s → {out}")
    next_script = "mv-script 复核 rough 蓝图" if meta.get("song_timing") == "后配歌曲" else "mv-script 创作视觉蓝图"
    print(f"[next] {next_script} → mv-plan 正式时间线 → mv-image → mv-video → mv-lyric-sync → mv-compose")


if __name__ == "__main__":
    main()
