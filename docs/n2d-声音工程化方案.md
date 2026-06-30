# n2d 声音工程化方案：把 BGM/SFX 提到和配音同等地位

> 状态：设计稿（未实施）。目标：让"BGM 和配音也很重要"在 n2d 流水线里**有抓手**，而不是停在口号。
> 日期：2026-06-05

## 0. 一句话诊断

n2d 的"声音"现在是**分裂**的：

- **配音(voice) = 一等公民**。它在每一阶段都有抓手——脚本阶段有结构化标注、配音阶段有 TTS 后端+情绪驱动、合成阶段有 ducking、质检阶段有专项。
- **BGM = 二等公民**。`bgm.txt` 只是文字描述没人读，没有生成后端，靠手工 Suno 或程序化正弦波占位，可以一路占位到成片。
- **SFX(音效) = 三等公民**。`bgm.txt` 列了"关键音效点"，纯文档，零实装。

配音能进流水线的根因只有两条：**它有一个生成后端(TTS)，且它的表演被参数化驱动(情绪/语速→TTS 参数)**。要让 BGM 同等，就得给它补上这两条，再配套门禁与质检。

## 1. 现状对照表（落到文件/行）

| 环节 | 配音(已做到) | BGM(缺) | 证据 |
|---|---|---|---|
| 脚本阶段产出 | `voiceover.txt` 四层标注 `[镜头·角色·情绪·语速] 台词 ‖气口 ⚡钩子`，驱动下游 | `bgm.txt` 只有"整体情绪曲线+分段风格文字+音效点"，**无机器可读结构**，无人读取 | `skills/n2d-script/references/formats.md:167`；`制漫剧/本宫才是这皇宫最大的妖/脚本/第1集/bgm.txt` |
| 生成后端 | `render_voice.py` 多后端(CosyVoice/FishSpeech/MiniMax/火山/say) | **无**。手工 Suno / 程序化正弦波占位 | `skills/n2d-voice/render_voice.py:22`；`skills/n2d-compose/compose.sh:45-51` |
| 表演/情绪驱动 | 每句情绪→emotion 参数、语速→atempo、钩子→留拍 | bgm.txt 情绪曲线**与 compose 完全脱钩**，不进任何参数 | `render_voice.py:27-50,184` |
| 时长对齐 | `时长清单.json` 逐句实测时长 | 无。BGM 不知道每段该多长 | `render_voice.py:244-254` |
| 卡点 | — | 只有 `BGM_OFFSET` 平移整条 BGM，**多爽点只能对齐第一个** | `compose.sh:11,42-44` |
| 混音 | sidechain ducking，配音永远压过 BGM，参数可调 | ✅ 这一环 BGM 已被照顾 | `compose.sh:83-92` |
| 进度门禁 | "配音占位未精修"会被质检拦 | `_设置.md: BGM来源: 占位` 可一路占位到成片，无拦截 | `制漫剧/.../_设置.md:10` |
| 质检 | 专项：占位未精修、双人声打架 | 仅一条"drop 对齐爽点时间戳" | `skills/n2d-review/references/checklist.md:50-59` |
| SFX | — | bgm.txt 列点=纯文档，零实装；clip 原生音默认丢弃 | `compose.sh:53-70`；`skills/n2d-compose/SKILL.md:35` |

## 2. 设计原则（对称于配音）

1. **每个声音元素都要有"后端"**。配音=TTS，BGM=器乐生成(复用 song 线)，SFX=音效库检索。没有后端的东西永远是手工补充，进不了流水线。
2. **声音由脚本结构化驱动，不靠文字描述**。bgm.txt 要像 voiceover.txt 一样机器可读。
3. **复用 voice-first 的时序经验**。配音已是"出图前先配音、用实测时长驱动镜头"。BGM 同理：**配音定稿后再定 BGM 段落时长**，让 drop 精确对齐爽点。
4. **占位可以有，但占位必须留痕 + 门禁拦截**。配音占位会写 `占位:true` 并被质检抓；BGM/SFX 占位也要同等待遇。
5. **不破坏现有默认行为**。所有新增走可选参数/可降级，缺文件时优雅退回当前占位逻辑（与 compose.sh 现有风格一致）。

## 3. 四个落点（按性价比排序）

### ① 给 BGM 一个生成后端（最根本）

**做什么**：让 n2d-compose 在 BGM 缺失时，不再只会程序化正弦波，而是能调用 `song` 线的 `song-compose`(ACE-Step 本地 / Suno 云) 生成**纯器乐** BGM。

**落点**：
- 新增 `skills/n2d-compose/gen_bgm.py`（或 `references/bgm生成.md` 指南）。输入：结构化 `bgm.json`(见落点②) + 目标总时长(来自 `时长清单.json` 末句 end + 集尾留拍)。输出：`出视频/<EP>/配音/bgm.wav` 或 `脚本/<EP>/bgm.wav`。
- 后端优先级仿 render_voice.py：`ACE-Step(本地，Mac 可跑) > Suno(云) > DiffRhythm > 程序化占位`。env 可覆盖。
- `compose.sh:41` 的 `if [ -n "$BGMFILE" ]` 分支前，加一层：若无 BGMFILE 但存在 `bgm.json`，先调 gen_bgm.py 产出再走真实 BGM 路径；都没有才退回正弦波占位。
- **合规**：ACE-Step/Suno 生成的器乐属合成音乐，无需授权；但若用户要"翻唱某歌当 BGM"走 song-cover 的合规闸门。纯器乐 BGM 不带 AI-ident 问题（无人声克隆）。

**为什么是最高优先级**：补上"后端"这一条，BGM 从"手工找"变成"流程内可生成、可重跑、可迭代"，和配音对称。其余三点都依赖它才有意义。

### ② bgm.txt → 结构化 bgm.json + 配音后回跑

**做什么**：让 `n2d-script` 像产 voiceover 一样产**机器可读**的 BGM 规格，且分两遍——改编阶段先出情绪意图(粗)，**配音定稿后回跑**用实测总时长切准段落(细)。

**落点**：
- `skills/n2d-script/references/formats.md` 在 bgm 段(167 行附近)旁，新增 `bgm.json` 格式：
  ```json
  {
    "ep": "第1集",
    "total_dur": 92.4,              // 配音回跑后填，= 时长清单末句 end + 集尾留拍
    "mood_curve": "压抑→爆发→悬停", // 整体情绪曲线
    "segments": [
      {"start": 0.0,  "end": 6.0,  "mood": "冷开场", "instruments": ["低频弦乐","匕首冷响"], "intensity": 0.3},
      {"start": 6.0,  "end": 48.0, "mood": "铺垫",   "instruments": ["古琴单音"],          "intensity": 0.5},
      {"start": 48.0, "end": 54.9, "mood": "爽点drop","instruments": ["低鼓","重弦"],       "intensity": 1.0, "hit": true}
    ],
    "sfx": [
      {"t": 1.2, "name": "白绫轻落", "tag": "托盘三连①"},
      {"t": 1.6, "name": "匕首冷响", "tag": "托盘三连②"}
    ]
  }
  ```
- 段落的 `start/end` 与 `hit`(爽点重音) 由 `故事板.md` 的爽点时间戳 + `时长清单.json` 对齐——这正是"配音后回跑"要算的东西。
- `n2d-script` SKILL.md 的"阶段2·分镜设计(配音后回跑)"段落里，把"产 bgm.json"列为分镜设计的并行产物（它和镜头时长共享同一份 `时长清单.json`）。
- 保留人读的 `bgm.txt`，但它降级为"给人看的说明"，`bgm.json` 才是驱动源。

### ③ 多爽点卡点 + SFX 卡点

**做什么**：compose 阶段读 `bgm.json.segments[].hit` 和 `bgm.json.sfx[]`，在**每个**爽点叠 BGM 重音/转场音，而不是只 `BGM_OFFSET` 对齐第一个。

**落点**：
- `compose.sh` 当前 BGM 是"整条循环+首尾 fade"(42-44 行)。改为：按 `segments` 拼接/增益——在 `hit:true` 段用 `volume` 包络抬一个重音，或在该时间点混入一条 drop 采样。
- 新增 SFX 层：读 `bgm.json.sfx[]`，从音效库(新增 `skills/n2d-compose/assets/sfx/` 或检索后端)取对应音效，用 `adelay` 放到 `t` 时间点，混进现有第 3 路 `[2:a]sfx`(compose.sh:89)。当前 sfx 路是空 anullsrc(69 行)，这里正好填实。
- 降级：`bgm.json` 缺 `hit`/`sfx` 时，行为完全等同今天（不回归）。

### ④ 进度门禁 + 质检补齐

**做什么**：让 BGM/SFX 占位无法"蒙混过关"，对称于配音的"占位未精修"拦截。

**落点**：
- `_进度.md` 模板：把单列 `bgm` 拆成三态或加备注——`规划✅ / 生成✅ / 卡点✅`。占位时成片步骤打 ⚠️ 警告(不阻断，但留痕)。
- `_设置.md`：`BGM来源` 字段记录实际来源(ACE-Step / Suno-ID / 文件路径 / 占位)，而非现在的笼统"占位"。新增 `音效库` 字段。
- `skills/n2d-review/references/checklist.md:50-59` 音频段新增三条机/判检查：
  - 🟡 BGM 是否仍为占位（查 bgm.wav 是否程序化正弦/`_设置.md` 标占位）——机检
  - 🟡 BGM 情绪是否匹配 `bgm.json.mood_curve`/脚本曲线——人判
  - 🟢 关键 SFX 是否到位（`bgm.json.sfx[]` 有定义但成片无对应音）——人判
- `n2d-review` SKILL.md 的 description/Triggers 同步提到"BGM 占位检查/音效对账"。

## 4. 实施顺序与影响面

建议顺序 **① → ② → ③ → ④**（后者依赖前者的产物）。受影响 skill 与**必须同步更新的索引**(CLAUDE.md 硬约定)：

| 落点 | 改的 skill | 连带 |
|---|---|---|
| ① BGM 后端 | n2d-compose（新增 gen_bgm.py + compose.sh 接入） | 与 song-compose 共享 ACE-Step 环境；README 索引 |
| ② bgm.json | n2d-script（formats.md + SKILL.md 回跑段） | — |
| ③ 多爽点/SFX | n2d-compose（compose.sh + sfx 资产） | — |
| ④ 门禁质检 | n2d-review + n2d-script(_进度模板) + _偏好约定(_设置字段) | **`skills/README.md` 索引必须同步**（CLAUDE.md 硬约定）；n2d-review description 更新 |

**测试**：n2d-compose 无现成 pytest；①③ 改动建议加一个 `skills/n2d-compose/test_gen_bgm.py`（按 CLAUDE.md 约定从脚本自身目录跑）。②的 bgm.json 解析若进 finalize_storyboard 路径，复用 `skills/n2d-script/test_finalize_storyboard.py` 同款 fixture。

## 5. 不做什么（边界）

- **不动配音线**。voice 已是一等公民，本方案只补 BGM/SFX 到同一水位。voice 唯一可选小修是"跨集音色一致性自检"，但不在本方案范围。
- **不强制真实 BGM**。占位仍合法（快速粗剪需要），但占位必须留痕 + 质检可见，而非静默通过。
- **不引入新重型依赖**。BGM 后端复用已有的 ACE-Step(acestep conda 环境)，不新增模型栈。
- **不破坏现有 compose 默认行为**。所有新增走"有结构化文件则启用、否则降级到今天"。

## 6. 一句话总结

配音之所以是一等公民，是因为它有**后端 + 参数化驱动 + 时长清单 + 门禁质检**四件套。把这四件套照搬给 BGM（生成后端=复用 song 线、参数化驱动=bgm.json、时长对齐=配音后回跑、门禁质检=拆进度列+加 checklist），BGM 就和配音站到同一条工程线上了。SFX 作为 BGM 的附属层一并解决。
