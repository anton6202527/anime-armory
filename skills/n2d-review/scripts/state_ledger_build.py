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

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
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


_CLIP_NUM_RE = re.compile(r"(?:Clip[_\s-]*|镜头)(\d+)", re.I)

# 自由文本 lifecycle 是否暗示「会变状态」（需结构化才能机检）——把静态道具(剑/镜)与演进道具(摔碎/染血)区分开。
_FREETEXT_STATEFUL_RE = re.compile(
    r"(摔碎|碎裂|破损|破碎|染血|沾血|血迹|脏污|弄脏|湿透|浸湿|燃烧|烧毁|焦黑|裂开|断裂|"
    r"变成|变为|转为|化为|褪色|生锈|腐蚀|后变|then|→|->)")


def _trigger_clip(trigger: Any) -> Optional[int]:
    m = _CLIP_NUM_RE.search(str(trigger or ""))
    return int(m.group(1)) if m else None


def props_from_registry(registry: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """把 asset_registry 里 PROP 资产的 lifecycle.states/transitions 解析成状态时间线。

    注册层 schema 早已定义这些字段、gate 也要求必填，但此前无人解析——
    道具状态演进（托盘摔碎/信物染血）只停留在声明。纯函数·可测。
    """
    out: Dict[str, Dict[str, Any]] = {}
    if not isinstance(registry, dict):
        return out
    for asset in registry.get("assets", []):
        if not isinstance(asset, dict) or asset.get("type") != "prop":
            continue
        life = asset.get("lifecycle")
        cur = str(asset.get("current_state") or "")
        issues: List[str] = []
        timeline: List[Dict[str, Any]] = []
        if not isinstance(life, dict):
            # 自由文本 lifecycle：默认给单状态结构化记录（states=[current_state]），不再留空——
            # 「结构化是默认」。若文本含状态演进语义却没结构化 → 明确标记 stateful_freetext，
            # state_continuity 据此把它当「应升级、未机检」问题上报（声明但不验证的口子在这里堵上）。
            life_text = str(life or "")
            stateful = bool(_FREETEXT_STATEFUL_RE.search(life_text))
            issues: List[str] = []
            if life_text and stateful:
                issues.append("lifecycle 为自由文本但含状态演进语义（默认应结构化）——"
                              "升级为 {states:[…], transitions:[{from,to,trigger}]} 才能机检道具状态演进")
            elif life_text:
                issues.append("lifecycle 为自由文本——升级为 {states:[…], transitions:[…]} 结构后才能对账道具状态演进")
            out[str(asset.get("id") or asset.get("name") or "PROP")] = {
                "name": asset.get("name"), "owner": asset.get("owner"),
                "current_state": cur, "states": ([cur] if cur else []), "timeline": [],
                "expected_state": cur, "lifecycle_note": life_text,
                "stateful_freetext": stateful, "issues": issues,
            }
            continue
        states = [str(s) for s in (life.get("states") or [])]
        for tr in life.get("transitions") or []:
            if not isinstance(tr, dict):
                continue
            frm, to = str(tr.get("from") or ""), str(tr.get("to") or "")
            timeline.append({"from": frm, "to": to, "trigger": str(tr.get("trigger") or ""),
                             "clip": _trigger_clip(tr.get("trigger")), "episode": tr.get("episode")})
            for st in (frm, to):
                if states and st and st not in states:
                    issues.append(f"transition 引用未声明状态「{st}」（states={states}）")
        if states and cur and cur not in states:
            issues.append(f"current_state「{cur}」不在 lifecycle.states 里")
        expected = timeline[-1]["to"] if timeline else (cur or (states[0] if states else ""))
        if timeline and cur and expected and cur != expected:
            issues.append(f"registry current_state「{cur}」落后于最后一笔 transition→「{expected}」，出图前先对齐")
        out[str(asset.get("id") or asset.get("name") or "PROP")] = {
            "name": asset.get("name"), "owner": asset.get("owner"),
            "current_state": cur, "states": states,
            "timeline": timeline, "expected_state": expected, "issues": issues,
        }
    return out


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
    props = props_from_registry(load_json(shared_asset_path(root, "asset_registry.json")))
    
    # Convert prop expected states into active modifiers for the ledger
    prop_modifiers = []
    for pid, p in props.items():
        if p.get("expected_state"):
            prop_modifiers.append({
                "id": f"prop_{slug(pid)}_{slug(p['expected_state'])}",
                "description": f"{p['name']} 处于 {p['expected_state']} 状态",
                "control_type": "prop_lock",
                "mask_prompt": f"{p['name']}: {p['expected_state']}",
                "added_in": "asset_registry",
                "active": True,
                "source": "asset_registry.lifecycle"
            })

    return {
        "kind": KIND,
        "version": VERSION,
        "schema_version": 1,
        "generated_at": now_iso(),
        "source": "n2d-review/state_ledger_build.py",
        "sources": sources,
        "characters": chars,
        "props": props,
        "prop_modifiers": prop_modifiers,
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
        print(f"storyboard: {len(data['sources'])}；characters: {len(data['characters'])}；props: {len(data.get('props', {}))}")
        for char, info in data["characters"].items():
            print(f"- {char}: active={len(info.get('modifiers', []))} timeline={len(info.get('timeline', []))}")
        for pid, p in data.get("props", {}).items():
            mark = " ⚠️" if p.get("issues") else ""
            print(f"- {pid}({p.get('name')}): 当前应为 `{p.get('expected_state')}` "
                  f"transitions={len(p.get('timeline', []))}{mark}")
            for issue in p.get("issues", []):
                print(f"    ⚠️ {issue}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
