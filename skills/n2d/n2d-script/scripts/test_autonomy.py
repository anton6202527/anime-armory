from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import autonomy  # noqa: E402


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_autonomy_refuses_draft_and_approves_confirmed_table_read(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 人工批准策略：仅高风险停审\n", encoding="utf-8")
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "voiceover.txt").write_text("台词", encoding="utf-8")
    (ep / "table_read_packet.md").write_text("# 围读\n", encoding="utf-8")
    _write_json(ep / "table_read_packet.json", {"status": "draft"})
    auth = autonomy.authorize(
        tmp_path,
        authorized_by="user:owner",
        source_quote="普通批准自行继续，高风险再问我。",
    )
    assert auth["status"] == "active"
    assert autonomy.approve(tmp_path, "table_read", "第1集")["status"] == "not_ready"

    _write_json(ep / "table_read_packet.json", {"status": "confirmed"})
    result = autonomy.approve(tmp_path, "table_read", "第1集")
    assert result["status"] == "approved"
    manifest = json.loads((ep / "table_read_signoff.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "approved"
    assert manifest["approvals"][0]["review_mode"] == "delegated_autonomy"
    assert manifest["approvals"][0]["authorized_by"] == "user:owner"


def test_autonomy_authorization_keeps_all_high_risk_stops(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 人工批准策略：仅高风险停审\n", encoding="utf-8")
    result = autonomy.authorize(
        tmp_path,
        authorized_by="user:owner",
        source_quote="自行继续制作，高风险再问。",
    )
    payload = result["authorization"]
    payload["human_confirmation_required"].remove("paid_generation_or_purchase")
    from autonomy_policy import validate_authorization

    issues = validate_authorization(payload, tmp_path)
    assert any("高风险停审项" in issue for issue in issues)
