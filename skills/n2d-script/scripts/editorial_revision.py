#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编剧级整体改良·编辑修订工作单（生成器层）——治「像真实编剧一样整体改剧本」的缺口。

`story_spine.py` 已是整体改良的**契约层**（tangent 分类 + keep/compress/fold/cut + continuity_fixes 改
不合理点 + 主线 logline，全部防瞎编 + 衔接校验）；但它要人从空 scaffold 手填。本模块是它**上游的
生成器/提案层**：从已确认的 `设定库/source_comprehension.json`（因果链 + 伏笔账，唯一防瞎编锚）+
现有 `开发包/story_spine.json`（线程）里**机检挖出编辑信号**，产出可读工作单，把「该砍哪条琐碎支线、
哪个伏笔埋了没还、主线哪里接不上」从零起草升级成**有依据的提案**，交 AI 编剧定夺、再由 story_spine.check
做最终防瞎编 + 衔接硬校验。

只做**机械信号挖掘**（确定性、可测）；砍/改/合的**语义判断交 AI 编剧**（SKILL 指引）。四类编辑信号：
  · foreshadow_debt      —— status=open 却没有任何线程 pays_foreshadow 承接 = 埋了没还 → 改（补还）或砍设定。
  · mainline_gap         —— 因果链 must_keep 的承接点没被任何 spine 节点 depends_on 引用 = 主线可能接不上。
  · tangent_candidates   —— 贡献分低 + class∈{tangent,supporting} + decision=keep = 与主线不相干的琐碎支线，
                            提案 cut/compress（贡献分=机械信号：承载的受保护伏笔/must_keep 因果/主线依赖 + 权重）。
  · unreasonable_beats   —— 「改掉不合理的地方」的信号真空补齐：巧合/便利/天降词面(contrivance)、动机缺阻力
                            (motive_without_stakes)、力量无代价(uncosted_power_use)、前因缺失(ungrounded_cause·零重叠保守判)。
                            **只点名候选交 AI 编剧核原著**，绝不内联问 LLM「合理吗」、绝不据它瞎编加情节。

防瞎编：工作单里引用的 foreshadow/causal/thread id 必须真实存在于 source_comprehension / story_spine，
check() 核对，臆造 id → block。**只提案不改稿**（宪法 B10）；改 story_spine 决策仍由编剧确认。

用法：
  python3 editorial_revision.py <作品根> build [--write]    # 生成/刷新工作单
  python3 editorial_revision.py <作品根> check [--json]      # 校验工作单 id 真实 + 编辑债覆盖
测试：cd skills/n2d-script/scripts && python -m pytest test_editorial_revision.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_editorial_revision_worksheet"
CHECK_KIND = "n2d_editorial_revision_check"
VERSION = 1
PACK_DIR = "开发包"
WORKSHEET_FILE = "editorial_revision_worksheet.json"
COMPREHENSION_JSON = "设定库/source_comprehension.json"
SPINE_JSON = "开发包/story_spine.json"

TANGENT_CLASSES = {"tangent", "supporting"}
CUTTABLE_DECISIONS = {"keep"}  # 只对仍 keep 的低贡献支线提案精简（已决定 cut/compress 的不重复提案）
# 贡献分阈值：≤ 此分且 class∈tangent/supporting 且 decision=keep → 琐碎支线提案精简。
CONTRIBUTION_CUT_THRESHOLD = 1

# 「不合理点」机检词库（治「改掉一些不合理的地方」的信号真空）——巧合/便利/天降式便宜达成的
# 因果标记。命中=候选，交 AI 编剧核（可能是原著本有的合理铺垫，也可能真是硬伤）；绝不自动改稿。
# 收窄到「因果便利」类，不收 突然/忽然（正常叙事高频）以压误报。
CONTRIVANCE_MARKERS = (
    "恰好", "正好", "刚好", "碰巧", "正巧", "巧合", "机缘巧合", "无缘无故", "不知为何",
    "不知怎么", "凭空", "莫名其妙", "莫名地", "天降", "主角光环", "说时迟那时快",
    "轻而易举", "易如反掌", "毫不费力", "瞬间学会", "一下子就会", "自动就",
)
# 权力/系统「有代价」的标记：源理解 power_system_rules 里出现这些=世界观设定了力量有成本；
# 若某因果 effect 动用了系统/异能却整条没提代价 → 可能是「无代价力量蠕变」候选。
POWER_COST_MARKERS = ("代价", "上限", "反噬", "限制", "冷却", "副作用", "损耗", "透支", "禁忌", "后遗")
POWER_USE_MARKERS = ("系统", "百妖谱", "技能", "异能", "法术", "秘术", "神通", "妖力", "灵力", "外挂")


def _bigrams(text: str) -> set:
    s = "".join(ch for ch in str(text or "") if not ch.isspace())
    return {s[i:i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else set()


def _hit_markers(text: str, markers: Sequence[str]) -> List[str]:
    t = str(text or "")
    return [m for m in markers if m in t]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


# ── 读取（自包含·不 import 其它脚本，保持本线独立） ───────────────────────────

def load_json(path: Path) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _understanding_contract(root: Path) -> Dict[str, Any]:
    data = load_json(root / COMPREHENSION_JSON)
    uc = data.get("understanding_contract") if isinstance(data, dict) else None
    return uc if isinstance(uc, dict) else {}


def _foreshadow_ledger(root: Path) -> List[Dict[str, Any]]:
    fl = _understanding_contract(root).get("foreshadowing_ledger")
    return [r for r in fl if isinstance(r, dict)] if isinstance(fl, list) else []


def _causality_chain(root: Path) -> List[Dict[str, Any]]:
    cc = _understanding_contract(root).get("causality_chain")
    return [r for r in cc if isinstance(r, dict)] if isinstance(cc, list) else []


def _character_motives(root: Path) -> List[Dict[str, Any]]:
    cm = _understanding_contract(root).get("character_motives")
    return [r for r in cm if isinstance(r, dict)] if isinstance(cm, list) else []


def _power_system_text(root: Path) -> str:
    psr = _understanding_contract(root).get("power_system_rules")
    if isinstance(psr, str):
        return psr
    if isinstance(psr, Mapping):
        return " ".join(str(v) for v in psr.values())
    if isinstance(psr, list):
        return " ".join(json.dumps(r, ensure_ascii=False) if isinstance(r, (dict, list)) else str(r) for r in psr)
    return ""


def _spine_and_threads(root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    data = load_json(root / SPINE_JSON)
    if not isinstance(data, dict):
        return [], []
    spine = [n for n in (data.get("spine") or []) if isinstance(n, dict)]
    threads = [t for t in (data.get("threads") or []) if isinstance(t, dict)]
    return spine, threads


def _tid(row: Mapping[str, Any]) -> str:
    return str(row.get("trace_id") or row.get("id") or "").strip()


# ── 纯信号函数（可测·无 IO） ──────────────────────────────────────────────────

def foreshadow_debt(ledger: Sequence[Mapping[str, Any]], threads: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """status=open 却没有任何线程 pays_foreshadow 承接的伏笔 = 埋了没还。改（补还）或砍设定。"""
    paid: set = set()
    for t in threads:
        for fid in t.get("pays_foreshadow") or []:
            fid = str(fid).strip()
            if fid:
                paid.add(fid)
    out: List[Dict[str, Any]] = []
    for row in ledger:
        fid = _tid(row)
        status = str(row.get("status") or "").strip().lower()
        if fid and status in {"", "open", "pending", "unpaid"} and fid not in paid:
            out.append({
                "foreshadow_id": fid,
                "setup": str(row.get("setup") or ""),
                "protected": bool(str(row.get("do_not_drop_reason") or "").strip()),
                "suggestion": "补还（给主线安排回收）或砍掉设定" if not str(row.get("do_not_drop_reason") or "").strip()
                              else "受保护伏笔，必须补还回收，不能砍",
            })
    return out


def mainline_gap(chain: Sequence[Mapping[str, Any]], spine: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """因果链 must_keep 的承接点没被任何 spine 节点 depends_on 引用 = 主线可能接不上。"""
    fed: set = set()
    for n in spine:
        for dep in n.get("depends_on") or []:
            dep = str(dep).strip()
            if dep:
                fed.add(dep)
    out: List[Dict[str, Any]] = []
    for row in chain:
        cid = _tid(row)
        if cid and str(row.get("must_keep") or "").strip() and cid not in fed:
            out.append({
                "causal_id": cid,
                "cause": str(row.get("cause") or ""),
                "effect": str(row.get("effect") or ""),
                "suggestion": "把该承接点接进某个 spine 节点的 depends_on，或确认主线不依赖它",
            })
    return out


def thread_contribution(thread: Mapping[str, Any], ledger: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """线程主线贡献分（机械信号·越高越该保）。防止把承载主线的支线误判成琐碎。"""
    protected_fids = {_tid(r) for r in ledger if str(r.get("do_not_drop_reason") or "").strip()}
    pays = [str(f).strip() for f in (thread.get("pays_foreshadow") or []) if str(f).strip()]
    conn = thread.get("connectivity") if isinstance(thread.get("connectivity"), Mapping) else {}
    deps = [str(d).strip() for d in (conn.get("downstream_mainline_deps") or []) if str(d).strip()]
    cls = str(thread.get("class") or "").strip()
    weight = str(thread.get("weight") or "").strip().lower()
    score = 0
    score += 2 * len([f for f in pays if f in protected_fids])   # 承载受保护伏笔=强主线
    score += len([f for f in pays if f not in protected_fids])    # 一般伏笔回收
    score += len(deps)                                            # 承载主线因果依赖
    score += {"high": 2, "mid": 1, "low": 0}.get(weight, 0)
    if cls == "spine":
        score += 99   # 主线永不进琐碎提案
    if cls == "tangent":
        score -= 2
    return {"thread_id": thread.get("id"), "name": thread.get("name"), "class": cls,
            "decision": str(thread.get("decision") or "").strip(), "score": score,
            "pays_protected": [f for f in pays if f in protected_fids],
            "mainline_deps": deps}


def tangent_candidates(threads: Sequence[Mapping[str, Any]], ledger: Sequence[Mapping[str, Any]],
                       *, threshold: int = CONTRIBUTION_CUT_THRESHOLD) -> List[Dict[str, Any]]:
    """贡献分低 + class∈{tangent,supporting} + decision=keep = 与主线不相干的琐碎支线，提案 cut/compress。"""
    out: List[Dict[str, Any]] = []
    for t in threads:
        contrib = thread_contribution(t, ledger)
        if (contrib["class"] in TANGENT_CLASSES
                and contrib["decision"] in CUTTABLE_DECISIONS
                and contrib["score"] <= threshold):
            proposal = "cut" if contrib["score"] <= 0 and contrib["class"] == "tangent" else "compress"
            out.append({**contrib, "proposal": proposal,
                        "note": "低主线贡献的琐碎支线；提案精简以突出主情节（砍前须给 payoff_reroute/no_orphan_proof，由 story_spine.check 校验）。"})
    out.sort(key=lambda r: r["score"])  # 最该砍的排前
    return out


def unreasonable_beat_candidates(
    chain: Sequence[Mapping[str, Any]],
    motives: Sequence[Mapping[str, Any]],
    power_system_text: str,
) -> List[Dict[str, Any]]:
    """机检「不合理点」候选（治「改掉一些不合理的地方」的信号真空）。

    确定性信号挖掘·**只点名候选交 AI 编剧核**（绝不内联问 LLM「合理吗」，与 causal_graph 同纪律）。
    每条引用真实 trace_id（防瞎编原生）。三类结构/词面信号（保守·宁少报不滥报）：
      · contrivance         —— 因果 cause/effect/adaptation_note 命中「巧合/便利/天降」类便宜达成标记。
      · motive_without_stakes —— character_motive 缺 obstacle 或 choice_pressure = want 可能过易达成（无张力）。
      · uncosted_power_use  —— 世界观设定了力量有代价（power_system 出现代价类词），但某 effect 动用系统/异能却整条没提代价。
      · ungrounded_cause    —— 因果 cause（非首条）与「此前所有 cause/effect + 伏笔 setup + 角色 want」零二字重叠 = 可能天降、缺前因。
    """
    out: List[Dict[str, Any]] = []

    # 1) 巧合/便利/天降 词面信号
    for row in chain:
        cid = _tid(row)
        if not cid:
            continue
        blob = " ".join(str(row.get(k) or "") for k in ("cause", "effect", "adaptation_note"))
        hits = _hit_markers(blob, CONTRIVANCE_MARKERS)
        if hits:
            out.append({
                "kind": "contrivance",
                "trace_id": cid,
                "evidence": f"因果链命中便宜达成标记：{'、'.join(hits)}",
                "cause": str(row.get("cause") or ""),
                "effect": str(row.get("effect") or ""),
                "suggestion": "核对原著是否本有合理铺垫；若是硬伤，在 story_spine.continuity_fixes 写最小改动 + no_contradiction_proof。",
            })

    # 2) 权力无代价：世界观设了代价，但 effect 用了系统/异能却整条没提代价
    world_has_cost = bool(_hit_markers(power_system_text, POWER_COST_MARKERS))
    if world_has_cost:
        for row in chain:
            cid = _tid(row)
            if not cid:
                continue
            blob = " ".join(str(row.get(k) or "") for k in ("cause", "effect", "adaptation_note"))
            if _hit_markers(blob, POWER_USE_MARKERS) and not _hit_markers(blob, POWER_COST_MARKERS):
                out.append({
                    "kind": "uncosted_power_use",
                    "trace_id": cid,
                    "evidence": "世界观设定了力量有代价，但此因果动用系统/异能却未体现代价（可能无代价力量蠕变）。",
                    "effect": str(row.get("effect") or ""),
                    "suggestion": "核对原著该处是否付了代价；若视觉/旁白省略了成本，补回或标注，避免读者觉得开挂。",
                })

    # 3) 动机无阻力：want 存在但缺 obstacle 或 choice_pressure
    for row in motives:
        mid = _tid(row)
        if not mid or not str(row.get("want") or "").strip():
            continue
        missing = [k for k in ("obstacle", "choice_pressure") if not str(row.get(k) or "").strip()]
        if missing:
            out.append({
                "kind": "motive_without_stakes",
                "trace_id": mid,
                "character": str(row.get("character") or ""),
                "evidence": f"动机缺 {'、'.join(missing)}——想要的东西可能过易达成，缺戏剧张力。",
                "suggestion": "补明阻力/选择压力（源里若有就回填，没有则这条线可能本就是琐碎支线，考虑并入或砍）。",
            })

    # 4) 前因缺失（天降候选·极保守：与已建立世界零二字重叠才报）
    grounded = set()
    for row in motives:
        for k in ("want", "obstacle", "arc_delta"):
            grounded |= _bigrams(row.get(k))
    prior = set(grounded)
    for idx, row in enumerate(chain):
        cid = _tid(row)
        cause = str(row.get("cause") or "")
        if idx >= 1 and cid and len("".join(cause.split())) >= 4:
            if not (_bigrams(cause) & prior):
                out.append({
                    "kind": "ungrounded_cause",
                    "trace_id": cid,
                    "evidence": "此因果的 cause 与此前所有因果/伏笔/动机零重叠——可能缺前因（天降）。",
                    "cause": cause,
                    "suggestion": "核对原著是否在更早处铺垫了此因；若确缺，补一处前因锚或在 continuity_fixes 记最小修补。",
                })
        # 本条并入「已建立世界」，供后续条判定前因
        prior |= _bigrams(row.get("cause")) | _bigrams(row.get("effect"))
    return out


# ── 工作单 build ──────────────────────────────────────────────────────────────

def build_worksheet(root: Path) -> Dict[str, Any]:
    ledger = _foreshadow_ledger(root)
    chain = _causality_chain(root)
    motives = _character_motives(root)
    power_text = _power_system_text(root)
    spine, threads = _spine_and_threads(root)
    debt = foreshadow_debt(ledger, threads)
    gap = mainline_gap(chain, spine)
    tangents = tangent_candidates(threads, ledger)
    unreasonable = unreasonable_beat_candidates(chain, motives, power_text)
    contributions = sorted((thread_contribution(t, ledger) for t in threads), key=lambda r: r["score"], reverse=True)
    inputs_missing: List[str] = []
    if not _understanding_contract(root):
        inputs_missing.append(COMPREHENSION_JSON)
    if not (spine or threads):
        inputs_missing.append(SPINE_JSON)
    return {
        "kind": KIND,
        "version": VERSION,
        "status": "draft",
        "generated_at": now_iso(),
        "consumes": [COMPREHENSION_JSON, SPINE_JSON],
        "inputs_missing": inputs_missing,
        "summary": {
            "foreshadow_debt": len(debt),
            "mainline_gaps": len(gap),
            "tangent_candidates": len(tangents),
            "unreasonable_beats": len(unreasonable),
            "threads_scored": len(contributions),
        },
        # 编辑信号（机检提案）——AI 编剧据此做语义取舍，落回 story_spine.json 的 decision/continuity_fixes。
        "foreshadow_debt": debt,
        "mainline_gaps": gap,
        "tangent_candidates": tangents,
        "unreasonable_beats": unreasonable,
        "thread_contributions": contributions,
        # 编剧动作账（人/agent 填）：每条改动须引用真实 id，check 防瞎编。
        "revision_ledger": [],
        "_agent_guidance": (
            "像真实编剧整体改良：① 砍/合 tangent_candidates 里的琐碎支线以突出主情节；② 补还或删除 "
            "foreshadow_debt 里埋了没还的伏笔；③ mainline_gaps 处把主线承接点接回 spine.depends_on；"
            "④ unreasonable_beats 逐条核对原著：真是硬伤就写进 story_spine.continuity_fixes（最小改动+"
            "no_contradiction_proof+touches_protected 标注），是原著本有合理铺垫或有意为之就在 revision_ledger "
            "记 dismiss 理由。所有改动落回 story_spine.json 的 threads[].decision/connectivity 与 continuity_fixes，"
            "再跑 story_spine.py check 做防瞎编+衔接硬校验。禁止臆造任何 id；改后主线必须仍衔接。"
            "unreasonable_beats 全是候选不是定论——不得据它凭空加情节，只能核原著后做最小修补或标注。"
        ),
    }


# ── check（防瞎编 + 编辑债覆盖） ─────────────────────────────────────────────

def _issue(rows: List[Dict[str, Any]], severity: str, code: str, message: str) -> None:
    rows.append({"severity": severity, "code": code, "message": message})


def check(root: Path) -> Dict[str, Any]:
    root = Path(root)
    issues: List[Dict[str, Any]] = []
    ws = load_json(root / PACK_DIR / WORKSHEET_FILE)
    ledger = _foreshadow_ledger(root)
    chain = _causality_chain(root)
    spine, threads = _spine_and_threads(root)
    known_foreshadow = {_tid(r) for r in ledger if _tid(r)}
    known_causal = {_tid(r) for r in chain if _tid(r)}
    known_thread = {str(t.get("id") or "").strip() for t in threads if str(t.get("id") or "").strip()}
    known_ids = known_foreshadow | known_causal | known_thread | {str(n.get("id") or "").strip() for n in spine}

    if not isinstance(ws, dict):
        _issue(issues, "warn", "worksheet_missing",
               f"缺 {PACK_DIR}/{WORKSHEET_FILE}——先跑 `editorial_revision.py <root> build --write` 生成编辑提案。")
        return _verdict(root, issues, ws)

    # 防瞎编：revision_ledger 每条动作引用的 id 必须真实存在
    for i, row in enumerate(ws.get("revision_ledger") or [], 1):
        if not isinstance(row, Mapping):
            continue
        refs = []
        for key in ("target_thread_id", "foreshadow_id", "causal_id"):
            v = str(row.get(key) or "").strip()
            if v:
                refs.append((key, v))
        for key in ("source_trace", "downstream_deps"):
            for v in row.get(key) or []:
                v = str(v).strip()
                if v:
                    refs.append((key, v))
        for key, v in refs:
            if v not in known_ids:
                _issue(issues, "block", "fabricated_id",
                       f"revision_ledger[{i}].{key}={v} 不在 source_comprehension/story_spine 里——禁止臆造 id（防瞎编）。")
        # 砍除动作必须给承接（衔接底线；细粒度 reroute 校验仍由 story_spine.check 兜）
        action = str(row.get("action") or "").strip()
        if action in {"cut", "fold"} and not str(row.get("reroute") or "").strip():
            _issue(issues, "block", "cut_without_reroute",
                   f"revision_ledger[{i}] action={action} 但缺 reroute（砍后主线/伏笔由谁承接）——改后须能衔接。")

    # 编辑债覆盖：埋了没还的伏笔若未在动作账里处理 → 提醒（非硬闸，story_spine 有兜底）
    addressed = {str(r.get("foreshadow_id") or "").strip() for r in (ws.get("revision_ledger") or []) if isinstance(r, Mapping)}
    for d in foreshadow_debt(ledger, threads):
        if d["protected"] and d["foreshadow_id"] not in addressed:
            _issue(issues, "warn", "unaddressed_protected_debt",
                   f"受保护伏笔 {d['foreshadow_id']} 埋了没还，且未在 revision_ledger 处理——必须补还回收。")
    return _verdict(root, issues, ws)


def _verdict(root: Path, issues: List[Dict[str, Any]], ws: Any) -> Dict[str, Any]:
    blocks = sum(1 for r in issues if r["severity"] == "block")
    return {
        "kind": CHECK_KIND,
        "version": VERSION,
        "root": str(root),
        "status": "blocked" if blocks else "pass",
        "summary": {"block": blocks, "warn": sum(1 for r in issues if r["severity"] == "warn")},
        "issues": issues,
        "worksheet_status": (ws or {}).get("status") if isinstance(ws, dict) else None,
    }


# ── CLI ────────────────────────────────────────────────────────────────────────

def _worksheet_md(ws: Mapping[str, Any]) -> str:
    s = ws.get("summary") or {}
    lines = [f"# 编辑修订工作单（编剧级整体改良提案）", "",
             f"- 埋了没还的伏笔：{s.get('foreshadow_debt', 0)}",
             f"- 主线接不上处：{s.get('mainline_gaps', 0)}",
             f"- 琐碎支线提案精简：{s.get('tangent_candidates', 0)}",
             f"- 不合理点候选（待核原著）：{s.get('unreasonable_beats', 0)}", ""]
    if ws.get("unreasonable_beats"):
        lines.append("## 不合理点候选（机检·须逐条核对原著，绝不据此瞎编）")
        for u in ws["unreasonable_beats"]:
            lines.append(f"- **{u.get('trace_id')}**（{u.get('kind')}）：{u.get('evidence')}")
    if ws.get("tangent_candidates"):
        lines.append("## 与主线不相干的琐碎支线（提案 cut/compress，突出主情节）")
        for t in ws["tangent_candidates"]:
            lines.append(f"- **{t.get('thread_id')}**（{t.get('name')}·分{t.get('score')}）→ 提案 {t.get('proposal')}")
    if ws.get("foreshadow_debt"):
        lines.append("\n## 埋了没还的伏笔（补还或删设定）")
        for d in ws["foreshadow_debt"]:
            tag = "🔒受保护" if d.get("protected") else ""
            lines.append(f"- {d.get('foreshadow_id')} {tag}：{d.get('suggestion')}")
    if ws.get("mainline_gaps"):
        lines.append("\n## 主线接不上（承接点接回 spine.depends_on）")
        for g in ws["mainline_gaps"]:
            lines.append(f"- {g.get('causal_id')}：{g.get('cause')} → {g.get('effect')}")
    lines.append("\n> " + str(ws.get("_agent_guidance") or ""))
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="编辑修订工作单：编剧级整体改良提案 + 防瞎编校验")
    ap.add_argument("root")
    ap.add_argument("command", choices=["build", "check"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    if ns.command == "build":
        ws = build_worksheet(root)
        if ns.write:
            write_json_atomic(root / PACK_DIR / WORKSHEET_FILE, ws)
            (root / PACK_DIR / "views").mkdir(parents=True, exist_ok=True)
            (root / PACK_DIR / "views" / "editorial_revision_worksheet.md").write_text(_worksheet_md(ws), encoding="utf-8")
        if ns.json:
            print(json.dumps(ws, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            s = ws["summary"]
            print(f"编辑提案：琐碎支线 {s['tangent_candidates']} · 伏笔债 {s['foreshadow_debt']} · 主线缺口 {s['mainline_gaps']}"
                  f" · 不合理点候选 {s.get('unreasonable_beats', 0)}"
                  + ("（已写工作单）" if ns.write else "（未写，加 --write 落盘）"))
        return 0
    res = check(root)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"编辑修订校验：{res['status']} · block {res['summary']['block']} · warn {res['summary']['warn']}")
        for r in res["issues"]:
            print(f"  [{r['severity']}] {r['code']}: {r['message']}")
    return 1 if res["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
