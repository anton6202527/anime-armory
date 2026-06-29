#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, "..", "_lib"))
CRAFT = os.path.abspath(os.path.join(HERE, "..", "..", "novel-craft", "scripts"))
for path in (LIB, CRAFT, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

import pipeline_runner  # noqa: E402
from novel_pipeline import (  # noqa: E402
    applicable_stages,
    artifact_graph,
    dry_run_plan,
    handoff_contract,
    registry_payload,
)
from provenance import append_event, read_events  # noqa: E402


def test_registry_declares_three_layer_pipeline_contract():
    payload = registry_payload()
    stages = {stage["key"]: stage for stage in payload["stages"]}

    assert payload["kind"] == "novel_pipeline_registry"
    assert {"setup", "draft", "review", "score", "revision", "screen_ready"} <= set(stages)
    assert stages["draft"]["can_parallel"] is True
    assert stages["revision"]["semantic_required"] is False
    assert payload["agent_layer"]["workflow_orchestrator"]["may_call_models"] is False
    assert payload["agent_layer"]["specialist_score"]["may_call_models"] is True


def test_dry_run_writes_plan_and_provenance():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
            f.write("# 设置\n")
        with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
            f.write("# 进度\n")

        plan = dry_run_plan(root)
        assert plan["next_stage"] == "blueprint"
        by_key = {stage["key"]: stage for stage in plan["stages"]}
        assert by_key["setup"]["status"] == "done"
        assert by_key["blueprint"]["status"] == "ready"

        json_path, md_path = pipeline_runner.write_plan(root, plan)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        events = read_events(root)
        assert events[-1]["event_type"] == "pipeline_plan_written"
        assert {item["path"] for item in events[-1]["outputs"]} == {
            "生产数据/novel_pipeline_plan.json",
            "生产数据/novel_pipeline_plan.md",
        }


def test_missing_project_kind_defaults_to_create_without_source_import():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "原创旧项目"}, f, ensure_ascii=False)
        for name in ("_设置.md", "_进度.md"):
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write("# ok\n")

        plan = dry_run_plan(root)
        keys = [stage["key"] for stage in plan["stages"]]
        assert plan["project_kind"] == "create"
        assert "source_import" not in keys
        assert plan["next_stage"] == "blueprint"


def test_legacy_source_artifacts_keep_source_import_stage():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "小说"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "源书旧项目"}, f, ensure_ascii=False)
        with open(os.path.join(root, "原作.txt"), "w", encoding="utf-8") as f:
            f.write("源书正文\n")
        with open(os.path.join(root, "小说", "source_manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"rights": "public-domain"}, f, ensure_ascii=False)

        plan = dry_run_plan(root)
        keys = [stage["key"] for stage in plan["stages"]]
        assert plan["project_kind"] == "import"
        assert "source_import" in keys


def test_explicit_derived_kind_keeps_source_import_without_artifacts():
    stages = applicable_stages({"kind": "rewrite"})
    assert any(stage["key"] == "source_import" for stage in stages)


def test_pipeline_run_state_machine_claims_and_completes_stage():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        for name in ("_设置.md", "_进度.md"):
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write("# ok\n")

        run = pipeline_runner.create_run(root, actor="orchestrator")
        assert run["next_stage"] == "blueprint"
        by_key = {stage["key"]: stage for stage in run["stages"]}
        assert by_key["setup"]["status"] == "completed"
        assert by_key["blueprint"]["status"] == "pending"

        claimed = pipeline_runner.update_run_stage(
            root, run["run_id"], "blueprint", "claimed", actor="writer-agent"
        )
        by_key = {stage["key"]: stage for stage in claimed["stages"]}
        assert by_key["blueprint"]["status"] == "running"
        assert by_key["blueprint"]["attempts"] == 1
        assert by_key["blueprint"]["claimed_by"] == "writer-agent"

        completed = pipeline_runner.update_run_stage(root, run["run_id"], "blueprint", "completed")
        by_key = {stage["key"]: stage for stage in completed["stages"]}
        assert by_key["blueprint"]["status"] == "completed"


def test_artifact_graph_marks_changed_outputs_stale():
    with tempfile.TemporaryDirectory() as root:
        meta = os.path.join(root, "_meta.json")
        with open(meta, "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        append_event(root, event_type="fixture_seeded", tool="test", outputs=[meta])
        with open(meta, "w", encoding="utf-8") as f:
            json.dump({"title": "测试书改", "kind": "create"}, f, ensure_ascii=False)

        graph = artifact_graph(root)
        stale = {item["pattern"]: item for item in graph["stale_artifacts"]}
        assert "_meta.json" in stale
        assert stale["_meta.json"]["files"] == ["_meta.json"]


def test_handoff_contract_bounds_specialist_agent():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)

        contract = handoff_contract(root, "blueprint")
        assert contract["kind"] == "novel_specialist_handoff_contract"
        assert contract["agent_role"] == "specialist_writer"
        assert contract["required_return"]["stage_key"] == "blueprint"
        assert "bypass_gate_without_waiver" in contract["forbidden_actions"]


def test_complete_stage_warns_when_disk_does_not_support_completion():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        for name in ("_设置.md", "_进度.md"):
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write("# ok\n")
        run = pipeline_runner.create_run(root, actor="orchestrator")
        # blueprint 无 设定/蓝图.md → artifact 视图非 done；标 completed 应记 warning（不静默接受）
        completed = pipeline_runner.update_run_stage(root, run["run_id"], "blueprint", "completed")
        by_key = {s["key"]: s for s in completed["stages"]}
        assert by_key["blueprint"]["status"] == "completed"
        assert by_key["blueprint"].get("completion_warning")


def test_dry_run_plan_flags_progress_disagreement():
    from novel_pipeline import dry_run_plan
    with tempfile.TemporaryDirectory() as root:
        def w(p, c):
            os.makedirs(os.path.join(root, os.path.dirname(p)) or root, exist_ok=True)
            with open(os.path.join(root, p), "w", encoding="utf-8") as f:
                f.write(c if isinstance(c, str) else json.dumps(c, ensure_ascii=False))
        w("_meta.json", {"title": "对账", "kind": "create", "target_chapters": 1})
        w("_设置.md", "# 设置\n")
        w("_进度.md", "# 进度\n\n| 章节 | 正文初稿 | 机检 |\n|---|---|---|\n| 第01章 | ☐ | ☐ |\n")
        for f in ("设定/蓝图.md", "设定/角色卡.md", "设定/世界观.md", "设定/读者契约.md",
                  "设定/章纲.md", "章节/第01章.md", "写作任务/第01章.md"):
            w(f, "# x\n")
        w("审稿/demo_gate.json", {"passed": True})
        plan = dry_run_plan(root)
        recon = plan.get("progress_reconciliation") or []
        assert any(r["type"] == "progress_disagreement" for r in recon)
