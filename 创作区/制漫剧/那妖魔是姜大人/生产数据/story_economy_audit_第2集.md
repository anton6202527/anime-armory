# 剧情经济性审查

- episode: 第2集
- ok: True
- total_duration_sec: 71.927
- target_total_max_sec: 88.0
- potential_savings_sec: 5.727

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP02_CLIP01 | 12.606s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP02_CLIP02 | 12.076s | premium_detail | 8.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP02_CLIP03 | 7.390s | premium_detail | 8.0-15.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP02_CLIP04 | 5.270s | compact_story | 3.0-6.0s | compress_or_narrate_before_video | 改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。 |
| EP02_CLIP05 | 9.207s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP02_CLIP06 | 10.520s | compact_story | 3.0-6.0s | compress_or_narrate_before_video | 改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。 |
| EP02_CLIP07 | 10.645s | premium_detail | 8.0-15.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP02_CLIP08 | 4.213s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |

## Findings

- WARN EP02_CLIP05 story_clip_over_economy_target: EP02_CLIP05 当前 9.207s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP02_CLIP06 story_clip_over_economy_target: EP02_CLIP06 当前 10.52s，分类=compact_story，建议 3-6s；compress_or_narrate_before_video。改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
