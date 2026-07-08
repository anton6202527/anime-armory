---
name: comic-compose
description: 画漫画嵌字与导出阶段。Use when lettering comic panels, placing speech bubbles, captions, narration, SFX, carrying drawn SFX metadata from finishing_plan.json, exporting pages or long-scroll segments, creating export_manifest.json, or composing final comic deliverables for projects under 创作区/画漫画. Triggers 漫画合成, 嵌字, 气泡, 旁白框, 拟声词, 手绘拟声词, 长图, 导出漫画, export_manifest, comic-compose.
---

# comic-compose — 嵌字、长图和导出

把面板图、`layout.json` 和 `lettering.json` 合成为可审查、可发布的页面图或条漫长图。`scripts/export_longstrip.py` 默认写导出 manifest，安装 Pillow 时可渲染单张长图，并按 `_设置.md` 的 `文字语言` 把中文、英文或中英双语文字嵌进后期绘制的不规则对白气泡、旁白容器或 SFX 区域。

## 输入

- `排版/第N话/layout.json`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/lettering.json`。
- 可选 `出图/第N话/finishing/finishing_plan.json`：拟声词是否作为传统手绘 lettering 元素融入画面。
- `出图/第N话/panels/P001.png` 等面板图。
- `生产数据/comic_identity_report_第N话.json/md`：若本话存在角色/资产 references，应先由 `comic-identity` 确认无缺失引用和无待重抽格。
- `_设置.md`：导出格式、单话分段高度、文字语言、嵌字方式。`单话分段高度: 0` 表示不分段，`文字语言` 默认中文。

## 输出

- `排版/第N话/export_manifest.json`。
- `排版/第N话/pages/`：按 `layout.json` 渲染的页漫或审查分页；超出 WebP 单边上限时自动落 PNG。
- `排版/第N话/长图/longstrip.webp` 或 `longstrip.png`；显式设置分段高度时输出 `part_001.webp/png` 等分段长图。
- `_进度.md`：导出就绪后把 `嵌字合成` 标为 `✅`，并勾选本话页面图、长图和 `export_manifest.json` 导出清单。

## 怎么跑

已有 `panel_script.json` 和 `layout.json` 后，可先生成 `lettering.json` 草案：

```bash
python3 skills/comic-compose/scripts/build_lettering.py "创作区/画漫画/作品名" --chapter 第1话
```

再生成 manifest，不要求 Pillow：


```bash
python3 skills/comic-compose/scripts/export_longstrip.py "创作区/画漫画/作品名" --chapter 第1话
```

如果已安装 Pillow，可按 layout 渲染页面图和长图：

```bash
python3 skills/comic-compose/scripts/export_longstrip.py "创作区/画漫画/作品名" --chapter 第1话 --render --write-progress
```

渲染时默认读取 `排版/第N话/lettering.json`，用系统中文字体做草稿嵌字，并在 `export_manifest.json` 里记录 `font_status=system_font_draft`、`text_language`、`target_platform`、`platform_profile`、`text_layout_qc`、`lettering_rendered=true`、`bilingual_lettering` 与空槽清理统计。正式发布前需要确认字体授权，或用 `--font path/to/font.ttf` 指定已授权字体。如目标平台限制图片高度，可传 `--max-height 12000` 或在 `_设置.md` 写对应高度来导出分段。`--formats webp+png` 会优先输出 WebP，遇到超高长图超过 WebP 单边限制时自动落 PNG 并写入 manifest。RTL 或需词典断行的文字会被 `text_layout_qc` 阻断当前 Pillow 草稿渲染，需改用人工/专业排版 renderer。长条图太高不便逐字检查时，加 `--qc-slots` 输出 `生产数据/qa_previews/第N话_lettering_slots.jpg`，manifest 会记录 `lettering_slot_qc` 路径和缺失槽位。

## 嵌字原则

文字不要烘焙在出图 prompt 里。推荐流程：

1. 面板图保持无字、无烘焙气泡，只预留低细节留白。
2. `lettering.json` 记录每条文字、气泡类型、位置、字号、阅读顺序；生成草案时会优先读取 `dialogue[].text_target` / `narration_target`，保留 `text_source` 便于追溯；`文字语言=中文` 时只渲中文；需要英文或双语时写 `text_en`，英文自动按词换行。拟声词可继承 finishing plan 的 `drawn_sfx` 元数据。
3. 合成阶段绘制最终不规则对白气泡/旁白容器并渲染文字；不要在不规则气泡里再叠一个矩形文字框。
4. 没有文字的槽位不画气泡；旧图里烘焙的空白气泡应回 `comic-image` 重出或在审查中标返修。
5. 字体、商用授权和目标地区发布规范在正式发布前确认。

`drawn_sfx` 只允许拟声词作为画面节奏元素；对白、旁白和系统正文仍不应烘焙进 raw panel。

若用户发现“空白气泡没有文字”，先说明这是当前阶段正确状态；本 skill 会从 `panel_script.json` 生成 `lettering.json` 并在导出时嵌字。若用户发现“人物换了一个人”，不要继续合成，先回 `comic-identity` 补共享参考并重抽受影响面板。

`lettering.json` schema 见 `references/lettering_schema.md`。

## 长图策略

- 默认导出单张 `longstrip.webp`，便于 App 内审阅和直接交付；若单张高度超过 WebP 能力上限，则按 `导出格式` 自动改用 `longstrip.png`。
- 只有显式设置 `单话分段高度` 为正数或传 `--max-height` 时，才切成多个 part，避免目标平台不接受超高图片；发布候选/商用导出还会按 `目标平台` profile 检查宽度、格式、文件大小和规格证据新鲜度。
- 每个导出物都要在 `export_manifest.json` 登记 panel 顺序和尺寸。
- 缺 panel 图时也要写 manifest，并列出 `missing_panels`，方便继续生产。

## 回写进度

只有当本话必要 panel 图齐全、`lettering.json` 已确认、导出 manifest 和目标导出物都就绪时，才把 `嵌字合成` 标 `✅`。仅 manifest 就绪可写 `⏳manifest`。

## 不做什么

- 不自动替用户购买或启用字体。
- 不在缺图时伪造完成。
- 不把角色漂移问题藏进长图导出；一致性先走 `comic-identity`。
- 不跳过 `comic-review` 直接宣称可发布。
