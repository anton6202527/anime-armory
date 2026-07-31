#!/usr/bin/env python3
"""Ad character/location/prop consistency evidence from actual shot images."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ASSET_RE = re.compile(r"\b(?:CHAR|LOC|PROP|BRAND|PROD)_[A-Za-z0-9_]+\b")


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def shot_label(shot, index):
    raw = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or "")
    m = re.search(r"\d+", raw)
    return f"镜头{int(m.group()):02d}" if m else f"镜头{index:02d}"


def assets(shot):
    value = shot.get("assets")
    out = set()
    if isinstance(value, dict):
        out.update(str(k) for k, v in value.items() if v and ASSET_RE.fullmatch(str(k)))
    elif isinstance(value, list):
        out.update(str(v) for v in value if ASSET_RE.fullmatch(str(v)))
    return out


def _load_imaging():
    try:
        from PIL import Image, ImageDraw  # type: ignore
        return Image, ImageDraw
    except Exception:
        return None, None


def _dhash(path: Path, Image):
    try:
        im = Image.open(path).convert("L").resize((9, 8))
        px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
        bits = 0
        for y in range(8):
            for x in range(8):
                bits = (bits << 1) | (px[y * 9 + x] < px[y * 9 + x + 1])
        return int(bits)
    except Exception:
        return None


def _contact_sheet(root: Path, aid: str, rel_images, Image, ImageDraw):
    images = []
    for rel in rel_images:
        path = root / rel
        if not path.is_file():
            continue
        try:
            im = Image.open(path).convert("RGB")
            im.thumbnail((320, 180))
            images.append((path, im.copy()))
        except Exception:
            pass
    if not images:
        return None
    canvas = Image.new("RGB", (320 * min(3, len(images)), 210 * ((len(images) + 2) // 3)), "white")
    draw = ImageDraw.Draw(canvas)
    for index, (path, im) in enumerate(images):
        x, y = (index % 3) * 320, (index // 3) * 210
        canvas.paste(im, (x, y))
        draw.text((x + 4, y + 184), path.stem, fill="black")
    out = root / "生产数据" / "一致性并排" / f"{aid}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=88)
    return str(out.relative_to(root))


def build(root: Path):
    root = root.resolve()
    sb = load(root / "脚本" / "storyboard.json", {}) or {}
    registry = load(root / "出图" / "共享" / "asset_registry.json", {}) or {}
    registry_text = json.dumps(registry, ensure_ascii=False)
    by_asset = {}
    findings = []
    Image, ImageDraw = _load_imaging()
    for index, shot in enumerate(sb.get("shots") or sb.get("clips") or [], 1):
        label = shot_label(shot, index)
        image = root / "出图" / "分镜" / "图片" / f"{label}.png"
        for aid in assets(shot):
            by_asset.setdefault(aid, []).append(str(image.relative_to(root)))
            if aid not in registry_text:
                findings.append({"severity": "block", "code": "asset_not_registered", "asset_id": aid,
                                 "shot": label, "msg": f"{aid} 未在 asset_registry 登记"})
            if not image.is_file():
                findings.append({"severity": "block", "code": "asset_shot_image_missing", "asset_id": aid,
                                 "shot": label, "msg": f"{label} 缺真实图片，无法复核 {aid}"})
    for aid, images in by_asset.items():
        # 产品/品牌是最严资产：跨镜阈值比常规资产更紧（26 vs 30 bit），命中标 priority=high
        # 并在 summary 置顶；仍是全帧启发式（产品 ROI 级比对归 product_qc），advisory 不 block。
        is_brand_asset = aid.startswith(("PROD_", "BRAND_"))
        if (is_brand_asset or aid.startswith(("CHAR_", "LOC_", "PROP_"))) and len(images) > 1:
            sheet = _contact_sheet(root, aid, images, Image, ImageDraw) if Image is not None else None
            hashes = [_dhash(root / rel, Image) for rel in images] if Image is not None else []
            valid = [value for value in hashes if value is not None]
            max_distance = max(((a ^ b).bit_count() for i, a in enumerate(valid) for b in valid[i + 1:]), default=0)
            drift_threshold = 26 if is_brand_asset else 30
            if max_distance > drift_threshold:
                finding = {"severity": "warn", "code": "cross_shot_visual_drift", "asset_id": aid,
                           "msg": f"{aid} 跨镜全帧 dHash 最大差 {max_distance}bit（阈 {drift_threshold}）；启发式仅提示并排复核",
                           "contact_sheet": sheet, "confidence": "heuristic"}
                if is_brand_asset:
                    finding["priority"] = "high"
                    finding["msg"] = ("[产品/品牌] " + finding["msg"] +
                                      "——产品跨镜漂移整片报废，优先看这条")
                findings.append(finding)
            findings.append({"severity": "info", "code": "manual_contact_review_required", "asset_id": aid,
                             "msg": f"{aid} 跨 {len(images)} 镜复用；需用列出的真实图片做人脸/服装/空间/道具并排签收",
                             "images": images, "contact_sheet": sheet})
    findings.sort(key=lambda f: (f.get("priority") != "high",
                                 {"block": 0, "warn": 1, "info": 2}.get(f.get("severity"), 3)))
    return {
        "schema_version": 1, "kind": "ad_asset_consistency", "assets": by_asset,
        "summary": {"block": sum(1 for f in findings if f["severity"] == "block"),
                    "warn": sum(1 for f in findings if f["severity"] == "warn")},
        "findings": findings,
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root)
    payload = build(root)
    out = root / "生产数据" / "asset_consistency.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# asset consistency block={payload['summary']['block']}")
    return 1 if payload["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
