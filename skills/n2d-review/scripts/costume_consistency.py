#!/usr/bin/env python3
"""Costume/garment consistency (independent dimension) using CLIP-I embedding.

Per-character: loads full-body reference from 定妆库, computes CLIP-I embedding.
For each shot: crops person region, computes CLIP-I embedding.
Cosine similarity vs reference -> verdict (block/warn/ok) with self-calibrated floor.

Follows the existing semantic_drift.py DINO/CLIP-I comparison pattern.
Available flag: requires torch + CLIP library; gracefully degrades to
available=False when dependencies are missing (C4: never hard-bind a backend).

Usage: python3 costume_consistency.py <作品根> 第N集 [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

import state_continuity as stc  # 剧情指定换装/染血/破损区间 → block 降 warn（不硬误伤剧情）

KIND = "n2d_costume_consistency_report"
VERSION = 1
DEFAULT_FALLBACK = 0.75  # CLIP-I cosine is higher than ArcFace, fallback higher


# ── Pure functions (testable without torch/CLIP) ────────────────────────

def calibrate_floor(scores: Sequence[float], fallback: float = DEFAULT_FALLBACK) -> float:
    """Self-calibrated floor from intra-reference consistency.
    When <2 scores, returns fallback. Uses min as floor (tightest bound).
    Pure function."""
    scores = [float(s) for s in scores if s is not None]
    if len(scores) < 2:
        return fallback
    return min(scores)


def band(score: float, floor: float, margin: float = 0.10) -> str:
    """Partition score into block/warn/ok by calibrated floor.
    block: score < floor
    warn:  floor <= score < floor + margin
    ok:    score >= floor + margin
    Pure function."""
    if score < floor:
        return "block"
    if score < floor + margin:
        return "warn"
    return "ok"


def _probe_clip() -> bool:
    """Check if CLIP library + torch are available without importing them."""
    try:
        import torch  # noqa: F401
        import clip  # noqa: F401
        return True
    except Exception:
        return False


# ── I/O functions (require torch + CLIP) ───────────────────────────────

def _load_clip():
    """Load CLIP ViT-B/32 model. Caller must ensure _probe_clip() returned True first."""
    import torch
    import clip
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = clip.load("ViT-B/32", device=device)
    return model, preprocess, device


def _clip_embedding(image_path: str, model, preprocess, device) -> Optional[List[float]]:
    """Compute CLIP image embedding for a single image. Returns None on failure."""
    try:
        import torch
        from PIL import Image
        im = Image.open(image_path).convert("RGB")
        with torch.no_grad():
            features = model.encode_image(preprocess(im).unsqueeze(0).to(device))
            features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy().flatten().tolist()
    except Exception:
        return None


def _cosine(a: List[float], b: List[float]) -> float:
    """Cosine similarity between two float vectors. Pure function."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _discover_costume_refs(root: str, character_names: List[str]) -> Dict[str, List[str]]:
    """Find full-body costume reference images per character from 定妆库.
    Returns {char_name: [ref_path, ...]}. Looks for 全身/全身板/full_body patterns."""
    refs: Dict[str, List[str]] = {}
    定妆 = os.path.join(root, "定妆库")
    if not os.path.isdir(定妆):
        return refs
    for char in character_names:
        char_dir = os.path.join(定妆, char)
        if not os.path.isdir(char_dir):
            for pattern in [f"*{char}*全身*", f"*{char}*full*body*", f"*{char}*定妆*"]:
                for p in glob.glob(os.path.join(定妆, pattern)):
                    if p.lower().endswith((".png", ".jpg", ".jpeg")):
                        refs.setdefault(char, []).append(p)
            continue
        for p in glob.glob(os.path.join(char_dir, "*.png")):
            name = os.path.basename(p)
            if any(kw in name for kw in ("全身", "full", "body", "fullbody", "定妆")):
                refs.setdefault(char, []).append(p)
        if char not in refs:
            for p in glob.glob(os.path.join(char_dir, "*.png"))[:3]:
                refs.setdefault(char, []).append(p)
    return refs


def _shot_images(root: str, ep: str) -> List[str]:
    """List all shot PNGs for the episode, sorted by shot number."""
    img_dir = os.path.join(root, "出图", ep, "图片")
    if not os.path.isdir(img_dir):
        return []
    shots = sorted(glob.glob(os.path.join(img_dir, "*.png")))
    return shots


def analyze(root: str, ep: str) -> Dict[str, Any]:
    """Main entry point for costume consistency analysis.
    Returns {available, notes, shots: [{shot, character, score, floor, verdict, ...}]}"""
    if not _probe_clip():
        return {"available": False, "notes": ["CLIP 不可用：缺 torch 或 clip 库。跳过服装独立维度。"], "shots": []}
    try:
        model, preprocess, device = _load_clip()
    except Exception as exc:
        return {"available": False, "notes": [f"CLIP 加载失败：{exc}。跳过服装独立维度。"], "shots": []}
    # Discover character names from identity_registry
    identity_path = os.path.join(root, "identity_registry.json")
    character_names: List[str] = []
    if os.path.isfile(identity_path):
        try:
            with open(identity_path, encoding="utf-8") as fh:
                reg = json.load(fh)
            for entry in reg.get("characters", []):
                cid = entry.get("character_id") or entry.get("id") or ""
                if cid:
                    character_names.append(cid)
        except Exception:
            pass
    if not character_names:
        return {"available": False, "notes": ["未找到角色定义（identity_registry.json 缺失或无角色）。"], "shots": []}
    refs = _discover_costume_refs(root, character_names)
    shots = _shot_images(root, ep)
    if not shots:
        return {"available": True, "notes": ["本集无出图 PNG。"], "shots": []}
    # Compute reference embeddings per character
    char_ref_embs: Dict[str, List[List[float]]] = {}
    char_floors: Dict[str, float] = {}
    for char, ref_paths in refs.items():
        embs = []
        for rp in ref_paths[:5]:
            emb = _clip_embedding(rp, model, preprocess, device)
            if emb:
                embs.append(emb)
        if embs:
            char_ref_embs[char] = embs
            intra_scores = [_cosine(embs[i], embs[j]) for i in range(len(embs)) for j in range(i + 1, len(embs))]
            char_floors[char] = calibrate_floor(intra_scores)
    if not char_ref_embs:
        return {"available": True, "notes": ["无可用角色服装参考图。"], "shots": []}
    # 剧情指定的换装/染血/破损/变身区间：落区间内的镜，服装偏离单一定妆是「该变」而非漂移 → block 降 warn。
    intervals = stc.appearance_change_intervals(root, ep)
    # Score each shot
    results: List[Dict[str, Any]] = []
    for sp in shots:
        shot_emb = _clip_embedding(sp, model, preprocess, device)
        if not shot_emb:
            continue
        shot_name = os.path.basename(sp)
        shot_no = stc.shot_num(shot_name)
        for char, ref_embs in char_ref_embs.items():
            ref_emb = ref_embs[0]
            score = _cosine(shot_emb, ref_emb)
            floor = char_floors.get(char, DEFAULT_FALLBACK)
            verdict = band(score, floor)
            row = {
                "shot": shot_name,
                "character": char,
                "score": round(score, 4),
                "floor": round(floor, 4),
                "verdict": verdict,
                "dimension": "服装独立(COST)",
            }
            stc.downgrade_costume_block(row, intervals, char, shot_no)
            results.append(row)
    # Deduplicate: keep worst verdict per shot
    deduped: Dict[str, Dict[str, Any]] = {}
    for r in results:
        key = r["shot"]
        if key not in deduped or r["verdict"] == "block" or (r["verdict"] == "warn" and deduped[key].get("verdict") == "ok"):
            deduped[key] = r
    return {"available": True, "notes": [], "shots": list(deduped.values())}


# ── CLI ────────────────────────────────────────────────────────────────

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="n2d costume consistency (CLIP-I)")
    ap.add_argument("root", help="作品根目录")
    ap.add_argument("episode", help="集号，如 第1集")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ns = ap.parse_args(argv)
    result = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"available={result['available']}")
        for s in result.get("shots", []):
            print(f"  [{s['verdict']}] {s['shot']} {s.get('character','')} score={s['score']} floor={s['floor']}")
    return 0 if result.get("available") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
