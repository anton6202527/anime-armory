#!/usr/bin/env python3
"""narrative_state_audit.py — 叙事状态台账（知识 / 位置 / 关系）跨集一致性。

为什么存在：现有 state_ledger（n2d-review）只追**视觉**状态（伤/泪/妆/服随镜号单调推进），跨集
的**叙事**状态完全没人看守——最容易出又最难发现的硬伤就藏在这里：
  · 知识：角色 A 第3集还不知道某事，第5集却表现得早就知道（「知道得太早」）。
  · 位置：A 上一集在甲地，本集无转场却出现在乙地（「位置瞬移」）。
  · 关系：A 与 B 的称呼/关系前后矛盾。
本脚本把这条轴落成 `设定库/narrative_state_ledger.json`：从各集 voiceover 捞**候选**（交编剧确认），
并对**已声明**的条目做确定性跨集校验（知识倒流 / 位置瞬移）。

诚实边界（同 setup_payoff）：自由文本自动判定"谁知道什么"不可靠——auto 候选一律 status=candidate，
`known_from_ep`/`keyword` 交编剧填；确定性校验只跑在字段填全的条目上（keyword 可由 【…】/《…》/称谓
等可靠专名自动预填）。

用法：
  python3 narrative_state_audit.py <作品根> [--episodes 1-10] [--write] [--json]   # 建账 + 校验
  python3 narrative_state_audit.py <作品根> --check [--strict] [--json]            # 只校验已声明条目
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

LEDGER_KIND = "n2d_narrative_state_ledger"
LEDGER_REL = os.path.join("设定库", "narrative_state_ledger.json")

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
_TITLE_RE = re.compile(r"[一-鿿]{0,4}(?:娘娘|王爷|师尊|陛下|公主|太子|小姐|少爷|夫人|长老|"
                       r"师兄|师姐|宗主|皇后|贵妃|将军|侍卫|掌门|大人|阁下|城主|帝君|魔尊)")
_BRACKET_RE = re.compile(r"【([^】]{1,20})】|《([^》]{1,20})》")

# 知识获取标记（角色"得知/明白"某事）。
KNOW_RE = re.compile(r"(知道了|得知|才知道|这才明白|原来|发现.{0,6}(?:是|竟)|听说|告诉.{0,6}[，。]|"
                     r"明白了|恍然|真相是|看穿|识破|察觉到|意识到)")
# 位置标记 + 地点抽取。
PLACE_RE = re.compile(r"(?:在|到了|来到|抵达|回到|前往|赶往|赶赴|身处|来到了|进了)"
                      r"([一-鿿]{2,6}?(?:城|宫|府|山|村|镇|院|阁|殿|寺|楼|庄|关|境|国|界|池|林|崖|窟|洞|堂)|[一-鿿]{2,4})")
# 转场标记（位置变化的合法解释）。
MOVE_RE = re.compile(r"(前往|赶往|出发|动身|启程|赶赴|回到|来到|抵达|进了|赶回|奔向|赶去|离开|踏上)")
# 关系标记。
REL_RE = re.compile(r"(是我的|是你的|拜.{0,4}为师|认.{0,4}作|结为|未婚(?:夫|妻)|夫妻|兄妹|姐弟|父子|母女|"
                    r"师徒|主仆|生死之交|宿敌|仇人)")


def ep_num(ep: str) -> Optional[int]:
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


def ep_label(value: str) -> str:
    return value if str(value).startswith("第") else f"第{value}集"


def entities(text: str) -> Set[str]:
    out: Set[str] = set()
    for grp in _BRACKET_RE.findall(text):
        for g in grp:
            if g.strip():
                out.add(g.strip())
    for t in _TITLE_RE.findall(text):
        out.add(t)
    return out


def _lines(text: str) -> List[Tuple[str, str]]:
    """voiceover → [(role, body)]；非镜头行 role=''。"""
    rows: List[Tuple[str, str]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = LINE_RE.match(line)
        if m:
            rows.append((m.group(2).strip(), (m.group(5) or "").strip()))
        else:
            rows.append(("", line))
    return rows


# ── 候选捞取（纯函数·可测） ───────────────────────────────────────────────────

def detect_knowledge(text: str, ep: str) -> List[dict]:
    out: List[dict] = []
    seen: Set[str] = set()
    for role, body in _lines(text):
        if not body or not KNOW_RE.search(body):
            continue
        desc = body[:40]
        if desc in seen:
            continue
        seen.add(desc)
        kw = sorted(entities(body))     # 可靠专名预填 keyword；没有则留空交人填
        out.append({
            "id": f"{ep}-知{len(out) + 1}",
            "character": role if role and role != "旁白" else "",
            "fact": desc,
            "keyword": kw[0] if kw else "",
            "known_from_ep": ep,
            "kind": "knowledge",
            "status": "candidate",
            "auto": True,
        })
    return out


def detect_locations(text: str, ep: str) -> List[dict]:
    out: List[dict] = []
    seen: Set[str] = set()
    for role, body in _lines(text):
        for place in PLACE_RE.findall(body):
            place = place.strip()
            key = f"{role}:{place}"
            if not place or key in seen:
                continue
            seen.add(key)
            out.append({
                "character": role if role and role != "旁白" else "",
                "ep": ep, "place": place, "status": "candidate", "auto": True,
            })
    return out


def detect_relationships(text: str, ep: str) -> List[dict]:
    out: List[dict] = []
    seen: Set[str] = set()
    for role, body in _lines(text):
        m = REL_RE.search(body)
        if not m:
            continue
        desc = body[:40]
        if desc in seen:
            continue
        seen.add(desc)
        out.append({
            "id": f"{ep}-关{len(out) + 1}",
            "desc": desc, "relation": m.group(1), "from_ep": ep,
            "status": "candidate", "auto": True,
        })
    return out


# ── 确定性跨集校验（纯函数·可测） ──────────────────────────────────────────────

def premature_knowledge(knowledge: Sequence[dict], ep_texts: Dict[str, str]) -> List[dict]:
    """「知道得太早」：某条知识声明 known_from_ep=K、character、keyword 填全后，
    若 K 之前的某集里该角色已提及该 keyword → 知识倒流 warn。纯函数·可测。"""
    findings: List[dict] = []
    num_texts = {ep_num(ep): txt for ep, txt in ep_texts.items() if ep_num(ep) is not None}
    for k in knowledge:
        char = str(k.get("character") or "").strip()
        kw = str(k.get("keyword") or "").strip()
        kn = ep_num(str(k.get("known_from_ep") or ""))
        if not (char and kw and kn is not None):
            continue
        for n, txt in num_texts.items():
            if n >= kn:
                continue
            for role, body in _lines(txt):
                if kw in body and (role == char or char in body):
                    findings.append({
                        "severity": "warn", "code": "knowledge_premature",
                        "message": f"知识倒流：「{k.get('fact') or kw}」声明第{kn}集才知道，但第{n}集 {char} 已提及"
                                   f"「{kw}」（{body[:24]}…）——核对谁在第几集知道什么。",
                        "character": char, "keyword": kw, "declared_ep": kn, "seen_ep": n,
                    })
                    break
    return findings


def location_jumps(locations: Sequence[dict], ep_texts: Dict[str, str]) -> List[dict]:
    """「位置瞬移」：同一角色相邻有声明的集，地点变了但两集都无转场标记 → warn。纯函数·可测。"""
    findings: List[dict] = []
    by_char: Dict[str, List[dict]] = {}
    for loc in locations:
        char = str(loc.get("character") or "").strip()
        if char and ep_num(str(loc.get("ep") or "")) is not None and loc.get("place"):
            by_char.setdefault(char, []).append(loc)
    for char, locs in by_char.items():
        locs = sorted(locs, key=lambda x: ep_num(str(x["ep"])))
        for a, b in zip(locs, locs[1:]):
            if a["place"] == b["place"]:
                continue
            txt_a = ep_texts.get(ep_label(a["ep"]), "")
            txt_b = ep_texts.get(ep_label(b["ep"]), "")
            if MOVE_RE.search(txt_a) or MOVE_RE.search(txt_b):
                continue
            findings.append({
                "severity": "warn", "code": "location_jump",
                "message": f"位置瞬移：{char} {a['ep']}在「{a['place']}」、{b['ep']}在「{b['place']}」，"
                           "两集都无转场（前往/赶往/抵达…）——补一笔过场或确认是否漏写。",
                "character": char, "from": a["place"], "to": b["place"],
                "from_ep": a["ep"], "to_ep": b["ep"],
            })
    return findings


# ── IO / 编排 ────────────────────────────────────────────────────────────────

def _read(path: str) -> str:
    try:
        return open(path, encoding="utf-8").read()
    except Exception:
        return ""


def discover_episodes(root: str) -> List[str]:
    eps = [os.path.basename(os.path.dirname(p))
           for p in glob.glob(os.path.join(root, "脚本", "第*集", "voiceover.txt"))]
    return sorted(eps, key=lambda e: ep_num(e) or 0)


def episode_texts(root: str, eps: Sequence[str]) -> Dict[str, str]:
    return {ep: _read(os.path.join(root, "脚本", ep, "voiceover.txt")) for ep in eps}


def load_existing(root: str) -> Optional[dict]:
    path = os.path.join(root, LEDGER_REL)
    if not os.path.isfile(path):
        return None
    try:
        d = json.load(open(path, encoding="utf-8"))
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _merge(existing: Sequence[dict], cands: Sequence[dict], key) -> List[dict]:
    merged = [dict(p) for p in existing if isinstance(p, dict)]
    have = {key(p) for p in merged}
    for c in cands:
        if key(c) not in have:
            merged.append(dict(c))
            have.add(key(c))
    return merged


def scaffold(root: str, eps: Sequence[str]) -> dict:
    know: List[dict] = []
    loc: List[dict] = []
    rel: List[dict] = []
    texts = episode_texts(root, eps)
    for ep in eps:
        t = texts[ep]
        know.extend(detect_knowledge(t, ep))
        loc.extend(detect_locations(t, ep))
        rel.extend(detect_relationships(t, ep))
    prev = load_existing(root) or {}
    return {
        "kind": LEDGER_KIND, "version": 1,
        "knowledge": _merge(prev.get("knowledge") or [], know, lambda p: p.get("fact") or p.get("id")),
        "locations": _merge(prev.get("locations") or [], loc, lambda p: f"{p.get('character')}:{p.get('ep')}:{p.get('place')}"),
        "relationships": _merge(prev.get("relationships") or [], rel, lambda p: p.get("desc") or p.get("id")),
    }


def check(root: str) -> dict:
    """对已落盘账本（或现场 scaffold）跑确定性跨集校验。"""
    eps = discover_episodes(root)
    texts = episode_texts(root, eps)
    ledger = load_existing(root) or scaffold(root, eps)
    findings = (premature_knowledge(ledger.get("knowledge") or [], texts)
                + location_jumps(ledger.get("locations") or [], texts))
    return {"ok": not findings, "findings": findings,
            "counts": {"knowledge": len(ledger.get("knowledge") or []),
                       "locations": len(ledger.get("locations") or []),
                       "relationships": len(ledger.get("relationships") or [])}}


def _parse_range(spec: str, available: Sequence[str]) -> List[str]:
    if not spec:
        return list(available)
    want: Set[int] = set()
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
    return [e for e in available if ep_num(e) in want]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 叙事状态台账（知识/位置/关系）跨集一致性")
    ap.add_argument("root")
    ap.add_argument("--episodes", default="")
    ap.add_argument("--write", action="store_true", help="落盘 设定库/narrative_state_ledger.json")
    ap.add_argument("--check", action="store_true", help="只跑跨集校验（不重建候选）")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")

    if ns.check:
        res = check(root)
        if ns.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"# 叙事状态跨集校验　{'PASS' if res['ok'] else 'WARN'}　"
                  f"知识 {res['counts']['knowledge']}/位置 {res['counts']['locations']}/关系 {res['counts']['relationships']}")
            for f in res["findings"]:
                print(f"- WARN [{f['code']}] {f['message']}")
            if res["ok"]:
                print("- ✅ 已声明条目未见知识倒流/位置瞬移")
        return 1 if (ns.strict and not res["ok"]) else 0

    eps = _parse_range(ns.episodes, discover_episodes(root))
    ledger = scaffold(root, eps)
    if ns.write:
        path = os.path.join(root, LEDGER_REL)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(ledger, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    findings = (premature_knowledge(ledger.get("knowledge") or [], episode_texts(root, eps))
                + location_jumps(ledger.get("locations") or [], episode_texts(root, eps)))
    if ns.json:
        print(json.dumps({"ledger": ledger, "findings": findings}, ensure_ascii=False, indent=2))
        return 0
    print(f"扫描 {len(eps)} 集 · 知识候选 {len(ledger['knowledge'])} · 位置 {len(ledger['locations'])} · "
          f"关系 {len(ledger['relationships'])}" + ("（已写盘）" if ns.write else "（未写盘，加 --write）"))
    for f in findings:
        print(f"- WARN [{f['code']}] {f['message']}")
    print("\n下一步：给知识条目填 character/keyword/known_from_ep（哪集才知道），位置条目确认 place；"
          "n2d-review NS1 会复核知识倒流/位置瞬移。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
