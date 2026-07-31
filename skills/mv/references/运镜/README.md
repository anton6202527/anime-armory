# MV 运镜参考库

本目录是 mv 系列的运镜参考库，按 MV 卡点和段落张力使用。机器可读真值源是 [`manifest.json`](manifest.json)：它登记中文/英文名、别名、slot、风险等级、prompt 模板、本地预览/contact sheet，以及已授权公开再分发动画的远端 URL/bytes/SHA-256。

## 使用原则

- `mv-plan` 写 `clip_plan.json` 时，用 manifest 选择一条主运镜，避免只写“炫酷运镜”。
- `mv-video` 写 prompt 时，仍按结构化字段落地：`镜头运动：{运镜词}；速度={...}；方向={...}；起止={...}`。
- 副歌/downbeat 可以用快推、甩镜、环绕、冲击变焦；verse/outro 优先固定、缓推、跟拍、拉远。
- 动作峰值必须对齐 beat/downbeat；运镜只服务节奏，不替代人物动作和转场母题。
- `_preview/` 是 Desktop 快速预览用轻量首帧；`_contact/` 是 agent 默认读取的五帧运动拼图。
- 只有需要判断完整运动节奏、轨迹或与 beat 的相位关系时，才运行 `python3 skills/mv/scripts/camera_reference.py fetch <运镜ID或名称>` 下载动画到仓库外用户缓存，并强制校验 bytes + SHA-256。
- 断网或下载失败时继续使用 manifest + contact sheet，不阻断 MV 规划或视频 prompt。

## 接入点

- 机器真值：`skills/mv/references/运镜/manifest.json`
- 规划阶段：`skills/mv/mv-plan/scripts/plan_clips.py`
- 视频 prompt：`skills/mv/mv-video/references/prompt_format.md`
- 动作库：`skills/mv/mv-video/references/action_knowledge.md`
