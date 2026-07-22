# n2d Creative Loop

- 集：第2集
- 阶段：script_stage2
- specialist：n2d-script-agent
- max iterations：2

## generate
使用 context_pack 生成本阶段候选产物；不得越过花钱/合规/进度回写边界。

## evaluate
- P-2 导演排戏包是否已 confirmed，并且 beat/轴线调度/景别进程/转场/竖屏构图/剪辑节奏可直接指导 storyboard
- storyboard 是否把台词/动作/镜头时长拆到可执行 Clip
- 高风险镜头是否套专项模板和 template_contract
- 镜头是否有景别阶梯、轴线、状态转场和素材清单闭环

## optimize
只修本阶段产物和直接依赖，不重写无关集/无关资产；保留可追溯 diff 摘要。

## finalize
通过 gate 后再交给用户确认；进度回写仍走对应 stage skill/contract。
