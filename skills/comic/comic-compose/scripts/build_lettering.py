#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 与 layout.json 生成 lettering.json 草案。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from text_metadata import infer_language_metadata, normalize_text_language
from lettering_contract import (
    apply_editorial_override,
    binding_for_path,
    load_translation_map as load_translation_map_contract,
    resolve_translation,
    script_text_entries,
    translation_usage,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_translation_map(path: Path) -> dict[str, object]:
    """Compatibility wrapper around the v2 translation-map parser."""

    return load_translation_map_contract(path)


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


def text_fields(
    text: str,
    translations: dict[str, object],
    text_language: str,
    source_text: str = "",
    zh_hint: str = "",
    *,
    content_ref: str = "",
) -> dict[str, object]:
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
    en, translation_binding = resolve_translation(translations, content_ref, text)
    if translation_binding:
        out["translation_binding"] = translation_binding
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


def build_lettering(
    panel_script: dict,
    layout: dict,
    translations: dict[str, object],
    text_language: str,
    finishing_map: dict[str, dict] | None = None,
    *,
    source_bindings: dict[str, dict] | None = None,
    editorial_overrides: dict[str, dict] | None = None,
) -> dict:
    finishing_map = finishing_map or {}
    editorial_overrides = editorial_overrides or {}
    slots = slots_by_panel(layout)
    items: list[dict] = []
    override_issues: list[dict[str, object]] = []

    for counter, entry in enumerate(script_text_entries(panel_script), 1):
        panel_id = str(entry["panel_id"])
        item_type = str(entry["type"])
        content_ref = str(entry["content_ref"])
        panel_slots = slots.get(panel_id, {})
        type_slots = panel_slots.get(item_type) or []
        slot_by_ref = {
            str(slot.get("content_ref") or "").strip(): slot
            for slot in type_slots
            if isinstance(slot, dict) and str(slot.get("content_ref") or "").strip()
        }
        if slot_by_ref:
            slot = slot_by_ref.get(content_ref, {})
        else:
            ordinal = int(entry.get("ordinal") or 1)
            slot = type_slots[ordinal - 1] if ordinal <= len(type_slots) else {}

        style = {
            "font": "project_default",
            "size": 44,
            "direction": "horizontal",
            "bubble": "round",
        }
        if item_type == "narration":
            style.update({"size": 42, "bubble": "caption"})
        elif item_type == "sfx":
            finish = finishing_map.get(panel_id, {})
            sfx_plan = finish.get("lettering_sfx_plan") if isinstance(finish.get("lettering_sfx_plan"), dict) else {}
            style.update(
                {
                    "size": 72,
                    "bubble": "none",
                    "drawn_lettering_mode": str(sfx_plan.get("mode") or "post_lettering_sfx").strip(),
                    "integration": str(sfx_plan.get("integration") or "").strip(),
                    "shape": str(sfx_plan.get("shape") or "").strip(),
                }
            )

        item = {
            "item_id": f"L{counter:03d}",
            "content_ref": content_ref,
            "panel_id": panel_id,
            "type": item_type,
            "speaker": str(entry.get("speaker") or ""),
            "source_text": str(entry.get("source_text") or ""),
            "source_text_sha256": str(entry.get("source_text_sha256") or ""),
            **text_fields(
                str(entry.get("source_text") or ""),
                translations,
                text_language,
                str(entry.get("text_source") or ""),
                str(entry.get("zh_hint") or ""),
                content_ref=content_ref,
            ),
            "slot_id": str(slot.get("slot_id") or ""),
            "style": style,
        }
        if item_type == "dialogue":
            item.update(
                {
                    "tone": str(entry.get("tone") or ""),
                    "slot_speaker": str(slot.get("speaker") or ""),
                    "tail": slot.get("tail") if isinstance(slot.get("tail"), dict) else {},
                }
            )
        if item_type == "sfx" and entry.get("sound_source"):
            item["sound_source"] = str(entry.get("sound_source"))

        override = editorial_overrides.get(content_ref)
        if isinstance(override, dict):
            item["editorial_override"] = override
            replacement, errors = apply_editorial_override(
                {key: str(item.get(key) or "") for key in ("text", "text_zh", "text_en", "text_custom") if key in item},
                override,
                str(entry.get("source_text_sha256") or ""),
                content_ref,
            )
            if errors:
                override_issues.append({"content_ref": content_ref, "errors": errors})
            else:
                item.update(replacement)
        items.append(item)

    payload = {
        "schema_version": 2,
        "kind": "comic_lettering",
        "chapter": panel_script.get("chapter", ""),
        "language_mode": normalize_text_language(text_language),
        "text_metadata_version": 1,
        "items": items,
    }
    if source_bindings is not None:
        payload["source_bindings"] = source_bindings
    payload["translation_usage"] = translation_usage(items)
    if override_issues:
        payload["editorial_override_issues"] = override_issues
    return payload


EN_MODES = ("英文", "中上英下", "英上中下")
STYLE_KEYS = ("font", "size", "direction", "bubble")


def write_translation_todo(root: Path, chapter: str, lettering: dict) -> Path | None:
    """英文/双语模式下缺 text_en 的条目 → 翻译任务包（翻译这步的 owner 是 agent）。

    agent 逐条翻译后写 排版/第N话/lettering_translations.json
    （{"translations": {"panel:P001.dialogue:1": {"text_en": "English", "source_text_sha256": "..."}}}），重跑
    build_lettering 即回填。旧中文原文 key 仍兼容，但会被合同检查标 warn。
    """
    todo_path = root / "排版" / chapter / "lettering_translations.todo.json"
    if lettering.get("language_mode") not in EN_MODES:
        if todo_path.is_file():
            todo_path.unlink()
        return None
    pending = [
        {
            "item_id": item.get("item_id"),
            "content_ref": item.get("content_ref"),
            "panel_id": item.get("panel_id"),
            "type": item.get("type"),
            "speaker": item.get("speaker", ""),
            "tone": item.get("tone", ""),
            "source_text": item.get("source_text") or item.get("text") or "",
            "source_text_sha256": item.get("source_text_sha256") or "",
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
                "schema_version": 2,
                "kind": "comic_lettering_translation_todo",
                "chapter": chapter,
                "instructions": (
                    "由 agent 按 speaker/tone 逐条译成自然英文台词（不是逐字直译），"
                    "写 排版/" + chapter + "/lettering_translations.json："
                    '{"translations": {"<content_ref>": {"text_en": "<English>", '
                    '"source_text_sha256": "<pending.source_text_sha256>"}}}，然后重跑 build_lettering.py 回填 text_en。'
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
    panel_script_path = root / "脚本" / args.chapter / "panel_script.json"
    layout_path = root / "排版" / args.chapter / "layout.json"
    finishing_path = root / "出图" / args.chapter / "finishing" / "finishing_plan.json"
    out_path = root / "排版" / args.chapter / "lettering.json"
    panel_script = load_json(panel_script_path)
    layout = load_json(layout_path)
    translation_path = Path(args.translation_map).expanduser().resolve() if args.translation_map else root / "排版" / args.chapter / "lettering_translations.json"
    try:
        translations = load_translation_map(translation_path)
    except ValueError as exc:
        print(f"[err] {exc}")
        return 2
    text_language = read_setting(root, "文字语言", "中文")
    finishing_map = finishing_by_panel(load_finishing_plan(root, args.chapter))
    try:
        previous = load_json(out_path) if out_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        previous = {}
    if not isinstance(previous, dict):
        previous = {}
    editorial_overrides = {
        str(item.get("content_ref")): item.get("editorial_override")
        for item in previous.get("items") or []
        if isinstance(item, dict)
        and str(item.get("content_ref") or "").strip()
        and isinstance(item.get("editorial_override"), dict)
    }
    source_bindings = {
        "panel_script": binding_for_path(root, panel_script_path),
        "layout": binding_for_path(root, layout_path),
        "finishing_plan": binding_for_path(root, finishing_path),
        "translation_map": binding_for_path(root, translation_path),
    }
    lettering = build_lettering(
        panel_script,
        layout,
        translations,
        text_language,
        finishing_map,
        source_bindings=source_bindings,
        editorial_overrides=editorial_overrides,
    )
    if not lettering.get("chapter"):
        lettering["chapter"] = args.chapter
    if translation_path.is_file():
        lettering["translation_map"] = source_bindings["translation_map"]["path"]
    check_lettering_style_baseline(root, args.chapter, lettering)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(lettering, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {out_path}")
    todo = write_translation_todo(root, args.chapter, lettering)
    if todo:
        print(f"[warn] {lettering.get('language_mode')} 模式缺英文译文，翻译任务包已生成：{todo}；由 agent 翻译后重跑本脚本回填 text_en")
    usage = lettering.get("translation_usage") or {}
    if usage.get("legacy_text_key_count"):
        print(
            "[warn] 翻译表仍有 "
            f"{usage.get('legacy_text_key_count')} 条按原文 key 兼容命中；请改为 content_ref key 后重跑。"
        )
    if usage.get("unbound_content_ref_count"):
        print(
            "[warn] 翻译表有 "
            f"{usage.get('unbound_content_ref_count')} 条 content_ref 字符串值缺 source_text_sha256，已拒绝应用；"
            "请按翻译 TODO 升级为结构化值。"
        )
    if usage.get("stale_content_ref_count"):
        print(
            "[warn] 翻译表有 "
            f"{usage.get('stale_content_ref_count')} 条结构化译文绑定旧源文字 SHA，已拒绝应用并等待重译。"
        )
    for issue in lettering.get("editorial_override_issues") or []:
        print(f"[warn] editorial_override {issue.get('content_ref')}：{'；'.join(issue.get('errors') or [])}")
    for mismatch in (lettering.get("style_consistency") or {}).get("mismatches") or []:
        print(f"[warn] 嵌字样式：{mismatch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
