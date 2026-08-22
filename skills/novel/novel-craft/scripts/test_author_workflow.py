#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import author_workflow
import exploration
from craft_profile import build_craft_contract_snapshot
from novel_pipeline import record_human_stage_approval


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def touch(path, text="x\n"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def test_manuscript_map_status_rejects_stale_profile_check(tmp_path):
    root = str(tmp_path)
    touch(os.path.join(root, "_设置.md"), "# 设置\n- 创作工艺档：genre_novel\n")
    write_json(os.path.join(root, "设定", "scene_cards.json"), {
        "kind": "novel_scene_cards",
        "scenes": [],
    })
    touch(os.path.join(root, "设定", "manuscript_map.json"), "{}\n")
    write_json(os.path.join(root, "设定", "manuscript_map_check.json"), {
        "kind": "novel_manuscript_map_check",
        "passed": True,
        "blocking": 0,
        "findings": [],
        "source_snapshot": build_craft_contract_snapshot(root, "genre_novel"),
    })
    assert author_workflow.manuscript_map_status(root) == (True, [])

    touch(os.path.join(root, "_设置.md"), "# 设置\n- 创作工艺档：literary\n")
    ok, blockers = author_workflow.manuscript_map_status(root)

    assert ok is False
    assert any("已过期" in item and "craft_profile_changed" in item for item in blockers)


def test_author_workflow_reports_next_step_and_writes_artifacts():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        touch(os.path.join(root, "_设置.md"), "# 设置\n文本主创模式：AI辅助\n")
        touch(os.path.join(root, "_进度.md"), "# 进度\n")

        payload = author_workflow.build_workflow(root)
        assert payload["kind"] == "novel_author_workflow"
        assert payload["current_step"] == "blueprint"
        assert payload["steps"][0]["status"] == "done"

        json_path, md_path = author_workflow.write_workflow(root, payload)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)


def test_author_workflow_surfaces_valid_exploration_without_advancing_formal_stages():
    with tempfile.TemporaryDirectory() as base:
        root = os.path.join(base, "project")
        source = os.path.join(base, "probe.md")
        write_json(os.path.join(root, "_meta.json"), {"title": "探索中的书", "kind": "create"})
        touch(os.path.join(root, "_设置.md"), "# 设置\n文本主创模式：AI辅助\n")
        touch(os.path.join(root, "_进度.md"), "# 进度\n- 当前阶段：初始化\n")
        touch(source, "# 角色试镜\n\n她在没人看见时仍然把钥匙还了回去。\n")
        formal_before = {
            rel: read_bytes(os.path.join(root, rel))
            for rel in ("_meta.json", "_设置.md", "_进度.md")
        }

        seed = exploration.capture_human_seed(
            root,
            text="一个人真正的选择发生在无人注视时。",
            author="作者",
            human_first_confirmed=True,
        )
        draft = exploration.register_draft(
            root,
            source_file=source,
            title="归还钥匙",
            exploration_kind="character_audition",
            creator="作者",
            authorship="human",
            seed_ids=[seed["seed_id"]],
        )
        exploration.record_decision(
            root,
            draft_id=draft["draft_id"],
            decision="promote_candidate",
            expected_sha256=draft["sha256"],
            reviewer="作者",
            reason="角色在无人监督时仍作出代价更高的选择",
            target="blueprint",
        )

        payload = author_workflow.build_workflow(root)
        exploration_step = next(step for step in payload["steps"] if step["key"] == "exploration")
        blueprint_step = next(step for step in payload["steps"] if step["key"] == "blueprint")
        assert exploration_step["status"] == "done"
        assert exploration_step["summary"]["integrity_ok"] is True
        assert exploration_step["summary"]["human_first_seed_count"] == 1
        assert exploration_step["summary"]["draft_count"] == 1
        assert exploration_step["summary"]["candidate_count"] == 1
        assert any("候选不会自动完成" in item for item in exploration_step["warnings"])
        assert blueprint_step["status"] == "pending"
        assert payload["current_step"] == "blueprint"
        rendered = author_workflow.render_markdown(payload)
        assert "human-first seed=1" in rendered
        assert "探索稿=1" in rendered
        assert "晋升候选=1" in rendered

        for rel, expected in formal_before.items():
            assert read_bytes(os.path.join(root, rel)) == expected
        assert not os.path.exists(os.path.join(root, "章节"))
        assert not os.path.exists(os.path.join(root, "审稿"))
        assert not os.path.exists(os.path.join(root, "设定"))


def test_author_workflow_blocks_tampered_exploration_sidecar_without_formal_writes():
    with tempfile.TemporaryDirectory() as base:
        root = os.path.join(base, "project")
        source = os.path.join(base, "probe.md")
        write_json(os.path.join(root, "_meta.json"), {"title": "损坏的探索区", "kind": "create"})
        touch(os.path.join(root, "_设置.md"), "# 设置\n")
        touch(os.path.join(root, "_进度.md"), "# 进度\n- 当前阶段：初始化\n")
        touch(source, "# POV 试写\n\n他只记得门关上的声音。\n")
        seed = exploration.capture_human_seed(
            root,
            text="想写一次被误记的告别。",
            author="作者",
            human_first_confirmed=True,
        )
        draft = exploration.register_draft(
            root,
            source_file=source,
            title="门声",
            exploration_kind="pov_probe",
            creator="作者",
            authorship="human",
            seed_ids=[seed["seed_id"]],
        )
        formal_before = {
            rel: read_bytes(os.path.join(root, rel))
            for rel in ("_meta.json", "_设置.md", "_进度.md")
        }
        sidecar = os.path.join(root, draft["metadata_path"].replace("/", os.sep))
        with open(sidecar, "a", encoding="utf-8") as f:
            f.write("\n")

        payload = author_workflow.build_workflow(root)
        exploration_step = next(step for step in payload["steps"] if step["key"] == "exploration")
        assert exploration_step["status"] == "pending"
        assert exploration_step["summary"]["integrity_ok"] is False
        assert any("完整性损坏" in item for item in exploration_step["blockers"])
        assert payload["current_step"] == "exploration"
        assert "探索区完整性损坏" in author_workflow.render_markdown(payload)

        for rel, expected in formal_before.items():
            assert read_bytes(os.path.join(root, rel)) == expected
        assert not os.path.exists(os.path.join(root, "章节"))
        assert not os.path.exists(os.path.join(root, "审稿"))
        assert not os.path.exists(os.path.join(root, "设定"))


def test_author_workflow_does_not_treat_blueprint_scaffold_as_stage_approval():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "kind": "create"})
        for rel in ["_设置.md", "_进度.md", "设定/创作蓝图.md", "设定/读者契约.md"]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "设定", "author_intent.json"), {
            "kind": "novel_author_intent",
            "core_theme": "选择会留下后果",
            "non_negotiables": ["不替作者决定结局"],
        })

        payload = author_workflow.build_workflow(root)
        blueprint = next(step for step in payload["steps"] if step["key"] == "blueprint")
        assert blueprint["status"] == "pending"
        assert "--approve-stage blueprint" in blueprint["command"]
        assert "--delegated" in blueprint["command"]
        assert any("尚未记录阶段批准" in item for item in blueprint["blockers"])

        record_human_stage_approval(
            root, "blueprint", approved_by="author", note="确认人物、主题与方向"
        )
        blueprint = next(
            step for step in author_workflow.build_steps(root) if step["key"] == "blueprint"
        )
        assert blueprint["status"] == "done"


def test_author_workflow_reaches_release_when_manifest_ready():
    with tempfile.TemporaryDirectory() as root:
        for rel in ["_设置.md", "_进度.md", "设定/创作蓝图.md", "设定/读者契约.md", "设定/角色卡.md"]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书"})
        write_json(os.path.join(root, "设定", "author_intent.json"), {
            "kind": "novel_author_intent",
            "core_theme": "信任需要承担代价",
            "non_negotiables": ["主角不牺牲无辜者换胜利"],
        })
        record_human_stage_approval(
            root, "blueprint", approved_by="author", note="确认蓝图与读者契约"
        )
        write_json(os.path.join(root, "设定", "scene_cards.json"), {"kind": "novel_scene_cards", "scenes": []})
        write_json(os.path.join(root, "审稿", "demo_gate.json"), {"status": "passed"})
        touch(os.path.join(root, "章节", "第01章.md"))
        write_json(os.path.join(root, "审稿", "state_ledger.json"), {"chapter_deltas": {}})
        write_json(os.path.join(root, "审稿", "review_report.json"), {"findings": []})
        write_json(os.path.join(root, "评分", "reader_telemetry_summary.json"), {"weakest_chapters": []})
        write_json(os.path.join(root, "修订", "edit_plan.json"), {"tasks": []})
        for rel in ["修订/editorial_letter.md", "修订/style_sheet.md", "修订/proof_checklist.md"]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "导出", "release_manifest.json"), {"release_ready": True})

        payload = author_workflow.build_workflow(root)
        # evidence 是非阻断 warning，导航应继续到第一个真正 pending 的步骤。
        assert payload["current_step"] == "setting_scene"
        evidence_step = [s for s in payload["steps"] if s["key"] == "evidence"][0]
        assert evidence_step["status"] == "warning"


def test_author_workflow_reads_blockers_from_reports():
    with tempfile.TemporaryDirectory() as root:
        for rel in [
            "_设置.md",
            "_进度.md",
            "设定/创作蓝图.md",
            "设定/读者契约.md",
            "设定/角色卡.md",
            "资料/research_sources.json",
        ]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        write_json(os.path.join(root, "设定", "scene_cards.json"), {"kind": "novel_scene_cards", "scenes": []})
        write_json(os.path.join(root, "审稿", "demo_gate.json"), {"status": "passed"})
        touch(os.path.join(root, "章节", "第01章.md"))
        write_json(os.path.join(root, "审稿", "state_ledger.json"), {"chapter_deltas": {}})
        write_json(os.path.join(root, "审稿", "review_report.json"), {
            "summary": {"blocking_count": 1, "verdict": "needs_work"},
            "findings": [{"blocking": True, "problem": "主线冲突未成立"}],
        })
        write_json(os.path.join(root, "评分", "score_report.json"), {
            "production_decision": {"decision": "revise"},
            "verdict": "小改",
        })

        payload = author_workflow.build_workflow(root)
        review_step = [s for s in payload["steps"] if s["key"] == "review_score"][0]
        assert review_step["status"] == "pending"
        assert any("review_report" in item or "主线冲突" in item for item in review_step["blockers"])
        md = author_workflow.render_markdown(payload)
        assert "阻断" in md
        assert "主线冲突未成立" in md


def test_author_workflow_accepts_scoped_reader_data_waiver():
    with tempfile.TemporaryDirectory() as root:
        for rel in [
            "_设置.md",
            "_进度.md",
            "设定/创作蓝图.md",
            "设定/读者契约.md",
            "设定/角色卡.md",
            "资料/research_sources.json",
        ]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书", "purpose": "商业连载", "target_platform": "番茄"})
        touch(os.path.join(root, "_设置.md"), "# 设置\n- 发布档：data_validated_launch\n")
        write_json(os.path.join(root, "设定", "scene_cards.json"), {"kind": "novel_scene_cards", "scenes": []})
        write_json(os.path.join(root, "审稿", "demo_gate.json"), {"status": "passed"})
        touch(os.path.join(root, "章节", "第01章.md"))
        write_json(os.path.join(root, "审稿", "state_ledger.json"), {"chapter_deltas": {}})
        write_json(os.path.join(root, "审稿", "review_report.json"), {"summary": {"blocking_count": 0}, "findings": []})
        write_json(os.path.join(root, "评分", "score_report.json"), {"production_decision": {"decision": "go"}, "verdict": "pass"})
        write_json(os.path.join(root, "评分", "reader_test_plan.json"), {"kind": "novel_reader_test_plan"})
        with open(os.path.join(root, "审稿", "waiver_log.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "type": "reader_data_missing",
                "reason": "封闭项目无读者数据。",
                "scope": {"release_profile": "data_validated_launch"},
            }, ensure_ascii=False) + "\n")

        payload = author_workflow.build_workflow(root)
        reader_step = [s for s in payload["steps"] if s["key"] == "reader_validation"][0]
        assert reader_step["status"] == "warning"
        assert reader_step["blockers"] == []
        assert "waiver" in reader_step["warnings"][0]


def test_commercial_publish_without_reader_telemetry_is_market_warning_only():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {
            "title": "测试书", "purpose": "商业连载", "target_platform": "番茄",
        })
        touch(os.path.join(root, "_设置.md"), "# 设置\n")
        payload = author_workflow.build_workflow(root)
        reader_step = next(step for step in payload["steps"] if step["key"] == "reader_validation")
        assert reader_step["status"] == "warning"
        assert reader_step["blockers"] == []
        assert any("不是发布合规" in warning for warning in reader_step["warnings"])
        assert payload["current_step"] != "reader_validation"


def test_data_validated_launch_release_command_preserves_selected_profile():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {
            "title": "测试书", "release_profile": "data_validated_launch",
        })
        touch(os.path.join(root, "_设置.md"), "# 设置\n")
        release = next(step for step in author_workflow.build_steps(root) if step["key"] == "release")
        assert "--release-profile data_validated_launch" in release["command"]


def test_derived_project_uses_its_real_blueprint_contract():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "续写书", "kind": "continue"})
        for rel in ["_设置.md", "_进度.md", "设定/续写方向.md", "设定/末章状态.md", "设定/读者契约.md"]:
            touch(os.path.join(root, rel))
        write_json(os.path.join(root, "设定", "author_intent.json"), {
            "kind": "novel_author_intent",
            "core_theme": "承诺需要兑现",
            "non_negotiables": ["不推翻原作结局"],
        })
        record_human_stage_approval(
            root, "blueprint", approved_by="author", note="确认续写方向与末章状态"
        )

        steps = author_workflow.build_steps(root)
        blueprint = next(step for step in steps if step["key"] == "blueprint")
        assert blueprint["status"] == "done"
        assert "设定/续写方向.md" in blueprint["evidence"]
        assert "设定/末章状态.md" in blueprint["evidence"]
        assert "设定/创作蓝图.md" not in blueprint["evidence"]


def test_draft_loop_requires_target_chapter_count_when_declared():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "三章书", "target_chapters": 3})
        touch(os.path.join(root, "章节", "第01章.md"))
        write_json(os.path.join(root, "审稿", "state_ledger.json"), {"chapter_deltas": {}})

        draft = next(step for step in author_workflow.build_steps(root) if step["key"] == "draft_loop")
        assert draft["status"] == "warning"
        assert any("1/3" in warning for warning in draft["warnings"])

        touch(os.path.join(root, "章节", "第02章.md"))
        touch(os.path.join(root, "章节", "第03章.md"))
        draft = next(step for step in author_workflow.build_steps(root) if step["key"] == "draft_loop")
        assert draft["status"] == "done"


def test_author_workflow_blocks_open_editor_queries():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书"})
        write_json(os.path.join(root, "修订", "edit_plan.json"), {"tasks": []})
        for rel in ["修订/editorial_letter.md", "修订/style_sheet.md", "修订/proof_checklist.md"]:
            touch(os.path.join(root, rel))
        os.makedirs(os.path.join(root, "修订"), exist_ok=True)
        with open(os.path.join(root, "修订", "editor_queries.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "query_id": "QUERY-001",
                "task_id": "EDIT-001",
                "status": "open",
                "question": "结局是否保留牺牲？",
            }, ensure_ascii=False) + "\n")

        payload = author_workflow.build_workflow(root)
        edit_step = [s for s in payload["steps"] if s["key"] == "edit"][0]
        assert edit_step["status"] == "pending"
        assert "editor query" in edit_step["blockers"][0]


def test_author_workflow_blocks_authenticity_read_only_when_explicitly_required():
    with tempfile.TemporaryDirectory() as root:
        write_json(os.path.join(root, "_meta.json"), {"title": "测试书"})
        touch(os.path.join(root, "章节", "第01章.md"), "正文\n")
        write_json(os.path.join(root, "修订", "edit_plan.json"), {"tasks": []})
        for rel in ["修订/editorial_letter.md", "修订/style_sheet.md", "修订/proof_checklist.md"]:
            touch(os.path.join(root, rel))
        auth_path = os.path.join(root, "修订", "authenticity_read.json")
        payload = {
            "kind": "novel_authenticity_read",
            "required_for_release": True,
            "status": "planned",
            "findings": [{"id": "AUTH-001", "severity": "major", "status": "open"}],
        }
        write_json(auth_path, payload)

        edit_step = next(step for step in author_workflow.build_steps(root) if step["key"] == "edit")
        assert edit_step["status"] == "pending"
        assert any("真实性/文化审读" in item for item in edit_step["blockers"])
        assert "authenticity_read.py check" in edit_step["command"]

        payload["required_for_release"] = False
        write_json(auth_path, payload)
        edit_step = next(step for step in author_workflow.build_steps(root) if step["key"] == "edit")
        assert edit_step["status"] == "done"
        assert edit_step["blockers"] == []
        assert any("可选咨询" in item for item in edit_step["warnings"])
