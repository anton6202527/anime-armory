---
name: update
description: 智能更新与重制计划分发中心（Smart Update Dispatcher）。统一的流水线更新嗅探与重制计划入口。根据当前工作目录，自动调用对应产线的 update 工具（如 n2d-update）来比对 skill 代码是否发生变更，并生成安全的回放/重制计划。Use when asked to 更新, 检查更新, 看看有没有更新, update, 重制计划, skill升级. Triggers 更新, update, 检查更新, skill升级, 重制计划, n2d-update.
---

# update — 智能更新分发中心

当大仓的 skill 代码或者 prompt 模板发生升级时，你不需要去猜这个更新是否影响了你现在的项目。
作为一个智能路由层，`update` 会根据你所在的目录上下文，自动调用对应产线的底层更新嗅探脚本。

## 用法

你可以直接对我说：“检查一下更新”或“生成重制计划”。

如果你需要人工调用：
```bash
python3 skills/update/scripts/dispatch.py check [作品根目录]
python3 skills/update/scripts/dispatch.py record [作品根目录]
```

## 支持的自动路由

| 目录上下文 | 路由到哪条产线 | 底层调用的工具 | 支持状态 |
|---|---|---|---|
| `制漫剧/<剧名>` | **n2d** (漫剧) | `skills/n2d-update/scripts/update_plan.py` | ✅ 完整支持快照比对与重跑计划 |
| `写小说/<书名>` | **novel** (小说) | 暂无专用工具，退回 `self_audit.py` 提示 | ⚠️ 建议使用自审或 git diff |
| `写歌/<曲名>` | **song** (歌曲) | 暂无 | 敬请期待 |
| `制MV/<曲名>` | **mv** (MV) | 暂无 | 敬请期待 |

## 架构优势

这套工具实现了和 `progress` 一样的两层架构：
- **用户心智统一**：查更新统一走 `update`，心智不再割裂。
- **底层公共快照**：底层共享了 `skills/common/skill_snapshot.py` 计算哈希、比对快照。未来如果有 `novel-update` 或 `mv-update`，也能直接复用这套基建，而只需重写属于自己的“重制范围判定逻辑”。
