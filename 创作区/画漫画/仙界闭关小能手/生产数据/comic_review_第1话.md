# 漫画审查报告 — 第1话

- 生成时间：2026-07-07T13:32:12
- 结论：pass
- panel 数：18
- block/warn/info：0 / 0 / 3

## 设置

- 定妆级别: 长线专门定妆+n2d级一致性
- 参考一致性策略: n2d级共享参考图+多视图+形态继承
- 年龄形态继承: 开启
- 角色一致性硬闸: 开启
- 风格锚: STYLE_XIANJIE_CINEMATIC_REALISTIC_GUOMAN
- 文字语言: 中文
- 合规用途: 内部打样

## 记录

- 已刷新风格一致性报告：生产数据/comic_style_consistency_第1话.md
- 已刷新 QA 长图预览：生产数据/qa_previews/第1话_longstrip_preview.webp
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第1话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | rights | _meta.json | 字体权利仍是 pending_before_publish | comic-review | 发布/商用前确认授权并更新 _meta.json |
| info | rights | _meta.json | 素材权利仍是 pending_before_publish | comic-review | 发布/商用前确认授权并更新 _meta.json |
| info | rights | 排版/第1话/export_manifest.json | 当前使用 system_font_draft，不能当正式发布字体授权 | comic-compose | 发布前用已授权字体重新导出，或更新字体授权记录 |

## 风格一致性

- 结论：pass
- 摘要：{"panel_count": 18, "finding_count": 0, "block_count": 0, "warn_count": 0, "info_count": 0}
