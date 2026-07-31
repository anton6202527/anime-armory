#!/usr/bin/env python3
"""O3V 在场检测 batch 后端 —— OWLv2 开放词表检测（在 facefusion conda 环境跑）。

读 object_presence_runner 产出的 manifest（`probes:[{shot,image,expected_assets:[{asset,phrase}]}]`），
对每帧用 OWLv2 做开放词表检测，判每个 expected 对象是否在场；expected 但缺席 → 写一条 block finding。
就地覆写 manifest 的 `findings`。模型只加载一次（batch）。

用法（由 object_presence_runner 通过 N2D_PRESENCE_BATCH_CMD 调起）：
    conda run -n facefusion python backends/presence_owlv2.py <manifest.json>

环境变量：
    N2D_OWLV2_MODEL      默认 google/owlv2-base-patch16-ensemble
    N2D_OWLV2_THRESHOLD  在场判定分数阈值，默认 0.10（OWLv2 分数偏低，按风格/项目用 golden set 标定）
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

MODEL = os.environ.get("N2D_OWLV2_MODEL", "google/owlv2-base-patch16-ensemble")
THRESHOLD = float(os.environ.get("N2D_OWLV2_THRESHOLD", "0.10"))


def _load():
    import torch
    from transformers import Owlv2ForObjectDetection, Owlv2Processor
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    proc = Owlv2Processor.from_pretrained(MODEL)
    model = Owlv2ForObjectDetection.from_pretrained(MODEL).to(device).eval()
    return proc, model, device, torch


def _max_scores(proc, model, device, torch, image, phrases: List[str]) -> Dict[str, float]:
    # OWLv2 text encoder has a short position limit (16 for the bundled base model).
    # Chinese scene/object labels can tokenize longer than that; truncate per model
    # contract instead of failing the whole frame.
    max_len = int(getattr(getattr(model, "config", None), "max_position_embeddings", 16) or 16)
    text_cfg = getattr(getattr(model, "config", None), "text_config", None)
    max_len = int(getattr(text_cfg, "max_position_embeddings", max_len) or max_len)
    inputs = proc(
        text=[phrases],
        images=image,
        return_tensors="pt",
        truncation=True,
        max_length=max_len,
    ).to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    target = torch.tensor([image.size[::-1]]).to(device)
    res = proc.post_process_object_detection(outputs, target_sizes=target, threshold=0.0)[0]
    best = {p: 0.0 for p in phrases}
    for score, label in zip(res["scores"].tolist(), res["labels"].tolist()):
        p = phrases[label]
        if score > best[p]:
            best[p] = float(score)
    return best


def asset_verdict(asset: Dict[str, Any], conf: float, threshold: float) -> Dict[str, Any]:
    """单个 expected_asset 的判定 → finding 或 None。纯函数·可测。

    向后兼容：默认 `expect="present"`（旧 manifest 无此字段 → 行为不变）：在场分 < 阈值 = 缺席 block。
    新增 `expect="absent"`（状态像素契约用）：在场分 ≥ 阈值 = 此处不该出现却出现 = warn（提前泄露疑似）。
    可选透传字段 char/state/kind（域内消费端用），通用 object/marks manifest 不带 → 不影响。"""
    expect = str(asset.get("expect") or "present")
    phrase = str(asset.get("phrase") or asset.get("asset"))
    present = conf >= threshold
    f: Optional[Dict[str, Any]] = None
    if expect == "absent":
        if present:
            f = {"asset": asset.get("asset"), "expected": False, "present": True,
                 "severity": "warn", "confidence": conf,
                 "message": f"OWLv2 在帧中检出「{phrase}」(max={conf} ≥ {threshold})，但此处不应出现"}
    else:
        if not present:
            f = {"asset": asset.get("asset"), "expected": True, "present": False,
                 "severity": "block", "confidence": conf,
                 "message": f"OWLv2 未在帧中检出「{phrase}」(max={conf} < {threshold})"}
    if f is not None:
        for k in ("char", "state", "kind"):
            if asset.get(k) is not None:
                f[k] = asset[k]
    return f


def main(argv: List[str]) -> int:
    if not argv:
        print("usage: presence_owlv2.py <manifest.json>", file=sys.stderr)
        return 2
    path = argv[0]
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    root = manifest.get("root") or os.path.dirname(os.path.dirname(path))
    probes = manifest.get("probes") or []
    if not probes:
        manifest["findings"] = []
        manifest["detector"] = f"owlv2:{MODEL}(no-probes)"
        _dump(path, manifest)
        return 0

    from PIL import Image
    proc, model, device, torch = _load()
    findings: List[Dict[str, Any]] = []
    checked = 0
    for probe in probes:
        image_rel = probe.get("image")
        if not image_rel:
            continue
        image_abs = image_rel if os.path.isabs(image_rel) else os.path.join(root, image_rel)
        if not os.path.isfile(image_abs):
            continue
        assets = probe.get("expected_assets") or []
        phrases = [str(a.get("phrase") or a.get("asset")) for a in assets]
        if not phrases:
            continue
        try:
            image = Image.open(image_abs).convert("RGB")
            scores = _max_scores(proc, model, device, torch, image, phrases)
        except Exception as exc:  # 单帧失败不拖垮整批
            print(f"[owlv2][warn] {probe.get('shot')} {image_rel}: {exc}", file=sys.stderr)
            continue
        checked += 1
        for a in assets:
            phrase = str(a.get("phrase") or a.get("asset"))
            conf = round(scores.get(phrase, 0.0), 4)
            f = asset_verdict(a, conf, THRESHOLD)
            if f is not None:
                f["shot"] = probe.get("shot")
                findings.append(f)
    manifest["findings"] = findings
    manifest["detector"] = f"owlv2:{MODEL}"
    manifest["detector_threshold"] = THRESHOLD
    manifest["frames_checked"] = checked
    _dump(path, manifest)
    print(f"owlv2: frames_checked={checked} findings={len(findings)} threshold={THRESHOLD}")
    return 0


def _dump(path: str, manifest: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
