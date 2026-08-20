#!/usr/bin/env python3
import importlib.util
import os
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location("edit_beatgrid", os.path.join(HERE, "edit_beatgrid.py"))
edit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(edit)


class BeatgridPatchTest(unittest.TestCase):
    def test_point_edits_and_section_replacement_are_deterministic(self):
        grid = {"duration": 8, "beats": [0, 1, 2], "downbeats": [0, 4], "sections": []}
        patch = {"operations": [
            {"target": "beats", "op": "move", "index": 1, "time": 1.1},
            {"target": "beats", "op": "add", "time": 3},
            {"target": "downbeats", "op": "delete", "index": 1},
            {"target": "sections", "op": "replace", "sections": [
                {"section": "verse", "start": 0, "end": 4},
                {"section": "chorus", "start": 4, "end": 8},
            ]},
        ]}
        result = edit.apply_patch(grid, patch)
        self.assertEqual(result["beats"], [0.0, 1.1, 2.0, 3.0])
        self.assertEqual(result["downbeats"], [0.0])
        self.assertTrue(result["sections_complete"])
        self.assertEqual(result["sections"][1]["source"], "manual_patch")

    def test_rejects_non_contiguous_sections(self):
        with self.assertRaisesRegex(ValueError, "空洞或重叠"):
            edit.apply_patch({"duration": 8, "beats": [1], "downbeats": [1]}, {
                "operations": [{"target": "sections", "op": "replace", "sections": [
                    {"section": "a", "start": 0, "end": 3},
                    {"section": "b", "start": 4, "end": 8},
                ]}],
            })


if __name__ == "__main__":
    unittest.main()
