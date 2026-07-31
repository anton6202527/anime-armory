from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("event_ledger.py")
spec = importlib.util.spec_from_file_location("event_ledger", SCRIPT)
event_ledger = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(event_ledger)

dashboard = event_ledger.dashboard


def _write_progress(root: Path) -> None:
    (root / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | raw | 剧本改编 | 配音 | 分镜设计 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |",
            ]
        ),
        encoding="utf-8",
    )


def test_audit_writes_hash_chain_and_reports_trace_warning(tmp_path: Path) -> None:
    event = dashboard.make_event(
        "第1集",
        "image",
        "generation",
        source="unit",
        cost={"amount": 1.2, "unit": "credits", "provider": "gpt-image"},
        generation={"asset": "出图/第1集/图片/Clip_01.png", "status": "pass", "attempt": 1},
    )
    pdir = tmp_path / "生产数据"
    pdir.mkdir()
    (pdir / "production_events.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    payload = event_ledger.audit(str(tmp_path), write=True)

    assert payload["status"] == "warn"
    assert payload["event_count"] == 1
    assert payload["hash_chain_head"]
    assert (pdir / "production_events_audit.json").is_file()
    chain = [json.loads(line) for line in (pdir / "production_events_chain.jsonl").read_text(encoding="utf-8").splitlines()]
    assert chain[0]["episode"] == "第1集"
    assert chain[0]["prev_hash"] == "0" * 64
    assert "trace" in payload["event_warnings"][0]["warnings"][0]
    assert payload["trace_summary"]["missing_trace_id"] == 1


def test_audit_strict_trace_fails_missing_trace_id(tmp_path: Path) -> None:
    event = dashboard.make_event(
        "第1集",
        "image",
        "generation",
        source="unit",
        generation={"asset": "出图/第1集/图片/Clip_01.png", "status": "pass", "attempt": 1},
    )
    pdir = tmp_path / "生产数据"
    pdir.mkdir()
    (pdir / "production_events.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    payload = event_ledger.audit(str(tmp_path), strict_trace=True)

    assert payload["status"] == "fail"
    assert payload["trace_errors"]


def test_audit_fails_on_bad_jsonl_and_missing_required_fields(tmp_path: Path) -> None:
    pdir = tmp_path / "生产数据"
    pdir.mkdir()
    (pdir / "production_events.jsonl").write_text(
        '{"kind":"n2d_production_event","version":1}\n{bad\n',
        encoding="utf-8",
    )

    payload = event_ledger.audit(str(tmp_path))

    assert payload["status"] == "fail"
    assert payload["line_errors"]
    assert payload["event_errors"]
    assert any("episode" in item for item in payload["event_errors"][0]["errors"])


def test_replay_rebuilds_dashboard_from_events(tmp_path: Path) -> None:
    _write_progress(tmp_path)
    pdir = tmp_path / "生产数据"
    pdir.mkdir()
    event = dashboard.make_event(
        "第1集",
        "video",
        "generation",
        source="unit",
        duration_sec=12,
        cost={"amount": 2, "unit": "credits", "provider": "veo"},
        generation={"asset": "出视频/第1集/视频/Clip_01.mp4", "status": "pass", "attempt": 1},
        meta={"trace_id": "t-1"},
    )
    (pdir / "production_events.jsonl").write_text(json.dumps(event, ensure_ascii=False) + "\n", encoding="utf-8")

    payload = event_ledger.replay(str(tmp_path), write=True)

    assert payload["status"] == "pass"
    ep1 = next(item for item in payload["dashboard"]["episodes"] if item["episode"] == "第1集")
    assert ep1["cost_totals"]["credits"] == 2
    assert (pdir / "dashboard_replay.json").is_file()


def _emit(pdir, events):
    with open(pdir / "production_events.jsonl", "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _ev(ts, stage="image"):
    return {"kind": "n2d_production_event", "version": 1, "ts": ts, "episode": "第1集",
            "stage": stage, "event": "cost", "source": "unit", "trace_id": ts, "cost": {"CNY": 1}}


def test_replay_matches_dashboard_after_stripping_generated_at(tmp_path: Path) -> None:
    pdir = tmp_path / "生产数据"; pdir.mkdir()
    evs = [_ev("2026-06-26T08:00:00+08:00"), _ev("2026-06-26T09:00:00+08:00", "video")]
    _emit(pdir, evs)
    data = dashboard.aggregate_events(str(tmp_path), evs)
    (pdir / dashboard.DASHBOARD_JSON).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    rep = event_ledger.replay(str(tmp_path))
    # 剥 generated_at 后内容一致 → 复现校验真通过（旧版因易变字段恒 False）
    assert rep["matches_current_dashboard"] is True


def test_chain_anchor_detects_history_rewrite_and_delete(tmp_path: Path) -> None:
    pdir = tmp_path / "生产数据"; pdir.mkdir()
    evs = [_ev("2026-06-26T08:00:00+08:00"), _ev("2026-06-26T09:00:00+08:00", "video")]
    _emit(pdir, evs)
    a1 = event_ledger.audit(str(tmp_path), write=True)
    assert a1["chain_tamper"] is None and (pdir / event_ledger.ANCHOR_JSON).is_file()
    # append 新事件 = append-only，不报篡改
    evs.append(_ev("2026-06-26T10:00:00+08:00", "compose"))
    _emit(pdir, evs)
    assert event_ledger.audit(str(tmp_path), write=True)["chain_tamper"] is None
    # 改写历史第1条 → 篡改检出 + status fail
    evs[0]["cost"] = {"CNY": 999}
    _emit(pdir, evs)
    a3 = event_ledger.audit(str(tmp_path), write=True)
    assert a3["status"] == "fail" and a3["chain_tamper"] is not None
