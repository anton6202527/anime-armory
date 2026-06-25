#!/usr/bin/env python3
"""Platform performance feedback for n2d."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import glob
import json
import os
import re
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  生产数据目录 / kind 单一真值源
    CONSISTENCY_FINDINGS_KIND,
    PLATFORM_FEEDBACK_KIND,
    PRODUCTION_DIR,
    normalize_finding,
    production_dir,
)
from n2d_settings import load_settings  # noqa: E402  _设置.md 解析单一真值源

VERSION = 1
KIND = PLATFORM_FEEDBACK_KIND
# 15s 留存低于此线 + 有一致性 block → 触发优先返工写回信号（投放反哺闭环回火端）
LOW_RETENTION_15S = 0.5

START_MARKER = "<!-- n2d-feedback:start -->"
END_MARKER = "<!-- n2d-feedback:end -->"
AUTO_FEATURES_FILENAME = "creative_features.auto.json"
UNKNOWN = "unknown"

# 投放→生成输入闭环的「写端」：把 A/B paired-lift 胜出变体凝成机器可读的第一方先验，
# 给 n2d-script 阶段2 finalize 当开场/断点设计先验读（第一方实测先验：本线投放实测，权重高于通用经验）。
# kind 本线自定义（不进 n2d/_lib 共享常量），消费端按 kind 校验。
CREATIVE_PRIORS_KIND = "n2d_creative_priors"
CREATIVE_PRIORS_FILENAME = "creative_priors.json"
CREATIVE_PRIORS_VERSION = 1
# A/B 维度 → 先验字段 / 取胜的 paired-lift 主指标。顺序即报告呈现顺序。
CREATIVE_PRIOR_DIMENSIONS: Tuple[Tuple[str, str, str], ...] = (
    ("opening_variant", "ab_opening_retention", "retention_3s"),
    ("cliffhanger_cut_variant", "ab_cliffhanger_follow", "follow_next_rate"),
    ("cover_variant", "ab_cover_retention", "retention_3s"),
    ("title_variant", "ab_title_retention", "retention_3s"),
)

CONFLICT_WORDS = (
    "赐死", "鸩酒", "追杀", "围住", "抓住", "拖走", "刺", "刀", "剑", "血", "死", "杀",
    "危机", "威胁", "压迫", "冲入", "逼近", "倒下", "跪", "审问", "对峙",
)
REVERSE_WORDS = ("倒叙", "闪回", "回忆", "记忆", "未来", "预告", "十七年前", "前世", "上一世")
SYSTEM_WORDS = ("系统", "任务", "面板", "奖励", "光幕", "弹出", "未公开")
DIALOGUE_WORDS = ("台词", "质问", "问道", "开口", "冷笑", "对白", "你", "我", "他说", "她说")
SPECTACLE_WORDS = ("法术", "妖气", "金光", "雷劫", "飞升", "神界", "爆发", "阵法", "大阵", "御剑")
TRUTH_WORDS = ("真相", "身份", "秘密", "未公开", "露出", "认出", "揭开", "原来", "竟", "居然")
REVERSAL_WORDS = ("反转", "突然", "却", "下一刻", "觉醒", "变成", "异变", "信号", "预告")
RESOLVED_WORDS = ("结束", "平静", "离去", "收束", "定格", "落幕", "讲完", "解决")
HOOK_WORDS = CONFLICT_WORDS + REVERSE_WORDS + SYSTEM_WORDS + SPECTACLE_WORDS + TRUTH_WORDS + REVERSAL_WORDS + (
    "钩子", "爽点", "悬念", "信息增量", "硬切", "action_cut", "hard_cut",
)


from n2d_route import normalize_episode  # noqa: E402  集号单一真值源


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def text_value(value: Any) -> str:
    return str(value or "").strip()


def first_text(row: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = text_value(row.get(key))
        if value:
            return value
    return ""


def normalize_variant_id(value: Any) -> str:
    text = text_value(value)
    return text or "base"


def episode_sort_key(value: Any) -> Tuple[int, str]:
    text = normalize_episode(value)
    match = re.search(r"\d+", text)
    return (int(match.group(0)) if match else 10**9, text)


def default_input(root: str, stem: str) -> Optional[str]:
    base = production_dir(root)
    for ext in ("csv", "jsonl", "json"):
        path = os.path.join(base, f"{stem}.{ext}")
        if os.path.isfile(path):
            return path
    return None


def parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"-", "—", "null", "None"}:
        return None
    if text.endswith("%"):
        return float(text[:-1]) / 100.0
    return float(text)


def read_records(path: str) -> List[Dict[str, Any]]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return [dict(row) for row in csv.DictReader(fh)]
    if ext == ".jsonl":
        rows = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return [dict(row) for row in data]
    if isinstance(data, dict):
        for key in ("records", "metrics", "features", "rows"):
            if isinstance(data.get(key), list):
                return [dict(row) for row in data[key]]
    raise ValueError(f"unsupported JSON shape: {path}")


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", normalize_episode(ep), "storyboard.json")


def discover_storyboard_episodes(root: str) -> List[str]:
    base = os.path.join(root, "脚本")
    if not os.path.isdir(base):
        return []
    episodes = []
    for name in os.listdir(base):
        path = os.path.join(base, name, "storyboard.json")
        if os.path.isfile(path):
            episodes.append(normalize_episode(name))
    return sorted(episodes, key=episode_sort_key)


def load_storyboard(root: str, ep: str) -> Optional[Dict[str, Any]]:
    path = storyboard_path(root, ep)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else None


def flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return " ".join(flatten_text(item) for item in value)
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            parts.append(str(key))
            parts.append(flatten_text(item))
        return " ".join(parts)
    return str(value)


def contains_any(text: str, words: Sequence[str]) -> bool:
    return any(word in text for word in words)


def clip_duration(clip: Dict[str, Any]) -> float:
    value = numeric_feature(clip, "duration")
    return max(0.0, value or 0.0)


def storyboard_total_duration(storyboard: Dict[str, Any], clips: List[Dict[str, Any]]) -> float:
    value = numeric_feature(storyboard, "total_duration")
    if value and value > 0:
        return value
    return sum(clip_duration(clip) for clip in clips)


def first_window_text(clips: List[Dict[str, Any]], window_sec: float = 15.0) -> str:
    parts = []
    elapsed = 0.0
    for clip in clips:
        if elapsed >= window_sec and parts:
            break
        parts.append(flatten_text(clip))
        elapsed += clip_duration(clip)
    return " ".join(parts)


def classify_opening(clips: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    if not clips:
        return "unknown", 0.0, ["no_clips"]
    first = flatten_text(clips[0])
    window = first_window_text(clips)
    rhythm = str(clips[0].get("rhythm") or "")
    signals: List[str] = []
    if contains_any(first, CONFLICT_WORDS):
        signals.append("first_clip_conflict")
        return "cold_conflict", 0.88, signals
    if contains_any(first, SYSTEM_WORDS):
        signals.append("first_clip_system_hook")
        return "system_hook", 0.84, signals
    if contains_any(first, REVERSE_WORDS):
        signals.append("first_clip_reverse_flash")
        return "reverse_flash", 0.82, signals
    if contains_any(first, SPECTACLE_WORDS):
        signals.append("first_clip_spectacle")
        return "spectacle_hook", 0.78, signals
    if contains_any(first, DIALOGUE_WORDS):
        signals.append("first_clip_dialogue")
        return "dialogue_hook", 0.70, signals
    if "爽点" in rhythm or "加速" in rhythm:
        signals.append(f"first_rhythm={rhythm}")
        return "cold_conflict", 0.64, signals
    if contains_any(window, CONFLICT_WORDS):
        signals.append("first_15s_conflict")
        return "cold_conflict", 0.62, signals
    if contains_any(window, REVERSE_WORDS):
        signals.append("first_15s_reverse")
        return "reverse_flash", 0.58, signals
    signals.append("no_strong_opening_signal")
    return "slow_lore", 0.45, signals


def classify_cliffhanger(clips: List[Dict[str, Any]]) -> Tuple[str, float, List[str]]:
    if not clips:
        return "unknown", 0.0, ["no_clips"]
    tail = " ".join(flatten_text(clip) for clip in clips[-2:])
    last = flatten_text(clips[-1])
    signals: List[str] = []
    if contains_any(tail, CONFLICT_WORDS):
        signals.append("tail_crisis")
        return "crisis_suspend", 0.82, signals
    if contains_any(tail, TRUTH_WORDS):
        signals.append("tail_truth_signal")
        return "truth_half_reveal", 0.78, signals
    if contains_any(tail, REVERSAL_WORDS) or contains_any(last, SYSTEM_WORDS):
        signals.append("tail_reversal_signal")
        return "reversal_signal", 0.74, signals
    if contains_any(last, RESOLVED_WORDS):
        signals.append("tail_resolved")
        return "resolved_clean", 0.62, signals
    signals.append("weak_tail_signal")
    return "resolved_clean", 0.42, signals


def hook_score(clip: Dict[str, Any], *, idx: int, last_idx: int, opening_type: str, cliffhanger_type: str) -> Tuple[int, List[str]]:
    text = flatten_text(clip)
    rhythm = str(clip.get("rhythm") or "")
    continuity = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    transition = str(continuity.get("transition") or "")
    score = 0
    signals: List[str] = []
    if contains_any(text, HOOK_WORDS):
        score += 2
        signals.append("hook_words")
    if "爽点" in rhythm:
        score += 2
        signals.append("rhythm_climax")
    elif "加速" in rhythm:
        score += 1
        signals.append("rhythm_accel")
    if transition in {"hard_cut", "action_cut"}:
        score += 1
        signals.append(f"transition={transition}")
    if idx == 0 and opening_type not in {"slow_lore", "unknown"}:
        score += 1
        signals.append("opening_hook")
    if idx == last_idx and cliffhanger_type not in {"resolved_clean", "unknown"}:
        score += 2
        signals.append("tail_hook")
    return score, signals


def infer_hook_interval(clips: List[Dict[str, Any]], total_duration: float, opening_type: str, cliffhanger_type: str) -> Tuple[Optional[float], int, List[str]]:
    if not clips or total_duration <= 0:
        return None, 0, ["missing_duration"]
    hook_times: List[float] = []
    signals: List[str] = []
    elapsed = 0.0
    last_idx = len(clips) - 1
    for idx, clip in enumerate(clips):
        score, clip_signals = hook_score(clip, idx=idx, last_idx=last_idx, opening_type=opening_type, cliffhanger_type=cliffhanger_type)
        if score >= 3:
            hook_times.append(round(elapsed, 3))
            label = clip.get("label") or clip.get("id") or f"clip{idx + 1}"
            signals.append(f"{label}:{'+'.join(clip_signals)}")
        elapsed += clip_duration(clip)
    if not hook_times:
        return None, 0, ["no_hook_signal"]
    if len(hook_times) == 1:
        return round(total_duration, 3), 1, signals
    gaps = [b - a for a, b in zip(hook_times, hook_times[1:]) if b > a]
    if not gaps:
        return round(total_duration / len(hook_times), 3), len(hook_times), signals
    return round(sum(gaps) / len(gaps), 3), len(hook_times), signals


def extract_storyboard_features(root: str, episodes: Optional[Sequence[str]] = None) -> List[Dict[str, Any]]:
    eps = [normalize_episode(ep) for ep in episodes] if episodes else discover_storyboard_episodes(root)
    rows: List[Dict[str, Any]] = []
    for ep in sorted({ep for ep in eps if ep}, key=episode_sort_key):
        storyboard = load_storyboard(root, ep)
        if not storyboard:
            continue
        clips_raw = storyboard.get("clips")
        clips = [clip for clip in clips_raw if isinstance(clip, dict)] if isinstance(clips_raw, list) else []
        total_duration = storyboard_total_duration(storyboard, clips)
        opening_type, opening_confidence, opening_signals = classify_opening(clips)
        cliffhanger_type, cliffhanger_confidence, cliffhanger_signals = classify_cliffhanger(clips)
        density = (len(clips) / total_duration * 60.0) if total_duration > 0 else None
        avg_shot = (total_duration / len(clips)) if clips else None
        hook_interval, hook_count, hook_signals = infer_hook_interval(clips, total_duration, opening_type, cliffhanger_type)
        rows.append({
            "episode": ep,
            "opening_type": opening_type,
            "opening_confidence": round(opening_confidence, 3),
            "opening_signals": "; ".join(opening_signals),
            "cliffhanger_type": cliffhanger_type,
            "cliffhanger_confidence": round(cliffhanger_confidence, 3),
            "cliffhanger_signals": "; ".join(cliffhanger_signals),
            "shot_density_per_min": None if density is None else round(density, 3),
            "avg_shot_sec": None if avg_shot is None else round(avg_shot, 3),
            "hook_interval_sec": hook_interval,
            "hook_count": hook_count,
            "hook_signals": "; ".join(hook_signals),
            "clip_count": len(clips),
            "total_duration_sec": round(total_duration, 3),
            "creative_features_source": "storyboard_auto",
        })
    return rows


def write_creative_features(path: str, rows: List[Dict[str, Any]]) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


# 投放摄取适配器：真实平台 API 导出的列名各不相同（含中文），在此映射到 canonical。
# 实时投放路径 = 定时任务/webhook 把平台导出写成 生产数据/platform_metrics.{csv,jsonl,json}（drop-point 契约），
# 列名只要落在下表别名内即可被摄取，无需手工改列。详见 references/schema.md「投放摄取适配器」。
METRIC_ALIASES: Dict[str, Tuple[str, ...]] = {
    "retention_3s": ("retention_3s", "3s_retention", "ret3s", "3秒留存", "3秒留存率", "三秒留存"),
    "retention_5s": ("retention_5s", "5s_retention", "ret5s", "5秒留存", "5秒留存率"),
    "retention_6s": ("retention_6s", "6s_retention", "ret6s", "6秒留存", "6秒留存率", "六秒留存"),
    "retention_15s": ("retention_15s", "15s_retention", "ret15s", "15秒留存", "15秒留存率"),
    "retention_25_pct": ("retention_25_pct", "retention_25", "25s_pct", "ret25", "quartile_25", "q25", "25%留存", "25%播放", "播放到25%"),
    "retention_50_pct": ("retention_50_pct", "retention_50", "50s_pct", "ret50", "quartile_50", "q50", "50%留存", "50%播放", "播放到50%"),
    "retention_75_pct": ("retention_75_pct", "retention_75", "75s_pct", "ret75", "quartile_75", "q75", "75%留存", "75%播放", "播放到75%"),
    "completion_rate": ("completion_rate", "completion", "complete_rate", "完播率", "完播", "看完率"),
    "follow_next_rate": ("follow_next_rate", "follow_rate", "next_follow_rate", "追更率", "追更", "下集点击率"),
    "plays": ("plays", "play_count", "views", "view_count", "exposure", "播放", "播放量", "曝光"),
    "ctr": ("ctr", "click_through_rate", "点击率", "封面点击率", "封面ctr"),
    "avg_watch_sec": ("avg_watch_sec", "average_watch_sec", "avg_view_sec", "平均观看秒数", "平均播放时长"),
    "avg_watch_pct": ("avg_watch_pct", "average_watch_pct", "avg_view_pct", "平均观看比例", "平均播放比例"),
    "avg_episodes_per_user": ("avg_episodes_per_user", "avg_eps_per_user", "average_episodes_watched", "用户平均观看集数", "人均观看集数"),
    "episodes_per_session": ("episodes_per_session", "eps_per_session", "session_episode_depth", "单次会话观看集数"),
    "time_to_next_episode_sec": ("time_to_next_episode_sec", "next_episode_delay_sec", "time_to_next_sec", "下集点击间隔秒"),
    "unlock_or_subscribe_rate": ("unlock_or_subscribe_rate", "unlock_rate", "subscribe_rate", "series_subscribe_rate", "付费解锁率", "订阅率", "追剧按钮转化率"),
    "paywall_position_sec": ("paywall_position_sec", "paywall_sec", "paywall_at_sec", "unlock_gate_sec", "付费点秒", "付费卡点秒", "解锁卡点秒"),
    "d1_retention": ("d1_retention", "day1_retention", "D1留存", "次日留存"),
    "d7_retention": ("d7_retention", "day7_retention", "D7留存", "7日留存"),
    "d14_retention": ("d14_retention", "day14_retention", "D14留存", "14日留存"),
}


def _resolve_metric_key(row: Dict[str, Any], key: str) -> str:
    if row.get(key) not in (None, ""):
        return key
    for alias in METRIC_ALIASES.get(key, ()):
        if row.get(alias) not in (None, ""):
            return alias
    return key


def metric(row: Dict[str, Any], key: str) -> Optional[float]:
    if key == "bounce_3s" and row.get("bounce_3s") in (None, ""):
        retention = parse_float(row.get(_resolve_metric_key(row, "retention_3s")))
        return None if retention is None else max(0.0, 1.0 - retention)
    try:
        return parse_float(row.get(_resolve_metric_key(row, key)))
    except ValueError:
        return None


def numeric_feature(row: Dict[str, Any], key: str) -> Optional[float]:
    try:
        return parse_float(row.get(key))
    except ValueError:
        return None


def feature_variant_key(row: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    ep = normalize_episode(row.get("episode"))
    variant = first_text(row, "variant_id", "variant", "ab_variant", "publish_variant")
    if not ep or not variant:
        return None
    return ep, normalize_variant_id(variant)


def prepare_rows(metrics_rows: List[Dict[str, Any]], feature_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    features_by_ep: Dict[str, Dict[str, Any]] = {}
    features_by_variant: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for item in feature_rows:
        ep = normalize_episode(item.get("episode"))
        if ep:
            features_by_ep[ep] = dict(item)
        key = feature_variant_key(item)
        if key:
            features_by_variant[key] = dict(item)
    merged = []
    for item in metrics_rows:
        ep = normalize_episode(item.get("episode"))
        if not ep:
            continue
        variant_id = normalize_variant_id(first_text(item, "variant_id", "variant", "ab_variant", "publish_variant"))
        row = dict(features_by_ep.get(ep, {}))
        row.update(features_by_variant.get((ep, variant_id), {}))
        row.update(item)
        row["episode"] = ep
        row["variant_id"] = normalize_variant_id(first_text(row, "variant_id", "variant", "ab_variant", "publish_variant"))
        if not row.get("bounce_3s"):
            retention = metric(row, "retention_3s")
            if retention is not None:
                row["bounce_3s"] = 1.0 - retention
        merged.append(row)
    return merged


def resolve_feature_rows(
    root: str,
    metrics_rows: List[Dict[str, Any]],
    features_path: Optional[str],
    *,
    auto_features: bool = True,
) -> Tuple[List[Dict[str, Any]], str, Dict[str, Any]]:
    if features_path:
        rows = read_records(features_path)
        return rows, features_path, {"mode": "file", "path": features_path, "count": len(rows)}
    if not auto_features:
        raise ValueError("missing creative features and --no-auto-features was set")
    episodes = sorted({normalize_episode(row.get("episode")) for row in metrics_rows if normalize_episode(row.get("episode"))}, key=episode_sort_key)
    rows = extract_storyboard_features(root, episodes=episodes)
    found = {normalize_episode(row.get("episode")) for row in rows}
    missing = [ep for ep in episodes if ep not in found]
    if not rows:
        raise ValueError("missing creative features and no storyboard.json could be auto-extracted")
    return rows, "storyboard:auto", {
        "mode": "storyboard_auto",
        "count": len(rows),
        "episodes": [row["episode"] for row in rows],
        "missing_storyboards": missing,
    }


def row_weight(row: Dict[str, Any]) -> float:
    plays = metric(row, "plays")
    return max(1.0, plays or 1.0)


def weighted_mean(rows: Iterable[Dict[str, Any]], key: str) -> Optional[float]:
    total = 0.0
    weight_total = 0.0
    for row in rows:
        value = metric(row, key)
        if value is None:
            continue
        weight = row_weight(row)
        total += value * weight
        weight_total += weight
    if weight_total == 0:
        return None
    return total / weight_total


def fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def fmt_metric(key: str, value: Optional[float]) -> str:
    if value is None:
        return "—"
    if key in {"avg_episodes_per_user", "episodes_per_session", "story_roi"}:
        return f"{value:.2f}"
    if key == "time_to_next_episode_sec":
        return f"{value:.1f}s"
    if key == "avg_watch_sec":
        return f"{value:.1f}s"
    return fmt_pct(value)


def lift(value: Optional[float], baseline: Optional[float]) -> Optional[float]:
    if value is None or baseline is None:
        return None
    return value - baseline


def density_value(row: Dict[str, Any]) -> Optional[float]:
    direct = numeric_feature(row, "shot_density_per_min")
    if direct is not None:
        return direct
    avg_shot = numeric_feature(row, "avg_shot_sec")
    if avg_shot and avg_shot > 0:
        return 60.0 / avg_shot
    return None


def density_bucket(value: Optional[float]) -> str:
    if value is None:
        return "unknown"
    if value < 12:
        return "<12/m 过慢"
    if value < 20:
        return "12-20/m 舒展"
    if value < 30:
        return "20-30/m 标准快节奏"
    if value < 40:
        return "30-40/m 高密度"
    return ">=40/m 过密"


def hook_bucket(value: Optional[float]) -> str:
    if value is None:
        return "unknown"
    if value <= 12:
        return "<=12s 高频钩子"
    if value <= 20:
        return "13-20s 标准钩子"
    if value <= 30:
        return "21-30s 偏稀"
    return ">30s 过稀"


def paywall_bucket(value: Optional[float]) -> str:
    if value is None:
        return "unknown"
    if value < 0:
        return "no_paywall"
    if value <= 15:
        return "<=15s 过早卡点"
    if value <= 45:
        return "16-45s 前中段卡点"
    if value <= 90:
        return "46-90s 中后段卡点"
    return ">90s 后段卡点"


def add_derived_features(rows: List[Dict[str, Any]]) -> None:
    for row in rows:
        row["shot_density_bucket"] = density_bucket(density_value(row))
        row["hook_interval_bucket"] = hook_bucket(numeric_feature(row, "hook_interval_sec"))
        row["paywall_position_bucket"] = paywall_bucket(metric(row, "paywall_position_sec"))
        row["paywall_after_promise_id"] = first_text(
            row,
            "paywall_after_promise_id",
            "after_promise_id",
            "paywall_promise_id",
            "付费点承诺ID",
        ) or UNKNOWN
        row["unlock_friction"] = first_text(
            row,
            "unlock_friction",
            "paywall_friction",
            "friction_level",
            "解锁摩擦",
            "付费摩擦",
        ) or UNKNOWN
        row["continue_path"] = first_text(
            row,
            "continue_path",
            "next_episode_path",
            "continue_cta",
            "next_cta",
            "追更路径",
            "续看路径",
        ) or UNKNOWN
        row["ab_test_id"] = first_text(row, "ab_test_id", "experiment_id", "test_id", "campaign_id") or "default"
        row["variant_id"] = normalize_variant_id(first_text(row, "variant_id", "variant", "ab_variant", "publish_variant"))
        row["opening_variant"] = first_text(row, "opening_variant", "opening_version", "opening_ab", "first_3s_variant", "first_3s_asset") or str(row.get("opening_type") or UNKNOWN)
        row["cover_variant"] = first_text(row, "cover_variant", "cover_id", "cover_asset", "thumbnail_variant", "thumbnail_id") or UNKNOWN
        row["cliffhanger_cut_variant"] = first_text(
            row,
            "cliffhanger_cut_variant",
            "tail_cut_variant",
            "ending_variant",
            "cliffhanger_variant",
            "final_hook_asset",
        ) or str(row.get("cliffhanger_type") or UNKNOWN)
        row["title_variant"] = first_text(row, "title_variant", "title_copy", "headline_variant", "caption_variant") or UNKNOWN


def group_stats(rows: List[Dict[str, Any]], group_field: str, metrics: Sequence[str], *, sort_metric: str, reverse: bool = True) -> List[Dict[str, Any]]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = str(row.get(group_field) or "unknown").strip() or "unknown"
        groups[key].append(row)
    result = []
    for key, items in groups.items():
        item = {
            "name": key,
            "n": len(items),
            "plays": int(sum(row_weight(row) for row in items)),
            "episodes": sorted({row["episode"] for row in items}),
        }
        for metric_key in metrics:
            item[metric_key] = weighted_mean(items, metric_key)
        result.append(item)
    result.sort(key=lambda x: (x.get(sort_metric) is None, x.get(sort_metric) or 0), reverse=False)
    if reverse:
        known = [item for item in result if item.get(sort_metric) is not None]
        unknown = [item for item in result if item.get(sort_metric) is None]
        result = list(reversed(known)) + unknown
    return result


def first_confident(groups: List[Dict[str, Any]], min_samples: int, metric_key: str) -> Optional[Dict[str, Any]]:
    for item in groups:
        if int(item.get("n") or 0) >= min_samples and item.get(metric_key) is not None:
            return item
    return None


def analyze_group(
    rows: List[Dict[str, Any]],
    *,
    name: str,
    group_field: str,
    primary_metric: str,
    metrics: Sequence[str],
    min_samples: int,
    higher_is_better: bool = True,
) -> Dict[str, Any]:
    baseline = weighted_mean(rows, primary_metric)
    groups = group_stats(rows, group_field, metrics, sort_metric=primary_metric, reverse=higher_is_better)
    best = first_confident(groups, min_samples, primary_metric)
    worst = first_confident(list(reversed(groups)), min_samples, primary_metric)
    return {
        "name": name,
        "group_field": group_field,
        "primary_metric": primary_metric,
        "baseline": baseline,
        "min_samples": min_samples,
        "groups": [{**item, "lift": lift(item.get(primary_metric), baseline)} for item in groups],
        "best": None if best is None else {**best, "lift": lift(best.get(primary_metric), baseline)},
        "worst": None if worst is None else {**worst, "lift": lift(worst.get(primary_metric), baseline)},
    }


def ab_context_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        normalize_episode(row.get("episode")),
        first_text(row, "platform") or "all_platforms",
        first_text(row, "ab_test_id", "experiment_id", "test_id", "campaign_id") or "default",
    )


def analyze_paired_ab(
    rows: List[Dict[str, Any]],
    *,
    name: str,
    group_field: str,
    primary_metric: str,
    metrics: Sequence[str],
    min_samples: int,
    higher_is_better: bool = True,
) -> Dict[str, Any]:
    contexts: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = str(row.get(group_field) or UNKNOWN).strip() or UNKNOWN
        if value == UNKNOWN:
            continue
        contexts[ab_context_key(row)].append(row)

    grouped_rows: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    paired_observations: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for context, items in contexts.items():
        by_value: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in items:
            value = str(item.get(group_field) or UNKNOWN).strip() or UNKNOWN
            if value != UNKNOWN:
                by_value[value].append(item)
                grouped_rows[value].append(item)
        if len(by_value) < 2:
            continue
        baseline = weighted_mean(items, primary_metric)
        if baseline is None:
            continue
        for value, value_rows in by_value.items():
            value_metric = weighted_mean(value_rows, primary_metric)
            if value_metric is None:
                continue
            paired_observations[value].append({
                "context": "/".join(context),
                "episode": context[0],
                "platform": context[1],
                "ab_test_id": context[2],
                "metric": value_metric,
                "baseline": baseline,
                "lift": value_metric - baseline,
                "plays": sum(row_weight(row) for row in value_rows),
            })

    result = []
    for value, observations in paired_observations.items():
        value_rows = grouped_rows[value]
        plays = sum(row_weight(row) for row in value_rows)
        paired_weight = sum(max(1.0, obs.get("plays") or 1.0) for obs in observations)
        paired_lift = None
        if paired_weight:
            paired_lift = sum((obs["lift"] * max(1.0, obs.get("plays") or 1.0)) for obs in observations) / paired_weight
        item = {
            "name": value,
            "n": len(observations),
            "raw_rows": len(value_rows),
            "plays": int(plays),
            "episodes": sorted({normalize_episode(row.get("episode")) for row in value_rows}, key=episode_sort_key),
            "paired_contexts": sorted({obs["context"] for obs in observations}),
            "paired_lift": paired_lift,
            "lift": paired_lift,
        }
        for metric_key in metrics:
            item[metric_key] = weighted_mean(value_rows, metric_key)
        result.append(item)

    result.sort(key=lambda x: (x.get("paired_lift") is None, x.get("paired_lift") or 0), reverse=higher_is_better)
    confident = [item for item in result if int(item.get("n") or 0) >= min_samples and item.get("paired_lift") is not None]
    best = confident[0] if confident else None
    worst = confident[-1] if confident else None
    return {
        "name": name,
        "group_field": group_field,
        "primary_metric": primary_metric,
        "baseline": weighted_mean(rows, primary_metric),
        "min_samples": min_samples,
        "paired": True,
        "groups": result,
        "best": best,
        "worst": worst,
    }


def build_recommendations(analyses: Dict[str, Dict[str, Any]], min_lift: float) -> List[str]:
    recs: List[str] = []
    opening = analyses["opening_retention"].get("best")
    if opening and (opening.get("lift") or 0) >= min_lift:
        recs.append(
            f"开场优先复用 `{opening['name']}`：3秒留存 {fmt_pct(opening.get('retention_3s'))}，"
            f"较总体 {fmt_pct(opening.get('lift'))}。"
        )
    cliff = analyses["cliffhanger_follow"].get("best")
    if cliff and (cliff.get("lift") or 0) >= min_lift:
        recs.append(
            f"集尾优先复用 `{cliff['name']}`：追更率 {fmt_pct(cliff.get('follow_next_rate'))}，"
            f"较总体 {fmt_pct(cliff.get('lift'))}。"
        )
    density_worst = analyses["shot_density_bounce"].get("worst")
    if density_worst and (density_worst.get("lift") or 0) >= min_lift:
        recs.append(
            f"镜头密度 `{density_worst['name']}` 跳出偏高：3秒跳出 {fmt_pct(density_worst.get('bounce_3s'))}，"
            f"较总体 {fmt_pct(density_worst.get('lift'))}，下一批降低密度或补留白。"
        )
    hook_worst = analyses["hook_interval_retention"].get("worst")
    if hook_worst and (hook_worst.get("lift") or 0) <= -min_lift:
        recs.append(
            f"钩子间隔 `{hook_worst['name']}` 留存偏低：15秒留存 {fmt_pct(hook_worst.get('retention_15s'))}，"
            "下一批把信息增量压回 15-20 秒内。"
        )
    ab_opening = analyses.get("ab_opening_retention", {}).get("best")
    if ab_opening and (ab_opening.get("paired_lift") or 0) >= min_lift:
        recs.append(
            f"A/B 开场优先 `{ab_opening['name']}`：同集内 3秒留存 lift {fmt_pct(ab_opening.get('paired_lift'))}，"
            f"覆盖 {ab_opening.get('n')} 个 paired context。"
        )
    ab_cover = analyses.get("ab_cover_retention", {}).get("best")
    if ab_cover and (ab_cover.get("paired_lift") or 0) >= min_lift:
        recs.append(
            f"A/B 封面优先 `{ab_cover['name']}`：同集内 3秒留存 lift {fmt_pct(ab_cover.get('paired_lift'))}；"
            "若有 CTR 字段，再用封面点击率复核。"
        )
    ab_tail = analyses.get("ab_cliffhanger_follow", {}).get("best")
    if ab_tail and (ab_tail.get("paired_lift") or 0) >= min_lift:
        recs.append(
            f"A/B 集尾断点优先 `{ab_tail['name']}`：同集内追更率 lift {fmt_pct(ab_tail.get('paired_lift'))}。"
        )
    ab_title = analyses.get("ab_title_retention", {}).get("best")
    if ab_title and (ab_title.get("paired_lift") or 0) >= min_lift:
        recs.append(
            f"A/B 标题文案优先 `{ab_title['name']}`：同集内 3秒留存 lift {fmt_pct(ab_title.get('paired_lift'))}。"
        )
    paywall = analyses.get("paywall_unlock", {}).get("best")
    if paywall and paywall.get("name") != UNKNOWN and (paywall.get("lift") or 0) >= min_lift:
        recs.append(
            f"付费/解锁卡点优先 `{paywall['name']}`：解锁/订阅率 {fmt_pct(paywall.get('unlock_or_subscribe_rate'))}，"
            f"较总体 {fmt_pct(paywall.get('lift'))}；确认卡点必须落在已登记承诺之后。"
        )
    continue_path = analyses.get("continue_path_follow", {}).get("best")
    if continue_path and continue_path.get("name") != UNKNOWN and (continue_path.get("lift") or 0) >= min_lift:
        recs.append(
            f"追更路径优先 `{continue_path['name']}`：追更率 {fmt_pct(continue_path.get('follow_next_rate'))}，"
            f"较总体 {fmt_pct(continue_path.get('lift'))}。"
        )
    if not recs:
        recs.append("样本或 lift 暂不足，先继续收集平台数据，不把偶然结果写成铁律。")
    return recs


def build_creative_priors(
    analyses: Dict[str, Dict[str, Any]],
    *,
    min_lift: float,
    min_samples: int,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """A/B paired-lift 胜出变体 → 机器可读第一方先验（投放→生成输入闭环的写端）。

    诚实边界：每个维度只在「同集内 paired_lift ≥ min_lift 且 paired context 数 n ≥ min_samples」
    时才写先验——样本不足或无显著胜出的维度直接缺省（不臆造），消费端按缺省 no-op。
    每条先验带 winner / lift / 样本量 / 采集时间，供 n2d-script 阶段2 finalize 当开场/断点设计先验读。
    """
    priors: Dict[str, Any] = {}
    for field, analysis_key, primary_metric in CREATIVE_PRIOR_DIMENSIONS:
        analysis = analyses.get(analysis_key) or {}
        best = analysis.get("best")
        if not isinstance(best, dict):
            continue
        paired_lift = best.get("paired_lift")
        n = int(best.get("n") or 0)
        # 双闸：lift 不够显著 或 paired context 样本不足 → 该维度不写先验。
        if paired_lift is None or paired_lift < min_lift or n < min_samples:
            continue
        priors[field] = {
            "winner": best.get("name"),
            "paired_lift": round(float(paired_lift), 4),
            "primary_metric": primary_metric,
            "metric_value": best.get(primary_metric),
            "n": n,
            "plays": int(best.get("plays") or 0),
            "episodes": list(best.get("episodes") or []),
        }
    return {
        "kind": CREATIVE_PRIORS_KIND,
        "version": CREATIVE_PRIORS_VERSION,
        "generated_at": generated_at or now_iso(),  # 采集时间占位（消费端可据此判先验新鲜度）
        "min_lift": min_lift,
        "min_samples": min_samples,
        "priors": priors,
    }


def write_creative_priors(root: str, priors: Dict[str, Any]) -> str:
    os.makedirs(production_dir(root), exist_ok=True)
    path = os.path.join(production_dir(root), CREATIVE_PRIORS_FILENAME)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(priors, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def load_consistency_reports(root: str) -> List[Dict[str, Any]]:
    """读 n2d-review/review-ui 外发的 n2d_consistency_findings（无文件优雅返回空）。"""
    reports: List[Dict[str, Any]] = []
    patterns = ("consistency_findings_*.json", "review_ui_findings_*.json")
    paths: List[str] = []
    for pattern in patterns:
        paths.extend(glob.glob(os.path.join(production_dir(root), pattern)))
    for path in sorted(set(paths)):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("kind") == CONSISTENCY_FINDINGS_KIND:
            reports.append(data)
    return reports


def consistency_by_dim(report: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    by_dim = ((report.get("summary") or {}).get("by_dim") or {})
    if isinstance(by_dim, dict) and by_dim:
        return by_dim
    out: Dict[str, Dict[str, int]] = {}
    for finding in report.get("findings") or []:
        if not isinstance(finding, dict):
            continue
        norm = normalize_finding(finding)  # 归一三端别名（sev/dim/msg → 规范字段，与 batch 消费端同一真值源）
        dim = norm["dimension"] or "QA"    # 展示维度保留原文（dim_totals 的 Top 维度键，不强转 canonical key）
        sev = norm["severity"] or "info"
        if sev not in {"block", "warn", "info"}:
            continue
        counts = out.setdefault(dim, {"block": 0, "warn": 0, "info": 0})
        counts[sev] = counts.get(sev, 0) + 1
    return out


def analyze_consistency(reports: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """一致性问题 Top：按维度计数 + 最严重的集，并排同集留存/跳出指标（有投放数据时）。

    一致性检出（脸漂/服装/场景/风格/语义/状态）单独看是生产质量数据；和投放留存并排，
    才能回答"脸漂严重的集是不是跳出率也高"——这是把 QA 线接进投放反哺闭环的读端。
    """
    if not reports:
        return None
    metrics_by_ep: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ep = normalize_episode(row.get("episode"))
        if ep and ep not in metrics_by_ep:
            metrics_by_ep[ep] = row
    dim_totals: Dict[str, Dict[str, int]] = {}
    episodes: List[Dict[str, Any]] = []
    for report in reports:
        ep = normalize_episode(report.get("episode"))
        by_dim = consistency_by_dim(report)
        ep_block = ep_warn = 0
        top_dim, top_weight = "", -1
        for dim, counts in by_dim.items():
            if not isinstance(counts, dict):
                continue
            block = int(counts.get("block") or 0)
            warn = int(counts.get("warn") or 0)
            ep_block += block
            ep_warn += warn
            agg = dim_totals.setdefault(dim, {"block": 0, "warn": 0})
            agg["block"] += block
            agg["warn"] += warn
            weight = block * 10 + warn
            if weight > top_weight and weight > 0:
                top_dim, top_weight = dim, weight
        metrics_row = metrics_by_ep.get(ep, {})
        episodes.append({
            "episode": ep,
            "block": ep_block,
            "warn": ep_warn,
            "top_dim": top_dim,
            "retention_15s": metric(metrics_row, "retention_15s") if metrics_row else None,
            "bounce_3s": metric(metrics_row, "bounce_3s") if metrics_row else None,
        })
    episodes.sort(key=lambda item: (-(item["block"] * 10 + item["warn"]), episode_sort_key(item["episode"])))
    worst = episodes[0] if episodes and (episodes[0]["block"] or episodes[0]["warn"]) else None
    # 写回信号（闭环回火端，不止展示）：一致性 block + 留存偏低的集 → 优先返工并提该维度权重，
    # 供 n2d-batch / n2d-score 消费。把"脸漂严重的集跳出也高"从洞察变成可执行动作。
    priority_signals: List[Dict[str, Any]] = []
    for e in episodes:
        ret = e.get("retention_15s")
        if e["block"] and ret is not None and ret < LOW_RETENTION_15S:
            priority_signals.append({
                "episode": e["episode"],
                "top_dim": e["top_dim"],
                "block": e["block"],
                "retention_15s": ret,
                "signal": "prioritize_rework",
                "note": f"一致性 block {e['block']} 且 15s 留存 {ret:.0%} 偏低 → 优先返工该集、提「{e['top_dim']}」维度权重",
            })
    return {
        "report_count": len(reports),
        "dim_totals": dim_totals,
        "episodes": episodes,
        "worst_episode": worst["episode"] if worst else None,
        "priority_signals": priority_signals,
    }


def analyze_feedback(root: str, metrics_path: str, features_path: Optional[str] = None, *, min_samples: int = 2, min_lift: float = 0.05, auto_features: bool = True) -> Dict[str, Any]:
    metrics_rows = read_records(metrics_path)
    feature_rows, feature_source, feature_meta = resolve_feature_rows(root, metrics_rows, features_path, auto_features=auto_features)
    rows = prepare_rows(metrics_rows, feature_rows)
    add_derived_features(rows)
    analyses = {
        "opening_retention": analyze_group(
            rows,
            name="开场留存",
            group_field="opening_type",
            primary_metric="retention_3s",
            metrics=("retention_3s", "retention_6s", "retention_15s", "retention_25_pct", "retention_50_pct", "completion_rate", "bounce_3s"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
        "cliffhanger_follow": analyze_group(
            rows,
            name="集尾追更",
            group_field="cliffhanger_type",
            primary_metric="follow_next_rate",
            metrics=("follow_next_rate", "unlock_or_subscribe_rate", "avg_episodes_per_user", "completion_rate", "retention_15s"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
        "shot_density_bounce": analyze_group(
            rows,
            name="镜头密度跳出",
            group_field="shot_density_bucket",
            primary_metric="bounce_3s",
            metrics=("bounce_3s", "retention_3s", "retention_6s", "retention_15s", "retention_25_pct", "completion_rate"),
            min_samples=min_samples,
            higher_is_better=False,
        ),
        "hook_interval_retention": analyze_group(
            rows,
            name="钩子间隔留存",
            group_field="hook_interval_bucket",
            primary_metric="retention_15s",
            metrics=("retention_15s", "retention_25_pct", "retention_50_pct", "completion_rate", "follow_next_rate"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
        "ab_opening_retention": analyze_paired_ab(
            rows,
            name="A/B 开场留存",
            group_field="opening_variant",
            primary_metric="retention_3s",
            metrics=("retention_3s", "retention_6s", "retention_15s", "retention_25_pct", "completion_rate", "follow_next_rate"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
        "ab_cover_retention": analyze_paired_ab(
            rows,
            name="A/B 封面留存",
            group_field="cover_variant",
            primary_metric="retention_3s",
            metrics=("retention_3s", "retention_6s", "retention_15s", "completion_rate", "follow_next_rate", "ctr"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
        "ab_cliffhanger_follow": analyze_paired_ab(
            rows,
            name="A/B 集尾断点追更",
            group_field="cliffhanger_cut_variant",
            primary_metric="follow_next_rate",
            metrics=("follow_next_rate", "unlock_or_subscribe_rate", "avg_episodes_per_user", "completion_rate", "retention_15s"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
        "ab_title_retention": analyze_paired_ab(
            rows,
            name="A/B 标题文案留存",
            group_field="title_variant",
            primary_metric="retention_3s",
            metrics=("retention_3s", "retention_6s", "retention_15s", "completion_rate", "follow_next_rate", "ctr"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
        "paywall_unlock": analyze_group(
            rows,
            name="付费/解锁卡点",
            group_field="paywall_position_bucket",
            primary_metric="unlock_or_subscribe_rate",
            metrics=("unlock_or_subscribe_rate", "follow_next_rate", "completion_rate", "retention_50_pct", "avg_episodes_per_user"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
        "continue_path_follow": analyze_group(
            rows,
            name="追更路径",
            group_field="continue_path",
            primary_metric="follow_next_rate",
            metrics=("follow_next_rate", "avg_episodes_per_user", "episodes_per_session", "completion_rate", "unlock_or_subscribe_rate"),
            min_samples=min_samples,
            higher_is_better=True,
        ),
    }
    return {
        "kind": KIND,
        "version": VERSION,
        "root": root,
        "generated_at": now_iso(),
        "source": {"metrics": metrics_path, "features": feature_source},
        "feature_extraction": feature_meta,
        "sample_count": len(rows),
        "min_samples": min_samples,
        "min_lift": min_lift,
        "analyses": analyses,
        "consistency": analyze_consistency(load_consistency_reports(root), rows),
        "recommendations": build_recommendations(analyses, min_lift),
    }


def render_groups(groups: List[Dict[str, Any]], metric_keys: Sequence[str]) -> List[str]:
    lines = ["| 分组 | n | plays | " + " | ".join(metric_keys) + " | lift |", "|---|---:|---:|" + "---:|" * (len(metric_keys) + 1)]
    for item in groups:
        values = " | ".join(fmt_metric(key, item.get(key)) for key in metric_keys)
        lines.append(f"| {item['name']} | {item['n']} | {item['plays']} | {values} | {fmt_pct(item.get('lift'))} |")
    return lines


def render_markdown(feedback: Dict[str, Any]) -> str:
    feature_meta = feedback.get("feature_extraction") or {}
    lines = [
        "# n2d 投放数据回灌",
        "",
        f"- 样本数：{feedback['sample_count']}",
        f"- 最小分组样本：{feedback['min_samples']}",
        f"- 生成时间：{feedback['generated_at']}",
        f"- 导演标签来源：{feature_meta.get('mode') or feedback.get('source', {}).get('features')}",
        "",
        "## 建议",
        "",
    ]
    for rec in feedback["recommendations"]:
        lines.append(f"- {rec}")
    sections = [
        ("opening_retention", ("retention_3s", "retention_6s", "retention_15s", "retention_25_pct", "retention_50_pct", "completion_rate", "bounce_3s")),
        ("cliffhanger_follow", ("follow_next_rate", "unlock_or_subscribe_rate", "avg_episodes_per_user", "completion_rate", "retention_15s")),
        ("shot_density_bounce", ("bounce_3s", "retention_3s", "retention_6s", "retention_15s", "retention_25_pct", "completion_rate")),
        ("hook_interval_retention", ("retention_15s", "retention_25_pct", "retention_50_pct", "completion_rate", "follow_next_rate")),
        ("ab_opening_retention", ("retention_3s", "retention_6s", "retention_15s", "retention_25_pct", "completion_rate", "follow_next_rate")),
        ("ab_cover_retention", ("retention_3s", "retention_6s", "retention_15s", "completion_rate", "follow_next_rate", "ctr")),
        ("ab_cliffhanger_follow", ("follow_next_rate", "unlock_or_subscribe_rate", "avg_episodes_per_user", "completion_rate", "retention_15s")),
        ("ab_title_retention", ("retention_3s", "retention_6s", "retention_15s", "completion_rate", "follow_next_rate", "ctr")),
        ("paywall_unlock", ("unlock_or_subscribe_rate", "follow_next_rate", "completion_rate", "retention_50_pct", "avg_episodes_per_user")),
        ("continue_path_follow", ("follow_next_rate", "avg_episodes_per_user", "episodes_per_session", "completion_rate", "unlock_or_subscribe_rate")),
    ]
    for key, metrics in sections:
        analysis = (feedback.get("analyses") or {}).get(key)
        if not analysis:
            continue
        lines.extend(["", f"## {analysis['name']}", ""])
        lines.extend(render_groups(analysis["groups"], metrics))
    consistency = feedback.get("consistency")
    if consistency:
        lines.extend(["", "## 一致性问题 Top（QA 回灌）", ""])
        dim_totals = consistency.get("dim_totals") or {}
        if dim_totals:
            lines += ["| 维度 | block | warn |", "|---|---:|---:|"]
            for dim, counts in sorted(dim_totals.items(), key=lambda kv: (-(kv[1]["block"] * 10 + kv[1]["warn"]), kv[0])):
                lines.append(f"| {dim} | {counts['block']} | {counts['warn']} |")
        if consistency.get("worst_episode"):
            lines.append(f"\n- 一致性问题最严重的集：**{consistency['worst_episode']}**")
        eps = [e for e in consistency.get("episodes") or [] if e["block"] or e["warn"]]
        if eps:
            lines += ["", "| 集 | block | warn | Top维度 | retention_15s | bounce_3s |", "|---|---:|---:|---|---:|---:|"]
            for e in eps:
                lines.append(
                    f"| {e['episode']} | {e['block']} | {e['warn']} | {e['top_dim'] or '—'} | "
                    f"{fmt_pct(e.get('retention_15s'))} | {fmt_pct(e.get('bounce_3s'))} |"
                )
    lines.append("")
    return "\n".join(lines)


def write_feedback(root: str, feedback: Dict[str, Any]) -> None:
    os.makedirs(production_dir(root), exist_ok=True)
    json_path = os.path.join(production_dir(root), "platform_feedback.json")
    md_path = os.path.join(production_dir(root), "platform_feedback.md")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(feedback, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(feedback))


def best_line(feedback: Dict[str, Any], analysis_key: str, metric_key: str, label: str) -> str:
    item = feedback.get("analyses", {}).get(analysis_key, {}).get("best")
    if not item:
        return f"- {label}：样本不足，继续观察。"
    return (
        f"- {label}：`{item['name']}`，{metric_key}={fmt_pct(item.get(metric_key))}，"
        f"lift={fmt_pct(item.get('lift'))}，n={item['n']}。"
    )


def worst_line(feedback: Dict[str, Any], analysis_key: str, metric_key: str, label: str) -> str:
    item = feedback.get("analyses", {}).get(analysis_key, {}).get("worst")
    if not item:
        return f"- {label}：样本不足，继续观察。"
    return (
        f"- {label}：`{item['name']}`，{metric_key}={fmt_pct(item.get(metric_key))}，"
        f"lift={fmt_pct(item.get('lift'))}，n={item['n']}。"
    )


def guide_snapshot(feedback: Dict[str, Any]) -> str:
    feature_meta = feedback.get("feature_extraction") or {}
    lines = [
        f"> 更新时间：{feedback['generated_at']}；样本数：{feedback['sample_count']}；最小分组样本：{feedback['min_samples']}。",
        f"> 导演标签来源：{feature_meta.get('mode') or feedback.get('source', {}).get('features')}。",
        "",
        best_line(feedback, "opening_retention", "retention_3s", "开场留存最高"),
        best_line(feedback, "cliffhanger_follow", "follow_next_rate", "集尾追更最高"),
        worst_line(feedback, "shot_density_bounce", "bounce_3s", "镜头密度跳出风险"),
        worst_line(feedback, "hook_interval_retention", "retention_15s", "钩子间隔低留存风险"),
        best_line(feedback, "ab_opening_retention", "retention_3s", "A/B 开场同集内最优"),
        best_line(feedback, "ab_cover_retention", "retention_3s", "A/B 封面同集内最优"),
        best_line(feedback, "ab_cliffhanger_follow", "follow_next_rate", "A/B 集尾断点同集内最优"),
        best_line(feedback, "ab_title_retention", "retention_3s", "A/B 标题文案同集内最优"),
        best_line(feedback, "paywall_unlock", "unlock_or_subscribe_rate", "付费/解锁卡点最优"),
        best_line(feedback, "continue_path_follow", "follow_next_rate", "追更路径最优"),
        "",
        "下一批执行建议：",
    ]
    for rec in feedback["recommendations"]:
        lines.append(f"- {rec}")
    return "\n".join(lines)


def update_director_guide(guide_path: str, feedback: Dict[str, Any]) -> None:
    snapshot = f"{START_MARKER}\n{guide_snapshot(feedback)}\n{END_MARKER}"
    if os.path.isfile(guide_path):
        text = open(guide_path, encoding="utf-8").read()
    else:
        text = ""
    if START_MARKER in text and END_MARKER in text:
        before = text.split(START_MARKER, 1)[0]
        after = text.split(END_MARKER, 1)[1]
        new_text = before + snapshot + after
    else:
        section = [
            "",
            "## 八、投放数据回灌（P2·每批更新）",
            "",
            "平台数据只能证明用户行为，不能单独解释原因；必须和 `creative_features` 导演标签一起看。每批上线后用 `n2d-feedback` 汇总开场留存、集尾追更、镜头密度跳出和钩子间隔；同一集有 A/B 时，额外比较开场、封面、集尾断点、标题文案的同集 paired lift，再把结论写进下面快照。样本不足时只观察，不改铁律。",
            "",
            snapshot,
            "",
        ]
        new_text = text.rstrip() + "\n" + "\n".join(section)
    with open(guide_path, "w", encoding="utf-8") as fh:
        fh.write(new_text)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="n2d platform feedback loop")
    ap.add_argument("root")
    ap.add_argument("--metrics", help="platform_metrics csv/jsonl/json; defaults to 生产数据/platform_metrics.*")
    ap.add_argument("--features", help="creative_features csv/jsonl/json; defaults to 生产数据/creative_features.*; absent -> auto-extract from storyboard.json")
    ap.add_argument("--no-auto-features", action="store_true", help="fail when creative_features is missing instead of extracting from storyboard.json")
    ap.add_argument("--write-features", action="store_true", help=f"write auto-extracted features to 生产数据/{AUTO_FEATURES_FILENAME}")
    ap.add_argument("--features-out", help=f"output path for --write-features/--extract-features-only; default 生产数据/{AUTO_FEATURES_FILENAME}")
    ap.add_argument("--extract-features-only", action="store_true", help="only extract creative features from storyboard.json and print/write them")
    ap.add_argument("--min-samples", type=int, default=2)
    ap.add_argument("--min-lift", type=float, default=0.05)
    ap.add_argument("--no-write", action="store_true")
    ap.add_argument(
        "--write-priors",
        action="store_true",
        help=f"write A/B-won 开场/断点/封面/标题 winners to 生产数据/{CREATIVE_PRIORS_FILENAME} (n2d-script 阶段2 finalize 读为先验)",
    )
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--update-guide", action="store_true")
    ap.add_argument(
        "--guide",
        default=os.path.join("skills", "n2d", "references", "导演节奏.md"),
        help="director rhythm guide to update when --update-guide is set",
    )
    return ap


def cmd(ns: argparse.Namespace) -> int:
    root = ns.root.rstrip("/")
    features_out = ns.features_out or os.path.join(production_dir(root), AUTO_FEATURES_FILENAME)
    if ns.extract_features_only:
        rows = extract_storyboard_features(root)
        if not rows:
            raise SystemExit("no storyboard features extracted: ensure 脚本/第N集/storyboard.json exists")
        if ns.write_features and not ns.no_write:
            write_creative_features(features_out, rows)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    metrics_path = ns.metrics or default_input(root, "platform_metrics")
    features_path = ns.features or default_input(root, "creative_features")
    if not metrics_path:
        raise SystemExit("missing platform metrics: pass --metrics or create 生产数据/platform_metrics.csv|jsonl|json")
    try:
        feedback = analyze_feedback(
            root,
            metrics_path,
            features_path,
            min_samples=ns.min_samples,
            min_lift=ns.min_lift,
            auto_features=not ns.no_auto_features,
        )
    except ValueError as exc:
        raise SystemExit(
            "missing creative features: pass --features, create 生产数据/creative_features.csv|jsonl|json, "
            "or ensure 脚本/第N集/storyboard.json exists for auto extraction"
        ) from exc
    if ns.write_features and feedback.get("feature_extraction", {}).get("mode") == "storyboard_auto" and not ns.no_write:
        episodes = feedback.get("feature_extraction", {}).get("episodes") or []
        write_creative_features(features_out, extract_storyboard_features(root, episodes=episodes))
    if not ns.no_write:
        write_feedback(root, feedback)
    if ns.write_priors and not ns.no_write:
        priors = build_creative_priors(
            feedback["analyses"],
            min_lift=ns.min_lift,
            min_samples=ns.min_samples,
            generated_at=feedback.get("generated_at"),
        )
        priors_path = write_creative_priors(root, priors)
        kept = sorted(priors["priors"])
        # 诚实可见提示：无显著胜出维度会落空文件（priors={}），明说不是 bug。
        print(
            f"creative_priors → {priors_path}：{('写入 ' + '、'.join(kept)) if kept else '无维度达 lift/样本阈值（priors 为空，下游 no-op）'}",
            file=sys.stderr,
        )
    if ns.update_guide:
        update_director_guide(ns.guide, feedback)
    print(render_markdown(feedback) if ns.markdown else json.dumps(feedback, ensure_ascii=False, indent=2))
    return 0


def main(argv: List[str]) -> int:
    return cmd(parser().parse_args(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
