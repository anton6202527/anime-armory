#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compile the single video render profile for an ad project.

The profile deliberately separates the resolution requested from a generation
backend from the resolution of the encoded delivery master.  A larger encoded
container is therefore never mistaken for native source detail.

Inputs, in precedence order:
1. project-evidenced ``brief.render_profile`` overrides;
2. placement/platform delivery constraints from ``platform_pack``;
3. ``_设置.md`` choices (出视频规格/视频分辨率/交付比例);
4. ad-craft contract defaults.

Output: ``生产数据/render_profile.json``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import contract
import platform_pack


KIND = "ad_render_profile"
SCHEMA_VERSION = 1
PROFILE_REL = "生产数据/render_profile.json"

_LABEL_SHORT_EDGE = {
    "720p": 720,
    "1080p": 1080,
    "1440p": 1440,
    "2160p": 2160,
    "4k": 2160,
    "uhd": 2160,
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_settings(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in read_text(path).splitlines():
        match = re.match(r"\s*[-*]?\s*([^#\n:：|]+?)\s*[:：]\s*(.+?)\s*$", line)
        if match:
            out[match.group(1).strip()] = match.group(2).split("#", 1)[0].strip()
    return out


def normalize_aspect(value: Any, fallback: str = "16:9") -> str:
    raw = str(value or "").strip().lower().replace("x", ":").replace("×", ":")
    if raw == "多比例":
        return contract.MULTI_ASPECT_RATIOS[0]
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)\s*", raw)
    if not match:
        return fallback
    a, b = float(match.group(1)), float(match.group(2))
    if a <= 0 or b <= 0:
        return fallback
    if a.is_integer() and b.is_integer():
        divisor = math.gcd(int(a), int(b))
        return f"{int(a) // divisor}:{int(b) // divisor}"
    return f"{a:g}:{b:g}"


def aspect_value(aspect: str) -> float:
    a, _, b = normalize_aspect(aspect).partition(":")
    return float(a) / float(b)


def _even(value: float) -> int:
    rounded = max(2, int(round(value)))
    return rounded if rounded % 2 == 0 else rounded + 1


def dimensions_for_short_edge(aspect: str, short_edge: int) -> Tuple[int, int]:
    ratio = aspect_value(aspect)
    short_edge = _even(short_edge)
    if ratio > 1:
        return _even(short_edge * ratio), short_edge
    if ratio < 1:
        return short_edge, _even(short_edge / ratio)
    return short_edge, short_edge


def _orient_exact(width: int, height: int, aspect: str) -> Tuple[int, int]:
    ratio = aspect_value(aspect)
    if ratio > 1 and width < height:
        width, height = height, width
    elif ratio < 1 and width > height:
        width, height = height, width
    return _even(width), _even(height)


def parse_resolution(value: Any, aspect: str) -> Optional[Dict[str, Any]]:
    """Parse 720p/1080p/4K or an exact WxH value and orient it to aspect."""
    raw = str(value or "").strip()
    if not raw:
        return None
    exact = re.search(r"(?<!\d)(\d{2,5})\s*[x×]\s*(\d{2,5})(?!\d)", raw, re.I)
    if exact:
        width, height = _orient_exact(int(exact.group(1)), int(exact.group(2)), aspect)
        if abs((width / height) - aspect_value(aspect)) > 0.025:
            return None
        return {
            "width": width,
            "height": height,
            "value": f"{width}x{height}",
            "request_value": f"{width}x{height}",
            "input": raw,
            "kind": "exact",
        }
    folded = re.sub(r"[\s_-]+", "", raw).lower()
    label = next((name for name in _LABEL_SHORT_EDGE if name in folded), None)
    if not label:
        return None
    width, height = dimensions_for_short_edge(aspect, _LABEL_SHORT_EDGE[label])
    canonical = "4K" if label in {"4k", "2160p", "uhd"} else label
    return {
        "width": width,
        "height": height,
        "value": f"{width}x{height}",
        "request_value": canonical,
        "input": raw,
        "kind": "label",
    }


def parse_fps(value: Any) -> Optional[float]:
    raw = str(value or "")
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:fps|帧)", raw, re.I)
    if not match:
        return None
    fps = float(match.group(1))
    return fps if 1 <= fps <= 240 else None


def _resolution_rank(row: Mapping[str, Any]) -> Tuple[int, int, int]:
    width, height = int(row.get("width") or 0), int(row.get("height") or 0)
    return width * height, max(width, height), min(width, height)


def _meets(actual: Mapping[str, Any], required: Mapping[str, Any]) -> bool:
    return (int(actual.get("width") or 0) >= int(required.get("width") or 0)
            and int(actual.get("height") or 0) >= int(required.get("height") or 0))


def _custom_profile(brief: Mapping[str, Any]) -> Dict[str, Any]:
    raw = brief.get("render_profile") or brief.get("video_render_profile") or {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def _section(profile: Mapping[str, Any], key: str) -> Dict[str, Any]:
    raw = profile.get(key)
    return dict(raw) if isinstance(raw, Mapping) else {}


def _constraint_resolution(spec: Mapping[str, Any], aspect: str) -> Optional[Dict[str, Any]]:
    """Return the strongest parseable resolution carried by a placement spec."""
    candidates = []
    groups = (
        ("required", "required_resolution_by_aspect", "required_resolution"),
        ("native", "native_resolution_by_aspect", "native_resolution"),
        ("target", "target_resolution_by_aspect", "target_resolution"),
        ("recommended", "recommended_resolution_by_aspect", "recommended_resolution"),
        ("minimum", "min_resolution_by_aspect", "min_resolution"),
    )
    for tier, map_key, scalar_key in groups:
        mapped = spec.get(map_key)
        raw = mapped.get(aspect) if isinstance(mapped, Mapping) else None
        raw = raw or spec.get(scalar_key)
        parsed = parse_resolution(raw, aspect)
        if parsed:
            candidates.append(dict(parsed, requirement=tier, field=map_key if raw is not spec.get(scalar_key) else scalar_key))
    if not candidates:
        return None
    return max(candidates, key=_resolution_rank)


def _constraint_floor(spec: Mapping[str, Any], aspect: str) -> Optional[Dict[str, Any]]:
    """Parse only hard/native/minimum resolution floors (not recommendations)."""
    candidates = []
    for tier, map_key, scalar_key in (
        ("required", "required_resolution_by_aspect", "required_resolution"),
        ("native", "native_resolution_by_aspect", "native_resolution"),
        ("minimum", "min_resolution_by_aspect", "min_resolution"),
    ):
        mapped = spec.get(map_key)
        raw = mapped.get(aspect) if isinstance(mapped, Mapping) else None
        raw = raw or spec.get(scalar_key)
        parsed = parse_resolution(raw, aspect)
        if parsed:
            candidates.append(dict(parsed, requirement=tier, field=map_key if isinstance(mapped, Mapping) else scalar_key))
    return max(candidates, key=_resolution_rank) if candidates else None


def _constraint_fps(spec: Mapping[str, Any]) -> Optional[float]:
    for key in ("required_fps", "target_fps", "frame_rate", "fps", "recommended_fps"):
        value = spec.get(key)
        if isinstance(value, (int, float)) and 1 <= float(value) <= 240:
            return float(value)
        parsed = parse_fps(value)
        if parsed:
            return parsed
    return None


def _native_required(spec: Mapping[str, Any]) -> bool:
    for key in ("native_resolution_required", "require_native_resolution", "source_resolution_must_meet",
                "native_delivery", "upscale_forbidden"):
        if spec.get(key) is True:
            return True
    policy = str(spec.get("upscale_policy") or "").lower()
    return policy in {"forbid", "forbidden", "native", "native_required", "no_upscale", "禁止放大", "原生"}


def _normalise_policy(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"forbid", "forbidden", "native", "native_required", "no_upscale", "禁止放大", "原生"}:
        return "forbid"
    if raw in {"allow", "allowed", "allow_upscale", "允许", "允许放大"}:
        return "allow"
    return "warn"


def _master_constraints(pack: Mapping[str, Any]) -> list[Dict[str, Any]]:
    placement_specs = pack.get("placement_specs") if isinstance(pack.get("placement_specs"), Mapping) else {}
    mapping = pack.get("deliverable_placements") if isinstance(pack.get("deliverable_placements"), Mapping) else {}
    targets = mapping.get("master") or []
    if isinstance(targets, str):
        targets = [targets]
    if not targets and len(placement_specs) == 1:
        targets = [next(iter(placement_specs))]
    rows = []
    for key in targets:
        spec = placement_specs.get(key)
        if isinstance(spec, Mapping):
            rows.append(dict(spec, _constraint_key=key))
    if rows:
        return rows
    specs = pack.get("specs") if isinstance(pack.get("specs"), Mapping) else {}
    return [dict(spec, _constraint_key=key) for key, spec in specs.items() if isinstance(spec, Mapping)]


def _authority_row(spec: Mapping[str, Any], parsed: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    row = {
        "kind": "placement_or_platform_requirement",
        "key": spec.get("_constraint_key") or spec.get("placement_key") or spec.get("platform_key") or "manual",
        "authority": spec.get("authority") or "project_override",
        "source": spec.get("source") or "",
        "checked_at": spec.get("checked_at") or "",
    }
    if parsed:
        row.update({"field": parsed.get("field"), "requirement": parsed.get("requirement"),
                    "resolution": parsed.get("value")})
    return row


def _source_hashes(root: Path) -> Dict[str, Optional[str]]:
    out: Dict[str, Optional[str]] = {}
    for rel in ("_设置.md", "需求/brief.json"):
        path = root / rel
        out[rel] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return out


def _profile_digest(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compile_profile(root: Path, *, aspect_override: Optional[str] = None,
                    pack: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    root = root.resolve()
    settings = dict(contract.DEFAULT_SETTINGS)
    settings.update(parse_settings(root / "_设置.md"))
    brief = load_json(root / "需求" / "brief.json", {}) or {}
    if not isinstance(brief, Mapping):
        brief = {}
    custom = _custom_profile(brief)
    custom_source = _section(custom, "source_generation")
    custom_master = _section(custom, "master_render")
    deliverables = brief.get("deliverables") if isinstance(brief.get("deliverables"), Mapping) else {}
    aspect_raw = (aspect_override or custom_master.get("aspect") or deliverables.get("aspect")
                  or settings.get("交付比例") or "16:9")
    aspect = normalize_aspect(aspect_raw)
    findings: list[Dict[str, Any]] = []
    aspect_text = str(aspect_raw or "").strip().lower().replace("x", ":").replace("×", ":")
    if aspect_text != "多比例" and not re.fullmatch(r"\s*\d+(?:\.\d+)?\s*:\s*\d+(?:\.\d+)?\s*", aspect_text):
        findings.append({
            "severity": "block", "code": "render_aspect_unadapted",
            "msg": f"交付比例={aspect_raw!r} 无法归一；自定义比例须写 W:H 或在 brief.render_profile.master_render.aspect 给出。",
        })

    spec_name = str(settings.get("出视频规格") or contract.DEFAULT_SETTINGS["出视频规格"])
    try:
        budget = contract.video_spec_profile(spec_name)
    except KeyError:
        budget = contract.video_spec_profile(contract.DEFAULT_SETTINGS["出视频规格"])
        if not parse_fps(spec_name) and not custom_source:
            findings.append({
                "severity": "block", "code": "custom_video_spec_unadapted",
                "msg": f"出视频规格={spec_name!r} 未给出可执行 fps/source_generation override。",
            })

    source_resolution_raw = (custom_source.get("resolution") or custom_source.get("size")
                             or settings.get("视频分辨率") or budget.get("resolution"))
    source_resolution = parse_resolution(source_resolution_raw, aspect)
    if source_resolution is None:
        findings.append({
            "severity": "block", "code": "source_resolution_unadapted",
            "msg": f"视频分辨率={source_resolution_raw!r} 无法归一；自定义值须写 720p/1080p/4K 或 WxH。",
        })
        source_resolution = parse_resolution(contract.DEFAULT_SETTINGS["视频分辨率"], aspect)
        assert source_resolution is not None
    source_fps = (float(custom_source["fps"]) if isinstance(custom_source.get("fps"), (int, float))
                  else parse_fps(custom_source.get("fps")) or parse_fps(spec_name) or float(budget["fps"]))
    if not 1 <= source_fps <= 240:
        findings.append({"severity": "block", "code": "source_fps_invalid", "msg": f"source fps={source_fps} 超出 1-240。"})

    delivery_pack = dict(pack) if isinstance(pack, Mapping) else platform_pack.build_pack(root)
    input_hashes = _source_hashes(root)
    input_hashes["生产数据/platform_pack.json"] = _profile_digest(
        {key: value for key, value in delivery_pack.items() if not str(key).startswith("_")})
    for row in delivery_pack.get("findings") or []:
        if isinstance(row, Mapping) and row.get("severity") in {"block", "warn"}:
            findings.append(dict(row, source_component="platform_pack"))
    constraints = _master_constraints(delivery_pack)
    target_candidates = []
    floor_candidates = []
    fps_candidates = []
    authority_master = []
    native_required = False
    for spec in constraints:
        allowed = spec.get("allowed_aspects") or []
        fixed_aspect = str(spec.get("aspect") or "")
        if allowed and aspect not in allowed:
            findings.append({
                "severity": "block", "code": "render_aspect_not_allowed",
                "msg": f"{spec.get('_constraint_key')} 不接受母版比例 {aspect}；allowed={allowed}。",
            })
        elif fixed_aspect and fixed_aspect not in {"placement_dependent", aspect}:
            findings.append({
                "severity": "block", "code": "render_aspect_mismatch",
                "msg": f"{spec.get('_constraint_key')} 要求 {fixed_aspect}，当前母版为 {aspect}。",
            })
        parsed = _constraint_resolution(spec, aspect)
        if parsed:
            target_candidates.append(parsed)
        floor = _constraint_floor(spec, aspect)
        if floor:
            floor_candidates.append(floor)
        fps = _constraint_fps(spec)
        if fps:
            fps_candidates.append(fps)
        native_required = native_required or _native_required(spec)
        authority_master.append(_authority_row(spec, parsed))

    platform_target = max(target_candidates, key=_resolution_rank) if target_candidates else None
    platform_floor = max(floor_candidates, key=_resolution_rank) if floor_candidates else None
    master_override_raw = custom_master.get("resolution") or custom_master.get("size")
    master_override = parse_resolution(master_override_raw, aspect) if master_override_raw else None
    if master_override_raw and master_override is None:
        findings.append({
            "severity": "block", "code": "master_resolution_unadapted",
            "msg": f"brief.render_profile.master_render.resolution={master_override_raw!r} 无法归一。",
        })
    master_resolution = dict(master_override or platform_target or source_resolution)
    if master_override and platform_floor and not _meets(master_override, platform_floor):
        findings.append({
            "severity": "block", "code": "custom_master_below_delivery_requirement",
            "msg": f"自定义母版 {master_override['value']} 低于 placement/交付最低要求 {platform_floor['value']}。",
        })
    elif master_override and platform_target and not _meets(master_override, platform_target):
        findings.append({
            "severity": "warn", "code": "custom_master_below_delivery_recommendation",
            "msg": f"自定义母版 {master_override['value']} 低于 placement 推荐 {platform_target['value']}；已尊重项目覆盖并留痕。",
        })
    master_fps_raw = custom_master.get("fps")
    if isinstance(master_fps_raw, (int, float)):
        master_fps = float(master_fps_raw)
    else:
        master_fps = parse_fps(master_fps_raw) or (max(fps_candidates) if fps_candidates else source_fps)
    if not 1 <= master_fps <= 240:
        findings.append({"severity": "block", "code": "master_fps_invalid", "msg": f"master fps={master_fps} 超出 1-240。"})

    policy = _normalise_policy(custom.get("upscale_policy") or custom_master.get("upscale_policy"))
    native_required = native_required or policy == "forbid"
    requires_upscale = not _meets(source_resolution, master_resolution)
    scale_factor = max(
        float(master_resolution["width"]) / max(1, float(source_resolution["width"])),
        float(master_resolution["height"]) / max(1, float(source_resolution["height"])),
    )
    if requires_upscale:
        severity = "block" if native_required else "warn"
        code = "native_resolution_source_below_requirement" if native_required else "container_upscale_only"
        msg = (f"生成源有效分辨率 {source_resolution['value']}，母版容器 {master_resolution['value']}；"
               + ("当前 placement/项目要求原生分辨率，禁止以容器放大冒充原生交付。"
                  if native_required else "编码会放大容器但不会增加原生细节，已显式留痕。"))
        findings.append({"severity": severity, "code": code, "msg": msg})

    provenance = {key: custom.get(key) for key in ("source", "checked_at", "approved_by") if custom.get(key)}
    if custom and not provenance.get("source"):
        findings.append({
            "severity": "warn", "code": "custom_render_profile_provenance_incomplete",
            "msg": "brief.render_profile 是项目覆盖但缺 source；可生产，客户/平台交付前须绑定书面规格来源。",
        })

    source_authority = [
        {"kind": "project_setting", "source": "_设置.md:视频分辨率", "value": str(source_resolution_raw)},
        {"kind": "project_setting", "source": "_设置.md:出视频规格", "value": spec_name},
    ]
    if custom_source:
        source_authority.insert(0, {
            "kind": "project_override", "source": custom.get("source") or "brief.render_profile.source_generation",
            "approved_by": custom.get("approved_by") or "", "resolution": source_resolution["value"], "fps": source_fps,
        })
    master_authority = list(authority_master)
    if master_override:
        master_authority.insert(0, {
            "kind": "project_override", "authority": "project_override",
            "source": custom.get("source") or "brief.render_profile.master_render",
            "approved_by": custom.get("approved_by") or "", "resolution": master_override["value"], "fps": master_fps,
        })
    if not master_authority:
        master_authority = [{
            "kind": "source_passthrough", "authority": "project_setting",
            "source": "无更高 placement/客户目标；保持生成源分辨率",
        }]

    payload: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "project_root": str(root),
        "source_generation": {
            "resolution": source_resolution["value"],
            "width": source_resolution["width"],
            "height": source_resolution["height"],
            "backend_request_resolution": source_resolution["request_value"],
            "fps": source_fps,
            "aspect": aspect,
            "quality_profile": spec_name,
            "effective_source_resolution": source_resolution["value"],
            "authority": source_authority,
        },
        "master_render": {
            "resolution": master_resolution["value"],
            "width": master_resolution["width"],
            "height": master_resolution["height"],
            "fps": master_fps,
            "aspect": aspect,
            "authority": master_authority,
        },
        "upscale": {
            "policy": policy,
            "required": requires_upscale,
            "native_resolution_required": native_required,
            "effective_source_resolution": source_resolution["value"],
            "container_resolution": master_resolution["value"],
            "scale_factor": round(scale_factor, 4),
            "quality_claim": "container_upscale_only" if requires_upscale else "native_source_sufficient",
        },
        "frame_rate_conversion": {
            "required": abs(master_fps - source_fps) > 0.01,
            "source_fps": source_fps,
            "master_fps": master_fps,
            "method": "duplicate_or_drop_frames" if abs(master_fps - source_fps) > 0.01 else "none",
        },
        "authority": {
            "source_generation": "_设置.md:视频分辨率 + _设置.md:出视频规格 + brief.render_profile override",
            "master_render": master_authority,
            "precedence": ["brief.render_profile", "placement_or_platform_requirement", "project_settings", "ad_contract_default"],
        },
        "custom_override": provenance,
        "input_sha256": input_hashes,
        "summary": {
            "block": sum(1 for row in findings if row["severity"] == "block"),
            "warn": sum(1 for row in findings if row["severity"] == "warn"),
        },
        "findings": findings,
    }
    payload["profile_sha256"] = _profile_digest(payload)
    return payload


def write_profile(root: Path, out_json: Optional[Path] = None, *,
                  aspect_override: Optional[str] = None,
                  pack: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    root = root.resolve()
    # Keep platform_pack materialised beside the render profile so both consumers
    # see the same placement snapshot in this invocation.
    current_pack = dict(pack) if isinstance(pack, Mapping) else platform_pack.write_pack(root)
    payload = compile_profile(root, aspect_override=aspect_override, pack=current_pack)
    out_json = out_json or (root / PROFILE_REL)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload["_json_path"] = str(out_json)
    return payload


def compact_ref(profile: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "path": PROFILE_REL,
        "sha256": profile.get("profile_sha256"),
        "source_generation": dict(profile.get("source_generation") or {}),
        "master_render": dict(profile.get("master_render") or {}),
        "upscale": dict(profile.get("upscale") or {}),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="compile ad source/master render profile")
    ap.add_argument("project_root")
    ap.add_argument("--json", default=None)
    ap.add_argument("--aspect", default=None, help="本次母版画幅；省略则读 brief/_设置.md")
    ap.add_argument("--shell", action="store_true", help="仅输出 compose 可读 TSV: width height fps aspect source_w source_h policy")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root)
    profile = write_profile(root, Path(ns.json) if ns.json else None, aspect_override=ns.aspect)
    if ns.shell:
        source = profile["source_generation"]
        master = profile["master_render"]
        upscale = profile["upscale"]
        print("\t".join(str(value) for value in (
            master["width"], master["height"], master["fps"], master["aspect"],
            source["width"], source["height"], upscale["policy"], upscale["quality_claim"],
        )))
        for finding in profile["findings"]:
            print(f"[{finding['severity']}] {finding['code']}: {finding['msg']}", file=sys.stderr)
    else:
        summary = profile["summary"]
        print(f"# render profile source={profile['source_generation']['resolution']}@{profile['source_generation']['fps']:g} "
              f"master={profile['master_render']['resolution']}@{profile['master_render']['fps']:g} "
              f"block={summary['block']} warn={summary['warn']}")
        print(f"[ok] {profile['_json_path']}")
    return 1 if profile["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
