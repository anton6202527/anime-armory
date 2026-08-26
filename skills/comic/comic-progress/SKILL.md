---
name: comic-progress
description: 画漫画进度仪表盘与下一步建议。Use when the user asks current status, next step, checklist, or progress for comic projects under 创作区/画漫画. It treats _进度.md as a claim, then read-only verifies development/chapter/source contracts, editorial approvals, identity model-pack signoffs, reference plans, panel jobs, and current stage-gate receipts before routing to the earliest truthful comic skill. Triggers 漫画进度, 画漫画进度, 下一步, 到哪了, 查进度, 缩略分镜进度, 原稿收尾进度, 一致性下一步, comic-progress.
---

# comic-progress — 画漫画进度扫描

只读扫描 `创作区/画漫画/` 下的漫画项目，汇总每话可被当前证据证明的真实前沿。`_进度.md` 只是状态声明；合同、SHA 签收或 gate receipt 缺失/过期时，输出会回到最早阻断，不会照表格勾选误报“已完成”。审查已完成但仍有未处置或因像素变化而失效的 review warning 时，会另列“风险处置”披露：不抹掉内部制作完成度，但明确公开/商业发布还不能据此静默放行。它不写文件、不出图、不导出。

## 怎么跑

扫描全部：

```bash
python3 skills/comic/comic-progress/scripts/scan.py
```

扫描指定项目：

```bash
python3 skills/comic/comic-progress/scripts/scan.py "创作区/画漫画/作品名"
```

JSON 输出：

```bash
python3 skills/comic/comic-progress/scripts/scan.py "创作区/画漫画/作品名" --json
```

## 输出解读

阶段路由：

| `_进度.md` 列 | 下一步 skill |
|---|---|
| 源本/企划 | `comic-script` |
| 漫画脚本 | `comic-script` |
| 缩略分镜 | `comic-name` |
| 页面排版 | `comic-layout` |
| 原稿收尾 | `comic-finishing` |
| 传统收尾（旧列名） | `comic-finishing` |
| 出图包 | `comic-image` |
| 出图 | `comic-image` |
| 出图已完成但引用缺失/旧图未用真实参考 | `comic-identity` |
| `定妆级别=长线专门定妆` 且常驻人物多视图缺失 | `comic-identity` |
| 出图已完成但缺少风格一致性报告 | `comic-review` |
| 风格一致性报告存在 block | `comic-image` |
| 嵌字合成 | `comic-compose` |
| 审查 | `comic-review` |

证据覆盖（按最早阻断路由）：

| 缺口 | 返回 skill |
|---|---|
| 开发包 strict/signoff、chapter contract、source spans/coverage、source semantics 或 panel script 绑定缺失/过期 | `comic-script` |
| `name_board` 处于 draft/review、未由人工或授权制作代理签收、内容 SHA 或上游 SHA 过期 | `comic-name` |
| `layout` 未由人工或授权制作代理签收，或内容/上游 SHA 过期 | `comic-layout` |
| `finishing_plan` 未 validated/pass 或上游过期 | `comic-finishing` |
| identity registry 未 v2、model-pack report 不 ready、纳管资产的多视图签收缺失/过期 | `comic-identity` |
| reference plan / `panel_jobs` 缺失、未完整覆盖或未消费当前 SHA | `comic-image` |
| 最晚已完成阶段的 gate receipt 缺失/过期、report SHA 不匹配或未 `execution_authorized` | `comic-review` |
| gate 存在 block | 按 finding 的 `return_to_stage` 返回对应 `comic-*` skill |

`[风险处置]` 使用 `comic-review` 的 SHA 绑定处置账核对 warning。只有具名审阅人对当前 finding 与当前像素留下 `false_positive` 或 `risk_accepted` 及理由，且追加事件的 chapter/sequence/hash-chain 完整，才算当前有效；旧处置随 finding/像素变化自动失效，账本损坏也会单列披露。该披露与主流程前沿分开，避免把“内部做完”和“可以公开发布”混为一谈。

`传统原稿流程=关闭` 只跳过 `原稿收尾/finishing`；缩略分镜/name 是必需的编辑阅读与页流合同，不会被该设置绕过。怪物资产按档位默认纳入多视图 report/signoff（`core_full`/`recurring_standard` 生物默认纳管，registry `model_pack_required` 可显式 true/false 覆盖；2026-07-17 起与 comic-identity model_pack 同口径）；`type=character` 仍全部纳入。

下游 gate 会重跑全部上游确定性检查，因此扫描器把“最晚已完成阶段的当前 receipt”作为传递证明，同时仍直接核验全部当前 artifacts/contracts。早期 receipt 因 runner 刷新 jobs/report 而 stale 不会单独触发回退。

如果下一步是出图、覆盖导出或正式发布前审查，先检查项目是否已有当前有效的模型/渠道、费用、覆盖范围和权利授权；同范围授权沉默沿用，缺失或实质扩张时才提醒用户确认。

进度表全勾只表示制作阶段前沿走完，不再输出“最终完成”。扫描器不直接相信旧 `completion_verdict`：它会沿 `release_contract` 读取当前 digest 的不可变 bundle，重算 release digest，并复核 settings、全部产物及 receipt 当前 SHA；只有指纹仍 current 且唯一 verdict 为 `accepted` 才令 `front.complete=true`。缺失、stale、blocked 或 machine_ready 都路由 `comic-supervisor` 刷新 active release/最终裁决。`_进度.md`、provider 成功和 dashboard 不能成为第二完成状态。

## 不做什么

- 不回写 `_进度.md`。
- 不会为了“显示完成”而自动补签、刷新 gate 或修改任何产物。
- 不替用户创建不存在的付费或覆盖授权，也不把窄范围授权扩张到新模型、新渠道、新预算或已发布成品覆盖。
- 不扫描其它生产线目录。
