# 剧情经济性审查

- episode: 第1集
- ok: True
- total_duration_sec: 50.231
- target_total_max_sec: 52.0
- potential_savings_sec: 5.876

| Clip | Dur | Class | Target | Action | Demo |
|---|---:|---|---:|---|---|
| EP01_CLIP01 | 6.237s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP02 | 7.969s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP03 | 11.609s | compact_story | 3.0-6.0s | compress_or_narrate_before_video | 改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。 |
| EP01_CLIP04 | 8.267s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP05 | 4.795s | montage_bridge | 3.0-6.0s | merge_or_montage_before_video | 改成 3-6s 蒙太奇：建立镜一闪 + 关键道具/动作特写 + 目的地落幅。 |
| EP01_CLIP06 | 7.458s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |
| EP01_CLIP07 | 3.896s | selective_detail | 5.0-8.0s | trim_to_selective_detail | 改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。 |

## Findings

- WARN EP01_CLIP03 story_clip_over_economy_target: EP01_CLIP03 当前 11.609s，分类=compact_story，建议 3-6s；compress_or_narrate_before_video。改成 3-6s：一句旁白承载信息，画面只拍能改变局势的物件/表情/动作。
- WARN EP01_CLIP04 story_clip_over_economy_target: EP01_CLIP04 当前 8.267s，分类=selective_detail，建议 5-8s；trim_to_selective_detail。改成 5-8s：建立局势 + 一个决定性细节 + 一个反应/宣判落点。

## Rules

- 默认把秒数还给战斗/动作、男女主或核心人物强情绪交流、真正反转/集尾钩。
- 解释、行进、普通反应、情报交代优先压成 2-6s，或并入相邻强戏。
- 长 story_clip 若不值得详拍，不应先拆成多个视频段烧额度；应先回 n2d-script 压缩剧情表达。
