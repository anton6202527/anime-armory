#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile

import story_vcs


def write_project(root: str) -> None:
    os.makedirs(os.path.join(root, "设定"), exist_ok=True)
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write("main-progress\n")
    with open(os.path.join(root, "设定", "动态百科.json"), "w", encoding="utf-8") as f:
        f.write('{"main": true}\n')


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_branch_manifest_records_base_hashes_and_dry_run_does_not_overwrite():
    with tempfile.TemporaryDirectory() as root:
        write_project(root)
        manifest = story_vcs.handle_branch(root, "take-a")
        assert manifest["kind"] == story_vcs.BRANCH_KIND
        assert manifest["files"][0]["base_sha256"]

        branch_progress = story_vcs.branch_file_for_rel(root, "_进度.md", "take-a")
        with open(branch_progress, "w", encoding="utf-8") as f:
            f.write("branch-progress\n")

        report = story_vcs.handle_merge(root, "take-a", dry_run=True)
        assert report["verdict"] == "ready"
        assert read(os.path.join(root, "_进度.md")) == "main-progress\n"


def test_merge_blocks_when_main_changed_since_branch_base():
    with tempfile.TemporaryDirectory() as root:
        write_project(root)
        story_vcs.handle_branch(root, "take-a")
        with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
            f.write("main-changed\n")

        report = story_vcs.handle_merge(root, "take-a")
        assert report["kind"] == "novel_story_vcs_merge_preflight"
        assert report["verdict"] == "block"
        assert report["conflicts"][0]["main_path"] == "_进度.md"
        assert read(os.path.join(root, "_进度.md")) == "main-changed\n"


def test_merge_blocks_missing_branch_file_even_with_force():
    with tempfile.TemporaryDirectory() as root:
        write_project(root)
        story_vcs.handle_branch(root, "take-a")
        branch_progress = story_vcs.branch_file_for_rel(root, "_进度.md", "take-a")
        os.remove(branch_progress)

        report = story_vcs.handle_merge(root, "take-a", force=True)
        assert report["kind"] == "novel_story_vcs_merge_preflight"
        assert report["verdict"] == "block"
        assert "_进度_branch_take-a.md" in report["missing_branch_files"][0]
        assert any(item["type"] == "missing_branch_file" for item in report["blockers"])
        assert read(os.path.join(root, "_进度.md")) == "main-progress\n"


def test_legacy_branch_without_base_hash_requires_explicit_acceptance():
    with tempfile.TemporaryDirectory() as root:
        write_project(root)
        branch_progress = story_vcs.branch_file_for_rel(root, "_进度.md", "legacy")
        with open(branch_progress, "w", encoding="utf-8") as f:
            f.write("legacy-progress\n")

        report = story_vcs.handle_merge(root, "legacy", dry_run=True)
        assert report["verdict"] == "block"
        assert report["legacy_without_base_hash"][0]["main_path"] == "_进度.md"
        assert any(item["type"] == "legacy_without_base_hash" for item in report["blockers"])

        accepted = story_vcs.handle_merge(root, "legacy", dry_run=True, accept_legacy_no_base=True)
        assert accepted["verdict"] == "ready"


def test_migrate_legacy_branch_and_health_report():
    with tempfile.TemporaryDirectory() as root:
        write_project(root)
        branch_progress = story_vcs.branch_file_for_rel(root, "_进度.md", "legacy")
        with open(branch_progress, "w", encoding="utf-8") as f:
            f.write("legacy-progress\n")

        migrated = story_vcs.handle_migrate(root, "legacy")
        assert migrated["status"] == "migrated"
        assert migrated["legacy_without_base_hash_count"] == 1
        blocked = story_vcs.handle_merge(root, "legacy", dry_run=True)
        assert blocked["verdict"] == "block"

        trusted = story_vcs.handle_migrate(root, "legacy", trust_current_main=True, overwrite=True)
        assert trusted["legacy_without_base_hash_count"] == 0
        ready = story_vcs.handle_merge(root, "legacy", dry_run=True)
        assert ready["verdict"] == "ready"

        health = story_vcs.handle_health(root)
        assert health["branch_count"] >= 1
        assert health["ready_count"] >= 1


def test_force_merge_writes_backup_and_rollback_restores_main():
    with tempfile.TemporaryDirectory() as root:
        write_project(root)
        story_vcs.handle_branch(root, "take-a")
        branch_progress = story_vcs.branch_file_for_rel(root, "_进度.md", "take-a")
        with open(branch_progress, "w", encoding="utf-8") as f:
            f.write("branch-progress\n")
        with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
            f.write("main-changed\n")

        merged = story_vcs.handle_merge(root, "take-a", force=True)
        assert merged["kind"] == story_vcs.MERGE_KIND
        assert read(os.path.join(root, "_进度.md")) == "branch-progress\n"
        assert merged["files"][0]["backup_path"]

        rollback = story_vcs.handle_rollback(root, merged["merge_id"])
        assert rollback["kind"] == "novel_story_vcs_rollback"
        assert read(os.path.join(root, "_进度.md")) == "main-changed\n"


def _clean_branch_merge(root, branch="take-a"):
    write_project(root)
    story_vcs.handle_branch(root, branch)
    bp = story_vcs.branch_file_for_rel(root, "_进度.md", branch)
    with open(bp, "w", encoding="utf-8") as f:
        f.write("branch-progress\n")
    return story_vcs.handle_merge(root, branch)


def test_merge_audit_ledger_append_only_with_begin_and_commit():
    import json as _json
    with tempfile.TemporaryDirectory() as root:
        merged = _clean_branch_merge(root)
        assert merged["status"] == "committed"
        audit = os.path.join(root, "生产数据", "vcs_audit.jsonl")
        lines1 = [_json.loads(x) for x in read(audit).splitlines() if x.strip()]
        actions1 = [e["action"] for e in lines1]
        assert "merge_begin" in actions1 and "merge" in actions1  # in-flight 标记 + 提交都进账本
        # 第二次 merge 只追加、不改写既有行（append-only）
        story_vcs.handle_branch(root, "take-b")
        bp = story_vcs.branch_file_for_rel(root, "设定/动态百科.json", "take-b")
        with open(bp, "w", encoding="utf-8") as f:
            f.write('{"branch": true}\n')
        story_vcs.handle_merge(root, "take-b")
        lines2 = read(audit).splitlines()
        assert lines2[: len(lines1)] == read(audit).splitlines()[: len(lines1)]
        assert len(lines2) > len(lines1)


def test_committed_report_marks_every_file_committed():
    with tempfile.TemporaryDirectory() as root:
        merged = _clean_branch_merge(root)
        assert all(f.get("committed") is True for f in merged["files"])


def test_toctou_main_changed_after_preflight_aborts_without_partial_write(monkeypatch=None):
    # 模拟"preflight 判 ready 后、覆盖前主文件被改"：monkeypatch preflight 返回 ready 但 base 已陈旧。
    with tempfile.TemporaryDirectory() as root:
        write_project(root)
        story_vcs.handle_branch(root, "take-a")
        bp = story_vcs.branch_file_for_rel(root, "_进度.md", "take-a")
        with open(bp, "w", encoding="utf-8") as f:
            f.write("branch-progress\n")
        real_pre = story_vcs.merge_preflight
        stale_base = story_vcs.sha256_file(os.path.join(root, "_进度.md"))  # 原始 hash
        with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
            f.write("main-changed-by-concurrent-writer\n")

        def fake_pre(r, b, **k):
            pf = real_pre(r, b, force=True)  # 拿到文件清单
            pf["verdict"] = "ready"
            for it in pf["files"]:
                it["base_sha256"] = stale_base  # 谎称 base 是改动前
            return pf
        import story_vcs as _m
        _orig = _m.merge_preflight
        _m.merge_preflight = fake_pre
        try:
            report = story_vcs.handle_merge(root, "take-a")
        finally:
            _m.merge_preflight = _orig
        assert report.get("status") == "aborted_toctou"
        assert read(os.path.join(root, "_进度.md")) == "main-changed-by-concurrent-writer\n"  # 未被覆盖


def test_rollback_recovers_from_crash_mid_merge():
    # 手工构造 in_progress 报告：A 已覆盖(有备份)、B 未覆盖(无备份, committed=False)。
    with tempfile.TemporaryDirectory() as root:
        write_project(root)
        os.makedirs(os.path.join(root, "设定"), exist_ok=True)
        merge_id = "merge_crash_test"
        backup_dir = os.path.join(root, "生产数据", "story_vcs_backups", merge_id)
        # A：_进度.md 原始内容备份 + 主文件已被改成 branch 内容（模拟已覆盖）
        os.makedirs(backup_dir, exist_ok=True)
        with open(os.path.join(backup_dir, "_进度.md"), "w", encoding="utf-8") as f:
            f.write("main-progress\n")  # 原件备份
        with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
            f.write("branch-progress\n")  # 已覆盖
        # B：动态百科.json 未被覆盖（无备份），主文件仍原件
        report = {
            "schema_version": 1, "kind": story_vcs.MERGE_KIND, "merge_id": merge_id,
            "branch": "take-a", "status": "in_progress",
            "files": [
                {"main_path": "_进度.md", "branch_path": "x",
                 "main_existed_before_merge": True,
                 "backup_path": "生产数据/story_vcs_backups/%s/_进度.md" % merge_id,
                 "committed": True},
                {"main_path": "设定/动态百科.json", "branch_path": "y",
                 "main_existed_before_merge": True,
                 "backup_path": "生产数据/story_vcs_backups/%s/设定/动态百科.json" % merge_id,
                 "committed": False},
            ],
        }
        story_vcs.atomic_write_json(story_vcs.merge_report_path(root, merge_id), report)
        rollback = story_vcs.handle_rollback(root, merge_id)  # 不应抛 backup missing
        assert read(os.path.join(root, "_进度.md")) == "main-progress\n"          # A 还原
        assert read(os.path.join(root, "设定", "动态百科.json")) == '{"main": true}\n'  # B 保持原件
        skipped = [f for f in rollback["files"] if f.get("skipped")]
        assert any("动态百科" in f["main_path"] for f in skipped)
