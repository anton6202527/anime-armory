#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 与 layout.json 生成 lettering.json 草案。"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_translation_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data = load_json(path)
    if isinstance(data.get("translations"), dict):
        return {str(k): str(v) for k, v in data["translations"].items()}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def read_setting(root: Path, key: str, default: str) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def text_fields(text: str, translations: dict[str, str]) -> dict[str, str]:
    text = str(text or "").strip()
    out = {"text": text, "text_zh": text}
    en = translations.get(text, "").strip()
    if en:
        out["text_en"] = en
    return out


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


def build_lettering(panel_script: dict, layout: dict, translations: dict[str, str], text_language: str) -> dict:
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
                    **text_fields(str(panel.get("narration", "")).strip(), translations),
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
                    **text_fields(dialogue.get("text", ""), translations),
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
                        **text_fields(str(sfx), translations),
                        "slot_id": slot.get("slot_id", ""),
                        "style": {"font": "project_default", "size": 72, "direction": "horizontal", "bubble": "none"},
                    }
                )
                counter += 1
    return {
        "schema_version": 1,
        "kind": "comic_lettering",
        "chapter": panel_script.get("chapter", ""),
        "language_mode": text_language,
        "items": items,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画 lettering.json 草案")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--translation-map", default=None, help="可选：中英翻译表 JSON，默认读 排版/第N话/lettering_translations.json")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    panel_script = load_json(root / "脚本" / args.chapter / "panel_script.json")
    layout = load_json(root / "排版" / args.chapter / "layout.json")
    translation_path = Path(args.translation_map).expanduser().resolve() if args.translation_map else root / "排版" / args.chapter / "lettering_translations.json"
    translations = load_translation_map(translation_path)
    text_language = read_setting(root, "文字语言", "中文")
    lettering = build_lettering(panel_script, layout, translations, text_language)
    if not lettering.get("chapter"):
        lettering["chapter"] = args.chapter
    if translations:
        lettering["translation_map"] = str(translation_path.relative_to(root))
    out_path = root / "排版" / args.chapter / "lettering.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(lettering, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
