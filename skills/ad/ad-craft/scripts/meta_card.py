#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作品卡片字段（synopsis / cover）在 `_meta.json` 上的确定性读写 —— 拍广告线自维护。

桌面「作品列表区」的卡片要展示封面缩略图 + 一段简介，数据来自作品根 `_meta.json` 的
`synopsis`（≤240 字）与 `cover`（作品根相对路径的**竖版** PNG，无封面为 null）。

拍广告线的取数（不跨线取数）：
- `synopsis` ← brief 的 `key_message`（优先）/ `campaign_objective`（其次）。
- `cover`    ← 一张竖版 key visual / endcard PNG（由 ad-image `plan_cover.py` 排包后外部渲染，再回填）。

写入语义遵 `write_if_absent`：立项只补占位、不覆盖用户手写内容；brief / 封面产出后确定性回填。
纯 stdlib；封面尺寸校验仅在 Pillow 存在时启用，缺失优雅降级（不硬阻断）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


SYNOPSIS_MAX = 240
_PLACEHOLDER_STRINGS = {"", "待补", "tbd"}


def _is_placeholder(value: Any) -> bool:
    """空、缺失、或显式占位（待补/tbd）都算系统占位，可被回填覆盖。"""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in _PLACEHOLDER_STRINGS
    return False


def _clean(text: Any) -> str:
    return text.strip() if isinstance(text, str) else ""


def _truncate(text: str, limit: int = SYNOPSIS_MAX) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def derive_synopsis(brief: Optional[Dict[str, Any]], fallback_objective: str = "") -> str:
    """按拍广告契约从 brief 派生简介：key_message 优先，其次 campaign_objective。

    brief 缺失或字段仍是占位时退回 fallback_objective（通常是立项默认广告目标）；
    再空则返回空串（卡片侧回退产线图标 + 「有进度/仅初始」文案）。
    """
    if isinstance(brief, dict):
        for key in ("key_message", "campaign_objective"):
            value = _clean(brief.get(key))
            if value and value.lower() not in _PLACEHOLDER_STRINGS:
                return _truncate(value)
    fallback = _clean(fallback_objective)
    if fallback and fallback.lower() not in _PLACEHOLDER_STRINGS:
        return _truncate(fallback)
    return ""


def _campaign_placeholder(brief: Optional[Dict[str, Any]]) -> str:
    """brief 仅由 campaign_objective 能派生出的占位串（用于判断 synopsis 是否仍是立项占位）。"""
    if isinstance(brief, dict):
        value = _clean(brief.get("campaign_objective"))
        if value and value.lower() not in _PLACEHOLDER_STRINGS:
            return _truncate(value)
    return ""


def load_meta(root: Path) -> Dict[str, Any]:
    path = root / "_meta.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_meta(root: Path, meta: Dict[str, Any]) -> None:
    (root / "_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _load_brief(root: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads((root / "需求" / "brief.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def initial_synopsis(default_objective: str = "") -> str:
    """立项当刻（brief 尚未由 AI 填充）的占位简介：只能用默认广告目标，缺则空串。"""
    return derive_synopsis({"campaign_objective": default_objective})


def backfill_synopsis(root: Path, *, force: bool = False) -> Dict[str, Any]:
    """brief 产出后确定性回填 synopsis。

    只在当前 synopsis 是系统占位（空 / 待补 / 仍等于立项 campaign_objective 占位）时覆盖；
    用户手写的自定义简介一律保留（force=True 才强制覆盖）。返回操作结果。
    """
    root = root.resolve()
    if not (root / "_meta.json").exists():
        return {"changed": False, "reason": "no_meta", "synopsis": None}
    meta = load_meta(root)
    brief = _load_brief(root)
    derived = derive_synopsis(brief)
    current = meta.get("synopsis")
    placeholder = _campaign_placeholder(brief)
    is_system_placeholder = (
        _is_placeholder(current)
        or (isinstance(current, str) and placeholder and current.strip() == placeholder)
    )
    if not derived:
        return {"changed": False, "reason": "no_source", "synopsis": current}
    if not (force or is_system_placeholder):
        return {"changed": False, "reason": "user_authored", "synopsis": current}
    if isinstance(current, str) and current.strip() == derived:
        return {"changed": False, "reason": "unchanged", "synopsis": current}
    meta["synopsis"] = derived
    save_meta(root, meta)
    return {"changed": True, "reason": "backfilled", "synopsis": derived}


def _normalized_cover_rel(root: Path, png: str) -> Tuple[Optional[str], Optional[str]]:
    """把封面 PNG 归一成作品根相对路径；越界 / 不存在 / 非 PNG 返回 (None, 原因)。"""
    root = root.resolve()
    candidate = Path(png)
    abs_path = candidate if candidate.is_absolute() else (root / candidate)
    try:
        abs_path = abs_path.resolve()
    except OSError:
        return None, "unresolved_path"
    try:
        rel = abs_path.relative_to(root)
    except ValueError:
        return None, "outside_project_root"
    if abs_path.suffix.lower() != ".png":
        return None, "not_png"
    if not abs_path.is_file():
        return None, "missing_file"
    return rel.as_posix(), None


def _is_portrait(abs_path: Path) -> Optional[bool]:
    """竖版校验：Pillow 存在时判 h>=w，缺失则返回 None（跳过，不硬阻断）。"""
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return None
    try:
        with Image.open(abs_path) as im:
            w, h = im.size
    except Exception:
        return None
    return h >= w


def set_cover(root: Path, png: str, *, allow_non_portrait: bool = False) -> Dict[str, Any]:
    """封面 PNG 渲染完成后确定性回填 `cover` 为作品根相对路径。

    校验：路径在作品根内、文件存在、扩展名 .png、（Pillow 可用时）竖版。
    这是封面产出后的回填 helper，不是主流程闸门——校验失败只拒绝写入并说明原因，
    不抛断言、不影响其它阶段。
    """
    root = root.resolve()
    if not (root / "_meta.json").exists():
        return {"changed": False, "reason": "no_meta", "cover": None}
    rel, reason = _normalized_cover_rel(root, png)
    if rel is None:
        return {"changed": False, "reason": reason, "cover": None}
    portrait = _is_portrait(root / rel)
    if portrait is False and not allow_non_portrait:
        return {"changed": False, "reason": "not_portrait", "cover": None}
    meta = load_meta(root)
    if meta.get("cover") == rel:
        return {"changed": False, "reason": "unchanged", "cover": rel}
    meta["cover"] = rel
    save_meta(root, meta)
    _record_cover_progress(root, rel)
    return {
        "changed": True,
        "reason": "backfilled",
        "cover": rel,
        "portrait_checked": portrait is not None,
    }


def _record_cover_progress(root: Path, rel: str) -> None:
    """B5：封面回填后用确定性脚本在 `_进度.md` 维护记录留痕（缺进度文件优雅跳过）。"""
    progress = root / "_进度.md"
    if not progress.exists():
        return
    try:
        _here = str(Path(__file__).resolve().parent)
        if _here not in sys.path:
            sys.path.insert(0, _here)
        import progress_set  # 同线 ad-craft/scripts；追加维护记录不改阶段行
        text = progress.read_text(encoding="utf-8")
        lines = progress_set.append_note(text.splitlines(), f"封面回填 _meta.json.cover={rel}")
        progress.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    except Exception:
        # 进度留痕是尽力而为，不得阻断封面回填主动作。
        pass


def clear_cover(root: Path) -> Dict[str, Any]:
    """封面作废时把 cover 归零（回退产线图标占位）。"""
    root = root.resolve()
    if not (root / "_meta.json").exists():
        return {"changed": False, "reason": "no_meta", "cover": None}
    meta = load_meta(root)
    if meta.get("cover") in (None, "", "null"):
        return {"changed": False, "reason": "already_null", "cover": None}
    meta["cover"] = None
    save_meta(root, meta)
    return {"changed": True, "reason": "cleared", "cover": None}


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description="拍广告作品卡片字段（synopsis/cover）确定性读写")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("synopsis", help="brief 产出后回填 _meta.json.synopsis")
    sp.add_argument("project_root")
    sp.add_argument("--force", action="store_true", help="强制覆盖（含用户手写简介）")

    cp = sub.add_parser("cover", help="封面 PNG 渲染完成后回填 _meta.json.cover")
    cp.add_argument("project_root")
    cp.add_argument("--png", required=True, help="竖版封面 PNG（作品根相对或绝对路径）")
    cp.add_argument("--allow-non-portrait", action="store_true",
                    help="允许非竖版封面（默认拒绝，卡片要求竖版）")

    clr = sub.add_parser("clear-cover", help="作废封面，cover 归零")
    clr.add_argument("project_root")

    args = ap.parse_args(argv)
    root = Path(args.project_root)
    if args.cmd == "synopsis":
        result = backfill_synopsis(root, force=args.force)
    elif args.cmd == "cover":
        result = set_cover(root, args.png, allow_non_portrait=args.allow_non_portrait)
    else:
        result = clear_cover(root)
    print(json.dumps(result, ensure_ascii=False))
    # 0 = 成功或有意的空操作（含保留用户内容 / 暂无数据源）；非 0 = 回填被拒（校验失败）。
    benign = {"unchanged", "already_null", "user_authored", "no_source"}
    return 0 if (result.get("changed") or result.get("reason") in benign) else 1


if __name__ == "__main__":
    sys.exit(main())
