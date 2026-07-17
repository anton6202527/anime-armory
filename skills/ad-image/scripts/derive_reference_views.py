#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从一张已批准定妆图裁多视图分参考（n2d derive_makeup_pack 的广告薄版·本线自包含）。

为什么：`reference_planner` 的处方经常是"产品/代言人要 ≥2-3 张参考"，但三层定妆库里
常常只有一张主定妆——单张定妆照对 AI 只是固定板式，换角度/景别必重画。业界 2026 的
标准做法是给品牌主体建 master sheet（正面/四分之三/侧面/背面/细节…）逐镜喂参考。
本工具把"一张网格定妆大图 → 逐视图分参考 PNG + 溯源 manifest"变成可审计的确定性动作。

**不碰 asset_registry**：registry 母本↔快照受 gate `registry_snapshot_findings` 治理，
本工具只产出图片 + `生产数据/ad_reference_views.json`（含 source sha256/裁切框/建议补丁），
把 `suggested_registry_patch` 抄进 registry 是操作者显式动作，不由脚本静默代办。

用法：
    # 2x2 网格定妆图 → 4 个命名视图
    python3 derive_reference_views.py <作品根> --asset PROD_X --source 出图/定妆/PROD_X.png \
        --grid 2x2 --names 正面,四分之三,侧面,背面
    # 或显式归一化裁切框（0-1，left,top,right,bottom）
    python3 derive_reference_views.py <作品根> --asset PROD_X --source ... \
        --box 正面:0,0,0.5,1 --box 侧面:0.5,0,1,1
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

KIND = "ad_reference_views"
MANIFEST_REL = os.path.join("生产数据", "ad_reference_views.json")
OUT_DIR_REL = os.path.join("出图", "共享", "定妆视图")
DEFAULT_NAMES = ("正面", "四分之三", "侧面", "背面", "顶部", "细节1", "细节2", "细节3", "细节4")
ASSET_RE = re.compile(r"^(PROD|BRAND|CHAR|LOC|PROP)_[A-Za-z0-9_]+$")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_pil():
    try:
        from PIL import Image  # type: ignore
        return Image
    except Exception:
        return None


def parse_grid(spec: str) -> Tuple[int, int]:
    m = re.fullmatch(r"(\d+)[xX×](\d+)", str(spec or "").strip())
    if not m:
        raise ValueError(f"--grid 需要 RxC 形式（如 2x2），got {spec!r}")
    rows, cols = int(m.group(1)), int(m.group(2))
    if not (1 <= rows <= 6 and 1 <= cols <= 6 and rows * cols >= 2):
        raise ValueError(f"--grid 行列须在 1-6 且至少 2 格，got {rows}x{cols}")
    return rows, cols


def parse_box(spec: str) -> Tuple[str, Tuple[float, float, float, float]]:
    name, _, coords = str(spec or "").partition(":")
    parts = [p for p in coords.split(",") if p.strip() != ""]
    if not name.strip() or len(parts) != 4:
        raise ValueError(f"--box 需要 名字:l,t,r,b（0-1 归一化），got {spec!r}")
    l, t, r, b = (float(p) for p in parts)
    if not (0 <= l < r <= 1 and 0 <= t < b <= 1):
        raise ValueError(f"--box 坐标须满足 0≤l<r≤1、0≤t<b≤1，got {spec!r}")
    return name.strip(), (l, t, r, b)


def grid_boxes(rows: int, cols: int, names: Sequence[str]) -> List[Tuple[str, Tuple[float, float, float, float]]]:
    out = []
    for idx in range(rows * cols):
        r, c = divmod(idx, cols)
        name = names[idx] if idx < len(names) else DEFAULT_NAMES[idx] if idx < len(DEFAULT_NAMES) else f"视图{idx + 1}"
        out.append((name, (c / cols, r / rows, (c + 1) / cols, (r + 1) / rows)))
    return out


def derive(root: Path, asset_id: str, source_rel: str,
           boxes: List[Tuple[str, Tuple[float, float, float, float]]],
           min_view_px: int = 96) -> Dict[str, Any]:
    """裁视图 → PNG + manifest 条目。返回 manifest 记录（含建议补丁）。PIL 缺失抛 RuntimeError。"""
    Image = _load_pil()
    if Image is None:
        raise RuntimeError("需要 PIL/Pillow 才能裁图（生成类工具不做无像素降级）：pip install Pillow")
    if not ASSET_RE.match(asset_id):
        raise ValueError(f"asset_id 须是 PROD_/BRAND_/CHAR_/LOC_/PROP_ 前缀的登记 ID，got {asset_id!r}")
    src = (root / source_rel) if not Path(source_rel).is_absolute() else Path(source_rel)
    if not src.is_file():
        raise FileNotFoundError(f"源定妆图不存在：{src}")
    out_dir = root / OUT_DIR_REL / asset_id
    out_dir.mkdir(parents=True, exist_ok=True)
    source_sha = sha256_file(src)
    views: List[Dict[str, Any]] = []
    with Image.open(src) as im:
        rgb = im.convert("RGB")
        W, H = rgb.size
        seen_names: set = set()
        for name, (l, t, r, b) in boxes:
            if name in seen_names:
                raise ValueError(f"视图名重复：{name!r}")
            seen_names.add(name)
            px = (round(l * W), round(t * H), round(r * W), round(b * H))
            if px[2] - px[0] < min_view_px or px[3] - px[1] < min_view_px:
                raise ValueError(
                    f"视图『{name}』裁出仅 {px[2] - px[0]}x{px[3] - px[1]}px（<{min_view_px}px）——"
                    "分参考太小对身份锁定没意义，源图分辨率不足就先出高清定妆")
            target = out_dir / f"{name}.png"
            rgb.crop(px).save(target)
            views.append({
                "view": name,
                "path": str(target.relative_to(root)),
                "box_normalized": [l, t, r, b],
                "box_pixels": list(px),
                "size": [px[2] - px[0], px[3] - px[1]],
            })
    return {
        "asset_id": asset_id,
        "source": {"path": source_rel, "sha256": source_sha, "size": [W, H]},
        "derived_at": now_iso(),
        "views": views,
        "suggested_registry_patch": {
            "asset_id": asset_id,
            "append_reference_images": [v["path"] for v in views],
            "note": "把这些路径补进 asset_registry 里该资产的 reference_images（母本编辑是操作者显式动作，"
                    "改完记得刷新 registry 快照，否则 gate registry_snapshot 会拦）",
        },
    }


def load_manifest(root: Path) -> Dict[str, Any]:
    path = root / MANIFEST_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("kind") == KIND:
            return data
    except Exception:
        pass
    return {"schema_version": 1, "kind": KIND, "records": []}


def write_manifest(root: Path, manifest: Dict[str, Any]) -> Path:
    """原子写；同 asset+source sha 的旧记录被替换（重跑幂等），不同来源并存。"""
    path = root / MANIFEST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root", help="作品根")
    ap.add_argument("--asset", required=True, help="登记资产 ID（PROD_/BRAND_/CHAR_/LOC_/PROP_ 前缀）")
    ap.add_argument("--source", required=True, help="已批准的定妆网格图/master sheet（相对作品根）")
    ap.add_argument("--grid", help="RxC 网格切分（如 2x2）")
    ap.add_argument("--names", default="", help="网格模式的视图名，逗号分隔（默认 正面,四分之三,侧面,背面…）")
    ap.add_argument("--box", action="append", default=[], help="显式裁切框 名字:l,t,r,b（0-1），可多次")
    ap.add_argument("--min-view-px", type=int, default=96, help="视图最小边像素（默认 96）")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    try:
        if bool(ns.grid) == bool(ns.box):
            raise ValueError("--grid 与 --box 必须二选一")
        if ns.grid:
            rows, cols = parse_grid(ns.grid)
            names = [n.strip() for n in ns.names.split(",") if n.strip()] or list(DEFAULT_NAMES)
            boxes = grid_boxes(rows, cols, names)
        else:
            boxes = [parse_box(spec) for spec in ns.box]
        record = derive(root, ns.asset, ns.source, boxes, min_view_px=ns.min_view_px)
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    manifest = load_manifest(root)
    manifest["records"] = [r for r in manifest.get("records") or []
                           if not (r.get("asset_id") == record["asset_id"]
                                   and (r.get("source") or {}).get("sha256") == record["source"]["sha256"])]
    manifest["records"].append(record)
    manifest["generated_at"] = now_iso()
    path = write_manifest(root, manifest)
    print(f"# {ns.asset}: {len(record['views'])} 个视图 → {OUT_DIR_REL}/{ns.asset}/")
    for v in record["views"]:
        print(f"  - {v['view']}: {v['path']} ({v['size'][0]}x{v['size'][1]})")
    print(f"[ok] manifest: {path}")
    print("[next] 把 suggested_registry_patch.append_reference_images 补进 asset_registry 并刷新快照")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
