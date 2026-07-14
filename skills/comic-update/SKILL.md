---
name: comic-update
description: 画漫画(comic) skill 更新影响扫描与最小重制计划器。Use when the user says comic-update, 漫画更新, skill更新, 更新影响, 返工, 重跑, 重制, 重审 for a comic project, asks whether changed comic skills affect an existing project, or wants a safe plan before rerunning script/name/layout/finishing/image/compose/review. It compares comic skill snapshots and the same SHA-bound development, editorial, identity, reference/job, and gate contracts used by comic-progress, then writes a minimum replay plan without directly overwriting creative assets or `_进度.md`.
---

# comic-update — skill 更新影响扫描 + 最小重制计划

`comic-update` 是 comic 线的更新影响入口。它做确定性分析：记录/对比本线 skill 文件内容快照，检查旧项目是否缺新版流程产物，并生成最小重制计划。它不直接改脚本、不出图、不合成、不回写 `_进度.md`。

## 输入 / 输出 / 边界

- **输入**：`创作区/画漫画/<项目>/_进度.md`（只是进度声明）、本线 `skills/comic*` 文件、项目内上次 `record` 的内容快照、已有分话产物及它们的当前 SHA/approval/gate receipts。
- **输出**：
  - `record` 或 `check` 自动 bootstrap 写 `生产数据/comic_skill_update_snapshot.json`
  - `check --write-plan` 写 `生产数据/comic_skill_update_plan.json`
  - `check --write-plan` 写 `生产数据/comic_skill_update_plan.md`
- **读写边界**：只写快照和计划；不覆盖 `panel_script.json`、`layout.json`、图片、导出物或 `_进度.md`。

## 快速使用

```bash
python3 skills/comic-update/scripts/update_plan.py check "创作区/画漫画/作品名" --write-plan
python3 skills/comic-update/scripts/update_plan.py record "创作区/画漫画/作品名"
python3 skills/comic-update/scripts/update_plan.py check "创作区/画漫画/作品名" --json
```

- `record`：阶段产物验收通过后，记录当前 comic skill 内容基线。
- `check`：对比基线和当前 skill 文件；无基线时默认建立临时基线，同时检查旧流程结构缺口。
- `--no-bootstrap`：无基线时不写盘，只提示需要 `record`。
- `--write-plan`：写计划 JSON/Markdown。
- `--json`：把计划 JSON 打到 stdout。

## 重制原则

- 不默认整部漫画无脑重做：回放上限只到每话已经到达的阶段。
- 旧流程缺口也算更新影响：包括开发包 strict/signoff、chapter contract/source coverage、已签收的 name/layout、validated finishing、identity registry v2/model-pack report+signoff、reference plan/`panel_jobs`，以及最晚已完成阶段当前有效的 gate receipt。下游 receipt 是上游 gate 的传递证明；仍会直接核验所有 artifacts/contracts，但不会因合法 stale 的早期 receipt 迫使整链重跑。即使没有历史快照，也要从最早结构缺口给出回放计划。
- 单纯缺失/过期的 gate receipt 不重建上游内容：只重跑对应 `comic-review gate --stage ...`。gate 含 block 时才按 `return_to_stage` 返修。
- name/layout 不把 draft 当完成：执行计划明确列出 `生成 draft → --submit-review → --approve --reviewed-by ... → stage gate`；签收人必须真实提供。
- reference plan/成图/导出物变化后，用 comic 共享的 stage input fingerprint 判定 image/compose/review receipt 过期，不靠文件时间或 `_进度.md`。
- 付费出图前先停：计划覆盖 `image` 时，先确认模型、渠道、预算、保留旧图和目标格范围，再交给 `comic-image` 或 `comic-batch`。
- 控制面变化不触发重制：`comic-progress`、`comic-settings`、`comic-update` 本身变化只提示刷新扫描/基线。

## 收尾

跑完 `check` 后，把计划摘要告诉用户：是否建议重制、受影响话别、从哪个阶段回放到哪个阶段、下一步进哪个 `comic-*` skill。重制验收通过后再跑：

```bash
python3 skills/comic-update/scripts/update_plan.py record "创作区/画漫画/作品名"
```
