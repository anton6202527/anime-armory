#!/usr/bin/env python3
"""A3 人物弧光账本（want-vs-need + 挣来的转变） — 2026-06-24 流程自审落地。

2026 分水岭：强情节是地板、**人物弧光是头部**（短剧首进豆瓣年榜靠人物深化）。此前 n2d-script 只有
`performance_signature`（反漂移=反成长，恰相反）和 4 信号动机词标签，**无人物 want-vs-need / 弧光 / 立体度**。
本脚本镜像 `setup_payoff_ledger` 模式：scaffold 一份 `设定库/character_arc_ledger.json`（人填），并机检：

  ① **want vs need 缺位**——核心角色缺 want 或 need，或 want==need（无内在矛盾·戏剧张力源·PsyAgent 2601.06158）；
  ② **挣来的转变**——arc 里有「转变/顿悟」里程碑却无前置「失败/挣扎/代价」（earned-change checklist·
     防"主角突然顿悟"·2026 观众拒收）；
  ③ **核心角色无弧光登记**——跨集核心角色 arc_milestones 为空（人物只是工具人）。

scaffold/check 都 report-only（warn/info）；`--check --strict` 有 warn 退 1。纯 stdlib·纯函数可测。
用法：python3 character_arc_ledger.py <作品根> --write   |   <作品根> --check [第N集] [--strict] [--json]
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

LEDGER_REL = os.path.join("设定库", "character_arc_ledger.json")
SETBACK_TYPES = ("失败", "挣扎", "代价", "受挫", "打击", "失去", "牺牲", "怀疑", "动摇")
CHANGE_TYPES = ("转变", "顿悟", "成长", "改变", "觉醒", "和解", "释怀", "蜕变")


def is_earned_change(milestones: List[Dict[str, Any]]) -> bool:
    """arc 是否"挣来的转变"：任一转变里程碑之前都有失败/挣扎/代价。纯函数·可测。

    无转变里程碑 → True（不评判）；有转变但其前无任何 setback → False。
    """
    seen_setback = False
    for m in milestones:
        t = str(m.get("type") or "")
        if any(s in t for s in SETBACK_TYPES):
            seen_setback = True
        if any(c in t for c in CHANGE_TYPES):
            if not seen_setback:
                return False
    return True


def want_need_issue(profile: Dict[str, Any]) -> Optional[str]:
    """want/need 问题码：'missing' / 'want_eq_need' / None。纯函数·可测。"""
    want = str(profile.get("want") or "").strip()
    need = str(profile.get("need") or "").strip()
    if not want or not need:
        return "missing"
    if want == need:
        return "want_eq_need"
    return None


def audit_ledger(ledger: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """人物弧光账本机检 → [(severity, code, msg)]。纯函数·可测。"""
    findings: List[Tuple[str, str, str]] = []
    chars = ledger.get("characters") if isinstance(ledger.get("characters"), dict) else {}
    for name, prof in chars.items():
        if not isinstance(prof, dict):
            continue
        milestones = prof.get("arc_milestones") if isinstance(prof.get("arc_milestones"), list) else []
        issue = want_need_issue(prof)
        if issue == "missing":
            findings.append(("warn", "want_need_missing",
                             f"角色「{name}」缺 want 或 need：人物没「想要 vs 真正需要」的内在矛盾，立不起来"))
        elif issue == "want_eq_need":
            findings.append(("info", "want_eq_need",
                             f"角色「{name}」want==need：缺内在矛盾（戏剧张力源是 want≠need 的张力）"))
        if milestones and not is_earned_change(milestones):
            findings.append(("warn", "unearned_change",
                             f"角色「{name}」arc 有转变/顿悟但前面无失败/挣扎/代价：转变没挣来=突然顿悟，"
                             "观众不信——先给可见的内在挣扎+至少一次失败再让他变"))
        if not milestones:
            findings.append(("info", "no_arc_registered",
                             f"角色「{name}」未登记 arc_milestones：若是核心角色，补成长/转变里程碑（人物弧光是 2026 头部分水岭）"))
    return findings


def _load_json(path: str) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _core_characters(root: str) -> List[str]:
    """从 identity_registry 取核心/常驻角色名（scaffold 用）。缺则空。"""
    reg = _load_json(os.path.join(root, "出图", "共享", "identity_registry.json"))
    if not isinstance(reg, dict):
        return []
    out = []
    chars = reg.get("characters")
    if isinstance(chars, list):
        for c in chars:
            if isinstance(c, dict):
                scope = str(c.get("scope") or c.get("tier") or "").lower()
                name = str(c.get("id") or c.get("name") or "").strip()
                if name and (c.get("core") is True or "核心" in scope or "常驻" in scope
                             or "core" in scope or "main" in scope):
                    out.append(name)
    return out


def scaffold(root: str) -> dict:
    """初始化/补全人物弧光账本（不覆盖已填字段）。"""
    path = os.path.join(root, LEDGER_REL)
    ledger = _load_json(path) or {"kind": "n2d_character_arc_ledger", "characters": {}}
    chars = ledger.setdefault("characters", {})
    for name in _core_characters(root):
        chars.setdefault(name, {"want": "", "need": "", "flaw": "", "arc_milestones": []})
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return ledger


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        print("用法: character_arc_ledger.py <作品根> --write | <作品根> --check [--strict] [--json]")
        sys.exit(2)
    root = args[0]
    if "--write" in flags:
        ledger = scaffold(root)
        print(f"✅ 人物弧光账本已 scaffold：{os.path.join(root, LEDGER_REL)}（{len(ledger.get('characters', {}))} 角色，请填 want/need/flaw/arc_milestones）")
        sys.exit(0)
    ledger = _load_json(os.path.join(root, LEDGER_REL))
    if not isinstance(ledger, dict):
        print(f"ℹ️ 无 {LEDGER_REL}——先 `character_arc_ledger.py <作品根> --write` scaffold 再填", file=sys.stderr)
        sys.exit(0)
    findings = audit_ledger(ledger)
    if "--json" in flags:
        print(json.dumps({"findings": [{"severity": s, "code": c, "msg": m} for s, c, m in findings]},
                         ensure_ascii=False, indent=2))
    else:
        print("# 人物弧光机检（A3·report-only·want-vs-need + 挣来的转变）")
        if not findings:
            print("- ✅ 弧光账本机检通过（want≠need·转变有铺垫·核心角色有 arc）")
        for s, c, m in findings:
            print(f"- {'⚠️' if s == 'warn' else 'ℹ️'} [{c}] {m}")
    warn_n = sum(1 for s, _, _ in findings if s == "warn")
    if "--strict" in flags and warn_n:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
