#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 与 layout.json 生成逐格出图任务包。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_setting(root: Path, key: str, default: str) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def load_reference_registry(root: Path) -> dict:
    path = root / "出图" / "共享" / "identity_registry.json"
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def path_relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_reference_path(root: Path, ref_id: str, registry: dict) -> str:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets, dict) else None
    candidates: list[Path] = []
    if isinstance(asset, dict):
        for key in ("anchor_path", "primary_path", "path"):
            raw = asset.get(key)
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                candidates.append(path if path.is_absolute() else root / path)
        views = asset.get("views") if isinstance(asset.get("views"), dict) else {}
        for key in ("front", "three_quarter", "face", "side", "back"):
            raw = views.get(key) if isinstance(views, dict) else ""
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                candidates.append(path if path.is_absolute() else root / path)
        for item in asset.get("reference_images") or []:
            raw = item.get("path") if isinstance(item, dict) else item
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                candidates.append(path if path.is_absolute() else root / path)
    shared = root / "出图" / "共享" / "图片"
    for suffix in ("__anchor.png", ".png", ".jpg", ".jpeg", ".webp"):
        candidates.append(shared / f"{ref_id}{suffix}")
    for path in candidates:
        if path.is_file():
            return path_relative_to_root(root, path)
    return ""


def compact_metadata(value: Any, *, max_len: int = 460) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list):
        text = "；".join(compact_metadata(item, max_len=max_len) for item in value)
    elif isinstance(value, dict):
        items = []
        for key, item in value.items():
            item_text = compact_metadata(item, max_len=max_len)
            if item_text:
                items.append(f"{key}:{item_text}")
        text = "；".join(items)
    else:
        text = str(value).strip()
    text = re.sub(r"\s+", " ", text).strip("； ")
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def asset_contract(ref_id: str, asset: dict[str, Any]) -> str:
    label = str(asset.get("display_name") or asset.get("name") or ref_id)
    parts = [f"{ref_id}={label}"]
    for key, title in (
        ("character_dna", "角色DNA"),
        ("dna_contract", "定妆契约"),
        ("variant_policy", "年龄/形态继承"),
        ("forbidden_inheritance", "禁继承"),
        ("style_contract", "风格契约"),
        ("notes", "备注"),
    ):
        text = compact_metadata(asset.get(key))
        if text:
            parts.append(f"{title}:{text}")
    age_variants = asset.get("age_variants")
    if isinstance(age_variants, dict) and age_variants:
        parts.append("已定义年龄形态:" + ",".join(map(str, age_variants.keys())))
    if str(asset.get("type") or "").lower() == "character" or ref_id.startswith("CHAR_"):
        parts.append("同一角色换年龄、受伤、闭关、觉醒或换装时，只允许改变年龄比例/状态/服饰层，不得换脸、换发际线、换眼型或丢失标志物")
    return "；".join(parts)


def registry_style_contract(registry: dict) -> str:
    parts: list[str] = []
    for key in ("style_contract", "consistency_policy", "forbidden_inheritance"):
        text = compact_metadata(registry.get(key), max_len=620)
        if text:
            parts.append(f"{key}:{text}")
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    for ref_id, asset in sorted(assets.items()):
        if not isinstance(asset, dict):
            continue
        if ref_id.startswith("STYLE_") or str(asset.get("type") or "").lower() == "style":
            parts.append(asset_contract(ref_id, asset))
    return "；".join(parts)


def panel_reference_ids(panel: dict) -> list[str]:
    ids: list[str] = []
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw).strip()
            if ref_id and ref_id.startswith(("CHAR_", "MON_", "LOC_", "PROP_", "SYS_", "FX_", "STYLE_")) and ref_id not in ids:
                ids.append(ref_id)
    return ids


def panel_rects(layout: dict) -> dict[str, dict]:
    rects = {}
    for segment in layout.get("segments", []):
        for panel in segment.get("panels", []):
            pid = panel.get("panel_id")
            if pid:
                rects[pid] = panel
    return rects


def build_prompt(panel: dict, style: str, registry: dict) -> str:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    ref_ids = panel_reference_ids(panel)
    parts = [
        f"无字漫画分格画面，{style}",
        f"画面事实：{panel.get('description', '')}",
    ]
    style_contract = registry_style_contract(registry)
    if style_contract:
        parts.append("项目风格锚与一致性契约：" + style_contract)
    if panel.get("characters"):
        parts.append("角色：" + "、".join(map(str, panel.get("characters", []))))
    if panel.get("location"):
        parts.append("场景：" + str(panel.get("location")))
    if panel.get("art_notes"):
        parts.append("构图与表演：" + str(panel.get("art_notes")))
    if ref_ids:
        contracts = []
        for ref_id in ref_ids:
            asset = assets.get(ref_id) if isinstance(assets, dict) else None
            if isinstance(asset, dict):
                contracts.append(asset_contract(ref_id, asset))
            else:
                contracts.append(ref_id)
        parts.append("共享参考ID与不可漂移约束：" + " || ".join(contracts))
    if panel.get("dialogue") or panel.get("narration"):
        parts.append("在不挡脸、不挡手脚、不挡关键道具的位置预留低细节留白区域；不要画对白气泡、旁白框、空白文字框或任何可读文字")
    parts.append("定型参考图是最高优先级；截图里的播放按钮、搜索框、字幕、水印、平台 UI、竖排标题和可读文字都不是设定，必须排除")
    parts.append("线条清晰，主体明确，角色脸部、发型、服装、灵力纹路、标志道具和整体画风稳定，适合后期嵌字")
    return "；".join(part for part in parts if part)


def build_jobs(root: Path, chapter: str) -> dict:
    panel_script = load_json(root / "脚本" / chapter / "panel_script.json")
    layout = load_json(root / "排版" / chapter / "layout.json")
    rects = panel_rects(layout)
    model = read_setting(root, "生图模型", "自定义")
    channel = read_setting(root, "生图渠道", "manual")
    style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    text_language = read_setting(root, "文字语言", "中文")
    registry = load_reference_registry(root)
    jobs = []
    for panel in panel_script.get("panels", []):
        pid = panel.get("panel_id")
        rect = rects.get(pid, {})
        jobs.append(
            {
                "panel_id": pid,
                "status": "planned",
                "size": {"width": int(rect.get("w", 1440)), "height": int(rect.get("h", 900))},
                "prompt": build_prompt(panel, style, registry),
                "negative_prompt": "文字，水印，logo，乱码字，字幕，播放按钮，搜索框，播放器控件，平台 UI，竖排标题，对白气泡，空白气泡，旁白框，文字框，额外手指，畸形手，手脚混淆，把脚画成手，脸部漂移，发际线漂移，眼型漂移，年龄形态换脸，服装漂移，标志灵纹丢失，低清晰度，低成本彩漫感，Q版化，过度血腥细节",
                "references": [
                    {"id": ref, "path": resolve_reference_path(root, str(ref), registry)}
                    for ref in panel_reference_ids(panel)
                ],
                "result_path": "",
                "source": channel,
            }
        )
    return {
        "schema_version": 1,
        "kind": "comic_panel_jobs",
        "chapter": chapter,
        "model": model,
        "channel": channel,
        "text_language": text_language,
        "jobs": jobs,
    }


def write_reference_index(root: Path, chapter: str, jobs: dict) -> None:
    refs: dict[str, dict[str, object]] = {}
    for job in jobs.get("jobs", []):
        for ref in job.get("references", []):
            rid = ref.get("id")
            if rid:
                item = refs.setdefault(rid, {"count": 0, "path": ""})
                item["count"] = int(item.get("count") or 0) + 1
                if ref.get("path"):
                    item["path"] = ref.get("path")
    lines = [
        f"# 共享参考任务索引 — {chapter}",
        "",
        "正式逐格出图前，先补齐这些角色、场景、道具或特效参考。",
        "",
        "| ref_id | 出现次数 | 状态 | 建议 |",
        "|---|---:|---|---|",
    ]
    for rid, item in sorted(refs.items()):
        count = int(item.get("count") or 0)
        path = str(item.get("path") or "")
        if path:
            lines.append(f"| {rid} | {count} | ✅ | `{path}` |")
        else:
            lines.append(f"| {rid} | {count} | ⬜ | 生成或放入 `出图/共享/图片/` 后回填 panel_jobs.json |")
    if not refs:
        lines.append("| （无） | 0 | - | 当前脚本未声明 references |")
    path = root / "出图" / "共享" / "prompt" / "00_索引.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_progress(root: Path, chapter: str, stage: str, value: str) -> None:
    path = root / "_进度.md"
    if not path.is_file():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    headers: list[str] = []
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and cells[0] == "话":
                headers = cells
            elif headers and len(cells) >= len(headers) and cells[0] == chapter and stage in headers:
                cells[headers.index(stage)] = value
                line = "| " + " | ".join(cells) + " |"
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画逐格出图任务包")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    jobs = build_jobs(root, args.chapter)
    out_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_reference_index(root, args.chapter, jobs)
    if not args.no_progress:
        update_progress(root, args.chapter, "出图包", "✅")
    print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
