# 镜头拆分决策计划

- episode: 第3集
- ok: True

| Clip | Dur | Action | Economy | Target | Video Shots | N | G | R | Risk Tags | Reason |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| EP03_CLIP01 | 10.880s | compress_before_video | selective_detail | 5.0-8.0s |  | 2 | 3 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP03_CLIP02 | 11.778s | compress_before_video | compact_story | 3.0-6.0s |  | 0 | 0 | 4 | long_clip_8s、mouth_visible、closeup、vfx_or_asset、spectacle_large_establishing | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP03_CLIP03 | 24.832s | compress_before_video | selective_detail | 5.0-8.0s | 5 | 0 | 1 | 5 | long_clip_12s、mouth_visible、closeup、vfx_or_asset、spectacle_large_establishing | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP03_CLIP04 | 33.363s | compress_before_video | selective_detail | 5.0-8.0s | 6 | 1 | 2 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP03_CLIP05 | 23.557s | compress_before_video | selective_detail | 5.0-8.0s | 4 | 0 | 1 | 5 | long_clip_12s、high_motion、mouth_visible、multi_character、vfx_or_asset、spectacle_mount_ride | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP03_CLIP06 | 20.955s | compress_before_video | selective_detail | 5.0-8.0s | 4 | 2 | 2 | 5 | long_clip_12s、mouth_visible、closeup、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP03_CLIP07 | 13.998s | compress_before_video | selective_detail | 5.0-8.0s | 3 | 0 | 2 | 4 | long_clip_12s、mouth_visible、closeup、multi_character | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP03_CLIP08 | 34.492s | compress_before_video | selective_detail | 5.0-8.0s | 6 | 2 | 2 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、large_expression_span、multi_character | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP03_CLIP09 | 16.842s | split_video_shots | premium_detail | 8.0-15.0s | 3 | 1 | 1 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |
| EP03_CLIP10 | 13.060s | compress_before_video | selective_detail | 5.0-8.0s | 3 | 2 | 2 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。Economy 来自 story_economy_audit；Video Shots 为建议拆出的 4-8s 物理生成/剪辑镜头数；story_clip >15s 不允许单段直提。
