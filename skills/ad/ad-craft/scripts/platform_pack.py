#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build ad platform delivery pack.

Turns target platforms + deliverables into a deterministic checklist before
video/compose: aspect, min resolution, safe area, cutdown rows, and platform
notes.  Pure stdlib and ad-line local.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


KIND = "ad_platform_pack"
PLATFORM_SPEC_MAX_AGE_DAYS = 45
# 平台规格采集日期：2026-08-20  来源：TikTok Ads Help、Google Ads Help、Meta for Business；国内平台发布前仍以当前后台模板为准
PLATFORM_SPECS = {
    "抖音": {
        "aspect": "9:16",
        "min_resolution": "720x1280",
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "required_before_release",
        "authority": "house_snapshot_requires_publisher_confirmation",
        "checked_at": "2026-08-20",
        "source": "项目内部投放快照；发布前须绑定抖音广告后台当前版位模板/书面规格",
        "text_rules": ["Logo、CTA、法律声明避开右侧互动栏与底部标题区", "首帧/前三秒出现产品或品牌"],
    },
    "小红书": {
        "aspect": "9:16",
        "min_resolution": "720x1280",
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "required_before_release",
        "authority": "house_snapshot_requires_publisher_confirmation",
        "checked_at": "2026-08-20",
        "source": "项目内部投放快照；发布前须绑定小红书聚光当前版位模板/书面规格",
        "text_rules": ["封面/首帧要能独立说明卖点", "底部交互区不放关键法律声明"],
    },
    "TikTok": {
        "aspect": "9:16",
        "allowed_aspects": ["9:16", "1:1", "16:9"],
        "min_resolution": "540x960",
        "recommended_resolution": "720x1280_or_higher",
        "accepted_formats": ["mp4", "mov", "mpeg", "3gp", "avi"],
        "max_file_size_mb": 500,
        "min_bitrate_bps": 516000,
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "download_current_official_template",
        "authority": "official_platform_spec",
        "checked_at": "2026-08-20",
        "source": "https://ads.tiktok.com/resources/help/article/tiktok-auction-in-feed-ads?lang=en",
        "text_rules": ["Safe zone changes with aspect, caption length and add-ons/anchors", "Use sound and vertical creative; keep CTA/logo clear of UI"],
    },
    "YouTube": {
        "aspect": "placement_dependent",
        "allowed_aspects": ["16:9", "9:16", "4:5", "1:1"],
        "min_resolution_by_aspect": {"16:9": "1280x720", "9:16": "720x1280", "4:5": "1080x1350", "1:1": "480x480"},
        "recommended_resolution": "1080p",
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "download_current_official_template",
        "authority": "official_platform_spec",
        "checked_at": "2026-08-20",
        "source": "https://support.google.com/google-ads/answer/17091270?hl=en-GB",
        "text_rules": ["Use the current Google Ads safe-zone template for each aspect", "Choose creative treatment by marketing objective; guidance is not an outcome guarantee"],
    },
    "Instagram Reels": {
        "aspect": "9:16",
        "recommended_resolution": "highest_available_9x16",
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "download_current_official_template",
        "authority": "official_platform_guidance",
        "checked_at": "2026-08-20",
        "source": "https://www.facebook.com/business/ads/facebook-instagram-reels-ads",
        "text_rules": ["Use 9:16 video with audio", "Keep key messages inside the Reels safe zone and verify in Meta's checker"],
    },
    "Facebook Reels": {
        "aspect": "9:16",
        "recommended_resolution": "highest_available_9x16",
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "download_current_official_template",
        "authority": "official_platform_guidance",
        "checked_at": "2026-08-20",
        "source": "https://www.facebook.com/business/ads/facebook-instagram-reels-ads",
        "text_rules": ["Use 9:16 video with audio", "Keep key messages inside the Reels safe zone and verify in Meta's checker"],
    },
}

# 平台名不足以确定安全区/时长/声音策略；发布规格以实际 placement 为一等键。
# 数值只收录当前官方页面明确给出的 delivery 约束；创意建议留在 text_rules，
# 不伪装成效果保证或通用上传硬门槛。
PLACEMENT_SPECS = {
    "TikTok:auction_in_feed": {
        **PLATFORM_SPECS["TikTok"],
        "platform": "TikTok", "placement": "auction_in_feed",
        "captions_recommended": True, "audio_recommended": True,
        "source": "https://ads.tiktok.com/resources/help/article/tiktok-auction-in-feed-ads?lang=en",
    },
    "TikTok:out_of_phone": {
        "platform": "TikTok", "placement": "out_of_phone", "aspect": "placement_dependent",
        "allowed_aspects": ["16:9", "9:16", "1:1"],
        "safe_area": "publisher_display_template", "safe_zone_asset": "required_before_release",
        "sound_mode": "sound_off", "captions_required": True,
        "recommended_duration_seconds": [10, 15],
        "authority": "official_platform_guidance", "checked_at": "2026-08-20",
        "source": "https://ads.tiktok.com/resources/help/article/creative-guidelines-for-tiktok-out-of-phone?lang=en",
        "text_rules": ["按实际 OOH 屏幕/合作媒体模板交付", "无声环境下用字幕/画面独立传达；billboard 版优先 10–15 秒"],
    },
    "YouTube:shorts": {
        "platform": "YouTube", "placement": "shorts", "aspect": "9:16",
        "allowed_aspects": ["9:16", "1:1", "16:9"], "recommended_resolution": "1080x1920",
        "safe_area": "placement_overlay_aware", "safe_zone_asset": "download_current_official_template",
        "authority": "official_platform_spec", "checked_at": "2026-08-20",
        "source": "https://support.google.com/google-ads/answer/17091270?hl=en-GB",
        "text_rules": ["9:16 为 Shorts 推荐原生比例；横版/方版虽可支持但应做独立预览", "使用当前 Shorts 安全区模板，关键品牌/CTA 避开互动覆盖层"],
    },
    "YouTube:demand_gen": {
        "platform": "YouTube", "placement": "demand_gen", "aspect": "placement_dependent",
        "allowed_aspects": ["16:9", "9:16", "4:5", "1:1"],
        "recommended_resolution_by_aspect": {
            "16:9": "1920x1080", "9:16": "1080x1920", "4:5": "1080x1350", "1:1": "1080x1080",
        },
        "min_duration_seconds": 5, "in_stream_eligible_min_duration_seconds": 10,
        "max_file_size_mb": 256 * 1024,
        "safe_area": "placement_overlay_aware", "safe_zone_asset": "download_current_official_template",
        "authority": "official_platform_spec", "checked_at": "2026-08-20",
        "source": "https://support.google.com/google-ads/answer/17091672?hl=en",
        "text_rules": ["少于 10 秒不具备 YouTube in-stream 展示资格", "按实际 Demand Gen surface 复核安全区"],
    },
    "YouTube:in_stream": {
        "platform": "YouTube", "placement": "in_stream", "aspect": "16:9",
        "allowed_aspects": ["16:9"], "min_resolution": "1280x720", "recommended_resolution": "1920x1080",
        "safe_area": "placement_overlay_aware", "safe_zone_asset": "download_current_official_template",
        "authority": "official_platform_spec", "checked_at": "2026-08-20",
        "source": "https://support.google.com/google-ads/answer/17091270?hl=en-GB",
        "text_rules": ["按具体可跳过/不可跳过格式与购买方式复核时长", "使用当前 Google Ads safe-zone 模板"],
    },
    "Instagram Reels:reels": {
        **PLATFORM_SPECS["Instagram Reels"],
        "platform": "Instagram Reels", "placement": "reels", "allowed_aspects": ["9:16"],
        "audio_recommended": True,
    },
    "Facebook Reels:reels": {
        **PLATFORM_SPECS["Facebook Reels"],
        "platform": "Facebook Reels", "placement": "reels", "allowed_aspects": ["9:16"],
        "audio_recommended": True,
    },
}


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def spec_age_days(value: Any, today: Optional[date] = None) -> Optional[int]:
    try:
        checked = date.fromisoformat(str(value))
    except ValueError:
        return None
    return ((today or date.today()) - checked).days


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def parse_settings(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in read_text(path).splitlines():
        m = re.match(r"\s*[-*]?\s*([^#\n:：|]+?)\s*[:：]\s*(.+?)\s*$", line)
        if m:
            out[m.group(1).strip()] = m.group(2).split("#", 1)[0].strip()
    return out


def normalize_platforms(brief: Mapping[str, Any], settings: Mapping[str, str]) -> list[str]:
    platforms: list[str] = []
    raw = brief.get("platforms") or []
    if isinstance(raw, str):
        platforms.append(raw)
    elif isinstance(raw, Sequence):
        platforms.extend(str(v) for v in raw if v)
    target = settings.get("目标平台") or ""
    if target and target not in ("未定", "跨平台"):
        platforms.append(target)
    out: list[str] = []
    for p in platforms:
        if p not in out:
            out.append(p)
    return out


def normalize_placements(brief: Mapping[str, Any]) -> list[Dict[str, str]]:
    """Accept list/mapping forms and normalize to platform+placement rows.

    Examples: `["TikTok:auction_in_feed"]`,
    `[{"platform":"YouTube","placement":"shorts"}]`,
    `{"TikTok":["auction_in_feed"]}`.
    """
    raw = brief.get("placements") or []
    rows: list[Dict[str, str]] = []
    if isinstance(raw, Mapping):
        expanded = []
        for platform, values in raw.items():
            values = values if isinstance(values, Sequence) and not isinstance(values, str) else [values]
            expanded.extend({"platform": platform, "placement": value} for value in values)
        raw = expanded
    elif isinstance(raw, str):
        raw = [raw]
    for item in raw if isinstance(raw, Sequence) else []:
        if isinstance(item, Mapping):
            platform = str(item.get("platform") or "").strip()
            placement = str(item.get("placement") or item.get("name") or "").strip()
        else:
            platform, sep, placement = str(item).partition(":")
            platform, placement = platform.strip(), placement.strip() if sep else ""
        if not platform or not placement:
            continue
        key = f"{platform}:{placement}"
        if not any(row["key"].lower() == key.lower() for row in rows):
            rows.append({"key": key, "platform": platform, "placement": placement})
    return rows


def spec_for(platform: str) -> Dict[str, Any]:
    for key, spec in PLATFORM_SPECS.items():
        if key.lower() in platform.lower() or key in platform:
            return dict(spec, platform_key=key)
    return {
        "platform_key": "manual",
        "aspect": "9:16",
        "min_resolution": "720x1280",
        "safe_area": "manual_required",
        "safe_zone_asset": "manual_required",
        "text_rules": ["未登记平台规格；不得以通用中心网格冒充平台安全区，投放前录入官方 placement 模板。"],
    }


def spec_for_placement(platform: str, placement: str) -> Dict[str, Any]:
    wanted = f"{platform}:{placement}".lower()
    for key, spec in PLACEMENT_SPECS.items():
        if key.lower() == wanted:
            return dict(spec, placement_key=key)
    return {
        "platform": platform, "placement": placement, "placement_key": "manual",
        "safe_area": "manual_required", "safe_zone_asset": "manual_required",
        "text_rules": ["未登记版位规格；发布前绑定该 placement 的当前官方/客户书面规格。"],
    }


def deliverable_rows(brief: Mapping[str, Any], settings: Mapping[str, str]) -> list[Dict[str, Any]]:
    deliverables = brief.get("deliverables") if isinstance(brief.get("deliverables"), Mapping) else {}
    master_duration = str(deliverables.get("master_duration") or settings.get("主片时长") or "30s")
    aspect = str(deliverables.get("aspect") or settings.get("交付比例") or "9:16")
    cutdowns = deliverables.get("cutdowns") or []
    if isinstance(cutdowns, str):
        cutdowns = [cutdowns]
    rows = [{
        "deliverable_id": "master",
        "label": "主片",
        "duration": master_duration,
        "aspect": aspect,
        "kind": "master",
        "status": "todo",
        "path": "",
    }]
    for raw in cutdowns:
        duration = str(raw)
        m = re.search(r"\d+", duration)
        key = m.group(0) if m else re.sub(r"\W+", "_", duration)
        rows.append({
            "deliverable_id": f"cut_{key}s" if key.isdigit() else f"cut_{key}",
            "label": f"{duration} cutdown",
            "duration": duration,
            "aspect": aspect,
            "kind": "cutdown",
            "status": "todo",
            "path": "",
        })
    return rows


def _evidence_for(evidence_map: Mapping[str, Any], key: str, platform: str) -> str:
    value = evidence_map.get(key)
    if not value:
        nested = evidence_map.get(platform)
        if isinstance(nested, Mapping):
            value = nested.get(key.split(":", 1)[-1])
        elif nested:
            value = nested
    return str(value or "").strip()


def _evidence_scope(evidence_map: Mapping[str, Any], key: str, platform: str) -> str:
    if evidence_map.get(key):
        return "placement"
    nested = evidence_map.get(platform)
    if isinstance(nested, Mapping) and nested.get(key.split(":", 1)[-1]):
        return "placement"
    return "platform_fallback" if evidence_map.get(platform) else "missing"


def _spec_findings(root: Path, label: str, spec: Mapping[str, Any], *, placement=False) -> list[Dict[str, Any]]:
    findings: list[Dict[str, Any]] = []
    key_field = "placement_key" if placement else "platform_key"
    if spec.get(key_field) == "manual":
        findings.append({
            "severity": "block", "code": "placement_spec_missing" if placement else "platform_spec_missing",
            "msg": f"{label} 缺官方/客户确认规格；先写 brief.{'placement_specs' if placement else 'platform_specs'} 再出视频。",
        })
    if spec.get(key_field) == "custom":
        required = ("safe_area", "source", "checked_at")
        if not (spec.get("aspect") or spec.get("allowed_aspects")):
            required = ("aspect_or_allowed_aspects",) + required
        missing = [key for key in required if key == "aspect_or_allowed_aspects" or not spec.get(key)]
        if missing:
            findings.append({
                "severity": "block", "code": "custom_placement_provenance_missing" if placement else "custom_platform_provenance_missing",
                "msg": f"{label} 自定义规格缺 {', '.join(missing)}；不能把无出处参数当平台标准。",
            })
    if spec.get("checked_at"):
        age = spec_age_days(spec.get("checked_at"))
        if age is None or age < 0:
            findings.append({"severity": "block", "code": "platform_spec_date_invalid",
                             "msg": f"{label} checked_at 无效/在未来；规格 provenance 不可审计。"})
        elif age > PLATFORM_SPEC_MAX_AGE_DAYS:
            findings.append({"severity": "warn", "code": "platform_spec_stale",
                             "msg": f"{label} 规格已 {age} 天未核验；付费制作可继续评估，发布前须重查当前官方/客户规格。"})
    needs_safe_evidence = spec.get("safe_area") not in {None, "", "none", "not_applicable"}
    evidence = str(spec.get("safe_zone_evidence") or "").strip()
    if needs_safe_evidence and not evidence:
        findings.append({"severity": "warn", "code": "safe_zone_asset_pending",
                         "msg": f"{label} 需在发布前绑定当前 placement/anchor 对应官方安全区模板，不可只用 center 网格。"})
    elif evidence and not evidence.startswith(("https://", "http://", "record:")):
        evidence_path = Path(evidence)
        if not evidence_path.is_absolute():
            evidence_path = root / evidence_path
        if not evidence_path.is_file():
            findings.append({"severity": "warn", "code": "safe_zone_evidence_missing",
                             "msg": f"{label} 声明的安全区证据文件不存在：{evidence}"})
    return findings


def build_pack(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    brief = load_json(root / "需求" / "brief.json", {}) or {}
    settings = parse_settings(root / "_设置.md")
    platforms = normalize_platforms(brief, settings)
    placement_rows = normalize_placements(brief)
    for row in placement_rows:
        if row["platform"] not in platforms:
            platforms.append(row["platform"])
    custom_specs = brief.get("platform_specs") if isinstance(brief.get("platform_specs"), Mapping) else {}
    custom_placement_specs = brief.get("placement_specs") if isinstance(brief.get("placement_specs"), Mapping) else {}
    evidence_map = brief.get("platform_safe_zone_evidence") if isinstance(brief.get("platform_safe_zone_evidence"), Mapping) else {}
    specs = {}
    for p in platforms:
        custom = custom_specs.get(p) if isinstance(custom_specs, Mapping) else None
        specs[p] = dict(custom, platform_key="custom") if isinstance(custom, Mapping) else spec_for(p)
        specs[p]["safe_zone_evidence"] = specs[p].get("safe_zone_evidence") or _evidence_for(evidence_map, p, p)
    placement_specs = {}
    for row in placement_rows:
        key = row["key"]
        custom = custom_placement_specs.get(key)
        if isinstance(custom, Mapping):
            spec = dict(custom, platform=row["platform"], placement=row["placement"], placement_key="custom")
        else:
            spec = spec_for_placement(row["platform"], row["placement"])
        spec["safe_zone_evidence"] = spec.get("safe_zone_evidence") or _evidence_for(evidence_map, key, row["platform"])
        spec["safe_zone_evidence_scope"] = _evidence_scope(evidence_map, key, row["platform"])
        placement_specs[key] = spec
    rows = deliverable_rows(brief, settings)
    findings = []
    if not platforms:
        findings.append({"severity": "warn", "code": "platforms_missing", "msg": "brief/_设置.md 未声明目标平台。"})
    placements_by_platform = {row["platform"] for row in placement_rows}
    for platform, spec in specs.items():
        if platform not in placements_by_platform:
            findings.append({"severity": "warn", "code": "placement_missing",
                             "msg": f"{platform} 只声明了平台、未声明实际 placement；平台名不足以确定安全区/时长/声音策略，发布前必须补 brief.placements。"})
            findings.extend(_spec_findings(root, platform, spec))
    for key, spec in placement_specs.items():
        findings.extend(_spec_findings(root, key, spec, placement=True))
        if spec.get("safe_zone_evidence") and spec.get("safe_zone_evidence_scope") != "placement":
            findings.append({"severity": "warn", "code": "safe_zone_evidence_not_placement_specific",
                             "msg": f"{key} 复用了平台级安全区证据；发布前须确认它确实对应当前 placement/caption/anchor。"})
    delivery_map = brief.get("deliverable_placements") if isinstance(brief.get("deliverable_placements"), Mapping) else {}
    placement_keys = set(placement_specs)
    if len(placement_keys) == 1 and not delivery_map:
        only = next(iter(placement_keys))
        delivery_map = {row["deliverable_id"]: [only] for row in rows}
    elif len(placement_keys) > 1 and not delivery_map:
        findings.append({"severity": "block", "code": "deliverable_placement_mapping_missing",
                         "msg": "多 placement 项目缺 brief.deliverable_placements；不能把所有版位约束同时套到每个交付件。"})
    normalized_map = {}
    for did, targets in delivery_map.items():
        targets = targets if isinstance(targets, Sequence) and not isinstance(targets, str) else [targets]
        targets = [str(v).strip() for v in targets if str(v).strip()]
        normalized_map[str(did)] = targets
        unknown = sorted(set(targets) - placement_keys)
        if unknown:
            findings.append({"severity": "block", "code": "deliverable_placement_unknown",
                             "msg": f"交付件 {did} 指向未登记 placement：{', '.join(unknown)}"})
    if placement_keys and normalized_map:
        covered = {target for targets in normalized_map.values() for target in targets}
        uncovered = sorted(placement_keys - covered)
        if uncovered:
            findings.append({"severity": "block", "code": "placement_without_deliverable",
                             "msg": "以下 placement 没有任何交付件：" + ", ".join(uncovered)})
        for row in rows:
            row["target_placements"] = normalized_map.get(row["deliverable_id"], [])
            if not row["target_placements"]:
                findings.append({"severity": "block", "code": "deliverable_without_placement",
                                 "msg": f"交付件 {row['deliverable_id']} 未映射 placement"})
    return {
        "schema_version": 3,
        "kind": KIND,
        "project_root": str(root),
        "platforms": platforms,
        "specs": specs,
        "placements": placement_rows,
        "placement_specs": placement_specs,
        "deliverable_placements": normalized_map,
        "deliverables": rows,
        "summary": {
            "platform_count": len(platforms),
            "placement_count": len(placement_rows),
            "deliverable_count": len(rows),
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
        },
        "findings": findings,
    }


def write_pack(root: Path, out_json: Optional[Path] = None) -> Dict[str, Any]:
    pack = build_pack(root)
    out_json = out_json or (root / "生产数据" / "platform_pack.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pack["_json_path"] = str(out_json)
    return pack


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build ad platform delivery pack")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    pack = write_pack(Path(args.project_root), Path(args.json) if args.json else None)
    s = pack["summary"]
    print(f"# platform_pack platforms={s['platform_count']} deliverables={s['deliverable_count']} warn={s['warn']}")
    print(f"[ok] {pack['_json_path']}")
    return 1 if s.get("block") else 0


if __name__ == "__main__":
    raise SystemExit(main())
