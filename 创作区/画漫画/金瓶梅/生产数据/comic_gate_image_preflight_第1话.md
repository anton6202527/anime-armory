# 漫画 Gate — image_preflight — 第1话

- 生成时间：2026-07-18T15:12:34
- 结论：warn
- block/warn/info：0 / 18 / 1

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=1 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=1（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=8（advisory·不阻断）
- redundancy_audit: must=0 warn=1（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 39 需处理 30；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | no_climax_panel | 生产数据/comic_chapter_beat_audit_第1话.json | 未标出高潮/转折/兑现格；请人工确认节拍不是平推。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P011 台词/旁白提到「景阳冈」（registry 实体 LOC_JINGYANGGANG）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P012 画面描述提到「武松」（registry 实体 CHAR_WU_SONG），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P013 画面描述提到「武大」（registry 实体 CHAR_WU_DA），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P027 画面描述提到「武大」（registry 实体 CHAR_WU_DA），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P031 画面描述提到「武大」（registry 实体 CHAR_WU_DA），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P032 画面描述提到「武松」（registry 实体 CHAR_WU_SONG），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P039 画面描述提到「武松」（registry 实体 CHAR_WU_SONG），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P043 画面描述提到「武松」（registry 实体 CHAR_WU_SONG），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P044 画面描述提到「武松」（registry 实体 CHAR_WU_SONG），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第1话.json | P006、P009 计划了相同的 (场景=LOC_JINGYANGGANG, 角色=CHAR_WU_SONG/MON_JINGYANG_TIGER, 景别=特写)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P006 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P009·景阳冈吊睛白额虎：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P009 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·武大：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P022 多人同框主色撞色（易串脸）：CHAR_WU_DA↔CHAR_WANG_PO（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P023 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P035·武松：缺 参考预算溢出（后端 multi_character_reference_limit=4 张，裁掉必需 expression）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P037·武松：缺 参考预算溢出（后端 multi_character_reference_limit=4 张，裁掉必需 back）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
