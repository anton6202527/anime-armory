#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile
import importlib.util


def load_queue_module():
    path = os.path.join(os.path.dirname(__file__), "queue.py")
    spec = importlib.util.spec_from_file_location("novel_batch_queue_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


novel_queue = load_queue_module()


def test_project_scope_task_id_is_stable_and_non_empty():
    task_id = novel_queue.stable_task_id("dashboard", None, "python3 tool.py", scope="project")
    assert task_id.startswith("dashboard_")
    assert task_id != "dashboard_ch00"


def write_minimal_project(root: str) -> None:
    os.makedirs(os.path.join(root, "章节"), exist_ok=True)
    with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump({"title": "测试小说", "kind": "create"}, f, ensure_ascii=False)
    with open(os.path.join(root, "_设置.md"), "w", encoding="utf-8") as f:
        f.write("# 设置\n")
    with open(os.path.join(root, "_进度.md"), "w", encoding="utf-8") as f:
        f.write("# 进度\n")
    with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
        f.write("# 第1章\n正文\n")


def test_plan_claim_complete_status():
    with tempfile.TemporaryDirectory() as root:
        q = novel_queue.NovelBatchQueue(root)
        tasks = novel_queue.build_tasks(
            root,
            "review",
            [1, 2],
            "echo {chapter_label}",
            max_retries=1,
            priority="P1",
        )
        result = q.upsert_tasks(tasks)
        assert result["added"] == 2

        claimed = q.claim_task("worker-a", lease_sec=60)
        assert claimed["chapter"] == 1
        assert claimed["status"] == "running"
        q.mark(claimed["id"], "worker-a", "pass")

        status = q.status()
        assert status["summary"]["by_status"]["completed"] == 1
        assert status["summary"]["by_status"]["pending"] == 1
        assert os.path.exists(q.queue_file)


def test_expired_lease_reclaims_task():
    with tempfile.TemporaryDirectory() as root:
        q = novel_queue.NovelBatchQueue(root)
        task = novel_queue.build_tasks(root, "dashboard", [], "echo {task_id}", max_retries=1, priority="P2")[0]
        q.upsert_tasks([task])
        claimed = q.claim_task("worker-a", lease_sec=-1)
        assert claimed["status"] == "running"

        result = q.reclaim_expired()
        assert result["reclaimed"] == 1
        status = q.status()
        assert status["summary"]["by_status"]["retry_queued"] == 1


def test_market_evidence_jobs_plan_to_claimable_tasks():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "评分"), exist_ok=True)
        with open(os.path.join(root, "评分", "market_evidence_jobs.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_market_evidence_jobs",
                "baseline_date": "2026-06-26",
                "target_platform": "红果短剧",
                "jobs": [
                    {
                        "id": "MARKET-SEARCH-001",
                        "kind": "novel_market_evidence_search_job",
                        "target_platform": "红果短剧",
                        "baseline_date": "2026-06-26",
                        "source_task_id": "MARKET-EVIDENCE-001",
                        "search_queries": ["红果短剧 热榜 报告 2026-06-26"],
                        "required_output_schema": {"platform": "红果短剧", "summary": "一句话结论"},
                        "manual_evidence_format": "平台|日期YYYY-MM-DD|来源|结论|URL",
                        "return_command_template": "python3 skills/novel-score/scripts/collect_market_baseline.py ...",
                    }
                ],
            }, f, ensure_ascii=False)
        q = novel_queue.NovelBatchQueue(root)

        tasks = novel_queue.build_market_evidence_tasks(
            root,
            novel_queue.default_command_template("market_evidence"),
            max_retries=1,
            priority="P1",
        )
        result = q.upsert_tasks(tasks)
        assert result["added"] == 1

        claimed = q.claim_task("worker-market", kinds={"market_evidence"})
        assert claimed["kind"] == "market_evidence"
        assert claimed["scope"] == "market_evidence:MARKET-SEARCH-001"
        assert claimed["search_queries"] == ["红果短剧 热榜 报告 2026-06-26"]
        assert claimed["required_output_schema"]["summary"] == "一句话结论"
        assert "collect_market_baseline.py" in claimed["command"]
        assert "红果短剧" in claimed["command"]


def test_fail_after_retry_goes_dead_letter():
    with tempfile.TemporaryDirectory() as root:
        q = novel_queue.NovelBatchQueue(root)
        task = novel_queue.build_tasks(root, "manual", [], "echo {task_id}", max_retries=0, priority="P0")[0]
        q.upsert_tasks([task])

        claimed = q.claim_task("worker-a")
        q.mark(claimed["id"], "worker-a", "fail", error_class="Boom", message="broken")
        status = q.status()
        assert status["summary"]["by_status"]["dead_letter"] == 1
        dead = [item for item in status["tasks"] if item["status"] == "dead_letter"][0]
        assert dead["last_error"]["class"] == "Boom"


def test_run_one_rejects_non_allowlisted_manual_command_by_default():
    with tempfile.TemporaryDirectory() as root:
        q = novel_queue.NovelBatchQueue(root)
        task = novel_queue.build_tasks(root, "manual", [], "echo {task_id}", max_retries=0, priority="P0")[0]
        q.upsert_tasks([task])

        result = q.run_one("worker-a", dry_run=True)
        assert result["status"] == "command_not_allowed"
        status = q.status()
        assert status["summary"]["by_status"]["dead_letter"] == 1


def test_run_one_dry_run_claims_allowlisted_task_and_marks_skipped():
    with tempfile.TemporaryDirectory() as root:
        q = novel_queue.NovelBatchQueue(root)
        task = novel_queue.build_tasks(
            root,
            "dashboard",
            [],
            novel_queue.default_command_template("dashboard"),
            max_retries=1,
            priority="P2",
        )[0]
        q.upsert_tasks([task])

        result = q.run_one("worker-a", dry_run=True)
        assert result["status"] == "dry_run"
        assert "skills/novel-dashboard/scripts/dashboard.py" in result["argv"][1]
        status = q.status()
        assert status["summary"]["by_status"]["skipped"] == 1
        assert os.path.exists(os.path.join(root, result["run_artifact"]))


def test_run_one_writes_run_artifact_logs_and_output_diff():
    with tempfile.TemporaryDirectory() as root:
        write_minimal_project(root)
        q = novel_queue.NovelBatchQueue(root)
        task = novel_queue.build_tasks(
            root,
            "dashboard",
            [],
            novel_queue.default_command_template("dashboard"),
            max_retries=1,
            priority="P2",
        )[0]
        q.upsert_tasks([task])

        result = q.run_one("worker-a", timeout_sec=60)
        assert result["status"] == "completed", result
        artifact_path = os.path.join(root, result["run_artifact"])
        assert os.path.exists(artifact_path)
        with open(artifact_path, encoding="utf-8") as f:
            artifact = json.load(f)
        assert artifact["kind"] == "novel_batch_task_run"
        assert os.path.exists(os.path.join(root, artifact["logs"]["stdout_path"]))
        assert os.path.exists(os.path.join(root, artifact["logs"]["stderr_path"]))
        changed_paths = {
            item["path"]
            for item in artifact["output_artifacts"]["added"] + artifact["output_artifacts"]["changed"]
        }
        assert "生产数据/novel_dashboard.json" in changed_paths

        status = q.status()
        completed = [item for item in status["tasks"] if item["status"] == "completed"][0]
        assert completed["last_run_artifact"] == result["run_artifact"]
        summary = q.run_artifact_summary()
        assert summary["count"] == 1
        assert summary["by_status"]["completed"] == 1


def test_run_artifact_redacts_truncates_logs_and_respects_snapshot_policy():
    with tempfile.TemporaryDirectory() as root:
        write_minimal_project(root)
        os.makedirs(os.path.join(root, "临时"), exist_ok=True)
        with open(os.path.join(root, "临时", "heavy.tmp"), "w", encoding="utf-8") as f:
            f.write("ignore me")
        q = novel_queue.NovelBatchQueue(root)
        before = q.output_snapshot(include_patterns=["章节/", "临时/"], exclude_patterns=["临时/"])
        assert "章节/第01章.md" in before
        assert "临时/heavy.tmp" not in before
        task = novel_queue.build_tasks(root, "dashboard", [], novel_queue.default_command_template("dashboard"), max_retries=1, priority="P2")[0]
        task["attempts"] = 1
        artifact_rel, artifact = q.write_run_artifact(
            task,
            "worker-a",
            {"status": "completed", "elapsed_ms": 1},
            stdout="api_key=SECRET_VALUE\n" + ("x" * 200),
            stderr="sk-1234567890abcdef\n",
            before={},
            after=before,
            max_log_bytes=80,
            snapshot_policy=q.snapshot_policy(["章节/"], ["临时/"]),
        )
        stdout_path = os.path.join(root, artifact["logs"]["stdout_path"])
        stderr_path = os.path.join(root, artifact["logs"]["stderr_path"])
        with open(stdout_path, encoding="utf-8") as f:
            stdout = f.read()
        with open(stderr_path, encoding="utf-8") as f:
            stderr = f.read()
        assert "SECRET_VALUE" not in stdout
        assert "sk-1234567890abcdef" not in stderr
        assert artifact["logs"]["stdout"]["truncated"] is True
        assert artifact["snapshot_policy"]["include"] == ["章节/"]
        assert os.path.exists(os.path.join(root, artifact_rel))


def test_governance_report_is_written_with_dead_letter_summary():
    with tempfile.TemporaryDirectory() as root:
        q = novel_queue.NovelBatchQueue(root)
        task = novel_queue.build_tasks(root, "manual", [], "echo {task_id}", max_retries=0, priority="P0")[0]
        q.upsert_tasks([task])
        claimed = q.claim_task("worker-a")
        q.mark(claimed["id"], "worker-a", "fail", error_class="Boom", message="broken")

        json_path, md_path, report = q.write_governance_report()
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        assert report["slo"]["dead_letter_count"] == 1
