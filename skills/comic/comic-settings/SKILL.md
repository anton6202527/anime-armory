---
name: comic-settings
description: comic 项目 `_设置.md` 的读写、审计、重置与同步入口。Use when the user asks to set/change/reset/audit/sync project settings, choices, preferences, `_设置.md`, global defaults, or selection points for a 画漫画/comic project. Wraps the comic line-owned settings helper so agents do not edit `_设置.md` by hand.
---

# comic-settings — 项目设置入口

你是 comic 项目选择点的确定性设置入口。所有对 `<作品根>/_设置.md` 的修改都优先走脚本，不手工改表，避免 key、旧别名、记录区和校验口径分叉。

## 命令

```bash
python3 skills/comic/comic-settings/scripts/settings_cli.py audit <作品根>
python3 skills/comic/comic-settings/scripts/settings_cli.py set <作品根> <选择点> <值>
python3 skills/comic/comic-settings/scripts/settings_cli.py reset <作品根> <选择点>
python3 skills/comic/comic-settings/scripts/settings_cli.py sync-global <作品根> --all
```

- `audit`：解析 `_设置.md`，按 `skills/comic/_lib/settings.py` 的 schema 校验，默认有 error 返回非零。
- `set`：调用 `set_project_setting()`，保留原格式，自动追加 `## 记录`。未知/实验值需要 `--force`。
- `set <作品根> 生产档位 <档位>`：将 `短篇验证` / `连载标准` / `连载高一致性` / `出版交付` 展开为定妆、形态继承、一致性硬闸等联动设置，避免相互矛盾的组合。
- `reset`：调用 `reset_project_setting()`，删除指定选择点并记录。
- `sync-global`：调用 `sync_global_settings()`，把当前项目可同步选择写入私有全局默认；可用 `--all` 或传 `选择点=值`。
- `基础视觉风格` 的内置候选见 `skills/comic/references/视觉风格候选.md`；可写 `预设(补充词)` 或 `自定义(...)`。
- `交付介质=web_images|print_pdf|epub_fxl` 与 `交付用途=internal|public|commercial` 分列；不要再用“商用”代替文件/介质格式。`epub_fxl` 仅表示外部 EPUB 的 readiness 合同，本线没有自动 EPUB renderer。
- `生图渠道=内置 imagegen` 表示使用当前 Codex 会话的内置图像工具；项目资产仍须复制进作品目录并写路径/SHA，不能只留在 `$CODEX_HOME/generated_images/`。

## 边界

- 本 skill 只管理设置，不启动脚本、排版、出图、嵌字、导出或审查。
- `_设置.md` 中的普通、可逆选择可沉默沿用；权利/合规、逐格当前像素、最终成品验收、不可逆发布/覆盖，以及阶段预算包创建、扩大、过期或合同变化才需要新的授权。已有精确绑定且有效的预算包在余量内不逐调用重复确认。
- 用户显式改选择点时，应立即用 `set` 落档；不要等下次阶段才写。
- `自定义` / `manual` / 实验后端不应被 schema 永久挡住；确认是用户明确选择时用 `--force`，并用 `--message` 写清原因。
- 漫画线默认 `生产档位=连载标准`，因此默认开启形态继承与角色一致性硬闸；短篇验证、高一致性连载或出版交付应显式切换档位。
