# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 3 · 🔴 high 0 · 🟡 medium 15

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 20 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 角色 | ⛔ block | 6 | 0 | 70 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 25 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | 🟡 warn | 0 | 0 | 86 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 10 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 4 | detect |
| 合规 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 3 | 0 | 60 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `爽点` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `集尾` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 7 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 8 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [detect] state_continuity: state_continuity  None 状态演进声明了累积状态（血迹）但本集出图 prompt 未注入——runner 会照画干净/无伤状态，跨镜/跨集视觉状态漏进生成。跑 `python3 skills/n2d-image/scripts/visual_state_manager.py <作品根> --inject` 注入后重出受影响镜。 
- warn [gate:image_preflight] 故事板 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6: 故事板 start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。
- warn [gate:image_preflight] 故事板 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#7: 故事板 start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。

### 角色问题
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 发型(H1): CHAR_01__囚途残损态 发型(H1)    
- block [detect] 发型(H1): CHAR_01__囚途残损态 发型(H1)    

### 资产问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
- warn [detect] 持有账本(POS):  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 3 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 3 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn [gate:image_preflight] 击中帧验证 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6: 击中帧验证 该 fight_exchange 模板包含 impact_frame_sync，但未在 continuity 规划中段光效爆发帧 (mid_impact / midframe)。

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 空间站位(B1): 入出画 空间站位(B1)   入出画 站位/遮挡与同场景首镜冲突：right/front → None/back（疑重新调度·交人判） 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（BEAST_01/伪死态, BEAST_01/复生态, CHAR_01, CHAR_01/囚途残损态, CHAR_01__, CHAR_01__囚途残损态）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 LOC_01 本集出现 8 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚途残损态」↔ 本镜 图片/Clip01_end.png DINO/CLIP cosine=0.10 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚途残损态」↔ 本镜 图片/Clip01_first.png DINO/CLIP cosine=0.11 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚途残损态」↔ 本镜 图片/Clip02_first.png DINO/CLIP cosine=0.14 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头1·姜月初：台词含强情绪但配音标注「短促决绝」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头12·虎妖：台词含强情绪但配音标注「傲慢从容」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头19·姜月初：台词含强情绪但配音标注「急促盘算」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第1集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=cccc53a5dc6e99b9，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第1集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第1集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 环境声(AMB):  环境声(AMB)   本集涉 1 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁；建 LOC→ambient bed 映射。 
- warn [gate:image_preflight] 时间基准 @ 第1集: 时间基准 当前使用 timing_estimate.json（无 WAV）推进画面；这是设计态时间基准。可见口型镜只可按 production_mode_route 生成表演驱动画面或 base_video_only 基础片，不能冒充最终说话镜。

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_06 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_08（fight_exchange）：剪辑峰值 @9.0s 附近（±0.4s）无 keyframe 锚（现有 keyframe 锚 [5.6]s）——峰值引用了不存在的离散关键帧，重排锚帧或对齐 cue 秒。
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- block [detect] 天气时辰(W1):  天气时辰(W1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- block [detect] 天气时辰(W1):  天气时辰(W1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)    

## 根因聚合

- block · character:character · 服装配色(N1) / 发型(H1) / 真值源(TRUTH) / image_prompt_lint
  - warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
  - warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
  - warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block · character:production_breakdown_check_第1集.json · P-3制片交接包
  - block [gate:image_prompt_preflight] P-3制片交接包 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/production_breakdown_check_第1集.json: P-3制片交接包 P-3 制片交接包未通过：7/9 confirmed。进入出图/视频前必须补齐并确认 continuity_chain.json、continuity_bible.json、ai_shooting_schedule.json、ai_call_sheet.md 等交接文件；问题示例：脚本/第1集/production_handoff_pack
- block · ops:ops · 打斗撞点(SPEC-APEX) / 风格(S1) / 天气时辰(W1) / 物理事件图(PHY) / 成本路由(K1) / 人审校准集(CAL) / 一致性探针包(PROBE)
  - warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_08（fight_exchange）：剪辑峰值 @9.0s 附近（±0.4s）无 keyframe 锚（现有 keyframe 锚 [5.6]s）——峰值引用了不存在的离散关键帧，重排锚帧或对齐 cue 秒。
  - warn [detect] 风格(S1):  风格(S1)    
  - warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- block · ops:score_第1集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第1集.json: 缺 score JSON；验收总账无法闭环
- warn · asset:WEAPON_01 · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/道具定妆.md ## 横刀（`WEAPON_01`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:31>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/道具定妆.md ## 横刀（`WEAPON_01`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:31>16
- warn · asset:asset · 打斗撞点(SPEC-APEX) / 持有账本(POS) / 结构化交互图谱(I2) / 系统面板(UI1)
  - warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
  - warn [detect] 持有账本(POS):  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn · asset:storyboard.json · 打斗撞点(SPEC-APEX)
  - warn [gate:image] 打斗撞点(SPEC-APEX) @ 脚本/第1集/storyboard.json: 打斗撞点(SPEC-APEX) Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如「命中 
- warn · asset:storyboard.json clip#6 · 击中帧验证
  - warn [gate:image_preflight] 击中帧验证 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6: 击中帧验证 该 fight_exchange 模板包含 impact_frame_sync，但未在 continuity 规划中段光效爆发帧 (mid_impact / midframe)。
  - warn [gate:image_prompt_preflight] 击中帧验证 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6: 击中帧验证 该 fight_exchange 模板包含 impact_frame_sync，但未在 continuity 规划中段光效爆发帧 (mid_impact / midframe)。
  - warn [gate:image] 击中帧验证 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6: 击中帧验证 该 fight_exchange 模板包含 impact_frame_sync，但未在 continuity 规划中段光效爆发帧 (mid_impact / midframe)。
- warn · asset:特效定妆.md ## 百妖谱金色古卷面板（`VFX_系统面板`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/特效定妆.md ## 百妖谱金色古卷面板（`VFX_系统面板`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:27>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/特效定妆.md ## 百妖谱金色古卷面板（`VFX_系统面板`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:27>16
- warn · asset:特效定妆.md ## 百妖谱（`VFX_百妖谱`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/特效定妆.md ## 百妖谱（`VFX_百妖谱`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:31>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/特效定妆.md ## 百妖谱（`VFX_百妖谱`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:31>16
- warn · asset:道具定妆.md ## 断刀（`PROP_断刀`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/道具定妆.md ## 断刀（`PROP_断刀`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:30>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/道具定妆.md ## 断刀（`PROP_断刀`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:30>16
- warn · asset:道具定妆.md ## 横刀（`PROP_横刀`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/道具定妆.md ## 横刀（`PROP_横刀`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:31>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/道具定妆.md ## 横刀（`PROP_横刀`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:31>16

## 依赖传播

- nodes=50 · edges=63 · clips=8 · images=27 · videos=0
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第1集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=5

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_01） | character | ⛔ block | 🟡 | ⛔ | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 虎妖（BEAST_01） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸骸荒野（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（PROP_横刀） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 断刀（PROP_断刀） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 翻覆囚车（PROP_翻覆囚车） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 百妖谱金色古卷面板（VFX_系统面板） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 百妖谱（VFX_百妖谱） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚途残损态 服装配色(N1)    
- [warn] CHAR_01__囚途残损态 服装配色(N1)    
- [warn] CHAR_01__囚途残损态 服装配色(N1)    

## 🟡 裴长青（CHAR_02）
- [warn] character_consistency  CHAR_02__濒死重伤态 锚点门 N3：CHAR_02__濒死重伤态 主参考非单张清晰正脸
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「face_anchor」（出图/共享/图片/
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「克制」（出图/共享/图片/定妆_CHAR_0

## 🟡 虎妖（BEAST_01）
- [warn]  配音情绪弧(VEA)   镜头12·虎妖：台词含强情绪但配音标注「傲慢从容」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  实体记忆(EMB)   本集有重复/核心实体（BEAST_01/伪死态, BEAST_01/复生态, CHAR_01, CHAR_01/囚
- [warn] image_prompt_lint  None 多视图对齐初筛异常 BEAST_01/“穿心复生态”：脚底线不齐：rear_three_qu

## 🟡 尸骸荒野（LOC_01）
- [warn]  场景平面(FP1)   场景 LOC_01 本集出现 8 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记

## 🟡 横刀（WEAPON_01）
- [warn]  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 

## 🟡 横刀（PROP_横刀）
- [warn]  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  打斗撞点(SPEC-APEX)    Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/scree
- [warn]  打斗撞点(SPEC-APEX)    Clip_08（fight_exchange）：剪辑峰值 @9.0s 附近（±0.4s）无 keyf
- [warn] 入出画 空间站位(B1)   入出画 站位/遮挡与同场景首镜冲突：right/front → None/back（疑重新调度·交人判） 
- [warn]  风格(S1)    
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- [block]  天气时辰(W1)    
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
