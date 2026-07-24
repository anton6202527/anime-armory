#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""editorial_revision 编辑提案生成器 + 防瞎编校验单测。
cd skills/n2d-script/scripts && python -m pytest test_editorial_revision.py -q"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import editorial_revision as er


def _mk(root, *, comprehension=None, spine=None):
    root = Path(root)
    if comprehension is not None:
        p = root / "设定库" / "source_comprehension.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"understanding_contract": comprehension}, ensure_ascii=False), encoding="utf-8")
    if spine is not None:
        p = root / "开发包" / "story_spine.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(spine, ensure_ascii=False), encoding="utf-8")
    return root


# ── pure signal functions ────────────────────────────────────────────────────

def test_foreshadow_debt_flags_open_unpaid():
    ledger = [
        {"trace_id": "F1", "status": "open"},                 # unpaid → debt
        {"trace_id": "F2", "status": "open"},                 # paid by thread → not debt
        {"trace_id": "F3", "status": "open", "do_not_drop_reason": "核心"},  # protected unpaid → debt
    ]
    threads = [{"id": "T1", "pays_foreshadow": ["F2"]}]
    debt = er.foreshadow_debt(ledger, threads)
    ids = {d["foreshadow_id"] for d in debt}
    assert ids == {"F1", "F3"}
    assert next(d for d in debt if d["foreshadow_id"] == "F3")["protected"] is True


def test_mainline_gap_flags_uncovered_must_keep():
    chain = [
        {"trace_id": "C1", "must_keep": "主线承接"},   # not fed by spine → gap
        {"trace_id": "C2", "must_keep": "主线承接"},   # fed → ok
        {"trace_id": "C3", "must_keep": ""},           # not must_keep → ignored
    ]
    spine = [{"id": "SPINE_01", "depends_on": ["C2"]}]
    gaps = er.mainline_gap(chain, spine)
    assert {g["causal_id"] for g in gaps} == {"C1"}


def test_contribution_score_protects_mainline_carrier():
    ledger = [{"trace_id": "F1", "do_not_drop_reason": "核心"}]
    carrier = {"id": "T1", "class": "supporting", "decision": "keep", "weight": "high",
               "pays_foreshadow": ["F1"], "connectivity": {"downstream_mainline_deps": ["C1", "C2"]}}
    tangent = {"id": "T2", "class": "tangent", "decision": "keep", "weight": "low",
               "pays_foreshadow": [], "connectivity": {}}
    assert er.thread_contribution(carrier, ledger)["score"] > er.thread_contribution(tangent, ledger)["score"]
    assert er.thread_contribution(tangent, ledger)["score"] <= 0


def test_spine_class_never_becomes_tangent_candidate():
    ledger = []
    threads = [{"id": "S", "class": "spine", "decision": "keep"}]
    assert er.tangent_candidates(threads, ledger) == []


def test_tangent_candidates_ranks_lowest_first():
    ledger = []
    threads = [
        {"id": "T_low", "class": "tangent", "decision": "keep", "weight": "low"},
        {"id": "T_mid", "class": "supporting", "decision": "keep", "weight": "mid"},  # score 1 == threshold
        {"id": "T_cut", "class": "tangent", "decision": "cut"},  # already cut → not re-proposed
    ]
    cands = er.tangent_candidates(threads, ledger)
    ids = [c["thread_id"] for c in cands]
    assert "T_cut" not in ids
    assert ids[0] == "T_low"  # lowest score first


# ── build_worksheet ──────────────────────────────────────────────────────────

def test_build_worksheet_end_to_end(tmp_path):
    root = _mk(tmp_path,
              comprehension={
                  "foreshadowing_ledger": [{"trace_id": "F1", "status": "open"}],
                  "causality_chain": [{"trace_id": "C1", "must_keep": "主线承接"}],
              },
              spine={"spine": [{"id": "SPINE_01", "depends_on": []}],
                     "threads": [{"id": "T1", "class": "tangent", "decision": "keep", "weight": "low"}]})
    ws = er.build_worksheet(root)
    assert ws["summary"]["foreshadow_debt"] == 1
    assert ws["summary"]["mainline_gaps"] == 1
    assert ws["summary"]["tangent_candidates"] == 1
    assert ws["inputs_missing"] == []


# ── check: anti-fabrication + continuity ─────────────────────────────────────

def _write_ws(root, ledger_rows):
    ws = er.build_worksheet(root)
    ws["revision_ledger"] = ledger_rows
    (root / "开发包").mkdir(parents=True, exist_ok=True)
    (root / "开发包" / "editorial_revision_worksheet.json").write_text(
        json.dumps(ws, ensure_ascii=False), encoding="utf-8")


def _base(tmp_path):
    return _mk(tmp_path,
               comprehension={"foreshadowing_ledger": [{"trace_id": "F1", "status": "open"}],
                              "causality_chain": [{"trace_id": "C1", "must_keep": "x"}]},
               spine={"spine": [{"id": "SPINE_01", "depends_on": ["C1"]}],
                      "threads": [{"id": "T1", "class": "tangent", "decision": "keep"}]})


def test_check_blocks_fabricated_id(tmp_path):
    root = _base(tmp_path)
    _write_ws(root, [{"action": "cut", "target_thread_id": "T_GHOST", "reroute": "x"}])
    res = er.check(root)
    assert res["status"] == "blocked"
    assert any(i["code"] == "fabricated_id" for i in res["issues"])


def test_check_blocks_cut_without_reroute(tmp_path):
    root = _base(tmp_path)
    _write_ws(root, [{"action": "cut", "target_thread_id": "T1"}])
    res = er.check(root)
    assert res["status"] == "blocked"
    assert any(i["code"] == "cut_without_reroute" for i in res["issues"])


def test_check_passes_valid_edit(tmp_path):
    root = _base(tmp_path)
    _write_ws(root, [{"action": "cut", "target_thread_id": "T1", "reroute": "信息已在 SPINE_01 交代",
                      "source_trace": ["C1"]}])
    res = er.check(root)
    assert res["status"] == "pass", res["issues"]


def test_check_warns_unaddressed_protected_debt(tmp_path):
    root = _mk(tmp_path,
               comprehension={"foreshadowing_ledger": [{"trace_id": "F1", "status": "open", "do_not_drop_reason": "核心"}],
                              "causality_chain": []},
               spine={"spine": [], "threads": []})
    _write_ws(root, [])
    res = er.check(root)
    assert any(i["code"] == "unaddressed_protected_debt" for i in res["issues"])


def test_check_missing_worksheet_warns(tmp_path):
    root = _base(tmp_path)
    res = er.check(root)
    assert any(i["code"] == "worksheet_missing" for i in res["issues"])
    assert res["status"] == "pass"  # missing = warn, not block


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
