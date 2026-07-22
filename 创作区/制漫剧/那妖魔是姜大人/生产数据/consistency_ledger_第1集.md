# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 5 · 🔴 high 0 · 🟡 medium 13

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | 🟡 warn | 0 | 0 | 27 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight |
| 角色 | ⛔ block | 66 | 0 | 89 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight |
| 资产 | ⛔ block | 12 | 0 | 27 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight |
| 镜头 | ⛔ block | 3 | 0 | 80 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight |
| 音频 | 🟡 warn | 0 | 0 | 11 | detect, gate:image_preflight, gate:image_prompt_preflight |
| 字幕 | 🟡 warn | 0 | 0 | 4 | detect |
| 合规 | 🟡 warn | 0 | 0 | 5 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, compliance |
| 生产操作 | ⛔ block | 5 | 0 | 73 | detect, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `爽点` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `集尾` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 7 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08），疑节奏塌·掉留存 
- warn [detect] 物理因果链(CG1):  物理因果链(CG1)   视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 8 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [detect] state_continuity: state_continuity  None 状态演进声明了累积状态（血迹）但本集出图 prompt 未注入——runner 会照画干净/无伤状态，跨镜/跨集视觉状态漏进生成。跑 `python3 skills/n2d-image/scripts/visual_state_manager.py <作品根> --inject` 注入后重出受影响镜。 
- warn [gate:image_preflight] 故事板 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6: 故事板 start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_tailframe_match 并原样继承，若是换机位/换场则在 transition/entry_exit 写清楚。

### 角色问题
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- warn [detect] 服装配色(N1): CHAR_01__囚途残损态 服装配色(N1)    
- block [detect] 发型(H1): CHAR_01__囚途残损态 发型(H1)    
- block [detect] 发型(H1): CHAR_01__囚途残损态 发型(H1)    

### 资产问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如
- warn [detect] 持有账本(POS):  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 结构化交互图谱(I2):  结构化交互图谱(I2)   接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 3 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 
- warn [detect] 系统面板(UI1):  系统面板(UI1)   检出 3 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 
- warn [gate:image_preflight] 击中帧验证 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/脚本/第1集/storyboard.json clip#6: 击中帧验证 该 fight_exchange 模板包含 impact_frame_sync，但未在 continuity 规划中段光效爆发帧 (mid_impact / midframe)。

### 镜头问题
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 场景(O2):  场景(O2)    
- warn [detect] 空间站位(B1): 入出画 空间站位(B1)   入出画 站位/遮挡与同场景首镜冲突：right/front → None/back（疑重新调度·交人判） 
- warn [detect] 视频语义一致(VSEM):  视频语义一致(VSEM)   本集已有视频产物和脚本/视频契约，但缺 video_semantic_consistency；无法核验视频侧主体/背景语义是否随视频生成漂移。 
- warn [detect] 相机空间轨迹(CAM1):  相机空间轨迹(CAM1)   视频含明确镜头运动/空间轨迹，但缺 camera_trajectory_probe；无法核验运动方向、深度、越轴和抖动连续性。 
- warn [detect] 运动质量(MOT1):  运动质量(MOT1)   视频含明确动作/运动镜，但缺 motion_quality 报告；无法核验冻结、抽搐、速度突变和动作完成度。 
- warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（BEAST_01/伪死态, BEAST_01/复生态, CHAR_01, CHAR_01/囚途残损态, CHAR_01__, CHAR_01__囚途残损态）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
- warn [detect] 视频证据完整性(EVID):  视频证据完整性(EVID)   本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 

### 音频问题
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头1·姜月初：台词含强情绪但配音标注「短促决绝」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头12·虎妖：台词含强情绪但配音标注「傲慢从容」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 配音情绪弧(VEA):  配音情绪弧(VEA)   镜头19·姜月初：台词含强情绪但配音标注「急促盘算」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 
- warn [detect] 声音空间(ASP):  声音空间(ASP)   缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 
- warn [detect] 多人对话音画(DAV):  多人对话音画(DAV)   检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 
- warn [detect] 生成配方(RCP):  生成配方(RCP)   脚本/第1集/voiceover.txt 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=cccc53a5dc6e99b9，但复跑审计证据不完整。 
- warn [detect] 强配方Schema(RCP2):  强配方Schema(RCP2)   脚本/第1集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_versi
- warn [detect] 成本路由(K1):  成本路由(K1)   脚本/第1集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 

### 字幕问题
- warn [detect] 系列包装(PKG):  系列包装(PKG)   缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_06 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 
- warn [detect] 文字渲染(OCR1):  文字渲染(OCR1)   Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 

### 合规问题
- warn [detect] 世界一致性(WCS):  世界一致性(WCS)   已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，dashboard 无法看集级世界一致性趋势。 
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

### 生产操作问题
- warn [detect] 打斗撞点(SPEC-APEX):  打斗撞点(SPEC-APEX)    Clip_08（fight_exchange）：剪辑峰值 @9.0s 附近（±0.4s）无 keyframe 锚（现有 keyframe 锚 [5.6]s）——峰值引用了不存在的离散关键帧，重排锚帧或对齐 cue 秒。
- warn [detect] 风格(S1):  风格(S1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- block [detect] 天气时辰(W1):  天气时辰(W1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- block [detect] 天气时辰(W1):  天气时辰(W1)    
- warn [detect] 天气时辰(W1):  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- warn [detect] 天气时辰(W1):  天气时辰(W1)    

## 根因聚合

- block · asset:01_clips.md · 剧本可看性消费 / 契约继承
  - block [gate:video_preflight] 剧本可看性消费 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/prompt/01_clips.md: 剧本可看性消费 出视频 的 script_contract_applied 收据已过期或不匹配当前合同/prompt SHA；重生成 prompt 或重跑 script_contract_receipt.py 后再进入付费阶段。
  - block [gate:video_preflight] 契约继承 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/prompt/01_clips.md: 契约继承 身份逐镜交接[identity_anchor_reference_group_missing]：Clip_01：多锚帧角色 Clip 缺 `reference_group` 兜底。即使目标后端支持 Character ID / Face Lock / reference controls，也必须把同一套 registry reference_gro
  - block [gate:video_preflight] 契约继承 @ 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/prompt/01_clips.md: 契约继承 身份逐镜交接[identity_anchor_reference_group_missing]：Clip_02：多锚帧角色 Clip 缺 `reference_group` 兜底。即使目标后端支持 Character ID / Face Lock / reference controls，也必须把同一套 registry reference_gro
- block · asset:01_分镜出图.md · 剧本可看性消费
  - block [gate:video_preflight] 剧本可看性消费 @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md: 剧本可看性消费 出图 的 script_contract_applied 收据已过期或不匹配当前合同/prompt SHA；重生成 prompt 或重跑 script_contract_receipt.py 后再进入付费阶段。
- block · asset:consumed_contracts_video_prompt_第1集.json · Prompt消费收据
  - block [gate:video_preflight] Prompt消费收据 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consumed_contracts_video_prompt_第1集.json: Prompt消费收据 prompt pack 消费合同不新鲜或不完整，禁止进入昂贵生成：storyboard 已变更但 prompt 未重签：脚本/第1集/storyboard.json
- block · character:CHAR_01 · 实体记忆(EMB) / image_prompt_lint / 脸漂预案 / image prompt compiler
  - warn [detect] 实体记忆(EMB):  实体记忆(EMB)   本集有重复/核心实体（BEAST_01/伪死态, BEAST_01/复生态, CHAR_01, CHAR_01/囚途残损态, CHAR_01__, CHAR_01__囚途残损态）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 
  - warn [detect] image_prompt_lint: image_prompt_lint  None 表情板人脸数量不符 CHAR_01/“囚途残损态”「六联表」（出图/共享/图片/定妆_CHAR_01__囚途残损态_表情_六联表.png）：声明 6 格，机器检出 4 张脸；需确认是否缺格、重复拼接、遮脸或检测漏脸后再放行。 
  - block [detect] image_prompt_lint: image_prompt_lint  None 脸部锚弱信噪比 CHAR_01/“囚途残损态”「六联表」（出图/共享/图片/定妆_CHAR_01__囚途残损态_表情_六联表.png）：单格短边 341px（最低 384px）——弱脸锚会把脸漂带进下游每一镜；核心/长线角色必须重出更紧的脸部特写（脸占 30–50%、≥1024px）后再放行。 
- block · character:Clip01_end.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_end.png: character_consistency 降级精度多人同框：图片/Clip01_end.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大
  - block [gate:image] character_consistency @ 图片/Clip01_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP01_CLIP01` · 刀口为何对准人 · ） 图片/Clip01_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip01_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip01_first.png: character_consistency 降级精度多人同框：图片/Clip01_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是
  - block [gate:image] character_consistency @ 图片/Clip01_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 1（`EP01_CLIP01` · 刀口为何对准人 · ） 图片/Clip01_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip02_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip02_first.png: character_consistency 降级精度多人同框：图片/Clip02_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是
  - block [gate:image] character_consistency @ 图片/Clip02_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 2（`EP01_CLIP02` · 一炷香前的荒野死局 · dialogue_shot_reverse） 图片/Clip02_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
  - warn [gate:image] character_consistency @ 图片/Clip02_first.png: character_consistency 发型 H1 初筛：图片/Clip02_first.png（发色/发型轮廓离群，非阻断）
- block · character:Clip03_first.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip03_first.png: character_consistency 降级精度多人同框：图片/Clip03_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是
  - block [gate:image] character_consistency @ 图片/Clip03_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 3（`EP01_CLIP03` · 以脱籍换搀扶 · dialogue_shot_reverse） 图片/Clip03_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip04_first.png · outfit_consistency / character_consistency
  - warn [detect] outfit_consistency @ 图片/Clip04_first.png: outfit_consistency  图片/Clip04_first.png 服装 N1 初筛：图片/Clip04_first.png（调色板离群，非阻断） 
  - block [gate:image] character_consistency @ 图片/Clip04_first.png: character_consistency 降级精度多人同框：图片/Clip04_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是
  - block [gate:image] character_consistency @ 图片/Clip04_first.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 4（`EP01_CLIP04` · 先活着再算账 · dialogue_shot_reverse） 图片/Clip04_first.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip05_end.png · outfit_consistency / character_consistency
  - warn [detect] outfit_consistency @ 图片/Clip05_end.png: outfit_consistency  图片/Clip05_end.png 服装 N1 初筛：图片/Clip05_end.png（调色板离群，非阻断） 
  - block [gate:image] character_consistency @ 图片/Clip05_end.png: character_consistency 降级精度多人同框：图片/Clip05_end.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大
  - block [gate:image] character_consistency @ 图片/Clip05_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 5（`EP01_CLIP05` · 死妖咳嗽站起 · reveal_reaction_chain） 图片/Clip05_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。
- block · character:Clip05_first.png · character_consistency / outfit_consistency
  - warn [detect] character_consistency @ 图片/Clip05_first.png: character_consistency  图片/Clip05_first.png 发型 H1 初筛：图片/Clip05_first.png（发色/发型轮廓离群，非阻断） 
  - warn [detect] outfit_consistency @ 图片/Clip05_first.png: outfit_consistency  图片/Clip05_first.png 服装 N1 初筛：图片/Clip05_first.png（调色板离群，非阻断） 
  - block [gate:image] character_consistency @ 图片/Clip05_first.png: character_consistency 降级精度多人同框：图片/Clip05_first.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是
- block · character:Clip06_end.png · character_consistency
  - block [gate:image] character_consistency @ 图片/Clip06_end.png: character_consistency 降级精度多人同框：图片/Clip06_end.png 在 Pillow 降级模式下无 embedding 串脸检测（无 insightface）；同框 ≥2 具名角色时次要角色脸是否串脸/画对未经核验，不放行；人审并排图：/Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大
  - block [gate:image] character_consistency @ 图片/Clip06_end.png: character_consistency 角色脸定妆比对覆盖缺口：镜头 6（`EP01_CLIP06` · 虎口最后威胁 · fight_exchange） 图片/Clip06_end.png；缺 full 精度脸部 embedding 比对。每张已落档角色图必须逐张对定妆/身份主参考过 full QC，未过不得进 video。

## 依赖传播

- nodes=94 · edges=234 · clips=8 · images=32 · videos=28
- graph: `创作区/制漫剧/那妖魔是姜大人/生产数据/consistency_dependency_graph_第1集.json`

## 合法不连续签收

- status=pass · accepted=0 · block=0 · warn=0

## 补充一致性合约

- motion_grammar_consistency: status=pass · block=0 · warn=0
- audio_space_consistency: status=pass · block=0 · warn=0
- expression_state_consistency: status=pass · block=0 · warn=5

## 角色/资产一致性画像

- 三态：**事前**=出图前漂移预案(drift_risk) · **落档**=image_qc/一致性机检 · **契约**=出图→出视频继承(handoff)

| 实体 | 类型 | 综合 | 事前 | 落档 | 契约 |
|---|---|---|---|---|---|
| 姜月初（CHAR_01） | character | ⛔ block | 🟡 | ⛔ | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 虎妖（BEAST_01） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 尸骸荒野（LOC_01） | scene | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（WEAPON_01） | weapon | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 横刀（PROP_横刀） | prop | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 断刀（PROP_断刀） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 翻覆囚车（PROP_翻覆囚车） | prop | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 百妖谱金色古卷面板（VFX_系统面板） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |
| 百妖谱（VFX_百妖谱） | vfx | 🟡 medium | 🟡 | 🟢 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚途残损态 服装配色(N1)    
- [warn] CHAR_01__囚途残损态 服装配色(N1)    
- [warn] CHAR_01__囚途残损态 服装配色(N1)    

## 🟡 裴长青（CHAR_02）
- [warn] character_consistency  CHAR_02__濒死重伤态 锚点门 N3：CHAR_02__濒死重伤态 主参考非单张清晰正脸
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「face_anchor」（出图/共享/图片/
- [warn] image_prompt_lint  None 脸部锚弱信噪比 CHAR_02/“濒死重伤态”「克制」（出图/共享/图片/定妆_CHAR_0

## 🟡 虎妖（BEAST_01）
- [warn]  配音情绪弧(VEA)   镜头12·虎妖：台词含强情绪但配音标注「傲慢从容」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  实体记忆(EMB)   本集有重复/核心实体（BEAST_01/伪死态, BEAST_01/复生态, CHAR_01, CHAR_01/囚
- [warn] image_prompt_lint  None 多视图对齐初筛异常 BEAST_01/“穿心复生态”：脚底线不齐：rear_three_qu

## 🟡 尸骸荒野（LOC_01）
- [warn]  场景平面(FP1)   场景 LOC_01 本集出现 8 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记

## 🟡 横刀（WEAPON_01）
- [warn]  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 

## 🟡 横刀（PROP_横刀）
- [warn]  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 

## 未归属到具体角色/资产的一致性问题
- [warn]  场景(O2)    
- [warn]  场景(O2)    
- [warn]  打斗撞点(SPEC-APEX)    Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/scree
- [warn]  打斗撞点(SPEC-APEX)    Clip_08（fight_exchange）：剪辑峰值 @9.0s 附近（±0.4s）无 keyf
- [warn] 入出画 空间站位(B1)   入出画 站位/遮挡与同场景首镜冲突：right/front → None/back（疑重新调度·交人判） 
- [warn]  风格(S1)    
- [warn]  天气时辰(W1)   光位锚声明主光在「right」，实测最亮区却偏「left」——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。 
- [block]  天气时辰(W1)    

说明：本表是验收交付面。`counts.block/high` 未清零时不得回写 `验收=✅`；medium 可由人工复核决定是否签收。
