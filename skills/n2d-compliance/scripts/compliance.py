#!/usr/bin/env python3
"""Create and precheck n2d compliance manifests."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

_COMMON = str(Path(__file__).resolve().parent.parent.parent / "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import (  # noqa: E402  合规清单 kind / 身份注册路径单一真值源
    COMPLIANCE_ALLOWED_RIGHTS,
    COMPLIANCE_APPROVED_CHARACTER,
    COMPLIANCE_BLOCKED_CHARACTER,
    COMPLIANCE_DONE_STATUSES,
    COMPLIANCE_DOMESTIC_REGIONS,
    COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS,
    COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS,
    COMPLIANCE_MANIFEST_KIND,
    COMPLIANCE_OVERSEAS_PLATFORMS,
    COMPLIANCE_PLACEHOLDER_MARKERS,
    COMPLIANCE_PLATFORM_REVIEW_STATUSES,
    COMPLIANCE_READY_STATUSES,
    COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED,
    COMPLIANCE_SAFE_VOICE,
    COMPLIANCE_STATUS_LIKE_VALUES,
    identity_registry_path,
)


KIND = COMPLIANCE_MANIFEST_KIND
ALLOWED_RIGHTS = COMPLIANCE_ALLOWED_RIGHTS
RIGHTS_EVIDENCE_REQUIRED = COMPLIANCE_RIGHTS_EVIDENCE_REQUIRED
PLATFORM_REVIEW_STATUSES = COMPLIANCE_PLATFORM_REVIEW_STATUSES
APPROVED_CHARACTER = COMPLIANCE_APPROVED_CHARACTER
BLOCKED_CHARACTER = COMPLIANCE_BLOCKED_CHARACTER
SAFE_VOICE = COMPLIANCE_SAFE_VOICE
COMPLIANCE_READY = COMPLIANCE_READY_STATUSES
COMPLIANCE_DONE = COMPLIANCE_DONE_STATUSES
STATUS_LIKE_VALUES = COMPLIANCE_STATUS_LIKE_VALUES
OVERSEAS_PLATFORMS = COMPLIANCE_OVERSEAS_PLATFORMS
DOMESTIC_REGIONS = COMPLIANCE_DOMESTIC_REGIONS
PLACEHOLDER_MARKERS = COMPLIANCE_PLACEHOLDER_MARKERS

# internal_only 免检范围（与 n2d-review gate 同源，取契约常量）：
# distribution_intent ∈ COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS 时，
# COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS（platform_review / overseas_localization）字段域的
# BLOCK 降为 INFO 并加注「内部 demo 免检，转投放前需补」；角色/声音授权、AI 标识、水印照常 BLOCK。
INTERNAL_SKIP_NOTE = "（内部 demo 免检，转投放前需补）"


def is_internal_distribution(data: Dict[str, Any]) -> bool:
    return str(data.get("distribution_intent") or "").strip().lower() in COMPLIANCE_INTERNAL_DISTRIBUTION_INTENTS


# 契约域名 → manifest 字段名（overseas_localization 在 manifest 里叫 localization）
INTERNAL_SKIPPABLE_MANIFEST_KEYS = tuple(
    "localization" if section == "overseas_localization" else section
    for section in COMPLIANCE_INTERNAL_SKIPPABLE_SECTIONS
)


def has_real_value(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    lower = text.lower()
    if lower in {"xxx", "xx", "x", "...", "n/a?"}:
        return False
    return not any(marker in lower for marker in PLACEHOLDER_MARKERS)


def looks_like_status_value(value: Any) -> bool:
    return str(value or "").strip().lower() in STATUS_LIKE_VALUES


def valid_iso_date(value: Any) -> bool:
    try:
        dt.date.fromisoformat(str(value or "").strip())
        return True
    except ValueError:
        return False


def has_embedded_iso_date(value: Any) -> bool:
    text = str(value or "")
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if not match:
        return False
    try:
        dt.date.fromisoformat(match.group(0))
        return True
    except ValueError:
        return False


def episode_in_scope(episode: str | None, value: Any) -> bool:
    if episode is None:
        return True
    if value in (None, "", [], "all", "全剧"):
        return True
    if isinstance(value, list):
        return episode in value or "all" in value or "全剧" in value
    return str(value).strip() in (episode, "all", "全剧")


def now_date() -> str:
    return dt.date.today().isoformat()


def manifest_path(root: Path) -> Path:
    return root / "合规" / "compliance_manifest.json"


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def identity_character_ids(root: Path) -> List[str]:
    data = load_json(Path(identity_registry_path(str(root))))
    if not isinstance(data, dict):
        return []
    out = []
    for char in data.get("characters", []) or []:
        if isinstance(char, dict) and char.get("id"):
            out.append(str(char["id"]))
    return out


def default_manifest(root: Path, episode: str | None = None) -> Dict[str, Any]:
    chars = identity_character_ids(root)
    if not chars:
        chars = ["CHAR_TODO"]
    return {
        "kind": KIND,
        "version": 1,
        "updated_at": now_date(),
        "distribution_intent": "publish_candidate",
        "scope": {"episodes": [episode] if episode else "all"},
        "rights": {
            "source_text": {"status": "user_declared", "evidence": "TODO: 原创/公版/授权证明"},
            "adaptation": {"status": "user_declared", "evidence": "TODO: 改编权说明"},
            "music_bgm": {"status": "not_applicable", "evidence": ""},
            "sfx": {"status": "not_applicable", "evidence": ""},
            "fonts": {"status": "not_applicable", "evidence": ""},
        },
        "character_likeness": {
            "characters": [
                {"character_id": char_id, "status": "synthetic_character", "evidence": "原创合成角色"}
                for char_id in chars
            ],
        },
        "voice": {
            "status": "synthetic_voice",
            "uses_voice_clone": False,
            "authorization_status": "not_applicable",
            "evidence": "未使用真人参考音；若使用参考音，改为 authorized_clone + approved + evidence",
        },
        "ai_disclosure": {
            "required": True,
            "visible_label": {"status": "planned", "text": "AI 合成"},
            "metadata_label": {"status": "planned"},
            "c2pa_or_content_credentials": {"status": "not_supported", "fallback": "平台上传披露 + 项目合规留痕"},
            "hidden_or_platform_watermark": {"status": "planned", "note": "按目标平台要求补隐式/自动标识"},
        },
        "watermark": {
            "ai_visible": {"status": "planned", "tool": "skills/watermark/watermark.py --mode ai"},
            "metadata": {"status": "planned"},
            "final_assets": [],
        },
        "platform_review": {
            "targets": [{
                "platform": "TODO",
                "region": "CN",
                "language": "zh",
                "policy_profile": f"TODO_profile_{now_date()}",
                "profile_checked_at": now_date(),
                "copyright_review": "ready",
                "ai_disclosure_upload": "ready",
                "content_rating_review": "ready",
                "requires_localization": False,
            }],
        },
        "localization": {
            "status": "not_applicable",
            "subtitle_languages": ["zh"],
            "dub_languages": [],
            "notes": "",
        },
    }


def write_manifest(root: Path, episode: str | None, force: bool = False) -> Path:
    path = manifest_path(root)
    if path.exists() and not force:
        raise RuntimeError(f"{path} already exists; use --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(default_manifest(root, episode), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def check_manifest(root: Path, episode: str | None, stage: str = "compose") -> List[str]:
    path = manifest_path(root)
    data = load_json(path)
    issues: List[str] = []
    if not isinstance(data, dict):
        return [f"BLOCK {path}: missing or invalid JSON"]
    internal = is_internal_distribution(data)

    def flag_skippable(msg: str) -> None:
        # 免检域（platform_review / overseas_localization→localization）：internal_only 时降 INFO 并加注。
        if internal:
            issues.append(f"INFO {path}: {msg}{INTERNAL_SKIP_NOTE}")
        else:
            issues.append(f"BLOCK {path}: {msg}")

    if data.get("kind") != KIND:
        issues.append(f"BLOCK {path}: kind must be {KIND}")
    for key in ("rights", "character_likeness", "voice", "ai_disclosure", "watermark", "platform_review", "localization"):
        if not isinstance(data.get(key), dict):
            if key in INTERNAL_SKIPPABLE_MANIFEST_KEYS:
                flag_skippable(f"missing {key}")
            else:
                issues.append(f"BLOCK {path}: missing {key}")
    rights = data.get("rights") if isinstance(data.get("rights"), dict) else {}
    for key in ("source_text", "adaptation", "music_bgm", "sfx", "fonts"):
        item = rights.get(key)
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: missing rights.{key}")
            continue
        status = str(item.get("status") or "").strip()
        if not status:
            issues.append(f"BLOCK {path}: rights.{key} requires status")
        elif status not in ALLOWED_RIGHTS:
            issues.append(f"BLOCK {path}: rights.{key} status must be one of {', '.join(sorted(ALLOWED_RIGHTS))}; got {status}")
        if status in RIGHTS_EVIDENCE_REQUIRED and not has_real_value(item.get("evidence")):
            issues.append(f"BLOCK {path}: rights.{key} requires evidence/ref")
    registered = set(identity_character_ids(root))
    listed = {
        str(item.get("character_id"))
        for item in ((data.get("character_likeness") or {}).get("characters") or [])
        if isinstance(item, dict) and item.get("character_id")
    }
    for char_id in sorted(registered - listed):
        issues.append(f"BLOCK {path}: missing character_likeness for {char_id}")
    characters = ((data.get("character_likeness") or {}).get("characters")) or []
    if not isinstance(characters, list):
        issues.append(f"BLOCK {path}: character_likeness.characters must be list")
    else:
        for idx, item in enumerate(characters, 1):
            if not isinstance(item, dict):
                issues.append(f"BLOCK {path}: character_likeness.characters[{idx}] must be object")
                continue
            status = str(item.get("status") or "").strip()
            char_id = item.get("character_id") or idx
            if status in BLOCKED_CHARACTER or status not in APPROVED_CHARACTER:
                issues.append(f"BLOCK {path}: character_likeness.{char_id} status not releasable: {status or 'missing'}")
            if status in {"actor_authorized", "self_authorized", "licensed_likeness"} and not has_real_value(item.get("evidence")):
                issues.append(f"BLOCK {path}: character_likeness.{char_id} requires evidence/ref")
    voice = data.get("voice") if isinstance(data.get("voice"), dict) else {}
    voice_status = str(voice.get("status") or "").strip()
    if voice_status not in SAFE_VOICE:
        issues.append(f"BLOCK {path}: voice status not releasable: {voice_status or 'missing'}")
    if voice.get("uses_voice_clone") is True or voice_status == "authorized_clone":
        if voice.get("authorization_status") != "approved":
            issues.append(f"BLOCK {path}: voice clone requires authorization_status=approved")
        if not has_real_value(voice.get("evidence")):
            issues.append(f"BLOCK {path}: voice clone requires evidence/ref")
    ai_disclosure = data.get("ai_disclosure") if isinstance(data.get("ai_disclosure"), dict) else {}
    if ai_disclosure.get("required") is not True:
        issues.append(f"BLOCK {path}: ai_disclosure.required must be true")
    for key in ("visible_label", "metadata_label", "c2pa_or_content_credentials", "hidden_or_platform_watermark"):
        item = ai_disclosure.get(key)
        if not isinstance(item, dict):
            issues.append(f"BLOCK {path}: missing ai_disclosure.{key}")
            continue
        status = str(item.get("status") or "").strip()
        if status not in COMPLIANCE_READY:
            issues.append(f"BLOCK {path}: ai_disclosure.{key} status not releasable: {status or 'missing'}")
        if stage == "review" and key in ("visible_label", "metadata_label") and status not in COMPLIANCE_DONE:
            issues.append(f"BLOCK {path}: ai_disclosure.{key} must be done before review")
    watermark = data.get("watermark") if isinstance(data.get("watermark"), dict) else {}
    visible = watermark.get("ai_visible")
    if not isinstance(visible, dict):
        issues.append(f"BLOCK {path}: missing watermark.ai_visible")
    else:
        status = str(visible.get("status") or "").strip()
        if status not in COMPLIANCE_READY:
            issues.append(f"BLOCK {path}: watermark.ai_visible status not releasable: {status or 'missing'}")
        if stage == "review" and status != "done":
            issues.append(f"BLOCK {path}: watermark.ai_visible must be done before review")
    metadata = watermark.get("metadata")
    if isinstance(metadata, dict):
        status = str(metadata.get("status") or "").strip()
        if status and status not in COMPLIANCE_READY:
            issues.append(f"BLOCK {path}: watermark.metadata status not releasable: {status}")
    # platform_review / overseas_localization：internal_only 不再整体跳过，而是同样检查、
    # 把 BLOCK 降为 INFO（内部 demo 免检，转投放前需补）——与 n2d-review gate 同源行为。
    targets = ((data.get("platform_review") or {}).get("targets")) or []
    if not targets:
        flag_skippable("publish candidate requires platform_review.targets")
    for idx, target in enumerate(targets, 1):
        if not isinstance(target, dict):
            flag_skippable(f"platform_review.targets[{idx}] must be object")
            continue
        for key in ("platform", "region", "policy_profile", "profile_checked_at", "copyright_review", "ai_disclosure_upload", "content_rating_review"):
            if not has_real_value(target.get(key)):
                flag_skippable(f"platform_review.targets[{idx}] requires real {key}")
        for key in ("platform", "region"):
            if has_real_value(target.get(key)) and looks_like_status_value(target.get(key)):
                flag_skippable(f"platform_review.targets[{idx}] {key} must be a concrete value, not status placeholder")
        if has_real_value(target.get("policy_profile")) and not has_embedded_iso_date(target.get("policy_profile")):
            flag_skippable(f"platform_review.targets[{idx}] policy_profile must include YYYY-MM-DD checked date")
        if has_real_value(target.get("profile_checked_at")) and not valid_iso_date(target.get("profile_checked_at")):
            flag_skippable(f"platform_review.targets[{idx}] profile_checked_at must be YYYY-MM-DD")
        for key in ("copyright_review", "ai_disclosure_upload", "content_rating_review"):
            value = str(target.get(key) or "").strip()
            if value and value not in PLATFORM_REVIEW_STATUSES:
                flag_skippable(f"platform_review.targets[{idx}] {key} must be ready/done/not_applicable")
        platform = str(target.get("platform") or "").strip()
        region = str(target.get("region") or "").strip().lower()
        overseas = target.get("requires_localization") is True or platform.lower() in OVERSEAS_PLATFORMS or (region and region not in DOMESTIC_REGIONS)
        if overseas:
            localization = data.get("localization") if isinstance(data.get("localization"), dict) else {}
            loc_status = str(localization.get("status") or "").strip()
            if loc_status not in {"ready", "done"}:
                flag_skippable(f"localization.status must be ready/done for overseas target {platform or region}")
            languages = {str(item).lower() for item in (localization.get("subtitle_languages") or [])}
            required = str(target.get("language") or "").strip().lower()
            if required and required not in languages:
                flag_skippable(f"localization.subtitle_languages must include target language {required}")
    if episode:
        final_assets = (data.get("watermark") or {}).get("final_assets") or []
        if (data.get("watermark") or {}).get("ai_visible", {}).get("status") == "done":
            assets = [item for item in final_assets if isinstance(item, dict) and episode_in_scope(episode, item.get("episode"))]
            if not assets:
                level = "BLOCK" if stage == "review" else "WARN"
                issues.append(f"{level} {path}: ai_visible done but no final asset registered for {episode}")
            for item in assets:
                rel = str(item.get("path") or "").strip()
                if not rel:
                    issues.append(f"BLOCK {path}: watermark final asset for {episode} requires path")
                    continue
                full = Path(rel) if Path(rel).is_absolute() else root / rel
                if not full.exists():
                    issues.append(f"BLOCK {path}: registered watermark asset missing: {rel}")
    return issues


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Create/check n2d compliance manifest.")
    ap.add_argument("root")
    ap.add_argument("episode", nargs="?")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--stage", choices=("image", "video", "compose", "review"), default="compose")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    if ns.init:
        path = write_manifest(root, ns.episode, force=ns.force)
        print(f"wrote {path}")
    if ns.check or not ns.init:
        issues = check_manifest(root, ns.episode, stage=ns.stage)
        if issues:
            print("\n".join(issues))
            return 1 if any(item.startswith("BLOCK") for item in issues) else 0
        print("compliance manifest ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
