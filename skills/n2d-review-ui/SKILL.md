---
name: n2d-review-ui
description: "Build a local visual UI for novel2drama/n2d. Two zero-build (self-contained HTML + JSON) views — (1) per-episode 人审画布 `review_ui.py`: first/tail frames, clips, seams, identity refs, QA flags, machine scores; (2) work-level 生产看板 `board.py`: reads `_进度.md` and renders 作品→集(swimlane)→阶段(stage chips, progress-colored)→Clip(接力链 edges, QA status) for the whole drama, optionally served on 127.0.0.1 (the MVP of the PC端+无限画布 vision, see novel2drama Q&A Q36). Use when asked for 人审UI, 审片UI, 无限画布, 可视化审片, 生产看板, 整部进度画布, 制作过程可视化, 首帧尾帧接缝可视化, QA flag 看板, 机器分看板, review canvas, production board, visual review UI."
---

# n2d-review-ui — 人审无限画布 + 生产看板

`n2d-review-ui` 把文本质检报告升级成可视化入口。它不替代 `n2d-review` / `n2d-score`，只读它们和产线的产物（`_进度.md` / `storyboard.json` / `score_*.json` / 帧/clip），**单一真值源，绝不 fork 逻辑**。两个零构建（自带 HTML + vanilla JS，无 npm）视图，颗粒度不同：

**① 单集人审画布 `review_ui.py`**（细看一集，挑穿帮）：
- 分镜首帧、尾帧、clip MP4；clip 接缝（上尾帧 vs 下首帧）；定妆 / reference group 参考图；
- QA flag / 机器分 / 自动回流任务；缺素材、缺尾帧、缺视频的可视标记。

**② 整部生产看板 `board.py`**（看全局，一眼到哪了）—— PC端+无限画布愿景的 MVP（见 `novel2drama` Q&A Q36）：
- 读 `_进度.md` 状态机，渲染 **作品 → 集（泳道）→ 阶段（stage chips，按进度上色 done/进行中/未开始）→ Clip（接力链边 + QA 状态色）** 的可缩放/平移画布；
- 每集显示完成度条 + 下一步该跑哪个 skill（前沿，与 `n2d-progress` 同源）；有 `storyboard.json` 的集进一步铺开 Clip 卡 + 接力链；
- `--serve` 在 `127.0.0.1` 起本地服务（复用 `n2d-dashboard` 的本地服务先例），媒体相对路径直接解析。
- **跨集深链**：board 上点某个 Clip → 新标签打开该集 `review_ui_第N集.html#clip=<id>`，深画布自动**居中并高亮**该 Clip（点集头则打开该集深画布）；该集深画布未生成时弹提示给出生成命令。两层（全局看板 ↔ 单集深审）由 Clip id 串起，看板看全局、深画布挑穿帮。

## 输入 / 输出 / 读写边界

- **输入**：`_进度.md`、`storyboard.json`、首尾帧、clip MP4、identity registry、score/gate/mechanical/visual check JSON。
- **输出**：`生产数据/review_ui_第N集.html/json`、可选 `review_ui_findings_第N集.json`，以及整部 `board.html/json`。
- **读写边界**：只生成可视化和可消费 findings；不改进度、不改原始媒体、不执行返工队列。
- **契约关系**：阶段前沿与 `n2d-progress` 同源于 `n2d_contract.py`；导出的 findings 使用统一 `n2d_consistency_findings` kind，供 `n2d-batch` 消费。

```bash
python3 skills/n2d-review-ui/scripts/board.py <作品根> --write --markdown   # 生成 生产数据/board.html + board.json
python3 skills/n2d-review-ui/scripts/board.py <作品根> --serve [--port 8765] # 本地起服务看板
```
输出：`制漫剧/<剧名>/生产数据/board.html` + `board.json`。**只读不改任何状态**；要改进度/重跑仍走对应 skill。

## 触发

- 用户说：人审 UI、审片 UI、无限画布、可视化审片、review canvas。
- 成片或阶段审查后，需要从文本报告切到人工看片。
- `n2d-score` 输出低分，需要快速定位是哪条 Clip、哪个接缝、哪个定妆参考出问题。

## 工作流

先跑已有机检和评分：

```bash
python3 skills/n2d-score/scripts/score.py <作品根> 第N集 --run-checks --threshold 85
```

再生成画布：

```bash
python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --markdown
python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第N集 --write --export-findings --markdown
```

输出：

```text
制漫剧/<剧名>/生产数据/review_ui_第N集.html
制漫剧/<剧名>/生产数据/review_ui_第N集.json
制漫剧/<剧名>/生产数据/review_ui_findings_第N集.json   # --export-findings 时生成，kind=n2d_consistency_findings
```

HTML 是静态文件，可直接用浏览器打开；不需要开发服务器。若媒体文件已落档，浏览器会直接显示图片和视频。

## 数据来源

- `脚本/第N集/storyboard.json`：Clip 顺序、`firstframe_png`、`continuity.endframe_png`、`video_out`、转场、节奏。
- `出图/第N集/图片/`：首帧 / 尾帧兜底扫描。
- `出视频/第N集/视频/`：clip MP4 兜底扫描。
- `出图/共享/identity_registry.json`：角色 reference group；缺 registry 时兜底扫描 `出图/共享/图片/定妆*.png`。
- `生产数据/score_第N集.json`：总分、维度分、证据、自动回流任务。
- `生产数据/score_inputs/第N集_{consistency,mechanical,visual}.json`：机检输入摘要。

## 使用原则

- **先机检，再人审**：UI 负责聚合、呈现，并可用 `--export-findings` 把红黄 QA flag 导出成 batch 可消费的 `n2d_consistency_findings`；低分来源仍由 `n2d-review` / `n2d-score` 产出。
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
  `python3 skills/n2d-batch/scripts/queue.py plan <作品根> --from-consistency-findings <作品根>/生产数据/review_ui_findings_第N集.json`。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 忘了跑机检/评分直接生成画布 | 这会导致画布里完全没有机器分数、QA 阻断和一致性标注 |
| 把画布当成剪辑工具 | 画布只读、不修改任何生产状态。重修画面应由对应的 skill 和 batch 完成 |
| 将本地 HTML 里的文件跨设备发人审阅 | HTML 里使用的是相对路径（本地或本地服务）。若要共享审查，需走在线服务部署 |
