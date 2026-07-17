#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告批量生成止损审计（n2d stop_loss 的广告薄版·本线自包含·advisory）。

为什么：AI 出图/出视频是按次计费的重抽循环，"再抽一次就好了"最烧钱。渲染器已把每次
生成写进 `生产数据/production_events.jsonl`（stage=image/video·event=generation/submission·
credit_count），本审计把这本账变成三个可执行的止损信号：

  · `redraw_rate_high`      —— 重抽率（≥2 次生成的资产占比）超阈值：先修 prompt/参考，别继续抽卡
  · `asset_attempts_high`   —— 单资产生成次数超阈值：这镜的问题不是随机噪声，回上游改处方
  · `credits_spend_high`    —— 累计 credit 消耗超预算线（设了 --max-credits / env 才判）
  · `qc_block_open`         —— product_qc/video_qc 仍有 block 却还在继续生成：先修当前坏图

**审不是门**：止损决定归人（也许客户就是要求重抽二十次），所以 findings 只 warn/info、
`summary.block` 恒 0；gate 以 advisory 侧车并入（报告缺失 info、warn 降档规则同 creative_axis）。
账本为空 → `no_evidence` info（机检空转要显式，不能静默绿灯）。

用法：
    python3 stop_loss.py <作品根> [--write] [--json] [--strict] [--max-credits N]
阈值 env：AD_STOPLOSS_MAX_REDRAW_RATE=0.35  AD_STOPLOSS_MAX_ATTEMPTS=4
         AD_STOPLOSS_MAX_QC_BLOCK=0（qc block 数>此值即报）  AD_STOPLOSS_MAX_CREDITS
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

KIND = "ad_stop_loss"
REPORT_REL = os.path.join("生产数据", "ad_stop_loss.json")
EVENTS_REL = os.path.join("生产数据", "production_events.jsonl")

MAX_REDRAW_RATE = float(os.environ.get("AD_STOPLOSS_MAX_REDRAW_RATE", "0.35"))
MAX_ATTEMPTS = int(os.environ.get("AD_STOPLOSS_MAX_ATTEMPTS", "4"))
MAX_QC_BLOCK = int(os.environ.get("AD_STOPLOSS_MAX_QC_BLOCK", "0"))
ENV_MAX_CREDITS = os.environ.get("AD_STOPLOSS_MAX_CREDITS", "")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    out.update(extra)
    return out


def load_events(root: Path) -> List[Dict[str, Any]]:
    path = root / EVENTS_REL
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict) and row.get("event") in {"generation", "submission"}:
            rows.append(row)
    return rows


def load_summary_block(root: Path, rel: str) -> Optional[int]:
    try:
        data = json.loads((root / rel).read_text(encoding="utf-8"))
        return int((data.get("summary") or {}).get("block"))
    except Exception:
        return None


def stage_stats(events: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """按 stage 聚合：逐资产生成次数（只数 event=generation，submission 是提交非产出）与 credit 总量。"""
    per_stage: Dict[str, Dict[str, Any]] = {}
    for row in events:
        stage = str(row.get("stage") or "unknown")
        gen = row.get("generation") if isinstance(row.get("generation"), Mapping) else {}
        st = per_stage.setdefault(stage, {"attempts": defaultdict(int), "credits": 0.0, "events": 0})
        st["events"] += 1
        try:
            st["credits"] += float(gen.get("credit_count") or 0)
        except (TypeError, ValueError):
            pass
        if row.get("event") == "generation" and gen.get("asset"):
            st["attempts"][str(gen["asset"])] += 1
    return per_stage


def build(root: Path, max_credits: Optional[float] = None) -> Dict[str, Any]:
    root = Path(root)
    events = load_events(root)
    findings: List[Dict[str, Any]] = []
    stats = stage_stats(events)
    if max_credits is None and ENV_MAX_CREDITS:
        try:
            max_credits = float(ENV_MAX_CREDITS)
        except ValueError:
            max_credits = None

    if not events:
        findings.append(finding("info", "no_evidence",
                                f"{EVENTS_REL} 无生成事件——止损审计空转（尚未开始生成，或渲染器没走本线 runner）。"
                                "空账不是健康证明。"))

    stages_out: Dict[str, Any] = {}
    total_credits = 0.0
    for stage, st in sorted(stats.items()):
        attempts: Dict[str, int] = dict(st["attempts"])
        assets = len(attempts)
        redrawn = sum(1 for n in attempts.values() if n >= 2)
        redraw_rate = (redrawn / assets) if assets else 0.0
        worst = max(attempts.items(), key=lambda kv: kv[1]) if attempts else ("", 0)
        total_credits += st["credits"]
        stages_out[stage] = {
            "generation_events": st["events"], "assets": assets, "redrawn_assets": redrawn,
            "redraw_rate": round(redraw_rate, 3), "credits": round(st["credits"], 2),
            "worst_asset": {"asset": worst[0], "attempts": worst[1]},
        }
        if assets >= 3 and redraw_rate > MAX_REDRAW_RATE:
            findings.append(finding("warn", "redraw_rate_high",
                                    f"{stage} 重抽率 {redraw_rate:.0%} > {MAX_REDRAW_RATE:.0%}"
                                    f"（{redrawn}/{assets} 个资产抽了≥2次）——别继续抽卡，回上游修 prompt/参考处方"
                                    "（reference_planner 事前处方/定妆多视图分参考）再生成",
                                    stage=stage))
        if worst[1] > MAX_ATTEMPTS:
            findings.append(finding("warn", "asset_attempts_high",
                                    f"{stage}·{worst[0]} 已生成 {worst[1]} 次（>{MAX_ATTEMPTS}）——"
                                    "这不是随机噪声，是处方问题：停手，改参考/prompt/换后端档再抽",
                                    stage=stage, asset=worst[0], attempts=worst[1]))
    if max_credits is not None and total_credits > max_credits:
        findings.append(finding("warn", "credits_spend_high",
                                f"累计 credit 消耗 {total_credits:.0f} 已超预算线 {max_credits:.0f}——"
                                "与制片确认追加预算或砍范围，不要静默烧完"))

    for rel, label in ((os.path.join("出图", "分镜", "product_qc.json"), "product_qc"),
                       (os.path.join("出视频", "分镜", "video_qc.json"), "video_qc")):
        blocks = load_summary_block(root, rel)
        if blocks is not None and blocks > MAX_QC_BLOCK and events:
            findings.append(finding("warn", "qc_block_open",
                                    f"{label} 仍有 block={blocks} 但生成账本还在增长——先修当前坏图/坏 Clip，"
                                    "带病续抽是最贵的浪费", report=rel))

    return {
        "schema_version": 1, "kind": KIND, "project_root": str(root), "generated_at": now_iso(),
        "thresholds": {"max_redraw_rate": MAX_REDRAW_RATE, "max_attempts": MAX_ATTEMPTS,
                       "max_qc_block": MAX_QC_BLOCK, "max_credits": max_credits,
                       "note": "审不是门：止损决定归人，findings 只 warn/info，summary.block 恒 0"},
        "stages": stages_out,
        "total_credits": round(total_credits, 2),
        "summary": {"block": 0,
                    "warn": sum(1 for f in findings if f["severity"] == "warn"),
                    "info": sum(1 for f in findings if f["severity"] == "info")},
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    lines = ["# 广告生成止损审计", "",
             f"- 累计 credit：{report.get('total_credits')}",
             f"- warn {report['summary']['warn']} · info {report['summary']['info']}（advisory·不产 block）", ""]
    for stage, st in (report.get("stages") or {}).items():
        lines.append(f"- **{stage}**：{st['assets']} 资产 · 重抽率 {st['redraw_rate']:.0%} · "
                     f"credits {st['credits']} · 最费 {st['worst_asset']['asset']}×{st['worst_asset']['attempts']}")
    lines.append("")
    icon = {"warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
    if not report.get("findings"):
        lines.append("- ✅ 重抽率/单资产次数/QC 状态均在阈值内")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    path = root / REPORT_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    for target, payload in ((path, json.dumps(report, ensure_ascii=False, indent=2) + "\n"),
                            (path.with_suffix(".md"), render_markdown(report))):
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, target)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--write", action="store_true", help=f"落盘 {REPORT_REL}（+ .md·原子写）")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-credits", type=float, default=None, help="credit 预算线（覆盖 env）")
    ap.add_argument("--strict", action="store_true", help="warn>0 时 exit 1")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    report = build(root, max_credits=ns.max_credits)
    if ns.write:
        write_report(root, report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
