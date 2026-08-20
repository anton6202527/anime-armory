#!/usr/bin/env python3
"""Build a SHA-bound comic delivery/release verdict.

Technical completion, production review and public/commercial release are kept
as separate states.  The script only reports and writes evidence; it never
publishes or changes ``_进度.md``.
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


COMIC_LIB = Path(__file__).resolve().parents[1] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
from contracts import sha256_file, stable_sha256, stage_inputs_fingerprint  # noqa: E402
from platform_profiles import profile_for_platform, validate_manifest  # noqa: E402
from settings import get_setting  # noqa: E402

REVIEW_SCRIPTS = Path(__file__).resolve().parents[1] / "comic-review" / "scripts"
if str(REVIEW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(REVIEW_SCRIPTS))
try:  # Kept optional for a clean, independently distributable old project.
    from finding_dispositions import summarize as summarize_finding_dispositions  # noqa: E402
except ImportError:  # pragma: no cover - compatibility with pre-ledger bundles
    summarize_finding_dispositions = None


PROFILES = ("internal", "digital", "print", "commercial")
PUBLIC_PROFILES = ("digital", "print", "commercial")
MEDIUMS = ("web_images", "print_pdf", "epub_fxl")
USAGES = ("internal", "public", "commercial")
LEGACY_PROFILE_AXES = {
    "internal": ("web_images", "internal"),
    "digital": ("web_images", "public"),
    "print": ("print_pdf", "public"),
    "commercial": ("web_images", "commercial"),
}
RIGHTS_CLEARED_VALUES = {
    "authorized",
    "cleared",
    "generated_original",
    "licensed",
    "not_applicable",
    "open_license",
    "original",
    "owned",
    "public_domain",
    "self_created",
    "self_owned",
    "不适用",
    "公共领域",
    "公版",
    "原创",
    "已授权",
    "已清权",
    "开源许可",
    "自制",
    "自有",
}


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def issue(
    code: str,
    reason: str,
    *,
    domain: str,
    blocking_profiles: tuple[str, ...] = PROFILES,
    blocking_mediums: tuple[str, ...] = (),
    blocking_usages: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "code": code,
        "reason": reason,
        "domain": domain,
        "blocking_profiles": list(blocking_profiles),
        "blocking_mediums": list(blocking_mediums),
        "blocking_usages": list(blocking_usages),
    }


def resolve_delivery_axes(
    profile: str = "internal",
    *,
    medium: str | None = None,
    usage: str | None = None,
) -> tuple[str, str, str]:
    if profile not in PROFILES:
        raise ValueError(f"unknown legacy profile: {profile}")
    legacy_medium, legacy_usage = LEGACY_PROFILE_AXES[profile]
    resolved_medium = medium or legacy_medium
    resolved_usage = usage or legacy_usage
    if resolved_medium not in MEDIUMS:
        raise ValueError(f"medium must be one of {MEDIUMS}")
    if resolved_usage not in USAGES:
        raise ValueError(f"usage must be one of {USAGES}")
    axis_id = f"{resolved_medium}+{resolved_usage}"
    return resolved_medium, resolved_usage, axis_id


def issue_blocks(item: Mapping[str, Any], medium: str, usage: str) -> bool:
    explicit_mediums = set(item.get("blocking_mediums") or [])
    explicit_usages = set(item.get("blocking_usages") or [])
    if explicit_mediums or explicit_usages:
        return (not explicit_mediums or medium in explicit_mediums) and (not explicit_usages or usage in explicit_usages)
    profiles = set(item.get("blocking_profiles") or [])
    if profiles == set(PROFILES) or "internal" in profiles:
        return True
    if usage == "internal":
        return False
    if medium == "print_pdf" and "print" in profiles:
        return True
    if medium in {"web_images", "epub_fxl"} and "digital" in profiles:
        return True
    return usage == "commercial" and "commercial" in profiles


def rights_value_is_cleared(value: Any) -> bool:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return normalized in RIGHTS_CLEARED_VALUES


def normalize_image_format(value: Any) -> str:
    normalized = str(value or "").strip().lower().lstrip(".")
    return {"jpeg": "jpg", "tiff": "tif"}.get(normalized, normalized)


def inspect_pdf(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    media_boxes = [
        {"width": float(width), "height": float(height)}
        for width, height in re.findall(
            rb"/MediaBox\s*\[\s*0(?:\.0+)?\s+0(?:\.0+)?\s+([0-9.]+)\s+([0-9.]+)\s*\]",
            data,
        )
    ]
    return {
        "header_valid": data.startswith(b"%PDF-"),
        "eof_marker_present": b"%%EOF" in data[-1024:],
        "page_count": data.count(b"/Type /Page") - data.count(b"/Type /Pages"),
        "image_object_count": data.count(b"/Subtype /Image"),
        "font_object_count": data.count(b"/Type /Font"),
        "icc_object_present": b"/ICCBased" in data or b"/OutputIntent" in data,
        "media_boxes_points": media_boxes,
    }


def inspect_epub(path: Path) -> dict[str, Any]:
    result = {
        "zip_valid": False,
        "mimetype_valid": False,
        "mimetype_first": False,
        "mimetype_stored": False,
        "container_present": False,
        "container_valid": False,
        "package_document": "",
        "package_documents": [],
        "package_xml_valid": False,
        "manifest_item_count": 0,
        "spine_item_ids": [],
        "spine_hrefs": [],
        "spine_valid": False,
        "nav_item_href": "",
        "nav_present": False,
        "nav_document_valid": False,
        "content_documents": [],
        "content_documents_valid": False,
        "content_image_count": 0,
        "content_images_missing_alt_attribute": 0,
        "all_content_images_have_alt_attribute": False,
        "rendition_layout": "",
        "fixed_layout": False,
        "package_title": "",
        "package_language": "",
        "package_accessibility_metadata": {},
        "errors": [],
    }

    def local_name(tag: Any) -> str:
        return str(tag or "").rsplit("}", 1)[-1]

    def member_path(base: str, href: str) -> str:
        raw_path = unquote(urlsplit(str(href or "")).path)
        normalized = posixpath.normpath(posixpath.join(base, raw_path))
        if not raw_path or normalized.startswith("../") or normalized.startswith("/"):
            return ""
        return normalized

    try:
        with zipfile.ZipFile(path) as archive:
            result["zip_valid"] = archive.testzip() is None
            entries = archive.infolist()
            names = {item.filename for item in entries}
            result["mimetype_first"] = bool(entries and entries[0].filename == "mimetype")
            mimetype_entry = next((item for item in entries if item.filename == "mimetype"), None)
            result["mimetype_stored"] = bool(mimetype_entry and mimetype_entry.compress_type == zipfile.ZIP_STORED)
            result["mimetype_valid"] = bool(
                mimetype_entry
                and result["mimetype_first"]
                and result["mimetype_stored"]
                and archive.read("mimetype") == b"application/epub+zip"
            )
            result["container_present"] = "META-INF/container.xml" in names
            if not result["container_present"]:
                result["errors"].append("META-INF/container.xml missing")
                return result
            try:
                container_root = ET.fromstring(archive.read("META-INF/container.xml"))
            except (ET.ParseError, KeyError) as exc:
                result["errors"].append(f"container XML invalid: {exc}")
                return result
            rootfiles = [node for node in container_root.iter() if local_name(node.tag) == "rootfile"]
            package_doc = str(rootfiles[0].attrib.get("full-path") or "") if rootfiles else ""
            package_doc = member_path("", package_doc)
            result["package_document"] = package_doc
            result["container_valid"] = bool(package_doc and package_doc in names)
            result["package_documents"] = [package_doc] if result["container_valid"] else []
            if not result["container_valid"]:
                result["errors"].append("container rootfile does not resolve to a real OPF")
                return result
            try:
                package_root = ET.fromstring(archive.read(package_doc))
                result["package_xml_valid"] = local_name(package_root.tag) == "package"
            except (ET.ParseError, KeyError) as exc:
                result["errors"].append(f"package OPF invalid: {exc}")
                return result
            if not result["package_xml_valid"]:
                result["errors"].append("OPF root is not package")
                return result

            package_base = posixpath.dirname(package_doc)
            manifest_items: dict[str, dict[str, str]] = {}
            for node in package_root.iter():
                if local_name(node.tag) != "item":
                    continue
                item_id = str(node.attrib.get("id") or "")
                href = str(node.attrib.get("href") or "")
                resolved = member_path(package_base, href)
                if item_id and resolved:
                    manifest_items[item_id] = {
                        "href": resolved,
                        "media_type": str(node.attrib.get("media-type") or ""),
                        "properties": str(node.attrib.get("properties") or ""),
                    }
            result["manifest_item_count"] = len(manifest_items)
            spine_ids = [
                str(node.attrib.get("idref") or "")
                for node in package_root.iter()
                if local_name(node.tag) == "itemref" and str(node.attrib.get("idref") or "")
            ]
            spine_items = [manifest_items.get(item_id) for item_id in spine_ids]
            result["spine_item_ids"] = spine_ids
            result["spine_hrefs"] = [str(item.get("href") or "") for item in spine_items if item]
            result["spine_valid"] = bool(
                spine_ids
                and len(spine_items) == len(spine_ids)
                and all(
                    item
                    and item.get("media_type") == "application/xhtml+xml"
                    and item.get("href") in names
                    for item in spine_items
                )
            )

            nav_item = next(
                (
                    item for item in manifest_items.values()
                    if "nav" in str(item.get("properties") or "").split()
                    and item.get("media_type") == "application/xhtml+xml"
                ),
                None,
            )
            result["nav_item_href"] = str((nav_item or {}).get("href") or "")
            result["nav_present"] = bool(result["nav_item_href"] and result["nav_item_href"] in names)
            if result["nav_present"]:
                try:
                    nav_root = ET.fromstring(archive.read(result["nav_item_href"]))
                    result["nav_document_valid"] = any(local_name(node.tag) == "nav" for node in nav_root.iter())
                except (ET.ParseError, KeyError):
                    result["nav_document_valid"] = False

            content_documents: list[str] = []
            content_valid = bool(result["spine_valid"])
            image_count = 0
            missing_alt = 0
            for item in spine_items:
                if not item:
                    content_valid = False
                    continue
                href = str(item.get("href") or "")
                content_documents.append(href)
                try:
                    content_root = ET.fromstring(archive.read(href))
                except (ET.ParseError, KeyError):
                    content_valid = False
                    continue
                if local_name(content_root.tag) != "html":
                    content_valid = False
                for node in content_root.iter():
                    if local_name(node.tag) == "img":
                        image_count += 1
                        if "alt" not in node.attrib:
                            missing_alt += 1
            result["content_documents"] = content_documents
            result["content_documents_valid"] = bool(content_documents and content_valid)
            result["content_image_count"] = image_count
            result["content_images_missing_alt_attribute"] = missing_alt
            result["all_content_images_have_alt_attribute"] = bool(result["content_documents_valid"] and missing_alt == 0)

            accessibility: dict[str, list[str]] = {}
            for node in package_root.iter():
                name = local_name(node.tag)
                text_value = str(node.text or "").strip()
                if name == "title" and not result["package_title"]:
                    result["package_title"] = text_value
                elif name == "language" and not result["package_language"]:
                    result["package_language"] = text_value
                if name != "meta":
                    continue
                prop = str(node.attrib.get("property") or node.attrib.get("name") or "").strip()
                value = text_value or str(node.attrib.get("content") or "").strip()
                canonical = prop.rsplit(":", 1)[-1].lower()
                if canonical == "layout" and prop.lower().endswith("rendition:layout"):
                    result["rendition_layout"] = value
                if canonical in {
                    "accessmode", "accessmodesufficient", "accessibilityfeature",
                    "accessibilityhazard", "accessibilitysummary",
                } and value:
                    accessibility.setdefault(canonical, []).append(value)
            result["fixed_layout"] = result["rendition_layout"] == "pre-paginated"
            result["package_accessibility_metadata"] = accessibility
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as exc:
        result["errors"].append(str(exc))
    return result


def _manifest_artifact_path(root: Path, raw_path: Any) -> tuple[Path | None, str]:
    value = str(raw_path or "").strip()
    if not value:
        return None, ""
    root_resolved = root.resolve()
    candidate = Path(value).expanduser()
    candidate = candidate.resolve() if candidate.is_absolute() else (root_resolved / candidate).resolve()
    try:
        relative = candidate.relative_to(root_resolved)
    except ValueError:
        return None, value
    return candidate, str(relative)


def rendered_artifacts(root: Path, manifest: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    artifacts_by_path: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    try:
        from PIL import Image
    except ImportError:
        Image = None

    failed_paths: set[str] = set()
    for section in ("pages", "rendered"):
        entries = manifest.get(section) or []
        if not isinstance(entries, list):
            issues.append(issue("export_artifact_list_invalid", f"manifest.{section} 必须是数组。", domain="technical"))
            continue
        for index, item in enumerate(entries):
            if not isinstance(item, Mapping) or not str(item.get("path") or "").strip():
                issues.append(
                    issue(
                        "export_artifact_entry_invalid",
                        f"manifest.{section}[{index}] 缺有效 path。",
                        domain="technical",
                    )
                )
                continue
            path, relative = _manifest_artifact_path(root, item.get("path"))
            if path is None:
                issues.append(
                    issue(
                        "export_artifact_outside_project",
                        f"manifest.{section}[{index}] 路径不在作品根内：{item.get('path')}",
                        domain="technical",
                    )
                )
                continue
            if not path.is_file():
                issues.append(issue("rendered_artifact_missing", relative, domain="technical"))
                continue

            artifact = artifacts_by_path.get(relative)
            if artifact is None and relative not in failed_paths:
                if Image is None:
                    issues.append(
                        issue(
                            "image_decoder_unavailable",
                            "缺 Pillow，无法证明最终图片可完整解码。",
                            domain="technical",
                        )
                    )
                    failed_paths.add(relative)
                    continue
                try:
                    with Image.open(path) as image:
                        detected_format = normalize_image_format(image.format)
                        image.load()
                        actual_size = {"width": int(image.width), "height": int(image.height)}
                except (OSError, ValueError, SyntaxError) as exc:
                    issues.append(
                        issue(
                            "export_artifact_decode_failed",
                            f"{relative} 不是可完整解码的图片：{exc}",
                            domain="technical",
                        )
                    )
                    failed_paths.add(relative)
                    continue
                if not detected_format:
                    issues.append(
                        issue(
                            "export_artifact_format_unknown",
                            f"{relative} 无法识别实际图片格式。",
                            domain="technical",
                        )
                    )
                    failed_paths.add(relative)
                    continue
                artifact = {
                    "path": relative,
                    "sha256": sha256_file(path),
                    "size": path.stat().st_size,
                    "dimensions": actual_size,
                    "format": detected_format,
                    "manifest_sections": [],
                }
                artifacts_by_path[relative] = artifact
            if artifact is None:
                continue
            if section not in artifact["manifest_sections"]:
                artifact["manifest_sections"].append(section)

            declared_size = item.get("size")
            if declared_size is not None and not isinstance(declared_size, Mapping):
                issues.append(
                    issue(
                        "export_artifact_dimensions_invalid",
                        f"{relative} 的 manifest size 必须是 width/height 对象。",
                        domain="technical",
                    )
                )
            elif isinstance(declared_size, Mapping):
                for axis in ("width", "height"):
                    if declared_size.get(axis) in (None, ""):
                        continue
                    try:
                        expected = int(declared_size[axis])
                    except (TypeError, ValueError):
                        issues.append(
                            issue(
                                "export_artifact_dimensions_invalid",
                                f"{relative} 的 manifest {axis} 不是有效整数。",
                                domain="technical",
                            )
                        )
                        continue
                    actual = int(artifact["dimensions"][axis])
                    if expected != actual:
                        issues.append(
                            issue(
                                "export_artifact_dimensions_mismatch",
                                f"{relative} manifest {axis}={expected}，实际为 {actual}。",
                                domain="technical",
                            )
                        )

            declared_format = normalize_image_format(item.get("format"))
            if declared_format and declared_format != artifact["format"]:
                issues.append(
                    issue(
                        "export_artifact_format_mismatch",
                        f"{relative} manifest format={declared_format}，实际为 {artifact['format']}。",
                        domain="technical",
                    )
                )
    documents = manifest.get("documents") or []
    if not isinstance(documents, list):
        issues.append(issue("export_document_list_invalid", "manifest.documents 必须是数组。", domain="technical"))
        documents = []
    for index, item in enumerate(documents):
        if not isinstance(item, Mapping) or not str(item.get("path") or "").strip():
            issues.append(issue("export_document_entry_invalid", f"manifest.documents[{index}] 缺有效 path。", domain="technical"))
            continue
        path, relative = _manifest_artifact_path(root, item.get("path"))
        if path is None:
            issues.append(issue("export_artifact_outside_project", f"manifest.documents[{index}] 路径不在作品根内。", domain="technical"))
            continue
        if not path.is_file():
            issues.append(issue("rendered_document_missing", relative, domain="technical"))
            continue
        fmt = str(item.get("format") or path.suffix.lstrip(".")).strip().lower()
        if fmt not in {"pdf", "epub"}:
            issues.append(issue("export_document_format_unsupported", f"{relative} format={fmt or 'missing'}；不能冒充 PDF/EPUB 交付。", domain="technical"))
            continue
        artifact: dict[str, Any] = {
            "path": relative,
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
            "format": fmt,
            "artifact_type": "document",
            "manifest_sections": ["documents"],
        }
        declared_sha = str(item.get("sha256") or "")
        if declared_sha and declared_sha != artifact["sha256"]:
            issues.append(issue("export_document_sha_mismatch", f"{relative} 与 manifest 记录 SHA 不一致。", domain="technical"))
        if fmt == "pdf":
            structural = inspect_pdf(path)
            artifact["pdf_structural_evidence"] = structural
            artifact["page_count"] = structural["page_count"]
            if not structural["header_valid"] or not structural["eof_marker_present"] or structural["page_count"] <= 0:
                issues.append(issue("pdf_structural_validation_failed", f"{relative} 缺有效 PDF header/EOF/page objects。", domain="technical"))
            declared_pages = item.get("page_count")
            if declared_pages not in (None, ""):
                try:
                    declared_count = int(declared_pages)
                except (TypeError, ValueError):
                    declared_count = -1
                if declared_count != structural["page_count"]:
                    issues.append(issue("pdf_page_count_mismatch", f"{relative} manifest page_count={declared_pages}，结构扫描为 {structural['page_count']}。", domain="technical"))
        else:
            structural = inspect_epub(path)
            artifact["epub_structural_evidence"] = structural
            structural_requirements = {
                "zip": bool(structural.get("zip_valid")),
                "mimetype-first-stored": bool(structural.get("mimetype_valid")),
                "container-rootfile": bool(structural.get("container_valid")),
                "opf": bool(structural.get("package_xml_valid")),
                "manifest-spine": bool(structural.get("manifest_item_count") and structural.get("spine_valid")),
                "nav": bool(structural.get("nav_present") and structural.get("nav_document_valid")),
                "xhtml-content": bool(structural.get("content_documents_valid")),
                "fixed-layout": bool(structural.get("fixed_layout")),
                "img-alt-attribute": bool(structural.get("all_content_images_have_alt_attribute")),
            }
            failed = [name for name, passed in structural_requirements.items() if not passed]
            if failed:
                issues.append(issue(
                    "epub_structural_validation_failed",
                    f"{relative} EPUB 结构预检失败：{', '.join(failed)}；合同自声明不能替代真实 ZIP/container/OPF/spine/nav/XHTML 解析。",
                    domain="technical", blocking_mediums=("epub_fxl",),
                ))
        artifacts_by_path[relative] = artifact
    platform_assets = manifest.get("platform_assets") if isinstance(manifest.get("platform_assets"), Mapping) else {}
    for asset_name, item in platform_assets.items():
        if not isinstance(item, Mapping):
            issues.append(issue("platform_asset_entry_invalid", f"platform_assets.{asset_name} 必须是对象。", domain="technical"))
            continue
        path, relative = _manifest_artifact_path(root, item.get("path"))
        if path is None or not path.is_file():
            issues.append(issue("platform_asset_missing", f"platform_assets.{asset_name} 缺文件或路径越界。", domain="technical"))
            continue
        if Image is None:
            issues.append(issue("image_decoder_unavailable", "缺 Pillow，无法证明平台缩略图可完整解码。", domain="technical"))
            continue
        try:
            with Image.open(path) as image:
                detected_format = normalize_image_format(image.format)
                image.load()
                dimensions = {"width": image.width, "height": image.height}
        except (OSError, ValueError, SyntaxError) as exc:
            issues.append(issue("platform_asset_decode_failed", f"{relative} 不可解码：{exc}", domain="technical"))
            continue
        current_sha = sha256_file(path)
        if str(item.get("sha256") or "") != current_sha:
            issues.append(issue("platform_asset_sha_mismatch", f"{relative} 与 manifest 登记 SHA 不一致。", domain="technical"))
        existing = artifacts_by_path.get(relative)
        if existing:
            if "platform_assets" not in existing["manifest_sections"]:
                existing["manifest_sections"].append("platform_assets")
            existing.setdefault("platform_asset_names", []).append(str(asset_name))
        else:
            artifacts_by_path[relative] = {
                "path": relative, "sha256": current_sha, "size": path.stat().st_size,
                "dimensions": dimensions, "format": detected_format,
                "artifact_type": "platform_asset", "manifest_sections": ["platform_assets"],
                "platform_asset_names": [str(asset_name)],
            }
    return list(artifacts_by_path.values()), issues


def platform_release_checks(
    root: Path,
    manifest: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    medium: str = "web_images",
) -> tuple[list[dict[str, Any]], str, dict[str, Any]]:
    """Recheck the current target platform from verified image facts.

    Compose-time findings may have been generated under a draft/demo usage or
    an earlier target platform.  Release therefore recompiles the profile with
    publish-like severity and replaces declared dimensions/formats with facts
    obtained from decoding the current files.
    """
    target_platform = get_setting(str(root), "目标平台", str(manifest.get("target_platform") or "通用"))
    platform_profile = profile_for_platform(target_platform)
    if medium == "print_pdf":
        return [], target_platform, platform_profile.to_manifest()
    verified = dict(manifest)
    artifact_map = {str(item.get("path") or ""): item for item in artifacts}
    for section in ("pages", "rendered"):
        verified_items: list[dict[str, Any]] = []
        entries = manifest.get(section) or []
        if not isinstance(entries, list):
            entries = []
        for item in entries:
            if not isinstance(item, Mapping):
                continue
            normalized = dict(item)
            _path, relative = _manifest_artifact_path(root, item.get("path"))
            artifact = artifact_map.get(relative)
            if artifact:
                normalized["size"] = dict(artifact.get("dimensions") or {})
                normalized["format"] = str(artifact.get("format") or "")
                normalized["path"] = relative
            verified_items.append(normalized)
        verified[section] = verified_items

    findings = validate_manifest(root, verified, platform_profile, usage="发布候选")
    findings_as_issues: list[dict[str, Any]] = []
    for finding in findings:
        blocking = PUBLIC_PROFILES if str(finding.get("severity") or "").lower() == "block" else ()
        reason = str(finding.get("reason") or "")
        suggested_fix = str(finding.get("suggested_fix") or "").strip()
        if suggested_fix:
            reason = f"{reason} 修复：{suggested_fix}"
        findings_as_issues.append(
            issue(
                str(finding.get("code") or "platform_profile"),
                reason,
                domain="platform",
                blocking_profiles=blocking,
                blocking_mediums=("web_images", "epub_fxl") if blocking else (),
                blocking_usages=("public", "commercial") if blocking else (),
            )
        )
    return findings_as_issues, target_platform, platform_profile.to_manifest()


def artifact_binding(artifacts: list[dict[str, Any]]) -> list[dict[str, str]]:
    return sorted(
        ({"path": str(item.get("path") or ""), "sha256": str(item.get("sha256") or "")} for item in artifacts),
        key=lambda item: item["path"],
    )


def finding_disposition_status(root: Path, chapter: str) -> dict[str, Any]:
    if summarize_finding_dispositions is None:
        return {
            "kind": "comic_finding_disposition_summary",
            "chapter": chapter,
            "available": False,
            "total": 0,
            "currently_resolved": 0,
            "unresolved_count": 0,
        }
    summary = dict(summarize_finding_dispositions(root, chapter))
    summary["available"] = True
    return summary


def finding_disposition_binding(root: Path, chapter: str) -> dict[str, Any]:
    summary = finding_disposition_status(root, chapter)
    source = root / str(summary.get("source") or f"生产数据/gate_findings_review_{chapter}.json")
    ledger = root / str(summary.get("ledger") or f"生产数据/finding_dispositions/{chapter}.jsonl")
    return {
        "summary_sha256": stable_sha256(summary),
        "source_path": str(source.relative_to(root)) if source.is_absolute() else str(source),
        "source_sha256": sha256_file(source) if source.is_file() else "",
        "ledger_path": str(ledger.relative_to(root)) if ledger.is_absolute() else str(ledger),
        "ledger_sha256": sha256_file(ledger) if ledger.is_file() else "",
        "total": int(summary.get("total") or 0),
        "currently_resolved": int(summary.get("currently_resolved") or 0),
        "unresolved_count": int(summary.get("unresolved_count") or len(summary.get("unresolved") or [])),
    }


def check_finding_dispositions(summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not summary.get("available"):
        return [issue(
            "finding_disposition_engine_unavailable",
            "warning 处置账能力不可用；内部报告保留提示，公开/商用不能在未核对 warning 时签收。",
            domain="release",
            blocking_profiles=PUBLIC_PROFILES,
            blocking_usages=("public", "commercial"),
        )]
    integrity_errors = int(summary.get("ledger_integrity_error_count") or 0)
    if integrity_errors:
        return [issue(
            "finding_disposition_ledger_integrity_failed",
            f"finding disposition ledger 有 {integrity_errors} 个事件未通过 schema/chapter/status/sequence/hash-chain 完整性校验。",
            domain="release",
            blocking_profiles=PUBLIC_PROFILES,
            blocking_usages=("public", "commercial"),
        )]
    unresolved = int(summary.get("unresolved_count") or len(summary.get("unresolved") or []))
    if unresolved:
        return [issue(
            "review_warnings_undisposed",
            f"当前 review warning 仍有 {unresolved} 条未以 finding fingerprint + artifact SHA 处置。",
            domain="release",
            blocking_profiles=PUBLIC_PROFILES,
            blocking_usages=("public", "commercial"),
        )]
    return []


def platform_preview_receipt_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / f"platform_preview_receipt_{chapter}.json"


def ordered_delivery_roles(manifest: Mapping[str, Any], artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Preserve authored delivery order and semantic section/role.

    A sorted path→SHA set cannot distinguish two valid image files whose page
    order was swapped after a platform preview.  This sequence is deliberately
    ordered and carries the manifest section plus any page/segment markers.
    """
    artifact_map = {str(item.get("path") or ""): str(item.get("sha256") or "") for item in artifacts}
    records: list[dict[str, Any]] = []
    for section in ("pages", "rendered", "documents"):
        entries = manifest.get(section) if isinstance(manifest.get(section), list) else []
        for order, item in enumerate(entries):
            if not isinstance(item, Mapping):
                continue
            path = str(item.get("path") or "")
            records.append({
                "section": section,
                "order": order,
                "path": path,
                "sha256": artifact_map.get(path, ""),
                "role": str(item.get("role") or ("page" if section == "pages" else "segment" if section == "rendered" else "document")),
                "page": item.get("page") if item.get("page") is not None else item.get("page_index"),
                "segment": item.get("segment") if item.get("segment") is not None else item.get("segment_index"),
            })
    platform_assets = manifest.get("platform_assets") if isinstance(manifest.get("platform_assets"), Mapping) else {}
    for asset_name in sorted(platform_assets):
        item = platform_assets.get(asset_name)
        if not isinstance(item, Mapping):
            continue
        path = str(item.get("path") or "")
        records.append({
            "section": "platform_assets", "order": asset_name, "path": path,
            "sha256": artifact_map.get(path, ""), "role": str(asset_name),
            "page": None, "segment": None,
        })
    return records


def current_preview_delivery_binding(
    root: Path,
    chapter: str,
    manifest: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest_path = root / "排版" / chapter / "export_manifest.json"
    return {
        "manifest": {
            "path": str(manifest_path.relative_to(root)),
            "sha256": sha256_file(manifest_path) if manifest_path.is_file() else "",
        },
        "ordered_roles": ordered_delivery_roles(manifest, artifacts),
        "artifact_set": artifact_binding(artifacts),
    }


def platform_preview_binding(
    root: Path,
    chapter: str,
    manifest: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    path = platform_preview_receipt_path(root, chapter)
    if not path.is_file():
        return {}
    return {
        "path": str(path.relative_to(root)),
        "sha256": sha256_file(path),
        "current_delivery": current_preview_delivery_binding(root, chapter, manifest, artifacts),
    }


def _project_file(root: Path, value: str) -> Path | None:
    candidate = Path(value).expanduser()
    candidate = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def create_platform_preview_receipt(
    root: Path,
    chapter: str,
    *,
    desktop_screenshot: Path,
    mobile_screenshot: Path,
    reviewer: str,
    reason: str,
    preview_source: str,
) -> Path:
    if not reviewer.strip() or not reason.strip():
        raise ValueError("--reviewer and --reason are required")
    manifest = load_json(root / "排版" / chapter / "export_manifest.json", {})
    artifacts, artifact_issues = rendered_artifacts(root, manifest if isinstance(manifest, Mapping) else {})
    if artifact_issues or not artifacts:
        raise ValueError("platform preview cannot bind invalid/empty deliverables")
    profile = profile_for_platform(get_setting(str(root), "目标平台", str(manifest.get("target_platform") or "通用")))
    if not profile.preview_viewports:
        raise ValueError(f"{profile.display_name} profile 没有一手证据支持特定 viewport preview；不要虚构 PC/mobile 后台预览")
    if preview_source not in {"actual_platform_preview", "local_simulation"}:
        raise ValueError("preview_source must explicitly be actual_platform_preview or local_simulation")
    screenshots: list[dict[str, Any]] = []
    for viewport, raw_path in (("desktop", desktop_screenshot), ("mobile", mobile_screenshot)):
        path = raw_path.expanduser().resolve()
        try:
            relative = path.relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError(f"{viewport} screenshot must be inside project root") from exc
        if not path.is_file():
            raise ValueError(f"{viewport} screenshot missing")
        try:
            from PIL import Image
            with Image.open(path) as image:
                image.load()
                dimensions = {"width": image.width, "height": image.height}
        except (ImportError, OSError, ValueError) as exc:
            raise ValueError(f"{viewport} screenshot is not a decodable image: {exc}") from exc
        screenshots.append({"viewport": viewport, "path": str(relative), "sha256": sha256_file(path), "dimensions": dimensions})
    payload = {
        "schema_version": 1,
        "kind": "comic_platform_preview_receipt",
        "chapter": chapter,
        "status": "approved",
        "target_platform": profile.platform_id,
        "preview_source": preview_source,
        "reviewer": reviewer.strip(),
        "reason": reason.strip(),
        "reviewed_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "screenshots": screenshots,
        "delivery_binding": current_preview_delivery_binding(root, chapter, manifest, artifacts),
    }
    path = platform_preview_receipt_path(root, chapter)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def check_platform_preview_receipt(
    root: Path,
    chapter: str,
    manifest: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
    target_platform: str,
    medium: str,
    usage: str,
) -> list[dict[str, Any]]:
    target_profile = profile_for_platform(target_platform)
    required_viewports = tuple(target_profile.preview_viewports)
    if usage == "internal" or medium == "print_pdf" or not required_viewports:
        return []
    blocking = dict(
        domain="release",
        blocking_profiles=PUBLIC_PROFILES,
        blocking_mediums=("web_images", "epub_fxl"),
        blocking_usages=("public", "commercial"),
    )
    path = platform_preview_receipt_path(root, chapter)
    receipt = load_json(path, {})
    if not isinstance(receipt, Mapping) or not receipt:
        return [issue("platform_preview_receipt_missing", "公开平台交付缺 PC/mobile 当前上传预览签收。", **blocking)]
    if (
        receipt.get("kind") != "comic_platform_preview_receipt"
        or receipt.get("chapter") != chapter
        or str(receipt.get("status") or "").lower() not in {"approved", "accepted", "pass"}
        or not str(receipt.get("reviewer") or "").strip()
        or not str(receipt.get("reviewed_at") or "").strip()
        or not str(receipt.get("reason") or "").strip()
    ):
        return [issue("platform_preview_receipt_invalid", "平台预览签收缺 kind/chapter/status/reviewer/reason/time。", **blocking)]
    expected_platform = target_profile.platform_id
    if str(receipt.get("target_platform") or "") != expected_platform:
        return [issue("platform_preview_platform_mismatch", f"预览签收平台不是当前 {expected_platform}。", **blocking)]
    if receipt.get("preview_source") != "actual_platform_preview":
        return [issue("platform_preview_not_actual", "公开发布必须绑定实际平台后台 preview；local simulation 只能作内部排版预览。", **blocking)]
    current_delivery = current_preview_delivery_binding(root, chapter, manifest, artifacts)
    if receipt.get("delivery_binding") != current_delivery:
        return [issue("platform_preview_receipt_stale", "平台预览签收未绑定当前 manifest SHA、全部交付物 SHA 与有序 page/segment/section 角色。", **blocking)]
    screenshots = receipt.get("screenshots") if isinstance(receipt.get("screenshots"), list) else []
    by_viewport = {str(item.get("viewport")): item for item in screenshots if isinstance(item, Mapping)}
    for viewport in required_viewports:
        record = by_viewport.get(viewport)
        if not record:
            return [issue("platform_preview_viewport_missing", f"平台预览签收缺 {viewport} 截图。", **blocking)]
        screenshot = _project_file(root, str(record.get("path") or ""))
        if screenshot is None or not screenshot.is_file() or str(record.get("sha256") or "") != sha256_file(screenshot):
            return [issue("platform_preview_screenshot_stale", f"{viewport} 预览截图缺失、越界或 SHA 已变化。", **blocking)]
    return []


def _print_issue(code: str, reason: str) -> dict[str, Any]:
    return issue(
        code, reason, domain="print", blocking_profiles=("print",),
        blocking_mediums=("print_pdf",),
    )


def print_delivery_checks(
    root: Path,
    chapter: str,
    manifest: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    documents = [item for item in manifest.get("documents") or [] if isinstance(item, Mapping) and str(item.get("format") or "").lower() == "pdf"]
    pdf_artifacts = {item["path"]: item for item in artifacts if item.get("format") == "pdf"}
    if not documents:
        return [_print_issue("print_pdf_missing", "print_pdf 介质没有 manifest.documents PDF；普通 PNG/WebP 图片包不能冒充印刷交付。")]
    document = dict(documents[0])
    pdf_artifact = pdf_artifacts.get(str(document.get("path") or ""))
    if not pdf_artifact:
        return [_print_issue("print_pdf_unverified", "当前 PDF 未通过文件存在性与结构预检。")]

    contract_path = root / "排版" / chapter / "print_delivery_contract.json"
    contract = load_json(contract_path, {})
    if not isinstance(contract, Mapping) or contract.get("kind") != "comic_print_delivery_contract" or contract.get("chapter") != chapter:
        return [_print_issue("print_delivery_contract_missing", "缺当前话有效 print_delivery_contract.json（trim/bleed/safe/DPI/binding/color/font）。")]
    geometry = contract.get("geometry_mm") if isinstance(contract.get("geometry_mm"), Mapping) else {}
    trim = geometry.get("trim") if isinstance(geometry.get("trim"), Mapping) else {}
    bleed = geometry.get("bleed") if isinstance(geometry.get("bleed"), Mapping) else {}
    safe = geometry.get("safe_area") if isinstance(geometry.get("safe_area"), Mapping) else {}
    try:
        trim_w, trim_h = float(trim["width"]), float(trim["height"])
        bleed_values = {key: float(bleed[key]) for key in ("top", "bottom", "inside", "outside")}
        safe_values = {key: float(safe[key]) for key in ("top", "bottom", "inside", "outside")}
        dpi = int(contract["dpi"])
    except (KeyError, TypeError, ValueError):
        issues.append(_print_issue("print_geometry_invalid", "trim/bleed/safe_area/dpi 必须是完整数值合同。"))
        return issues
    if trim_w <= 0 or trim_h <= 0 or any(value < 0 for value in (*bleed_values.values(), *safe_values.values())):
        issues.append(_print_issue("print_geometry_invalid", "trim 必须为正，bleed/safe 不得为负。"))
    if dpi < 300:
        issues.append(_print_issue("print_dpi_below_floor", f"印刷合同 dpi={dpi}，低于 300。"))
    expected_w = round((trim_w + bleed_values["inside"] + bleed_values["outside"]) / 25.4 * dpi)
    expected_h = round((trim_h + bleed_values["top"] + bleed_values["bottom"]) / 25.4 * dpi)
    expected_media_box = {
        "width": (trim_w + bleed_values["inside"] + bleed_values["outside"]) / 25.4 * 72,
        "height": (trim_h + bleed_values["top"] + bleed_values["bottom"]) / 25.4 * 72,
    }
    source_pages = document.get("source_pages") if isinstance(document.get("source_pages"), list) else []
    if len(source_pages) != int(document.get("page_count") or 0) or not source_pages:
        issues.append(_print_issue("print_page_image_preflight_missing", "PDF 缺逐页源图模式/尺寸/透明度证据。"))
    for index, page in enumerate(source_pages, 1):
        size = page.get("pixel_size") if isinstance(page, Mapping) and isinstance(page.get("pixel_size"), Mapping) else {}
        actual = (int(size.get("width") or 0), int(size.get("height") or 0))
        if abs(actual[0] - expected_w) > 2 or abs(actual[1] - expected_h) > 2:
            issues.append(_print_issue("print_page_geometry_mismatch", f"第 {index} 页 {actual[0]}x{actual[1]}px，不等于 trim+bleed@{dpi}dpi 的 {expected_w}x{expected_h}px。"))
        if str(page.get("mode") or "") != str((contract.get("color") or {}).get("mode") or ""):
            issues.append(_print_issue("print_color_mode_mismatch", f"第 {index} 页 mode={page.get('mode')}，合同为 {(contract.get('color') or {}).get('mode')}。"))
        if page.get("has_alpha") is not False:
            issues.append(_print_issue("print_transparency_not_flattened", f"第 {index} 页透明度未证明已扁平化。"))
        source_path = _project_file(root, str(page.get("path") or ""))
        if source_path is None or not source_path.is_file() or str(page.get("sha256") or "") != sha256_file(source_path):
            issues.append(_print_issue("print_source_page_stale", f"第 {index} 页源图缺失、越界或 SHA 已变化；旧 PDF 证据不可沿用。"))

    current_page_order = [str(item.get("path") or "") for item in manifest.get("pages") or [] if isinstance(item, Mapping)]
    if list(contract.get("page_order") or []) != current_page_order or list(document.get("page_order") or []) != current_page_order:
        issues.append(_print_issue("print_page_order_mismatch", "合同、PDF source order 与当前 manifest.pages 顺序不一致。"))
    binding = contract.get("binding") if isinstance(contract.get("binding"), Mapping) else {}
    if (binding.get("reading_direction"), binding.get("edge")) not in {("rtl", "right"), ("ltr", "left")}:
        issues.append(_print_issue("print_binding_invalid", "装订边与阅读方向不一致或缺失。"))

    structural = pdf_artifact.get("pdf_structural_evidence") or {}
    media_boxes = structural.get("media_boxes_points") if isinstance(structural.get("media_boxes_points"), list) else []
    if len(media_boxes) != len(source_pages) or any(
        abs(float(box.get("width") or 0) - expected_media_box["width"]) > 0.5
        or abs(float(box.get("height") or 0) - expected_media_box["height"]) > 0.5
        for box in media_boxes
        if isinstance(box, Mapping)
    ):
        issues.append(_print_issue("print_pdf_media_box_mismatch", "PDF MediaBox 未证明与 trim+bleed 的物理尺寸一致。"))
    font = contract.get("font_handling") if isinstance(contract.get("font_handling"), Mapping) else {}
    if font.get("mode") == "rasterized":
        if int(structural.get("font_object_count") or 0) != 0 or int(structural.get("image_object_count") or 0) < len(source_pages):
            issues.append(_print_issue("print_font_flattening_unproven", "声明文字栅格化，但 PDF 结构没有证明零 Font object 且每页有 Image object。"))
    elif font.get("mode") == "embedded":
        if int(structural.get("font_object_count") or 0) <= 0 or not str(font.get("embedding_evidence") or ""):
            issues.append(_print_issue("print_font_embedding_unproven", "声明嵌入字体，但缺 Font object 或 embedding_evidence。"))
    else:
        issues.append(_print_issue("print_font_policy_missing", "font_handling.mode 必须为 rasterized 或 embedded。"))

    color = contract.get("color") if isinstance(contract.get("color"), Mapping) else {}
    icc_policy = str(color.get("icc_policy") or "")
    if icc_policy == "embedded" and not structural.get("icc_object_present"):
        issues.append(_print_issue("print_icc_embedding_unproven", "合同要求 embedded ICC，但 PDF 无 ICCBased/OutputIntent 证据。"))
    elif icc_policy in {"printer_managed_srgb", "printer_managed_gray"}:
        if not str(color.get("icc_profile_name") or "").strip() or not str(contract.get("vendor_requirement_evidence") or "").strip():
            issues.append(_print_issue("print_icc_declaration_incomplete", "printer-managed ICC 路线缺 profile 名或印厂要求证据。"))
    elif icc_policy != "embedded":
        issues.append(_print_issue("print_icc_policy_missing", "缺可验证的 embedded/printer-managed ICC policy。"))

    receipt_path = root / "生产数据" / f"print_readiness_receipt_{chapter}.json"
    receipt = load_json(receipt_path, {})
    checks = receipt.get("checks") if isinstance(receipt, Mapping) and isinstance(receipt.get("checks"), Mapping) else {}
    expected_checks = {
        "safe_area_content_clear", "page_order_and_binding_correct",
        "color_and_icc_match_vendor", "font_handling_and_license_confirmed",
    }
    pdf_path = root / str(document.get("path") or "")
    valid_receipt = (
        isinstance(receipt, Mapping)
        and receipt.get("kind") == "comic_print_readiness_receipt"
        and receipt.get("chapter") == chapter
        and str(receipt.get("status") or "").lower() in {"approved", "accepted", "pass"}
        and bool(str(receipt.get("reviewer") or "").strip())
        and bool(str(receipt.get("reason") or "").strip())
        and (receipt.get("contract") or {}).get("sha256") == sha256_file(contract_path)
        and pdf_path.is_file()
        and (receipt.get("pdf") or {}).get("sha256") == sha256_file(pdf_path)
        and receipt.get("pdf_document_record_sha256") == stable_sha256(document)
        and all(checks.get(key) is True for key in expected_checks)
    )
    if not valid_receipt:
        issues.append(_print_issue("print_readiness_receipt_missing_or_stale", "safe area、页序/装订、ICC/色彩、字体处置无法全自动证明；缺绑定当前合同/PDF SHA 的四项人审签收。"))
    return issues


def accessible_digital_checks(
    root: Path,
    chapter: str,
    artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    def problem(code: str, reason: str) -> dict[str, Any]:
        return issue(code, reason, domain="accessibility", blocking_mediums=("epub_fxl",))

    path = root / "排版" / chapter / "accessible_digital_contract.json"
    contract = load_json(path, {})
    if not isinstance(contract, Mapping) or contract.get("kind") != "comic_accessible_digital_contract" or contract.get("chapter") != chapter:
        return [problem("accessible_contract_missing", "epub_fxl 缺 accessible_digital_contract.json；普通图片包不能冒充 accessible digital。")]
    issues: list[dict[str, Any]] = []
    epub = next((item for item in artifacts if item.get("format") == "epub"), None)
    artifact = contract.get("artifact") if isinstance(contract.get("artifact"), Mapping) else {}
    if not epub or artifact.get("path") != epub.get("path") or artifact.get("sha256") != epub.get("sha256"):
        issues.append(problem("accessible_epub_missing_or_stale", "合同未绑定当前结构有效的 EPUB SHA。"))
    rendering = contract.get("rendering") if isinstance(contract.get("rendering"), Mapping) else {}
    structural = epub.get("epub_structural_evidence") if isinstance(epub, Mapping) and isinstance(epub.get("epub_structural_evidence"), Mapping) else {}
    if rendering.get("rendition_layout") != "pre-paginated" or structural.get("rendition_layout") != "pre-paginated":
        issues.append(problem("accessible_fixed_layout_unproven", "合同与实际 OPF 必须同时证明 rendition:layout=pre-paginated；不能把可重排 EPUB 当作固定版式交付。"))
    reading_order = contract.get("reading_order") if isinstance(contract.get("reading_order"), list) else []
    actual_spine_ids = list(structural.get("spine_item_ids") or [])
    actual_spine_hrefs = list(structural.get("spine_hrefs") or [])
    if not reading_order:
        issues.append(problem("accessible_reading_order_missing", "缺明确 reading_order/spine 顺序。"))
    elif reading_order not in (actual_spine_ids, actual_spine_hrefs):
        issues.append(problem("accessible_reading_order_mismatch", "合同 reading_order 未精确匹配实际 OPF spine idref/href 顺序。"))
    alternatives = contract.get("text_alternatives") if isinstance(contract.get("text_alternatives"), Mapping) else {}
    try:
        coverage = float(alternatives.get("coverage") or 0)
    except (TypeError, ValueError):
        coverage = 0
    if coverage < 1.0 or alternatives.get("missing"):
        issues.append(problem("accessible_text_alternatives_incomplete", "页面/格/非文字视觉的 alt description 覆盖未达到 100%。"))
    if any(not str(alternatives.get(key) or "").strip() for key in ("reviewer", "reviewed_at", "reason")):
        issues.append(problem("accessible_text_alternatives_attestation_missing", "human-attested alt 复核必须具名 reviewer、reviewed_at 与 reason；空声明不能冒充人工审阅。"))
    navigation = contract.get("navigation") if isinstance(contract.get("navigation"), Mapping) else {}
    if navigation.get("toc") is not True or not navigation.get("landmarks") or not structural.get("nav_document_valid"):
        issues.append(problem("accessible_navigation_incomplete", "缺合同 TOC/landmarks，或实际 EPUB nav document 无法解析。"))
    metadata = contract.get("accessibility_metadata") if isinstance(contract.get("accessibility_metadata"), Mapping) else {}
    required_metadata = (
        "title", "language", "accessibility_summary", "access_modes",
        "access_mode_sufficient", "accessibility_features", "accessibility_hazards",
    )
    if any(not metadata.get(key) for key in required_metadata):
        issues.append(problem("accessible_metadata_incomplete", "缺 title/language/accessMode/accessModeSufficient/accessibilityFeature/accessibilityHazard/accessibilitySummary；无 hazard 也须显式填 none。"))
    package_metadata = structural.get("package_accessibility_metadata") if isinstance(structural.get("package_accessibility_metadata"), Mapping) else {}
    actual_required = (
        "accessmode", "accessmodesufficient", "accessibilityfeature",
        "accessibilityhazard", "accessibilitysummary",
    )
    if (
        not structural.get("package_title")
        or not structural.get("package_language")
        or any(not package_metadata.get(key) for key in actual_required)
    ):
        issues.append(problem("accessible_opf_metadata_incomplete", "实际 OPF 缺 title/language 或 EPUB Accessibility discoverability 元数据；外部 JSON 合同不能代替包内 metadata。"))
    if not structural.get("all_content_images_have_alt_attribute"):
        issues.append(problem("accessible_xhtml_alt_markup_incomplete", "实际 spine XHTML 存在缺 alt 属性的 img，或内容文档不可解析。alt 文案质量仍须人工复核。"))
    provenance = contract.get("provenance") if isinstance(contract.get("provenance"), Mapping) else {}
    if provenance.get("standard") != "EPUB Accessibility 1.1" or provenance.get("url") != "https://www.w3.org/TR/epub-a11y-11/":
        issues.append(problem("accessible_standard_provenance_missing", "合同缺 W3C EPUB Accessibility 1.1 官方 URL/版本 provenance。"))
    assurance = contract.get("assurance") if isinstance(contract.get("assurance"), Mapping) else {}
    if assurance.get("level") != "workflow_readiness_human_attested" or assurance.get("not_conformance_certification") is not True:
        issues.append(problem("accessible_assurance_overclaim", "本线只机检结构、metadata 存在性与 img alt 属性；不会判断替代文本语义质量或辅助技术体验，也无自动 EPUB renderer。只能声明 workflow readiness / human-attested，不能冒充 EPUB Accessibility/WCAG 认证。"))
    return issues


def check_review_receipt(root: Path, chapter: str) -> list[dict[str, Any]]:
    receipt_path = root / "生产数据" / "gate_receipts" / f"review_{chapter}.json"
    receipt = load_json(receipt_path, {})
    if not isinstance(receipt, Mapping) or not receipt:
        return [issue("review_gate_receipt_missing", "缺当前 review gate receipt。", domain="production")]
    current = stage_inputs_fingerprint(root, chapter, "review")
    if (
        receipt.get("kind") != "comic_gate_receipt"
        or receipt.get("stage") != "review"
        or receipt.get("chapter") != chapter
        or receipt.get("execution_authorized") is not True
    ):
        return [issue("review_gate_receipt_invalid", "review receipt 的 kind/stage/chapter 或执行授权无效。", domain="production")]
    if receipt.get("inputs_fingerprint_sha256") != current.get("sha256"):
        return [issue("review_gate_receipt_stale", "review 后输入已变化，旧 gate receipt 失效。", domain="production")]
    report_path = root / str(receipt.get("report_path") or "")
    if not report_path.is_file():
        return [issue("review_gate_report_missing", "review receipt 指向的报告缺失。", domain="production")]
    if str(receipt.get("report_sha256") or "") != sha256_file(report_path):
        return [issue("review_gate_report_stale", "review gate 报告与 receipt SHA 不一致。", domain="production")]
    report = load_json(report_path, {})
    report_inputs = report.get("inputs_fingerprint") if isinstance(report, Mapping) and isinstance(report.get("inputs_fingerprint"), Mapping) else {}
    if (
        not isinstance(report, Mapping)
        or report.get("kind") != "comic_gate"
        or report.get("stage") != "review"
        or report.get("chapter") != chapter
        or report.get("verdict") != receipt.get("verdict")
        or report_inputs.get("sha256") != current.get("sha256")
        or report_inputs.get("sha256") != receipt.get("inputs_fingerprint_sha256")
    ):
        return [issue("review_gate_report_invalid", "review gate 报告合同、verdict 或输入指纹与 receipt 不一致。", domain="production")]
    # Don't trust the recorded verdict: recompute it from the findings' own
    # severities.  A hand-edit that flips verdict block→warn while leaving
    # block-severity findings in place (and re-hashing report_sha256, which the
    # gate report file is not itself part of the review fingerprint) would
    # otherwise pass every check above and release the chapter.
    if not isinstance(report.get("findings"), list):
        return [issue(
            "review_gate_findings_missing",
            "review gate 报告必须携带 findings 数组；缺字段不能按零 finding 解释。",
            domain="production",
        )]
    report_findings = report.get("findings")
    recomputed_verdict = (
        "block" if any(isinstance(f, Mapping) and f.get("severity") == "block" for f in report_findings)
        else "warn" if any(isinstance(f, Mapping) and f.get("severity") == "warn" for f in report_findings)
        else "pass"
    )
    if recomputed_verdict != report.get("verdict"):
        return [issue(
            "review_gate_report_verdict_tampered",
            f"review gate 报告 verdict={report.get('verdict')!r} 与其 findings 严重度重算值 {recomputed_verdict!r} 不一致（疑似手改绕过 block）。",
            domain="production",
        )]
    # Recompute the receipt_id over the same material the gate signs, so tampering
    # with findings content (not just the verdict field) is caught.
    recorded_receipt_id = str(report.get("receipt_id") or "")
    gate_receipt_id = str(receipt.get("receipt_id") or "")
    expected_receipt_id = stable_sha256({
        "project_root": ".",
        "chapter": chapter,
        "stage": "review",
        "inputs": report_inputs.get("sha256"),
        "verdict": report.get("verdict"),
        "findings": report_findings,
    })
    if (
        not recorded_receipt_id
        or not gate_receipt_id
        or recorded_receipt_id != gate_receipt_id
        or recorded_receipt_id != expected_receipt_id
    ):
        return [issue(
            "review_gate_receipt_id_mismatch",
            "report/receipt 的 receipt_id 必填、必须相等，并须匹配 inputs+verdict+findings 重算值。",
            domain="production",
        )]
    if recomputed_verdict == "block" or receipt.get("verdict") == "block":
        return [issue("review_gate_blocked", "review gate 仍有 block。", domain="production")]
    return []


def review_gate_summary(root: Path, chapter: str) -> dict[str, Any]:
    """机检真相摘要：verdict + 计数 + 有效豁免清单，嵌进发布裁决供叙事对账。

    背景：历史上 review gate 实为 warn（如 0 block/133 warn）而 `_进度.md`
    叙事写「pass」，完成度表述比机检结论乐观。发布裁决是叙事的上游证据，
    必须原样携带机检结论；任何「内部验收通过」的表述都应引用本区块。
    """
    receipt = load_json(root / "生产数据" / "gate_receipts" / f"review_{chapter}.json", {})
    report = load_json(root / "生产数据" / f"comic_gate_review_{chapter}.json", {})
    counts = {}
    report_summary = report.get("summary") if isinstance(report, Mapping) and isinstance(report.get("summary"), Mapping) else {}
    for key in ("block_count", "warn_count", "info_count"):
        value = report_summary.get(key)
        if isinstance(value, int):
            counts[key] = value
    waivers = []
    waiver_dir = root / "生产数据" / "gate_waivers"
    if waiver_dir.is_dir():
        for path in sorted(waiver_dir.glob(f"*{chapter}_latest.json")):
            payload = load_json(path, {})
            if isinstance(payload, Mapping):
                waivers.append(
                    {
                        "path": str(path.relative_to(root)),
                        "stage": str(payload.get("stage") or ""),
                        "reason": str(payload.get("reason") or ""),
                        "created_at": str(payload.get("created_at") or ""),
                    }
                )
    return {
        "receipt_verdict": str(receipt.get("verdict") or "missing") if isinstance(receipt, Mapping) else "missing",
        "counts": counts,
        "waivers": waivers,
    }


def vlm_adjudication_summary(root: Path, chapter: str) -> dict[str, Any]:
    """VLM 三轴（角色/生物身份、背景、道具）裁决覆盖摘要。

    2026-07 实证：两话 103 条任务 0 裁决仍以 internal profile 放行——
    「画错生物形态」类漂移全程无人拦。gate 只 warn（advisory 哲学），
    闭环必须在发布裁决收口（strict 档拒空壳的通用模式）。
    只统计 SHA 仍然有效的裁决：重抽过的格旧裁决不算数。
    """
    tasks_payload = load_json(root / "生产数据" / f"comic_vlm_judge_tasks_{chapter}.json", {})
    tasks = tasks_payload.get("tasks") if isinstance(tasks_payload, Mapping) else None
    tasks = [task for task in tasks or [] if isinstance(task, Mapping)]
    expected = {
        str(task.get("task_id")): str((task.get("panel") or {}).get("sha256") or "")
        for task in tasks
        if task.get("task_id")
    }
    verdict_payload = load_json(root / "生产数据" / f"comic_vlm_judge_verdicts_{chapter}.json", {})
    records = verdict_payload.get("verdicts") if isinstance(verdict_payload, Mapping) else None
    adjudicated: dict[str, str] = {}
    for record in records or []:
        if not isinstance(record, Mapping):
            continue
        task_id = str(record.get("task_id") or "")
        if task_id not in expected:
            continue
        if str(record.get("panel_sha256") or "") != expected[task_id]:
            continue  # 该格已重抽，旧裁决作废
        verdict = str(record.get("verdict") or "")
        if verdict in {"pass", "suspect"}:
            adjudicated[task_id] = verdict
    open_suspects = sorted(tid for tid, verdict in adjudicated.items() if verdict == "suspect")
    return {
        "tasks_file_present": bool(tasks_payload),
        "total": len(expected),
        "adjudicated": len(adjudicated),
        "open_suspects": open_suspects,
    }


def check_vlm_adjudication(root: Path, chapter: str, summary: Mapping[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    total = int(summary.get("total") or 0)
    adjudicated = int(summary.get("adjudicated") or 0)
    open_suspects = list(summary.get("open_suspects") or [])
    if not summary.get("tasks_file_present"):
        if (root / "生产数据" / f"comic_character_consistency_{chapter}.json").is_file():
            issues.append(issue(
                "vlm_tasks_missing",
                "角色一致性报告存在但 VLM 并排判定任务包缺失——身份三轴机检未建立，不能声称完成生产验收。",
                domain="production",
            ))
        return issues
    if total > 0 and adjudicated == 0:
        issues.append(issue(
            "vlm_adjudication_missing",
            f"VLM 并排判定任务包 {total} 条、有效裁决 0 条——角色/生物身份、背景、道具三轴机检空转，"
            "画错生物形态这类漂移不会被拦。先用 vlm_adjudicate.py queue/submit 完成裁决。",
            domain="production",
        ))
    elif total > 0 and adjudicated < total:
        issues.append(issue(
            "vlm_adjudication_partial",
            f"VLM 裁决覆盖不完整：{adjudicated}/{total}（重抽过的格需重建任务包后再裁决）。",
            domain="release",
            blocking_profiles=PUBLIC_PROFILES,
        ))
    if open_suspects:
        issues.append(issue(
            "vlm_suspect_unresolved",
            f"VLM 裁决存在未处置的 suspect {len(open_suspects)} 条（{', '.join(open_suspects[:6])}"
            f"{' …' if len(open_suspects) > 6 else ''}）——确认漂移的格必须重抽并重新裁决，或书面豁免。",
            domain="release",
            blocking_profiles=PUBLIC_PROFILES,
        ))
    return issues


def review_receipt_binding(root: Path, chapter: str) -> dict[str, str]:
    path = root / "生产数据" / "gate_receipts" / f"review_{chapter}.json"
    receipt = load_json(path, {})
    if not isinstance(receipt, Mapping) or not path.is_file():
        return {}
    return {
        "path": str(path.relative_to(root)),
        "sha256": sha256_file(path),
        "receipt_id": str(receipt.get("receipt_id") or ""),
        "report_sha256": str(receipt.get("report_sha256") or ""),
    }


def medium_specific_binding(
    root: Path,
    chapter: str,
    medium: str,
    manifest: Mapping[str, Any],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Bind the contracts/receipts that give a medium its claimed meaning.

    Artifact SHA alone is insufficient: the same PDF can be approved under a
    different bleed/ICC contract, and the same EPUB can be paired with a newly
    edited accessibility attestation.  Web preview has its own ordered binding.
    """
    if medium == "web_images":
        return {}

    def file_binding(relative: str) -> dict[str, str]:
        path = root / relative
        return {
            "path": relative,
            "sha256": sha256_file(path) if path.is_file() else "",
        }

    if medium == "epub_fxl":
        return {
            "medium": medium,
            "accessible_digital_contract": file_binding(f"排版/{chapter}/accessible_digital_contract.json"),
            "epub_artifacts": sorted(
                ({"path": item["path"], "sha256": item["sha256"]} for item in artifacts if item.get("format") == "epub"),
                key=lambda item: item["path"],
            ),
        }

    pdf_documents = [
        dict(item) for item in manifest.get("documents") or []
        if isinstance(item, Mapping) and str(item.get("format") or "").lower() == "pdf"
    ]
    return {
        "medium": "print_pdf",
        "print_delivery_contract": file_binding(f"排版/{chapter}/print_delivery_contract.json"),
        "print_readiness_receipt": file_binding(f"生产数据/print_readiness_receipt_{chapter}.json"),
        "pdf_artifacts": sorted(
            ({"path": item["path"], "sha256": item["sha256"]} for item in artifacts if item.get("format") == "pdf"),
            key=lambda item: item["path"],
        ),
        "pdf_document_records": [stable_sha256(item) for item in pdf_documents],
    }


def check_acceptance(
    root: Path,
    chapter: str,
    artifacts: list[dict[str, Any]],
    profile: str,
    medium: str,
    usage: str,
    *,
    disposition_binding: Mapping[str, Any],
    preview_binding: Mapping[str, Any],
    medium_binding: Mapping[str, Any],
) -> list[dict[str, Any]]:
    path = root / "生产数据" / f"release_acceptance_{chapter}.json"
    acceptance = load_json(path, {})
    if not isinstance(acceptance, Mapping) or not acceptance:
        return [
            issue(
                "release_acceptance_missing",
                "发布候选缺 SHA 绑定的人工签收。",
                domain="release",
                blocking_profiles=("digital", "print", "commercial"),
            )
        ]
    if str(acceptance.get("status") or "").lower() not in {"approved", "accepted", "pass"}:
        return [issue("release_acceptance_not_approved", "人工发布签收未批准。", domain="release", blocking_profiles=("digital", "print", "commercial"))]
    if (
        not str(acceptance.get("reviewer") or "").strip()
        or not str(acceptance.get("approved_at") or "").strip()
        or not str(acceptance.get("reason") or "").strip()
    ):
        return [issue("release_acceptance_identity_missing", "发布签收缺 reviewer/approved_at/reason。", domain="release", blocking_profiles=("digital", "print", "commercial"))]
    acceptance_profile = str(acceptance.get("profile") or "")
    fallback_axes = LEGACY_PROFILE_AXES.get(acceptance_profile, ("", ""))
    acceptance_medium = str(acceptance.get("medium") or fallback_axes[0])
    acceptance_usage = str(acceptance.get("usage") or fallback_axes[1])
    if acceptance_medium != medium or acceptance_usage != usage:
        return [issue(
            "release_acceptance_profile_mismatch",
            f"发布签收 medium+usage={acceptance_medium or 'missing'}+{acceptance_usage or 'missing'}，不能授权当前 {medium}+{usage}。",
            domain="release",
            blocking_profiles=("digital", "print", "commercial"),
        )]
    recorded = acceptance.get("artifacts")
    recorded_map = {
        str(item.get("path")): str(item.get("sha256"))
        for item in recorded or []
        if isinstance(item, Mapping) and item.get("path") and item.get("sha256")
    }
    current_map = {item["path"]: item["sha256"] for item in artifacts}
    if not recorded_map or recorded_map != current_map:
        return [issue("release_acceptance_stale", "发布签收没有精确绑定当前全部导出物 SHA。", domain="release", blocking_profiles=("digital", "print", "commercial"))]
    stale_issues: list[dict[str, Any]] = []
    recorded_review = acceptance.get("review_receipt") if isinstance(acceptance.get("review_receipt"), Mapping) else {}
    if dict(recorded_review) != review_receipt_binding(root, chapter):
        stale_issues.append(issue("release_acceptance_review_stale", "发布签收未精确绑定当前 review gate receipt。", domain="release", blocking_profiles=("digital", "print", "commercial")))
    if dict(acceptance.get("finding_dispositions") or {}) != dict(disposition_binding):
        stale_issues.append(issue("release_acceptance_dispositions_stale", "发布签收未精确绑定当前 finding disposition summary/ledger SHA。", domain="release", blocking_profiles=PUBLIC_PROFILES, blocking_usages=("public", "commercial")))
    if dict(acceptance.get("platform_preview_receipt") or {}) != dict(preview_binding):
        stale_issues.append(issue("release_acceptance_preview_stale", "发布签收未精确绑定当前平台预览 receipt；预览处置变化后需重签。", domain="release", blocking_profiles=PUBLIC_PROFILES, blocking_mediums=("web_images", "epub_fxl"), blocking_usages=("public", "commercial")))
    if dict(acceptance.get("medium_specific_binding") or {}) != dict(medium_binding):
        stale_issues.append(issue("release_acceptance_medium_binding_stale", "发布签收未精确绑定当前介质合同/验收 receipt/PDF 或 EPUB 记录；介质证据变化后需重签。", domain="release", blocking_profiles=PUBLIC_PROFILES, blocking_usages=("public", "commercial")))
    return stale_issues


def create_acceptance(
    root: Path,
    chapter: str,
    profile: str,
    *,
    reviewer: str,
    reason: str,
    medium: str | None = None,
    usage: str | None = None,
) -> Path:
    resolved_medium, resolved_usage, _axis_id = resolve_delivery_axes(profile, medium=medium, usage=usage)
    if resolved_usage == "internal":
        raise ValueError("internal profile does not need a public release acceptance")
    if not reviewer.strip() or not reason.strip():
        raise ValueError("--reviewer and --reason are required")
    preflight = build(root, chapter, profile, medium=resolved_medium, usage=resolved_usage)
    acceptance_codes = {
        "release_acceptance_missing",
        "release_acceptance_not_approved",
        "release_acceptance_identity_missing",
        "release_acceptance_profile_mismatch",
        "release_acceptance_stale",
        "release_acceptance_review_stale",
        "release_acceptance_dispositions_stale",
        "release_acceptance_preview_stale",
        "release_acceptance_medium_binding_stale",
    }
    blockers = [
        item for item in preflight["issues"]
        if issue_blocks(item, resolved_medium, resolved_usage) and item["code"] not in acceptance_codes
    ]
    if blockers:
        raise ValueError("release preflight blocked: " + ",".join(item["code"] for item in blockers))
    receipt = review_receipt_binding(root, chapter)
    if not receipt:
        raise ValueError("current review receipt missing")
    payload = {
        "schema_version": 2,
        "kind": "comic_release_acceptance",
        "status": "approved",
        "chapter": chapter,
        "profile": profile,
        "medium": resolved_medium,
        "usage": resolved_usage,
        "reviewer": reviewer.strip(),
        "reason": reason.strip(),
        "approved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifacts": preflight["artifacts"],
        "review_receipt": receipt,
        "finding_dispositions": preflight["finding_disposition_binding"],
        "platform_preview_receipt": preflight["platform_preview_binding"],
        "medium_specific_binding": preflight["medium_specific_binding"],
    }
    path = root / "生产数据" / f"release_acceptance_{chapter}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def build(
    root: Path,
    chapter: str,
    profile: str = "internal",
    *,
    medium: str | None = None,
    usage: str | None = None,
) -> dict[str, Any]:
    resolved_medium, resolved_usage, axis_id = resolve_delivery_axes(profile, medium=medium, usage=usage)
    manifest_path = root / "排版" / chapter / "export_manifest.json"
    manifest = load_json(manifest_path, {})
    issues: list[dict[str, Any]] = []
    if not isinstance(manifest, Mapping) or not manifest:
        issues.append(issue("export_manifest_missing", "缺 export_manifest.json。", domain="technical"))
        artifacts: list[dict[str, Any]] = []
    else:
        artifacts, artifact_issues = rendered_artifacts(root, manifest)
        issues.extend(artifact_issues)
        if manifest.get("missing_panels"):
            issues.append(issue("manifest_missing_panels", "manifest 仍列出缺图。", domain="technical"))
        if manifest.get("render_error"):
            issues.append(issue("manifest_render_error", str(manifest.get("render_error")), domain="technical"))
        if manifest.get("format_error"):
            issues.append(issue("manifest_format_error", str(manifest.get("format_error")), domain="technical"))
        fulfillment = manifest.get("format_fulfillment") if isinstance(manifest.get("format_fulfillment"), Mapping) else {}
        if fulfillment and fulfillment.get("verdict") != "pass":
            issues.append(issue("export_format_unfulfilled", f"请求格式未实际生成：{fulfillment.get('missing') or 'unknown'}。", domain="technical"))
        if manifest.get("pdf_export_error") and resolved_medium == "print_pdf":
            issues.append(_print_issue("pdf_export_failed", str(manifest.get("pdf_export_error"))))
        if not artifacts:
            issues.append(issue("rendered_artifacts_empty", "没有已落盘的最终导出物。", domain="technical"))
        if resolved_medium == "web_images" and not any(item.get("artifact_type") != "document" for item in artifacts):
            issues.append(issue("web_image_delivery_missing", "web_images 介质没有可解码页面/长图。", domain="technical", blocking_mediums=("web_images",)))

    platform_issues, target_platform, platform_profile = platform_release_checks(
        root,
        manifest if isinstance(manifest, Mapping) else {},
        artifacts,
        resolved_medium,
    )
    issues.extend(platform_issues)

    # These contracts are always reported so delivery_states can expose every
    # medium, but their issues only block their own medium.
    issues.extend(print_delivery_checks(root, chapter, manifest if isinstance(manifest, Mapping) else {}, artifacts))
    issues.extend(accessible_digital_checks(root, chapter, artifacts))

    issues.extend(check_review_receipt(root, chapter))
    adjudication = vlm_adjudication_summary(root, chapter)
    issues.extend(check_vlm_adjudication(root, chapter, adjudication))
    dispositions = finding_disposition_status(root, chapter)
    disposition_receipt_binding = finding_disposition_binding(root, chapter)
    issues.extend(check_finding_dispositions(dispositions))
    target_profile_obj = profile_for_platform(target_platform)
    preview_receipt_binding = (
        platform_preview_binding(root, chapter, manifest if isinstance(manifest, Mapping) else {}, artifacts)
        if resolved_usage in {"public", "commercial"}
        and resolved_medium in {"web_images", "epub_fxl"}
        and target_profile_obj.preview_viewports
        else {}
    )
    issues.extend(check_platform_preview_receipt(
        root, chapter, manifest if isinstance(manifest, Mapping) else {},
        artifacts, target_platform, resolved_medium, resolved_usage,
    ))
    current_medium_binding = medium_specific_binding(
        root, chapter, resolved_medium,
        manifest if isinstance(manifest, Mapping) else {}, artifacts,
    )
    issues.extend(check_acceptance(
        root, chapter, artifacts, profile, resolved_medium, resolved_usage,
        disposition_binding=disposition_receipt_binding,
        preview_binding=preview_receipt_binding,
        medium_binding=current_medium_binding,
    ))

    meta = load_json(root / "_meta.json", {})
    rights = meta.get("rights") if isinstance(meta, Mapping) and isinstance(meta.get("rights"), Mapping) else {}
    for key in ("source_status", "font_status", "asset_status"):
        if not rights_value_is_cleared(rights.get(key)):
            issues.append(
                issue(
                    f"{key}_unverified",
                    f"{key}={rights.get(key) or 'missing'}；公开/印刷/商用交付必须显式声明原创、自有、公版、已授权、开源许可或不适用。",
                    domain="rights",
                    blocking_profiles=("digital", "print", "commercial"),
                    blocking_usages=("public", "commercial"),
                )
            )

    technical_blocks = [item for item in issues if item["domain"] == "technical"]
    production_blocks = [item for item in issues if item["domain"] in {"technical", "production"}]
    profile_blocks = [item for item in issues if issue_blocks(item, resolved_medium, resolved_usage)]
    ready = lambda target_medium, target_usage: not [  # noqa: E731
        item for item in issues if issue_blocks(item, target_medium, target_usage)
    ]
    delivery_states = {
        "technical_complete": not technical_blocks,
        "production_complete": not production_blocks,
        "publish_ready_internal": not production_blocks,
        "publish_ready_digital": ready("web_images", "public"),
        "publish_ready_print": ready("print_pdf", "public"),
        "publish_ready_commercial": ready("web_images", "commercial"),
        "publish_ready_web_images_public": ready("web_images", "public"),
        "publish_ready_web_images_commercial": ready("web_images", "commercial"),
        "publish_ready_print_pdf_public": ready("print_pdf", "public"),
        "publish_ready_print_pdf_commercial": ready("print_pdf", "commercial"),
        "publish_ready_epub_fxl_public": ready("epub_fxl", "public"),
        "publish_ready_epub_fxl_commercial": ready("epub_fxl", "commercial"),
    }
    return {
        "schema_version": 2,
        "kind": "comic_release_verdict",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "project_root": str(root),
        "chapter": chapter,
        "profile": profile,
        "medium": resolved_medium,
        "usage": resolved_usage,
        "delivery_axis": axis_id,
        "target_platform": target_platform,
        "platform_profile": platform_profile,
        "verdict": "pass" if not profile_blocks else "blocked",
        "review_gate_summary": review_gate_summary(root, chapter),
        "vlm_adjudication": adjudication,
        "finding_dispositions": dispositions,
        "finding_disposition_binding": disposition_receipt_binding,
        "platform_preview_binding": preview_receipt_binding,
        "medium_specific_binding": current_medium_binding,
        "delivery_states": delivery_states,
        "artifacts": artifacts,
        "issues": issues,
    }


def write_outputs(root: Path, chapter: str, report: Mapping[str, Any]) -> tuple[Path, Path]:
    json_path = root / "生产数据" / f"release_verdict_{chapter}.json"
    md_path = root / "生产数据" / f"release_verdict_{chapter}.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    gate_summary = report.get("review_gate_summary") or {}
    counts = gate_summary.get("counts") or {}
    lines = [
        f"# 漫画发布裁决 — {chapter}",
        "",
        f"- profile: {report.get('profile')}",
        f"- medium: {report.get('medium')}",
        f"- usage: {report.get('usage')}",
        f"- verdict: {report.get('verdict')}",
        "",
        "## 机检结论（review gate 真相区块——任何「验收通过」叙事必须引用本区块，不得只写 pass）",
        "",
        f"- review receipt verdict: **{gate_summary.get('receipt_verdict', 'missing')}**"
        + (
            f"（block {counts.get('block_count', '?')} / warn {counts.get('warn_count', '?')} / info {counts.get('info_count', '?')}）"
            if counts
            else ""
        ),
    ]
    for waiver in gate_summary.get("waivers") or []:
        lines.append(
            f"- 豁免留痕: `{waiver.get('path')}`（{waiver.get('stage')}；{waiver.get('reason')}）"
        )
    adjudication = report.get("vlm_adjudication") or {}
    if adjudication.get("tasks_file_present"):
        lines.append(
            f"- VLM 三轴裁决覆盖: {adjudication.get('adjudicated', 0)}/{adjudication.get('total', 0)}"
            + (f"，未处置 suspect {len(adjudication.get('open_suspects') or [])} 条" if adjudication.get("open_suspects") else "")
        )
    lines += [
        "",
        "## Delivery states",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in (report.get("delivery_states") or {}).items())
    lines += ["", "## Issues", ""]
    lines.extend(f"- {item.get('code')}: {item.get('reason')}" for item in report.get("issues") or [])
    if not report.get("issues"):
        lines.append("- 无。")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="漫画技术/生产/发布状态分离裁决")
    parser.add_argument("project_root")
    parser.add_argument("chapter")
    parser.add_argument("--profile", choices=PROFILES, default="internal")
    parser.add_argument("--medium", choices=MEDIUMS, default=None, help="技术交付介质；与 usage 解耦。旧 --profile 仍兼容")
    parser.add_argument("--usage", choices=USAGES, default=None, help="internal/public/commercial；commercial 不再是技术介质")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--accept", action="store_true", help="为当前导出物和 review receipt 写 SHA 绑定的人工发布签收")
    parser.add_argument("--accept-platform-preview", action="store_true", help="写 PC/mobile 当前平台预览 SHA 签收")
    parser.add_argument("--desktop-screenshot", default="")
    parser.add_argument("--mobile-screenshot", default="")
    parser.add_argument("--preview-source", choices=("actual_platform_preview", "local_simulation"), default=None)
    parser.add_argument("--reviewer", default="")
    parser.add_argument("--reason", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root).expanduser().resolve()
    if args.accept_platform_preview:
        if not args.desktop_screenshot or not args.mobile_screenshot or not args.preview_source:
            print("[block] --desktop-screenshot, --mobile-screenshot and --preview-source are required", file=sys.stderr)
            return 2
        try:
            create_platform_preview_receipt(
                root,
                args.chapter,
                desktop_screenshot=Path(args.desktop_screenshot),
                mobile_screenshot=Path(args.mobile_screenshot),
                reviewer=args.reviewer,
                reason=args.reason,
                preview_source=args.preview_source,
            )
        except ValueError as exc:
            print(f"[block] {exc}", file=sys.stderr)
            return 2
    if args.accept:
        try:
            create_acceptance(
                root, args.chapter, args.profile, reviewer=args.reviewer, reason=args.reason,
                medium=args.medium, usage=args.usage,
            )
        except ValueError as exc:
            print(f"[block] {exc}", file=sys.stderr)
            return 2
    report = build(root, args.chapter, args.profile, medium=args.medium, usage=args.usage)
    if args.write:
        write_outputs(root, args.chapter, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"verdict={report['verdict']} medium={report['medium']} usage={report['usage']} legacy_profile={args.profile}")
    return 1 if report["verdict"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
