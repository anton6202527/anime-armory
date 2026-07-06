# 验收总账 · 第4集

- 验收状态：阻断
- ⛔ block 7 · 🔴 high 0 · 🟡 medium 19

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 1 | 0 | 40 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 角色 | ⛔ block | 31 | 0 | 88 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | ⛔ block | 1 | 0 | 24 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | ⛔ block | 12 | 0 | 22 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 18 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 2 | 0 | 34 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

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
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    
- block [detect] 脸(G1):  脸(G1)    

### 资产问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_11（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__镇魔司伪装态, CHAR_04, CHAR_04__, CHAR_04__常态）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 荒野官道夜路 本集复用 3 镜但缺 location_spatial_memory 条目；多视角/反打时门窗、固定物、光源和合法机位只靠文字记忆。 
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 返村官道 本集复用 2 镜但缺 location_spatial_memory 条目；多视角/反打时门窗、固定物、光源和合法机位只靠文字记忆。 
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 上盘村村道 本集复用 5 镜但缺 location_spatial_memory 条目；多视角/反打时门窗、固定物、光源和合法机位只靠文字记忆。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道_反打.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道_平面图.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头3·姜月初：台词含强情绪但配音标注「内心崩溃」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头18·陈青源：台词含强情绪但配音标注「压低」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头43·姜月初：台词含强情绪但配音标注「杀意」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「[镜头18 “闻弦之境”] 弦乐急停」→「[镜头23-24 上盘村村口] 环境」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第4集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=d643994814874cd5，但复跑审计证据不完整。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第4集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=9e19649ba3ea8589，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第4集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   合成/第4集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 声音空间(ASP):  声音空间(ASP)   声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_perspective/occlusion_policy。 
- warn [detect] 物理事件图(PHY):  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_01__囚犯初醒态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_GROUP_飞鹰门众人__常态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_GROUP_狼妖群__常态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_05__常态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_03__诈死复苏态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_02__濒死战损态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- block · asset:asset · 打斗撞点(SPEC-APEX) / 结构化交互图谱(I2) / 成本路由(K1)
  - warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_11（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- block · character:CHAR_01 · 多视角身份包(MVIEW) / 实体记忆(EMB) / image_prompt_lint / 脸漂预案
  - warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_01 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
  - warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__镇魔司伪装态, CHAR_04, CHAR_04__, CHAR_04__常态）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
  - block [detect] image_prompt_lint: image_prompt_lint  None 脸部锚弱信噪比 CHAR_01/镇魔司伪装态「基础」（出图/共享/图片/定妆_CHAR_01__镇魔司伪装态.png）：脸占画面仅 1%（建议 ≥30%，至少 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 
- block · character:character · 脸(G1) / 跨集脸漂(G5) / 真值源(TRUTH) / 叙事状态(NS1) / image_prompt_lint
  - block [detect] 脸(G1):  脸(G1)    
  - block [detect] 脸(G1):  脸(G1)    
  - block [detect] 脸(G1):  脸(G1)    
- block · character:image_qc_第4集.json · 出图落档QC
  - block [gate:image] 出图落档QC @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/image_qc/第4集/image_qc_第4集.json: 出图落档QC 输入首帧 image_qc 仍有 3 项硬阻断（崩脸/人体解剖N5/接缝断/降级精度近景/非法 CHAR/缺高风险人体合约）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。
- block · ops:candidate_selection_第4集.json · 关键镜候选
  - block [gate:image] 关键镜候选 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/生产数据/candidate_selection_第4集.json: 关键镜候选 production 出图后缺 candidate_selection_第4集.json；关键镜必须经过 best-of-N 选优而不是单张通过。生成候选后跑 `python3 skills/n2d-image/scripts/candidate_select.py "/Users/wesley/learn/anime-armory/创作区/制漫
- block · ops:score_第4集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第4集.json: 缺 score JSON；验收总账无法闭环
- block · shot:Clip01_first.png · multimodal_continuity
  - block [detect] multimodal_continuity @ 图片/Clip01_first.png: multimodal_continuity  图片/Clip01_first.png 高风险道具禁形/尺寸未逐图确认：镜头 1（`EP04_CLIP01` · 求援冷开：救上盘村 · dialogue_shot_reverse） 的 `PROP_镇魔司黑衣赤纹`（镇魔司黑衣赤纹）登记了 must_not_have=现代物件、文字水印、结构漂移、数量漂移；sc
  - block [gate:image] multimodal_continuity @ 图片/Clip01_first.png: multimodal_continuity 高风险道具禁形/尺寸未逐图确认：镜头 1（`EP04_CLIP01` · 求援冷开：救上盘村 · dialogue_shot_reverse） 的 `PROP_镇魔司黑衣赤纹`（镇魔司黑衣赤纹）登记了 must_not_have=现代物件、文字水印、结构漂移、数量漂移；scale=None。文字约束不能证明既有 P
- block · shot:Clip02_first.png · multimodal_continuity
  - block [detect] multimodal_continuity @ 图片/Clip02_first.png: multimodal_continuity  图片/Clip02_first.png 高风险道具禁形/尺寸未逐图确认：镜头 2（`EP04_CLIP02` · 姜月初接案：假皮变责任 · relationship_turn） 的 `PROP_镇魔司黑衣赤纹`（镇魔司黑衣赤纹）登记了 must_not_have=现代物件、文字水印、结构漂移、数量漂移；scal
  - block [gate:image] multimodal_continuity @ 图片/Clip02_first.png: multimodal_continuity 高风险道具禁形/尺寸未逐图确认：镜头 2（`EP04_CLIP02` · 姜月初接案：假皮变责任 · relationship_turn） 的 `PROP_镇魔司黑衣赤纹`（镇魔司黑衣赤纹）登记了 must_not_have=现代物件、文字水印、结构漂移、数量漂移；scale=None。文字约束不能证明既有 PNG
- block · shot:ambient_map.json · 环境声(AMB)
  - block [gate:image] 环境声(AMB) @ 设定库/ambient_map.json: 环境声(AMB) [production一致性升级:重复同维度] 场景 荒野官道夜路（3 镜）在 ambient_map.json 无登记环境声床——补一条 荒野官道夜路→ambient bed。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第4集.json 的 accepted 后复跑；finding_hash
  - block [gate:image] 环境声(AMB) @ 设定库/ambient_map.json: 环境声(AMB) [production一致性升级:重复同维度] 场景 返村官道（2 镜）在 ambient_map.json 无登记环境声床——补一条 返村官道→ambient bed。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第4集.json 的 accepted 后复跑；finding_hash=193
  - block [gate:image] 环境声(AMB) @ 设定库/ambient_map.json: 环境声(AMB) [production一致性升级:重复同维度] 场景 上盘村村口（1 镜）在 ambient_map.json 无登记环境声床——补一条 上盘村村口→ambient bed。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第4集.json 的 accepted 后复跑；finding_hash=7
- block · shot:location_spatial_memory.json · 场景平面(FP1)
  - block [gate:image] 场景平面(FP1) @ 设定库/location_spatial_memory.json: 场景平面(FP1) [production一致性升级:重复同维度] 场景 荒野官道夜路 本集复用 3 镜但缺 location_spatial_memory 条目；多视角/反打时门窗、固定物、光源和合法机位只靠文字记忆。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第4集.json 的 accepted 后复跑；
  - block [gate:image] 场景平面(FP1) @ 设定库/location_spatial_memory.json: 场景平面(FP1) [production一致性升级:重复同维度] 场景 返村官道 本集复用 2 镜但缺 location_spatial_memory 条目；多视角/反打时门窗、固定物、光源和合法机位只靠文字记忆。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第4集.json 的 accepted 后复跑；fi
  - block [gate:image] 场景平面(FP1) @ 设定库/location_spatial_memory.json: 场景平面(FP1) [production一致性升级:重复同维度] 场景 上盘村村道 本集复用 5 镜但缺 location_spatial_memory 条目；多视角/反打时门窗、固定物、光源和合法机位只靠文字记忆。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第4集.json 的 accepted 后复跑；f
- block · shot:storyboard.json · 结构化交互图谱(I2)
  - block [gate:image] 结构化交互图谱(I2) @ 脚本/第4集/storyboard.json: 结构化交互图谱(I2) 接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- block · story:storyboard.json · 跨集色调 / 语义谱系(P0) / 节奏密度(Rhythm)
  - warn [gate:image_preflight] 跨集色调 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第4集/storyboard.json: 跨集色调 本集色调基线基调「冷灰晨雾、低饱和血迹、青灰村道」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）
  - warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子
  - warn [gate:image] 跨集色调 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第4集/storyboard.json: 跨集色调 本集色调基线基调「冷灰晨雾、低饱和血迹、青灰村道」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画风跳）

## 依赖传播

- nodes=45 · edges=59 · clips=11 · images=6 · videos=0
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
| 姜月初（CHAR_01） | character | ⛔ block | 🟡 | ⛔ | 🟢 |
| 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
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
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 飞鹰门马匹与火把（MOUNT_GROUP_01） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 上盘村断石碑（PROP_上盘村断石碑） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 村道血迹破布（PROP_村道血迹破布） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 木架残肢剪影（PROP_木架残肢剪影） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 狼爪寒光（VFX_狼爪寒光） | vfx | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 妖气（VFX_妖气） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 残余金纹（VFX_残余金纹） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 系统面板（VFX_系统面板） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 虎山神摹影（VFX_虎山神摹影） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 道行计数 overlay（VFX_道行计数overlay） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚犯初醒态 跨集脸漂(G5)    CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4
- [warn]  配音情绪弧(VEA)   镜头3·姜月初：台词含强情绪但配音标注「内心崩溃」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  配音情绪弧(VEA)   镜头43·姜月初：台词含强情绪但配音标注「杀意」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为

## ⛔ 镇魔司黑衣赤纹（PROP_镇魔司黑衣赤纹）
- [block] multimodal_continuity  图片/Clip01_first.png 高风险道具禁形/尺寸未逐图确认：镜头 1（`EP04_
- [block] multimodal_continuity  图片/Clip02_first.png 高风险道具禁形/尺寸未逐图确认：镜头 2（`EP04_

## 🟡 陈青源（CHAR_04）
- [warn]  配音情绪弧(VEA)   镜头18·陈青源：台词含强情绪但配音标注「压低」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01__, CHAR_01__镇魔司伪装态, CHAR_04, 
- [warn] character_consistency  CHAR_04__常态 锚点门 N3：CHAR_04__常态 主参考非单张清晰正脸（非阻断） 

## 🟡 GROUP_飞鹰门众人（GROUP_飞鹰门众人）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_飞鹰门众人__常态.png 生成事件缺 cost/provider 记账；无法计

## 🟡 GROUP_狼妖群（GROUP_狼妖群）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_狼妖群__常态.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 青面郎君（CHAR_05）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_05__常态.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_05__常态.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_05__常态_三视图.png 生成事件缺 cost/provider 记账；无法计

## 🟡 虎山神 / 虎妖（CHAR_03）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_03__诈死复苏态.png 生成事件缺 cost/provider 记账；无法计算

## 🟡 裴长青（CHAR_02）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_02__濒死战损态.png 生成事件缺 cost/provider 记账；无法计算
- [warn] character_consistency  CHAR_02__濒死战损态 锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸

## 🟡 荒野官道夜路（LOC_02）
- [warn]  场景平面(FP1)   场景 荒野官道夜路 本集复用 3 镜但缺 location_spatial_memory 条目；多视角/反打时门窗
- [warn]  环境声(AMB)   场景 荒野官道夜路（3 镜）在 ambient_map.json 无登记环境声床——补一条 荒野官道夜路→ambie

## 🟡 上盘村村口与村道（LOC_03）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道_反打.png 生成事件缺 cost/provider 记账；无法计算
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_上盘村村口与村道_平面图.png 生成事件缺 cost/provider 记账；无法计

## 🟡 上盘村断石碑（PROP_上盘村断石碑）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_上盘村断石碑.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_上盘村断石碑_比例.png 生成事件缺 cost/provider 记账；无法计算重试
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_上盘村断石碑_手持.png 生成事件缺 cost/provider 记账；无法计算重试

## 🟡 村道血迹破布（PROP_村道血迹破布）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_村道血迹破布.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_村道血迹破布_比例.png 生成事件缺 cost/provider 记账；无法计算重试

## 🟡 木架残肢剪影（PROP_木架残肢剪影）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_木架残肢剪影.png 生成事件缺 cost/provider 记账；无法计算重试性价比

## 🟡 狼爪寒光（VFX_狼爪寒光）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_特效_狼爪寒光.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 未归属到具体角色/资产的一致性问题
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    
- [block]  脸(G1)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
