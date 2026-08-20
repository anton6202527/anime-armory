#!/usr/bin/env python3
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

import delivery_qc


def ok_pcm_identity(duration=3.0):
    return {
        "contract": delivery_qc.AUDIO_IDENTITY_CONTRACT,
        "sample_rate_hz": 8000,
        "thresholds": dict(delivery_qc.AUDIO_IDENTITY_THRESHOLDS),
        "source_duration_seconds": duration,
        "output_duration_seconds": duration,
        "duration_delta_seconds": 0.0,
        "status": "ok",
        "anchors": [
            {"anchor": "start", "correlation": 1.0, "offset_ms": 0.0},
            {"anchor": "middle", "correlation": 1.0, "offset_ms": 0.0},
            {"anchor": "end", "correlation": 1.0, "offset_ms": 0.0},
        ],
        "min_correlation": 1.0,
        "max_abs_offset_ms": 0.0,
        "drift_ms": 0.0,
    }


class DeliveryQcTest(unittest.TestCase):
    def test_main_rejects_output_outside_project(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as outside:
            delivery = os.path.join(outside, "成片_MV.mp4")
            with open(delivery, "wb") as handle:
                handle.write(b"outside")
            with mock.patch.object(sys, "argv", ["delivery_qc.py", root, delivery]):
                self.assertEqual(delivery_qc.main(), 2)

    def test_missing_media_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            row = delivery_qc.inspect_delivery(os.path.join(root, "missing.mp4"))
            self.assertIn("missing_video_stream", row["blocks"])
            self.assertIn("missing_audio_stream", row["blocks"])

    def test_clean_delivery_contract(self):
        probed = {
            "format": {"duration": "10.0"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "profile": "High",
                 "pix_fmt": "yuv420p", "color_primaries": "bt709",
                 "color_transfer": "bt709", "color_space": "bt709",
                 "color_range": "tv", "field_order": "progressive"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
            ],
        }
        with mock.patch.object(delivery_qc, "probe", return_value=probed), \
             mock.patch.object(delivery_qc, "loudness", return_value={"input_tp": "-1.2", "input_i": "-10.0"}), \
             mock.patch.object(delivery_qc, "signal_scan", return_value={"black_segments": 0, "freeze_segments": 0}):
            row = delivery_qc.inspect_delivery(
                "delivery.mp4", song_duration=10.0, source_loudness={"input_i": "-10.1"}
            )
        self.assertEqual(row["blocks"], [])

    def test_delivery_rejects_non_high_profile_and_full_range(self):
        probed = {
            "format": {"duration": "10.0"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "profile": "Main",
                 "pix_fmt": "yuv420p", "color_primaries": "bt709",
                 "color_transfer": "bt709", "color_space": "bt709",
                 "color_range": "pc", "field_order": "progressive"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
            ],
        }
        with mock.patch.object(delivery_qc, "probe", return_value=probed), \
             mock.patch.object(delivery_qc, "loudness", return_value={"input_tp": "-1.2", "input_i": "-10.0"}), \
             mock.patch.object(delivery_qc, "signal_scan", return_value={"black_segments": 0, "freeze_segments": 0}):
            row = delivery_qc.inspect_delivery("delivery.mp4", song_duration=10.0)
        self.assertIn("delivery_h264_profile_not_high", row["blocks"])
        self.assertIn("color_range_not_limited", row["blocks"])

    def test_delivery_rejects_dimensions_outside_locked_aspect(self):
        probed = {
            "format": {"duration": "10.0"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "profile": "High", "width": 1920, "height": 1080,
                 "pix_fmt": "yuv420p", "color_primaries": "bt709", "color_transfer": "bt709",
                 "color_space": "bt709", "color_range": "tv", "field_order": "progressive"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
            ],
        }
        with mock.patch.object(delivery_qc, "probe", return_value=probed), \
             mock.patch.object(delivery_qc, "loudness", return_value={"input_tp": "-1.2", "input_i": "-10.0"}), \
             mock.patch.object(delivery_qc, "signal_scan", return_value={"black_segments": 0, "freeze_segments": 0}):
            row = delivery_qc.inspect_delivery("delivery.mp4", expected_dimensions=(1080, 1920))
        self.assertIn("dimensions_not_expected_1080x1920", row["blocks"])

    def test_pcm_identity_checks_start_middle_end_and_drift(self):
        signal = [((index % 97) - 48) / 48.0 for index in range(24000)]
        with mock.patch.object(delivery_qc, "_decode_pcm", side_effect=[signal, list(signal)]):
            result = delivery_qc.audio_identity("source.wav", "delivery.mp4", sample_rate=8000)
        self.assertEqual(result["status"], "ok")
        self.assertEqual([row["anchor"] for row in result["anchors"]], ["start", "middle", "end"])
        self.assertEqual(result["drift_ms"], 0)
        self.assertEqual(result["source_duration_seconds"], 3.0)
        self.assertEqual(result["output_duration_seconds"], 3.0)
        self.assertEqual(result["duration_delta_seconds"], 0.0)

    def test_pcm_identity_rejects_duration_delta_even_when_samples_correlate(self):
        source = [((index % 97) - 48) / 48.0 for index in range(24000)]
        output = source + source[:2000]
        with mock.patch.object(delivery_qc, "_decode_pcm", side_effect=[source, output]):
            result = delivery_qc.audio_identity("source.wav", "delivery.mp4", sample_rate=8000)
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["duration_delta_seconds"], 0.25)

    def test_pcm_identity_measures_uniform_offset_at_all_three_anchors(self):
        source = [
            (((index * 1103515245 + 12345) % 65536) - 32768) / 32768.0
            for index in range(40000)
        ]
        delay_samples = 160
        output = ([0.0] * delay_samples) + source[:-delay_samples]
        with mock.patch.object(delivery_qc, "_decode_pcm", side_effect=[source, output]):
            result = delivery_qc.audio_identity("source.wav", "delivery.mp4", sample_rate=8000)
        self.assertEqual(result["status"], "ok")
        self.assertEqual([row["offset_ms"] for row in result["anchors"]], [20.0, 20.0, 20.0])
        self.assertEqual(result["drift_ms"], 0.0)

    def test_identity_ledger_compares_and_binds_final_and_master_independently(self):
        with tempfile.TemporaryDirectory() as root:
            song = os.path.join(root, "歌", "song.wav")
            final = os.path.join(root, "成片_MV.mp4")
            master = os.path.join(root, "成片_MV_master.mov")
            os.makedirs(os.path.dirname(song), exist_ok=True)
            for path, data in ((song, b"song"), (final, b"final"), (master, b"master")):
                with open(path, "wb") as handle:
                    handle.write(data)
            with mock.patch.object(
                delivery_qc, "audio_identity", side_effect=[ok_pcm_identity(), ok_pcm_identity()]
            ) as compare:
                ledger = delivery_qc.build_audio_identity_ledger(
                    root, song, {"final": final, "master": master}
                )
        self.assertEqual(ledger["status"], "ok")
        self.assertEqual(set(ledger["outputs"]), {"final", "master"})
        self.assertEqual(ledger["outputs"]["final"]["path"], "成片_MV.mp4")
        self.assertEqual(ledger["outputs"]["master"]["path"], "成片_MV_master.mov")
        self.assertNotEqual(ledger["outputs"]["final"]["sha256"], ledger["outputs"]["master"]["sha256"])
        self.assertEqual(compare.call_args_list[0].args[:2], (song, final))
        self.assertEqual(compare.call_args_list[1].args[:2], (song, master))

    def test_main_blocks_when_master_pcm_identity_is_missing(self):
        with tempfile.TemporaryDirectory() as root:
            song = os.path.join(root, "歌", "song.wav")
            final = os.path.join(root, "成片_MV.mp4")
            os.makedirs(os.path.dirname(song), exist_ok=True)
            for path in (song, final):
                with open(path, "wb") as handle:
                    handle.write(path.encode("utf-8"))

            def clean_row(path, **_kwargs):
                return {
                    "path": path, "duration": 3.0, "probe": {}, "loudness": {},
                    "signal_scan": {}, "blocks": [], "warnings": [],
                }

            with mock.patch.object(sys, "argv", ["delivery_qc.py", root, final]), \
                 mock.patch.object(delivery_qc.mv_utils, "audio_duration", return_value=3.0), \
                 mock.patch.object(delivery_qc, "loudness", return_value={"input_i": "-10"}), \
                 mock.patch.object(delivery_qc, "inspect_delivery", side_effect=clean_row), \
                 mock.patch.object(delivery_qc, "audio_identity", return_value=ok_pcm_identity()):
                self.assertEqual(delivery_qc.main(), 1)
            report_path = os.path.join(root, "生产数据", "delivery_qc", "delivery_qc.json")
            with open(report_path, encoding="utf-8") as handle:
                report = json.load(handle)
        self.assertEqual(report["audio_identity"]["outputs"]["final"]["status"], "ok")
        self.assertEqual(report["audio_identity"]["outputs"]["master"]["status"], "missing_output")
        self.assertIn("audio_identity_master_missing_output", report["files"][0]["blocks"])
        self.assertEqual(report["files"][0]["path"], "成片_MV.mp4")
        self.assertEqual(report["files"][0]["sha256"], report["inputs_sha256"]["成片_MV.mp4"])
        self.assertNotIn(root, json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
