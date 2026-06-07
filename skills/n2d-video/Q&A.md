# n2d-video Q&A

## Q1: 为了确保生成视频的 Clip 之间能够衔接顺畅，视频 prompt 应该怎么改？

A: 把每个镜头的生成约束从"单镜头好看"升级成"连续镜头组一致"。视频 prompt 必须统一增加 `continuity` 字段，并在每个 Clip 明确 5 个子字段：

- `start_state`：从上一 Clip 末尾/本 Clip 首帧承接的人物姿态、站位、视线、道具状态、场景状态。
- `action`：本 Clip 内唯一主动作链，幅度可控，不重设人物/场景。
- `end_state`：给下一 Clip 承接的结尾姿态、视线方向、画面重心或可切出的物件/空镜。
- `constraints`：服装发型、人物左右站位、轴线方向、光线、天气、道具、背景布局保持一致。
- `negative`：不要换脸、不要换衣、不要新增人物、不要改变场景、不要改变发型、不要生成文字/logo/水印、不要生成原生人声。

落地规则：

1. 同一场景内按连续 Clip 组生成 prompt，保持角色、服装、光线、天气、站位、轴线方向一致。
2. 自动读取上一 Clip 的 `end_state` 作为下一 Clip 的 `start_state`；同时读取下一 Clip 的入点/首帧，反推当前 Clip 的 `end_state`。
3. 相邻镜头优先做动作匹配、视线匹配、道具特写、空镜缓冲，不要每条都做大幅运镜。
4. 如果后端支持首尾帧或多镜连拍，优先用上一 Clip 末帧/下一 Clip 首帧作为约束；不支持时也必须在 prompt 里写清首尾状态。
5. 接不上时后期用 4-8 帧交叉淡化、闪白、遮挡物擦镜、快速切特写、环境空镜补缝。

本规则已写入：

- `skills/n2d-video/SKILL.md`
- `skills/n2d-video/references/prompt_format.md`
