# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 4 · 🔴 high 0 · 🟡 medium 35

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 6 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 132 | 0 | 101 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 86 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | ⛔ block | 3 | 0 | 77 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 14 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 3 | detect |
| 合规 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 3 | 0 | 39 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 10 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10→EP01_CLIP11），疑节奏塌·掉留存 
- warn [detect] 视线状态回读(X2):  视线状态回读(X2)   15 个视线/状态高风险镜当前 image_qc 精度为 degraded；需要 full QC 或人审签收，不能把降级绿灯当作像素一致已验证。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 15 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子
- warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子

### 角色问题
- warn [detect] 服装配色(N1): CHAR_WUDA__日常卖饼态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_PANJINLIAN__25岁武大家常态 服装配色(N1)    
- warn [detect] 发型(H1): CHAR_WUDA__日常卖饼态 发型(H1)    
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_09：角色 CHAR_WUSONG 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_09：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_15：角色 CHAR_WUSONG 相邻镜情绪硬跳（悲→怒）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_15：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（悲→怒）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 

### 资产问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_01（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_02（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
- warn [detect] 持有账本(POS):  持有账本(POS)   PROP_BADGE 在 Clip_02 有持有状态，但 possession_ledger 未登记本镜状态。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip01_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.015 vs 场景中位 -0.203）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip01_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 -0.006 vs 场景中位 -0.203）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/Clip02_end.png：色温/调色与同场景其它镜不一致——本镜偏冷(蓝)（暖冷 -0.389 vs 场景中位 -0.203）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP01_CLIP02_a3.png：色温/调色与同场景其它镜不一致——本镜偏冷(蓝)（暖冷 -0.383 vs 场景中位 -0.203）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（BEAST_TIGER/扑击态, CHAR_MAGISTRATE, CHAR_PANJINLIAN, CHAR_PANJINLIAN__, CHAR_PANJINLIAN__25岁武大家常态, CHAR_WUDA）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_场景_景阳冈夜间空地.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头1·旁白：台词含强情绪但配音标注「紧张」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头29·武松：台词含强情绪但配音标注「克制」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐母题(LM1):  音乐母题(LM1)   音乐母题 MOTIF_WUSONG 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。 
- warn [detect] 音乐母题(LM1):  音乐母题(LM1)   音乐母题 MOTIF_WUSONG 缺 audio_sha256/hash/cue；无法确认 compose 复用的是同一段动机。 
- warn [detect] 音乐母题(LM1):  音乐母题(LM1)   音乐母题 MOTIF_JINLIAN 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。 
- warn [detect] 音乐母题(LM1):  音乐母题(LM1)   音乐母题 MOTIF_JINLIAN 缺 audio_sha256/hash/cue；无法确认 compose 复用的是同一段动机。 
- warn [detect] 音乐母题(LM1):  音乐母题(LM1)   音乐母题 MOTIF_THRESHOLD 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。 
- warn [detect] 音乐母题(LM1):  音乐母题(LM1)   音乐母题 MOTIF_THRESHOLD 缺 audio_sha256/hash/cue；无法确认 compose 复用的是同一段动机。 

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_04 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_11 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ 创作区/制漫剧/金瓶梅/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/金瓶梅/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/金瓶梅/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 风格(S1):  风格(S1)    
- block [detect] 糊/低质(N4):  糊/低质(N4)    
- warn [detect] 糊/低质(N4):  糊/低质(N4)    
- warn [detect] 糊/低质(N4):  糊/低质(N4)    
- warn [detect] 物理事件图(PHY):  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/风格锚_北宋市井写实电影感.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_WUSONG__28岁打虎态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_CHAR_WUSONG__28岁打虎态.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

## 根因聚合

- block · character:Clip01_end.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip01_end.png: character_consistency  图片/Clip01_end.png 降级精度多人同框：图片/Clip01_end.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-ar
  - block [gate:image] character_consistency @ 图片/Clip01_end.png: character_consistency 降级精度多人同框：图片/Clip01_end.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产
- block · character:Clip01_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip01_first.png: character_consistency  图片/Clip01_first.png 降级精度多人同框：图片/Clip01_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anim
  - block [gate:image] character_consistency @ 图片/Clip01_first.png: character_consistency 降级精度多人同框：图片/Clip01_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/
- block · character:Clip02_end.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip02_end.png: character_consistency  图片/Clip02_end.png 降级精度多人同框：图片/Clip02_end.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-ar
  - block [gate:image] character_consistency @ 图片/Clip02_end.png: character_consistency 降级精度多人同框：图片/Clip02_end.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/生产
- block · character:Clip02_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip02_first.png: character_consistency  图片/Clip02_first.png 降级精度多人同框：图片/Clip02_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anim
  - block [gate:image] character_consistency @ 图片/Clip02_first.png: character_consistency 降级精度多人同框：图片/Clip02_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/
- block · character:Clip03_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip03_first.png: character_consistency  图片/Clip03_first.png 降级精度多人同框：图片/Clip03_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anim
  - block [detect] character_consistency @ 图片/Clip03_first.png: character_consistency  图片/Clip03_first.png 角色脸定妆比对覆盖缺口：镜头 3（`EP01_CLIP03` · 打虎成名，家门转冷 · ensemble_blocking） 图片/Clip03_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full 
  - block [gate:image] character_consistency @ 图片/Clip03_first.png: character_consistency 降级精度多人同框：图片/Clip03_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/
- block · character:Clip04_end.png · image_artifact_presence
  - block [detect] image_artifact_presence @ 图片/Clip04_end.png: image_artifact_presence  图片/Clip04_end.png 出图目标尚未生成：图片/Clip04_end.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。 
  - block [gate:image] image_artifact_presence @ 图片/Clip04_end.png: image_artifact_presence 出图目标尚未生成：图片/Clip04_end.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。
- block · character:Clip04_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip04_first.png: character_consistency  图片/Clip04_first.png 降级精度多人同框：图片/Clip04_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anim
  - block [detect] character_consistency @ 图片/Clip04_first.png: character_consistency  图片/Clip04_first.png 角色脸定妆比对覆盖缺口：镜头 4（`EP01_CLIP04` · 一担炊饼与一扇楼窗 · ensemble_blocking） 图片/Clip04_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full 
  - block [gate:image] character_consistency @ 图片/Clip04_first.png: character_consistency 降级精度多人同框：图片/Clip04_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/
- block · character:Clip05_end.png · image_artifact_presence
  - block [detect] image_artifact_presence @ 图片/Clip05_end.png: image_artifact_presence  图片/Clip05_end.png 出图目标尚未生成：图片/Clip05_end.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。 
  - block [gate:image] image_artifact_presence @ 图片/Clip05_end.png: image_artifact_presence 出图目标尚未生成：图片/Clip05_end.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。
- block · character:Clip05_first.png · character_consistency
  - block [detect] character_consistency @ 图片/Clip05_first.png: character_consistency  图片/Clip05_first.png 降级精度多人同框：图片/Clip05_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anim
  - block [detect] character_consistency @ 图片/Clip05_first.png: character_consistency  图片/Clip05_first.png 角色脸定妆比对覆盖缺口：镜头 5（`EP01_CLIP05` · 兄弟重逢，楼上第一次看见 · multi_character_same_frame） 图片/Clip05_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/
  - block [gate:image] character_consistency @ 图片/Clip05_first.png: character_consistency 降级精度多人同框：图片/Clip05_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/
- block · character:Clip05_first_a3.png · image_artifact_presence
  - block [detect] image_artifact_presence @ 图片/Clip05_first_a3.png: image_artifact_presence  图片/Clip05_first_a3.png 出图目标尚未生成：图片/Clip05_first_a3.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。 
  - block [gate:image] image_artifact_presence @ 图片/Clip05_first_a3.png: image_artifact_presence 出图目标尚未生成：图片/Clip05_first_a3.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。
- block · character:Clip06_first.png · image_artifact_presence
  - block [detect] image_artifact_presence @ 图片/Clip06_first.png: image_artifact_presence  图片/Clip06_first.png 出图目标尚未生成：图片/Clip06_first.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。 
  - block [gate:image] image_artifact_presence @ 图片/Clip06_first.png: image_artifact_presence 出图目标尚未生成：图片/Clip06_first.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。
- block · character:Clip07_end.png · image_artifact_presence
  - block [detect] image_artifact_presence @ 图片/Clip07_end.png: image_artifact_presence  图片/Clip07_end.png 出图目标尚未生成：图片/Clip07_end.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。 
  - block [gate:image] image_artifact_presence @ 图片/Clip07_end.png: image_artifact_presence 出图目标尚未生成：图片/Clip07_end.png；当前无法执行脸/身份像素质检。这是产物缺件，不是崩脸判定。

## 依赖传播

- nodes=66 · edges=194 · clips=15 · images=15 · videos=0
- graph: `创作区/制漫剧/金瓶梅/生产数据/consistency_dependency_graph_第1集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=3

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 景阳冈夜间空地（LOC_JINGYANGGANG） | scene | ⛔ block | 🟡 | ⛔ | 🟢 |
| 武松（CHAR_WUSONG） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 景阳冈猛虎（BEAST_TIGER） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 猎户群像（CROWD_HUNTERS） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 武大（CHAR_WUDA） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 潘金莲（CHAR_PANJINLIAN） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 知县（CHAR_MAGISTRATE） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 西门庆（CHAR_XIMENQING） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 梢棒（PROP_QUARTERSTAFF） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 都头腰牌（PROP_BADGE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| REWARD SILVER（PROP_REWARD_SILVER） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 阳谷街面与武大家楼窗（LOC_YANGGU_STREET） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 炊饼担（PROP_CAKE_POLE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| WINDOW LATTICE（PROP_WINDOW_LATTICE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 武大家楼屋雪夜（LOC_WUDA_HOME） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| STAIR RAIL（PROP_STAIR_RAIL） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| DINING TABLE（PROP_DINING_TABLE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| TEA CUP（PROP_TEA_CUP） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| DOORFRAME（PROP_DOORFRAME） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 门闩（PROP_DOOR_LATCH） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 炭盆（PROP_BRAZIER） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 半杯酒（PROP_WINE_CUP） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| SPILLED WINE（PROP_SPILLED_WINE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 素布行李（PROP_LUGGAGE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 武大家木门（PROP_DOOR） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 县衙案厅（LOC_COUNTY_YAMEN） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 公文（PROP_OFFICIAL_DOC） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 东京礼担（PROP_GIFT_LOAD） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 阳谷城门清晨（LOC_CITY_GATE） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| WINDOW CURTAIN（PROP_WINDOW_CURTAIN） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 叉竿（PROP_CURTAIN_FORK） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |

## ⛔ 景阳冈夜间空地（LOC_JINGYANGGANG）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_景阳冈夜间空地.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_景阳冈夜间空地_反打.png 生成事件缺 cost/provider 记账；无法计算重
- [block] multimodal_continuity  None 关键场景/道具/服装/VFX 已进入 scene/multimodal QC，但 D

## 🟡 武松（CHAR_WUSONG）
- [warn]  配音情绪弧(VEA)   镜头29·武松：台词含强情绪但配音标注「克制」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 
- [warn]  表情连续(EXP1)   Clip_09：角色 CHAR_WUSONG 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演
- [warn]  表情连续(EXP1)   Clip_15：角色 CHAR_WUSONG 相邻镜情绪硬跳（悲→怒）——确认有节拍/事件依据，否则表演 OOC

## 🟡 景阳冈猛虎（BEAST_TIGER）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（BEAST_TIGER/扑击态, CHAR_MAGISTRATE, CHAR_PANJINL
- [warn]  成本路由(K1)   出图/共享/图片/定妆_BEAST_TIGER__常态.png 生成事件缺 cost/provider 记账；无法计
- [warn]  成本路由(K1)   出图/共享/图片/定妆_BEAST_TIGER__常态.png 生成事件缺 cost/provider 记账；无法计

## 🟡 猎户群像（CROWD_HUNTERS）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CROWD_HUNTERS__常态.png 生成事件缺 cost/provider 记账；无

## 🟡 武大（CHAR_WUDA）
- [warn] CHAR_WUDA__日常卖饼态 服装配色(N1)    
- [warn] CHAR_PANJINLIAN__25岁武大家常态 服装配色(N1)    
- [warn] CHAR_WUDA__日常卖饼态 发型(H1)    

## 🟡 潘金莲（CHAR_PANJINLIAN）
- [warn] CHAR_PANJINLIAN__25岁武大家常态 服装配色(N1)    
- [warn]  表情连续(EXP1)   Clip_09：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，
- [warn]  表情连续(EXP1)   Clip_15：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（悲→怒）——确认有节拍/事件依据，否则表演

## 🟡 知县（CHAR_MAGISTRATE）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（BEAST_TIGER/扑击态, CHAR_MAGISTRATE, CHAR_PANJINL
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_MAGISTRATE__常态.png 生成事件缺 cost/provider 记账
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_MAGISTRATE__常态.png 生成事件缺 cost/provider 记账

## 🟡 西门庆（CHAR_XIMENQING）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_XIMENQING__常态.png 生成事件缺 cost/provider 记账；
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_XIMENQING__常态.png 生成事件缺 cost/provider 记账；

## 🟡 梢棒（PROP_QUARTERSTAFF）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_梢棒.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_梢棒_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价比和
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_梢棒_手持.png 生成事件缺 cost/provider 记账；无法计算重试性价比和

## 🟡 都头腰牌（PROP_BADGE）
- [warn]  持有账本(POS)   PROP_BADGE 在 Clip_02 有持有状态，但 possession_ledger 未登记本镜状态。 
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_都头腰牌.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_都头腰牌_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价

## 🟡 REWARD SILVER（PROP_REWARD_SILVER）
- [warn] image_prompt_lint  None 资产 PROP_REWARD_SILVER：出图/共享/图片/定妆_道具_REWARD_SI

## 🟡 阳谷街面与武大家楼窗（LOC_YANGGU_STREET）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_阳谷街面与武大家楼窗.png 生成事件缺 cost/provider 记账；无法计算重
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_阳谷街面与武大家楼窗_反打.png 生成事件缺 cost/provider 记账；无法
- [warn] image_prompt_lint  None 资产 LOC_YANGGU_STREET：出图/共享/图片/定妆_场景_阳谷街面与武大家楼窗

## 🟡 炊饼担（PROP_CAKE_POLE）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_炊饼担.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_炊饼担_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_炊饼担_手持.png 生成事件缺 cost/provider 记账；无法计算重试性价比

## 🟡 WINDOW LATTICE（PROP_WINDOW_LATTICE）
- [warn] image_prompt_lint  None 资产 PROP_WINDOW_LATTICE：出图/共享/图片/定妆_道具_WINDOW_L

## 🟡 DINING TABLE（PROP_DINING_TABLE）
- [warn] image_prompt_lint  None 资产 PROP_DINING_TABLE：出图/共享/图片/定妆_道具_DINING_TAB

## 🟡 DOORFRAME（PROP_DOORFRAME）
- [warn] image_prompt_lint  None 资产 PROP_DOORFRAME：出图/共享/图片/定妆_道具_DOORFRAME_反面.

## 🟡 SPILLED WINE（PROP_SPILLED_WINE）
- [warn] image_prompt_lint  None 资产 PROP_SPILLED_WINE：出图/共享/图片/定妆_道具_SPILLED_WI

## 🟡 素布行李（PROP_LUGGAGE）
- [warn] image_prompt_lint  None 资产 PROP_LUGGAGE：出图/共享/图片/定妆_道具_素布行李_比例.png fac
- [warn] image_prompt_lint  None 资产 PROP_LUGGAGE：出图/共享/图片/定妆_道具_素布行李_手持.png fac

## 🟡 武大家木门（PROP_DOOR）
- [warn] image_prompt_lint  None 资产 PROP_DOORFRAME：出图/共享/图片/定妆_道具_DOORFRAME_反面.
- [warn] image_prompt_lint  None 资产 PROP_DOOR：出图/共享/图片/定妆_道具_武大家木门.png faceless
- [warn] image_prompt_lint  None 资产 PROP_DOOR：出图/共享/图片/定妆_道具_武大家木门_比例.png facel

## 🟡 公文（PROP_OFFICIAL_DOC）
- [warn] image_prompt_lint  None 资产 PROP_OFFICIAL_DOC：出图/共享/图片/定妆_道具_公文_比例.png 
- [warn] image_prompt_lint  None 资产 PROP_OFFICIAL_DOC：出图/共享/图片/定妆_道具_公文_手持.png 

## 🟡 东京礼担（PROP_GIFT_LOAD）
- [warn] image_prompt_lint  None 资产 PROP_GIFT_LOAD：出图/共享/图片/定妆_道具_东京礼担_比例.png f
- [warn] image_prompt_lint  None 资产 PROP_GIFT_LOAD：出图/共享/图片/定妆_道具_东京礼担_手持.png f

## 🟡 WINDOW CURTAIN（PROP_WINDOW_CURTAIN）
- [warn] image_prompt_lint  None 资产 PROP_WINDOW_CURTAIN：出图/共享/图片/定妆_道具_WINDOW_C
- [warn] image_prompt_lint  None 资产 PROP_WINDOW_CURTAIN：出图/共享/图片/定妆_道具_WINDOW_C

## 🟡 叉竿（PROP_CURTAIN_FORK）
- [warn] image_prompt_lint  None 资产 PROP_CURTAIN_FORK：出图/共享/图片/定妆_道具_叉竿_比例.png 
- [warn] image_prompt_lint  None 资产 PROP_CURTAIN_FORK：出图/共享/图片/定妆_道具_叉竿_手持.png 

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  打斗撞点(SPEC-APEX)    Clip_01（fight_exchange）：impact 剪辑峰值（hit_stop/scree
- [warn]  打斗撞点(SPEC-APEX)    Clip_02（fight_exchange）：impact 剪辑峰值（hit_stop/scree
- [warn]  风格(S1)    
- [warn]  色温调色(GRADE1)   图片/Clip01_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.015 v
- [warn]  色温调色(GRADE1)   图片/Clip01_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 -0.00
- [warn]  色温调色(GRADE1)   图片/Clip02_end.png：色温/调色与同场景其它镜不一致——本镜偏冷(蓝)（暖冷 -0.389 v
- [warn]  色温调色(GRADE1)   图片/EP01_CLIP02_a3.png：色温/调色与同场景其它镜不一致——本镜偏冷(蓝)（暖冷 -0.3

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
