from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("dashboard.py")
spec = importlib.util.spec_from_file_location("dashboard", SCRIPT)
dashboard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(dashboard)


def write_progress(root: Path) -> None:
    (root / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | raw | 剧本改编 | 配音 | 分镜设计 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | ✅ | ✅ | ✅ | ✅ | ✅ | 1/2 | ⬜ | ⬜ | ⬜ |",
                "| 第2集 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )


def write_storyboard(root: Path, episode: str = "第1集", duration: float = 60.0) -> None:
    path = root / "脚本" / episode / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "episode": 1,
                "total_duration": duration,
                "clips": [{"id": "Clip_01", "duration": duration}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_platform_metrics(root: Path, rows: list[dict[str, object]]) -> None:
    path = root / "生产数据" / "platform_metrics.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def test_gate_findings_payload_is_batch_compatible(tmp_path: Path) -> None:
    payload = dashboard.gate_findings_payload(str(tmp_path), "第1集", "image", [
        {
            "sev": "block",
            "dim": "角色一致性",
            "loc": "Clip_03",
            "msg": "崩脸",
            "return_to_stage": "image",
            "affected_shots": ["Clip_03"],
        }
    ])
    assert payload["kind"] == "n2d_consistency_findings"
    assert payload["findings"][0]["dim_key"] == "character_consistency"
    assert payload["auto_return_tasks"][0]["return_to_stage"] == "image"
    assert payload["auto_return_tasks"][0]["affected_shots"] == ["Clip_03"]


def test_aggregate_generation_cost_redraw_and_qa(tmp_path: Path) -> None:
    write_progress(tmp_path)
    events = [
        dashboard.make_event(
            "第1集",
            "image",
            "generation",
            cost={"amount": 0.2, "currency": "USD", "unit": "USD", "provider": "codex"},
            duration_sec=30,
            generation={"asset": "Clip_01.png", "status": "pass"},
        ),
        dashboard.make_event(
            "第1集",
            "image",
            "redraw",
            cost={"amount": 0.1, "currency": "USD", "unit": "USD", "provider": "codex"},
            duration_sec=20,
            generation={"asset": "Clip_02.png", "status": "fail", "redraw_reason": "脸漂移"},
        ),
        dashboard.make_event(
            "第1集",
            "image",
            "qa_gate",
            qa={"severity": "block", "dim": "角色一致性", "loc": "Clip_02", "msg": "脸漂移"},
        ),
        dashboard.make_event(
            "第1集",
            "image",
            "qa_gate",
            qa={"severity": "warn", "dim": "场景", "loc": "Clip_01", "msg": "光位轻微跳"},
        ),
    ]

    result = dashboard.aggregate_events(str(tmp_path), events)
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")

    assert ep1["generation_attempts"] == 2
    assert ep1["generation_passes"] == 1
    assert ep1["generation_fails"] == 1
    assert ep1["redraw_count"] == 1
    assert ep1["redraw_reasons"] == {"脸漂移": 1}
    assert ep1["qa_blockers"] == 1
    assert ep1["qa_warnings"] == 1
    assert ep1["cost_totals"] == {"USD": 0.3}
    assert ep1["duration_sec"] == 50
    assert ep1["final_pass_rate"] == 0.5
    assert ep1["progress_next_stage"] == "出图"


def test_append_and_build_writes_dashboard_files(tmp_path: Path) -> None:
    write_progress(tmp_path)
    event = dashboard.make_event(
        "1",
        "video",
        "generation",
        duration_sec=10,
        generation={"asset": "Clip_01.mp4", "status": "pass"},
    )

    dashboard.append_events(str(tmp_path), [event])
    result = dashboard.build(str(tmp_path), write=True)

    prod = tmp_path / "生产数据"
    assert (prod / "production_events.jsonl").is_file()
    assert (prod / "dashboard.json").is_file()
    assert (prod / "dashboard.md").is_file()
    assert result["totals"]["generation_attempts"] == 1
    assert "n2d 生产数据仪表盘" in (prod / "dashboard.md").read_text(encoding="utf-8")
    assert (prod / "production_events.lock").exists()
    assert [p for p in prod.iterdir() if ".tmp." in p.name] == []


def test_gate_replace_predicate_keeps_latest_stage_events(tmp_path: Path) -> None:
    write_progress(tmp_path)
    old_gate = dashboard.make_event(
        "第1集",
        "image",
        "qa_gate",
        source="n2d-review/scripts/gate.py",
        qa={"severity": "block", "dim": "旧阻断", "loc": "old", "msg": "old"},
    )
    manual = dashboard.make_event(
        "第1集",
        "image",
        "generation",
        generation={"asset": "Clip_01.png", "status": "pass"},
    )
    new_gate = dashboard.make_event(
        "第1集",
        "image",
        "qa_gate",
        source="n2d-review/scripts/gate.py",
        qa={"severity": "warn", "dim": "新警告", "loc": "new", "msg": "new"},
    )
    dashboard.write_events(str(tmp_path), [old_gate, manual])
    dashboard.replace_events(
        str(tmp_path),
        lambda event: (
            event.get("episode") == "第1集"
            and event.get("stage") == "image"
            and event.get("source") == "n2d-review/scripts/gate.py"
            and event.get("event") in {"qa_gate", "qa_gate_run"}
        ),
        [new_gate],
    )

    events = dashboard.load_events(str(tmp_path))
    assert [event["event"] for event in events] == ["generation", "qa_gate"]
    assert events[1]["qa"]["dim"] == "新警告"


def test_roi_metrics_cost_per_min_first_pass_redraw_and_recoup(tmp_path: Path) -> None:
    write_progress(tmp_path)
    write_storyboard(tmp_path, "第1集", duration=60.0)
    write_platform_metrics(
        tmp_path,
        [
            {
                "episode": "第1集",
                "plays": 1000,
                "revenue": 20,
                "distribution_spend": 5,
                "currency": "CNY",
                "duration_sec": 60,
            }
        ],
    )
    events = [
        dashboard.make_event(
            "第1集",
            "image",
            "generation",
            cost={"amount": 6, "currency": "CNY", "unit": "CNY", "provider": "codex"},
            duration_sec=100,
            generation={"asset": "Clip_01.png", "attempt": 1, "status": "pass"},
        ),
        dashboard.make_event(
            "第1集",
            "video",
            "redraw",
            cost={"amount": 3, "currency": "CNY", "unit": "CNY", "provider": "seedance"},
            duration_sec=50,
            generation={"asset": "Clip_02.mp4", "attempt": 1, "status": "fail", "redraw_reason": "动作漂"},
        ),
        dashboard.make_event(
            "第1集",
            "video",
            "generation",
            cost={"amount": 3, "currency": "CNY", "unit": "CNY", "provider": "seedance"},
            duration_sec=60,
            generation={"asset": "Clip_02.mp4", "attempt": 2, "status": "pass"},
        ),
    ]

    result = dashboard.aggregate_events(str(tmp_path), events)
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")
    totals = result["totals"]

    assert ep1["runtime_sec"] == 60
    assert ep1["cost_totals"] == {"CNY": 12.0}
    assert ep1["cost_per_finished_min"] == {"CNY": 12.0}
    assert ep1["one_pass_rate"] == round(1 / 3, 4)
    assert ep1["redraw_rate"] == round(1 / 3, 4)
    assert ep1["release_revenue_totals"] == {"CNY": 20.0}
    assert ep1["release_spend_totals"] == {"CNY": 5.0}
    assert ep1["release_net_totals"] == {"CNY": 15.0}
    assert ep1["recoup_ratio"] == {"CNY": 1.25}
    assert totals["cost_per_finished_min"] == {"CNY": 12.0}
    assert totals["recoup_ratio"] == {"CNY": 1.25}


def test_one_pass_rate_does_not_count_summarized_multi_attempt_pass(tmp_path: Path) -> None:
    write_progress(tmp_path)
    events = [
        dashboard.make_event(
            "第1集",
            "image",
            "generation",
            generation={"asset": "Clip_01.png", "attempts": 3, "status": "pass"},
        )
    ]

    result = dashboard.aggregate_events(str(tmp_path), events)
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")

    assert ep1["generation_attempts"] == 3
    assert ep1["one_pass_count"] == 0
    assert ep1["one_pass_rate"] == 0.0


def _seed_events(root: Path) -> None:
    events = [
        dashboard.make_event("第1集", "image", "generation", generation={"status": "pass", "attempt": 1}),
        dashboard.make_event("第1集", "image", "generation", generation={"status": "fail", "attempt": 1}),
        dashboard.make_event("第1集", "image", "cost", cost={"amount": 12.0, "currency": "CNY", "unit": "CNY", "provider": "codex"}),
        dashboard.make_event("第1集", "image", "qa_gate", qa={"severity": "block", "dim": "角色一致性", "msg": "脸漂"}),
    ]
    dashboard.append_events(str(root), events)


def test_default_thresholds_alert_on_qa_blockers_only(tmp_path: Path) -> None:
    # 默认阈值：只有 QA 阻断开箱即告；成本/通过率默认 None 不误报。
    _seed_events(tmp_path)
    db = dashboard.build(str(tmp_path), write=True)
    kinds = {a["kind"] for a in db["alerts"]}
    assert "qa_blockers" in kinds
    assert "final_pass_rate" not in kinds  # 默认 floor=None
    assert "budget" not in kinds            # 默认 cap=None
    assert db["alert_counts"]["critical"] >= 1
    assert (tmp_path / "生产数据" / "alerts.json").is_file()
    assert (tmp_path / "生产数据" / "alerts.md").is_file()


def test_thresholds_json_triggers_passrate_and_budget(tmp_path: Path) -> None:
    pdir = tmp_path / "生产数据"
    pdir.mkdir(parents=True)
    (pdir / "alert_thresholds.json").write_text(
        json.dumps({"final_pass_rate_floor": 0.8, "budget_cap": 10.0, "redraw_rate_ceiling": 0.3}),
        encoding="utf-8",
    )
    _seed_events(tmp_path)
    db = dashboard.build(str(tmp_path), write=True)
    kinds = {a["kind"] for a in db["alerts"]}
    assert {"qa_blockers", "final_pass_rate", "budget"} <= kinds
    assert any(a["level"] == "critical" and a["kind"] == "budget" for a in db["alerts"])


def test_thresholds_from_settings_md(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "# _设置\n\n## 选择\n- 告警通过率下限: 80%\n- 告警预算上限: 10\n", encoding="utf-8"
    )
    th = dashboard.load_thresholds(str(tmp_path))
    assert th["final_pass_rate_floor"] == 0.8
    assert th["budget_cap"] == 10.0


def test_no_alert_flag_skips_alert_files(tmp_path: Path) -> None:
    _seed_events(tmp_path)
    db = dashboard.build(str(tmp_path), write=True, alerts=False)
    assert "alerts" not in db
    assert not (tmp_path / "生产数据" / "alerts.json").exists()


def test_watch_once_rebuilds_and_writes_html(tmp_path: Path) -> None:
    _seed_events(tmp_path)
    rc = dashboard.main(["watch", str(tmp_path), "--once"])
    assert rc == 0
    assert (tmp_path / "生产数据" / "dashboard.html").is_file()
    assert (tmp_path / "生产数据" / "alerts.json").is_file()


def test_build_fail_on_critical_exit_code(tmp_path: Path) -> None:
    _seed_events(tmp_path)
    rc = dashboard.main(["build", str(tmp_path), "--fail-on-critical"])
    assert rc == 3  # 默认 QA 阻断 = critical


def test_redraw_category_classification_and_totals(tmp_path: Path) -> None:
    """重抽原因分维度：自由文本读时归类 + 显式合法 category 尊重 + 显式非法回退归类 + totals 汇总。"""
    write_progress(tmp_path)
    events = [
        # 自由文本 → 关键词归类 face_consistency
        dashboard.make_event(
            "第1集", "image", "redraw",
            generation={"asset": "a.png", "status": "fail", "redraw_reason": "第3镜沈念崩脸"},
        ),
        # 显式合法 category：尊重，不按文本归类
        dashboard.make_event(
            "第1集", "image", "redraw",
            generation={"asset": "b.png", "status": "fail",
                        "redraw_reason": "看着不舒服", "redraw_category": "scene_drift"},
        ),
        # 显式非法 category：回退到文本归类（道具 → prop_structure）
        dashboard.make_event(
            "第2集", "image", "redraw",
            generation={"asset": "c.png", "status": "fail",
                        "redraw_reason": "法宝道具结构错了", "redraw_category": "not_a_category"},
        ),
        # 归不进任何类 → other
        dashboard.make_event(
            "第2集", "image", "redraw",
            generation={"asset": "d.png", "status": "fail", "redraw_reason": "随便重抽一下"},
        ),
    ]
    result = dashboard.aggregate_events(str(tmp_path), events)
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")
    ep2 = next(item for item in result["episodes"] if item["episode"] == "第2集")
    assert ep1["redraw_categories"] == {"face_consistency": 1, "scene_drift": 1}
    assert ep2["redraw_categories"] == {"prop_structure": 1, "other": 1}
    assert result["totals"]["redraw_categories"] == {
        "face_consistency": 1, "scene_drift": 1, "prop_structure": 1, "other": 1,
    }
    # markdown 渲染含分维度小节与一致性小计
    md = dashboard.render_markdown(result)
    assert "重抽原因分维度" in md
    assert "一致性小计" in md


# ── T10: 一致性审查事件接通（写而不读修复）─────────────────────────────────────
def test_consistency_findings_event_counts_and_folds_into_qa_blockers(tmp_path: Path) -> None:
    write_progress(tmp_path)
    events = [
        dashboard.make_event(
            "第1集", "review", "consistency_findings",
            source="n2d-review/scripts/consistency_audit.py",
            meta={"total_block": 2, "total_warn": 3, "finding_count": 5},
        ),
    ]
    result = dashboard.aggregate_events(str(tmp_path), events)
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")
    assert ep1["consistency_blockers"] == 2 and ep1["consistency_warnings"] == 3
    assert ep1["qa_blockers"] == 2   # 折入 qa_blockers，阈值告警/总账看得到审查检出
    totals = result["totals"]
    assert totals["consistency_blockers"] == 2 and totals["consistency_warnings"] == 3
