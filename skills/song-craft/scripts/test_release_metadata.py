#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile
from datetime import date, timedelta

import release_metadata


def test_release_metadata_requires_roles_and_explicit_status():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "合规"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试歌", "genre": "pop", "language": "zh"}, f)
        with open(os.path.join(root, "合规", "rights_metadata.json"), "w", encoding="utf-8") as f:
            json.dump({"sound_recording": {"performers": ["Artist"], "isrc": "USABC2600001"}}, f)
        args = type("Args", (), {
            "release_title": "测试歌", "title": "", "version_title": "", "artist": [],
            "language": "", "genre": "", "explicit": "clean",
            "release_date": (date.today() + timedelta(days=14)).isoformat(), "territory": ["worldwide"],
            "label": "Label", "p_line": "2026 Label", "c_line": "2026 Author",
            "upc_ean": "", "cover_art": "导出/cover.jpg",
        })()
        payload = release_metadata.build(root, args)
        report = release_metadata.check(payload)
        assert report["passed"]
        assert payload["artists"][0]["role"] == "main_artist"
