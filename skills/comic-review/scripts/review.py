#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic comic review report generator.

This script intentionally checks only things that can be located from project
artifacts. Subjective visual judgement remains a human review task, but the
report still records likely visual risks such as baked blank bubbles.
"""
from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime
import json
import re
from pathlib import Path
from typing import Any


IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


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
    text = read_text(root / "_设置.md")
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def add_issue(
    issues: list[dict[str, str]],
    severity: str,
    artifact: str,
    reason: str,
    return_to: str,
    suggested_fix: str,
    category: str,
) -> None:
    issues.append(
        {
            "severity": severity,
            "category": category,
            "artifact": artifact,
            "reason": reason,
            "return_to": return_to,
            "suggested_fix": suggested_fix,
        }
    )


def ordered_panel_ids(layout: dict) -> list[str]:
    ids: list[str] = []
    for segment in layout.get("segments") or []:
        panels = sorted(segment.get("panels") or [], key=lambda p: (p.get("y", 0), p.get("x", 0)))
        for panel in panels:
            pid = panel.get("panel_id")
            if pid and pid not in ids:
                ids.append(str(pid))
    return ids


def panel_slots(layout: dict) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for segment in layout.get("segments") or []:
        for panel in segment.get("panels") or []:
            pid = panel.get("panel_id")
            if not pid:
                continue
            out[str(pid)] = {str(slot.get("slot_id")) for slot in panel.get("bubble_slots") or [] if slot.get("slot_id")}
    return out


def lettering_items_by_panel(lettering: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for item in lettering.get("items") or []:
        pid = item.get("panel_id")
        if pid:
            out.setdefault(str(pid), []).append(item)
    return out


def panel_reference_ids(panel_script: dict) -> set[str]:
    ids: set[str] = set()
    for panel in panel_script.get("panels") or []:
        for key in ("references", "characters"):
            for raw in panel.get(key) or []:
                ref_id = str(raw).strip()
                if ref_id.startswith(("CHAR_", "MON_", "LOC_", "PROP_", "SYS_", "FX_", "STYLE_")):
                    ids.add(ref_id)
    return ids


def has_style_anchor(registry: dict) -> bool:
    if not isinstance(registry, dict):
        return False
    if registry.get("style_contract") or registry.get("visual_style"):
        return True
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    for ref_id, asset in assets.items():
        if not isinstance(asset, dict):
            continue
        if ref_id.startswith("STYLE_") or str(asset.get("type") or "").lower() == "style":
            return True
    return False


def find_panel_image(panel_dir: Path, panel_id: str) -> Path | None:
    for ext in IMAGE_EXTS:
        candidate = panel_dir / f"{panel_id}{ext}"
        if candidate.is_file():
            return candidate
    matches = sorted(panel_dir.glob(f"{panel_id}.*"))
    return next((path for path in matches if path.suffix.lower() in IMAGE_EXTS), None)


def visual_white_components(path: Path) -> list[dict[str, int]]:
    """Return likely baked white bubble/text-container regions in raw art.

    The heuristic is deliberately conservative: it downscales the image, looks
    for large low-saturation near-white connected components, and ignores tiny
    highlights. Results are review hints, not final proof.
    """
    try:
        from PIL import Image
    except ImportError:
        return []

    try:
        image = Image.open(path).convert("RGB")
    except OSError:
        return []

    src_w, src_h = image.size
    max_w = 480
    scale = min(1.0, max_w / max(src_w, 1))
    if scale < 1.0:
        image = image.resize((max(1, int(src_w * scale)), max(1, int(src_h * scale))))
    w, h = image.size
    pixels = image.load()
    mask = [[False] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            if r >= 238 and g >= 238 and b >= 230 and max(r, g, b) - min(r, g, b) <= 35:
                mask[y][x] = True

    seen = [[False] * w for _ in range(h)]
    components: list[dict[str, int]] = []
    min_area = max(260, int(w * h * 0.0028))
    for y in range(h):
        for x in range(w):
            if not mask[y][x] or seen[y][x]:
                continue
            q: deque[tuple[int, int]] = deque([(x, y)])
            seen[y][x] = True
            area = 0
            min_x = max_x = x
            min_y = max_y = y
            while q:
                cx, cy = q.popleft()
                area += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h and mask[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = True
                        q.append((nx, ny))
            bw = max_x - min_x + 1
            bh = max_y - min_y + 1
            if area < min_area or bw < 30 or bh < 18:
                continue
            inv = 1.0 / scale if scale else 1.0
            components.append(
                {
                    "x": int(min_x * inv),
                    "y": int(min_y * inv),
                    "w": int(bw * inv),
                    "h": int(bh * inv),
                    "area": int(area * inv * inv),
                }
            )
    return components[:8]


def refresh_preview(root: Path, chapter: str, rendered: list[dict]) -> str:
    if not rendered:
        return ""
    try:
        from PIL import Image
    except ImportError:
        return ""

    source = root / str(rendered[0].get("path", ""))
    if not source.is_file():
        return ""
    try:
        image = Image.open(source).convert("RGB")
    except OSError:
        return ""
    max_w = 727
    max_h = 9000
    scale = min(1.0, max_w / max(image.width, 1))
    target_w = max(1, int(image.width * scale))
    target_h = max(1, int(image.height * scale))
    image = image.resize((target_w, target_h))
    if image.height > max_h:
        image = image.crop((0, 0, image.width, max_h))
    out = root / "生产数据" / "qa_previews" / f"{chapter}_longstrip_preview.webp"
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out, quality=88)
    return str(out.relative_to(root))


def refresh_contact_sheet(root: Path, chapter: str, panel_ids: list[str], panel_dir: Path) -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return ""

    images: list[tuple[str, Any]] = []
    for pid in panel_ids:
        path = find_panel_image(panel_dir, pid)
        if not path:
            continue
        try:
            images.append((pid, Image.open(path).convert("RGB")))
        except OSError:
            continue
    if not images:
        return ""

    cols = 3
    thumb_w = 360
    label_h = 28
    gap = 18
    bg = (18, 18, 18)
    fg = (235, 235, 235)
    font = ImageFont.load_default()
    thumbs: list[tuple[str, Any]] = []
    thumb_h = 0
    for pid, image in images:
        scale = min(1.0, thumb_w / max(image.width, 1))
        thumb = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))))
        thumbs.append((pid, thumb))
        thumb_h = max(thumb_h, thumb.height)
    rows = (len(thumbs) + cols - 1) // cols
    width = cols * thumb_w + (cols + 1) * gap
    height = rows * (thumb_h + label_h) + (rows + 1) * gap
    canvas = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(canvas)
    for idx, (pid, thumb) in enumerate(thumbs):
        row = idx // cols
        col = idx % cols
        x = gap + col * (thumb_w + gap)
        y = gap + row * (thumb_h + label_h + gap)
        canvas.paste(thumb, (x, y))
        draw.text((x, y + thumb_h + 8), pid, fill=fg, font=font)
    out = root / "生产数据" / f"panel_contact_sheet_{chapter}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=90)
    return str(out.relative_to(root))


def update_progress(root: Path, chapter: str, stage: str, value: str) -> bool:
    path = root / "_进度.md"
    if not path.is_file():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    headers: list[str] = []
    updated = False
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if cells and cells[0] == "话":
                headers = cells
            elif headers and len(cells) >= len(headers) and cells[0] == chapter and stage in headers:
                cells[headers.index(stage)] = value
                line = "| " + " | ".join(cells) + " |"
                updated = True
        out.append(line)
    if updated:
        path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return updated


def verdict_for(issues: list[dict[str, str]]) -> str:
    if any(issue["severity"] == "block" for issue in issues):
        return "block"
    if any(issue["severity"] == "warn" for issue in issues):
        return "revise"
    return "pass"


def review(root: Path, chapter: str, *, refresh_qa_preview: bool = True) -> dict:
    settings = {
        "定妆级别": read_setting(root, "定妆级别", "长线专门定妆"),
        "参考一致性策略": read_setting(root, "参考一致性策略", "共享参考图"),
        "年龄形态继承": read_setting(root, "年龄形态继承", ""),
        "角色一致性硬闸": read_setting(root, "角色一致性硬闸", ""),
        "风格锚": read_setting(root, "风格锚", ""),
        "文字语言": read_setting(root, "文字语言", "中文"),
        "合规用途": read_setting(root, "合规用途", "自用草稿"),
    }
    issues: list[dict[str, str]] = []
    notes: list[str] = []

    paths = {
        "progress": root / "_进度.md",
        "settings": root / "_设置.md",
        "meta": root / "_meta.json",
        "panel_script": root / "脚本" / chapter / "panel_script.json",
        "layout": root / "排版" / chapter / "layout.json",
        "lettering": root / "排版" / chapter / "lettering.json",
        "manifest": root / "排版" / chapter / "export_manifest.json",
        "identity_report": root / "生产数据" / f"comic_identity_report_{chapter}.json",
        "identity_registry": root / "出图" / "共享" / "identity_registry.json",
        "panel_dir": root / "出图" / chapter / "panels",
    }
    for key in ("progress", "settings", "meta", "panel_script", "layout", "lettering", "manifest"):
        if not paths[key].is_file():
            add_issue(issues, "block", str(paths[key].relative_to(root)), "审查必需文件缺失", "comic-" + ("compose" if key in ("lettering", "manifest") else "script"), "补齐文件后重新运行 comic-review", "missing_artifact")

    panel_script = load_json(paths["panel_script"], {})
    layout = load_json(paths["layout"], {})
    lettering = load_json(paths["lettering"], {})
    manifest = load_json(paths["manifest"], {})
    meta = load_json(paths["meta"], {})
    identity_report = load_json(paths["identity_report"], {})
    identity_registry = load_json(paths["identity_registry"], {})

    script_panels = [str(panel.get("panel_id")) for panel in panel_script.get("panels") or [] if panel.get("panel_id")]
    layout_panels = ordered_panel_ids(layout)
    manifest_panels = [str(item.get("panel_id")) for item in manifest.get("panels") or [] if item.get("panel_id")]
    slots_by_panel = panel_slots(layout)
    lettering_by_panel = lettering_items_by_panel(lettering)

    if not script_panels:
        add_issue(issues, "block", "脚本/" + chapter + "/panel_script.json", "没有可审查的 panels", "comic-script", "补齐分格脚本", "script")
    for panel in panel_script.get("panels") or []:
        pid = str(panel.get("panel_id") or "")
        if not str(panel.get("story_function") or "").strip():
            add_issue(issues, "warn", pid, "story_function 为空，审查难以判断本格叙事功能", "comic-script", "补上本格叙事功能", "script")

    missing_in_layout = [pid for pid in script_panels if pid not in layout_panels]
    if missing_in_layout:
        add_issue(issues, "block", "排版/" + chapter + "/layout.json", "layout 缺少脚本中的 panel：" + ", ".join(missing_in_layout), "comic-layout", "重新生成或修正 layout.json", "layout")
    missing_in_manifest = [pid for pid in layout_panels if pid not in manifest_panels]
    if missing_in_manifest:
        add_issue(issues, "block", "排版/" + chapter + "/export_manifest.json", "manifest 缺少 layout 中的 panel：" + ", ".join(missing_in_manifest), "comic-compose", "重新导出 manifest/长图", "export")

    manifest_missing = [str(pid) for pid in manifest.get("missing_panels") or []]
    if manifest_missing:
        add_issue(issues, "block", "排版/" + chapter + "/export_manifest.json", "导出 manifest 记录缺图：" + ", ".join(manifest_missing), "comic-image", "补齐缺失 panel 图后重新导出", "export")
    if not manifest.get("rendered"):
        add_issue(issues, "block", "排版/" + chapter + "/export_manifest.json", "未登记实际渲染导出物", "comic-compose", "运行 export_longstrip.py --render", "export")

    setting_lang = settings["文字语言"]
    manifest_lang = str(manifest.get("text_language") or "").strip()
    if manifest_lang and manifest_lang != setting_lang:
        add_issue(issues, "warn", "排版/" + chapter + "/export_manifest.json", f"text_language={manifest_lang} 与项目设置 {setting_lang} 不一致", "comic-compose", "按当前 _设置.md 重新导出", "lettering")
    if setting_lang == "中文" and manifest.get("bilingual_lettering"):
        add_issue(issues, "warn", "排版/" + chapter + "/export_manifest.json", "项目设置为中文，但 manifest 仍标记双语嵌字", "comic-compose", "按文字语言=中文重新渲染长图", "lettering")
    if setting_lang in ("英文", "中上英下", "英上中下"):
        missing_en = [
            str(item.get("item_id"))
            for item in lettering.get("items") or []
            if str(item.get("text_zh") or item.get("text") or "").strip() and not str(item.get("text_en") or "").strip()
        ]
        if missing_en:
            add_issue(issues, "block", "排版/" + chapter + "/lettering.json", "英文/双语导出缺英文译文：" + ", ".join(missing_en[:20]), "comic-compose", "补齐 text_en 或改回文字语言=中文", "lettering")

    slot_ids = {sid for slots in slots_by_panel.values() for sid in slots}
    item_slot_ids = {str(item.get("slot_id")) for item in lettering.get("items") or [] if item.get("slot_id")}
    unknown_slots = sorted(item_slot_ids - slot_ids)
    if unknown_slots:
        add_issue(issues, "warn", "排版/" + chapter + "/lettering.json", "lettering 引用了 layout 不存在的 slot：" + ", ".join(unknown_slots), "comic-compose", "同步 layout 和 lettering 的 slot_id", "lettering")

    consistency_text = " ".join(str(settings.get(key) or "") for key in ("参考一致性策略", "年龄形态继承", "角色一致性硬闸"))
    high_grade_consistency = any(token in consistency_text.lower() for token in ("dna", "形态继承", "硬闸", "高一致性", "多视图"))
    if high_grade_consistency:
        if not isinstance(identity_registry, dict) or not identity_registry:
            add_issue(issues, "block", str(paths["identity_registry"].relative_to(root)), "高一致性长线口径缺少 identity_registry.json", "comic-identity", "登记角色/风格锚和定妆契约后重跑报告", "identity")
        elif not has_style_anchor(identity_registry):
            add_issue(issues, "block", str(paths["identity_registry"].relative_to(root)), "高一致性长线口径缺少项目风格锚或 style_contract", "comic-identity", "登记 STYLE_ 风格资产或 registry.style_contract", "identity")
        assets = identity_registry.get("assets") if isinstance(identity_registry, dict) and isinstance(identity_registry.get("assets"), dict) else {}
        used_refs = panel_reference_ids(panel_script)
        character_ids = sorted(ref_id for ref_id in (used_refs | set(assets.keys())) if ref_id.startswith("CHAR_"))
        for ref_id in character_ids:
            asset = assets.get(ref_id) if isinstance(assets.get(ref_id), dict) else {}
            if not asset:
                add_issue(issues, "block", str(paths["identity_registry"].relative_to(root)), f"{ref_id} 未在 registry.assets 登记", "comic-identity", "补登记角色锚点、DNA 和多视图", "identity")
                continue
            if not (asset.get("character_dna") or asset.get("dna_contract")):
                add_issue(issues, "block", str(paths["identity_registry"].relative_to(root)), f"{ref_id} 缺少 character_dna/dna_contract，无法做跨年龄或跨话一致性", "comic-identity", "把定型图提炼成角色 DNA/禁漂移项", "identity")
            if "形态继承" in consistency_text and not (asset.get("variant_policy") or asset.get("age_variants")):
                add_issue(issues, "block", str(paths["identity_registry"].relative_to(root)), f"{ref_id} 缺少年龄/形态继承策略", "comic-identity", "登记 age_variants 或 variant_policy，明确少年/成年/受伤/觉醒等形态如何继承定型图", "identity")

    if settings["定妆级别"].startswith("长线") or "专门定妆" in settings["定妆级别"]:
        missing_views = identity_report.get("missing_character_views") if isinstance(identity_report, dict) else None
        if not isinstance(missing_views, dict):
            add_issue(issues, "block", str(paths["identity_report"].relative_to(root)), "长线专门定妆缺少可解析的 missing_character_views", "comic-identity", "重新运行 comic-identity report --write", "identity")
        else:
            blockers = {k: v for k, v in missing_views.items() if isinstance(v, list) and v}
            if blockers:
                reason = "；".join(f"{character} 缺 {','.join(map(str, views))}" for character, views in sorted(blockers.items()))
                add_issue(issues, "block", str(paths["identity_report"].relative_to(root)), "长线专门定妆未补齐：" + reason, "comic-identity", "为常驻角色补 front/three_quarter/side/back/face 后重跑报告", "identity")
    summary = identity_report.get("summary") if isinstance(identity_report, dict) else {}
    if int((summary or {}).get("missing_ref_count") or 0) > 0 or int((summary or {}).get("rerun_target_count") or 0) > 0:
        add_issue(issues, "block", str(paths["identity_report"].relative_to(root)), "一致性报告仍有缺失 reference 或待重抽格", "comic-identity", "补齐 reference 并重抽 rerun_targets", "identity")

    raw_bubble_hits: list[dict[str, Any]] = []
    for pid in layout_panels:
        image_path = find_panel_image(paths["panel_dir"], pid)
        if not image_path:
            add_issue(issues, "block", str((paths["panel_dir"] / f"{pid}.png").relative_to(root)), "panel 图缺失", "comic-image", "生成或登记该 panel 图", "image")
            continue
        components = visual_white_components(image_path)
        if components:
            raw_bubble_hits.append({"panel_id": pid, "path": str(image_path.relative_to(root)), "components": components[:3]})
    if raw_bubble_hits:
        add_issue(
            issues,
            "warn",
            "出图/" + chapter + "/panels",
            "原始面板图疑似烘焙了空白气泡/文字容器：" + ", ".join(hit["panel_id"] for hit in raw_bubble_hits[:18]),
            "comic-image",
            "后续重抽这些格时要求无字画面、无空白气泡，只保留低细节留白；系统绘卷等叙事道具可人工豁免",
            "image",
        )

    rights = (meta.get("rights") or {}) if isinstance(meta, dict) else {}
    publish_like = settings["合规用途"] not in ("自用草稿", "内部草稿", "草稿")
    for key, label in (("font_status", "字体权利"), ("asset_status", "素材权利")):
        if str(rights.get(key) or "").startswith("pending"):
            add_issue(
                issues,
                "block" if publish_like else "info",
                "_meta.json",
                f"{label}仍是 {rights.get(key)}",
                "comic-review",
                "发布/商用前确认授权并更新 _meta.json",
                "rights",
            )
    if manifest.get("font_status") == "system_font_draft":
        add_issue(
            issues,
            "block" if publish_like else "info",
            "排版/" + chapter + "/export_manifest.json",
            "当前使用 system_font_draft，不能当正式发布字体授权",
            "comic-compose",
            "发布前用已授权字体重新导出，或更新字体授权记录",
            "rights",
        )

    rendered = manifest.get("rendered") or []
    preview = refresh_preview(root, chapter, rendered) if refresh_qa_preview else ""
    if preview:
        notes.append(f"已刷新 QA 长图预览：{preview}")
    contact_sheet = refresh_contact_sheet(root, chapter, layout_panels, paths["panel_dir"]) if refresh_qa_preview else ""
    if contact_sheet:
        notes.append(f"已刷新 panel contact sheet：{contact_sheet}")

    verdict = verdict_for(issues)
    return {
        "schema_version": 1,
        "kind": "comic_review",
        "project_root": str(root),
        "chapter": chapter,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "verdict": verdict,
        "settings": settings,
        "summary": {
            "panel_count": len(layout_panels or script_panels),
            "issue_count": len(issues),
            "block_count": sum(1 for issue in issues if issue["severity"] == "block"),
            "warn_count": sum(1 for issue in issues if issue["severity"] == "warn"),
            "info_count": sum(1 for issue in issues if issue["severity"] == "info"),
        },
        "artifacts": {
            "panel_script": str(paths["panel_script"].relative_to(root)),
            "layout": str(paths["layout"].relative_to(root)),
            "lettering": str(paths["lettering"].relative_to(root)),
            "manifest": str(paths["manifest"].relative_to(root)),
            "identity_report": str(paths["identity_report"].relative_to(root)),
            "rendered": rendered,
            "qa_preview": preview,
            "contact_sheet": contact_sheet,
        },
        "raw_bubble_candidates": raw_bubble_hits,
        "issues": issues,
        "notes": notes,
    }


def write_markdown(report: dict, path: Path) -> None:
    summary = report.get("summary") or {}
    lines = [
        f"# 漫画审查报告 — {report.get('chapter')}",
        "",
        f"- 生成时间：{report.get('created_at')}",
        f"- 结论：{report.get('verdict')}",
        f"- panel 数：{summary.get('panel_count', 0)}",
        f"- block/warn/info：{summary.get('block_count', 0)} / {summary.get('warn_count', 0)} / {summary.get('info_count', 0)}",
        "",
        "## 设置",
        "",
    ]
    for key, value in (report.get("settings") or {}).items():
        lines.append(f"- {key}: {value}")
    notes = report.get("notes") or []
    if notes:
        lines += ["", "## 记录", ""]
        lines.extend(f"- {note}" for note in notes)
    lines += ["", "## 问题清单", ""]
    issues = report.get("issues") or []
    if not issues:
        lines.append("- 未发现阻断或警告。")
    else:
        lines += ["| severity | category | artifact | reason | return_to | suggested_fix |", "|---|---|---|---|---|---|"]
        for issue in issues:
            row = [
                issue.get("severity", ""),
                issue.get("category", ""),
                issue.get("artifact", ""),
                issue.get("reason", ""),
                issue.get("return_to", ""),
                issue.get("suggested_fix", ""),
            ]
            lines.append("| " + " | ".join(str(item).replace("|", "\\|").replace("\n", " ") for item in row) + " |")
    if report.get("raw_bubble_candidates"):
        lines += ["", "## 疑似烘焙气泡", ""]
        for hit in report["raw_bubble_candidates"]:
            lines.append(f"- {hit['panel_id']}: `{hit['path']}` components={len(hit.get('components') or [])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画审查报告")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--write-progress", action="store_true", help="只有 verdict=pass 时把 _进度.md 审查标为 ✅")
    parser.add_argument("--no-preview", action="store_true", help="不刷新 QA 长图预览")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    report = review(root, args.chapter, refresh_qa_preview=not args.no_preview)
    out_json = root / "生产数据" / f"comic_review_{args.chapter}.json"
    out_md = root / "生产数据" / f"comic_review_{args.chapter}.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, out_md)
    if args.write_progress and report["verdict"] == "pass":
        update_progress(root, args.chapter, "审查", "✅")
        report["progress_written"] = True
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(f"[ok] {out_json}")
        print(f"[ok] {out_md}")
        print(f"verdict={report['verdict']} block={summary['block_count']} warn={summary['warn_count']} info={summary['info_count']}")
        if args.write_progress and report["verdict"] != "pass":
            print("[info] verdict 非 pass，未回写 _进度.md")
    return 0 if report["verdict"] != "block" else 1


if __name__ == "__main__":
    raise SystemExit(main())
