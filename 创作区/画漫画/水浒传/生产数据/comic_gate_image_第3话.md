# 漫画 Gate — image — 第3话

- 生成时间：2026-07-18T13:22:47
- 结论：pass
- block/warn/info：0 / 0 / 26

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=3 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: dreamina_image2image; reference_image_limit=10; persistent_subject=False
- 角色注册表 v2: pass
- 角色多视图技术齐套与人审签收: pass
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=0（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 44 需处理 29；处方 SHA 已校验
- panel_variety: panels=46 近重复对=0（advisory·不阻断）
- style consistency refreshed: 生产数据/comic_style_consistency_第3话.md
- character consistency refreshed: 生产数据/comic_character_consistency_第3话.md
- vlm judge coverage: 138/138
- scene/prop consistency refreshed: 生产数据/comic_scene_prop_consistency_第3话.md

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第3话.json | 高潮候选在 93%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第3话.json | P016 台词/旁白提到「小苏学士」（registry 实体 CHAR_SU_XUESHI）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第3话.json | P020 台词/旁白提到「王都尉」（registry 实体 CHAR_WANG_DUWEI）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | mentioned_not_bound | 生产数据/comic_entity_presence_audit_第3话.json | P040 台词/旁白提到「王都尉」（registry 实体 CHAR_WANG_DUWEI）但未绑定；若仅口头提及可忽略，若要入画需补 references。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P012.png | P012 的落盘 post_qc=warn 已人审签收为误报：放大复核为空白荐书纸面、药包和天光，不是气泡/文字框；药铺重制版已无店招文字。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P020.png | P020 的落盘 post_qc=warn 已人审签收为误报：放大复核为人物手持空白荐书与街巷天光，不是烘焙气泡。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P029.png | P029 的落盘 post_qc=warn 已人审签收为误报：放大复核为宴舞长袖的计划内白色动势前景，不是气泡或文字容器。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P034.png | P034 的落盘 post_qc=warn 已人审签收为误报：放大复核为黄罗礼包与庭院亮部，不是气泡。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P036.png | P036 的落盘 post_qc=warn 已人审签收为误报：放大复核为廊下天光和石地留白，不是气泡。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P038.png | P038 的落盘 post_qc=warn 已人审签收为误报：放大复核为庭院亮空与球路负空间，不含气泡、文字框或可读字。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P039.png | P039 的落盘 post_qc=warn 已人审签收为误报：放大复核为庭院白墙、日光与铺地，不是气泡。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P040.png | P040 的落盘 post_qc=warn 已人审签收为误报：放大复核为廊柱间天光与远处无字礼盒，不是气泡。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P042.png | P042 的落盘 post_qc=warn 已人审签收为误报：放大复核为逆光庭院与石地负空间，不是气泡。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_post_qc_warn | 出图/第3话/panels/P043.png | P043 的落盘 post_qc=warn 已人审签收为误报：放大复核为殿檐天光与脚—球周围留白，不是气泡。 | review | 若该格重抽或构图变化，需要重新复核 panel_qc。 |
| info | panel_style_outlier | 出图/第3话/panels/P002.png | 风格指纹内聚度 0.4662 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P003.png | 风格指纹内聚度 0.6437 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P004.png | 风格指纹内聚度 0.7645 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P006.png | 风格指纹内聚度 0.7774 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P007.png | 风格指纹内聚度 0.7181 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P016.png | 风格指纹内聚度 0.6959 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P017.png | 风格指纹内聚度 0.7606 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P019.png | 风格指纹内聚度 0.7618 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P022.png | 风格指纹内聚度 0.7740 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | panel_style_outlier | 出图/第3话/panels/P030.png | 风格指纹内聚度 0.7716 明显低于本话中位 0.8288，疑似画风、细节密度或照片感跳变。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | style_anchor_drift | 出图/共享/style_baseline.json | 本话整体指纹与风格锚图最高相似度仅 0.8523，风格锚可能已失去约束力。 | review | 已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。 |
| info | identity_similarity_engine_degraded | 生产数据/comic_character_consistency_第3话.json | CCIP 动漫身份 embedding 不可用；VLM 三轴并排裁决已完整覆盖，已按规定完成身份轴兜底。 | review | 保留当前 VLM 裁决证据；后续环境具备 dghs-imgutils 时可补跑 CCIP。 |
