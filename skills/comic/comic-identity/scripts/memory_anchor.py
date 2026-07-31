#!/usr/bin/env python3
"""跨话记忆锚计划（2026-07 标准审计·参照同仓成熟生产线 memory-sink 模式的漫画重实现，不跨线 import）。

外部基准（EntityBench Gap-Decay）与同仓成熟生产线实证一致：角色一致性随**复现间隔**急剧衰减——
长间隔再登场/晚话登场的角色最容易漂。顶尖流水线的解法是把**最早定妆关键帧钉成全局记忆锚**，
再登场时作为最高优先参考重注入。comic 线此前完全没有这层：每话出图只按当话 references 组装，
第 8 话再登场的配角和第 1 话相比"各自像定妆、彼此已漂"。

本脚本 report-only：扫描全部 脚本/第*话/panel_script.json 的角色出场史，对目标话里
- 复现间隔 ≥ GAP_CHAPTERS(默认 2) 的再登场角色，或
- 距首次登场 ≥ LATE_GAP(默认 5) 话的常驻角色，
产出 `生产数据/comic_memory_anchor_第N话.json/md`，逐角色钉住 registry 里最早的 front/face
定妆参考作为 pinned 锚。消费端：`comic-image/scripts/build_panel_jobs.py` 出图前读取本计划，
把 pinned 锚置于该角色参考组最前（文件契约·不跨 skill import 实现）。

用法：
  cd skills/comic/comic-identity/scripts
  python3 memory_anchor.py <作品根> 第N话 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

VERSION = 2
KIND = "comic_memory_anchor_plan"

GAP_CHAPTERS = int(os.environ.get("COMIC_MEMORY_ANCHOR_GAP", "2"))
LATE_GAP = int(os.environ.get("COMIC_MEMORY_ANCHOR_LATE_GAP", "5"))
MAX_PINNED_REFS = int(os.environ.get("COMIC_MEMORY_ANCHOR_MAX_REFS", "2"))
PIN_VIEWS = ("front", "face")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def chapter_number(name: str) -> Optional[int]:
    m = re.search(r"第\s*(\d+)\s*话", str(name or ""))
    return int(m.group(1)) if m else None


def normalize_chapter(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("第") and raw.endswith("话"):
        return raw
    m = re.search(r"\d+", raw)
    return f"第{int(m.group(0))}话" if m else raw


def appearance_history(root: Path) -> Dict[str, List[int]]:
    """角色 → 出场话号列表（升序）。来源：各话 panel_script.json 的 panels[].characters。"""
    history: Dict[str, set] = {}
    script_dir = root / "脚本"
    if not script_dir.is_dir():
        return {}
    for chapter_dir in script_dir.glob("第*话"):
        num = chapter_number(chapter_dir.name)
        if num is None:
            continue
        try:
            data = json.loads((chapter_dir / "panel_script.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        for panel in data.get("panels") or []:
            if not isinstance(panel, Mapping):
                continue
            for cid in panel.get("characters") or []:
                cid = str(cid).strip()
                if cid.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")):
                    history.setdefault(cid, set()).add(num)
    return {cid: sorted(nums) for cid, nums in history.items()}


def pinned_refs(registry: Mapping[str, Any], char_id: str) -> List[Dict[str, str]]:
    """registry 里该角色的最早定妆锚（front/face 优先，最多 MAX_PINNED_REFS 张）。"""
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    asset = assets.get(char_id) if isinstance(assets, Mapping) else None
    if not isinstance(asset, Mapping):
        return []
    views = asset.get("views") if isinstance(asset.get("views"), Mapping) else {}
    out: List[Dict[str, str]] = []
    for view in PIN_VIEWS:
        rel = views.get(view)
        if isinstance(rel, str) and rel.strip():
            out.append({"id": char_id, "view": view, "path": rel.strip(),
                        "role": "memory_anchor"})
        if len(out) >= MAX_PINNED_REFS:
            break
    return out


def plan_rows(history: Mapping[str, List[int]], registry: Mapping[str, Any],
              target: int) -> List[Dict[str, Any]]:
    """目标话的记忆锚计划行。纯函数·可测（registry 只读 views）。"""
    rows: List[Dict[str, Any]] = []
    for cid, chapters in sorted(history.items()):
        if target not in chapters:
            continue
        earlier = [c for c in chapters if c < target]
        reasons: List[str] = []
        if earlier:
            gap = target - max(earlier)
            if gap >= GAP_CHAPTERS:
                reasons.append(f"复现间隔 {gap} 话 ≥ {GAP_CHAPTERS}")
            if target - min(earlier) >= LATE_GAP:
                reasons.append(f"距首登场已 {target - min(earlier)} 话 ≥ {LATE_GAP}")
        if not reasons:
            continue
        refs = pinned_refs(registry, cid)
        rows.append({
            "character_id": cid,
            "first_chapter": min(earlier) if earlier else target,
            "last_seen_chapter": max(earlier) if earlier else target,
            "reasons": reasons,
            "pinned_refs": refs,
            "status": "ready" if refs else "missing_canonical_views",
        })
    return rows


def build_plan(root: Path, chapter: str) -> Dict[str, Any]:
    target = chapter_number(chapter) or 0
    history = appearance_history(root)
    try:
        registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    except Exception:
        registry = {}
    rows = plan_rows(history, registry, target)
    sources: List[Dict[str, str]] = []
    for chapter_dir in sorted((root / "脚本").glob("第*话")) if (root / "脚本").is_dir() else []:
        path = chapter_dir / "panel_script.json"
        if path.is_file():
            sources.append({"path": str(path.relative_to(root)), "sha256": file_sha256(path)})
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_sha = file_sha256(registry_path) if registry_path.is_file() else ""
    inputs = {
        "target_chapter": chapter,
        "panel_scripts": sources,
        "appearance_history_sha256": canonical_sha(history),
        "identity_registry_sha256": registry_sha,
        "policy": {"gap_chapters": GAP_CHAPTERS, "late_gap": LATE_GAP, "pin_views": list(PIN_VIEWS)},
    }
    inputs_fingerprint = canonical_sha(inputs)
    for row in rows:
        for ref in row.get("pinned_refs") or []:
            raw = str(ref.get("path") or "")
            path = Path(raw) if Path(raw).is_absolute() else root / raw
            ref["sha256"] = file_sha256(path) if path.is_file() else ""
            ref["exists"] = path.is_file()
        if row.get("status") == "ready" and not all(ref.get("exists") for ref in row.get("pinned_refs") or []):
            row["status"] = "missing_canonical_views"
    return {
        "kind": KIND, "version": VERSION, "chapter": chapter, "generated_at": now_iso(),
        "inputs": inputs,
        "inputs_fingerprint": inputs_fingerprint,
        "policy": {"gap_chapters": GAP_CHAPTERS, "late_gap": LATE_GAP,
                   "pin_views": list(PIN_VIEWS),
                   "consumer": "comic-image/build_panel_jobs 出图前把 pinned_refs 置于该角色参考组最前"},
        "summary": {"characters": len(rows),
                    "ready": sum(1 for r in rows if r["status"] == "ready"),
                    "missing_views": sum(1 for r in rows if r["status"] != "ready")},
        "characters": rows,
    }


def render_markdown(plan: Mapping[str, Any]) -> str:
    lines = [f"# 跨话记忆锚计划 · {plan.get('chapter')}", ""]
    rows = plan.get("characters") or []
    if not rows:
        lines.append("- ✅ 本话无需重注入记忆锚（无长间隔再登场/晚话常驻角色）")
    for row in rows:
        refs = "、".join(r["path"] for r in row.get("pinned_refs") or []) or "（缺 canonical 视图）"
        lines.append(f"- {row['character_id']}：{'；'.join(row['reasons'])} → 钉 {refs}")
    return "\n".join(lines) + "\n"


def plan_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / f"comic_memory_anchor_{chapter}.json"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    chapter = normalize_chapter(ns.chapter)
    plan = build_plan(root, chapter)
    if ns.write:
        out = plan_path(root, chapter)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        out.with_suffix(".md").write_text(render_markdown(plan), encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2) if ns.json else render_markdown(plan))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
