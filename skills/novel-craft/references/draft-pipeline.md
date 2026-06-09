# Draft pipeline

本文件定义 `draft` 阶段的可复跑写章闭环。适用于 create / spinoff / rewrite / continue / expand 等所有需要批量写章节的 novel 项目。

## 入口条件

- `_meta.json` 存在，含 `kind/target_chapters/target_words_per_chapter/demo_chapters`。`target_chapters` 必须由 init 脚本写入或用户显式改入元数据；不能只写在 `_设置.md` / `_进度.md` 的人类文案里。
- `设定/章纲.md` 已经用户确认。
- `审稿/demo_gate.json.status == passed`。未通过时只能写 Demo 或准备包，不能批量写余章。
- `_设置.md` 已落 `小说生成模式` 与 `章节生成粒度`；缺则按 `_偏好约定.md` 问一次或用全局默认预填。

## 三档小说生成模式

| 模式 | 适合 | gate 密度 |
|---|---|---|
| `极速初稿` | 用户要尽快得到可读草稿/大纲化正文 | Demo 过后按小批写，轻量机检，最后全量 review |
| `稳妥初稿` | 默认；兼顾速度和一致性 | 每章任务包 + 每 3-5 章轻量 review + 全量 review |
| `商业连载` | 要投平台或长期连载 | 每章任务包 + 每章状态增量 + 小批 score/review，开篇三章重点打磨 |
| `漫剧源书` | 主要服务 novel2drama | 章纲和正文优先镜头化、事件密度、角色动作可视化；输出建议含 `n2d` |

## 执行闭环

1. 生成任务包：

```bash
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --chapter 4
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --range 4-8
python3 skills/novel-craft/scripts/draft_packets.py "<作品根>" --next
```

`--allow-missing-demo` 只能用于准备包或修复流程，不代表批量写章 gate 通过；脚本会在任务包、`审稿/state_ledger.json.waivers[]` 和 `审稿/waiver_log.jsonl` 中记录 `missing_demo_gate`。

2. 按 `写作任务/第NN章.md` 写入 `章节/第NN章.md`。
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

- 本章输出文件、目标字数、人称、目标平台、小说生成模式。
- 必读源文件路径：蓝图、设定圣经、角色卡、世界观、章纲、Demo gate、状态账本。
- 本章章纲原文。
- 上一章结尾摘录。
- Demo 风格锚点、读者承诺、设定硬约束、禁止漂移项。
- 状态增量 JSON 模板。

## 反模式

| 错误 | 纠正 |
|---|---|
| 一次性把全书都塞给模型 | 先出任务包，按 `章节生成粒度` 分批 |
| 只看章纲不看状态账本 | 每章写完更新 state delta / ledger |
| Demo 没通过就批量写 | 回 Demo gate；必要时只用 `--allow-missing-demo` 做准备包，并保留 `missing_demo_gate` waiver |
| 写完不回扫 | 至少机检 + 小批 review，导出前必须过 QA gate |
