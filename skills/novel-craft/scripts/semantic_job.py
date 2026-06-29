#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create and complete AI-agent semantic jobs for novel workflows.

Deterministic scripts should calculate structure and provenance. When the next
step needs semantic judgement, this helper writes a small job artifact that an
AI agent can consume in one pass: read prompt, produce JSON, validate fields,
and place the response at the script's expected path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from typing import Any

try:
    from semantic_schemas import schema_contract, validate_payload
except ImportError:  # pragma: no cover - compatibility if helper is copied alone
    schema_contract = None
    validate_payload = None
try:
    from provenance import append_event
except ImportError:  # pragma: no cover - provenance is additive, not required
    append_event = None


JOB_KIND = "novel_semantic_job"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _now_ts() -> float:
    return time.time()


def _iso_from_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def project_path(root: str, path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(root, path)


def _safe_slug(value: str) -> str:
    out = []
    for ch in str(value or ""):
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch in " .:/\\":
            out.append("_")
    slug = "".join(out).strip("_")
    return slug[:80] or "semantic"


def create_job(root: str, *, semantic_kind: str, prompt: str, response_out: str,
               required_fields: list[str] | None = None,
               complete_command: str = "", metadata: dict[str, Any] | None = None,
               schema_ref: str | None = None,
               source_snapshot: dict[str, Any] | None = None,
               response_contract: dict[str, Any] | None = None,
               assigned_role: str = "",
               human_required: bool = False,
               review_required: bool = False,
               model_provider: str = "",
               model: str = "",
               cost_estimate: str = "") -> dict[str, Any]:
    root = os.path.abspath(root)
    prompt = str(prompt or "")
    required_fields = list(required_fields or [])
    prompt_hash = _sha(prompt)
    job_id = f"{_safe_slug(semantic_kind)}_{prompt_hash[:12]}"
    schema_ref = str(schema_ref or semantic_kind or "").strip()
    job_dir = os.path.join(root, "语义任务")
    prompt_path = os.path.join(job_dir, f"{job_id}.prompt.md")
    job_path = os.path.join(job_dir, f"{job_id}.json")
    response_abs = project_path(root, response_out)
    if response_contract is None:
        response_contract = schema_contract(schema_ref) if schema_contract else {
            "schema_ref": schema_ref,
            "required": {field: "present" for field in required_fields},
        }
    payload = {
        "schema_version": 1,
        "kind": JOB_KIND,
        "job_id": job_id,
        "semantic_kind": semantic_kind,
        "schema_ref": schema_ref,
        "status": "open",
        "created_at": _now(),
        "updated_at": _now(),
        "project_root": root,
        "prompt_path": os.path.relpath(prompt_path, root).replace(os.sep, "/"),
        "prompt_hash": prompt_hash,
        "response_out": os.path.relpath(response_abs, root).replace(os.sep, "/"),
        "required_fields": required_fields,
        "response_contract": response_contract,
        "source_snapshot": source_snapshot or {},
        "assigned_role": assigned_role,
        "claimed_by": "",
        "attempts": 0,
        "lease_expires_at": None,
        "lease_expires_at_iso": "",
        "model_provider": model_provider,
        "model": model,
        "cost_estimate": cost_estimate,
        "human_required": bool(human_required),
        "review_required": bool(review_required),
        "blocked_reason": "",
        "rejected_reason": "",
        "complete_command": complete_command,
        "metadata": metadata or {},
    }
    _write_text(prompt_path, prompt.rstrip() + "\n")
    _write_json(job_path, payload)
    if append_event:
        append_event(
            root,
            event_type="semantic_job_created",
            tool="novel-craft/scripts/semantic_job.py",
            outputs=[prompt_path, job_path],
            metadata={
                "job_id": job_id,
                "semantic_kind": semantic_kind,
                "schema_ref": schema_ref,
                "response_out": payload["response_out"],
            },
        )
    payload["job_path"] = job_path
    return payload


def _save_job(job_path: str, job: dict[str, Any]) -> dict[str, Any]:
    job["updated_at"] = _now()
    _write_json(job_path, job)
    return job


def _event_for_job(root: str, event_type: str, job_path: str, job: dict[str, Any],
                   metadata: dict[str, Any] | None = None) -> None:
    if not append_event:
        return
    meta = {
        "job_id": job.get("job_id"),
        "semantic_kind": job.get("semantic_kind"),
        "schema_ref": job.get("schema_ref"),
        "status": job.get("status"),
    }
    meta.update(metadata or {})
    append_event(
        root,
        event_type=event_type,
        tool="novel-craft/scripts/semantic_job.py",
        outputs=[job_path],
        metadata=meta,
    )


def _lease_expired(job: dict[str, Any]) -> bool:
    expires = float(job.get("lease_expires_at") or 0)
    return bool(expires and expires < _now_ts())


def _clear_lease(job: dict[str, Any]) -> None:
    job["lease_expires_at"] = None
    job["lease_expires_at_iso"] = ""


def claim_job(job_path: str, *, claimed_by: str, model_provider: str = "",
              model: str = "", cost_estimate: str = "", lease_sec: int = 3600) -> dict[str, Any]:
    job_path = os.path.abspath(job_path)
    job = _load_json(job_path)
    if not isinstance(job, dict) or job.get("kind") != JOB_KIND:
        raise ValueError(f"not a semantic job: {job_path}")
    if job.get("status") == "claimed" and not _lease_expired(job):
        raise ValueError(f"job {job.get('job_id')} is already claimed by {job.get('claimed_by')}")
    if job.get("status") not in {"open", "blocked", "rejected", "claimed"}:
        raise ValueError(f"job {job.get('job_id')} cannot be claimed from {job.get('status')}")
    root = str(job.get("project_root") or os.path.dirname(os.path.dirname(job_path)))
    job["status"] = "claimed"
    job["claimed_by"] = claimed_by
    job["attempts"] = int(job.get("attempts") or 0) + 1
    job["lease_expires_at"] = _now_ts() + int(lease_sec or 3600)
    job["lease_expires_at_iso"] = _iso_from_ts(float(job["lease_expires_at"]))
    if model_provider:
        job["model_provider"] = model_provider
    if model:
        job["model"] = model
    if cost_estimate:
        job["cost_estimate"] = cost_estimate
    job["blocked_reason"] = ""
    job["rejected_reason"] = ""
    _save_job(job_path, job)
    _event_for_job(
        root,
        "semantic_job_claimed",
        job_path,
        job,
        {"claimed_by": claimed_by, "lease_expires_at": job.get("lease_expires_at_iso")},
    )
    return job


def block_job(job_path: str, *, reason: str) -> dict[str, Any]:
    job_path = os.path.abspath(job_path)
    job = _load_json(job_path)
    if not isinstance(job, dict) or job.get("kind") != JOB_KIND:
        raise ValueError(f"not a semantic job: {job_path}")
    root = str(job.get("project_root") or os.path.dirname(os.path.dirname(job_path)))
    job["status"] = "blocked"
    job["blocked_reason"] = reason
    _clear_lease(job)
    _save_job(job_path, job)
    _event_for_job(root, "semantic_job_blocked", job_path, job, {"reason": reason})
    return job


def reject_job(job_path: str, *, reason: str) -> dict[str, Any]:
    job_path = os.path.abspath(job_path)
    job = _load_json(job_path)
    if not isinstance(job, dict) or job.get("kind") != JOB_KIND:
        raise ValueError(f"not a semantic job: {job_path}")
    root = str(job.get("project_root") or os.path.dirname(os.path.dirname(job_path)))
    job["status"] = "rejected"
    job["rejected_reason"] = reason
    _clear_lease(job)
    _save_job(job_path, job)
    _event_for_job(root, "semantic_job_rejected", job_path, job, {"reason": reason})
    return job


def reopen_job(job_path: str) -> dict[str, Any]:
    job_path = os.path.abspath(job_path)
    job = _load_json(job_path)
    if not isinstance(job, dict) or job.get("kind") != JOB_KIND:
        raise ValueError(f"not a semantic job: {job_path}")
    root = str(job.get("project_root") or os.path.dirname(os.path.dirname(job_path)))
    job["status"] = "open"
    job["claimed_by"] = ""
    job["blocked_reason"] = ""
    job["rejected_reason"] = ""
    _clear_lease(job)
    _save_job(job_path, job)
    _event_for_job(root, "semantic_job_reopened", job_path, job)
    return job


def reclaim_job(job_path: str) -> dict[str, Any]:
    job_path = os.path.abspath(job_path)
    job = _load_json(job_path)
    if not isinstance(job, dict) or job.get("kind") != JOB_KIND:
        raise ValueError(f"not a semantic job: {job_path}")
    if job.get("status") != "claimed":
        raise ValueError(f"job {job.get('job_id')} is not claimed")
    if not _lease_expired(job):
        raise ValueError(f"job {job.get('job_id')} lease has not expired")
    root = str(job.get("project_root") or os.path.dirname(os.path.dirname(job_path)))
    previous_claimed_by = job.get("claimed_by") or ""
    job["status"] = "open"
    job["claimed_by"] = ""
    job["last_error"] = {"class": "LeaseExpired", "message": "semantic job lease expired", "at": _now()}
    _clear_lease(job)
    _save_job(job_path, job)
    _event_for_job(root, "semantic_job_reclaimed", job_path, job, {"previous_claimed_by": previous_claimed_by})
    return job


def approve_job(job_path: str, *, reviewer: str = "") -> dict[str, Any]:
    job_path = os.path.abspath(job_path)
    job = _load_json(job_path)
    if not isinstance(job, dict) or job.get("kind") != JOB_KIND:
        raise ValueError(f"not a semantic job: {job_path}")
    if job.get("status") != "review_pending":
        raise ValueError(f"job {job.get('job_id')} is not review_pending")
    root = str(job.get("project_root") or os.path.dirname(os.path.dirname(job_path)))
    job["status"] = "completed"
    job["completed_at"] = _now()
    job["reviewed_by"] = reviewer
    _clear_lease(job)
    _save_job(job_path, job)
    _event_for_job(root, "semantic_job_approved", job_path, job, {"reviewer": reviewer})
    return job


def validate_response(payload: Any, required_fields: list[str], schema_ref: str = "") -> list[str]:
    if validate_payload:
        return validate_payload(schema_ref, payload, required_fields)
    issues: list[str] = []
    if not isinstance(payload, dict):
        return ["response must be a JSON object"]
    for field in required_fields:
        if field not in payload:
            issues.append(f"missing required field: {field}")
    return issues


def complete_job(
    job_path: str,
    response_path: str,
    *,
    copy_response: bool = True,
    allow_unclaimed: bool = False,
    completed_by: str = "",
) -> dict[str, Any]:
    job_path = os.path.abspath(job_path)
    job = _load_json(job_path)
    if not isinstance(job, dict) or job.get("kind") != JOB_KIND:
        raise ValueError(f"not a semantic job: {job_path}")
    root = str(job.get("project_root") or os.path.dirname(os.path.dirname(job_path)))
    if not allow_unclaimed:
        if job.get("status") != "claimed":
            raise ValueError(f"job {job.get('job_id')} must be claimed before completion")
        if _lease_expired(job):
            raise ValueError(f"job {job.get('job_id')} lease expired; reclaim or re-claim before completion")
        if completed_by and job.get("claimed_by") and completed_by != job.get("claimed_by"):
            raise PermissionError(f"job {job.get('job_id')} is claimed by {job.get('claimed_by')}, not {completed_by}")
    response = _load_json(response_path)
    schema_ref = str(job.get("schema_ref") or job.get("semantic_kind") or "")
    issues = validate_response(response, [str(x) for x in job.get("required_fields") or []], schema_ref)
    if issues:
        raise ValueError("; ".join(issues))
    out_path = project_path(root, str(job.get("response_out") or ""))
    if copy_response:
        response_abs = os.path.abspath(response_path)
        out_abs = os.path.abspath(out_path)
        if response_abs != out_abs:
            os.makedirs(os.path.dirname(out_abs), exist_ok=True)
            shutil.copyfile(response_abs, out_abs)
    if job.get("review_required"):
        job["status"] = "review_pending"
        job["response_submitted_at"] = _now()
    else:
        job["status"] = "completed"
        job["completed_at"] = _now()
    _clear_lease(job)
    job["updated_at"] = _now()
    job["response_path"] = os.path.relpath(out_path, root).replace(os.sep, "/")
    job["response_hash"] = _sha(json.dumps(response, ensure_ascii=False, sort_keys=True))
    if completed_by:
        job["completed_by"] = completed_by
    _write_json(job_path, job)
    if append_event:
        event_type = "semantic_job_review_pending" if job.get("status") == "review_pending" else "semantic_job_completed"
        append_event(
            root,
            event_type=event_type,
            tool="novel-craft/scripts/semantic_job.py",
            inputs=[response_path],
            outputs=[out_path, job_path],
            metadata={
                "job_id": job.get("job_id"),
                "semantic_kind": job.get("semantic_kind"),
                "schema_ref": schema_ref,
                "response_hash": job["response_hash"],
            },
        )
    return job


def prompt_from_file(path: str, json_field: str | None = None) -> str:
    if json_field:
        payload = _load_json(path)
        value = payload
        for part in json_field.split("."):
            if not isinstance(value, dict) or part not in value:
                raise KeyError(f"{path} missing JSON field {json_field}")
            value = value[part]
        return str(value)
    with open(path, encoding="utf-8") as f:
        return f.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="novel semantic job helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create", help="create a semantic job")
    create.add_argument("project_root")
    create.add_argument("--kind", required=True)
    create.add_argument("--prompt-file", required=True)
    create.add_argument("--prompt-json-field")
    create.add_argument("--response-out", required=True)
    create.add_argument("--required-field", action="append", default=[])
    create.add_argument("--complete-command", default="")
    create.add_argument("--metadata-json", default="{}")
    create.add_argument("--schema-ref", default="")
    create.add_argument("--source-snapshot-json", default="{}")
    create.add_argument("--assigned-role", default="")
    create.add_argument("--human-required", action="store_true")
    create.add_argument("--review-required", action="store_true")
    create.add_argument("--model-provider", default="")
    create.add_argument("--model", default="")
    create.add_argument("--cost-estimate", default="")

    complete = sub.add_parser("complete", help="validate and complete a semantic job")
    complete.add_argument("job_path")
    complete.add_argument("--response", required=True)
    complete.add_argument("--no-copy-response", action="store_true")
    complete.add_argument("--allow-unclaimed", action="store_true", help="migration escape hatch for legacy unclaimed jobs")
    complete.add_argument("--completed-by", default="")

    show = sub.add_parser("show", help="print a job prompt")
    show.add_argument("job_path")

    claim = sub.add_parser("claim", help="claim a semantic job")
    claim.add_argument("job_path")
    claim.add_argument("--claimed-by", required=True)
    claim.add_argument("--model-provider", default="")
    claim.add_argument("--model", default="")
    claim.add_argument("--cost-estimate", default="")
    claim.add_argument("--lease-sec", type=int, default=3600)

    block = sub.add_parser("block", help="mark a semantic job blocked")
    block.add_argument("job_path")
    block.add_argument("--reason", required=True)

    reject = sub.add_parser("reject", help="reject a semantic job response or task")
    reject.add_argument("job_path")
    reject.add_argument("--reason", required=True)

    reopen = sub.add_parser("reopen", help="reopen a blocked/rejected semantic job")
    reopen.add_argument("job_path")

    reclaim = sub.add_parser("reclaim", help="reopen a claimed semantic job whose lease expired")
    reclaim.add_argument("job_path")

    approve = sub.add_parser("approve", help="approve a review_pending semantic job")
    approve.add_argument("job_path")
    approve.add_argument("--reviewer", default="")

    args = parser.parse_args(argv)
    if args.cmd == "create":
        root = os.path.abspath(args.project_root)
        metadata = json.loads(args.metadata_json or "{}")
        source_snapshot = json.loads(args.source_snapshot_json or "{}")
        prompt = prompt_from_file(args.prompt_file, args.prompt_json_field)
        job = create_job(
            root,
            semantic_kind=args.kind,
            prompt=prompt,
            response_out=args.response_out,
            required_fields=args.required_field,
            complete_command=args.complete_command,
            metadata=metadata,
            schema_ref=args.schema_ref or None,
            source_snapshot=source_snapshot,
            assigned_role=args.assigned_role,
            human_required=args.human_required,
            review_required=args.review_required,
            model_provider=args.model_provider,
            model=args.model,
            cost_estimate=args.cost_estimate,
        )
        print(f"[ok] semantic job → {job['job_path']}")
        print(f"[prompt] {os.path.join(root, job['prompt_path'])}")
        print(f"[response_out] {os.path.join(root, job['response_out'])}")
        return 0
    if args.cmd == "complete":
        try:
            job = complete_job(
                args.job_path,
                args.response,
                copy_response=not args.no_copy_response,
                allow_unclaimed=args.allow_unclaimed,
                completed_by=args.completed_by,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(f"[ok] semantic job completed: {job['job_id']}")
        print(f"[response] {job.get('response_path')}")
        if job.get("complete_command"):
            print(f"[next] {job['complete_command']}")
        return 0
    if args.cmd == "show":
        job = _load_json(args.job_path)
        root = str(job.get("project_root") or os.path.dirname(os.path.dirname(os.path.abspath(args.job_path))))
        prompt_path = project_path(root, str(job.get("prompt_path") or ""))
        with open(prompt_path, encoding="utf-8") as f:
            print(f.read())
        return 0
    if args.cmd == "claim":
        try:
            job = claim_job(
                args.job_path,
                claimed_by=args.claimed_by,
                model_provider=args.model_provider,
                model=args.model,
                cost_estimate=args.cost_estimate,
                lease_sec=args.lease_sec,
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(f"[ok] semantic job claimed: {job['job_id']} by {job.get('claimed_by')}")
        return 0
    if args.cmd == "block":
        try:
            job = block_job(args.job_path, reason=args.reason)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(f"[ok] semantic job blocked: {job['job_id']}")
        return 0
    if args.cmd == "reject":
        try:
            job = reject_job(args.job_path, reason=args.reason)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(f"[ok] semantic job rejected: {job['job_id']}")
        return 0
    if args.cmd == "reopen":
        try:
            job = reopen_job(args.job_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(f"[ok] semantic job reopened: {job['job_id']}")
        return 0
    if args.cmd == "reclaim":
        try:
            job = reclaim_job(args.job_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(f"[ok] semantic job reclaimed: {job['job_id']}")
        return 0
    if args.cmd == "approve":
        try:
            job = approve_job(args.job_path, reviewer=args.reviewer)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 2
        print(f"[ok] semantic job approved: {job['job_id']}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
