# 漫画 Gate — image_preflight — 第1话

- 生成时间：2026-07-15T02:41:22
- 结论：warn
- block/warn/info：0 / 21 / 22

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=1 block=0 warn=0
- ネーム审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=2（advisory·不阻断）
- reference_planner: 含角色格 28 需处理 24；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| warn | narration_heavy_chapter | 生产数据/comic_redundancy_audit_第1话.json | 本话 14/25 个有文本格是纯旁白（56%>50%）——信息压缩靠旁白硬转=没画面化的流水账；条漫铁律是能画不说：把交代改成画面/对白/道具特写，旁白只留画面外增量。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_fact_mention | 生产数据/comic_redundancy_audit_第1话.json | 短语『斩杀生物』在 P021/P023/P025 复现 3 格——同一信息反复告知读者即冗余；只留首次落地处。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P004·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P004 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P005·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P006·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P007·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P008·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P009·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P010·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P011·姜月初：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P011·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P011·裴长青：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P012·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P013·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P014·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P015·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P015 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P016·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P016 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P019·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P019 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·姜月初：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P020·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·裴长青：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·虎山神：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P020 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P022·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P022 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P023·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P024·姜月初：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side、back）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P024·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P024·裴长青：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P024·裴长青：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P024·虎山神：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side、back）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P024 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P025·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P026·姜月初：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，已丢 side）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P026·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P026·裴长青：缺 侧脸参考（极端角度/转头/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P027·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | escalation_suggested | 生产数据/comic_reference_plan_第1话.json | P028·姜月初：弱后端×核心长线角×大变化格：建议升档——补该角色专门定妆多视图（front/¾/side/back/face + 表情库），或换支持持久主体的后端（可灵/Seedream 主体库）按 ID 引用；漫画线不内置 LoRA，坚持一致性可在本线外训练后把产出图登记为 registry 参考，仍走共享参考流程。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P028 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
