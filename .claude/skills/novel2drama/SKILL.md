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

详细架构与目录约定见 `references/architecture.md`。实战 Q&A 见 `Q&A.md`（全阶段共用，沉淀的翻车修正都在那）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../_偏好约定.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`生视频AI`、`生图AI`、`配音后端`、`视频分辨率`、`画幅`、`BGM来源`、`一致性增强`。

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

每个阶段都按 **集** 为单位推进；进度统一写进 `<作品根>/common/_进度.md`。

## 调度工作流

### 入口判定

**情境 A — 用户给了一个小说路径，作品根尚不存在**：
→ 推荐 `/n2d-script <小说路径>`（Stage 1 首跑：拆集 + 精修第1集）

**情境 B — 用户给了一个已存在的作品根 或 `_进度.md` 路径**：
→ 走下面的"读进度 → 路由"流程

**情境 C — 用户问"怎么开始 / 流程是什么"**：
→ 简述上面的六阶段全景 + 让用户给小说路径

### 读进度 → 路由

> **首选：跑确定性路由脚本**（别靠 LLM 推 16×N 大表，烧上下文且易错）：
> ```bash
> python3 <skill>/progress.py <作品根>          # 全局：最小未完成集 + 各阶段卡集数 + 推荐命令
> python3 <skill>/progress.py <作品根> 第N集    # 查指定集所处阶段 + 推荐命令
> ```
> 把脚本输出**直接讲给用户**。下面的"逐列判断"是脚本内部逻辑（容错/手查时参考）。
>
> **回写进度统一用脚本**（别手工编辑表格）：`python3 <skill>/progress.py set <作品根> 第N集 <列名> <值>`（值 = ✅ / ⬜ / 12/19）。各阶段 skill 收尾都调它。

1. 定位 `<作品根>/common/_进度.md`，读进度表
2. 进度表头形如：`| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |`
3. 对每一集逐列判断：
   - `剧本改编`/`bgm`/`封面` 任一 ⬜ → 还在 /n2d-script 阶段1·剧本改编
   - 阶段1 齐、`配音` ⬜ → 该集等 /n2d-voice 角色配音(统计台词时长)
   - `配音` ✅、`分镜设计` ⬜ → 回跑 /n2d-script 阶段2·分镜设计（时长驱动：分镜剧本+故事板+素材清单+SRT）
   - `分镜设计` ✅、`出图prompt`/`出图` 未满 → /n2d-image
   - `出图` 满、`视频` 未满 → /n2d-video
   - `视频` 满、`成片` ⬜ → /n2d-compose（剪辑合成+BGM+字幕；问用户 BGM 选项）
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

### 跨阶段并行的 OK 信号

阶段不必严格串行——第 K 集出图时，第 K+1 集物料可以并行精修，第 K-1 集视频可以并行生成。**调度规则**：只要 `_进度.md` 该集对应列还是 ⬜ 就可以开干；不需要等前面集全部跑完。

## 作品目录约定

```
制漫剧/<剧名>/
├── 小说/                          原文（.txt/.docx）
├── common/                        全局资产 + 废料
│   ├── _进度.md                   全作品 dashboard（4 skill 共用 single source of truth）
│   ├── global_style.md            全局画风/世界观/目标AI
│   ├── characters/                角色卡（设定 + 定妆 prompt 源头）
│   ├── locations/                 场景卡
│   └── 废料/                      4 选 1 / 废图 / 废视频
│       ├── 出图/{common,第N集}/   筛选 / 废图
│       └── 出视频/第N集/          废视频片段
├── 脚本/                          ← n2d-script 产物
│   └── 第N集/
│       ├── raw.txt 分镜剧本.md 故事板.md 素材清单.md
│       ├── voiceover.txt bgm.txt 封面.md
│       └── 字幕_中文.srt 字幕_英文.srt
├── 出图/                          ← n2d-image 产物
│   ├── common/                    全篇定妆库
│   │   ├── prompt/
│   │   │   ├── 00_索引.md
│   │   │   └── 角色定妆.md / 场景定妆.md / 道具定妆.md
│   │   └── 定妆_*.png
│   └── 第N集/                     本集分镜
│       ├── prompt/
│       │   ├── 00_总览.md
│       │   └── 01_分镜出图.md
│       └── 镜头N_*.png
└── 出视频/                        ← n2d-video 产物
    ├── common/                    （如有跨集复用片段，如转场/空镜）
    │   ├── prompt/
    │   └── *.mp4
    └── 第N集/
        ├── prompt/
        │   ├── 00_总览.md
        │   └── 01_clips.md
        └── 视频/                  ← clip MP4 全归这（n2d-video）
        │   └── ClipK_*.mp4
        ├── 配音/                  ← n2d-voice：line_NN.wav + voice_*.wav + 时长清单.json
        └── 成片_第N集_{mode}.mp4   ← n2d-compose 输出
```

> **prompt/PNG/MP4 分离铁律**：每个 `出图/` 或 `出视频/` 文件夹（无论是 `common/` 还是 `第N集/`）一律分两层——`prompt/` 子目录装所有 prompt md，**生成产物 PNG/MP4 在 `prompt/` 同级**（即 `common/` 或 `第N集/` 的根）。

> 旧仓库可能没有 `小说/` 子目录（原文直接在作品根）。仍能识别——作品根下 `.txt/.docx` 即为原文。

## 子 skill 速查

| skill | 何时调 | 输入 | 关键输出 |
|---|---|---|---|
| `/n2d-script` | 阶段1 剧本改编(台词) / 阶段2 分镜设计(配音后) | 小说路径 或 作品根 + 集号 | 阶段1: voiceover+bgm+封面；阶段2: 分镜剧本+故事板+素材清单+字幕 |
| `/n2d-image` | 物料齐后出图 prompt + 生图 | 作品根 + 集号 | `出图/{common,第N集}/` prompt + PNG + 进度勾 ✅ |
| `/n2d-voice` | 阶段1齐后配音(出图前) | 作品根 + 集号 | `出视频/第N集/配音/` 音频 + 时长清单.json + 配音列 ✅ |
| `/n2d-video` | 出图齐后出视频 prompt + 生视频 | 作品根 + 集号 | `出视频/第N集/视频/` MP4 + 进度勾 ✅ |
| `/n2d-compose` | 视频齐后合成成片 | 作品根 + 集号 | `成片_第N集_{mode}.mp4` + 成片列 ✅ |

## 实战参考

- 详细架构、目录铁律、首跑示范：`references/architecture.md`
- 翻车 + 修正 + 决策案例（20+ Q&A）：`Q&A.md`
- **导演节奏 / 留存工程（全阶段共用）**：`references/导演节奏.md` —— 留存曲线/黄金3秒/钩子密度/爽点憋放/集尾cliffhanger/镜头时长曲线/卡点/念白节奏。这是红果爆款"画质普通但留人"那一层，n2d-script/voice/video/compose 都引用。
- 镜头空间语法：`n2d-script/references/分镜语法.md`
- 平台档案 / prompt 格式：在各阶段 skill 的 `references/` 下
