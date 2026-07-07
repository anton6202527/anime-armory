from __future__ import annotations

import csv
import importlib.util
import json
import os
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
    assert payload["findings"][0]["severity"] == "block"
    assert payload["findings"][0]["sev"] == "block"
    assert payload["findings"][0]["dimension"] == "角色一致性"
    assert payload["findings"][0]["dim"] == "角色一致性"
    assert payload["findings"][0]["message"] == "崩脸"
    assert payload["findings"][0]["msg"] == "崩脸"
    assert payload["findings"][0]["dim_key"] == "character_consistency"
    assert payload["auto_return_tasks"][0]["return_to_stage"] == "image"
    assert payload["auto_return_tasks"][0]["affected_shots"] == ["Clip_03"]


def test_make_event_promotes_trace_context_from_meta() -> None:
    event = dashboard.make_event(
        "第1集",
        "image",
        "manual",
        meta={"task_id": "001-image-progress", "idempotency_key": "idem-1"},
    )

    assert event["trace"]["trace_id"] == "idem-1"
    assert event["trace"]["task_id"] == "001-image-progress"
    assert event["trace"]["idempotency_key"] == "idem-1"


def test_gate_noise_and_false_positive_recovery_rollup(tmp_path: Path) -> None:
    root = tmp_path
    write_storyboard(root)
    events = [
        dashboard.make_event("第1集", "image", "generation", generation={"status": "pass"}),
        dashboard.make_event("第1集", "video", "generation", generation={"status": "fail"}),
        dashboard.make_event("第1集", "image", "qa", qa={"severity": "warn", "dim": "角色", "msg": "轻微漂移"}),
        dashboard.make_event("第1集", "video", "qa", qa={"severity": "block", "dim": "口型", "msg": "不同步"}),
        dashboard.make_event("第1集", "video", "waiver", meta={"waiver": "false_positive", "reason": "误报"}),
    ]

    data = dashboard.aggregate_events(str(root), events)
    ep1 = next(item for item in data["episodes"] if item["episode"] == "第1集")
    totals = data["totals"]
    md = dashboard.render_markdown(data)

    assert ep1["warnings_per_attempt"] == 0.5
    assert ep1["blockers_per_attempt"] == 0.5
    assert ep1["false_positive_recoveries"] == 1
    assert ep1["false_positive_recovery_rate"] == 0.5
    assert totals["warnings_per_attempt"] == 0.5
    assert totals["blockers_per_attempt"] == 0.5
    assert totals["false_positive_recovery_rate"] == 0.5
    assert "Gate 噪声" in md and "误报回收率" in md


def test_image_preflight_gate_events_merge_image_qc(monkeypatch, tmp_path: Path) -> None:
    class Proc:
        returncode = 0
        stdout = "[]"
        stderr = ""

    class ImageQc:
        Path = Path
        HARD_LINT_CODES = ("unknown_char_id",)
        PROHIBITED_FACE_PATCH_LABEL = "本地贴脸修复产物禁用"

        @staticmethod
        def lint_prompts(root: Path, episode: str) -> dict:
            return {"findings": [{"level": "block", "code": "unknown_char_id", "msg": "bad CHAR_id"}]}

        @staticmethod
        def prohibited_face_patch_outputs(root: Path, episode: str) -> dict:
            return {"outputs": []}

    monkeypatch.setattr(dashboard.subprocess, "run", lambda *args, **kwargs: Proc())
    monkeypatch.setattr(dashboard, "load_image_qc_module", lambda: ImageQc)

    events, code, findings = dashboard.gate_events(str(tmp_path), "第1集", "image_preflight")

    assert code == 1
    assert findings == [{
        "sev": "block",
        "dim": "image_prompt_lint",
        "loc": None,
        "msg": "bad CHAR_id",
        "return_to_stage": "image",
    }]
    assert events[0]["stage"] == "image_preflight"
    assert events[0]["qa_gate"]["blocks"] == 1


def test_dashboard_passively_reads_consistency_ledger(tmp_path: Path) -> None:
    root = tmp_path
    write_progress(root)
    path = root / "生产数据" / "consistency_ledger_第1集.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": "n2d_consistency_ledger",
        "counts": {"block": 1, "high": 0, "medium": 1},
        "delivery_surface": {"status": "blocked"},
        "rows": [
            {"id": "CHAR_01", "name": "沈念", "kind": "character", "overall": "block"},
            {"id": "PROP_01", "name": "铜镜", "kind": "prop", "overall": "medium"},
        ],
    }, ensure_ascii=False), encoding="utf-8")

    data = dashboard.aggregate_events(str(root), [])
    ep1 = next(item for item in data["episodes"] if item["episode"] == "第1集")
    markdown = dashboard.render_markdown(data)

    assert ep1["consistency_ledger"]["counts"]["block"] == 1
    assert ep1["consistency_ledger"]["delivery_surface"]["status"] == "blocked"
    assert data["totals"]["consistency_ledger_counts"]["medium"] == 1
    assert "## 验收总账" in markdown
    assert "沈念(block)" in markdown


def test_resolvable_asset_path_accepts_repo_relative_root_prefixed_path(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    root = workspace / "创作区" / "制漫剧" / "项目"
    asset = root / "合成" / "第1集" / "成片_第1集_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"x")
    monkeypatch.chdir(workspace)

    raw = os.path.relpath(asset, workspace)

    assert dashboard.resolvable_asset_path(str(root), raw) == str(asset)


def test_image_qc_findings_reruns_degraded_report(monkeypatch, tmp_path: Path) -> None:
    report_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    report_dir.mkdir(parents=True)
    prompt = tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("## Clip 01\n", encoding="utf-8")
    (report_dir / "image_qc_第1集.json").write_text(
        json.dumps({
            "qc_environment": {"precision_level": "none"},
            "checks": {},
            "lint": {"findings": []},
            "inputs_fingerprint": dashboard.artifact_fingerprint(
                str(tmp_path),
                ["出图/第1集/prompt/01_分镜出图.md"],
            ),
        }),
        encoding="utf-8",
    )

    class Proc:
        returncode = 0
        stdout = '[{"sev":"block","dim":"出图落档QC","msg":"rerun degraded"}]'
        stderr = ""

    monkeypatch.setattr(dashboard.subprocess, "run", lambda *args, **kwargs: Proc())
    findings = dashboard.run_image_qc_findings(str(tmp_path), "第1集", fail_closed=True)

    assert findings == [{"sev": "block", "dim": "出图落档QC", "msg": "rerun degraded"}]


def test_image_qc_findings_uses_configured_python(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    class Proc:
        returncode = 0
        stdout = "[]"
        stderr = ""

    def _run(args, **_kwargs):
        captured["args"] = args
        return Proc()

    monkeypatch.setenv("N2D_IMAGE_QC_PYTHON", "/envs/facefusion/bin/python")
    monkeypatch.setattr(dashboard.subprocess, "run", _run)

    findings = dashboard.run_image_qc_findings(str(tmp_path), "第1集", fail_closed=True)

    assert findings == []
    assert captured["args"][0] == "/envs/facefusion/bin/python"


def test_image_qc_findings_prefers_existing_full_report(monkeypatch, tmp_path: Path) -> None:
    report_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    report_dir.mkdir(parents=True)
    prompt = tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("## Clip 01\n", encoding="utf-8")
    (report_dir / "image_qc_第1集.json").write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "checks": {},
            "lint": {"findings": []},
            "summary": {"hard_blocks": 0},
            "inputs_fingerprint": dashboard.artifact_fingerprint(
                str(tmp_path),
                ["出图/第1集/prompt/01_分镜出图.md"],
            ),
        }),
        encoding="utf-8",
    )

    def _unexpected_run(*_args, **_kwargs):
        raise AssertionError("should not rerun image_qc when a full report exists")

    monkeypatch.setattr(dashboard.subprocess, "run", _unexpected_run)
    findings = dashboard.run_image_qc_findings(str(tmp_path), "第1集", fail_closed=True)

    assert findings == []


def test_image_qc_findings_rejects_missing_declared_pngs(monkeypatch, tmp_path: Path) -> None:
    report_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    report_dir.mkdir(parents=True)
    missing_png = "出图/第1集/图片/Clip_01.png"
    (report_dir / "image_qc_第1集.json").write_text(
        json.dumps({
            "qc_environment": {"precision_level": "none"},
            "checks": {},
            "inputs_fingerprint": dashboard.artifact_fingerprint(str(tmp_path), [missing_png]),
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    def _unexpected_module():
        raise AssertionError("must not convert a report whose declared episode PNG is missing")

    monkeypatch.setattr(dashboard, "load_image_qc_module", _unexpected_module)
    findings = dashboard.run_image_qc_findings(str(tmp_path), "第1集", fail_closed=True)

    assert len(findings) == 1
    assert findings[0]["sev"] == "block"
    assert "尚未落档" in findings[0]["msg"]
    assert missing_png in findings[0]["msg"]


def test_image_qc_findings_reruns_stale_report(monkeypatch, tmp_path: Path) -> None:
    report_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    report_dir.mkdir(parents=True)
    prompt = tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("old", encoding="utf-8")
    fp = dashboard.artifact_fingerprint(str(tmp_path), ["出图/第1集/prompt/01_分镜出图.md"])
    prompt.write_text("new", encoding="utf-8")
    (report_dir / "image_qc_第1集.json").write_text(
        json.dumps({"qc_environment": {"precision_level": "full"}, "inputs_fingerprint": fp}),
        encoding="utf-8",
    )

    class Proc:
        returncode = 0
        stdout = '[{"sev":"block","dim":"出图落档QC","msg":"rerun"}]'
        stderr = ""

    monkeypatch.setattr(dashboard.subprocess, "run", lambda *args, **kwargs: Proc())
    findings = dashboard.run_image_qc_findings(str(tmp_path), "第1集", fail_closed=True)

    assert findings == [{"sev": "block", "dim": "出图落档QC", "msg": "rerun"}]


def test_image_qc_findings_accepts_noisy_stdout(monkeypatch, tmp_path: Path) -> None:
    class Proc:
        returncode = 0
        stdout = "onnxruntime provider warning\nfind model: buffalo_l\n" \
                 '[{"sev":"block","dim":"出图落档QC","msg":"rerun"}]\n'
        stderr = ""

    monkeypatch.setattr(dashboard.subprocess, "run", lambda *args, **kwargs: Proc())
    findings = dashboard.run_image_qc_findings(str(tmp_path), "第1集", fail_closed=True)

    assert findings == [{"sev": "block", "dim": "出图落档QC", "msg": "rerun"}]


def test_image_qc_findings_reruns_report_missing_prop_confirmation_dependency(monkeypatch, tmp_path: Path) -> None:
    report_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    report_dir.mkdir(parents=True)
    prompt = tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("current", encoding="utf-8")
    (report_dir / "image_qc_第1集.json").write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "checks": {},
            "lint": {"findings": []},
            "prop_shape_review": {
                "total": 1,
                "pending": 1,
                "targets": [{"asset": "PROP_01", "png": "图片/Clip_01.png", "confirmed": False}],
            },
            "inputs_fingerprint": dashboard.artifact_fingerprint(
                str(tmp_path),
                ["出图/第1集/prompt/01_分镜出图.md"],
            ),
        }),
        encoding="utf-8",
    )

    class Proc:
        returncode = 0
        stdout = "[]"
        stderr = ""

    monkeypatch.setattr(dashboard.subprocess, "run", lambda *args, **kwargs: Proc())
    findings = dashboard.run_image_qc_findings(str(tmp_path), "第1集", fail_closed=True)

    assert findings == []


def test_image_preflight_uses_lint_only_not_pixel_qc(monkeypatch, tmp_path: Path) -> None:
    class ImageQc:
        Path = Path
        HARD_LINT_CODES = ("unknown_char_id",)
        PROHIBITED_FACE_PATCH_LABEL = "本地贴脸修复产物禁用"

        @staticmethod
        def lint_prompts(root: Path, episode: str) -> dict:
            return {"findings": [{"level": "block", "code": "unknown_char_id", "msg": "bad CHAR_id"}]}

        @staticmethod
        def prohibited_face_patch_outputs(root: Path, episode: str) -> dict:
            return {"outputs": []}

    def fail_if_full_qc_runs(*args, **kwargs):
        raise AssertionError("image_preflight must not run side-effectful full image_qc")

    monkeypatch.setattr(dashboard, "load_image_qc_module", lambda: ImageQc)
    monkeypatch.setattr(dashboard, "image_qc_findings", fail_if_full_qc_runs)
    monkeypatch.setattr(dashboard, "run_image_qc_findings", fail_if_full_qc_runs)

    findings = dashboard.image_preflight_qc_findings(str(tmp_path), "第1集")
    assert findings == [{
        "sev": "block",
        "dim": "image_prompt_lint",
        "loc": None,
        "msg": "bad CHAR_id",
        "return_to_stage": "image",
    }]


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
    assert ep1["generation_pass_rate"] == 0.5
    assert ep1["deliverable_pass_rate"] == 0.0
    assert ep1["final_pass_rate"] == 0.0
    assert ep1["progress_next_stage"] == "出图"


def test_aggregate_blocks_missing_latest_pass_deliverable(tmp_path: Path) -> None:
    write_progress(tmp_path)
    asset = "出图/第1集/图片/Clip_01.png"
    events = [
        dashboard.make_event(
            "第1集",
            "image",
            "generation",
            generation={"asset": asset, "status": "pass"},
        )
    ]

    result = dashboard.aggregate_events(str(tmp_path), events)
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")

    assert ep1["generation_passes"] == 1
    assert ep1["qa_blockers"] == 1
    assert ep1["deliverable_pass_rate"] == 0.0
    assert ep1["missing_deliverables"][0]["asset"] == asset


def test_aggregate_does_not_block_existing_latest_pass_deliverable(tmp_path: Path) -> None:
    write_progress(tmp_path)
    asset = "出图/第1集/图片/Clip_01.png"
    path = tmp_path / asset
    path.parent.mkdir(parents=True)
    path.write_bytes(b"png")
    events = [
        dashboard.make_event(
            "第1集",
            "image",
            "generation",
            generation={"asset": asset, "status": "pass"},
        )
    ]

    result = dashboard.aggregate_events(str(tmp_path), events)
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")

    assert ep1["qa_blockers"] == 0
    assert ep1["missing_deliverables"] == []


def test_aggregate_passively_counts_fresh_standalone_image_qc(tmp_path: Path) -> None:
    write_progress(tmp_path)
    report_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    report_dir.mkdir(parents=True)
    prompt = tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("## Clip 01\n", encoding="utf-8")
    (report_dir / "image_qc_第1集.json").write_text(
        json.dumps({
            "summary": {"hard_blocks": 2, "advisory": 3},
            "inputs_fingerprint": dashboard.artifact_fingerprint(
                str(tmp_path),
                ["出图/第1集/prompt/01_分镜出图.md"],
            ),
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    result = dashboard.aggregate_events(str(tmp_path), [])
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")

    assert ep1["qa_blockers"] == 2
    assert ep1["qa_warnings"] == 3
    assert ep1["consistency_blockers"] == 2
    assert ep1["image_qc_passive"]["freshness"] == "fresh"


def test_aggregate_blocks_stale_standalone_image_qc(tmp_path: Path) -> None:
    write_progress(tmp_path)
    report_dir = tmp_path / "生产数据" / "image_qc" / "第1集"
    report_dir.mkdir(parents=True)
    prompt = tmp_path / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("old", encoding="utf-8")
    fp = dashboard.artifact_fingerprint(str(tmp_path), ["出图/第1集/prompt/01_分镜出图.md"])
    prompt.write_text("new", encoding="utf-8")
    (report_dir / "image_qc_第1集.json").write_text(
        json.dumps({"summary": {"hard_blocks": 0, "advisory": 0}, "inputs_fingerprint": fp}, ensure_ascii=False),
        encoding="utf-8",
    )

    result = dashboard.aggregate_events(str(tmp_path), [])
    ep1 = next(item for item in result["episodes"] if item["episode"] == "第1集")

    assert ep1["qa_blockers"] == 1
    assert ep1["image_qc_passive"]["freshness"] == "stale"


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


def test_waiver_command_records_auditable_event(tmp_path: Path) -> None:
    """逃生口/闸门放行写一条 waiver 事件——执行时「松动」从静默变成 dashboard 可审计留痕。"""
    rc = dashboard.main([
        "waiver", str(tmp_path),
        "--episode", "第1集", "--stage", "image",
        "--waiver", "skip-final-gate", "--reason", "operator override",
        "--scope", "第1集", "--no-build",
    ])
    assert rc == 0
    events = dashboard.load_events(str(tmp_path))
    waivers = [e for e in events if e.get("event") == "waiver"]
    assert len(waivers) == 1
    w = waivers[0]
    assert w["stage"] == "image"
    assert w["meta"]["waiver"] == "skip-final-gate"
    assert w["meta"]["reason"] == "operator override"
    # waiver 事件不带 generation/cost/qa，build 聚合必须无害容忍（不计入一次通过率/重抽率）
    result = dashboard.build(str(tmp_path), write=False)
    assert result["totals"]["generation_attempts"] == 0


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


# ── 成本预检（forecast）单测 ──

def test_forecast_episode_cost_pure():
    assert dashboard.forecast_episode_cost({"CNY": 6.0}, 5.0) == {"CNY": 30.0}
    assert dashboard.forecast_episode_cost({"CNY": 6.0, "USD": 1.0}, 2.0) == {"CNY": 12.0, "USD": 2.0}
    assert dashboard.forecast_episode_cost({}, 5.0) == {}           # 无历史单价
    assert dashboard.forecast_episode_cost({"CNY": 6.0}, 0) == {}    # 无计划时长
    assert dashboard.forecast_episode_cost({"CNY": 0}, 5.0) == {}    # 单价为0忽略


def test_affordable_episode_count_pure():
    assert dashboard.affordable_episode_count(100.0, 30.0) == 3
    assert dashboard.affordable_episode_count(20.0, 30.0) == 0
    assert dashboard.affordable_episode_count(100.0, 0) is None      # 单集成本未知
    assert dashboard.affordable_episode_count(100.0, -1) is None


def test_top_redraw_leak_pure():
    leak = dashboard.top_redraw_leak({"崩脸": 5, "构图": 2, "字幕": 0, "其它": 8}, top=2)
    assert leak == [("其它", 8), ("崩脸", 5)]                         # 按次数降序，0 次剔除
    assert dashboard.top_redraw_leak({}) == []


def test_anchor_plan_budget_reads_sidecar(tmp_path: Path) -> None:
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "anchor_plan_第2集.json").write_text(json.dumps({
        "kind": "n2d_anchor_plan",
        "episode": "第2集",
        "summary": {
            "clips_planned": 7,
            "total_anchors": 9,
            "added_images": 9,
            "added_video_segments": 3,
        },
    }, ensure_ascii=False), encoding="utf-8")

    out = dashboard.anchor_plan_budget(str(tmp_path), "第2集")

    assert out["available"] is True
    assert out["added_images"] == 9
    assert out["added_video_segments"] == 3


def test_anchor_plan_budget_missing_warns(tmp_path: Path) -> None:
    out = dashboard.anchor_plan_budget(str(tmp_path), "第2集")
    assert out["available"] is False
    assert "缺 anchor_plan" in out["note"]


def test_cmd_forecast_end_to_end(tmp_path, capsys):
    root = str(tmp_path)
    # 历史：第1集 已完成 1 分钟、花 12 CNY → ¥12/min；外加一次崩脸重抽
    # （直接构造事件，绕开 CLI 与进度解析，只验 forecast 逻辑）
    dashboard.append_events(root, [
        dashboard.make_event("第1集", "image", "generation",
                             cost={"amount": 12, "unit": "CNY", "currency": "CNY", "provider": "x"},
                             generation={"status": "pass"},
                             release={"runtime_sec": 60}),
        dashboard.make_event("第1集", "video", "redraw",
                             generation={"status": "fail", "redraw_reason": "崩脸重抽"}),
    ])
    # 第2集计划时长 120s = 2 分钟
    sb = tmp_path / "脚本" / "第2集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"total_duration": 120}), encoding="utf-8")

    rc = dashboard.main(["forecast", root, "第2集", "--budget", "100", "--unit", "CNY", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["planned_min"] == 2.0
    assert out["cost_per_finished_min"] == {"CNY": 12.0}
    assert out["forecast_cost"] == {"CNY": 24.0}            # 12 ¥/min × 2 min
    assert out["anchor_plan"]["available"] is False
    assert out["budget"]["over_budget"] is False
    assert out["budget"]["more_episodes_affordable"] == 4   # 100 // 24
    assert any(x["category"] for x in out["redraw_leak_top"])  # 重抽漏点滚出来了


def test_cmd_forecast_no_history_graceful(tmp_path, capsys):
    # 无历史成本：不臆造，给 note + planned_min，仍 rc=0
    sb = tmp_path / "脚本" / "第1集"
    sb.mkdir(parents=True)
    (sb / "storyboard.json").write_text(json.dumps({"total_duration": 90}), encoding="utf-8")
    rc = dashboard.main(["forecast", str(tmp_path), "第1集", "--json"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["forecast_cost"] == {}
    assert any("无历史成本" in n for n in out["notes"])


def test_image_qc_findings_graceful_on_bad_root(tmp_path: Path) -> None:
    # 空目录无出图产物/prompt → image_qc 正常返回空 findings；helper 必返回 list、绝不抛、不阻断 gate
    out = dashboard.image_qc_findings(str(tmp_path), "第1集")
    assert isinstance(out, out.__class__) and isinstance(out, list)
    assert all(isinstance(f, dict) for f in out)


# ── ④ 跨集角色一致性 KPI（读 identity_drift_report，软门不阻断）──
def test_identity_kpi_flags_declining_and_blocked_character():
    report = {
        "available": True,
        "characters": {
            "王敦": {
                "episodes": {
                    "第1集": {"ok": 4, "warn": 0, "block": 0, "mean_score": 0.75},
                    "第2集": {"ok": 2, "warn": 1, "block": 1, "mean_score": 0.55},
                },
                "total_warn": 1, "total_block": 1, "first_bad_episode": "第2集",
            },
            "柳娘子": {  # 稳定且 mean_score 微升 → 不算漂
                "episodes": {
                    "第1集": {"ok": 5, "warn": 0, "block": 0, "mean_score": 0.80},
                    "第2集": {"ok": 5, "warn": 0, "block": 0, "mean_score": 0.81},
                },
                "total_warn": 0, "total_block": 0, "first_bad_episode": "",
            },
        },
    }
    kpi = dashboard.identity_consistency_kpi(report)
    assert kpi["available"] is True
    assert kpi["characters_tracked"] == 2
    assert kpi["characters_drifting"] == 1
    assert kpi["earliest_systemic_episode"] == "第2集"
    assert kpi["degrade"] is True
    wang = next(r for r in kpi["rows"] if r["character"] == "王敦")
    assert wang["significant"] is True and wang["trend"]["declining"] is True
    liu = next(r for r in kpi["rows"] if r["character"] == "柳娘子")
    assert liu["significant"] is False


def test_identity_kpi_stable_when_no_drift():
    report = {"available": True, "characters": {
        "沈念": {"episodes": {"第1集": {"ok": 6, "warn": 0, "block": 0, "mean_score": 0.78}},
                 "total_warn": 0, "total_block": 0, "first_bad_episode": ""}}}
    kpi = dashboard.identity_consistency_kpi(report)
    assert kpi["degrade"] is False and kpi["characters_drifting"] == 0


def test_identity_kpi_empty_report_unavailable():
    kpi = dashboard.identity_consistency_kpi({"available": True, "characters": {}})
    assert kpi["available"] is False


def test_cost_keys_split_by_quality_tier():
    # 带 quality_tier 的成本事件按 provider@tier:unit 拆桶；无 tier 维持旧键（老事件零影响）
    assert dashboard.cost_keys({"unit": "USD", "provider": "seedance", "quality_tier": "fast"}) == (
        "USD", "seedance@fast:USD")
    assert dashboard.cost_keys({"unit": "USD", "provider": "seedance", "quality_tier": "pro"}) == (
        "USD", "seedance@pro:USD")
    assert dashboard.cost_keys({"unit": "USD", "provider": "seedance"}) == ("USD", "seedance:USD")


def test_cost_keys_fold_urgency_tier():
    # G8：batch_24h 时效档加 #后缀拆 realtime vs batch 成本；realtime（默认）不污染旧键
    assert dashboard.cost_keys({"unit": "USD", "provider": "seedance", "urgency_tier": "batch_24h"}) == (
        "USD", "seedance#batch_24h:USD")
    assert dashboard.cost_keys({"unit": "USD", "provider": "seedance", "quality_tier": "fast", "urgency_tier": "batch_24h"}) == (
        "USD", "seedance@fast#batch_24h:USD")
    # realtime / 缺省 → 维持旧键，老事件零影响
    assert dashboard.cost_keys({"unit": "USD", "provider": "seedance", "urgency_tier": "realtime"}) == (
        "USD", "seedance:USD")
