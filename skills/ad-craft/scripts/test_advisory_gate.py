"""advisory 侧车并入 gate 的降档纪律。

本线的分界线由 score_findings 立下：创意/启发式只提示复核，只有广告法与确定性闸门能 BLOCK。
这些测试锁的就是这条——新增的编剧轴与参考处方侧车，无论自身报什么，都不得把 gate 变成硬阻断。
"""
import json
import os
import time
from pathlib import Path

import gate


def _write(root: Path, rel: str, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _report(block=0, warn=0, available=True):
    return {"schema_version": 1, "available": available,
            "summary": {"block": block, "warn": warn, "info": 0}, "findings": []}


def _by_code(findings):
    return {f["code"]: f["severity"] for f in findings}


def test_missing_advisory_report_is_info_never_block(tmp_path):
    """报告缺失只提示「建议先跑」——advisory 与 product_qc 那类硬闸的分界线。"""
    for fn in (gate.reference_plan_findings, gate.creative_axis_findings):
        findings = fn(str(tmp_path))
        assert findings, fn.__name__
        assert {f["severity"] for f in findings} == {"info"}, fn.__name__


def test_sidecar_block_is_downgraded_to_warn(tmp_path):
    """侧车即使报 block，也只能降为 warn 并入 gate——第二道保险。"""
    _write(tmp_path, "生产数据/ad_reference_plan.json", _report(block=3))

    codes = _by_code(gate.reference_plan_findings(str(tmp_path)))

    assert codes["ad_reference_plan_advisory"] == "warn"
    assert "block" not in codes.values()


def test_sidecar_warn_is_downgraded_to_info(tmp_path):
    _write(tmp_path, "生产数据/ad_copy_quality_audit.json", _report(warn=2))

    codes = _by_code(gate.creative_axis_findings(str(tmp_path)))

    assert codes["ad_copy_quality_warn"] == "info"


def test_unavailable_report_is_reported_not_treated_as_pass(tmp_path):
    """缺料降级 ≠ 通过。available=false 必须说出来，不能静默当作干净。"""
    _write(tmp_path, "生产数据/ad_idea_payoff_audit.json", _report(available=False))

    codes = _by_code(gate.creative_axis_findings(str(tmp_path)))

    assert codes["ad_idea_payoff_unavailable"] == "info"


def test_stale_advisory_report_warns(tmp_path):
    """干净但过期的侧车不是新产物的证据——但这里只 warn，不像硬闸那样 block。"""
    _write(tmp_path, "生产数据/ad_reference_plan.json", _report())
    storyboard = _write(tmp_path, "脚本/storyboard.json", {"shots": []})
    later = time.time() + 60
    os.utime(storyboard, (later, later))

    codes = _by_code(gate.reference_plan_findings(str(tmp_path)))

    assert codes["ad_reference_plan_stale"] == "warn"


def test_advisory_sidecars_never_block_any_gate_stage(tmp_path):
    """端到端：侧车全线报 block，gate 的 block 计数不得因它们增加。"""
    for rel in ("生产数据/ad_reference_plan.json", "生产数据/ad_concept_pack_check.json",
                "生产数据/ad_idea_payoff_audit.json", "生产数据/ad_copy_quality_audit.json"):
        _write(tmp_path, rel, _report(block=5, warn=5))

    for stage in gate.STAGES:
        payload = gate.run_gate(str(tmp_path), stage)
        advisory = [f for f in payload["findings"]
                    if f["code"].startswith(("ad_reference_plan", "ad_concept_pack",
                                             "ad_idea_payoff", "ad_copy_quality"))]
        assert advisory, stage
        assert all(f["severity"] != "block" for f in advisory), stage


def test_reference_plan_only_runs_at_image_stage(tmp_path):
    """参考处方是出图前的事前处方；video/compose 阶段图已生成，再提示已无意义。"""
    codes_by_stage = {stage: _by_code(gate.run_gate(str(tmp_path), stage)["findings"])
                      for stage in gate.STAGES}

    assert "ad_reference_plan_missing" in codes_by_stage["image"]
    assert "ad_reference_plan_missing" not in codes_by_stage["compose"]
