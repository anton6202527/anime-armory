import json
from pathlib import Path

import pytest

import creative_watchdown as cw


def _master(root: Path) -> Path:
    path = root / "合成" / "第1集" / "成片_第1集_zh.mp4"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"master-v1")
    return path


def _record(root: Path, *, findings=()):
    return cw.record_watchdown(
        root,
        "第1集",
        reviewer_kind="executor_visual_audio",
        watched_duration_sec=100.0,
        coverage=1.0,
        dimensions_reviewed=list(cw.DIMENSIONS),
        findings=findings,
        review_notes=["从头到尾听看母版，核对表演、连续性、对白和节奏。"],
    )


def test_watchdown_binds_master_sha_duration_and_never_claims_final_acceptance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    master = _master(tmp_path)
    monkeypatch.setattr(cw, "probe_duration", lambda path: 100.0)

    receipt = _record(tmp_path)
    check = cw.validate_watchdown(tmp_path, "第1集")

    assert receipt["master"]["sha256"] == cw.file_sha256(master)
    assert receipt["watched_duration_sec"] == 100.0
    assert receipt["coverage"] == 1.0
    assert receipt["final_user_acceptance"] is False
    assert receipt["release_completion_verdict"] is False
    assert check["status"] == "pass"


def test_watchdown_rejects_partial_watch_and_out_of_range_timecode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _master(tmp_path)
    monkeypatch.setattr(cw, "probe_duration", lambda path: 100.0)

    with pytest.raises(ValueError, match="实际听看时长不足"):
        cw.record_watchdown(
            tmp_path, "1", reviewer_kind="human", watched_duration_sec=40, coverage=1,
            dimensions_reviewed=list(cw.DIMENSIONS), review_notes=["只看了一部分"],
        )
    with pytest.raises(ValueError, match="timecode 超出"):
        _record(tmp_path, findings=[{
            "timecode_sec": 120, "severity": "warn", "dimension": "pacing", "message": "不存在的时码"
        }])


def test_watchdown_becomes_stale_when_master_bytes_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    master = _master(tmp_path)
    monkeypatch.setattr(cw, "probe_duration", lambda path: 100.0)
    _record(tmp_path)

    master.write_bytes(b"master-v2")
    check = cw.validate_watchdown(tmp_path, "第1集")

    assert check["status"] == "block"
    assert any("SHA" in issue for issue in check["issues"])


def test_block_finding_requires_revision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _master(tmp_path)
    monkeypatch.setattr(cw, "probe_duration", lambda path: 100.0)

    receipt = _record(tmp_path, findings=[{
        "timecode_sec": 31.2, "severity": "block", "dimension": "audio_dialogue", "message": "关键对白被音乐盖住"
    }])

    assert receipt["status"] == "needs_revision"
    assert cw.validate_watchdown(tmp_path, "第1集")["status"] == "block"


@pytest.mark.parametrize(
    ("mutation", "issue_fragment"),
    [
        (lambda data: data.update({"kind": "forged"}), "kind"),
        (lambda data: data.update({"version": 999}), "version"),
        (lambda data: data.update({"episode": "第2集"}), "episode"),
        (lambda data: data.update({"reviewer_kind": "robot"}), "reviewer_kind"),
        (lambda data: data.update({"reviewed_at": "2026-08-26T10:00:00"}), "时区"),
        (lambda data: data.update({"coverage": 1.5}), "coverage"),
        (lambda data: data.update({"coverage": 0.5, "watched_duration_sec": 100.0}), "coverage"),
        (lambda data: data.update({"dimensions_reviewed": ["pacing"]}), "维度"),
        (lambda data: data.update({"review_notes": "我看过了"}), "review_notes"),
        (lambda data: data["master"].update({"duration_sec": 80.0}), "duration"),
        (lambda data: data["master"].update({"sha256": "0" * 64}), "SHA"),
    ],
)
def test_validate_watchdown_rejects_forged_receipt_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation,
    issue_fragment: str,
) -> None:
    _master(tmp_path)
    monkeypatch.setattr(cw, "probe_duration", lambda path: 100.0)
    _record(tmp_path)
    path = cw.receipt_path(tmp_path, "第1集")
    data = json.loads(path.read_text(encoding="utf-8"))
    mutation(data)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    check = cw.validate_watchdown(tmp_path, "第1集")

    assert check["status"] == "block"
    assert any(issue_fragment in issue for issue in check["issues"])


def test_validate_watchdown_derives_block_from_findings_even_if_status_is_forged_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _master(tmp_path)
    monkeypatch.setattr(cw, "probe_duration", lambda path: 100.0)
    _record(tmp_path)
    path = cw.receipt_path(tmp_path, "第1集")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["status"] = "pass"
    data["timecode_findings"] = [{
        "timecode_sec": 1.5,
        "severity": "block",
        "dimension": "story_performance",
        "message": "主角动机在剪辑后断裂",
    }]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    check = cw.validate_watchdown(tmp_path, "第1集")

    assert check["status"] == "block"
    assert check["derived_status"] == "needs_revision"
    assert any("block 级" in issue for issue in check["issues"])


def test_validate_watchdown_rejects_non_object_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _master(tmp_path)
    monkeypatch.setattr(cw, "probe_duration", lambda path: 100.0)
    path = cw.receipt_path(tmp_path, "第1集")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")

    check = cw.validate_watchdown(tmp_path, "第1集")

    assert check["status"] == "block"
    assert any("必须是对象" in issue for issue in check["issues"])
