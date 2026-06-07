# mv-video Q&A

## Q1: MV 系列如何像 n2d-video 一样保证 clip 之间衔接顺畅？

A: MV 的 clip 衔接不能照搬漫剧。漫剧更强调叙事空间连续，MV 更强调"视觉身份一致 + 卡点落点准 + 动作/视线/道具可切"。因此每个 MV clip 也必须增加 `continuity` 字段，但要同时读取相邻 clip、`beatgrid.json`、段落张力和歌词钩子。

每个 clip 必填 5 个字段：

- `start_state`：承接上一 clip 末尾/本 clip 首帧的人物姿态、站位、视线、道具状态、场景状态。
- `action`：本 clip 内唯一主动作链，动作峰值或镜头冲击点对齐指定 beat/downbeat。
- `end_state`：给下一 clip 承接的结尾姿态、视线方向、画面重心、道具特写、光效或空镜落点。
- `constraints`：角色定妆、服装发型、主色调、光线、天气、道具、背景布局、轴线/屏幕方向在同段落内保持一致。
- `negative`：不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声。

MV 版落地规则：

1. `clip 时长` 仍由 `beatgrid.json` 决定，不因为连续性改成等长。
2. `action` 的峰值对齐 beat/downbeat，尤其副歌高光、拔剑、回眸、光效爆点。
3. 同一段落尽量保持角色、服装、主色调、场景光线一致；跨段落可以换场景，但角色定妆和核心道具保持。
4. 接不住时优先用动作切、视线切、道具特写、光效切、遮挡擦镜、空镜缓冲，不要让视频模型硬做复杂连续动作。
5. 视频模型生成原生音频一律禁止，音乐和歌词字幕由 `mv-compose` / `mv-lyric-sync` 使用原歌轨统一处理。

本规则已写入：

- `skills/mv-video/SKILL.md`
- `skills/mv-video/references/prompt_format.md`
