#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ingest real listener/platform feedback for a song project."""
from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import date
from typing import Any


EVENTS_KIND = "song_feedback_events"
SUMMARY_KIND = "song_feedback_summary"


FIELD_ALIASES = {
    "take_id": ("take_id", "take", "版本", "稿件版本"),
    "platform": ("platform", "平台"),
    "source_name": ("source_name", "source", "批次", "来源"),
    "plays": ("plays", "starts", "播放", "开始"),
    "completes": ("completes", "complete", "完播"),
    "skips": ("skips", "drops", "跳出", "跳过"),
    "likes": ("likes", "点赞"),
    "saves": ("saves", "收藏"),
    "shares": ("shares", "分享"),
    "comments": ("comments", "评论数"),
    "reuses": ("reuses", "短视频复用", "二创"),
    "comment": ("comment", "text", "评论"),
}


def pick(row: dict[str, Any], key: str, default: Any = "") -> Any:
    for name in FIELD_ALIASES[key]:
        if name in row and row[name] not in ("", None):
            return row[name]
    return default


def as_int(value: Any) -> int:
    try:
        if value in ("", None):
            return 0
        return int(float(str(value).strip()))
    except Exception:
        return 0


def read_rows(path: str) -> list[dict[str, Any]]:
    if path.lower().endswith(".jsonl"):
        out = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        out.append(payload)
        return out
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def normalize_rows(rows: list[dict[str, Any]], *, platform: str, source_name: str) -> list[dict[str, Any]]:
    out = []
    for idx, row in enumerate(rows, 1):
        comment = str(pick(row, "comment", "") or "")
        comments_count = as_int(pick(row, "comments", 0)) or (1 if comment else 0)
        out.append({
            "schema_version": 1,
            "kind": EVENTS_KIND,
            "row_id": idx,
            "take_id": str(pick(row, "take_id", "selected") or "selected"),
            "platform": str(pick(row, "platform", platform) or platform),
            "source_name": str(pick(row, "source_name", source_name) or source_name),
            "plays": as_int(pick(row, "plays", 0)),
            "completes": as_int(pick(row, "completes", 0)),
            "skips": as_int(pick(row, "skips", 0)),
            "likes": as_int(pick(row, "likes", 0)),
            "saves": as_int(pick(row, "saves", 0)),
            "shares": as_int(pick(row, "shares", 0)),
            "comments": comments_count,
            "reuses": as_int(pick(row, "reuses", 0)),
            "comment": comment,
        })
    return out


def summarize(events: list[dict[str, Any]], root: str) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "plays": 0, "completes": 0, "skips": 0, "likes": 0, "saves": 0,
        "shares": 0, "comments": 0, "reuses": 0, "comment_samples": [],
    })
    for event in events:
        key = "|".join([event.get("platform") or "", event.get("source_name") or "", event.get("take_id") or "selected"])
        group = groups[key]
        group["platform"], group["source_name"], group["take_id"] = key.split("|")
        for field in ("plays", "completes", "skips", "likes", "saves", "shares", "comments", "reuses"):
            group[field] += int(event.get(field) or 0)
        if event.get("comment") and len(group["comment_samples"]) < 10:
            group["comment_samples"].append(event["comment"])
    group_rows = []
    for group in groups.values():
        plays = max(int(group["plays"] or 0), 0)
        group["completion_rate"] = round(group["completes"] / plays, 4) if plays else 0
        group["skip_rate"] = round(group["skips"] / plays, 4) if plays else 0
        group["save_rate"] = round(group["saves"] / plays, 4) if plays else 0
        group["share_rate"] = round(group["shares"] / plays, 4) if plays else 0
        group["reuse_rate"] = round(group["reuses"] / plays, 4) if plays else 0
        group["signals"] = signals_for(group)
        group_rows.append(group)
    group_rows.sort(key=lambda g: (-g.get("completion_rate", 0), -g.get("save_rate", 0), -g.get("share_rate", 0)))
    return {
        "schema_version": 1,
        "kind": SUMMARY_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "event_count": len(events),
        "groups": group_rows,
        "best_group": group_rows[0] if group_rows else {},
        "recommendations": recommendations(group_rows),
    }


def signals_for(group: dict[str, Any]) -> list[str]:
    signals = []
    if group.get("plays", 0) < 50:
        signals.append("low_sample")
    if group.get("completion_rate", 0) < 0.35 and group.get("plays", 0) >= 50:
        signals.append("completion_weak")
    if group.get("save_rate", 0) >= 0.03:
        signals.append("save_signal")
    if group.get("share_rate", 0) >= 0.02 or group.get("reuse_rate", 0) >= 0.01:
        signals.append("spread_signal")
    return signals


def recommendations(groups: list[dict[str, Any]]) -> list[str]:
    if not groups:
        return ["暂无数据；先导入平台或测试听众反馈。"]
    recs = []
    best = groups[0]
    recs.append(f"当前最佳组：{best.get('platform')} / {best.get('source_name')} / {best.get('take_id')}。")
    weak = [g for g in groups if "completion_weak" in g.get("signals", [])]
    if weak:
        recs.append("存在完播弱项：优先复查前 8-15 秒 hook、封面/标题与投放人群匹配。")
    if any("spread_signal" in g.get("signals", []) for g in groups):
        recs.append("已有分享/复用信号：保留该 take 的副歌/节奏核心，优先做短视频剪辑版本。")
    if all("low_sample" in g.get("signals", []) for g in groups):
        recs.append("全部样本偏低：不要据此重写歌曲，先扩大同条件测试。")
    return recs


def write_outputs(root: str, events: list[dict[str, Any]], summary: dict[str, Any]) -> tuple[str, str, str]:
    out_dir = os.path.join(root, "发行")
    os.makedirs(out_dir, exist_ok=True)
    events_path = os.path.join(out_dir, "feedback_events.jsonl")
    summary_path = os.path.join(out_dir, "feedback_summary.json")
    report_path = os.path.join(out_dir, "feedback_report.md")
    with open(events_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(render_markdown(summary))
    return events_path, summary_path, report_path


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Song Feedback Report",
        "",
        f"- 生成日期：{summary.get('generated_at')}",
        f"- event_count：{summary.get('event_count')}",
        "",
        "| platform | source | take | plays | completion | saves | shares | reuses | signals |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for group in summary.get("groups") or []:
        lines.append(
            f"| {group.get('platform')} | {group.get('source_name')} | {group.get('take_id')} | "
            f"{group.get('plays')} | {group.get('completion_rate')} | {group.get('saves')} | "
            f"{group.get('shares')} | {group.get('reuses')} | {', '.join(group.get('signals') or [])} |"
        )
    lines.extend(["", "## Recommendations", ""])
    for item in summary.get("recommendations") or []:
        lines.append(f"- {item}")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="导入歌曲真实反馈/投放数据")
    ap.add_argument("project_root")
    ap.add_argument("--input", required=True)
    ap.add_argument("--platform", default="manual")
    ap.add_argument("--source-name", default="feedback")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    rows = read_rows(args.input)
    events = normalize_rows(rows, platform=args.platform, source_name=args.source_name)
    summary = summarize(events, root)
    events_path, summary_path, report_path = write_outputs(root, events, summary)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"[ok] feedback events  → {events_path}")
        print(f"[ok] feedback summary → {summary_path}")
        print(f"[ok] feedback report  → {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
