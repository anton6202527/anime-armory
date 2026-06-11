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
    consistency_dim_key,
    consistency_dim_spec,
    consistency_dimensions,
    stage_for_key,
    stage_for_progress_column,
    stage_requires_for_mode,
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


def test_stage_requires_for_mode_drops_voice_in_native_av():
    spec = stage_for_key("image_prompt")
    assert spec is not None
    assert "配音" in spec["requires"]
    assert "配音" not in stage_requires_for_mode(spec, "原生音画")
    assert "配音" in stage_requires_for_mode(spec, "配音先行")


def test_consistency_dimensions_are_single_source():
    dims = consistency_dimensions()
    assert dims["character_consistency"]["return_to_stage"] == "image"
    assert dims["contract_inheritance"]["return_to_stage"] == "video_prompt"
    assert consistency_dim_key("脸(G1)") == "character_consistency"
    assert consistency_dim_key("视觉契约继承") == "contract_inheritance"
    assert consistency_dim_spec("状态百科(P1)")["scope"]


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
    assert "n2d-batch" not in skills                    # 无就绪标志的横切工具不进 readiness 行
    comp = next(x for x in cc if x["skill"] == "n2d-compliance")
    assert comp["required_before"]                      # 合规是付费阶段硬前置
    am = next(x for x in cc if x["skill"] == "n2d-asset-market")
    assert am["artifact"] is None                       # 仓库级，无 per-work 标志


def test_cross_cutting_tools_are_separate_from_readiness():
    import n2d_contract as c
    tools = c.cross_cutting_tools()
    skills = {x["skill"] for x in tools}
    assert {"n2d-model-router", "n2d-batch", "n2d-progress", "n2d-review"} <= skills
    assert c.CROSS_CUTTING is c.CROSS_CUTTING_READINESS  # legacy alias means readiness-tracked only


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
    assert c.PRODUCT_KINDS is c.BOUNDARY_PRODUCT_KINDS   # legacy alias; new name says this is boundary metadata


def test_json_kind_constants_cover_cross_cutting_outputs():
    import n2d_contract as c
    assert c.BATCH_QUEUE_KIND == "n2d_batch_queue"
    assert c.PRODUCTION_EVENT_KIND == "n2d_production_event"
    assert c.PRODUCTION_DASHBOARD_KIND == "n2d_production_dashboard"
    assert c.PLATFORM_FEEDBACK_KIND == "n2d_platform_feedback"
    assert c.REVIEW_UI_KIND == "n2d_review_ui"
    assert c.EPISODE_REVIEW_SCORE_KIND == "n2d_episode_review_score"
    assert c.SCORE_VISUAL_CHECKS_KIND == "n2d_score_visual_checks"
    assert c.SKILL_UPDATE_SNAPSHOT_KIND == "n2d_skill_update_snapshot"
    assert c.SKILL_UPDATE_PLAN_KIND == "n2d_skill_update_plan"


# ── 共享路径 / 目录单一真值源 ──────────────────────────────────────────────
def test_production_dir_and_registry_path():
    import n2d_contract as c
    assert c.production_dir("/w/") == "/w/生产数据"
    assert c.identity_registry_path("/w") == "/w/出图/共享/identity_registry.json"
    # registry 路径取自 BOUNDARY_PRODUCT_KINDS 注册的 path —— move 时只改一处
    assert c.BOUNDARY_PRODUCT_KINDS[c.IDENTITY_REGISTRY_KIND]["path"] in c.identity_registry_path("/w")


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


# ── T6: finding schema 三端归一 ──────────────────────────────────────────────
import n2d_contract as _c6


def test_resolve_dim_key_from_key_label_keyword():
    assert _c6.resolve_dim_key("character_consistency") == "character_consistency"   # 已是 key
    assert _c6.resolve_dim_key("角色一致性") == "character_consistency"               # 中文 label
    assert _c6.resolve_dim_key("这镜脸崩了") == "character_consistency"               # 关键词「脸」
    assert _c6.resolve_dim_key("声纹漂移") == "voice_consistency"                     # 音色/声纹也是一致性维度
    assert _c6.resolve_dim_key("毫不相关的东西") == ""                                # 解析不出


def test_normalize_finding_absorbs_three_emit_styles():
    # review 侧
    a = _c6.normalize_finding({"severity": "block", "dimension": "角色一致性", "message": "崩脸",
                               "affected_shots": ["Clip_03"]})
    # review-ui 侧（sev/dim/msg）
    b = _c6.normalize_finding({"sev": "block", "dim": "角色一致性", "msg": "崩脸", "affected_shots": ["Clip_03"]})
    # score 侧（dimensions 复数 + verdict）
    c = _c6.normalize_finding({"verdict": "block", "dimensions": ["character_consistency"], "msg": "崩脸"})
    for r in (a, b, c):
        assert r["severity"] == "block"
        assert r["dim_key"] == "character_consistency"
        assert r["return_to_stage"] == "image"        # 未给则按 dim_key 从契约回退
    assert a["message"] == b["message"] == "崩脸"
    assert a["affected_shots"] == ["Clip_03"]


def test_normalize_finding_keeps_explicit_return_stage():
    r = _c6.normalize_finding({"sev": "warn", "dim": "字幕正确性", "return_to_stage": "compose"})
    assert r["return_to_stage"] == "compose"           # 显式给的不被覆盖
    assert r["dim_key"] == "subtitle_correctness"


def test_make_consistency_finding_factory():
    f = _c6.make_consistency_finding("block", "场景一致性", "场景漂移", affected_shots=["Clip_05"])
    assert f["severity"] == "block" and f["dim_key"] == "scene_consistency"
    assert f["return_to_stage"] == "image" and f["affected_shots"] == ["Clip_05"]


def test_finding_dim_key_falls_back():
    assert _c6.finding_dim_key({"dimension": "character_consistency"}) == "character_consistency"
    assert _c6.finding_dim_key({"dimension": "自定义维度"}) == "自定义维度"   # 解析不出→原文
    assert _c6.finding_dim_key({}) == "一致性"                              # 全空→兜底


def test_finding_fingerprint_can_scope_to_shot():
    coarse = _c6.finding_fingerprint("第1集", "image", "character_consistency")
    scoped = _c6.finding_fingerprint("第1集", "image", "character_consistency", "Clip_03")
    assert coarse != scoped
    assert _c6.finding_fingerprints(
        "第1集", "image", "character_consistency", {"affected_shots": ["Clip_03", "Clip_05"]}
    ) == [
        _c6.finding_fingerprint("第1集", "image", "character_consistency", "Clip_03"),
        _c6.finding_fingerprint("第1集", "image", "character_consistency", "Clip_05"),
    ]


# ── T11: 镜头类型判定关键词单一真值源 ────────────────────────────────────────
def test_shot_type_keywords_single_source():
    keys = [st for st, _ in _c6.SHOT_TYPE_KEYWORDS]
    assert "fight_exchange" in keys and "general_motion" not in keys  # general 是兜底，不在表里
    # 专项模板子集 ⊆ 全表，且排除纯近景说话/空镜（它们不需要专项模板）
    special = dict(_c6.special_template_keywords())
    assert set(special).issubset(set(keys))
    assert "dialogue_closeup" not in special and "empty_establishing" not in special
    assert "fight_exchange" in special and "multi_character_same_frame" in special
    # 派生保序且关键词与全表一致
    assert special["fight_exchange"] == dict(_c6.SHOT_TYPE_KEYWORDS)["fight_exchange"]
