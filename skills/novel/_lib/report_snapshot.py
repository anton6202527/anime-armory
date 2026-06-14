#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chapter/text snapshot helpers for review and score report freshness."""
import hashlib
import os
import re


CHAPTER_RE = re.compile(r"第0*(\d+)章")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def chapter_number_from_path(path):
    match = CHAPTER_RE.search(os.path.basename(path))
    return int(match.group(1)) if match else None


def chapter_sort_key(path):
    number = chapter_number_from_path(path)
    return (number is None, number or 0, os.path.basename(path))


def rel_path(root, path):
    return os.path.relpath(os.path.abspath(path), os.path.abspath(root)).replace(os.sep, "/")


def chapter_files(root):
    chdir = os.path.join(root, "章节")
    if not os.path.isdir(chdir):
        return []
    files = []
    for name in os.listdir(chdir):
        if name.endswith(".md") and CHAPTER_RE.search(name):
            files.append(os.path.join(chdir, name))
    return sorted(files, key=chapter_sort_key)


def snapshot_files(root, files, *, mode="custom"):
    root = os.path.abspath(root)
    entries = []
    for path in files:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            continue
        rel = rel_path(root, abs_path)
        entries.append({
            "path": rel,
            "chapter": chapter_number_from_path(abs_path),
            "sha256": sha256_file(abs_path),
            "bytes": os.path.getsize(abs_path),
        })
    entries.sort(key=lambda item: (item["chapter"] is None, item["chapter"] or 0, item["path"]))
    aggregate = hashlib.sha256()
    for item in entries:
        aggregate.update(item["path"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(item["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    return {
        "schema_version": 1,
        "kind": "novel_text_snapshot",
        "mode": mode,
        "files": entries,
        "aggregate_hash": aggregate.hexdigest(),
    }


def snapshot_chapters(root, *, mode="chapters"):
    return snapshot_files(root, chapter_files(root), mode=mode)


def validate_snapshot(root, snapshot):
    if not isinstance(snapshot, dict):
        return False, "报告缺少 source_snapshot；不能证明 review/score 绑定当前正文。"
    if snapshot.get("kind") != "novel_text_snapshot":
        return False, "source_snapshot.kind 不是 novel_text_snapshot。"
    expected_files = snapshot.get("files")
    if not isinstance(expected_files, list):
        return False, "source_snapshot.files 缺失或不是 list。"
    root = os.path.abspath(root)
    mode = snapshot.get("mode") or "custom"
    if str(mode).startswith("review") or mode in {"chapters", "score:full"}:
        current = snapshot_chapters(root, mode=mode)
    else:
        current_paths = [os.path.join(root, item.get("path", "")) for item in expected_files]
        current = snapshot_files(root, current_paths, mode=mode)
    if len(current["files"]) != len(expected_files):
        return False, "source_snapshot 文件集合与当前正文不一致；需重新生成报告。"
    if current["aggregate_hash"] != snapshot.get("aggregate_hash"):
        return False, "source_snapshot 与当前正文 hash 不匹配；需重新 review/score。"
    return True, "source_snapshot fresh"
