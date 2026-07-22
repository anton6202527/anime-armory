# 镜头拆分决策计划

- episode: 第2集
- ok: False

| Clip | Dur | Action | Economy | Target | Video Shots | N | G | R | Risk Tags | Reason |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| EP02_CLIP01 | 12.606s | split_video_shots | premium_detail | 8.0-15.0s | 3 | 1 | 1 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP02_CLIP02 | 12.076s | split_video_shots | premium_detail | 8.0-15.0s | 3 | 0 | 2 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP02_CLIP03 | 7.390s | split_video_shots | premium_detail | 8.0-15.0s |  | 2 | 1 | 5 | high_motion、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset、spectacle_fight_exchange | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP02_CLIP04 | 5.270s | template_required | compact_story | 3.0-6.0s |  | 1 | 0 | 3 | mouth_visible、closeup、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP02_CLIP05 | 9.207s | compress_before_video | selective_detail | 5.0-8.0s |  | 2 | 1 | 4 | long_clip_8s、mouth_visible、closeup、large_expression_span、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP02_CLIP06 | 10.520s | compress_before_video | compact_story | 3.0-6.0s |  | 0 | 0 | 3 | long_clip_8s、mouth_visible、closeup、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |
| EP02_CLIP07 | 10.645s | split_video_shots | premium_detail | 8.0-15.0s |  | 1 | 1 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP02_CLIP08 | 4.213s | split_video_shots | selective_detail | 5.0-8.0s |  | 0 | 1 | 3 | mouth_visible、closeup、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。Economy 来自 story_economy_audit；Video Shots 先按明确景别/机位切换拆物理 take，连续长 take 再适配后端窗口；story_clip >15s 不允许未拆直提。
