# n2d 编排器 `run.py next` — 已实现接口契约

> 目的：把 I2 铁律（"确定性步骤和普通可逆选择自动链式跑完，只在高风险边界停"）从 SKILL.md 的 prose
> 变成**一段可执行的确定性胶水**。早期代理每推进一集一个阶段要手工串
> `source_check → update_plan → progress.py → model-router → dashboard gate → stage skill → progress set → dashboard record`，
> 本设计把这串散装命令收敛成 1 个入口 + 1 个结构化"下一步动作"对象。
>
> **本文是已落地的接口契约。** 实现在 `skills/n2d/run.py`，回归在 `skills/n2d/test_run.py`；阶段预算包的签发、只读探测、原子消费与结算分别由本线 `_lib/spend_envelope.py`、`n2d-batch/scripts/spend_probe.py` 和 batch runner 承担。更新时间：2026-08-22。

---

## 0. 一个必须先讲清的现实约束（决定了编排器的形态）

stage skill **不是**"一条命令跑完即出产物"的子进程。它们混着两类工作：

- **(a) 确定性脚本**：gate 机检、model-router 路由、prompt 脚手架、进度/manifest/dashboard 回写、身份矩阵刷新……
- **(b) 代理创作**：读 prompt 包 → 调自身 LLM 生成剧本/分镜 JSON/出图 prompt 文案 → 注入项目；以及真正花钱的出图/出视频/合成。

所以编排器**不能**把 `n2d-image` 当 `subprocess` 一把梭跑完。它能做的是：

> **把确定性前置自动跑完，对普通、可逆选择落 producer-owned 推荐值，再交回结构化「下一步动作卡」给 supervisor 继续派发。付费阶段若已有与当前项目、阶段、输入 SHA、scope、模型、渠道、额度和期限完全匹配的阶段预算包，则直接交 batch runner 原子消费并继续；只有预算包缺失/失效/扩大、合规授权、公开发布、破坏性操作和最终人工验收必须停。**

创作工位交给 supervisor specialist，付费 runner 只能消费已有授权，不能自行签发或扩大预算。这样既接近一键成片，又不把未授权支出或人工验收伪装成自动化。

---

## 1. 命令面

```bash
python3 skills/n2d/run.py enter <作品根> [第N集] [--json] [--auto]
python3 skills/n2d/run.py next  <作品根> [第N集] [--json] [--auto]
```

- `enter` → 进入作品时先跑一次入口检查（`source_check` + `update_plan check --write-plan`），再返回同一张 `NextAction`；适合 agent 接手项目第一步。
- `next` → 只做逐步推进和该阶段确定性前置；适合已在同一会话内连续推进时反复调用。
- 无集号 → 用 `summarize()` 取**最小未完成集**为前沿。
- 带集号 → 只推进该集。
- `--json` → 输出机器可读的 `NextAction`（代理消费）；默认输出人话（用户可读）。
- `--auto` → **连续推进**：每跑完一个确定性前置就看下一步，能自动就继续，**直到第一个真实 stop-point**；不加 `--auto` 只解析一次前沿并跑该阶段前置。
- 确定性前置可自动回写；普通选择默认写推荐值；授权范围内的付费任务转交唯一消费边界执行。编排器与 supervisor **绝不**签发/扩大预算、绕过合规、公开发布或代替最终人工验收。

> 不引入新子命令做回写——回写仍走既有 `progress.py set` / `dashboard record`，编排器内部调它们。

---

## 2. 返回契约 `NextAction`（`--json` 形态）

```jsonc
{
  "frontier": { "ep": "第3集", "stage_key": "image", "label": "出图", "owner": "n2d-image" },
  "prework": [                       // 本轮自动跑掉的确定性前置，按序
    { "step": "source_check", "status": "clean" },
    { "step": "update_plan",  "status": "no_change" },
    { "step": "identity_matrix", "status": "refreshed" },
    { "step": "gate", "stage": "image_preflight", "status": "pass" }
  ],
  "stop_reason": "needs_stage_execution",  // 已有有效阶段预算包；见 §3 枚举
  "action_card": {
    "headline": "第3集 出图阶段已有有效预算包，可继续执行",
    "to_user": "supervisor 可派发 batch runner；探针不消费预算，runner 在真实提交前原子消费。",
    "exact_command": "python3 skills/n2d/n2d-batch/scripts/runner.py <作品根> --limit 1 --stop-on-fail",
    "phase_spend_envelope": { "status": "authorized", "envelope_id": "…", "authorization_digest": "…" },
    "writeback_after": "python3 skills/n2d/progress.py set <作品根> 第3集 出图 <a/b>"
  },
  "gate": {                          // 命中 gate 时透传 gate.py 结构化字段，不重新发明
    "stage": "image_preflight", "status": "pass",
    "return_to_stage": null, "affected_artifacts": [], "rerun_scope": null
  }
}
```

字段全部来自现有真值源，**编排器不新增并行表**：
- `frontier` ← `n2d_route.stage_of()` 的 `{ep,col,label,skill}` + `STAGE_GRAPH[key]`。
- `gate` ← `dashboard.py gate --stage … --json` 的 `return_to_stage/affected_artifacts/rerun_scope` 原样透传。
- `action_card.menu` ← 选择点经 `选择点与偏好.md` 适配层解析（路由到能力/设置，不 branch 菜单文字）。

---

## 3. stop-point 分类法（**全部派生自已有契约/选择点，零硬编码**）

| stop_reason | 触发条件（真值源） | 编排器动作 |
|---|---|---|
| `needs_agent_gen` | 前沿阶段 owner 的产出含"代理 LLM 创作"（script_stage1/2、image_prompt、video_prompt 文案） | 跑完脚手架，停，给"该生成什么 + prompt 包路径" |
| `needs_stage_execution` | 前置已齐，需对应 specialist/runner；付费阶段还必须已有当前绑定完全匹配且有余量的 v2 阶段预算包 | supervisor 自动派发；预算探针只读，只有 runner 在真实提交前原子消费 |
| `needs_payment_confirm` | 兼容保留的停因名：当前付费/不可逆动作没有可用阶段预算包，或包已过期、超额、合同/输入/模型/渠道/scope 不匹配；安全本地首次合成除外 | 一次性汇总需签发/扩大/重签的边界；不为包内每个调用重复确认 |
| `needs_choice` | 项目显式设 `普通选择策略=逐项询问`，且当前普通选择未解析 | 停，弹对应菜单；默认策略不产生此停因 |
| `needs_compliance` | `n2d-compliance --check` 在 image/video/compose 前报缺口 | 停，列缺口，绝不放行 |
| `needs_acceptance_signoff` | 技术检查已过，仍缺独立验收签收 | 停，等待签收，不让生成者自批 |
| `blocked_by_entry_check` | 源文本/skill/旧资产新鲜度入口检查失败 | 停，按 repair plan 最小回流 |
| `capability_evidence_required` | 后端能力证据过期、保守或仅人工声明 | 停，刷新官方证据/adapter smoke，或换可证实后端 |
| `prework_failed` | P-1 开发包、P-2 导演排戏包、源语言理解层、中段前情资产包、边界复核等确定性前置未确认或脚本失败 | 停，给补齐命令/路径，不进入创作或花钱 |
| `blocked_by_gate` | `dashboard gate` 退出码 1 | 停，透传 `return_to_stage/affected_artifacts/rerun_scope`，指向最小返工 |
| `blocked_by_image_qc` | video/compose/review 前置发现 `image_qc` 缺失、非 full、或 hard block | 停，回 `n2d-image` 修复/确认受影响 PNG；不再误报为后端环境缺失 |
| `blocked_by_review_acceptance` | 审片结论/人工验收未满足发布边界 | 停，按 finding 回流或补签收 |
| `env_missing` | `doctor.py` 报该阶段所需后端/精度档缺失 | 停（或路由占位+大声告警），不让代理跑到花钱工位才发现 |
| `auto_ran` | 纯确定性步骤（router/gate-pass/矩阵刷新/进度回写） | **不停**，`--auto` 下继续推进 |
| `done` | 路由无前沿，且 canonical release verdict + acceptance receipt 仍然新鲜；显式 clip-only 项目例外 | 报完成 |
| `unknown_stage` | 前沿阶段不在 action registry | fail-closed，升级维护者；禁止猜测路由 |

枚举唯一真值为 `skills/n2d/_lib/n2d_action_registry.py::STOP_REASONS`；本表只做人读解释。schema 与 supervisor 有穷举测试，新增值必须先改注册表再补消费者测试。

> 关键不变量：**普通选择缺失会先自动落推荐值；已授权且绑定一致的付费阶段继续派发。编排器只在前置证据不成立、阶段预算包缺失/失效/越界、合规/能力/env 缺口或人工验收时停。**
> 其余（找前沿、跑 gate、写路由表、刷身份矩阵、回写进度+dashboard）一律自动，对代理透明。

---

## 4. 执行循环（伪码）

> **边界**：`源新鲜度自检`（source_check）与 `skill 更新影响检查`（update_plan）是 **dispatcher 进作品时的一次性入口步骤**。它们进 `run.py enter`，**不**进 `run.py next` ——否则每步推进都会重跑、浪费。`run.py next` 只管"逐步推进 + 每步的确定性前置（doctor/router/gate/compliance/P-1 开发包/P-2 导演排戏包/首跑选择探测）"。

```
def next(root, ep=None, auto=False):
    while True:
        route = stage_of(root, row(ep or 最小未完成集), header)  # 现有真值
        if route.col is None: return DONE
        spec = STAGE_GRAPH[route.stage_key]

        # 4.1 跑该阶段的确定性前置（当前散在 SKILL.md §gate前置 / §读进度路由）
        if spec.key == "script_stage1": run(development_pack check --write-missing)
        if spec.key == "script_stage2": run(director_blocking_pack check --write-missing)
        if spec.owner == "n2d-video": run(model_router --write)   # 出视频前置
        if spec.gate_stage: g = run(dashboard gate --stage spec.gate_stage --json)
            if g.blocked: return STOP(blocked_by_gate, gate=g)

        # 4.2 选择点 / 合规 / env
        if ordinary_choice_autopilot_enabled(root): apply_recommended_choices(root)
        elif unresolved_choice(spec): return STOP(needs_choice, menu=…)
        if spec.gate_stage in PAID and compliance_gap(): return STOP(needs_compliance)
        if needs_agent_gen(spec):    return STOP(needs_agent_gen, prompt_pack=…)
        if is_paid(spec):
            auth = read_only_probe_current_phase_envelope(spec)
            if auth.status == "authorized": return DISPATCH(needs_stage_execution, auth=auth)
            return STOP(needs_payment_confirm, authorization_gap=auth.issue)

        # 4.3 纯确定性阶段：极少；若有，跑完→回写→继续
        run_deterministic(spec); progress_set(...); dashboard_record(...)
        if not auto: return STOP(auto_ran, advanced=spec.key)
        # auto: loop 继续推进下一阶段
```

---

## 5. 护栏（与仓库铁规对齐）

- **VCS-free（E1）**：编排器只读文件/内容快照，**不调任何 git**；source_check/update_plan 已是 git-free 内容快照，直接复用。
- **契约单一真值（contract）**：阶段图、列名、gate stage、回退字段一律读 `STAGE_GRAPH`/`stage_of`/`gate.py`；编排器**不复制**任何阶段定义。改阶段仍只改 contract。
- **选择点即适配层（C1/C2）**：菜单经 `选择点与偏好.md` 适配层，路由到设置/能力，**不 branch 菜单文字**；普通可逆选择默认用推荐值。付费生成按阶段预算包确认一次，包内调用不重复打断；不可逆/合规/最终人工验收仍按实际动作确认。
- **幂等**：重复 `next` 不产生副作用——前置都是只读机检或幂等回写；`--auto` 在任一 stop-point 必停。
- **不抢 n2d-batch 的活**：`run.py next` 推**单集前沿一步**；多集并发/重试/预算仍走 `n2d-batch`（编排器可作为 batch runner 每个 task 的内部步进器，但本期不做）。
- **独立性（A1/F2）**：落在 `skills/n2d/`，只 import `_lib/`，无 `skills/common`、无跨线引用。

---

## 6. 测试计划（纯 Python 逻辑，符合本仓 pytest 约定）

`skills/n2d/test_run.py`（cd 到 `skills/n2d/` 跑），用临时 `_进度.md` + `_设置.md` 夹具：
1. 前沿解析对齐 `stage_of`（各制作模式：配音先行/先出视频后配音/原生音画）。
2. stop_reason 分类：image 无有效预算包时为 `needs_payment_confirm`，有效 v2 包且当前绑定匹配时为 `needs_stage_execution`；默认缺普通选择会落推荐值，只有显式逐项询问才 `needs_choice`；gate block 必透传 `return_to_stage`。
3. `--auto` 在第一个真实 stop-point 停；已授权付费任务可派发，但探针/supervisor 不消费也不扩大预算。
4. 幂等：连跑两次 `next` 状态不变、无重复回写。
5. 合规缺口 / env 缺失短路。

---

## 7. 已确定的自动化边界

1. `run.py` 在 `needs_agent_gen` / `needs_stage_execution` 返回工位契约，`n2d-supervisor` 继续派发 specialist；它们不是用户选择停点。
2. `n2d-batch runner --next-preflight` 消费同一前沿契约，多集并发/重试/预算仍归 batch；付费任务必须有与当前输入绑定的授权，provider 状态不明时先恢复/结算，绝不靠新 attempt id 重放。
3. `needs_payment_confirm` 只代表预算包缺失/失效/越界或不可逆风险，不代表每次 provider 调用都要问；`needs_compliance`、`needs_acceptance_signoff`、公开发布与破坏性操作仍是人工边界。其他可恢复问题优先自动修复或返回最小返工范围。
