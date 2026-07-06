---
name: comic-compose
description: 画漫画嵌字与导出阶段。Use when lettering comic panels, placing speech bubbles, captions, narration, SFX, exporting pages or long-scroll segments, creating export_manifest.json, or composing final comic deliverables for projects under 创作区/画漫画. Triggers 漫画合成, 嵌字, 气泡, 旁白框, 拟声词, 长图, 导出漫画, export_manifest, comic-compose.
---

# comic-compose — 嵌字、长图和导出

把面板图、`layout.json` 和 `lettering.json` 合成为可审查、可发布的页面图或条漫长图。`scripts/export_longstrip.py` 默认写导出 manifest，安装 Pillow 时可渲染单张长图并把文字嵌进对应气泡/旁白框/SFX 区域。

## 输入

- `排版/第N话/layout.json`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/lettering.json`。
- `出图/第N话/panels/P001.png` 等面板图。
- `生产数据/comic_identity_report_第N话.json/md`：若本话存在角色/资产 references，应先由 `comic-identity` 确认无缺失引用和无待重抽格。
- `_设置.md`：导出格式、单话分段高度、嵌字方式。`单话分段高度: 0` 表示不分段。

## 输出

- `排版/第N话/export_manifest.json`。
- `排版/第N话/pages/`：页漫或审查分页。
- `排版/第N话/长图/longstrip.webp`；显式设置分段高度时输出 `part_001.webp` 等分段长图。
- `_进度.md`：导出就绪后把 `嵌字合成` 标为 `✅`。

## 怎么跑

已有 `panel_script.json` 和 `layout.json` 后，可先生成 `lettering.json` 草案：

```bash
python3 skills/comic-compose/scripts/build_lettering.py "创作区/画漫画/作品名" --chapter 第1话
```

再生成 manifest，不要求 Pillow：


```bash
python3 skills/comic-compose/scripts/export_longstrip.py "创作区/画漫画/作品名" --chapter 第1话
```

如果已安装 Pillow，可渲染长图：

```bash
python3 skills/comic-compose/scripts/export_longstrip.py "创作区/画漫画/作品名" --chapter 第1话 --render
```

渲染时默认读取 `排版/第N话/lettering.json`，用系统中文字体做草稿嵌字，并在 `export_manifest.json` 里记录 `font_status=system_font_draft` 与 `lettering_rendered=true`。正式发布前需要确认字体授权，或用 `--font path/to/font.ttf` 指定已授权字体。如目标平台限制图片高度，可传 `--max-height 12000` 或在 `_设置.md` 写对应高度来导出分段。

## 嵌字原则

文字不要烘焙在出图 prompt 里。推荐流程：

1. 面板图保持无字或空白气泡。
2. `lettering.json` 记录每条文字、气泡类型、位置、字号、阅读顺序。
3. 合成阶段用可控文字渲染，便于改错字、压缩台词、本地化和审查。
4. 字体、商用授权和目标地区发布规范在正式发布前确认。

若用户发现“空白气泡没有文字”，先说明这是当前阶段正确状态；本 skill 会从 `panel_script.json` 生成 `lettering.json` 并在导出时嵌字。若用户发现“人物换了一个人”，不要继续合成，先回 `comic-identity` 补共享参考并重抽受影响面板。

`lettering.json` schema 见 `references/lettering_schema.md`。

## 长图策略

- 默认导出单张 `longstrip.webp`，便于 App 内审阅和直接交付。
- 只有显式设置 `单话分段高度` 为正数或传 `--max-height` 时，才切成多个 part，避免目标平台不接受超高图片。
- 每个导出物都要在 `export_manifest.json` 登记 panel 顺序和尺寸。
- 缺 panel 图时也要写 manifest，并列出 `missing_panels`，方便继续生产。

## 回写进度

只有当本话必要 panel 图齐全、`lettering.json` 已确认、导出 manifest 和目标导出物都就绪时，才把 `嵌字合成` 标 `✅`。仅 manifest 就绪可写 `⏳manifest`。

## 不做什么

- 不自动替用户购买或启用字体。
- 不在缺图时伪造完成。
- 不把角色漂移问题藏进长图导出；一致性先走 `comic-identity`。
- 不跳过 `comic-review` 直接宣称可发布。
