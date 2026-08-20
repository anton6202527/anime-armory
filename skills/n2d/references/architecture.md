# n2d 主状态机 — 架构与目录约定（时间基准先行 / 逐镜混合音画路由）

本文档是调度器 `n2d` 的扩展参考。说清楚整个 pipeline 是怎么组织的，子 skill 如何协作，目录铁律，以及 first-time 的标准首跑示范。

---

## 一、为什么拆成多个 skill

早期调度 skill 在 100+ 集制作期间膨胀到："拆集 + 物料 + 出图 prompt + 出图操作 + 视频" 全揉一起，导致：

- 任一集只在某一阶段时，无关阶段细节也塞进上下文
- 不同生成轴（生图模型 / 生图渠道 / 生视频模型 / 生视频渠道）的差异散布在多处
- 经验沉淀（Q&A）越累越多，单文件难翻

拆分后每阶段一个 skill，调度器只路由、按需加载。**完整流水线用同一张 `_进度.md`，但实际顺序由 `制作模式` 决定**：

| 阶段 | Skill | 关注点 | 不关注 |
|---|---|---|---|
| 调度 | `n2d` | 路由 + 全局架构 | 任何具体生产细节 |
| ①剧本改编 | `n2d-script`(阶段1) | 拆集 + 台词/bgm/封面 + 角色/场景卡 + global_style + table read 围读包 | 分镜 / AI CLI 调用 |
| ②声音前期/最终配音 | `n2d-voice` | 默认先建 voice casting + 无 WAV timing；音色获批后生成 final voice；按需提供可信 guide/performance 轨 | 分镜 / 出图 |
| ③分镜设计 | `n2d-script`(阶段2) | 按逐镜 timing basis 定稿分镜/故事板/素材/SRT；默认读 no-audio timing，final voice 到位后刷新实测时长；出图前补 executable animatic、P-3 制片拆解和 batch seed | 出图细节 |
| ④出图 | `n2d-image` | 两层出图 prompt（定妆库+本集分镜）+ 扫 CLI + 生图 | 视频 prompt |
| ⑤视频 | `n2d-video` | 视频 prompt + 扫 CLI + 生视频 / 指导；默认 `clip_delivery_complete` 边界 | 物料模板 |
| ⑥合成（可选） | `n2d-compose` | 用户启用 `合成阶段` 后，FFmpeg 脚本化剪辑 + BGM + 烧字幕 → 成片 | prompt 设计 |

> **两个非显然的顺序决定**：① 默认前移的是“声音选角 + 时间基准”，不是整集最终配音。逐镜 route 决定表演音轨先行、基础视频后置口型、旁白后配、画面先行或原生音画。② 出图分两层（先共享定妆库锁脸/场景/画风，再本集分镜，保跨镜一致）。

---

## 二、目录铁律

### 作品根

每个作品独占一个目录：

```
创作区/制漫剧/<剧名>/
├── 小说/                  原文
├── _进度.md               全作品进度表
├── 设定库/                世界观、角色圣经、场景语义与规则真值
├── 角色库/                本作品分档角色生产资产包
├── 废料/                  废料归档
├── 脚本/                  n2d-script 产物
├── 出图/                  n2d-image 产物
└── 出视频/                n2d-video 产物
```

`<剧名>` 用中文是 OK 的（macOS/Linux 路径支持）。

### 共享 vs 本集

**铁律**：**全篇复用的资产放共享层，仅本集出现的放本集层**。1 skill = 1 顶层文件夹，里面再按"common / 第N集"拆。

```
作品根/
├── _进度.md                              全作品进度表
├── 设定库/                               跨阶段语义设定真值（不放角色生产包）
│   ├── global_style.md                   全局画风/世界观/目标AI（仅 1 份）
│   ├── characters/                       角色设定（一角色一文件）
│   ├── locations/                        场景设定
│   └── voicebank/                        音色引用/音色库
├── 角色库/                               角色可迁移生产包（替代旧 `设定库/character_assets/`）
│   ├── README.md                         分档与导出规则
│   └── <CHAR_ID>__<slug>/                reference/prompts/lora/voice/adapters/qc + manifest.json
├── 生产数据/                             机器证据 / gate / 队列 / 锁版账本
│   ├── artifact_catalog.json             可重建只读索引（不是 gate / 业务真值）
│   ├── timelines/第N集/                  持久 editorial / animatic OTIO + lock timeline
│   ├── views/                            从 JSON/JSONL 派生的人读 Markdown / HTML
│   ├── cache_manifests/                  _work / _clipcache 可清理性与保留策略
│   ├── video_qc/第N集/_frames/           按源媒体版本去重的 QC 抽帧
│   ├── animatic_第N集.json / animatic_第N集.html
│   ├── ai_shooting_schedule_batch_seed_第N集.json / .md
│   ├── final_timeline_probe_第N集.json
│   ├── script_supervisor_log_第N集.jsonl / script_supervisor_log_第N集_summary.json
│   └── creative_decision_log.jsonl        重大变更/豁免/降级的生产决策账
├── 废料/                                 废料归档（4 选 1 / 废图 / 废视频）
├── 脚本/                                 ← n2d-script（①剧本改编 + ③分镜设计）
│   └── 第N集/
│       ├── raw.txt                       拆集出来的原文片段
│       ├── voiceover.txt / bgm.txt / 封面.md   ①剧本改编产物
│       ├── table_read_packet.json / table_read_packet.md  ①后围读验收包
│       ├── 分镜剧本.md / 故事板.md / 素材清单.md  ③分镜设计产物（配音后回跑）
│       ├── animatic_packet.json / animatic_packet.md       ③后粗剪签收包（timed 预览落 生产数据/）
│       ├── production_breakdown.json / continuity_breakdown.json / continuity_bible.json
│       ├── ai_shooting_schedule.json / ai_call_sheet.md    P-3 制片/场记/排期/通告
│       ├── 字幕_中文.srt / 字幕_英文.srt（英文仅海外/中英双语时生成）
│       └── 镜头时长.json                 ③定稿锁定的逐镜头时长（驱动 Clip 长）
├── 合成/第N集/配音/                       ← n2d-voice（②配音）：line_NN.wav + voice_zh.wav + 时长清单.json（落「合成」层，不在出视频）
├── 出图/                                 ← n2d-image（④出图）
│   ├── 共享/                             全篇定妆库（旧项目 common/ 读取兼容）
│   │   ├── prompt/                       共享 prompt 文件
│   │   │   ├── 00_索引.md                全篇定妆清单 + 状态
│   │   │   └── 角色定妆.md / 场景定妆.md / 道具定妆.md（+ ⚙️法宝定妆.md / 特效定妆.md·仙侠玄幻可选）
│   │   └── 图片/                         共享 PNG 产物（与 prompt/ 同级子目录）
│   │       └── 定妆_*.png                角色/场景/道具定妆 PNG（人物按角色库档位生成所需角度，不一刀切全套）
│   └── 第N集/                            本集分镜
│       ├── prompt/                       本集 prompt 文件
│       │   ├── 00_总览.md                本集图清单 + 引用共享 + 本集视觉一致性契约 + 本集基础视觉风格契约（继承 storyboard.json visual/style contract）
│       │   └── 01_分镜出图.md            本集分镜 prompt
│       └── 图片/                         本集 PNG 产物（与 prompt/ 同级子目录）
│           ├── 镜头N_*.png               本集分镜首帧 PNG
│           └── 镜头N_end.png             可选尾锚（relay 时为下一 Clip 同一边界帧；否则只作镜内控制）
├── 出视频/                               ← n2d-video（⑤视频）：唯一产物=各镜头 clips
│   ├── 共享/                             （如有跨集复用片段，如转场/空镜；旧项目 common/ 读取兼容）
│   │   ├── prompt/
│   │   └── *.mp4
│   └── 第N集/
│       ├── prompt/                       本集 prompt 文件
│       │   ├── 00_总览.md                本集 Clip 清单
│       │   └── 01_clips.md               每 Clip 视频 prompt
│       └── 视频/                         ClipK_*.mp4 定稿片段（供 n2d-compose 归集）
└── 合成/                                 ← n2d-voice 配音轨 + n2d-compose（⑥合成）同住此层
    └── 第N集/
        ├── 配音/                         ← n2d-voice 产物（line_NN.wav / voice_zh.wav / 时长清单.json）
        ├── _voicecache/                  配音缓存
        ├── _work/                        compose 可重建中间件（不放持久证据）
        ├── _clipcache/                   clip 处理缓存（不放正式 Clip）
        └── 成片_第N集_<mode>.mp4         ← n2d-compose 最终成片
```

### prompt / 产物分离铁律（n2d-image / n2d-video 通用）

每个 `出图/` 或 `出视频/` 文件夹（`共享/` 或 `第N集/`；旧项目 `common/` 仅读取兼容）一律分两层：

- **`prompt/` 子目录** 装该文件夹所有 prompt md（共享层的 00_索引 + 角色/场景/道具定妆，或本集的 00_总览 + 01_分镜/clips）
- **生成产物**：PNG 进 **`图片/` 子目录**（与 `prompt/` 同级；含分镜首帧 `镜头N_*.png` + 按契约生成的可选尾锚 `镜头N_end.png`，共享层为 `图片/定妆_*.png`）；**clip MP4 进 `出视频/第N集/视频/` 子目录**；**配音 / 成片产物落 `合成/第N集/`**

好处：
- 一目了然——浏览父目录只看到产物缩略图，找 prompt 进 `prompt/` 子目录
- 打包分享方便——单独打 `prompt/` 给文案审稿，单独打父目录给视觉审稿
- 4 个层级（出图/共享, 出图/第N集, 出视频/共享, 出视频/第N集）规则一致，跨 skill 心智零负担

> `设定库/` 是语义真值，`角色库/` 是角色生产包，`出图/共享/` 是项目内执行引用层；三者职责不同，不能互相替代。旧 `设定库/character_assets/` 迁到作品根 `角色库/` 后必须删除旧目录，不能长期双写。

### 作品、系列与跨系列的三层资产边界

1. **作品内**：角色包在 `<作品根>/角色库/`；场景/道具/武器/服装/VFX 在 `出图/共享/asset_registry.json` + `出图/共享/图片/`。
2. **制漫剧系列内**：稳定、审过、授权清楚且值得复用的资产，显式导出到 `创作区/制漫剧/_资产库/<type>/<slug>/asset_pack.json`。同系列新作品导入的是包副本，不回指源作品。
3. **跨系列 / 跨仓库 / 跨机器**：只交付所需的单个自包含 pack；`files[]` 与 SHA256 都留在包内，`portability.requires_source_library=false`。目标系列自行适配通用字段，不 import n2d 实现，也不要求携带整个 `_资产库/`。

其它五条生产线各有自己的 `_资产库/`。仓库根不再设置共享 `资产库/`。

**判定表**：

| 资产 | 放哪 | 理由 |
|---|---|---|
| 角色定妆（含形态变体） | 共享 | 跨集复用 |
| 场景定妆 | 共享 | 多集复用 |
| 反复入镜道具 / HUD 光幕 | 共享 | 全集统一视觉 |
| ⚙️法宝 / 法器（仙侠玄幻）| 共享 | 跨集复用，按形态/成长阶段出多态 |
| ⚙️特效 / VFX（剑气/灵力/法术/护体光/阵法）| 共享 | 高频复现且会漂，锁颜色/形状/拖尾/强度 |
| 死亡 / 仅本集形态 | **仍共享** | 规则统一 > 节省 3MB |
| 一次性道具 | 本集 | 不复用 |
| 分镜出图（首帧 `镜头N_*.png`）| 本集 | 一镜一图 |
| 可选尾锚（`镜头N_end.png`）| 本集 | relay 时焊接同一边界帧；其他模式只控制本镜落幅，不要求等于下一首帧 |
| 封面 | 本集 | 一集一封 |
| 视频片段 | 本集 | 一镜一段 |

### 废料

```
废料/
├── 出图/
│   ├── 共享/                         共享层定妆筛选 4 选 1 / 废图
│   └── 第N集/                        本集分镜筛选 4 选 1 / 废图
└── 出视频/
    └── 第N集/                        废视频片段
```

**不要**留在 Downloads，不要散落作品根。

---

## 三、机器契约与进度表（_进度.md）协议

机器契约真值源在 `skills/n2d/_lib/n2d_contract.py`，人读版见 `references/contract.md`。阶段图、列名、gate stage、manifest 路径、回退目标都从这里派生；`n2d/_lib/n2d_route.py`、`n2d/progress.py`、`n2d-progress/scan.py`、`n2d-review/scripts/gate.py` 不应各自维护一张阶段表。

进度表是主状态机所有 skill 的 **single source of truth**。**表头由 `skills/n2d/_lib/n2d_contract.py` 定义，`n2d-script/scripts/split_novel.py` 生成时读取它**——本文与调度器 SKILL 只复述、不另立一套。当前 18 列格式：

```markdown
# <剧名> — 生产进度

共拆分 **N** 集。

| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 第1集 | 2388 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | 4/19 | ✅ | 0/12 | ⬜ | ⬜ |
```

> **回写一律走脚本**：`python3 <skill>/progress.py set <作品根> 第N集 <列名> <值>`；旧项目缺新列先 `progress.py ensure-col`。别手工编辑表格（避免列错位）。
> **每集产物快照**：`progress.py set` 回写进度时会自动刷新 `脚本/第N集/manifest.json`，记录 schema 版本、制作模式、阶段产物路径、存在性和文件 hash，供 review 与最小返工范围使用。需要手动重建时可跑 `python3 skills/n2d/manifest.py <作品根> 第N集 [--stage stage_key]`。

**列含义**：

| 列组 | 写入者 | 含义 |
|---|---|---|
| raw | n2d-script 拆集脚本 | 原文片段已落档（展示用，不计入流程完成判定） |
| 剧本改编 / bgm / 封面 | n2d-script 阶段1 | 配音前的剧本改编（台词/BGM 设计/封面）完毕 |
| 配音 | n2d-voice | `⏳rough`=声音选角/无 WAV 时间基准已建立；`✅`=所需 final voice 已真实生成。逐镜口型完成度另由 route + lipsync 产物检查，不能只看本格 |
| 分镜设计 / 素材清单 / 字幕中 / 字幕英 | n2d-script 阶段2 | 按逐镜 timing basis 定稿分镜/故事板/素材/SRT；可先读 `timing_estimate.json`，final voice 后刷新实测时长，native AV 读脚本/对齐结果 |
| 出图prompt | n2d-image | 本集出图 prompt **全套**写完（共享定妆库 + 本集分镜） |
| 出图 | n2d-image | `已完成 PNG / 本集需要的总数`（分子含共享复用 + 本集分镜） |
| 视频prompt / 视频 | n2d-video | prompt 写完 ✅；`视频` = `已完成 MP4 / 本集 Clip 总数`；默认到这里是 `clip_delivery_complete`，不是可发布母版 |
| 成片 | n2d-compose | 默认交付尾段：剪辑合成 + BGM + 烧字幕 → 成片完成；只有显式跳过才停在 clip |
| 验收 | n2d-review | 默认最终尾段：review gate + score + consistency ledger + review-ui + release/readiness + production locks + creative governance 全部通过，并经人工显式签收 |

**调度规则**：任一必经列为 ⬜ 时，对应 skill 可以接手该集；列已 ✅ 时，下游 skill 才能继续。`成片/验收` 只有在 `_设置.md` 写 `合成阶段: 启用`，或本集已经开始这两个列时才参与路由。完整逐列路由判断见调度器 `SKILL.md`。

---

## 四、四项架构（生图模型 / 生图渠道 / 生视频模型 / 生视频渠道）

视频阶段拆成路由策略与执行偏好：`视频模型路由` 默认 `自动按镜头路由`；`生视频模型`（Seedance 2.0 / Veo 3.1 / Kling 3.0 / Hailuo 02/2.3 / Runway Gen-4 / Luma Ray3.2 / Pika 2.5 / HunyuanVideo 1.5 / Wan 2.2 / LTX-2.3 / manual）只作普通镜/兜底或固定模式目标；`生视频渠道`（即梦/Dreamina / 豆包 / 海螺AI / 可灵/Kling / Google Gemini API / Runway API / 本地开源 / manual）只作调用入口偏好。**新作品首跑不问具体模型/渠道**；只有固定模式、账号/交付约束、用户明说，或 n2d-video 阶段 router/probe 找不到可执行后端时，才在出视频前问并落档。图片阶段按 `生图模型 + 生图AI/生图渠道` 选择点统一到一个官方/已登录组合（默认 OpenAI GPT Image 系列 via Codex）。全项目生图优先 Codex/OpenAI；Dreamina/即梦官方 CLI、官方多参考/主体后端等非 Codex/OpenAI 后端必须先有用户签核例外；正式生图前扫描本机/当前会话可用后端时，不得因为视频阶段走即梦而自动切图片后端。禁止第三方逆向、`同视频AI` / `同视频模型` 含糊口径和 web 自动化出图。

```
生图模型 → 生图渠道 → 图片 → 生视频模型（运动估计/风格基线） → 生视频渠道（调用入口）
   ↑          ↑                         ↑                         ↑
决定画面能力  决定 CLI/API/产品入口       决定图片要能被谁消化        决定 CLI/API/网页
```

- **当前默认**：生图组合 = `生图模型 + 生图AI/生图渠道` 所选官方/已登录组合（默认 OpenAI GPT Image 系列 via Codex）。若正式生图前扫到多个可自动落 PNG 的渠道，默认仍推荐 Codex/OpenAI；非 Codex/OpenAI 只有用户签核后才写回选择。视频阶段默认 `视频模型路由=自动按镜头路由`。未固定后端时，具体生视频模型/渠道延后到 n2d-video；`_设置.md` 的 `生视频模型/生视频渠道` 只作固定模式、普通镜兜底或调用入口偏好。即使视频渠道=即梦，也不能把图片阶段写成含糊的 `同视频AI` 或 `同视频模型`。
- **跨模型桥接**：生图模型/渠道与最终生视频模型不一定同厂。已固定生视频模型时，image prompt 末尾拼该模型的"图像风格锚定句"；未固定时用通用视频兼容锚定，n2d-video 路由只能选能消化现有首帧的后端。若用户临时固定不兼容后端，必须提示重出图/重拼锚定或改路由。

**记录位置**：`global_style.md` 顶部记三行：
```
视频模型路由：<默认自动按镜头路由；固定模式才锁单模型>
生视频后端决策：<默认延后到 n2d-video；自动模式逐 Clip 见 video_model_routes>
目标视频模型：<固定模式或 n2d-video 路由后才落定；自动模式仅普通镜/兜底>
生视频渠道：<固定模式或 n2d-video 路由后才落定；自动模式仅调用入口偏好>
生图模型：OpenAI GPT Image 系列
生图渠道：Codex   ← 默认；非 Codex/OpenAI 官方图后端需用户签核例外
```

详细档案见 `n2d-image/references/platforms.md` 和 `n2d-video/references/platforms.md`。

---

## 五、首跑示范（拿到小说第一次）

```
用户：把这个小说改成漫剧素材：/Users/me/works/我的小说.docx

调度（n2d）→ 识别"情境 A 首跑"：
  先给「制作模式」菜单选一次：
    A 混合自动路由（默认）/ B 配音先行 / C 原生音画 / D 先出视频后配音
    → 用户选后落 _设置.md。下面按默认 A 走；逐集 router 写可执行的逐镜声音合同。
  不询问具体生视频模型/渠道；后端选择延后到 n2d-video 出视频前。
  推荐：调 n2d-script "/Users/me/works/我的小说.docx"
  说明：会先拆集，然后精修第1集

用户：跑 n2d-script

n2d-script（阶段1·剧本改编）→
  1. 把小说挪到 创作区/制漫剧/我的小说/小说/
  2. 跑 split_novel.py → 生成 创作区/制漫剧/我的小说/{_进度.md, 设定库/{global_style.md, characters/, locations/}, 脚本/第N集/raw.txt}
  3. 在 _进度.md 写入 N 集骨架（raw 列 ✅，其他全 ⬜）
  4. 精修 设定库/global_style.md + 设定库/characters/ + 设定库/locations/
  5. 精修第1集 阶段1剧本(台词+bgm+封面) → 剧本改编/bgm/封面列 ✅（**此阶段不做分镜**）
  6. 报告：第1集剧本齐；默认先跑 n2d-voice preflight，生成选角表与无 WAV 时间基准，再回阶段2分镜

用户：跑 n2d-voice 创作区/制漫剧/我的小说 第1集

n2d-voice →
  1. `voice_preflight.py prepare` 解析 voiceover.txt，落 `设定库/voice_casting.json` + `合成/第1集/配音/timing_estimate.json`
  2. 不生成 WAV；配音列写 `⏳rough`，表示时间基准已建立
  3. 少量试听锁定角色声音；最终音色获批后才跑 render_voice，落 line WAV / voice_zh.wav / 实测时长清单并写 `✅`

用户：跑 n2d-script 第1集（阶段2·分镜设计，配音后回跑）

n2d-script（阶段2）→
  1. 跑 finalize_storyboard.py → 用实测时长定 分镜剧本 + 故事板(Clip时长) + 镜头时长.json
  2. 产 素材清单 + 字幕_中文.srt（默认中文-only；海外才加 字幕_英文.srt）
  3. 分镜设计/素材清单/字幕中 列 ✅
  4. 确认 animatic_packet + timed animatic + P-3 交接包 → 可导入 batch seed 或直接调 n2d-image

用户：跑 n2d-image 创作区/制漫剧/我的小说 第1集

n2d-image →
  1. 走"强制 5 步 SOP"：扫共享 → 列需求 → 差集 → 追加共享定妆 → 建本集 prompt
  2. 写完 → 出图prompt 列 ✅
  3. 扫描可用生图后端：多个可用则让用户选一个，零可用则停；再按 _设置.md 的 生图AI 生图
  4. 出 PNG → 用户筛 → 落档 出图/{共享,第N集}/ → 出图列填 K/N
  5. 全部生成 → 出图列 K/K → 报告可调 n2d-video

用户：跑 n2d-video ... → 默认到 clip_delivery_complete；如需母带/BGM/字幕/发布包，再启用 n2d-compose（成片落 合成/第1集/）并走 review/readiness
```

---

## 六、调度脚本意图（不实现，写给读者）

调度本身**不需要复杂逻辑**——核心就是读 `_进度.md` 找最小未完成集 + 最早未完成列，然后人话报告"调哪个 skill 处理哪一集"。

伪代码：

```
def dispatch(work_root):
    progress = read(f"{work_root}/_进度.md")
    mode = read_setting(work_root, "制作模式", default="混合自动路由")
    compose_enabled = read_setting(work_root, "合成阶段", default="启用") == "启用"
    for episode in episodes_sorted_by_number(progress):
        compose_tail = compose_enabled or any_started(episode, ["成片", "验收"])
        if any(episode[c] != "✅" for c in ["剧本改编", "bgm", "封面"]):
            return ("n2d-script(阶段1)", episode.id, "剧本改编未齐")
        if mode == "混合自动路由" and episode["配音"] == "⬜":
            return ("n2d-voice(preflight)", episode.id, "缺声音选角/无 WAV 时间基准")
        if mode == "配音先行" and episode["配音"] != "✅":
            return ("n2d-voice(final)", episode.id, "强配音先行模式尚无最终配音")
        if episode["分镜设计"] != "✅":   # 实际路由只闸 分镜设计；素材清单/字幕中是阶段2 副产物、字幕英仅海外投放才出，均不阻塞路由（与 progress.py STAGES 一致）
            return ("n2d-script(阶段2)", episode.id, "分镜设计未齐（配音后回跑）")
        if episode["出图prompt"] != "✅" or not all_done(episode["出图"]):  # "4/19" 形式
            return ("n2d-image", episode.id, "出图未完")
        if episode["视频prompt"] != "✅" or not all_done(episode["视频"]):
            return ("n2d-video", episode.id, "视频未完")
        if compose_tail and route_requires_final_voice(episode) and episode["配音"] != "✅":
            return ("n2d-voice(final)", episode.id, "成片所需最终声音未齐")
        if compose_tail and route_requires_post_lipsync(episode) and not lipsync_done(episode):
            return ("n2d-video(lipsync pass)", episode.id, "可见口型镜头后期表演未齐")
        if compose_tail and episode["成片"] != "✅":
            return ("n2d-compose", episode.id, "未合成")
        if compose_tail and episode["验收"] != "✅":
            return ("n2d-review", episode.id, "未验收")
    return (None, None, "全集 clip_delivery_complete（若启用合成尾段且验收通过，则为 master_delivery_complete）")
```

> 实际不需要另写脚本——机读路由用 `n2d/progress.py`，它经 `n2d/_lib/n2d_route.py` 复用 `n2d_contract.STAGE_GRAPH`，再消费逐镜 production route。混合模式的 no-audio timing 放行、成片前 final voice 回补、base plate 的 lipsync pass、原生音画的配音可选层都在同一套路由里生效。

---

## 七、配音 / 分镜 / 合成阶段（均已实现）

主状态机已全部落地：默认先跑声音 preflight，再由逐镜 route 决定音画先后；项目级 `配音先行` / `原生音画` / `先出视频后配音` 只作显式兼容模式。`视频` 列完成只表示基础 clip 交付；若 route 要求 final voice 或后期口型，这些条件满足后才可进入成片签收。只有用户启用 `合成阶段` 或本集已开始 `成片/验收` 时，才进入完整母版尾段和人工签收。
