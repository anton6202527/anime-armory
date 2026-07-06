---
name: comic-compose
description: 画漫画嵌字与导出阶段。Use when lettering comic panels, placing speech bubbles, captions, narration, SFX, exporting pages or long-scroll segments, creating export_manifest.json, or composing final comic deliverables for projects under 创作区/画漫画. Triggers 漫画合成, 嵌字, 气泡, 旁白框, 拟声词, 长图, 导出漫画, export_manifest, comic-compose.
---

# comic-compose — 嵌字、长图和导出

把面板图、`layout.json` 和 `lettering.json` 合成为可审查、可发布的页面图或条漫长图分段。MVP 提供 `scripts/export_longstrip.py`：默认写导出 manifest，安装 Pillow 时可选渲染长图分段。

## 输入

- `排版/第N话/layout.json`。
- `脚本/第N话/panel_script.json`。
- `排版/第N话/lettering.json`。
- `出图/第N话/panels/P001.png` 等面板图。
- `_设置.md`：导出格式、单话分段高度、嵌字方式。

## 输出

- `排版/第N话/export_manifest.json`。
- `排版/第N话/pages/`：页漫或审查分页。
- `排版/第N话/长图/part_001.webp` 等分段长图。
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

如果已安装 Pillow，可渲染长图分段：

```bash
python3 skills/comic-compose/scripts/export_longstrip.py "创作区/画漫画/作品名" --chapter 第1话 --render
```

## 嵌字原则

文字不要烘焙在出图 prompt 里。推荐流程：

1. 面板图保持无字或空白气泡。
2. `lettering.json` 记录每条文字、气泡类型、位置、字号、阅读顺序。
3. 合成阶段用可控文字渲染，便于改错字、压缩台词、本地化和审查。
4. 字体、商用授权和目标地区发布规范在正式发布前确认。

`lettering.json` schema 见 `references/lettering_schema.md`。

## 长图策略

- 默认按 `单话分段高度` 切成多个 part，避免一张图过高。
- 每个 part 要在 `export_manifest.json` 登记 panel 顺序和尺寸。
- 缺 panel 图时也要写 manifest，并列出 `missing_panels`，方便继续生产。

## 回写进度

只有当本话必要 panel 图齐全、`lettering.json` 已确认、导出 manifest 和目标导出物都就绪时，才把 `嵌字合成` 标 `✅`。仅 manifest 就绪可写 `⏳manifest`。

## 不做什么

- 不自动替用户购买或启用字体。
- 不在缺图时伪造完成。
- 不跳过 `comic-review` 直接宣称可发布。
