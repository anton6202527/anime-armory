# Demo gate 机器留痕

Demo gate 通过后必须留下一个机器可读文件，供批量写章、review、score 继续使用。

路径：

```text
审稿/demo_gate.json
```

最小 schema：

```json
{
  "schema_version": 1,
  "kind": "novel_demo_gate",
  "generated_at": "YYYY-MM-DD",
  "project_root": "写小说/<项目>",
  "status": "passed|needs_revision",
  "approved_chapters": ["章节/第1章.md", "章节/第2章.md"],
  "style_anchor": {
    "source_chapter": "章节/第1章.md",
    "pov": "third-limited",
    "sentence_rhythm": "短句/中句/长句比例说明",
    "dialogue_ratio": "高/中/低",
    "signature_moves": ["标志性写法"],
    "banned_drift": ["禁止跑偏项"]
  },
  "reader_promises": ["前3章已经许诺的爽点/悬念"],
  "setting_constraints": ["金手指代价、角色不可漂规则"],
  "reader_contract": {
    "theme": "一句话题旨",
    "dramatic_question": "核心戏剧问题",
    "must_answer": ["终局必须回答的问题"],
    "reader_promises": ["开篇已许诺的爽点/情感/悬念"],
    "aesthetic_register": "文风气质与文学质感",
    "delight_engine": ["这本书持续好看的机制"],
    "banned_drift": ["禁止偏成的题材/口吻/支线"]
  },
  "user_feedback": ["用户审 Demo 后留下的具体修改意见"],
  "score_report_path": "评分/score_report.json",
  "review_report_path": "审稿/review_report.json"
}
```

执行约定：

- `status != passed` 时，不批量写余下章节。
- `draft_packets.py --allow-missing-demo` 只允许生成准备包 / 修复包，不等于 Demo gate 通过；必须在任务包、`审稿/state_ledger.json.waivers[]` 和 `审稿/waiver_log.jsonl` 记录 `missing_demo_gate`。
- 批量写章 prompt 必须喂 `style_anchor`、`reader_promises`、`setting_constraints` 和 `reader_contract`。
- `novel-review` 审文风漂移时，以 `style_anchor.source_chapter` 和 `banned_drift` 为一号对照。
- `novel-review` 审题旨偏移、承诺遗忘、文学质感时，以 `reader_contract` 和 `设定/读者契约.md` 为一号对照。

`reader_contract` 字段说明见 `reader-contract.md`。旧项目只有 `reader_promises` / `setting_constraints` 时仍可继续跑；新项目应补 `设定/读者契约.md` 并在 Demo 通过后同步关键字段。
