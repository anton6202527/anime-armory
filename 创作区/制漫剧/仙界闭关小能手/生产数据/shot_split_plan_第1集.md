# 镜头拆分决策计划

- episode: 第1集
- ok: True

| Clip | Action | N | G | R | Risk Tags | Reason |
|---|---|---:|---:|---:|---|---|
| EP01_CLIP01 | template_required | 1 | 2 | 4 | long_clip_12s、mouth_visible、closeup、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP02 | template_required | 0 | 2 | 4 | long_clip_12s、mouth_visible、closeup、multi_character | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP03 | keep_single | 0 | 0 | 2 | long_clip_12s | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| EP01_CLIP04 | template_required | 0 | 1 | 4 | long_clip_12s、closeup、multi_character、vfx_or_asset | 复杂动作、多人、奇观或证据链必须使用 template/template_contract；缺失时先补，已存在时保持合同并让下游继承。 |
| EP01_CLIP05 | keep_single | 0 | 0 | 3 | long_clip_12s、closeup、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| EP01_CLIP06 | keep_single | 0 | 0 | 3 | long_clip_12s、closeup、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |
| EP01_CLIP07 | keep_single | 2 | 1 | 2 | closeup、vfx_or_asset | 低风险或已有足够合同/锚点，保留单镜头，后续只继承现有连续性契约。 |

N=叙事权重，G=分镜语法拆分需求，R=生成风险桶。
