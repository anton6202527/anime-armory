#!/usr/bin/env python3
"""Shared schemas and metadata for the n2d pipeline."""

from __future__ import annotations
from typing import Dict, List, Any, Tuple
try:
    from n2d_const import *
except ImportError:
    from .n2d_const import *

# ── n2d 边界型机器产物注册表 ──────────────────────────────────────────────
BOUNDARY_PRODUCT_KINDS = {
    MANIFEST_KIND: {
        "owner": "n2d (contract)",
        "path": "脚本/{ep}/manifest.json",
        "layer": "contract",
        "boundary": "episode_summary",
    },
    IDENTITY_REGISTRY_KIND: {
        "owner": "n2d-image",
        "writer_owner": "n2d-image",
        "schema_owner": "n2d (contract)",
        "consumer_owner": "n2d-identity",
        "path": f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
        "layer": "shared_asset",
        "boundary": "identity_definition",
    },
    ASSET_REFERENCE_REGISTRY_KIND: {
        "owner": "n2d-asset-market",
        "path": f"出图/{SHARED_ASSET_DIR}/asset_registry.json",
        "layer": "shared_asset",
        "boundary": "asset_definition",
    },
    IDENTITY_ADAPTER_MATRIX_KIND: {
        "owner": "n2d-identity",
        "path": f"{PRODUCTION_DIR}/identity_adapter_matrix.json",
        "layer": "production_data",
        "boundary": "adapter_mapping",
    },
    COMPLIANCE_MANIFEST_KIND: {
        "owner": "n2d-compliance",
        "path": "合规/compliance_manifest.json",
        "layer": "governance",
        "boundary": "rights_clearance",
    },
    IMAGE_QC_REPORT_KIND: {
        "owner": "n2d-image",
        "path": f"{PRODUCTION_DIR}/image_qc/{{ep}}/image_qc_{{ep}}.json",
        "layer": "production_data",
        "boundary": "image_drop_qc",
    },
    CONSISTENCY_FINDINGS_KIND: {
        "owner": "n2d-review",
        "path": f"{PRODUCTION_DIR}/consistency_findings_{{ep}}.json",
        "layer": "production_data",
        "boundary": "consistency_findings",
    },
    GATE_FINDINGS_KIND: {
        "owner": "n2d-dashboard",
        "path": f"{PRODUCTION_DIR}/gate_findings_{{stage}}_{{ep}}.json",
        "layer": "production_data",
        "boundary": "gate_findings",
    },
    CONSISTENCY_LEDGER_KIND: {
        "owner": "n2d-review",
        "path": f"{PRODUCTION_DIR}/consistency_ledger_{{ep}}.json",
        "layer": "production_data",
        "boundary": "consistency_ledger",
    },
    VIDEO_MODEL_ROUTES_KIND: {
        "owner": "n2d-model-router",
        "path": f"{PRODUCTION_DIR}/video_model_routes.json",
        "layer": "production_data",
        "boundary": "routing_decisions",
    },
    MOTION_CONTROL_MANIFEST_KIND: {
        "owner": "n2d-video",
        "path": f"{PRODUCTION_DIR}/motion_control_manifest.json",
        "layer": "production_data",
        "boundary": "control_readiness",
    },
    EMOTION_FLOW_KIND: {
        "owner": "n2d-voice",
        "path": "合成/{ep}/配音/emotion_flow.json",
        "layer": "production_data",
        "boundary": "emotional_pacing",
    },
    CONTRACT_INHERITANCE_KIND: {
        "owner": "n2d-video",
        "path": f"{PRODUCTION_DIR}/contract_inheritance_{{ep}}.json",
        "layer": "production_data",
        "boundary": "visual_contract_handoff",
    },
    IDENTITY_DRIFT_REPORT_KIND: {
        "owner": "n2d-identity",
        "path": f"{PRODUCTION_DIR}/identity_drift_report.json",
        "layer": "production_data",
        "boundary": "identity_drift",
    },
    IDENTITY_VOICE_DRIFT_REPORT_KIND: {
        "owner": "n2d-identity",
        "path": f"{PRODUCTION_DIR}/identity_voice_drift_report.json",
        "layer": "production_data",
        "boundary": "voice_key_drift",
    },
    IDENTITY_VOICE_PRINT_REPORT_KIND: {
        "owner": "n2d-identity",
        "path": f"{PRODUCTION_DIR}/identity_voice_print_{{ep}}.json",
        "layer": "production_data",
        "boundary": "voice_print_consistency",
    },
    VISUAL_STATE_LEDGER_KIND: {
        "owner": "n2d-image",
        "path": f"出图/{SHARED_ASSET_DIR}/visual_state_ledger.json",
        "layer": "shared_asset",
        # 边界须点明与 identity_registry 的分工：本账本记【状态演进】(受伤/战损/获法宝随集累积)，
        # identity_registry 记【身份锁定】(角色是谁)，互补不重叠（见 test_visual_state_manager）。
        "boundary": "state_continuity_vs_identity_registry",
    },
    ASSET_RERUN_PLAN_KIND: {
        "owner": "n2d-image",
        "path": f"{PRODUCTION_DIR}/asset_rerun_plan_{{ep}}.json",
        "layer": "production_data",
        "boundary": "rerun_plan",
    },
    BATCH_QUEUE_KIND: {
        "owner": "n2d-batch",
        "path": f"{PRODUCTION_DIR}/batch_queue.json",
        "layer": "production_data",
        "boundary": "work_queue",
    },
    EPISODE_REVIEW_SCORE_KIND: {
        "owner": "n2d-score",
        "path": f"{PRODUCTION_DIR}/score_{{ep}}.json",
        "layer": "production_data",
        "boundary": "review_score",
    },
    SCORE_VISUAL_CHECKS_KIND: {
        "owner": "n2d-score",
        "path": f"{PRODUCTION_DIR}/score_inputs/{{ep}}_visual.json",
        "layer": "production_data",
        "boundary": "visual_score_inputs",
    },
    REVIEW_UI_KIND: {
        "owner": "n2d-review-ui",
        "path": f"{PRODUCTION_DIR}/review_ui_{{ep}}.json",
        "layer": "production_data",
        "boundary": "human_review_ui",
    },
    PLATFORM_FEEDBACK_KIND: {
        "owner": "n2d-feedback",
        "path": f"{PRODUCTION_DIR}/platform_feedback.json",
        "layer": "production_data",
        "boundary": "feedback_metrics",
    },
    GENRE_PERFORMANCE_RECORD_KIND: {
        "owner": "n2d-feedback",
        "path": f"{PRODUCTION_DIR}/genre_performance.jsonl",
        "layer": "production_data",
        "boundary": "market_signal",
    },
    DIFFERENTIATION_CANDIDATES_KIND: {
        "owner": "n2d-feedback",
        "path": f"{PRODUCTION_DIR}/differentiation_candidates.json",
        "layer": "production_data",
        "boundary": "market_positioning",
    },
    LORA_CARD_KIND: {
        "owner": "n2d-lora",
        "path": "设定库/lora/{character}/{form}/lora_card.json",
        "layer": "training_asset",
        "boundary": "lora_card",
    },
    LORA_DATASET_MANIFEST_KIND: {
        "owner": "n2d-lora",
        "path": "设定库/lora/{character}/{form}/dataset_manifest.json",
        "layer": "training_asset",
        "boundary": "lora_dataset",
    },
    LORA_TRAIN_JOB_KIND: {
        "owner": "n2d-lora",
        "path": "设定库/lora/{character}/{form}/train_job.json",
        "layer": "training_asset",
        "boundary": "lora_train_job",
    },
    ASSET_PACK_KIND: {
        "owner": "n2d-asset-market",
        "path": "资产库/{slug}/asset_pack.json",
        "layer": "asset_market",
        "boundary": "asset_pack",
    },
    MOTIF_REGISTRY_KIND: {
        "owner": "n2d-script",
        "path": f"出图/{SHARED_ASSET_DIR}/motif_registry.json",
        "layer": "shared_asset",
        # 题材母题真值：场景级母题(系统面板/升级/签到…)定义，引用 asset_registry 的成长 VFX，
        # 持有镜头模板 id + 台词模式 + overlay 文字层规格 + 逐次成长 progression(单调不回退)。
        # 与 asset_registry 互补：本表记【母题桥段】，asset_registry 记【单资产】，VFX 成长状态机本体落 asset_registry。
        "boundary": "motif_definition",
    },
    MOTIF_PLAN_KIND: {
        "owner": "n2d-script",
        "path": f"{PRODUCTION_DIR}/motif_plan_{{ep}}.json",
        "layer": "production_data",
        "boundary": "motif_suggestion",
    },
}

PRODUCT_KINDS = BOUNDARY_PRODUCT_KINDS

PROGRESS_COLUMNS = (
    "集", "字数", "raw", "剧本改编", "bgm", "封面", "配音", "分镜设计",
    "素材清单", "字幕中", "字幕英", "出图prompt", "出图", "视频prompt", "视频", "成片",
)

IDENTITY_FORK_HISTORY_FIELD = "fork_history"
IDENTITY_FORK_HISTORY_ENTRY_FIELDS = (
    "from_pack",
    "from_slug",
    "from_character_id",
    "forked_at",
    "reason",
)

# ── 一致性维度定义 ────────────────────────────────────────────────────────────
# 一致性维度富表（评分维度·单一真值源）——n2d-score 按 weight 加权打分，consistency_audit / gate /
# feedback / batch 按 audit_labels 把检测器段(脸(G1)/服装配色(N1)…)归并到评分维度并据 return_to_stage 回流。
# 字段：label(中文名) · weight(评分权重·不必和=100，score 按 total_weight 归一) · return_to_stage(回流 stage) ·
# scope(回流修法) · audit_labels(consistency_audit 段名→本维度) · keywords(自由文本兜底解析)。
# 2026-06-15：modularize 重构曾误把本表换成 7 键精简表(face/voice/motion…)致 n2d-score 全挂；此处恢复
# 富表为单一真值源，并把发型机检 发型(H1) 折进 character_consistency（发型属角色 DNA）。
CONSISTENCY_DIMENSIONS: Dict[str, Dict[str, Any]] = {
    "character_consistency": {
        "label": "角色 DNA/形体一致性（脸/发型/身形/手）",
        "weight": 20,
        "return_to_stage": "image",
        "scope": "回 n2d-image 重出脸/发型/身形/手部漂移镜头；必要时补 identity_registry.character_dna / reference_group / 身高表。",
        "audit_labels": ("锚点门(N3)", "脸(G1)", "发型(H1)", "片内时序(N2)", "手部/解剖(N5)", "身高比例(R1)"),
        "keywords": ("角色", "角色DNA", "DNA", "脸", "发型", "身高", "体型", "手部", "解剖", "资产身份", "identity", "face", "锚点"),
    },
    "outfit_consistency": {
        "label": "角色 DNA 一致性（服装/配饰）",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 重出服装/配色/配饰漂移镜头；先检查 character_dna、定妆组和服装参考图。",
        "audit_labels": ("服装配色(N1)",),
        "keywords": ("服装", "配色", "妆造", "配饰", "accessory", "outfit"),
    },
    "scene_consistency": {
        "label": "场景/构图连续性",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 修场景定妆、光位锚、轴线视线、时辰天气、字幕安全区或尾帧；必要时回 n2d-video 重出接缝/相机轨迹 clip。",
        "audit_labels": ("场景(O2)", "接缝接力", "轴线视线(X1)", "天气时辰(W1)", "光位方向(W2)", "字幕安全区(L2)", "空间站位(B1)", "物件常驻(O3)", "视线状态回读(X2)", "场景平面(FP1)", "相机空间轨迹(CAM1)"),
        "keywords": ("场景", "接缝", "尾帧", "场景资产", "轴线", "视线", "站位", "遮挡", "前后景", "天气", "时辰", "字幕安全区", "字幕带", "构图", "物件常驻", "平面图", "相机轨迹", "camera"),
    },
    "subtitle_correctness": {
        "label": "字幕正确性",
        "weight": 16,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2重跑 finalize_storyboard / 字幕重定时 / 修翻译层；必要时重出配音 manifest。",
        "audit_labels": ("字幕对齐(L1)",),
        "keywords": ("字幕", "srt", "cue", "对齐", "断句", "漏译", "阅读速度", "双语", "subtitle"),
    },
    "audio_visual_sync": {
        "label": "音画同步",
        "weight": 16,
        "return_to_stage": "compose",
        "scope": "回 n2d-compose 对齐配音轨、clip 时长、原生音轨策略和多人对话说话人结构；若时长源头错，回 n2d-script 阶段2。",
        "audit_labels": ("音画同步(AV1)", "多人对话音画(DAV)"),
        "keywords": ("音画", "配音", "原生音", "双人声", "多人对话", "说话人", "时长", "voice", "audio", "口型", "mouth"),
    },
    "voice_consistency": {
        "label": "音色一致性",
        "weight": 10,
        "return_to_stage": "voice",
        "scope": "回 n2d-voice 按 voicemap 注册音色重配受影响角色台词；重配后复核时长清单与分镜时长。",
        "audit_labels": ("音色声纹", "声纹一致性", "音色漂移"),
        "keywords": ("音色", "声纹", "speaker", "voice print", "voice_key", "voicemap", "克隆音色"),
    },
    "rhythm_density": {
        "label": "节奏密度",
        "weight": 12,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2重切镜头时长曲线、补钩子/爽点/集尾 cliffhanger。",
        "audit_labels": ("节奏密度(Rhythm)",),
        "keywords": ("节奏", "钩子", "爽点", "留存", "集尾", "rhythm"),
    },
    "style_consistency": {
        "label": "风格一致性",
        "weight": 12,
        "return_to_stage": "image",
        "scope": "回 n2d-image 继承 style_contract 重出偏风格镜头；必要时回 n2d-script 修 style_contract。",
        "audit_labels": ("风格(S1)", "糊/低质(N4)"),
        "keywords": ("风格", "style", "画风", "基础视觉", "糊", "低质", "清晰度"),
    },
    "semantic_continuity": {
        "label": "语义继承",
        "weight": 8,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段1/2或 prompt 生成层，修 raw/voiceover→storyboard→出图/出视频的语义谱系断点、VLM 判题失败与称谓口头禅漂移。",
        "audit_labels": ("语义谱系(P0)", "称谓口头禅(A1)", "台词语域(D1)", "视频VLM判题(VLM1)"),
        "keywords": ("语义", "谱系", "继承", "称谓", "口头禅", "人设", "语域", "VLM", "LMM", "semantic", "voiceover", "storyboard"),
    },
    "state_continuity": {
        "label": "状态百科",
        "weight": 8,
        "return_to_stage": "image",
        "scope": "回 n2d-image 修 visual_state_ledger / 出图分镜状态锁；必要时回 storyboard 修角色状态演进。",
        "audit_labels": ("状态百科(P1)", "状态转场视频证据(ST1)"),
        "keywords": ("状态", "动态百科", "visual_state_ledger", "state", "状态转场", "state_transition"),
    },
    "multimodal_continuity": {
        "label": "多模态漂移",
        "weight": 8,
        "return_to_stage": "image",
        "scope": "回 n2d-image 或 n2d-video 按离群道具/场景/法宝参考组只重出受影响镜头；必要时补资产 taxonomy 和视频侧 embedding probe。",
        "audit_labels": ("多模态(P2)", "视频语义一致(VSEM)"),
        "keywords": ("多模态", "道具", "法宝", "视觉语义", "embedding", "DINO", "CLIP", "DreamSim", "视频语义"),
    },
    "contract_inheritance": {
        "label": "视觉契约继承",
        "weight": 8,
        "return_to_stage": "video_prompt",
        "scope": "回 n2d-video 修 出视频/prompt/00_总览.md 的本集视觉一致性契约；以出图总览原文为准，光位锚/轴线视线不得改写。",
        "audit_labels": ("契约继承", "视觉契约继承"),
        "keywords": ("契约继承", "contract_inheritance", "光位锚", "轴线视线", "导演一致性"),
    },
    "interaction_continuity": {
        "label": "交互/接触因果一致性",
        "weight": 8,
        "return_to_stage": "script_stage2",
        "scope": "回 n2d-script 阶段2补 interaction_graph/contact_graph、左右手/持有状态、持有账本、递交/释放因果和 causal_event_graph；必要时重跑 n2d-model-router 补 motion_control。",
        "audit_labels": ("交互接触(I1)", "持有账本(POS)", "结构化交互图谱(I2)", "物理因果链(CG1)"),
        "keywords": ("交互", "接触", "持有", "持有账本", "递给", "抓握", "因果链", "物理", "motion_control", "interaction", "contact", "possession"),
    },
    "delivery_packaging_consistency": {
        "label": "成片/包装一致性",
        "weight": 8,
        "return_to_stage": "compose",
        "scope": "回 n2d-compose 统一响度、混剪色彩、BGM/room tone、字幕样式、成片时间线探针与系列包装；缺规范先补 series_packaging。",
        "audit_labels": ("成片统一(C1)", "成片时间线探针(FT1)", "系列包装(PKG)"),
        "keywords": ("成片统一", "包装", "片头", "片尾", "LUFS", "响度", "room tone", "BGM", "subtitle style", "final_timeline_probe"),
    },
    "production_ops_consistency": {
        "label": "生产操作一致性",
        "weight": 6,
        "return_to_stage": "review",
        "scope": "回对应 image/video/compose/review 生成节点补 production_events、recipe_hash、强配方 schema、后端/seed/参考图记录、成本、重试原因、人审校准集与一致性 probe；不得让未登记媒体进入交付。",
        "audit_labels": ("生成配方(RCP)", "强配方Schema(RCP2)", "成本路由(K1)", "人审校准集(CAL)", "一致性探针包(PROBE)"),
        "keywords": ("生成配方", "recipe_hash", "prompt_sha256", "reference_bundle_sha256", "成本", "路由", "重试", "production_events", "provider", "seed", "校准集", "probe"),
    },
}

# 显式声明：以下维度**有意**不接 consistency_audit / gate 机检 runner（audit_labels 为空）。
# 当前没有空 audit_labels 维度；仍保留 allowlist 断言，让未来新增维度不会因漏配 audit_labels 而
# **静默**失去机检（要么接 runner，要么显式登记进这里）。
# 注 1：voice_consistency 的声纹机检走 n2d-identity 的 identity.py --write 旁路（非 consistency_audit），
#       故其 audit_labels 非空但不在本表——它有机检，只是不在主审计套件内。
# 注 2：audio_visual_sync 已于 2026-06 接入 consistency_audit 的 音画同步(AV1) advisory runner
#       （lipsync_consistency.py·口型↔配音偏移，SyncNet/LatentSync/外部偏移报告，缺则优雅降级，
#       block 封顶到 warn 不硬阻断 gate；实测严重档喂 n2d-score）——故已移出本缺口表。
# 注 3：rhythm_density 已接入 consistency_audit 的 节奏密度(Rhythm) advisory runner（pacing_retention.py）。
#       它仍不是成片观感模型，常规 profile 不硬阻断；production profile 可按 gate 策略对重复/关键场景
#       或人工未签收问题升级。
GATE_UNAUDITED_DIMENSIONS: frozenset = frozenset()
assert {k for k, v in CONSISTENCY_DIMENSIONS.items() if not v.get("audit_labels")} == GATE_UNAUDITED_DIMENSIONS, (
    "空 audit_labels 的一致性维度必须与 GATE_UNAUDITED_DIMENSIONS 显式一致——"
    "新增维度请配 audit_labels 接机检 runner，或显式登记为已知缺口，别让机检静默蒸发。"
)

# ── STAGE_GRAPH ──────────────────────────────────────────────────────────────
STAGE_GRAPH: List[Dict[str, Any]] = [
    {
        "key": "source",
        "label": "源文本落档",
        "owner": "n2d-script",
        "progress_columns": ("raw",),
        "command": "n2d-script {root}",
        "routes": False,
        "gate_stage": None,
        "requires": (),
        "outputs": ("脚本/{ep}/raw.txt",),
        "return_to_stage": "source",
    },
    {
        "key": "script_stage1",
        "label": "阶段1·剧本改编",
        "owner": "n2d-script",
        "progress_columns": ("剧本改编", "bgm", "封面"),
        "command": "n2d-script {root} {ep}",
        "routes": True,
        "gate_stage": None,
        "requires": ("raw",),
        "outputs": (
            "脚本/{ep}/voiceover.txt",
            "脚本/{ep}/bgm.txt",
            "脚本/{ep}/封面.md",
            "设定库/global_style.md",
            "设定库/characters/_角色总表.md",
            "设定库/locations/_场景总表.md",
        ),
        "return_to_stage": "script_stage1",
    },
    {
        "key": "voice",
        "label": "角色配音",
        "owner": "n2d-voice",
        "progress_columns": ("配音",),
        "command": "n2d-voice {root} {ep}",
        "routes": True,
        "gate_stage": None,
        "requires": ("剧本改编",),
        "outputs": (
            "合成/{ep}/配音/voice_zh.wav",
            "合成/{ep}/配音/时长清单.json",
            "合成/{ep}/配音/_占位说明.md",
        ),
        "output_contract": {
            "any_of": (
                {
                    "label": "真实配音",
                    "all_of": (
                        "合成/{ep}/配音/voice_zh.wav",
                        "合成/{ep}/配音/时长清单.json",
                    ),
                },
                {
                    "label": "视频先行占位时长",
                    "all_of": (
                        "合成/{ep}/配音/_占位说明.md",
                        "合成/{ep}/配音/时长清单.json",
                    ),
                },
            ),
        },
        "return_to_stage": "voice",
    },
    {
        "key": "script_stage2",
        "label": "阶段2·分镜设计",
        "owner": "n2d-script",
        "progress_columns": ("分镜设计", "素材清单", "字幕中", "字幕英"),
        "command": "n2d-script {root} {ep}  (配音后定稿)",
        "routes": True,
        "gate_stage": None,
        "requires": ("配音",),
        "outputs": (
            "脚本/{ep}/分镜剧本.md",
            "脚本/{ep}/故事板.md",
            "脚本/{ep}/storyboard.json",
            "脚本/{ep}/素材清单.md",
            "脚本/{ep}/字幕_中文.srt",
            "脚本/{ep}/字幕_英文.srt",
            "脚本/{ep}/镜头时长.json",
        ),
        "return_to_stage": "script_stage2",
    },
    {
        "key": "image_prompt",
        "label": "出图prompt",
        "owner": "n2d-image",
        "progress_columns": ("出图prompt",),
        "command": "n2d-image {root} {ep}",
        "routes": True,
        "gate_stage": "image_prompt_preflight",
        "requires": ("配音", "分镜设计"),
        "outputs": (
            f"出图/{SHARED_ASSET_DIR}/prompt/00_索引.md",
            "出图/{ep}/prompt/00_总览.md",
            "出图/{ep}/prompt/01_分镜出图.md",
        ),
        "return_to_stage": "image_prompt",
    },
    {
        "key": "image",
        "label": "出图",
        "owner": "n2d-image",
        "progress_columns": ("出图",),
        "command": "n2d-image {root} {ep}",
        "routes": True,
        "gate_stage": "image",
        "requires": ("出图prompt",),
        "outputs": (
            f"出图/{SHARED_ASSET_DIR}/图片",
            "出图/{ep}/图片",
        ),
        "return_to_stage": "image",
    },
    {
        "key": "video_prompt",
        "label": "视频prompt",
        "owner": "n2d-video",
        "progress_columns": ("视频prompt",),
        "command": "n2d-video {root} {ep}",
        "routes": True,
        "gate_stage": "video_prompt_preflight",
        "requires": ("出图",),
        "outputs": (
            "出视频/{ep}/prompt/00_总览.md",
            "出视频/{ep}/prompt/01_clips.md",
        ),
        "return_to_stage": "video_prompt",
    },
    {
        "key": "video",
        "label": "图生视频",
        "owner": "n2d-video",
        "progress_columns": ("视频",),
        "command": "n2d-video {root} {ep}",
        "routes": True,
        "gate_stage": "video",
        "requires": ("视频prompt", "出图"),
        "outputs": ("出视频/{ep}/视频",),
        "return_to_stage": "video",
    },
    {
        "key": "compose",
        "label": "合成成片",
        "owner": "n2d-compose",
        "progress_columns": ("成片",),
        "command": "n2d-compose {root} {ep}",
        "routes": True,
        "gate_stage": "compose",
        "requires": ("视频",),
        "outputs": (
            "合成/{ep}/成片_{ep}_zh.mp4",
            "合成/{ep}/成片_{ep}_bilingual.mp4",
        ),
        "output_contract": {
            "any_of": (
                {"label": "中文字幕成片", "all_of": ("合成/{ep}/成片_{ep}_zh.mp4",)},
                {"label": "双语成片", "all_of": ("合成/{ep}/成片_{ep}_bilingual.mp4",)},
                {"label": "英文字幕成片", "all_of": ("合成/{ep}/成片_{ep}_en.mp4",)},
            ),
        },
        "return_to_stage": "compose",
    },
    {
        "key": "review",
        "label": "审查验收",
        "owner": "n2d-review",
        "progress_columns": (),
        "command": "n2d-review {root} {ep}",
        "routes": False,
        "gate_stage": "review",
        "requires": ("成片",),
        "outputs": (
            "合成/{ep}/成片_{ep}_zh.mp4",
            "合成/{ep}/成片_{ep}_bilingual.mp4",
        ),
        "output_contract": {
            "any_of": (
                {"label": "中文字幕成片", "all_of": ("合成/{ep}/成片_{ep}_zh.mp4",)},
                {"label": "双语成片", "all_of": ("合成/{ep}/成片_{ep}_bilingual.mp4",)},
                {"label": "英文字幕成片", "all_of": ("合成/{ep}/成片_{ep}_en.mp4",)},
            ),
        },
        "return_to_stage": "review",
    },
]

GATE_RECOVERY: Dict[str, Any] = {
    "image_prompt_preflight": {
        "return_to_stage": "script_stage2",
        "rerun_scope": "先修合规包、配音/分镜、storyboard visual/style_contract 与专项镜头模板，再生成出图 prompt。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
        ),
    },
    "image_preflight": {
        "return_to_stage": "image_prompt",
        "rerun_scope": "先修合规包、配音/分镜、storyboard visual/style_contract、出图 prompt、共享定妆与资产注册层，再重跑 image_preflight；未过不得调用生图后端。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            f"出图/{SHARED_ASSET_DIR}/asset_registry.json",
            f"出图/{SHARED_ASSET_DIR}/prompt",
            "出图/{ep}/prompt",
        ),
    },
    "image": {
        "return_to_stage": "image_prompt",
        "rerun_scope": "先修 storyboard.json visual_contract/style_contract、出图 prompt、共享定妆，再重跑 image gate；未过 gate 不生图。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            f"出图/{SHARED_ASSET_DIR}/prompt",
            "出图/{ep}/prompt",
            "出图/{ep}/图片",
        ),
    },
    "video_prompt_preflight": {
        "return_to_stage": "image",
        "rerun_scope": "先修身份矩阵/路由、已落档 PNG、image_qc full 报告、storyboard frame assets 与出图交接，再生成视频 prompt。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            f"出图/{SHARED_ASSET_DIR}/asset_registry.json",
            f"{PRODUCTION_DIR}/identity_adapter_matrix.json",
            "出图/{ep}/图片",
            f"{PRODUCTION_DIR}/image_qc/{{ep}}",
        ),
    },
    "video_preflight": {
        "return_to_stage": "video_prompt",
        "rerun_scope": "先修身份矩阵/路由、首尾帧、视频 prompt、导演一致性契约、基础视觉风格契约或缺失 PNG，再重跑 video_preflight；未过不得调用出视频后端。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            f"出图/{SHARED_ASSET_DIR}/asset_registry.json",
            f"{PRODUCTION_DIR}/identity_adapter_matrix.json",
            "出图/{ep}/图片",
            "出视频/{ep}/prompt",
            "出视频/{ep}/control",
        ),
    },
    "video": {
        "return_to_stage": "video_prompt",
        "rerun_scope": "先修尾帧、视频 prompt、导演一致性契约、基础视觉风格契约或缺失 PNG，再重跑 video gate；未过 gate 不出视频。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            "出图/{ep}/图片",
            "出视频/{ep}/prompt",
            "出视频/{ep}/视频",
        ),
    },
    "compose": {
        "return_to_stage": "compose",
        "rerun_scope": "先补视频/字幕/真配音，再重跑 compose gate；通过后再合成。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            "出视频/{ep}/视频",
            "合成/{ep}/配音",
            "脚本/{ep}/字幕_中文.srt",
            "合成/{ep}",
        ),
    },
    "review": {
        "return_to_stage": "review",
        "rerun_scope": "按 finding 回退到最早受影响阶段。",
        "affected_artifacts": (
            "合规/compliance_manifest.json",
            "脚本/{ep}/storyboard.json",
            f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
            "出视频/{ep}/视频",
            "合成/{ep}",
        ),
    },
}

GATE_STAGES = tuple(GATE_RECOVERY.keys())

IDENTITY_IMAGE_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "codex": {
        "allowed_modes": ("reference_group",),
        "default_mode": "reference_group",
        "default_status": "fallback_reference_group",
    },
    "openai": {
        "allowed_modes": ("reference_group",),
        "default_mode": "reference_group",
        "default_status": "fallback_reference_group",
    },
    "dreamina": {
        "allowed_modes": ("reference_group",),
        "default_mode": "reference_group",
        "default_status": "fallback_reference_group",
    },
    "seedream": {
        "allowed_modes": ("universal_reference", "reference_group"),
        "default_mode": "universal_reference",
        "default_status": "unregistered",
    },
    "kling": {
        "allowed_modes": ("character_id", "subject_library", "custom_model", "element_library", "reference_group"),
        "default_mode": "character_id",
        "default_status": "unregistered",
    },
    "sora": {
        "allowed_modes": ("character_cameo", "reference_group"),
        "default_mode": "character_cameo",
        "default_status": "unregistered",
    },
}

IDENTITY_VIDEO_ADAPTERS: Dict[str, Dict[str, Any]] = {
    "dreamina": {
        "allowed_modes": ("first_last_frame", "reference_group"),
        "default_mode": "first_last_frame",
        "default_status": "fallback_reference_group",
    },
    "kling": {
        "allowed_modes": ("character_id", "reference_group"),
        "default_mode": "character_id",
        "default_status": "unregistered",
    },
    "seedance": {
        "allowed_modes": ("face_lock", "reference_group"),
        "default_mode": "face_lock",
        "default_status": "unregistered",
    },
    "veo": {
        "allowed_modes": ("reference_controls", "reference_group"),
        "default_mode": "reference_controls",
        "default_status": "unregistered",
    },
    "sora": {
        "allowed_modes": ("character_cameo", "reference_media", "reference_group"),
        "default_mode": "character_cameo",
        "default_status": "unregistered",
    },
}

MOTION_CONTROL_REQUIRED_SHOT_TYPES = (
    "fight_exchange",
    "chase",
    "flight",
    "hug_or_pull",
    "intimate_interaction",
    "multi_character_same_frame",
    "ensemble_blocking",
    "multi_person_blocking",
)
MOTION_CONTROL_RISK_FLAGS = (
    "physical_contact",
    "complex_blocking",
    "multi_character_overlap",
    "high_speed_motion",
    "extreme_camera",
    "identity_high_risk",
)

# ── 生图后端治理 ─────────────────────────────────────────────────────────────
# 采集日期：2026-06-14  来源：n2d-image/SKILL.md 放行清单 + 各后端官方文档
APPROVED_IMAGE_BACKENDS: Dict[str, Dict[str, Any]] = {
    "codex": {
        "name": "Codex",
        "label": "Codex",
        "canonical": "codex",
        "multi_reference": True,
        "native_subject": False,
        "tier": "tier-1",
    },
    "openai": {
        # 官方 OpenAI Images（gpt-image / DALL·E）入口，与 codex 同属 OpenAI 官方路线、
        # 同走 reference_group（见 IDENTITY_IMAGE_ADAPTERS["openai"] 与 n2d-image references）。
        "name": "OpenAI gpt-image / DALL·E",
        "label": "官方 OpenAI gpt-image / DALL·E",
        "canonical": "openai",
        "multi_reference": True,
        "native_subject": False,
        "tier": "tier-1",
    },
    "dreamina_official": {
        "name": "Dreamina/即梦官方 CLI",
        "label": "Dreamina/即梦官方 CLI",
        "canonical": "dreamina",
        "multi_reference": True,
        "native_subject": False,
        "tier": "tier-1",
    },
    "seedream": {
        "name": "Seedream",
        "label": "Seedream",
        "canonical": "seedream",
        "multi_reference": True,
        "native_subject": True,
        "tier": "tier-1",
    },
    "kling_subject": {
        "name": "可灵主体库",
        "label": "可灵主体库",
        "canonical": "kling",
        "multi_reference": True,
        "native_subject": True,
        "tier": "tier-2",
    },
    "nano_banana": {
        "name": "Nano Banana",
        "label": "Nano Banana",
        "canonical": "nano_banana",
        "multi_reference": True,
        "native_subject": False,
        "tier": "tier-2",
    },
    "sora_cameo": {
        "name": "Sora Cameo",
        "label": "Sora Cameo",
        "canonical": "sora",
        "multi_reference": True,
        "native_subject": True,
        "tier": "tier-2",
    },
}

IMAGE_BACKEND_ALIASES = {
    "即梦": "dreamina_official",
    "dreamina": "dreamina_official",
    "codex": "codex",
    "openai": "openai",
    "gpt-image": "openai",
    "dall-e": "openai",
    "dalle": "openai",
    "seedream": "seedream",
    "可灵": "kling_subject",
    "kling": "kling_subject",
    "nano banana": "nano_banana",
    "nano_banana": "nano_banana",
    "nanobanana": "nano_banana",
    "gemini": "nano_banana",
    "sora": "sora_cameo",
}

FORBIDDEN_IMAGE_BACKEND_KEYWORDS = ("同视频ai", "同视频AI", "第三方", "逆向", "web自动化", "web 自动化")

# 图后端身份一致性能力档（出图侧）。
#
# `APPROVED_IMAGE_BACKENDS` 只回答「这个出图后端是否可用/官方」；
# 本表回答「它能把角色身份锁到哪一级」。`face_drift_risk.py`、gate 和后续路由建议应读这里，
# 避免把 Dreamina 这类“多参考但无持久主体 ID”的后端误当成 Seedream/可灵主体库。
# 采集日期同 APPROVED_IMAGE_BACKENDS：2026-06-14；易变事实需走 freshness/refresh 流程刷新。
IMAGE_IDENTITY_PROFILES: Dict[str, Dict[str, Any]] = {
    "codex": {
        "label": "Codex",
        "persistent_subject": False,
        "multi_reference": True,
        "strategy": "multi_reference",
        "max_reference_images": None,
        "ingests_video": False,
        "recommended_diverse_reference_min": None,
        "native_modes": (),
        "notes": "无持久角色 ID；每镜使用 reference_group + 锚点句 + full QC。",
    },
    "openai": {
        "label": "官方 OpenAI gpt-image / DALL·E",
        "persistent_subject": False,
        "multi_reference": True,
        "strategy": "multi_reference",
        "max_reference_images": None,
        "ingests_video": False,
        "recommended_diverse_reference_min": None,
        "native_modes": (),
        "notes": "支持图片输入/编辑，但无 n2d 持久主体 ID；按 reference_group 兜底。",
    },
    "dreamina": {
        "label": "Dreamina/即梦官方 CLI",
        "persistent_subject": False,
        "multi_reference": True,
        "strategy": "multi_reference_sticky_reference",
        "max_reference_images": None,
        "ingests_video": False,
        "recommended_diverse_reference_min": None,
        "native_modes": (),
        "notes": "官方 CLI 可多参考/图生图；按无持久角色 ID 处理，切角色前必须清空参考框。",
    },
    "nano_banana": {
        "label": "Nano Banana / Gemini 多参考",
        "persistent_subject": False,
        "multi_reference": True,
        "strategy": "multi_reference",
        "max_reference_images": 14,
        "max_character_refs": 5,
        "max_object_refs": 10,
        "max_style_refs": 3,
        "ingests_video": False,
        "recommended_diverse_reference_min": None,
        "native_modes": (),
        "notes": (
            "Google Gemini/Nano Banana 多图参考后端；无持久角色 ID，不等同 Seedream Universal Reference，"
            "不写入 seedream adapter。按官方 2026-06 文档：Gemini 3 Pro Image 高保真人物参考最多 5 张、"
            "总输入最多 14 张；Gemini 3.1 Flash Image 支持至多 4 个角色相似与 10 个对象保真。"
            "reference_planner 应在容量内优先选当前镜角色 face_anchor/expression/服装/场景参考，禁止全量喂图。"
        ),
    },
    "seedream": {
        "label": "Seedream Universal Reference",
        "persistent_subject": True,
        "multi_reference": True,
        "strategy": "universal_reference",
        "max_reference_images": 14,
        "ingests_video": False,
        "recommended_diverse_reference_min": 8,
        "native_modes": ("universal_reference",),
        "notes": "支持原生主体/通用参考能力；注册或 ready 后按 ID/handle/reference 跨镜复用。注册时喂多样参考集（多角度+多表情+多光）比单 sheet 稳。",
    },
    "kling": {
        "label": "可灵 Kling 主体库",
        "persistent_subject": True,
        "multi_reference": True,
        "strategy": "subject_library",
        "max_reference_images": None,
        "ingests_video": True,
        "recommended_diverse_reference_min": 10,
        "native_modes": ("character_id", "subject_library", "custom_model", "element_library"),
        "notes": "支持主体库/角色 ID 类能力；高危多人同框与接触镜优先注册。Custom Model 可吃 10–30 段视频/多帧拿最丰富身份，是治板式的首选。",
    },
    "sora": {
        "label": "Sora Character Cameo",
        "persistent_subject": True,
        "multi_reference": True,
        "strategy": "character_cameo",
        "max_reference_images": None,
        "ingests_video": True,
        "recommended_diverse_reference_min": 8,
        "native_modes": ("character_cameo",),
        "notes": "支持可复用角色 Cameo；以官方当前能力为准，执行前刷新候选。",
    },
}

# ── 横切 readiness 注册表 ───────────────────────────────────────────────
READINESS_TRACKED_SKILLS: List[Dict[str, Any]] = [
    {
        "key": "compliance",
        "label": "合规治理",
        "skill": "n2d-compliance",
        "artifact": "合规/compliance_manifest.json",
        "required_before": ("image", "video", "compose"),
    },
    {
        "key": "identity",
        "label": "身份一致性",
        "skill": "n2d-identity",
        "artifact": f"出图/{SHARED_ASSET_DIR}/identity_registry.json",
        "required_before": ("image", "video"),
    },
    {
        "key": "motion-control",
        "label": "Motion Control",
        "skill": "n2d-video",
        "artifact": f"{PRODUCTION_DIR}/motion_control_manifest.json",
        "required_before": ("video",),
    },
]

CROSS_CUTTING_TOOLS: List[Dict[str, Any]] = [
    {"key": "update", "label": "重制/更新", "skill": "n2d-update", "artifact": f"{PRODUCTION_DIR}/skill_update_plan_*.json"},
    {"key": "batch", "label": "批量调度", "skill": "n2d-batch", "artifact": f"{PRODUCTION_DIR}/batch_queue.json"},
    {"key": "score", "label": "评分审计", "skill": "n2d-score", "artifact": f"{PRODUCTION_DIR}/score_*.json"},
    {"key": "dashboard", "label": "生产看板", "skill": "n2d-dashboard", "artifact": f"{PRODUCTION_DIR}/dashboard.json"},
    {"key": "feedback", "label": "返工反馈", "skill": "n2d-feedback", "artifact": f"{PRODUCTION_DIR}/platform_feedback.json"},
]

CONTINUITY_FIELDS = (
    "start_state",
    "action",
    "end_state",
    "constraints",
    "negative",
    "transition",
    "need_endframe",
    "spatial_anchor",
    "identity_anchor_points",
    "emotion_flow",
)

COSTLY_HINTS = {
    "配音": "声音克隆需肖像/音色授权（合规闸门）",
    "出图": "会真出图·消耗额度 → 开跑前确认生图后端 + 重抽预算档位",
    "视频": "会真出视频·消耗额度 → 开跑前确认生视频后端",
    "成片": "合成成片（混音+烧字幕），相对便宜但耗时",
}
