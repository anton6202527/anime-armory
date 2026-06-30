#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan and optionally mark ad delivery outputs from `_进度.md`.

`compose.sh` builds the master. This helper closes the delivery bookkeeping
loop: read the deliverable matrix, emit deterministic commands/expected paths,
and mark rows complete when files already exist.
"""
import argparse
import json
import os
import re
import sys

_CRAFT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ad-craft", "scripts"))
if _CRAFT not in sys.path:
    sys.path.insert(0, _CRAFT)
import contract  # noqa: E402
import progress_set  # noqa: E402


FIELDS = ("label", "duration", "aspect", "kind", "spec", "status", "path")


def _split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells):
    return bool(cells) and all(set(c) <= set("-: ") for c in cells)


def parse_deliverables(text):
    rows = []
    in_matrix = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_matrix = "交付版本矩阵" in s
            continue
        if not in_matrix or not s.startswith("|"):
            continue
        cells = _split_row(s)
        if len(cells) < 7 or cells[0] in ("交付件", "") or _is_separator(cells):
            continue
        rows.append(dict(zip(FIELDS, cells[:7])))
    return rows


def _safe_name(text):
    text = text.replace(":", "x")
    return re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", text).strip("_") or "variant"


def expected_relpath(row):
    kind = row["kind"]
    if kind == "master":
        return "合成/成片_主片.mp4"
    if kind == "cutdown":
        return f"合成/cutdown/成片_{_safe_name(row['duration'])}.mp4"
    if kind == "reframe":
        return f"合成/多比例/成片_{_safe_name(row['aspect'])}.mp4"
    return f"合成/ab/{_safe_name(row['label'])}.mp4"


def deliverable_id(row):
    if row["kind"] == "master":
        return "master"
    if row["kind"] == "cutdown":
        return "cut_" + row["duration"].lower()
    return row["label"]


def planned_command(row, root):
    quoted = json.dumps(root, ensure_ascii=False)
    out = expected_relpath(row)
    if row["kind"] == "master":
        return f"bash skills/ad-compose/compose.sh {quoted} {row['aspect']}"
    if row["kind"] == "cutdown":
        plan = os.path.join(root, "合成", "cutdown", f"plan_{_safe_name(row['duration'])}.json")
        outp = os.path.join(root, out)
        # --render 实际拼接产出 MP4（需 ffmpeg）；--json 同时落计划
        return (f"python3 skills/ad-compose/cutdown.py {quoted} --target {row['duration']} "
                f"--aspect {row['aspect']} --render "
                f"--out {json.dumps(outp, ensure_ascii=False)} "
                f"--json {json.dumps(plan, ensure_ascii=False)}")
    if row["kind"] == "reframe":
        src = os.path.join(root, "合成", "成片_主片.mp4")
        outp = os.path.join(root, out)
        # reframe --render 实际跑 ffmpeg crop/pad 输出 MP4（主体偏置时补 --crop-x/--crop-y）
        return (f"python3 skills/ad-compose/reframe.py --src 1920x1080 --target {row['aspect']} "
                f"--in {json.dumps(src, ensure_ascii=False)} --render "
                f"--out {json.dumps(outp, ensure_ascii=False)}")
    return f"# A/B 版本需操作者手工生成 → {out}"


def build_plan(root, progress_text):
    root = os.path.abspath(root)
    rows = parse_deliverables(progress_text)
    items = []
    for row in rows:
        rel = expected_relpath(row)
        abs_path = os.path.join(root, rel)
        profile = contract.delivery_profile(row["spec"] if row["spec"] in contract.DELIVERY_PROFILE else "平台默认")
        items.append({
            "deliverable_id": deliverable_id(row),
            "label": row["label"],
            "kind": row["kind"],
            "duration": row["duration"],
            "aspect": row["aspect"],
            "spec": row["spec"],
            "expected_path": rel,
            "exists": os.path.isfile(abs_path),
            "command": planned_command(row, root),
            "loudness_lufs": profile["loudness_lufs"],
        })
    return {"schema_version": 1, "kind": "ad_delivery_plan", "project_root": root, "deliverables": items}


def mark_existing(root, progress_text, plan):
    out = progress_text
    for item in plan["deliverables"]:
        if not item["exists"]:
            continue
        out = progress_set.set_deliverable_text(
            out,
            item["deliverable_id"],
            "✅",
            item["expected_path"],
            item["spec"],
            f"交付件完成：{item['label']}",
        )
    return out


def main():
    ap = argparse.ArgumentParser(description="拍广告交付矩阵计划/回写")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None, help="输出 delivery_plan.json；默认 合成/delivery_plan.json")
    ap.add_argument("--mark-existing", action="store_true", help="发现输出文件存在时回写 _进度.md 对应交付件 ✅")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    progress_path = os.path.join(root, "_进度.md")
    if not os.path.isfile(progress_path):
        print(f"[err] 缺 _进度.md：{progress_path}", file=sys.stderr)
        sys.exit(2)
    with open(progress_path, encoding="utf-8") as f:
        progress_text = f.read()
    plan = build_plan(root, progress_text)
    if args.mark_existing:
        with open(progress_path, "w", encoding="utf-8") as f:
            f.write(mark_existing(root, progress_text, plan))
    json_path = args.json or os.path.join(root, "合成", "delivery_plan.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(f"# ad delivery plan  rows={len(plan['deliverables'])}")
    for item in plan["deliverables"]:
        flag = "✅" if item["exists"] else "⬜"
        print(f"{flag} {item['label']} -> {item['expected_path']}")
    print(f"[ok] {json_path}")


if __name__ == "__main__":
    main()
