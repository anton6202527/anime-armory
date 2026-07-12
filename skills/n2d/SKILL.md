---
name: n2d
description: Dispatcher for the 小说 → AI 漫剧/短剧 production pipeline. Use when given a novel file/path, an existing 作品 folder, or asked anything about turning a novel into AI comic-drama / short-drama materials for 即梦AI / 可灵Kling / Seedance / Veo. Inspects the 作品 root, reads `_进度.md`, and routes the user to the right stage skill — `n2d-script` (阶段1 剧本改编 / 阶段2 分镜设计), `n2d-voice` (配音先行的配音+时长清单 / 原生音画的可选旁白层), `n2d-image` (出图), `n2d-video` (出视频; default completion boundary), or optional `n2d-compose`/`n2d-review` when the project opts into final assembly. Triggers 小说改漫剧, 小说转视频, AI漫剧, AI短剧, 分镜, 配音, 出图, 出视频, 合成, 成片, 验收, 即梦, 可灵, 双语字幕, 海外投放, 题材, 母题, 系统面板, 穿越系统流, 升级场景增强, n2d.
---
> 规模统计：Skill 数 21 | SKILL.md 总行数 4689 | 目录文本总行数 258799

# n2d — 主状态机调度器

> **n2d 系列**（本调度 + `n2d-script`/`n2d-voice`/`n2d-image`/`n2d-video`/`n2d-compose`/`n2d-review`）专管"小说→AI 漫剧/短剧"，**产物统一落 `创作区/制漫剧/<剧名>/`**。

你是 **AI 漫剧制作总调度**。这个 skill 本身不做生产工作，它的职责是：

1. **定位作品根**（创作区/制漫剧/<剧名>/）
2. **读 `_进度.md`** 判断当前作品处于哪一阶段
3. **推荐下一步该调哪个子 skill**（n2d-script 阶段1/2 · n2d-voice · n2d-image · n2d-video；`n2d-compose`/`n2d-review` 是可选尾段）
4. **解释流水线整体结构** 给第一次使用的用户

详细架构与目录约定见 `references/architecture.md`。机器契约见 `references/contract.md`（脚本真值源：`skills/n2d/_lib/n2d_contract.py`，定义阶段图、`_进度.md` schema、manifest、gate 回滚字段）。实战 Q&A 见 `Q&A.md`（全阶段共用，沉淀的翻车修正都在那）。

## 资产目录边界（正式约定）

- **作品根 `设定库/`**：保留，继续做世界观、角色圣经、场景语义、提示词与制作规则的真值层；它比视觉角色资产更广，不被 `角色库/` 替代。
- **作品根 `角色库/`**：替代旧 `设定库/character_assets/`，只收角色可迁移生产包。所有入镜具名人物至少建基础包；主角/核心长线/预计出场 10 集及以上用 `core_full`，复现配角用 `recurring_standard`，具名短线角色用 `named_minimal`，局部群像用 `restricted_partial`。档位控制生产深度，不改变角色 DNA 真值归属。
- **作品内非角色视觉资产**：场景、道具、武器、服装、VFX 仍由 `出图/共享/asset_registry.json` + `出图/共享/图片/` 管理；稳定、审过且授权清楚后，才显式导出。
- **系列根 `创作区/制漫剧/_资产库/`**：只供制漫剧系列不同作品复用，不是仓库公共层。其它五条生产线各有自己的 `_资产库/`，任何生产线不得运行时 import 或回读另一条线的目录。
- **跨系列 / 跨仓库 / 跨机器**：只显式交付所需的单个自包含 asset pack。目标侧复制或 fork 后自行适配；包必须 `requires_source_library=false`，不要求顺带打包整个系列库。
- **旧目录迁移**：运行 `python3 skills/n2d-image/scripts/migrate_character_library.py <作品根>` 先 dry-run，确认后加 `--apply`。发现旧、新两套同时存在时脚本拒绝自动合并，避免双真值长期并存。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/n2d/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`制作模式`、`合成阶段`、`项目规模`、`基础视觉风格`、`视频模型路由`（只记录用户主动固定约束；具体生视频后端到 n2d-video 阶段再定）、`生视频模型`、`生视频渠道`、`生图模型`、`生图AI`（旧称，实为 `生图渠道`/访问入口）、`配音后端`、`视频分辨率`、`画幅`、`对口型`、`BGM来源`、`一致性增强`、`目标平台`、`发行地区`、`合规用途`。

> 作为生产线入口：开新作品（`创作区/制漫剧/<剧名>/`）时先给首跑选择包（至少 `制作模式` + `项目规模` + `基础视觉风格`；有明确账号/预算/后端约束时可先问 `生图模型` + `生图AI/生图渠道`），选后初始化 `<作品根>/_设置.md`。`项目规模=多集长线/长篇量产` 时，首跑就把“GPT Image 2/Codex 参考派生 vs Seedream/可灵等原生主体库”的一致性税讲清：短 demo 可用 GPT Image 2，经 Codex/OpenAI 访问；长线核心/常驻角色默认推荐主体库或等效 face_embedding/LoRA，别等第 3 集才被 gate 拦。真正进 `n2d-image` 付费生图前会重新扫描当前可用生图渠道：多个可自动落 PNG 的官方/已登录渠道则让用户选一个并写 `生图AI`，同时确认/补齐对应 `生图模型`；一个都没有则停下提示准备可用生图渠道。拆集不再让用户选择单集时长；内部用 `拆集节奏=前长后短` 的节奏倾向，旧项目 `_设置.md` 的 `单集时长` 仅作兼容读取。粗拆默认按章/场景/强钩候选，不锚字数；剧情连贯和剧情丰满优先于时长，不能为省秒数删掉必要镜头、铺垫、动机或承接。**生视频后端选择不在开局出现**：开局只记录用户主动指定的固定后端/单账号/交付硬约束；默认写/沿用 `视频模型路由=自动按镜头路由`，具体 `生视频模型` / `生视频渠道` 到 `n2d-video` 出视频前由 router/probe + 适配层决定，无法自动执行或需要人工取舍时再问。若 `_设置.md` 已存在，直接沿用其中值；若用户本轮已明说某项，按其话覆盖落档。旧项目的 `生视频AI` 只作兼容 fallback，新项目不要再写这个合并字段。

## 主状态机全景（模式感知·同一套进度表）

```
小说.txt/.docx
   ↓ 源理解合同              source_comprehension：现代白话理解 + 爽点承诺账 + 人物动机 + 因果链 + 伏笔账 + 设定/战力规则（confirmed 才能拆集）
   ↓ P-1 开发包              series_bible + 改编策略 + 前3-5集追更弧 + 制作可行性 + 试播绿灯（confirmed 才进阶段1）
   ↓ n2d-script  阶段1·剧本改编   voiceover(台词) + 角色/场景/style + bgm + 封面（**不做分镜**）
   ↓ 低成本围读验收          table_read_packet：台词/角色声音/时长风险 confirmed 才进导演排戏
   ↓ 制作模式分流
      A 混合自动路由（默认）   → 声音选角 + 无 WAV 时间基准；逐镜分流表演音轨/后期配音/画面先行/native AV
      B 配音先行              → 已锁音色的真实配音 + 时长清单；配音时长驱动分镜；视频层无声
      C 原生音画              → 跳过逐句配音硬依赖；脚本时长驱动分镜
      D 先出视频后配音        → 旧式项目级画面先行固定策略；仅用户明确选择时采用
   ↓ P-2 导演排戏包          director beat sheet + 轴线调度 + 景别进程 + 转场图 + 竖屏构图 + 剪辑节奏（confirmed 才进阶段2）
   ↓ n2d-script  阶段2·分镜设计   主干提炼 + Clip 时长权重 → 按所选模式定稿 Clip 时长 → 分镜剧本 + 故事板 + 素材清单 + 字幕_中/英.srt + 镜头时长.json
   ↓ Animatic 粗剪验收       animatic_packet + timed HTML/JSON 预览：镜头节奏/信息可读/贵工位风险 confirmed 才进出图 prompt
   ↓ P-3 制片拆解包          production breakdown + continuity chain + continuity bible + AI shooting schedule + batch seed + AI call sheet（confirmed 才进出图 prompt）
   ↓ n2d-image                  出图 prompt + PNG
   ↓ n2d-video                  图生视频；逐镜声音路线决定表演音轨、base video→后期口型、无声画面或 native AV；默认到 clip_delivery_complete
   ↓（可选：合成阶段=启用）
     n2d-compose                OTIO 多轨时间线 + 粗剪 preview + 剪辑合成 + 背景音乐 + 字幕；原生音画模式保留 clip 原片音轨
   ↓（可选尾段）
     n2d-review                 release verdict + production locks + creative governance + 失败归因回流 + review gate + score + 验收总账 + review-ui；只在已启用合成/发布包时签收 master_delivery_complete
```

每个阶段都按 **集** 为单位推进；进度统一写进 `<作品根>/_进度.md`。`合成阶段` 默认 `跳过`：`视频` 列完成只表示 `clip_delivery_complete`（镜头 MP4 齐，可内部预览/继续后配音），不等于可发布母版；齐片后会 best-effort 用真实 Clip + `edit_target_sec` 生成 `actual_rough_cut.mp4`，用于尽早看节奏但仍不是母版。用户需要母带、BGM、烧字幕、交付矩阵或发布证据包时，再把 `_设置.md` 的 `合成阶段` 设为 `启用` 或直接调用 `n2d-compose`；只有合成、技术 QA、锁版和人工验收通过，才叫 `master_delivery_complete`。发行再按 `publish_ready_cn / publish_ready_overseas / publish_ready_commercial` 分别判，不用一个“完成”状态混掉地区/用途差异。

> **运行时收敛层**：正式 `run.py next` 会物化 `生产数据/episode_graph_第N集.json`（storyboard→route→job→media→粗剪→母版→release 的派生索引）和 `生产数据/blocking_bundles/latest_第N集.json`（选择/付费/合规/adapter/合同/QC 分类修复包），并追加隐私最小化 `flow_events.jsonl`。这些都不另立状态机：`_进度.md`、现有 gate 与 release verdict 仍是权威。安全的 report-only 前置按 stage 缓存，指纹覆盖脚本、合同、路由、prompt 与媒体变化；命中只省重复执行，不缓存 block/异常。

> **机器契约层**：阶段顺序、列名、gate stage、每集 manifest、回退目标统一由 `skills/n2d/_lib/n2d_contract.py` 定义，`progress.py` / `n2d-progress` / `n2d-review gate` 复用它。改阶段职责或列名时，先改 contract，再同步 `references/contract.md` 与本说明。
>
> **开局能力自检（doctor·E2）**：接手一个作品后、跑重活前，先 `python3 skills/n2d/doctor.py [作品根]` 一次性摊开本机精度档——脸部机检 `full|degraded|none`（缺 insightface→近景自动转人审）、ffmpeg、配音后端和所选生图后端连通。混合默认下，缺配音后端不会触发 `say`/静音占位；先产 `voice_casting.json + timing_estimate.json`，等音色锁定后再验证最终渲染后端。生视频后端若未固定，doctor 只提示“后移到 n2d-video”，不在开局探默认模型/渠道；只有 `视频模型路由=固定生视频模型` 时才展示关键帧能力档。只探不改、不花钱。

> **工业化北极星（2026-06-09 口径）**：n2d 的目标不是承诺“一键无人值守百集”，而是做到**工作室级轻工业化**：可复制、可度量、可批量、可回滚、可数据迭代。放量前必须先用第 1 集打样锁定风格/定妆/声音/模型路由，再用 `n2d-batch + n2d-dashboard + n2d-score + n2d-review-ui` 小批量验证成本、通过率、漂移、QA 阻断和投放回收；任何红灯都先回产线修，不盲目追加集数。生产级治理补齐后，发布/放量前优先跑统一交付门：`python3 skills/n2d/scripts/production_readiness.py <作品根> 第N集 --write`。它会串起 `run.py next --json`、strict trace 的 `event_ledger.py audit/replay`、`generation_recipe_manifest.py`、`gate_policy_coverage.py`、`validate_artifacts.py`、`release_manifest.py build/check`、`artifact_lineage.py`、`production_locks.py check`、`creative_governance.py check`、`governance.py check/dead-letter`、题材包上下文等证据，落 `生产数据/production_readiness_第N集.*`；单项工具仍可单独调试。留存闸门不再等到 3 集后才看：第 1-2 集进入出图 prompt 前先跑 `pilot_arc_contract` strict gate，锁系列承诺、主角欲望、首个兑现/阻碍/反转；第 3 集起再叠完整 series retention gate（跨集冷开场链、雷同桥段、看点高潮位）。

> **2026 市场现实 → 两条运营铁律（联网基准·见 `n2d-dashboard/references/industry_benchmark.json`）**：
> 1. **速度即生死（R3·爆款新鲜期缩至 ~3 周·ROI 中位 ~1.1）**：抢新鲜趋势窗口比打磨更值钱。打样与抢先**并行**（第 1 集打样的同时，用 `n2d-batch` 把后续集的文字/出图 prompt 先备好），不串行等。成本侧守 dashboard 的 `cost_per_finished_min`（全链行业带 400-1000 元/分）与 `recoup_ratio`，红线先治。
> 2. **Agent 自动串接，人只做决策（I2·行业 Agent 取代工具链）**：确定性步骤（机检/规划/记账/gate）应由代理**自动链式跑完**，只在**决策点 + 花钱点 + 合规点**停下问人（见 `skills/n2d/references/选择点与偏好.md`「AI 代理交互节点」）。不要把割裂的 CLI 命令甩给用户手敲；`anchor_planner → 确认 → n2d-image`、`gate → score → review-ui` 这类"机器算完接语义判断"的组合，代理应在后台一气呵成，用户感受到的是连贯创作助理。

### 横切 skill 速查（非必经 · 全文见 [`references/横切skill地图.md`](references/横切skill地图.md)）

主状态机之外的横切能力，按用户意图点名触发即调。**其中的确定性前置（gate / model-router / 身份矩阵刷新 / 合规检查）已由编排器 `run.py next` 自动跑进每个 stage 的 prework**（见下「读进度 → 路由」），这里只在用户**显式**要某能力、或要理解其完整职责时用：

| 触发意图 | 调 | 一句话 |
|---|---|---|
| Agentic 总控 / 自动前置 / 专家派发 / context pack / creative loop | `n2d-supervisor` | 消费 `run.py next --json`，只在选择/花钱/合规/验收点停人；少量 specialist 只产建议与草稿，不替代 stage skill |
| 生产数据 / ROI / 成本 / 通过率 / 重抽率 / 监控告警 / 事件账本审计 | `n2d-dashboard` | 阶段完成必入账；`event_ledger.py` 审计/重放账本，回答可追溯和工业级成本/回收 |
| 身份闭环 / identity_registry / Face Lock / Character ID / 跨集漂移报表 | `n2d-identity` | 出图/出视频/审片的身份 binding 真值源 |
| LoRA 训练 / 部署 / 第三代一致性 / safetensors 注册 | `n2d-lora` | 仅核心长线角色；验证未过不写 `ready` |
| 合规 / 版权 / 角色授权 / 声音克隆 / 平台审核 / 出海 | `n2d-compliance` | 付费 gate 硬输入；缺口阻断 image/video/compose |
| 多集批跑 / 排队 / 并发 / 重试 / 只重跑受影响镜头 / 死信停线 | `n2d-batch` | 按 `_进度.md` 生成队列；幂等键、错误分类、SLO、dead-letter 支撑放量治理 |
| 模型路由 / 按镜头选视频后端 / primary·fallback | `n2d-model-router` | 出视频前置；默认按镜头路由 |
| 机器分 / 自动审片评分 / 低分回流 | `n2d-score` | 七维分，默认阈值 85，低分入 batch |
| 人审 UI / 无限画布 / 可视化审片 / 人审校准 | `n2d-review-ui` | 静态画布 + 金标 case 校准，统一人工 block/warn/pass 口径 |
| 投放回灌 / 留存追更 / 同集 A/B / 更新导演节奏 / 实验登记 | `n2d-feedback` | 平台指标反哺，A/B 先登记实验再审计样本和变体 |

> 完整职责、输入/产物、命令示例见 [`references/横切skill地图.md`](references/横切skill地图.md)；底部「子 skill 速查」表含各自产物路径。

> **声音选角先行，最终配音后置**：混合默认先跑 `python3 skills/n2d-voice/voice_preflight.py prepare <作品根> 第N集`，只写 `设定库/voice_casting.json` 与 `合成/第N集/配音/timing_estimate.json`，不生成 WAV。试听通过后用 `voice_preflight.py lock` 锁 backend/model/voice_id/canonical sample/审批人；只有锁定后才允许 `render_voice.py` 批量渲染。macOS `say` 只保留给显式旧模式/冒烟测试，不再是新项目估时默认。

## 制作模式与视频路由（调度摘要）

完整规则、模式代价、固定后端菜单和多帧路由细则见 [`references/制作模式与视频路由.md`](references/制作模式与视频路由.md)。入口只执行以下硬规则：

- `制作模式` 是作品级选择点，写入 `_设置.md`；机器默认由 `skills/n2d/_lib/n2d_const.py::PRODUCTION_MODE_DEFAULT` 定义，当前默认是 `混合自动路由`。真正的默认原则是“时间基准先行”，不是“最终配音先行”。
- 新作品第一次拆集必须问一次制作模式，不能因全局默认静默预填。菜单：**A. 混合自动路由（当前机器默认）**（声音选角先行；先产无 WAV 时间估算，再按镜头分流）、**B. 配音先行**（音色已锁且对白表演占绝对主导时，可用真实表演音轨驱动全片）、**C. 原生音画**（经能力核验的镜头一次出台词+口型+环境声）、**D. 先出视频后配音**（旧式项目级固定画面先行，仅显式兼容）。`production_mode_router.py` 会写 `clip_routes[]`：`performance_audio_first / base_video_then_post_lipsync / rough_timing_final_dub_later / post_dub / picture_first / native_av`，并记录 timing basis、表演轨状态、音色锁状态和最终声音阶段。
- `混合自动路由` 下：对白近景/正反打/口型可见镜，有可信表演轨就前置驱动；没有时只允许生成 `base_video_only` 中性嘴型基础片，最终声音就绪后走独立后期表演/口型 pass。旁白、内心戏、口外音只用 `timing_estimate.json` 锁大致节奏；动作、空镜、蒙太奇画面先行；逐镜 `native_speech` 可直接走原生同步音画。
- 用户明确说“整个项目统一后配音”“所有镜头先把画面做出来”时，才落档 `制作模式=先出视频后配音`；一般的“最终配音后置”不再自动归入 D，而由默认 A 逐镜处理。
- `原生音画` 的说话镜由 router 写 `mode=native_av` / `native_audio_policy=native_speech`；若后端不支持原生说话，必须写 `requires_voice_fallback=true`，gate 重新要求真实配音。
- 原生音画合成时保留视频原生音轨；review/付费投放前必须有 `字幕_中文.srt` 和 `生产数据/native_av_subtitle_alignment_第N集.json`。
- 新作品默认 `视频模型路由=自动按镜头路由`。开局不问 `生视频模型`/`生视频渠道`，除非用户主动固定后端、项目已有固定模式、router/probe 找不到可执行后端，或发行/能力缺口需要用户确认。
- 视频后端能力以 `n2d-video` 的 router/probe/适配层为准；未知或未核验的新后端不得假定支持多帧、原生音画或首尾帧能力。

## 调度工作流

### 入口判定

**情境 A — 用户给了一个小说路径，作品根尚不存在**：
→ 推荐 `n2d-script <小说路径>`（先落 P-1 开发包草稿 + 首批粗切，再进 Stage 1）。**首跑时先按上面摘要把制作模式菜单念给用户选一次**，再按 `n2d/references/visual_styles.md` 选择 `基础视觉风格`；生视频后端不在开局选择，除非用户主动固定某后端/账号硬约束，否则延后到 `n2d-video` 出视频前由 router/probe 决策。选后统一落 `_设置.md`。
> **P-1 开发包 gate（拆集/写词前的制片开发层）**：新作品会在 `<作品根>/开发包/` 生成 `series_bible.md`、`adaptation_strategy.json`、`season_arc.json`、`production_feasibility.json`、`pilot_greenlight.md`。`run.py next/enter` 在 `script_stage1` 前自动跑 `development_pack.py check --write-missing`；`status=confirmed` 只代表内容填完，另需 `开发包/signoff.json` 绑定当前源输入、五件套 SHA、明确 reviewer/role/time/risk，由创意与制片两组签收。任一内容或 signoff 缺失/过期都会阻断正式写词。
```bash
python3 skills/n2d-script/scripts/development_pack.py <作品根> scaffold --write
python3 skills/n2d-script/scripts/development_pack.py <作品根> check --json --write-missing
```
> **低成本围读 gate（导演排戏前的编剧室/演员围读层）**：每集完成 voiceover/时长脚手架后先生成 `table_read_packet.json/md`。内容 `status=confirmed` 只表示可审；director/head_writer 还须在 `table_read_signoff.json` 对当前输入与围读包哈希签收。这样先发现“台词不活、信息太满、角色声线不清”，又不允许生成器自称已围读。
```bash
python3 skills/n2d-script/scripts/story_acceptance_packets.py <作品根> 第1集 scaffold --kind table_read
python3 skills/n2d-script/scripts/story_acceptance_packets.py <作品根> 第1集 check --kind table_read --json --write-missing
```
> **P-2 导演排戏包 gate（分镜前的导演排戏层）**：围读确认后，`run.py next/enter` 在 `script_stage2` 前继续自动跑 `director_blocking_pack.py check --write-missing`。脚本可从旧 storyboard 预填内容，但永远保持 draft，不自我签收；六件套内容 confirmed 后，还要由导演 + 制片/剪辑在 `director_blocking_signoff.json` 对当前哈希双角色签收。
```bash
python3 skills/n2d-script/scripts/director_blocking_pack.py <作品根> 第1集 scaffold --write
python3 skills/n2d-script/scripts/director_blocking_pack.py <作品根> 第1集 check --json --write-missing
```
> **正反打连续性合同（传统影视语法 → AI 生产）**：P-2 的 `axis_blocking_map.json` 不只写“守轴线”，还必须在 `shot_reverse_patterns[]` 锁 180° 行动轴线、A/B 屏幕左右或 9:16 纵深高低位、互补视线、OTS/clean single/insert coverage、镜头高度/距离匹配、越轴策略和缓冲/重建空间镜。凡 `storyboard.json` 用 `dialogue_shot_reverse`，先跑 `python3 skills/n2d-script/scripts/shot_reverse_contract.py <作品根> 第N集 --write --sync-axis-map` 物化 `脚本/第N集/shot_reverse_contract.json` 并回填 `shot_reverse_patterns[]`；P-3 会把它继承进 `continuity_bible.json#shot_reverse_continuity`，出图/出视频 prompt 收据也会记录该合同 SHA。无理由越轴、左右互换、看镜头替代看戏内对象、OTS 没有前景肩部，视为连续性硬伤，不靠后期补救。
> **Animatic 粗剪 gate（出图 prompt 前的导演预演验收层）**：从 storyboard + 镜头时长物化 timed preview、working `editorial_timeline.otio` 与不可变 `animatic_timeline.otio` 签收快照。放行要同时满足预览可生成、packet 内容 confirmed，以及导演 + 剪辑/制片在 `animatic_signoff.json` 对当前输入、preview 与快照哈希签收；后续镜头替换只更新 working OTIO。
```bash
python3 skills/n2d-script/scripts/story_acceptance_packets.py <作品根> 第1集 scaffold --kind animatic
python3 skills/n2d-script/scripts/story_acceptance_packets.py <作品根> 第1集 check --kind animatic --json --write-missing
```
> **P-3 制片拆解包 gate（出图 prompt 前的一副导演/场记/制片交接层）**：Animatic 签收后自动生成六件套；内容 confirmed 后，还要由制片/副导演/场记在 `production_handoff_signoff.json` 对当前 storyboard、P-2 签收、animatic 签收与交付文件哈希签收。
> **接缝分类硬合同**：P-2 为每条 seam 显式写 `continuous_take_relay / match_on_action / graphic_match / eyeline_cut / reaction_cut / insert_cutaway / j_cut / l_cut / dissolve / hard_cut / intentional_discontinuity` 之一及模式证据。只有 relay 绑定同一边界帧 SHA；动作匹配看相位/方向，graphic match 看匹配元素/构图，视线/J-L/反应/插入/溶解各看自身证据。迁移脚本只生成待审候选。
```bash
python3 skills/n2d-script/scripts/production_breakdown.py <作品根> 第1集 scaffold --write
python3 skills/n2d-script/scripts/production_breakdown.py <作品根> 第1集 check --json --write-missing
python3 skills/n2d-batch/scripts/queue.py plan <作品根> --from-shooting-schedule <作品根>/生产数据/ai_shooting_schedule_batch_seed_第1集.json
```
P-3 还会生成 `生产数据/ai_shooting_schedule_batch_seed_第N集.json/md`，把排期翻译成可导入 batch queue 的 image/video 任务草案。人确认 P-3 后再导入队列，队列仍走现有 stage command、gate 和 output verify，不绕过 `n2d-image` / `n2d-video`。
> **预防式合同 gate（不是更多检测器，而是下游开工条件）**：`run.py next/enter` 会按阶段自动跑 `skills/n2d/scripts/preventive_contracts.py`。`script_stage2` 前要求本集承诺/兑现/阻碍/集尾钩；`image_prompt` 前要求每个 Clip 有戏剧功能和剪辑意图；`image` 前要求核心角色/道具/场景有引用槽位、多视角/身份锁策略；`video_prompt`/`video` 前要求持物、接触、打斗、多人同框、法术特效有物理/动作分解；`video_prompt`/`video`/`compose` 前要求对白近景、原生音画、后配音的口型/字幕/声纹/时长策略；`review/release` 前第1集必须有 pilot acceptance。`status=confirmed` 现在不是空口签收：相关合同段不能含 TODO/待补，Clip id 必须能反查 `storyboard.json`，引用槽位必须指向真实文件 path/hash，pilot acceptance 必须带 reviewer、risk_selection、代表 clip 的 artifact path/hash 和 QC 报告。源理解里的 `SRC_*` trace id 必须进入 episode/shot/prompt/产物链路，`contract_trace.py` 在 release 前会审。缺口会写 `生产数据/preventive_contracts_<stage>_第N集.*` 并阻断，先补 `脚本/第N集/preventive_contracts.json` 到 `status=confirmed`。
```bash
python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第1集 --stage script_stage2 --write --write-missing --json
python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第1集 --stage image_prompt --write --json
python3 skills/n2d/scripts/preventive_contracts.py <作品根> 第1集 --stage video_prompt --write --json
```
> **源理解合同 gate（拆集前最上游）**：不能只切章节。`run.py next` 在 `script_stage1` 会先跑 `source_language.py`，只要 `小说/*.txt` 存在，就要求 `设定库/source_comprehension.json` 为 `status=confirmed`，且 `understanding_contract` 补齐现代白话理解、爽点/承诺账、人物动机、因果链、伏笔账、改编边界和设定/战力规则；文言文/外文只影响脚手架模板，不再是唯一阻断条件。处理命令：
```bash
python3 skills/n2d-script/scripts/source_language.py <作品根> --scaffold
python3 skills/n2d-script/scripts/source_language.py <作品根> --json
```
> 放行后流程口径是：**小说 → 源理解合同 → P-1 开发包 → 每集承诺合同 → 围读 → P-2 导演排戏 → 分镜意图合同 → executable animatic → P-3 制片拆解/场记链/场记 bible/排期/队列种子 → 引用/动作/音频合同 → AI shooting schedule 入 batch → 生成后场记日志 → 粗剪 timeline/preview → rough cut lock → picture lock → 重大变更决策账 → pilot / mini-pilot 风险抽样 → 小批量 stop-loss → release verdict profile → creative governance → 失败归因与预防规则回写**。这条链条的目标是预防错误理解、错删伏笔、镜头无功能、引用不真实、相邻/跨集镜头裸断、复杂动作崩坏、音频后置救火、锁版漂移、发布证据不全和“制作没错但没人想追”，而不是等人审发现后再局部重抽。

**情境 A2 — 用户明确要从中间章节/中间集开始制作**：
→ 先让 `n2d-script` 创建并补齐中段开工前情资产包，再拆目标窗口；不要只截目标章节直接写词。
```bash
python3 skills/n2d-script/scripts/midstart_context.py <作品根> scaffold --target "第48章" --window "第45-52章"
python3 skills/n2d-script/scripts/midstart_context.py <作品根> check
```
必补：主角常态/当前形态、形象生命周期、前情摘要、关键角色/场景/道具卡、目标章节前后窗口。`check` 通过后再跑 `split_novel.py` 或精修目标集；`run.py next` 在 `script_stage1` 前若发现该资产包未补齐会阻断。

**情境 B — 用户给了一个已存在的作品根 或 `_进度.md` 路径**：
→ **先跑源新鲜度自检**（见下「源新鲜度自检」节）→ **再跑 skill 更新影响检查**（见下「skill 更新影响检查」节）→ 再走"读进度 → 路由"流程

**情境 C — 用户问"怎么开始 / 流程是什么"**：
→ 简述上面的主状态机全景 + 让用户给小说路径

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

**情境 E — 用户要合规前置 / 版权前置 / 角色授权 / 声音克隆授权 / 平台审核 / 出海本地化**：
→ 推荐 `n2d-compliance`。先初始化合规包，人工补齐 evidence/profile 后再进付费 gate：
```bash
python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第1集 --init
python3 skills/n2d-compliance/scripts/compliance.py <作品根> 第1集 --check
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage image_preflight
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

### 源新鲜度自检（本剧源文本更新 → 漫剧源是否过期 + 重切影响）

本剧 `小说/<剧>.txt` 改了之后，已拆的 raw 也跟着旧。**进作品根先跑一次自检**（确定性，秒级，不烧上下文）：

```bash
python3 <skill>/source_check.py <作品根>          # 自检：比对 小说/<剧>.txt 与 小说/_源指纹.json
python3 <skill>/source_check.py <作品根> --record # 记/更新指纹基线（首切定稿后、或同步并确认后）
```

- **无基线** → 提示用户首切定稿后 `--record` 记一次（之后才能自动发现源更新）。
- **clean** → 静默放行，直接进路由。
- **drift（源已更新）** → 脚本会列出**变动章 + 落在哪些集 + 每集是 `raw-only(可安全重切)` 还是 `已生产(需谨慎)`**。把它讲给用户，给三选：
  - ① **确认源**：确保本剧 `小说/<剧>.txt` 已是当前要使用的源文本。
  - ② **评估/重切**：⚠️**重切属"不可逆/花钱"点，每次确认、绝不自动执行**。只 raw-only 受影响 → 推进到那些集前从新源重切该窗口 raw（按 `n2d-script` P0→P6 + 精修窗口铁律）；**别为几章重跑整本 split**（字数变动会重排集号、波及已生产集）。触及已生产集 → 逐集评估配音/出图/出视频是否返工。
  - ③ **忽略本次** / 接受现状 → 处理完后 `--record` 更新基线。
- 受影响集可登记进 `脚本/boundary_review.json` 的待重切/边界签收记录，推进到时再切；该文件按 episode + raw 指纹校验，源片段变化后旧签收失效（配合 `首切范围=部分先切`：下游已生产集少 → 改动波及面天然小）。

> **可选自动守望（agent hook）**：支持会话结束 hook 的 agent 可在自己的私有配置里让 Stop/after-response hook 跑 `source_watch.py`（例如 Claude Code 可放在 `.claude/settings.json`，其它工具按各自 hook 机制配置），扫所有有 `小说/_源指纹.json` 的漫剧，**仅在本剧源文本变动时打一行提醒**（含变动章是否触及已生产集），clean 时全静默。新漫剧首切后跑一次 `source_check.py <作品根> --record` 才纳入守望。

### skill 更新影响检查（skills 更新 → 是否需要重制到当前阶段）

已有作品进入调度时，源新鲜度自检之后再跑一次轻量检查：

```bash
python3 skills/n2d-update/scripts/update_plan.py check <作品根> 第N集 --write-plan
```

- 无变化 → 静默继续读进度路由。
- 无基线 → 提醒先 `record` 建立 skill 内容快照（基于文件内容 SHA，无版本控制依赖）；建立前无法检测变更。
- 有变化 → 把 `生产数据/skill_update_plan_第N集.md` 讲给用户：从哪个阶段回放、最多重制到哪个当前阶段、哪些 skill 变了。
- **只提示，不自动开跑**：出图/出视频/配音/合成都可能花钱或覆盖产物，必须等用户确认后再交 `n2d-batch` 或对应 stage skill 执行。
- 重制上限 = 该集已到达的阶段。例如第1集当前 `出图=57/68`，计划最多到 `image`，不主动出视频/合成。

阶段完成、用户接受现状或重制结束后，记录新基线：

```bash
python3 skills/n2d-update/scripts/update_plan.py record <作品根> 第N集
```

### 读进度 → 路由

> **首选：跑编排器 `run.py next`**（I2 铁律的落地——一条命令把"找前沿 → 跑确定性前置（doctor / model-router / gate / compliance / 首跑选择探测）→ 停在第一个决策/花钱/合规点"收敛掉，别再手敲那串散装 CLI）：
> ```bash
> python3 skills/n2d/run.py enter <作品根>         # 进入作品：先跑源新鲜度 + skill 更新影响检查，再给下一步动作卡
> python3 skills/n2d/run.py next <作品根>          # 最小未完成集：自动跑前置，停在下一个 stop-point，给「下一步动作卡」
> python3 skills/n2d/run.py next <作品根> 第N集    # 指定集
> python3 skills/n2d/run.py pilot <作品根> 第1集   # 首集打样计划：按分镜风险挑 2-3 个代表 Clip，先验证画风/脸/口型/接缝/路由
> python3 skills/n2d/run.py next <作品根> --json   # 机器可读 NextAction（代理消费 frontier/prework/stop_reason/action_card/gate）
> ```
> `stop_reason` 的唯一机器真值在 `n2d/_lib/n2d_action_registry.py::STOP_REASONS`，当前完整集合为 `{needs_agent_gen, needs_stage_execution, needs_payment_confirm, needs_choice, needs_compliance, needs_acceptance_signoff, blocked_by_entry_check, capability_evidence_required, blocked_by_gate, blocked_by_image_qc, blocked_by_review_acceptance, prework_failed, env_missing, auto_ran, done, unknown_stage}`。schema、run.py 和 n2d-supervisor 都消费同一集合；未登记值 fail-closed，禁止消费者静默漏分支。`blocked_by_gate` 透传最小返工，`auto_ran` 表示确定性前置已执行，`unknown_stage` 必须升级人工/维护者处理。设计契约见 `../../docs/n2d-编排器设计.md`。
> 入口检查若发现 skill/source/资产漂移，`run.py next|enter` 会先自动跑 `skills/n2d/scripts/repair_preflight.py <作品根> 第N集 --stage <stage> --write-missing --json`（视频链路会尝试 `--repair-qc`），再刷新 entry check；仍未通过才停下给报告路径。出图/出视频 prompt pack 还会分别写 `生产数据/consumed_contracts_image_prompt_第N集.json`、`consumed_contracts_video_prompt_第N集.json`，绑定 storyboard、continuity_chain、script_quality_contract、director_camera_plan、reference_plan 和 prompt 文件 SHA；preflight 发现缺失或 SHA 过期即回对应 prompt 阶段。
> NextAction 同时带 `action_contract`、`trace`、`action_card.context_pack`、`action_card.creative_loop`、`action_card.specialist`：`n2d-supervisor` 只消费这些契约做上层编排和专家派发，不能让单个 skill 自己决定下一步、改 `_进度.md`、绕过 gate 或执行付费操作。
> 产物契约体检统一走 schema registry：`python3 skills/n2d/scripts/validate_artifacts.py <作品根> --write` 会扫描现有 JSON/JSONL，校验 `kind/version`、关键机器字段、batch/trace/context/supervisor/gate policy 等结构，落 `生产数据/artifact_validation.{json,md}`。它不替代业务 gate，只回答“机器产物能不能被路由和审计”。
> Gate 策略矩阵已数据化在 `skills/n2d/_lib/gate_policy_matrix.json`：每个 gate stage 声明 family、人审边界、trace 策略和 required check groups；`n2d-review/scripts/gate.py` 读取该矩阵决定 preflight family，具体检查仍由现有 gate 函数执行。发布前 `gate_policy_coverage.py` 会把这些 check groups 映射到实现、测试和本集 release 证据，缺口 fail-closed。
> 发布证据链统一走 `generation_recipe_manifest.py` + `artifact_lineage.py` + `release_manifest.py`：每个最终 PNG/MP4 必须有 provider/model/channel/seed/prompt hash/reference hash/output hash 的生成配方记录；`release_manifest.py build --write` 会强制写/引用 `生产数据/artifact_lineage_第N集.json`，记录设置、进度、storyboard、prompt、图/视频/母带、event audit、artifact validation、gate policy coverage、生成配方、人工签收等 hash；`check` 会校验 lineage 文件存在且 hash 未漂移。
> 题材增强不写进核心状态机，走 `skills/n2d/references/genre_packs/*.json`：当前内置 `xianxia/xuanhuan/chuanyue/urban/suspense`，每个 pack 定义典型高风险场景、动作契约字段、QC 重点、风格绑定原则和降级方案。新增题材后跑 `python3 skills/n2d/scripts/genre_packs.py validate --all`。
> 高动态/大场景前置也收进编排器：到 `image_prompt` 前会自动跑源文覆盖、留存节拍、剧情完整性体检（选择→后果、动机向量、A/B/C 线程、前几集契约、假 cliffhanger、对白推进；写 `设定库/story_integrity_ledger.json`、`thread_scheduler.json`、`pilot_arc_contract.json`）、`spectacle_contract_audit.py`、`shot_risk_audit.py`，并写 `生产数据/spectacle_plan_第N集.*`、`spectacle_probe_pack_第N集.*`、`spectacle_sequence_plan_第N集.json` 与 `scene_layer_pack_plan_第N集.*`；到 `video_prompt`/`video` 前会在 router 之后补写 Motion Control manifest 骨架与 `trajectory_controller_plan_第N集.*`（本机有 MotionCtrl/CameraCtrl/DragNUWA 环境时作为增强路线，否则只留计划）；到 `compose` 前会写 `生产数据/action_edit_cues_第N集.*`；到 `review/验收` 前会写 `spectacle_video_qc_第N集.json`、`motion_reference_library.json`、`score_第N集.json`、`consistency_ledger_第N集.json`、`review_ui_第N集.*`、`contract_trace_第N集.*`、`mini_pilot_risk_第N集.*`、`audience_experience_第N集.*`、`failure_taxonomy_第N集.*` 与 `release_verdict_第N集.*`，让打斗 hit-stop、武技/法术撞点、突破雷击峰值、追逐 speed-ramp、腾云风声、大场景 scale reveal、关键帧覆盖、命中/峰值可读、剪辑/音效同步、成片高动态证据、观众体验、失败归因和发布裁决都进入闭环。`release_verdict` 还会强制校验最终母版存在、母版 SHA256、score/ledger/review-ui/生成配方证据晚于母版、字段级合规 verdict、发行 profile、pilot/mini-pilot、contract trace、stop-loss 与观众体验；`验收` 列只有这些证据通过并经人工显式签收后才回写 `✅`。
>
> **每集收尾自动包**：`run.py next <作品根> 第N集` 进入 `review/验收` 前沿时会自动跑以下确定性命令；任一 required 步失败会停在 `blocked_by_review_acceptance`，不会建议回写 `验收=✅`。手工排查时可单跑：
> ```bash
> python3 skills/n2d/progress.py audit-dag <作品根> --json
> python3 skills/n2d-script/scripts/production_breakdown.py <作品根> 第N集 check --json
> python3 skills/n2d/scripts/contract_trace.py <作品根> 第N集 --write
> python3 skills/n2d/scripts/pilot_risk_sampler.py <作品根> 第N集 --write --write-missing
> python3 skills/n2d/scripts/audience_experience.py <作品根> 第N集 --write
> python3 skills/n2d/scripts/failure_taxonomy.py <作品根> 第N集 --write
> python3 skills/n2d/scripts/release_verdict.py <作品根> 第N集 --profile demo|internal|cn_public|overseas|commercial --write
> ```
>
> **底层/手查：确定性路由脚本 `progress.py`**（编排器内部即调它解析前沿；容错或只想看前沿表时直接用，别靠 LLM 推 16×N 大表）：
> ```bash
> python3 <skill>/progress.py <作品根>          # 全局：最小未完成集 + 各阶段卡集数 + 推荐命令
> python3 <skill>/progress.py <作品根> 第N集    # 查指定集所处阶段 + 推荐命令
> ```
> 把脚本输出**直接讲给用户**。下面的"逐列判断"是脚本内部逻辑（容错/手查时参考）。
>
> **回写进度统一用脚本**（别手工编辑表格）：`python3 <skill>/progress.py set <作品根> 第N集 <列名> <值>`（值 = ✅ / ⬜ / ⏳rough / 12/19）。各阶段 skill 收尾都调它；`set` 会自动刷新 `脚本/第N集/manifest.json` 产物快照，并记录 `last_progress_state`。旧项目表头缺新列时先跑：`python3 <skill>/progress.py ensure-col <作品根> <列名> ⬜`。需要手动重建快照时可跑：`python3 skills/n2d/manifest.py <作品根> 第N集 --stage <stage_key>`。

> **先读 `制作模式`、`合成阶段` 与 `基础视觉风格`**。默认 `制作模式=混合自动路由`：阶段1后先运行 `voice_preflight.py prepare`，建立 `voice_casting.json` 与 `timing_estimate.json`，不生成 WAV；再由 `production_mode_router` 逐镜决定表演音轨先行、neutral-mouth base plate 后置口型、旁白/口外音后配、画面先行或 native AV。`配音=⏳rough` 表示时间基准就绪，不代表已有粗配音。最终音色定妆后才批量生成 final voice；成片前逐镜检查 final voice 与 lipsync 产物。`配音先行`、`原生音画`、`先出视频后配音` 只作用户显式项目级兼容模式。默认 `合成阶段=跳过`，所以基础 `视频` 列满仍只表示 `clip_delivery_complete`。
>
> 旧项目若曾把占位配音写成 `✅`，先跑 `python3 <skill>/progress.py audit-placeholders <作品根>`，确认后加 `--fix`。新项目不得再为填状态制造 say/静音 WAV。

1. 定位 `<作品根>/_进度.md`，读进度表（老项目若仍在 `<作品根>/common/_进度.md`，路由脚本会兼容读取）
2. 进度表头形如：`| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |`（`奇观连续性` 是信息态留痕列：✅=本集打斗/追逐/腾云/大场景已被序列总账覆盖，—=本集无奇观镜/不适用，na 不挡 flow；由 image_prompt prework 自动回写，旧项目缺列跑 `progress.py ensure-col <作品根> 奇观连续性 —`。`成片/验收` 是可选尾段列，默认不参与完成判定；旧项目缺 `验收` 列且已 `成片✅` 时，`run.py next` 会暴露审查验收前沿，先跑 `progress.py ensure-col <作品根> 验收 ⬜` 再签收。）
3. 对每一集逐列判断：
   - `剧本改编`/`bgm`/`封面` 任一 ⬜ → 还在 n2d-script 阶段1·剧本改编
   - 阶段1 齐、`配音` ⬜ → 运行 n2d-voice preflight（声音选角 + 无 WAV 时间基准）
   - 混合模式 `配音=⏳rough`、`分镜设计` ⬜ → 先确认 P-2 导演排戏包，再回跑阶段2；finalize 读取 `timing_estimate.json` 并把 provisional timing 写入 OTIO。项目级配音先行仍要求 `✅`，原生音画可选。
     - ⚠️ **时间基准检查**：校验 `timing_estimate.json.source_fingerprint` 与当前 voiceover 一致。旧 `占位:true` 只作兼容，不能冒充 final voice；新混合流程不要求它存在。
   - `分镜设计` ✅、`出图prompt`/`出图` 未满 → 先确认 P-3 制片拆解包，再进 n2d-image
   - `出图` 满、`视频` 未满 → 先确认 `生产数据/image_qc/<ep>/image_qc_<ep>.json` 存在、`qc_environment.precision_level=full` 且 `summary.hard_blocks=0`，再跑 `python3 skills/n2d-model-router/scripts/router.py <作品根> 第N集 --write` → n2d-video。缺报告、低精度或 hard block 都回 `n2d-image` / image_qc setup，不允许直接进视频。
   - `视频` 满、`合成阶段=跳过` 且本集未开始 `成片/验收` → `clip_delivery_complete`；如用户要母带/BGM/烧字幕/发布包，先设 `合成阶段=启用` 或直接运行 n2d-compose
   - `视频` 满、`合成阶段=启用` 或本集已开始 `成片/验收`、`成片` ⬜ → n2d-compose（剪辑合成+BGM+字幕；问用户 BGM 选项）
   - `成片` ✅、`验收` ⬜ → n2d-review 验收包（review gate + score + consistency ledger + review-ui）；证据通过后停在 `needs_acceptance_signoff`，人工确认后回写 `验收=✅`
   - **gate 前置（通用编排规则）**：路由到 image/video/compose 任一阶段时，正式生产入口统一跑 dashboard gate：正式生图前用 `--stage image_preflight`，正式出视频前用 `--stage video_preflight`，合成前用 `--stage compose`（仅合成尾段启用时；它会调用 `n2d-review/scripts/gate.py --json`，退出码 1 即先补再做，并把 QA 阻断入账）。`gate.py --json` 只作底层/调试入口。结构化输出会带 `return_to_stage` / `affected_artifacts` / `rerun_scope`，用于按最小范围回退返工。image_preflight 还会拦「storyboard.json 缺 visual_contract 视觉契约种子 / style_contract 基础视觉风格种子 / 本集总览缺契约」，把跨镜一致性和所选基础风格挡在花钱出图之前；生成后落档回验仍用 `--stage image` / `--stage video`。旧 `cinematic_contract` 兼容但新产物不再使用该标题。dashboard 的 `generation_pass_rate` 只表示生产尝试效率；对外验收和告警看 `deliverable_pass_rate` / `final_pass_rate`，存在 QA block 时可交付通过率归零。
   - **后端 smoke 证据（production / 付费 / batch 硬闸）**：候选刷新证明“今天查过 API/CLI 文档”，smoke 证明“本项目最近真实可运行”。production profile、`合规用途=paid_distribution`、`投放时效=隔夜批量/batch_24h` 或 `_设置.md` `后端Smoke硬闸: 是` 时，image/video gate 会要求默认 7 天内 fresh smoke（`N2D_BACKEND_SMOKE_MAX_AGE_DAYS` 可调）：`python3 skills/n2d/_lib/backend_smoke.py probe|record <作品根> --kind image|video --backend <后端> [--channel <渠道>]`。内部 demo 可用 `N2D_REQUIRE_BACKEND_SMOKE=0` 显式关闭；放量、多 worker 或付费批量前不要只靠文档刷新或无产物手录 pass。
   - **原生音画额外前置**：`制作模式=原生音画` 时，`出视频/第N集/prompt/00_总览.md` 必须写「原生音画物理一致性契约」，锁定声源归属、口型策略、材质/动作声、空间声学、字幕/后期策略；同时生成 `生产数据/native_av_physics_第N集.json`（kind=`n2d_native_av_physics`），逐 Clip 记录 `audio_intent`、`speaker_source`、`lip_sync`、`action_sounds[].visible_evidence/timing`、`spatial_acoustics`、`post_policy.compose_policy`。总览缺字段或 sidecar 缺机器字段都会 BLOCK。该契约是视频后端一次生成台词+口型时的音画物理护栏；成片后还必须补 `生产数据/native_av_subtitle_alignment_第N集.json`（kind=`n2d_native_av_subtitle_alignment`，词级对齐 SRT 证据），review/付费投放缺失会 BLOCK。
4. **推荐策略**：
   - 用户没指定集 → 找"最小未完成集编号" + 它所处的阶段，给出对应 skill 建议
   - 用户指定集 → 直接报该集所处阶段
5. **报告格式**：
   ```
   当前作品：<作品名>（共 N 集已拆分）
   最近完成：第K集 Stage 1 物料齐
   下一步建议：调 n2d-image <作品根> 第K集 生成出图 prompt + PNG
   可并行：n2d-script <作品根> 第K+1集 精修下一集物料（低成本前期，不影响第K集出图）
   ```

> **删减/改稿走源头回流（别手删产物）**：要删某镜/某句，用 `n2d-script/delete_shot.py <作品根> 第N集 镜头X`——它自动回流 voiceover/EN字幕/时长清单/voice 轨/finalize，并跑一遍 image gate 对账 storyboard.json（删句后接力/时长会失配）；删完按提示同步 storyboard.json 设计文档 + 移走已出 PNG/clip 到 `废料/`，再重跑 compose。绝不在成片 MP4 上直接剪（同源头回流铁律）。

### 跨阶段并行的 OK 信号

阶段不必严格串行——第 K 集出图时，第 K+1 集物料可以并行精修，第 K-1 集视频可以并行生成。**调度规则**：只要 `_进度.md` 该集对应列还是 ⬜ 就可以开干；不需要等前面集全部跑完。以后给用户“下一步”建议时，若存在安全的跨集/次要缺口，固定多写一条 `可并行：...`；优先推荐低成本前期，若并行项也会花钱/不可逆/触发合规，则必须单独确认。

## 作品目录约定

```
创作区/制漫剧/<剧名>/
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
│           └── 镜头N_end.png      可选尾锚（relay 时=下一 Clip 同一边界帧；否则仅作镜内控制）
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
        └── 成片_第N集_{mode}.mp4   ← n2d-compose 输出
```
> **出视频/ vs 合成/ 分家（2026）**：`出视频/第N集/` 只放 per-shot clips（`视频/`）+ 视频 prompt（`prompt/`）；一切音频/后期——`配音/`（含 `时长清单.json`）、`_voicecache/`、compose `_work/`、最终 `成片_*.mp4`——落同级 `合成/第N集/`。compose 从 `出视频/` 读 clips、从 `合成/` 读配音、把成片写回 `合成/`。

> **prompt/PNG/MP4 分离铁律**：每个 `出图/` 或 `出视频/` 文件夹（无论是 `共享/` 还是 `第N集/`）一律分两层——`prompt/` 子目录装所有 prompt md，**PNG 进 `图片/` 子目录**（与 `prompt/` 同级，含分镜首帧 + 尾帧 `镜头N_end.png`），**clip MP4 进 `出视频/第N集/视频/` 子目录**。详见 `references/architecture.md`「prompt / 产物分离铁律」。

> 旧仓库可能没有 `小说/` 子目录（原文直接在作品根）。仍能识别——作品根下 `.txt/.docx` 即为原文。

## 子 skill 速查

| skill | 何时调 | 输入 | 关键输出 |
|---|---|---|---|
| `n2d-script` | 阶段1 剧本改编(台词) / 阶段2 分镜设计(模式感知) | 小说路径 或 作品根 + 集号 | 阶段1: voiceover+bgm+封面；阶段2: 主干提炼 + Clip 时长权重 + 分镜剧本+故事板+素材清单+字幕 |
| `n2d-image` | 物料齐后出图 prompt + 生图 | 作品根 + 集号 | `出图/{共享,第N集}/` prompt + PNG + 进度勾 ✅ |
| `n2d-voice` | 阶段1齐后先建声音选角 + 无 WAV 时间基准；音色定妆后生成 guide/final 配音 | 作品根 + 集号 | `设定库/voice_casting.json` + `timing_estimate.json`（⏳rough，无音频）；获批后 `line_NN.wav` / `时长清单.json`（✅） |
| `n2d-identity` | 角色身份闭环：reference group / Face Lock / Character ID / LoRA adapter matrix + 跨集漂移报表 | 作品根 (+集号范围) | `生产数据/identity_adapter_matrix.json/md` + `identity_drift_report.json/md` |
| `n2d-lora` | 核心长线角色 LoRA 生命周期：数据集审计、训练任务、验证报告、registry ready 回写 | 作品根 + character_id + form | `设定库/lora/<CHAR_ID>/<形态>/` + 更新 `identity_registry.json` |
| `n2d-compliance` | 付费生成和投放前置：版权/改编权、角色授权、声音克隆、平台审核、出海本地化 | 作品根 (+集号) | `合规/compliance_manifest.json` |
| `n2d-model-router` | 出视频前按镜头类型/模板/身份/原生音画/时长选择视频后端 primary/fallback | 作品根 + 集号 | `出视频/第N集/prompt/video_model_routes.json/md` |
| `n2d-video` | 出图齐后出视频 prompt + 生视频，逐 Clip 继承模型路由表 | 作品根 + 集号 | `出视频/第N集/视频/` MP4（出视频唯一产物=clips）+ 进度勾 ✅ |
| `n2d-compose` | 可选尾段：视频齐后按用户启用的 `合成阶段` 合成成片 | 作品根 + 集号 | `合成/第N集/成片_第N集_{mode}.mp4` + 成片列 ✅ |
| `n2d-review` | 任意阶段闸门 / 出成片后质检；或流程自审找优化 | 作品根 (+集号) | 质检报告 `_质检_第N集.md` / 流程自审建议（跨阶段 QA，非必经） |
| `n2d-score` | 成片或阶段审查后给每集打机器分；含 visual checks；低分自动回流 | 作品根 + 集号 | `生产数据/score_第N集.json/md` + `score_inputs/第N集_visual.json` + `auto_return_tasks` / 可选 batch 队列 |
| `n2d-review-ui` | 机检/评分后生成人审无限画布，看首帧、尾帧、clip、接缝、定妆参考、QA flag、机器分 | 作品根 + 集号 | `生产数据/review_ui_第N集.html/json` |
| `n2d-feedback` | 上线一批后把平台留存/追更/跳出数据反哺导演节奏；同集 A/B 比较开场/封面/集尾断点/标题文案 | 作品根 + 平台指标 + 自动/手工导演标签 + 可选 A/B 变体字段 | `生产数据/platform_feedback.json/md` + 可选更新 `导演节奏.md` |

## 常见错误

| 错误 | 纠正 |
|---|---|
| 不查进度直接猜测用户的当前阶段 | 每开始一个会话，务必调用脚本或人工确认 `_进度.md` 的前沿在哪 |
| 跳过合规前置包 (n2d-compliance) | 后续的任何 image/video 生成都会因为 gate 被拦截，造成多次碰壁 |
| 用户说“后配音”就把整项目切成 `先出视频后配音` | 默认仍用混合自动路由：旁白/口外音/动作镜自然后配；只有用户明确要求整集全部画面先行才切项目级模式 |
| 源文件更新后不检查漫剧侧的过期漂移 | 应依赖于源新鲜度自检及 `update_plan` 判断，重切必要的窗口，以免文本与生产资产脱节 |

## 实战参考

- 详细架构、目录铁律、首跑示范：`references/architecture.md`
- 翻车 + 修正 + 决策案例（20+ Q&A）：`Q&A.md`
- **导演节奏 / 留存工程（全阶段共用）**：`references/导演节奏.md` —— 留存曲线/黄金3秒/钩子密度/爽点憋放/集尾cliffhanger/镜头时长曲线/卡点/念白节奏。这是红果爆款"画质普通但留人"那一层，n2d-script/voice/video/compose 都引用。
- **传统导演排戏 / P-2 方法论**：`../../docs/n2d-传统短剧导演排戏流程.md` —— 专业导演拿到剧本后的排戏、调度、运镜、镜头衔接和竖屏短剧落地；解释 `director_blocking_pack.py` 为什么在分镜前阻断。
- **传统短剧制作全流程 / P-1~P-3 落地方案**：`../../docs/n2d-传统短剧制作全流程落地方案.md` —— 从小说开发、编剧改编、导演排戏、制片拆解、AI 拍摄到后期验收的完整剧组化流程；解释 `production_breakdown.py` 为什么在出图 prompt 前阻断。
- **模型矩阵（各阶段 SOTA/默认/升级触发，全阶段共用档案）**：`references/模型矩阵.md` —— 配音/图/视频后端的当前梯队与"何时该 opt-in 升级"，n2d-voice/image/video 的"知情提示"都以它为准。
- 镜头空间语法：`n2d-script/references/分镜语法.md`
- 平台档案 / prompt 格式：在各阶段 skill 的 `references/` 下
