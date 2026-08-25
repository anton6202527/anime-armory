---
name: comic-batch
description: 画漫画流程推进与批跑控制。Use when advancing a comic chapter from its current _进度.md frontier, batch-running panel image generation, rerolling selected panels, or chaining image → compose → review for projects under 创作区/画漫画. It recognizes comic-name and comic-finishing frontiers, orchestrates existing comic-* stage scripts, and keeps paid/high-cost generation explicit. Triggers 漫画批跑, 漫画自动推进, 抽到满意为止, 批量出图, 重抽漫画格, comic-batch.
---

# comic-batch — 漫画流程推进与批跑

`comic-batch` 是漫画线的流程层：读取 `_进度.md`，自动运行可复算阶段，把缩略分镜/name board 和 layout 当作显式编辑签收点。首次推进到这两步先生成 `draft`；`审阅策略=逐阶段用户确认` 时等待人工，项目 `_设置.md` 显式采用 `用户授权制作代理`（或存在当前有效的 `生产数据/authorizations/editorial_review.json`）时，batch 会在同一次进程内完成 `draft → review → approved → check` 并继续收尾、出图包、出图与合成，不再只打印命令后退出。代理签收写 `delegate:` 身份、授权来源、证据和当前 SHA，不能伪装成人审。`--next-json` 提供单动作机器协议，供 `comic-supervisor` 持有 durable loop；创作阶段由 supervisor 派给项目注册的 `story_editor/comic_writer` adapter，审查阶段也不跳过证据化验收。

`传统原稿流程=关闭` 只跳过原稿收尾，不再跳过缩略分镜/name board；已签收 name board 是所有 layout adapter 的强制编辑合同。出图前编排器先运行 layout `--check`，传统收尾开启时再运行 finishing `--check`，然后才进入 `image_preflight`。因此即使手动指定 `--stage image`，也不能绕过 draft、失效审批或 stale 上游。

## 适用场景

- 用户已经确认付费/高成本出图，要求继续批量生成面板图。
- 预算充足，需要对失败或不满意面板多次重抽。
- 出图齐全后，需要继续衔接嵌字合成或审查。
- 一话中途被打断，需要从 `_进度.md` 和 job 包恢复；若停在 name/layout draft，授权有效时脚本在当前 run 内提交、签收、复核并继续，显式逐阶段人审才清洁停在编辑签收点。

## 输入

- `创作区/画漫画/<作品>/_进度.md`。
- `出图/第N话/prompt/panel_jobs.json`。
- `_设置.md` 里的 `生图模型`、`生图渠道`、`基础视觉风格`。
- delegated name/layout 审阅还要求项目 `_设置.md` **显式**写 `审阅策略: 用户授权制作代理`；不能用代码默认值代替授权。正式授权 envelope 的固定路径为 `生产数据/authorizations/editorial_review.json`，须使用 `comic-editorial-authorization/v1`、授权主体原话、阶段 scope、delegate、带时区时间与匹配的 `authorization_sha256`。
- 付费出图还要求真实人类预先签发 `生产数据/spend_envelopes/image_第N话.json`。它与 editorial authorization 是两套不同合同，不能互相冒充。

## 怎么跑

从当前进度自动判断阶段；当前前沿为 `出图` 时，会读取本项目 `_设置.md`，按已选 `生图渠道` 调用 `comic-image` 的 Codex 或 Dreamina 官方 CLI runner：

```bash
python3 skills/comic/comic-batch/scripts/run.py "创作区/画漫画/作品名" --chapter 第1话 --image-max-attempts 3
python3 skills/comic/comic-batch/scripts/run.py "创作区/画漫画/作品名" --chapter 第1话 --next-json
```

只跑部分格：

```bash
python3 skills/comic/comic-batch/scripts/run.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003,P007 --image-max-attempts 3
```

人工看图后重抽指定格；旧图会归档到 `出图/第N话/candidates/<panel_id>/`：

```bash
python3 skills/comic/comic-batch/scripts/run.py "创作区/画漫画/作品名" --chapter 第1话 --targets P003,P007 --force --image-max-attempts 3
```

## 费用与覆盖

付费/高成本动作必须有可追溯的阶段预算 envelope。`comic-batch` 和两个 image runner **只能校验/消费，绝不自行签发授权**。创建授权必须由真实人类提供姓名、证据定位与原话；`agent/auto/delegate/system/runner` 等身份会被拒绝。先生成当前 `panel_jobs.json`，再由人执行：

```bash
python3 skills/comic/_lib/spend_envelope.py issue "创作区/画漫画/作品名" --chapter 第1话 \
  --panels all --expires-at 2026-12-31T23:59:59+08:00 \
  --max-calls 24 --max-attempts 3 --currency CNY --max-total 240 --max-cost-per-call 10 \
  --approver "制片人姓名" --approval-reference "chat://message/123" \
  --source-quote "批准本话以上面板在 240 CNY 内连续出图，最多 24 次、3 个重试轮次。"
```

envelope 精确绑定项目路径摘要、`stage=image`、稳定的逐格执行输入 hash、模型、渠道、面板 scope、是否允许 `--force`、过期时间、最大 call、唯一 retry-round 数、币种、单次与总成本上限。已授权集合的子集和现有余量可沉默续跑；扩面板、改输入/模型/渠道、从普通生成扩大到 `--force`、过期或额度不足时，runner 以 `comic_spend_authorization_stop` JSON 和退出码 5 清洁停止。

消费账本固定为 `生产数据/spend_ledger.json`：真实付费 submit 前用文件锁+原子替换占用一次，Dreamina 的 `query_result`/下载轮询不重复消费；实际成本原子结算并释放差额。供应商未返回精确成本时按已批准单次上限保守结算，费用未知不提交。实际成本越界或结算未知会把账本持久标为 blocked；已 reserve 后进程崩溃的 consumption ID 视为供应商状态不明，禁止用同 ID 再提交，避免双花。首次授权后只有授权缺失/失效/扩大才再问人，逐格像素签收仍是独立硬停。

## 完成判定

- `name_board.workflow_status` 或 `layout.workflow_status` 为 `draft/review` 时，项目授权有效则批跑在同一次调用内执行 submit/approve/check，只有 schema、当前 subject SHA、上游 SHA 和授权收据均通过才回写 `✅` 并继续。该收据明确标记 `review_kind=delegated_policy_auto_review`，只代表机器结构复核，不冒充视觉/语义人审；视觉与成品质量仍由后续真实 review/最终验收负责。缺 key 不会继承 permissive 默认，授权缺失/过期/哈希不匹配会 fail closed。显式逐阶段人审项目才等待用户。
- `layout --check` 会复核 name/layout schema、validator、approval subject SHA 与当前 panel script/name/settings；失败时连手动 image 模式也停止。
- `finishing --check` 会复核 plan 覆盖和 panel script/name/layout/settings SHA；缺输入、空计划和 stale 都停止。
- `comic-batch` 调用出图 runner 前先跑 `skills/comic/comic-review/scripts/gate.py --stage image_preflight`；被 gate block 时不启动付费/批量出图。
- `comic-image` runner 会在所有 job `ready` 且 PNG 有效时把 `_进度.md` 的 `出图` 标为 `✅`；`post_qc=block` 的格子标 `qc_block`，不算 ready。
- runner 每张落盘后先做目标格 post-QC。指定 `--targets` / `--limit` 的验样批次若尚未补齐整话，只报告该批通过并延后整话 gate；全部 panel 都是 `ready` 且文件存在后，`comic-batch` 才跑 `skills/comic/comic-review/scripts/gate.py --stage image` 刷新整话风格与角色一致性报告。禁止用“未生成的其它格”把已通过的小批验样误报成失败。
- `comic-batch` 只在阶段脚本成功时继续，不吞掉失败。review gate pass 后只把派生进度记为 `✅（machine_ready）`；最终完成只由 `completion_verdict=accepted` 定义。
- 出图完成后下一步通常是 `comic-compose`；正式发布前仍要跑 `comic-review`。

## 不做什么

- 不绕过 `comic-image` 的 job 包和状态登记。
- 不自动购买字体、启用未知付费模型或覆盖已经发布的导出图。
- 不把候选图直接混入正式交付；正式图只在 `panels/`，候选和旧图进 `candidates/`。
