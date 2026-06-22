# Draft pipeline

本文件定义 `draft` 阶段的可复跑写章闭环。适用于 create / spinoff / rewrite / continue / expand 等所有需要批量写章节的 novel 项目。

## 入口条件

- `_meta.json` 存在，含 `kind/target_chapters/target_words_per_chapter/target_wordcount_min_max/demo_chapters`。`target_chapters` 必须由 init 脚本写入或用户显式改入元数据；不能只写在 `_设置.md` / `_进度.md` 的人类文案里。旧项目缺 `target_wordcount_min_max` 时，review 会按 scale/target_words 推导，但新项目必须显式写入。
- `设定/章纲.md` 已经用户确认。
- `设定/读者契约.md` 已经写明核心题旨、读者承诺、好看机制、文学质感和禁偏清单。旧项目缺失时可先按 `references/reader-contract.md` 补一版，再继续批量写章。
- `审稿/demo_gate.json.status == passed`。未通过时只能写 Demo 或准备包，不能批量写余章。
- `_设置.md` 已落 `小说生成模式` 与 `章节生成粒度`；缺则按 `skills/novel-craft/references/选择点与偏好.md` 问一次或用全局默认预填。

## 四档小说生成模式

| 模式 | 适合 | gate 密度 |
|---|---|---|
| `极速初稿` | 用户要尽快得到可读草稿/大纲化正文 | Demo 过后按小批写，轻量机检，最后全量 review |
| `稳妥初稿` | 默认；兼顾速度和一致性 | 每章任务包 + 每 3-5 章轻量 review + 全量 review；`scale=long` 或目标章数 ≥30 时自动升三段式，除非用户显式选 `默认单步` |
| `商业连载` | 要投平台或长期连载 | 默认 Architect → Ghostwriter → Senior Editor 三段式；每章状态增量 + 小批 score/review，开篇三章重点打磨 |

`scale=long` / `target_chapters>=30` / `商业连载` / `漫剧源书`，或 `_设置.md` 写 `小说生成工作流：三步迭代` 时，`draft_packets.py` 的默认 `--step auto` 会一次生成三份任务包：

```bash
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4
# 等价于：
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4 --step trio
```

若项目只需要旧式单包，显式传 `--step full` 或在 `_设置.md` 明确写 `小说生成工作流：默认单步`。只补某一段可传 `--step architect|ghostwriter|editor`。

`_设置.md` 写 `小说生成工作流：边写边自检` 时，`draft_packets.py` 会把每章的自检闭环写进任务包：正文落 `章节/第NN章.md`，状态增量落 `审稿/state_delta_第NN章.json`，然后执行：

```bash
python3 skills/novel/scripts/post_write.py "<作品根>" --chapter 第NN章
```

该 hook 会先跑 `reader_contract_sentry.py`，阻断缺少 `reader_contract_progress` / `theme_alignment` 的章节，再跑状态账本对账、百科更新、逻辑哨兵和力量体系自检；硬闸失败时先修正文或状态增量，再重跑。这个选项不改变单步/三步的写作拆分，只把“写完即自检”的程序化闭环变成用户可选择的工作流。

`小批回扫间隔` 默认 `5章`，可改 `3章` 或 `关闭`。到达回扫点时，任务包和 `flow.py` 会提示：

```bash
python3 skills/novel-review/scripts/mechanical_check.py "<作品根>" --range 1-5 --json-out "<作品根>/审稿/batch_mechanical_第01-05章.json"
```

随后由 AI/人工按 `novel-review/references/checklist.md` 对这一小批集中审文风、节奏、钩子、人设、读者承诺，输出集中修正清单，修完再重跑该窗口机检。小批报告不替代导出前全量 `review_report.json`。

长篇每 3-5 章或每个自然 arc 前，先物化弧段任务包；弧段写完后跑 arc gate：

```bash
python3 skills/novel-craft/scripts/arc_packets.py "<作品根>" --arc 1-5
python3 skills/novel-review/scripts/arc_gate.py "<作品根>" --arc 1-5
```

`arc_gate.py` 专门抓整段没有题旨对齐、连续 3 章不推进读者契约、长窗口只种不收等中段跑偏信号。它不替代逐章 `post_write.py`，而是长篇压力测试。

`draft_queue.py` 同样会在这些项目里初始化 `workflow=trio`，按 pass 认领和标记：

```bash
python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" claim --agent agent-a
python3 skills/novel-craft/scripts/draft_queue.py "<作品根>" done 4 --step architect --agent agent-a
```

三个 pass 都 `done` 后，该章才聚合为 `done`；普通项目仍按整章队列运行。

## 执行闭环

1. 生成任务包：

```bash
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --range 4-8
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --next
```

`--allow-missing-demo` 只能用于准备包或修复流程，不代表批量写章 gate 通过；脚本会在任务包、`审稿/state_ledger.json.waivers[]` 和 `审稿/waiver_log.jsonl` 中记录 `missing_demo_gate`。

2. 按任务包写作：普通项目按 `写作任务/第NN章.md` 写入 `章节/第NN章.md`；三段式项目按 `第NN章_architect.md` 产 beats，按 `第NN章_ghostwriter.md` 产 draft，按 `第NN章_editor.md` 写最终正文；`边写边自检` 项目还必须在任务包要求的位置同步准备 state_delta，并在小批回扫点集中修正最近 3-5 章。
3. 填写 `审稿/state_delta_第NN章.json`，记录人物、关系、伏笔、设定变化。
4. 先对账再合并到 `审稿/state_ledger.json`。如果增量改变了设定圣经，回写 `设定/设定圣经.md` 或 `设定/角色卡.md`。

```bash
python3 skills/novel-craft/scripts/reconcile_ledger.py "<作品根>" --chapter NN --audit
python3 skills/novel-craft/scripts/reconcile_ledger.py "<作品根>" --chapter NN --merge --verified "<作品根>/审稿/state_verify_第NN章.json"
```

`state_verify_第NN章.json` 必须来自人工/LLM 核对，并原样带回 audit prompt 给出的 `chapter_file_hash` 与 `delta_hash`：

```json
{
  "chapter": 4,
  "status": "ok",
  "chapter_file_hash": "<章节/第04章.md 的 sha256>",
  "delta_hash": "<审稿/state_delta_第04章.json 的 sha256>",
  "notes": "delta 与正文一致"
}
```

未经验证的 delta 不能合并；缺少 `chapter` 的泛化核对结论不能合并；正文或 delta 改动导致 hash 不匹配时必须重新 audit。
5. 运行机检：

```bash
python3 skills/novel-review/scripts/mechanical_check.py "<作品根>" --json-out "<作品根>/审稿/mechanical_findings.json"
```

6. LLM/人工按 `novel-review` 清单判定：就地修章、重出任务包，或回 `demo/outline/setting_bible`。

## 单章任务包必须包含

- 本章输出文件、小说用途、建议篇幅、人称、目标平台、小说生成模式。
- 必读源文件路径：蓝图、设定圣经、角色卡、世界观、章纲、Demo gate、状态账本。
- 必读 `设定/读者契约.md`，并在任务包内展开 `reader_contract`：核心题旨、核心戏剧问题、读者承诺、文学质感、好看机制、禁偏清单。
- 本章章纲原文。
- 上一章结尾摘录。
- Demo 风格锚点、读者承诺、设定硬约束、禁止漂移项。
- 状态增量 JSON 模板。
- 如需视觉资产索引，可在 ghostwriter/editor 任务里要求标记人物 `[CHAR_xx]`，地点 `[LOC_xx]`，道具 `[PROP_xx]`，服装 `[OUTFIT_xx]`，特效 `[VFX_xx]`；这些标签只作为小说项目内部写作辅助。

## 反模式

| 错误 | 纠正 |
|---|---|
| 一次性把全书都塞给模型 | 先出任务包，按 `章节生成粒度` 分批 |
| 只看章纲不看状态账本 | 每章写完更新 state delta / ledger |
| 只推进事件不推进读者契约 | 每章至少推进题旨、承诺、关系弧光、秘密揭示、能力代价或文学质感中的一项 |
| Demo 没通过就批量写 | 回 Demo gate；必要时只用 `--allow-missing-demo` 做准备包，并保留 `missing_demo_gate` waiver |
| 写完不回扫 | 至少机检 + 小批 review，导出前必须过 QA gate |
