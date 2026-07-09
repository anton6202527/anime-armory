# 画漫画 skill 更新计划 — 那妖魔是姜大人

- 生成时间：2026-07-09T02:44:20+00:00
- 当前阶段上界：审查 (`review`)
- 当前前沿：缩略分镜 / comic-name / missing_column
- 变更 skill：comic-update
- 新纳入 skill：无
- 结构缺口：6
- 是否建议重制：是
- 建议回放：漫画脚本 → 审查
- 受影响话别：第1话、第2话

## 备注
- 项目存在新版 comic 流程缺口；即使没有历史快照，也建议按缺口回放。

## 结构缺口
- `第1话` `缩略分镜` warn: name_board_missing — 已推进到后续阶段，但缺少缩略分镜/name_board。（排版/第1话/name_board.json）
- `第1话` `原稿收尾` warn: finishing_plan_missing — 已推进到出图/合成/审查，但缺少原稿收尾计划。（出图/第1话/finishing/finishing_plan.json）
- `第2话` `漫画脚本` block: visual_contract_missing — panel_script 缺少新版必需的 visual_contract。（脚本/第2话/panel_script.json）
- `第2话` `缩略分镜` warn: name_board_missing — 已推进到后续阶段，但缺少缩略分镜/name_board。（排版/第2话/name_board.json）
- `第2话` `原稿收尾` warn: finishing_plan_missing — 已推进到出图/合成/审查，但缺少原稿收尾计划。（出图/第2话/finishing/finishing_plan.json）
- `第2话` `审查` block: review_gate_block — 最近 review gate 仍有 86 个阻断。（生产数据/comic_gate_review_第2话.json）

## 变更文件
- `skills/comic-update/scripts/update_plan.py`

## 建议步骤
- 人工/AI判断：重制前先保留当前 panel_script/layout/panel_jobs/成图/导出物；旧图进入 candidates 或废料目录，不无痕覆盖。
- 可执行命令：`python3 skills/comic-name/scripts/build_name_board.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第1话`
- 可执行命令：`python3 skills/comic-layout/scripts/build_layout.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第1话`
- 可执行命令：`python3 skills/comic-finishing/scripts/build_finishing_plan.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第1话`
- 可执行命令：`python3 skills/comic-image/scripts/build_panel_jobs.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第1话`
- 人工/AI判断：正式重出 PNG 前确认模型、渠道、预算和目标格；若只改便宜结构层，先跑 image gate 判断旧图是否可保留。
- 可执行命令：`python3 skills/comic-review/scripts/gate.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第1话 --stage image_preflight`
- 人工/AI判断：若 layout 或面板图变化，重新运行 comic-compose 生成 第1话 的 lettering、页面图和长图。
- 可执行命令：`python3 skills/comic-review/scripts/gate.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第1话 --stage review`
- 人工/AI判断：按 comic-script 补齐 第2话 的 visual_contract、逐格场景锚/视线/完整性/站位字段。
- 可执行命令：`python3 skills/comic-name/scripts/build_name_board.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第2话`
- 可执行命令：`python3 skills/comic-layout/scripts/build_layout.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第2话`
- 可执行命令：`python3 skills/comic-finishing/scripts/build_finishing_plan.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第2话`
- 可执行命令：`python3 skills/comic-image/scripts/build_panel_jobs.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第2话`
- 人工/AI判断：正式重出 PNG 前确认模型、渠道、预算和目标格；若只改便宜结构层，先跑 image gate 判断旧图是否可保留。
- 可执行命令：`python3 skills/comic-review/scripts/gate.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第2话 --stage image_preflight`
- 人工/AI判断：若 layout 或面板图变化，重新运行 comic-compose 生成 第2话 的 lettering、页面图和长图。
- 可执行命令：`python3 skills/comic-review/scripts/gate.py "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人" --chapter 第2话 --stage review`
- 可执行命令（重制产物验收通过）：`python3 skills/comic-update/scripts/update_plan.py record "/Users/wesley/learn/anime-armory/创作区/画漫画/那妖魔是姜大人"`
