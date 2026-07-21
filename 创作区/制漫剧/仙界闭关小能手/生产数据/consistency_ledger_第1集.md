# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 6 · 🔴 high 0 · 🟡 medium 14

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 3 | 0 | 9 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 25 | 0 | 64 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 39 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 镜头 | ⛔ block | 1 | 0 | 56 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 音频 | ⛔ block | 1 | 0 | 9 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 2 | 0 | 41 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, score |

### 剧情问题
- warn [detect] 节奏密度(Rhythm) @ 脚本/第1集/storyboard.json:  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：62.6 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 4 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04），疑节奏塌·掉留存 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 低梁下的羞辱』），疑慢热；开场镜时长 6.2s > 5s，前3秒易掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 7 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 剧情经济性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json: 剧情经济性 story_economy_audit 仍有 2 条压缩建议；本次不硬拦，但建议在付费生成前处理，避免解释/行进/普通反应占用视频预算。
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `众杂役` 未进入 storyboard。；缺：众杂役
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白
- warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `众杂役` 未进入 storyboard。；缺：众杂役

### 角色问题
- warn [detect] 脸(G1): CHAR_01__本集为14岁杂役常态 脸(G1)    
- warn [detect] 脸(G1): CHAR_02__常态 脸(G1)    
- warn [detect] 脸(G1): CHAR_01__本集为14岁杂役常态 脸(G1)    
- block [detect] 脸(G1): CHAR_01__本集为14岁杂役常态 脸(G1)    
- warn [detect] 脸(G1): CHAR_01__本集为14岁杂役常态 脸(G1)    
- block [detect] 脸(G1): CHAR_01__本集为14岁杂役常态 脸(G1)    
- block [detect] 服装配色(N1): CHAR_01__本集为14岁杂役常态 服装配色(N1)    
- block [detect] 服装配色(N1): CHAR_01__本集为14岁杂役常态 服装配色(N1)    

### 资产问题
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 成本路由(K1):  成本路由(K1)   出图/共享/图片/定妆_道具_木牌.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP01_CLIP05.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 -0.068 vs 场景中位 -0.469）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP01_CLIP06_a1.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 -0.204 vs 场景中位 -0.469）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP01_CLIP06_a2.png：色温/调色与同场景其它镜不一致——本镜偏冷(蓝)（暖冷 -0.655 vs 场景中位 -0.469）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP01_CLIP07.png：色温/调色与同场景其它镜不一致——本镜偏冷(蓝)（暖冷 -0.682 vs 场景中位 -0.469）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP01_CLIP02_a1.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.385 vs 场景中位 0.152）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/常态, CHAR_01__, CHAR_01__本集为14岁杂役常态, CHAR_01中景, CHAR_01中景偏右）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 

### 音频问题
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「[镜头2] 众人哄笑短促混响，张老大」→「[镜头7-9] 扁担吱呀、水桶晃动、」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「[镜头7-9] 扁担吱呀、水桶晃动、」→「[镜头13] 反向水滴后静音半拍，幽」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `众杂役` 未进入 storyboard。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- warn [detect] 音乐母题(LM1):  音乐母题(LM1)   本集有配乐/多角色但缺 设定库/leitmotif_registry.json——建议像 voice_key 一样为主要角色/情绪主题登记主题动机（subject→motif），保证跨集 BGM 母题可复现不串用。 
- warn [detect] 环境声(AMB):  环境声(AMB)   本集涉 4 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁；建 LOC→ambient bed 映射。 
- warn [gate:image_preflight] 时间基准 @ 第1集: 时间基准 当前使用 timing_estimate.json（无 WAV）推进画面；这是设计态时间基准。可见口型镜只可按 production_mode_route 生成表演驱动画面或 base_video_only 基础片，不能冒充最终说话镜。
- warn [gate:image_prompt_preflight] 时间基准 @ 第1集: 时间基准 当前使用 timing_estimate.json（无 WAV）推进画面；这是设计态时间基准。可见口型镜只可按 production_mode_route 生成表演驱动画面或 base_video_only 基础片，不能冒充最终说话镜。

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): CHAR_01__本集为14岁杂役常态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_02__常态 锚点门(N3)    
- warn [detect] 锚点门(N3): CHAR_03__常态 锚点门(N3)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 糊/低质(N4):  糊/低质(N4)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「left」，实测最亮区却偏「right」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 

## 根因聚合

- block · audio:leitmotif_registry.json · 音乐母题(LM1)
  - block [gate:image] 音乐母题(LM1) @ 设定库/leitmotif_registry.json: 音乐母题(LM1) [production一致性升级:关键场景] 本集有配乐/多角色但缺 设定库/leitmotif_registry.json——建议像 voice_key 一样为主要角色/情绪主题登记主题动机（subject→motif），保证跨集 BGM 母题可复现不串用。。如确认为可接受，写入 生产数据/consistency_advisory_si
- block · character:character · 脸(G1) / 服装配色(N1) / 发型(H1) / 真值源(TRUTH) / 伏笔兑现(SP1) / 叙事状态(NS1) / image_prompt_lint
  - warn [detect] 脸(G1): CHAR_01__本集为14岁杂役常态 脸(G1)    
  - warn [detect] 脸(G1): CHAR_02__常态 脸(G1)    
  - warn [detect] 脸(G1): CHAR_01__本集为14岁杂役常态 脸(G1)    
- block · character:image_qc_第1集.json · 出图落档QC
  - block [gate:image] 出图落档QC @ 创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.json: 出图落档QC 输入首帧 image_qc 仍有 1 项硬阻断（崩脸/人体解剖N5/接缝断/降级精度近景/非法 CHAR/缺高风险人体合约）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。
- block · character:图片 · 脸(G1) / 服装配色(N1) / 发型(H1) / 锚点门(N3)
  - block [gate:image] 脸(G1) @ 出图/第1集/图片: 脸(G1) 一致性审计发现问题
  - block [gate:image] 脸(G1) @ 出图/第1集/图片: 脸(G1) 一致性审计发现问题
  - block [gate:image] 服装配色(N1) @ 出图/第1集/图片: 服装配色(N1) 一致性审计发现问题
- block · ops:candidate_selection_第1集.json · 关键镜候选
  - block [gate:image] 关键镜候选 @ 创作区/制漫剧/仙界闭关小能手/生产数据/candidate_selection_第1集.json: 关键镜候选 production 出图后缺 candidate_selection_第1集.json；关键镜必须经过 best-of-N 选优而不是单张通过。生成候选后跑 `python3 skills/n2d-image/scripts/candidate_select.py "创作区/制漫剧/仙界闭关小能手" 第1集 --apply`。
- block · ops:score_第1集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第1集.json: 缺 score JSON；验收总账无法闭环
- block · shot:shot · 场景(O2) / 色温调色(GRADE1) / 视频证据完整性(EVID) / 成本路由(K1) / multimodal_continuity / image_prompt_lint
  - warn [detect] 场景(O2):  场景(O2)    
  - warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP01_CLIP05.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 -0.068 vs 场景中位 -0.469）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
  - warn [detect] 色温调色(GRADE1):  色温调色(GRADE1)   图片/EP01_CLIP06_a1.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 -0.204 vs 场景中位 -0.469）；同场景调色横跳像换相机/换调色，人核对是否有意，否则统一白平衡/调色重出。 
- block · story:storyboard.json · 节奏密度(Rhythm) / 剧情经济性 / 语义谱系(P0)
  - warn [detect] 节奏密度(Rhythm) @ 脚本/第1集/storyboard.json:  节奏密度(Rhythm)   节奏/留存 advisory 总分偏低：62.6 
  - warn [gate:image_preflight] 剧情经济性 @ /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json: 剧情经济性 story_economy_audit 仍有 2 条压缩建议；本次不硬拦，但建议在付费生成前处理，避免解释/行进/普通反应占用视频预算。
  - warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `众杂役` 未进入 storyboard。；缺：众杂役
- warn · asset:PROP_01 · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/出图/共享/prompt/道具定妆.md ## 破损黑盆（`PROP_01`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:20>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/仙界闭关小能手/出图/共享/prompt/道具定妆.md ## 破损黑盆（`PROP_01`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:20>16
- warn · asset:asset · 结构化交互图谱(I2) / 成本路由(K1)
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
  - warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn · asset:道具定妆.md ## 扁担（`PROP_扁担`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/出图/共享/prompt/道具定妆.md ## 扁担（`PROP_扁担`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:23>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/仙界闭关小能手/出图/共享/prompt/道具定妆.md ## 扁担（`PROP_扁担`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:23>16
- warn · asset:道具定妆.md ## 旧布包（`PROP_旧布包`） · image prompt compiler
  - warn [gate:image_preflight] image prompt compiler @ /Users/lalala/learn/anime-armory/创作区/制漫剧/仙界闭关小能手/出图/共享/prompt/道具定妆.md ## 旧布包（`PROP_旧布包`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:26>16
  - warn [gate:image] image prompt compiler @ 创作区/制漫剧/仙界闭关小能手/出图/共享/prompt/道具定妆.md ## 旧布包（`PROP_旧布包`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:26>16

## 依赖传播

- nodes=41 · edges=55 · clips=7 · images=17 · videos=0
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
| 贺平生（CHAR_01） | character | ⛔ block | 🟡 | ⛔ | 🟢 |
| 张老大（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 杂役背景组（GROUP_01） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 韩老三（CHAR_03） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 秀竹峰杂役大殿（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 木牌（PROP_木牌） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 秀竹峰杂役院（LOC_02） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 旧布包（PROP_旧布包） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 扁担（PROP_扁担） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 水桶（PROP_水桶） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 秀竹峰后山浅潭（LOC_03） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 破损黑盆（PROP_01） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |

## ⛔ 贺平生（CHAR_01）
- [warn] CHAR_01__本集为14岁杂役常态 锚点门(N3)    
- [warn] CHAR_01__本集为14岁杂役常态 脸(G1)    
- [warn] CHAR_01__本集为14岁杂役常态 脸(G1)    

## 🟡 张老大（CHAR_02）
- [warn] CHAR_02__常态 锚点门(N3)    
- [warn] CHAR_02__常态 脸(G1)    
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「[镜头2] 众人哄笑短促混响，张老大」→「[镜头7-9] 

## 🟡 杂役背景组（GROUP_01）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_01__常态.png 生成事件缺 cost/provider 记账；无法计算重试
- [warn]  成本路由(K1)   出图/共享/图片/定妆_GROUP_01__常态.png 生成事件缺 cost/provider 记账；无法计算重试

## 🟡 韩老三（CHAR_03）
- [warn] CHAR_03__常态 锚点门(N3)    
- [warn]  成本路由(K1)   出图/共享/图片/定妆_CHAR_03__常态.png 生成事件缺 cost/provider 记账；无法计算重试性
- [warn] character_consistency  CHAR_03__常态 锚点门 N3：CHAR_03__常态 主参考非单张清晰正脸（非阻断） 

## 🟡 秀竹峰杂役大殿（LOC_01）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_秀竹峰杂役大殿.png 生成事件缺 cost/provider 记账；无法计算重试性价

## 🟡 木牌（PROP_木牌）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_木牌.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_木牌_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价比和
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_木牌_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价比和

## 🟡 秀竹峰杂役院（LOC_02）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_秀竹峰杂役院.png 生成事件缺 cost/provider 记账；无法计算重试性价比

## 🟡 旧布包（PROP_旧布包）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_旧布包.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_旧布包_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_旧布包_手持.png 生成事件缺 cost/provider 记账；无法计算重试性价比

## 🟡 扁担（PROP_扁担）
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「[镜头2] 众人哄笑短促混响，张老大」→「[镜头7-9] 
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「[镜头7-9] 扁担吱呀、水桶晃动、」→「[镜头13] 反
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_扁担.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切

## 🟡 水桶（PROP_水桶）
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「[镜头2] 众人哄笑短促混响，张老大」→「[镜头7-9] 
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（fast→slow）且无过渡：「[镜头7-9] 扁担吱呀、水桶晃动、」→「[镜头13] 反
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_水桶.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切

## 🟡 秀竹峰后山浅潭（LOC_03）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_秀竹峰后山浅潭.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn]  成本路由(K1)   出图/共享/图片/定妆_场景_秀竹峰后山浅潭.png 生成事件缺 cost/provider 记账；无法计算重试性价

## 🟡 破损黑盆（PROP_01）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_破损黑盆.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_破损黑盆_比例.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn]  成本路由(K1)   出图/共享/图片/定妆_道具_破损黑盆_手持.png 生成事件缺 cost/provider 记账；无法计算重试性价

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  色温调色(GRADE1)   图片/EP01_CLIP05.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 -0.068
- [warn]  色温调色(GRADE1)   图片/EP01_CLIP06_a1.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 -0.
- [warn]  色温调色(GRADE1)   图片/EP01_CLIP06_a2.png：色温/调色与同场景其它镜不一致——本镜偏冷(蓝)（暖冷 -0.6
- [warn]  色温调色(GRADE1)   图片/EP01_CLIP07.png：色温/调色与同场景其它镜不一致——本镜偏冷(蓝)（暖冷 -0.682 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
