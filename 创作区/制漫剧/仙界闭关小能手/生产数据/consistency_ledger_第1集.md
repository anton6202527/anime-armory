# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 7 · 🔴 high 0 · 🟡 medium 11

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 5 | 0 | 330 | detect, gate:compose, gate:image_preflight, gate:image, gate:video_preflight, gate:video |
| 角色 | ⛔ block | 16 | 0 | 183 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video |
| 资产 | ⛔ block | 7 | 0 | 76 | detect, gate:compose, gate:image_preflight, gate:image, gate:video_preflight |
| 镜头 | ⛔ block | 40 | 0 | 227 | detect, gate:compose, gate:image_preflight, gate:image, gate:video_preflight, gate:video |
| 音频 | ⛔ block | 1 | 0 | 12 | detect, gate:compose, gate:video |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 2 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video, compliance |
| 生产操作 | ⛔ block | 40 | 0 | 68 | detect, gate:compose, gate:image_preflight, gate:image, gate:video, score, audio_space_consistency |

### 剧情问题
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜1 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜2 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜4 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜5 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜6 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜7 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜8 prompt 未见状态锁。 
- warn [detect] 状态百科(P1):  状态百科(P1)   贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜9 prompt 未见状态锁。 

### 角色问题
- warn [detect] 脸(G1): 贺平生 脸(G1)    
- warn [detect] 脸(G1): 贺平生 脸(G1)    
- warn [detect] 脸(G1): 贺平生 脸(G1)    
- block [detect] 脸(G1): 贺平生 脸(G1)    
- warn [detect] 脸(G1): 贺平生 脸(G1)    
- block [detect] 脸(G1): 贺平生 脸(G1)    
- warn [detect] 脸(G1): 贺平生 脸(G1)    
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景

### 资产问题
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 
- warn [detect] 交互接触(I1):  交互接触(I1)   物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 景深一致(DOF1):  景深一致(DOF1)   图片/Clip02_first.png：景深档与同场景其它镜不一致——本镜偏浅景深(背景偏糊)（景深比 0.535 vs 场景中位 1.004）；同场景深焦↔浅景深横跳像换相机，人核对是否有意，否则统一景深档重出。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_HAN_LAOSAN, CHAR_HAN_LAOSAN__, CHAR_HE_PINGSHENG, CHAR_HE_PINGSHENG__, CHAR_ZHANG_LAODA, CHAR_ZHANG_LAODA__）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   video_eval_manifest 已建立，但这些风险 sidecar 尚未写回：causal_event:生产数据/causal_event_graph_第1集.json；dialogue_av:生产数据/dialogue_av_alignment_第1集.json；physical_event:生产数据/physic
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   这些视频证据 sidecar 存在但缺明细/判题结果：camera:生产数据/camera_trajectory_probe_第1集.json；motion:生产数据/motion_quality_第1集.json；subject_video:生产数据/subject_video_consistency_第1集.json 
- warn [detect] 成片时间线探针(FT1):  成片时间线探针(FT1)   成片已存在但缺 final_timeline_probe；无法直接量片确认剪点亮度/色温跳、静音缝、响度突变。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第1集/成片_第1集_zh.mp4 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=8904400e3e14644a，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   合成/第1集/成片_第1集_zh.mp4 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 音乐衔接(BGM):  音乐衔接(BGM)   配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身世快闪用短促弦乐切片」；调性/速度whiplash，加渐变过渡或确认是卡点切。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 
- warn [detect] 多人对话音画(DAV):  多人对话音画(DAV)   检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 
- warn [detect] 成片统一(C1):  成片统一(C1)   storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。 
- warn [detect] 成片统一(C1):  成片统一(C1)   缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   合成/第1集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=a899b7e94c5d0cdc，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   合成/第1集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_ver

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:compose] 合规前置 @ 创作区/制漫剧/仙界闭关小能手/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 锚点门(N3): 张老大 锚点门(N3)    
- warn [detect] 锚点门(N3): 贺平生 锚点门(N3)    
- warn [detect] 锚点门(N3): 韩老三 锚点门(N3)    
- block [detect] 风格(S1):  风格(S1)    
- block [detect] 风格(S1):  风格(S1)    
- block [detect] 风格(S1):  风格(S1)    
- warn [detect] 风格(S1):  风格(S1)    
- block [detect] 风格(S1):  风格(S1)    

## 根因聚合

- block · asset:storyboard.json clip#14→clip#15 · 人物在场链
  - block [gate:compose] 人物在场链 @ 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#14→clip#15: 人物在场链 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CHAR_HAN_LAOSAN。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
- block · asset:storyboard.json clip#1→clip#2 · 人物在场链
  - block [gate:compose] 人物在场链 @ 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#1→clip#2: 人物在场链 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CROWD_ZAYI。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
- block · asset:storyboard.json clip#20→clip#21 · 人物在场链
  - block [gate:compose] 人物在场链 @ 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#20→clip#21: 人物在场链 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：PROP_HEI_TAO_PEN。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
- block · asset:storyboard.json clip#23→clip#24 · 人物在场链
  - block [gate:compose] 人物在场链 @ 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#23→clip#24: 人物在场链 连续接缝里实体在下一 Clip 凭空出现但未解释入画/进场/现身：PROP_BIAN_DAN。请在 continuity.entry_exit 写入画动作，或用空镜/换场/时间跳跃隔开。
- block · asset:storyboard.json clip#24→clip#25 · 人物在场链
  - block [gate:compose] 人物在场链 @ 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#24→clip#25: 人物在场链 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CHAR_HE_PINGSHENG、PROP_BIAN_DAN、PROP_SHUI_TONG。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
- block · asset:storyboard.json clip#5→clip#6 · 人物在场链
  - block [gate:compose] 人物在场链 @ 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#5→clip#6: 人物在场链 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CHAR_ZHANG_LAODA。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
  - block [gate:compose] 人物在场链 @ 创作区/制漫剧/仙界闭关小能手/脚本/第1集/storyboard.json clip#5→clip#6: 人物在场链 连续接缝里实体在下一 Clip 凭空出现但未解释入画/进场/现身：CROWD_ZAYI。请在 continuity.entry_exit 写入画动作，或用空镜/换场/时间跳跃隔开。
- block · audio:consistency_findings_第1集.json · 证据等级
  - block [gate:compose] 证据等级 @ 创作区/制漫剧/仙界闭关小能手/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。交付边界不放行——在装好进阶依赖的环境复跑，或显式 N2D_ALLOW_DEGRAD
  - warn [gate:video] 证据等级 @ 创作区/制漫剧/仙界闭关小能手/生产数据/consistency_findings_第1集.json: 证据等级 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主体一致 / SyncNet 口型词级 进阶依赖未装，未数值化验证）；本集最弱证据级=structured。（出图/出视频阶段先 WARN，交付边界 compose/review 将 BLOC
- block · character:character · 脸(G1) / 无脸崩坏(G1b) / 服装配色(N1) / 发型(H1) / 表情连续(EXP1) / 真值源(TRUTH) / 强配方Schema(RCP2) / 台词语域(D1) / 叙事状态(NS1) / image_prompt_lint
  - warn [detect] 脸(G1): 贺平生 脸(G1)    
  - warn [detect] 脸(G1): 贺平生 脸(G1)    
  - warn [detect] 脸(G1): 贺平生 脸(G1)    
- block · character:image_qc_第1集.json · 出图落档QC
  - block [gate:video_preflight] 出图落档QC @ 创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.json: 出图落档QC 输入首帧 image_qc 仍有 49 项硬阻断（崩脸/接缝断/降级精度近景/非法 CHAR）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。
- block · character:vlm_canonical_第1集.json · fidelity-gate
  - block [gate:compose] fidelity-gate @ 创作区/制漫剧/仙界闭关小能手/生产数据/vlm_canonical_第1集.json: fidelity-gate 终验须 fidelity-gate 激活——跑 vlm_verify --write 落 canonical 通过表。缺 VLM 语义判定时，脸(G1)的机械通过不构成角色设定完整验证。（无 VLM 后端时装依赖或显式 N2D_ALLOW_DEGRADED_QC=1 自负其责。）
- block · character:图片 · 脸(G1) / 服装配色(N1) / 发型(H1) / 锚点门(N3) / 无脸崩坏(G1b)
  - block [gate:compose] 脸(G1) @ 出图/第1集/图片: 脸(G1) 一致性审计发现问题
  - block [gate:compose] 脸(G1) @ 出图/第1集/图片: 脸(G1) 一致性审计发现问题
  - block [gate:compose] 服装配色(N1) @ 出图/第1集/图片: 服装配色(N1) 一致性审计发现问题
- block · ops:consistency_calibration.jsonl · 人审校准集(CAL)
  - block [gate:compose] 人审校准集(CAL) @ 生产数据/consistency_calibration.jsonl: 人审校准集(CAL) [production一致性升级:交付边界] 检测到人审签收/覆盖记录，但缺 consistency_calibration.jsonl；误报/漏报没有进入全局校准集。。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=f6

## 依赖传播

- nodes=188 · edges=442 · clips=25 · images=74 · videos=25
- graph: `创作区/制漫剧/仙界闭关小能手/生产数据/consistency_dependency_graph_第1集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=1
- expression_state_consistency: status=pass · block=0 · warn=0

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 贺平生（CHAR_HE_PINGSHENG） | character | ⛔ block | 🟡 | ⛔ | 🟢 |
| 张老大（CHAR_ZHANG_LAODA） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 韩老三（CHAR_HAN_LAOSAN） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 江剑（CHAR_JIANG_JIAN） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 太虚门长老（CHAR_TAIXUMEN_ZHANGLAO） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 贺三杰（CHAR_HE_SANJIE） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 群杂役（CROWD_ZAYI） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 黑陶破盆（PROP_HEI_TAO_PEN） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 水桶与扁担（PROP_SHUI_TONG） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 两口巨大水缸（PROP_WATER_JARS） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 太虚门远景修士剪影（CROWD_TAIXU_CULTIVATOR） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 贺平生杂役小屋（LOC_ZAYI_HUT） | scene | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 碧绿灵水（PROP_GREEN_WATER） | prop | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 盆底微绿亮点（VFX_BASIN_MICROGLOW） | vfx | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 后山挑水路（LOC_HOUSHAN_WATER_PATH） | scene | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 杂役饭棚（LOC_ZAYI_FOOD_YARD） | scene | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 杂役饭碗（PROP_FOOD_BOWL） | prop | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 杂役院水缸区（LOC_ZAYI_WATER_JARS） | scene | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 灵米布袋（PROP_SPIRIT_RICE_BAG） | prop | 🟢 ok | 🟢 | 🟢 | 🟢 |
| 灰败灵米（PROP_GRAY_RICE） | prop | 🟢 ok | 🟢 | 🟢 | 🟢 |

## ⛔ 贺平生（CHAR_HE_PINGSHENG）
- [warn] 贺平生 锚点门(N3)    
- [warn] 贺平生 脸(G1)    
- [warn] 贺平生 脸(G1)    

## 🟡 张老大（CHAR_ZHANG_LAODA）
- [warn] 张老大 锚点门(N3)    
- [warn]  表情连续(EXP1)   Clip_10：角色 CHAR_ZHANG_LAODA 相邻镜情绪硬跳（喜→悲）——确认有节拍/事件依据，否则表
- [warn]  表情连续(EXP1)   Clip_10：角色 CHAR_ZHANG_LAODA__ 相邻镜情绪硬跳（喜→悲）——确认有节拍/事件依据，否

## 🟡 韩老三（CHAR_HAN_LAOSAN）
- [warn] 韩老三 锚点门(N3)    
- [warn]  实体记忆(EMB)   本集有重复/核心实体（CHAR_HAN_LAOSAN, CHAR_HAN_LAOSAN__, CHAR_HE_PI
- [warn]  成本路由(K1)   出图/共享/图片/定妆_韩老三.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成

## 🟡 江剑（CHAR_JIANG_JIAN）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_江剑_背影_三视图.png 生成事件缺 cost/provider 记账；无法计算重试性价比
- [warn] image_prompt_lint  None 镜头 12（`EP01_CLIP12` · 江剑背影送往秀竹峰 · multi_charac

## 🟡 太虚门长老（CHAR_TAIXUMEN_ZHANGLAO）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_太虚门长老_回忆背影_三视图.png 生成事件缺 cost/provider 记账；无法计算

## 🟡 贺三杰（CHAR_HE_SANJIE）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_贺三杰_回忆影_三视图.png 生成事件缺 cost/provider 记账；无法计算重试性

## 🟡 群杂役（CROWD_ZAYI）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_群杂役_虚化_三视图.png 生成事件缺 cost/provider 记账；无法计算重试性价
- [warn] image_prompt_lint  None 镜头 6（`EP01_CLIP06` · 群杂役笑影压近 · ensemble_blocki

## 🟡 黑陶破盆（PROP_HEI_TAO_PEN）
- [warn]  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- [warn]  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- [warn]  无脸崩坏(G1b)    黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景

## 🟡 水桶与扁担（PROP_SHUI_TONG）
- [warn]  成本路由(K1)   出图/共享/图片/定妆_水桶与扁担.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [block]  风格(S1)    
- [block]  风格(S1)    
- [block]  风格(S1)    
- [warn]  风格(S1)    
- [block]  风格(S1)    
- [block]  风格(S1)    
- [warn]  风格(S1)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
