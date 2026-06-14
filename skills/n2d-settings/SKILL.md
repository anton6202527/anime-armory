---
name: n2d-settings
description: n2d 项目 `_设置.md` 的读写、审计、重置与同步入口。Use when the user asks to set/change/reset/audit/sync project settings, choices, preferences, `_设置.md`, global defaults, or selection points for a 制漫剧/n2d project. Wraps the shared settings helper so agents do not edit `_设置.md` by hand.
---

# n2d-settings — 项目设置入口

你是 n2d 项目选择点的确定性设置入口。所有对 `<作品根>/_设置.md` 的修改都优先走脚本，不手工改表，避免粗体 key、旧别名、记录区和校验口径分叉。

## 命令

```bash
python3 skills/n2d-settings/scripts/settings_cli.py audit <作品根>
python3 skills/n2d-settings/scripts/settings_cli.py set <作品根> <选择点> <值>
python3 skills/n2d-settings/scripts/settings_cli.py reset <作品根> <选择点>
python3 skills/n2d-settings/scripts/settings_cli.py sync-global <作品根> --all
```

- `audit`：解析 `_设置.md`，按 `skills/n2d/_lib/settings.py` 的 schema 校验，默认有 error 返回非零。
- `set`：调用 `set_project_setting()`，保留原格式，自动追加 `## 记录`。未知/实验值需要 `--force`。
- `reset`：调用 `reset_project_setting()`，删除指定选择点并记录。
- `sync-global`：调用 `sync_global_settings()`，把当前项目可同步选择写入全局默认；可用 `--all` 或传 `选择点=值`。

## 边界

- 本 skill 只管理设置，不启动任何出图、出视频、配音、合成或重制。
- 合规/花钱/不可逆选择即使已写入 `_设置.md`，对应 stage 开跑前仍要再次确认。
- 用户显式改选择点时，应立即用 `set` 落档；不要等下次阶段才写。
- `自定义` / `manual` / 实验后端不应被 schema 永久挡住；确认是用户明确选择时用 `--force`，并用 `--message` 写清原因。
