#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""作品级竖版封面 prompt/job 包 + 确定性回填。

漫画作品卡片需要一张竖版封面（约 9:16 / 5:7）。本步骤复用本线出图能力：
项目风格锚 + 角色定妆同源参考，产出一份稳定的封面 prompt/job 包。

优雅降级（C4/B4）：纯净机（断网、无重依赖、无凭证）上本步骤**只**产出
job 包 + 合规留痕，`_meta.json` 的 ``cover`` 保持 ``null``、绝不硬阻断主流程。
真正渲染出竖版 PNG 后，用 ``--backfill <png>`` 确定性回填 ``cover`` 为
作品根相对路径。

「由什么生成这张封面」落到**具体模型名**（读自 `_设置.md` 的 `生图模型`，
如 ``GPT Image 2``）；渠道/CLI 作为访问入口（access path）分列（`生图渠道`）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_panel_jobs as bpj  # noqa: E402
import reference_planner  # noqa: E402


COVER_DIR = Path("出图") / "封面"
COVER_JOB_REL = COVER_DIR / "prompt" / "cover_job.json"
COVER_PNG_REL = COVER_DIR / "cover.png"
# 竖版 9:16 作品封面画布（作品卡片按封面缩略图 + 简介展示）。
COVER_SIZE = {"width": 1440, "height": 2560}
MAX_COVER_CHARACTER_REFS = 3


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_synopsis(root: Path) -> str:
    """封面概念文案取自本线产物：优先 _meta.json 已回填的 synopsis，
    否则现读 story_bible.md 的「一句话核心」。不跨线取数。"""
    meta_path = root / "_meta.json"
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
        text = str(meta.get("synopsis") or "").strip()
        if text:
            return text
    bible = root / "设定库" / "story_bible.md"
    if not bible.is_file():
        return ""
    lines = bible.read_text(encoding="utf-8").splitlines()
    collecting = False
    picked: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            if collecting:
                break
            collecting = stripped.lstrip("#").strip() == "一句话核心"
            continue
        if collecting:
            item = stripped.lstrip("-*").strip()
            if item:
                picked.append(item)
    return " ".join(picked).strip()


def cover_character_refs(root: Path, registry: dict) -> list[dict[str, Any]]:
    """收集作品主要角色的定妆参考，与逐格出图**同源**（同一 registry、
    同一批共享定妆 PNG）。只取已有可解析参考图的具名角色。"""
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    out: list[dict[str, Any]] = []
    for ref_id in sorted(assets):
        if not str(ref_id).startswith("CHAR_"):
            continue
        refs = bpj.resolve_reference_paths(root, ref_id, registry)
        if not refs:
            continue
        asset = assets.get(ref_id) if isinstance(assets, dict) else {}
        out.append(
            {
                "character_id": ref_id,
                "contract": bpj.asset_contract(ref_id, asset if isinstance(asset, dict) else {}),
                "references": refs,
            }
        )
        if len(out) >= MAX_COVER_CHARACTER_REFS:
            break
    return out


def build_cover_prompt(title: str, synopsis: str, style: str, style_anchor: str, registry: dict, char_refs: list[dict[str, Any]]) -> str:
    parts = [
        f"《{title}》作品竖版封面 key visual，{style}",
        f"竖版构图（约 9:16），画面中心为主角，气势与情绪先行，留出上方标题安全区（不写任何文字/标题）",
    ]
    if synopsis:
        parts.append("作品核心（仅供画面立意，不得写进画面）：" + synopsis)
    if style_anchor and style_anchor not in {"未指定", "manual", ""}:
        parts.append("风格锚：" + style_anchor)
    style_contract = bpj.registry_style_contract(registry)
    if style_contract:
        parts.append("项目风格锚与一致性契约：" + style_contract)
    for item in char_refs:
        if item.get("contract"):
            parts.append("角色定妆同源契约：" + item["contract"])
    return "；".join(parts)


def build_cover_job(root: Path) -> dict:
    model = bpj.read_setting(root, "生图模型", "GPT Image 2")
    channel = bpj.read_setting(root, "生图渠道", "manual")
    style = bpj.read_setting(root, "基础视觉风格", "彩色国漫条漫")
    style_anchor = bpj.read_setting(root, "风格锚", "未指定")
    text_language = bpj.read_setting(root, "文字语言", "中文")
    caps = bpj.resolve_capabilities(model, channel) if bpj.resolve_capabilities else None

    title = root.name
    meta_path = root / "_meta.json"
    if meta_path.is_file():
        try:
            title = str(json.loads(meta_path.read_text(encoding="utf-8")).get("title") or title)
        except (OSError, json.JSONDecodeError):
            pass

    registry = bpj.load_reference_registry(root)
    synopsis = read_synopsis(root)
    char_refs = cover_character_refs(root, registry)
    references = [ref for item in char_refs for ref in item["references"]]

    submit_prompt = build_cover_prompt(title, synopsis, style, style_anchor, registry, char_refs)
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_sha = reference_planner.file_sha256(registry_path) if registry_path.is_file() else ""

    return {
        "schema_version": 1,
        "kind": "comic_cover_job",
        "scope": "work_cover",
        "title": title,
        "size": COVER_SIZE,
        "orientation": "portrait",
        "text_language": text_language,
        "synopsis_source": "设定库/story_bible.md 一句话核心 / _meta.json synopsis",
        # C5：生成者落到具体模型名；渠道/CLI 作为访问入口分列。
        "生成模型": model,
        "生成渠道": channel,
        "backend_capabilities": caps.to_dict() if caps else {},
        "reference_budget": caps.to_dict() if caps else {},
        "prompt": submit_prompt,
        "submit_prompt": submit_prompt,
        "submit_prompt_sha256": hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest(),
        "negative_prompt": bpj.PRODUCTION_NEGATIVE_CONTRACT,
        "character_bindings": [{"character_id": item["character_id"]} for item in char_refs],
        "references": references,
        "consumed_contracts": {
            "identity_registry": {
                "path": "出图/共享/identity_registry.json",
                "sha256": registry_sha,
                "schema_version": registry.get("schema_version"),
            }
        },
        # C4/B4：纯净机上只产 job 包 + 留痕，不渲染、不写 cover。
        "compliance_note": (
            "纯净机降级：本包只产封面 prompt/job 与合规留痕，不调用任何生成后端；"
            "cover 保持 null。真正渲染出竖版 PNG 后用 "
            "build_cover_job.py --backfill <png> 确定性回填 _meta.json cover。"
            "封面生成者以具体模型名（生成模型）为准，渠道仅为访问入口。"
        ),
        "status": "planned",
        "result_path": "",
        "generated_at": now_iso(),
    }


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    """纯标准库读取 PNG 宽高（IHDR）；非合法 PNG 返回 None。"""
    try:
        with path.open("rb") as handle:
            header = handle.read(24)
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    try:
        width, height = struct.unpack(">II", header[16:24])
    except struct.error:
        return None
    if width <= 0 or height <= 0:
        return None
    return width, height


def update_meta_cover(root: Path, rel_path: str) -> None:
    meta_path = root / "_meta.json"
    meta = {}
    if meta_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            meta = {}
    meta["cover"] = rel_path
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def refresh_meta_synopsis(root: Path) -> str:
    """立项后阶段的确定性回填：圣经补齐「一句话核心」后，把简介写进 _meta.json。

    只在 _meta.synopsis 当前为空时回填，尊重用户手写内容（不 clobber）。
    """
    meta_path = root / "_meta.json"
    if not meta_path.is_file():
        return ""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if str(meta.get("synopsis") or "").strip():
        return str(meta["synopsis"])
    synopsis = read_synopsis(root)
    if not synopsis:
        return ""
    meta["synopsis"] = synopsis
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return synopsis


def update_progress(root: Path, prefix: str, mark: str = "[x]") -> None:
    """回写 _进度.md 里以 prefix 开头的作品封面复选项（B5）。"""
    path = root / "_进度.md"
    if not path.is_file():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ] ") and prefix in stripped:
            line = line.replace("- [ ] ", f"- {mark} ", 1)
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def do_build(root: Path) -> int:
    filled = refresh_meta_synopsis(root)
    if filled:
        print(f"[ok] _meta.json synopsis 回填：{filled}")
    job = build_cover_job(root)
    out_path = root / COVER_JOB_REL
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_progress(root, "竖版封面 prompt/job 包")
    print(f"[ok] {COVER_JOB_REL}")
    print(f"     生成模型={job['生成模型']}（渠道={job['生成渠道']}）尺寸={job['size']['width']}x{job['size']['height']}")
    print("[note] 纯净机降级：cover 仍为 null。渲染出竖版 PNG 后运行：")
    print(f"       python3 skills/comic-image/scripts/build_cover_job.py {root} --backfill <png>")
    return 0


def do_backfill(root: Path, png: Path) -> int:
    png = png if png.is_absolute() else (root / png)
    png = png.resolve()
    if not png.is_file():
        print(f"[err] 封面 PNG 不存在：{png}", file=sys.stderr)
        return 2
    try:
        png.relative_to(root)
    except ValueError:
        print(f"[err] 封面 PNG 必须在作品根内：{png}", file=sys.stderr)
        return 2
    dims = _png_dimensions(png)
    if dims is None:
        print(f"[err] 不是合法 PNG：{png}", file=sys.stderr)
        return 2
    width, height = dims
    if height <= width:
        print(f"[err] 封面须为竖版（height>width），当前 {width}x{height}", file=sys.stderr)
        return 2
    rel = str(png.relative_to(root))
    update_meta_cover(root, rel)
    update_progress(root, "竖版封面 PNG 渲染并回填")
    # 生成留痕：由哪个具体模型产出这张封面（C5）。
    job_path = root / COVER_JOB_REL
    model = channel = ""
    if job_path.is_file():
        try:
            job = json.loads(job_path.read_text(encoding="utf-8"))
            model = str(job.get("生成模型") or "")
            channel = str(job.get("生成渠道") or "")
        except (OSError, json.JSONDecodeError):
            pass
    print(f"[ok] _meta.json cover = {rel}（{width}x{height}）")
    if model:
        print(f"     生成模型={model}（渠道={channel}）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画作品竖版封面 prompt/job 包，或回填 cover")
    parser.add_argument("project_root")
    parser.add_argument("--backfill", metavar="PNG", default=None, help="渲染出竖版封面 PNG 后回填 _meta.json cover")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    if not root.is_dir():
        print(f"[err] 作品根不存在：{root}", file=sys.stderr)
        return 2
    if args.backfill:
        return do_backfill(root, Path(args.backfill))
    return do_build(root)


if __name__ == "__main__":
    raise SystemExit(main())
