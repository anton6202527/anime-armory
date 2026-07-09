#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comic character consistency report.

The script keeps the reliable part first: a per-character contact sheet that
places registered references beside every panel where the character appears.
Optional Pillow-based face/hair/outfit fingerprints are advisory only.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import re
from typing import Any, Sequence


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
REFERENCE_VIEW_ORDER = ("face", "front", "three_quarter", "side", "back", "anchor", "primary_path", "path")
DEFAULT_BINS = 10


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(str(raw or ""))
    return path if path.is_absolute() else root / path


def file_sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def panel_character_ids(panel: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw or "").strip()
            if ref_id.startswith("CHAR_") and ref_id not in out:
                out.append(ref_id)
    return out


def find_panel_image(root: Path, chapter: str, panel_id: str) -> Path | None:
    base = root / "出图" / chapter / "panels"
    for suffix in IMAGE_EXTS:
        path = base / f"{panel_id}{suffix}"
        if path.is_file():
            return path
    matches = sorted(base.glob(f"{panel_id}.*"))
    return next((item for item in matches if item.suffix.lower() in IMAGE_EXTS), None)


def append_ref(out: list[dict[str, str]], root: Path, role: str, raw: Any, ref_id: str, seen: set[Path]) -> None:
    if not isinstance(raw, str) or not raw.strip():
        return
    path = resolve_path(root, raw)
    if not path.is_file():
        return
    resolved = path.resolve()
    if resolved in seen:
        return
    seen.add(resolved)
    out.append({"id": ref_id, "role": role, "path": rel(root, path), "sha256": file_sha256(path)})


def character_references(root: Path, registry: dict[str, Any], ref_id: str) -> list[dict[str, str]]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets.get(ref_id), dict) else {}
    refs: list[dict[str, str]] = []
    seen: set[Path] = set()
    if isinstance(asset, dict):
        for key in ("anchor_path", "primary_path", "path"):
            append_ref(refs, root, key, asset.get(key), ref_id, seen)
        views = asset.get("views") if isinstance(asset.get("views"), dict) else {}
        for view in REFERENCE_VIEW_ORDER:
            append_ref(refs, root, view, views.get(view) if isinstance(views, dict) else "", ref_id, seen)
        for item in asset.get("reference_images") or []:
            if isinstance(item, dict):
                append_ref(refs, root, str(item.get("view") or item.get("role") or "reference"), item.get("path"), ref_id, seen)
            else:
                append_ref(refs, root, "reference", item, ref_id, seen)
    shared = root / "出图" / "共享" / "图片"
    for role in ("anchor", "face", "front", "three_quarter", "side", "back"):
        for suffix in IMAGE_EXTS:
            append_ref(refs, root, role, str(shared / f"{ref_id}__{role}{suffix}"), ref_id, seen)
    for suffix in IMAGE_EXTS:
        append_ref(refs, root, "anchor", str(shared / f"{ref_id}{suffix}"), ref_id, seen)
    refs.sort(key=lambda item: (REFERENCE_VIEW_ORDER.index(item["role"]) if item["role"] in REFERENCE_VIEW_ORDER else 99, item["path"]))
    return refs


def image_available() -> bool:
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


def crop_fraction(image: Any, box: tuple[float, float, float, float]) -> Any:
    w, h = image.size
    left = max(0, min(w - 1, int(w * box[0])))
    top = max(0, min(h - 1, int(h * box[1])))
    right = max(left + 1, min(w, int(w * box[2])))
    bottom = max(top + 1, min(h, int(h * box[3])))
    return image.crop((left, top, right, bottom))


def channel_hist(values: Sequence[float], bins: int) -> list[float]:
    hist = [0.0] * bins
    if not values:
        return hist
    for value in values:
        idx = min(bins - 1, max(0, int(value * bins)))
        hist[idx] += 1.0
    total = float(len(values))
    return [item / total for item in hist]


def crop_fingerprint(path: Path, region: str, bins: int = DEFAULT_BINS) -> list[float]:
    from PIL import Image, ImageFilter

    image = Image.open(path).convert("RGB")
    if region == "face":
        image = crop_fraction(image, (0.25, 0.04, 0.75, 0.48))
    elif region == "hair":
        image = crop_fraction(image, (0.22, 0.0, 0.78, 0.34))
    elif region == "outfit":
        image = crop_fraction(image, (0.18, 0.32, 0.82, 0.86))
    else:
        image = crop_fraction(image, (0.12, 0.08, 0.88, 0.90))
    image.thumbnail((144, 144))
    hsv = image.convert("HSV")
    pixels = image_data(hsv)
    hue = [h / 255.0 for (h, _s, _v) in pixels]
    sat = [s / 255.0 for (_h, s, _v) in pixels]
    val = [v / 255.0 for (_h, _s, v) in pixels]
    edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_values = image_data(edges)
    edge_density = (sum(edge_values) / len(edge_values) / 255.0) if edge_values else 0.0
    return channel_hist(hue, bins) + channel_hist(sat, bins) + channel_hist(val, bins) + [edge_density] * 4


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def best_similarity(root: Path, panel_path: Path, refs: list[dict[str, str]], region: str) -> dict[str, Any]:
    if not refs:
        return {"score": 0.0, "reference": "", "available": False}
    try:
        panel_fp = crop_fingerprint(panel_path, region)
    except Exception:
        return {"score": 0.0, "reference": "", "available": False}
    best = {"score": 0.0, "reference": "", "available": True}
    preferred = refs
    if region == "face":
        preferred = [item for item in refs if item.get("role") in {"face", "front", "three_quarter", "anchor"}] or refs
    elif region == "hair":
        preferred = [item for item in refs if item.get("role") in {"face", "front", "three_quarter"}] or refs
    elif region == "outfit":
        preferred = [item for item in refs if item.get("role") in {"front", "three_quarter", "side", "anchor"}] or refs
    for item in preferred:
        ref_path = resolve_path(root, item["path"])
        try:
            score = cosine(panel_fp, crop_fingerprint(ref_path, region))
        except Exception:
            continue
        if score > float(best["score"]):
            best = {"score": round(score, 4), "reference": item["path"], "available": True}
    return best


def add_finding(
    findings: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    character_id: str = "",
    panel_id: str = "",
    artifact: str,
    reason: str,
    suggested_fix: str,
) -> None:
    findings.append(
        {
            "severity": severity,
            "dimension": "character_consistency",
            "code": code,
            "character_id": character_id,
            "panel_id": panel_id,
            "artifact": artifact,
            "reason": reason,
            "return_to_stage": "image",
            "suggested_fix": suggested_fix,
        }
    )


def acceptance_records(root: Path, chapter: str) -> tuple[Path, list[dict[str, Any]]]:
    path = root / "生产数据" / f"character_consistency_acceptance_{chapter}.json"
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
    character_id = str(finding.get("character_id") or "").strip()
    artifact = str(finding.get("artifact") or "").strip()
    for record in records:
        accepted_code = str(record.get("code") or "").strip()
        accepted_panel = str(record.get("panel_id") or "").strip()
        accepted_character = str(record.get("character_id") or "").strip()
        accepted_artifact = str(record.get("artifact") or "").strip()
        if accepted_code and accepted_code != code:
            continue
        if accepted_character and accepted_character != character_id:
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
            finding["suggested_fix"] = "已人审签收为计划内角色状态差异；若后续重抽该格需重新运行角色一致性机检。"
        accepted_count += 1
    if accepted_count:
        notes.append(f"已按 {rel(root, path)} 人审签收 {accepted_count} 条角色一致性 finding；原始机器 severity 保留在 machine_severity。")


def render_contact_sheet(root: Path, chapter: str, rows: list[dict[str, Any]], out: Path) -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return ""

    tiles: list[tuple[str, Path, str]] = []
    for row in rows:
        character_id = str(row.get("character_id") or "")
        for ref in row.get("references", [])[:6]:
            tiles.append((f"{character_id} ref:{ref.get('role')}", resolve_path(root, ref["path"]), "ref"))
        for panel in row.get("panels", [])[:18]:
            path = resolve_path(root, panel["path"])
            tiles.append((f"{character_id} {panel.get('panel_id')}", path, "panel"))
    if not tiles:
        return ""

    thumb_w = 240
    thumb_h = 240
    label_h = 34
    pad = 12
    cols = 5
    rows_count = math.ceil(len(tiles) / cols)
    canvas = Image.new("RGB", (cols * (thumb_w + pad) + pad, rows_count * (thumb_h + label_h + pad) + pad), (236, 236, 236))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    for idx, (label, path, kind) in enumerate(tiles):
        row = idx // cols
        col = idx % cols
        x = pad + col * (thumb_w + pad)
        y = pad + row * (thumb_h + label_h + pad)
        draw.rectangle((x, y, x + thumb_w, y + label_h), fill=(22, 22, 22) if kind == "panel" else (48, 70, 52))
        draw.text((x + 6, y + 9), label[:34], fill=(250, 250, 250), font=font)
        try:
            image = Image.open(path).convert("RGB")
            image.thumbnail((thumb_w, thumb_h), resampling)
            px = x + (thumb_w - image.width) // 2
            py = y + label_h + (thumb_h - image.height) // 2
            canvas.paste(image, (px, py))
        except OSError:
            draw.rectangle((x, y + label_h, x + thumb_w, y + label_h + thumb_h), outline=(180, 30, 30), width=3)
            draw.text((x + 8, y + label_h + 8), "missing/unreadable", fill=(180, 30, 30), font=font)

    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=92)
    return rel(root, out)


def analyze(root: Path, chapter: str, *, bins: int = DEFAULT_BINS) -> dict[str, Any]:
    root = root.resolve()
    script = load_json(root / "脚本" / chapter / "panel_script.json", {})
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    panels_by_character: dict[str, list[dict[str, str]]] = {}
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    pillow_available = image_available()

    for panel in script.get("panels") or []:
        pid = str(panel.get("panel_id") or "")
        if not pid:
            continue
        panel_path = find_panel_image(root, chapter, pid)
        for char_id in panel_character_ids(panel):
            if not panel_path:
                add_finding(
                    findings,
                    severity="block",
                    code="character_panel_missing",
                    character_id=char_id,
                    panel_id=pid,
                    artifact=f"出图/{chapter}/panels/{pid}.png",
                    reason="角色出场格缺少面板图，无法做角色一致性复核。",
                    suggested_fix="回 comic-image 补齐该 panel 图。",
                )
                continue
            panels_by_character.setdefault(char_id, []).append({"panel_id": pid, "path": rel(root, panel_path)})

    rows: list[dict[str, Any]] = []
    for char_id, char_panels in sorted(panels_by_character.items()):
        refs = character_references(root, registry if isinstance(registry, dict) else {}, char_id)
        if not refs:
            add_finding(
                findings,
                severity="block",
                code="character_reference_missing",
                character_id=char_id,
                artifact="出图/共享/identity_registry.json",
                reason=f"{char_id} 在本话出场，但没有可读取的共享参考图。",
                suggested_fix="回 comic-identity 补 anchor/front/face 等参考图后重建出图包并重抽受影响格。",
            )
        metrics: list[dict[str, Any]] = []
        if pillow_available and refs:
            for panel in char_panels:
                panel_path = resolve_path(root, panel["path"])
                metric = {"panel_id": panel["panel_id"]}
                for region, threshold in (("face", 0.50), ("hair", 0.46), ("outfit", 0.42)):
                    result = best_similarity(root, panel_path, refs, region)
                    metric[region] = result
                    if result.get("available") and float(result.get("score") or 0.0) < threshold:
                        add_finding(
                            findings,
                            severity="warn",
                            code=f"{region}_fingerprint_low",
                            character_id=char_id,
                            panel_id=panel["panel_id"],
                            artifact=panel["path"],
                            reason=(
                                f"{char_id} {region} 指纹与参考图相似度偏低："
                                f"score={float(result.get('score') or 0.0):.3f}。这是启发式提示，需并排人审。"
                            ),
                            suggested_fix="查看 character consistency contact sheet；如确实换脸/换发型/换服装，回 comic-image 用同一参考组重抽该格。",
                        )
                metrics.append(metric)
        elif not pillow_available:
            notes.append("未装 Pillow，跳过 face/hair/outfit 指纹，只生成文本报告。")
        rows.append({"character_id": char_id, "references": refs, "panels": char_panels, "metrics": metrics})

    contact = render_contact_sheet(
        root,
        chapter,
        rows,
        root / "生产数据" / "qa_previews" / f"{chapter}_character_consistency_contact_sheet.jpg",
    )
    if contact:
        notes.append(f"已生成角色一致性并排复核图：{contact}")

    apply_manual_acceptances(root, chapter, findings, notes)

    block_count = sum(1 for item in findings if item.get("severity") == "block")
    warn_count = sum(1 for item in findings if item.get("severity") == "warn")
    info_count = sum(1 for item in findings if item.get("severity") == "info")
    return {
        "schema_version": 1,
        "kind": "comic_character_consistency",
        "project_root": str(root),
        "chapter": chapter,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "available": pillow_available,
        "verdict": "block" if block_count else "warn" if warn_count else "pass",
        "summary": {
            "character_count": len(rows),
            "panel_binding_count": sum(len(row.get("panels") or []) for row in rows),
            "finding_count": len(findings),
            "block_count": block_count,
            "warn_count": warn_count,
            "info_count": info_count,
        },
        "contact_sheet": contact,
        "characters": rows,
        "findings": findings,
        "notes": notes,
    }


def findings_payload(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "kind": "comic_consistency_findings",
        "dimension": "character_consistency",
        "chapter": report.get("chapter"),
        "created_at": report.get("created_at"),
        "summary": report.get("summary"),
        "findings": report.get("findings") or [],
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report.get("summary") or {}
    lines = [
        f"# 漫画角色一致性报告 — {report.get('chapter')}",
        "",
        f"- 生成时间：{report.get('created_at')}",
        f"- 结论：{report.get('verdict')}",
        f"- 角色数：{summary.get('character_count', 0)}",
        f"- 出场绑定：{summary.get('panel_binding_count', 0)}",
        f"- block/warn/info：{summary.get('block_count', 0)} / {summary.get('warn_count', 0)} / {summary.get('info_count', 0)}",
    ]
    if report.get("contact_sheet"):
        lines.append(f"- 并排复核图：`{report.get('contact_sheet')}`")
    notes = report.get("notes") or []
    if notes:
        lines += ["", "## 记录", ""]
        lines.extend(f"- {note}" for note in notes)
    lines += ["", "## 角色", "", "| character | refs | panels |", "|---|---:|---:|"]
    for row in report.get("characters") or []:
        lines.append(f"| {row.get('character_id')} | {len(row.get('references') or [])} | {len(row.get('panels') or [])} |")
    lines += ["", "## Findings", ""]
    findings = report.get("findings") or []
    if not findings:
        lines.append("- 未发现角色一致性阻断或警告。")
    else:
        lines += ["| severity | code | character | panel | artifact | reason |", "|---|---|---|---|---|---|"]
        for item in findings:
            row = [
                item.get("severity", ""),
                item.get("code", ""),
                item.get("character_id", ""),
                item.get("panel_id", ""),
                item.get("artifact", ""),
                item.get("reason", ""),
            ]
            lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(root: Path, chapter: str, report: dict[str, Any]) -> dict[str, str]:
    out_json = root / "生产数据" / f"comic_character_consistency_{chapter}.json"
    out_md = root / "生产数据" / f"comic_character_consistency_{chapter}.md"
    findings = root / "生产数据" / f"consistency_findings_character_{chapter}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, out_md)
    findings.write_text(json.dumps(findings_payload(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"json": rel(root, out_json), "markdown": rel(root, out_md), "findings": rel(root, findings)}


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画角色一致性复核")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    report = analyze(root, args.chapter)
    paths = write_outputs(root, args.chapter, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(f"[ok] {paths['json']}")
        print(f"[ok] {paths['markdown']}")
        print(f"verdict={report['verdict']} block={summary['block_count']} warn={summary['warn_count']} info={summary['info_count']}")
    return 1 if report["verdict"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
