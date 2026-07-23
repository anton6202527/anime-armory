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
from datetime import date


REQUIRED_FIELDS = ("pov", "desire", "obstacle", "conflict", "turn", "value_shift")
OPTIONAL_FIELDS = ("location", "time", "reveal_or_payoff", "subtext", "sensory_anchor",
                   "outcome", "plotline")
# 场景结局极性（Swain/Sanderson try-fail 循环）：yes=达成、yes-but=达成但付代价、
# no-and=失败且恶化、no-but=失败但有转机。中段应以 yes-but / no-and 为主——
# 连胜无代价 = 张力自由落体（manuscript_map 的 OUTCOME-* 检测消费此字段）。
OUTCOME_VALUES = ("yes", "yes-but", "no-and", "no-but")
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
        "location": "",
        "time": "",
        "desire": "",
        "obstacle": "",
        "conflict": "",
        "turn": "",
        "value_shift": "",
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
    findings = []
    if data.get("kind") != "novel_scene_cards":
        return {
            "schema_version": 1,
            "kind": "novel_scene_card_check",
            "exists": False,
            "blocking": 0,
            "warnings": 0,
            "findings": [{
                "id": "SCENE-CARDS-MISSING",
                "severity": "warning",
                "reason": "缺少 设定/scene_cards.json；可先 scaffold，再由 AI/人工补字段。",
            }],
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
        missing = [field for field in REQUIRED_FIELDS if not str(scene.get(field) or "").strip()]
        if missing:
            findings.append({
                "id": "SCENE-CARD-MISSING-FIELDS",
                "severity": "blocking",
                "chapter": scene.get("chapter"),
                "scene_id": scene.get("id"),
                "reason": "缺少关键字段：" + "、".join(missing),
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
