---
name: novel-score
description: 给【已写好】的小说/章节做"市场 + 品质"综合评分体检——联网实时拉取红果/抖音/番茄当前最火题材与套路作基准,按 题材热度匹配 / 开篇黄金三章钩子 / 爽点密度与节奏 / 人设与金手指 / 剧情结构主线 / 文学性文笔 / 完读留存潜力 多维打分,出加权总分 + 平台档位 + 「过 / 小改 / 大改 / 弃稿重立」判定 + 改写ROI(值不值得继续改) + 该改哪几章哪几维。与 novel-review(挑硬伤)互补:本 skill 判"值不值得做、能不能火"。题材热度除了联网拉公榜,还读 n2d-feedback 写的「自有题材战绩库」做第一方先验(选题↔投放闭环的读端),自有 ROI/留存权重高于公榜。Use when asked to 给小说打分/评分/测一下能不能火/这本值不值得写下去/要不要继续改/市场体检/题材够不够热/爆款潜力/自有战绩/选题反哺. Triggers 小说评分, 打分, 测评, 能不能火, 爆款潜力, 题材热度, 市场体检, 值不值得改, 要不要继续改, 改写ROI, 题材战绩库, 选题反哺, novel score, novel rating.
---

# novel-score — 小说「市场 + 品质」综合评分体检

给**已写好**的小说/章节打分:对标**当前**红果/抖音/番茄最火题材,从文学性、剧情、爽点、留存等多维评定,给出**总分 + 档位 + 是否值得继续改写的判定 + 改哪里**。

**只读不改**,不写、不续、不润色——产出评分报告 + 下一步建议,由用户/上层据此路由到 `novel-rewrite` / `novel-expand` / `novel-continue` / `novel-create`。

## 与 novel-review 的分工(别混)

| | novel-review | **novel-score(本 skill)** |
|---|---|---|
| 问的问题 | 写得**对不对/扎不扎实** | **值不值得做、能不能火** |
| 干什么 | 挑硬伤:视角穿帮/OOC/设定矛盾/锚点漂/原文照搬/节奏 | 市场+品质打分:题材热度/钩子/爽点/留存/文学性 |
| 产出 | 按严重度排序的问题清单 | 加权总分 + 档位 + 判定 + 改写ROI |
| 顺序 | 抠硬伤 | **先 score 定方向(值不值得改),再 review 抠细节** |

> 典型用法:`novel-score` 判"这本要不要继续/往哪改" → 决定改 → `novel-rewrite/expand/continue` 改 → `novel-review` 抠硬伤。

## 偏好(私有 · 用户选择,不写死在本 skill)

按 `../_偏好约定.md` 读:先 `<作品根>/_设置.md` → 缺用全局默认 `创作偏好-默认.md` 预填并告知一句 → 再缺**首次问一次**→写回 `_设置.md`→之后沉默沿用。

本 skill 选择点:`目标平台`(决定**评分权重档**——商业爽文向 vs 品质向,见 `references/rubric.md`)。缺省按 **红果/抖音 商业爽文向**。

## 输入

- 一个项目作品根(`写小说/<项目>/`,含 `章节/*.md`,理想还有 `设定/`),**或**用户直接贴的文本 / `.txt`/`.docx` / 前几章。
- 篇幅不限:整本最好;只有**前 3 章**也能做"开篇市场体检"(开篇决定红果/抖音留存,价值最高)。

## 工作流
## 工作流

### 0. 定位 + 定档
- 找作品根/文本。读 `_设置.md` 的 `目标平台` → 选权重档(缺则问一次并写回)。
- 确认评分范围:整本 / 仅前 3 章 / 指定 arc / **指定 Take 版本**。

### 1. 联网实时拉取「题材热榜」(评分基准 · 必做)
题材热度会变,**每次评分前现拉**,不靠记忆:
- 同步跑共享采集器落盘，避免 score/self-audit 各拉一份：
  `python3 skills/novel-score/scripts/collect_market_baseline.py "<作品根>/评分" --target-platform "<目标平台>" --allow-fetch-errors`。
- `score.py` 会检查 `market_baseline_*.json` 的 `expires_after_days`、人读 md 文件、有效证据。缺失/过期/缺 md/无证据会失败并提示重拉。有效证据指至少一个 `status=ok` 且 `signals` 非空的来源，或 `notes` 有人工核验补充；全是 `fetch_error` 不算基准。只有离线测试或人工明确豁免时才加 `--allow-stale-baseline`；此时 `score_report.waivers[]` 与 `审稿/waiver_log.jsonl` 会记录 `score_baseline_freshness`，且 QA gate 只降为 warning，不会伪装成 fresh。

### 1.5 读「自有题材战绩库」做第一方先验(闭环 · 选题反哺)
公榜热度谁都能爬;真正的护城河是**自有投放战绩**。`score.py` 会自动读跨项目战绩库(`$N2D_GENRE_LEDGER` 或 `<repo>/生产战绩/genre_ledger.jsonl`，`--genre-ledger` 可改;由 `n2d-feedback --emit-ledger` 写),按本书 `genre` 聚合出「题材自有 3秒留存/15秒留存/完播/追更/ROI」,注入打分 prompt 的市场基准。
- **判读铁律**:第一方实测**权重高于公榜热度**。本题材自有 ROI/留存若明显低于平台基准 → `topic_heat` 下调,并在短评里点明「选题代差/本题材我方做不动」,哪怕公榜还热也别盲目上。
- 战绩库为空(还没回灌过)时正常退化为纯公榜评分,并提示「先用 n2d-feedback --emit-ledger 回灌以闭环」。这是 **选题→生产→投放→反哺选题** 闭环的读端;架构上与 n2d 线只在该数据文件层连接,不互相 import。
- **反同质化(立项前更有用)**:`n2d-feedback/scripts/differentiate.py` 从同一战绩库反推「未被做烂的组合」(题材×开场×结尾,避开公榜饱和+复用已验证轴),产 `生产战绩/差异化候选.{json,md}`。**立项/换题材**时先看它选差异化方向,再用本 skill 评具体稿——前者答"做什么不撞车",后者答"这稿能不能火"。

### 2. 取样与评估
- **自动化打分引擎**：
  1. 先生成绑定任务：`python3 skills/novel-score/scripts/score.py <作品根> [--scope opening|full|arc] [--file <Take路径>] [--chapter <章节号>]`。脚本会写 `评分/score_task.json`，内含 `source_snapshot`、market baseline hash、`assessment_prompt_hash` 和 `score_task_id`。
  2. 用该 prompt 取回 LLM JSON 后再注入：`python3 skills/novel-score/scripts/score.py <作品根> --mock-assessment <评估JSON> [--task 评分/score_task.json]`。评估 JSON 必须回显同一个 `score_task_id`；正文、baseline 或 scope 变化会阻断，必须重出 task。
- **单 Take 评估**：针对多版生成中的某一版进行独立打分，分数会自动同步至 `章节/takes/第NN章/takes_manifest.json`。
- **批量/全本评估**：默认 opening 取前 3 章；`--scope full` 读取 `章节/` 全量定稿文件，并会在新增/删除章节后使旧 full score task 失效。

### 3. 逐维打分(对照 `references/rubric.md`)
七维,每维 1-10 分 → 按权重档换算加权;每维**给分 + 证据引文 + 一句短评**。
题材热度匹配维度**必须对照第 1 步热榜**(不是泛泛而谈)。
另设**雷点扣分项**(开篇慢热 / 套路过时退潮 / 主角降智圣母 / 注水拖沓 / 三观雷 / AI味同质化 / 烂尾断更感)——命中按 `rubric.md` 单独减分。

### 4. 总分 + 档位 + 判定 + 改写ROI
- 加权总分(百分制)→ 落 `rubric.md` 的档位(爆款潜力 / 合格偏上 / 及格线下 / 不及格)。
- **判定四选**:`过`(可投/可继续) / `小改`(润色+局部强化指定维度) / `大改`(结构级改写) / `弃稿重立`(题材/主线不行,改写ROI低)。
- **改写ROI**:明说"继续改值不值"——提升空间 vs 改写成本。

### 5. 产出报告 + 推进
写两份产物：

- `评分/评分报告_<YYYY-MM-DD>.md`（给人读）
- `评分/score_report.json`（给调度器读）:
  - 遵守 `novel-craft/references/qa-report-schema.md`。
  - `score_task_id / score_task_path / assessment_prompt_hash` 必须保留，用于追踪评分 JSON 绑定的 prompt。
  - `source_snapshot` 必须记录本次评分样本的 path/hash/aggregate hash；正文或 Take 文件改动后旧分数失效，QA gate 会提示重评。
  - `market_baseline` 必须带 `baseline_path`(人读 md)、`baseline_json_path`、`sources`、`expires_after_days` 和 freshness 状态。
  - `waivers[]` 必须记录所有评分阶段显式豁免；baseline freshness 阻断被豁免时仍保留 `freshness.blocking=true`，且 waiver scope 必须绑定当次 `baseline_date` 与 `freshness_status`。
  - `next_actions[]` 必须写清 `recommended_skill` 和应回流的 `return_to_stage`。
  - 若针对 Take 评分，分数同步后可配合 `novel-craft/scripts/manage_takes.py --select --chapter N --take M` 定稿。


## 容错铁律(同 review)
只报**真问题、真差距**。轻微主观偏好不进扣分。打分给**证据引文**,不空口定性——否则分数没有说服力。

## 时效铁律
题材热榜**有保质期**。报告头注明基准日期;若沿用旧 `题材热榜_*.md` 超过约 2-4 周,**重拉**再评,别拿过期榜单打分。

## 详细评分维度 / 权重档 / 档位 / 判定规则

见 `references/rubric.md`。

机器报告 schema 见 `novel-craft/references/qa-report-schema.md`。
市场基准采集细则见 `references/market-baseline.md`。

## 何时不用本 skill
- 还没写正文(只有设定/章纲)→ 太早;先出 Demo 章再来体检(或走 novel-create 的 Demo gate)。
- 只想查硬伤(人设崩/视角穿帮)→ 用 `novel-review`。
- 只想测书名 → 用 `novel-title`。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 不联网、凭记忆评题材热度 | 必先拉当下热榜;题材是会退潮的,旧认知会误判 |
| 七维平均主义、不分平台 | 按 `目标平台` 选权重档:商业向题材/爽点权重高,品质向文学/结构权重高 |
| 只给分不给证据 | 每维必带原文引文 + 抓手,否则分数不可信 |
| 低分一律建议"继续改" | 要算改写ROI:题材退潮/主线塌就直说弃稿重立更划算 |
| 逐字读完整本烧上下文 | 重点前3章 + 抽样 + 结局;章多拆给子任务/子代理 |
| 评完不路由 | 按判定明确委托 novel-rewrite/expand/continue/create + 指出改哪 |
| 把 score 当 review 用(去挑错别字) | 硬伤交 review;本 skill 判方向与潜力 |
