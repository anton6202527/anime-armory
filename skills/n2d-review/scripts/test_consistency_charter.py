#!/usr/bin/env python3
"""cd skills/n2d-review/scripts && python -m pytest test_consistency_charter.py

一致性不变量 charter 守护测试。核心断言：每个 locked 闸（may_be_profile_gated=False）在
gate.py 源码里**仍是无条件 BLOCK**，severity 没被偷偷塞进 `if profile==production`。谁以后
降级一个 locked 闸而不先改 charter，本测试立刻红——把"静默降级"挡在合入之前。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GATE_PY = HERE / "gate.py"

spec = importlib.util.spec_from_file_location("consistency_charter", HERE / "consistency_charter.py")
charter = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(charter)


def _gate_source() -> str:
    # 多文件源码全集（gate.py + gates/*.py）：按证据族拆分后 locked 闸可迁出 gate.py，charter 核对看全集。
    return charter.gate_source_text(HERE)


def test_charter_not_empty_and_well_formed():
    assert charter.CHARTER
    for name, e in charter.CHARTER.items():
        assert e.get("required_severity") == "block", f"{name} 缺 required_severity"
        assert "may_be_profile_gated" in e, f"{name} 必须显式声明 may_be_profile_gated"
        assert "may_be_opt_in" in e, f"{name} 必须显式声明 may_be_opt_in"
        assert e.get("rationale"), f"{name} 缺 rationale（裁决留痕）"


def test_every_charter_gate_exists_in_gate_py():
    """charter 登记的闸函数必须真存在于 gate.py（防改名/删除导致静默失效）。"""
    bodies = charter.top_level_bodies(_gate_source())
    missing = [n for n in charter.CHARTER if n not in bodies]
    assert not missing, f"charter 引用了 gate.py 不存在的闸函数：{missing}"


def test_gate_source_text_is_multifile(tmp_path):
    """按证据族拆分的 enabler：gate_source_text 必须把 gates/<family>.py 里的顶层 def 也纳入源码全集，
    否则迁出 gate.py 的 locked 闸会被 audit_source 误报 missing_gate（这正是要防的回归）。"""
    (tmp_path / "gate.py").write_text("def check_in_gate_py():\n    pass\n", encoding="utf-8")
    gates = tmp_path / "gates"
    gates.mkdir()
    (gates / "scene.py").write_text("def check_moved_to_gates_scene():\n    add(BLOCK)\n", encoding="utf-8")
    (gates / "__init__.py").write_text("", encoding="utf-8")
    (gates / "test_scene.py").write_text("def check_should_be_skipped():\n    pass\n", encoding="utf-8")
    bodies = charter.top_level_bodies(charter.gate_source_text(tmp_path))
    assert "check_in_gate_py" in bodies                  # gate.py 本体
    assert "check_moved_to_gates_scene" in bodies        # 迁出到 gates/ 的 locked 闸被纳入
    assert "check_should_be_skipped" not in bodies       # test_ 文件跳过


def test_enforcement_decisions_well_formed():
    """强制力决策日志：每条刻意分级的 severity 设计必须留痕，且其 guard_token 仍在对应 gate 源码里。

    这把"悄悄反转一条既定能力门控/分级"（如 44af5704）挡在合入前：谁把分级改回一刀切，
    guard_token（如 backend_supports_three_plus_frames）从函数体消失，本测试即红 → 逼一次显式 charter 更新。"""
    decisions = getattr(charter, "ENFORCEMENT_DECISIONS", None)
    assert decisions, "ENFORCEMENT_DECISIONS 不应为空"
    bodies = charter.top_level_bodies(_gate_source())
    seen_ids = set()
    for d in decisions:
        for k in ("id", "gate_function", "design", "guard_token", "rule", "rationale", "decided"):
            assert d.get(k), f"决策 {d.get('id')!r} 缺字段 {k}（裁决留痕不完整）"
        assert d["id"] not in seen_ids, f"决策 id 重复：{d['id']}"
        seen_ids.add(d["id"])
        body = bodies.get(d["gate_function"])
        assert body, f"决策 {d['id']} 指向不存在的 gate 函数 {d['gate_function']}"
        assert d["guard_token"] in body, (
            f"决策 {d['id']} 的 guard_token {d['guard_token']!r} 不在 {d['gate_function']} 源码里——"
            "该刻意分级设计可能被悄悄改回一刀切；要改请先更新 ENFORCEMENT_DECISIONS 留痕。")


def test_three_frame_graduated_severity_registered():
    """具体守护：三帧契约分级 severity 决策必须在册（防回退到 44af5704 的无条件 BLOCK）。"""
    ids = {d.get("id") for d in getattr(charter, "ENFORCEMENT_DECISIONS", [])}
    assert "three_frame_graduated_severity" in ids


def test_locked_gates_are_not_profile_gated():
    """★核心守护：locked 闸源码不得用 consistency_release_profile 决定 severity。"""
    violations = charter.audit_source(_gate_source())
    profile_gated = [v for v in violations if v["kind"] == "profile_gated"]
    assert not profile_gated, (
        "有 locked 一致性闸被悄悄降级为 profile-only（severity 进了 if production）：\n"
        + "\n".join(f"  - {v['problem']}" for v in profile_gated)
        + "\n若这是有意降级，请先在 consistency_charter.py 把该闸 may_be_profile_gated 改 True "
          "+ review_status=disputed_downgrade + 留痕；不要直接改 gate.py。"
    )


def test_no_missing_gate_violations():
    missing = [v for v in charter.audit_source(_gate_source()) if v["kind"] == "missing_gate"]
    assert not missing, "charter↔gate.py 失联：\n" + "\n".join(f"  - {v['problem']}" for v in missing)


def test_charter_completeness_no_unregistered_profile_gates():
    """★完整性守护：gate.py 里任何按 profile 决定 BLOCK 的函数都必须在 charter 登记裁决——
    根除'修了一个漏一个'。新增 profile 门控不登记即此测试红。"""
    unregistered = charter.find_unregistered_profile_gates(_gate_source())
    assert not unregistered, (
        "发现按 profile 决定 BLOCK 但未在 consistency_charter 登记的闸（漏网的潜在 demo 降级）：\n"
        + "\n".join(f"  - {n}" for n in unregistered)
        + "\n每个都必须在 charter 显式裁决：拉平就 may_be_profile_gated=False，"
          "确要保留 profile 门控就 =True + rationale 留痕。"
    )


def test_completeness_detector_catches_synthetic_unregistered():
    fake = (
        'def check_made_up_thing(root, ep, stage):\n'
        '    if consistency_release_profile(root) == "production":\n'
        '        add(BLOCK, "x", "y", "z")\n'
    )
    assert "check_made_up_thing" in charter.find_unregistered_profile_gates(fake, charter={})


def test_rehardened_gates_are_locked_not_disputed():
    """2026-06-27 裁决：曾被悄悄降级的脸漂总闸/参考规划闸已恢复无条件 BLOCK 并 locked。
    铁律=不准降级·demo 不降标准，故它们必须在 locked 集、不在 disputed 集。"""
    locked = set(charter.locked_gates())
    for name in ("check_long_running_weak_backend", "check_reference_plan_applied",
                 "check_core_anchor_pinning", "check_anchor_fingerprints",
                 # 第二批拉平（2026-06-27 默认全 False）
                 "check_asset_reference_registry", "_check_fidelity_gate_active",
                 "check_consistency_audit_gate", "_strict_advisory_should_block",
                 "check_action_beat_budget", "check_generation_recipe_evidence",
                 "_styleid_release_gate_required", "native_voice_identity_required"):
        assert name in locked, f"{name} 应已 locked（may_be_profile_gated=False）"
    assert charter.disputed_entries() == {}, "裁决后不应再有 disputed/opt-in 待决项"


def test_any_disputed_entry_has_null_decided():
    """若将来又出现 disputed 项，decided 必须为空（裁决了就改 review_status）。"""
    for name, e in charter.disputed_entries().items():
        assert e.get("decided") is None, f"{name} 仍 disputed 但已填 decided"


def test_detector_catches_a_synthetic_downgrade():
    """探测器自身有效性：构造一个 profile 门控的 locked 闸源码，必须被抓到。"""
    fake_source = (
        "def _x_severity(root, ep):\n"
        "    return BLOCK if consistency_release_profile(root) == 'production' else WARN\n"
        "\n"
        "def check_input_frame_qc(root, ep):\n"
        "    sev = _x_severity(root, ep)\n"
        "    add(sev, 'x', 'y', 'z')\n"
    )
    violations = charter.audit_source(fake_source, {"check_input_frame_qc": charter.CHARTER["check_input_frame_qc"]})
    assert any(v["kind"] == "profile_gated" for v in violations)


def test_detector_passes_a_clean_gate():
    clean = (
        "def check_input_frame_qc(root, ep):\n"
        "    if hard_blocks(root, ep):\n"
        "        add(BLOCK, 'x', 'y', 'z')\n"
    )
    violations = charter.audit_source(clean, {"check_input_frame_qc": charter.CHARTER["check_input_frame_qc"]})
    assert not violations
