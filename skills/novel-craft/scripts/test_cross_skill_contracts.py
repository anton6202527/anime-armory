#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跨 skill 接缝守护 — 锁住「文档声称的边 = 代码实际的边」。

每个 test 对应一处曾经静默失效的生产者/消费者接缝（A1/A2/A3/A4/B1/B2）。
若有人改回不兼容的键名/调用方式，这里立刻红，而不是等到跑真实项目才发现空账本/空检查。

运行：cd skills/novel-craft/scripts && python3 -m pytest test_cross_skill_contracts.py
"""
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
_LIB = os.path.abspath(os.path.join(HERE, "..", "..", "novel", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
_WIKI = os.path.abspath(os.path.join(HERE, "..", "..", "novel-wiki", "scripts"))
_REVIEW = os.path.abspath(os.path.join(HERE, "..", "..", "novel-review", "scripts"))

import propose_state_delta
import reconcile_ledger
import draft_packets
import report_gate
import consistency_scaffold as cs


# ── A1：state_delta 草案的键 ⊇ reconcile 真正消费的键 ──────────────────────────

def _merge_consumed_keys():
    """从 reconcile_ledger.merge_delta_to_ledger 源码抽 `delta.get("KEY"` —— 真实消费键。"""
    src = open(reconcile_ledger.__file__, encoding="utf-8").read()
    return set(re.findall(r'delta\.get\("([^"]+)"', src))


def test_proposer_emits_every_merge_consumed_key():
    consumed = _merge_consumed_keys()
    assert consumed, "没从 reconcile_ledger 抽到任何 delta.get 键——正则或源码变了"
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"))
        with open(os.path.join(root, "章节", "第01章.md"), "w", encoding="utf-8") as f:
            f.write("# 第1章\n沈念看向林照。\n")
        payload, _ = propose_state_delta.build_delta(root, 1)
    missing = consumed - set(payload)
    assert not missing, f"propose_state_delta 漏了 reconcile 会消费的键 {missing}（会被静默写空账本）"


def test_draft_packet_template_carries_merge_keys():
    consumed = _merge_consumed_keys()
    src = open(draft_packets.__file__, encoding="utf-8").read()
    for key in consumed:
        assert f'"{key}"' in src, f"draft_packets 状态增量模板缺消费键 {key}"


# ── A2：report_gate 导出模式与 export.py 传一致的闸门参数 ──────────────────────

def _run_report_gate(argv, root, meta_outputs=None):
    captured = {}

    def fake(root_arg, **kw):
        captured.update(kw)
        captured["_root"] = root_arg
        return {"blocking": False, "warnings": [], "blockers": []}

    if meta_outputs is not None:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"outputs": meta_outputs}, f, ensure_ascii=False)
    orig = report_gate.collect_gate_status
    old_argv = sys.argv
    report_gate.collect_gate_status = fake
    sys.argv = ["report_gate.py", *argv]
    try:
        try:
            report_gate.main()
        except SystemExit:
            pass
    finally:
        report_gate.collect_gate_status = orig
        sys.argv = old_argv
    return captured


def test_report_gate_export_mode_mirrors_export():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"))
        cap = _run_report_gate([root], root, meta_outputs=["txt", "docx"])
    # 非 progress 模式 = 模拟 export 硬闸：必须带 export_formats + 状态闭环，
    # 否则会静默漏掉 ai_usage / compliance / state-closure 三道。
    assert cap.get("export_formats") == ["txt", "docx"], cap
    assert cap.get("require_state_closure") is True, cap


def test_report_gate_progress_mode_stays_light():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "章节"))
        cap = _run_report_gate([root, "--progress-mode"], root, meta_outputs=["txt"])
    assert cap.get("export_formats") is None, cap
    assert cap.get("require_state_closure") is False, cap


# ── A3：伏笔巡检接进 consistency_audit ────────────────────────────────────────

def test_foreshadow_has_analyze_adapter():
    src = open(os.path.join(_WIKI, "foreshadow_ledger.py"), encoding="utf-8").read()
    assert "def analyze(" in src, "foreshadow_ledger 缺 analyze(project) 子检测器适配"


def test_consistency_audit_runs_foreshadow():
    src = open(os.path.join(_REVIEW, "consistency_audit.py"), encoding="utf-8").read()
    assert "foreshadow_ledger" in src, "consistency_audit 未 import foreshadow_ledger"
    assert "foreshadow" in src and "伏笔超期" in src, "consistency_audit 未把伏笔挂成子检测器"


def _consistency_detector_keys():
    """consistency_audit.main 结果字典里的检测器 section key（mechanical 走独立路径不算）。"""
    src = open(os.path.join(_REVIEW, "consistency_audit.py"), encoding="utf-8").read()
    block = src[src.index("result = {"):]
    block = block[:block.index("\n        }")]
    keys = set(re.findall(r'"(\w+)":\s*(?:_run_detector|run_\w+)\(', block))
    return keys - {"mechanical"}


def test_every_consistency_detector_surfaces_in_review_report():
    """每个 consistency_audit 检测器都必须在 build_review_report 的 CONSISTENCY_SECTION_MAP 里有
    映射，否则它的机检产出到不了 review_report→QA gate→修订计划（静默失效）。"""
    review_src = open(os.path.join(_REVIEW, "build_review_report.py"), encoding="utf-8").read()
    m = re.search(r"CONSISTENCY_SECTION_MAP\s*=\s*\{(.*?)\n\}", review_src, re.S)
    mapped = set(re.findall(r'\n    "([^"]+)":\s*\{', m.group(1)))
    detectors = _consistency_detector_keys()
    missing = detectors - mapped
    assert not missing, f"这些 consistency 检测器没接进 review_report：{missing}"


# ── A4：revision_plan 回流进写章 / 弧段包 ─────────────────────────────────────

def test_revision_plan_injected_into_chapter_packet():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "修订"))
        plan = {"kind": "novel_revision_plan", "tasks": [
            {"id": "REV-001", "priority": "P0", "chapter": 5, "title": "第5章人设崩",
             "recommended_skill": "novel-review", "return_to_stage": "review", "reason": "对齐动机"},
        ]}
        with open(os.path.join(root, "修订", "revision_plan.json"), "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False)
        sec = draft_packets.revision_section_for_chapter(root, 5)
        assert "本章待处理修订项" in sec and "第5章人设崩" in sec, sec
        # 不命中本章 + 无全书级 P0 → 空，不污染其它章节包
        assert draft_packets.revision_section_for_chapter(root, 99) == ""


# ── B1：派生线一致性注册表脚手架按题材门控 ────────────────────────────────────

def test_registry_scaffold_gated_by_genre():
    power = dict(cs.consistency_registry_files("系统流"))
    assert "设定/character_guardrails.json" in power
    assert "设定/power_system_registry.json" in power
    nonpower = dict(cs.consistency_registry_files("现代言情"))
    assert "设定/character_guardrails.json" in nonpower  # 始终 seed
    assert "设定/power_system_registry.json" not in nonpower  # 非力量题材不 seed


# ── B2：角色卡命名兜底（角色卡.md / 人物.md）───────────────────────────────────

def test_resolve_character_card_accepts_both_names():
    with tempfile.TemporaryDirectory() as root:
        sdir = os.path.join(root, "设定")
        os.makedirs(sdir)
        assert cs.resolve_character_card(root) is None  # 都没有
        with open(os.path.join(sdir, "人物.md"), "w", encoding="utf-8") as f:
            f.write("## 沈念\n")
        assert cs.resolve_character_card(root).endswith("人物.md")  # 派生线命名也认
        with open(os.path.join(sdir, "角色卡.md"), "w", encoding="utf-8") as f:
            f.write("## 沈念\n")
        assert cs.resolve_character_card(root).endswith("角色卡.md")  # 两者都在时优先 角色卡.md


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ok  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
