---
name: mv-score
description: 在正式调用生图后端/生视频模型消耗大量积分前，对 MV 的视觉蓝图和分镜剧本（clip_plan）进行"视觉表现力与卡点节奏"的打分与体检。拦截平庸、冗长或不符合 MV 节奏规律的分镜设计。Use when asked to 评MV分镜, MV体检, 评价MV蓝图, 看看这MV设计行不行, MV评分. Triggers 评MV, MV分镜打分, MV体检, 评价MV蓝图, MV能不能火, MV评分, mv-score.
---

# mv-score — MV 视觉蓝图与分镜体检

生成视频的成本是整个管线中最高的。如果在 `mv-plan` 阶段规划出的分镜过于平淡、没有爽点、或者运镜设计不合理，后续花再多钱生成的画面也救不回成片的质量。

`mv-score` 充当生成前的**质量闸门**。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/mv-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

## 确定性卡点前奏（先机检，后 LLM）

卡点节奏不是只能"凭感觉"判——「副歌快切 / 主歌长镜 / clip 不等长 / 总时长≈歌长 / 切点踩鼓点」全是可机算的。**在任何生图/生视频烧积分前**，先跑确定性前奏把这些变成数字，喂给下面的 LLM 语义评分当卡点维度依据：

```bash
python3 skills/mv-score/scripts/score_pacing.py 制MV/<曲名>/ [--json]
```

它读 `分镜/clip_plan.json` + `节拍/beatgrid.json`（+ 成品歌量真长，缺则退回 beatgrid.duration），输出 `评分/pacing_prescore.json`，四个机器指标 + 一个 `pacing_score`(0-10) 机器先验：

1. **等长 clip CV** —— `(极差/均值)` 过低 → 疑似等长不卡点（MV 命门）。
2. **总时长 vs 歌长** —— 规划 clip 总时长是否≈歌长（容差按 10% 取大）。
3. **切点踩鼓点率** —— clip 内部边界落在 downbeat ±容差内的比例。
4. **副歌 vs 主歌密度对比** —— 副歌 clips/秒 是否 ≥ 主歌（>1 = 副歌更快切，符合规律）。

**同源引擎**：这四个指标来自共享模块 `mv-craft/scripts/pacing.py`（纯函数、无 IO），与 `mv-review`（`mv_check.py` 的事后质检）**共用同一套数学**——事前闸门和事后体检对"卡点节奏"的判据完全一致，不再各写一份。机器先验**不替代** LLM 终判：它只是把"卡点与节奏张力"这一维从凭感觉提升为有量化依据。

## pre-spend 真闸门 + 受影响 clip 回流（--threshold / --enqueue）

不给阈值时它只是**建议性**机检（exit 0，供 LLM 参考）。给 `--threshold` 后它升级为**花积分前的真闸门**：综合 `pacing_score`（折百分制）或任一关键卡点维度（疑等长 / 总时长差大 / 踩鼓点率<0.5 / 副歌不快）低于阈值 → **exit 1 拦截**，在出图/出视频前把平庸/不卡点的分镜挡下来，并打印「该回哪个上游 stage」。

```bash
# 阈值≤10 视为十分制（贴 pacing_score）；>10 视为百分制（贴综合分）
python3 skills/mv-score/scripts/score_pacing.py 制MV/<曲名>/ --threshold 80 \
    --dim 视觉记忆点=55 --dim 崩脸=40 \      # 可选：把 LLM 语义维度分回灌进闸门
    --enqueue                                 # 可选：落回流清单文件
```

**受影响 clip → 源头 stage 映射（MV 专属）**，写进 `pacing_prescore.json` 的 `affected_clips`（含 `clip_id` + `return_to_stage` + `reason` + `detail`）：

| 成因 | reason | 回流 stage |
|---|---|---|
| clip 切点未踩 downbeat / clip 时长离群 | `off_downbeat` / `duration_outlier` | **mv-plan**（重拆时长、对齐 beatgrid） |
| 视觉记忆点弱 / 蓝图问题（LLM 语义维度低） | `low_semantic_dim` | **mv-script**（重梳视觉蓝图） |
| 崩脸 / 单曲视觉一致性差（LLM 语义维度低） | `low_semantic_dim` | **mv-image**（重出图、锁身份） |

确定性卡点成因（前两类）机检直接定位到具体 clip；语义成因靠 `--dim 维度名=分` 把 LLM 打的视觉维度回灌进来，低于阈值即路由到 mv-script/mv-image（点名了 clip 就记 clip_id，没点名记 `*`=整段重做）。

加 `--enqueue` 时额外写 `评分/回流清单.json`（`kind=mv_score_rework_queue`）：按 `return_to_stage` 聚合受影响 clip，**mv 自有格式、不依赖 n2d-batch**，人或工具都能消费——按每个 task 的 `return_to_stage` 重跑对应 mv-* skill 即可。

退出码：clip_plan/beatgrid 缺失或损坏 → 2；`--threshold` 下被拦截 → 1；否则 0。判据全在 `score_pacing.py` 的纯函数里（`decide_block` / `pacing_affected_clips` / `semantic_affected_clips` / `map_semantic_dim_stage`），mv 线自包含、可单测。

## 评分维度 (1-10分)
1. **视觉记忆点 (Visual Hook)**：场景和角色设定是否有辨识度？是否贴合歌曲的氛围？
2. **卡点与节奏张力 (Beat & Pacing)**：分镜是否遵循了「主歌长镜叙事、副歌快切爆发」的规律？高潮部分的时长划分是否能带来视觉冲击？**先读 `score_pacing.py` 的机器预评分**（等长 CV / 总时长对账 / 踩鼓点率 / 副歌密度对比），在其量化结果上做语义判断，不要孤立凭画面描述猜节奏。
3. **连贯性与运镜 (Continuity & Camera)**：镜头运动（推、拉、摇、移）是否服务于音乐情绪？相邻镜头的转场（如匹配剪辑、动势衔接）设计是否顺畅？
4. **动作想象力 (Action Vocabulary)**：是否按 `mv-video/references/action_knowledge.md` 选择了动作家族、动作峰值和转场母题？副歌是否有高光动作，主歌是否不过度塞动作？
5. **单曲视觉一致性 (Single-song Consistency)**：是否继承 `mv-image/references/visual_consistency.md` 的身份锚点、主色、段落 look 和母题，避免一支歌内换脸/换画风？
6. **情感共鸣 (Emotional Payoff)**：画面表现的动作和情节，是否兑现了歌曲高潮部分的情感承诺？

## 工作流
1. **读取物料**：读取 `视觉蓝图.md` 和 `分镜/clip_plan.json`。若项目是 `歌曲输入时序=后配歌曲` 且最终歌/beatgrid 未入库，只能评 rough 视觉方向，不给正式分镜放行。
1b. **确定性卡点前奏（在 LLM 之前）**：跑 `scripts/score_pacing.py`（见上节），得到 `评分/pacing_prescore.json` 的四个机器指标 + `pacing_score`。这是 0 积分消耗的机检，让"副歌快切爆发"等节奏判断从凭感觉变成可量化，与 `mv-review` 同源。
2. **LLM 语义评分**：结合音乐的结构（如 BPM 和段落）**和上一步的机器预评分**，分析目前的镜头切分和画面内容，按上述维度打分。卡点/节奏维度以 `pacing_prescore.json` 的量化结果为依据。
   - 评分时必须检查 `action_family/action_peak/visual_motif/transition_motif` 是否存在且服务歌曲；缺失则建议回 `mv-plan` 语义分镜引擎补全。
3. **决策与回流**：先跑带 `--threshold` 的真闸门（见上节）；exit 1 即在出图前被挡，按 `affected_clips` / `回流清单.json` 回到对应上游 stage（卡点→mv-plan、蓝图→mv-script、崩脸→mv-image）。LLM 综合判读：
   - **高分 (≥80)**：概念极佳，可以放心推进到 `mv-image` 出图。
   - **中分 (60-79)**：局部修改（如把副歌某几个平淡的镜头改成强烈的冲击镜头），然后推进。
   - **低分 (<60)**：打回 `mv-plan` 甚至重新梳理 `视觉蓝图.md`。

## 执行方式
先跑确定性卡点前奏（0 积分），再让 LLM 在其量化结果上做语义评分：

```bash
python3 skills/mv-score/scripts/score_pacing.py 制MV/<曲名>/        # 机器卡点预评分 → 评分/pacing_prescore.json
cat 制MV/<曲名>/视觉蓝图.md 制MV/<曲名>/分镜/clip_plan.json 制MV/<曲名>/评分/pacing_prescore.json
```
然后让 LLM 阅读视觉蓝图 + clip_plan + 机器预评分，给出综合评分报告（视觉维度靠 LLM，卡点/节奏维度以机器指标为准）。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 脱离音乐的情绪盲目打分 | 评判卡点和张力的基础是“歌曲当时的 BPM 与高潮在哪”，不能孤立地仅看画面描述 |
| 后配歌曲 rough 蓝图当正式 clip_plan 放行 | 等最终歌入库并跑 mv-beat/mv-plan 后再做正式评分 |
| 因为个别镜头小扣分就全盘废弃 | 对于中分(60-79)的设计，大模型应提供局部的 prompt 修正建议，而不是强迫推翻已确认的视觉蓝图 |
