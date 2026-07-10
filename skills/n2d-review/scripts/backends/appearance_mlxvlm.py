#!/usr/bin/env python3
"""VAP 外观判官 batch 后端 —— MLX-VLM（Apple Silicon 原生 4-bit，在 n2dvlm conda 环境跑）。

读 appearance_judge_runner 产出的 manifest（`pairs:[{character,shot,reference,shot_image}]`），
对每对（定妆参考帧 ↔ 本集出场帧）问 VLM「是否同一角色 + 外观相似度」，就地把 warn/block 判定写进
manifest 的 `findings` 并覆写。VLM 只加载一次（batch）。

用法（由 appearance_judge_runner 通过 N2D_APPEARANCE_BATCH_CMD 调起）：
    conda run -n n2dvlm python backends/appearance_mlxvlm.py <manifest.json>

环境变量：
    N2D_VLM_MODEL          默认 mlx-community/Qwen2.5-VL-3B-Instruct-4bit（16GB 内存安全；
                           内存富裕可换 mlx-community/Qwen2.5-VL-7B-Instruct-4bit 提质）
    N2D_APPEARANCE_WARN_FLOOR / N2D_APPEARANCE_BLOCK_FLOOR  相似度→verdict floor（0.7 / 0.5）
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

PARENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)
import detector_reliability  # noqa: E402

MODEL = os.environ.get("N2D_VLM_MODEL", "mlx-community/Qwen2.5-VL-3B-Instruct-4bit")
WARN_FLOOR = float(os.environ.get("N2D_APPEARANCE_WARN_FLOOR", "0.7"))
BLOCK_FLOOR = float(os.environ.get("N2D_APPEARANCE_BLOCK_FLOOR", "0.5"))

PROMPT = (
    "你是动漫角色一致性审核员。第一张是角色「{cid}」的定妆参考图，第二张是同一角色在某镜头里的画面。"
    "判断两张图是否同一个角色（脸型/发型/发饰/服装/气质），给外观相似度 0~1 与结论。"
    "只输出一行 JSON，不要多余文字："
    '{{"similarity": 0.0-1.0, "verdict": "ok|warn|block", "message": "简述差异或一致点"}}'
)


def _extract_json(text: str) -> Optional[dict]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _verdict_from(res: Optional[dict]) -> Optional[Dict[str, Any]]:
    if not isinstance(res, dict):
        return None
    sim = res.get("similarity")
    verdict = str(res.get("verdict") or "").lower()
    if verdict not in ("ok", "warn", "block") and isinstance(sim, (int, float)):
        verdict = "block" if sim < BLOCK_FLOOR else "warn" if sim < WARN_FLOOR else "ok"
    if verdict not in ("ok", "warn", "block"):
        return None
    governed = detector_reliability.govern_verdict(verdict, detector_kind="vlm")
    return {"verdict": governed["verdict"], "vlm_raw_verdict": verdict,
            "similarity": sim, "message": res.get("message") or "",
            "needs_human_confirmation": governed["human_confirmation_required"]}


def main(argv: List[str]) -> int:
    if not argv:
        print("usage: appearance_mlxvlm.py <manifest.json>", file=sys.stderr)
        return 2
    path = argv[0]
    with open(path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    root = manifest.get("root") or os.path.dirname(os.path.dirname(path))
    pairs = manifest.get("pairs") or []
    if not pairs:
        manifest["findings"] = []
        manifest["judge"] = f"mlx-vlm:{MODEL}(no-pairs)"
        _dump(path, manifest)
        return 0

    from mlx_vlm import generate, load
    from mlx_vlm.prompt_utils import apply_chat_template
    from mlx_vlm.utils import load_config

    model, processor = load(MODEL)
    config = load_config(MODEL)
    findings: List[Dict[str, Any]] = []
    judged = 0
    for pair in pairs:
        ref, shot_img = pair.get("reference"), pair.get("shot_image")
        if not ref or not shot_img:
            continue
        ref_abs = ref if os.path.isabs(ref) else os.path.join(root, ref)
        shot_abs = shot_img if os.path.isabs(shot_img) else os.path.join(root, shot_img)
        if not (os.path.isfile(ref_abs) and os.path.isfile(shot_abs)):
            continue
        prompt = PROMPT.format(cid=pair.get("character") or "角色")
        try:
            formatted = apply_chat_template(processor, config, prompt, num_images=2)
            out = generate(model, processor, formatted, image=[ref_abs, shot_abs], verbose=False)
            text = out.text if hasattr(out, "text") else str(out)
            verdict = _verdict_from(_extract_json(text))
        except Exception as exc:  # 单对失败不拖垮整批
            print(f"[mlx-vlm][warn] {pair.get('shot')} {pair.get('character')}: {exc}", file=sys.stderr)
            continue
        judged += 1
        if verdict and verdict["verdict"] in ("warn", "block"):
            findings.append({
                "shot": pair.get("shot"), "character": pair.get("character"),
                "verdict": verdict["verdict"], "similarity": verdict.get("similarity"),
                "vlm_raw_verdict": verdict.get("vlm_raw_verdict"),
                "needs_human_confirmation": verdict.get("needs_human_confirmation"),
                "message": verdict.get("message") or "外观判官判定与定妆不一致",
            })
    manifest["findings"] = findings
    manifest["judge"] = f"mlx-vlm:{MODEL}"
    manifest["pairs_judged"] = judged
    _dump(path, manifest)
    print(f"mlx-vlm: pairs_judged={judged} findings={len(findings)} model={MODEL}")
    return 0


def _dump(path: str, manifest: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
