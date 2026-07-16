# 漫画 Gate — review — 第1话

- 生成时间：2026-07-16T01:33:12
- 结论：warn
- block/warn/info：0 / 23 / 51

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
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=2（advisory·不阻断）
- reference_planner: 含角色格 27 需处理 24；处方 SHA 已校验
- panel_variety: panels=28 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第1话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第1话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第1话.md
- comic-review report refreshed in review gate
- drift_report: 追踪 3 角色 · 有漂移 0（跨话汇总·advisory）

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
| info | panel_style_outlier | 出图/第1话/panels/P010.png | 风格指纹内聚度 0.8091 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P019.png | 风格指纹内聚度 0.8080 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P024.png | 风格指纹内聚度 0.7024 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P025.png | 风格指纹内聚度 0.8079 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第1话/panels/P028.png | 风格指纹内聚度 0.7415 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | location_color_grade_shift | 出图/第1话/panels/P015.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.227, tint_dev=0.058。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | location_color_grade_shift | 出图/第1话/panels/P018.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.210, tint_dev=0.052。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | location_color_grade_shift | 出图/第1话/panels/P019.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.232, tint_dev=0.089。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | location_color_grade_shift | 出图/第1话/panels/P024.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.482, tint_dev=0.215。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | location_color_grade_shift | 出图/第1话/panels/P028.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.236, tint_dev=0.040。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | adjacent_panel_grade_jump | 出图/第1话/panels/P025.png | 与同场景锚 LOC_DESOLATE_WILDERNESS 的前一格 P024 相比冷暖/亮度跳变：warmth_jump=0.502, val_jump=0.075；疑似光位翻转或昼夜漂移。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | tone_value_outlier | 出图/第1话/panels/P009.png | 黑白灰量化偏离话内中位：black_ratio=0.045（中位 0.226），线宽代理 edge_density=0.0842（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | tone_value_outlier | 出图/第1话/panels/P021.png | 黑白灰量化偏离话内中位：black_ratio=0.4285（中位 0.226），线宽代理 edge_density=0.0813（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | tone_value_outlier | 出图/第1话/panels/P028.png | 黑白灰量化偏离话内中位：black_ratio=0.3853（中位 0.226），线宽代理 edge_density=0.1412（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| warn | scene_layout_outlier | 出图/第1话/panels/P021.png | P021 的布局指纹在场景锚 LOC_DESOLATE_WILDERNESS 组内离群（0.826 < 中位 0.928 - 0.1）。机位变化合法，但整格结构换掉（门窗家具错位/常驻物件消失）需要人审。 | image | 看该场景锚 contact sheet 并排比对；结构漂移则按 spatial_layout/resident_assets 重抽。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_BASE 在本话出场（P002,P003,P004,P005,P006,P007,P008,P009）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| info | image | 出图/第1话/panels/P028.png | 疑似烘焙空白气泡已人审签收为误报：误报：几何连通区是黑墨冲击、暗红布带与白色速度线，画面无空白气泡或文字容器。 | comic-review | 若该格重抽或构图变化，需要重新复核原始图空白气泡机检 |
| info | style | 出图/第1话/panels/P010.png | 风格指纹内聚度 0.8091 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P019.png | 风格指纹内聚度 0.8080 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P024.png | 风格指纹内聚度 0.7024 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P025.png | 风格指纹内聚度 0.8079 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P028.png | 风格指纹内聚度 0.7415 明显低于本话中位 0.8502，疑似画风、细节密度或照片感跳变。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P015.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.227, tint_dev=0.058。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P018.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.210, tint_dev=0.052。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P019.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.232, tint_dev=0.089。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P024.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.482, tint_dev=0.215。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P028.png | 同场景“尸骸荒野”内调色代理偏离组中位：warmth_dev=0.236, tint_dev=0.040。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P025.png | 与同场景锚 LOC_DESOLATE_WILDERNESS 的前一格 P024 相比冷暖/亮度跳变：warmth_jump=0.502, val_jump=0.075；疑似光位翻转或昼夜漂移。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P009.png | 黑白灰量化偏离话内中位：black_ratio=0.045（中位 0.226），线宽代理 edge_density=0.0842（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P021.png | 黑白灰量化偏离话内中位：black_ratio=0.4285（中位 0.226），线宽代理 edge_density=0.0813（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style | 出图/第1话/panels/P028.png | 黑白灰量化偏离话内中位：black_ratio=0.3853（中位 0.226），线宽代理 edge_density=0.1412（中位 0.083）。疑似网点密度/黑场/线宽口径不统一。 | comic-review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
