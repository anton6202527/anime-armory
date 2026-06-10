#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claim/mark queue for batch novel chapter drafting."""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

from store import atomic_write_json, file_lock


QUEUE_REL = os.path.join("写作任务", "draft_queue.json")
LOCK_REL = os.path.join("写作任务", "draft_queue.lock")


def now():
    return datetime.now().replace(microsecond=0)


def stamp(dt=None):
    return (dt or now()).isoformat()


def queue_path(root):
    return os.path.join(root, QUEUE_REL)


def lock_path(root):
    return os.path.join(root, LOCK_REL)


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_meta(root):
    return load_json(os.path.join(root, "_meta.json"), {}) or {}


def existing_chapters(root):
    chdir = os.path.join(root, "章节")
    if not os.path.isdir(chdir):
        return set()
    nums = set()
    for name in os.listdir(chdir):
        m = re.search(r"第0*(\d+)章", name)
        if m and name.endswith(".md"):
            nums.add(int(m.group(1)))
    return nums


def chapter_key(chapter):
    return f"{int(chapter):02d}"


def new_queue(root, *, start=None, end=None):
    meta = load_meta(root)
    target = int(end or meta.get("target_chapters") or 0)
    if target <= 0:
        raise RuntimeError("缺少 _meta.target_chapters；请用 --end 指定队列终章。")
    first = int(start or (int(meta.get("demo_chapters") or 0) + 1) or 1)
    done = existing_chapters(root)
    chapters = {}
    for chapter in range(first, target + 1):
        status = "done" if chapter in done else "todo"
        chapters[chapter_key(chapter)] = {
            "chapter": chapter,
            "status": status,
            "created_at": stamp(),
        }
    return {
        "schema_version": 1,
        "kind": "novel_draft_queue",
        "project_root": os.path.abspath(root),
        "updated_at": stamp(),
        "chapters": chapters,
    }


def load_queue(root):
    return load_json(queue_path(root))


def save_queue(root, queue):
    queue["updated_at"] = stamp()
    atomic_write_json(queue_path(root), queue)


def ensure_queue(root, *, start=None, end=None):
    queue = load_queue(root)
    if queue:
        return queue
    queue = new_queue(root, start=start, end=end)
    save_queue(root, queue)
    return queue


def parse_stamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def expired(item, ref=None):
    if item.get("status") != "claimed":
        return False
    expires = parse_stamp(item.get("lease_expires_at"))
    return bool(expires and expires < (ref or now()))


def init_queue(root, *, start=None, end=None, force=False):
    with file_lock(lock_path(root)):
        if load_queue(root) and not force:
            raise RuntimeError("draft_queue.json 已存在；如需重建请加 --force。")
        queue = new_queue(root, start=start, end=end)
        save_queue(root, queue)
        return queue


def claim_chapter(root, *, agent, ttl_minutes=120, chapter=None):
    with file_lock(lock_path(root)):
        queue = ensure_queue(root)
        selected = None
        keys = [chapter_key(chapter)] if chapter else sorted(queue.get("chapters") or {})
        for key in keys:
            item = (queue.get("chapters") or {}).get(key)
            if not item:
                continue
            if item.get("status") == "todo" or expired(item):
                selected = item
                break
        if not selected:
            raise RuntimeError("没有可认领章节。")
        selected["status"] = "claimed"
        selected["claimed_by"] = agent
        selected["claimed_at"] = stamp()
        selected["lease_expires_at"] = stamp(now() + timedelta(minutes=int(ttl_minutes)))
        selected.pop("failed_reason", None)
        save_queue(root, queue)
        return selected


def mark_chapter(root, chapter, status, *, agent=None, reason=None):
    if status not in {"done", "failed", "todo"}:
        raise ValueError("status must be done, failed, or todo")
    with file_lock(lock_path(root)):
        queue = ensure_queue(root)
        key = chapter_key(chapter)
        item = (queue.get("chapters") or {}).get(key)
        if not item:
            raise RuntimeError(f"队列中没有第 {int(chapter):02d} 章。")
        item["status"] = status
        item["updated_by"] = agent or ""
        item["updated_at"] = stamp()
        if status == "done":
            item["done_at"] = stamp()
            item.pop("failed_reason", None)
        elif status == "failed":
            item["failed_reason"] = reason or ""
        else:
            for field in ("claimed_by", "claimed_at", "lease_expires_at", "done_at", "failed_reason"):
                item.pop(field, None)
        save_queue(root, queue)
        return item


def queue_summary(queue):
    counts = {}
    for item in (queue.get("chapters") or {}).values():
        status = "todo" if expired(item) else item.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def print_result(payload, as_json=False):
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload)


def main():
    ap = argparse.ArgumentParser(description="novel 批量写章队列：init/claim/done/fail/status")
    ap.add_argument("project_root")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--start", type=int)
    p_init.add_argument("--end", type=int)
    p_init.add_argument("--force", action="store_true")

    p_claim = sub.add_parser("claim")
    p_claim.add_argument("--agent", default=os.environ.get("USER") or "agent")
    p_claim.add_argument("--ttl-minutes", type=int, default=120)
    p_claim.add_argument("--chapter", type=int)

    for name in ("done", "todo"):
        p = sub.add_parser(name)
        p.add_argument("chapter", type=int)
        p.add_argument("--agent", default=os.environ.get("USER") or "agent")

    p_fail = sub.add_parser("fail")
    p_fail.add_argument("chapter", type=int)
    p_fail.add_argument("--agent", default=os.environ.get("USER") or "agent")
    p_fail.add_argument("--reason", default="")

    sub.add_parser("status")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    try:
        if args.cmd == "init":
            queue = init_queue(root, start=args.start, end=args.end, force=args.force)
            payload = {"ok": True, "queue": queue_path(root), "summary": queue_summary(queue)}
        elif args.cmd == "claim":
            item = claim_chapter(root, agent=args.agent, ttl_minutes=args.ttl_minutes, chapter=args.chapter)
            payload = {"ok": True, "claimed": item}
        elif args.cmd == "done":
            item = mark_chapter(root, args.chapter, "done", agent=args.agent)
            payload = {"ok": True, "chapter": item}
        elif args.cmd == "todo":
            item = mark_chapter(root, args.chapter, "todo", agent=args.agent)
            payload = {"ok": True, "chapter": item}
        elif args.cmd == "fail":
            item = mark_chapter(root, args.chapter, "failed", agent=args.agent, reason=args.reason)
            payload = {"ok": True, "chapter": item}
        else:
            with file_lock(lock_path(root)):
                queue = ensure_queue(root)
            payload = {"ok": True, "queue": queue_path(root), "summary": queue_summary(queue)}
    except Exception as exc:
        print(f"[err] {exc}", file=sys.stderr)
        sys.exit(2)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.cmd == "claim":
        print(f"[ok] claimed chapter {payload['claimed']['chapter']:02d} by {payload['claimed'].get('claimed_by')}")
    else:
        print(f"[ok] {payload['summary'] if 'summary' in payload else payload['chapter']}")


if __name__ == "__main__":
    main()
