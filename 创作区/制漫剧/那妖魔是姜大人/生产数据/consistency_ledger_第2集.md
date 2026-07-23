# 验收总账 · 第2集

- 验收状态：阻断
- ⛔ block 10 · 🔴 high 0 · 🟡 medium 7

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 14 | 0 | 45 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 角色 | ⛔ block | 63 | 0 | 91 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_prompt_preflight |
| 资产 | ⛔ block | 5 | 0 | 21 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 镜头 | ⛔ block | 82 | 0 | 89 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 音频 | 🟡 warn | 0 | 0 | 29 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 字幕 | 🟡 warn | 0 | 0 | 6 | detect |
| 合规 | 🟡 warn | 0 | 0 | 6 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, compliance |
| 生产操作 | ⛔ block | 37 | 0 | 79 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, score |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   复杂镜视频 prompt 未充分继承专项模板契约。 
- warn [detect] 状态百科(P1):  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜4 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜5 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜6 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜7 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜8 prompt 未见状态锁。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 3 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03），疑节奏塌·掉留存 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 3 个长镜聚集（EP02_CLIP05→EP02_CLIP06→EP02_CLIP07），疑节奏塌·掉留存 

### 角色问题
- block [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    

### 资产问题
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 5 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 5 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 

### 镜头问题
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集色调/光位漂移 L1=0.4744（vs 前 1 集基线，阈 warn=0.45·core block=0.8）——确认是否 allowed_variations 内的合理变化，否则对齐前集场景定妆。
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    [allowed_variations 已签收] 场景[尸骸荒野] 跨集结构漂移 dHash 汉明=27（vs 前 1 集结构原型，阈 warn=18·core block=26）——核心场景跨集结构硬漂：色调没动但布局/家具/构图朝向变了（同房间被重新布置/拍反向），回 n2d-image 对齐场景定妆 spatial_l
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP02_CLIP01_start_a2.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.147 vs 场景中位 -0.037）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP02_CLIP08_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.164 vs 场景中位 -0.037）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   本集已有视频产物和脚本/视频契约，但缺 video_semantic_consistency；无法核验视频侧主体/背景语义是否随视频生成漂移。 
- warn [detect] 相机空间轨迹(CAM1):  相机空间轨迹(CAM1)   视频含明确镜头运动/空间轨迹，但缺 camera_trajectory_probe；无法核验运动方向、深度、越轴和抖动连续性。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头4·姜月初：台词含强情绪但配音标注「压抑决绝」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 
- warn [detect] 多人对话音画(DAV):  多人对话音画(DAV)   检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第2集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=88863180b1df2f34，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第2集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 环境声(AMB):  环境声(AMB)   本集涉 2 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁；建 LOC→ambient bed 映射。 
- warn [gate:image_preflight] 时间基准 @ 第2集: 时间基准 当前使用 timing_estimate.json（无 WAV）推进画面；这是设计态时间基准。可见口型镜只可按 production_mode_route 生成表演驱动画面或 base_video_only 基础片，不能冒充最终说话镜。

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_01 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_04 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_05 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_06 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 片内时序(N2):  片内时序(N2)    
- warn [detect] 片内时序(N2):  片内时序(N2)    

## 根因聚合

- block · asset:WEAPON_01 · multimodal_continuity / 物料漂移预案 / image prompt compiler
  - block [detect] multimodal_continuity @ 图片/EP02_CLIP01_start_a1.png: multimodal_continuity  图片/EP02_CLIP01_start_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 1（`EP02_CLIP01` · 杀人余震与二十年到账 · ） 的 `WEAPON_01`（横刀，type=weapon）登记了 must_not_have=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃
  - block [detect] multimodal_continuity @ 图片/EP02_CLIP01_start_a2.png: multimodal_continuity  图片/EP02_CLIP01_start_a2.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 1（`EP02_CLIP01` · 杀人余震与二十年到账 · ） 的 `WEAPON_01`（横刀，type=weapon）登记了 must_not_have=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃
  - block [detect] multimodal_continuity @ 图片/EP02_CLIP01_start_a3.png: multimodal_continuity  图片/EP02_CLIP01_start_a3.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 1（`EP02_CLIP01` · 杀人余震与二十年到账 · ） 的 `WEAPON_01`（横刀，type=weapon）登记了 must_not_have=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃
- block · asset:consumed_contracts_image_prompt_第2集.json · Prompt消费收据
  - block [gate:image] Prompt消费收据 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consumed_contracts_image_prompt_第2集.json: Prompt消费收据 prompt pack 消费合同不新鲜或不完整，禁止进入昂贵生成：storyboard 已变更但 prompt 未重签：脚本/第2集/storyboard.json；continuity_chain 已变更但 prompt 未重签：脚本/第2集/continuity_chain.json
- block · asset:dialogue_fact_contract_第2集.json · 对白事实锁
  - block [gate:video_prompt_preflight] 对白事实锁 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/dialogue_fact_contract_第2集.json: 对白事实锁 missing_dialogue_fact_contract: native_speech/native_av is active but dialogue_fact_contract is missing; run this script with --write before paid video submit.
- block · asset:storyboard.json clip#3 · 空间硬控
  - block [gate:image_prompt_preflight] 空间硬控 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#3: 空间硬控 该 fight_exchange 模板具有 pose_reference_required: true 约束，必须配置 pose_image_path。
- block · asset:storyboard.json clip#8 · 专项镜头模板
  - block [gate:image_prompt_preflight] 专项镜头模板 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#8: 专项镜头模板 template=system_panel 的 template_contract 缺字段：growth_ref
  - block [gate:image_prompt_preflight] 专项镜头模板 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#8: 专项镜头模板 template=system_panel 的 template_contract 缺字段：panel_tier
- block · character:Clip03_end.png · character_consistency / outfit_consistency
  - block [detect] character_consistency @ 图片/Clip03_end.png: character_consistency  图片/Clip03_end.png 崩脸 G1 block：图片/Clip03_end.png（脸/身份漂移机检） 
  - warn [detect] character_consistency @ 图片/Clip03_end.png: character_consistency  图片/Clip03_end.png 发型 H1 初筛：图片/Clip03_end.png（发色/发型轮廓离群，非阻断） 
  - warn [detect] outfit_consistency @ 图片/Clip03_end.png: outfit_consistency  图片/Clip03_end.png 服装 N1 初筛：图片/Clip03_end.png（调色板离群，非阻断） 
- block · character:Clip07_end.png · character_consistency / outfit_consistency
  - block [detect] character_consistency @ 图片/Clip07_end.png: character_consistency  图片/Clip07_end.png 崩脸 G1 block：图片/Clip07_end.png（脸/身份漂移机检） 
  - warn [detect] outfit_consistency @ 图片/Clip07_end.png: outfit_consistency  图片/Clip07_end.png 服装 N1 初筛：图片/Clip07_end.png（调色板离群，非阻断） 
  - block [gate:image] character_consistency @ 图片/Clip07_end.png: character_consistency 崩脸 G1 block：图片/Clip07_end.png（脸/身份漂移机检）
- block · character:EP02_CLIP01_start.png · character_consistency
  - warn [detect] character_consistency @ 图片/EP02_CLIP01_start.png: character_consistency  图片/EP02_CLIP01_start.png 崩脸 G1 warn：图片/EP02_CLIP01_start.png（脸/身份漂移机检） 
  - block [detect] character_consistency @ 图片/EP02_CLIP01_start.png: character_consistency  图片/EP02_CLIP01_start.png 角色脸定妆比对覆盖缺口：镜头 1（`EP02_CLIP01` · 杀人余震与二十年到账 · ） 图片/EP02_CLIP01_start.png；脸部比对为 warn，疑似身份漂移。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 vide
  - warn [gate:image] character_consistency @ 图片/EP02_CLIP01_start.png: character_consistency 崩脸 G1 warn：图片/EP02_CLIP01_start.png（脸/身份漂移机检）
- block · character:EP02_CLIP02_preimpact.png · character_consistency / outfit_consistency
  - block [detect] character_consistency @ 图片/EP02_CLIP02_preimpact.png: character_consistency  图片/EP02_CLIP02_preimpact.png 崩脸 G1 block：图片/EP02_CLIP02_preimpact.png（脸/身份漂移机检） 
  - warn [detect] character_consistency @ 图片/EP02_CLIP02_preimpact.png: character_consistency  图片/EP02_CLIP02_preimpact.png 发型 H1 初筛：图片/EP02_CLIP02_preimpact.png（发色/发型轮廓离群，非阻断） 
  - warn [detect] outfit_consistency @ 图片/EP02_CLIP02_preimpact.png: outfit_consistency  图片/EP02_CLIP02_preimpact.png 服装 N1 初筛：图片/EP02_CLIP02_preimpact.png（调色板离群，非阻断） 
- block · character:EP02_CLIP02_start.png · character_consistency
  - block [detect] character_consistency @ 图片/EP02_CLIP02_start.png: character_consistency  图片/EP02_CLIP02_start.png 崩脸 G1 block：图片/EP02_CLIP02_start.png（脸/身份漂移机检） 
  - warn [detect] character_consistency @ 图片/EP02_CLIP02_start.png: character_consistency  图片/EP02_CLIP02_start.png 发型 H1 初筛：图片/EP02_CLIP02_start.png（发色/发型轮廓离群，非阻断） 
  - block [gate:image] character_consistency @ 图片/EP02_CLIP02_start.png: character_consistency 崩脸 G1 block：图片/EP02_CLIP02_start.png（脸/身份漂移机检）
- block · character:EP02_CLIP03_impact.png · character_consistency / outfit_consistency
  - block [detect] character_consistency @ 图片/EP02_CLIP03_impact.png: character_consistency  图片/EP02_CLIP03_impact.png 崩脸 G1 block：图片/EP02_CLIP03_impact.png（脸/身份漂移机检） 
  - warn [detect] character_consistency @ 图片/EP02_CLIP03_impact.png: character_consistency  图片/EP02_CLIP03_impact.png 发型 H1 初筛：图片/EP02_CLIP03_impact.png（发色/发型轮廓离群，非阻断） 
  - warn [detect] outfit_consistency @ 图片/EP02_CLIP03_impact.png: outfit_consistency  图片/EP02_CLIP03_impact.png 服装 N1 初筛：图片/EP02_CLIP03_impact.png（调色板离群，非阻断） 
- block · character:EP02_CLIP04_end_a1.png · character_consistency
  - warn [detect] character_consistency @ 图片/EP02_CLIP04_end_a1.png: character_consistency  图片/EP02_CLIP04_end_a1.png 崩脸 G1 warn：图片/EP02_CLIP04_end_a1.png（脸/身份漂移机检） 
  - block [detect] character_consistency @ 图片/EP02_CLIP04_end_a1.png: character_consistency  图片/EP02_CLIP04_end_a1.png 角色脸定妆比对覆盖缺口：镜头 5（`EP02_CLIP05` · 摹影虎山神获圆满刀法 · system_panel） 图片/EP02_CLIP04_end_a1.png；脸部比对为 warn，疑似身份漂移。每张已落档角色图必须逐张对定妆/身份主参考过 full
  - warn [gate:image] character_consistency @ 图片/EP02_CLIP04_end_a1.png: character_consistency 崩脸 G1 warn：图片/EP02_CLIP04_end_a1.png（脸/身份漂移机检）

## 依赖传播

- nodes=77 · edges=188 · clips=8 · images=28 · videos=16
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第2集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=0

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_01） | character | ⛔ block | 🟡 | ⛔ | 🟢 |
| 横刀（WEAPON_01） | weapon | ⛔ block | 🟡 | ⛔ | 🟢 |
| 百妖谱金色古卷面板（VFX_系统面板） | vfx | ⛔ block | 🟡 | ⛔ | 🟢 |
| 横刀（WEAPON_横刀） | weapon | ⛔ block | 🟡 | ⛔ | 🟢 |
| 百妖谱（VFX_百妖谱） | vfx | ⛔ block | 🟡 | ⛔ | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 虎妖（BEAST_01） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸骸荒野（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 墨虎谱影（VFX_墨虎谱影） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [block] CHAR_01__囚途残损态 服装配色(N1)    
- [block] CHAR_01__囚途残损态 服装配色(N1)    
- [block] CHAR_01__囚途残损态 服装配色(N1)    

## ⛔ 横刀（WEAPON_01）
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a2.png 高风险道具禁形/尺寸/物料拓扑未逐图确
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a3.png 高风险道具禁形/尺寸/物料拓扑未逐图确

## ⛔ 百妖谱金色古卷面板（VFX_系统面板）
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a2.png 高风险道具禁形/尺寸/物料拓扑未逐图确
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a3.png 高风险道具禁形/尺寸/物料拓扑未逐图确

## ⛔ 横刀（WEAPON_横刀）
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a2.png 高风险道具禁形/尺寸/物料拓扑未逐图确
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a3.png 高风险道具禁形/尺寸/物料拓扑未逐图确

## ⛔ 百妖谱（VFX_百妖谱）
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a2.png 高风险道具禁形/尺寸/物料拓扑未逐图确
- [block] multimodal_continuity  图片/EP02_CLIP01_start_a3.png 高风险道具禁形/尺寸/物料拓扑未逐图确

## 🟡 裴长青（CHAR_02）
- [warn]  表情连续(EXP1)   Clip_07：角色 CHAR_02 相邻镜情绪硬跳（惊/惧→悲）——确认有节拍/事件依据，否则表演 OOC（情
- [warn] character_consistency  CHAR_02__濒死重伤态 锚点门 N3：CHAR_02__濒死重伤态 主参考非单张清晰正脸
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「face_anchor」（出图/共享/图片/

## 🟡 虎妖（BEAST_01）
- [warn]  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜4 prompt 未见状态锁。 
- [warn]  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜5 prompt 未见状态锁。 
- [warn]  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜6 prompt 未见状态锁。 

## 🟡 尸骸荒野（LOC_01）
- [warn]  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集色调/光位漂移 L1=0.4744（vs 前 1 集基线，阈 warn=0.45·c
- [warn]  跨集场景漂移(SCNX)    [allowed_variations 已签收] 场景[尸骸荒野] 跨集结构漂移 dHash 汉明=27（
- [warn]  场景平面(FP1)   场景 尸骸荒野 本集出现 6 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。

## 未归属到具体角色/资产的一致性问题
- [warn]  片内时序(N2)    
- [warn]  片内时序(N2)    
- [warn]  片内时序(N2)    
- [warn]  片内时序(N2)    
- [warn]  片内时序(N2)    
- [warn]  片内时序(N2)    
- [warn]  片内时序(N2)    
- [warn]  片内时序(N2)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
