#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画面板风格一致性机检。

This gate is intentionally self-contained inside the comic line; do not import
modules from other production lines into the comic pipeline.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


DEFAULT_MARGIN = 0.04
DEFAULT_BINS = 16
EDGE_WEIGHT_DIMS = 4
GRADE_WARMTH_MARGIN = 0.20
GRADE_TINT_MARGIN = 0.18


def _norm_bucket(value: str) -> str:
    return re.sub(r"\s+", "_", str(value or "").strip())[:32] or "unknown"


def style_context_bucket(location: str, explicit: str = "") -> str:
    """Group panels whose planned scene lighting/content should be compared together."""
    if str(explicit or "").strip():
        return _norm_bucket(explicit)
    loc = (location or "unknown").strip()
    if any(token in loc for token in ("山", "林", "坡", "岭", "野外", "荒野")):
        return "outdoor_mountain"
    if any(token in loc for token in ("水", "泉", "潭", "河", "湖", "海", "雨")):
        return "water_or_rain"
    if any(token in loc for token in ("殿", "堂", "厅", "馆", "庙", "祠")):
        return "hall_interior"
    if any(token in loc for token in ("院", "庭", "园", "校场", "广场")):
        return "yard_or_courtyard"
    if any(token in loc for token in ("房", "室", "屋", "寝", "床", "门口")):
        return "room_interior"
    if any(token in loc for token in ("街", "市", "巷", "城", "码头")):
        return "street_or_city"
    if any(token in loc for token in ("回忆", "梦", "幻", "蒙太奇")):
        return "montage"
    return _norm_bucket(loc)


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def read_setting(root: Path, key: str, default: str = "") -> str:
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in read_text(root / "_设置.md").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def normalize_generation_source(value: Any) -> str:
    source = str(value or "").strip()
    if "+" in source:
        source = source.split("+", 1)[0].strip()
    return source


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def median(values: Sequence[float]) -> float:
    vals = sorted(values)
    if not vals:
        return 0.0
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return (vals[mid - 1] + vals[mid]) / 2.0


def channel_hist(values: Sequence[float], bins: int) -> list[float]:
    hist = [0.0] * bins
    if not values:
        return hist
    for value in values:
        idx = min(bins - 1, max(0, int(value * bins)))
        hist[idx] += 1.0
    total = float(len(values))
    return [item / total for item in hist]


def style_band(cohesion: float, floor: float, margin: float) -> str:
    if cohesion >= floor - margin:
        return "ok"
    if cohesion >= floor - 2 * margin:
        return "warn"
    return "block"


def grade_proxy(r: float, g: float, b: float) -> tuple[float, float]:
    eps = 1e-6
    warmth = math.log((r + eps) / (b + eps))
    tint = math.log((g + eps) / math.sqrt((r + eps) * (b + eps)))
    return warmth, tint


def probe_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


def image_data(image: Any) -> list[Any]:
    getter = getattr(image, "get_flattened_data", None)
    if callable(getter):
        return list(getter())
    return list(image.getdata())


def image_fingerprint(path: Path, bins: int) -> dict[str, Any] | None:
    try:
        from PIL import Image, ImageFilter, ImageStat
    except Exception:
        return None
    try:
        image = Image.open(path).convert("RGB")
    except OSError:
        return None
    source_size = image.size
    sample = image.copy()
    sample.thumbnail((160, 160))
    hsv = sample.convert("HSV")
    pixels = image_data(hsv)
    sat = [s / 255.0 for (_h, s, _v) in pixels]
    val = [v / 255.0 for (_h, _s, v) in pixels]
    edges = sample.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_values = image_data(edges)
    edge_density = (sum(edge_values) / len(edge_values) / 255.0) if edge_values else 0.0
    means = ImageStat.Stat(sample).mean
    warmth, tint = grade_proxy(float(means[0]), float(means[1]), float(means[2]))
    fp = channel_hist(sat, bins) + channel_hist(val, bins) + [edge_density] * EDGE_WEIGHT_DIMS
    return {
        "fingerprint": fp,
        "size": {"width": source_size[0], "height": source_size[1]},
        "sat_mean": sum(sat) / len(sat) if sat else 0.0,
        "val_mean": sum(val) / len(val) if val else 0.0,
        "edge_density": edge_density,
        "warmth": warmth,
        "tint": tint,
    }


def internal_gutter_count(path: Path) -> int:
    try:
        from PIL import Image, ImageStat
    except Exception:
        return 0
    try:
        image = Image.open(path).convert("RGB")
    except OSError:
        return 0
    image.thumbnail((360, 360))
    w, h = image.size
    if w < 120 or h < 120:
        return 0
    gray = image.convert("L")
    pix = gray.load()
    def scan_axis(length: int, other: int, getter: Any) -> int:
        means: list[float] = []
        stdevs: list[float] = []
        dark_ratios: list[float] = []
        light_ratios: list[float] = []
        for i in range(length):
            values = [getter(i, j) for j in range(other)]
            mean = sum(values) / max(len(values), 1)
            var = sum((value - mean) ** 2 for value in values) / max(len(values), 1)
            means.append(mean)
            stdevs.append(math.sqrt(var))
            dark_ratios.append(sum(1 for value in values if value < 28) / other)
            light_ratios.append(sum(1 for value in values if value > 228) / other)

        candidates: list[tuple[int, int, str]] = []
        in_run = False
        run_len = 0
        run_start = 0
        run_kind = ""
        for i in range(max(6, length // 20), min(length - 6, length - length // 20)):
            kind = ""
            if dark_ratios[i] > 0.94 and means[i] < 22 and stdevs[i] < 18:
                kind = "dark"
            elif light_ratios[i] > 0.90 and means[i] > 218 and stdevs[i] < 20:
                kind = "light"
            if kind:
                if not in_run:
                    run_start = i
                    run_kind = kind
                if kind == run_kind:
                    run_len += 1
                else:
                    if 2 <= run_len <= max(12, length // 22):
                        candidates.append((run_start, i - 1, run_kind))
                    run_start = i
                    run_len = 1
                    run_kind = kind
                in_run = True
            elif in_run:
                if 2 <= run_len <= max(12, length // 22):
                    candidates.append((run_start, i - 1, run_kind))
                in_run = False
                run_len = 0
                run_kind = ""
        if in_run and 2 <= run_len <= max(12, length // 22):
            candidates.append((run_start, min(length - 7, run_start + run_len - 1), run_kind))

        confirmed = 0
        for start, end, kind in candidates:
            left0 = max(0, start - 14)
            left1 = max(0, start - 4)
            right0 = min(length, end + 4)
            right1 = min(length, end + 14)
            if left1 <= left0 or right1 <= right0:
                continue
            left_mean = sum(means[left0:left1]) / (left1 - left0)
            right_mean = sum(means[right0:right1]) / (right1 - right0)
            if kind == "dark":
                ok = left_mean > 42 and right_mean > 42 and abs(left_mean - right_mean) < 110
            else:
                ok = left_mean < 205 and right_mean < 205 and abs(left_mean - right_mean) < 130
            if ok:
                confirmed += 1
        return confirmed

    vertical = scan_axis(w, h, lambda x, y: pix[x, y])
    horizontal = scan_axis(h, w, lambda y, x: pix[x, y])
    return vertical + horizontal


def outer_frame_edges(path: Path) -> int:
    try:
        from PIL import Image, ImageStat
    except Exception:
        return 0
    try:
        image = Image.open(path).convert("L")
    except OSError:
        return 0
    w, h = image.size
    if w < 120 or h < 120:
        return 0
    band = max(2, min(8, min(w, h) // 300))
    inset = band * 3
    edges = {
        "top": ((0, 0, w, band), (0, inset, w, inset + band)),
        "bottom": ((0, h - band, w, h), (0, h - inset - band, w, h - inset)),
        "left": ((0, 0, band, h), (inset, 0, inset + band, h)),
        "right": ((w - band, 0, w, h), (w - inset - band, 0, w - inset, h)),
    }
    count = 0
    for outer_box, inner_box in edges.values():
        outer = ImageStat.Stat(image.crop(outer_box))
        inner = ImageStat.Stat(image.crop(inner_box))
        outer_mean = float(outer.mean[0])
        outer_std = float(outer.stddev[0])
        inner_mean = float(inner.mean[0])
        light_frame = outer_mean > 190 and outer_std < 14 and inner_mean < 165 and outer_mean - inner_mean > 55
        dark_frame = outer_mean < 28 and outer_std < 14 and inner_mean > 55 and inner_mean - outer_mean > 35
        if light_frame or dark_frame:
            count += 1
    return count


def panel_order(root: Path, chapter: str) -> list[str]:
    jobs = load_json(root / "出图" / chapter / "prompt" / "panel_jobs.json", {})
    ids = [str(job.get("panel_id")) for job in jobs.get("jobs") or [] if job.get("panel_id")]
    if ids:
        return ids
    script = load_json(root / "脚本" / chapter / "panel_script.json", {})
    return [str(panel.get("panel_id")) for panel in script.get("panels") or [] if panel.get("panel_id")]


def panel_contexts(root: Path, chapter: str) -> dict[str, dict[str, str]]:
    script = load_json(root / "脚本" / chapter / "panel_script.json", {})
    out: dict[str, dict[str, str]] = {}
    for panel in script.get("panels") or []:
        pid = str(panel.get("panel_id") or "")
        if pid:
            explicit = str(panel.get("style_bucket") or panel.get("scene_family") or panel.get("visual_context") or "").strip()
            out[pid] = {
                "location": str(panel.get("location") or "unknown").strip() or "unknown",
                "style_bucket": explicit,
            }
    return out


def find_panel(root: Path, chapter: str, panel_id: str) -> Path | None:
    base = root / "出图" / chapter / "panels"
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        path = base / f"{panel_id}{ext}"
        if path.is_file():
            return path
    return None


def preview_label(item: dict[str, Any]) -> str:
    code = str(item.get("code") or "")
    severity = str(item.get("machine_severity") or item.get("severity") or "")
    panel_id = str(item.get("panel_id") or "")
    if code:
        return f"{panel_id} {code} {severity}".strip()
    return panel_id


def render_preview_sheet(
    root: Path,
    chapter: str,
    panel_ids: Sequence[str],
    labels: dict[str, str],
    out: Path,
    *,
    thumb_w: int,
    cols: int,
) -> str | None:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    tiles = []
    pad = 12
    label_h = 34
    for panel_id in panel_ids:
        path = find_panel(root, chapter, panel_id)
        if not path:
            continue
        try:
            image = Image.open(path).convert("RGB")
        except OSError:
            continue
        ratio = thumb_w / max(image.width, 1)
        thumb_h = max(1, round(image.height * ratio))
        image = image.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        tile = Image.new("RGB", (thumb_w, thumb_h + label_h), "white")
        tile.paste(image, (0, label_h))
        draw = ImageDraw.Draw(tile)
        draw.text((8, 10), labels.get(panel_id, panel_id)[:58], fill=(20, 20, 20))
        tiles.append(tile)
    if not tiles:
        return None

    rows = (len(tiles) + cols - 1) // cols
    row_heights = [max(tile.height for tile in tiles[row * cols : (row + 1) * cols]) for row in range(rows)]
    canvas_w = cols * thumb_w + (cols + 1) * pad
    canvas_h = sum(row_heights) + (rows + 1) * pad
    canvas = Image.new("RGB", (canvas_w, canvas_h), (235, 235, 235))
    y = pad
    for row in range(rows):
        x = pad
        for tile in tiles[row * cols : (row + 1) * cols]:
            canvas.paste(tile, (x, y))
            x += thumb_w + pad
        y += row_heights[row] + pad

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=92)
    return rel(root, out)


def write_preview_artifacts(root: Path, chapter: str, report: dict[str, Any]) -> dict[str, str]:
    panels = [str(item.get("panel_id") or "") for item in report.get("panels") or [] if item.get("panel_id")]
    out_dir = root / "生产数据" / "qa_previews"
    artifacts: dict[str, str] = {}
    contact = render_preview_sheet(
        root,
        chapter,
        panels,
        {panel_id: panel_id for panel_id in panels},
        out_dir / f"{chapter}_panels_contact_sheet.jpg",
        thumb_w=300,
        cols=4,
    )
    if contact:
        artifacts["contact_sheet"] = contact

    by_panel: dict[str, list[str]] = {}
    for finding in report.get("findings") or []:
        panel_id = str(finding.get("panel_id") or "")
        if not panel_id:
            continue
        by_panel.setdefault(panel_id, []).append(preview_label(finding))
    if by_panel:
        detail_ids = [panel_id for panel_id in panels if panel_id in by_panel]
        labels = {panel_id: "; ".join(by_panel[panel_id]) for panel_id in detail_ids}
        detail = render_preview_sheet(
            root,
            chapter,
            detail_ids,
            labels,
            out_dir / f"{chapter}_style_outliers_detail.jpg",
            thumb_w=420,
            cols=2,
        )
        if detail:
            artifacts["findings_detail"] = detail
    return artifacts


def add_finding(
    findings: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    panel_id: str = "",
    artifact: str,
    reason: str,
    suggested_fix: str,
    evidence_family: str,
) -> None:
    findings.append(
        {
            "severity": severity,
            "dimension": "style_consistency",
            "code": code,
            "panel_id": panel_id,
            "artifact": artifact,
            "reason": reason,
            "return_to_stage": "image",
            "suggested_fix": suggested_fix,
            "evidence_family": evidence_family,
        }
    )


def acceptance_records(root: Path, chapter: str) -> tuple[Path, list[dict[str, Any]]]:
    path = root / "生产数据" / f"style_consistency_acceptance_{chapter}.json"
    payload = load_json(path, {})
    if not isinstance(payload, dict):
        return path, []
    records = payload.get("accepted_findings")
    if not isinstance(records, list):
        records = payload.get("acceptances")
    if not isinstance(records, list):
        return path, []
    return path, [item for item in records if isinstance(item, dict)]


def matching_acceptance(finding: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any] | None:
    code = str(finding.get("code") or "").strip()
    panel_id = str(finding.get("panel_id") or "").strip()
    artifact = str(finding.get("artifact") or "").strip()
    for record in records:
        accepted_code = str(record.get("code") or "").strip()
        accepted_panel = str(record.get("panel_id") or "").strip()
        accepted_artifact = str(record.get("artifact") or "").strip()
        if accepted_code and accepted_code != code:
            continue
        panel_matches = accepted_panel and accepted_panel == panel_id
        artifact_matches = accepted_artifact and accepted_artifact == artifact
        if panel_matches or artifact_matches:
            return record
    return None


def apply_manual_acceptances(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    path, records = acceptance_records(root, chapter)
    if not records:
        return
    accepted_count = 0
    for finding in findings:
        if finding.get("severity") not in {"block", "warn"}:
            continue
        record = matching_acceptance(finding, records)
        if not record:
            continue
        machine_severity = str(finding.get("severity") or "")
        finding["machine_severity"] = machine_severity
        finding["severity"] = "info"
        finding["return_to_stage"] = "review"
        finding["manual_acceptance"] = {
            "status": "accepted",
            "accepted_by": str(record.get("accepted_by") or "manual_review"),
            "accepted_at": str(record.get("accepted_at") or ""),
            "reason": str(record.get("reason") or ""),
            "evidence": str(record.get("evidence") or ""),
            "source": rel(root, path),
        }
        if record.get("suggested_followup"):
            finding["suggested_fix"] = str(record["suggested_followup"])
        else:
            finding["suggested_fix"] = "已人审签收为计划内画面差异；若后续重抽该格需重新运行风格一致性机检。"
        accepted_count += 1
    if accepted_count:
        notes.append(f"已按 {rel(root, path)} 人审签收 {accepted_count} 条风格一致性 finding；原始机器 severity 保留在 machine_severity。")


def analyze(root: Path, chapter: str, *, margin: float = DEFAULT_MARGIN, bins: int = DEFAULT_BINS) -> dict[str, Any]:
    root = root.resolve()
    ids = panel_order(root, chapter)
    contexts = panel_contexts(root, chapter)
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    jobs = load_json(root / "出图" / chapter / "prompt" / "panel_jobs.json", {})
    findings: list[dict[str, Any]] = []
    panels: list[dict[str, Any]] = []
    notes: list[str] = []

    style_anchor = read_setting(root, "风格锚", "")
    style_contract = registry.get("style_contract") if isinstance(registry, dict) else None
    if not style_anchor and not style_contract:
        add_finding(
            findings,
            severity="block",
            code="style_anchor_missing",
            artifact="出图/共享/identity_registry.json",
            reason="缺少项目风格锚或 style_contract，无法约束跨格画风。",
            suggested_fix="回 comic-identity 登记 STYLE_ 风格资产和 style_contract，再重建出图包。",
            evidence_family="text_contract",
        )

    source_pairs = set()
    for job in jobs.get("jobs") or []:
        source_pairs.add(
            (
                str(job.get("model") or jobs.get("model") or ""),
                normalize_generation_source(job.get("source") or jobs.get("channel") or ""),
            )
        )
    source_pairs = {pair for pair in source_pairs if pair != ("", "")}
    if len(source_pairs) > 1:
        add_finding(
            findings,
            severity="block",
            code="generation_recipe_mixed",
            artifact=f"出图/{chapter}/prompt/panel_jobs.json",
            reason="同一话面板使用了多个生图模型/渠道记录：" + "；".join(f"{m}/{c}" for m, c in sorted(source_pairs)),
            suggested_fix="统一生图模型/渠道后重抽受影响格，保持同一套生成配方。",
            evidence_family="generation_recipe",
        )

    if not probe_pillow():
        notes.append("未装 Pillow，风格指纹/调色/拼贴机检跳过，只保留文本契约检查。")
        apply_manual_acceptances(root, chapter, findings, notes)
        return make_report(root, chapter, panels, findings, notes, margin, bins, available=False)

    fingerprints: list[list[float]] = []
    comparable: list[dict[str, Any]] = []
    for pid in ids:
        path = find_panel(root, chapter, pid)
        if not path:
            add_finding(
                findings,
                severity="block",
                code="panel_image_missing",
                panel_id=pid,
                artifact=f"出图/{chapter}/panels/{pid}.png",
                reason="面板图缺失，无法做风格一致性检查。",
                suggested_fix="回 comic-image 补齐该 panel 图。",
                evidence_family="artifact_presence",
            )
            continue
        data = image_fingerprint(path, bins)
        if not data:
            add_finding(
                findings,
                severity="block",
                code="panel_image_unreadable",
                panel_id=pid,
                artifact=rel(root, path),
                reason="面板图无法解码，无法做风格一致性检查。",
                suggested_fix="回 comic-image 重新生成或登记有效图片。",
                evidence_family="artifact_presence",
            )
            continue
        context = contexts.get(pid, {})
        item = {
            "panel_id": pid,
            "path": rel(root, path),
            "location": context.get("location", "unknown"),
            "style_context_bucket": style_context_bucket(context.get("location", "unknown"), context.get("style_bucket", "")),
            "size": data["size"],
            "sat_mean": round(float(data["sat_mean"]), 4),
            "val_mean": round(float(data["val_mean"]), 4),
            "edge_density": round(float(data["edge_density"]), 4),
            "warmth": round(float(data["warmth"]), 4),
            "tint": round(float(data["tint"]), 4),
            "internal_gutters": internal_gutter_count(path),
            "outer_frame_edges": outer_frame_edges(path),
        }
        panels.append(item)
        comparable.append({**item, "fingerprint": data["fingerprint"]})
        fingerprints.append(data["fingerprint"])
        if item["internal_gutters"] >= 2:
            add_finding(
                findings,
                severity="block",
                code="internal_panel_gutters",
                panel_id=pid,
                artifact=rel(root, path),
                reason="检测到疑似内部分栏/拼贴 gutter，单个漫画 panel 被模型画成多面板。",
                suggested_fix="补强单一连续画面约束并 force 重抽该格。",
                evidence_family="layout_geometry",
            )
        if item["outer_frame_edges"] >= 2:
            add_finding(
                findings,
                severity="block",
                code="outer_panel_frame",
                panel_id=pid,
                artifact=rel(root, path),
                reason="检测到疑似模型画出的外框/截图边，正式面板不能自带边框。",
                suggested_fix="补强无外框/无截图边/画面铺满画布约束并 force 重抽该格。",
                evidence_family="layout_geometry",
            )

    if len(fingerprints) >= 4:
        scores: list[float] = []
        for idx, fp in enumerate(fingerprints):
            sims = [cosine(fp, other) for j, other in enumerate(fingerprints) if j != idx]
            scores.append(sum(sims) / len(sims) if sims else 1.0)
        floor = median(scores)
        context_scores: dict[str, dict[str, Any]] = {}
        by_bucket: dict[str, list[dict[str, Any]]] = {}
        for comp in comparable:
            by_bucket.setdefault(str(comp.get("style_context_bucket") or "unknown"), []).append(comp)
        for bucket, group in by_bucket.items():
            if len(group) < 4:
                continue
            local_scores: list[tuple[dict[str, Any], float]] = []
            for idx, comp in enumerate(group):
                fp = comp["fingerprint"]
                sims = [cosine(fp, other["fingerprint"]) for j, other in enumerate(group) if j != idx]
                local_scores.append((comp, sum(sims) / len(sims) if sims else 1.0))
            local_floor = median([score for _comp, score in local_scores])
            for comp, score in local_scores:
                context_scores[str(comp["panel_id"])] = {
                    "bucket": bucket,
                    "score": score,
                    "floor": local_floor,
                    "band": style_band(score, local_floor, margin),
                }
        context_adjustments: list[str] = []
        for item, score in zip(panels, scores):
            global_band = style_band(score, floor, margin)
            context = context_scores.get(str(item["panel_id"]))
            band = global_band
            if context:
                item["style_context_cohesion"] = round(float(context["score"]), 4)
                item["style_context_floor"] = round(float(context["floor"]), 4)
                item["style_context_verdict"] = context["band"]
            if global_band == "warn" and context and context["band"] == "ok":
                band = "ok"
                item["style_context_adjustment"] = "global_warn_cleared_by_scene_bucket"
                context_adjustments.append(
                    f"{item['panel_id']} 全话指纹轻微离群，但在 {context['bucket']} 场景族群内一致，按计划内场景变化通过。"
                )
            item["style_cohesion"] = round(score, 4)
            item["style_floor"] = round(floor, 4)
            item["global_style_verdict"] = global_band
            item["style_verdict"] = band
            if band != "ok":
                add_finding(
                    findings,
                    severity=band,
                    code="panel_style_outlier",
                    panel_id=item["panel_id"],
                    artifact=item["path"],
                    reason=f"风格指纹内聚度 {score:.4f} 明显低于本话中位 {floor:.4f}，疑似画风、细节密度或照片感跳变。",
                    suggested_fix="与全话 contact sheet 并排人审；若确实跳变，回 comic-image 用同一风格锚和参考图重抽该格。",
                    evidence_family="appearance_embedding",
                )
        notes.extend(context_adjustments)
    else:
        notes.append(f"可比 panel 数 {len(fingerprints)} <4，风格离群统计跳过。")

    by_location: dict[str, list[dict[str, Any]]] = {}
    for item in panels:
        by_location.setdefault(str(item.get("location") or "unknown"), []).append(item)
    for location, group in sorted(by_location.items()):
        if len(group) < 3:
            continue
        warmth_floor = median([float(item["warmth"]) for item in group])
        tint_floor = median([float(item["tint"]) for item in group])
        for item in group:
            warmth_dev = abs(float(item["warmth"]) - warmth_floor)
            tint_dev = abs(float(item["tint"]) - tint_floor)
            if warmth_dev > GRADE_WARMTH_MARGIN or tint_dev > GRADE_TINT_MARGIN:
                add_finding(
                    findings,
                    severity="warn",
                    code="location_color_grade_shift",
                    panel_id=item["panel_id"],
                    artifact=item["path"],
                    reason=(
                        f"同场景“{location}”内调色代理偏离组中位："
                        f"warmth_dev={warmth_dev:.3f}, tint_dev={tint_dev:.3f}。"
                    ),
                    suggested_fix="人审确认是否为有意光效；否则统一白平衡/冷暖光口径后重抽该格。",
                    evidence_family="color_grade",
                )

    apply_manual_acceptances(root, chapter, findings, notes)
    return make_report(root, chapter, panels, findings, notes, margin, bins, available=True)


def make_report(
    root: Path,
    chapter: str,
    panels: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    notes: list[str],
    margin: float,
    bins: int,
    *,
    available: bool,
) -> dict[str, Any]:
    block_count = sum(1 for item in findings if item.get("severity") == "block")
    warn_count = sum(1 for item in findings if item.get("severity") == "warn")
    info_count = sum(1 for item in findings if item.get("severity") == "info")
    return {
        "schema_version": 1,
        "kind": "comic_style_consistency",
        "project_root": str(root),
        "chapter": chapter,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "available": available,
        "margin": margin,
        "bins": bins,
        "verdict": "block" if block_count else "warn" if warn_count else "pass",
        "summary": {
            "panel_count": len(panels),
            "finding_count": len(findings),
            "block_count": block_count,
            "warn_count": warn_count,
            "info_count": info_count,
        },
        "panels": panels,
        "findings": findings,
        "notes": notes,
    }


def findings_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "comic_consistency_findings",
        "dimension": "style_consistency",
        "chapter": report.get("chapter"),
        "created_at": report.get("created_at"),
        "summary": report.get("summary"),
        "findings": report.get("findings") or [],
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        f"# 漫画风格一致性报告 — {report.get('chapter')}",
        "",
        f"- 生成时间：{report.get('created_at')}",
        f"- 结论：{report.get('verdict')}",
        f"- panel 数：{summary.get('panel_count', 0)}",
        f"- block/warn/info：{summary.get('block_count', 0)} / {summary.get('warn_count', 0)} / {summary.get('info_count', 0)}",
        "",
    ]
    if report.get("notes"):
        lines += ["## 记录", ""]
        lines.extend(f"- {note}" for note in report["notes"])
        lines.append("")
    lines += ["## Findings", ""]
    findings = report.get("findings") or []
    if not findings:
        lines.append("- 未发现明显风格一致性问题。")
    else:
        lines += ["| severity | code | panel | artifact | reason | suggested_fix |", "|---|---|---|---|---|---|"]
        for item in findings:
            row = [
                item.get("severity", ""),
                item.get("code", ""),
                item.get("panel_id", ""),
                item.get("artifact", ""),
                item.get("reason", ""),
                item.get("suggested_fix", ""),
            ]
            lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in row) + " |")
    lines += ["", "## Panel 指纹", "", "| panel | location | cohesion | sat | val | edge | warmth | tint | gutters | frame |", "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for panel in report.get("panels") or []:
        lines.append(
            "| "
            + " | ".join(
                str(value)
                for value in (
                    panel.get("panel_id", ""),
                    panel.get("location", ""),
                    panel.get("style_cohesion", ""),
                    panel.get("sat_mean", ""),
                    panel.get("val_mean", ""),
                    panel.get("edge_density", ""),
                    panel.get("warmth", ""),
                    panel.get("tint", ""),
                    panel.get("internal_gutters", ""),
                    panel.get("outer_frame_edges", ""),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def write_outputs(root: Path, chapter: str, report: dict[str, Any]) -> dict[str, str]:
    previews = write_preview_artifacts(root, chapter, report)
    if previews:
        report["preview_artifacts"] = previews
    out_json = root / "生产数据" / f"comic_style_consistency_{chapter}.json"
    out_md = root / "生产数据" / f"comic_style_consistency_{chapter}.md"
    out_findings = root / "生产数据" / f"consistency_findings_style_{chapter}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(markdown(report), encoding="utf-8")
    out_findings.write_text(json.dumps(findings_payload(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"json": rel(root, out_json), "markdown": rel(root, out_md), "findings": rel(root, out_findings)}


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画面板风格一致性机检")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    parser.add_argument("--bins", type=int, default=DEFAULT_BINS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    report = analyze(root, args.chapter, margin=args.margin, bins=args.bins)
    paths = write_outputs(root, args.chapter, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(f"[ok] {paths['json']}")
        print(f"[ok] {paths['markdown']}")
        print(f"[ok] {paths['findings']}")
        print(f"verdict={report['verdict']} block={summary['block_count']} warn={summary['warn_count']} info={summary['info_count']}")
    return 1 if report.get("verdict") == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
