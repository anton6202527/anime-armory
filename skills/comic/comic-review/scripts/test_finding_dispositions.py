from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

import finding_dispositions as fd


def write_review(root: Path, reason: str = "脸部相似度偏低") -> None:
    panel = root / "出图/第1话/panels/P001.png"
    panel.parent.mkdir(parents=True, exist_ok=True)
    if not panel.exists():
        Image.new("RGB", (32, 32), "red").save(panel)
    payload = {
        "kind": "comic_gate_findings", "chapter": "第1话", "stage": "review",
        "findings": [{
            "severity": "warn", "code": "face_fingerprint_low", "panel_id": "P001",
            "artifact": "出图/第1话/panels/P001.png", "reason": reason,
            "suggested_fix": "并排人审", "evidence_family": "character_consistency",
        }],
    }
    path = root / "生产数据/gate_findings_review_第1话.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_disposition_is_bound_to_current_finding_and_pixels(tmp_path: Path) -> None:
    write_review(tmp_path)
    first = fd.summarize(tmp_path, "第1话")
    finding_id = first["unresolved"][0]["finding_id"]
    fd.append_disposition(
        tmp_path, "第1话", finding_id, status="false_positive",
        reviewer="责任编辑", reason="低机位导致代理分数偏低，目视身份一致",
    )
    assert fd.summarize(tmp_path, "第1话")["unresolved_count"] == 0

    Image.new("RGB", (32, 32), "blue").save(tmp_path / "出图/第1话/panels/P001.png")
    after = fd.summarize(tmp_path, "第1话")
    assert after["unresolved_count"] == 1
    assert after["stale_count"] == 1


def test_changed_reason_invalidates_old_disposition(tmp_path: Path) -> None:
    write_review(tmp_path)
    finding = fd.summarize(tmp_path, "第1话")["unresolved"][0]
    fd.append_disposition(
        tmp_path, "第1话", finding["finding_id"], status="risk_accepted",
        reviewer="主编", reason="当前话允许计划内强背光",
    )
    write_review(tmp_path, reason="服装纹样也可能发生漂移")
    assert fd.summarize(tmp_path, "第1话")["unresolved_count"] == 1


def test_reopened_event_revokes_current_risk_acceptance(tmp_path: Path) -> None:
    write_review(tmp_path)
    finding_id = fd.summarize(tmp_path, "第1话")["unresolved"][0]["finding_id"]
    fd.append_disposition(
        tmp_path, "第1话", finding_id, status="risk_accepted",
        reviewer="责任编辑", reason="内部预览可接受",
    )
    fd.append_disposition(
        tmp_path, "第1话", finding_id, status="reopened",
        reviewer="责任编辑", reason="发布前决定重新处理",
    )

    summary = fd.summarize(tmp_path, "第1话")

    assert summary["currently_resolved"] == 0
    assert summary["unresolved_count"] == 1
    assert summary["reopened_count"] == 1
    assert summary["stale_count"] == 0


def test_receipt_bound_review_report_is_authoritative_over_missing_sidecar(tmp_path: Path) -> None:
    panel = tmp_path / "出图/第1话/panels/P001.png"
    panel.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), "red").save(panel)
    report_path = tmp_path / "生产数据/comic_gate_review_第1话.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "kind": "comic_gate",
                "chapter": "第1话",
                "stage": "review",
                "findings": [{
                    "severity": "warn",
                    "code": "report_only_warning",
                    "panel_id": "P001",
                    "artifact": "出图/第1话/panels/P001.png",
                    "reason": "warning exists only in the authoritative report",
                }],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = fd.summarize(tmp_path, "第1话")

    assert summary["source"] == "生产数据/comic_gate_review_第1话.json"
    assert summary["unresolved_count"] == 1
    assert summary["unresolved"][0]["code"] == "report_only_warning"


def test_colliding_broad_findings_remain_independently_disposable(tmp_path: Path) -> None:
    panel = tmp_path / "出图/第1话/panels/P001.png"
    panel.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), "red").save(panel)
    report_path = tmp_path / "生产数据/comic_gate_review_第1话.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "kind": "comic_gate",
                "chapter": "第1话",
                "stage": "review",
                "findings": [
                    {
                        "severity": "warn", "code": "style", "artifact": "出图/第1话/panels/P001.png",
                        "reason": "检测到疑似模型外框", "suggested_fix": "检查边缘",
                    },
                    {
                        "severity": "warn", "code": "style", "artifact": "出图/第1话/panels/P001.png",
                        "reason": "黑白灰量化偏离话内中位", "suggested_fix": "检查网点",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    first = fd.summarize(tmp_path, "第1话")
    finding_ids = [item["finding_id"] for item in first["unresolved"]]
    assert len(finding_ids) == len(set(finding_ids)) == 2
    for current_id in finding_ids:
        fd.append_disposition(
            tmp_path, "第1话", current_id, status="false_positive",
            reviewer="责任编辑", reason="逐项并排复核通过",
        )
    assert fd.summarize(tmp_path, "第1话")["unresolved_count"] == 0

    Image.new("RGB", (32, 32), "blue").save(panel)
    after = fd.summarize(tmp_path, "第1话")
    assert after["unresolved_count"] == 2
    assert after["stale_count"] == 2


def test_tampered_event_is_not_trusted_and_blocks_further_append(tmp_path: Path) -> None:
    write_review(tmp_path)
    finding_id = fd.summarize(tmp_path, "第1话")["unresolved"][0]["finding_id"]
    fd.append_disposition(
        tmp_path, "第1话", finding_id, status="risk_accepted",
        reviewer="主编", reason="当前版本承担此风险",
    )
    path = fd.ledger_path(tmp_path, "第1话")
    event = json.loads(path.read_text(encoding="utf-8"))
    event.pop("event_sha256")
    event["chapter"] = "第2话"
    path.write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    summary = fd.summarize(tmp_path, "第1话")
    assert summary["currently_resolved"] == 0
    assert summary["unresolved_count"] == 1
    assert summary["ledger_integrity_error_count"] == 1
    try:
        fd.append_disposition(
            tmp_path, "第1话", finding_id, status="false_positive",
            reviewer="主编", reason="不应追加到损坏账本",
        )
    except ValueError as exc:
        assert "integrity" in str(exc)
    else:
        raise AssertionError("tampered ledger unexpectedly accepted a new event")


def test_hash_chain_detects_removed_earlier_event(tmp_path: Path) -> None:
    write_review(tmp_path)
    finding_id = fd.summarize(tmp_path, "第1话")["unresolved"][0]["finding_id"]
    fd.append_disposition(
        tmp_path, "第1话", finding_id, status="risk_accepted",
        reviewer="主编", reason="内部阶段接受",
    )
    fd.append_disposition(
        tmp_path, "第1话", finding_id, status="reopened",
        reviewer="主编", reason="公开前重开",
    )
    path = fd.ledger_path(tmp_path, "第1话")
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text(lines[1] + "\n", encoding="utf-8")

    summary = fd.summarize(tmp_path, "第1话")
    assert summary["ledger_integrity_error_count"] == 1
    assert summary["currently_resolved"] == 0
    assert summary["unresolved_count"] == 1
