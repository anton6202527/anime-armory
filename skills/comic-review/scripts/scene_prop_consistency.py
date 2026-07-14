#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画场景/道具一致性复核（LOC_/PROP_ 的图像级覆盖）。

角色早有指纹+contact sheet，而 LOC_/PROP_ 此前只有契约文本、出图后零图像检查。
本脚本补上：
  1. 同 scene_anchor 组 contact sheet（LOC_ 锚点参考图在前，出场格并排在后）；
  2. 组内布局指纹（3x3 边缘/亮度网格）离群提示——机位可变、结构不该整格换掉；
  3. PROP_/SYS_/FX_ 并排复核图（参考图 + 出场格）；
  4. 合并 VLM 三轴任务包的 background_continuity / prop_identity 裁决。
机检部分全部 warn-only（场景机位变化天然合法），真判断交给并排人审 + VLM 轴。
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
LAYOUT_OUTLIER_MARGIN = 0.10


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


def find_panel_image(root: Path, chapter: str, panel_id: str) -> Path | None:
    base = root / "出图" / chapter / "panels"
    for suffix in IMAGE_EXTS:
        path = base / f"{panel_id}{suffix}"
        if path.is_file():
            return path
    return None


def pillow_available() -> bool:
    try:
        import PIL  # noqa: F401

        return True
    except Exception:
        return False


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
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def layout_fingerprint(path: Path) -> list[float] | None:
    """3x3 网格的亮度 + 边缘密度：场景结构布局的低成本代理。"""
    try:
        from PIL import Image, ImageFilter
    except Exception:
        return None
    try:
        image = Image.open(path).convert("L")
    except OSError:
        return None
    image.thumbnail((96, 96))
    edges = image.filter(ImageFilter.FIND_EDGES)
    w, h = image.size
    if w < 9 or h < 9:
        return None
    fp: list[float] = []
    for source in (image, edges):
        pix = source.load()
        for gy in range(3):
            for gx in range(3):
                x0, x1 = w * gx // 3, w * (gx + 1) // 3
                y0, y1 = h * gy // 3, h * (gy + 1) // 3
                values = [pix[x, y] for x in range(x0, x1) for y in range(y0, y1)]
                fp.append((sum(values) / max(1, len(values))) / 255.0)
    return fp


def asset_anchor_paths(root: Path, registry: dict[str, Any], ref_id: str, limit: int = 3) -> list[str]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets.get(ref_id), dict) else {}
    candidates: list[str] = []
    if isinstance(asset, dict):
        for key in ("anchor_path", "primary_path", "path"):
            raw = asset.get(key)
            if isinstance(raw, str) and raw.strip():
                candidates.append(raw)
        for item in asset.get("reference_images") or []:
            raw = item.get("path") if isinstance(item, dict) else item
            if isinstance(raw, str) and raw.strip():
                candidates.append(raw)
    shared = root / "出图" / "共享" / "图片"
    for suffix in ("__anchor.png", ".png"):
        candidates.append(str(shared / f"{ref_id}{suffix}"))
    out: list[str] = []
    seen: set[str] = set()
    for raw in candidates:
        path = resolve_path(root, raw)
        if path.is_file():
            key = str(path.resolve())
            if key not in seen:
                seen.add(key)
                out.append(rel(root, path))
        if len(out) >= limit:
            break
    return out


def panel_ref_ids(panel: dict[str, Any], prefixes: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for binding in panel.get("character_bindings") or []:
        if not isinstance(binding, dict):
            continue
        for key in ("character_id", "form_id", "outfit_id", "expression_id", "state_id"):
            ref_id = str(binding.get(key) or "").strip()
            if ref_id.startswith(prefixes) and ref_id not in out:
                out.append(ref_id)
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw or "").strip()
            if ref_id.startswith(prefixes) and ref_id not in out:
                out.append(ref_id)
    return out


def panel_scene_anchor(panel: dict[str, Any]) -> str:
    for key in ("scene_anchor_id", "scene_id", "location_id"):
        value = str(panel.get(key) or "").strip()
        if value:
            return value
    for ref_id in panel_ref_ids(panel, ("LOC_",)):
        return ref_id
    return ""


def add_finding(
    findings: list[dict[str, Any]],
    *,
    severity: str,
    code: str,
    subject: str = "",
    panel_id: str = "",
    artifact: str,
    reason: str,
    suggested_fix: str,
    evidence_family: str,
) -> None:
    findings.append(
        {
            "severity": severity,
            "dimension": "scene_prop_consistency",
            "code": code,
            "subject": subject,
            "panel_id": panel_id,
            "artifact": artifact,
            "reason": reason,
            "return_to_stage": "image",
            "suggested_fix": suggested_fix,
            "evidence_family": evidence_family,
        }
    )


def render_group_sheet(root: Path, title_rows: list[tuple[str, str]], out: Path) -> str:
    """title_rows: [(label, root 相对路径)]，参考图排最前。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return ""
    tiles: list[tuple[str, Path]] = [(label, resolve_path(root, raw)) for label, raw in title_rows]
    tiles = [(label, path) for label, path in tiles if path.is_file()]
    if not tiles:
        return ""
    thumb = 240
    label_h = 32
    pad = 10
    cols = 5
    rows = math.ceil(len(tiles) / cols)
    canvas = Image.new("RGB", (cols * (thumb + pad) + pad, rows * (thumb + label_h + pad) + pad), (238, 238, 238))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    for idx, (label, path) in enumerate(tiles):
        x = pad + (idx % cols) * (thumb + pad)
        y = pad + (idx // cols) * (thumb + label_h + pad)
        draw.rectangle((x, y, x + thumb, y + label_h), fill=(48, 70, 52) if label.startswith("ref") else (22, 22, 22))
        draw.text((x + 6, y + 8), label[:34], fill=(250, 250, 250), font=font)
        try:
            image = Image.open(path).convert("RGB")
            image.thumbnail((thumb, thumb), resampling)
            canvas.paste(image, (x + (thumb - image.width) // 2, y + label_h + (thumb - image.height) // 2))
        except OSError:
            draw.text((x + 8, y + label_h + 8), "unreadable", fill=(180, 30, 30), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=90)
    return rel(root, out)


def analyze(root: Path, chapter: str) -> dict[str, Any]:
    root = root.resolve()
    script = load_json(root / "脚本" / chapter / "panel_script.json", {})
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    registry = registry if isinstance(registry, dict) else {}
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    pillow_ready = pillow_available()

    scene_groups: dict[str, list[dict[str, str]]] = {}
    prop_groups: dict[str, list[dict[str, str]]] = {}
    for panel in script.get("panels") or []:
        pid = str(panel.get("panel_id") or "")
        if not pid:
            continue
        panel_path = find_panel_image(root, chapter, pid)
        if not panel_path:
            continue
        entry = {"panel_id": pid, "path": rel(root, panel_path)}
        anchor = panel_scene_anchor(panel)
        if anchor:
            scene_groups.setdefault(anchor, []).append(entry)
        for prop_id in panel_ref_ids(panel, ("PROP_", "SYS_", "FX_", "VFX_", "OUTFIT_")):
            prop_groups.setdefault(prop_id, []).append(entry)

    scenes: list[dict[str, Any]] = []
    for anchor, entries in sorted(scene_groups.items()):
        refs = asset_anchor_paths(root, registry, anchor)
        if not refs and anchor.startswith("LOC_"):
            add_finding(
                findings,
                severity="warn",
                code="scene_anchor_reference_missing",
                subject=anchor,
                artifact="出图/共享/identity_registry.json",
                reason=f"场景锚 {anchor} 没有可读取的参考图，场景一致性只能靠逐格互比。",
                suggested_fix="用 comic-identity anchors 为该 LOC_ 生成/登记锚点图。",
                evidence_family="reference_presence",
            )
        row: dict[str, Any] = {"scene_anchor_id": anchor, "references": refs, "panels": entries}
        if pillow_ready and len(entries) >= 3:
            fps = []
            for entry in entries:
                fp = layout_fingerprint(resolve_path(root, entry["path"]))
                if fp:
                    fps.append((entry, fp))
            if len(fps) >= 3:
                scores = []
                for idx, (_entry, fp) in enumerate(fps):
                    sims = [cosine(fp, other) for j, (_e, other) in enumerate(fps) if j != idx]
                    scores.append(sum(sims) / len(sims))
                floor = median(scores)
                for (entry, _fp), score in zip(fps, scores):
                    if score < floor - LAYOUT_OUTLIER_MARGIN:
                        add_finding(
                            findings,
                            severity="warn",
                            code="scene_layout_outlier",
                            subject=anchor,
                            panel_id=entry["panel_id"],
                            artifact=entry["path"],
                            reason=(
                                f"{entry['panel_id']} 的布局指纹在场景锚 {anchor} 组内离群"
                                f"（{score:.3f} < 中位 {floor:.3f} - {LAYOUT_OUTLIER_MARGIN}）。机位变化合法，"
                                "但整格结构换掉（门窗家具错位/常驻物件消失）需要人审。"
                            ),
                            suggested_fix="看该场景锚 contact sheet 并排比对；结构漂移则按 spatial_layout/resident_assets 重抽。",
                            evidence_family="layout_geometry",
                        )
                row["layout_cohesion_floor"] = round(floor, 4)
        sheet = ""
        if pillow_ready:
            tiles = [(f"ref {anchor}", raw) for raw in refs] + [(e["panel_id"], e["path"]) for e in entries[:18]]
            sheet = render_group_sheet(
                root, tiles, root / "生产数据" / "qa_previews" / f"{chapter}_scene_{anchor}_sheet.jpg"
            )
        if sheet:
            row["contact_sheet"] = sheet
        scenes.append(row)

    props: list[dict[str, Any]] = []
    for prop_id, entries in sorted(prop_groups.items()):
        refs = asset_anchor_paths(root, registry, prop_id)
        if not refs:
            add_finding(
                findings,
                severity="warn",
                code="prop_reference_missing",
                subject=prop_id,
                artifact="出图/共享/identity_registry.json",
                reason=f"{prop_id} 在本话出场（{','.join(e['panel_id'] for e in entries[:8])}）但没有参考图，无法并排核对同一物。",
                suggested_fix="用 comic-identity anchors 生成/登记该道具锚点图后重建出图包。",
                evidence_family="reference_presence",
            )
        row = {"prop_id": prop_id, "references": refs, "panels": entries}
        if pillow_ready:
            tiles = [(f"ref {prop_id}", raw) for raw in refs] + [(e["panel_id"], e["path"]) for e in entries[:18]]
            sheet = render_group_sheet(
                root, tiles, root / "生产数据" / "qa_previews" / f"{chapter}_prop_{prop_id}_sheet.jpg"
            )
            if sheet:
                row["contact_sheet"] = sheet
        props.append(row)

    if not pillow_ready:
        notes.append("未装 Pillow，场景/道具并排图与布局指纹跳过，只保留结构性检查。")

    # 合并 VLM 三轴的 background / prop 裁决。
    try:
        import vlm_judge

        for axis, code in (("background_continuity", "vlm_judge_background_suspect"), ("prop_identity", "vlm_judge_prop_suspect")):
            for item in vlm_judge.suspect_verdicts(root, chapter, axis):
                task = item["task"]
                verdict = item["verdict"]
                add_finding(
                    findings,
                    severity="warn",
                    code=code,
                    subject=str(task.get("subject") or ""),
                    panel_id=str((task.get("panel") or {}).get("panel_id") or ""),
                    artifact=str((task.get("panel") or {}).get("path") or ""),
                    reason=(
                        "VLM 并排判定低分/存疑："
                        + (("、".join(item["low_scores"])) if item["low_scores"] else "verdict=suspect")
                        + ("；" + str(verdict.get("notes") or "") if verdict.get("notes") else "")
                    ),
                    suggested_fix="按裁决 notes 并排复核；确认漂移则回 comic-image 重抽该格。",
                    evidence_family="vlm_judge",
                )
        status = vlm_judge.judge_status(root, chapter)
        notes.append(f"VLM 三轴裁决进度：{status['verdict_count']}/{status['task_count']}（{status['verdict_file']}）。")
    except Exception as exc:  # pragma: no cover
        notes.append(f"VLM 并排判定不可用：{exc}")

    block_count = sum(1 for item in findings if item.get("severity") == "block")
    warn_count = sum(1 for item in findings if item.get("severity") == "warn")
    return {
        "schema_version": 1,
        "kind": "comic_scene_prop_consistency",
        "project_root": str(root),
        "chapter": chapter,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "available": pillow_ready,
        "verdict": "block" if block_count else "warn" if warn_count else "pass",
        "summary": {
            "scene_anchor_count": len(scenes),
            "prop_count": len(props),
            "finding_count": len(findings),
            "block_count": block_count,
            "warn_count": warn_count,
            "info_count": sum(1 for item in findings if item.get("severity") == "info"),
        },
        "scenes": scenes,
        "props": props,
        "findings": findings,
        "notes": notes,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report.get("summary") or {}
    lines = [
        f"# 漫画场景/道具一致性报告 — {report.get('chapter')}",
        "",
        f"- 生成时间：{report.get('created_at')}",
        f"- 结论：{report.get('verdict')}",
        f"- 场景锚：{summary.get('scene_anchor_count', 0)} | 道具：{summary.get('prop_count', 0)}",
        f"- block/warn：{summary.get('block_count', 0)} / {summary.get('warn_count', 0)}",
        "",
        "## 场景锚",
        "",
        "| anchor | refs | panels | contact sheet |",
        "|---|---:|---:|---|",
    ]
    for row in report.get("scenes") or []:
        lines.append(
            f"| {row.get('scene_anchor_id')} | {len(row.get('references') or [])} | {len(row.get('panels') or [])} | {row.get('contact_sheet', '')} |"
        )
    lines += ["", "## 道具", "", "| prop | refs | panels | contact sheet |", "|---|---:|---:|---|"]
    for row in report.get("props") or []:
        lines.append(
            f"| {row.get('prop_id')} | {len(row.get('references') or [])} | {len(row.get('panels') or [])} | {row.get('contact_sheet', '')} |"
        )
    lines += ["", "## Findings", ""]
    findings = report.get("findings") or []
    if not findings:
        lines.append("- 未发现场景/道具一致性问题。")
    else:
        lines += ["| severity | code | subject | panel | reason |", "|---|---|---|---|---|"]
        for item in findings:
            lines.append(
                "| "
                + " | ".join(
                    str(item.get(key, "")).replace("|", "\\|").replace("\n", " ")
                    for key in ("severity", "code", "subject", "panel_id", "reason")
                )
                + " |"
            )
    notes = report.get("notes") or []
    if notes:
        lines += ["", "## 记录", ""]
        lines.extend(f"- {note}" for note in notes)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(root: Path, chapter: str, report: dict[str, Any]) -> dict[str, str]:
    out_json = root / "生产数据" / f"comic_scene_prop_consistency_{chapter}.json"
    out_md = root / "生产数据" / f"comic_scene_prop_consistency_{chapter}.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, out_md)
    return {"json": rel(root, out_json), "markdown": rel(root, out_md)}


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画场景/道具一致性复核")
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
        print(f"verdict={report['verdict']} block={summary['block_count']} warn={summary['warn_count']}")
    return 1 if report["verdict"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
