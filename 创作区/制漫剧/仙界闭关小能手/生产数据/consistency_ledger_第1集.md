# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 2 · 🔴 high 4 · 🟡 medium 17

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 5 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 1 | 0 | 52 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 14 | detect, gate:image_preflight, gate:image |
| 镜头 | 🟡 warn | 0 | 0 | 59 | detect, gate:image_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 5 | detect |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 1 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 2 | 0 | 61 | detect, gate:image_preflight, gate:image, score |

### 剧情问题
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 6 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 7 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白
- warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白
- warn [gate:image] 语义谱系(P0) @ 脚本/第1集/storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。

### 角色问题
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn [detect] 多视角身份包(MVIEW):  多视角身份包(MVIEW)   核心/长线角色 CHAR_HE_PINGSHENG 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。 
- warn [detect] 台词语域(D1):  台词语域(D1)   缺 dialogue_register/语域表；目前只能查称谓 + 文白横跳启发式，无法约束角色正式度、句长上限和禁用词。建议补 formality/sentence_len_max/forbidden/口癖。 
- warn [detect] 叙事状态(NS1):  叙事状态(NS1)   本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的 narrative_state_audit.py --write 建账，填 character/keyword/known_from_ep。 
- warn [detect] character_consistency @ 图片/Clip02_挑水命令.png: character_consistency  图片/Clip02_挑水命令.png 疑似漏分类角色镜：图片/Clip02_挑水命令.png 检出人脸但不在出图 prompt 角色镜清单（character_shots）→ 未纳入定妆覆盖比对。确认是否角色镜：是则回 n2d-image 在 prompt 标注该镜角色身份后重跑 image_qc；否（路人/群像
- warn [detect] character_consistency @ 太虚门长老_回忆背影: character_consistency  太虚门长老_回忆背影 锚点门 N3：太虚门长老_回忆背影 主参考非单张清晰正脸（非阻断） 

### 资产问题
- warn [detect] 天气时辰(W1):  天气时辰(W1)   天气 fog→overcast 同场景内突变且无时间转场 cue（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'等转场，或登记 intentional_discontinuity） 
- warn [detect] 天气时辰(W1):  天气时辰(W1)   天气 overcast→fog 同场景内突变且无时间转场 cue（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'等转场，或登记 intentional_discontinuity） 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 

### 镜头问题
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG/常态, CHAR_HE_PINGSHENG/肩颈红痕, CHAR_ZHANG_LAODA, CHAR_ZHANG_LAODA/常态, LOC_HOUSHAN_QIANTAN）但缺 entity_memory_bank；后续镜头无法按已验收
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip01_黑殿审问.png DINO/CLIP cosine=0.33 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip01_黑殿审问_end.png DINO/CLIP cosine=0.35 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip01_黑殿审问_mid.png DINO/CLIP cosine=0.43 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip02_挑水命令.png DINO/CLIP cosine=0.41 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip02_挑水命令_end.png DINO/CLIP cosine=0.28 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip02_挑水命令_mid.png DINO/CLIP cosine=0.50 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身世快闪用短促弦乐切片」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 
- warn [detect] 环境声(AMB):  环境声(AMB)   本集涉 5 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁；建 LOC→ambient bed 映射。 

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
- warn [detect] 锚点门(N3): 韩老三 锚点门(N3)    

## 根因聚合

- block · character:consistency_findings_第1集.json · 一致性总审
  - block [gate:image] 一致性总审 @ 创作区/制漫剧/仙界闭关小能手/生产数据/consistency_findings_第1集.json: 一致性总审 一致性审计精度为 degraded（insightface 等不可用，脸/像素一致性未真正验证）；出图后闸门不放行——请在 full 环境复跑，或显式 N2D_ALLOW_DEGRADED_QC=1 放行并自负其责。
- block · ops:consistency_findings_第1集.json · 一致性总审
  - warn [gate:image] 一致性总审 @ 创作区/制漫剧/仙界闭关小能手/生产数据/consistency_findings_第1集.json: 一致性总审 另有 66 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当作已全部处理。
  - block [gate:image] 一致性总审 @ 创作区/制漫剧/仙界闭关小能手/生产数据/consistency_findings_第1集.json: 一致性总审 consistency_audit.py 退出码 1，但未导出 block finding；stderr=
- block · ops:score_第1集.json · 自动审片总分
  - block [score] 自动审片总分 @ 生产数据/score_第1集.json: 缺 score JSON；验收总账无法闭环
- warn · asset:asset · 天气时辰(W1) / 交互接触(I1) / 结构化交互图谱(I2)
  - warn [detect] 天气时辰(W1):  天气时辰(W1)   天气 fog→overcast 同场景内突变且无时间转场 cue（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'等转场，或登记 intentional_discontinuity） 
  - warn [detect] 天气时辰(W1):  天气时辰(W1)   天气 overcast→fog 同场景内突变且无时间转场 cue（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'等转场，或登记 intentional_discontinuity） 
  - warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn · audio:audio · 配音情绪弧(VEA) / 音乐衔接(BGM) / 语义谱系(P0) / 声音空间(ASP) / 环境声(AMB)
  - warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
  - warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身世快闪用短促弦乐切片」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
  - warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `旁白` 未进入 storyboard。 
- warn · character:Clip02_挑水命令.png · character_consistency
  - warn [detect] character_consistency @ 图片/Clip02_挑水命令.png: character_consistency  图片/Clip02_挑水命令.png 疑似漏分类角色镜：图片/Clip02_挑水命令.png 检出人脸但不在出图 prompt 角色镜清单（character_shots）→ 未纳入定妆覆盖比对。确认是否角色镜：是则回 n2d-image 在 prompt 标注该镜角色身份后重跑 image_qc；否（路人/群像
  - warn [gate:image] character_consistency @ 图片/Clip02_挑水命令.png: character_consistency 疑似漏分类角色镜：图片/Clip02_挑水命令.png 检出人脸但不在出图 prompt 角色镜清单（character_shots）→ 未纳入定妆覆盖比对。确认是否角色镜：是则回 n2d-image 在 prompt 标注该镜角色身份后重跑 image_qc；否（路人/群像背景脸）可忽略。
- warn · character:_设置.md · 生图后端适配 / 风格化脸机检
  - warn [gate:image_preflight] 生图后端适配 @ /Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/_设置.md: 生图后端适配 统一标准已按「Codex CLI」自动加载弥补措施：加载 reference_group：正/45度/侧/半身/脸锚/表情库按镜头风险选入参；近景/大表情/暗光镜强制同源脸锚或表情参考，并用 full image_qc 回验；长线核心角反复漂移时升档到原生主体或 LoRA，不降低角色一致性标准。这些是后端差异的执行补偿，不降低 n2d 的出图标
  - warn [gate:image_preflight] 生图后端适配 @ /Users/wesley/learn/anime-arsenal/创作区/制漫剧/仙界闭关小能手/_设置.md: 生图后端适配 适配层评分建议升档：当前「Codex CLI」score=30，推荐「Seedream Universal Reference (访问入口 Seedream 官方 API)」score=57。理由：推荐后端能力=persistent_subject,multi_reference,high_fidelity_reference；若确认切换，先统
  - warn [gate:image_prompt_preflight] 风格化脸机检 @ 创作区/制漫剧/仙界闭关小能手/_设置.md: 风格化脸机检 基础视觉风格「国漫写实」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N2D_STYLEID_MODEL。未配置前，角色脸一致性 KPI 按降级档处理，近景结果需提高人审权重。
- warn · character:character · 无脸崩坏(G1b) / 真值源(TRUTH) / 多视角身份包(MVIEW) / 台词语域(D1) / 叙事状态(NS1) / image_prompt_lint
  - warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
  - warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
  - warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。 
- warn · character:identity_eval_pack.json · 多视角身份包(MVIEW)
  - warn [gate:image] 多视角身份包(MVIEW) @ 设定库/identity_eval_pack.json: 多视角身份包(MVIEW) 核心/长线角色 CHAR_HE_PINGSHENG 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧脸/背影/表情桶的固定身份哨兵。
- warn · character:太虚门长老_回忆背影 · character_consistency
  - warn [detect] character_consistency @ 太虚门长老_回忆背影: character_consistency  太虚门长老_回忆背影 锚点门 N3：太虚门长老_回忆背影 主参考非单张清晰正脸（非阻断） 
  - warn [gate:image] character_consistency @ 太虚门长老_回忆背影: character_consistency 锚点门 N3：太虚门长老_回忆背影 主参考非单张清晰正脸（非阻断）
- warn · character:张老大 · character_consistency
  - warn [detect] character_consistency @ 张老大: character_consistency  张老大 锚点门 N3：张老大 主参考非单张清晰正脸（非阻断） 
  - warn [gate:image] character_consistency @ 张老大: character_consistency 锚点门 N3：张老大 主参考非单张清晰正脸（非阻断）
- warn · character:张老大（CHAR_ZHANG_LAODA） · 脸漂预案
  - warn [gate:image_preflight] 脸漂预案 @ 张老大（CHAR_ZHANG_LAODA）: 脸漂预案 本集脸漂风险 high（分68.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。
  - warn [gate:image] 脸漂预案 @ 张老大（CHAR_ZHANG_LAODA）: 脸漂预案 本集脸漂风险 high（分68.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场景图并拼身份锁定句；不要只靠文字外貌描述。

## 依赖传播

- nodes=48 · edges=59 · clips=7 · images=20 · videos=0
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
| 黑陶破盆（PROP_HEI_TAO_PEN） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 水桶与扁担（PROP_SHUI_TONG） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 铁碗/钥匙铁锁（PROP_TIE_WAN） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 旧钥匙与生锈铁锁（PROP_KEY_LOCK） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 太虚门远景修士剪影（CROWD_TAIXU_CULTIVATOR） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |

## 🔴 贺平生（CHAR_HE_PINGSHENG）
- [warn] 贺平生 锚点门(N3)    
- [warn] 贺平生_幼年 锚点门(N3)    
- [warn]  无脸崩坏(G1b)    贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景

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

## 🟡 黑陶破盆（PROP_HEI_TAO_PEN）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_黑陶破盆.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换

## 🟡 水桶与扁担（PROP_SHUI_TONG）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_水桶与扁担.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切

## 🟡 铁碗/钥匙铁锁（PROP_TIE_WAN）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_铁碗钥匙铁锁.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型

## 🟡 旧钥匙与生锈铁锁（PROP_KEY_LOCK）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_旧钥匙与生锈铁锁.png 生成事件缺 cost/provider 记账；无法计算重试性价比和

## 未归属到具体角色/资产的一致性问题
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  天气时辰(W1)   主光方位 left→right 硬翻转（疑光位跳·人比对相邻镜） 
- [warn]  天气时辰(W1)   天气 fog→overcast 同场景内突变且无时间转场 cue（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'
- [warn]  天气时辰(W1)   天气 overcast→fog 同场景内突变且无时间转场 cue（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'
- [warn]  天气时辰(W1)   主光方位 left→right 硬翻转（疑光位跳·人比对相邻镜） 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
