#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile

import mix_signoff


def args_for(checks):
    return type("Args", (), {
        "audio": "混音/pre_master.wav", "reviewer": "producer",
        "monitoring_context": "headphones+speakers", "check": checks, "notes": "",
    })()


def test_mix_signoff_binds_audio_and_requires_all_checks():
    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, "混音", "pre_master.wav")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"audio")
        incomplete = mix_signoff.build(root, args_for([]))
        assert not incomplete["passed"]
        complete = mix_signoff.build(root, args_for([f"{name}|pass|checked" for name in mix_signoff.REQUIRED_CHECKS]))
        assert complete["passed"]
        assert complete["audio"]["sha256"]
