# Clip 经济性规划（生成次数预算 + 合并候选）

- episode: 第2集
- 当前预计生成次数: 12（10.01/min）
- 合并后预计: 8（6.67/min）
- 合并候选组: 0 · 并入相邻强戏候选: 0 · 单Clip补take_policy候选: 2
- 能力快照: 2026-07-22（单次多镜上限口径 15.0s·会过期）

## 合并候选组

- 无（相邻镜要么不同场景，要么高风险/超单次窗口）

## 并入相邻强戏候选

- 无

## 单 Clip 补 take_policy 候选（内部镜位一次生成）

- EP02_CLIP01（12.606s·当前 3 take → 1）：storyboard 该 Clip 写 take_policy=single_take_multishot：内部镜位交 multishot-native 后端一次生成，不再拆独立付费 take。
- EP02_CLIP02（12.076s·当前 3 take → 1）：storyboard 该 Clip 写 take_policy=single_take_multishot：内部镜位交 multishot-native 后端一次生成，不再拆独立付费 take。

## Findings（全部 heuristic·report-only）

- WARN generation_density_high: 当前每分钟预计生成 10.01 次（> 10/min 口径）。多镜叙事后端（快照 2026-07-22）单次可承载多个镜位；按下方 merge/fold 候选合并后约 6.67/min。简单叙事优先合并，不必逐节拍独立成付费 clip。
- WARN merge_candidates_available: 发现 0 组相邻合并候选 + 2 个单 Clip 补 take_policy 候选，采纳后本集预计生成次数 12 → 8。均属阶段2精修的签收变更，由编剧确认后改 storyboard，本脚本不自动改写。

## Rules

- 生成次数预算按集看，不只按单 Clip 时长看：简单叙事优先「更少更长的多镜单拍」而不是逐节拍独立 clip。
- 合并候选只提案不执行：改 storyboard 是签收产物变更，须编剧在阶段2精修确认。
- 高动作模板/锚链/奇观镜不进合并候选：安全拆分与锚帧链优先于省次数（与 shot_split_decision 同口径）。
- 本报告全部启发式、report-only（宪法 B10）；密度口径带能力快照日期，会过期，执行前按 C2 刷新。
