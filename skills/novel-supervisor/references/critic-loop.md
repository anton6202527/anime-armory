# 可选·成本闸控的 Critic 迭代（spec，非常开）

## 为什么是 spec 而不是已接线的功能
`novel-supervisor` 本体是**确定性编排 + 熔断器**，**不挂任何 LLM 评委/辩论**（见 SKILL.md）。
这是有意的：开放式 LLM 互评既烧 token，又容易"凭感觉打分"产生不可复现的把关。

但 2026 研究确实显示**结构化的 critic / 盲审能提升创作质量**：
- 盲同行评审反馈（blind peer review）改进创作 — arXiv 2601.08003。
- 多 writer 人格 + LLM Discussion/Debate 三阶段（提案→批判→修订）减少同质化、补逻辑漏洞。

所以这里把 critic 写成**可选、按需、成本闸控**的 spec：想要更高质量时显式开，平时不跑。
**不要**把它默认接进 `post_write` 或 supervisor 的常开主路（那会让每章都烧一轮互评 token）。

## 触发条件（全部满足才值得跑）
1. 章节/弧段已过确定性闸（`novel-review` blocking=0、`logic_sentry`/`timeline_check` 无确定性阻断）——
   critic 是"好上加好"，不是用来兜底硬伤（硬伤交确定性闸，便宜可靠）。
2. 该章是**高权重节点**（开篇黄金三章 / 弧段高潮 / 关键反转），值得多花 token。
3. 用户/`_设置.md` 显式开启 `critic_loop=on`，或单次显式调用。成本点 → 每次确认（对标选择点纪律）。

## 必须 checklist-grounded（不许凭感觉）
每个 critic agent 的判据**绑定项目已有的结构化真值**，不是开放式"你觉得好不好"：
- 读者契约：`设定/读者契约.md` 的价值边界 / 女频雷点是否触发。
- 角色弧光：`设定/arc_summaries.json` / 情绪进度 — 本章是否推进了登记的弧段，还是原地打转。
- 伏笔账本：`设定/foreshadowing_ledger.json` — 本章该埋/该收的是否兑现。
- 力量体系：`设定/power_system_registry.json` — 数值/等级是否自洽（与 power_system 自检同源）。
每条 critic 结论必须**引用具体账本条目**作证据，否则丢弃（防"plausible but ungrounded"）。

## 推荐结构（perspective-diverse，胜过 N 个同质评委）
给每个 critic 不同**镜头**而非重复同一提示：
- 爽点/留存镜：钩子密度、章末钩子、弃书点。
- 逻辑镜：动机自洽、金手指代价、设定一致（接 storyworld 压力测试维度）。
- 文笔/对话镜：活人感、AI 味、对话信息密度。
多数镜判"需改"才回流；单镜异议记为 advisory。**评委 ≠ 生成者**（别让写这章的同一 persona 自评）。

## 判官去偏协议（一旦真跑 LLM 判官就**必接**·确定性执行层已就绪）
LLM 判官有系统偏差（LitBench arXiv 2507.00769 / dual-judge / blind peer review arXiv 2601.08003），
最突出是 **position bias**（偏好靠前候选）与**单模型偏**。判官产出的原始 verdict **不能直接采信**，
必须过三条去偏协议——已在 `skills/novel/_lib/judge_protocol.py` 实现为**纯确定性校验/聚合层**
（它不调用 LLM，只把 LLM 在仓库外产出的 verdict 按协议过一遍）：
1. **position-swap 稳定**：每对候选让判官在 (A,B) 与 (B,A) 两序各判一次；只有两序判同一赢家才算数，
   翻面=位置偏 → 该判官此对作废（`position_stable_winner`）。
2. **dual-judge 一致**：≥2 个**不同**判官模型、全体 position-stable 票指向同一赢家才采纳；分歧 →
   `tie`（需人判），不强行取多数（`pairwise_consensus(min_judges=2)`）。
3. **rubric-anchored**：量规分先按判官内 z 归一去判官宽严偏再聚合；判官间高方差准则标 `low_confidence`，
   不拿去当结论（`zscore_normalize` / `aggregate_rubric`）。
一次成对裁决用 `debias_verdict(judgements, panel=...)` 收口，返回 `{winner, decision, confidence,
consensus, rubric}`，全过程留痕。结论始终 **advisory**，绝不当确定性门控（B10）。

**直接可执行（别再手算）**：把判官原始 verdict 写成 JSON，跑 CLI——
```bash
# verdicts.json: [{"judge":"m1","ab_winner":"稿A","ba_winner":"稿A"}, ...]；panel.json: {"m1":{"hook":9}, ...}
python3 skills/novel/_lib/judge_protocol.py --verdicts verdicts.json [--panel panel.json]
# critic-loop 要「不达标就别采纳」时加 opt-in 硬闸（信心不足 → exit 1）：
python3 skills/novel/_lib/judge_protocol.py --verdicts verdicts.json --require-confidence high
```
默认恒 `exit 0`（纯 advisory）；只有显式 `--require-confidence` 才把信心不足升成非零退出。

## 成本闸控
- 跑前估算 token（章字数 × 镜头数 × 轮数），超 `_设置.md` 预算上限 → 停下报数等确认。
- 默认单轮、≤3 镜；想要 debate（提案→批判→修订）再加一轮，且每加一轮重新确认成本。
- 熔断：复用 supervisor 的 `record-execution` 计数，同章 critic 连续 N 轮无新增有效意见即停（防无限互评）。

## 落地边界（现状）
本文件是**设计 spec**，仓库内**未接线**任何常开 LLM critic。要实现时：
- 入口应是显式子命令（如 `novel-review --critic <章>`）或 `_设置.md` 显式开关，**不是** post_write 默认。
- 产出落 `审稿/critic_<章>.json`，作为 advisory 进 `novel-review` 汇总，**不**作确定性门控
  （与 B10 一致：LLM 软判不硬阻断发布）。
