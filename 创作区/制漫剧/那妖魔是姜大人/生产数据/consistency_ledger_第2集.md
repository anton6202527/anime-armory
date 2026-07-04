# 验收总账 · 第2集

- 验收状态：阻断
- ⛔ block 2 · 🔴 high 0 · 🟡 medium 16

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 1 | 0 | 15 | detect, gate:image_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 角色 | 🟡 warn | 0 | 0 | 69 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 资产 | 🟡 warn | 0 | 0 | 8 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 镜头 | 🟡 warn | 0 | 0 | 45 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 音频 | 🟡 warn | 0 | 0 | 19 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video |
| 字幕 | 🟡 warn | 0 | 0 | 9 | detect |
| 合规 | 🟡 warn | 0 | 0 | 7 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, gate:video, compliance |
| 生产操作 | ⛔ block | 1 | 0 | 59 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm) @ 脚本/第2集/storyboard.json:  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：66.0 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CLIP04→EP02_CLIP05→EP02_CLIP06→EP02_CLIP07→EP02_CLIP08→EP02_CLIP09），疑节奏塌·掉留存 
- block [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn [detect] 物理因果链(CG1):  物理因果链(CG1)   视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 跨集色调 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第2集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）

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
- warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:video_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:video_prompt_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn [gate:video] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变

### 镜头问题
- warn [detect] 运动质量(MOT1):  运动质量(MOT1)   高动作后验报告缺字段：impact_frame；动作镜不能只看 prompt/manifest，需用抽帧、姿态/光流或 VLM 回读速度曲线、命中帧和距离/空间曲线是否成立。 
- warn [detect] 高动态成片证据(SPECV):  高动态成片证据(SPECV)   Clip_03 fight_exchange 缺高动态后验证据字段：contact_map。 
- warn [detect] 高动态成片证据(SPECV):  高动态成片证据(SPECV)   Clip_03 fight_exchange 动作关键维未实测：limb_artifact（光流方向对账/肢体畸变/运动模糊）。按 sampling_plan 在动作峰值帧加密抽帧，跑动作-artifact runner 写 生产数据/spectacle_motion_artifacts_第2集.json。 
- warn [detect] 高动态成片证据(SPECV):  高动态成片证据(SPECV)   Clip_04 fight_exchange 缺高动态后验证据字段：contact_map。 
- warn [detect] 高动态成片证据(SPECV):  高动态成片证据(SPECV)   Clip_04 fight_exchange 动作关键维未实测：limb_artifact（光流方向对账/肢体畸变/运动模糊）。按 sampling_plan 在动作峰值帧加密抽帧，跑动作-artifact runner 写 生产数据/spectacle_motion_artifacts_第2集.json。 
- warn [detect] 高动态成片证据(SPECV):  高动态成片证据(SPECV)   Clip_10 stealth_stalk 动作关键维未实测：limb_artifact（光流方向对账/肢体畸变/运动模糊）。按 sampling_plan 在动作峰值帧加密抽帧，跑动作-artifact runner 写 生产数据/spectacle_motion_artifacts_第2集.json。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/猛虎快刀圆满态, CHAR_01/脱力态, CHAR_01/血尘战损态, CHAR_01__, CHAR_02）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。 
- warn [detect] 多人对话音画(DAV):  多人对话音画(DAV)   检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=69c1c35402c930c7，但复跑审计证据不完整。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第2集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=4e8d3bf74472ab2f，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver

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
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
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

- block · ops:score_第2集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第2集.json: 缺 score JSON；验收总账无法闭环
- block · story:story · 语义谱系(P0) / 节奏密度(Rhythm) / 视频语义一致(VSEM) / 物理因果链(CG1) / 状态转场视频证据(ST1)
  - warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
  - warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CLIP04→EP02_CLIP05→EP02_CLIP06→EP02_CLIP07→EP02_CLIP08→EP02_CLIP09），疑节奏塌·掉留存 
  - block [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured VSEM threshold. 
- warn · asset:asset · 物件状态(OST) / 系统面板(UI1)
  - warn [detect] 物件状态(OST):  物件状态(OST)   道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual_state_ledger 给该道具登记 timeline 转换，否则修穿帮。 
  - warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
  - warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn · asset:asset_registry.json asset#4 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:video_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#4: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · audio:audio · 配音情绪弧(VEA) / 声音空间(ASP) / 多人对话音画(DAV) / 生成配方(RCP) / 强配方Schema(RCP2) / 成本路由(K1)
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 声音空间(ASP):  声音空间(ASP)   原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。 
- warn · audio:consistency_findings_第2集.json · 证据等级
  - warn [gate:video] 证据等级 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_findings_第2集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（出图/出视频阶段先 WARN，交付边界 compose/review 将 BLOC
- warn · audio:dialogue_av_alignment_第2集.json · 多人对话音画(DAV)
  - warn [gate:video] 多人对话音画(DAV) @ 生产数据/dialogue_av_alignment_第2集.json: 多人对话音画(DAV) 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。
- warn · audio:voiceover.txt · 配音情绪弧(VEA)
  - warn [gate:image] 配音情绪弧(VEA) @ 脚本/第2集/voiceover.txt: 配音情绪弧(VEA) 镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
  - warn [gate:image] 配音情绪弧(VEA) @ 脚本/第2集/voiceover.txt: 配音情绪弧(VEA) 镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn · audio:第2集 · 配音
  - warn [gate:image_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image_prompt_preflight] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image] 配音 @ 第2集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
- warn · character:01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 1（`EP02_CLIP01` · 杀裴后的二十年到账 · system_panel）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 2（`EP02_CLIP02` · 虎妖嘲讽与转刀 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第2集/prompt/01_分镜出图.md ## 镜头 3（`EP02_CLIP03` · 二十年尽压一刀 · fight_exchange）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂

## 依赖传播

- nodes=85 · edges=184 · clips=10 · images=35 · videos=12
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
- [warn]  声音空间(ASP)   原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BG
- [warn]  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：66.0 
- [warn]  节奏密度(Rhythm)   连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CL
- [block]  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured 
- [warn]  视频语义一致(VSEM)   DINOv2 whole-frame similarity is below the configured 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
