#!/usr/bin/env python3
"""话内冗余机检（2026-07 标准审计·port 自 n2d 冗余机检模式的漫画重实现，不跨线 import）。

条漫/页漫读者一屏能看到多格，冗余比视频更显眼，但此前 comic 线零机检覆盖四类问题：
① redundant_text_pair：台词/旁白两两 char-2gram Jaccard ≥ 阈值 = 同义反复（小说式复述被带进分格）。
② repeated_fact_mention：同一事实短语在 ≥3 格复现（措辞不同的复述，Jaccard 抓不到）。
③ narration_heavy_chapter：旁白格占比过高 = 信息压缩靠"旁白硬转"而非画面化（实证：金瓶梅
   source_semantics 把整段背景"并入"成冷旁白——缩短了但没消解，条漫应"能画不说"）。
④ repeated_composition_plan：(场景锚 × 出镜角色 × 景别档) 相同的格 ≥2 = 计划层构图重复，
   出图前就该换景别/机位或合并（一屏多格时重复构图立刻穿帮）。

口径诚实：阈值是内部启发式（confidence=low·env 可标定），默认 report-only（exit 0）；
`--strict` 只对高置信命中（相似度 ≥ STRICT_SIM）exit 1。先跑两部作品校准误报再议升硬闸。

用法：
  cd skills/comic-review/scripts
  python3 redundancy_audit.py <作品根> 第N话 [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

VERSION = 1
KIND = "comic_redundancy_audit"

PAIR_SIM_WARN = float(os.environ.get("COMIC_REDUNDANCY_SIM_WARN", "0.6"))
STRICT_SIM = float(os.environ.get("COMIC_REDUNDANCY_SIM_STRICT", "0.75"))
MIN_TEXT_CHARS = int(os.environ.get("COMIC_REDUNDANCY_MIN_CHARS", "8"))
NARRATION_RATIO_WARN = float(os.environ.get("COMIC_NARRATION_RATIO_WARN", "0.5"))
FACT_NGRAM_LEN = int(os.environ.get("COMIC_FACT_NGRAM_LEN", "4"))
FACT_MIN_PANELS = int(os.environ.get("COMIC_FACT_MIN_PANELS", "3"))

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】]+")
_LENS_CLASS_RE = re.compile(
    r"ECU|CU|MCU|MS|MLS|LS|WS|EWS|OTS|POV|特写|近景|中景|全景|远景|大远景|过肩|俯视|仰视|鸟瞰",
    re.IGNORECASE,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_chapter(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("第") and raw.endswith("话"):
        return raw
    m = re.search(r"\d+", raw)
    return f"第{int(m.group(0))}话" if m else raw


def load_panels(root: Path, chapter: str) -> List[Dict[str, Any]]:
    path = root / "脚本" / chapter / "panel_script.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    panels = data.get("panels") if isinstance(data, Mapping) else None
    return [p for p in (panels or []) if isinstance(p, Mapping)]


def panel_texts(panel: Mapping[str, Any]) -> List[Dict[str, str]]:
    """一格里的可嵌字文本行：台词（text_target 优先）+ 旁白。纯函数·可测。"""
    out: List[Dict[str, str]] = []
    pid = str(panel.get("panel_id") or "?")
    for item in panel.get("dialogue") or []:
        if isinstance(item, Mapping):
            text = str(item.get("text_target") or item.get("text") or "").strip()
            speaker = str(item.get("speaker") or "")
        else:
            text, speaker = str(item or "").strip(), ""
        if text:
            out.append({"panel": pid, "kind": "dialogue", "speaker": speaker, "text": text})
    narration = str(panel.get("narration_target") or panel.get("narration") or "").strip()
    if narration:
        out.append({"panel": pid, "kind": "narration", "speaker": "旁白", "text": narration})
    return out


def shingles(text: str, n: int = 2) -> Set[str]:
    clean = _NOISE_RE.sub("", str(text or ""))
    if len(clean) < n:
        return {clean} if clean else set()
    return {clean[i:i + n] for i in range(len(clean) - n + 1)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0


def redundant_pairs(rows: List[Mapping[str, str]], threshold: float = PAIR_SIM_WARN,
                    min_chars: int = MIN_TEXT_CHARS) -> List[Dict[str, Any]]:
    """文本行两两相似度；只比够长的行，避免「什么？」类短句误报。纯函数·可测。"""
    usable = [(row, shingles(row.get("text") or "")) for row in rows
              if len(_NOISE_RE.sub("", str(row.get("text") or ""))) >= min_chars]
    out: List[Dict[str, Any]] = []
    for i in range(len(usable)):
        for j in range(i + 1, len(usable)):
            if usable[i][0].get("panel") == usable[j][0].get("panel"):
                continue  # 同格内台词-旁白呼应是合法手法，不罚
            sim = jaccard(usable[i][1], usable[j][1])
            if sim >= threshold:
                a, b = usable[i][0], usable[j][0]
                out.append({
                    "panels": [a.get("panel"), b.get("panel")],
                    "similarity": round(sim, 3),
                    "texts": [str(a.get("text"))[:60], str(b.get("text"))[:60]],
                })
    return out


def repeated_fact_mentions(rows: List[Mapping[str, str]], *,
                           ngram_len: int = FACT_NGRAM_LEN,
                           min_panels: int = FACT_MIN_PANELS,
                           exclude_names: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """同一事实短语在 ≥min_panels 个不同格复现。角色名/专名天然复现，从统计剔除。纯函数·可测。"""
    names = set(exclude_names or set()) | {str(r.get("speaker") or "") for r in rows}
    gram_panels: Dict[str, Set[str]] = {}
    for row in rows:
        clean = _NOISE_RE.sub("", str(row.get("text") or ""))
        pid = str(row.get("panel") or "?")
        seen: Set[str] = set()
        for i in range(max(0, len(clean) - ngram_len + 1)):
            gram = clean[i:i + ngram_len]
            if gram in seen or any(gram in name for name in names if name):
                continue
            seen.add(gram)
            gram_panels.setdefault(gram, set()).add(pid)
    hits = {g: sorted(p) for g, p in gram_panels.items() if len(p) >= min_panels}
    out: List[Dict[str, Any]] = []
    for gram in sorted(hits, key=lambda g: (-len(hits[g]), g)):
        if any((gram in prev["phrase"] or prev["phrase"] in gram)
               and set(prev["panels"]) == set(hits[gram]) for prev in out):
            continue
        out.append({"phrase": gram, "panels": hits[gram]})
    return out[:8]


def narration_stats(panels: List[Mapping[str, Any]]) -> Tuple[int, int]:
    """(有旁白的格数, 有任何文本的格数)。纯函数·可测。"""
    narr = texty = 0
    for panel in panels:
        rows = panel_texts(panel)
        if not rows:
            continue
        texty += 1
        if all(r["kind"] == "narration" for r in rows):
            narr += 1
    return narr, texty


def _lens_class(panel: Mapping[str, Any]) -> str:
    blob = " ".join(str(panel.get(k) or "") for k in ("art_notes", "description"))
    m = _LENS_CLASS_RE.search(blob)
    return m.group(0).upper() if m else ""


def repeated_compositions(panels: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """(场景锚, 出镜角色, 景别档) 相同的格分组 ≥2 = 计划层构图重复候选。
    景别未标注不参与（未标注归 visual_contract/art_notes 契约管，这里不重复罚）。纯函数·可测。"""
    groups: Dict[Tuple[str, Tuple[str, ...], str], List[str]] = {}
    for panel in panels:
        lens = _lens_class(panel)
        if not lens:
            continue
        loc = str(panel.get("scene_anchor_id") or panel.get("location") or "").strip()
        chars = tuple(sorted(str(c) for c in (panel.get("characters") or [])))
        if not loc and not chars:
            continue
        groups.setdefault((loc, chars, lens), []).append(str(panel.get("panel_id") or "?"))
    out = []
    for (loc, chars, lens), ids in sorted(groups.items()):
        if len(ids) >= 2:
            out.append({"panels": ids, "scene": loc, "characters": list(chars), "lens": lens})
    return out


def build_report(root: Path, chapter: str) -> Dict[str, Any]:
    panels = load_panels(root, chapter)
    rows: List[Dict[str, str]] = []
    char_names: Set[str] = set()
    for panel in panels:
        rows.extend(panel_texts(panel))
        char_names.update(str(c) for c in (panel.get("characters") or []))
    pairs = redundant_pairs(rows)
    facts = repeated_fact_mentions(rows, exclude_names=char_names)
    comps = repeated_compositions(panels)
    narr_panels, texty_panels = narration_stats(panels)
    narr_ratio = (narr_panels / texty_panels) if texty_panels else 0.0
    findings: List[Dict[str, Any]] = []
    if texty_panels >= 8 and narr_ratio > NARRATION_RATIO_WARN:
        findings.append({
            "severity": "warn", "code": "narration_heavy_chapter",
            "message": f"本话 {narr_panels}/{texty_panels} 个有文本格是纯旁白（{narr_ratio:.0%}>"
                       f"{NARRATION_RATIO_WARN:.0%}）——信息压缩靠旁白硬转=没画面化的流水账；"
                       "条漫铁律是能画不说：把交代改成画面/对白/道具特写，旁白只留画面外增量。",
        })
    for pair in pairs:
        sev = "block" if pair["similarity"] >= STRICT_SIM else "warn"
        findings.append({
            "severity": sev, "code": "redundant_text_pair",
            "message": f"{pair['panels'][0]} 与 {pair['panels'][1]} 文本相似度 {pair['similarity']:.0%}"
                       f"（『{pair['texts'][0]}』≈『{pair['texts'][1]}』）——同义反复，合并或删其一。",
        })
    for fact in facts:
        findings.append({
            "severity": "warn", "code": "repeated_fact_mention",
            "message": f"短语『{fact['phrase']}』在 {'/'.join(fact['panels'])} 复现 "
                       f"{len(fact['panels'])} 格——同一信息反复告知读者即冗余；只留首次落地处。",
        })
    for comp in comps:
        findings.append({
            "severity": "warn", "code": "repeated_composition_plan",
            "message": f"{'、'.join(comp['panels'])} 计划了相同的 (场景={comp['scene'][:20]}, "
                       f"角色={'/'.join(comp['characters']) or '无'}, 景别={comp['lens']})——"
                       "一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。",
        })
    return {
        "kind": KIND, "version": VERSION, "chapter": chapter, "generated_at": now_iso(),
        "thresholds": {"pair_sim_warn": PAIR_SIM_WARN, "strict_sim": STRICT_SIM,
                       "narration_ratio_warn": NARRATION_RATIO_WARN,
                       "provenance": "internal-heuristic·confidence=low·2026-07，误报校准后再议升硬闸"},
        "summary": {
            "panels": len(panels),
            "text_rows": len(rows),
            "redundant_pairs": len(pairs),
            "repeated_fact_phrases": len(facts),
            "repeated_composition_groups": len(comps),
            "narration_only_panels": narr_panels,
            "texty_panels": texty_panels,
            "narration_ratio": round(narr_ratio, 3),
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
        },
        "redundant_pairs": pairs,
        "repeated_fact_mentions": facts,
        "repeated_compositions": comps,
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        f"# 话内冗余机检 · {report.get('chapter')}",
        "",
        f"- 格 {s.get('panels')} · 文本行 {s.get('text_rows')} · 同义反复对 {s.get('redundant_pairs')}"
        f" · 事实复现 {s.get('repeated_fact_phrases')} · 构图重复组 {s.get('repeated_composition_groups')}"
        f" · 纯旁白格占比 {s.get('narration_ratio')}",
        "",
    ]
    for f in report.get("findings") or []:
        icon = "⛔" if f["severity"] == "block" else "⚠️"
        lines.append(f"- {icon} `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 未检出话内冗余/构图重复")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter")
    ap.add_argument("--write", action="store_true", help="写 生产数据/comic_redundancy_audit_<话>.json/md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="高置信命中（相似度≥STRICT_SIM）exit 1")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    chapter = normalize_chapter(ns.chapter)
    report = build_report(root, chapter)
    if ns.write:
        out = root / "生产数据"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"comic_redundancy_audit_{chapter}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / f"comic_redundancy_audit_{chapter}.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    if ns.strict and report["summary"]["block"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
