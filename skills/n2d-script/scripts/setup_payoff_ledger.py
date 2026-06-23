#!/usr/bin/env python3
"""SP1 导出端：拆集时把「伏笔种下→兑现」脚手架成 设定库/setup_payoff_ledger.json。

为什么在 n2d-script：P0 语义谱系 / P1 状态百科管的是「语义/视觉状态」跨集继承；**叙事坑**（伏笔种下
后哪一集兑现、坑别忘了填、兑现别早于种下）是另一条轴。当用户**直接丢小说文件、不经上游小说创作线**时，
漫剧侧此前没有这条兜底——本脚手架在拆集阶段从各集 voiceover/故事板里**捞出候选伏笔/悬念钩**，写成一份
待人补全兑现集的账本草稿；n2d-review 的 `extended_consistency.check_setup_payoff`(SP1) 再消费它校验整账
（坑没填 / 兑现早于种下 / 缺种下集 / 重复 id）。

诚实边界：**不自动判定哪句是伏笔**（文本自动识别伏笔不可靠）——只按显式悬念/钩子标记捞**候选**，
`payoff_ep` 一律留空交编剧填。已存在的账本**不覆盖**：默认只增量补未登记的候选（`--write` 才落盘）。

用法：
  python3 setup_payoff_ledger.py <作品根> [--episodes 1-10] [--write] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence

LEDGER_KIND = "n2d_setup_payoff_ledger"
LEDGER_REL = os.path.join("设定库", "setup_payoff_ledger.json")

# 显式悬念/钩子标记（只捞候选·不臆断伏笔）。与 n2d-review SP1 同口径（独立线·复制不 import）。
FORESHADOW_MARKERS = (
    "伏笔", "悬念", "埋下", "留下疑问", "未解", "成谜", "卖关子", "悬而未决",
    "意味深长", "别有深意", "暗藏", "似乎另有", "不为人知", "cliffhanger", "钩子",
)


# ── 纯函数（无依赖·可测） ─────────────────────────────────────────────────────

def ep_num(ep: str) -> Optional[int]:
    """'第3集' / 'ep3' / '3' → 3；解析不出 → None。"""
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


def detect_setups(text: str, ep: str) -> List[dict]:
    """从一集文本里捞候选伏笔（命中标记的句子）。每条 payoff_ep 留空交人填。纯函数·可测。"""
    out: List[dict] = []
    seen: set = set()
    for raw_line in re.split(r"[\n。！？!?]", text or ""):
        line = raw_line.strip()
        if not line or not any(m in line for m in FORESHADOW_MARKERS):
            continue
        desc = line[:40]
        if desc in seen:
            continue
        seen.add(desc)
        out.append({
            "id": f"{ep}-伏笔{len(out) + 1}",
            "setup_ep": ep,
            "payoff_ep": "",          # 交编剧填：哪一集兑现这个坑
            "desc": desc,
            "status": "open",          # open=待规划兑现；ongoing=长线进行中；done=已兑现
        })
    return out


def merge_candidates(existing: Sequence[dict], candidates: Sequence[dict]) -> List[dict]:
    """已有账本 + 新候选 → 合并（按 desc 去重·绝不覆盖已填的 payoff_ep）。纯函数·可测。"""
    merged: List[dict] = [dict(p) for p in existing if isinstance(p, dict)]
    have = {str(p.get("desc") or p.get("id")) for p in merged}
    for c in candidates:
        if str(c.get("desc") or c.get("id")) not in have:
            merged.append(dict(c))
            have.add(str(c.get("desc") or c.get("id")))
    return merged


def build_ledger(pairs: Sequence[dict]) -> dict:
    return {"kind": LEDGER_KIND, "version": 1, "pairs": list(pairs)}


# ── IO（best-effort·缺则空） ──────────────────────────────────────────────────

def _read(path: str) -> str:
    try:
        return open(path, encoding="utf-8").read()
    except Exception:
        return ""


def _episode_text(root: str, ep: str) -> str:
    parts = [
        _read(os.path.join(root, "脚本", ep, "voiceover.txt")),
        _read(os.path.join(root, "脚本", ep, "故事板.md")),
    ]
    sb = os.path.join(root, "脚本", ep, "storyboard.json")
    if os.path.isfile(sb):
        parts.append(_read(sb))
    return "\n".join(parts)


def discover_episodes(root: str) -> List[str]:
    eps = []
    for d in glob.glob(os.path.join(root, "脚本", "第*集")):
        if os.path.isdir(d):
            eps.append(os.path.basename(d))
    return sorted(eps, key=lambda e: ep_num(e) or 0)


def _parse_range(spec: str, available: Sequence[str]) -> List[str]:
    if not spec:
        return list(available)
    want: set = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                want.update(range(int(a), int(b) + 1))
            except ValueError:
                pass
        elif part.isdigit():
            want.add(int(part))
    return [e for e in available if (ep_num(e) in want)]


def load_existing(root: str) -> List[dict]:
    path = os.path.join(root, LEDGER_REL)
    if not os.path.isfile(path):
        return []
    try:
        data = json.load(open(path, encoding="utf-8"))
        return [p for p in (data.get("pairs") or data.get("setups") or []) if isinstance(p, dict)]
    except Exception:
        return []


def scaffold(root: str, episodes: Sequence[str]) -> dict:
    candidates: List[dict] = []
    for ep in episodes:
        candidates.extend(detect_setups(_episode_text(root, ep), ep))
    merged = merge_candidates(load_existing(root), candidates)
    return {"ledger": build_ledger(merged), "new_candidates": candidates, "existing": load_existing(root)}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--episodes", default="", help="如 1-10 或 3,5,7；默认全部已拆集")
    ap.add_argument("--write", action="store_true", help="落盘 设定库/setup_payoff_ledger.json（不覆盖已填 payoff）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    eps = _parse_range(ns.episodes, discover_episodes(root))
    res = scaffold(root, eps)
    if ns.write:
        path = os.path.join(root, LEDGER_REL)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(res["ledger"], fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    n_new = len(res["new_candidates"])
    n_total = len(res["ledger"]["pairs"])
    print(f"扫描 {len(eps)} 集 · 新捞候选伏笔 {n_new} 条 · 账本共 {n_total} 条"
          + ("（已写盘）" if ns.write else "（未写盘，加 --write 落档）"))
    for p in res["ledger"]["pairs"]:
        flag = "⚠待填兑现集" if not p.get("payoff_ep") and p.get("status") not in ("ongoing", "done") else ""
        print(f"  [{p.get('setup_ep')}→{p.get('payoff_ep') or '?'}] {p.get('desc')} {flag}")
    if any(not p.get("payoff_ep") and p.get("status") not in ("ongoing", "done") for p in res["ledger"]["pairs"]):
        print("\n下一步：给每个伏笔填 payoff_ep（哪一集兑现）或标 status=ongoing；"
              "n2d-review SP1 会校验坑没填/兑现早于种下。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
