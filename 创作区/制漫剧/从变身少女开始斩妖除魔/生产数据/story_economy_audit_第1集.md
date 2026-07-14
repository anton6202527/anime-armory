# 剧情经济性审查

- episode: 第1集
- ok: True
- total_duration_sec: 129.846
- target_total_max_sec: 145.0
- potential_savings_sec: 0.0

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP01_CLIP01 | 5.140s | selective_detail | 4.0-6.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP02 | 10.747s | premium_detail | 9.0-12.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP03 | 10.726s | premium_detail | 9.0-12.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP04 | 7.703s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP05 | 11.890s | premium_detail | 9.0-13.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP06 | 5.925s | selective_detail | 5.0-7.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP07 | 13.101s | premium_detail | 10.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP08 | 8.588s | premium_detail | 8.0-10.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP09 | 9.760s | premium_detail | 8.0-11.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP10 | 7.150s | premium_detail | 7.0-9.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP11 | 14.641s | premium_detail | 12.0-15.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP12 | 11.642s | premium_detail | 9.0-13.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP13 | 12.833s | premium_detail | 10.0-14.0s | keep_detail_but_split_video_shots | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
