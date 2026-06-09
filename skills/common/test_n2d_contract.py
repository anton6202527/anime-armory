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
