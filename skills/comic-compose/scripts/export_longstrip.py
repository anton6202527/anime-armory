#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成漫画导出 manifest，并可选用 Pillow 渲染长图分段。"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def ordered_panel_ids(layout: dict) -> list[str]:
    ids: list[str] = []
    for seg in layout.get("segments", []):
        panels = sorted(seg.get("panels", []), key=lambda p: (p.get("y", 0), p.get("x", 0)))
        for panel in panels:
            pid = panel.get("panel_id")
            if pid and pid not in ids:
                ids.append(pid)
    return ids


def find_panel_image(panel_dir: Path, panel_id: str) -> Path | None:
    for ext in IMAGE_EXTS:
        candidate = panel_dir / f"{panel_id}{ext}"
        if candidate.is_file():
            return candidate
    matches = sorted(panel_dir.glob(f"{panel_id}.*"))
    return next((m for m in matches if m.suffix.lower() in IMAGE_EXTS), None)


def build_manifest(root: Path, chapter: str, layout_path: Path, panel_dir: Path, out_dir: Path, max_height: int) -> dict:
    layout = load_json(layout_path)
    panel_ids = ordered_panel_ids(layout)
    panels = []
    missing = []
    for pid in panel_ids:
        img = find_panel_image(panel_dir, pid)
        if img:
            panels.append({"panel_id": pid, "path": str(img.relative_to(root))})
        else:
            missing.append(pid)
    return {
        "schema_version": 1,
        "kind": "comic_export_manifest",
        "chapter": chapter,
        "layout": str(layout_path.relative_to(root)),
        "panel_dir": str(panel_dir.relative_to(root)),
        "out_dir": str(out_dir.relative_to(root)),
        "max_segment_height": max_height,
        "panels": panels,
        "missing_panels": missing,
        "rendered": [],
    }


def render_longstrip(manifest: dict, root: Path, out_dir: Path, max_height: int, gap: int, background: str) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow 未安装；已可生成 manifest，如需渲染长图请先安装 Pillow。") from exc

    images = []
    for item in manifest["panels"]:
        path = root / item["path"]
        image = Image.open(path).convert("RGB")
        images.append((item["panel_id"], image))
        item["size"] = {"width": image.width, "height": image.height}

    if not images:
        return

    width = max(image.width for _, image in images)
    parts: list[list[tuple[str, Image.Image]]] = []
    current: list[tuple[str, Image.Image]] = []
    current_h = 0
    for pid, image in images:
        add_h = image.height + (gap if current else 0)
        if current and current_h + add_h > max_height:
            parts.append(current)
            current = []
            current_h = 0
            add_h = image.height
        current.append((pid, image))
        current_h += add_h
    if current:
        parts.append(current)

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered = []
    for idx, part in enumerate(parts, 1):
        height = sum(img.height for _, img in part) + gap * max(0, len(part) - 1)
        canvas = Image.new("RGB", (width, height), background)
        y = 0
        panel_ids = []
        for pid, image in part:
            x = math.floor((width - image.width) / 2)
            canvas.paste(image, (x, y))
            y += image.height + gap
            panel_ids.append(pid)
        out_path = out_dir / f"part_{idx:03d}.webp"
        canvas.save(out_path, quality=92)
        rendered.append({"path": str(out_path.relative_to(root)), "panel_ids": panel_ids, "size": {"width": width, "height": height}})
    manifest["rendered"] = rendered


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画长图导出 manifest/渲染")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--layout", default=None)
    parser.add_argument("--panel-dir", default=None)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--max-height", type=int, default=12000)
    parser.add_argument("--gap", type=int, default=24)
    parser.add_argument("--background", default="#ffffff")
    parser.add_argument("--render", action="store_true", help="用 Pillow 实际渲染长图分段")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    layout_path = Path(args.layout).expanduser().resolve() if args.layout else root / "排版" / args.chapter / "layout.json"
    panel_dir = Path(args.panel_dir).expanduser().resolve() if args.panel_dir else root / "出图" / args.chapter / "panels"
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else root / "排版" / args.chapter / "长图"
    manifest_path = root / "排版" / args.chapter / "export_manifest.json"

    if not layout_path.is_file():
        print(f"[err] layout 不存在：{layout_path}")
        return 2
    panel_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(root, args.chapter, layout_path, panel_dir, out_dir, args.max_height)

    if args.render:
        try:
            render_longstrip(manifest, root, out_dir, args.max_height, args.gap, args.background)
        except RuntimeError as err:
            manifest["render_error"] = str(err)
            print(f"[warn] {err}")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {manifest_path}")
    if manifest["missing_panels"]:
        print("[warn] 缺少面板图：" + ", ".join(manifest["missing_panels"]))
    if manifest["rendered"]:
        print(f"[ok] rendered {len(manifest['rendered'])} part(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
