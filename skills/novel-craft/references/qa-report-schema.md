# QA 报告机器 schema

`novel-review` 和 `novel-score` 都保留 Markdown 报告给人读，但必须同时写 JSON 报告给调度器读。JSON 是回流、阻断、趋势统计的稳定输入；Markdown 可以改排版，JSON 字段名不要漂。

## `审稿/review_report.json`

用于回答“写得对不对、哪里必须改”。顶层字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | int | 是 | 当前为 `1` |
| `kind` | string | 是 | 固定 `novel_review_report` |
| `project_root` | string | 是 | 作品根 |
| `generated_at` | string | 是 | `YYYY-MM-DD` |
| `scope` | object | 是 | 审稿范围：章节、arc、是否全量 |
| `source_snapshot` | object | 是 | 本次审稿绑定的正文快照；含章节文件 path/hash 与 aggregate hash |
| `summary` | object | 是 | `blocking_count` / `suggestion_count` / `polish_count` / `verdict` |
| `mechanical_findings_path` | string/null | 是 | `mechanical_check.py --json-out` 产物路径 |
| `waivers` | list[object] | 是 | 显式豁免清单；没有豁免时为空数组 |
| `findings` | list[object] | 是 | 合并机检 + 人判后的问题清单 |
| `next_actions` | list[object] | 是 | 推荐回流动作，按优先级排序 |

`summary` 必须包含 `waiver_count`。任何通过命令行或人工决定跳过的 gate 都必须写入 `waivers[]`，避免“豁免通过”和“正常通过”长得一样。

`waivers[]` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 稳定豁免 ID，如 `WAIVER-MISSING-MECHANICAL` |
| `type` | string | 豁免类型，如 `missing_mechanical` |
| `created_at` | string | `YYYY-MM-DD` |
| `reason` | string | 显式豁免原因，不能空 |
| `affected_gate` | string | 被豁免的 gate |
| `risk` | string | 被跳过检查的风险说明 |
| `scope` | object | 作用域绑定；baseline/报告/hash 类豁免必须写具体对象，不能空泛放行 |

`findings[]` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 稳定问题 ID，如 `REV-001` |
| `severity` | string | `blocking` / `suggestion` / `polish` |
| `dimension` | string | `pov/ooc/setting/anchor/plot/pacing/style/theme/reader_promise/prose/plagiarism/format/wordcount/...` |
| `chapter` | int/null | 章节号；全局问题为 null |
| `location` | string | 章+段/行定位 |
| `evidence` | string | 短证据引文或机检证据 |
| `problem` | string | 问题描述 |
| `fix_hint` | string | 可执行修法 |
| `recommended_skill` | string | `novel-create/novel-rewrite/novel-spinoff/novel-craft/novel-review/...` |
| `return_to_stage` | string | `blueprint/setting_bible/source_model/direction_spec/outline/demo/draft/review/export` |
| `affected_files` | list[string] | 建议修改的文件 |
| `blocking` | bool | 是否阻断进入下一阶段 |
| `confidence` | string | `high/medium/low` |

`next_actions[]` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `priority` | string | `must/should/could` |
| `action` | string | 动作描述 |
| `recommended_skill` | string | 应回流的 skill |
| `return_to_stage` | string | 应回流的机器阶段 |
| `finding_ids` | list[string] | 关联问题 ID |

## `评分/score_report.json`

用于回答“值不值得做、能不能火、该往哪改”。顶层字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | int | 是 | 当前为 `1` |
| `kind` | string | 是 | 固定 `novel_score_report` |
| `project_root` | string/null | 是 | 有作品根则填；用户贴文本则为 null |
| `generated_at` | string | 是 | `YYYY-MM-DD` |
| `target_platform` | string | 是 | 评分权重档对应的平台 |
| `score_task_id` | string | 是 | 本次评分 prompt 任务 ID；assessment JSON 必须回显同值 |
| `score_task_path` | string | 是 | `评分/score_task.json` 或显式 `--task` 路径 |
| `assessment_prompt_hash` | string | 是 | 生成评分 JSON 的 prompt sha256 |
| `scope` | object | 是 | 整本 / 前三章 / 指定 arc |
| `source_snapshot` | object | 是 | 本次评分取样绑定的正文快照；含样本文件 path/hash 与 aggregate hash |
| `market_baseline` | object | 是 | 热榜基准日期、来源文件、来源链接 |
| `scores` | list[object] | 是 | 七维分数 |
| `title_check` | object/null | 否 | 书名体检（附加项，不计入总分）；新版 `score.py` 总会写入，书名未定时为 null；更早的旧报告可缺省 |
| `deductions` | list[object] | 是 | 雷点扣分 |
| `total_score` | number | 是 | 百分制总分 |
| `tier` | string | 是 | `爆款潜力/合格偏上/及格线下/不及格` |
| `verdict` | string | 是 | `过/小改/大改/弃稿重立` |
| `rewrite_roi` | string | 是 | `high/medium/low` |
| `waivers` | list[object] | 是 | 评分阶段显式豁免；没有豁免时为空数组 |
| `next_actions` | list[object] | 是 | 推荐下一步 |

`scores[]` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `dimension` | string | `topic_heat/opening_hook/payoff_density/character_power/plot_structure/prose/retention` |
| `raw_score` | number | 1-10 |
| `weight` | number | 当前平台权重 |
| `weighted_score` | number | 折算后分值 |
| `evidence` | string | 原文证据或热榜对照证据 |
| `comment` | string | 一句短评 |
| `improve_by` | string | 应交给哪个 skill 或哪类修改 |

`title_check` 字段（书名体检，维度沿用 `novel-title` 5 维；规则见 `novel-score/references/rubric.md`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 体检的现有书名（`_meta.json.title`） |
| `scores` | object | `hook/platform_fit/character_identity/anti_collision/memorability`，各 1-5 |
| `total` | number | 5 维合计（满分 25） |
| `max_total` | number | 固定 25 |
| `comment` | string | 一句短评 |
| `collision` | object | `status/path/generated_at`；读 `设定/书名撞名检查_*.json`，缺则 `unchecked`（≠ 不撞名） |
| `needs_rename` | bool | 总分 <15 或 `hard_collision` 或 LLM 显式判换名；true 且非弃稿重立 → `next_actions[]` 路由 `novel-title` |

`market_baseline` 字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `baseline_date` | string | `YYYY-MM-DD` |
| `baseline_path` | string | `评分/题材热榜_<YYYY-MM-DD>.md` |
| `baseline_json_path` | string | `评分/market_baseline_<YYYY-MM-DD>.json` |
| `sources` | list[object] | 每个来源含 `platform/url/title/collected_at/use_for/status/signals` |
| `manual_evidence` | list[object] | 结构化人工证据，含 `platform/date/source/summary[/url]` |
| `coverage_warnings` | list[string] | 红果/抖音/漫剧等目标平台覆盖缺口 |
| `expires_after_days` | int | 建议 14-28；过期重拉 |
| `freshness` | object | `status/blocking/reason/expires_on`；`no_evidence` 必须阻断，除非人工显式豁免 |

有效市场基准必须至少满足其一：存在 `status=ok` 且 `signals` 非空的来源；或存在结构化 `manual_evidence` 人工补充。全是 `fetch_error`、空 signals 或自由文本 `notes` 的 baseline 不能作为评分证据；红果/抖音/漫剧目标缺覆盖时 `freshness.status=coverage_gap` 并阻断。

`source_snapshot` 由 `novel-craft/scripts/report_snapshot.py` 生成。`review_report` 应对当前 `章节/` 全量快照负责；`score_report` 应对本次评分样本负责。`score:full` 与 review 一样会校验当前章节全集，新增/删除章节后旧 full score 失效；`score:opening` 只绑定前 3 章样本。正文变更后旧 report/task 失效，必须重审/重评。`qa_gate.py` 会先校验 `review_report` / `score_report` 必填字段和基础类型；schema 缺字段、`kind/schema_version` 不匹配、缺 `score_task_id/assessment_prompt_hash` 等旧报告在 export gate 下阻断。

`评分/score_task.json` 是评分 prompt 与 assessment 的绑定层。无 `--mock-assessment` 运行 `score.py` 时生成 task；注入 assessment 时必须读取同一 task，校验 `source_snapshot`、market baseline hash、scope、评分档，并要求 assessment JSON 回显 `score_task_id`。

`score_report.waivers[]` 同 review 的 `waivers[]` 字段结构。`--allow-stale-baseline` 只能生成 `type=score_baseline_freshness` 的显式豁免，并且 `market_baseline.freshness.blocking` 仍必须保留为 `true`，由 QA gate 降级为 warning，而不是伪装成 fresh。该豁免必须带 `scope.baseline_date` 与 `scope.freshness_status`，只豁免对应那一次 baseline；baseline 日期或状态变化后旧 waiver 不再匹配。

## `审稿/waiver_log.jsonl`

所有跨报告或产物级绕过都写统一日志，每行一个 JSON object：

```json
{"id":"WAIVER-IGNORE-QA-GATE-20260608123000000000","type":"ignore_qa_gate","created_at":"2026-06-08","reason":"explicit --ignore-qa-gate during export","affected_gate":"export_qa_gate","source":"novel-craft/scripts/export.py","scope":{"source_aggregate_hash":"...","chapter_count":12,"blocker_ids":["REVIEW-MISSING"],"formats":["txt"]},"details":{}}
```

当前必须写日志的入口：

- `novel-craft/scripts/export.py --ignore-qa-gate`
- `novel-craft/scripts/report_gate.py --waive-missing-score`
- `novel-craft/scripts/draft_packets.py --allow-missing-demo`
- `novel-score/scripts/score.py --allow-stale-baseline` 且 freshness 阻断

`missing_score_report` 豁免只能由 `report_gate.py --waive-missing-score` 生成，scope 必须绑定当前 `draft_mode/target_platform/outputs/chapter_count/source_aggregate_hash`；章节正文或目标变了，旧豁免不再匹配。`ignore_qa_gate` 豁免必须绑定本次章节 hash、blocker ids、导出 formats，以及已有 rights/review/score 报告文件 hash；若 blocker ids 含 `RIGHTS-*`，只能说明用户强制导出留痕，不代表版权风险已解除。

## 回流约定

- `blocking=true` 或 `verdict=大改/弃稿重立` 时，上层调度器不能直接进入 `export`。
- `dimension=theme/reader_promise/prose` 的阻断或建议项应对照 `设定/读者契约.md` 与 `审稿/demo_gate.json.reader_contract`，分别回流 `outline/demo/draft`，不要只做表层润色。
- `return_to_stage` 必须使用 `contract.py` 里的稳定 stage key。
- `recommended_skill` 必须是 `novel` 路由表中存在的 skill，或明确写 `manual`。
- JSON 中的证据只放短引文；长段落留在 Markdown 报告。

## 执行入口

- `python3 skills/novel-review/scripts/build_review_report.py "<作品根>" [--human-assessment 审稿/human_findings.json]`：把机检/人判汇总成 `审稿/review_report.json`，供 gate 消费。
- `python3 skills/novel-craft/scripts/report_gate.py "<作品根>"`：按 export 硬闸检查 rights/review/score 阻断，默认阻断时返回非 0；`--progress-mode` 用于续跑提示，缺 review 只显示 warning。商业/漫剧项目确需跳过评分时，用 `--waive-missing-score --reason "<原因>"` 写入带 scope 的 `missing_score_report` 豁免。
- `python3 skills/novel-craft/scripts/progress.py "<作品根>"`：展示下一阶段 owner/gate/on_fail，同时展示 QA gate 阻断。
- `python3 skills/novel-craft/scripts/export.py "<作品根>" ...`：默认执行 QA gate；除非用户明确要求并传 `--ignore-qa-gate`，否则阻断未清不能导出。
