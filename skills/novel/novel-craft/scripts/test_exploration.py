#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

import exploration
import qa_gate


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
CREATE_INIT = os.path.join(REPO, "skills", "novel", "novel-create", "scripts", "init_project.py")


def write_project(root):
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "create", "title": "测试作品"}, f, ensure_ascii=False)
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write("formal-progress\n")
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("formal-chapter\n")
    with open(os.path.join(root, "设定", "创作蓝图.md"), "w", encoding="utf-8") as f:
        f.write("formal-blueprint\n")
    with open(os.path.join(root, "审稿", "state_ledger.json"), "w", encoding="utf-8") as f:
        json.dump({"formal": True}, f)


def formal_snapshot(root):
    rels = (
        "_meta.json",
        "_进度.md",
        "章节/第01章.md",
        "设定/创作蓝图.md",
        "审稿/state_ledger.json",
    )
    result = {}
    for rel in rels:
        path = os.path.join(root, rel.replace("/", os.sep))
        with open(path, "rb") as f:
            result[rel] = hashlib.sha256(f.read()).hexdigest()
    return result


class ExplorationWorkflowTest(unittest.TestCase):
    def test_human_seed_requires_explicit_pre_ai_confirmation_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as root:
            write_project(root)
            seed_source = os.path.join(root, "author-seed.md")
            raw = "雨停后，她仍不肯进屋。\r\n我想知道她在怕谁。\r\n".encode("utf-8")
            with open(seed_source, "wb") as f:
                f.write(raw)

            with self.assertRaises(exploration.ExplorationError):
                exploration.capture_human_seed(
                    root,
                    from_file=seed_source,
                    author="作者",
                    human_first_confirmed=False,
                )
            self.assertFalse(os.path.exists(os.path.join(root, "探索")))

            before = formal_snapshot(root)
            record = exploration.capture_human_seed(
                root,
                from_file=seed_source,
                author="作者",
                label="未润色原文",
                human_first_confirmed=True,
            )
            snapshot = os.path.join(root, record["snapshot_path"].replace("/", os.sep))
            with open(snapshot, "rb") as f:
                self.assertEqual(f.read(), raw)
            self.assertEqual(record["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(record["capture_claim"]["kind"], "explicit_human_first_confirmation")
            self.assertEqual(formal_snapshot(root), before)

    def test_register_binds_seed_and_promotion_only_creates_non_canon_candidate(self):
        with tempfile.TemporaryDirectory() as root:
            write_project(root)
            before = formal_snapshot(root)
            seed = exploration.capture_human_seed(
                root,
                text="一个退休摆渡人拒绝渡最后一位乘客。",
                author="作者",
                human_first_confirmed=True,
            )
            source = os.path.join(root, "audition.md")
            draft_text = "# 角色试镜\n\n他把船桨横在膝上，没有看河对岸。\n"
            with open(source, "w", encoding="utf-8") as f:
                f.write(draft_text)

            draft = exploration.register_draft(
                root,
                source_file=source,
                title="摆渡人拒渡",
                exploration_kind="character_audition",
                creator="作者",
                authorship="human",
                question="无人施压时，他还会拒绝吗？",
                seed_ids=[seed["seed_id"]],
            )
            self.assertEqual(draft["status"], "registered_non_canon")
            self.assertFalse(draft["requires_state_delta"])
            self.assertEqual(draft["seed_bindings"][0]["sha256"], seed["sha256"])

            with self.assertRaises(exploration.ExplorationError):
                exploration.record_decision(
                    root,
                    draft_id=draft["draft_id"],
                    decision="promote_candidate",
                    reviewer="作者",
                    reason="人物选择成立",
                    target="blueprint",
                )

            decision = exploration.record_decision(
                root,
                draft_id=draft["draft_id"],
                decision="promote_candidate",
                expected_sha256=draft["sha256"],
                reviewer="作者",
                reason="拒渡是主动承担后果，不是被动拖延",
                target="blueprint",
            )
            self.assertFalse(decision["formal_write_performed"])
            self.assertEqual(decision["canon_effect"], "none_until_separate_formal_review_and_integration")
            candidate = os.path.join(root, decision["candidate"]["path"].replace("/", os.sep))
            with open(candidate, encoding="utf-8") as f:
                self.assertEqual(f.read(), draft_text)
            self.assertEqual(exploration.sha256_file(candidate), draft["sha256"])
            self.assertEqual(formal_snapshot(root), before)
            self.assertFalse(os.path.exists(os.path.join(root, "审稿", f"state_delta_{draft['draft_id']}.json")))

            status = exploration.exploration_status(root)
            self.assertTrue(status["integrity_ok"])
            self.assertEqual(len(status["seeds"]), 1)
            self.assertEqual(len(status["drafts"]), 1)
            self.assertEqual(len(status["decisions"]), 1)

    def test_tampered_snapshot_blocks_hash_bound_decision_without_partial_record(self):
        with tempfile.TemporaryDirectory() as root:
            write_project(root)
            source = os.path.join(root, "ending.txt")
            with open(source, "w", encoding="utf-8") as f:
                f.write("错误结局第一版")
            draft = exploration.register_draft(
                root,
                source_file=source,
                title="错误结局",
                exploration_kind="ending_probe",
                creator="writer-agent",
                authorship="ai-assisted",
            )
            draft_path = os.path.join(root, draft["snapshot_path"].replace("/", os.sep))
            with open(draft_path, "a", encoding="utf-8") as f:
                f.write("\n事后偷偷改动")

            with self.assertRaises(exploration.ExplorationError):
                exploration.record_decision(
                    root,
                    draft_id=draft["draft_id"],
                    decision="promote_candidate",
                    expected_sha256=draft["sha256"],
                    reviewer="作者",
                    reason="看似可用",
                    target="outline",
                )
            with open(os.path.join(root, "探索", "manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(manifest["decisions"], [])
            self.assertFalse(os.path.isdir(os.path.join(root, "探索", "决策")))
            self.assertFalse(os.path.isdir(os.path.join(root, "探索", "晋升候选")))
            self.assertFalse(exploration.exploration_status(root)["integrity_ok"])

    def test_seed_and_draft_sidecars_are_manifest_bound_and_tampering_is_visible(self):
        with tempfile.TemporaryDirectory() as base:
            root = os.path.join(base, "project")
            source = os.path.join(base, "probe.md")
            write_project(root)
            seed = exploration.capture_human_seed(
                root,
                text="先有人，再有故事。",
                author="作者",
                human_first_confirmed=True,
            )
            seed_sidecar = os.path.join(root, seed["metadata_path"].replace("/", os.sep))
            with open(seed_sidecar, encoding="utf-8") as f:
                sidecar_payload = json.load(f)
            self.assertNotIn("metadata_sha256", sidecar_payload, "sidecar 不得递归绑定自身")
            self.assertEqual(seed["metadata_sha256"], exploration.sha256_file(seed_sidecar))
            with open(os.path.join(root, "探索", "manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(
                manifest["seeds"][0]["metadata_sha256"],
                exploration.sha256_file(seed_sidecar),
            )

            with open(source, "w", encoding="utf-8") as f:
                f.write("# 试写\n\n他第一次没有回答。\n")
            draft = exploration.register_draft(
                root,
                source_file=source,
                title="沉默试镜",
                exploration_kind="character_audition",
                creator="作者",
                authorship="human",
                seed_ids=[seed["seed_id"]],
            )
            draft_sidecar = os.path.join(root, draft["metadata_path"].replace("/", os.sep))
            self.assertEqual(draft["metadata_sha256"], exploration.sha256_file(draft_sidecar))
            with open(os.path.join(root, "探索", "manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(
                manifest["drafts"][0]["metadata_sha256"],
                exploration.sha256_file(draft_sidecar),
            )
            self.assertTrue(exploration.exploration_status(root)["integrity_ok"])

            with open(draft_sidecar, "a", encoding="utf-8") as f:
                f.write("\n")
            status = exploration.exploration_status(root)
            self.assertFalse(status["integrity_ok"])
            draft_status = status["drafts"][0]
            self.assertEqual(draft_status["snapshot"]["integrity"], "ok")
            self.assertEqual(draft_status["sidecar"]["integrity"], "stale")
            with self.assertRaises(exploration.ExplorationError):
                exploration.record_decision(
                    root,
                    draft_id=draft["draft_id"],
                    decision="promote_candidate",
                    expected_sha256=draft["sha256"],
                    reviewer="作者",
                    reason="sidecar 已损坏时不得晋升",
                    target="blueprint",
                )

            # 用另一个项目覆盖 seed sidecar；绑定损坏后不能登记依赖它的新稿。
            root2 = os.path.join(base, "project-seed-tamper")
            write_project(root2)
            seed2 = exploration.capture_human_seed(
                root2,
                text="未经建议的第二颗种子。",
                author="作者",
                human_first_confirmed=True,
            )
            seed2_sidecar = os.path.join(root2, seed2["metadata_path"].replace("/", os.sep))
            with open(seed2_sidecar, "a", encoding="utf-8") as f:
                f.write("\n")
            seed_status = exploration.exploration_status(root2)
            self.assertFalse(seed_status["integrity_ok"])
            self.assertEqual(seed_status["seeds"][0]["sidecar"]["integrity"], "stale")
            with self.assertRaises(exploration.ExplorationError):
                exploration.register_draft(
                    root2,
                    source_file=source,
                    title="不应登记",
                    exploration_kind="scene_probe",
                    creator="作者",
                    authorship="human",
                    seed_ids=[seed2["seed_id"]],
                )

    def test_status_is_read_only_for_legacy_project_without_exploration_area(self):
        with tempfile.TemporaryDirectory() as root:
            write_project(root)
            status = exploration.exploration_status(root)
            self.assertFalse(status["initialized"])
            self.assertTrue(status["integrity_ok"])
            self.assertFalse(os.path.exists(os.path.join(root, "探索")))

    def test_exploration_directory_symlink_cannot_escape_project_root(self):
        with tempfile.TemporaryDirectory() as base:
            root = os.path.join(base, "project")
            outside = os.path.join(base, "outside")
            write_project(root)
            os.makedirs(outside)
            try:
                os.symlink(outside, os.path.join(root, "探索"), target_is_directory=True)
            except (OSError, NotImplementedError) as exc:  # pragma: no cover - platform policy.
                self.skipTest(f"symlink unavailable: {exc}")

            with self.assertRaises(exploration.ExplorationError):
                exploration.capture_human_seed(
                    root,
                    text="不得写到作品外",
                    author="作者",
                    human_first_confirmed=True,
                )
            with self.assertRaises(exploration.ExplorationError):
                exploration.exploration_status(root)
            self.assertEqual(os.listdir(outside), [], "连 lock/manifest 都不得写到外部软链目标")

    def test_exploration_artifacts_do_not_change_formal_qa_gate(self):
        with tempfile.TemporaryDirectory() as base:
            root = os.path.join(base, "project")
            source = os.path.join(base, "probe.md")
            write_project(root)
            with open(source, "w", encoding="utf-8") as f:
                f.write("# POV 试写\n\n她只听见河面上传来第二个人的脚步。\n")

            before = qa_gate.collect_gate_status(root, require_state_closure=True)
            seed = exploration.capture_human_seed(
                root,
                text="河上只有一条看不见的路。",
                author="作者",
                human_first_confirmed=True,
            )
            draft = exploration.register_draft(
                root,
                source_file=source,
                title="旁观者 POV",
                exploration_kind="pov_probe",
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
                reason="旁观者让隐瞒关系变得可见",
                target="outline",
            )
            after = qa_gate.collect_gate_status(root, require_state_closure=True)

            for payload in (before, after):
                payload.pop("generated_at", None)
                payload.pop("project_root", None)
            self.assertEqual(after, before, "探索目录必须对正式 QA gate 完全不可见")

    def test_create_init_can_atomically_capture_human_first_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "project")
            got = subprocess.run(
                [
                    sys.executable,
                    CREATE_INIT,
                    "--title", "河的背面",
                    "--genre", "现实主义",
                    "--premise", "摆渡人拒绝最后一次渡河",
                    "--scale", "short",
                    "--purpose", "传统小说",
                    "--platform", "跨平台",
                    "--out", root,
                    "--human-seed", "我只看见一只停在河中央的船。",
                    "--human-seed-author", "作者",
                    "--human-first-confirmed",
                ],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(got.returncode, 0, got.stderr)
            with open(os.path.join(root, "探索", "manifest.json"), encoding="utf-8") as f:
                manifest = json.load(f)
            self.assertEqual(len(manifest["seeds"]), 1)
            self.assertEqual(manifest["formal_pipeline_effect"], "none")
            self.assertTrue(os.path.exists(os.path.join(root, "_进度.md")))
            self.assertFalse(os.path.exists(os.path.join(root, "章节", "第01章.md")))


if __name__ == "__main__":
    unittest.main()
