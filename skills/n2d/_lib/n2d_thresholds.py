#!/usr/bin/env python3
"""告警阈值的单一真值源——n2d-dashboard（写/告警）与 n2d-score（读通过率下限）共用。

历史 bug：score 自己只读 `生产数据/alert_thresholds.json`，漏了 dashboard 也认的
`_设置.md`/环境变量来源——只在 _设置.md 设了「告警通过率下限」时，dashboard 告警生效但
score 静默忽略。把加载逻辑收拢到这里，三方来源对齐：默认 ← _设置.md ← json ← 环境变量。

纯标准库；依赖 n2d_settings.get_setting（同源处理 `- 制作模式:` 与裸 `制作模式:` 两种写法）。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

try:
    from n2d_contract import production_dir
    from n2d_settings import get_setting
except ImportError:  # imported via sys.path parent
    from .n2d_contract import production_dir
    from .n2d_settings import get_setting


THRESHOLDS_FILE = "alert_thresholds.json"

# 阈值默认值（None = 关闭该项）。默认只对「QA 阻断」开箱即告（gate 阻断本就要停线）；
# 成本/通过率/回收比默认 None，由用户显式设阈值，避免生产早期误报。
DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "budget_cap": None,             # 单币种累计成本上限
    "budget_warn_ratio": 0.8,       # 达上限该比例先 warn
    "final_pass_rate_floor": None,  # 总通过率低于 → critical
    "redraw_rate_ceiling": None,    # 重抽率高于 → warn
    "qa_blockers_ceiling": 0,       # QA 阻断数 > 此 → critical
    "cost_per_min_ceiling": None,   # 每分钟成本上限（单币种）→ warn
    "recoup_floor": None,           # 回收比低于 → warn（仅有投放数据时）
}

# _设置.md 标签 → 阈值键
SETTINGS_MAP = {
    "告警预算上限": "budget_cap",
    "告警预算预警比例": "budget_warn_ratio",
    "告警通过率下限": "final_pass_rate_floor",
    "告警重抽率上限": "redraw_rate_ceiling",
    "告警QA阻断上限": "qa_blockers_ceiling",
    "告警每分钟成本上限": "cost_per_min_ceiling",
    "告警回收比下限": "recoup_floor",
}

# 阈值键 → 环境变量覆盖
ENV_MAP = {
    "budget_cap": "N2D_ALERT_BUDGET_CAP",
}

BENCHMARK_FILE = "industry_benchmark.json"
BENCHMARK_REFERENCE_FILE = os.path.abspath(
    # 本文件已迁到 skills/n2d/_lib/，到 skills/ 需上溯两级（③ name-accuracy）。
    os.path.join(os.path.dirname(__file__), "..", "..", "n2d-dashboard", "references", BENCHMARK_FILE)
)

# 行业基准参照（**只读·非闸门**）的 fallback。默认值从
# `n2d-dashboard/references/industry_benchmark.json` 读取，方便流程自审刷新基准而不改代码。
FALLBACK_INDUSTRY_BENCHMARK: Dict[str, Any] = {
    "one_pass_rate": 0.90,            # 分镜/镜头一次性通过率行业宣传基准（≈纳米漫剧 90%+）
    "redraw_rate": 0.10,             # 重抽率参照（≈1 − 一次通过率）
    "cost_per_min": {"CNY": 6.0},    # ~0.1 元/秒 × 60 = 6 元/成片分钟（有戏AI 0.1 元/秒口径）
    "cross_ep_consistency": 0.95,    # 跨集角色一致性（由 n2d-score 视觉相似度跟踪，非本仪表盘 ROI 字段）
    "collected": "2026-06",
    "sources": [],
}

# _设置.md 标签 → benchmark 键（允许项目覆盖参照线，比如自有战绩库的真实基准）
BENCHMARK_SETTINGS_MAP = {
    "基准一次通过率": "one_pass_rate",
    "基准重抽率": "redraw_rate",
}


def load_reference_benchmark() -> Dict[str, Any]:
    cfg: Dict[str, Any] = json.loads(json.dumps(FALLBACK_INDUSTRY_BENCHMARK))
    try:
        data = json.load(open(BENCHMARK_REFERENCE_FILE, encoding="utf-8"))
        if isinstance(data, dict):
            cfg.update(data)
    except (ValueError, OSError):
        pass
    return cfg


def load_benchmark(root: str) -> Dict[str, Any]:
    """行业基准参照：默认 ← _设置.md ← industry_benchmark.json。**只读，不参与告警/阻断。**"""
    cfg: Dict[str, Any] = load_reference_benchmark()
    for label, key in BENCHMARK_SETTINGS_MAP.items():
        val = get_setting(root, label, "")
        ratio = parse_ratio(val)
        if ratio is not None:
            cfg[key] = ratio
    path = os.path.join(production_dir(root), BENCHMARK_FILE)
    if os.path.isfile(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update(data)
        except (ValueError, OSError):
            pass
    return cfg


def parse_ratio(text: Optional[str]) -> Optional[float]:
    """把 '0.8' / '80%' 解析成 float；解析不出返回 None。"""
    if text is None:
        return None
    text = str(text).strip()
    if not text:
        return None
    try:
        if text.endswith("%"):
            return float(text[:-1]) / 100.0
        return float(text)
    except ValueError:
        return None


def load_thresholds(root: str) -> Dict[str, Any]:
    """默认 ← _设置.md ← alert_thresholds.json ← 环境变量（后者优先）。"""
    cfg: Dict[str, Any] = dict(DEFAULT_THRESHOLDS)
    for label, key in SETTINGS_MAP.items():
        val = get_setting(root, label, "")
        if val:
            cfg[key] = parse_ratio(val)
    path = os.path.join(production_dir(root), THRESHOLDS_FILE)
    if os.path.isfile(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if k in DEFAULT_THRESHOLDS})
        except (ValueError, OSError):
            pass
    for key, env in ENV_MAP.items():
        if os.environ.get(env):
            cfg[key] = parse_ratio(os.environ[env])
    return cfg
