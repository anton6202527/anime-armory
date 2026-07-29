# 验收总账 · 第3集

- 验收状态：阻断
- ⛔ block 6 · 🔴 high 0 · 🟡 medium 11

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 1 | 0 | 42 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 角色 | ⛔ block | 5 | 0 | 62 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 资产 | ⛔ block | 7 | 0 | 18 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 镜头 | ⛔ block | 1 | 0 | 75 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 音频 | ⛔ block | 8 | 0 | 28 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight |
| 字幕 | 🟡 warn | 0 | 0 | 1 | detect |
| 合规 | 🟡 warn | 0 | 0 | 6 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, compliance |
| 生产操作 | ⛔ block | 40 | 0 | 64 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video_prompt_preflight, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。
- warn [detect] 语义谱系(P0):  语义谱系(P0)   复杂镜视频 prompt 未充分继承专项模板契约。
- warn [detect] 语义谱系(P0):  语义谱系(P0)   复杂镜视频 prompt 未充分继承专项模板契约。
- warn [detect] 语义谱系(P0):  语义谱系(P0)   复杂镜视频 prompt 未充分继承专项模板契约。
- warn [detect] 语义谱系(P0):  语义谱系(P0)   复杂镜视频 prompt 未充分继承专项模板契约。
- warn [detect] 语义谱系(P0):  语义谱系(P0)   复杂镜视频 prompt 未充分继承专项模板契约。
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 4 个长镜聚集（EP03_CLIP01→EP03_CLIP02→EP03_CLIP03→EP03_CLIP04），疑节奏塌·掉留存
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 3 个长镜聚集（EP03_CLIP06→EP03_CLIP07→EP03_CLIP08），疑节奏塌·掉留存

### 角色问题
- warn [detect] 服装配色(N1): CHAR_01__镇魔司制服态 服装配色(N1)
- warn [detect] 服装配色(N1): CHAR_01__镇魔司制服态 服装配色(N1)
- warn [detect] 发型(H1): CHAR_01__镇魔司制服态 发型(H1)
- warn [detect] 发型(H1): CHAR_01__镇魔司制服态 发型(H1)
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_04：角色 CHAR_01 相邻镜情绪硬跳（惊→喜）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_07：角色 CHAR_01 相邻镜情绪硬跳（喜→悲）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
- warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_07：角色 CHAR_03 相邻镜情绪硬跳（惊→悲）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
- warn [detect] 真值源(TRUTH):  真值源(TRUTH)   项目已有 identity_registry / asset_registry / storyboard / state ledger / generation_recipe 等多种真值源，但缺 consistency_truth_map；冲突时无法机器说明谁覆盖谁。

### 资产问题
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。

### 镜头问题
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集色调/光位漂移 L1=0.4515（vs 前 2 集基线，阈 warn=0.45·core block=0.8）——确认是否 allowed_variations 内的合理变化，否则对齐前集场景定妆。
- warn [detect] 跨集场景漂移(SCNX):  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集结构漂移 dHash 汉明=24（vs 前 2 集结构原型，阈 warn=18·core block=26）——色调一致但结构疑似变样（家具挪位/构图朝向变），核对是否同一空间，否则对齐场景定妆 spatial_layout。
- warn [detect] 景深一致(DOF1):  景深一致(DOF1)   图片/Clip01_first_a1.png：景深档与同场景其它镜不一致——本镜偏深焦(背景偏清)（景深比 1.377 vs 场景中位 0.758）；同场景深焦↔浅景深横跳像换相机，人核对是否有意，否则统一景深档重出。
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/“囚途残损态”, CHAR_01/镇魔司制服态, CHAR_01__, CHAR_01__囚途残损态, CHAR_01__镇魔司制服态）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。
- warn [detect] 场景平面(FP1):  场景平面(FP1)   场景 LOC_02 本集出现 6 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记忆。
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚途残损态」↔ 本镜 图片/Clip01_first.png DINO/CLIP cosine=0.11 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。
- warn [detect] multimodal_continuity: multimodal_continuity  None outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚途残损态」↔ 本镜 图片/Clip01_first_a1.png DINO/CLIP cosine=0.39 < 0.55——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头2·姜月初：台词含强情绪但配音标注「错愕心虚」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头12·陈青源：台词含强情绪但配音标注「急切恭敬」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。
- warn [detect] 音色声纹 @ voicemap:飞鹰门众人:  音色声纹   角色「飞鹰门众人」未在 voicemap 登记：渲染将走内置兜底猜测，跨集音色不稳。先在 设定库/voicemap.json 登记其音色键再配音。
- warn [detect] 音色声纹 @ voicemap:陈青源:  音色声纹   角色「陈青源」未在 voicemap 登记：渲染将走内置兜底猜测，跨集音色不稳。先在 设定库/voicemap.json 登记其音色键再配音。
- warn [detect] 语义谱系(P0):  语义谱系(P0)   配音角色 `飞鹰门众人` 未进入 storyboard。
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第3集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=2b039e84f9118338，但复跑审计证据不完整。
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第3集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第3集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 风格(S1):  风格(S1)
- warn [detect] 风格(S1):  风格(S1)
- block [detect] 风格(S1):  风格(S1)
- warn [detect] 风格(S1):  风格(S1)
- warn [detect] 天气时辰(W1):  天气时辰(W1)
- block [detect] 天气时辰(W1):  天气时辰(W1)
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。
- warn [detect] 物理事件图(PHY):  物理事件图(PHY)   本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。

## 根因聚合

- block · asset:motion_control_manifest.json · Motion Control
  - block [gate:video_preflight] Motion Control @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/control/Clip_01/motion_control_manifest.json: Motion Control 缺 motion_control_manifest.json；必须先准备 ready 控制资产，或写 status=degrade_only 的拆镜 manifest
  - block [gate:video_preflight] Motion Control @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/control/Clip_05/motion_control_manifest.json: Motion Control 缺 motion_control_manifest.json；必须先准备 ready 控制资产，或写 status=degrade_only 的拆镜 manifest
  - block [gate:video_preflight] Motion Control @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/control/Clip_07/motion_control_manifest.json: Motion Control 缺 motion_control_manifest.json；必须先准备 ready 控制资产，或写 status=degrade_only 的拆镜 manifest
- block · asset:storyboard.json clip#6 · 实体排程
  - block [gate:image_prompt_preflight] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#6: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
- block · asset:storyboard.json clip#8 · 实体排程
  - block [gate:image_prompt_preflight] 实体排程 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#8: 实体排程 同一实体同时被登记为可见/必须出现和 offscreen_presence：GROUP_01。画外保留只能用于不清晰入画的声音、影子、手部/物件/反应承接；请拆清楚可见槽位与画外槽位。
- block · audio:video_model_routes.json · 后期表演通道 / 生视频后端适配 / 单Clip时长
  - warn [gate:video_preflight] 后期表演通道 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/video_model_routes.json: 后期表演通道 Clip_01 只获准生成中性嘴型基础片；完成 lipsync_pass 前不是最终说话镜
  - warn [gate:video_preflight] 后期表演通道 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/video_model_routes.json: 后期表演通道 Clip_02 只获准生成中性嘴型基础片；完成 lipsync_pass 前不是最终说话镜
  - warn [gate:video_preflight] 后期表演通道 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/video_model_routes.json: 后期表演通道 Clip_05 只获准生成中性嘴型基础片；完成 lipsync_pass 前不是最终说话镜
- block · character:CHAR_01 · 表情连续(EXP1) / 实体记忆(EMB) / image_prompt_lint / image prompt compiler / 脸漂实测
  - warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_04：角色 CHAR_01 相邻镜情绪硬跳（惊→喜）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
  - warn [detect] 表情连续(EXP1):  表情连续(EXP1)   Clip_07：角色 CHAR_01 相邻镜情绪硬跳（喜→悲）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。
  - warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（CHAR_01, CHAR_01/“囚途残损态”, CHAR_01/镇魔司制服态, CHAR_01__, CHAR_01__囚途残损态, CHAR_01__镇魔司制服态）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。
- block · character:CHAR_02 · image_prompt_lint / image prompt compiler / 实体排程
  - warn [detect] image_prompt_lint: image_prompt_lint  None 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「克制」（出图/共享/图片/定妆_CHAR_02__濒死重伤态_表情_克制.png）：脸占画面仅 3%（建议 ≥30%，最低线 ≥12%）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。
  - warn [detect] image_prompt_lint: image_prompt_lint  None 多视图对齐初筛异常 CHAR_02/“濒死重伤态”：脚底线不齐：side(0.950) vs rear_three_quarter(1.000)，差 0.050>0.035；身体中心线不齐：side(0.485) vs rear_three_quarter(0.625)，差 0.140>0.055——像素几何是
  - warn [gate:image_preflight] image prompt compiler @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/出图/共享/prompt/角色定妆.md ## 裴长青（`CHAR_02/“濒死重伤态”`）: image prompt compiler 共享资产编译图片请求可进一步精简：submit_prompt_many_clauses:43>16
- block · character:production_breakdown_check_第3集.json · P-3制片交接包
  - block [gate:image_prompt_preflight] P-3制片交接包 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/production_breakdown_check_第3集.json: P-3制片交接包 P-3 制片交接包未通过：7/9 confirmed。进入出图/视频前必须补齐并确认 continuity_chain.json、continuity_bible.json、ai_shooting_schedule.json、ai_call_sheet.md 等交接文件；问题示例：脚本/第3集/production_handoff_pack
- block · character:storyboard.json clip#3 · 表情一致性
  - block [gate:image_prompt_preflight] 表情一致性 @ 创作区/制漫剧/那妖魔是姜大人/脚本/第3集/storyboard.json clip#3: 表情一致性 continuity.expression_span='小' 非法；必须是 微/中/大 之一。
- block · character:video_model_routes.json · 后端跨集锁
  - block [gate:video_preflight] 后端跨集锁 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/video_model_routes.json: 后端跨集锁 1 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；高风险/含角色镜头的路由漂移必须写结构化 baseline_override（accepted/reviewer/reason/expires_at/affected_routes）或刷新基线
  - block [gate:video_prompt_preflight] 后端跨集锁 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/video_model_routes.json: 后端跨集锁 1 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；高风险/含角色镜头的路由漂移必须写结构化 baseline_override（accepted/reviewer/reason/expires_at/affected_routes）或刷新基线
- block · ops:01_clips.md ## Clip 01（时长 10.520s · EP03_CLIP01 · 众人跪求的假大人） · 帧策略 / prompt compiler
  - block [gate:video_preflight] 帧策略 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/01_clips.md ## Clip 01（时长 10.520s · EP03_CLIP01 · 众人跪求的假大人）: 帧策略 多镜位 Clip 选择了 edit_cut，但缺少分镜边界图或尾帧；先补图再付费生成
  - warn [gate:video_preflight] prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/01_clips.md ## Clip 01（时长 10.520s · EP03_CLIP01 · 众人跪求的假大人）: prompt compiler 提交 prompt 可进一步精简：submit_prompt_many_clauses:21>12
- block · ops:01_clips.md ## Clip 04（时长 15.383s · EP03_CLIP04 · 贱籍死局与马蹄） · 帧策略 / prompt compiler
  - block [gate:video_preflight] 帧策略 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/01_clips.md ## Clip 04（时长 15.383s · EP03_CLIP04 · 贱籍死局与马蹄）: 帧策略 多镜位 Clip 选择了 edit_cut，但缺少分镜边界图或尾帧；先补图再付费生成
  - warn [gate:video_preflight] prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/01_clips.md ## Clip 04（时长 15.383s · EP03_CLIP04 · 贱籍死局与马蹄）: prompt compiler 提交 prompt 可进一步精简：submit_prompt_many_clauses:18>12
- block · ops:01_clips.md ## Clip 05（时长 4.428s · EP03_CLIP05 · 马队急停试探） · 帧策略 / prompt compiler
  - block [gate:video_preflight] 帧策略 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/01_clips.md ## Clip 05（时长 4.428s · EP03_CLIP05 · 马队急停试探）: 帧策略 多镜位 Clip 选择了 edit_cut，但缺少分镜边界图或尾帧；先补图再付费生成
  - warn [gate:video_preflight] prompt compiler @ 创作区/制漫剧/那妖魔是姜大人/出视频/第3集/prompt/01_clips.md ## Clip 05（时长 4.428s · EP03_CLIP05 · 马队急停试探）: prompt compiler 提交 prompt 可进一步精简：submit_prompt_many_clauses:22>12

## 依赖传播

- nodes=54 · edges=87 · clips=8 · images=20 · videos=0
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第3集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=2

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_01） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 03（CHAR_03） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| 虎妖（BEAST_01） | character | 🟡 warn | 🟢 | 🟡 | 🟢 |
| LOC_02（LOC_02） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 横刀（WEAPON_横刀） | weapon | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 尸骸荒野（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 镇魔司制服（PROP_镇魔司制服） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| GROUP_01（GROUP_01） | character | 🟢 ok | 🟢 | 🟢 | 🟢 |

## 🟡 姜月初（CHAR_01）
- [warn] CHAR_01__镇魔司制服态 服装配色(N1)
- [warn] CHAR_01__镇魔司制服态 服装配色(N1)
- [warn] CHAR_01__镇魔司制服态 发型(H1)

## 🟡 03（CHAR_03）
- [warn]  表情连续(EXP1)   Clip_07：角色 CHAR_03 相邻镜情绪硬跳（惊→悲）——确认有节拍/事件依据，否则表演 OOC（情绪没
- [warn]  节奏密度(Rhythm)   连续 4 个长镜聚集（EP03_CLIP01→EP03_CLIP02→EP03_CLIP03→EP03_CL
- [warn]  节奏密度(Rhythm)   连续 3 个长镜聚集（EP03_CLIP06→EP03_CLIP07→EP03_CLIP08），疑节奏塌·掉

## 🟡 裴长青（CHAR_02）
- [warn] character_consistency  CHAR_02__濒死重伤态 锚点门 N3：CHAR_02__濒死重伤态 主参考非单张清晰正脸
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「克制」（出图/共享/图片/定妆_CHAR_0
- [warn] image_prompt_lint  None 多视图对齐初筛异常 CHAR_02/“濒死重伤态”：脚底线不齐：side(0.950) vs

## 🟡 虎妖（BEAST_01）
- [warn] image_prompt_lint  None 多视图对齐初筛异常 BEAST_01/“穿心复生态”：脚底线不齐：rear_three_qu

## 🟡 LOC_02（LOC_02）
- [warn]  场景平面(FP1)   场景 LOC_02 本集出现 6 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记

## 🟡 尸骸荒野（LOC_01）
- [warn]  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集色调/光位漂移 L1=0.4515（vs 前 2 集基线，阈 warn=0.45·c
- [warn]  跨集场景漂移(SCNX)    场景[尸骸荒野] 跨集结构漂移 dHash 汉明=24（vs 前 2 集结构原型，阈 warn=18·co

## 🟡 镇魔司制服（PROP_镇魔司制服）
- [warn] CHAR_01__镇魔司制服态 服装配色(N1)
- [warn] CHAR_01__镇魔司制服态 服装配色(N1)
- [warn] CHAR_01__镇魔司制服态 发型(H1)

## 未归属到具体角色/资产的一致性问题
- [warn]  风格(S1)
- [warn]  风格(S1)
- [block]  风格(S1)
- [warn]  风格(S1)
- [warn]  景深一致(DOF1)   图片/Clip01_first_a1.png：景深档与同场景其它镜不一致——本镜偏深焦(背景偏清)（景深比 1.
- [warn]  天气时辰(W1)
- [block]  天气时辰(W1)
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
