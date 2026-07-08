# 剧情经济性审查

- episode: 第5集
- ok: True
- total_duration_sec: 152.393
- target_total_max_sec: 141.0
- potential_savings_sec: 21.09

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP05_CLIP01 | 19.247s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP05_CLIP02 | 15.408s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP05_CLIP03 | 19.890s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP05_CLIP04 | 10.479s | premium_detail | 8.0-11.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP05_CLIP05 | 11.798s | premium_detail | 8.0-15.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP05_CLIP06 | 12.093s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP05_CLIP07 | 26.545s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP05_CLIP08 | 15.897s | premium_detail | 10.0-18.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |
| EP05_CLIP09 | 21.036s | premium_detail | 16.0-22.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。 |

## Findings

- WARN EP05_CLIP01 story_clip_over_economy_target: EP05_CLIP01 当前 19.247s，分类=premium_detail，建议 8-15s；keep_detail_but_split_video_shots。保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。
- WARN EP05_CLIP02 story_clip_over_economy_target: EP05_CLIP02 当前 15.408s，分类=premium_detail，建议 8-15s；keep_detail_but_split_video_shots。保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。
- WARN EP05_CLIP03 story_clip_over_economy_target: EP05_CLIP03 当前 19.89s，分类=premium_detail，建议 8-15s；keep_detail_but_split_video_shots。保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。
- WARN EP05_CLIP07 story_clip_over_economy_target: EP05_CLIP07 当前 26.545s，分类=premium_detail，建议 8-15s；keep_detail_but_split_video_shots。保留起手/接触或眼神/停顿/关键台词，拆成 4-8s video_shot，别把解释塞进动作段。

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
