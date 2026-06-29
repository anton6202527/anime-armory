# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 9 · 🔴 high 4 · 🟡 medium 10

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 1 | 0 | 6 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 1 | 0 | 56 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 12 | detect, gate:image_preflight, gate:image |
| 镜头 | ⛔ block | 14 | 0 | 10 | detect, gate:image_preflight, gate:image |
| 音频 | ⛔ block | 1 | 0 | 5 | detect, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 1 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 2 | 0 | 41 | detect, gate:image_preflight, gate:image, score |

### 剧情问题
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 6 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06），疑节奏塌·掉留存 
- warn [detect] 视线状态回读(X2):  视线状态回读(X2)   7 个视线/状态高风险镜当前 image_qc 精度为 degraded；需要 full QC 或人审签收，不能把降级绿灯当作像素一致已验证。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 7 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白
- warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白
- warn [gate:image] 语义谱系(P0) @ 脚本/第1集/storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。
- block [gate:image] 节奏密度(Rhythm) @ 脚本/第1集/storyboard.json: 节奏密度(Rhythm) [production一致性升级:关键场景] 连续 6 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06），疑节奏塌·掉留存。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.js

### 角色问题
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_HE_PINGSHENG 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
- warn [detect] 台词语域(D1):  台词语域(D1)   缺 dialogue_register/语域表；目前只能查称谓 + 文白横跳启发式，无法约束角色正式度、句长上限和禁用词。建议补 formality/sentence_len_max/forbidden/口癖。 
- warn [detect] 叙事状态(NS1):  叙事状态(NS1)   本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。 
- warn [detect] character_consistency @ 太虚门长老_回忆背影: character_consistency  太虚门长老_回忆背影 锚点门 N3：太虚门长老_回忆背影 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ 张老大: character_consistency  张老大 锚点门 N3：张老大 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ 江剑_背影: character_consistency  江剑_背影 锚点门 N3：江剑_背影 主参考非单张清晰正脸（非阻断） 
- warn [detect] character_consistency @ 群杂役_虚化: character_consistency  群杂役_虚化 锚点门 N3：群杂役_虚化 主参考非单张清晰正脸（非阻断） 

### 资产问题
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG/常态, CHAR_HE_PINGSHENG/肩颈红痕, CHAR_ZHANG_LAODA, CHAR_ZHANG_LAODA/常态, LOC_HOUSHAN_QIANTAN）但缺 entity_memory_bank；后续镜头无法按已验收
- warn [detect] image_qc_precision: image_qc_precision  None image_qc 精度为 degraded：正式进 video 前需补依赖重跑到 full 精度；普通人审记录只能辅助定位，不能替代 video/compose 前的 full QC gate。 
- warn [detect] scene_consistency: scene_consistency  None 接缝接力 未执行：视觉机检不可用；本轮图片一致性为降级判定，需补依赖后重跑或人工复核。 
- warn [detect] style_consistency: style_consistency  None 风格归属无法机检：style_contract 未登记风格锚（style_anchor）。请在定妆阶段出 1–2 张「国漫写实」风格锚图、登记进 style_contract.style_anchor，后续每集出图帧才能对锚做风格归属佐证。当前降级为人判：逐图核对是否踩 风格禁忌：低幼Q版、欧美卡通脸、照片级毛
- block [detect] multimodal_continuity @ 图片/Clip04_两缸水和空屋.png: multimodal_continuity  图片/Clip04_两缸水和空屋.png 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸水和空屋 的 `PROP_KEY_LOCK`（旧钥匙与生锈铁锁）登记了 must_not_have=现代防盗锁、金色宝物、符文刻字、巨大链锁、多套重复；scale=少年单手可握，锁体小，适合低矮旧房木门。。文字约束不能证
- block [detect] multimodal_continuity @ 图片/Clip04_两缸水和空屋.png: multimodal_continuity  图片/Clip04_两缸水和空屋.png 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸水和空屋 的 `PROP_TIE_WAN`（铁碗/钥匙铁锁）登记了 must_not_have=现代锁具、金色宝物、瓷碗、异物化、多套重复；scale=铁碗可手持，钥匙铁锁为小型杂役房门物件。。文字约束不能证明既有 PN
- block [detect] multimodal_continuity @ 图片/Clip05_夜挑五趟.png: multimodal_continuity  图片/Clip05_夜挑五趟.png 高风险道具禁形/尺寸未逐图确认：Clip 05 夜挑五趟 的 `PROP_SHUI_TONG`（水桶与扁担）登记了 must_not_have=现代塑料桶、金属水桶、单只桶漂移、华丽异物化；scale=少年挑水工具，桶身到少年膝上附近。。文字约束不能证明既有 PNG 没长出禁
- block [detect] multimodal_continuity @ 图片/Clip06_水底破盆.png: multimodal_continuity  图片/Clip06_水底破盆.png 高风险道具禁形/尺寸未逐图确认：Clip 06 水底破盆 🔑核心机缘 的 `PROP_HEI_TAO_PEN`（黑陶破盆）登记了 must_not_have=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；scale=普通脸盆大小，可被十四岁少年夹在臂弯。。文字约束不

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身世快闪用短促弦乐切片」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 
- warn [detect] 环境声(AMB):  环境声(AMB)   本集涉 5 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁；建 LOC→ambient bed 映射。 
- block [gate:image] 音乐母题(LM1) @ 设定库/leitmotif_registry.json: 音乐母题(LM1) [production一致性升级:关键场景] 本集有配乐/多角色但缺 设定库/leitmotif_registry.json——建议像 voice_key 一样为主要角色/情绪主题登记主题动机（subject→motif），保证跨集 BGM 母题可复现不串用。。如确认为可接受，写入 生产数据/consistency_advisory_si

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 

### 生产操作问题
- warn [detect] 锚点门(N3): 太虚门长老_回忆背影 锚点门(N3)    
- warn [detect] 锚点门(N3): 张老大 锚点门(N3)    
- warn [detect] 锚点门(N3): 江剑_背影 锚点门(N3)    
- warn [detect] 锚点门(N3): 群杂役_虚化 锚点门(N3)    
- warn [detect] 锚点门(N3): 贺三杰_回忆影 锚点门(N3)    
- warn [detect] 锚点门(N3): 贺平生 锚点门(N3)    
- warn [detect] 锚点门(N3): 贺平生_幼年 锚点门(N3)    
- block [detect] 锚点门(N3): 远景修士剪影 锚点门(N3)    

## 根因聚合

- block · audio:leitmotif_registry.json · 音乐母题(LM1)
  - block [gate:image] 音乐母题(LM1) @ 设定库/leitmotif_registry.json: 音乐母题(LM1) [production一致性升级:关键场景] 本集有配乐/多角色但缺 设定库/leitmotif_registry.json——建议像 voice_key 一样为主要角色/情绪主题登记主题动机（subject→motif），保证跨集 BGM 母题可复现不串用。。如确认为可接受，写入 生产数据/consistency_advisory_si
- block · character:图片 · 锚点门(N3)
  - block [gate:image] 锚点门(N3) @ 出图/共享/图片: 锚点门(N3) 一致性审计发现问题
  - warn [gate:image] 锚点门(N3) @ 出图/共享/图片: 锚点门(N3) 一致性审计发现问题
  - warn [gate:image] 锚点门(N3) @ 出图/共享/图片: 锚点门(N3) 一致性审计发现问题
- block · ops:ops · 锚点门(N3) / 成本路由(K1) / 人审校准集(CAL) / 一致性探针包(PROBE)
  - warn [detect] 锚点门(N3): 太虚门长老_回忆背影 锚点门(N3)    
  - warn [detect] 锚点门(N3): 张老大 锚点门(N3)    
  - warn [detect] 锚点门(N3): 江剑_背影 锚点门(N3)    
- block · ops:score_第1集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第1集.json: 缺 score JSON；验收总账无法闭环
- block · shot:Clip04_两缸水和空屋.png · multimodal_continuity
  - block [detect] multimodal_continuity @ 图片/Clip04_两缸水和空屋.png: multimodal_continuity  图片/Clip04_两缸水和空屋.png 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸水和空屋 的 `PROP_KEY_LOCK`（旧钥匙与生锈铁锁）登记了 must_not_have=现代防盗锁、金色宝物、符文刻字、巨大链锁、多套重复；scale=少年单手可握，锁体小，适合低矮旧房木门。。文字约束不能证
  - block [detect] multimodal_continuity @ 图片/Clip04_两缸水和空屋.png: multimodal_continuity  图片/Clip04_两缸水和空屋.png 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸水和空屋 的 `PROP_TIE_WAN`（铁碗/钥匙铁锁）登记了 must_not_have=现代锁具、金色宝物、瓷碗、异物化、多套重复；scale=铁碗可手持，钥匙铁锁为小型杂役房门物件。。文字约束不能证明既有 PN
  - block [gate:image] multimodal_continuity @ 图片/Clip04_两缸水和空屋.png: multimodal_continuity 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸水和空屋 的 `PROP_KEY_LOCK`（旧钥匙与生锈铁锁）登记了 must_not_have=现代防盗锁、金色宝物、符文刻字、巨大链锁、多套重复；scale=少年单手可握，锁体小，适合低矮旧房木门。。文字约束不能证明既有 PNG 没长出禁形或尺寸没漂，需人工
- block · shot:Clip05_夜挑五趟.png · multimodal_continuity
  - block [detect] multimodal_continuity @ 图片/Clip05_夜挑五趟.png: multimodal_continuity  图片/Clip05_夜挑五趟.png 高风险道具禁形/尺寸未逐图确认：Clip 05 夜挑五趟 的 `PROP_SHUI_TONG`（水桶与扁担）登记了 must_not_have=现代塑料桶、金属水桶、单只桶漂移、华丽异物化；scale=少年挑水工具，桶身到少年膝上附近。。文字约束不能证明既有 PNG 没长出禁
  - block [gate:image] multimodal_continuity @ 图片/Clip05_夜挑五趟.png: multimodal_continuity 高风险道具禁形/尺寸未逐图确认：Clip 05 夜挑五趟 的 `PROP_SHUI_TONG`（水桶与扁担）登记了 must_not_have=现代塑料桶、金属水桶、单只桶漂移、华丽异物化；scale=少年挑水工具，桶身到少年膝上附近。。文字约束不能证明既有 PNG 没长出禁形或尺寸没漂，需人工/视觉模型确认 `图
- block · shot:Clip06_水底破盆.png · multimodal_continuity
  - block [detect] multimodal_continuity @ 图片/Clip06_水底破盆.png: multimodal_continuity  图片/Clip06_水底破盆.png 高风险道具禁形/尺寸未逐图确认：Clip 06 水底破盆 🔑核心机缘 的 `PROP_HEI_TAO_PEN`（黑陶破盆）登记了 must_not_have=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；scale=普通脸盆大小，可被十四岁少年夹在臂弯。。文字约束不
  - block [detect] multimodal_continuity @ 图片/Clip06_水底破盆.png: multimodal_continuity  图片/Clip06_水底破盆.png 高风险道具禁形/尺寸未逐图确认：Clip 06 水底破盆 🔑核心机缘 的 `PROP_SHUI_TONG`（水桶与扁担）登记了 must_not_have=现代塑料桶、金属水桶、单只桶漂移、华丽异物化；scale=少年挑水工具，桶身到少年膝上附近。。文字约束不能证明既有 PN
  - block [gate:image] multimodal_continuity @ 图片/Clip06_水底破盆.png: multimodal_continuity 高风险道具禁形/尺寸未逐图确认：Clip 06 水底破盆 🔑核心机缘 的 `PROP_HEI_TAO_PEN`（黑陶破盆）登记了 must_not_have=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；scale=普通脸盆大小，可被十四岁少年夹在臂弯。。文字约束不能证明既有 PNG 没长出禁形或尺寸没漂
- block · shot:Clip07_盆底微光.png · multimodal_continuity
  - block [detect] multimodal_continuity @ 图片/Clip07_盆底微光.png: multimodal_continuity  图片/Clip07_盆底微光.png 高风险道具禁形/尺寸未逐图确认：Clip 07 盆底微光 🔑集尾硬断 的 `PROP_HEI_TAO_PEN`（黑陶破盆）登记了 must_not_have=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；scale=普通脸盆大小，可被十四岁少年夹在臂弯。。文字约束不
  - block [gate:image] multimodal_continuity @ 图片/Clip07_盆底微光.png: multimodal_continuity 高风险道具禁形/尺寸未逐图确认：Clip 07 盆底微光 🔑集尾硬断 的 `PROP_HEI_TAO_PEN`（黑陶破盆）登记了 must_not_have=强光柱、金边、符文文字、玉石质感、现代塑料盆、多盆重复；scale=普通脸盆大小，可被十四岁少年夹在臂弯。。文字约束不能证明既有 PNG 没长出禁形或尺寸没漂
- block · shot:reference_plan_第1集.json · 参考规划落实
  - block [gate:image_preflight] 参考规划落实 @ /Users/lalala/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/生产数据/reference_plan_第1集.json: 参考规划落实 逐镜参考规划有 19 条行动项未确认落实（无持久主体 ID 后端×大变化镜 7 镜）：镜头 EP01_CLIP01、EP01_CLIP02、EP01_CLIP03、EP01_CLIP04、EP01_CLIP05、EP01_CLIP06、EP01_CLIP07。请按 reference_plan_第1集.md 把补拍/多样参考/控制网/升档落进 
- block · shot:storyboard.json · 结构化交互图谱(I2)
  - block [gate:image] 结构化交互图谱(I2) @ 脚本/第1集/storyboard.json: 结构化交互图谱(I2) 接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- block · story:storyboard.json · 语义谱系(P0) / 节奏密度(Rhythm)
  - warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白
  - warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白
  - warn [gate:image] 语义谱系(P0) @ 脚本/第1集/storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。
- warn · asset:asset · 交互接触(I1) / 结构化交互图谱(I2)
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 

## 依赖传播

- nodes=28 · edges=39 · clips=7 · images=0 · videos=0
- graph: `创作区/制漫剧/仙界闭关小能手/生产数据/consistency_dependency_graph_第1集.json`

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
| 黑陶破盆（PROP_HEI_TAO_PEN） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 水桶与扁担（PROP_SHUI_TONG） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 铁碗/钥匙铁锁（PROP_TIE_WAN） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 旧钥匙与生锈铁锁（PROP_KEY_LOCK） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 贺平生（CHAR_HE_PINGSHENG） | character | 🔴 high | 🔴 | 🟡 | 🟢 |
| 张老大（CHAR_ZHANG_LAODA） | character | 🔴 high | 🔴 | 🟡 | 🟢 |
| 群杂役（CROWD_ZAYI） | character | 🔴 high | 🔴 | 🟡 | 🟢 |
| 后山山泉浅潭（LOC_HOUSHAN_QIANTAN） | location | 🔴 high | 🔴 | 🟡 | 🟢 |
| 韩老三（CHAR_HAN_LAOSAN） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 江剑（CHAR_JIANG_JIAN） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 太虚门长老（CHAR_TAIXUMEN_ZHANGLAO） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 贺三杰（CHAR_HE_SANJIE） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 秀竹峰杂役大殿（LOC_ZAYI_DADIAN） | location | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 秀竹峰杂役院与空房（LOC_ZAYI_YUAN） | location | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 太虚门外门旧院/秀竹峰山门回忆场（LOC_WAIMEN_JIUYUAN） | location | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 太虚门远景修士剪影（CROWD_TAIXU_CULTIVATOR） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 黑陶破盆（PROP_HEI_TAO_PEN）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_黑陶破盆.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换
- [block] multimodal_continuity  图片/Clip06_水底破盆.png 高风险道具禁形/尺寸未逐图确认：Clip 06 水底破盆
- [block] multimodal_continuity  图片/Clip07_盆底微光.png 高风险道具禁形/尺寸未逐图确认：Clip 07 盆底微光

## ⛔ 水桶与扁担（PROP_SHUI_TONG）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_水桶与扁担.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切
- [block] multimodal_continuity  图片/Clip05_夜挑五趟.png 高风险道具禁形/尺寸未逐图确认：Clip 05 夜挑五趟
- [block] multimodal_continuity  图片/Clip06_水底破盆.png 高风险道具禁形/尺寸未逐图确认：Clip 06 水底破盆

## ⛔ 铁碗/钥匙铁锁（PROP_TIE_WAN）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_铁碗钥匙铁锁.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型
- [block] multimodal_continuity  图片/Clip04_两缸水和空屋.png 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸

## ⛔ 旧钥匙与生锈铁锁（PROP_KEY_LOCK）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_旧钥匙与生锈铁锁.png 生成事件缺 cost/provider 记账；无法计算重试性价比和
- [block] multimodal_continuity  图片/Clip04_两缸水和空屋.png 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸

## 🔴 贺平生（CHAR_HE_PINGSHENG）
- [warn] 贺平生 锚点门(N3)    
- [warn] 贺平生_幼年 锚点门(N3)    
- [warn]  多视角身份包(MVIEW)   核心/长线角色 CHAR_HE_PINGSHENG 缺 identity_eval_pack / mult

## 🔴 张老大（CHAR_ZHANG_LAODA）
- [warn] 张老大 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG/常态, CHAR_
- [warn]  成本路由(K1)   出图/共享/图片/定妆_张老大.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成

## 🔴 群杂役（CROWD_ZAYI）
- [warn] 群杂役_虚化 锚点门(N3)    
- [warn]  成本路由(K1)   出图/共享/图片/定妆_群杂役_虚化_三视图.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn] character_consistency  群杂役_虚化 锚点门 N3：群杂役_虚化 主参考非单张清晰正脸（非阻断） 

## 🔴 后山山泉浅潭（LOC_HOUSHAN_QIANTAN）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG/常态, CHAR_
- [warn]  成本路由(K1)   出图/共享/图片/定妆_后山山泉浅潭.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型

## 🟡 韩老三（CHAR_HAN_LAOSAN）
- [warn] 韩老三 锚点门(N3)    
- [warn]  成本路由(K1)   出图/共享/图片/定妆_韩老三.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成
- [warn]  成本路由(K1)   出图/共享/图片/定妆_韩老三_三视图.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 🟡 江剑（CHAR_JIANG_JIAN）
- [warn] 江剑_背影 锚点门(N3)    
- [warn]  成本路由(K1)   出图/共享/图片/定妆_江剑_背影_三视图.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn] character_consistency  江剑_背影 锚点门 N3：江剑_背影 主参考非单张清晰正脸（非阻断） 

## 🟡 太虚门长老（CHAR_TAIXUMEN_ZHANGLAO）
- [warn] 太虚门长老_回忆背影 锚点门(N3)    
- [warn]  成本路由(K1)   出图/共享/图片/定妆_太虚门长老_回忆背影_三视图.png 生成事件缺 cost/provider 记账；无法计算
- [warn] character_consistency  太虚门长老_回忆背影 锚点门 N3：太虚门长老_回忆背影 主参考非单张清晰正脸（非阻断） 

## 🟡 贺三杰（CHAR_HE_SANJIE）
- [warn] 贺三杰_回忆影 锚点门(N3)    
- [warn]  成本路由(K1)   出图/共享/图片/定妆_贺三杰_回忆影_三视图.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn] character_consistency  贺三杰_回忆影 锚点门 N3：贺三杰_回忆影 主参考非单张清晰正脸（非阻断） 

## 🟡 秀竹峰杂役大殿（LOC_ZAYI_DADIAN）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_秀竹峰杂役大殿.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 🟡 太虚门外门旧院/秀竹峰山门回忆场（LOC_WAIMEN_JIUYUAN）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_太虚门外门旧院.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模

## 未归属到具体角色/资产的一致性问题
- [block] 远景修士剪影 锚点门(N3)    
- [warn]  配音情绪弧(VEA)   镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身
- [warn]  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- [warn]  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响
- [warn]  节奏密度(Rhythm)   连续 6 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CL
- [warn]  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / s
- [warn]  视线状态回读(X2)   7 个视线/状态高风险镜当前 image_qc 精度为 degraded；需要 full QC 或人审签收，不能

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
