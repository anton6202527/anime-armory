# 漫画镜头语言参考库

本目录是 comic 系列的镜头语言参考库。漫画不直接播放运镜，但这些条目可以转译为静态格子的机位、景别、速度线、前景遮挡、格子轻重和阅读节奏。机器可读真值源是 [`manifest.json`](manifest.json)；本地 `_contact/` 五帧拼图让 agent 离线理解运动轨迹，已授权公开再分发的完整动画则以 URL/bytes/SHA-256 登记在 manifest。

默认只读 manifest + contact sheet。只有静态转译仍无法判断运动方向/节奏时，才运行 `python3 skills/comic/scripts/camera_reference.py fetch <运镜ID或名称>` 下载到仓库外用户缓存；下载强制校验 bytes + SHA-256，断网不阻断漫画脚本。

## 静态转译

- 推镜头：更近景别、更大面部/道具占比，用于压迫、发现、情绪聚焦。
- 拉镜头：扩大环境关系，用于孤独、余韵、暴露处境。
- 甩镜/冲击变焦：斜切格、动势线、速度线、冲击线，适合动作峰值或惊讶反应。
- 焦点转移：前后景虚实、视线引导、景深层次，适合证物/背后危险揭示。
- 前景遮挡揭示：门框、树枝、肩后视角，制造悬念和空间层次。
- 顶视俯拍/无人机航拍：大格定场、阵法几何、路线、群像站位。
- 环绕/盘旋：优先转成大格奇观或连续小格，不强求单格表达完整运动。

## 接入点

- 机器真值：`skills/comic/references/运镜/manifest.json`
- 分格脚本：`skills/comic/comic-script/SKILL.md`
- 出图任务 schema：`skills/comic/comic-image/references/prompt_job_schema.md`
- 排版：`skills/comic/comic-layout/SKILL.md`
