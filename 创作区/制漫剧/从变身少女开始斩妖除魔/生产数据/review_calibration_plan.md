# n2d-review 独立校准计划（未执行）

- 当前层级：self-checked=complete；adversarially-tested=complete；externally-grounded=complete；externally-calibrated=not_run。
- 原因：尚无本项目已生成图片/视频可组成留出样本，也没有独立于实现与抽样的人工审阅者。不能用代码测试、论文链接或 agent 自评替代盲法校准。

## 触发时点

1. 姜月初常态/妖化五角与第1集高风险样片生成后，先做探索校准。
2. 第1–3集完成、可用样本达到100项后，做 production 校准。
3. 换主生图/生视频后端、风格或主体锁方案后重新抽样；旧校准不能跨后端直接复用。

## 预声明方案

- Population：本项目所有待验收角色视图、分镜图与视频片段；抽样前锁定清单与 SHA。
- Strata：常态近景、妖化近景、侧/后视角、多人同框、暗光/遮挡、动作/VFX、对白静态、场景/道具连续性。
- Exploratory：每层至少5项，总样本不少于40；只用于找阈值和漏检类型，不宣称生产准确率。
- Production：分层随机总样本不少于100；抽样人独立于实现者；审阅者看不到 gate 结果。
- Ground truth：两轮独立标签；分歧交第三人裁决；三名审阅者均声明与实现无利益冲突。
- 预声明阈值：核心身份/多视图 BLOCK 的 FNR ≤10%；FPR ≤5%。其他维度先以探索数据确定阈值，不倒推修改以追求通过。
- 产物：protocol、sample_manifest、predictions、ground_truth 四类文件均记录当前 SHA；机器复算 confusion matrix、FNR/FPR。

## 失败处理

- FNR 超阈：提高对应硬闸、增加反例和结构化证据；回放所有漏检样本。
- FPR 超阈：先区分低置信启发式与确定性合同；把低置信项降为 WARN+人审，不降低权利、像素、哈希和结构化缺失类硬闸。
- 任一独立性、盲法、抽样锁定、裁决、当前 SHA 或指标字段缺失：校准记 invalid，不记 complete。

即使将来校准通过，也只能表述为“本次锁定样本在预声明阈值内”，不能表述为审查无偏、没有盲区或跨题材普适。
