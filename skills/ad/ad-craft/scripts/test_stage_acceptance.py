import csv
import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract  # noqa: E402
import stage_acceptance as sa  # noqa: E402

_AD_FEEDBACK_SCRIPTS = Path(__file__).resolve().parents[2] / "ad-feedback" / "scripts"
if str(_AD_FEEDBACK_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_AD_FEEDBACK_SCRIPTS))
from _test_readiness_fixture import write_formal_readiness  # noqa: E402


def _stamp(path, seconds_ago):
    when = time.time() - seconds_ago
    os.utime(path, (when, when))


def _codes(report):
    return {f["code"] for f in report["findings"]}


def write(root, rel, value):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    else:
        path.write_text(value, encoding="utf-8")
    return path


def concept_pack(**overrides):
    payload = {
        "schema_version": 1,
        "kind": "ad_concept_pack",
        "big_idea": "把一天的元气装进一个盒子",
        "key_message": "0 糖也能有元气",
        "creative_route": "生活方式片",
        "objective": "转化行动",
        "hypothesis": "目标受众会因低负担卖点采取行动",
        "kv_direction": "晨光中的产品特写",
        "usps": [{"id": "USP_01", "text": "0 糖 0 卡", "supports_key_message": True}],
        "storyline": [{"section": "钩子", "desc": "打开产品", "planned_seconds": 3}],
    }
    payload.update(overrides)
    return payload


def test_every_contract_stage_has_explicit_typed_criteria():
    for stage in contract.stage_table():
        rows = contract.stage_criteria(stage["key"])
        assert rows
        assert all(row["evidence"] in {"deterministic", "official", "house", "human", "heuristic"} for row in rows)
        assert all(row.get("authority") and row.get("threshold") and row.get("on_fail") for row in rows)


def test_brief_acceptance_requires_campaign_objective(tmp_path):
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"], "audience": "A"})
    report = sa.evaluate(tmp_path, "brief")
    assert report["summary"]["accepted"] is False
    assert any("campaign_objective" in f["msg"] for f in report["findings"])


def test_concept_acceptance_has_machine_completion_standard(tmp_path):
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"],
                                         "audience": "A", "campaign_objective": "转化行动"})
    write(tmp_path, "创意/concept.md", "# 概念\n## Big Idea\nX\n## 一句话主张\nY\n## 广告目标\n转化\n## 创意假设\nH1\n## 强制项\nLogo")
    write(tmp_path, "创意/创意脚本.md", "故事展开")
    write(tmp_path, "创意/concept.json", concept_pack())
    sa.dependency_graph.accept_stage(tmp_path, "brief")
    report = sa.evaluate(tmp_path, "concept")
    assert report["summary"]["block"] == 0


def test_concept_markdown_keywords_cannot_replace_machine_truth(tmp_path):
    """旧 Markdown 即使把全部关键词写齐，formal 仍须 fail closed。"""
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"],
                                         "audience": "A", "campaign_objective": "转化行动"})
    write(tmp_path, "创意/concept.md",
          "Big Idea 一句话主张 广告目标 创意假设 为什么 强制项 mandatories logo 法律声明")
    write(tmp_path, "创意/创意脚本.md", "故事展开")
    sa.dependency_graph.accept_stage(tmp_path, "brief")

    report = sa.evaluate(tmp_path, "concept")

    assert "concept_machine_truth_missing" in _codes(report)
    assert report["summary"]["accepted"] is False


def test_concept_structural_blocks_come_from_machine_truth(tmp_path):
    """concept_pack 的确定性结构 block 必须进入承重阶段验收。"""
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"],
                                         "audience": "A", "campaign_objective": "转化行动"})
    write(tmp_path, "创意/concept.md", "人读视图")
    write(tmp_path, "创意/创意脚本.md", "故事展开")
    write(tmp_path, "创意/concept.json", concept_pack(big_idea="待补", usps=[]))
    sa.dependency_graph.accept_stage(tmp_path, "brief")

    report = sa.evaluate(tmp_path, "concept")

    assert {"concept_field_pending", "usps_empty"} <= _codes(report)
    assert report["summary"]["accepted"] is False


def test_concept_malformed_json_fails_closed(tmp_path):
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"],
                                         "audience": "A", "campaign_objective": "转化行动"})
    write(tmp_path, "创意/concept.md", "人读视图")
    write(tmp_path, "创意/创意脚本.md", "故事展开")
    write(tmp_path, "创意/concept.json", "{not-json")
    sa.dependency_graph.accept_stage(tmp_path, "brief")

    assert "concept_machine_truth_malformed" in _codes(sa.evaluate(tmp_path, "concept"))


def test_formal_concept_blocks_objective_divergence_but_rough_warns(tmp_path):
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"],
                                         "audience": "A", "campaign_objective": "品牌认知"})
    write(tmp_path, "创意/concept.md", "人读视图")
    write(tmp_path, "创意/创意脚本.md", "故事展开")
    write(tmp_path, "创意/concept.json", concept_pack(objective="转化行动"))
    sa.dependency_graph.accept_stage(tmp_path, "brief")

    formal = [row for row in sa.evaluate(tmp_path, "concept", "formal")["findings"]
              if row["code"] == "objective_brief_mismatch"]
    rough = [row for row in sa.evaluate(tmp_path, "concept", "rough")["findings"]
             if row["code"] == "objective_brief_mismatch"]

    assert formal and formal[0]["severity"] == "block"
    assert rough and rough[0]["severity"] == "warn"


def test_formal_stage_cannot_skip_missing_upstream_hash_receipts(tmp_path):
    write(tmp_path, "创意/concept.md", "Big Idea key message 广告目标 创意假设 强制项")
    write(tmp_path, "创意/创意脚本.md", "treatment")
    write(tmp_path, "创意/concept.json", concept_pack())
    report = sa.evaluate(tmp_path, "concept")
    assert any(row["code"] == "dependency_receipts_missing" and row["severity"] == "block"
               for row in report["findings"])


def test_compose_acceptance_blocks_missing_planned_deliverable(tmp_path):
    write(tmp_path, "合成/delivery_plan.json", {"deliverables": [
        {"deliverable_id": "master", "exists": True},
        {"deliverable_id": "cut_6s", "exists": False},
    ]})
    write(tmp_path, "合成/delivery_qc.json", {"summary": {"block": 0, "warn": 0},
                                                "items": [{"deliverable_id": "master", "passed": True}]})
    report = sa.evaluate(tmp_path, "compose")
    assert any(f["code"] == "deliverable_not_accepted" for f in report["findings"])


def test_compose_distrusts_exists_flag_and_rechecks_disk(tmp_path):
    """delivery_plan 自报 exists=True 不作数：expected_path 磁盘缺失照样 block。"""
    write(tmp_path, "合成/delivery_plan.json", {"deliverables": [
        {"deliverable_id": "master", "exists": True, "expected_path": "合成/成片_主片.mp4"},
    ]})
    write(tmp_path, "合成/delivery_qc.json", {"summary": {"block": 0, "warn": 0},
                                                "items": [{"deliverable_id": "master", "passed": True}]})
    report = sa.evaluate(tmp_path, "compose")
    assert any(f["code"] == "deliverable_not_accepted" for f in report["findings"])
    # 文件真实落盘后同一检查放行。
    write(tmp_path, "合成/成片_主片.mp4", "master-bytes")
    report = sa.evaluate(tmp_path, "compose")
    assert not any(f["code"] == "deliverable_not_accepted" for f in report["findings"])


def test_compose_record_writes_formal_acceptance_before_dependency_receipt(tmp_path, monkeypatch):
    write(tmp_path, "合成/delivery_plan.json", {"deliverables": [{
        "deliverable_id": "master", "expected_path": "合成/成片_主片.mp4",
    }]})
    write(tmp_path, "合成/成片_主片.mp4", "master-bytes")
    monkeypatch.setattr(sa.dependency_graph, "upstream_findings", lambda *_args, **_kwargs: [])
    monkeypatch.setitem(sa.ACCEPTORS, "compose", lambda _root, _out, _mode: None)

    payload = sa.evaluate(tmp_path, "compose", "formal")
    report_path = sa.record_acceptance(tmp_path, payload)

    assert report_path.is_file()
    assert payload["summary"]["accepted"] is True
    assert sa.dependency_graph.compose_acceptance_status(tmp_path)["accepted"] is True


def test_voice_blocks_when_voicemap_newer_than_manifest(tmp_path):
    manifest = write(tmp_path, "配音/时长清单.json", {"lines": [
        {"idx": 1, "seconds": 1.0, "voice_key": "VO_A", "line_wav": "line_01.wav"}]})
    voicemap = write(tmp_path, "设定库/voicemap.json", {"旁白": {"voice_key": "VO_B"}})
    _stamp(manifest, 600)
    _stamp(voicemap, 60)  # 音色绑定改于清单之后
    report = sa.evaluate(tmp_path, "voice")
    assert "voice_manifest_voicemap_stale" in _codes(report)


def test_voice_accepts_older_or_missing_voicemap(tmp_path):
    manifest = write(tmp_path, "配音/时长清单.json", {"lines": [
        {"idx": 1, "seconds": 1.0, "voice_key": "VO_A", "line_wav": "line_01.wav"}]})
    # voicemap 缺失：不新增要求。
    assert "voice_manifest_voicemap_stale" not in _codes(sa.evaluate(tmp_path, "voice"))
    voicemap = write(tmp_path, "设定库/voicemap.json", {"旁白": {"voice_key": "VO_A"}})
    _stamp(voicemap, 600)
    _stamp(manifest, 60)  # 清单晚于 voicemap = 已按当前绑定重算
    assert "voice_manifest_voicemap_stale" not in _codes(sa.evaluate(tmp_path, "voice"))


def test_image_blocks_stale_registry_snapshot_like_gate(tmp_path):
    """母本晚于快照的对账与花钱 gate 同口径，在验收侧也要 block。"""
    master = write(tmp_path, "设定库/asset_registry.json", {"brand": {"id": "B", "name": "改过"}})
    snapshot = write(tmp_path, "出图/共享/asset_registry.json", {"brand": {"id": "B", "name": "旧"}})
    _stamp(snapshot, 600)
    _stamp(master, 60)
    report = sa.evaluate(tmp_path, "image")
    assert any(f["code"] == "asset_registry_snapshot_stale" and f["severity"] == "block"
               for f in report["findings"])


def test_image_fresh_registry_snapshot_passes(tmp_path):
    master = write(tmp_path, "设定库/asset_registry.json", {"brand": {"id": "B"}})
    snapshot = write(tmp_path, "出图/共享/asset_registry.json", {"brand": {"id": "B"}})
    _stamp(master, 600)
    _stamp(snapshot, 60)
    assert "asset_registry_snapshot_stale" not in _codes(sa.evaluate(tmp_path, "image"))


def test_paid_stage_without_gate_record_warns_not_blocks(tmp_path):
    report = sa.evaluate(tmp_path, "image")
    rows = [f for f in report["findings"] if f["code"] == "gate_report_missing"]
    assert rows and all(f["severity"] == "warn" for f in rows)


def test_fresh_gate_record_silences_advisory_and_stale_record_warns(tmp_path):
    brief = write(tmp_path, "需求/brief.json", {"brand": "B"})
    record = write(tmp_path, "生产数据/gate_reports/image.json",
                   {"kind": "ad_gate_report", "stage": "image", "summary": {"block": 0}})
    _stamp(brief, 600)
    _stamp(record, 60)  # 落档晚于关键输入 = 有效
    codes = _codes(sa.evaluate(tmp_path, "image"))
    assert "gate_report_missing" not in codes and "gate_report_stale" not in codes
    _stamp(record, 600)
    _stamp(brief, 60)  # 关键输入晚于落档 = gate 结论过期
    report = sa.evaluate(tmp_path, "image")
    assert any(f["code"] == "gate_report_stale" and f["severity"] == "warn"
               for f in report["findings"])


def _timeline_report(tmp_path, payload):
    write(tmp_path, "脚本/广告脚本.md", "S1：展示产品。")
    write(tmp_path, "脚本/voiceover.txt", "旁白：一句。")
    write(tmp_path, "脚本/时间轴.json", payload)
    return sa.evaluate(tmp_path, "script")


def test_timeline_valid_structure_passes(tmp_path):
    report = _timeline_report(tmp_path, [{"start": 0, "end": 2, "shot_id": "S1"},
                                          {"start": 2, "end": 5, "shot_id": "S2"}])
    assert not any(f["code"].startswith("timeline_") for f in report["findings"])


def test_timeline_blocks_start_not_before_end(tmp_path):
    report = _timeline_report(tmp_path, [{"start": 3, "end": 3, "shot_id": "S1"}])
    assert "timeline_segment_invalid" in _codes(report)


def test_timeline_blocks_overlapping_segments(tmp_path):
    report = _timeline_report(tmp_path, [{"start": 0, "end": 3, "shot_id": "S1"},
                                          {"start": 2, "end": 5, "shot_id": "S2"}])
    assert "timeline_overlap" in _codes(report)


def test_timeline_blocks_missing_fields(tmp_path):
    report = _timeline_report(tmp_path, [{"shot_id": "S1", "duration": 3}])
    assert "timeline_segment_fields_missing" in _codes(report)


def test_timeline_blocks_total_mismatch(tmp_path):
    report = _timeline_report(tmp_path, {"master_seconds": 30, "segments": [
        {"start": 0, "end": 3}, {"start": 3, "end": 10}]})
    assert "timeline_total_mismatch" in _codes(report)


def test_timeline_dict_with_consistent_total_passes(tmp_path):
    report = _timeline_report(tmp_path, {"master_seconds": 10, "segments": [
        {"start": 0, "end": 3}, {"start": 3, "end": 10}]})
    assert not any(f["code"].startswith("timeline_") for f in report["findings"])


def test_brief_deferred_warn_mentions_gate_severity(tmp_path):
    write(tmp_path, "需求/brief.json", {"brand": "B", "product": "P", "usp": ["U"],
                                         "audience": "A", "campaign_objective": "转化"})
    report = sa.evaluate(tmp_path, "brief")
    rows = [f for f in report["findings"] if f["code"] == "brief_production_pending"]
    assert rows and all(f["severity"] == "warn" for f in rows)
    assert "花钱 gate 将按 block 处理" in rows[0]["msg"]


def _feedback_plan(root: Path, *, native=False):
    assets = []
    for variant_id, hook_id in (("A", "H1"), ("B", "H2")):
        path = root / "variants" / f"{variant_id}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((f"asset-{variant_id}-" * 20).encode("utf-8"))
        assets.append({
            "variant_id": variant_id, "hook_id": hook_id,
            "message_id": "M1", "cta_id": "C1", "allocation": 0.5,
            "asset_path": path.relative_to(root).as_posix(), "asset_sha256": sa.sha(path),
        })
    plan = {
        "design_mode": "platform_native" if native else "local_binomial",
        "hypothesis": "hook 提升 CTR", "primary_kpi": "CTR",
        "conversion_event": "purchase", "attribution_window": "7d_click",
        "platform": "TikTok", "placement": "auction_in_feed", "audience": "prospecting",
        "randomization_unit": "impression", "analysis_unit": "impression",
        "independent_bernoulli": True,
        "decision_rule": "multiplicity-adjusted pooled two-proportion score test",
        "start_date": "2026-07-01", "end_date": "2026-07-31", "min_impressions": 100,
        "held_constant": {"budget": "50/50", "bidding": "same", "landing_page": "same",
                          "placement": "auction_in_feed"},
        "variants": assets,
    }
    if native:
        config_path = root / "投放反馈" / "config-export.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_bytes(b"native-config-evidence-v1")
        plan["platform_experiment"] = {
            "experiment_id": "exp-no-winner",
            "config_receipt": {
                "experiment_id": "exp-no-winner", "status": "configured",
                "evidence_path": config_path.relative_to(root).as_posix(),
                "evidence_sha256": sa.sha(config_path),
                "asset_bindings": {row["variant_id"]: row["asset_sha256"] for row in assets},
            },
        }
    else:
        plan.update({
            "metric_definition": {"numerator": "clicks", "denominator": "impressions"},
            "baseline_rate": 0.05, "minimum_detectable_effect": 0.05,
            "alpha": 0.05, "power": 0.8, "multiple_comparison_method": "none",
            "stopping_rule": {"type": "fixed_sample", "minimum_sample_per_arm": "computed",
                              "no_early_stopping": True},
        })
    return plan


def _complete_feedback_project(root: Path, *, native=False):
    root.mkdir(parents=True, exist_ok=True)
    write_formal_readiness(root, "CTR")
    plan = _feedback_plan(root, native=native)
    validation = sa.feedback_experiment_plan.build(plan, root)
    assert validation["summary"]["approved"] is True
    write(root, "投放反馈/experiment_plan.json", plan)
    write(root, "投放反馈/experiment_plan_validation.json", validation)

    if native:
        evidence = root / "投放反馈" / "result-evidence.txt"
        evidence.write_bytes(b"platform completed: no winner")
        write(root, "投放反馈/platform_experiment_result.json", {
            "experiment_id": "exp-no-winner", "status": "completed", "primary_kpi": "CTR",
            "conclusion": "no_winner", "winner_variant_id": None,
            "asset_bindings": {row["variant_id"]: row["asset_sha256"] for row in plan["variants"]},
            "evidence_path": evidence.relative_to(root).as_posix(),
            "evidence_sha256": sa.sha(evidence),
        })
        impressions = 5000
    else:
        impressions = max(5000, int(validation["power_analysis"]["effective_stopping_sample_per_arm"]))

    raw = root / "source-results.csv"
    with raw.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=(
            "variant_id", "platform", "placement", "audience",
            "impressions", "clicks", "conversions", "spend", "revenue"))
        writer.writeheader()
        for variant_id in ("A", "B"):
            writer.writerow({
                "variant_id": variant_id, "platform": "TikTok",
                "placement": "auction_in_feed", "audience": "prospecting",
                "impressions": impressions, "clicks": max(1, impressions // 20),
                "conversions": max(1, impressions // 200), "spend": 100, "revenue": 200,
            })
    assert sa.feedback_ingest.main([str(root), "--input", str(raw)]) == 0
    report = json.loads((root / "投放反馈" / "feedback_report.json").read_text(encoding="utf-8"))
    assert report["analysis_status"] == "complete"
    assert report["winner"] is None
    return report


def _feedback_acceptance_codes(root: Path):
    findings = []
    sa.accept_feedback(root.resolve(), findings, "formal")
    return {row["code"] for row in findings}, findings


@pytest.mark.parametrize("native", [False, True])
def test_feedback_complete_no_winner_passes_formal_acceptance(tmp_path, native):
    root = tmp_path / ("native" if native else "local")
    _complete_feedback_project(root, native=native)

    _codes_, findings = _feedback_acceptance_codes(root)

    assert not [row for row in findings if row["severity"] == "block"]


def test_feedback_interim_cannot_pass_formal_acceptance(tmp_path):
    root = tmp_path / "project"
    report = _complete_feedback_project(root)
    report["analysis_status"] = "interim"
    write(root, "投放反馈/feedback_report.json", report)

    codes, _ = _feedback_acceptance_codes(root)

    assert "feedback_analysis_incomplete" in codes


@pytest.mark.parametrize("field,value", [
    ("kind", "not_a_feedback_report"),
    ("schema_version", 4),
])
def test_feedback_report_requires_current_kind_and_schema(tmp_path, field, value):
    root = tmp_path / "project"
    report = _complete_feedback_project(root)
    report[field] = value
    write(root, "投放反馈/feedback_report.json", report)

    assert "feedback_report_contract_invalid" in _feedback_acceptance_codes(root)[0]


def test_feedback_rejects_tampered_derived_validation_even_with_fresh_file_receipt(tmp_path):
    root = tmp_path / "project"
    report = _complete_feedback_project(root)
    validation_path = root / "投放反馈" / "experiment_plan_validation.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    validation["power_analysis"]["effective_stopping_sample_per_arm"] = 1
    write(root, "投放反馈/experiment_plan_validation.json", validation)
    report["analysis_receipts"]["experiment_validation"]["sha256"] = sa.sha(validation_path)
    write(root, "投放反馈/feedback_report.json", report)

    codes, _ = _feedback_acceptance_codes(root)

    assert "experiment_validation_semantic_stale" in codes


def test_feedback_rejects_tampered_report_semantics(tmp_path):
    root = tmp_path / "project"
    report = _complete_feedback_project(root)
    report["winner"] = "A"
    write(root, "投放反馈/feedback_report.json", report)

    assert "feedback_report_semantic_stale" in _feedback_acceptance_codes(root)[0]


@pytest.mark.parametrize("rel", [
    "需求/brief.json",
    "生产数据/campaign_readiness.json",
    "投放反馈/experiment_plan.json",
    "投放反馈/experiment_plan_validation.json",
    "variants/A.mp4",
    "variants/B.mp4",
    "投放反馈/raw/source-results.csv",
])
def test_feedback_analysis_receipts_reject_mutated_local_inputs(tmp_path, rel):
    root = tmp_path / "project"
    _complete_feedback_project(root)
    path = root / rel
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["mutated_after_analysis"] = True
        write(root, rel, payload)
    else:
        path.write_bytes(path.read_bytes() + b"\nmutated")

    codes, _ = _feedback_acceptance_codes(root)

    assert "feedback_analysis_receipt_stale" in codes


@pytest.mark.parametrize("rel", [
    "投放反馈/config-export.json",
    "投放反馈/platform_experiment_result.json",
    "投放反馈/result-evidence.txt",
])
def test_feedback_analysis_receipts_reject_mutated_native_inputs(tmp_path, rel):
    root = tmp_path / "project"
    _complete_feedback_project(root, native=True)
    path = root / rel
    if path.name == "platform_experiment_result.json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["mutated_after_analysis"] = True
        write(root, rel, payload)
    else:
        path.write_bytes(path.read_bytes() + b"\nmutated")

    codes, _ = _feedback_acceptance_codes(root)

    assert "feedback_analysis_receipt_stale" in codes


@pytest.mark.parametrize("escape", ["absolute", "traversal", "symlink"])
def test_feedback_raw_source_rejects_path_escape(tmp_path, escape):
    root = tmp_path / "project"
    report = _complete_feedback_project(root)
    outside = tmp_path / "outside.csv"
    outside.write_text("variant_id,impressions,clicks\nA,1,1\n", encoding="utf-8")
    if escape == "absolute":
        malicious = str(outside)
    elif escape == "traversal":
        malicious = "../outside.csv"
    else:
        link = root / "投放反馈" / "raw" / "escape.csv"
        link.symlink_to(outside)
        malicious = link.relative_to(root).as_posix()
    report["source_data"].update({"path": malicious, "sha256": sa.sha(outside)})
    report["analysis_receipts"]["raw_source"].update({"path": malicious, "sha256": sa.sha(outside)})
    write(root, "投放反馈/feedback_report.json", report)

    codes, _ = _feedback_acceptance_codes(root)

    assert "feedback_analysis_path_invalid" in codes
    assert "feedback_source_path_invalid" in codes


def test_feedback_variant_asset_symlink_escape_is_rejected(tmp_path):
    root = tmp_path / "project"
    _complete_feedback_project(root)
    outside = tmp_path / "outside.mp4"
    outside.write_bytes(b"outside-media")
    asset = root / "variants" / "A.mp4"
    asset.unlink()
    asset.symlink_to(outside)

    assert "feedback_analysis_path_invalid" in _feedback_acceptance_codes(root)[0]


def _fps_manifest(root: Path, monkeypatch):
    profile = {
        "profile_sha256": "p" * 64,
        "source_generation": {
            "width": 1920, "height": 1080, "resolution": "1920x1080",
            "aspect": "16:9", "fps": 24,
        },
    }
    write(root, "生产数据/render_profile.json", profile)
    monkeypatch.setattr(sa.render_profile, "compile_profile", lambda _root: profile)
    output = write(root, "出视频/分镜/视频/镜头01.mp4", "video-bytes")
    output_sha = sa.sha(output)
    ref = {"sha256": profile["profile_sha256"]}
    return {
        "render_profile": ref,
        "jobs": [{
            "job_id": "S1", "status": "done", "render_profile": ref,
            "render_profile_sha256": profile["profile_sha256"],
            "video_resolution": "1920x1080", "requested_source_fps": 24, "source_fps": 24,
            "output": "出视频/分镜/视频/镜头01.mp4", "output_sha256": output_sha,
            "observed_output": {"width": 1920, "height": 1080, "fps": 24,
                                "output_sha256": output_sha},
        }],
    }


@pytest.mark.parametrize("mutation", [
    {"requested_source_fps": None},
    {"requested_source_fps": 30},
    {"source_fps": None},
    {"source_fps": 30},
])
def test_video_request_fps_requires_authoritative_and_legacy_fields(tmp_path, monkeypatch, mutation):
    manifest = _fps_manifest(tmp_path, monkeypatch)
    manifest["jobs"][0].update(mutation)
    findings = []

    sa.accept_video_render_profile(tmp_path, findings, manifest)

    assert any(row["code"] == "video_request_fps_mismatch" and row["severity"] == "block"
               for row in findings)


def test_video_request_fps_accepts_matching_authoritative_and_legacy_fields(tmp_path, monkeypatch):
    manifest = _fps_manifest(tmp_path, monkeypatch)
    findings = []

    sa.accept_video_render_profile(tmp_path, findings, manifest)

    assert not [row for row in findings if row["code"] == "video_request_fps_mismatch"]
