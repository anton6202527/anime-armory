#!/usr/bin/env python3
"""Profile-aware comic chapter contract and beat audit.

Contract/file facts can be ``must``.  Opening, ending, climax placement and
capacity are editorial heuristics and therefore never exceed ``warn``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from chapter_contract import (
    ENDING_MODES,
    chapter_contract as get_chapter_contract,
    normalize_chapter,
    validate_chapter_entry,
)


VERSION = 2
KIND = "comic_chapter_beat_audit"

OPENING_FUNCS = {"opening_hook", "cold_open", "hook", "establishing_hook"}
CLIMAX_FUNCS = {"action_peak", "turning_point", "climax", "reveal", "payoff"}
ENDING_FUNCTIONS = {
    "cliffhanger": {"cliffhanger", "hook"},
    "reveal": {"reveal", "page_turn_reveal"},
    "decision": {"decision", "turning_point"},
    "emotional_aftershock": {"emotional_aftershock", "reaction", "resolution"},
    "closure_with_new_promise": {"new_promise", "hook", "resolution"},
    "gag_payoff": {"gag_payoff", "punchline", "payoff"},
    "complete_closure": {"complete_closure", "closure", "resolution", "payoff"},
    "transition": {"transition", "bridge"},
}
CLIMAX_BAND = (0.5, 0.85)  # editorial heuristic only


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def read_setting(root: Path, key: str, default: str = "") -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def load_panel_script(root: Path, chapter: str) -> tuple[dict[str, Any] | None, str | None]:
    path = root / "脚本" / chapter / "panel_script.json"
    if not path.is_file():
        return None, "panel_script_missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, "panel_script_invalid"
    if not isinstance(data, dict) or not isinstance(data.get("panels"), list):
        return None, "panel_script_invalid"
    return data, None


def load_panels(root: Path, chapter: str) -> List[Dict[str, Any]]:
    data, _ = load_panel_script(root, chapter)
    return [p for p in ((data or {}).get("panels") or []) if isinstance(p, Mapping)]


def _func(panel: Mapping[str, Any]) -> str:
    raw = str(panel.get("story_function") or "").strip().lower()
    return re.sub(r"[\s\-]+", "_", raw)


def _soft_budget(contract: Mapping[str, Any] | None) -> tuple[float | None, float | None, str]:
    budget = contract.get("budget") if isinstance(contract, Mapping) else None
    if not isinstance(budget, Mapping):
        return None, None, "panels"
    soft = budget.get("soft_range")
    if not isinstance(soft, list) or len(soft) != 2:
        return None, None, str(budget.get("unit") or "panels")
    try:
        return float(soft[0]), float(soft[1]), str(budget.get("unit") or "panels")
    except (TypeError, ValueError):
        return None, None, str(budget.get("unit") or "panels")


def audit_beats(
    panels: List[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
    target_platform: str = "",
) -> List[Dict[str, Any]]:
    """Return deterministic findings plus explicitly low-confidence heuristics."""
    findings: List[Dict[str, Any]] = []
    if not panels:
        return [{"severity": "must", "confidence": "deterministic", "code": "empty_panel_script",
                 "message": "panel_script.json 无格。"}]
    n = len(panels)
    first = _func(panels[0])
    if first not in OPENING_FUNCS:
        findings.append({"severity": "warn", "confidence": "heuristic", "code": "missing_opening_hook",
                         "message": f"首格 story_function={first or '空'}；请人工确认首屏/首页是否有明确进入理由。"})

    ending_mode = str((contract or {}).get("ending_mode") or "")
    last = _func(panels[-1])
    if ending_mode in ENDING_MODES:
        expected = ENDING_FUNCTIONS[ending_mode]
        if last not in expected:
            findings.append({
                "severity": "warn",
                "confidence": "heuristic",
                "code": "ending_mode_mismatch",
                "message": f"合同 ending_mode={ending_mode}，末格 story_function={last or '空'}；"
                           f"期望候选为 {sorted(expected)}。这是编辑复核提示，不是硬闸。",
            })

    format_profile = str((contract or {}).get("format_profile") or "")
    climax_idx = [index for index, panel in enumerate(panels) if _func(panel) in CLIMAX_FUNCS]
    if format_profile != "yonkoma":
        if not climax_idx:
            findings.append({"severity": "warn", "confidence": "heuristic", "code": "no_climax_panel",
                             "message": "未标出高潮/转折/兑现格；请人工确认节拍不是平推。"})
        elif n >= 8:
            peak = max(climax_idx) / (n - 1)
            if peak < CLIMAX_BAND[0]:
                findings.append({"severity": "warn", "confidence": "heuristic", "code": "climax_too_early",
                                 "message": f"最后一个高潮候选在 {peak:.0%}；按格序估算可能偏早，"
                                            "需在ネーム阶段结合页面/滚动几何复核。"})
            elif peak > CLIMAX_BAND[1]:
                findings.append({"severity": "info", "confidence": "heuristic", "code": "climax_at_tail",
                                 "message": f"高潮候选在 {peak:.0%}；确认中段是否有足够支撑。"})

    low, high, unit = _soft_budget(contract)
    if unit == "panels" and low is not None and n < low:
        findings.append({"severity": "warn", "confidence": "heuristic", "code": "panel_count_below_soft_budget",
                         "message": f"本话 {n} 格，低于合同软容量 {low:g}；剧情闭环优先，不要为凑格硬填。"})
    if unit == "panels" and high is not None and n > high:
        findings.append({"severity": "warn", "confidence": "heuristic", "code": "panel_count_above_soft_budget",
                         "message": f"本话 {n} 格，高于合同软容量 {high:g}；仅作产能预警，不得据此劈断场戏。"})

    platform_key = target_platform.strip().lower()
    if format_profile != "yonkoma" and ("快看" in platform_key or "kuaikan" in platform_key) and n < 20:
        findings.append({"severity": "warn", "confidence": "platform_snapshot", "code": "kuaikan_submission_panel_floor",
                         "message": f"目标平台为快看且本话 {n} 格；其投稿成稿快照要求不少于 20 格。"
                                    "这是平台适配提示，不是通用分话标准。"})
    return findings


def audit_blueprint(root: Path, chapter: str | None = None) -> List[Dict[str, Any]]:
    wanted = normalize_chapter(chapter or "第1话")
    contract, error = get_chapter_contract(root, wanted)
    if error:
        return [{"severity": "must", "confidence": "deterministic", "code": error,
                 "message": f"{wanted} 缺有效 split_blueprint v2 chapter contract：{error}。"}]
    assert contract is not None
    issues = validate_chapter_entry(contract, 0)
    return [{"severity": "must", "confidence": "deterministic", **issue} for issue in issues]


def build_report(root: Path, chapter: str) -> Dict[str, Any]:
    panel_script, panel_error = load_panel_script(root, chapter)
    panels = [panel for panel in ((panel_script or {}).get("panels") or []) if isinstance(panel, Mapping)]
    contract, contract_error = get_chapter_contract(root, chapter)
    findings: List[Dict[str, Any]] = []
    if panel_error:
        findings.append({"severity": "must", "confidence": "deterministic", "code": panel_error,
                         "message": f"{chapter} 缺有效 panel_script.json：{panel_error}。"})
    else:
        findings.extend(audit_beats(
            panels,
            contract=contract,
            target_platform=read_setting(root, "目标平台", ""),
        ))
    if contract_error:
        findings.extend(audit_blueprint(root, chapter))
    elif contract is not None:
        findings.extend({"severity": "must", "confidence": "deterministic", **issue}
                        for issue in validate_chapter_entry(contract, 0))
    low, high, unit = _soft_budget(contract)
    return {
        "kind": KIND,
        "version": VERSION,
        "chapter": chapter,
        "generated_at": now_iso(),
        "profile": {
            "chapter_type": (contract or {}).get("chapter_type"),
            "format_profile": (contract or {}).get("format_profile"),
            "ending_mode": (contract or {}).get("ending_mode"),
            "target_platform": read_setting(root, "目标平台", ""),
        },
        "thresholds": {
            "soft_budget": [low, high] if low is not None else None,
            "budget_unit": unit,
            "climax_band": list(CLIMAX_BAND),
            "policy": "格数与高潮位置仅为 heuristic/platform WARN；剧情闭环和合同事实优先。",
        },
        "summary": {
            "panels": len(panels),
            "must": sum(1 for finding in findings if finding["severity"] == "must"),
            "warn": sum(1 for finding in findings if finding["severity"] == "warn"),
            "info": sum(1 for finding in findings if finding["severity"] == "info"),
        },
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        f"# 分话节拍机检 · {report.get('chapter')}",
        "",
        f"- 格 {summary.get('panels')} · must {summary.get('must')} · warn {summary.get('warn')} · info {summary.get('info')}",
        "",
    ]
    icon = {"must": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for finding in report.get("findings") or []:
        lines.append(f"- {icon.get(finding['severity'], '·')} `{finding['code']}` {finding['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 合同事实完整；未发现需人工复核的节拍信号")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root")
    parser.add_argument("chapter")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="仅确定性 must 级 exit 1；启发式永不硬阻断")
    args = parser.parse_args(argv)
    root = Path(args.root)
    chapter = normalize_chapter(args.chapter)
    report = build_report(root, chapter)
    if args.write:
        out = root / "生产数据"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"comic_chapter_beat_audit_{chapter}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (out / f"comic_chapter_beat_audit_{chapter}.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_markdown(report))
    return 1 if args.strict and report["summary"]["must"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
