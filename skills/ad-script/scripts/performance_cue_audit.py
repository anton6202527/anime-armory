#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""人物镜**表演指令**机检（advisory·出图前·编剧/分镜轴）。

传统片场导演给演员的不是形容词而是**可演的东西**（playable direction）：具体动作
（"拧开瓶盖闻了一下"）、视线（"看向镜头外的孩子"）、情绪节拍（"松了口气"）。
"表演自然点/开心点/要有高级感"是结果指令（result direction），演员演不了，AI 更演不了——
AI 流水线里表演只存在于 prompt 文字里，storyboard 人物镜不写这三样，生成的人就是
死脸假笑目光涣散（n2d 的 script_quality_gate 把 performance_cues 列为必填七字段之一，
广告线人物镜同理，只是 4-10 镜量级用 advisory 口径）。

三轴机检（缺三轴 warn / 缺两轴 info / 无人物镜或 endcard 豁免）：
    ① 情绪/状态 —— 松了口气/惊喜/犹豫/专注…（有情绪词即可，比没有强）
    ② 视线 —— 看向/注视/对视/看镜头/镜头外…（视线差一寸，情绪差一档）
    ③ 可演动作 —— 拧开/递给/试用/涂抹/起身…（具体物理动词，不是"表现出喜欢"）

全 advisory：`summary.block` 恒 0。词汇表见 references/表演指令.md。

用法：
    python3 performance_cue_audit.py <作品根> [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

VERSION = 1
KIND = "ad_performance_cue_audit"
REPORT_REL = os.path.join("生产数据", "ad_performance_cue_audit.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")
CUE_DOC = "skills/ad-script/references/表演指令.md"

CHAR_KEY_RE = re.compile(r"\bCHAR_[A-Za-z0-9_]*\b")
PEOPLE_RE = re.compile(r"人物|主角|模特|演员|女主|男主|代言人|妈妈|爸爸|孩子|情侣|上班族|白领", re.IGNORECASE)
ENDCARD_RE = re.compile(r"片尾|尾板|end.?card|endcard|logo|CTA|价格板|二维码", re.IGNORECASE)

EMOTION_RE = re.compile(
    r"情绪|表情|微笑|大笑|皱眉|惊喜|惊讶|犹豫|放松|疲惫|兴奋|欣慰|满足|松了?口气|叹气|苦恼|"
    r"专注|好奇|心动|嫌弃|烦躁|安心|得意|眼睛一亮|嘴角|如释重负", re.IGNORECASE)
EYELINE_RE = re.compile(
    r"视线|看向|望向|注视|凝视|对视|看镜头|直视镜头|镜头外|低头看|抬头|扫了一眼|目光|余光|回头看",
    re.IGNORECASE)
ACTION_RE = re.compile(
    r"拿起|放下|拧开|打开|推开|递给|接过|转身|起身|坐下|靠近|凑近|试用|涂抹|喷|按下|滑动|点击|"
    r"举起|咬|喝|吃|闻|擦|挥手|比划|拍了拍|摸|翻|捧着|抱着|指着|穿上|脱下|摇晃|搅拌", re.IGNORECASE)

AXES: Tuple[Tuple[str, re.Pattern], ...] = (("情绪/状态", EMOTION_RE), ("视线", EYELINE_RE), ("可演动作", ACTION_RE))


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, shots: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    if shots:
        out["shots"] = list(shots)
    return out


def iter_shots(storyboard: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = storyboard.get("shots") or storyboard.get("clips") or storyboard.get("镜头") or []
    return [r for r in rows if isinstance(r, dict)]


def shot_id(shot: Mapping[str, Any], idx: int) -> str:
    return str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"镜头{idx + 1}")


def shot_blob(shot: Mapping[str, Any]) -> str:
    parts = []
    for key in ("shot", "frame", "画面", "主体动作", "description", "desc", "visual", "scene", "场景",
                "performance", "表演", "acting", "emotion", "情绪", "eyeline", "视线",
                "shot_type", "section", "purpose", "vo", "台词"):
        val = shot.get(key)
        if val:
            parts.append(str(val))
    assets = shot.get("assets")
    if isinstance(assets, Mapping):
        parts.extend(str(k) for k in assets)
    elif isinstance(assets, (list, tuple)):
        parts.extend(str(v) for v in assets)
    return " ".join(parts)


def is_people_shot(shot: Mapping[str, Any]) -> bool:
    blob = shot_blob(shot)
    if ENDCARD_RE.search(blob):
        return False
    return bool(CHAR_KEY_RE.search(blob) or PEOPLE_RE.search(blob))


def missing_axes(shot: Mapping[str, Any]) -> List[str]:
    blob = shot_blob(shot)
    return [name for name, pattern in AXES if not pattern.search(blob)]


def build(root: Path) -> Dict[str, Any]:
    root = Path(root)
    findings: List[Dict[str, Any]] = []
    try:
        storyboard = json.loads((root / STORYBOARD_REL).read_text(encoding="utf-8"))
    except Exception:
        storyboard = None
    available = isinstance(storyboard, dict)
    people_shots: List[Tuple[str, List[str]]] = []
    if not available:
        findings.append(finding("warn", "storyboard_missing",
                                f"缺 {STORYBOARD_REL}——没有分镜可审表演指令（insufficient_data）。"))
    else:
        for idx, shot in enumerate(iter_shots(storyboard)):
            if not is_people_shot(shot):
                continue
            people_shots.append((shot_id(shot, idx), missing_axes(shot)))
        bare = [sid for sid, miss in people_shots if len(miss) == 3]
        thin = [(sid, miss) for sid, miss in people_shots if len(miss) == 2]
        if bare:
            findings.append(finding(
                "warn", "performance_cue_unspecified",
                f"{'、'.join(bare)} 是人物镜但情绪/视线/可演动作**三轴全没写**——"
                "导演行规：给演员可演的过程，不给'自然点/开心点'这类结果形容词；AI 同理，"
                f"不写就是死脸假笑目光涣散。词汇表见 {CUE_DOC}",
                bare))
        for sid, miss in thin:
            findings.append(finding(
                "info", "performance_cue_thin",
                f"{sid} 人物镜缺 {'/'.join(miss)}——补上表演才立得住（advisory）", [sid]))

    return {
        "schema_version": VERSION, "kind": KIND, "available": available,
        "project_root": str(root), "generated_at": now_iso(),
        "cue_reference": CUE_DOC,
        "inputs": {"people_shots": len(people_shots)},
        "summary": {"block": 0,
                    "warn": sum(1 for f in findings if f["severity"] == "warn"),
                    "info": sum(1 for f in findings if f["severity"] == "info")},
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report["summary"]
    lines = ["# 人物镜表演指令机检", "",
             f"- 人物镜 {report['inputs'].get('people_shots')} 个 · warn {s['warn']} · info {s['info']}"
             "（advisory：表演好坏归导演，本检只保证三轴想过）", ""]
    icon = {"warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 人物镜均已声明情绪/视线/可演动作（演得好坏仍需人判）")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    for target, payload in ((path, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                            (path.with_suffix(".md"), render_markdown(report))):
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ .md·原子写）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="warn>0 时 exit 1")
    ns = ap.parse_args(argv)
    report = build(Path(ns.root))
    if ns.write:
        write_report(Path(ns.root), report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
