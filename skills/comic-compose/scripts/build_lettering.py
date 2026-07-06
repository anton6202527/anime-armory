#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 与 layout.json 生成 lettering.json 草案。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slots_by_panel(layout: dict) -> dict[str, dict[str, list[dict]]]:
    out: dict[str, dict[str, list[dict]]] = {}
    for segment in layout.get("segments", []):
        for panel in segment.get("panels", []):
            pid = panel.get("panel_id")
            if not pid:
                continue
            grouped = {"dialogue": [], "narration": [], "sfx": []}
            for slot in panel.get("bubble_slots", []):
                grouped.setdefault(slot.get("type", "dialogue"), []).append(slot)
            out[pid] = grouped
    return out


def build_lettering(panel_script: dict, layout: dict) -> dict:
    slots = slots_by_panel(layout)
    items = []
    counter = 1
    for panel in panel_script.get("panels", []):
        pid = panel.get("panel_id")
        if not pid:
            continue
        panel_slots = slots.get(pid, {})
        if str(panel.get("narration", "")).strip():
            slot = (panel_slots.get("narration") or [{}])[0]
            items.append(
                {
                    "item_id": f"L{counter:03d}",
                    "panel_id": pid,
                    "type": "narration",
                    "speaker": "",
                    "text": str(panel.get("narration", "")).strip(),
                    "slot_id": slot.get("slot_id", ""),
                    "style": {"font": "project_default", "size": 42, "direction": "horizontal", "bubble": "caption"},
                }
            )
            counter += 1
        dialogue_slots = panel_slots.get("dialogue") or []
        for idx, dialogue in enumerate(panel.get("dialogue") or []):
            slot = dialogue_slots[idx] if idx < len(dialogue_slots) else {}
            items.append(
                {
                    "item_id": f"L{counter:03d}",
                    "panel_id": pid,
                    "type": "dialogue",
                    "speaker": dialogue.get("speaker", ""),
                    "text": dialogue.get("text", ""),
                    "tone": dialogue.get("tone", ""),
                    "slot_id": slot.get("slot_id", ""),
                    "style": {"font": "project_default", "size": 44, "direction": "horizontal", "bubble": "round"},
                }
            )
            counter += 1
        if panel.get("sfx"):
            slot = (panel_slots.get("sfx") or [{}])[0]
            for sfx in panel.get("sfx") or []:
                items.append(
                    {
                        "item_id": f"L{counter:03d}",
                        "panel_id": pid,
                        "type": "sfx",
                        "speaker": "",
                        "text": str(sfx),
                        "slot_id": slot.get("slot_id", ""),
                        "style": {"font": "project_default", "size": 72, "direction": "horizontal", "bubble": "none"},
                    }
                )
                counter += 1
    return {"schema_version": 1, "kind": "comic_lettering", "chapter": panel_script.get("chapter", ""), "items": items}


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画 lettering.json 草案")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    panel_script = load_json(root / "脚本" / args.chapter / "panel_script.json")
    layout = load_json(root / "排版" / args.chapter / "layout.json")
    lettering = build_lettering(panel_script, layout)
    out_path = root / "排版" / args.chapter / "lettering.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(lettering, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
