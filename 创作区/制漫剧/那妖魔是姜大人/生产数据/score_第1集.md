# n2d 自动审片评分

- 集：第1集
- Profile：standard
- 总分：80 / 100
- 阈值：85
- 状态：回流
- 生成时间：2026-07-07T06:40:06+00:00

## 长篇叙事一致性 KPI（报告型·非扣分·NarrLV/DirectorBench 轴）

- 叙事连续性：0.9011 · profile standard · 参考线 0.7 → **达标**（集数 10）
- 子分：伏笔已回收 0.6286 · 伏笔已规划 1.0 · 冷开场链 1.0 · 反套路 1.0 · 情绪起伏 0.8567 · 叙事原子 1.0 · 实体排程 1.0
- 基准：长篇叙事一致性参 NarrLV（Temporal Narrative Atom）/ EntityBench（per-shot entity schedule）/DirectorBench（长视频多代理诊断）；report-only·非扣分·子信号为确定性近似，不替代人读

## 维度

| 维度 | 权重 | 分数 | 状态 | block | warn | 回流 stage |
|---|---:|---:|---|---:|---:|---|
| 角色 DNA/形体一致性（脸/发型/身形/手） | 20 | 16 | 回流 | 2 | 1 | image |
| 角色 DNA 一致性（服装/配饰） | 12 | 100 | 通过 | 0 | 0 | image |
| 场景/构图连续性 | 12 | 0 | 回流 | 4 | 32 | image |
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
| 生产操作一致性 | 6 | 100 | 通过 | 0 | 0 | review |
| UI/系统面板/HUD 一致性 | 6 | 100 | 通过 | 0 | 0 | image |
| 音乐母题/leitmotif 一致性 | 6 | 100 | 通过 | 0 | 0 | script_stage1 |
| 图中文字渲染一致性（OCR 校验） | 8 | 100 | 通过 | 0 | 0 | image |

## 自动回流建议

- `image`：角色 DNA/形体一致性（脸/发型/身形/手）、场景/构图连续性；回 n2d-image 重出脸/发型/身形/手部漂移镜头；必要时补 identity_registry.character_dna / reference_group / 身高表；视频侧主体漂移回 n2d-video 重出对应 clip。跨集体型漂移补 character_dna.身形/体型锁；外观判官(VAP)判失败按离群镜重出。表情连续(EXP1)失配回 n2d-image 补 expressions 表情参考重出情绪镜。表情过锁(EXP3·report-only)疑似 copy-paste 冻脸（高身份×零表情·IPRO）时，别只重抽单镜——解耦表情（AU/FACS 表情控件 / expressions 参考）或下调身份参考权重后整体重出情绪镜。辨识标记(MK1)漂移/丢失回 n2d-image 把 identity_registry.identity_marks 的标记锁补进出图 prompt 重出；获得型标记穿帮回 storyboard 核对获得集。；回 n2d-image 修场景定妆、光位锚、轴线视线、时辰天气、字幕安全区或尾帧；必要时回 n2d-video 重出接缝/相机轨迹/运动质量 clip。；定位镜头：Clip_01、Clip_02、Clip_06；定位产物：出视频/第1集、出视频/第1集/control/Clip_01/motion_control_manifest.json、生产数据/spectacle_video_qc_第1集.json、出视频/第1集、出视频/第1集/control/Clip_02/motion_control_manifest.json、生产数据/spectacle_video_qc_第1集.json、出视频/第1集、出图/第1集/图片/Clip_01.png、出图/第1集/图片/Clip_02.png、出图/第1集/图片/Clip_06.png
- `compose`：音画同步；回 n2d-compose 对齐配音轨、clip 时长、原生音轨策略和多人对话说话人结构；若时长源头错，回 n2d-script 阶段2。；定位镜头：Clip_02；定位产物：出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4、出视频/第1集/视频/Clip_02.mp4、合成/第1集

## 数据采集建议

- `n2d-score`：；存在无法自动归到 schema 维度的 block 级证据（如 完整性/视频）——必须人判归类或修复，不能直接放行。[进度凭据对账] review/第1集/成片: 进度「成片」标 ✅ 却无新鲜通过的闸门凭据（gate_failed）：闸门未过：compose 仍有 3 个 block 级问题（见 gate_findings_compose_第1集.json）。修掉 block 后重跑 → python3 skills/n2d-dashboard/scripts/dashboard.py gate "创作区/制漫剧/那妖魔是姜大人" 第1集 --stage compose（凡绕过 progress set 直接写 ✅ 都会在此被抓——重跑该阶段闸门盖新鲜凭据后再交付）

## 未归类证据（无法自动归到 schema 维度·需人判分诊）

- block [进度凭据对账] review/第1集/成片: 进度「成片」标 ✅ 却无新鲜通过的闸门凭据（gate_failed）：闸门未过：compose 仍有 3 个 block 级问题（见 gate_findings_compose_第1集.json）。修掉 block 后重跑 → python3 skills/n2d-dashboard/scripts/dashboard.py gate "创作区/制漫剧/那妖魔是姜大人" 第1集 --stage compose（凡绕过 progress set 直接写 ✅ 都会在此被抓——重跑该阶段闸门盖新鲜凭据后再交付）（来源 dashboard）

## 证据

### 角色 DNA/形体一致性（脸/发型/身形/手）
- 锚点门(N3): block=0 warn=0 ok=0 skipped=True
- 脸(G1): block=0 warn=0 ok=31 skipped=False
- 无脸崩坏(G1b): block=0 warn=0 ok=0 skipped=True
- 跨集脸漂(G5): block=0 warn=1 ok=0 skipped=False
- 发型(H1): block=0 warn=0 ok=31 skipped=False
- 辨识标记(MK1): block=0 warn=0 ok=0 skipped=True
- 片内时序(N2): block=0 warn=0 ok=16 skipped=False
- 手部/解剖(N5): block=0 warn=0 ok=0 skipped=True
- ...另有 11 条
### 角色 DNA 一致性（服装/配饰）
- 服装配色(N1): block=0 warn=0 ok=31 skipped=False
### 场景/构图连续性
- 场景(O2): block=0 warn=3 ok=0 skipped=False
- 接缝接力: block=0 warn=0 ok=0 skipped=False
- 轴线视线(X1): block=0 warn=0 ok=0 skipped=False
- 天气时辰(W1): block=0 warn=5 ok=0 skipped=False
- 色温调色(GRADE1): block=0 warn=6 ok=25 skipped=False
- 字幕安全区(L2): block=0 warn=0 ok=0 skipped=False
- 空间站位(B1): block=0 warn=0 ok=0 skipped=False
- 物件常驻(O3): block=0 warn=0 ok=0 skipped=False
- ...另有 25 条
### 字幕正确性
- 字幕对齐(L1): block=0 warn=0 ok=0 skipped=True
- 译名一致(TX1): block=0 warn=0 ok=0 skipped=True
- mechanical[字幕] 第1集: 检测到 fitted 配音轨 voice_*_fitted.wav：逐句原始时长清单 start 不再代表成片时间轴，跳过字幕起点漂移对账；以 compose/visual 的成片≈配音≈字幕末行对账为准。
- visual[subtitle_ocr]: block=0 warn=0 skipped=True
- visual[subtitle_ocr] 缺 pytesseract/Pillow，字幕 OCR 跳过
### 音画同步
- 音画同步(AV1): block=0 warn=0 ok=0 skipped=True
- 多人对话音画(DAV): block=0 warn=0 ok=0 skipped=False
- mechanical[完整性] 第1集: 产物快照：配音句 28 · 视频片段 16 · 成片 1
- mechanical[原生音轨] 创作区/制漫剧/那妖魔是姜大人/出视频/第1集/视频/Clip_02_看见虎妖尸身_part1.mp4: clip 含原生音轨；compose 默认应丢弃。若按 opt-in 混入环境声，需确认低风险、无口型、无原生人声
- mechanical[时长] 第1集: 源 clip 物理总长 127.86s 与镜头时长累计 120.52s 差 7.34s；已检测到 fitted 配音轨且成片 120.10s≈锁定槽位，split 时长已由 compose Time-Warp 修正。
- visual[av_duration]: block=0 warn=1 skipped=False metrics={"final_sec": 120.1, "srt_sec": 120.515, "storyboard_sec": 120.515, "voice_sec": 120.515034}
- visual[av_duration] 成片 vs srt 时长差 0.42s > 0.4s
- visual[lip_sync]: block=0 warn=0 skipped=False metrics={"mouth_visible_no_hits": 22, "mouth_visible_yes_hits": 0}
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
- visual[final_rhythm_density]: block=0 warn=1 skipped=False metrics={"clip_count": 11, "final_sec": 120.1, "hook_count": 10, "hook_interval_sec": 12.01, "shot_density_per_min": 5.495}
- visual[final_rhythm_density] 成片镜头密度 5.5/min 偏慢，可能前段留不住
### 风格一致性
- 风格(S1): block=0 warn=0 ok=31 skipped=False
- 糊/低质(N4): block=0 warn=0 ok=0 skipped=False
- 景深一致(DOF1): block=0 warn=0 ok=31 skipped=False
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
- 成本路由(K1): block=0 warn=0 ok=0 skipped=False
- 人审校准集(CAL): block=0 warn=0 ok=0 skipped=False
- 一致性探针包(PROBE): block=0 warn=0 ok=0 skipped=False
- 视频证据完整性(EVID): block=0 warn=0 ok=0 skipped=False
- 真值源(TRUTH): block=0 warn=0 ok=0 skipped=False
### UI/系统面板/HUD 一致性
- 系统面板(UI1): block=0 warn=0 ok=0 skipped=False
### 音乐母题/leitmotif 一致性
- 音乐母题(LM1): block=0 warn=0 ok=0 skipped=False
- 音乐衔接(BGM): block=0 warn=0 ok=0 skipped=False
### 图中文字渲染一致性（OCR 校验）
- 文字渲染(OCR1): block=0 warn=0 ok=0 skipped=False
