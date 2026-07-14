---
name: comic-batch
description: 画漫画流程推进与批跑控制。Use when advancing a comic chapter from its current _进度.md frontier, batch-running panel image generation, rerolling selected panels, or chaining image -> compose -> review for projects under 创作区/画漫画. It recognizes comic-name and comic-finishing frontiers, orchestrates existing comic-* stage scripts, and keeps paid/high-cost generation explicit. Triggers 漫画批跑, 漫画自动推进, 抽到满意为止, 批量出图, 重抽漫画格, comic-batch.
---

# comic-batch — 漫画流程推进与批跑

`comic-batch` 是漫画线的流程层：读取 `_进度.md`，自动运行可复算阶段，但把ネーム和 layout 当作显式编辑签收点。首次推进到这两步只生成 `draft` 并正常停止；只有人工执行 `draft → review → approved`、SHA 检查通过且阶段写成 ✅ 后，批跑才继续收尾、出图包、出图与合成。创作阶段（源本/企划、漫画脚本）仍不自动化，审查阶段也不代替人工验收。

`传统原稿流程=关闭` 只跳过原稿收尾，不再跳过ネーム；已签收 name 是所有 layout adapter 的强制编辑合同。出图前编排器先运行 layout `--check`，传统收尾开启时再运行 finishing `--check`，然后才进入 `image_preflight`。因此即使手动指定 `--stage image`，也不能绕过 draft、失效审批或 stale 上游。

## 适用场景

- 用户已经确认付费/高成本出图，要求继续批量生成面板图。
- 预算充足，需要对失败或不满意面板多次重抽。
- 出图齐全后，需要继续衔接嵌字合成或审查。
- 一话中途被打断，需要从 `_进度.md` 和 job 包恢复；若停在 name/layout draft，脚本会打印提交复核和签收命令并清洁退出，不会重复覆盖草案或自动签收。

## 输入

- `创作区/画漫画/<作品>/_进度.md`。
- `出图/第N话/prompt/panel_jobs.json`。
- `_设置.md` 里的 `生图模型`、`生图渠道`、`基础视觉风格`。

## 怎么跑

从当前进度自动判断阶段；当前前沿为 `出图` 时，会调用 `comic-image` 的 Codex runner：

```bash
python3 skills/comic-batch/scripts/run.py "创作区/画漫画/作品名" --chapter 第1话 --image-max-attempts 3
```

只跑部分格：

```bash
python3 skills/comic-batch/scripts/run.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003,P007 --image-max-attempts 3
```

人工看图后重抽指定格；旧图会归档到 `出图/第N话/candidates/<panel_id>/`：

```bash
python3 skills/comic-batch/scripts/run.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003,P007 --force --image-max-attempts 3
```

## 费用与覆盖

付费/高成本动作必须由用户在会话中确认模型、渠道、费用策略和覆盖范围。确认后同一批次按参数执行；后续追加重抽仍应明确目标格和是否覆盖正式 `panels/Pxxx.png`。

## 完成判定

- `name_board.workflow_status` 或 `layout.workflow_status` 为 `draft/review` 时，批跑返回成功等待人工处理；不会继续下一阶段，也不会写假 `✅`。
- `layout --check` 会复核 name/layout schema、validator、approval subject SHA 与当前 panel script/name/settings；失败时连手动 image 模式也停止。
- `finishing --check` 会复核 plan 覆盖和 panel script/name/layout/settings SHA；缺输入、空计划和 stale 都停止。
- `comic-batch` 调用出图 runner 前先跑 `skills/comic-review/scripts/gate.py --stage image_preflight`；被 gate block 时不启动付费/批量出图。
- `comic-image` runner 会在所有 job `ready` 且 PNG 有效时把 `_进度.md` 的 `出图` 标为 `✅`；`post_qc=block` 的格子标 `qc_block`，不算 ready。
- runner 每张落盘后先做目标格 post-QC。指定 `--targets` / `--limit` 的验样批次若尚未补齐整话，只报告该批通过并延后整话 gate；全部 panel 都是 `ready` 且文件存在后，`comic-batch` 才跑 `skills/comic-review/scripts/gate.py --stage image` 刷新整话风格与角色一致性报告。禁止用“未生成的其它格”把已通过的小批验样误报成失败。
- `comic-batch` 只在阶段脚本成功时继续，不吞掉失败。
- 出图完成后下一步通常是 `comic-compose`；正式发布前仍要跑 `comic-review`。

## 不做什么

- 不绕过 `comic-image` 的 job 包和状态登记。
- 不自动购买字体、启用未知付费模型或覆盖已经发布的导出图。
- 不把候选图直接混入正式交付；正式图只在 `panels/`，候选和旧图进 `candidates/`。
