#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-draft storyworld pressure test for long-form novel projects."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date


SETTING_FILES = {
    "characters": os.path.join("设定", "角色卡.md"),
    "world": os.path.join("设定", "世界观.md"),
    "outline": os.path.join("设定", "章纲.md"),
    "reader_contract": os.path.join("设定", "读者契约.md"),
    "timeline_md": os.path.join("设定", "时间线.md"),
    "timeline_json": os.path.join("设定", "timeline.json"),
    "power": os.path.join("设定", "power_system_registry.json"),
}

WORLD_RULE_WORDS = ("规则", "限制", "代价", "禁忌", "边界", "不能", "成本")
GEOGRAPHY_WORDS = ("地图", "地理", "地点", "城", "州", "国", "宗门", "势力", "区域")
CONFLICT_WORDS = ("冲突", "阻碍", "代价", "失败", "反派", "追杀", "危机", "抉择", "背叛")
GOAL_WORDS = ("目标", "欲望", "动机", "想要", "执念", "恐惧")


def read_text(path):
    if not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def count_headings(text):
    return len(re.findall(r"(?m)^#{2,6}\s+|\n[-*]\s*(?:角色|人物|主角|配角)[:：]", text or ""))


def chapter_count(outline):
    nums = {int(m.group(1)) for m in re.finditer(r"第\s*(\d+)\s*章", outline or "")}
    return len(nums)


def has_any(text, words):
    return any(word in (text or "") for word in words)


def axis(name, status, evidence, recommendation):
    return {
        "axis": name,
        "status": status,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def pressure_test(root):
    paths = {key: os.path.join(root, rel) for key, rel in SETTING_FILES.items()}
    characters = read_text(paths["characters"])
    world = read_text(paths["world"])
    outline = read_text(paths["outline"])
    contract = read_text(paths["reader_contract"])
    timeline = read_text(paths["timeline_md"]) or json.dumps(load_json(paths["timeline_json"]) or {}, ensure_ascii=False)
    power = load_json(paths["power"])

    char_count = count_headings(characters)
    chapters = chapter_count(outline)
    axes = []

    axes.append(axis(
        "character_agency",
        "pass" if char_count >= 3 and has_any(characters, GOAL_WORDS) else "risk",
        {"character_heading_count": char_count, "has_goal_words": has_any(characters, GOAL_WORDS)},
        "角色卡至少列主角/关键对手/关键关系人，并写目标、恐惧、底线与变化弧。",
    ))
    axes.append(axis(
        "world_rules",
        "pass" if has_any(world, WORLD_RULE_WORDS) else "risk",
        {"has_rule_words": has_any(world, WORLD_RULE_WORDS), "world_chars": len(world)},
        "世界观必须写清硬规则、代价、限制和不可越界项，否则长篇会靠临场补丁推进。",
    ))
    axes.append(axis(
        "geography_and_factions",
        "pass" if has_any(world + characters, GEOGRAPHY_WORDS) else "risk",
        {"has_geography_words": has_any(world + characters, GEOGRAPHY_WORDS)},
        "补地点/势力/行动半径，避免角色瞬移、势力边界模糊和场景重复。",
    ))
    axes.append(axis(
        "timeline_causality",
        "pass" if len(timeline.strip()) >= 30 else "risk",
        {"timeline_chars": len(timeline.strip())},
        "补时间线或事件顺序表，至少覆盖开局前史、当前卷关键节点、伏笔回收窗口。",
    ))
    axes.append(axis(
        "outline_pressure",
        "pass" if chapters >= 5 and has_any(outline, CONFLICT_WORDS) else "risk",
        {"chapter_count_detected": chapters, "has_conflict_words": has_any(outline, CONFLICT_WORDS)},
        "章纲不只列事件，还要标每章冲突、失败代价、章末钩子和读者承诺推进。",
    ))
    axes.append(axis(
        "reader_contract",
        "pass" if len(contract.strip()) >= 30 else "risk",
        {"reader_contract_chars": len(contract.strip())},
        "补读者契约：核心爽感/情绪承诺/题旨推进/禁忌体验，用于后续 sentry。",
    ))
    axes.append(axis(
        "power_progression",
        "pass" if isinstance(power, dict) and (power.get("levels") or power.get("progression") or power.get("systems")) else "review",
        {"power_registry_exists": isinstance(power, dict), "keys": sorted(power.keys())[:10] if isinstance(power, dict) else []},
        "系统流/修仙/战力文应先补 power_system_registry；非战力文可保留 review。",
    ))

    risk_axes = [item["axis"] for item in axes if item["status"] == "risk"]
    review_axes = [item["axis"] for item in axes if item["status"] == "review"]
    verdict = "pass"
    if len(risk_axes) >= 3:
        verdict = "block_pre_draft"
    elif risk_axes:
        verdict = "revise_setting"
    elif review_axes:
        verdict = "pass_with_review"

    return {
        "schema_version": 1,
        "kind": "novel_storyworld_pressure_test",
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "verdict": verdict,
        "risk_axes": risk_axes,
        "review_axes": review_axes,
        "axes": axes,
        "next_actions": [
            {
                "recommended_skill": "novel-craft",
                "return_to_stage": "setting",
                "action": "补齐 storyworld_pressure_test 标记为 risk 的设定项，再生成正式写作任务包。",
            }
        ] if risk_axes else [],
    }


def write_artifacts(root, report):
    out_dir = os.path.join(root, "审稿")
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, "storyworld_pressure_test.json")
    md_path = os.path.join(out_dir, f"storyworld_pressure_test_{date.today().isoformat()}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Storyworld Pressure Test — {date.today().isoformat()}\n\n")
        f.write(f"- verdict: **{report['verdict']}**\n")
        f.write(f"- risk_axes: {', '.join(report['risk_axes']) or 'none'}\n\n")
        f.write("| Axis | Status | Evidence | Recommendation |\n")
        f.write("|---|---|---|---|\n")
        for item in report["axes"]:
            f.write(
                f"| {item['axis']} | {item['status']} | "
                f"{json.dumps(item['evidence'], ensure_ascii=False)} | {item['recommendation']} |\n"
            )
    return json_path, md_path


def main():
    ap = argparse.ArgumentParser(description="长篇 storyworld 写前压力测试")
    ap.add_argument("project_root")
    ap.add_argument("--json", action="store_true", help="stdout 输出 JSON")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = pressure_test(root)
    json_path, md_path = write_artifacts(root, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[ok] storyworld pressure JSON → {json_path}")
        print(f"[ok] storyworld pressure MD   → {md_path}")
        print(f"     verdict: {report['verdict']} | risk_axes: {', '.join(report['risk_axes']) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
