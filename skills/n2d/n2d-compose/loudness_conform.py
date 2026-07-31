#!/usr/bin/env python3
"""成片响度达标门（集成 LUFS conformance · L2-loud）——合成后查 integrated loudness 贴不贴平台目标。

为什么不能只靠 dynaudnorm/alimiter：
  compose.sh 末段混音用 `dynaudnorm`（动态归一）+ `alimiter`（限峰），这俩只防「忽大忽小」
  和「削顶爆音」，**不保证整段集成响度落在平台目标**。各投放平台对 integrated LUFS 有事实标准
  （流媒体 -14、广电 -23…），偏离会被平台二次响度归一（压扁动态/拉低音量）或显得「比别家小声」。
  本门在成片产出后量一次集成响度 + 真峰，落 ok/warn/block，让响度问题在交付前被抓到。

平台目标（**dated 候选 snapshot · 2026-06**，choice-point 风格——不写死单一值，按 _设置.md 平台选）：
  youtube/bilibili/tiktok 走流媒体事实标准 -14 LUFS；broadcast 走 EBU R128 / ATSC A/85 的 -23；
  default -16（偏保守的通用短视频值）。新平台标准变了就更新此表 + 注记日期，勿散落改各处。

机制：
  measure() 调 `ffmpeg -i <成片> -af loudnorm=print_format=json -f null -`，从 stderr 末尾的
  JSON 块解析 input_i（集成 LUFS）与 input_tp（真峰 dBTP）。无 ffmpeg / 解析失败 → None（优雅降级，
  不在 import 期硬依赖 ffmpeg）。
  纯数学分档（lufs_band / true_peak_band）无依赖、带 pytest：
    集成响度：|measured - target| ≤ tol → ok；≤ 2*tol → warn（轻偏，平台可能二次归一）；否则 block。
    真峰：> ceiling（默认 -1.0 dBTP）→ block（有限幅/削波/平台转码爆音风险），否则 ok。

诚实边界：loudnorm 一遍测量（非两遍线性）的 input_i 与离线 BS.1770 表里有亚 dB 误差，故 tol 默认 1.0 dB
留足缓冲，只在明显偏离时 block——这是交付前体检门，不替代专业母带。

用法：python3 loudness_conform.py <作品根> 第N集 [--platform youtube] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import List, Optional

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
import series_consistency  # noqa: E402

# 平台 → 集成 LUFS 目标（dated 候选 snapshot · 2026-06）。改这里，勿散落。
PLATFORM_TARGETS = {
    "youtube": -14.0,
    "bilibili": -14.0,
    "tiktok": -14.0,
    "broadcast": -23.0,
    "default": -16.0,
}
DEFAULT_TOL = 1.0          # 集成响度容差（dB）：≤tol ok，≤2*tol warn，否则 block
DEFAULT_TP_CEILING = -1.0  # 真峰上限（dBTP）：超过判 block（削波/平台转码爆音风险）


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def lufs_band(measured_lufs: float, target_lufs: float, tol: float = DEFAULT_TOL) -> str:
    """集成响度落档：|measured - target| ≤ tol → 'ok'；≤ 2*tol → 'warn'；否则 'block'。
    边界含等号（恰好 tol = ok，恰好 2*tol = warn）。纯函数·可测。"""
    diff = abs(measured_lufs - target_lufs)
    if diff <= tol:
        return "ok"
    if diff <= 2.0 * tol:
        return "warn"
    return "block"


def true_peak_band(tp_dbtp: float, ceiling: float = DEFAULT_TP_CEILING) -> str:
    """真峰落档：> ceiling → 'block'（削波/转码爆音风险）；≤ ceiling → 'ok'。
    边界含等号（恰好 ceiling = ok）。纯函数·可测。"""
    if tp_dbtp > ceiling:
        return "block"
    return "ok"


def worst_band(bands) -> str:
    order = {"ok": 0, "warn": 1, "block": 2}
    w = "ok"
    for b in bands:
        if order.get(b, 0) > order.get(w, 0):
            w = b
    return w


def resolve_target(platform: str) -> float:
    """平台名 → 集成 LUFS 目标，未知平台回退 default。纯函数·可测。"""
    return PLATFORM_TARGETS.get((platform or "").strip().lower(), PLATFORM_TARGETS["default"])


def resolve_platform_key(root: str, platform: Optional[str]):
    """(platform_key, source)：CLI 显式给了就用；缺省从 <root>/_设置.md「目标平台」解析。

    此前 compose.sh 固定传 default（-16），抖音/TikTok 集实际该按 -14 判——目标错档让
    响度门形同虚设。映射复用 deliver.PLATFORM_LOUDNESS_KEY（延迟导入避免与
    deliver→loudness_conform 的模块级引用成环）；解析失败回退 default，不阻断。"""
    if platform:
        return platform, "cli"
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import deliver  # noqa: PLC0415  同目录·延迟导入防环
        p = os.path.join(root, "_设置.md")
        text = open(p, encoding="utf-8").read() if os.path.isfile(p) else ""
        setting = deliver.parse_setting(text, "目标平台")
        if setting:
            return deliver.loudness_key_for_platform(setting), f"settings:{setting}"
    except Exception:
        pass
    return "default", "fallback"


# ---------- 音频测量（需 ffmpeg · 缺则 None） ----------

def _parse_loudnorm_json(stderr: str) -> Optional[dict]:
    """从 ffmpeg loudnorm=print_format=json 的 stderr 里抠出最后一个 JSON 块并解析。失败→None。"""
    # loudnorm 把 JSON 打到 stderr 末尾；取最后一对花括号块，容忍前后的日志噪声。
    matches = re.findall(r"\{[^{}]*\}", stderr or "", re.DOTALL)
    for raw in reversed(matches):
        try:
            data = json.loads(raw)
        except Exception:
            continue
        if "input_i" in data:
            return data
    return None


def measure(path: str, ffmpeg: str = "ffmpeg") -> Optional[dict]:
    """量成片集成响度 + 真峰：跑 loudnorm 分析遍，解析 input_i / input_tp。
    返回 {"integrated": float, "true_peak": float}；ffmpeg 缺失/失败/解析不出 → None（优雅）。"""
    if not path or not os.path.isfile(path):
        return None
    try:
        proc = subprocess.run(
            [ffmpeg, "-hide_banner", "-nostats", "-i", path,
             "-af", "loudnorm=print_format=json", "-f", "null", "-"],
            capture_output=True, text=True,
        )
    except Exception:
        return None
    data = _parse_loudnorm_json(proc.stderr)
    if not data:
        return None
    try:
        return {"integrated": float(data["input_i"]), "true_peak": float(data["input_tp"])}
    except Exception:
        return None


def _is_backup_or_work_cut(path: str) -> bool:
    """True for backup/temp derivatives that must not be treated as master."""
    name = os.path.basename(str(path or "")).lower()
    return any(token in name for token in (
        ".pre_",
        ".pre-",
        ".bak",
        ".backup",
        ".tmp",
        ".loudnorm_tmp",
    ))


def _find_final_cut(root: str, ep: str) -> Optional[str]:
    """合成/<ep>/ 下找成片母带，排除 loudnorm/backup/temp 派生件。"""
    import glob
    base = os.path.join(root, "合成", ep)
    for name in (f"成片_{ep}_zh.mp4", f"成片_{ep}.mp4"):
        preferred = os.path.join(base, name)
        if os.path.isfile(preferred):
            return preferred
    cands = [
        p for p in sorted(glob.glob(os.path.join(base, "成片_*.mp4")))
        if not _is_backup_or_work_cut(p)
    ]
    if not cands:
        return None
    return max(cands, key=lambda p: os.path.getmtime(p))


def analyze(root: str, ep: str, platform: str = "default",
            tol: float = DEFAULT_TOL, tp_ceiling: float = DEFAULT_TP_CEILING,
            ffmpeg: str = "ffmpeg") -> dict:
    target = resolve_target(platform)
    baseline_source = "platform_snapshot"
    series = series_consistency.load(root)
    baseline = series.get("audio_baseline") if isinstance(series, dict) and isinstance(series.get("audio_baseline"), dict) else {}
    if platform == "default" and str(series.get("status") or "").lower() in {"confirmed", "approved", "ready"}:
        try:
            target = float(baseline.get("target_lufs"))
            tol = float(baseline.get("tolerance_lu"))
            tp_ceiling = float(baseline.get("true_peak_dbtp"))
            baseline_source = "series_consistency"
        except (TypeError, ValueError):
            pass
    res: dict = {
        "available": False, "platform": platform, "target": target, "baseline_source": baseline_source,
        "measured_lufs": None, "true_peak": None, "verdict": "ok", "notes": [],
    }
    out = _find_final_cut(root, ep)
    if out is None:
        res["notes"].append("本集无成片（合成/<集>/成片_*.mp4 不存在）——先 n2d-compose 合成再查响度。")
        return res
    res["out"] = os.path.basename(out)
    m = measure(out, ffmpeg=ffmpeg)
    if m is None:
        res["notes"].append("响度达标门已跳过（未装 ffmpeg 或 loudnorm 测量失败）——集成 LUFS 暂由人耳/外部工具判。")
        return res
    res["available"] = True
    res["measured_lufs"] = round(m["integrated"], 2)
    res["true_peak"] = round(m["true_peak"], 2)
    lv = lufs_band(m["integrated"], target, tol)
    tv = true_peak_band(m["true_peak"], tp_ceiling)
    res["lufs_verdict"] = lv
    res["tp_verdict"] = tv
    res["verdict"] = worst_band([lv, tv])
    if lv != "ok":
        res["notes"].append(
            f"集成响度 {res['measured_lufs']} LUFS 偏离 {platform} 目标 {target} "
            f"（差 {abs(m['integrated'] - target):.1f} dB，容差 {tol}）"
            f"{'——平台会二次响度归一' if lv == 'block' else '——轻偏'}。")
    if tv != "ok":
        res["notes"].append(
            f"真峰 {res['true_peak']} dBTP 超上限 {tp_ceiling} ——削波/转码爆音风险，回 compose 收限幅。")
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--platform", default=None,
                    help="youtube/bilibili/tiktok/broadcast/default（dated 候选 snapshot）；"
                         "缺省时自动读 _设置.md「目标平台」映射")
    ap.add_argument("--tol", type=float, default=DEFAULT_TOL)
    ap.add_argument("--tp-ceiling", type=float, default=DEFAULT_TP_CEILING)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    platform, platform_source = resolve_platform_key(ns.root.rstrip("/"), ns.platform)
    res = analyze(ns.root.rstrip("/"), ns.episode, platform, ns.tol, ns.tp_ceiling, ns.ffmpeg)
    res["platform_source"] = platform_source
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 成片响度达标门（L2-loud·{platform} 目标 {res['target']} LUFS·来源 {platform_source}）：{ns.root} {ns.episode} ===")
    for note in res["notes"]:
        print("ℹ️ " + note)
    if not res["available"]:
        return 0
    icon = {"block": "⛔", "warn": "⚠️", "ok": "✅"}
    print(f"{icon.get(res['lufs_verdict'], '?')} 集成响度 {res['measured_lufs']} LUFS（目标 {res['target']}）")
    print(f"{icon.get(res['tp_verdict'], '?')} 真峰 {res['true_peak']} dBTP（上限 {ns.tp_ceiling}）")
    print(f"\n响度达标判定：{icon.get(res['verdict'], '?')} {res['verdict']}")
    return 1 if res["verdict"] == "block" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
