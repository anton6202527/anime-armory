# 漫画 Gate — image_preflight — 第6话

- 生成时间：2026-07-19T17:32:14
- 结论：warn
- block/warn/info：0 / 12 / 1

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=6 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=2（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=1（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 48 需处理 31；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第6话.json | 合同 ending_mode=closure_with_new_promise，末格 story_function=ending_promise；期望候选为 ['hook', 'new_promise', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | climax_too_early | 生产数据/comic_chapter_beat_audit_第6话.json | 最后一个高潮候选在 45%；按格序估算可能偏早，需在缩略分镜/name board 阶段结合页面/滚动几何复核。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第6话.json | P026 画面描述提到「高俅」（registry 实体 CHAR_GAO_QIU），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第6话.json | P045 台词/旁白提到「史太公」（registry 实体 CHAR_SHI_TAIGONG）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P003 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P005 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P029 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_SHI_TAIGONG（同主色「白」）、CHAR_WANG_MOTHER↔CHAR_SHI_TAIGONG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P030 多人同框主色撞色（易串脸）：CHAR_SHI_TAIGONG↔CHAR_WANG_JIN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P033 多人同框主色撞色（易串脸）：CHAR_WANG_MOTHER↔CHAR_SHI_TAIGONG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P034 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）、CHAR_WANG_JIN↔CHAR_SHI_TAIGONG（同主色「白」）、CHAR_WANG_MOTHER↔CHAR_SHI_TAIGONG（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P035 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P037 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第6话.json | P038 多人同框主色撞色（易串脸）：CHAR_WANG_JIN↔CHAR_WANG_MOTHER（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
