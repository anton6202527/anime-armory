---
name: comic-supervisor
description: 用持久化 producer 一键总控 Comic，从当前业务前沿连续执行安全动作、派发语义/视觉专家、断点续跑，直到最终成品或真正硬边界。
---

# Comic Supervisor

## Triggers

- “一键生成漫画最终成品”“不要频繁停下来确认”“继续跑到完成”
- 需要 crash-safe 循环、专家适配器、动作日志、熔断与最终完成定义

## 核心合同

1. `comic-batch --next-json` 每次只声明一个当前业务前沿动作。
2. `producer.py` 持有 durable loop；确定性、可逆动作直接执行，语义创作和实际像素审阅通过项目注册的专家适配器执行。
3. 只在这些真实边界停：权利/合规缺口、阶段预算包创建/扩大/过期、不可逆发布或覆盖、具名最终验收、适配器缺失、熔断。
4. `provider succeeded`、队列结束、`_进度.md` 和 dashboard 都不是完成。只认 `生产数据/completion_verdict_第N话.json` 的 `accepted`。
5. 视觉代理必须实际读取 `visual_review_packet` 的当前 contact sheet，且项目已有 `视觉审阅策略：用户授权制作代理实际查看当前像素` 或当前 hash-bound envelope；收据必须 `human_signoff=false`，不能冒充真人。
6. 每话同一时间只允许一个 producer 持有 OS 级 lease。planner 为动作提供排除 `_进度.md`/本阶段输出的 `work_unit_input_digest`；不可变 action card 以动作意图 + 该上游输入修订为稳定逻辑幂等键，claim 另记可变 pre/post frontier。每条命令都先写 fsync intent、返回后写 commit，启动时扫描全部未决 claim：副作用后崩溃不重放，后来真实上游修订仍可形成新 work unit 合法返工。
7. 缺 active release contract 时，只从 `_设置.md` 中显式存在且合法的 `交付介质/交付用途/目标平台` 原子 bootstrap，并绑定 settings SHA；缺值或非法值不会静默退成 internal。

## 一键运行

```bash
python3 skills/comic/comic-supervisor/scripts/producer.py "创作区/画漫画/<项目>" --chapter 第1话
```

计划预览：

```bash
python3 skills/comic/comic-supervisor/scripts/producer.py "创作区/画漫画/<项目>" --chapter 第1话 --plan-only --json
```

## 专家适配器

项目可在 `生产数据/comic_specialist_execution_adapters.json` 注册 `story_editor`、`comic_writer`、`visual_qc_agent`、`quality_editor`。命令必须是 argv 数组或无 shell 运算符的字符串；`{request}` 会替换为 SHA/路径齐全的任务包。适配器完成后必须自行运行任务包里的验证命令并写回本线合同；producer 不伪造创作内容、视觉结论或签收。

## 输出

- `生产数据/producer/<chapter>/producer_run.json`
- `生产数据/producer/<chapter>/events.jsonl`
- `生产数据/producer/<chapter>/commands.jsonl`
- `生产数据/producer/<chapter>/lease.json`
- `生产数据/producer/<chapter>/action_cards/<sha256>.json`
- `生产数据/producer/<chapter>/claims/<sha256>.json`
- `生产数据/producer/<chapter>/requests/*.json`
- 最终以 `生产数据/completion_verdict_<chapter>.json` 为唯一完成裁决

## 不做

- 不自行签发预算包，不扩大模型/渠道/次数/费用范围。
- 不自动发布、覆盖已发布成品或替用户作最终验收。
- 不用 shell 拼接执行项目适配器，不把未知后端静默换成 Codex。
- 不自动重放崩溃窗口中 execution outcome 不明的 action claim；先按后置条件/供应商 receipt 调和。
