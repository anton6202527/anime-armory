#!/usr/bin/env python3
import os
import tempfile
import unittest

import delivery_qc


class DeliveryQcTest(unittest.TestCase):
    def test_missing_media_blocks(self):
        with tempfile.TemporaryDirectory() as root:
            row = delivery_qc.inspect_delivery(os.path.join(root, "missing.mp4"))
            self.assertIn("missing_video_stream", row["blocks"])
            self.assertIn("missing_audio_stream", row["blocks"])


if __name__ == "__main__":
    unittest.main()
