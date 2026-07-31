#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""广告补拍任务包（传统 pickup shots 纪律的 AI 线对应物·advisory·本线自包含）。

为什么：传统制片在粗剪评审后必列 **pickup list**（缺 coverage/穿帮/技术废片/产品镜补拍），
预留补拍日逐条清账。本线的生产实锤（星盒手账App，git 历史）暴露的正是反面：product_qc
12 条 warn 悬置、video_qc 6 block 无人回收、gate 22 block 至项目死亡——**"抓到问题"与
"处置问题"之间没有闭环**，QC 报告只是报告，没人把它变成"下一步做什么"。

本脚本把既有 QC/止损账本收口成结构化补拍任务包：
  · 逐条 QC finding → pickup task（shot/资产 + 病因 + 确定性处置建议）
  · 与生成账本联动：单资产已抽 >N 次仍 fail → 处置升级为"改分镜/换处方"
    （传统行规：补拍救不了的回炉重拍，不是继续抽卡）
  · 补拍继承纪律写进每条任务：补拍镜必须继承原镜的 protect/continuity/资产声明
    （防补拍镜自己漂——传统 continuity sheet 的补拍页规矩）

**审不是门**：处置决定归人（也许某条 warn 客户可接受），findings 只 warn/info、
`summary.block` 恒 0；gate 以 advisory 侧车并入 video/compose（报告缺失 info）。
真正的硬挡仍归 gate 的 product_qc/video_qc/verifier_coverage 确定性闸——本脚本管的是
"挡下来之后，路在哪"。

用法：
    python3 pickup_plan.py <作品根> [--write] [--json] [--strict]
阈值 env：AD_PICKUP_MAX_ATTEMPTS=4（超过则处置升级为改分镜/换处方）
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

KIND = "ad_pickup_plan"
REPORT_REL = os.path.join("生产数据", "ad_pickup_plan.json")
EVENTS_REL = os.path.join("生产数据", "production_events.jsonl")
PRODUCT_QC_REL = os.path.join("出图", "分镜", "product_qc.json")
VIDEO_QC_REL = os.path.join("出视频", "分镜", "video_qc.json")

MAX_ATTEMPTS = int(os.environ.get("AD_PICKUP_MAX_ATTEMPTS", "4"))

# 病因 → 确定性处置建议（词面路由，未命中给通用建议）。
_ACTION_ROUTES = (
    ("dhash|漂移|drift", "回 ad-image/reference_planner 补该镜参考处方（定妆多视图分参考）后重出；连续失败换后端档"),
    ("brand_color|品牌色|ΔE|delta_e", "核对品牌色规范→出图 prompt 锁色/后期调色；整图氛围色偏离而产品色对的可人工放行"),
    ("logo|ncc", "补 logo 模板注册或重出该镜（logo 变形/缺失是硬伤，不可调色救）"),
    ("clip_presence|未回收|querying|submission", "先回收远端视频（render_dreamina --collect 同族命令）；提交后长期未回收=账面死锁"),
    ("backend|后端", "按 gate 后端治理决议执行：要么按现行策略重出，要么落 合规/image_backend_override.json 签核例外——二选一，不许悬置"),
    ("seam|色跳|color_jump", "相邻镜调色对齐或声明有意转场；合成期加过渡"),
    ("text|字|ocr|渲染", "文字渲染失败镜改为后期字卡（合成期烧字），别用生成器硬抽文字"),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def finding(severity: str, code: str, msg: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"severity": severity, "code": code, "msg": msg}
    out.update(extra)
    return out


def load_json_file(path: Path) -> Optional[dict]:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def load_attempts(root: Path) -> Dict[str, int]:
    """逐资产生成次数（event=generation，与 stop_loss 同口径）。"""
    path = root / EVENTS_REL
    if not path.is_file():
        return {}
    attempts: Dict[str, int] = defaultdict(int)
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict) or row.get("event") != "generation":
            continue
        gen = row.get("generation") if isinstance(row.get("generation"), Mapping) else {}
        if gen.get("asset"):
            attempts[str(gen["asset"])] += 1
    return dict(attempts)


def route_action(text: str) -> str:
    import re
    blob = str(text or "").lower()
    for pattern, action in _ACTION_ROUTES:
        if re.search(pattern, blob, re.IGNORECASE):
            return action
    return "按 finding 病因回上游修复后重出该镜（改 prompt/参考/处方，不要原样重抽）"


def _subject_of(entry: Mapping[str, Any]) -> str:
    """从 QC finding 里尽力取出镜/资产标识（各 QC 键名不一，词面容忍）。"""
    for key in ("shot", "shot_id", "clip", "clip_id", "asset", "image", "file", "path", "subject"):
        val = entry.get(key)
        if val:
            return str(val)
    shots = entry.get("shots")
    if isinstance(shots, (list, tuple)) and shots:
        return str(shots[0])
    return ""


def collect_tasks(root: Path) -> List[Dict[str, Any]]:
    """QC 报告 findings（block/warn）→ pickup tasks。报告缺失=该阶段还没跑到，不臆造任务。"""
    attempts = load_attempts(root)
    tasks: List[Dict[str, Any]] = []
    for rel, source in ((PRODUCT_QC_REL, "product_qc"), (VIDEO_QC_REL, "video_qc")):
        report = load_json_file(root / rel)
        if not report:
            continue
        for entry in report.get("findings") or []:
            if not isinstance(entry, Mapping):
                continue
            sev = str(entry.get("severity") or "")
            if sev not in ("block", "warn"):
                continue
            subject = _subject_of(entry)
            msg = str(entry.get("msg") or entry.get("message") or entry.get("code") or "")
            n_attempts = attempts.get(subject, 0)
            escalated = n_attempts > MAX_ATTEMPTS
            action = ("已生成 %d 次仍 fail（>%d）——补拍救不了的回炉重拍：改分镜/换手法/换后端档，"
                      "不要继续抽卡" % (n_attempts, MAX_ATTEMPTS)) if escalated \
                else route_action(f"{entry.get('code')} {msg}")
            tasks.append({
                "source": source, "report": rel,
                "subject": subject or "(未标注镜/资产)",
                "code": str(entry.get("code") or entry.get("check") or ""),
                "severity": sev, "blocking": sev == "block",
                "attempts": n_attempts, "escalated": escalated,
                "action": action,
                "inherit": "补拍镜必须继承原镜的 protect/安全区、continuity、资产/参考声明（防补拍镜自己漂）",
            })
    order = {"block": 0, "warn": 1}
    tasks.sort(key=lambda t: (order.get(t["severity"], 9), t["source"], t["subject"]))
    return tasks


def build(root: Path) -> Dict[str, Any]:
    root = Path(root)
    findings: List[Dict[str, Any]] = []
    has_any_qc = (root / PRODUCT_QC_REL).is_file() or (root / VIDEO_QC_REL).is_file()
    tasks = collect_tasks(root)
    blocking = [t for t in tasks if t["blocking"]]
    escalated = [t for t in tasks if t["escalated"]]

    if not has_any_qc:
        findings.append(finding("info", "no_qc_reports",
                                "product_qc/video_qc 都还没跑——没有 QC 结论可收口（先出图/出视频再回来列补拍单）。"))
    elif blocking:
        findings.append(finding("warn", "pickup_backlog_open",
                                f"{len(blocking)} 条 blocking fail 待处置（任务包已逐条给出确定性处置建议）——"
                                "生产实锤教训：block 悬置不清就是项目死因；每条要么执行补拍，要么签核豁免留痕，"
                                "不许静默搁置", count=len(blocking)))
    elif tasks:
        findings.append(finding("info", "pickup_warn_only",
                                f"{len(tasks)} 条 warn 级待人工确认（无 blocking fail）——逐条过目后接受或补拍",
                                count=len(tasks)))
    if escalated:
        findings.append(finding("warn", "pickup_escalated",
                                f"{len(escalated)} 条任务已超单资产生成次数上限（>{MAX_ATTEMPTS}）——"
                                "处置已升级为改分镜/换处方；继续原样重抽=烧钱不改命",
                                subjects=[t["subject"] for t in escalated[:6]]))

    return {
        "schema_version": 1, "kind": KIND, "project_root": str(root), "generated_at": now_iso(),
        "thresholds": {"max_attempts": MAX_ATTEMPTS,
                       "note": "审不是门：处置决定归人，findings 只 warn/info，summary.block 恒 0；"
                               "硬挡归 gate 的 QC/覆盖账本确定性闸"},
        "tasks": tasks,
        "summary": {"block": 0,
                    "warn": sum(1 for f in findings if f["severity"] == "warn"),
                    "info": sum(1 for f in findings if f["severity"] == "info"),
                    "tasks": len(tasks), "blocking_tasks": len(blocking)},
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = ["# 广告补拍任务包（pickup list）", "",
             f"- 任务 {s.get('tasks')} 条（blocking {s.get('blocking_tasks')}）· "
             f"warn {s.get('warn')} · info {s.get('info')}（advisory·不产 block）", ""]
    icon = {"block": "⛔", "warn": "⚠️", "info": "ℹ️"}
    for t in report.get("tasks") or []:
        esc = "（已升级：改分镜/换处方）" if t.get("escalated") else ""
        lines.append(f"- {icon.get(t['severity'], '·')} [{t['source']}] {t['subject']} `{t['code']}`"
                     f" ×{t['attempts']}次{esc} → {t['action']}")
    if not report.get("tasks"):
        lines.append("- ✅ 无待处置 QC fail")
    lines.append("")
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['msg']}")
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
    ap.add_argument("--strict", action="store_true", help="warn>0 时 exit 1")
    ns = ap.parse_args(argv)
    report = build(Path(ns.root))
    if ns.write:
        write_report(Path(ns.root), report)
    print(json.dumps(report, ensure_ascii=False, indent=2) if ns.json else render_markdown(report))
    return 1 if (ns.strict and report["summary"]["warn"]) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
