#!/usr/bin/env python3
"""audience_emotion_account.py — 每集观众情绪账本。

记录“期待/恐惧/信任/好奇/兑现”的债务变化，帮助判断剧情是否合理好看。report-only，不涉及时长硬门。
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

KIND = "n2d_audience_emotion_account"
EXPECT_RE = re.compile(r"(想要|必须|誓要|目标|为了|要去|夺回|救出|证明|复仇|活下去)")
FEAR_RE = re.compile(r"(危险|来不及|会死|会输|失去|害怕|一旦|否则|被抓|围住|赐死|追杀)")
TRUST_RE = re.compile(r"(信任|背叛|怀疑|盟友|敌人|师徒|夫妻|救你|护你|骗)")
CURIOSITY_RE = re.compile(r"(真相|秘密|到底是谁|为什么|为何|身世|系统|任务|线索|证据)")
PAYOFF_RE = re.compile(r"(因此|于是|终于|兑现|揭穿|发现|得到|升级|突破|反杀|打脸|救出|夺回)")
HOOK_RE = re.compile(r"(🪝|集尾|突然|真相|危机|来了|不可能|怎么会)")


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def score(text: str, regex: re.Pattern[str]) -> int:
    return len(regex.findall(text or ""))


def build_account(root: Path, ep: str) -> Dict[str, Any]:
    base = root / "脚本" / ep
    text = "\n".join(read(base / name) for name in ("voiceover.txt", "分镜剧本.md", "故事板.md", "storyboard.json"))
    ledgers = {
        "expectation_debt": score(text, EXPECT_RE),
        "fear_debt": score(text, FEAR_RE),
        "trust_debt": score(text, TRUST_RE),
        "curiosity_debt": score(text, CURIOSITY_RE),
        "payoff_credit": score(text, PAYOFF_RE),
        "ending_hook": bool(HOOK_RE.search(" ".join(text.splitlines()[-6:]))),
    }
    findings: List[Dict[str, Any]] = []
    if ledgers["curiosity_debt"] and not ledgers["ending_hook"] and ledgers["payoff_credit"] == 0:
        findings.append({"severity": "warn", "code": "curiosity_without_hook_or_payoff", "message": "本集种下好奇/秘密，但缺兑现或集尾钩接力，观众情绪债可能悬空。"})
    if ledgers["fear_debt"] >= 2 and ledgers["payoff_credit"] == 0:
        findings.append({"severity": "info", "code": "fear_unpaid", "message": "危机/恐惧信号较多但本集无明显回报；确认下一集冷开场接住。"})
    if not any(ledgers[k] for k in ("expectation_debt", "fear_debt", "curiosity_debt", "payoff_credit")):
        findings.append({"severity": "warn", "code": "flat_emotion_account", "message": "未检测到明确期待、恐惧、好奇或兑现信号；本集可能情绪驱动力偏弱。"})
    return {"kind": KIND, "episode": ep, "account": ledgers, "findings": findings}


def render_md(report: Dict[str, Any]) -> str:
    acc = report.get("account") or {}
    lines = [
        "# 观众情绪账本",
        "",
        f"- episode: {report.get('episode')}",
        f"- expectation_debt: {acc.get('expectation_debt')}",
        f"- fear_debt: {acc.get('fear_debt')}",
        f"- trust_debt: {acc.get('trust_debt')}",
        f"- curiosity_debt: {acc.get('curiosity_debt')}",
        f"- payoff_credit: {acc.get('payoff_credit')}",
        f"- ending_hook: {acc.get('ending_hook')}",
        "",
    ]
    for f in report.get("findings") or []:
        lines.append(f"- {str(f.get('severity') or 'info').upper()} [{f.get('code')}] {f.get('message')}")
    return "\n".join(lines) + "\n"


def write_outputs(root: Path, ep: str, report: Dict[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    jp = out / f"audience_emotion_account_{ep}.json"
    mp = out / f"audience_emotion_account_{ep}.md"
    tmp = jp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, jp)
    tmp_md = mp.with_suffix(".md.tmp")
    tmp_md.write_text(render_md(report), encoding="utf-8")
    os.replace(tmp_md, mp)
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 每集观众情绪账本")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ns.episode if ns.episode.startswith("第") else f"第{ns.episode}集"
    report = build_account(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, report)
        report["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_md(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
