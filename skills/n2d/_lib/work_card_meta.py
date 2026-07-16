#!/usr/bin/env python3
"""work_card_meta.py — n2d 作品卡片（封面 + 简介）产物字段的单一真值源。

桌面应用「作品列表区」的卡片要展示封面缩略图 + 一段简介，数据来自作品根
`_meta.json` 的 `synopsis` / `cover` 两个字段。本模块是 n2d 本线对这两个字段的
确定性读写实现，供 n2d-script 立项与 n2d-image 封面步骤共用（同属 n2d 线共享
`_lib`，不跨线、不依赖已删除的公共层）。

约定（与 docs/作品卡片-封面与简介契约.md 对齐）：
- `synopsis`: string，≤ 240 字，取自本线已有产物；立项当刻可为空串占位，bible
  产出后用确定性方式回填，**不覆盖用户已填的非占位内容**（write_if_absent 语义）。
- `cover`: string | null，相对作品根的竖版 PNG 路径（如 `出图/封面/cover.png`）；
  纯净机上封面步骤只产 prompt/job 包，`cover` 保持 null；真正渲染出 PNG 后用
  `backfill_cover` 确定性回填。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

SYNOPSIS_MAX = 240
DEFAULT_COVER_REL = "出图/封面/cover.png"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# 占位前缀：这些内容视为「尚未填写」，回填时可覆盖；用户填的真实简介不含这些。
_PLACEHOLDER_PREFIXES = ("待补", "待填", "待精修", "TODO", "todo", "TBD")


def _meta_path(root: os.PathLike | str) -> Path:
    return Path(root) / "_meta.json"


def load_meta(root: os.PathLike | str) -> Dict[str, Any]:
    path = _meta_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_meta_atomic(root: os.PathLike | str, meta: Dict[str, Any]) -> Path:
    path = _meta_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def is_placeholder_synopsis(value: Any) -> bool:
    """空串 / 占位文案视为「未填写」，可被确定性回填覆盖。"""
    text = str(value or "").strip()
    if not text:
        return True
    return any(text.startswith(prefix) for prefix in _PLACEHOLDER_PREFIXES)


def clip_synopsis(value: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) > SYNOPSIS_MAX:
        text = text[: SYNOPSIS_MAX - 1].rstrip() + "…"
    return text


def _read_md_section(path: Path, heading: str) -> str:
    """读取 markdown `## <heading>` 段的首个非占位正文行。"""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return ""
    target = None
    for i, line in enumerate(lines):
        if line.strip().lstrip("#").strip() == heading and line.lstrip().startswith("#"):
            target = i
            break
    if target is None:
        return ""
    for line in lines[target + 1:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            break
        # 去掉引用块 / 列表标记
        cleaned = stripped.lstrip(">").lstrip("-*").strip()
        if not cleaned:
            continue
        if is_placeholder_synopsis(cleaned):
            continue
        return cleaned
    return ""


def read_synopsis_candidate(root: os.PathLike | str) -> str:
    """按契约 §3 从 n2d 本线已有产物推导 synopsis 候选；无则返回空串。

    优先序（都取非占位内容）：
      1. 开发包/series_bible.md 的「一句话卖点」
      2. 设定库/series_bible.md 的「一句话卖点」（若未来登记）
      3. 开发包/adaptation_strategy.json 的核心承诺（principles 首个非占位项）
      4. 开发包/season_arc.json 的 series_promise
    """
    root = Path(root)
    for rel in ("开发包/series_bible.md", "设定库/series_bible.md"):
        text = _read_md_section(root / rel, "一句话卖点")
        if text:
            return clip_synopsis(text)

    strategy = root / "开发包" / "adaptation_strategy.json"
    try:
        data = json.loads(strategy.read_text(encoding="utf-8"))
        for item in data.get("principles") or []:
            text = str(item or "").strip()
            if text and not is_placeholder_synopsis(text):
                return clip_synopsis(text)
    except Exception:
        pass

    arc = root / "开发包" / "season_arc.json"
    try:
        data = json.loads(arc.read_text(encoding="utf-8"))
        text = str(data.get("series_promise") or "").strip()
        if text and not is_placeholder_synopsis(text):
            return clip_synopsis(text)
    except Exception:
        pass
    return ""


def ensure_work_card_fields(
    root: os.PathLike | str,
    *,
    synopsis: Optional[str] = None,
    cover: Any = None,
) -> Dict[str, Any]:
    """立项时补齐 synopsis / cover 两个键（write_if_absent：只补缺、不 clobber）。

    - 缺 `synopsis` → 写入 `synopsis`（传入值或空串占位）
    - 缺 `cover` → 写入 `cover`（默认 None）
    已存在的键一律不改。返回本次实际新增的字段。
    """
    meta = load_meta(root)
    if not meta:
        return {}
    changed: Dict[str, Any] = {}
    if "synopsis" not in meta:
        meta["synopsis"] = clip_synopsis(synopsis) if synopsis else ""
        changed["synopsis"] = meta["synopsis"]
    if "cover" not in meta:
        meta["cover"] = cover
        changed["cover"] = meta["cover"]
    if changed:
        _write_meta_atomic(root, meta)
    return changed


def backfill_synopsis(root: os.PathLike | str, synopsis: Optional[str] = None) -> Tuple[bool, str]:
    """bible 产出后确定性回填 synopsis。

    只在当前 synopsis 为空 / 占位时写入；用户已填的真实简介不覆盖。
    `synopsis` 显式给定时用它，否则从本线产物推导。返回 (是否写入, 最终值)。
    """
    meta = load_meta(root)
    if not meta:
        return False, ""
    current = meta.get("synopsis")
    if not is_placeholder_synopsis(current):
        return False, str(current)
    candidate = clip_synopsis(synopsis) if synopsis else read_synopsis_candidate(root)
    if not candidate:
        return False, str(current or "")
    if str(current or "") == candidate:
        return False, candidate
    meta["synopsis"] = candidate
    _write_meta_atomic(root, meta)
    return True, candidate


def validate_cover_png(root: os.PathLike | str, png_rel: str = DEFAULT_COVER_REL) -> Tuple[bool, str, str]:
    """校验封面 PNG：在作品根内、真实 PNG、可解码。返回 (ok, 规范相对路径, 原因)。

    只接受解析后仍在作品根内的规范相对路径（拒绝绝对路径 / `..` 越界）。
    """
    root = Path(root).resolve()
    rel = str(png_rel or "").strip()
    if not rel:
        return False, "", "empty_path"
    candidate = (root / rel)
    try:
        resolved = candidate.resolve()
        resolved.relative_to(root)
    except Exception:
        return False, "", "path_escapes_root"
    if not resolved.is_file():
        return False, "", "file_missing"
    try:
        with open(resolved, "rb") as fh:
            head = fh.read(8)
    except Exception:
        return False, "", "unreadable"
    if head != PNG_MAGIC:
        return False, "", "not_png"
    normalized = resolved.relative_to(root).as_posix()
    return True, normalized, "ok"


def backfill_cover(root: os.PathLike | str, png_rel: str = DEFAULT_COVER_REL) -> Tuple[bool, str, str]:
    """真正渲染出竖版 PNG 后确定性回填 `cover`。

    - PNG 校验不过 → 不写，`cover` 保持原值（通常 null），返回原因。
    - 已有有效 `cover`（用户或先前回填）→ 不 clobber。
    返回 (是否写入, cover 值, 原因)。
    """
    meta = load_meta(root)
    if not meta:
        return False, "", "no_meta"
    ok, normalized, reason = validate_cover_png(root, png_rel)
    if not ok:
        return False, str(meta.get("cover") or ""), reason
    current = meta.get("cover")
    if current and str(current).strip():
        # 已有封面路径不覆盖；仅当仍指向同一张时视为幂等成功。
        if str(current).strip() == normalized:
            return False, normalized, "already_set"
        return False, str(current), "cover_already_set_keep"
    meta["cover"] = normalized
    _write_meta_atomic(root, meta)
    return True, normalized, "backfilled"
