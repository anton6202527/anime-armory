---
name: artifact-catalog
description: "仓库级作品资产索引、数据结构 doctor 与渐进迁移工具。用于生成只读 artifact_catalog.json、审计缓存/零字节/重复视图/绝对路径，以及把旧 n2d 持久时间线移出 _work。"
---

# artifact-catalog — 作品资产索引与渐进迁移

这是仓库级维护工具，不属于任何一条创作生产线。它只扫描作品目录并生成可重建索引；六条线运行时不得 import 本工具，保证每条线仍可独立分发。

## 产物

- `<作品根>/生产数据/artifact_catalog.json`：机器读取入口，记录相对路径、角色、阶段、单元、状态、体积、哈希、派生关系与是否可清理。
- `<作品根>/_meta.json`：`migrate --apply` 只补齐缺失的 `project_id / line / title`，不覆盖系列自己的业务字段。

`artifact_catalog.json` 是派生索引，不是业务真值。业务真值仍是各线 `_进度.md`、`_设置.md`、合同、事件账、签收和正式媒体。

## 标准调用

```bash
# 只读审计；不修改作品
python3 tools/artifact-catalog/scripts/catalog.py doctor <作品根>

# 原子刷新 catalog；旧 catalog 的 size/mtime 未变项会复用 SHA
python3 tools/artifact-catalog/scripts/catalog.py build <作品根> --write

# 先预览旧项目迁移计划
python3 tools/artifact-catalog/scripts/catalog.py migrate <作品根>

# 确认后执行：补最小身份、清理废弃零字节 voice 占位、迁持久 timeline/OTIO、刷新 catalog
python3 tools/artifact-catalog/scripts/catalog.py migrate <作品根> --apply
```

## 边界

- `doctor` 永远只读。
- `build --write` 只覆盖派生 catalog。
- `migrate` 默认 dry-run；只有 `--apply` 才改盘。
- 不移动业务正文、prompt、正式媒体、签收、合规文件或跨线交接副本。
- 不自动删除 `_clipcache`；缓存清理由本线自己的 cache policy 执行。
- Markdown/HTML 与同 stem JSON 成对时标记为 `role=view`，先让桌面端按 catalog 识别；旧文件不强搬，避免破坏硬编码消费者。
