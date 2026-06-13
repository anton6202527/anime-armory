#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""候选项新鲜度检查（本线 · 纯标准库 · 无网络/模型调用）。

实现「候选项快照 + 适配层 + 手输兜底 + 新鲜度标注」原则里**可机检的那一半**：
`skills/ad-craft/references/选择点与偏好.md` 要求所有易变候选清单（模型/平台/价格/规格/法规…）都带采集日期，
正式花钱/不可逆/合规步骤前必须按需要核验刷新。本模块只回答一个问题——
**「这些候选快照各自多久没核验了，哪些该刷新了？」**，把散落的 prose 约定变成
review 流程自审可以一键跑的机检。

设计要点：
- 单一真值源：`CANDIDATE_SOURCES` 登记全仓库的易变候选清单（md 快照 + py catalog），
  同目录 refresh.py 复用同一份登记，避免两处各抄一份。
- 统一戳记：无论 markdown 还是 python catalog，都用同一行 `采集日期：YYYY-MM-DD`
  注释/字段标注，本模块只 regex 不 import 业务模块，保持纯净 & 零副作用。
- 透明失败：解析不到日期 = `missing`（当作必须人工核验），不静默当“新鲜”。

CLI:
    cd skills/<line>/_lib && python3 freshness.py                 # 默认阈值，全量
    python3 freshness.py --max-age 30 --today 2026-06-13     # 指定阈值/基准日
    python3 freshness.py --json                              # 机读输出
退出码：0=全部新鲜；3=有 stale/missing（供 CI / 自审脚本判定）。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
from typing import Dict, List, Optional


# 仓库根（本文件在 skills/<line>/_lib/ 下）
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))  # 本文件在 skills/<line>/_lib/ 下

# 采集日期戳记：md 快照顶部写「采集日期：2026-06-13」；py catalog 写同样一行注释/常量。
# 兼容全角/半角冒号；只取第一处出现（快照顶部）。
_STAMP_RE = re.compile(r"采集日期\s*[:：]\s*(\d{4}-\d{2}-\d{2})")


# ── 候选源登记表（ad 线本地易变候选清单）──────────────────────────────────
# 每条：相对仓库根的路径、它覆盖的选择点、刷新最长容忍天数、备注。
# 新增易变候选清单（新后端 catalog）务必在此登记，否则机检/刷新都看不到它。
CANDIDATE_SOURCES: List[Dict[str, object]] = [
    {
        "id": "ad-image-backends",
        "path": "skills/ad-craft/scripts/contract.py",
        "choice_points": ["生图AI"],
        "max_age_days": 45,
        "note": "AD_APPROVED/FORBIDDEN 生图后端白名单（ad 线策略，与 n2d 故意不同：禁即梦）。",
    },
]


def parse_stamp(text: str) -> Optional[str]:
    """从文本里取第一处「采集日期：YYYY-MM-DD」；取不到返回 None。"""
    m = _STAMP_RE.search(text or "")
    return m.group(1) if m else None


def _read(path: str) -> Optional[str]:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def stamp_age_days(date_str: str, today: Optional[_dt.date] = None) -> Optional[int]:
    """采集日期距今天数；日期不合法返回 None。负数（未来日期）按 0 处理。"""
    today = today or _dt.date.today()
    try:
        d = _dt.date.fromisoformat(date_str)
    except ValueError:
        return None
    return max(0, (today - d).days)


def check_source(source: Dict[str, object], today: Optional[_dt.date] = None) -> Dict[str, object]:
    """检查单个候选源，返回 {id, path, stamp, age_days, status, ...}。

    status ∈ {fresh, stale, missing_file, missing_stamp, bad_stamp}。
    """
    today = today or _dt.date.today()
    rel = str(source["path"])
    abspath = os.path.join(REPO_ROOT, rel)
    max_age = int(source.get("max_age_days", 30))
    out: Dict[str, object] = {
        "id": source["id"],
        "path": rel,
        "choice_points": list(source.get("choice_points", [])),
        "max_age_days": max_age,
        "stamp": None,
        "age_days": None,
        "status": "fresh",
        "note": source.get("note", ""),
    }
    text = _read(abspath)
    if text is None:
        out["status"] = "missing_file"
        return out
    stamp = parse_stamp(text)
    if not stamp:
        out["status"] = "missing_stamp"
        return out
    out["stamp"] = stamp
    age = stamp_age_days(stamp, today)
    if age is None:
        out["status"] = "bad_stamp"
        return out
    out["age_days"] = age
    out["status"] = "stale" if age > max_age else "fresh"
    return out


def check_all(today: Optional[_dt.date] = None) -> List[Dict[str, object]]:
    today = today or _dt.date.today()
    return [check_source(s, today) for s in CANDIDATE_SOURCES]


_BAD_STATUSES = {"stale", "missing_stamp", "bad_stamp", "missing_file"}


def has_problems(results: List[Dict[str, object]]) -> bool:
    return any(r["status"] in _BAD_STATUSES for r in results)


_ICON = {
    "fresh": "✅",
    "stale": "⚠️ 过期",
    "missing_stamp": "❓ 无采集日期",
    "bad_stamp": "❓ 日期非法",
    "missing_file": "❌ 文件缺失",
}


def render_table(results: List[Dict[str, object]]) -> str:
    lines = ["| 候选源 | 选择点 | 采集日期 | 距今 | 阈值 | 状态 |",
             "|---|---|---|---|---|---|"]
    for r in results:
        age = "" if r["age_days"] is None else f"{r['age_days']}d"
        cps = "/".join(r["choice_points"])
        lines.append(
            f"| {r['id']} | {cps} | {r['stamp'] or '—'} | {age} | "
            f"{r['max_age_days']}d | {_ICON.get(str(r['status']), r['status'])} |"
        )
    return "\n".join(lines)


def _main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="候选项快照新鲜度检查")
    ap.add_argument("--max-age", type=int, default=None,
                    help="统一覆盖各源的最长容忍天数（默认用每源各自的 max_age_days）")
    ap.add_argument("--today", default=None, help="基准日 YYYY-MM-DD（默认系统今天）")
    ap.add_argument("--json", action="store_true", help="输出机读 JSON")
    args = ap.parse_args(argv)

    today = _dt.date.fromisoformat(args.today) if args.today else _dt.date.today()
    sources = CANDIDATE_SOURCES
    if args.max_age is not None:
        sources = [dict(s, max_age_days=args.max_age) for s in sources]
    results = [check_source(s, today) for s in sources]

    if args.json:
        print(json.dumps({"today": today.isoformat(), "results": results},
                         ensure_ascii=False, indent=2))
    else:
        print(f"# 候选项新鲜度（基准日 {today.isoformat()}）\n")
        print(render_table(results))
        bad = [r for r in results if r["status"] in _BAD_STATUSES]
        if bad:
            print(f"\n{len(bad)} 项需刷新 → 跑 本线 _lib/refresh.py（搜索+核验+落档带来源）。")
        else:
            print("\n全部新鲜。")
    return 3 if has_problems(results) else 0


if __name__ == "__main__":
    raise SystemExit(_main())
