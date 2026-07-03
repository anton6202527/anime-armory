# 验收总账 · 第2集

- 验收状态：阻断
- ⛔ block 2 · 🔴 high 0 · 🟡 medium 14

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 8 | detect, gate:image_preflight, gate:image |
| 角色 | 🟡 warn | 0 | 0 | 88 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | ⛔ block | 1 | 0 | 5 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | 🟡 warn | 0 | 0 | 115 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 11 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 9 | detect |
| 合规 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 1 | 0 | 57 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm) @ 脚本/第2集/storyboard.json:  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：66.0 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CLIP04→EP02_CLIP05→EP02_CLIP06→EP02_CLIP07→EP02_CLIP08→EP02_CLIP09），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 跨集色调 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子
- warn [gate:image] 跨集色调 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
- warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子

### 角色问题
- warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.427)→第2集(均值0.4429)，相对基线掉幅 -0.0159，且本集均值低于绝对下限——已系统性偏离定妆锚
- warn [detect] 服装配色(N1): CHAR_01__囚犯初醒态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚犯初醒态 服装配色(N1)    
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn [detect] 台词语域(D1):  台词语域(D1)   缺 dialogue_register/语域表；目前只能查称谓 + 文白横跳启发式，无法约束角色正式度、句长上限和禁用词。建议补 formality/sentence_len_max/forbidden/口癖。 
- warn [detect] 叙事状态(NS1):  叙事状态(NS1)   本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。 
- warn [detect] character_consistency @ CHAR_01__囚犯初醒态: character_consistency  CHAR_01__囚犯初醒态 跨集脸漂移趋势 medium：CHAR_01__囚犯初醒态 第1集→第2集 mean 0.427→0.4429 drop=-0.0159。high 级系统性退化必须先回 n2d-image 补主体库/参考包/重抽并重跑 identity/image_qc。 
- warn [detect] outfit_consistency @ 图片/Clip04_end.png: outfit_consistency  图片/Clip04_end.png 服装 N1 初筛：图片/Clip04_end.png（调色板离群，非阻断） 

### 资产问题
- warn [detect] 物件状态(OST):  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual_state_ledger 给该道具登记 timeline 转换，否则修穿帮。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn [gate:image_preflight] 资产引用注册层 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- block [gate:image] 预防式合同 @ VFX_only: 预防式合同 reference_slot_gate: 道具/场景 VFX_only 缺 reference_slots/reference_group。
- warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变

### 镜头问题
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/猛虎快刀圆满态, CHAR_01/脱力态, CHAR_01/血尘战损态, CHAR_01__, CHAR_02）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_end.png DINO/CLIP cosine=0.30 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_first.png DINO/CLIP cosine=0.25 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_mid.png DINO/CLIP cosine=0.24 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip02_end.png DINO/CLIP cosine=0.26 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=69c1c35402c930c7，但复跑审计证据不完整。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第2集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=4e8d3bf74472ab2f，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第2集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [gate:image_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_01 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_04 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_05 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_06 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): CHAR_01__囚犯初醒态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_02__濒死战损态 锚点门(N3)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   主光方位 right→left 硬翻转（疑光位跳·人比对相邻镜） 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_perspective/occlusion_policy。 
- warn [detect] 物理事件图(PHY):  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_first.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_mid.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_first.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- block · asset:VFX_only · 预防式合同
  - block [gate:image] 预防式合同 @ VFX_only: 预防式合同 reference_slot_gate: 道具/场景 VFX_only 缺 reference_slots/reference_group。
- block · ops:score_第2集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第2集.json: 缺 score JSON；验收总账无法闭环
- warn · asset:asset · 物件状态(OST) / 系统面板(UI1)
  - warn [detect] 物件状态(OST):  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual_state_ledger 给该道具登记 timeline 转换，否则修穿帮。 
  - warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
  - warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn · asset:asset_registry.json asset#4 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · audio:audio · 配音情绪弧(VEA) / 生成配方(RCP) / 强配方Schema(RCP2) / 成本路由(K1)
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=69c1c35402c930c7，但复跑审计证据不完整。 
- warn · audio:第2集 · 配音 / 物料新鲜度
  - warn [gate:image_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image_preflight] 物料新鲜度 @ 第2集: 物料新鲜度 前期物料可能已过期：n2d, n2d-image, n2d-script, n2d-voice 自上次 skill 基线后有改动，可能影响本阶段（image）的输入物料。出图/出视频是花钱且不可逆的步骤——先跑 `python3 skills/n2d-update/scripts/update_plan.py check "/Users/wesl
  - warn [gate:image_prompt_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
- warn · character:01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 5（`EP02_CLIP05` · 一百年到账与收录选择 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 6（`EP02_CLIP06` · 古卷收虎与道行流逝 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂

## 依赖传播

- nodes=58 · edges=93 · clips=10 · images=35 · videos=0
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第2集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=6

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_01） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 虎山神 / 虎妖（CHAR_03） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 百妖谱金色古卷面板（VFX_系统面板） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 虎山神摹影黑血妖气（VFX_虎山神摹影） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 道行计数金色 overlay（VFX_道行计数overlay） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |

## 🟡 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 锚点门(N3)    
- [warn] CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.427)→第2集(均值0.44
- [warn] CHAR_01__囚犯初醒态 服装配色(N1)    

## 🟡 裴长青（CHAR_02）
- [warn] CHAR_02__濒死战损态 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/猛虎快刀圆满态, CHAR_01/脱力态, CHAR_01
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸

## 🟡 虎山神 / 虎妖（CHAR_03）
- [warn] image_prompt_lint  None 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_r
- [warn] image_prompt_lint  None 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_r
- [warn] image_prompt_lint  None 镜头 4（`EP02_CLIP04` · 一刀斩虎山神 · fight_exchange）：

## 🟡 横刀（WEAPON_01）
- [warn]  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已

## 未归属到具体角色/资产的一致性问题
- [warn]  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光
- [warn]  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direction）——实测光
- [warn]  天气时辰(W1)   主光方位 right→left 硬翻转（疑光位跳·人比对相邻镜） 
- [warn]  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 
- [warn]  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- [warn]  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_
- [warn]  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：66.0 
- [warn]  节奏密度(Rhythm)   连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CL

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
