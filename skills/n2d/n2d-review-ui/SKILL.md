---
name: n2d-review-ui
description: "Build local visual UI for n2d. Zero-build HTML + JSON views: (1) per-episode 人审画布 `review_ui.py`; (2) work-level 生产看板 `board.py`; (3) per-episode 工作台 `episode_app.py` that aggregates dashboard/board/review/score/gate data for desktop app display. Use when asked for 人审UI, 审片UI, 无限画布, 可视化审片, 生产看板, 单集工作台, 按集显示生产数据, 制作过程可视化, 首帧尾帧接缝可视化, QA flag 看板, 机器分看板, review canvas, production board, visual review UI."
---

# n2d-review-ui — 人审无限画布 + 生产看板

`n2d-review-ui` 把文本质检报告升级成可视化入口。它不替代 `n2d-review` / `n2d-score`，只读它们和产线的产物（`_进度.md` / `storyboard.json` / `score_*.json` / `dashboard.json` / gate findings / 帧/clip），**单一真值源，绝不 fork 逻辑**。三个零构建（自带 HTML + vanilla JS，无 npm）视图，颗粒度不同：

**① 单集人审画布 `review_ui.py`**（细看一集，挑穿帮）：
- 分镜首帧、中段锚帧、尾帧、后端实际入参、clip MP4；clip 接缝（上尾帧 vs 下首帧）；定妆 / reference group 参考图；
- QA flag / 机器分 / 自动回流任务；缺素材、缺尾帧、缺视频的可视标记。

**② 整部生产看板 `board.py`**（看全局，一眼到哪了）—— PC端+无限画布愿景的 MVP（见 `n2d` Q&A Q36）：
- 读 `_进度.md` 状态机，渲染 **作品 → 集（泳道）→ 阶段（stage chips，按进度上色 done/进行中/未开始）→ Clip（接力链边 + QA 状态色）** 的可缩放/平移画布；
- 每集显示完成度条 + 下一步该跑哪个 skill（前沿，与 `n2d-progress` 同源）+ dashboard 里的成本/通过率/重抽率/QA 数；有 `storyboard.json` 的集进一步铺开 Clip 卡 + 接力链；
- `--serve` 在 `127.0.0.1` 起本地服务（复用 `n2d-dashboard` 的本地服务先例），媒体相对路径直接解析。
- **跨集深链**：board 上点集头 → 新标签打开 `episode_app_第N集.html` 单集工作台；点某个 Clip → 新标签打开该集 `review_ui_第N集.html#clip=<id>`，深画布自动**居中并高亮**该 Clip。看板看全局，单集工作台负责状态/问题/证据，深画布挑穿帮。

**③ 单集工作台 `episode_app.py`**（按集生产驾驶舱）：
- 聚合 `_进度.md` / `dashboard.json` / `board.json` / `review_ui_第N集.json` / `score_第N集.json` / `consistency_ledger_第N集.json` / `gate_findings_*_第N集.json`；
- 输出稳定的 `episode_index.json` 和 `episodes/第N集.json`，desktop app 优先读这两个聚合契约，而不是直接扫几十个散 JSON；
- HTML 分 `总览 / 阶段 / 镜头 / 问题 / 证据`，其中“问题”按 `return_to_stage` 分组，优先回答“回哪个阶段修”。

## 输入 / 输出 / 读写边界

- **输入**：`_进度.md`、`storyboard.json`、首尾帧、clip MP4、identity registry、score/gate/mechanical/visual check JSON。
- **输出**：`生产数据/review_ui_第N集.html/json`、可选 `review_ui_findings_第N集.json`，整部 `board.html/json`，单集工作台 `episode_app_第N集.html` + `episodes/第N集.json` + `episode_index.json`，以及人审校准 `review_calibration_cases.json`、`review_calibration.json/md`。
- **读写边界**：只生成可视化和可消费 findings；不改进度、不改原始媒体、不执行返工队列。
- **契约关系**：阶段前沿与 `n2d-progress` 同源于 `n2d_contract.py`；导出的 findings 使用统一 `n2d_consistency_findings` kind，供 `n2d-batch` 消费。

```bash
python3 skills/n2d/n2d-review-ui/scripts/board.py <作品根> --write --markdown   # 生成 生产数据/board.html + board.json
python3 skills/n2d/n2d-review-ui/scripts/board.py <作品根> --serve [--port 8765] # 本地起服务看板
python3 skills/n2d/n2d-review-ui/scripts/episode_app.py <作品根> --episode 第N集 --write --index
python3 skills/n2d/n2d-review-ui/scripts/episode_app.py <作品根> --all --write   # 生成所有集工作台 + episode_index.json
```
输出：`创作区/制漫剧/<剧名>/生产数据/board.html` + `board.json`。**只读不改任何状态**；要改进度/重跑仍走对应 skill。

## 触发

- 用户说：人审 UI、审片 UI、无限画布、可视化审片、review canvas。
- 成片或阶段审查后，需要从文本报告切到人工看片。
- `n2d-score` 输出低分，需要快速定位是哪条 Clip、哪个接缝、哪个定妆参考出问题。

## 工作流

先跑已有机检和评分：

```bash
python3 skills/n2d/n2d-score/scripts/score.py <作品根> 第N集 --run-checks --threshold 85
```

再生成画布：

```bash
python3 skills/n2d/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --markdown
python3 skills/n2d/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --export-findings --markdown
```

输出：

```text
创作区/制漫剧/<剧名>/生产数据/review_ui_第N集.html
创作区/制漫剧/<剧名>/生产数据/review_ui_第N集.json
创作区/制漫剧/<剧名>/生产数据/review_ui_findings_第N集.json   # --export-findings 时生成，kind=n2d_consistency_findings
```

HTML 是静态文件，可直接用浏览器打开；不需要开发服务器。若媒体文件已落档，浏览器会直接显示图片和视频。`n2d/run.py next` 到验收包时会自动跑本脚本并刷新同作品的 `board.html`。若手工单跑 `dashboard.py gate` / `score.py`，仍需手工跑本脚本或通过 `n2d/run.py next` 收尾。

单集工作台输出：

```text
创作区/制漫剧/<剧名>/生产数据/episode_index.json
创作区/制漫剧/<剧名>/生产数据/episodes/第N集.json
创作区/制漫剧/<剧名>/生产数据/episode_app_第N集.html
```

`episode_index.json` 给 desktop app 左侧集列表用；`episodes/第N集.json` 给单集工作台用。原始报告仍保留在“证据”页，默认界面只展示状态、问题和下一步。

## 数据来源

- `脚本/第N集/storyboard.json`：Clip 顺序、`firstframe_png`、`continuity.anchors[]`/`midframe`、`continuity.endframe_png`、`video_out`、转场、节奏。登记路径存在时优先使用；登记路径失效时按 Clip 编号兜底扫描真实产物，避免 `EP01_CLIP01` 这类逻辑 ID 与实际 `Clip_01_标题.mp4` 命名不同导致假缺文件。
- `出图/第N集/图片/`：首帧 / 尾帧兜底扫描。
- `出视频/第N集/视频/`：clip MP4 兜底扫描。
- `生产数据/video_batch_第N集_*.json`：读取 `anchor_consumption` 与 `multiframe_images_rel`，展示后端实际消费了哪些首/中/尾锚帧。
- `出图/共享/identity_registry.json`：角色 reference group；缺 registry 时兜底扫描 `出图/共享/图片/定妆*.png`。
- `生产数据/score_第N集.json`：总分、维度分、证据、自动回流任务。
- `生产数据/score_inputs/第N集_{consistency,mechanical,visual}.json`：机检输入摘要。

## 使用原则

- **先机检，再人审**：UI 负责聚合、呈现，并可用 `--export-findings` 把红黄 QA flag 导出成 batch 可消费的 `n2d_consistency_findings`；低分来源仍由 `n2d-review` / `n2d-score` 产出。
- **批量人审前先校准**：同一批审片员要先跑少量金标 case，校准 block/warn/pass 口径；否则同样的脸漂、接缝跳切、字幕遮挡会被不同人判成不同等级，后续 batch 回流和评分阈值都会失真。
- **先看红黄，再看全片**：画布支持按 block / warn / 缺素材筛选，先处理阻断项。
- **接缝并排看**：每个接缝都展示“上一尾帧 → 下一首帧”，用于判断跳切、尾帧没接上、构图突变。
- **定妆同屏比对**：角色参考图在左侧固定区域，审片时和每个 Clip 的首帧/视频并排比。
- **缺文件也是 QA**：首帧、尾帧、视频路径登记了但不存在，会在卡片上直接标出。

## 回流

UI 本身不改进度、不重跑、不提交任务。发现问题后按：

- 首帧 / 定妆 / 风格 / 场景问题：回 `n2d-image`。
- 视频运动 / 片内漂移 / 接缝问题：回 `n2d-video`，必要时先补尾帧。
- 字幕 / 时长 / 音画同步：回 `n2d-compose` 或 `n2d-script` 阶段2。
- 机器分低于阈值：用 `n2d-score --enqueue-low` 写入 `n2d-batch`。
- 要把画布里的红黄 flag 直接排入返工队列：先生成 findings，再执行
  `python3 skills/n2d/n2d-batch/scripts/queue.py plan <作品根> --from-consistency-findings <作品根>/生产数据/review_ui_findings_第N集.json`。

## 人审校准

```bash
# 初始化金标 case 模板，人工把 asset/gold_label/rationale 补实
python3 skills/n2d/n2d-review-ui/scripts/calibration.py init <作品根>

# 收集 reviewer 投票后评分；votes 支持 CSV 或 JSONL
python3 skills/n2d/n2d-review-ui/scripts/calibration.py score <作品根> --votes votes.csv --write
```

`votes.csv` 最少字段：

```csv
case_id,reviewer,label
CAL_FACE_001,alice,block
CAL_FACE_001,bob,warn
```

输出 `生产数据/review_calibration.json/md`。`status=needs_calibration` 时，先统一口径或补训练样例，再进入正式批量验收；它不自动改 review 结论，只给人工验收一致性证据。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 忘了跑机检/评分直接生成画布 | 这会导致画布里完全没有机器分数、QA 阻断和一致性标注 |
| 把画布当成剪辑工具 | 画布只读、不修改任何生产状态。重修画面应由对应的 skill 和 batch 完成 |
| 将本地 HTML 里的文件跨设备发人审阅 | HTML 里使用的是相对路径（本地或本地服务）。若要共享审查，需走在线服务部署 |
