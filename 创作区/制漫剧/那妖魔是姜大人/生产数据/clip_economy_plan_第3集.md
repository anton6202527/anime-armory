# Clip 经济性规划（生成次数预算 + 合并候选）

- episode: 第3集
- 当前预计生成次数: 14（9.46/min）
- 合并后预计: 14（9.46/min）
- 合并候选组: 0 · 并入相邻强戏候选: 0 · 单Clip补take_policy候选: 0
- 复杂度: simple（2场景/4角色/2动作镜）· 预算 7.0/min · 片段经济档 紧凑· 超预算
- 能力快照: 2026-07-22（单次多镜上限口径 15.0s·会过期）

## 合并候选组

- 无（相邻镜要么不同场景，要么高风险/超单次窗口）

## 并入相邻强戏候选

- 无

## 单 Clip 补 take_policy 候选（内部镜位一次生成）

- 无

## Findings（全部 heuristic·report-only）

- WARN generation_density_over_budget: 本集复杂度=simple（2场景/4角色/2动作镜），当前每分钟预计生成 9.46 次 > 预算 7.0/min。采纳下方 merge/单拍多镜合并后约 9.46/min。简单叙事优先「更少更长的多镜单拍」，不必逐节拍独立成付费 clip。
- WARN long_clips_force_part_split: 3 个 clip 时长超单次生成窗口，被拆成 ≥3 段付费 part：EP03_CLIP04(15.383s→3段), EP03_CLIP06(15.551s→3段), EP03_CLIP07(12.221s→3段)。「每个独立生成 clip 再简短点」：把这些 beat 写短到单次窗口一段成，或合并内部镜位（take_policy=single_take_multishot），直接减 part 数。时长/节奏改动属阶段2签收变更，本脚本不自动改写。

## Rules

- 两条正交预算：takes/min（一个 clip 拆几次生成）与 clips/min（本集被拆成几个 clip）。前者靠 merge/单拍省，后者靠合并相邻节拍减 clip 数。
- 生成次数预算按集看，不只按单 Clip 时长看：简单叙事优先「更少更长的多镜单拍」而不是逐节拍独立 clip。
- 长 clip（超单次生成窗口、被拆成多段付费 part）会被点名 shorten：把 beat 写短到单次窗口一段成，直接减 part 数（用户诉求「每个独立生成 clip 再简短点」）。
- 已生成视频的 Clip 是沉没成本：不进省次数候选、不触发 enforce 阻断；进行中的集不追溯返工，返工走 n2d-update 最小重制。
- 合并候选只提案不执行：改 storyboard 是签收产物变更，须编剧在阶段2精修确认。
- 高动作模板/锚链/奇观镜不进合并候选：安全拆分与锚帧链优先于省次数（与 shot_split_decision 同口径）。
- 本报告全部启发式、report-only（宪法 B10）；密度口径带能力快照日期，会过期，执行前按 C2 刷新。
