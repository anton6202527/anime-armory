---
name: comic-review
description: 画漫画审查阶段。Use when reviewing comic scripts, name boards, layouts, traditional ink/tone/effects coverage, panel art, lettering, bilingual lettering, empty bubbles, long-scroll exports, readability, panel order, text overlap, hand/foot anatomy, character consistency, source adaptation faithfulness, platform deliverable readiness, or rework lists for projects under 创作区/画漫画. Triggers 漫画审查, 漫画质检, 阅读顺序, 遮挡, 角色一致性, 手脚错乱, 空气泡, 双语嵌字, 台词太多, 长图检查, ネーム检查, 网点检查, 效果线检查, 发布前检查, comic-review.
---

# comic-review — 漫画审查与返修

审查漫画是否读得顺、看得清、角色不漂、文字不挡、导出规格可用。它不生产新内容，只产问题清单、返修建议和发布前判断。`合规用途=demo学习/自用草稿` 时，字体/素材授权 pending 只记录在 notes，不作为问题；切到发布候选、商用或授权交付时才启用发布前授权 gate。

## 输入

- `_进度.md`、`_设置.md`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/layout.json`、`lettering.json`、`export_manifest.json`。
- 可选 `排版/第N话/name_board.json` 和 `出图/第N话/finishing/finishing_plan.json`。
- `出图/第N话/panels/`。
- 可选源本、故事圣经和共享参考。

## 输出

- `生产数据/comic_review_第N话.json`。
- `生产数据/comic_review_第N话.md`。
- `生产数据/comic_style_consistency_第N话.json/md` 与 `consistency_findings_style_第N话.json`：面板风格一致性、场景族群基线、调色离群、拼贴/分栏/外框嫌疑和生成配方一致性 findings。
- `生产数据/comic_character_consistency_第N话.json/md` 与 `consistency_findings_character_第N话.json`：角色参考图对本话面板的并排复核、可选 face/hair/outfit 指纹提示和返修目标。
- `生产数据/comic_gate_<stage>_第N话.json/md` 与 `gate_findings_<stage>_第N话.json`：`image_preflight` / `image` / `compose` / `review` 阶段 gate 结果，供 `comic-batch` 和人工续跑消费。
- `生产数据/qa_previews/第N话_panels_contact_sheet.jpg`、`第N话_style_outliers_detail.jpg`、`第N话_character_consistency_contact_sheet.jpg`：风格和角色复核自动生成的人审证据图，用于签收计划内光效、系统特效、动作速度线、构图差异或启发式角色指纹误报。
- `_进度.md`：人工或机器审查通过后，把 `审查` 标 `✅`；有阻断问题时不回写完成。

## 怎么跑

生成审查报告，不回写进度：

```bash
python3 skills/comic-review/scripts/review.py "创作区/画漫画/作品名" --chapter 第1话
```

如果报告 `verdict=pass`，可显式允许脚本把 `_进度.md` 的 `审查` 标为 `✅`：

```bash
python3 skills/comic-review/scripts/review.py "创作区/画漫画/作品名" --chapter 第1话 --write-progress
```

脚本会刷新 `生产数据/qa_previews/第N话_longstrip_preview.webp`，并检查设置、脚本、排版、嵌字、导出 manifest、一致性报告、权利状态、`lettering_slot_qc` 嵌字槽位接触表和疑似烘焙空白气泡。视觉美术判断仍需人工复核；机检发现的疑似气泡是定位线索，不是像素级最终判决。

只跑风格一致性机检：

```bash
python3 skills/comic-review/scripts/style_consistency.py "创作区/画漫画/作品名" --chapter 第1话
```

该报告使用漫画线自包含的风格一致性口径：同一话必须统一生图模型/渠道、登记风格锚/`style_contract`，并用面板风格指纹检查画风/照片感/细节密度离群；全话基线之外还会按场景族群复核，避免把脚本计划内的日景、夜景、山路、水底或蒙太奇误判成画风漂移。同场景会检查冷暖/品绿调色横跳，并检测疑似内部分栏、拼贴 gutter、外框/截图边。`block` 回 `comic-image` 重抽，`warn` 必须人审签收或重抽。

只跑角色一致性机检：

```bash
python3 skills/comic-review/scripts/character_consistency.py "创作区/画漫画/作品名" --chapter 第1话
```

该报告优先产出并排人审证据：每个 `CHAR_` 的共享参考图放在同一张 contact sheet 里，旁边是本话所有出场 panel。装了 Pillow 时会额外给 face / hair / outfit 三类裁剪指纹相似度提示；这些像素提示是启发式，只能 `warn`，不能替代人眼对脸型、发际线、发型、服装、配饰和标志物的判定。

正式出图或交付前跑 gate：

```bash
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage image_preflight
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage image
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage compose
python3 skills/comic-review/scripts/gate.py "创作区/画漫画/作品名" --chapter 第1话 --stage review
```

`image_preflight` 在付费/批量出图前阻断缺共享参考、长线多视图缺口、缺风格锚、缺 `visual_contract`、逐格缺人物完整性/眼神目标、逐格缺场景布局/光位/轴线、`LOC_` 未登记、无理由看镜头、多人同格缺站位/遮挡/接触点、混用模型/渠道等问题；它还会用 `comic-image` 的 `build_panel_jobs.py --check` 按当前脚本/收尾/风格契约重编提交 prompt 并与落盘出图包比对，改了契约没重建出图包（`panel_jobs_stale_contract`）或脚本新增格缺 job（`panel_jobs_missing_panels`）都阻断。`image` 在出图后阻断缺图、`post_qc=block`、风格/角色一致性 block，以及成图生成时哈希与当前提交契约不一致的格（`panel_generated_under_stale_contract`，防手工把旧图改回 ready）；`compose` 追加导出 manifest 和渲染物检查；`review` 追加完整 `comic-review` 报告。`comic-batch` 出图前后会自动跑对应 gate。风格锚判定不认 `未指定/无/待定` 等占位值。

若人审确认离群来自计划内画面差异（如开场空镜、巨物压迫、系统金光、梦境/蒙太奇），可写 `生产数据/style_consistency_acceptance_第N话.json` 做带证据签收，再重跑 `style_consistency.py`。签收记录必须至少匹配 `code + panel_id` 或 `code + artifact`，并写明 `reason` 与 `evidence`；脚本会把对应 finding 降为 `info`，同时保留原始 `machine_severity`。

若 face/hair/outfit 指纹低分来自低机位、遮挡、泥污、强光、动作变形或剧情换装等计划内角色状态，可写 `生产数据/character_consistency_acceptance_第N话.json` 做带证据签收，再重跑 `character_consistency.py` 或 gate。签收记录至少匹配 `code + panel_id` 或 `code + artifact`，可选再加 `character_id`；脚本会把对应 finding 降为 `info`，同时保留原始 `machine_severity`。签收不能替代缺定妆图、缺角色 DNA、明显换脸或主服装设定错误的返修。

若“疑似烘焙空白气泡”其实是天空、雾光、宣纸留白或系统绘卷等计划内亮部，可写 `生产数据/raw_bubble_acceptance_第N话.json` 做人审签收。`accepted_findings[]` 至少包含 `{"code":"raw_bubble_candidate","panel_id":"Pxxx","reason":"...","evidence":"..."}`；重跑 `comic-review` 后对应项会降为 `info`，但该格重抽后必须重新复核。

若 `panel_qc` 已带 `manual_review.verdict=pass`，gate 会把该格落盘 `post_qc=warn` 作为已签收误报降为 `info`；没有 panel_qc 人审记录时，仍需 `raw_bubble_acceptance_第N话.json` 或重抽该格。

## 审查维度

| 维度 | 检查点 |
|---|---|
| 阅读顺序 | 视线是否自然，页漫/条漫方向是否一致 |
| 叙事闭环 | 本话是否有钩子、冲突、推进、转折或收束 |
| 分格密度 | 单格信息是否过载，台词是否过长 |
| 画面可读性 | 主体、表情、动作、道具是否清楚 |
| 气泡遮挡 | 是否挡脸、手、关键动作、重要道具 |
| 角色一致性 | 脸、发型、服装、标志物是否跨格稳定 |
| 人物完整性 | 头发、脸、手、脚、服装、标志物和关键道具是否完整可读；动作格是否裁掉叙事必要部位 |
| 眼神/视线一致性 | `gaze_target`、`eyeline_direction` 是否存在且具体；角色是否看向戏内对象而不是“坚定眼神/看前方/无理由看镜头” |
| 场景连续性 | `scene_anchor_id` 是否登记到 `visual_contract.scene_anchors`；空间布局、主光方向/冷暖、轴线视线、常驻物件和前后景层级是否跨格继承 |
| 站位/遮挡一致性 | 多人同格是否写清左右、前后景、遮挡、接触点和视线轴线，避免正反打或动作格空间关系漂移 |
| 传统工艺层 | 启用 `传统原稿流程` 时，是否有 name board、原稿安全区、墨线/黑场/网点/效果线计划，以及出图 job 是否消费 finishing plan |
| 角色指纹/并排证据 | `CHAR_` 参考图是否与本话出场 panel 并排可审，face/hair/outfit 启发式是否提示异常 |
| 风格一致性 | 生图模型/渠道是否统一，风格锚是否登记，面板是否出现照片感/色彩/细节密度离群，场景族群内是否自洽，同场景是否冷暖调色横跳，是否出现多面板拼贴 gutter 或外框/截图边 |
| 长线定妆 | `定妆级别=长线专门定妆` 时，常驻人物是否补齐 front / three_quarter / side / back / face |
| 高一致性长线口径 | `角色一致性硬闸=开启` 或 `年龄形态继承=开启`（按设置值显式判断，长值策略 token 兼容）时，是否登记风格锚、角色 DNA、禁漂移项和形态继承策略；硬闸开启同时强制长线多视图缺口阻断 |
| 手脚/动作解剖 | 脚尖、脚步、踩踏、跪地、武器落点是否被画成手或漂浮肢体 |
| 文字质量 | 错字、标点、语气、拟声词是否统一；`文字语言` 与 manifest、`lettering.json` 是否一致 |
| 空气泡 | 没有文字的气泡/旁白框是否已删除或回图像阶段重出 |
| 导出规格 | 长图尺寸、可选分段、缺图、manifest 是否齐全 |
| 合规发布 | 字体、素材、源本、第三方资产状态是否可追溯 |

详细 checklist 见 `references/review_checklist.md`。

## 处理结论

- `pass`：可进入发布或归档。
- `revise`：有问题但可局部修。
- `block`：阅读顺序、缺图、严重遮挡、角色大漂、权利不明等问题阻断发布。

对每个问题写明：

- `severity`：block / warn / info。
- `artifact`：具体文件或 panel_id。
- `reason`：为什么影响阅读或发布。
- `return_to`：回 `comic-script` / `comic-name` / `comic-layout` / `comic-finishing` / `comic-image` / `comic-compose`。
- `suggested_fix`：最小返修动作。

缺 name board 或 finishing plan 默认是 warn/info；角色脸、眼神、场景轴线和共享参考缺口仍按原硬闸处理。

## 不做什么

- 不直接重写脚本或重出图。
- 不用主观“好看/不好看”当硬阻断；阻断要落到可定位的阅读、画面、文字、导出或合规问题。
- 不把草稿字体授权当正式发布授权。
