# 四阶段流水线 — 架构与目录约定

本文档是调度器 `novel2drama` 的扩展参考。说清楚整个 pipeline 是怎么组织的，子 skill 如何协作，目录铁律，以及 first-time 的标准首跑示范。

---

## 一、为什么拆四块

原 `novel2drama` skill 在 100+ 集制作期间膨胀到："拆集 + 物料 + 出图 prompt + 出图操作 + 视频" 全揉一起，导致：

- 任一集只在某一阶段时，无关阶段细节也塞进上下文
- 不同 AI 工具（图 AI / 视频 AI）的差异散布在多处
- 经验沉淀（Q&A）越累越多，单文件难翻

拆分后每阶段一个 skill，按需加载：

| Stage | Skill | 关注点 | 不关注 |
|---|---|---|---|
| 0 调度 | `novel2drama` | 路由 + 全局架构 | 任何具体生产细节 |
| 1 物料 | `n2d-script` | 拆集 + 8 类素材模板 + 角色/场景卡 | AI CLI 调用 / 锚定句细节 |
| 2 出图 | `n2d-image` | 出图 prompt + 扫 CLI + 生图 / 指导 | 视频 prompt / 故事板 |
| 3 视频 | `n2d-video` | 视频 prompt + 扫 CLI + 生视频 / 指导 | 物料模板 |

---

## 二、目录铁律

### 作品根

每个作品独占一个目录：

```
artifacts/<剧名>/
├── 小说/                  原文
├── 分镜剧本/              所有素材根
└── temp/                  废料归档
```

`<剧名>` 用中文是 OK 的（macOS/Linux 路径支持）。

### 共享 vs 本集

**铁律**：**全篇复用的资产放共享层，仅本集出现的放本集层**。

```
分镜剧本/                              ← 共享层根
├── global_style.md                   全局画风/世界观/目标AI（仅 1 份）
├── characters/                       角色设定（一角色一文件）
├── locations/                        场景设定
├── 出图/                             【共享 PNG 库】定妆图
├── 出图prompt/                       【共享 prompt 库】定妆 prompt 实战
│   ├── 00_索引.md                    全篇定妆清单 + 状态
│   ├── 角色定妆.md
│   ├── 场景定妆.md
│   └── 道具定妆.md
├── _进度.md                          全作品进度表
└── 第N集/                            ← 本集层根
    ├── raw.txt                       拆集出来的原文片段
    ├── 分镜剧本.md / 故事板.md / 素材清单.md
    ├── voiceover.txt / bgm.txt / 封面.md
    ├── 字幕_中文.srt / 字幕_英文.srt
    ├── 出图prompt/                   本集分镜出图 prompt
    │   ├── 00_总览_出图清单.md
    │   └── 01_分镜出图.md
    ├── 出图/                         本集分镜 PNG（不含定妆）
    └── 视频/                         本集 MP4
```

**判定表**：

| 资产 | 放哪 | 理由 |
|---|---|---|
| 角色定妆（含形态变体） | 共享 | 跨集复用 |
| 场景定妆 | 共享 | 多集复用 |
| 反复入镜道具 / HUD 光幕 | 共享 | 全集统一视觉 |
| 死亡 / 仅本集形态 | **仍共享** | 规则统一 > 节省 3MB |
| 一次性道具 | 本集 | 不复用 |
| 分镜出图 | 本集 | 一镜一图 |
| 封面 | 本集 | 一集一封 |
| 视频片段 | 本集 | 一镜一段 |

### 废料

筛选/废图/废视频统一进 `temp/第N集/`。**不要**留在 Downloads，不要散落作品根。

---

## 三、进度表（_进度.md）协议

进度表是 4 个 skill 的 **single source of truth**。格式：

```markdown
# <剧名> — 生产进度

共拆分 **N** 集。

| 集 | 字数 | raw | 分镜剧本 | 故事板 | 素材清单 | 配音 | BGM | 封面 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 第1集 | 2388 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 4/19 | 0/12 |（开局即高潮）
```

**列含义**：

| 列组 | 写入者 | 含义 |
|---|---|---|
| raw | n2d-script 拆集脚本 | 原文片段已落档 |
| 分镜剧本 → 字幕英 | n2d-script | 8 类素材生成完毕 |
| 出图prompt | n2d-image | 本集出图 prompt **全套**写完（共享层 + 本集层） |
| 出图 | n2d-image | `已完成 PNG / 本集需要的总数`（分子含共享复用 + 本集分镜） |
| 视频 | n2d-video | `已完成 MP4 / 本集 Clip 总数` |

**调度规则**：任一列为 ⬜ 时，对应 skill 可以接手该集；列已 ✅ 时，下游 skill 才能继续。

---

## 四、双轴（图 AI / 视频 AI）

skill 默认支持四个目标平台：**即梦AI**（默认） / **可灵Kling** / **Seedance** / **Veo**（海外）。

```
图 AI（出图工具）→ 图片 → 视频 AI（出视频工具）
       ↑                          ↑
   决定形式               决定内容
prompt 写法/语言         图片该长啥样
```

- **同 AI 闭环**（默认）：图 AI = 视频 AI = 即梦。最稳，prompt 直接写。
- **跨 AI 桥接**：图 AI ≠ 视频 AI（如 Gemini 出图 + 即梦视频）。**所有 image prompt 末尾必须拼接视频 AI 的"图像风格锚定句"**，否则视频 AI 的 image2video 运动估计会崩。

**记录位置**：`global_style.md` 顶部记两行：
```
目标视频AI：即梦
目标图AI：即梦   ← 同视频AI 即同 AI 闭环
```

详细档案见 `n2d-image/references/platforms.md` 和 `n2d-video/references/platforms.md`。

---

## 五、首跑示范（拿到小说第一次）

```
用户：把这个小说改成漫剧素材：/Users/me/works/我的小说.docx

调度（novel2drama）→ 识别"情境 A 首跑"：
  推荐：调 /n2d-script "/Users/me/works/我的小说.docx"
  说明：会先拆集，然后精修第1集

用户：跑 /n2d-script

n2d-script →
  1. 把小说挪到 artifacts/我的小说/小说/
  2. 跑 split_novel.py → 生成 artifacts/我的小说/分镜剧本/ + 第N集/raw.txt
  3. 在 _进度.md 写入 N 集骨架（raw 列 ✅，其他全 ⬜）
  4. 精修 global_style.md + characters/ + locations/
  5. 精修第1集 8 类素材 → 物料列 ✅
  6. 报告：第1集物料齐，可调 /n2d-image 出图

用户：跑 /n2d-image artifacts/我的小说 第1集

n2d-image →
  1. 走"强制 5 步 SOP"：扫共享 → 列需求 → 差集 → 追加共享 → 建本集 prompt
  2. 写完 → 出图prompt 列 ✅
  3. 扫本机生图 CLI（dreamina / gemini-cli / ...）
  4. 有 CLI：调 → 出 PNG → 用户筛 → 落档 → 出图列填 K/N
     无 CLI：分步指导用户在即梦 web 上一张张生 → 用户截图回传 → 落档
  5. 全部生成 → 出图列 K/K → 报告可调 /n2d-video

用户：跑 /n2d-video ...
```

---

## 六、调度脚本意图（不实现，写给读者）

调度本身**不需要复杂逻辑**——核心就是读 `_进度.md` 找最小未完成集 + 最早未完成列，然后人话报告"调哪个 skill 处理哪一集"。

伪代码：

```
def dispatch(work_root):
    progress = read(f"{work_root}/分镜剧本/_进度.md")
    for episode in episodes_sorted_by_number(progress):
        stage1_cols = ["分镜剧本", "故事板", "素材清单", "配音", "BGM", "封面", "字幕中", "字幕英"]
        if any(episode[c] != "✅" for c in stage1_cols):
            return ("n2d-script", episode.id, "物料未齐")
        if episode["出图prompt"] != "✅":
            return ("n2d-image", episode.id, "出图prompt 未写")
        if not all_done(episode["出图"]):  # "4/19" 形式
            return ("n2d-image", episode.id, "出图未完")
        if not all_done(episode["视频"]):
            return ("n2d-video", episode.id, "视频未完")
    return (None, None, "全集完工")
```

实际操作上不需要写脚本——人肉读表即可。

---

## 七、扩展（未来加 Stage 4 合成）

预留：Stage 4 = 配音 + BGM + 字幕 + 剪辑合成。当前不在 skill 范围（剪映/CapCut/FFmpeg 手工或外部工具）。

若未来加入 `n2d-compose`，进度表追加 `视频` 列右边的 `成片` 列即可，调度规则向后扩展。
