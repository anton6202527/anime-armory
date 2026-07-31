---
name: mv-plan
description: 制MV clip/timeline 规划 — 从 视觉蓝图 + lyrics + beatgrid 生成 分镜/clip_plan.json、clip_plan.md、timeline_manifest.json，并为 mv-image/mv-video 生成逐 clip prompt 包、导演合约、身份继承和参考输入。Use when asked to MV分镜规划 / 自动拆clip / timeline_manifest / clip_plan / 按beatgrid规划MV. Triggers MV分镜规划, 自动拆clip, clip_plan, timeline_manifest, MV时间线, mv-plan.
---

# mv-plan — clip/timeline 规划

把 `创作区/制MV/<曲名>/` 里的 `节拍/beatgrid.json`、`词/lyrics.md`、`视觉蓝图.md` 和 `_设置.md` 变成机器可读的 MV 时间线。若项目选择 `歌曲输入时序=后配歌曲`，必须等最终 `歌/song.*` 入库并跑完真实 beatgrid 后再执行本阶段。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`MV规划粒度`、`卡点策略`、`MV视觉风格`。

## 产物

- `分镜/clip_plan.json`：给 `mv-image` / `mv-video` 的逐 clip 任务。
- `分镜/clip_plan.md`：人读版分镜。
- `分镜/timeline_manifest.json`：给 `mv-compose` 的剪辑真值源。
- `出图/段落/prompt/Clip_XXX.md`：首帧/尾帧需求。
- `出视频/prompt/Clip_XXX.md`：视频 motion prompt 任务。
- `分镜/semantic_prompts.json`：语义分镜引擎补写后的结构化留痕。

`clip_plan.json` 除时间线外还要沉淀 MV 的导演和一致性字段：`inputs_sha256`、`section_contract`、`action_family`、实际落在确认拍的 `action_peak`、`visual_motif`、`transition_motif`、`seam_contract`、`shot_design`、`identity_contract`、`reference_inputs`、`asset_ids`，以及 continuity 内的身份/服装/道具状态、场景拓扑、屏幕方向、视线、动作向量和光线状态。字段由本阶段初填，语义分镜引擎精修，后续直接消费。

## 用法

```bash
python3 skills/mv/mv-plan/scripts/plan_clips.py "<制MV作品根>"
python3 skills/mv/mv-plan/scripts/plan_clips.py "<制MV作品根>" --granularity 精细 --strategy 全程强卡点
```

## 工作流

1. 先跑 `mv-beat` 得到 `节拍/beatgrid.json`。没有最终歌/beatgrid 时不得用 rough 蓝图硬拆正式 timeline。
2. 跑本脚本 `plan_clips.py`。脚本入口会先过 `mv-craft/scripts/gate.py plan`：缺正式歌、beatgrid、视觉蓝图或后配歌曲仍是 rough 时阻断；需要字幕/唱演口型时也要求 `词/lyrics.md`，纯器乐且“无字幕+关闭口型”可合法无歌词。成功后生成 clip/timeline 框架并回写 `_进度.md`。
3. 跑语义分镜引擎。demo 可先查看框架；**正式付费出图必须注入覆盖全部 clip 的具体画面/动作并落 hash 收据**。AI 代理先把 `compose_prompts.py` 输出交给用户/导演复核，再用 `--mock-assessment` 注入；不得把通用动作占位直接送下游。
   - 语义补全时读取 `mv-video/references/action_knowledge.md`（动作家族/动作峰值/转场母题）和 `mv-image/references/visual_consistency.md`（身份锚点/主色/母题），优先补 `action_family/action_peak/visual_motif/transition_motif/shot_design`，再补 continuity；写回时同步落 `分镜/semantic_prompts.json`，便于复查和重跑。`compose_prompts.py` 默认要求覆盖全部 clip，缺字段会报错；临时局部注入才用 `--allow-partial`。
4. 跑 `mv-craft/scripts/identity_registry.py <作品根>`，生成身份/资产/参考注册表。
5. 跑 `mv-score` 产绑定当前 plan/beatgrid/song 的 deterministic pacing receipt；不设 `--threshold` 时只给证据、不把审美启发式做硬挡。`mv-score`/`pacing.py` 是**纯数值卡点引擎**（等长/downbeat/密度/总时长），从不读画面字段——视觉重复它看不见。
6. **出图前跑 `mv-review/scripts/shot_variety_audit.py <作品根> --write`**：读本阶段写好的 `shot_design`，在花积分前拦「同 (场景,景别,机位,运镜) 反复 / 连续同场景景别单调 / 副歌 key 镜静止运镜 / 单场景占比过高 / 母题过用 / 大变化镜头缺参考锚」。report-only（advisory·永不 block），被 image gate 与审片消费。命中就回本阶段换景别/机位/场景/补参考再出图——MV 命门除卡点就是视觉不重复。**同时跑 `mv-review/scripts/craft_audit.py <作品根> --write`（传统 MV 手法机检）**：查副歌复现无升级（每次副歌回归要加码，末副歌最大 payoff）/ 副歌运镜能量不高于主歌（无动静对比）/ hook 不上脸（副歌至少一次对镜演唱近景）/ 冷开场过长（首钩前 >8s）/ 关键镜单候选（key 镜出 2-3 张首帧候选再挑）/ bridge 不换气 / 词画零呼应。同为 report-only，被 image gate 消费。
7. **出图前跑 `mv-image/scripts/drift_risk.py <作品根> --write`**：不读像素、不花钱，用 clip_plan+identity_registry 的高危信号（近景/大表情/极端角度/逆光暗部/换装/长间隔复现/多主体同框/缺参考锚）预测哪些 clip 最易漂，high 风险镜出图前挂定妆/表情/场景参考。report-only，被 image gate 与 consistency_findings 消费；image_qc 已有实测脸警时自动回灌升档。
8. **正式大盘（≥12 clip）全量出图前跑 `scripts/pilot_matrix.py <作品根> --write`**：从 clip_plan（+drift_risk/shot_variety 报告）挑 3-5 个代表镜（开场钩/副歌爆点/最高漂移风险近景/最大运动/换装换景首镜）先打样，人工确认「脸像不像、风格对不对、爆点体感够不够」再全量——全量返工=整曲重烧积分，打样是最后一个免费决策点。report-only，正式大盘未打样时 image gate 提示（advisory·不拦）。
9. `mv-image` 按 `clip_plan.json` 出首帧和 `match_action` 接缝需要的尾帧，并登记每张图的 model/channel/prompt/hash 收据。
10. `mv-craft` 生成 production pack、真实 animatic、OTIO 并完成具名 picture lock。
11. `mv-video/scripts/video_jobs.py` 按锁定计划生成逐 clip 任务和可用的多镜头 `sequence_units`。
12. `mv-compose` 按 `timeline_manifest.json` 合成。

## 原则

- demo 没有 sections 时可产标为 `unverified_lyric_weight_estimate` 的脚手架；正式项目必须由 `_meta.section_timings` 具名确认并完整覆盖全曲，绝不把歌词字数估算伪装成音乐段落。
- `max_clips` 只是成本目标，不得吞并 verse→chorus 等签收段落边界。
- 副歌/主歌密度由歌曲与创意决定；切点取确认网格，机器报告密度，不用固定公式替代剪辑判断。
- 默认 `speed_mode=trim_hold`，保留动作原速度；逐镜显式 `retime` 才允许变速。
- 接缝必须分类：`beat_cut`/`section_break` 允许有意跳变，`match_action` 要尾帧目标并锁姿态相位、方向、视线、道具和光位，`terminal` 要稳定收束。
- `timeline_manifest.json` 是合成真值源；不要让 `mv-compose` 再凭文件名猜顺序。
- MV 不做跨集强一致，但同一首歌内必须继承视觉一致性包；动作知识库只提供可选动作家族，不覆盖歌曲情绪。
- 每个 clip 必须像传统 MV shot list 一样写清景别、机位、运镜、焦段感、走位、光影、场景 setup、首尾状态和参考输入；不要只写“好看/炫酷”。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 没有生成 `beatgrid.json` 就尝试切分镜头 | 必须先由 `mv-beat` 确定歌曲真实的重拍 (downbeat) 阵列后，才能进行有效卡点切分 |
| 后配歌曲路线未补最终歌就跑 mv-plan | 先补入最终成品歌，再跑 mv-beat；然后重跑/复核 mv-script |
| 让 compose 自己猜播放顺序 | compose 只能严格服从 `timeline_manifest.json`，如果该清单为空或内容未更新，合成将会混乱 |
| 生成后完全不让用户确认直接发往下游 | 本阶段结束后**必须**询问用户是否要人工调整或启动「语义分镜引擎」，否则画面将会高度重复或平淡 |
| 语义分镜只靠聊天记录 | 语义补全必须写回 `clip_plan.json`，并落 `semantic_prompts.json` 作为可追踪产物 |
