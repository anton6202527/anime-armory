---
name: shared-cleanup
description: 公共 skill 瘦身/清理工具。Use when asked to scan, clean, slim, trim, prune, or delete unused/generated files under this repository's `skills/` tree, including Python caches, pytest/mypy/ruff caches, OS junk, temp/backup files, empty throwaway dirs, or placeholder skill scaffolds. Applicable to all families (`n2d-*`, `mv-*`, `song-*`, `novel-*`) and standalone public skills; defaults to dry-run/report and only deletes allowlisted generated junk when explicitly run in clean mode.
---

# shared-cleanup — 公共 skill 瘦身清理

`shared-cleanup` 只清理 `skills/` 树里的低风险垃圾文件，适用于 n2d / mv / song / novel / 公共能力所有 skill。

## Workflow

1. 先扫描，不直接删：

```bash
python3 skills/shared-cleanup/scripts/cleanup.py scan
```

2. 确认报告里 `auto_clean=true` 的项目后再删除：

```bash
python3 skills/shared-cleanup/scripts/cleanup.py clean
```

3. 空目录默认只报告；要一起删空目录时显式加：

```bash
python3 skills/shared-cleanup/scripts/cleanup.py clean --include-empty-dirs
```

## Deletion Policy

自动删除仅限：

- Python/测试/类型检查缓存：`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.hypothesis`, `*.pyc`, `*.pyo`
- OS 垃圾：`.DS_Store`, `Thumbs.db`, `desktop.ini`
- 临时/备份文件：`*~`, `*.bak`, `*.orig`, `*.tmp`, `*.swp`, `*.swo`, `*.log`

只报告、不自动删：

- 含 TODO 模板文本的 `SKILL.md`（可能是未完成 scaffold）
- `node_modules`, `dist`, `build`, `.venv` 等大目录（可能是某个 skill 的资产或本地实验）
- 空目录（除非加 `--include-empty-dirs`）

## Output

默认输出人读表。需要机器消费时：

```bash
python3 skills/shared-cleanup/scripts/cleanup.py scan --json
```

## Rules

- 不清理作品目录、生成资产目录、仓库根缓存；默认根目录是 `skills/`。
- 不用“未被引用”作为自动删除依据；这类判断容易误删路由型 skill。
- 删除前先看 `scan` 输出；清理后跑 `git status --short --ignored` 确认只减少 ignored/generated 文件。
