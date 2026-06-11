---
name: progress
description: 智能进度分发中心（Smart Progress Dispatcher）。统一的进度查询与更新入口。根据你当前工作目录的上下文（写小说/、制漫剧/、写歌/、制MV/），自动把进度查询路由到对应产线的专属进度工具（如 n2d-progress、novel-craft 的 progress.py 等）。Use when asked to 查进度, 看进度, 更新进度, 下一步做什么, progress. Triggers 进度, 查进度, progress, progress dispatcher.
---

# progress — 智能进度分发中心

不需要再记复杂的工具路径。作为一个智能路由层，`progress` 会根据你所在的目录上下文，自动调用对应产线的底层进度脚本。

## 用法

你可以直接对我说：“查一下现在的进度”或“下一步该干什么”。

如果你需要人工调用：
```bash
python3 skills/progress/scripts/dispatch.py [作品根目录]
```

## 支持的自动路由

| 目录上下文 | 路由到哪条产线 | 底层调用的工具 |
|---|---|---|
| `写小说/<书名>` | **novel** (小说) | `skills/novel-craft/scripts/progress.py` |
| `制漫剧/<剧名>` | **n2d** (漫剧) | `skills/n2d-progress/scan.py` |
| `写歌/<曲名>` | **song** (歌曲) | `skills/song-craft/scripts/progress.py` (如有) |
| `制MV/<曲名>` | **mv** (MV) | `skills/mv-craft/scripts/progress.py` (如有) |

## 架构优势

这套工具实现了**“大模型入口级智能分发（Option 2）”**：
- **用户心智统一**：不论你现在是在做视频、写书还是写歌，查询进度的意图是一致的。
- **底层严密解耦**：虽然入口统一，但解析 `_进度.md` 的业务逻辑依然封装在各自的产线中，避免了写出一个需要兼容 4 种截然不同数据结构的万能上帝类（God Object）。
- **公共解析下沉（Option 1）**：虽然业务逻辑解耦，但所有产线的进度工具都在底层共享了 `skills/common/markdown_parser.py` 来确保原子写（Atomic Write）、文件锁（File Lock）和格式解析的稳定性。
