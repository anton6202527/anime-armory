---
name: comic-batch
description: 画漫画流程推进与批跑控制。Use when advancing a comic chapter from its current _进度.md frontier, batch-running panel image generation, rerolling selected panels, or chaining image -> compose -> review for projects under 创作区/画漫画. It recognizes comic-name and comic-finishing frontiers, orchestrates existing comic-* stage scripts, and keeps paid/high-cost generation explicit. Triggers 漫画批跑, 漫画自动推进, 抽到满意为止, 批量出图, 重抽漫画格, comic-batch.
---

# comic-batch — 漫画流程推进与批跑

`comic-batch` 是漫画线的流程层：读取 `_进度.md`，从当前前沿起**自动 chain 免费确定性阶段**（缩略分镜→页面排版→原稿收尾→出图包→嵌字合成的 lettering/导出），出图阶段带 gate 批跑，审查阶段只产 review gate 报告、不代替人工把 `审查` 标 ✅。创作阶段（源本/企划、漫画脚本）不自动化。`传统原稿流程=关闭` 或旧进度表缺列时自动跳过对应阶段。它不替代各 stage skill 的判断，只负责批量执行、重抽、候选归档和衔接。出图前必须先跑 `comic-review` 的 `image_preflight` gate（runner 本身也内置该 gate，编排层跑过后以 `--skip-gate` 免重复）；出图后必须跑 `image` gate，不能把 `qc_block` 或角色/风格一致性 block 继续传给合成。

## 适用场景

- 用户已经确认付费/高成本出图，要求继续批量生成面板图。
- 预算充足，需要对失败或不满意面板多次重抽。
- 出图齐全后，需要继续衔接嵌字合成或审查。
- 一话中途被打断，需要从 `_进度.md` 和 job 包恢复；如果前沿停在缩略分镜、页面排版或原稿收尾，它会提示先用对应 stage skill，而不会自动跳过传统工艺层。

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

- `comic-batch` 调用出图 runner 前先跑 `skills/comic-review/scripts/gate.py --stage image_preflight`；被 gate block 时不启动付费/批量出图。
- `comic-image` runner 会在所有 job `ready` 且 PNG 有效时把 `_进度.md` 的 `出图` 标为 `✅`；`post_qc=block` 的格子标 `qc_block`，不算 ready。
- runner 完成后 `comic-batch` 会跑 `skills/comic-review/scripts/gate.py --stage image`，刷新风格一致性和角色一致性报告。
- `comic-batch` 只在阶段脚本成功时继续，不吞掉失败。
- 出图完成后下一步通常是 `comic-compose`；正式发布前仍要跑 `comic-review`。

## 不做什么

- 不绕过 `comic-image` 的 job 包和状态登记。
- 不自动购买字体、启用未知付费模型或覆盖已经发布的导出图。
- 不把候选图直接混入正式交付；正式图只在 `panels/`，候选和旧图进 `candidates/`。
