#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import register_cover


def test_register_cover_invalidates_recording_evidence():
    with tempfile.TemporaryDirectory() as root:
        source = os.path.join(root, "cover.wav")
        with open(source, "wb") as f:
            f.write(b"cover-audio")
        for relpath in ("合规/rights_metadata.json", "合规/ai_usage.json"):
            path = os.path.join(root, relpath)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"old": True}, f)
        receipt_path = register_cover.register(root, source, "voice-model", "authorized", "")
        receipt = json.load(open(receipt_path, encoding="utf-8"))
        assert receipt["requires_new_recording_metadata"]
        assert "合规/rights_metadata.json" in receipt["invalidated_evidence_hashes"]
        assert os.path.exists(os.path.join(root, "混音", "pre_master.wav"))
