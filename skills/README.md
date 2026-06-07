# Skills 索引

本项目的自定义 skills 按 创作线×生产线 + 公共能力 组织（写小说→制漫剧、写歌→制MV，外加公共 video-faceswap / image-faceswap 换脸、watermark 水印）。**目录保持扁平**（每个 skill 仍是 `skills/<name>/SKILL.md`）——
skill 之间用 `<skills>/<name>/...` 互相引用，故**不要**移进子目录，否则交叉引用与 skill 发现会失效。
本文件仅作分类说明。

> **工具中立 / 跨 AI 使用**：真身在仓库根 `skills/`，**不绑定任何特定 AI**。
> - **Claude Code** 经软链 `.claude/skills → ../skills` 自动发现并用 `Skill` 工具按触发词路由（无需改动）。
> - **其他 AI agent / 人**：直接读 `skills/<name>/SKILL.md`（= 这个 skill 干啥、何时用；frontmatter 的 `description` + 正文 `Triggers` 就是路由依据），照其说明做事，需要时跑 `skills/<name>/scripts/` 下的脚本。
> - **脚本是通用的**：纯 Python/bash，只调通用工具（ffmpeg / librosa / whisper / yt-dlp / 生图生视频 CLI 等），**无任何 Claude 专有 API**，谁都能执行。引用一律走中立路径 `skills/...`（旧 `.claude/skills/...` 经软链仍兼容）。

> **偏好约定（通用化原则）**：所有 skill 保持**通用**，不把平台/后端/分辨率写死成唯一路径。凡「让用户选」的点都是**选择点**，用户的实际选择是**私有的**，存在用户自己的空间——每作品 `<作品根>/_设置.md`（权威）+ 私有全局默认（memory 区 `创作偏好-默认.md`，开新项目预填），**不进共享 skill 代码 / 不进 git**。行为：选择点首次问一次→写 `_设置.md`→同项目沉默沿用；合规/不可逆/花钱多的点每次仍确认。机制与全部选择点目录见 [`_偏好约定.md`](_偏好约定.md)；每个 skill 有「## 偏好（私有）」段引用它。**新增选择点**→加进 `_偏好约定.md` 目录，别在正文写死。

---

## 一、n2d ——「小说 → AI 漫剧/短剧」生产管线

`novel2drama` 是总调度，按 `_进度.md` 把用户路由到对应阶段 skill。阶段顺序（**默认 `制作模式=配音先行`**）：

| 阶段 | Skill | 职责 |
|---|---|---|
| 调度 | `novel2drama` | 检查 作品 根目录，**入口先跑源新鲜度自检**（`source_check.py`：比对 `小说/<剧>.txt` 与 `小说/_源指纹.json`，写小说成品更新→列出变动章/受影响集/是否触及已生产集，提示同步+重切，重切每次确认不自动），读 `_进度.md`，路由到下面的阶段 |
| 1 剧本改编 | `n2d-script` | 拆集 + 精修前 5-10 集窗口复核边界 + 配音台词/BGM/封面/角色场景卡/global_style |
| 2 配音 | `n2d-voice` | voiceover.txt → 角色配音 + 拼接音轨 + 时长清单.json（驱动下游镜头时长）；macOS say 中文空音频时自动降级静音占位并醒目告警 |
| 3 分镜设计 | `n2d-script` | 配音后回跑：按实测时长生成分镜剧本/故事板/素材清单/字幕/镜头时长 |
| 4 出图 | `n2d-image` | 两层出图 prompt（定妆库 + 本集分镜）→ 每次重扫本机生图能力，Codex/OpenAI/Gemini/Flux/ComfyUI 等优先，Dreamina/即梦兜底 |
| 5 出视频 | `n2d-video` | 由故事板生成每 Clip 视频 prompt → 即梦/可灵/Veo/Seedance 图生视频 |
| 6 合成 | `n2d-compose` | 拼 视频 clips + 配音 + BGM + 烧双语字幕 → 成片 |
| 质检·自审（横切） | `n2d-review` | 双模 QA：①作品质检（崩脸/字幕错位/音画/节奏/合规，机检+人判，出定位报告）②流程自审（联网对标→审 skills+Q&A→出优化建议）。非必经阶段，任意闸门或成片后可跑 |
| 进度·下一步（横切·只读）| `n2d-progress` | 扫 `制漫剧/<剧名>/_进度.md` 逐集矩阵 → 压缩出每部剧完成度 + 生产前沿（下一步该跑哪个 n2d skill）+ 次要缺口，给可一键继续的建议；出图/视频/成片/配音等花钱·不可逆·合规步骤先提醒确认。**只读·不改文件·不碰其它三条线**。脚本 `scan.py` 纯标准库。触发词：进度 / 当前进度 / 下一步 / 还差什么 / progress / check |

> **选择点 `制作模式`（出片顺序）**：默认 `配音先行`（真实配音时长驱动镜头，音画准·返工少）。另支持 `先出视频后配音`（**快速 demo·不推荐**：镜头时长靠估算锁死，后期补真音对不上 → 音画不同步/可能重切重出视频）——仅纯视觉 demo/比稿用，各阶段入口会复述不推荐理由并放行占位闸门。两种流程图 + 完整理由见 `novel2drama/SKILL.md`「制作模式」节；选择点定义见 `_偏好约定.md`。

> **仙侠武侠打斗专项工艺**：`n2d-script/references/打斗分镜.md`（五帧拆招/命中帧出图/首尾帧锁动作/后期补打击感），已挂接 script/image/video/compose/review 全链；总纲见 `novel2drama/Q&A.md` Q31。
> **仙侠非打斗奇观工艺**：`n2d-script/references/仙侠场面分镜.md`（御剑飞行/追逐/渡劫突破/炼丹炼器/大阵法阵/大场面 establish/斗法对轰/神魂(神识·元神出窍·夺舍)——飞行追逐锁姿态动背景、渡劫炼丹法阵对轰爆发帧出图+元素入库、神魂元神=肉身半透明派生治"二我"、大场面三镜由远及近），同样挂接全链；总纲见 `novel2drama/Q&A.md` Q33。
> **资产库题材自适应**：共享定妆库通用三类（角色/场景/道具）+ ⚙️仙侠玄幻可选两类（**法宝/特效**，本命法宝按形态多态、剑气/光效锁颜色拖尾）；**视图按题材自适应**——打斗/追逐/转身/过肩多的题材角色补**背面凑正侧背三视图**，多集核心场景按机位补**场景多视图（四视图）**保跨镜背景自洽；见 `n2d-image/references/prompt_format.md §1`+`角色一致性checklist.md`、`Q&A.md` Q32。
> **模型矩阵（防过期快照）**：各轴 SOTA vs n2d 默认 vs 升级触发（含图/视频/配音 + **口型 lip-sync**：MuseTalk 首选/Wav2Lip/LatentSync；配音情绪解耦 IndexTTS-2），见 `novel2drama/references/模型矩阵.md`，由 `n2d-review` 流程自审每次刷新——版本名只活在带日期的快照里，正文写能力不绑版本。
> **单 Clip 上限按后端（非一刀切 8s）**：`n2d-video/references/platforms.md`「单 Clip 上限铁律」按后端定上限（即梦 image2video≤8s / Seedance 2.0≤15s / 可灵多镜 / Veo≈8s），`n2d-script` 阶段2 拆 Clip 读该值——能一镜到底就别切碎（更少拼接缝·跨镜更稳）。
> **clip 衔接接力链（治"剪起来跳"·横切全链）**：clip 间顺滑是一条逐级继承的接力链，单一真值源在 `n2d-script`。① `n2d-script` 在 `故事板.md`/`storyboard.json` 把每个接缝写成契约：`上一 Clip 出点 = 下一 Clip 入点`（同一句）+ `转场类型` + `需要尾帧?`（见 `references/formats.md §4`）。② `n2d-image` 在标 `需要尾帧` 的接缝出**尾帧 PNG `镜头N_end.png`**（=下一 Clip 首帧构图）。③ `n2d-video` **读取**契约不重写 start_state、有尾帧用首尾双帧引导焊接点。④ `n2d-compose` 按 `转场类型` 接 clip（有意硬切硬切/跳变微溶解/缺空镜报警），不盲拼。⑤ `n2d-review` 逐接缝并排读图查跳切/闪烁/接力断链。**MV 线同构但卡点优先**：契约源在 `mv-video` clip 表（`出点=下一入点` + `转场` + `需要尾帧?`，单一真值踩 `mv-beat` 的 beatgrid downbeats 定切点）；默认**卡点硬切**、靠"视觉身份一致+卡点准"接缝，尾帧接力仅**同段落·非卡点切·连续镜**可选（`mv-image` 出 `_end.png`、`mv-video` 双帧引导）。`mv-compose` 按 `转场` 接（卡点硬切硬切/跳变微溶解/缺空镜报警），`mv-review` 逐接缝查跳切——但**副歌卡点切的有意跳变不算问题**（容差比 n2d 宽）。
> **定妆变更影响扫描**：改了共享定妆资产后，`n2d-image/scripts/asset_impact.py <作品根> <资产名>` 列出引用它的下游镜头（已出图的需重出），属 `n2d-review` 机检家族；兼容两种 prompt schema。
> **一致性梯子（出图）**：①参考图派生（默认）→ **②后端原生角色ID/主体**（可灵主体库 / Seedream Universal Reference / Sora Cameo·注册一次按 ID 引用·opt-in·先于 LoRA 用尽）→ ③LoRA。能力对照见 `n2d-image/references/platforms.md`「后端原生角色ID / 主体库」，opt-in 流程见 `n2d-image/SKILL.md` 同名节；后端无持久 ID 自动回退第①档。

## 二、novel ——「写小说」创作工坊

`novel-author` 是总调度（与 `novel2drama` 同构），按输入（几个字/想法/书名/URL/路径/配角名/扩缩/审稿/评分）路由到下面的子 skill；指向已有 `写小说/<项目>/` 且有 `_进度.md` 时，先读它续跑未完成阶段。与 novel2drama(制漫剧·`制漫剧/`) 平行：这条线做**纯文本小说**，**产物统一落 `写小说/<项目>/`**，成稿后可交 novel2drama 改编漫剧。

| Skill | 职责 |
|---|---|
| `novel-author` | 顶层分派器：看输入 / 读 `写小说/<项目>/_进度.md`，路由到下面的子 skill，**自身不写作** |
| `novel-create` | **原创从零·访谈引导**：只有几个字/想法/部分风格/碎片时，访谈→创作蓝图→设定圣经→章纲→Demo→成书（家族里唯一从零生成，其余都需既有源） |
| `novel-title` | 头脑风暴 5–8 个书名候选，5 维打分排序 |
| `novel-fetch` | 按书名/章节目录 URL 联网抓公版小说全文 → txt + docx |
| `novel-craft` | 写作工艺共享库（章纲编织/单章守则/扩写/精简/**设定圣经统一 schema**）+ **共享脚本 `scripts/`**（`export.py` 通用导出器：章节 md→txt/docx/大纲/n2d 含续写合本；`derive_common.py`：派生类 init 共用的 docx→txt/版权判定/落 `_设置.md`），被其他 novel-* 按路径引用 |
| `novel-expand` | 短篇 → 长篇：在保留事件骨架前提下加细节 |
| `novel-condense` | 长篇 → 短版：砍描写/支线/重复内心戏，并章 |
| `novel-continue` | 续编（完本后写续集）/ 接更（接未完本往后写） |
| `novel-rewrite` | 改写/魔改/翻拍：改主线、加原创设定的转化型重写 |
| `novel-spinoff` | 配角平行视角外传，锚点处锁定原作事件 |
| `novel-review` | 双模 QA（与 n2d/mv/song-review 同构）：①作品质检（串视角/人设崩/设定矛盾/锚点漂移/原文照搬，机检+人判，出定位报告，判"写得对不对"）②流程自审（联网对标→审 novel-* + novel-craft→出优化建议）。机检 `mechanical_check.py` 带 pytest |
| `novel-score` | 市场+品质评分体检：联网拉红果/抖音/番茄当下热榜对标，多维打分→总分+档位+「过/小改/大改/弃稿重立」判定+改写ROI（判"值不值得做、能不能火"） |

## 三、song ——「写歌」创作线（词 + 曲 + 演唱 → 成品歌）

`song` 是总调度，从主题/几个字/曲风 → 一首带人声的成品歌。与 novel-author(写小说) 平行的创作线；产物落 `写歌/<曲名>/`（`词/lyrics.md` + `歌/song.wav`），交给 制MV(mv) 做视频。

| Skill | 职责 | 状态 |
|---|---|---|
| `song` | 写歌总调度 | ✅ |
| `song-lyrics` | 访谈式作词 + 作词工艺知识库（结构/押韵/字数贴旋律/hook），**零安装** | ✅ |
| `song-compose` | 词→带人声的歌：云 Suno / 本地 ACE-Step(Mac可跑) / DiffRhythm | ✅ |
| `song-cover` | 翻唱/换声：RVC / so-vits-svc | ✅ |
| `song-review` | 双模 QA：①作品质检（词可唱性/押韵/hook/结构 + 曲演唱试听清单 + 音频削波/静音/采样率 + 音色合规，机检+人判，出定位报告）②流程自审（联网对标→审 song skills→出优化建议）。非必经阶段，作词/作曲后或交 mv 前可跑 | ✅ |

> 唱歌的声音要装东西：TTS（CosyVoice/FishSpeech）不能唱；唱歌走音乐生成模型(Suno/ACE-Step)或歌声转换(RVC)。**克隆真人嗓需授权（2026 opt-in）。**

## 四、mv ——「制MV」生产线（成品歌 → AI 音乐 MV 视频）

`mv` 是总调度，**输入 = 一首已做好的歌**（来自 写歌/ 或用户给），产物落 `制MV/<曲名>/成片_MV.mp4`。与 novel2drama(制漫剧) 平行：**写歌→制MV**，正如 **写小说→制漫剧**。**完全独立、自包含——不复用 n2d-* 或任何家族 skill**。

| 阶段 | Skill | 职责 | 状态 |
|---|---|---|---|
| 调度+立项 | `mv` | 扫 制MV 根，拷入歌+词，定视觉蓝图，路由 | ✅ |
| 卡点 | `mv-beat` | librosa 检测 BPM+鼓点 → beatgrid | ✅ |
| 出图 | `mv-image` | mv 自建：共享定妆 + 分段分镜 PNG | ✅ |
| 出视频 | `mv-video` | mv 自建：图生视频（按段落+卡点） | ✅ |
| 卡拉OK字幕 | `mv-lyric-sync` | whisperx 词级对齐 → karaoke.ass | ✅ |
| 合成 | `mv-compose` | 歌轨 + 卡点剪辑 + 卡拉OK烧录 → 成片_MV.mp4（自带 mv_compose.sh + render_lyrics.py） | ✅ |
| 质检·自审（横切） | `mv-review` | 双模 QA：①作品质检（视觉一致性/卡点节奏[clip 对齐 beatgrid·不等长]/卡拉OK字幕越界·对账/音画合成[成片时长·画幅·音轨]/换脸合规，机检[+ffprobe]+人判，出定位报告）②流程自审（联网对标→审 mv skills→出优化建议）。非必经阶段，任意闸门或成片后可跑 | ✅ |

> 独立铁律：mv-* 即便与 n2d 逻辑相似也各写各的；只用通用外部工具（非 skill）。
> 输入歌本身的音质/词体检属 `song-review`，mv-review 不重复——只审歌轨进没进、卡点对不对。

## 公共能力（不属任何家族，谁都能调）

| Skill | 职责 |
|---|---|
| `video-faceswap` | 通用**视频**换脸（FaceFusion，Mac可跑）+ 强制 AI 标识（打标调公共 `watermark`）；**仅本人/授权/合成脸**，带合规闸门。制MV/制漫剧/单独使用都可调 |
| `image-faceswap` | 通用**图片**换脸（同 FaceFusion 底座，单图秒级）+ 强制 AI 标识（打标调公共 `watermark`）；**仅本人/授权/合成脸**，带合规闸门。出图阶段/单独使用都可调 |
| `watermark` | 通用**水印**（图/视频同一工具，按扩展名自动判定）：①合规 **AI 标识**（法律强制·可见提示+元数据·**只加不去**）②**品牌/logo/账号**水印（文字或 logo·位置/透明度/大小可选）。faceswap 打标 + n2d/mv 合成阶段 + 单独使用都可调；Pillow+ffmpeg，无 libass 走 overlay |

> 换脸/克隆真人 = deepfake，2026 强监管：须**肖像同意 + AI 标识水印**（中国《标识办法》、US DEFIANCE/NO FAKES）；video-/image-faceswap 已内置合规闸门，仅本人/授权/合成脸，且强制打标。两者共用同一 FaceFusion 安装；**打标统一调公共 `watermark` skill**（图/视频同工具，原 label_watermark*.py 已合并进去）。`watermark` 还能打品牌/账号水印（`--mode brand`），但**绝不**提供去水印。

---

> 四条线两两对应、**互不依赖**：**写小说→制漫剧**、**写歌→制MV**。创作线产成品（小说/歌）→ 生产线做视频（漫剧/MV）。衔接只在成品文件层面，不是 skill 依赖。换脸是公共 `video-faceswap`（视频）/ `image-faceswap`（图片）。
