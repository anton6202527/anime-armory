# 验收总账 · 第2集

- 验收状态：阻断
- ⛔ block 3 · 🔴 high 0 · 🟡 medium 15

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 13 | detect, gate:image_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 角色 | ⛔ block | 2 | 0 | 69 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 资产 | 🟡 warn | 0 | 0 | 8 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 镜头 | 🟡 warn | 0 | 0 | 39 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 音频 | ⛔ block | 4 | 0 | 15 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 字幕 | 🟡 warn | 0 | 0 | 9 | detect |
| 合规 | 🟡 warn | 0 | 0 | 7 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video, compliance |
| 生产操作 | ⛔ block | 5 | 0 | 60 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm) @ 脚本/第2集/storyboard.json:  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：66.0 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CLIP04→EP02_CLIP05→EP02_CLIP06→EP02_CLIP07→EP02_CLIP08→EP02_CLIP09），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 跨集色调 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子
- warn [gate:image] 跨集色调 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
- warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子

### 角色问题
- warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4469)，相对基线掉幅 -0.0412，且本集均值低于绝对下限——已系统性偏离定妆锚
- warn [detect] 服装配色(N1): CHAR_01__囚犯初醒态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚犯初醒态 服装配色(N1)    
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn [detect] 台词语域(D1):  台词语域(D1)   缺 dialogue_register/语域表；目前只能查称谓 + 文白横跳启发式，无法约束角色正式度、句长上限和禁用词。建议补 formality/sentence_len_max/forbidden/口癖。 
- warn [detect] 叙事状态(NS1):  叙事状态(NS1)   本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。 
- warn [detect] character_consistency @ CHAR_01__囚犯初醒态: character_consistency  CHAR_01__囚犯初醒态 跨集脸漂移趋势 medium：CHAR_01__囚犯初醒态 第1集→第2集 mean 0.4057→0.4469 drop=-0.0412。high 级系统性退化必须先回 n2d-image 补主体库/参考包/重抽并重跑 identity/image_qc。 
- warn [detect] outfit_consistency @ 图片/Clip04_end.png: outfit_consistency  图片/Clip04_end.png 服装 N1 初筛：图片/Clip04_end.png（调色板离群，非阻断） 

### 资产问题
- warn [detect] 物件状态(OST):  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual_state_ledger 给该道具登记 timeline 转换，否则修穿帮。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn [gate:image_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:image] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:video_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:video_prompt_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:video] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变

### 镜头问题
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/猛虎快刀圆满态, CHAR_01/脱力态, CHAR_01/血尘战损态, CHAR_01__, CHAR_02）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] style_consistency: style_consistency  None 景别像素兜底：镜8 声明 CU(特写) 但 出图/第2集/图片/Clip08_end.png 实测脸占比 3.5% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 
- warn [detect] style_consistency: style_consistency  None 景别像素兜底：镜9 声明 CU(特写) 但 出图/第2集/图片/Clip09_a1.png 实测脸占比 0.8% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 
- warn [gate:image_preflight] 物料漂移预案 @ 荒野尸骸战场（LOC_01）: 物料漂移预案 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 ready），锁 layout/axis/light_anchor，反打不越轴（production 核心 LOC 缺则 gate BLOCK）。
- warn [gate:image_preflight] 参考规划落实 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/reference_plan_第2集.json: 参考规划落实 逐镜参考规划有 8 条行动项未确认落实（无持久主体 ID 后端×大变化镜 0 镜）：镜头 EP02_CLIP01、EP02_CLIP02、EP02_CLIP03、EP02_CLIP04、EP02_CLIP05、EP02_CLIP06、EP02_CLIP07、EP02_CLIP09。请按 reference_plan_第2集.md 把补拍/多样参
- warn [gate:image_preflight] 物理尺寸对账 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md: 物理尺寸对账 多人同框镜头（姜月初、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎山神「远大于姜月初和裴长青，同框必须保持体量优势。」；裴长青「比姜月初高约一个头；与虎山神相比明显弱势。」 在 registry 声明了相对身量(relative_scale)，但本镜 prompt 未写入——把声明的相对身量写
- warn [gate:image_prompt_preflight] 物料漂移预案 @ 荒野尸骸战场（LOC_01）: 物料漂移预案 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 ready），锁 layout/axis/light_anchor，反打不越轴（production 核心 LOC 缺则 gate BLOCK）。

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
- warn [gate:image_preflight] 合规前置 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): CHAR_01__囚犯初醒态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_02__濒死战损态 锚点门(N3)    
- warn [detect] 声音空间(ASP):  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_perspective/occlusion_policy。 
- warn [detect] 物理事件图(PHY):  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_first.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_mid.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_first.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/第2集/图片/Clip01_mid.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- block · audio:video_model_routes.json · 生视频后端适配
  - block [gate:video_preflight] 生视频后端适配 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/video_model_routes.json: 生视频后端适配 生视频后端「dreamina」（渠道 Dreamina，执行后端 dreamina）缺少本次官方 API/CLI 刷新证据：refresh evidence is 1 day(s) old。正式付费出视频前必须实时查官方文档/本机 CLI 或 API help，确认单 Clip 上限、首尾/多帧能力、原生音画/口型、身份绑定、分辨率/价格/额
  - block [gate:video_preflight] 生视频后端适配 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/video_model_routes.json: 生视频后端适配 生视频后端「seedance」（渠道 Dreamina，执行后端 dreamina）缺少本次官方 API/CLI 刷新证据：refresh evidence is 1 day(s) old。正式付费出视频前必须实时查官方文档/本机 CLI 或 API help，确认单 Clip 上限、首尾/多帧能力、原生音画/口型、身份绑定、分辨率/价格/额
  - block [gate:video] 生视频后端适配 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第2集/prompt/video_model_routes.json: 生视频后端适配 生视频后端「seedance」（渠道 Dreamina，执行后端 dreamina）缺少本次官方 API/CLI 刷新证据：refresh evidence is 1 day(s) old。正式付费出视频前必须实时查官方文档/本机 CLI 或 API help，确认单 Clip 上限、首尾/多帧能力、原生音画/口型、身份绑定、分辨率/价格/额
- block · character:model_routes_baseline.json · 后端跨集锁
  - block [gate:video_preflight] 后端跨集锁 @ 创作区/制漫剧/那妖魔是姜大人/设定库/model_routes_baseline.json: 后端跨集锁 第2集 含高风险/含角色路由（Clip_01、Clip_02、Clip_03、Clip_04、Clip_05、Clip_06）但缺 `设定库/model_routes_baseline.json`。第2集起必须先用打样集 `n2d-model-router --write-baseline` 建立 shot_type→primary 后端基线，否
  - block [gate:video] 后端跨集锁 @ 创作区/制漫剧/那妖魔是姜大人/设定库/model_routes_baseline.json: 后端跨集锁 第2集 含高风险/含角色路由（Clip_01、Clip_02、Clip_03、Clip_04、Clip_05、Clip_06）但缺 `设定库/model_routes_baseline.json`。第2集起必须先用打样集 `n2d-model-router --write-baseline` 建立 shot_type→primary 后端基线，否
- block · ops:production_events.jsonl · 强配方Schema(RCP2) / 生成配方(RCP)
  - block [gate:video] 强配方Schema(RCP2) @ 生产数据/production_events.jsonl: 强配方Schema(RCP2) [production一致性升级:重复同维度] 脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_
  - block [gate:video] 强配方Schema(RCP2) @ 生产数据/production_events.jsonl: 强配方Schema(RCP2) [production一致性升级:重复同维度] 合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifac
  - block [gate:video] 生成配方(RCP) @ 生产数据/production_events.jsonl: 生成配方(RCP) [production一致性升级:重复同维度] 脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=69c1c35402c930c7，但复跑审计证据不完整。。如确认为可
- block · ops:score_第2集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第2集.json: 缺 score JSON；验收总账无法闭环
- warn · asset:asset · 物件状态(OST) / 系统面板(UI1)
  - warn [detect] 物件状态(OST):  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual_state_ledger 给该道具登记 timeline 转换，否则修穿帮。 
  - warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
  - warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn · asset:asset_registry.json asset#4 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:video_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · audio:audio · 配音情绪弧(VEA) / 生成配方(RCP) / 强配方Schema(RCP2) / 成本路由(K1)
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=69c1c35402c930c7，但复跑审计证据不完整。 
- warn · audio:voiceover.txt · 配音情绪弧(VEA)
  - warn [gate:image] 配音情绪弧(VEA) @ 脚本/第2集/voiceover.txt: 配音情绪弧(VEA) 镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
  - warn [gate:image] 配音情绪弧(VEA) @ 脚本/第2集/voiceover.txt: 配音情绪弧(VEA) 镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn · audio:第2集 · 配音
  - warn [gate:image_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image_prompt_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
- warn · character:01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂

## 依赖传播

- nodes=73 · edges=124 · clips=10 · images=35 · videos=0
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
| 虎山神 / 虎妖（CHAR_03） | character | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 百妖谱金色古卷面板（VFX_系统面板） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 虎山神摹影黑血妖气（VFX_虎山神摹影） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| VFX 妖气（VFX_妖气） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 道行计数金色 overlay（VFX_道行计数overlay） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| VFX 残余金纹（VFX_残余金纹） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |

## 🟡 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 锚点门(N3)    
- [warn] CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4
- [warn] CHAR_01__囚犯初醒态 服装配色(N1)    

## 🟡 裴长青（CHAR_02）
- [warn] CHAR_02__濒死战损态 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/猛虎快刀圆满态, CHAR_01/脱力态, CHAR_01
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸

## 🟡 横刀（WEAPON_01）
- [warn]  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已

## 未归属到具体角色/资产的一致性问题
- [warn]  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 
- [warn]  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- [warn]  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_
- [warn]  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：66.0 
- [warn]  节奏密度(Rhythm)   连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CL
- [warn]  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / s
- [warn]  状态转场视频证据(ST1)   检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 
- [warn]  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/obj

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
