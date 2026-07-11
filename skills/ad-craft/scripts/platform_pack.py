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
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence


KIND = "ad_platform_pack"
PLATFORM_SPECS = {
    "抖音": {
        "aspect": "9:16",
        "min_resolution": "720x1280",
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "required_before_release",
        "text_rules": ["Logo、CTA、法律声明避开右侧互动栏与底部标题区", "首帧/前三秒出现产品或品牌"],
    },
    "小红书": {
        "aspect": "9:16",
        "min_resolution": "720x1280",
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "required_before_release",
        "text_rules": ["封面/首帧要能独立说明卖点", "底部交互区不放关键法律声明"],
    },
    "TikTok": {
        "aspect": "9:16",
        "min_resolution": "720x1280",
        "safe_area": "placement_overlay_aware",
        "safe_zone_asset": "download_current_official_template",
        "text_rules": ["Avoid app UI overlays; keep CTA and logo in safe area", "Hook in the first 3 seconds"],
    },
}


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


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


def build_pack(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    brief = load_json(root / "需求" / "brief.json", {}) or {}
    settings = parse_settings(root / "_设置.md")
    platforms = normalize_platforms(brief, settings)
    custom_specs = brief.get("platform_specs") if isinstance(brief.get("platform_specs"), Mapping) else {}
    evidence_map = brief.get("platform_safe_zone_evidence") if isinstance(brief.get("platform_safe_zone_evidence"), Mapping) else {}
    specs = {}
    for p in platforms:
        custom = custom_specs.get(p) if isinstance(custom_specs, Mapping) else None
        specs[p] = dict(custom, platform_key="custom") if isinstance(custom, Mapping) else spec_for(p)
        specs[p]["safe_zone_evidence"] = specs[p].get("safe_zone_evidence") or evidence_map.get(p) or ""
    rows = deliverable_rows(brief, settings)
    findings = []
    if not platforms:
        findings.append({"severity": "warn", "code": "platforms_missing", "msg": "brief/_设置.md 未声明目标平台。"})
    for platform, spec in specs.items():
        if spec.get("platform_key") == "manual":
            findings.append({"severity": "block", "code": "platform_spec_missing", "msg": f"{platform} 缺官方/客户确认规格；先写 brief.platform_specs 再出视频。"})
        if (spec.get("safe_zone_asset") in {"required_before_release", "download_current_official_template"}
                and not spec.get("safe_zone_evidence")):
            findings.append({"severity": "warn", "code": "safe_zone_asset_pending",
                             "msg": f"{platform} 需在发布前绑定当前 placement/anchor 对应官方安全区模板，不可只用 center 网格。"})
    return {
        "schema_version": 1,
        "kind": KIND,
        "project_root": str(root),
        "platforms": platforms,
        "specs": specs,
        "deliverables": rows,
        "summary": {
            "platform_count": len(platforms),
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
