#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告分镜**声画对位（see-say）**机检（advisory·出图前·编剧/分镜轴）。

传统 DRTV（直效电视广告）的核心工艺纪律："see-say"——**观众听到的每句实质卖点，
画面必须同窗给出对应视觉**。行业口径：卖点"边说边演示"的记忆留存约是"只说不演"的两倍；
反面典型叫 *radio with pictures*（配了画面的广播）——VO 在念防水/续航/实测，画面却在放
情绪空镜，镜头的钱等于白花。ad 线现有机检（copy_quality 管文案自身、shot_variety 管
视觉重复、idea_payoff 管创意→分镜兑现）都没有查**逐镜 VO↔画面是否对上**，本脚本补上。

**广告口径必须收着报**（关键词初筛·confidence=low）：
  ① 情绪 VO 铺在产品 beauty 镜上是合法手法（品牌片常态），不能一律要求逐字对画——
     只有 VO 里出现**可演示的具体卖点词**（防水/实测/成分/对比…）而画面完全没有对应物时才报。
  ② 片尾 endcard/logo/CTA/slogan 板豁免（对齐 shot_variety_audit 的有意重复豁免）；
     纯品牌口号 VO（去掉品牌名/slogan 后没剩几个字）也豁免。
  ③ 画面描述缺失的镜不判（insufficient data，不臆造声画错位）。

全 advisory：`summary.block` 恒 0（Creative heuristics stay advisory，见 ad-craft/gate.py），
gate 只把它当 warn/info 抬进报告，永不硬挡付费。

用法：
    python3 see_say_audit.py <作品根> [--write] [--json] [--strict]
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
KIND = "ad_see_say_audit"
REPORT_REL = os.path.join("生产数据", "ad_see_say_audit.json")
STORYBOARD_REL = os.path.join("脚本", "storyboard.json")
BRIEF_REL = os.path.join("需求", "brief.json")

# ── 阈值（内部启发式·env 可标定·confidence=low） ───────────────────────────────
# 实质 VO 的最小长度（去噪后字符数）：短于此视为口号/衬词，不判。
SEESAY_MIN_VO_CHARS = int(os.environ.get("AD_SEESAY_MIN_VO_CHARS", "10"))
# VO↔画面 char-2gram Jaccard 下限：低于它且具体卖点词也没出现在画面里才报。
SEESAY_SIM_FLOOR = float(os.environ.get("AD_SEESAY_SIM_FLOOR", "0.06"))
# 错位镜占比超过它（且样本 ≥3）→ 整片可能是 "radio with pictures"，聚合 info。
VO_ORPHAN_FRAC = float(os.environ.get("AD_SEESAY_ORPHAN_FRAC", "0.5"))
# 画面描述最少字符：低于此视为没写画面，不判该镜。
VISUAL_MIN_CHARS = int(os.environ.get("AD_SEESAY_VISUAL_MIN_CHARS", "4"))
# 信息态桥段 insert 覆盖：信息态 VO 句达到此数而全片零 insert 镜才报（宁缺毋滥）。
INFO_BEAT_MIN = int(os.environ.get("AD_SEESAY_INFO_BEAT_MIN", "2"))
NGRAM = 2
PROVENANCE = "internal-heuristic·confidence=low"

_NOISE_RE = re.compile(r"[\s，。！？、；：…—\-\|,.!?;:\"'“”‘’()（）\[\]【】]+")
# 豁免镜（有意重复/结构位）：与 shot_variety_audit 同口径（本线自包含，不跨文件 import）。
_EXEMPT_RE = re.compile(
    r"片尾|尾板|end.?card|endcard|收尾|logo|CTA|slogan|口号|品牌板|"
    r"产品特写|产品展示|产品beauty|beauty.?shot|hero.?shot|包装展示|卖点板|价格板|二维码|下单",
    re.IGNORECASE)
# 可演示的具体卖点词（DRTV 口径：这些词说出口，画面就必须给对应视觉）。
_CONCRETE_RE = re.compile(
    r"防水|防摔|防尘|防滑|防漏|续航|充电|快充|折叠|降噪|静音|清洁|去污|除螨|除菌|杀菌|消毒|"
    r"吸力|吸水|保湿|美白|防晒|修复|淡纹|收纳|安装|拆卸|组装|测试|实测|挑战|对比|"
    r"before|after|成分|配方|材质|面料|重量|尺寸|容量|升级|提速|加热|制冷|过滤|"
    r"耐磨|透气|拉伸|承重|一键|按下|操作|演示|倒入|涂抹|擦拭|喷洒|清洗|水洗|烹煮|烘烤|油炸|切开|切片",
    re.IGNORECASE)  # 单字动词（喷/洗/切…）是常用字子串（如"一切"），噪声太大，只收双字锚定形。
# 信息态 VO（数字/价格/参数句）与 insert 镜形态（第七轮 info_beat_no_insert 消费）。
_INFO_BEAT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|折|元|克|g|ml|mAh|小时|分钟|天|倍|档|种)|价格|参数|规格")
_INSERT_RE = re.compile(r"特写|insert|微距|close.?up|macro|UI|界面|屏幕|价格板|包装(?:特写|细节)|手部|贴脸",
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
    """去噪后的 char n-gram 集合（与本线 shot_variety/copy_quality 同法·本线自包含）。"""
    c = clean(text)
    if len(c) < n:
        return {c} if c else set()
    return {c[i:i + n] for i in range(len(c) - n + 1)}


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0


# ── storyboard / brief 解析（字段容忍：广告 storyboard schema 较薄） ──────────────

def load_json_file(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def iter_shots(storyboard: Mapping[str, Any]) -> List[Dict[str, Any]]:
    rows = storyboard.get("shots") or storyboard.get("clips") or storyboard.get("镜头") or []
    return [r for r in rows if isinstance(r, dict)]


def shot_id(shot: Mapping[str, Any], idx: int) -> str:
    return str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or f"镜头{idx + 1}")


def shot_vo(shot: Mapping[str, Any]) -> str:
    for key in ("vo", "voiceover", "voice_over", "台词", "旁白", "配音"):
        val = shot.get(key)
        if val:
            return str(val)
    return ""


def shot_visual(shot: Mapping[str, Any]) -> str:
    """画面侧文本：视觉描述 + 出场资产/实体清单（有就并入，画面里"有产品"也算对上）。"""
    parts: List[str] = []
    for key in ("shot", "frame", "画面", "主体动作", "description", "desc", "visual"):
        val = shot.get(key)
        if val:
            parts.append(str(val))
            break
    for key in ("entities", "assets", "资产", "出场资产", "主体", "props"):
        val = shot.get(key)
        if isinstance(val, (list, tuple)):
            parts.extend(str(x) for x in val if x)
        elif val:
            parts.append(str(val))
    return " ".join(parts)


def is_exempt(shot: Mapping[str, Any]) -> bool:
    """有意重复/结构位镜（片尾/logo/CTA/产品 beauty…）——声画对位不判。"""
    blob = " ".join(str(shot.get(k) or "") for k in
                    ("shot_type", "scene", "场景", "shot", "frame", "画面", "section", "role", "purpose"))
    if shot.get("endcard") or shot.get("is_endcard") or shot.get("is_hero") or shot.get("hero_product"):
        return True
    return bool(_EXEMPT_RE.search(blob))


def brand_tokens(root: Path) -> List[str]:
    """从 brief.json 取品牌/产品/slogan 词（产品名出现在 VO 里也算具体卖点词）。"""
    brief = load_json_file(root / BRIEF_REL) or {}
    out: List[str] = []
    for key in ("brand", "product", "品牌", "产品"):
        val = clean(str(brief.get(key) or ""))
        if len(val) >= 2:
            out.append(val)
    return out


def slogan_tokens(root: Path) -> List[str]:
    brief = load_json_file(root / BRIEF_REL) or {}
    out: List[str] = []
    for key in ("slogan", "tagline", "口号", "brand", "品牌"):
        val = clean(str(brief.get(key) or ""))
        if len(val) >= 2:
            out.append(val)
    return out


def concrete_hits(vo: str, tokens: Sequence[str]) -> List[str]:
    """VO 里的可演示卖点词：正则命中 + brief 品牌/产品名命中，去重保序。"""
    c = clean(vo)
    hits = [m.group(0) for m in _CONCRETE_RE.finditer(c)]
    hits += [t for t in tokens if t and t in c]
    seen: Set[str] = set()
    out = []
    for h in hits:
        key = h.lower()
        if key not in seen:
            seen.add(key)
            out.append(h)
    return out


def is_pure_brand_vo(vo: str, slogans: Sequence[str]) -> bool:
    """纯品牌口号 VO：去掉品牌名/slogan 后剩不下实质内容 → 豁免（品牌片合法手法）。"""
    c = clean(vo)
    for t in slogans:
        if t:
            c = c.replace(t, "")
    return len(c) < SEESAY_MIN_VO_CHARS


# ── 信号 ─────────────────────────────────────────────────────────────────────

def audit_see_say(shots: List[Tuple[str, Dict[str, Any]]], root: Path,
                  findings: List[Dict[str, Any]]) -> Dict[str, int]:
    tokens = brand_tokens(root)
    slogans = slogan_tokens(root)
    vo_shots = 0
    eligible = 0
    mismatches: List[Tuple[float, str, str, List[str]]] = []  # (sim, sid, vo摘, missing tokens)
    for sid, shot in shots:
        vo = shot_vo(shot)
        if not clean(vo):
            continue
        vo_shots += 1
        if is_exempt(shot):
            continue
        if len(clean(vo)) < SEESAY_MIN_VO_CHARS or is_pure_brand_vo(vo, slogans):
            continue
        visual = shot_visual(shot)
        if len(clean(visual)) < VISUAL_MIN_CHARS:
            continue  # 画面没写：insufficient data，不臆造错位
        hits = concrete_hits(vo, tokens)
        if not hits:
            continue  # 情绪/氛围 VO：合法，不要求逐字对画
        visual_clean = clean(visual).lower()
        shown = [h for h in hits if h.lower() in visual_clean]
        if shown:
            eligible += 1
            continue
        sim = jaccard(shingles(vo), shingles(visual))
        eligible += 1
        if sim < SEESAY_SIM_FLOOR:
            mismatches.append((sim, sid, str(vo)[:18], hits[:4]))
            findings.append(finding(
                "warn", "see_say_mismatch",
                f"{sid} 的 VO 在说具体卖点（{'、'.join(hits[:4])}）但画面『{clean(visual)[:18]}』"
                f"没有对应视觉（相似度 {sim:.0%}）——DRTV 纪律：说到就要演到，"
                "改画面演示该卖点，或把这句 VO 挪到有对应画面的镜（advisory·关键词初筛）",
                [sid]))
    # ── 信息态桥段 insert 覆盖（2026-07 第七轮·信息态非人物特写覆盖）────
    # VO 里的数字/价格/参数/功能句是"信息态桥段"——该给专属 insert 特写（UI/包装/价格板/
    # 演示手部），而不是叠在人物镜里念完拉倒。判据：信息态 VO 句 ≥2 而全片没有任何一镜
    # 是 insert/特写形态 → warn（豁免镜也算 insert——产品特写正是 insert 的典型形态）。
    info_beats = [vo for _sid2, shot2 in shots
                  for vo in [shot_vo(shot2)]
                  if vo and (_INFO_BEAT_RE.search(vo) or concrete_hits(vo, tokens))]
    has_insert = any(_INSERT_RE.search(
        " ".join(str(s.get(k) or "") for k in ("shot", "frame", "画面", "shot_type", "景别", "prompt")))
        for _sid2, s in shots)
    if len(info_beats) >= INFO_BEAT_MIN and not has_insert:
        findings.append(finding(
            "warn", "info_beat_no_insert",
            f"VO 有 {len(info_beats)} 句信息态内容（数字/价格/参数/可演示卖点）但全片没有一镜是"
            "insert/特写形态（UI 特写/包装特写/价格板/演示手部）——信息态桥段叠在人物镜里念完"
            "＝观众看脸没看货；给关键信息各切一个专属 insert（advisory·关键词初筛）"))

    if eligible >= 3 and len(mismatches) / eligible > VO_ORPHAN_FRAC:
        worst = sorted(mismatches)[:3]
        findings.append(finding(
            "info", "vo_visual_ratio",
            f"{eligible} 个实质 VO 镜里 {len(mismatches)} 个声画错位（>{VO_ORPHAN_FRAC:.0%}）——"
            "整片接近 radio with pictures（配画面的广播），建议整体重排声画对位；最错位的镜："
            + "、".join(sid for _s, sid, _v, _h in worst),
            [sid for _s, sid, _v, _h in worst]))
    return {"vo_shots": vo_shots, "eligible_shots": eligible, "mismatch_shots": len(mismatches)}


def build(root: Path) -> Dict[str, Any]:
    """契约形状（findings 用 `msg` 键，ad gate 可直接消费）：

        {"schema_version":1,"kind":"ad_see_say_audit","available":bool,
         "summary":{"block":0,"warn","info"},"findings":[{"severity","code","msg"}]}

    `summary.block` 恒为 0——advisory 纪律。"""
    root = Path(root)
    storyboard = load_json_file(root / STORYBOARD_REL)
    findings: List[Dict[str, Any]] = []
    available = isinstance(storyboard, dict)
    shots: List[Tuple[str, Dict[str, Any]]] = []
    stats = {"vo_shots": 0, "eligible_shots": 0, "mismatch_shots": 0}

    if not available:
        findings.append(finding("warn", "storyboard_missing",
                                "缺 脚本/storyboard.json——没有分镜可审声画对位（insufficient_data，"
                                "不代表分镜没问题）。配音后跑 ad-script 分镜 pass 产出 storyboard.json。"))
    else:
        raw = iter_shots(storyboard)
        shots = [(shot_id(s, i), s) for i, s in enumerate(raw)]
        if not shots:
            findings.append(finding("warn", "storyboard_empty",
                                    "storyboard.json 存在但没有 shots——分镜还没落档。"))
        else:
            stats = audit_see_say(shots, root, findings)
            if stats["vo_shots"] == 0:
                findings.append(finding("info", "no_vo_data",
                                        "分镜里没有任何 VO 字段——声画对位无从判起（insufficient_data，"
                                        "不代表声画没问题）。分镜 pass 回填逐镜 VO 后重跑。"))

    return {
        "schema_version": VERSION,
        "kind": KIND,
        "available": available,
        "project_root": str(root),
        "generated_at": now_iso(),
        "thresholds": {
            "min_vo_chars": SEESAY_MIN_VO_CHARS, "sim_floor": SEESAY_SIM_FLOOR,
            "orphan_frac": VO_ORPHAN_FRAC, "visual_min_chars": VISUAL_MIN_CHARS,
            "ngram": NGRAM, "provenance": PROVENANCE,
            "note": "advisory：本检永不产 block。情绪 VO 铺产品 beauty 镜合法；只有 VO 出现可演示"
                    "卖点词而画面无对应物才报。片尾/logo/CTA/纯口号 VO 已豁免；画面缺描述的镜不判。",
        },
        "inputs": {
            "shots": len(shots),
            "exempt_shots": sum(1 for _sid, s in shots if is_exempt(s)),
            **stats,
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
    lines = ["# 广告分镜声画对位（see-say）机检", ""]
    if not report.get("available"):
        lines += ["- ⚠️ 未找到 `脚本/storyboard.json`（available=false·降级为建议，不阻断）", ""]
    lines += [f"- 分镜 {i.get('shots')} 镜 · VO 镜 {i.get('vo_shots')} · 参检 {i.get('eligible_shots')}"
              f" · 错位 {i.get('mismatch_shots')} · 豁免 {i.get('exempt_shots')} 镜",
              f"- warn {s.get('warn')} · info {s.get('info')}（advisory：本检不产 block）", ""]
    icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 未检出声画错位（说到即演到；好不好看仍需人判）")
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
