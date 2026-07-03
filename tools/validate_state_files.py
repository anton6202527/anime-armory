#!/usr/bin/env python3
"""状态文件 schema-lint（P1-5）。

`_进度.md` / `_设置.md` 是 n2d 的状态机真值源，却是人可手改、无 schema 校验的 markdown——
手抖破坏 `| 集 |` 表头或列对齐就**静默断路由**（dispatcher 解析失败或错位读单元格）。本 lint 用
**与路由同一套解析器**（markdown_parser + n2d_route.cell_state）离线校验所有作品根的状态文件，
把「会让 run.py next 崩/错」的状态在 CI/pre-commit 就拦下，而不是产线上才发现。

同时把历史**双路径**残留 surface 成可迁移的 deprecation（退役而非永远静默双读）：
  • `common/_进度.md`（旧布局，progress_path 已不再兜底）；
  • `出视频/<集>/配音/时长清单.json`（2026 出视频↔合成分家前的旧位，应在 合成/ 下）。

git-free·纯 stdlib（只读文件）。
用法：
  python3 tools/validate_state_files.py            # 扫 创作区/ 全部作品根
  python3 tools/validate_state_files.py <作品根>    # 只校验一个根
  python3 tools/validate_state_files.py --strict    # legacy 残留也算失败（迁移闸门）
退出码：1 = 有硬错误（表解析失败）；0 = 干净（legacy 残留默认只警告，--strict 下升为失败）。
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
from typing import List, Tuple

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_LIB = os.path.join(ROOT, "skills", "n2d", "_lib")
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

VALID_CELL_HINT = "✅ / ⬜ / ⏳rough / N/M / — / 空"


def _parse_table(content: str):
    from markdown_parser import parse_markdown_table  # n2d/_lib
    return parse_markdown_table(content, header_identifier="集")


def _is_n2d_root(root: str) -> bool:
    # 制漫剧线作品根（n2d 状态机）——硬校验；其它线只软提示。
    return os.sep + "制漫剧" + os.sep in (root + os.sep)


def find_work_roots(base: str) -> List[str]:
    # 本 lint 校验 n2d 状态机（制漫剧线）；其它创作线（小说/MV/歌）有各自的 _进度 约定与校验，
    # 不在此耦合（独立性）。默认只扫 制漫剧 作品根。
    roots = []
    for p in glob.glob(os.path.join(base, "创作区", "制漫剧", "*")):
        if os.path.isfile(os.path.join(p, "_进度.md")) or os.path.isfile(os.path.join(p, "common", "_进度.md")):
            roots.append(p)
    return sorted(roots)


def validate_root(root: str) -> Tuple[List[str], List[str]]:
    """→ (errors, warnings)。errors 非空 = 硬失败。纯 IO 读。"""
    errors: List[str] = []
    warnings: List[str] = []
    rel = os.path.relpath(root, ROOT)

    canonical = os.path.join(root, "_进度.md")
    legacy = os.path.join(root, "common", "_进度.md")
    prog = canonical if os.path.isfile(canonical) else (legacy if os.path.isfile(legacy) else "")

    if not prog:
        errors.append(f"{rel}: 缺 _进度.md")
        return errors, warnings
    if prog == legacy:
        warnings.append(f"{rel}: 仍用旧布局 common/_进度.md——progress_path 已退役该兜底，请迁到 {rel}/_进度.md")

    try:
        content = open(prog, encoding="utf-8").read()
    except Exception as exc:
        errors.append(f"{rel}: 读 _进度.md 失败：{exc}")
        return errors, warnings

    try:
        header, rows = _parse_table(content)
    except Exception as exc:
        msg = f"{rel}: _进度.md 表解析失败（表头/列对齐坏了 → 会让 run.py next 断路由）：{exc}"
        (errors if _is_n2d_root(root) else warnings).append(msg)
        return errors, warnings

    if "集" not in header:
        (errors if _is_n2d_root(root) else warnings).append(
            f"{rel}: _进度.md 表头缺『集』列（dispatcher 按它认逐集行）")
    # 行单元格数与表头一致性（markdown_parser 已对齐，这里再核每行非空 PK）
    from n2d_route import cell_state, episode_number  # noqa: E402
    ep_rows = 0
    for r in rows:
        ep = r.get("集") or r.get("_pk") or ""
        if episode_number(ep) is None:
            continue
        ep_rows += 1
        # cell_state 永不抛错；这里检查是否有列值含明显坏 token（换行/竖线残留）。
        for col, val in r.items():
            if col.startswith("_"):
                continue
            if "|" in str(val) or "\n" in str(val):
                errors.append(f"{rel}: 集 {ep} 列『{col}』值异常（含 | 或换行 → 列对齐坏）：{val!r}")
    if _is_n2d_root(root) and ep_rows == 0:
        warnings.append(f"{rel}: _进度.md 无可识别的逐集行（第N集）")

    # _设置.md（可选）：能解析即可
    settings_md = os.path.join(root, "_设置.md")
    if os.path.isfile(settings_md):
        try:
            from settings import load_settings_meta
            load_settings_meta(root)
        except Exception as exc:
            errors.append(f"{rel}: _设置.md 解析失败：{exc}")

    # legacy 双路径残留（出视频/<集>/配音 旧清单位）
    for p in glob.glob(os.path.join(root, "出视频", "*", "配音", "时长清单.json")):
        warnings.append(f"{os.path.relpath(p, ROOT)}: 旧位时长清单（出视频/配音）——2026 出视频↔合成分家后应在 合成/ 下，请迁移")

    return errors, warnings


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="n2d 状态文件 schema-lint")
    ap.add_argument("root", nargs="?", help="单个作品根；缺省扫 创作区/")
    ap.add_argument("--strict", action="store_true", help="legacy 残留也算失败")
    ns = ap.parse_args(argv)

    roots = [os.path.abspath(ns.root)] if ns.root else find_work_roots(ROOT)
    all_err: List[str] = []
    all_warn: List[str] = []
    for root in roots:
        e, w = validate_root(root)
        all_err += e
        all_warn += w

    for w in all_warn:
        print(f"  ⚠ {w}")
    for e in all_err:
        print(f"  ❌ {e}")
    n = len(roots)
    if not all_err and (not all_warn or not ns.strict):
        print(f"✅ 状态文件 schema-lint：{n} 个作品根，{len(all_warn)} 处 legacy 警告，0 硬错误")
    if all_err or (ns.strict and all_warn):
        print(f"❌ 状态文件 schema-lint 未通过：{len(all_err)} 硬错误 / {len(all_warn)} 警告（--strict）")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
