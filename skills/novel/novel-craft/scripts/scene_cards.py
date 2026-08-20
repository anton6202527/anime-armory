#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Scaffold and check novel scene cards.

Scene cards are deterministic planning artifacts. The script never writes
prose; it creates placeholders and validates whether each scene has enough
dramatic function to guide drafting/editing.
"""
import argparse
import json
import os
import re
import sys
from datetime import date


_HERE = os.path.dirname(os.path.abspath(__file__))
_NOVEL_LIB = os.path.abspath(os.path.join(_HERE, "..", "..", "_lib"))
if _NOVEL_LIB not in sys.path:
    sys.path.insert(0, _NOVEL_LIB)
from craft_profile import (  # noqa: E402
    CORE_SCENE_FIELDS,
    NARRATIVE_FUNCTION_FIELDS,
    TRADITIONAL_SCENE_FIELDS,
    is_supported_craft_profile,
    missing_literary_dynamics,
    missing_required_scene_fields,
    narrative_functions,
    requires_traditional_turn,
    resolve_craft_profile,
)
from project_io import load_project_settings  # noqa: E402

# Backward-compatible public constant: the default/legacy `genre_novel`
# contract still requires the complete traditional field set.
REQUIRED_FIELDS = CORE_SCENE_FIELDS + TRADITIONAL_SCENE_FIELDS
OPTIONAL_FIELDS = ("location", "time", "reveal_or_payoff", "subtext", "sensory_anchor",
                   "outcome", "plotline", "turn_source")
# 场景结局极性（Swain/Sanderson try-fail 循环）：yes=达成、yes-but=达成但付代价、
# no-and=失败且恶化、no-but=失败但有转机。中段应以 yes-but / no-and 为主——
# 连胜无代价 = 张力自由落体（manuscript_map 的 OUTCOME-* 检测消费此字段）。
OUTCOME_VALUES = ("yes", "yes-but", "no-and", "no-but")
# 转折的能动性来源（Pixar 第 19 条巧合纪律：巧合可以把人物**推进**麻烦，不可以把人物
# **捞出**麻烦）。"伏笔兑现"指转折由前文已埋伏笔触发（≠巧合）；"巧合"+有利 outcome
# 会被 manuscript_map 的 TURN-COINCIDENCE-RESCUE 提示。留空=不判定。
TURN_SOURCE_VALUES = ("主角行动", "对手行动", "盟友援手", "伏笔兑现", "巧合")
CHARACTER_ENGINE_FIELDS = (
    "want",
    "need",
    "misbelief",
    "wound",
    "fear",
    "tactic",
    "moral_boundary",
    "choice_cost",
)
CHAPTER_RE = re.compile(r"第\s*0*(\d+)\s*章\s*(?:[《<]([^》>]+)[》>])?\s*(?:[—-]\s*(.*))?")


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def scene_path(root):
    return os.path.join(root, "设定", "scene_cards.json")


def parse_range(value):
    if not value:
        return None
    m = re.fullmatch(r"(\d+)-(\d+)", value)
    if not m:
        raise SystemExit("--range 格式应为 1-5")
    start, end = int(m.group(1)), int(m.group(2))
    if start > end:
        start, end = end, start
    return start, end


def parse_outline(root):
    path = os.path.join(root, "设定", "章纲.md")
    outline = {}
    if not os.path.exists(path):
        return outline
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw in f:
            m = CHAPTER_RE.search(raw)
            if not m:
                continue
            chapter = int(m.group(1))
            outline[chapter] = {
                "title": (m.group(2) or "").strip(),
                "beat": (m.group(3) or raw.strip()).strip(),
                "raw": raw.strip(),
            }
    return outline


def empty_card(chapter, scene_no, outline_item):
    return {
        "id": f"SC{chapter:03d}-{scene_no:02d}",
        "chapter": chapter,
        "scene_no": scene_no,
        "source_outline": outline_item.get("raw") or outline_item.get("beat") or "",
        "pov": "",
        # 比角色 POV 更宽的叙述归属：全知叙述者、群体合唱、镜头式观察、游移视角等。
        # literary 可用 viewpoint 替代 pov；experimental 两者都不作硬前置。
        "viewpoint": "",
        "location": "",
        "time": "",
        "desire": "",
        "obstacle": "",
        "conflict": "",
        "turn": "",
        "value_shift": "",
        # 文学/实验档可用这些明确登记的叙事功能替代传统 turn/value_shift；商业/类型档
        # 仍须填写传统字段。字段留空不代表失败，具体要求由项目 `创作工艺档` 决定。
        "revelation": "",
        "relation_drift": "",
        "perceptual_shift": "",
        "motif_return": "",
        "deliberate_stasis": "",
        # Sequel 半拍（Swain Scene-Sequel）：turn 之后 POV 的 反应→两难→决定。
        # 传统手艺：高压场景后必须给情绪落地拍，否则读者疲劳（连打不喘=麻木）；
        # 不必每场都填——衔接下一场即高压续压时留空即合法，连续多章全空才会被
        # manuscript_map 的 sequel gap 检测提示。
        "aftermath": "",
        # 场景结局极性（try-fail 循环）：yes / yes-but（达成但付代价）/ no-and（失败且
        # 恶化）/ no-but（失败但有转机）；中段应以 yes-but、no-and 为主，留空=不判定。
        "outcome": "",
        # 本场所属情节线自由标签（主线/某支线名）；连续同线过长会被"横云断山"检测提示。
        "plotline": "",
        # 转折能动性来源（Pixar 巧合纪律）：主角行动/对手行动/盟友援手/伏笔兑现/巧合；
        # "巧合"+有利结局会被巧合救场检测提示。留空=不判定。
        "turn_source": "",
        "reveal_or_payoff": "",
        "subtext": "",
        "sensory_anchor": "",
        "want": "",
        "need": "",
        "misbelief": "",
        "wound": "",
        "fear": "",
        "tactic": "",
        "moral_boundary": "",
        "choice_cost": "",
    }


def scaffold(root, chapters=None, scenes_per_chapter=1, force=False):
    path = scene_path(root)
    data = load_json(path, {}) or {}
    if data.get("kind") != "novel_scene_cards":
        data = {
            "schema_version": 1,
            "kind": "novel_scene_cards",
            "updated_at": date.today().isoformat(),
            "scenes": [],
        }
    outline = parse_outline(root)
    if chapters is None:
        chapters = sorted(outline) or [1]
    existing_ids = {s.get("id") for s in data.get("scenes") or [] if isinstance(s, dict)}
    new_scenes = []
    for chapter in chapters:
        outline_item = outline.get(chapter, {"raw": "", "beat": ""})
        for scene_no in range(1, scenes_per_chapter + 1):
            card = empty_card(chapter, scene_no, outline_item)
            if card["id"] in existing_ids and not force:
                continue
            if force:
                data["scenes"] = [s for s in data.get("scenes", []) if s.get("id") != card["id"]]
            new_scenes.append(card)
    data.setdefault("scenes", []).extend(new_scenes)
    data["updated_at"] = date.today().isoformat()
    data["scenes"].sort(key=lambda s: (int(s.get("chapter") or 0), int(s.get("scene_no") or 0), s.get("id") or ""))
    write_json(path, data)
    return path, len(new_scenes)


def check(root, chapter=None):
    data = load_json(scene_path(root), {}) or {}
    craft_profile = resolve_craft_profile(load_project_settings(root))
    findings = []
    profile_supported = is_supported_craft_profile(craft_profile)
    if not profile_supported:
        findings.append({
            "id": "SCENE-CARD-CRAFT-PROFILE-UNSUPPORTED",
            "severity": "blocking",
            "confidence": "contract",
            "reason": (
                f"创作工艺档={craft_profile} 尚无结构检查适配；请改用 commercial_serial / "
                "genre_novel / literary / experimental，或先为该自定义档补适配规则。"
            ),
        })
    if data.get("kind") != "novel_scene_cards":
        findings.append({
            "id": "SCENE-CARDS-MISSING",
            "severity": "warning",
            "reason": "缺少 设定/scene_cards.json；可先 scaffold，再由 AI/人工补字段。",
        })
        return {
            "schema_version": 1,
            "kind": "novel_scene_card_check",
            "craft_profile": craft_profile,
            "exists": False,
            "blocking": sum(1 for f in findings if f["severity"] == "blocking"),
            "warnings": sum(1 for f in findings if f["severity"] != "blocking"),
            "findings": findings,
        }
    scenes = [s for s in data.get("scenes") or [] if isinstance(s, dict)]
    if chapter is not None:
        scenes = [s for s in scenes if int(s.get("chapter") or 0) == chapter]
    if chapter is not None and not scenes:
        findings.append({
            "id": "SCENE-CARD-CHAPTER-MISSING",
            "severity": "warning",
            "chapter": chapter,
            "reason": f"第{chapter:02d}章没有 scene card。",
        })
    for scene in scenes:
        missing = missing_required_scene_fields(scene, craft_profile) if profile_supported else []
        if missing:
            findings.append({
                "id": "SCENE-CARD-MISSING-FIELDS",
                "severity": "blocking",
                "confidence": "contract",
                "chapter": scene.get("chapter"),
                "scene_id": scene.get("id"),
                "reason": f"创作工艺档={craft_profile} 缺少契约字段：" + "、".join(missing),
            })
        literary_missing = missing_literary_dynamics(scene, craft_profile) if profile_supported else []
        if literary_missing:
            findings.append({
                "id": "SCENE-CARD-LITERARY-DYNAMICS-OMITTED",
                "severity": "warning",
                "confidence": "heuristic",
                "chapter": scene.get("chapter"),
                "scene_id": scene.get("id"),
                "reason": (
                    "文学档未登记常规动力字段：" + "、".join(literary_missing)
                    + "。意象段、意识流、关系微移或有意停滞可以合法省略；仅请人工确认不是无意漏填。"
                ),
            })
        if profile_supported and not requires_traditional_turn(craft_profile) and not narrative_functions(scene):
            findings.append({
                "id": "SCENE-CARD-NARRATIVE-FUNCTION-MISSING",
                "severity": "warning",
                "confidence": "heuristic",
                "chapter": scene.get("chapter"),
                "scene_id": scene.get("id"),
                "reason": (
                    f"创作工艺档={craft_profile} 未登记任何叙事功能；可按实际场景填写 "
                    + " / ".join(NARRATIVE_FUNCTION_FIELDS)
                    + " 中至少一项。该判断需人工结合语境复核，不硬阻断。"
                ),
            })
        weak = [field for field in OPTIONAL_FIELDS if not str(scene.get(field) or "").strip()]
        if weak:
            findings.append({
                "id": "SCENE-CARD-WEAK-FIELDS",
                "severity": "warning",
                "chapter": scene.get("chapter"),
                "scene_id": scene.get("id"),
                "reason": "建议补字段：" + "、".join(weak),
            })
        outcome = str(scene.get("outcome") or "").strip()
        if outcome and outcome not in OUTCOME_VALUES:
            findings.append({
                "id": "SCENE-CARD-OUTCOME-INVALID",
                "severity": "warning",
                "chapter": scene.get("chapter"),
                "scene_id": scene.get("id"),
                "reason": f"outcome=「{outcome}」不在枚举 {'/'.join(OUTCOME_VALUES)} 内；"
                          "留空=不判定，填了就要可机读（try-fail 检测靠它）。",
            })
        turn_source = str(scene.get("turn_source") or "").strip()
        if turn_source and turn_source not in TURN_SOURCE_VALUES:
            findings.append({
                "id": "SCENE-CARD-TURN-SOURCE-INVALID",
                "severity": "warning",
                "chapter": scene.get("chapter"),
                "scene_id": scene.get("id"),
                "reason": f"turn_source=「{turn_source}」不在枚举 {'/'.join(TURN_SOURCE_VALUES)} 内；"
                          "留空=不判定，填了就要可机读（巧合救场检测靠它）。",
            })
        character_missing = [field for field in CHARACTER_ENGINE_FIELDS if not str(scene.get(field) or "").strip()]
        if character_missing:
            findings.append({
                "id": "SCENE-CARD-CHARACTER-ENGINE-MISSING",
                "severity": "warning",
                "chapter": scene.get("chapter"),
                "scene_id": scene.get("id"),
                "reason": "人物内驱字段建议补齐：" + "、".join(character_missing),
            })
    return {
        "schema_version": 1,
        "kind": "novel_scene_card_check",
        "craft_profile": craft_profile,
        "exists": True,
        "blocking": sum(1 for f in findings if f["severity"] == "blocking"),
        "warnings": sum(1 for f in findings if f["severity"] != "blocking"),
        "findings": findings,
    }


def main():
    ap = argparse.ArgumentParser(description="scaffold/check novel scene cards")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scaffold")
    sc.add_argument("project_root")
    sc.add_argument("--range")
    sc.add_argument("--scenes-per-chapter", type=int, default=1)
    sc.add_argument("--force", action="store_true")
    ck = sub.add_parser("check")
    ck.add_argument("project_root")
    ck.add_argument("--chapter", type=int)
    ck.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = os.path.abspath(args.project_root)
    if args.cmd == "scaffold":
        rng = parse_range(args.range)
        chapters = list(range(rng[0], rng[1] + 1)) if rng else None
        path, count = scaffold(root, chapters=chapters, scenes_per_chapter=max(1, args.scenes_per_chapter), force=args.force)
        print(f"[ok] scene cards: {path} (+{count})")
        return
    result = check(root, chapter=args.chapter)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[summary] blocking={result['blocking']} warnings={result['warnings']}")
        for item in result["findings"]:
            print(f"- {item['severity']} {item['id']}: {item['reason']}")
    raise SystemExit(1 if result["blocking"] else 0)


if __name__ == "__main__":
    main()
