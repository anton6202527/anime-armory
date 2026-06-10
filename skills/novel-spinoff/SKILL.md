---
name: novel-spinoff
description: Given a source novel (.txt/.docx) and the name of a side/支线 character in it, write a parallel-POV spin-off novel from that character's perspective — locked to the source's events at anchor points, otherwise free. Defaults to public-domain / user-owned / user-licensed source novels and refuses copyrighted contemporary web novels without an explicit rights declaration. Outputs full text (txt + docx), chapter outline (md), and an optional n2d-script-friendly skeleton ready for the AI 漫剧 pipeline. Use when asked to 同人, 外传, 配角视角, 换视角写, 平行视角, 重写视角, write spin-off, POV rewrite, parallel POV. Triggers 同人, 外传, 视角续写, 配角视角, 平行外传, 分叉外传, spin-off, POV rewrite, fan fiction (own work / public domain only).
---

# novel-spinoff — 从配角视角写外传

给定**原作小说**（公版 / 自有 / 用户已声明授权）+ **该原作里的某个配角名**，产出一部从该配角视角写的新小说。

支持三种时间线关系：
- **并行外传**（default）—— 和原作同一段时间，看同一批事件的"另一面"，原作中该角色出场的每一幕都是必须对齐的硬锚点。
- **续接后传** —— 原作结束之后该角色的故事，自由度最大但需要为原作结局接一个钩子。
- **分叉外传** —— 在原作某节点分叉，该角色走另一条路（用户指定分叉点）。

输出（可多选）：txt + docx 全文 / 章节大纲 md / n2d-script 友好的 `脚本/第N集/raw.txt` 目录结构。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**，按 `../_偏好约定.md`（家族统一的偏好读写机制 + 全部选择点目录与缺省）解析：`<作品根>/_设置.md` → 全局默认 `创作偏好-默认.md` 预填并告知一句 → 缺则**首次问一次**→写回 `_设置.md`→**沉默沿用**（合规/不可逆/花钱点每次仍确认）。

本 skill 涉及的选择点：`目标平台`、`权利来源`、`输出格式`、`篇幅档`、`小说生成模式`、`章节生成粒度`、`AI使用披露`。

## 合法性铁律（不可逾越）

家族统一铁律（公版 / 自有 / `--i-have-rights` + provenance 留痕；判公版标准）见 `novel-author/SKILL.md` 合法性继承。本 skill 是家族里**最严**的一档，特有红线：
- 同人是法律灰色区，**比 novel-fetch 更严**：派生作品是原作版权人专有权利。当代受版权网文/出版物 → **直接拒做**，即使非商用、不发布也不行；拥有阅读权 ≠ 改编权。
- **遇到当代网文不要"读了再说"**——读了再写派生 = 绕铁律一圈。直接拒做，引导改用公版（《晋书》《史记》《聊斋》《封神》《镜花缘》等）或用户自有/已授权作品。
- **外传写作中不大段复刻原作原文**：对话/动作可**复述**不可整段照搬；锚点对齐靠**事件骨架**而非文本搬运（工艺 + 法律边界）。

## 工作流（八步）

总览：**0** 确认输入 → **1** 建骨架 → **2** 设定三卡 → **3** 书名候选 → **4** 章纲 → **5** Demo + 用户审 → **6** 写余下章节 → **7** 回扫 → **8** 导出。

每个**用户审核 gate**：第 0 步、第 2 步末（设定）、第 3 步末（书名）、第 4 步末（章纲）、**第 5 步末（Demo 三章）——这是最重要的 gate**、第 7 步末（回扫报告）。任何 gate 没过，不进下一步。

> **派生流水线**：阶段表 + demo_gate / draft_packets / 状态账本 / export / ai_usage 的通用机制见 `novel-craft/references/derive-pipeline.md`。本 skill 的 `source_model` = 锚点/角色/世界观，`direction_spec` = 时间线关系/分叉点确认。

### 第 0 步 — 确认输入三件套 + 合法性

跟用户确认（缺省即用默认）：
- **原作路径**：`.txt` 或 `.docx`；若没有先用 `novel-fetch` 抓公版。
- **配角名 + 简短描述**：用户用一句话告诉你"这是谁"。
- **时间线关系**：并行 / 续接 / 分叉（分叉需指定原作第几章/什么节点起分叉）。
- **规模**：short / medium / long / 微短剧 / 漫剧（见 `novel-craft/references/split.md`；必要时用 `--target-chapters` 覆盖章数）。
- **目标平台**（第 3 步书名候选要用）：起点 / 晋江 / 抖音漫剧 / 番茄 / 红果 / 历史向 / 跨平台。
- **输出形式**（可多选）：txt+docx 全文 / 大纲 md / n2d-script 目录结构。

判合法性：原作版权状态。**当代受版权 → 拒做并退出**。公版 / 用户自有 / `--i-have-rights` → 继续。

### 第 1 步 — 建项目骨架

```bash
python3 <skill>/scripts/init_project.py "<原作路径>" \
  --character "<配角名>" \
  --mode parallel|sequel|branch \
  --scale short|medium|long|微短剧|漫剧 \
  [--target-chapters N] \
  [--branch-point "第N章"] \
  [--draft-mode 稳妥初稿] [--chapter-granularity 逐章] [--ai-text-usage AI-assisted] \
  [--out <输出根>] \
  [--i-have-rights]
```

落点 = `写小说/<原作名>-<配角名>外传/`（可 `--out` 改）。目录骨架（`设定/{角色卡,世界观,锚点表.json,书名候选,章纲}` + `章节/` + `导出/` + `_meta.json` + `原作.txt` + `_进度.md`）完整结构见 `references/formats.md`。

脚本只做确定性活：建目录、抽 docx → txt、用正则把"明显提到配角名"的章节段落粗筛进 `锚点表.json` 的 `candidates` 字段（待第 2 步精筛）。LLM 判断由主对话的当前 agent 接管。

### 第 2 步 — 建设定（人 / 世 / 锚）三卡

> 角色卡 / 世界观按家族统一 schema `novel-craft/references/setting-bible.md`（与 create/rewrite 同字段，含首现章/复用范围/代价三列）；锚点表是 spinoff 专属，见 `references/timeline-anchoring.md`。

由主对话执行（不是脚本）。**这是整部外传质量的天花板，必须做扎实。**

1. **锚点表精筛** —— 打开 `锚点表.json`，逐个 candidate 段落判断：
   - 是真出场（有动作/对话/视角带过 → `anchor`）还是仅被提及（别人嘴里说了一下 → `mention`）。
   - 真出场的标注：原作章节号 / 关键事件 / 该角色的状态 / 对话要点 / 在场其他角色 / 已知情报 / 未知情报。
   - 这一表是**整部外传的硬约束**：新文里该角色在对应时间点的状态/位置/已知情报必须和锚点一致。
   - 详见 `references/timeline-anchoring.md`。

2. **角色卡** —— 填 `设定/角色卡.md`：
   - 外观、出身、能力体系、性格底色、动机 / 心结 / 渴望、和原作主角的关系（爱/恨/敬/惧/敌/友）、说话习惯。
   - **关键**：原作里这个角色被作者**留白**的部分（动机模糊、行为突兀、消失的几章 等），列成一张"留白清单"——这是外传的发力点。

3. **世界观卡** —— 填 `设定/世界观.md`：
   - 从原作摘核心规则（修炼体系/魔法规则/政治格局/地理 等），**只摘已确立的**，不要在外传里发明新规则去推翻原作。

4. 报告给用户：锚点数、留白点数、几条候选支线。**用户审过 → 进第 3 步**。

### 第 3 步 — 书名候选 + 平台对位评分

**委托给 `novel-title` skill 执行**。本步骤是 novel-title 的标准用法：

- 传入 `_meta.json.spinoff_character`、`_meta.json.target_platform`、第 2 步建好的设定卡摘要（类型 = 同人外传 / 修真等）、用户可能给过的暂定名。
- novel-title 走它自己的流程（5–8 候选 / 5 维评分 / 推荐 / 用户选）。
- novel-title 回写本项目 `_meta.json.title` 与 `设定/书名候选.md`。

详细评分规则、各平台命名习惯、配比要求详见 `skills/novel-title/references/title-patterns.md`。

用户选定后：
- 确认 `_meta.json.title` 已被 novel-title 回写。
- 在本项目 `_进度.md` 把"书名"勾上。
- **用户审过 → 进第 4 步**。

### 第 4 步 — 章纲表

由主对话执行。打开 `设定/章纲.md`，按规模写出每章一行 outline：

```markdown
# 章纲 — 《<选定书名>》

## 总体弧线
（三幕结构 / 关键转折点 / 最终目的地，一段话）

## 锚点-章节映射
- 锚点 A（原作第 3 章，X 与主角初遇）→ 本作第 5 章前后
- 锚点 B（原作第 7 章，X 救场）→ 本作第 12 章
...

## 逐章
- 第 1 章 《标题》 — 主线事件 / 关键转折 / 涉及锚点（若有） / 视角情绪 / 钩子
- 第 2 章 ...
- ...
```

要求：
- 每个锚点至少有一章覆盖（节奏上可以放在锚点前的"赴约章"或锚点后的"复盘章"）。
- 章节之间情节要有递进，不能流水账。
- 三幕结构（约 1:2:1 章数分配），中段必须有一次大反转。
- **总章数 / 字数分档先按 `skills/novel-craft/references/split.md` 反推**（按 `_meta.json.target_platform` 选档）——抖音漫剧友好通常 70-100 章，网文长篇 12-20 章，差一个量级。
- 章纲编织（三幕 / 锚点织网 / 钩子）详见 `skills/novel-craft/references/outline.md` + 本 skill 的 `references/workflow.md`。

写完让用户确认，可改。**章纲未敲定前不要进第 5 步 Demo**。

### 第 5 步 — Demo（前几章）+ 用户审【最重要 gate】

**不在敲定章纲后立刻写全本**——先写**前几章 Demo** 让用户验文风、视角、节奏、锚点对齐。Demo 通过才进第 6 步写完整本。

**Demo 章数**（按规模）：
- 长篇 / 微短剧 / 漫剧 → 前 **3 章**
- 中篇 → 前 **2 章**
- 短篇 1–3 章 → 直接整本，跳过 Demo 步（短篇本身就是 demo 量级）

写法同第 6 步逐章生成（见下），但**每章独立**写完后**主对话立即停下**贴给用户看，不要一口气写完三章再说。这样用户在第 1 章就能发现问题（视角错 / 口吻不对 / 锚点没对上 / 文风偏），避免错误传染到后两章。

Demo 审核 checklist（贴给用户的时候带上）：
- [ ] **视角**：通篇是不是该配角的视角？有无穿帮（写到他不在场的事/别人内心）？
- [ ] **口吻 / 人设**：说话和做事像不像原作里这个人？OOC 吗？
- [ ] **锚点对齐**：本章涉及的锚点是否对齐了事件骨架？有没有大段照搬原文？
- [ ] **文风**：句长、修辞密度、段落节奏，是不是你想要的？
- [ ] **节奏**：开头钩子够不够、结尾留没留下章想看的东西？
- [ ] **私货密度**：有没有"原作没说的东西被你说了"？

用户给 fix 意见 → 在 Demo 章里 Edit 修改 + 把意见沉淀到 `设定/角色卡.md` "口吻习惯"段或 `references/pov-craft.md` 项目本地副本里，作为后续章节的隐式指南。**返工后再次给用户审**。

> **可选市场体检（批量前最便宜的 go/no-go）**：Demo 过审后，可对 Demo 章跑一次 `novel-score`（"配角外传题材/开篇钩子够不够火、值不值得写满 N 章"）——在投入批量写作前用最低成本验证方向。题材冷/开篇弱时改 premise 比写完 80 章再发现划算得多。用户说"先确认能不能火"尤其要跑。
> **机器留痕（必做）**：Demo 审完写 `审稿/demo_gate.json`（见 `novel-craft/references/demo-gate.md`）。`status != passed` 不进第 6 步；后续逐章 prompt 必喂 `style_anchor`、`reader_promises`、`setting_constraints`。

**Demo 通过 → 进第 6 步**。

### 第 6 步 — 写剩余章节

先读 `novel-craft/references/draft-pipeline.md`，再由主对话调度。每一章先生成任务包，再拆给一个子任务 / 子代理写。这样可以保护主对话上下文，长篇也撑得住。

```bash
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --next
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --range 4-8
```

每个任务包 / 子代理 prompt 必含：
- 设定卡三件套全文（角色卡 + 世界观卡 + 锚点表精筛后的部分）
- 章纲表全文（让子代理知道前后章在干嘛）
- **本章 outline**
- **本章涉及的锚点**（如果有）+ 原作对应段落的事件骨架（不是原文复制）
- 上一章末尾 ~500 字（衔接）
- **Demo 章作为口吻样本**（贴 demo 第 1 章全文进 prompt，让子代理对齐 demo 已定调的文风）
- **`审稿/demo_gate.json`**（机器留痕里的文风锚点 / 读者承诺 / 禁止漂移项）
- 写作守则（来自 `references/pov-craft.md`）：第几人称 / 不要 OOC / 不大段复刻原作 / 视角一致性

子代理输出 = 一份 markdown 文件，写到 `章节/第NN章.md`。**单章目标字数**：漫剧 1000-1500 字/章，微短剧 1500-2500，中篇 3000-5000，长篇 5000-8000，短篇 6000-10000。
写完后填写 `审稿/state_delta_第NN章.json`，把人物状态、锚点兑现、伏笔新增/回收合并进 `审稿/state_ledger.json`。

**调度建议**：
- 章和章之间有强依赖（前一章末尾喂下一章开头），不能完全并行。但可以 2-3 章为一组顺写，组与组之间靠章纲衔接。
- 每写完一组（如 5 章），跑一次第 7 步的轻量一致性扫描，再决定是否继续。

主对话每章写完后：
- 更新 `_进度.md` 把该章勾上。
- 短报告：第 N 章 ✓，字数 X，涉及锚点 Y。

### 第 7 步 — 一致性回扫（交 `novel-review` 跑，别手搓）

回扫的机检 + 维度清单已由 `novel-review` **通用化、独立化**（它本就把本步抽出来做成家族通用 QA）。本步**直接调 `novel-review`**，不再在主对话手写一套回扫：

```bash
# 机检：原文照搬(对 原作.txt) + 视角"我"泄漏 + 章号/标题对账 + 术语漂移
python3 skills/novel-review/scripts/mechanical_check.py "<作品根>" --pov "<配角名>" --terms "<规范术语逗号分隔>"
```

- **轻量**（每组 5 章后）：跑机检 + LLM 抽查近章口吻/术语/伏笔，问题就地改。
- **全量**（全部写完后）：机检后按 `novel-review` 模式① 维度逐章人判——**锚点对齐**（每个锚点对原作骨架：事件/时间/在场人/已知情报）、伏笔回收、第 2 步"留白清单"是否给答案、文风一致（抽 3-5 章比口吻）、原文照搬。
- 发现问题的章节直接 Edit 修改，**不要重写整章**除非伤筋动骨；阻断级回 spinoff 重写该章。

### 第 8 步 — 导出三种形态

```bash
python3 skills/novel-craft/scripts/export.py "<作品根>" \
  --formats txt,docx,outline,n2d \
  [--title "<书名>"]   # 家族通用导出器（原 spinoff/scripts/export.py 已上移至 novel-craft 共用）
```

`--title` 缺省读 `_meta.json` 的 `title` 字段（第 3 步选定），再缺省才回退到 `<原作名>-<配角名>外传`。

脚本干活：
- `章节/第NN章.md` 合并 → `导出/<书名>.txt`（与 novel-fetch 同款格式：provenance 头 + `第N章 标题` 行 + 段落正文）。
- 同源 → `导出/<书名>.docx`（章标题 Heading 1）。
- 章纲表 → `导出/大纲.md`（清版，给读者看）。
- `--formats` 含 `n2d` → 在 `导出/n2d-script/` 下铺出 `小说/<书名>.docx` 等待 n2d-script 处理。

报告：四个产物路径 + 锚点对齐报告 + 总字数。完工。

## 输出约定

- 默认作品根 = `写小说/<原作名>-<配角名>外传/`；用 `--out` 可改。
- 三种最终产物都进 `导出/`；中间产物（章节 md / 设定卡 / 锚点表 / 书名候选）保留在作品根，方便用户复盘和二次修改。
- 详见 `references/formats.md`。

## 何时不用本 skill

- 写**完全原创**小说（无原作 / 无配角锚定）→ 不需要本 skill 的锚点机制，走 `novel-create` 或当前 agent 的原创写作流程。
- **改写原作主线**（不是配角视角，是想把主角故事重写一遍）→ 不在本 skill 范围；这是"翻拍"不是"外传"。
- 原作还没拿到 → 先跑 `novel-fetch`。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 拿当代受版权网文做配角外传 / "先读了再说只总结" | 拒做（读了再写派生=绕铁律一圈）；引导改用公版（《晋书》《史记》《聊斋》《封神》等）或用户自有/已授权 |
| 跳过锚点表直接写 | 并行外传必出 OOC / 时间线漂移；锚点表是外传的硬地基 |
| **跳过 Demo 直接写满本** | 最致命错误。视角/口吻/锚点对不对 1 章就能看出；写满才发现要重来沉没成本极高。且 Demo 须逐章独立审（第 1 章错的口吻会传染后两章） |
| 章纲没和用户确认就开写 Demo | 章纲是 Demo 的前置；第 4 步必须用户点头 |
| 一次性把全本塞进主对话写 | 逐章拆给子任务/子代理（跑 `draft_packets.py`），把 Demo 第 1 章 + `审稿/demo_gate.json` 塞进 prompt 锚定文风 |
| 锚点章节大段复刻原作原文 | 用事件骨架对齐，不搬文本；既是工艺也是法律边界 |
| 在外传里"修正"原作设定 | 设定只能扩展不能推翻；想推翻就改用"分叉外传"模式 |
