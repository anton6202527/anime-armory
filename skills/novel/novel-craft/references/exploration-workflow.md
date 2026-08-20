# 非正史探索通道：human-first seed → 试写 → hash-bound 晋升候选

## 目的

探索通道给“还不知道故事真正是什么”的阶段留一块不受正式蓝图、章节状态账本和发布 gate 约束的空间。它适合角色试镜、关键场景试写、不同 POV、声音测试、结构实验和错误结局。

它不是正式生产阶段，也不是另一套正史：

- 所有产物只落在作品根 `探索/`。
- 不写 `章节/`、`设定/`、`审稿/`、`state_delta`、`state_ledger` 或 `_进度.md`。
- `novel-gate`、逐章 `post_write` 和正式导出不会把 `探索/` 当正文输入。
- “晋升”只生成非正史候选和决策记录；作者仍须在对应的蓝图、设定、章纲、Demo 或章节流程中单独吸收，并重新走该阶段的人审/hash/gate。

## 一、先冻结作者自己的种子

在展示市场基准、爆款案例、AI premise 候选或续写建议之前，先让作者用自己的话留下原始输入。可以很短，但要保留原文，而不是由 AI 帮其润色后的摘要。推荐至少包含：

- 忘不掉的意象、人物或关系；
- 真正想追问的问题；
- 不希望作品被改造成什么；
- 期待读完后的余味；
- 尚未想通的矛盾。

新建原创项目时可在初始化命令里一起冻结：

```bash
python3 skills/novel/novel-create/scripts/init_project.py \
  --title "<暂定名>" --genre "<题材或待确认>" --premise "<只做检索用的一句话>" \
  --scale short --purpose "传统小说" --platform "跨平台" \
  --human-seed-file "<作者原始种子.md>" \
  --human-seed-author "<作者>" --human-first-confirmed
```

已有项目用独立命令：

```bash
python3 skills/novel/novel-craft/scripts/exploration.py "<作品根>" seed \
  --from-file "<作者原始种子.md>" \
  --author "<作者>" --label "立项前原始种子" --human-first-confirmed
```

`--human-first-confirmed` 是事实声明：只在内容确实形成于 AI/市场建议出现前时使用。后来的新想法可以作为探索稿登记，但不得倒签为 human-first。每次 capture 都生成新的不可变快照：

```text
探索/
├── manifest.json
└── 种子/
    ├── seed_<time>_<id>.md
    └── seed_<time>_<id>.json
```

种子 JSON 记录作者、确认语义、正文 SHA-256 和字节数。`manifest.json` 另行记录该 JSON sidecar 的 `metadata_path` 与 `metadata_sha256`；sidecar 不记录自己的 hash，以免自引用。原文或 sidecar 变化后都不要改旧记录；重新 capture，保留思想演化。

## 二、试写要回答问题，不承担交付义务

一次探索只问一个高杠杆问题，例如：

- 角色独处时真正会做什么，而非角色卡说他会做什么？
- 换成旁观者 POV，故事的道德重心是否改变？
- 先写终局选择，能否反推出真正的主题？
- 去掉核心机制后，人物关系是否仍值得读？
- 同一冲突用克制、黑色幽默、冷峻三种声音，哪种最有生命？

先在任意 UTF-8 `.md` / `.txt` 文件完成试写，再把当下版本登记为不可变快照：

```bash
python3 skills/novel/novel-craft/scripts/exploration.py "<作品根>" register \
  --file "<试写稿.md>" \
  --title "雨夜角色试镜" \
  --kind character_audition \
  --question "她在无人观看时还会不会救对手？" \
  --creator "<作者或执行者>" --authorship human \
  --seed-id "<seed_id>"
```

`--kind` 可用：`character_audition`、`scene_probe`、`pov_probe`、`voice_probe`、`structure_probe`、`ending_probe`、`other`。`--authorship` 必须如实写 `human`、`ai-assisted` 或 `ai-generated`。

修改已有探索稿时，不覆盖已登记快照；另存新文件并重新登记，用 `--parent-draft-id` 建版本血缘。系统会绑定父稿和 human seed 的当前 SHA；任一上游快照被篡改，登记或晋升会停止。

探索稿与种子一样采用双重绑定：正文快照由 `sha256` 绑定，JSON sidecar 由 manifest 中的 `metadata_sha256` 绑定。`status` 会分别报告 `snapshot.integrity` 与 `sidecar.integrity`；任一项不是 `ok`，顶层 `integrity_ok` 就是 `false`。

## 三、先看 hash，再做明确选择

只读查看全部探索产物及完整性：

```bash
python3 skills/novel/novel-craft/scripts/exploration.py "<作品根>" status --json
```

`author_workflow.py` 也会把这份状态作为入口证据展示：没有探索区只是可选提示；已有 human-first seed、探索稿和晋升候选会显示数量，但不会替任何正式阶段打勾；只要探索区存在且完整性损坏，就先阻断吸收，避免错误证据进入正史。

要把某稿列为“值得进入正式流程的候选”，必须由复核人明确选择当前 SHA、说明原因和拟进入哪个阶段：

```bash
python3 skills/novel/novel-craft/scripts/exploration.py "<作品根>" decide \
  --draft-id "<draft_id>" \
  --decision promote_candidate \
  --expected-sha256 "<status 给出的 current_sha256>" \
  --reviewer "<作者/编辑>" \
  --reason "人物在这一版第一次做出了与自我叙述相冲突的选择" \
  --target blueprint
```

这一步生成：

```text
探索/
├── 决策/decision_<time>_<id>.json
└── 晋升候选/<draft_id>__<sha>__<decision>.md
```

决策文件绑定探索稿路径、SHA、human seed、父稿、复核人、理由和目标阶段；候选副本与所选稿逐字节同 hash。目标只表达编辑意图：

- `blueprint`：把发现转写为蓝图变更，重新执行 blueprint 人审批准；
- `setting`：由作者改设定圣经/角色卡，再重新批准 setting；
- `outline`：回章纲审查；
- `demo`：以正式 Demo 任务包重写，不直接复制为通过的 Demo；
- `chapter`：按正式写章包吸收，再走 `state_delta`、对账和 `post_write`；
- `style`：只提炼可迁移的声音规则，不照搬句子；
- `other`：在理由中说明正式落点。

搁置或否决也应留决策，避免下一轮反复生成同一路径：

```bash
python3 skills/novel/novel-craft/scripts/exploration.py "<作品根>" decide \
  --draft-id "<draft_id>" --decision hold \
  --reviewer "<作者/编辑>" --reason "声音有效，但人物动机仍未显影"
```

## 四、晋升后的编辑问题

候选进入正式流程前，作者至少回答：

1. 这次试写发现了什么，而非“哪一版更流畅”？
2. 它改变蓝图、人物、世界规则、章纲或文风中的哪一项？
3. 哪些只是试写条件，不应进入正史？
4. 与已批准蓝图/设定冲突时，是放弃候选，还是明确重签上游？
5. 若使用 AI，人工选择、改写和终稿控制应如何进入 `合规/ai_usage.json`？

正式吸收必须是可见的编辑动作。不得增加“自动复制到第 NN 章”的捷径：它会绕过章节任务包、状态增量、设定对账和 Demo gate，也会把一次有用实验误当成已经成立的正史。

## Schema 摘要

`探索/manifest.json`：

```json
{
  "schema_version": 1,
  "kind": "novel_exploration_manifest",
  "canon_status": "non_canon",
  "formal_pipeline_effect": "none",
  "seeds": [],
  "drafts": [],
  "decisions": []
}
```

稳定不变量：

- seed / draft 正文与各自 sidecar 均由 manifest 绑定 SHA-256，candidate 绑定其真实文件 SHA-256；
- `promote_candidate` 必须显式提供当前 SHA、复核人、理由、目标；
- 文件 hash 漂移时只能重新登记，旧决策不会静默迁移；
- 所有记录的 `canon_status` 都是 `non_canon` 或 `non_canon_candidate`；
- 正式状态账本、进度和 gate 对探索区零副作用。

## 常见错误

| 错误 | 纠正 |
|---|---|
| AI 先给五个点子，再让作者选一个当“原始种子” | 先冻结作者原文，再展示 AI/市场信息 |
| 在 `章节/` 里试写并指望 gate 忽略 | 试写只放 `探索/`，正式吸收另走章节流程 |
| 改掉已登记探索稿 | 新版本另登记，并用 `--parent-draft-id` 绑定血缘 |
| 只写“这版更好”就晋升 | 说明发现、目标阶段与为什么值得改变正式设计 |
| 晋升后直接复制成正式章 | 禁止；候选不是正史，需任务包、状态对账和正式 gate |
