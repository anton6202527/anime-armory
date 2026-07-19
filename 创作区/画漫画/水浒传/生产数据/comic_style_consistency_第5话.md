# 漫画风格一致性报告 — 第5话

- 生成时间：2026-07-19T16:59:05
- 结论：warn
- panel 数：48
- block/warn/info：0 / 24 / 0

## 记录

- 跨话基准比对通过：与基准话（第1话）相似度 0.9744。

## Findings

| severity | code | panel | artifact | reason | suggested_fix |
|---|---|---|---|---|---|
| warn | panel_style_outlier | P004 | 出图/第5话/panels/P004.png | 风格指纹内聚度 0.6576 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P007 | 出图/第5话/panels/P007.png | 风格指纹内聚度 0.6881 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P012 | 出图/第5话/panels/P012.png | 风格指纹内聚度 0.6000 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P014 | 出图/第5话/panels/P014.png | 风格指纹内聚度 0.7082 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P022 | 出图/第5话/panels/P022.png | 风格指纹内聚度 0.5620 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P026 | 出图/第5话/panels/P026.png | 风格指纹内聚度 0.6948 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P027 | 出图/第5话/panels/P027.png | 风格指纹内聚度 0.6739 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P031 | 出图/第5话/panels/P031.png | 风格指纹内聚度 0.7124 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P034 | 出图/第5话/panels/P034.png | 风格指纹内聚度 0.5653 明显低于本话中位 0.7690，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | location_color_grade_shift | P034 | 出图/第5话/panels/P034.png | 同场景“LOC_SHI_TRAINING_YARD”内调色代理偏离组中位：warmth_dev=0.542, tint_dev=0.043。 | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | P012 | 出图/第5话/panels/P012.png | 同场景“LOC_WANG_JIN_HOME”内调色代理偏离组中位：warmth_dev=0.429, tint_dev=0.044。 | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | adjacent_panel_grade_jump | P004 | 出图/第5话/panels/P004.png | 与同场景锚 LOC_WANG_JIN_HOME 的前一格 P003 相比冷暖/亮度跳变：warmth_jump=0.158, val_jump=0.353；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P005 | 出图/第5话/panels/P005.png | 与同场景锚 LOC_WANG_JIN_HOME 的前一格 P004 相比冷暖/亮度跳变：warmth_jump=0.129, val_jump=0.352；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P023 | 出图/第5话/panels/P023.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P022 相比冷暖/亮度跳变：warmth_jump=0.075, val_jump=0.419；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P035 | 出图/第5话/panels/P035.png | 与同场景锚 LOC_SHI_TRAINING_YARD 的前一格 P034 相比冷暖/亮度跳变：warmth_jump=0.626, val_jump=0.312；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | tone_value_outlier | P002 | 出图/第5话/panels/P002.png | 黑白灰量化偏离话内中位：black_ratio=0.3556（中位 0.029），线宽代理 edge_density=0.1029（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P004 | 出图/第5话/panels/P004.png | 黑白灰量化偏离话内中位：black_ratio=0.3496（中位 0.029），线宽代理 edge_density=0.0674（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P012 | 出图/第5话/panels/P012.png | 黑白灰量化偏离话内中位：black_ratio=0.3136（中位 0.029），线宽代理 edge_density=0.0547（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P022 | 出图/第5话/panels/P022.png | 黑白灰量化偏离话内中位：black_ratio=0.3304（中位 0.029），线宽代理 edge_density=0.0753（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P034 | 出图/第5话/panels/P034.png | 黑白灰量化偏离话内中位：black_ratio=0.2195（中位 0.029），线宽代理 edge_density=0.0647（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P036 | 出图/第5话/panels/P036.png | 黑白灰量化偏离话内中位：black_ratio=0.3457（中位 0.029），线宽代理 edge_density=0.1169（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P044 | 出图/第5话/panels/P044.png | 黑白灰量化偏离话内中位：black_ratio=0.2594（中位 0.029），线宽代理 edge_density=0.116（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P046 | 出图/第5话/panels/P046.png | 黑白灰量化偏离话内中位：black_ratio=0.3711（中位 0.029），线宽代理 edge_density=0.1142（中位 0.116）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style_anchor_drift |  | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8779，风格锚可能已失去约束力。 | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |

## Panel 指纹

| panel | location | cohesion | sat | val | edge | warmth | tint | gutters | frame |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P001 | LOC_WANG_JIN_HOME | 0.8236 | 0.1437 | 0.4973 | 0.1211 | 0.1356 | 0.0291 | 0 | 0 |
| P002 | LOC_WANG_JIN_HOME | 0.7654 | 0.1708 | 0.2962 | 0.1029 | 0.1315 | 0.0247 | 0 | 0 |
| P003 | LOC_WANG_JIN_HOME | 0.8189 | 0.1539 | 0.553 | 0.1482 | 0.1783 | 0.0263 | 0 | 0 |
| P004 | LOC_WANG_JIN_HOME | 0.6576 | 0.2533 | 0.1999 | 0.0674 | 0.0205 | 0.0218 | 0 | 0 |
| P005 | LOC_WANG_JIN_HOME | 0.7936 | 0.147 | 0.5517 | 0.1205 | 0.1499 | 0.0039 | 0 | 0 |
| P006 | LOC_WANG_JIN_HOME | 0.7713 | 0.1404 | 0.3983 | 0.0815 | 0.1663 | 0.0157 | 0 | 0 |
| P007 | LOC_WANG_JIN_HOME | 0.6881 | 0.1717 | 0.67 | 0.0941 | 0.1857 | 0.0142 | 0 | 0 |
| P008 | LOC_WANG_JIN_HOME | 0.7357 | 0.1601 | 0.336 | 0.0934 | 0.11 | 0.0018 | 0 | 0 |
| P009 | LOC_WANG_JIN_HOME | 0.7977 | 0.1891 | 0.4014 | 0.0848 | 0.0821 | 0.0229 | 0 | 0 |
| P010 | LOC_WANG_JIN_HOME | 0.7993 | 0.1922 | 0.4335 | 0.1023 | 0.1912 | 0.006 | 0 | 0 |
| P011 | LOC_WANG_JIN_HOME | 0.7449 | 0.1683 | 0.2777 | 0.0867 | -0.0356 | -0.0089 | 0 | 0 |
| P012 | LOC_WANG_JIN_HOME | 0.6 | 0.279 | 0.2182 | 0.0547 | -0.2934 | 0.0595 | 0 | 0 |
| P013 | LOC_ESCAPE_ROAD | 0.736 | 0.1538 | 0.6824 | 0.0984 | 0.1539 | 0.0106 | 0 | 0 |
| P014 | LOC_ESCAPE_ROAD | 0.7082 | 0.1152 | 0.7368 | 0.0943 | 0.1176 | 0.0036 | 0 | 0 |
| P015 | LOC_YUE_TEMPLE | 0.8237 | 0.2163 | 0.5722 | 0.1737 | 0.231 | 0.011 | 0 | 0 |
| P016 | LOC_WANG_JIN_HOME | 0.7847 | 0.2252 | 0.5264 | 0.1027 | 0.2319 | 0.0153 | 0 | 0 |
| P017 | LOC_DIANSHUAI_HALL | 0.7675 | 0.3564 | 0.5194 | 0.1393 | 0.3941 | -0.0911 | 0 | 0 |
| P018 | LOC_DIANSHUAI_HALL | 0.7847 | 0.3036 | 0.5143 | 0.1202 | 0.3233 | -0.0306 | 0 | 0 |
| P019 | LOC_ESCAPE_ROAD | 0.7352 | 0.1056 | 0.6983 | 0.105 | 0.0985 | 0.0068 | 0 | 0 |
| P020 | LOC_ESCAPE_ROAD | 0.7544 | 0.1169 | 0.6835 | 0.1147 | 0.1003 | 0.0034 | 0 | 0 |
| P021 | LOC_ESCAPE_ROAD | 0.806 | 0.1604 | 0.6203 | 0.0969 | 0.1668 | -0.0027 | 0 | 0 |
| P022 | LOC_SHI_MANOR | 0.562 | 0.3236 | 0.3223 | 0.0753 | 0.3137 | 0.0304 | 0 | 0 |
| P023 | LOC_SHI_MANOR | 0.7384 | 0.2108 | 0.7412 | 0.1367 | 0.239 | 0.0281 | 0 | 0 |
| P024 | LOC_SHI_MANOR | 0.7774 | 0.2084 | 0.6618 | 0.1255 | 0.2415 | 0.0305 | 0 | 0 |
| P025 | LOC_SHI_MANOR | 0.7565 | 0.2129 | 0.7316 | 0.1488 | 0.235 | 0.0245 | 0 | 0 |
| P026 | LOC_SHI_MANOR | 0.6948 | 0.2142 | 0.7684 | 0.137 | 0.2374 | 0.0228 | 0 | 0 |
| P027 | LOC_SHI_MANOR | 0.6739 | 0.2265 | 0.6563 | 0.1371 | 0.2581 | 0.0269 | 0 | 0 |
| P028 | LOC_SHI_MANOR | 0.7329 | 0.2051 | 0.6365 | 0.1383 | 0.227 | 0.0213 | 0 | 0 |
| P029 | LOC_SHI_MANOR | 0.7578 | 0.1848 | 0.6078 | 0.1104 | 0.1873 | 0.0072 | 0 | 0 |
| P030 | LOC_SHI_MANOR | 0.8122 | 0.2044 | 0.4771 | 0.1058 | 0.2025 | 0.0075 | 0 | 0 |
| P031 | LOC_SHI_MANOR | 0.7124 | 0.1792 | 0.6822 | 0.0966 | 0.1901 | 0.0115 | 0 | 0 |
| P032 | LOC_SHI_MANOR | 0.7704 | 0.1715 | 0.6771 | 0.166 | 0.1883 | 0.0134 | 0 | 0 |
| P033 | LOC_SHI_MANOR | 0.7575 | 0.2429 | 0.5667 | 0.1161 | 0.2727 | 0.0093 | 0 | 0 |
| P034 | LOC_SHI_TRAINING_YARD | 0.5653 | 0.3899 | 0.2505 | 0.0647 | -0.4139 | 0.052 | 0 | 0 |
| P035 | LOC_SHI_TRAINING_YARD | 0.8129 | 0.1856 | 0.5627 | 0.1635 | 0.2119 | 0.0082 | 0 | 0 |
| P036 | LOC_SHI_TRAINING_YARD | 0.7574 | 0.248 | 0.2879 | 0.1169 | 0.1519 | 0.006 | 0 | 0 |
| P037 | LOC_SHI_TRAINING_YARD | 0.7467 | 0.1159 | 0.6174 | 0.1619 | 0.1036 | 0.0061 | 0 | 0 |
| P038 | LOC_SHI_TRAINING_YARD | 0.8127 | 0.1411 | 0.5634 | 0.1592 | 0.1417 | 0.0054 | 0 | 0 |
| P039 | LOC_SHI_TRAINING_YARD | 0.8197 | 0.1849 | 0.5267 | 0.1558 | 0.2183 | 0.0107 | 0 | 0 |
| P040 | LOC_SHI_TRAINING_YARD | 0.7893 | 0.1307 | 0.5159 | 0.1498 | 0.1288 | 0.01 | 0 | 0 |
| P041 | LOC_SHI_TRAINING_YARD | 0.8211 | 0.2093 | 0.6382 | 0.1372 | 0.218 | 0.0172 | 0 | 0 |
| P042 | LOC_SHI_TRAINING_YARD | 0.8167 | 0.1606 | 0.3732 | 0.134 | 0.1042 | 0.0131 | 0 | 0 |
| P043 | LOC_SHI_TRAINING_YARD | 0.8001 | 0.1951 | 0.4142 | 0.1222 | 0.0977 | 0.0074 | 0 | 0 |
| P044 | LOC_SHI_TRAINING_YARD | 0.7809 | 0.1807 | 0.356 | 0.116 | 0.0734 | 0.0036 | 0 | 0 |
| P045 | LOC_SHI_TRAINING_YARD | 0.7832 | 0.1282 | 0.6041 | 0.1499 | 0.1265 | 0.009 | 0 | 0 |
| P046 | LOC_SHI_TRAINING_YARD | 0.762 | 0.2209 | 0.3529 | 0.1142 | 0.0728 | 0.0105 | 0 | 0 |
| P047 | LOC_SHI_MANOR | 0.7861 | 0.2174 | 0.3922 | 0.0992 | 0.2632 | 0.0156 | 0 | 0 |
| P048 | LOC_SHI_TRAINING_YARD | 0.7997 | 0.1365 | 0.6045 | 0.1464 | 0.1351 | 0.0053 | 0 | 0 |
