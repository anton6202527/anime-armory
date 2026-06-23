#!/usr/bin/env python3
"""OCR1 图中文字校验 batch 后端 —— EasyOCR（中英，在 n2docr conda 环境跑）。

读 text_render_runner 产出的 manifest（`probes:[{shot,image,expected_text}]`），用 EasyOCR 实读每帧
渲染文字，与预期做归一相似度比对，把不符的写进 manifest 的 `findings` 并覆写。OCR 只加载一次（batch）。

判级：① 预期含数字且 OCR 读出的数字与预期不一致 → block（系统面板数值错=硬伤）；
      ② 否则按归一相似度：< block_floor → block，< warn_floor → warn，其余 ok。

用法（由 text_render_runner 通过 N2D_TEXT_OCR_BATCH_CMD 调起）：
    conda run -n n2docr python backends/text_ocr_easyocr.py <manifest.json>

环境变量：
    N2D_OCR_LANGS        默认 "ch_sim,en"
    N2D_OCR_WARN_FLOOR   默认 0.8   N2D_OCR_BLOCK_FLOOR 默认 0.5
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
from typing import Any, Dict, List

LANGS = os.environ.get("N2D_OCR_LANGS", "ch_sim,en").split(",")
WARN_FLOOR = float(os.environ.get("N2D_OCR_WARN_FLOOR", "0.8"))
BLOCK_FLOOR = float(os.environ.get("N2D_OCR_BLOCK_FLOOR", "0.5"))

_PUNCT = re.compile(r"[\s　，。、；：:,.;！!？?\-—_/|]+")


def _norm(s: str) -> str:
    return _PUNCT.sub("", str(s or "")).lower()


def _digits(s: str) -> List[str]:
    return re.findall(r"\d+", str(s or ""))


def main(argv: List[str]) -> int:
    if not argv:
        print("usage: text_ocr_easyocr.py <manifest.json>", file=sys.stderr)
        return 2
    path = argv[0]
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    root = manifest.get("root") or os.path.dirname(os.path.dirname(path))
    probes = manifest.get("probes") or []
    if not probes:
        manifest["findings"] = []
        manifest["ocr"] = f"easyocr:{'+'.join(LANGS)}(no-probes)"
        _dump(path, manifest)
        return 0

    import easyocr
    reader = easyocr.Reader(LANGS, gpu=False, verbose=False)
    findings: List[Dict[str, Any]] = []
    checked = 0
    for probe in probes:
        image_rel, expected = probe.get("image"), probe.get("expected_text")
        if not image_rel or not expected:
            continue
        image_abs = image_rel if os.path.isabs(image_rel) else os.path.join(root, image_rel)
        if not os.path.isfile(image_abs):
            continue
        try:
            chunks = reader.readtext(image_abs, detail=0, paragraph=True)
            ocr_text = " ".join(chunks) if isinstance(chunks, list) else str(chunks)
        except Exception as exc:  # 单帧失败不拖垮整批
            print(f"[easyocr][warn] {probe.get('shot')} {image_rel}: {exc}", file=sys.stderr)
            continue
        checked += 1
        ne, no = _norm(expected), _norm(ocr_text)
        sim = round(difflib.SequenceMatcher(None, ne, no).ratio(), 3)
        exp_d, ocr_d = _digits(expected), _digits(ocr_text)
        digit_mismatch = bool(exp_d) and exp_d != ocr_d
        verdict = None
        if digit_mismatch:
            verdict = "block"
        elif sim < BLOCK_FLOOR:
            verdict = "block"
        elif sim < WARN_FLOOR:
            verdict = "warn"
        if verdict:
            findings.append({
                "shot": probe.get("shot"), "verdict": verdict,
                "expected": expected, "ocr_text": ocr_text, "similarity": sim,
                "message": (f"图中数字渲染错误：预期数字 {exp_d} OCR 实读 {ocr_d}"
                            if digit_mismatch else
                            f"图中文字渲染偏离：预期「{expected}」OCR 实读「{ocr_text}」"),
            })
    manifest["findings"] = findings
    manifest["ocr"] = f"easyocr:{'+'.join(LANGS)}"
    manifest["frames_checked"] = checked
    _dump(path, manifest)
    print(f"easyocr: frames_checked={checked} findings={len(findings)}")
    return 0


def _dump(path: str, manifest: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
