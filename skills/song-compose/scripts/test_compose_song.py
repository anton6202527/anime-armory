#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose_song.py tests.

Can run without pytest:
    python3 skills/song-compose/scripts/test_compose_song.py
"""
import array
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
import wave


HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE = os.path.join(HERE, "compose_song.py")


def write_wav(path, seconds=1.0, rate=44100):
    samples = int(seconds * rate)
    data = array.array("h")
    for i in range(samples):
        v = int(12000 * math.sin(2 * math.pi * 220 * i / rate))
        data.extend([v, v])
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(data.tobytes())


def make_project(root):
    os.makedirs(os.path.join(root, "词"), exist_ok=True)
    os.makedirs(os.path.join(root, "歌"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({
            "title": "测试歌",
            "genre": "国风流行",
            "mood": "燃",
            "target_platform": "抖音",
            "theme": "少年仗剑下山",
            "vocal_source": "synthetic",
            "rights_status": "original",
        }, f, ensure_ascii=False)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# _设置\n\n## 选择\n- 作曲后端: ACE-Step\n- 生成版数: 2\n- 目标时长: 90s\n- 挑版策略: 最佳hook\n")
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[verse1]\n我从山门一路向前\n\n[chorus]\n仗剑下山闯人间\n")


class ComposeSongTest(unittest.TestCase):
    def test_generates_manifest_and_prompts(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            subprocess.run([sys.executable, COMPOSE, tmp], capture_output=True, text=True, check=True)
            manifest_path = os.path.join(tmp, "歌", "takes_manifest.json")
            self.assertTrue(os.path.exists(manifest_path))
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["backend"], "ACE-Step")
            self.assertEqual(manifest["requested_takes"], 2)
            self.assertEqual(manifest["target_duration_seconds"], 90)
            self.assertTrue(os.path.exists(os.path.join(tmp, "歌", "compose_prompts", "take_01.md")))

    def test_register_score_and_select_take(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "generated.wav")
            write_wav(src)
            subprocess.run([sys.executable, COMPOSE, tmp], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, COMPOSE, tmp, "--register", src, "--take", "1"], capture_output=True, text=True, check=True)
            subprocess.run([
                sys.executable, COMPOSE, tmp,
                "--score", "take_01", "--hook-score", "5", "--vocal-score", "4", "--notes", "副歌最稳",
            ], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, COMPOSE, tmp, "--select", "take_01"], capture_output=True, text=True, check=True)
            self.assertTrue(os.path.exists(os.path.join(tmp, "歌", "song.wav")))
            with open(os.path.join(tmp, "歌", "takes_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["selected_take"], "take_01")
            take = manifest["takes"][0]
            self.assertEqual(take["status"], "selected")
            self.assertEqual(take["score"]["hook"], 5)
            self.assertEqual(take["notes"], "副歌最稳")


if __name__ == "__main__":
    unittest.main()
