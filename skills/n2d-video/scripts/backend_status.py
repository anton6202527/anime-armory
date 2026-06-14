#!/usr/bin/env python3
"""n2d-video Proactive Notice — 启动阶段自动报盘后端能力。

读取 `_设置.md` 所选后端，对照 `n2d_platform_profiles.py` 打印其：
  · 时间轴关键帧能力（首/中/尾）
  · 拆段接力需求
  · 建议的分镜规划策略
  · 验收基准（中锚是原生锁还是 QC 参考）

用法：python3 backend_status.py <作品根>
"""
import os
import sys
from pathlib import Path

# 设置 path 以前能导入 n2d/_lib
SCRIPT_DIR = Path(__file__).resolve().parent
COMMON_DIR = SCRIPT_DIR.parents[1] / "n2d" / "_lib"
if str(COMMON_DIR) not in sys.path:
    sys.path.insert(0, str(COMMON_DIR))

try:
    from n2d_settings import get_setting
    from n2d_platform_profiles import video_backend_frame_control
except ImportError:
    print("[err] 无法导入 n2d 基础库，请确保在作品根目录或正确环境下运行。")
    sys.exit(1)

def print_banner():
    print("=" * 70)
    print(" " * 20 + "n2d-video 启动报盘：后端能力快照")
    print("=" * 70)

def main():
    if len(sys.argv) < 2:
        print("用法: python3 backend_status.py <作品根>")
        sys.exit(1)
    
    root = sys.argv[1]
    model = get_setting(root, "生视频模型", "Seedance 2.0")
    channel = get_setting(root, "生视频渠道", "即梦/Dreamina")
    
    # 兼容旧字段
    if not model or model == "Seedance 2.0":
        legacy_ai = get_setting(root, "生视频AI", "")
        if legacy_ai:
            model = legacy_ai

    control = video_backend_frame_control(model, channel)
    mode = control.get("mode", "unknown")
    max_frames = control.get("max_timeline_frames", 1)
    supports_mid = control.get("supports_native_mid_anchors", False)
    supports_last = control.get("supports_last_frame", False)
    fallback = control.get("fallback", "Unknown capability; assume single-frame only.")
    verified = control.get("verified", "unknown")

    print_banner()
    print(f"当前模型  : {model}")
    print(f"执行渠道  : {channel}")
    print(f"能力档案  : {mode} (max_timeline_frames: {max_frames})")
    print(f"数据来源  : {verified}")
    print("-" * 70)

    print("【关键帧能力详述】")
    if mode == "multi_keyframe":
        print("✅ 原生多帧：支持 首 + N个中锚 + 尾 一镜到底。")
        print("   - 建议：放手规划中段锚帧，无需拆段，一致性最稳。")
    elif mode in ("first_last", "frames2video"):
        print("⚠️ 首尾两帧：支持 首 + 尾 锁定。")
        print("   - 建议：中段锚帧(Mid)将触发「拆段接力」或仅作 QC 参考，无法一次请求锁死。")
    elif mode == "multimodal2video":
        print("⚠️ 首尾两帧(多模态)：支持 首 + 尾 引导。")
        print("   - 建议：适合简单接缝；中段复杂动作建议拆段。")
    else:
        print("❌ 单首帧：仅支持首帧引导。")
        print("   - 建议：中/尾关键帧将退化为文字约束，强烈建议改用拆段接力(Relay)。")
    
    print("\n【执行与验收策略】")
    if supports_mid:
        print("🔹 中段锚帧：原生参与生成。")
    else:
        print("🔹 中段锚帧：不参与生成，仅作为 video_qc 的一致性基准(Baseline)。")
    
    if max_frames < 2:
        print("🔹 拆段接力：对于 >4s 且有锚点的镜，一键执行 split relay 自动化拆段。")
    
    print(f"\n[提示] 后端能力决定成本分布。{fallback}")
    print("=" * 70)

if __name__ == "__main__":
    main()
