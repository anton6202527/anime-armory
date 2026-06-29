#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import pytest

import semantic_job
from provenance import append_event, events_for_artifact, lineage_for_artifact, openlineage_events, read_events


def test_create_and_complete_semantic_job():
    with tempfile.TemporaryDirectory() as root:
        job = semantic_job.create_job(
            root,
            semantic_kind="score_assessment",
            prompt="请输出 JSON",
            response_out="评分/assessment.json",
            required_fields=["score_task_id", "scores"],
            complete_command="python3 score.py ...",
            metadata={"score_task_id": "task-1"},
            source_snapshot={"baseline_hash": "abc"},
        )
        assert os.path.exists(job["job_path"])
        assert os.path.exists(os.path.join(root, job["prompt_path"]))
        assert job["schema_ref"] == "score_assessment"
        assert job["source_snapshot"]["baseline_hash"] == "abc"
        assert job["response_contract"]["required"]["score_task_id"] == "str"
        response = os.path.join(root, "tmp_response.json")
        with open(response, "w", encoding="utf-8") as f:
            json.dump({"score_task_id": "task-1", "scores": [], "deductions": []}, f)

        semantic_job.claim_job(job["job_path"], claimed_by="score-agent")
        done = semantic_job.complete_job(job["job_path"], response, completed_by="score-agent")

        assert done["status"] == "completed"
        assert done["completed_by"] == "score-agent"
        assert done["response_path"] == "评分/assessment.json"
        assert os.path.exists(os.path.join(root, "评分", "assessment.json"))
        events = read_events(root)
        assert [event["event_type"] for event in events] == [
            "semantic_job_created",
            "semantic_job_claimed",
            "semantic_job_completed",
        ]
        assert events[-1]["metadata"]["response_hash"] == done["response_hash"]


def test_complete_rejects_missing_required_field():
    with tempfile.TemporaryDirectory() as root:
        job = semantic_job.create_job(
            root,
            semantic_kind="ledger_reconcile",
            prompt="prompt",
            response_out="审稿/state_verify_第01章.json",
            required_fields=["chapter", "status", "notes"],
        )
        response = os.path.join(root, "bad.json")
        with open(response, "w", encoding="utf-8") as f:
            json.dump({"chapter": 1, "status": "ok"}, f)

        semantic_job.claim_job(job["job_path"], claimed_by="ledger-agent")
        with pytest.raises(ValueError) as exc:
            semantic_job.complete_job(job["job_path"], response)
        assert "notes" in str(exc.value)


def test_complete_rejects_unclaimed_job_by_default():
    with tempfile.TemporaryDirectory() as root:
        job = semantic_job.create_job(
            root,
            semantic_kind="score_assessment",
            prompt="prompt",
            response_out="评分/assessment.json",
            required_fields=["score_task_id"],
        )
        response = os.path.join(root, "response.json")
        with open(response, "w", encoding="utf-8") as f:
            json.dump({"score_task_id": "task-1", "scores": [], "deductions": []}, f)

        with pytest.raises(ValueError) as exc:
            semantic_job.complete_job(job["job_path"], response)
        assert "must be claimed" in str(exc.value)

        done = semantic_job.complete_job(job["job_path"], response, allow_unclaimed=True)
        assert done["status"] == "completed"


def test_complete_accepts_response_already_at_output_path():
    with tempfile.TemporaryDirectory() as root:
        job = semantic_job.create_job(
            root,
            semantic_kind="score_assessment",
            prompt="prompt",
            response_out="评分/assessment.json",
            required_fields=["score_task_id"],
        )
        response = os.path.join(root, "评分", "assessment.json")
        os.makedirs(os.path.dirname(response), exist_ok=True)
        with open(response, "w", encoding="utf-8") as f:
            json.dump({"score_task_id": "task-1", "scores": [], "deductions": []}, f)

        semantic_job.claim_job(job["job_path"], claimed_by="score-agent")
        done = semantic_job.complete_job(job["job_path"], response)

        assert done["status"] == "completed"
        assert done["response_path"] == "评分/assessment.json"


def test_complete_rejects_schema_type_mismatch():
    with tempfile.TemporaryDirectory() as root:
        job = semantic_job.create_job(
            root,
            semantic_kind="score_assessment",
            prompt="prompt",
            response_out="评分/assessment.json",
            required_fields=["score_task_id", "scores", "deductions"],
        )
        response = os.path.join(root, "bad.json")
        with open(response, "w", encoding="utf-8") as f:
            json.dump({"score_task_id": "task-1", "scores": {}, "deductions": []}, f)

        semantic_job.claim_job(job["job_path"], claimed_by="score-agent")
        with pytest.raises(ValueError) as exc:
            semantic_job.complete_job(job["job_path"], response)
        assert "scores" in str(exc.value)


def test_semantic_job_lifecycle_claim_block_reopen_review_approve():
    with tempfile.TemporaryDirectory() as root:
        job = semantic_job.create_job(
            root,
            semantic_kind="custom_judgement",
            prompt="prompt",
            response_out="审稿/custom.json",
            required_fields=["ok"],
            assigned_role="specialist_reviewer",
            human_required=True,
            review_required=True,
        )
        assert job["assigned_role"] == "specialist_reviewer"
        assert job["human_required"] is True
        assert job["review_required"] is True

        claimed = semantic_job.claim_job(
            job["job_path"],
            claimed_by="review-agent",
            model_provider="openai",
            model="test-model",
            cost_estimate="low",
        )
        assert claimed["status"] == "claimed"
        assert claimed["attempts"] == 1
        assert claimed["claimed_by"] == "review-agent"
        assert claimed["model_provider"] == "openai"

        blocked = semantic_job.block_job(job["job_path"], reason="missing source")
        assert blocked["status"] == "blocked"
        assert blocked["blocked_reason"] == "missing source"

        reopened = semantic_job.reopen_job(job["job_path"])
        assert reopened["status"] == "open"
        assert reopened["blocked_reason"] == ""

        semantic_job.claim_job(job["job_path"], claimed_by="review-agent")
        response = os.path.join(root, "response.json")
        with open(response, "w", encoding="utf-8") as f:
            json.dump({"ok": True}, f)
        pending = semantic_job.complete_job(job["job_path"], response)
        assert pending["status"] == "review_pending"
        assert pending["response_path"] == "审稿/custom.json"

        approved = semantic_job.approve_job(job["job_path"], reviewer="human-editor")
        assert approved["status"] == "completed"
        assert approved["reviewed_by"] == "human-editor"


def test_reclaim_expired_semantic_job_lease():
    with tempfile.TemporaryDirectory() as root:
        job = semantic_job.create_job(
            root,
            semantic_kind="custom_judgement",
            prompt="prompt",
            response_out="审稿/custom.json",
            required_fields=["ok"],
        )
        claimed = semantic_job.claim_job(job["job_path"], claimed_by="agent-a", lease_sec=-1)
        assert claimed["status"] == "claimed"

        reclaimed = semantic_job.reclaim_job(job["job_path"])
        assert reclaimed["status"] == "open"
        assert reclaimed["claimed_by"] == ""
        assert reclaimed["last_error"]["class"] == "LeaseExpired"

        claimed_again = semantic_job.claim_job(job["job_path"], claimed_by="agent-b")
        assert claimed_again["claimed_by"] == "agent-b"
        assert claimed_again["attempts"] == 2


def test_provenance_lineage_and_openlineage_export():
    with tempfile.TemporaryDirectory() as root:
        source = os.path.join(root, "章节", "第01章.md")
        out = os.path.join(root, "审稿", "review_report.json")
        os.makedirs(os.path.dirname(source), exist_ok=True)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(source, "w", encoding="utf-8") as f:
            f.write("正文\n")
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"kind": "review"}, f)
        append_event(
            root,
            event_type="review_report_written",
            tool="test_review",
            inputs=[source],
            outputs=[out],
            metadata={"run_id": "run-1"},
        )

        hits = events_for_artifact(root, "审稿/review_report.json")
        assert hits[0]["artifact_role"] == "output"
        lineage = lineage_for_artifact(root, "审稿/review_report.json")
        assert lineage["lineage"]["producers"][0]["inputs"][0]["path"] == "章节/第01章.md"
        exported = openlineage_events(root)
        assert exported[0]["run"]["runId"] == "run-1"
        assert exported[0]["outputs"][0]["name"] == "审稿/review_report.json"
