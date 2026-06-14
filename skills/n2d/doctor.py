#!/usr/bin/env python3
"""n2d doctor —— 开局一次性「能力/精度自检」，把静默降级摊到台面上。

为什么存在（E2·让 agent 跑得更顺）：n2d 的好几道机检会**静默降级**——缺 insightface 时
脸部一致性退回 Pillow（只看清晰度、判不了同人，近景自动转人审）；缺语音环境时配音退回
`say` 占位；生图后端不通时本应停工。这些精度模式以前要等跑到 image_qc / 配音 / 出图报告里
才暴露，agent 在那之前并不知道自己处在哪个档，规划不了「近景要不要预留人审」「先 say 占位
后重配」之类决策。doctor 把这些探针前移到**开局一次跑完**：

  python3 skills/n2d/doctor.py [作品根]

不带作品根 → 只探机器能力（库/CLI）；带作品根 → 额外按 `_设置.md` 探所选生图/生视频/配音
后端的连通与能力档。纯探针，不改任何文件、不花钱。
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
LIB_DIR = SCRIPT_DIR / "_lib"
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))


# ---------- 纯逻辑（无 I/O · pytest 覆盖） ----------

def face_qc_precision(libs: Dict[str, bool]) -> str:
    """库探测结果 → 脸部机检精度档。纯函数·可测。

    full        : insightface + onnxruntime 双备 → 跑 arcface 同人余弦，近景不必转人审。
    degraded    : 仅 Pillow/cv2 → 只能判清晰度/Haar 人脸存在，**判不了同人**，近景自动转人审。
    none        : 连 Pillow 都没有 → 像素层一致性机检全跳过，纯靠人审。"""
    if libs.get("insightface") and libs.get("onnxruntime"):
        return "full"
    if libs.get("cv2") or libs.get("PIL"):
        return "degraded"
    return "none"


def precision_lines(probes: Dict[str, Any]) -> List[str]:
    """probes → 人类可读自检行（含精度结论）。纯函数·可测，便于单测 + 复用到看板。"""
    libs = probes.get("libs", {})
    cli = probes.get("cli", {})
    lines: List[str] = []
    prec = face_qc_precision(libs)
    icon = {"full": "✅", "degraded": "⚠️", "none": "❌"}[prec]
    if prec == "full":
        lines.append(f"{icon} 脸部一致性机检：full 精度（insightface+onnxruntime 就位）——arcface 同人余弦可用，近景镜不必转人审。")
    elif prec == "degraded":
        lines.append(f"{icon} 脸部一致性机检：降级（仅 Pillow/cv2）——判不了同人，**近景/特写镜会自动转人审**，并出定妆↔本镜对比图。补 insightface+onnxruntime+buffalo_l 才回 full。")
    else:
        lines.append(f"{icon} 脸部一致性机检：none（连 Pillow 都缺）——像素层一致性全跳过，纯人审。先 pip 装 Pillow。")

    ff = "✅" if cli.get("ffmpeg") and cli.get("ffprobe") else "❌"
    lines.append(f"{ff} ffmpeg/ffprobe：{'就位——抽帧/接缝/片内时序机检可跑。' if ff=='✅' else '缺——接缝/片内时序/合成相关机检会跳过或失败。'}")

    voice = probes.get("voice", {})
    if voice.get("heavy_env"):
        lines.append("✅ 配音：检出零样本克隆环境（CosyVoice/GPT-SoVITS 等）——可正式配音。")
    elif voice.get("say"):
        lines.append("⚠️ 配音：仅 macOS `say` 占位可用，未见零样本克隆环境——可先 `say` 占位跑通时长清单/分镜，**正式出图前必须重配真音色**（声纹/时长会变）。")
    else:
        lines.append("❌ 配音：无任何可用后端（`say` 也没有）——配音阶段会卡住。")

    img = probes.get("image_backend")
    if img:
        si = {"ok": "✅", "down": "⛔", "unknown": "⚠️"}.get(img.get("status"), "⚠️")
        tail = "" if img.get("status") == "ok" else f"：{img.get('detail','')}"
        lines.append(f"{si} 生图后端「{img.get('name')}」：{img.get('status')}{tail}")
        if img.get("status") == "down":
            lines.append("   ↳ 出图是付费工位，不通就停——先修后端再开工，禁止静默兜底换后端（会引入跨镜后端混用漂移）。")

    vid = probes.get("video_backend")
    if vid:
        lines.append(f"ℹ️ 生视频后端「{vid.get('name')}」：关键帧能力档={vid.get('mode')}（max_timeline_frames={vid.get('max_frames')}；来源 {vid.get('verified')}）。")
    return lines


# ---------- 探针 I/O ----------

def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def probe_libs() -> Dict[str, bool]:
    return {m: _has_module(m) for m in ("insightface", "onnxruntime", "cv2", "PIL", "librosa", "numpy")}


def probe_cli() -> Dict[str, bool]:
    return {c: shutil.which(c) is not None for c in ("ffmpeg", "ffprobe", "say")}


def probe_voice() -> Dict[str, bool]:
    # 重环境（克隆）多在 repo 外 conda env，系统 py 里探不到——以 import 命中为「同机可用」的弱证据。
    heavy = any(_has_module(m) for m in ("cosyvoice", "GPT_SoVITS", "fish_speech"))
    return {"say": shutil.which("say") is not None, "heavy_env": heavy}


def probe_image_backend(root: Optional[str]) -> Optional[Dict[str, Any]]:
    if not root:
        return None
    try:
        from n2d_settings import get_setting
        import image_backends
    except Exception:
        return None
    name = (get_setting(root, "生图AI", "Codex") or "Codex").strip()
    status, detail = image_backends.probe_backend(name)
    return {"name": name, "status": status, "detail": detail}


def probe_video_backend(root: Optional[str]) -> Optional[Dict[str, Any]]:
    if not root:
        return None
    try:
        from n2d_settings import get_setting
        from n2d_platform_profiles import video_backend_frame_control
    except Exception:
        return None
    model = (get_setting(root, "生视频模型", "Seedance 2.0") or "Seedance 2.0").strip()
    channel = (get_setting(root, "生视频渠道", "即梦/Dreamina") or "即梦/Dreamina").strip()
    ctrl = video_backend_frame_control(model, channel)
    return {"name": model, "channel": channel, "mode": ctrl.get("mode", "unknown"),
            "max_frames": ctrl.get("max_timeline_frames", 1), "verified": ctrl.get("verified", "unknown")}


def collect(root: Optional[str]) -> Dict[str, Any]:
    return {
        "libs": probe_libs(),
        "cli": probe_cli(),
        "voice": probe_voice(),
        "image_backend": probe_image_backend(root),
        "video_backend": probe_video_backend(root),
    }


def main(argv: List[str]) -> int:
    root = argv[0].rstrip("/") if argv else None
    if root and not os.path.isdir(root):
        print(f"[warn] 作品根不存在：{root}——只做机器能力自检（不探项目后端）。")
        root = None
    probes = collect(root)
    print("=" * 70)
    print(" " * 22 + "n2d doctor：能力/精度自检")
    print("=" * 70)
    if root:
        print(f"作品根：{root}")
    libs = probes["libs"]
    print("库：" + " ".join(f"{k}={'✓' if v else '✗'}" for k, v in libs.items()))
    print("-" * 70)
    for line in precision_lines(probes):
        print(line)
    print("=" * 70)
    print("提示：doctor 只探不改、不花钱。降级档不阻断生产，但会改变验收方式（近景转人审/先占位后重配）——开局先看一眼，少踩坑。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
