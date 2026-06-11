---
name: update
description: 智能更新与重制计划分发中心（Smart Update Dispatcher）。统一入口用于检查 skill 代码/prompt 更新是否影响项目；当前只有 n2d 线完整支持快照比对与最小重制计划，其它产线会被识别并给出友好待接入提示。Use when asked to 更新, 检查更新, 看看有没有更新, update, 重制计划, skill升级. Triggers 更新, update, 检查更新, skill升级, 重制计划, n2d-update.
---

# update — 智能更新分发中心

当大仓的 skill 代码或者 prompt 模板发生升级时，你不需要去猜这个更新是否影响了你现在的项目。
`update` 会根据你所在的目录上下文分发。当前**完整自动化支持 n2d**：比对 skill 快照，生成从最早受影响阶段回放到当前阶段的最小重制计划。其它产线先明确提示“未接入”，避免伪支持。

## 用法

你可以直接对我说：“检查一下更新”或“生成重制计划”。

如果你需要人工调用：
```bash
python3 skills/update/scripts/dispatch.py check [作品根目录]
python3 skills/update/scripts/dispatch.py record [作品根目录]
```

对 `制漫剧/<剧名>` 未传集号时，公共入口默认补 `--all`，扫描全剧；在仓库根运行时会扫描所有 `制漫剧/*/_进度.md`。

## 支持的自动路由

| 目录上下文 | 路由到哪条产线 | 底层调用的工具 | 支持状态 |
|---|---|---|---|
| `制漫剧/<剧名>` | **n2d** (漫剧) | `skills/n2d-update/scripts/update_plan.py` | ✅ 完整支持快照比对与重跑计划 |
| 仓库根 / `制漫剧/` | **n2d** 批量 | 逐个 n2d 项目调用 `update_plan.py --all` | ✅ 批量扫描 |
| `写小说/<书名>` | **novel** (小说) | 暂无专用工具，退回 `self_audit.py` 提示 | ⚠️ 建议使用自审或 git diff |
| `写歌/<曲名>` | **song** (歌曲) | 暂无 | ⚠️ 友好提示，待接入 |
| `制MV/<曲名>` | **mv** (MV) | 暂无 | ⚠️ 友好提示，待接入 |
| `拍广告/<项目>` | **ad** (广告) | 暂无 | ⚠️ 友好提示，待接入 |

## 架构边界

- **入口统一**：用户只记 `update`。
- **能力不虚标**：只有 n2d 已经有 `skill_snapshot.py` + 阶段回放判定 + plan 落盘；其它线先提示待接入。
- **未来扩展点**：song/mv/ad 如需接入，可复用 `skills/common/skill_snapshot.py` 做哈希快照，但重制范围必须由各自产线契约判断，不能由公共层猜。
