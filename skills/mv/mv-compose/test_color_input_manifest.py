#!/usr/bin/env python3
import os
import tempfile
import unittest
from unittest import mock

import color_input_manifest as color


class ColourManifestTest(unittest.TestCase):
    def test_classifies_declared_unknown_and_hdr(self):
        self.assertEqual(color.classify({"color_primaries": "bt709", "color_transfer": "bt709",
                                         "color_space": "bt709", "color_range": "tv"}),
                         "declared_bt709_limited")
        self.assertEqual(color.classify({"color_primaries": "bt709", "color_transfer": "bt709",
                                         "color_space": "bt709", "color_range": "pc"}),
                         "declared_bt709_full")
        self.assertEqual(color.classify({}), "untagged")
        self.assertEqual(color.classify({"color_primaries": "bt2020", "color_transfer": "smpte2084"}),
                         "unsupported_hdr_or_wide_gamut")

    def test_full_range_has_explicit_numeric_transform(self):
        self.assertIn("in_range=full:out_range=limited", color.transform_for("declared_bt709_full"))
        self.assertIn("range=tv", color.transform_for("declared_bt709_limited"))

    def test_acceptance_is_bound_to_current_untagged_hashes(self):
        rows = [{"path": "a.mp4", "sha256": "a" * 64, "classification": "untagged"}]
        receipt = {"untagged_acceptance": {"accepted": True, "reviewer": "colorist", "notes": "source docs",
                                             "bound_inputs_sha256": {"a.mp4": "a" * 64}}}
        self.assertTrue(color.valid_acceptance(receipt, rows))
        rows[0]["sha256"] = "b" * 64
        self.assertFalse(color.valid_acceptance(receipt, rows))


if __name__ == "__main__":
    unittest.main()
