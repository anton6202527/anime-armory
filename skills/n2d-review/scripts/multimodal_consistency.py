#!/usr/bin/env python3
"""多模态视觉语义/道具漂移机检（P2）。

第一版不引入联网模型下载：用本地图片视觉指纹（RGB 直方图 + dHash）作为可复现 embedding，
按 `01_分镜出图.md` 的参考资产分组，检查同一场景/道具/法宝/特效在多镜里是否出现视觉离群。

后续若接 CLIP/DINO/SAM，可在 `_image_embedding` 处替换或追加更强 embedding；输出结构保持稳定。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import identity_registry_path  # noqa: E402

import face_consistency as fc  # 复用 fallback is_character_asset / cosine

KIND = "n2d_multimodal_consistency_report"
VERSION = 1
DEFAULT_FACTOR = 1.8
DEFAULT_FLOOR = 0.10


def _probe_pillow() -> bool:
    try:
        import PIL  # noqa
        return True
    except Exception:
        return False


def median(xs: Sequence[float]) -> float:
    s = sorted(xs)
    if not s:
        return 0.0
    m = len(s) // 2
    return s[m] if len(s) % 2 else (s[m - 1] + s[m]) / 2.0


def is_outlier(value: float, group_median: float, factor: float = DEFAULT_FACTOR,
               floor: float = DEFAULT_FLOOR) -> bool:
    return value > group_median * factor and value > floor


def dhash_bits(gray: Sequence[Sequence[float]]) -> List[float]:
    bits: List[float] = []
    for row in gray:
        for i in range(len(row) - 1):
            bits.append(1.0 if row[i] < row[i + 1] else 0.0)
    return bits


def l2_normalize(vec: Sequence[float]) -> List[float]:
    n = math.sqrt(sum(v * v for v in vec))
    if n <= 0:
        return [0.0 for _ in vec]
    return [float(v) / n for v in vec]


def image_embedding(path: str) -> Optional[List[float]]:
    """本地可复现视觉 embedding：RGB 4^3 直方图 + 64 位 dHash。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("RGB")
        small = im.copy()
        small.thumbnail((96, 96))
        hist = [0.0] * 64
        px = list(small.getdata())
        for r, g, b in px:
            ri, gi, bi = r // 64, g // 64, b // 64
            hist[int(ri) * 16 + int(gi) * 4 + int(bi)] += 1.0
        total = len(px) or 1
        hist = [v / total for v in hist]
        gray_im = im.convert("L").resize((9, 8))
        vals = list(gray_im.getdata())
        gray = [[float(vals[y * 9 + x]) for x in range(9)] for y in range(8)]
        bits = dhash_bits(gray)
        return l2_normalize(hist + bits)
    except Exception:
        return None


def split_blocks(text: str) -> List[Dict[str, str]]:
    blocks: List[Dict[str, str]] = []
    cur = None
    lines: List[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if cur is not None:
                blocks.append({"heading": cur, "body": "\n".join(lines)})
            cur = line[3:].strip()
            lines = [line]
        elif cur is not None:
            lines.append(line)
    if cur is not None:
        blocks.append({"heading": cur, "body": "\n".join(lines)})
    return blocks


def normalize_asset(name: str) -> str:
    s = str(name).strip().replace("\\", "/").split("/")[-1]
    if s.lower().endswith(".png"):
        s = s[:-4]
    if s.startswith("定妆_"):
        s = s[len("定妆_"):]
    return re.sub(r"_(侧|背|半身|全身|三视图|设定表|表情)$", "", s)


def target_from_block(root: str, ep: str, block: Dict[str, str]) -> Optional[str]:
    text = block["body"]
    # 优先取目标存档/目标行。
    m = re.search(r"(?:目标存档|目标)\s*[：:]\s*`?([^`\n]+?\.png)`?", text)
    if m:
        return resolve_image_path(root, ep, m.group(1).strip())
    # 兜底取出图路径里看起来不像参考定妆的 PNG。
    for p in re.findall(r"出图/[^`\s，。、,）)]+?\.png", text):
        if "/共享/" not in p and "/common/" not in p and "定妆_" not in p:
            return resolve_image_path(root, ep, p)
    # 再兜底按标题 Clip/镜头 glob。
    m = re.search(r"Clip\s*([0-9]+)", block["heading"], re.I)
    key = f"Clip_{int(m.group(1)):02d}" if m else None
    if not key:
        m = re.search(r"镜头\s*([0-9]+)", block["heading"])
        key = f"镜头{int(m.group(1))}" if m else None
    if key:
        matches = glob.glob(os.path.join(root, "出图", ep, "图片", key + "*.png"))
        matches += glob.glob(os.path.join(root, "出图", ep, key + "*.png"))
        if matches:
            return sorted(matches)[0]
    return None


def resolve_image_path(root: str, ep: str, value: str) -> Optional[str]:
    v = value.strip().strip("`").replace("\\", "/")
    cands = []
    if os.path.isabs(v):
        cands.append(v)
    cands.append(os.path.join(root, v))
    cands.append(os.path.join(root, "出图", ep, "图片", os.path.basename(v)))
    cands.append(os.path.join(root, "出图", ep, os.path.basename(v)))
    cands.append(os.path.join(root, "出图", "共享", "图片", os.path.basename(v)))
    cands.append(os.path.join(root, "出图", "common", "图片", os.path.basename(v)))
    for c in cands:
        if os.path.isfile(c):
            return c
    return cands[0] if cands else None


def refs_from_block(block: Dict[str, str]) -> List[str]:
    refs = []
    # 贪婪匹配到分隔符为止再交 normalize_asset 剥 .png；惰性 `+?` 会只捕获首字（定妆_法宝血玉 → 法）
    for raw in re.findall(r"定妆_([^`\s，。、,）)]+)", block["body"]):
        asset = normalize_asset(raw)
        if asset and asset not in refs:
            refs.append(asset)
    return refs


def identity_character_assets(root: str) -> List[str]:
    """Return character asset keys from identity_registry.

    When the registry exists it is the authoritative character set.  Anything
    referenced by image prompts but absent from this set is treated as a
    non-character visual asset for P2 grouping.
    """
    path = identity_registry_path(root)
    if not os.path.isfile(path):
        return []
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    names: List[str] = []

    def add(value: object) -> None:
        name = normalize_asset(str(value or ""))
        if name and name not in names:
            names.append(name)

    chars = data.get("characters") if isinstance(data, dict) else None
    if not isinstance(chars, list):
        return names
    for char in chars:
        if not isinstance(char, dict):
            continue
        for key in ("name", "asset_key", "character_id", "id"):
            add(char.get(key))
        forms = char.get("forms")
        if isinstance(forms, list):
            for form in forms:
                if not isinstance(form, dict):
                    continue
                for key in ("asset_key", "name", "character_id", "id"):
                    add(form.get(key))
                refs = form.get("reference_group")
                if isinstance(refs, dict):
                    for rel in refs.values():
                        add(rel)
    return names


def non_character_refs(root: str, refs: Sequence[str], character_assets: Sequence[str]) -> List[str]:
    char_set = {normalize_asset(name) for name in character_assets if normalize_asset(name)}
    out: List[str] = []
    for ref in refs:
        asset = normalize_asset(ref)
        is_char = asset in char_set if char_set else fc.is_character_asset(asset)
        if not is_char and asset not in out:
            out.append(asset)
    return out


def analyze(root: str, ep: str, factor: float = DEFAULT_FACTOR, floor: float = DEFAULT_FLOOR) -> dict:
    res = {
        "kind": KIND,
        "version": VERSION,
        "root": root.rstrip("/"),
        "episode": ep,
        "available": _probe_pillow(),
        "embedding_backend": "rgb_hist+dhash",
        "groups": {},
        "shots": [],
        "verdicts": [],
        "notes": [],
    }
    if not res["available"]:
        res["notes"].append("多模态一致性已跳过（未装 Pillow）；后续可接 CLIP/DINO/SAM。")
        return res
    p = os.path.join(root.rstrip("/"), "出图", ep, "prompt", "01_分镜出图.md")
    if not os.path.isfile(p):
        res["notes"].append("缺出图分镜 prompt，无法按参考资产分组。")
        return res
    text = open(p, encoding="utf-8").read()
    rows = []
    character_assets = identity_character_assets(root.rstrip("/"))
    if character_assets:
        res["character_asset_source"] = "identity_registry"
        res["character_assets"] = character_assets
    else:
        res["character_asset_source"] = "fallback_keyword_heuristic"
    for block in split_blocks(text):
        target = target_from_block(root.rstrip("/"), ep, block)
        refs = refs_from_block(block)
        non_chars = non_character_refs(root.rstrip("/"), refs, character_assets)
        if target and os.path.isfile(target):
            rows.append({"heading": block["heading"], "target": target, "assets": non_chars})

    groups: Dict[str, List[Dict[str, str]]] = {}
    for row in rows:
        for asset in row["assets"]:
            groups.setdefault(asset, []).append(row)

    for asset, items in sorted(groups.items()):
        if len(items) < 3:
            res["groups"][asset] = {"shots": len(items), "skipped": "组<3镜"}
            continue
        embeds: Dict[str, List[float]] = {}
        labels: Dict[str, str] = {}
        for item in items:
            emb = image_embedding(item["target"])
            if emb is not None:
                key = os.path.basename(item["target"])
                embeds[key] = emb
                labels[key] = item["heading"]
        if len(embeds) < 3:
            res["groups"][asset] = {"shots": len(embeds), "skipped": "可读图<3"}
            continue
        names = list(embeds)
        avg_dist = {}
        for name in names:
            ds = [1.0 - fc.cosine(embeds[name], embeds[other]) for other in names if other != name]
            avg_dist[name] = sum(ds) / len(ds)
        gmed = median(list(avg_dist.values()))
        res["groups"][asset] = {"shots": len(names), "median_dist": round(gmed, 3)}
        for name in names:
            if is_outlier(avg_dist[name], gmed, factor, floor):
                res["shots"].append({
                    "png": name,
                    "heading": labels.get(name, ""),
                    "asset": asset,
                    "avg_dist": round(avg_dist[name], 3),
                    "group_median": round(gmed, 3),
                    "verdict": "warn",
                    "message": f"`{asset}` 参考组内视觉 embedding 离群，疑似道具/场景/法宝语义漂移。",
                })
    res["verdicts"] = [s["verdict"] for s in res["shots"]]
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--factor", type=float, default=DEFAULT_FACTOR)
    ap.add_argument("--floor", type=float, default=DEFAULT_FLOOR)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root, ns.episode, ns.factor, ns.floor)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"=== 多模态视觉语义/道具漂移（P2）：{ns.root} {ns.episode} ===")
    for note in res["notes"]:
        print("ℹ️ " + note)
    for s in res["shots"]:
        print(f"⚠️ {s['png']} · {s['asset']} dist {s['avg_dist']} ≫ 组中位 {s['group_median']}：{s['message']}")
    if not res["shots"]:
        print("✅ 未发现同一参考资产组内视觉 embedding 离群。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
