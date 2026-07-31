#!/usr/bin/env python3
"""场景语义嵌入 batch 后端 —— DINOv2 全图嵌入（在装了 torch 的 conda 环境跑）。

读 scene_embed.py 产出的 manifest（`probes:[{shot,scene,image,embedding}]`），对每帧用 DINOv2 出
CLS 嵌入（L2 归一化），就地回填每个 probe 的 `embedding`。模型只加载一次（batch）。CLIP 同形可替。

为什么 DINOv2：自监督视觉特征对**几何/材质/布局**敏感（正是 HSV 色调直方图的盲区），且无需文本对齐，
适合「同一场景跨集是否还是同一空间」的判别——给 SCNX 跨集场景漂移补一条学习型指纹。

用法（由 scene_embed.py 经 N2D_SCENE_EMBED_BATCH_CMD 调起）：
    conda run -n facefusion python backends/scene_embed_dinov2.py <manifest.json>

环境变量：
    N2D_DINOV2_MODEL   默认 facebook/dinov2-base（small/large 可换，越大越准越慢）
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

MODEL = os.environ.get("N2D_DINOV2_MODEL", "facebook/dinov2-base")


def _load():
    import torch
    from transformers import AutoImageProcessor, AutoModel
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    proc = AutoImageProcessor.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL).to(device).eval()
    return proc, model, device, torch


def _embed(proc, model, device, torch, image) -> List[float]:
    inputs = proc(images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        out = model(**inputs)
    # CLS token（pooler_output 缺则取 last_hidden_state[:,0]）
    vec = getattr(out, "pooler_output", None)
    if vec is None:
        vec = out.last_hidden_state[:, 0]
    vec = vec[0].float()
    vec = vec / (vec.norm() + 1e-8)  # L2 归一化 → cosine 即点积
    return [round(float(x), 6) for x in vec.tolist()]


def run(manifest_path: str) -> int:
    with open(manifest_path, encoding="utf-8") as fh:
        manifest: Dict[str, Any] = json.load(fh)
    root = manifest.get("root") or os.path.dirname(os.path.dirname(manifest_path))
    proc, model, device, torch = _load()
    from PIL import Image
    cache: Dict[str, List[float]] = {}
    for probe in manifest.get("probes", []):
        rel = probe.get("image")
        if not rel:
            continue
        abspath = rel if os.path.isabs(rel) else os.path.join(root, rel)
        if not os.path.isfile(abspath):
            continue
        if abspath not in cache:
            try:
                cache[abspath] = _embed(proc, model, device, torch, Image.open(abspath).convert("RGB"))
            except Exception as exc:
                print(f"[scene_embed_dinov2][warn] {abspath}: {exc}", file=sys.stderr)
                continue
        probe["embedding"] = cache[abspath]
    manifest["embed_backend"] = {"model": MODEL, "dim": len(next(iter(cache.values()))) if cache else 0}
    tmp = manifest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, manifest_path)
    print(f"✓ scene_embed: {len(cache)} 帧嵌入（{MODEL}）→ {manifest_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: scene_embed_dinov2.py <manifest.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run(sys.argv[1]))
