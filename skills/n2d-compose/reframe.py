#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d 多比例 reframe：把一集成片母带（如竖屏 9:16）重构成其它交付比例（16:9/1:1），
算 ffmpeg crop/scale 滤镜，并可 `--render` 实际产出重构后的 MP4。

**语境差异（vendored fork·参照同仓另一条创作线的成熟 reframe 实现·不跨线 import）**：几何算法同构，但 n2d 短剧母带
  默认是**竖屏 9:16**（剧本/出图/出视频按竖屏构图，主体居中偏上），派生横屏/方版时中心裁切容易把
  上下信息裁掉——故横转更建议 `pad`（加边保全画）或带焦点 `--crop-x/--crop-y`。默认 `--src` 也按
  n2d 竖屏 `1080x1920`。

crop 默认中心裁切；可传 `--crop-x/--crop-y`（归一焦点 0..1，主体中心位置）把裁切窗对到主体上——
  不传焦点时退化为中心裁切，文案不再宣称「safe-area 感知」。自包含纯标准库 + pytest。

用法：
    python3 reframe.py --src 1080x1920 --target 16:9 --mode pad
    python3 reframe.py --src 1080x1920 --target 1:1 --crop-x 0.5 --crop-y 0.42
    python3 reframe.py --src 1080x1920 --target 16:9 --in 合成/第1集/成片_第1集_zh.mp4 --render
"""
import argparse
import os
import shutil
import subprocess
import sys


def parse_aspect(s):
    """'16:9' 或 '1080x1920' → (w_ratio, h_ratio) 浮点比值。"""
    s = s.strip().lower().replace("x", ":")
    a, b = s.split(":")
    return float(a), float(b)


def aspect_value(s):
    w, h = parse_aspect(s)
    return w / h


def out_resolution(target_aspect, out_long=1920):
    ta = aspect_value(target_aspect)
    if ta >= 1:
        ow, oh = out_long, round(out_long / ta)
    else:
        oh, ow = out_long, round(out_long * ta)
    return (ow - ow % 2, oh - oh % 2)


def reframe_filter(src_wh, target_aspect, mode="crop", out_long=1920,
                   crop_x=None, crop_y=None):
    """返回 ffmpeg -vf 滤镜串：把 src 分辨率 reframe 到 target 比例。纯函数·可测。

    mode=crop：裁切到目标比例。crop_x/crop_y 为归一焦点（0..1）；缺省两者 → 中心裁切；
               给了焦点 → 裁切窗中心对到焦点（夹进画内）。
    mode=pad ：保留全画，上下/左右加黑边（letterbox/pillarbox）——竖转横首选，不丢上下信息。
    """
    # src_wh 仅用于校验格式，实际滤镜按目标分辨率构造。
    sw, sh = (int(x) for x in src_wh.lower().split("x"))  # noqa: F841 校验可解析
    ow, oh = out_resolution(target_aspect, out_long)

    if mode == "crop":
        if crop_x is None and crop_y is None:
            return (f"scale={ow}:{oh}:force_original_aspect_ratio=increase,"
                    f"crop={ow}:{oh},setsar=1")
        fx = 0.5 if crop_x is None else max(0.0, min(1.0, crop_x))
        fy = 0.5 if crop_y is None else max(0.0, min(1.0, crop_y))
        x_expr = f"max(0\\,min(iw-{ow}\\,{fx:.4f}*iw-{ow}/2))"
        y_expr = f"max(0\\,min(ih-{oh}\\,{fy:.4f}*ih-{oh}/2))"
        return (f"scale={ow}:{oh}:force_original_aspect_ratio=increase,"
                f"crop={ow}:{oh}:{x_expr}:{y_expr},setsar=1")
    elif mode == "pad":
        return (f"scale={ow}:{oh}:force_original_aspect_ratio=decrease,"
                f"pad={ow}:{oh}:(ow-iw)/2:(oh-ih)/2:black,setsar=1")
    raise ValueError(f"unknown mode: {mode}")


def _ffmpeg():
    return shutil.which("ffmpeg")


def render_reframe(in_path, out_path, vf):
    """实际跑 ffmpeg 把 in_path 按 vf reframe 成 out_path。返回 (ok, msg)。"""
    ff = _ffmpeg()
    if not ff:
        return False, "无 ffmpeg：跳过渲染（滤镜串已出，可在带 ffmpeg 的机器上 --render）"
    if not os.path.isfile(in_path):
        return False, f"缺输入：{in_path}"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    args = [ff, "-y", "-loglevel", "error", "-i", in_path, "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", out_path]
    rc = subprocess.run(args, capture_output=True, text=True)
    if rc.returncode != 0:
        # 某些输入无音轨，-c:a copy 会报错；重试无音轨
        args2 = [ff, "-y", "-loglevel", "error", "-i", in_path, "-vf", vf, "-an",
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path]
        rc2 = subprocess.run(args2, capture_output=True, text=True)
        if rc2.returncode != 0:
            return False, f"reframe 渲染失败：{rc.stderr[-500:]}"
    return True, f"reframe 成片：{out_path}"


def main():
    ap = argparse.ArgumentParser(description="n2d 多比例 reframe 滤镜计算 + 渲染")
    ap.add_argument("--src", default="1080x1920", help="源分辨率（默认 n2d 竖屏 1080x1920）")
    ap.add_argument("--target", required=True, help="目标比例，如 16:9 / 1:1 / 9:16")
    ap.add_argument("--mode", default="crop", choices=["crop", "pad"])
    ap.add_argument("--out-long", type=int, default=1920)
    ap.add_argument("--crop-x", type=float, default=None,
                    help="归一焦点 X（0..1，主体水平中心位置）；不传=中心裁切")
    ap.add_argument("--crop-y", type=float, default=None,
                    help="归一焦点 Y（0..1，主体垂直中心位置）；不传=中心裁切")
    ap.add_argument("--in", dest="in_path", default=None, help="输入 MP4（--render 时用）")
    ap.add_argument("--render", action="store_true", help="实际 ffmpeg 输出 reframe MP4")
    ap.add_argument("--out", default=None, help="渲染输出路径（默认 交付/成片_<比例>.mp4）")
    args = ap.parse_args()
    vf = reframe_filter(args.src, args.target, args.mode, args.out_long,
                        args.crop_x, args.crop_y)
    ow, oh = out_resolution(args.target, args.out_long)
    print(f"# {args.src} → {args.target} ({args.mode})  输出 {ow}x{oh}")
    print(vf)
    out_default = f"交付/成片_{args.target.replace(':', 'x')}.mp4"
    print(f"\n# 示例：ffmpeg -i 成片_主片.mp4 -vf \"{vf}\" -c:a copy {out_default}")
    if args.mode == "crop" and args.crop_x is None and args.crop_y is None:
        print("# 中心裁切（未指定焦点）：竖屏母带转横/方版时上下信息可能被裁——"
              "主体不在中心请用 --crop-x/--crop-y，或改 --mode pad 加边保全画。")

    if args.render:
        out_path = args.out or out_default
        ok, msg = render_reframe(args.in_path or "", out_path, vf)
        print(("[ok] " if ok else "[skip] ") + msg)
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
