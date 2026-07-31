#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# mv-lyric-sync：whisperx 把【已知歌词】强制对齐到 歌/song.* → 词级时间戳
#   → 字幕/karaoke.ass(逐字\k高亮) + 字幕/lyrics.lrc(逐行)。mv 系列自包含。
# 用法: align.py <制MV作品根> [--lang zh] [--device cpu] [--audio <vocals.wav>]
# 依赖: pip install whisperx   （首次会下 wav2vec2 对齐模型；CPU 可跑，慢）
import sys, os, re, json, argparse, difflib
import importlib.util
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "mv_utils.py")
GATE_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "gate.py")

def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def load_gate():
    spec = importlib.util.spec_from_file_location("mv_gate", GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

mv_utils = load_mv_utils()
mv_gate = load_gate()

def load_lyric_lines(path):
    lines = []
    for ln in open(path, encoding="utf-8"):
        ln = ln.strip()
        if not ln or ln.startswith("#") or ln.startswith(">"): continue
        if re.fullmatch(r"\[[^\]]+\]", ln): continue          # 段落标签 [verse]
        ln = re.sub(r"（歌词…）|\(歌词…\)", "", ln).strip()
        if ln: lines.append(ln)
    return lines


def alignable_char(value):
    return bool(value and (value.isalnum() or "\u3400" <= value <= "\u9fff"))


def flatten_aligned_chars(result):
    rows = []
    for segment in result.get("segments") or []:
        for row in segment.get("chars") or []:
            char = str(row.get("char") or "")
            if alignable_char(char) and row.get("start") is not None and row.get("end") is not None:
                rows.append({"char": char, "start": float(row["start"]), "end": float(row["end"])})
    return rows


def map_chars_to_lines(lines, aligned_chars):
    source = [(line_index, char) for line_index, line in enumerate(lines) for char in line if alignable_char(char)]
    source_text = "".join(char.lower() for _line, char in source)
    observed_text = "".join(row["char"].lower() for row in aligned_chars)
    matcher = difflib.SequenceMatcher(a=source_text, b=observed_text, autojunk=False)
    source_to_observed = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            source_to_observed[block.a + offset] = block.b + offset
    per_line = [[] for _ in lines]
    matched_per_line = [0 for _ in lines]
    for source_index, (line_index, _char) in enumerate(source):
        observed_index = source_to_observed.get(source_index)
        if observed_index is not None:
            per_line[line_index].append(aligned_chars[observed_index])
            matched_per_line[line_index] += 1
    total = len(source)
    return per_line, matched_per_line, total, len(source_to_observed) / total if total else 0.0


def aspect_geometry(root):
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    settings = mv_utils.parse_settings(root)
    aspect = meta.get("aspect") or settings.get("合成画幅") or "16:9"
    return {"9:16": (1080, 1920), "1:1": (1080, 1080)}.get(aspect, (1920, 1080))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--audio", default=None, help="可指定 demucs 分离后的人声文件，提升歌词对齐稳定性")
    ap.add_argument("--allow-low-confidence", action="store_true", help="仅用于人工复核流程：低置信度也落档并推进阶段")
    ap.add_argument("--reviewer", help="配合 --allow-low-confidence，记录逐行听审人")
    ap.add_argument("--notes", default="", help="低置信度人工校正/接受说明")
    args = ap.parse_args()
    if args.allow_low_confidence and not str(args.reviewer or "").strip():
        sys.exit("--allow-low-confidence 必须同时提供 --reviewer；低覆盖不能匿名放行")
    if args.allow_low_confidence and not str(args.notes or "").strip():
        sys.exit("--allow-low-confidence 必须同时提供 --notes，说明逐行听审/校正依据")

    song = args.audio
    if not song:
        vocals_path = os.path.join(args.root, "歌", "_demucs", "vocals.wav")
        if os.path.exists(vocals_path):
            song = vocals_path
            print(f"[info] 自动检测到 demucs 人声轨：{vocals_path}，将使用其进行对齐提升精度。")
        else:
            song = mv_utils.find_song(args.root)
    lyr = os.path.join(args.root, "词", "lyrics.md")
    errors, warnings = mv_gate.check(args.root, "lyric_sync")
    for msg in warnings:
        print(f"[warn] {msg}")
    if errors:
        for msg in errors:
            print(f"[err] {msg}", file=sys.stderr)
        sys.exit(2)
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
    res = whisperx.align(seg, model_a, meta, audio, args.device, return_char_alignments=True)
    chars = flatten_aligned_chars(res)
    if not chars: sys.exit("对齐失败：无字符级时间戳；检查语言模型、歌词与音频，勿退回按 word 数硬切行")
    per_line, matched_per_line, source_chars, confidence = map_chars_to_lines(lines, chars)

    # 把对齐到的词按原始行切回（按每行字符数顺序消费）
    out_dir = os.path.join(args.root, "字幕"); os.makedirs(out_dir, exist_ok=True)
    ass_events, lrc_lines, report_lines = [], [], []
    for index, line in enumerate(lines):
        aligned = per_line[index]
        if not aligned:
            continue
        start, end = aligned[0]["start"], aligned[-1]["end"]
        # .ass 逐字 \k（厘秒）
        ktext = "".join(f"{{\\k{max(1,int(round((row['end']-row['start'])*100)))}}}{row['char']}" for row in aligned)
        ass_events.append(f"Dialogue: 0,{mv_utils.ts_ass(start)},{mv_utils.ts_ass(end)},Default,,0,0,0,,{ktext}")
        lrc_lines.append(f"{mv_utils.ts_lrc(start)}{line}")
        line_coverage = round(matched_per_line[index] / max(1, sum(1 for char in line if alignable_char(char))), 4)
        report_lines.append({
            "line": line,
            "start": round(float(start), 3),
            "end": round(float(end), 3),
            "char_count": len(aligned),
            "source_char_count": sum(1 for char in line if alignable_char(char)),
            "line_character_coverage": line_coverage,
            "line_confidence": line_coverage,
            "duration": round(float(end - start), 3),
        })

    play_w, play_h = aspect_geometry(args.root)
    font_size = 54 if play_h <= 1080 else 62
    margin_v = max(64, int(play_h * 0.075))
    ass = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {play_w}\nPlayResY: {play_h}\n\n"
           "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
           "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
           "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
           f"Style: Default,PingFang SC,{font_size},&H00FFFFFF,&H0000C8FF,&H00000000,&H64000000,"
           f"-1,0,0,0,100,100,0,0,1,3,1,2,40,40,{margin_v},1\n\n"
           "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
           + "\n".join(ass_events) + "\n")
    open(os.path.join(out_dir, "karaoke.ass"), "w", encoding="utf-8").write(ass)
    open(os.path.join(out_dir, "lyrics.lrc"), "w", encoding="utf-8").write("\n".join(lrc_lines) + "\n")
    timing_issues = []
    for previous, current in zip(report_lines, report_lines[1:]):
        if current["start"] < previous["start"]:
            timing_issues.append(f"non_monotonic:{current['line']}")
        if current["start"] < previous["end"] - 0.05:
            timing_issues.append(f"line_overlap:{previous['line']}->{current['line']}")
    report = {
        "schema_version": 3,
        "kind": "mv_lyric_alignment_report",
        "audio": os.path.relpath(song, args.root),
        "master_song": mv_utils.relpath(args.root, mv_utils.find_song(args.root)),
        "inputs_sha256": {
            os.path.relpath(song, args.root): mv_utils.content_hash(song),
            mv_utils.relpath(args.root, mv_utils.find_song(args.root)): mv_utils.content_hash(mv_utils.find_song(args.root)),
            "词/lyrics.md": mv_utils.content_hash(lyr),
        },
        "language": args.lang,
        "device": args.device,
        "audio_duration": round(float(dur), 3),
        "lyric_lines": len(lines),
        "aligned_lines": len(report_lines),
        "alignment_unit": "character",
        "source_characters": source_chars,
        "aligned_characters": sum(matched_per_line),
        "character_coverage_ratio": round(confidence, 4),
        # Legacy alias retained for existing gate/readers.  This is textual
        # character coverage, not a calibrated acoustic probability.
        "alignment_confidence": round(confidence, 4),
        "coverage_seconds": round(float(report_lines[-1]["end"] - report_lines[0]["start"]), 3) if report_lines else 0,
        "lines": report_lines,
        "timing_issues": timing_issues,
        "alignment_contract": "known_lyrics_forced_alignment; no ASR transcript substitution",
        "warnings": [],
    }
    if len(report_lines) != len(lines):
        report["warnings"].append("aligned_lines != lyric_lines，可能有歌词未对齐")
    if confidence < 0.9:
        report["warnings"].append(f"字符时间轴覆盖率仅 {confidence:.1%}，需人工校正歌词、语言或人声 stem")
    weak_lines = [row["line"] for row in report_lines if row["line_confidence"] < 0.85]
    if weak_lines:
        report["warnings"].append(f"{len(weak_lines)} 行字符覆盖低于 85%")
    if timing_issues:
        report["warnings"].append(f"{len(timing_issues)} 个歌词行时间乱序/重叠问题")
    if args.allow_low_confidence:
        report["manual_review"] = {
            "accepted": True,
            "reviewer": str(args.reviewer).strip(),
            "date": date.today().isoformat(),
            "notes": args.notes,
            "bound_inputs_sha256": dict(report["inputs_sha256"]),
        }
    open(os.path.join(out_dir, "alignment_report.json"), "w", encoding="utf-8").write(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    passed = len(report_lines) == len(lines) and confidence >= 0.9 and not weak_lines and not timing_issues
    if passed or args.allow_low_confidence:
        mv_utils.update_progress_stage(args.root, "lyric_sync")
    print(f"[ok] 对齐 {len(report_lines)}/{len(lines)} 行，字符时间轴覆盖率 {confidence:.1%} → 字幕/karaoke.ass + lyrics.lrc")
    if report["warnings"]:
        print("[warn] " + "；".join(report["warnings"]))
    if not passed and not args.allow_low_confidence:
        sys.exit("字符对齐未达到发布阈值，已落报告但未推进阶段；人工修正后重跑，或显式 --allow-low-confidence 留痕")
    print("[next] mv-compose 合成（有 libass 烧 .ass 逐字高亮，无则自带 render_lyrics.py 用 .lrc）")


if __name__ == "__main__":
    main()
