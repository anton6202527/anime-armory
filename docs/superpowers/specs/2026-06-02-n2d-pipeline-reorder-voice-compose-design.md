# novel2drama 产线重排 + 配音/合成 skill 设计

日期：2026-06-02
状态：设计待实现
作者：wesley（与 Claude 协作）

## 1. 背景与问题

当前 novel2drama 四阶段产线（`novel2drama` 调度 + `n2d-script`/`n2d-image`/`n2d-video`）的流程顺序**与主流工作室做法相反**，导致后期被迫"压速贴字幕"，节奏不可控、成本高。

**当前（错误）顺序**：
```
分镜 → 故事板(Clip时长按平台默认估) → 出图 → 出视频 → [配音最后才生成]
```
实证（引 skill 原文）：
- `n2d-script` 故事板"**Clip 时长/运镜按目标视频 AI 档案**"（时长是估的，非配音定）。
- 字幕 SRT "**时间轴依故事板时长 + voiceover 台词推导**"（从估的时长推）。
- `voiceover.txt` 仅文本；真实配音音频不在流水线内（"Stage 4 配音/BGM/字幕合成不在本流水线 skill 范围"）。

**问题**：镜头时长先定死，配音最后塞，长了只能压速（本项目第1集即如此：MiniMax 配音超字幕窗口 → atempo 压速 → 不同步/不自然）。

## 2. 目标与主流流程

对齐主流：**先配音，配音时长决定镜头时长**，节奏可控、后期成本低。

**修正后顺序**：
```
小说
 ↓ n2d-script (阶段1)      分镜剧本 + 配音文案(文本) + 角色/场景/global_style + 故事板草稿(镜头清单, 不锁时长)
 ↓ n2d-voice  ★前移        配音文案 → 真实音频(CosyVoice等) → 统计每句时长 → 时长清单(timing manifest)
 ↓ n2d-script (阶段2·定稿)  读时长清单 → 故事板 Clip 时长定稿 + 字幕SRT(真实时间轴) + 素材清单/封面
 ↓ n2d-image              出图(镜头时长已定)
 ↓ n2d-video              图生视频(clip长 = 配音驱动的镜头长)
 ↓ n2d-compose ★新         合成 + BGM + 字幕 → 导出成片
```

对齐的行业栈：即梦(图+视频) / CosyVoice(配音) / Suno(BGM) / 剪映(字幕+混音)。本设计中 CosyVoice = n2d-voice 一个后端；Suno = 用户生成后投喂 n2d-compose；剪映那步由 n2d-compose 用 FFmpeg 脚本化替代。

## 3. 目录结构

```
制漫剧/<剧名>/出视频/第N集/
├── prompt/                       # 视频 prompt（不变）
│   ├── 00_总览.md
│   └── 01_clips.md
├── 视频/                         # ★ n2d-video 生成的 clip MP4 全归这
│   └── Clip1_*.mp4 … ClipK_*.mp4
├── 配音/                         # ★ n2d-voice 产出
│   ├── line_00.wav … line_NN.wav   # 逐句（可回退/替换/放 GPT-SoVITS 外部 wav）
│   ├── voice_zh.wav  voice_en.wav  # 拼好的整轨
│   ├── 时长清单.json               # ★ 每句 {镜头, 角色, 文本, 时长s}（驱动故事板定稿）
│   └── _voicecache/                # API 配音缓存（gitignore）
└── 成片_第N集_{zh|en|bilingual}.mp4   # ★ n2d-compose 输出（成片落集根）

制漫剧/<剧名>/common/废料/出视频/第N集/   # 废片（不变）
BGM：默认占位；可选 BGMFILE / common/bgm/ 放文件覆盖（含 Suno 生成的曲）
```

变化：n2d-video 产物从"集根平铺"改进 `视频/` 子文件夹；配音资产进 `配音/`；成片落集根。

## 4. 时长清单机制（核心新增）

`配音/时长清单.json`：n2d-voice 生成，是"配音驱动镜头时长"的桥梁。
```json
[
  {"idx":0,"镜头":"镜头1","角色":"沈念旁白","文本":"这里…不是我的宿舍。","时长":2.8},
  {"idx":1,"镜头":"镜头2","角色":"沈念旁白","文本":"粗麻、霉味…","时长":4.9},
  ...
]
```
- n2d-voice 逐句 TTS 后用 ffprobe 量每句时长写入。
- n2d-script 阶段2 读它：每镜头时长 = 该镜台词配音时长之和 + 留白(默认 +0.4s/镜，可配)；据此锁 `故事板.md` 的 Clip 时长，并生成 `字幕_中/英.srt` 真实时间码（累加镜头时长）。
- 无台词的纯空镜/转场镜头：给默认时长（如 2-3s，可配）。

## 5. Skill 改动清单

### 5.1 n2d-script（重写为两阶段）
- **阶段1（pre-voice）**：拆集 + `分镜剧本.md` + `voiceover.txt`(逐镜配音文案,角色·情绪) + `角色卡/场景卡/global_style` + `故事板.md 草稿`（镜头清单 + 运动/运镜描述，**时长留空/标 TBD**）。**不**再在此生成 SRT 与锁定 Clip 时长。
- **阶段2（post-voice·定稿）**：读 `配音/时长清单.json` → 锁 `故事板.md` Clip 时长 + 生成 `字幕_中/英.srt`(真实时间轴) + `素材清单.md` + `封面.md`。
- 触发：首跑/精修走阶段1；检测到该集 `配音` 列 ✅ 后走阶段2 定稿。
- `references/platforms.md` 中"Clip 时长按平台档案"改为"Clip 时长由配音时长驱动；平台档案只约束单 Clip 上限(如即梦≤8s)，超限则拆 Clip"。

### 5.2 n2d-voice（新 · 前移到出图前）
- **输入**：`脚本/第N集/voiceover.txt` + 后端选择/凭证(env)。
- **职责**：① 后端可插拔：GPT-SoVITS(本地克隆) / CosyVoice(本地克隆) / MiniMax / 火山 / macOS say(占位) ② 声音克隆管理（参考音频 → 克隆音色；含 demucs 人声分离去 BGM）③ 角色→音色映射(env 覆盖) ④ 逐句生成 → 统一电平(loudnorm -16 LUFS) ⑤ **量每句时长写 `时长清单.json`** ⑥ 拼整轨 `voice_{zh,en}.wav`。
- **不做**按窗口压速（因镜头时长本就由配音定，无需压）。
- **输出**：`配音/line_NN.wav` + `voice_*.wav` + `时长清单.json`。`_进度.md` 加「配音」列。
- **可独立**：单独重生某集/某角色配音、换音色重克隆，不碰其他阶段。
- 复用本项目已建工具：`_render_voice.py`(多后端,去掉窗口压速)、`_voice_clone.py`(MiniMax 复刻)、demucs 人声分离流程、GPT-SoVITS/CosyVoice 本地接入指引。

### 5.3 n2d-video（小改）
- clip 时长改成**读定稿 `故事板.md`**（来自配音驱动），不再用平台默认估。
- 产物落 `出视频/第N集/视频/`（非集根平铺）；废料/进度路径同步。

### 5.4 n2d-compose（新 · 合成）
- **输入**：`视频/`(clips) + (可选)`配音/voice_*.wav` + (可选)BGM(占位/文件/Suno文件) + `字幕_中/英.srt` + 模式(zh/en/bilingual)。
- **职责**：① 统一规格拼接 ② BGM（占位合成 or 文件）③ 混音（配音 + ducking BGM + clip 自带音效底）④（可选）转场音效层 ⑤ 烧字幕（**Pillow+overlay**，因本机 ffmpeg 无 libass）⑥ 出成片。
- **BGM 来源（提示用户，给丰富选项 + 接受自定义）**：ⓐ Suno 生成后给文件 ⓑ 素材库 ⓒ 指定本地文件 ⓓ 占位合成；也接受用户自由描述需求 → **鉴定合理可行**(文件存在/格式/时长够循环/版权)→ 可行照办，不可行说明并给替代。
- **转场音效**：可选层（用户给 SFX 文件就在 clip 边界铺，不给跳过）。
- **输出**：`成片_第N集_{mode}.mp4`。`_进度.md` 加「成片」列。
- 复用：`_compose.sh`(拼接/BGM/混音/ducking)、`_render_subs.py`(Pillow 烧字幕)。

### 5.5 novel2drama 调度器 + 进度表
- 阶段全景 + 路由按新顺序重排。
- `_进度.md` 列重排为：`… 分镜剧本 | 草稿故事板 | 配音 | 故事板定稿 | 素材清单 | 字幕中 | 字幕英 | 出图prompt | 出图 | 视频prompt | 视频 | 成片`。
- 路由规则按新阶段判定下一步。

### 5.6 收尾提示流（完成消息驱动助手，非 skill 硬链）
- skill 之间不能自动互调。各 skill 完成消息**指示助手发起询问**，用户选了再调下一 skill。
- n2d-video 跑完某集所有 clip → 完成消息让助手问：「① 现在合成成片？ ② 加BGM？(占位/给文件/Suno) ③ 加配音？(若配音已在前置阶段生成则跳过)」→ 路由 n2d-compose。
- **内嵌行业参考文案**（在决定音频时展示给用户）：
  > 对于 90 秒左右的一集漫剧，很多工作室会准备：
  > - 1 条背景音乐（全程循环）
  > - 2~5 个转场音效
  > - AI 角色配音

## 6. 复用现有工具映射

| 已建工具(本项目 出视频/) | 归入 skill | 改动 |
|---|---|---|
| `_render_voice.py` | n2d-voice | 多后端保留，**去掉按窗口压速**，加 CosyVoice 后端，输出时长清单 |
| `_voice_clone.py` | n2d-voice | MiniMax 复刻，原样 |
| demucs 人声分离流程 | n2d-voice | 封装成"克隆前清洗"可选步 |
| GPT-SoVITS / CosyVoice 本地接入指引 | n2d-voice | 写进 references |
| `_compose.sh` | n2d-compose | 拼接/BGM/混音/ducking，原样 |
| `_render_subs.py` | n2d-compose | Pillow+overlay 烧字幕，原样 |

## 7. 边界 / 错误处理

- n2d-script 阶段2 在 `配音` 列未 ✅ 时拒绝运行，提示先跑 n2d-voice。
- n2d-voice 后端凭证缺失 → 回退 say 占位并告警。
- 单 Clip 配音时长超平台上限(即梦≤8s) → 故事板定稿时**拆 Clip**（尾帧=下一首帧）。
- BGM 用户自定义不可行 → 明确说明原因 + 给替代，不静默忽略。
- 本机 ffmpeg 无 libass → 字幕走 Pillow+overlay（已验证）。

## 8. 不做（YAGNI）

- 不做 BGM 自动选曲/曲库语义匹配（占位 + 用户文件足够）。
- 不直接调 Suno API（无稳定接口；走用户生成→投喂）。
- 不做转场音效自动生成（用户给文件才铺）。
- 不做多语种配音自动翻译（en 配音用现成 en SRT 文本）。

## 9. 影响范围小结

主要重写：`n2d-script`(拆两阶段)。新增：`n2d-voice`、`n2d-compose`。小改：`n2d-video`(读定稿+视频/目录)、`novel2drama`(顺序/路由/进度列)。新机制：`时长清单.json`。
