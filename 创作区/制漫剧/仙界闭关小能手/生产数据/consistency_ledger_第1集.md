# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 5 · 🔴 high 3 · 🟡 medium 13

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 3 | 0 | 6 | detect |
| 角色 | 🟡 warn | 0 | 0 | 5 | detect, gate:image_prompt_preflight |
| 资产 | ⛔ block | 1 | 0 | 13 | detect |
| 镜头 | 🟡 warn | 0 | 0 | 1 | detect |
| 音频 | 🟡 warn | 0 | 0 | 6 | detect |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 1 | detect, gate:image_prompt_preflight, compliance |
| 生产操作 | ⛔ block | 1 | 0 | 2 | detect, score |

### 剧情问题
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜1 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜3 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜6 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜7 prompt 未见状态锁。 
- block [detect] 状态百科(P1):  状态百科(P1)   贺平生 的状态 `肩颈出现挑水红痕，动作疲惫` 在镜19前提前泄露。 
- block [detect] 状态百科(P1):  状态百科(P1)   贺平生 的状态 `肩颈出现挑水红痕，动作疲惫` 在镜19前提前泄露。 
- block [detect] 状态百科(P1):  状态百科(P1)   黑陶破盆 的状态 `旧黑陶破盆，弱月光反射` 在镜22前提前泄露。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 6 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06），疑节奏塌·掉留存 

### 角色问题
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_HE_PINGSHENG 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
- warn [detect] 台词语域(D1):  台词语域(D1)   缺 dialogue_register/语域表；目前只能查称谓 + 文白横跳启发式，无法约束角色正式度、句长上限和禁用词。建议补 formality/sentence_len_max/forbidden/口癖。 
- warn [detect] 叙事状态(NS1):  叙事状态(NS1)   本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。 
- warn [gate:image_prompt_preflight] 风格化脸机检 @ 创作区/制漫剧/仙界闭关小能手/_设置.md: 风格化脸机检 基础视觉风格「国漫写实」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N2D_STYLEID_MODEL。未配置前，角色脸一致性 KPI 按降级档处理，近景结果需提高人审权重。

### 资产问题
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 

### 镜头问题
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG/常态, CHAR_HE_PINGSHENG/肩颈红痕, CHAR_ZHANG_LAODA, CHAR_ZHANG_LAODA/常态, LOC_HOUSHAN_QIANTAN）但缺 entity_memory_bank；后续镜头无法按已验收

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身世快闪用短促弦乐切片」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 
- warn [detect] 音乐母题(LM1):  音乐母题(LM1)   本集有配乐/多角色但缺 设定库/leitmotif_registry.json——建议像 voice_key 一样为主要角色/情绪主题登记主题动机（subject→motif），保证跨集 BGM 母题可复现不串用。 
- warn [detect] 环境声(AMB):  环境声(AMB)   本集涉 5 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁；建 LOC→ambient bed 映射。 

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 

### 生产操作问题
- warn [detect] 人审校准集(CAL):  人审校准集(CAL)   检测到人审签收/覆盖记录，但缺 consistency_calibration.jsonl；误报/漏报没有进入全局校准集。 
- warn [detect] 一致性探针包(PROBE):  一致性探针包(PROBE)   项目已有多集或媒体产物，但缺 consistency_probe_pack；后端/模板升级没有固定哨兵小样。 
- block [score] 自动审片总分 @ 生产数据/score_第1集.json: 缺 score JSON；验收总账无法闭环

## 根因聚合

- block · asset:asset · 交互接触(I1) / 结构化交互图谱(I2)
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- block · ops:score_第1集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第1集.json: 缺 score JSON；验收总账无法闭环
- block · story:story · 状态百科(P1) / 节奏密度(Rhythm) / 状态转场视频证据(ST1)
  - warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜1 prompt 未见状态锁。 
  - warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜3 prompt 未见状态锁。 
  - warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜6 prompt 未见状态锁。 
- warn · audio:audio · 配音情绪弧(VEA) / 音乐衔接(BGM) / 语义谱系(P0) / 声音空间(ASP) / 音乐母题(LM1) / 环境声(AMB)
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身世快闪用短促弦乐切片」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
  - warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- warn · character:_设置.md · 风格化脸机检
  - warn [gate:image_prompt_preflight] 风格化脸机检 @ 创作区/制漫剧/仙界闭关小能手/_设置.md: 风格化脸机检 基础视觉风格「国漫写实」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N2D_STYLEID_MODEL。未配置前，角色脸一致性 KPI 按降级档处理，近景结果需提高人审权重。
- warn · character:character · 真值源(TRUTH) / 多视角身份包(MVIEW) / 台词语域(D1) / 叙事状态(NS1)
  - warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
  - warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_HE_PINGSHENG 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
  - warn [detect] 台词语域(D1):  台词语域(D1)   缺 dialogue_register/语域表；目前只能查称谓 + 文白横跳启发式，无法约束角色正式度、句长上限和禁用词。建议补 formality/sentence_len_max/forbidden/口癖。 
- warn · compliance:compliance · 世界一致性(WCS)
  - warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn · ops:ops · 人审校准集(CAL) / 一致性探针包(PROBE)
  - warn [detect] 人审校准集(CAL):  人审校准集(CAL)   检测到人审签收/覆盖记录，但缺 consistency_calibration.jsonl；误报/漏报没有进入全局校准集。 
  - warn [detect] 一致性探针包(PROBE):  一致性探针包(PROBE)   项目已有多集或媒体产物，但缺 consistency_probe_pack；后端/模板升级没有固定哨兵小样。 
- warn · shot:shot · 实体记忆(EMB)
  - warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG/常态, CHAR_HE_PINGSHENG/肩颈红痕, CHAR_ZHANG_LAODA, CHAR_ZHANG_LAODA/常态, LOC_HOUSHAN_QIANTAN）但缺 entity_memory_bank；后续镜头无法按已验收
- warn · subtitle:subtitle · 系列包装(PKG)
  - warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

## 依赖传播

- nodes=27 · edges=38 · clips=7 · images=0 · videos=0
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
| 贺平生（CHAR_HE_PINGSHENG） | character | ⛔ block | 🔴 | ⛔ | 🟢 |
| 黑陶破盆（PROP_HEI_TAO_PEN） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 张老大（CHAR_ZHANG_LAODA） | character | 🔴 high | 🔴 | 🟡 | 🟢 |
| 群杂役（CROWD_ZAYI） | character | 🔴 high | 🔴 | 🟢 | 🟢 |
| 后山山泉浅潭（LOC_HOUSHAN_QIANTAN） | location | 🔴 high | 🔴 | 🟡 | 🟢 |
| 韩老三（CHAR_HAN_LAOSAN） | character | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 江剑（CHAR_JIANG_JIAN） | character | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 秀竹峰杂役大殿（LOC_ZAYI_DADIAN） | location | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 秀竹峰杂役院与空房（LOC_ZAYI_YUAN） | location | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 太虚门外门旧院/秀竹峰山门回忆场（LOC_WAIMEN_JIUYUAN） | location | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 水桶与扁担（PROP_SHUI_TONG） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 铁碗/钥匙铁锁（PROP_TIE_WAN） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 旧钥匙与生锈铁锁（PROP_KEY_LOCK） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 太虚门长老（CHAR_TAIXUMEN_ZHANGLAO） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 贺三杰（CHAR_HE_SANJIE） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 太虚门远景修士剪影（CROWD_TAIXU_CULTIVATOR） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 贺平生（CHAR_HE_PINGSHENG）
- [warn]  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜1 prompt 未见状态锁。 
- [warn]  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜3 prompt 未见状态锁。 
- [warn]  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜6 prompt 未见状态锁。 

## ⛔ 黑陶破盆（PROP_HEI_TAO_PEN）
- [block]  状态百科(P1)   黑陶破盆 的状态 `旧黑陶破盆，弱月光反射` 在镜22前提前泄露。 

## 🔴 张老大（CHAR_ZHANG_LAODA）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG/常态, CHAR_

## 🔴 后山山泉浅潭（LOC_HOUSHAN_QIANTAN）
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG/常态, CHAR_

## 未归属到具体角色/资产的一致性问题
- [warn]  配音情绪弧(VEA)   镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身
- [warn]  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- [warn]  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响
- [warn]  节奏密度(Rhythm)   连续 6 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CL
- [warn]  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / s
- [warn]  状态转场视频证据(ST1)   检测到 7 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 b
- [warn]  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
