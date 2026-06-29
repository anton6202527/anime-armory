# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 8 · 🔴 high 3 · 🟡 medium 12

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 4 | detect, gate:image_preflight, gate:image |
| 角色 | ⛔ block | 13 | 0 | 77 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image |
| 资产 | 🟡 warn | 0 | 0 | 14 | detect, gate:image_preflight, gate:image |
| 镜头 | ⛔ block | 15 | 0 | 10 | detect, gate:image_preflight, gate:image |
| 音频 | 🟡 warn | 0 | 0 | 5 | detect |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 1 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, compliance |
| 生产操作 | ⛔ block | 3 | 0 | 58 | detect, gate:image_preflight, gate:image, score |

### 剧情问题
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 6 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06），疑节奏塌·掉留存 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 7 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [gate:image_preflight] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白
- warn [gate:image] 语义谱系(P0) @ storyboard.json: 语义谱系(P0) 配音角色 `旁白` 未进入 storyboard。；缺：旁白

### 角色问题
- block [detect] 脸(G1): 贺平生 脸(G1)    
- warn [detect] 脸(G1): 贺平生 脸(G1)    
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- block [detect] 服装配色(N1): 贺平生 服装配色(N1)    
- warn [detect] 服装配色(N1): 贺平生 服装配色(N1)    
- block [detect] 服装配色(N1): 贺平生 服装配色(N1)    
- warn [detect] 发型(H1): 贺平生 发型(H1)    

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
- warn [detect] style_consistency: style_consistency  None 景别像素兜底：镜2 声明 CU(特写) 但 出图/第1集/图片/Clip02_挑水命令.png 实测脸占比 2.9% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 
- warn [detect] style_consistency: style_consistency  None 景别像素兜底：镜7 声明 ECU(特写) 但 出图/第1集/图片/Clip07_盆底微光.png 实测脸占比 0.4% < 5%——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。 
- warn [detect] style_consistency: style_consistency  None 风格归属无法机检：style_contract 未登记风格锚（style_anchor）。请在定妆阶段出 1–2 张「国漫写实」风格锚图、登记进 style_contract.style_anchor，后续每集出图帧才能对锚做风格归属佐证。当前降级为人判：逐图核对是否踩 风格禁忌：低幼Q版、欧美卡通脸、照片级毛
- block [detect] multimodal_continuity @ 图片/Clip04_两缸水和空屋.png: multimodal_continuity  图片/Clip04_两缸水和空屋.png 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸水和空屋 的 `PROP_KEY_LOCK`（旧钥匙与生锈铁锁）登记了 must_not_have=现代防盗锁、金色宝物、符文刻字、巨大链锁、多套重复；scale=少年单手可握，锁体小，适合低矮旧房木门。。文字约束不能证
- block [detect] multimodal_continuity @ 图片/Clip04_两缸水和空屋.png: multimodal_continuity  图片/Clip04_两缸水和空屋.png 高风险道具禁形/尺寸未逐图确认：Clip 04 两缸水和空屋 的 `PROP_TIE_WAN`（铁碗/钥匙铁锁）登记了 must_not_have=现代锁具、金色宝物、瓷碗、异物化、多套重复；scale=铁碗可手持，钥匙铁锁为小型杂役房门物件。。文字约束不能证明既有 PN
- block [detect] multimodal_continuity @ 图片/Clip05_夜挑五趟.png: multimodal_continuity  图片/Clip05_夜挑五趟.png 高风险道具禁形/尺寸未逐图确认：Clip 05 夜挑五趟 的 `PROP_SHUI_TONG`（水桶与扁担）登记了 must_not_have=现代塑料桶、金属水桶、单只桶漂移、华丽异物化；scale=少年挑水工具，桶身到少年膝上附近。。文字约束不能证明既有 PNG 没长出禁

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

- block · character:Clip04_两缸水和空屋.png · character_consistency / outfit_consistency
  - block [detect] character_consistency @ 图片/Clip04_两缸水和空屋.png: character_consistency  图片/Clip04_两缸水和空屋.png 崩脸 G1 block：图片/Clip04_两缸水和空屋.png（脸/身份漂移机检） 
  - warn [gate:image] character_consistency @ 图片/Clip04_两缸水和空屋.png: character_consistency 崩脸 G1 warn：图片/Clip04_两缸水和空屋.png（脸/身份漂移机检）
  - block [gate:image] character_consistency @ 图片/Clip04_两缸水和空屋.png: character_consistency 角色脸定妆比对覆盖缺口：Clip 04 两缸水和空屋 图片/Clip04_两缸水和空屋.png；脸部比对为 warn，疑似身份漂移。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip04_两缸水和空屋_end.png · character_consistency / outfit_consistency
  - warn [detect] character_consistency @ 图片/Clip04_两缸水和空屋_end.png: character_consistency  图片/Clip04_两缸水和空屋_end.png 崩脸 G1 warn：图片/Clip04_两缸水和空屋_end.png（脸/身份漂移机检） 
  - block [detect] character_consistency @ 图片/Clip04_两缸水和空屋_end.png: character_consistency  图片/Clip04_两缸水和空屋_end.png 角色脸定妆比对覆盖缺口：Clip 04 两缸水和空屋 图片/Clip04_两缸水和空屋_end.png；脸部比对为 warn，疑似身份漂移。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。 
  - warn [detect] outfit_consistency @ 图片/Clip04_两缸水和空屋_end.png: outfit_consistency  图片/Clip04_两缸水和空屋_end.png 服装 N1 初筛：图片/Clip04_两缸水和空屋_end.png（调色板离群，非阻断） 
- block · character:Clip04_两缸水和空屋_mid.png · outfit_consistency / character_consistency
  - warn [detect] outfit_consistency @ 图片/Clip04_两缸水和空屋_mid.png: outfit_consistency  图片/Clip04_两缸水和空屋_mid.png 服装 N1 初筛：图片/Clip04_两缸水和空屋_mid.png（调色板离群，非阻断） 
  - block [gate:image] character_consistency @ 图片/Clip04_两缸水和空屋_mid.png: character_consistency 崩脸 G1 block：图片/Clip04_两缸水和空屋_mid.png（脸/身份漂移机检）
  - warn [gate:image] outfit_consistency @ 图片/Clip04_两缸水和空屋_mid.png: outfit_consistency 服装 N1 初筛：图片/Clip04_两缸水和空屋_mid.png（调色板离群，非阻断）
- block · character:character · 脸(G1) / 无脸崩坏(G1b) / 服装配色(N1) / 发型(H1) / 真值源(TRUTH) / 多视角身份包(MVIEW) / 台词语域(D1) / 叙事状态(NS1) / image_prompt_lint
  - block [detect] 脸(G1): 贺平生 脸(G1)    
  - warn [detect] 脸(G1): 贺平生 脸(G1)    
  - warn [detect] 无脸崩坏(G1b):  无脸崩坏(G1b)    贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景
- block · character:image_qc_第1集.json · 出图落档QC
  - block [gate:image] 出图落档QC @ 创作区/制漫剧/仙界闭关小能手/生产数据/image_qc/第1集/image_qc_第1集.json: 出图落档QC 输入首帧 image_qc 仍有 9 项硬阻断（崩脸/接缝断/降级精度近景/非法 CHAR）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。
- block · character:图片 · 锚点门(N3) / 脸(G1) / 服装配色(N1) / 发型(H1) / 无脸崩坏(G1b)
  - block [gate:image] 锚点门(N3) @ 出图/共享/图片: 锚点门(N3) 一致性审计发现问题
  - block [gate:image] 脸(G1) @ 出图/第1集/图片: 脸(G1) 一致性审计发现问题
  - block [gate:image] 服装配色(N1) @ 出图/第1集/图片: 服装配色(N1) 一致性审计发现问题
- block · ops:ops · 锚点门(N3) / 风格(S1) / 天气时辰(W1) / 物理事件图(PHY) / 成本路由(K1) / 人审校准集(CAL) / 一致性探针包(PROBE)
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
| 贺平生（CHAR_HE_PINGSHENG） | character | ⛔ block | 🔴 | ⛔ | 🟢 |
| 黑陶破盆（PROP_HEI_TAO_PEN） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 水桶与扁担（PROP_SHUI_TONG） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 铁碗/钥匙铁锁（PROP_TIE_WAN） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
| 旧钥匙与生锈铁锁（PROP_KEY_LOCK） | prop | ⛔ block | 🟡 | ⛔ | 🟢 |
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

## ⛔ 贺平生（CHAR_HE_PINGSHENG）
- [warn] 贺平生 锚点门(N3)    
- [warn] 贺平生_幼年 锚点门(N3)    
- [block] 贺平生 脸(G1)    

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
- [block]  风格(S1)    
- [block]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  风格(S1)    
- [warn]  天气时辰(W1)   主光方位 left→right 硬翻转（疑光位跳·人比对相邻镜） 
- [warn]  天气时辰(W1)   天气 fog→overcast 同场景内突变且无时间转场 cue（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'
- [warn]  天气时辰(W1)   天气 overcast→fog 同场景内突变且无时间转场 cue（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'
- [warn]  天气时辰(W1)   主光方位 left→right 硬翻转（疑光位跳·人比对相邻镜） 

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
