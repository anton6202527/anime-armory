# n2d 自动审片评分

- 集：第1集
- Profile：demo
- 总分：93 / 100
- 阈值：85
- 状态：通过
- 生成时间：2026-07-07T10:20:41+00:00

## 长篇叙事一致性 KPI（报告型·非扣分·NarrLV/DirectorBench 轴）

- 叙事连续性：0.9205 · profile demo · 参考线 0.6 → **达标**（集数 10）
- 子分：伏笔已回收 0.6286 · 伏笔已规划 1.0 · 冷开场链 1.0 · 反套路 1.0 · 情绪起伏 0.8567 · 叙事原子 1.0 · 实体排程 1.0
- 基准：长篇叙事一致性参 NarrLV（Temporal Narrative Atom）/ EntityBench（per-shot entity schedule）/DirectorBench（长视频多代理诊断）；report-only·非扣分·子信号为确定性近似，不替代人读

## 维度

| 维度 | 权重 | 分数 | 状态 | block | warn | 回流 stage |
|---|---:|---:|---|---:|---:|---|
| 角色 DNA/形体一致性（脸/发型/身形/手） | 20 | 86 | 需复核 | 0 | 16 | image |
| 角色 DNA 一致性（服装/配饰） | 12 | 100 | 通过 | 0 | 0 | image |
| 场景/构图连续性 | 12 | 86 | 需复核 | 0 | 31 | image |
| 字幕正确性 | 16 | 98 | 通过 | 0 | 0 | script_stage2 |
| 音画同步 | 16 | 82 | 需复核 | 0 | 2 | compose |
| 音色一致性 | 10 | 88 | 需复核 | 0 | 1 | voice |
| 节奏密度 | 12 | 88 | 需复核 | 0 | 4 | script_stage2 |
| 风格一致性 | 12 | 100 | 通过 | 0 | 0 | image |
| 语义继承 | 8 | 86 | 需复核 | 0 | 1 | script_stage2 |
| 状态百科 | 8 | 100 | 通过 | 0 | 0 | image |
| 多模态漂移 | 8 | 88 | 需复核 | 0 | 8 | image |
| 视觉契约继承 | 8 | 100 | 通过 | 0 | 0 | video_prompt |
| 交互/接触因果一致性 | 8 | 100 | 通过 | 0 | 0 | script_stage2 |
| 成片/包装一致性 | 8 | 100 | 通过 | 0 | 0 | compose |
| 生产操作一致性 | 6 | 88 | 需复核 | 0 | 10 | review |
| UI/系统面板/HUD 一致性 | 6 | 100 | 通过 | 0 | 0 | image |
| 音乐母题/leitmotif 一致性 | 6 | 100 | 通过 | 0 | 0 | script_stage1 |
| 图中文字渲染一致性（OCR 校验） | 8 | 100 | 通过 | 0 | 0 | image |

## 自动回流建议

- `compose`：音画同步；回 n2d-compose 对齐配音轨、clip 时长、原生音轨策略和多人对话说话人结构；若时长源头错，回 n2d-script 阶段2。；定位镜头：Clip_02；定位产物：出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4、出视频/第1集/视频/Clip_02.mp4、合成/第1集

## 证据

### 角色 DNA/形体一致性（脸/发型/身形/手）
- 锚点门(N3): block=0 warn=0 ok=0 skipped=True
- 脸(G1): block=0 warn=0 ok=33 skipped=False
- 无脸崩坏(G1b): block=0 warn=0 ok=0 skipped=True
- 跨集脸漂(G5): block=0 warn=1 ok=0 skipped=False
- 发型(H1): block=0 warn=0 ok=33 skipped=False
- 辨识标记(MK1): block=0 warn=0 ok=0 skipped=True
- 片内时序(N2): block=0 warn=15 ok=1 skipped=False
- 手部/解剖(N5): block=0 warn=0 ok=0 skipped=True
- ...另有 9 条
### 角色 DNA 一致性（服装/配饰）
- 服装配色(N1): block=0 warn=0 ok=33 skipped=False
### 场景/构图连续性
- 场景(O2): block=0 warn=0 ok=0 skipped=False
- 接缝接力: block=0 warn=0 ok=0 skipped=False
- 轴线视线(X1): block=0 warn=0 ok=0 skipped=False
- 天气时辰(W1): block=0 warn=6 ok=0 skipped=False
- 色温调色(GRADE1): block=0 warn=6 ok=27 skipped=False
- 字幕安全区(L2): block=0 warn=0 ok=0 skipped=False
- 空间站位(B1): block=0 warn=0 ok=0 skipped=False
- 物件常驻(O3): block=0 warn=0 ok=0 skipped=False
- ...另有 22 条
### 字幕正确性
- 字幕对齐(L1): block=0 warn=0 ok=0 skipped=True
- 译名一致(TX1): block=0 warn=0 ok=0 skipped=True
- mechanical[字幕] 第1集: 检测到 fitted 配音轨 voice_*_fitted.wav：逐句原始时长清单 start 不再代表成片时间轴，跳过字幕起点漂移对账；以 compose/visual 的成片≈配音≈字幕末行对账为准。
- visual[subtitle_ocr]: block=0 warn=0 skipped=True
- visual[subtitle_ocr] 缺 pytesseract/Pillow，字幕 OCR 跳过
### 音画同步
- 音画同步(AV1): block=0 warn=0 ok=0 skipped=True
- 多人对话音画(DAV): block=0 warn=0 ok=0 skipped=False
- mechanical[完整性] 第1集: 产物快照：配音句 28 · 视频片段 16 · 成片 3
- mechanical[原生音轨] 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4: clip 含原生音轨；compose 默认应丢弃。若按 opt-in 混入环境声，需确认低风险、无口型、无原生人声
- mechanical[时长] 第1集: 源 clip 物理总长 125.78s 与镜头时长累计 120.52s 差 5.26s；已检测到 fitted 配音轨且成片 120.10s≈锁定槽位，split 时长已由 compose Time-Warp 修正。
- visual[av_duration]: block=0 warn=0 skipped=False metrics={"final_sec": 120.117007, "srt_sec": 120.515, "storyboard_sec": 120.515, "voice_sec": 120.515034}
- visual[av_duration] 音画时长对账通过：成片 120.12s
- visual[lip_sync]: block=0 warn=1 skipped=False metrics={"mouth_visible_no_hits": 5, "mouth_visible_yes_hits": 6}
- ...另有 1 条
### 音色一致性
- 音色声纹: block=0 warn=0 ok=0 skipped=False
- 配音情绪弧(VEA): block=0 warn=1 ok=0 skipped=False
- 口音方言(ACC): block=0 warn=0 ok=0 skipped=False
- 声纹机检不可用：mode=no_speaker_backend precision=insufficient_precision；未装 resemblyzer/speechbrain 声纹后端——本机无法量音色相似度，交还人判（脸侧缺 insightface 同样降级）
### 节奏密度
- 节奏密度(Rhythm): block=0 warn=3 ok=0 skipped=False
- 节奏密度(Rhythm) detail: 节奏/留存 advisory 总分偏低：57.4 定位产物：脚本/第1集/storyboard.json
- 节奏密度(Rhythm) detail: 连续 10 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10），疑节奏塌·掉留存 定位镜头：EP01_CLIP01、EP01_CLIP02、EP01_CLIP03、EP01_CLIP04 定位产物：脚本/第1集/storyboard.json
- 节奏密度(Rhythm) detail: 开场镜未见冷开场/钩子标注（rhythm/label=『铺垫·长镜 死人堆惊醒』），疑慢热；开场镜时长 9.2s > 5s，前3秒易掉留存 定位镜头：EP01_CLIP01、Clip_01 定位产物：脚本/第1集/storyboard.json
- visual[final_rhythm_density]: block=0 warn=1 skipped=False metrics={"clip_count": 11, "final_sec": 120.117, "hook_count": 10, "hook_interval_sec": 12.012, "shot_density_per_min": 5.495}
- visual[final_rhythm_density] 成片镜头密度 5.5/min 偏慢，可能前段留不住
### 风格一致性
- 风格(S1): block=0 warn=0 ok=33 skipped=False
- 糊/低质(N4): block=0 warn=0 ok=0 skipped=False
- 景深一致(DOF1): block=0 warn=0 ok=33 skipped=False
### 语义继承
- 语义谱系(P0): block=0 warn=0 ok=0 skipped=False
- 称谓口头禅(A1): block=0 warn=0 ok=0 skipped=True
- 台词语域(D1): block=0 warn=0 ok=0 skipped=True
- 视频VLM判题(VLM1): block=0 warn=1 ok=0 skipped=False
- 视频VLM判题(VLM1) detail: 本机未配置重型 VLM runner；此文件仅占位并指向 manifest，不能作为 pass 结论。 定位产物：生产数据/video_vlm_consistency_第1集.json、出视频/第1集/video_vlm_consistency.json
- 伏笔兑现(SP1): block=0 warn=0 ok=0 skipped=False
- mechanical[视频] 第1集: 检测到 split-part 视频：物理 MP4 16 / 逻辑 clip 11 / storyboard 11
### 状态百科
- 状态百科(P1): block=0 warn=0 ok=0 skipped=False
- 状态转场视频证据(ST1): block=0 warn=0 ok=0 skipped=False
### 多模态漂移
- 多模态(P2): block=0 warn=0 ok=0 skipped=False
- 视频语义一致(VSEM): block=0 warn=8 ok=0 skipped=False
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_01 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consistency.json
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_03 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consistency.json
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_04 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consistency.json
- 视频语义一致(VSEM) detail: DINOv2 whole-frame similarity is below the configured VSEM threshold. 定位镜头：Clip_05 定位产物：生产数据/video_semantic_consistency_第1集.json、出视频/第1集/video_semantic_consistency.json
- 特效窜色(VFXC): block=0 warn=0 ok=0 skipped=True
- 实体记忆(EMB): block=0 warn=0 ok=0 skipped=False
### 视觉契约继承
- 契约继承: block=0 warn=0 ok=5 skipped=False
- 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md
- 契约继承 detail: 逐字一致 定位产物：出图/第1集/prompt/00_总览.md、出视频/第1集/prompt/00_总览.md
### 交互/接触因果一致性
- 交互接触(I1): block=0 warn=0 ok=0 skipped=False
- 持有账本(POS): block=0 warn=0 ok=0 skipped=False
- 结构化交互图谱(I2): block=0 warn=0 ok=0 skipped=False
- 物理因果链(CG1): block=0 warn=0 ok=0 skipped=False
- 物理事件图(PHY): block=0 warn=0 ok=0 skipped=False
### 成片/包装一致性
- 成片统一(C1): block=0 warn=0 ok=0 skipped=False
- 成片时间线探针(FT1): block=0 warn=0 ok=0 skipped=False
- 系列包装(PKG): block=0 warn=0 ok=0 skipped=False
- 系列调色(GRD): block=0 warn=0 ok=0 skipped=False
- 环境声(AMB): block=0 warn=0 ok=0 skipped=False
- 声音空间(ASP): block=0 warn=0 ok=0 skipped=False
### 生产操作一致性
- 生成配方(RCP): block=0 warn=0 ok=0 skipped=False
- 强配方Schema(RCP2): block=0 warn=0 ok=0 skipped=False
- 成本路由(K1): block=0 warn=10 ok=0 skipped=False
- 成本路由(K1) detail: 创作区/制漫剧/那妖魔是姜大人/合成/第1集/成片_第1集_zh.mp4 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、合成/第1集/成片_第1集_zh.mp4
- 成本路由(K1) detail: 创作区/制漫剧/那妖魔是姜大人/合成/第1集/成片_第1集_zh.mp4 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、合成/第1集/成片_第1集_zh.mp4
- 成本路由(K1) detail: 出图/第1集/图片/Clip06_mid_reaction.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位镜头：Clip_06 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、出图/第1集/图片/Clip06_mid_reaction.png
- 成本路由(K1) detail: 出图/第1集/图片/Clip06_end_reaction.png 生成事件缺 cost/provider 记账；无法计算重试性价比和模型切换成本。 定位镜头：Clip_06 定位产物：生产数据/production_events.jsonl、出视频/第1集/prompt/video_model_routes.json、出图/第1集/图片/Clip06_end_reaction.png
- 人审校准集(CAL): block=0 warn=0 ok=0 skipped=False
- ...另有 3 条
### UI/系统面板/HUD 一致性
- 系统面板(UI1): block=0 warn=0 ok=0 skipped=False
### 音乐母题/leitmotif 一致性
- 音乐母题(LM1): block=0 warn=0 ok=0 skipped=False
- 音乐衔接(BGM): block=0 warn=0 ok=0 skipped=False
### 图中文字渲染一致性（OCR 校验）
- 文字渲染(OCR1): block=0 warn=0 ok=0 skipped=False
