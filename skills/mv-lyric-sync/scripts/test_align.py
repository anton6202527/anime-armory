#!/usr/bin/env python3
import unittest

import align


class CharacterAlignmentTest(unittest.TestCase):
    def test_maps_cjk_by_character_not_word_count(self):
        lines = ["山门外，风起", "Hello world!"]
        observed = []
        t = 0.0
        for char in "山门外风起helloworld":
            observed.append({"char": char, "start": t, "end": t + 0.1})
            t += 0.1
        per_line, matched, total, confidence = align.map_chars_to_lines(lines, observed)
        self.assertEqual([len(row) for row in per_line], [5, 10])
        self.assertEqual(matched, [5, 10])
        self.assertEqual(total, 15)
        self.assertEqual(confidence, 1.0)

    def test_missing_character_reduces_confidence_without_shifting_lines(self):
        lines = ["甲乙丙", "丁戊"]
        observed = [{"char": c, "start": i, "end": i + 0.1} for i, c in enumerate("甲丙丁戊")]
        per_line, matched, _total, confidence = align.map_chars_to_lines(lines, observed)
        self.assertEqual(matched, [2, 2])
        self.assertEqual([row[0]["char"] for row in per_line], ["甲", "丁"])
        self.assertLess(confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
