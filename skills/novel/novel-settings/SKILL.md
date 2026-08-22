---
name: novel-settings
description: novel 项目 `_设置.md` 的读写、审计、重置与同步入口。Use when the user asks to set/change/reset/audit/sync project settings, choices, preferences, `_设置.md`, global defaults, or selection points for a 写小说/novel project. Wraps the novel line-owned settings helper so agents do not edit `_设置.md` by hand.
---

# novel-settings — 项目设置入口

你是 novel 项目选择点的确定性设置入口。所有对 `<作品根>/_设置.md` 的修改都优先走脚本，不手工改表，避免粗体 key、旧别名、记录区和校验口径分叉。

## 命令

```bash
python3 skills/novel/novel-settings/scripts/settings_cli.py audit <作品根>
python3 skills/novel/novel-settings/scripts/settings_cli.py set <作品根> <选择点> <值>
python3 skills/novel/novel-settings/scripts/settings_cli.py reset <作品根> <选择点>
python3 skills/novel/novel-settings/scripts/settings_cli.py sync-global <作品根> --all
```

- `audit`：解析 `_设置.md`，按 `skills/novel/_lib/settings.py` 的 schema 校验，默认有 error 返回非零。
- `set`：调用 `set_project_setting()`，保留原格式，自动追加 `## 记录`。未知/实验值需要 `--force`。
- `reset`：调用 `reset_project_setting()`，删除指定选择点并记录。
- `sync-global`：调用 `sync_global_settings()`，把当前项目可同步选择写入私有全局默认；可用 `--all` 或传 `选择点=值`。

`创作工艺档` 使用规范值 `commercial_serial / genre_novel / literary / experimental`；中文别名会归一。它独立于 `目标平台`，改档后应重跑 `scene_cards.py check` 与 `manuscript_map.py --write`。

## 边界

- 本 skill 只管理设置，不启动写作、审稿、评分、导出或本地化。
- `_设置.md` 中的普通、可逆选择可沉默沿用；权利/合规、核心作者意图、不可逆发布/覆盖、最终署名/成品验收，以及阶段预算包创建、扩大、过期或合同变化才需要新的授权。已有精确绑定且有效的预算包在余量内不逐调用重复确认。
- 用户显式改选择点时，应立即用 `set` 落档；不要等下次阶段才写。
- `自定义` / `manual` / 实验后端不应被 schema 永久挡住；确认是用户明确选择时用 `--force`，并用 `--message` 写清原因。
