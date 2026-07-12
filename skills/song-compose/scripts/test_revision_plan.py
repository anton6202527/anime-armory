#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import revision_plan


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def test_ace_step_timecode_issue_becomes_repaint_job():
    with tempfile.TemporaryDirectory() as root:
        audio = os.path.join(root, "歌", "takes", "take_01.wav")
        os.makedirs(os.path.dirname(audio), exist_ok=True)
        with open(audio, "wb") as f:
            f.write(b"audio")
        write_json(os.path.join(root, "歌", "takes_manifest.json"), {
            "backend": "ACE-Step", "takes": [{"take_id": "take_01", "audio_path": "歌/takes/take_01.wav"}],
        })
        write_json(os.path.join(root, "歌", "take_review.json"), {
            "recommended_take": "take_01",
            "reviews": [{"take_id": "take_01", "timecode_notes": [{"timecode": "00:20-00:28", "severity": "block", "note": "咬字错误", "status": "open"}]}],
        })
        report = revision_plan.build(root)
        assert report["jobs"][0]["task_type"] == "repaint"
        assert report["jobs"][0]["repainting_start"] == 20
