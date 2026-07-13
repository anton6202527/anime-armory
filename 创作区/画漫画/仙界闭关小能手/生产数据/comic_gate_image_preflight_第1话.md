# 漫画 Gate — image_preflight — 第1话

- 生成时间：2026-07-12T18:00:45
- 结论：block
- block/warn/info：228 / 7 / 0

## 记录

- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- chapter_beat_audit: must=0 warn=3（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 17 需处理 1（advisory·不阻断）

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| block | visual_contract_missing | 脚本/第1话/panel_script.json | panel_script 缺少 visual_contract，无法锁本话风格、场景光位、轴线视线和角色完整性口径。 | script | 在 panel_script.json 顶层补 visual_contract.scene_anchors / character_integrity_policy 后重建出图包。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P001 | P001 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P001 | P001 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P001 | P001 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P002 | P002 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P002 | P002 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P002 | P002 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P003 | P003 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P003 | P003 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P003 | P003 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P004 | P004 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P004 | P004 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P004 | P004 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P005 | P005 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P005 | P005 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P005 | P005 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P006 | P006 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P006 | P006 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P006 | P006 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P007 | P007 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P007 | P007 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P007 | P007 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P008 | P008 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P008 | P008 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P008 | P008 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P009 | P009 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P009 | P009 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P010 | P010 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P010 | P010 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_multi_character_staging_missing | 脚本/第1话/panel_script.json#P010 | P010 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。 | script | 补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P011 | P011 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P011 | P011 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P012 | P012 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P012 | P012 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P013 | P013 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P013 | P013 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P014 | P014 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P014 | P014 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P015 | P015 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P015 | P015 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P016 | P016 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P017 | P017 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P017 | P017 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | panel_character_contract_missing | 脚本/第1话/panel_script.json#P018 | P018 含角色但缺少人物一致性字段：gaze_target,eyeline_direction,character_integrity/completeness_notes。漫画格也必须锁脸、眼神目标和身体完整性。 | script | 补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。 |
| block | panel_scene_contract_missing | 脚本/第1话/panel_script.json#P018 | P018 含场景但缺少场景连续性字段：scene_anchor_id/LOC_,spatial_layout,lighting_anchor,axis_eyeline。同一场景必须继承布局、光位和轴线视线。 | script | 补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。 |
| block | generation_recipe_mixed | 出图/第1话/prompt/panel_jobs.json | 同一话记录了多个生图模型/渠道：GPT Image 2/Codex CLI；GPT Image 2/Codex CLI + crop_outer_frame | image | 统一模型和渠道后重建 job 包并重抽受影响格。 |
| block | panel_jobs_schema_legacy | 出图/第1话/prompt/panel_jobs.json | panel_jobs 不是 compiler-aware schema v2。 | image | 重跑 comic-image/scripts/build_panel_jobs.py。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P001: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P002: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P003: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P004: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P005: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P006: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P007: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P008: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P009: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P010: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P011: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P012: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P013: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P014: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P015: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P016: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P017: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: missing_full_production_contract | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: prompt_source_kind_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: prompt_compiler_incompatible | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: prompt_alias_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: source_contract_hash_invalid | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: submit_prompt_hash_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: prompt_backend_mismatch | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: empty_submit_prompt | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: missing_visible_facts | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | compiled_prompt_invalid | 出图/第1话/prompt/panel_jobs.json | P018: missing_style_or_render_stage | image | 重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。 |
| block | panel_jobs_stale_contract | 出图/第1话/prompt/panel_jobs.json | 这些格的落盘出图包与当前脚本/收尾/风格契约不一致（改了契约没重建出图包）：P001、P002、P003、P004、P005、P006、P007、P008、P009、P010、P011、P012、P013、P014、P015、P016、P017、P018 | image | 重跑 comic-image/scripts/build_panel_jobs.py（陈旧格自动回 planned），再重抽这些格。 |
| warn | name_board_missing | 排版/第1话/name_board.json | 传统原稿流程已启用，但缺少缩略分镜/name_board；页流、翻页钩子和格子轻重缺少ネーム层证据。 | name | 运行 comic-name 生成 name_board.json，再重建 layout。 |
| warn | manuscript_safe_area_missing | 排版/第1话/layout.json | layout 缺少 manuscript.safe_area / trim_box；页漫或投稿规格下容易把关键画面、气泡或拟声词放进裁切风险区。 | layout | 重跑 comic-layout，并确认已接入 comic-name 的原稿安全框。 |
| warn | finishing_plan_missing | 出图/第1话/finishing/finishing_plan.json | 传统原稿流程已启用，但缺少墨线/黑场/网点/效果线计划，出图 prompt 只能泛泛写漫画风。 | finishing | 运行 comic-finishing 生成 finishing_plan.json 后重建出图包。 |
| warn | missing_opening_hook | 生产数据/comic_chapter_beat_audit_第1话.json | 首格 story_function=opening_pressure，不是开场钩类（opening_hook/cold_open）——条漫首屏决定点开率，第一格就要给读者停下的理由。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | panel_count_below_platform_floor | 生产数据/comic_chapter_beat_audit_第1话.json | 本话仅 18 格 < 20（快看官方成稿门槛 ≥20 格·2026-07 官方投稿页）——投稿平台会拒收；确认是有意的短话或补格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | split_blueprint_missing | 生产数据/comic_chapter_beat_audit_第1话.json | 缺 脚本/split_blueprint.json 全书拆分蓝图——拆分只覆盖眼前话次，后续话次会断供（实证：第 2 话曾因此卡死）。先按『冲突→爽点/揭示→钩子』闭环把全书粗切成候选话次边界账（每话记 source_range/核心冲突/结尾钩子候选/预计格数），再逐话精修。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P006·贺平生：缺 情绪表情库（哭/怒/惊…；当前仅中性视图·大表情格易脸重画） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包，或按升档建议补专门定妆/换持久主体后端。 |
