---
name: comic-image
description: 画漫画出图阶段。Use when preparing shared visual references, per-panel image prompts, generation job packets, registering panel images, or checking textless comic art for projects under 创作区/画漫画. Produces 出图/共享 references, 出图/第N话/prompt job packs, and 出图/第N话/panels images. Triggers 漫画出图, 分格出图, panel image, 漫画prompt, 角色定妆, 场景参考, 道具参考, comic-image.
---

# comic-image — 漫画出图包与面板图

把漫画脚本和排版转换成逐格 prompt/job 包和面板图登记。共享定妆、reference registry、一致性重抽计划由 `comic-identity` 维护；本 skill 消费其结果，并把真实参考图传给出图后端。出图阶段只画无字画面和低细节留白，不再让图像模型画空白气泡或文字框，气泡与文字由 `comic-compose` 可控绘制。

## 输入

- `_设置.md`：生图模型、生图渠道、参考一致性策略、定妆级别、文字语言、基础视觉风格。
- `设定库/story_bible.md`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/layout.json`。
- `出图/共享/identity_registry.json` 与 `出图/共享/图片/`：由 `comic-identity` 维护的角色、场景、道具参考。

## 输出

- `出图/共享/prompt/00_索引.md`：本话需要的共享参考索引。
- `出图/第N话/prompt/panel_jobs.json`：逐格出图任务包，schema 见 `references/prompt_job_schema.md`。
- `出图/第N话/panels/P001.png` 等面板图。
- `生产数据/codex_reference_bundles/第N话/Pxxx.json`：Codex 真实图片参考入参证据。
- `生产数据/panel_qc/第N话/Pxxx.json`：每格落盘后即时 deterministic QC，记录 PNG/尺寸/参考输入/疑似烘焙气泡问题；人工视觉判断仍需现场复核。
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
每格生成落盘后 runner 会立刻写 `生产数据/panel_qc/第N话/Pxxx.json`，并把 `post_qc` 写回对应 job。`verdict=warn/block` 时不要继续无脑批跑；先看具体 panel，必要时补共享参考、压缩 prompt 或 `--force --targets Pxxx` 重抽。这个 post-QC 是 comic 线自维护实现，只服务漫画 panel；不要抽成公共实现，也不要被其它系列 import。

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
2. 跑 `comic-identity report --write`，确认主角、常驻角色、关键场景、关键道具、标志服装都有可传给模型的真实参考图；若项目登记了 `character_dna`、`variant_policy`、`STYLE_` 风格锚，逐格 prompt 必须消费这些契约。
3. 若共享参考不足，先停在 `comic-identity` 补定妆/锚点，不直接批量生成面板图。
4. 明确要求“无字画面 + 低细节留白”，不要让模型直接生成中文正文、英文正文、对白气泡、空白气泡、旁白框或文字框；`文字语言` 只影响后期嵌字和导出元数据。
5. 人物动作格必须写清手脚归属、武器/道具接触点和身体受力；凡脚尖、脚步、踩踏、跪地、鞋靴落点等叙事，不得把脚画成手。
6. Codex 路线必须把 reference path 转成真实 `--image` 入参，而不是只把路径写进 prompt。
7. 每生成一格立刻做落盘 QC：PNG 有效性、尺寸、真实参考输入数、疑似烘焙空白气泡/文字容器；再做人工视觉复核，重点看脸、服装、手脚、武器接触点、文字水印和剧情动作是否跑偏。
8. 若单格 QC 发现角色/道具漂移，先回 `comic-identity` 种锚点或补引用，再对该格 `--force --targets Pxxx` 重抽；不要把坏图继续传给排版合成。
9. 如果用户已在外部生成图片，把文件放入 `出图/第N话/panels/`，并更新 job 包里的 `result_path`、`status`、`source`。
10. job 包齐全后可把 `出图包` 标 `✅`；所有必需 panel 图就绪且无待重抽目标后把 `出图` 标 `✅`。
11. 预算允许多抽时，保留失败和重抽证据；不要把候选图混进正式 `panels/`，正式目录只留当前采纳版本。

## Prompt 要点

- 一格一个主动作或主信息。
- `基础视觉风格` 先按 `skills/comic/references/视觉风格候选.md` 解析成线条、上色、明暗、纹理和阅读形态；用户写 `自定义(...)` 时原样保留可执行技法词。
- 角色身份锚、服装、发型、标志物要写具体。
- 同一角色的不同年龄、闭关前后、受伤、觉醒、换装或境界形态必须继承 `identity_registry.json` 的定型 DNA；不要用“年轻版/老年版”泛化出新脸。
- 用户截图参考里的播放按钮、字幕、搜索框、平台 UI、竖排标题、水印不是视觉设定，必须进入 negative prompt 或禁继承说明。
- 风格要跟项目风格锚一致；不要退化成低细节彩漫、Q 版、泛化韩漫脸，或和定型图不相干的模型默认风格。
- 场景与道具引用写成结构化 ID 或清晰路径。
- 需要文字的区域只写“预留低细节留白区域”，不要画空白气泡；气泡形状、文字、中英双语由 `comic-compose` 绘制。
- 动作格写清手、脚、武器、道具和地面的接触点；脚部叙事必须能看出鞋靴/脚尖/小腿和地面受力，不能用手掌替代脚掌。
- 复杂动作拆分为多格或标注分层/合成建议。
- 输出尺寸跟随 `layout.json` 的面板比例。
- 不写具体在世画师、具体 IP、角色名或“某作品同款”作为风格提示；改写成可执行视觉特征。

## 不做什么

- 不嵌最终台词，也不画最终气泡；那是 `comic-compose`。旧项目已有空白气泡时，合成或重出图阶段要清理，不能留下无字气泡。
- 不静默选择付费后端；出图前必须确认模型、渠道、成本和覆盖范围。
- 不跳过 `comic-identity` 的共享参考检查直接生产核心角色高风险面板。
