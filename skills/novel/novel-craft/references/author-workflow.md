# 作者成书通用流程

这份流程把 novel 线已有工具串成“从想法到定稿”的作者工作台。它适用于原创、派生、短篇、商业连载、出海译制底稿和漫剧/微短剧源书；具体平台、篇幅和 AI 使用方式仍以项目 `_设置.md` 为准。

## 原则

- **一步一产物**：每一步都要落文件，下一步只读这些文件，不靠聊天记忆。
- **作者种子先于建议**：原创项目在展示 AI/市场候选前，先把作者未经润色的原始种子冻结到 `探索/`；探索试写与正式正文、状态账本和 gate 隔离。
- **判断先于正文**：用途、读者、题材、资料、读者契约、设定圣经和 Demo gate 没过，不批量写。
- **证据先于专业事实**：行业、医学、法律、金融、历史、海外、平台规则等内容先建 `novel-research` 资料包。
- **事实必须落场景**：资料包补齐后要生成 `research_scene_usage`，明确每条事实服务哪个章节/场景、怎么用、哪里不能写过头。
- **意图先于蓝图细化**：作者主题、余味、不可妥协项和伦理/审美边界要落成 `author_intent`，后续审稿和编辑按它判断“改得对不对”。
- **素材先于生活感**：人物行为、五感、场景烟火气先进 `novel-observe`，再转化进场景。
- **正向审美先于精修**：先登记项目 Demo 或授权/公版样本“为什么有效”，再做 line edit。
- **证据分层**：真实读者反馈与经审计的自有投放数据是经验数据；合成读者探针只提复核假设；公榜只作市场语境。不得把三者混成同一“读者事实”权重序。
- **结构先于句子**：developmental edit 未完成前，不做大规模 copyedit/proofread。

## 0. 入口分流

目标：明确这是原创、导入、派生、续写、扩写、压缩、改写、审稿、评分、编辑还是发布。

产物：
- 新项目：`_meta.json`、`_设置.md`、`_进度.md`
- 原创且作者提供原始想法：`探索/种子/<seed_id>.md` + `.json`（可选，不作为正式 pipeline 阻断项）
- 导入项目：`原作.txt`、`小说/source_manifest.json`

命令：
```bash
python3 skills/novel/scripts/import_novel.py "<路径或URL>"
python3 skills/novel/novel-create/scripts/init_project.py --title "<暂定名>" --genre "<题材>" --premise "<一句话故事>" --scale short --purpose "<用途>" --platform "<平台>" --human-seed-file "<作者原始种子.md>" --human-seed-author "<作者>" --human-first-confirmed
python3 skills/novel/novel-settings/scripts/settings_cli.py "<作品根>" audit
```

通过标准：
- 作品根存在，`_设置.md` 写明 `小说用途`、`目标平台`、`文本主创模式`、`AI使用披露` 等关键选择点。
- 原创项目若声称保留 human-first seed，其文件与 `探索/manifest.json` SHA 对齐；没有种子不阻断旧项目或派生项目。

## 1. 构思与市场假设

目标：把碎片想法变成可写、可验证的创作蓝图。

产物：
- 可选探索：`探索/草稿/*`、`探索/决策/*`、`探索/晋升候选/*`（始终非正史）
- `设定/创作蓝图.md` 或派生项目的方向/spec 文件
- `设定/author_intent.json`、`设定/作者意图.md`
- `设定/读者契约.md`
- 商业项目：`评分/market_baseline_*.json`、`评分/题材热榜_*.md`

命令：
```bash
python3 skills/novel/novel-craft/scripts/exploration.py "<作品根>" register --file "<试写稿.md>" --title "<标题>" --kind character_audition --creator "<作者>" --authorship human
python3 skills/novel/novel-craft/scripts/exploration.py "<作品根>" status --json
python3 skills/novel/novel-craft/scripts/author_intent.py scaffold "<作品根>"
python3 skills/novel/novel-craft/scripts/author_intent.py check "<作品根>" --write
python3 skills/novel/novel-score/scripts/collect_market_baseline.py "<作品根>/评分" --target-platform "<目标平台>" --allow-fetch-errors
python3 skills/novel/novel-craft/scripts/author_workflow.py "<作品根>" --write
```

通过标准：
- `author_intent.json` 写明 `core_theme`、`target_emotional_aftertaste`、`non_negotiables`、`aesthetic_boundaries`、`forbidden_tropes`、`ethical_boundaries` 和 `misreading_risks`。
- 若探索稿影响正式设计，先用当前 SHA 登记 `promote_candidate`，再把“发现”转写进蓝图/设定并重新执行相应阶段复核；默认派发独立 specialist reviewer，显式逐阶段人审项目才停用户；不得把候选直接复制成正式章。
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
- `_设置.md` 的 `创作工艺档` 已确认；旧项目缺失时按 `genre_novel` 兼容，不从目标平台反推。
- `commercial_serial / genre_novel` 场景卡有 POV、目标、阻碍、冲突、转折和价值变化；`literary` 只要求 POV/viewpoint 可归属，其余常规动力字段为人工复核提醒；`experimental` 不以主观字段缺失硬挡。后两档可用揭示、关系微移、感知变化、意象复现或有意停滞替代传统 `turn/value_shift`。
- 结构地图按所选工艺档检查。商业/类型档缺 `turn/value_shift` 阻断；文学/实验档只在所有登记叙事功能均缺时给启发式提醒，不以主观结构判断硬挡全稿审稿。
- `manuscript_map_check.json` 会绑定生成时的规范工艺档与 `scene_cards.json` 哈希，并记录 `_设置.md` 来源；改档或改场景卡后旧 check 自动 stale，改目标平台等无关选择则不会。stale 后必须重跑 `manuscript_map.py "<作品根>" --write`，author workflow/pipeline 不接受旧 `passed=true`。
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
- 商业项目已有绑定当前样本与市场基准的 score；`production_decision=kill` 只作为待作者确认的重立建议，不自动阻断批量写。

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
- `reader_panel_signals.json` 始终是 synthetic/context-only 合成探针；schema v3 只保留未校准表面分量、不产聚合留存分，并以 `source_snapshot` 绑定实际 scope。stale 只提示重跑、v1/v2 新鲜度未知，均不展示为当前信号；补完阅读视角证据后仍不能当真实读者或统计留存证据，也不自动调分。
- 读者测试计划写明 cohort、A/B 分配、采集字段、隐私说明；真实反馈尽量带 `ab_test_id`、`variant_id`、`take_id`。
- 普通 platform/KDP 发布不要求先拥有历史 reader telemetry；需要数据验证的发布明确选 `data_validated_launch`，此时才要求真实 telemetry 或作用域匹配的 waiver。beta 测试若要执行，先建 reader test plan。

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
- 可选：`修订/authenticity_read.json` / `.md`
- 可选：`修订/authenticity_read_check.json` / `.md`

命令：
```bash
python3 skills/novel/novel-craft/scripts/revision_planner.py "<作品根>"
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>"
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>" --line-packet NN
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>" --query-task EDIT-001 --query "<需要作者裁决的问题>" --query-severity P0
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>" --answer-query EQ-001 --answer "<作者/主编裁决>" --query-status answered
python3 skills/novel/novel-edit/scripts/edit_plan.py "<作品根>" --close-task EDIT-001 --status fixed --note "<改法与回测>"
python3 skills/novel/novel-edit/scripts/style_sheet_check.py "<作品根>" --write
python3 skills/novel/novel-edit/scripts/authenticity_read.py scaffold "<作品根>" --scope "<高语境场景>" --reader-id "<匿名ID>" --fit "<与范围的匹配说明>"
python3 skills/novel/novel-edit/scripts/authenticity_read.py add "<作品根>" --category agency --severity major --location "<章/场>" --observation "<具体观察>"
python3 skills/novel/novel-edit/scripts/authenticity_read.py resolve "<作品根>" --finding AUTH-001 --decision adapted --author-note "<处理方式或保留理由>" --decided-by "<作者/主编>"
python3 skills/novel/novel-edit/scripts/authenticity_read.py complete "<作品根>" --summary "<覆盖范围与结论>"
python3 skills/novel/novel-edit/scripts/authenticity_read.py check "<作品根>" --write
```

通过标准：
- P0/P1 结构任务已关闭或显式接受。
- 所有 editor query 已回答、接受、豁免或关闭。
- style sheet 覆盖术语、称谓、格式、时间线和主创模式。
- `style_sheet_check.json.blocking=0`。
- proof checklist 无未处理项。
- 真实性/文化审读只在题材与作者需要时启用；默认是咨询证据，未完成或过期只提示，不自动判表达“合格/不合格”。
- 若项目显式用 `scaffold --required` 把它设为发布前置，则须完成审读、绑定当前全部章节 snapshot，并由作者对 open major 意见逐条留理由裁决；作者可接受、调整、拒绝或追问。

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
- 已启用的 authenticity read 会被 release manifest 绑定；可选审读不完整只 warning，只有显式 `required_for_release=true` 才阻断发布。
- AI-assisted / AI-generated 文本有逐章 `chapter_usage`，发布元数据有标题、简介、分类、关键词、权利摘要和 AI/合规摘要。
- 只有 `data_validated_launch` 要求真实读者数据，或由 waiver 明确说明无法取得数据及适用 profile；普通发布把遥测列为市场验证建议。
- 所有 waiver 都有作用域、理由和版本 hash。

## 快速命令

```bash
python3 skills/novel/novel-craft/scripts/author_workflow.py "<作品根>" --write
python3 skills/novel/scripts/flow.py "<作品根>"
python3 skills/novel/novel-dashboard/scripts/dashboard.py "<作品根>" --write --html
```
