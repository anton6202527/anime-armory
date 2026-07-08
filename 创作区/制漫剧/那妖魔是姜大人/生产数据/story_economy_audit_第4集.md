# 剧情经济性审查

- episode: 第4集
- ok: False
- total_duration_sec: 239.159
- target_total_max_sec: 100.0
- potential_savings_sec: 143.879

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP04_CLIP01 | 33.811s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP04_CLIP02 | 31.348s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP04_CLIP03 | 27.136s | montage_bridge | 3.0-6.0s | merge_or_montage_before_video | 改成 3-6s 蒙太奇：建立镜一闪 + 关键道具/动作特写 + 目的地落幅。 |
| EP04_CLIP04 | 17.381s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP04_CLIP05 | 32.081s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP04_CLIP06 | 21.590s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP04_CLIP07 | 24.895s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP04_CLIP08 | 16.251s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP04_CLIP09 | 11.953s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP04_CLIP10 | 12.433s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP04_CLIP11 | 10.280s | premium_detail | 8.0-15.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |

## Findings

- BLOCK EP04_CLIP01 non_premium_story_clip_too_long: EP04_CLIP01 当前 33.811s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP04_CLIP02 story_clip_over_economy_target: EP04_CLIP02 当前 31.348s，分类=premium_detail，建议 8-15s；keep_detail_but_split_video_shots。保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。
- BLOCK EP04_CLIP03 non_premium_story_clip_too_long: EP04_CLIP03 当前 27.136s，分类=montage_bridge，建议 3-6s；merge_or_montage_before_video。改成 3-6s 蒙太奇：建立镜一闪 + 关键道具/动作特写 + 目的地落幅。
- BLOCK EP04_CLIP04 non_premium_story_clip_too_long: EP04_CLIP04 当前 17.381s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- BLOCK EP04_CLIP05 non_premium_story_clip_too_long: EP04_CLIP05 当前 32.081s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- BLOCK EP04_CLIP06 non_premium_story_clip_too_long: EP04_CLIP06 当前 21.59s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- BLOCK EP04_CLIP07 non_premium_story_clip_too_long: EP04_CLIP07 当前 24.895s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- BLOCK EP04_CLIP08 non_premium_story_clip_too_long: EP04_CLIP08 当前 16.251s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP04_CLIP09 story_clip_over_economy_target: EP04_CLIP09 当前 11.953s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP04_CLIP10 story_clip_over_economy_target: EP04_CLIP10 当前 12.433s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
