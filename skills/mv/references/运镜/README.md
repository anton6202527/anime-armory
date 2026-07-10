# MV 运镜参考库

本目录是 mv 系列的运镜参考库，以运镜库快照为初始来源，已复制为本系列自包含资源，按 mv 的卡点和段落张力使用。机器可读真值源是 [`manifest.json`](manifest.json)：它登记中文/英文名、别名、slot、风险等级、prompt 模板和媒体路径。

## 使用原则

- `mv-plan` 写 `clip_plan.json` 时，用 manifest 选择一条主运镜，避免只写“炫酷运镜”。
- `mv-video` 写 prompt 时，仍按结构化字段落地：`镜头运动：{运镜词}；速度={...}；方向={...}；起止={...}`。
- 副歌/downbeat 可以用快推、甩镜、环绕、冲击变焦；verse/outro 优先固定、缓推、跟拍、拉远。
- 动作峰值必须对齐 beat/downbeat；运镜只服务节奏，不替代人物动作和转场母题。
- `_preview/` 是 Tauri 预览用轻量首帧，避免直接解码 animated WebP。

## 接入点

- 机器真值：`skills/mv/references/运镜/manifest.json`
- 规划阶段：`skills/mv-plan/scripts/plan_clips.py`
- 视频 prompt：`skills/mv-video/references/prompt_format.md`
- 动作库：`skills/mv-video/references/action_knowledge.md`
