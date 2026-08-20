#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run.py（mv 单一入口编排器）tests。

Can run without pytest:
    python3 skills/mv/test_run.py
"""
import importlib.util
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location("mv_run_test", os.path.join(HERE, "run.py"))
run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run)


def read_text(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def make_project(root, plan_done=False):
    for sub in ("歌", "词", "节拍", "分镜", "出图/段落/图片"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    settings = dict(run.contract.DEFAULT_SETTINGS)
    settings.update({"字幕语言": "无字幕", "演唱口型": "关闭"})
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write(run.contract.settings_markdown("测试", settings))
    meta = {
        "title": "测试", "song_rights_status": "自有", "has_song": True,
        "has_lyrics": True, **run.contract.runtime_state_from_settings(settings),
    }
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    runtime = run.contract.runtime_state_from_settings(settings)
    stages = run.contract.workflow_stage_table(
        runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"],
    )
    done_before = "image" if plan_done else "plan"
    frontier_index = next(i for i, row in enumerate(stages) if row["key"] == done_before)
    rows = [
        (row["label"], row["owner"], "[x]" if i < frontier_index else "[ ]")
        for i, row in enumerate(stages)
    ]
    table = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in rows)
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write("# 进度\n\n## 制MV 阶段\n| 阶段 | skill | 状态 |\n|---|---|---|\n" + table + "\n")
    with open(os.path.join(root, "歌", "song.mp3"), "wb") as f:
        f.write(b"fake")
    with open(os.path.join(root, "词", "lyrics.md"), "w", encoding="utf-8") as f:
        f.write("[verse]\n一句歌词\n")
    with open(os.path.join(root, "节拍", "beatgrid.json"), "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 2, "kind": "mv_beatgrid", "song": "歌/song.mp3",
            "duration": 5,
            "source_audio_sha256": hashlib.sha256(b"fake").hexdigest(),
            "beats": [1, 2], "downbeats": [1],
            "sections": [{"section": "verse", "start": 0, "end": 5}],
            "timing_verified": True, "downbeats_verified": True,
            "sections_verified": True, "sections_complete": True,
            "timing_review": {"accepted": True, "reviewer": "节拍师", "notes": "逐拍与段落核验"},
        }, f, ensure_ascii=False)
    with open(os.path.join(root, "视觉蓝图.md"), "w", encoding="utf-8") as f:
        f.write("# 视觉蓝图\n")


def make_plan_receipts(root):
    settings = run.mv_utils.parse_settings(root)
    song = run.mv_utils.find_song(root)
    plan = {
        "schema_version": 3, "kind": "mv_clip_plan", "root_rel": ".", "title": "测试",
        "inputs_sha256": {
            "song": run.mv_utils.content_hash(song),
            "beatgrid": run.mv_utils.content_hash(os.path.join(root, "节拍", "beatgrid.json")),
            "lyrics": run.mv_utils.content_hash(os.path.join(root, "词", "lyrics.md")),
            "blueprint": run.mv_utils.content_hash(os.path.join(root, "视觉蓝图.md")),
            "alignment": "",
            "settings_plan": run.contract.plan_settings_digest(settings),
        },
        "clips": [{"clip_id": "Clip_001", "section": "verse", "start": 0, "end": 5,
                   "duration": 5, "selected_video_path": "", "transition": "cut",
                   "speed_mode": "none"}],
    }
    plan_path = os.path.join(root, "分镜", "clip_plan.json")
    with open(plan_path, "w", encoding="utf-8") as handle:
        json.dump(plan, handle, ensure_ascii=False)
    timeline = {
        "schema_version": 3, "kind": "mv_timeline_manifest", "root_rel": ".", "title": "测试",
        "song_path": "歌/song.mp3", "rate": 24,
        "audio_policy": "locked_master_song_only; generated_clip_audio_discarded",
        "beatgrid_path": "节拍/beatgrid.json",
        "source_clip_plan_sha256": run.mv_utils.content_hash(plan_path),
        "timebase": {"rate": 24, "unit": "frame", "quantized": True},
        "clips": [{"clip_id": "Clip_001", "section": "verse", "start": 0.0, "end": 5.0,
                   "duration": 5.0, "start_frame": 0, "end_frame": 120,
                   "duration_frames": 120, "video_path": "", "transition": "cut",
                   "speed_mode": "none", "seam_contract": {}}],
    }
    with open(os.path.join(root, "分镜", "timeline_manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(timeline, handle, ensure_ascii=False)


class NextActionTest(unittest.TestCase):
    def test_missing_progress_stops_with_init_hint(self):
        with tempfile.TemporaryDirectory() as tmp:
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "missing_progress")
            self.assertIn("init_project", action["action_card"]["exact_command"])

    def test_frontier_plan_ready_to_run_with_exact_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            action = run.build_next_action(tmp)
            self.assertEqual(action["frontier"]["key"], "plan")
            self.assertEqual(action["stop_reason"], "ready_to_run")
            self.assertIn("plan_clips.py", action["action_card"]["exact_command"])
            self.assertEqual(action["gate"]["errors"], [])

    def test_gate_error_becomes_blocked_by_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            with open(os.path.join(tmp, "视觉蓝图.md"), "w", encoding="utf-8") as f:
                f.write("- 状态：rough（待成品歌/beatgrid 复核）\n")
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "blocked_by_gate")
            self.assertTrue(any("rough" in e for e in action["gate"]["errors"]))

    def test_paid_frontier_marks_paid_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp, plan_done=True)
            with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
                json.dump({"clips": [{"clip_id": "Clip_001",
                                      "image_path": "出图/段落/图片/Clip_001.png"}]}, f)
            action = run.build_next_action(tmp)
            self.assertEqual(action["frontier"]["key"], "image")
            self.assertTrue(action["action_card"]["paid_or_irreversible"])

    def test_all_stop_reasons_in_stage_actions_registered(self):
        for key, (stop, _cmd, _paid) in run.STAGE_ACTIONS.items():
            self.assertIn(stop, run.STOP_REASONS, f"stage {key} 用了未登记停因 {stop}")

    def test_na_rejects_unregistered_stop_reason(self):
        with self.assertRaises(ValueError):
            run.na({"stop_reason": "made_up_reason"})

    def test_contract_stage_table_and_actions_are_complete(self):
        self.assertEqual(run.contract.validate_stage_table(run.STAGE_ACTIONS), [])

    def test_semantic_plan_is_explicit_agent_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            make_plan_receipts(tmp)
            text = read_text(os.path.join(tmp, "_进度.md"))
            text = text.replace(
                "| clip/timeline 规划 | mv-plan/scripts/plan_clips.py | [ ] |",
                "| clip/timeline 规划 | mv-plan/scripts/plan_clips.py | [x] |",
            )
            with open(os.path.join(tmp, "_进度.md"), "w", encoding="utf-8") as handle:
                handle.write(text)
            action = run.build_next_action(tmp)
            self.assertEqual(action["frontier"]["key"], "semantic_plan")
            self.assertEqual(action["stop_reason"], "needs_agent_generation")

    def test_settings_meta_mismatch_stops_before_routing(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            path = os.path.join(tmp, "_设置.md")
            text = read_text(path).replace("MV用途: 歌曲Demo", "MV用途: 投放版")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "state_inconsistent")
            self.assertTrue(action["state_consistency"]["meta_mismatches"])
            self.assertIn("state_contract.py sync", action["action_card"]["exact_command"])

    def test_incomplete_progress_stage_table_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            path = os.path.join(tmp, "_进度.md")
            text = read_text(path)
            text = "\n".join(
                line for line in text.splitlines() if "语义分镜注入" not in line
            ) + "\n"
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "state_inconsistent")
            self.assertTrue(any("semantic_plan" in message for message in action["state_consistency"]["errors"]))

    def test_all_rows_done_with_missing_output_receipts_is_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            path = os.path.join(tmp, "_进度.md")
            text = read_text(path).replace("[ ]", "[x]")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "stale_receipts")
            self.assertTrue(action["receipt_health"])

    def test_all_five_new_receipt_stages_surface_as_stale_when_falsely_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            settings = dict(run.contract.DEFAULT_SETTINGS)
            with open(os.path.join(tmp, "_设置.md"), "w", encoding="utf-8") as handle:
                handle.write(run.contract.settings_markdown("测试", settings))
            meta_path = os.path.join(tmp, "_meta.json")
            with open(meta_path, encoding="utf-8") as handle:
                meta = json.load(handle)
            meta.update(run.contract.runtime_state_from_settings(settings))
            with open(meta_path, "w", encoding="utf-8") as handle:
                json.dump(meta, handle, ensure_ascii=False)
            stages = run.contract.workflow_stage_table(
                settings["歌曲输入时序"], settings["字幕语言"], settings["演唱口型"],
            )
            table = "\n".join(
                f"| {row['label']} | {row['owner']} | [x] |" for row in stages
            )
            with open(os.path.join(tmp, "_进度.md"), "w", encoding="utf-8") as handle:
                handle.write("# 进度\n\n## 制MV 阶段\n| 阶段 | skill | 状态 |\n|---|---|---|\n" + table + "\n")
            with open(os.path.join(tmp, "歌", "song.mp3"), "wb") as handle:
                handle.write(b"changed-after-beat")
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "stale_receipts")
            stale = {row["stage"] for row in action["receipt_health"]}
            self.assertTrue(
                {"beat", "lyric_sync", "plan", "pacing_check", "picture_lock"}.issubset(stale),
                stale,
            )

    def test_disclosure_action_includes_required_arguments(self):
        command = run.STAGE_ACTIONS["disclosure"][1]
        self.assertIn("--visual-mode", command)
        self.assertIn("--video-mode", command)
        self.assertIn("--publish-target", command)
        self.assertIn("--territory", command)
        self.assertIn("--human-contribution", command)
        self.assertIn("--reviewer", command)

    def test_review_and_handoff_actions_write_authoritative_receipts(self):
        self.assertIn("--write-receipt", run.STAGE_ACTIONS["review"][1])
        handoff = run.STAGE_ACTIONS["handoff"][1]
        self.assertIn("release_decision.py", handoff)
        self.assertIn("--machine-evidence", handoff)
        self.assertIn("--upload-receipt", handoff)
        self.assertIn("--published-url", handoff)
        self.assertIn("completion.py complete", handoff)

    def test_state_sync_mirrors_settings_and_invalidates_downstream(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp, plan_done=True)
            progress_path = os.path.join(tmp, "_进度.md")
            text = read_text(progress_path).replace("[ ]", "[x]")
            with open(progress_path, "w", encoding="utf-8") as handle:
                handle.write(text)
            settings_path = os.path.join(tmp, "_设置.md")
            text = read_text(settings_path).replace("MV用途: 歌曲Demo", "MV用途: 投放版")
            with open(settings_path, "w", encoding="utf-8") as handle:
                handle.write(text)
            receipt = run.state_contract.sync(tmp)
            with open(os.path.join(tmp, "_meta.json"), encoding="utf-8") as handle:
                meta = json.load(handle)
            self.assertEqual(meta["use_case"], "投放版")
            self.assertFalse(meta["is_demo"])
            self.assertIn("plan", receipt["invalidated_stages"])
            progress_text = read_text(progress_path)
            self.assertIn("| clip/timeline 规划 | mv-plan/scripts/plan_clips.py | [ ] |", progress_text)

    def test_state_sync_downgrades_done_output_with_stale_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            progress_path = os.path.join(tmp, "_进度.md")
            with open(progress_path, encoding="utf-8") as handle:
                progress_content = handle.read().replace("[ ]", "✅")
            with open(progress_path, "w", encoding="utf-8") as handle:
                handle.write(progress_content)
            run.state_contract.sync(tmp)
            rows = run.stage_states(tmp)
            by_key = {row["key"]: row["state"] for row in rows}
            for stage in ("plan", "semantic_plan", "pacing_check", "picture_lock"):
                self.assertEqual(by_key[stage], "todo", stage)

    def test_no_progress_evidence_is_not_promoted_when_sync_restores_missing_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            progress_path = os.path.join(tmp, "_进度.md")
            progress_text = "\n".join(
                line for line in read_text(progress_path).splitlines()
                if "AI使用披露" not in line
            ) + "\n"
            with open(progress_path, "w", encoding="utf-8") as handle:
                handle.write(progress_text)
            script = os.path.join(HERE, "mv-craft", "scripts", "ai_usage.py")
            result = subprocess.run([
                sys.executable, script, tmp,
                "--visual-mode", "AI-generated", "--video-mode", "AI-generated",
                "--publish-target", "未定", "--territory", "CN", "--realism", "stylized",
                "--real-person", "none", "--music-mode", "human",
                "--human-contribution", "人工导演、挑版与终审", "--reviewer", "披露负责人",
                "--no-progress",
            ], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(run.completion.stage_health(tmp, "disclosure")["ok"])
            run.state_contract.sync(tmp)
            disclosure = next(row for row in run.stage_states(tmp) if row["key"] == "disclosure")
            self.assertEqual(disclosure["state"], "todo")

    def test_legacy_project_can_explicitly_bootstrap_settings_from_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            os.remove(os.path.join(tmp, "_设置.md"))
            action = run.build_next_action(tmp)
            self.assertEqual(action["stop_reason"], "state_inconsistent")
            self.assertIn("--bootstrap-settings-from-meta", action["action_card"]["exact_command"])
            run.state_contract.sync(tmp, bootstrap_settings_from_meta=True)
            self.assertTrue(os.path.isfile(os.path.join(tmp, "_设置.md")))
            audit = run.state_contract.audit(tmp, run.STAGE_ACTIONS)
            self.assertTrue(audit["ok"], audit["errors"])

    def test_song_timing_sync_reorders_workflow_and_resets_timing_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_project(tmp)
            progress_path = os.path.join(tmp, "_进度.md")
            progress_content = read_text(progress_path).replace("[ ]", "[x]")
            with open(progress_path, "w", encoding="utf-8") as handle:
                handle.write(progress_content)
            settings_path = os.path.join(tmp, "_设置.md")
            settings_content = read_text(settings_path).replace(
                "歌曲输入时序: 先传音乐", "歌曲输入时序: 后配歌曲"
            )
            with open(settings_path, "w", encoding="utf-8") as handle:
                handle.write(settings_content)
            receipt = run.state_contract.sync(tmp)
            self.assertIn("beat", receipt["invalidated_stages"])
            rows = run.stage_states(tmp)
            keys = [row["key"] for row in rows]
            self.assertLess(keys.index("script"), keys.index("song_ingest"))
            beat = next(row for row in rows if row["key"] == "beat")
            self.assertEqual(beat["state"], "todo")


class ImpactTest(unittest.TestCase):
    def _project(self, tmp):
        make_project(tmp, plan_done=True)
        clips = [
            {"clip_id": "Clip_001", "image_path": "出图/段落/图片/Clip_001.png",
             "seam_contract": {"type": "match_action"}},
            {"clip_id": "Clip_002", "image_path": "出图/段落/图片/Clip_002.png",
             "seam_contract": {"type": "beat_cut"}},
        ]
        with open(os.path.join(tmp, "分镜", "clip_plan.json"), "w", encoding="utf-8") as f:
            json.dump({"clips": clips}, f, ensure_ascii=False)
        os.makedirs(os.path.join(tmp, "出视频"), exist_ok=True)
        with open(os.path.join(tmp, "出视频", "jobs_manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"jobs": [{"clip_id": "Clip_001",
                                 "takes": [{"take_id": "take_01", "video_sha256": "f" * 64}]}]},
                      f, ensure_ascii=False)

    def test_unknown_clip_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            result = run.build_impact(tmp, "Clip_099", "image")
            self.assertIn("error", result)

    def test_image_change_cascades_to_registered_takes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            result = run.build_impact(tmp, "Clip_001", "image")
            actions = " ".join(s["action"] for s in result["steps"])
            self.assertIn("image_qc", actions)
            self.assertIn("submitted_refs/controls", actions)
            self.assertIn("inherit_contract", actions)

    def test_edit_change_starts_from_replan(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            result = run.build_impact(tmp, "Clip_001", "edit")
            self.assertEqual(result["steps"][0]["stage"], "plan")

    def test_neighbor_seam_notes_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            result = run.build_impact(tmp, "Clip_002", "image")
            positions = {row["position"] for row in result["affected_neighbors"]}
            self.assertIn("prev", positions)

    def test_no_video_manifest_skips_video_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp)
            os.remove(os.path.join(tmp, "出视频", "jobs_manifest.json"))
            result = run.build_impact(tmp, "Clip_002", "image")
            stages = {s["stage"] for s in result["steps"]}
            self.assertNotIn("video", stages)


if __name__ == "__main__":
    unittest.main()
