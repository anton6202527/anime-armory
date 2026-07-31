#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告分镜**视觉多样性 / 构图重复**机检（advisory·出图前·编剧/分镜轴）。

ad 的一致性套件（product_qc / asset_drift_report / reference_planner）全是在**保持资产一致**
（同一产品/logo/品牌色跨镜零漂移），没有任何东西查**镜头设计是否重复单调**——同一景别机位反复、
整片一个场景、两镜画面描述几乎一样。本脚本把"构图重复/景别单调/静态长镜"做成广告线自己的
**视觉不重复**机检。

**广告口径必须收着报**：
  ① 广告很短（6–30s，常 4–10 镜），"连续 5 镜同景别"这类阈值几乎用不上——只查**构图/描述重复对**
     和**长片才成立的单调**。
  ② 广告里**有意重复是常态**：产品特写 beauty shot、片尾 endcard/logo/CTA、slogan 板会刻意反复出现
     以提升 recall——这些**豁免**，绝不报为冗余（对齐 `copy_quality_audit` 把品牌重复豁免的思路）。
  ③ 单场景广告（一镜到底 demo / 单产品白底）本就合法——场景单调只 info、不 warn。

全 advisory：`summary.block` 恒 0（Creative heuristics stay advisory，见 ad-craft/gate.py），
gate 只把它当 warn/info 抬进报告，永不硬挡付费。

用法：
    python3 shot_variety_audit.py <作品根> [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

VERSION = 1
KIND = "ad_shot_variety_audit"
REPORT_REL = os.path.join("生产数据", "ad_shot_variety_audit.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")

# ── 阈值（内部启发式·env 可标定·confidence=low） ───────────────────────────────
# 画面描述 char-2gram Jaccard（与 copy_quality 同口径 0.6；中文短句 0.6≈大半重合）。
DESC_SIM_WARN = float(os.environ.get("AD_SHOTVAR_DESC_SIM", "0.6"))
DESC_MIN_CHARS = int(os.environ.get("AD_SHOTVAR_DESC_MIN_CHARS", "6"))
# 场景单调 / 景别单调 只在片子够长时才成立（短广告单场景合法）。
MIN_SHOTS_FOR_MONOTONY = int(os.environ.get("AD_SHOTVAR_MIN_SHOTS", "5"))
SCENE_MONO_FRAC = float(os.environ.get("AD_SHOTVAR_SCENE_FRAC", "0.85"))
# 再钩间隔（业界留存口径：≥30s 信息流广告约每 15-20s 需一个再钩/转折/揭晓，防中段划走）。
# 只对总时长 ≥ REHOOK_MIN_TOTAL 的长广告生效；短广告一个开场钩即可（开场钩归 ad-score hook 维度管）。
REHOOK_MIN_TOTAL = float(os.environ.get("AD_SHOTVAR_REHOOK_MIN_TOTAL", "20"))
REHOOK_GAP_WARN = float(os.environ.get("AD_SHOTVAR_REHOOK_GAP", "20"))
NGRAM = 2
PROVENANCE = "internal-heuristic·confidence=low"

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】]+")
# 豁免镜（有意重复/hold 的结构位）：片尾板、logo/CTA/slogan 墙、产品 beauty/特写展示。
_EXEMPT_RE = re.compile(
    r"片尾|尾板|end.?card|endcard|收尾|logo|CTA|slogan|口号|品牌板|"
    r"产品特写|产品展示|产品beauty|beauty.?shot|hero.?shot|包装展示|卖点板|价格板|二维码|下单",
    re.IGNORECASE)
# 明确的静止/hold 意图（豁免"静态"类判断，虽然本脚本目前不单独判静态长镜）。
_HOLD_RE = re.compile(r"固定|静止|定格|hold|freeze|保持", re.IGNORECASE)
# 再钩标记（半确定性关键词初筛，与 ad-score hook 口径同族·本线自包含）：转折/揭晓/对比/悬念等。
_REHOOK_RE = re.compile(
    r"钩子|hook|悬念|冲突|痛点|反转|转折|提问|对比|反差|揭晓|揭秘|真相|结果|竟然|居然|"
    r"挑战|测试|实测|before|after|证言|见证|数字冲击|倒计时",
    re.IGNORECASE)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, shots: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    """ad gate 消费 `msg` 键（见 ad-craft/gate.py:52）。附 shots 便于定位，不影响 gate。"""
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    if shots:
        out["shots"] = list(shots)
    return out


def clean(text: str) -> str:
    return _NOISE_RE.sub("", str(text or ""))


def shingles(text: str, n: int = NGRAM) -> Set[str]:
    """去噪后的 char n-gram 集合（与本线 copy_quality 同法·本线自包含）。"""
    c = clean(text)
    if len(c) < n:
        return {c} if c else set()
    return {c[i:i + n] for i in range(len(c) - n + 1)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").strip().lower())


# ── storyboard 解析（字段容忍：广告 storyboard schema 较薄） ──────────────────────

def load_storyboard(root: Path) -> Optional[dict]:
    path = root / STORYBOARD_REL
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def iter_shots(storyboard: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = storyboard.get("shots") or storyboard.get("clips") or storyboard.get("镜头") or []
    return [r for r in rows if isinstance(r, dict)]


def shot_id(shot: Mapping[str, Any], idx: int) -> str:
    return str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"镜头{idx + 1}")


def shot_scene(shot: Mapping[str, Any]) -> str:
    return _norm(shot.get("scene") or shot.get("场景") or shot.get("location") or shot.get("location_id"))


def shot_framing(shot: Mapping[str, Any]) -> str:
    return _norm(shot.get("景别") or shot.get("shot_size") or shot.get("shot_scale") or shot.get("framing"))


def shot_kind(shot: Mapping[str, Any]) -> str:
    return _norm(shot.get("shot_type"))


def shot_desc(shot: Mapping[str, Any]) -> str:
    for key in ("shot", "frame", "画面", "主体动作", "description", "desc", "visual"):
        val = shot.get(key)
        if val:
            return str(val)
    return ""


def is_exempt(shot: Mapping[str, Any]) -> bool:
    """有意重复/结构位镜（片尾/logo/CTA/产品 beauty/价格板…）——不参与重复判定。"""
    blob = " ".join(str(shot.get(k) or "") for k in
                    ("shot_type", "scene", "场景", "shot", "frame", "画面", "section", "role", "purpose"))
    if shot.get("endcard") or shot.get("is_endcard") or shot.get("is_hero") or shot.get("hero_product"):
        return True
    return bool(_EXEMPT_RE.search(blob))


# ── 信号 ─────────────────────────────────────────────────────────────────────

def audit_duplicate_composition(shots: List[Tuple[str, Dict[str, Any]]], findings: List[Dict[str, Any]]) -> int:
    """非豁免镜共享同一 (景别,场景,shot_type) 签名 ≥2 → 构图重复。"""
    groups: Dict[tuple, List[str]] = {}
    for sid, shot in shots:
        if is_exempt(shot):
            continue
        sig = (shot_framing(shot), shot_scene(shot), shot_kind(shot))
        if not any(sig):  # 三要素全空：分镜没写视觉字段，不臆造重复
            continue
        groups.setdefault(sig, []).append(sid)
    hits = 0
    for sig, ids in sorted(groups.items()):
        if len(ids) < 2:
            continue
        framing, scene, kind = sig
        combo = "、".join(x for x in (framing, scene, kind) if x) or "空构图"
        findings.append(finding("warn", "duplicate_shot_composition",
                                f"{'、'.join(ids)} 计划了相同构图（{combo}）——广告镜位金贵，"
                                "给其中几个换景别/机位/场景，别让同一画面反复占秒（产品 beauty/片尾板已豁免）",
                                ids))
        hits += 1
    return hits


def audit_duplicate_description(shots: List[Tuple[str, Dict[str, Any]]], findings: List[Dict[str, Any]]) -> int:
    """非豁免镜画面描述近重复（char-2gram Jaccard≥0.6）——分镜没结构字段时也能抓视觉冗余。"""
    items = [(sid, shot_desc(shot), shingles(shot_desc(shot)))
             for sid, shot in shots
             if not is_exempt(shot) and len(clean(shot_desc(shot))) >= DESC_MIN_CHARS]
    hits = 0
    reported: Set[frozenset] = set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            sim = jaccard(items[i][2], items[j][2])
            if sim >= DESC_SIM_WARN:
                key = frozenset((items[i][0], items[j][0]))
                if key in reported:
                    continue
                reported.add(key)
                findings.append(finding("warn", "duplicate_shot_description",
                                        f"{items[i][0]} 与 {items[j][0]} 画面描述相似度 {sim:.0%}"
                                        f"（『{items[i][1][:18]}』≈『{items[j][1][:18]}』）——两镜视觉几乎一样，"
                                        "合并或换个角度/景别拍",
                                        [items[i][0], items[j][0]]))
                hits += 1
    return hits


def audit_scene_monotony(shots: List[Tuple[str, Dict[str, Any]]], findings: List[Dict[str, Any]]) -> int:
    """长片里绝大多数镜同一场景 → info（短广告单场景合法，故只提示）。"""
    scenes = [shot_scene(shot) for _sid, shot in shots if shot_scene(shot)]
    if len(shots) < MIN_SHOTS_FOR_MONOTONY or not scenes:
        return 0
    from collections import Counter
    top, n = Counter(scenes).most_common(1)[0]
    if len(set(scenes)) > 1 and n / len(shots) >= SCENE_MONO_FRAC:
        findings.append(finding("info", "scene_monotony",
                                f"{len(shots)} 镜里 {n} 镜在同一场景『{top}』——若非刻意的单场景创意，"
                                "插一个不同空间/产品使用场景换气，广告更抓人（advisory）"))
        return 1
    return 0


def audit_framing_variety(shots: List[Tuple[str, Dict[str, Any]]], findings: List[Dict[str, Any]]) -> int:
    """长片里所有非豁免镜只有一种景别 → info（仅当分镜真写了景别字段才判）。"""
    framings = [shot_framing(shot) for _sid, shot in shots
                if not is_exempt(shot) and shot_framing(shot)]
    if len(framings) < MIN_SHOTS_FOR_MONOTONY:
        return 0
    if len(set(framings)) == 1:
        findings.append(finding("info", "framing_variety_low",
                                f"{len(framings)} 个非豁免镜全是同一景别（{framings[0]}）——"
                                "远/中/近切换能明显提节奏，考虑加景别层次（advisory）"))
        return 1
    return 0


def _shot_seconds(shot: Mapping[str, Any]) -> Optional[float]:
    for key in ("duration", "时长", "duration_sec", "seconds"):
        if shot.get(key) is not None:
            try:
                return float(re.sub(r"[^\d.]", "", str(shot.get(key))) or 0) or None
            except ValueError:
                return None
    return None


def _is_rehook(shot: Mapping[str, Any]) -> bool:
    blob = " ".join(str(shot.get(k) or "") for k in
                    ("shot", "frame", "画面", "主体动作", "description", "desc", "visual",
                     "section", "role", "purpose", "vo", "voiceover", "台词"))
    return bool(_REHOOK_RE.search(blob))


def audit_rehook_gap(shots: List[Tuple[str, Dict[str, Any]]], findings: List[Dict[str, Any]]) -> int:
    """≥20s 长广告的再钩间隔：连续 >20s 没有任何转折/揭晓/对比类节拍 → warn（业界留存口径：
    信息流长广告约每 15-20s 需一个再钩防中段划走；15/6s 短广告一个开场钩就够，不判）。
    时长字段缺失过半时不判（insufficient data，不臆造节奏问题）。"""
    timed = [(sid, shot, _shot_seconds(shot)) for sid, shot in shots]
    known = [t for _sid, _s, t in timed if t]
    if len(known) < max(1, len(timed) // 2 + 1):
        return 0
    total = sum(known)
    if total < REHOOK_MIN_TOTAL:
        return 0
    elapsed = 0.0
    last_hook_end = 0.0
    worst_gap, worst_span = 0.0, ("", "")
    span_start_id = timed[0][0] if timed else ""
    for sid, shot, secs in timed:
        start = elapsed
        elapsed += secs or 0.0
        if _is_rehook(shot):
            gap = start - last_hook_end
            if gap > worst_gap:
                worst_gap, worst_span = gap, (span_start_id, sid)
            last_hook_end = elapsed
            span_start_id = sid
    tail_gap = elapsed - last_hook_end
    if tail_gap > worst_gap:
        worst_gap, worst_span = tail_gap, (span_start_id, timed[-1][0] if timed else "")
    if worst_gap > REHOOK_GAP_WARN:
        findings.append(finding("warn", "rehook_gap",
                                f"总长 {total:.0f}s 的广告里，{worst_span[0]}→{worst_span[1]} 之间约 {worst_gap:.0f}s "
                                f"没有任何再钩节拍（转折/揭晓/对比/证言…）——信息流长广告约每 {REHOOK_GAP_WARN:.0f}s "
                                "要给观众一个继续看的理由，否则中段划走（advisory·关键词初筛，节奏好坏仍需人判）",
                                [worst_span[0], worst_span[1]]))
        return 1
    return 0


def build(root: Path) -> Dict[str, Any]:
    """契约形状（findings 用 `msg` 键，ad gate 可直接消费）：

        {"schema_version":1,"kind":"ad_shot_variety_audit","available":bool,
         "summary":{"block":0,"warn","info"},"findings":[{"severity","code","msg"}]}

    `summary.block` 恒为 0——advisory 纪律。"""
    root = Path(root)
    storyboard = load_storyboard(root)
    findings: List[Dict[str, Any]] = []
    available = isinstance(storyboard, dict)
    shots: List[Tuple[str, Dict[str, Any]]] = []

    if not available:
        findings.append(finding("warn", "storyboard_missing",
                                "缺 脚本/storyboard.json——没有分镜可审视觉多样性（insufficient_data，"
                                "不代表分镜没问题）。配音后跑 ad-script 分镜 pass 产出 storyboard.json。"))
    else:
        raw = iter_shots(storyboard)
        shots = [(shot_id(s, i), s) for i, s in enumerate(raw)]
        if not shots:
            findings.append(finding("warn", "storyboard_empty",
                                    "storyboard.json 存在但没有 shots——分镜还没落档。"))
        else:
            audit_duplicate_composition(shots, findings)
            audit_duplicate_description(shots, findings)
            audit_scene_monotony(shots, findings)
            audit_framing_variety(shots, findings)
            audit_rehook_gap(shots, findings)

    return {
        "schema_version": VERSION,
        "kind": KIND,
        "available": available,
        "project_root": str(root),
        "generated_at": now_iso(),
        "thresholds": {
            "desc_sim_warn": DESC_SIM_WARN, "desc_min_chars": DESC_MIN_CHARS,
            "min_shots_for_monotony": MIN_SHOTS_FOR_MONOTONY, "scene_mono_frac": SCENE_MONO_FRAC,
            "rehook_min_total": REHOOK_MIN_TOTAL, "rehook_gap_warn": REHOOK_GAP_WARN,
            "ngram": NGRAM, "provenance": PROVENANCE,
            "note": "advisory：本检永不产 block。产品 beauty/片尾/logo/CTA 板等有意重复镜已豁免；"
                    "短广告单场景合法，故场景/景别单调只 info。",
        },
        "inputs": {
            "shots": len(shots),
            "exempt_shots": sum(1 for _sid, s in shots if is_exempt(s)),
        },
        "summary": {
            "block": 0,  # advisory：恒 0，不是「这次刚好没有」
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    i = report.get("inputs") or {}
    lines = ["# 广告分镜视觉多样性机检", ""]
    if not report.get("available"):
        lines += ["- ⚠️ 未找到 `脚本/storyboard.json`（available=false·降级为建议，不阻断）", ""]
    lines += [f"- 分镜 {i.get('shots')} 镜 · 豁免（片尾/logo/产品beauty…）{i.get('exempt_shots')} 镜",
              f"- warn {s.get('warn')} · info {s.get('info')}（advisory：本检不产 block）", ""]
    icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 未检出构图重复/画面复读/场景景别单调（好不好看仍需人判）")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    """原子写（tmp + os.replace）：报告被 gate/review 并发读时不会读到半截 JSON。"""
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    for target, payload in ((path, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                            (path.with_suffix(".md"), render_markdown(report))):
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="作品根")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ 同名 .md·原子写）")
    ap.add_argument("--json", action="store_true", help="打印 JSON 而非 markdown")
    ap.add_argument("--strict", action="store_true",
                    help="warn>0 时 exit 1（本检 advisory·恒无 block，--strict 只影响退出码）")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = build(root)
    if ns.write:
        write_report(root, report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
