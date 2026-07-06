---
name: comic-image
description: 画漫画出图阶段。Use when preparing shared visual references, per-panel image prompts, generation job packets, registering panel images, or checking textless comic art for projects under 创作区/画漫画. Produces 出图/共享 references, 出图/第N话/prompt job packs, and 出图/第N话/panels images. Triggers 漫画出图, 分格出图, panel image, 漫画prompt, 角色定妆, 场景参考, 道具参考, comic-image.
---

# comic-image — 漫画出图包与面板图

把漫画脚本和排版转换成共享参考、逐格 prompt/job 包和面板图登记。MVP 不绑定任何具体出图后端；没有可执行后端时，仍然产出可手工执行的 job 包和 manifest。

## 输入

- `_设置.md`：生图模型、生图渠道、参考一致性策略、基础视觉风格。
- `设定库/story_bible.md`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/layout.json`。
- `出图/共享/` 现有角色、场景、道具参考。

## 输出

- `出图/共享/prompt/`：角色、场景、道具、风格参考任务。
- `出图/共享/图片/`：共享参考图登记位置。
- `出图/第N话/prompt/panel_jobs.json`：逐格出图任务包，schema 见 `references/prompt_job_schema.md`。
- `出图/第N话/panels/P001.png` 等面板图。
- `_进度.md`：job 包完成标 `出图包=✅`；面板图齐全标 `出图=✅`。

## 怎么跑

先自动探测并写入本项目生图选择点；检测到 Codex 且 `image_generation` 可用时优先 Codex：

```bash
python3 skills/comic-image/scripts/detect_image_backend.py "创作区/画漫画/作品名" --write-settings
```

已有 `panel_script.json` 和 `layout.json` 后，可生成逐格出图任务包：

```bash
python3 skills/comic-image/scripts/build_panel_jobs.py "创作区/画漫画/作品名" --chapter 第1话
```

脚本只写 `panel_jobs.json` 和 `出图/共享/prompt/00_索引.md`，不调用任何生图后端；它会把本话 `出图包` 标为 `✅`，但不会把 `出图` 标完成。

若已选择 `生图渠道=Codex CLI`，可逐格生成真实 PNG：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话
```

建议先 `--targets P001 --limit 1` 做 smoke test；通过后再批跑。生成完成会更新 `panel_jobs.json` 的 `result_path/status`，全部面板就绪时把本话 `出图` 标为 `✅`。

预算充足或后端偶发失败时，可加多次尝试：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --max-attempts 3
```

若人工看图后需要重抽某几格，用 `--force --targets P003,P007`；旧图会归档到 `出图/第N话/candidates/<panel_id>/`，新图覆盖正式 `panels/Pxxx.png` 并写入 job history。

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003,P007 --force --max-attempts 3
```

需要从“当前进度”自动推进一话、按预算多抽并衔接合成/审查时，使用 `comic-batch`；`comic-image` 仍只负责出图阶段本身。

## 工作流

1. 先查共享参考是否足够：主角、常驻角色、关键场景、关键道具、标志服装至少要有可传给模型的参考或明确待补任务。
2. 若共享参考不足，先写 `出图/共享/prompt/00_索引.md` 和参考任务，不直接批量生成面板图。
3. 读 `panel_script.json` 和 `layout.json`，给每格生成 prompt/job。prompt 必须包含画面事实、构图、角色状态、参考 ID、禁止漂移项和留白/气泡预留。
4. 明确要求“无字画面”或“空白气泡”，不要让模型直接生成中文正文。
5. 如果用户已在外部生成图片，把文件放入 `出图/第N话/panels/`，并更新 job 包里的 `result_path`、`status`、`source`。
6. job 包齐全后可把 `出图包` 标 `✅`；所有必需 panel 图就绪后把 `出图` 标 `✅`。
7. 预算允许多抽时，保留失败和重抽证据；不要把候选图混进正式 `panels/`，正式目录只留当前采纳版本。

## Prompt 要点

- 一格一个主动作或主信息。
- 角色身份锚、服装、发型、标志物要写具体。
- 场景与道具引用写成结构化 ID 或清晰路径。
- 需要气泡的区域写“预留空白区域”，但不写台词正文。
- 复杂动作拆分为多格或标注分层/合成建议。
- 输出尺寸跟随 `layout.json` 的面板比例。

## 不做什么

- 不嵌最终台词；那是 `comic-compose`。
- 不静默选择付费后端；出图前必须确认模型、渠道、成本和覆盖范围。
- 不跳过共享参考直接生产核心角色高风险面板。
