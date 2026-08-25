# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 2 · 🔴 high 0 · 🟡 medium 37

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 5 | detect, gate:image_preflight, gate:image |
| 角色 | 🟡 warn | 0 | 0 | 92 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 82 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | ⛔ block | 1 | 0 | 98 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 14 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 3 | detect |
| 合规 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 3 | 0 | 37 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 10 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10→EP01_CLIP11），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 15 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子
- warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子

### 角色问题
- warn [detect] 脸(G1): CHAR_WUSONG__28岁打虎态 脸(G1)    
- warn [detect] 脸(G1): CHAR_WUDA__日常卖饼态 脸(G1)    
- warn [detect] 脸(G1): CHAR_WUSONG__28岁打虎态 脸(G1)    
- warn [detect] 服装配色(N1): CHAR_WUDA__日常卖饼态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_PANJINLIAN__25岁武大家常态 服装配色(N1)    
- warn [detect] 发型(H1): CHAR_WUDA__日常卖饼态 发型(H1)    
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_09：角色 CHAR_WUSONG 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_09：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 

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
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/金瓶梅/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/金瓶梅/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): CHAR_MAGISTRATE__常态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_PANJINLIAN__25岁武大家常态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_WUDA__日常卖饼态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_WUSONG__28岁打虎态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_XIMENQING__常态 锚点门(N3)    
- warn [detect] 风格(S1):  风格(S1)    
- block [detect] 糊/低质(N4):  糊/低质(N4)    
- warn [detect] 糊/低质(N4):  糊/低质(N4)    

## 根因聚合

- block · ops:ops · 锚点门(N3) / 风格(S1) / 糊/低质(N4) / 物理事件图(PHY) / 成本路由(K1) / 人审校准集(CAL) / 一致性探针包(PROBE)
  - warn [detect] 锚点门(N3): CHAR_MAGISTRATE__常态 锚点门(N3)    
  - warn [detect] 锚点门(N3): CHAR_PANJINLIAN__25岁武大家常态 锚点门(N3)    
  - warn [detect] 锚点门(N3): CHAR_WUDA__日常卖饼态 锚点门(N3)    
- block · ops:production_events.jsonl:line 504 · 固定 Seed / 生成配方证据
  - warn [gate:image] 固定 Seed @ 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl:line 504: 固定 Seed image 生成事件记录了 requested_seed，但缺少 seed_strategy；支持 seed 时要记 effective_seed/seed_effective=true，不支持时要记 seed_effective=false + seed_support=unsupported_or_unknown。
  - block [gate:image] 生成配方证据 @ 创作区/制漫剧/金瓶梅/生产数据/production_events.jsonl:line 504: 生成配方证据 出图/第1集/图片/Clip05_first.png 生成事件缺必填配方证据：route_hash。每个最终媒体必须记录 provider/model/channel/route_hash/capability_evidence_id/recipe_hash/prompt_sha256/reference_bundle_sha256/backe
- block · ops:score_第1集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第1集.json: 缺 score JSON；验收总账无法闭环
- block · shot:图片 · 糊/低质(N4)
  - block [gate:image] 糊/低质(N4) @ 出图/第1集/图片: 糊/低质(N4) 一致性审计发现问题
- warn · asset:asset · 打斗撞点(SPEC-APEX) / 持有账本(POS) / 结构化交互图谱(I2) / 成本路由(K1) / 系统面板(UI1)
  - warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_01（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
  - warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_02（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
  - warn [detect] 持有账本(POS):  持有账本(POS)   PROP_BADGE 在 Clip_02 有持有状态，但 possession_ledger 未登记本镜状态。 
- warn · asset:场景定妆.md ## 县衙案厅（`LOC_COUNTY_YAMEN`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 县衙案厅（`LOC_COUNTY_YAMEN`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:30>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 县衙案厅（`LOC_COUNTY_YAMEN`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:30>16
- warn · asset:场景定妆.md ## 景阳冈夜间空地（`LOC_JINGYANGGANG`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 景阳冈夜间空地（`LOC_JINGYANGGANG`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:32>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 景阳冈夜间空地（`LOC_JINGYANGGANG`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:32>16
- warn · asset:场景定妆.md ## 武大家楼屋雪夜（`LOC_WUDA_HOME`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 武大家楼屋雪夜（`LOC_WUDA_HOME`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:34>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 武大家楼屋雪夜（`LOC_WUDA_HOME`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:34>16
- warn · asset:场景定妆.md ## 阳谷城门清晨（`LOC_CITY_GATE`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 阳谷城门清晨（`LOC_CITY_GATE`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:33>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 阳谷城门清晨（`LOC_CITY_GATE`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:33>16
- warn · asset:场景定妆.md ## 阳谷街面与武大家楼窗（`LOC_YANGGU_STREET`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 阳谷街面与武大家楼窗（`LOC_YANGGU_STREET`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:33>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/金瓶梅/出图/共享/prompt/场景定妆.md ## 阳谷街面与武大家楼窗（`LOC_YANGGU_STREET`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:33>16
- warn · asset:道具定妆.md ## DINING TABLE（`PROP_DINING_TABLE`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/出图/共享/prompt/道具定妆.md ## DINING TABLE（`PROP_DINING_TABLE`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:24>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/金瓶梅/出图/共享/prompt/道具定妆.md ## DINING TABLE（`PROP_DINING_TABLE`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:24>16
- warn · asset:道具定妆.md ## DOORFRAME（`PROP_DOORFRAME`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/金瓶梅/出图/共享/prompt/道具定妆.md ## DOORFRAME（`PROP_DOORFRAME`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:25>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/金瓶梅/出图/共享/prompt/道具定妆.md ## DOORFRAME（`PROP_DOORFRAME`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:25>16

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
| 武松（CHAR_WUSONG） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| BEAST_TIGER（BEAST_TIGER） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| Hunters（CROWD_HUNTERS） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 武大（CHAR_WUDA） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 潘金莲（CHAR_PANJINLIAN） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 知县（CHAR_MAGISTRATE） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 西门庆（CHAR_XIMENQING） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 景阳冈夜间空地（LOC_JINGYANGGANG） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 梢棒（PROP_QUARTERSTAFF） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 都头腰牌（PROP_BADGE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| REWARD SILVER（PROP_REWARD_SILVER） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 阳谷街面与武大家楼窗（LOC_YANGGU_STREET） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 炊饼担（PROP_CAKE_POLE） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| WINDOW LATTICE（PROP_WINDOW_LATTICE） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 武大家楼屋雪夜（LOC_WUDA_HOME） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| STAIR RAIL（PROP_STAIR_RAIL） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| DINING TABLE（PROP_DINING_TABLE） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| TEA CUP（PROP_TEA_CUP） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| DOORFRAME（PROP_DOORFRAME） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 门闩（PROP_DOOR_LATCH） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 炭盆（PROP_BRAZIER） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 半杯酒（PROP_WINE_CUP） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| SPILLED WINE（PROP_SPILLED_WINE） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 素布行李（PROP_LUGGAGE） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 武大家木门（PROP_DOOR） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 县衙案厅（LOC_COUNTY_YAMEN） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 公文（PROP_OFFICIAL_DOC） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 东京礼担（PROP_GIFT_LOAD） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 阳谷城门清晨（LOC_CITY_GATE） | scene | 🟡 medium | 🟡 | 🟢 | 🟢 |
| WINDOW CURTAIN（PROP_WINDOW_CURTAIN） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 叉竿（PROP_CURTAIN_FORK） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |

## 🟡 武松（CHAR_WUSONG）
- [warn] CHAR_WUSONG__28岁打虎态 锚点门(N3)    
- [warn] CHAR_WUSONG__28岁打虎态 脸(G1)    
- [warn] CHAR_WUSONG__28岁打虎态 脸(G1)    

## 🟡 BEAST_TIGER（BEAST_TIGER）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（BEAST_TIGER/扑击态, CHAR_MAGISTRATE, CHAR_PANJINL
- [warn]  成本路由(K1)   出图/共享/图片/定妆_BEAST_TIGER__常态.png 生成事件缺 cost/provider 记账；无法计
- [warn]  成本路由(K1)   出图/共享/图片/定妆_BEAST_TIGER__常态.png 生成事件缺 cost/provider 记账；无法计

## 🟡 Hunters（CROWD_HUNTERS）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CROWD_HUNTERS__常态.png 生成事件缺 cost/provider 记账；无

## 🟡 武大（CHAR_WUDA）
- [warn] CHAR_PANJINLIAN__25岁武大家常态 锚点门(N3)    
- [warn] CHAR_WUDA__日常卖饼态 锚点门(N3)    
- [warn] CHAR_WUDA__日常卖饼态 脸(G1)    

## 🟡 潘金莲（CHAR_PANJINLIAN）
- [warn] CHAR_PANJINLIAN__25岁武大家常态 锚点门(N3)    
- [warn] CHAR_PANJINLIAN__25岁武大家常态 服装配色(N1)    
- [warn]  表情连续(EXP1)   Clip_09：角色 CHAR_PANJINLIAN 相邻镜情绪硬跳（喜→怒/悲/惊）——确认有节拍/事件依据，

## 🟡 知县（CHAR_MAGISTRATE）
- [warn] CHAR_MAGISTRATE__常态 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（BEAST_TIGER/扑击态, CHAR_MAGISTRATE, CHAR_PANJINL
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_MAGISTRATE__常态.png 生成事件缺 cost/provider 记账

## 🟡 西门庆（CHAR_XIMENQING）
- [warn] CHAR_XIMENQING__常态 锚点门(N3)    
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_XIMENQING__常态.png 生成事件缺 cost/provider 记账；
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_XIMENQING__常态.png 生成事件缺 cost/provider 记账；

## 🟡 景阳冈夜间空地（LOC_JINGYANGGANG）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_景阳冈夜间空地.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_景阳冈夜间空地_反打.png 生成事件缺 cost/provider 记账；无法计算重

## 🟡 梢棒（PROP_QUARTERSTAFF）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_梢棒.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_梢棒_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价比和
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_梢棒_手持.png 生成事件缺 cost/provider 记账；无法计算重试性价比和

## 🟡 都头腰牌（PROP_BADGE）
- [warn]  持有账本(POS)   PROP_BADGE 在 Clip_02 有持有状态，但 possession_ledger 未登记本镜状态。 
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_都头腰牌.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_都头腰牌_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价

## 🟡 阳谷街面与武大家楼窗（LOC_YANGGU_STREET）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_阳谷街面与武大家楼窗.png 生成事件缺 cost/provider 记账；无法计算重
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_阳谷街面与武大家楼窗_反打.png 生成事件缺 cost/provider 记账；无法

## 🟡 炊饼担（PROP_CAKE_POLE）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_炊饼担.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_炊饼担_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_炊饼担_手持.png 生成事件缺 cost/provider 记账；无法计算重试性价比

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
