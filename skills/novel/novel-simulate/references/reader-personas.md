# 合成阅读视角 + 信号 schema

## 内置阅读视角（`simulate_panel.py` 预设）

| ID | 名称 | 关注 | 字面观察词表 |
|---|---|---|---|
| `rookie` | 小白爽文党 | 节奏/升级/反杀/不憋屈 | 打脸·逆袭·碾压·突破·反杀·升级·解气·吊打… |
| `logic` | 逻辑考据党 | 设定自洽/体系/无降智 | 因为·所以·原理·规则·体系·境界·代价·破绽… |
| `emote` | 情感互动党 | 弧光/CP/张力/金句 | 心疼·温柔·守护·告白·暧昧·心动·眼泪·羁绊… |
| `critic` | 毒舌老书虫 | 同质化/文笔/新意 | 退婚·老爷爷·系统·穿越·重生·赘婿·扮猪吃虎… |

> 四项都是编辑视角预设，不是真实人群分类。`critic` 的词表用于定位熟悉母题，不是“命中越多越差”；其它词表也不是“越多越好”。每次判断都要回到具体句段、叙事功能和真人证据。

## 项目级自定义 cohort

默认位置：`<作品根>/设定/reader_probe_cohort.json`。CLI 未显式传 `--personas` / `--cohort` / `--viewpoint` 时自动读取。也可用 `--cohort <path>` 显式指定：

```json
{
  "schema_version": 1,
  "kind": "novel_reader_probe_cohort",
  "name": "慢热关系视角组",
  "description": "只描述阅读偏好，不声明代表任何人群。",
  "perspectives": [
    {
      "id": "slow_burn",
      "name": "慢热关系视角",
      "focus": "关系细微移动与未说出口的选择",
      "keywords": ["犹豫", "试探", "沉默"],
      "probe_questions": ["关系变化是否落实为一个不可逆选择？"],
      "reading_history": "熟悉慢热关系叙事",
      "genre_familiarity": "高",
      "tolerances": "可接受低事件密度，但不能接受关系静止",
      "expectations": "每个场景至少改变理解、关系或选择之一"
    }
  ]
}
```

约束：

- 最多 12 个视角；`id` 以英文字母开头，只含字母、数字、`_`、`-`。
- `keywords` 最多 64 项，只做字面计数，不接受正则；没有词表也可只做定性问题。
- `probe_questions` 最多 8 项；其余允许字段只有 `reading_history`、`genre_familiarity`、`tolerances`、`expectations`。
- 未知字段会拒绝，避免把年龄、性别、族裔等人口统计画像伪装成可代表人群的“合成读者”。输出固定声明 `population_representativeness=none`。
- 显式 CLI 输入不会偷偷混入平台默认视角；需要内置视角与自定义视角并用时，同时传 `--personas` 与 `--cohort` / `--viewpoint`。
- 作品内 cohort 只持久化相对路径和 SHA。作品外 CLI 文件只记录 basename + SHA，不把绝对路径写入产物。

## 信号 schema v3（`评分/reader_panel_signals.json`）

```json
{
  "date": "2026-08-20",
  "schema_version": 3,
  "kind": "novel_synthetic_reader_probe",
  "evidence_type": "synthetic_probe",
  "validation_status": "unvalidated",
  "decision_authority": "context_only",
  "numeric_score_eligible": false,
  "analysis_mode": "surface_signals_only",
  "signal_only": true,
  "scope": "opening",
  "scope_chapter": null,
  "chapters_read": [1, 2, 3],
  "sampled_chars": 6200,
  "source_snapshot": {
    "schema_version": 1,
    "kind": "novel_text_snapshot",
    "mode": "reader_probe:opening:3",
    "files": [
      {"path": "章节/第01章.md", "chapter": 1, "sha256": "<64位SHA-256>", "bytes": 8240},
      {"path": "章节/第02章.md", "chapter": 2, "sha256": "<64位SHA-256>", "bytes": 7912},
      {"path": "章节/第03章.md", "chapter": 3, "sha256": "<64位SHA-256>", "bytes": 8061}
    ],
    "aggregate_hash": "<scope聚合SHA-256>"
  },
  "cohort": {
    "name": "慢热关系视角组",
    "perspective_ids": ["slow_burn"],
    "synthetic_probe_only": true,
    "population_representativeness": "none"
  },
  "perspectives": {
    "slow_burn": {
      "name": "慢热关系视角",
      "focus": "关系细微移动与未说出口的选择",
      "probe_questions": ["关系变化是否落实为一个不可逆选择？"],
      "keyword_surface": {
        "available": true,
        "literal_hits": 9,
        "density_per_kchar": 1.45,
        "matched_terms": {"犹豫": 3, "试探": 4, "沉默": 2}
      }
    }
  },
  "surface_signals": {
    "hook_tail_markers": {
      "tail_window_chars": 160,
      "chapter_tails_observed": 3,
      "chapter_tails_with_marker_hits": 2,
      "literal_marker_hits": 5,
      "density_per_kchar": 11.11,
      "matched_markers": {"突然": 2, "竟然": 1, "？": 2}
    },
    "lexical_4gram": {
      "cjk_4gram_count": 6197,
      "unique_cjk_4gram_count": 5020,
      "unique_cjk_4gram_ratio": 0.81
    },
    "cliche_terms": {
      "literal_hits": 13,
      "density_per_kchar": 2.1,
      "matched_terms": {"系统": 8, "重生": 5}
    }
  },
  "aggregate_score": null,
  "aggregate_score_policy": "forbidden_unless_calibrated_against_real_reader_outcomes",
  "prohibited_inferences": [
    "retention_probability",
    "population_preference",
    "demographic_behavior"
  ]
}
```

### 分量的精确定义

- `hook_tail_markers`：每章末 160 字内 `HOOK_MARKERS` 的字面命中、覆盖章数和千字密度。它只证明出现过标记，不证明钩子有效，也不认为标记越多越好。
- `lexical_4gram`：抽取全部 CJK 字符后，以滑动窗口计算四字片段总数、唯一数和去重比。低比率可能来自机械重复，也可能来自有意复沓；高比率不等于信息丰富或文笔好。
- `cliche_terms`：`CLICHE_KW` 的字面命中。命中可能是套路照搬、反套路讨论、人物对白或无关同词，必须回正文判定。
- `keyword_surface`：各视角自有词表的字面命中。没有词表时 `available=false`、`density_per_kchar=null`，不据此推断叙事功能缺失。
- 所有密度都只为了让不同长度取样可复算地并排查看；没有行业基准、置信区间或统一方向，不能相加。

### scope 与新鲜度

- `opening` 绑定**生成时实际存在的前 3 个编号章节**；若当时只有 1–2 章，只绑定已有章。后来新增章节进入前三、删除前三章或其中正文 hash 改变，探针即 stale。
- `chapter` 必须写 `scope_chapter=N` 并只绑定精确第 N 章。该章不存在时生成命令报错，不回退到第一章；新增无关章节不会让这个单章探针过期。
- `source_snapshot.files[].path` 只能是作品根相对路径；消费者先重建当前实际 scope 文件集，再验证 SHA。
- `fresh` 才能展示分量；`stale` 只提示重跑并隐藏旧值。schema v1/v2 没有快照，状态为 `unknown`，不能伪装 fresh。

## v1/v2 兼容

旧 `reader_panel_signals.json` 可能含 `retention_proxy` / `retention_prior`、`hook_strength`、`lexical_diversity`、`cliche_density_per_kchar`。消费者仍能打开旧文件，但必须：

1. 忽略并不展示两个旧聚合留存字段；
2. 不按旧聚合值建立编辑任务、阈值或调分；
3. 旧值只可作为历史档案人工打开，score/edit/revision 不把它展示为当前分量；
4. 建议重跑 `simulate_panel.py` 生成 v3 原始命中与计数。

## 行为表面比较 schema v2（`评分/behavioral_signals.json`）

```json
{
  "schema_version": 2,
  "kind": "novel_synthetic_behavior_probe",
  "evidence_type": "synthetic_probe",
  "validation_status": "unvalidated",
  "decision_authority": "context_only",
  "numeric_score_eligible": false,
  "automatic_constraint_eligible": false,
  "prediction_chapters": [
    {
      "chapter": 7,
      "prediction_count": 5,
      "pairwise_surface_difference": 0.63,
      "next_chapter_max_surface_overlap": 0.41,
      "next_chapter_available": true,
      "interpretation": "literal_2gram_comparison_only"
    }
  ],
  "survey_chapters": [
    {
      "chapter": 7,
      "response_count": 3,
      "annotations": {
        "bored": [{"perspective": "logic", "span": "中段排位说明"}],
        "confused": [],
        "disbelief": []
      },
      "recall_previous_chapter_surface_overlap": {"logic": 0.32},
      "interpretation": "synthetic_annotations_and_literal_overlap_only"
    }
  ],
  "questions": [
    {
      "type": "review_prediction_next_chapter_overlap",
      "question": "重合是有效兑现、类型承诺、偶然同词还是过度明示？",
      "decision_authority": "context_only",
      "automatic_action": null
    }
  ],
  "alerts": [],
  "blocking": 0
}
```

- `pairwise_surface_difference` 只描述预测文本两两 2-gram 差异，不叫“悬念值”，没有越高越好的方向。
- `next_chapter_max_surface_overlap` 只描述预测被下一章开头字面覆盖的最大比率，不叫“意外度”；重合不等于陈词滥调，也不自动要求反转。
- `recall_previous_chapter_surface_overlap` 只描述文本重合，不等于记忆成功/失败、信息留存或弃读。
- bored/confused/disbelief 只保留合成视角标注的 span，再转成正文核对问题；不按多数投票升级为弃书风险、信息事故或 OOC。
- `behavioral_signals.json` 不被 `draft_packets.py` 当负约束消费。若上一章预测文本作为附录出现，标题必须明确 context-only，写章包必须声明作者意图、人物因果和已批准章纲优先。

## 判读铁律

- 表面信号是**未校准观察**；视角输出是合成假设。两者都需编辑回到正文逐条验证。
- 合成探针只负责提出问题、寻找证据、记录分歧；不宣告“某类读者一定会怎样”。
- 合成探针不能给出真实留存、受众占比、人口统计偏好或统计显著性。
- 需要回答真实读者在哪里流失、哪个版本更好时，走 `novel-feedback` 导入真人/平台数据。
