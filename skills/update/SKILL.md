---
name: update
description: 智能更新与重制计划分发中心（Smart Update Dispatcher）。统一入口用于检查 skill 代码/prompt 更新是否影响项目；n2d 支持快照比对与最小重制计划，n2d/mv/ad 支持选择性图片/视频 media_refresh 计划。media_refresh 只生成计划，不做审片/质检判定；保留/重制结论必须来自已有 gate/QC/review findings 或显式人工输入。Use when asked to 更新, 检查更新, 看看有没有更新, update, 重制计划, skill升级, 只重出部分图片, 只重出部分视频. Triggers 更新, update, 检查更新, skill升级, 重制计划, n2d-update, 媒体重制, 部分图片重制, 部分视频重制.
---

# update — 智能更新分发中心

当大仓的 skill 代码或者 prompt 模板发生升级时，你不需要去猜这个更新是否影响了你现在的项目。
`update` 会根据你所在的目录上下文分发。当前有两类能力：

1. **skill 快照更新影响**：n2d 完整支持，比对 skill 快照，生成从最早受影响阶段回放到当前阶段的最小重制计划。
2. **选择性媒体刷新**：n2d / mv / ad 支持对少量图片或视频生成 media_refresh 计划。它不直接调用生图/生视频后端，也不做“坏/能用”的审片判定；所有保留/重制结论必须引用已有 gate/QC/review findings 或显式人工输入。

## 用法

你可以直接对我说：“检查一下更新”或“生成重制计划”。

如果你需要人工调用：
```bash
python3 skills/update/scripts/dispatch.py check [作品根目录]
python3 skills/update/scripts/dispatch.py record [作品根目录]
python3 skills/update/scripts/dispatch.py media [作品根目录] --image Clip_001 --video Clip_002 --write-plan
```

对 `制漫剧/<剧名>` 未传集号时，公共入口默认补 `--all`，扫描全剧；在仓库根运行时会扫描所有 `制漫剧/*/_进度.md`。在作品目录内可以只给集号（`dispatch.py check 第1集`），目录用当前位置推断。

`media` 必须指向具体作品根；n2d 还要传 `--episode 第N集`，避免误扫全剧。`--image` / `--video` / `--target` 都可以逗号分隔多个目标；未列入 targets 的图片/视频默认不动。

## 支持的自动路由

| 目录上下文 | 路由到哪条产线 | 底层调用的工具 | 支持状态 |
|---|---|---|---|
| `制漫剧/<剧名>` | **n2d** (漫剧) | `skills/n2d-update/scripts/update_plan.py` | ✅ 完整支持快照比对与重跑计划 |
| `制漫剧/<剧名>` | **n2d media** | `skills/update/scripts/media_refresh.py` | ✅ 指定集/指定 Clip 的图片/视频选择性刷新 |
| 仓库根 / `制漫剧/` | **n2d** 批量 | 逐个 n2d 项目调用 `update_plan.py --all` | ✅ 批量扫描 |
| `写小说/<书名>` | **novel** (小说) | 暂无专用工具，退回 `self_audit.py` 提示 | ⚠️ 建议使用自审或 git diff |
| `写歌/<曲名>` | **song** (歌曲) | 暂无 | ⚠️ 友好提示，待接入 |
| `制MV/<曲名>` | **mv media** | `media_refresh.py` | ✅ 指定 Clip 首帧/尾帧/视频选择性刷新计划 |
| `拍广告/<项目>` | **ad media** | `media_refresh.py` | ✅ 指定广告镜头图片/视频选择性刷新计划 |

## media 原则

- **只生成计划**：`media_refresh` 是选择性刷新计划生成器，不替代 `n2d-review`、`mv-review`、`ad-review` 或各线 gate/QC 做审片。
- **判定来源**：所有“坏/能用/可沿用/需重制”的结论，必须来自已有 gate/QC/review findings（含 severity、affected targets、return_to_stage 等）或显式人工输入。
- **无证据不判**：如果没有 findings 或人工判定，`media_refresh` 只能列出下一步复核命令/人工确认步骤；不得把 `--image`/`--video`/`--target` 直接当作坏目标，也不得无条件排入重制。
- **证据驱动沿用**：finding 或人工判定显示轻微构图、表情、背景细节或审美偏差不影响叙事/卡点/品牌表达时，才按“能用沿用”处理。
- **证据驱动重制**：只有已有 finding、人工判定或文件完整性事实确认缺文件、身份/产品/场景漂移、品牌色/logo/接缝/时长/契约继承 block、后端混用或合规阻断时，才把对应 target 排入重制。
- **不碰未列目标**：`media` 是少量图片/视频刷新工具，不做整集、整支 MV 或整条广告全链重跑。
- **机器契约清楚**：计划 JSON 的 `execution_steps[]` 按顺序区分 `type=command`（可执行 shell）与 `type=agent_step`（需要 AI 代理按对应 SKILL 路由），`commands[]` 只保留可执行命令。
- **有历史账**：`--write-plan` 会写 `生产数据/media_refresh_plan*.json/md`，并追加 `生产数据/skill_update_runs.jsonl`，方便回看每次 update 计划做了什么。

## 架构边界

- **入口统一**：用户只记 `update`。
- **能力不虚标**：skill 快照比对目前只有 n2d 完整支持；媒体选择性刷新只支持确有图片/视频生产线的 n2d/mv/ad。song/novel 会明确提示应转交 mv/n2d 生产线。
- **未来扩展点**：song/mv/ad 如需接入，可复用 `skills/common/skill_snapshot.py` 做哈希快照，但重制范围必须由各自产线契约判断，不能由公共层猜。
