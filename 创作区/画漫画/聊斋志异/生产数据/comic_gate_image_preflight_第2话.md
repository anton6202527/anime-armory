# 漫画 Gate — image_preflight — 第2话

- 生成时间：2026-07-27T10:21:02
- 结论：block
- block/warn/info：4 / 6 / 1

## 记录

- 开发包严格合同: pass
- 源范围/SHA/逐格 coverage 合同: pass
- continuity_audit: chapters=2 block=0 warn=0
- 缩略分镜/name board 审批合同: pass
- 排版审批合同: pass
- 原稿收尾合同: pass
- backend adapter: openai_gpt_image_project_memory; reference_image_limit=16; persistent_subject=False
- 角色注册表 v2: pass
- chapter_beat_audit: must=0 warn=0（advisory·不阻断）
- setup_payoff_ledger: must=0 warn=3（advisory·不阻断）
- reentry_context_audit: must=0 warn=0（advisory·不阻断）
- entity_presence_audit: must=0 warn=0（advisory·不阻断）
- source_fabrication_audit: must=0 warn=0（advisory·不阻断）
- redundancy_audit: must=0 warn=0（advisory·不阻断）
- subtext_audit: must=0 warn=0（advisory·不阻断）
- reference_planner: 含角色格 16 需处理 13；处方 SHA 已校验

## Findings

| severity | code | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| block | model_pack_not_signed_off | 生产数据/comic_model_pack_report.json | 角色多视图技术齐套与人审签收 未通过：_sha256": "ac07876752beca8b7dd1b0415b29808f29491a136cec84e3349866b5add05dcc",             "crop_box": []           }         }       ],       "model_pack_fingerprint": "73b3169cb60d1f972353d73a9dadf7b5061fc5dac4aa1d02740bd87463662532",       "signoff": {         "path": "生产数据/comic_model_pack_signoffs/MON_FOX_SERVANT.json",         "status": "current",         "approved_at": "2026-07-22T03:07:31+00:00",         "reviewer": "Codex制作代理"       },       "signoff_required": true,       "readiness": "ready",       "technical_block": false,       "findings": []     },     {       "kind": "comic_character_model_pack",       "version": 1,       "character_id": "MON_PAINTED_SKIN",       "asset_type": "monster",       "tier": "restricted_partial",       "required_views": [         "front"       ],       "view_evidence": [         {           "view": "front",           "path": "",           "sha256": "",           "width": 0,           "height": 0,           "source_view": "",           "derivation": {}         }       ],       "model_pack_fingerprint": "6d26b2dbe52a6da5af90d07978bacfa7396bb1be13f3c20af5337145b8ad7ed2",       "signoff": {         "path": "生产数据/comic_model_pack_signoffs/MON_PAINTED_SKIN.json",         "status": "missing",         "approved_at": "",         "reviewer": ""       },       "signoff_required": true,       "readiness": "needs_fix",       "technical_block": true,       "findings": [         {           "severity": "block",           "code": "model_pack_view_missing",           "view": "front",           "message": "缺必需视图 front"         }       ],       "montage": "生产数据/model_pack_montage/MON_PAINTED_SKIN.jpg"     }   ],   "summary": {     "assets": 10,     "characters": 7,     "monsters": 3,     "ready": 5,     "needs_approval": 4,     "needs_fix": 1   } } | identity | 按 角色多视图技术齐套与人审签收 输出修复并重新签收后重跑 gate。 |
| block | missing_character_views | 生产数据/comic_identity_report.json | 长线专门定妆未补齐：MON_PAINTED_SKIN 缺 front | identity | 补 front/three_quarter/side/back/face 后重跑 gate。 |
| info | climax_at_tail | 生产数据/comic_chapter_beat_audit_第2话.json | 高潮候选在 93%；确认中段是否有足够支撑。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | payoff_overdue | 生产数据/comic_setup_payoff_audit_第2话.json | 伏笔「首屏异鬼铺皮执笔，读者先知危险而王生不知。」兑现话 第1话 已早于本话 第2话 但仍 open——坑该收没收=长线断供/忘坑；补收并标 done，或改 payoff_chapter/标 ongoing。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | payoff_overdue | 生产数据/comic_setup_payoff_audit_第2话.json | 伏笔「道士见王生邪气萦绕，王生仍以为求财魔法。」兑现话 第1话 已早于本话 第2话 但仍 open——坑该收没收=长线断供/忘坑；补收并标 done，或改 payoff_chapter/标 ongoing。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| warn | payoff_overdue | 生产数据/comic_setup_payoff_audit_第2话.json | 伏笔「疯乞让陈氏吞下的浓痰停在胸间。」兑现话 第1话 已早于本话 第2话 但仍 open——坑该收没收=长线断供/忘坑；补收并标 done，或改 payoff_chapter/标 ongoing。 | comic-script | 按机检建议回 comic-script 修分话/分格后重跑。 |
| block | reference_plan_stale | 生产数据/comic_reference_plan_第2话.json | 已落盘处方的 inputs_fingerprint 与当前输入不一致。 | identity | 重跑 comic-image 构建参考处方和 panel_jobs。 |
| block | reference_plan_stale | 生产数据/comic_reference_plan_第2话.json | 已落盘处方的 plan_sha256 与当前输入不一致。 | identity | 重跑 comic-image 构建参考处方和 panel_jobs。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P003·贾母：缺 背身参考（背影/过肩格） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P004·狐兄弟：缺 45°/three_quarter 参考（档位或本格变化量需要） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
| warn | missing_reference | 生产数据/comic_reference_plan_第2话.json | P004·狐兄弟：缺 45°/¾ 侧脸参考（动作格主身份锚·避免 frontal 摆拍偏置） | identity | 按处方补该角色缺的视图/表情/服装参考并重建出图包。 |
