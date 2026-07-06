# n2d Supervisor Plan

- 集：第4集
- 阶段：script_stage1
- 停因：blocked_by_entry_check
- specialist：n2d-script-agent
- human gate：True
- call specialist：False

## Specialist

- scope：剧本改编、分镜设计、题材母题、爽点/钩子/叙事连续性

## Allowed

- run deterministic prework already declared by run.py
- read context_pack before opening full references
- call the selected specialist for draft/evaluation when should_call_specialist=true
- write supervisor plan under 生产数据/supervisor

## Forbidden

- execute paid generation
- override compliance or gate blocks
- change backend without adapter evidence
- write _进度.md directly
- replace stage skill contracts

## Runtime Guardrails（五类失效模式护栏）

- 派发轮 0/6　循环预算耗尽：False
- specialist 超时预算：600s（级联超时隔离）
- 产物须重过 gate：True（防幻觉级联当既定事实）
- 约束指纹：`ef67cd4ae145b4dd`（每轮回带，防上下文丢约束）
- 工具策略：只调 run.py 声明的确定性 prework 与选定 specialist；未声明工具调用视为越界（工具误用护栏）

## Packs

- context：`生产数据/context_packs/context_pack_第4集_script_stage1.json`
- creative loop：`生产数据/creative_loops/creative_loop_第4集_script_stage1.json`
