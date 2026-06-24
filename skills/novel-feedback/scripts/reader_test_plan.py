#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a reader test plan before ingesting real reader telemetry."""
import argparse
import json
import os
from datetime import date


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def default_questions():
    return [
        "读到哪里最想停下？为什么？",
        "前三章里最想追看的悬念是什么？",
        "主角是否有明确目标和行动力？",
        "哪一场戏最有记忆点？",
        "是否出现套路疲劳、看不懂或不信服的地方？",
    ]


def build_plan(args):
    metrics = [
        {"name": "completion_rate", "target": args.min_completion, "direction": "higher_is_better"},
        {"name": "drop_rate", "target": args.max_drop, "direction": "lower_is_better"},
        {"name": "comment_negative_rate", "target": 0.25, "direction": "lower_is_better"},
    ]
    variants = []
    for idx, take in enumerate(args.take or ["take-a"], 1):
        variants.append({
            "variant_id": chr(ord("A") + idx - 1),
            "take_id": take,
            "hypothesis": "待填写：这个版本要验证什么",
        })
    return {
        "schema_version": 1,
        "kind": "novel_reader_test_plan",
        "project_root": os.path.abspath(args.project_root),
        "generated_at": date.today().isoformat(),
        "platform": args.platform,
        "source_name": args.source_name,
        "scope": args.scope,
        "target_reader": args.target_reader,
        "min_sample": args.min_sample,
        "variants": variants,
        "metrics": metrics,
        "questions": args.question or default_questions(),
        "decision_rules": [
            f"样本量低于 {args.min_sample} 时只作方向性参考，不做 kill/go 决策。",
            "真实反馈优先于模拟读者；若与 novel-simulate 冲突，以真实完读/弃读为准。",
            "A/B 只在同一 ab_test_id 内比较，必须带 take_id 才能归因到具体稿件版本。",
        ],
    }


def write_markdown(path, plan):
    lines = [
        "# 读者测试计划",
        "",
        f"- 平台/来源：{plan['platform']} / {plan['source_name']}",
        f"- 测试范围：{plan['scope']}",
        f"- 目标读者：{plan['target_reader']}",
        f"- 最小样本量：{plan['min_sample']}",
        "",
        "## 版本",
    ]
    for item in plan["variants"]:
        lines.append(f"- {item['variant_id']}：{item['take_id']} — {item['hypothesis']}")
    lines.extend(["", "## 指标"])
    for item in plan["metrics"]:
        lines.append(f"- {item['name']}：目标 {item['target']} ({item['direction']})")
    lines.extend(["", "## 问题"])
    for q in plan["questions"]:
        lines.append(f"- {q}")
    lines.extend(["", "## 判读规则"])
    for rule in plan["decision_rules"]:
        lines.append(f"- {rule}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


def main():
    ap = argparse.ArgumentParser(description="生成真实读者测试计划")
    ap.add_argument("project_root")
    ap.add_argument("--platform", default="内测")
    ap.add_argument("--source-name", default="未命名测试")
    ap.add_argument("--scope", default="opening:1-3")
    ap.add_argument("--target-reader", default="目标平台核心读者")
    ap.add_argument("--min-sample", type=int, default=30)
    ap.add_argument("--min-completion", type=float, default=0.65)
    ap.add_argument("--max-drop", type=float, default=0.25)
    ap.add_argument("--take", action="append", help="测试版本 take_id，可重复")
    ap.add_argument("--question", action="append", help="追加/覆盖测试问题，可重复")
    args = ap.parse_args()
    plan = build_plan(args)
    score_dir = os.path.join(os.path.abspath(args.project_root), "评分")
    json_path = os.path.join(score_dir, "reader_test_plan.json")
    md_path = os.path.join(score_dir, "读者测试计划.md")
    write_json(json_path, plan)
    write_markdown(md_path, plan)
    print(f"[ok] reader test plan: {md_path}")


if __name__ == "__main__":
    main()
