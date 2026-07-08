# 验收总账 · 第4集

- 验收状态：阻断
- ⛔ block 3 · 🔴 high 0 · 🟡 medium 22

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 39 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 角色 | ⛔ block | 68 | 0 | 85 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 23 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | ⛔ block | 1 | 0 | 54 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 12 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟢 ok | 0 | 0 | 0 | — |
| 合规 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 2 | 0 | 62 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 11 个长镜聚集（EP04_CLIP01→EP04_CLIP02→EP04_CLIP03→EP04_CLIP04→EP04_CLIP05→EP04_CLIP06→EP04_CLIP07→EP04_CLIP08→EP04_CLIP09→EP04_CLIP10→EP04_CLIP11），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 11 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第4集/storyboard.json 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=442802c5a0b83a40，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第4集/storyboard.json 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver
- warn [gate:image_preflight] 故事板 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第4集/storyboard.json clip#2: 故事板 start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。
- warn [gate:image_preflight] 故事板 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第4集/storyboard.json clip#3: 故事板 start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。
- warn [gate:image_preflight] 故事板 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第4集/storyboard.json clip#4: 故事板 start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。

### 角色问题
- warn [detect] 跨集脸漂(G5): CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性偏离定妆锚
- warn [detect] 叙事状态(NS1):  叙事状态(NS1)   本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。 
- warn [detect] character_consistency @ CHAR_01__囚犯初醒态: character_consistency  CHAR_01__囚犯初醒态 跨集脸漂移趋势 medium：CHAR_01__囚犯初醒态 第1集→第2集 mean 0.406→0.4461 drop=-0.0401。high 级系统性退化必须先回 n2d-image 补主体库/参考包/重抽并重跑 identity/image_qc。 
- warn [detect] character_consistency @ CHAR_01__囚犯初醒态: character_consistency  CHAR_01__囚犯初醒态 锚点门 N3：CHAR_01__囚犯初醒态 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ CHAR_01__镇魔司伪装态: character_consistency  CHAR_01__镇魔司伪装态 锚点门 N3：CHAR_01__镇魔司伪装态 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ CHAR_02__濒死战损态: character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ CHAR_04__常态: character_consistency  CHAR_04__常态 锚点门 N3：CHAR_04__常态 主参考非单张清晰正脸（非阻断） 
- warn [detect] image_prompt_lint: image_prompt_lint  None 脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 0%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再

### 资产问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_11（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 PROP_镇魔司黑衣赤纹 出现于 11 镜，但 entity_memory_bank 没有已验收记忆条目。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 PROP_上盘村断石碑 出现于 2 镜，但 entity_memory_bank 没有已验收记忆条目。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 PROP_村道血迹破布 出现于 2 镜，但 entity_memory_bank 没有已验收记忆条目。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 PROP_木架残肢剪影 出现于 2 镜，但 entity_memory_bank 没有已验收记忆条目。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    [allowed_variations 已签收] 场景[荒野官道夜路] 跨集结构漂移 dHash 汉明=27（vs 前 1 集结构原型，阈 warn=18·core block=26）——核心场景跨集结构硬漂：色调没动但布局/家具/构图朝向变了（同房间被重新布置/拍反向），回 n2d-image 对齐场景定妆 spatial
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道_反打.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道_平面图.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__镇魔司伪装态」↔ 本镜 图片/Clip01_end.png DINO/CLIP cosine=0.40 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头3·姜月初：台词含强情绪但配音标注「内心崩溃」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头18·陈青源：台词含强情绪但配音标注「压低」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头43·姜月初：台词含强情绪但配音标注「杀意」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「[镜头18 “闻弦之境”] 弦乐急停」→「[镜头23-24 上盘村村口] 环境」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第4集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=d643994814874cd5，但复跑审计证据不完整。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第4集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=9e19649ba3ea8589，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第4集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   合成/第4集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 糊/低质(N4):  糊/低质(N4)    
- warn [detect] 声音空间(ASP):  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_perspective/occlusion_policy。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 CHAR_04 出现于 8 镜，但 entity_memory_bank 没有已验收记忆条目。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 GROUP_飞鹰门众人 出现于 5 镜，但 entity_memory_bank 没有已验收记忆条目。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 CHAR_05 出现于 11 镜，但 entity_memory_bank 没有已验收记忆条目。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   重复/核心实体 CHAR_04__ 出现于 8 镜，但 entity_memory_bank 没有已验收记忆条目。 

## 根因聚合

- block · character:Clip01_end.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_end.png: character_consistency 降级精度近景：图片/Clip01_end.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_re
  - block [gate:image] character_consistency @ 图片/Clip01_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP04_CLIP01` · 求援冷开：救上盘村 · dialogue_shot_reverse） 图片/Clip01_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip01_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_first.png: character_consistency 降级精度近景：图片/Clip01_first.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_
  - block [gate:image] character_consistency @ 图片/Clip01_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP04_CLIP01` · 求援冷开：救上盘村 · dialogue_shot_reverse） 图片/Clip01_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip01_mid.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_mid.png: character_consistency 降级精度近景：图片/Clip01_mid.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_re
  - block [gate:image] character_consistency @ 图片/Clip01_mid.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP04_CLIP01` · 求援冷开：救上盘村 · dialogue_shot_reverse） 图片/Clip01_mid.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip02_end.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip02_end.png: character_consistency 降级精度近景：图片/Clip02_end.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_re
  - block [gate:image] character_consistency @ 图片/Clip02_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 2（`EP04_CLIP02` · 姜月初接案：假皮变责任 · relationship_turn） 图片/Clip02_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip02_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip02_first.png: character_consistency 降级精度近景：图片/Clip02_first.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_
  - block [gate:image] character_consistency @ 图片/Clip02_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 2（`EP04_CLIP02` · 姜月初接案：假皮变责任 · relationship_turn） 图片/Clip02_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip02_mid.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip02_mid.png: character_consistency 降级精度近景：图片/Clip02_mid.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_re
  - block [gate:image] character_consistency @ 图片/Clip02_mid.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 2（`EP04_CLIP02` · 姜月初接案：假皮变责任 · relationship_turn） 图片/Clip02_mid.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip03_end.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip03_end.png: character_consistency 降级精度近景：图片/Clip03_end.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_re
  - block [gate:image] character_consistency @ 图片/Clip03_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 3（`EP04_CLIP03` · 返村路：青面郎君情报 · mount_ride） 图片/Clip03_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip03_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip03_first.png: character_consistency 降级精度近景：图片/Clip03_first.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_
  - block [gate:image] character_consistency @ 图片/Clip03_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 3（`EP04_CLIP03` · 返村路：青面郎君情报 · mount_ride） 图片/Clip03_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip03_mid.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip03_mid.png: character_consistency 降级精度近景：图片/Clip03_mid.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_re
  - block [gate:image] character_consistency @ 图片/Clip03_mid.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 3（`EP04_CLIP03` · 返村路：青面郎君情报 · mount_ride） 图片/Clip03_mid.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip04_end.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip04_end.png: character_consistency 降级精度近景：图片/Clip04_end.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_re
  - block [gate:image] character_consistency @ 图片/Clip04_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 4（`EP04_CLIP04` · 闻弦战力账：必须赢 · reveal_reaction_chain） 图片/Clip04_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip04_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip04_first.png: character_consistency 降级精度近景：图片/Clip04_first.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_
  - block [gate:image] character_consistency @ 图片/Clip04_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 4（`EP04_CLIP04` · 闻弦战力账：必须赢 · reveal_reaction_chain） 图片/Clip04_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip04_mid.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip04_mid.png: character_consistency 降级精度近景：图片/Clip04_mid.png 在 Pillow 降级模式下无法验脸（无 insightface）；近景/特写脸是否同人未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/face_re
  - block [gate:image] character_consistency @ 图片/Clip04_mid.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 4（`EP04_CLIP04` · 闻弦战力账：必须赢 · reveal_reaction_chain） 图片/Clip04_mid.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。

## 依赖传播

- nodes=74 · edges=87 · clips=11 · images=34 · videos=0
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第4集.json`

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
| 陈青源（CHAR_04） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| GROUP_飞鹰门众人（GROUP_飞鹰门众人） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| GROUP_狼妖群（GROUP_狼妖群） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 青面郎君（CHAR_05） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 虎山神 / 虎妖（CHAR_03） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 荒野尸骸战场（LOC_01） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 尸场物资包（PROP_尸场物资包） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 荒野官道夜路（LOC_02） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 上盘村村口与村道（LOC_03） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 飞鹰门马匹与火把（MOUNT_GROUP_01） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 上盘村断石碑（PROP_上盘村断石碑） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 村道血迹破布（PROP_村道血迹破布） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 木架残肢剪影（PROP_木架残肢剪影） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 狼爪寒光（VFX_狼爪寒光） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 妖气（VFX_妖气） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 残余金纹（VFX_残余金纹） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 系统面板（VFX_系统面板） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 虎山神摹影（VFX_虎山神摹影） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 道行计数 overlay（VFX_道行计数overlay） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 百妖谱金光（VFX_百妖谱金光） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## 🟡 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4
- [warn]  配音情绪弧(VEA)   镜头3·姜月初：台词含强情绪但配音标注「内心崩溃」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  配音情绪弧(VEA)   镜头43·姜月初：台词含强情绪但配音标注「杀意」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为

## 🟡 陈青源（CHAR_04）
- [warn]  配音情绪弧(VEA)   镜头18·陈青源：台词含强情绪但配音标注「压低」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为
- [warn]  实体记忆(EMB)   重复/核心实体 CHAR_04 出现于 8 镜，但 entity_memory_bank 没有已验收记忆条目。 
- [warn]  实体记忆(EMB)   重复/核心实体 CHAR_04__ 出现于 8 镜，但 entity_memory_bank 没有已验收记忆条目。

## 🟡 GROUP_飞鹰门众人（GROUP_飞鹰门众人）
- [warn]  实体记忆(EMB)   重复/核心实体 GROUP_飞鹰门众人 出现于 5 镜，但 entity_memory_bank 没有已验收记忆条
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_飞鹰门众人__常态.png 生成事件缺 cost/provider 记账；无法计

## 🟡 GROUP_狼妖群（GROUP_狼妖群）
- [warn]  实体记忆(EMB)   重复/核心实体 GROUP_狼妖群 出现于 6 镜，但 entity_memory_bank 没有已验收记忆条目。
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_狼妖群__常态.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 青面郎君（CHAR_05）
- [warn]  实体记忆(EMB)   重复/核心实体 CHAR_05 出现于 11 镜，但 entity_memory_bank 没有已验收记忆条目。 
- [warn]  实体记忆(EMB)   重复/核心实体 CHAR_05__ 出现于 6 镜，但 entity_memory_bank 没有已验收记忆条目。
- [warn]  实体记忆(EMB)   重复/核心实体 CHAR_05__常态 出现于 6 镜，但 entity_memory_bank 没有已验收记忆条

## 🟡 虎山神 / 虎妖（CHAR_03）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_03__诈死复苏态.png 生成事件缺 cost/provider 记账；无法计算

## 🟡 裴长青（CHAR_02）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_02__濒死战损态.png 生成事件缺 cost/provider 记账；无法计算
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸

## 🟡 荒野官道夜路（LOC_02）
- [warn]  跨集场景漂移(SCNX)    [allowed_variations 已签收] 场景[荒野官道夜路] 跨集结构漂移 dHash 汉明=2
- [warn]  实体记忆(EMB)   重复/核心实体 LOC_02 出现于 5 镜，但 entity_memory_bank 没有已验收记忆条目。 
- [warn]  实体记忆(EMB)   重复/核心实体 荒野官道夜路 出现于 3 镜，但 entity_memory_bank 没有已验收记忆条目。 

## 🟡 上盘村村口与村道（LOC_03）
- [warn]  实体记忆(EMB)   重复/核心实体 LOC_03 出现于 6 镜，但 entity_memory_bank 没有已验收记忆条目。 
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道_反打.png 生成事件缺 cost/provider 记账；无法计算

## 🟡 横刀（WEAPON_01）
- [warn]  实体记忆(EMB)   重复/核心实体 WEAPON_01 横刀 出现于 2 镜，但 entity_memory_bank 没有已验收记忆

## 🟡 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹）
- [warn]  实体记忆(EMB)   重复/核心实体 PROP_镇魔司黑衣赤纹 出现于 11 镜，但 entity_memory_bank 没有已验收记

## 🟡 飞鹰门马匹与火把（MOUNT_GROUP_01）
- [warn]  实体记忆(EMB)   重复/核心实体 MOUNT_GROUP_01 飞鹰门马匹与火把 出现于 3 镜，但 entity_memory_b

## 🟡 上盘村断石碑（PROP_上盘村断石碑）
- [warn]  实体记忆(EMB)   重复/核心实体 PROP_上盘村断石碑 出现于 2 镜，但 entity_memory_bank 没有已验收记忆条
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_上盘村断石碑.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_上盘村断石碑_比例.png 生成事件缺 cost/provider 记账；无法计算重试

## 🟡 村道血迹破布（PROP_村道血迹破布）
- [warn]  实体记忆(EMB)   重复/核心实体 PROP_村道血迹破布 出现于 2 镜，但 entity_memory_bank 没有已验收记忆条
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_村道血迹破布.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_村道血迹破布_比例.png 生成事件缺 cost/provider 记账；无法计算重试

## 🟡 木架残肢剪影（PROP_木架残肢剪影）
- [warn]  实体记忆(EMB)   重复/核心实体 PROP_木架残肢剪影 出现于 2 镜，但 entity_memory_bank 没有已验收记忆条
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_木架残肢剪影.png 生成事件缺 cost/provider 记账；无法计算重试性价比

## 🟡 狼爪寒光（VFX_狼爪寒光）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_特效_狼爪寒光.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  打斗撞点(SPEC-APEX)    Clip_11（fight_exchange）：impact 剪辑峰值（hit_stop/scree
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  糊/低质(N4)    
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「[镜头18 “闻弦之境”] 弦乐急停」→「[镜头23-24
- [warn]  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
