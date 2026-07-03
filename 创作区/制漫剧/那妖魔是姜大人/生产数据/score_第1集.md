# n2d 自动审片评分

- 集：第1集
- Profile：demo
- 总分：52 / 100
- 阈值：50
- 状态：需复核
- 生成时间：2026-07-01T21:12:59+00:00

## 长篇叙事一致性 KPI（报告型·非扣分·NarrLV/DirectorBench 轴）

- 叙事连续性：0.8577 · profile demo · 参考线 0.6 → **达标**（集数 10）
- 子分：伏笔已回收 0.3333 · 伏笔已规划 1.0 · 冷开场链 None · 反套路 1.0 · 情绪起伏 0.9286 · 叙事原子 1.0 · 实体排程 1.0
- 基准：长篇叙事一致性参 NarrLV（Temporal Narrative Atom）/ EntityBench（per-shot entity schedule）/DirectorBench（长视频多代理诊断）；report-only·非扣分·子信号为确定性近似，不替代人读

## 维度

| 维度 | 权重 | 分数 | 状态 | block | warn | 回流 stage |
|---|---:|---:|---|---:|---:|---|
| 角色 DNA/形体一致性（脸/发型/身形/手） | 10 | 98 | 需复核 | 0 | 0 | image |
| 角色 DNA 一致性（服装/配饰） | 12 | 100 | 通过 | 0 | 0 | image |
| 场景/构图连续性 | 12 | 0 | 需复核 | 0 | 30 | image |
| 字幕正确性 | 16 | 70 | 缺数据 | 0 | 0 | script_stage2 |
| 音画同步 | 16 | 14 | 需复核 | 0 | 7 | compose |
| 音色一致性 | 10 | 88 | 需复核 | 0 | 1 | voice |
| 节奏密度 | 12 | 40 | 需复核 | 0 | 5 | script_stage2 |
| 风格一致性 | 12 | 88 | 需复核 | 0 | 1 | image |
| 语义继承 | 8 | 88 | 需复核 | 0 | 1 | script_stage2 |
| 状态百科 | 8 | 88 | 需复核 | 0 | 1 | image |
| 多模态漂移 | 8 | 0 | 需复核 | 0 | 9 | image |
| 视觉契约继承 | 8 | 100 | 通过 | 0 | 0 | video_prompt |
| 交互/接触因果一致性 | 8 | 0 | 需复核 | 0 | 12 | script_stage2 |
| 成片/包装一致性 | 8 | 0 | 需复核 | 0 | 9 | compose |
| 生产操作一致性 | 6 | 0 | 需复核 | 0 | 43 | review |
| UI/系统面板/HUD 一致性 | 6 | 76 | 需复核 | 0 | 2 | image |
| 音乐母题/leitmotif 一致性 | 6 | 28 | 需复核 | 0 | 6 | script_stage1 |
| 图中文字渲染一致性（OCR 校验） | 8 | 28 | 需复核 | 0 | 6 | image |

## 自动回流建议

- `image`：场景/构图连续性、多模态漂移、图中文字渲染一致性（OCR 校验）；回 n2d-image 修场景定妆、光位锚、轴线视线、时辰天气、字幕安全区或尾帧；必要时回 n2d-video 重出接缝/相机轨迹/运动质量 clip。；回 n2d-image 或 n2d-video 按离群道具/场景/法宝参考组只重出受影响镜头；必要时补资产 taxonomy 和视频侧 embedding probe。；回 n2d-image 重出图中文字渲染错的镜头：系统面板数值/属性、牌匾/匾额/招牌、卷轴书页等中文字若 OCR 实读与预期不符（错字/缺笔/乱码/数值不对），优先改用独立文字图层叠加而非让模型画；预期文字来自 ui_asset_registry.text_template 或 storyboard 声明，校验经 text_render sidecar。；定位镜头：Clip_01、Clip_02、Clip_03、Clip_04、Clip_05、Clip_07、Clip_08、Clip_09；定位产物：出视频/第1集、出视频/第1集/control/Clip_01/motion_control_manifest.json、出视频/第1集、出视频/第1集/control/Clip_01/motion_control_manifest.json、生产数据/spectacle_video_qc_第1集.json、出视频/第1集、出视频/第1集/control/Clip_02/motion_control_manifest.json、出视频/第1集、出视频/第1集/control/Clip_02/motion_control_manifest.json、生产数据/spectacle_video_qc_第1集.json、出视频/第1集、出图/第1集/图片/Clip_01.png、出图/第1集/图片/Clip_02.png、出视频/第1集/video_semantic_consistency.json
- `compose`：音画同步、成片/包装一致性；回 n2d-compose 对齐配音轨、clip 时长、原生音轨策略和多人对话说话人结构；若时长源头错，回 n2d-script 阶段2。；回 n2d-compose 统一响度、混剪色彩、BGM/room tone、字幕样式、成片时间线探针与系列包装；缺规范先补 series_packaging。系列调色(GRD)漂移补/复用 series_grade.json 的 LUT/白平衡/对比基线；环境声(AMB)漂移补/复用 ambient_map.json 的每场环境声床。；定位镜头：Clip_11；定位产物：合成/第1集、出视频/第1集/视频/Clip_01_死人堆惊醒.mp4、出视频/第1集/视频/Clip_11.mp4、合成/第1集、出视频/第1集/prompt/video_model_routes.json、出视频/第1集/prompt/video_model_routes.json、合成/第1集、脚本/第1集/storyboard.json、合成/第1集、出视频/第1集/prompt/video_model_routes.json、合成/第1集/final_timeline_probe.json、合成/第1集、设定库/series_packaging.json、合成/交付
- `script_stage2`：节奏密度、交互/接触因果一致性；回 n2d-script 阶段2重切镜头时长曲线、补钩子/爽点/集尾 cliffhanger。；回 n2d-script 阶段2补 interaction_graph/contact_graph、左右手/持有状态、持有账本、递交/释放因果和 causal_event_graph；必要时重跑 n2d-model-router 补 motion_control。；定位镜头：EP01_CLIP01、Clip_01、EP01_CLIP02、Clip_02、EP01_CLIP03、Clip_03、EP01_CLIP04、Clip_04、EP01_CLIP05、Clip_05、EP01_CLIP06、Clip_06、EP01_CLIP07、Clip_07、EP01_CLIP08、Clip_08、EP01_CLIP09、Clip_09、EP01_CLIP10、Clip_10、EP01_CLIP11、Clip_11；定位产物：脚本/第1集/storyboard.json、脚本/第1集/storyboard.json、出视频/第1集/prompt/video_model_routes.json、脚本/第1集/storyboard.json、生产数据/causal_event_graph_第1集.json、脚本/第1集/storyboard.json、出视频/第1集、生产数据/causal_event_graph_第1集.json
- `review`：生产操作一致性；回对应 image/video/compose/review 生成节点补 production_events、recipe_hash、强配方 schema、后端/seed/参考图记录、成本、重试原因、人审校准集与一致性 probe；不得让未登记媒体进入交付。；定位产物：出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png、出视频/第1集/prompt/video_model_routes.json、出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png、出视频/第1集/prompt/video_model_routes.json、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png、出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png、出视频/第1集/prompt/video_model_routes.json、出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png、设定库/consistency_probe_pack.json、出视频/第1集、合成/第1集、生产数据/*_第1集.json
- `script_stage1`：音乐母题/leitmotif 一致性；回 n2d-script 阶段1（bgm）或 n2d-compose 复用 leitmotif_registry 的角色/情绪主题动机；同一角色/主题跨集 BGM 母题应可复现且不串用，缺登记先补 leitmotif_registry。；定位产物：设定库/leitmotif_registry.json、脚本/第1集/storyboard.json

## 数据采集建议

- `n2d-score`：字幕正确性；缺机器信号，先采集 consistency/mechanical/visual checks；不要在缺证据时直接返工。

## 证据

### 角色 DNA/形体一致性（脸/发型/身形/手）
- 锚点门(N3): block=0 warn=0 ok=0 skipped=True
- 脸(G1): block=0 warn=0 ok=33 skipped=False
- 无脸崩坏(G1b): block=0 warn=0 ok=0 skipped=True
- 跨集脸漂(G5): block=0 warn=0 ok=0 skipped=True
- 发型(H1): block=0 warn=0 ok=33 skipped=False
- 辨识标记(MK1): block=0 warn=0 ok=0 skipped=True
- 片内时序(N2): block=0 warn=0 ok=11 skipped=False
- 手部/解剖(N5): block=0 warn=0 ok=0 skipped=True
- ...另有 10 条
### 角色 DNA 一致性（服装/配饰）
- 服装配色(N1): block=0 warn=0 ok=33 skipped=False
### 场景/构图连续性
- 场景(O2): block=0 warn=0 ok=0 skipped=False
- 接缝接力: block=0 warn=0 ok=0 skipped=False
- 轴线视线(X1): block=0 warn=0 ok=0 skipped=False
- 天气时辰(W1): block=0 warn=5 ok=0 skipped=False
- 色温调色(GRADE1): block=0 warn=0 ok=0 skipped=True
- 字幕安全区(L2): block=0 warn=0 ok=0 skipped=False
- 空间站位(B1): block=0 warn=0 ok=0 skipped=False
- 物件常驻(O3): block=0 warn=0 ok=0 skipped=False
- ...另有 22 条
### 字幕正确性
- 字幕对齐(L1): block=0 warn=0 ok=0 skipped=True
- 译名一致(TX1): block=0 warn=0 ok=0 skipped=True
- visual[subtitle_ocr]: block=0 warn=0 skipped=True
- visual[subtitle_ocr] 缺 pytesseract/Pillow，字幕 OCR 跳过
### 音画同步
- 音画同步(AV1): block=0 warn=0 ok=0 skipped=True
- 多人对话音画(DAV): block=0 warn=1 ok=0 skipped=False
- 多人对话音画(DAV) detail: 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 定位产物：生产数据/dialogue_av_alignment_第1集.json、合成/第1集
- mechanical[完整性] 第1集: 缺 时长清单.json（未配音则正常）
- mechanical[完整性] 第1集: 产物快照：配音句 0 · clip 11 · 成片 1
- mechanical[原生音轨] 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_01_死人堆惊醒.mp4: clip 含原生音轨；compose 默认应丢弃。若按 opt-in 混入环境声，需确认低风险、无口型、无原生人声
- mechanical[时长] 第1集: clip 总长 89.09s 与镜头时长累计 88.00s 差 1.09s
- visual[av_duration]: block=0 warn=2 skipped=False metrics={"final_sec": 89.104, "srt_sec": 88.0, "storyboard_sec": 88.0, "voice_sec": null}
- ...另有 4 条
### 音色一致性
- 音色声纹: block=0 warn=0 ok=0 skipped=False
- 配音情绪弧(VEA): block=0 warn=1 ok=0 skipped=False
- 口音方言(ACC): block=0 warn=0 ok=0 skipped=False
- 声纹机检不可用：mode=no_speaker_backend precision=insufficient_precision；未装 resemblyzer/speechbrain 声纹后端——本机无法量音色相似度，交还人判（脸侧缺 insightface 同样降级）
### 节奏密度
- 节奏密度(Rhythm): block=0 warn=3 ok=0 skipped=False
- 节奏密度(Rhythm) detail: 节奏/留存 advisory 总分偏低：52.0 定位产物：脚本/第1集/storyboard.json
- 节奏密度(Rhythm) detail: 连续 11 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10→EP01_CLIP11），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、EP01_CLIP02、EP01_CLIP03、EP01_CLIP04 定位产物：脚本/第1集/storyboard.json
- 节奏密度(Rhythm) detail: 开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 死人堆惊醒』），疑慢热；开场镜时长 6.0s > 5s，前3秒易掉留存 定位镜头：EP01_CLIP01、Clip_01 定位产物：脚本/第1集/storyboard.json
- visual[final_rhythm_density]: block=0 warn=2 skipped=False metrics={"clip_count": 11, "final_sec": 89.104, "hook_count": 0, "hook_interval_sec": null, "shot_density_per_min": 7.407}
- visual[final_rhythm_density] 成片镜头密度 7.4/min 偏慢，可能前段留不住
- visual[final_rhythm_density] 配音时长清单缺钩子/爽点/集尾标记，无法确认成片钩子密度
### 风格一致性
- 风格(S1): block=0 warn=1 ok=32 skipped=False
- 糊/低质(N4): block=0 warn=0 ok=0 skipped=False
- 景深一致(DOF1): block=0 warn=0 ok=0 skipped=False
### 语义继承
- 语义谱系(P0): block=0 warn=1 ok=0 skipped=False
- 语义谱系(P0) detail: `钩子` 留存标记未进入 storyboard 节奏/导演意图。 定位产物：脚本/第1集/storyboard.json、出图/第1集/prompt、出视频/第1集/prompt
- 称谓口头禅(A1): block=0 warn=0 ok=0 skipped=True
- 台词语域(D1): block=0 warn=0 ok=0 skipped=True
- 视频VLM判题(VLM1): block=0 warn=0 ok=0 skipped=True
- 伏笔兑现(SP1): block=0 warn=0 ok=0 skipped=False
### 状态百科
- 状态百科(P1): block=0 warn=0 ok=0 skipped=False
- 状态转场视频证据(ST1): block=0 warn=1 ok=0 skipped=False
- 状态转场视频证据(ST1) detail: 检测到 11 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 定位产物：脚本/第1集/storyboard.json、生产数据/state_transition_manifest_第1集.json
### 多模态漂移
- 多模态(P2): block=0 warn=0 ok=0 skipped=False
- 视频语义一致(VSEM): block=0 warn=8 ok=0 skipped=False
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_01 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consistency.json
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_03 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consistency.json
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_04 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consistency.json
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_05 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consistency.json
- 特效窜色(VFXC): block=0 warn=0 ok=0 skipped=True
- 实体记忆(EMB): block=0 warn=1 ok=0 skipped=False
- ...另有 1 条
### 视觉契约继承
- 契约继承: block=0 warn=0 ok=5 skipped=False
- 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md
### 交互/接触因果一致性
- 交互接触(I1): block=0 warn=5 ok=0 skipped=False
- 交互接触(I1) detail: 物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 定位镜头：Clip_02 定位产物：脚本/第1集/storyboard.json、出视频/第1集/prompt/video_model_routes.json
- 交互接触(I1) detail: 物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 定位镜头：Clip_03 定位产物：脚本/第1集/storyboard.json、出视频/第1集/prompt/video_model_routes.json
- 交互接触(I1) detail: 物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 定位镜头：Clip_04 定位产物：脚本/第1集/storyboard.json、出视频/第1集/prompt/video_model_routes.json
- 交互接触(I1) detail: 物理接触/持有镜缺 interaction_graph/contact_graph 或左右手/接触点描述；人物接触、递物、拉扯容易跨镜乱跳。 定位镜头：Clip_05 定位产物：脚本/第1集/storyboard.json、出视频/第1集/prompt/video_model_routes.json
- 持有账本(POS): block=0 warn=0 ok=0 skipped=False
- 结构化交互图谱(I2): block=0 warn=5 ok=0 skipped=False
- 结构化交互图谱(I2) detail: 接触/持有镜缺结构化 interaction_graph；自由文本提示无法稳定约束接触点、身体部位归属与遮挡顺序。 定位镜头：Clip_02 定位产物：脚本/第1集/storyboard.json
- ...另有 7 条
### 成片/包装一致性
- 成片统一(C1): block=0 warn=4 ok=0 skipped=False
- 成片统一(C1) detail: 成片响度不贴目标：LUFS=-17.99 target=-16.0 true_peak=-2.13 定位产物：合成/第1集、出视频/第1集/prompt/video_model_routes.json
- 成片统一(C1) detail: 本集视频混用了 2 个 primary 后端，但缺色彩匹配报告；混剪易出现亮度/色温跳。 定位产物：出视频/第1集/prompt/video_model_routes.json、合成/第1集
- 成片统一(C1) detail: storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。 定位产物：脚本/第1集/storyboard.json、合成/第1集、出视频/第1集/prompt/video_model_routes.json
- 成片统一(C1) detail: 缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 定位产物：合成/第1集、出视频/第1集/prompt/video_model_routes.json
- 成片时间线探针(FT1): block=0 warn=1 ok=0 skipped=False
- 成片时间线探针(FT1) detail: 成片已存在但缺 final_timeline_probe；无法直接量片确认剪点亮度/色温跳、静音缝、响度突变。 定位产物：合成/第1集/final_timeline_probe.json、合成/第1集
- 系列包装(PKG): block=0 warn=1 ok=0 skipped=True
- ...另有 7 条
### 生产操作一致性
- 生成配方(RCP): block=0 warn=0 ok=0 skipped=False
- 强配方Schema(RCP2): block=0 warn=0 ok=0 skipped=False
- 成本路由(K1): block=0 warn=40 ok=0 skipped=False
- 成本路由(K1) detail: 出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png
- 成本路由(K1) detail: 出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、出图/共享/图片/风格锚_冷灰写实3D国风漫剧.png
- 成本路由(K1) detail: 出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、出图/共享/图片/定妆_CHAR_01__囚犯初醒态_正面.png
- 成本路由(K1) detail: 出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、出图/共享/图片/定妆_CHAR_03__诈死复苏态_正面.png
- 人审校准集(CAL): block=0 warn=0 ok=0 skipped=False
- ...另有 6 条
### UI/系统面板/HUD 一致性
- 系统面板(UI1): block=0 warn=2 ok=0 skipped=False
- 系统面板(UI1) detail: 检出 6 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 定位产物：设定库/system_state_ledger.json、脚本/第1集/storyboard.json、设定库/ui_asset_registry.json、出图/第1集/prompt/01_分镜出图.md
- 系统面板(UI1) detail: 检出 6 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 定位镜头：Clip_02 定位产物：设定库/ui_asset_registry.json、脚本/第1集/storyboard.json、出图/第1集/prompt/01_分镜出图.md、设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳
### 音乐母题/leitmotif 一致性
- 音乐母题(LM1): block=0 warn=6 ok=0 skipped=False
- 音乐母题(LM1) detail: 音乐母题 MOTIF_jiang_survival 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。 定位产物：设定库/leitmotif_registry.json、脚本/第1集/storyboard.json
- 音乐母题(LM1) detail: 音乐母题 MOTIF_jiang_survival 缺 audio_sha256/hash/cue；无法确认 compose 复用的是同一段动机。 定位产物：设定库/leitmotif_registry.json、脚本/第1集/storyboard.json
- 音乐母题(LM1) detail: 音乐母题 MOTIF_tiger_pressure 缺 file/audio/clip；生成式 BGM 只写描述无法保证跨集复现。 定位产物：设定库/leitmotif_registry.json、脚本/第1集/storyboard.json
- 音乐母题(LM1) detail: 音乐母题 MOTIF_tiger_pressure 缺 audio_sha256/hash/cue；无法确认 compose 复用的是同一段动机。 定位产物：设定库/leitmotif_registry.json、脚本/第1集/storyboard.json
- 音乐衔接(BGM): block=0 warn=0 ok=0 skipped=False
### 图中文字渲染一致性（OCR 校验）
- 文字渲染(OCR1): block=0 warn=6 ok=0 skipped=False
- 文字渲染(OCR1) detail: Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_02 定位产物：出图/第1集/prompt/01_分镜出图.md、生产数据/text_render_第1集.json、设定库/ui_asset_registry.json、出图/第1集/图片
- 文字渲染(OCR1) detail: Clip_07 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_07 定位产物：出图/第1集/prompt/01_分镜出图.md、生产数据/text_render_第1集.json、设定库/ui_asset_registry.json、出图/第1集/图片
- 文字渲染(OCR1) detail: Clip_08 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_08 定位产物：出图/第1集/prompt/01_分镜出图.md、生产数据/text_render_第1集.json、设定库/ui_asset_registry.json、出图/第1集/图片
- 文字渲染(OCR1) detail: Clip_09 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_09 定位产物：出图/第1集/prompt/01_分镜出图.md、生产数据/text_render_第1集.json、设定库/ui_asset_registry.json、出图/第1集/图片
