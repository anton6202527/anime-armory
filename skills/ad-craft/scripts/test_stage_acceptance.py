import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract  # noqa: E402
import stage_acceptance as sa  # noqa: E402


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
    sa.dependency_graph.accept_stage(tmp_path, "brief")
    report = sa.evaluate(tmp_path, "concept")
    assert report["summary"]["block"] == 0


def test_formal_stage_cannot_skip_missing_upstream_hash_receipts(tmp_path):
    write(tmp_path, "创意/concept.md", "Big Idea key message 广告目标 创意假设 强制项")
    write(tmp_path, "创意/创意脚本.md", "treatment")
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
