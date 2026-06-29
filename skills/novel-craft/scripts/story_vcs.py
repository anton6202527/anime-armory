#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Story VCS: file-level branch/take helper without git.

This tool gives novel projects a small VCS-free safety layer for A/B branches:
branch manifests record base hashes, merge preflight detects conflicts, merges
write audit/provenance events, and rollback restores the pre-merge backups.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from typing import Any

from store import atomic_write_json, file_lock

try:
    from provenance import append_event
except Exception:  # pragma: no cover - provenance is additive
    append_event = None


CORE_FILES = [
    "_进度.md",
    "设定/动态百科.json",
    "设定/foreshadowing_ledger.json",
    "设定/visual_state_ledger.json",
]
BRANCH_KIND = "novel_story_vcs_branch"
MERGE_KIND = "novel_story_vcs_merge"


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rel(root: str, path: str) -> str:
    return os.path.relpath(os.path.abspath(path), os.path.abspath(root)).replace(os.sep, "/")


def safe_name(value: str) -> str:
    name = re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", str(value or "").strip())
    return name.strip("._") or "branch"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(root: str, path: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"path": rel(root, path), "exists": os.path.exists(path)}
    if os.path.isfile(path):
        payload.update({
            "sha256": sha256_file(path),
            "size_bytes": os.path.getsize(path),
            "mtime": datetime.fromtimestamp(os.path.getmtime(path)).isoformat(timespec="seconds"),
        })
    return payload


def get_branch_file_path(base_path: str, branch_name: str) -> str:
    dir_name = os.path.dirname(base_path)
    base_name = os.path.basename(base_path)
    name, ext = os.path.splitext(base_name)
    return os.path.join(dir_name, f"{name}_branch_{safe_name(branch_name)}{ext}")


def branch_file_for_rel(root: str, rel_path: str, branch_name: str) -> str:
    return get_branch_file_path(os.path.join(root, rel_path), branch_name)


def branch_manifest_path(root: str, branch_name: str) -> str:
    return os.path.join(root, "生产数据", "story_vcs_branches", f"{safe_name(branch_name)}.json")


def merge_report_path(root: str, merge_id: str) -> str:
    return os.path.join(root, "生产数据", "story_vcs_merges", f"{safe_name(merge_id)}.json")


def branch_names(root: str) -> list[str]:
    names: set[str] = set()
    manifest_dir = os.path.join(root, "生产数据", "story_vcs_branches")
    if os.path.isdir(manifest_dir):
        for name in os.listdir(manifest_dir):
            if name.endswith(".json"):
                names.add(os.path.splitext(name)[0])
    for rel_path in CORE_FILES:
        directory = os.path.dirname(os.path.join(root, rel_path)) or root
        base = os.path.splitext(os.path.basename(rel_path))[0]
        ext = os.path.splitext(os.path.basename(rel_path))[1]
        if not os.path.isdir(directory):
            continue
        prefix = f"{base}_branch_"
        for name in os.listdir(directory):
            if name.startswith(prefix) and name.endswith(ext):
                names.add(name[len(prefix):-len(ext)] if ext else name[len(prefix):])
    return sorted(names)


def log_vcs_event(root: str, action: str, branch_name: str, details: dict[str, Any]) -> str:
    audit_dir = os.path.join(root, "生产数据")
    os.makedirs(audit_dir, exist_ok=True)
    audit_file = os.path.join(audit_dir, "vcs_audit.jsonl")
    event = {
        "schema_version": 1,
        "kind": "novel_story_vcs_audit_event",
        "timestamp": now(),
        "action": action,
        "branch": branch_name,
        "details": details,
    }
    lock_path = audit_file + ".lock"
    with file_lock(lock_path):
        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return audit_file


def atomic_copy_file(src: str, dst: str) -> None:
    """Copy src→dst crash-atomically: temp copy → fsync bytes → atomic replace → fsync dir.

    与 store.atomic_write_text 同档（B2·crash-atomic 非仅 atomic-visibility）：内容文件/备份在断电后
    也保证「要么旧、要么新、绝不半截」，不会出现报告说备份已存在、其字节却没落盘的窗口。
    非 POSIX / 不支持 fsync 目录的平台优雅跳过（退化为 atomic-visibility）。"""
    d = os.path.dirname(dst) or "."
    os.makedirs(d, exist_ok=True)
    tmp = f"{dst}.tmp.{os.getpid()}"
    try:
        shutil.copy2(src, tmp)
        with open(tmp, "rb") as f:
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, dst)
        try:
            dir_fd = os.open(d, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except (OSError, AttributeError):  # pragma: no cover - 非 POSIX 目录 fsync 不可用
            pass
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def load_manifest(root: str, branch_name: str) -> dict[str, Any] | None:
    path = branch_manifest_path(root, branch_name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict) or payload.get("kind") != BRANCH_KIND:
        raise ValueError(f"not a story VCS branch manifest: {path}")
    return payload


def build_legacy_manifest(root: str, branch_name: str) -> dict[str, Any]:
    files = []
    for rel_path in CORE_FILES:
        branch_file = branch_file_for_rel(root, rel_path, branch_name)
        if not os.path.exists(branch_file):
            continue
        files.append({
            "main_path": rel_path,
            "branch_path": rel(root, branch_file),
            "base_sha256": "",
            "branch_sha256": sha256_file(branch_file),
            "legacy_without_base_hash": True,
        })
    return {
        "schema_version": 1,
        "kind": BRANCH_KIND,
        "branch": branch_name,
        "created_at": "",
        "legacy_without_manifest": True,
        "files": files,
    }


def handle_migrate(root: str, branch_name: str, *, trust_current_main: bool = False, overwrite: bool = False) -> dict[str, Any]:
    root = os.path.abspath(root)
    branch_name = safe_name(branch_name)
    manifest_path = branch_manifest_path(root, branch_name)
    existing = load_manifest(root, branch_name)
    if existing and not overwrite:
        return {
            "schema_version": 1,
            "kind": "novel_story_vcs_migration",
            "branch": branch_name,
            "status": "exists",
            "manifest": rel(root, manifest_path),
            "message": "branch manifest already exists; pass --overwrite to rebuild migration manifest",
        }
    legacy = build_legacy_manifest(root, branch_name)
    files = []
    for item in legacy.get("files") or []:
        main_path = os.path.join(root, item["main_path"])
        branch_path = os.path.join(root, item["branch_path"])
        branch_sha = sha256_file(branch_path)
        migrated = dict(item)
        migrated["branch_sha256"] = branch_sha
        if trust_current_main and os.path.exists(main_path):
            migrated["base_sha256"] = sha256_file(main_path)
            migrated["legacy_without_base_hash"] = False
            migrated["migration_assumption"] = "trusted_current_main_as_base"
        else:
            migrated["base_sha256"] = ""
            migrated["legacy_without_base_hash"] = True
            migrated["migration_assumption"] = "base_unknown_requires_accept_legacy_no_base"
        files.append(migrated)
    manifest = {
        "schema_version": 1,
        "kind": BRANCH_KIND,
        "branch": branch_name,
        "created_at": now(),
        "migrated_from_legacy": True,
        "trust_current_main": trust_current_main,
        "files": files,
        "merge_history": [],
    }
    atomic_write_json(manifest_path, manifest)
    audit = log_vcs_event(root, "migrate", branch_name, {
        "manifest": rel(root, manifest_path),
        "file_count": len(files),
        "trust_current_main": trust_current_main,
    })
    if append_event:
        append_event(
            root,
            event_type="story_vcs_branch_migrated",
            tool="novel-craft/scripts/story_vcs.py",
            inputs=[os.path.join(root, item["branch_path"]) for item in files],
            outputs=[manifest_path, audit],
            metadata={"branch": branch_name, "file_count": len(files), "trust_current_main": trust_current_main},
        )
    return {
        "schema_version": 1,
        "kind": "novel_story_vcs_migration",
        "branch": branch_name,
        "status": "migrated",
        "manifest": rel(root, manifest_path),
        "trust_current_main": trust_current_main,
        "file_count": len(files),
        "legacy_without_base_hash_count": sum(1 for item in files if item.get("legacy_without_base_hash")),
        "files": files,
    }


def handle_health(root: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    reports = []
    for name in branch_names(root):
        report = merge_preflight(root, name, force=False, accept_legacy_no_base=False)
        reports.append({
            "branch": name,
            "manifest": report.get("manifest") or "",
            "verdict": report.get("verdict"),
            "blocker_count": len(report.get("blockers") or []),
            "missing_branch_file_count": len(report.get("missing_branch_files") or []),
            "legacy_without_base_hash_count": len(report.get("legacy_without_base_hash") or []),
            "conflict_count": len(report.get("conflicts") or []),
            "blockers": report.get("blockers") or [],
        })
    return {
        "schema_version": 1,
        "kind": "novel_story_vcs_health_report",
        "generated_at": now(),
        "project_root": root,
        "branch_count": len(reports),
        "ready_count": sum(1 for item in reports if item.get("verdict") == "ready"),
        "blocked_count": sum(1 for item in reports if item.get("verdict") == "block"),
        "branches": reports,
    }


def handle_branch(root: str, branch_name: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    branch_name = safe_name(branch_name)
    files = []
    for rel_path in CORE_FILES:
        src = os.path.join(root, rel_path)
        if not os.path.exists(src):
            continue
        dst = branch_file_for_rel(root, rel_path, branch_name)
        atomic_copy_file(src, dst)
        files.append({
            "main_path": rel_path,
            "branch_path": rel(root, dst),
            "base_sha256": sha256_file(src),
            "branch_sha256": sha256_file(dst),
        })
    manifest = {
        "schema_version": 1,
        "kind": BRANCH_KIND,
        "branch": branch_name,
        "created_at": now(),
        "files": files,
        "merge_history": [],
    }
    manifest_path = branch_manifest_path(root, branch_name)
    atomic_write_json(manifest_path, manifest)
    audit = log_vcs_event(root, "branch", branch_name, {"branched_files": len(files), "manifest": rel(root, manifest_path)})
    if append_event:
        append_event(
            root,
            event_type="story_vcs_branch_created",
            tool="novel-craft/scripts/story_vcs.py",
            inputs=[os.path.join(root, item["main_path"]) for item in files],
            outputs=[manifest_path, audit, *[os.path.join(root, item["branch_path"]) for item in files]],
            metadata={"branch": branch_name, "file_count": len(files)},
        )
    return manifest


def handle_checkout(root: str, branch_name: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    branch_name = safe_name(branch_name)
    manifest = load_manifest(root, branch_name) or build_legacy_manifest(root, branch_name)
    audit = log_vcs_event(root, "checkout", branch_name, {"file_count": len(manifest.get("files") or [])})
    if append_event:
        append_event(
            root,
            event_type="story_vcs_checkout_recorded",
            tool="novel-craft/scripts/story_vcs.py",
            inputs=[branch_manifest_path(root, branch_name)] if os.path.exists(branch_manifest_path(root, branch_name)) else [],
            outputs=[audit],
            metadata={"branch": branch_name},
        )
    return {"branch": branch_name, "files": manifest.get("files") or []}


def merge_preflight(
    root: str,
    branch_name: str,
    *,
    force: bool = False,
    accept_legacy_no_base: bool = False,
) -> dict[str, Any]:
    root = os.path.abspath(root)
    branch_name = safe_name(branch_name)
    manifest = load_manifest(root, branch_name) or build_legacy_manifest(root, branch_name)
    files = []
    conflicts = []
    missing = []
    legacy_without_base = []
    for item in manifest.get("files") or []:
        main_rel = item["main_path"]
        branch_rel = item["branch_path"]
        main_path = os.path.join(root, main_rel)
        branch_path = os.path.join(root, branch_rel)
        if not os.path.exists(branch_path):
            missing.append(branch_rel)
            continue
        base_sha = item.get("base_sha256") or ""
        main_sha = sha256_file(main_path) if os.path.exists(main_path) else ""
        branch_sha = sha256_file(branch_path)
        conflict = bool(base_sha and main_sha and main_sha != base_sha)
        legacy = bool(item.get("legacy_without_base_hash") or not base_sha)
        record = {
            "main_path": main_rel,
            "branch_path": branch_rel,
            "base_sha256": base_sha,
            "current_main_sha256": main_sha,
            "branch_sha256": branch_sha,
            "conflict": conflict,
            "legacy_without_base_hash": legacy,
        }
        files.append(record)
        if conflict and not force:
            conflicts.append(record)
        if legacy and not accept_legacy_no_base:
            legacy_without_base.append(record)
    blockers = []
    for item in conflicts:
        blockers.append({"type": "base_conflict", "path": item["main_path"], "message": "main changed since branch base"})
    for branch_rel in missing:
        blockers.append({"type": "missing_branch_file", "path": branch_rel, "message": "branch file is missing"})
    for item in legacy_without_base:
        blockers.append({
            "type": "legacy_without_base_hash",
            "path": item["branch_path"],
            "message": "legacy branch has no base hash; rerun branch or pass --accept-legacy-no-base",
        })
    return {
        "schema_version": 1,
        "kind": "novel_story_vcs_merge_preflight",
        "branch": branch_name,
        "generated_at": now(),
        "verdict": "block" if blockers else "ready",
        "force": force,
        "accept_legacy_no_base": accept_legacy_no_base,
        "conflicts": conflicts,
        "missing_branch_files": missing,
        "legacy_without_base_hash": legacy_without_base,
        "blockers": blockers,
        "files": files,
        "manifest": rel(root, branch_manifest_path(root, branch_name)) if os.path.exists(branch_manifest_path(root, branch_name)) else "",
    }


def handle_merge(
    root: str,
    branch_name: str,
    *,
    dry_run: bool = False,
    force: bool = False,
    accept_legacy_no_base: bool = False,
) -> dict[str, Any]:
    root = os.path.abspath(root)
    branch_name = safe_name(branch_name)
    preflight = merge_preflight(root, branch_name, force=force, accept_legacy_no_base=accept_legacy_no_base)
    if dry_run or preflight["verdict"] == "block":
        preflight["dry_run"] = dry_run
        return preflight

    merge_id = f"merge_{branch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir = os.path.join(root, "生产数据", "story_vcs_backups", merge_id)

    # TOCTOU 闭合：preflight 判 ready 后、真正覆盖前，主文件可能被并发改动。覆盖任何文件之前，
    # 先重新核对所有 base_sha256；冲突且非 force 则整体中止，绝不留半合并状态。
    toctou_conflicts = []
    if not force:
        for item in preflight.get("files") or []:
            base_sha = item.get("base_sha256") or ""
            if not base_sha:
                continue  # legacy 无 base：已由 preflight 的 accept_legacy_no_base 决策
            main_path = os.path.join(root, item["main_path"])
            current = sha256_file(main_path) if os.path.exists(main_path) else ""
            if current and current != base_sha:
                toctou_conflicts.append({
                    "main_path": item["main_path"],
                    "base_sha256": base_sha,
                    "current_main_sha256": current,
                })
    if toctou_conflicts:
        log_vcs_event(root, "merge_aborted", branch_name,
                      {"merge_id": merge_id, "reason": "toctou_base_hash_changed",
                       "conflicts": toctou_conflicts})
        return {
            "schema_version": 1, "kind": MERGE_KIND, "merge_id": merge_id,
            "branch": branch_name, "verdict": "block", "status": "aborted_toctou",
            "blockers": [f"{c['main_path']}: 主文件在 preflight 后被改动（base≠current），已中止合并"
                         for c in toctou_conflicts],
            "toctou_conflicts": toctou_conflicts, "force": force,
        }

    # 崩溃原子化：覆盖前先写 in_progress 报告（含每个文件的备份路径 + 是否新建），
    # 这样即便覆盖循环中途崩溃，rollback 也有完整的"备份在哪/哪些是新建/哪些已动过"映射可恢复。
    report_path = merge_report_path(root, merge_id)
    planned = []
    for item in preflight.get("files") or []:
        main_path = os.path.join(root, item["main_path"])
        backup_path = os.path.join(backup_dir, item["main_path"])
        main_existed = os.path.exists(main_path)
        planned.append({
            **item,
            "main_existed_before_merge": main_existed,
            "backup_path": rel(root, backup_path) if main_existed else "",
            "merged_sha256": "",
            "committed": False,
        })
    report = {
        "schema_version": 1,
        "kind": MERGE_KIND,
        "merge_id": merge_id,
        "branch": branch_name,
        "merged_at": now(),
        "status": "in_progress",
        "force": force,
        "accept_legacy_no_base": accept_legacy_no_base,
        "files": planned,
    }
    atomic_write_json(report_path, report)
    log_vcs_event(root, "merge_begin", branch_name,
                  {"merge_id": merge_id, "planned_files": len(planned),
                   "report": rel(root, report_path)})

    # 逐文件：先备份后覆盖，每覆盖一个就把该项标 committed 并刷新报告——
    # 保证任何崩溃点 rollback 都能据报告精确还原"已动过的文件"、跳过"未动的文件"。
    merged = []
    for entry in planned:
        main_path = os.path.join(root, entry["main_path"])
        branch_path = os.path.join(root, entry["branch_path"])
        if entry["main_existed_before_merge"]:
            atomic_copy_file(main_path, os.path.join(root, entry["backup_path"]))
        atomic_copy_file(branch_path, main_path)
        entry["merged_sha256"] = sha256_file(main_path)
        entry["committed"] = True
        merged.append(entry)
        atomic_write_json(report_path, report)  # report["files"] 即 planned，原地刷新进度

    report["status"] = "committed"
    report["merged_at"] = now()
    atomic_write_json(report_path, report)

    manifest = load_manifest(root, branch_name)
    if manifest:
        manifest.setdefault("merge_history", []).append({
            "merge_id": merge_id,
            "merged_at": report["merged_at"],
            "force": force,
            "accept_legacy_no_base": accept_legacy_no_base,
        })
        manifest["last_merge"] = {
            "merge_id": merge_id,
            "merged_at": report["merged_at"],
            "force": force,
            "accept_legacy_no_base": accept_legacy_no_base,
        }
        atomic_write_json(branch_manifest_path(root, branch_name), manifest)

    audit = log_vcs_event(root, "merge", branch_name, {
        "merge_id": merge_id,
        "merged_files": len(merged),
        "force": force,
        "accept_legacy_no_base": accept_legacy_no_base,
        "report": rel(root, report_path),
    })
    if append_event:
        append_event(
            root,
            event_type="story_vcs_branch_merged",
            tool="novel-craft/scripts/story_vcs.py",
            inputs=[os.path.join(root, item["branch_path"]) for item in merged],
            outputs=[report_path, audit, *[os.path.join(root, item["main_path"]) for item in merged]],
            metadata={"branch": branch_name, "merge_id": merge_id, "force": force},
        )
    return report


def handle_rollback(root: str, merge_id: str) -> dict[str, Any]:
    root = os.path.abspath(root)
    merge_id = safe_name(merge_id)
    path = merge_report_path(root, merge_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"merge report not found: {path}")
    with open(path, encoding="utf-8") as f:
        report = json.load(f)
    restored = []
    for item in report.get("files") or []:
        main_path = os.path.join(root, item["main_path"])
        backup_rel = item.get("backup_path") or ""
        # 旧报告无 committed 字段：视为已提交（旧版总是整体提交）。in_progress 报告里 committed=False
        # 的文件表示崩溃前未覆盖到 → 主文件仍是原件，跳过即可，绝不误删/误报缺备份。
        committed = item.get("committed", True)
        if item.get("main_existed_before_merge") and backup_rel:
            backup_path = os.path.join(root, backup_rel)
            if os.path.exists(backup_path):
                atomic_copy_file(backup_path, main_path)
                restored.append({"main_path": item["main_path"], "restored_from": backup_rel})
            elif not committed:
                restored.append({"main_path": item["main_path"], "skipped": "未覆盖（崩溃前未动），主文件保持原件"})
            else:
                raise FileNotFoundError(f"rollback backup missing: {backup_rel}")
        elif not item.get("main_existed_before_merge") and committed and os.path.exists(main_path):
            os.remove(main_path)
            restored.append({"main_path": item["main_path"], "removed": True})
        else:
            restored.append({"main_path": item["main_path"], "skipped": "无需还原"})
    rollback = {
        "schema_version": 1,
        "kind": "novel_story_vcs_rollback",
        "merge_id": merge_id,
        "branch": report.get("branch") or "",
        "rolled_back_at": now(),
        "files": restored,
    }
    rollback_path = os.path.join(root, "生产数据", "story_vcs_merges", f"{merge_id}_rollback.json")
    atomic_write_json(rollback_path, rollback)
    audit = log_vcs_event(root, "rollback", str(report.get("branch") or ""), {"merge_id": merge_id, "restored_files": len(restored)})
    if append_event:
        append_event(
            root,
            event_type="story_vcs_merge_rolled_back",
            tool="novel-craft/scripts/story_vcs.py",
            inputs=[path],
            outputs=[rollback_path, audit, *[os.path.join(root, item["main_path"]) for item in restored]],
            metadata={"merge_id": merge_id, "branch": report.get("branch") or ""},
        )
    return rollback


def print_payload(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    kind = payload.get("kind")
    if kind == BRANCH_KIND:
        print(f"[ok] branch {payload.get('branch')} files={len(payload.get('files') or [])}")
    elif kind == "novel_story_vcs_merge_preflight":
        print(f"[{payload.get('verdict')}] merge preflight branch={payload.get('branch')}")
        for item in payload.get("blockers") or []:
            print(f"- block {item.get('type')} {item.get('path')}: {item.get('message')}")
        for item in payload.get("conflicts") or []:
            print(f"- conflict {item.get('main_path')}: base={item.get('base_sha256')} current={item.get('current_main_sha256')}")
    elif kind == MERGE_KIND:
        print(f"[ok] merged {payload.get('branch')} merge_id={payload.get('merge_id')} files={len(payload.get('files') or [])}")
    elif kind == "novel_story_vcs_rollback":
        print(f"[ok] rolled back {payload.get('merge_id')} files={len(payload.get('files') or [])}")
    elif kind == "novel_story_vcs_migration":
        print(f"[{payload.get('status')}] migrated branch={payload.get('branch')} files={payload.get('file_count', 0)} manifest={payload.get('manifest')}")
        if payload.get("legacy_without_base_hash_count"):
            print(f"- legacy_without_base_hash: {payload.get('legacy_without_base_hash_count')} (merge still requires --accept-legacy-no-base)")
    elif kind == "novel_story_vcs_health_report":
        print(f"[health] branches={payload.get('branch_count', 0)} ready={payload.get('ready_count', 0)} blocked={payload.get('blocked_count', 0)}")
        for item in payload.get("branches") or []:
            print(f"- {item.get('branch')}: {item.get('verdict')} blockers={item.get('blocker_count', 0)} manifest={item.get('manifest') or 'legacy'}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VCS-free story branch helper")
    parser.add_argument("cmd", choices=["branch", "checkout", "merge", "rollback", "migrate", "health"])
    parser.add_argument("root", help="项目根目录")
    parser.add_argument("name", nargs="?", default="", help="分支名或 merge_id；health 可省略")
    parser.add_argument("--dry-run", action="store_true", help="merge preflight only")
    parser.add_argument("--force", action="store_true", help="merge despite base hash conflict")
    parser.add_argument("--overwrite", action="store_true", help="migrate: overwrite an existing branch manifest")
    parser.add_argument("--trust-current-main", action="store_true", help="migrate: treat current main files as trusted branch base hashes")
    parser.add_argument(
        "--accept-legacy-no-base",
        action="store_true",
        help="allow legacy branch files that lack base hashes; still blocks missing files",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    try:
        if args.cmd == "branch":
            if not args.name:
                raise ValueError("branch name is required")
            payload = handle_branch(root, args.name)
        elif args.cmd == "checkout":
            if not args.name:
                raise ValueError("branch name is required")
            payload = handle_checkout(root, args.name)
        elif args.cmd == "merge":
            if not args.name:
                raise ValueError("branch name is required")
            payload = handle_merge(
                root,
                args.name,
                dry_run=args.dry_run,
                force=args.force,
                accept_legacy_no_base=args.accept_legacy_no_base,
            )
            if payload.get("kind") == "novel_story_vcs_merge_preflight" and payload.get("verdict") == "block":
                print_payload(payload, args.json)
                return 1
        elif args.cmd == "migrate":
            if not args.name:
                raise ValueError("branch name is required")
            payload = handle_migrate(root, args.name, trust_current_main=args.trust_current_main, overwrite=args.overwrite)
        elif args.cmd == "health":
            payload = handle_health(root)
        else:
            if not args.name:
                raise ValueError("merge_id is required")
            payload = handle_rollback(root, args.name)
    except Exception as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 1
    print_payload(payload, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
