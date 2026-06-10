#!/usr/bin/env python3
"""n2d 动态百科 / 状态哨兵（P1）。

检查会随剧情变化的视觉状态是否按镜头单调继承：

- `storyboard.json.visual_contract.角色状态演进`：伤、泪、乱发、觉醒态等从某镜开始保持。
- `出图/共享/visual_state_ledger.json`：跨集持续的可变状态锁（n2d-image 写方）。
- `出图/第N集/prompt/01_分镜出图.md`：逐镜 prompt 是否漏写 / 提前泄露状态。

这是 review 侧只读机检，不修改 ledger，也不注入 prompt。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import VISUAL_STATE_LEDGER_KIND, production_dir, shared_asset_path  # noqa: E402

import semantic_continuity as sem  # 复用文本抽词/Markdown 分块

KIND = "n2d_state_continuity_report"
VERSION = 1


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        data = json.load(open(path, encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def episode_num(text: str) -> Optional[int]:
    m = re.search(r"第\s*([0-9０-９]+)\s*集", str(text))
    if not m:
        m = re.search(r"([0-9０-９]+)", str(text))
    if not m:
        return None
    raw = m.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    try:
        return int(raw)
    except ValueError:
        return None


def shot_num(text: Any) -> Optional[int]:
    # 真实 producer 用 Clip 编号（storyboard 角色状态演进 `自:"Clip14"`、出图块 `## Clip 14`）；
    # 旧/手写状态句也可能是 镜N/镜头N/shotN/片段N。Clip 优先匹配。
    s = str(text)
    m = (re.search(r"(?:Clip|片段)\s*[_-]?\s*([0-9０-９]+)", s, re.I)
         or re.search(r"镜(?:头)?\s*([0-9０-９]+)", s)
         or re.search(r"shot\s*([0-9]+)", s, re.I))
    if not m:
        return None
    raw = m.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    return int(raw)


def range_end_shot(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    if re.search(r"(?:集尾|全集|后续|跨集|长期|持续|未解除|until\s+end)", text, re.I):
        return None
    return shot_num(text)


def is_single_shot_keep(value: Any) -> bool:
    return bool(re.search(r"(本镜|单镜|仅本镜|当前镜|只本镜|本\s*shot|single\s*shot)", str(value or ""), re.I))


def storyboard_path(root: str, ep: str) -> str:
    return os.path.join(root, "脚本", ep, "storyboard.json")


def image_prompt_path(root: str, ep: str) -> str:
    return os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")


def ledger_path(root: str) -> str:
    return shared_asset_path(root, "visual_state_ledger.json")


def state_terms(text: Any) -> List[str]:
    terms = sem.salient_terms(text, limit=16)
    # 状态句经常写成“Clip3 起左颊新伤”，补几个更短的稳定片段。
    extra: List[str] = []
    for t in terms:
        extra.extend(re.findall(r"[\u4e00-\u9fff]{2,6}", t))
    out: List[str] = []
    seen = set()
    for t in terms + extra:
        key = sem.normalize_text(t)
        if key and key not in seen and len(key) >= 2:
            seen.add(key)
            out.append(t)
    return out[:12]


def states_from_storyboard(sb: Dict[str, Any]) -> List[Dict[str, Any]]:
    vc = sb.get("visual_contract") if isinstance(sb.get("visual_contract"), dict) else {}
    data = vc.get("角色状态演进") or vc.get("角色状态演进表") or {}
    states: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        for char, entries in data.items():
            if isinstance(entries, str):
                entries = [entries]
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    status = entry.get("状态") or entry.get("status") or entry.get("description") or entry
                    start = shot_num(entry.get("自") or entry.get("from") or entry.get("start") or status) or 1
                    keep = entry.get("保持") or entry.get("until") or entry.get("keep") or "未声明"
                    end = range_end_shot(entry.get("至") or entry.get("until") or entry.get("end") or keep)
                    if end is None and is_single_shot_keep(keep):
                        end = start
                else:
                    status = str(entry)
                    start = shot_num(status) or 1
                    keep = "未声明"
                    end = range_end_shot(status)
                    if end is None and is_single_shot_keep(status):
                        end = start
                states.append({
                    "source": "storyboard.visual_contract",
                    "character": str(char),
                    "description": str(status),
                    "start_shot": start,
                    "end_shot": end,
                    "keep": str(keep),
                    "terms": state_terms(status),
                })
    return states


def states_from_visual_ledger(root: str, ep: str) -> List[Dict[str, Any]]:
    data = load_json(ledger_path(root))
    if not data:
        return []
    if data.get("kind") not in (None, VISUAL_STATE_LEDGER_KIND):
        return []
    current_ep = episode_num(ep) or 10**6
    states: List[Dict[str, Any]] = []
    chars = data.get("characters") if isinstance(data.get("characters"), dict) else {}
    for char, item in chars.items():
        mods = item.get("modifiers", []) if isinstance(item, dict) else []
        for mod in mods:
            if not isinstance(mod, dict) or not mod.get("active", True):
                continue
            added = episode_num(mod.get("added_in", "")) or 0
            if added > current_ep:
                continue
            removed = episode_num(mod.get("removed_in") or mod.get("ended_in") or mod.get("inactive_in") or "")
            if removed is not None and removed <= current_ep:
                continue
            desc = mod.get("description") or mod.get("mask_prompt") or mod.get("id")
            states.append({
                "source": "visual_state_ledger",
                "character": str(char),
                "description": str(desc),
                "start_shot": int(mod.get("start_shot") or 1),
                "end_shot": range_end_shot(mod.get("end_shot") or mod.get("until")),
                "keep": "跨集持续",
                "terms": state_terms(desc),
            })
    return states


def image_blocks(root: str, ep: str) -> List[Dict[str, Any]]:
    text = sem.read_text(image_prompt_path(root, ep))
    blocks: List[Dict[str, Any]] = []
    for blk in sem.split_md_blocks(text):
        no = shot_num(blk["heading"]) or shot_num(blk["body"])
        body = blk["body"]
        chars = []
        for raw in re.findall(r"定妆_([^`\s，。、,）)]+)", body):
            name = raw[:-4] if raw.endswith(".png") else raw
            name = re.sub(r"_(侧|背|半身|全身|三视图|设定表|表情)$", "", name)
            if name not in chars:
                chars.append(name)
        blocks.append({"shot": no, "heading": blk["heading"], "body": body, "characters": chars})
    return blocks


def block_mentions_character(block: Dict[str, Any], char: str) -> bool:
    text = block.get("body", "")
    return char in text or any(str(c).startswith(char) or char.startswith(str(c)) for c in block.get("characters", []))


def has_any_term(text: str, terms: Sequence[str]) -> bool:
    nt = sem.normalize_text(text)
    return any(sem.normalize_text(t) in nt for t in terms if sem.normalize_text(t))


def analyze(root: str, ep: str) -> Dict[str, Any]:
    root = root.rstrip("/")
    sb = load_json(storyboard_path(root, ep))
    notes: List[str] = []
    alerts: List[Dict[str, Any]] = []
    if not sb:
        return {
            "kind": KIND,
            "version": VERSION,
            "root": root,
            "episode": ep,
            "available": False,
            "states": [],
            "alerts": [],
            "verdicts": [],
            "notes": [f"缺 {storyboard_path(root, ep)}，状态哨兵跳过。"],
        }
    states = states_from_storyboard(sb) + states_from_visual_ledger(root, ep)
    if not states:
        notes.append("未发现角色状态演进或 visual_state_ledger active modifiers。")
    blocks = image_blocks(root, ep)
    if not blocks:
        notes.append("缺出图分镜 prompt，暂不验证状态继承。")

    for st in states:
        if not st.get("terms"):
            continue
        char = st["character"]
        start = int(st.get("start_shot") or 1)
        end = st.get("end_shot")
        end = int(end) if isinstance(end, int) else None
        for blk in blocks:
            no = blk.get("shot")
            if no is None or not block_mentions_character(blk, char):
                continue
            present = has_any_term(blk.get("body", ""), st["terms"])
            if no < start and present:
                alerts.append({
                    "verdict": "block",
                    "kind": "premature_state_leak",
                    "character": char,
                    "shot": no,
                    "state": st["description"],
                    "message": f"{char} 的状态 `{st['description']}` 在镜{start}前提前泄露。",
                })
            elif end is not None and no > end:
                if present:
                    alerts.append({
                        "verdict": "warn",
                        "kind": "state_leak_after_end",
                        "character": char,
                        "shot": no,
                        "state": st["description"],
                        "message": f"{char} 的状态 `{st['description']}` 声明至镜{end}，但镜{no} 仍保留。",
                    })
            elif no >= start and not present:
                alerts.append({
                    "verdict": "warn",
                    "kind": "state_missing_after_start",
                    "character": char,
                    "shot": no,
                    "state": st["description"],
                    "missing_terms": st["terms"],
                    "message": f"{char} 在镜{start}后应保持 `{st['description']}`，但镜{no} prompt 未见状态锁。",
                })

    verdicts = [a["verdict"] for a in alerts]
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "root": root,
        "episode": ep,
        "available": True,
        "states": states,
        "alerts": alerts,
        "verdicts": verdicts,
        "notes": notes,
        "summary": {
            "block": sum(1 for v in verdicts if v == "block"),
            "warn": sum(1 for v in verdicts if v == "warn"),
            "states": len(states),
        },
    }


def write_report(root: str, ep: str, data: Dict[str, Any]) -> str:
    safe_ep = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", ep)
    out = os.path.join(production_dir(root), f"state_continuity_{safe_ep}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    return out


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root, ns.episode)
    if ns.write:
        res["written"] = write_report(ns.root.rstrip("/"), ns.episode, res)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"=== n2d 动态百科 / 状态哨兵（P1）：{ns.root} {ns.episode} ===")
        for note in res.get("notes", []):
            print("ℹ️ " + note)
        for a in res.get("alerts", []):
            icon = "⛔" if a["verdict"] == "block" else "⚠️"
            print(f"{icon} 镜{a.get('shot')} · {a.get('character')}：{a.get('message')}")
        if not res.get("alerts"):
            print("✅ 状态演进未发现提前泄露/漏继承。")
    return 1 if any(v == "block" for v in res.get("verdicts", [])) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
