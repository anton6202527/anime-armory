#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile

import mix_signoff


def args_for(checks, reviewer="制作人甲"):
    return type("Args", (), {
        "audio": "混音/pre_master.wav", "reviewer": reviewer,
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


def test_mix_signoff_rejects_automated_reviewer_tokens():
    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, "混音", "pre_master.wav")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"audio")
        checks = [f"{name}|pass|checked" for name in mix_signoff.REQUIRED_CHECKS]
        for reviewer in (
            "agent", "mix-automation", "system", "qa_delegate", "listener",
            "Codex", "AI", "制作代理:审听", "机器人/审听",
        ):
            report = mix_signoff.build(root, args_for(checks, reviewer))
            assert report["passed"] is False
            assert "MIX-REVIEWER-AUTOMATED" in {row["id"] for row in report["findings"]}
