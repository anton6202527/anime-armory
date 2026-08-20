#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Known-lyrics alignment with hash-bound, fail-closed acceptance evidence.

WhisperX's character/word scores are retained as useful diagnostics. They are
not calibrated probabilities and the stock aligner is not singing-specific, so
they never satisfy formal acceptance by themselves.
"""

import argparse
import array
import copy
import difflib
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "mv_utils.py")
GATE_PATH = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "gate.py")

SCHEMA_VERSION = 5
COVERAGE_METRIC = "text_character_mapping_ratio_not_acoustic_confidence"
REPORT_KIND = "mv_lyric_alignment_report"
ACOUSTIC_KIND = "mv_singing_alignment_acoustic_evidence"
ACCEPTANCE_EXCLUDED_KEYS = ("acceptance", "manual_review", "acoustic_evidence")
PASS_STATUSES = {"pass", "sufficient"}


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv_utils = _load_module("mv_utils", MV_UTILS_PATH)
mv_gate = _load_module("mv_gate", GATE_PATH)


def load_lyric_lines(path):
    lines = []
    with open(path, encoding="utf-8") as source:
        for raw in source:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith(">"):
                continue
            if re.fullmatch(r"\[[^\]]+\]", line):
                continue
            line = re.sub(r"（歌词…）|\(歌词…\)", "", line).strip()
            if line:
                lines.append(line)
    return lines


def alignable_char(value):
    return bool(value and (value.isalnum() or "\u3400" <= value <= "\u9fff"))


def _finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def flatten_aligned_chars(result):
    """Flatten timed characters without discarding WhisperX's raw scores."""
    rows = []
    for segment in result.get("segments") or []:
        for row in segment.get("chars") or []:
            char = str(row.get("char") or "")
            if not (alignable_char(char) and row.get("start") is not None and row.get("end") is not None):
                continue
            item = {"char": char, "start": float(row["start"]), "end": float(row["end"])}
            score = _finite_number(row.get("score"))
            if score is not None:
                item["score"] = score
            rows.append(item)
    return rows


def flatten_aligned_words(result):
    """Flatten timed words while preserving raw WhisperX word scores."""
    rows = []
    for segment in result.get("segments") or []:
        for row in segment.get("words") or []:
            word = str(row.get("word") or "").strip()
            if not (word and row.get("start") is not None and row.get("end") is not None):
                continue
            item = {"word": word, "start": float(row["start"]), "end": float(row["end"])}
            score = _finite_number(row.get("score"))
            if score is not None:
                item["score"] = score
            rows.append(item)
    return rows


def score_summary(rows):
    scores = [float(row["score"]) for row in rows if _finite_number(row.get("score")) is not None]
    result = {"timed_units": len(rows), "scored_units": len(scores)}
    if scores:
        ordered = sorted(scores)
        result.update({
            "minimum": round(ordered[0], 6),
            "mean": round(sum(ordered) / len(ordered), 6),
            "maximum": round(ordered[-1], 6),
        })
    return result


def map_chars_to_lines(lines, aligned_chars):
    source = [
        (line_index, char_index, char)
        for line_index, line in enumerate(lines)
        for char_index, char in enumerate(line)
        if alignable_char(char)
    ]
    source_text = "".join(char.lower() for _line, _index, char in source)
    observed_text = "".join(row["char"].lower() for row in aligned_chars)
    matcher = difflib.SequenceMatcher(a=source_text, b=observed_text, autojunk=False)
    source_to_observed = {}
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            source_to_observed[block.a + offset] = block.b + offset
    per_line = [[] for _ in lines]
    matched_per_line = [0 for _ in lines]
    for source_index, (line_index, char_index, _char) in enumerate(source):
        observed_index = source_to_observed.get(source_index)
        if observed_index is not None:
            row = dict(aligned_chars[observed_index])
            row["source_char_index"] = char_index
            per_line[line_index].append(row)
            matched_per_line[line_index] += 1
    total = len(source)
    coverage = len(source_to_observed) / total if total else 0.0
    return per_line, matched_per_line, total, coverage


def karaoke_text(line, aligned):
    """Preserve every original glyph; unmatched glyphs receive no fake timing."""
    by_index = {
        int(row["source_char_index"]): row
        for row in aligned
        if row.get("source_char_index") is not None
    }
    parts = []
    for index, char in enumerate(line):
        row = by_index.get(index)
        centiseconds = max(1, int(round((row["end"] - row["start"]) * 100))) if row else 0
        parts.append(f"{{\\k{centiseconds}}}{char}")
    return "".join(parts)


def aspect_geometry(root):
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    settings = mv_utils.parse_settings(root)
    aspect = meta.get("aspect") or settings.get("合成画幅") or "16:9"
    return {"9:16": (1080, 1920), "1:1": (1080, 1080)}.get(aspect, (1920, 1080))


def stable_json_sha256(payload):
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def preaccept_report_payload(report):
    payload = copy.deepcopy(report)
    for key in ACCEPTANCE_EXCLUDED_KEYS:
        payload.pop(key, None)
    return payload


def preaccept_report_sha256(report):
    return stable_json_sha256(preaccept_report_payload(report))


def _asset_binding(path, rel):
    return {"path": rel, "sha256": mv_utils.content_hash(path)}


def acceptance_binding(root, report):
    master_rel = str(report.get("master_song") or "")
    audio_rel = str(report.get("audio") or "")
    lyrics_rel = "词/lyrics.md"
    ass_rel = "字幕/karaoke.ass"
    lrc_rel = "字幕/lyrics.lrc"
    return {
        "master": _asset_binding(os.path.join(root, master_rel), master_rel),
        "alignment_audio": _asset_binding(os.path.join(root, audio_rel), audio_rel),
        "lyrics": _asset_binding(os.path.join(root, lyrics_rel), lyrics_rel),
        "ass": _asset_binding(os.path.join(root, ass_rel), ass_rel),
        "lrc": _asset_binding(os.path.join(root, lrc_rel), lrc_rel),
        "report_preaccept_content_sha256": preaccept_report_sha256(report),
    }


def report_freshness_errors(root, report):
    errors = []
    if report.get("kind") != REPORT_KIND or int(report.get("schema_version") or 0) != SCHEMA_VERSION:
        errors.append("alignment_report 必须是 schema 5")
    if "alignment_confidence" in report:
        errors.append("schema 5 禁止 alignment_confidence；字符覆盖率不是声学置信度")
    if report.get("coverage_metric") != COVERAGE_METRIC:
        errors.append("coverage_metric 未声明为纯文本字符映射覆盖率")
    current_master = mv_utils.find_song(root)
    current_master_rel = mv_utils.relpath(root, current_master) if current_master else ""
    if not current_master or report.get("master_song") != current_master_rel:
        errors.append("报告未绑定当前 master song")
    for label, receipts in (("inputs_sha256", report.get("inputs_sha256")),
                            ("outputs_sha256", report.get("outputs_sha256"))):
        if not isinstance(receipts, dict) or not receipts:
            errors.append(f"缺 {label}")
            continue
        for rel, digest in receipts.items():
            current = mv_utils.content_hash(os.path.join(root, rel))
            if not current or current != digest:
                errors.append(f"{label} 已过期：{rel}")
    for required in (str(report.get("audio") or ""), str(report.get("master_song") or ""), "词/lyrics.md"):
        if not required or (report.get("inputs_sha256") or {}).get(required) != mv_utils.content_hash(
                os.path.join(root, required)):
            errors.append(f"输入收据缺失或过期：{required or '<empty>'}")
    for required in ("字幕/karaoke.ass", "字幕/lyrics.lrc"):
        if (report.get("outputs_sha256") or {}).get(required) != mv_utils.content_hash(os.path.join(root, required)):
            errors.append(f"输出收据缺失或过期：{required}")
    return list(dict.fromkeys(errors))


def _pearson(left, right):
    if len(left) != len(right) or len(left) < 3:
        return -1.0
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_delta = [value - left_mean for value in left]
    right_delta = [value - right_mean for value in right]
    left_energy = sum(value * value for value in left_delta)
    right_energy = sum(value * value for value in right_delta)
    if left_energy <= 1e-18 or right_energy <= 1e-18:
        return -1.0
    return sum(a * b for a, b in zip(left_delta, right_delta)) / math.sqrt(left_energy * right_energy)


def decode_audio_envelope(path, sample_rate=8000, envelope_rate=100):
    """Decode via ffmpeg and return a mono RMS envelope for correlation."""
    if not shutil.which("ffmpeg"):
        raise ValueError("找不到 ffmpeg，无法自动验证 stem→master 时间基准")
    command = [
        "ffmpeg", "-nostdin", "-v", "error", "-i", path, "-vn", "-ac", "1",
        "-ar", str(sample_rate), "-f", "f32le", "pipe:1",
    ]
    try:
        completed = subprocess.run(command, capture_output=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError(f"ffmpeg 解码失败：{exc}") from exc
    if completed.returncode != 0 or not completed.stdout:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()[-400:]
        raise ValueError(f"ffmpeg 解码失败：{detail or 'empty PCM'}")
    samples = array.array("f")
    usable = len(completed.stdout) - (len(completed.stdout) % samples.itemsize)
    samples.frombytes(completed.stdout[:usable])
    if sys.byteorder != "little":
        samples.byteswap()
    hop = max(1, sample_rate // envelope_rate)
    envelope = []
    for start in range(0, len(samples) - hop + 1, hop):
        block = samples[start:start + hop]
        rms = math.sqrt(sum(float(value) * float(value) for value in block) / hop)
        envelope.append(math.log1p(rms * 1000.0))
    if len(envelope) < envelope_rate * 4:
        raise ValueError("音频太短，无法可靠验证 stem→master offset/drift")
    return envelope


def _fit_offset_drift(matches, duration):
    if not matches:
        return 0.0, 0.0
    if len(matches) == 1:
        return float(matches[0][1]), 0.0
    xs = [float(row[0]) for row in matches]
    ys = [float(row[1]) for row in matches]
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    denominator = sum((value - x_mean) ** 2 for value in xs)
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys)) / denominator if denominator else 0.0
    offset_at_start = y_mean - slope * x_mean
    return offset_at_start, slope * duration


def estimate_stem_master_timing_from_envelopes(
        stem, master, envelope_rate=100, search_seconds=2.0, window_seconds=10.0,
        min_correlation=0.15, max_drift_seconds=0.08):
    """Estimate ``master_time = stem_time + offset + drift * fraction``."""
    if not 0.15 <= float(min_correlation) <= 1.0:
        raise ValueError("stem minimum correlation 必须在 [0.15,1]，不得放宽默认下限")
    if not 0.0 <= float(max_drift_seconds) <= 0.08:
        raise ValueError("stem maximum drift 必须在 [0,0.08] 秒，不得放宽默认上限")
    if not 0.0 < float(search_seconds) <= 10.0:
        raise ValueError("stem offset 搜索窗必须在 (0,10] 秒")
    stem_duration = len(stem) / envelope_rate
    master_duration = len(master) / envelope_rate
    duration_delta = master_duration - stem_duration
    if abs(duration_delta) > 0.25:
        raise ValueError(
            f"stem/master 解码时长差 {duration_delta:+.3f}s 超过 0.25s，无法可靠推定 drift"
        )
    search = max(1, int(round(search_seconds * envelope_rate)))
    half_window = max(envelope_rate * 2, int(round(window_seconds * envelope_rate / 2)))
    lower = half_window
    upper = min(len(stem), len(master)) - half_window
    if upper <= lower:
        raise ValueError("音频共同有效区太短，无法做三点 stem→master 相关性验证")
    span = upper - lower
    centers = sorted(set([
        lower + int(span * 0.15),
        lower + int(span * 0.50),
        lower + int(span * 0.85),
    ]))
    matches = []
    windows = []
    for center in centers:
        stem_start = center - half_window
        stem_end = center + half_window
        probe = stem[stem_start:stem_end]
        best = None
        for shift in range(-search, search + 1):
            master_start = stem_start + shift
            master_end = stem_end + shift
            if master_start < 0 or master_end > len(master):
                continue
            correlation = _pearson(probe, master[master_start:master_end])
            candidate = (correlation, -abs(shift), shift)
            if best is None or candidate > best:
                best = candidate
        if best is None:
            raise ValueError("没有足够重叠窗口可验证 stem→master 时间基准")
        correlation, _prefer_near_zero, shift = best
        if abs(shift) >= search:
            raise ValueError("最佳 stem→master offset 落在搜索边界，无法确认真实偏移")
        offset = shift / envelope_rate
        center_seconds = center / envelope_rate
        matches.append((center_seconds, offset))
        windows.append({
            "stem_center_seconds": round(center_seconds, 4),
            "offset_seconds": round(offset, 4),
            "correlation": round(float(correlation), 6),
        })
    weakest = min(row["correlation"] for row in windows)
    if weakest < min_correlation:
        raise ValueError(
            f"stem→master 最低相关性 {weakest:.3f} < {min_correlation:.3f}，自动验证不充分"
        )
    duration = min(stem_duration, master_duration)
    offset, drift = _fit_offset_drift(matches, duration)
    if abs(drift) > max_drift_seconds:
        raise ValueError(
            f"stem→master 推定 drift {drift:+.3f}s 超过 {max_drift_seconds:.3f}s；不能静默套用"
        )
    return {
        "offset_seconds": round(offset, 6),
        "drift_seconds": round(drift, 6),
        "duration_seconds": round(duration, 4),
        "stem_duration_seconds": round(stem_duration, 4),
        "master_duration_seconds": round(master_duration, 4),
        "duration_delta_seconds": round(duration_delta, 4),
        "windows": windows,
        "minimum_correlation": round(weakest, 6),
        "thresholds": {
            "minimum_correlation": min_correlation,
            "maximum_absolute_drift_seconds": max_drift_seconds,
            "search_seconds": search_seconds,
            "maximum_absolute_duration_delta_seconds": 0.25,
        },
    }


def named_stem_timing_declaration(master, audio, reviewer, notes, offset, drift):
    supplied = [reviewer, notes, offset is not None, drift is not None]
    if not all(supplied):
        raise ValueError(
            "显式 stem 时间基准必须同时给 --stem-timing-reviewer、--stem-timing-notes、"
            "--stem-master-offset-seconds 与 --stem-master-drift-seconds"
        )
    if not valid_reviewer(reviewer):
        raise ValueError("stem 时间基准 reviewer 必须具名，不能匿名/占位")
    if not str(notes).strip():
        raise ValueError("stem 时间基准必须说明 offset/drift 的测量或来源")
    offset_number = _finite_number(offset)
    drift_number = _finite_number(drift)
    if offset_number is None or drift_number is None:
        raise ValueError("stem offset/drift 必须是有限数值")
    return {
        "schema_version": 1,
        "status": "pass",
        "method": "named_offset_drift_declaration",
        "reviewer": str(reviewer).strip(),
        "reviewed_at": date.today().isoformat(),
        "notes": str(notes).strip(),
        "offset_seconds": offset_number,
        "drift_seconds": drift_number,
        "mapping": "master_time = stem_time + offset_seconds + drift_seconds * (stem_time / stem_duration)",
        "bindings": {
            "master": _asset_binding(master, None),
            "alignment_audio": _asset_binding(audio, None),
        },
    }


def build_stem_master_timing(
        root, master, audio, *, reviewer=None, notes=None, offset=None, drift=None,
        search_seconds=2.0, min_correlation=0.15, max_drift_seconds=0.08):
    master_rel = mv_utils.relpath(root, master)
    audio_rel = mv_utils.relpath(root, audio)
    bindings = {
        "master": _asset_binding(master, master_rel),
        "alignment_audio": _asset_binding(audio, audio_rel),
    }
    explicit_any = any(value not in (None, "") for value in (reviewer, notes, offset, drift))
    if os.path.realpath(master) == os.path.realpath(audio):
        if explicit_any:
            raise ValueError("对齐音频就是 master，不应再声明 stem offset/drift")
        return {
            "schema_version": 1,
            "status": "pass",
            "method": "same_master_file",
            "offset_seconds": 0.0,
            "drift_seconds": 0.0,
            "mapping": "identity",
            "bindings": bindings,
        }
    if explicit_any:
        result = named_stem_timing_declaration(master, audio, reviewer, notes, offset, drift)
        result["bindings"] = bindings
        return result
    if bindings["master"]["sha256"] == bindings["alignment_audio"]["sha256"]:
        return {
            "schema_version": 1,
            "status": "pass",
            "method": "automatic_exact_content_hash",
            "offset_seconds": 0.0,
            "drift_seconds": 0.0,
            "mapping": "identity",
            "bindings": bindings,
        }
    stem_envelope = decode_audio_envelope(audio)
    master_envelope = decode_audio_envelope(master)
    estimate = estimate_stem_master_timing_from_envelopes(
        stem_envelope,
        master_envelope,
        search_seconds=search_seconds,
        min_correlation=min_correlation,
        max_drift_seconds=max_drift_seconds,
    )
    return {
        "schema_version": 1,
        "status": "pass",
        "method": "automatic_ffmpeg_rms_envelope_correlation",
        "mapping": "master_time = stem_time + offset_seconds + drift_seconds * (stem_time / stem_duration)",
        "bindings": bindings,
        **estimate,
    }


def stem_timing_errors(root, report):
    timing = report.get("stem_master_timing") or {}
    errors = []
    if timing.get("status") != "pass":
        errors.append("stem_master_timing 未通过")
    expected = {
        "master": _asset_binding(
            os.path.join(root, str(report.get("master_song") or "")),
            str(report.get("master_song") or ""),
        ),
        "alignment_audio": _asset_binding(
            os.path.join(root, str(report.get("audio") or "")),
            str(report.get("audio") or ""),
        ),
    }
    if timing.get("bindings") != expected:
        errors.append("stem_master_timing 未绑定当前 master/alignment audio")
    method = str(timing.get("method") or "")
    offset = _finite_number(timing.get("offset_seconds"))
    drift = _finite_number(timing.get("drift_seconds"))
    if offset is None or drift is None:
        errors.append("stem_master_timing 缺有限 offset/drift")
    same_master = report.get("audio") == report.get("master_song")
    if same_master:
        if method != "same_master_file" or offset != 0.0 or drift != 0.0:
            errors.append("对齐音频就是 master 时必须使用 identity 时间基准")
        return errors
    if method == "named_offset_drift_declaration":
        if not valid_reviewer(timing.get("reviewer")) or not str(timing.get("notes") or "").strip():
            errors.append("显式 stem offset/drift 缺具名 reviewer 或 notes")
    elif method == "automatic_exact_content_hash":
        if expected["master"]["sha256"] != expected["alignment_audio"]["sha256"]:
            errors.append("automatic_exact_content_hash 与当前 master/stem 内容不符")
        if offset != 0.0 or drift != 0.0:
            errors.append("内容完全相同时 offset/drift 必须为 0")
    elif method == "automatic_ffmpeg_rms_envelope_correlation":
        thresholds = timing.get("thresholds") or {}
        minimum = _finite_number(thresholds.get("minimum_correlation"))
        maximum_drift = _finite_number(thresholds.get("maximum_absolute_drift_seconds"))
        search = _finite_number(thresholds.get("search_seconds"))
        maximum_duration_delta = _finite_number(
            thresholds.get("maximum_absolute_duration_delta_seconds")
        )
        if minimum is None or not 0.15 <= minimum <= 1.0:
            errors.append("自动 stem timing 缺有效 minimum_correlation>=0.15")
        if maximum_drift is None or not 0.0 <= maximum_drift <= 0.08:
            errors.append("自动 stem timing 缺有效 maximum_absolute_drift_seconds<=0.08")
        if search is None or not 0.0 < search <= 10.0:
            errors.append("自动 stem timing 缺有效 offset 搜索窗")
        if maximum_duration_delta is None or not 0.0 <= maximum_duration_delta <= 0.25:
            errors.append("自动 stem timing 缺有效时长差阈值<=0.25s")
        windows = timing.get("windows") or []
        if not isinstance(windows, list) or len(windows) < 3:
            errors.append("自动 stem timing 必须保留至少早/中/晚三个相关性窗口")
        else:
            correlations = []
            for index, row in enumerate(windows):
                correlation = _finite_number(row.get("correlation")) if isinstance(row, dict) else None
                window_offset = _finite_number(row.get("offset_seconds")) if isinstance(row, dict) else None
                if correlation is None or window_offset is None:
                    errors.append(f"自动 stem timing window[{index}] 缺 correlation/offset")
                    continue
                correlations.append(correlation)
                if minimum is not None and correlation < minimum:
                    errors.append(f"自动 stem timing window[{index}] 相关性未达阈值")
            recorded_minimum = _finite_number(timing.get("minimum_correlation"))
            if correlations and (
                    recorded_minimum is None or abs(recorded_minimum - min(correlations)) > 1e-5):
                errors.append("自动 stem timing minimum_correlation 与窗口证据不一致")
        duration_delta = _finite_number(timing.get("duration_delta_seconds"))
        if (duration_delta is None or maximum_duration_delta is None
                or abs(duration_delta) > maximum_duration_delta):
            errors.append("自动 stem timing 的 stem/master 时长差未通过阈值")
        if drift is None or maximum_drift is None or abs(drift) > maximum_drift:
            errors.append("自动 stem timing drift 未通过阈值")
    else:
        errors.append("非 master 对齐音频缺自动验证或显式具名 offset/drift")
    return errors


def apply_stem_timing(rows, timing, stem_duration):
    offset = float(timing.get("offset_seconds") or 0.0)
    drift = float(timing.get("drift_seconds") or 0.0)
    duration = max(float(stem_duration), 1e-9)
    transformed = []
    for source in rows:
        row = dict(source)
        for key in ("start", "end"):
            value = float(row[key])
            row[key] = value + offset + drift * (value / duration)
        if row["start"] < -0.05 or row["end"] <= row["start"]:
            raise ValueError("stem→master 映射产生无效时间戳；请核对 offset/drift")
        row["start"] = max(0.0, row["start"])
        transformed.append(row)
    return transformed


def timing_issues_for_lines(report_lines):
    issues = []
    timed = [row for row in report_lines if row.get("start") is not None and row.get("end") is not None]
    for row in timed:
        if float(row["end"]) <= float(row["start"]):
            issues.append(f"non_positive_duration:{row['line']}")
    for previous, current in zip(timed, timed[1:]):
        if current["start"] < previous["start"]:
            issues.append(f"non_monotonic:{current['line']}")
        if current["start"] < previous["end"] - 0.05:
            issues.append(f"line_overlap:{previous['line']}->{current['line']}")
    return issues


def text_timing_pass(report):
    try:
        coverage = float(report.get("character_coverage_ratio"))
    except (TypeError, ValueError):
        return False
    per_line = []
    for row in report.get("lines") or []:
        number = _finite_number(row.get("line_character_coverage"))
        per_line.append(number if number is not None else 0.0)
    return bool(
        int(report.get("aligned_lines") or 0) == int(report.get("lyric_lines") or -1)
        and coverage >= 0.9
        and (not per_line or min(per_line) >= 0.85)
        and not report.get("timing_issues")
    )


def weak_line_indices(report_lines):
    return [
        index for index, row in enumerate(report_lines)
        if row.get("start") is None
        or row.get("end") is None
        or float(row.get("line_character_coverage") or 0.0) < 0.85
    ]


def correction_required_line_indices(report_lines, overall_coverage):
    """Return every line whose raw evidence requires a manual timing correction."""
    required = set(weak_line_indices(report_lines))
    if float(overall_coverage) < 0.9:
        required.update(
            index for index, row in enumerate(report_lines)
            if float(row.get("line_character_coverage") or 0.0) < 1.0
        )
    timed = [
        (index, row) for index, row in enumerate(report_lines)
        if row.get("start") is not None and row.get("end") is not None
    ]
    for index, row in timed:
        if float(row["end"]) <= float(row["start"]):
            required.add(index)
    for (previous_index, previous), (current_index, current) in zip(timed, timed[1:]):
        if current["start"] < previous["start"] or current["start"] < previous["end"] - 0.05:
            required.update((previous_index, current_index))
    return sorted(required)


def load_and_validate_corrections(path, weak_indices):
    try:
        with open(path, encoding="utf-8") as source:
            payload = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 corrections JSON：{exc}") from exc
    rows = payload.get("corrections") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("--corrections-file 必须是含非空 corrections[] 的 JSON")
    by_index = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("line_index"), int):
            raise ValueError("每条 correction 必须含 0-based 整数 line_index")
        start = _finite_number(row.get("start"))
        end = _finite_number(row.get("end"))
        if start is None or end is None or start < 0 or end <= start:
            raise ValueError("每条 correction 必须含有效 start/end（master 时间秒）")
        by_index[row["line_index"]] = row
    missing = sorted(set(weak_indices) - set(by_index))
    if missing:
        raise ValueError(f"corrections[] 未覆盖全部低覆盖/缺时码歌词行：{missing}")
    return payload


def validate_corrected_outputs(ass_path, lrc_path, expected_lines):
    with open(ass_path, encoding="utf-8") as source:
        ass = source.read()
    with open(lrc_path, encoding="utf-8") as source:
        lrc = source.read()
    ass_events = sum(1 for line in ass.splitlines() if line.startswith("Dialogue:"))
    lrc_events = sum(1 for line in lrc.splitlines() if re.match(r"^\[\d+:\d+(?:\.\d+)?\]", line.strip()))
    if ass_events < expected_lines or lrc_events < expected_lines:
        raise ValueError(
            f"校正版字幕不完整：ASS Dialogue={ass_events}、LRC timed lines={lrc_events}，"
            f"歌词行={expected_lines}"
        )


def apply_line_corrections(report_lines, corrections):
    result = copy.deepcopy(report_lines)
    for correction in corrections.get("corrections") or []:
        index = correction["line_index"]
        if index < 0 or index >= len(result):
            raise ValueError(f"correction line_index 越界：{index}")
        start = float(correction["start"])
        end = float(correction["end"])
        result[index].update({
            "start": round(start, 3),
            "end": round(end, 3),
            "duration": round(end - start, 3),
            "timing_source": "manual_correction",
        })
    return result


def correction_packet_errors(report):
    packet = report.get("low_coverage_correction") or {}
    errors = []
    if text_timing_pass(report):
        return errors
    if packet.get("applied") is not True:
        errors.append("低文本覆盖必须先应用 corrections + 校正版 ASS/LRC")
        return errors
    if not valid_reviewer(packet.get("reviewer")) or not str(packet.get("notes") or "").strip():
        errors.append("低覆盖校正缺具名 reviewer/notes")
    if not isinstance(packet.get("corrections"), list) or not packet.get("corrections"):
        errors.append("低覆盖校正缺非空 corrections[]")
    if packet.get("bound_outputs_sha256") != report.get("outputs_sha256"):
        errors.append("低覆盖校正未绑定当前校正版 ASS/LRC")
    corrected = {row.get("line_index") for row in packet.get("corrections") or [] if isinstance(row, dict)}
    recorded_required = packet.get("required_line_indices")
    if not isinstance(recorded_required, list) or any(not isinstance(value, int) for value in recorded_required):
        errors.append("低覆盖校正缺 required_line_indices")
        recorded_required = []
    try:
        coverage = float(report.get("character_coverage_ratio") or 0.0)
    except (TypeError, ValueError):
        coverage = 0.0
    minimum_required = set(weak_line_indices(report.get("lines") or []))
    if coverage < 0.9:
        minimum_required.update(
            index for index, row in enumerate(report.get("lines") or [])
            if float(row.get("line_character_coverage") or 0.0) < 1.0
        )
    if not minimum_required.issubset(set(recorded_required)):
        errors.append("低覆盖校正的 required_line_indices 未覆盖全部缺字/弱行")
    missing = sorted(set(recorded_required) - corrected)
    if missing:
        errors.append(f"低覆盖校正未覆盖歌词行：{missing}")
    return errors


def valid_reviewer(value):
    name = str(value or "").strip()
    return bool(name and name.lower() not in {"unknown", "anonymous", "reviewer", "n/a", "na", "none", "匿名"})


def _line_evidence_rows(evidence):
    rows = evidence.get("per_line")
    if isinstance(rows, list) and rows:
        return rows, "per_line"
    rows = evidence.get("phonemes")
    if isinstance(rows, list) and rows:
        return rows, "phonemes"
    return [], None


def validate_acoustic_evidence(evidence, expected_binding, lyric_lines):
    errors = []
    if not isinstance(evidence, dict):
        return ["声学证据必须是 JSON object"]
    if evidence.get("kind") != ACOUSTIC_KIND or int(evidence.get("schema_version") or 0) != 1:
        errors.append(f"声学证据必须是 {ACOUSTIC_KIND} schema 1")
    model = evidence.get("model") or {}
    if not str(model.get("name") or "").strip() or not str(model.get("version") or "").strip():
        errors.append("声学证据必须具名 model.name + model.version")
    if evidence.get("singing_specific") is not True:
        errors.append("声学证据模型必须明确 singing_specific=true")
    if evidence.get("calibrated") is not True:
        errors.append("声学证据必须明确 calibrated=true；WhisperX 原始 score 不合格")
    if evidence.get("acceptance_eligible") is not True:
        errors.append("正式声学证据必须明确 acceptance_eligible=true")
    if not str(evidence.get("metric") or "").strip():
        errors.append("声学证据缺具名 metric")
    threshold = _finite_number(evidence.get("threshold"))
    confidence = _finite_number(evidence.get("confidence"))
    if threshold is None or not 0.0 <= threshold <= 1.0:
        errors.append("声学证据 threshold 必须在 [0,1]")
    if confidence is None or not 0.0 <= confidence <= 1.0:
        errors.append("声学证据 confidence 必须在 [0,1]")
    if confidence is not None and threshold is not None and confidence < threshold:
        errors.append("声学证据总体 confidence 低于 threshold")
    if str(evidence.get("status") or "").strip().lower() not in PASS_STATUSES:
        errors.append("声学证据 status 必须为 pass/sufficient")
    if evidence.get("binding") != expected_binding:
        errors.append("声学证据未绑定当前 master/stem/lyrics/ASS/LRC/report 前置内容")
    rows, granularity = _line_evidence_rows(evidence)
    if not rows:
        errors.append("声学证据必须提供 per_line[] 或 phonemes[]")
        return errors
    covered = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("line_index"), int):
            errors.append(f"{granularity}[{index}] 缺整数 line_index")
            continue
        line_index = row["line_index"]
        if line_index < 0 or line_index >= lyric_lines:
            errors.append(f"{granularity}[{index}] line_index 越界")
            continue
        covered.add(line_index)
        score = _finite_number(row.get("score"))
        row_threshold = _finite_number(row.get("threshold"))
        effective_threshold = row_threshold if row_threshold is not None else threshold
        if score is None or effective_threshold is None or score < effective_threshold:
            errors.append(f"{granularity}[{index}] score 未达到阈值")
        status = str(row.get("status") or "pass").strip().lower()
        if status not in PASS_STATUSES:
            errors.append(f"{granularity}[{index}] status={status!r}")
    missing = sorted(set(range(lyric_lines)) - covered)
    if missing:
        errors.append(f"声学证据未覆盖全部歌词行：{missing}")
    return errors


def listening_review_valid(root, report):
    manual = report.get("manual_review") or {}
    acceptance = report.get("acceptance") or {}
    if not (
        manual.get("accepted") is True
        and manual.get("verdict") == "pass"
        and manual.get("kind") == "named_full_listening_review"
        and valid_reviewer(manual.get("reviewer"))
        and str(manual.get("notes") or "").strip()
    ):
        return False
    current_binding = acceptance_binding(root, report)
    return bool(
        manual.get("binding") == current_binding
        and manual.get("bound_report_preaccept_sha256") == current_binding["report_preaccept_content_sha256"]
        and manual.get("bound_inputs_sha256") == report.get("inputs_sha256")
        and manual.get("bound_outputs_sha256") == report.get("outputs_sha256")
        and acceptance.get("route") == "named_listening_review"
        and acceptance.get("evidence_content_sha256") == stable_json_sha256(manual)
    )


def acceptance_errors(root, report):
    errors = report_freshness_errors(root, report)
    errors.extend(stem_timing_errors(root, report))
    errors.extend(correction_packet_errors(report))
    acceptance = report.get("acceptance") or {}
    route = acceptance.get("route")
    if acceptance.get("status") != "accepted" or acceptance.get("accepted") is not True:
        errors.append("alignment_report 尚未正式接受")
    elif route == "named_listening_review":
        if not listening_review_valid(root, report):
            errors.append("具名 listening review 未绑定当前全部资产/报告前置内容")
    elif route == "singing_acoustic_evidence":
        evidence = report.get("acoustic_evidence")
        errors.extend(validate_acoustic_evidence(
            evidence, acceptance_binding(root, report), int(report.get("lyric_lines") or 0)
        ))
        if acceptance.get("evidence_content_sha256") != stable_json_sha256(evidence):
            errors.append("声学证据内容已在签收后变化")
    else:
        errors.append("正式接受 route 必须是 singing acoustic evidence 或 named listening review")
    return list(dict.fromkeys(errors))


def whisperx_identity(whisperx, model_a, metadata):
    try:
        version = importlib.metadata.version("whisperx")
    except importlib.metadata.PackageNotFoundError:
        version = str(getattr(whisperx, "__version__", "runtime-unversioned"))
    model_name = None
    if isinstance(metadata, dict):
        for key in ("model_name", "model", "type"):
            if isinstance(metadata.get(key), str) and metadata[key].strip():
                model_name = metadata[key].strip()
                break
    if not model_name:
        model_name = f"{model_a.__class__.__module__}.{model_a.__class__.__name__}"
    return {"producer": "whisperx", "producer_version": version, "alignment_model": model_name}


def make_report_lines(lines, per_line, matched_per_line):
    report_lines = []
    for index, line in enumerate(lines):
        aligned = per_line[index]
        source_count = sum(1 for char in line if alignable_char(char))
        matched_indices = {row["source_char_index"] for row in aligned}
        coverage = round(matched_per_line[index] / max(1, source_count), 4)
        if not aligned:
            report_lines.append({
                "line_index": index,
                "line": line,
                "start": None,
                "end": None,
                "aligned": False,
                "char_count": 0,
                "source_char_count": source_count,
                "line_character_coverage": 0.0,
                "unaligned_source_indices": [i for i, char in enumerate(line) if alignable_char(char)],
                "duration": None,
                "timing_source": "whisperx_forced_alignment",
            })
            continue
        start, end = aligned[0]["start"], aligned[-1]["end"]
        report_lines.append({
            "line_index": index,
            "line": line,
            "start": round(float(start), 3),
            "end": round(float(end), 3),
            "char_count": len(aligned),
            "source_char_count": source_count,
            "line_character_coverage": coverage,
            "aligned": coverage == 1.0,
            "unaligned_source_indices": [
                i for i, char in enumerate(line) if alignable_char(char) and i not in matched_indices
            ],
            "duration": round(float(end - start), 3),
            "timing_source": "whisperx_forced_alignment",
        })
    return report_lines


def make_alignment_report(
        root, master, audio_path, lyrics_path, language, device, duration, lines,
        report_lines, source_chars, matched_per_line, coverage, chars, words,
        engine_identity, stem_timing):
    audio_rel = mv_utils.relpath(root, audio_path)
    master_rel = mv_utils.relpath(root, master)
    timed_lines = [row for row in report_lines if row.get("start") is not None and row.get("end") is not None]
    inputs = {
        audio_rel: mv_utils.content_hash(audio_path),
        master_rel: mv_utils.content_hash(master),
        "词/lyrics.md": mv_utils.content_hash(lyrics_path),
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "audio": audio_rel,
        "master_song": master_rel,
        "inputs_sha256": inputs,
        "language": language,
        "device": device,
        "audio_duration": round(float(duration), 3),
        "lyric_lines": len(lines),
        "aligned_lines": len(timed_lines),
        "alignment_unit": "character",
        "source_characters": source_chars,
        "aligned_characters": sum(matched_per_line),
        "character_coverage_ratio": round(float(coverage), 4),
        "coverage_metric": COVERAGE_METRIC,
        "coverage_seconds": round(float(timed_lines[-1]["end"] - timed_lines[0]["start"]), 3)
        if timed_lines else 0,
        "lines": report_lines,
        "timing_issues": timing_issues_for_lines(report_lines),
        "alignment_contract": "known_lyrics_forced_alignment; no ASR transcript substitution",
        "stem_master_timing": stem_timing,
        "whisperx_alignment_scores": {
            **engine_identity,
            "calibrated": False,
            "singing_specific": False,
            "acceptance_eligible": False,
            "interpretation": "raw aligner diagnostics; not a singing acoustic acceptance confidence",
            "character_summary": score_summary(chars),
            "word_summary": score_summary(words),
            "characters": chars,
            "words": words,
        },
        "warnings": [],
    }
    if len(timed_lines) != len(lines):
        report["warnings"].append("aligned_lines != lyric_lines，可能有歌词未对齐")
    if coverage < 0.9:
        report["warnings"].append(f"文本字符时间轴覆盖率仅 {coverage:.1%}；这不是声学置信度")
    weak = weak_line_indices(report_lines)
    if weak:
        report["warnings"].append(f"{len(weak)} 行字符覆盖低于 85% 或缺时间戳")
    if report["timing_issues"]:
        report["warnings"].append(f"{len(report['timing_issues'])} 个歌词行时间乱序/重叠问题")
    return report


def write_subtitles(root, lines, per_line):
    out_dir = os.path.join(root, "字幕")
    os.makedirs(out_dir, exist_ok=True)
    events = []
    lrc_lines = []
    for line, aligned in zip(lines, per_line):
        if not aligned:
            continue
        start, end = aligned[0]["start"], aligned[-1]["end"]
        events.append(
            f"Dialogue: 0,{mv_utils.ts_ass(start)},{mv_utils.ts_ass(end)},Default,,0,0,0,,"
            f"{karaoke_text(line, aligned)}"
        )
        lrc_lines.append(f"{mv_utils.ts_lrc(start)}{line}")
    play_w, play_h = aspect_geometry(root)
    font_size = 54 if play_h <= 1080 else 62
    margin_v = max(64, int(play_h * 0.075))
    ass = (
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {play_w}\nPlayResY: {play_h}\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, "
        "Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,PingFang SC,{font_size},&H00FFFFFF,&H0000C8FF,&H00000000,&H64000000,"
        f"-1,0,0,0,100,100,0,0,1,3,1,2,40,40,{margin_v},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        + "\n".join(events)
        + "\n"
    )
    ass_path = os.path.join(out_dir, "karaoke.ass")
    lrc_path = os.path.join(out_dir, "lyrics.lrc")
    with open(ass_path, "w", encoding="utf-8") as target:
        target.write(ass)
    with open(lrc_path, "w", encoding="utf-8") as target:
        target.write("\n".join(lrc_lines) + "\n")
    return ass_path, lrc_path


def _validate_correction_cli(args):
    if not args.allow_low_coverage:
        return
    if not valid_reviewer(args.correction_reviewer):
        raise ValueError("--allow-low-coverage 必须提供具名 --correction-reviewer（旧名 --reviewer）")
    if not str(args.correction_notes or "").strip():
        raise ValueError("--allow-low-coverage 必须提供 --correction-notes（旧名 --notes）")
    for label, path in (
        ("--corrections-file", args.corrections_file),
        ("--corrected-ass", args.corrected_ass),
        ("--corrected-lrc", args.corrected_lrc),
    ):
        if not path or not os.path.isfile(path):
            raise ValueError(f"{label} 不存在：{path}")


def generate_alignment(args):
    if args.acoustic_evidence or args.listening_reviewer or args.listening_notes:
        raise ValueError("正式签收必须在检查产物后另跑 --accept-existing；不能与首次生成合并")
    _validate_correction_cli(args)
    master = mv_utils.find_song(args.root)
    if not master:
        raise ValueError(f"缺 {args.root}/歌/song.*")
    audio_path = args.audio
    if not audio_path:
        vocals_path = os.path.join(args.root, "歌", "_demucs", "vocals.wav")
        if os.path.exists(vocals_path):
            audio_path = vocals_path
            print(f"[info] 自动检测到 demucs 人声轨：{vocals_path}")
        else:
            audio_path = master
    audio_path = os.path.abspath(audio_path)
    lyrics_path = os.path.join(args.root, "词", "lyrics.md")
    gate_errors, warnings = mv_gate.check(args.root, "lyric_sync")
    for message in warnings:
        print(f"[warn] {message}")
    if gate_errors:
        raise ValueError("；".join(gate_errors))
    if not os.path.isfile(audio_path):
        raise ValueError(f"--audio 指定文件不存在：{audio_path}")
    if not os.path.isfile(lyrics_path):
        raise ValueError(f"缺 {lyrics_path}")
    lines = load_lyric_lines(lyrics_path)
    if not lines:
        raise ValueError("lyrics.md 没有可对齐的歌词行（还没填词？）")
    stem_timing = build_stem_master_timing(
        args.root,
        master,
        audio_path,
        reviewer=args.stem_timing_reviewer,
        notes=args.stem_timing_notes,
        offset=args.stem_master_offset_seconds,
        drift=args.stem_master_drift_seconds,
        search_seconds=args.stem_search_seconds,
        min_correlation=args.stem_min_correlation,
        max_drift_seconds=args.stem_max_drift_seconds,
    )
    try:
        import whisperx
    except ImportError as exc:
        raise ValueError("缺依赖：pip install whisperx") from exc
    audio = whisperx.load_audio(audio_path)
    duration = len(audio) / 16000.0
    model_a, metadata = whisperx.load_align_model(language_code=args.lang, device=args.device)
    segments = [{"start": 0.0, "end": duration, "text": " ".join(lines)}]
    result = whisperx.align(
        segments, model_a, metadata, audio, args.device, return_char_alignments=True
    )
    chars = flatten_aligned_chars(result)
    words = flatten_aligned_words(result)
    if not chars:
        raise ValueError("对齐失败：无字符级时间戳；勿退回按 word 数硬切行")
    chars = apply_stem_timing(chars, stem_timing, duration)
    words = apply_stem_timing(words, stem_timing, duration)
    master_duration = mv_utils.audio_duration(master)
    if master_duration and max(row["end"] for row in chars) > master_duration + 0.10:
        raise ValueError("stem→master 映射后的歌词时间戳超出 master 时长；offset/drift 声明不可接受")
    per_line, matched, source_chars, coverage = map_chars_to_lines(lines, chars)
    report_lines = make_report_lines(lines, per_line, matched)
    raw_timing_issues = timing_issues_for_lines(report_lines)
    required_corrections = correction_required_line_indices(report_lines, coverage)
    correction_packet = None
    if args.allow_low_coverage:
        corrections = load_and_validate_corrections(args.corrections_file, required_corrections)
        validate_corrected_outputs(args.corrected_ass, args.corrected_lrc, len(lines))
        report_lines = apply_line_corrections(report_lines, corrections)
    # Do not overwrite existing project subtitles until a requested correction
    # packet has passed all structural checks.
    ass_path, lrc_path = write_subtitles(args.root, lines, per_line)
    if args.allow_low_coverage:
        shutil.copyfile(args.corrected_ass, ass_path)
        shutil.copyfile(args.corrected_lrc, lrc_path)
        correction_packet = {
            "schema_version": 1,
            "applied": True,
            "reviewer": str(args.correction_reviewer).strip(),
            "reviewed_at": date.today().isoformat(),
            "notes": str(args.correction_notes).strip(),
            "corrections_file_sha256": mv_utils.content_hash(args.corrections_file),
            "corrected_ass_source_sha256": mv_utils.content_hash(args.corrected_ass),
            "corrected_lrc_source_sha256": mv_utils.content_hash(args.corrected_lrc),
            "required_line_indices": required_corrections,
            "corrections": corrections["corrections"],
        }
    report = make_alignment_report(
        args.root,
        master,
        audio_path,
        lyrics_path,
        args.lang,
        args.device,
        duration,
        lines,
        report_lines,
        source_chars,
        matched,
        coverage,
        chars,
        words,
        whisperx_identity(whisperx, model_a, metadata),
        stem_timing,
    )
    report["raw_timing_issues"] = raw_timing_issues
    report["outputs_sha256"] = {
        "字幕/karaoke.ass": mv_utils.content_hash(ass_path),
        "字幕/lyrics.lrc": mv_utils.content_hash(lrc_path),
    }
    if correction_packet:
        correction_packet["bound_outputs_sha256"] = dict(report["outputs_sha256"])
        report["low_coverage_correction"] = correction_packet
    report["acceptance"] = {
        "status": "pending",
        "accepted": False,
        "required_routes": ["singing_acoustic_evidence", "named_listening_review"],
        "required_binding": acceptance_binding(args.root, report),
    }
    report_path = os.path.join(args.root, "字幕", "alignment_report.json")
    with open(report_path, "w", encoding="utf-8") as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print(
        f"[ok] 生成待签收时间轴：{report['aligned_lines']}/{len(lines)} 行，"
        f"文本字符覆盖 {coverage:.1%} → 字幕/karaoke.ass + lyrics.lrc"
    )
    if report["warnings"]:
        print("[warn] " + "；".join(report["warnings"]))
    if correction_packet:
        print("[ok] 已应用低覆盖 corrections 与校正版 ASS/LRC；仍需独立正式签收")
    elif not text_timing_pass(report):
        print("[block] 低文本覆盖/时序问题尚缺 corrections + 校正版 ASS/LRC", file=sys.stderr)
    print("[next] 检查当前产物后，用 --accept-existing + 声学证据或具名逐行听审二选一签收")
    return report


def accept_existing(args):
    report_path = os.path.join(args.root, "字幕", "alignment_report.json")
    try:
        with open(report_path, encoding="utf-8") as source:
            report = json.load(source)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取待签收 alignment_report.json：{exc}") from exc
    base_errors = report_freshness_errors(args.root, report)
    base_errors.extend(stem_timing_errors(args.root, report))
    base_errors.extend(correction_packet_errors(report))
    if base_errors:
        raise ValueError("；".join(dict.fromkeys(base_errors)))
    if args.show_required_binding:
        print(json.dumps(acceptance_binding(args.root, report), ensure_ascii=False, indent=2))
        return report
    if (report.get("acceptance") or {}).get("status") == "accepted":
        errors = acceptance_errors(args.root, report)
        if errors:
            raise ValueError("既有签收已失效：" + "；".join(errors))
        # Idempotent repair path: if a prior process stopped after the report
        # write but before progress update, rerunning --accept-existing heals
        # the state without weakening or replacing its evidence.
        mv_utils.update_progress_stage(args.root, "lyric_sync")
        print(f"[ok] 既有正式签收仍有效：{report['acceptance']['route']}；已同步 lyric_sync")
        return report
    acoustic = bool(args.acoustic_evidence)
    listening = bool(args.listening_reviewer or args.listening_notes)
    if acoustic == listening:
        raise ValueError(
            "正式接受必须二选一：--acoustic-evidence FILE，或 "
            "--listening-reviewer NAME + --listening-notes NOTES"
        )
    expected_binding = acceptance_binding(args.root, report)
    recorded_binding = (report.get("acceptance") or {}).get("required_binding")
    if recorded_binding != expected_binding:
        raise ValueError("pending 报告内容已变化，required_binding 失效；重新生成再签收")
    preaccept_file_sha = mv_utils.content_hash(report_path)
    if acoustic:
        try:
            with open(args.acoustic_evidence, encoding="utf-8") as source:
                evidence = json.load(source)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"无法读取 acoustic evidence：{exc}") from exc
        evidence_errors = validate_acoustic_evidence(evidence, expected_binding, int(report["lyric_lines"]))
        if evidence_errors:
            raise ValueError("；".join(evidence_errors))
        stored = copy.deepcopy(evidence)
        stored.update({
            "method": f"{evidence['model']['name']}@{evidence['model']['version']}:{evidence['metric']}",
            "evidence_file_sha256": mv_utils.content_hash(args.acoustic_evidence),
            "bound_inputs_sha256": dict(report["inputs_sha256"]),
            "bound_outputs_sha256": dict(report["outputs_sha256"]),
            "bound_report_preaccept_sha256": expected_binding["report_preaccept_content_sha256"],
        })
        report["acoustic_evidence"] = stored
        report["acceptance"] = {
            "status": "accepted",
            "accepted": True,
            "route": "singing_acoustic_evidence",
            "accepted_at": date.today().isoformat(),
            "binding": expected_binding,
            "bound_preaccept_report_file_sha256": preaccept_file_sha,
            "evidence_content_sha256": stable_json_sha256(stored),
        }
    else:
        if not valid_reviewer(args.listening_reviewer):
            raise ValueError("--listening-reviewer 必须具名，不能匿名/占位")
        if not str(args.listening_notes or "").strip():
            raise ValueError("--listening-notes 必须说明逐行听审结论")
        report["manual_review"] = {
            "schema_version": 1,
            "kind": "named_full_listening_review",
            "accepted": True,
            "verdict": "pass",
            "scope": "full_song_line_by_line_against_master_and_alignment_audio",
            "reviewer": str(args.listening_reviewer).strip(),
            "reviewed_at": date.today().isoformat(),
            "notes": str(args.listening_notes).strip(),
            "reviewed_artifacts": ["master", "alignment_audio", "lyrics", "ass", "lrc", "report_preaccept"],
            "binding": expected_binding,
            "bound_inputs_sha256": dict(report["inputs_sha256"]),
            "bound_outputs_sha256": dict(report["outputs_sha256"]),
            "bound_report_preaccept_sha256": expected_binding["report_preaccept_content_sha256"],
            "bound_preaccept_report_file_sha256": preaccept_file_sha,
        }
        report["acceptance"] = {
            "status": "accepted",
            "accepted": True,
            "route": "named_listening_review",
            "accepted_at": date.today().isoformat(),
            "reviewer": str(args.listening_reviewer).strip(),
            "binding": expected_binding,
            "bound_preaccept_report_file_sha256": preaccept_file_sha,
            "evidence_content_sha256": stable_json_sha256(report["manual_review"]),
        }
    errors = acceptance_errors(args.root, report)
    if errors:
        raise ValueError("签收自检失败（未写 accepted、未推进阶段）：" + "；".join(errors))
    with open(report_path, "w", encoding="utf-8") as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write("\n")
    mv_utils.update_progress_stage(args.root, "lyric_sync")
    print(f"[ok] alignment schema 5 正式接受：{report['acceptance']['route']}；已推进 lyric_sync")
    print("[next] mv-compose 合成（有 libass 烧 ASS；无则由 render_lyrics.py 消费 LRC）")
    return report


def build_parser():
    parser = argparse.ArgumentParser(
        description="已知歌词强制对齐；生成后必须以歌声声学证据或具名逐行听审二选一签收"
    )
    parser.add_argument("root")
    parser.add_argument("--lang", default="zh")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--audio", help="对齐音频（如 vocals stem）；非 master 时必须验证 offset/drift")
    parser.add_argument("--allow-low-coverage", "--allow-low-confidence", dest="allow_low_coverage",
                        action="store_true", help="应用逐行 corrections 与校正版字幕；不等于正式接受")
    parser.add_argument("--correction-reviewer", "--reviewer", dest="correction_reviewer")
    parser.add_argument("--correction-notes", "--notes", dest="correction_notes", default="")
    parser.add_argument("--corrections-file")
    parser.add_argument("--corrected-ass")
    parser.add_argument("--corrected-lrc")
    parser.add_argument("--stem-timing-reviewer")
    parser.add_argument("--stem-timing-notes")
    parser.add_argument("--stem-master-offset-seconds", type=float)
    parser.add_argument("--stem-master-drift-seconds", type=float)
    parser.add_argument("--stem-search-seconds", type=float, default=2.0)
    parser.add_argument("--stem-min-correlation", type=float, default=0.15)
    parser.add_argument("--stem-max-drift-seconds", type=float, default=0.08)
    parser.add_argument("--accept-existing", action="store_true",
                        help="不重跑 WhisperX；验当前 hash 后正式签收 pending report")
    parser.add_argument("--acoustic-evidence", help="歌声/逐音素 acoustic evidence JSON")
    parser.add_argument("--listening-reviewer", help="完整逐行听审人姓名")
    parser.add_argument("--listening-notes", help="完整逐行听审结论")
    parser.add_argument("--show-required-binding", action="store_true",
                        help="打印声学证据必须原样绑定的当前资产 + report 前置内容 SHA")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    args.root = os.path.abspath(args.root)
    try:
        if args.accept_existing:
            accept_existing(args)
            return 0
        if args.show_required_binding:
            raise ValueError("--show-required-binding 只能与 --accept-existing 一起使用")
        generate_alignment(args)
    except ValueError as exc:
        print(f"[block] {exc}", file=sys.stderr)
        return 2
    # A successful WhisperX run remains pending: raw scores are not singing
    # acoustic proof.
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
