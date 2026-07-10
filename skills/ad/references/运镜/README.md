# 广告运镜参考库

本目录是 ad 系列的运镜参考库，以运镜库快照为初始来源，已复制为本系列自包含资源，按广告产品展示、demo 实拍和平台安全区使用。机器可读真值源是 [`manifest.json`](manifest.json)：它登记中文/英文名、别名、slot、风险等级、prompt 模板和媒体路径。

## 使用原则

- `ad-video` 写逐 Clip prompt 时，从 manifest 选择一条主运镜，并补速度、方向、起幅、落幅。
- 产品、logo、CTA、法律声明必须留 action-safe；强推、环绕、甩镜、无人机和载具跟拍只能在产品形态/品牌色已锁定且安全区足够时使用。
- 产品 hero 可以用缓推、环绕、前景遮挡揭示；demo 实拍优先稳定器跟拍、手持轻晃、低机位贴地跟拍。
- end card、包装定格、法律声明镜头优先固定机位或极慢推镜头。
- `_preview/` 是 Tauri 预览用轻量首帧，避免直接解码 animated WebP。

## 接入点

- 机器真值：`skills/ad/references/运镜/manifest.json`
- 视频阶段：`skills/ad-video/SKILL.md`
- 视频路由：`skills/ad-video/scripts/route.py`
- 视频 prompt：`skills/ad-video/scripts/plan_prompts.py`
