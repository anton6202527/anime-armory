#!/usr/bin/env python3
"""Create a versioned, evidence-bound MV platform/jurisdiction release decision.

This is intentionally not an uploader. It records what the human actually did
in the platform upload flow and binds screenshots/exports/receipts copied into
the project. A C2PA credential is one machine-readable signal; it never stands
in for a platform disclosure switch or a visible label.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
import re
import sys
from typing import Any
from urllib.parse import urlparse

import mv_utils
import completion


RULESET_VERSION = "2026-08-20"
SOURCES = {
    "CN-AIGC-LABEL-2025": {
        "title": "人工智能生成合成内容标识办法",
        "url": "https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm",
        "published": "2025-03-14",
        "effective": "2025-09-01",
        "checked_at": RULESET_VERSION,
        "scope_note": "第十条要求用户发布生成合成内容时主动声明并使用平台标识功能。",
    },
    "EU-AIA-ARTICLE-50-2026": {
        "title": "EU AI Act Article 50 transparency guidance",
        "url": "https://digital-strategy.ec.europa.eu/en/policies/guidelines-ai-transparency-obligations",
        "effective": "2026-08-02",
        "checked_at": RULESET_VERSION,
        "scope_note": "机器可读标记与 deepfake 可见披露是不同义务；具体角色适用性需法务复核。",
    },
    "YOUTUBE-AI-DISCLOSURE": {
        "title": "Disclosing use of altered or synthetic content",
        "url": "https://support.google.com/youtube/answer/14328491",
        "checked_at": RULESET_VERSION,
        "scope_note": "写实且有实质改变的合成内容需在上传流程声明；官方示例含合成音乐。",
    },
    "YOUTUBE-MUSIC-GENAI": {
        "title": "Disclose Gen AI usage for music content",
        "url": "https://support.google.com/youtube/answer/17124251",
        "checked_at": RULESET_VERSION,
        "scope_note": "音乐合作伙伴交付支持 Fully/Partly/No Gen AI 分类。",
    },
    "TIKTOK-AIGC": {
        "title": "TikTok Community Guidelines: Edited Media and AIGC",
        "url": "https://www.tiktok.com/community-guidelines/en/integrity-authenticity/",
        "checked_at": RULESET_VERSION,
        "scope_note": "写实描绘人物或场景的 AI/编辑媒体要求清晰标识。",
    },
}
CHINA_PLATFORMS = {"抖音", "B站", "小红书", "网易云", "QQ音乐"}
KNOWN_PLATFORMS = CHINA_PLATFORMS | {"YouTube", "TikTok"}
STATUS_CHOICES = ("completed", "pending", "not_applicable")
MACHINE_LABEL_METHODS = ("c2pa", "platform_metadata", "other", "pending")
UPLOAD_RECEIPT_KIND = "mv_platform_upload_receipt"
UPLOAD_RECEIPT_SCHEMA_VERSION = 3
UPLOAD_SOURCES = {"platform_api_response", "platform_ui_export"}
PLATFORM_HOST_SUFFIXES = {
    "抖音": ("douyin.com", "iesdouyin.com"),
    "B站": ("bilibili.com", "b23.tv"),
    "小红书": ("xiaohongshu.com", "xhslink.com"),
    "YouTube": ("youtube.com", "youtu.be"),
    "TikTok": ("tiktok.com",),
    "Spotify": ("spotify.com",),
    "网易云": ("music.163.com", "163.com"),
    "QQ音乐": ("y.qq.com", "qq.com"),
}
_PLACEHOLDER_ID = re.compile(r"^(?:<.*>|test|demo|fake|unknown|none|n/a|待填|待定)$", re.I)


def _real_ai(disclosure: dict[str, Any]) -> bool:
    return disclosure.get("gen_ai_classification") != "no_gen_ai"


def applicable_requirements(
    disclosure: dict[str, Any], platforms: list[str], territories: list[str]
) -> list[dict[str, Any]]:
    ai_present = _real_ai(disclosure)
    realism = disclosure.get("realism")
    real_person = disclosure.get("real_person_status") == "authorized"
    music_ai = disclosure.get("music_mode") in {"AI-assisted", "AI-generated"}
    territory_set = {str(row).upper() for row in territories}
    platform_set = {str(row) for row in platforms}
    rows: list[dict[str, Any]] = []

    def add(key: str, reason: str, source: str, evidence: str) -> None:
        if key not in {row["id"] for row in rows}:
            rows.append({"id": key, "required": True, "reason": reason, "source": source, "evidence_class": evidence})

    if ai_present:
        # Production policy: preserve a machine-readable disclosure signal for
        # every AI-bearing release even where the legal duty falls on a provider.
        policy_source = (
            "EU-AIA-ARTICLE-50-2026" if "EU" in territory_set
            else "CN-AIGC-LABEL-2025" if "CN" in territory_set or platform_set & CHINA_PLATFORMS
            else "internal-production-policy"
        )
        add(
            "machine_readable_disclosure",
            "AI-bearing delivery must retain a verifiable machine-readable disclosure signal.",
            policy_source,
            "machine",
        )
    if ai_present and ("CN" in territory_set or platform_set & CHINA_PLATFORMS):
        add("platform_ai_declaration", "中国发布用户须主动声明生成合成内容。", "CN-AIGC-LABEL-2025", "platform")
        add("visible_platform_label", "必须使用传播平台提供的显著标识功能。", "CN-AIGC-LABEL-2025", "platform")
    if ai_present and "EU" in territory_set and (realism in {"photorealistic", "mixed"} or real_person):
        add("visible_platform_label", "EU deepfake/写实合成场景需评估并落实可见披露。", "EU-AIA-ARTICLE-50-2026", "platform")
    if "YouTube" in platform_set and (realism in {"photorealistic", "mixed"} or real_person or music_ai):
        add("platform_ai_declaration", "YouTube 上传流程需声明写实合成内容；合成音乐也在官方示例中。", "YOUTUBE-AI-DISCLOSURE", "platform")
    if "YouTube" in platform_set and music_ai:
        add("music_genai_metadata", "YouTube 音乐交付需记录 Fully/Partly Gen AI 分类。", "YOUTUBE-MUSIC-GENAI", "platform")
    if "TikTok" in platform_set and (realism in {"photorealistic", "mixed"} or real_person):
        add("visible_platform_label", "TikTok 要求写实人物/场景 AIGC 清晰标识。", "TIKTOK-AIGC", "platform")
    unknown = sorted(platform_set - KNOWN_PLATFORMS)
    if unknown or not platform_set:
        add("current_platform_policy_review", f"目标平台缺内置规则或未明确：{unknown or platforms}。", "manual", "platform")
    return rows


def _inside(root: str, path: str) -> bool:
    try:
        project = os.path.realpath(root)
        target = os.path.realpath(path)
        return os.path.commonpath((project, target)) == project and target != project
    except ValueError:
        return False


def _evidence(root: str, raw: str, label: str) -> dict[str, str]:
    path = (os.path.abspath(raw) if os.path.isabs(str(raw or ""))
            else os.path.abspath(os.path.join(root, str(raw or "")))) if raw else ""
    if not path or not _inside(root, path) or not os.path.isfile(path):
        raise ValueError(f"{label} 必须是已复制到作品根内的真实文件")
    return {"path": mv_utils.relpath(root, path), "sha256": mv_utils.content_hash(path)}


def _url_ok(raw: str) -> bool:
    parsed = urlparse(str(raw or ""))
    return parsed.scheme == "https" and bool(parsed.netloc)


def published_url_errors(raw: str, platforms: list[str]) -> list[str]:
    parsed = urlparse(str(raw or "").strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    errors = []
    if parsed.scheme != "https" or not host:
        return ["published_url 必须是具体平台的 https URL"]
    if host in {"localhost"} or host.endswith((".invalid", ".example", ".test", ".localhost")):
        errors.append("published_url 使用保留/测试域名，不能作为真实发布地址")
    known_suffixes = {
        suffix for platform in platforms for suffix in PLATFORM_HOST_SUFFIXES.get(str(platform), ())
    }
    if known_suffixes and not any(host == suffix or host.endswith("." + suffix) for suffix in known_suffixes):
        errors.append(f"published_url 域名 {host!r} 与声明平台 {platforms!r} 不匹配")
    if parsed.path in {"", "/"}:
        errors.append("published_url 缺具体作品路径/ID")
    return errors


def _bound_evidence_errors(root: str, evidence: Any, label: str) -> tuple[str, list[str]]:
    if not isinstance(evidence, dict):
        return "", [f"{label} 必须是 path+sha256 对象"]
    rel = str(evidence.get("path") or "")
    path = os.path.abspath(os.path.join(root, rel)) if rel and not os.path.isabs(rel) else ""
    if not path or not _inside(root, path) or not os.path.isfile(path):
        return "", [f"{label} 必须指向作品根内现存相对路径"]
    current = mv_utils.content_hash(path)
    if evidence.get("sha256") != current:
        return "", [f"{label} SHA-256 已过期"]
    return path, []


def _provider_evidence_format_errors(path: str, source: str) -> list[str]:
    if source == "platform_api_response":
        try:
            with open(path, encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, UnicodeError, json.JSONDecodeError):
            return ["platform_api_response 原始证据必须是可解析 JSON"]
        return [] if isinstance(payload, dict) and payload else ["platform_api_response JSON 不能为空"]
    try:
        with open(path, "rb") as handle:
            head = handle.read(12)
    except OSError:
        return ["platform_ui_export 原始证据不可读"]
    if not (head.startswith(b"\x89PNG\r\n\x1a\n") or head.startswith(b"\xff\xd8\xff") or head.startswith(b"%PDF-")):
        return ["platform_ui_export 必须是 PNG/JPEG/PDF 的真实导出或截图文件"]
    return []


def _json_pointer(document: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ValueError("上传 API 回执 JSON Pointer 无效")
    current = document
    for encoded in pointer.split("/")[1:]:
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif isinstance(current, list) and re.fullmatch(r"0|[1-9][0-9]*", token or ""):
            index = int(token)
            if index >= len(current):
                raise ValueError("上传 API 回执 JSON Pointer 未命中")
            current = current[index]
        else:
            raise ValueError("上传 API 回执 JSON Pointer 未命中")
    return current


def _aware_instant(value: Any, label: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed
    except ValueError:
        return None


def validate_requirement_evidence(
    root: str, evidence: Any, *, evidence_class: str,
    machine_label_method: str, provenance: dict[str, Any],
) -> list[str]:
    """Reject arbitrary bytes masquerading as a disclosure-action capture."""
    path, errors = _bound_evidence_errors(root, evidence, f"{evidence_class} requirement evidence")
    if errors or not path:
        return errors
    if evidence_class == "platform":
        source = "platform_api_response" if path.lower().endswith(".json") else "platform_ui_export"
        return _provider_evidence_format_errors(path, source)
    if evidence_class != "machine":
        return [f"未知 evidence_class={evidence_class!r}"]
    if machine_label_method == "c2pa":
        output = str(((provenance.get("c2pa") or {}).get("output")) or "")
        if not output or os.path.abspath(path) != os.path.abspath(os.path.join(root, output)):
            return ["C2PA machine evidence 必须是当前 provenance 复验的 signed output"]
        return []
    if machine_label_method == "platform_metadata":
        return _provider_evidence_format_errors(path, "platform_api_response")
    source = "platform_api_response" if path.lower().endswith(".json") else "platform_ui_export"
    return _provider_evidence_format_errors(path, source)


def validate_upload_receipt(
    root: str, receipt_path: str, *, platforms: list[str], operator: str,
    published_url: str, final_rel: str = "成片_MV.mp4",
    machine_label_method: str = "", provenance: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Validate a v3 receipt and the exact bytes represented as uploaded.

    ``machine_label_method`` and ``provenance`` are optional only for the
    completion controller's compatibility call.  In that path the method is
    recovered from the current release decision and provenance is reloaded
    from the project; the formal CLI passes both explicitly.
    """
    errors: list[str] = []
    payload = mv_utils.load_json(receipt_path, None)
    if not isinstance(payload, dict):
        return {}, ["上传回执必须是可解析的结构化 JSON，而不是任意占位文件"]
    if payload.get("kind") != UPLOAD_RECEIPT_KIND or payload.get("schema_version") != UPLOAD_RECEIPT_SCHEMA_VERSION:
        errors.append(f"上传回执必须是 schema v{UPLOAD_RECEIPT_SCHEMA_VERSION} {UPLOAD_RECEIPT_KIND}")
    source = str(payload.get("source") or "")
    if source not in UPLOAD_SOURCES:
        errors.append(f"上传回执 source 必须是 {sorted(UPLOAD_SOURCES)}")
    platform = str(payload.get("platform") or "")
    if platform not in platforms:
        errors.append("上传回执 platform 未覆盖 release_decision 声明平台")
    if str(payload.get("operator") or "").strip() != str(operator or "").strip():
        errors.append("上传回执 operator 与发布决策具名操作人不一致")
    if str(payload.get("published_url") or "").strip() != str(published_url or "").strip():
        errors.append("上传回执 published_url 与命令参数不一致")
    errors.extend(published_url_errors(published_url, platforms))
    remote_id = str(payload.get("remote_asset_id") or "").strip()
    if len(remote_id) < 3 or _PLACEHOLDER_ID.search(remote_id):
        errors.append("上传回执缺真实 remote_asset_id")
    uploaded_at = str(payload.get("uploaded_at") or "").strip()
    parsed_time = _aware_instant(uploaded_at, "uploaded_at")
    if parsed_time is None:
        errors.append("上传回执 uploaded_at 必须是带时区的 ISO-8601 时间")

    effective_method = str(machine_label_method or "").strip()
    if not effective_method:
        decision = mv_utils.load_json(os.path.join(root, "合规", "release_decision.json"), {})
        if isinstance(decision, dict):
            effective_method = str(decision.get("machine_label_method") or "").strip()
    if not effective_method:
        # Direct validators created before a release decision are the ordinary
        # (non-C2PA) path and therefore upload the current delivery MP4.
        effective_method = "platform_metadata"
    current_provenance = provenance
    if not isinstance(current_provenance, dict):
        loaded = mv_utils.load_json(os.path.join(root, "合规", "provenance.json"), {})
        current_provenance = loaded if isinstance(loaded, dict) else {}

    if effective_method == "c2pa":
        c2pa = current_provenance.get("c2pa") or {}
        expected_path = str(c2pa.get("output") or "") if isinstance(c2pa, dict) else ""
        expected_sha = str(c2pa.get("output_sha256") or "") if isinstance(c2pa, dict) else ""
        if not expected_path or not expected_sha:
            errors.append("上传回执无法绑定 C2PA：当前 provenance.c2pa 缺 output/output_sha256")
        else:
            expected_full = os.path.abspath(os.path.join(root, expected_path))
            current_sha = (
                mv_utils.content_hash(expected_full)
                if not os.path.isabs(expected_path) and _inside(root, expected_full)
                else ""
            )
            if not current_sha or current_sha != expected_sha:
                errors.append("当前 provenance.c2pa.output 缺失、越界或 SHA-256 已过期")
    else:
        expected_path = final_rel
        expected_sha = mv_utils.content_hash(os.path.join(root, final_rel))
        if not expected_sha:
            errors.append("上传回执无法绑定当前 成片_MV.mp4")

    _uploaded_path, uploaded_errors = _bound_evidence_errors(
        root, payload.get("uploaded_asset"), "上传回执 uploaded_asset",
    )
    errors.extend(uploaded_errors)
    uploaded_asset = payload.get("uploaded_asset") or {}
    if isinstance(uploaded_asset, dict):
        if uploaded_asset.get("path") != expected_path:
            if effective_method == "c2pa":
                errors.append("使用 C2PA 机器标识时，uploaded_asset.path 必须精确等于当前 provenance.c2pa.output")
            else:
                errors.append("非 C2PA 发布的 uploaded_asset.path 必须是当前 成片_MV.mp4")
        if uploaded_asset.get("sha256") != expected_sha:
            if effective_method == "c2pa":
                errors.append("使用 C2PA 机器标识时，uploaded_asset.sha256 必须精确等于当前 provenance.c2pa.output_sha256")
            else:
                errors.append("非 C2PA 发布的 uploaded_asset.sha256 未绑定当前 成片_MV.mp4")
    provider_path, provider_errors = _bound_evidence_errors(
        root, payload.get("provider_evidence"), "上传回执 provider_evidence",
    )
    errors.extend(provider_errors)
    if provider_path and source in UPLOAD_SOURCES:
        if os.path.abspath(provider_path) == os.path.abspath(receipt_path):
            errors.append("上传回执 JSON 不能自称为原始平台证据")
        else:
            provider_format_errors = _provider_evidence_format_errors(provider_path, source)
            errors.extend(provider_format_errors)
            if source == "platform_api_response" and not provider_format_errors:
                try:
                    with open(provider_path, encoding="utf-8") as handle:
                        document = json.load(handle)
                    bindings = payload.get("provider_bindings") or {}
                    if not isinstance(bindings, dict):
                        raise ValueError("上传 API 回执缺 provider_bindings")
                    observed_id = str(_json_pointer(
                        document, str((bindings.get("remote_asset_id") or {}).get("json_pointer") or "")
                    )).strip()
                    observed_url = str(_json_pointer(
                        document, str((bindings.get("published_url") or {}).get("json_pointer") or "")
                    )).strip()
                    time_binding = bindings.get("uploaded_at") or {}
                    observed_time_raw = _json_pointer(document, str(time_binding.get("json_pointer") or ""))
                    observed_time = _aware_instant(observed_time_raw, "provider uploaded_at")
                    if observed_id != remote_id:
                        errors.append("上传 API 原始响应 remote_asset_id 与回执不一致")
                    if observed_url != str(published_url):
                        errors.append("上传 API 原始响应 published_url 与回执不一致")
                    if observed_time is None or parsed_time is None or abs(
                        (observed_time - parsed_time).total_seconds()
                    ) > 1:
                        errors.append("上传 API 原始响应 uploaded_at 与回执不一致")
                except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                    errors.append(str(exc))
            elif source == "platform_ui_export":
                observation = payload.get("ui_observation") or {}
                observed_at = _aware_instant(observation.get("observed_at"), "observed_at") if isinstance(observation, dict) else None
                if not (
                    isinstance(observation, dict)
                    and completion._valid_reviewer(observation.get("reviewer"))
                    and str(observation.get("reviewer") or "").strip() == str(operator or "").strip()
                    and completion._valid_notes(observation.get("notes"))
                    and observation.get("remote_asset_id") == remote_id
                    and observation.get("published_url") == str(published_url)
                    and observed_at is not None
                ):
                    errors.append("platform_ui_export 只能作为具名 UI 观察：需同一 operator、notes、时间、remote id 与 URL")
    return dict(payload), errors


def upload_receipt_claim(payload: dict[str, Any]) -> dict[str, Any]:
    """Project the stable v3 fields embedded in a release decision."""
    if not isinstance(payload, dict) or not payload:
        return {}
    asset = payload.get("uploaded_asset") or {}
    return {
        **{
            key: payload.get(key) for key in (
                "kind", "schema_version", "source", "platform", "remote_asset_id",
                "operator", "uploaded_at", "published_url",
            )
        },
        "uploaded_asset": {
            "path": asset.get("path") if isinstance(asset, dict) else None,
            "sha256": asset.get("sha256") if isinstance(asset, dict) else None,
        },
    }


def _split_values(rows: list[str]) -> list[str]:
    return list(dict.fromkeys(
        value.strip()
        for row in rows
        for value in str(row or "").split(",")
        if value.strip()
    ))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project_root")
    ap.add_argument("--platform", action="append", default=[])
    ap.add_argument("--territory", action="append", default=[])
    ap.add_argument("--operator", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--platform-declaration-status", choices=STATUS_CHOICES, default="pending")
    ap.add_argument("--visible-label-status", choices=STATUS_CHOICES, default="pending")
    ap.add_argument("--music-metadata-status", choices=STATUS_CHOICES, default="pending")
    ap.add_argument("--platform-policy-review-status", choices=STATUS_CHOICES, default="pending")
    ap.add_argument("--machine-label-method", choices=MACHINE_LABEL_METHODS, default="pending")
    ap.add_argument("--platform-evidence", default="")
    ap.add_argument("--machine-evidence", default="")
    ap.add_argument("--submission-status", choices=("uploaded", "not_uploaded"), default="not_uploaded")
    ap.add_argument("--upload-receipt", default="")
    ap.add_argument("--published-url", default="")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    disclosure_rel = "合规/ai_usage.json"
    provenance_rel = "合规/provenance.json"
    final_rel = "成片_MV.mp4"
    disclosure = mv_utils.load_json(os.path.join(root, disclosure_rel), None)
    provenance = mv_utils.load_json(os.path.join(root, provenance_rel), None)
    if not isinstance(disclosure, dict) or disclosure.get("kind") != "mv_ai_usage":
        print("[err] 缺当前 ai_usage disclosure", file=sys.stderr)
        return 1
    if not isinstance(provenance, dict) or provenance.get("kind") != "mv_provenance":
        print("[err] 缺当前 provenance", file=sys.stderr)
        return 1
    if not os.path.isfile(os.path.join(root, final_rel)):
        print("[err] 缺 成片_MV.mp4", file=sys.stderr)
        return 1

    platforms = _split_values(args.platform or [str(disclosure.get("publish_target") or "")])
    platforms = [row for row in platforms if row and row not in {"未定", "跨平台"}]
    territories = _split_values(args.territory or disclosure.get("territories") or [])
    requirements = applicable_requirements(disclosure, platforms, territories)
    status_by_id = {
        "platform_ai_declaration": args.platform_declaration_status,
        "visible_platform_label": args.visible_label_status,
        "music_genai_metadata": args.music_metadata_status,
        "current_platform_policy_review": args.platform_policy_review_status,
        "machine_readable_disclosure": "completed" if args.machine_label_method != "pending" else "pending",
    }
    errors: list[str] = []
    # A release decision is downstream of the named, current final review.  Do
    # not create a ready/uploaded decision that handoff will only reject later.
    for stage in ("compose", "disclosure", "provenance", "review"):
        health = completion.stage_health(root, stage)
        errors.extend(f"{stage}: {message}" for message in health["errors"])
    platform_evidence: dict[str, str] = {}
    machine_evidence: dict[str, str] = {}
    upload_evidence: dict[str, str] = {}
    upload_claim: dict[str, Any] = {}
    needs_platform_evidence = any(row["evidence_class"] == "platform" for row in requirements)
    needs_machine_evidence = any(row["evidence_class"] == "machine" for row in requirements)
    try:
        if needs_platform_evidence:
            platform_evidence = _evidence(root, args.platform_evidence, "--platform-evidence")
        if needs_machine_evidence:
            machine_evidence = _evidence(root, args.machine_evidence, "--machine-evidence")
        if args.submission_status == "uploaded":
            upload_evidence = _evidence(root, args.upload_receipt, "--upload-receipt")
    except ValueError as exc:
        errors.append(str(exc))

    for row in requirements:
        row["status"] = status_by_id.get(row["id"], "pending")
        row["evidence"] = machine_evidence if row["evidence_class"] == "machine" else platform_evidence
        if row["status"] != "completed":
            errors.append(f"required action pending: {row['id']}")
        elif row.get("evidence"):
            errors.extend(validate_requirement_evidence(
                root, row["evidence"], evidence_class=row["evidence_class"],
                machine_label_method=args.machine_label_method, provenance=provenance,
            ))

    if args.machine_label_method == "c2pa" and needs_machine_evidence:
        c2pa = provenance.get("c2pa") or {}
        required_truths = ("embedded", "structurally_valid", "signature_valid", "trusted", "timestamped")
        missing = [key for key in required_truths if c2pa.get(key) is not True]
        if missing or c2pa.get("certificate_profile") != "production":
            errors.append(f"C2PA 不能作为生产机器标识证据：missing={missing}, profile={c2pa.get('certificate_profile')}")
    if args.submission_status != "uploaded":
        errors.append("尚无真实上传回执")
    if args.submission_status == "uploaded":
        receipt_path = os.path.join(root, upload_evidence.get("path") or "") if upload_evidence else ""
        if receipt_path:
            upload_claim, receipt_errors = validate_upload_receipt(
                root, receipt_path, platforms=platforms, operator=args.operator,
                published_url=args.published_url, final_rel=final_rel,
                machine_label_method=args.machine_label_method, provenance=provenance,
            )
            errors.extend(receipt_errors)
        else:
            errors.append("uploaded 状态缺结构化上传回执")
        errors.extend(published_url_errors(args.published_url, platforms))
    if not platforms:
        errors.append("必须明确至少一个具体发布平台")
    if not territories:
        errors.append("必须明确至少一个发布法域")
    if not completion._valid_reviewer(args.operator):
        errors.append("必须提供真实具名 --operator")
    if not completion._valid_notes(args.notes):
        errors.append("必须提供非空 --notes")
    errors = list(dict.fromkeys(errors))

    input_rows = [
        final_rel, disclosure_rel, provenance_rel,
        "生产数据/review/review_receipt.json",
    ]
    uploaded_asset = upload_claim.get("uploaded_asset") if upload_claim else {}
    if isinstance(uploaded_asset, dict) and not errors:
        uploaded_rel = str(uploaded_asset.get("path") or "")
        if uploaded_rel and uploaded_rel not in input_rows:
            input_rows.append(uploaded_rel)
    inputs = tuple(input_rows)
    payload = {
        "schema_version": 1,
        "kind": "mv_release_decision",
        "ruleset_version": RULESET_VERSION,
        "evaluated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "decision": "ready_for_handoff" if not errors else "blocked",
        "operator": str(args.operator).strip(),
        "notes": str(args.notes).strip(),
        "platforms": platforms,
        "territories": territories,
        "submission": {
            "status": args.submission_status,
            "published_url": args.published_url or None,
            "receipt": upload_evidence,
            "receipt_claim": upload_receipt_claim(upload_claim),
        },
        "machine_label_method": args.machine_label_method,
        "requirements": requirements,
        "errors": errors,
        "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in inputs},
        "sources": {key: SOURCES[key] for key in sorted({row["source"] for row in requirements}) if key in SOURCES},
    }
    out = os.path.join(root, "合规", "release_decision.json")
    mv_utils.write_json(out, payload)
    if errors:
        print("[block] release decision：" + "；".join(errors), file=sys.stderr)
        return 1
    print(f"[ok] release decision → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
