---
name: novel
description: Top-level dispatcher for the novel-* skill family — inspects an open-ended novel request (a bare idea / few words / book name / URL / dragged file path / spin-off character / expand·condense·rewrite / 审稿查硬伤 / 评分·能不能火) and routes to the right sub-skill, imports a dragged novel file/link into 写小说/<项目>/ when no action is specified, or resumes an in-progress 写小说/<项目>/ from its _进度.md. Use when the user gives a novel-related task without specifying which tool. Does not write novels itself — only routes/imports source material; the canonical sub-skill roster is the routing table in the body. Triggers 小说工坊, novel, 小说相关任务, 拖进一本小说, 导入小说, 帮我处理小说, 不知道用哪个小说 skill, 小说打分, 小说评分, 能不能火, 值不值得改, 审稿, 小说进度, novel-progress.
---

# novel — 小说工坊调度入口

不直接写小说，**读取用户输入 → 路由**到 novel-* 家族最合适的 sub-skill。

和已存在的 `n2d` 平行：那条线管漫剧/视频生产、产物落 `制漫剧/`；这条线管纯文本小说生产、**产物统一落 `写小说/<项目>/`**（如 `写小说/仙界闭关小能手-王敦外传/`）。两条线在 novel-fetch（取材）和 novel-spinoff/expand 的输出处自然衔接——`写小说/` 里的成品可交给 `n2d` 改编，产物再流向 `制漫剧/`。

**本系列成员**见下方"路由规则"表（家族唯一权威名册；新增/移除子 skill 只改那张表）。

## 偏好（私有 · 用户选择，不写死在本 skill）

本 skill 的可选项**不写死在源码里**。按 `../skills/novel-craft/references/选择点与偏好.md` 读用户私有选择：先读 `<作品根>/_设置.md`；缺则用全局默认 `创作偏好-默认.md` 预填并告知一句；再缺则**首次问一次**→写回 `_设置.md`→同项目之后**沉默沿用**（合规/不可逆/花钱多的点每次仍确认）。

本 skill 涉及的选择点：`目标平台`、`权利来源`、`权利辖区`、`发行地区`、`输出格式`、`篇幅档`、`小说生成模式`、`章节生成粒度`、`AI使用披露`。

> 作为入口：路由到子 skill 前，若已有项目则读其 `<作品根>/_设置.md`，新项目按全局默认初始化。

## 路由规则

> 机器校验源：`novel-craft/scripts/registry.py`；测试会校验它与本表、`skills/README.md`、磁盘目录一致。

| 用户输入形态 | 路由到 |
|---|---|
| **只有几个字 / 一个想法 / 部分风格 / 零散笔记 / 半成品片段**，没有成型源文 → 要写一本**原创新书** | `novel-create`（访谈→蓝图→设定→章纲→Demo→成书） |
| 拖进来一本**本地小说文件/目录/file:///URL**，但没说下一步动作，只是要先建档 | `novel/scripts/import_novel.py` → `写小说/<书名>/` |
| 给了**书名 / 作者 / URL**，明确要把公版书"取回来" | `novel-fetch` |
| 已有原作 + 想**起一个好书名** | `novel-title` |
| 已有原作 + 指定一个**配角名**，要**视角续写**（POV 切换、事件锁定） | `novel-spinoff` |
| 已有原作 + 要**改主线 / 换设定 / 加原创材料**（魔改 / 重构 / 翻拍 / 二创重写） | `novel-rewrite` |
| 已有原作 + 要**接着末章往后写新章节**（时间向前推） | `novel-continue` |
| 已有一段较短的文本，要**扩写章节内细节**（时间不动 / 加厚） | `novel-expand` |
| 已有长篇，要**压缩为短版 / 漫剧脚本量级** | `novel-condense` |
| 自己手写小说时要**工艺指南**（章纲 / 单章 / 扩 / 缩 / 续 的原则） | `novel-craft` |
| 已有在建项目，要看**当前进度 / 全线看板 / 下一步该跑哪个 skill** | `novel-progress` |
| 已写好若干章，要**质检 / 审稿 / 查问题**（人设崩 / 视角穿帮 / 设定矛盾 / 锚点漂移 / 题旨偏移 / 读者承诺违约 / 文学性变薄 / 节奏 / 原文照搬 / **五感缺失 / 伏笔逾期**） | `novel-review` |
| 已写好若干章，要**打分 / 评分 / 市场体检**（题材够不够热、能不能火、值不值得继续写/改、要不要弃稿重立） | `novel-score` |
| 已写好若干章，要**查逻辑硬伤 / 维护设定百科 / 角色生死状态 / 伏笔回收 / 关系温度** | `novel-wiki` |
| 已写好若干章，要**模拟读者反馈 / 测留存 / 找弃书点** | `novel-simulate` |
| 想要**提取授权样本/项目 Demo 的文风指纹 / 保持笔力一致 / 查文风漂移** | `novel-style` |
| 想要**分析情节节奏 / 画热力图 / 查注水 / 查断章** | `novel-balance` |
| 想要**宣发引流 / 写视频脚本 / 挖掘爆点章节** | `novel-promote` |
| 把小说改成**漫剧 / 短剧** | `n2d`（另一条管线） |

⚠️ **续 / 扩 / 视角 / 改 四者很容易混**：
- **续写** = 加**新章节**（时间向前推） → novel-continue
- **扩写** = 加**章节内细节**（时间不动 / 既有内容更厚） → novel-expand
- **视角续写** = **换 POV** 写同一段时间、**事件锁定不改** → novel-spinoff
- **改写** = **改主线 / 换设定 / 加原创材料**（事件可改、可新增设定，与视角续写正相反）→ novel-rewrite

⚠️ **QA 不是五个对等裁决，而是「3 个裁决 + 2 个分析仪」**（用户给"已写好的若干章 + 一个评估诉求"时按诉求**性质**分流）：

**裁决型（直接出结论，可入 gate）**
- **写得对不对**（人设崩/视角穿帮/设定矛盾/原文照搬/题旨偏移）→ `novel-review`（挑硬伤）
- **值不值得做 / 能不能火**（题材热度/爽点/留存/文学性 → 总分+判定+改写ROI）→ `novel-score`
- **读者会不会弃书**（模拟读者反馈、测留存、找弃书点）→ `novel-simulate`

**分析仪型（产出数据/台账，喂给上面的裁决，不单独当验收结论）**
- **逻辑/设定一致性 + 动态百科 + 伏笔台账**（角色生死、伏笔 planted→payoff 逾期、关系温度、设定自洽）→ `novel-wiki`。它是 `novel-review` 的一致性引擎（由 review 的 `consistency_audit.py` 一键串跑），也是 `设定/动态百科.json` 与 `设定/foreshadowing_ledger.json` 的权威存储。
- **节奏热力图**（注水、断章、高潮密集度）→ `novel-balance`；其「烂尾预警」读 `novel-wiki` 的伏笔台账回收率。

- 速记：问"能不能火/要不要继续写"=score；"哪里写崩了"=review；"读者爱不爱看"=simulate；"设定/伏笔有没有漏"=wiki；"节奏拖不拖"=balance。
- 串用顺序：先 score 定方向 → review 抠硬伤（自动调 wiki 查一致性/伏笔）→ balance 收节奏 → simulate 验留存。**写完一卷别只跑 review/score**：wiki（伏笔逾期）+ balance（节奏）+ simulate（留存）是常被漏掉的三项，建议一并提示用户。

⚠️ **"文风漂移"双触发仲裁**：提取/分析文风指纹、查笔力一致 → `novel-style`（文风是它的主责）；只有当诉求是"**作为质检项**报告某章偏离全书文风"且同时要查别的硬伤时，才并入 `novel-review`。单看文风一律走 style。

每条路由**简短确认输入后调起对应 skill**，让那个 skill 自走流程。不要在本 skill 里硬写小说。

## 决策树

0. **先看有没有在建项目**：用户指向（或当前正处于）某个 `写小说/<项目>/`，且其下有 `_进度.md` → **先读进度**：
   - **进度路由**：跑 `python3 skills/novel/progress.py "<作品根>"` 找第一条未完成项（基于章节矩阵表）；也可调 `novel-progress` 查看全线看板。
   - **准入检查 (Gate)**：在进入 `drafting` (写正文) 或 `export` 前，跑 `python3 skills/novel/novel-gate.py <作品根> --stage <阶段>`；该入口统一调用 novel QA gate，覆盖 rights/review/score 阻断。
   - **写后自动化**：每写完一章，建议跑 `python3 skills/novel/scripts/post_write.py <作品根> --chapter 第N章` 自动勾选进度并更新百科。
   - **标准化旧项目**：若 `_进度.md` 格式陈旧，跑 `python3 skills/novel/scripts/standardize_progress.py <作品根>` 迁移到标准矩阵。
   - 仅当 `_进度.md` 显示已全部完成、或用户明确要开新动作时，才往下走 1-5。
1. 用户给了**本地 .txt/.md/.docx、目录、file:// 或 URL**，且意图是"拖进来/导入/先建作品/纳管源书"，或没说具体动作 → 先跑 `python3 skills/novel/scripts/import_novel.py "<路径或URL>"` 建 `写小说/<书名>/`。
2. 用户给了**本地文件路径** + 明确动作（续写XX视角 / 起书名 / 扩 / 缩 / 漫剧改编）→ 直接按动作路由。
3. 用户给了**书名 / 作者 / 公版目录 URL**，明确说"抓回来/下载公版/联网取书" → `novel-fetch`。
4. 用户的输入是**只言片语 / 一个想法 / 一点风格 / 零散碎片**，要写一本**原创新书**（没有成型源文）→ `novel-create`（它会用访谈把碎片补全成蓝图，**别在这里反问"给我个文件"**）。
5. 用户给了**碎片 + 已有半成品/笔记文件**，要继续往成书走 → 也走 `novel-create`，用 `--ingest` 把碎片吃进 `素材/`。

## 拖入小说 / 链接建档

当用户说"从任何地方拖进来一本小说"、只给一个路径/URL、或只是要先把源书收进仓库时，不要问"要做什么"。先导入建档：

```bash
python3 skills/novel/scripts/import_novel.py "<路径或URL>"
```

脚本行为：
- 自动从文件名、URL、HTML title 或正文首行推断书名，落到 `写小说/<书名>/`。
- 写入 `原作.txt`、`小说/<书名>.txt`、可用时写 `小说/<书名>.docx`、`小说/source_manifest.json`、`_meta.json`、`_设置.md`、`_进度.md`。
- 本地 `.txt/.md/.docx` 可直接纳管；通用 URL 必须加 `--i-have-rights`，Project Gutenberg / Wikisource 自动记为 `public-domain`，但只写入来源侧公版依据和辖区提示；跨地区发行、商用或 n2d 改编前必须补 `--distribution-regions`/权利复核；已知付费墙站拒抓。
- 如果目标作品已存在，交互环境会提示 `新建版本 / 覆盖 / 使用现有 / 取消`。非交互环境不会自动覆盖，必须显式传：

```bash
python3 skills/novel/scripts/import_novel.py "<路径或URL>" --on-exists new-version
python3 skills/novel/scripts/import_novel.py "<路径或URL>" --on-exists overwrite --force
python3 skills/novel/scripts/import_novel.py "<路径或URL>" --on-exists use-existing
```

## 何时不路由

- 用户在 `制漫剧/<剧名>/` 目录里有 `_进度.md`（漫剧管线状态）→ 让 `n2d` 接手，不要硬塞进 novel-* 家族。
- 用户在写**完全原创**小说（无源文本）→ 路由到 `novel-create`（它有访谈立项 + 蓝图/设定/章纲/Demo/进度跟踪的引导流程）。**只有**用户明确只想"随手聊两句、不要立项不要建项目"时，才不走 skill、直接帮写。

## 合法性继承（铁律）

novel-* 家族的合法性规则一致：**公版 / 自有 / 用户声明授权（`--i-have-rights`）**，并且公版必须记录辖区。

- 命中付费墙站或当代受版权网文，本 skill **拒绝路由** novel-spinoff / novel-rewrite / novel-expand / novel-condense（这些都会派生作品）。
- 仅当 `novel-fetch` 用来取公版书、或 `novel-title` 用来起原创书名时，才可对原作版权状态宽松。
- `public-domain` 不是“全球自动可商用”。`source_manifest.json/_meta.json` 会记录 `rights_jurisdiction`、`rights_covered_regions`、`distribution_regions`、`source_license_url`；导出 n2d/合本或商业/漫剧项目前，QA gate 会阻断发行地区未写或不被来源辖区覆盖的公版素材。
- 路由前先做一次铁律筛查；命中即拒做并解释为什么。

## 持续改进（meta-capability）

novel 同时承担 novel-* 家族的**经验累积**职责。在跑任何 novel-* 流水线的过程中，遇到以下**信号**时及时把发现写进对应文件：

### 触发信号

- **用户明确反馈**："这点不错"/"这样写就对了"/"以后都这样"/"不要那样，要这样"
- **自检反复出现的弱点**：同一类问题在两章 Demo 里都出现 → 升格为 skill 守则
- **用户重复问同一个问题**：可能跨项目都会问 → 升格为 Q&A
- **跨 skill 的判断模式**：例如"用什么标准甄别主角 vs 配角"、"原作太大锚点怎么精筛"

### 写到哪里

| 发现类型 | 写到 |
|---|---|
| 单 skill 的工艺细节 | 该 skill 的 `references/<相关>.md` |
| 单章写作守则 | `novel-craft/references/chapter.md` |
| 章纲编织模式 | `novel-craft/references/outline.md` |
| 扩 / 续 / 缩 的特定工艺 | `novel-craft/references/{expand,continue,condense}.md` |
| 路由判断模式（哪个 skill 适合哪种输入） | `novel/SKILL.md` 路由表 |
| 跨 skill 的 Q&A / 判断标准 | `novel/Q&A.md` |
| 项目特有的设定 / 角色口吻 | 项目本地的 `设定/角色卡.md`，**不写进 skill** |

### 节奏

- 不要每条都写——**只有清晰、可重用、跨场景适用**的才写。
- 用户明确叫停"别写"时不写。
- 写之前可以确认一次（"我想把这条加进 <文件>，要不要？"）；auto mode 下可以更主动，但优先选 `Q&A.md` 这个低风险落点。

### 反模式

- 把项目特有细节误写进 skill references（如某项目角色卡里的具体设定）。
- 在 SKILL.md 末尾堆 changelog——经验整合到正文，不要 changelog。
- 写进 skill 后不更新该 skill 的"常见错误"表，造成经验孤岛。
- 同一条经验在两个 skill 里写两份——应合并到 `novel-craft/` 后引用。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 拿到模糊请求就硬路由 | 先问澄清问题，2-3 句话搞清楚动作再路由 |
| 把漫剧改编请求路由进 novel-* | 改用 n2d 那条线 |
| 跳过合法性筛查 | 路由前必须查；本 skill 的最大职责就是把铁律前置 |
| 在本 skill 里直接开始写 | 不写；路由出去 |
