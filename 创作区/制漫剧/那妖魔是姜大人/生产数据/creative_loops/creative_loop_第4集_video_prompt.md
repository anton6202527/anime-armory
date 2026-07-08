# n2d Creative Loop

- 集：第4集
- 阶段：video_prompt
- specialist：n2d-visual-agent
- max iterations：2

## generate
使用 context_pack 生成本阶段候选产物；不得越过花钱/合规/进度回写边界。

## evaluate
- 是否继承 storyboard.template_contract 的专属字段
- 模型路由、首中尾帧、motion control/degrade plan 是否一致
- 身份/资产/屏幕方向/接缝是否有明确锁定句和负向约束

## optimize
只修本阶段产物和直接依赖，不重写无关集/无关资产；保留可追溯 diff 摘要。

## finalize
通过 gate 后再交给用户确认；进度回写仍走对应 stage skill/contract。
