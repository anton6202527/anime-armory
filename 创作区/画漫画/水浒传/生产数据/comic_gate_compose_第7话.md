# 漫画 Gate — compose — 第7话

- 生成时间：2026-07-20T12:05:31
- 结论：warn
- block/warn/info：0 / 27 / 7

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=7 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=1（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=1（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 47 需处理 29；处方 SHA 已校验
- panel_variety: panels=48 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第7话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第7话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第7话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第7话.json | 合同 ending_mode=closure_with_new_promise，末格 story_function=ending_promise；期望候选为 ['hook', 'new_promise', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第7话.json | P001 台词/旁白提到「史太公」（registry 实体 CHAR_SHI_TAIGONG）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第7话.json | P006 台词/旁白提到「朱武」（registry 实体 CHAR_ZHU_WU）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第7话.json | P006 台词/旁白提到「陈达」（registry 实体 CHAR_CHEN_DA）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第7话.json | P006 台词/旁白提到「杨春」（registry 实体 CHAR_YANG_CHUN）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第7话.json | P017 画面描述提到「史进」（registry 实体 CHAR_SHI_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P002 多人同框主色撞色（易串脸）：CHAR_SHI_JIN↔CHAR_LI_JI（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P003 多人同框主色撞色（易串脸）：CHAR_LI_JI↔CHAR_SHI_JIN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P004 多人同框主色撞色（易串脸）：CHAR_SHI_JIN↔CHAR_LI_JI（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P013 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P018 多人同框主色撞色（易串脸）：CHAR_CHEN_DA↔CHAR_ZHU_WU（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P043 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P046 多人同框主色撞色（易串脸）：CHAR_CHEN_DA↔CHAR_ZHU_WU（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P047 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第7话.json | P048 多人同框主色撞色（易串脸）：CHAR_ZHU_WU↔CHAR_CHEN_DA（同主色「红」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | panel_post_qc_warn | 出图/第7话/panels/P018.png | P018 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区来自山间雾光与白马局部，不是画面内生成的对白框或文字。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第7话/panels/P037.png | P037 的落盘 post_qc=warn 已人审签收为误报：人工复核确认两处候选白区分别来自白马与敞开寨门外的雾天亮空，不是对白框或文字。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第7话/panels/P038.png | P038 的落盘 post_qc=warn 已人审签收为误报：人工复核确认候选白区来自寨门外山雾、天空及人物高光，不是对白框或文字。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| warn | panel_style_outlier | 出图/第7话/panels/P003.png | 风格指纹内聚度 0.7696 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第7话/panels/P004.png | 风格指纹内聚度 0.7188 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第7话/panels/P005.png | 风格指纹内聚度 0.7918 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第7话/panels/P010.png | 风格指纹内聚度 0.7186 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第7话/panels/P012.png | 风格指纹内聚度 0.7602 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第7话/panels/P014.png | 风格指纹内聚度 0.7287 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第7话/panels/P039.png | 风格指纹内聚度 0.7379 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第7话/panels/P043.png | 风格指纹内聚度 0.7869 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第7话/panels/P047.png | 风格指纹内聚度 0.6293 明显低于本话中位 0.8511，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | location_color_grade_shift | 出图/第7话/panels/P047.png | 同场景“LOC_SHI_MANOR”内调色代理偏离组中位：warmth_dev=0.242, tint_dev=0.009。 | image | 人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。 |
| warn | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8371，风格锚可能已失去约束力。 | image | 并排比对锚图与本话 contact sheet；必要时更新风格锚或统一重抽。 |
| warn | hair_fingerprint_low | 出图/第7话/panels/P002.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.373。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第7话/panels/P004.png | CHAR_LI_JI hair 指纹与参考图相似度偏低：score=0.455。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第7话/panels/P047.png | CHAR_YANG_CHUN hair 指纹与参考图相似度偏低：score=0.276。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第7话.json | CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。 | review | 独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第7话.json | VLM 并排判定任务包已生成 132 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 由多模态 agent 逐条看图打分并写回 生产数据/comic_vlm_judge_verdicts_第7话.json 后重跑 gate。 |
