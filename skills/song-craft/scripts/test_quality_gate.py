#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import os
import tempfile

import quality_gate


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def test_compose_gate_requires_all_contract_evidence():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"rights_status": "original", "vocal_source": "synthetic"})
        report = quality_gate.evaluate(root, "compose")
        assert not report["passed"]
        assert report["blocking"] >= 4
        sources = {
            "创作/song_brief.json": {"kind": "brief"},
            "素材/reference_pack.json": {"kind": "references"},
            "歌/song_form.json": {"kind": "form"},
        }
        report_paths = {
            "创作/song_brief_check.json": "创作/song_brief.json",
            "素材/reference_pack_check.json": "素材/reference_pack.json",
            "歌/song_form_check.json": "歌/song_form.json",
        }
        for relpath, payload in sources.items():
            write_json(os.path.join(root, relpath), payload)
        for report_path, source_path in report_paths.items():
            write_json(os.path.join(root, report_path), {"passed": True, "source_sha256": quality_gate._canonical_sha256(sources[source_path])})
        lyrics = os.path.join(root, "词", "lyrics.md")
        os.makedirs(os.path.dirname(lyrics), exist_ok=True)
        with open(lyrics, "w", encoding="utf-8") as f:
            f.write("[chorus]\n一句歌词\n")
        write_json(os.path.join(root, "词", "lyric_prosody.json"), {"passed": True, "source_sha256": quality_gate.sha256_file(lyrics)})
        assert quality_gate.evaluate(root, "compose")["passed_without_waiver"]
        with open(lyrics, "a", encoding="utf-8") as f:
            f.write("又改了一句\n")
        stale = quality_gate.evaluate(root, "compose")
        assert not stale["passed"]
        assert any(item["id"] == "GATE-STALE-EVIDENCE" for item in stale["findings"])


def test_selection_gate_detects_stale_review_audio():
    with tempfile.TemporaryDirectory() as root:
        audio = os.path.join(root, "歌", "takes", "take_01.wav")
        os.makedirs(os.path.dirname(audio), exist_ok=True)
        with open(audio, "wb") as f:
            f.write(b"first")
        scores = {key: 4 for key in quality_gate.REVIEW_DIMENSIONS}
        write_json(os.path.join(root, "歌", "takes_manifest.json"), {
            "takes": [{"take_id": "take_01", "audio_path": "歌/takes/take_01.wav", "score": scores}],
        })
        write_json(os.path.join(root, "歌", "take_review.json"), {
            "reviews": [{"take_id": "take_01", "scores": scores, "audio_sha256": hashlib.sha256(b"other").hexdigest()}],
        })
        report = quality_gate.evaluate(root, "select", take_id="take_01")
        assert not report["passed"]
        assert any(item["id"] == "GATE-REVIEW-STALE" for item in report["findings"])
