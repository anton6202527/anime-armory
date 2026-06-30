#!/usr/bin/env python3
"""场景几何 batch 后端 —— OWLv2 门窗**侧位**检测（在 facefusion conda 环境跑）。

读 scene_geometry_conformance 产出的 manifest（`probes:[{shot,scene,image,expected_openings:[{label,phrase,expected_h}]}]`），
对每帧用 OWLv2 检测门/窗/开口短语，取最高分框的**质心横坐标**判画面侧（left/center/right），
就地回填 `detected: {scene: {label: [side, ...]}}`（场景级聚合在 conformance.aggregate 做）。模型只加载一次。

与 presence_owlv2 的区别：那个只回是否在场（max score）；这个还要框的**位置**（门窗在哪侧），
因为 floor_plan 的核对靶是「门应在画左」，不是「门在不在」。

用法（由 scene_geometry_conformance 经 N2D_SCENE_GEOMETRY_BATCH_CMD 调起）：
    conda run -n facefusion python backends/scene_geometry_owlv2.py <manifest.json>

环境变量：
    N2D_OWLV2_MODEL      默认 google/owlv2-base-patch16-ensemble
    N2D_OWLV2_THRESHOLD  在场判定分数阈值，默认 0.10
    N2D_GEOM_DEADZONE    质心距中线 < 此（归一）→ center（不判左右），默认 0.12
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from typing import Any, Dict, List

MODEL = os.environ.get("N2D_OWLV2_MODEL", "google/owlv2-base-patch16-ensemble")
THRESHOLD = float(os.environ.get("N2D_OWLV2_THRESHOLD", "0.10"))
DEADZONE = float(os.environ.get("N2D_GEOM_DEADZONE", "0.12"))


def _load():
    import torch
    from transformers import Owlv2ForObjectDetection, Owlv2Processor
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    proc = Owlv2Processor.from_pretrained(MODEL)
    model = Owlv2ForObjectDetection.from_pretrained(MODEL).to(device).eval()
    return proc, model, device, torch


def _side(cx_norm: float) -> str:
    if cx_norm < 0.5 - DEADZONE:
        return "left"
    if cx_norm > 0.5 + DEADZONE:
        return "right"
    return "center"


def _best_box_side(proc, model, device, torch, image, phrase: str) -> str:
    inputs = proc(text=[[phrase]], images=image, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    target = torch.tensor([image.size[::-1]]).to(device)
    res = proc.post_process_object_detection(outputs, target_sizes=target, threshold=THRESHOLD)[0]
    best_score, best_cx = 0.0, None
    W = float(image.size[0]) or 1.0
    for score, box in zip(res["scores"].tolist(), res["boxes"].tolist()):
        if score > best_score:
            best_score = score
            best_cx = (float(box[0]) + float(box[2])) / 2.0 / W  # 框中心归一横坐标
    if best_cx is None:
        return ""  # 未检出 → 空（conformance 视作该镜没这个结构）
    return _side(best_cx)


def run(manifest_path: str) -> int:
    with open(manifest_path, encoding="utf-8") as fh:
        manifest: Dict[str, Any] = json.load(fh)
    root = manifest.get("root") or os.path.dirname(os.path.dirname(manifest_path))
    proc, model, device, torch = _load()
    from PIL import Image
    detected: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
    for probe in manifest.get("probes", []):
        rel = probe.get("image")
        scene = str(probe.get("scene") or "")
        if not rel or not scene:
            continue
        abspath = rel if os.path.isabs(rel) else os.path.join(root, rel)
        if not os.path.isfile(abspath):
            continue
        try:
            image = Image.open(abspath).convert("RGB")
        except Exception as exc:
            print(f"[scene_geometry_owlv2][warn] {abspath}: {exc}", file=sys.stderr)
            continue
        for op in probe.get("expected_openings", []):
            label = str(op.get("label") or "")
            phrase = str(op.get("phrase") or label)
            side = _best_box_side(proc, model, device, torch, image, phrase)
            if side:
                detected[scene][label].append(side)
    manifest["detected"] = {s: dict(d) for s, d in detected.items()}
    manifest["geometry_backend"] = {"model": MODEL, "threshold": THRESHOLD, "deadzone": DEADZONE}
    tmp = manifest_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, manifest_path)
    print(f"✓ scene_geometry: {sum(len(v) for v in detected.values())} 场景门窗侧位 → {manifest_path}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: scene_geometry_owlv2.py <manifest.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(run(sys.argv[1]))
