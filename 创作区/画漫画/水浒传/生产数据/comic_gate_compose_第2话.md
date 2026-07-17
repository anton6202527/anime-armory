# 漫画 Gate — compose — 第2话

- 生成时间：2026-07-17T16:58:06
- 结论：warn
- block/warn/info：0 / 30 / 4

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=2 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 26 需处理 12；处方 SHA 已校验
- panel_variety: panels=42 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第2话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第2话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第2话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第2话.json | 高潮候选在 100%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | payoff_due_here | 生产数据/comic_setup_payoff_audit_第2话.json | 伏笔「伏魔碑背‘遇洪而开’，洪信误将宿命当作对权势与好奇心的许可。」计划本话（第2话）兑现——确认本话已把它收掉并标 status=done。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | panel_post_qc_warn | 出图/第2话/panels/P036.png | P036 的落盘 post_qc=warn 已人审签收为误报：原图放大复核后确认白色区域为宫观天空与室内壁面采光，不是烘焙气泡或文字容器；远景白鹤、无脸道童收拾法器的余韵语义可执行。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第2话/panels/P037.png | P037 的落盘 post_qc=warn 已人审签收为误报：原图放大复核后确认候选白色区域为侧殿自然逆光和空白墙面，不是烘焙气泡；洪信人物、服装、宫廷空间与惊疑后回望语义一致。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| warn | panel_style_outlier | 出图/第2话/panels/P004.png | 风格指纹内聚度 0.7360 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P005.png | 风格指纹内聚度 0.7069 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P006.png | 风格指纹内聚度 0.6676 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P008.png | 风格指纹内聚度 0.6214 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P009.png | 风格指纹内聚度 0.6549 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P010.png | 风格指纹内聚度 0.7094 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P013.png | 风格指纹内聚度 0.6856 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P016.png | 风格指纹内聚度 0.6813 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P017.png | 风格指纹内聚度 0.7150 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P023.png | 风格指纹内聚度 0.7252 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P034.png | 风格指纹内聚度 0.7078 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第2话/panels/P036.png | 风格指纹内聚度 0.7347 明显低于本话中位 0.7800，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | location_color_grade_shift | 出图/第2话/panels/P013.png | 同场景“伏魔殿封禁记忆层”内调色代理偏离组中位：warmth_dev=0.225, tint_dev=0.015。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | 出图/第2话/panels/P030.png | 同场景“伏魔殿封禁记忆层”内调色代理偏离组中位：warmth_dev=0.223, tint_dev=0.007。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | location_color_grade_shift | 出图/第2话/panels/P017.png | 同场景“坍塌后的伏魔殿外廊”内调色代理偏离组中位：warmth_dev=0.239, tint_dev=0.048。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | tone_value_outlier | 出图/第2话/panels/P004.png | 黑白灰量化偏离话内中位：black_ratio=0.3642（中位 0.017），线宽代理 edge_density=0.0758（中位 0.114）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P005.png | 黑白灰量化偏离话内中位：black_ratio=0.4058（中位 0.017），线宽代理 edge_density=0.0866（中位 0.114）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P006.png | 黑白灰量化偏离话内中位：black_ratio=0.4496（中位 0.017），线宽代理 edge_density=0.0616（中位 0.114）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P007.png | 黑白灰量化偏离话内中位：black_ratio=0.3799（中位 0.017），线宽代理 edge_density=0.0814（中位 0.114）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P008.png | 黑白灰量化偏离话内中位：black_ratio=0.4579（中位 0.017），线宽代理 edge_density=0.0685（中位 0.114）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P009.png | 黑白灰量化偏离话内中位：black_ratio=0.5737（中位 0.017），线宽代理 edge_density=0.0747（中位 0.114）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P010.png | 黑白灰量化偏离话内中位：black_ratio=0.4456（中位 0.017），线宽代理 edge_density=0.0682（中位 0.114）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P030.png | 黑白灰量化偏离话内中位：black_ratio=0.3463（中位 0.017），线宽代理 edge_density=0.073（中位 0.114）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8779，风格锚可能已失去约束力。 | image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P029.png | CHAR_ABBOT_SHANGQING hair 指纹与参考图相似度偏低：score=0.405。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第2话/panels/P030.png | CHAR_ABBOT_SHANGQING face 指纹与参考图相似度偏低：score=0.428。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P030.png | CHAR_ABBOT_SHANGQING hair 指纹与参考图相似度偏低：score=0.373。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_BASE 在本话出场（P002,P003,P011,P012,P018,P022,P024,P026）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_COURT_ENVOY 在本话出场（P002,P003,P011,P012,P014,P017,P018,P019）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | VFX_108_STARLIGHTS 在本话出场（P001,P006,P007,P008,P009,P010,P013,P015）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
