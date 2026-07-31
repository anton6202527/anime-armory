#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose_song.py tests.

Can run without pytest:
    python3 skills/song/song-compose/scripts/test_compose_song.py
"""
import array
import hashlib
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
TAKE_REVIEW = os.path.join(HERE, "take_review.py")


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def canonical_hash(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
    sources = {
        "创作/song_brief.json": {"kind": "song_brief", "sonic_identity": "国风流行"},
        "素材/reference_pack.json": {"kind": "song_reference_pack", "references": []},
        "歌/song_form.json": {"kind": "song_form_packet", "bpm": 100, "meter": "4/4"},
    }
    for relpath, payload in sources.items():
        write_json(os.path.join(root, relpath), payload)
    reports = {
        "创作/song_brief_check.json": canonical_hash(sources["创作/song_brief.json"]),
        "素材/reference_pack_check.json": canonical_hash(sources["素材/reference_pack.json"]),
        "歌/song_form_check.json": canonical_hash(sources["歌/song_form.json"]),
        "词/lyric_prosody.json": hashlib.sha256(open(os.path.join(root, "词", "lyrics.md"), "rb").read()).hexdigest(),
    }
    for relpath, source_hash in reports.items():
        write_json(os.path.join(root, relpath), {"kind": "test_evidence", "passed": True, "source_sha256": source_hash})


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
            self.assertEqual(manifest["schema_version"], 3)
            self.assertEqual(manifest["requested_takes"], 2)
            self.assertEqual(manifest["target_duration_seconds"], 90)
            prompt_path = os.path.join(tmp, "歌", "compose_prompts", "take_01.md")
            self.assertTrue(os.path.exists(prompt_path))
            take = manifest["takes"][0]
            self.assertEqual(take["prompt_source_kind"], "compiled_submit_fields")
            self.assertEqual(take["prompt_compiler"]["profile"], "ace_step_prompt_lyrics")
            self.assertIn("prompt", take["submit_fields"])
            self.assertIn("lyrics", take["submit_fields"])
            self.assertEqual(take["submit_fields"]["audio_duration"], 90)
            with open(prompt_path, encoding="utf-8") as f:
                prompt_text = f.read()
            self.assertIn("## 后端编译提交字段", prompt_text)
            self.assertIn("## 提交边界", prompt_text)

    def test_register_score_and_select_take(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            src = os.path.join(tmp, "generated.wav")
            write_wav(src)
            subprocess.run([sys.executable, COMPOSE, tmp], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, COMPOSE, tmp, "--register", src, "--take", "1"], capture_output=True, text=True, check=True)
            subprocess.run([
                sys.executable, COMPOSE, tmp,
                "--score", "take_01", "--hook-score", "5", "--melody-score", "4", "--vocal-score", "4",
                "--arrangement-score", "4", "--mix-score", "4", "--fit-score", "5", "--notes", "副歌最稳",
            ], capture_output=True, text=True, check=True)
            subprocess.run([
                sys.executable, TAKE_REVIEW, tmp, "--write", "--take", "take_01",
                "--hook-score", "5", "--melody-score", "4", "--vocal-score", "4",
                "--arrangement-score", "4", "--mix-score", "4", "--fit-score", "5",
            ], capture_output=True, text=True, check=True)
            subprocess.run([sys.executable, COMPOSE, tmp, "--select", "take_01"], capture_output=True, text=True, check=True)
            self.assertTrue(os.path.exists(os.path.join(tmp, "歌", "song.wav")))
            self.assertTrue(os.path.exists(os.path.join(tmp, "混音", "pre_master.wav")))
            with open(os.path.join(tmp, "歌", "takes_manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["selected_take"], "take_01")
            take = manifest["takes"][0]
            self.assertEqual(take["status"], "selected")
            self.assertEqual(take["score"]["hook"], 5)
            self.assertEqual(take["notes"], "副歌最稳")
            self.assertTrue(manifest["selection_receipt"]["pre_master_sha256"])


import importlib.util
import types

_spec = importlib.util.spec_from_file_location("compose_song", COMPOSE)
compose_song = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compose_song)


class MakeStyleTest(unittest.TestCase):
    def _args(self):
        return types.SimpleNamespace(style=None, bpm=None, key=None, language=None)

    def test_make_style_includes_instrumentation_and_vocal(self):
        meta = {"genre": "流行", "mood": "燃", "instrumentation": "piano and strings",
                "vocal_type": "female vocals", "theme": "少年下山"}
        s = compose_song.make_style(meta, {}, self._args())
        self.assertIn("piano and strings", s)
        self.assertIn("female vocals", s)

    def test_make_style_skips_absent_fields(self):
        # 缺器乐/人声字段时跳过，不塞空（向后兼容旧 meta）
        s = compose_song.make_style({"genre": "流行"}, {}, self._args())
        self.assertEqual(s, "流行")

    def test_validate_compiled_take_detects_drift(self):
        payload = compose_song.compile_prompt({
            "take_id": "take_01",
            "backend": "ACE-Step",
            "title": "测试歌",
            "style_seed": "国风流行",
            "lyrics": "[verse]\n一句歌词",
            "duration_seconds": 90,
        })
        raw = json.dumps(payload["submit_fields"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        take = {
            "prompt_source_kind": "compiled_submit_fields",
            "prompt_compiler": {key: payload[key] for key in ("kind", "version", "profile_version", "profile", "backend", "field_map")},
            "style_prompt": payload["style_prompt"],
            "lyrics": payload["lyrics"],
            "submit_fields": payload["submit_fields"],
            "source_contract_sha256": payload["source_contract_sha256"],
            "lyrics_sha256": payload["lyrics_sha256"],
            "submit_fields_sha256": __import__("hashlib").sha256(raw.encode("utf-8")).hexdigest(),
        }
        self.assertEqual(compose_song.validate_compiled_take(take, "ACE-Step"), [])
        take["submit_fields"]["prompt"] += " drift"
        self.assertIn("submit_fields_hash_mismatch", compose_song.validate_compiled_take(take, "ACE-Step"))


if __name__ == "__main__":
    unittest.main()
