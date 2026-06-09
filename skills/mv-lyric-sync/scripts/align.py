#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# mv-lyric-sync：whisperx 把【已知歌词】强制对齐到 歌/song.wav → 词级时间戳
#   → 字幕/karaoke.ass(逐字\k高亮) + 字幕/lyrics.lrc(逐行)。mv 系列自包含。
# 用法: align.py <制MV作品根> [--lang zh] [--device cpu] [--audio <vocals.wav>]
# 依赖: pip install whisperx   （首次会下 wav2vec2 对齐模型；CPU 可跑，慢）
import sys, os, re, json, argparse


def _ts_lrc(t):
    m = int(t // 60); s = t - 60 * m
    return f"[{m:02d}:{s:05.2f}]"


def _ts_ass(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:d}:{m:02d}:{s:05.2f}"


def load_lyric_lines(path):
    lines = []
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#") or ln.startswith(">"): continue
        if re.fullmatch(r"\[[^\]]+\]", ln): continue          # 段落标签 [verse]
        ln = re.sub(r"（歌词…）|\(歌词…\)", "", ln).strip()
        if ln: lines.append(ln)
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--audio", default=None, help="可指定 demucs 分离后的人声文件，提升歌词对齐稳定性")
    args = ap.parse_args()

    song = args.audio if args.audio else next((os.path.join(args.root, "歌", f"song{e}")
                                               for e in (".wav", ".mp3", ".m4a", ".flac")
                                               if os.path.exists(os.path.join(args.root, "歌", f"song{e}"))), None)
    lyr = os.path.join(args.root, "词", "lyrics.md")
    if not song or not os.path.exists(song): sys.exit(f"缺 {args.root}/歌/song.* 或 --audio 指定文件不存在")
    if not os.path.exists(lyr): sys.exit(f"缺 {args.root}/词/lyrics.md")
    lines = load_lyric_lines(lyr)
    if not lines: sys.exit("lyrics.md 没有可对齐的歌词行（还没填词？）")

    try:
        import whisperx
    except ImportError:
        sys.exit("缺依赖：pip install whisperx")

    audio = whisperx.load_audio(song)
    dur = len(audio) / 16000.0
    full = " ".join(lines)
    # 强制对齐【已知歌词】（不转写，直接拿 lyrics 当 transcript 对到音频）
    model_a, meta = whisperx.load_align_model(language_code=args.lang, device=args.device)
    seg = [{"start": 0.0, "end": dur, "text": full}]
    res = whisperx.align(seg, model_a, meta, audio, args.device, return_char_alignments=False)
    words = res.get("word_segments") or [w for s in res["segments"] for w in s.get("words", [])]
    words = [w for w in words if w.get("start") is not None and w.get("end") is not None]
    if not words: sys.exit("对齐失败：无词级时间戳（试 --device cpu，或检查歌词与音频是否匹配）")

    # 把对齐到的词按原始行切回（按每行字符数顺序消费）
    out_dir = os.path.join(args.root, "字幕"); os.makedirs(out_dir, exist_ok=True)
    wi = 0
    ass_events, lrc_lines, report_lines = [], [], []
    for line in lines:
        n = len(line.replace(" ", "")) or 1
        wl = words[wi:wi + n]; wi += n
        if not wl: break
        start, end = wl[0]["start"], wl[-1]["end"]
        # .ass 逐字 \k（厘秒）
        ktext = "".join(f"{{\\k{max(1,int(round((w['end']-w['start'])*100)))}}}{w['word']}" for w in wl)
        ass_events.append(f"Dialogue: 0,{_ts_ass(start)},{_ts_ass(end)},Default,,0,0,0,,{ktext}")
        lrc_lines.append(f"{_ts_lrc(start)}{line}")
        report_lines.append({
            "line": line,
            "start": round(float(start), 3),
            "end": round(float(end), 3),
            "word_count": len(wl),
            "duration": round(float(end - start), 3),
        })

    ass = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
           "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
           "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           "Style: Default,PingFang SC,54,&H00FFFFFF,&H0000C8FF,&H00000000,&H64000000,"
           "-1,0,0,0,100,100,0,0,1,3,1,2,40,40,80,1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
           + "\n".join(ass_events) + "\n")
    open(os.path.join(out_dir, "karaoke.ass"), "w", encoding="utf-8").write(ass)
    open(os.path.join(out_dir, "lyrics.lrc"), "w", encoding="utf-8").write("\n".join(lrc_lines) + "\n")
    report = {
        "schema_version": 1,
        "kind": "mv_lyric_alignment_report",
        "audio": os.path.relpath(song, args.root),
        "language": args.lang,
        "device": args.device,
        "audio_duration": round(float(dur), 3),
        "lyric_lines": len(lines),
        "aligned_lines": len(report_lines),
        "word_segments": len(words),
        "consumed_word_segments": wi,
        "unused_word_segments": max(0, len(words) - wi),
        "coverage_seconds": round(float(report_lines[-1]["end"] - report_lines[0]["start"]), 3) if report_lines else 0,
        "lines": report_lines,
        "warnings": [],
    }
    if len(report_lines) != len(lines):
        report["warnings"].append("aligned_lines != lyric_lines，可能有歌词未对齐")
    if len(words) - wi > max(3, 0.2 * len(words)):
        report["warnings"].append("未消费词级片段偏多，可能实唱/歌词不一致或切行策略需人工校正")
    open(os.path.join(out_dir, "alignment_report.json"), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"[ok] 对齐 {len(lines)} 行 / {wi} 词 → 字幕/karaoke.ass + lyrics.lrc")
    if report["warnings"]:
        print("[warn] " + "；".join(report["warnings"]))
    print("[next] mv-compose 合成（有 libass 烧 .ass 逐字高亮，无则自带 render_lyrics.py 用 .lrc）")


if __name__ == "__main__":
    main()
