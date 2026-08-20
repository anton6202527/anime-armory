#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Platform export profiles for comic deliverables.

Every machine-enforced field carries its own first-party provenance and
freshness policy. ``verified``/``collected_at`` remain as compatibility
summaries; consumers must use ``field_provenance`` for decisions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
import re
from typing import Any


MiB = 1024 * 1024
KiB = 1024


def evidence(
    source_url: str,
    collected_at: str,
    *,
    confidence: str = "verified_first_party",
    max_age_days: int = 180,
    note: str = "",
) -> dict[str, Any]:
    return {
        "source_url": source_url,
        "collected_at": collected_at,
        "confidence": confidence,
        "max_age_days": max_age_days,
        "note": note,
    }


@dataclass(frozen=True)
class PlatformProfile:
    platform_id: str
    display_name: str
    verified: bool
    collected_at: str
    source_urls: tuple[str, ...]
    page_width_px: int | None = None
    max_image_height_px: int | None = None
    max_file_bytes: int | None = None
    allowed_formats: tuple[str, ...] = ()
    format_specific_constraints: dict[str, dict[str, Any]] = field(default_factory=dict)
    required_dpi: float | None = None
    color_mode: str | None = None
    thumbnail: dict[str, Any] | None = None
    thumbnail_assets: dict[str, dict[str, Any]] = field(default_factory=dict)
    min_panels: int | None = None
    recommended_min_pages: int | None = None
    max_pages: int | None = None
    field_provenance: dict[str, dict[str, Any]] = field(default_factory=dict)
    preview_viewports: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def to_manifest(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_urls"] = list(self.source_urls)
        data["allowed_formats"] = list(self.allowed_formats)
        data["preview_viewports"] = list(self.preview_viewports)
        data["notes"] = list(self.notes)
        data["provenance_model"] = "field_level_v1"
        return data


TAPAS_SOURCE = "https://help.tapas.io/hc/en-us/articles/1260802028970-Series-Basics-How-to-publish-a-comic-episode-on-Tapas"
TAPAS_THUMB_SOURCE = "https://help.tapas.io/hc/en-us/articles/360018625314-A-Quick-Guide-to-Thumbnailing"
WEBTOON_THUMB_SOURCE = "https://webtooncanvas.zendesk.com/hc/en-us/articles/32913712749588-Designing-Your-Series-Episode-Thumbnails-Sizes-Guidelines-and-Help"
WEBTOON_PREVIEW_SOURCE = "https://webtooncanvas.zendesk.com/hc/en-us/articles/42850360989076-Preview-Episodes-Before-Publishing"
KUAIKAN_SOURCE = "https://mini.kkmh.com/webs/send/letter"
MANGA_PLUS_SOURCE = "https://mangaplus-creators.jp/help"


PROFILES = {
    "generic": PlatformProfile(
        platform_id="generic",
        display_name="通用",
        verified=True,
        collected_at="2026-08-20",
        source_urls=(),
        allowed_formats=("webp", "png", "jpg"),
        field_provenance={
            "allowed_formats": evidence("", "2026-08-20", confidence="workflow_default", max_age_days=3650),
        },
        notes=("No platform-specific hard limits are applied.",),
    ),
    "tapas": PlatformProfile(
        platform_id="tapas",
        display_name="Tapas",
        verified=True,
        collected_at="2026-08-20",
        source_urls=(TAPAS_SOURCE, TAPAS_THUMB_SOURCE),
        page_width_px=940,
        max_file_bytes=10 * MiB,
        allowed_formats=("png", "jpg", "gif"),
        thumbnail={"width": 300, "height": 300, "formats": ["png", "jpg", "gif"], "max_file_bytes": 2 * MiB},
        thumbnail_assets={
            "episode": {"width": 300, "height": 300, "formats": ["png", "jpg", "gif"], "max_file_bytes": 2 * MiB, "constraint_level": "required"},
        },
        format_specific_constraints={"gif": {"max_image_height_px": 1000}},
        field_provenance={
            "page_width_px": evidence(TAPAS_SOURCE, "2026-08-20"),
            "max_file_bytes": evidence(TAPAS_SOURCE, "2026-08-20"),
            "allowed_formats": evidence(TAPAS_SOURCE, "2026-08-20"),
            "format_specific_constraints.gif.max_image_height_px": evidence(TAPAS_SOURCE, "2026-08-20"),
            "thumbnail_assets.episode": evidence(TAPAS_SOURCE, "2026-08-20"),
            "thumbnail_assets.episode.width": evidence(TAPAS_SOURCE, "2026-08-20"),
            "thumbnail_assets.episode.height": evidence(TAPAS_SOURCE, "2026-08-20"),
            "thumbnail_assets.episode.formats": evidence(TAPAS_SOURCE, "2026-08-20"),
            "thumbnail_assets.episode.max_file_bytes": evidence(TAPAS_SOURCE, "2026-08-20"),
            "thumbnail_assets.episode.constraint_level": evidence(TAPAS_SOURCE, "2026-08-20"),
            "preview_viewports": evidence(TAPAS_SOURCE, "2026-08-20"),
        },
        preview_viewports=("desktop", "mobile"),
        notes=("Tapas comic episode pages are documented as 940 px wide, no height limit, PNG/JPG/GIF, 10 MB.",),
    ),
    "webtoon": PlatformProfile(
        platform_id="webtoon",
        display_name="WEBTOON",
        verified=True,
        collected_at="2026-08-20",
        source_urls=(WEBTOON_THUMB_SOURCE, WEBTOON_PREVIEW_SOURCE),
        allowed_formats=(),
        thumbnail_assets={
            "series_square": {"width": 1080, "height": 1080, "formats": ["jpg", "png"], "max_file_bytes": 500 * KiB, "constraint_level": "required"},
            "series_vertical": {"width": 1080, "height": 1920, "formats": ["jpg", "png"], "max_file_bytes": 700 * KiB, "constraint_level": "required"},
            "episode": {"width": 202, "height": 142, "formats": ["jpg", "png"], "max_file_bytes": 500 * KiB, "constraint_level": "recommended"},
        },
        field_provenance={
            "thumbnail_assets.series_square": evidence(WEBTOON_THUMB_SOURCE, "2026-08-20"),
            "thumbnail_assets.series_vertical": evidence(WEBTOON_THUMB_SOURCE, "2026-08-20"),
            "thumbnail_assets.episode": evidence(WEBTOON_THUMB_SOURCE, "2026-08-20"),
            **{
                f"thumbnail_assets.{asset}.{field_name}": evidence(WEBTOON_THUMB_SOURCE, "2026-08-20")
                for asset in ("series_square", "series_vertical", "episode")
                for field_name in ("width", "height", "formats", "max_file_bytes", "constraint_level")
            },
            "preview_viewports": evidence(WEBTOON_PREVIEW_SOURCE, "2026-08-20"),
        },
        preview_viewports=("desktop", "mobile"),
        notes=(
            "The verified 2026 fields cover square/vertical series thumbnails and episode thumbnails.",
            "Main episode upload dimensions are intentionally not invented; verify any unmodeled Creator Dashboard limit at publish time.",
        ),
    ),
    "kuaikan_submission": PlatformProfile(
        platform_id="kuaikan_submission",
        display_name="快看漫画投稿",
        verified=True,
        collected_at="2026-08-20",
        source_urls=(KUAIKAN_SOURCE,),
        page_width_px=1280,
        allowed_formats=("png", "jpg"),
        required_dpi=300,
        color_mode="RGB",
        min_panels=20,
        field_provenance={
            "page_width_px": evidence(KUAIKAN_SOURCE, "2026-08-20"),
            "allowed_formats": evidence(KUAIKAN_SOURCE, "2026-08-20"),
            "min_panels": evidence(KUAIKAN_SOURCE, "2026-08-20"),
            "required_dpi": evidence(KUAIKAN_SOURCE, "2026-08-20"),
            "color_mode": evidence(KUAIKAN_SOURCE, "2026-08-20"),
        },
        notes=(
            "快看邮箱投稿页要求策划案、主角人设与首话分镜成稿；成稿不少于 20 格，宽 1280px，PNG/JPG，300dpi、RGB。",
            "20 格是该投稿 profile 的收稿门槛，不是所有漫画的叙事硬规则。",
        ),
    ),
    "manga_plus_creators": PlatformProfile(
        platform_id="manga_plus_creators",
        display_name="MANGA Plus Creators",
        verified=True,
        collected_at="2026-08-20",
        source_urls=(MANGA_PLUS_SOURCE,),
        max_file_bytes=5 * MiB,
        allowed_formats=("png", "jpg"),
        recommended_min_pages=9,
        max_pages=100,
        field_provenance={
            "max_file_bytes": evidence(MANGA_PLUS_SOURCE, "2026-08-20"),
            "allowed_formats": evidence(MANGA_PLUS_SOURCE, "2026-08-20"),
            "recommended_min_pages": evidence(MANGA_PLUS_SOURCE, "2026-08-20", note="Official wording is more than 8 pages; executable threshold is 9."),
            "max_pages": evidence(MANGA_PLUS_SOURCE, "2026-08-20"),
        },
        notes=(
            "Monthly Awards has no fixed page-count rule; more than 8 pages is recommended and up to 100 pages are accepted.",
            "The 8-page value is advisory, not a production BLOCK.",
        ),
    ),
}

ALIASES = {
    "通用": "generic", "generic": "generic", "webtoon": "webtoon",
    "web toon": "webtoon", "webtoon canvas": "webtoon", "tapas": "tapas",
    "快看": "kuaikan_submission", "快看漫画": "kuaikan_submission",
    "快看漫画投稿": "kuaikan_submission", "kuaikan": "kuaikan_submission",
    "manga plus": "manga_plus_creators", "manga plus creators": "manga_plus_creators",
    "mangaplus creators": "manga_plus_creators",
}


def normalize_platform(value: str | None) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "generic"
    lowered = re.sub(r"\s+", " ", raw).lower()
    return ALIASES.get(raw, ALIASES.get(lowered, lowered))


def profile_for_platform(value: str | None) -> PlatformProfile:
    key = normalize_platform(value)
    return PROFILES.get(key) or PlatformProfile(
        platform_id=key or "custom", display_name=str(value or "自定义"), verified=False,
        collected_at="", source_urls=(),
        notes=("Custom or unsupported platform profile; verify width, height, format and file size before publish.",),
    )


def is_publish_like_usage(value: str) -> bool:
    usage = str(value or "").strip().lower()
    if not usage:
        return False
    draft_tokens = ("草稿", "打样", "内部", "自用", "测试", "预览", "demo", "draft", "internal", "preview", "test")
    return not any(token in usage for token in draft_tokens)


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def rendered_items(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in (manifest.get("pages") or []) + (manifest.get("rendered") or []) if isinstance(item, dict)]


def _age_days(raw_date: str, *, today: date | None = None) -> int | None:
    try:
        collected = date.fromisoformat(raw_date)
    except (TypeError, ValueError):
        return None
    return ((today or date.today()) - collected).days


def profile_age_days(profile: PlatformProfile, *, today: date | None = None) -> int | None:
    """Compatibility aggregate; ``field_age_days`` is authoritative."""
    return _age_days(profile.collected_at, today=today) if profile.collected_at else None


def field_age_days(profile: PlatformProfile, field_name: str, *, today: date | None = None) -> int | None:
    record = profile.field_provenance.get(field_name) or {}
    return _age_days(str(record.get("collected_at") or ""), today=today)


def _active_constraint_fields(profile: PlatformProfile) -> list[str]:
    names: list[str] = []
    for name in (
        "page_width_px", "max_image_height_px", "max_file_bytes", "allowed_formats",
        "required_dpi", "color_mode", "min_panels", "recommended_min_pages", "max_pages", "preview_viewports",
    ):
        if getattr(profile, name):
            names.append(name)
    names.extend(
        f"thumbnail_assets.{asset_name}.{field_name}"
        for asset_name, spec in profile.thumbnail_assets.items()
        for field_name in spec
    )
    names.extend(
        f"format_specific_constraints.{fmt}.{constraint}"
        for fmt, constraints in profile.format_specific_constraints.items()
        for constraint in constraints
    )
    return names


def validate_manifest(root: Path, manifest: dict[str, Any], profile: PlatformProfile, usage: str = "") -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    publish_like = is_publish_like_usage(usage)

    def add(severity: str, code: str, artifact: str, reason: str, suggested_fix: str) -> None:
        findings.append({"severity": severity, "code": code, "artifact": artifact, "reason": reason, "suggested_fix": suggested_fix})

    if not profile.verified and profile.platform_id != "generic":
        add("block" if publish_like else "warn", "platform_profile_unverified", "排版/export_manifest.json", f"{profile.display_name} 平台没有可机检的一手字段证据。", "发布/商用前逐字段核验官方尺寸、格式和文件上限，并记录 field_provenance。")

    for field_name in _active_constraint_fields(profile):
        provenance = profile.field_provenance.get(field_name)
        if not provenance:
            add("block" if publish_like else "warn", "platform_field_provenance_missing", "排版/export_manifest.json", f"{profile.display_name}.{field_name} 缺字段级来源，不能作为硬规格使用。", "补一手 source_url、collected_at、confidence 和 max_age_days。")
            continue
        confidence = str(provenance.get("confidence") or "")
        if confidence not in {"verified_first_party", "workflow_default"}:
            add("block" if publish_like else "warn", "platform_field_unverified", "排版/export_manifest.json", f"{profile.display_name}.{field_name} confidence={confidence or 'missing'}。", "发布前用一手官方资料核验该字段。")
        age = field_age_days(profile, field_name)
        max_age = int(provenance.get("max_age_days") or 180)
        if age is not None and age > max_age:
            add("warn", "platform_field_stale", "排版/export_manifest.json", f"{profile.display_name}.{field_name} 一手资料已 {age} 天未刷新（阈值 {max_age} 天）。", "发布前刷新该字段并只更新它自己的 provenance。")

    panel_count = len([item for item in manifest.get("panels") or [] if isinstance(item, dict)])
    page_count = len([item for item in manifest.get("pages") or [] if isinstance(item, dict)])
    if profile.min_panels and panel_count and panel_count < profile.min_panels:
        add("block" if publish_like else "warn", "platform_panel_minimum_not_met", "排版/export_manifest.json", f"{profile.display_name} 收稿门槛为至少 {profile.min_panels} 格，当前 manifest 为 {panel_count} 格。", "只在该投稿 profile 下补足成稿或改用符合实际目标的平台 profile。")
    if profile.max_pages and page_count > profile.max_pages:
        add("block" if publish_like else "warn", "platform_page_maximum_exceeded", "排版/export_manifest.json", f"{profile.display_name} 最多 {profile.max_pages} 页，当前为 {page_count} 页。", "拆分投稿或按平台规则调整页面文件。")
    if profile.recommended_min_pages and page_count and page_count < profile.recommended_min_pages:
        recommendation = (
            "超过 8 页（执行阈值至少 9 页）"
            if profile.platform_id == "manga_plus_creators"
            else f"至少 {profile.recommended_min_pages} 页"
        )
        add("warn", "platform_page_count_below_recommendation", "排版/export_manifest.json", f"{profile.display_name} 建议{recommendation}，当前为 {page_count} 页；该项仅 advisory。", "按作品完整性决定是否扩充，不要为凑页数拆坏戏剧闭环。")

    allowed = set(profile.allowed_formats)
    for item in rendered_items(manifest):
        path = root / str(item.get("path") or "")
        fmt = str(item.get("format") or path.suffix.lstrip(".")).lower().replace("jpeg", "jpg")
        size = item.get("size") if isinstance(item.get("size"), dict) else {}
        width = int(size.get("width") or 0)
        height = int(size.get("height") or 0)
        actual_mode = str(item.get("color_mode") or "")
        actual_dpi = item.get("dpi")
        if path.is_file():
            try:
                from PIL import Image
                with Image.open(path) as image:
                    image.load()
                    actual_mode = str(image.mode or actual_mode)
                    info_dpi = image.info.get("dpi")
                    if isinstance(info_dpi, (tuple, list)) and info_dpi:
                        actual_dpi = float(info_dpi[0])
                    elif isinstance(info_dpi, (int, float)):
                        actual_dpi = float(info_dpi)
            except (ImportError, OSError, ValueError, TypeError):
                pass
        artifact = _display_path(root, path)
        if allowed and fmt and fmt not in allowed:
            add("block" if publish_like else "warn", "platform_format_mismatch", artifact, f"{profile.display_name} 不在 profile 允许格式内：{fmt}", "按平台允许格式重新导出。")
        if profile.page_width_px and width and width != profile.page_width_px:
            add("block" if publish_like else "warn", "platform_width_mismatch", artifact, f"{profile.display_name} profile 要求页面宽度 {profile.page_width_px}px，当前为 {width}px。", "调整页面尺寸或平台 profile 后重新排版/导出。")
        if profile.max_image_height_px and height and height > profile.max_image_height_px:
            add("block" if publish_like else "warn", "platform_height_exceeded", artifact, f"{profile.display_name} profile 最大图片高度 {profile.max_image_height_px}px，当前为 {height}px。", "设置单话分段高度或 --max-height 后重新导出。")
        format_constraints = profile.format_specific_constraints.get(fmt) or {}
        format_max_height = int(format_constraints.get("max_image_height_px") or 0)
        if format_max_height and height and height > format_max_height:
            add("block" if publish_like else "warn", "platform_format_height_exceeded", artifact, f"{profile.display_name} 的 {fmt.upper()} 特例最大高度 {format_max_height}px，当前为 {height}px。", "缩短/分段该格式文件，或改用平台允许的其它格式。")
        if profile.max_file_bytes and path.is_file() and path.stat().st_size > profile.max_file_bytes:
            add("block" if publish_like else "warn", "platform_file_too_large", artifact, f"{profile.display_name} profile 单图上限 {profile.max_file_bytes} bytes，当前为 {path.stat().st_size} bytes。", "压缩、改格式或分段后重新导出。")
        if profile.required_dpi:
            try:
                dpi_value = float(actual_dpi or 0)
            except (TypeError, ValueError):
                dpi_value = 0
            if abs(dpi_value - float(profile.required_dpi)) > 2.0:
                add("block" if publish_like else "warn", "platform_dpi_mismatch", artifact, f"{profile.display_name} 要求 {profile.required_dpi:g}dpi，当前元数据为 {dpi_value:g}dpi（0 表示缺失）。", "以目标 DPI 重导并写入 PNG/JPEG 分辨率元数据；不得只改声明字段。")
        if profile.color_mode and actual_mode != profile.color_mode:
            add("block" if publish_like else "warn", "platform_color_mode_mismatch", artifact, f"{profile.display_name} 要求 {profile.color_mode}，实际解码 mode={actual_mode or 'unknown'}。", "转换到目标色彩模式后重导，并重新解码核验。")

    registered_assets = manifest.get("platform_assets") if isinstance(manifest.get("platform_assets"), dict) else {}
    for asset_name, spec in profile.thumbnail_assets.items():
        item = registered_assets.get(asset_name)
        if not isinstance(item, dict):
            constraint_level = str(spec.get("constraint_level") or "required")
            add(
                "block" if publish_like and constraint_level == "required" else "warn",
                "platform_thumbnail_asset_missing",
                "排版/export_manifest.json",
                f"{profile.display_name} 缺已落盘并登记 SHA 的 {asset_name} 缩略图；字段规格不等于产物。",
                "实际生成该缩略图后用 --platform-asset NAME=PATH 重导 manifest。",
            )
            continue
        path = root / str(item.get("path") or "")
        if not path.is_file():
            add("block" if publish_like else "warn", "platform_thumbnail_file_missing", _display_path(root, path), f"{asset_name} 只有登记字段，没有真实文件。", "生成真实缩略图并重新登记路径/SHA。")
            continue
        size = item.get("size") if isinstance(item.get("size"), dict) else {}
        actual = (int(size.get("width") or 0), int(size.get("height") or 0))
        actual_format = str(item.get("format") or path.suffix.lstrip(".")).lower().replace("jpeg", "jpg")
        if path.is_file():
            try:
                from PIL import Image
                with Image.open(path) as image:
                    image.load()
                    actual = (image.width, image.height)
                    actual_format = str(image.format or actual_format).lower().replace("jpeg", "jpg")
            except (ImportError, OSError, ValueError):
                add("block" if publish_like else "warn", "platform_thumbnail_decode_failed", _display_path(root, path), f"{asset_name} 不是可完整解码的缩略图。", "重新导出并登记真实文件。")
        expected = (int(spec.get("width") or 0), int(spec.get("height") or 0))
        if actual != expected:
            level = str(spec.get("constraint_level") or "required")
            add("block" if publish_like and level == "required" else "warn", "platform_thumbnail_dimensions_mismatch", _display_path(root, path), f"{asset_name} 应为 {expected[0]}x{expected[1]}，当前为 {actual[0]}x{actual[1]}（{level}）。", "按官方缩略图尺寸重新导出。")
        fmt = actual_format
        if spec.get("formats") and fmt not in set(spec["formats"]):
            add("block" if publish_like else "warn", "platform_thumbnail_format_mismatch", _display_path(root, path), f"{asset_name} 格式 {fmt or 'missing'} 不在 {spec['formats']}。", "按官方缩略图格式重新导出。")
        if path.is_file() and spec.get("max_file_bytes") and path.stat().st_size >= int(spec["max_file_bytes"]):
            add("block" if publish_like else "warn", "platform_thumbnail_file_too_large", _display_path(root, path), f"{asset_name} 达到或超过必须低于的 {spec['max_file_bytes']} bytes。", "压缩缩略图并保持官方尺寸。")
    return findings
