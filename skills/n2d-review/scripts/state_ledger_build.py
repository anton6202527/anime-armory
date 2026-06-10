#!/usr/bin/env python3
"""Build n2d visual_state_ledger from storyboard state evolution.

This is the deterministic writer-side companion to `state_continuity.py`.
It scans storyboard visual contracts across episodes and emits a dynamic
encyclopedia ledger that image/review stages can consume without asking an LLM
to rediscover persistent visual states.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import VISUAL_STATE_LEDGER_KIND, shared_asset_path  # noqa: E402

import state_continuity as stc  # noqa: E402

KIND = VISUAL_STATE_LEDGER_KIND
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_episode_filter(value: Optional[str]) -> Optional[Tuple[int, int]]:
    if not value:
        return None
    nums = [int(x) for x in re.findall(r"\d+", value)]
    if not nums:
        return None
    return (nums[0], nums[-1])


def in_episode_filter(ep: str, filt: Optional[Tuple[int, int]]) -> bool:
    if filt is None:
        return True
    num = stc.episode_num(ep)
    return num is not None and filt[0] <= num <= filt[1]


def storyboard_files(root: str, episodes: Optional[str] = None) -> List[Tuple[str, str]]:
    filt = parse_episode_filter(episodes)
    rows: List[Tuple[str, str]] = []
    for path in glob.glob(os.path.join(root.rstrip("/"), "脚本", "第*集", "storyboard.json")):
        ep = os.path.basename(os.path.dirname(path))
        if in_episode_filter(ep, filt):
            rows.append((ep, path))
    return sorted(rows, key=lambda item: stc.episode_num(item[0]) or 10**9)


def load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def slug(text: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", str(text)).strip("_")
    return cleaned[:48] or "state"


def is_cross_episode_keep(text: Any) -> bool:
    s = str(text or "")
    return bool(re.search(r"(跨集|后续|全剧|长期|持续到第|直到第|未解除|until\s+episode)", s, re.I))


def is_remove_state(text: Any) -> bool:
    s = str(text or "")
    return bool(re.search(r"(解除|移除|去除|消失|痊愈|恢复|换回|不再|结束|失效)", s))


def modifier_from_state(ep: str, state: Dict[str, Any]) -> Dict[str, Any]:
    desc = str(state.get("description") or "")
    start = int(state.get("start_shot") or 1)
    end = state.get("end_shot")
    keep = str(state.get("keep") or "")
    cross = is_cross_episode_keep(keep)
    return {
        "id": f"{slug(state.get('character', 'char'))}_{slug(desc)}_{slug(ep)}_{start}",
        "description": desc,
        "control_type": "prompt_tag",
        "mask_prompt": desc,
        "added_in": ep,
        "start_shot": start,
        "end_shot": end,
        "keep": keep,
        "scope": "cross_episode" if cross else "episode",
        "active": bool(cross and not is_remove_state(desc)),
        "source": "storyboard.visual_contract",
    }


def build(root: str, episodes: Optional[str] = None) -> Dict[str, Any]:
    chars: Dict[str, Dict[str, Any]] = {}
    sources: List[str] = []
    for ep, path in storyboard_files(root, episodes):
        data = load_json(path)
        if not data:
            continue
        sources.append(path)
        for state in stc.states_from_storyboard(data):
            char = str(state.get("character") or "").strip()
            if not char:
                continue
            item = chars.setdefault(char, {"modifiers": [], "timeline": []})
            mod = modifier_from_state(ep, state)
            item["timeline"].append(mod)
            if mod["active"]:
                item["modifiers"].append(mod)
            elif is_remove_state(mod["description"]):
                for prev in reversed(item["modifiers"]):
                    if prev.get("active", True):
                        prev["active"] = False
                        prev["removed_in"] = ep
                        prev["remove_reason"] = mod["description"]
                        break
    return {
        "kind": KIND,
        "version": VERSION,
        "schema_version": 1,
        "generated_at": now_iso(),
        "source": "n2d-review/state_ledger_build.py",
        "sources": sources,
        "characters": chars,
        "global_environment": [],
    }


def ledger_path(root: str) -> str:
    return shared_asset_path(root, "visual_state_ledger.json", prefer_existing=False)


def write(root: str, data: Dict[str, Any]) -> str:
    path = ledger_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(description="build n2d visual_state_ledger from storyboards")
    ap.add_argument("root")
    ap.add_argument("--episodes", help="episode range, e.g. 1-10 or 第1集-第10集")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    data = build(ns.root.rstrip("/"), ns.episodes)
    if ns.write:
        data["written"] = write(ns.root.rstrip("/"), data)
    if ns.json or ns.write:
        print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"=== n2d 动态百科构建：{ns.root} ===")
        print(f"storyboard: {len(data['sources'])}；characters: {len(data['characters'])}")
        for char, info in data["characters"].items():
            print(f"- {char}: active={len(info.get('modifiers', []))} timeline={len(info.get('timeline', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
