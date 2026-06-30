# 镜头拆分决策计划

- episode: 第1集
- ok: True

| Clip | Action | N | G | R | Risk Tags | Reason |
|---|---|---:|---:|---:|---|---|
| EP01_CLIP01 | template_required | 1 | 2 | 3 | long_clip_8s、mouth_visible、closeup、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP02 | template_required | 1 | 2 | 3 | long_clip_8s、mouth_visible、closeup、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP03 | template_required | 0 | 2 | 3 | long_clip_8s、mouth_visible、closeup、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP04 | template_required | 0 | 2 | 3 | long_clip_8s、mouth_visible、closeup、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP05 | template_required | 0 | 0 | 4 | long_clip_8s、mouth_visible、closeup、many_named_characters | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP06 | template_required | 0 | 0 | 4 | long_clip_8s、mouth_visible、closeup、many_named_characters | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP07 | template_required | 0 | 1 | 4 | long_clip_8s、mouth_visible、closeup、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP08 | template_required | 0 | 1 | 4 | long_clip_8s、mouth_visible、closeup、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP09 | defer_to_composite | 0 | 0 | 3 | long_clip_8s、mouth_visible、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| EP01_CLIP10 | defer_to_composite | 0 | 0 | 3 | long_clip_8s、mouth_visible、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| EP01_CLIP11 | defer_to_composite | 0 | 0 | 4 | long_clip_12s、mouth_visible、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| EP01_CLIP12 | defer_to_composite | 2 | 1 | 3 | mouth_visible、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。
