#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Version contract for comic lettering.

``lettering.json`` is a derived artifact.  A file-level stage fingerprint alone
cannot prove that its text was rebuilt from the current script: a user can rerun
the gate against a new script while leaving the old lettering untouched.  This
module keeps the derivation explicit and independently recomputable:

* every upstream input is bound by project path + current SHA-256;
* every script text unit has a stable ``content_ref`` and source-text SHA;
* translations resolve by ``content_ref`` first (legacy text keys only warn);
* editorial rewrites are explicit, reviewed, and bound to the current source SHA.

The checker is dependency-free so comic-compose and comic-review can both call
the same deterministic implementation without introducing a cross-line layer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


KIND = "comic_lettering_contract"
SCHEMA_VERSION = 2
DISPLAY_FIELDS = ("text", "text_zh", "text_en", "text_custom")
REQUIRED_BINDINGS = ("panel_script", "layout", "finishing_plan", "translation_map")


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def record_path(root: Path, path: Path) -> str:
    resolved = path.expanduser().resolve()
    try:
        return str(resolved.relative_to(root.resolve()))
    except ValueError:
        return str(resolved)


def resolve_recorded_path(root: Path, raw: Any) -> Path | None:
    text = str(raw or "").strip()
    if not text or "://" in text or text.startswith("data:"):
        return None
    path = Path(text).expanduser()
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def binding_for_path(root: Path, path: Path) -> dict[str, Any]:
    exists = path.is_file()
    return {
        "path": record_path(root, path),
        "exists": exists,
        "sha256": sha256_file(path) if exists else "",
    }


def first_text(record: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = str(record.get(key, "") or "").strip()
        if value:
            return value
    return ""


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    return value if isinstance(value, list) else [value]


def script_text_entries(panel_script: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return current letterable source units in authored reading order.

    Empty target strings deliberately do not become lettering items.  Ordinals
    are still based on the raw source arrays, matching comic-name/layout refs, so
    an empty middle dialogue does not shift all subsequent balloons.
    """

    entries: list[dict[str, Any]] = []
    for panel in panel_script.get("panels") or []:
        if not isinstance(panel, Mapping):
            continue
        panel_id = str(panel.get("panel_id") or "").strip()
        if not panel_id:
            continue

        narration = first_text(panel, ("narration_target", "target_narration", "narration"))
        if narration:
            entries.append(
                {
                    "content_ref": f"panel:{panel_id}.narration",
                    "panel_id": panel_id,
                    "type": "narration",
                    "ordinal": 1,
                    "source_text": narration,
                    "source_text_sha256": sha256_text(narration),
                    "text_source": first_text(panel, ("narration_source", "source_excerpt")),
                    "zh_hint": str(panel.get("meaning_zh") or "").strip(),
                    "speaker": "",
                    "tone": "",
                }
            )

        for index, dialogue in enumerate(_as_list(panel.get("dialogue")), 1):
            if not isinstance(dialogue, Mapping):
                continue
            text = first_text(dialogue, ("text_target", "target_text", "text"))
            if not text:
                continue
            entries.append(
                {
                    "content_ref": f"panel:{panel_id}.dialogue:{index}",
                    "panel_id": panel_id,
                    "type": "dialogue",
                    "ordinal": index,
                    "source_text": text,
                    "source_text_sha256": sha256_text(text),
                    "text_source": first_text(dialogue, ("source_text", "text_source", "source_excerpt")),
                    "zh_hint": str(panel.get("meaning_zh") or "").strip(),
                    "speaker": str(dialogue.get("speaker") or ""),
                    "tone": str(dialogue.get("tone") or ""),
                }
            )

        sfx_values = _as_list(panel.get("sfx"))
        sfx_targets = _as_list(panel.get("sfx_target") or panel.get("target_sfx"))
        for index, sfx in enumerate(sfx_values, 1):
            target = sfx_targets[index - 1] if index <= len(sfx_targets) else ""
            if isinstance(target, Mapping):
                target_text = first_text(target, ("text_target", "target_text", "text"))
            else:
                target_text = str(target or "").strip()
            if isinstance(sfx, Mapping):
                text = target_text or first_text(sfx, ("text_target", "target_text", "text"))
                original = first_text(sfx, ("text_source", "source_text", "source_excerpt"))
                sound_source = str(sfx.get("source") or "").strip()
            else:
                raw_text = str(sfx or "").strip()
                text = target_text or raw_text
                original = raw_text if target_text and target_text != raw_text else ""
                sound_source = ""
            if not text:
                continue
            entries.append(
                {
                    "content_ref": f"panel:{panel_id}.sfx:{index}",
                    "panel_id": panel_id,
                    "type": "sfx",
                    "ordinal": index,
                    "source_text": text,
                    "source_text_sha256": sha256_text(text),
                    "text_source": original,
                    "zh_hint": "",
                    "speaker": "",
                    "tone": "",
                    "sound_source": sound_source,
                }
            )
    return entries


def translations_from_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    values = payload.get("translations") if isinstance(payload.get("translations"), Mapping) else payload
    return {
        str(key): dict(value) if isinstance(value, Mapping) else value
        for key, value in values.items()
        if isinstance(value, (str, Mapping))
    }


def load_translation_map(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = load_json(path, None)
    if payload is None:
        raise ValueError(f"翻译表不是有效 JSON：{path}")
    return translations_from_payload(payload)


def resolve_translation(
    translations: Mapping[str, Any],
    content_ref: str,
    source_text: str,
) -> tuple[str, dict[str, str] | None]:
    """Resolve English text with source-SHA safety.

    A positional ``content_ref`` alone is insufficient: after dialogue 1 changes
    from A to B, the same ref still exists.  Therefore only an object value whose
    ``source_text_sha256`` matches B may be applied.  Old ``content_ref: string``
    entries are surfaced as unbound and intentionally *not* applied.  A legacy
    ``source_text: string`` key remains safe from stale-position reuse because
    the key itself is the current source text, but it warns because duplicate
    lines cannot carry contextual translations.
    """

    current_sha = sha256_text(source_text)
    if content_ref in translations:
        raw = translations.get(content_ref)
        if isinstance(raw, Mapping):
            text = first_text(raw, ("text_en", "translation", "text"))
            recorded_sha = str(raw.get("source_text_sha256") or "").strip()
            if not text:
                return "", {
                    "key": content_ref,
                    "resolution": "content_ref_invalid",
                    "source_text_sha256": recorded_sha,
                }
            if not recorded_sha:
                return "", {
                    "key": content_ref,
                    "resolution": "content_ref_unbound",
                    "source_text_sha256": "",
                }
            if recorded_sha != current_sha:
                return "", {
                    "key": content_ref,
                    "resolution": "content_ref_stale",
                    "source_text_sha256": recorded_sha,
                }
            return text, {
                "key": content_ref,
                "resolution": "content_ref_sha256",
                "source_text_sha256": recorded_sha,
            }
        if isinstance(raw, str) and raw.strip():
            return "", {
                "key": content_ref,
                "resolution": "content_ref_unbound",
                "source_text_sha256": "",
            }
        return "", {
            "key": content_ref,
            "resolution": "content_ref_invalid",
            "source_text_sha256": "",
        }

    legacy_raw = translations.get(source_text, "")
    if isinstance(legacy_raw, Mapping):
        legacy = first_text(legacy_raw, ("text_en", "translation", "text"))
    else:
        legacy = str(legacy_raw or "").strip()
    if legacy:
        return legacy, {"key": source_text, "resolution": "legacy_text_key"}
    return "", None


def expected_display_fields(
    entry: Mapping[str, Any],
    translations: Mapping[str, Any],
    language_mode: str,
) -> tuple[dict[str, str], dict[str, str] | None]:
    source = str(entry.get("source_text") or "")
    fields = {"text": source}
    mode = str(language_mode or "中文").strip()
    zh_hint = str(entry.get("zh_hint") or "").strip()
    if mode == "英文":
        fields["text_en"] = source
        if zh_hint:
            fields["text_zh"] = zh_hint
    elif mode.startswith("自定义语言"):
        fields["text_custom"] = source
        if zh_hint:
            fields["text_zh"] = zh_hint
    else:
        fields["text_zh"] = source
    translated, binding = resolve_translation(
        translations,
        str(entry.get("content_ref") or ""),
        source,
    )
    if translated:
        fields["text_en"] = translated
    return fields, binding


def editorial_override_errors(
    override: Any,
    current_source_sha256: str,
    current_content_ref: str = "",
) -> list[str]:
    if not isinstance(override, Mapping):
        return ["editorial_override 必须是对象"]
    errors: list[str] = []
    bound_sha = str(override.get("source_text_sha256") or "").strip()
    if not bound_sha:
        errors.append("缺 source_text_sha256")
    elif bound_sha != current_source_sha256:
        errors.append("source_text_sha256 已失效")
    if current_content_ref:
        bound_ref = str(override.get("content_ref") or "").strip()
        if not bound_ref:
            errors.append("缺 content_ref")
        elif bound_ref != current_content_ref:
            errors.append("content_ref 与当前 item 不一致")
    for key in ("reason", "reviewed_by", "reviewed_at"):
        if not str(override.get(key) or "").strip():
            errors.append(f"缺 {key}")
    replacement = override.get("replacement")
    if not isinstance(replacement, Mapping) or not replacement:
        errors.append("缺 replacement")
    else:
        for key, value in replacement.items():
            if str(key) not in DISPLAY_FIELDS:
                errors.append(f"replacement 含非法字段 {key}")
            if not isinstance(value, str):
                errors.append(f"replacement.{key} 必须是字符串")
    return errors


def apply_editorial_override(
    fields: dict[str, str],
    override: Any,
    current_source_sha256: str,
    current_content_ref: str = "",
) -> tuple[dict[str, str], list[str]]:
    errors = editorial_override_errors(override, current_source_sha256, current_content_ref)
    if errors:
        return dict(fields), errors
    out = dict(fields)
    for key, value in (override.get("replacement") or {}).items():
        out[str(key)] = str(value)
    return out, []


def translation_usage(items: list[Mapping[str, Any]]) -> dict[str, Any]:
    content_refs: list[str] = []
    legacy_refs: list[str] = []
    unbound_refs: list[str] = []
    stale_refs: list[str] = []
    invalid_refs: list[str] = []
    for item in items:
        binding = item.get("translation_binding")
        if not isinstance(binding, Mapping):
            continue
        content_ref = str(item.get("content_ref") or "")
        if binding.get("resolution") == "content_ref_sha256":
            content_refs.append(content_ref)
        elif binding.get("resolution") == "legacy_text_key":
            legacy_refs.append(content_ref)
        elif binding.get("resolution") == "content_ref_unbound":
            unbound_refs.append(content_ref)
        elif binding.get("resolution") == "content_ref_stale":
            stale_refs.append(content_ref)
        elif binding.get("resolution") == "content_ref_invalid":
            invalid_refs.append(content_ref)
    return {
        "content_ref_count": len(content_refs),
        "legacy_text_key_count": len(legacy_refs),
        "legacy_content_refs": legacy_refs,
        "unbound_content_ref_count": len(unbound_refs),
        "unbound_content_refs": unbound_refs,
        "stale_content_ref_count": len(stale_refs),
        "stale_content_refs": stale_refs,
        "invalid_content_ref_count": len(invalid_refs),
        "invalid_content_refs": invalid_refs,
    }


def finding(severity: str, code: str, chapter: str, reason: str, suggested_fix: str) -> dict[str, str]:
    return {
        "severity": severity,
        "code": code,
        "artifact": f"排版/{chapter}/lettering.json",
        "reason": reason,
        "suggested_fix": suggested_fix,
    }


def _compare_binding(
    root: Path,
    chapter: str,
    name: str,
    recorded: Any,
    current_path: Path,
    findings: list[dict[str, str]],
    *,
    require_expected_path: bool,
) -> None:
    if not isinstance(recorded, Mapping):
        findings.append(finding(
            "block",
            "lettering_source_binding_missing",
            chapter,
            f"source_bindings.{name} 缺失，无法证明 lettering 消费了哪个当前输入。",
            "重跑 build_lettering.py 重建 lettering.json。",
        ))
        return
    if "sha256" not in recorded or not str(recorded.get("path") or "").strip():
        findings.append(finding(
            "block",
            "lettering_source_binding_incomplete",
            chapter,
            f"source_bindings.{name} 必须同时记录 path/exists/sha256。",
            "重跑 build_lettering.py 重建完整输入绑定。",
        ))
        return
    expected_path = record_path(root, current_path)
    if require_expected_path and str(recorded.get("path")) != expected_path:
        findings.append(finding(
            "block",
            "lettering_source_path_mismatch",
            chapter,
            f"source_bindings.{name}.path={recorded.get('path')}，当前权威路径应为 {expected_path}。",
            "不要手改绑定路径；从当前作品输入重跑 build_lettering.py。",
        ))
    current = binding_for_path(root, current_path)
    if bool(recorded.get("exists")) != current["exists"] or str(recorded.get("sha256") or "") != current["sha256"]:
        findings.append(finding(
            "block",
            "lettering_source_binding_stale",
            chapter,
            f"source_bindings.{name} 与当前文件不一致（记录 SHA={recorded.get('sha256') or '<empty>'}，当前 SHA={current['sha256'] or '<missing>'}）。",
            "上游输入已变化；重跑 build_lettering.py，再重新导出成品。",
        ))


def analyze(root: Path, chapter: str, lettering_path: Path | None = None) -> dict[str, Any]:
    root = root.expanduser().resolve()
    lettering_path = lettering_path or root / "排版" / chapter / "lettering.json"
    findings: list[dict[str, str]] = []
    notes: list[str] = []
    lettering = load_json(lettering_path, None)
    if not isinstance(lettering, Mapping):
        findings.append(finding(
            "block", "lettering_missing_or_invalid", chapter,
            "lettering.json 缺失或不是有效 JSON。",
            "运行 build_lettering.py 生成当前版本。",
        ))
        return _report(chapter, findings, notes)

    if int(lettering.get("schema_version") or 0) < SCHEMA_VERSION:
        findings.append(finding(
            "block", "lettering_schema_legacy", chapter,
            f"lettering schema_version={lettering.get('schema_version')}，缺少 v{SCHEMA_VERSION} 的输入和逐条文本绑定。",
            "重跑 build_lettering.py 升级 lettering.json；不要复制旧 gate receipt。",
        ))
    if str(lettering.get("kind") or "") != "comic_lettering":
        findings.append(finding(
            "block", "lettering_kind_invalid", chapter,
            "lettering kind 不是 comic_lettering。",
            "重跑 build_lettering.py 生成合法产物。",
        ))
    if str(lettering.get("chapter") or "") != chapter:
        findings.append(finding(
            "block", "lettering_chapter_mismatch", chapter,
            f"lettering.chapter={lettering.get('chapter')}，与当前 {chapter} 不一致。",
            "为当前话重跑 build_lettering.py。",
        ))

    bindings = lettering.get("source_bindings")
    bindings = bindings if isinstance(bindings, Mapping) else {}
    canonical = {
        "panel_script": root / "脚本" / chapter / "panel_script.json",
        "layout": root / "排版" / chapter / "layout.json",
        "finishing_plan": root / "出图" / chapter / "finishing" / "finishing_plan.json",
    }
    for name, path in canonical.items():
        _compare_binding(root, chapter, name, bindings.get(name), path, findings, require_expected_path=True)

    translation_record = bindings.get("translation_map")
    translation_path: Path | None = None
    if isinstance(translation_record, Mapping):
        translation_path = resolve_recorded_path(root, translation_record.get("path"))
    if translation_path is None:
        findings.append(finding(
            "block", "lettering_translation_binding_missing", chapter,
            "source_bindings.translation_map 缺少可解析 path；即使当前无译文，也必须绑定默认翻译表的缺失状态。",
            "重跑 build_lettering.py 写入 translation_map path/exists/sha256。",
        ))
        translation_path = root / "排版" / chapter / "lettering_translations.json"
    _compare_binding(
        root,
        chapter,
        "translation_map",
        translation_record,
        translation_path,
        findings,
        require_expected_path=False,
    )

    panel_script = load_json(canonical["panel_script"], None)
    if not isinstance(panel_script, Mapping):
        findings.append(finding(
            "block", "lettering_panel_script_invalid", chapter,
            "当前 panel_script.json 缺失或不可解析，无法复算逐条文字合同。",
            "先修复 comic-script 产物，再重建 lettering。",
        ))
        return _report(chapter, findings, notes)

    translations: dict[str, Any] = {}
    if translation_path.is_file():
        payload = load_json(translation_path, None)
        if payload is None:
            findings.append(finding(
                "block", "lettering_translation_map_invalid", chapter,
                "当前 translation_map 不是有效 JSON。",
                "修复 lettering_translations.json 后重跑 build_lettering.py。",
            ))
        else:
            translations = translations_from_payload(payload)

    expected_entries = script_text_entries(panel_script)
    expected_by_ref = {str(entry["content_ref"]): entry for entry in expected_entries}
    raw_items = lettering.get("items")
    items = raw_items if isinstance(raw_items, list) else []
    if not isinstance(raw_items, list):
        findings.append(finding(
            "block", "lettering_items_invalid", chapter,
            "lettering.items 必须是数组。",
            "重跑 build_lettering.py。",
        ))

    actual_by_ref: dict[str, Mapping[str, Any]] = {}
    for position, item in enumerate(items, 1):
        if not isinstance(item, Mapping):
            findings.append(finding(
                "block", "lettering_item_invalid", chapter,
                f"items[{position}] 不是对象。",
                "重跑 build_lettering.py。",
            ))
            continue
        content_ref = str(item.get("content_ref") or "").strip()
        if not content_ref:
            findings.append(finding(
                "block", "lettering_content_ref_missing", chapter,
                f"item {item.get('item_id') or position} 缺稳定 content_ref。",
                "重跑 build_lettering.py；对白、旁白与 SFX 都必须绑定 content_ref。",
            ))
            continue
        if content_ref in actual_by_ref:
            findings.append(finding(
                "block", "lettering_content_ref_duplicate", chapter,
                f"content_ref={content_ref} 在 lettering.items 中重复。",
                "去除重复条目并从 panel_script 重建。",
            ))
            continue
        actual_by_ref[content_ref] = item

    missing_refs = [ref for ref in expected_by_ref if ref not in actual_by_ref]
    extra_refs = [ref for ref in actual_by_ref if ref not in expected_by_ref]
    if missing_refs:
        findings.append(finding(
            "block", "lettering_content_coverage_missing", chapter,
            "当前脚本文字未进入 lettering：" + "、".join(missing_refs[:30]),
            "重跑 build_lettering.py；不要让新增对白/旁白/SFX 静默漏出。",
        ))
    if extra_refs:
        findings.append(finding(
            "block", "lettering_content_ref_stale", chapter,
            "lettering 仍含当前脚本不存在的文字：" + "、".join(extra_refs[:30]),
            "重跑 build_lettering.py 清理已删除或改序的文字。",
        ))

    resolved_items: list[Mapping[str, Any]] = []
    language_mode = str(lettering.get("language_mode") or "中文")
    for content_ref, entry in expected_by_ref.items():
        item = actual_by_ref.get(content_ref)
        if item is None:
            continue
        resolved_items.append(item)
        item_id = str(item.get("item_id") or content_ref)
        source_text = str(entry.get("source_text") or "")
        current_sha = str(entry.get("source_text_sha256") or "")
        if str(item.get("source_text") or "") != source_text or str(item.get("source_text_sha256") or "") != current_sha:
            findings.append(finding(
                "block", "lettering_source_text_stale", chapter,
                f"{item_id}/{content_ref} 未绑定当前脚本文字或 source_text_sha256 已失效。",
                "重跑 build_lettering.py；不能只重跑 gate 或手改 SHA。",
            ))
        if str(item.get("panel_id") or "") != str(entry.get("panel_id") or "") or str(item.get("type") or "") != str(entry.get("type") or ""):
            findings.append(finding(
                "block", "lettering_content_identity_mismatch", chapter,
                f"{item_id}/{content_ref} 的 panel_id/type 与当前脚本不一致。",
                "重跑 build_lettering.py。",
            ))

        expected_fields, expected_translation_binding = expected_display_fields(entry, translations, language_mode)
        override = item.get("editorial_override")
        override_errors: list[str] = []
        if override is not None:
            expected_fields, override_errors = apply_editorial_override(
                expected_fields,
                override,
                current_sha,
                content_ref,
            )
            if override_errors:
                findings.append(finding(
                    "block", "lettering_editorial_override_invalid", chapter,
                    f"{item_id}/{content_ref} editorial_override 无效：" + "；".join(override_errors),
                    "对当前 source_text_sha256 重新人工确认，补 reason/reviewed_by/reviewed_at/replacement；或移除改写并重建。",
                ))

        mismatched_fields = []
        for field in DISPLAY_FIELDS:
            actual = str(item.get(field) or "")
            expected = str(expected_fields.get(field) or "")
            if actual != expected:
                mismatched_fields.append(field)
        if mismatched_fields:
            code = "lettering_editorial_override_replacement_mismatch" if override is not None else "lettering_text_diverged_without_override"
            findings.append(finding(
                "block", code, chapter,
                f"{item_id}/{content_ref} 的 {','.join(mismatched_fields)} 与当前脚本/翻译表不一致"
                + ("，且 editorial_override 不能证明该改写。" if override is not None else "，但没有 SHA-bound editorial_override。"),
                "直接台词改写必须写 editorial_override；否则重跑 build_lettering.py 恢复当前源文字。",
            ))

        actual_translation_binding = item.get("translation_binding")
        if expected_translation_binding is None:
            if isinstance(actual_translation_binding, Mapping):
                findings.append(finding(
                    "block", "lettering_translation_binding_stale", chapter,
                    f"{item_id}/{content_ref} 仍记录 translation_binding，但当前翻译表已无对应译文。",
                    "重跑 build_lettering.py。",
                ))
        elif not isinstance(actual_translation_binding, Mapping) or any(
            str(actual_translation_binding.get(key) or "") != str(value or "")
            for key, value in expected_translation_binding.items()
        ):
            findings.append(finding(
                "block", "lettering_translation_binding_stale", chapter,
                f"{item_id}/{content_ref} 的 translation_binding 未绑定当前翻译表解析结果。",
                "重跑 build_lettering.py；翻译应优先使用 content_ref key。",
            ))
        if expected_translation_binding:
            resolution = expected_translation_binding["resolution"]
            if resolution == "legacy_text_key":
                findings.append(finding(
                    "warn", "lettering_translation_legacy_text_key", chapter,
                    f"{item_id}/{content_ref} 仍按中文原文 key={expected_translation_binding['key']!r} 取译文；重复原文无法表达不同上下文。",
                    f"迁移为 content_ref={content_ref} 的对象值，并绑定当前 source_text_sha256 后重跑 build_lettering.py。",
                ))
            elif resolution == "content_ref_unbound":
                findings.append(finding(
                    "warn", "lettering_translation_content_ref_unbound", chapter,
                    f"{item_id}/{content_ref} 的译文只绑定位置，没有 source_text_sha256，已拒绝应用以免脚本改词后错译。",
                    "把翻译值升级为 {\"text_en\": \"...\", \"source_text_sha256\": \"当前源文字SHA\"} 后重建。",
                ))
            elif resolution == "content_ref_stale":
                findings.append(finding(
                    "block", "lettering_translation_source_stale", chapter,
                    f"{item_id}/{content_ref} 的译文绑定旧 source_text_sha256={expected_translation_binding.get('source_text_sha256')}，当前原句已变化；旧译文未应用。",
                    "按 translation todo 针对当前原句重新翻译，更新 source_text_sha256 后重跑 build_lettering.py。",
                ))
            elif resolution == "content_ref_invalid":
                findings.append(finding(
                    "block", "lettering_translation_entry_invalid", chapter,
                    f"{item_id}/{content_ref} 的结构化译文缺 text_en/translation/text。",
                    "补齐结构化译文及当前 source_text_sha256 后重跑 build_lettering.py。",
                ))

    current_usage = translation_usage(resolved_items)
    recorded_usage = lettering.get("translation_usage")
    if not isinstance(recorded_usage, Mapping) or any(
        recorded_usage.get(key) != current_usage[key]
        for key in (
            "content_ref_count",
            "legacy_text_key_count",
            "legacy_content_refs",
            "unbound_content_ref_count",
            "unbound_content_refs",
            "stale_content_ref_count",
            "stale_content_refs",
            "invalid_content_ref_count",
            "invalid_content_refs",
        )
    ):
        findings.append(finding(
            "block", "lettering_translation_usage_stale", chapter,
            "lettering.translation_usage 与逐条 translation_binding 不一致。",
            "重跑 build_lettering.py 重建翻译消费账。",
        ))

    return _report(chapter, findings, notes)


def _report(chapter: str, findings: list[dict[str, str]], notes: list[str]) -> dict[str, Any]:
    block = sum(1 for item in findings if item.get("severity") == "block")
    warn = sum(1 for item in findings if item.get("severity") == "warn")
    return {
        "schema_version": 1,
        "kind": KIND,
        "chapter": chapter,
        "verdict": "block" if block else "warn" if warn else "pass",
        "summary": {"block": block, "warn": warn, "finding_count": len(findings)},
        "findings": findings,
        "notes": notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 lettering 与当前脚本/layout/finishing/翻译表的版本合同")
    parser.add_argument("project_root")
    parser.add_argument("chapter", nargs="?", default="第1话")
    parser.add_argument("--chapter", dest="chapter_opt", default="")
    parser.add_argument("--lettering", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = Path(args.project_root).expanduser().resolve()
    chapter = args.chapter_opt or args.chapter
    lettering_path = Path(args.lettering).expanduser().resolve() if args.lettering else None
    report = analyze(root, chapter, lettering_path)
    if args.write:
        out = root / "生产数据" / f"comic_lettering_contract_{chapter}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["verdict"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
