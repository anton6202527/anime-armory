#!/usr/bin/env python3
import os
import tempfile
import unittest
from unittest import mock

import delivery_qc


class DeliveryQcTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
