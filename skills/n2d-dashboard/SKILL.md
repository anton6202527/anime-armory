---
name: n2d-dashboard
description: "P0 横切 skill for novel2drama/n2d production metrics, ROI dashboard, generation cost accounting, QA gate event logging, redraw reason analysis, local monitoring, and threshold alerts. Use after n2d generation/review/gate runs, or when asked for 生产数据仪表盘, 实时监控, 成本预警, ROI, 每分钟成本, 一次通过率, 重抽率, 投放回收, dashboard, metrics, alerts."
---

# n2d-dashboard — P0 生产数据仪表盘

这是 n2d 工业化的 P0 横切层：**每集记录成本、耗时、生成次数、重抽原因、QA 阻断项、最终通过率和 ROI**。`_进度.md` 只回答“做没做”；本 skill 回答“每分钟成本多少、每集耗时多少、一次通过率/重抽率能否量产、投放回收能否覆盖生产成本”。

## 输入 / 输出 / 读写边界

- **输入**：各 stage 的 generation/redraw/manual/release 事件、gate findings、平台投放指标、告警阈值。
- **输出**：`生产数据/production_events.jsonl`、`dashboard.json/md/html`、`alerts.json/md`、`gate_findings_*_第N集.json`。
- **读写边界**：只记账、汇总、告警和 gate 入账；不修改 `_进度.md`、不执行实际生成、不解释评分维度。
- **契约关系**：事件枚举、重抽分类、gate stage 和 finding schema 与 `skills/common/n2d_contract.py` 对齐；生产 gate 推荐从本 skill 入口调用。

## 核心原则

- **事件日志是机器真值**：所有生产数据先追加到 `制漫剧/<剧名>/生产数据/production_events.jsonl`，再由脚本汇总成 `dashboard.json` + `dashboard.md`。不要把成本/重抽原因塞进 `_进度.md`。
- **事件读写带本地锁**：`record` / `gate` / `build` / `watch` 对 `production_events.jsonl` 和 dashboard 输出统一走 `production_events.lock`；JSON/MD/HTML 用临时文件原子替换，避免多 worker 同时记账时读半截或互相覆盖。
- **每次生成都记账**：n2d-image / n2d-video / n2d-voice / n2d-compose 的每次 AI 调用或实质性处理，都记录 `stage`、`asset`、`duration_sec`、`cost`、`status`。重抽必须写 `redraw_reason`。
- **重抽原因分维度（契约枚举）**：`redraw_reason` 仍写自由文本，但记账时同步归入契约 `REDRAW_REASON_CATEGORIES` 九类维度（脸漂/服装/场景/画风/道具/参考图裁切/prompt 冲突/时序/其他）——显式传 `--redraw-category` 则尊重，否则按关键词自动归类；存量自由文本事件在 rebuild 时读时归类，不改写历史 jsonl。`dashboard.md` 出「重抽原因分维度」表并单列**一致性小计**（face/outfit/scene/style），让"一致性是不是最大成本杀手"一眼可见、可驱动投入决策。
- **每次审查都入账**：生产前 gate、成片后 review 的 QA finding 都写入仪表盘。`block` 是 QA 阻断，`warn` 是风险提示；两者分开统计。
- **最终通过率定义固定**：`final_pass_rate = generation_passes / (generation_passes + generation_fails)`。没有记录 pass/fail 时显示 `—`，不得凭感觉补。
- **ROI 五件套固定**：`cost_per_finished_min`（生产成本 ÷ 成片分钟）、`duration_sec`（每集生产耗时）、`one_pass_rate`（一次通过数 ÷ 生成尝试数）、`redraw_rate`（重抽数 ÷ 生成尝试数）、`recoup_ratio`（投放净回收 ÷ 同币种生产成本）。没有同币种成本/收入时显示 `—`，不跨币种硬算。
- **投放回收从平台数据或 release 事件来**：dashboard 会自动读取 `生产数据/platform_metrics.csv|jsonl|json` 的 `revenue/distribution_spend/plays` 等字段；也可手动 `record --event release|revenue`。投放数据不再只进 `n2d-feedback`，必须进入 ROI 仪表盘。
- **默认覆盖同一 gate 结果**：同一集同一 stage 重跑 `dashboard.py gate` 时，默认替换旧 gate 事件，避免 QA 阻断重复累计；要保留历史用 `--append`。
- **工业级判断看 ROI 趋势**：单集 dashboard 是局部事实；批量后看 `每分钟成本`、`每集耗时`、`一次通过率`、`重抽率`、`投放净回收/生产成本`、`QA阻断Top`，再决定优先优化哪个 stage。
- **行业基准只作参照线，不作闸门**：`dashboard.md` 的「行业基准对照」段把一次通过率/重抽率/每分钟成本/跨集一致性并排到行业宣传基准（默认读 `references/industry_benchmark.json`，采集 2026-06），给一条「你 X% vs 行业 Y%」的达标/差距参照。**这是只读参照、不参与告警/阻断**（厂商口径不一、会过期）。覆盖：`_设置.md` 写 `基准一次通过率 / 基准重抽率`，或 `生产数据/industry_benchmark.json`；基准本身以一次 `n2d-review` 流程自审复核为准，刷新基准只改 JSON，不改 Python。
- **外部 API 成本只作校准线**：按 2026-06 官方公开资料，Veo 3.1 已按生成秒计价（Lite/Fast/Standard/4K 档位不同），Kling/Runway/Luma 也都以 credits/秒/任务形式收费。dashboard 不硬编码外部价格；每个项目要记录真实 `provider/cost/currency/unit`，再由 `cost_per_finished_min` 和重抽率判断“这条路线是否值得放量”。
- **工业级门槛不是单项指标**：只有同时满足“成本可控、通过率稳定、QA 阻断可收敛、投放回收能覆盖生产成本、跨集一致性没有持续恶化”，才算该项目进入可放量状态。任一项红灯，先回 router/identity/template/feedback 修产线，不盲目加集数。

## 文件结构

```text
制漫剧/<剧名>/生产数据/
  production_events.jsonl   # 事件日志，append-only 为主
  production_events.lock    # 本地文件锁，保护事件读写 + dashboard 重建
  platform_metrics.csv      # 可选：平台播放/收入/投放成本，dashboard 自动合并 ROI
  dashboard.json            # 机器读汇总
  dashboard.md              # 人读仪表盘
```

事件 schema 见 `references/schema.md`。

## 标准调用

### 1. 生成后记录

```bash
python3 skills/n2d-dashboard/scripts/dashboard.py record <作品根> \
  --episode 第1集 \
  --stage image \
  --event generation \
  --asset Clip_01.png \
  --status pass \
  --duration-sec 38 \
  --cost 0.06 \
  --currency USD \
  --unit USD \
  --provider codex
```

> **从 Python 记账走 `common/n2d_telemetry.record_event`**（封装本 CLI，是脚本侧的规范写入口）：它强校验 `event ∈ VALID_EVENTS`（与本命令 `--event` 白名单一致），批量记账传 `build=False` 走 `--no-build` 避免每条都重建抢锁。直接 shell 出本命令也可（image/video/compose SKILL 的「记账铁律」即如此）；`n2d-batch/runner` 则直接 import dashboard 模块批量追加。三条路径都写同一份 `production_events.jsonl`。

重抽必须写原因：

```bash
python3 skills/n2d-dashboard/scripts/dashboard.py record <作品根> \
  --episode 第1集 \
  --stage video \
  --event redraw \
  --asset Clip_03.mp4 \
  --status fail \
  --redraw-reason "动作幅度过大导致脸漂移" \
  --duration-sec 92 \
  --cost 12 \
  --unit credits \
  --provider seedance
```

### 2. gate 后记录 QA

```bash
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage image_preflight   # 正式生图前
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage image             # 生图后落档回验
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage video_preflight   # 正式出视频前
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage video             # 出视频后落档回验
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage compose
python3 skills/n2d-dashboard/scripts/dashboard.py gate <作品根> 第1集 --stage review
```

该命令会调用 `n2d-review/scripts/gate.py --json`，把 `severity/dimension/loc/message/return_to_stage/rerun_scope/affected_artifacts` 写进生产数据，并刷新 dashboard；为兼容旧消费脚本，外发 JSON 同时保留 `sev/dim/msg` alias。同时外发 `生产数据/gate_findings_<stage>_第N集.json`（kind=`n2d_consistency_findings`），可直接：

```bash
python3 skills/n2d-batch/scripts/queue.py plan <作品根> \
  --from-consistency-findings <作品根>/生产数据/gate_findings_video_第1集.json \
  --max-concurrency 1 \
  --max-retries 2
```

### 3. 手动重建

```bash
python3 skills/n2d-dashboard/scripts/dashboard.py build <作品根>
python3 skills/n2d-dashboard/scripts/dashboard.py build <作品根> --markdown
```

### 3.5 成本预检（开跑前估这集要花多少）

dashboard 默认**事后**记账；`forecast` 用历史 `cost_per_finished_min`（已有 ROI 指标）× 本集 `storyboard.json` 计划时长，给一个**开跑前**的成本预测，并把已有的 `redraw_categories` 滚成「过去钱漏在哪」的 Top 漏点（先治这些最省钱）。可选 `--budget` 判超支 + 还能撑几集：

```bash
python3 skills/n2d-dashboard/scripts/dashboard.py forecast <作品根> 第2集 --budget 100 --unit CNY
python3 skills/n2d-dashboard/scripts/dashboard.py forecast <作品根> 第2集 --json
```

无历史成本 / 缺本集计划时长时**不臆造**，只给 note + 已有的重抽漏点（先 `record` 几集真实成本，或先跑分镜设计出 `storyboard.json`）。`--unit` 须与 `record` 的 `cost.unit` 一致。

### 4. 投放回收入账

优先把平台导出的留存/播放/收入表放到 `生产数据/platform_metrics.csv|jsonl|json`，字段见 `n2d-feedback/references/schema.md`。dashboard 会自动合并：

```csv
episode,platform,plays,revenue,distribution_spend,currency,duration_sec
第1集,douyin,12000,86.5,30,CNY,92
```

没有平台表时，可手动记录 release/revenue 事件：

```bash
python3 skills/n2d-dashboard/scripts/dashboard.py record <作品根> \
  --episode 第1集 --stage release --event release \
  --plays 12000 --revenue 86.5 --spend 30 --revenue-currency CNY --runtime-sec 92
```

## 实时监控 + 阈值告警（纯本地 · 跨 AI 通用）

检测/计算**全本地、纯标准库**，对已构建的 dashboard 汇总做阈值判定。**循环触发不依赖任何 harness**：`record`/`gate` 每次写事件即重建并评估（推送路径，零额外设施）；要常亮看板时用脚本内置 `watch` 轮询。Claude Code hook / `cron` / `loop` 技能只是**可选外壳**，别的 AI agent 或纯命令行同样能用。

**① 阈值配置**（`None`=关闭该项；优先级 默认 ← `_设置.md` ← `生产数据/alert_thresholds.json` ← 环境变量）。默认只对 **QA 阻断**开箱即告（gate 阻断本就是要停线的异常）；成本/通过率/回收比默认关，避免生产早期误报：

```json
// 生产数据/alert_thresholds.json
{ "budget_cap": 500.0, "budget_warn_ratio": 0.8, "final_pass_rate_floor": 0.8,
  "redraw_rate_ceiling": 0.4, "qa_blockers_ceiling": 0, "cost_per_min_ceiling": 30.0, "recoup_floor": 1.0 }
```

也可在 `<作品根>/_设置.md` 写 `- 告警通过率下限: 80%` / `- 告警预算上限: 500` 等（键：`告警预算上限/告警预算预警比例/告警通过率下限/告警重抽率上限/告警QA阻断上限/告警每分钟成本上限/告警回收比下限`）。

**② 告警送达三层**（后两层可选 opt-in）：
- **默认**：写 `生产数据/alerts.json` + `alerts.md`（当前状态快照，幂等覆盖非追加）+ stderr 打印；`build --fail-on-critical` 有 critical 时退出码 3，供 batch/cron/CI 停线。
- **本机弹窗**（`--notify`）：macOS `osascript` / Linux `notify-send` 自动探测，best-effort，失败静默。
- **外发 webhook**（`--webhook URL` 或环境变量 `N2D_ALERT_WEBHOOK`）：stdlib POST JSON，飞书自定义机器人 / Slack / Discord 通吃。

**③ 实时监控**：

```bash
# 推送：记一条事件即重建+评估+（可选）告警（任何 agent/人调 record/gate 都自动触发）
python3 skills/n2d-dashboard/scripts/dashboard.py record <作品根> ... --notify
# 轮询常亮看板：events 变化即重建，本机起 http.server 看自动刷新 HTML
python3 skills/n2d-dashboard/scripts/dashboard.py watch <作品根> --interval 15 --serve 8787 --notify
# 单次（适合 cron / CI）：cron 行 = */5 * * * * python3 .../dashboard.py watch <作品根> --once --webhook $URL
python3 skills/n2d-dashboard/scripts/dashboard.py build <作品根> --html --fail-on-critical
```

`watch --serve` 会写并伺服 `生产数据/dashboard.html`（自动刷新、含告警块 + 逐集表），纯 stdlib `http.server`，只绑 `127.0.0.1`。

> **跨机器实时**：单机够用；多机分布式 worker 时，`production_events.jsonl` 需放共享/同步存储（与分布式队列同一前提），否则单机 watch 看不到别机事件。

## 各阶段硬要求

| 阶段 | 必记字段 |
|---|---|
| `voice` | 后端、总耗时、失败/占位句数、成本或本地耗时；若单句降级占位，记 `redraw_reason` 或 `meta` |
| `image` | 每张定妆/分镜 PNG 的尝试次数、通过/失败、重抽原因、成本、耗时 |
| `video` | 每个 Clip 的尝试次数、通过/失败、重跑原因、成本、耗时、是否含原生音轨可写 `meta=native_audio=yes/no` |
| `compose` | 合成耗时、输出文件、原生音轨策略、水印状态；失败则记 QA 或 manual 事件 |
| `review` | gate/review finding：`block/warn/info`、定位、修法回流 stage |

## 验收

一次 n2d 生成或审查完成后，必须能打开：

- `生产数据/production_events.jsonl`：有本次事件；
- `生产数据/dashboard.json`：机器可读汇总；
- `生产数据/dashboard.md`：人可读表，含成本、每分钟成本、每集耗时、一次通过率、重抽率、QA 阻断、投放净回收、回收/成本。

若某阶段没有成本 API，就至少记录 `duration_sec` 和 `provider`；成本字段可留空，但不能不记事件。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 只更新 `_进度.md`，不记生产数据 | `_进度.md` 不是生产指标，必须再跑 `n2d-dashboard record/gate` |
| 重抽只说“重抽了” | 必须写 `redraw_reason`，否则无法聚类优化 |
| 只看“能生成” | 不够。必须看 ROI 五件套：每分钟成本、每集耗时、一次通过率、重抽率、投放回收 |
| 平台收入只写在复盘文档 | 放进 `platform_metrics.*` 或 `record --event release`，否则 dashboard 无法算 recoup |
| gate 重跑多次导致阻断翻倍 | 默认用 `dashboard.py gate`，它会替换同集同 stage 旧 gate 事件；历史对比才加 `--append` |
| 把 warn 当 block | `block` 才是 QA 阻断；warn 单独统计 |
| 通过率凭主观写 | 只按有状态的生成事件计算，不手填 |
