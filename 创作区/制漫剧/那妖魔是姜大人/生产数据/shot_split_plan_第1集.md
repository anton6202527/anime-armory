# 镜头拆分决策计划

- episode: 第1集
- ok: True

| Clip | Dur | Action | Economy | Target | Video Shots | N | G | R | Risk Tags | Reason |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| EP01_CLIP01 | 3.884s | split_video_shots | selective_detail | 4.0-6.0s |  | 2 | 2 | 4 | mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP02 | 11.520s | split_video_shots | premium_detail | 9.0-12.0s |  | 0 | 2 | 5 | long_clip_8s、high_motion、mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP03 | 11.989s | split_video_shots | premium_detail | 9.0-12.0s |  | 0 | 1 | 4 | long_clip_8s、mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP04 | 7.419s | split_video_shots | selective_detail | 5.0-8.0s |  | 0 | 1 | 3 | mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP05 | 11.608s | split_video_shots | premium_detail | 9.0-13.0s |  | 2 | 2 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP06 | 8.251s | compress_before_video | selective_detail | 5.0-7.0s |  | 2 | 1 | 5 | long_clip_8s、high_motion、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset、spectacle_fight_exchange | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP07 | 10.811s | split_video_shots | premium_detail | 10.0-15.0s |  | 2 | 1 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP08 | 9.316s | split_video_shots | premium_detail | 8.0-10.0s | 3 | 2 | 1 | 5 | long_clip_8s、high_motion、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset、spectacle_fight_exchange | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。Economy 来自 story_economy_audit；Video Shots 先按明确景别/机位切换拆物理 take，连续长 take 再适配后端窗口；story_clip >15s 不允许未拆直提。
