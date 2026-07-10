# Prompt compiler 跨线落地决策

日期：2026-07-10

## 统一原则

完整生产合同服务于制作决策、确定性 gate、人工复核和溯源；实际后端输入只包含模型能执行的内容与真实请求控制。两者通过本线自持 compiler 单向连接，manifest 用 compiler/profile、source hash 与 submit hash 绑定。各线不共享 compiler 代码，也不建立目录依赖。

## 落地矩阵

| 生产线/阶段 | 完整合同保留 | 实际提交 | 结果 |
|---|---|---|---|
| n2d-video | 导演意图、continuity、身份/在场链、接缝、执行配方、音画/QC | 主动作、运镜、必要环境响应、节奏/落幅、最短保持；负向/音频/参考控制分字段 | 已迁移；runner/gate 只认 compiler 块 |
| ad-video | 品牌色、产品锁、资产 ID、精确 CTA/slogan/价格/法律声明、安全区、广告合规、路由 | 产品动作、运镜、明确环境响应、落幅、产品保持；精确文字由后期可控叠加 | 已迁移；Dreamina runner 与继承闸门校验 |
| mv-video | 身份锚、参考输入、首尾帧、卡点、continuity、渠道/规格、声音策略 | 人物主动作、运镜、明确环境响应、动作峰值、落幅；歌曲始终外铺 | 已迁移；schema v2 take + inherit gate |
| comic-image | 角色 DNA、场景锚、内部 ID/路径、continuity、禁继承、传统稿层、审计 | 可见画面、构图/表演、画风稿层、可画连续性、最短身份保持、墨线/网点/效果、无字与人体接触点 | 已迁移；schema v2 job + preflight/runner 双校验 |
| song-compose | A&R、参考边界、和声/topline、权利/音色来源、操作与挑版标准 | 后端映射的 style/prompt + **完整歌词原文** + duration/title；不把整份合同粘进 style | 已迁移；schema v2 take 与登记前 hash 校验 |
| novel | 蓝图、设定、状态账本、读者契约、章纲、场景卡、前文窗口、修订项 | 上述信息本身就是逐章写作所需上下文 | 不新增短 prompt compiler；保持 task packet + static/dynamic context + retrieval/hash/cache metrics |

## 迁移规则

1. 旧任务包若缺 compiler 元数据或仍把完整合同当提交文本，正式付费生成前重建，不长期维护两套执行真值。
2. `prompt` 兼容键若保留，只能指向 `submit_prompt`；完整合同另存明确命名字段。
3. 参考图、首尾帧、音频、主体句柄、ControlNet 等必须作为结构化请求控制真实传入，不能退化成路径散文。
4. 长度阈值通常只作 advisory；缺主动作/可见事实/必要字段、后端不一致、内部合同泄漏、hash 漂移才作确定性 BLOCK。
5. 不为了“全仓统一”抽公共 compiler。统一的是边界与审计法则，不是实现代码和媒介信息密度。
