from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

import pytest


LIB_DIR = Path(__file__).resolve().parent
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from editorial_authorization import (  # noqa: E402
    AUTHORIZATION_RELATIVE_PATH,
    EditorialAuthorizationError,
    authorization_payload_sha256,
    delegated_authorization_errors,
    delegated_review_authorization,
)


def test_project_setting_is_explicit_delegated_authority_and_revocation_stales_receipt(tmp_path: Path) -> None:
    settings = tmp_path / "_设置.md"
    settings.write_text("- 审阅策略：用户授权制作代理\n", encoding="utf-8")
    reviewer = "delegate:comic-production-agent"

    receipt = delegated_review_authorization(tmp_path, reviewer, "name_board")

    assert receipt is not None
    assert receipt["source"] == "project_setting"
    assert delegated_authorization_errors(tmp_path, reviewer, "name_board", receipt) == []
    settings.write_text("- 审阅策略：逐阶段用户确认\n", encoding="utf-8")
    assert delegated_authorization_errors(tmp_path, reviewer, "name_board", receipt)


def test_missing_project_policy_does_not_inherit_permissive_default(tmp_path: Path) -> None:
    with pytest.raises(EditorialAuthorizationError, match="未显式设置"):
        delegated_review_authorization(tmp_path, "delegate:comic-production-agent", "layout")


def test_digest_bound_envelope_can_authorize_a_scoped_delegate(tmp_path: Path) -> None:
    path = tmp_path / AUTHORIZATION_RELATIVE_PATH
    path.parent.mkdir(parents=True)
    payload = {
        "schema": "comic-editorial-authorization/v1",
        "status": "authorized",
        "authorized_by": "project-owner@example.test",
        "source_quote": "允许制作代理审阅本项目 name board 与 layout",
        "scope": ["name_board", "layout"],
        "delegate": "comic-production-agent",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    payload["authorization_sha256"] = authorization_payload_sha256(payload)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    receipt = delegated_review_authorization(
        tmp_path,
        "delegate:comic-production-agent",
        "layout",
    )

    assert receipt is not None
    assert receipt["source"] == "authorization_envelope"
    assert delegated_authorization_errors(
        tmp_path,
        "delegate:comic-production-agent",
        "layout",
        receipt,
    ) == []

    payload["scope"] = ["name_board"]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(EditorialAuthorizationError):
        delegated_review_authorization(tmp_path, "delegate:comic-production-agent", "layout")
