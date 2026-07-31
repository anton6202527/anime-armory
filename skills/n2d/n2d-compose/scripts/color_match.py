#!/usr/bin/env python3
"""
color_match.py - 自动色彩匹配 (Agentic Color Grading)
用于在 n2d-compose 阶段，计算目标视频段与参考色彩（Reference Look）的 RGB 偏差，
并输出 FFmpeg 的 colorchannelmixer 或 eq 滤镜参数，治愈多模型混剪带来的色彩断层。
"""
import sys
import subprocess
import os
import json

def get_mean_color(image_or_video_path):
    # 用 ffmpeg 提取首帧并计算平均 RGB
    # 这里用一种极简的黑科技：缩小到 1x1 像素然后读取颜色
    cmd = [
        "ffmpeg", "-i", image_or_video_path,
        "-vframes", "1",
        "-vf", "scale=1:1",
        "-f", "image2pipe",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, check=True)
        if len(res.stdout) >= 3:
            return res.stdout[0], res.stdout[1], res.stdout[2]
    except Exception:
        pass
    return None

def main():
    if len(sys.argv) < 3:
        print("")
        return
    
    target_clip = sys.argv[1]
    reference_clip = sys.argv[2]
    
    if not os.path.exists(target_clip) or not os.path.exists(reference_clip):
        print("")
        return
        
    ref_color = get_mean_color(reference_clip)
    tgt_color = get_mean_color(target_clip)
    
    if not ref_color or not tgt_color:
        print("")
        return
        
    r_r, r_g, r_b = ref_color
    t_r, t_g, t_b = tgt_color
    
    # 避免除以 0
    t_r = max(1, t_r)
    t_g = max(1, t_g)
    t_b = max(1, t_b)
    
    # 计算缩放系数，为了避免极端失真，限制在 0.8 - 1.2 之间
    scale_r = min(1.2, max(0.8, r_r / t_r))
    scale_g = min(1.2, max(0.8, r_g / t_g))
    scale_b = min(1.2, max(0.8, r_b / t_b))
    
    # 如果偏差很小，不加滤镜
    if abs(scale_r - 1.0) < 0.05 and abs(scale_g - 1.0) < 0.05 and abs(scale_b - 1.0) < 0.05:
        print("")
        return
        
    filter_str = f"colorchannelmixer=rr={scale_r:.3f}:gg={scale_g:.3f}:bb={scale_b:.3f}"
    print(filter_str)

if __name__ == "__main__":
    main()
