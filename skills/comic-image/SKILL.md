---
name: comic-image
description: 画漫画出图阶段。Builds strict per-panel production contracts and backend-aware concise image prompts, binds real shared references, carries ink/tone/effects plans, generates/registers textless panel images, and runs immediate QC. Produces 出图/共享 references, schema-v2 panel job packs, and panels. Triggers 漫画出图, 分格出图, panel image, 漫画prompt, prompt compiler, 角色定妆, 场景参考, 道具参考, 墨线, 网点, 效果线, comic-image.
---

# comic-image — 漫画出图包与面板图

把漫画脚本和排版转换成逐格“完整生产合同 + 后端编译提交 prompt”任务包和面板图登记。共享定妆、reference registry、一致性重抽计划由 `comic-identity` 维护；本 skill 消费其结果，并把真实参考图传给出图后端。出图阶段只画无字画面和低细节留白，不再让图像模型画空白气泡或文字框，气泡与文字由 `comic-compose` 可控绘制。

## 输入

- `_设置.md`：生图模型、生图渠道、参考一致性策略、定妆级别、文字语言、基础视觉风格。
- `设定库/story_bible.md`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/layout.json`。
- 可选 `出图/第N话/finishing/finishing_plan.json`：墨线、黑场、网点/灰阶、效果线、漫符和手绘拟声词计划。
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

重建出图包时，已 ready 的格只有在提交契约未变（`submit_prompt_sha256` 与画布尺寸一致）时才保留生成状态；改了 `panel_script`/`finishing_plan`/风格设置后重建，受影响格自动回 `planned` 并在输出里列为 `stale_reset_to_planned`，必须重抽，不允许旧图按新契约蒙混过 gate。参考图集合的扩充（补视图）不算契约变化——参考图内容变化由 `comic-identity report` 的 sha 比对触发重抽。加 `--check` 可只读对比当前契约与已落盘出图包（输出 JSON，不写任何文件），`comic-review gate --stage image_preflight` 会自动跑这一检查并对陈旧格阻断。

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
每格生成落盘后 runner 会立刻写 `生产数据/panel_qc/第N话/Pxxx.json`，并把 `post_qc` 写回对应 job。`verdict=block` 时该 job 标为 `qc_block` 而不是 `ready`，默认立即停止批跑，不能进入合成；修复后用 `--force --targets Pxxx` 重抽。`verdict=warn` 可继续登记，但 `comic-review gate --stage image` 会要求人审签收或重抽。这个 post-QC 是 comic 线自维护实现，只服务漫画 panel；不要抽成公共实现，也不要被其它系列 import。

带 `references` 的格子默认要求 reference path 存在。Codex runner 会把这些图片作为 `codex exec --image` 附件传入，并落 `codex_reference_bundles`；只有明确需要纯文生图试验时才加 `--allow-missing-refs`。

预算充足或后端偶发失败时，可加多次尝试：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --max-attempts 3
```

如果 Codex 子进程没有返回 `image_generation_end`，而是输出 imagegen/prompting 使用说明后超时，说明该子进程被用户配置或技能加载带偏；保留真实 `--image` 附件，改用干净子进程重试：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003 --timeout-sec 600 --ignore-user-config
```

若仍复现同类说明文档输出，再追加 `--ignore-rules`；若两者仍不能稳定返回 PNG，应停下报告当前 Codex CLI 子进程不可稳定落图，不要继续批量重试消耗额度。

若人工看图后需要重抽某几格，用 `--force --targets P003,P007`；旧图会归档到 `出图/第N话/candidates/<panel_id>/`，新图覆盖正式 `panels/Pxxx.png` 并写入 job history。

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003,P007 --force --max-attempts 3
```

需要从“当前进度”自动推进一话、按预算多抽并衔接合成/审查时，使用 `comic-batch`；`comic-image` 仍只负责出图阶段本身。

## 工作流

1. 读 `panel_script.json`、`layout.json` 和可选 `finishing_plan.json`，给每格生成 schema v2 job。每个 job 明确分层：
   - `production_contract_prompt` / `production_negative_contract` 是完整生产合同，保留参考 ID、角色 DNA、场景锚、continuity、禁继承、传统稿层和审计信息，供 gate、人工复核与溯源；
   - `skills/comic/_lib/comic_image_prompt_compiler.py` 把合同编译成 `submit_prompt`：只留可见画面事实、构图/表演、画风稿层、可画的场景连续性、最短身份保持、墨线/黑场/网点/效果、无字策略和人体接触点；内部 ID、路径、registry 元数据、正文台词不得进入；
   - `prompt` 只是 `submit_prompt` 的兼容别名，runner 只提交编译层，不读取完整生产合同。
   - 正式出图前，`panel_script.json` 顶层 `visual_contract` 和逐格视觉契约必须存在。含角色格必须消费 `gaze_target / eyeline_direction / character_integrity`；含场景格必须消费 `scene_anchor_id / spatial_layout / lighting_anchor / axis_eyeline`。`scene_anchor_id` 必须登记到 `visual_contract.scene_anchors`，眼神目标必须是具体戏内对象，多人同格必须有站位/遮挡/接触点。这些字段完整写入 `continuity_contract`；compiler 只抽取模型能画出来的布局、光位、轴线、站位和眼神目标。
   - 漫画格也要锁脸、眼神和身体完整性：脸型、眼型/眼距、发际线、发型、服装主色、配饰/伤痕/标志物、手脚和关键道具不能跨格漂移；动作格不得为了构图裁掉叙事需要的头发、脸、手脚、武器或接触点。
   - 除非本格明确 `camera_role=POV/破第四墙`，不要让角色看读者镜头；眼神应锁定对话对象、对手、武器/道具、命中点、画外声源或下一动作目标。
   - 启用传统原稿流程时，应先跑 `comic-finishing`，让 job 带 `traditional_finish_contract`，把墨线、黑场、网点/灰阶、效果线、漫符和手绘拟声词计划注入 prompt。缺该契约时 gate 给 warn，正式长线项目应补齐后再批量出图。
2. 生成 job 包时通过 comic 自己的 `image_backend_adapter` 把 `生图模型 + 生图渠道` 归一成参考图预算、是否支持真实图片输入、是否具备持久主体能力等结构字段；不要把 Codex/渠道壳当生成模型，也不要把未知后端写死成唯一口径。
3. 跑 `comic-identity report --write`，确认主角、常驻角色、关键场景、关键道具、标志服装都有可传给模型的真实参考图；`character_dna`、`variant_policy`、`STYLE_` 风格锚进入完整合同，模型通过真实图片输入 + 精简身份保持语句消费，不把 registry 全文粘进 prompt。
4. 正式批量出图前跑 `comic-review/scripts/gate.py --stage image_preflight`，阻断缺共享参考、多视图缺口、缺风格锚、缺逐格视觉契约、混用生成配方、legacy schema、缺 compiler、后端/profile 不一致或 prompt/hash 漂移；`comic-batch` 会自动跑。
5. 若共享参考不足，先停在 `comic-identity` 补定妆/锚点，不直接批量生成面板图。
6. 明确要求“无字画面 + 低细节留白”，不要让模型直接生成中文正文、英文正文、对白气泡、空白气泡、旁白框或文字框；`文字语言` 只影响后期嵌字和导出元数据。
7. 人物动作格必须写清手脚归属、武器/道具接触点和身体受力；凡脚尖、脚步、踩踏、跪地、鞋靴落点等叙事，不得把脚画成手。
8. Codex 路线必须把 reference path 转成真实 `--image` 入参；路径和内部 ID 不写进模型 prompt。runner 会校验 compiler/profile 后只提交 `submit_prompt` 的小型执行包装。
9. 每生成一格立刻做落盘 QC：PNG 有效性、尺寸、真实参考输入数、疑似烘焙空白气泡/文字容器；`block` 先修当前格，不把坏图继续传给排版合成。
10. 若单格 QC 发现角色/道具漂移，先回 `comic-identity` 种锚点或补引用，再对该格 `--force --targets Pxxx` 重抽。
11. 如果用户已在外部生成图片，把文件放入 `出图/第N话/panels/`，并更新 job 包里的 `result_path`、`status`、`source`。
12. job 包齐全后可把 `出图包` 标 `✅`；所有必需 panel 图就绪且无 `qc_block` 或待重抽目标后把 `出图` 标 `✅`。
13. 预算允许多抽时，保留失败和重抽证据；不要把候选图混进正式 `panels/`，正式目录只留当前采纳版本。

## Prompt 要点

- 一格一个主动作或主信息。
- `基础视觉风格` 先按 `skills/comic/references/视觉风格候选.md` 解析成线条、上色、明暗、纹理和阅读形态；用户写 `自定义(...)` 时原样保留可执行技法词。
- 角色身份锚、服装、发型、标志物要写具体。
- 同一角色的不同年龄、闭关前后、受伤、觉醒、换装或境界形态必须继承 `identity_registry.json` 的定型 DNA；不要用“年轻版/老年版”泛化出新脸。
- 用户截图参考里的播放按钮、字幕、搜索框、平台 UI、竖排标题、水印不是视觉设定，必须进入 negative prompt 或禁继承说明。
- 风格要跟项目风格锚一致；不要退化成低细节彩漫、Q 版、泛化韩漫脸，或和定型图不相干的模型默认风格。
- 场景与道具引用在完整合同/job 中写成结构化 ID 或路径；模型 prompt 只写可见结构/材质，并通过真实图片附件消费引用。
- 场景连续性写成可执行约束：同一 `scene_anchor_id/LOC_` 的空间布局、主光方向、冷暖色、常驻物件、人物左右关系和前后景层级必须继承；剧情改光、换轴或换景必须在 panel_script 里写理由。
- 眼神一致性写成正向约束：`gaze_target` 是读者能看懂的戏内目标，不是泛泛“坚定眼神”；动作/冲突格还要写“镜头是旁观者，角色不看镜头，视线锁定 X”。
- 需要文字的区域只写“预留低细节留白区域”，不要画空白气泡；气泡形状、文字、中英双语由 `comic-compose` 绘制。
- 动作格写清手、脚、武器、道具和地面的接触点；脚部叙事必须能看出鞋靴/脚尖/小腿和地面受力，不能用手掌替代脚掌。
- 复杂动作拆分为多格或标注分层/合成建议。
- 输出尺寸跟随 `layout.json` 的面板比例。
- 传统漫画完成稿要写清目标稿层：清线稿、墨线+黑场、网点完成稿或彩色完成稿；不要只写“漫画风”。网点、速度线、集中线、冲击闪、漫符必须服务阅读和动作路径，不遮挡脸、手、脚、关键道具或最终文字槽。
- 不写具体在世画师、具体 IP、角色名或“某作品同款”作为风格提示；改写成可执行视觉特征。

## 不做什么

- 不嵌最终台词，也不画最终气泡；那是 `comic-compose`。旧项目已有空白气泡时，合成或重出图阶段要清理，不能留下无字气泡。
- 不静默选择付费后端；出图前必须确认模型、渠道、成本和覆盖范围。
- 不跳过 `comic-identity` 的共享参考检查直接生产核心角色高风险面板。
