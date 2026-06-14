#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update 拍广告 `_进度.md` stage rows and deliverable matrix rows.

The parser is deliberately narrow: it only edits the two generated markdown
tables and appends a maintenance note. This keeps manual notes outside those
tables intact while giving stage skills one deterministic status writer.
"""
import argparse
import os
import sys
from datetime import date

import contract


STATUS_CHOICES = ("✅", "⬜", "⏳rough", "🔴block")


def _split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _row(cells):
    return "| " + " | ".join(cells) + " |"


def _is_separator(cells):
    return bool(cells) and all(set(c) <= set("-: ") for c in cells)


def stage_label(stage):
    by_key = {s["key"]: s["label"] for s in contract.stage_table()}
    by_label = {s["label"]: s["label"] for s in contract.stage_table()}
    if stage in by_key:
        return by_key[stage]
    if stage in by_label:
        return by_label[stage]
    raise KeyError(f"unknown ad stage: {stage}")


def deliverable_match(cells, target):
    """Match generated matrix rows by label/id/duration aliases."""
    label = cells[0] if len(cells) > 0 else ""
    duration = cells[1] if len(cells) > 1 else ""
    kind = cells[3] if len(cells) > 3 else ""
    t = target.strip().lower()
    if t == label.strip().lower():
        return True
    if t == "master" and (kind == "master" or "主片" in label):
        return True
    if t.startswith("cut_") and kind == "cutdown":
        return t[4:] == duration.lower()
    if t in (duration.lower(), f"cut_{duration.lower()}") and kind == "cutdown":
        return True
    if t.replace("x", ":") == duration.replace("x", ":").lower() and kind == "reframe":
        return True
    return False


def append_note(lines, note):
    if not note:
        return lines
    stamp = date.today().isoformat()
    entry = f"- {stamp} {note}"
    for i, line in enumerate(lines):
        if line.strip() == "## 维护记录":
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            lines.insert(j, entry)
            return lines
    lines.extend(["", "## 维护记录", entry])
    return lines


def get_stage_status(text, stage):
    """读「阶段进度」表里某阶段的当前状态；找不到返回 None。"""
    label = stage_label(stage)
    in_stage = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_stage = "阶段进度" in s
            continue
        if not in_stage or not s.startswith("|"):
            continue
        cells = _split_row(s)
        if len(cells) < 4 or _is_separator(cells):
            continue
        if cells[0] == label:
            return cells[1]
    return None


def set_stage_text(text, stage, status, artifact=None, remark=None, note=None):
    label = stage_label(stage)
    lines = text.splitlines()
    in_stage = False
    changed = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("## "):
            in_stage = "阶段进度" in s
            continue
        if not in_stage or not s.startswith("|"):
            continue
        cells = _split_row(s)
        if len(cells) < 4 or cells[0] in ("阶段", "") or _is_separator(cells):
            continue
        if cells[0] == label:
            cells[1] = status
            if artifact is not None:
                cells[2] = artifact
            if remark is not None:
                cells[3] = remark
            lines[i] = _row(cells)
            changed = True
            break
    if not changed:
        raise ValueError(f"stage row not found: {label}")
    append_note(lines, note or f"{label} -> {status}")
    return "\n".join(lines) + "\n"


def set_deliverable_text(text, target, status, path=None, spec=None, note=None):
    lines = text.splitlines()
    in_matrix = False
    changed = False
    for i, line in enumerate(lines):
        s = line.strip()
        if s.startswith("## "):
            in_matrix = "交付版本矩阵" in s
            continue
        if not in_matrix or not s.startswith("|"):
            continue
        cells = _split_row(s)
        if len(cells) < 7 or cells[0] in ("交付件", "") or _is_separator(cells):
            continue
        if deliverable_match(cells, target):
            if spec is not None:
                cells[4] = spec
            cells[5] = status
            if path is not None:
                cells[6] = path
            lines[i] = _row(cells)
            changed = True
            break
    if not changed:
        raise ValueError(f"deliverable row not found: {target}")
    append_note(lines, note or f"交付件 {target} -> {status}")
    return "\n".join(lines) + "\n"


def read_progress(root):
    path = os.path.join(os.path.abspath(root), "_进度.md")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as f:
        return path, f.read()


def write_progress(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description="更新拍广告 _进度.md 阶段/交付矩阵")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("set-stage", help="更新阶段进度行")
    sp.add_argument("project_root")
    sp.add_argument("stage", help="阶段 key 或中文阶段名")
    sp.add_argument("--status", required=True, choices=STATUS_CHOICES)
    sp.add_argument("--artifact", default=None)
    sp.add_argument("--remark", default=None)
    sp.add_argument("--note", default=None)

    dp = sub.add_parser("set-deliverable", help="更新交付版本矩阵行")
    dp.add_argument("project_root")
    dp.add_argument("deliverable", help="master / cut_15s / 15s / 中文交付件名")
    dp.add_argument("--status", required=True, choices=STATUS_CHOICES)
    dp.add_argument("--path", default=None)
    dp.add_argument("--spec", default=None)
    dp.add_argument("--note", default=None)

    args = ap.parse_args()
    path, text = read_progress(args.project_root)
    try:
        if args.cmd == "set-stage":
            out = set_stage_text(text, args.stage, args.status, args.artifact, args.remark, args.note)
        else:
            out = set_deliverable_text(text, args.deliverable, args.status, args.path, args.spec, args.note)
    except (KeyError, ValueError) as exc:
        print(f"[err] {exc}", file=sys.stderr)
        sys.exit(2)
    write_progress(path, out)
    print(f"[ok] updated {path}")


if __name__ == "__main__":
    main()
