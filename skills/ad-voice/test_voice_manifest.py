#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""voice_manifest + render_voice 纯函数单测。
    cd skills/ad-voice && python3 -m pytest test_voice_manifest.py
    (或 python3 test_voice_manifest.py)
"""
import argparse
import os
import unittest

import voice_manifest as vm
import render_voice as rv


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
        # 权威 schema 字段：idx/role/text/seconds/占位/voice_key
        self.assertEqual(e["idx"], 1)
        self.assertEqual(e["role"], "旁白")
        self.assertEqual(e["text"], "你好")
        self.assertEqual(e["seconds"], 2.0)
        self.assertTrue(e["占位"])
        self.assertIn("voice_key", e)
        self.assertIn("音色键", e)

    def test_manifest_entry_placeholder_always_present(self):
        # 占位字段恒在（bool），便于 has_placeholder=any(占位) 口径一致。
        e = vm.manifest_entry(2, "旁白", "你好", 1.0, 0.0, 1.0, 0.2, "line_02.wav",
                              {}, real_backend=True, is_placeholder=False)
        self.assertIn("占位", e)
        self.assertFalse(e["占位"])

    def test_parse_voiceover(self):
        text = "# comment\n旁白：又是一天\n代言人：选它没错\n无前缀句"
        parsed = vm.parse_voiceover(text)
        self.assertEqual(parsed[0], ("旁白", "又是一天"))
        self.assertEqual(parsed[1], ("代言人", "选它没错"))
        self.assertEqual(parsed[2], ("旁白", "无前缀句"))

    def test_parse_voiceover_dialogue_with_inline_colon(self):
        # 台词正文里自带冒号（前缀含空格/句子标点）不应被误拆成角色行。
        parsed = vm.parse_voiceover("他停顿了一下，说：明天见")
        self.assertEqual(parsed, [("旁白", "他停顿了一下，说：明天见")])

        parsed2 = vm.parse_voiceover("代言人：他对我说：买它")
        # 冒号靠行首的「代言人」是角色，剩下整句（含内部冒号）是台词正文。
        self.assertEqual(parsed2, [("代言人", "他对我说：买它")])

    def test_parse_voiceover_spaced_prefix_not_split(self):
        # 含空格的前缀（一句话）即便有冒号也不拆成角色行。
        self.assertEqual(vm.parse_voiceover("warning sign: stop"),
                         [("旁白", "warning sign: stop")])

    def test_parse_voiceover_sentence_punct_prefix_not_split(self):
        # 冒号前是一整句（含句子标点）→ 是台词正文，不拆成角色。
        self.assertEqual(vm.parse_voiceover("他停顿，然后说：明天见"),
                         [("旁白", "他停顿，然后说：明天见")])

    def test_parse_voiceover_role_length_boundary(self):
        # 长度边界：12 字以内的合法标签照拆，超过 12 归旁白整句。
        role12 = "一" * 12
        self.assertEqual(vm.parse_voiceover(f"{role12}：内容"), [(role12, "内容")])
        role13 = "一" * 13
        self.assertEqual(vm.parse_voiceover(f"{role13}：内容"), [("旁白", f"{role13}：内容")])


def _args(backend="say", ref=None, clone=False, ref_prefix=None, voice_id=None):
    return argparse.Namespace(backend=backend, ref=ref, clone=clone,
                              ref_prefix=ref_prefix, voice_id=voice_id)


class CloneGateTest(unittest.TestCase):
    def setUp(self):
        # 清掉可能影响判定的参考音 env
        self._saved = {}
        for k in list(os.environ):
            if "_REF_" in k or k.endswith("_REF_AUDIO"):
                self._saved[k] = os.environ.pop(k)

    def tearDown(self):
        os.environ.update(self._saved)

    def test_default_voice_no_auth_required(self):
        # 默认嗓（无 ref / 无 voice_id）即便真后端也不触发闸门。
        self.assertEqual(rv.clone_authorization_check("cosyvoice", _args(backend="cosyvoice")), [])
        # 占位后端永不触发
        self.assertEqual(rv.clone_authorization_check("say", _args(backend="say")), [])
        self.assertEqual(rv.clone_authorization_check("estimate", _args(backend="estimate")), [])

    def test_ref_triggers_gate(self):
        r = rv.clone_authorization_check("cosyvoice", _args(backend="cosyvoice", ref="me.wav"))
        self.assertTrue(r)

    def test_clone_flag_triggers_gate(self):
        r = rv.clone_authorization_check("cosyvoice", _args(backend="cosyvoice", clone=True))
        self.assertTrue(r)

    def test_voice_id_triggers_gate(self):
        # 云端商用后端请求具体代言人/名人音色 → 要授权
        r = rv.clone_authorization_check("minimax", _args(backend="minimax", voice_id="star-li"))
        self.assertTrue(r)

    def test_variant_backend_name_still_gates_when_cloning(self):
        # 关键：变体名（连字符/大小写）不再绕过——只要在克隆就拦。
        for name in ("cosyvoice-v2", "Cosy_Voice", "XTTS", "FishSpeech", "fish-speech"):
            r = rv.clone_authorization_check(name, _args(backend=name, ref="ref.wav"))
            self.assertTrue(r, f"{name} should gate when ref supplied")

    def test_variant_backend_default_voice_no_gate(self):
        # 变体名 + 默认嗓（无克隆痕迹）→ 不该过度触发。
        for name in ("cosyvoice-v2", "XTTS", "fishspeech"):
            self.assertEqual(
                rv.clone_authorization_check(name, _args(backend=name)), [],
                f"{name} default voice should NOT gate")

    def test_ref_env_triggers_gate(self):
        os.environ["COSYVOICE_REF_AUDIO"] = "/tmp/me.wav"
        try:
            r = rv.clone_authorization_check("cosyvoice-v2", _args(backend="cosyvoice-v2"))
            self.assertTrue(r)
        finally:
            os.environ.pop("COSYVOICE_REF_AUDIO", None)

    def test_ref_text_env_does_not_trigger(self):
        # *_REF_*_TEXT 是逐字稿（非声纹来源），不触发闸门。
        os.environ["COSYVOICE_REF_VO_TEXT"] = "参考逐字稿"
        try:
            self.assertEqual(
                rv.clone_authorization_check("cosyvoice", _args(backend="cosyvoice")), [])
        finally:
            os.environ.pop("COSYVOICE_REF_VO_TEXT", None)

    def test_norm_backend(self):
        self.assertEqual(rv.norm_backend("Cosy_Voice-v2"), "cosyvoicev2")
        self.assertEqual(rv.norm_backend("XTTS"), "xtts")


if __name__ == "__main__":
    unittest.main()
