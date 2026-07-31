# 派生流水线（rewrite / continue / expand / condense / spinoff 共用后半段）

所有"从一部原作派生出新作"的 novel-* skill 共享同一条机器流水线。各 skill 的 SKILL.md 只需写**自己的 `source_model` / `direction_spec` 映射**，通用机制引本文件，不再各自重述。

## 机器阶段表（不可改）

`_meta.json` / `_进度.md` 必须遵守 `contract.md`。机器阶段 key 固定：

```
setup → source_model → direction_spec → title → outline → demo → draft → review → export
```

- `source_model`：本 skill 从原作**吸收/抽取**了什么（每个 skill 不同——见各自 SKILL.md）。
- `direction_spec`：本 skill 与用户敲定的**改动/方向**契约（每个 skill 不同）。
- 其余阶段（title / outline / demo / draft / review / export）走下面的通用机制。

各 skill 的映射速查：

| skill | source_model | direction_spec |
|---|---|---|
| novel-rewrite | 原作内核 / 旧设定吸收 | 改动spec / 新设定确认 |
| novel-continue | 末章状态 / 伏笔 / 作者口吻 | 续写方向候选与用户选定 |
| novel-expand | 事件骨架 / 人物 / 世界观 | 扩写比例 / 章节映射 |
| novel-condense | 主线骨架 / 锚点 / 反转点 | 压缩比 / 目标用途 / 合章策略 |
| novel-spinoff | 原作时间线 / 锚点表 / 配角线索 | 配角 POV / 锚点对齐策略 |

## 通用后半段机制

1. **书名（title）**：委托 `novel-title`（按派生类型）。
2. **章纲（outline）**：先按 `split.md` 反推总章数 / 字数分档（按 target_platform），再用 `outline.md` + 本 skill 的工艺 ref 编织。
3. **Demo gate（demo）**：前 2-3 章逐章独立写、逐章审。审完必须写 `审稿/demo_gate.json`（schema 见 `demo-gate.md`）；`status != passed` 不进 draft。gate 产出的 `style_anchor` / `reader_promises` / `setting_constraints` 是后续子任务的必喂上下文。
4. **批量写章（draft）**：先读 `draft-pipeline.md`，跑 `scripts/draft_packets.py "<作品根>" --next|--range A-B` 生成逐章任务包；每章写完填 `审稿/state_delta_第NN章.json`，经 `reconcile_ledger.py` audit→merge 同步进 `审稿/state_ledger.json`（未经验证不合并）。
5. **回扫（review）**：用 `novel-review` 按本 skill 的重点维度回扫（各 skill 自列重点）。
6. **导出（export）**：发布前先 `scripts/ai_usage.py` 写 AI 使用披露，再 `scripts/export.py "<作品根>" --formats ...`（家族通用导出器，默认执行 QA gate）。

> 本文件只描述**通用骨架**；各 skill 的 source_model 抽取细则、Demo 敏感点、review 重点维度仍写在自己的 SKILL.md / references。
