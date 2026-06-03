# Skills 索引

本项目的自定义 skills 分两大家族。**目录保持扁平**（每个 skill 仍是 `.claude/skills/<name>/SKILL.md`）——
skill 之间用 `<skills>/<name>/...` 互相引用，故**不要**移进子目录，否则交叉引用与 skill 发现会失效。
本文件仅作分类说明。

---

## 一、n2d ——「小说 → AI 漫剧/短剧」生产管线

`novel2drama` 是总调度，按 `_进度.md` 把用户路由到对应阶段 skill。阶段顺序：

| 阶段 | Skill | 职责 |
|---|---|---|
| 调度 | `novel2drama` | 检查 作品 根目录，读 `_进度.md`，路由到下面的阶段 |
| 1 剧本改编 | `n2d-script` | 拆集 + 配音台词/BGM/封面/角色场景卡/global_style；配音后回跑做分镜设计 |
| 2 配音 | `n2d-voice` | voiceover.txt → 角色配音 + 拼接音轨 + 时长清单.json（驱动下游镜头时长） |
| 3 出图 | `n2d-image` | 两层出图 prompt（定妆库 + 本集分镜）→ 即梦/gemini/DALL-E/Flux 生图 |
| 4 出视频 | `n2d-video` | 由故事板生成每 Clip 视频 prompt → 即梦/可灵/Veo/Seedance 图生视频 |
| 5 合成 | `n2d-compose` | 拼 视频 clips + 配音 + BGM + 烧双语字幕 → 成片 |

## 二、novel ——「写小说」创作工坊

`novel-author` 是总调度，按输入（几个字/想法/书名/URL/路径/配角名/扩缩需求）路由到下面的子 skill。

| Skill | 职责 |
|---|---|
| `novel-author` | 顶层分派器，只路由不写作 |
| `novel-create` | **原创从零·访谈引导**：只有几个字/想法/部分风格/碎片时，访谈→创作蓝图→设定圣经→章纲→Demo→成书（家族里唯一从零生成，其余都需既有源） |
| `novel-title` | 头脑风暴 5–8 个书名候选，5 维打分排序 |
| `novel-fetch` | 按书名/章节目录 URL 联网抓公版小说全文 → txt + docx |
| `novel-craft` | 写作工艺共享库（章纲编织/单章守则/扩写/精简），被其他 novel-* 按路径引用 |
| `novel-expand` | 短篇 → 长篇：在保留事件骨架前提下加细节 |
| `novel-condense` | 长篇 → 短版：砍描写/支线/重复内心戏，并章 |
| `novel-continue` | 续编（完本后写续集）/ 接更（接未完本往后写） |
| `novel-rewrite` | 改写/魔改/翻拍：改主线、加原创设定的转化型重写 |
| `novel-spinoff` | 配角平行视角外传，锚点处锁定原作事件 |
| `novel-review` | 审稿质检：串视角/人设崩/设定矛盾/锚点漂移/原文照搬，出定位报告 |

---

> 两家族的衔接：novel 工坊产出的小说成稿，可作为 n2d 管线 `n2d-script` 的输入，进入漫剧生产。
