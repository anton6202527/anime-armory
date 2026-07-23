# 验收总账 · 第2集

- 验收状态：阻断
- ⛔ block 7 · 🔴 high 0 · 🟡 medium 10

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 14 | 0 | 39 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 角色 | ⛔ block | 27 | 0 | 90 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_prompt_preflight |
| 资产 | ⛔ block | 4 | 0 | 21 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 镜头 | ⛔ block | 5 | 0 | 82 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 音频 | 🟡 warn | 0 | 0 | 26 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 字幕 | 🟡 warn | 0 | 0 | 6 | detect |
| 合规 | 🟡 warn | 0 | 0 | 6 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, compliance |
| 生产操作 | ⛔ block | 10 | 0 | 72 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, score |

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
- block [detect] 脸(G1): CHAR_02__濒死重伤态 脸(G1)    
- block [detect] 脸(G1): CHAR_02__濒死重伤态 脸(G1)    
- block [detect] 脸(G1): CHAR_02__濒死重伤态 脸(G1)    
- block [detect] 脸(G1): CHAR_02__濒死重伤态 脸(G1)    
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
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集结构漂移 dHash 汉明=24（vs 前 1 集结构原型，阈 warn=18·core block=26）——色调一致但结构疑似变样（家具挪位/构图朝向变），核对是否同一空间，否则对齐场景定妆 spatial_layout。
- warn [detect] 景深一致(DOF1):  景深一致(DOF1)   图片/EP02_CLIP01_start_a2.png：景深档与同场景其它镜不一致——本镜偏深焦(背景偏清)（景深比 1.038 vs 场景中位 0.69）；同场景深焦↔浅景深横跳像换相机，人核对是否有意，否则统一景深档重出。 
- warn [detect] 景深一致(DOF1):  景深一致(DOF1)   图片/EP02_CLIP04_end_a2.png：景深档与同场景其它镜不一致——本镜偏深焦(背景偏清)（景深比 0.996 vs 场景中位 0.69）；同场景深焦↔浅景深横跳像换相机，人核对是否有意，否则统一景深档重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP02_CLIP01_start_a2.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.147 vs 场景中位 -0.037）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP02_CLIP08_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.212 vs 场景中位 -0.037）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP02_CLIP08_start_a1.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.42 vs 场景中位 -0.037）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头4·姜月初：台词含强情绪但配音标注「压抑决绝」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第2集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=88863180b1df2f34，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第2集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 环境声(AMB):  环境声(AMB)   本集涉 2 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁；建 LOC→ambient bed 映射。 
- warn [gate:image_preflight] 时间基准 @ 第2集: 时间基准 当前使用 timing_estimate.json（无 WAV）推进画面；这是设计态时间基准。可见口型镜只可按 production_mode_route 生成表演驱动画面或 base_video_only 基础片，不能冒充最终说话镜。
- warn [gate:image_prompt_preflight] 时间基准 @ 第2集: 时间基准 当前使用 timing_estimate.json（无 WAV）推进画面；这是设计态时间基准。可见口型镜只可按 production_mode_route 生成表演驱动画面或 base_video_only 基础片，不能冒充最终说话镜。
- warn [gate:image] 时间基准 @ 第2集: 时间基准 当前使用 timing_estimate.json（无 WAV）推进画面；这是设计态时间基准。可见口型镜只可按 production_mode_route 生成表演驱动画面或 base_video_only 基础片，不能冒充最终说话镜。

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
- warn [gate:video_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): CHAR_01__囚途残损态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_02__濒死重伤态 锚点门(N3)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- block [detect] 风格(S1):  风格(S1)    
- block [detect] 天气时辰(W1):  天气时辰(W1)    
- block [detect] 天气时辰(W1):  天气时辰(W1)    
- block [detect] 天气时辰(W1):  天气时辰(W1)    

## 根因聚合

- block · asset:dialogue_fact_contract_第2集.json · 对白事实锁
  - block [gate:video_prompt_preflight] 对白事实锁 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/dialogue_fact_contract_第2集.json: 对白事实锁 missing_dialogue_fact_contract: native_speech/native_av is active but dialogue_fact_contract is missing; run this script with --write before paid video submit.
- block · asset:storyboard.json clip#3 · 空间硬控
  - block [gate:image_prompt_preflight] 空间硬控 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#3: 空间硬控 该 fight_exchange 模板具有 pose_reference_required: true 约束，必须配置 pose_image_path。
- block · asset:storyboard.json clip#8 · 专项镜头模板
  - block [gate:image_prompt_preflight] 专项镜头模板 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#8: 专项镜头模板 template=system_panel 的 template_contract 缺字段：growth_ref
  - block [gate:image_prompt_preflight] 专项镜头模板 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#8: 专项镜头模板 template=system_panel 的 template_contract 缺字段：panel_tier
- block · character:character · 脸(G1) / 服装配色(N1) / 发型(H1) / 真值源(TRUTH) / 台词语域(D1) / 叙事状态(NS1) / image_prompt_lint
  - block [detect] 脸(G1): CHAR_02__濒死重伤态 脸(G1)    
  - block [detect] 脸(G1): CHAR_02__濒死重伤态 脸(G1)    
  - block [detect] 脸(G1): CHAR_02__濒死重伤态 脸(G1)    
- block · character:image_qc_第2集.json · 出图落档QC
  - block [gate:video_prompt_preflight] 出图落档QC @ 创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第2集/image_qc_第2集.json: 出图落档QC 输入首帧 image_qc 仍有 43 项硬阻断（崩脸/人体解剖N5/接缝断/降级精度近景/非法 CHAR/缺高风险人体合约）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。
- block · character:production_breakdown_check_第2集.json · P-3制片交接包
  - block [gate:image_prompt_preflight] P-3制片交接包 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/production_breakdown_check_第2集.json: P-3制片交接包 P-3 制片交接包未通过：7/9 confirmed。进入出图/视频前必须补齐并确认 continuity_chain.json、continuity_bible.json、ai_shooting_schedule.json、ai_call_sheet.md 等交接文件；问题示例：脚本/第2集/production_handoff_pack
- block · character:storyboard.json clip#3 · 分区合成
  - block [gate:image_prompt_preflight] 分区合成 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json clip#3: 分区合成 该 fight_exchange 模板具有 regional_construct_required: true 约束，检测到同框多角色，请在 execution_strategy / multi_subject_strategy / template_contract.execution_strategy 中明确保底合成策略以防串脸。
- block · character:第2集 · 脸漂报告新鲜度
  - block [gate:image_prompt_preflight] 脸漂报告新鲜度 @ 第2集: 脸漂报告新鲜度 脸漂实测报告内容级陈旧：历史集 ['第1集(指纹不符)'] 的当前 PNG 像素与报告记录的指纹不一致——图在报告生成后重出过，集级覆盖看着没问题、报告其实基于旧像素，measured-drift 环会误判『全绿』。重跑 `python3 skills/n2d-identity/scripts/identity.py <作品根> --writ
- block · ops:01_clips.md ## Clip 06（时长 10.520s · EP02_CLIP06 · 结算闻弦初境与二十五年余额） · 帧策略 / prompt compiler
  - block [gate:video_preflight] 帧策略 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/01_clips.md ## Clip 06（时长 10.520s · EP02_CLIP06 · 结算闻弦初境与二十五年余额）: 帧策略 多镜位 Clip 选择了 edit_cut，但缺少分镜边界图或尾帧；先补图再付费生成
  - warn [gate:video_preflight] prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/01_clips.md ## Clip 06（时长 10.520s · EP02_CLIP06 · 结算闻弦初境与二十五年余额）: prompt compiler 提交 prompt 可进一步精简：submit_prompt_many_clauses:20>12
- block · ops:01_clips.md ## Clip 08（时长 4.213s · EP02_CLIP08 · 摹影进阶会变成什么） · 帧策略 / prompt compiler
  - block [gate:video_preflight] 帧策略 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/01_clips.md ## Clip 08（时长 4.213s · EP02_CLIP08 · 摹影进阶会变成什么）: 帧策略 多镜位 Clip 选择了 edit_cut，但缺少分镜边界图或尾帧；先补图再付费生成
  - warn [gate:video_preflight] prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/01_clips.md ## Clip 08（时长 4.213s · EP02_CLIP08 · 摹影进阶会变成什么）: prompt compiler 提交 prompt 可进一步精简：submit_prompt_many_clauses:21>12
- block · ops:ops · 锚点门(N3) / 风格(S1) / 天气时辰(W1) / 物理事件图(PHY) / 生成配方(RCP) / 强配方Schema(RCP2) / 成本路由(K1) / 人审校准集(CAL) / 一致性探针包(PROBE)
  - warn [detect] 锚点门(N3): CHAR_01__囚途残损态 锚点门(N3)    
  - warn [detect] 锚点门(N3): CHAR_02__濒死重伤态 锚点门(N3)    
  - warn [detect] 风格(S1):  风格(S1)    
- block · ops:score_第2集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第2集.json: 缺 score JSON；验收总账无法闭环

## 依赖传播

- nodes=59 · edges=87 · clips=8 · images=26 · videos=0
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
| 裴长青（CHAR_02） | character | ⛔ block | 🟢 | ⛔ | 🟢 |
| 虎妖（BEAST_01） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸骸荒野（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 百妖谱金色古卷面板（VFX_系统面板） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 横刀（WEAPON_横刀） | weapon | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 百妖谱（VFX_百妖谱） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 墨虎谱影（VFX_墨虎谱影） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚途残损态 锚点门(N3)    
- [block] CHAR_01__囚途残损态 服装配色(N1)    
- [block] CHAR_01__囚途残损态 服装配色(N1)    

## ⛔ 裴长青（CHAR_02）
- [warn] CHAR_02__濒死重伤态 锚点门(N3)    
- [block] CHAR_02__濒死重伤态 脸(G1)    
- [block] CHAR_02__濒死重伤态 脸(G1)    

## 🟡 虎妖（BEAST_01）
- [warn]  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜4 prompt 未见状态锁。 
- [warn]  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜5 prompt 未见状态锁。 
- [warn]  状态百科(P1)   虎妖 在镜3后应保持 `命中后断首死亡`，但镜6 prompt 未见状态锁。 

## 🟡 尸骸荒野（LOC_01）
- [warn]  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集结构漂移 dHash 汉明=24（vs 前 1 集结构原型，阈 warn=18·co
- [warn]  场景平面(FP1)   场景 尸骸荒野 本集出现 6 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。

## 未归属到具体角色/资产的一致性问题
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [block]  风格(S1)    
- [warn]  景深一致(DOF1)   图片/EP02_CLIP01_start_a2.png：景深档与同场景其它镜不一致——本镜偏深焦(背景偏清)（景
- [warn]  景深一致(DOF1)   图片/EP02_CLIP04_end_a2.png：景深档与同场景其它镜不一致——本镜偏深焦(背景偏清)（景深比
- [warn]  色温调色(GRADE1)   图片/EP02_CLIP01_start_a2.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（
- [warn]  色温调色(GRADE1)   图片/EP02_CLIP08_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.
- [warn]  色温调色(GRADE1)   图片/EP02_CLIP08_start_a1.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
