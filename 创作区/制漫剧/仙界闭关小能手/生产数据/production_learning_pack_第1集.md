# 生产复盘学习包

- episode: 第1集
- findings: 1230
- learning_patterns: 99
- packaging_variants: 4
- vlm_clip_questions: 25

## Active Learning

| Dimension | Count | Examples |
|---|---:|---|
| 状态百科(P1) | 385 | 贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜1 prompt 未见状态锁。；缺：十四岁瘦削少年、粗布杂役服、十四岁瘦削少；贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜2 prompt 未见状态锁。；缺：十四岁瘦削少年、粗布杂役服、十四岁瘦削少；贺平生 在镜1后应保持 `十四岁瘦削少年，粗布杂役服`，但镜4 prompt 未见状态锁。；缺：十四岁瘦削少年、粗布杂役服、十四岁瘦削少 |
| multimodal_continuity | 57 | outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip01_end.png DINO/CLIP cosine=0.35 < 0.55—；outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip01_first.png DINO/CLIP cosine=0.30 < 0.5；outfit 语义漂移疑似（调色板未报）：参考「贺平生」↔ 本镜 图片/Clip01_mid.png DINO/CLIP cosine=0.38 < 0.55— |
| image_prompt_lint | 53 | 镜头 1（`EP01_CLIP01` · 黑殿全景慢推 · ensemble_blocking）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1.4）。；镜头 2（`EP01_CLIP02` · 张老大问年龄 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/1；镜头 3（`EP01_CLIP03` · 贺平生答十四岁 · dialogue_shot_reverse）：近景/特写镜头缺乏物理镜头参数（如 85mm, f/ |
| 人物在场链 | 52 | 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CROWD_ZAYI。请在上一或下一 Clip 的 continuity.entry_e；连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CHAR_ZHANG_LAODA。请在上一或下一 Clip 的 continuity.e；连续接缝里实体在下一 Clip 凭空出现但未解释入画/进场/现身：CROWD_ZAYI。请在 continuity.entry_exit 写入画动作，或用空镜/ |
| 生成配方证据 | 50 | 出视频/第1集/视频/Clip_01_黑殿全景慢推.mp4 是本集最终媒体，但 production_events.jsonl 缺对应 image/video ；出视频/第1集/视频/Clip_02_张老大问年龄.mp4 是本集最终媒体，但 production_events.jsonl 缺对应 image/video ；出视频/第1集/视频/Clip_03_贺平生答十四岁.mp4 是本集最终媒体，但 production_events.jsonl 缺对应 image/video |
| 角色资产包 | 48 | 角色资产包分区不存在：reference；角色资产包分区不存在：prompts；角色资产包分区不存在：lora |
| 定妆对账 | 42 | 定妆图 定妆_太虚门长老_回忆背影_45度.png 属已登记角色但未进 identity_registry 任何 reference_group；face 机检；定妆图 定妆_太虚门长老_回忆背影_侧.png 属已登记角色但未进 identity_registry 任何 reference_group；face 机检会按；定妆图 定妆_太虚门长老_回忆背影_侧背.png 属已登记角色但未进 identity_registry 任何 reference_group；face 机检会 |
| 成本路由(K1) | 40 | 出图/共享/图片/定妆_秀竹峰杂役大殿.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。；出图/共享/图片/定妆_秀竹峰杂役院.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。；出图/共享/图片/定妆_后山山泉浅潭.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 |
| 资产引用注册层 | 30 | 建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变；建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变；建议为反复出现的场景增加 lighting_signature（色温/饱和度/主光位），以防跨镜色调突变 |
| 天气时辰(W1) | 30 | [production一致性升级:核心场景交付边界光照不连续] 光位锚声明主光在「left」，实测最亮区却偏「right」（注册 key_light_direc；[production一致性升级:核心场景交付边界光照不连续] 主光方位 right→left 硬翻转（疑光位跳·人比对相邻镜）。如确认为可接受，写入 生产数据；[production一致性升级:核心场景交付边界光照不连续] 光位锚声明主光在「left」，实测最亮区却偏「right」——实测光向与声明光位锚矛盾，人核对是 |
| 风格(S1) | 28 | [fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题；[fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题；[fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题 |
| 运动一致性 | 25 | 镜头运动未用结构化运镜词（推/拉/摇/移/升降/变焦/环绕/跟拍/甩镜/弧线/手持/固定…）：运镜是传达情绪与节奏最强的工具，自由散文下游模型常乱给。请从 CA；镜头运动未用结构化运镜词（推/拉/摇/移/升降/变焦/环绕/跟拍/甩镜/弧线/手持/固定…）：运镜是传达情绪与节奏最强的工具，自由散文下游模型常乱给。请从 CA；镜头运动未用结构化运镜词（推/拉/摇/移/升降/变焦/环绕/跟拍/甩镜/弧线/手持/固定…）：运镜是传达情绪与节奏最强的工具，自由散文下游模型常乱给。请从 CA |
| 物料漂移预案 | 24 | 本集物料漂移风险 high（分54）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位 r；本集物料漂移风险 medium（分48）：本集高频场景：登记 scene_atlas.base_views（G-I2 场景多机位锁：front + 反打/侧机位；本集物料漂移风险 medium（分40）：结构/件数强锁：参考图标清拓扑（单镜面/三件套/唯一圆口），逐镜 prompt 锁件数不增减。 |
| 中段锚帧 | 24 | storyboard 声明了 1 个锚帧（continuity.midframe/anchors）但视频 prompt 此 Clip 只引用了 0 个`**中段；storyboard 声明了 1 个锚帧（continuity.midframe/anchors）但视频 prompt 此 Clip 只引用了 0 个`**中段；storyboard 声明了 1 个锚帧（continuity.midframe/anchors）但视频 prompt 此 Clip 只引用了 0 个`**中段 |
| 脸(G1) | 23 | [fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题；[fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题；一致性审计发现问题 |
| 角色一致性 | 22 | 含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂；含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂；含角色镜头只看到主参考；侧脸/半身/全身锚或角色ID缺失时容易漂 |
| 合规前置 | 17 | 平台审核缺字段：platform（发布/合成前需补；当前 image 阶段不阻断）；平台审核缺字段：policy_profile（发布/合成前需补；当前 image 阶段不阻断）；pre_broadcast_review 不能停在 pending（境内投放须先过播前审核）（发布/合成前需补；当前 image 阶段不阻断） |
| 锚点门(N3) | 17 | 一致性审计发现问题；一致性审计发现问题；一致性审计发现问题 |
| 无脸崩坏(G1b) | 15 | 贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景；贺平生 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景；黑陶破盆 应在场但检测不到脸（脸糊/遮挡/崩脸），人判是否崩脸或换近景 |
| 节奏密度 | 12 | dashboard block[video/节奏密度(Rhythm)]: [production一致性升级:重复同维度] 节奏/留存 advisory 总分偏低；dashboard block[video/节奏密度(Rhythm)]: [production一致性升级:重复同维度] 连续 11 个长镜聚集（EP01_CL；dashboard block[video/节奏密度(Rhythm)]: [production一致性升级:重复同维度] 连续 11 个长镜聚集（EP01_CL |
| 服装配色(N1) | 12 | [fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题；[fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题；[fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题 |
| 视频语义一致(VSEM) | 12 | DINOv2 whole-frame similarity is below the configured VSEM threshold.；DINOv2 whole-frame similarity is below the configured VSEM threshold.；DINOv2 whole-frame similarity is below the configured VSEM threshold. |
| 交互接触(I1) | 12 | 物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。；物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。；物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 |
| 结构化交互图谱(I2) | 12 | 接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。；接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。；接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 |
| 脸漂预案 | 10 | 本集脸漂风险 high（分80.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场；本集脸漂风险 high（分67.9·multi_reference）：已补 ready 的同源表情参考：Codex-only 仍按 high 风险进入逐镜多参考；本集脸漂风险 high（分66.0·multi_reference）：GPT Image 2（渠道 Codex CLI） 无持久主体 ID：每镜必须喂定妆组/场 |
| character_consistency | 10 | 发型 H1 初筛：图片/Clip13_end.png（发色/发型轮廓离群，非阻断）；发型 H1 初筛：图片/Clip13_first.png（发色/发型轮廓离群，非阻断）；发型 H1 初筛：图片/Clip13_mid.png（发色/发型轮廓离群，非阻断） |
| 发型(H1) | 9 | [fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题；[fresh image_qc hard=0 已覆盖同类像素硬闸] 一致性审计发现问题；一致性审计发现问题 |
| 强配方Schema(RCP2) | 9 | [production一致性升级:重复同维度] 出图/第1集/图片/Clip03_外门遗孤_mid.png 强配方 schema 缺字段：input_finge；[production一致性升级:重复同维度] 合成/第1集/成片_第1集_zh.mp4 强配方 schema 缺字段：prompt_sha256, refer；[production一致性升级:重复同维度] 合成/第1集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, ref |
| 生成配方(RCP) | 9 | [production一致性升级:重复同维度] 出图/第1集/图片/Clip03_外门遗孤_mid.png 生成事件缺配方字段：mode, seed/seed_；[production一致性升级:重复同维度] 合成/第1集/成片_第1集_zh.mp4 生成事件缺配方字段：mode, seed/seed_degrade, ；[production一致性升级:重复同维度] 合成/第1集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade |
| 现实覆盖 | 8 | 场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=image；场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=video；场景现实验证器覆盖 0/2 真跑（DINOv2/OWLv2）；休眠 2（适用但后端没真出活）。stage=compose |
| outfit_consistency | 8 | 服装 N1 初筛：图片/Clip13_end.png（调色板离群，非阻断）；服装 N1 初筛：图片/Clip13_first.png（调色板离群，非阻断）；服装 N1 初筛：图片/Clip13_mid.png（调色板离群，非阻断） |
| 导演运镜落实 | 6 | director_camera_plan_第1集.json（12 镜）的出图运镜词汇已现身 prompt 包（命中 3/5：起幅、运动余量、导演意图）——文档级；director_camera_plan_第1集.json（12 镜）的出视频运镜词汇已现身 prompt 包（命中 6/6：起幅、落幅、镜头运动、运动精修、动；director_camera_plan_第1集.json（25 镜）的出图运镜注入已逐镜签收落实（director_camera_plan_applied_第 |
| 进度凭据对账 | 6 | 进度「出图」标 ✅ 却无新鲜通过的闸门凭据（stale）：闸门凭据已陈旧：image 跑过后产物又变了（图/契约/storyboard 被改），旧绿不算数。对当；进度「视频」标 ✅ 却无新鲜通过的闸门凭据（gate_failed）：闸门未过：video 仍有 4 个 block 级问题（见 gate_findings_v；进度「成片」标 ✅ 却无新鲜通过的闸门凭据（gate_failed）：闸门未过：compose 仍有 69 个 block 级问题（见 gate_finding |
| 场景平面(FP1) | 6 | [production一致性升级:重复同维度] 场景 秀竹峰杂役大殿 本集复用 9 镜但缺 location_spatial_memory 条目；多视角/反打时；[production一致性升级:重复同维度] 场景 秀竹峰水缸区 本集复用 2 镜但缺 location_spatial_memory 条目；多视角/反打时门；[production一致性升级:重复同维度] 场景 后山山泉浅潭 本集复用 6 镜但缺 location_spatial_memory 条目；多视角/反打时门 |
| style_consistency | 5 | 景别像素兜底：镜3 声明 CU(特写) 但 出图/第1集/图片/Clip03_end.png 实测脸占比 3.5% < 5%——画面里脸很小，渲染更像远景而非特；景别像素兜底：镜5 声明 CU(特写) 但 出图/第1集/图片/Clip05_end.png 实测脸占比 4.2% < 5%——画面里脸很小，渲染更像远景而非特；景别像素兜底：镜10 声明 CU(特写) 但 出图/第1集/图片/Clip10_end.png 实测脸占比 1.1% < 5%——画面里脸很小，渲染更像远景而非 |
| 伏笔兑现(SP1) | 5 | 伏笔「- 出点：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化」（第1集种下）无兑现集（坑没填）——补 payoff_ep 或标 sta；伏笔「- 入点：身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人掠走，全部用碎片化」（第1集种下）无兑现集（坑没填）——补 payoff_ep 或标 sta；伏笔「**分镜**：[0-6s] 身世快闪：父亲外出遇妖兽、母亲病榻、家中修真资源被人」（第1集种下）无兑现集（坑没填）——补 payoff_ep 或标 sta |
| 逐镜仲裁 | 4 | 2 个镜被多检测器同时报，已按证据族归并（severity 以最坏维度为准，勿按条数重复计=双计数）：Clip_13(4维/3族/9条·最坏warn)；Clip；1 个镜被多检测器同时报，已按证据族归并（severity 以最坏维度为准，勿按条数重复计=双计数）：Clip_07(2维/2族/3条·最坏block)；14 个镜被多检测器同时报，已按证据族归并（severity 以最坏维度为准，勿按条数重复计=双计数）：Clip_03(3维/3族/3条·最坏block)；Cl |
| fidelity-gate | 4 | fidelity-gate 未激活；vlm_verify --write 可在出图后跑 canonical 通过表。image 阶段不硬拦（出图后还没建 can；出视频后建议跑 vlm_verify --write 落 canonical 通过表，否则 compose/review gate 会 BLOCK。；终验须 fidelity-gate 激活——跑 vlm_verify --write 落 canonical 通过表。缺 VLM 语义判定时，脸(G1)的机械通 |
| 一致性总审 | 4 | 另有 122 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿；另有 88 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿当；另有 141 条一致性 WARN 未在此展开（已超过单次 12 条上限）——完整清单见 生产数据/consistency_findings_第1集.json，勿 |
| 合规提示 | 4 | implicit_metadata.service_provider_code 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐；implicit_metadata.content_id 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐）；implicit_metadata.service_provider_code 缺；无法自动写入完整元数据隐式标识（AI 标识非阻断；发布前按目标地区/平台补齐 |
| 场景/构图连续性 | 3 | dashboard block[compose/人物在场链]: 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CROWD_ZAYI。请；dashboard block[compose/人物在场链]: 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CHAR_ZHANG_L；dashboard block[compose/人物在场链]: 连续接缝里实体在下一 Clip 凭空出现但未解释入画/进场/现身：CROWD_ZAYI。请在 c |
| 证据等级 | 3 | 证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主；证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主；证据等级未达标(PENDING)：主体视频一致(S2V) 本可验到 embedding/pixel 级，本次只到结构/启发式级（torch-DINOv2 跨帧主 |
| 成片统一(C1) | 3 | 成片响度不贴目标：LUFS=-20.05 target=-16.0 true_peak=-0.66；storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。；缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 |
| 人审校准集(CAL) | 3 | [production一致性升级:交付边界] 检测到人审签收/覆盖记录，但缺 consistency_calibration.jsonl；误报/漏报没有进入全局；[production一致性升级:交付边界] 检测到人审签收/覆盖记录，但缺 consistency_calibration.jsonl；误报/漏报没有进入全局；检测到人审签收/覆盖记录，但缺 consistency_calibration.jsonl；误报/漏报没有进入全局校准集。 |
| 环境声(AMB) | 3 | [production一致性升级:交付边界] 本集涉 11 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，；[production一致性升级:交付边界] 本集涉 11 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，；本集涉 11 个场景但缺 设定库/ambient_map.json——reverb_profile 只管每场混响，环境底噪（雨/集市/宫廷）跨镜跨集连续性无锁； |
| 表情连续(EXP1) | 3 | Clip_10：角色 CHAR_HE_PINGSHENG 相邻镜情绪硬跳（喜→悲）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。；Clip_10：角色 CHAR_ZHANG_LAODA 相邻镜情绪硬跳（喜→悲）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。；Clip_21：角色 CHAR_HE_PINGSHENG 相邻镜情绪硬跳（悲→惊）——确认有节拍/事件依据，否则表演 OOC（情绪没有过渡镜）。 |
| 生图AI一致性 | 2 | production_events 第88行 provider「visual_inspection」不在官方后端清单内；请确认其为官方 API/CLI，并补充后；production_events 第88行 provider「visual_inspection」不在官方后端清单内；请确认其为官方 API/CLI，并补充后 |
| 景别阶梯 | 2 | 12 个镜写了 lens 但抽不出景别分级（EP01_CLIP03、EP01_CLIP04、EP01_CLIP05、EP01_CLIP07、EP01_CLIP1；12 个镜写了 lens 但抽不出景别分级（EP01_CLIP03、EP01_CLIP04、EP01_CLIP05、EP01_CLIP07、EP01_CLIP1 |
| 生视频后端连通性 | 2 | 生视频后端「即梦/Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI ；生视频后端「即梦/Dreamina」无法自动探活：`dreamina` 无自动探针（未导出健康端点 base url）——付费出视频前请人工确认：官方 CLI  |
| 多人对话音画(DAV) | 2 | 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。；检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 |
| 节奏密度(Rhythm) | 2 | [production一致性升级:重复同维度] 节奏/留存 advisory 总分偏低：67.8。如确认为可接受，写入 生产数据/consistency_adv；[production一致性升级:重复同维度] 连续 11 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLI |
| 系列留存(SERIES) | 2 | [冷开场质量] 第2集 冷开场质量极浅（score=0.00，depth=shallow）——前 2 拍缺冲突/悬念/反转信号，观众 3s 内无理由留步；补至少；[冷开场质量] 第2集 冷开场质量极浅（score=0.00，depth=shallow）——前 2 拍缺冲突/悬念/反转信号，观众 3s 内无理由留步；补至少 |
| 物料新鲜度 | 2 | 前期物料可能已过期：n2d, n2d-image, n2d-script 自上次 skill 基线后有改动，可能影响本阶段（video）的输入物料。出图/出视频；前期物料可能已过期：n2d, n2d-image, n2d-script 自上次 skill 基线后有改动，可能影响本阶段（image）的输入物料。出图/出视频 |
| 生图后端适配 | 2 | 统一标准已按「Codex CLI」自动加载弥补措施：加载 reference_group：正/45度/侧/半身/脸锚/表情库按镜头风险选入参；近景/大表情/暗光；适配层评分建议升档：当前「Codex CLI」score=30，推荐「Seedream Universal Reference (访问入口 Seedream 官 |
| 漂移预案 | 2 | 脸漂风险预案：本集无 high/医 medium 角色/物料（🟢 全低危）。；物料漂移风险预案：本集无 high/医 medium 角色/物料（🟢 全低危）。 |
| 视频证据完整性(EVID) | 2 | video_eval_manifest 已建立，但这些风险 sidecar 尚未写回：causal_event:生产数据/causal_event_graph_；这些视频证据 sidecar 存在但缺明细/判题结果：camera:生产数据/camera_trajectory_probe_第1集.json；motion:生 |
| 角色 DNA/形体一致性（脸/发型/身形/手） | 1 | dashboard block[video_preflight/出图落档QC]: 输入首帧 image_qc 仍有 49 项硬阻断（崩脸/接缝断/降级精度近景/ |
| 角色 DNA 一致性（服装/配饰） | 1 | 未采集该维度机器信号 |
| 字幕正确性 | 1 | 未采集该维度机器信号 |
| 音画同步 | 1 | 未采集该维度机器信号 |
| 音色一致性 | 1 | 未采集该维度机器信号 |
| 风格一致性 | 1 | 未采集该维度机器信号 |
| 语义继承 | 1 | dashboard block[video/视频语义一致(VSEM)]: DINOv2 whole-frame similarity is below the  |
| 状态百科 | 1 | 未采集该维度机器信号 |
| 多模态漂移 | 1 | 未采集该维度机器信号 |
| 视觉契约继承 | 1 | 未采集该维度机器信号 |
| 交互/接触因果一致性 | 1 | 未采集该维度机器信号 |
| 成片/包装一致性 | 1 | 未采集该维度机器信号 |
| 生产操作一致性 | 1 | 未采集该维度机器信号 |
| UI/系统面板/HUD 一致性 | 1 | 未采集该维度机器信号 |
| 音乐母题/leitmotif 一致性 | 1 | 未采集该维度机器信号 |
| 图中文字渲染一致性（OCR 校验） | 1 | 未采集该维度机器信号 |
| scene_consistency | 1 | 场景 O2 初筛：图片/Clip07_first.png 光色（非阻断） |
| state_continuity | 1 | 本集出现累积状态关键词（消耗/觉醒）但无 visual_state_ledger.json——状态可能跨镜/跨集演进，建议跑 `python3 skills/n |
| 原生音轨 | 1 | clip 含原生音轨；当前策略=丢弃，compose 会剥离以避免原生台词与配音双人声 |
| 出图落档QC | 1 | 输入首帧 image_qc 仍有 49 项硬阻断（崩脸/接缝断/降级精度近景/非法 CHAR）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n |
| 参考规划落实 | 1 | reference_plan_第1集.json 的 19 条行动项已有结构化落实证据，且 plan/prompt SHA 与当前文件一致。 |
| 预防式合同 | 1 | pilot_release_gate: 第1集缺 pilot_acceptance；先用 2-3 个代表镜头验证脸/场景/动作/口型/接缝/路由。 |
| 资产身份注册层 | 1 | 本集分镜/出图 prompt 引用了未登记的角色标记 `CHAR_xx`，但它不在 identity_registry.json 已登记 id 中——要么写错/ |
| 原生音画 | 1 | ffprobe 不可用，25 个 clip 无法探测原生音轨——「原生台词 + n2d-voice 配音 = 双人声」硬闸门无法校验，交付边界不放行。装 ffp |
| 验收总账 | 1 | 一致性验收总账未清零：block=7 high=0 medium=11。review 不再按单镜看着像放行；请按 consistency_ledger 的交付域 |
| 风格化脸机检 | 1 | 基础视觉风格「国漫写实」属于风格化/漫剧脸，当前脸一致性机检后端=arcface；建议项目级设置 `脸一致性机检后端: styleid` 并配置 N2D_STY |
| 场景(O2) | 1 | - |
| 景深一致(DOF1) | 1 | 图片/Clip02_first.png：景深档与同场景其它镜不一致——本镜偏浅景深(背景偏糊)（景深比 0.535 vs 场景中位 1.004）；同场景深焦↔浅 |
| 配音情绪弧(VEA) | 1 | 镜头11·旁白：台词含强情绪但配音标注「快闪压缩」归平淡(neutral)——配音会念平、情绪跟不上画面；改标注为 怒/惊恐/悲/喜 等，或确认确为克制反差。 |
| 音乐衔接(BGM) | 1 | 配乐相邻段速度两极硬接（slow→fast）且无过渡：「配器：低频鼓点、暗色弦乐、少量古琴/」→「22-38s：身世快闪用短促弦乐切片」；调性/速度whipla |
| 声音空间(ASP) | 1 | 缺 acoustic_space/room_tone/ambient_map；同一场景的 room tone、混响、远近感和环境声床无法跨 clip 复核。 |
| 物理因果链(CG1) | 1 | 视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 |
| 真值源(TRUTH) | 1 | 项目已有 identity_registry / asset_registry / storyboard / state ledger / generation |
| 实体记忆(EMB) | 1 | 本集有重复/核心实体（CHAR_HAN_LAOSAN, CHAR_HAN_LAOSAN__, CHAR_HE_PINGSHENG, CHAR_HE_PINGSH |
| 状态转场视频证据(ST1) | 1 | 检测到 25 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 |
| 物理事件图(PHY) | 1 | 本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 |
| 世界一致性(WCS) | 1 | 已有媒体或世界/物理/时序 sidecar，但缺 world_consistency_score；对象持久、关系稳定、因果合规、flicker 仍散在报告里，d |
| 成片时间线探针(FT1) | 1 | 成片已存在但缺 final_timeline_probe；无法直接量片确认剪点亮度/色温跳、静音缝、响度突变。 |
| 系列包装(PKG) | 1 | 缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 |
| 台词语域(D1) | 1 | 缺 dialogue_register/语域表；目前只能查称谓 + 文白横跳启发式，无法约束角色正式度、句长上限和禁用词。建议补 formality/sente |
| 一致性探针包(PROBE) | 1 | 项目已有多集或媒体产物，但缺 consistency_probe_pack；后端/模板升级没有固定哨兵小样。 |
| 系列调色(GRD) | 1 | 成片已出但缺 设定库/series_grade.json——剧级调色锁（LUT/白平衡/对比/饱和基线）缺位，逐集观感色温/对比易漂；tone_light_co |
| 叙事状态(NS1) | 1 | 本集有知识/位置叙事但缺 设定库/narrative_state_ledger.json——跨集易出『知道得太早/位置瞬移』硬伤。跑 n2d-script 的  |

## Packaging A/B

| Variant | Mode | Source Clip |
|---|---|---|
| COVER_01 | 冲突脸 | EP01_CLIP01 |
| COVER_02 | 危险反差 | EP01_CLIP01 |
| COVER_03 | 身份秘密 | EP01_CLIP01 |
| COVER_04 | 爽点动作 | EP01_CLIP01 |
