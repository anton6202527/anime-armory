#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize real reader telemetry into chapter-level feedback artifacts."""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime


NEGATIVE_WORDS = (
    "弃", "退", "看不下去", "无聊", "拖", "水", "尬", "崩", "降智", "憋屈", "劝退",
    "boring", "drop", "confusing", "slow", "cringe",
)
POSITIVE_WORDS = (
    "爽", "好看", "追", "上头", "喜欢", "期待", "甜", "燃", "绝", "带感",
    "hooked", "love", "great", "excited",
)

FIELD_ALIASES = {
    "chapter": ("chapter", "章节", "chapter_no", "chapter_num", "章"),
    "event": ("event", "事件", "type", "行为"),
    "count": ("count", "数量", "cnt", "value"),
    "reader_id": ("reader_id", "user_id", "读者", "用户"),
    "views": ("views", "pv", "阅读次数"),
    "starts": ("starts", "start_count", "开始阅读", "开读"),
    "completes": ("completes", "complete_count", "完读", "读完"),
    "drops": ("drops", "drop_count", "弃读", "流失"),
    "likes": ("likes", "点赞"),
    "follows": ("follows", "追更", "收藏"),
    "completion_rate": ("completion_rate", "完读率"),
    "drop_rate": ("drop_rate", "弃读率", "流失率"),
    "avg_read_seconds": ("avg_read_seconds", "平均阅读秒数", "平均阅读时长"),
    "comment": ("comment", "comments", "评论", "text", "正文"),
    "sentiment": ("sentiment", "情绪", "polarity"),
    "timestamp": ("timestamp", "time", "created_at", "时间"),
    "ab_test_id": ("ab_test_id", "experiment_id", "实验ID", "AB测试", "ab"),
    "variant_id": ("variant_id", "variant", "版本", "组别", "bucket"),
    "take_id": ("take_id", "take", "稿件版本", "素材版本", "revision_id"),
}

EVENT_ALIASES = {
    "view": {"view", "views", "pv", "read", "阅读"},
    "start": {"start", "starts", "开始", "开读"},
    "complete": {"complete", "completes", "finish", "finished", "完读", "读完"},
    "drop": {"drop", "drops", "quit", "abandon", "弃读", "流失"},
    "comment": {"comment", "comments", "review", "评论"},
    "like": {"like", "likes", "点赞"},
    "follow": {"follow", "follows", "追更", "收藏"},
}


def _lookup(row, key, default=""):
    for alias in FIELD_ALIASES[key]:
        if alias in row and row.get(alias) not in (None, ""):
            return row.get(alias)
    return default


def parse_chapter(value):
    if isinstance(value, int):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    m = re.search(r"(\d+)", text)
    return int(m.group(1)) if m else None


def parse_number(value, default=0.0):
    if value in (None, ""):
        return default
    text = str(value).strip().replace(",", "")
    if text.endswith("%"):
        try:
            return float(text[:-1]) / 100.0
        except ValueError:
            return default
    try:
        return float(text)
    except ValueError:
        return default


def parse_int(value, default=0):
    return int(round(parse_number(value, default)))


def normalize_event(value):
    text = str(value or "").strip().lower()
    for event, aliases in EVENT_ALIASES.items():
        if text in {str(a).lower() for a in aliases}:
            return event
    return text or "metric"


def infer_sentiment(comment, explicit=""):
    text = str(comment or "").strip()
    explicit_l = str(explicit or "").strip().lower()
    if explicit_l in {"positive", "pos", "正面", "好评"}:
        return "positive"
    if explicit_l in {"negative", "neg", "负面", "差评"}:
        return "negative"
    if explicit_l in {"neutral", "中性"}:
        return "neutral"
    lowered = text.lower()
    if any(word in lowered or word in text for word in NEGATIVE_WORDS):
        return "negative"
    if any(word in lowered or word in text for word in POSITIVE_WORDS):
        return "positive"
    return "neutral" if text else ""


def read_input(path):
    suffix = os.path.splitext(path)[1].lower()
    rows = []
    if suffix == ".jsonl":
        with open(path, encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError(f"{path}:{line_no} 不是 JSON object")
                rows.append(payload)
    else:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows.extend(dict(row) for row in reader)
    return rows


def normalize_rows(rows, *, input_path, source_name, platform):
    normalized = []
    imported_at = datetime.now().isoformat(timespec="seconds")
    for index, row in enumerate(rows, 1):
        chapter = parse_chapter(_lookup(row, "chapter"))
        if chapter is None:
            continue
        comment = str(_lookup(row, "comment") or "").strip()
        event = normalize_event(_lookup(row, "event"))
        count = parse_int(_lookup(row, "count", 1), 1)
        rec = {
            "schema_version": 1,
            "kind": "novel_reader_telemetry_event",
            "source_name": source_name,
            "platform": platform,
            "input_file": os.path.abspath(input_path),
            "imported_at": imported_at,
            "row_index": index,
            "chapter": chapter,
            "event": event,
            "count": count,
        }
        for key in ("reader_id", "timestamp", "ab_test_id", "variant_id", "take_id"):
            value = _lookup(row, key)
            if value not in (None, ""):
                rec[key] = str(value)
        for key in ("views", "starts", "completes", "drops", "likes", "follows"):
            value = _lookup(row, key)
            if value not in (None, ""):
                rec[key] = parse_int(value)
        for key in ("completion_rate", "drop_rate", "avg_read_seconds"):
            value = _lookup(row, key)
            if value not in (None, ""):
                rec[key] = parse_number(value)
        if comment:
            rec["comment"] = comment
            rec["sentiment"] = infer_sentiment(comment, _lookup(row, "sentiment"))
            if event == "metric":
                rec["event"] = "comment"
        normalized.append(rec)
    return normalized


def load_existing_jsonl(path):
    records = []
    if not os.path.isfile(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict) and payload.get("kind") == "novel_reader_telemetry_event":
                records.append(payload)
    return records


def _empty_chapter(chapter):
    return {
        "chapter": chapter,
        "views": 0,
        "starts": 0,
        "completes": 0,
        "drops": 0,
        "likes": 0,
        "follows": 0,
        "comments": [],
        "_completion_rates": [],
        "_drop_rates": [],
        "_read_seconds": [],
    }


def aggregate(records, *, min_sample=20, low_completion=0.55, high_drop=0.35):
    by_chapter = {}
    for rec in records:
        ch = rec.get("chapter")
        if not isinstance(ch, int):
            continue
        row = by_chapter.setdefault(ch, _empty_chapter(ch))
        for key in ("views", "starts", "completes", "drops", "likes", "follows"):
            row[key] += int(rec.get(key) or 0)
        event = rec.get("event")
        count = int(rec.get("count") or 1)
        if event in {"view", "start", "complete", "drop", "like", "follow"}:
            field = {
                "view": "views",
                "start": "starts",
                "complete": "completes",
                "drop": "drops",
                "like": "likes",
                "follow": "follows",
            }[event]
            if not rec.get(field):
                row[field] += count
        if rec.get("comment"):
            row["comments"].append({
                "text": str(rec.get("comment")),
                "sentiment": rec.get("sentiment") or infer_sentiment(rec.get("comment")),
                "source_name": rec.get("source_name"),
            })
        if "completion_rate" in rec:
            row["_completion_rates"].append(float(rec["completion_rate"]))
        if "drop_rate" in rec:
            row["_drop_rates"].append(float(rec["drop_rate"]))
        if "avg_read_seconds" in rec:
            row["_read_seconds"].append(float(rec["avg_read_seconds"]))

    chapters = []
    for ch in sorted(by_chapter):
        row = by_chapter[ch]
        starts = row["starts"] or row["views"]
        completion_rate = (
            row["completes"] / starts
            if starts
            else (sum(row["_completion_rates"]) / len(row["_completion_rates"]) if row["_completion_rates"] else None)
        )
        drop_rate = (
            row["drops"] / starts
            if starts
            else (sum(row["_drop_rates"]) / len(row["_drop_rates"]) if row["_drop_rates"] else None)
        )
        avg_read_seconds = (
            round(sum(row["_read_seconds"]) / len(row["_read_seconds"]), 2)
            if row["_read_seconds"] else None
        )
        comments = row["comments"]
        neg = sum(1 for item in comments if item.get("sentiment") == "negative")
        pos = sum(1 for item in comments if item.get("sentiment") == "positive")
        flags = []
        if starts and starts < min_sample:
            flags.append("low_sample")
        if completion_rate is not None and completion_rate < low_completion:
            flags.append("low_completion")
        if drop_rate is not None and drop_rate > high_drop:
            flags.append("high_drop")
        if comments and neg >= max(2, len(comments) * 0.3):
            flags.append("negative_comment_spike")
        chapters.append({
            "chapter": ch,
            "views": row["views"],
            "starts": row["starts"],
            "completes": row["completes"],
            "drops": row["drops"],
            "completion_rate": round(completion_rate, 4) if completion_rate is not None else None,
            "drop_rate": round(drop_rate, 4) if drop_rate is not None else None,
            "avg_read_seconds": avg_read_seconds,
            "likes": row["likes"],
            "follows": row["follows"],
            "comment_count": len(comments),
            "positive_comments": pos,
            "negative_comments": neg,
            "sample_comments": [item["text"] for item in comments[:5]],
            "flags": flags,
        })
    return chapters


def aggregate_experiments(records, *, min_sample=20):
    groups = {}
    for rec in records:
        ab_test_id = str(rec.get("ab_test_id") or "").strip()
        variant_id = str(rec.get("variant_id") or "").strip()
        if not ab_test_id or not variant_id:
            continue
        key = (ab_test_id, variant_id)
        row = groups.setdefault(key, {
            "ab_test_id": ab_test_id,
            "variant_id": variant_id,
            "take_ids": set(),
            "chapters": set(),
            "views": 0,
            "starts": 0,
            "completes": 0,
            "drops": 0,
            "likes": 0,
            "follows": 0,
            "comments": 0,
        })
        if rec.get("take_id"):
            row["take_ids"].add(str(rec.get("take_id")))
        if isinstance(rec.get("chapter"), int):
            row["chapters"].add(rec["chapter"])
        for field in ("views", "starts", "completes", "drops", "likes", "follows"):
            row[field] += int(rec.get(field) or 0)
        event = rec.get("event")
        count = int(rec.get("count") or 1)
        if event in {"view", "start", "complete", "drop", "like", "follow"}:
            field = {
                "view": "views",
                "start": "starts",
                "complete": "completes",
                "drop": "drops",
                "like": "likes",
                "follow": "follows",
            }[event]
            if not rec.get(field):
                row[field] += count
        if rec.get("comment"):
            row["comments"] += 1

    out = []
    for row in groups.values():
        starts = row["starts"] or row["views"]
        completion_rate = row["completes"] / starts if starts else None
        drop_rate = row["drops"] / starts if starts else None
        flags = []
        if starts and starts < min_sample:
            flags.append("low_sample")
        out.append({
            "ab_test_id": row["ab_test_id"],
            "variant_id": row["variant_id"],
            "take_ids": sorted(row["take_ids"]),
            "chapters": sorted(row["chapters"]),
            "views": row["views"],
            "starts": row["starts"],
            "completes": row["completes"],
            "drops": row["drops"],
            "likes": row["likes"],
            "follows": row["follows"],
            "comments": row["comments"],
            "completion_rate": round(completion_rate, 4) if completion_rate is not None else None,
            "drop_rate": round(drop_rate, 4) if drop_rate is not None else None,
            "flags": flags,
        })
    out.sort(key=lambda item: (item["ab_test_id"], item["variant_id"]))
    leaders = []
    for ab_id in sorted({item["ab_test_id"] for item in out}):
        candidates = [item for item in out if item["ab_test_id"] == ab_id]
        candidates.sort(key=lambda item: (
            item["completion_rate"] if item["completion_rate"] is not None else -1.0,
            -(item["drop_rate"] if item["drop_rate"] is not None else 1.0),
            item["variant_id"],
        ), reverse=True)
        if candidates:
            leaders.append({
                "ab_test_id": ab_id,
                "status": "descriptive_leader",
                "decision": "inconclusive",
                "decision_authority": "context_only",
                "leader_variant_id": candidates[0]["variant_id"],
                # v1 compatibility: older consumers read variant_id from best_by_ab_test.
                "variant_id": candidates[0]["variant_id"],
                "completion_rate": candidates[0]["completion_rate"],
                "drop_rate": candidates[0]["drop_rate"],
                "take_ids": candidates[0]["take_ids"],
                "caveat": "low_sample" if "low_sample" in candidates[0]["flags"] else "",
                "reason": "raw rate ranking only; no statistical winner is declared",
            })
    return {
        "groups": out,
        "leaders_by_ab_test": leaders,
        "best_by_ab_test": leaders,
        "compatibility_note": "best_by_ab_test is a deprecated alias; entries are descriptive leaders, not winners",
        "decision_authority": "context_only",
    }


def build_summary(records, *, platform, source_name, min_sample, low_completion, high_drop):
    chapters = aggregate(records, min_sample=min_sample, low_completion=low_completion, high_drop=high_drop)
    experiments = aggregate_experiments(records, min_sample=min_sample)
    total_starts = sum((c["starts"] or c["views"]) for c in chapters)
    total_completes = sum(c["completes"] for c in chapters)
    total_drops = sum(c["drops"] for c in chapters)
    aggregate_completion = total_completes / total_starts if total_starts else None
    aggregate_drop = total_drops / total_starts if total_starts else None
    priority = sorted(
        [c for c in chapters if c["flags"]],
        key=lambda c: (
            "low_sample" in c["flags"],
            c["completion_rate"] if c["completion_rate"] is not None else 1.0,
            -(c["drop_rate"] if c["drop_rate"] is not None else 0.0),
            c["chapter"],
        ),
    )
    return {
        "schema_version": 1,
        "kind": "novel_reader_telemetry_summary",
        "generated_at": date.today().isoformat(),
        "platform": platform,
        "latest_source_name": source_name,
        "records_ingested": len(records),
        "thresholds": {
            "min_sample": min_sample,
            "low_completion": low_completion,
            "high_drop": high_drop,
        },
        "aggregate": {
            "chapter_count": len(chapters),
            "total_starts": total_starts,
            "total_completes": total_completes,
            "total_drops": total_drops,
            "completion_rate": round(aggregate_completion, 4) if aggregate_completion is not None else None,
            "drop_rate": round(aggregate_drop, 4) if aggregate_drop is not None else None,
            "total_comments": sum(c["comment_count"] for c in chapters),
        },
        "weakest_chapters": [c["chapter"] for c in priority[:8]],
        "chapters": chapters,
        "experiments": experiments,
    }


def apply_reader_test_plan(root, summary):
    plan_path = os.path.join(root, "评分", "reader_test_plan.json")
    if not os.path.isfile(plan_path):
        summary["reader_test_plan"] = {
            "present": False,
            "warning": "未找到 reader_test_plan.json；本批反馈只能做事后解释，A/B 归因可信度较低。",
        }
        return summary
    with open(plan_path, encoding="utf-8") as f:
        plan = json.load(f)
    variants = plan.get("variants") or []
    by_variant = {str(v.get("variant_id")): v for v in variants}
    by_take = {str(v.get("take_id")): v for v in variants if v.get("take_id")}
    min_delta = float((plan.get("retest_policy") or {}).get("min_completion_delta") or 0.05)
    for group in summary.get("experiments", {}).get("groups") or []:
        match = by_variant.get(str(group.get("variant_id")))
        if not match:
            for take in group.get("take_ids") or []:
                match = by_take.get(str(take))
                if match:
                    break
        if match:
            group["planned_hypothesis"] = match.get("hypothesis") or ""
    for leader in summary.get("experiments", {}).get("leaders_by_ab_test") or []:
        groups = [g for g in summary["experiments"]["groups"] if g["ab_test_id"] == leader["ab_test_id"]]
        rates = sorted([g.get("completion_rate") for g in groups if g.get("completion_rate") is not None], reverse=True)
        if len(rates) >= 2 and rates[0] - rates[1] < min_delta:
            leader["interpretation"] = "inconclusive_delta_too_small"
        elif leader.get("caveat") == "low_sample":
            leader["interpretation"] = "directional_low_sample"
        else:
            leader["interpretation"] = "descriptive_leader_only"
        leader["decision"] = "inconclusive"
        leader["decision_authority"] = "context_only"
        leader["reason"] = (
            "reader_test_plan lacks a complete statistical decision protocol for allocation balance, "
            "cohort/window comparability, confidence intervals, and stopping rules"
        )
    summary["reader_test_plan"] = {
        "present": True,
        "path": plan_path,
        "scope": plan.get("scope"),
        "min_sample": plan.get("min_sample"),
        "min_completion_delta": min_delta,
        "retest_required_after_revision": (plan.get("retest_policy") or {}).get("required_after_revision", True),
    }
    return summary


def write_artifacts(root, records, summary):
    score_dir = os.path.join(root, "评分")
    os.makedirs(score_dir, exist_ok=True)
    raw_path = os.path.join(score_dir, "reader_telemetry.jsonl")
    summary_path = os.path.join(score_dir, "reader_telemetry_summary.json")
    md_path = os.path.join(score_dir, f"真实读者反馈_{date.today().isoformat()}.md")
    with open(raw_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 真实读者反馈 — {date.today().isoformat()}\n\n")
        f.write(f"- 平台/来源：{summary['platform']} / {summary['latest_source_name']}\n")
        f.write(f"- 记录数：{summary['records_ingested']}\n")
        agg = summary["aggregate"]
        f.write(f"- 总完读率：{agg['completion_rate'] if agg['completion_rate'] is not None else '—'}\n")
        f.write(f"- 总弃读率：{agg['drop_rate'] if agg['drop_rate'] is not None else '—'}\n")
        f.write(f"- 评论数：{agg['total_comments']}\n\n")
        if summary["weakest_chapters"]:
            f.write("## 优先复核章节\n\n")
            for ch in summary["weakest_chapters"]:
                item = next(c for c in summary["chapters"] if c["chapter"] == ch)
                f.write(
                    f"- 第{ch:02d}章：完读 {item['completion_rate']} / 弃读 {item['drop_rate']} / "
                    f"评论 {item['comment_count']} / flags={','.join(item['flags'])}\n"
                )
        if summary.get("experiments", {}).get("groups"):
            f.write("\n## A/B 与版本归因\n\n")
            f.write("| experiment | variant | take_ids | 假设 | 开读 | 完读率 | 弃读率 | flags |\n")
            f.write("|---|---|---|---|---:|---:|---:|---|\n")
            for item in summary["experiments"]["groups"]:
                f.write(
                    f"| {item['ab_test_id']} | {item['variant_id']} | {', '.join(item['take_ids'])} | "
                    f"{item.get('planned_hypothesis', '')} | {item['starts']} | {item['completion_rate']} | "
                    f"{item['drop_rate']} | {', '.join(item['flags'])} |\n"
                )
            if summary["experiments"].get("leaders_by_ab_test"):
                f.write("\n### 描述性领先版本（不判胜负）\n\n")
                for item in summary["experiments"]["leaders_by_ab_test"]:
                    f.write(
                        f"- {item['ab_test_id']}：leader={item['leader_variant_id']}，interpretation="
                        f"{item.get('interpretation', 'descriptive_leader_only')}，decision=inconclusive，"
                        f"caveat={item.get('caveat', '')}\n"
                    )
        f.write("\n## 章节明细\n\n")
        f.write("| 章节 | 开读 | 完读 | 弃读 | 完读率 | 弃读率 | 负评 | flags |\n")
        f.write("|---|---:|---:|---:|---:|---:|---:|---|\n")
        for item in summary["chapters"]:
            f.write(
                f"| 第{item['chapter']:02d}章 | {item['starts']} | {item['completes']} | {item['drops']} | "
                f"{item['completion_rate']} | {item['drop_rate']} | {item['negative_comments']} | "
                f"{', '.join(item['flags'])} |\n"
            )
    return raw_path, summary_path, md_path


def main():
    ap = argparse.ArgumentParser(description="导入真实读者反馈/留存数据")
    ap.add_argument("project_root")
    ap.add_argument("--input", required=True, action="append", help="CSV 或 JSONL，可重复")
    ap.add_argument("--platform", default="未注明平台")
    ap.add_argument("--source-name", default="未命名反馈批次")
    ap.add_argument("--append", action="store_true", help="保留既有 reader_telemetry.jsonl 并追加新批次")
    ap.add_argument("--min-sample", type=int, default=20)
    ap.add_argument("--low-completion", type=float, default=0.55)
    ap.add_argument("--high-drop", type=float, default=0.35)
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    raw_path = os.path.join(root, "评分", "reader_telemetry.jsonl")
    records = load_existing_jsonl(raw_path) if args.append else []
    imported = 0
    for input_path in args.input:
        rows = read_input(input_path)
        new_records = normalize_rows(
            rows,
            input_path=input_path,
            source_name=args.source_name,
            platform=args.platform,
        )
        records.extend(new_records)
        imported += len(new_records)
    summary = build_summary(
        records,
        platform=args.platform,
        source_name=args.source_name,
        min_sample=args.min_sample,
        low_completion=args.low_completion,
        high_drop=args.high_drop,
    )
    summary = apply_reader_test_plan(root, summary)
    raw_path, summary_path, md_path = write_artifacts(root, records, summary)
    print(f"[ok] 新导入 {imported} 条，累计 {len(records)} 条")
    print(f"[ok] telemetry JSONL → {raw_path}")
    print(f"[ok] summary JSON    → {summary_path}")
    print(f"[ok] feedback MD     → {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
