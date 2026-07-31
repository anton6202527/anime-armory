# 作者成书通用流程

这份流程把 novel 线已有工具串成“从想法到定稿”的作者工作台。它适用于原创、派生、短篇、商业连载、出海译制底稿和漫剧/微短剧源书；具体平台、篇幅和 AI 使用方式仍以项目 `_设置.md` 为准。

## 原则

- **一步一产物**：每一步都要落文件，下一步只读这些文件，不靠聊天记忆。
- **判断先于正文**：用途、读者、题材、资料、读者契约、设定圣经和 Demo gate 没过，不批量写。
- **证据先于专业事实**：行业、医学、法律、金融、历史、海外、平台规则等内容先建 `novel-research` 资料包。
- **事实必须落场景**：资料包补齐后要生成 `research_scene_usage`，明确每条事实服务哪个章节/场景、怎么用、哪里不能写过头。
- **意图先于蓝图细化**：作者主题、余味、不可妥协项和伦理/审美边界要落成 `author_intent`，后续审稿和编辑按它判断“改得对不对”。
- **素材先于生活感**：人物行为、五感、场景烟火气先进 `novel-observe`，再转化进场景。
- **正向审美先于精修**：先登记项目 Demo 或授权/公版样本“为什么有效”，再做 line edit。
- **读者事实优先级**：真实读者反馈 > 自有投放战绩 > 模拟读者 > 公榜泛化。
- **结构先于句子**：developmental edit 未完成前，不做大规模 copyedit/proofread。

## 0. 入口分流

目标：明确这是原创、导入、派生、续写、扩写、压缩、改写、审稿、评分、编辑还是发布。

产物：
- 新项目：`_meta.json`、`_设置.md`、`_进度.md`
- 导入项目：`原作.txt`、`小说/source_manifest.json`

命令：
```bash
python3 skills/novel/scripts/import_novel.py "<路径或URL>"
python3 skills/novel/novel-create/scripts/init_project.py --title "<暂定名>" --genre "<题材>" --premise "<一句话故事>" --scale short
python3 skills/novel/novel-settings/scripts/settings_cli.py "<作品根>" audit
```

通过标准：
- 作品根存在，`_设置.md` 写明 `小说用途`、`目标平台`、`文本主创模式`、`AI使用披露` 等关键选择点。

## 1. 构思与市场假设

目标：把碎片想法变成可写、可验证的创作蓝图。

产物：
- `设定/创作蓝图.md` 或派生项目的方向/spec 文件
- `设定/author_intent.json`、`设定/作者意图.md`
- `设定/读者契约.md`
- 商业项目：`评分/market_baseline_*.json`、`评分/题材热榜_*.md`

命令：
```bash
python3 skills/novel/novel-craft/scripts/author_intent.py scaffold "<作品根>"
python3 skills/novel/novel-craft/scripts/author_intent.py check "<作品根>" --write
python3 skills/novel/novel-score/scripts/collect_market_baseline.py "<作品根>/评分" --target-platform "<目标平台>" --allow-fetch-errors
python3 skills/novel/novel-craft/scripts/author_workflow.py "<作品根>" --write
```

通过标准：
- `author_intent.json` 写明 `core_theme`、`target_emotional_aftertaste`、`non_negotiables`、`aesthetic_boundaries`、`forbidden_tropes`、`ethical_boundaries` 和 `misreading_risks`。
- 蓝图回答 logline、目标读者、主角、核心欲望、金手指/能力代价、主线冲突、承诺与禁偏。
- 商业/平台项目的市场判断带日期、来源和证据质量。

## 2. 资料、观察与审美准备

目标：让作品有事实可信度、生活质感和正向质量标尺。

产物：
- `资料/research_needs.json`、`资料/research_needs.md`
- `资料/research_jobs.json`、`资料/research_jobs.md`
- `资料/research_sources.json`、`资料/专业资料包_<主题>.md`
- `资料/research_scene_usage.json`、`资料/research_scene_usage.md`
- `素材/观察札记.jsonl`、`素材/观察素材库.md`
- `写作任务/观察素材_第NN章.md`
- `设定/aesthetic_bank.json`、`设定/审美样本库.md`

命令：
```bash
python3 skills/novel/novel-research/scripts/research_pack.py jobs "<作品根>"
python3 skills/novel/novel-research/scripts/research_pack.py scaffold "<作品根>" --topic "<主题>" --domain platform --source "<标题>|<日期>|official|high|<URL>|<说明>" --claim "<事实>|SRC-001|high|all|<用法>|<不确定项>|<禁用写法>"
python3 skills/novel/novel-research/scripts/research_pack.py scene-usage "<作品根>"
python3 skills/novel/novel-observe/scripts/observe.py scaffold "<作品根>"
python3 skills/novel/novel-observe/scripts/observe.py select "<作品根>" --chapter NN --write-packet
python3 skills/novel/novel-aesthetic/scripts/aesthetic_bank.py scaffold "<作品根>"
```

通过标准：
- 高风险专业域有 `ready` 资料包；每条事实有来源、日期、可信度、使用边界和禁用项。
- 每条关键事实有章节/场景映射，`dramatic_use` 说明它如何服务剧情，不把资料摘抄当正文。
- 现实质感章节至少有可转化的观察素材；正式写章包优先读取 `写作任务/观察素材_第NN章.md`。
- Demo 或样本高光写清 `why_it_works` 与 `transfer_rule`。

## 3. 设定圣经与场景卡

目标：把世界、人物、规则、伏笔和场景目的结构化，避免长篇漂移。

产物：
- `设定/角色卡.md`、`设定/世界观.md`、`设定/设定圣经.md`
- `设定/scene_cards.json`
- `设定/manuscript_map.json`、`设定/manuscript_map.md`
- 系统流/修仙等：`设定/power_system_registry.json`

命令：
```bash
python3 skills/novel/novel-craft/scripts/scene_cards.py scaffold "<作品根>"
python3 skills/novel/novel-craft/scripts/scene_cards.py check "<作品根>"
python3 skills/novel/novel-craft/scripts/manuscript_map.py "<作品根>" --write
python3 skills/novel/novel-wiki/scripts/storyworld_pressure_test.py "<作品根>"
```

通过标准：
- 主要角色有欲望、误信、恐惧、底线、战术和选择代价。
- 场景卡有 POV、目标、阻碍、冲突、转折和价值变化。
- 结构地图按章列出主欲望、阻碍、转折、价值变化、揭示/回收和五感锚点；缺转折/价值变化不进入全稿审稿。
- 长篇/复杂世界观 storyworld 压力测试不阻断。

## 4. Demo Gate

目标：用前 1-3 章验证文风、钩子、爽点、承诺和设定自洽。

产物：
- `章节/第01章.md` 至 Demo 章
- `审稿/demo_gate.json`
- `审稿/demo_readiness.json`、`审稿/demo_readiness.md`
- 商业项目：`评分/score_report.json`

命令：
```bash
python3 skills/novel/novel-review/scripts/consistency_audit.py "<作品根>"
python3 skills/novel/novel-score/scripts/score.py "<作品根>" --scope opening
python3 skills/novel/novel-craft/scripts/demo_readiness.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/semantic_job.py claim "<作品根>/语义任务/<score_job>.json" --claimed-by reviewer
```

通过标准：
- `demo_gate.json.status=passed`。
- `demo_readiness.json.ready_for_batch=true`；商业放量和文学/审美锚点都无阻断。
- `style_anchor`、`reader_promises`、`setting_constraints`、`reader_contract` 已写入 Demo gate。
- 商业项目 score 的 `production_decision` 不是 `kill`。

## 5. 分章写作循环

目标：按任务包逐章写，写后同步状态账本，避免越写越散。

产物：
- `写作任务/第NN章*.md`
- `章节/第NN章.md`
- `审稿/state_delta_第NN章.json`
- `审稿/state_verify_第NN章.json`
- `审稿/state_ledger.json`

命令：
```bash
python3 skills/novel/novel-craft/scripts/draft_queue.py "<作品根>" init
python3 skills/novel/novel-craft/scripts/draft_packets.py "<作品根>" --chapter NN
python3 skills/novel/novel-craft/scripts/propose_state_delta.py "<作品根>" --chapter NN
python3 skills/novel/novel-craft/scripts/reconcile_ledger.py "<作品根>" --chapter NN --audit
python3 skills/novel/scripts/post_write.py "<作品根>" --chapter 第NN章 --conclusion "<作品根>/审稿/state_verify_第NN章.json"
```

通过标准：
- 正文、状态增量、核对结论三者 hash 对齐。
- post_write 通过百科、逻辑、读者契约和力量体系检查。

## 6. 小批回扫与弧段压力

目标：每 3-5 章或自然 arc 做一次结构回看，及时修方向。

产物：
- `写作任务/弧段_第AA-BB章.md`
- `审稿/arc_plan_第AA-BB章.json`
- `审稿/arc_gate_第AA-BB章.json`
- `审稿/consistency_audit.json`

命令：
```bash
python3 skills/novel/novel-craft/scripts/arc_packets.py "<作品根>" --arc AA-BB
python3 skills/novel/novel-review/scripts/arc_gate.py "<作品根>" --arc AA-BB
python3 skills/novel/novel-review/scripts/consistency_audit.py "<作品根>"
```

通过标准：
- 没有连续 3 章不推进读者契约。
- 未收伏笔、承诺、关系变化和力量进阶均有账。

## 7. 方向评分、硬伤审稿与读者验证

目标：确认作品是否值得继续、哪里会流失读者、哪些问题必须回源头修。

产物：
- `评分/score_report.json`
- `审稿/review_report.json`
- `评分/reader_panel_signals.json`
- `评分/reader_test_plan.json`
- 有真实数据时：`评分/reader_telemetry_summary.json`

命令：
```bash
python3 skills/novel/novel-score/scripts/score.py "<作品根>" --scope full
python3 skills/novel/novel-review/scripts/build_review_report.py "<作品根>"
python3 skills/novel/novel-simulate/scripts/simulate_panel.py "<作品根>" --scope opening
python3 skills/novel/novel-feedback/scripts/reader_test_plan.py "<作品根>" --scope opening:1-3 --target-reader "<目标读者>" --cohort "核心读者|来源|纳入标准" --ab-test-id "opening-ab-001" --privacy-note "匿名指标与必要评论"
python3 skills/novel/novel-feedback/scripts/ingest_reader_events.py "<作品根>" --input "<反馈.csv>" --platform "<平台>" --source-name "<批次>"
```

通过标准：
- score/review 绑定当前正文 snapshot。
- 模拟读者未补完定性面板时只作低权重参考。
- 读者测试计划写明 cohort、A/B 分配、采集字段、隐私说明；真实反馈尽量带 `ab_test_id`、`variant_id`、`take_id`。
- beta/package 前至少有 reader test plan；platform/KDP 发布前必须有真实 reader telemetry，或有 `scope.release_profile` 匹配的 `reader_data_missing` / `reader_telemetry_missing` waiver。

## 8. 分层专业编辑

目标：把审稿、评分、节奏、读者反馈合并成编辑轮次，先改结构，再改语言，最后校样。

产物：
- `修订/revision_plan.json`
- `修订/edit_plan.json`
- `修订/编辑计划.md`
- `修订/editorial_letter.md`
- `修订/style_sheet.md`
- `修订/proof_checklist.md`
- `修订/editor_queries.jsonl`
- `修订/第NN章_line_edit_packet.md`

命令：
```bash
python3 skills/novel/novel-craft/scripts/revision_planner.py "<作品根>"
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>"
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>" --line-packet NN
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>" --query-task EDIT-001 --query "<需要作者裁决的问题>" --query-severity P0
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>" --answer-query QUERY-001 --answer "<作者/主编裁决>" --query-status answered
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>" --close-task EDIT-001 --status fixed --note "<改法与回测>"
python3 skills/novel/novel-edit/scripts/style_sheet_check.py "<作品根>" --write
```

通过标准：
- P0/P1 结构任务已关闭或显式接受。
- 所有 editor query 已回答、接受、豁免或关闭。
- style sheet 覆盖术语、称谓、格式、时间线和主创模式。
- `style_sheet_check.json.blocking=0`。
- proof checklist 无未处理项。

## 9. AI/合规、发布元数据、导出与回归

目标：先固定 AI 使用、平台/辖区合规与商品页元数据，再固化一个可交付版本，证明正文、审稿、评分、合规、资料、元数据和导出物是同一版。

产物：
- `合规/ai_usage.json`、`合规/AI使用说明.md`
- `合规/compliance_profile.json`、`合规/compliance_profile.md`
- `导出/metadata_pack.json`、`导出/metadata_pack.md`
- `导出/*.txt` / `.docx` / `*outline*.md`
- `导出/release_manifest.json`
- `导出/release_manifest.md`
- `生产数据/novel_dashboard.*`

命令：
```bash
python3 skills/novel/novel-craft/scripts/ai_usage.py "<作品根>" --text-mode AI-assisted --default-chapter-mode human_revised_ai_draft --human-contribution "<人工贡献>"
python3 skills/novel/novel-craft/scripts/compliance_profile.py "<作品根>" --write
python3 skills/novel/novel-craft/scripts/metadata_pack.py "<作品根>" --write
python3 skills/novel/novel-gate.py "<作品根>" --stage export
python3 skills/novel/novel-craft/scripts/export.py "<作品根>" --formats txt,docx,outline
python3 skills/novel/novel-craft/scripts/release_manifest.py "<作品根>" --release-name v1 --release-profile platform_publish
python3 skills/novel/novel-dashboard/scripts/dashboard.py "<作品根>" --write --html
```

通过标准：
- release manifest `release_ready=true`。
- review/score/compliance/research/AI usage/metadata pack 均非 stale。
- AI-assisted / AI-generated 文本有逐章 `chapter_usage`，发布元数据有标题、简介、分类、关键词、权利摘要和 AI/合规摘要。
- platform/KDP 发布有真实读者数据，或 waiver 明确说明无法取得数据及适用 profile。
- 所有 waiver 都有作用域、理由和版本 hash。

## 快速命令

```bash
python3 skills/novel/novel-craft/scripts/author_workflow.py "<作品根>" --write
python3 skills/novel/scripts/flow.py "<作品根>"
python3 skills/novel/novel-dashboard/scripts/dashboard.py "<作品根>" --write --html
```
