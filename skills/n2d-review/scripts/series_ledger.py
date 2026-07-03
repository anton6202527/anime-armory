#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""剧级验收总账（series-level acceptance ledger）—— 把"每集是否可交付"上卷成"整季是否可交付"。

为什么需要它：`consistency_ledger.py` 的验收终点是**每集**（`consistency_ledger_第N集.json`），
`run.py` 的最终签收也以单集总账为交付面。但漫剧是按**季/系列**上线的——一部剧 30 集里只要
有一集带 block、或某个主角的脸在第 12 集开始跨集漂移、或还有集压根没出验收总账，整季就不该签收。
本脚本是现有 ledger 模式的自然上卷：纯聚合、不重算、不审片，只回答"这一整季能不能交付"。

聚合三类输入（都是已落档的机检产物，缺失优雅降级）：
  1. 每集 `生产数据/consistency_ledger_第N集.json` —— 单集 block/high/medium 计数 + 交付状态；
  2. 跨集 `生产数据/identity_drift_report.json`（n2d-identity 产）—— 逐角色跨集脸漂，
     `total_block>0` = 系列级身份阻断，并给 `first_bad_episode`；
  3.（可选）`生产数据/series_retention.json` —— 系列留存/钩子曲线塌陷（有则并入观察，不阻断签收，
     留存是"该不该改"而非"能不能交付"，与 score 分工一致）。

剧级 `delivery_surface.status`：
  - blocked —— 任一集 block>0 或 high>0、或有集**缺验收总账**（脚本已出但未签收）、或有角色跨集脸漂到 block；
  - pass —— 以上全无。
阻断原因逐条列在 `delivery_surface.blocking`，可直接指到"回去签收第几集 / 哪个角色从第几集开始漂"。

用法：
    python3 series_ledger.py <作品根> [--episodes 第1集,第3集...] [--json] [--strict]
    --strict：blocked 时退出码 1（供 CI / 批量签收闸门）；默认 0（只读报告）。
从本目录跑测试：cd skills/n2d-review/scripts && python3 -m pytest test_series_ledger.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SERIES_LEDGER_KIND = "n2d_series_ledger"
VERSION = 1

_EP_NUM_RE = re.compile(r"\d+")


def _ep_num(label: str) -> int:
    m = _EP_NUM_RE.search(label or "")
    return int(m.group()) if m else 10**9


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _counts_of(ledger: Optional[Mapping[str, Any]]) -> Dict[str, int]:
    counts = (ledger or {}).get("counts") if isinstance(ledger, Mapping) else {}
    counts = counts if isinstance(counts, Mapping) else {}
    return {
        "block": int(counts.get("block") or 0),
        "high": int(counts.get("high") or 0),
        "medium": int(counts.get("medium") or 0),
    }


def _episode_entry(ep: str, ledger: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """单集卷积条目。ledger 缺失 = 该集未签收（present=False），系列级视为阻断项。"""
    if ledger is None:
        return {"episode": ep, "present": False, "status": "missing",
                "counts": {"block": 0, "high": 0, "medium": 0}}
    counts = _counts_of(ledger)
    surface = ledger.get("delivery_surface") if isinstance(ledger.get("delivery_surface"), Mapping) else {}
    status = str(surface.get("status") or "").strip().lower()
    # block/high 计数**独立**重算季级状态，不轻信子 surface：子 ledger 可能报 status=pass 却 counts.high>0
    # （docstring 声称 high 阻断却被子 pass 静默覆盖）。真有 block/high 一律 blocked，子 pass 不放行。
    if counts["block"] or counts["high"]:
        status = "blocked"
    elif status not in ("pass", "blocked"):
        status = "pass"
    return {"episode": ep, "present": True, "status": status, "counts": counts}


def _identity_blockers(identity_drift: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """从跨集脸漂报告抽系列级身份信号：block 角色（total_block>0）+ warn 角色 + 各自起漂集。"""
    out: Dict[str, Any] = {
        "available": False,
        "block_characters": [],   # [{character, first_bad_episode, total_block}]
        "warn_characters": [],    # [{character, first_bad_episode, total_warn}]
    }
    if not isinstance(identity_drift, Mapping):
        return out
    out["available"] = bool(identity_drift.get("available", True))
    chars = identity_drift.get("characters")
    if not isinstance(chars, Mapping):
        return out
    for name, info in sorted(chars.items()):
        if not isinstance(info, Mapping):
            continue
        total_block = int(info.get("total_block") or 0)
        total_warn = int(info.get("total_warn") or 0)
        first_bad = str(info.get("first_bad_episode") or "").strip()
        if total_block > 0:
            out["block_characters"].append(
                {"character": name, "first_bad_episode": first_bad, "total_block": total_block})
        elif total_warn > 0:
            out["warn_characters"].append(
                {"character": name, "first_bad_episode": first_bad, "total_warn": total_warn})
    return out


def build_series_ledger(
    *,
    episode_ledgers: Sequence[Tuple[str, Optional[Mapping[str, Any]]]],
    identity_drift: Optional[Mapping[str, Any]] = None,
    retention: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """剧级总账（纯函数·可测）。

    episode_ledgers：有序 [(集标签, 单集 ledger dict 或 None), ...]。None = 该集未签收。
    """
    episodes: List[Dict[str, Any]] = [_episode_entry(ep, lg) for ep, lg in episode_ledgers]

    totals = {"block": 0, "high": 0, "medium": 0}
    blocked_eps: List[str] = []
    missing_eps: List[str] = []
    for e in episodes:
        for k in totals:
            totals[k] += e["counts"][k]
        if not e["present"]:
            missing_eps.append(e["episode"])
        elif e["status"] == "blocked":
            blocked_eps.append(e["episode"])

    ident = _identity_blockers(identity_drift)
    identity_block_chars = [c["character"] for c in ident["block_characters"]]

    # 跨集脸漂报告缺失/不可用 = 季级头号风险（跨集崩脸）**未核验**——对称于「缺集 ledger 阻断」。
    # 多集季(≥2)才有跨集语义，故仅多集时把「缺身份报告」当阻断项，避免单集/早期作品误挡。
    present_eps = sum(1 for e in episodes if e["present"])
    identity_report_missing = (not ident["available"]) and present_eps >= 2

    is_blocked = bool(blocked_eps or missing_eps or identity_block_chars or identity_report_missing)

    # 最薄弱集排序（block > high > medium），给"先回去签收/返工哪几集"一个明确次序。
    def _weak_key(e: Dict[str, Any]) -> Tuple[int, int, int, int]:
        c = e["counts"]
        # 缺签收（present=False）排最前 → 0；其余按 block/high/medium 降序。
        return (0 if not e["present"] else 1, -c["block"], -c["high"], -c["medium"])

    weakest = [e["episode"] for e in sorted(episodes, key=_weak_key)
               if (not e["present"]) or e["status"] == "blocked"]

    retention_summary = None
    if isinstance(retention, Mapping):
        retention_summary = {
            "available": True,
            "status": str(retention.get("status") or retention.get("verdict") or "unknown"),
            "note": "留存信号只观察、不阻断剧级签收（该不该改 ≠ 能不能交付）。",
        }

    return {
        "kind": SERIES_LEDGER_KIND,
        "version": VERSION,
        "episode_count": len(episodes),
        "ledgers_present": sum(1 for e in episodes if e["present"]),
        "episodes": episodes,
        "counts": totals,
        "cross_episode": {
            "identity_drift": ident,
            "retention": retention_summary,
        },
        "delivery_surface": {
            "status": "blocked" if is_blocked else "pass",
            "blocking": {
                "episodes_blocked": blocked_eps,
                "episodes_missing_ledger": missing_eps,
                "identity_block_characters": ident["block_characters"],
                "identity_report_missing": identity_report_missing,
            },
            "weakest_episodes": weakest,
            "blocking_counts": {"block": totals["block"], "high": totals["high"]},
        },
    }


# ── I/O 层 ───────────────────────────────────────────────────────────────────
def discover_episodes(root: str) -> List[str]:
    """系列内集标签：取 脚本/第*集/ 与已有 consistency_ledger_*.json 的并集，按集号排序。"""
    labels = set()
    sdir = os.path.join(root, "脚本")
    try:
        for d in os.listdir(sdir):
            if d.startswith("第") and d.endswith("集") and os.path.isdir(os.path.join(sdir, d)):
                labels.add(d)
    except OSError:
        pass
    prod = os.path.join(root, "生产数据")
    try:
        for fn in os.listdir(prod):
            m = re.match(r"consistency_ledger_(第\d+集)\.json$", fn)
            if m:
                labels.add(m.group(1))
    except OSError:
        pass
    return sorted(labels, key=_ep_num)


def run(root: str, episodes: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    root = root.rstrip("/")
    eps = list(episodes) if episodes else discover_episodes(root)
    prod = os.path.join(root, "生产数据")
    episode_ledgers: List[Tuple[str, Optional[Dict[str, Any]]]] = []
    for ep in eps:
        episode_ledgers.append((ep, _load_json(os.path.join(prod, f"consistency_ledger_{ep}.json"))))
    identity_drift = _load_json(os.path.join(prod, "identity_drift_report.json"))
    retention = _load_json(os.path.join(prod, "series_retention.json"))

    ledger = build_series_ledger(
        episode_ledgers=episode_ledgers,
        identity_drift=identity_drift,
        retention=retention,
    )

    os.makedirs(prod, exist_ok=True)
    json_path = os.path.join(prod, "series_ledger.json")
    md_path = os.path.join(prod, "series_ledger.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(ledger))
    ledger["json_path"], ledger["markdown_path"] = json_path, md_path
    return ledger


_SEV_ICON = {"blocked": "⛔", "missing": "⬜", "pass": "✅"}


def render_markdown(ledger: Mapping[str, Any]) -> str:
    surface = ledger.get("delivery_surface") or {}
    counts = ledger.get("counts") or {}
    status = surface.get("status")
    lines = [
        f"# 剧级验收总账 · {_SEV_ICON.get(status, '❓')} {status}",
        "",
        f"- 集数：{ledger.get('episode_count')}（已签收 {ledger.get('ledgers_present')}）",
        f"- 全季计数：⛔block {counts.get('block', 0)} · 🔴high {counts.get('high', 0)} · 🟡medium {counts.get('medium', 0)}",
        "",
        "| 集 | 状态 | block | high | medium |",
        "|---|---|---:|---:|---:|",
    ]
    for e in ledger.get("episodes", []):
        c = e["counts"]
        lines.append(f"| {e['episode']} | {_SEV_ICON.get(e['status'], e['status'])} | "
                     f"{c['block']} | {c['high']} | {c['medium']} |")

    blocking = surface.get("blocking") or {}
    if status == "blocked":
        lines += ["", "## 阻断项（清零才可签收整季）"]
        if blocking.get("episodes_missing_ledger"):
            lines.append(f"- ⬜ 缺验收总账（脚本已出未签收）：{'、'.join(blocking['episodes_missing_ledger'])}")
        if blocking.get("episodes_blocked"):
            lines.append(f"- ⛔ 单集仍有 block/high：{'、'.join(blocking['episodes_blocked'])}")
        for bc in blocking.get("identity_block_characters", []):
            fb = bc.get("first_bad_episode") or "?"
            lines.append(f"- ⛔ 跨集脸漂：{bc.get('character')}（自 {fb} 起，block×{bc.get('total_block')}）")
    else:
        lines += ["", "✅ 全季每集已签收且无跨集身份阻断，可交付。"]

    ident = ((ledger.get("cross_episode") or {}).get("identity_drift") or {})
    if ident.get("warn_characters"):
        lines += ["", "## 跨集身份观察（warn·非阻断）"]
        for wc in ident["warn_characters"]:
            lines.append(f"- 🟡 {wc.get('character')}（自 {wc.get('first_bad_episode') or '?'} 起，warn×{wc.get('total_warn')}）")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--episodes", default=None,
                    help="逗号分隔的集标签（默认自动发现 脚本/ 与已有 ledger 的并集）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="blocked 时退出码 1（供 CI / 批量签收闸门）")
    ns = ap.parse_args(argv)
    eps = [e.strip() for e in ns.episodes.split(",") if e.strip()] if ns.episodes else None
    ledger = run(ns.root, eps)

    status = (ledger.get("delivery_surface") or {}).get("status")
    if ns.json:
        print(json.dumps(ledger, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_markdown(ledger))
        print(f"→ {ledger['markdown_path']}")
    return 1 if (ns.strict and status == "blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
