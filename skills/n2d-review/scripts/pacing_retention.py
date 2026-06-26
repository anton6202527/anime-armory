#!/usr/bin/env python3
"""节奏/留存机检（advisory）——给 rhythm_density 补可重复的启发式审计。

背景：节奏体感无可靠强检，**不该被普通 gate 直接硬闸**。但「无强检」≠「零机检」：
基于已有结构化数据（`storyboard.json` 的镜头时长序列 / rhythm 标注，
可选成片/SRT 时长）能做**启发式留存预测**，对照短剧基准给一个 0-100 advisory 分 + 定位风险镜，
比纯人判多一条可重复的证据链。2026 行业已有发布前观感/留存预测做法（前3秒钩子强度、pacing/留存
曲线、镜头时长节奏密度，对照短剧基准）——本脚本把这套落成**纯启发式、无外部模型**的旁路评估器。

诚实边界（与 lipsync_consistency 同级·advisory）：
  这只是**启发式代理**，不是真观感模型——它读不到成片画面，只数镜头时长/类型/标注。故全程 advisory：
    · 脚本自身 `verdict` 一律封顶到 `warn`（不把启发式预测直接写成 block）；
    · 证据不足（无 storyboard / clips[] 太少）→ 整维 `inconclusive`，交人判，**绝不臆造分**；
    · consistency_audit 会汇总本维度；production profile 可由 gate 对重复/关键场景问题升级或要求签收。

基准来源（自标定·带采集日期·可 env 覆盖，不写死成铁律）：
  默认读取 `n2d-dashboard/references/industry_benchmark.json` 的 `retention_benchmarks.proxy_thresholds`
  （2026-06-25 采集），再由环境变量覆盖；缺文件时退回本仓 `n2d/references/导演节奏.md`
  的镜头时长曲线（铺垫 3-5s/镜、爽点碎切 1-2s/镜、钩子间隔 15-20s、0-3s 立冷开场钩）。
  基准会随平台变，别当死律。
  **provenance 诚实（GAP-1·2026-06-25 流程自审实搜）**：其中 `density_slow_per_min`(10) /
  `density_fast_per_min`(45) 的「镜/分钟」带、以及 beat_audit 的「每 15-20s 一钩」间隔，
  都是**内部启发式**——短剧 CPM/SPM 与「每 N 秒一钩」**无可辩护的公开基准**（实搜确认）。
  benchmark JSON 已用 `n2d_internal_pacing_heuristic_2026` 源把这两项标为 confidence=low 的
  internal-heuristic（非市场背书），本脚本只作 advisory 旁路，绝不据此 gate；真值须由
  n2d-feedback 第一方留存数据校准。

落地产物：main() 写 `生产数据/pacing_retention_第N集.json`（blocks/warnings/infos/evidence/metrics），
参照 lipsync_consistency.py 写 `生产数据/lipsync_第N集.json` 的既有模式，供 n2d-score 旁路消费。
n2d-score 侧的读取留作 follow-up（见文末 NOTE）——本次只加「写 json」这一侧，不改 score 主逻辑。

纯函数部分（评分 / 基准对照 / 风险镜定位）无依赖、带 pytest。

用法：python3 pacing_retention.py <作品根> 第N集 [--json] [--no-write-report]
退出码：永远 0（本脚本 advisory；缺数据也 0，交人判不臆造）。
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from typing import Any, Dict, List, Optional, Sequence

# ── 基准阈值（benchmark json + env 覆盖 + 本仓 导演节奏.md fallback；非铁律）──

_BENCHMARK_CACHE: Optional[dict] = None


def _default_benchmark_path() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d-dashboard", "references", "industry_benchmark.json"))


def _load_benchmark() -> dict:
    """读取行业基准文件；失败返回空 dict，保证本脚本可离线运行。"""
    global _BENCHMARK_CACHE
    if _BENCHMARK_CACHE is not None:
        return _BENCHMARK_CACHE
    path = os.environ.get("N2D_PACE_BENCHMARK_JSON") or _default_benchmark_path()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        _BENCHMARK_CACHE = data if isinstance(data, dict) else {}
    except Exception:
        _BENCHMARK_CACHE = {}
    return _BENCHMARK_CACHE


def _bench_value(name: str, default: float) -> float:
    bench = _load_benchmark()
    rb = bench.get("retention_benchmarks") if isinstance(bench, dict) else None
    thresholds = rb.get("proxy_thresholds") if isinstance(rb, dict) else None
    if isinstance(thresholds, dict):
        try:
            value = thresholds.get(name)
            if value not in (None, ""):
                return float(value)
        except Exception:
            pass
    return default


def _env_float(name: str, default: float) -> float:
    """读环境变量覆盖阈值（缺/坏 → 默认）。让基准可调而不改源码。"""
    try:
        v = os.environ.get(name)
        return float(v) if v is not None and v != "" else default
    except Exception:
        return default


# 黄金前3秒钩子：开场镜该是冷开场/钩子、且不宜过长（长开场镜 = 慢热 = 前3秒掉留存）。
HOOK_WINDOW_SEC = _env_float("N2D_PACE_HOOK_WINDOW_SEC", _bench_value("hook_window_sec", 3.0))     # 「黄金前几秒」窗口
HOOK_MAX_OPEN_SHOT_SEC = _env_float("N2D_PACE_HOOK_OPEN_MAX_SEC", _bench_value("open_shot_max_sec", 5.0))  # 开场镜超此 → 慢热风险
# 短剧留存基准（代理目标，非实测留存）：前3秒留存>80%、中点>60%——本脚本把它们当「钩子/中段不能塌」的目标线。
RETENTION_HOOK_FLOOR = _env_float("N2D_PACE_RETENTION_HOOK_FLOOR", _bench_value("retention_hook_floor", 0.80))  # 前3秒留存目标
RETENTION_MID_FLOOR = _env_float("N2D_PACE_RETENTION_MID_FLOOR", _bench_value("retention_mid_floor", 0.60))    # 中点留存目标

# pacing 密度（镜/分钟）：太慢像 PPT、太快疲劳跳出。区间取自 导演节奏 + 短剧普遍密度。
DENSITY_SLOW_PER_MIN = _env_float("N2D_PACE_DENSITY_SLOW", _bench_value("density_slow_per_min", 10.0))   # < 此 → 偏慢
DENSITY_FAST_PER_MIN = _env_float("N2D_PACE_DENSITY_FAST", _bench_value("density_fast_per_min", 45.0))   # ≥ 此 → 过密

# 留存曲线代理：长镜聚集 = 掉留存风险点。单镜超此算「长镜」；连续长镜 ≥ 聚集阈 → 风险段。
LONG_SHOT_SEC = _env_float("N2D_PACE_LONG_SHOT_SEC", _bench_value("long_shot_sec", 6.0))          # 超此算长镜
LONG_CLUSTER_MIN = int(_env_float("N2D_PACE_LONG_CLUSTER_MIN", _bench_value("long_cluster_min", 3)))  # 连续长镜 ≥ 此 → 聚集风险

# advisory 分下限：低于此 n2d-score 该重点看（但仍不 gate）。
ADVISORY_WARN_FLOOR = _env_float("N2D_PACE_WARN_FLOOR", _bench_value("advisory_warn_floor", 70.0))

# 评分至少要几个 clip 才可信（太少 → inconclusive，不臆造分）。
MIN_CLIPS_FOR_SCORE = int(_env_float("N2D_PACE_MIN_CLIPS", _bench_value("min_clips_for_score", 4)))

# 开场钩信号关键词（命中 rhythm/label/标注 → 认为开场是钩子，与 导演节奏 的「冷开场/倒叙钩」同口径）。
HOOK_MARKERS = (
    "冷开场", "钩子", "倒叙", "悬念", "开场钩", "cold open", "hook", "cliffhanger",
    "反转", "断点", "爆", "⚡", "💥", "🪝",
)
# 长镜/铺垫标注关键词（用于交叉印证长镜聚集是不是「有意铺垫」）。
SLOW_MARKERS = ("铺垫", "长镜", "留白", "定格", "空镜", "沉淀", "慢")

# ── 静音首屏（muted-first-screen）markers ──
# 2026 投放硬现实：信息流**静音自动播放 + 后期配音字幕**，首屏 0-3s 必须在「关声」下也能抓人。
# 若开场钩只靠旁白/台词「声音」承载、画面无冲突且无烧屏字幕/标题卡，静音观众=白给（直接掉钩）。
# 视觉/烧屏文字钩 = 静音下仍可读的钩；结构视觉钩（冷开场/倒叙/断点/cliffhanger）本就是画面跳入，算安全。
VISUAL_HOOK_MARKERS = (
    "画面", "视觉", "特写", "近景", "大特写", "冲突", "动作", "打斗", "打", "摔", "撞", "扇", "掌掴",
    "血", "脸", "表情", "瞪", "奔", "追", "逃", "爆炸", "火", "刀", "剑", "定格", "特效", "vfx",
)
ONSCREEN_TEXT_MARKERS = (
    "字幕", "标题", "标题卡", "大字", "弹幕", "字卡", "题板", "花字", "title", "caption", "text",
)
# 结构性视觉钩：本身即「画面跳入」，静音下也成立——与 HOOK_MARKERS 里偏声音/内容的（悬念/钩子/反转词）区分。
STRUCTURAL_VISUAL_HOOK = ("冷开场", "倒叙", "断点", "cold open", "cliffhanger", "🪝", "⚡", "💥")


# ---------- 纯数学/启发式核心（无依赖 · pytest 覆盖） ----------

def shot_durations(clips: Sequence[dict]) -> List[float]:
    """从 clips 抽镜头时长序列（>0 才计）。纯函数·可测。"""
    out: List[float] = []
    for c in clips:
        if not isinstance(c, dict):
            continue
        try:
            d = float(c.get("duration") or 0)
        except Exception:
            continue
        if d > 0:
            out.append(d)
    return out


def shot_density_per_min(n_shots: int, total_sec: float) -> float:
    """镜/分钟。total_sec≤0 → 0（不除零）。纯函数·可测。"""
    if total_sec <= 0:
        return 0.0
    return n_shots / total_sec * 60.0


def is_hook_text(text: str) -> bool:
    """文本命中任一开场钩信号 → True。纯函数·可测。"""
    low = (text or "").lower()
    return any(m.lower() in low for m in HOOK_MARKERS)


def is_slow_text(text: str) -> bool:
    """文本命中长镜/铺垫标注 → True（用于印证有意铺垫）。纯函数·可测。"""
    low = (text or "").lower()
    return any(m.lower() in low for m in SLOW_MARKERS)


def is_muted_safe_hook(text: str) -> bool:
    """首屏钩在静音下是否仍可读：命中视觉钩 ∪ 烧屏文字钩 ∪ 结构视觉钩 → True。纯函数·可测。

    用来区分「靠画面/字幕抓人（静音安全）」vs「只靠旁白声音抓人（静音掉钩）」。
    保守：命中任一视觉/文字/结构信号即算安全，宁放过不误杀（advisory 不该噪）。"""
    low = (text or "").lower()
    for group in (VISUAL_HOOK_MARKERS, ONSCREEN_TEXT_MARKERS, STRUCTURAL_VISUAL_HOOK):
        if any(m.lower() in low for m in group):
            return True
    return False


def _clip_text(clip: dict) -> str:
    """汇聚一个 clip 上能体现节奏意图的标注文本（rhythm/label/标注…）。"""
    if not isinstance(clip, dict):
        return ""
    parts = [
        str(clip.get("rhythm") or ""),
        str(clip.get("label") or ""),
        str(clip.get("note") or clip.get("标注") or ""),
        str(clip.get("shot_size") or ""),
    ]
    return " ".join(p for p in parts if p)


# 静音首屏扣分：首屏是钩子、但钩点疑似纯声音/旁白（无画面冲突/无烧屏字幕）→ 静音掉钩。
MUTED_HOOK_PENALTY = _env_float("N2D_PACE_MUTED_PENALTY", 15.0)


def hook_strength(clips: Sequence[dict],
                  hook_window: float = HOOK_WINDOW_SEC,
                  open_max: float = HOOK_MAX_OPEN_SHOT_SEC) -> dict:
    """黄金前3秒钩子信号强度（0-100 子分）。开场镜：是钩子类型 + 不过长 + 落在窗口内 + 静音可读 → 高分。
    无 clips → score=None（交人判，不臆造）。纯函数·可测。"""
    if not clips:
        return {"score": None, "reasons": ["无 clips，开场钩无法评估"],
                "open_is_hook": None, "muted_safe": None}
    first = clips[0] if isinstance(clips[0], dict) else {}
    text = _clip_text(first)
    is_hook = is_hook_text(text)
    muted_safe = is_muted_safe_hook(text)
    try:
        open_dur = float(first.get("duration") or 0)
    except Exception:
        open_dur = 0.0
    score = 100.0
    reasons: List[str] = []
    if not is_hook:
        score -= 45.0
        reasons.append(f"开场镜未见冷开场/钩子标注（rhythm/label=『{text[:24]}』），疑慢热")
    elif not muted_safe:
        # 是钩子但只靠声音/旁白承载（不再叠加在非钩子的 -45 上，避免双罚）。
        score -= MUTED_HOOK_PENALTY
        reasons.append("首屏钩疑仅靠声音/旁白承载（无画面冲突 / 无烧屏字幕·标题卡）："
                       "信息流静音自动播放下掉钩——首帧给可视冲突或烧一行钩子字幕/标题卡")
    if open_dur > open_max:
        score -= 30.0
        reasons.append(f"开场镜时长 {open_dur:.1f}s > {open_max:.0f}s，前3秒易掉留存")
    elif open_dur <= 0:
        score -= 15.0
        reasons.append("开场镜缺时长，无法确认前3秒节奏")
    score = max(0.0, min(100.0, score))
    return {"score": round(score, 1), "reasons": reasons or ["开场即钩子、不冗长且静音可读，前3秒钩稳"],
            "open_is_hook": is_hook, "muted_safe": muted_safe, "open_dur": round(open_dur, 2)}


def pacing_score(durations: Sequence[float],
                 slow_per_min: float = DENSITY_SLOW_PER_MIN,
                 fast_per_min: float = DENSITY_FAST_PER_MIN) -> dict:
    """pacing 密度子分（0-100）。密度落在 [slow, fast) → 满分；越界按距离扣。
    无镜 → score=None。纯函数·可测。"""
    durs = [d for d in durations if d > 0]
    if not durs:
        return {"score": None, "density_per_min": None, "reasons": ["无有效镜头时长，密度无法评估"]}
    total = sum(durs)
    density = shot_density_per_min(len(durs), total)
    score = 100.0
    reasons: List[str] = []
    if density < slow_per_min:
        score -= min(50.0, (slow_per_min - density) / max(slow_per_min, 1e-6) * 60.0)
        reasons.append(f"镜头密度 {density:.1f}/min < {slow_per_min:.0f}，偏慢像 PPT，中段易划走")
    elif density >= fast_per_min:
        score -= min(40.0, (density - fast_per_min) / max(fast_per_min, 1e-6) * 50.0)
        reasons.append(f"镜头密度 {density:.1f}/min ≥ {fast_per_min:.0f}，过密疲劳易跳出")
    score = max(0.0, min(100.0, score))
    return {"score": round(score, 1), "density_per_min": round(density, 2),
            "total_sec": round(total, 2), "shot_count": len(durs),
            "reasons": reasons or [f"镜头密度 {density:.1f}/min 在健康区间"]}


def long_shot_clusters(clips: Sequence[dict],
                       long_sec: float = LONG_SHOT_SEC,
                       cluster_min: int = LONG_CLUSTER_MIN) -> List[dict]:
    """留存曲线代理：定位「连续长镜聚集」风险段（长镜堆叠 = 节奏塌 = 掉留存）。
    返回每段 {start_idx,end_idx,clip_ids,length,intentional}。有铺垫标注 → intentional=True（降权）。
    纯函数·可测。"""
    risks: List[dict] = []
    run: List[int] = []
    for i, c in enumerate(clips):
        try:
            d = float(c.get("duration") or 0) if isinstance(c, dict) else 0.0
        except Exception:
            d = 0.0
        if d >= long_sec:
            run.append(i)
        else:
            if len(run) >= cluster_min:
                risks.append(_make_cluster(clips, run))
            run = []
    if len(run) >= cluster_min:
        risks.append(_make_cluster(clips, run))
    return risks


def _make_cluster(clips: Sequence[dict], idxs: Sequence[int]) -> dict:
    ids = [str(clips[i].get("id") or clips[i].get("label") or f"#{i+1}")
           if isinstance(clips[i], dict) else f"#{i+1}" for i in idxs]
    intentional = all(is_slow_text(_clip_text(clips[i])) if isinstance(clips[i], dict) else False
                      for i in idxs)
    return {"start_idx": idxs[0], "end_idx": idxs[-1], "clip_ids": ids,
            "length": len(idxs), "intentional": intentional}


def retention_proxy_score(durations: Sequence[float], clusters: Sequence[dict]) -> dict:
    """留存曲线代理子分（0-100）：镜头时长方差越平（等长堆叠=催眠）越扣；非有意长镜聚集越多越扣。
    无镜 → score=None。纯函数·可测。"""
    durs = [d for d in durations if d > 0]
    if len(durs) < 2:
        return {"score": None, "reasons": ["镜头不足，留存曲线代理无法评估"], "cv": None}
    mean = statistics.fmean(durs)
    stdev = statistics.pstdev(durs)
    cv = (stdev / mean) if mean > 0 else 0.0  # 变异系数：节奏「有快慢」的度量
    score = 100.0
    reasons: List[str] = []
    if cv < 0.25:
        score -= 30.0
        reasons.append(f"镜头时长变异系数 {cv:.2f} 偏低（近等长堆叠），节奏平像催眠")
    bad_clusters = [c for c in clusters if not c.get("intentional")]
    if bad_clusters:
        score -= min(45.0, 15.0 * len(bad_clusters))
        reasons.append(f"{len(bad_clusters)} 段非铺垫长镜聚集，掉留存风险点")
    score = max(0.0, min(100.0, score))
    return {"score": round(score, 1), "cv": round(cv, 3),
            "long_clusters": len(clusters), "risky_clusters": len(bad_clusters),
            "reasons": reasons or [f"镜头时长有快慢呼吸（CV {cv:.2f}），无失控长镜聚集"]}


def advisory_total(hook: dict, pacing: dict, retention: dict) -> Optional[float]:
    """三子分加权成 0-100 advisory 总分（钩子 40% / pacing 30% / 留存 30%）。
    任一子分为 None（证据不足）则该轴退出加权，按剩余轴归一；全 None → None（inconclusive）。纯函数·可测。"""
    weighted = [(hook.get("score"), 0.40), (pacing.get("score"), 0.30), (retention.get("score"), 0.30)]
    avail = [(s, w) for s, w in weighted if s is not None]
    if not avail:
        return None
    wsum = sum(w for _, w in avail)
    return round(sum(s * w for s, w in avail) / wsum, 1)


def advisory_verdict(score: Optional[float], warn_floor: float = ADVISORY_WARN_FLOOR) -> str:
    """总分 → advisory verdict（封顶 warn，绝不 block）：
      None        → 'inconclusive'（证据不足，交人判，不罚分）；
      < warn_floor → 'warn'（节奏/留存偏弱，建议看）；
      其余         → 'ok'。纯函数·可测。"""
    if score is None:
        return "inconclusive"
    if score < warn_floor:
        return "warn"
    return "ok"


# ---------- 输入读取（尽力而为·缺则空·与 I/O 分离） ----------

def _read_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def load_storyboard(root: str, ep: str) -> Optional[dict]:
    """读 脚本/<集>/storyboard.json（与 n2d-score visual_checks 同路径）。缺/坏 → None。"""
    data = _read_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    return data if isinstance(data, dict) else None


def storyboard_clips(sb: Optional[dict]) -> List[dict]:
    if not sb:
        return []
    return [c for c in sb.get("clips", []) if isinstance(c, dict)]


# ---------- 编排（纯数据 → 报告，I/O 独立） ----------

def analyze(root: str, ep: str) -> dict:
    """读 storyboard → 三轴启发式 → advisory 总分 + 风险镜。缺数据优雅 inconclusive，绝不臆造分。"""
    res: dict = {"available": False, "verdict": "inconclusive", "score": None,
                 "hook": {}, "pacing": {}, "retention": {}, "risk_shots": [], "notes": []}
    sb = load_storyboard(root, ep)
    clips = storyboard_clips(sb)
    if not clips:
        res["notes"].append(
            "缺 storyboard.json 或 clips[]，节奏/留存机检跳过——交人判（对 n2d/references/导演节奏.md）。")
        return res
    if len(clips) < MIN_CLIPS_FOR_SCORE:
        res["notes"].append(
            f"clips 仅 {len(clips)} 个（< {MIN_CLIPS_FOR_SCORE}），样本太少不臆造分，交人判。")
        res["available"] = False
        return res

    durs = shot_durations(clips)
    hook = hook_strength(clips)
    pacing = pacing_score(durs)
    clusters = long_shot_clusters(clips)
    retention = retention_proxy_score(durs, clusters)
    total = advisory_total(hook, pacing, retention)
    verdict = advisory_verdict(total)

    risk_shots: List[dict] = []
    for c in clusters:
        if c.get("intentional"):
            continue
        risk_shots.append({
            "clips": c["clip_ids"],
            "kind": "long_shot_cluster",
            "verdict": "warn",
            "message": f"连续 {c['length']} 个长镜聚集（{'→'.join(c['clip_ids'])}），疑节奏塌·掉留存",
        })
    first_id = str(clips[0].get("id") or clips[0].get("label") or "#1")
    if hook.get("open_is_hook") is False or (hook.get("score") is not None and hook["score"] < 60):
        risk_shots.append({
            "clips": [first_id], "kind": "weak_hook", "verdict": "warn",
            "message": "；".join(hook.get("reasons", [])) or "开场钩偏弱",
        })
    elif hook.get("open_is_hook") and hook.get("muted_safe") is False:
        # 是钩子、分也没塌，但只靠声音——单列「静音首屏」风险镜，别被均分掩盖。
        risk_shots.append({
            "clips": [first_id], "kind": "muted_first_screen", "verdict": "warn",
            "message": "首屏钩疑仅靠声音/旁白，信息流静音自动播放下掉钩——"
                       "首帧补可视冲突或烧屏钩子字幕/标题卡",
        })

    res.update(available=True, verdict=verdict, score=total,
               hook=hook, pacing=pacing, retention=retention, risk_shots=risk_shots)
    res["notes"].append(
        f"advisory 节奏/留存分 {total}（钩子{hook.get('score')}/pacing{pacing.get('score')}"
        f"/留存{retention.get('score')}）——脚本自身不写 block；consistency_audit/gate 按 profile 汇总和升级。")
    return res


def to_score_report(res: dict) -> dict:
    """analyze 结果 → n2d-score 可消费报告（blocks/warnings/infos/evidence/metrics）。
    blocks 恒 0（advisory 不硬阻断）；warnings 数风险镜 + 低分；不可用 → 全 0 + skip 证据。纯函数·可测。"""
    risk = res.get("risk_shots", [])
    evidence: List[str] = []
    warnings = 0
    if not res.get("available"):
        evidence.extend(res.get("notes", []))
        return {"blocks": 0, "warnings": 0, "infos": 0, "evidence": evidence,
                "metrics": {"available": False, "verdict": "inconclusive", "score": None}}
    warnings += len(risk)
    if res.get("verdict") == "warn":
        warnings += 1
        evidence.append(f"节奏/留存 advisory 分 {res.get('score')} 偏低（< {ADVISORY_WARN_FLOOR:.0f}），建议看")
    for r in risk[:12]:
        evidence.append(f"{'/'.join(r['clips'])}: {r['message']}")
    infos = 1 if res.get("verdict") == "ok" and not risk else 0
    if infos:
        evidence.append(f"节奏/留存 advisory 通过：分 {res.get('score')}（无风险镜）")
    return {
        "blocks": 0,  # advisory 永不硬阻断 gate
        "warnings": warnings,
        "infos": infos,
        "evidence": evidence,
        "metrics": {
            "available": True,
            "verdict": res.get("verdict"),
            "score": res.get("score"),
            "hook_score": res.get("hook", {}).get("score"),
            "pacing_score": res.get("pacing", {}).get("score"),
            "retention_score": res.get("retention", {}).get("score"),
            "density_per_min": res.get("pacing", {}).get("density_per_min"),
            "risk_shot_count": len(risk),
        },
    }


def write_score_report(root: str, ep: str, res: dict) -> str:
    """写 生产数据/pacing_retention_<集>.json，供 n2d-score 旁路消费（参照 lipsync_<集>.json 模式）。"""
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"pacing_retention_{ep}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(to_score_report(res), fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="n2d 节奏/留存机检（advisory 旁路）")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write-report", action="store_true",
                    help="不写 生产数据/pacing_retention_<集>.json（默认会写，供 n2d-score 消费）")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    res = analyze(root, ns.episode)
    if not ns.no_write_report and os.path.isdir(ns.root):
        write_score_report(root, ns.episode, res)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"=== 节奏/留存机检（advisory）：{root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    icon = {"warn": "⚠️", "ok": "·", "inconclusive": "·"}
    for r in res["risk_shots"]:
        print(f"{icon.get(r['verdict'], '·')} {'/'.join(r['clips'])}: {r['message']}")
    print(f"\nadvisory 总分 {res['score']}（verdict={res['verdict']}）·风险镜 {len(res['risk_shots'])}"
          "（脚本自身不阻断；consistency_audit/gate 会按 profile 汇总和升级）")
    return 0


# NOTE（已接·2026-06-25 流程自审）：n2d-score 的 visual_checks.check_final_rhythm_density 现已
# 经 `_fold_pacing_advisory` 折入本报告（hook_strength/留存代理/风险镜 + 静音首屏）——成片侧密度/
# hook_interval 仍是 post-compose 硬闸，本 storyboard 态 advisory 叠加为补充证据（advisory 永不
# block，折入时即便误写 block 也降为 warn）。即"score 消死胡同"已闭合，这份报告不再只喂 consistency_audit。

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
