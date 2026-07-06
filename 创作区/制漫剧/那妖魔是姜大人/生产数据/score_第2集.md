# n2d 自动审片评分

- 集：第2集
- Profile：standard
- 总分：90 / 100
- 阈值：85
- 状态：通过
- 生成时间：2026-07-06T10:23:20+00:00

## 长篇叙事一致性 KPI（报告型·非扣分·NarrLV/DirectorBench 轴）

- 叙事连续性：0.9011 · profile standard · 参考线 0.7 → **达标**（集数 10）
- 子分：伏笔已回收 0.6286 · 伏笔已规划 1.0 · 冷开场链 1.0 · 反套路 1.0 · 情绪起伏 0.8567 · 叙事原子 1.0 · 实体排程 1.0
- 基准：长篇叙事一致性参 NarrLV（Temporal Narrative Atom）/ EntityBench（per-shot entity schedule）/DirectorBench（长视频多代理诊断）；report-only·非扣分·子信号为确定性近似，不替代人读

## 维度

| 维度 | 权重 | 分数 | 状态 | block | warn | 回流 stage |
|---|---:|---:|---|---:|---:|---|
| 角色 DNA/形体一致性（脸/发型/身形/手） | 20 | 86 | 需复核 | 0 | 7 | image |
| 角色 DNA 一致性（服装/配饰） | 12 | 88 | 需复核 | 0 | 2 | image |
| 场景/构图连续性 | 12 | 86 | 需复核 | 0 | 23 | image |
| 字幕正确性 | 16 | 98 | 通过 | 0 | 0 | script_stage2 |
| 音画同步 | 16 | 84 | 需复核 | 0 | 2 | compose |
| 音色一致性 | 10 | 88 | 需复核 | 0 | 2 | voice |
| 节奏密度 | 12 | 88 | 需复核 | 0 | 3 | script_stage2 |
| 风格一致性 | 12 | 100 | 通过 | 0 | 0 | image |
| 语义继承 | 8 | 88 | 需复核 | 0 | 2 | script_stage2 |
| 状态百科 | 8 | 88 | 需复核 | 0 | 1 | image |
| 多模态漂移 | 8 | 88 | 需复核 | 0 | 2 | image |
| 视觉契约继承 | 8 | 100 | 通过 | 0 | 0 | video_prompt |
| 交互/接触因果一致性 | 8 | 88 | 需复核 | 0 | 2 | script_stage2 |
| 成片/包装一致性 | 8 | 88 | 需复核 | 0 | 8 | compose |
| 生产操作一致性 | 6 | 88 | 需复核 | 0 | 47 | review |
| UI/系统面板/HUD 一致性 | 6 | 88 | 需复核 | 0 | 2 | image |
| 音乐母题/leitmotif 一致性 | 6 | 100 | 通过 | 0 | 0 | script_stage1 |
| 图中文字渲染一致性（OCR 校验） | 8 | 88 | 需复核 | 0 | 8 | image |

## 自动回流建议

- `compose`：音画同步；回 n2d-compose 对齐配音轨、clip 时长、原生音轨策略和多人对话说话人结构；若时长源头错，回 n2d-script 阶段2。；定位镜头：Clip_11；定位产物：合成/第2集、出视频/第2集/视频/Clip_11.mp4

## 证据

### 角色 DNA/形体一致性（脸/发型/身形/手）
- 锚点门(N3): block=0 warn=0 ok=0 skipped=True
- 脸(G1): block=0 warn=0 ok=35 skipped=False
- 无脸崩坏(G1b): block=0 warn=0 ok=0 skipped=True
- 跨集脸漂(G5): block=0 warn=1 ok=0 skipped=False
- 发型(H1): block=0 warn=0 ok=35 skipped=False
- 辨识标记(MK1): block=0 warn=0 ok=0 skipped=True
- 片内时序(N2): block=0 warn=0 ok=11 skipped=False
- 手部/解剖(N5): block=0 warn=0 ok=0 skipped=True
- ...另有 19 条
### 角色 DNA 一致性（服装/配饰）
- 服装配色(N1): block=0 warn=2 ok=33 skipped=False
### 场景/构图连续性
- 场景(O2): block=0 warn=1 ok=0 skipped=False
- 接缝接力: block=0 warn=0 ok=0 skipped=False
- 轴线视线(X1): block=0 warn=0 ok=0 skipped=False
- 天气时辰(W1): block=0 warn=0 ok=0 skipped=False
- 色温调色(GRADE1): block=0 warn=6 ok=29 skipped=False
- 字幕安全区(L2): block=0 warn=0 ok=0 skipped=False
- 空间站位(B1): block=0 warn=0 ok=0 skipped=False
- 物件常驻(O3): block=0 warn=0 ok=0 skipped=False
- ...另有 20 条
### 字幕正确性
- 字幕对齐(L1): block=0 warn=0 ok=0 skipped=True
- 译名一致(TX1): block=0 warn=0 ok=0 skipped=True
- mechanical[字幕] 第2集: 检测到 fitted 配音轨 voice_*_fitted.wav：逐句原始时长清单 start 不再代表成片时间轴，跳过字幕起点漂移对账；以 compose/visual 的成片≈配音≈字幕末行对账为准。
- visual[subtitle_ocr]: block=0 warn=0 skipped=True
- visual[subtitle_ocr] 缺 pytesseract/Pillow，字幕 OCR 跳过
### 音画同步
- 音画同步(AV1): block=0 warn=0 ok=0 skipped=True
- 多人对话音画(DAV): block=0 warn=1 ok=0 skipped=False
- 多人对话音画(DAV) detail: 检测到原生音/多人对话视频产物，但缺 dialogue_av_alignment；无法核验说话人、口型、镜头对人和台词顺序。 定位产物：生产数据/dialogue_av_alignment_第2集.json、合成/第2集
- mechanical[完整性] 第2集: 产物快照：配音句 28 · clip 11 · 成片 1
- visual[av_duration]: block=0 warn=0 skipped=False metrics={"final_sec": 113.173991, "srt_sec": 113.229, "storyboard_sec": 113.229, "voice_sec": 113.229048}
- visual[av_duration] 音画时长对账通过：成片 113.17s
- visual[lip_sync]: block=0 warn=1 skipped=False metrics={"mouth_visible_no_hits": 12, "mouth_visible_yes_hits": 8}
- visual[lip_sync] 发现 8 处可见口型风险，但缺 lip-sync/SyncNet 外部检测报告
### 音色一致性
- 音色声纹: block=0 warn=0 ok=0 skipped=False
- 配音情绪弧(VEA): block=0 warn=2 ok=0 skipped=False
- 口音方言(ACC): block=0 warn=0 ok=0 skipped=False
- 声纹机检不可用：mode=no_speaker_backend precision=insufficient_precision；未装 resemblyzer/speechbrain 声纹后端——本机无法量音色相似度，交还人判（脸侧缺 insightface 同样降级）
### 节奏密度
- 节奏密度(Rhythm): block=0 warn=2 ok=0 skipped=False
- 节奏密度(Rhythm) detail: 节奏/留存 advisory 总分偏低：66.0 定位产物：脚本/第2集/storyboard.json
- 节奏密度(Rhythm) detail: 连续 9 个长镜聚集（EP02_CLIP01→EP02_CLIP02→EP02_CLIP03→EP02_CLIP04→EP02_CLIP05→EP02_CLIP06→EP02_CLIP07→EP02_CLIP08→EP02_CLIP09），疑节奏塌·掉留存 定位镜头：EP02_CLIP01、EP02_CLIP02、EP02_CLIP03、EP02_CLIP04 定位产物：脚本/第2集/storyboard.json
- visual[final_rhythm_density]: block=0 warn=1 skipped=False metrics={"clip_count": 10, "final_sec": 113.174, "hook_count": 9, "hook_interval_sec": 12.575, "shot_density_per_min": 5.302}
- visual[final_rhythm_density] 成片镜头密度 5.3/min 偏慢，可能前段留不住
### 风格一致性
- 风格(S1): block=0 warn=0 ok=35 skipped=False
- 糊/低质(N4): block=0 warn=0 ok=0 skipped=False
- 景深一致(DOF1): block=0 warn=0 ok=35 skipped=False
### 语义继承
- 语义谱系(P0): block=0 warn=1 ok=0 skipped=False
- 语义谱系(P0) detail: `钩子` 留存标记未进入 storyboard 节奏/导演意图。 定位产物：脚本/第2集/storyboard.json、出图/第2集/prompt、出视频/第2集/prompt
- 称谓口头禅(A1): block=0 warn=0 ok=0 skipped=True
- 台词语域(D1): block=0 warn=0 ok=0 skipped=True
- 视频VLM判题(VLM1): block=0 warn=0 ok=0 skipped=True
- 伏笔兑现(SP1): block=0 warn=0 ok=0 skipped=False
- mechanical[视频] 第2集: clip MP4 数 11 与 storyboard clips 10 不一致
### 状态百科
- 状态百科(P1): block=0 warn=0 ok=0 skipped=False
- 状态转场视频证据(ST1): block=0 warn=1 ok=0 skipped=False
- 状态转场视频证据(ST1) detail: 检测到 10 个疑似状态变化镜，但缺 state_transition_manifest；无法验证视频里 before→after 是否真的完成。 定位产物：脚本/第2集/storyboard.json、生产数据/state_transition_manifest_第2集.json
### 多模态漂移
- 多模态(P2): block=0 warn=0 ok=0 skipped=False
- 视频语义一致(VSEM): block=0 warn=1 ok=0 skipped=False
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_10 定位产物：生产数据/video_semantic_consistency_第2集.json、出视频/第2集/video_semantic_consistency.json
- 特效窜色(VFXC): block=0 warn=0 ok=0 skipped=True
- 实体记忆(EMB): block=0 warn=1 ok=0 skipped=False
- 实体记忆(EMB) detail: 本集有重复/核心实体（CHAR_01, CHAR_01/猛虎快刀圆满态, CHAR_01/脱力态, CHAR_01/血尘战损态, CHAR_01__, CHAR_02）但缺 entity_memory_bank；后续镜头无法按已验收画面检索实体视角/表情/地点记忆。 定位产物：生产数据/entity_memory_bank.json、出图/共享/entity_memory_bank.json、脚本/第2集/storyboard.json、出图/共享/identity_registry.json
### 视觉契约继承
- 契约继承: block=0 warn=0 ok=5 skipped=False
- 契约继承 detail: 逐字一致 定位产物：出图/第2集/prompt/00_总览.md、出视频/第2集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第2集/prompt/00_总览.md、出视频/第2集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第2集/prompt/00_总览.md、出视频/第2集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第2集/prompt/00_总览.md、出视频/第2集/prompt/00_总览.md
### 交互/接触因果一致性
- 交互接触(I1): block=0 warn=0 ok=0 skipped=False
- 持有账本(POS): block=0 warn=0 ok=0 skipped=False
- 结构化交互图谱(I2): block=0 warn=0 ok=0 skipped=False
- 物理因果链(CG1): block=0 warn=1 ok=0 skipped=False
- 物理因果链(CG1) detail: 视频/脚本包含明显物理因果动作，但缺 causal_event_graph；状态转场之外的因果链无法复核。 定位产物：脚本/第2集/storyboard.json、生产数据/causal_event_graph_第2集.json
- 物理事件图(PHY): block=0 warn=1 ok=0 skipped=False
- 物理事件图(PHY) detail: 本集存在物理/因果动作且已有媒体，但缺 physical_event_graph；无法归因到具体 law/object/frame/violation。 定位产物：生产数据/physical_event_graph_第2集.json、脚本/第2集/storyboard.json、出视频/第2集、生产数据/causal_event_graph_第2集.json
### 成片/包装一致性
- 成片统一(C1): block=0 warn=3 ok=0 skipped=False
- 成片统一(C1) detail: 本集视频混用了 2 个 primary 后端，但缺色彩匹配报告；混剪易出现亮度/色温跳。 定位产物：出视频/第2集/prompt/video_model_routes.json、合成/第2集
- 成片统一(C1) detail: storyboard 存在多档节奏，但缺 tension_mix/BGM 增益证据；BGM 全集一刀切会削弱钩子与对白清晰度。 定位产物：脚本/第2集/storyboard.json、合成/第2集、出视频/第2集/prompt/video_model_routes.json
- 成片统一(C1) detail: 缺 room tone / foley 统一证据；原生音画、配音、BGM 混合后空间感可能忽干忽湿。 定位产物：合成/第2集、出视频/第2集/prompt/video_model_routes.json
- 成片时间线探针(FT1): block=0 warn=1 ok=0 skipped=False
- 成片时间线探针(FT1) detail: 成片已存在但缺 final_timeline_probe；无法直接量片确认剪点亮度/色温跳、静音缝、响度突变。 定位产物：合成/第2集/final_timeline_probe.json、合成/第2集
- 系列包装(PKG): block=0 warn=1 ok=0 skipped=True
- 系列包装(PKG) detail: 缺系列包装规范（片头/片尾/封面字/字幕字体/转场音效/平台交付名）；多集发布会出现包装漂移。 定位产物：设定库/series_packaging.json、合成/交付
- ...另有 6 条
### 生产操作一致性
- 生成配方(RCP): block=0 warn=2 ok=0 skipped=False
- 生成配方(RCP) detail: 脚本/第2集/voiceover.txt 生成事件缺配方字段：seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=69c1c35402c930c7，但复跑审计证据不完整。 定位产物：生产数据/production_events.jsonl、生产数据/generation_recipe_第2集.json、脚本/第2集/voiceover.txt
- 生成配方(RCP) detail: 合成/第2集/配音/voice_zh.wav 生成事件缺配方字段：mode, seed/seed_degrade, backend_version/model_version, declared_recipe_hash；已可推导 hash=4e8d3bf74472ab2f，但复跑审计证据不完整。 定位产物：生产数据/production_events.jsonl、生产数据/generation_recipe_第2集.json、合成/第2集/配音/voice_zh.wav
- 强配方Schema(RCP2): block=0 warn=2 ok=0 skipped=False
- 强配方Schema(RCP2) detail: 脚本/第2集/voiceover.txt 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_version, qc_version, backend_version/model_version, seed_effective_or_unsupported；recipe_hash 已有但还不能完整复现/归因。 定位产物：生产数据/production_events.jsonl、生产数据/generation_recipe_第2集.json、脚本/第2集/voiceover.txt
- 强配方Schema(RCP2) detail: 合成/第2集/配音/voice_zh.wav 强配方 schema 缺字段：prompt_sha256, reference_bundle_sha256/reference_manifest, input_fingerprint, settings_sha256, artifact_sha256, adapter_version, qc_version, backend_version/model_version, seed_effective_or_unsupported；recipe_hash 已有但还不能完整复现/归因。 定位产物：生产数据/production_events.jsonl、生产数据/generation_recipe_第2集.json、合成/第2集/配音/voice_zh.wav
- 成本路由(K1): block=0 warn=40 ok=0 skipped=False
- 成本路由(K1) detail: 脚本/第2集/voiceover.txt 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位产物：生产数据/production_events.jsonl、出视频/第2集/prompt/video_model_routes.json、脚本/第2集/voiceover.txt
- ...另有 10 条
### UI/系统面板/HUD 一致性
- 系统面板(UI1): block=0 warn=2 ok=0 skipped=False
- 系统面板(UI1) detail: 检出 8 个系统数值/HUD 镜头，但缺 system_state_ledger；等级/经验/成长值单调性无法复核。 定位产物：设定库/system_state_ledger.json、脚本/第2集/storyboard.json、设定库/ui_asset_registry.json、出图/第2集/prompt/01_分镜出图.md
- 系统面板(UI1) detail: 检出 8 个 UI/HUD/图中文字镜头，但缺 设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳；建库锁面板定妆底图（边框/配色/字体/版式）并 image2image 只换数值区。 定位镜头：Clip_01 定位产物：设定库/ui_asset_registry.json、脚本/第2集/storyboard.json、出图/第2集/prompt/01_分镜出图.md、设定库/ui_asset_registry.json——系统面板/血条/等级框跨集易漂、面板中文渲染不稳
### 音乐母题/leitmotif 一致性
- 音乐母题(LM1): block=0 warn=0 ok=0 skipped=False
- 音乐衔接(BGM): block=0 warn=0 ok=0 skipped=False
### 图中文字渲染一致性（OCR 校验）
- 文字渲染(OCR1): block=0 warn=8 ok=0 skipped=False
- 文字渲染(OCR1) detail: Clip_01 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_01 定位产物：出图/第2集/prompt/01_分镜出图.md、生产数据/text_render_第2集.json、设定库/ui_asset_registry.json、出图/第2集/图片
- 文字渲染(OCR1) detail: Clip_02 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_02 定位产物：出图/第2集/prompt/01_分镜出图.md、生产数据/text_render_第2集.json、设定库/ui_asset_registry.json、出图/第2集/图片
- 文字渲染(OCR1) detail: Clip_04 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_04 定位产物：出图/第2集/prompt/01_分镜出图.md、生产数据/text_render_第2集.json、设定库/ui_asset_registry.json、出图/第2集/图片
- 文字渲染(OCR1) detail: Clip_05 含图中文字（面板/牌匾等）但未声明预期文字——补 ui_asset_registry.text_template 或镜头「图中文字：…」字段，OCR 才有对照基准；并跑 text_render_runner 实读校验。 定位镜头：Clip_05 定位产物：出图/第2集/prompt/01_分镜出图.md、生产数据/text_render_第2集.json、设定库/ui_asset_registry.json、出图/第2集/图片
