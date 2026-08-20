#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-canon exploration workspace for novel projects.

This tool deliberately writes only below ``<project>/探索/``.  It captures a
human-authored seed before AI/market suggestions, registers immutable draft
snapshots, and records hash-bound editorial decisions.  A
``promote_candidate`` decision creates another non-canon candidate snapshot;
it never writes ``章节/``, ``设定/``, ``审稿/``, ``_进度.md`` or the state ledger.

CLI examples::

    python3 exploration.py <作品根> seed --text "..." --author "作者" \
        --human-first-confirmed
    python3 exploration.py <作品根> register --file /tmp/scene.md \
        --title "角色试镜" --kind character_audition --creator "作者" \
        --authorship human --seed-id seed_...
    python3 exploration.py <作品根> status --json
    python3 exploration.py <作品根> decide --draft-id draft_... \
        --decision promote_candidate --expected-sha256 <sha256> \
        --reviewer "作者" --reason "发现了角色真正害怕的事" --target blueprint
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from store import atomic_write_json, file_lock


SCHEMA_VERSION = 1
MANIFEST_KIND = "novel_exploration_manifest"
SEED_KIND = "novel_human_seed"
DRAFT_KIND = "novel_exploration_draft"
DECISION_KIND = "novel_exploration_decision"

EXPLORATION_DIR = "探索"
MANIFEST_REL = "探索/manifest.json"
LOCK_REL = "探索/.exploration.lock"

DRAFT_KINDS = (
    "character_audition",
    "scene_probe",
    "pov_probe",
    "voice_probe",
    "structure_probe",
    "ending_probe",
    "other",
)
AUTHORSHIP_KINDS = ("human", "ai-assisted", "ai-generated")
DECISIONS = ("promote_candidate", "hold", "reject")
TARGETS = ("blueprint", "setting", "outline", "demo", "chapter", "style", "other")
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class ExplorationError(ValueError):
    """Raised when an exploration operation would violate its safety contract."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _new_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return f"{prefix}_{stamp}_{uuid.uuid4().hex[:10]}"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_bytes(path: str, payload: bytes) -> None:
    """Crash-safe same-directory byte write without newline/encoding changes."""
    directory = os.path.dirname(path) or "."
    os.makedirs(directory, exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}.{uuid.uuid4().hex[:8]}"
    try:
        with open(tmp, "xb") as f:
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        try:
            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except (OSError, AttributeError):  # pragma: no cover - non-POSIX fallback.
            pass
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def _project_root(project_root: str) -> str:
    root = os.path.abspath(project_root)
    if not os.path.isdir(root):
        raise ExplorationError(f"找不到作品根：{root}")
    if not (os.path.isfile(os.path.join(root, "_meta.json")) or
            os.path.isfile(os.path.join(root, "_进度.md"))):
        raise ExplorationError("目标目录不像 novel 作品根：缺 _meta.json 与 _进度.md")
    return root


def _exploration_path(root: str, rel_path: str) -> str:
    """Resolve a manifest path and reject traversal/symlink escape."""
    if not isinstance(rel_path, str) or not rel_path.strip():
        raise ExplorationError("探索产物路径为空")
    root_real = os.path.realpath(root)
    exploration_real = os.path.realpath(os.path.join(root_real, EXPLORATION_DIR))
    try:
        exploration_inside_root = os.path.commonpath([exploration_real, root_real]) == root_real
    except ValueError:
        exploration_inside_root = False
    if not exploration_inside_root:
        raise ExplorationError(
            f"作品内 {EXPLORATION_DIR}/ 解析到作品根之外，拒绝读写：{exploration_real}"
        )
    candidate = os.path.realpath(os.path.join(root_real, rel_path.replace("/", os.sep)))
    try:
        inside = os.path.commonpath([candidate, exploration_real]) == exploration_real
    except ValueError:
        inside = False
    if not inside:
        raise ExplorationError(f"探索 manifest 含越界路径：{rel_path}")
    return candidate


def _blank_manifest() -> dict[str, Any]:
    now = _now()
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": MANIFEST_KIND,
        "canon_status": "non_canon",
        "formal_pipeline_effect": "none",
        "created_at": now,
        "updated_at": now,
        "seeds": [],
        "drafts": [],
        "decisions": [],
    }


def _load_manifest(root: str, *, missing_ok: bool = True) -> dict[str, Any]:
    path = _exploration_path(root, MANIFEST_REL)
    if not os.path.exists(path):
        if missing_ok:
            return _blank_manifest()
        raise ExplorationError(f"探索 manifest 不存在：{MANIFEST_REL}")
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise ExplorationError(f"探索 manifest 无法读取：{exc}") from exc
    if not isinstance(payload, dict) or payload.get("kind") != MANIFEST_KIND:
        raise ExplorationError("探索 manifest kind 不合法，拒绝覆盖")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ExplorationError(
            f"不支持的探索 manifest schema_version={payload.get('schema_version')}"
        )
    for key in ("seeds", "drafts", "decisions"):
        if not isinstance(payload.get(key), list):
            raise ExplorationError(f"探索 manifest.{key} 必须是数组")
    return payload


def _write_manifest(root: str, manifest: dict[str, Any]) -> str:
    manifest["updated_at"] = _now()
    path = _exploration_path(root, MANIFEST_REL)
    atomic_write_json(path, manifest)
    return path


def _decode_text(payload: bytes, label: str) -> str:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExplorationError(f"{label} 必须是 UTF-8 文本") from exc
    if not text.strip():
        raise ExplorationError(f"{label} 为空")
    return text


def _read_text_file(path: str, label: str) -> tuple[bytes, str]:
    source = os.path.abspath(path)
    if not os.path.isfile(source):
        raise ExplorationError(f"找不到{label}：{source}")
    with open(source, "rb") as f:
        payload = f.read()
    _decode_text(payload, label)
    return payload, source


def _find(items: list[dict[str, Any]], key: str, value: str, label: str) -> dict[str, Any]:
    found = next((item for item in items if item.get(key) == value), None)
    if not found:
        raise ExplorationError(f"找不到{label}：{value}")
    return found


def _verify_bound_file(root: str, record: dict[str, Any], *, label: str) -> tuple[str, str]:
    rel_path = record.get("snapshot_path")
    expected = str(record.get("sha256") or "")
    if not SHA256_RE.fullmatch(expected):
        raise ExplorationError(f"{label}登记的 sha256 不合法")
    path = _exploration_path(root, rel_path)
    if not os.path.isfile(path):
        raise ExplorationError(f"{label}快照缺失：{rel_path}")
    current = sha256_file(path)
    if current != expected:
        raise ExplorationError(
            f"{label}快照已变化：登记 {expected}，当前 {current}；请作为新版本重新登记"
        )
    return path, current


def _verify_sidecar(root: str, record: dict[str, Any], *, label: str) -> tuple[str, str]:
    """Verify a sidecar whose non-recursive hash binding lives in manifest."""
    rel_path = record.get("metadata_path")
    expected = str(record.get("metadata_sha256") or "")
    if not isinstance(rel_path, str) or not rel_path.strip():
        raise ExplorationError(f"{label}缺 metadata_path")
    if not SHA256_RE.fullmatch(expected):
        raise ExplorationError(f"{label}缺 manifest 绑定的 metadata_sha256")
    path = _exploration_path(root, rel_path)
    if not os.path.isfile(path):
        raise ExplorationError(f"{label} sidecar 缺失：{rel_path}")
    current = sha256_file(path)
    if current != expected:
        raise ExplorationError(
            f"{label} sidecar 已变化：登记 {expected}，当前 {current}；拒绝沿用旧绑定"
        )
    return path, current


def _verify_bound_record(root: str, record: dict[str, Any], *, label: str) -> tuple[str, str]:
    path, current = _verify_bound_file(root, record, label=label)
    _verify_sidecar(root, record, label=label)
    return path, current


def _artifact_integrity(root: str, rel_path: Any, expected_sha256: Any) -> dict[str, Any]:
    """Return a read-only integrity result for one manifest-bound artifact."""
    result = {
        "path": rel_path,
        "expected_sha256": expected_sha256,
        "exists": False,
        "current_sha256": None,
        "integrity": "invalid",
    }
    if not isinstance(rel_path, str) or not rel_path.strip():
        result.update({"integrity": "unbound", "error": "missing path binding"})
        return result
    if not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(expected_sha256):
        result.update({"integrity": "unbound", "error": "missing or invalid sha256 binding"})
        return result
    try:
        path = _exploration_path(root, rel_path)
        result["exists"] = os.path.isfile(path)
        result["current_sha256"] = sha256_file(path) if result["exists"] else None
        result["integrity"] = "ok" if result["current_sha256"] == expected_sha256 else "stale"
    except (ExplorationError, OSError) as exc:
        result["error"] = str(exc)
    return result


def capture_human_seed(
    project_root: str,
    *,
    text: str | None = None,
    from_file: str | None = None,
    author: str,
    label: str = "",
    human_first_confirmed: bool,
) -> dict[str, Any]:
    """Freeze an exact human-authored seed before AI/market suggestion exposure."""
    root = _project_root(project_root)
    if bool(text is not None) == bool(from_file is not None):
        raise ExplorationError("seed 必须且只能提供 --text 或 --from-file 之一")
    if not str(author or "").strip():
        raise ExplorationError("seed 必须记录非空作者/确认人")
    if not human_first_confirmed:
        raise ExplorationError(
            "未确认这是 AI/市场建议出现前的人类原始输入；拒绝把后见想法伪标为 human-first"
        )

    if from_file is not None:
        payload, source = _read_text_file(from_file, "原始种子文件")
        source_info = {"mode": "file", "source_name": os.path.basename(source)}
    else:
        payload = str(text).encode("utf-8")
        _decode_text(payload, "原始种子")
        source_info = {"mode": "inline"}

    seed_id = _new_id("seed")
    seed_rel = f"探索/种子/{seed_id}.md"
    meta_rel = f"探索/种子/{seed_id}.json"
    seed_path = _exploration_path(root, seed_rel)
    meta_path = _exploration_path(root, meta_rel)
    record = {
        "schema_version": SCHEMA_VERSION,
        "kind": SEED_KIND,
        "seed_id": seed_id,
        "status": "frozen",
        "canon_status": "non_canon",
        "captured_at": _now(),
        "author": str(author).strip(),
        "label": str(label or "").strip(),
        "capture_claim": {
            "kind": "explicit_human_first_confirmation",
            "confirmed": True,
            "confirmed_by": str(author).strip(),
            "meaning": "human-authored before AI or market suggestions were shown",
        },
        "source": source_info,
        "snapshot_path": seed_rel,
        "metadata_path": meta_rel,
        "sha256": sha256_bytes(payload),
        "size_bytes": len(payload),
        "formal_pipeline_effect": "none",
    }

    lock_path = _exploration_path(root, LOCK_REL)
    with file_lock(lock_path):
        manifest = _load_manifest(root)
        _atomic_write_bytes(seed_path, payload)
        atomic_write_json(meta_path, record)
        manifest_record = dict(record)
        # Sidecar 不写自身 hash，避免递归；只有 manifest 持有其 hash binding。
        manifest_record["metadata_sha256"] = sha256_file(meta_path)
        manifest["seeds"].append(manifest_record)
        _write_manifest(root, manifest)
    return manifest_record


def register_draft(
    project_root: str,
    *,
    source_file: str,
    title: str,
    exploration_kind: str,
    creator: str,
    authorship: str,
    question: str = "",
    seed_ids: list[str] | None = None,
    parent_draft_id: str | None = None,
) -> dict[str, Any]:
    """Copy a text file into an immutable non-canon exploration snapshot."""
    root = _project_root(project_root)
    if exploration_kind not in DRAFT_KINDS:
        raise ExplorationError(f"未知探索稿类型：{exploration_kind}")
    if authorship not in AUTHORSHIP_KINDS:
        raise ExplorationError(f"未知 authorship：{authorship}")
    if not str(title or "").strip() or not str(creator or "").strip():
        raise ExplorationError("探索稿必须有非空 title 与 creator")
    payload, source = _read_text_file(source_file, "探索稿")
    suffix = os.path.splitext(source)[1].lower()
    if suffix not in (".md", ".txt"):
        raise ExplorationError("探索稿只接受 UTF-8 .md / .txt")

    draft_id = _new_id("draft")
    draft_rel = f"探索/草稿/{draft_id}{suffix}"
    meta_rel = f"探索/草稿/{draft_id}.json"
    draft_path = _exploration_path(root, draft_rel)
    meta_path = _exploration_path(root, meta_rel)
    lock_path = _exploration_path(root, LOCK_REL)

    with file_lock(lock_path):
        manifest = _load_manifest(root)
        bindings: list[dict[str, Any]] = []
        seen: set[str] = set()
        for seed_id in seed_ids or []:
            if seed_id in seen:
                continue
            seen.add(seed_id)
            seed = _find(manifest["seeds"], "seed_id", seed_id, "human seed")
            _verify_bound_record(root, seed, label=f"human seed {seed_id}")
            bindings.append({
                "seed_id": seed_id,
                "snapshot_path": seed["snapshot_path"],
                "sha256": seed["sha256"],
                "metadata_path": seed["metadata_path"],
                "metadata_sha256": seed["metadata_sha256"],
            })

        parent_binding = None
        if parent_draft_id:
            parent = _find(manifest["drafts"], "draft_id", parent_draft_id, "父探索稿")
            _verify_bound_record(root, parent, label=f"父探索稿 {parent_draft_id}")
            parent_binding = {
                "draft_id": parent_draft_id,
                "snapshot_path": parent["snapshot_path"],
                "sha256": parent["sha256"],
                "metadata_path": parent["metadata_path"],
                "metadata_sha256": parent["metadata_sha256"],
            }

        record = {
            "schema_version": SCHEMA_VERSION,
            "kind": DRAFT_KIND,
            "draft_id": draft_id,
            "status": "registered_non_canon",
            "canon_status": "non_canon",
            "registered_at": _now(),
            "title": str(title).strip(),
            "exploration_kind": exploration_kind,
            "question": str(question or "").strip(),
            "creator": str(creator).strip(),
            "authorship": authorship,
            "source_name": os.path.basename(source),
            "snapshot_path": draft_rel,
            "metadata_path": meta_rel,
            "sha256": sha256_bytes(payload),
            "size_bytes": len(payload),
            "seed_bindings": bindings,
            "parent_draft_binding": parent_binding,
            "formal_pipeline_effect": "none",
            "requires_state_delta": False,
        }
        _atomic_write_bytes(draft_path, payload)
        atomic_write_json(meta_path, record)
        manifest_record = dict(record)
        manifest_record["metadata_sha256"] = sha256_file(meta_path)
        manifest["drafts"].append(manifest_record)
        _write_manifest(root, manifest)
    return manifest_record


def record_decision(
    project_root: str,
    *,
    draft_id: str,
    decision: str,
    reviewer: str,
    reason: str,
    expected_sha256: str | None = None,
    target: str | None = None,
) -> dict[str, Any]:
    """Record a hash-bound decision and optionally create a non-canon candidate."""
    root = _project_root(project_root)
    if decision not in DECISIONS:
        raise ExplorationError(f"未知 decision：{decision}")
    if not str(reviewer or "").strip() or not str(reason or "").strip():
        raise ExplorationError("决策必须有非空 reviewer 与 reason")
    if target is not None and target not in TARGETS:
        raise ExplorationError(f"未知 target：{target}")
    if decision == "promote_candidate":
        if not expected_sha256 or not SHA256_RE.fullmatch(expected_sha256):
            raise ExplorationError("promote_candidate 必须显式传当前 --expected-sha256")
        if target is None:
            raise ExplorationError("promote_candidate 必须声明 --target（仅表达拟进入哪个正式阶段）")

    # Validate the exploration root before file_lock creates its parent.  Without
    # this preflight, a project-local ``探索`` symlink could make the lock itself
    # the first out-of-scope write even though later artifact checks reject it.
    _exploration_path(root, EXPLORATION_DIR)
    lock_path = _exploration_path(root, LOCK_REL)
    with file_lock(lock_path):
        manifest = _load_manifest(root, missing_ok=False)
        draft = _find(manifest["drafts"], "draft_id", draft_id, "探索稿")
        draft_path, current_sha = _verify_bound_record(root, draft, label=f"探索稿 {draft_id}")
        if expected_sha256 and current_sha != expected_sha256:
            raise ExplorationError(
                f"显式选择的 hash 与当前探索稿不符：expected={expected_sha256}, current={current_sha}"
            )

        decision_id = _new_id("decision")
        decision_rel = f"探索/决策/{decision_id}.json"
        candidate_rel = None
        candidate_sha = None
        if decision == "promote_candidate":
            suffix = os.path.splitext(draft_path)[1].lower() or ".md"
            candidate_rel = (
                f"探索/晋升候选/{draft_id}__{current_sha[:12]}__{decision_id[-10:]}{suffix}"
            )
            candidate_path = _exploration_path(root, candidate_rel)
            with open(draft_path, "rb") as f:
                candidate_payload = f.read()
            _atomic_write_bytes(candidate_path, candidate_payload)
            candidate_sha = sha256_file(candidate_path)
            if candidate_sha != current_sha:  # pragma: no cover - filesystem corruption guard.
                raise ExplorationError("晋升候选复制后 hash 不一致，拒绝登记")

        payload = {
            "schema_version": SCHEMA_VERSION,
            "kind": DECISION_KIND,
            "decision_id": decision_id,
            "created_at": _now(),
            "decision": decision,
            "reviewer": str(reviewer).strip(),
            "reason": str(reason).strip(),
            "intended_formal_target": target,
            "draft_binding": {
                "draft_id": draft_id,
                "snapshot_path": draft["snapshot_path"],
                "sha256": current_sha,
                "metadata_path": draft["metadata_path"],
                "metadata_sha256": draft["metadata_sha256"],
                "seed_bindings": draft.get("seed_bindings") or [],
                "parent_draft_binding": draft.get("parent_draft_binding"),
            },
            "candidate": ({
                "path": candidate_rel,
                "sha256": candidate_sha,
                "canon_status": "non_canon_candidate",
            } if candidate_rel else None),
            "canon_effect": "none_until_separate_formal_review_and_integration",
            "formal_write_performed": False,
            "next_step": (
                "人工复核候选后，在正式蓝图/设定/章纲/Demo/章节流程中单独吸收并重跑其批准或 gate；"
                "本决策不等于正史。"
                if decision == "promote_candidate" else
                "保留为探索证据；不进入正式流程。"
            ),
        }
        decision_path = _exploration_path(root, decision_rel)
        atomic_write_json(decision_path, payload)
        decision_sha = sha256_file(decision_path)
        manifest["decisions"].append({
            "decision_id": decision_id,
            "decision": decision,
            "draft_id": draft_id,
            "draft_sha256": current_sha,
            "decision_path": decision_rel,
            "decision_sha256": decision_sha,
            "candidate_path": candidate_rel,
            "candidate_sha256": candidate_sha,
            "created_at": payload["created_at"],
        })
        draft["latest_decision"] = decision
        draft["latest_decision_id"] = decision_id
        if decision == "promote_candidate":
            draft["status"] = "promoted_non_canon_candidate"
        elif decision == "hold":
            draft["status"] = "on_hold_non_canon"
        else:
            draft["status"] = "rejected_non_canon"
        _write_manifest(root, manifest)
    return payload


def exploration_status(project_root: str) -> dict[str, Any]:
    """Return integrity status without creating or modifying project files."""
    root = _project_root(project_root)
    _exploration_path(root, EXPLORATION_DIR)
    manifest_path = _exploration_path(root, MANIFEST_REL)
    if not os.path.exists(manifest_path):
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": "novel_exploration_status",
            "initialized": False,
            "canon_status": "non_canon",
            "formal_pipeline_effect": "none",
            "seeds": [],
            "drafts": [],
            "decisions": [],
            "integrity_ok": True,
        }

    manifest = _load_manifest(root, missing_ok=False)
    groups: dict[str, list[dict[str, Any]]] = {"seeds": [], "drafts": [], "decisions": []}
    integrity_ok = True
    for key, id_key in (("seeds", "seed_id"), ("drafts", "draft_id")):
        for record in manifest[key]:
            snapshot = _artifact_integrity(root, record.get("snapshot_path"), record.get("sha256"))
            sidecar = _artifact_integrity(
                root, record.get("metadata_path"), record.get("metadata_sha256")
            )
            states = {snapshot["integrity"], sidecar["integrity"]}
            combined = "ok" if states == {"ok"} else (
                "invalid" if "invalid" in states else
                "unbound" if "unbound" in states else
                "stale"
            )
            item = {
                id_key: record.get(id_key),
                # Keep top-level snapshot fields stable for CLI callers that
                # copy current_sha256 into decide --expected-sha256.
                "path": snapshot["path"],
                "expected_sha256": snapshot["expected_sha256"],
                "exists": snapshot["exists"],
                "current_sha256": snapshot["current_sha256"],
                "snapshot": snapshot,
                "sidecar": sidecar,
                "integrity": combined,
            }
            if item["integrity"] != "ok":
                integrity_ok = False
            groups[key].append(item)

    for record in manifest["decisions"]:
        item = {
            "decision_id": record.get("decision_id"),
            "decision": record.get("decision"),
            "draft_id": record.get("draft_id"),
            "path": record.get("decision_path"),
            "expected_sha256": record.get("decision_sha256"),
        }
        try:
            path = _exploration_path(root, record.get("decision_path"))
            item["exists"] = os.path.isfile(path)
            item["current_sha256"] = sha256_file(path) if item["exists"] else None
            item["integrity"] = "ok" if item["current_sha256"] == item["expected_sha256"] else "stale"
            candidate_rel = record.get("candidate_path")
            if candidate_rel:
                candidate_path = _exploration_path(root, candidate_rel)
                candidate_current = sha256_file(candidate_path) if os.path.isfile(candidate_path) else None
                item["candidate"] = {
                    "path": candidate_rel,
                    "expected_sha256": record.get("candidate_sha256"),
                    "current_sha256": candidate_current,
                    "integrity": "ok" if candidate_current == record.get("candidate_sha256") else "stale",
                }
                if item["candidate"]["integrity"] != "ok":
                    integrity_ok = False
        except (ExplorationError, OSError) as exc:
            item.update({"exists": False, "current_sha256": None, "integrity": "invalid", "error": str(exc)})
        if item["integrity"] != "ok":
            integrity_ok = False
        groups["decisions"].append(item)

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "novel_exploration_status",
        "initialized": True,
        "canon_status": "non_canon",
        "formal_pipeline_effect": "none",
        "manifest_path": MANIFEST_REL,
        "integrity_ok": integrity_ok,
        **groups,
    }


def _print_status(status: dict[str, Any]) -> None:
    print("# 非正史探索区")
    print(f"initialized: {status['initialized']}")
    print(f"integrity_ok: {status['integrity_ok']}")
    print("formal_pipeline_effect: none")
    for key, label in (("seeds", "human seeds"), ("drafts", "drafts"), ("decisions", "decisions")):
        print(f"{label}: {len(status[key])}")
        for item in status[key]:
            item_id = item.get("seed_id") or item.get("draft_id") or item.get("decision_id")
            print(f"- {item_id}: {item.get('integrity')} {item.get('path')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="novel 非正史探索区：human-first seed、探索稿、hash-bound 晋升决策")
    parser.add_argument("project_root", help="novel 作品根")
    sub = parser.add_subparsers(dest="command", required=True)

    seed = sub.add_parser("seed", help="冻结 AI/市场建议出现前的人类原始种子")
    seed_source = seed.add_mutually_exclusive_group(required=True)
    seed_source.add_argument("--text", help="原始种子原文；较长内容建议用 --from-file")
    seed_source.add_argument("--from-file", help="UTF-8 原始种子文件")
    seed.add_argument("--author", required=True, help="作者/确认人")
    seed.add_argument("--label", default="", help="简短标签")
    seed.add_argument("--human-first-confirmed", action="store_true", help="显式确认此内容形成于 AI/市场建议之前")

    register = sub.add_parser("register", help="登记一个不可变的非正史探索稿快照")
    register.add_argument("--file", required=True, help="UTF-8 .md/.txt 探索稿")
    register.add_argument("--title", required=True)
    register.add_argument("--kind", required=True, choices=DRAFT_KINDS)
    register.add_argument("--creator", required=True)
    register.add_argument("--authorship", required=True, choices=AUTHORSHIP_KINDS)
    register.add_argument("--question", default="", help="本次试写要回答的问题")
    register.add_argument("--seed-id", action="append", default=[], help="绑定 human seed；可重复")
    register.add_argument("--parent-draft-id", help="绑定父探索稿；修改稿应登记为新 draft")

    decide = sub.add_parser("decide", help="登记 hash-bound 的候选晋升/搁置/否决决定")
    decide.add_argument("--draft-id", required=True)
    decide.add_argument("--decision", required=True, choices=DECISIONS)
    decide.add_argument("--expected-sha256", help="promote_candidate 必填；从 status 读取当前 hash")
    decide.add_argument("--reviewer", required=True)
    decide.add_argument("--reason", required=True)
    decide.add_argument("--target", choices=TARGETS, help="拟进入的正式阶段；仅候选意图，不执行正式写入")

    status = sub.add_parser("status", help="只读检查探索区及所有 hash")
    status.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "seed":
            record = capture_human_seed(
                args.project_root,
                text=args.text,
                from_file=args.from_file,
                author=args.author,
                label=args.label,
                human_first_confirmed=args.human_first_confirmed,
            )
            print(json.dumps(record, ensure_ascii=False, indent=2))
        elif args.command == "register":
            record = register_draft(
                args.project_root,
                source_file=args.file,
                title=args.title,
                exploration_kind=args.kind,
                creator=args.creator,
                authorship=args.authorship,
                question=args.question,
                seed_ids=args.seed_id,
                parent_draft_id=args.parent_draft_id,
            )
            print(json.dumps(record, ensure_ascii=False, indent=2))
        elif args.command == "decide":
            record = record_decision(
                args.project_root,
                draft_id=args.draft_id,
                decision=args.decision,
                reviewer=args.reviewer,
                reason=args.reason,
                expected_sha256=args.expected_sha256,
                target=args.target,
            )
            print(json.dumps(record, ensure_ascii=False, indent=2))
        else:
            status = exploration_status(args.project_root)
            if args.json:
                print(json.dumps(status, ensure_ascii=False, indent=2))
            else:
                _print_status(status)
    except ExplorationError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
