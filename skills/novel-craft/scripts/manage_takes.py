#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Manage multi-take versioning for novel chapters.

Allows registering, scoring, and selecting between multiple AI-generated
versions of the same chapter.
"""
import argparse
import json
import os
import re
import shutil
import sys
from datetime import date


def rel(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def normalize_take_id(value):
    if value is None:
        return None
    text = str(value).strip()
    m = re.fullmatch(r"(?:take_?)?(\d+)", text, flags=re.I)
    if m:
        return f"take_{int(m.group(1)):02d}"
    if re.fullmatch(r"take_\d{2,}", text, flags=re.I):
        return text.lower()
    return f"take_{text.zfill(2)}"


def get_manifest_path(root, chapter):
    return os.path.join(root, "章节", "takes", f"第{chapter:02d}章", "takes_manifest.json")


def ensure_manifest(root, chapter):
    path = get_manifest_path(root, chapter)
    if os.path.exists(path):
        return path, load_json(path, {})
    
    manifest = {
        "schema_version": 1,
        "kind": "novel_take_manifest",
        "chapter": chapter,
        "generated_at": date.today().isoformat(),
        "project_root": rel(root, root),
        "selected_take": None,
        "takes": []
    }
    write_json(path, manifest)
    return path, manifest


def register_take(root, chapter, src_file, take_id, note=""):
    if not os.path.exists(src_file):
        raise SystemExit(f"[err] 找不到源文件：{src_file}")
    
    path, manifest = ensure_manifest(root, chapter)
    take_id = normalize_take_id(take_id)
    
    take_dir = os.path.join(root, "章节", "takes", f"第{chapter:02d}章")
    dst_file = os.path.join(take_dir, f"{take_id}.md")
    os.makedirs(take_dir, exist_ok=True)
    shutil.copy(src_file, dst_file)
    
    # Update manifest
    existing = next((t for t in manifest["takes"] if t["take_id"] == take_id), None)
    if existing:
        existing["registered_at"] = date.today().isoformat()
        existing["note"] = note or existing.get("note", "")
        existing["status"] = "registered"
    else:
        manifest["takes"].append({
            "take_id": take_id,
            "status": "registered",
            "file_path": rel(root, dst_file),
            "note": note,
            "registered_at": date.today().isoformat(),
            "score": None,
            "verdict": None
        })
    
    write_json(path, manifest)
    return dst_file


def select_take(root, chapter, take_id):
    path, manifest = ensure_manifest(root, chapter)
    take_id = normalize_take_id(take_id)
    
    take = next((t for t in manifest["takes"] if t["take_id"] == take_id), None)
    if not take:
        raise SystemExit(f"[err] {take_id} 尚未登记")
    
    src = os.path.join(root, take["file_path"])
    dst = os.path.join(root, "章节", f"第{chapter:02d}章.md")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy(src, dst)
    
    # Update status
    for t in manifest["takes"]:
        if t["take_id"] == take_id:
            t["status"] = "selected"
        elif t["status"] == "selected":
            t["status"] = "registered"
            
    manifest["selected_take"] = take_id
    manifest["selected_at"] = date.today().isoformat()
    write_json(path, manifest)
    return dst


def list_takes(root, chapter):
    path, manifest = ensure_manifest(root, chapter)
    print(f"# Chapter {chapter:02d} Takes")
    print(f"Manifest: {rel(root, path)}")
    print(f"Selected: {manifest.get('selected_take') or 'None'}")
    print("-" * 40)
    for t in manifest["takes"]:
        score_s = f"Score: {t.get('score')}" if t.get('score') else ""
        verdict_s = f"Verdict: {t.get('verdict')}" if t.get('verdict') else ""
        print(f"[{t['status']}] {t['take_id']} | {t['registered_at']} | {score_s} {verdict_s}")
        if t.get("note"):
            print(f"  Note: {t['note']}")


def main():
    ap = argparse.ArgumentParser(description="管理小说章节的多版挑版（Takes）")
    ap.add_argument("project_root")
    ap.add_argument("--chapter", type=int, required=True, help="章节号")
    ap.add_argument("--register", help="登记一个新生成的版本（文件路径）")
    ap.add_argument("--take", help="版本 ID（如 1 或 take_01）")
    ap.add_argument("--note", default="", help="备注")
    ap.add_argument("--select", help="选定一个版本作为正式章节（提供 take ID）")
    ap.add_argument("--list", action="store_true", help="列出当前章节的所有版本")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    if args.register:
        take_id = args.take or "1"
        dst = register_take(root, args.chapter, args.register, take_id, args.note)
        print(f"[ok] 章节 {args.chapter} 版本 {take_id} 登记完成 → {dst}")
    
    if args.select:
        dst = select_take(root, args.chapter, args.select)
        print(f"[ok] 章节 {args.chapter} 已选定版本 {args.select} → {dst}")

    if args.list:
        list_takes(root, args.chapter)


if __name__ == "__main__":
    main()
