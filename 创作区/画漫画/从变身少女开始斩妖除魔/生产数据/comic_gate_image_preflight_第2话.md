# 漫画 Gate — image_preflight — 第2话

- 生成时间：2026-07-17T09:11:36
- 结论：warn
- block/warn/info：0 / 32 / 28

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
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=4（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 30 需处理 26；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第2话.json | 高潮候选在 93%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | payoff_due_here | 生产数据/comic_setup_payoff_audit_第2话.json | 伏笔「虎妖心口被贯穿却能复生，暗示鸣骨境妖物可觉醒天赋神通」计划本话（第2话）兑现——确认本话已把它收掉并标 status=done。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | narration_heavy_chapter | 生产数据/comic_redundancy_audit_第2话.json | 本话 19/24 个有文本格是纯旁白（79%>50%）——信息压缩靠旁白硬转=没画面化的流水账；条漫铁律是能画不说：把交代改成画面/对白/道具特写，旁白只留画面外增量。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第2话.json | P003、P018 计划了相同的 (场景=LOC_DESOLATE_WILDERN, 角色=CHAR_JIANG_YUECHU, 景别=近景)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第2话.json | P007、P026 计划了相同的 (场景=LOC_DESOLATE_WILDERN, 角色=CHAR_JIANG_YUECHU/CHAR_PEI_CHANGQING, 景别=中景)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_composition_plan | 生产数据/comic_redundancy_audit_第2话.json | P001、P002、P028 计划了相同的 (场景=LOC_DESOLATE_WILDERN, 角色=CHAR_JIANG_YUECHU/CHAR_PEI_CHANGQING, 景别=近景)——一屏多格时重复构图立刻穿帮；换景别/机位/前景遮挡或合并格。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P001·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第2话.json | P001 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P002·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第2话.json | P002 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P003·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P004·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P005·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P005 多人同框主色撞色（易串脸）：MON_TIGER_SHANSHEN↔CHAR_JIANG_YUECHU（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第2话.json | P005 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P006·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第2话.json | P006·虎山神：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P006 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P007·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P008·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P008 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第2话.json | P010·虎山神：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P010·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P010 多人同框主色撞色（易串脸）：MON_TIGER_SHANSHEN↔CHAR_JIANG_YUECHU（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P011·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P011 多人同框主色撞色（易串脸）：MON_TIGER_SHANSHEN↔CHAR_JIANG_YUECHU（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P012·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P012 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P013·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P013 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P015·虎山神：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side、back）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P015·姜月初：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side、back）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P015·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P015 多人同框主色撞色（易串脸）：MON_TIGER_SHANSHEN↔CHAR_JIANG_YUECHU（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P016·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P016 多人同框主色撞色（易串脸）：MON_TIGER_SHANSHEN↔CHAR_JIANG_YUECHU（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P017·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P018·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P020·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P020 多人同框主色撞色（易串脸）：MON_TIGER_SHANSHEN↔CHAR_JIANG_YUECHU（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | strong_emotion_expression_reference_missing | 生产数据/comic_reference_plan_第2话.json | P022·姜月初：缺 强情绪格缺对应表情参考（expression_id=EXPR_NEUTRAL；不能用中性 face 冒充） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P022·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P023·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P023 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P024·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P024 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第2话.json | P024 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P025·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第2话.json | P025 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第2话.json | P025 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P026·姜月初：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side、back）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P026·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P026·裴长青：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P026·裴长青：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P027·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P028·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第2话.json | P028 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P029·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第2话.json | P030·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P030·裴长青：缺 全身/三视图参考（远景/全身动作格·单张头肩定妆不够） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
