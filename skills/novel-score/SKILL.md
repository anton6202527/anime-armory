---
name: novel-score
description: 给【已写好】的小说/章节做"市场 + 品质"综合评分体检——联网实时拉取红果/抖音/番茄当前最火题材与套路作基准,记录证据质量,按 题材热度匹配 / 开篇黄金三章钩子 / 爽点密度与节奏 / 人设与金手指 / 剧情结构主线 / 文学性文笔 / 完读留存潜力 多维打分,出加权总分 + 平台档位 + 「过 / 小改 / 大改 / 弃稿重立」判定 + 改写ROI(值不值得继续改) + 该改哪几章哪几维。与 novel-review(挑硬伤)互补:本 skill 判"值不值得做、能不能火"。题材热度除了联网拉公榜,还读外部投放侧回灌的「自有题材战绩库」、novel-feedback 真实读者反馈、novel-simulate 虚拟试读信号和合规参考分布百分位；真实反馈/自有 ROI 权重高于公榜。已定名项目附带「书名体检」:按 novel-title 5 维标准体检现有书名(不计入总分),弱名/撞名时 next_actions 路由 novel-title 重起候选。Use when asked to 给小说打分/评分/测一下能不能火/这本值不值得写下去/要不要继续改/市场体检/题材够不够热/爆款潜力/自有战绩/真实读者反馈/参考分布/选题反哺/顺带看看书名行不行. Triggers 小说评分, 打分, 测评, 能不能火, 爆款潜力, 题材热度, 市场体检, 值不值得改, 要不要继续改, 改写ROI, 题材战绩库, 真实读者反馈, 完读率, 参考分布, 百分位, 选题反哺, 书名体检, novel score, novel rating.
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

按 `../skills/novel-craft/references/选择点与偏好.md` 读:先 `<作品根>/_设置.md` → 缺用全局默认 `创作偏好-默认.md` 预填并告知一句 → 再缺**首次问一次**→写回 `_设置.md`→之后沉默沿用。

本 skill 选择点:`目标平台`(决定**评分权重档**——商业爽文向 vs 品质向,见 `references/rubric.md`)。缺省按 **红果/抖音 商业爽文向**。

> 读端先验权重序：**真实读者反馈**(`novel-feedback` 的 `reader_telemetry_summary.json`) > **真实投放战绩**(外部回灌的题材战绩库) > **模拟读者留存信号**(`novel-simulate` 的 `reader_panel_signals.json`) > 外部公榜泛化。

## 输入

- 一个项目作品根(`创作区/写小说/<项目>/`,含 `章节/*.md`,理想还有 `设定/`),**或**用户直接贴的文本 / `.txt`/`.docx` / 前几章。
- 篇幅不限:整本最好;只有**前 3 章**也能做"开篇市场体检"(开篇决定红果/抖音留存,价值最高)。

## 工作流

### 0. 定位 + 定档
- 找作品根/文本。读 `_设置.md` 的 `目标平台` → 选权重档(缺则问一次并写回)。
- 确认评分范围:整本 / 仅前 3 章 / 指定 arc / **指定 Take 版本**。

### 1. 联网实时拉取「题材热榜」(评分基准 · 必做)
题材热度会变,**每次评分前现拉**,不靠记忆:
- 同步跑共享采集器落盘，避免 score/self-audit 各拉一份：
  `python3 skills/novel-score/scripts/collect_market_baseline.py "<作品根>/评分" --target-platform "<目标平台>" --allow-fetch-errors`。
- 红果/抖音/漫剧等 app 内榜无公开网页时，用结构化且未过期的人工证据补齐：`--manual-evidence "红果短剧|YYYY-MM-DD|第三方榜单|结论|URL"`；`--note` 只做人读备注，不计入有效证据。若缺口存在，采集器会额外写 `评分/market_evidence_tasks.json` 和 `评分/市场证据待补.md`，交给 `novel-research` 补平台市场资料包后再回跑采集器。
- 采集器会给每个来源写 `source_quality`，给整份基准写 `evidence_quality`；评分 prompt 会显示 high/medium/low 置信度。低质量证据不是不能看，但不能与官方/结构化/信号充足来源等权处理。
- `score.py` 会检查 `market_baseline_*.json` 的 `expires_after_days`、人读 md 文件、有效证据和短剧/漫剧覆盖缺口。缺失/过期/缺 md/无证据/coverage_gap 会失败并提示重拉。有效证据指至少一个 `status=ok` 且 `signals` 非空且未过期的来源，或 `manual_evidence[]` 有结构化且未过期的人工核验补充；全是 `fetch_error`、过期人工证据或自由文本 `notes` 不算基准。只有离线测试或人工明确豁免时才加 `--allow-stale-baseline`；此时 `score_report.waivers[]` 与 `审稿/waiver_log.jsonl` 会记录 `score_baseline_freshness`，且 QA gate 只降为 warning，不会伪装成 fresh。

### 1.5 读「自有题材战绩库」做第一方先验(闭环 · 选题反哺)
公榜热度谁都能爬;真正的护城河是**自有投放战绩**。`score.py` 会自动读跨项目战绩库(`$NOVEL_GENRE_LEDGER` 或 `<repo>/生产战绩/genre_ledger.jsonl`，`--genre-ledger` 可改;该文件由**外部投放侧回灌**),按本书 `genre` 聚合出「题材自有 3秒留存/15秒留存/完播/追更/ROI」,注入打分 prompt 的市场基准。
- **判读铁律**:第一方实测**权重高于公榜热度**。本题材自有 ROI/留存若明显低于平台基准 → `topic_heat` 下调,并在短评里点明「选题代差/本题材我方做不动」,哪怕公榜还热也别盲目上。
- 战绩库为空(还没回灌过)时正常退化为纯公榜评分。本 skill 只做容忍缺失的消费方,不依赖任何特定写端存在。
- **反同质化(立项前更有用)**:若外部回灌产出过 `生产战绩/差异化候选.{json,md}`(从战绩库反推「未被做烂的题材×开场×结尾组合」),**立项/换题材**时可先读它选差异化方向,再用本 skill 评具体稿——前者答"做什么不撞车",后者答"这稿能不能火"。无该文件则跳过。

### 1.6 读「真实读者反馈」做留存维度最高优先级证据(选做 · 真实读端)
若作品根有 `评分/reader_telemetry_summary.json`（`novel-feedback` 产）,`score.py` 会自动读取并把章节完读率、弃读率、评论情绪和 `weakest_chapters` 注入评分 prompt。有效注入时 `score_report.reader_telemetry_path` 与 `score_report.reader_telemetry_summary` 会记录来源。

```bash
python3 skills/novel-feedback/scripts/ingest_reader_events.py "<作品根>" \
  --input "<平台后台.csv或测试读者.jsonl>" \
  --platform "<平台>" \
  --source-name "<批次名>"
```

- **判读铁律**：真实读者反馈高于模拟读者和公榜；真实完读/弃读与模拟信号冲突时，retention 维度以真实反馈为准，模拟只当原因假设。
- `low_sample` 只提示样本小，不当硬证据。低完读/高弃读/负评集中时，score 应下调 retention，并把 `next_actions` 指向 `novel-review` / `novel-balance` 查具体定因。
- 无该文件正常退化；尚未发布/内测时可先跑 `novel-simulate`。

### 1.7 读「模拟读者留存信号」做留存维度先验(选做 · 虚拟试读)
若作品根有 `评分/reader_panel_signals.json`（`novel-simulate` 产）,`score.py` 会自动读取并把其 `retention_prior` / `hook_strength` / `cliche_density_per_kchar`(字段名与 `simulate_panel.py` 输出一致)注入打分 prompt 的「模拟读者留存信号」段,作**完读留存潜力**维度先验;有效注入时 `score_report.reader_panel_path` 会记录来源:
- **权重序**:真实读者反馈(1.6) > 真实投放战绩(1.5) > 模拟读者信号(本节,虚拟试读) > 公榜泛化。模拟信号是"发布前的虚拟试读",比公榜贴本书,但**不等于真实留存**,只作辅助先验,不可单独定生死。
- `reader_panel_signals.json` 默认 `signal_only=true/qualitative_completed=false`，只能低权重参考；必须补完人格心声/弃书点后才算完整模拟读者面板。
- 模拟 `retention_prior` 明显偏低且 `cliche_density_per_kchar` 高 → 留存维度下调并在短评点明"开篇疑似劝退/套路堆叠",建议先跑 `novel-simulate` 看弃书点再决定改哪。
- 无该文件正常退化(纯公榜+战绩库);需要更细的人格弃书点时提示先跑 `novel-simulate`。

### 1.8 参考分布百分位(选做 · 合规样本)
若作品根有 `评分/reference_distribution*.json`，`score.py` 会读取最新一份，在生成评分任务时提示参考水位，并在最终报告写 `benchmark_percentile`（总分百分位 + 逐维百分位）。参考分布只能纳入 `public-domain/user-owned/user-declared/original/authorized/licensed` 样本；未知权利样本会跳过。

构建入口：

```bash
python3 skills/novel-score/scripts/build_reference_distribution.py \
  "<作品根>/评分/reference_distribution_<YYYY-MM-DD>.json" \
  --sample "<某样本>/评分/score_report.json|original|自有样本|样本名"
```

这不是“抄参考作品”，只是 WebNovelBench 式相对水位：告诉你当前稿在自有/授权/公版参考样本里大概处于第几百分位。

### 2. 取样与评估
- **自动化打分引擎**：
  1. 先生成绑定任务：`python3 skills/novel-score/scripts/score.py <作品根> [--scope opening|full|arc] [--file <Take路径>] [--chapter <章节号>]`。脚本会写 `评分/score_task.json`，内含 `source_snapshot`、market baseline hash、`assessment_prompt_hash` 和 `score_task_id`。
  2. 用该 prompt 取回 LLM JSON 后再注入：`python3 skills/novel-score/scripts/score.py <作品根> --mock-assessment <评估JSON> [--task 评分/score_task.json]`。评估 JSON 必须回显同一个 `score_task_id`；正文、baseline 或 scope 变化会阻断，必须重出 task。
- **单 Take 评估**：针对多版生成中的某一版进行独立打分，分数会自动同步至 `章节/takes/第NN章/takes_manifest.json`。
- **批量/全本评估**：默认 opening 取前 3 章；`--scope full` 读取 `章节/` 全量定稿文件，并会在新增/删除章节后使旧 full score task 失效。

### 3. 逐维打分(对照 `references/rubric.md`)
七维,每维 1-10 分 → 按权重档换算加权;每维**给分 + 证据引文 + 一句短评**。
题材热度匹配维度**必须对照第 1 步热榜**(不是泛泛而谈)。
剧情结构、文学性、留存三维必须同时对照 `设定/读者契约.md`（若存在）：核心题旨是否被推进、读者承诺是否递进/兑现、文学质感是否匹配目标平台。缺契约时在报告里提示先按 `novel-craft/references/reader-contract.md` 补齐。
先判断主类型，再套 `rubric.md` 的类型专项评分尺：悬疑看公平谜面和证据链，硬科幻看假设与约束，文学/现实主义看观察精度和语言辨识度，历史看 register 与制度可信，恐怖看未知感和规则，言情看关系推进和情绪兑现，群像看多线弧光。不得把“爽点密度低”机械扣到所有类型上。
若存在 `设定/aesthetic_bank.json`，品质向/文学向/历史/悬疑项目在文学性、结构、人物维度引用 1-3 条 `novel-aesthetic` 正向样本作为辅助标尺；只迁移机制，不复制样本文字。
另设**雷点扣分项**(开篇慢热 / 套路过时退潮 / 主角降智圣母 / 注水拖沓 / 三观雷 / AI味同质化 / 烂尾断更感)——命中按 `rubric.md` 单独减分。

### 3.5 书名体检(附加项 · 不计入总分)
项目已定名(`_meta.json.title`)时,评分 prompt 会附带「书名体检」:按 `novel-title` 的 5 维标准(钩子/平台契合/角色识别/抗撞名/可记忆性,各 1-5 分)体检**现有书名**。抗撞名只做初判 + 读已有 `设定/书名撞名检查_*.json`;总分 <15/25 或硬撞名 → `needs_rename`,`next_actions[]` 路由 `novel-title` 重出候选并联网查重(判定为弃稿重立时不路由)。本 skill **只体检、不出候选**——起名/查重/回写 `_meta.json.title` 仍归 `novel-title`。规则细节见 `references/rubric.md` 的「书名体检」节。

### 3.6 短剧改编潜力体检(附加项 · 不计入总分 · 短剧/漫剧目标才触发)
当 `_设置.md 目标平台` / `小说用途` 或 `_meta.json` 命中 红果/抖音/漫剧/短剧 时,评分 prompt 会附带「短剧改编潜力体检」:按 5 维(可视化场景密度 / 强钩可镜头化 / 人物关系冲突浓度 / 单元剧式节拍 / 题材人设短剧新鲜度,各 1-5 分)评估**这部本身的可改编度**。当前改编机会、平台投入和选品池方向只引用 `评分/market_baseline_<日期>.json` 或 `novel-research` 平台资料包,规则见 `references/market-claims.md`。总分 <15/25 → `low_potential`,`next_actions[]` 提示先用 `novel-condense` 出漫剧版精简骨架(判定为弃稿重立时不路由)。改编门槛在**结构与冲突**不在文笔,故单列、不计入百分制总分。本 skill **只体检改编度**,实际改编/出漫剧版仍归 `novel-condense`;后续漫剧转制流程由用户显式交接成品文件。

### 4. 总分 + 档位 + 判定 + 改写ROI + 生产决策
- 加权总分(百分制)→ 落 `rubric.md` 的档位(爆款潜力 / 合格偏上 / 及格线下 / 不及格)。
- **判定四选**:`过`(可投/可继续) / `小改`(润色+局部强化指定维度) / `大改`(结构级改写) / `弃稿重立`(题材/主线不行,改写ROI低)。
- **改写ROI**:明说"继续改值不值"——提升空间 vs 改写成本。
- **生产决策三选**：`go` / `revise` / `kill`。`revise` 先回蓝图/章纲/开篇弱项，`kill` 停止批量写。

### 5. 产出报告 + 推进
写两份产物：

- `评分/评分报告_<YYYY-MM-DD>.md`（给人读）
- `评分/score_report.json`（给调度器读）:
  - 遵守 `novel-craft/references/qa-report-schema.md`。
  - `score_task_id / score_task_path / assessment_prompt_hash` 必须保留，用于追踪评分 JSON 绑定的 prompt。
  - `source_snapshot` 必须记录本次评分样本的 path/hash/aggregate hash；正文或 Take 文件改动后旧分数失效，QA gate 会提示重评。
  - `market_baseline` 必须带 `baseline_path`(人读 md)、`baseline_json_path`、`sources`、`expires_after_days` 和 freshness 状态。
  - `reader_telemetry_path` / `reader_telemetry_summary` 存在时表示真实读者反馈已接入；`reader_panel_path` 存在时表示虚拟试读信号已接入。
  - `benchmark_percentile` 存在时表示已接入合规参考分布百分位。
  - `waivers[]` 必须记录所有评分阶段显式豁免；baseline freshness 阻断被豁免时仍保留 `freshness.blocking=true`，且 waiver scope 必须绑定当次 `baseline_date` 与 `freshness_status`。
  - `production_decision` 必须包含 `decision/route/reason/score/verdict`，作为 demo 后 go/no-go 的机器判断。
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
- 想要**新书名候选**(起名/改名/查重) → 用 `novel-title`;本 skill 只在评分时顺带体检现有书名,不出候选。

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
