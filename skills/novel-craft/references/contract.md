# novel-* 契约层

本文件定义 novel 系列的机器契约。正文工艺可以在各 skill 自由展开，但脚本、导出、续跑和质检只应依赖这里定义的稳定字段。

机器单一真值源：`skills/novel-craft/scripts/contract.py`。

## `_meta.json` Schema

所有 `创作区/写小说/<项目>/` 根目录必须有 `_meta.json`。

### 通用字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | int | 是 | 当前为 `1` |
| `kind` | string | 是 | `create/spinoff/rewrite/expand/condense/continue` |
| `title` | string/null | 是 | 用户选定书名；未定为 null |
| `source_title` | string | 派生类必填 | 原作名；`create` 可无 |
| `rights_status` | string | 是 | `original/public-domain/user-declared/...` |
| `rights_jurisdiction` | string | 推荐 | 权利/公版依据适用辖区，如 `US/CN/GLOBAL/user-declared` |
| `rights_basis` | string | 推荐 | 原创/授权/公版判断依据 |
| `source_license_url` | string | 推荐 | 来源许可或公版说明 URL |
| `rights_covered_regions` | list[string] | 公版推荐 | 来源权利依据覆盖地区，如 Gutenberg 默认 `["US"]` |
| `distribution_regions` | list[string] | 发布推荐 | 计划发行/交付地区；未定留空 |
| `requires_region_rights_review` | bool | 公版推荐 | 公版但非全球覆盖时为 true |
| `requires_user_rights` | bool | 来源要求时填 | 通用/授权来源是否要求用户自持权利 |
| `rights_declared_at` | string/null | 派生授权时填 | `YYYY-MM-DD` |
| `outputs` | list[string] | 是 | 只能含 `txt/docx/outline` |
| `created_at` | string | 是 | `YYYY-MM-DD` |
| `purpose` | string | 推荐 | 小说最终用途，如 `传统小说/漫剧源书/微短剧源书/短读/短篇/出海译制底稿/自定义`；用途先于平台决定交付形态，红果/抖音等差异写入 `target_platform` |
| `target_platform` | string | 推荐 | 起名、评分、章长权重使用 |
| `draft_mode` | string | 推荐 | `极速初稿/稳妥初稿/商业连载/漫剧源书`，决定写章 gate 密度 |
| `chapter_granularity` | string | 推荐 | `逐章/小批/全书草稿`，决定生成任务包的批次 |
| `ai_text_usage` | string/null | 推荐 | `AI-generated/AI-assisted/未使用AI文本`，导出发布前披露留痕 |

### 规模字段

`create/spinoff/rewrite` 使用统一 scale：

| scale | 单章建议篇幅 target | 质检预警带宽 min-max | 默认章数 |
|---|---|---|---|
| `漫剧` | 1000-1500 | 800-1800 | 90 |
| `微短剧` | 1500-2500 | 1200-3000 | 50 |
| `medium` | 3000-5000 | 2500-6000 | 20 |
| `long` | 5000-8000 | 4000-10000 | 40 |
| `short` | 6000-10000 | 5000-15000 | 3 |

字段：
- `scale`
- `target_chapters`
- `target_words_per_chapter`
- `target_wordcount_min_max`
- `demo_chapters`

`target_words_per_chapter` 与 `target_wordcount_min_max` 是历史字段名，当前语义分别是单章建议篇幅与 review 默认预警带宽。旧项目缺该字段时，`mechanical_check.py` 会按 `scale.min_max` 或 `target_words_per_chapter` 推导；再缺才回退旧漫剧带宽。该带宽只生成预警，不允许单独裁定拆章。

### kind 专属字段

| kind | 专属字段 |
|---|---|
| `spinoff` | `spinoff_character`, `mode`, `branch_point`, `person` |
| `rewrite` | `rewrite_type`, `person` |
| `expand` | `ratio`, `orig_chars_estimate`, `target_chars_estimate` |
| `condense` | `ratio`, `target`, `orig_chars_estimate`, `target_chars_estimate` |
| `continue` | `mode`, `new_chapters`, `orig_chapter_count_estimate`, `direction_chosen`, `combine_with_original` |
| `create` | `genre`, `premise`, `ingested`, `person` |

## `_进度.md` Schema

所有项目第一屏都带机器 schema marker：

```markdown
<!-- novel-progress-schema: 1; kind: <kind> -->
```

**有两种 `_进度.md` 物理布局，分别由两个 reader 负责（这是实现现状，别混用）：**

1. **章节矩阵型（实际默认）** — `init_project.py`（create 与各派生 skill 都）调 `novel/_lib/novel_contract.py:build_progress_markdown` 生成：`## 状态总览` 下一张「章节 × 标题 × 字数 × 各 routing 阶段」矩阵表，逐章逐阶段打勾。**新建项目落地的就是这种**。它由 `skills/novel/progress.py` 逐章路由读写、`skills/novel/scripts/post_write.py` 写后更新。
2. **同构阶段清单型** — 形如下面两段、用 `novel-create-stage-table` / `novel-derived-stage-table` marker + `<!-- stage:<key> -->` 逐项的阶段级清单，由 `skills/novel-craft/scripts/progress.py` 读取。**注意**：该 reader 遇到章节矩阵型会打印 `[redirect]` 指向 `novel/progress.py`（它只读阶段清单型）。

> 即：阶段级查询走 `novel-craft/scripts/progress.py`（清单型）；逐章生产进度走 `novel/progress.py`（矩阵型，init 实际产物）。下面「原创阶段表 / 派生同构阶段表」是**流程语义**定义（每个 stage 的含义/负责人/回流），与上面哪种物理布局无关，两种 reader 都对齐同一套 stage key。

阶段清单型样例 —— 原创 `create`：

```markdown
## 原创阶段（机器读）
<!-- novel-create-stage-table: 1; kind: create -->
- [x] 项目骨架 <!-- stage:setup -->
- [ ] 创作蓝图 <!-- stage:blueprint -->
- [ ] 设定圣经 / 角色卡 / 世界观 <!-- stage:setting_bible -->
- [ ] 书名 <!-- stage:title -->
- [ ] 章纲 <!-- stage:outline -->
- [ ] Demo gate <!-- stage:demo -->
- [ ] 批量写章节 <!-- stage:draft -->
- [ ] 一致性回扫 <!-- stage:review -->
- [ ] 导出 <!-- stage:export -->
```

阶段清单型样例 —— 派生类：

```markdown
## 同构阶段（机器读）
<!-- novel-derived-stage-table: 1; kind: <kind> -->
- [x] 项目骨架 <!-- stage:setup -->
- [ ] <kind 专属源模型> <!-- stage:source_model -->
- [ ] 变换 spec / 方向确认 <!-- stage:direction_spec -->
- [ ] 书名 <!-- stage:title -->
- [ ] 章纲 <!-- stage:outline -->
- [ ] Demo gate <!-- stage:demo -->
- [ ] 批量写章节 <!-- stage:draft -->
- [ ] 一致性回扫 <!-- stage:review -->
- [ ] 导出 <!-- stage:export -->
```

## 原创阶段表

| stage | 含义 | 负责人 | 失败回流 |
|---|---|---|---|
| `setup` | 建项目骨架、写 `_meta/_设置/_进度` | `novel-create/scripts/init_project.py` | 重跑 init 或换 `--out` |
| `blueprint` | 把想法补成创作蓝图：premise/主角/金手指/爽点/冲突/风格卡 | `novel-create` | 回立项访谈补缺口 |
| `setting_bible` | 建设定圣经、角色卡、世界观和一致性约束 | `novel-create` + `setting-bible.md` | 回创作蓝图或重建设定约束 |
| `title` | 书名候选、评分、用户选择 | `novel-title` | 重跑 `novel-title` |
| `outline` | 按 scale、平台节奏和三幕/钩子编章纲 | `novel-craft/references/outline.md` | 回蓝图/设定调整主线 |
| `demo` | 前 1-3 章验证文风、爽点、钩子、设定自洽 | `novel-create` | 回蓝图/设定/章纲/风格卡，不批量写 |
| `draft` | 批量写余下章节：先出章节任务包，再由 agent/子代理逐章写，写完填状态增量 | `novel-craft/scripts/draft_packets.py` + `novel-create/agent` | 就地修章、重出任务包，或回 `demo` |
| `review` | 机检 + 人判一致性回扫 | `novel-review` | 按报告回源头阶段 |
| `export` | QA gate 通过后导出 txt/docx/outline | `novel-craft/scripts/export.py` | 先清 `review_report/score_report` 阻断；再修 `_meta/章节` |

## 派生同构阶段表

| stage | 含义 | 负责人 | 失败回流 |
|---|---|---|---|
| `setup` | 建项目骨架、抽原作、写 `_meta/_设置/_进度` | `init_project.py` | 重跑 init 或换 `--out` |
| `source_model` | 吸收原作，建锚点/骨架/末章状态/新设定底稿 | 当前派生 skill | 回本阶段补设定/骨架 |
| `direction_spec` | 明确变换目标：外传时间线、改动方向、扩缩策略、续写方向 | 当前派生 skill | 回 `source_model` 或改变换目标 |
| `title` | 书名候选、评分、用户选择 | `novel-title` | 重跑 `novel-title` |
| `outline` | 按 scale 和节拍编章纲 | `novel-craft/references/outline.md` | 回 `direction_spec` |
| `demo` | 前 1-3 章验证文风/方向/设定 | 当前派生 skill | 回设定/章纲/口吻卡，不批量写 |
| `draft` | 批量写余下章节：先出章节任务包，再由 agent/子代理逐章写，写完填状态增量 | `novel-craft/scripts/draft_packets.py` + 当前派生 skill/agent | 就地修章、重出任务包，或回 `demo` |
| `review` | 机检 + 人判一致性回扫 | `novel-review` | 按报告回源头阶段 |
| `export` | QA gate 通过后导出 txt/docx/outline | `novel-craft/scripts/export.py` | 先清 `review_report/score_report` 阻断；再修 `_meta/章节` |

## QA gate

`scripts/report_gate.py <作品根>` 是 rights/review/score 到调度器的硬闸：

- 读取 `_meta.json` 和 `小说/source_manifest.json`：显式 `rights_status=unknown` 或来源要求用户权利但缺 `rights_declared/rights_declared_at` → `RIGHTS-*` 阻断。
- 公版来源必须区分 `rights_covered_regions` 与 `distribution_regions`。普通文本导出缺发行区先 warning；导出 `combine`、商业连载、目标平台含红果/番茄/抖音/漫剧时，缺发行区或发行区不被来源覆盖 → `RIGHTS-PD-REGION-*` 阻断。
- Export 硬闸默认要求 `审稿/review_report.json` 存在；缺失即 `REVIEW-MISSING` 阻断。`progress.py` 只做续跑提示，缺报告先显示 warning。
- 读取 `source_snapshot`：review/score 报告必须绑定正文 hash。正文文件 hash、aggregate hash 不匹配，或 review 报告生成后 `章节/` 新增/删除文件，进入 `REVIEW-SNAPSHOT` / `SCORE-SNAPSHOT`；export 阶段阻断，progress 阶段提示。
- 读取 `审稿/review_report.json`：任一 `blocking=true` 或 `severity=blocking` → 阻断。
- 读取 `评分/score_report.json`：`verdict=大改/弃稿重立` → 阻断。
- 读取 `评分/score_report.json.market_baseline.freshness`：`blocking=true` → `SCORE-BASELINE` 阻断；只有 `score_report.waivers[]` 或 `审稿/waiver_log.jsonl` 存在同 `baseline_date + freshness_status` 作用域的 `score_baseline_freshness` 时降为 warning。
- 缺 `score_report.json`：商业连载、漫剧源书、目标平台含红果/番茄/抖音/漫剧时在 export / go-no-go 节点阻断；`drafting` 阶段不阻断，因为还没有可评分正文样本。
- `review` / `score` / `export` 阶段要求章节写后闭环：`审稿/state_delta_第NN章.json` 必须存在，并且已合并进 `审稿/state_ledger.json.chapter_deltas.chapter_NN`。
- 商业/平台/出海导出时要求 `合规/ai_usage.json`；`AI-generated` / `AI-assisted` 文本必须填写 `human_contribution`，记录创意、人工改写、审稿取舍等人类贡献。新版披露建议同时填 `disclosure_detail.text_directness/human_steering/replaceability/direct_incorporation/review_steps`，以便按平台或读者要求解释 AI 介入直接程度、人工 steering、可替代性和复核链路。
- 所有绕过 gate 的动作必须写 `审稿/waiver_log.jsonl`；报告自身也应带 `waivers[]`。waiver 必须写 `scope`，能绑定章节、报告、baseline 或具体 gate 时不能留空。
- `scripts/progress.py` 会展示阻断和推荐回流 stage；`scripts/export.py` 默认阻断导出。

## Draft packet

`scripts/draft_packets.py <作品根> --chapter N|--range A-B|--next` 是 draft 阶段的共享编排器：

- 默认要求 `审稿/demo_gate.json.status == passed`，防止 Demo 未过就批量写。
- 生成 `写作任务/第NN章.md`，内含创作蓝图/设定/章纲路径、本章章纲、上一章承接、Demo 风格锚点、状态账本摘录、输出格式要求。
- 首次运行会创建 `审稿/state_ledger.json`；每章写完后按任务包模板填 `审稿/state_delta_第NN章.json`，再跑 `novel-review`。
- 它不调用 AI、不替代写作，只把“每章该喂什么上下文”固化，避免长篇批量生成时上下文漂移。

## AI 使用披露

发布或交平台前跑 `scripts/ai_usage.py <作品根> --text-mode AI-generated|AI-assisted|未使用AI文本 --human-contribution "<人工贡献>"`，并尽量补：

- `--text-directness direct_generation|outline_to_draft|revision_only|brainstorming_only|none`
- `--human-steering "<人工如何设定目标、蓝图、取舍和最终责任>"`
- `--replaceability replaceable|assistive_non_replaceable|human_primary|unknown`
- `--direct-incorporation none|minor_phrases|substantial_passages|full_draft`
- `--review-step "<复核步骤>"`（可重复）

产出：

- `合规/ai_usage.json`
- `合规/AI使用说明.md`

这只做项目留痕和平台披露准备，不替代法律意见；不同平台发布前仍按最新规则复核。

## 维护原则

- 改分档、输出格式、kind 后缀、阶段 key：先改 `contract.py`，再同步本文件和测试。
- 各 skill 不再复制分档表；只引用 `contract.py` / 本文件。
- `_进度.md` 的人类表述可变，`stage:<key>` 不随文案变化。
