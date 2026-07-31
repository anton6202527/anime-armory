#!/usr/bin/env python3
"""面板构图重复机检（2026-07 标准审计·参照同仓成熟生产线镜头多样性机检模式的漫画重实现，不跨线 import）。

条漫读者一屏能同时看到多格——近重复构图比视频更立刻穿帮。此前 comic 的一致性机检全部
只抓"太不同=漂移"，没有"太相似=重复"的反向告警（similarity 高反而被判为好）。

本检对本话 `出图/第N话/panels/*.png` 做全两两 64 位 dHash：
- 距离 ≤ DUP_WARN(默认 8)：近重复构图 warn（业界感知哈希实践：d≤5 判重、d≤10 宽松上限——
  2026-07 实搜 idealo/imagededup 默认 10、生产系统多用 ≤5；取 8 折中，env 可标定）。
- 相邻格（P00N 与 P00N+1）豁免距离 ≤ ADJACENT_OK(默认 4) 的对——连续动作微差是合法手法；
  非相邻近重复没有该借口。

report-only（exit 0），Pillow 缺失优雅跳过。用法：
  cd skills/comic/comic-review/scripts
  python3 panel_variety.py <作品根> 第N话 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

VERSION = 1
KIND = "comic_panel_variety"

DUP_WARN = int(os.environ.get("COMIC_PANEL_DUP_DHASH", "8"))
ADJACENT_OK = int(os.environ.get("COMIC_PANEL_ADJACENT_OK_DHASH", "4"))
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_chapter(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("第") and raw.endswith("话"):
        return raw
    m = re.search(r"\d+", raw)
    return f"第{int(m.group(0))}话" if m else raw


def dhash_bits(path: Path, size: int = 8) -> Optional[List[int]]:
    """64 位差值哈希；Pillow 缺失/解码失败 → None（诚实降级，不臆造）。"""
    try:
        from PIL import Image
    except Exception:
        return None
    try:
        with Image.open(path) as im:
            gray = im.convert("L").resize((size + 1, size))
            getter = getattr(gray, "get_flattened_data", None) or gray.getdata  # Pillow 14 弃用 getdata
            px = list(getter())
    except Exception:
        return None
    bits: List[int] = []
    for row in range(size):
        line = px[row * (size + 1):(row + 1) * (size + 1)]
        bits.extend(1 if line[col] > line[col + 1] else 0 for col in range(size))
    return bits


def hamming(a: List[int], b: List[int]) -> int:
    return sum(x != y for x, y in zip(a, b))


def panel_number(name: str) -> Optional[int]:
    m = re.search(r"P0*(\d+)", name, re.IGNORECASE)
    return int(m.group(1)) if m else None


def duplicate_pairs(hashes: Mapping[str, List[int]], *,
                    dup_warn: int = DUP_WARN,
                    adjacent_ok: int = ADJACENT_OK) -> List[Dict[str, Any]]:
    """全两两近重复对；相邻格微差豁免。纯函数·可测。"""
    names = sorted(hashes)
    out: List[Dict[str, Any]] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            dist = hamming(hashes[names[i]], hashes[names[j]])
            if dist > dup_warn:
                continue
            na, nb = panel_number(names[i]), panel_number(names[j])
            adjacent = na is not None and nb is not None and abs(na - nb) == 1
            if adjacent and dist <= adjacent_ok:
                continue  # 连续动作微差合法
            out.append({"panels": [names[i], names[j]], "dhash": dist, "adjacent": adjacent})
    return out


def build_report(root: Path, chapter: str) -> Dict[str, Any]:
    panels_dir = root / "出图" / chapter / "panels"
    files = sorted(p for p in panels_dir.glob("*") if p.suffix.lower() in IMAGE_EXTS) \
        if panels_dir.is_dir() else []
    hashes: Dict[str, List[int]] = {}
    unreadable: List[str] = []
    for path in files:
        bits = dhash_bits(path)
        if bits is None:
            unreadable.append(path.name)
        else:
            hashes[path.stem] = bits
    available = bool(hashes) or not files
    pairs = duplicate_pairs(hashes) if hashes else []
    findings = [{
        "severity": "warn", "code": "near_duplicate_panels",
        "message": f"{pair['panels'][0]} ↔ {pair['panels'][1]} 构图近重复（dHash={pair['dhash']}/64"
                   + ("·相邻格" if pair["adjacent"] else "·非相邻格")
                   + "）——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡重出其一，或合并格。",
    } for pair in pairs]
    return {
        "kind": KIND, "version": VERSION, "chapter": chapter, "generated_at": now_iso(),
        "available": available,
        "thresholds": {"dup_warn": DUP_WARN, "adjacent_ok": ADJACENT_OK,
                       "provenance": "2026-07 实搜：imagededup 默认 d≤10 宽松上限、生产系统多用 ≤5；取 8 折中·env 可标定"},
        "summary": {"panels": len(files), "hashed": len(hashes),
                    "unreadable": len(unreadable), "duplicate_pairs": len(pairs)},
        "unreadable": unreadable,
        "duplicate_pairs": pairs,
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [f"# 面板构图重复机检 · {report.get('chapter')}",
             "",
             f"- 面板 {s.get('panels')} · 已哈希 {s.get('hashed')} · 近重复对 {s.get('duplicate_pairs')}",
             ""]
    for f in report.get("findings") or []:
        lines.append(f"- ⚠️ `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 未检出面板近重复构图")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    chapter = normalize_chapter(ns.chapter)
    report = build_report(root, chapter)
    if ns.write:
        out = root / "生产数据"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"comic_panel_variety_{chapter}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / f"comic_panel_variety_{chapter}.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
