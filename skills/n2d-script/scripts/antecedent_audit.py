#!/usr/bin/env python3
"""antecedent_audit.py — 前因依赖检查（删集/跳章致前因缺失）。

为什么存在：拆集时若把中间某集删掉/跳过（第3集没了，第2→第4直切），后文会引用一个从没在
**留存集**里交代过的人/物/设定——观众断片"这谁啊"。现有 source_adaptation_audit 只逐集查
"本集源覆盖"，从不回看"被引用的前情交代集是否还在"。本脚本补这条跨集轴：

  ① 集号内缝隙（interior gap）：留存集号在 min~max 之间缺号 = 中间集被删/跳过（确定性信号）。
     —— 窗口起点（中段开工，如从第50集起）不算缝隙；若项目保留了早期样例集又从中段开工，
        在 `脚本/episode_scope.json` 声明 `window_start` / `intentional_gaps`，避免把有意窗口误判成事故。
  ② 实体首现错位：某人/物/称谓在"缝隙后"才首次出现且此前留存集里没交代过 —— 其引入很可能在被删集里。

诚实边界：看不到被删集的内容，只能从"集号缺口 + 实体首现位置"推断。命中=warn；--strict 升 block。

用法：
  python3 antecedent_audit.py <作品根> 第N集 [--strict] [--json]   # 单集闸（出图前）
  python3 antecedent_audit.py <作品根> --series [--json]           # 全剧前因依赖图
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

LINE_RE = re.compile(r"^\[镜头(\d+)·([^·\]]+)·([^·\]]+?)(?:·([^·\]]+))?\]\s*(.*)$")
_TITLE_RE = re.compile(r"[一-鿿]{0,4}(?:娘娘|王爷|师尊|陛下|公主|太子|小姐|少爷|夫人|长老|"
                       r"师兄|师姐|宗主|皇后|贵妃|将军|侍卫|掌门|大人|阁下|城主|帝君|魔尊)")
_BRACKET_RE = re.compile(r"【([^】]{1,20})】|《([^》]{1,20})》")


def ep_num(ep: str) -> Optional[int]:
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


def ep_label(value: str) -> str:
    return value if str(value).startswith("第") else f"第{value}集"


def discover_episodes(root: str) -> List[str]:
    eps = [os.path.basename(d) for d in glob.glob(os.path.join(root, "脚本", "第*集"))
           if os.path.isdir(d)]
    return sorted(eps, key=lambda e: ep_num(e) or 0)


def _voiceover(root: str, ep: str) -> str:
    p = Path(root) / "脚本" / ep / "voiceover.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def entities_in_text(text: str) -> Set[str]:
    """一集里的具名实体：角色名（[镜头·角色·…] 的角色，非旁白）+ 称谓 + 【…】《…》专名。纯函数·可测。"""
    ents: Set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        m = LINE_RE.match(line)
        if m:
            role = m.group(2).strip()
            if role and role != "旁白":
                ents.add(role)
            body = m.group(5) or ""
        else:
            body = line
        for grp in _BRACKET_RE.findall(body):
            for g in grp:
                if g.strip():
                    ents.add(g.strip())
        for t in _TITLE_RE.findall(body):
            ents.add(t)
    return ents


def interior_gaps(nums: Sequence[int]) -> List[int]:
    """留存集号里 min~max 之间缺的号（窗口起点之前不算）。纯函数·可测。"""
    if not nums:
        return []
    present = set(nums)
    return [n for n in range(min(present) + 1, max(present)) if n not in present]


def _num_list(value: Any) -> List[int]:
    if value is None:
        return []
    if isinstance(value, (str, int)):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    out: List[int] = []
    for item in value:
        n = ep_num(str(item))
        if n is not None:
            out.append(n)
    return out


def load_episode_scope(root: str) -> Dict[str, Any]:
    """读取中段/跳集范围声明。缺文件=空 scope；不让声明文件本身成为新依赖。"""
    for rel in ("脚本/episode_scope.json", "设定库/episode_scope.json"):
        p = Path(root) / rel
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def intentional_gap_numbers(scope: Mapping[str, Any], nums: Sequence[int]) -> Set[int]:
    """scope 里声明的有意缺口：显式 intentional_gaps + window_start 之前的缺号。"""
    allowed = set(_num_list(scope.get("intentional_gaps") or scope.get("acknowledged_gaps")))
    wstart = ep_num(str(scope.get("window_start") or scope.get("window_start_episode") or ""))
    present = set(nums)
    if wstart is not None and present:
        allowed |= {n for n in range(min(present) + 1, wstart) if n not in present}
    return allowed


def first_appearances(root: str, eps: Sequence[str]) -> Dict[str, int]:
    """每个实体在留存集里的首现集号。纯函数语义（IO 仅读 voiceover）。"""
    first: Dict[str, int] = {}
    for ep in sorted(eps, key=lambda e: ep_num(e) or 0):
        n = ep_num(ep)
        if n is None:
            continue
        for ent in entities_in_text(_voiceover(root, ep)):
            if ent not in first:
                first[ent] = n
    return first


def audit(root: str, ep: str) -> Dict[str, Any]:
    """单集前因依赖闸：本集是否坐落在被删集之后、是否引用了缝隙里才该交代的实体。"""
    ep = ep_label(ep)
    cur = ep_num(ep)
    eps = discover_episodes(root)
    nums = [ep_num(e) for e in eps if ep_num(e) is not None]
    findings: List[Dict[str, Any]] = []
    if cur is None or not nums:
        return {"episode": ep, "ok": True, "findings": findings, "stats": {}}

    all_gaps = set(interior_gaps(nums))
    scope = load_episode_scope(root)
    allowed_gaps = intentional_gap_numbers(scope, nums)
    gaps = all_gaps - allowed_gaps
    present = set(nums)
    earlier = [n for n in nums if n < cur]
    # 本集是不是"紧跟断档的第一个留存集"：前一号缺失、且其前面还有留存集（排除窗口起点）。
    # 只在此处报，避免同一缝隙对其后每集重复刷。
    first_after_gap = (cur - 1) in gaps and bool(earlier)

    if first_after_gap:
        # 紧邻本集、连续缺的那段断档（cur-1, cur-2, … 直到遇到留存集）
        miss, x = [], cur - 1
        while x in gaps:
            miss.append(x)
            x -= 1
        miss = sorted(miss)
        findings.append({
            "severity": "warn", "code": "antecedent_gap",
            "message": f"{ep} 之前的第{'/'.join(map(str, miss))}集缺失（集号断档）——若是删集/跳章，"
                       f"本集引用的人/物/设定的前因交代可能在被删集里。恢复被删集或在本集补一句前情。",
            "missing_episodes": miss,
        })
        # 实体错位：本集首现、且断档前留存集里从没出现过的具名实体（其引入疑在被删集）
        prior_ents: Set[str] = set()
        for e in eps:
            n = ep_num(e)
            if n is not None and n < miss[0]:
                prior_ents |= entities_in_text(_voiceover(root, e))
        orphan = sorted(entities_in_text(_voiceover(root, ep)) - prior_ents)
        if orphan:
            findings.append({
                "severity": "info", "code": "entity_first_seen_after_gap",
                "message": f"{ep} 首次出现且断档前未交代的实体：{'/'.join(orphan[:8])}"
                           "——确认是本集新引入（正常）还是前因被删（断片）。",
                "entities": orphan[:8],
            })

    ok = not any(f["severity"] in ("warn", "must", "block") for f in findings)
    return {"episode": ep, "ok": ok, "findings": findings,
            "stats": {"present_episodes": len(nums),
                      "interior_gaps": sorted(all_gaps),
                      "active_gaps": sorted(gaps),
                      "intentional_gaps": sorted(all_gaps & allowed_gaps)}}


def audit_series(root: str) -> Dict[str, Any]:
    eps = discover_episodes(root)
    nums = [ep_num(e) for e in eps if ep_num(e) is not None]
    all_gaps = interior_gaps(nums)
    scope = load_episode_scope(root)
    allowed_gaps = intentional_gap_numbers(scope, nums)
    gaps = [g for g in all_gaps if g not in allowed_gaps]
    first = first_appearances(root, eps)
    findings: List[Dict[str, Any]] = []
    if gaps:
        findings.append({"severity": "warn", "code": "interior_gaps",
                         "message": f"集号断档（中间集被删/跳过）：缺第{'/'.join(map(str, gaps))}集——"
                                    "这些集若承载前因，后文会断片。",
                         "missing_episodes": gaps})
    # 首现落在某条缝隙之后的实体（其引入可能在缝隙里）
    after_gap = {ent: n for ent, n in first.items() if any(g < n for g in gaps)}
    suspicious = {ent: n for ent, n in after_gap.items()
                  if any(g == n - 1 for g in gaps)}  # 紧跟缺号之后首现，最可疑
    if suspicious:
        findings.append({"severity": "info", "code": "entity_intro_maybe_in_gap",
                         "message": "紧跟断档之后才首现的实体（引入疑在被删集）："
                                    + "；".join(f"{e}(第{n}集)" for e, n in sorted(suspicious.items(), key=lambda kv: kv[1])[:10]),
                         "entities": list(suspicious)})
    intentional = sorted(set(all_gaps) & allowed_gaps)
    if intentional:
        findings.append({"severity": "info", "code": "intentional_episode_scope",
                         "message": f"已按 episode_scope 声明忽略有意缺口：第{'/'.join(map(str, intentional))}集",
                         "missing_episodes": intentional})
    return {"episodes": eps, "interior_gaps": all_gaps, "active_gaps": gaps,
            "intentional_gaps": intentional, "first_appearances": first, "findings": findings}


def print_human(res: Dict[str, Any], series: bool) -> None:
    if series:
        print(f"# 前因依赖图（全剧）　留存集 {len(res['episodes'])}　断档 {res['interior_gaps'] or '无'}")
    else:
        print(f"# 前因依赖检查 — {res['episode']}")
    findings = res.get("findings") or []
    if not findings:
        print("- ✅ 未发现集号断档导致的前因缺失风险")
        return
    icon = {"block": "BLOCK", "must": "BLOCK", "warn": "WARN", "info": "INFO"}
    for f in findings:
        print(f"- {icon.get(f['severity'], 'INFO')} [{f['code']}] {f['message']}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 前因依赖检查（删集/跳章致前因缺失）")
    ap.add_argument("root")
    ap.add_argument("episode", nargs="?", help="第N集；省略且加 --series 则全剧")
    ap.add_argument("--series", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")

    if ns.series or not ns.episode:
        res = audit_series(root)
        if ns.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print_human(res, series=True)
        has_warn = any(f["severity"] in ("warn", "must", "block") for f in res["findings"])
        return 1 if (ns.strict and has_warn) else 0

    res = audit(root, ep_label(ns.episode))
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print_human(res, series=False)
    has_block = any(f["severity"] in ("warn", "must", "block") for f in res["findings"])
    return 1 if (ns.strict and has_block) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
