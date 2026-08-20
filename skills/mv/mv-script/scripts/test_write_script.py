#!/usr/bin/env python3
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "write_script.py")
SPEC = importlib.util.spec_from_file_location("mv_write_script", SCRIPT)
write_script = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(write_script)


class WriteScriptContractTest(unittest.TestCase):
    def test_beatgrid_sections_override_stale_meta_structure(self):
        grid = {"sections": [{"section": "intro"}, {"label": "chorus"}]}
        self.assertEqual(write_script._section_names(grid, {"structure": ["verse"]}), ["intro", "chorus"])

    def test_content_receipt_binds_current_inputs_and_uses_relative_source_metadata(self):
        with tempfile.TemporaryDirectory() as root:
            for rel in ("歌", "词", "节拍", "设定"):
                os.makedirs(os.path.join(root, rel), exist_ok=True)
            with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as handle:
                json.dump({"title": "T", "structure": ["stale"], "song_timing": "后配歌曲"}, handle)
            with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as handle:
                handle.write("# _设置\n\n## 选择\n- 歌曲输入时序: 先传音乐\n- MV视觉风格: 电影叙事\n")
            with open(os.path.join(root, "歌", "song.wav"), "wb") as handle:
                handle.write(b"song")
            with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as handle:
                handle.write("一句歌词\n")
            with open(os.path.join(root, "节拍", "beatgrid.json"), "w", encoding="utf-8") as handle:
                json.dump({
                    "sections": [{"section": "verse", "start": 0, "end": 1}],
                    "sections_verified": True,
                    "sections_complete": True,
                }, handle)
            source = os.path.join(root, "candidate.md")
            with open(source, "w", encoding="utf-8") as handle:
                handle.write("# 当前视觉蓝图\n")

            proc = subprocess.run(
                [sys.executable, SCRIPT, root, "--content-file", source],
                text=True, capture_output=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            with open(os.path.join(root, "设定", "mv_script_state.json"), encoding="utf-8") as handle:
                state = json.load(handle)
            self.assertEqual(state["schema_version"], 2)
            self.assertEqual(state["source"]["original_name"], "candidate.md")
            self.assertNotIn(root, json.dumps(state, ensure_ascii=False))
            self.assertEqual(state["section_names"], ["verse"])
            self.assertEqual(state["song_timing"], "先传音乐")
            self.assertTrue(all(len(value) == 64 for value in state["inputs_sha256"].values()))
            self.assertEqual(len(state["output_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
