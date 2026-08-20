#!/usr/bin/env python3
"""Apply a named, auditable patch to an MV beat/downbeat/section grid."""
import argparse
import importlib.util
import json
import os
import sys
from datetime import date


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
UTILS = os.path.join(REPO, "skills", "mv", "mv-craft", "scripts", "mv_utils.py")
SPEC = importlib.util.spec_from_file_location("mv_utils", UTILS)
mv_utils = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mv_utils)


def _time(value, duration):
    result = round(float(value), 3)
    if result < 0 or result > duration:
        raise ValueError(f"时间 {result} 超出 0..{duration}")
    return result


def _edit_points(values, operation, duration):
    rows = [float(value) for value in values]
    op = operation.get("op")
    if op == "add":
        rows.append(_time(operation.get("time"), duration))
    elif op == "move":
        index = int(operation.get("index"))
        if not 0 <= index < len(rows):
            raise ValueError(f"move index 越界：{index}")
        rows[index] = _time(operation.get("time"), duration)
    elif op == "delete":
        index = int(operation.get("index"))
        if not 0 <= index < len(rows):
            raise ValueError(f"delete index 越界：{index}")
        rows.pop(index)
    else:
        raise ValueError(f"不支持的点操作：{op}")
    rows = sorted(set(round(value, 3) for value in rows))
    if any(right <= left for left, right in zip(rows, rows[1:])):
        raise ValueError("编辑后时间点必须严格递增")
    return rows


def _sections(rows, duration):
    normalized = []
    for index, row in enumerate(rows or []):
        if not isinstance(row, dict):
            raise ValueError(f"sections[{index}] 必须是对象")
        start, end = _time(row.get("start"), duration), _time(row.get("end"), duration)
        if end <= start:
            raise ValueError(f"sections[{index}] end 必须大于 start")
        normalized.append({"section": str(row.get("section") or row.get("name") or f"section{index + 1}"),
                           "start": start, "end": end, "source": "manual_patch"})
    normalized.sort(key=lambda row: row["start"])
    if normalized:
        if abs(normalized[0]["start"]) > 0.15 or abs(normalized[-1]["end"] - duration) > 0.15:
            raise ValueError("sections 必须从 0 连续覆盖到歌尾（容差 150ms）")
        for left, right in zip(normalized, normalized[1:]):
            if abs(left["end"] - right["start"]) > 0.15:
                raise ValueError("sections 存在空洞或重叠")
    return normalized


def apply_patch(grid, patch):
    result = json.loads(json.dumps(grid, ensure_ascii=False))
    duration = float(result.get("duration") or 0)
    if duration <= 0:
        raise ValueError("beatgrid.duration 无效")
    operations = patch.get("operations") if isinstance(patch, dict) else None
    if not isinstance(operations, list) or not operations:
        raise ValueError("patch 必须含非空 operations[]")
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("operations[] 必须是对象")
        target = operation.get("target")
        if target in {"beats", "downbeats"}:
            result[target] = _edit_points(result.get(target) or [], operation, duration)
        elif target == "sections" and operation.get("op") == "replace":
            result["sections"] = _sections(operation.get("sections"), duration)
            result["section_source"] = "manual_patch"
            result["sections_complete"] = bool(result["sections"])
        else:
            raise ValueError(f"不支持的 target/op：{target}/{operation.get('op')}")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root")
    parser.add_argument("--patch", required=True, help="JSON patch 文件")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", required=True)
    parser.add_argument("--accept-grid", action="store_true", help="听审完整网格后重新签收 timing truth")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    grid_path = os.path.join(root, "节拍", "beatgrid.json")
    grid = mv_utils.load_json(grid_path, None)
    patch = mv_utils.load_json(args.patch, None)
    if not isinstance(grid, dict) or not isinstance(patch, dict):
        parser.error("缺 beatgrid.json 或 patch JSON 损坏")
    try:
        before = mv_utils.content_hash(grid_path)
        result = apply_patch(grid, patch)
    except (TypeError, ValueError) as exc:
        parser.error(str(exc))
    entry = {
        "date": date.today().isoformat(),
        "reviewer": args.reviewer.strip(),
        "notes": args.notes.strip(),
        "patch": {"original_name": os.path.basename(args.patch), "sha256": mv_utils.content_hash(args.patch)},
        "before_sha256": before,
        "operations": patch["operations"],
    }
    if not entry["reviewer"] or not entry["notes"]:
        parser.error("reviewer/notes 不能为空")
    result.setdefault("edit_ledger", []).append(entry)
    if args.accept_grid:
        complete = bool(result.get("beats") and result.get("downbeats") and result.get("sections_complete"))
        if not complete:
            parser.error("网格仍不完整，不能 --accept-grid")
        result["downbeats_verified"] = True
        result["sections_verified"] = True
        result["timing_verified"] = True
        result["timing_review"] = {
            "accepted": True, "reviewer": entry["reviewer"], "date": entry["date"],
            "notes": entry["notes"], "source": "manual_patch_ledger",
        }
    else:
        result["timing_verified"] = False
        result["timing_review"] = {"accepted": False, "reviewer": entry["reviewer"],
                                   "date": entry["date"], "notes": "edited; full grid requires re-acceptance"}
    mv_utils.write_json(grid_path, result)
    print(f"[ok] beatgrid patch → {grid_path}；timing_verified={result.get('timing_verified')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
