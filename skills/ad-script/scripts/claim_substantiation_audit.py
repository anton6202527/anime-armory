#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告**承诺-证据配对**预检（advisory·出图前·编剧/合规轴增量）。

广告法硬闸（ad_law_check）管**绝对化用语**等词面红线；本审计补的是平台/监管高频拒因里
"承诺句必须配证据/免责"的**配对**纪律（TikTok/Meta 官方拒审原因、FTC 16 CFR Part 255
2023 修订、《广告法》38 条、《价格法》划线价七日口径、价格欺诈认定行规）：

  ① testimonial_needs_disclaimer  证言形态（"我用了/亲测/自从用了…"）出现——本线人物是
     AI 生成的**非真实使用者**，FTC "actual consumer" 与广告法 38 条双双踩线；必须在
     supers/legal_lines 配"情景演绎/非真实用户体验"免责行，缺=warn。
  ② results_claim_no_disclosure   结果承诺句（"28天瘦8斤/提升30%"）——FTC 2023 已废除
     "results not typical" 万能免责，非典型结果必须披露一般可预期结果或试验依据；
     legal_lines 无 依据/报告/因人而异 类披露=warn。
  ③ price_math_mismatch           折扣算术硬对账（"原价199 现价139 说5折"→139/199=7折）
     ——价格欺诈认定的确定性子集，纯算术零假阳性。
  ④ strikethrough_price_no_basis  出现划线价/原价但无价格依据说明（七日最低价/吊牌价/
     指导价）——《价格法》行规：划线价无说明即视为原价主张，最高频电商处罚项。
  ⑤ urgency_no_substantiation     紧迫话术（限时/最后一天/仅剩N件）无兑现依据（截止日期/
     库存来源）——平台明文拒因"limited time 与落地页不符"。
  ⑥ induce_click_reject           诱导点击词（点击有惊喜/恭喜获奖）——平台明文拒审词，
     投前预检。

**审不是门**（与 creative_axis 同档）：这些判定大多依赖"字段/免责行是否存在"，旧项目
没这些声明会整片报警——所以恒 advisory，`summary.block` 恒 0；真要硬挡由人把结论抄进
ad_law_check 的流程走。扫描范围只限 VO/supers/legal_lines/CTA（卖点语域），不碰剧情台词。

用法：
    python3 claim_substantiation_audit.py <作品根> [--write] [--json] [--strict]
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
KIND = "ad_claim_substantiation_audit"
REPORT_REL = os.path.join("生产数据", "ad_claim_substantiation_audit.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")
VOICEOVER_REL = os.path.join("脚本", "voiceover.txt")
SCRIPT_MD_REL = os.path.join("脚本", "广告脚本.md")

PROVENANCE = "internal-heuristic·confidence=low"
# 折扣算术容差（"5折"对 0.45-0.55 都算对；超出 ±此值才报）。
PRICE_TOL = float(os.environ.get("AD_CLAIM_PRICE_TOL", "0.5"))

# ── 词表（确定性形态·全部收窄到卖点语域高置信形）─────────────────────────────
_TESTIMONIAL_RE = re.compile(
    r"我(?:自己)?(?:一直)?(?:在)?用了?|亲测|亲身(?:体验|试用)|自从用了|我家(?:一直|都)用|"
    r"用了[一两三四五六七八九十\d]+(?:天|周|个月)|真实(?:用户|体验)")
_DISCLAIMER_RE = re.compile(
    r"情景演绎|演绎(?:内容|示意)|广告创意|非真实(?:用户|体验|案例)|效果因人而异|"
    r"AI\s*(?:生成|合成)|虚拟(?:人物|形象)|艺术(?:演绎|加工)", re.IGNORECASE)
_RESULTS_RE = re.compile(
    r"[\d一两三四五六七八九十]+(?:天|周|个月)(?:内)?[^。！？\n]{0,8}?"
    r"(?:瘦|减|降|白|淡化|去除|修复|见效|提升|改善)|"
    r"(?:提升|降低|减少|节省|提速)\s*[\d.]+\s*%")
_DISCLOSURE_RE = re.compile(
    r"依据|试验|实验|检测报告|测试报告|临床|数据来源|因人而异|个体差异|"
    r"具体以(?:实际|产品)|详见|见(?:官网|详情)")
_URGENCY_RE = re.compile(
    r"限时|最后[一两三\d]+天|仅剩\s*[\d一两三四五六七八九十]+|售完不补|错过(?:再无|不再)|"
    r"今日(?:截止|最后)|马上抢|手慢无")
_URGENCY_BASIS_RE = re.compile(
    r"截止|活动时间|至\s*\d+\s*月\s*\d+|有效期|库存|限量\s*\d+|以(?:平台|页面)(?:公示|显示)为准")
_INDUCE_RE = re.compile(r"点击(?:有|领)(?:惊喜|好礼|奖)|恭喜(?:你)?(?:获|中)奖|免费领取(?:!|！)?限")
_PRICE_PAIR_RE = re.compile(
    r"(?:原价|划线价|门市价|日常价|吊牌价)\s*[¥￥]?\s*(\d+(?:\.\d+)?)"
    r"[^\d。！？\n]{0,20}?(?:现价|券后|到手|活动价|特价|仅需|只要)\s*[¥￥]?\s*(\d+(?:\.\d+)?)")
_DISCOUNT_RE = re.compile(r"([\d.]+)\s*折")
_PRICE_BASIS_RE = re.compile(r"七日|7\s*日|吊牌价|指导价|厂商建议|历史(?:成交)?价|价格说明")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, shots: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    if shots:
        out["shots"] = list(shots)
    return out


def load_json_file(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def gather_copy(root: Path) -> Tuple[str, str]:
    """(卖点语域正文, 免责/法务语域正文)。

    卖点语域 = VO + supers/字幕/CTA + 脚本 md；免责语域 = storyboard legal_lines +
    supers（免责常烧在字幕行里）。剧情台词广告里几乎不存在，不单独区分。"""
    storyboard = load_json_file(root / STORYBOARD_REL) or {}
    copy_parts: List[str] = [read_text(root / VOICEOVER_REL), read_text(root / SCRIPT_MD_REL)]
    legal_parts: List[str] = []
    rows = storyboard.get("shots") or storyboard.get("clips") or storyboard.get("镜头") or []
    for shot in rows:
        if not isinstance(shot, dict):
            continue
        for key in ("vo", "voiceover", "台词", "旁白", "supers", "super", "字幕", "cta", "CTA", "subtitle"):
            val = shot.get(key)
            if val:
                copy_parts.append(str(val))
        for key in ("legal_lines", "legal", "免责", "法律声明", "disclaimer"):
            val = shot.get(key)
            if isinstance(val, (list, tuple)):
                legal_parts.extend(str(x) for x in val if x)
            elif val:
                legal_parts.append(str(val))
    # supers 也算免责载体（免责行常直接写成字幕）。
    legal_parts.extend(p for p in copy_parts[2:] if p)
    return "\n".join(p for p in copy_parts if p), "\n".join(p for p in legal_parts if p)


def price_math_issues(text: str) -> List[str]:
    """折扣算术不符/现价高于原价：纯算术，零 LLM。返回问题描述列表。纯函数·可测。"""
    issues: List[str] = []
    pairs = [(float(a), float(b)) for a, b in _PRICE_PAIR_RE.findall(text or "")]
    discounts = [float(d) for d in _DISCOUNT_RE.findall(text or "") if 0 < float(d) < 10]
    for p0, p1 in pairs:
        if p0 <= 0:
            continue
        if p1 > p0:
            issues.append(f"现价 {p1:g} 高于原价 {p0:g}——先涨后降/标错，必查")
            continue
        real = p1 / p0 * 10
        for d in discounts:
            if abs(real - d) > PRICE_TOL:
                issues.append(f"标称 {d:g}折 但 {p1:g}/{p0:g} 实为 {real:.1f}折（容差 ±{PRICE_TOL:g}）")
    return issues


def audit(root: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    copy, legal = gather_copy(root)
    findings: List[Dict[str, Any]] = []
    stats = {"copy_chars": len(copy), "testimonial_hits": 0, "results_hits": 0,
             "price_pairs": len(_PRICE_PAIR_RE.findall(copy)), "urgency_hits": 0}
    if len(copy.strip()) < 10:
        return [finding("info", "no_copy_data",
                        "VO/supers/脚本文案为空——承诺-证据配对无从判起（insufficient_data）。")], stats

    t_hits = _TESTIMONIAL_RE.findall(copy)
    stats["testimonial_hits"] = len(t_hits)
    if t_hits and not _DISCLAIMER_RE.search(legal):
        findings.append(finding(
            "warn", "testimonial_needs_disclaimer",
            f"文案含证言形态（{'、'.join(sorted(set(t_hits))[:3])}）但全片无演绎/非真实用户免责行——"
            "本线人物是 AI 生成的非真实使用者：FTC actual-consumer 与《广告法》38 条双红线；"
            "supers/legal_lines 加「情景演绎，非真实用户体验」，或把证言改为第三人称卖点句"
            f"（{PROVENANCE}）"))

    r_hits = _RESULTS_RE.findall(copy)
    stats["results_hits"] = len(r_hits)
    if r_hits and not _DISCLOSURE_RE.search(legal):
        findings.append(finding(
            "warn", "results_claim_no_disclosure",
            f"文案含 {len(r_hits)} 处结果承诺句（数字+周期+效果）但无试验依据/一般可预期结果披露——"
            "FTC 2023 已废除 results-not-typical 万能免责；补「依据：XX 测试报告」或"
            "「效果因人而异+一般可预期结果」披露行，且停留时长要过字数换算闸"
            f"（{PROVENANCE}）"))

    for issue in price_math_issues(copy):
        findings.append(finding("warn", "price_math_mismatch",
                                f"价格算术不符：{issue}——价格欺诈认定的确定性子集，投放必被拒/罚，先改数"))
    if _PRICE_PAIR_RE.search(copy) and not _PRICE_BASIS_RE.search(copy + legal):
        findings.append(finding(
            "warn", "strikethrough_price_no_basis",
            "出现划线价/原价对比但无价格依据说明——《价格法》行规：原价=促销前七日内最低成交价，"
            "无说明的划线价即原价主张（最高频电商处罚项）；补「原价为七日内最低成交价」类依据行"))

    u_hits = _URGENCY_RE.findall(copy)
    stats["urgency_hits"] = len(u_hits)
    if u_hits and not _URGENCY_BASIS_RE.search(copy + legal):
        findings.append(finding(
            "warn", "urgency_no_substantiation",
            f"紧迫话术（{'、'.join(sorted(set(u_hits))[:3])}）无兑现依据——平台明文拒因"
            "「limited time 与落地页不符」；补截止日期/库存来源，或删紧迫话术"))

    i_hits = _INDUCE_RE.findall(copy)
    if i_hits:
        findings.append(finding(
            "warn", "induce_click_reject",
            f"诱导点击词（{'、'.join(sorted(set(i_hits))[:3])}）——平台明文拒审词（抖音/TikTok 审核规范），"
            "投前必删；奖励机制真实存在也要改为明示规则"))
    return findings, stats


def build(root: Path) -> Dict[str, Any]:
    root = Path(root)
    available = (root / STORYBOARD_REL).is_file() or (root / VOICEOVER_REL).is_file() \
        or (root / SCRIPT_MD_REL).is_file()
    if available:
        findings, stats = audit(root)
    else:
        findings = [finding("warn", "no_script_artifacts",
                            "缺 脚本/storyboard.json 与 voiceover.txt——没有文案可预检"
                            "（insufficient_data，不代表文案没问题）。")]
        stats = {}
    return {
        "schema_version": VERSION, "kind": KIND, "available": available,
        "project_root": str(root), "generated_at": now_iso(),
        "thresholds": {"price_tol": PRICE_TOL, "provenance": PROVENANCE,
                       "note": "advisory：本检永不产 block；扫描范围限 VO/supers/legal_lines 卖点语域。"
                               "配对判定依赖免责/依据行的词面存在性——结论需人工复核后走 ad_law_check 流程硬化。"},
        "inputs": stats,
        "summary": {"block": 0,
                    "warn": sum(1 for f in findings if f["severity"] == "warn"),
                    "info": sum(1 for f in findings if f["severity"] == "info")},
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = ["# 广告承诺-证据配对预检", "",
             f"- warn {s.get('warn')} · info {s.get('info')}（advisory：本检不产 block）", ""]
    icon = {"warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 未检出无证据的承诺句/价格算术错误/紧迫话术")
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
