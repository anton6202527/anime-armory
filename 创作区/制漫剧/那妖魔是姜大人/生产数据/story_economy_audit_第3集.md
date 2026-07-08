# 剧情经济性审查

- episode: 第3集
- ok: False
- total_duration_sec: 203.757
- target_total_max_sec: 85.0
- potential_savings_sec: 118.757

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP03_CLIP01 | 10.880s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP02 | 11.778s | compact_story | 3.0-6.0s | compress_or_narrate_before_video | 改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。 |
| EP03_CLIP03 | 24.832s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP04 | 33.363s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP05 | 23.557s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP06 | 20.955s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP07 | 13.998s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP08 | 34.492s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP09 | 16.842s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP03_CLIP10 | 13.060s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |

## Findings

- WARN EP03_CLIP01 story_clip_over_economy_target: EP03_CLIP01 当前 10.88s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP03_CLIP02 story_clip_over_economy_target: EP03_CLIP02 当前 11.778s，分类=compact_story，建议 3-6s；compress_or_narrate_before_video。改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。
- BLOCK EP03_CLIP03 non_premium_story_clip_too_long: EP03_CLIP03 当前 24.832s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- BLOCK EP03_CLIP04 non_premium_story_clip_too_long: EP03_CLIP04 当前 33.363s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- BLOCK EP03_CLIP05 non_premium_story_clip_too_long: EP03_CLIP05 当前 23.557s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- BLOCK EP03_CLIP06 non_premium_story_clip_too_long: EP03_CLIP06 当前 20.955s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP03_CLIP07 story_clip_over_economy_target: EP03_CLIP07 当前 13.998s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- BLOCK EP03_CLIP08 non_premium_story_clip_too_long: EP03_CLIP08 当前 34.492s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP03_CLIP09 story_clip_over_economy_target: EP03_CLIP09 当前 16.842s，分类=premium_detail，建议 8-15s；keep_detail_but_split_video_shots。保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。
- WARN EP03_CLIP10 story_clip_over_economy_target: EP03_CLIP10 当前 13.06s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
