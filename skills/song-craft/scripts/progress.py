#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read 写歌/<项目>/_进度.md and report the current frontier.

只读，不改文件。写歌线历史进度文件格式比较宽松，本脚本只依赖
`| 阶段 | skill | 状态 |` 表，缺少机器契约字段时也能给出下一步。
"""

import argparse
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    import contract
except Exception:  # pragma: no cover - 进度查询不能因契约导入失败直接不可用
    contract = None


PARTIAL_RE = re.compile(r"(\d+)\s*/\s*(\d+)")
HIGH_RISK_HINTS = {
    "song-compose": "会调用作曲/人声后端或登记外部成品；生成版数、后端与费用先确认。",
    "song-cover": "翻唱/换声涉及真人嗓授权，未授权不得克隆真人歌手嗓。",
    "song-review": "交 MV 或发布前建议跑质检与 AI 音频使用披露。",
}


def progress_path(root):
    return os.path.join(root, "_进度.md")


def read_progress(root):
    path = progress_path(root)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_stage_rows(text):
    rows = []
    in_section = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("## "):
            in_section = "写歌阶段" in s or "阶段" in s
            continue
        if not in_section or not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if cells[0] in ("阶段", "") or set(cells[0]) <= set("-: "):
            continue
        rows.append({"label": cells[0], "owner": cells[1], "status": cells[2]})
    return rows


def state_of(status):
    raw = status.strip()
    if "[x]" in raw.lower() or "✅" in raw:
        return "done"
    match = PARTIAL_RE.search(raw)
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        if total > 0 and current >= total:
            return "done"
        if current > 0:
            return "partial"
    if "[~]" in raw or "⏳" in raw or "rough" in raw.lower():
        return "partial"
    if "[ ]" in raw or "⬜" in raw or not raw:
        return "todo"
    return "partial"


def is_optional(label):
    return "可选" in label or "optional" in label.lower()


def stage_by_owner():
    if contract is None:
        return {}
    result = {}
    for stage in contract.stage_table():
        owner = str(stage.get("owner", ""))
        if owner:
            result.setdefault(owner.split("/")[0], stage)
    return result


def report(root, limit):
    text = read_progress(root)
    rows = parse_stage_rows(text)
    title = os.path.basename(root)
    print(f"# song progress — {title}")
    if not rows:
        print("[warn] _进度.md 未发现可解析的「写歌阶段」表。")
        return 0

    owner_map = stage_by_owner()
    frontier = None
    for row in rows:
        state = state_of(row["status"])
        marker = {"done": "✅", "partial": "⏳", "todo": "⬜"}[state]
        print(f"- {marker} {row['label']}  ·  {row['owner']}  ·  {row['status']}")
        if frontier is None and state != "done":
            if state == "todo" and is_optional(row["label"]):
                continue
            frontier = (row, state)

    print()
    if frontier is None:
        print("[done] 写歌阶段未发现阻断项。下一步：song-review 质检，或交给 mv 制作 MV。")
        return 0

    row, state = frontier
    owner = row["owner"]
    meta = owner_map.get(owner) or owner_map.get(owner.split("/")[0]) or {}
    gate = meta.get("gate", "")
    hint = HIGH_RISK_HINTS.get(owner.split("/")[0], "")
    print(f"[前沿] 下一步：**{row['label']}** → 跑 `{owner}`")
    if gate:
        print(f"  gate: {gate}")
    if hint:
        print(f"  ⚠️ {hint}")

    later = [r for r in rows[rows.index(row) + 1:] if state_of(r["status"]) != "done"]
    if later:
        print("\n后续待办：")
        for item in later[:limit]:
            if is_optional(item["label"]):
                suffix = "（可选）"
            else:
                suffix = ""
            print(f"- {item['label']} → {item['owner']} {suffix}")
        if len(later) > limit:
            print(f"- ... 另有 {len(later) - limit} 项")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="读取写歌项目 _进度.md，报告下一步（只读）")
    ap.add_argument("project_root")
    ap.add_argument("--limit", type=int, default=5)
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    try:
        return report(root, args.limit)
    except FileNotFoundError as exc:
        print(f"[err] 找不到进度文件：{exc.filename}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
