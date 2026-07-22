# 漫画 Gate — image — 第2话

- 生成时间：2026-07-22T15:17:59
- 结论：warn
- block/warn/info：0 / 32 / 1

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=2 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=3（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 16 需处理 13；处方 SHA 已校验
- panel_variety: panels=16 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第2话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第2话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第2话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第2话.json | 高潮候选在 93%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | payoff_overdue | 生产数据/comic_setup_payoff_audit_第2话.json | 伏笔「首屏异鬼铺皮执笔，读者先知危险而王生不知。」兑现话 第1话 已早于本话 第2话 但仍 open——坑该收没收=长线断供/忘坑；补收并标 done，或改 payoff_chapter/标 ongoing。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | payoff_overdue | 生产数据/comic_setup_payoff_audit_第2话.json | 伏笔「道士见王生邪气萦绕，王生仍以为求财魔法。」兑现话 第1话 已早于本话 第2话 但仍 open——坑该收没收=长线断供/忘坑；补收并标 done，或改 payoff_chapter/标 ongoing。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | payoff_overdue | 生产数据/comic_setup_payoff_audit_第2话.json | 伏笔「疯乞让陈氏吞下的浓痰停在胸间。」兑现话 第1话 已早于本话 第2话 但仍 open——坑该收没收=长线断供/忘坑；补收并标 done，或改 payoff_chapter/标 ongoing。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P003·贾母：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P004·狐兄弟：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P004·狐兄弟：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | tone_value_outlier | 出图/第2话/panels/P002.png | 黑白灰量化偏离话内中位：black_ratio=0.3751（中位 0.059），线宽代理 edge_density=0.0524（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P003.png | 黑白灰量化偏离话内中位：black_ratio=0.3565（中位 0.059），线宽代理 edge_density=0.055（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P004.png | 黑白灰量化偏离话内中位：black_ratio=0.2626（中位 0.059），线宽代理 edge_density=0.0593（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P006.png | 黑白灰量化偏离话内中位：black_ratio=0.2614（中位 0.059），线宽代理 edge_density=0.0424（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P007.png | 黑白灰量化偏离话内中位：black_ratio=0.2497（中位 0.059），线宽代理 edge_density=0.058（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | tone_value_outlier | 出图/第2话/panels/P015.png | 黑白灰量化偏离话内中位：black_ratio=0.4109（中位 0.059），线宽代理 edge_density=0.0797（中位 0.086）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.7094，风格锚可能已失去约束力。 | image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | ccip_identity_low | 出图/第2话/panels/P007.png | CHAR_JIA_CHILD CCIP 身份距离 0.2126 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） | image | 并排对比 contact sheet 与定妆图；确认脸漂则回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P007.png | CHAR_JIA_CHILD hair 指纹与参考图相似度偏低：score=0.341。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P015.png | CHAR_JIA_CHILD hair 指纹与参考图相似度偏低：score=0.294。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P006.png | CHAR_JIA_FATHER hair 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P002.png | CHAR_JIA_MOTHER hair 指纹与参考图相似度偏低：score=0.431。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第2话/panels/P004.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.491。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | ccip_identity_low | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS CCIP 身份距离 0.2107 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） | image | 并排对比 contact sheet 与定妆图；确认脸漂则回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.392。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P007.png | MON_FOX_BROTHERS hair 指纹与参考图相似度偏低：score=0.274。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第2话/panels/P015.png | MON_FOX_BROTHERS face 指纹与参考图相似度偏低：score=0.450。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P015.png | MON_FOX_BROTHERS hair 指纹与参考图相似度偏低：score=0.260。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | ccip_identity_low | 出图/第2话/panels/P007.png | MON_FOX_SERVANT CCIP 身份距离 0.2219 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） | image | 并排对比 contact sheet 与定妆图；确认脸漂则回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第2话/panels/P007.png | MON_FOX_SERVANT face 指纹与参考图相似度偏低：score=0.438。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P007.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.325。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P008.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.438。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | ccip_identity_low | 出图/第2话/panels/P015.png | MON_FOX_SERVANT CCIP 身份距离 0.196 超过同角色阈值 0.178（多人同格，全图对比结果需并排人审确认） | image | 并排对比 contact sheet 与定妆图；确认脸漂则回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第2话/panels/P015.png | MON_FOX_SERVANT face 指纹与参考图相似度偏低：score=0.462。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第2话/panels/P015.png | MON_FOX_SERVANT hair 指纹与参考图相似度偏低：score=0.281。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第2话.json | VLM 并排判定任务包已生成 57 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 用 vlm_adjudicate.py queue 出队、由多模态 agent 看图打分后 submit 回写 生产数据/comic_vlm_judge_verdicts_第2话.json；或恢复 CCIP（comicqc env）后重跑 gate。 |
