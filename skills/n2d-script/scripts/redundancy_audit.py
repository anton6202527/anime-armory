#!/usr/bin/env python3
"""集内冗余机检（2026-07 实跑痛点回修）——台词同义反复 + 分镜构图重复的花钱前拦截。

实跑暴露的观感问题里，「成片情节冗余」「镜头重复」此前在机检层是盲区：
  - story_economy_audit 只查单 clip 时长预算，看不见「第3镜和第7镜旁白说的是同一件事」；
  - beat_audit --series 的桥段指纹是跨集粒度，对单集内部的重复完全无效；
  - storyboard/prompt/image 全线没有集内近重复镜头比对。
本脚本补两个纯文本检查（stdlib·零依赖·pre-money）：

① redundant_voiceover_pair：voiceover 行两两 char-2gram Jaccard ≥ 阈值 = 同义反复/信息重复。
② repeated_composition_plan：storyboard 里 (场景, 景别档集合, 出镜角色) 完全相同的 clip
   出现 ≥2 次 = 计划层面的镜头重复——出图前就该换景别/机位或合并。

口径诚实：阈值是内部启发式（confidence=low·env 可标定），默认 report-only（exit 0）；
`--strict` 只对高置信命中（相似度 ≥ STRICT_SIM）exit 1。先跑两部片校准误报再考虑升硬闸。

用法：
  cd skills/n2d-script/scripts
  python3 redundancy_audit.py <作品根> 第N集 [--write] [--json] [--strict]
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
KIND = "n2d_redundancy_audit"

# 相似度阈值（内部启发式·2026-07；char-2gram Jaccard 对中文短句 0.6 ≈ 大半内容重合）
PAIR_SIM_WARN = float(os.environ.get("N2D_REDUNDANCY_SIM_WARN", "0.6"))
STRICT_SIM = float(os.environ.get("N2D_REDUNDANCY_SIM_STRICT", "0.75"))
MIN_LINE_CHARS = int(os.environ.get("N2D_REDUNDANCY_MIN_CHARS", "8"))

_LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)(?:·[^\]]*)?\]\s*(.+?)\s*(?:[⚡💥🪝].*)?$")
_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】]+")
_LENS_CLASS_RE = re.compile(
    r"ECU|CU|MCU|MS|MLS|LS|WS|EWS|OTS|POV|特写|近景|中景|全景|远景|大远景|过肩|插入|insert",
    re.IGNORECASE,
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_voiceover_lines(path: Path) -> List[Dict[str, Any]]:
    """[镜头N·角色·情绪·速度] 文本  → [{shot, role, text}]。容错：无法解析的行跳过。"""
    out: List[Dict[str, Any]] = []
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        out.append({"shot": int(m.group(1)), "role": m.group(2).strip(), "text": m.group(3).strip()})
    return out


def shingles(text: str, n: int = 2) -> Set[str]:
    """去噪后的 char n-gram 集合。纯函数·可测。"""
    clean = _NOISE_RE.sub("", str(text or ""))
    if len(clean) < n:
        return {clean} if clean else set()
    return {clean[i:i + n] for i in range(len(clean) - n + 1)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0


def redundant_pairs(lines: List[Mapping[str, Any]], threshold: float = PAIR_SIM_WARN,
                    min_chars: int = MIN_LINE_CHARS) -> List[Dict[str, Any]]:
    """voiceover 行两两相似度；只比够长的行，避免「行。」「什么？」这类短句误报。纯函数·可测。"""
    rows = [(row, shingles(row.get("text") or "")) for row in lines
            if len(_NOISE_RE.sub("", str(row.get("text") or ""))) >= min_chars]
    out: List[Dict[str, Any]] = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            sim = jaccard(rows[i][1], rows[j][1])
            if sim >= threshold:
                a, b = rows[i][0], rows[j][0]
                out.append({
                    "shots": [a.get("shot"), b.get("shot")],
                    "roles": [a.get("role"), b.get("role")],
                    "similarity": round(sim, 3),
                    "texts": [str(a.get("text"))[:60], str(b.get("text"))[:60]],
                })
    return out


NARRATION_ROLES = ("旁白", "系统", "画外音", "narration", "voiceover")
NARRATION_RATIO_WARN = float(os.environ.get("N2D_NARRATION_RATIO_WARN", "0.5"))
FACT_NGRAM_LEN = int(os.environ.get("N2D_FACT_NGRAM_LEN", "4"))
FACT_MIN_LINES = int(os.environ.get("N2D_FACT_MIN_LINES", "3"))


def narration_ratio(lines: List[Mapping[str, Any]]) -> float:
    """旁白/系统/画外音占全部台词行的比例。纯函数·可测。"""
    if not lines:
        return 0.0
    hits = sum(1 for row in lines
               if any(tag in str(row.get("role") or "") for tag in NARRATION_ROLES))
    return hits / len(lines)


def repeated_fact_mentions(lines: List[Mapping[str, Any]], *,
                           ngram_len: int = FACT_NGRAM_LEN,
                           min_lines: int = FACT_MIN_LINES) -> List[Dict[str, Any]]:
    """同一事实短语在 ≥min_lines 行里复现（措辞不同的复述，Jaccard 抓不到）。纯函数·可测。

    实证：EP2「二十年道行」在镜头 3/4/8 说了三遍、「二十五(年)」在 19/23/25 三遍——
    观众三次听到同一信息=冗余。角色名天然复现，从统计中剔除。"""
    role_names = {str(row.get("role") or "") for row in lines}
    gram_lines: Dict[str, List[int]] = {}
    for row in lines:
        clean = _NOISE_RE.sub("", str(row.get("text") or ""))
        seen: Set[str] = set()
        for i in range(max(0, len(clean) - ngram_len + 1)):
            gram = clean[i:i + ngram_len]
            if gram in seen or any(gram in name for name in role_names):
                continue
            seen.add(gram)
            gram_lines.setdefault(gram, []).append(int(row.get("shot") or 0))
    hits = {g: shots for g, shots in gram_lines.items() if len(shots) >= min_lines}
    # 合并互相重叠的 n-gram（同一短语的滑窗片段），保留出现行集合相同里最长代表
    out: List[Dict[str, Any]] = []
    for gram in sorted(hits, key=lambda g: (-len(hits[g]), g)):
        if any(gram in prev["phrase"] or prev["phrase"] in gram for prev in out
               if set(prev["shots"]) == set(hits[gram])):
            continue
        out.append({"phrase": gram, "shots": hits[gram]})
    return out[:8]


def _clip_signature(clip: Mapping[str, Any]) -> Optional[Tuple[str, Tuple[str, ...], Tuple[str, ...]]]:
    loc = str(clip.get("location_id") or clip.get("scene") or "").strip()
    lenses: Set[str] = set()
    for shot in clip.get("shots") or []:
        if isinstance(shot, Mapping):
            m = _LENS_CLASS_RE.search(str(shot.get("lens") or ""))
            if m:
                lenses.add(m.group(0).upper())
    chars = tuple(sorted(str(c) for c in (clip.get("character_ids") or [])))
    if not loc and not lenses and not chars:
        return None
    return (loc, tuple(sorted(lenses)), chars)


def repeated_compositions(clips: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """(场景, 景别档集合, 出镜角色) 相同的 clip 分组；组 ≥2 即计划层镜头重复候选。纯函数·可测。

    景别集合为空（未标注）不参与——未标注该由 storyboard 契约管，这里不重复罚。"""
    groups: Dict[Tuple, List[str]] = {}
    for clip in clips:
        sig = _clip_signature(clip)
        if sig is None or not sig[1]:
            continue
        groups.setdefault(sig, []).append(str(clip.get("id") or "?"))
    out = []
    for sig, ids in sorted(groups.items()):
        if len(ids) >= 2:
            out.append({"clips": ids, "location": sig[0], "lenses": list(sig[1]), "characters": list(sig[2])})
    return out


def build_report(root: Path, ep: str) -> Dict[str, Any]:
    lines = parse_voiceover_lines(root / "脚本" / ep / "voiceover.txt")
    try:
        sb = json.loads((root / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
        clips = [c for c in (sb.get("clips") or []) if isinstance(c, Mapping)]
    except Exception:
        clips = []
    pairs = redundant_pairs(lines)
    comps = repeated_compositions(clips)
    facts = repeated_fact_mentions(lines)
    narr = narration_ratio(lines)
    findings: List[Dict[str, Any]] = []
    if narr > NARRATION_RATIO_WARN and len(lines) >= 10:
        findings.append({
            "severity": "warn", "code": "narration_heavy_episode",
            "message": f"整集旁白/系统/画外音占 {narr:.0%}（>{NARRATION_RATIO_WARN:.0%}）——解说压过表演，"
                       "观感即『流水账』。把可演的信息改成对白/动作/画面（旁白只留画面外增量），"
                       "小说式心理/环境描写外化或删除。",
        })
    for fact in facts:
        findings.append({
            "severity": "warn", "code": "repeated_fact_mention",
            "message": f"短语『{fact['phrase']}』在镜头 {'/'.join(str(s) for s in fact['shots'])} 复现 "
                       f"{len(fact['shots'])} 次——同一信息反复告知观众即冗余；只保留信息首次落地那一处，"
                       "其余改推进或删除。",
        })
    for pair in pairs:
        sev = "block" if pair["similarity"] >= STRICT_SIM else "warn"
        findings.append({
            "severity": sev, "code": "redundant_voiceover_pair",
            "message": f"镜头{pair['shots'][0]} 与 镜头{pair['shots'][1]} 台词相似度 {pair['similarity']:.0%}"
                       f"（『{pair['texts'][0]}』≈『{pair['texts'][1]}』）——同义反复/信息重复，"
                       "合并成一句或删其一（小说式重复不应带进成片）。",
        })
    for comp in comps:
        findings.append({
            "severity": "warn", "code": "repeated_composition_plan",
            "message": f"{'、'.join(comp['clips'])} 计划了相同的 (场景={comp['location'][:16]}, "
                       f"景别={'/'.join(comp['lenses'])}, 角色={'/'.join(comp['characters']) or '无'})——"
                       "出图前换景别/机位（特写-中景-全景轮换、插入镜、反应镜）或合并镜头，"
                       "否则成片会出现构图重复。",
        })
    return {
        "kind": KIND, "version": VERSION, "episode": ep, "generated_at": now_iso(),
        "thresholds": {"pair_sim_warn": PAIR_SIM_WARN, "strict_sim": STRICT_SIM,
                       "min_line_chars": MIN_LINE_CHARS,
                       "provenance": "internal-heuristic·confidence=low·2026-07，误报校准后再议升硬闸"},
        "summary": {
            "voiceover_lines": len(lines),
            "narration_ratio": round(narr, 3),
            "repeated_fact_phrases": len(facts),
            "redundant_pairs": len(pairs),
            "repeated_composition_groups": len(comps),
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
        },
        "redundant_pairs": pairs,
        "repeated_compositions": comps,
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        f"# 集内冗余机检 · {report.get('episode')}",
        "",
        f"- 台词行 {s.get('voiceover_lines')} · 同义反复对 {s.get('redundant_pairs')}"
        f" · 构图重复组 {s.get('repeated_composition_groups')}",
        "",
    ]
    for f in report.get("findings") or []:
        icon = "⛔" if f["severity"] == "block" else "⚠️"
        lines.append(f"- {icon} `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 未检出集内冗余/构图重复")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true", help="写 生产数据/redundancy_audit_<集>.json/md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="高置信命中（相似度≥STRICT_SIM）exit 1")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = build_report(root, ns.episode)
    if ns.write:
        out = root / "生产数据"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"redundancy_audit_{ns.episode}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / f"redundancy_audit_{ns.episode}.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    if ns.strict and report["summary"]["block"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
