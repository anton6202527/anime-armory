# 漫画 Gate — image_preflight — 第5话

- 生成时间：2026-07-19T16:47:20
- 结论：warn
- block/warn/info：0 / 32 / 1

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=5 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=1（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=3（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 41 需处理 28；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第5话.json | 合同 ending_mode=closure_with_new_promise，末格 story_function=ending_promise；期望候选为 ['hook', 'new_promise', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第5话.json | 高潮候选在 94%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第5话.json | P003 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第5话.json | P018 画面描述提到「王进」（registry 实体 CHAR_WANG_JIN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第5话.json | P047 画面描述提到「高俅」（registry 实体 CHAR_GAO_QIU），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P005 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P011 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P012 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P013 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P014 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P019 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P020 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P021 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P022 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P027 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P028 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P029·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P029·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P029 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）、CHAR_SHI_TAIGONG↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P030·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P030·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P030 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）、CHAR_SHI_TAIGONG↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P031 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P032·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P032·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P032 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）、CHAR_SHI_TAIGONG↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P033 多人同框主色撞色（易串脸）：CHAR_WANG_MOTHER↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P038·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P038·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P038 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P047·史太公：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第5话.json | P047·史太公：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第5话.json | P047 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_SHI_TAIGONG（同主色「白」）、CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_SHI_TAIGONG↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
