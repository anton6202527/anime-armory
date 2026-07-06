# 验收总账 · 第3集

- 验收状态：阻断
- ⛔ block 6 · 🔴 high 0 · 🟡 medium 17

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 5 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 153 | 0 | 96 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 资产 | ⛔ block | 14 | 0 | 30 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 镜头 | ⛔ block | 32 | 0 | 86 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 音频 | 🟡 warn | 0 | 0 | 24 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | ⛔ block | 3 | 0 | 6 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, compliance |
| 生产操作 | ⛔ block | 116 | 0 | 44 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, score, expression_state_consistency |

### 剧情问题
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 10 个长镜聚集（EP03_CLIP01→EP03_CLIP02→EP03_CLIP03→EP03_CLIP04→EP03_CLIP05→EP03_CLIP06→EP03_CLIP07→EP03_CLIP08→EP03_CLIP09→EP03_CLIP10），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 跨集色调 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
- warn [gate:image] 跨集色调 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
- warn [gate:image] 叙事状态(NS1) @ 设定库/narrative_state_ledger.json: 叙事状态(NS1) 本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。

### 角色问题
- block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- warn [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    

### 资产问题
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[荒野尸骸战场] 跨集色调/光位漂移 L1=0.6143（vs 前 2 集基线，阈 warn=0.45·core block=0.8）——确认是否 allowed_variations 内的合理变化，否则对齐前集场景定妆。
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[荒野尸骸战场] 跨集结构漂移 dHash 汉明=24（vs 前 2 集结构原型，阈 warn=18·core block=26）——色调一致但结构疑似变样（家具挪位/构图朝向变），核对是否同一空间，否则对齐场景定妆 spatial_layout。
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip08_first_a1.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.041 vs 场景中位 -0.164）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip08_first_a3.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.036 vs 场景中位 -0.164）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头1·旁白：台词含强情绪但配音标注「低沉」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头18·姜月初：台词含强情绪但配音标注「内心崩溃」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头19·旁白：台词含强情绪但配音标注「悬停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头27·旁白：台词含强情绪但配音标注「沉下」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头33·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头35·旁白：台词含强情绪但配音标注「硬断」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「马队出现：鼓点加速，火把和马蹄声盖住」→「镜头20：姜月初“何事？”前留 0.」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第3集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=2b039e84f9118338，但复跑审计证据不完整。 

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- block [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json character_likeness: 合规前置 identity_registry 中角色 GROUP_飞鹰门众人 缺肖像/角色授权记录
- block [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json character_likeness: 合规前置 identity_registry 中角色 GROUP_狼妖群 缺肖像/角色授权记录
- block [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json character_likeness: 合规前置 identity_registry 中角色 CHAR_05 缺肖像/角色授权记录
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): CHAR_01__囚犯初醒态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_01__镇魔司伪装态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_02__濒死战损态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_04__常态 锚点门(N3)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    

## 根因聚合

- block · asset:asset_registry.json asset#1 · 资产引用注册层 / 空间/场面调度一致性
  - warn [gate:image_preflight] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - block [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 资产引用注册层 反复场景资产缺空间布局字段：spatial_layout
  - block [gate:image] 空间/场面调度一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#1: 空间/场面调度一致性 核心/高频 LOC 缺空间发布字段：floor_plan, doors_windows, screen_direction_rules；请补平面图、门窗方向、轴线规则和左右站位/screen_direction 规则，避免多集同场景门窗/站位/越轴漂移。
- block · asset:asset_registry.json asset#2 · 资产引用注册层
  - block [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#2: 资产引用注册层 关键道具资产缺生命周期字段：owner
  - block [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#2: 资产引用注册层 关键道具资产缺生命周期字段：current_state
  - block [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#2: 资产引用注册层 关键道具资产缺生命周期字段：lifecycle
- block · character:CHAR_01 · 多视角身份包(MVIEW) / 实体记忆(EMB) / 脸漂预案 / 核心角色一致性
  - warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_01 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
  - warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__囚犯初醒态, CHAR_01__镇魔司伪装态, CHAR_02, CHAR_04）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
  - warn [gate:image_preflight] 脸漂预案 @ 姜月初（CHAR_01）: 脸漂预案 本集脸漂风险 high（分85.5·multi_reference）：已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考 + split_composite + full image_qc 回验，不再因预测 high 在 preflight 阶段硬阻断。
- block · character:CHAR_05 · image_prompt_lint / 合规前置
  - warn [detect] image_prompt_lint: image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再
  - warn [detect] image_prompt_lint: image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再
  - warn [detect] image_prompt_lint: image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「基础」（出图/共享/图片/定妆_CHAR_05__常态.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 
- block · character:Clip01_end.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_end.png: character_consistency 降级精度近景：图片/Clip01_end.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/face_re
  - block [gate:image] character_consistency @ 图片/Clip01_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP03_CLIP01` · 埋尸冷开：欠命账落地 · multi_character_same_frame） 图片/Clip01_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 vide
- block · character:Clip01_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_first.png: character_consistency 降级精度近景：图片/Clip01_first.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/face_
  - block [gate:image] character_consistency @ 图片/Clip01_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP03_CLIP01` · 埋尸冷开：欠命账落地 · multi_character_same_frame） 图片/Clip01_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 vi
- block · character:Clip01_first_a1.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_first_a1.png: character_consistency 降级精度近景：图片/Clip01_first_a1.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/fa
  - block [gate:image] character_consistency @ 图片/Clip01_first_a1.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP03_CLIP01` · 埋尸冷开：欠命账落地 · multi_character_same_frame） 图片/Clip01_first_a1.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进
- block · character:Clip01_first_a2.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_first_a2.png: character_consistency 降级精度近景：图片/Clip01_first_a2.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/fa
  - block [gate:image] character_consistency @ 图片/Clip01_first_a2.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP03_CLIP01` · 埋尸冷开：欠命账落地 · multi_character_same_frame） 图片/Clip01_first_a2.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进
- block · character:Clip01_first_a3.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_first_a3.png: character_consistency 降级精度近景：图片/Clip01_first_a3.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第3集/fa
  - block [gate:image] character_consistency @ 图片/Clip01_first_a3.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP03_CLIP01` · 埋尸冷开：欠命账落地 · multi_character_same_frame） 图片/Clip01_first_a3.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进
- block · character:Clip02_end.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip02_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 2（`EP03_CLIP02` · 搜尸求生：生存物资 · ） 图片/Clip02_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip02_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip02_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 2（`EP03_CLIP02` · 搜尸求生：生存物资 · ） 图片/Clip02_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip02_mid.png · character_consistency
  - warn [detect] character_consistency @ 图片/Clip02_mid.png: character_consistency  图片/Clip02_mid.png 发型 H1 初筛：图片/Clip02_mid.png（发色/发型轮廓离群，非阻断） 
  - block [gate:image] character_consistency @ 图片/Clip02_mid.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 2（`EP03_CLIP02` · 搜尸求生：生存物资 · ） 图片/Clip02_mid.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
  - warn [gate:image] character_consistency @ 图片/Clip02_mid.png: character_consistency 发型 H1 初筛：图片/Clip02_mid.png（发色/发型轮廓离群，非阻断）

## 依赖传播

- nodes=109 · edges=146 · clips=10 · images=58 · videos=0
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第3集.json`

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
| 陈青源（CHAR_04） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 青面郎君（CHAR_05） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸场物资包（PROP_尸场物资包） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 荒野官道夜路（LOC_02） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 上盘村村口与村道（LOC_03） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 飞鹰门马匹与火把（MOUNT_GROUP_01） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 上盘村断石碑（PROP_上盘村断石碑） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 村道血迹破布（PROP_村道血迹破布） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 木架残肢剪影（PROP_木架残肢剪影） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 狼爪寒光（VFX_狼爪寒光） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| GROUP_飞鹰门众人（GROUP_飞鹰门众人） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| GROUP_狼妖群（GROUP_狼妖群） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 虎山神 / 虎妖（CHAR_03） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 妖气（VFX_妖气） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 残余金纹（VFX_残余金纹） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 系统面板（VFX_系统面板） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 虎山神摹影（VFX_虎山神摹影） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 道行计数 overlay（VFX_道行计数overlay） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 锚点门(N3)    
- [warn] CHAR_01__镇魔司伪装态 锚点门(N3)    
- [block] CHAR_01__镇魔司伪装态 脸(G1)    

## 🟡 陈青源（CHAR_04）
- [warn] CHAR_04__常态 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__囚犯初醒态, CHAR_01__镇
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_04__常态.png 生成事件缺 cost/provider 记账；无法计算重试性

## 🟡 青面郎君（CHAR_05）
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「基础」（出图/共享/图片/定妆_CHAR_05__常态

## 🟡 裴长青（CHAR_02）
- [warn] CHAR_02__濒死战损态 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__囚犯初醒态, CHAR_01__镇
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸

## 🟡 荒野尸骸战场（LOC_01）
- [warn]  跨集场景漂移(SCNX)    场景[荒野尸骸战场] 跨集色调/光位漂移 L1=0.6143（vs 前 2 集基线，阈 warn=0.45
- [warn]  跨集场景漂移(SCNX)    场景[荒野尸骸战场] 跨集结构漂移 dHash 汉明=24（vs 前 2 集结构原型，阈 warn=18·

## 🟡 尸场物资包（PROP_尸场物资包）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包.png 生成事件缺 cost/provider 记账；无法计算重试性价比和
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包_比例.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包_手持.png 生成事件缺 cost/provider 记账；无法计算重试性

## 🟡 荒野官道夜路（LOC_02）
- [warn]  场景平面(FP1)   场景 LOC_02 荒野官道夜路 本集复用 7 镜但缺 location_spatial_memory 条目；多视
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_荒野官道夜路.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_荒野官道夜路_反打.png 生成事件缺 cost/provider 记账；无法计算重试

## 🟡 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_镇魔司黑衣赤纹.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_镇魔司黑衣赤纹_比例.png 生成事件缺 cost/provider 记账；无法计算重
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_镇魔司黑衣赤纹_手持.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 飞鹰门马匹与火把（MOUNT_GROUP_01）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_飞鹰门马匹与火把.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_飞鹰门马匹与火把_比例.png 生成事件缺 cost/provider 记账；无法计算
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_飞鹰门马匹与火把_手持.png 生成事件缺 cost/provider 记账；无法计算

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
