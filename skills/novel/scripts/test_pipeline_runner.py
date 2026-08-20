#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.abspath(os.path.join(HERE, "..", "_lib"))
CRAFT = os.path.abspath(os.path.join(HERE, "..", "novel-craft", "scripts"))
for path in (LIB, CRAFT, HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

import pipeline_runner  # noqa: E402
from craft_profile import build_craft_contract_snapshot  # noqa: E402
from novel_pipeline import (  # noqa: E402
    applicable_stages,
    artifact_graph,
    dry_run_plan,
    evaluate_stage,
    handoff_contract,
    record_human_stage_approval,
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
        assert plan["next_stage"] == "author_workflow"
        by_key = {stage["key"]: stage for stage in plan["stages"]}
        assert by_key["setup"]["status"] == "done"
        assert by_key["author_workflow"]["status"] == "ready"
        assert by_key["author_intent"]["status"] == "ready"
        assert by_key["blueprint"]["status"] == "blocked"

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
        assert plan["next_stage"] == "author_workflow"


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


def test_kind_specific_blueprint_and_outline_contracts_use_real_artifacts():
    expected = {
        "create": (["设定/创作蓝图.md"], ["设定/角色卡.md", "设定/读者契约.md"]),
        "rewrite": (["设定/改动spec.md"], ["设定/角色卡.md", "设定/读者契约.md"]),
        "continue": (["设定/续写方向.md", "设定/末章状态.md"], ["设定/人物.md", "设定/读者契约.md"]),
        "expand": (["设定/事件骨架.json", "设定/章节映射.md"], ["设定/人物.md", "设定/读者契约.md"]),
        "condense": (["设定/主线骨架.json", "设定/章节映射.md"], ["设定/人物.md", "设定/读者契约.md"]),
        "spinoff": (["设定/锚点表.json"], ["设定/角色卡.md", "设定/读者契约.md"]),
    }
    for kind, (blueprint_outputs, outline_inputs) in expected.items():
        by_key = {stage["key"]: stage for stage in applicable_stages({"kind": kind})}
        assert by_key["blueprint"]["outputs"] == blueprint_outputs
        assert by_key["outline"]["inputs"] == outline_inputs


def test_source_import_accepts_original_text_without_manifest():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "原作.txt"), "w", encoding="utf-8") as f:
            f.write("已由派生项目初始化器落盘的源书正文。\n")
        stage = next(s for s in applicable_stages({"kind": "continue"}) if s["key"] == "source_import")
        evaluated = evaluate_stage(root, stage)
        assert evaluated["status"] == "done"


def test_pipeline_rejects_stale_manuscript_map_check(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# 设置\n- 创作工艺档：genre_novel\n")
    with open(os.path.join(root, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_scene_cards", "scenes": []}, f)
    with open(os.path.join(root, "设定", "manuscript_map.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_manuscript_map"}, f)
    with open(os.path.join(root, "设定", "manuscript_map.md"), "w", encoding="utf-8") as f:
        f.write("# map\n")
    with open(os.path.join(root, "设定", "manuscript_map_check.json"), "w", encoding="utf-8") as f:
        json.dump({
            "kind": "novel_manuscript_map_check",
            "passed": True,
            "blocking": 0,
            "findings": [],
            "source_snapshot": build_craft_contract_snapshot(root, "genre_novel"),
        }, f)
    stage = next(s for s in applicable_stages({"kind": "create"}) if s["key"] == "manuscript_map")
    assert evaluate_stage(root, stage)["status"] == "done"

    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# 设置\n- 创作工艺档：experimental\n")
    stale = evaluate_stage(root, stage)

    assert stale["status"] == "blocked"
    assert any("来源已过期" in item for item in stale["gate_blockers"])


def test_blueprint_requires_hash_bound_human_approval_and_reapproval_after_edit():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        with open(os.path.join(root, "设定", "author_intent.json"), "w", encoding="utf-8") as f:
            json.dump({
                "core_theme": "选择",
                "non_negotiables": ["不替用户决定"],
            }, f, ensure_ascii=False)
        blueprint_path = os.path.join(root, "设定", "创作蓝图.md")
        with open(blueprint_path, "w", encoding="utf-8") as f:
            f.write("# 创作蓝图\n已由作者复核的内容。\n")
        stage = next(s for s in applicable_stages({"kind": "create"}) if s["key"] == "blueprint")

        before = evaluate_stage(root, stage)
        assert before["status"] == "ready"
        assert before["human_approval"]["approved"] is False

        approval_path, _record = record_human_stage_approval(
            root, "blueprint", approved_by="author", note="作者确认方向与不可妥协项"
        )
        assert os.path.exists(approval_path)
        approved = evaluate_stage(root, stage)
        assert approved["status"] == "done"
        assert approved["human_approval"]["approved"] is True

        with open(blueprint_path, "a", encoding="utf-8") as f:
            f.write("方向发生实质修改。\n")
        stale = evaluate_stage(root, stage)
        assert stale["status"] == "ready"
        assert "重新人工复核" in stale["human_approval"]["message"]


def test_human_approval_requires_complete_inputs_and_expires_when_input_changes():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        with open(os.path.join(root, "设定", "创作蓝图.md"), "w", encoding="utf-8") as f:
            f.write("# 创作蓝图\n")

        try:
            record_human_stage_approval(
                root, "blueprint", approved_by="author", note="确认蓝图"
            )
        except ValueError as exc:
            assert "inputs are incomplete" in str(exc)
            assert "设定/author_intent.json" in str(exc)
        else:
            raise AssertionError("approval must reject an incomplete input set")

        intent_path = os.path.join(root, "设定", "author_intent.json")
        with open(intent_path, "w", encoding="utf-8") as f:
            json.dump({"core_theme": "选择", "non_negotiables": ["保留开放结局"]}, f, ensure_ascii=False)
        _path, record = record_human_stage_approval(
            root, "blueprint", approved_by="author", note="确认蓝图"
        )
        assert {item["path"] for item in record["input_snapshot"]} == {
            "_meta.json",
            "设定/author_intent.json",
        }

        with open(intent_path, "w", encoding="utf-8") as f:
            json.dump({"core_theme": "责任", "non_negotiables": ["保留开放结局"]}, f, ensure_ascii=False)
        stage = next(s for s in applicable_stages({"kind": "create"}) if s["key"] == "blueprint")
        stale = evaluate_stage(root, stage)
        assert stale["status"] == "ready"
        assert stale["human_approval"]["approved"] is False
        assert "输入已变化" in stale["human_approval"]["message"]


def test_setting_approval_expires_when_approved_blueprint_changes():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        blueprint_path = os.path.join(root, "设定", "创作蓝图.md")
        with open(blueprint_path, "w", encoding="utf-8") as f:
            f.write("# 创作蓝图\n第一版。\n")
        for name in ("设定圣经.md", "角色卡.md", "世界观.md", "读者契约.md"):
            with open(os.path.join(root, "设定", name), "w", encoding="utf-8") as f:
                f.write(f"# {name.removesuffix('.md')}\n")

        record_human_stage_approval(root, "setting", approved_by="author", note="确认设定")
        stage = next(s for s in applicable_stages({"kind": "create"}) if s["key"] == "setting")
        assert evaluate_stage(root, stage)["status"] == "done"

        with open(blueprint_path, "a", encoding="utf-8") as f:
            f.write("第二版。\n")
        stale = evaluate_stage(root, stage)
        assert stale["status"] == "ready"
        assert "输入已变化" in stale["human_approval"]["message"]


def test_edit_stage_blocks_only_explicitly_required_authenticity_read():
    with tempfile.TemporaryDirectory() as root:
        for rel in (
            "修订/edit_plan.json",
            "修订/editorial_letter.md",
            "修订/style_sheet.md",
            "修订/proof_checklist.md",
        ):
            path = os.path.join(root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if path.endswith(".json"):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"tasks": []}, f)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write("ok\n")
        auth_path = os.path.join(root, "修订", "authenticity_read.json")
        with open(auth_path, "w", encoding="utf-8") as f:
            json.dump({
                "kind": "novel_authenticity_read",
                "required_for_release": True,
                "status": "planned",
                "findings": [],
            }, f)
        stage = next(s for s in applicable_stages({"kind": "create"}) if s["key"] == "edit")

        blocked = evaluate_stage(root, stage)
        assert blocked["status"] == "blocked"
        assert any("authenticity_read" in item for item in blocked["gate_blockers"])

        with open(auth_path, "w", encoding="utf-8") as f:
            json.dump({
                "kind": "novel_authenticity_read",
                "required_for_release": False,
                "status": "planned",
                "findings": [],
            }, f)
        optional = evaluate_stage(root, stage)
        assert optional["status"] == "done"


def test_pipeline_run_state_machine_claims_and_completes_stage():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        for name in ("_设置.md", "_进度.md"):
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write("# ok\n")

        run = pipeline_runner.create_run(root, actor="orchestrator")
        assert run["next_stage"] == "author_workflow"
        by_key = {stage["key"]: stage for stage in run["stages"]}
        assert by_key["setup"]["status"] == "completed"
        assert by_key["author_workflow"]["status"] == "pending"
        assert by_key["author_intent"]["status"] == "pending"
        assert by_key["blueprint"]["status"] == "blocked"

        claimed = pipeline_runner.update_run_stage(
            root, run["run_id"], "author_workflow", "claimed", actor="orchestrator"
        )
        by_key = {stage["key"]: stage for stage in claimed["stages"]}
        assert by_key["author_workflow"]["status"] == "running"
        assert by_key["author_workflow"]["attempts"] == 1
        assert by_key["author_workflow"]["claimed_by"] == "orchestrator"

        os.makedirs(os.path.join(root, "生产数据"), exist_ok=True)
        for name in ("author_workflow.json", "作者成书流程.md"):
            with open(os.path.join(root, "生产数据", name), "w", encoding="utf-8") as f:
                f.write("{}" if name.endswith(".json") else "# 流程\n")
        completed = pipeline_runner.update_run_stage(root, run["run_id"], "author_workflow", "completed")
        by_key = {stage["key"]: stage for stage in completed["stages"]}
        assert by_key["author_workflow"]["status"] == "completed"


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


def test_complete_stage_rejects_unsupported_claim_and_force_requires_reason():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "kind": "create"}, f, ensure_ascii=False)
        for name in ("_设置.md", "_进度.md"):
            with open(os.path.join(root, name), "w", encoding="utf-8") as f:
                f.write("# ok\n")
        run = pipeline_runner.create_run(root, actor="orchestrator")
        # blueprint 无 设定/创作蓝图.md → 普通 complete 拒绝；显式 force 必须留理由。
        try:
            pipeline_runner.update_run_stage(root, run["run_id"], "blueprint", "completed")
            assert False, "unsupported completion should fail"
        except ValueError as exc:
            assert "artifact view" in str(exc)
        try:
            pipeline_runner.update_run_stage(root, run["run_id"], "blueprint", "force_completed")
            assert False, "force completion without reason should fail"
        except ValueError as exc:
            assert "requires --reason" in str(exc)
        completed = pipeline_runner.update_run_stage(
            root, run["run_id"], "blueprint", "force_completed",
            actor="editor", reason="作者明确跳过本轮蓝图门槛",
        )
        by_key = {s["key"]: s for s in completed["stages"]}
        assert by_key["blueprint"]["status"] == "completed"
        assert by_key["blueprint"]["completion_waiver"]["actor"] == "editor"


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
        for f in ("设定/创作蓝图.md", "设定/角色卡.md", "设定/世界观.md", "设定/读者契约.md",
                  "设定/章纲.md", "章节/第01章.md", "写作任务/第01章.md"):
            w(f, "# x\n")
        w("审稿/demo_gate.json", {"passed": True})
        plan = dry_run_plan(root)
        recon = plan.get("progress_reconciliation") or []
        assert any(r["type"] == "progress_disagreement" for r in recon)
