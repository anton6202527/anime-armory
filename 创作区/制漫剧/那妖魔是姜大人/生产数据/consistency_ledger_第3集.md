# 验收总账 · 第3集

- 验收状态：阻断
- ⛔ block 3 · 🔴 high 0 · 🟡 medium 15

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 1 | 0 | 64 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 23 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | 🟡 warn | 0 | 0 | 25 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 16 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 2 | 0 | 38 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 10 个长镜聚集（EP03_CLIP01→EP03_CLIP02→EP03_CLIP03→EP03_CLIP04→EP03_CLIP05→EP03_CLIP06→EP03_CLIP07→EP03_CLIP08→EP03_CLIP09→EP03_CLIP10），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 跨集色调 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
- warn [gate:image] 跨集色调 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json: 跨集色调 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）

### 角色问题
- block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- warn [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
- warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4469)，相对基线掉幅 -0.0412，且本集均值低于绝对下限——已系统性偏离定妆锚
- warn [detect] 服装配色(N1): CHAR_01__囚犯初醒态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚犯初醒态 服装配色(N1)    
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_01 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_01__镇魔司伪装态_脸部特写_脸锚裁切.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

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
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__囚犯初醒态, CHAR_01__镇魔司伪装态, CHAR_02, CHAR_04）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 LOC_02 荒野官道夜路 本集复用 7 镜但缺 location_spatial_memory 条目；多视角/反打时门窗、固定物、光源和合法机位只靠文字记忆。 

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
- warn [gate:image_preflight] 合规前置 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): CHAR_01__囚犯初醒态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_01__镇魔司伪装态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_02__濒死战损态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_04__常态 锚点门(N3)    
- warn [detect] 声音空间(ASP):  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_perspective/occlusion_policy。 
- warn [detect] 物理事件图(PHY):  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_01__镇魔司伪装态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_01__镇魔司伪装态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- block · character:character · 脸(G1) / 跨集脸漂(G5) / 服装配色(N1) / 真值源(TRUTH) / 成本路由(K1) / 叙事状态(NS1) / image_prompt_lint
  - block [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
  - warn [detect] 脸(G1): CHAR_01__镇魔司伪装态 脸(G1)    
  - warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4469)，相对基线掉幅 -0.0412，且本集均值低于绝对下限——已系统性偏离定妆锚
- block · ops:candidate_selection_第3集.json · 关键镜候选
  - block [gate:image] 关键镜候选 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/candidate_selection_第3集.json: 关键镜候选 关键镜 best-of-N 未闭环：缺选片行 EP03_CLIP09、EP03_CLIP10。补候选、重跑 candidate_select.py，直到每个关键镜都有 K>=3 的终选或明确重抽处方。
- block · ops:score_第3集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第3集.json: 缺 score JSON；验收总账无法闭环
- warn · asset:asset · 结构化交互图谱(I2) / 成本路由(K1)
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn · asset:asset_registry.json asset#5 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#5: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#5: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · asset:asset_registry.json asset#6 · 资产引用注册层
  - warn [gate:image_preflight] 资产引用注册层 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#6: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
  - warn [gate:image] 资产引用注册层 @ 创作区/制漫剧/那妖魔是姜大人/出图/共享/asset_registry.json asset#6: 资产引用注册层 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变
- warn · audio:audio · 配音情绪弧(VEA) / 音乐衔接(BGM) / 生成配方(RCP) / 强配方Schema(RCP2) / 成本路由(K1)
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头1·旁白：台词含强情绪但配音标注「低沉」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头18·姜月初：台词含强情绪但配音标注「内心崩溃」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头19·旁白：台词含强情绪但配音标注「悬停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn · audio:第3集 · 配音
  - warn [gate:image_preflight] 配音 @ 第3集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image_prompt_preflight] 配音 @ 第3集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
  - warn [gate:image] 配音 @ 第3集: 配音 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时
- warn · character:01_分镜出图.md ## 镜头 10（`EP03_CLIP10` · 唯一希望：集尾硬断 · dialogue_shot_reverse） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md ## 镜头 10（`EP03_CLIP10` · 唯一希望：集尾硬断 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md ## 镜头 10（`EP03_CLIP10` · 唯一希望：集尾硬断 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 1（`EP03_CLIP01` · 埋尸冷开：欠命账落地 · multi_character_same_frame） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md ## 镜头 1（`EP03_CLIP01` · 埋尸冷开：欠命账落地 · multi_character_same_frame）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md ## 镜头 1（`EP03_CLIP01` · 埋尸冷开：欠命账落地 · multi_character_same_frame）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 5（`EP03_CLIP05` · 马队火把齐停 · mount_ride） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md ## 镜头 5（`EP03_CLIP05` · 马队火把齐停 · mount_ride）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md ## 镜头 5（`EP03_CLIP05` · 马队火把齐停 · mount_ride）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
- warn · character:01_分镜出图.md ## 镜头 6（`EP03_CLIP06` · 少说话的冷面官威 · dialogue_shot_reverse） · 角色一致性
  - warn [gate:image_preflight] 角色一致性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md ## 镜头 6（`EP03_CLIP06` · 少说话的冷面官威 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂
  - warn [gate:image] 角色一致性 @ 创作区/制漫剧/那妖魔是姜大人/出图/第3集/prompt/01_分镜出图.md ## 镜头 6（`EP03_CLIP06` · 少说话的冷面官威 · dialogue_shot_reverse）: 角色一致性 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂

## 依赖传播

- nodes=36 · edges=67 · clips=10 · images=10 · videos=0
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
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 陈青源（CHAR_04） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 飞鹰门马队（GROUP_飞鹰门马队） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 飞鹰门马匹与火把（MOUNT_GROUP_01） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸场物资包（PROP_尸场物资包） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 荒野官道夜路（LOC_02） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 虎山神 / 虎妖（CHAR_03） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 锚点门(N3)    
- [warn] CHAR_01__镇魔司伪装态 锚点门(N3)    
- [block] CHAR_01__镇魔司伪装态 脸(G1)    

## 🟡 裴长青（CHAR_02）
- [warn] CHAR_02__濒死战损态 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__囚犯初醒态, CHAR_01__镇
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸

## 🟡 陈青源（CHAR_04）
- [warn] CHAR_04__常态 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__囚犯初醒态, CHAR_01__镇
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_04__常态.png 生成事件缺 cost/provider 记账；无法计算重试性

## 🟡 飞鹰门马队（GROUP_飞鹰门马队）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_飞鹰门马队__常态.png 生成事件缺 cost/provider 记账；无法计
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_飞鹰门马队__常态_手部局部.png 生成事件缺 cost/provider 记
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_飞鹰门马队__常态_布料局部.png 生成事件缺 cost/provider 记

## 🟡 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_镇魔司黑衣赤纹.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_镇魔司黑衣赤纹_比例.png 生成事件缺 cost/provider 记账；无法计算重
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_镇魔司黑衣赤纹_手持.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 飞鹰门马匹与火把（MOUNT_GROUP_01）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_飞鹰门马匹与火把.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_飞鹰门马匹与火把_比例.png 生成事件缺 cost/provider 记账；无法计算
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_飞鹰门马匹与火把_手持.png 生成事件缺 cost/provider 记账；无法计算

## 🟡 尸场物资包（PROP_尸场物资包）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包.png 生成事件缺 cost/provider 记账；无法计算重试性价比和
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包_比例.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_尸场物资包_手持.png 生成事件缺 cost/provider 记账；无法计算重试性

## 🟡 荒野官道夜路（LOC_02）
- [warn]  场景平面(FP1)   场景 LOC_02 荒野官道夜路 本集复用 7 镜但缺 location_spatial_memory 条目；多视
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_荒野官道夜路.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_荒野官道夜路_反打.png 生成事件缺 cost/provider 记账；无法计算重试

## 未归属到具体角色/资产的一致性问题
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」（注册 key_light_direction）——实测光
- [warn]  配音情绪弧(VEA)   镜头1·旁白：台词含强情绪但配音标注「低沉」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒
- [warn]  配音情绪弧(VEA)   镜头19·旁白：台词含强情绪但配音标注「悬停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 
- [warn]  配音情绪弧(VEA)   镜头27·旁白：台词含强情绪但配音标注「沉下」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
