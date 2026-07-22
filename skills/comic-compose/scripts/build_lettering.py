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
        # Bind each script dialogue to its layout slot by the authoritative
        # content_ref (panel:PID.dialogue:N, 1-based), not by array index.  The
        # layout only creates a slot for dialogues with real target text, so a
        # positional pairing silently mis-attributes every balloon after an
        # empty-target line.  Positional fallback only for legacy boards whose
        # slots carry no content_ref.
        slot_by_ref = {
            str(s.get("content_ref") or "").strip(): s
            for s in dialogue_slots
            if isinstance(s, dict) and str(s.get("content_ref") or "").strip()
        }
        use_content_ref = bool(slot_by_ref)
        for idx, dialogue in enumerate(panel.get("dialogue") or []):
            dialogue_text = first_text(dialogue, ("text_target", "target_text", "text"))
            content_ref = f"panel:{pid}.dialogue:{idx + 1}"
            if use_content_ref:
                # Layout intentionally emitted no balloon for an empty-target line —
                # don't invent one.  A real line with no matching slot is kept
                # (slot_id="") so review can flag the coverage gap instead of it
                # silently rendering as a rogue floating bubble.
                if not dialogue_text and content_ref not in slot_by_ref:
                    continue
                slot = slot_by_ref.get(content_ref, {})
            else:
                slot = dialogue_slots[idx] if idx < len(dialogue_slots) else {}
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
                    "content_ref": content_ref,
                    "slot_speaker": str(slot.get("speaker") or ""),
                    "tail": slot.get("tail") if isinstance(slot.get("tail"), dict) else {},
                    "style": {"font": "project_default", "size": 44, "direction": "horizontal", "bubble": "round"},
                }
            )
            counter += 1
        if panel.get("sfx"):
            sfx_slots = panel_slots.get("sfx") or []
            sfx_targets = panel.get("sfx_target") or panel.get("target_sfx") or []
            if isinstance(sfx_targets, str):
                sfx_targets = [sfx_targets]
            finish = finishing_map.get(str(pid), {})
            sfx_plan = finish.get("lettering_sfx_plan") if isinstance(finish.get("lettering_sfx_plan"), dict) else {}
            integration = str(sfx_plan.get("integration") or "").strip()
            shape = str(sfx_plan.get("shape") or "").strip()
            mode = str(sfx_plan.get("mode") or "post_lettering_sfx").strip()
            for idx, sfx in enumerate(panel.get("sfx") or []):
                slot = sfx_slots[idx] if idx < len(sfx_slots) else {}
                target = sfx_targets[idx] if idx < len(sfx_targets) else ""
                if isinstance(target, dict):
                    target_text = first_text(target, ("text_target", "target_text", "text"))
                else:
                    target_text = str(target or "").strip()
                if isinstance(sfx, dict):
                    sfx_text = target_text or first_text(sfx, ("text_target", "target_text", "text"))
                    source_text = first_text(sfx, ("text_source", "source_text", "source_excerpt"))
                    sound_source = str(sfx.get("source") or "").strip()
                else:
                    sfx_text = target_text or str(sfx or "").strip()
                    source_text = ""
                    sound_source = ""
                item = {
                    "item_id": f"L{counter:03d}",
                    "panel_id": pid,
                    "type": "sfx",
                    "speaker": "",
                    **text_fields(sfx_text, translations, text_language, source_text),
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
                if sound_source:
                    item["sound_source"] = sound_source
                items.append(item)
                counter += 1
    return {
        "schema_version": 1,
        "kind": "comic_lettering",
        "chapter": panel_script.get("chapter", ""),
        "language_mode": normalize_text_language(text_language),
        "text_metadata_version": 1,
        "items": items,
    }


EN_MODES = ("英文", "中上英下", "英上中下")
STYLE_KEYS = ("font", "size", "direction", "bubble")


def write_translation_todo(root: Path, chapter: str, lettering: dict) -> Path | None:
    """英文/双语模式下缺 text_en 的条目 → 翻译任务包（翻译这步的 owner 是 agent）。

    agent 逐条翻译后写 排版/第N话/lettering_translations.json
    （{"translations": {"中文原文": "English"}}），重跑 build_lettering 即回填。
    """
    todo_path = root / "排版" / chapter / "lettering_translations.todo.json"
    if lettering.get("language_mode") not in EN_MODES:
        if todo_path.is_file():
            todo_path.unlink()
        return None
    pending = [
        {
            "item_id": item.get("item_id"),
            "panel_id": item.get("panel_id"),
            "type": item.get("type"),
            "speaker": item.get("speaker", ""),
            "tone": item.get("tone", ""),
            "text_zh": item.get("text_zh") or item.get("text") or "",
        }
        for item in lettering.get("items") or []
        if str(item.get("text") or "").strip() and not str(item.get("text_en") or "").strip()
    ]
    if not pending:
        if todo_path.is_file():
            todo_path.unlink()
        return None
    todo_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "comic_lettering_translation_todo",
                "chapter": chapter,
                "instructions": (
                    "由 agent 按 speaker/tone 逐条译成自然英文台词（不是逐字直译），"
                    "写 排版/" + chapter + "/lettering_translations.json："
                    '{"translations": {"<text_zh>": "<English>"}}，然后重跑 build_lettering.py 回填 text_en。'
                ),
                "pending_count": len(pending),
                "pending": pending,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return todo_path


def dominant_styles(lettering: dict) -> dict[str, dict]:
    """每种 item type 的主流 style（font/size/direction/bubble）。"""
    by_type: dict[str, dict[tuple, int]] = {}
    for item in lettering.get("items") or []:
        style = item.get("style") if isinstance(item.get("style"), dict) else {}
        key = tuple(str(style.get(k, "")) for k in STYLE_KEYS)
        by_type.setdefault(str(item.get("type") or ""), {})[key] = by_type.get(str(item.get("type") or ""), {}).get(key, 0) + 1
    out: dict[str, dict] = {}
    for item_type, counter in by_type.items():
        best = max(counter, key=counter.get)
        out[item_type] = {
            "style": dict(zip(STYLE_KEYS, best)),
            "variant_count": len(counter),
            "item_count": sum(counter.values()),
        }
    return out


def check_lettering_style_baseline(root: Path, chapter: str, lettering: dict) -> None:
    """嵌字字体/字号/气泡样式的项目级基线：首话落盘，后续各话比对。

    结果写进 lettering["style_consistency"]，comic-review 把 mismatches 转 warn。
    """
    baseline_path = root / "排版" / "lettering_style_baseline.json"
    current = dominant_styles(lettering)
    mismatches: list[str] = []
    for item_type, info in current.items():
        if info["variant_count"] > 1:
            mismatches.append(f"本话 {item_type} 出现 {info['variant_count']} 种样式（字体/字号/气泡应统一）")
    baseline = {}
    if baseline_path.is_file():
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            baseline = {}
    if not baseline.get("styles"):
        baseline_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "kind": "comic_lettering_style_baseline",
                    "source_chapter": chapter,
                    "styles": {k: v["style"] for k, v in current.items()},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"[ok] 嵌字样式基线已建立：{baseline_path}")
    else:
        for item_type, info in current.items():
            expected = baseline["styles"].get(item_type)
            if expected and expected != info["style"]:
                mismatches.append(
                    f"{item_type} 样式与基线话（{baseline.get('source_chapter')}）不一致：{info['style']} != {expected}"
                )
    lettering["style_consistency"] = {
        "baseline": str(Path("排版") / "lettering_style_baseline.json"),
        "dominant_styles": {k: v["style"] for k, v in current.items()},
        "mismatches": mismatches,
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
    check_lettering_style_baseline(root, args.chapter, lettering)
    out_path = root / "排版" / args.chapter / "lettering.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(lettering, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {out_path}")
    todo = write_translation_todo(root, args.chapter, lettering)
    if todo:
        print(f"[warn] {lettering.get('language_mode')} 模式缺英文译文，翻译任务包已生成：{todo}；由 agent 翻译后重跑本脚本回填 text_en")
    for mismatch in (lettering.get("style_consistency") or {}).get("mismatches") or []:
        print(f"[warn] 嵌字样式：{mismatch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
