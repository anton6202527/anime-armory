---
name: progress
description: 智能进度分发中心（Smart Progress Dispatcher）。统一的只读进度查询入口。根据当前目录上下文（写小说/、制漫剧/、写歌/、制MV/、拍广告/）把“查进度/下一步”路由到对应产线的专属进度工具；在仓库根会汇总所有带 _进度.md 的项目。Use when asked to 查进度, 看进度, 下一步做什么, progress. Triggers 进度, 查进度, 当前进度, 下一步, progress, progress dispatcher.
---

# progress — 智能进度分发中心

不需要再记复杂的工具路径。`progress` 是**只读**路由层：根据你所在的目录上下文，自动调用对应产线的底层进度脚本，输出当前前沿和下一步建议。

它不回写 `_进度.md`。真正推进状态仍由各阶段 skill 完成产物后按自己的契约回写。

## 用法

你可以直接对我说：“查一下现在的进度”或“下一步该干什么”。

输出下一步时，推荐的 skill 名称一律写裸名（如 `n2d-image`、`mv-compose`），不要写 `/n2d-image`。公共 progress 面向跨 AI agent，斜杠前缀可能被误当成宿主工具命令。

如果你需要人工调用：
```bash
python3 skills/progress/scripts/dispatch.py [作品根/作品子目录/产线根/仓库根] [--limit N]
```

在仓库根运行时，会扫描 `写小说/`、`制漫剧/`、`写歌/`、`制MV/`、`拍广告/` 下所有带 `_进度.md` 的项目。
在作品子目录运行时，会向上寻找最近的 `_进度.md` 并回到作品根后再分发。
`--limit` 是公共层自己的只读选项，只转发给支持它的 novel/song/mv 进度脚本；其它任意底层参数不透传。

## 支持的自动路由

| 目录上下文 | 路由到哪条产线 | 底层调用的工具 |
|---|---|---|
| `写小说/<书名>` | **novel** (小说) | `skills/novel-craft/scripts/progress.py` |
| `制漫剧/<剧名>` | **n2d** (漫剧) | `skills/n2d-progress/scan.py` |
| `写歌/<曲名>` | **song** (歌曲) | `skills/song-craft/scripts/progress.py` |
| `制MV/<曲名>` | **mv** (MV) | `skills/mv-craft/scripts/progress.py` |
| `拍广告/<项目>` | **ad** (广告) | `skills/ad-craft/scripts/progress.py` |
| 仓库根或单条产线根 | 汇总扫描 | 逐项目调用对应工具 |

## 架构边界

- **入口统一**：用户只记 `progress`，不用记每条线的脚本路径。
- **解析归属各线**：n2d 是逐集矩阵，song/mv/ad 是单项目阶段表，novel 有自己的写作状态机；公共层不做万能解析器。
- **公共能力只放稳定基建**：需要写文件、加锁、原子更新的逻辑放在各线或 `skills/common/`，只读扫描不强行共享一个大 parser。产线上下文探测（目录归属 + marker 兜底）是稳定基建，统一在 `skills/common/line_detect.py`，progress/update 两个 dispatcher 共用，新增产线只改一处。
- **progress 脚本归属约定**：单项目阶段表的线放在各自 craft skill（`<线>-craft/scripts/progress.py`，novel/song/mv/ad 一致）；n2d 因逐集矩阵复杂度单独成 skill（`n2d-progress/scan.py`）。
