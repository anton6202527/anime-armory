# 六阶段流水线 — 架构与目录约定（剧本改编→配音→分镜设计→出图→视频→合成）

本文档是调度器 `n2d` 的扩展参考。说清楚整个 pipeline 是怎么组织的，子 skill 如何协作，目录铁律，以及 first-time 的标准首跑示范。

---

## 一、为什么拆成多个 skill

早期调度 skill 在 100+ 集制作期间膨胀到："拆集 + 物料 + 出图 prompt + 出图操作 + 视频" 全揉一起，导致：

- 任一集只在某一阶段时，无关阶段细节也塞进上下文
- 不同 AI 工具（图 AI / 生视频模型 / 生视频渠道）的差异散布在多处
- 经验沉淀（Q&A）越累越多，单文件难翻

拆分后每阶段一个 skill，调度器只路由、按需加载。**完整六阶段**（顺序见下文，注意配音前移、分镜在配音之后）：

| 阶段 | Skill | 关注点 | 不关注 |
|---|---|---|---|
| 调度 | `n2d` | 路由 + 全局架构 | 任何具体生产细节 |
| ①剧本改编 | `n2d-script`(阶段1) | 拆集 + 台词/bgm/封面 + 角色/场景卡 + global_style | 分镜 / AI CLI 调用 |
| ②配音 | `n2d-voice` | 逐句 AI 配音 + 时长清单.json（实测时长驱动镜头） | 分镜 / 出图 |
| ③分镜设计 | `n2d-script`(阶段2) | 用配音时长设计分镜剧本/故事板/素材清单/SRT | 出图细节 |
| ④出图 | `n2d-image` | 两层出图 prompt（定妆库+本集分镜）+ 扫 CLI + 生图 | 视频 prompt |
| ⑤视频 | `n2d-video` | 视频 prompt + 扫 CLI + 生视频 / 指导 | 物料模板 |
| ⑥合成 | `n2d-compose` | FFmpeg 脚本化剪辑 + BGM + 烧字幕 → 成片 | prompt 设计 |

> **两个非显然的顺序决定**：配音前移到分镜之前（`n2d-voice` 产的逐句实测时长驱动镜头时长，故 `n2d-script` 跑两遍）；出图分两层（先共享定妆库锁脸/场景/画风，再本集分镜，保跨镜一致）。

---

## 二、目录铁律

### 作品根

每个作品独占一个目录：

```
制漫剧/<剧名>/
├── 小说/                  原文
├── _进度.md               全作品进度表
├── 设定库/                跨阶段设定资产
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
├── 设定库/                               跨阶段设定资产
│   ├── global_style.md                   全局画风/世界观/目标AI（仅 1 份）
│   ├── characters/                       角色设定（一角色一文件）
│   ├── locations/                        场景设定
│   └── voicebank/                        音色引用/音色库
├── 废料/                                 废料归档（4 选 1 / 废图 / 废视频）
├── 脚本/                                 ← n2d-script（①剧本改编 + ③分镜设计）
│   └── 第N集/
│       ├── raw.txt                       拆集出来的原文片段
│       ├── voiceover.txt / bgm.txt / 封面.md   ①剧本改编产物
│       ├── 分镜剧本.md / 故事板.md / 素材清单.md  ③分镜设计产物（配音后回跑）
│       ├── 字幕_中文.srt / 字幕_英文.srt（英文仅海外/中英双语时生成）
│       └── 镜头时长.json                 ③定稿锁定的逐镜头时长（驱动 Clip 长）
├── 合成/第N集/配音/                       ← n2d-voice（②配音）：line_NN.wav + voice_zh.wav + 时长清单.json（落「合成」层，不在出视频）
├── 出图/                                 ← n2d-image（④出图）
│   ├── 共享/                             全篇定妆库（旧项目 common/ 读取兼容）
│   │   ├── prompt/                       共享 prompt 文件
│   │   │   ├── 00_索引.md                全篇定妆清单 + 状态
│   │   │   └── 角色定妆.md / 场景定妆.md / 道具定妆.md（+ ⚙️法宝定妆.md / 特效定妆.md·仙侠玄幻可选）
│   │   └── 图片/                         共享 PNG 产物（与 prompt/ 同级子目录）
│   │       └── 定妆_*.png                角色/场景/道具 定妆 PNG（人物含正/侧/背标准三视图 + _三视图拼版 + _半身/_全身服装参考）
│   └── 第N集/                            本集分镜
│       ├── prompt/                       本集 prompt 文件
│       │   ├── 00_总览.md                本集图清单 + 引用共享 + 本集视觉一致性契约 + 本集基础视觉风格契约（继承 storyboard.json visual/style contract）
│       │   └── 01_分镜出图.md            本集分镜 prompt
│       └── 图片/                         本集 PNG 产物（与 prompt/ 同级子目录）
│           ├── 镜头N_*.png               本集分镜首帧 PNG
│           └── 镜头N_end.png             尾帧接力 PNG（=下一 Clip 首帧构图，供 n2d-video 首尾双帧锁接点）
├── 出视频/                               ← n2d-video（⑤视频）：唯一产物=各镜头 clips
│   ├── 共享/                             （如有跨集复用片段，如转场/空镜；旧项目 common/ 读取兼容）
│   │   ├── prompt/
│   │   └── *.mp4
│   └── 第N集/
│       ├── prompt/                       本集 prompt 文件
│       │   ├── 00_总览.md                本集 Clip 清单
│       │   └── 01_clips.md               每 Clip 视频 prompt
│       └── 视频/                         ClipK_*.mp4 定稿片段（供 n2d-compose 归集）
└── 合成/                                 ← n2d-voice 配音轨 + n2d-compose（⑥合成）+ 可选水印同住此层
    └── 第N集/
        ├── 配音/                         ← n2d-voice 产物（line_NN.wav / voice_zh.wav / 时长清单.json）
        ├── _voicecache/                  配音缓存
        ├── _work/                        compose 中间件（每次重建）
        ├── 成片_第N集_<mode>.mp4         ← n2d-compose 最终成片
        └── 成片_第N集_<mode>_水印.mp4    ← （可选）本线 n2d-watermark skill 打 AI合规/品牌水印后产物
```

### prompt / 产物分离铁律（n2d-image / n2d-video 通用）

每个 `出图/` 或 `出视频/` 文件夹（`共享/` 或 `第N集/`；旧项目 `common/` 仅读取兼容）一律分两层：

- **`prompt/` 子目录** 装该文件夹所有 prompt md（共享层的 00_索引 + 角色/场景/道具定妆，或本集的 00_总览 + 01_分镜/clips）
- **生成产物**：PNG 进 **`图片/` 子目录**（与 `prompt/` 同级；含分镜首帧 `镜头N_*.png` + 尾帧接力 `镜头N_end.png`，共享层为 `图片/定妆_*.png`）；**clip MP4 进 `出视频/第N集/视频/` 子目录**（出视频阶段唯一产物，供 n2d-compose 归集）；**配音 / 成片 / 水印产物落 `合成/第N集/`**（不在出视频层）

好处：
- 一目了然——浏览父目录只看到产物缩略图，找 prompt 进 `prompt/` 子目录
- 打包分享方便——单独打 `prompt/` 给文案审稿，单独打父目录给视觉审稿
- 4 个层级（出图/共享, 出图/第N集, 出视频/共享, 出视频/第N集）规则一致，跨 skill 心智零负担

> 作品根的跨阶段设定统一放 `设定库/`，全局进度放作品根 `_进度.md`，废料放作品根 `废料/`；`出图/共享/图片/` 与 `出视频/共享/` 仍是 stage 内的全篇定妆/转场库。语义不同——前者是"跨技能共用设定"，后者是"该技能内跨集复用"。路径互不重叠。

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
| 尾帧接力（`镜头N_end.png`）| 本集 | 接缝焊接=下一 Clip 首帧构图，供 n2d-video 首尾双帧锁接点 |
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

机器契约真值源在 `skills/common/n2d_contract.py`，人读版见 `references/contract.md`。阶段图、列名、gate stage、manifest 路径、回退目标都从这里派生；`common/n2d_route.py`、`n2d/progress.py`、`n2d-progress/scan.py`、`n2d-review/scripts/gate.py` 不应各自维护一张阶段表。

进度表是六阶段所有 skill 的 **single source of truth**。**表头由 `skills/common/n2d_contract.py` 定义，`n2d-script/scripts/split_novel.py` 生成时读取它**——本文与调度器 SKILL 只复述、不另立一套。当前 16 列格式：

```markdown
# <剧名> — 生产进度

共拆分 **N** 集。

| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 第1集 | 2388 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 4/19 | ✅ | 0/12 | ⬜ |
```

> **回写一律走脚本**：`python3 <skill>/progress.py set <作品根> 第N集 <列名> <值>`；旧项目缺新列先 `progress.py ensure-col`。别手工编辑表格（避免列错位）。
> **每集产物快照**：`progress.py set` 回写进度时会自动刷新 `脚本/第N集/manifest.json`，记录 schema 版本、制作模式、阶段产物路径、存在性和文件 hash，供 review 与最小返工范围使用。需要手动重建时可跑 `python3 skills/n2d/manifest.py <作品根> 第N集 [--stage stage_key]`。

**列含义**：

| 列组 | 写入者 | 含义 |
|---|---|---|
| raw | n2d-script 拆集脚本 | 原文片段已落档（展示用，不计入流程完成判定） |
| 剧本改编 / bgm / 封面 | n2d-script 阶段1 | 配音前的剧本改编（台词/BGM 设计/封面）完毕 |
| 配音 | n2d-voice | 逐句配音 + 时长清单.json。真实配音写 `✅`；任一句占位/估算写 `⏳rough`，不能冒充定稿 |
| 分镜设计 / 素材清单 / 字幕中 / 字幕英 | n2d-script 阶段2 | 用配音时长定稿分镜剧本/故事板/素材清单/SRT |
| 出图prompt | n2d-image | 本集出图 prompt **全套**写完（共享定妆库 + 本集分镜） |
| 出图 | n2d-image | `已完成 PNG / 本集需要的总数`（分子含共享复用 + 本集分镜） |
| 视频prompt / 视频 | n2d-video | prompt 写完 ✅；`视频` = `已完成 MP4 / 本集 Clip 总数` |
| 成片 | n2d-compose | 剪辑合成 + BGM + 烧字幕 → 成片完成 |

**调度规则**：任一列为 ⬜ 时，对应 skill 可以接手该集；列已 ✅ 时，下游 skill 才能继续。完整逐列路由判断见调度器 `SKILL.md`。

---

## 四、三项架构（图 AI / 生视频模型 / 生视频渠道）

视频阶段拆成两个选择点：`生视频模型`（Seedance 2.0 / Veo 3.1 / Kling 3.0 / Hailuo 02/2.3 / Runway Gen-4 / Luma Ray3.2 / Pika 2.5 / HunyuanVideo 1.5 / Wan 2.2 / LTX-2.3 / manual）和 `生视频渠道`（即梦/Dreamina / 豆包 / 海螺AI / 可灵/Kling / Google Gemini API / Runway API / 本地开源 / manual）。新作品首跑必须让用户选择一次；默认只作预选/兜底，不是静默固定。图片阶段按 `生图AI` 选择点统一到一个官方/已登录后端（默认 Codex，可选 Dreamina/即梦官方 CLI、官方多参考后端），禁止第三方逆向、`同视频AI` / `同视频模型` 含糊口径和 web 自动化出图。

```
图 AI（出图工具）→ 图片 → 生视频模型（运动估计/风格基线） → 生视频渠道（调用入口）
       ↑                          ↑                         ↑
   决定 prompt 写法        决定图片要能被谁消化        决定 CLI/API/网页
```

- **当前默认**：图 AI = `生图AI` 所选官方/已登录后端（默认 Codex，可选 Dreamina/即梦官方 CLI）；生视频模型读 `_设置.md` 的 `生视频模型`（默认 Seedance 2.0），渠道读 `生视频渠道`（默认 即梦/Dreamina）。即使渠道=即梦，也必须在 `生图AI` 中显式写 Dreamina/即梦，不能写含糊的 `同视频AI` 或 `同视频模型`。
- **跨 AI 桥接**：图 AI ≠ 生视频模型（如 Codex 出图 + Seedance 2.0，或 Seedream 出图 + Kling 3.0）。**所有 image prompt 末尾必须拼接生视频模型的"图像风格锚定句"**，否则生视频模型的 image2video 运动估计会崩。

**记录位置**：`global_style.md` 顶部记三行：
```
目标视频模型：<读 _设置.md 的 生视频模型；新作品首跑选择>
生视频渠道：<读 _设置.md 的 生视频渠道；新作品首跑选择>
目标图AI：Codex   ← 默认；可换官方/已登录图后端；Dreamina/即梦官方 CLI 可用于图片
```

详细档案见 `n2d-image/references/platforms.md` 和 `n2d-video/references/platforms.md`。

---

## 五、首跑示范（拿到小说第一次）

```
用户：把这个小说改成漫剧素材：/Users/me/works/我的小说.docx

调度（n2d）→ 识别"情境 A 首跑"：
  先给「制作模式」菜单选一次（影响全程出片顺序，不静默默认）：
    A 配音先行（推荐·配音已就绪）/ B 先出视频后配音（快速 demo 或配音还没就绪）/ C 原生音画（native AV，一次出同步音画）
    → 用户选后落 _设置.md（见 SKILL「制作模式 · 首跑选择」）。下面按默认 A 走。
  推荐：调 n2d-script "/Users/me/works/我的小说.docx"
  说明：会先拆集，然后精修第1集

用户：跑 n2d-script

n2d-script（阶段1·剧本改编）→
  1. 把小说挪到 制漫剧/我的小说/小说/
  2. 跑 split_novel.py → 生成 制漫剧/我的小说/{_进度.md, 设定库/{global_style.md, characters/, locations/}, 脚本/第N集/raw.txt}
  3. 在 _进度.md 写入 N 集骨架（raw 列 ✅，其他全 ⬜）
  4. 精修 设定库/global_style.md + 设定库/characters/ + 设定库/locations/
  5. 精修第1集 阶段1剧本(台词+bgm+封面) → 剧本改编/bgm/封面列 ✅（**此阶段不做分镜**）
  6. 报告：第1集剧本齐，下一步 n2d-voice 配音（配音先行：真音时长驱动镜头）

用户：跑 n2d-voice 制漫剧/我的小说 第1集

n2d-voice →
  1. 把 voiceover.txt 逐句配音（CosyVoice/克隆/MiniMax；缺凭证回退 say 占位）
  2. 落 合成/第1集/配音/{line_NN.wav, voice_zh.wav, 时长清单.json(每句实测时长)}
  3. 全句真实配音 → 配音列 ✅；若任一句占位/估算 → 配音列 ⏳rough，并提示只能作 rough timing

用户：跑 n2d-script 第1集（阶段2·分镜设计，配音后回跑）

n2d-script（阶段2）→
  1. 跑 finalize_storyboard.py → 用实测时长定 分镜剧本 + 故事板(Clip时长) + 镜头时长.json
  2. 产 素材清单 + 字幕_中文.srt（默认中文-only；海外才加 字幕_英文.srt）
  3. 分镜设计/素材清单/字幕中 列 ✅ → 报告：可调 n2d-image

用户：跑 n2d-image 制漫剧/我的小说 第1集

n2d-image →
  1. 走"强制 5 步 SOP"：扫共享 → 列需求 → 差集 → 追加共享定妆 → 建本集 prompt
  2. 写完 → 出图prompt 列 ✅
  3. 按 _设置.md 的 生图AI（默认 Codex，可选官方后端）生图
  4. 出 PNG → 用户筛 → 落档 出图/{共享,第N集}/ → 出图列填 K/N
  5. 全部生成 → 出图列 K/K → 报告可调 n2d-video

用户：跑 n2d-video ... → n2d-compose（成片落 合成/第1集/）
```

---

## 六、调度脚本意图（不实现，写给读者）

调度本身**不需要复杂逻辑**——核心就是读 `_进度.md` 找最小未完成集 + 最早未完成列，然后人话报告"调哪个 skill 处理哪一集"。

伪代码：

```
def dispatch(work_root):
    progress = read(f"{work_root}/_进度.md")
    for episode in episodes_sorted_by_number(progress):
        if any(episode[c] != "✅" for c in ["剧本改编", "bgm", "封面"]):
            return ("n2d-script(阶段1)", episode.id, "剧本改编未齐")
        if episode["配音"] != "✅":
            return ("n2d-voice", episode.id, "未配音")
        if episode["分镜设计"] != "✅":   # 实际路由只闸 分镜设计；素材清单/字幕中是阶段2 副产物、字幕英仅海外投放才出，均不阻塞路由（与 progress.py STAGES 一致）
            return ("n2d-script(阶段2)", episode.id, "分镜设计未齐（配音后回跑）")
        if episode["出图prompt"] != "✅" or not all_done(episode["出图"]):  # "4/19" 形式
            return ("n2d-image", episode.id, "出图未完")
        if episode["视频prompt"] != "✅" or not all_done(episode["视频"]):
            return ("n2d-video", episode.id, "视频未完")
        if episode["成片"] != "✅":
            return ("n2d-compose", episode.id, "未合成")
    return (None, None, "全集完工")
```

> 实际不需要另写脚本——机读路由用 `n2d/progress.py`，它经 `common/n2d_route.py` 复用 `n2d_contract.STAGE_GRAPH` 并按 `制作模式` 调整依赖。`制作模式=先出视频后配音` 的 `⏳rough` 放行/合成前补真音、`制作模式=原生音画` 的配音可选旁白层，都在同一套路由里生效。

---

## 七、配音 / 分镜 / 合成阶段（均已实现）

六阶段已全部落地：配音(`n2d-voice`·前移到分镜与出图之前) → 分镜设计(`n2d-script` 阶段2·配音时长驱动) → 剪辑合成+BGM+烧字幕(`n2d-compose`·FFmpeg 脚本化替代剪映)。`成片` 列已在 split_novel.py 生成的表头里（最右一列），调度规则即 §六 伪代码。完整逐列路由见调度器 SKILL.md。
