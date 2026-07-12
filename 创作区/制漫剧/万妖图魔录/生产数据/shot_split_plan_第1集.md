# 镜头拆分决策计划

- episode: 第1集
- ok: True

| Clip | Dur | Action | Economy | Target | Video Shots | N | G | R | Risk Tags | Reason |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| EP01_CLIP01 | 8.435s | compress_before_video | selective_detail | 5.0-8.0s |  | 3 | 3 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP02 | 6.150s | compress_before_video | compact_story | 3.0-6.0s |  | 0 | 2 | 3 | mouth_visible、closeup、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP03 | 7.632s | split_video_shots | selective_detail | 5.0-8.0s |  | 0 | 1 | 3 | mouth_visible、closeup、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP04 | 11.028s | compress_before_video | selective_detail | 5.0-8.0s |  | 1 | 1 | 4 | long_clip_8s、mouth_visible、closeup、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP05 | 8.614s | compress_before_video | selective_detail | 5.0-8.0s |  | 1 | 1 | 5 | long_clip_8s、high_motion、mouth_visible、closeup、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP06 | 5.439s | split_video_shots | selective_detail | 5.0-8.0s |  | 2 | 1 | 4 | high_motion、mouth_visible、closeup、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP07 | 13.487s | compress_before_video | selective_detail | 5.0-8.0s | 3 | 0 | 1 | 5 | long_clip_12s、mouth_visible、closeup、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP08 | 2.400s | template_required | selective_detail | 5.0-8.0s |  | 0 | 0 | 4 | high_motion、mouth_visible、closeup、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP09 | 5.874s | split_video_shots | selective_detail | 5.0-8.0s |  | 2 | 2 | 3 | mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP10 | 9.188s | compress_before_video | selective_detail | 5.0-8.0s |  | 0 | 2 | 4 | long_clip_8s、mouth_visible、closeup、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP11 | 9.586s | split_video_shots | premium_detail | 8.0-15.0s |  | 2 | 2 | 5 | long_clip_8s、high_motion、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset、spectacle_fight_exchange | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP12 | 6.113s | compress_before_video | compact_story | 3.0-6.0s |  | 0 | 0 | 3 | mouth_visible、closeup、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP13 | 13.473s | compress_before_video | selective_detail | 5.0-8.0s | 3 | 2 | 1 | 4 | long_clip_12s、mouth_visible、closeup、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP01_CLIP14 | 3.794s | defer_to_composite | compact_story | 3.0-6.0s |  | 0 | 0 | 3 | mouth_visible、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| EP01_CLIP15 | 6.582s | split_video_shots | selective_detail | 5.0-8.0s |  | 1 | 1 | 3 | mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP16 | 3.074s | split_video_shots | premium_detail | 8.0-15.0s |  | 0 | 0 | 3 | mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP17 | 4.369s | split_video_shots | premium_detail | 8.0-15.0s |  | 2 | 1 | 5 | high_motion、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset、spectacle_fight_exchange | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP01_CLIP18 | 0.893s | defer_to_composite | selective_detail | 5.0-8.0s |  | 0 | 1 | 3 | mouth_visible、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| EP01_CLIP19 | 1.300s | defer_to_composite | selective_detail | 5.0-8.0s |  | 0 | 1 | 3 | mouth_visible、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。Economy 来自 story_economy_audit；Video Shots 先按明确景别/机位切换拆物理 take，连续长 take 再适配后端窗口；story_clip >15s 不允许未拆直提。
