#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit/synchronize MV settings-derived runtime state and workflow rows.

``_设置.md`` is the preference truth. ``_meta.json`` mirrors compatibility
fields, while ``_进度.md`` mirrors the workflow variant derived from those
settings.  ``audit`` is read-only; ``sync`` is the explicit migration action.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import tempfile
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import completion  # noqa: E402
import contract  # noqa: E402
import mv_utils  # noqa: E402
import progress  # noqa: E402


RUNTIME_META_KEYS = tuple(contract.runtime_state_from_settings().keys())


def derive_runtime_state(root):
    settings_path = os.path.join(root, "_设置.md")
    settings = mv_utils.parse_settings(root)
    derived = contract.runtime_state_from_settings(settings)
    return {
        "settings_path": "_设置.md",
        "settings_present": os.path.isfile(settings_path),
        "settings": settings,
        "derived": derived,
    }


def _stage_rows(root):
    try:
        text = progress.read_progress(root)
    except FileNotFoundError:
        return None, []
    rows = [row for row in progress.parse_stage_rows(text) if not progress.is_retired_external(row)]
    by_label = {row["label"]: row["key"] for row in contract.stage_table()}
    normalized = []
    for row in rows:
        label = progress.clean_label(row.get("label"))
        normalized.append({
            "key": by_label.get(label),
            "label": label,
            "owner": row.get("owner", ""),
            "status": row.get("status", ""),
            "state": progress.state_of(row.get("status", "")),
        })
    return text, normalized


def progress_stage_issues(root, runtime=None):
    runtime = runtime or derive_runtime_state(root)["derived"]
    _text, rows = _stage_rows(root)
    if not rows:
        return ["_进度.md 缺可解析的完整制MV阶段表"]
    expected = contract.workflow_stage_table(
        runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"]
    )
    expected_keys = [row["key"] for row in expected]
    actual_keys = [row["key"] for row in rows]
    issues = []
    unknown = [row["label"] for row in rows if not row["key"]]
    if unknown:
        issues.append(f"_进度.md 有未登记阶段：{unknown}")
    known_actual = [key for key in actual_keys if key]
    duplicate = sorted({key for key in known_actual if known_actual.count(key) > 1})
    if duplicate:
        issues.append(f"_进度.md 有重复阶段：{duplicate}")
    missing = [key for key in expected_keys if key not in known_actual]
    extra = [key for key in known_actual if key not in expected_keys]
    if missing:
        issues.append(f"_进度.md 缺当前流程阶段：{missing}")
    if extra:
        issues.append(f"_进度.md 含不属于当前流程的阶段：{extra}")
    if known_actual != expected_keys:
        issues.append("_进度.md 阶段顺序与当前 歌曲输入时序/字幕/口型 派生流程不一致")
    return issues


def audit(root, stage_actions=None):
    root = os.path.abspath(root)
    runtime_info = derive_runtime_state(root)
    runtime = runtime_info["derived"]
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), None)
    errors = []
    warnings = []
    if not runtime_info["settings_present"]:
        errors.append("缺 _设置.md；运行时选择没有单一真值")
    if not isinstance(meta, dict):
        errors.append("缺或损坏 _meta.json")
        meta = {}
    mismatches = []
    for key, expected in runtime.items():
        actual = meta.get(key)
        if actual != expected:
            mismatches.append({"field": key, "settings_value": expected, "meta_value": actual})
    if mismatches:
        names = ", ".join(row["field"] for row in mismatches)
        errors.append(f"_meta.json 与 _设置.md 派生值不一致：{names}")
    has_song = mv_utils.find_song(root) is not None
    has_lyrics = os.path.isfile(os.path.join(root, "词", "lyrics.md"))
    for field, actual in (("has_song", has_song), ("has_lyrics", has_lyrics)):
        if meta.get(field) != actual:
            warnings.append(f"_meta.{field}={meta.get(field)!r} 与当前文件状态 {actual!r} 不一致")
    errors.extend(progress_stage_issues(root, runtime))
    contract_issues = contract.validate_stage_table(stage_actions)
    errors.extend(f"stage contract: {message}" for message in contract_issues)
    return {
        "kind": "mv_runtime_state_audit",
        "schema_version": 1,
        "ok": not errors,
        "root": root,
        "settings_present": runtime_info["settings_present"],
        "derived": runtime,
        "meta_mismatches": mismatches,
        "errors": errors,
        "warnings": warnings,
    }


_INVALIDATION_START = {
    "song_timing": "beat",
    "use_case": "plan",
    "aspect": "plan",
    "target_platform": "compose",
    "publish_target": "compose",
    "visual_style": "script",
    "plan_granularity": "plan",
    "beat_strategy": "plan",
    "image_model": "image",
    "image_channel": "image",
    "image_backend": "image",
    "video_model": "video_jobs",
    "video_channel": "video_jobs",
    "video_backend": "video_jobs",
    "video_spec": "video_jobs",
    "lip_sync_mode": "lyric_sync",
    "subtitle_language": "lyric_sync",
    "ai_visual_usage": "disclosure",
}


def _invalidated_stages(old_meta, runtime, expected_keys):
    start_indexes = []
    changed = []
    for field, expected in runtime.items():
        if old_meta.get(field) == expected:
            continue
        changed.append(field)
        start = _INVALIDATION_START.get(field)
        if start in expected_keys:
            start_indexes.append(expected_keys.index(start))
    if not start_indexes:
        return changed, set()
    first = min(start_indexes)
    return changed, set(expected_keys[first:])


def _replace_stage_table(text, stages, status_by_key):
    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 3 and cells[0] == "阶段" and cells[1] == "skill":
            header_index = index
            break
    table_lines = [
        "| 阶段 | skill | 状态 |",
        "|---|---|---|",
        *[
            f"| {stage['label']} | {stage['owner']} | {status_by_key.get(stage['key'], '[ ]')} |"
            for stage in stages
        ],
    ]
    if header_index is None:
        prefix = text.rstrip()
        return prefix + "\n\n## 制MV 阶段\n" + "\n".join(table_lines) + "\n"
    end = header_index
    while end < len(lines) and lines[end].strip().startswith("|"):
        end += 1
    new_lines = lines[:header_index] + table_lines + lines[end:]
    return "\n".join(new_lines).rstrip() + "\n"


def _atomic_write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".mv-state-", dir=os.path.dirname(path), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


_META_TO_SETTING = {
    "use_case": "MV用途",
    "song_timing": "歌曲输入时序",
    "visual_style": "MV视觉风格",
    "plan_granularity": "MV规划粒度",
    "beat_strategy": "卡点策略",
    "image_model": "生图模型",
    "image_channel": "生图渠道",
    "video_model": "生视频模型",
    "video_channel": "生视频渠道",
    "video_spec": "出视频规格",
    "lip_sync_mode": "演唱口型",
    "subtitle_language": "字幕语言",
    "aspect": "合成画幅",
    "ai_visual_usage": "AI视觉使用披露",
    "publish_target": "发行目标平台",
}


def _bootstrap_settings_from_meta(root, meta):
    values = dict(contract.DEFAULT_SETTINGS)
    for meta_key, setting_key in _META_TO_SETTING.items():
        value = meta.get(meta_key)
        if value not in (None, ""):
            values[setting_key] = value
    # Historical projects often only stored target_platform.
    if not meta.get("publish_target") and meta.get("target_platform"):
        values["发行目标平台"] = meta["target_platform"]
    if not meta.get("image_channel") and meta.get("image_backend"):
        values["生图渠道"] = meta["image_backend"]
    if not meta.get("video_channel") and meta.get("video_backend"):
        values["生视频渠道"] = meta["video_backend"]
    title = str(meta.get("title") or os.path.basename(root))
    _atomic_write_text(
        os.path.join(root, "_设置.md"), contract.settings_markdown(title, values)
    )


def sync(root, *, bootstrap_settings_from_meta=False):
    """Explicitly mirror settings to meta and migrate/reorder the progress table."""
    root = os.path.abspath(root)
    meta_path = os.path.join(root, "_meta.json")
    progress_path = os.path.join(root, "_进度.md")
    old_meta = mv_utils.load_json(meta_path, None)
    if not isinstance(old_meta, dict):
        raise ValueError("缺或损坏 _meta.json，不能安全迁移")
    runtime_info = derive_runtime_state(root)
    if not runtime_info["settings_present"]:
        if not bootstrap_settings_from_meta:
            raise ValueError(
                "缺 _设置.md；旧项目需显式加 --bootstrap-settings-from-meta，从现有 meta 建立一次性设置真值"
            )
        _bootstrap_settings_from_meta(root, old_meta)
        runtime_info = derive_runtime_state(root)
    runtime = runtime_info["derived"]
    old_progress = mv_utils.read_text(progress_path, "")
    if not old_progress:
        raise ValueError("缺 _进度.md，先重新初始化/恢复项目骨架")
    stages = contract.workflow_stage_table(
        runtime["song_timing"], runtime["subtitle_language"], runtime["lip_sync_mode"]
    )
    expected_keys = [stage["key"] for stage in stages]
    changed_fields, invalidated = _invalidated_stages(old_meta, runtime, expected_keys)

    _text, old_rows = _stage_rows(root)
    old_status = {row["key"]: row["status"] for row in old_rows if row.get("key")}
    status_by_key = {}
    for stage in stages:
        key = stage["key"]
        # Synchronization is a migration/invalidation operation, never a
        # completion controller.  Evidence-only writers (for example
        # ``--no-progress``) deliberately leave the row unfinished; a later
        # sync must not reverse that choice merely because output health is OK.
        # Missing/newly conditional rows therefore start todo.  Existing rows
        # may be preserved or downgraded, but are never promoted here.
        status = old_status.get(key, "[ ]")
        if key in invalidated:
            status = "[ ]"
        elif key == "song_ingest" and progress.state_of(status) == "done" and not mv_utils.find_song(root):
            status = "[ ]"
        elif (
            key in completion.OUTPUT_HEALTH_STAGES
            and progress.state_of(status) == "done"
            and not completion.stage_health(root, key)["ok"]
        ):
            # A markdown checkmark is only a cache.  Never preserve it when
            # the authoritative output/receipt validator says the evidence
            # is missing, stale, or malformed.
            status = "[ ]"
        status_by_key[key] = status

    new_meta = dict(old_meta)
    new_meta.update(runtime)
    new_meta["has_song"] = mv_utils.find_song(root) is not None
    new_meta["has_lyrics"] = os.path.isfile(os.path.join(root, "词", "lyrics.md"))
    new_progress = _replace_stage_table(old_progress, stages, status_by_key)
    _atomic_write_text(meta_path, json.dumps(new_meta, ensure_ascii=False, indent=2) + "\n")
    _atomic_write_text(progress_path, new_progress)

    receipt = {
        "schema_version": 1,
        "kind": "mv_state_sync_receipt",
        "synced_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "changed_runtime_fields": changed_fields,
        "invalidated_stages": [key for key in expected_keys if key in invalidated],
        "workflow_stage_keys": expected_keys,
        "inputs_sha256": {"_设置.md": mv_utils.content_hash(os.path.join(root, "_设置.md"))},
        "outputs_sha256": {
            "_meta.json": mv_utils.content_hash(meta_path),
            "_进度.md": mv_utils.content_hash(progress_path),
        },
    }
    receipt_path = os.path.join(root, "生产数据", "state_sync", "state_sync_receipt.json")
    mv_utils.write_json(receipt_path, receipt)
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    for name in ("audit", "sync"):
        parser = sub.add_parser(name)
        parser.add_argument("project_root")
        parser.add_argument("--json", action="store_true")
        if name == "sync":
            parser.add_argument("--bootstrap-settings-from-meta", action="store_true")
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    if args.command == "audit":
        result = audit(root)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"[{'ok' if result['ok'] else 'inconsistent'}] MV runtime state")
            for message in result["errors"]:
                print(f"  - {message}")
        return 0 if result["ok"] else 1
    try:
        receipt = sync(
            root,
            bootstrap_settings_from_meta=args.bootstrap_settings_from_meta,
        )
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(receipt, ensure_ascii=False, indent=2))
    else:
        print("[ok] 已从 _设置.md 同步 _meta.json，并迁移完整 _进度.md 阶段表")
        if receipt["invalidated_stages"]:
            print("[reset] " + ", ".join(receipt["invalidated_stages"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
