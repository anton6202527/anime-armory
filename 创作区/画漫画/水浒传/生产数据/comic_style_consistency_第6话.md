# 漫画风格一致性报告 — 第6话

- 生成时间：2026-07-19T18:53:37
- 结论：warn
- panel 数：48
- block/warn/info：0 / 32 / 0

## 记录

- 跨话基准比对通过：与基准话（第1话）相似度 0.9761。

## Findings

| severity | code | panel | artifact | reason | suggested_fix |
|---|---|---|---|---|---|
| warn | panel_style_outlier | P010 | 出图/第6话/panels/P010.png | 风格指纹内聚度 0.7150 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P013 | 出图/第6话/panels/P013.png | 风格指纹内聚度 0.6565 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P018 | 出图/第6话/panels/P018.png | 风格指纹内聚度 0.7447 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P023 | 出图/第6话/panels/P023.png | 风格指纹内聚度 0.6960 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P024 | 出图/第6话/panels/P024.png | 风格指纹内聚度 0.4681 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P026 | 出图/第6话/panels/P026.png | 风格指纹内聚度 0.4121 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P029 | 出图/第6话/panels/P029.png | 风格指纹内聚度 0.5815 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P031 | 出图/第6话/panels/P031.png | 风格指纹内聚度 0.7107 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P032 | 出图/第6话/panels/P032.png | 风格指纹内聚度 0.6544 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P036 | 出图/第6话/panels/P036.png | 风格指纹内聚度 0.7207 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P040 | 出图/第6话/panels/P040.png | 风格指纹内聚度 0.6858 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P042 | 出图/第6话/panels/P042.png | 风格指纹内聚度 0.6181 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | P048 | 出图/第6话/panels/P048.png | 风格指纹内聚度 0.7203 明显低于本话中位 0.7932，疑似画风、细节密度或照片感跳变。 | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | location_color_grade_shift | P024 | 出图/第6话/panels/P024.png | 同场景“LOC_SHI_MANOR”内调色代理偏离组中位：warmth_dev=0.405, tint_dev=0.000。 | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | P026 | 出图/第6话/panels/P026.png | 同场景“LOC_SHI_MANOR”内调色代理偏离组中位：warmth_dev=0.553, tint_dev=0.041。 | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | P013 | 出图/第6话/panels/P013.png | 同场景“LOC_SHI_TRAINING_YARD”内调色代理偏离组中位：warmth_dev=0.255, tint_dev=0.024。 | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | adjacent_panel_grade_jump | P024 | 出图/第6话/panels/P024.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P023 相比冷暖/亮度跳变：warmth_jump=0.415, val_jump=0.005；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P025 | 出图/第6话/panels/P025.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P024 相比冷暖/亮度跳变：warmth_jump=0.452, val_jump=0.089；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P026 | 出图/第6话/panels/P026.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P025 相比冷暖/亮度跳变：warmth_jump=0.600, val_jump=0.053；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P027 | 出图/第6话/panels/P027.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P026 相比冷暖/亮度跳变：warmth_jump=0.623, val_jump=0.138；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P031 | 出图/第6话/panels/P031.png | 与同场景锚 LOC_SHI_MANOR 的前一格 P030 相比冷暖/亮度跳变：warmth_jump=0.126, val_jump=0.365；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P040 | 出图/第6话/panels/P040.png | 与同场景锚 LOC_SHI_TRAINING_YARD 的前一格 P039 相比冷暖/亮度跳变：warmth_jump=0.215, val_jump=0.355；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | adjacent_panel_grade_jump | P041 | 出图/第6话/panels/P041.png | 与同场景锚 LOC_SHI_TRAINING_YARD 的前一格 P040 相比冷暖/亮度跳变：warmth_jump=0.169, val_jump=0.357；疑似光位翻转或昼夜漂移。 | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | tone_value_outlier | P002 | 出图/第6话/panels/P002.png | 黑白灰量化偏离话内中位：black_ratio=0.337（中位 0.037），线宽代理 edge_density=0.1035（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P010 | 出图/第6话/panels/P010.png | 黑白灰量化偏离话内中位：black_ratio=0.3873（中位 0.037），线宽代理 edge_density=0.0959（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P017 | 出图/第6话/panels/P017.png | 黑白灰量化偏离话内中位：black_ratio=0.3099（中位 0.037），线宽代理 edge_density=0.1126（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P022 | 出图/第6话/panels/P022.png | 黑白灰量化偏离话内中位：black_ratio=0.3191（中位 0.037），线宽代理 edge_density=0.0977（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P023 | 出图/第6话/panels/P023.png | 黑白灰量化偏离话内中位：black_ratio=0.4405（中位 0.037），线宽代理 edge_density=0.0629（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P024 | 出图/第6话/panels/P024.png | 黑白灰量化偏离话内中位：black_ratio=0.2396（中位 0.037），线宽代理 edge_density=0.0565（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P031 | 出图/第6话/panels/P031.png | 黑白灰量化偏离话内中位：black_ratio=0.3345（中位 0.037），线宽代理 edge_density=0.0724（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | P040 | 出图/第6话/panels/P040.png | 黑白灰量化偏离话内中位：black_ratio=0.3793（中位 0.037），线宽代理 edge_density=0.099（中位 0.126）。疑似网点密度/黑场/线宽口径不统一。 | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style_anchor_drift |  | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8762，风格锚可能已失去约束力。 | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |

## Panel 指纹

| panel | location | cohesion | sat | val | edge | warmth | tint | gutters | frame |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| P001 | LOC_SHI_TRAINING_YARD | 0.8283 | 0.2126 | 0.5733 | 0.1343 | 0.2076 | 0.0068 | 0 | 0 |
| P002 | LOC_SHI_TRAINING_YARD | 0.7593 | 0.2426 | 0.3283 | 0.1035 | 0.2178 | 0.01 | 0 | 0 |
| P003 | LOC_SHI_MANOR | 0.811 | 0.1908 | 0.4496 | 0.1051 | 0.1812 | 0.0184 | 0 | 0 |
| P004 | LOC_SHI_MANOR | 0.793 | 0.1803 | 0.6336 | 0.1266 | 0.2111 | 0.0206 | 0 | 0 |
| P005 | LOC_SHI_MANOR | 0.8232 | 0.2146 | 0.4542 | 0.1007 | 0.1027 | 0.0247 | 0 | 0 |
| P006 | LOC_SHI_TRAINING_YARD | 0.8293 | 0.1817 | 0.423 | 0.1544 | 0.1169 | 0.0062 | 0 | 0 |
| P007 | LOC_SHI_TRAINING_YARD | 0.8214 | 0.1459 | 0.5055 | 0.1716 | 0.1568 | 0.01 | 0 | 0 |
| P008 | LOC_SHI_TRAINING_YARD | 0.819 | 0.1494 | 0.5892 | 0.1631 | 0.1647 | 0.0022 | 0 | 0 |
| P009 | LOC_SHI_TRAINING_YARD | 0.7958 | 0.2036 | 0.5671 | 0.1481 | 0.2397 | 0.0108 | 0 | 0 |
| P010 | LOC_SHI_TRAINING_YARD | 0.715 | 0.2206 | 0.2856 | 0.0959 | 0.0132 | 0.0035 | 0 | 0 |
| P011 | LOC_SHI_TRAINING_YARD | 0.7911 | 0.1688 | 0.5923 | 0.1691 | 0.1887 | 0.0083 | 0 | 0 |
| P012 | LOC_SHI_TRAINING_YARD | 0.8122 | 0.1286 | 0.5225 | 0.1749 | 0.1357 | 0.009 | 0 | 0 |
| P013 | LOC_SHI_TRAINING_YARD | 0.6565 | 0.3499 | 0.5593 | 0.1252 | 0.4314 | 0.0319 | 0 | 0 |
| P014 | LOC_SHI_TRAINING_YARD | 0.8417 | 0.174 | 0.4854 | 0.1413 | 0.2123 | 0.0041 | 0 | 0 |
| P015 | LOC_SHI_TRAINING_YARD | 0.8421 | 0.1619 | 0.5775 | 0.1695 | 0.1795 | 0.0015 | 0 | 0 |
| P016 | LOC_SHI_TRAINING_YARD | 0.8102 | 0.1844 | 0.3755 | 0.1322 | 0.1048 | -0.0015 | 0 | 0 |
| P017 | LOC_SHI_TRAINING_YARD | 0.7915 | 0.1924 | 0.3232 | 0.1126 | 0.1656 | 0.0147 | 0 | 0 |
| P018 | LOC_SHI_TRAINING_YARD | 0.7447 | 0.1405 | 0.3116 | 0.0908 | 0.0198 | 0.0338 | 0 | 0 |
| P019 | LOC_SHI_TRAINING_YARD | 0.8013 | 0.1369 | 0.5549 | 0.1618 | 0.1398 | 0.0134 | 0 | 0 |
| P020 | LOC_SHI_MANOR | 0.8074 | 0.2092 | 0.6203 | 0.1569 | 0.2589 | 0.0139 | 0 | 0 |
| P021 | LOC_SHI_TRAINING_YARD | 0.7923 | 0.2079 | 0.6038 | 0.1457 | 0.195 | 0.008 | 0 | 0 |
| P022 | LOC_SHI_TRAINING_YARD | 0.7599 | 0.2858 | 0.2938 | 0.0977 | 0.3735 | 0.0081 | 0 | 0 |
| P023 | LOC_SHI_MANOR | 0.696 | 0.2457 | 0.2714 | 0.0629 | 0.1945 | 0.0222 | 0 | 0 |
| P024 | LOC_SHI_MANOR | 0.4681 | 0.456 | 0.2768 | 0.0565 | 0.61 | 0.0176 | 0 | 0 |
| P025 | LOC_SHI_MANOR | 0.7596 | 0.2181 | 0.3656 | 0.0902 | 0.1582 | -0.0077 | 0 | 0 |
| P026 | LOC_SHI_MANOR | 0.4121 | 0.5084 | 0.3127 | 0.0664 | 0.7581 | 0.0583 | 0 | 0 |
| P027 | LOC_SHI_MANOR | 0.8343 | 0.2117 | 0.4508 | 0.1108 | 0.1352 | 0.0264 | 0 | 0 |
| P028 | LOC_SHI_MANOR | 0.8129 | 0.1949 | 0.6447 | 0.1697 | 0.2252 | 0.025 | 0 | 0 |
| P029 | LOC_SHI_MANOR | 0.5815 | 0.3279 | 0.5221 | 0.0994 | 0.3788 | 0.0259 | 0 | 0 |
| P030 | LOC_SHI_MANOR | 0.7862 | 0.2077 | 0.6464 | 0.1472 | 0.2074 | 0.0217 | 0 | 0 |
| P031 | LOC_SHI_MANOR | 0.7107 | 0.2858 | 0.2817 | 0.0724 | 0.0817 | -0.0068 | 0 | 0 |
| P032 | LOC_SHI_MANOR | 0.6544 | 0.3112 | 0.3896 | 0.0896 | 0.1661 | 0.0717 | 0 | 0 |
| P033 | LOC_SHI_MANOR | 0.7735 | 0.1853 | 0.6996 | 0.1228 | 0.1902 | 0.0117 | 0 | 0 |
| P034 | LOC_SHI_MANOR | 0.7982 | 0.1316 | 0.5986 | 0.1241 | 0.1377 | 0.0134 | 0 | 0 |
| P035 | LOC_ESCAPE_ROAD | 0.7984 | 0.188 | 0.6188 | 0.1169 | 0.1913 | 0.0147 | 0 | 0 |
| P036 | LOC_ESCAPE_ROAD | 0.7207 | 0.1227 | 0.6793 | 0.1428 | 0.1191 | 0.0108 | 0 | 0 |
| P037 | LOC_ESCAPE_ROAD | 0.7934 | 0.1505 | 0.6476 | 0.1293 | 0.1586 | 0.0068 | 0 | 0 |
| P038 | LOC_ESCAPE_ROAD | 0.8347 | 0.1854 | 0.6291 | 0.1234 | 0.2014 | 0.0183 | 0 | 0 |
| P039 | LOC_SHI_TRAINING_YARD | 0.8193 | 0.2288 | 0.5909 | 0.1489 | 0.2226 | 0.0125 | 0 | 0 |
| P040 | LOC_SHI_TRAINING_YARD | 0.6858 | 0.2428 | 0.2355 | 0.099 | 0.0079 | -0.015 | 0 | 0 |
| P041 | LOC_SHI_TRAINING_YARD | 0.798 | 0.1703 | 0.5922 | 0.1623 | 0.1769 | -0.0008 | 0 | 0 |
| P042 | LOC_SHI_MANOR | 0.6181 | 0.236 | 0.7159 | 0.1071 | 0.2759 | 0.0153 | 0 | 0 |
| P043 | LOC_SHI_MANOR | 0.8224 | 0.172 | 0.5314 | 0.1497 | 0.1877 | 0.0133 | 0 | 0 |
| P044 | LOC_SHI_MANOR | 0.7767 | 0.1794 | 0.6286 | 0.1078 | 0.2052 | 0.0081 | 0 | 0 |
| P045 | LOC_SHI_MANOR | 0.8019 | 0.198 | 0.6312 | 0.139 | 0.2098 | 0.0149 | 0 | 0 |
| P046 | LOC_SHI_ANCESTRAL_GRAVE | 0.7976 | 0.1816 | 0.6485 | 0.1447 | 0.2009 | 0.02 | 0 | 0 |
| P047 | LOC_SHI_ANCESTRAL_GRAVE | 0.7845 | 0.1695 | 0.6467 | 0.1244 | 0.1748 | 0.0144 | 0 | 0 |
| P048 | LOC_SHI_MANOR | 0.7203 | 0.2218 | 0.6277 | 0.1276 | 0.2669 | 0.0125 | 0 | 0 |
