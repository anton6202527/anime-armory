#!/usr/bin/env python3
"""SP1 导出端：拆集时把「伏笔种下→兑现」脚手架成 设定库/setup_payoff_ledger.json。

为什么在 n2d-script：P0 语义谱系 / P1 状态百科管的是「语义/视觉状态」跨集继承；**叙事坑**（伏笔种下
后哪一集兑现、坑别忘了填、兑现别早于种下）是另一条轴。当用户**直接丢小说文件、不经上游小说创作线**时，
漫剧侧此前没有这条兜底——本脚手架在拆集阶段从各集 voiceover/故事板里**捞出候选伏笔/悬念钩**，写成一份
待人补全兑现集的账本草稿；n2d-review 的 `extended_consistency.check_setup_payoff`(SP1) 再消费它校验整账
（坑没填 / 兑现早于种下 / 缺种下集 / 重复 id）。

诚实边界：**不自动判定哪句是伏笔**（文本自动识别伏笔不可靠）——只按显式悬念/钩子标记捞**候选**，
`payoff_ep` 一律留空交编剧填。已存在的账本**不覆盖**：默认只增量补未登记的候选（`--write` 才落盘）。

用法：
  python3 setup_payoff_ledger.py <作品根> [--episodes 1-10] [--write] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence

LEDGER_KIND = "n2d_setup_payoff_ledger"
LEDGER_REL = os.path.join("设定库", "setup_payoff_ledger.json")

# 显式悬念/钩子标记（只捞候选·不臆断伏笔）。与 n2d-review SP1 同口径（独立线·复制不 import）。
FORESHADOW_MARKERS = (
    "伏笔", "悬念", "埋下", "留下疑问", "未解", "成谜", "卖关子", "悬而未决",
    "意味深长", "别有深意", "暗藏", "似乎另有", "不为人知", "cliffhanger", "钩子", "集尾", "🪝",
)
PLACEHOLDER_RE = re.compile(r"(待精修|TODO|TBD|参考 references|按 split_plan\.json)")
BEAT_PLAN_RE = re.compile(r"^\s*[-*]?\s*(?:0-3s|前\s*15s|中段|爽点|集尾|开场钩|留存节拍|节拍点)")
VOICEOVER_META_RE = re.compile(r"^\s*[-*]?\s*(?:本集功能|建议时长|口播节奏|集尾尾扣|改编定位)\s*[:：]")
JSON_FIELD_RE = re.compile(r"^\s*[\"'][^\"']+[\"']\s*:")
STORYBOARD_META_RE = re.compile(
    r"^\s*(?:\*\*片段\d+|[-*]\s*(?:中段锚帧|衔接|节奏|累计|时长|场景|画面|字幕|台词|音效|需要尾帧))"
)
MARKDOWN_TABLE_RE = re.compile(r"^\s*\|")
VOICEOVER_PREFIX_RE = re.compile(r"^\[镜头\d+·[^]]+\]\s*")
HOOK_LABEL_RE = re.compile(r"\s*[⚡💥🪝]?\s*(?:钩子|爽点|集尾)\s*$", re.IGNORECASE)

# 无显式标记、但句式本身就是「挖坑」的弱信号——交编剧确认后才算坑（status=candidate，不进 gate）。
# 治「作者漏标记 → 真伏笔永不进账」：身世/凶手/神秘信物/未解之谜的疑问句与悬置物。
AUTO_FORESHADOW_RE = re.compile(
    r"(到底是谁|究竟是谁|会是谁|是谁.{0,4}[？?]|为什么.{0,12}[？?]|为何.{0,12}[？?]|"
    r"不知道.{0,10}(是|为|会)|不明白|想不通|另有.{0,4}隐情|另有.{0,4}图谋|身世|来历|真实身份|"
    r"神秘的?(信物|令牌|玉佩|盒子|信|纸条|声音|人影)|古怪的|蹊跷|反常|不对劲|总觉得.{0,8}不|"
    r"那个.{0,6}(到底|究竟)|留作后用|日后必有用)")


# ── 纯函数（无依赖·可测） ─────────────────────────────────────────────────────

def ep_num(ep: str) -> Optional[int]:
    """'第3集' / 'ep3' / '3' → 3；解析不出 → None。"""
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


def is_placeholder_line(line: str) -> bool:
    value = str(line or "")
    return bool(
        PLACEHOLDER_RE.search(value)
        or BEAT_PLAN_RE.search(value)
        or VOICEOVER_META_RE.search(value)
        or JSON_FIELD_RE.search(value)
        or STORYBOARD_META_RE.search(value)
        or MARKDOWN_TABLE_RE.search(value)
    )


def clean_desc(line: str) -> str:
    line = str(line or "").strip()
    line = VOICEOVER_PREFIX_RE.sub("", line)
    line = re.sub(r"^[#>\-\s]+", "", line).strip()
    line = HOOK_LABEL_RE.sub("", line).strip()
    line = re.sub(r"\s*[⚡💥🪝]\s*$", "", line).strip()
    return line[:80]


def detect_setups(text: str, ep: str) -> List[dict]:
    """从一集文本里捞候选伏笔（命中标记的句子）。每条 payoff_ep 留空交人填。纯函数·可测。"""
    out: List[dict] = []
    seen: set = set()
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line or is_placeholder_line(line) or not any(m in line for m in FORESHADOW_MARKERS):
            continue
        desc = clean_desc(line)
        if not desc:
            continue
        if desc in seen:
            continue
        seen.add(desc)
        out.append({
            "id": f"{ep}-伏笔{len(out) + 1}",
            "setup_ep": ep,
            "payoff_ep": "",          # 交编剧填：哪一集兑现这个坑
            "desc": desc,
            "status": "open",          # open=待规划兑现；ongoing=长线进行中；done=已兑现
        })
    return out


def detect_auto_candidates(text: str, ep: str) -> List[dict]:
    """无显式标记、但句式像挖坑的弱信号候选（status=candidate，交编剧确认/删除）。纯函数·可测。

    与 detect_setups 互补：那个认显式标记（→open坑·进 gate），这个认句式（→candidate·只提示不拦）。
    避免误把每句疑问都当伏笔——只命中身世/凶手/神秘信物/未解之谜类强句式，且去重限量。"""
    out: List[dict] = []
    seen: set = set()
    for raw_line in re.split(r"[\n。！？!?]", text or ""):
        line = raw_line.strip()
        if not line or is_placeholder_line(line) or len(line) < 4 or not AUTO_FORESHADOW_RE.search(line):
            continue
        # 已被显式标记捞走的句子不重复
        if any(m in line for m in FORESHADOW_MARKERS):
            continue
        desc = line[:40]
        if desc in seen:
            continue
        seen.add(desc)
        out.append({
            "id": f"{ep}-候选{len(out) + 1}",
            "setup_ep": ep,
            "payoff_ep": "",
            "desc": desc,
            "status": "candidate",   # 待编剧确认：升为 open(确为伏笔) 或删除(非伏笔)
            "auto": True,
        })
        if len(out) >= 8:            # 限量：弱信号宁缺毋滥
            break
    return out


def merge_candidates(existing: Sequence[dict], candidates: Sequence[dict]) -> List[dict]:
    """已有账本 + 新候选 → 合并（按 desc 去重·绝不覆盖已填的 payoff_ep）。纯函数·可测。"""
    merged: List[dict] = [dict(p) for p in existing if isinstance(p, dict)]
    have = {str(p.get("desc") or p.get("id")) for p in merged}
    for c in candidates:
        if str(c.get("desc") or c.get("id")) not in have:
            merged.append(dict(c))
            have.add(str(c.get("desc") or c.get("id")))
    return merged


def build_ledger(pairs: Sequence[dict]) -> dict:
    return {"kind": LEDGER_KIND, "version": 1, "pairs": list(pairs)}


# ── IO（best-effort·缺则空） ──────────────────────────────────────────────────

def _read(path: str) -> str:
    try:
        return open(path, encoding="utf-8").read()
    except Exception:
        return ""


def _episode_text(root: str, ep: str) -> str:
    parts = [
        _read(os.path.join(root, "脚本", ep, "voiceover.txt")),
        _read(os.path.join(root, "脚本", ep, "故事板.md")),
    ]
    return "\n".join(parts)


def discover_episodes(root: str) -> List[str]:
    eps = []
    for d in glob.glob(os.path.join(root, "脚本", "第*集")):
        if os.path.isdir(d):
            eps.append(os.path.basename(d))
    return sorted(eps, key=lambda e: ep_num(e) or 0)


def _parse_range(spec: str, available: Sequence[str]) -> List[str]:
    if not spec:
        return list(available)
    want: set = set()
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
    return [e for e in available if (ep_num(e) in want)]


def load_existing(root: str) -> List[dict]:
    path = os.path.join(root, LEDGER_REL)
    if not os.path.isfile(path):
        return []
    try:
        data = json.load(open(path, encoding="utf-8"))
        return [p for p in (data.get("pairs") or data.get("setups") or []) if isinstance(p, dict)]
    except Exception:
        return []


def scaffold(root: str, episodes: Sequence[str], auto: bool = True) -> dict:
    candidates: List[dict] = []
    auto_candidates: List[dict] = []
    for ep in episodes:
        text = _episode_text(root, ep)
        candidates.extend(detect_setups(text, ep))
        if auto:
            auto_candidates.extend(detect_auto_candidates(text, ep))
    merged = merge_candidates(load_existing(root), list(candidates) + list(auto_candidates))
    return {"ledger": build_ledger(merged), "new_candidates": candidates,
            "auto_candidates": auto_candidates, "existing": load_existing(root)}


def _unfilled(p: dict) -> bool:
    """这条坑是否「显式伏笔但兑现集没填」（candidate 弱信号不计入 gate）。"""
    if p.get("status") in ("ongoing", "done", "candidate", "进行中"):
        return False
    return not str(p.get("payoff_ep") or "").strip()


def gate(root: str, ep: str) -> dict:
    """script_stage2 收尾闸：本集检出显式悬念钩，但台账缺/未填其兑现集 → block。

    只认显式标记的坑（避免弱信号误拦）；本集每条显式伏笔都须在账本里有匹配条目且 payoff_ep 已填
    或 status=ongoing。任一未填 → ok=False（run.py strict 下阻断出图）。纯标准库。"""
    detected = detect_setups(_episode_text(root, ep), ep)
    existing = load_existing(root)
    by_desc = {str(p.get("desc") or p.get("id")): p for p in existing if isinstance(p, dict)}
    findings: List[dict] = []
    for d in detected:
        match = by_desc.get(d["desc"])
        if match is None:
            findings.append({"severity": "block", "code": "setup_unlogged",
                             "desc": d["desc"],
                             "message": f"本集检出伏笔/悬念钩「{d['desc']}」但 setup_payoff_ledger 未登记——"
                                        "跑 setup_payoff_ledger.py --write 建账并填兑现集。"})
        elif _unfilled(match):
            findings.append({"severity": "block", "code": "payoff_unfilled",
                             "desc": d["desc"],
                             "message": f"伏笔「{d['desc']}」在账本里但没填兑现集（payoff_ep 空）——"
                                        "补 payoff_ep（哪集兑现）或标 status=ongoing。"})
    return {"episode": ep, "ok": not findings, "detected": len(detected), "findings": findings}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("--episodes", default="", help="如 1-10 或 3,5,7；默认全部已拆集")
    ap.add_argument("--write", action="store_true", help="落盘 设定库/setup_payoff_ledger.json（不覆盖已填 payoff）")
    ap.add_argument("--gate", metavar="第N集", help="script_stage2 收尾闸：本集显式伏笔未填兑现集则 exit 1")
    ap.add_argument("--no-auto", action="store_true", help="不捞无标记的弱信号候选（只认显式标记）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")

    if ns.gate:
        ep = ns.gate if str(ns.gate).startswith("第") else f"第{ns.gate}集"
        g = gate(root, ep)
        if ns.json:
            print(json.dumps(g, ensure_ascii=False, indent=2))
        else:
            print(f"# 伏笔台账闸 — {ep}　检出显式伏笔 {g['detected']} 条　{'PASS' if g['ok'] else 'BLOCK'}")
            for f in g["findings"]:
                print(f"- BLOCK [{f['code']}] {f['message']}")
            if g["ok"]:
                print("- ✅ 本集显式伏笔均已在账本登记并填了兑现集（或标 ongoing）")
        return 0 if g["ok"] else 1

    eps = _parse_range(ns.episodes, discover_episodes(root))
    res = scaffold(root, eps, auto=not ns.no_auto)
    if ns.write:
        path = os.path.join(root, LEDGER_REL)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(res["ledger"], fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    n_new = len(res["new_candidates"])
    n_auto = len(res.get("auto_candidates") or [])
    n_total = len(res["ledger"]["pairs"])
    print(f"扫描 {len(eps)} 集 · 显式伏笔 {n_new} 条 · 弱信号候选 {n_auto} 条（待确认）· 账本共 {n_total} 条"
          + ("（已写盘）" if ns.write else "（未写盘，加 --write 落档）"))
    for p in res["ledger"]["pairs"]:
        if p.get("status") == "candidate":
            flag = "🔍弱信号·确认是否伏笔"
        elif not p.get("payoff_ep") and p.get("status") not in ("ongoing", "done"):
            flag = "⚠待填兑现集"
        else:
            flag = ""
        print(f"  [{p.get('setup_ep')}→{p.get('payoff_ep') or '?'}] {p.get('desc')} {flag}")
    if any(not p.get("payoff_ep") and p.get("status") not in ("ongoing", "done") for p in res["ledger"]["pairs"]):
        print("\n下一步：给每个伏笔填 payoff_ep（哪一集兑现）或标 status=ongoing；"
              "n2d-review SP1 会校验坑没填/兑现早于种下。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
