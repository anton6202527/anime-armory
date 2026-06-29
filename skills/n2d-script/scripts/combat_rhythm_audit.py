#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打斗剪辑节奏曲线审计（advisory-only·P2）——打斗段切点节奏是否过慢/平淡无起伏。

为什么存在：打斗"视觉盛宴"不止四轴撞点对齐（那是 combat_cue_apex_audit 管的硬闸），还要**剪辑节奏**
——切点要够密、且向命中拍**收紧加速**，而不是一路等长长镜把拆招拍成 PPT。combat 四轴加固时 #6
「战斗节奏曲线」被留作未做。本审计补上，但**刻意只做 advisory**：2026-06-28 实搜确认没有可辩护的
公开「打斗切点/秒」硬基准，唯一可用的是通用短剧「画面每~5s 一切」剪辑经验 + 导演节奏.md 动作曲线，
故阈值带 internal-heuristic provenance、**只提示不阻断**（不造假 BLOCK）。

只审 impact 型打斗镜（fight_exchange / magic_burst）。两个 info 码：
  R1 combat_pacing_too_slow —— 本镜平均切点间隔 > 区域慢阈值（国内 ~5s / 海外 ~3.5s）→ 动作节奏拖沓。
  R2 combat_rhythm_flat —— ≥3 个切点却近乎等长（变异系数 < 0.15）→ 缺节奏起伏/加速感；
     若本镜有 apex 命中拍而后半段切点没比前半段更密，附注「未向命中拍收紧」。

零像素·零花钱·纯 stdlib：写 `生产数据/combat_rhythm_<集>.{json,md}`，给人审/导演调剪辑。
report-only——**不接 gate、不升 BLOCK**（与 combat_cue_apex 硬闸分层：撞点对齐是硬伤，节奏曲线是审美）。
区域档/阈值复用 beat_audit.pacing_region + industry_benchmark.proxy_thresholds（单一真值源）。
切点边界复用 anchor_planner.parse_shot_boundaries；奇观判定复用 n2d_contract.infer_spectacle_type。

用法：python3 combat_rhythm_audit.py <作品根> <第N集> [--json]
测试：cd skills/n2d-script/scripts && python -m pytest test_combat_rhythm_audit.py
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "n2d", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from anchor_planner import parse_shot_boundaries, apex_anchor_seconds  # 切点边界 + apex 秒（同目录·单一真值）
from n2d_contract import infer_spectacle_type  # 奇观判定（与生产侧同口径）

try:  # 区域档 + 阈值（beat_audit 单一真值源·G2 同款）
    import beat_audit as _ba
except Exception:  # pragma: no cover - 异常布局兜底
    _ba = None  # type: ignore

AUDIT_KIND = "n2d_combat_rhythm_audit"

COMBAT_SPECTACLE = frozenset({"fight_exchange", "magic_burst"})
DEFAULT_COMBAT_SLOW_SEC = 5.0           # 国内：通用短剧「每~5s 一切」+ 导演节奏动作曲线（combat 应 ≤ 此）
DEFAULT_OVERSEAS_COMBAT_SLOW_SEC = 3.5  # 海外：ReelShort/TikTok 动作更碎更狠
MIN_CUTS_FOR_RHYTHM = 3
UNIFORM_COV_CEILING = 0.15              # 切点间隔变异系数 < 此 = 近乎等长 = 节奏平淡


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def cut_intervals(clip: Mapping[str, Any], duration: float) -> List[float]:
    """clip 的切点间隔列表 = [0, 各分镜边界, duration] 的相邻差。纯函数·可测。

    无内部分镜边界（单镜/缺 shots[].t）→ [duration]（单长镜，平均间隔=整镜时长）。"""
    if not isinstance(duration, (int, float)) or duration <= 0:
        return []
    bounds = [b for b in parse_shot_boundaries(dict(clip)) if 0 < b < duration]
    pts = [0.0] + sorted(set(bounds)) + [float(duration)]
    return [round(pts[i + 1] - pts[i], 2) for i in range(len(pts) - 1) if pts[i + 1] > pts[i]]


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _cov(xs: Sequence[float]) -> float:
    """变异系数 = stdev/mean；空或单元素 → 0（不算平淡，证据不足）。纯函数·可测。"""
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    if m <= 0:
        return 0.0
    var = sum((x - m) ** 2 for x in xs) / len(xs)
    return (var ** 0.5) / m


def tightens_toward_apex(intervals: Sequence[float]) -> bool:
    """切点是否向后段收紧（后半段平均间隔 < 前半段）= 有加速感。纯函数·可测。

    切点数 < 3 → True（证据不足不判平淡）。用于 combat_rhythm_flat 的附注，不单独成码。"""
    n = len(intervals)
    if n < MIN_CUTS_FOR_RHYTHM:
        return True
    half = n // 2
    early = _mean(intervals[:half])
    late = _mean(intervals[half:])
    return late < early


def audit_clip(clip: Mapping[str, Any], clip_id: str, *, slow_sec: float = DEFAULT_COMBAT_SLOW_SEC) -> List[Dict[str, Any]]:
    """单镜打斗节奏审计 → info findings（R1 过慢 / R2 平淡）。纯函数·可测。只审 impact 型打斗镜。"""
    if infer_spectacle_type(clip) not in COMBAT_SPECTACLE:
        return []
    duration = clip.get("duration")
    if not isinstance(duration, (int, float)) or duration <= 0:
        return []
    intervals = cut_intervals(clip, float(duration))
    if not intervals:
        return []
    n_cuts = len(intervals)
    mean_iv = _mean(intervals)
    findings: List[Dict[str, Any]] = []

    if mean_iv > slow_sec:
        findings.append({
            "clip_id": clip_id, "code": "combat_pacing_too_slow", "level": "info",
            "mean_cut_interval": round(mean_iv, 2), "cuts": n_cuts, "slow_sec": slow_sec,
            "msg": (f"{clip_id}：打斗镜平均切点间隔 {round(mean_iv, 2)}s（{n_cuts} 切）> 慢阈值 {slow_sec}s——"
                    "动作节奏拖沓，建议拆更多短镜（起手/命中/受击/收势一拍一镜），向命中拍提速。"),
        })

    if n_cuts >= MIN_CUTS_FOR_RHYTHM and _cov(intervals) < UNIFORM_COV_CEILING:
        apexes = apex_anchor_seconds(dict(clip), float(duration))
        tail = ""
        if apexes and not tightens_toward_apex(intervals):
            tail = "；且后半段切点未比前半段更密=未向命中拍收紧（apex 应是节奏最密点）"
        findings.append({
            "clip_id": clip_id, "code": "combat_rhythm_flat", "level": "info",
            "cov": round(_cov(intervals), 3), "cuts": n_cuts,
            "msg": (f"{clip_id}：打斗镜 {n_cuts} 个切点近乎等长（变异系数 {round(_cov(intervals), 3)} < "
                    f"{UNIFORM_COV_CEILING}）=节奏平淡缺起伏{tail}。建议蓄力放慢、命中前提速、命中处 hit-stop，"
                    "把切点曲线做出加速感。"),
        })
    return findings


# ── 装配（读盘 → 审计 → 落档） ─────────────────────────────────────────────────

def _clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("id") or clip.get("clip_id") or clip.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I) or re.search(r"(\d+)", raw)
    return f"Clip_{int(m.group(1)):02d}" if m else f"Clip_{idx:02d}"


def storyboard_path(root: Path, ep: str) -> Path:
    return root / "脚本" / ep / "storyboard.json"


def resolve_slow_sec(root: str) -> float:
    """区域档慢阈值：benchmark proxy_thresholds（海外优先 overseas_*）+ 默认兜底。复用 beat_audit 单一真值源。"""
    if _ba is None:
        return DEFAULT_COMBAT_SLOW_SEC
    try:
        proxy = _ba._proxy_thresholds(root)
        overseas = _ba.pacing_region(root) == "overseas"
    except Exception:
        return DEFAULT_COMBAT_SLOW_SEC

    def _f(v, d):
        try:
            return float(v)
        except (TypeError, ValueError):
            return float(d)
    if overseas:
        return _f(proxy.get("overseas_combat_cut_interval_slow_sec"), DEFAULT_OVERSEAS_COMBAT_SLOW_SEC)
    return _f(proxy.get("combat_cut_interval_slow_sec"), DEFAULT_COMBAT_SLOW_SEC)


def build_audit(root: Path, ep: str) -> Dict[str, Any]:
    slow_sec = resolve_slow_sec(str(root))
    p = storyboard_path(root, ep)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"kind": AUDIT_KIND, "version": 1, "episode": ep, "slow_sec": slow_sec,
                "findings": [], "summary": {"error": f"缺少或损坏：{p}", "combat_clips": 0, "findings": 0}}
    clips = data.get("clips") if isinstance(data, dict) else None
    findings: List[Dict[str, Any]] = []
    combat_clips = 0
    for idx, clip in enumerate(clips or [], 1):
        if not isinstance(clip, dict):
            continue
        if infer_spectacle_type(clip) in COMBAT_SPECTACLE:
            combat_clips += 1
        findings.extend(audit_clip(clip, _clip_id(clip, idx), slow_sec=slow_sec))
    by_code: Dict[str, int] = {}
    for f in findings:
        by_code[f["code"]] = by_code.get(f["code"], 0) + 1
    return {
        "kind": AUDIT_KIND, "version": 1, "episode": ep, "slow_sec": slow_sec,
        "findings": findings,
        "summary": {"combat_clips": combat_clips, "findings": len(findings), "by_code": by_code,
                    "advisory_only": True},
    }


def render_md(audit: Mapping[str, Any]) -> str:
    s = audit.get("summary") or {}
    lines = [
        "# 打斗剪辑节奏曲线审计（advisory-only）",
        "",
        f"- episode: {audit.get('episode')} ｜ 慢阈值: {audit.get('slow_sec')}s（区域档·proxy_thresholds）",
        f"- impact 型打斗镜: {s.get('combat_clips', 0)} ｜ 提示: {s.get('findings', 0)}（全 info·只提示不阻断）",
        "",
        "> 节奏曲线是审美不是硬伤：阈值带 internal-heuristic provenance（无公开打斗切点基准），"
        "**不升 BLOCK**。撞点对齐硬伤走 combat_cue_apex_audit。",
        "",
    ]
    if s.get("error"):
        return "\n".join(lines + [f"⚠️ {s['error']}", ""])
    if not audit.get("findings"):
        return "\n".join(lines + ["✅ 打斗镜切点节奏：够密 + 有起伏（无过慢/平淡提示）。", ""])
    for f in audit["findings"]:
        lines.append(f"- ℹ️ `{f.get('code')}` {f.get('msg')}")
    lines.append("")
    return "\n".join(lines)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="打斗剪辑节奏曲线审计（advisory-only）")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true", help="只打印 JSON，不落档")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ns.episode if str(ns.episode).startswith("第") else f"第{ns.episode}集"
    audit = build_audit(root, ep)
    if ns.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
        return 0
    out = root / "生产数据"
    _atomic_write(out / f"combat_rhythm_{ep}.json", json.dumps(audit, ensure_ascii=False, indent=2))
    _atomic_write(out / f"combat_rhythm_{ep}.md", render_md(audit))
    s = audit["summary"]
    print(f"[ok] 打斗节奏曲线审计（advisory）→ {out / f'combat_rhythm_{ep}.json'}")
    print(f"     impact 打斗镜 {s.get('combat_clips', 0)} / 提示 {s.get('findings', 0)}（{s.get('by_code') or {}}·只提示不阻断）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
