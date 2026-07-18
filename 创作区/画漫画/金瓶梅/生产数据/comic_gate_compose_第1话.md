# 漫画 Gate — compose — 第1话

- 生成时间：2026-07-18T16:55:08
- 结论：warn
- block/warn/info：0 / 44 / 13

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
- panel_variety: panels=44 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第1话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第1话.md
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第1话.md

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
| info | panel_post_qc_warn | 出图/第1话/panels/P001.png | P001 的落盘 post_qc=warn 已人审签收为误报：放大复核为空间中的白色剑光与雨线，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P011.png | P011 的落盘 post_qc=warn 已人审签收为误报：放大复核为天空、街面和轿中自然亮部，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P015.png | P015 的落盘 post_qc=warn 已人审签收为误报：空白候选来自衣袖、窗沿与纸张底色，不是气泡；纸面伪字纹理由后续嵌字前清理单独处理。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P017.png | P017 的落盘 post_qc=warn 已人审签收为误报：放大复核为窗外日光、墙面和蒸汽留白，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P021.png | P021 的落盘 post_qc=warn 已人审签收为误报：放大复核为逆光天空与街面高光，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P023.png | P023 的落盘 post_qc=warn 已人审签收为误报：放大复核为袖口、墙面和雪景亮部，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P025.png | P025 的落盘 post_qc=warn 已人审签收为误报：放大复核为瓷器、雪地与蒸汽亮部，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P031.png | P031 的落盘 post_qc=warn 已人审签收为误报：放大复核为雪街、衣袖与远景雾光，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P034.png | P034 的落盘 post_qc=warn 已人审签收为误报：放大复核为瓷器、袖口、蒸汽与雪地亮部，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P039.png | P039 的落盘 post_qc=warn 已人审签收为误报：放大复核为白袖、蒸饼布和火光，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P041.png | P041 的落盘 post_qc=warn 已人审签收为误报：放大复核为室内墙面与下层雪路；中间黑横线是脚本要求的双层时间蒙太奇分隔，不是气泡。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第1话/panels/P043.png | P043 的落盘 post_qc=warn 已人审签收为误报：放大复核为雪地、鞋面和衣袖亮部，不是气泡或文字框。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| warn | internal_panel_gutters | 出图/第1话/panels/P028.png | 检测到疑似内部分栏/拼贴 gutter，单个漫画 panel 被模型画成多面板。 | image | 补强单一连续画面约束并 force 重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P001.png | 风格指纹内聚度 0.4869 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P002.png | 风格指纹内聚度 0.7471 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P003.png | 风格指纹内聚度 0.7848 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P005.png | 风格指纹内聚度 0.7772 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P012.png | 风格指纹内聚度 0.7902 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P013.png | 风格指纹内聚度 0.7923 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | panel_style_outlier | 出图/第1话/panels/P031.png | 风格指纹内聚度 0.8012 明显低于本话中位 0.8436，疑似画风、细节密度或照片感跳变。 | image | 与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。 |
| warn | adjacent_panel_grade_jump | 出图/第1话/panels/P028.png | 与同场景锚 LOC_WU_HOME 的前一格 P027 相比冷暖/亮度跳变：warmth_jump=0.438, val_jump=0.033；疑似光位翻转或昼夜漂移。 | image | 并排两格人审；非剧情光效则按场景锚 lighting_anchor 重抽该格。 |
| warn | tone_value_outlier | 出图/第1话/panels/P001.png | 黑白灰量化偏离话内中位：black_ratio=0.4259（中位 0.045），线宽代理 edge_density=0.0947（中位 0.131）。疑似网点密度/黑场/线宽口径不统一。 | image | 对照 finishing_plan 的 tone/black/ink 计划人审；口径确实漂了则统一收尾契约后重抽。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P014.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.444。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P029.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.368。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P036.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.445。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P039.png | CHAR_PAN_JINLIAN hair 指纹与参考图相似度偏低：score=0.346。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第1话/panels/P039.png | CHAR_WU_DA face 指纹与参考图相似度偏低：score=0.486。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P039.png | CHAR_WU_DA hair 指纹与参考图相似度偏低：score=0.335。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | face_fingerprint_low | 出图/第1话/panels/P040.png | CHAR_WU_DA face 指纹与参考图相似度偏低：score=0.367。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P040.png | CHAR_WU_DA hair 指纹与参考图相似度偏低：score=0.318。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P003.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.414。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P005.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.441。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P029.png | CHAR_WU_SONG hair 指纹与参考图相似度偏低：score=0.448。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P006.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.386。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P008.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.410。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | hair_fingerprint_low | 出图/第1话/panels/P009.png | MON_JINGYANG_TIGER hair 指纹与参考图相似度偏低：score=0.385。这是色彩分布代理，需并排人审。 | image | 查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。 |
| warn | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第1话.json | CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。 | review | 独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。 |
| warn | vlm_judge_unadjudicated | 生产数据/comic_vlm_judge_tasks_第1话.json | VLM 并排判定任务包已生成 147 条但 0 条裁决——角色/生物身份、背景、道具三轴机检空转，画错生物形态这类漂移不会被拦。 | review | 由多模态 agent 逐条看图打分并写回 生产数据/comic_vlm_judge_verdicts_第1话.json 后重跑 gate。 |
