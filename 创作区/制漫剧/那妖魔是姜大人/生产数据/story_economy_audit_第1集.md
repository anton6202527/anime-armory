# 剧情经济性审查

- episode: 第1集
- ok: True
- total_duration_sec: 74.798
- target_total_max_sec: 85.0
- potential_savings_sec: 0.0

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP01_CLIP01 | 3.884s | selective_detail | 4.0-6.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP02 | 11.520s | premium_detail | 9.0-12.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP03 | 11.989s | premium_detail | 9.0-12.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP04 | 7.419s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP05 | 11.608s | premium_detail | 9.0-13.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP06 | 8.251s | premium_detail | 5.0-9.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP07 | 10.811s | premium_detail | 10.0-15.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP08 | 9.316s | premium_detail | 8.0-10.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
