#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""长篇叙事一致性 KPI（报告型·非扣分·对标 NarrLV / DirectorBench 2026）。

为什么存在：n2d 的跨集叙事连续性此前只有零散闸（SP1 伏笔账、P0 语义谱系 Diff、跨集后端锁），
`模型矩阵.md` 引用了 NarrLV(arXiv 2507.11245)/DirectorBench 却**零接线**。本模块把已有的确定性
跨集信号聚合成一条 0–1 的"长篇叙事连续性"报告型 KPI——与 `character_consistency_kpi` 同性质：
**不参与扣分**，只给 n2d-review 模式② 一个可横向对标的叙事健康度数字。

聚合的子信号（全部来自既有确定性产物，缺则该子项跳过、不臆造）：
- 伏笔已回收 payoff_completed_rate：`设定库/setup_payoff_ledger.json`（status=done/completed 占比）。
- 伏笔已规划 payoff_planned_rate：已填 payoff_ep / ongoing / planned 占比；只表示制作计划，不等同已回收。
- 反套路 anti_trope = 1 − 跨集桥段同质化 max Jaccard（beat_audit --series）。NarrLV 的"段落多样性/不复读"。
- 冷开场链 cold_open_chain_rate：beat_audit.cold_open_chain（P2 切点让下集冷开场达成率）。DirectorBench 的"幕间衔接"。
- 情绪起伏 emotion_variation：各集 `[情绪]` 标注的平均去重率（情绪不一条道走到黑）。
- 叙事原子 narrative_atom_density：reveal/decision/reversal/state-change/goal-change 等 TNA-like 原子密度。
- 实体排程 entity_schedule_coverage：storyboard.json `entity_schedule` 覆盖率（EntityBench 轴）。

诚实边界：全 report-only。子信号是确定性近似（关键词/标记/分位），不是语义叙事模型；KPI 是"健康度指示"，
不替代人读。缺所有子信号 → score=None、verdict=None（不臆造达标）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_SKILLS = os.path.abspath(os.path.join(SKILL_DIR, ".."))

# 子信号权重（仅对"可用"的子项归一化）。profile 可调整权重和参考线。
_PROFILE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "standard": {
        "payoff_completed": 0.22, "payoff_planned": 0.08, "cold_open_chain": 0.18,
        "anti_trope": 0.14, "emotion_variation": 0.12, "narrative_atom_density": 0.14,
        "entity_schedule": 0.12,
    },
    "demo": {
        "payoff_completed": 0.16, "payoff_planned": 0.14, "cold_open_chain": 0.18,
        "anti_trope": 0.14, "emotion_variation": 0.14, "narrative_atom_density": 0.14,
        "entity_schedule": 0.10,
    },
    "production": {
        "payoff_completed": 0.25, "payoff_planned": 0.05, "cold_open_chain": 0.18,
        "anti_trope": 0.10, "emotion_variation": 0.10, "narrative_atom_density": 0.14,
        "entity_schedule": 0.18,
    },
    "overseas": {
        "payoff_completed": 0.22, "payoff_planned": 0.06, "cold_open_chain": 0.16,
        "anti_trope": 0.14, "emotion_variation": 0.12, "narrative_atom_density": 0.16,
        "entity_schedule": 0.14,
    },
}
_PROFILE_RELEASE_LINES = {"demo": 0.60, "standard": 0.70, "production": 0.78, "overseas": 0.74}
_DEFAULT_RELEASE_LINE = _PROFILE_RELEASE_LINES["standard"]
_BENCHMARK_REF = ("长篇叙事一致性参 NarrLV（Temporal Narrative Atom）/ EntityBench（per-shot entity schedule）/"
                  "DirectorBench（长视频多代理诊断）；"
                  "report-only·非扣分·子信号为确定性近似，不替代人读")
NARRATIVE_ATOM_RE = re.compile(
    r"(原来|竟是|真相|揭|发现|决定|选择|目标|誓|转而|改为|背叛|结盟|和解|决裂|"
    r"升级|突破|觉醒|身份|身世|线索|证据|规则|系统|任务|惩罚|奖励|位置|赶到|离开|进入|"
    r"却|反而|不料|岂料|没想到|逆转|翻盘|代价|牺牲)"
)


# ── 纯函数（无 I/O·可测） ──────────────────────────────────────────────────────

def build_narrative_kpi(signals: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """聚合跨集叙事子信号 → 报告型 KPI。纯函数·可测。

    signals（全部可选，缺=None 跳过该子项）：
      payoff_completed_rate/payoff_rate, payoff_planned_rate, cold_open_chain_rate,
      homogenization_max, emotion_variation, narrative_atom_density, entity_schedule_coverage,
      open_setups, episodes_counted, profile。
    返回含 narrative_continuity(0–1 或 None)、各子分、release_line、verdict、benchmark_ref。"""
    s = dict(signals or {})
    profile = _resolve_profile(s)
    weights = _PROFILE_WEIGHTS.get(profile, _PROFILE_WEIGHTS["standard"])
    payoff_completed = _clamp01(s.get("payoff_completed_rate", s.get("payoff_rate")))
    payoff_planned = _clamp01(s.get("payoff_planned_rate"))
    chain = _clamp01(s.get("cold_open_chain_rate"))
    homog = _clamp01(s.get("homogenization_max"))
    anti_trope = (1.0 - homog) if homog is not None else None
    emo = _clamp01(s.get("emotion_variation"))
    atom = _clamp01(s.get("narrative_atom_density"))
    entity = _clamp01(s.get("entity_schedule_coverage"))

    subs = {
        "payoff_completed": payoff_completed,
        "payoff_planned": payoff_planned,
        "cold_open_chain": chain,
        "anti_trope": anti_trope,
        "emotion_variation": emo,
        "narrative_atom_density": atom,
        "entity_schedule": entity,
    }
    avail = {k: v for k, v in subs.items() if v is not None}
    if avail:
        wsum = sum(weights.get(k, 0.0) for k in avail)
        score = round(sum(v * weights.get(k, 0.0) for k, v in avail.items()) / wsum, 4) if wsum else None
    else:
        score = None

    try:
        line = float(os.environ.get("N2D_NARRATIVE_RELEASE_LINE", str(_PROFILE_RELEASE_LINES.get(profile, _DEFAULT_RELEASE_LINE))))
    except ValueError:
        line = _PROFILE_RELEASE_LINES.get(profile, _DEFAULT_RELEASE_LINE)
    verdict = None if score is None else ("above" if score >= line else "below")
    return {
        "narrative_continuity": score,
        "subscores": {k: (round(v, 4) if isinstance(v, float) else v) for k, v in subs.items()},
        "signals_used": sorted(avail.keys()),
        "profile": profile,
        "weights": {k: weights.get(k) for k in sorted(avail)},
        "open_setups": s.get("open_setups"),
        "planned_setups": s.get("planned_setups"),
        "completed_setups": s.get("completed_setups"),
        "episodes_counted": s.get("episodes_counted"),
        "release_line": line,
        "verdict": verdict,
        "benchmark_ref": _BENCHMARK_REF,
        "note": "报告型 KPI·不参与扣分；与 character_consistency_kpi 正交（角色 vs 叙事）",
    }


def payoff_rate_from_ledger(pairs: Optional[List[Mapping[str, Any]]]) -> Dict[str, Any]:
    """SP1 账本 pairs → completed/planned 两条率。

    completed = status 明确 done/completed/resolved/closed。
    planned = completed 或已填 payoff_ep / status ongoing/planned/scheduled。
    旧版 `payoff_rate` 兼容映射到 completed，避免把未来计划当已回收。"""
    if not isinstance(pairs, (list, tuple)) or not pairs:
        return {"payoff_rate": None, "payoff_completed_rate": None, "payoff_planned_rate": None,
                "open_setups": None, "planned_setups": 0, "completed_setups": 0, "total": 0}
    total = 0
    completed = 0
    planned = 0
    open_n = 0
    for p in pairs:
        if not isinstance(p, Mapping):
            continue
        total += 1
        status = str(p.get("status") or "").strip().lower()
        has_payoff = bool(str(p.get("payoff_ep") or "").strip())
        is_completed = status in {"done", "completed", "resolved", "closed", "已兑现", "完成"}
        is_planned = is_completed or has_payoff or status in {"ongoing", "planned", "scheduled", "in_progress", "进行中", "已规划"}
        if is_completed:
            completed += 1
        if is_planned:
            planned += 1
        else:
            open_n += 1
    completed_rate = round(completed / total, 4) if total else None
    planned_rate = round(planned / total, 4) if total else None
    return {"payoff_rate": completed_rate, "payoff_completed_rate": completed_rate,
            "payoff_planned_rate": planned_rate, "open_setups": open_n,
            "planned_setups": planned, "completed_setups": completed, "total": total}


def _clamp01(v: Any) -> Optional[float]:
    if not isinstance(v, (int, float)):
        return None
    return max(0.0, min(1.0, float(v)))


def _resolve_profile(signals: Mapping[str, Any]) -> str:
    raw = str(signals.get("profile") or os.environ.get("N2D_NARRATIVE_PROFILE") or "").strip().lower()
    if raw in _PROFILE_WEIGHTS:
        return raw
    if raw in {"prod", "release", "paid", "投放", "上线", "production_release"}:
        return "production"
    if raw in {"test", "sample", "pilot", "打样", "测试"}:
        return "demo"
    if raw in {"intl", "international", "global", "english", "海外", "出海"}:
        return "overseas"
    return "standard"


# ── I/O 采集（best-effort·缺则 None） ──────────────────────────────────────────

def _load_beat_audit():
    """按路径加载 n2d-script 的 beat_audit（同线 cross-skill·importlib·失败返回 None）。"""
    path = os.path.join(REPO_SKILLS, "n2d-script", "scripts", "beat_audit.py")
    try:
        spec = importlib.util.spec_from_file_location("n2d_beat_audit_for_kpi", path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _load_entity_schedule_audit():
    path = os.path.join(REPO_SKILLS, "n2d-script", "scripts", "entity_schedule_audit.py")
    try:
        spec = importlib.util.spec_from_file_location("n2d_entity_schedule_for_kpi", path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _load_setup_pairs(root: str) -> Optional[List[Mapping[str, Any]]]:
    for cand in (Path(root) / "设定库" / "setup_payoff_ledger.json",):
        try:
            data = json.loads(cand.read_text(encoding="utf-8"))
            pairs = data.get("pairs") or data.get("setups")
            if isinstance(pairs, list):
                return pairs
        except Exception:
            continue
    return None


def collect_narrative_signals(root: str) -> Dict[str, Any]:
    """从既有产物采集跨集叙事子信号（缺则该项 None·绝不臆造）。"""
    out: Dict[str, Any] = {"payoff_rate": None, "payoff_completed_rate": None, "payoff_planned_rate": None,
                           "open_setups": None, "planned_setups": None, "completed_setups": None,
                           "cold_open_chain_rate": None, "homogenization_max": None,
                           "emotion_variation": None, "narrative_atom_density": None,
                           "entity_schedule_coverage": None, "episodes_counted": None,
                           "profile": _infer_profile(root)}
    # 伏笔兑现
    pr = payoff_rate_from_ledger(_load_setup_pairs(root))
    out["payoff_rate"] = pr["payoff_rate"]
    out["payoff_completed_rate"] = pr["payoff_completed_rate"]
    out["payoff_planned_rate"] = pr["payoff_planned_rate"]
    out["open_setups"] = pr["open_setups"]
    out["planned_setups"] = pr["planned_setups"]
    out["completed_setups"] = pr["completed_setups"]

    beat = _load_beat_audit()
    if beat is not None:
        try:
            eps, dups = beat.audit_series(root)
            out["episodes_counted"] = len(eps)
            if dups:
                out["homogenization_max"] = max(float(d[2]) for d in dups)
            elif len(eps) >= 2:
                out["homogenization_max"] = 0.0  # 有≥2集且没检出重复 = 无同质化
        except Exception:
            pass
        try:
            _eps2, _states, _findings, rate = beat.cold_open_chain(root)
            out["cold_open_chain_rate"] = rate
        except Exception:
            pass
        try:
            out["emotion_variation"] = _emotion_variation(beat, root)
        except Exception:
            pass
        try:
            out["narrative_atom_density"] = _narrative_atom_density(beat, root)
        except Exception:
            pass
    try:
        out["entity_schedule_coverage"] = _entity_schedule_coverage(root)
    except Exception:
        pass
    return out


def _emotion_variation(beat, root: str) -> Optional[float]:
    """各集 [情绪] 标注的平均去重率（distinct/len，≥3 拍的集才计）。越高=情绪越有起伏。"""
    sdir = Path(root) / "脚本"
    ratios: List[float] = []
    for d in sorted(sdir.glob("第*集")):
        vpath = d / "voiceover.txt"
        if not vpath.exists():
            continue
        try:
            beats = beat.parse_voiceover(vpath)
        except Exception:
            continue
        emos = [b.get("emotion") for b in beats if b.get("emotion")]
        if len(emos) >= 3:
            ratios.append(len(set(emos)) / len(emos))
    if not ratios:
        return None
    return round(sum(ratios) / len(ratios), 4)


def _narrative_atom_density(beat, root: str) -> Optional[float]:
    """TNA-like 密度：每 4 拍至少一个状态变化/揭示/目标转折类原子。"""
    sdir = Path(root) / "脚本"
    ratios: List[float] = []
    for d in sorted(sdir.glob("第*集")):
        vpath = d / "voiceover.txt"
        if not vpath.exists():
            continue
        try:
            beats = beat.parse_voiceover(vpath)
        except Exception:
            continue
        if len(beats) < 3:
            continue
        atom_n = sum(1 for b in beats if NARRATIVE_ATOM_RE.search(str(b.get("text") or "")) or b.get("hooks"))
        target = max(1.0, len(beats) / 4.0)
        ratios.append(min(1.0, atom_n / target))
    if not ratios:
        return None
    return round(sum(ratios) / len(ratios), 4)


def _entity_schedule_coverage(root: str) -> Optional[float]:
    mod = _load_entity_schedule_audit()
    if mod is None:
        return None
    sdir = Path(root) / "脚本"
    vals: List[float] = []
    for d in sorted(sdir.glob("第*集")):
        if not (d / "storyboard.json").exists():
            continue
        res = mod.audit_episode(root, d.name)
        stats = res.get("stats") if isinstance(res, Mapping) else {}
        cov = stats.get("coverage") if isinstance(stats, Mapping) else None
        if isinstance(cov, (int, float)):
            vals.append(float(cov))
    if not vals:
        return None
    return round(sum(vals) / len(vals), 4)


def _infer_profile(root: str) -> str:
    raw = str(os.environ.get("N2D_NARRATIVE_PROFILE") or os.environ.get("N2D_SCORE_PROFILE") or "").strip()
    if raw:
        return _resolve_profile({"profile": raw})
    p = Path(root) / "_设置.md"
    try:
        text = p.read_text(encoding="utf-8").lower()
    except Exception:
        return "standard"
    if any(x in text for x in ("production", "付费", "投放", "上线", "发行", "douyin", "抖音")):
        return "production"
    if any(x in text for x in ("demo", "打样", "测试", "internal_only", "内部")):
        return "demo"
    if any(x in text for x in ("overseas", "english", "海外", "出海")):
        return "overseas"
    return "standard"


def narrative_kpi(root: str) -> Dict[str, Any]:
    """采集 + 聚合，一步到位。"""
    return build_narrative_kpi(collect_narrative_signals(root))


def render_markdown(kpi: Mapping[str, Any]) -> str:
    sc = kpi.get("narrative_continuity")
    if sc is None:
        return "## 长篇叙事一致性 KPI（报告型）\n\n- 缺跨集信号（伏笔账/多集 voiceover），暂不评估。\n"
    verdict_zh = {"above": "达标", "below": "低于参考线"}.get(kpi.get("verdict"), "—")
    subs = kpi.get("subscores", {})
    return (
        "## 长篇叙事一致性 KPI（报告型·非扣分·NarrLV/DirectorBench 轴）\n\n"
        f"- 叙事连续性：**{sc}** · profile {kpi.get('profile')} · 参考线 {kpi.get('release_line')} → **{verdict_zh}**（集数 {kpi.get('episodes_counted')}）\n"
        f"- 子分：伏笔已回收 {subs.get('payoff_completed')} · 伏笔已规划 {subs.get('payoff_planned')} · "
        f"冷开场链 {subs.get('cold_open_chain')} · 反套路 {subs.get('anti_trope')} · "
        f"情绪起伏 {subs.get('emotion_variation')} · 叙事原子 {subs.get('narrative_atom_density')} · "
        f"实体排程 {subs.get('entity_schedule')}"
        + (f" · 未填伏笔 {kpi.get('open_setups')}" if kpi.get("open_setups") else "") + "\n"
        f"- 基准：{kpi.get('benchmark_ref')}\n"
    )


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="长篇叙事一致性 KPI（报告型）")
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    kpi = narrative_kpi(ns.root.rstrip("/"))
    print(json.dumps(kpi, ensure_ascii=False, indent=2) if ns.json else render_markdown(kpi))
    return 0


if __name__ == "__main__":
    sys.exit(main())
