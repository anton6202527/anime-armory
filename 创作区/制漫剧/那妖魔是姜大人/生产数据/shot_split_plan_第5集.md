# 镜头拆分决策计划

- episode: 第5集
- ok: True

| Clip | Dur | Action | Economy | Target | Video Shots | N | G | R | Risk Tags | Reason |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| EP05_CLIP01 | 19.247s | split_video_shots | premium_detail | 8.0-15.0s | 4 | 2 | 2 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、large_expression_span、many_named_characters、vfx_or_asset、spectacle_fight_exchange | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |
| EP05_CLIP02 | 15.408s | split_video_shots | premium_detail | 8.0-15.0s | 3 | 0 | 0 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、large_expression_span、many_named_characters、vfx_or_asset、spectacle_fight_exchange | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |
| EP05_CLIP03 | 19.890s | split_video_shots | premium_detail | 8.0-15.0s | 4 | 2 | 1 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、large_expression_span、many_named_characters、vfx_or_asset、spectacle_fight_exchange | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |
| EP05_CLIP04 | 10.479s | template_required | premium_detail | 8.0-11.0s |  | 0 | 2 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、many_named_characters、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP05_CLIP05 | 11.798s | template_required | premium_detail | 8.0-15.0s |  | 0 | 1 | 5 | long_clip_8s、high_motion、mouth_visible、closeup、large_expression_span、many_named_characters、vfx_or_asset、spectacle_fight_exchange | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP05_CLIP06 | 12.093s | split_video_shots | premium_detail | 8.0-15.0s | 3 | 0 | 0 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset、spectacle_fight_exchange | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |
| EP05_CLIP07 | 26.545s | split_video_shots | premium_detail | 8.0-15.0s | 5 | 2 | 2 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、large_expression_span、many_named_characters、vfx_or_asset | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |
| EP05_CLIP08 | 15.897s | split_video_shots | premium_detail | 10.0-18.0s | 3 | 0 | 1 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、many_named_characters、vfx_or_asset | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |
| EP05_CLIP09 | 21.036s | split_video_shots | premium_detail | 16.0-22.0s | 4 | 2 | 1 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、vfx_or_asset | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。Economy 来自 story_economy_audit；Video Shots 为建议拆出的 4-8s 物理生成/剪辑镜头数；story_clip >15s 不允许单段直提。
