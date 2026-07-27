#!/usr/bin/env python3
"""跨话角色漂移报表（2026-07 标准审计·参照同仓成熟生产线跨集漂移报表的漫画重实现，不跨线 import）。

为什么存在：漫画线此前的一致性机检都是**单话**的——`character_consistency` 逐话出并排复核图和 findings，
`memory_anchor` 事前钉锚，`reference_planner` 事前处方。但"这个角色从**第几话**开始崩、是不是**跨话反复**崩"
没有任何机器统计，只能靠人脑记。长线连载条漫跨话脸漂随复现间隔累积（Gap-Decay），不落成跨话报表就治不到根。

本报表把各话已生成的 `生产数据/comic_character_consistency_第N话.json` 汇总成**逐角色×逐话**的
ok/warn/block 时间线，标出 `first_bad_chapter`（第几话开始崩）、跨话漂移话次数，并按 findings 类别给
工程化修复建议（补参考/补服装/补专门定妆/换持久主体后端）。**只读各话报告、只写汇总报表**——不重算像素、
不改 registry、不重抽。默认 report-only。

用法：
  cd skills/comic-identity/scripts
  python3 drift_report.py <作品根> [--chapters 1-10] [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

VERSION = 1
KIND = "comic_identity_drift_report"

_SEV_RANK = {"ok": 0, "info": 0, "warn": 1, "block": 2}
_RANK_SEV = {0: "ok", 1: "warn", 2: "block"}


# ── 纯函数（无依赖·可测） ─────────────────────────────────────────────────────

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def chapter_num(value: str) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def parse_chapter_range(spec: str, available: Sequence[str]) -> List[str]:
    if not spec:
        return list(available)
    want: set = set()
    for part in str(spec).split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            try:
                want.update(range(int(a), int(b) + 1))
            except ValueError:
                pass
        elif part.isdigit():
            want.add(int(part))
    return [c for c in available if chapter_num(c) in want]


def char_status_in_report(report: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    """一话的 character_consistency 报告 → {char_id: {status, codes}}。纯函数·可测。

    status = 该角色所有 findings 里最严重的一档（block>warn>ok）；出现在 characters 行但无不良 finding=ok。"""
    out: Dict[str, Dict[str, Any]] = {}
    for row in report.get("characters") or []:
        cid = str(row.get("character_id") or "").strip()
        if cid.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")):
            out.setdefault(cid, {"rank": 0, "codes": set()})
    for f in report.get("findings") or []:
        cid = str(f.get("character_id") or "").strip()
        if not cid.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")):
            continue
        rank = _SEV_RANK.get(str(f.get("severity") or "warn"), 1)
        entry = out.setdefault(cid, {"rank": 0, "codes": set()})
        entry["rank"] = max(entry["rank"], rank)
        code = str(f.get("code") or "").strip()
        if rank >= 1 and code:
            entry["codes"].add(code)
    return {cid: {"status": _RANK_SEV[e["rank"]], "codes": sorted(e["codes"])}
            for cid, e in out.items()}


def recommend(char_id: str, bad_chapters: Sequence[str], codes: Sequence[str]) -> Optional[str]:
    """按漂移话次数 + finding 类别给工程化修复建议。纯函数·可测。"""
    codes = set(codes)
    if not bad_chapters:
        return None
    if any(c == "character_reference_missing" for c in codes):
        return (f"{char_id}：{'、'.join(bad_chapters)} 缺可读共享参考——回 comic-identity 补 anchor/front/face 定妆，"
                "重建出图包并重抽受影响格（根因是没参考，不是模型不稳）。")
    if any("outfit" in c for c in codes):
        return (f"{char_id}：{'、'.join(bad_chapters)} 服装漂移——在 registry.assets 的 outfits 子注册登记该换装"
                "（描述+参考图+绝不清单），重抽换装格；锁脸锁不住领型/纽扣/花纹。")
    if len(bad_chapters) >= 2:
        return (f"{char_id}：跨 {len(bad_chapters)} 话反复漂移（{'、'.join(bad_chapters)}）——补专门定妆多视图"
                "（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；"
                "漫画线不内置 LoRA，坚持一致性可本线外训练后把产出登记为 registry 参考。")
    return (f"{char_id}：仅 {bad_chapters[0]} 单话漂移——按该话 identity report 的 rerun_targets 重抽受影响格即可，"
            "先不升重资产。")


def build_timeline(chapter_reports: Sequence[tuple]) -> Dict[str, Any]:
    """[(chapter, report_dict)] → 逐角色跨话漂移汇总。纯函数·可测。"""
    chapters = [ch for ch, _ in chapter_reports]
    per_char: Dict[str, Dict[str, Any]] = {}
    for chapter, report in chapter_reports:
        for cid, st in char_status_in_report(report).items():
            entry = per_char.setdefault(cid, {"char_id": cid, "chapter_status": {}, "codes": set()})
            entry["chapter_status"][chapter] = st["status"]
            entry["codes"].update(st["codes"])
    rows: List[Dict[str, Any]] = []
    for cid in sorted(per_char):
        entry = per_char[cid]
        status_by_ch = entry["chapter_status"]
        bad = [ch for ch in chapters if status_by_ch.get(ch) in ("warn", "block")]
        block = [ch for ch in chapters if status_by_ch.get(ch) == "block"]
        first_bad = min(bad, key=lambda c: chapter_num(c) or 0) if bad else None
        rows.append({
            "char_id": cid,
            "appeared_chapters": [ch for ch in chapters if ch in status_by_ch],
            "chapter_status": status_by_ch,
            "first_bad_chapter": first_bad,
            "warn_or_block_chapters": bad,
            "block_chapters": block,
            "codes": sorted(entry["codes"]),
            "recommendation": recommend(cid, bad, entry["codes"]),
        })
    return {
        "chapters": chapters,
        "characters": rows,
        "summary": {
            "chapters_scanned": len(chapters),
            "characters_tracked": len(rows),
            "characters_with_drift": sum(1 for r in rows if r["warn_or_block_chapters"]),
            "characters_block": sum(1 for r in rows if r["block_chapters"]),
        },
    }


# ── IO ────────────────────────────────────────────────────────────────────────

def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def discover_chapter_reports(root: Path) -> List[tuple]:
    base = root / "生产数据"
    if not base.is_dir():
        return []
    out: List[tuple] = []
    for path in base.glob("comic_character_consistency_第*话.json"):
        data = load_json(path, {})
        if isinstance(data, Mapping):
            ch = str(data.get("chapter") or path.stem.replace("comic_character_consistency_", ""))
            out.append((ch, data))
    return sorted(out, key=lambda t: chapter_num(t[0]) or 0)


def build_report(root: Path, chapter_spec: str = "") -> Dict[str, Any]:
    reports = discover_chapter_reports(root)
    if chapter_spec:
        keep = set(parse_chapter_range(chapter_spec, [ch for ch, _ in reports]))
        reports = [(ch, r) for ch, r in reports if ch in keep]
    timeline = build_timeline(reports)
    notes: List[str] = []
    if not reports:
        notes.append("未找到任何 comic_character_consistency_第N话.json——先逐话跑 comic-review 生成单话一致性报告。")
    return {
        "kind": KIND, "version": VERSION, "generated_at": now_iso(),
        "provenance": "跨话汇总各话 character_consistency 报告·标 first_bad_chapter·report-only·2026-07",
        "summary": timeline["summary"],
        "chapters": timeline["chapters"],
        "characters": timeline["characters"],
        "notes": notes,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    chapters = report.get("chapters") or []
    lines = ["# 跨话角色漂移报表", "",
             f"- 扫描 {s.get('chapters_scanned')} 话 · 追踪 {s.get('characters_tracked')} 角色 · "
             f"有漂移 {s.get('characters_with_drift')} · 含 block {s.get('characters_block')}", ""]
    icon = {"ok": "🟢", "warn": "🟡", "block": "🔴"}
    if chapters:
        lines.append("| 角色 | " + " | ".join(chapters) + " | 首崩话 |")
        lines.append("|---|" + "---|" * (len(chapters) + 1))
        for r in report.get("characters") or []:
            cells = [icon.get(r["chapter_status"].get(ch, ""), "·") if ch in r["chapter_status"] else "" for ch in chapters]
            lines.append(f"| {r['char_id']} | " + " | ".join(cells) + f" | {r.get('first_bad_chapter') or '—'} |")
        lines.append("")
    recs = [r["recommendation"] for r in report.get("characters") or [] if r.get("recommendation")]
    if recs:
        lines.append("## 修复建议")
        lines += [f"- {rec}" for rec in recs]
    else:
        lines.append("- ✅ 未检出跨话角色漂移")
    for note in report.get("notes") or []:
        lines.append(f"- · {note}")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--chapters", default="", help="如 1-10 或 3,5；默认全部有报告的话")
    ap.add_argument("--write", action="store_true", help="写 生产数据/comic_identity_drift_report.json/md")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = build_report(root, ns.chapters)
    if ns.write:
        out = root / "生产数据"
        out.mkdir(parents=True, exist_ok=True)
        (out / "comic_identity_drift_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / "comic_identity_drift_report.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
