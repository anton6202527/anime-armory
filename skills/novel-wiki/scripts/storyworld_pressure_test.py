#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pre-draft storyworld pressure test for long-form novel projects.

判定分两层（诚实分层，防"关键词空壳全 pass"）：
- 本脚本是**结构化实质检查**（structural）：不再只看"文件填没填/长度够不够"，而是
  逐角色核对目标、数规则词多样性、数时间线事件、查契约必备信号、算章纲冲突覆盖率。
  仍是确定性脚本，能挡住"塞满关键词的空壳设定"里最粗的一层，但判不了语义自洽。
- "设定是否真能约束写作/是否自洽/有没有想象力支点"是语义判断——用
  `--register-semantic-job` 登记一个 `语义任务/` 复核 job 交 LLM 人判（分层与
  novel-score 的评估任务一致）；不注册时报告的 `semantic_followup` 也会列出建议人判的轴。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "novel", "_lib"))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from consistency_scaffold import resolve_character_card  # noqa: E402  同认 角色卡.md / 人物.md

_CRAFT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "novel-craft", "scripts"))


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
# 读者契约的必备信号（对应 novel-craft/references/reader-contract.md 模板要素）：
# 至少命中 2 类才算结构成立——单靠字数达标的空段落过不了。
CONTRACT_SIGNAL_GROUPS = {
    "题旨/核心问题": ("题旨", "核心戏剧问题", "核心问题", "主题"),
    "读者承诺": ("承诺", "爽点", "兑现", "好看机制"),
    "禁偏/边界": ("禁", "不许", "红线", "边界", "禁忌"),
}


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


def count_distinct(text, words):
    return sum(1 for word in words if word in (text or ""))


def character_blocks(text):
    """按 ##+ 标题切角色块，返回 [(名字, 块内容)]。"""
    blocks = []
    parts = re.split(r"(?m)^(#{2,6}\s+.+)$", text or "")
    for i in range(1, len(parts) - 1, 2):
        name = re.sub(r"^#{2,6}\s+", "", parts[i]).strip()
        blocks.append((name, parts[i + 1]))
    return blocks


def timeline_event_count(timeline_md, timeline_json):
    """数时间线里可辨认的事件条目（JSON events 优先；MD 按行/句切）。"""
    if isinstance(timeline_json, dict):
        events = timeline_json.get("events")
        if isinstance(events, list) and events:
            return len(events)
    segments = []
    for line in (timeline_md or "").splitlines():
        segments.extend(s.strip() for s in re.split(r"[。；;]", line))
    return sum(1 for s in segments if len(s) >= 5)


def outline_conflict_coverage(outline):
    """逐章行里含冲突/代价/钩子词的占比（0-1）；无逐章行返回 0。"""
    chapter_lines = [ln for ln in (outline or "").splitlines() if re.search(r"第\s*\d+\s*章", ln)]
    if not chapter_lines:
        return 0.0, 0
    hits = sum(1 for ln in chapter_lines if has_any(ln, CONFLICT_WORDS + ("钩子", "悬念")))
    return hits / len(chapter_lines), len(chapter_lines)


def axis(name, status, evidence, recommendation):
    return {
        "axis": name,
        "status": status,
        "evidence": evidence,
        "recommendation": recommendation,
    }


def pressure_test(root):
    paths = {key: os.path.join(root, rel) for key, rel in SETTING_FILES.items()}
    paths["characters"] = resolve_character_card(root) or paths["characters"]  # 兼容派生线 人物.md
    characters = read_text(paths["characters"])
    world = read_text(paths["world"])
    outline = read_text(paths["outline"])
    contract = read_text(paths["reader_contract"])
    timeline = read_text(paths["timeline_md"]) or json.dumps(load_json(paths["timeline_json"]) or {}, ensure_ascii=False)
    power = load_json(paths["power"])

    chapters = chapter_count(outline)
    axes = []

    # 逐角色核对：不再"全文任意位置出现一个目标词就 pass"——数出**带目标的角色块**。
    blocks = character_blocks(characters)
    blocks_with_goal = [name for name, body in blocks if has_any(body, GOAL_WORDS)]
    axes.append(axis(
        "character_agency",
        "pass" if len(blocks) >= 3 and len(blocks_with_goal) >= 2 else "risk",
        {"character_block_count": len(blocks),
         "blocks_with_goal": blocks_with_goal[:10],
         "blocks_without_goal": [n for n, b in blocks if not has_any(b, GOAL_WORDS)][:10]},
        "角色卡至少列主角/关键对手/关键关系人，且每个关键角色块内写明目标、恐惧、底线与变化弧（不是全文提一次就算）。",
    ))
    rule_word_variety = count_distinct(world, WORLD_RULE_WORDS)
    axes.append(axis(
        "world_rules",
        "pass" if rule_word_variety >= 2 else "risk",
        {"rule_word_variety": rule_word_variety, "world_chars": len(world)},
        "世界观必须写清硬规则、代价、限制和不可越界项（至少两类：规则本体 + 违反的代价），否则长篇会靠临场补丁推进。",
    ))
    axes.append(axis(
        "geography_and_factions",
        "pass" if has_any(world + characters, GEOGRAPHY_WORDS) else "risk",
        {"has_geography_words": has_any(world + characters, GEOGRAPHY_WORDS)},
        "补地点/势力/行动半径，避免角色瞬移、势力边界模糊和场景重复。",
    ))
    event_count = timeline_event_count(timeline, load_json(paths["timeline_json"]))
    axes.append(axis(
        "timeline_causality",
        "pass" if event_count >= 3 else "risk",
        {"timeline_event_count": event_count},
        "补时间线或事件顺序表（至少 3 个可辨认事件）：开局前史、当前卷关键节点、伏笔回收窗口。",
    ))
    conflict_ratio, chapter_lines = outline_conflict_coverage(outline)
    axes.append(axis(
        "outline_pressure",
        "pass" if chapters >= 5 and conflict_ratio >= 0.3 else "risk",
        {"chapter_count_detected": chapters, "chapter_lines": chapter_lines,
         "conflict_coverage_ratio": round(conflict_ratio, 2)},
        "章纲不只列事件：至少 30% 的逐章条目要标冲突、失败代价、章末钩子或读者承诺推进（当前覆盖率见 evidence）。",
    ))
    contract_signals = [name for name, words in CONTRACT_SIGNAL_GROUPS.items() if has_any(contract, words)]
    axes.append(axis(
        "reader_contract",
        "pass" if len(contract.strip()) >= 30 and len(contract_signals) >= 2 else "risk",
        {"reader_contract_chars": len(contract.strip()), "signals_present": contract_signals},
        "补读者契约：题旨/核心戏剧问题、读者承诺/好看机制、禁偏清单至少写两类，用于后续 sentry（凑字数的空段落过不了）。",
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
        "schema_version": 2,
        "kind": "novel_storyworld_pressure_test",
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "check_depth": "structural",  # 结构化实质检查；语义自洽仍需 LLM 人判（见 semantic_followup）
        "verdict": verdict,
        "risk_axes": risk_axes,
        "review_axes": review_axes,
        "axes": axes,
        "semantic_followup": {
            "note": "本报告只证明设定的结构成立；『规则是否自洽、目标是否互相挤压出戏、设定有没有想象力支点』需 LLM 复核。",
            "register_command": "python3 skills/novel-wiki/scripts/storyworld_pressure_test.py <作品根> --register-semantic-job",
            "axes_needing_semantic_review": [
                "world_rules（规则之间是否互相矛盾/有无代价闭环）",
                "character_agency（角色目标是否互相挤压出冲突，还是各自独立不相干）",
                "reader_contract（承诺是否可被前 10 章兑现）",
                "novelty_anchor（设定里有没有可转述传播的想象力支点——结构检查判不了）",
            ],
        },
        "next_actions": [
            {
                "recommended_skill": "novel-craft",
                "return_to_stage": "setting",
                "action": "补齐 storyworld_pressure_test 标记为 risk 的设定项，再生成正式写作任务包。",
            }
        ] if risk_axes else [],
    }


def register_semantic_job(root, report):
    """把语义复核登记成 语义任务/ job（与 score 评估任务同一分层机制）。优雅降级：craft 缺失只提示。"""
    if _CRAFT not in sys.path:
        sys.path.insert(0, _CRAFT)
    try:
        import semantic_job
    except ImportError:
        print("[warn] 找不到 novel-craft/scripts/semantic_job.py，跳过语义任务登记。", file=sys.stderr)
        return None
    setting_excerpts = []
    for key in ("characters", "world", "outline", "reader_contract"):
        path = os.path.join(root, SETTING_FILES[key]) if key != "characters" else (resolve_character_card(root) or os.path.join(root, SETTING_FILES[key]))
        text = read_text(path)
        if text:
            setting_excerpts.append(f"## {os.path.basename(path)}\n{text[:3000]}")
    prompt = (
        "# Storyworld 语义压力复核\n\n"
        "结构化检查已通过/出具（见 审稿/storyworld_pressure_test.json），请对下列设定做**语义级**判定，"
        "逐项回答并给证据：\n"
        "1. world_rules：世界规则之间是否自洽？每条硬规则有没有违反的代价闭环？\n"
        "2. character_agency：主要角色的目标是否互相挤压（天然生成冲突），还是各自独立不相干？\n"
        "3. reader_contract：读者承诺能否被前 10 章兑现？有没有承诺了但设定支撑不了的项？\n"
        "4. novelty_anchor：设定里有没有可被读者一句话转述传播的想象力支点？没有的话，最接近的候选是什么？\n\n"
        "输出 JSON：{\"verdict\": \"pass|revise_setting\", \"findings\": [{\"axis\":..., \"ok\": bool, "
        "\"evidence\":..., \"fix\":...}]}\n\n" + "\n\n".join(setting_excerpts)
    )
    job = semantic_job.create_job(
        root,
        semantic_kind="storyworld_semantic_review",
        prompt=prompt,
        response_out=os.path.join("审稿", "storyworld_semantic_review.json"),
        required_fields=["verdict", "findings"],
    )
    return job


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
    ap.add_argument("--register-semantic-job", action="store_true",
                    help="登记 语义任务/storyworld_semantic_review job，交 LLM 做语义级复核（规则自洽/目标挤压/承诺可兑现/想象力支点）")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = pressure_test(root)
    json_path, md_path = write_artifacts(root, report)
    if args.register_semantic_job:
        job = register_semantic_job(root, report)
        if job:
            print(f"[ok] 语义复核任务已登记 → 语义任务/{job.get('job_id')}.json")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[ok] storyworld pressure JSON → {json_path}")
        print(f"[ok] storyworld pressure MD   → {md_path}")
        print(f"     verdict: {report['verdict']} | risk_axes: {', '.join(report['risk_axes']) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
