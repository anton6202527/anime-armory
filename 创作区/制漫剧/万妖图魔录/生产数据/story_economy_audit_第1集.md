# 剧情经济性审查

- episode: 第1集
- ok: True
- total_duration_sec: 127.431
- target_total_max_sec: 167.0
- potential_savings_sec: 16.488

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP01_CLIP01 | 8.435s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP02 | 6.150s | compact_story | 3.0-6.0s | compress_or_narrate_before_video | 改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。 |
| EP01_CLIP03 | 7.632s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP04 | 11.028s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP05 | 8.614s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP06 | 5.439s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP07 | 13.487s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP08 | 2.400s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP09 | 5.874s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP10 | 9.188s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP11 | 9.586s | premium_detail | 8.0-15.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP12 | 6.113s | compact_story | 3.0-6.0s | compress_or_narrate_before_video | 改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。 |
| EP01_CLIP13 | 13.473s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP14 | 3.794s | compact_story | 3.0-6.0s | compress_or_narrate_before_video | 改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。 |
| EP01_CLIP15 | 6.582s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP16 | 3.074s | premium_detail | 8.0-15.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP17 | 4.369s | premium_detail | 8.0-15.0s | keep_detail | 保留起手/接触或眼神/停顿/关键台词，按动作与镜位拆 take；别把解释塞进动作段，短插入镜不必硬拉到后端最短时长。 |
| EP01_CLIP18 | 0.893s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP19 | 1.300s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |

## Findings

- WARN EP01_CLIP01 story_clip_over_economy_target: EP01_CLIP01 当前 8.435s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP01_CLIP02 story_clip_over_economy_target: EP01_CLIP02 当前 6.15s，分类=compact_story，建议 3-6s；compress_or_narrate_before_video。改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。
- WARN EP01_CLIP04 story_clip_over_economy_target: EP01_CLIP04 当前 11.028s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP01_CLIP05 story_clip_over_economy_target: EP01_CLIP05 当前 8.614s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP01_CLIP07 story_clip_over_economy_target: EP01_CLIP07 当前 13.487s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP01_CLIP10 story_clip_over_economy_target: EP01_CLIP10 当前 9.188s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。
- WARN EP01_CLIP12 story_clip_over_economy_target: EP01_CLIP12 当前 6.113s，分类=compact_story，建议 3-6s；compress_or_narrate_before_video。改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。
- WARN EP01_CLIP13 story_clip_over_economy_target: EP01_CLIP13 当前 13.473s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
