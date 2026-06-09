# novel-* 契约层

本文件定义 novel 系列的机器契约。正文工艺可以在各 skill 自由展开，但脚本、导出、续跑和质检只应依赖这里定义的稳定字段。

机器单一真值源：`skills/novel-craft/scripts/contract.py`。

## `_meta.json` Schema

所有 `写小说/<项目>/` 根目录必须有 `_meta.json`。

### 通用字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `schema_version` | int | 是 | 当前为 `1` |
| `kind` | string | 是 | `create/spinoff/rewrite/expand/condense/continue` |
| `title` | string/null | 是 | 用户选定书名；未定为 null |
| `source_title` | string | 派生类必填 | 原作名；`create` 可无 |
| `rights_status` | string | 是 | `original/public-domain/user-declared/...` |
| `rights_declared_at` | string/null | 派生授权时填 | `YYYY-MM-DD` |
| `outputs` | list[string] | 是 | 只能含 `txt/docx/outline/n2d` |
| `created_at` | string | 是 | `YYYY-MM-DD` |
| `target_platform` | string | 推荐 | 起名、评分、章长权重使用 |
| `draft_mode` | string | 推荐 | `极速初稿/稳妥初稿/商业连载/漫剧源书`，决定写章 gate 密度 |
| `chapter_granularity` | string | 推荐 | `逐章/小批/全书草稿`，决定生成任务包的批次 |
| `ai_text_usage` | string/null | 推荐 | `AI-generated/AI-assisted/未使用AI文本`，导出发布前披露留痕 |

### 规模字段

`create/spinoff/rewrite` 使用统一 scale：

| scale | 字数/章 target | min-max | 默认章数 |
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
- `demo_chapters`

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

所有项目第一屏应包含：

```markdown
<!-- novel-progress-schema: 1; kind: <kind> -->
```

所有项目都应包含机器读阶段表；`progress.py` 优先读取 `stage:<key>`，人类可读的详细准备表、章节表、回扫表可以保留在后面。

原创 `create` 项目阶段表：

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

派生类项目阶段表：

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
| `export` | QA gate 通过后导出 txt/docx/outline/n2d | `novel-craft/scripts/export.py` | 先清 `review_report/score_report` 阻断；再修 `_meta/章节` |

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
| `export` | QA gate 通过后导出 txt/docx/outline/n2d | `novel-craft/scripts/export.py` | 先清 `review_report/score_report` 阻断；再修 `_meta/章节` |

## QA gate

`scripts/report_gate.py <作品根>` 是 review/score 到调度器的硬闸：

- Export 硬闸默认要求 `审稿/review_report.json` 存在；缺失即 `REVIEW-MISSING` 阻断。`progress.py` 只做续跑提示，缺报告先显示 warning。
- 读取 `source_snapshot`：review/score 报告必须绑定正文 hash。正文文件 hash、aggregate hash 不匹配，或 review 报告生成后 `章节/` 新增/删除文件，进入 `REVIEW-SNAPSHOT` / `SCORE-SNAPSHOT`；export 阶段阻断，progress 阶段提示。
- 读取 `审稿/review_report.json`：任一 `blocking=true` 或 `severity=blocking` → 阻断。
- 读取 `评分/score_report.json`：`verdict=大改/弃稿重立` → 阻断。
- 读取 `评分/score_report.json.market_baseline.freshness`：`blocking=true` → `SCORE-BASELINE` 阻断；只有 `score_report.waivers[]` 或 `审稿/waiver_log.jsonl` 存在同 `baseline_date + freshness_status` 作用域的 `score_baseline_freshness` 时降为 warning。
- 缺 `score_report.json`：商业连载、漫剧源书、目标平台含红果/番茄/抖音/漫剧时阻断；其他项目 warning。
- 所有绕过 gate 的动作必须写 `审稿/waiver_log.jsonl`；报告自身也应带 `waivers[]`。waiver 必须写 `scope`，能绑定章节、报告、baseline 或具体 gate 时不能留空。
- `scripts/progress.py` 会展示阻断和推荐回流 stage；`scripts/export.py` 默认阻断导出。

## Draft packet

`scripts/draft_packets.py <作品根> --chapter N|--range A-B|--next` 是 draft 阶段的共享编排器：

- 默认要求 `审稿/demo_gate.json.status == passed`，防止 Demo 未过就批量写。
- 生成 `写作任务/第NN章.md`，内含创作蓝图/设定/章纲路径、本章章纲、上一章承接、Demo 风格锚点、状态账本摘录、输出格式要求。
- 首次运行会创建 `审稿/state_ledger.json`；每章写完后按任务包模板填 `审稿/state_delta_第NN章.json`，再跑 `novel-review`。
- 它不调用 AI、不替代写作，只把“每章该喂什么上下文”固化，避免长篇批量生成时上下文漂移。

## AI 使用披露

发布或交平台前跑 `scripts/ai_usage.py <作品根> --text-mode AI-generated|AI-assisted|未使用AI文本`，产出：

- `合规/ai_usage.json`
- `合规/AI使用说明.md`

这只做项目留痕和平台披露准备，不替代法律意见；不同平台发布前仍按最新规则复核。

## 维护原则

- 改分档、输出格式、kind 后缀、阶段 key：先改 `contract.py`，再同步本文件和测试。
- 各 skill 不再复制分档表；只引用 `contract.py` / 本文件。
- `_进度.md` 的人类表述可变，`stage:<key>` 不随文案变化。
