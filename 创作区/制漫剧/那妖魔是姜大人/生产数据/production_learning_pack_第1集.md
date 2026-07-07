# 生产复盘学习包

- episode: 第1集
- findings: 513
- learning_patterns: 63
- packaging_variants: 4
- vlm_clip_questions: 11

## Active Learning

| Dimension | Count | Examples |
|---|---:|---|
| image_prompt_lint | 59 | 镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以增强物理光学透视和电影感。；镜头 1（`EP01_CLIP01` · 死人堆惊醒 · ）：缺『身份锁定句』（多参考/编辑类后端最敏感的锁脸句）；镜头 2（`EP01_CLIP02` · 看见虎妖尸身 · realm_portal）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。建议补充以 |
| 片内时序(N2) | 48 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 场景/构图连续性 | 37 | 场景(O2): block=0 warn=0 ok=0 skipped=False；接缝接力: block=0 warn=0 ok=0 skipped=False；轴线视线(X1): block=0 warn=0 ok=0 skipped=False |
| multimodal_continuity | 33 | outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_end.png DINO/CLIP cosine=0；outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_first.png DINO/CLIP cosine；outfit 语义漂移疑似（调色板未报）：参考「CHAR_01__囚犯初醒态」↔ 本镜 图片/Clip01_mid.png DINO/CLIP cosine=0 |
| 物料漂移预案 | 27 | 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 r；本集物料漂移风险 medium（分46）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。；本集物料漂移风险 medium（分42）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| 人物在场链 | 22 | 实体从上一 Clip 消失但缺出画/画外/换场解释：尸骸前景、荒野尸场。若是有意不连续，请把转场写清楚。；实体在下一 Clip 出现但缺入画/换场解释：CHAR_03、巨岩、黑色妖血。若是新入场，请把 entry_exit 写成机器真值。；实体从上一 Clip 消失但缺出画/画外/换场解释：CHAR_03、巨岩、黑色妖血。若是有意不连续，请把转场写清楚。 |
| 角色一致性 | 20 | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂；含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂；含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| 角色 DNA/形体一致性（脸/发型/身形/手） | 17 | 锚点门(N3): block=0 warn=0 ok=0 skipped=True；脸(G1): block=0 warn=0 ok=33 skipped=False；无脸崩坏(G1b): block=0 warn=0 ok=0 skipped=True |
| 节奏密度 | 15 | 节奏密度(Rhythm): block=0 warn=3 ok=0 skipped=False；节奏密度(Rhythm) detail: 节奏/留存 advisory 总分偏低：57.4 定位产物：脚本/第1集/storyboard.json；visual[final_rhythm_density]: block=0 warn=1 skipped=False metrics={"clip_count" |
| 合规前置 | 12 | distribution_intent=internal_only；platform_review / localization / regulatory_fi；distribution_intent=internal_only；platform_review / localization / regulatory_fi；distribution_intent=internal_only；platform_review / localization / regulatory_fi |
| 天气时辰(W1) | 12 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 生产操作一致性 | 10 | 生成配方(RCP): block=0 warn=0 ok=0 skipped=False；强配方Schema(RCP2): block=0 warn=0 ok=0 skipped=False；成本路由(K1): block=0 warn=10 ok=0 skipped=False |
| 色温调色(GRADE1) | 10 | 图片/Clip07_end.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.27 vs 场景中位 -0.091）；同场景调色横跳像换相机/；图片/Clip07_first.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.243 vs 场景中位 -0.091）；同场景调色横跳像换；图片/Clip07_mid.png：色温/调色与同场景其它镜不一致——本镜偏暖(琥珀)（暖冷 0.246 vs 场景中位 -0.091）；同场景调色横跳像换相机 |
| 成本路由(K1) | 10 | 创作区/制漫剧/那妖魔是姜大人/合成/第1集/成片_第1集_zh.mp4 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。；创作区/制漫剧/那妖魔是姜大人/合成/第1集/成片_第1集_zh.mp4 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。；出图/第1集/图片/Clip06_mid_reaction.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 |
| 音画同步 | 9 | 音画同步(AV1): block=0 warn=0 ok=0 skipped=True；多人对话音画(DAV): block=0 warn=0 ok=0 skipped=False；mechanical[完整性] 第1集: 产物快照：配音句 28 · 视频片段 16 · 成片 3 |
| 脸漂预案 | 9 | 本集脸漂风险 high（分95.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场；本集脸漂风险 high（分93.5·multi_reference）：已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考；本集脸漂风险 high（分90.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场 |
| 定妆对账 | 9 | identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_狼妖群__常态_布料局部.png 磁盘缺失；补出该图或修 registr；identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_狼妖群__常态_手部局部.png 磁盘缺失；补出该图或修 registr；identity_registry 登记的定妆参考 出图/共享/图片/定妆_GROUP_飞鹰门众人__常态_布料局部.png 磁盘缺失；补出该图或修 regis |
| 多模态漂移 | 8 | 多模态(P2): block=0 warn=0 ok=0 skipped=False；视频语义一致(VSEM): block=0 warn=8 ok=0 skipped=False；特效窜色(VFXC): block=0 warn=0 ok=0 skipped=True |
| 现实覆盖 | 8 | 场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=image；场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=video；场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=compose |
| 导演运镜落实 | 8 | director_camera_plan_第1集.json（11 镜）的出图运镜注入已逐镜签收落实（director_camera_plan_applied_第；director_camera_plan_第1集.json（11 镜）的出视频运镜词汇已现身 prompt 包（命中 6/6：起幅、落幅、镜头运动、运动精修、动；director_camera_plan_第1集.json（11 镜）的出图运镜注入已逐镜签收落实（director_camera_plan_applied_第 |
| 视频语义一致(VSEM) | 8 | DINOv2 whole-frame similarity is below the configured VSEM threshold.；DINOv2 whole-frame similarity is below the configured VSEM threshold.；DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| 语义继承 | 7 | 语义谱系(P0): block=0 warn=0 ok=0 skipped=False；称谓口头禅(A1): block=0 warn=0 ok=0 skipped=True；台词语域(D1): block=0 warn=0 ok=0 skipped=True |
| 成片/包装一致性 | 6 | 成片统一(C1): block=0 warn=0 ok=0 skipped=False；成片时间线探针(FT1): block=0 warn=0 ok=0 skipped=False；系列包装(PKG): block=0 warn=0 ok=0 skipped=False |
| 剧本可看性消费 | 6 | 出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。；出图 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。；出视频 prompt 已签收消费 script_quality_contract（SHA fresh，字段完整）。 |
| style_consistency | 6 | 景别像素兜底：镜3 声明 CU(特写) 但 出图/第1集/图片/Clip03_end.png 实测脸占比 0.9% < 5%——画面里脸很小，渲染更像远景而非特；景别像素兜底：镜6 声明 CU(特写) 但 出图/第1集/图片/Clip06_end.png 实测脸占比 0.3% < 5%——画面里脸很小，渲染更像远景而非特；景别像素兜底：镜7 声明 CU(特写) 但 出图/第1集/图片/Clip07_end.png 实测脸占比 0.3% < 5%——画面里脸很小，渲染更像远景而非特 |
| 高动态成片证据(SPECV) | 6 | Clip_01 large_establishing 缺 Motion Control ready 输入：camera_path, depth_sequence；Clip_02 realm_portal 缺 Motion Control ready 输入：depth_sequence, camera_path, spat；Clip_06 fight_exchange 缺高动态后验证据字段：contact_map。 |
| 字幕正确性 | 5 | 字幕对齐(L1): block=0 warn=0 ok=0 skipped=True；译名一致(TX1): block=0 warn=0 ok=0 skipped=True；mechanical[字幕] 第1集: 检测到 fitted 配音轨 voice_*_fitted.wav：逐句原始时长清单 start 不再代表成片时间轴，跳 |
| 交互/接触因果一致性 | 5 | 交互接触(I1): block=0 warn=0 ok=0 skipped=False；持有账本(POS): block=0 warn=0 ok=0 skipped=False；结构化交互图谱(I2): block=0 warn=0 ok=0 skipped=False |
| 故事板 | 5 | start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_ta；start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_ta；start_state 与上一 Clip 的 end_state 不同；普通剪辑接缝允许，但若要尾帧无缝接力，请声明 handoff_mode=exact_ta |
| 跨集脸漂(G5) | 5 | CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性；CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性；CHAR_01__囚犯初醒态 跨集脸漂：第1集(均值0.4057)→第2集(均值0.4461)，相对基线掉幅 -0.0404，且本集均值低于绝对下限——已系统性 |
| 音色一致性 | 4 | 音色声纹: block=0 warn=0 ok=0 skipped=False；配音情绪弧(VEA): block=0 warn=1 ok=0 skipped=False；口音方言(ACC): block=0 warn=0 ok=0 skipped=False |
| 剧本可看性合同 | 4 | script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。；script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。；script_quality_contract 已通过：上游看点、首屏钩、留存承诺、逐镜戏剧功能可交接。 |
| 证据等级 | 4 | 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主；证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主；证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主 |
| 一致性总审 | 4 | 另有 5 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当作；另有 47 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当；另有 47 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当 |
| character_consistency | 4 | 锚点门 N3：CHAR_01__囚犯初醒态 主参考非单张清晰正脸（非阻断）；锚点门 N3：CHAR_01__镇魔司伪装态 主参考非单张清晰正脸（非阻断）；锚点门 N3：CHAR_02__濒死战损态 主参考非单张清晰正脸（非阻断） |
| 资产引用注册层 | 4 | 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变；建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变；建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变 |
| 风格一致性 | 3 | 风格(S1): block=0 warn=0 ok=33 skipped=False；糊/低质(N4): block=0 warn=0 ok=0 skipped=False；景深一致(DOF1): block=0 warn=0 ok=33 skipped=False |
| 生视频后端连通性 | 3 | 生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录；生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录；生视频后端「Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI 已登录 |
| 物料新鲜度 | 3 | skill 有改动但仅限横切/QC/gate 层（n2d），不影响本阶段输入物料；如需可跑 `python3 skills/n2d-update/scripts；前期物料可能已过期：n2d, n2d-image, n2d-script, n2d-video 自上次 skill 基线后有改动，可能影响本阶段（video）的；skill 有改动但仅限横切/QC/gate 层（n2d），不影响本阶段输入物料；如需可跑 `python3 skills/n2d-update/scripts |
| 节奏密度(Rhythm) | 3 | 节奏/留存 advisory 总分偏低：57.4；连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLI；开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 死人堆惊醒』），疑慢热；开场镜时长 9.2s > 5s，前3秒易掉留存 |
| 状态百科 | 2 | 状态百科(P1): block=0 warn=0 ok=0 skipped=False；状态转场视频证据(ST1): block=0 warn=0 ok=0 skipped=False |
| 视觉契约继承 | 2 | 契约继承: block=0 warn=0 ok=5 skipped=False；契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md |
| 音乐母题/leitmotif 一致性 | 2 | 音乐母题(LM1): block=0 warn=0 ok=0 skipped=False；音乐衔接(BGM): block=0 warn=0 ok=0 skipped=False |
| 物理尺寸对账 | 2 | 多人同框镜头（姜月初、虎妖、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎妖「远大于姜月初和裴长青，同框必须保；多人同框镜头（姜月初、虎妖、虎山神、裴长青）中 姜月初「比裴长青矮约一个头；与虎山神同框时体量差极大，突出凡人压迫感。」；虎妖「远大于姜月初和裴长青，同框必须保 |
| 配音情绪弧(VEA) | 2 | 镜头24·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。；镜头24·旁白：台词含强情绪但配音标注「压迫」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 |
| 后端跨集锁 | 2 | 1 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；确认；1 个 clip 的 shot_type 自然路由与 设定库/model_routes_baseline 不符，已按基线锚定（原后端降 fallback）；确认 |
| 视频 | 2 | clip 数 16 与 storyboard clips 11 不一致；final_timeline_probe 已验证成片时间线，raw split 数量差异；clip 数 16 与 storyboard clips 11 不一致；final_timeline_probe 已验证成片时间线，raw split 数量差异 |
| 原生音轨 | 2 | clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声；clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声 |
| 时长 | 2 | clip 总长 125.78s 与镜头时长累计 120.52s 差 5.26s；final_timeline_probe 已验证最终成片时长，raw split；clip 总长 125.78s 与镜头时长累计 120.52s 差 5.26s；final_timeline_probe 已验证最终成片时长，raw split |
| 一致性满档账 | 2 | 本集本次 gate 凭 3 条降级 QC waiver 放行（交付边界·非满档一致性交付）：维度 现实覆盖、证据等级。这些维度未在满档(full)精度下验证，全；本集本次 gate 凭 3 条降级 QC waiver 放行（交付边界·非满档一致性交付）：维度 现实覆盖、证据等级。这些维度未在满档(full)精度下验证，全 |
| 生图后端适配 | 2 | 统一标准已按「Codex」自动加载弥补措施：加载 reference_group + face_embedding：正/45度/侧/半身/脸锚/表情库按镜头风险；适配层评分建议升档：当前「Codex」score=15，推荐「Seedream Universal Reference (访问入口 Seedream 官方 AP |
| 运动质量(MOT1) | 2 | 高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不能只看 prompt/manifest，需用抽帧；高动作后验报告缺字段：speed_curve, spatial_path/distance_curve；动作镜不能只看 prompt/manifest，需用抽帧 |
| 角色 DNA 一致性（服装/配饰） | 1 | 服装配色(N1): block=0 warn=0 ok=33 skipped=False |
| UI/系统面板/HUD 一致性 | 1 | 系统面板(UI1): block=0 warn=0 ok=0 skipped=False |
| 图中文字渲染一致性（OCR 校验） | 1 | 文字渲染(OCR1): block=0 warn=0 ok=0 skipped=False |
| state_continuity | 1 | 本集出现累积状态关键词（伤口/觉醒）但无 visual_state_ledger.json——状态可能跨镜/跨集演进，建议跑 `python3 skills/n |
| 语义谱系(P0) | 1 | `钩子` 留存标记未进入 storyboard 节奏/导演意图。；缺：钩子 |
| 参考规划落实 | 1 | 逐镜参考规划有 10 条行动项未确认落实（无持久主体 ID 后端×大变化镜 0 镜）：镜头 EP01_CLIP02、EP01_CLIP03、EP01_CLIP0 |
| 主角装备库 | 1 | 该 VFX/法术资产看起来承担武器/法宝识别功能；若它是实体武器或主角本命法宝，请拆成 WEAPON_xx 实体资产 + VFX_xx 光效表现，并在角色 si |
| 合规提示 | 1 | explicit_label.status 尚非 done；成片未确认已落显式标签（AI 标识非阻断；发布前按目标地区/平台补齐） |
| 验收总账 | 1 | 一致性验收总账仍有 medium=24；可人工签收，但需逐项看角色/资产/镜头/声音跨集账本。 |
| 风格化脸机检 | 1 | 基础视觉风格「冷灰写实3D国风漫剧」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N |
| 视频VLM判题(VLM1) | 1 | 本机未配置重型 VLM runner；此文件仅占位并指向 manifest，不能作为 pass 结论。 |

## Packaging A/B

| Variant | Mode | Source Clip |
|---|---|---|
| COVER_01 | 冲突脸 | EP01_CLIP01 |
| COVER_02 | 危险反差 | EP01_CLIP01 |
| COVER_03 | 身份秘密 | EP01_CLIP01 |
| COVER_04 | 爽点动作 | EP01_CLIP01 |
