#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import propose_state_delta as psd


def test_build_delta_records_hash_and_candidate_entities():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        chapter = os.path.join(root, "章节", "第01章.md")
        with open(chapter, "w", encoding="utf-8") as f:
            f.write("# 第1章\n沈念看向林照，林照拔剑。\n")
        payload, path = psd.build_delta(root, 1)
        assert path == chapter
        assert payload["kind"] == "novel_state_delta"
        assert payload["status"] == "draft_suggested"
        assert payload["source_chapter_sha256"] == psd.sha256_file(chapter)
        assert "沈念" in payload["candidate_entities"]


def test_main_writes_suggested_delta():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"), exist_ok=True)
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("# 第1章\n沈念出现。\n")
        import sys
        old = sys.argv
        sys.argv = ["propose_state_delta.py", root, "--chapter", "1"]
        try:
            assert psd.main() == 0
        finally:
            sys.argv = old
        out = os.path.join(root, "审稿", "state_delta_第01章.suggested.json")
        data = json.load(open(out, encoding="utf-8"))
        assert data["chapter"] == 1
