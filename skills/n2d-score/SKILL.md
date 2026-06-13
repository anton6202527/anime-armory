---
name: n2d-score
description: P2 automatic review scoring for n2d. Produce a machine score per episode across semantic continuity, state continuity, multimodal continuity, character consistency, outfit consistency, scene consistency, subtitle correctness, audio-visual sync, rhythm density, and style consistency; integrates visual checks such as image similarity, subtitle OCR, audio/video duration reconciliation, lip-sync risk/report ingestion, and final rhythm density; write score JSON/Markdown, feed n2d-review-ui visual human review canvas, and optionally enqueue low-score reruns into n2d-batch. Use when asked for 自动审片评分, 机器分, 每集评分, 低于阈值自动回流, 语义继承评分, 状态一致性评分, 多模态漂移评分, 角色一致性评分, 字幕正确性评分, 音画同步评分, 节奏密度评分, 图像相似度评分, 字幕OCR, 口型检测, 成片节奏密度, style score, review score.
---

# n2d-score — P2 自动审片评分体系

`n2d-score` 把 n2d-review 的确定性机检、n2d-dashboard 的生产数据、gate/review findings，以及更贴近实际观感的 visual checks 汇总成**每集机器分**。它不取代人判；它负责判断“这集是否低于阈值，应自动回流哪个 stage”。

## 输入 / 输出 / 读写边界

- **输入**：mechanical/consistency/visual checks、dashboard gate/review findings、identity drift、字幕/成片/配音/SRT/storyboard 时长信号。
- **输出**：`生产数据/score_inputs/*`、`score_第N集.json/md`，可选低分回流任务写入 `batch_queue.json`。
- **读写边界**：只评分和排队；不修改图/视频/字幕/配音，不直接判定最终美学质量。
- **契约关系**：finding kind、回流 stage、合规/水印等未映射 block 的处理与 `n2d_contract.py` 对齐；通过率阈值优先读 dashboard 阈值配置。

## 评分维度

| 维度 | 权重 | 主要来源 | 低分回流 |
|---|---:|---|---|
| 语义继承 | 8 | `semantic_continuity.py` 的 P0 语义谱系 Diff：voiceover/storyboard/出图/出视频 prompt 是否逐层继承 | `script_stage2` |
| 状态百科 | 8 | `state_continuity.py` 的 P1 动态百科：状态提前泄露、区间结束后泄露、开始后漏继承 | `image` |
| 多模态漂移 | 8 | `multimodal_consistency.py` 的 P2 非角色资产组 embedding 离群，按 identity_registry 排除角色 | `image` |
| 角色一致性 | 20 | `consistency_audit` 的 锚点门/脸/片内时序 + dashboard 角色类 block + **`n2d-identity` 跨集漂移**（早集稳·本集崩的回归，warn 级，不重复计片内崩脸） | `image` |
| 服装一致性 | 12 | 服装配色机检 | `image` |
| 场景一致性 | 12 | 场景机检 + 接缝接力 + 尾帧/下一首帧图像相似度 | `image` / 必要时 `video` |
| 字幕正确性 | 16 | `mechanical_check` 字幕 findings + 成片字幕 OCR 抽检 | `script_stage2` |
| 音画同步 | 16 | 配音/故事板/时长/原生音轨 findings + 成片/配音/SRT 时长对账 + 口型检测报告/口型风险 | `compose`，源头错回 `script_stage2` |
| 节奏密度 | 12 | 钩子/爽点/集尾留存信号 + 成片镜头密度/钩子间隔 | `script_stage2` |
| 风格一致性 | 12 | 风格机检 + 糊/低质 | `image` |

默认阈值 `85`。任一维度 block 会让该维度 fail；总分低于阈值或存在 fail 时，整集状态为 `fail`，输出 `auto_return_tasks`。缺机器信号的维度是 `insufficient_data`：只输出 `data_collection_tasks`，先采集检查信号，不直接排返工。

**无静默丢弃（P1）**：mechanical_check / dashboard 的 findings 若 `dim` 归不到评分维度（如 `完整性`=缺产物、`水印`=AI 标识、`视频`），不再被 `continue` 静默吞掉，而是落进 `unmapped_findings`。其中 **block 级会强制整集不给 `pass`（降 `warn`）并出 `triage_unmapped` 人判分诊任务**；warn/info 仅留痕。历史 bug：`BLOCK 完整性 / BLOCK 水印` 因关键词没命中被丢弃、不扣分、可放行。

## 标准命令

### 跑机检并评分

```bash
python3 skills/n2d-score/scripts/score.py <作品根> 第1集 --run-checks
```

输出：

```text
生产数据/score_inputs/第1集_consistency.json
生产数据/score_inputs/第1集_mechanical.json
生产数据/score_inputs/第1集_visual.json
生产数据/score_inputs/第1集_identity.json   # 跨集漂移（registry/insightface 可用时才有）
生产数据/score_第1集.json
生产数据/score_第1集.md
```

`第N集_identity.json` 由 `n2d-identity`（窗口=本集+前两集）产出的 `drift` 报告：单集评分本来对**跨集**角色漂移是盲的（片内每镜对定妆库都过，但相对前几集已经换了脸也看不出）。评分只采纳其中的**跨集回归**信号（某角色早集 ok、本集开始 block/临界），按 warn 级并进角色一致性——片内崩脸的 block 已由 `脸(G1)` 计，不在此重复扣分。`identity_registry.json` 缺失或 insightface/cv2 没装时该输入缺席，角色一致性按 `insufficient_data` 显式标注，不臆造通过。

`第N集_visual.json` 由 `scripts/visual_checks.py` 生成，包含：

- `image_similarity`：`storyboard.json` 的 `endframe_png` 对下一 Clip `firstframe_png` 做 dHash 相似度；
- `subtitle_ocr`：有成片、SRT、ffmpeg、Pillow、pytesseract 时抽检底部字幕；也可读取外部 OCR 报告；
- `av_duration`：成片 vs 配音主轨 vs SRT 末尾 vs storyboard 时长对账；
- `lip_sync`：读取外部 `lip_sync_第N集.json`/`syncnet_第N集.json`，否则根据视频 prompt 的 `mouth_visible=yes` 给风险提示；
- `final_rhythm_density`：按成片或 storyboard 时长计算镜头密度、钩子间隔、集尾钩子。

缺依赖或缺成片时 section 会写 `skipped=true`，不会静默当通过。

### 使用已缓存输入评分

```bash
python3 skills/n2d-score/scripts/score.py <作品根> 第1集
```

缺某维度机器信号时，该维度记 `insufficient_data` 并按 70 分处理，不会静默通过；但也不会进入 `auto_return_tasks`，避免“没证据就重出图/重剪”。先按 `data_collection_tasks` 跑 `--run-checks` 或补人判证据。

### 低分自动进入批量返工队列

```bash
python3 skills/n2d-score/scripts/score.py <作品根> 第1集 \
  --run-checks \
  --threshold 85 \
  --enqueue-low \
  --max-concurrency 1 \
  --max-retries 1
```

低分时会调用 `n2d-batch` 安全合并写入 `生产数据/batch_queue.json`，把每个低分维度聚合到对应 `return_to_stage`。例如语义继承/字幕/节奏低分 → `script_stage2` rerun；状态百科/多模态/角色/服装/风格低分 → `image` rerun；音画同步低分 → `compose` rerun。证据里出现 `Clip 2`、`Clip_02`、`EP01_CLIP02`、`镜头2` 或 `出图/出视频/合成/脚本/...` 路径时，会落到 `affected_shots` / `affected_artifacts`，让 batch 优先按最小范围返工。若只有缺数据，`--enqueue-low` 不会写 batch 队列。

### 生成可视化人审画布

```bash
python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第1集 --write --markdown
```

`n2d-review-ui` 会读取本 skill 的 `score_第N集.json` 和 `score_inputs/`，把评分维度、QA flag、visual checks 证据与首帧、尾帧、clip、接缝、定妆参考合并到静态 HTML/JSON。工业级人审以画布为入口，文本评分报告只做摘要和留档。

## 与其他横切层的关系

- `n2d-review` 负责产生确定性机检和 gate finding。
- `n2d-dashboard` 负责沉淀真实成本、耗时、重抽、QA 阻断、通过率；n2d-score 会读取 dashboard 的 episode 汇总作为辅助信号。**通过率下限与 dashboard 同源**：n2d-score 不再硬编码 0.75，按 `--pass-rate-floor` 或 `生产数据/alert_thresholds.json` 的 `final_pass_rate_floor`（与 dashboard 同一阈值）判定低通过率告警；都没配则不告警，避免 score 说有风险而 dashboard 没红灯的口径打架。
- `n2d-review-ui` 负责消费 score JSON/inputs，生成可视化人审画布，让人直接核首帧、尾帧、clip、接缝、定妆参考、QA flag 和机器分。
- `n2d-batch` 负责按 score 的 `auto_return_tasks` 排返工队列；缺数据只看 `data_collection_tasks`，不入 batch。

## 验收

一次成片或阶段审查后，至少应能看到：

- `生产数据/score_第N集.json`：机器可读分数、维度分、回流 stage；
- `生产数据/score_第N集.md`：人读表；
- `生产数据/review_ui_第N集.html/json`：可视化人审画布（评分后应由 `n2d-review-ui` 生成）；
- 若低于阈值且启用 `--enqueue-low`，`生产数据/batch_queue.json` 有对应 rerun 任务。

schema 见 `references/schema.md`。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 缺数据也算通过 | 缺数据维度固定按 70 分和 `insufficient_data`，必须补机检或人判 |
| 缺数据直接返工 | 缺数据只输出 `data_collection_tasks`，先采集检查信号；有 block/warn 证据后才入 `auto_return_tasks` |
| 把机器分当最终审片结论 | 机器分是回流触发器，人判仍负责语义/美学/口型细节 |
| 只生成分数不生成画布 | 跑 `n2d-review-ui`，把 score 和 visual checks 放进可视化人审 UI |
| 低分整集重跑 | 看 `auto_return_tasks.return_to_stage`、`affected_shots`、`affected_artifacts`，只回最低必要 stage 和能定位到的 Clip/产物 |
| 只看总分不看维度 | 维度分决定回流方向，总分只决定是否放行 |
