# 漫画 Gate — image — 第1话

- 生成时间：2026-07-17T05:36:16
- 结论：block
- block/warn/info：3 / 40 / 15

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=1 block=0 warn=0
- backend adapter: native_subject_capable; reference_image_limit=10; persistent_subject=True
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=4（advisory·不阻断）
- redundancy_audit: must=0 warn=2（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 27 需处理 23；处方 SHA 已校验
- panel_variety: panels=28 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第1话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第1话.md
- vlm judge coverage: 93/93
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第1话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| block | name_approval_missing_or_stale | 排版/第1话/name_board.json | 缩略分镜/name board 审批合同 未通过：[block] _设置.md 已变化，当前缩略分镜/name board 已 stale | name | 按 缩略分镜/name board 审批合同 输出修复并重新签收后重跑 gate。 |
| block | layout_approval_missing_or_stale | 排版/第1话/layout.json | 排版审批合同 未通过：[block] name_board 的 settings SHA 已过期 [block] layout upstream settings_sha256 已过期 | layout | 按 排版审批合同 输出修复并重新签收后重跑 gate。 |
| block | finishing_contract_missing_or_stale | 出图/第1话/finishing/finishing_plan.json | 原稿收尾合同 未通过：[block] name_board 上游 SHA 已过期 | finishing | 按 原稿收尾合同 输出修复并重新签收后重跑 gate。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P005 画面描述提到「虎妖」（registry 实体 MON_TIGER_SHANSHEN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P020 画面描述提到「横刀」（registry 实体 PROP_HENGDAO_BROKEN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P025 画面描述提到「虎妖」（registry 实体 MON_TIGER_SHANSHEN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第1话.json | P026 画面描述提到「虎妖」（registry 实体 MON_TIGER_SHANSHEN），但该格 characters/references/scene_anchor 都没绑它——出图不会附其定妆参考，形态全靠模型自由发挥。确认入画则补进该格 references（或 characters），不入画则改写描述。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | narration_heavy_chapter | 生产数据/comic_redundancy_audit_第1话.json | 本话 14/25 个有文本格是纯旁白（56%>50%）——信息压缩靠旁白硬转=没画面化的流水账；条漫铁律是能画不说：把交代改成画面/对白/道具特写，旁白只留画面外增量。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | repeated_fact_mention | 生产数据/comic_redundancy_audit_第1话.json | 短语『斩杀生物』在 P021/P023/P025 复现 3 格——同一信息反复告知读者即冗余；只留首次落地处。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P004 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P011·裴长青：缺 侧脸参考（极端角度/转头格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P015 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P016 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P019 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·姜月初：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，裁掉必需 side）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·裴长青：缺 侧脸参考（极端角度/转头格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P020·虎山神：缺 参考预算溢出（后端 multi_character_reference_limit=3 张，裁掉必需 side）；拆格/升档/精选参考包 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P020 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P022 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P024·裴长青：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | same_frame_color_collision | 生产数据/comic_reference_plan_第1话.json | P024 多人同框主色撞色（易串脸）：CHAR_JIANG_YUECHU↔MON_TIGER_SHANSHEN（同主色「黑」）——用互斥发色/服装主色/配饰强分，必要时拆反打。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第1话.json | P026·裴长青：缺 侧脸参考（极端角度/转头格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | multi_character_closeup | 生产数据/comic_reference_plan_第1话.json | P028 多人近景=串脸最高发档：优先拆单人CU+反打或降景别，坚持同框须登记分区/分别出图+合成。 | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P028.png | P028 的落盘 post_qc=warn 已人审签收为误报：误报：几何连通区是黑墨冲击、暗红布带与白色速度线，画面无空白气泡或文字容器。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
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
| warn | vlm_judge_character_suspect | 出图/第1话/panels/P003.png | VLM 并排判定给出低分/存疑：verdict=suspect；P003 仅左下角失焦的灰白衣肩臂与苍白手掌入镜，无脸无发型可辨，无法确认是姜月初本人 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_character_suspect | 出图/第1话/panels/P015.png | VLM 并排判定给出低分/存疑：face=2、outfit=1、build=2；背景右侧虎怪呈普通橙黄虎纹真虎毛色、通体无灰黑鳞甲、胸口黑洞金纹不可见，与registry DNA严重不符 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_character_suspect | 出图/第1话/panels/P016.png | VLM 并排判定给出低分/存疑：verdict=suspect；左侧女子长发完全披散无高马尾束发，袍子比定妆整洁垂坠且背身看不到脸，认脸存疑 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_character_suspect | 出图/第1话/panels/P018.png | VLM 并排判定给出低分/存疑：face=2、outfit=1；虎怪变为橙黄真虎头与毛色、全身无鳞甲改穿破布裤束绳腰带，仅胸口黑洞保留，严重漂移 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_character_suspect | 出图/第1话/panels/P019.png | VLM 并排判定给出低分/存疑：face=2、outfit=1；橙黄虎头无灰黑鳞甲、下身破布裤，仅胸口黑洞存在，与虎山神DNA不符 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_character_suspect | 出图/第1话/panels/P020.png | VLM 并排判定给出低分/存疑：outfit=2；虎首人身直立且胸口有黑洞，但通体橙黄普通虎纹、身穿破布长袍，完全没有registry要求的灰黑鳞甲与金纹 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_character_suspect | 出图/第1话/panels/P022.png | VLM 并排判定给出低分/存疑：outfit=2；远景虎首人身直立、胸口黑洞清晰，但仍是破布长袍无鳞甲，毛色灰棕非定妆的灰白虎首配灰黑鳞甲 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_character_suspect | 出图/第1话/panels/P024.png | VLM 并排判定给出低分/存疑：outfit=2；直立虎人胸口黑洞在，但橙黄普通虎头、赤膊配毛皮短裙，灰黑鳞甲完全缺失 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第1话.json | CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。 | review | 独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。 |
| warn | scene_layout_outlier | 出图/第1话/panels/P021.png | P021 的布局指纹在场景锚 LOC_DESOLATE_WILDERNESS 组内离群（0.826 < 中位 0.928 - 0.1）。机位变化合法，但整格结构换掉（门窗家具错位/常驻物件消失）需要人审。 | image | 看该场景锚 contact sheet 并排比对；结构漂移则按 spatial_layout/resident_assets 重抽。 |
| warn | prop_reference_missing | 出图/共享/identity_registry.json | OUTFIT_BASE 在本话出场（P002,P003,P004,P005,P006,P007,P008,P009）但没有参考图，无法并排核对同一物。 | image | 用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。 |
| warn | vlm_judge_background_suspect | 出图/第1话/panels/P017.png | VLM 并排判定低分/存疑：layout=2；本格转为水墨意象合成画面，荒原地平线与岩壁结构完全未继承，空间连续性断裂（疑为有意的心象插页） | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_background_suspect | 出图/第1话/panels/P018.png | VLM 并排判定低分/存疑：layout=2、lighting=2；由墨色意象骤回深红实景，布局与光位无从继承，背景链路在此断开 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_prop_suspect | 出图/第1话/panels/P018.png | VLM 并排判定低分/存疑：structure=2；裴长青手中为完整修长弯刀，无断口无环首，与断横刀参考的断裂刀身结构不符 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_prop_suspect | 出图/第1话/panels/P023.png | VLM 并排判定低分/存疑：structure=2；姜月初握柄姿态合理，但刀身是弧形长弯刀且刃尖完整、护手金饰，与锚定的直刃环首断刀刃口崩缺不符 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_prop_suspect | 出图/第1话/panels/P024.png | VLM 并排判定低分/存疑：structure=2；手持弯刀完整无断口、无环首，与断横刀锚定不符（与P023同一把弯刀，批内自洽但对锚漂移） | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_prop_suspect | 出图/第1话/panels/P025.png | VLM 并排判定低分/存疑：structure=2；变成直刃但配金色分段华丽剑柄，无环首无崩口无血渍缠布，规格材质与锚定断刀不符 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_prop_suspect | 出图/第1话/panels/P026.png | VLM 并排判定低分/存疑：structure=1；双手倒持的是对称双刃宝剑（卷云鎏金剑格），完全不是单刃环首断横刀 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_prop_suspect | 出图/第1话/panels/P027.png | VLM 并排判定低分/存疑：structure=2；手中为金柄弯刀刃形完整，与锚定直刃断刀结构不符 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
| warn | vlm_judge_prop_suspect | 出图/第1话/panels/P028.png | VLM 并排判定低分/存疑：structure=1；刺下的仍是P026那柄鎏金双刃剑，非断横刀，属道具彻底替换 | image | 按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。 |
