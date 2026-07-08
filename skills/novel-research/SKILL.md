---
name: novel-research
description: Professional research packet layer for novel-* projects. Use when a novel scene or project needs verifiable specialist knowledge instead of memory-only writing: medical, legal, criminal investigation, finance, military, history, religion, overseas/localization, technology, career/industry fiction, commercial platform submission, adaptation, or when the user asks for 专业、真实、行业感、别外行. Produces 资料/专业资料包_<主题>.md, 资料/research_sources.json, and refresh plans; draft packets auto-reference applicable packs, review/export block stale high-risk packets, and review checks whether professional facts have evidence support. Does not write prose.
---

# novel-research — 专业资料包层

不写正文，只给 novel-* 项目建立“事实证据层”：专业场景先有可追溯资料包，再进写章和审稿。

产物统一落在作品根：

- `资料/专业资料包_<主题>.md`：给人/AI 写章前读的资料包。
- `资料/research_sources.json`：机器索引。每条来源、事实、适用章节、可信度、不确定项、禁用项都结构化。
- `资料/research_scene_usage.json` / `资料/research_scene_usage.md`：把每条可用事实映射到章节/场景卡，记录戏剧用途、不确定边界和禁用写法。
- `资料/research_needs.json` / `资料/research_needs.md`：从蓝图、设置、章纲、章节和商业目标反推“还缺哪些专业资料包”。
- `资料/research_jobs.json` / `资料/research_jobs.md`：把资料缺口转成可分派的实时深搜任务、建议检索式和 scaffold 命令。
- `资料/research_refresh_plan.md`：定期刷新审计计划。列出过期包、临期包和高风险“需实时深搜”任务。
- `审稿/research_fact_support.json`：审稿阶段的证据覆盖检查结果。
- `评分/market_evidence_tasks.json` / `评分/市场证据待补.md`：`novel-score` 发现红果/抖音/漫剧市场基准缺口时生成的待补任务，由本 skill 接手补平台市场资料包。

## 触发

- 医疗、法律、刑侦、金融、军事、历史、宗教、海外、科技、职业文。
- 商业连载、平台投稿、出海、本地化、影视/短剧/漫剧改编前的事实、规则、行业细节。
- `novel-score/scripts/collect_market_baseline.py` 生成 `market_evidence_tasks.json`，要求补红果/抖音/漫剧/短剧的结构化榜单、投放、选品或平台趋势证据。
- 用户说“专业、真实、行业感、别外行、不要瞎编、符合流程/法规/行业常识”。
- `novel-review` 或 `draft_packets.py` 发现章节含高风险专业关键词但没有资料包。
- 用户要求“刷新知识库、检查资料是否过时、最新行业动态、前沿知识、定期联网复查”。

## 原则

- **本地规则做骨架，实时深搜做证据**：本 skill 的脚本只生成/校验资料包；资料来源由 agent 用实时搜索、官方文件、论文、教材、行业手册、专家材料或用户提供证据补齐。
- **证据先于正文**：高风险专业场景没有 `ready` 资料包时，不进入正式写章；可先写“准备包”，但需标明未核验。
- **显式 required domains 更严格**：若 `_meta.json` / `_设置.md` / `资料/research_requirements.json` 声明 `research_required_domains`，对应领域缺 ready 包会在 QA gate 直接 blocking，即使正文尚未命中关键词。
- **每条事实带来源**：事实必须指向 `SRC-xxx`，并写可信度、来源日期/访问日期、适用章节、用法边界。
- **禁用项显式写出**：行业误区、影视夸张、法规不确定、平台风险、不能写成的结论，都写入 `forbidden_items` 或事实的 `forbidden_use`。
- **过期要重查**：法律、平台规则、医学指南、金融、海外发行、AI/版权规则等资料包默认 90 天内有效；历史/文化/职业常识可按风险延长，但要写 `freshness_days`。
- **高风险过期直接阻断**：review/export 前会通过 QA gate 检查 `research_sources.json`；医学、法律、金融、平台、出海等 high-risk 包过期或缺 `updated_at`，不能继续商用导出。

## 工作流

1. **判定是否需要资料包**
   - 读 `_meta.json`、`_设置.md`、`设定/章纲.md` 和目标章节。
   - 命中高风险专业域时，先建资料包；商业/平台/出海项目至少建平台规则/目标地区/题材专业域资料包。
   - 可先跑需求清单，给作者一个“缺什么资料才能继续写”的落地列表：
     ```bash
     python3 skills/novel-research/scripts/research_pack.py needs "<作品根>"
     python3 skills/novel-research/scripts/research_pack.py needs "<作品根>" --chapter 4 --json
     python3 skills/novel-research/scripts/research_pack.py jobs "<作品根>" --chapter 4
     ```
   - `needs` 是诊断，`jobs` 是执行清单；后续 agent/作者按 `research_jobs` 的 P0/P1 顺序深搜、补来源、回写资料包。
   - 任务领取/关闭用：
     ```bash
     python3 skills/novel-research/scripts/research_pack.py job-update "<作品根>" RJ-001-MEDICAL \
       --status in_progress --assignee researcher-a --source-count 2 --notes "已找到官方指南和教材"
    python3 skills/novel-research/scripts/research_pack.py job-update "<作品根>" RJ-001-MEDICAL \
      --status verified --source-count 4 --notes "claims 已回写 research_sources.json"
     ```
   - 资料包补好后，把事实落到具体章节/场景，防止“查了资料但写章时乱用或忘用”：
     ```bash
     python3 skills/novel-research/scripts/research_pack.py scene-usage "<作品根>"
     python3 skills/novel-research/scripts/research_pack.py scene-usage "<作品根>" --chapter 4 --json
     ```
   - 重跑 `jobs` 会保留已有 `status/assignee/source_count/notes`，不会把已领取任务打回 open。
   - 若 `评分/market_evidence_tasks.json` 存在且有 `status=open`，优先补“平台市场”资料包；补完后回跑 `collect_market_baseline.py --manual-evidence ...`，让 score 使用同一份证据。
   - 可在 `_meta.json` 写 `"research_required_domains": ["medical", "legal"]`，或在 `资料/research_requirements.json` 写 `{"required_domains":["platform","overseas"]}`，强制这些领域必须有 ready 资料包。

2. **实时深搜并落证据**
   - 官方/一手资料优先：法律法规、监管/平台规则、医学指南、统计机构、论文、教材、权威手册。
   - 每条来源记录标题、URL/出处、发布日期或版本日期、访问日期、来源类型、可信度，并做五轴评估：`currency`（时效）、`relevance`（与本书/章节的相关性）、`authority`（权威性）、`accuracy`（是否能支撑 claims）、`purpose`（来源目的/偏向）。
   - 不能确认的内容进入“不确定项”，不要写进事实表当确定事实。

3. **生成/更新资料包**
   ```bash
   python3 skills/novel-research/scripts/research_pack.py scaffold "<作品根>" \
     --topic "<主题>" --domain medical|legal|crime|finance|military|history|religion|overseas|technology|career|platform|other \
     --chapters 3-5 --risk high --keyword "<关键词>" \
     --source "<标题>|<日期>|official|high|<URL>|<说明>|currency=date_recorded;relevance=direct_topic;authority=high_authority;accuracy=source_bound_claims;purpose=informational" \
     --claim "<事实>|SRC-001|high|3-5|<写作使用方式>|<不确定项>|<禁用写法>"
   ```
   - 没有现成证据时也可先 scaffold 空包，但 `status=draft` 不放行正式专业事实写作。
   - 人工编辑 `research_sources.json` 后，再跑 check。

4. **校验资料包**
   ```bash
   python3 skills/novel-research/scripts/research_pack.py check "<作品根>"
   python3 skills/novel-research/scripts/research_pack.py check "<作品根>" --chapter 4 --json
   ```
   - 输出/更新 `审稿/research_fact_support.json`。
   - 高风险章节没有适用 `ready` 包、来源缺日期/可信度、事实没有来源、资料过期，都会进入阻断或建议。
   - `required_domains` 缺 ready 包时类型为 `missing_required_research_pack`，导出/商用 gate 会直接阻断。

5. **刷新审计**
   ```bash
   python3 skills/novel-research/scripts/research_pack.py refresh-audit "创作区/写小说"
   python3 skills/novel-research/scripts/research_pack.py refresh-audit "创作区/写小说" --json
   ```
   - 扫描所有 `创作区/写小说/**/资料/research_sources.json`，也支持直接传单个作品根。
   - 按 `domain`、`risk_level`、`freshness_days`、`updated_at` 判断过期/临期。
   - 每个项目输出 `资料/research_refresh_plan.md`。
   - high-risk 过期资料包会生成“需实时深搜”任务清单；命令默认以非 0 退出，定时任务可用 `--no-fail` 只产计划。

6. **写章自动引用**
   - `novel-craft/scripts/draft_packets.py` 会读取 `资料/research_sources.json`。
   - 与当前章节匹配的资料包会自动加入“必读源文件”，并生成“专业资料包”小节。
   - 写章时只能使用资料包里的确定事实；不确定/禁用项不得写成定论。

7. **审稿/导出检查**
   - `novel-review/scripts/consistency_audit.py` 会调用本 skill 的校验逻辑。
   - `novel-review/scripts/build_review_report.py` 会把专业证据缺口汇入 `review_report.json`，建议回到 `novel-research` 补资料包。
   - `novel-craft` 的 QA gate 会在 review/export 前读取本索引；商业、平台、出海、医学、法律、金融等高风险过期包直接 blocking。

## 资料包 schema 摘要

`research_sources.json` 顶层：

- `schema_version`: `1`
- `kind`: `novel_research_sources`
- `packs[]`: 每个主题一包。

每个 `pack` 关键字段：

- `topic` / `topic_slug` / `domain` / `risk_level` / `status`
- `pack_path`
- `applicable_chapters`: `["all"]`、`[3,4,5]` 或 `["3-5"]`
- `keywords`: 用于章纲/正文命中。
- `freshness_days` / `updated_at`
- `sources[]`: `id/title/url/source_type/published_date/accessed_date/reliability/notes/evaluation{currency,relevance,authority,accuracy,purpose}`
- `claims[]`: `id/claim/source_ids/confidence/applicable_chapters/usage/uncertainty/forbidden_use`
- `uncertain_items[]`
- `forbidden_items[]`

`research_scene_usage.json` 关键字段：

- `claim_id` / `claim` / `topic` / `domain`
- `applicable_chapters`
- `scene_ids`：从 `设定/scene_cards.json` 匹配出的场景。
- `dramatic_use`：这条事实在剧情中的用途，不是资料摘抄。
- `uncertainty` / `forbidden_use`：保留不确定项和禁用写法。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 凭模型记忆写医疗/法律/金融细节 | 先做资料包；没有来源只能写“待核验”，不能当事实 |
| 写到一半才发现缺资料 | 先跑 `research_pack.py needs`，按阻断/建议顺序补包 |
| 只放链接，不拆事实 | 每条可写入正文的事实都要单独进 `claims[]` |
| 查了资料但没有绑定场景 | 跑 `research_pack.py scene-usage`，把 claims 映射到章节/scene cards |
| 来源只写“可信” | 补五轴评估；尤其说明时效、权威性、来源目的和 claims 支撑关系 |
| 把影视/网文套路当行业真相 | 放入 `forbidden_items` 或 `uncertain_items`，不要作为确定事实 |
| 资料包写了但任务包没读 | 跑 `draft_packets.py`；它会按章节自动注入适用包 |
| 审稿只看文学问题，不看专业事实 | 跑 `consistency_audit.py`，再用 `build_review_report.py` 汇总 |
