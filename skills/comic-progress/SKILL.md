---
name: comic-progress
description: 画漫画进度仪表盘与下一步建议。Use when the user asks current status, next step, checklist, or progress for comic projects under 创作区/画漫画. It scans _进度.md read-only and routes to comic-script, comic-layout, comic-image, comic-compose, or comic-review without modifying files. Triggers 漫画进度, 画漫画进度, 下一步, 到哪了, 查进度, comic-progress.
---

# comic-progress — 画漫画进度扫描

只读扫描 `创作区/画漫画/` 下的漫画项目，汇总每话前沿并给下一步 skill。它不写文件、不出图、不导出。

## 怎么跑

扫描全部：

```bash
python3 skills/comic-progress/scripts/scan.py
```

扫描指定项目：

```bash
python3 skills/comic-progress/scripts/scan.py "创作区/画漫画/作品名"
```

JSON 输出：

```bash
python3 skills/comic-progress/scripts/scan.py "创作区/画漫画/作品名" --json
```

## 输出解读

阶段路由：

| `_进度.md` 列 | 下一步 skill |
|---|---|
| 源本/企划 | `comic-script` |
| 漫画脚本 | `comic-script` |
| 页面排版 | `comic-layout` |
| 出图包 | `comic-image` |
| 出图 | `comic-image` |
| 嵌字合成 | `comic-compose` |
| 审查 | `comic-review` |

如果下一步是出图、覆盖导出或正式发布前审查，转述时提醒用户确认模型/渠道、费用、覆盖范围和权利状态。

## 不做什么

- 不回写 `_进度.md`。
- 不替用户确认付费或覆盖动作。
- 不扫描其它生产线目录。
