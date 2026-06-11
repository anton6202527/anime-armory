#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""voice_manifest 纯函数单测。
    cd skills/ad-voice && python3 test_voice_manifest.py
"""
import unittest

import voice_manifest as vm


class VoiceManifestTest(unittest.TestCase):
    def test_role_key_vo_default(self):
        self.assertEqual(vm.role_key("旁白", {}), "VO")
        self.assertEqual(vm.role_key("无名", {}), "VO")
        self.assertEqual(vm.role_key("女主", {}), "FEMALE")

    def test_role_key_voicemap_override(self):
        vmap = {"代言人": {"key": "STAR"}}
        self.assertEqual(vm.role_key("代言人小李", vmap), "STAR")

    def test_voice_key_placeholder(self):
        k = vm.voice_key_for("旁白", {}, real_backend=False, placeholder_voice="Tingting")
        self.assertTrue(k.endswith(vm.PLACEHOLDER_SUFFIX))
        self.assertEqual(vm.voice_key_for("旁白", {}, real_backend=True), "VO")

    def test_manifest_entry_shape(self):
        e = vm.manifest_entry(1, "旁白", "你好", 2.0, 0.0, 2.0, 0.3, "line_01.wav",
                              {}, real_backend=False, is_placeholder=True)
        self.assertEqual(e["时长"], 2.0)
        self.assertTrue(e["占位"])
        self.assertIn("voice_key", e)
        self.assertIn("音色键", e)

    def test_parse_voiceover(self):
        text = "# comment\n旁白：又是一天\n代言人：选它没错\n无前缀句"
        parsed = vm.parse_voiceover(text)
        self.assertEqual(parsed[0], ("旁白", "又是一天"))
        self.assertEqual(parsed[1], ("代言人", "选它没错"))
        self.assertEqual(parsed[2], ("旁白", "无前缀句"))


if __name__ == "__main__":
    unittest.main()
