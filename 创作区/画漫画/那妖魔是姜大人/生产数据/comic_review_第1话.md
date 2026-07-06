# 漫画审查报告 — 第1话

- 生成时间：2026-07-06T22:47:58
- 结论：pass
- panel 数：18
- block/warn/info：0 / 0 / 3

## 设置

- 定妆级别: 长线专门定妆
- 文字语言: 中文
- 合规用途: 自用草稿

## 记录

- 已刷新 QA 长图预览：生产数据/qa_previews/第1话_longstrip_preview.webp
- 已刷新 panel contact sheet：生产数据/panel_contact_sheet_第1话.jpg

## 问题清单

| severity | category | artifact | reason | return_to | suggested_fix |
|---|---|---|---|---|---|
| info | rights | _meta.json | 字体权利仍是 pending_before_publish | comic-review | 发布/商用前确认授权并更新 _meta.json |
| info | rights | _meta.json | 素材权利仍是 pending_before_publish | comic-review | 发布/商用前确认授权并更新 _meta.json |
| info | rights | 排版/第1话/export_manifest.json | 当前使用 system_font_draft，不能当正式发布字体授权 | comic-compose | 发布前用已授权字体重新导出，或更新字体授权记录 |
