#!/usr/bin/env python3
"""分话节拍/边界机检（2026-07 标准审计·port 自 n2d 拆集节拍模式的漫画重实现，不跨线 import）。

comic-script 此前唯一机检是源语义归一化；"本话必须有开场吸引/冲突/转折/结尾钩子"全是散文规则。
实证空档：金瓶梅 10 回只拆了 1 回、红楼梦 120 回只拆序章，**无全书拆分蓝图**，第 2 话已断供。
本审计补四类检查（report-only 起步；`--strict` 对 must 级 exit 1）：

① missing_opening_hook / weak_ending：首格该是 opening_hook 类、末格必须是钩子类
   （2026 实搜共识：条漫每话结尾必须钩子、绝不平收；付费卡点前 30 话定生死）。
② climax_position：高潮格（action_peak/turning_point/reveal 高权重）应落在本话 ~2/3 处
   （行业惯例 2/3；过早=后半塌，过晚=憋不到）。
③ panel_count_band：每话 20-60 格（快看官方门槛 ≥20 格·2026-07 实抓官方投稿页；
   商业周更常态 40-60；60+ 提示拆话）。
④ split_blueprint_missing：作品根缺 `脚本/split_blueprint.json`（全书候选话次边界蓝图）
   → 拆分只做了眼前一话、后续断供的结构性风险（实证：第 2 话卡死的根因层）。

阈值出处：格数带/钩子/高潮位来自 2026-07 实搜（快看官方页=高置信；其余从业者口径=中，
env 可标定）；蓝图检查是本仓实证结论。

用法：
  cd skills/comic-script/scripts
  python3 chapter_beat_audit.py <作品根> 第N话 [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

VERSION = 1
KIND = "comic_chapter_beat_audit"

PANEL_MIN = int(os.environ.get("COMIC_PANEL_MIN", "20"))       # 快看官方成稿门槛（2026-07 官方页）
PANEL_MAX = int(os.environ.get("COMIC_PANEL_MAX", "60"))       # 商业周更常态上限（从业者口径·中置信）
CLIMAX_LO = float(os.environ.get("COMIC_CLIMAX_LO", "0.5"))    # 高潮位健康带（~2/3 处·从业者口径）
CLIMAX_HI = float(os.environ.get("COMIC_CLIMAX_HI", "0.85"))

OPENING_FUNCS = ("opening_hook", "cold_open", "hook")
ENDING_FUNCS = ("cliffhanger", "hook", "reveal", "turning_point", "page_turn_reveal")
CLIMAX_FUNCS = ("action_peak", "turning_point", "climax", "reveal", "payoff")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_chapter(value: str) -> str:
    raw = str(value or "").strip()
    if raw.startswith("第") and raw.endswith("话"):
        return raw
    m = re.search(r"\d+", raw)
    return f"第{int(m.group(0))}话" if m else raw


def load_panels(root: Path, chapter: str) -> List[Dict[str, Any]]:
    path = root / "脚本" / chapter / "panel_script.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [p for p in (data.get("panels") or []) if isinstance(p, Mapping)]


def _func(panel: Mapping[str, Any]) -> str:
    return str(panel.get("story_function") or "").strip().lower()


def audit_beats(panels: List[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """节拍检查（纯函数·可测）。返回 findings（severity: must/warn/info）。"""
    findings: List[Dict[str, Any]] = []
    if not panels:
        return [{"severity": "must", "code": "empty_panel_script",
                 "message": "panel_script.json 无格——先完成分格脚本。"}]
    n = len(panels)
    # ① 首/末格钩子
    first = _func(panels[0])
    if not any(tok in first for tok in OPENING_FUNCS):
        findings.append({"severity": "warn", "code": "missing_opening_hook",
                         "message": f"首格 story_function={first or '空'}，不是开场钩类"
                                    "（opening_hook/cold_open）——条漫首屏决定点开率，第一格就要给读者停下的理由。"})
    last = _func(panels[-1])
    if not any(tok in last for tok in ENDING_FUNCS):
        findings.append({"severity": "must", "code": "weak_ending",
                         "message": f"末格 story_function={last or '空'}，不是钩子/揭示/反转类——"
                                    "条漫每话结尾必须钩住下一话（2026 从业共识：绝不平收；付费模式下这是生死线）。"})
    # ② 高潮位
    climax_idx = [i for i, p in enumerate(panels)
                  if any(tok in _func(p) for tok in CLIMAX_FUNCS)]
    if not climax_idx:
        findings.append({"severity": "warn", "code": "no_climax_panel",
                         "message": "本话没有任何 action_peak/turning_point/reveal 高潮格——"
                                    "全程平推的一话读者没有非看完不可的理由。"})
    elif n >= 8:
        peak = max(climax_idx) / (n - 1)
        if peak < CLIMAX_LO:
            findings.append({"severity": "warn", "code": "climax_too_early",
                             "message": f"最后一个高潮格落在 {peak:.0%} 位（<{CLIMAX_LO:.0%}）——"
                                        "后半话全是收尾/交代，读者在高潮后就走了；把兑现后移或在后半补反转。"})
        elif peak > CLIMAX_HI and not any(tok in last for tok in ("cliffhanger", "hook")):
            findings.append({"severity": "info", "code": "climax_at_tail",
                             "message": f"高潮压在 {peak:.0%} 位且末格非悬置钩——确认不是憋到最后一格才爆、"
                                        "读者中段无支撑。"})
    # ③ 格数带
    if n < PANEL_MIN:
        findings.append({"severity": "warn", "code": "panel_count_below_platform_floor",
                         "message": f"本话仅 {n} 格 < {PANEL_MIN}（快看官方成稿门槛 ≥20 格·2026-07 官方投稿页）——"
                                    "投稿平台会拒收；确认是有意的短话或补格。"})
    elif n > PANEL_MAX:
        findings.append({"severity": "warn", "code": "panel_count_above_weekly_norm",
                         "message": f"本话 {n} 格 > {PANEL_MAX}（商业周更常态 40-60）——"
                                    "考虑按钩子断点拆成两话（多一个付费/追更卡点）。"})
    return findings


def audit_blueprint(root: Path) -> List[Dict[str, Any]]:
    """全书拆分蓝图检查：源本多回/多章但只拆了眼前话次=结构性断供风险。"""
    findings: List[Dict[str, Any]] = []
    blueprint = root / "脚本" / "split_blueprint.json"
    if blueprint.is_file():
        try:
            data = json.loads(blueprint.read_text(encoding="utf-8"))
            planned = data.get("chapters") or data.get("episodes") or []
            if isinstance(planned, list) and planned:
                return findings
        except Exception:
            pass
        findings.append({"severity": "warn", "code": "split_blueprint_invalid",
                         "message": "脚本/split_blueprint.json 存在但无有效话次列表——修复或重建全书拆分蓝图。"})
        return findings
    # 已启动话次数 vs 源本规模（source_manifest 若有）
    started = len([d for d in (root / "脚本").glob("第*话") if d.is_dir()]) if (root / "脚本").is_dir() else 0
    scale_note = ""
    manifest = root / "源本" / "source_manifest.json"
    if manifest.is_file():
        try:
            m = json.loads(manifest.read_text(encoding="utf-8"))
            units = m.get("chapter_count") or m.get("回数") or len(m.get("chapters") or [])
            if units:
                scale_note = f"（源本约 {units} 回/章，已启动仅 {started} 话）"
        except Exception:
            pass
    findings.append({"severity": "warn", "code": "split_blueprint_missing",
                     "message": f"缺 脚本/split_blueprint.json 全书拆分蓝图{scale_note}——"
                                "拆分只覆盖眼前话次，后续话次会断供（实证：第 2 话曾因此卡死）。"
                                "先按『冲突→爽点/揭示→钩子』闭环把全书粗切成候选话次边界账"
                                "（每话记 source_range/核心冲突/结尾钩子候选/预计格数），再逐话精修。"})
    return findings


def build_report(root: Path, chapter: str) -> Dict[str, Any]:
    panels = load_panels(root, chapter)
    findings = audit_beats(panels) + audit_blueprint(root)
    return {
        "kind": KIND, "version": VERSION, "chapter": chapter, "generated_at": now_iso(),
        "thresholds": {"panel_min": PANEL_MIN, "panel_max": PANEL_MAX,
                       "climax_band": [CLIMAX_LO, CLIMAX_HI],
                       "provenance": "格数下限=快看官方投稿页(2026-07 实抓·高)；格数上限/高潮位/结尾钩="
                                     "从业者口径(中)·env 可标定"},
        "summary": {
            "panels": len(panels),
            "must": sum(1 for f in findings if f["severity"] == "must"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "info": sum(1 for f in findings if f["severity"] == "info"),
        },
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [f"# 分话节拍机检 · {report.get('chapter')}",
             "",
             f"- 格 {s.get('panels')} · must {s.get('must')} · warn {s.get('warn')} · info {s.get('info')}",
             ""]
    icon = {"must": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 分话节拍健康")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="must 级 exit 1")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    chapter = normalize_chapter(ns.chapter)
    report = build_report(root, chapter)
    if ns.write:
        out = root / "生产数据"
        out.mkdir(parents=True, exist_ok=True)
        (out / f"comic_chapter_beat_audit_{chapter}.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (out / f"comic_chapter_beat_audit_{chapter}.md").write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    if ns.strict and report["summary"]["must"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
