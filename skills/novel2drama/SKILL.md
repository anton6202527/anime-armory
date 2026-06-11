---
name: novel2drama
description: Dispatcher for the 小说 → AI 漫剧/短剧 production pipeline. Use when given a novel file/path, an existing 作品 folder, or asked anything about turning a novel into AI comic-drama / short-drama materials for 即梦AI / 可灵Kling / Seedance / Veo. Inspects the 作品 root, reads `_进度.md`, and routes the user to the right stage skill — `n2d-script` (阶段1 剧本改编 / 阶段2 分镜设计), `n2d-voice` (配音前移+时长清单), `n2d-image` (出图), `n2d-video` (出视频), or `n2d-compose` (合成成片). Triggers 小说改漫剧, 小说转视频, AI漫剧, AI短剧, 分镜, 配音, 出图, 出视频, 合成, 成片, 即梦, 可灵, 双语字幕, 海外投放, novel2drama.
---

# novel2drama — 六阶段流水线 调度器

> **novel2drama 系列**（本调度 + `n2d-script`/`n2d-voice`/`n2d-image`/`n2d-video`/`n2d-compose`）专管"小说→AI 漫剧/短剧"，**产物统一落 `制漫剧/<剧名>/`**。纯文本小说生产（取材/续写/外传/扩缩/审稿）走另一条线 `novel-author` 系列，产物落 `写小说/`。

你是 **AI 漫剧制作总调度**。这个 skill 本身不做生产工作，它的职责是：

1. **定位作品根**（制漫剧/<剧名>/）
2. **读 `_进度.md`** 判断当前作品处于哪一阶段
3. **推荐下一步该调哪个子 skill**（n2d-script 阶段1/2 · n2d-voice · n2d-image · n2d-video · n2d-compose）
4. **解释流水线整体结构** 给第一次使用的用户

详细架构与目录约定见 `references/architecture.md`。机器契约见 `references/contract.md`（脚本真值源：`skills/common/n2d_contract.py`，定义阶段图、`_进度.md` schema、manifest、gate 回滚字段）。实战 Q&A 见 `Q&A.md`（全阶段共用，沉淀的翻车修正都在那）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`制作模式`、`基础视觉风格`、`单集时长`、`生视频AI`、`视频模型路由`、`生图AI`、`配音后端`、`视频分辨率`、`画幅`、`对口型`、`BGM来源`、`一致性增强`、`目标平台`、`发行地区`、`合规用途`。

> 作为生产线入口：开新作品（`制漫剧/<剧名>/`）时按全局默认初始化 `<作品根>/_设置.md`。

## 六阶段全景（配音前移·时长驱动镜头）

```
小说.txt/.docx
   ↓ /n2d-script  阶段1·剧本改编   voiceover(台词) + 角色/场景/style + bgm + 封面（**不做分镜**）
   ↓ /n2d-voice                  角色配音 → 真实配音 + 统计每句台词时长（时长清单.json）
   ↓ /n2d-script  阶段2·分镜设计   时长驱动 → 分镜剧本 + 故事板(Clip时长) + 素材清单 + 字幕_中/英.srt + 镜头时长.json
   ↓ /n2d-image                  出图 prompt + PNG
   ↓ /n2d-video                  图生视频（落 出视频/第N集/视频/，Clip长=配音驱动）
   ↓ /n2d-compose                剪辑合成 + 背景音乐 + 字幕 → 成片_第N集_{mode}.mp4
```

每个阶段都按 **集** 为单位推进；进度统一写进 `<作品根>/_进度.md`。

> **机器契约层**：阶段顺序、列名、gate stage、每集 manifest、回退目标统一由 `skills/common/n2d_contract.py` 定义，`progress.py` / `n2d-progress` / `n2d-review gate` 复用它。改阶段职责或列名时，先改 contract，再同步 `references/contract.md` 与本说明。

> **生产数据仪表盘 + ROI（P0 横切）**：阶段完成后不只回写 `_进度.md`，还要调用 `n2d-dashboard` 写 `生产数据/production_events.jsonl` 并刷新 `dashboard.json` / `dashboard.md`。`_进度.md` 回答“哪步完成了”，仪表盘回答“每分钟成本、每集耗时、一次通过率、重抽率、QA 阻断、投放回收是否支撑工业级”。每次出图/出视频/配音/合成/审查都要入账；上线后把 `platform_metrics.*` 或 `record --event release` 补进去，不能只停在“能生成”。

> **工业化北极星（2026-06-09 口径）**：n2d 的目标不是承诺“一键无人值守百集”，而是做到**工作室级轻工业化**：可复制、可度量、可批量、可回滚、可数据迭代。放量前必须先用第 1 集打样锁定风格/定妆/声音/模型路由，再用 `n2d-batch + n2d-dashboard + n2d-score + n2d-review-ui` 小批量验证成本、通过率、漂移、QA 阻断和投放回收；任何红灯都先回产线修，不盲目追加集数。

> **角色身份闭环（P0/P1 横切）**：用户要“identity_registry / Face Lock / Character ID / LoRA / reference group / 跨集漂移报表”时，调 `n2d-identity`。它读取 `出图/共享/identity_registry.json`，生成 `生产数据/identity_adapter_matrix.json/md` 和 `identity_drift_report.json/md`。出图/出视频/审片只从这套矩阵取身份 binding，不在 prompt 现场手写临时 ID。

> **LoRA 生命周期（P2/P1 横切）**：用户要“LoRA 自动化 / LoRA 训练 / LoRA 部署 / 第三代一致性 / safetensors 注册”时，调 `n2d-lora`。它只服务核心长线角色，管理 `设定库/lora/<CHAR_ID>/<形态>/` 下的数据集、训练任务、验证报告和 registry ready 回写；验证未通过不能写 `lora.status=ready`。

> **合规与版权前置（P0 横切）**：用户要“合规前置 / 版权前置 / 角色授权 / 声音克隆授权 / AI 标识 / 水印 / 平台审核 / 出海本地化”时，调 `n2d-compliance`。它生成/检查 `合规/compliance_manifest.json`，作为 `n2d-review gate` 的硬输入；image 前阻断源文本/改编权/角色肖像授权缺口，video 前阻断声音克隆/AI 标识策略缺口，compose/review 前阻断平台审核、水印落档和出海本地化缺口。合规不可沉默沿用，规则 profile 必须带检查日期。

> **批量任务队列（P1 横切）**：用户要“多集一起跑 / 自动排队 / 并发 / 失败重试 / 只重跑受影响镜头 / worker 自动执行队列”时，调 `n2d-batch`。它按 `_进度.md` 生成 `生产数据/batch_queue.json`，执行者用 `claim` 占并发槽、用 `mark` 回写 pass/fail；配置 `生产数据/batch_runner.json` 后，`runner.py` 可自动 claim、执行配置命令、写 dashboard telemetry、回写状态。定妆变更或审查回流用 `--rerun-from image|video|compose --affected-shot/--affected-artifact` 做最小范围重跑。

> **模型适配层（P1 横切）**：路由到 `/n2d-video` 前，先调 `n2d-model-router` 生成 `出视频/第N集/prompt/video_model_routes.json/md`。`视频模型路由=自动按镜头路由` 为默认：打斗、追逐、对话反打、飞行、空镜、法术爆发、亲密互动、拥抱拉扯、多人同框、群像站位按后端能力选 primary/fallback；`生视频AI` 只做普通镜/兜底，不再固定全片。若用户明确账号/预算限制只能用单后端，才写 `视频模型路由=固定生视频AI`，但每 Clip 仍要写模型路由字段和 fallback/degrade plan。

> **自动审片评分（P2 横切）**：用户要“机器分 / 自动审片评分 / 低于阈值自动回流 / 图像相似度 / 字幕 OCR / 口型检测 / 成片节奏密度”，或完成一次成片/阶段审查后，调 `n2d-score`。它把 `n2d-review` 机检、一致性审查、`n2d-dashboard` 阻断和 `visual_checks.py` 汇总成七维分：角色一致性、服装一致性、场景一致性、字幕正确性、音画同步、节奏密度、风格一致性。默认阈值 `85`；低分输出 `auto_return_tasks`，加 `--enqueue-low` 可直接写入 `n2d-batch` 返工队列。

> **人审可视化 UI（P2 横切）**：用户要“人审 UI / 审片 UI / 无限画布 / 可视化审片 / 看首帧尾帧 clip 接缝定妆 QA flag 机器分”时，调 `n2d-review-ui`。它消费 `storyboard.json`、出图首尾帧、出视频 clip、`identity_registry`、`n2d-score` 输出和 score inputs，生成 `生产数据/review_ui_第N集.html/json`；先用机器分和 QA flag 筛 block/warn，再在画布里逐接缝、逐 clip 人判。

> **投放数据回灌（P2 横切）**：用户要“平台数据反哺 / 投放数据回灌 / 哪种开场留存高 / 哪类 cliffhanger 追更高 / 镜头密度导致跳出 / 自动提取导演标签 / 同集开场封面标题集尾 A/B”，调 `n2d-feedback`。它读取 `platform_metrics`，默认从 `storyboard.json` 自动抽取 `creative_features`（opening/cliffhanger/镜头密度/钩子间隔），也支持同一集多版本 `ab_test_id + variant_id`，比较 `opening_variant / cover_variant / cliffhanger_cut_variant / title_variant` 的同集 paired lift；生成 `生产数据/platform_feedback.json/md`，并可用 `--update-guide` 更新 `novel2drama/references/导演节奏.md` 的数据化快照。手工 `creative_features` 可覆盖自动标签；样本不足只观察。

> **配音后端是关键选择点（首跑前透露一次）**：`/n2d-voice` 多后端——① macOS `say`=**占位专用**（快，但时长不准，仅供出图前 rough timing）；② CosyVoice/GPT-SoVITS（本地克隆，真实时长）；③ MiniMax/火山（云，速度快）。**核心铁律：占位时长 ≠ 真实时长**，用占位定稿镜头/出视频会大返工。推荐 /n2d-voice 时带上后端建议（如 `--backend=cosyvoice`），别让用户默认落到占位。后端选择记入 `_设置.md` 的 `配音后端`（见 `_偏好约定.md`）。

## 制作模式（出片顺序 · 选择点 `制作模式`）

两种出片顺序，**默认且强烈推荐 `配音先行`**。选择点记入 `_设置.md` 的 `制作模式`（见 `_偏好约定.md`）。

**① `配音先行`（默认·推荐）** — 上面的六阶段全景就是这条：
```
剧本改编 → 真实配音(测每句时长) → 分镜设计(时长驱动) → 出图 → 出视频 → 合成
```
真实配音时长驱动镜头/Clip 时长，音画对得准、节奏可控、返工最少。

**② `先出视频后配音`（快速 demo · 不推荐）** — 把真实配音挪到最后：
```
剧本改编 → 估算时长(按台词文本/或 say占位) → 分镜设计(估时驱动) → 出图 → 出视频 → 【后期】真实配音 → 合成(配音拟合到已成片镜头长)
```
镜头时长靠**台词文本估算**锁死（仍需先跑一次 `/n2d-voice` 出占位 `时长清单.json` 当时间脚手架，真实配音留到出视频之后）。

> ### ⚠️ 为什么「先出视频后配音」不推荐（选这条时，**每个阶段入口都要把这段复述给用户**）
> 1. **时长锁错 → 音画不同步**：镜头/Clip 时长只能按台词文本**估算**（估算与真实配音差 20–40%）。等后期补真实配音，长度对不上 → 要么把配音强行变速/塞留白（语速怪、尴尬空拍），要么回头**重切镜头、重出视频**。而**出视频是最贵环节（比图贵 1–2 个数量级）**，这里返工浪费最大。
> 2. **念白表演没参与分镜**：情绪/语速/停顿/钩子的真实念白节奏（黄金 3 秒、钩子憋放、集尾硬断）没驱动镜头设计，留存曲线精度下降——这正是漫剧"留住人"的那一层。
> 3. **对口型无法精准**：正面说话特写的口型在配音之前对不准。
>
> **可接受的场景**：纯视觉 demo / 比稿 / 给客户看画面风格 / 内部快速预览——不追求音画精准。但要讲清：**demo 过审后仍要回头补真实配音并重定时，可能要重切/重出部分镜头**。
>
> **闸门放行**：`配音先行` 下的占位硬闸门（finalize 拒绝定稿、n2d-video 拒绝出视频）在本模式下是**用户主动选择后放行**——finalize 用 `FINALIZE_ALLOW_PLACEHOLDER=1`，n2d-video 见占位时复述上面警告后继续（详见各 skill）。**放行 ≠ 安全**，只是用户已知情同意。

**③ `原生音画`（native AV · 新路线，按剧选）** — 用 Seedance 2.0 / Veo 3 / Sora 类后端一次生成同步音画：
```
剧本改编 → 分镜设计(脚本时长驱动) → 出图 → 出视频(说话镜=原生同步音画: 台词+口型+环境声) → 合成
```
- **说话镜绕过配音先行链路**：`n2d-model-router` 在 `制作模式=原生音画` 时，把对话反打/说话特写/mouth_visible 镜头路由到原生音画后端（`mode=native_av`、`native_audio_policy=native_speech`），台词文本/情绪/单镜时长来自脚本，**这些镜头不出逐句 `时长清单`、不单独跑 n2d-voice 配音**；动作/空镜等非说话镜与配音先行一致。
- **为什么有这条**：行业头部（Seedance 2.0 等）已能一次出同步音画，规避「配音→对口型」代差与「占位时长驱动→重定时返工」的坑。代价：少了逐句音色/语速精细控制；原生口型/音质不稳时本镜回退配音先行（router 写了 degrade_plan）。
- **合规不变**：native_speech 是合成人声，成片仍须 **AI 标识水印**；模仿某真人音色与声音克隆同级**需授权**（compliance gate 把关，不豁免）。
- **适用**：后端原生音画质量够、追求最短链路/规避对口型的项目；对逐句配音表演有强控需求（强情绪念白、特定配音演员音色）仍选 `配音先行`。
- **全链已接通（不再只在 router 层声明）**：① `n2d-script/finalize_storyboard.py` 在原生音画模式下、无配音清单时从 `storyboard.json` 的脚本规划 `duration` 出 `镜头时长.json`（不崩、不读配音）；② `gate.py` 的 image/video 阶段对原生音画**不要求「配音」列就绪**、占位检查放行；③ `n2d-compose` 检测到原生音画时**自动把 `视频原生音轨` 转为「保留原片音轨」**（台词在 clip 自带音轨里，丢弃会丢台词）。说话镜字幕建议用 whisperx 对成片词级对齐（参考 mv-lyric-sync），不在 finalize 按配音重定时。

### 制作模式 · 首跑选择（新作品首次拆集时必给菜单，别静默默认）

`制作模式` 影响全程出片顺序，**不**走"全局默认静默预填"那条——哪怕全局默认是 `配音先行`，**新作品第一次拆集（n2d-script 情境A / 本调度情境A）时也要把菜单念给用户选一次**，选后写入 `_设置.md`、之后沉默沿用、随时可改（机制见 `../_偏好约定.md`「制作模式」条的"首跑必给菜单"例外）。简明菜单原话：

> 先定**出片顺序**（之后默认沿用，随时可改）：
> - **A. 配音先行（推荐）** — 先出真实配音、用实测时长驱动镜头，音画最准、返工最少。**配音素材/音色/凭证已就绪时选这条。**
> - **B. 先出视频后配音（快速 demo / 配音还没就绪）** — 先用估算时长把画面推起来，真实配音留到出视频后再补。代价：后期补音对不准、可能重切重出（最贵的返工），仅 demo/比稿或配音暂时缺位时用；补齐后仍要回来重定时。
> - **C. 原生音画（native AV / Seedance 2.0 类一次出同步音画）** — 说话镜由原生音画后端一次出台词+口型+环境声，绕过配音/对口型。规避代差与占位返工，但少了逐句音色控制；合规仍需 AI 标识，仿真人音色需授权。后端原生音画质量够时用。
>
> 你选哪个？（不选默认 A）

> 实战注脚：本仓库前几集就是因为**早期配音没准备好**而走了 B（后配音）。这正是 B 的合理用途——但每到下一阶段仍会提醒你它的代价。用户一旦明确表态（如"用后配音""先把画面做出来"），按 `_偏好约定.md` 解析顺序第 0 条**当场落档** `制作模式=先出视频后配音`，不必再问。

## 调度工作流

### 入口判定

**情境 A — 用户给了一个小说路径，作品根尚不存在**：
→ 推荐 `/n2d-script <小说路径>`（Stage 1 首跑：拆集 + 精修第1集）。**首跑时把上面「制作模式 · 首跑选择」的 A/B/C 菜单完整念给用户选一次**（配音先行 / 先出视频后配音 / 原生音画 + 一句原因），选后落 `_设置.md`。

**情境 B — 用户给了一个已存在的作品根 或 `_进度.md` 路径**：
→ **先跑源新鲜度自检**（见下「源新鲜度自检」节）→ **再跑 skill 更新影响检查**（见下「skill 更新影响检查」节）→ 再走"读进度 → 路由"流程

**情境 C — 用户问"怎么开始 / 流程是什么"**：
→ 简述上面的六阶段全景 + 让用户给小说路径

**情境 D — 用户要批量推进多集 / 并发 / 失败重试 / 预算上限 / 只重跑受影响镜头**：
→ 推荐 `n2d-batch`，先生成队列而不是直接开跑：
```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes 1-10 --max-concurrency 2 --max-retries 1 --budget <预算>
python3 skills/n2d-batch/scripts/queue.py claim <作品根> --limit 2
python3 skills/n2d-batch/scripts/queue.py mark <作品根> <task_id> --status pass
python3 skills/n2d-batch/scripts/runner.py <作品根> --until-empty --limit 1 --timeout-sec 3600
```
定向返工：
```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --episodes 2 --rerun-from image --affected-shot Clip_03 --scope "只重跑定妆更新影响的 Clip_03"
```

**情境 E — 用户要合规前置 / 版权前置 / 角色授权 / 声音克隆授权 / AI 标识 / 平台审核 / 出海本地化**：
→ 推荐 `n2d-compliance`。先初始化合规包，人工补齐 evidence/profile 后再进付费 gate：
```bash
python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第1集 --init
python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第1集 --check
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage image
```

**情境 F — 用户要自动审片评分 / 机器分 / 低于阈值回流**：
→ 推荐 `n2d-score`。先跑审片机检再评分；需要自动返工就加 `--enqueue-low`：
```bash
python3 skills/n2d-score/scripts/score.py <作品根> 第1集 --run-checks --threshold 85
python3 skills/n2d-score/scripts/score.py <作品根> 第1集 --run-checks --threshold 85 --enqueue-low --max-concurrency 1 --max-retries 1
```

**情境 G — 用户要人审 UI / 无限画布 / 可视化审片**：
→ 推荐 `n2d-review-ui`。先跑 `n2d-score --run-checks` 确保机器分、visual checks 和 QA flag 齐，再生成静态画布：
```bash
python3 skills/n2d-score/scripts/score.py <作品根> 第1集 --run-checks --threshold 85
python3 skills/n2d-review-ui/scripts/review_ui.py <作品根> 第1集 --write --markdown
```

**情境 H — 用户要投放数据回灌 / 留存追更分析 / 更新导演节奏 / 同集 A/B / ROI 回收**：
→ 推荐 `n2d-feedback`。先准备平台指标；导演标签默认从 `storyboard.json` 自动抽取，低置信再用手工 `--features` 覆盖。同集 A/B 时，每个变体一行，至少写 `episode/platform/ab_test_id/variant_id`，并按测试对象补 `opening_variant/cover_variant/cliffhanger_cut_variant/title_variant`：
```bash
python3 skills/n2d-feedback/scripts/feedback.py <作品根> --metrics <平台指标.csv>
python3 skills/n2d-feedback/scripts/feedback.py <作品根> --metrics <平台指标.csv> --write-features --update-guide
python3 skills/n2d-dashboard/scripts/dashboard.py build <作品根> --markdown
```
`platform_metrics.*` 里如果有 `revenue/distribution_spend/currency/duration_sec`，dashboard 会同时生成 ROI：每分钟成本、投放净回收、回收/生产成本。

### 源新鲜度自检（写小说成品更新 → 漫剧源是否过期 + 重切影响）

两条创作线只在**成品文件**一处耦合：写小说导出 → 漫剧 `小说/<剧>.txt`。写小说改了之后，漫剧的源会过期，已拆的 raw 也跟着旧。**进作品根先跑一次自检**（确定性，秒级，不烧上下文）：

```bash
python3 <skill>/source_check.py <作品根>          # 自检：优先比对同名 写小说/<剧>/章节，找不到再比对 小说/<剧>.txt 与 小说/_源指纹.json
python3 <skill>/source_check.py <作品根> --record # 记/更新指纹基线（首切定稿后、或同步并确认后）
```

- **无基线** → 提示用户首切定稿后 `--record` 记一次（之后才能自动发现源更新）。
- **clean** → 静默放行，直接进路由。
- **drift（源已更新）** → 脚本会列出**变动章 + 落在哪些集 + 每集是 `raw-only(可安全重切)` 还是 `已生产(需谨慎)`**。把它讲给用户，给三选：
  - ① **同步源**（若写小说侧改了还没同步）：写小说 `novel-craft/scripts/export.py` 重导出 → 覆盖漫剧 `小说/<剧>.txt`。
  - ② **评估/重切**：⚠️**重切属"不可逆/花钱"点，每次确认、绝不自动执行**。只 raw-only 受影响 → 推进到那些集前从新源重切该窗口 raw（按 `n2d-script` P0→P6 + 精修窗口铁律）；**别为几章重跑整本 split**（字数变动会重排集号、波及已生产集）。触及已生产集 → 逐集评估配音/出图/出视频是否返工。
  - ③ **忽略本次** / 接受现状 → 处理完后 `--record` 更新基线。
- 受影响集可登记进 `脚本/_拆集复核.md` 的"待重切"区，推进到时再切（配合 `首切范围=部分先切`：下游已生产集少 → 改动波及面天然小）。

> 这不是单独的协调 agent——novel↔n2d 的耦合只有一个文件，盯它的新鲜度做进调度器入口即可；常驻 watcher 逆本仓库无状态 skill 架构。
>
> **可选自动守望（agent hook）**：支持会话结束 hook 的 agent 可在自己的私有配置里让 Stop/after-response hook 跑 `source_watch.py`（例如 Claude Code 可放在 `.claude/settings.json`，其它工具按各自 hook 机制配置），扫所有有 `小说/_源指纹.json` 的漫剧，**仅在写小说成品变动时打一行提醒**（含变动章是否触及已生产集），clean 时全静默。即不进调度器、改完写小说也会自动弹。挂源 = 同名 `写小说/<剧名>/章节`（章一改即发现，不必等重导出）。新漫剧首切后跑一次 `source_check.py <作品根> --record` 才纳入守望。

### skill 更新影响检查（skills 更新 → 是否需要重制到当前阶段）

已有作品进入调度时，源新鲜度自检之后再跑一次轻量检查：

```bash
python3 skills/n2d-update/scripts/update_plan.py check <作品根> 第N集 --write-plan
```

- 无变化 → 静默继续读进度路由。
- 无基线 → 提醒先 `record` 建立 skill 快照；如果当前 git 工作区已有相关 skill 改动，脚本仍会列出变动文件。
- 有变化 → 把 `生产数据/skill_update_plan_第N集.md` 讲给用户：从哪个阶段回放、最多重制到哪个当前阶段、哪些 skill 变了。
- **只提示，不自动开跑**：出图/出视频/配音/合成都可能花钱或覆盖产物，必须等用户确认后再交 `n2d-batch` 或对应 stage skill 执行。
- 重制上限 = 该集已到达的阶段。例如第1集当前 `出图=57/68`，计划最多到 `image`，不主动出视频/合成。

阶段完成、用户接受现状或重制结束后，记录新基线：

```bash
python3 skills/n2d-update/scripts/update_plan.py record <作品根> 第N集
```

### 读进度 → 路由

> **首选：跑确定性路由脚本**（别靠 LLM 推 16×N 大表，烧上下文且易错）：
> ```bash
> python3 <skill>/progress.py <作品根>          # 全局：最小未完成集 + 各阶段卡集数 + 推荐命令
> python3 <skill>/progress.py <作品根> 第N集    # 查指定集所处阶段 + 推荐命令
> ```
> 把脚本输出**直接讲给用户**。下面的"逐列判断"是脚本内部逻辑（容错/手查时参考）。
>
> **回写进度统一用脚本**（别手工编辑表格）：`python3 <skill>/progress.py set <作品根> 第N集 <列名> <值>`（值 = ✅ / ⬜ / ⏳rough / 12/19）。各阶段 skill 收尾都调它；`set` 会自动刷新 `脚本/第N集/manifest.json` 产物快照，并记录 `last_progress_state`。旧项目表头缺新列时先跑：`python3 <skill>/progress.py ensure-col <作品根> <列名> ⬜`。需要手动重建快照时可跑：`python3 skills/novel2drama/manifest.py <作品根> 第N集 --stage <stage_key>`。

> **先读 `制作模式` 与 `基础视觉风格`**（`_设置.md`，见上「制作模式」节和 `references/visual_styles.md`）。`progress.py` / `n2d-progress/scan.py` 共用同一套模式感知路由；下面逐列判断默认按 `配音先行`。若 `制作模式=先出视频后配音`，在脚本输出之上叠加以下调整，并**复述「制作模式」节的不推荐警告**：
> - 配音 ⬜ 时，`/n2d-voice` 只为出**占位/估算 `时长清单.json`** 当时间脚手架；占位回写 `配音=⏳rough`，不是 `✅`，真实配音留到最后。
> - 阶段2、出图、出视频遇占位**不拦截**（用户已选此模式）：finalize 用 `FINALIZE_ALLOW_PLACEHOLDER=1`，n2d-video 复述警告后继续。
> - **视频列满后、合成前，插一步真实配音 + 拟合**：`/n2d-voice` 换 CosyVoice/克隆/MiniMax 重出真音轨 → 跑 `n2d-compose/fit_voice_to_clips.py`（先 dry-run 对账，再 `--apply` 出 `voice_<lang>_fitted.wav`，把真音逐镜头拟合到锁定时长；真音远超槽位的镜头列为 overflow、退出码 2，提示回 `/n2d-video` 重出加长）→ 再 `VOICEFILE=…_fitted.wav /n2d-compose`。详见 n2d-compose「先出视频后配音」节。
> - `progress.py` 与 `n2d-progress/scan.py` 共用同一套模式感知路由：`⏳rough` 在该模式下可推进分镜/出图/出视频，但视频满、配音仍占位时会把前沿拦回 `/n2d-voice`（而非 `/n2d-compose`）；`/n2d-compose` 本身也有占位守门，占位轨直接合成会被拒。
> - 旧项目若曾把占位配音写成 `✅`，先跑 `python3 <skill>/progress.py audit-placeholders <作品根>` 检查；确认要修则加 `--fix`，把伪完成降级为 `⏳rough`。

1. 定位 `<作品根>/_进度.md`，读进度表（老项目若仍在 `<作品根>/common/_进度.md`，路由脚本会兼容读取）
2. 进度表头形如：`| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |`
3. 对每一集逐列判断：
   - `剧本改编`/`bgm`/`封面` 任一 ⬜ → 还在 /n2d-script 阶段1·剧本改编
   - 阶段1 齐、`配音` ⬜ → 该集等 /n2d-voice 角色配音(统计台词时长)
   - 非原生音画：`配音` ✅、`分镜设计` ⬜ → 回跑 /n2d-script 阶段2·分镜设计（时长驱动：分镜剧本+故事板+素材清单+SRT）。原生音画：`配音` 可选，`分镜设计` 直接按 `storyboard.json clips[].duration` 定稿。
     - ⚠️ **占位检查**：新进度约定下，占位配音应写 `配音=⏳rough`，真实配音才写 `✅`。旧项目若仍显示 `配音=✅`，也要读该集 `合成/第N集/配音/时长清单.json`，若有 `占位:true`（macOS say 占位音色）→ 告知用户"当前是占位配音，时长不准；正式出视频前必须 /n2d-voice 换真实配音重跑 + 回跑阶段2 重定时"。finalize_storyboard/n2d-video 都会硬闸门拦截，但这里提前透露省返工。
   - `分镜设计` ✅、`出图prompt`/`出图` 未满 → /n2d-image
   - `出图` 满、`视频` 未满 → 先跑 `python3 skills/n2d-model-router/scripts/router.py <作品根> 第N集 --write` → /n2d-video
   - `视频` 满、`成片` ⬜ → /n2d-compose（剪辑合成+BGM+字幕；问用户 BGM 选项）
   - **gate 前置（通用编排规则）**：路由到 image/video/compose 任一阶段时，正式生产入口统一跑 `python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第N集 --stage image|video|compose`（它会调用 `n2d-review/scripts/gate.py --json`，退出码 1 即先补再做，并把 QA 阻断入账）。`gate.py --json` 只作底层/调试入口。结构化输出会带 `return_to_stage` / `affected_artifacts` / `rerun_scope`，用于按最小范围回退返工。image gate 还会拦「storyboard.json 缺 visual_contract 视觉契约种子 / style_contract 基础视觉风格种子 / 本集总览缺契约」，把跨镜一致性和所选基础风格挡在花钱出图之前。旧 `cinematic_contract` 兼容但新产物不再使用该标题。
4. **推荐策略**：
   - 用户没指定集 → 找"最小未完成集编号" + 它所处的阶段，给出对应 skill 建议
   - 用户指定集 → 直接报该集所处阶段
5. **报告格式**：
   ```
   当前作品：<作品名>（共 N 集已拆分）
   最近完成：第K集 Stage 1 物料齐
   下一步建议：调 /n2d-image <作品根> 第K集 生成出图 prompt + PNG
   也可：/n2d-script <作品根> 第K+1集 精修下一集物料（可并行）
   ```

> **删减/改稿走源头回流（别手删产物）**：要删某镜/某句，用 `n2d-script/delete_shot.py <作品根> 第N集 镜头X`——它自动回流 voiceover/EN字幕/时长清单/voice 轨/finalize，并跑一遍 image gate 对账 storyboard.json（删句后接力/时长会失配）；删完按提示同步 storyboard.json 设计文档 + 移走已出 PNG/clip 到 `废料/`，再重跑 compose。绝不在成片 MP4 上直接剪（同源头回流铁律）。

### 跨阶段并行的 OK 信号

阶段不必严格串行——第 K 集出图时，第 K+1 集物料可以并行精修，第 K-1 集视频可以并行生成。**调度规则**：只要 `_进度.md` 该集对应列还是 ⬜ 就可以开干；不需要等前面集全部跑完。

## 作品目录约定

```
制漫剧/<剧名>/
├── 小说/                          原文（.txt/.docx）
├── _进度.md                       全作品 dashboard（4 skill 共用 single source of truth）
├── 设定库/                        跨阶段设定资产
│   ├── global_style.md            全局画风/世界观/目标AI
│   ├── characters/                角色卡（设定 + 定妆 prompt 源头）
│   ├── locations/                 场景卡
│   └── voicebank/                 音色引用/音色库
├── 废料/                          4 选 1 / 废图 / 废视频
│   ├── 出图/{共享,第N集}/       筛选 / 废图
│   └── 出视频/第N集/              废视频片段
├── 脚本/                          ← n2d-script 产物
│   └── 第N集/
│       ├── raw.txt 分镜剧本.md 故事板.md 素材清单.md
│       ├── voiceover.txt bgm.txt 封面.md manifest.json
│       └── 字幕_中文.srt（字幕_英文.srt 仅海外/中英双语时生成）
├── 出图/                          ← n2d-image 产物
│   ├── 共享/                      全篇定妆库
│   │   ├── prompt/
│   │   │   ├── 00_索引.md
│   │   │   └── 角色定妆.md / 场景定妆.md / 道具定妆.md
│   │   └── 图片/定妆_*.png        （共享 PNG 进 图片/ 子目录）
│   └── 第N集/                     本集分镜
│       ├── prompt/
│       │   ├── 00_总览.md         （含本集视觉一致性契约 + 本集基础视觉风格契约，继承 storyboard.json visual/style contract）
│       │   └── 01_分镜出图.md
│       └── 图片/                  （本集 PNG 进 图片/ 子目录）
│           ├── 镜头N_*.png        分镜首帧
│           └── 镜头N_end.png      尾帧接力（=下一 Clip 首帧构图，n2d-video 双帧锁接点）
├── 出视频/                        ← n2d-video 产物（只放 clips + 视频 prompt）
│   ├── 共享/                      （如有跨集复用片段，如转场/空镜）
│   │   ├── prompt/
│   │   └── *.mp4
│   └── 第N集/
│       ├── prompt/
│       │   ├── 00_总览.md
│       │   └── 01_clips.md
│       └── 视频/                  ← clip MP4 全归这（n2d-video 唯一产物）
│           └── ClipK_*.mp4
└── 合成/                          ← 音频 + 后期（n2d-voice 配音 + n2d-compose 成片）
    └── 第N集/
        ├── 配音/                  ← n2d-voice：line_NN.wav + voice_*.wav + 时长清单.json
        ├── _voicecache/           （配音缓存）
        ├── _work/                 （compose 中间产物）
        ├── 成片_第N集_{mode}.mp4   ← n2d-compose 输出
        └── 成片_第N集_{mode}_水印.mp4  （可选：compose 调 shared-watermark 后）
```
> **出视频/ vs 合成/ 分家（2026）**：`出视频/第N集/` 只放 per-shot clips（`视频/`）+ 视频 prompt（`prompt/`）；一切音频/后期——`配音/`（含 `时长清单.json`）、`_voicecache/`、compose `_work/`、最终 `成片_*.mp4` 及可选水印——落同级 `合成/第N集/`。compose 从 `出视频/` 读 clips、从 `合成/` 读配音、把成片写回 `合成/`。

> **prompt/PNG/MP4 分离铁律**：每个 `出图/` 或 `出视频/` 文件夹（无论是 `共享/` 还是 `第N集/`）一律分两层——`prompt/` 子目录装所有 prompt md，**PNG 进 `图片/` 子目录**（与 `prompt/` 同级，含分镜首帧 + 尾帧 `镜头N_end.png`），**clip MP4 进 `出视频/第N集/视频/` 子目录**。详见 `references/architecture.md`「prompt / 产物分离铁律」。

> 旧仓库可能没有 `小说/` 子目录（原文直接在作品根）。仍能识别——作品根下 `.txt/.docx` 即为原文。

## 子 skill 速查

| skill | 何时调 | 输入 | 关键输出 |
|---|---|---|---|
| `/n2d-script` | 阶段1 剧本改编(台词) / 阶段2 分镜设计(配音后) | 小说路径 或 作品根 + 集号 | 阶段1: voiceover+bgm+封面；阶段2: 分镜剧本+故事板+素材清单+字幕 |
| `/n2d-image` | 物料齐后出图 prompt + 生图 | 作品根 + 集号 | `出图/{共享,第N集}/` prompt + PNG + 进度勾 ✅ |
| `/n2d-voice` | 阶段1齐后配音(出图前) | 作品根 + 集号 | `合成/第N集/配音/` 音频 + 时长清单.json + 配音列 ✅ |
| `/n2d-identity` | 角色身份闭环：reference group / Face Lock / Character ID / LoRA adapter matrix + 跨集漂移报表 | 作品根 (+集号范围) | `生产数据/identity_adapter_matrix.json/md` + `identity_drift_report.json/md` |
| `/n2d-lora` | 核心长线角色 LoRA 生命周期：数据集审计、训练任务、验证报告、registry ready 回写 | 作品根 + character_id + form | `设定库/lora/<CHAR_ID>/<形态>/` + 更新 `identity_registry.json` |
| `/n2d-compliance` | 付费生成和投放前置：版权/改编权、角色授权、声音克隆、AI 标识、水印、平台审核、出海本地化 | 作品根 (+集号) | `合规/compliance_manifest.json` |
| `/n2d-model-router` | 出视频前按镜头类型/模板/身份/原生音画/时长选择视频后端 primary/fallback | 作品根 + 集号 | `出视频/第N集/prompt/video_model_routes.json/md` |
| `/n2d-video` | 出图齐后出视频 prompt + 生视频，逐 Clip 继承模型路由表 | 作品根 + 集号 | `出视频/第N集/视频/` MP4（出视频唯一产物=clips）+ 进度勾 ✅ |
| `/n2d-compose` | 视频齐后合成成片(+可选水印) | 作品根 + 集号 | `合成/第N集/成片_第N集_{mode}.mp4` + 成片列 ✅ |
| `/n2d-review` | 任意阶段闸门 / 出成片后质检；或流程自审找优化 | 作品根 (+集号) | 质检报告 `_质检_第N集.md` / 流程自审建议（跨阶段 QA，非必经） |
| `/n2d-score` | 成片或阶段审查后给每集打机器分；含 visual checks；低分自动回流 | 作品根 + 集号 | `生产数据/score_第N集.json/md` + `score_inputs/第N集_visual.json` + `auto_return_tasks` / 可选 batch 队列 |
| `/n2d-review-ui` | 机检/评分后生成人审无限画布，看首帧、尾帧、clip、接缝、定妆参考、QA flag、机器分 | 作品根 + 集号 | `生产数据/review_ui_第N集.html/json` |
| `/n2d-feedback` | 上线一批后把平台留存/追更/跳出数据反哺导演节奏；同集 A/B 比较开场/封面/集尾断点/标题文案 | 作品根 + 平台指标 + 自动/手工导演标签 + 可选 A/B 变体字段 | `生产数据/platform_feedback.json/md` + 可选更新 `导演节奏.md` |

## 常见错误

| 错误 | 纠正 |
|---|---|
| 不查进度直接猜测用户的当前阶段 | 每开始一个会话，务必调用脚本或人工确认 `_进度.md` 的前沿在哪 |
| 跳过合规前置包 (n2d-compliance) | 后续的任何 image/video 生成都会因为 gate 被拦截，造成多次碰壁 |
| 未让用户确认就设定了“先出视频后配音”模式 | 除非用户主动点名要求出 demo，否则应永远以默认的`配音先行`推流程以减少大返工 |
| 源文件更新后（写小说）不检查漫剧侧的过期漂移 | 应依赖于源新鲜度自检及 `update_plan` 判断，重切必要的窗口，以免两边脱节 |

## 实战参考

- 详细架构、目录铁律、首跑示范：`references/architecture.md`
- 翻车 + 修正 + 决策案例（20+ Q&A）：`Q&A.md`
- **导演节奏 / 留存工程（全阶段共用）**：`references/导演节奏.md` —— 留存曲线/黄金3秒/钩子密度/爽点憋放/集尾cliffhanger/镜头时长曲线/卡点/念白节奏。这是红果爆款"画质普通但留人"那一层，n2d-script/voice/video/compose 都引用。
- **模型矩阵（各阶段 SOTA/默认/升级触发，全阶段共用档案）**：`references/模型矩阵.md` —— 配音/图/视频后端的当前梯队与"何时该 opt-in 升级"，n2d-voice/image/video 的"知情提示"都以它为准。
- 镜头空间语法：`n2d-script/references/分镜语法.md`
- 平台档案 / prompt 格式：在各阶段 skill 的 `references/` 下
