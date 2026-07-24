#!/usr/bin/env python3
"""Tests for story_spine.py — 主线提炼 + 支线剪枝合同校验。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import story_spine as SS  # noqa: E402


def _mk(tmp_path, *, comprehension=None, strategy=None, spine=None, settings=None):
    root = tmp_path / "work"
    (root / "开发包").mkdir(parents=True, exist_ok=True)
    (root / "设定库").mkdir(parents=True, exist_ok=True)
    if comprehension is not None:
        (root / "设定库" / "source_comprehension.json").write_text(
            json.dumps(comprehension, ensure_ascii=False), encoding="utf-8")
    if strategy is not None:
        (root / "开发包" / "adaptation_strategy.json").write_text(
            json.dumps(strategy, ensure_ascii=False), encoding="utf-8")
    if spine is not None:
        (root / "开发包" / "story_spine.json").write_text(
            json.dumps(spine, ensure_ascii=False), encoding="utf-8")
    if settings is not None:
        (root / "_设置.md").write_text(settings, encoding="utf-8")
    return root


def _comprehension(fids):
    return {
        "kind": "n2d_source_comprehension",
        "understanding_contract": {
            "foreshadowing_ledger": [
                {"trace_id": fid, "setup": f"伏笔{fid}", "payoff_plan": "后文回收",
                 "status": "open", "do_not_drop_reason": reason}
                for fid, reason in fids
            ],
            "causality_chain": [],
        },
    }


def _good_spine(threads, *, status="confirmed", fixes=None):
    return {
        "kind": "n2d_story_spine",
        "version": 1,
        "status": status,
        "mainline_logline": "姜月初以杀伐换升级并偿因果债。",
        "spine": [{"id": "SPINE_01", "beat": "主角杀裴取道行", "source_span": "第1章",
                   "causal_role": "起因", "depends_on": []}],
        "threads": threads,
        "continuity_fixes": fixes or [],
        "protected_invariants": ["人物动机", "伏笔兑现"],
    }


def test_confirmed_spine_with_kept_foreshadows_passes(tmp_path):
    comp = _comprehension([("SRC_FORESHADOW_001", "主线身份"), ("SRC_FORESHADOW_002", "系统代价")])
    spine = _good_spine([
        {"id": "THREAD_A", "name": "身份线", "class": "spine", "decision": "keep",
         "weight": "high", "source_spans": ["第1-5章"], "cut_keywords": [],
         "opens_foreshadow": ["SRC_FORESHADOW_001"], "pays_foreshadow": ["SRC_FORESHADOW_001"],
         "connectivity": {"downstream_mainline_deps": [], "payoff_reroute": "", "no_orphan_proof": ""}},
        {"id": "THREAD_B", "name": "系统线", "class": "supporting", "decision": "keep",
         "weight": "high", "source_spans": ["全书"], "cut_keywords": [],
         "opens_foreshadow": ["SRC_FORESHADOW_002"], "pays_foreshadow": ["SRC_FORESHADOW_002"],
         "connectivity": {"downstream_mainline_deps": [], "payoff_reroute": "", "no_orphan_proof": ""}},
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线  # source=explicit_user")
    report = SS.check(root)
    assert report["mode"] == "enforce"
    assert report["status"] == "pass", [i for i in report["issues"] if i["severity"] == "block"]


def test_cut_tangent_with_reroute_passes(tmp_path):
    comp = _comprehension([("SRC_FORESHADOW_001", "主线身份"), ("SRC_FORESHADOW_009", "旁枝小谜")])
    spine = _good_spine([
        {"id": "THREAD_A", "name": "身份线", "class": "spine", "decision": "keep",
         "weight": "high", "source_spans": ["第1-5章"],
         "opens_foreshadow": ["SRC_FORESHADOW_001"], "pays_foreshadow": ["SRC_FORESHADOW_001"],
         "connectivity": {}},
        {"id": "THREAD_C", "name": "村邻八卦旁枝", "class": "tangent", "decision": "cut",
         "weight": "low", "source_spans": ["第7章"], "cut_keywords": ["村邻", "八卦"],
         "opens_foreshadow": ["SRC_FORESHADOW_009"], "pays_foreshadow": ["SRC_FORESHADOW_009"],
         "connectivity": {"downstream_mainline_deps": [],
                          "payoff_reroute": "该谜团与主线无关，随线程整体退役；其唯一信息在主线SPINE_01已交代。",
                          "no_orphan_proof": "SRC_FORESHADOW_009 仅此线程开合，裁掉后无下游主线节点依赖。"}},
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 激进精简  # source=explicit_user")
    report = SS.check(root)
    assert report["mode"] == "enforce"
    assert report["status"] == "pass", [i for i in report["issues"] if i["severity"] == "block"]


def test_cut_without_reroute_blocks(tmp_path):
    comp = _comprehension([("SRC_FORESHADOW_001", "主线身份")])
    spine = _good_spine([
        {"id": "THREAD_C", "name": "旁枝", "class": "tangent", "decision": "cut",
         "weight": "low", "source_spans": ["第7章"], "cut_keywords": ["村邻"],
         "opens_foreshadow": [], "pays_foreshadow": [],
         "connectivity": {}},
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "cut_without_reroute" in codes
    assert "cut_without_orphan_proof" in codes
    assert report["status"] == "block"


def test_protected_foreshadow_orphaned_blocks(tmp_path):
    # 受保护伏笔的唯一承载线程被 cut 且无 reroute → 孤儿伏笔 block。
    comp = _comprehension([("SRC_FORESHADOW_003", "首集选择的长线后果")])
    spine = _good_spine([
        {"id": "THREAD_D", "name": "镇魔司遗物线", "class": "tangent", "decision": "cut",
         "weight": "mid", "source_spans": ["第3章"], "cut_keywords": ["遗物"],
         "opens_foreshadow": ["SRC_FORESHADOW_003"], "pays_foreshadow": ["SRC_FORESHADOW_003"],
         # 故意不给 reroute → 触发孤儿伏笔
         "connectivity": {"payoff_reroute": "", "no_orphan_proof": ""}},
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "protected_foreshadow_orphaned" in codes
    assert report["status"] == "block"


def test_fabricated_foreshadow_id_blocks(tmp_path):
    comp = _comprehension([("SRC_FORESHADOW_001", "主线身份")])
    spine = _good_spine([
        {"id": "THREAD_A", "name": "身份线", "class": "spine", "decision": "keep",
         "opens_foreshadow": ["SRC_FORESHADOW_999"], "pays_foreshadow": [],  # 不存在的 id
         "connectivity": {}},
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "foreshadow_id_fabricated" in codes
    assert report["status"] == "block"


def test_spine_thread_cannot_be_cut(tmp_path):
    comp = _comprehension([("SRC_FORESHADOW_001", "主线身份")])
    spine = _good_spine([
        {"id": "THREAD_A", "name": "主线", "class": "spine", "decision": "cut",
         "opens_foreshadow": ["SRC_FORESHADOW_001"], "pays_foreshadow": ["SRC_FORESHADOW_001"],
         "connectivity": {"payoff_reroute": "x", "no_orphan_proof": "y"}},
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "spine_thread_cut" in codes


def test_advisory_mode_never_blocks(tmp_path):
    # 保守/未设置：即便有 block 级问题，对外 status 也是 advisory（不阻断老项目）。
    comp = _comprehension([("SRC_FORESHADOW_001", "主线身份")])
    spine = _good_spine([
        {"id": "THREAD_C", "name": "旁枝", "class": "tangent", "decision": "cut",
         "opens_foreshadow": [], "pays_foreshadow": [], "connectivity": {}},
    ], status="draft")
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 保守")
    report = SS.check(root)
    assert report["mode"] == "advisory"
    assert report["status"] == "advisory"
    assert report["summary"]["block"] >= 1  # 问题仍被报告，只是不阻断


def test_missing_file_scaffolds_and_reports(tmp_path):
    comp = _comprehension([("SRC_FORESHADOW_001", "主线身份")])
    root = _mk(tmp_path, comprehension=comp, settings="主线剪枝: 突出主线")
    report = SS.check(root, write_missing=True)
    assert (root / "开发包" / "story_spine.json").exists()
    codes = {i["code"] for i in report["issues"]}
    assert "story_spine_missing" in codes
    assert report["status"] == "block"  # enforce mode


# ── 主线衔接机检（P1：depends_on / downstream_mainline_deps 依赖图·"改了要衔接上"）──

def _comprehension_causal(fids, causes):
    """causes: [(trace_id, must_keep_bool)]。"""
    return {
        "kind": "n2d_source_comprehension",
        "understanding_contract": {
            "foreshadowing_ledger": [
                {"trace_id": fid, "setup": f"伏笔{fid}", "payoff_plan": "后文回收",
                 "status": "open", "do_not_drop_reason": reason}
                for fid, reason in fids
            ],
            "causality_chain": [
                {"trace_id": cid, "cause": f"因{cid}", "effect": f"果{cid}",
                 "must_keep": "主线承接" if must_keep else "", "adaptation_note": ""}
                for cid, must_keep in causes
            ],
        },
    }


def _spine_with_deps(threads, spine_deps, *, status="confirmed"):
    return {
        "kind": "n2d_story_spine", "version": 1, "status": status,
        "mainline_logline": "姜月初以杀伐换升级并偿因果债。",
        "spine": [{"id": "SPINE_01", "beat": "主角杀裴取道行", "source_span": "第1章",
                   "causal_role": "起因", "depends_on": spine_deps}],
        "threads": threads, "continuity_fixes": [],
        "protected_invariants": ["人物动机", "伏笔兑现"],
    }


def test_mainline_dependency_orphaned_blocks(tmp_path):
    # 主线节点 depends_on SRC_CAUSE_010，其唯一承载线程被 cut 且无 reroute → 主线衔接断裂 block。
    comp = _comprehension_causal([("SRC_FORESHADOW_001", "主线身份")],
                                 [("SRC_CAUSE_010", False)])
    spine = _spine_with_deps([
        {"id": "THREAD_A", "name": "身份线", "class": "spine", "decision": "keep",
         "source_spans": ["第1-5章"], "opens_foreshadow": ["SRC_FORESHADOW_001"],
         "pays_foreshadow": ["SRC_FORESHADOW_001"], "connectivity": {}},
        {"id": "THREAD_E", "name": "旧恩怨支线", "class": "tangent", "decision": "cut",
         "source_spans": ["第6章"], "cut_keywords": ["旧恩怨"],
         "connectivity": {"downstream_mainline_deps": ["SRC_CAUSE_010"],
                          "payoff_reroute": "", "no_orphan_proof": "无关"}},
    ], ["SRC_CAUSE_010"])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "mainline_dependency_orphaned" in codes
    assert report["status"] == "block"


def test_mainline_dependency_rerouted_passes(tmp_path):
    # 同上但给了 payoff_reroute → 主线依赖被承接，不再断裂。
    comp = _comprehension_causal([("SRC_FORESHADOW_001", "主线身份")],
                                 [("SRC_CAUSE_010", False)])
    spine = _spine_with_deps([
        {"id": "THREAD_A", "name": "身份线", "class": "spine", "decision": "keep",
         "source_spans": ["第1-5章"], "opens_foreshadow": ["SRC_FORESHADOW_001"],
         "pays_foreshadow": ["SRC_FORESHADOW_001"], "connectivity": {}},
        {"id": "THREAD_E", "name": "旧恩怨支线", "class": "tangent", "decision": "cut",
         "source_spans": ["第6章"], "cut_keywords": ["旧恩怨"],
         "connectivity": {"downstream_mainline_deps": ["SRC_CAUSE_010"],
                          "payoff_reroute": "该因果由主线SPINE_01的杀裴动机直接承接，不经本支线也成立。",
                          "no_orphan_proof": "SRC_CAUSE_010 的效果已并入主线节点。"}},
    ], ["SRC_CAUSE_010"])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "mainline_dependency_orphaned" not in codes
    assert report["status"] == "pass", [i for i in report["issues"] if i["severity"] == "block"]


def test_must_keep_cause_cut_without_reroute_blocks(tmp_path):
    comp = _comprehension_causal([("SRC_FORESHADOW_001", "主线身份")],
                                 [("SRC_CAUSE_020", True)])
    spine = _spine_with_deps([
        {"id": "THREAD_A", "name": "身份线", "class": "spine", "decision": "keep",
         "source_spans": ["第1-5章"], "opens_foreshadow": ["SRC_FORESHADOW_001"],
         "pays_foreshadow": ["SRC_FORESHADOW_001"], "connectivity": {}},
        {"id": "THREAD_F", "name": "承接支线", "class": "supporting", "decision": "fold_into_main",
         "source_spans": ["第8章"], "cut_keywords": ["承接"],
         "connectivity": {"downstream_mainline_deps": ["SRC_CAUSE_020"],
                          "payoff_reroute": "", "no_orphan_proof": "x"}},
    ], [])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "must_keep_cause_cut_without_reroute" in codes
    assert report["status"] == "block"


def test_fabricated_causal_dep_blocks(tmp_path):
    # spine.depends_on 引用不存在的因果 id → 臆造依赖 block。
    comp = _comprehension_causal([("SRC_FORESHADOW_001", "主线身份")],
                                 [("SRC_CAUSE_010", False)])
    spine = _spine_with_deps([
        {"id": "THREAD_A", "name": "身份线", "class": "spine", "decision": "keep",
         "source_spans": ["第1-5章"], "opens_foreshadow": ["SRC_FORESHADOW_001"],
         "pays_foreshadow": ["SRC_FORESHADOW_001"], "connectivity": {}},
    ], ["SRC_CAUSE_777"])  # 不存在
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "causal_dep_fabricated" in codes
    assert report["status"] == "block"


def test_causal_checks_silent_without_source_chain(tmp_path):
    # 无因果链、无 depends_on 的老项目：新机检不误报。
    comp = _comprehension([("SRC_FORESHADOW_001", "主线身份")])
    spine = _good_spine([
        {"id": "THREAD_A", "name": "身份线", "class": "spine", "decision": "keep",
         "source_spans": ["第1-5章"], "opens_foreshadow": ["SRC_FORESHADOW_001"],
         "pays_foreshadow": ["SRC_FORESHADOW_001"], "connectivity": {}},
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "mainline_dependency_orphaned" not in codes
    assert "causal_dep_fabricated" not in codes
    assert report["status"] == "pass", [i for i in report["issues"] if i["severity"] == "block"]


# ── P4：章节锚严格解析 + 整章剔除计划 ────────────────────────────────────────

def test_parse_chapter_span_strict():
    assert SS.parse_chapter_span("第3章") == (3, 3)
    assert SS.parse_chapter_span("第3-5章") == (3, 5)
    assert SS.parse_chapter_span("第3章-第5章") == (3, 5)
    assert SS.parse_chapter_span("第十二章") == (12, 12)
    assert SS.parse_chapter_span("第一百零三章") == (103, 103)
    assert SS.parse_chapter_span("第3至5章") == (3, 5)
    # 任何附加限定/倒序/非章指代 → fail-closed 不可解析
    assert SS.parse_chapter_span("第3章前半") is None
    assert SS.parse_chapter_span("第5-3章") is None
    assert SS.parse_chapter_span("待补：第X章") is None
    assert SS.parse_chapter_span("狼患支线那几章") is None


def test_parse_chapter_spans_mixed():
    chapters, unparsed = SS.parse_chapter_spans(["第2章", "第4-5章", "第3章打斗段"])
    assert chapters == {2, 4, 5}
    assert unparsed == ["第3章打斗段"]


def _cut_thread(tid, spans, *, decision="cut", extra=None):
    t = {"id": tid, "name": f"线程{tid}", "class": "tangent", "serves_mainline": "偏离主线",
         "decision": decision, "weight": "low", "source_spans": spans, "cut_keywords": ["旁枝"],
         "opens_foreshadow": [], "pays_foreshadow": [],
         "connectivity": {"downstream_mainline_deps": [], "payoff_reroute": "主线一句带过",
                          "no_orphan_proof": "该线无伏笔"}}
    if extra:
        t.update(extra)
    return t


def test_spine_cut_chapter_plan_resolves_and_protects(tmp_path):
    comp = _comprehension([])
    spine = _good_spine([
        _cut_thread("THREAD_CUT", ["第4章", "第6-7章"]),
        _cut_thread("THREAD_KEEP", ["第6章"], decision="keep"),
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    plan = SS.spine_cut_chapter_plan(root)
    assert plan["status"] == "ok"
    # 第6章同时被 keep 线程锚定 → 冲突保留；第1章是主线 spine 锚（_good_spine 用第1章）不受影响
    assert sorted(plan["cut_chapters"]) == [4, 7]
    assert plan["conflicts"] and plan["conflicts"][0]["chapter"] == 6
    assert "thread:THREAD_KEEP" in plan["conflicts"][0]["protected_by"]


def test_spine_cut_chapter_plan_spine_anchor_protects(tmp_path):
    comp = _comprehension([])
    spine = _good_spine([_cut_thread("THREAD_CUT", ["第1章", "第4章"])])  # 第1章=主线锚
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    plan = SS.spine_cut_chapter_plan(root)
    assert sorted(plan["cut_chapters"]) == [4]
    assert any(c["chapter"] == 1 and "spine" in c["protected_by"] for c in plan["conflicts"])


def test_spine_cut_chapter_plan_explicit_source_chapters(tmp_path):
    comp = _comprehension([])
    spine = _good_spine([_cut_thread("THREAD_CUT", [], extra={"source_chapters": [8, 9]})])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    plan = SS.spine_cut_chapter_plan(root)
    assert sorted(plan["cut_chapters"]) == [8, 9]


def test_spine_cut_chapter_plan_requires_confirmed(tmp_path):
    comp = _comprehension([])
    spine = _good_spine([_cut_thread("THREAD_CUT", ["第4章"])], status="draft")
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    assert SS.spine_cut_chapter_plan(root)["status"] == "not_confirmed"


def test_check_warns_unparseable_cut_spans_and_reports_resolved(tmp_path):
    comp = _comprehension([])
    spine = _good_spine([
        _cut_thread("THREAD_BAD", ["狼患那几章"]),
        _cut_thread("THREAD_OK", ["第4章"]),
    ])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    report = SS.check(root)
    codes = {i["code"] for i in report["issues"]}
    assert "cut_thread_spans_unparseable" in codes
    assert "spine_cut_chapters_resolved" in codes
    # 解析性问题只 warn 不 block（B10：不因锚格式硬阻断创作）
    assert report["status"] != "block", [i for i in report["issues"] if i["severity"] == "block"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))


def test_chapter_heading_number():
    assert SS.chapter_heading_number("第4章 旧忆") == 4
    assert SS.chapter_heading_number("第十二回 风波再起") == 12
    assert SS.chapter_heading_number("正文里提到第4章的事") is None


def test_check_warns_when_cut_chapter_already_in_split_episode(tmp_path):
    comp = _comprehension([])
    spine = _good_spine([_cut_thread("THREAD_CUT", ["第4章"])])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    ep = root / "脚本" / "第2集"
    ep.mkdir(parents=True)
    (ep / "raw.txt").write_text("第4章 旧忆\n少年递来信物。\n", encoding="utf-8")
    report = SS.check(root)
    rows = [i for i in report["issues"] if i["code"] == "spine_cut_chapter_already_split"]
    assert rows and rows[0]["severity"] == "warn"
    assert rows[0]["evidence"]["episodes"][0]["episode"] == "第2集"
    assert report["status"] != "block"  # 追溯返工是显式决策，不阻断


def test_check_no_already_split_warning_when_raw_clean(tmp_path):
    comp = _comprehension([])
    spine = _good_spine([_cut_thread("THREAD_CUT", ["第4章"])])
    root = _mk(tmp_path, comprehension=comp, spine=spine, settings="主线剪枝: 突出主线")
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "raw.txt").write_text("第3章 反击\n她反击！\n", encoding="utf-8")
    report = SS.check(root)
    assert "spine_cut_chapter_already_split" not in {i["code"] for i in report["issues"]}
