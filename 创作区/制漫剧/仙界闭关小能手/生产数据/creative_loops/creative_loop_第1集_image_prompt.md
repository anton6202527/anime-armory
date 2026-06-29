# n2d Creative Loop

- 集：第1集
- 阶段：image_prompt
- specialist：n2d-visual-agent
- max iterations：2

## generate
使用 context_pack 生成本阶段候选产物；不得越过花钱/合规/进度回写边界。

## evaluate
- 每镜是否绑定 CHAR/LOC/PROP/VFX 资产 ID 和参考图
- 多人/表情/坐骑/载具/奇观是否使用保真实现拆法
- 图中文字、系统面板、测灵等级是否走 overlay 而非烤字

## optimize
只修本阶段产物和直接依赖，不重写无关集/无关资产；保留可追溯 diff 摘要。

## finalize
通过 gate 后再交给用户确认；进度回写仍走对应 stage skill/contract。
