# n2d 编排器 `run.py next` — 接口契约设计（待评审 v0.1）

> 目的：把 I2 铁律（"确定性步骤代理自动链式跑完，只在决策/花钱/合规点停"）从 SKILL.md 的 prose
> 变成**一段可执行的确定性胶水**。当前代理每推进一集一个阶段要手工串
> `source_check → update_plan → progress.py → model-router → dashboard gate → stage skill → progress set → dashboard record`，
> 本设计把这串散装命令收敛成 1 个入口 + 1 个结构化"下一步动作"对象。
>
> **本文是接口契约，不是实现。** 评审通过后再实现 + 配 pytest。

---

## 0. 一个必须先讲清的现实约束（决定了编排器的形态）

stage skill **不是**"一条命令跑完即出产物"的子进程。它们混着两类工作：

- **(a) 确定性脚本**：gate 机检、model-router 路由、prompt 脚手架、进度/manifest/dashboard 回写、身份矩阵刷新……
- **(b) 代理创作**：读 prompt 包 → 调自身 LLM 生成剧本/分镜 JSON/出图 prompt 文案 → 注入项目；以及真正花钱的出图/出视频/合成。

所以编排器**不能**把 `n2d-image` 当 `subprocess` 一把梭跑完。它能做的是：

> **把某阶段所有"确定性前置"自动跑完，跑到第一个"需要脑子 / 需要钱包 / 需要签字"的点就停下，
> 交回一张结构化的「下一步动作卡」。**

这是诚实版：它消灭代理现在手写的全部确定性拼接，但创作/花钱那一下仍回到代理/用户。这正好就是 I2 想要的"人只做决策"。

---

## 1. 命令面

```bash
python3 skills/n2d/run.py next <作品根> [第N集] [--json] [--auto]
```

- 无集号 → 用 `summarize()` 取**最小未完成集**为前沿。
- 带集号 → 只推进该集。
- `--json` → 输出机器可读的 `NextAction`（代理消费）；默认输出人话（用户可读）。
- `--auto` → **连续推进**：每跑完一个确定性前置就看下一步，能自动就继续，**直到第一个 stop-point**；不加 `--auto` 只解析一次前沿 + 跑该阶段前置 + 停。
- 只读 / 只跑确定性前置；**绝不**自行花钱、自行执行创作、自行改后端。

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
  "stop_reason": "needs_payment_confirm",   // 见 §3 枚举
  "action_card": {
    "headline": "第3集 准备出图（花钱·不可逆）",
    "to_user": "出图前需你确认 生成粒度（逐个/小批/按场景/整集）并放行。",
    "menu": { "choice_point": "生成粒度", "options": ["逐个","小批","按场景分批","整集"], "default_preselect": "逐个" },
    "exact_command": "n2d-image <作品根> 第3集",
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
| `needs_payment_confirm` | 前沿 `STAGE_GRAPH[key].gate_stage` 属花钱档（image / video / compose；voice 走云后端时） | 停，附 `生成粒度` 菜单 + 放行确认 |
| `needs_choice` | 该阶段有**未解析**的"首跑必给"/"每次必问"选择点（制作模式·生视频模型·生视频渠道·基础视觉风格·BGM来源·生成粒度） | 停，弹对应菜单（默认预选=设置里的上次值，但不沉默沿用） |
| `needs_compliance` | `n2d-compliance --check` 在 image/video/compose 前报缺口 | 停，列缺口，绝不放行 |
| `blocked_by_gate` | `dashboard gate` 退出码 1 | 停，透传 `return_to_stage/affected_artifacts/rerun_scope`，指向最小返工 |
| `env_missing` | `doctor.py` 报该阶段所需后端/精度档缺失 | 停（或路由占位+大声告警），不让代理跑到花钱工位才发现 |
| `auto_ran` | 纯确定性步骤（router/gate-pass/矩阵刷新/进度回写） | **不停**，`--auto` 下继续推进 |
| `done` | `stage_of` 返回 `col=None`（已成片） | 报完成 |

> 关键不变量：**编排器只会在 `gate_stage` 标了花钱、或选择点未解析、或合规/env 缺口时停。**
> 其余（找前沿、跑 gate、写路由表、刷身份矩阵、回写进度+dashboard）一律自动，对代理透明。

---

## 4. 执行循环（伪码）

> **边界**：`源新鲜度自检`（source_check）与 `skill 更新影响检查`（update_plan）是 **dispatcher 进作品时的
> 一次性入口步骤**（SKILL.md 情境B），**不**进 `run.py next` ——否则每步推进都会重跑、浪费。`run.py next`
> 只管"逐步推进 + 每步的确定性前置（doctor/router/gate/compliance/首跑选择探测）"。

```
def next(root, ep=None, auto=False):
    while True:
        route = stage_of(root, row(ep or 最小未完成集), header)  # 现有真值
        if route.col is None: return DONE
        spec = STAGE_GRAPH[route.stage_key]

        # 4.1 跑该阶段的确定性前置（当前散在 SKILL.md §gate前置 / §读进度路由）
        if spec.owner == "n2d-video": run(model_router --write)   # 出视频前置
        if spec.gate_stage: g = run(dashboard gate --stage spec.gate_stage --json)
            if g.blocked: return STOP(blocked_by_gate, gate=g)

        # 4.2 选择点 / 合规 / env
        if unresolved_choice(spec): return STOP(needs_choice, menu=…)
        if spec.gate_stage in PAID and compliance_gap(): return STOP(needs_compliance)
        if needs_agent_gen(spec):    return STOP(needs_agent_gen, prompt_pack=…)
        if is_paid(spec):            return STOP(needs_payment_confirm, menu=生成粒度)

        # 4.3 纯确定性阶段：极少；若有，跑完→回写→继续
        run_deterministic(spec); progress_set(...); dashboard_record(...)
        if not auto: return STOP(auto_ran, advanced=spec.key)
        # auto: loop 继续推进下一阶段
```

---

## 5. 护栏（与仓库铁规对齐）

- **VCS-free（E1）**：编排器只读文件/内容快照，**不调任何 git**；source_check/update_plan 已是 git-free 内容快照，直接复用。
- **契约单一真值（contract）**：阶段图、列名、gate stage、回退字段一律读 `STAGE_GRAPH`/`stage_of`/`gate.py`；编排器**不复制**任何阶段定义。改阶段仍只改 contract。
- **选择点即适配层（C1/C2）**：菜单经 `选择点与偏好.md` 适配层，路由到设置/能力，**不 branch 菜单文字**；花钱/不可逆/合规点每次确认，不沉默沿用。
- **幂等**：重复 `next` 不产生副作用——前置都是只读机检或幂等回写；`--auto` 在任一 stop-point 必停。
- **不抢 n2d-batch 的活**：`run.py next` 推**单集前沿一步**；多集并发/重试/预算仍走 `n2d-batch`（编排器可作为 batch runner 每个 task 的内部步进器，但本期不做）。
- **独立性（A1/F2）**：落在 `skills/n2d/`，只 import `_lib/`，无 `skills/common`、无跨线引用。

---

## 6. 测试计划（纯 Python 逻辑，符合本仓 pytest 约定）

`skills/n2d/test_run.py`（cd 到 `skills/n2d/` 跑），用临时 `_进度.md` + `_设置.md` 夹具：
1. 前沿解析对齐 `stage_of`（各制作模式：配音先行/先出视频后配音/原生音画）。
2. stop_reason 分类：到 image 前必 `needs_payment_confirm`；缺选择点必 `needs_choice`；gate block 必透传 `return_to_stage`。
3. `--auto` 在第一个 stop-point 停、不越过花钱点。
4. 幂等：连跑两次 `next` 状态不变、无重复回写。
5. 合规缺口 / env 缺失短路。

---

## 7. 待你拍板的开放问题

1. **落点**：`skills/n2d/run.py`（与 doctor/progress/manifest 同级）——同意？
2. **`--auto` 的默认边界**：我倾向 auto 也**永远**停在 `needs_agent_gen`（创作要代理脑子）。即 auto 只自动跑"确定性前置链"，不替代任何创作。认可？
3. **是否本期就接 `n2d-batch`**（让 runner 每个 task 调 `run.py next` 步进）？我建议**本期不接**，先把单集前沿打通、配测试，batch 接入下一迭代。
4. **人话输出**用中文动作卡（headline + 一句 to_user + 命令 + 菜单）即可，还是要更精简？
