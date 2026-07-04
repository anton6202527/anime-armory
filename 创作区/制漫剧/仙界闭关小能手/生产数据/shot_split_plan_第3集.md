# 镜头拆分决策计划

- episode: 第3集
- ok: True

| Clip | Action | N | G | R | Risk Tags | Reason |
|---|---|---:|---:|---:|---|---|
| Clip_01 | keep_single | 2 | 2 | 4 | long_clip_8s、closeup、large_expression_span、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| Clip_02 | defer_to_composite | 0 | 0 | 4 | long_clip_12s、closeup、large_expression_span、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| Clip_03 | keep_single | 0 | 1 | 3 | long_clip_8s、closeup、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| Clip_04 | defer_to_composite | 0 | 0 | 3 | long_clip_8s、closeup、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| Clip_05 | template_required | 0 | 3 | 5 | long_clip_8s、mouth_visible、closeup、large_expression_span、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| Clip_06 | template_required | 0 | 1 | 4 | long_clip_8s、mouth_visible、closeup、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| Clip_07 | keep_single | 1 | 0 | 3 | long_clip_12s、closeup、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| Clip_08 | defer_to_composite | 2 | 1 | 4 | long_clip_12s、closeup、large_expression_span、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| Clip_09 | keep_single | 0 | 0 | 3 | long_clip_8s、closeup、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| Clip_10 | keep_single | 0 | 2 | 3 | long_clip_12s、closeup、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| Clip_11 | defer_to_composite | 2 | 1 | 4 | long_clip_12s、closeup、large_expression_span、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |
| Clip_12 | keep_single | 0 | 1 | 2 | long_clip_8s、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| Clip_13 | defer_to_composite | 2 | 1 | 2 | multi_character、vfx_or_asset | 把文字、光效、证据标记、复杂同框等交给分层出图或后期合成，避免视频后端自由生成。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。
