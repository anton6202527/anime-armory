#!/usr/bin/env python3
"""N2D_VLM_CMD 单图判官后端 —— MLX-VLM（Apple Silicon 原生 4-bit，在 n2dvlm conda 环境跑）。

对接 `n2d-image/scripts/vlm_verify.py` 的 fidelity-gate：它把每张渲染图 + 设定档 prompt 经
`N2D_VLM_CMD` 模板（占位 {image} {prompt}）调一条命令，期待 stdout 回判定 JSON
`{"match":bool,"confidence":0-1,"mismatches":[...],"reason":"..."}`。build_judge_prompt 已在
prompt 里把这个输出格式讲清，本后端只负责把单图 + prompt 喂给本地 Qwen2.5-VL 并把模型输出原样
打到 stdout（vlm_verify.parse_verdict 容忍 ```fence``` 和前后噪声、截取第一个{到最后一个}）。

与 appearance_mlxvlm.py 的区别：那个是 appearance_judge_runner 的**批量配对图**后端（输出
verdict/similarity）；本后端是 vlm_verify 的**单图设定核对**后端（输出 match/...），接口不同。

用法（经 N2D_VLM_CMD 调起）：
    conda run -n n2dvlm python <此脚本> --image {image} --prompt {prompt}

环境变量：
    N2D_VLM_MODEL   默认 mlx-community/Qwen2.5-VL-3B-Instruct-4bit（16GB 内存安全；
                    内存富裕换 mlx-community/Qwen2.5-VL-7B-Instruct-4bit 提质）
    N2D_VLM_MAX_TOKENS  默认 512
失败：非 0 退出码 + stderr（vlm_verify 见非 0 即跳过该图、不假报），绝不打污染 stdout 的噪声。
"""
from __future__ import annotations

import argparse
import os
import sys

MODEL = os.environ.get("N2D_VLM_MODEL", "mlx-community/Qwen2.5-VL-3B-Instruct-4bit")
MAX_TOKENS = int(os.environ.get("N2D_VLM_MAX_TOKENS", "512"))


def main(argv) -> int:
    ap = argparse.ArgumentParser(description="MLX-VLM single-image judge for N2D_VLM_CMD")
    ap.add_argument("--image", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--model", default=MODEL)
    ns = ap.parse_args(argv)

    if not os.path.isfile(ns.image):
        print(f"image not found: {ns.image}", file=sys.stderr)
        return 2

    try:
        from mlx_vlm import generate, load
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import load_config
    except Exception as exc:  # 不在 n2dvlm 环境 / 没装 mlx-vlm
        print(f"mlx-vlm unavailable: {exc}（请 conda run -n n2dvlm）", file=sys.stderr)
        return 3

    try:
        model, processor = load(ns.model)
        config = load_config(ns.model)
        formatted = apply_chat_template(processor, config, ns.prompt, num_images=1)
        out = generate(model, processor, formatted, image=[ns.image],
                       max_tokens=MAX_TOKENS, verbose=False)
        text = out.text if hasattr(out, "text") else str(out)
    except Exception as exc:
        print(f"mlx-vlm generate failed: {exc}", file=sys.stderr)
        return 4

    # 模型输出原样回 stdout（含判定 JSON）；vlm_verify.parse_verdict 负责截取/容错。
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
