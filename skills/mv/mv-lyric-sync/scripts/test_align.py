#!/usr/bin/env python3
import argparse
import array
import json
import math
import os
import random
import shutil
import sys
import tempfile
import types
import unittest
import wave
from unittest import mock

import align


def _write(path, content, binary=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if binary else "w"
    kwargs = {} if binary else {"encoding": "utf-8"}
    with open(path, mode, **kwargs) as target:
        target.write(content)


def _write_wav(path, samples, sample_rate=8000):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pcm = array.array("h", samples)
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(path, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(pcm.tobytes())


def _project(root, *, low=False, stem=False):
    master_rel = "歌/song.wav"
    audio_rel = "歌/vocals.wav" if stem else master_rel
    _write(os.path.join(root, master_rel), b"master-audio", binary=True)
    if stem:
        _write(os.path.join(root, audio_rel), b"stem-audio", binary=True)
    _write(os.path.join(root, "词/lyrics.md"), "甲乙\n丙丁\n")
    _write(os.path.join(root, "字幕/karaoke.ass"), "Dialogue: first\nDialogue: second\n")
    _write(os.path.join(root, "字幕/lyrics.lrc"), "[00:00.00]甲乙\n[00:01.00]丙丁\n")
    lines = [
        {
            "line_index": 0, "line": "甲乙", "start": 0.0, "end": 0.9,
            "line_character_coverage": 1.0, "aligned": True,
        },
        {
            "line_index": 1, "line": "丙丁", "start": 1.0, "end": 1.9,
            "line_character_coverage": 0.5 if low else 1.0, "aligned": not low,
        },
    ]
    inputs = {
        audio_rel: align.mv_utils.content_hash(os.path.join(root, audio_rel)),
        master_rel: align.mv_utils.content_hash(os.path.join(root, master_rel)),
        "词/lyrics.md": align.mv_utils.content_hash(os.path.join(root, "词/lyrics.md")),
    }
    outputs = {
        "字幕/karaoke.ass": align.mv_utils.content_hash(os.path.join(root, "字幕/karaoke.ass")),
        "字幕/lyrics.lrc": align.mv_utils.content_hash(os.path.join(root, "字幕/lyrics.lrc")),
    }
    timing = {
        "schema_version": 1,
        "status": "pass",
        "method": "named_offset_drift_declaration" if stem else "same_master_file",
        "offset_seconds": 0.0,
        "drift_seconds": 0.0,
        "reviewer": "Timing Engineer" if stem else None,
        "notes": "DAW sample marker comparison" if stem else None,
        "bindings": {
            "master": {
                "path": master_rel,
                "sha256": align.mv_utils.content_hash(os.path.join(root, master_rel)),
            },
            "alignment_audio": {
                "path": audio_rel,
                "sha256": align.mv_utils.content_hash(os.path.join(root, audio_rel)),
            },
        },
    }
    report = {
        "schema_version": 5,
        "kind": align.REPORT_KIND,
        "audio": audio_rel,
        "master_song": master_rel,
        "inputs_sha256": inputs,
        "outputs_sha256": outputs,
        "alignment_unit": "character",
        "coverage_metric": align.COVERAGE_METRIC,
        "character_coverage_ratio": 0.75 if low else 1.0,
        "lyric_lines": 2,
        "aligned_lines": 2,
        "lines": lines,
        "timing_issues": [],
        "stem_master_timing": timing,
        "whisperx_alignment_scores": {
            "calibrated": False,
            "singing_specific": False,
            "acceptance_eligible": False,
        },
    }
    if low:
        report["low_coverage_correction"] = {
            "applied": True,
            "reviewer": "Subtitle Editor",
            "notes": "corrected line 2 against master",
            "required_line_indices": [1],
            "corrections": [{"line_index": 1, "start": 1.0, "end": 1.9}],
            "bound_outputs_sha256": dict(outputs),
        }
    report["acceptance"] = {
        "status": "pending",
        "accepted": False,
        "required_binding": align.acceptance_binding(root, report),
    }
    _write(
        os.path.join(root, "字幕/alignment_report.json"),
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    return report


def _acoustic(binding, line_count=2):
    return {
        "schema_version": 1,
        "kind": align.ACOUSTIC_KIND,
        "model": {"name": "SingingPhonemeAligner", "version": "2.3.1"},
        "singing_specific": True,
        "calibrated": True,
        "acceptance_eligible": True,
        "metric": "calibrated_phoneme_boundary_score",
        "threshold": 0.9,
        "confidence": 0.95,
        "status": "pass",
        "binding": binding,
        "per_line": [
            {"line_index": index, "score": 0.95, "threshold": 0.9, "status": "pass"}
            for index in range(line_count)
        ],
    }


class CharacterAlignmentTest(unittest.TestCase):
    def test_maps_cjk_by_character_not_word_count(self):
        lines = ["山门外，风起", "Hello world!"]
        observed = []
        time = 0.0
        for char in "山门外风起helloworld":
            observed.append({"char": char, "start": time, "end": time + 0.1})
            time += 0.1
        per_line, matched, total, coverage = align.map_chars_to_lines(lines, observed)
        self.assertEqual([len(row) for row in per_line], [5, 10])
        self.assertEqual(matched, [5, 10])
        self.assertEqual(total, 15)
        self.assertEqual(coverage, 1.0)

    def test_missing_character_reduces_coverage_without_shifting_lines(self):
        lines = ["甲乙丙", "丁戊"]
        observed = [{"char": char, "start": i, "end": i + 0.1} for i, char in enumerate("甲丙丁戊")]
        per_line, matched, _total, coverage = align.map_chars_to_lines(lines, observed)
        self.assertEqual(matched, [2, 2])
        self.assertEqual([row[0]["char"] for row in per_line], ["甲", "丁"])
        self.assertEqual([row["source_char_index"] for row in per_line[0]], [0, 2])
        self.assertLess(coverage, 0.9)

    def test_karaoke_preserves_punctuation_and_unmatched_has_no_fake_duration(self):
        line = "山门，风起！"
        observed = [
            {"source_char_index": 0, "char": "山", "start": 0.0, "end": 0.2},
            {"source_char_index": 1, "char": "门", "start": 0.2, "end": 0.4},
            {"source_char_index": 3, "char": "风", "start": 0.4, "end": 0.6},
        ]
        text = align.karaoke_text(line, observed)
        self.assertIn("，", text)
        self.assertIn("！", text)
        self.assertIn("{\\k0}起", text)
        self.assertEqual("".join(part.rsplit("}", 1)[-1] for part in text.split("{") if part), line)

    def test_whisperx_char_and_word_scores_are_preserved(self):
        result = {"segments": [{
            "chars": [{"char": "山", "start": 0, "end": 0.2, "score": 0.73}],
            "words": [{"word": "山门", "start": 0, "end": 0.4, "score": 0.61}],
        }]}
        self.assertEqual(align.flatten_aligned_chars(result)[0]["score"], 0.73)
        self.assertEqual(align.flatten_aligned_words(result)[0]["score"], 0.61)


class SchemaFiveTest(unittest.TestCase):
    def test_first_cli_run_writes_pending_schema_five_and_returns_three(self):
        with tempfile.TemporaryDirectory() as root:
            _project(root)
            fake_whisperx = types.SimpleNamespace(
                __version__="test",
                load_audio=lambda _path: [0.0] * 32000,
                load_align_model=lambda **_kwargs: (object(), {"model_name": "test-wav2vec"}),
                align=lambda *_args, **_kwargs: {"segments": [{
                    "chars": [
                        {"char": char, "start": index * 0.4, "end": index * 0.4 + 0.3, "score": 0.8}
                        for index, char in enumerate("甲乙丙丁")
                    ],
                    "words": [
                        {"word": "甲乙", "start": 0.0, "end": 0.7, "score": 0.75},
                        {"word": "丙丁", "start": 0.8, "end": 1.5, "score": 0.74},
                    ],
                }]},
            )
            with mock.patch.dict(sys.modules, {"whisperx": fake_whisperx}), \
                    mock.patch.object(align.mv_gate, "check", return_value=([], [])), \
                    mock.patch.object(align.mv_utils, "update_progress_stage") as progress:
                code = align.main([root])
            self.assertEqual(code, 3)
            progress.assert_not_called()
            with open(os.path.join(root, "字幕/alignment_report.json"), encoding="utf-8") as source:
                report = json.load(source)
            self.assertEqual(report["schema_version"], 5)
            self.assertEqual(report["acceptance"]["status"], "pending")
            self.assertNotIn("alignment_confidence", report)
            gate_errors = align.mv_gate._alignment_contract_errors(root, "compose", {})
            self.assertTrue(any("正式接受" in error for error in gate_errors), gate_errors)

    def test_schema_five_has_text_coverage_but_no_alignment_confidence(self):
        with tempfile.TemporaryDirectory() as root:
            base = _project(root)
            chars = [
                {"char": "甲", "start": 0.0, "end": 0.2, "score": 0.7},
                {"char": "乙", "start": 0.2, "end": 0.4, "score": 0.8},
            ]
            report = align.make_alignment_report(
                root,
                os.path.join(root, "歌/song.wav"),
                os.path.join(root, "歌/song.wav"),
                os.path.join(root, "词/lyrics.md"),
                "zh",
                "cpu",
                2.0,
                ["甲乙"],
                [base["lines"][0]],
                2,
                [2],
                1.0,
                chars,
                [{"word": "甲乙", "start": 0.0, "end": 0.4, "score": 0.6}],
                {"producer": "whisperx", "producer_version": "3.4.2", "alignment_model": "wav2vec2"},
                base["stem_master_timing"],
            )
            self.assertEqual(report["schema_version"], 5)
            self.assertEqual(report["character_coverage_ratio"], 1.0)
            self.assertNotIn("alignment_confidence", report)
            raw = report["whisperx_alignment_scores"]
            self.assertFalse(raw["calibrated"])
            self.assertFalse(raw["singing_specific"])
            self.assertFalse(raw["acceptance_eligible"])
            self.assertEqual(raw["characters"][0]["score"], 0.7)
            self.assertEqual(raw["words"][0]["score"], 0.6)

    def test_preaccept_hash_ignores_only_acceptance_evidence(self):
        report = {"schema_version": 5, "value": 1, "acceptance": {"status": "pending"}}
        original = align.preaccept_report_sha256(report)
        report["manual_review"] = {"accepted": True}
        report["acoustic_evidence"] = {"status": "pass"}
        report["acceptance"] = {"status": "accepted"}
        self.assertEqual(align.preaccept_report_sha256(report), original)
        report["value"] = 2
        self.assertNotEqual(align.preaccept_report_sha256(report), original)


class StemMasterTimingTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg required")
    def test_ffmpeg_decode_and_correlation_verify_real_wav_stem(self):
        with tempfile.TemporaryDirectory() as root:
            sample_rate = 8000
            duration = 16
            rng = random.Random(29)
            amplitudes = [0.12 + rng.random() * 0.82 for _ in range(duration * 10)]
            stem_samples = []
            for index in range(sample_rate * duration):
                amplitude = amplitudes[min(len(amplitudes) - 1, index // (sample_rate // 10))]
                value = amplitude * math.sin(2 * math.pi * (170 + (index // 800) % 7 * 31) * index / sample_rate)
                stem_samples.append(int(22000 * value))
            shift = int(0.10 * sample_rate)
            master_samples = [0] * shift + stem_samples[:-shift]
            master = os.path.join(root, "歌/song.wav")
            stem = os.path.join(root, "歌/vocals.wav")
            _write_wav(master, master_samples, sample_rate)
            _write_wav(stem, stem_samples, sample_rate)
            timing = align.build_stem_master_timing(
                root, master, stem, min_correlation=0.8
            )
            self.assertEqual(timing["method"], "automatic_ffmpeg_rms_envelope_correlation")
            self.assertAlmostEqual(timing["offset_seconds"], 0.10, places=2)
            self.assertAlmostEqual(timing["drift_seconds"], 0.0, places=2)
            report = {"master_song": "歌/song.wav", "audio": "歌/vocals.wav", "stem_master_timing": timing}
            self.assertEqual(align.stem_timing_errors(root, report), [])
            report["stem_master_timing"]["windows"] = report["stem_master_timing"]["windows"][:1]
            self.assertTrue(any("三个相关性窗口" in error for error in align.stem_timing_errors(root, report)))

    def test_envelope_correlation_finds_positive_master_offset(self):
        rng = random.Random(13)
        stem = [rng.random() for _ in range(800)]
        shift = 4
        master = [0.0] * shift + stem[:-shift]
        result = align.estimate_stem_master_timing_from_envelopes(
            stem,
            master,
            envelope_rate=20,
            search_seconds=1.0,
            window_seconds=6.0,
            min_correlation=0.95,
            max_drift_seconds=0.05,
        )
        self.assertAlmostEqual(result["offset_seconds"], 0.2, places=2)
        self.assertAlmostEqual(result["drift_seconds"], 0.0, places=2)
        self.assertGreaterEqual(result["minimum_correlation"], 0.99)

    def test_unrelated_envelopes_fail_closed(self):
        one = [random.Random(1).random() for _ in range(800)]
        two_rng = random.Random(2)
        two = [two_rng.random() for _ in range(800)]
        with self.assertRaisesRegex(ValueError, "相关性"):
            align.estimate_stem_master_timing_from_envelopes(
                one,
                two,
                envelope_rate=20,
                search_seconds=1.0,
                window_seconds=6.0,
                min_correlation=0.95,
            )

    def test_automatic_thresholds_cannot_be_weakened(self):
        signal = [float(index % 11) for index in range(800)]
        with self.assertRaisesRegex(ValueError, "不得放宽"):
            align.estimate_stem_master_timing_from_envelopes(
                signal, signal, envelope_rate=20, min_correlation=0.01
            )

    def test_explicit_stem_offset_requires_named_complete_declaration(self):
        with tempfile.TemporaryDirectory() as root:
            master = os.path.join(root, "歌/song.wav")
            stem = os.path.join(root, "歌/vocals.wav")
            _write(master, b"master", binary=True)
            _write(stem, b"stem", binary=True)
            result = align.build_stem_master_timing(
                root,
                master,
                stem,
                reviewer="Audio Engineer",
                notes="verified against DAW sample markers",
                offset=0.125,
                drift=0.004,
            )
            self.assertEqual(result["method"], "named_offset_drift_declaration")
            self.assertEqual(result["offset_seconds"], 0.125)
            with self.assertRaisesRegex(ValueError, "同时给"):
                align.build_stem_master_timing(root, master, stem, reviewer="Audio Engineer")


class CorrectionContractTest(unittest.TestCase):
    def test_global_low_coverage_requires_every_line_with_missing_characters(self):
        rows = [
            {"line": "a", "start": 0.0, "end": 1.0, "line_character_coverage": 0.88},
            {"line": "b", "start": 1.1, "end": 2.0, "line_character_coverage": 0.92},
            {"line": "c", "start": 2.1, "end": 3.0, "line_character_coverage": 1.0},
        ]
        self.assertEqual(align.correction_required_line_indices(rows, 0.89), [0, 1])

    def test_low_coverage_corrections_must_cover_each_weak_line_with_master_times(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "corrections.json")
            _write(path, json.dumps({"corrections": [{"line_index": 0, "start": 0, "end": 1}]}))
            with self.assertRaisesRegex(ValueError, "未覆盖"):
                align.load_and_validate_corrections(path, [0, 1])
            _write(path, json.dumps({"corrections": [
                {"line_index": 0, "start": 0, "end": 1},
                {"line_index": 1, "start": 1.1, "end": 2.0},
            ]}))
            payload = align.load_and_validate_corrections(path, [0, 1])
            self.assertEqual(len(payload["corrections"]), 2)

    def test_low_coverage_cannot_formally_accept_without_correction_packet(self):
        with tempfile.TemporaryDirectory() as root:
            report = _project(root, low=True)
            report.pop("low_coverage_correction")
            self.assertTrue(any("corrections" in error for error in align.correction_packet_errors(report)))


class AcousticEvidenceTest(unittest.TestCase):
    def test_named_calibrated_singing_model_and_all_lines_are_required(self):
        binding = {"asset": "current"}
        evidence = _acoustic(binding)
        self.assertEqual(align.validate_acoustic_evidence(evidence, binding, 2), [])
        evidence["calibrated"] = False
        self.assertTrue(any("calibrated" in error for error in align.validate_acoustic_evidence(evidence, binding, 2)))
        evidence["calibrated"] = True
        evidence["acceptance_eligible"] = False
        self.assertTrue(any("acceptance_eligible" in error for error in align.validate_acoustic_evidence(evidence, binding, 2)))
        evidence["acceptance_eligible"] = True
        evidence["model"]["version"] = ""
        self.assertTrue(any("model.name" in error for error in align.validate_acoustic_evidence(evidence, binding, 2)))

    def test_stale_binding_or_missing_line_fails(self):
        binding = {"asset": "current"}
        evidence = _acoustic({"asset": "stale"})
        evidence["per_line"] = evidence["per_line"][:1]
        errors = align.validate_acoustic_evidence(evidence, binding, 2)
        self.assertTrue(any("未绑定" in error for error in errors))
        self.assertTrue(any("未覆盖" in error for error in errors))


class FormalAcceptanceTest(unittest.TestCase):
    def _args(self, root, **overrides):
        values = {
            "root": root,
            "show_required_binding": False,
            "acoustic_evidence": None,
            "listening_reviewer": None,
            "listening_notes": None,
        }
        values.update(overrides)
        return argparse.Namespace(**values)

    def test_named_listening_review_binds_all_assets_and_invalidates_on_output_change(self):
        with tempfile.TemporaryDirectory() as root:
            _project(root)
            args = self._args(
                root,
                listening_reviewer="Lin Mei",
                listening_notes="逐行对照 master、stem、ASS、LRC 与报告，边界通过",
            )
            with mock.patch.object(align.mv_utils, "update_progress_stage") as progress:
                report = align.accept_existing(args)
            progress.assert_called_once_with(root, "lyric_sync")
            self.assertEqual(report["acceptance"]["route"], "named_listening_review")
            self.assertTrue(align.listening_review_valid(root, report))
            self.assertEqual(
                set(report["manual_review"]["binding"]),
                {"master", "alignment_audio", "lyrics", "ass", "lrc", "report_preaccept_content_sha256"},
            )
            with mock.patch.object(align.mv_utils, "update_progress_stage") as progress:
                same = align.accept_existing(self._args(root))
            progress.assert_called_once_with(root, "lyric_sync")
            self.assertEqual(same["acceptance"]["route"], "named_listening_review")
            tampered = json.loads(json.dumps(report))
            tampered["manual_review"]["notes"] = "changed after sign-off"
            self.assertFalse(align.listening_review_valid(root, tampered))
            _write(os.path.join(root, "字幕/lyrics.lrc"), "[00:00.00]changed\n")
            self.assertFalse(align.listening_review_valid(root, report))

    def test_acoustic_route_accepts_current_full_per_line_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            report = _project(root, stem=True)
            evidence_path = os.path.join(root, "acoustic.json")
            _write(evidence_path, json.dumps(_acoustic(align.acceptance_binding(root, report))))
            args = self._args(root, acoustic_evidence=evidence_path)
            with mock.patch.object(align.mv_utils, "update_progress_stage") as progress:
                accepted = align.accept_existing(args)
            progress.assert_called_once()
            self.assertEqual(accepted["acceptance"]["route"], "singing_acoustic_evidence")
            self.assertEqual(align.acceptance_errors(root, accepted), [])
            self.assertEqual(align.mv_gate._alignment_contract_errors(root, "compose", {}), [])
            accepted["acoustic_evidence"]["confidence"] = 0.99
            self.assertTrue(any("签收后变化" in error for error in align.acceptance_errors(root, accepted)))

    def test_low_text_coverage_accepts_only_with_bound_corrections_plus_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            _project(root, low=True)
            args = self._args(
                root,
                listening_reviewer="Subtitle QC",
                listening_notes="校正版逐行对照 master 与 ASS/LRC 后通过",
            )
            with mock.patch.object(align.mv_utils, "update_progress_stage"):
                accepted = align.accept_existing(args)
            self.assertEqual(accepted["acceptance"]["status"], "accepted")
            self.assertEqual(align.acceptance_errors(root, accepted), [])
            self.assertEqual(align.mv_gate._alignment_contract_errors(root, "compose", {}), [])

    def test_acceptance_is_exactly_one_route(self):
        with tempfile.TemporaryDirectory() as root:
            _project(root)
            with self.assertRaisesRegex(ValueError, "二选一"):
                align.accept_existing(self._args(root))


if __name__ == "__main__":
    unittest.main()
