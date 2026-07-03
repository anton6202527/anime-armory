# 剧本质量交接合同

- episode: 第1集
- status: block
- blocks: 41
- warnings: 17
- clips: 25

## 可签收字段

- core_attraction: -
- first_3s_visual_hook: visual_hook 黑暗杂役大殿里，瘦小少年被粗壮班头威胁审问，周围笑影压近。 hook_type 危机 content_proposition 观众要知道这个少年为什么被仙门嘲笑，以及他会不会得到机会。 onscreen_text 五行灵根，竟被仙门当场笑成费钱废物？ muted_safe_proof 关声也能从黑暗大殿、压迫站位、少年低头和烧屏短字读
- retention_promise_ledger: 3
- audience_question_ledger: 6
- performance_cues: 0

## Clip 戏剧功能

| Clip | Dramatic Function | Audience Effect | Spectacle Function |
|---|---|---|---|
| EP01_CLIP01 | - | - | - |
| EP01_CLIP02 | - | - | - |
| EP01_CLIP03 | - | - | - |
| EP01_CLIP04 | - | - | - |
| EP01_CLIP05 | - | - | - |
| EP01_CLIP06 | - | - | - |
| EP01_CLIP07 | - | - | - |
| EP01_CLIP08 | - | - | - |
| EP01_CLIP09 | - | - | - |
| EP01_CLIP10 | - | - | - |
| EP01_CLIP11 | - | - | - |
| EP01_CLIP12 | - | - | - |
| EP01_CLIP13 | - | - | - |
| EP01_CLIP14 | - | - | - |
| EP01_CLIP15 | - | - | - |
| EP01_CLIP16 | - | - | - |
| EP01_CLIP17 | - | - | - |
| EP01_CLIP18 | - | - | - |
| EP01_CLIP19 | - | - | - |
| EP01_CLIP20 | - | - | - |
| EP01_CLIP21 | - | - | - |
| EP01_CLIP22 | - | - | - |
| EP01_CLIP23 | - | - | - |
| EP01_CLIP24 | - | - | - |
| EP01_CLIP25 | - | - | - |

## Findings

| Severity | Code | Clip | Message |
|---|---|---|---|
| block | core_attraction_missing | - | storyboard 缺本集核心看点/core_attraction；无法签收这一集到底卖什么。 |
| block | first_3s_promise_missing | - | first_3s_visual_hook 缺内容承诺/观众问题字段。 |
| warn | first_3s_silent_readable_missing | - | first_3s_visual_hook 建议写 muted_readable/silent_readable，保证无声滑屏也能读懂。 |
| warn | retention_ledger_row_weak | - | retention_promise_ledger 第 3 项缺 promise/question 或 payoff/status。 |
| block | clip_dramatic_function_missing | EP01_CLIP01 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP01 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | clip_dramatic_function_missing | EP01_CLIP02 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP02 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP03 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP03 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP04 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP04 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP05 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP05 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | spectacle_story_function_missing | EP01_CLIP05 | 高动态/奇观 Clip 缺 spectacle_story_function；奇观必须服务剧情，不能只写酷炫动作。 |
| block | clip_dramatic_function_missing | EP01_CLIP06 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP06 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP07 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP07 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | clip_dramatic_function_missing | EP01_CLIP08 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP08 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | clip_dramatic_function_missing | EP01_CLIP09 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP09 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP10 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP10 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP11 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP11 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | clip_dramatic_function_missing | EP01_CLIP12 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP12 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | spectacle_story_function_missing | EP01_CLIP12 | 高动态/奇观 Clip 缺 spectacle_story_function；奇观必须服务剧情，不能只写酷炫动作。 |
| block | clip_dramatic_function_missing | EP01_CLIP13 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP13 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | spectacle_story_function_missing | EP01_CLIP13 | 高动态/奇观 Clip 缺 spectacle_story_function；奇观必须服务剧情，不能只写酷炫动作。 |
| block | clip_dramatic_function_missing | EP01_CLIP14 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP14 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP15 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP15 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP16 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP16 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP17 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP17 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | clip_dramatic_function_missing | EP01_CLIP18 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP18 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP19 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP19 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP20 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP20 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | clip_dramatic_function_missing | EP01_CLIP21 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP21 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP22 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP22 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | clip_dramatic_function_missing | EP01_CLIP23 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP23 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | clip_dramatic_function_missing | EP01_CLIP24 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| warn | clip_audience_effect_missing | EP01_CLIP24 | 普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。 |
| block | clip_dramatic_function_missing | EP01_CLIP25 | Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。 |
| block | key_clip_audience_effect_missing | EP01_CLIP25 | 关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。 |
| block | adaptation_triage_missing | - | 缺 adaptation_triage.json；小说取舍没有有账改编，不能把上游改写交给下游。 |
