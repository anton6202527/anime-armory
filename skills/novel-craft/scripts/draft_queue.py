#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claim/mark queue for batch novel chapter drafting."""
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.join(_SKILLS, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from project_io import list_chapter_files, load_project_settings  # noqa: E402

from store import atomic_write_json, file_lock


QUEUE_REL = os.path.join("写作任务", "draft_queue.json")
LOCK_REL = os.path.join("写作任务", "draft_queue.lock")
TRIO_STEPS = ("architect", "ghostwriter", "editor")


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


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def setting_value(root, key):
    return load_project_settings(root).get(key, "")


def use_trio_pipeline(root, meta):
    mode = setting_value(root, "小说生成模式") or meta.get("draft_mode") or ""
    workflow = setting_value(root, "小说生成工作流") or meta.get("draft_workflow") or meta.get("writing_workflow") or ""
    return mode in {"商业连载", "漫剧源书"} or "三步" in workflow or "trio" in str(workflow).lower()


def existing_chapters(root):
    return {idx for idx, _path in list_chapter_files(root, extensions=(".md",), numbered_only=True)}


def chapter_key(chapter):
    return f"{int(chapter):02d}"


def new_queue(root, *, start=None, end=None):
    meta = load_meta(root)
    workflow = "trio" if use_trio_pipeline(root, meta) else "full"
    target = int(end or meta.get("target_chapters") or 0)
    if target <= 0:
        raise RuntimeError("缺少 _meta.target_chapters；请用 --end 指定队列终章。")
    first = int(start or (int(meta.get("demo_chapters") or 0) + 1) or 1)
    done = existing_chapters(root)
    chapters = {}
    for chapter in range(first, target + 1):
        status = "done" if chapter in done else "todo"
        item = {
            "chapter": chapter,
            "status": status,
            "created_at": stamp(),
        }
        if workflow == "trio":
            item["workflow"] = "trio"
            item["steps"] = {
                step: {"status": status, "created_at": item["created_at"]}
                for step in TRIO_STEPS
            }
        chapters[chapter_key(chapter)] = item
    return {
        "schema_version": 1,
        "kind": "novel_draft_queue",
        "workflow": workflow,
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


def aggregate_step_status(item):
    steps = item.get("steps") or {}
    statuses = [step.get("status", "unknown") for step in steps.values()]
    if statuses and all(status == "done" for status in statuses):
        return "done"
    if any(status == "claimed" for status in statuses):
        return "claimed"
    if any(status == "failed" for status in statuses):
        return "failed"
    return "todo"


def select_step(item, requested=None):
    steps = item.get("steps") or {}
    if not steps:
        return None, item
    keys = [requested] if requested else list(TRIO_STEPS)
    for step in keys:
        if step not in steps:
            continue
        sub = steps[step]
        if sub.get("status") == "todo" or expired(sub):
            return step, sub
    return None, None


def init_queue(root, *, start=None, end=None, force=False):
    with file_lock(lock_path(root)):
        if load_queue(root) and not force:
            raise RuntimeError("draft_queue.json 已存在；如需重建请加 --force。")
        queue = new_queue(root, start=start, end=end)
        save_queue(root, queue)
        return queue


def claim_chapter(root, *, agent, ttl_minutes=120, chapter=None, step=None):
    with file_lock(lock_path(root)):
        queue = ensure_queue(root)
        selected = None
        selected_step = None
        selected_chapter = None
        keys = [chapter_key(chapter)] if chapter else sorted(queue.get("chapters") or {})
        for key in keys:
            item = (queue.get("chapters") or {}).get(key)
            if not item:
                continue
            if item.get("steps"):
                selected_step, selected = select_step(item, step)
                if selected:
                    selected_chapter = item
                    break
            elif item.get("status") == "todo" or expired(item):
                selected = item
                selected_chapter = item
                break
        if not selected:
            raise RuntimeError("没有可认领章节。")
        selected["status"] = "claimed"
        selected["claimed_by"] = agent
        selected["claimed_at"] = stamp()
        selected["lease_expires_at"] = stamp(now() + timedelta(minutes=int(ttl_minutes)))
        selected.pop("failed_reason", None)
        if selected_step and selected_chapter:
            selected_chapter["status"] = aggregate_step_status(selected_chapter)
            selected_chapter["current_step"] = selected_step
            selected_chapter["updated_at"] = stamp()
        save_queue(root, queue)
        if selected_step and selected_chapter:
            payload = dict(selected)
            payload["chapter"] = selected_chapter["chapter"]
            payload["step"] = selected_step
            return payload
        return selected


def mark_chapter(root, chapter, status, *, agent=None, reason=None, step=None):
    if status not in {"done", "failed", "todo"}:
        raise ValueError("status must be done, failed, or todo")
    with file_lock(lock_path(root)):
        queue = ensure_queue(root)
        key = chapter_key(chapter)
        item = (queue.get("chapters") or {}).get(key)
        if not item:
            raise RuntimeError(f"队列中没有第 {int(chapter):02d} 章。")
        target = item
        if step and item.get("steps"):
            if step not in item["steps"]:
                raise RuntimeError(f"第 {int(chapter):02d} 章没有 step={step}。")
            target = item["steps"][step]
        target["status"] = status
        target["updated_by"] = agent or ""
        target["updated_at"] = stamp()
        if status == "done":
            target["done_at"] = stamp()
            target.pop("failed_reason", None)
        elif status == "failed":
            target["failed_reason"] = reason or ""
        else:
            for field in ("claimed_by", "claimed_at", "lease_expires_at", "done_at", "failed_reason"):
                target.pop(field, None)
        if step and item.get("steps"):
            item["status"] = aggregate_step_status(item)
            item["updated_by"] = agent or ""
            item["updated_at"] = stamp()
            if item["status"] == "done":
                item["done_at"] = stamp()
            else:
                item.pop("done_at", None)
        else:
            if item.get("steps"):
                for sub in item["steps"].values():
                    sub["status"] = status
                    sub["updated_by"] = agent or ""
                    sub["updated_at"] = stamp()
                    if status == "done":
                        sub["done_at"] = stamp()
                        sub.pop("failed_reason", None)
                    elif status == "failed":
                        sub["failed_reason"] = reason or ""
                    else:
                        for field in ("claimed_by", "claimed_at", "lease_expires_at", "done_at", "failed_reason"):
                            sub.pop(field, None)
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
        if step and item.get("steps"):
            payload = dict(target)
            payload["chapter"] = item["chapter"]
            payload["step"] = step
            payload["chapter_status"] = item["status"]
            return payload
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
    p_claim.add_argument("--step", choices=TRIO_STEPS)

    for name in ("done", "todo"):
        p = sub.add_parser(name)
        p.add_argument("chapter", type=int)
        p.add_argument("--agent", default=os.environ.get("USER") or "agent")
        p.add_argument("--step", choices=TRIO_STEPS)

    p_fail = sub.add_parser("fail")
    p_fail.add_argument("chapter", type=int)
    p_fail.add_argument("--agent", default=os.environ.get("USER") or "agent")
    p_fail.add_argument("--step", choices=TRIO_STEPS)
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
            item = claim_chapter(root, agent=args.agent, ttl_minutes=args.ttl_minutes, chapter=args.chapter, step=args.step)
            payload = {"ok": True, "claimed": item}
        elif args.cmd == "done":
            item = mark_chapter(root, args.chapter, "done", agent=args.agent, step=args.step)
            payload = {"ok": True, "chapter": item}
        elif args.cmd == "todo":
            item = mark_chapter(root, args.chapter, "todo", agent=args.agent, step=args.step)
            payload = {"ok": True, "chapter": item}
        elif args.cmd == "fail":
            item = mark_chapter(root, args.chapter, "failed", agent=args.agent, reason=args.reason, step=args.step)
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
        suffix = f" {payload['claimed']['step']}" if payload["claimed"].get("step") else ""
        print(f"[ok] claimed chapter {payload['claimed']['chapter']:02d}{suffix} by {payload['claimed'].get('claimed_by')}")
    else:
        print(f"[ok] {payload['summary'] if 'summary' in payload else payload['chapter']}")


if __name__ == "__main__":
    main()
