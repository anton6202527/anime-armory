import json
from pathlib import Path

import pytest

import dependency_graph as dg


def _write(root: Path, rel: str, value=b"x"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        path.write_text(json.dumps(value), encoding="utf-8")
    elif isinstance(value, str):
        path.write_text(value, encoding="utf-8")
    else:
        path.write_bytes(value)
    return path


def _project(tmp_path: Path):
    root = tmp_path / "ad"
    _write(root, "需求/brief.json", {"brand": "A"})
    _write(root, "创意/concept.json", {
        "schema_version": 1, "kind": "ad_concept_pack", "big_idea": "旧创意",
        "key_message": "旧主张", "creative_route": "功能", "objective": "转化",
        "hypothesis": "演示能促成转化", "kv_direction": "产品特写",
        "usps": [{"id": "USP_01", "text": "卖点", "supports_key_message": True}],
    })
    _write(root, "创意/concept.md", "# 创意\n旧创意")
    _write(root, "创意/创意脚本.md", "旧 treatment")
    storyboard = {"shots": [
        {"shot_id": "S1", "duration": 1, "assets": {"PROD_A": True}},
        {"shot_id": "S2", "duration": 1, "assets": {"PROD_B": True}},
    ]}
    _write(root, "脚本/storyboard.json", storyboard)
    _write(root, "出图/共享/asset_registry.json", {
        "products": [{"id": "PROD_A", "spec": "red"}, {"id": "PROD_B", "spec": "blue"}]})
    for pos in (1, 2):
        _write(root, f"出图/分镜/prompt/镜头{pos:02d}.md", f"prompt {pos}")
        _write(root, f"出图/分镜/图片/镜头{pos:02d}.png", f"image {pos}".encode())
        _write(root, f"出视频/分镜/prompt/镜头{pos:02d}.md", f"video prompt {pos}")
        _write(root, f"出视频/分镜/视频/镜头{pos:02d}.mp4", f"video {pos}".encode())
    _write(root, "合规/locale_matrix.json", {"default_locale": "zh-CN"})
    plan = {"deliverables": [
        {"deliverable_id": "cut_s1", "kind": "cutdown", "duration": "1s",
         "expected_path": "合成/cut_s1.mp4"},
        {"deliverable_id": "cut_s2", "kind": "cutdown", "duration": "2s",
         "expected_path": "合成/cut_s2.mp4"},
    ]}
    _write(root, "合成/delivery_plan.json", plan)
    _write(root, "合成/cutdown/plan_1s.json", {"kept_shots": ["S1"]})
    _write(root, "合成/cutdown/plan_2s.json", {"kept_shots": ["S2"]})
    _write(root, "合成/cut_s1.mp4", b"cut one")
    _write(root, "合成/cut_s2.mp4", b"cut two")
    return root


def _status(report, node_id):
    return next(row["status"] for row in report["nodes"] if row["node_id"] == node_id)


def _accept_compose(root: Path):
    """Dependency tests isolate graph mechanics from the compose acceptor."""
    _write(root, "生产数据/stage_acceptance/compose.json", {
        "schema_version": 1, "kind": "ad_stage_acceptance", "stage": "compose", "mode": "formal",
        "contract_version": dg.contract.CONTRACT_VERSION,
        "acceptance_version": dg.contract.STAGE_ACCEPTANCE_VERSION,
        "dependency_snapshot_sha256": dg.stage_snapshot_sha256(root, "compose"),
        "findings": [], "summary": {"block": 0, "warn": 0, "accepted": True},
    })
    return dg.accept_stage(root, "compose")


def test_direct_compose_receipt_requires_current_formal_acceptance(tmp_path):
    root = _project(tmp_path)
    with pytest.raises(ValueError, match="formal accepted"):
        dg.accept_stage(root, "compose")


@pytest.mark.parametrize("rel", [
    "合成/delivery_qc.json",
    "生产数据/render_profile.json",
    "生产数据/placement_adaptation.json",
])
def test_compose_receipt_binds_release_evidence_bytes(tmp_path, rel):
    root = _project(tmp_path)
    _write(root, rel, {"revision": 1})
    _accept_compose(root)
    _write(root, rel, {"revision": 2})
    assert _status(dg.analyze(root), "compose:cut_s1") == "stale_input"


def test_compose_receipt_binds_whole_delivery_plan_and_final_media(tmp_path):
    root = _project(tmp_path)
    _write(root, "合成/delivery_qc.json", {"revision": 1})
    _accept_compose(root)
    plan = json.loads((root / "合成/delivery_plan.json").read_text(encoding="utf-8"))
    plan["audit_revision"] = 2
    _write(root, "合成/delivery_plan.json", plan)
    assert _status(dg.analyze(root), "compose:cut_s1") == "stale_input"

    _write(root, "合成/cut_s1.mp4", b"rerendered for plan revision 2")
    _write(root, "合成/cut_s2.mp4", b"rerendered second cut for plan revision 2")
    _accept_compose(root)
    _write(root, "合成/cut_s1.mp4", b"replaced after acceptance")
    assert _status(dg.analyze(root), "compose:cut_s1") == "stale_input"


def test_compose_receipt_binds_cross_ratio_execution_receipt_bytes(tmp_path):
    root = _project(tmp_path)
    plan_path = root / "合成" / "delivery_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    plan["deliverables"][0]["kind"] = "reframe"
    _write(root, "合成/delivery_plan.json", plan)
    receipt = _write(root, "生产数据/placement_adaptation_receipts/cut_s1.json", {"revision": 1})
    _accept_compose(root)
    receipt.write_text(json.dumps({"revision": 2}), encoding="utf-8")
    assert _status(dg.analyze(root), "compose:cut_s1") == "stale_input"


def test_dependency_graph_invalidates_only_changed_shot(tmp_path):
    root = _project(tmp_path)
    dg.accept_stage(root, "image")
    _write(root, "出图/分镜/prompt/镜头01.md", "changed S1 prompt")
    report = dg.analyze(root)
    assert _status(report, "image:S1") == "stale_input"
    assert _status(report, "image:S2") == "current"


def test_concept_json_change_invalidates_concept_script_and_storyboard(tmp_path):
    """机器真值改动必须让创意收据及两个直接消费工位同时失效。"""
    root = _project(tmp_path)
    _write(root, "脚本/广告脚本.md", "旧广告脚本")
    _write(root, "脚本/voiceover.txt", "旧旁白")
    _write(root, "脚本/时间轴.json", [{"start": 0, "end": 2}])
    _write(root, "脚本/广告法机检报告.json", {"summary": {"block": 0, "warn": 0}})
    _write(root, "脚本/镜头时长.json", {"findings": []})
    _write(root, "脚本/字幕_zh.srt", "1\n00:00:00,000 --> 00:00:01,000\n字幕\n")
    _write(root, "配音/时长清单.json", {"lines": [{"idx": 1, "seconds": 1.0}]})
    dg.accept_stage(root, "concept")
    dg.accept_stage(root, "script")
    dg.accept_stage(root, "storyboard")
    assert _status(dg.analyze(root), "concept") == "current"
    assert _status(dg.analyze(root), "script") == "current"
    assert _status(dg.analyze(root), "storyboard") == "current"

    pack = json.loads((root / "创意/concept.json").read_text(encoding="utf-8"))
    pack["big_idea"] = "新创意"
    _write(root, "创意/concept.json", pack)
    report = dg.analyze(root)

    assert _status(report, "concept") == "output_changed"
    assert _status(report, "script") == "stale_input"
    assert _status(report, "storyboard") == "stale_input"


def test_dependency_graph_invalidates_only_deliverable_using_changed_clip(tmp_path):
    root = _project(tmp_path)
    _accept_compose(root)
    _write(root, "出视频/分镜/视频/镜头01.mp4", b"changed video one")
    report = dg.analyze(root)
    assert _status(report, "compose:cut_s1") == "stale_input"
    assert _status(report, "compose:cut_s2") == "current"


def _voice_outputs(root: Path):
    _write(root, "脚本/voiceover.txt", "旁白：整理灵感。")
    _write(root, "配音/时长清单.json", {"lines": [{"idx": 1, "seconds": 1.0}]})
    _write(root, "配音/vo.wav", b"vo")
    _write(root, "配音/voice_qc.json", {"summary": {"block": 0, "warn": 0}})


def test_voicemap_change_invalidates_voice(tmp_path):
    """音色注册表在 voice 血缘内：改 voicemap.json 必须让 voice 节点 stale。"""
    root = _project(tmp_path)
    _voice_outputs(root)
    _write(root, "设定库/voicemap.json", {"旁白": {"voice_key": "VO_A"}})
    dg.accept_stage(root, "voice")
    assert _status(dg.analyze(root), "voice") == "current"
    _write(root, "设定库/voicemap.json", {"旁白": {"voice_key": "VO_B"}})
    assert _status(dg.analyze(root), "voice") == "stale_input"


def test_voicemap_created_after_acceptance_invalidates_voice(tmp_path):
    """voicemap 从缺到有也是输入变化：缺失时以 sentinel 参与哈希，补建后触发 stale。"""
    root = _project(tmp_path)
    _voice_outputs(root)
    dg.accept_stage(root, "voice")
    assert _status(dg.analyze(root), "voice") == "current"
    _write(root, "设定库/voicemap.json", {"旁白": {"voice_key": "VO_A"}})
    assert _status(dg.analyze(root), "voice") == "stale_input"


def test_vo_wav_change_invalidates_compose_default_branch(tmp_path):
    """无 locale matrix 分支：整轨 VO 是 compose 输入，重配音后 compose 必须 stale。"""
    root = _project(tmp_path)
    _write(root, "配音/vo.wav", b"vo v1")
    _accept_compose(root)
    assert _status(dg.analyze(root), "compose:cut_s1") == "current"
    _write(root, "配音/vo.wav", b"vo v2 re-recorded")
    report = dg.analyze(root)
    assert _status(report, "compose:cut_s1") == "stale_input"
    assert _status(report, "compose:cut_s2") == "stale_input"


def test_subtitle_created_after_acceptance_invalidates_compose(tmp_path):
    """发现时不存在的字幕也要无条件登记：后补文件必须触发 compose stale。"""
    root = _project(tmp_path)
    _accept_compose(root)
    assert _status(dg.analyze(root), "compose:cut_s1") == "current"
    _write(root, "脚本/字幕_zh.srt", "1\n00:00:00,000 --> 00:00:01,000\n后补字幕\n")
    assert _status(dg.analyze(root), "compose:cut_s1") == "stale_input"


def test_endcard_removed_after_acceptance_invalidates_compose(tmp_path):
    """从有到缺同样触发 stale：endcard 被删后 compose 不能仍算 current。"""
    root = _project(tmp_path)
    endcard = _write(root, "合成/_work/endcard.png", b"endcard")
    _accept_compose(root)
    assert _status(dg.analyze(root), "compose:cut_s1") == "current"
    endcard.unlink()
    assert _status(dg.analyze(root), "compose:cut_s1") == "stale_input"


def test_locale_change_invalidates_only_mapped_delivery_variant(tmp_path):
    root = _project(tmp_path)
    _write(root, "脚本/voiceover_zh.txt", "中文")
    _write(root, "脚本/字幕_zh.srt", "中文字幕")
    _write(root, "脚本/voiceover_en.txt", "English")
    _write(root, "脚本/字幕_en.srt", "English captions")
    _write(root, "合规/locale_matrix.json", {
        "default_locale": "zh-CN",
        "locales": {
            "zh-CN": {"voiceover_path": "脚本/voiceover_zh.txt", "subtitle_path": "脚本/字幕_zh.srt"},
            "en-US": {"voiceover_path": "脚本/voiceover_en.txt", "subtitle_path": "脚本/字幕_en.srt"},
        },
        "deliverable_locales": {"cut_s1": ["zh-CN"], "cut_s2": ["en-US"]},
    })
    _accept_compose(root)
    _write(root, "脚本/字幕_en.srt", "Changed English captions")
    report = dg.analyze(root)
    assert _status(report, "compose:cut_s1") == "current"
    assert _status(report, "compose:cut_s2") == "stale_input"


def test_evidence_byte_change_invalidates_handoff_and_review_receipts(tmp_path):
    root = _project(tmp_path)
    evidence = _write(root, "证据/commercial-disclosure.png", b"receipt-v1")
    brief = json.loads((root / "需求" / "brief.json").read_text(encoding="utf-8"))
    brief.update({
        "commercial_content": {"relationship_type": "brand_owned_paid_ad", "creator_involved": False},
        "commercial_disclosure_receipts": [{
            "deliverable_id": "cut_s1", "platform": "TikTok",
            "placement": "TikTok:auction_in_feed", "evidence_file": evidence.relative_to(root).as_posix(),
        }],
    })
    _write(root, "需求/brief.json", brief)
    for rel in (
        "生产数据/campaign_readiness.json", "合规/locale_matrix_validation.json",
        "合规/release_variant_manifest.json", "合规/compliance_manifest.json",
        "合成/delivery_qc.json", "合成/accessibility_qc.json", "合成/rendered_text_qc.json",
        "合成/asr_consistency.json", "生产数据/final_media_consistency.json",
        "生产数据/consistency_findings.json", "合规/ad_review_m0.json", "合规/human_signoff.json",
    ):
        _write(root, rel, {"summary": {"block": 0}})

    dg.accept_stage(root, "handoff")
    dg.accept_stage(root, "review")
    before = dg.analyze(root)
    assert _status(before, "handoff") == "current"
    assert _status(before, "review") == "current"

    evidence.write_bytes(b"receipt-v2-mutated-after-signoff")
    after = dg.analyze(root)
    assert _status(after, "handoff") == "stale_input"
    assert _status(after, "review") == "stale_input"


def test_handoff_receipt_depends_on_compose_acceptance_and_receipts(tmp_path):
    root = _project(tmp_path)
    _accept_compose(root)
    for rel in (
        "合规/ai_usage.json", "合规/locale_matrix_validation.json", "合规/provenance_qc.json",
        "生产数据/campaign_readiness.json", "合规/release_variant_manifest.json",
        "合规/compliance_manifest.json",
    ):
        _write(root, rel, {"summary": {"block": 0}})
    dg.accept_stage(root, "handoff")
    assert _status(dg.analyze(root), "handoff") == "current"

    acceptance_path = root / "生产数据/stage_acceptance/compose.json"
    acceptance = json.loads(acceptance_path.read_text(encoding="utf-8"))
    acceptance["review_note"] = "bytes changed"
    _write(root, "生产数据/stage_acceptance/compose.json", acceptance)
    assert _status(dg.analyze(root), "handoff") == "stale_input"

    # Restore/re-accept handoff, then prove the compose receipt subset itself is
    # a cycle-free handoff input (without hashing all downstream receipts).
    dg.accept_stage(root, "handoff", allow_unchanged_output=True)
    receipt_path = root / "生产数据/dependency_receipts.json"
    receipts = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipts["receipts"]["compose:cut_s1"]["accepted_at"] = "2099-01-01T00:00:00+00:00"
    _write(root, "生产数据/dependency_receipts.json", receipts)
    assert _status(dg.analyze(root), "handoff") == "stale_input"


def _feedback_project(tmp_path: Path):
    root = tmp_path / "feedback-ad"
    _write(root, "证据/readiness-proof.bin", b"readiness-proof-v1")
    _write(root, "需求/brief.json", {
        "campaign_mode": "formal", "evidence_file": "证据/readiness-proof.bin"})
    _write(root, "生产数据/campaign_readiness.json", {
        "kind": "ad_campaign_readiness", "mode": "formal",
        "summary": {"block": 0, "release_ready": True},
    })
    _write(root, "variants/A.mp4", b"variant-a-v1")
    _write(root, "variants/B.mp4", b"variant-b-v1")
    _write(root, "投放反馈/config-export.json", b"config-evidence-v1")
    _write(root, "投放反馈/result-evidence.json", b"result-evidence-v1")
    plan = {
        "design_mode": "platform_native",
        "variants": [
            {"variant_id": "A", "asset_path": "variants/A.mp4"},
            {"variant_id": "B", "asset_path": "variants/B.mp4"},
        ],
        "platform_experiment": {"config_receipt": {
            "evidence_path": "投放反馈/config-export.json",
        }},
    }
    _write(root, "投放反馈/experiment_plan.json", plan)
    _write(root, "投放反馈/experiment_plan_validation.json", {
        "schema_version": 3, "kind": "ad_experiment_plan_validation",
        "summary": {"block": 0, "warn": 0, "approved": True},
    })
    _write(root, "投放反馈/raw/results.csv", "variant_id,impressions,clicks\nA,100,10\nB,100,10\n")
    _write(root, "投放反馈/platform_experiment_result.json", {
        "evidence_path": "投放反馈/result-evidence.json"})
    _write(root, "投放反馈/feedback_report.json", {
        "schema_version": 5, "kind": "ad_feedback_report",
        "source_data": {"path": "投放反馈/raw/results.csv"},
        "analysis_receipts": {"raw_source": {"path": "投放反馈/raw/results.csv"}},
        "summary": {"block": 0, "warn": 0},
    })
    return root


def _mutate_feedback_input(path: Path):
    if path.suffix == ".json" and path.name not in {"config-export.json", "result-evidence.json"}:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["mutation_after_acceptance"] = True
        path.write_text(json.dumps(payload), encoding="utf-8")
    else:
        path.write_bytes(path.read_bytes() + b"\nmutation")


@pytest.mark.parametrize("rel", [
    "需求/brief.json",
    "证据/readiness-proof.bin",
    "生产数据/campaign_readiness.json",
    "投放反馈/experiment_plan.json",
    "投放反馈/experiment_plan_validation.json",
    "variants/A.mp4",
    "variants/B.mp4",
    "投放反馈/raw/results.csv",
    "投放反馈/config-export.json",
    "投放反馈/platform_experiment_result.json",
    "投放反馈/result-evidence.json",
])
def test_feedback_receipt_stales_when_any_analysis_input_changes(tmp_path, rel):
    root = _feedback_project(tmp_path)
    dg.accept_stage(root, "feedback")
    assert _status(dg.analyze(root), "feedback") == "current"

    _mutate_feedback_input(root / rel)

    assert _status(dg.analyze(root), "feedback") == "stale_input"


def test_feedback_dynamic_paths_use_sentinels_and_never_hash_outside_project(tmp_path):
    root = tmp_path / "confined-ad"
    outside = tmp_path / "outside-secret.bin"
    outside.write_bytes(b"outside-v1")
    link = root / "variants" / "escape.mp4"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    _write(root, "需求/brief.json", {"campaign_mode": "formal"})
    _write(root, "生产数据/campaign_readiness.json", {"summary": {"release_ready": True}})
    _write(root, "投放反馈/experiment_plan.json", {
        "design_mode": "platform_native",
        "variants": [
            {"variant_id": "absolute", "asset_path": str(outside)},
            {"variant_id": "traversal", "asset_path": "../outside-secret.bin"},
            {"variant_id": "symlink", "asset_path": "variants/escape.mp4"},
        ],
        "platform_experiment": {"config_receipt": {"evidence_path": str(outside)}},
    })
    _write(root, "投放反馈/experiment_plan_validation.json", {"summary": {"block": 0, "warn": 0}})
    _write(root, "投放反馈/platform_experiment_result.json", {
        "evidence_path": "variants/escape.mp4"})
    _write(root, "投放反馈/feedback_report.json", {
        "source_data": {"path": "../outside-secret.bin"},
        "analysis_receipts": {"raw_source": {"path": "../outside-secret.bin"}},
        "summary": {"block": 0, "warn": 0},
    })

    node = next(row for row in dg.discover(root) if row["node_id"] == "feedback")
    sentinels = [row for row in node["inputs"]
                 if str(row.get("name") or "").startswith("invalid_project_path:")]
    assert len(sentinels) >= 6
    assert dg.file_sha(outside) not in json.dumps(node["inputs"], ensure_ascii=False)
    before = node["input_sha256"]

    outside.write_bytes(b"outside-v2-that-must-never-enter-the-graph")
    after = next(row for row in dg.discover(root) if row["node_id"] == "feedback")

    assert after["input_sha256"] == before
