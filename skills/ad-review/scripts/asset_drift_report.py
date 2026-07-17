#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告线·事后跨镜资产漂移报表（asset_drift_report）—— 逐资产 × 逐镜时间线。

为什么存在（真空档）：
  - `asset_consistency.py` 做 dHash 时**显式排除 PROD_/BRAND_**（只覆盖 CHAR_/LOC_/PROP_），
    且只出一个全局 `max_distance > 30` 的 warn——不知道"哪个资产从第几镜开始崩"。
  - `ad-image/scripts/product_qc.py` 覆盖产品，但只在**单批次内**做 dHash 组比对，
    **没有跨镜逐产品时间线**。
  结果：广告线最严的铁律「产品/logo/品牌色跨镜零漂移」在**跨镜聚合**维度上没有任何机器统计。
  本报表把已生成的各份机检报告汇总成 `逐资产 × 逐镜` 的 ok/warn/block/noevidence 时间线，
  标出 `first_bad_shot`（第几镜开始崩）、跨镜连崩镜数，并按广告口径给修复建议与优先级。

设计铁律：
  - **纯标准库·零像素**：只聚合已有报告，不开图、不算距离、不依赖 Pillow。
    因此不存在"缺 Pillow 输出假距离"的风险；精度完全继承上游报告。
  - **ad 线自包含**：不 import 其他系列任何模块，全部结构均在本线重实现。同目录 sibling import 允许。
  - **advisory 不是 gate·默认绝不产 block**：`consistency_findings.py:195` 把 severity **直通**给
    总账，`review.py:139-158` 见 block 即硬阻断——本报表一旦产 block 就等于把一个启发式聚合
    变成真实发布阻断。故 findings **只允许 warn/info，`summary.block` 恒为 0**；
    最严重的「产品资产跨镜连崩」也只出 **warn**，把紧迫度写进 msg/priority 而非 severity。
    默认 exit 0；`--strict` 只影响**退出码**（有 warn 则 1），不改任何 finding 的 severity。
  - 广告**不拆集**：粒度只有镜头 shot，不引入集/话概念。

证据来源（只读）：
  - `脚本/storyboard.json`            → 资产全集 + 镜序（shots[].assets，含 PROD_/BRAND_/CHAR_/LOC_/PROP_）
  - `设定库/asset_registry.json`      → registered 标记（fallback `出图/共享/asset_registry.json`）
  - `出图/分镜/product_qc.json`       → per-shot findings（schema：severity/shot/check/reason/detail）
  - `生产数据/asset_consistency.json` → per-shot findings（schema：severity/asset_id/shot/code/msg）

schema 键选择（接线用·必读）：
  build() 的 findings **以 `msg` 为准**（与 asset_consistency/voice_consistency 及 ad gate 一致，
  也正是 `consistency_findings.py:195` 消费 sibling build() 的键），并给 `code`。
  为兼容 `consistency_findings.py:151` 那条 `item.get("reason") or item.get("msg")` 的读法，
  额外冗余一个**同值** `message` 键；但**权威键是 `msg`**。

诚实边界：
  - **本报表是"审"不是"门"**：跨镜漂移聚合是启发式（归位规则 + 上游报告的严重度），
    不足以承担硬阻断。默认 findings 只出 warn/info，`summary.block` 恒为 0。
    广告线真正的硬闸仍是 `product_qc` 的 prompt-lint 与 provenance（参考图/reference_inputs 证据链），
    本报表不取代、也不重复它们。
  - `noevidence` ≠ `ok`。只有该镜确实在上游报告里留下了针对该资产的记录，才算"跑过"；
    上游对**完全干净的镜头不留痕**，这类镜头会诚实标为 noevidence 而不是 ok（缺证据不算通过）。
  - 本报表**不重算像素**，不会发现上游没发现的漂移；它只回答"崩在哪、从第几镜起、要不要回定妆库"。

用法：
    python3 asset_drift_report.py <作品根> [--write] [--json] [--strict]
    # --write 落 生产数据/asset_drift_report.json + .md（原子写：同盘 temp + os.replace）

测试（从本目录跑）：
    cd skills/ad-review/scripts && python3 -m pytest test_asset_drift_report.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

VERSION = 1
KIND = "ad_asset_drift_report"

# 与 asset_consistency.ASSET_RE 同构（刻意重复一行常量而非 import，保持本模块可独立测试）。
ASSET_RE = re.compile(r"\b(?:CHAR|LOC|PROP|BRAND|PROD)_[A-Za-z0-9_]+\b")

# 产品/品牌资产：广告铁律最严的一档，崩了整片报废。
CRITICAL_PREFIXES = ("PROD_", "BRAND_")

_SEV_RANK = {"ok": 0, "info": 0, "warn": 1, "block": 2}
_RANK_SEV = {0: "ok", 1: "warn", 2: "block"}

SEVERITIES = ("block", "warn", "info")
# 本报表自己产出的 findings 只允许这两档——block 会经 consistency_findings → review 变成硬阻断。
ADVISORY_SEVERITIES = ("warn", "info")


# ── 纯函数（无 IO·可测） ─────────────────────────────────────────────────────

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def shot_num(value: str) -> Optional[int]:
    m = re.search(r"\d+", str(value or ""))
    return int(m.group()) if m else None


def shot_label(shot: Mapping[str, Any], index: int) -> str:
    """与 asset_consistency.shot_label 同构：镜头NN。"""
    raw = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or "")
    m = re.search(r"\d+", raw)
    return f"镜头{int(m.group()):02d}" if m else f"镜头{index:02d}"


def shot_assets(shot: Mapping[str, Any]) -> List[str]:
    """与 asset_consistency.assets 同构，但返回有序 list（报表要稳定顺序）。"""
    value = shot.get("assets")
    out: List[str] = []
    if isinstance(value, dict):
        out = [str(k) for k, v in value.items() if v and ASSET_RE.fullmatch(str(k))]
    elif isinstance(value, list):
        out = [str(v) for v in value if ASSET_RE.fullmatch(str(v))]
    return sorted(set(out))


def asset_kind(asset_id: str) -> str:
    head = str(asset_id).split("_", 1)[0]
    return head.lower() if head else "unknown"


def is_critical(asset_id: str) -> bool:
    return str(asset_id).startswith(CRITICAL_PREFIXES)


def norm_severity(value: Any, default: str = "info") -> str:
    sev = str(value or "").strip().lower()
    return sev if sev in _SEV_RANK else default


def check_name(item: Mapping[str, Any]) -> str:
    """product_qc 用 `check`，asset_consistency 用 `code`——统一成一个 check 名。"""
    return str(item.get("check") or item.get("code") or "unknown_check").strip() or "unknown_check"


def check_reason(item: Mapping[str, Any]) -> str:
    return str(item.get("reason") or item.get("msg") or item.get("message") or "").strip()


def worst_of(checks: Sequence[Mapping[str, Any]]) -> str:
    rank = max((_SEV_RANK.get(norm_severity(c.get("severity")), 0) for c in checks), default=0)
    return _RANK_SEV[rank]


def pick_worst_check(timeline: Sequence[Mapping[str, Any]],
                     asset_checks: Sequence[Mapping[str, Any]]) -> Optional[str]:
    """最严重（并列时最高频，再并列时字典序）的 check 名。纯函数·可测。"""
    tally: Dict[str, List[int]] = {}
    flat: List[Mapping[str, Any]] = list(asset_checks)
    for row in timeline:
        flat.extend(row.get("checks") or [])
    for item in flat:
        rank = _SEV_RANK.get(norm_severity(item.get("severity")), 0)
        if rank < 1:
            continue
        name = check_name(item)
        entry = tally.setdefault(name, [0, 0])
        entry[0] = max(entry[0], rank)
        entry[1] += 1
    if not tally:
        return None
    return sorted(tally.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]))[0][0]


def recommend(asset_id: str, bad_shots: Sequence[str], block_shots: Sequence[str],
              worst_check: Optional[str]) -> Dict[str, Any]:
    """广告口径的修复建议分类。纯函数·可测。

    - 产品/品牌资产崩 → P0（整片报废风险），无论只崩一镜。
    - 同一资产多镜连崩 → 回定妆库/registry 修根因，别只重抽单图。
    - 单镜孤立崩 → 只重抽该镜，先不升重资产。
    """
    if not bad_shots:
        return {"priority": None, "action": None, "recommendation": None}
    tail = f"（worst_check={worst_check}）" if worst_check else ""
    shots_txt = "、".join(bad_shots)
    critical = is_critical(asset_id)
    multi = len(bad_shots) >= 2

    if critical and multi:
        return {
            "priority": "P0",
            "action": "reground_registry",
            "recommendation": (
                f"{asset_id}：产品/品牌资产跨 {len(bad_shots)} 镜连崩（{shots_txt}）{tail}——"
                "**整片报废风险，最高优先级**。根因在参考侧不在单图：回 设定库/asset_registry 复核并重登记"
                "包装正/侧/背 + logo 特写定妆图、品牌 HEX、logo mask/保护区、包装文字禁改项，"
                "重建产品镜 image-to-image 参考输入后**整组重抽**，不要只重抽个别镜。"
            ),
        }
    if critical:
        return {
            "priority": "P0",
            "action": "rerun_shot",
            "recommendation": (
                f"{asset_id}：产品/品牌资产在 {shots_txt} 单镜漂移{tail}——"
                "**整片报废风险，最高优先级**，但目前是孤立镜：带真实定妆参考图重抽该镜并复跑 product_qc；"
                "若重抽后仍崩，按跨镜连崩处理回定妆库/registry。"
            ),
        }
    if multi:
        return {
            "priority": "P1",
            "action": "reground_registry",
            "recommendation": (
                f"{asset_id}：跨 {len(bad_shots)} 镜反复漂移（{shots_txt}）{tail}——"
                "单镜重抽治不了根：回 设定库/asset_registry 补该资产的多视图定妆与绝不清单，"
                "重建出图包后重抽全部受影响镜。"
            ),
        }
    return {
        "priority": "P2",
        "action": "rerun_shot",
        "recommendation": (
            f"{asset_id}：仅 {shots_txt} 单镜孤立漂移{tail}——"
            "按该镜上游报告的证据重抽该镜即可，先不升重资产。"
        ),
    }


def attribute_shot_finding(item: Mapping[str, Any], assets_in_shot: Sequence[str]) -> List[str]:
    """把一条 per-shot finding 归位到该镜的哪些资产上。纯函数·可测。

    优先级：finding 文本/detail 里点名的资产 > 该镜的产品/品牌资产 > 该镜全部资产。
    （product_qc 的 findings 只带 shot 不带 asset_id，必须靠这套归位规则。）
    """
    if not assets_in_shot:
        return []
    named = str(item.get("asset_id") or "").strip()
    if named:
        return [named] if named in assets_in_shot else []
    try:
        blob = json.dumps(item, ensure_ascii=False, default=str)
    except Exception:
        blob = check_reason(item)
    hits = [a for a in assets_in_shot if a in set(ASSET_RE.findall(blob))]
    if hits:
        return hits
    critical = [a for a in assets_in_shot if is_critical(a)]
    return critical or list(assets_in_shot)


def build_timeline(shots: Sequence[str],
                   assets_by_shot: Mapping[str, Sequence[str]],
                   evidence: Mapping[str, Mapping[str, List[Dict[str, Any]]]],
                   asset_level: Mapping[str, List[Dict[str, Any]]],
                   registered: Iterable[str]) -> List[Dict[str, Any]]:
    """(镜序, 逐镜资产, 逐镜逐资产证据, 资产级证据) → 逐资产行。纯函数·可测。"""
    registered_ids = set(registered)
    universe: Dict[str, List[str]] = {}
    for shot in shots:
        for aid in assets_by_shot.get(shot) or []:
            universe.setdefault(aid, []).append(shot)

    rows: List[Dict[str, Any]] = []
    for aid in sorted(universe):
        appeared = universe[aid]
        timeline: List[Dict[str, Any]] = []
        for shot in appeared:
            checks = list((evidence.get(shot) or {}).get(aid) or [])
            status = worst_of(checks) if checks else "noevidence"
            timeline.append({"shot": shot, "status": status, "checks": checks})
        bad = [r["shot"] for r in timeline if r["status"] in ("warn", "block")]
        blocks = [r["shot"] for r in timeline if r["status"] == "block"]
        noev = [r["shot"] for r in timeline if r["status"] == "noevidence"]
        a_checks = list(asset_level.get(aid) or [])
        worst = pick_worst_check(timeline, a_checks)
        rec = recommend(aid, bad, blocks, worst)
        rows.append({
            "asset_id": aid,
            "kind": asset_kind(aid),
            "critical": is_critical(aid),
            "registered": aid in registered_ids,
            "appeared_shots": appeared,
            "timeline": timeline,
            "first_bad_shot": bad[0] if bad else None,
            "bad_shot_count": len(bad),
            "bad_shots": bad,
            "block_shots": blocks,
            "noevidence_shots": noev,
            "asset_checks": a_checks,
            "worst_check": worst,
            "worst_status": worst_of([{"severity": r["status"]} for r in timeline] + a_checks)
            if timeline or a_checks else "noevidence",
            **rec,
        })
    return rows


def finding(severity: str, code: str, msg: str, asset: str = "",
            shot: str = "", detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """findings 条目。权威键是 `msg`；`message` 是同值冗余（见 docstring 的 schema 键选择）。

    severity 被**强制降到 advisory 档**：本报表绝不产 block（block 会经 consistency_findings
    直通到 review 变成硬阻断）。紧迫度请读 detail.priority，不要读 severity。
    """
    sev = severity if severity in ADVISORY_SEVERITIES else ("warn" if severity == "block" else "info")
    return {
        "severity": sev,
        "code": code,
        "msg": msg,
        "message": msg,
        "asset": asset,
        "shot": shot,
        "detail": detail or {},
    }


def rows_to_findings(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """逐资产行 → findings。**只出 warn/info**；紧迫度走 priority 而非 severity。纯函数·可测。

    上游证据里的 block 不会被原样透传成 block finding——它体现为 detail.evidence_severity
    与 msg 里的措辞，severity 仍是 warn。硬闸留给 product_qc。
    """
    out: List[Dict[str, Any]] = []
    for row in rows:
        aid = row["asset_id"]
        base = {"priority": row.get("priority"), "action": row.get("action"),
                "worst_check": row.get("worst_check"), "bad_shots": row.get("bad_shots"),
                "block_shots": row.get("block_shots"),
                "evidence_severity": "block" if row["block_shots"] else ("warn" if row["bad_shots"] else "ok"),
                "recommendation": row.get("recommendation")}
        if row["bad_shots"]:
            heat = (f"上游证据已达 block（{'、'.join(row['block_shots'])}）"
                    if row["block_shots"] else "上游证据为 warn")
            out.append(finding(
                "warn", "asset_cross_shot_drift",
                f"[{row.get('priority')}] {aid} 跨 {row['bad_shot_count']} 镜漂移"
                f"（{'、'.join(row['bad_shots'])}）；首崩 {row['first_bad_shot']}；{heat}；"
                f"{row.get('recommendation')}（本条为 advisory 聚合，不作硬阻断——"
                "硬闸以 product_qc 的 prompt-lint/provenance 为准）",
                aid, row["first_bad_shot"] or "", dict(base)))
        if row["noevidence_shots"]:
            out.append(finding(
                "info", "asset_shot_no_evidence",
                f"{aid} 有 {len(row['noevidence_shots'])} 镜没有任何机检证据"
                f"（{ '、'.join(row['noevidence_shots']) }）——缺证据不算通过，需补跑 product_qc/"
                "asset_consistency 或人工并排签收。",
                aid, "", {"noevidence_shots": row["noevidence_shots"]}))
        if not row["registered"]:
            out.append(finding(
                "warn", "asset_not_in_registry",
                f"{aid} 出现在 storyboard 但未在 asset_registry 登记——跨镜零漂移没有参照物。",
                aid, "", {}))
    return out


def summarize(findings: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    out = {key: 0 for key in SEVERITIES}
    for item in findings:
        sev = item.get("severity")
        if sev in out:
            out[sev] += 1
    return out


# ── IO ────────────────────────────────────────────────────────────────────────

def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def registry_ids(root: Path) -> tuple:
    """(ids, source_relpath)。设定库 优先，fallback 出图/共享。"""
    for rel in ("设定库/asset_registry.json", "出图/共享/asset_registry.json"):
        data = load_json(root / rel)
        if data is not None:
            try:
                blob = json.dumps(data, ensure_ascii=False, default=str)
            except Exception:
                blob = ""
            return set(ASSET_RE.findall(blob)), rel
    return set(), ""


def collect_evidence(root: Path, assets_by_shot: Mapping[str, Sequence[str]]):
    """读上游报告 → (逐镜逐资产证据, 资产级证据, sources, notes)。"""
    evidence: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    asset_level: Dict[str, List[Dict[str, Any]]] = {}
    sources: List[str] = []
    notes: List[str] = []

    def add(shot: str, aid: str, item: Dict[str, Any]) -> None:
        evidence.setdefault(shot, {}).setdefault(aid, []).append(item)

    for rel, source in (("出图/分镜/product_qc.json", "product_qc"),
                        ("生产数据/asset_consistency.json", "asset_consistency")):
        report = load_json(root / rel)
        if not isinstance(report, Mapping):
            notes.append(f"缺 {rel}——该来源的逐镜证据为空，相关镜头只能标 noevidence。")
            continue
        sources.append(rel)
        for item in report.get("findings") or []:
            if not isinstance(item, Mapping):
                continue
            rec = {"check": check_name(item), "severity": norm_severity(item.get("severity")),
                   "reason": check_reason(item), "source": source}
            shot = str(item.get("shot") or "").strip()
            aid = str(item.get("asset_id") or "").strip()
            if shot and shot in assets_by_shot:
                for target in attribute_shot_finding(item, assets_by_shot[shot]):
                    add(shot, target, rec)
            elif aid:
                asset_level.setdefault(aid, []).append(rec)
    return evidence, asset_level, sources, notes


def build(root: Path) -> Dict[str, Any]:
    """接入契约：返回 ad_asset_drift_report。advisory·零像素·只读上游报告。"""
    root = Path(root).resolve()
    sb = load_json(root / "脚本" / "storyboard.json", {}) or {}
    raw_shots = sb.get("shots") or sb.get("clips") or []
    if not isinstance(raw_shots, list):
        raw_shots = []

    shots: List[str] = []
    assets_by_shot: Dict[str, List[str]] = {}
    for index, shot in enumerate(raw_shots, 1):
        if not isinstance(shot, Mapping):
            continue
        label = shot_label(shot, index)
        if label in assets_by_shot:  # 同标签重复镜：合并资产，保持镜序唯一
            assets_by_shot[label] = sorted(set(assets_by_shot[label]) | set(shot_assets(shot)))
            continue
        shots.append(label)
        assets_by_shot[label] = shot_assets(shot)

    reg_ids, reg_source = registry_ids(root)
    tracked = sorted({a for shot in shots for a in assets_by_shot[shot]})
    if not tracked:
        return {
            "schema_version": VERSION, "kind": KIND, "generated_at": now_iso(),
            "available": False,
            "degraded": "no_asset_universe",
            "summary": {"block": 0, "warn": 0, "info": 0, "assets_tracked": 0,
                        "shots_scanned": len(shots), "assets_with_drift": 0,
                        "assets_with_block_evidence": 0, "critical_assets_with_drift": 0,
                        "shots_with_evidence": 0},
            "shots": shots,
            "assets": [],
            "findings": [],
            "notes": ["缺 脚本/storyboard.json 或其中没有可识别的 shots[].assets——"
                      "无资产全集可追踪，跨镜漂移报表降级为不可用（不臆造通过）。"],
            "sources": [rel for rel in [reg_source] if rel],
        }

    evidence, asset_level, sources, notes = collect_evidence(root, assets_by_shot)
    rows = build_timeline(shots, assets_by_shot, evidence, asset_level, reg_ids)
    findings = rows_to_findings(rows)
    if not reg_source:
        findings.append(finding("warn", "asset_registry_missing",
                                "缺 设定库/asset_registry.json（也无 出图/共享/ fallback）——"
                                "无法核对资产是否登记。"))
    counts = summarize(findings)
    shots_with_evidence = sum(1 for shot in shots if evidence.get(shot))
    return {
        "schema_version": VERSION,
        "kind": KIND,
        "generated_at": now_iso(),
        "available": True,
        "summary": {
            **counts,
            "assets_tracked": len(rows),
            "shots_scanned": len(shots),
            "shots_with_evidence": shots_with_evidence,
            "assets_with_drift": sum(1 for r in rows if r["bad_shot_count"]),
            # 上游证据里达 block 的资产数——**不是** finding severity（本报表恒 0 block）。
            "assets_with_block_evidence": sum(1 for r in rows if r["block_shots"]),
            "critical_assets_with_drift": sum(1 for r in rows if r["critical"] and r["bad_shot_count"]),
        },
        "shots": shots,
        "assets": rows,
        "findings": findings,
        "notes": notes,
        "sources": [rel for rel in ["脚本/storyboard.json", reg_source, *sources] if rel],
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    shots = list(report.get("shots") or [])
    lines = ["# 广告跨镜资产漂移报表", "",
             f"- generated_at: {report.get('generated_at')} · available: {report.get('available')}",
             f"- 扫描 {s.get('shots_scanned', 0)} 镜（有证据 {s.get('shots_with_evidence', 0)} 镜）· "
             f"追踪 {s.get('assets_tracked', 0)} 资产 · 有漂移 {s.get('assets_with_drift', 0)} · "
             f"其中上游证据达 block {s.get('assets_with_block_evidence', 0)} · "
             f"产品/品牌漂移 {s.get('critical_assets_with_drift', 0)}",
             f"- findings — block: {s.get('block', 0)}  warn: {s.get('warn', 0)}  info: {s.get('info', 0)}",
             "",
             "> **advisory 报表，恒 0 block、绝不硬阻断**：跨镜聚合是启发式，紧迫度看优先级列（P0/P1/P2）"
             "而非 severity；硬闸以 product_qc 的 prompt-lint/provenance 为准。",
             "> `noevidence` 表示该镜没有机检证据——**缺证据不算通过**。", ""]
    icon = {"ok": "🟢", "warn": "🟡", "block": "🔴", "noevidence": "⚪"}
    rows = list(report.get("assets") or [])
    if shots and rows:
        lines.append("| 资产 | " + " | ".join(shots) + " | 首崩镜 | 崩镜数 | worst_check | 优先级 |")
        lines.append("|---|" + "---|" * (len(shots) + 4))
        for r in rows:
            by_shot = {t["shot"]: t["status"] for t in r.get("timeline") or []}
            cells = [icon.get(by_shot.get(shot, ""), "") for shot in shots]
            lines.append(
                f"| {r['asset_id']} | " + " | ".join(cells) +
                f" | {r.get('first_bad_shot') or '—'} | {r.get('bad_shot_count', 0)}"
                f" | {r.get('worst_check') or '—'} | {r.get('priority') or '—'} |")
        lines.append("")
    recs = [(r.get("priority") or "P9", r["recommendation"]) for r in rows if r.get("recommendation")]
    lines.append("## 修复建议")
    if recs:
        lines += [f"- [{p}] {text}" for p, text in sorted(recs, key=lambda kv: kv[0])]
    else:
        lines.append("- ✅ 未检出跨镜资产漂移")
    lines.append("")
    lines.append("## Findings")
    for item in report.get("findings") or []:
        lines.append(f"- [{item.get('severity')}] {item.get('code')}: {item.get('message')}")
    for note in report.get("notes") or []:
        lines.append(f"- · {note}")
    return "\n".join(lines).rstrip() + "\n"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")  # 同盘 temp
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_report(root: Path, report: Mapping[str, Any]) -> tuple:
    out_dir = Path(root) / "生产数据"
    json_path = out_dir / "asset_drift_report.json"
    md_path = out_dir / "asset_drift_report.md"
    _atomic_write(json_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(md_path, render_markdown(report))
    return json_path, md_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_root", help="作品根目录")
    ap.add_argument("--write", action="store_true",
                    help="落 生产数据/asset_drift_report.json + .md（原子写）")
    ap.add_argument("--json", action="store_true", help="打印 JSON 而非 Markdown")
    ap.add_argument("--strict", action="store_true",
                    help="有 warn 时退出码 1（默认 advisory，恒 0）；只影响退出码，不改 findings severity")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{ns.project_root}")
        return 2
    report = build(root)
    if ns.write:
        json_path, md_path = write_report(root, report)
        print(f"[ok] asset drift report JSON → {json_path}")
        print(f"[ok] asset drift report MD   → {md_path}")
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not ns.write:
        print(render_markdown(report))
    # 默认恒 0（advisory）。--strict 只改退出码：本报表不产 block，故按 warn 计。
    if ns.strict and (report["summary"]["warn"] or report["summary"]["block"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
