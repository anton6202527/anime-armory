#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rights_metadata


def base_payload():
    return {
        "kind": rights_metadata.RIGHTS_KIND,
        "title": "测试歌",
        "rights_status": "original",
        "composition_rights": {
            "contributors": [{"name": "作者", "share_percent": 100}],
            "split_total": 100,
        },
        "sound_recording": {"performers": ["歌手"], "isrc": ""},
        "licenses": {
            "derivative_type": "original",
            "composition_authorization_status": "not_applicable",
            "sample_usage_status": "none",
            "sample_clearance_status": "not_applicable",
            "cover_license_status": "not_applicable",
            "voice_authorization_status": "synthetic",
        },
    }


def test_rights_blocks_ambiguous_voice_and_uncleared_sample():
    payload = base_payload()
    payload["licenses"]["voice_authorization_status"] = "synthetic_or_own"
    payload["licenses"]["sample_usage_status"] = "used"
    report = rights_metadata.check_metadata(payload)
    assert not report["passed"]
    ids = {item["id"] for item in report["findings"]}
    assert "RIGHTS-VOICE-AUTH" in ids
    assert "RIGHTS-SAMPLE-CLEARANCE" in ids


def test_cover_requires_license():
    payload = base_payload()
    payload["licenses"]["derivative_type"] = "cover"
    report = rights_metadata.check_metadata(payload)
    assert any(item["id"] == "RIGHTS-COVER-LICENSE" for item in report["findings"])
