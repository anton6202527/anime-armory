# 验收总账 · 第2集

- 验收状态：通过
- ⛔ block 0 · 🔴 high 0 · 🟡 medium 27

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 46 | detect, gate:compose, gate:image_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 角色 | 🟡 warn | 0 | 0 | 124 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 资产 | 🟡 warn | 0 | 0 | 22 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 镜头 | 🟡 warn | 0 | 0 | 242 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 音频 | 🟡 warn | 0 | 0 | 36 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, review-ui, score |
| 字幕 | 🟡 warn | 0 | 0 | 15 | detect, review-ui, score |
| 合规 | 🟡 warn | 0 | 0 | 9 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video_preflight, gate:video_prompt_preflight, gate:video, compliance |
| 生产操作 | 🟡 warn | 0 | 0 | 75 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:review, gate:video, review-ui, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm) @ 脚本/第2集/storyboard.json:  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：66.0 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CLIP04→EP02_CLIP05→EP02_CLIP06→EP02_CLIP07→EP02_CLIP08→EP02_CLIP09），疑节奏塌·掉留存 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 物理因果链(CG1):  物理因果链(CG1)   视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:compose] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子
- warn [gate:compose] 视频 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/视频: 视频 clip 数 11 与 storyboard clips 10 不一致

### 角色问题
- warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚
- warn [detect] 服装配色(N1): CHAR_01__囚犯初醒态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚犯初醒态 服装配色(N1)    
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_01 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
- warn [detect] 叙事状态(NS1):  叙事状态(NS1)   本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。 
- warn [detect] character_consistency @ CHAR_01__囚犯初醒态: character_consistency  CHAR_01__囚犯初醒态 跨集脸漂移趋势 medium：CHAR_01__囚犯初醒态 第1集→第2集 mean 0.4057→0.4461 drop=-0.0404。high 级系统性退化必须先回 n2d-image 补主体库/参考包/重抽并重跑 identity/image_qc。 
- warn [detect] outfit_consistency @ 图片/Clip04_end.png: outfit_consistency  图片/Clip04_end.png 服装 N1 初筛：图片/Clip04_end.png（调色板离群，非阻断） 

### 资产问题
- warn [detect] 物件状态(OST):  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual_state_ledger 给该道具登记 timeline 转换，否则修穿帮。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn [gate:compose] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:compose] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#3: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:compose] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:image_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip06_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076 vs 场景中位 -0.116）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip06_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076 vs 场景中位 -0.116）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip06_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076 vs 场景中位 -0.116）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.193 vs 场景中位 -0.116）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.202 vs 场景中位 -0.116）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.208 vs 场景中位 -0.116）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 高动态成片证据(SPECV):  高动态成片证据(SPECV)   Clip_03 fight_exchange 缺高动态后验证据字段：contact_map。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。 
- warn [detect] 多人对话音画(DAV):  多人对话音画(DAV)   检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 
- warn [detect] 成片统一(C1):  成片统一(C1)   storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。 
- warn [detect] 成片统一(C1):  成片统一(C1)   缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=69c1c35402c930c7，但复跑审计证据不完整。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第2集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=4e8d3bf74472ab2f，但复跑审计证据不完整。 

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
- warn [gate:compose] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_preflight] 合规前置 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:review] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 声音空间(ASP):  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_perspective/occlusion_policy。 
- warn [detect] 物理事件图(PHY):  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_first.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_mid.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_first.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_mid.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_mid.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_first.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- warn · asset:EP02_CLIP01 · UI/系统面板/HUD 一致性
  - warn [review-ui] UI/系统面板/HUD 一致性 @ EP02_CLIP01: UI/系统面板/HUD 一致性 系统面板(UI1) detail: 检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 定位镜头：Clip_01 定位产物：设定库/ui_a
- warn · asset:asset · 物件状态(OST) / 系统面板(UI1)
  - warn [detect] 物件状态(OST):  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual_state_ledger 给该道具登记 timeline 转换，否则修穿帮。 
  - warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
  - warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn · asset:asset_registry.json asset#1 · 资产引用注册层
  - warn [gate:compose] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:review] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · asset:asset_registry.json asset#3 · 资产引用注册层
  - warn [gate:compose] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#3: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#3: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:review] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#3: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · asset:asset_registry.json asset#4 · 资产引用注册层
  - warn [gate:compose] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · asset:episode · UI/系统面板/HUD 一致性
  - warn [review-ui] UI/系统面板/HUD 一致性 @ episode: UI/系统面板/HUD 一致性 系统面板(UI1): block=0 warn=2 ok=0 skipped=False
  - warn [review-ui] UI/系统面板/HUD 一致性 @ episode: UI/系统面板/HUD 一致性 系统面板(UI1) detail: 检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 定位产物：设定库/system_state_ledger.json、脚本/第2集/storyboard.json、设定库/ui_asset_registry.json、出图/
- warn · asset:score_第2集.json · UI/系统面板/HUD 一致性
  - warn [score] UI/系统面板/HUD 一致性 @ 生产数据/score_第2集.json: UI/系统面板/HUD 一致性: status=warn score=88 block=0 warn=2
- warn · audio:audio · 配音情绪弧(VEA) / 声音空间(ASP) / 多人对话音画(DAV) / 成片统一(C1) / 生成配方(RCP) / 强配方Schema(RCP2) / 成本路由(K1)
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 声音空间(ASP):  声音空间(ASP)   原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。 
- warn · audio:consistency_findings_第2集.json · 证据等级
  - warn [gate:video] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第2集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（出图/出视频阶段先 WARN，交付边界 compose/review 将 BLOC
- warn · audio:dialogue_av_alignment_第2集.json · 多人对话音画(DAV)
  - warn [gate:compose] 多人对话音画(DAV) @ 生产数据/dialogue_av_alignment_第2集.json: 多人对话音画(DAV) 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。
  - warn [gate:image] 多人对话音画(DAV) @ 生产数据/dialogue_av_alignment_第2集.json: 多人对话音画(DAV) 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。
  - warn [gate:review] 多人对话音画(DAV) @ 生产数据/dialogue_av_alignment_第2集.json: 多人对话音画(DAV) 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。
- warn · audio:episode · 音画同步 / 音色一致性
  - warn [review-ui] 音画同步 @ episode: 音画同步 音画同步(AV1): block=0 warn=0 ok=0 skipped=True
  - warn [review-ui] 音画同步 @ episode: 音画同步 多人对话音画(DAV): block=0 warn=1 ok=0 skipped=False
  - warn [review-ui] 音画同步 @ episode: 音画同步 多人对话音画(DAV) detail: 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 定位产物：生产数据/dialogue_av_alignment_第2集.json、合成/第2集
- warn · audio:score_第2集.json · 音画同步 / 音色一致性
  - warn [score] 音画同步 @ 生产数据/score_第2集.json: 音画同步: status=warn score=84 block=0 warn=2
  - warn [score] 音色一致性 @ 生产数据/score_第2集.json: 音色一致性: status=warn score=88 block=0 warn=2

## 依赖传播

- nodes=100 · edges=196 · clips=10 · images=35 · videos=12
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
| 陈青源（CHAR_04） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 青面郎君（CHAR_05） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 虎山神 / 虎妖（CHAR_03） | character | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 尸场物资包（PROP_尸场物资包） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 荒野官道夜路（LOC_02） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 上盘村村口与村道（LOC_03） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 飞鹰门马匹与火把（MOUNT_GROUP_01） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 上盘村断石碑（PROP_上盘村断石碑） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 村道血迹破布（PROP_村道血迹破布） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 木架残肢剪影（PROP_木架残肢剪影） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 狼爪寒光（VFX_狼爪寒光） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 妖气（VFX_妖气） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 系统面板（VFX_系统面板） | vfx | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 虎山神摹影（VFX_虎山神摹影） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| GROUP_飞鹰门众人（GROUP_飞鹰门众人） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| GROUP_狼妖群（GROUP_狼妖群） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 残余金纹（VFX_残余金纹） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 道行计数 overlay（VFX_道行计数overlay） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## 🟡 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4
- [warn] CHAR_01__囚犯初醒态 服装配色(N1)    
- [warn] CHAR_01__囚犯初醒态 服装配色(N1)    

## 🟡 陈青源（CHAR_04）
- [warn] character_consistency  CHAR_04__常态 锚点门 N3：CHAR_04__常态 主参考非单张清晰正脸（非阻断） 
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_04/常态「基础」（出图/共享/图片/定妆_CHAR_04__常态

## 🟡 青面郎君（CHAR_05）
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「基础」（出图/共享/图片/定妆_CHAR_05__常态

## 🟡 裴长青（CHAR_02）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/猛虎快刀圆满态, CHAR_01/脱力态, CHAR_01
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸

## 🟡 横刀（WEAPON_01）
- [warn]  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已

## 🟡 系统面板（VFX_系统面板）
- [warn]  系统面板(UI1)   检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核
- [warn]  系统面板(UI1)   检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  色温调色(GRADE1)   图片/Clip06_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076 v
- [warn]  色温调色(GRADE1)   图片/Clip06_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076
- [warn]  色温调色(GRADE1)   图片/Clip06_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076 v
- [warn]  色温调色(GRADE1)   图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.193 v
- [warn]  色温调色(GRADE1)   图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.202
- [warn]  色温调色(GRADE1)   图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.208 v
- [warn]  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
