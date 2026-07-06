# 生产复盘学习包

- episode: 第1集
- findings: 834
- learning_patterns: 94
- packaging_variants: 4
- vlm_clip_questions: 11

## Active Learning

| Dimension | Count | Examples |
|---|---:|---|
| prompt | 154 | 中文图片 prompt 缺字段：身份保持；中文图片 prompt 缺字段：镜头构图；中文图片 prompt 缺字段：动作瞬间 |
| 人物在场链 | 77 | 实体从上一 Clip 消失但缺出画/画外/换场解释：尸骸前景、荒野尸场。若是有意不连续，请把转场写清楚。；实体在下一 Clip 出现但缺入画/换场解释：CHAR_03、巨岩、黑色妖血。若是新入场，请把 entry_exit 写成机器真值。；实体从上一 Clip 消失但缺出画/画外/换场解释：CHAR_03、巨岩、黑色妖血。若是有意不连续，请把转场写清楚。 |
| 成本路由(K1) | 40 | 出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。；出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。；出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 |
| 场景/构图连续性 | 37 | 场景(O2): block=0 warn=0 ok=0 skipped=False；接缝接力: block=0 warn=0 ok=0 skipped=False；轴线视线(X1): block=0 warn=0 ok=0 skipped=False |
| 角色资产包 | 34 | 角色资产包分区不存在：prompts；角色资产包分区不存在：lora；角色资产包分区不存在：voice |
| 生成配方证据 | 32 | 出视频/第1集/视频/Clip_01_死人堆惊醒.mp4 是本集最终媒体，但 production_events.jsonl 缺对应 image/video g；出视频/第1集/视频/Clip_02_看见虎妖尸身.mp4 是本集最终媒体，但 production_events.jsonl 缺对应 image/video ；出视频/第1集/视频/Clip_03_镇魔司压迫交易.mp4 是本集最终媒体，但 production_events.jsonl 缺对应 image/video |
| 视频语义一致(VSEM) | 29 | DINOv2 whole-frame similarity is below the configured VSEM threshold.；DINOv2 whole-frame similarity is below the configured VSEM threshold.；DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| 物理尺寸对账 | 24 | 多人同框镜头（姜月初、虎妖、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎妖「远大于姜月初和裴长青，同框必须保；多人同框镜头（姜月初、虎妖、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎妖「远大于姜月初和裴长青，同框必须保；多人同框镜头（姜月初、虎妖、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎妖「远大于姜月初和裴长青，同框必须保 |
| 角色 DNA/形体一致性（脸/发型/身形/手） | 23 | 锚点门(N3): block=1 warn=2 ok=0 skipped=False；脸(G1): block=0 warn=3 ok=28 skipped=False；无脸崩坏(G1b): block=0 warn=0 ok=0 skipped=True |
| 角色一致性 | 20 | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂；含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂；含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| 生产操作一致性 | 17 | 生成配方(RCP): block=0 warn=2 ok=0 skipped=False；生成配方(RCP) detail: 脚本/第1集/storyboard.json 生成事件缺配方字段：mode, seed/seed_degrade, back；生成配方(RCP) detail: 合成/第1集/配音/voice_zh.wav 生成事件缺配方字段：seed/seed_degrade, backend_ve |
| 节奏密度 | 15 | 节奏密度(Rhythm): block=0 warn=3 ok=0 skipped=False；节奏密度(Rhythm) detail: 节奏/留存 advisory 总分偏低：57.4 定位产物：脚本/第1集/storyboard.json；visual[final_rhythm_density]: block=0 warn=0 skipped=True |
| 成片/包装一致性 | 13 | 成片统一(C1): block=0 warn=2 ok=0 skipped=False；成片统一(C1) detail: storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。；成片统一(C1) detail: 缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 定位产物：合成/第1集、 |
| 物料漂移预案 | 13 | 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 r；本集物料漂移风险 medium（分46）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。；本集物料漂移风险 medium（分34）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| 合规前置 | 12 | distribution_intent=internal_only；platform_review / localization / regulatory_fi；distribution_intent=internal_only；platform_review / localization / regulatory_fi；distribution_intent=internal_only；platform_review / localization / regulatory_fi |
| 结构化交互图谱(I2) | 12 | 接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。；接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。；接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 |
| 节奏密度(Rhythm) | 12 | [production一致性升级:重复同维度] 节奏/留存 advisory 总分偏低：57.4。如确认为可接受，写入 生产数据/consistency_adv；[production一致性升级:重复同维度] 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLI；[production一致性升级:重复同维度] 开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 死人堆惊醒』），疑慢热；开场镜时长 9.2s |
| 交互/接触因果一致性 | 11 | 交互接触(I1): block=0 warn=0 ok=0 skipped=False；持有账本(POS): block=0 warn=0 ok=0 skipped=False；结构化交互图谱(I2): block=1 warn=8 ok=0 skipped=False |
| 语义谱系(P0) | 11 | `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子；`钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子；`钩子` 留存标记未进入 storyboard 节奏/导演意图。 |
| 音画同步 | 10 | 音画同步(AV1): block=0 warn=0 ok=0 skipped=True；多人对话音画(DAV): block=0 warn=1 ok=0 skipped=False；多人对话音画(DAV) detail: 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺 |
| 天气时辰(W1) | 10 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 多模态漂移 | 9 | 多模态(P2): block=0 warn=0 ok=0 skipped=False；视频语义一致(VSEM): block=0 warn=8 ok=0 skipped=False；特效窜色(VFXC): block=0 warn=0 ok=0 skipped=True |
| 脸漂预案 | 9 | 本集脸漂风险 high（分95.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场；本集脸漂风险 high（分93.5·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场；本集脸漂风险 high（分90.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场 |
| 资产引用注册层 | 9 | 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变；建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变；建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变 |
| 现实覆盖 | 8 | 场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=image；场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=video；场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=compose |
| 导演运镜落实 | 8 | director_camera_plan_第1集.json（11 镜）的出图运镜注入已逐镜签收落实（director_camera_plan_applied_第；director_camera_plan_第1集.json（11 镜）的出视频运镜词汇已现身 prompt 包（命中 6/6：起幅、落幅、镜头运动、运动精修、动；director_camera_plan_第1集.json（11 镜）的出图运镜注入已逐镜签收落实（director_camera_plan_applied_第 |
| 语义继承 | 7 | 语义谱系(P0): block=0 warn=1 ok=0 skipped=False；语义谱系(P0) detail: `钩子` 留存标记未进入 storyboard 节奏/导演意图。 定位产物：脚本/第1集/storyboard.json、出图；称谓口头禅(A1): block=0 warn=0 ok=0 skipped=True |
| 锚点门(N3) | 7 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 打斗撞点(SPEC-APEX) | 7 | Clip_06（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `an；Clip_10（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `an；Clip_06（fight_exchange）：剪辑峰值钉在 [5.0]s，但本镜 continuity.anchors 无 keyframe 锚——跑 `an |
| 剧本可看性消费 | 6 | 出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。；出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。；出视频 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| 强配方Schema(RCP2) | 6 | [production一致性升级:重复同维度] 脚本/第1集/storyboard.json 强配方 schema 缺字段：prompt_sha256, ref；[production一致性升级:重复同维度] 合成/第1集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, ref；[production一致性升级:重复同维度] 脚本/第1集/storyboard.json 强配方 schema 缺字段：prompt_sha256, ref |
| 生成配方(RCP) | 6 | [production一致性升级:重复同维度] 脚本/第1集/storyboard.json 生成事件缺配方字段：mode, seed/seed_degrade；[production一致性升级:重复同维度] 合成/第1集/配音/voice_zh.wav 生成事件缺配方字段：seed/seed_degrade, back；[production一致性升级:重复同维度] 脚本/第1集/storyboard.json 生成事件缺配方字段：mode, seed/seed_degrade |
| 色温调色(GRADE1) | 6 | 图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.27 vs 场景中位 -0.091）；同场景调色横跳像换相机/；图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.243 vs 场景中位 -0.091）；同场景调色横跳像换；图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.246 vs 场景中位 -0.091）；同场景调色横跳像换相机 |
| 高动态成片证据(SPECV) | 6 | Clip_01 large_establishing 缺 Motion Control ready 输入：camera_path, depth_sequence；Clip_02 realm_portal 缺 Motion Control ready 输入：depth_sequence, camera_path, spat；Clip_06 fight_exchange 缺高动态后验证据字段：contact_map。 |
| 文字渲染(OCR1) | 6 | Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，O；Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，O；Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，O |
| 图中文字渲染一致性（OCR 校验） | 5 | 文字渲染(OCR1): block=0 warn=6 ok=0 skipped=False；文字渲染(OCR1) detail: Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_templ；文字渲染(OCR1) detail: Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_templ |
| style_consistency | 5 | 景别像素兜底：镜3 声明 CU(特写) 但 出图/第1集/图片/Clip03_end.png 实测脸占比 0.9% < 5%——画面里脸很小，渲染更像远景而非特；景别像素兜底：镜6 声明 CU(特写) 但 出图/第1集/图片/Clip06_end.png 实测脸占比 0.3% < 5%——画面里脸很小，渲染更像远景而非特；景别像素兜底：镜7 声明 CU(特写) 但 出图/第1集/图片/Clip07_end.png 实测脸占比 0.3% < 5%——画面里脸很小，渲染更像远景而非特 |
| 合规提示 | 5 | implicit_metadata.service_provider_code 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐；implicit_metadata.content_id 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐）；implicit_metadata.service_provider_code 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐 |
| 字幕正确性 | 4 | 字幕对齐(L1): block=0 warn=0 ok=0 skipped=True；译名一致(TX1): block=0 warn=0 ok=0 skipped=True；visual[subtitle_ocr]: block=0 warn=0 skipped=True |
| 音色一致性 | 4 | 音色声纹: block=0 warn=0 ok=0 skipped=False；配音情绪弧(VEA): block=0 warn=1 ok=0 skipped=False；口音方言(ACC): block=0 warn=0 ok=0 skipped=False |
| 配音 | 4 | 当前是占位配音驱动；允许出图 demo，但正式出视频前应换真实配音并重定时；先出视频后配音模式已放行占位时长进入出视频；后期补真音可能需要重出视频；先出视频后配音模式已放行占位时长进入出视频；后期补真音可能需要重出视频 |
| 剧本可看性合同 | 4 | script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。；script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。；script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。 |
| 跨集脸漂(G5) | 4 | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.427)→第2集(均值0.4429)，相对基线掉幅 -0.0159，且本集均值低于绝对下限——已系统性偏；CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4429)，相对基线掉幅 -0.0372，且本集均值低于绝对下限——已系统性；CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性 |
| fidelity-gate | 4 | fidelity-gate 未激活；vlm_verify --write 可在出图后跑 canonical 通过表。image 阶段不硬拦（出图后还没建 can；出视频后建议跑 vlm_verify --write 落 canonical 通过表，否则 compose/review gate 会 BLOCK。；终验 fidelity-gate 未激活但 N2D_ALLOW_DEGRADED_QC=1 放行（自负其责·已留痕）；脸一致分数未经 VLM canonical |
| 一致性总审 | 4 | 另有 28 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当；另有 97 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当；另有 107 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿 |
| 运动质量(MOT1) | 4 | [production一致性升级:重复同维度] 高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不；[production一致性升级:重复同维度] 高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不；高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不能只看 prompt/manifest，需用抽帧 |
| 风格一致性 | 3 | 风格(S1): block=0 warn=0 ok=31 skipped=False；糊/低质(N4): block=0 warn=0 ok=0 skipped=False；景深一致(DOF1): block=0 warn=0 ok=0 skipped=False |
| 状态百科 | 3 | 状态百科(P1): block=0 warn=0 ok=0 skipped=False；状态转场视频证据(ST1): block=0 warn=1 ok=0 skipped=False；状态转场视频证据(ST1) detail: 检测到 11 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 befor |
| UI/系统面板/HUD 一致性 | 3 | 系统面板(UI1): block=0 warn=2 ok=0 skipped=False；系统面板(UI1) detail: 检出 6 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 定位产；系统面板(UI1) detail: 检出 6 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级 |
| 证据等级 | 3 | 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主；证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主；证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主 |
| image_prompt_lint | 3 | 脸部锚弱信噪比 CHAR_01/囚犯初醒态「克制」（出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_克制.png）：脸占画面仅 8%（建议 ≥30%；脸部锚弱信噪比 CHAR_01/囚犯初醒态「震动」（出图/共享/图片/定妆_CHAR_01__囚犯初醒态_表情_震动.png）：脸占画面仅 11%（建议 ≥30；VLM 设定核验未运行（未配置 N2D_VLM_CMD）——服装剪裁/配饰/识别特征是否违反 canonical 设定未机检，缺左腕疤、月白窄袖画成交领这类设定 |
| 生视频后端连通性 | 3 | 生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录；生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录；生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录 |
| 脸(G1) | 3 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 物料新鲜度 | 3 | skill 有改动但仅限横切/QC/gate 层（n2d），不影响本阶段输入物料；如需可跑 `python3 skills/n2d-update/scripts；前期物料可能已过期：n2d, n2d-image, n2d-script, n2d-video, n2d-voice 自上次 skill 基线后有改动，可能影响；前期物料可能已过期：n2d, n2d-image, n2d-script, n2d-voice 自上次 skill 基线后有改动，可能影响本阶段（image）的 |
| 进度凭据对账 | 3 | 进度「出图」标 ✅ 却无新鲜通过的闸门凭据（gate_failed）：闸门未过：image 仍有 111 个 block 级问题（见 gate_findings；进度「视频」标 ✅ 却无新鲜通过的闸门凭据（gate_failed）：闸门未过：video 仍有 9 个 block 级问题（见 gate_findings_v；进度「成片」标 ✅ 却无新鲜通过的闸门凭据（stale）：闸门凭据已陈旧：compose 跑过后产物又变了（图/契约/storyboard 被改），旧绿不算数。 |
| 场景(O2) | 3 | ；； |
| 成片统一(C1) | 3 | 成片响度不贴目标：LUFS=-17.99 target=-16.0 true_peak=-2.13；storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。；缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 |
| 视觉契约继承 | 2 | 契约继承: block=0 warn=0 ok=5 skipped=False；契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md |
| 音乐母题/leitmotif 一致性 | 2 | 音乐母题(LM1): block=0 warn=0 ok=0 skipped=False；音乐衔接(BGM): block=0 warn=0 ok=0 skipped=False |
| 专项镜头模板 | 2 | 复杂镜头疑似「realm_portal」，但缺 template/template_contract；回 n2d-script 按 references/专项镜；复杂镜头疑似「realm_portal」，但缺 template/template_contract；回 n2d-script 按 references/专项镜 |
| 多人对话音画(DAV) | 2 | 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。；检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 |
| 物理因果链(CG1) | 2 | 视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。；视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 |
| character_consistency | 2 | 锚点门 N3：CHAR_01__囚犯初醒态 主参考非单张清晰正脸（非阻断）；锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸（非阻断） |
| 时长 | 2 | clip 总长 89.09s 与镜头时长累计 88.00s 差 1.09s；clip 总长 127.86s 与镜头时长累计 120.52s 差 7.34s |
| 风格化脸机检 | 2 | 基础视觉风格「冷灰写实3D国风漫剧」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N；基础视觉风格「冷灰写实3D国风漫剧」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N |
| 生图后端适配 | 2 | 统一标准已按「Codex」自动加载弥补措施：加载 reference_group：正/45度/侧/半身/脸锚/表情库按镜头风险选入参；近景/大表情/暗光镜强制同；适配层评分建议升档：当前「Codex」score=30，推荐「Seedream Universal Reference (访问入口 Seedream 官方 AP |
| 声音空间(ASP) | 2 | 声音空间条目 row_1 缺字段：location, room_tone/ambient_bed, reverb_profile, distance_persp；原生音画物理契约存在，但 acoustic_space 未标 native clip/声源映射；原生声、配音、BGM 混合后难查错声源/错混响。 |
| 系统面板(UI1) | 2 | 检出 6 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。；检出 6 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁 |
| 角色 DNA 一致性（服装/配饰） | 1 | 服装配色(N1): block=0 warn=0 ok=31 skipped=False |
| 关键镜候选 | 1 | 关键镜 best-of-N 未闭环：候选不足 EP01_CLIP01=actual0、EP01_CLIP02=actual0、EP01_CLIP03=actua |
| state_continuity | 1 | 本集出现累积状态关键词（伤口/觉醒）但无 visual_state_ledger.json——状态可能跨镜/跨集演进，建议跑 `python3 skills/n |
| 逐镜仲裁 | 1 | 1 个镜被多检测器同时报，已按证据族归并（severity 以最坏维度为准，勿按条数重复计=双计数）：Clip_08(2维/2族/4条·最坏block) |
| 原生音画 | 1 | 原生音画：当前 视频原生音轨=丢弃，但 native_speech 台词在 clip 原片音轨里；compose 将按有效策略自动「保留原片音轨」以免丢失原生台 |
| 原生音画字幕对齐 | 1 | 缺 native AV 字幕对齐 sidecar：原生音画说话镜不走前期配音 SRT，成片后必须用 whisperx 或等效词级对齐生成中文字幕并写 `kind |
| 原生音画声线一致性 | 1 | native voice identity 片段已登记，但声纹后端不可用：mode=no_speaker_backend precision=insuffici |
| 一致性满档账 | 1 | 本集本次 gate 凭 4 条降级 QC waiver 放行（交付边界·非满档一致性交付）：维度 fidelity-gate、原生音画声线一致性、现实覆盖。这些 |
| 参考规划落实 | 1 | 逐镜参考规划有 10 条行动项未确认落实（无持久主体 ID 后端×大变化镜 0 镜）：镜头 EP01_CLIP02、EP01_CLIP03、EP01_CLIP0 |
| 预防式合同 | 1 | pilot_release_gate: 第1集缺 pilot_acceptance；先用 2-3 个代表镜头验证脸/场景/动作/口型/接缝/路由。 |
| 主角装备库 | 1 | 该 VFX/法术资产看起来承担武器/法宝识别功能；若它是实体武器或主角本命法宝，请拆成 WEAPON_xx 实体资产 + VFX_xx 光效表现，并在角色 si |
| 视频 | 1 | clip 数 16 与 storyboard clips 11 不一致 |
| 原生音轨 | 1 | clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声 |
| 验收总账 | 1 | 一致性验收总账未清零：block=6 high=0 medium=10。review 不再按单镜看着像放行；请按 consistency_ledger 的交付域 |
| 配音情绪弧(VEA) | 1 | 镜头24·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 |
| 真值源(TRUTH) | 1 | 项目已有 identity_registry / asset_registry / storyboard / state ledger / generation |
| 多视角身份包(MVIEW) | 1 | 核心/长线角色 CHAR_01 缺 identity_eval_pack / multiview_identity_pack；后端或画风升级前缺正脸/45度/侧 |
| 实体记忆(EMB) | 1 | 本集有重复/核心实体（CHAR_01, CHAR_01/囚犯初醒态, CHAR_01/百妖谱能力触发态, CHAR_01__, CHAR_02, CHAR_02 |
| 状态转场视频证据(ST1) | 1 | 检测到 11 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 |
| 物理事件图(PHY) | 1 | 本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 |
| 世界一致性(WCS) | 1 | 已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，d |
| 视频证据完整性(EVID) | 1 | 本集已有媒体但缺 video_eval_manifest；视频 VLM/语义/物理/运动/相机/对白证据没有统一任务清单。 |
| 成片时间线探针(FT1) | 1 | 成片已存在但缺 final_timeline_probe；无法直接量片确认剪点亮度/色温跳、静音缝、响度突变。 |
| 系列包装(PKG) | 1 | 缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 |
| 一致性探针包(PROBE) | 1 | 项目已有多集或媒体产物，但缺 consistency_probe_pack；后端/模板升级没有固定哨兵小样。 |
| 系列调色(GRD) | 1 | 第1集 成片缺 合成/第1集/grade_applied.json 套用证据——compose 应留痕本集套用了哪版剧级调色，便于跨集对账。 |

## Packaging A/B

| Variant | Mode | Source Clip |
|---|---|---|
| COVER_01 | 冲突脸 | EP01_CLIP01 |
| COVER_02 | 危险反差 | EP01_CLIP01 |
| COVER_03 | 身份秘密 | EP01_CLIP01 |
| COVER_04 | 爽点动作 | EP01_CLIP01 |
