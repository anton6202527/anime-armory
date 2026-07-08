# 镜头拆分决策计划

- episode: 第4集
- ok: True

| Clip | Dur | Action | Economy | Target | Video Shots | N | G | R | Risk Tags | Reason |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| EP04_CLIP01 | 33.811s | compress_before_video | selective_detail | 5.0-8.0s | 6 | 1 | 3 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP02 | 31.348s | split_video_shots | premium_detail | 8.0-15.0s | 6 | 2 | 2 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | story_clip 时长超过 12s，必须规划 4-8s 物理 video_shot；超过 15s 不允许作为单个付费视频段直提。 |
| EP04_CLIP03 | 27.136s | compress_before_video | montage_bridge | 3.0-6.0s | 5 | 0 | 2 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、multi_character、vfx_or_asset、spectacle_mount_ride | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP04 | 17.381s | compress_before_video | selective_detail | 5.0-8.0s | 3 | 1 | 3 | 5 | long_clip_12s、mouth_visible、closeup、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP05 | 32.081s | compress_before_video | selective_detail | 5.0-8.0s | 6 | 2 | 3 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP06 | 21.590s | compress_before_video | selective_detail | 5.0-8.0s | 4 | 1 | 3 | 5 | long_clip_12s、mouth_visible、closeup、many_named_characters、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP07 | 24.895s | compress_before_video | selective_detail | 5.0-8.0s | 5 | 1 | 3 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、many_named_characters、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP08 | 16.251s | compress_before_video | selective_detail | 5.0-8.0s | 3 | 0 | 3 | 5 | long_clip_12s、mouth_visible、closeup、many_named_characters、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP09 | 11.953s | compress_before_video | selective_detail | 5.0-8.0s |  | 0 | 3 | 4 | long_clip_8s、mouth_visible、closeup、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP10 | 12.433s | compress_before_video | selective_detail | 5.0-8.0s | 3 | 2 | 3 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP04_CLIP11 | 10.280s | template_required | premium_detail | 8.0-15.0s |  | 2 | 2 | 5 | long_clip_8s、high_motion、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset、spectacle_fight_exchange | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。Economy 来自 story_economy_audit；Video Shots 为建议拆出的 4-8s 物理生成/剪辑镜头数；story_clip >15s 不允许单段直提。
