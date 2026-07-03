# n2d 自动审片评分

- 集：第1集
- Profile：demo
- 总分：61 / 100
- 阈值：85
- 状态：回流
- 生成时间：2026-07-03T14:44:43+00:00

## 长篇叙事一致性 KPI（报告型·非扣分·NarrLV/DirectorBench 轴）

- 叙事连续性：0.7817 · profile demo · 参考线 0.6 → **达标**（集数 10）
- 子分：伏笔已回收 0.0 · 伏笔已规划 0.5833 · 冷开场链 1.0 · 反套路 1.0 · 情绪起伏 1.0 · 叙事原子 1.0 · 实体排程 1.0 · 未填伏笔 5
- 基准：长篇叙事一致性参 NarrLV（Temporal Narrative Atom）/ EntityBench（per-shot entity schedule）/DirectorBench（长视频多代理诊断）；report-only·非扣分·子信号为确定性近似，不替代人读

## 维度

| 维度 | 权重 | 分数 | 状态 | block | warn | 回流 stage |
|---|---:|---:|---|---:|---:|---|
| 角色 DNA/形体一致性（脸/发型/身形/手） | 20 | 65 | 回流 | 1 | 0 | image |
| 角色 DNA 一致性（服装/配饰） | 12 | 70 | 缺数据 | 0 | 0 | image |
| 场景/构图连续性 | 12 | 0 | 回流 | 3 | 0 | image |
| 字幕正确性 | 16 | 70 | 缺数据 | 0 | 0 | script_stage2 |
| 音画同步 | 16 | 70 | 缺数据 | 0 | 0 | compose |
| 音色一致性 | 10 | 70 | 缺数据 | 0 | 0 | voice |
| 节奏密度 | 12 | 30 | 回流 | 2 | 0 | script_stage2 |
| 风格一致性 | 12 | 70 | 缺数据 | 0 | 0 | image |
| 语义继承 | 8 | 30 | 回流 | 2 | 0 | script_stage2 |
| 状态百科 | 8 | 70 | 缺数据 | 0 | 0 | image |
| 多模态漂移 | 8 | 70 | 缺数据 | 0 | 0 | image |
| 视觉契约继承 | 8 | 70 | 缺数据 | 0 | 0 | video_prompt |
| 交互/接触因果一致性 | 8 | 70 | 缺数据 | 0 | 0 | script_stage2 |
| 成片/包装一致性 | 8 | 70 | 缺数据 | 0 | 0 | compose |
| 生产操作一致性 | 6 | 70 | 缺数据 | 0 | 0 | review |
| UI/系统面板/HUD 一致性 | 6 | 70 | 缺数据 | 0 | 0 | image |
| 音乐母题/leitmotif 一致性 | 6 | 70 | 缺数据 | 0 | 0 | script_stage1 |
| 图中文字渲染一致性（OCR 校验） | 8 | 70 | 缺数据 | 0 | 0 | image |

## 自动回流建议

- `image`：角色 DNA/形体一致性（脸/发型/身形/手）、场景/构图连续性；回 n2d-image 重出脸/发型/身形/手部漂移镜头；必要时补 identity_registry.character_dna / reference_group / 身高表；视频侧主体漂移回 n2d-video 重出对应 clip。跨集体型漂移补 character_dna.身形/体型锁；外观判官(VAP)判失败按离群镜重出。表情连续(EXP1)失配回 n2d-image 补 expressions 表情参考重出情绪镜。表情过锁(EXP3·report-only)疑似 copy-paste 冻脸（高身份×零表情·IPRO）时，别只重抽单镜——解耦表情（AU/FACS 表情控件 / expressions 参考）或下调身份参考权重后整体重出情绪镜。辨识标记(MK1)漂移/丢失回 n2d-image 把 identity_registry.identity_marks 的标记锁补进出图 prompt 重出；获得型标记穿帮回 storyboard 核对获得集。；回 n2d-image 修场景定妆、光位锚、轴线视线、时辰天气、字幕安全区或尾帧；必要时回 n2d-video 重出接缝/相机轨迹/运动质量 clip。
- `script_stage2`：节奏密度、语义继承；回 n2d-script 阶段2重切镜头时长曲线、补钩子/爽点/集尾 cliffhanger。；回 n2d-script 阶段1/2或 prompt 生成层，修 raw/voiceover→storyboard→出图/出视频的语义谱系断点、VLM 判题失败与称谓口头禅漂移。伏笔兑现(SP1)：坑没填/兑现早于种下回 n2d-script 修 setup_payoff_ledger 与拆集边界。；定位镜头：EP01_CLIP01、Clip_01、EP01_CLIP02、Clip_02、EP01_CLIP03、Clip_03、EP01_CLIP04、Clip_04、EP01_CLIP05、Clip_05、EP01_CLIP06、Clip_06、EP01_CLIP07、Clip_07、EP01_CLIP08、Clip_08、EP01_CLIP09、Clip_09、EP01_CLIP10、Clip_10、EP01_CLIP11、Clip_11；定位产物：脚本/第1集/storyboard.json、出图/第1集/prompt、出视频/第1集/prompt

## 数据采集建议

- `n2d-score`：角色 DNA 一致性（服装/配饰）、字幕正确性、音画同步、音色一致性、风格一致性、状态百科、多模态漂移、视觉契约继承、交互/接触因果一致性、成片/包装一致性、生产操作一致性、UI/系统面板/HUD 一致性、音乐母题/leitmotif 一致性、图中文字渲染一致性（OCR 校验）；缺机器信号，先采集 consistency/mechanical/visual checks；不要在缺证据时直接返工。

## 证据

### 角色 DNA/形体一致性（脸/发型/身形/手）
- dashboard block[video_preflight/出图落档QC]: 输入首帧 image_qc 仍有 49 项硬阻断（崩脸/接缝断/降级精度近景/非法 CHAR）——图生视频会忠实把这些缺陷动起来，是最贵工位上的纯浪费。先回 n2d-image 修复并重跑 image_qc 再出视频。
### 角色 DNA 一致性（服装/配饰）
- 未采集该维度机器信号
### 场景/构图连续性
- dashboard block[compose/人物在场链]: 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CROWD_ZAYI。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
- dashboard block[compose/人物在场链]: 连续接缝里实体从上一 Clip 消失但未解释出画/离场/反打/画外保留：CHAR_ZHANG_LAODA。请在上一或下一 Clip 的 continuity.entry_exit/offscreen_presence 写清楚，或改为换场/空镜/时间跳跃接缝。
- dashboard block[compose/人物在场链]: 连续接缝里实体在下一 Clip 凭空出现但未解释入画/进场/现身：CROWD_ZAYI。请在 continuity.entry_exit 写入画动作，或用空镜/换场/时间跳跃隔开。
### 字幕正确性
- 未采集该维度机器信号
### 音画同步
- 未采集该维度机器信号
### 音色一致性
- 未采集该维度机器信号
### 节奏密度
- dashboard block[video/节奏密度(Rhythm)]: [production一致性升级:重复同维度] 节奏/留存 advisory 总分偏低：67.8。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=6e58cc9e054c，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
- dashboard block[video/节奏密度(Rhythm)]: [production一致性升级:重复同维度] 连续 11 个长镜聚集（EP01_CLIP01→EP01_CLIP02→EP01_CLIP03→EP01_CLIP04→EP01_CLIP05→EP01_CLIP06→EP01_CLIP07→EP01_CLIP08→EP01_CLIP09→EP01_CLIP10→EP01_CLIP11），疑节奏塌·掉留存。如确认为可接受，写入 生产数据/consistency_advisory_signoff_第1集.json 的 accepted 后复跑；finding_hash=01e346aa30e7，签收需包含 accepted=true/reviewer/reason/expires_at，并匹配 finding_hash 或 dimension+message_contains/loc_contains/shot。
### 风格一致性
- 未采集该维度机器信号
### 语义继承
- dashboard block[video/视频语义一致(VSEM)]: DINOv2 whole-frame similarity is below the configured VSEM threshold.
- dashboard block[video/视频语义一致(VSEM)]: DINOv2 whole-frame similarity is below the configured VSEM threshold.
### 状态百科
- 未采集该维度机器信号
### 多模态漂移
- 未采集该维度机器信号
### 视觉契约继承
- 未采集该维度机器信号
### 交互/接触因果一致性
- 未采集该维度机器信号
### 成片/包装一致性
- 未采集该维度机器信号
### 生产操作一致性
- 未采集该维度机器信号
### UI/系统面板/HUD 一致性
- 未采集该维度机器信号
### 音乐母题/leitmotif 一致性
- 未采集该维度机器信号
### 图中文字渲染一致性（OCR 校验）
- 未采集该维度机器信号
