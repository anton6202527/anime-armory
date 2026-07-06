# 生产复盘学习包

- episode: 第2集
- findings: 577
- learning_patterns: 85
- packaging_variants: 4
- vlm_clip_questions: 10

## Active Learning

| Dimension | Count | Examples |
|---|---:|---|
| multimodal_continuity | 52 | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_end.png DINO/CLIP cosine=0；outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_first.png DINO/CLIP cosine；outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_mid.png DINO/CLIP cosine=0 |
| 成本路由(K1) | 40 | 脚本/第2集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。；出图/第2集/图片/Clip01_first.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。；出图/第2集/图片/Clip01_mid.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 |
| 场景/构图连续性 | 35 | 场景(O2): block=0 warn=1 ok=0 skipped=False；接缝接力: block=0 warn=0 ok=0 skipped=False；轴线视线(X1): block=0 warn=0 ok=0 skipped=False |
| 字幕正确性 | 31 | 字幕对齐(L1): block=0 warn=0 ok=0 skipped=True；译名一致(TX1): block=0 warn=0 ok=0 skipped=True；mechanical[字幕] 中文 cue#2: 起点漂移 +1.50s（字幕6.84/配音5.34） |
| 角色 DNA/形体一致性（脸/发型/身形/手） | 28 | 锚点门(N3): block=0 warn=0 ok=0 skipped=True；脸(G1): block=0 warn=0 ok=35 skipped=False；无脸崩坏(G1b): block=0 warn=0 ok=0 skipped=True |
| 物料漂移预案 | 25 | 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 r；本集物料漂移风险 medium（分46）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。；本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| 锚点门(N3) | 20 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 生产操作一致性 | 17 | 生成配方(RCP): block=0 warn=2 ok=0 skipped=False；生成配方(RCP) detail: 脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_vers；生成配方(RCP) detail: 合成/第2集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, back |
| 角色一致性 | 16 | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂；含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂；含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| 资产引用注册层 | 15 | 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变；建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变；建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变 |
| 成片/包装一致性 | 14 | 成片统一(C1): block=0 warn=3 ok=0 skipped=False；成片统一(C1) detail: 本集视频混用了 2 个 primary 后端，但缺色彩匹配报告；混剪易出现亮度/色温跳。 定位产物：出视频/第2集/promp；成片统一(C1) detail: storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。 |
| 运动一致性 | 14 | 镜头运动未用结构化运镜词（推/拉/摇/移/升降/变焦/环绕/跟拍/甩镜/弧线/手持/固定…）：运镜是传达情绪与节奏最强的工具，自由散文下游模型常乱给。请从 CA；镜头运动未用结构化运镜词（推/拉/摇/移/升降/变焦/环绕/跟拍/甩镜/弧线/手持/固定…）：运镜是传达情绪与节奏最强的工具，自由散文下游模型常乱给。请从 CA；镜头运动未用结构化运镜词（推/拉/摇/移/升降/变焦/环绕/跟拍/甩镜/弧线/手持/固定…）：运镜是传达情绪与节奏最强的工具，自由散文下游模型常乱给。请从 CA |
| 节奏密度 | 13 | 节奏密度(Rhythm): block=0 warn=2 ok=0 skipped=False；节奏密度(Rhythm) detail: 节奏/留存 advisory 总分偏低：66.0 定位产物：脚本/第2集/storyboard.json；visual[final_rhythm_density]: block=0 warn=1 skipped=False metrics={"clip_count" |
| 语义谱系(P0) | 11 | `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子；`钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子；`钩子` 留存标记未进入 storyboard 节奏/导演意图。 |
| 服装配色(N1) | 10 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 脸漂预案 | 9 | 本集脸漂风险 high（分100.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/；本集脸漂风险 high（分100.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/；本集脸漂风险 high（分99.4·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场 |
| 定妆对账 | 9 | identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_狼妖群__常态_布料局部.png 磁盘缺失；补出该图或修 registr；identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_狼妖群__常态_手部局部.png 磁盘缺失；补出该图或修 registr；identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_飞鹰门众人__常态_布料局部.png 磁盘缺失；补出该图或修 regis |
| 音画同步 | 8 | 音画同步(AV1): block=0 warn=0 ok=0 skipped=True；多人对话音画(DAV): block=0 warn=1 ok=0 skipped=False；多人对话音画(DAV) detail: 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺 |
| 合规前置 | 8 | distribution_intent=internal_only；platform_review / localization / regulatory_fi；distribution_intent=internal_only；platform_review / localization / regulatory_fi；distribution_intent=internal_only；platform_review / localization / regulatory_fi |
| 视频语义一致(VSEM) | 8 | [consistency_advisory_signoff 已签收·视频后验证据] DINOv2 whole-frame similarity is below；DINOv2 whole-frame similarity is below the configured VSEM threshold.；[consistency_advisory_signoff 已签收·视频后验证据] DINOv2 whole-frame similarity is below |
| 文字渲染(OCR1) | 8 | Clip_01 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，O；Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，O；Clip_04 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，O |
| 语义继承 | 7 | 语义谱系(P0): block=0 warn=1 ok=0 skipped=False；语义谱系(P0) detail: `钩子` 留存标记未进入 storyboard 节奏/导演意图。 定位产物：脚本/第2集/storyboard.json、出图；称谓口头禅(A1): block=0 warn=0 ok=0 skipped=True |
| 多模态漂移 | 7 | 多模态(P2): block=0 warn=0 ok=0 skipped=False；视频语义一致(VSEM): block=1 warn=1 ok=0 skipped=False；特效窜色(VFXC): block=0 warn=0 ok=0 skipped=True |
| 交互/接触因果一致性 | 7 | 交互接触(I1): block=0 warn=0 ok=0 skipped=False；持有账本(POS): block=0 warn=0 ok=0 skipped=False；结构化交互图谱(I2): block=0 warn=0 ok=0 skipped=False |
| 剧本可看性消费 | 7 | 出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。；出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。；出视频 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| 剧本可看性合同 | 6 | script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。；script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。；script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。 |
| 表情一致性 | 6 | expression_span=大 但本镜景别未识别为近景/特写/反打——跨情绪大表情通常是脸戏；若确为远景/空镜风险较低，否则复核景别或下调跨度档。；expression_span=大 但本镜景别未识别为近景/特写/反打——跨情绪大表情通常是脸戏；若确为远景/空镜风险较低，否则复核景别或下调跨度档。；expression_span=大 但本镜景别未识别为近景/特写/反打——跨情绪大表情通常是脸戏；若确为远景/空镜风险较低，否则复核景别或下调跨度档。 |
| 色温调色(GRADE1) | 6 | 图片/Clip06_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076 vs 场景中位 -0.116）；同场景调色横跳像换相机；图片/Clip06_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076 vs 场景中位 -0.116）；同场景调色横跳像换；图片/Clip06_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.076 vs 场景中位 -0.116）；同场景调色横跳像换相机 |
| 图中文字渲染一致性（OCR 校验） | 5 | 文字渲染(OCR1): block=0 warn=8 ok=0 skipped=False；文字渲染(OCR1) detail: Clip_01 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_templ；文字渲染(OCR1) detail: Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_templ |
| 合规提示 | 5 | implicit_metadata.service_provider_code 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐；implicit_metadata.content_id 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐）；implicit_metadata.service_provider_code 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐 |
| 跨集脸漂(G5) | 5 | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性；CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性；CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性 |
| 场景(O2) | 5 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 多人对话音画(DAV) | 5 | 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。；检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。；检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 |
| character_consistency | 5 | 跨集脸漂移趋势 medium：CHAR_01__囚犯初醒态 第1集→第2集 mean 0.4057→0.4461 drop=-0.0404。high 级系统性退；锚点门 N3：CHAR_01__囚犯初醒态 主参考非单张清晰正脸（非阻断）；锚点门 N3：CHAR_01__镇魔司伪装态 主参考非单张清晰正脸（非阻断） |
| 高动态成片证据(SPECV) | 5 | Clip_03 fight_exchange 缺高动态后验证据字段：contact_map。；Clip_03 fight_exchange 动作关键维未实测：limb_artifact（光流方向对账/肢体畸变/运动模糊）。按 sampling_plan ；Clip_04 fight_exchange 缺高动态后验证据字段：contact_map。 |
| 音色一致性 | 4 | 音色声纹: block=0 warn=0 ok=0 skipped=False；配音情绪弧(VEA): block=0 warn=2 ok=0 skipped=False；口音方言(ACC): block=0 warn=0 ok=0 skipped=False |
| 配音 | 4 | 先出视频后配音模式已放行占位时长进入出视频；后期补真音可能需要重出视频；先出视频后配音模式已放行占位时长进入出视频；后期补真音可能需要重出视频；当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时 |
| 物料新鲜度 | 4 | 前期物料可能已过期：n2d, n2d-image, n2d-script 自上次 skill 基线后有改动，可能影响本阶段（video_prompt）的输入物料；前期物料可能已过期：n2d, n2d-image, n2d-script, n2d-video 自上次 skill 基线后有改动，可能影响本阶段（video）的；前期物料可能已过期：n2d, n2d-image, n2d-script 自上次 skill 基线后有改动，可能影响本阶段（image）的输入物料。出图/出视频 |
| 主角装备库 | 4 | 该 VFX/法术资产看起来承担武器/法宝识别功能；若它是实体武器或主角本命法宝，请拆成 WEAPON_xx 实体资产 + VFX_xx 光效表现，并在角色 si；该 VFX/法术资产看起来承担武器/法宝识别功能；若它是实体武器或主角本命法宝，请拆成 WEAPON_xx 实体资产 + VFX_xx 光效表现，并在角色 si；该 VFX/法术资产看起来承担武器/法宝识别功能；若它是实体武器或主角本命法宝，请拆成 WEAPON_xx 实体资产 + VFX_xx 光效表现，并在角色 si |
| 逐镜仲裁 | 4 | 2 个镜被多检测器同时报，已按证据族归并（severity 以最坏维度为准，勿按条数重复计=双计数）：Clip_07(2维/2族/2条·最坏warn)；Clip；1 个镜被多检测器同时报，已按证据族归并（severity 以最坏维度为准，勿按条数重复计=双计数）：Clip_07(2维/2族/2条·最坏warn)；2 个镜被多检测器同时报，已按证据族归并（severity 以最坏维度为准，勿按条数重复计=双计数）：Clip_07(2维/2族/2条·最坏warn)；Clip |
| 现实覆盖 | 4 | 场景现实验证器覆盖 2/2 真跑（DINOv2/OWLv2）；休眠 0（适用但后端没真出活）。stage=compose；场景现实验证器覆盖 2/2 真跑（DINOv2/OWLv2）；休眠 0（适用但后端没真出活）。stage=image；场景现实验证器覆盖 2/2 真跑（DINOv2/OWLv2）；休眠 0（适用但后端没真出活）。stage=video |
| 一致性总审 | 4 | 另有 83 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第2集.json，勿当；另有 29 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第2集.json，勿当；另有 83 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第2集.json，勿当 |
| image_prompt_lint | 4 | 脸部锚弱信噪比 CHAR_04/常态「基础」（出图/共享/图片/定妆_CHAR_04__常态.png）：脸占画面仅 1%（建议 ≥30%，至少 ≥12%）——弱；脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅；脸部锚弱信噪比 CHAR_05/常态「CHAR_05/常态 同源脸锚」（出图/共享/图片/定妆_CHAR_05__常态_脸部特写_脸锚裁切.png）：脸占画面仅 |
| 风格一致性 | 3 | 风格(S1): block=0 warn=0 ok=35 skipped=False；糊/低质(N4): block=0 warn=0 ok=0 skipped=False；景深一致(DOF1): block=0 warn=0 ok=35 skipped=False |
| 状态百科 | 3 | 状态百科(P1): block=0 warn=0 ok=0 skipped=False；状态转场视频证据(ST1): block=0 warn=1 ok=0 skipped=False；状态转场视频证据(ST1) detail: 检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 befor |
| UI/系统面板/HUD 一致性 | 3 | 系统面板(UI1): block=0 warn=2 ok=0 skipped=False；系统面板(UI1) detail: 检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 定位产；系统面板(UI1) detail: 检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级 |
| 生视频后端连通性 | 3 | 生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录；生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录；生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录 |
| 脸漂报告新鲜度 | 3 | 脸漂实测报告缺失/未实测（identity_drift_report.json 不存在或 available≠true），但历史集已出图 ['第1集']：跨集脸；脸漂实测报告缺失/未实测（identity_drift_report.json 不存在或 available≠true），但历史集已出图 ['第1集']：跨集脸；脸漂实测报告缺失/未实测（identity_drift_report.json 不存在或 available≠true），但历史集已出图 ['第1集']：跨集脸 |
| 成片统一(C1) | 3 | 本集视频混用了 2 个 primary 后端，但缺色彩匹配报告；混剪易出现亮度/色温跳。；storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。；缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 |
| 视觉契约继承 | 2 | 契约继承: block=0 warn=0 ok=5 skipped=False；契约继承 detail: 逐字一致 定位产物：出图/第2集/prompt/00_总览.md、出视频/第2集/prompt/00_总览.md |
| 音乐母题/leitmotif 一致性 | 2 | 音乐母题(LM1): block=0 warn=0 ok=0 skipped=False；音乐衔接(BGM): block=0 warn=0 ok=0 skipped=False |
| 视频 | 2 | clip 数 11 与 storyboard clips 10 不一致；clip 数 11 与 storyboard clips 10 不一致 |
| 时长 | 2 | clip 总长 114.68s 与镜头时长累计 113.23s 差 1.45s；clip 总长 114.68s 与镜头时长累计 113.23s 差 1.45s |
| 生图后端适配 | 2 | 统一标准已按「Codex」自动加载弥补措施：加载 reference_group：正/45度/侧/半身/脸锚/表情库按镜头风险选入参；近景/大表情/暗光镜强制同；适配层评分建议升档：当前「Codex」score=30，推荐「Seedream Universal Reference (访问入口 Seedream 官方 AP |
| 跨集色调 | 2 | 本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画；本集色调基线基调「冷青灰夜色为主」与打样集 第1集「冷青灰荒野+土褐枯草+黑血暗红」不一致——色调可逐集细化但基调应跨集恒定；以打样集为准或确认有意改（防整部画 |
| 景别阶梯 | 2 | 连续 3 镜同景别 CU（EP02_CLIP07→EP02_CLIP09）——景别阶梯单调、缺远近或机位变化；按导演意图穿插不同景别/机位（或确认为设计内的同景；连续 3 镜同景别 CU（EP02_CLIP07→EP02_CLIP09）——景别阶梯单调、缺远近或机位变化；按导演意图穿插不同景别/机位（或确认为设计内的同景 |
| 物理尺寸对账 | 2 | 多人同框镜头（姜月初、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎山神「远大于姜月初和裴长青，同框必须保持体；多人同框镜头（姜月初、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎山神「远大于姜月初和裴长青，同框必须保持体 |
| 物件状态(OST) | 2 | 道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual；道具『横刀』状态前后矛盾：EP02_CLIP07 写「满」（满），EP02_CLIP08 写「空」（空），中间无已声明的状态转换——若确有变化请在 visual |
| 物理因果链(CG1) | 2 | 视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。；视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 |
| 真值源(TRUTH) | 2 | 项目已有 identity_registry / asset_registry / storyboard / state ledger / generation；项目已有 identity_registry / asset_registry / storyboard / state ledger / generation |
| style_consistency | 2 | 景别像素兜底：镜8 声明 CU(特写) 但 出图/第2集/图片/Clip08_end.png 实测脸占比 3.5% < 5%——画面里脸很小，渲染更像远景而非特；景别像素兜底：镜9 声明 CU(特写) 但 出图/第2集/图片/Clip09_a1.png 实测脸占比 0.8% < 5%——画面里脸很小，渲染更像远景而非特写 |
| outfit_consistency | 2 | 服装 N1 初筛：图片/Clip04_end.png（调色板离群，非阻断）；服装 N1 初筛：图片/Clip10_mid.png（调色板离群，非阻断） |
| 配音情绪弧(VEA) | 2 | 镜头13·旁白：台词含强情绪但配音标注「骤停」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。；镜头27·姜月初：台词含强情绪但配音标注「低哑」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 |
| 声音空间(ASP) | 2 | 声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_persp；原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。 |
| 节奏密度(Rhythm) | 2 | 节奏/留存 advisory 总分偏低：66.0；连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CLIP04→EP02_CLIP05→EP02_CLIP |
| 生成配方(RCP) | 2 | 脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version,；合成/第2集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_ |
| 强配方Schema(RCP2) | 2 | 脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/refer；合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/ref |
| 系统面板(UI1) | 2 | 检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。；检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁 |
| 角色 DNA 一致性（服装/配饰） | 1 | 服装配色(N1): block=0 warn=2 ok=33 skipped=False |
| 参考规划落实 | 1 | 逐镜参考规划有 8 条行动项未确认落实（无持久主体 ID 后端×大变化镜 0 镜）：镜头 EP02_CLIP01、EP02_CLIP02、EP02_CLIP03 |
| scene_consistency | 1 | 场景 O2 初筛：图片/Clip07_mid.png 光色（非阻断） |
| state_continuity | 1 | 本集出现累积状态关键词（升级/染血/泪痕/消耗）但无 visual_state_ledger.json——状态可能跨镜/跨集演进，建议跑 `python3 sk |
| 验收总账 | 1 | 一致性验收总账未清零：block=3 high=0 medium=24。review 不再按单镜看着像放行；请按 consistency_ledger 的交付域 |
| 风格化脸机检 | 1 | 基础视觉风格「冷灰写实3D国风漫剧」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N |
| 多视角身份包(MVIEW) | 1 | 核心/长线角色 CHAR_01 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧 |
| 实体记忆(EMB) | 1 | 本集有重复/核心实体（CHAR_01, CHAR_01/猛虎快刀圆满态, CHAR_01/脱力态, CHAR_01/血尘战损态, CHAR_01__, CHAR |
| 状态转场视频证据(ST1) | 1 | 检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 |
| 物理事件图(PHY) | 1 | 本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 |
| 世界一致性(WCS) | 1 | 已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，d |
| 视频证据完整性(EVID) | 1 | 本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 |
| 成片时间线探针(FT1) | 1 | 成片已存在但缺 final_timeline_probe；无法直接量片确认剪点亮度/色温跳、静音缝、响度突变。 |
| 系列包装(PKG) | 1 | 缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 |
| 一致性探针包(PROBE) | 1 | 项目已有多集或媒体产物，但缺 consistency_probe_pack；后端/模板升级没有固定哨兵小样。 |
| 系列调色(GRD) | 1 | 第2集 成片缺 合成/第2集/grade_applied.json 套用证据——compose 应留痕本集套用了哪版剧级调色，便于跨集对账。 |
| 叙事状态(NS1) | 1 | 本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的  |

## Packaging A/B

| Variant | Mode | Source Clip |
|---|---|---|
| COVER_01 | 冲突脸 | EP02_CLIP01 |
| COVER_02 | 危险反差 | EP02_CLIP01 |
| COVER_03 | 身份秘密 | EP02_CLIP01 |
| COVER_04 | 爽点动作 | EP02_CLIP01 |
