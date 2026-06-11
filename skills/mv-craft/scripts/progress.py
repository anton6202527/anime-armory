#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read 制MV/<项目>/_进度.md and report the current frontier.

只读，不改文件。MV 线不按集拆分，进度以阶段表为主；本脚本兼容历史
`| 阶段 | skill | 状态 |` 表，并用 mv-craft 契约补充 gate 提示。
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
    "mv-image": "会真出图并消耗额度；进入组图前先确认生图AI、参考图/主体库/LoRA一致性增强。",
    "mv-video": "会真出视频并消耗额度；开跑前确认出视频规格、后端与生成粒度。",
    "mv-compose": "合成会覆盖/产出成片文件；先确认画幅、字幕与 AI 视觉披露。",
    "shared-video-faceswap": "换脸仅限本人/已授权/合成脸，且必须加 AI 标识。",
    "video-faceswap": "换脸仅限本人/已授权/合成脸，且必须加 AI 标识。",
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
            in_section = "制MV" in s and "阶段" in s
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
    if "[~]" in raw or "⏳" in raw or "rough" in raw.lower() or "占位" in raw:
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
    print(f"# mv progress — {title}")
    if not rows:
        print("[warn] _进度.md 未发现可解析的「制MV 阶段」表。")
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
        print("[done] 制MV阶段未发现阻断项。下一步：mv-review 质检，或发布前补 AI 视觉披露。")
        return 0

    row, state = frontier
    owner = row["owner"]
    owner_key = owner.split("/")[0]
    meta = owner_map.get(owner_key) or {}
    gate = meta.get("gate", "")
    hint = HIGH_RISK_HINTS.get(owner_key, "")
    print(f"[前沿] 下一步：**{row['label']}** → 跑 `{owner}`")
    if gate:
        print(f"  gate: {gate}")
    if hint:
        print(f"  ⚠️ {hint}")

    later = [r for r in rows[rows.index(row) + 1:] if state_of(r["status"]) != "done"]
    if later:
        print("\n后续待办：")
        for item in later[:limit]:
            suffix = "（可选）" if is_optional(item["label"]) else ""
            print(f"- {item['label']} → {item['owner']} {suffix}")
        if len(later) > limit:
            print(f"- ... 另有 {len(later) - limit} 项")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="读取制MV项目 _进度.md，报告下一步（只读）")
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
