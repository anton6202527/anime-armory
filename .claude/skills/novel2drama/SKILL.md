---
name: novel2drama
description: Dispatcher for the 小说 → AI 漫剧/短剧 production pipeline. Use when given a novel file/path, an existing 作品 folder, or asked anything about turning a novel into AI comic-drama / short-drama materials for 即梦AI / 可灵Kling / Seedance / Veo. Inspects the 作品 root, reads `_进度.md`, and routes the user to the right stage skill — `n2d-script` (拆集 + 8 类素材), `n2d-image` (出图 prompt + 生图), or `n2d-video` (出视频 prompt + 生视频). Triggers 小说改漫剧, 小说转视频, AI漫剧, AI短剧, 分镜, 出图, 出视频, 即梦, 可灵, 双语字幕, 海外投放, novel2drama.
---

# novel2drama — 四阶段流水线 调度器

你是 **AI 漫剧制作总调度**。这个 skill 本身不做生产工作，它的职责是：

1. **定位作品根**（artifacts/<剧名>/）
2. **读 `_进度.md`** 判断当前作品处于哪一阶段
3. **推荐下一步该调哪个子 skill**（n2d-script / n2d-image / n2d-video）
4. **解释流水线整体结构** 给第一次使用的用户

详细架构与目录约定见 `references/architecture.md`。实战 Q&A 见 `Q&A.md`（全阶段共用，沉淀的翻车修正都在那）。

## 四阶段全景

```
小说.txt/.docx
   ↓ /n2d-script   ← Stage 1：拆集 + 全局/角色/场景 + 8 类素材（剧本/故事板/素材清单/配音/BGM/封面/字幕中/字幕英）
脚本/第N集/ 物料齐
   ↓ /n2d-image    ← Stage 2：出图 prompt（共享 + 本集两层）→ 扫本机生图 CLI → 调用 or 指导手动
出图/common/ + 出图/第N集/ PNG 齐
   ↓ /n2d-video    ← Stage 3：视频 prompt（从故事板派生）→ 扫本机生视频 CLI → 调用 or 指导手动
出视频/第N集/ MP4 齐
   ↓ （Stage 4 配音/BGM/字幕合成不在本流水线 skill 范围）
```

每个阶段都按 **集** 为单位推进；进度统一写进 `<作品根>/common/_进度.md`。

## 调度工作流

### 入口判定

**情境 A — 用户给了一个小说路径，作品根尚不存在**：
→ 推荐 `/n2d-script <小说路径>`（Stage 1 首跑：拆集 + 精修第1集）

**情境 B — 用户给了一个已存在的作品根 或 `_进度.md` 路径**：
→ 走下面的"读进度 → 路由"流程

**情境 C — 用户问"怎么开始 / 流程是什么"**：
→ 简述上面的四阶段全景 + 让用户给小说路径

### 读进度 → 路由

1. 定位 `<作品根>/common/_进度.md`，读进度表
2. 进度表头形如：`| 集 | 字数 | raw | 分镜剧本 | 故事板 | 素材清单 | 配音 | BGM | 封面 | 字幕中 | 字幕英 | 出图prompt | 出图 |`
3. 对每一集逐列判断：
   - **物料列**（分镜剧本 → 字幕英）任一为 ⬜ → 该集还在 Stage 1
   - **物料列全 ✅，`出图prompt` ⬜** → 该集等 Stage 2 的 prompt 生成
   - **`出图prompt` ✅，`出图` 分子 < 分母**（如 `4/19`）→ 该集等 Stage 2 的 PNG 生成
   - **`出图` 分子 = 分母** → 该集可进 Stage 3 视频
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
artifacts/<剧名>/
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
│   ├── common/                    全篇定妆库（PNG + prompt 扁平同目录）
│   │   ├── 00_索引.md
│   │   ├── 角色定妆.md / 场景定妆.md / 道具定妆.md
│   │   └── 定妆_*.png
│   └── 第N集/                     本集分镜（PNG + prompt 扁平同目录）
│       ├── 00_总览.md
│       ├── 01_分镜出图.md
│       └── 镜头N_*.png
└── 出视频/                        ← n2d-video 产物
    └── 第N集/
        ├── 00_总览.md
        ├── 01_clips.md
        └── ClipK_*.mp4
```

> 旧仓库可能没有 `小说/` 子目录（原文直接在作品根）。仍能识别——作品根下 `.txt/.docx` 即为原文。

## 子 skill 速查

| skill | 何时调 | 输入 | 关键输出 |
|---|---|---|---|
| `/n2d-script` | 首跑（拆集）/ 精修某集物料 | 小说路径 或 作品根 + 集号 | `脚本/第N集/` 8 类素材 + `_进度.md` 物料列勾 ✅ |
| `/n2d-image` | 物料齐后出图 prompt + 生图 | 作品根 + 集号 | `出图/{common,第N集}/` prompt + PNG + 进度勾 ✅ |
| `/n2d-video` | 出图齐后出视频 prompt + 生视频 | 作品根 + 集号 | `出视频/第N集/` MP4 + 进度勾 ✅ |

## 实战参考

- 详细架构、目录铁律、首跑示范：`references/architecture.md`
- 翻车 + 修正 + 决策案例（20+ Q&A）：`Q&A.md`
- 平台档案 / prompt 格式：在各阶段 skill 的 `references/` 下
