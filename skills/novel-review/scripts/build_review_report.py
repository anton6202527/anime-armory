#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build scheduler-readable novel review reports.

Takes deterministic findings from mechanical_check.py and optional human/LLM
findings, then writes:
  - 审稿/review_report.json
  - 审稿/审稿报告.md

This closes the gap between "机检发现问题" and the QA gate contract consumed by
novel-craft/progress.py and export.py.
"""
import argparse
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
# 本线自包含：report_snapshot/waivers 的真身在 novel/_lib（不伸手进 novel-craft/scripts）
_COMMON = os.path.join(SKILLS_ROOT, "novel", "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

from io_utils import load_json, write_json
from report_snapshot import snapshot_chapters
from waivers import make_waiver


SEVERITY_MAP = {
    "🔴": "blocking",
    "🟡": "suggestion",
    "🟢": "polish",
    "blocking": "blocking",
    "suggestion": "suggestion",
    "polish": "polish",
}

DIMENSION_MAP = {
    "格式": "format",
    "章号": "format",
    "标题": "outline",
    "字数": "wordcount",
    "原文照搬": "plagiarism",
    "题旨偏移": "theme",
    "读者承诺": "reader_promise",
    "文学性": "prose",
    "文笔": "prose",
}

RETURN_STAGE_BY_DIM = {
    "format": "draft",
    "outline": "outline",
    "wordcount": "draft",
    "plagiarism": "draft",
    "theme": "outline",
    "reader_promise": "demo",
    "prose": "draft",
}

CONSISTENCY_SECTION_MAP = {
    "reader_contract": {
        "dimension": "reader_promise",
        "recommended_skill": "novel-review",
        "return_to_stage": "demo",
        "count_key": "alerts",
        "problem": "逐章读者契约检查发现题旨/承诺推进缺失",
        "fix_hint": "回读者契约、Demo gate 和相关章纲，补齐 reader_contract_progress/theme_alignment；必要时重排该段章纲。",
    },
    "logic_sentry": {
        "dimension": "logic",
        "recommended_skill": "novel-wiki",
        "return_to_stage": "wiki",
        "count_key": "alerts",
        "problem": "逻辑哨兵发现状态/位置/人物事实冲突候选",
        "fix_hint": "回动态百科和对应章节核对人物状态、地点、道具与时间线；确认后修正文或更新 state_ledger。",
    },
    "style_drift": {
        "dimension": "style_drift",
        "recommended_skill": "novel-style",
        "return_to_stage": "draft",
        "count_key": "drifted",
        "problem": "文风指纹相对锚点章漂移",
        "fix_hint": "回文风锚点和漂移章节做主编润色，统一句式节奏、意象密度、对白风格与叙述口吻。",
    },
    "power_system": {
        "dimension": "power_system",
        "recommended_skill": "novel-wiki",
        "return_to_stage": "draft",
        "count_key": "alerts",
        "problem": "力量体系/等级/战力 progression 存在一致性风险",
        "fix_hint": "回设定/power_system_registry.json 与相关章节，修正退档、未知境界、越级过快或面板字段漂移。",
    },
    "research_fact_support": {
        "dimension": "professional_research",
        "recommended_skill": "novel-research",
        "return_to_stage": "research",
        "count_key": "alerts",
        "problem": "专业/行业事实缺少可追溯资料包或资料包未通过证据校验",
        "fix_hint": "回 `novel-research` 补 `资料/专业资料包_<主题>.md` 与 `research_sources.json`，每条事实绑定来源、日期、可信度、适用章节和禁用/不确定项。",
    },
    # 2026 新增检测器 + 伏笔超期：consistency_audit 早已串跑它们并写进 consistency_audit.json，
    # 但 review_report 长期只认上面 5 个 section，导致这些机检产出到不了正式报告/QA gate/修订计划
    # （静默失效）。这里补齐映射，每个 section key 必须与 consistency_audit.main 结果字典一致；
    # 全部经 _run_detector，count_key 统一为 alerts（int 计数），blocking 由各检测器 阻断级 alert 决定。
    "hook_endings": {
        "dimension": "hook",
        "recommended_skill": "novel-review",
        "return_to_stage": "draft",
        "count_key": "alerts",
        "problem": "断章钩子缺失/章末钩力不足",
        "fix_hint": "回章末按 `novel-craft/references/hooks.md` 补悬念/反转/承诺钩子，避免平钩收束。",
    },
    "voice_drift": {
        "dimension": "voice_drift",
        "recommended_skill": "novel-review",
        "return_to_stage": "draft",
        "count_key": "alerts",
        "problem": "角色语感漂移（一人多腔/串腔）",
        "fix_hint": "回 `设定/角色语感.json` 与对应章节，统一该角色口头禅、句式、语气与说话习惯。",
    },
    "tone_curve": {
        "dimension": "tone_curve",
        "recommended_skill": "novel-review",
        "return_to_stage": "draft",
        "count_key": "alerts",
        "problem": "情绪/爽点曲线偏离设计（情绪点缺失或爽点回报平淡）",
        "fix_hint": "回 `设定/tone_curve.json` 与 `情绪节奏.md`，在弱段补情绪点/爽点回报，校准情绪三拍。",
    },
    "thread_resolution": {
        "dimension": "thread",
        "recommended_skill": "novel-wiki",
        "return_to_stage": "wiki",
        "count_key": "alerts",
        "problem": "支线/未收线程长期未收口",
        "fix_hint": "回 `state_ledger` 的 open_threads 与章纲，安排回收或显式 drop，避免悬而不决。",
    },
    "antagonist_scaling": {
        "dimension": "power_system",
        "recommended_skill": "novel-wiki",
        "return_to_stage": "draft",
        "count_key": "alerts",
        "problem": "反派战力/等级缩放与主角成长不匹配",
        "fix_hint": "回 `设定/power_system_registry.json` 与反派设定，修正越级/战力崩坏/反派忽强忽弱。",
    },
    "timeline": {
        "dimension": "logic",
        "recommended_skill": "novel-wiki",
        "return_to_stage": "wiki",
        "count_key": "alerts",
        "problem": "时间线/事件顺序存在矛盾候选",
        "fix_hint": "回 `设定/timeline.json` 与对应章节核对事件先后、季节/年龄/时长推进的一致性。",
    },
    "minor_characters": {
        "dimension": "logic",
        "recommended_skill": "novel-wiki",
        "return_to_stage": "wiki",
        "count_key": "alerts",
        "problem": "配角连续性（生死/特征/在场）冲突候选",
        "fix_hint": "回动态百科与对应章节核对配角状态，确认后修正文或更新 state_ledger。",
    },
    "foreshadow": {
        "dimension": "foreshadow",
        "recommended_skill": "novel-wiki",
        "return_to_stage": "wiki",
        "count_key": "alerts",
        "problem": "高价值伏笔越过预期回收窗口，疑似遗忘/烂尾",
        "fix_hint": "回 `设定/foreshadowing_ledger.json` 与章纲，补回收或调整 expected_payoff_chapter；确认废弃则 drop。",
    },
    "trope_cliche": {
        "dimension": "novelty",
        "recommended_skill": "novel-create",
        "return_to_stage": "blueprint",
        "count_key": "alerts",
        "problem": "前提/开局命中高频套路，且未在差异化决策里点名如何颠覆（同质化预警·建议级）",
        "fix_hint": "回 `设定/创作蓝图.md` 的差异化决策段，为命中套路写明差异化/颠覆点（或换开局）；也可在 author_intent.forbidden_tropes 显式登记。",
    },
    "plot_variety": {
        "dimension": "novelty",
        "recommended_skill": "novel-review",
        "return_to_stage": "draft",
        "count_key": "alerts",
        "problem": "跨章节拍/桥段复读（同型桥段连打、危机→打脸循环、钩型/开篇单一、长铺垫零爽点）",
        "fix_hint": "对照 `审稿/plot_variety_findings.json` 命中的章段换节拍/换钩型/插小爽点；trope_cliche 管前提级套路，本项管跨章循环复读。",
    },
    "chapter_transition": {
        "dimension": "logic",
        "recommended_skill": "novel-review",
        "return_to_stage": "draft",
        "count_key": "alerts",
        "problem": "章边界承接断裂候选（上一章末尾与本章开篇人物零交集且无转场标记/开篇悬空）",
        "fix_hint": "对照 `审稿/transition_findings.json`：有意切线的开篇补转场标记（与此同时/翌日/另一边…），非有意的补一句承接把读者带过去。",
    },
    "prose_craft": {
        "dimension": "line_craft",
        "recommended_skill": "novel-edit",
        "return_to_stage": "draft",
        "count_key": "alerts",
        "problem": "行文手艺问题候选（过滤词滤镜/副词对话标签/开篇设定倾倒/点破主题/生理化情绪复读/哲理对白）",
        "fix_hint": "对照 `审稿/prose_craft_findings.json` 按传统 line-edit 手艺修：删滤镜直写感知、情绪进台词与动作节拍、设定拆进冲突现场、主题由事件承载不由旁白宣讲。",
    },
    "manuscript_map": {
        "dimension": "structure",
        "recommended_skill": "novel-craft",
        "return_to_stage": "outline",
        "count_key": "alerts",
        "problem": "结构地图缺口（章缺 turn/value_shift 价值转折、缺章纲与场景卡来源）",
        "fix_hint": "回 `设定/scene_cards.json` 补 turn/value_shift；传统手艺：无价值转折的场景删掉或合并进相邻场景。",
    },
}


def read_meta(root):
    return load_json(os.path.join(root, "_meta.json"), {}) or {}


def rel(root, path):
    if not path:
        return None
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")


def owner_skill(meta):
    kind = meta.get("kind")
    if kind in {"create", "rewrite", "spinoff", "expand", "condense", "continue"}:
        return f"novel-{kind}"
    return "novel-review"


def affected_files_for(finding):
    chapter = finding.get("chapter")
    if isinstance(chapter, int) and chapter > 0:
        return [f"章节/第{chapter:02d}章.md"]
    dim = finding.get("dim") or finding.get("dimension")
    if dim in {"章号", "格式"}:
        return ["章节/"]
    return []


def missing_mechanical_waiver(root, mechanical_path, scope, source_snapshot):
    waiver = make_waiver(
        "missing_mechanical",
        reason="explicit --allow-missing-mechanical",
        affected_gate="mechanical_check",
        source="novel-review/scripts/build_review_report.py",
        details={
            "intended_mechanical_findings_path": rel(root, mechanical_path),
        },
        scope={
            "review_scope": scope,
            "source_aggregate_hash": (source_snapshot or {}).get("aggregate_hash") or "",
            "chapter_count": len((source_snapshot or {}).get("files") or []),
        },
    )
    waiver["risk"] = "格式、字数、章号、术语漂移、原文照搬等确定性机检未执行；本报告不是正常全量通过。"
    return waiver


def normalize_mechanical_finding(raw, idx, meta):
    severity = SEVERITY_MAP.get(raw.get("severity"), "suggestion")
    dimension = DIMENSION_MAP.get(raw.get("dim"), raw.get("dim") or "mechanical")
    stage = RETURN_STAGE_BY_DIM.get(dimension, "draft")
    skill = "novel-craft" if dimension in {"format", "outline", "wordcount"} else owner_skill(meta)
    if dimension == "plagiarism":
        skill = owner_skill(meta)
    chapter = raw.get("chapter")
    if chapter == 0:
        chapter = None
    return {
        "id": f"REV-MECH-{idx:03d}",
        "severity": severity,
        "dimension": dimension,
        "chapter": chapter,
        "location": "全局" if chapter is None else f"第{chapter}章",
        "evidence": raw.get("evidence", ""),
        "problem": raw.get("msg") or raw.get("problem") or "",
        "fix_hint": _fix_hint(dimension, raw),
        "recommended_skill": skill,
        "return_to_stage": stage,
        "affected_files": affected_files_for(raw),
        "blocking": severity == "blocking",
        "confidence": "high",
        "source": "mechanical_check",
    }


def _fix_hint(dimension, raw):
    if dimension == "format":
        return "修正章节文件命名、H1 标题、章号连续性或 meta 注释。"
    if dimension == "outline":
        return "同步正文标题与设定/章纲.md，或回章纲阶段确认新标题。"
    if dimension == "wordcount":
        return "按项目建议篇幅增删内容，保留本章戏剧节拍和钩子。"
    if dimension == "plagiarism":
        return "重写雷同段，保留事件骨架但不要复刻原文表达。"
    if dimension == "theme":
        return "回看 `设定/读者契约.md` 与章纲，删改偏离核心题旨的支线或重写本章目标。"
    if dimension == "reader_promise":
        return "回到 Demo gate/读者契约，补兑现、递进或明确延迟兑现的读者承诺。"
    if dimension == "prose":
        return "按 `novel-craft/references/chapter.md` 做文学性精修：具体意象、动作化情绪、对白有戏，删空泛辞藻。"
    return raw.get("fix_hint") or "按问题定位回源头阶段修订。"


def normalize_human_finding(raw, idx):
    severity = SEVERITY_MAP.get(raw.get("severity"), raw.get("severity") or "suggestion")
    finding = dict(raw)
    finding.setdefault("id", f"REV-HUMAN-{idx:03d}")
    finding["severity"] = severity
    finding.setdefault("dimension", raw.get("dimension") or "manual")
    finding.setdefault("chapter", raw.get("chapter"))
    finding.setdefault("location", "全局" if raw.get("chapter") in (None, 0) else f"第{raw.get('chapter')}章")
    finding.setdefault("evidence", "")
    finding.setdefault("problem", raw.get("problem") or raw.get("msg") or "")
    finding.setdefault("fix_hint", raw.get("fix_hint") or "按人工审稿建议修订。")
    finding.setdefault("recommended_skill", raw.get("recommended_skill") or "novel-review")
    finding.setdefault("return_to_stage", raw.get("return_to_stage") or "draft")
    finding.setdefault("affected_files", raw.get("affected_files") or affected_files_for(raw))
    finding.setdefault("blocking", severity == "blocking")
    finding.setdefault("confidence", raw.get("confidence") or "medium")
    finding.setdefault("source", "human_assessment")
    return finding


def normalize_consistency_findings(payload, meta, start_idx=1):
    if not isinstance(payload, dict):
        return []
    findings = []
    idx = start_idx
    for section, spec in CONSISTENCY_SECTION_MAP.items():
        data = payload.get(section) or {}
        if not isinstance(data, dict) or not data.get("ran"):
            continue
        count = int(data.get(spec["count_key"]) or 0)
        blocking = int(data.get("blocking") or 0)
        if count <= 0 and blocking <= 0:
            continue
        severity = "blocking" if blocking > 0 else "suggestion"
        problem = spec["problem"]
        evidence_parts = []
        if count:
            evidence_parts.append(f"{spec['count_key']}={count}")
        if blocking:
            evidence_parts.append(f"blocking={blocking}")
        if data.get("json"):
            evidence_parts.append(f"source={data['json']}")
        findings.append({
            "id": f"REV-CONS-{idx:03d}",
            "severity": severity,
            "dimension": spec["dimension"],
            "chapter": None,
            "location": "全局",
            "evidence": "；".join(evidence_parts),
            "problem": problem,
            "fix_hint": spec["fix_hint"],
            "recommended_skill": spec["recommended_skill"],
            "return_to_stage": spec["return_to_stage"],
            "affected_files": [],
            "blocking": severity == "blocking",
            "confidence": "medium",
            "source": "consistency_audit",
        })
        idx += 1
    return findings


def load_human_findings(path):
    if not path:
        return []
    payload = load_json(path)
    if payload is None:
        raise FileNotFoundError(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("findings") or []
    raise ValueError("human assessment 必须是 list 或含 findings 的 object")


def build_next_actions(findings):
    actions = []
    seen = set()
    priority_for = {"blocking": "must", "suggestion": "should", "polish": "could"}
    for finding in findings:
        if finding["severity"] not in {"blocking", "suggestion"}:
            continue
        key = (finding["recommended_skill"], finding["return_to_stage"], finding["severity"])
        if key in seen:
            for action in actions:
                if (
                    action["recommended_skill"],
                    action["return_to_stage"],
                    "blocking" if action["priority"] == "must" else "suggestion",
                ) == key:
                    action["finding_ids"].append(finding["id"])
            continue
        seen.add(key)
        actions.append({
            "priority": priority_for[finding["severity"]],
            "action": finding["fix_hint"],
            "recommended_skill": finding["recommended_skill"],
            "return_to_stage": finding["return_to_stage"],
            "finding_ids": [finding["id"]],
        })
    return actions


def write_markdown(path, meta, report):
    lines = [
        f"# 审稿报告 — {meta.get('title') or meta.get('source_title') or '未定'}",
        "",
        "## 概览",
        "",
        f"- 阻断级：{report['summary']['blocking_count']}",
        f"- 建议级：{report['summary']['suggestion_count']}",
        f"- 润色级：{report['summary']['polish_count']}",
        f"- 结论：{report['summary']['verdict']}",
        f"- 显式豁免：{report['summary'].get('waiver_count', 0)}",
        "",
    ]
    if report.get("waivers"):
        lines.extend(["## 显式豁免", ""])
        for waiver in report["waivers"]:
            lines.append(
                f"- **{waiver['id']}** [{waiver['type']}] {waiver['reason']}；"
                f"影响 gate：{waiver['affected_gate']}；风险：{waiver['risk']}"
            )
        lines.append("")
    lines.extend(["## 问题清单", ""])
    if not report["findings"]:
        lines.append("- 未发现问题。")
    for finding in report["findings"]:
        lines.append(
            f"- **{finding['id']}** [{finding['severity']}] {finding['location']} · "
            f"{finding['dimension']}：{finding['problem']}"
        )
        if finding.get("evidence"):
            lines.append(f"  - 证据：{finding['evidence']}")
        lines.append(f"  - 修法：{finding['fix_hint']}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def build_report(root, mechanical_path=None, human_path=None, consistency_path=None,
                 scope="full", allow_missing_mechanical=False):
    meta = read_meta(root)
    if mechanical_path is None:
        mechanical_path = os.path.join(root, "审稿", "mechanical_findings.json")
    mechanical_exists = os.path.exists(mechanical_path)
    if not mechanical_exists and not allow_missing_mechanical:
        raise FileNotFoundError(
            f"缺少机检文件：{mechanical_path}；先运行 mechanical_check.py --json-out，"
            "或显式加 --allow-missing-mechanical。"
        )
    source_snapshot = snapshot_chapters(root, mode=f"review:{scope}")
    waivers = []
    if not mechanical_exists:
        waivers.append(missing_mechanical_waiver(root, mechanical_path, scope, source_snapshot))
    mechanical = load_json(mechanical_path, {}) if mechanical_exists else {}
    mechanical = mechanical or {}
    raw_mechanical = mechanical.get("findings") or []
    findings = [
        normalize_mechanical_finding(raw, idx + 1, meta)
        for idx, raw in enumerate(raw_mechanical)
    ]
    if consistency_path is None:
        consistency_path = os.path.join(root, "审稿", "consistency_audit.json")
    consistency = load_json(consistency_path, {}) if os.path.exists(consistency_path) else {}
    findings.extend(normalize_consistency_findings(consistency, meta, len(findings) + 1))
    human = load_human_findings(human_path)
    findings.extend(normalize_human_finding(raw, idx + 1) for idx, raw in enumerate(human))
    order = {"blocking": 0, "suggestion": 1, "polish": 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f.get("chapter") or 0, f["id"]))
    summary = {
        "blocking_count": sum(1 for f in findings if f["severity"] == "blocking" or f.get("blocking")),
        "suggestion_count": sum(1 for f in findings if f["severity"] == "suggestion"),
        "polish_count": sum(1 for f in findings if f["severity"] == "polish"),
        "waiver_count": len(waivers),
        "verdict": "blocked" if any(f.get("blocking") for f in findings) else ("needs_revision" if findings else "pass"),
    }

    # ── 连续条件通过熔断 (P2-⑨) ────────────────────────────────────────────
    # "有条件通过"（needs_revision）连续 3 次 → 强制阻断，防止项目在"每次都有小问题
    # 但都不阻塞"的状态下漂移 30 章才发现跑偏。阻断后需人工确认方向再继续。
    streak_path = os.path.join(root, "审稿", "review_streak.json")
    streak_data = load_json(streak_path, {}) if os.path.exists(streak_path) else {}
    if not isinstance(streak_data, dict):
        streak_data = {}
    streak = streak_data.get("needs_revision_streak", 0)
    if summary["verdict"] == "needs_revision":
        streak += 1
    else:
        streak = 0
    if streak >= 3:
        findings.insert(0, {
            "id": f"FUSE-{len(findings)+1:03d}",
            "severity": "blocking",
            "blocking": True,
            "dimension": "流程熔断",
            "problem": f"连续 {streak} 次审稿均为「有条件通过」(needs_revision)——项目可能在\"每次都有小问题但都不阻塞\"的状态下持续漂移。",
            "location": "审稿/review_report.json (本次)",
            "fix_hint": (
                "人工确认方向：1) 回看最近 5-10 章的 revision_plan/审稿报告，判断小问题是否已聚合成系统性跑偏；"
                "2) 若是方向性问题，回流到 novel-rewrite 或 novel-create 的方向设定阶段；"
                "3) 若确认只是零散问题，跑 review 加 --advisory 重置 streak。"
            ),
            "recommended_skill": "novel-review",
            "return_to_stage": "review",
            "affected_files": [f"审稿/review_report_{src['generated_at']}.json" if isinstance(src := streak_data.get("last_report", {}), dict) and src.get("generated_at") else "审稿/review_report.json"],
            "chapter": None,
            "evidence": f"审稿/review_streak.json → needs_revision_streak={streak}",
        })
        summary["verdict"] = "blocked"
        summary["blocking_count"] += 1
        summary["fuse_triggered"] = True
    # 持久化 streak
    streak_data["needs_revision_streak"] = streak
    streak_data["last_report"] = {"generated_at": date.today().isoformat(), "verdict": summary["verdict"]}
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(streak_path, "w", encoding="utf-8") as f:
        json.dump(streak_data, f, ensure_ascii=False, indent=2)
    summary["needs_revision_streak"] = streak
    return {
        "schema_version": 1,
        "kind": "novel_review_report",
        "project_root": os.path.abspath(root),
        "generated_at": date.today().isoformat(),
        "scope": {"mode": scope},
        "source_snapshot": source_snapshot,
        "summary": summary,
        "mechanical_findings_path": rel(root, mechanical_path) if os.path.exists(mechanical_path) else None,
        "waivers": waivers,
        "findings": findings,
        "next_actions": build_next_actions(findings),
    }


def main():
    ap = argparse.ArgumentParser(description="把 novel 机检/人判结果汇总成 review_report.json")
    ap.add_argument("project_root")
    ap.add_argument("--mechanical", default=None, help="mechanical_check.py --json-out 产物；缺省 审稿/mechanical_findings.json")
    ap.add_argument("--human-assessment", default=None, help="人工/LLM 审稿 JSON；list 或含 findings 字段")
    ap.add_argument("--consistency", default=None,
                    help="consistency_audit.py 汇总产物；缺省自动读取 审稿/consistency_audit.json（若存在）")
    ap.add_argument("--scope", default="full")
    ap.add_argument("--allow-missing-mechanical", action="store_true",
                    help="显式允许没有机检文件时生成报告；默认缺机检即失败")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)
    try:
        report = build_report(
            root,
            args.mechanical,
            args.human_assessment,
            args.consistency,
            scope=args.scope,
            allow_missing_mechanical=args.allow_missing_mechanical,
        )
    except Exception as exc:
        print(f"[err] 构建 review_report 失败：{exc}", file=sys.stderr)
        sys.exit(2)

    review_dir = os.path.join(root, "审稿")
    os.makedirs(review_dir, exist_ok=True)
    json_path = os.path.join(review_dir, "review_report.json")
    md_path = os.path.join(review_dir, "审稿报告.md")
    write_json(json_path, report)
    write_markdown(md_path, read_meta(root), report)
    print(f"[ok] review report JSON → {json_path}")
    print(f"[ok] review report MD   → {md_path}")
    print(f"     阻断：{report['summary']['blocking_count']} | 建议：{report['summary']['suggestion_count']} | 润色：{report['summary']['polish_count']}")


if __name__ == "__main__":
    main()
