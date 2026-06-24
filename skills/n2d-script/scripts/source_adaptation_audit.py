#!/usr/bin/env python3
"""Audit source raw coverage in n2d script adaptation.

This is a cheap deterministic guard before image prompt generation. It checks
that high-salience source elements in `raw.txt` did not disappear when the
episode was adapted into `voiceover.txt` / storyboard.

Usage:
  python3 source_adaptation_audit.py <作品根> 第N集 [--strict] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

EVENT_RE = re.compile(
    r"(死|杀|伤|毒|醒|穿越|重生|系统|提示|升级|突破|发现|真相|背叛|逼|威胁|救|逃|"
    r"打|跪|反击|揭|暴露|秘密|证据|线索|婚|退婚|觉醒|血脉|法宝|灵力|境界|凶手|"
    r"告白|心动|误会|吃醋|分手|复合)"
)
BRACKET_RE = re.compile(r"(【[^】]{2,40}】|《[^》]{2,40}》)")
TITLE_RE = re.compile(
    r"([\u4e00-\u9fff]{1,4}(?:娘娘|王爷|师尊|陛下|公主|太子|小姐|少爷|夫人|长老|"
    r"师兄|师姐|宗主|皇后|贵妃|将军|侍卫|掌门))"
)
CJK_RE = re.compile(r"[\u4e00-\u9fff]+")

STOP_BIGRAMS = {
    "这个", "那个", "他们", "她们", "我们", "你们", "自己", "没有", "不是", "只是", "已经",
    "突然", "然后", "这里", "那里", "一个", "一种", "什么", "怎么", "还是", "因为", "所以",
    "但是", "如果", "时候", "眼前", "身后", "声音", "众人", "所有", "开始", "继续",
}

SCENE_FUNCTIONS: List[Tuple[str, str, re.Pattern[str], str]] = [
    ("motivation", "角色动机", re.compile(r"(为了|想要|必须|誓要|不能让|保护|复仇|活下去|查清|证明)"), "warn"),
    ("conflict_cause", "冲突原因", re.compile(r"(因为|逼|威胁|陷害|背叛|下毒|抢|杀|封锁|通缉)"), "warn"),
    ("setup", "伏笔/线索", re.compile(r"(伏笔|悬念|线索|秘密|信物|玉佩|令牌|印记|不对劲|另有隐情)"), "info"),
    ("payoff", "兑现/爽点", re.compile(r"(反击|打脸|夺回|突破|升级|赢|救出|揭穿|真相|兑现)"), "warn"),
    ("reversal", "反转", re.compile(r"(原来|竟然|没想到|反而|却|逆转|翻盘)"), "warn"),
    ("relationship_shift", "关系变化", re.compile(r"(信任|背叛|心动|误会|和解|决裂|告白|退婚|结盟|仇人)"), "warn"),
    ("world_rule", "世界/系统规则", re.compile(r"(系统|面板|规则|等级|境界|任务|奖励|代价|禁忌)"), "info"),
    ("choice", "角色选择", re.compile(r"(决定|选择|答应|拒绝|放弃|留下|离开|救|杀|公开|隐瞒)"), "warn"),
    ("consequence", "后果/代价", re.compile(r"(因此|于是|代价|后果|失去|得到|暴露|触发|受伤|被抓|关系破裂)"), "warn"),
]


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def raw_path(root: str, ep: str) -> Path:
    return Path(root) / "脚本" / ep / "raw.txt"


def adaptation_paths(root: str, ep: str) -> List[Path]:
    base = Path(root) / "脚本" / ep
    return [
        base / "voiceover.txt",
        base / "分镜剧本.md",
        base / "故事板.md",
        base / "storyboard.json",
    ]


def adaptation_text(root: str, ep: str) -> Tuple[str, List[str]]:
    chunks: List[str] = []
    used: List[str] = []
    for path in adaptation_paths(root, ep):
        if path.exists():
            text = read_text(path)
            chunks.append(text)
            used.append(str(path))
    return "\n".join(chunks), used


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[。！？!?；;])\s*|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) >= 6]


def cjk_bigrams(text: str) -> Set[str]:
    chars = "".join(CJK_RE.findall(text))
    return {chars[i:i + 2] for i in range(max(0, len(chars) - 1)) if chars[i:i + 2] not in STOP_BIGRAMS}


def normalized_variants(token: str) -> Set[str]:
    token = token.strip()
    variants = {token}
    if token.startswith("【") and token.endswith("】"):
        variants.add(token[1:-1])
    if token.startswith("《") and token.endswith("》"):
        variants.add(token[1:-1])
    return {v for v in variants if v}


def present(token: str, text: str) -> bool:
    return any(v in text for v in normalized_variants(token))


def important_terms(raw: str) -> List[str]:
    seen: Set[str] = set()
    terms: List[str] = []
    for rx in (BRACKET_RE, TITLE_RE):
        for m in rx.finditer(raw):
            term = m.group(1).strip()
            if term and term not in seen:
                terms.append(term)
                seen.add(term)
    return terms


def key_event_sentences(raw: str, limit: int = 10) -> List[str]:
    candidates = [s for s in split_sentences(raw) if EVENT_RE.search(s)]
    # Prefer sentences containing explicit system/name/title/bracket markers,
    # then longer event-heavy sentences. This keeps the report small.
    def score(sentence: str) -> Tuple[int, int]:
        marker = 1 if (BRACKET_RE.search(sentence) or TITLE_RE.search(sentence)) else 0
        hits = len(EVENT_RE.findall(sentence))
        return (marker + hits, min(len(sentence), 160))
    return sorted(candidates, key=score, reverse=True)[:limit]


def scene_function_sentences(raw: str, limit: int = 12) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for sentence in split_sentences(raw):
        hits = [(code, label, severity) for code, label, rx, severity in SCENE_FUNCTIONS if rx.search(sentence)]
        if not hits:
            continue
        marker = 1 if (BRACKET_RE.search(sentence) or TITLE_RE.search(sentence)) else 0
        candidates.append({
            "sentence": sentence,
            "functions": [h[0] for h in hits],
            "labels": [h[1] for h in hits],
            "severity": "warn" if any(h[2] == "warn" for h in hits) else "info",
            "score": len(hits) + len(EVENT_RE.findall(sentence)) + marker,
        })
    return sorted(candidates, key=lambda row: (row["score"], min(len(row["sentence"]), 160)), reverse=True)[:limit]


def function_marker_present(functions: Sequence[str], adapted: str) -> bool:
    by_code = {code: rx for code, _label, rx, _severity in SCENE_FUNCTIONS}
    return any(by_code[code].search(adapted) for code in functions if code in by_code)


def sentence_coverage(sentence: str, adapted: str) -> float:
    grams = cjk_bigrams(sentence)
    if not grams:
        return 1.0
    adapted_grams = cjk_bigrams(adapted)
    return len(grams & adapted_grams) / len(grams)


def local_required_terms(sentence: str) -> List[str]:
    terms = []
    for term in important_terms(sentence):
        if term not in terms:
            terms.append(term)
    return terms


def add(findings: List[Dict[str, Any]], severity: str, code: str, message: str,
        evidence: Optional[Dict[str, Any]] = None) -> None:
    row: Dict[str, Any] = {"severity": severity, "code": code, "message": message}
    if evidence:
        row["evidence"] = evidence
    findings.append(row)


def audit(root: str, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    raw_file = raw_path(root, ep)
    findings: List[Dict[str, Any]] = []
    if not raw_file.exists():
        add(findings, "must", "missing_raw", f"缺 {raw_file}，无法核对源文覆盖。")
        return {"episode": ep, "ok": False, "stats": {}, "findings": findings}
    raw = read_text(raw_file)
    adapted, used_paths = adaptation_text(root, ep)
    if not adapted.strip():
        add(findings, "must", "missing_adaptation", f"{ep} 缺 voiceover/storyboard 改编产物，无法核对源文覆盖。")
        return {"episode": ep, "ok": False, "stats": {"raw_chars": len(raw)}, "findings": findings}

    terms = important_terms(raw)
    missing_terms = [t for t in terms if not present(t, adapted)]
    for term in missing_terms[:12]:
        sev = "warn"
        code = "source_term_missing"
        add(findings, sev, code, f"源文关键名词 `{term}` 未出现在 voiceover/storyboard；确认不是误删或需改写为等价表达。",
            {"term": term})

    event_sentences = key_event_sentences(raw)
    omitted_events = []
    for sentence in event_sentences:
        required = local_required_terms(sentence)
        if required and any(present(t, adapted) for t in required):
            continue
        cov = sentence_coverage(sentence, adapted)
        # Below 12% shared CJK bigrams means this event is probably absent, not
        # merely compressed. Keep this conservative to avoid punishing paraphrase.
        if cov < 0.12:
            omitted_events.append({"sentence": sentence[:120], "coverage": round(cov, 3), "required_terms": required})
    for item in omitted_events[:8]:
        add(findings, "warn", "source_event_maybe_omitted",
            "源文关键事件在改编稿中覆盖率极低；确认没有漏掉动机/伏笔/反转。",
            item)

    function_items = scene_function_sentences(raw)
    lost_functions = []
    for item in function_items:
        sentence = str(item["sentence"])
        required = local_required_terms(sentence)
        cov = sentence_coverage(sentence, adapted)
        has_required_term = bool(required and any(present(t, adapted) for t in required))
        has_same_function = function_marker_present(item["functions"], adapted)
        if cov < 0.10 and not has_required_term and not has_same_function:
            lost_functions.append({
                "sentence": sentence[:120],
                "functions": item["labels"],
                "coverage": round(cov, 3),
            })
    for item in lost_functions[:8]:
        sev = "warn" if any(label in {"角色动机", "冲突原因", "兑现/爽点", "反转", "关系变化", "角色选择", "后果/代价"}
                            for label in item["functions"]) else "info"
        add(findings, sev, "scene_function_maybe_lost",
            "源文场景功能在改编稿中覆盖很低；确认压缩没有删掉剧情功能。",
            item)

    raw_event_count = len(event_sentences)
    adapted_event_count = len(EVENT_RE.findall(adapted))
    if raw_event_count >= 2 and adapted_event_count == 0:
        add(findings, "warn", "adaptation_has_no_event_signals",
            "源文有多个关键事件信号，但改编稿没有检测到冲突/反转/系统/爽点类词，疑似改得过平。",
            {"raw_event_sentences": raw_event_count})

    stats = {
        "raw_chars": len(raw),
        "adaptation_chars": len(adapted),
        "adaptation_paths": used_paths,
        "important_terms": len(terms),
        "missing_terms": len(missing_terms),
        "key_event_sentences": raw_event_count,
        "omitted_event_sentences": len(omitted_events),
        "scene_function_sentences": len(function_items),
        "lost_scene_functions": len(lost_functions),
    }
    ok = not any(f["severity"] in {"must", "warn"} for f in findings)
    return {"episode": ep, "ok": ok, "stats": stats, "findings": findings}


def print_human(result: Dict[str, Any]) -> None:
    stats = result.get("stats") or {}
    print(f"# 源文改编覆盖校验 — {result.get('episode')}")
    print(
        f"raw={stats.get('raw_chars', 0)} chars  adapted={stats.get('adaptation_chars', 0)} chars  "
        f"terms_missing={stats.get('missing_terms', 0)}  events_omitted={stats.get('omitted_event_sentences', 0)}  "
        f"scene_functions_lost={stats.get('lost_scene_functions', 0)}"
    )
    findings = result.get("findings") or []
    if not findings:
        print("- PASS：未发现源文关键元素完全丢失。")
        return
    for row in findings:
        marker = {"must": "BLOCK", "warn": "WARN", "info": "INFO"}.get(row.get("severity"), "INFO")
        print(f"- {marker} [{row.get('code')}] {row.get('message')}")
        ev = row.get("evidence") or {}
        if ev.get("sentence"):
            print(f"  source: {ev['sentence']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d source-to-adaptation coverage audit")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    result = audit(ns.root.rstrip("/"), ep_label(ns.episode))
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    has_must = any(f["severity"] == "must" for f in result.get("findings") or [])
    has_warn = any(f["severity"] == "warn" for f in result.get("findings") or [])
    if ns.strict and (has_must or has_warn):
        return 1
    return 1 if has_must else 0


if __name__ == "__main__":
    raise SystemExit(main())
