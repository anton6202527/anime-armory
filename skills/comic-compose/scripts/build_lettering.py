#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 与 layout.json 生成 lettering.json 草案。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from text_metadata import infer_language_metadata, normalize_text_language


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_translation_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data = load_json(path)
    if isinstance(data.get("translations"), dict):
        return {str(k): str(v) for k, v in data["translations"].items()}
    return {str(k): str(v) for k, v in data.items() if isinstance(v, str)}


def load_finishing_plan(root: Path, chapter: str) -> dict:
    path = root / "出图" / chapter / "finishing" / "finishing_plan.json"
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def finishing_by_panel(plan: dict) -> dict[str, dict]:
    out = {}
    for panel in plan.get("panels") or []:
        if isinstance(panel, dict) and panel.get("panel_id"):
            out[str(panel.get("panel_id"))] = panel
    return out


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


def first_text(record: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(record.get(key, "") or "").strip()
        if value:
            return value
    return ""


def text_fields(text: str, translations: dict[str, str], text_language: str, source_text: str = "", zh_hint: str = "") -> dict[str, str]:
    text = str(text or "").strip()
    mode = normalize_text_language(text_language)
    metadata = infer_language_metadata(text, mode)
    out = {"text": text, **metadata}
    source = str(source_text or "").strip()
    if source and source != text:
        out["text_source"] = source
        source_meta = infer_language_metadata(source, "")
        out["source_lang"] = source_meta["lang"]
        out["source_dir"] = source_meta["dir"]
    if mode == "英文":
        out["text_en"] = text
        if zh_hint:
            out["text_zh"] = str(zh_hint).strip()
    elif mode.startswith("自定义语言"):
        out["text_custom"] = text
        if zh_hint:
            out["text_zh"] = str(zh_hint).strip()
    else:
        out["text_zh"] = text
    en = first_text({"text_en": translations.get(text, "")}, ("text_en",))
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


def build_lettering(panel_script: dict, layout: dict, translations: dict[str, str], text_language: str, finishing_map: dict[str, dict] | None = None) -> dict:
    finishing_map = finishing_map or {}
    slots = slots_by_panel(layout)
    items = []
    counter = 1
    for panel in panel_script.get("panels", []):
        pid = panel.get("panel_id")
        if not pid:
            continue
        panel_slots = slots.get(pid, {})
        narration_text = first_text(panel, ("narration_target", "target_narration", "narration"))
        if narration_text:
            slot = (panel_slots.get("narration") or [{}])[0]
            items.append(
                {
                    "item_id": f"L{counter:03d}",
                    "panel_id": pid,
                    "type": "narration",
                    "speaker": "",
                    **text_fields(
                        narration_text,
                        translations,
                        text_language,
                        first_text(panel, ("narration_source", "source_excerpt")),
                        str(panel.get("meaning_zh", "") or "").strip(),
                    ),
                    "slot_id": slot.get("slot_id", ""),
                    "style": {"font": "project_default", "size": 42, "direction": "horizontal", "bubble": "caption"},
                }
            )
            counter += 1
        dialogue_slots = panel_slots.get("dialogue") or []
        for idx, dialogue in enumerate(panel.get("dialogue") or []):
            slot = dialogue_slots[idx] if idx < len(dialogue_slots) else {}
            dialogue_text = first_text(dialogue, ("text_target", "target_text", "text"))
            items.append(
                {
                    "item_id": f"L{counter:03d}",
                    "panel_id": pid,
                    "type": "dialogue",
                    "speaker": dialogue.get("speaker", ""),
                    **text_fields(
                        dialogue_text,
                        translations,
                        text_language,
                        first_text(dialogue, ("source_text", "text_source", "source_excerpt")),
                        str(panel.get("meaning_zh", "") or "").strip(),
                    ),
                    "tone": dialogue.get("tone", ""),
                    "slot_id": slot.get("slot_id", ""),
                    "style": {"font": "project_default", "size": 44, "direction": "horizontal", "bubble": "round"},
                }
            )
            counter += 1
        if panel.get("sfx"):
            slot = (panel_slots.get("sfx") or [{}])[0]
            sfx_targets = panel.get("sfx_target") or panel.get("target_sfx") or []
            if isinstance(sfx_targets, str):
                sfx_targets = [sfx_targets]
            finish = finishing_map.get(str(pid), {})
            sfx_plan = finish.get("lettering_sfx_plan") if isinstance(finish.get("lettering_sfx_plan"), dict) else {}
            integration = str(sfx_plan.get("integration") or "").strip()
            shape = str(sfx_plan.get("shape") or "").strip()
            mode = str(sfx_plan.get("mode") or "post_lettering_sfx").strip()
            for idx, sfx in enumerate(panel.get("sfx") or []):
                sfx_text = str(sfx_targets[idx] if idx < len(sfx_targets) and str(sfx_targets[idx]).strip() else sfx).strip()
                items.append(
                    {
                        "item_id": f"L{counter:03d}",
                        "panel_id": pid,
                        "type": "sfx",
                        "speaker": "",
                        **text_fields(sfx_text, translations, text_language, str(sfx)),
                        "slot_id": slot.get("slot_id", ""),
                        "style": {
                            "font": "project_default",
                            "size": 72,
                            "direction": "horizontal",
                            "bubble": "none",
                            "drawn_lettering_mode": mode,
                            "integration": integration,
                            "shape": shape,
                        },
                    }
                )
                counter += 1
    return {
        "schema_version": 1,
        "kind": "comic_lettering",
        "chapter": panel_script.get("chapter", ""),
        "language_mode": normalize_text_language(text_language),
        "text_metadata_version": 1,
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
    finishing_map = finishing_by_panel(load_finishing_plan(root, args.chapter))
    lettering = build_lettering(panel_script, layout, translations, text_language, finishing_map)
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
