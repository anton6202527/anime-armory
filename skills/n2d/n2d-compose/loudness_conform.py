#!/usr/bin/env python3
"""成片响度达标门（集成 LUFS conformance · L2-loud）——合成后查 integrated loudness 贴不贴平台目标。

为什么不能只靠 dynaudnorm/alimiter：
  compose.sh 末段混音用 `dynaudnorm`（动态归一）+ `alimiter`（限峰），这俩只防「忽大忽小」
  和「削顶爆音」，**不保证整段集成响度落在交付目标**。平台是否公开响度口径并不一致；
  因此内部数字发行目标、平台书面规格与广播标准必须分层记录，不能把一个 house target
  冒充所有平台官方标准。明显偏离可能触发平台播放增益或产生主观音量落差。
  本门在成片产出后量一次集成响度 + 真峰，落 ok/warn/block，让响度问题在交付前被抓到。

交付目标（**dated profile snapshot · 2026-08-26**，按 _设置.md / 客户规格选择）：
  youtube/bilibili/tiktok 的 -14 LUFS 是本线数字发行 house profile，不宣称是三平台统一官方值；
  `broadcast` 是 EBU R128 的 -23 LUFS，北美 ATSC A/85 另用 `broadcast_atsc=-24`；default -16
  是内部短视频母版。客户/播出机构书面规格优先，且必须在项目收据记录来源和日期。

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

# 交付 profile → 集成 LUFS 目标（dated snapshot · 2026-08-26）。
# 数字平台键均为 house profile；只有明确标注的广播键对应公开节目标准。
PLATFORM_TARGETS = {
    "youtube": -14.0,
    "bilibili": -14.0,
    "tiktok": -14.0,
    "broadcast": -23.0,
    "broadcast_atsc": -24.0,
    "default": -16.0,
}
PLATFORM_TARGET_AUTHORITIES = {
    "youtube": "house_profile; verify current client/platform specification",
    "bilibili": "house_profile; verify current client/platform specification",
    "tiktok": "house_profile; verify current client/platform specification",
    "broadcast": "EBU R 128 v5 programme loudness",
    "broadcast_atsc": "ATSC A/85 recommended practice",
    "default": "house_profile",
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


def two_pass_conform(
    input_path: str,
    output_path: str,
    *,
    target_lufs: float,
    true_peak: float = DEFAULT_TP_CEILING,
    lra: float = 11.0,
    ffmpeg: str = "ffmpeg",
) -> dict:
    """Program-level deterministic EBU R128 two-pass normalization.

    Video is stream-copied; the complete mixed programme is measured first and
    only then encoded once to 48 kHz AAC.  This must run after dialogue/BGM/
    ambience/foley have been mixed, never on individual dialogue lines.
    """
    report = {
        "status": "block", "input": input_path, "output": output_path,
        "target_lufs": float(target_lufs), "true_peak_dbtp": float(true_peak),
        "lra": float(lra), "sample_rate": 48000,
    }
    if not os.path.isfile(input_path):
        report["error"] = "input programme is missing"
        return report
    first_filter = (
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:"
        "print_format=json"
    )
    try:
        first = subprocess.run(
            [ffmpeg, "-nostdin", "-hide_banner", "-nostats", "-i", input_path,
             "-map", "0:a:0", "-af", first_filter, "-f", "null", "-"],
            capture_output=True, text=True, timeout=900, check=False,
        )
    except Exception as exc:
        report["error"] = f"loudnorm analysis failed: {exc}"
        return report
    measured = _parse_loudnorm_json(first.stderr)
    required = ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")
    if first.returncode != 0 or not measured or any(key not in measured for key in required):
        report["error"] = first.stderr[-1000:] or "loudnorm analysis did not return complete measurements"
        return report
    second_filter = (
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}:"
        f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
        f"measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:linear=true:print_format=json"
    )
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    tmp = f"{output_path}.tmp.{os.getpid()}.mp4"
    try:
        second = subprocess.run(
            [ffmpeg, "-nostdin", "-y", "-hide_banner", "-loglevel", "error", "-i", input_path,
             "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy", "-af", second_filter,
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
             "-movflags", "+faststart", tmp],
            capture_output=True, text=True, timeout=900, check=False,
        )
    except Exception as exc:
        report["error"] = f"loudnorm render failed: {exc}"
        return report
    if second.returncode != 0:
        report["error"] = second.stderr[-1000:] or "loudnorm render failed"
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return report
    os.replace(tmp, output_path)
    final = measure(output_path, ffmpeg=ffmpeg)
    if not final:
        report["error"] = "post-conform loudness measurement unavailable"
        return report
    report["first_pass"] = {key: measured.get(key) for key in required}
    report["measured_lufs"] = round(final["integrated"], 2)
    report["measured_true_peak_dbtp"] = round(final["true_peak"], 2)
    report["lufs_verdict"] = lufs_band(final["integrated"], target_lufs)
    report["tp_verdict"] = true_peak_band(final["true_peak"], true_peak)
    report["status"] = "pass" if report["lufs_verdict"] == "ok" and report["tp_verdict"] == "ok" else "block"
    if report["status"] != "pass":
        report["error"] = "post-conform programme is outside the delivery loudness contract"
    return report


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
    baseline_source = "dated_delivery_profile"
    target_authority = PLATFORM_TARGET_AUTHORITIES.get(platform, PLATFORM_TARGET_AUTHORITIES["default"])
    series = series_consistency.load(root)
    baseline = series.get("audio_baseline") if isinstance(series, dict) and isinstance(series.get("audio_baseline"), dict) else {}
    if platform == "default" and str(series.get("status") or "").lower() in {"confirmed", "approved", "ready"}:
        try:
            target = float(baseline.get("target_lufs"))
            tol = float(baseline.get("tolerance_lu"))
            tp_ceiling = float(baseline.get("true_peak_dbtp"))
            baseline_source = "series_consistency"
            target_authority = str(baseline.get("authority") or "project_approved_series_baseline")
        except (TypeError, ValueError):
            pass
    res: dict = {
        "available": False, "platform": platform, "target": target, "baseline_source": baseline_source,
        "target_authority": target_authority,
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
            f"{'——可能触发播放增益或转码风险' if lv == 'block' else '——轻偏'}。")
    if tv != "ok":
        res["notes"].append(
            f"真峰 {res['true_peak']} dBTP 超上限 {tp_ceiling} ——削波/转码爆音风险，回 compose 收限幅。")
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--platform", default=None,
                    help="youtube/bilibili/tiktok/broadcast/broadcast_atsc/default（dated delivery profile）；"
                         "缺省时自动读 _设置.md「目标平台」映射")
    ap.add_argument("--tol", type=float, default=DEFAULT_TOL)
    ap.add_argument("--tp-ceiling", type=float, default=DEFAULT_TP_CEILING)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--conform-input", default=None,
                    help="two-pass conform this complete mixed programme")
    ap.add_argument("--conform-output", default=None,
                    help="output MP4 for --conform-input (video copied, audio AAC 48 kHz)")
    ns = ap.parse_args(argv)
    platform, platform_source = resolve_platform_key(ns.root.rstrip("/"), ns.platform)
    if ns.conform_input:
        if not ns.conform_output:
            ap.error("--conform-output is required with --conform-input")
        target = resolve_target(platform)
        res = two_pass_conform(
            ns.conform_input, ns.conform_output, target_lufs=target,
            true_peak=ns.tp_ceiling, ffmpeg=ns.ffmpeg,
        )
        res["platform"] = platform
        res["platform_source"] = platform_source
        res["target_authority"] = PLATFORM_TARGET_AUTHORITIES.get(platform, PLATFORM_TARGET_AUTHORITIES["default"])
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if res.get("status") == "pass" else 2
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
