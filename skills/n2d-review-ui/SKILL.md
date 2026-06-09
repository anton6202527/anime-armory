---
name: n2d-review-ui
description: Build a local visual human-review UI for novel2drama/n2d episodes. Generate an infinite-canvas-style static HTML board and JSON manifest showing first frames, tail frames, video clips, seams, identity/reference images, QA flags, and machine scores from n2d-review/n2d-score outputs. Use when asked for 人审UI, 审片UI, 无限画布, 可视化审片, 首帧尾帧接缝可视化, QA flag 看板, 机器分看板, review canvas, visual review UI.
---

# n2d-review-ui — 人审无限画布

`n2d-review-ui` 把文本质检报告升级成可视化人审入口。它不替代 `n2d-review` / `n2d-score`，而是把它们的输出和真实素材放到同一张本地画布里：

- 分镜首帧、尾帧、clip MP4；
- clip 接缝：上一尾帧 vs 下一首帧；
- 定妆 / reference group 参考图；
- QA flag / 机器分 / 自动回流任务；
- 缺素材、缺尾帧、缺视频的可视标记。

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
```

输出：

```text
制漫剧/<剧名>/生产数据/review_ui_第N集.html
制漫剧/<剧名>/生产数据/review_ui_第N集.json
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

- **先机检，再人审**：UI 只负责聚合和呈现；低分来源仍由 `n2d-review` / `n2d-score` 产出。
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
