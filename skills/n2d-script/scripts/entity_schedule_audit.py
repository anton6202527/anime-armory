#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""entity_schedule_audit.py — 逐镜头实体排程检查（EntityBench 轴）。

为什么存在：长篇视频的一致性不只看"这一镜画得像不像"，还要知道每个 shot/clip 应该出现谁、
哪些物件/地点必须存在、角色此刻知道什么。EntityBench 2026 的核心做法是 per-shot entity
schedule；本脚本把 n2d 的 storyboard.json 也收束到这个机器真值层。

字段约定（clip 级或 shots[] 级均可；shot 级覆盖 clip 级）：
  entity_schedule: {
    "characters": ["CHAR_01/常态", "CHAR_02"],
    "objects": ["PROP_玉佩"],
    "locations": ["LOC_冷宫"],
    "knowledge_state": {"CHAR_01": ["知道玉佩是假"]},
    "required_presence": ["CHAR_01", "PROP_玉佩"]
  }

report-only（默认 exit 0）；--strict 时 warn/block exit 1。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


CHAR_FIELD_KEYS = ("character_ids", "characters", "roles", "cast", "subjects", "人物", "角色")
OBJECT_FIELD_KEYS = ("object_ids", "objects", "props", "weapons", "assets", "道具", "物件")
LOCATION_FIELD_KEYS = ("location_id", "location_ids", "locations", "scene_id", "场景", "地点")
TEXT_FIELD_KEYS = ("description", "text", "summary", "action", "visual", "画面", "镜头")


def ep_label(value: str) -> str:
    return value if str(value).startswith("第") else f"第{value}集"


def _storyboard_path(root: str, ep: str) -> Path:
    return Path(root) / "脚本" / ep / "storyboard.json"


def _token(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("id", "asset_id", "character_id", "name", "label"):
            if str(value.get(key) or "").strip():
                return str(value.get(key)).strip()
        return ""
    return str(value or "").strip()


def _tokens(value: Any) -> Set[str]:
    if value is None:
        return set()
    if isinstance(value, Mapping):
        return {t for t in (_token(value),) if t}
    if isinstance(value, (list, tuple, set)):
        return {t for item in value for t in _tokens(item)}
    text = str(value).strip()
    if not text:
        return set()
    return {p.strip() for p in re.split(r"[,/、，；;]\s*", text) if p.strip()}


def _collect_fields(section: Mapping[str, Any], keys: Sequence[str]) -> Set[str]:
    out: Set[str] = set()
    for key in keys:
        out |= _tokens(section.get(key))
    return out


def _entity_schedule(section: Mapping[str, Any], fallback: Optional[Mapping[str, Any]] = None) -> Optional[Mapping[str, Any]]:
    own = section.get("entity_schedule") or section.get("实体排程")
    if isinstance(own, Mapping):
        return own
    return fallback if isinstance(fallback, Mapping) else None


def _required_presence(schedule: Mapping[str, Any]) -> Set[str]:
    req = schedule.get("required_presence") or schedule.get("must_present") or schedule.get("必须出现")
    if isinstance(req, Mapping):
        out: Set[str] = set()
        for value in req.values():
            out |= _tokens(value)
        return out
    return _tokens(req)


def _schedule_entities(schedule: Mapping[str, Any]) -> Dict[str, Set[str]]:
    chars = _collect_fields(schedule, ("characters", "character_ids", "角色"))
    objs = _collect_fields(schedule, ("objects", "object_ids", "props", "weapons", "道具", "物件"))
    locs = _collect_fields(schedule, ("locations", "location_ids", "scene_id", "场景", "地点"))
    return {"characters": chars, "objects": objs, "locations": locs,
            "required_presence": _required_presence(schedule)}


def _unit_text(section: Mapping[str, Any]) -> str:
    return " ".join(str(section.get(k) or "") for k in TEXT_FIELD_KEYS)


def _expected_entities(unit: Mapping[str, Any], parent: Mapping[str, Any]) -> Dict[str, Set[str]]:
    merged: Dict[str, Any] = {}
    merged.update(parent)
    merged.update(unit)
    return {
        "characters": _collect_fields(merged, CHAR_FIELD_KEYS),
        "objects": _collect_fields(merged, OBJECT_FIELD_KEYS),
        "locations": _collect_fields(merged, LOCATION_FIELD_KEYS),
    }


def _unit_id(clip: Mapping[str, Any], idx: int, shot: Optional[Mapping[str, Any]] = None, shot_idx: int = 0) -> str:
    cid = str(clip.get("id") or f"clip#{idx}").strip()
    if not shot:
        return cid
    sid = str(shot.get("id") or shot.get("shot") or shot.get("shot_id") or f"shot#{shot_idx}").strip()
    return f"{cid}/{sid}"


def iter_units(storyboard: Mapping[str, Any]) -> List[Tuple[str, Mapping[str, Any], Mapping[str, Any], Optional[Mapping[str, Any]]]]:
    """返回 (unit_id, unit, parent_clip, fallback_schedule)。纯结构展开。"""
    clips = storyboard.get("clips") or storyboard.get("shots") or []
    if not isinstance(clips, list):
        return []
    units: List[Tuple[str, Mapping[str, Any], Mapping[str, Any], Optional[Mapping[str, Any]]]] = []
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        fallback = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else None
        subshots = clip.get("shots")
        if isinstance(subshots, list) and subshots:
            for sidx, shot in enumerate(subshots, 1):
                if isinstance(shot, Mapping):
                    units.append((_unit_id(clip, idx, shot, sidx), shot, clip, fallback))
        else:
            units.append((_unit_id(clip, idx), clip, clip, fallback))
    return units


def audit_episode(root: str, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    path = _storyboard_path(root, ep)
    findings: List[Dict[str, Any]] = []
    if not path.exists():
        return {"episode": ep, "ok": False, "findings": [{
            "severity": "block", "code": "missing_storyboard",
            "message": f"缺 {path}，无法建立逐镜头实体排程。"
        }], "stats": {"units": 0}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"episode": ep, "ok": False, "findings": [{
            "severity": "block", "code": "bad_storyboard_json",
            "message": f"storyboard.json 不可解析：{exc}"
        }], "stats": {"units": 0}}
    if not isinstance(data, Mapping):
        return {"episode": ep, "ok": False, "findings": [{
            "severity": "block", "code": "bad_storyboard_shape",
            "message": "storyboard.json 顶层不是对象。"
        }], "stats": {"units": 0}}

    units = iter_units(data)
    if not units:
        findings.append({"severity": "block", "code": "no_storyboard_units",
                         "message": "storyboard.json 缺 clips[]/shots[]，无法逐镜头排程。"})

    scheduled = 0
    mismatches = 0
    for uid, unit, parent, fallback in units:
        schedule = _entity_schedule(unit, fallback)
        expected = _expected_entities(unit, parent)
        has_expected = any(expected.values())
        if not isinstance(schedule, Mapping):
            sev = "warn" if has_expected or _unit_text(unit) else "info"
            findings.append({"severity": sev, "code": "missing_entity_schedule",
                             "unit": uid,
                             "message": f"{uid} 缺 entity_schedule；无法给出 per-shot 角色/物件/地点/知识状态真值。"})
            continue
        scheduled += 1
        ents = _schedule_entities(schedule)
        missing_chars = sorted(expected["characters"] - ents["characters"])
        missing_objs = sorted(expected["objects"] - ents["objects"])
        missing_locs = sorted(expected["locations"] - ents["locations"])
        if missing_chars or missing_objs or missing_locs:
            mismatches += 1
            bits = []
            if missing_chars:
                bits.append("角色 " + "/".join(missing_chars[:6]))
            if missing_objs:
                bits.append("物件 " + "/".join(missing_objs[:6]))
            if missing_locs:
                bits.append("地点 " + "/".join(missing_locs[:4]))
            findings.append({"severity": "warn", "code": "entity_schedule_missing_expected",
                             "unit": uid,
                             "message": f"{uid} 的 entity_schedule 漏登记已在 clip/shot 字段出现的{'；'.join(bits)}。",
                             "missing": {"characters": missing_chars, "objects": missing_objs, "locations": missing_locs}})
        required = ents["required_presence"]
        declared = ents["characters"] | ents["objects"] | ents["locations"]
        dangling = sorted(required - declared)
        if dangling:
            mismatches += 1
            findings.append({"severity": "warn", "code": "required_presence_unbound",
                             "unit": uid,
                             "message": f"{uid} required_presence 指向未在 characters/objects/locations 登记的实体：{'/'.join(dangling[:8])}",
                             "entities": dangling})
        if not ents["locations"] and (expected["locations"] or schedule):
            findings.append({"severity": "info", "code": "entity_schedule_missing_location",
                             "unit": uid,
                             "message": f"{uid} entity_schedule 未登记 locations；长镜/跨镜场景连续性会缺 LOC 真值。"})

    warnish = any(f["severity"] in ("warn", "must", "block") for f in findings)
    stats = {
        "units": len(units),
        "scheduled_units": scheduled,
        "coverage": round(scheduled / len(units), 4) if units else None,
        "mismatched_units": mismatches,
        "missing_schedule_units": len(units) - scheduled,
    }
    return {"episode": ep, "ok": not warnish, "findings": findings, "stats": stats}


def print_human(res: Mapping[str, Any]) -> None:
    stats = res.get("stats") if isinstance(res.get("stats"), Mapping) else {}
    print(f"# 逐镜头实体排程检查 — {res.get('episode')}")
    print(f"单元 {stats.get('units', 0)}　已排程 {stats.get('scheduled_units', 0)}　覆盖率 {stats.get('coverage')}")
    findings = res.get("findings") or []
    if not findings:
        print("- OK: entity_schedule 覆盖且未发现字段漏登")
        return
    icon = {"block": "BLOCK", "must": "BLOCK", "warn": "WARN", "info": "INFO"}
    for f in findings:
        if isinstance(f, Mapping):
            print(f"- {icon.get(str(f.get('severity')), 'INFO')} [{f.get('code')}] {f.get('message')}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 逐镜头实体排程检查")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = audit_episode(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print_human(res)
    has_warn = any(f.get("severity") in ("warn", "must", "block") for f in res.get("findings", []) if isinstance(f, Mapping))
    return 1 if (ns.strict and has_warn) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
