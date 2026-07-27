# 剧情经济性审查

- episode: 第3集
- ok: True
- total_duration_sec: 88.833
- target_total_max_sec: 95.0
- potential_savings_sec: 2.085

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP03_CLIP01 | 10.520s | selective_detail | 8.0-11.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP02 | 7.441s | selective_detail | 6.0-9.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP03 | 11.755s | selective_detail | 8.0-12.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP04 | 15.383s | premium_detail | 9.0-16.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP03_CLIP05 | 4.428s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP03_CLIP06 | 15.551s | premium_detail | 10.0-14.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP03_CLIP07 | 12.221s | premium_detail | 10.0-14.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP03_CLIP08 | 11.534s | selective_detail | 8.0-11.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |

## Findings

- WARN EP03_CLIP06 story_clip_over_economy_target: EP03_CLIP06 当前 15.551s，分类=premium_detail，建议 10-14s；keep_detail_but_split_video_shots。保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。
- WARN EP03_CLIP08 story_clip_over_economy_target: EP03_CLIP08 当前 11.534s，分类=selective_detail，建议 8-11s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
