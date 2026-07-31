# 验收总账 · 第1集

- 验收状态：阻断
- ⛔ block 12 · 🔴 high 0 · 🟡 medium 5

## 交付域闭环

| 交付域 | 综合 | block | high | medium | 证据源 |
|---|---|---:|---:|---:|---|
| 剧情 | ⛔ block | 3 | 0 | 46 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video |
| 角色 | ⛔ block | 154 | 0 | 120 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video |
| 资产 | ⛔ block | 27 | 0 | 31 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video |
| 镜头 | ⛔ block | 44 | 0 | 63 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video |
| 音频 | 🟡 warn | 0 | 0 | 14 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:video |
| 字幕 | 🟡 warn | 0 | 0 | 4 | detect |
| 合规 | 🟡 warn | 0 | 0 | 7 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video, compliance |
| 生产操作 | ⛔ block | 31 | 0 | 93 | detect, gate:compose, gate:image_preflight, gate:image_prompt_preflight, gate:image, gate:video_preflight, gate:video, score, expression_state_consistency |

### 剧情问题
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `钩子` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `爽点` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 语义谱系(P0):  语义谱系(P0)   `集尾` 留存标记未进入 storyboard 节奏/导演意图。 
- warn [detect] 节奏密度(Rhythm):  节奏密度(Rhythm)   连续 7 个长镜聚集（EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08），疑节奏塌·掉留存 
- warn [detect] 物理因果链(CG1):  物理因果链(CG1)   视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 
- warn [detect] 视线状态回读(X2):  视线状态回读(X2)   8 个视线/状态高风险镜当前 image_qc 精度为 degraded；需要 full QC 或人审签收，不能把降级绿灯当作像素一致已验证。 
- warn [detect] 状态转场视频证据(ST1):  状态转场视频证据(ST1)   检测到 8 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 
- warn [detect] state_continuity: state_continuity  None 状态演进声明了累积状态（血迹）但本集出图 prompt 未注入——runner 会照画干净/无伤状态，跨镜/跨集视觉状态漏进生成。跑 `python3 skills/n2d/n2d-image/scripts/visual_state_manager.py <作品根> --inject` 注入后重出受影响镜。

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
- warn [detect] human_anatomy_continuity: human_anatomy_continuity  None 人体解剖 N5 未执行：手部畸形机检已跳过（未装 cv2）——多指/粘连暂由人逐帧放大看。；本轮图片一致性为降级判定，需补依赖后重跑或人工复核。 

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
- warn [gate:compose] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_preflight] 合规前置 @ /Users/wesley/learn/anime-armory/创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image_prompt_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:image] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video_preflight] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放
- warn [gate:video] 合规前置 @ 创作区/制漫剧/那妖魔是姜大人/合规/compliance_manifest.json: 合规前置 distribution_intent=internal_only；platform_review / localization / regulatory_filing 检查降为 INFO（内部 demo 免检，转投放前需补），产物不得直接投放

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
  - block [gate:video] 剧本可看性消费 @ 创作区/制漫剧/那妖魔是姜大人/出图/第1集/prompt/01_分镜出图.md: 剧本可看性消费 出图 的 script_contract_applied 收据已过期或不匹配当前合同/prompt SHA；重生成 prompt 或重跑 script_contract_receipt.py 后再进入付费阶段。
- block · asset:WEAPON_01 · multimodal_continuity / image_prompt_lint / image prompt compiler
  - block [detect] multimodal_continuity @ 图片/EP01_CLIP01_a1.png: multimodal_continuity  图片/EP01_CLIP01_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 1（`EP01_CLIP01` · 刀口为何对准人 · ） 的 `WEAPON_01`（横刀，type=weapon）登记了 must_not_have=变成长剑、华丽仙剑、现代军刀、多把复制、副刀、短刃、匕首、右手第二把
  - block [detect] multimodal_continuity @ 图片/EP01_CLIP02_a1.png: multimodal_continuity  图片/EP01_CLIP02_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 2（`EP01_CLIP02` · 一炷香前的荒野死局 · dialogue_shot_reverse） 的 `WEAPON_01`（横刀，type=weapon）登记了 must_not_have=变成长剑、华丽仙剑、现
  - block [detect] multimodal_continuity @ 图片/EP01_CLIP02_face_reveal.png: multimodal_continuity  图片/EP01_CLIP02_face_reveal.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 2（`EP01_CLIP02` · 一炷香前的荒野死局 · dialogue_shot_reverse） 的 `WEAPON_01`（横刀，type=weapon）登记了 must_not_have=变成
- block · asset:consumed_contracts_video_prompt_第1集.json · Prompt消费收据
  - block [gate:video_preflight] Prompt消费收据 @ 创作区/制漫剧/那妖魔是姜大人/生产数据/consumed_contracts_video_prompt_第1集.json: Prompt消费收据 prompt pack 消费合同不新鲜或不完整，禁止进入昂贵生成：storyboard 已变更但 prompt 未重签：脚本/第1集/storyboard.json
- block · asset:storyboard.json · 打斗撞点(SPEC-APEX)
  - block [gate:compose] 打斗撞点(SPEC-APEX) @ 脚本/第1集/storyboard.json: 打斗撞点(SPEC-APEX) [production一致性升级:核心打斗镜剪辑撞点未对齐 apex 关键帧] Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collis
  - warn [gate:image] 打斗撞点(SPEC-APEX) @ 脚本/第1集/storyboard.json: 打斗撞点(SPEC-APEX) Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如「命中 
  - warn [gate:video] 打斗撞点(SPEC-APEX) @ 脚本/第1集/storyboard.json: 打斗撞点(SPEC-APEX) Clip_06（fight_exchange）：impact 剪辑峰值（hit_stop/screen_shake/impact_sfx/闪白…）的 when 取不到秒数——template_contract.impact_frame/collision_or_apex_frame 需写成带 `<秒>s` 的命中帧（如「命中 
- block · asset:第1集 PROP_断刀 · 资产引用注册层
  - block [gate:compose] 资产引用注册层 @ 第1集 PROP_断刀: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `PROP_断刀`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
- block · asset:第1集 PROP_断刀中景横向封路 · 资产引用注册层
  - block [gate:compose] 资产引用注册层 @ 第1集 PROP_断刀中景横向封路: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `PROP_断刀中景横向封路`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
- block · asset:第1集 PROP_断刀刀柄 · 资产引用注册层
  - block [gate:compose] 资产引用注册层 @ 第1集 PROP_断刀刀柄: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `PROP_断刀刀柄`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
- block · asset:第1集 PROP_横刀 · 资产引用注册层
  - block [gate:compose] 资产引用注册层 @ 第1集 PROP_横刀: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `PROP_横刀`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
- block · asset:第1集 PROP_横刀中轴 · 资产引用注册层
  - block [gate:compose] 资产引用注册层 @ 第1集 PROP_横刀中轴: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `PROP_横刀中轴`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
- block · asset:第1集 PROP_横刀刀尖首次触及并微入CHAR_02胸前衣料 · 资产引用注册层
  - block [gate:compose] 资产引用注册层 @ 第1集 PROP_横刀刀尖首次触及并微入CHAR_02胸前衣料: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `PROP_横刀刀尖首次触及并微入CHAR_02胸前衣料`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。
- block · asset:第1集 PROP_横刀刀柄 · 资产引用注册层
  - block [gate:compose] 资产引用注册层 @ 第1集 PROP_横刀刀柄: 资产引用注册层 本集分镜/出图 prompt 引用了未登记的资产标记 `PROP_横刀刀柄`，但它不在 asset_registry.json 已登记 id 中——要么写错/笔误（回分镜改正），要么该资产尚未定妆登记（先补登记+定妆再引用）。未知标记禁止进入付费出图/出视频（防写错 id 空烧）。

## 依赖传播

- nodes=95 · edges=242 · clips=8 · images=34 · videos=28
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
| 尸骸荒野（LOC_01） | scene | ⛔ block | 🟡 | ⛔ | 🟢 |
| 横刀（WEAPON_01） | weapon | ⛔ block | 🟡 | ⛔ | 🟢 |
| 百妖谱金色古卷面板（VFX_系统面板） | vfx | ⛔ block | 🟡 | ⛔ | 🟢 |
| 横刀（WEAPON_横刀） | weapon | ⛔ block | 🟢 | ⛔ | 🟢 |
| 百妖谱（VFX_百妖谱） | vfx | ⛔ block | 🟡 | ⛔ | 🟢 |
| 墨虎谱影（VFX_墨虎谱影） | vfx | ⛔ block | 🟢 | ⛔ | 🟢 |
| 裴长青（CHAR_02） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |
| 虎妖（BEAST_01） | character | 🟡 medium | 🟡 | 🟡 | 🟢 |

## ⛔ 姜月初（CHAR_01）
- [warn] CHAR_01__囚途残损态 服装配色(N1)    
- [warn] CHAR_01__囚途残损态 服装配色(N1)    
- [warn] CHAR_01__囚途残损态 服装配色(N1)    

## ⛔ 尸骸荒野（LOC_01）
- [warn]  场景平面(FP1)   场景 LOC_01 本集出现 8 镜但缺 scene_floorplan；反打/绕场/多镜复用时空间关系只靠文字记
- [block] multimodal_continuity  None 关键场景/道具/服装/VFX 已进入 scene/multimodal QC，但 D
- [warn] image_prompt_lint  None 资产 LOC_01：出图/共享/图片/定妆_场景_尸骸荒野.png faceless 像素核

## ⛔ 横刀（WEAPON_01）
- [warn]  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 
- [block] multimodal_continuity  出图/共享/图片/定妆_武器_横刀.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：共享主参
- [block] multimodal_continuity  图片/EP01_CLIP01_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 1

## ⛔ 百妖谱金色古卷面板（VFX_系统面板）
- [block] multimodal_continuity  图片/EP01_CLIP07_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 7
- [block] multimodal_continuity  图片/EP01_CLIP07_a2.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 7

## ⛔ 横刀（WEAPON_横刀）
- [warn]  持有账本(POS)   PROP_横刀刀柄冲锋 在 Clip_06 有持有状态，但 possession_ledger 未登记本镜状态。 
- [block] multimodal_continuity  出图/共享/图片/定妆_武器_横刀.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：共享主参
- [block] multimodal_continuity  图片/EP01_CLIP01_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 1

## ⛔ 百妖谱（VFX_百妖谱）
- [block] multimodal_continuity  图片/EP01_CLIP07_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 7
- [block] multimodal_continuity  图片/EP01_CLIP07_a2.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 7
- [block] multimodal_continuity  图片/EP01_CLIP07_a1.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：镜头 7

## ⛔ 墨虎谱影（VFX_墨虎谱影）
- [block] multimodal_continuity  出图/共享/图片/定妆_特效_墨虎谱影.png 高风险道具禁形/尺寸/物料拓扑未逐图确认：共享
- [warn] image_prompt_lint  None 资产 VFX_墨虎谱影：出图/共享/图片/定妆_特效_墨虎谱影.png faceless 像

## 🟡 裴长青（CHAR_02）
- [warn] image_prompt_lint  None 多视图对齐初筛异常 CHAR_02/“濒死重伤态”：脚底线不齐：side(0.950) vs

## 🟡 虎妖（BEAST_01）
- [warn]  配音情绪弧(VEA)   镜头12·虎妖：台词含强情绪但配音标注「傲慢从容」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注
- [warn]  实体记忆(EMB)   本集有重复/核心实体（BEAST_01/伪死态, BEAST_01/复生态, CHAR_01, CHAR_01/囚
- [warn] image_prompt_lint  None 多视图对齐初筛异常 BEAST_01/“穿心复生态”：脚底线不齐：rear_three_qu

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
