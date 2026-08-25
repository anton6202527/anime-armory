import json
from pathlib import Path

import pytest

from visual_authorization import (
    POLICY, SCHEMA, VisualAuthorizationError, authorization_errors,
    authorization_payload_sha256, delegated_visual_authorization,
)


def test_setting_must_be_project_explicit(tmp_path: Path):
    with pytest.raises(VisualAuthorizationError):
        delegated_visual_authorization(tmp_path, "delegate:visual-agent", "panel_pixels")
    (tmp_path / "_设置.md").write_text(f"- 视觉审阅策略：{POLICY}\n", encoding="utf-8")
    receipt = delegated_visual_authorization(tmp_path, "delegate:visual-agent", "panel_pixels")
    assert receipt and receipt["source"] == "project_setting"
    assert authorization_errors(tmp_path, "delegate:visual-agent", "panel_pixels", receipt) == []


def test_digest_bound_envelope(tmp_path: Path):
    path = tmp_path / "生产数据" / "authorizations" / "visual_review.json"
    path.parent.mkdir(parents=True)
    payload = {
        "schema": SCHEMA, "status": "authorized", "authorized_by": "Wesley",
        "source_quote": "允许代理查看当前像素并继续可逆制作。",
        "issued_at": "2026-08-25T00:00:00+08:00", "expires_at": "2099-01-01T00:00:00Z",
        "scope": ["panel_pixels"], "delegate": "visual-agent",
    }
    payload["authorization_sha256"] = authorization_payload_sha256(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    receipt = delegated_visual_authorization(tmp_path, "delegate:visual-agent", "panel_pixels")
    assert receipt and receipt["authorized_by"] == "Wesley"
    payload["source_quote"] = "changed"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    assert authorization_errors(tmp_path, "delegate:visual-agent", "panel_pixels", receipt)
