# 镜头拆分决策计划

- episode: 第3集
- ok: True

| Clip | Action | N | G | R | Risk Tags | Reason |
|---|---|---:|---:|---:|---|---|
| EP03_CLIP01 | template_required | 2 | 3 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP03_CLIP02 | template_required | 0 | 0 | 4 | long_clip_8s、mouth_visible、closeup、vfx_or_asset、spectacle_large_establishing | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP03_CLIP03 | template_required | 0 | 1 | 5 | long_clip_12s、mouth_visible、closeup、vfx_or_asset、spectacle_large_establishing | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP03_CLIP04 | defer_to_composite | 1 | 2 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| EP03_CLIP05 | template_required | 0 | 1 | 5 | long_clip_12s、high_motion、mouth_visible、large_expression_span、multi_character、vfx_or_asset、spectacle_mount_ride | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP03_CLIP06 | template_required | 2 | 2 | 5 | long_clip_12s、mouth_visible、closeup、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP03_CLIP07 | template_required | 0 | 2 | 4 | long_clip_12s、mouth_visible、closeup、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP03_CLIP08 | template_required | 2 | 2 | 5 | long_clip_12s、high_motion、mouth_visible、closeup、large_expression_span、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP03_CLIP09 | template_required | 1 | 1 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP03_CLIP10 | template_required | 2 | 2 | 5 | long_clip_12s、mouth_visible、closeup、large_expression_span、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。
