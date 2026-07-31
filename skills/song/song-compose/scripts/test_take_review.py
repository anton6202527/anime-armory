#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import take_review


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def test_take_review_recommends_highest_score():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "歌", "takes_manifest.json"), {
            "kind": "song_take_manifest",
            "takes": [{"take_id": "take_01"}, {"take_id": "take_02"}],
        })
        args = type("Args", (), {
            "take": "take_01", "blind_label": "A", "reviewer": "me",
            "hook_score": 5, "melody_score": 4, "vocal_score": 4, "arrangement_score": 3,
            "mix_score": 3, "fit_score": 5, "timecode": ["00:32|note|副歌进入"],
            "strength": [], "risk": [], "notes": "最稳", "recommend": "", "rationale": "",
        })()
        report = take_review.build_review(root, args)
        take_review.write_report(root, report)
        assert report["recommended_take"] == "take_01"
        assert report["reviews"][0]["total_score"] == 24
        assert os.path.exists(os.path.join(root, "歌", "take_review.json"))
