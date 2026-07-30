# 漫画 Gate — image_preflight — 第1话

- 生成时间：2026-07-30T20:17:02
- 结论：block
- block/warn/info：1 / 9 / 0

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=1 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=1（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=0（advisory·不阻断）
- source_fabrication_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=2（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 16 需处理 13；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| block | generation_recipe_mixed | 出图/第1话/prompt/panel_jobs.json | 同一话记录了多个生图模型/渠道：GPT Image 2/Codex CLI；GPT Image 2/内置 imagegen | image | 统一模型和渠道后重建 job 包并重抽受影响格。 |
| warn | ending_mode_mismatch | 生产数据/comic_chapter_beat_audit_第1话.json | 合同 ending_mode=closure_with_new_promise，末格 story_function=theme_handoff；期望候选为 ['hook', 'new_promise', 'resolution']。这是编辑复核提示，不是硬闸。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | narration_heavy_chapter | 生产数据/comic_redundancy_audit_第1话.json | 本话 7/12 个有文本格是纯旁白（58%>50%）——信息压缩靠旁白硬转=没画面化的流水账；条漫铁律是能画不说：把交代改成画面/对白/道具特写，旁白只留画面外增量。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第1话.json | P004、P007、P010 计划了相同的 (场景=LOC_JINGYANG_RIDGE, 角色=CHAR_WUSONG/MON_TIGER, 景别=近景)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P004 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P007 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P010 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P013·景阳冈猛虎：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P016·武大：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P016 多人同框主色撞色（易串脸）：CHAR_WUDA↔CHAR_PANJINLIAN（同主色「白」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
