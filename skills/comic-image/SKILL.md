---
name: comic-image
description: 画漫画出图阶段。Use when preparing shared visual references, per-panel image prompts, generation job packets, registering panel images, or checking textless comic art for projects under 创作区/画漫画. Produces 出图/共享 references, 出图/第N话/prompt job packs, and 出图/第N话/panels images. Triggers 漫画出图, 分格出图, panel image, 漫画prompt, 角色定妆, 场景参考, 道具参考, comic-image.
---

# comic-image — 漫画出图包与面板图

把漫画脚本和排版转换成逐格 prompt/job 包和面板图登记。共享定妆、reference registry、一致性重抽计划由 `comic-identity` 维护；本 skill 消费其结果，并把真实参考图传给出图后端。

## 输入

- `_设置.md`：生图模型、生图渠道、参考一致性策略、基础视觉风格。
- `设定库/story_bible.md`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/layout.json`。
- `出图/共享/identity_registry.json` 与 `出图/共享/图片/`：由 `comic-identity` 维护的角色、场景、道具参考。

## 输出

- `出图/共享/prompt/00_索引.md`：本话需要的共享参考索引。
- `出图/第N话/prompt/panel_jobs.json`：逐格出图任务包，schema 见 `references/prompt_job_schema.md`。
- `出图/第N话/panels/P001.png` 等面板图。
- `生产数据/codex_reference_bundles/第N话/Pxxx.json`：Codex 真实图片参考入参证据。
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

正式逐格出图前，先用 `comic-identity` 补齐共享锚点并回填路径：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 report --write
```

若报告显示 `missing_refs`，先补定妆或用已采纳面板种临时锚点，再出图。

若已选择 `生图渠道=Codex CLI`，可逐格生成真实 PNG：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话
```

建议先 `--targets P001 --limit 1` 做 smoke test；通过后再批跑。生成完成会更新 `panel_jobs.json` 的 `result_path/status`，全部面板就绪时把本话 `出图` 标为 `✅`。

带 `references` 的格子默认要求 reference path 存在。Codex runner 会把这些图片作为 `codex exec --image` 附件传入，并落 `codex_reference_bundles`；只有明确需要纯文生图试验时才加 `--allow-missing-refs`。

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

1. 读 `panel_script.json` 和 `layout.json`，给每格生成 prompt/job。prompt 必须包含画面事实、构图、角色状态、参考 ID、禁止漂移项和留白/气泡预留。
2. 跑 `comic-identity report --write`，确认主角、常驻角色、关键场景、关键道具、标志服装都有可传给模型的真实参考图。
3. 若共享参考不足，先停在 `comic-identity` 补定妆/锚点，不直接批量生成面板图。
4. 明确要求“无字画面”或“空白气泡”，不要让模型直接生成中文正文。
5. Codex 路线必须把 reference path 转成真实 `--image` 入参，而不是只把路径写进 prompt。
6. 如果用户已在外部生成图片，把文件放入 `出图/第N话/panels/`，并更新 job 包里的 `result_path`、`status`、`source`。
7. job 包齐全后可把 `出图包` 标 `✅`；所有必需 panel 图就绪后把 `出图` 标 `✅`。
8. 预算允许多抽时，保留失败和重抽证据；不要把候选图混进正式 `panels/`，正式目录只留当前采纳版本。

## Prompt 要点

- 一格一个主动作或主信息。
- 角色身份锚、服装、发型、标志物要写具体。
- 场景与道具引用写成结构化 ID 或清晰路径。
- 需要气泡的区域写“预留空白区域”，但不写台词正文。
- 复杂动作拆分为多格或标注分层/合成建议。
- 输出尺寸跟随 `layout.json` 的面板比例。

## 不做什么

- 不嵌最终台词；那是 `comic-compose`。空白气泡是正确中间态，不是缺字。
- 不静默选择付费后端；出图前必须确认模型、渠道、成本和覆盖范围。
- 不跳过 `comic-identity` 的共享参考检查直接生产核心角色高风险面板。
