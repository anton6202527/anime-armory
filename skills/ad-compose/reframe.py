#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多比例 reframe：把主片（如 16:9）重构成其它交付比例（9:16/1:1），算 ffmpeg crop/scale 滤镜。

广告多比例交付的核心：同一主片要出横/竖/方版。本脚本算从源比例到目标比例的中心裁切
（crop）或加边（pad）滤镜串，并支持按安全框留余量。自包含纯标准库 + 单测。

用法：
    python3 reframe.py --src 1920x1080 --target 9:16 --mode crop
    → 打印 ffmpeg -vf 滤镜串
"""
import argparse
import sys


def parse_aspect(s):
    """'9:16' 或 '1920x1080' → (w_ratio, h_ratio) 浮点比值。"""
    s = s.strip().lower().replace("x", ":")
    a, b = s.split(":")
    return float(a), float(b)


def aspect_value(s):
    w, h = parse_aspect(s)
    return w / h


def reframe_filter(src_wh, target_aspect, mode="crop", out_long=1920):
    """返回 ffmpeg -vf 滤镜串：把 src 分辨率 reframe 到 target 比例。

    mode=crop：中心裁切到目标比例（主体居中，最常用）。
    mode=pad ：保留全画，上下/左右加黑边（letterbox/pillarbox）。
    out_long：输出长边像素（短边按目标比例推）。
    """
    sw, sh = (int(x) for x in src_wh.lower().split("x"))
    ta = aspect_value(target_aspect)  # target w/h
    if ta >= 1:  # 横/方：长边=宽
        ow, oh = out_long, round(out_long / ta)
    else:        # 竖：长边=高
        oh, ow = out_long, round(out_long * ta)
    # 偶数化（H.264 要求）
    ow -= ow % 2
    oh -= oh % 2

    if mode == "crop":
        # 先放大覆盖目标框再中心裁切
        return (f"scale={ow}:{oh}:force_original_aspect_ratio=increase,"
                f"crop={ow}:{oh},setsar=1")
    elif mode == "pad":
        return (f"scale={ow}:{oh}:force_original_aspect_ratio=decrease,"
                f"pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:black,setsar=1")
    raise ValueError(f"unknown mode: {mode}")


def out_resolution(target_aspect, out_long=1920):
    ta = aspect_value(target_aspect)
    if ta >= 1:
        ow, oh = out_long, round(out_long / ta)
    else:
        oh, ow = out_long, round(out_long * ta)
    return (ow - ow % 2, oh - oh % 2)


def main():
    ap = argparse.ArgumentParser(description="多比例 reframe 滤镜计算")
    ap.add_argument("--src", required=True, help="源分辨率，如 1920x1080")
    ap.add_argument("--target", required=True, help="目标比例，如 9:16 / 1:1 / 16:9")
    ap.add_argument("--mode", default="crop", choices=["crop", "pad"])
    ap.add_argument("--out-long", type=int, default=1920)
    args = ap.parse_args()
    vf = reframe_filter(args.src, args.target, args.mode, args.out_long)
    ow, oh = out_resolution(args.target, args.out_long)
    print(f"# {args.src} → {args.target} ({args.mode})  输出 {ow}x{oh}")
    print(vf)
    print(f"\n# 示例：ffmpeg -i 成片_主片.mp4 -vf \"{vf}\" -c:a copy 多比例/成片_{args.target.replace(':','x')}.mp4")
    print("# crop 注意：主体/产品/字幕需在 action-safe 内，否则竖版会裁掉两侧主体（ad-image/ad-video 出图出视频时已留余量）")
    sys.exit(0)


if __name__ == "__main__":
    main()
