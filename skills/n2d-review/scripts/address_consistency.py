#!/usr/bin/env python3
"""称谓/口头禅一致性门（剧本层·像素之外的「人设漂移」）——补 AI 改写最隐蔽的一类塌人设。

2026 实测：图/声都锁住了，**台词层的人设照样漂**——这是中文网文改漫特有的盲区：AI 改写/续写时
同一角色被称呼忽「师姐」忽「姐姐」忽「柳娘子」，自称忽「本宫」忽「我」，口头禅时有时无、甚至被
安到别人嘴里。观众对「称呼」「自称」「口头禅」极敏感，一处漂人设就塌。现产线无任何机检管这层。

词典：<作品根>/设定库/称谓表.json
  {"称谓": {"柳娘子": {"canonical":"柳姐姐","allowed":["柳姐姐","柳娘子","姐姐"],"forbidden":["柳妹妹","丫头"]}},
   "口头禅": {"小禾": ["奴婢该死","娘娘恕罪"]}}

判据（扫 voiceover.txt 逐行 [镜头·角色·情绪] 台词）：
  🔴 forbidden 称谓出现在任一台词    —— 用了明令禁用的称呼（铁错）。
  🟡 口头禅串属角色 A，却出现在角色 B 的台词 —— 口头禅被安错人（OOC 漂）。
  🟡 某角色 canonical 称谓全集未现、却出现其 allowed 变体 —— 正称被变体悄悄取代（疑似漂）。
  报告：逐角色 allowed 称谓本集使用分布（让"忽 A 忽 B"一眼可见）+ 口头禅使用次数（突然消失可见）。

诚实边界：纯字符串匹配、无 NER/指代消解——不知道台词在称呼**谁**，故只查「禁用称谓现身」「口头禅
错位」「正称缺席」这类**不依赖听者**的硬信号，命中作"可疑→人读上下文判"。无词典→优雅跳过（提示
据 global_style 术语表/人设起一份）。纯函数（build_index/scan_line/usage）无依赖、带 pytest。

用法：python3 address_consistency.py <作品根> 第N集 [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple


# ---------- 纯函数（无依赖 · pytest 覆盖） ----------

def build_index(registry: dict) -> dict:
    """称谓表 → 索引：{forbidden:{词:owner}, allowed:{owner:[词]}, canonical:{owner:词},
    catchphrase:{词:owner}}。纯函数·可测。"""
    称谓 = (registry or {}).get("称谓", {}) or {}
    口头禅 = (registry or {}).get("口头禅", {}) or {}
    idx: dict = {"forbidden": {}, "allowed": {}, "canonical": {}, "catchphrase": {}}
    for owner, spec in 称谓.items():
        if not isinstance(spec, dict):
            continue
        idx["allowed"][owner] = [str(x).strip() for x in spec.get("allowed", []) if str(x).strip()]
        if spec.get("canonical"):
            idx["canonical"][owner] = str(spec["canonical"]).strip()
        for w in spec.get("forbidden", []):
            w = str(w).strip()
            if w:
                idx["forbidden"][w] = owner
    for owner, phrases in 口头禅.items():
        for ph in (phrases or []):
            ph = str(ph).strip()
            if ph:
                idx["catchphrase"][ph] = owner
    return idx


def scan_line(speaker: str, text: str, idx: dict) -> List[dict]:
    """单行台词 → findings。禁用称谓出现=block；他角色口头禅被本说话人念出=warn。纯函数·可测。"""
    out: List[dict] = []
    for word, owner in idx.get("forbidden", {}).items():
        if word and word in text:
            out.append({"verdict": "block", "kind": "forbidden_address", "word": word,
                        "owner": owner, "speaker": speaker,
                        "message": f"禁用称谓「{word}」（属{owner}）出现在台词"})
    for ph, owner in idx.get("catchphrase", {}).items():
        if ph and ph in text and speaker and owner and speaker != owner:
            out.append({"verdict": "warn", "kind": "catchphrase_misassigned", "word": ph,
                        "owner": owner, "speaker": speaker,
                        "message": f"口头禅「{ph}」属{owner}，却由{speaker}念出（疑口头禅错位/OOC）"})
    return out


def appellation_usage(lines: List[Tuple[str, str]], idx: dict) -> Dict[str, Dict[str, int]]:
    """逐角色 allowed 称谓在全集台词中的出现次数 → {owner:{词:count}}。纯函数·可测。"""
    usage: Dict[str, Dict[str, int]] = {}
    full = "\n".join(t for _, t in lines)
    for owner, words in idx.get("allowed", {}).items():
        counts = {w: len(re.findall(re.escape(w), full)) for w in words}
        usage[owner] = counts
    return usage


def canonical_dropouts(usage: Dict[str, Dict[str, int]], idx: dict) -> List[dict]:
    """正称(canonical)全集 0 次、却有 allowed 变体出现 → 疑「正称被变体悄悄取代」。纯函数·可测。"""
    out: List[dict] = []
    for owner, canon in idx.get("canonical", {}).items():
        counts = usage.get(owner, {})
        if not counts:
            continue
        canon_n = counts.get(canon, 0)
        variant_n = sum(c for w, c in counts.items() if w != canon)
        if canon_n == 0 and variant_n > 0:
            variants = sorted([w for w, c in counts.items() if w != canon and c > 0])
            out.append({"verdict": "warn", "kind": "canonical_absent", "owner": owner,
                        "canonical": canon, "variants_seen": variants,
                        "message": f"{owner} 正称「{canon}」本集未现，只见变体 {('、'.join(variants))}（疑称谓漂）"})
    return out


# ---------- IO ----------

def load_registry(root: str) -> dict:
    path = os.path.join(root, "设定库", "称谓表.json")
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}


_LINE_RE = re.compile(r"\[(?:镜头[^·]*)·([^·]+)·[^\]]*\]\s*(.+)")


def parse_voiceover(root: str, ep: str) -> List[Tuple[str, str]]:
    """voiceover.txt → [(说话人, 台词)]。"""
    p = os.path.join(root, "脚本", ep, "voiceover.txt")
    lines: List[Tuple[str, str]] = []
    try:
        for ln in open(p, encoding="utf-8"):
            m = _LINE_RE.match(ln.strip())
            if m:
                lines.append((m.group(1).strip(), m.group(2).strip()))
    except Exception:
        pass
    return lines


def analyze(root: str, ep: str) -> dict:
    reg = load_registry(root)
    idx = build_index(reg)
    has_reg = bool(idx["allowed"] or idx["forbidden"] or idx["catchphrase"])
    res: dict = {"available": has_reg, "findings": [], "usage": {}, "notes": []}
    if not has_reg:
        res["notes"].append("无 设定库/称谓表.json——称呼/自称/口头禅漂移无防护。"
                            "建议据人设起一份（每角色 canonical/allowed/forbidden + 口头禅）。")
        return res
    lines = parse_voiceover(root, ep)
    if not lines:
        res["notes"].append(f"缺/空 脚本/{ep}/voiceover.txt——只载词典，未扫本集台词。")
        return res
    findings: List[dict] = []
    for speaker, text in lines:
        findings.extend(scan_line(speaker, text, idx))
    usage = appellation_usage(lines, idx)
    findings.extend(canonical_dropouts(usage, idx))
    res["findings"] = findings
    res["usage"] = usage
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 称谓/口头禅一致性门（剧本层）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    nb = 0
    icon = {"block": "⛔", "warn": "⚠️"}
    for f in res["findings"]:
        if f["verdict"] == "block":
            nb += 1
        print(f"{icon[f['verdict']]} {f['message']}")
    for owner, counts in res["usage"].items():
        shown = "、".join(f"{w}×{c}" for w, c in counts.items() if c) or "（全集未出现任何登记称谓）"
        print(f"  · {owner} 称谓分布：{shown}")
    print(f"\n禁用称谓/硬错 🔴 {nb} · 共 {len(res['findings'])} 条检出")
    return 1 if nb else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
