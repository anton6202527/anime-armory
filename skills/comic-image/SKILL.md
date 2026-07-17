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
- `出图/封面/prompt/cover_job.json`：作品级竖版封面（约 9:16 / 5:7）prompt/job 包，复用项目风格锚 + 角色定妆同源参考。
- `_meta.json` 的 `cover`：作品卡片封面，作品根相对路径；渲染出竖版 PNG 后才确定性回填，否则恒为 `null`。

## 作品封面（作品卡片）

作品列表卡片要展示封面缩略图 + 简介。简介 `synopsis` 由立项从 `设定库/story_bible.md` 的「一句话核心」写入 `_meta.json`；封面 `cover` 由本步骤产出。

```bash
# 1) 产出竖版封面 prompt/job 包（纯净机降级：只产包 + 合规留痕，cover 保持 null，不硬阻断主流程）
python3 skills/comic-image/scripts/build_cover_job.py "创作区/画漫画/作品名"
# 2) 用本项目生图后端渲染出一张竖版 PNG（放进作品根内，如 出图/封面/cover.png）后确定性回填 cover
python3 skills/comic-image/scripts/build_cover_job.py "创作区/画漫画/作品名" --backfill 出图/封面/cover.png
```

封面「由什么生成」以 `_设置.md` 的 `生图模型`（具体模型名，如 `GPT Image 2`）为准，渠道/CLI（`生图渠道`）作为访问入口分列。job 包只声明生成契约、不调用后端；`--backfill` 校验 PNG 合法且为竖版（`height>width`）后回填 `cover` 并回写 `_进度.md` 的作品封面项。

## 怎么跑

先自动探测并写入本项目生图选择点；检测到 Codex 且 `image_generation` 可用时优先 Codex：

```bash
python3 skills/comic-image/scripts/detect_image_backend.py "创作区/画漫画/作品名" --write-settings
```

已有 `panel_script.json` 和 `layout.json` 后，可生成逐格出图任务包：

```bash
python3 skills/comic-image/scripts/build_panel_jobs.py "创作区/画漫画/作品名" --chapter 第1话
```

含具名角色的格必须先写逐角色结构化绑定，不能把 `characters: ["主角"]`、`characters: ["CHAR_MAIN"]` 或 panel-wide `outfit_id` 当完整身份合同：

```json
"character_bindings": [{
  "character_id": "CHAR_MAIN",
  "form_id": "FORM_BASE",
  "outfit_id": "OUTFIT_BASE",
  "expression_id": "EXPR_NEUTRAL",
  "state_id": "STATE_BASE"
}]
```

上述 ID 必须存在于 identity registry v2；未知 form/outfit/expression/state、由 `story_function/strong_emotion/expression_intensity` 明确声明的强情绪格仍绑定中性或无表情参考、裸名字角色都会阻断 job 构建。只靠画面文字关键词猜出的情绪信号仍是 heuristic WARN。

脚本只写 `panel_jobs.json` 和 `出图/共享/prompt/00_索引.md`，不调用任何生图后端；它会把本话 `出图包` 标为 `✅`，但不会把 `出图` 标完成。

重建出图包时，已 ready 的格只有在提交契约未变（`submit_prompt_sha256` 与画布尺寸一致）时才保留生成状态；改了 `panel_script`/`finishing_plan`/风格设置后重建，受影响格自动回 `planned` 并在输出里列为 `stale_reset_to_planned`，必须重抽，不允许旧图按新契约蒙混过 gate。参考图集合的扩充（补视图）不算契约变化——参考图内容变化由 `comic-identity report` 的 sha 比对触发重抽。加 `--check` 可只读对比当前契约与已落盘出图包（输出 JSON，不写任何文件），`comic-review gate --stage image_preflight` 会自动跑这一检查并对陈旧格阻断。

正式逐格出图前，先用 `comic-identity` 补齐共享锚点并回填路径：

```bash
python3 skills/comic-identity/scripts/identity.py "创作区/画漫画/作品名" --chapter 第1话 report --write
```

若报告显示 `missing_refs`，先补定妆或用已采纳面板种临时锚点，再出图。

若已选择 `生图渠道=Codex CLI`，可逐格生成真实 PNG。runner 启动时**内置 `image_preflight` gate**（离钱最近的入口自带闸门）：gate block 即退出。`--skip-gate` 只可复用 `生产数据/gate_receipts/image_preflight_第N话.json` 中同时绑定当前完整 preflight 输入指纹、当前 `panel_jobs` SHA、真实 gate report SHA 且 `execution_authorized=true` 的无 block receipt（`warn` 可带建议放行）；否则必须同时传 `--waiver-reason`，runner 会写 `生产数据/gate_waivers/` 持久审计 receipt，不能只打印跳过：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 \
  --skip-gate --waiver-reason "人工复核确认本次为已知误报"
```

Codex 内置 `image_generation` 当前单次最多接收 5 张图片附件。即使渠道候选表声明更高参考能力，runner 仍以真实工具上限为硬边界，按“角色身份 → 场景/妖物 → 关键道具 → 风格 → 特效”选择 5 张；被省略附件必须写入 reference bundle 的 `omitted_attachments`，其完整约束继续保留在文字生产合同中，禁止静默丢约束或让工具超限后反复空耗。

若只是参考预算或 QC 规则升级导致一张已生成且人工检查良好的图被旧规则标成 `qc_block`，用 `--recheck-existing --targets Pxxx` 对原 PNG 重跑 post-QC；该模式不得调用模型、归档或重抽。检测器升级不能成为删除好图和重复付费的理由。

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话
```

若项目选择 `生图渠道=Dreamina/即梦官方 CLI`，使用同样受 `image_preflight` 约束的 Dreamina runner。它按逐格目标画布选择官方支持的最近画幅，最多附入 10 张真实参考图，保留服务端原始候选，再以中央安全区规则裁到 layout 的精确尺寸；每格立即写回 submit_id、参考 bundle、prompt 快照、原始候选、画布归一记录与 post-QC：

```bash
python3 skills/comic-image/scripts/dreamina_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 \
  --max-attempts 2 --timeout-sec 600 --continue-on-qc-block
```

`comic-batch` 会读取本项目 `_设置.md` 的生图模型/渠道，在 Codex 与 Dreamina runner 之间自动分派；已明确选定的渠道不可被批跑器静默改写。

目检发现伪字、串脸、服装漂移或关键接触点错误时，可在该格剩余尝试额度内用 `--force --targets Pxxx --max-attempts 1 --correction "..."` 做一次执行层纠偏；纠偏文本写进 prompt 快照与生成事件，不得借此改剧情、加角色或绕过原始哈希合同。

建议先 `--targets P001 --limit 1` 做 smoke test；通过后再批跑。生成完成会更新 `panel_jobs.json` 的 `result_path/status`，全部面板就绪时把本话 `出图` 标为 `✅`。
每格生成落盘后 runner 会立刻写 `生产数据/panel_qc/第N话/Pxxx.json`，并把 `post_qc` 写回对应 job。`verdict=block` 时该 job 标为 `qc_block` 而不是 `ready`，默认立即停止批跑，不能进入合成；修复后用 `--force --targets Pxxx` 重抽。`verdict=warn` 可继续登记，但 `comic-review gate --stage image` 会要求人审签收或重抽。这个 post-QC 是 comic 线自维护实现，只服务漫画 panel；不要抽成公共实现，也不要被其它系列 import。

带 `references` 的格子默认要求 reference path 存在。Codex runner 会把这些图片作为 `codex exec --image` 附件传入，并落 `codex_reference_bundles`；只有明确需要纯文生图试验时才加 `--allow-missing-refs`。

换装格在该角色自己的 `character_bindings[].outfit_id` 与相符 `state_id` 中声明：build_panel_jobs 从 registry 的 `assets[角色].outfits[该ID]` 取服装描述、禁漂移项和真实服装参考图；未登记或 state 与 outfit 冲突时直接拒绝建立正式 job。

预算充足或后端偶发失败时，可加多次尝试：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --max-attempts 3
```

如果 Codex 子进程没有返回 `image_generation_end`，而是输出 imagegen/prompting 使用说明后超时，说明该子进程被用户配置或技能加载带偏；保留真实 `--image` 附件，改用干净子进程重试：

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003 --timeout-sec 600 --ignore-user-config
```

若仍复现同类说明文档输出，再追加 `--ignore-rules`。Codex 路线必须有熔断，禁止死磕：

- 明确返回配额耗尽、余额不足、rate limit/credit exhausted 时，立刻停止 Codex 重试。
- `--ignore-user-config --ignore-rules` 后仍连续出现 transport/TLS/app-server 失败，最多再做一次与正式请求同附件范围的健康验证；仍失败即把 Codex 队列标为通道不可用，不得拿其它正式 panel 逐个试错。
- 项目已有用户对备用后端与预算的明确授权时，同一轮直接经本线适配层切备用后端；没有授权才停下说明成本与缺口。切换时必须把“具体生图模型+版本”和“访问渠道”分列记录，不能只写“即梦/某厂商”。
- 切到即梦官方时，先用 `comic-settings` 写入适配层核验后的具体模型版本与 `即梦官方 CLI` 渠道，再重建 `panel_jobs.json` 和 reference plan、重跑 `image_preflight`；不得把 Codex 编译 prompt、gate receipt 或失败状态直接冒充即梦任务。沿用同一 panel 的画面合同、身份锚、场景锚、附件 SHA、无字要求和 QC 标准，失败请求保留在 history/事件账。
- 备用后端也失败时再熔断并报告；不得在 Codex 与备用后端之间无限来回切换。

若人工看图后需要重抽某几格，用 `--force --targets P003,P007`；旧图会归档到 `出图/第N话/candidates/<panel_id>/`，新图覆盖正式 `panels/Pxxx.png` 并写入 job history。

```bash
python3 skills/comic-image/scripts/codex_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003,P007 --force --max-attempts 3
```

当适配层已把项目切到 `Seedream 5.0 + Dreamina/即梦官方 CLI` 并重建任务包后，使用即梦 runner；它直接消费即梦 profile 编译的 `submit_prompt`，将任务包选中的 1–10 张真实参考图作为官方 `image2image` 入参，按 panel 画布选择最近的即梦比例，记录 submit_id/credit/reference manifest/post-QC。不要拿它执行仍标为 Codex 的旧任务包：

```bash
# 单格 smoke test；若已有旧后端正式图，--force 会先归档到 candidates/
python3 skills/comic-image/scripts/dreamina_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 \
  --targets P001 --limit 1 --force --model-version 5.0 --resolution-type 2k

# smoke test 人审通过后继续全部未完成格
python3 skills/comic-image/scripts/dreamina_panel_runner.py "创作区/画漫画/作品名" --chapter 第1话 \
  --model-version 5.0 --resolution-type 2k
```

即梦 runner 与 Codex runner 使用同一个 `image_preflight`、编译合同校验、旧图归档、逐格 QC 和进度条件，但各自写独立 reference bundle；切后端后必须整话保持单一生成配方，旧后端成功图只能保留为候选/视觉复核材料，不能混在最终 ready 集合里。

需要从“当前进度”自动推进一话、按预算多抽并衔接合成/审查时，使用 `comic-batch`；`comic-image` 仍只负责出图阶段本身。

## 工作流

1. 读 `panel_script.json`、`layout.json` 和可选 `finishing_plan.json`，给每格生成 schema v2 job。每个 job 明确分层：
   - `production_contract_prompt` / `production_negative_contract` 是完整生产合同，保留参考 ID、角色 DNA、场景锚、continuity、禁继承、传统稿层和审计信息，供 gate、人工复核与溯源；
   - `skills/comic/_lib/comic_image_prompt_compiler.py` 把合同编译成 `submit_prompt`：只留可见画面事实、构图/表演、画风稿层、可画的场景连续性、最短身份保持、墨线/黑场/网点/效果、无字策略和人体接触点；内部 ID、路径、registry 元数据、正文台词不得进入；非写实安全呈现改写也必须在此编译期完成，再计算 prompt SHA；
   - `prompt` 只是 `submit_prompt` 的兼容别名，runner 只提交编译层，不读取完整生产合同。
   - 正式出图前，`panel_script.json` 顶层 `visual_contract` 和逐格视觉契约必须存在。含角色格必须消费 `gaze_target / eyeline_direction / character_integrity`；含场景格必须消费 `scene_anchor_id / spatial_layout / lighting_anchor / axis_eyeline`。`scene_anchor_id` 必须登记到 `visual_contract.scene_anchors`，眼神目标必须是具体戏内对象，多人同格必须有站位/遮挡/接触点。这些字段完整写入 `continuity_contract`；compiler 只抽取模型能画出来的布局、光位、轴线、站位和眼神目标。
   - 漫画格也要锁脸、眼神和身体完整性：脸型、眼型/眼距、发际线、发型、服装主色、配饰/伤痕/标志物、手脚和关键道具不能跨格漂移；动作格不得为了构图裁掉叙事需要的头发、脸、手脚、武器或接触点。
   - 除非本格明确 `camera_role=POV/破第四墙`，不要让角色看读者镜头；眼神应锁定对话对象、对手、武器/道具、命中点、画外声源或下一动作目标。
   - 启用传统原稿流程时，应先跑 `comic-finishing`，让 job 带 `traditional_finish_contract`，把墨线、黑场、网点/灰阶、效果线、漫符和手绘拟声词计划注入 prompt。缺该契约时 gate 给 warn，正式长线项目应补齐后再批量出图。
2. 生成 job 包时通过 comic 自己的 `image_backend_adapter` 把 `生图模型 + 生图渠道` 归一成参考图预算、是否支持真实图片输入、是否具备持久主体能力等结构字段；不要把 Codex/渠道壳当生成模型，也不要把未知后端写死成唯一口径。
   - 即梦官方 CLI 的 `image2image` 当前实机支持 1–10 张本地图片（2026-07-16 以 `dreamina image2image --help` 核验）；适配层按 10 张总预算规划，仍需为 `style_only`、具名主体、LOC 与关键 PROP 公平保留槽位。CLI/版本变化后先重跑 `--help` 再改能力表，不能凭旧印象降成 2 张。
3. 跑 `comic-identity report --write`，确认主角、常驻角色、关键场景、关键道具、标志服装都有可传给模型的真实参考图；`character_dna`、`variant_policy`、`STYLE_` 风格锚进入完整合同，模型通过真实图片输入 + 精简身份保持语句消费，不把 registry 全文粘进 prompt。
4. `build_panel_jobs.py` 会生成并立即消费 `生产数据/comic_reference_plan_第N话.json`。计划绑定 panel script、registry、memory anchor、设置与实际参考图片 SHA，逐格写 `panel_plan_sha256`；job 再写 `execution_input_sha256` 和 `consumed_contracts`。计划过期、具名角色没有至少一个真实身份锚、LOC/常驻 PROP 缺真实图、关键附件超过执行后端上限时拒绝构建并给拆反打/分区合成建议，不静默丢约束。
5. 正式批量出图前跑 `comic-review/scripts/gate.py --stage image_preflight`，阻断缺共享参考、多视图缺口、缺风格锚、缺逐格视觉契约、混用生成配方、legacy schema、缺 compiler、后端/profile 不一致或 prompt/hash 漂移；`comic-batch` 会自动跑。
6. 若共享参考不足，先停在 `comic-identity` 补定妆/锚点，不直接批量生成面板图。
7. 明确要求“无字画面 + 低细节留白”，不要让模型直接生成中文正文、英文正文、对白气泡、空白气泡、旁白框或文字框；`文字语言` 只影响后期嵌字和导出元数据。
8. 人物动作格必须写清手脚归属、武器/道具接触点和身体受力；凡脚尖、脚步、踩踏、跪地、鞋靴落点等叙事，不得把脚画成手。
9. Codex 路线必须把 reference path 转成真实 `--image` 入参；路径和内部 ID 不写进模型 prompt。runner 会校验 compiler/profile 后只提交 `submit_prompt` 的小型执行包装，不能在执行期再次静默改写已哈希的提交词。
10. 每生成一格立刻做落盘 QC：PNG 有效性、尺寸、真实参考输入数、疑似烘焙空白气泡/文字容器；`block` 先修当前格，不把坏图继续传给排版合成。
11. 若单格 QC 发现角色/道具漂移，先回 `comic-identity` 种锚点或补引用，再对该格 `--force --targets Pxxx` 重抽。
12. 如果用户已在外部生成图片，把文件放入 `出图/第N话/panels/`，并更新 job 包里的 `result_path`、`status`、`source`。
13. job 包齐全后可把 `出图包` 标 `✅`；所有必需 panel 图就绪且无 `qc_block` 或待重抽目标后把 `出图` 标 `✅`。
14. 预算允许多抽时，保留失败和重抽证据；不要把候选图混进正式 `panels/`，正式目录只留当前采纳版本。

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

## 跨话记忆锚消费（2026-07 落地）

`build_panel_jobs.py` 出图前读取 `生产数据/comic_memory_anchor_第N话.json`（comic-identity/memory_anchor.py 产·文件契约，不跨 skill import）：计划里 `status=ready` 的角色，其 pinned 最早定妆锚（front/face）置于该角色参考组**最前**（同路径去重）——长间隔再登场角色以首登场形象为最高权重参考。计划绑定所有脚本、registry 与 pinned 图片 SHA；长间隔角色需要锚时，计划缺失或 stale 会阻断 job 构建。

## 逐格参考事前处方（reference_planner·2026-07 落地）

治跨话脸漂根因：不同格的**服装/表情/景别/角度**变化时，单张定妆照对 AI 只是"固定板式"、身份判别细节不足，模型在新条件下会重画整张脸，逐话累积成漂移。`character_consistency`/identity report 是**事后**量漂移，`memory_anchor` 是事前钉锚，缺的是**事前处方**：

```bash
python3 skills/comic-image/scripts/reference_planner.py "创作区/画漫画/作品名" 第1话 --write
```

逐格逐角色算变化量 delta（近景/大表情/极端角度/背身过肩/换装/动作/多人同框），按后端能力表路由 front/¾/face/side/back/表情/服装与 memory anchor。分配器先公平保留每个具名角色一锚，再保留 LOC/常驻 PROP；超过执行上限就明确建议拆反打/分区生成后合成。缺结构化绑定、未知状态、显式强情绪合同缺对应表情、关键真实附件缺失和计划 stale 是可复算的 BLOCK；关键词猜情绪、主色撞色、升档和像素代理仍只 WARN/INFO。`build_panel_jobs.py` 只消费该计划选中的真实图与 SHA，并写消费收据，不另起一套挑图逻辑。
