# 镜头拆分决策计划

- episode: 第3集
- ok: True

| Clip | Dur | Action | Economy | Target | Video Shots | N | G | R | Risk Tags | Reason |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| EP03_CLIP01 | 10.520s | split_video_shots | selective_detail | 8.0-11.0s |  | 2 | 2 | 4 | long_clip_8s、mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP03_CLIP02 | 7.441s | single_take_multishot | selective_detail | 6.0-9.0s |  | 0 | 0 | 3 | mouth_visible、closeup、vfx_or_asset | 一次多镜生成：内部镜位由 multishot-native 后端一次生成（Seedance/Kling 多镜叙事口径），不拆独立付费 take。来源可为 storyboard 显式 take_policy，或低风险纯镜位覆盖镜的默认自动合并（single_take_source=auto_low_risk_editorial）。后端不支持或跨度超窗时由出视频阶段回落 edit_cut 拆 take；奇观/大表情/高风险/需锚帧链镜不自动合并。 |
| EP03_CLIP03 | 11.755s | single_take_multishot | selective_detail | 8.0-12.0s |  | 0 | 2 | 3 | long_clip_8s、mouth_visible、closeup、vfx_or_asset | 一次多镜生成：内部镜位由 multishot-native 后端一次生成（Seedance/Kling 多镜叙事口径），不拆独立付费 take。来源可为 storyboard 显式 take_policy，或低风险纯镜位覆盖镜的默认自动合并（single_take_source=auto_low_risk_editorial）。后端不支持或跨度超窗时由出视频阶段回落 edit_cut 拆 take；奇观/大表情/高风险/需锚帧链镜不自动合并。 |
| EP03_CLIP04 | 15.383s | split_video_shots | premium_detail | 9.0-16.0s | 3 | 0 | 2 | 4 | long_clip_12s、mouth_visible、closeup、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP03_CLIP05 | 4.428s | single_take_multishot | selective_detail | 5.0-8.0s |  | 0 | 1 | 3 | mouth_visible、multi_character、vfx_or_asset | 一次多镜生成：内部镜位由 multishot-native 后端一次生成（Seedance/Kling 多镜叙事口径），不拆独立付费 take。来源可为 storyboard 显式 take_policy，或低风险纯镜位覆盖镜的默认自动合并（single_take_source=auto_low_risk_editorial）。后端不支持或跨度超窗时由出视频阶段回落 edit_cut 拆 take；奇观/大表情/高风险/需锚帧链镜不自动合并。 |
| EP03_CLIP06 | 15.551s | split_video_shots | premium_detail | 10.0-14.0s | 3 | 0 | 2 | 5 | long_clip_12s、mouth_visible、closeup、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP03_CLIP07 | 12.221s | split_video_shots | premium_detail | 10.0-14.0s | 3 | 0 | 1 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 按 storyboard 镜位切换规划独立物理 take；连续长镜再按后端窗口拆段。后端最短档位只决定多生成后裁尾，不反向拉长剪辑节拍。 |
| EP03_CLIP08 | 11.534s | compress_before_video | selective_detail | 8.0-11.0s |  | 2 | 1 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 剧情经济性超预算且不属于战斗/强情绪详拍：先回编剧压缩、合并、旁白带过或改成蒙太奇，再决定是否拆 video_shot。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。Economy 来自 story_economy_audit；Video Shots 先按明确景别/机位切换拆物理 take，连续长 take 再适配后端窗口；story_clip >15s 不允许未拆直提。
