#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Platform export profiles for comic deliverables.

Profiles are scoped to the comic line and intentionally small. They store only
constraints we can verify from first-party documentation; unknown platforms
return advisory findings rather than invented hard limits.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path
import re
from typing import Any


MiB = 1024 * 1024


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
    thumbnail: dict[str, Any] | None = None
    min_panels: int | None = None
    recommended_min_pages: int | None = None
    max_pages: int | None = None
    notes: tuple[str, ...] = ()

    def to_manifest(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_urls"] = list(self.source_urls)
        data["allowed_formats"] = list(self.allowed_formats)
        data["notes"] = list(self.notes)
        return data


PROFILES = {
    "generic": PlatformProfile(
        platform_id="generic",
        display_name="通用",
        verified=True,
        collected_at="2026-07-14",
        source_urls=(),
        allowed_formats=("webp", "png", "jpg"),
        notes=("No platform-specific hard limits are applied.",),
    ),
    "tapas": PlatformProfile(
        platform_id="tapas",
        display_name="Tapas",
        verified=True,
        collected_at="2026-07-14",
        source_urls=(
            "https://help.tapas.io/hc/en-us/articles/1260802028970-Series-Basics-How-to-publish-a-comic-episode-on-Tapas",
            "https://help.tapas.io/hc/en-us/articles/360018625314-A-Quick-Guide-to-Thumbnailing",
        ),
        page_width_px=940,
        max_file_bytes=10 * MiB,
        allowed_formats=("png", "jpg", "gif"),
        thumbnail={"width": 300, "height": 300, "formats": ["png", "jpg", "gif"], "max_file_bytes": 2 * MiB},
        notes=("Tapas comic episode pages are documented as 940 px wide, no height limit, PNG/JPG/GIF, 10 MB.",),
    ),
    "webtoon": PlatformProfile(
        platform_id="webtoon",
        display_name="WEBTOON",
        verified=False,
        collected_at="2026-07-14",
        source_urls=(
            "https://www.webtoons.com/en/notice/detail?noticeNo=1766",
            "https://www.webtoons.com/en/notice/detail?noticeNo=3621",
        ),
        allowed_formats=("jpg", "png"),
        notes=(
            "WEBTOON help center was reachable, but current upload dimensions were not exposed in the scraped first-party page. Verify in Creator Dashboard before publish.",
        ),
    ),
    "kuaikan_submission": PlatformProfile(
        platform_id="kuaikan_submission",
        display_name="快看漫画投稿",
        verified=True,
        collected_at="2026-07-14",
        source_urls=("https://mini.kkmh.com/webs/send/letter",),
        page_width_px=1280,
        allowed_formats=("png", "jpg"),
        min_panels=20,
        notes=(
            "快看邮箱投稿页要求策划案、主角人设与首话分镜成稿；成稿不少于 20 格，宽 1280px，PNG/JPG，300dpi、RGB。",
            "20 格是该投稿 profile 的收稿门槛，不是所有漫画的叙事硬规则。",
        ),
    ),
    "manga_plus_creators": PlatformProfile(
        platform_id="manga_plus_creators",
        display_name="MANGA Plus Creators",
        verified=True,
        collected_at="2026-07-14",
        source_urls=("https://mangaplus-creators.jp/help",),
        max_file_bytes=5 * MiB,
        allowed_formats=("png", "jpg"),
        recommended_min_pages=8,
        max_pages=100,
        notes=(
            "Monthly Awards has no fixed page-count rule; more than 8 pages is recommended and up to 100 pages are accepted.",
            "The 8-page value is advisory, not a production BLOCK.",
        ),
    ),
}

ALIASES = {
    "通用": "generic",
    "generic": "generic",
    "webtoon": "webtoon",
    "web toon": "webtoon",
    "webtoon canvas": "webtoon",
    "tapas": "tapas",
    "快看": "kuaikan_submission",
    "快看漫画": "kuaikan_submission",
    "快看漫画投稿": "kuaikan_submission",
    "kuaikan": "kuaikan_submission",
    "manga plus": "manga_plus_creators",
    "manga plus creators": "manga_plus_creators",
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
        platform_id=key or "custom",
        display_name=str(value or "自定义"),
        verified=False,
        collected_at="",
        source_urls=(),
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


def profile_age_days(profile: PlatformProfile, *, today: date | None = None) -> int | None:
    if not profile.collected_at:
        return None
    try:
        collected = date.fromisoformat(profile.collected_at)
    except ValueError:
        return None
    return ((today or date.today()) - collected).days


def validate_manifest(root: Path, manifest: dict[str, Any], profile: PlatformProfile, usage: str = "") -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    publish_like = is_publish_like_usage(usage)

    def add(severity: str, code: str, artifact: str, reason: str, suggested_fix: str) -> None:
        findings.append(
            {
                "severity": severity,
                "code": code,
                "artifact": artifact,
                "reason": reason,
                "suggested_fix": suggested_fix,
            }
        )

    if not profile.verified and profile.platform_id not in {"generic"}:
        add(
            "block" if publish_like else "warn",
            "platform_profile_unverified",
            "排版/export_manifest.json",
            f"{profile.display_name} 平台规格未有当前可机检的一手尺寸证据。",
            "发布/商用前在平台后台或官方文档核验宽度、高度、格式、文件大小，并更新 platform profile。",
        )

    age = profile_age_days(profile)
    if profile.platform_id != "generic" and age is not None and age > 180:
        add(
            "warn",
            "platform_profile_stale",
            "排版/export_manifest.json",
            f"{profile.display_name} profile 距上次一手资料采集已 {age} 天。",
            "发布前刷新官方资料的尺寸、格式、文件大小与投稿政策，并更新 collected_at/provenance。",
        )

    panel_count = len([item for item in manifest.get("panels") or [] if isinstance(item, dict)])
    page_count = len([item for item in manifest.get("pages") or [] if isinstance(item, dict)])
    if profile.min_panels and panel_count and panel_count < profile.min_panels:
        add(
            "block" if publish_like else "warn",
            "platform_panel_minimum_not_met",
            "排版/export_manifest.json",
            f"{profile.display_name} 收稿门槛为至少 {profile.min_panels} 格，当前 manifest 为 {panel_count} 格。",
            "只在该投稿 profile 下补足成稿或改用符合实际目标的平台 profile。",
        )
    if profile.max_pages and page_count > profile.max_pages:
        add(
            "block" if publish_like else "warn",
            "platform_page_maximum_exceeded",
            "排版/export_manifest.json",
            f"{profile.display_name} 最多 {profile.max_pages} 页，当前为 {page_count} 页。",
            "拆分投稿或按平台规则调整页面文件。",
        )
    if profile.recommended_min_pages and page_count and page_count < profile.recommended_min_pages:
        add(
            "warn",
            "platform_page_count_below_recommendation",
            "排版/export_manifest.json",
            f"{profile.display_name} 建议超过 {profile.recommended_min_pages} 页，当前为 {page_count} 页；该项仅 advisory。",
            "按作品完整性决定是否扩充，不要为凑页数拆坏戏剧闭环。",
        )

    allowed = set(profile.allowed_formats)
    for item in rendered_items(manifest):
        path = root / str(item.get("path") or "")
        fmt = str(item.get("format") or path.suffix.lstrip(".")).lower()
        size = item.get("size") if isinstance(item.get("size"), dict) else {}
        width = int(size.get("width") or 0)
        height = int(size.get("height") or 0)
        artifact = _display_path(root, path)
        if allowed and fmt and fmt not in allowed:
            add("block" if publish_like else "warn", "platform_format_mismatch", artifact, f"{profile.display_name} 不在 profile 允许格式内：{fmt}", "按平台允许格式重新导出。")
        if profile.page_width_px and width and width != profile.page_width_px:
            add(
                "block" if publish_like else "warn",
                "platform_width_mismatch",
                artifact,
                f"{profile.display_name} profile 要求页面宽度 {profile.page_width_px}px，当前为 {width}px。",
                "调整 页面尺寸 或平台 profile 后重新排版/导出。",
            )
        if profile.max_image_height_px and height and height > profile.max_image_height_px:
            add(
                "block" if publish_like else "warn",
                "platform_height_exceeded",
                artifact,
                f"{profile.display_name} profile 最大图片高度 {profile.max_image_height_px}px，当前为 {height}px。",
                "设置 单话分段高度 或 --max-height 后重新导出。",
            )
        if profile.max_file_bytes and path.is_file() and path.stat().st_size > profile.max_file_bytes:
            add(
                "block" if publish_like else "warn",
                "platform_file_too_large",
                artifact,
                f"{profile.display_name} profile 单图上限 {profile.max_file_bytes} bytes，当前为 {path.stat().st_size} bytes。",
                "压缩、改格式或分段后重新导出。",
            )
    return findings
