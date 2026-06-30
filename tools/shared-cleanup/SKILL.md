---
name: shared-cleanup
description: 仓库级瘦身/清理工具。Use when asked to scan, clean, slim, trim, prune, or delete unused/generated files under this repository or its `skills/` tree, including Python caches, pytest/mypy/ruff caches, OS junk, temp/backup files, empty throwaway dirs, or placeholder skill scaffolds. Defaults to dry-run/report and only deletes allowlisted generated junk when explicitly run in clean mode, with deleted-byte/saved-space reporting.
---

# shared-cleanup — 仓库级瘦身清理工具

`shared-cleanup` 清理低风险生成垃圾。默认只扫 `skills/`；需要检查整个仓库时显式加 `--repo`。这是仓库级 dev 工具，位于 `tools/shared-cleanup/`，不计入 workflow skill 集合。

## Workflow

1. 先扫描，不直接删：

```bash
python3 tools/shared-cleanup/scripts/cleanup.py scan
```

检查整个仓库：

```bash
python3 tools/shared-cleanup/scripts/cleanup.py scan --repo
```

2. 确认报告里 `auto_clean=true` 的项目后再删除：

```bash
python3 tools/shared-cleanup/scripts/cleanup.py clean
```

清理整个仓库的 allowlist 垃圾：

```bash
python3 tools/shared-cleanup/scripts/cleanup.py clean --repo
```

3. 空目录默认只报告；要一起删空目录时显式加：

```bash
python3 tools/shared-cleanup/scripts/cleanup.py clean --include-empty-dirs
```

## Deletion Policy

自动删除仅限：

- Python/测试/类型检查缓存：`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.hypothesis`, `*.pyc`, `*.pyo`
- OS 垃圾：`.DS_Store`, `Thumbs.db`, `desktop.ini`
- 临时/备份文件：`*~`, `*.bak`, `*.orig`, `*.tmp`, `*.swp`, `*.swo`
- `skills/` 默认扫描中的本地调试日志：`*.log`

自动删除前会检查 Git 跟踪状态：命中 allowlist 但已被 git 跟踪的文件，或包含已跟踪文件的 allowlist 目录，只报告为 `REVIEW`，不自动删除。

只报告、不自动删：

- 含 TODO 模板文本的 `SKILL.md`（可能是未完成 scaffold）
- `node_modules`, `dist`, `build`, `.venv`, `.next`, `.turbo`, `.cache`, `coverage` 等大目录（可能是依赖、构建产物、资产或本地实验）
- `--repo` 模式下的 `*.log`（可能是生产运行、生成溯源或失败复盘证据）
- 已被 git 跟踪的 allowlist 命中项（如纳入版本管理的快照日志或测试 fixture）
- 空目录（除非加 `--include-empty-dirs`）

## Output

默认输出人读表。需要机器消费时：

```bash
python3 tools/shared-cleanup/scripts/cleanup.py scan --json
```

`clean` 输出会包含：

- `cleaned`：删除的 allowlist 项数量。
- `saved` / `saved_bytes`：本次删除的文件字节数，用于计算节省空间。
- `auto_bytes`：当前扫描中可自动删除项的总大小。
- `review_bytes`：只报告、不自动删除项的总大小。

## Rules

- 默认根目录是 `skills/`；只有显式 `--repo` 才扫整个仓库。
- 即使在 `--repo` 模式，也只自动删 allowlist 生成垃圾；作品目录、生成资产目录、依赖目录、构建目录和日志文件默认只按规则报告，不做语义性删除。
- 不用“未被引用”作为自动删除依据；这类判断容易误删路由型 skill。
- 不自动删除已被 git 跟踪的文件或包含已跟踪文件的目录；这类项需要人工确认后用 git 操作处理。
- 删除前先看 `scan` 输出；清理后跑 `git status --short --ignored` 确认只减少 ignored/generated 文件。
