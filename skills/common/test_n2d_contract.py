#!/usr/bin/env python3
"""Tests for the n2d machine-readable contract."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from n2d_contract import (  # noqa: E402
    CINEMATIC_CONTRACT_FIELDS,
    CONTRACT_VERSION,
    GATE_STAGES,
    STYLE_CONTRACT_FIELDS,
    annotate_finding,
    episode_manifest_path,
    routing_stages,
    stage_for_progress_column,
    write_episode_manifest,
)


def test_routing_stages_are_derived_from_contract():
    stages = routing_stages()
    labels = [s[1] for s in stages]
    assert labels[:3] == ["阶段1·剧本改编", "角色配音", "阶段2·分镜设计"]
    assert ("成片",) == tuple(stages[-1][0])


def test_style_contract_fields_are_machine_readable():
    assert STYLE_CONTRACT_FIELDS == (
        "风格名",
        "视觉基调",
        "镜头与构图",
        "光色策略",
        "运动边界",
        "风格禁忌",
    )


def test_legacy_cinematic_contract_fields_are_machine_readable():
    assert CINEMATIC_CONTRACT_FIELDS == (
        "摄影基调",
        "镜头焦段",
        "光源动机",
        "色彩策略",
        "运镜边界",
        "真实感禁忌",
    )


def test_progress_column_maps_to_owner_and_stage():
    spec = stage_for_progress_column("视频prompt")
    assert spec is not None
    assert spec["key"] == "video_prompt"
    assert spec["owner"] == "n2d-video"


def test_gate_finding_annotation_adds_recovery_scope():
    finding = {"sev": "block", "dim": "prompt", "loc": "x", "msg": "bad"}
    out = annotate_finding(finding, "video", ep="第3集")
    assert "video" in GATE_STAGES
    assert out["return_to_stage"] == "video_prompt"
    assert any("第3集" in p for p in out["affected_artifacts"])
    assert out["msg"] == "bad"


def test_write_episode_manifest_records_artifact_hash(tmp_path):
    root = str(tmp_path)
    ep_dir = tmp_path / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "storyboard.json").write_text('{"clips":[]}\n', encoding="utf-8")
    path = write_episode_manifest(root, "第1集", stage="script_stage2")
    assert path == episode_manifest_path(root, "第1集")
    data = json.loads(open(path, encoding="utf-8").read())
    assert data["kind"] == "n2d_episode_manifest"
    assert data["schema_version"] == CONTRACT_VERSION
    assert data["stage"] == "script_stage2"
    storyboard = next(a for a in data["artifacts"] if a["path"] == "脚本/第1集/storyboard.json")
    assert storyboard["exists"] is True
    assert storyboard["sha256"]


def test_cross_cutting_registry():
    import n2d_contract as c
    cc = c.cross_cutting()
    skills = {x["skill"] for x in cc}
    assert {"n2d-compliance", "n2d-identity", "n2d-lora", "n2d-asset-market",
            "n2d-dashboard", "n2d-score", "n2d-review-ui", "n2d-feedback"} <= skills
    comp = next(x for x in cc if x["skill"] == "n2d-compliance")
    assert comp["required_before"]                      # 合规是付费阶段硬前置
    am = next(x for x in cc if x["skill"] == "n2d-asset-market")
    assert am["artifact"] is None                       # 仓库级，无 per-work 标志


# ── ③ Motion Control / LoRA ready 判定单一真值源 ──────────────────────────
def test_motion_control_required_single_source():
    import n2d_contract as c
    assert c.motion_control_required("fight_exchange") is True
    assert c.motion_control_required("hug_or_pull") is True
    assert c.motion_control_required("dialogue_closeup") is False
    # risk_flags 路径：物理接触标记也触发
    assert c.motion_control_required(risk_flags=["physical_interaction"]) is True
    assert c.motion_control_required("closeup", risk_flags=["mouth_visible"]) is False
    assert c.motion_control_required() is False


def test_lora_ready_judgment_single_source():
    import n2d_contract as c
    assert c.lora_verdict_ok("pass") is True
    assert c.lora_verdict_ok("fail") is False
    assert c.lora_verdict_ok("") is False
    # report 必填字段 ⊆ registry ready 字段（model_sha256 落库后叫 model_hash + 多 validation_report 回链）
    assert "model_sha256" in c.LORA_REPORT_REQUIRED_FIELDS
    assert "model_hash" in c.LORA_REGISTRY_READY_FIELDS
    assert "validation_report" in c.LORA_REGISTRY_READY_FIELDS


# ── ① 产物 kind 注册表（含与 identity_registry 的边界）──────────────────────
def test_product_kinds_registered_with_boundary():
    import n2d_contract as c
    vs = c.product_kind(c.VISUAL_STATE_LEDGER_KIND)
    assert vs["owner"] == "n2d-image"
    assert "identity_registry" in vs["boundary"]        # 定性：与身份层分工写明
    idr = c.product_kind(c.IDENTITY_REGISTRY_KIND)
    assert "visual_state_ledger" in idr["boundary"]     # 反向也点明
    assert c.product_kind(c.MOTION_CONTROL_MANIFEST_KIND)["owner"].startswith("n2d-model-router")
    assert c.product_kind("nope") is None


def test_json_kind_constants_cover_cross_cutting_outputs():
    import n2d_contract as c
    assert c.BATCH_QUEUE_KIND == "n2d_batch_queue"
    assert c.PRODUCTION_EVENT_KIND == "n2d_production_event"
    assert c.PRODUCTION_DASHBOARD_KIND == "n2d_production_dashboard"
    assert c.PLATFORM_FEEDBACK_KIND == "n2d_platform_feedback"
    assert c.REVIEW_UI_KIND == "n2d_review_ui"
    assert c.EPISODE_REVIEW_SCORE_KIND == "n2d_episode_review_score"
    assert c.SCORE_VISUAL_CHECKS_KIND == "n2d_score_visual_checks"


# ── 共享路径 / 目录单一真值源 ──────────────────────────────────────────────
def test_production_dir_and_registry_path():
    import n2d_contract as c
    assert c.production_dir("/w/") == "/w/生产数据"
    assert c.identity_registry_path("/w") == "/w/出图/共享/identity_registry.json"
    # registry 路径取自 PRODUCT_KINDS 注册的 path —— move 时只改一处
    assert c.PRODUCT_KINDS[c.IDENTITY_REGISTRY_KIND]["path"] in c.identity_registry_path("/w")


# ── identity 共享字段 / 后端能力表 ─────────────────────────────────────────
def test_identity_reference_and_handle_fields():
    import n2d_contract as c
    assert c.IDENTITY_REFERENCE_KEYS == ("front", "side", "back", "outfit", "turnaround")
    assert c.IDENTITY_HANDLE_FIELDS == ("id", "handle", "reference", "model_path")


def test_identity_adapter_table_default_mode_in_allowed():
    import n2d_contract as c
    for adapters in (c.IDENTITY_IMAGE_ADAPTERS, c.IDENTITY_VIDEO_ADAPTERS):
        for backend, spec in adapters.items():
            assert spec["default_mode"] in spec["allowed_modes"], backend  # 重置出的 mode 必过校验
    # reset 模板带 handle 字段时初始为空串
    img = c.identity_reset_template(c.IDENTITY_IMAGE_ADAPTERS)
    assert img["kling"] == {"mode": "subject_library", "status": "unregistered", "id": ""}
    assert img["codex"] == {"mode": "reference_group", "status": "fallback_reference_group"}
    assert img["dreamina"] == {"mode": "reference_group", "status": "fallback_reference_group"}
    allowed = c.identity_allowed_modes(c.IDENTITY_IMAGE_ADAPTERS)
    assert allowed["seedream"] == ("universal_reference",)


def test_image_backend_classification_allows_official_dreamina_cli():
    import n2d_contract as c
    assert c.classify_image_backend("Dreamina") == ("dreamina", "approved")
    assert c.classify_image_backend("即梦") == ("dreamina", "approved")
    assert c.classify_image_backend("同视频AI") == ("", "forbidden")


def test_lora_ready_blocks_single_source():
    from n2d_contract import (
        lora_dataset_warning_blocks,
        lora_gap_message,
        lora_registry_ready_blocks,
        lora_report_ready_blocks,
    )

    # 数据集警告覆核：无警告→空；有警告无放行→缺口；放行但无 notes→缺口；放行+notes→空。
    assert lora_dataset_warning_blocks({}) == []
    assert lora_dataset_warning_blocks({"warnings": ["dataset_has_warnings"]}) == [
        "dataset_warnings_without_override"
    ]
    assert lora_dataset_warning_blocks(
        {"warnings": ["dataset_has_warnings"], "manual_review": {"allow_dataset_warnings": True}}
    ) == ["dataset_warnings_override_notes_missing"]
    assert (
        lora_dataset_warning_blocks(
            {
                "warnings": ["dataset_has_warnings"],
                "manual_review": {"allow_dataset_warnings": True, "notes": "已人工抽查 20 张"},
            }
        )
        == []
    )

    good_report = {
        "kind": "n2d_lora_validation_report",
        "verdict": "pass",
        "base_model": "sdxl",
        "model_path": "设定库/lora/x.safetensors",
        "trigger": "shenian",
        "model_sha256": "abc",
    }
    assert lora_report_ready_blocks(good_report) == []
    bad = dict(good_report, verdict="fail", trigger="")
    blocks = lora_report_ready_blocks(bad)
    assert "validation_verdict_not_pass:fail" in blocks
    assert "missing_report_field:trigger" in blocks

    good_cfg = {
        "base_model": "sdxl",
        "model_path": "设定库/lora/x.safetensors",
        "trigger": "shenian",
        "validation_report": "设定库/lora/validation_report.json",
        "model_hash": "abc",
    }
    assert lora_registry_ready_blocks(good_cfg, good_report) == []
    assert "ready_model_hash_mismatch" in lora_registry_ready_blocks(
        dict(good_cfg, model_hash="def"), good_report
    )
    # 报告路径非空但读不出 → ready_validation_report_missing
    assert "ready_validation_report_missing" in lora_registry_ready_blocks(good_cfg, None)
    # 报告路径为空 → 只报 ready_missing_validation_report，不重复报 report_missing
    no_report_cfg = dict(good_cfg, validation_report="")
    blocks = lora_registry_ready_blocks(no_report_cfg, None)
    assert blocks == ["ready_missing_validation_report"]

    assert lora_gap_message("ready_missing_trigger") == "LoRA ready 但缺字段：trigger"
    assert "verdict=pass" in lora_gap_message("ready_validation_report_not_pass")


def test_identity_adapter_status_sets():
    from n2d_contract import (
        IDENTITY_ADAPTER_KNOWN_STATUSES,
        IDENTITY_ADAPTER_READY_STATUSES,
    )

    assert "ready" in IDENTITY_ADAPTER_READY_STATUSES
    assert "fallback_reference_group" in IDENTITY_ADAPTER_KNOWN_STATUSES
    assert "candidate" in IDENTITY_ADAPTER_KNOWN_STATUSES


def test_classify_redraw_reason():
    from n2d_contract import REDRAW_REASON_CATEGORIES, classify_redraw_reason

    assert classify_redraw_reason("第3镜沈念崩脸，五官漂了") == "face_consistency"
    assert classify_redraw_reason("参考图被裁切导致构图不对") == "reference_cropping"
    assert classify_redraw_reason("背景光位和上一镜对不上") == "scene_drift"
    assert classify_redraw_reason("随便写的原因") == "other"
    assert classify_redraw_reason("") == "other"
    # 直接传枚举键原样返回
    assert classify_redraw_reason("face_consistency") == "face_consistency"
    assert set(c for c, _ in []) <= set(REDRAW_REASON_CATEGORIES)


def test_migrate_legacy_shared_assets(tmp_path):
    from n2d_contract import migrate_legacy_shared_assets

    root = tmp_path / "剧"
    legacy = root / "出图" / "common"
    legacy.mkdir(parents=True)
    (legacy / "identity_registry.json").write_text("{}", encoding="utf-8")

    # 只有 legacy → 整体改名
    result = migrate_legacy_shared_assets(str(root))
    assert result["removed_legacy"] is True
    assert (root / "出图" / "共享" / "identity_registry.json").is_file()
    assert not legacy.exists()

    # 并存 + 冲突 → 冲突文件留在旧目录，不覆盖
    legacy.mkdir(parents=True)
    (legacy / "identity_registry.json").write_text('{"old": true}', encoding="utf-8")
    (legacy / "extra.json").write_text("{}", encoding="utf-8")
    result = migrate_legacy_shared_assets(str(root))
    assert result["conflicts"] == ["identity_registry.json"]
    assert "extra.json" in result["moved"]
    assert (legacy / "identity_registry.json").read_text(encoding="utf-8") == '{"old": true}'
    assert (root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8") == "{}"


def test_voicemap_contract():
    from n2d_contract import VOICE_KEY_FIELD, voicemap_path

    assert voicemap_path("/tmp/剧").endswith("设定库/voicemap.json")
    assert VOICE_KEY_FIELD == "voice_key"
