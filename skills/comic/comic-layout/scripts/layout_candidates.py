#!/usr/bin/env python3
"""Generate, preview and rank deterministic Comic layout candidates."""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("comic_layout_candidate_builder", HERE / "build_layout.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(builder)


PARAMETERS = (
    {"candidate_id": "balanced", "max_segment_height": 16000, "gutter": 140},
    {"candidate_id": "fast_read", "max_segment_height": 12000, "gutter": 96},
    {"candidate_id": "dramatic_pause", "max_segment_height": 18000, "gutter": 190},
)
CROSS_PAGE_MODES = {"cross_page_art", "cross-page-art", "binding_crossing", "跨页", "跨页画面"}


def _sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def has_protected_complex_layout(name_board: Mapping[str, Any]) -> bool:
    """Protect only explicit binding-crossing art, never ordinary spread ids."""
    for page in name_board.get("pages") or []:
        if not isinstance(page, Mapping):
            continue
        if page.get("cross_page_art") is True:
            return True
        if str(page.get("spread_mode") or "").strip().lower() in CROSS_PAGE_MODES:
            return True
    return False


def _rect_intersection_area(left: Mapping[str, Any], right: Mapping[str, Any]) -> int:
    x1 = max(int(left.get("x") or 0), int(right.get("x") or 0))
    y1 = max(int(left.get("y") or 0), int(right.get("y") or 0))
    x2 = min(int(left.get("x") or 0) + int(left.get("w") or 0), int(right.get("x") or 0) + int(right.get("w") or 0))
    y2 = min(int(left.get("y") or 0) + int(left.get("h") or 0), int(right.get("y") or 0) + int(right.get("h") or 0))
    return max(0, x2 - x1) * max(0, y2 - y1)


def _continuous_geometry(layout: Mapping[str, Any]) -> tuple[int, int, list[dict[str, Any]]]:
    width = max(1, int((layout.get("canvas") or {}).get("width") or 1440))
    segment_gap = max(24, width // 24)
    cursor = 0
    panels: list[dict[str, Any]] = []
    for segment in layout.get("segments") or []:
        if not isinstance(segment, Mapping):
            continue
        for panel in segment.get("panels") or []:
            if isinstance(panel, Mapping):
                panels.append({**dict(panel), "y": int(panel.get("y") or 0) + cursor})
        cursor += int(segment.get("height") or 0) + segment_gap
    return width, max(1, cursor - segment_gap), panels


def preview_evidence(layout: Mapping[str, Any]) -> dict[str, Any]:
    """Derive advisory signals from the exact geometry rendered for review."""
    profile = str(layout.get("geometry_profile") or "")
    if profile == "longstrip_single_column":
        width, height, panels = _continuous_geometry(layout)
        viewport_h = max(1, int(round(width * 16 / 9)))
        frame_count = max(1, math.ceil(height / viewport_h))
        frames: list[dict[str, Any]] = []
        for index in range(frame_count):
            frame = {"x": 0, "y": index * viewport_h, "w": width, "h": min(viewport_h, max(1, height - index * viewport_h))}
            intersections = [_rect_intersection_area(frame, panel) for panel in panels]
            visible = [panel for panel, area in zip(panels, intersections) if area > 0]
            coverage = min(1.0, sum(intersections) / max(1, int(frame["w"]) * int(frame["h"])))
            frames.append({
                "frame": index + 1,
                "y_range": [int(frame["y"]), int(frame["y"]) + int(frame["h"])],
                "panel_ids": [str(panel.get("panel_id") or "") for panel in visible],
                "coverage_ratio": round(coverage, 4),
            })
        dead_air = sum(frame["coverage_ratio"] < 0.08 for frame in frames)
        overcrowded = sum(len(frame["panel_ids"]) > 6 for frame in frames)
        tiny = sum(
            int(panel.get("w") or 0) < width * 0.32 or int(panel.get("h") or 0) < viewport_h * 0.08
            for panel in panels
        )
        metrics = {
            "frame_count": frame_count,
            "dead_air_frames": dead_air,
            "overcrowded_frames": overcrowded,
            "tiny_panel_count": tiny,
            "mean_coverage_ratio": round(sum(frame["coverage_ratio"] for frame in frames) / len(frames), 4),
            "score_delta": -dead_air * 6 - overcrowded * 3 - tiny * 2,
        }
        return {
            "kind": "continuous_phone_screen_beats",
            "viewport": {"width": width, "height": viewport_h, "aspect_ratio": "9:16"},
            "canvas": {"width": width, "height": height},
            "frames": frames,
            "metrics": metrics,
            "advisory_only": True,
        }

    segments = [segment for segment in layout.get("segments") or [] if isinstance(segment, Mapping)]
    pages: list[dict[str, Any]] = []
    near_spine_slots = 0
    tiny = 0
    for index, segment in enumerate(segments, 1):
        width = max(1, int(segment.get("width") or 1))
        height = max(1, int(segment.get("height") or 1))
        side = str(segment.get("page_side") or "")
        panel_area = 0
        for panel in segment.get("panels") or []:
            if not isinstance(panel, Mapping):
                continue
            panel_area += max(0, int(panel.get("w") or 0)) * max(0, int(panel.get("h") or 0))
            if int(panel.get("w") or 0) * int(panel.get("h") or 0) < width * height * 0.035:
                tiny += 1
            for slot in panel.get("bubble_slots") or []:
                if not isinstance(slot, Mapping):
                    continue
                center_x = int(slot.get("x") or 0) + int(slot.get("w") or 0) / 2
                if (side == "left" and center_x > width * 0.82) or (side == "right" and center_x < width * 0.18):
                    near_spine_slots += 1
        pages.append({
            "page": index,
            "segment_id": str(segment.get("segment_id") or f"PAGE_{index:03d}"),
            "page_side": side,
            "spread_id": str(segment.get("spread_id") or ""),
            "fill_ratio": round(min(1.0, panel_area / (width * height)), 4),
            "panel_ids": [str(panel.get("panel_id") or "") for panel in segment.get("panels") or [] if isinstance(panel, Mapping)],
        })
    pairs = [pages[start:start + 2] for start in range(0, len(pages), 2)]
    metrics = {
        "page_count": len(pages),
        "spread_count": len(pairs),
        "near_spine_bubble_count": near_spine_slots,
        "tiny_panel_count": tiny,
        "mean_page_fill_ratio": round(sum(page["fill_ratio"] for page in pages) / max(1, len(pages)), 4),
        "score_delta": -near_spine_slots * 3 - tiny * 2,
    }
    return {
        "kind": "spread_page_turn_contact_sheet",
        "pages": pages,
        "spreads": [[page["segment_id"] for page in pair] for pair in pairs],
        "metrics": metrics,
        "advisory_only": True,
    }


def preview_svg(layout: Mapping[str, Any], evidence: Mapping[str, Any]) -> str:
    kind = str(evidence.get("kind") or "")
    if kind == "continuous_phone_screen_beats":
        width = int((evidence.get("canvas") or {}).get("width") or 1440)
        height = int((evidence.get("canvas") or {}).get("height") or 1)
        _width, _height, panels = _continuous_geometry(layout)
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#151719"/>',
        ]
        for index, panel in enumerate(panels, 1):
            x, y, w, h = (int(panel.get(key) or 0) for key in ("x", "y", "w", "h"))
            pid = html.escape(str(panel.get("panel_id") or f"P{index:03d}"))
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#d8d2c8" stroke="#f2eee7" stroke-width="4"/>')
            parts.append(f'<text x="{x + 18}" y="{y + 42}" fill="#17191b" font-size="28" font-family="sans-serif">{pid}</text>')
        viewport_h = int((evidence.get("viewport") or {}).get("height") or max(1, width * 16 // 9))
        for frame in evidence.get("frames") or []:
            y = int((frame.get("y_range") or [0])[0])
            parts.append(f'<rect x="2" y="{y + 2}" width="{max(1, width - 4)}" height="{max(1, min(viewport_h - 4, height - y - 2))}" fill="none" stroke="#50d6c4" stroke-width="4" stroke-dasharray="18 12"/>')
            parts.append(f'<text x="18" y="{y + 34}" fill="#50d6c4" font-size="24" font-family="sans-serif">screen {int(frame.get("frame") or 0)}</text>')
        parts.append("</svg>")
        return "\n".join(parts) + "\n"

    segments = [segment for segment in layout.get("segments") or [] if isinstance(segment, Mapping)]
    thumb_w, gap, label_h = 420, 52, 48
    max_source_w = max((int(segment.get("width") or 1) for segment in segments), default=1)
    max_source_h = max((int(segment.get("height") or 1) for segment in segments), default=1)
    thumb_h = max(300, int(max_source_h / max_source_w * thumb_w))
    rows = max(1, math.ceil(len(segments) / 2))
    width = thumb_w * 2 + gap * 3
    height = rows * (thumb_h + label_h + gap) + gap
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#151719"/>',
    ]
    for index, segment in enumerate(segments):
        row, col = divmod(index, 2)
        source_w, source_h = max(1, int(segment.get("width") or 1)), max(1, int(segment.get("height") or 1))
        scale = min(thumb_w / source_w, thumb_h / source_h)
        page_w, page_h = int(source_w * scale), int(source_h * scale)
        x0 = gap + col * (thumb_w + gap) + (thumb_w - page_w) // 2
        y0 = gap + row * (thumb_h + label_h + gap)
        label = html.escape(f"{segment.get('segment_id', '')} · {segment.get('page_side', '')}")
        parts.append(f'<rect x="{x0}" y="{y0}" width="{page_w}" height="{page_h}" fill="#f7f4ee" stroke="#777" stroke-width="3"/>')
        for panel in segment.get("panels") or []:
            if not isinstance(panel, Mapping):
                continue
            x = x0 + int(int(panel.get("x") or 0) * scale)
            y = y0 + int(int(panel.get("y") or 0) * scale)
            w = max(1, int(int(panel.get("w") or 0) * scale))
            h = max(1, int(int(panel.get("h") or 0) * scale))
            pid = html.escape(str(panel.get("panel_id") or ""))
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#d8d2c8" stroke="#222" stroke-width="2"/>')
            parts.append(f'<text x="{x + 7}" y="{y + 20}" fill="#222" font-size="16" font-family="sans-serif">{pid}</text>')
        parts.append(f'<text x="{x0}" y="{y0 + page_h + 32}" fill="#50d6c4" font-size="22" font-family="sans-serif">{label}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def score(layout: Mapping[str, Any], preview: Mapping[str, Any] | None = None) -> dict[str, Any]:
    panels = [panel for segment in layout.get("segments") or [] for panel in segment.get("panels") or [] if isinstance(panel, Mapping)]
    eye_path = sum(bool(panel.get("eye_flow_entry") or panel.get("eye_flow_exit")) for panel in panels)
    bubble_slots = sum(len(panel.get("bubble_slots") or []) for panel in panels)
    overflow_risk = sum(len(panel.get("bubble_slots") or []) > 4 for panel in panels)
    safe_area = sum(all(int(panel.get(key) or 0) >= 0 for key in ("x", "y", "w", "h")) for panel in panels)
    page_turns = sum(bool(panel.get("page_turn_hook")) for panel in panels)
    shapes = [str(panel.get("panel_shape") or "standard") for panel in panels]
    repetition = max(0, len(shapes) - len(set(shapes)))
    preview = dict(preview or preview_evidence(layout))
    preview_delta = int((preview.get("metrics") or {}).get("score_delta") or 0)
    total = 50 + eye_path * 2 + safe_area + page_turns * 3 - overflow_risk * 8 - repetition + preview_delta
    return {
        "total": total, "eye_path_contracts": eye_path, "bubble_slot_count": bubble_slots,
        "bubble_overflow_risk": overflow_risk, "safe_area_panels": safe_area,
        "page_turn_hooks": page_turns, "repeated_composition_penalty": repetition,
        "preview_geometry_delta": preview_delta,
    }


def build(root: Path, chapter: str) -> dict[str, Any]:
    name = builder.load_json(root / "排版" / chapter / "name_board.json")
    protected = has_protected_complex_layout(name)
    candidates = []
    for params in PARAMETERS:
        layout = builder.build_layout(
            root,
            chapter,
            params["max_segment_height"],
            params["gutter"],
            honor_candidate_selection=False,
        )
        evidence = preview_evidence(layout)
        svg = preview_svg(layout, evidence)
        candidates.append({
            **params,
            "layout_sha256": _sha(layout),
            "preview_evidence": {**evidence, "svg_sha256": _sha_text(svg)},
            "score": score(layout, evidence),
            "layout": layout,
        })
    candidates.sort(key=lambda row: (-row["score"]["total"], row["candidate_id"]))
    return {
        "schema_version": 2, "kind": "comic_layout_candidates", "chapter": chapter,
        "input_bindings": {
            "panel_script_sha256": builder.sha256_file(root / "脚本" / chapter / "panel_script.json"),
            "name_board_sha256": builder.sha256_file(root / "排版" / chapter / "name_board.json"),
            "settings_sha256": builder.sha256_file(root / "_设置.md"),
        },
        "protected_complex_layout": protected,
        "selection_policy": "human_required_for_cross_page_art" if protected else "highest_preview_grounded_deterministic_score_may_apply_under_delegated_editorial_policy",
        "recommended_candidate_id": candidates[0]["candidate_id"], "candidates": candidates,
    }


def write(root: Path, chapter: str, payload: Mapping[str, Any], *, apply_best: bool) -> tuple[Path, Path | None]:
    serializable = json.loads(json.dumps(dict(payload), ensure_ascii=False))
    path = root / "排版" / chapter / "layout_candidates.json"
    preview_dir = path.parent / "layout_previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    for candidate in serializable.get("candidates") or []:
        evidence = candidate.get("preview_evidence") or preview_evidence(candidate.get("layout") or {})
        svg = preview_svg(candidate.get("layout") or {}, evidence)
        suffix = "screen_beats" if evidence.get("kind") == "continuous_phone_screen_beats" else "page_turn_contact_sheet"
        preview_path = preview_dir / f"{candidate.get('candidate_id')}_{suffix}.svg"
        preview_path.write_text(svg, encoding="utf-8")
        evidence["path"] = str(preview_path.relative_to(root))
        evidence["svg_sha256"] = _sha_text(svg)
        candidate["preview_evidence"] = evidence
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    selection = None
    if apply_best:
        if serializable.get("protected_complex_layout"):
            raise ValueError("explicit cross-page art is protected and cannot auto-apply")
        best = (serializable.get("candidates") or [])[0]
        selection = path.with_name("layout_candidate_selection.json")
        preview = best.get("preview_evidence") or {}
        record = {
            "schema_version": 2, "kind": "comic_layout_candidate_selection", "chapter": chapter,
            "candidate_id": best["candidate_id"], "max_segment_height": best["max_segment_height"], "gutter": best["gutter"],
            "layout_sha256": best["layout_sha256"], "score": best["score"],
            "preview_evidence": {
                "kind": preview.get("kind"), "path": preview.get("path"), "svg_sha256": preview.get("svg_sha256"),
                "metrics": preview.get("metrics"), "advisory_only": True,
            },
            "input_bindings": serializable["input_bindings"], "human_signoff": False,
        }
        selection.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path, selection


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("project_root"); parser.add_argument("--chapter", default="第1话"); parser.add_argument("--apply-best", action="store_true"); parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv); root = Path(args.project_root).expanduser().resolve()
    try: payload = build(root, args.chapter); outputs = write(root, args.chapter, payload, apply_best=args.apply_best)
    except (ValueError, builder.LayoutError) as exc: print(f"[err] {exc}"); return 2
    if args.json: print(json.dumps({"report": payload, "outputs": [str(item) for item in outputs if item]}, ensure_ascii=False, indent=2))
    else: print(f"recommended={payload['recommended_candidate_id']} protected={payload['protected_complex_layout']}")
    return 0


if __name__ == "__main__": raise SystemExit(main())
