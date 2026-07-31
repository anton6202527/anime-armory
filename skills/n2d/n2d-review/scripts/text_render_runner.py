#!/usr/bin/env python3
"""OCR1 图中文字渲染校验 runner —— 关掉"图中中文字从不被实读校验"的缺口。

AI 生图的中文字渲染（系统面板数值/属性、牌匾匾额招牌、卷轴书页）是 2026 仍未解的弱项（base 模型
字形准确率 ~74%）。本 runner 为每个**声明了预期文字**的图中文字镜配 `(image, expected_text)` probe，
写成可复现 manifest；OCR batch 后端实读渲染文字、与预期做归一相似度比对，把不符的写进 `findings`
（数字不符=block，文本漂移=warn），供 `extended_consistency.check_text_render`（OCR1）消费。

预期文字来源：① 镜头绑定的 `ui_asset_registry` 资产 `text_template`/`text`；② storyboard clip 的
`图中文字`/`render_text`/`on_image_text` 字段。

外部命令契约（batch 优先）：
* `N2D_TEXT_OCR_BATCH_CMD`：收 `<manifest_path>`，就地填 `findings` 覆写。见 `backends/text_ocr_easyocr.py`。
缺命令则只产 manifest（不臆造），交装好 OCR 的环境复跑。

用法：python3 text_render_runner.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys
from typing import Any, Dict, List

import production_consistency as pc
import extended_consistency as ec

TEXT_RENDER_KIND = "n2d_text_render"


def _episode_images(root: str, ep: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for pat in ("png", "jpg", "jpeg", "webp"):
        for path in glob.glob(os.path.join(root, "出图", ep, "**", f"*.{pat}"), recursive=True):
            label = pc._clip_label({"id": os.path.basename(path)}, 0)
            out.setdefault(label, path)
    return out


def _ui_assets(root: str) -> Dict[str, dict]:
    reg = ec._registry(root, os.path.join("设定库", "ui_asset_registry.json"),
                       os.path.join("出图", "共享", "ui_asset_registry.json"))
    out: Dict[str, dict] = {}
    if isinstance(reg, dict):
        for a in (reg.get("assets") or reg.get("ui_assets") or []):
            if isinstance(a, dict) and a.get("id"):
                out[str(a["id"])] = a
    return out


def build_manifest(root: str, ep: str) -> dict:
    images = _episode_images(root, ep)
    ui_assets = _ui_assets(root)
    probes: List[dict] = []
    for _clip, label, text in ec._clip_iter(root, ep):
        low = text.lower()
        is_text = any(k.lower() in low for k in ec.UI_KEYWORDS) or any(k in text for k in ec.TEXT_IN_IMAGE_KEYWORDS)
        if not is_text:
            continue
        expected = ec._expected_text_for(text, ui_assets)
        if not expected or label not in images:
            continue
        probes.append({
            "shot": label,
            "image": os.path.relpath(images[label], root),
            "expected_text": expected,
        })
    return {
        "kind": TEXT_RENDER_KIND,
        "root": root,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "probes": probes,
        "findings": [],
    }


def _run_batch(path: str) -> bool:
    cmd = os.environ.get("N2D_TEXT_OCR_BATCH_CMD", "").strip()
    if not cmd:
        return False
    try:
        subprocess.run([*cmd.split(), path], timeout=3600, check=True)
        return True
    except Exception as exc:
        print(f"[text_render][warn] OCR 后端调用失败（忽略，保留 manifest）：{exc}", file=sys.stderr)
        return False


def write(root: str, ep: str) -> str:
    manifest = build_manifest(root, ep)
    path = os.path.join(root, "生产数据", f"text_render_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _run_batch(path)
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="OCR1 图中文字渲染校验 manifest/runner")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    if ns.write:
        path = write(root, ns.episode)
        if not ns.json:
            print(path)
            return 0
    manifest = build_manifest(root, ns.episode)
    if ns.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        on = bool(os.environ.get("N2D_TEXT_OCR_BATCH_CMD"))
        print(f"probes={len(manifest['probes'])} ocr={'on' if on else 'off(manifest only)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
