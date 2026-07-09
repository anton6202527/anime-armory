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
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
try:
    import style_consistency
except Exception:  # pragma: no cover - review must still run if optional style gate breaks
    style_consistency = None
try:
    import character_consistency
except Exception:  # pragma: no cover - review must still run if optional character gate breaks
    character_consistency = None

COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
try:
    from platform_profiles import profile_for_platform, validate_manifest as validate_platform_manifest
except Exception:  # pragma: no cover
    profile_for_platform = None
    validate_platform_manifest = None


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


def display_path(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


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


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list):
        text = "；".join(compact_text(item) for item in value)
    elif isinstance(value, dict):
        text = "；".join(f"{key}:{compact_text(item)}" for key, item in value.items())
    else:
        text = str(value).strip()
    return " ".join(text.split()).strip("； ")


def panel_refs(panel: dict) -> list[str]:
    ids: list[str] = []
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw).strip()
            if ref_id and ref_id not in ids:
                ids.append(ref_id)
    return ids


def panel_character_refs(panel: dict) -> list[str]:
    return [ref_id for ref_id in panel_refs(panel) if ref_id.startswith(("CHAR_", "MON_"))]


def panel_character_count(panel: dict) -> int:
    names = {compact_text(name) for name in panel.get("characters") or [] if compact_text(name)}
    names.update(panel_character_refs(panel))
    return len(names)


def panel_has_character(panel: dict) -> bool:
    return bool(panel.get("characters")) or bool(panel_character_refs(panel))


def panel_scene_anchor_id(panel: dict) -> str:
    for key in ("scene_anchor_id", "scene_id", "location_id"):
        value = compact_text(panel.get(key))
        if value:
            return value
    for ref_id in panel_refs(panel):
        if ref_id.startswith("LOC_"):
            return ref_id
    return ""


def panel_has_scene(panel: dict) -> bool:
    return bool(compact_text(panel.get("location")) or panel_scene_anchor_id(panel))


def contract_value(panel: dict, inherited: dict, *keys: str) -> str:
    for key in keys:
        value = compact_text(panel.get(key))
        if value:
            return value
    for key in keys:
        value = compact_text(inherited.get(key))
        if value:
            return value
    return ""


CAMERA_GAZE_TERMS = (
    "看镜头",
    "直视镜头",
    "看读者",
    "直视读者",
    "看观众",
    "直视观众",
    "looking at viewer",
    "eye contact with camera",
    "camera",
    "viewer",
)
POV_CAMERA_ROLE_TERMS = ("pov", "主观", "第一人称", "破第四墙", "直视镜头", "直视读者")
VAGUE_GAZE_TERMS = ("坚定", "冷静", "愤怒", "悲伤", "惊讶", "眼神", "目光", "远方", "前方", "某处", "none", "n/a")
FACE_INTEGRITY_TERMS = ("脸", "五官", "眼", "眼型", "眼距", "发际线", "发型", "头发")
BODY_INTEGRITY_TERMS = ("手", "脚", "肢体", "身体", "腿", "手臂", "完整", "道具", "武器", "接触点")


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def camera_role_allows_direct_gaze(panel: dict) -> bool:
    return contains_any(compact_text(panel.get("camera_role")) + " " + compact_text(panel.get("pov")), POV_CAMERA_ROLE_TERMS)


def is_vague_gaze_target(value: str) -> bool:
    text = value.strip().lower()
    if not text:
        return False
    return any(term.lower() == text or term.lower() in text for term in VAGUE_GAZE_TERMS)


def is_weak_integrity_contract(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    return not (contains_any(text, FACE_INTEGRITY_TERMS) and contains_any(text, BODY_INTEGRITY_TERMS))


def visual_scene_anchors(panel_script: dict) -> dict:
    visual_contract = panel_script.get("visual_contract") if isinstance(panel_script.get("visual_contract"), dict) else {}
    anchors = visual_contract.get("scene_anchors") if isinstance(visual_contract.get("scene_anchors"), dict) else {}
    return anchors if isinstance(anchors, dict) else {}


def check_visual_contract_issues(panel_script: dict, chapter: str, issues: list[dict[str, str]]) -> None:
    panels = panel_script.get("panels") if isinstance(panel_script.get("panels"), list) else []
    if not panels:
        return
    visual_contract = panel_script.get("visual_contract") if isinstance(panel_script.get("visual_contract"), dict) else {}
    scene_anchors = visual_scene_anchors(panel_script)
    if not visual_contract:
        add_issue(
            issues,
            "block",
            "脚本/" + chapter + "/panel_script.json",
            "panel_script 缺少 visual_contract，无法审查角色脸、眼神、场景光位和轴线一致性",
            "comic-script",
            "补 visual_contract.scene_anchors / character_integrity_policy 后重建出图包",
            "visual_contract",
        )
    elif not scene_anchors:
        add_issue(
            issues,
            "block",
            "脚本/" + chapter + "/panel_script.json",
            "visual_contract 缺少 scene_anchors；长线漫画场景不能只靠逐格自然语言",
            "comic-script",
            "登记 LOC_ 场景锚，并写 spatial_layout / lighting_anchor / axis_eyeline",
            "visual_contract",
        )
    for scene_id, scene_contract in scene_anchors.items():
        if not isinstance(scene_contract, dict):
            continue
        missing = [key for key in ("spatial_layout", "lighting_anchor", "axis_eyeline") if not compact_text(scene_contract.get(key))]
        if missing:
            add_issue(
                issues,
                "block",
                f"脚本/{chapter}/panel_script.json#visual_contract.scene_anchors.{scene_id}",
                f"{scene_id} 场景锚缺少：" + ",".join(missing),
                "comic-script",
                "补齐该 LOC_ 的布局、光位和轴线视线",
                "visual_contract",
            )
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        pid = compact_text(panel.get("panel_id")) or "unknown"
        artifact = f"脚本/{chapter}/panel_script.json#{pid}"
        if panel_has_character(panel):
            gaze_target = contract_value(panel, {}, "gaze_target", "eyeline_target")
            eyeline_direction = contract_value(panel, {}, "eyeline_direction", "gaze_direction")
            integrity = contract_value(panel, visual_contract, "character_integrity", "completeness_notes", "character_integrity_policy")
            missing = []
            if not gaze_target:
                missing.append("gaze_target")
            if not eyeline_direction:
                missing.append("eyeline_direction")
            if not integrity:
                missing.append("character_integrity/completeness_notes")
            if missing:
                add_issue(
                    issues,
                    "block",
                    artifact,
                    f"{pid} 含角色但缺少人物/眼神契约：" + ",".join(missing),
                    "comic-script",
                    "补眼神目标、视线方向、脸/眼/发/服装/手脚完整性后再出图",
                    "visual_contract",
                )
            if gaze_target and contains_any(gaze_target, CAMERA_GAZE_TERMS) and not camera_role_allows_direct_gaze(panel):
                add_issue(
                    issues,
                    "block",
                    artifact,
                    f"{pid} 的 gaze_target 指向读者/镜头，但没有 POV 或破第四墙叙事理由",
                    "comic-script",
                    "改成戏内对象/对手/道具/画外声源，或明确 camera_role=POV/破第四墙",
                    "visual_contract",
                )
            elif gaze_target and is_vague_gaze_target(gaze_target):
                add_issue(
                    issues,
                    "warn",
                    artifact,
                    f"{pid} 的 gaze_target 过泛：{gaze_target}",
                    "comic-script",
                    "改成读者能定位的戏内目标，如对话对象、道具、命中点或画外声源",
                    "visual_contract",
                )
            if integrity and is_weak_integrity_contract(integrity):
                add_issue(
                    issues,
                    "warn",
                    artifact,
                    f"{pid} 的人物完整性契约未同时覆盖脸/眼/发和手脚/身体/关键道具",
                    "comic-script",
                    "补脸型、眼型/眼距、发际线、发型、服装标志、手脚和关键道具完整性",
                    "visual_contract",
                )
        if panel_has_scene(panel):
            scene_id = panel_scene_anchor_id(panel)
            scene_contract = scene_anchors.get(scene_id) if scene_id in scene_anchors and isinstance(scene_anchors.get(scene_id), dict) else {}
            missing_scene = []
            if not scene_id:
                missing_scene.append("scene_anchor_id/LOC_")
            elif visual_contract and scene_id not in scene_anchors:
                add_issue(
                    issues,
                    "block",
                    artifact,
                    f"{pid} 使用 {scene_id}，但 visual_contract.scene_anchors 未登记该场景锚",
                    "comic-script",
                    "登记该 LOC_ 场景锚，或改用已登记场景锚",
                    "visual_contract",
                )
            if not contract_value(panel, scene_contract, "spatial_layout", "scene_layout", "layout"):
                missing_scene.append("spatial_layout")
            if not contract_value(panel, scene_contract, "lighting_anchor", "light_anchor"):
                missing_scene.append("lighting_anchor")
            if not contract_value(panel, scene_contract, "axis_eyeline", "eyeline_axis", "axis"):
                missing_scene.append("axis_eyeline")
            if missing_scene:
                add_issue(
                    issues,
                    "block",
                    artifact,
                    f"{pid} 含场景但缺少场景连续性契约：" + ",".join(missing_scene),
                    "comic-script",
                    "补 LOC_ 场景锚、空间布局、光位/冷暖和轴线视线",
                    "visual_contract",
                )
            if panel_character_count(panel) >= 2 and not contract_value(panel, scene_contract, "spatial_relationships", "blocking", "staging"):
                add_issue(
                    issues,
                    "block",
                    artifact,
                    f"{pid} 含多个角色但缺少人物左右/前后景/遮挡或轴线关系",
                    "comic-script",
                    "补 spatial_relationships/blocking/staging，写清站位、遮挡和关键接触点",
                    "visual_contract",
                )


def traditional_workflow_enabled(root: Path) -> bool:
    return read_setting(root, "传统原稿流程", "启用") not in {"关闭", "off", "disabled", "false", "False"}


def finishing_panel_ids(finishing_plan: dict) -> set[str]:
    ids: set[str] = set()
    for panel in finishing_plan.get("panels") or []:
        if isinstance(panel, dict) and panel.get("panel_id"):
            ids.add(str(panel.get("panel_id")))
    return ids


def check_traditional_manga_issues(root: Path, chapter: str, panel_script: dict, layout: dict, issues: list[dict[str, str]]) -> None:
    if not traditional_workflow_enabled(root):
        return
    name_path = root / "排版" / chapter / "name_board.json"
    finish_path = root / "出图" / chapter / "finishing" / "finishing_plan.json"
    name_board = load_json(name_path, {})
    finishing_plan = load_json(finish_path, {})
    if not name_board:
        add_issue(
            issues,
            "warn",
            display_path(root, name_path),
            "传统原稿流程已启用，但缺少缩略分镜/name_board；页流、翻页钩子和格子轻重缺少ネーム层证据",
            "comic-name",
            "运行 comic-name 生成 name_board.json，再重建 layout",
            "traditional_manga",
        )
    manuscript = layout.get("manuscript") if isinstance(layout.get("manuscript"), dict) else {}
    if not manuscript or not manuscript.get("safe_area"):
        add_issue(
            issues,
            "warn",
            "排版/" + chapter + "/layout.json",
            "layout 缺少原稿 trim/safe_area/inner_frame，页漫或投稿规格有裁切和嵌字风险",
            "comic-layout",
            "重跑 comic-layout，并确认已接入 comic-name 的原稿安全框",
            "traditional_manga",
        )
    if not finishing_plan:
        add_issue(
            issues,
            "warn",
            display_path(root, finish_path),
            "缺少墨线/黑场/网点/效果线计划，出图 prompt 缺传统完成稿层",
            "comic-finishing",
            "运行 comic-finishing 生成 finishing_plan.json 后重建出图包",
            "traditional_manga",
        )
    else:
        planned = finishing_panel_ids(finishing_plan)
        missing = [
            str(panel.get("panel_id"))
            for panel in panel_script.get("panels") or []
            if isinstance(panel, dict) and panel.get("panel_id") and str(panel.get("panel_id")) not in planned
        ]
        if missing:
            add_issue(
                issues,
                "warn",
                display_path(root, finish_path),
                "这些 panel 缺少传统原稿收尾计划：" + ", ".join(missing[:20]),
                "comic-finishing",
                "重跑 comic-finishing 或补齐对应 panel 的 ink/tone/effects 计划",
                "traditional_manga",
            )


def source_semantics_requires_normalization(panel_script: dict, source_semantics: dict) -> bool:
    script_meta = panel_script.get("source_semantics") if isinstance(panel_script.get("source_semantics"), dict) else {}
    return bool(source_semantics.get("requires_normalization") or script_meta.get("requires_normalization"))


def required_source_semantic_panel_fields(source_semantics: dict) -> list[str]:
    contract = source_semantics.get("panel_script_contract") if isinstance(source_semantics.get("panel_script_contract"), dict) else {}
    fields = contract.get("required_panel_fields_when_normalized")
    if isinstance(fields, list) and all(isinstance(item, str) for item in fields):
        return fields
    return ["source_excerpt", "meaning_zh", "text_target", "adaptation_note"]


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


def is_publish_like_usage(value: str) -> bool:
    usage = str(value or "").strip().lower()
    if not usage:
        return False
    draft_tokens = ("草稿", "打样", "内部", "自用", "测试", "预览", "demo", "draft", "internal", "preview", "test")
    return not any(token in usage for token in draft_tokens)


def is_demo_like_usage(value: str) -> bool:
    usage = str(value or "").strip().lower()
    return any(token in usage for token in ("demo", "学习", "草稿", "自用", "内部", "测试", "预览", "draft", "internal", "preview", "test"))


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


def load_raw_bubble_acceptance(root: Path, chapter: str) -> dict[str, dict[str, Any]]:
    path = root / "生产数据" / f"raw_bubble_acceptance_{chapter}.json"
    data = load_json(path, {})
    accepted: dict[str, dict[str, Any]] = {}
    if isinstance(data, dict):
        for item in data.get("accepted_findings") or []:
            if not isinstance(item, dict):
                continue
            panel_id = str(item.get("panel_id") or "").strip()
            code = str(item.get("code") or "raw_bubble_candidate").strip()
            if panel_id and code in {"raw_bubble_candidate", "baked_blank_bubble_candidate"}:
                accepted[panel_id] = {
                    "panel_id": panel_id,
                    "code": code,
                    "status": "accepted",
                    "accepted_by": str(item.get("accepted_by") or data.get("accepted_by") or "manual_review"),
                    "accepted_at": str(item.get("accepted_at") or data.get("accepted_at") or ""),
                    "reason": str(item.get("reason") or ""),
                    "evidence": str(item.get("evidence") or ""),
                    "source": display_path(root, path),
                }
        for panel_id in data.get("accepted_panels") or []:
            pid = str(panel_id).strip()
            if pid and pid not in accepted:
                accepted[pid] = {
                    "panel_id": pid,
                    "code": "raw_bubble_candidate",
                    "status": "accepted",
                    "accepted_by": str(data.get("accepted_by") or "manual_review"),
                    "accepted_at": str(data.get("accepted_at") or ""),
                    "reason": "accepted by panel list",
                    "evidence": "",
                    "source": display_path(root, path),
                }
    qc_dir = root / "生产数据" / "panel_qc" / chapter
    if not qc_dir.is_dir():
        return accepted
    for qc_path in sorted(qc_dir.glob("*.json")):
        qc = load_json(qc_path, {})
        if not isinstance(qc, dict):
            continue
        panel_id = str(qc.get("panel_id") or qc_path.stem).strip()
        manual = qc.get("manual_review") if isinstance(qc.get("manual_review"), dict) else {}
        verdict = str(manual.get("verdict") or "").strip().lower()
        if not panel_id or verdict not in {"pass", "accepted", "accept"}:
            continue
        accepted[panel_id] = {
            "panel_id": panel_id,
            "code": "raw_bubble_candidate",
            "status": "accepted",
            "accepted_by": str(manual.get("reviewed_by") or manual.get("accepted_by") or "manual_review"),
            "accepted_at": str(manual.get("reviewed_at") or manual.get("accepted_at") or ""),
            "reason": str(manual.get("reason") or ""),
            "evidence": display_path(root, qc_path),
            "source": display_path(root, qc_path),
        }
    return accepted


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
        "source_semantics": root / "脚本" / chapter / "source_semantics.json",
        "layout": root / "排版" / chapter / "layout.json",
        "lettering": root / "排版" / chapter / "lettering.json",
        "manifest": root / "排版" / chapter / "export_manifest.json",
        "identity_report": root / "生产数据" / f"comic_identity_report_{chapter}.json",
        "identity_registry": root / "出图" / "共享" / "identity_registry.json",
        "style_report": root / "生产数据" / f"comic_style_consistency_{chapter}.json",
        "character_report": root / "生产数据" / f"comic_character_consistency_{chapter}.json",
        "panel_dir": root / "出图" / chapter / "panels",
    }
    for key in ("progress", "settings", "meta", "panel_script", "layout", "lettering", "manifest"):
        if not paths[key].is_file():
            add_issue(issues, "block", str(paths[key].relative_to(root)), "审查必需文件缺失", "comic-" + ("compose" if key in ("lettering", "manifest") else "script"), "补齐文件后重新运行 comic-review", "missing_artifact")

    panel_script = load_json(paths["panel_script"], {})
    script_source_meta = panel_script.get("source_semantics") if isinstance(panel_script.get("source_semantics"), dict) else {}
    source_semantics_path = root / str(script_source_meta.get("path") or paths["source_semantics"].relative_to(root))
    source_semantics = load_json(source_semantics_path, {})
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
    semantics_file_exists = source_semantics_path.is_file()
    script_requires_semantics = bool(script_source_meta.get("requires_normalization"))
    if semantics_file_exists or script_requires_semantics:
        if not source_semantics:
            add_issue(
                issues,
                "block",
                display_path(root, source_semantics_path),
                "source_semantics 元数据存在但文件不可解析或缺失",
                "comic-script",
                "重新运行 source_semantics_gate.py 并修复输出文件",
                "script",
            )
        elif source_semantics.get("requires_normalization") and source_semantics.get("status") != "pass":
            add_issue(
                issues,
                "block",
                display_path(root, source_semantics_path),
                "源语义归一化 gate 未通过：" + "；".join(map(str, source_semantics.get("issues") or [])),
                "comic-script",
                "补齐专名表、逐段释义、目标嵌字文本、歧义处理和改编取舍账后重跑 gate",
                "script",
            )
    if source_semantics_requires_normalization(panel_script, source_semantics):
        required_fields = required_source_semantic_panel_fields(source_semantics)
        missing_trace: list[str] = []
        for panel in panel_script.get("panels") or []:
            pid = str(panel.get("panel_id") or "")
            missing = [field for field in required_fields if not str(panel.get(field) or "").strip()]
            if missing:
                missing_trace.append(f"{pid or 'unknown'}({','.join(missing)})")
        if missing_trace:
            add_issue(
                issues,
                "block",
                "脚本/" + chapter + "/panel_script.json",
                "归一化源本的 panel 缺少语义追溯字段：" + "；".join(missing_trace[:20]),
                "comic-script",
                "为每格补 source_excerpt、meaning_zh、text_target、adaptation_note 后再排版",
                "script",
            )
    for panel in panel_script.get("panels") or []:
        pid = str(panel.get("panel_id") or "")
        if not str(panel.get("story_function") or "").strip():
            add_issue(issues, "warn", pid, "story_function 为空，审查难以判断本格叙事功能", "comic-script", "补上本格叙事功能", "script")
    if isinstance(panel_script, dict):
        check_visual_contract_issues(panel_script, chapter, issues)
        check_traditional_manga_issues(root, chapter, panel_script, layout if isinstance(layout, dict) else {}, issues)

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

    slot_qc = manifest.get("lettering_slot_qc") if isinstance(manifest.get("lettering_slot_qc"), dict) else {}
    if manifest.get("lettering_rendered"):
        if not slot_qc:
            add_issue(
                issues,
                "info",
                "排版/" + chapter + "/export_manifest.json",
                "manifest 未记录嵌字槽位 QC 接触表，长条图过高时不便逐字复核",
                "comic-compose",
                "用 export_longstrip.py --render --qc-slots 重新导出",
                "lettering",
            )
        else:
            qc_path = root / str(slot_qc.get("path") or "")
            missing_slots = [str(item) for item in slot_qc.get("missing_slots") or []]
            if not qc_path.is_file():
                add_issue(
                    issues,
                    "warn",
                    "排版/" + chapter + "/export_manifest.json",
                    "manifest 记录了 lettering_slot_qc，但 QC 图文件不存在",
                    "comic-compose",
                    "用 export_longstrip.py --render --qc-slots 重新导出",
                    "lettering",
                )
            if missing_slots:
                add_issue(
                    issues,
                    "warn",
                    display_path(root, qc_path),
                    "嵌字槽位 QC 接触表存在缺失 slot：" + ", ".join(missing_slots[:20]),
                    "comic-compose",
                    "同步 layout/lettering 后重新导出并复核槽位接触表",
                    "lettering",
                )

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

    text_layout_qc = manifest.get("text_layout_qc") if isinstance(manifest.get("text_layout_qc"), dict) else {}
    unsupported_text = text_layout_qc.get("unsupported_items") if isinstance(text_layout_qc.get("unsupported_items"), list) else []
    if unsupported_text:
        ids = [str(item.get("item_id") or item.get("panel_id") or "") for item in unsupported_text if isinstance(item, dict)]
        add_issue(
            issues,
            "block",
            "排版/" + chapter + "/lettering.json",
            "当前嵌字 renderer 不支持 RTL 或需词典分词文字：" + ", ".join(item for item in ids[:20] if item),
            "comic-compose",
            "改用人工/专业排版 renderer，或改成当前 renderer 支持的目标嵌字语言后重新导出",
            "lettering",
        )

    platform_findings = manifest.get("platform_findings") if isinstance(manifest.get("platform_findings"), list) else []
    for finding in platform_findings:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity") or "warn")
        if severity not in {"block", "warn", "info"}:
            severity = "warn"
        add_issue(
            issues,
            severity,
            str(finding.get("artifact") or "排版/" + chapter + "/export_manifest.json"),
            str(finding.get("reason") or "平台导出规格 finding"),
            "comic-compose",
            str(finding.get("suggested_fix") or "按目标平台 profile 重新导出"),
            "export",
        )
    if not platform_findings and validate_platform_manifest and profile_for_platform:
        profile = profile_for_platform(str(manifest.get("target_platform") or read_setting(root, "目标平台", "通用")))
        for finding in validate_platform_manifest(root, manifest, profile, settings["合规用途"]):
            severity = str(finding.get("severity") or "warn")
            add_issue(
                issues,
                severity if severity in {"block", "warn", "info"} else "warn",
                str(finding.get("artifact") or "排版/" + chapter + "/export_manifest.json"),
                str(finding.get("reason") or "平台导出规格 finding"),
                "comic-compose",
                str(finding.get("suggested_fix") or "按目标平台 profile 重新导出"),
                "export",
            )

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
    raw_bubble_acceptance = load_raw_bubble_acceptance(root, chapter)
    accepted_raw_bubble_hits = [hit for hit in raw_bubble_hits if hit["panel_id"] in raw_bubble_acceptance]
    unresolved_raw_bubble_hits = [hit for hit in raw_bubble_hits if hit["panel_id"] not in raw_bubble_acceptance]
    if unresolved_raw_bubble_hits:
        add_issue(
            issues,
            "warn",
            "出图/" + chapter + "/panels",
            "原始面板图疑似烘焙了空白气泡/文字容器：" + ", ".join(hit["panel_id"] for hit in unresolved_raw_bubble_hits[:18]),
            "comic-image",
            "后续重抽这些格时要求无字画面、无空白气泡，只保留低细节留白；系统绘卷等叙事道具可人工豁免",
            "image",
        )
    for hit in accepted_raw_bubble_hits:
        acceptance = raw_bubble_acceptance.get(hit["panel_id"], {})
        add_issue(
            issues,
            "info",
            hit["path"],
            "疑似烘焙空白气泡已人审签收为误报：" + str(acceptance.get("reason") or "计划内亮部/雾面/叙事道具"),
            "comic-review",
            "若该格重抽或构图变化，需要重新复核原始图空白气泡机检",
            "image",
        )

    style_report: dict[str, Any] = {}
    if style_consistency is None:
        add_issue(
            issues,
            "warn",
            "skills/comic-review/scripts/style_consistency.py",
            "风格一致性机检模块不可用，已跳过严格画风离群检查",
            "comic-review",
            "修复 style_consistency.py 后重跑 comic-review",
            "style",
        )
    else:
        style_report = style_consistency.analyze(root, chapter)
        style_paths = style_consistency.write_outputs(root, chapter, style_report)
        notes.append(f"已刷新风格一致性报告：{style_paths['markdown']}")
        for finding in style_report.get("findings") or []:
            severity = str(finding.get("severity") or "warn")
            if severity not in {"block", "warn", "info"}:
                severity = "warn"
            add_issue(
                issues,
                severity,
                str(finding.get("artifact") or finding.get("panel_id") or paths["style_report"].relative_to(root)),
                str(finding.get("reason") or "风格一致性 finding"),
                "comic-image" if severity in {"block", "warn"} else "comic-review",
                str(finding.get("suggested_fix") or "按风格一致性报告返修"),
                "style",
            )

    character_report: dict[str, Any] = {}
    if character_consistency is None:
        add_issue(
            issues,
            "warn",
            "skills/comic-review/scripts/character_consistency.py",
            "角色一致性机检模块不可用，已跳过角色并排复核图和 face/hair/outfit 指纹检查",
            "comic-review",
            "修复 character_consistency.py 后重跑 comic-review",
            "character",
        )
    else:
        character_report = character_consistency.analyze(root, chapter)
        character_paths = character_consistency.write_outputs(root, chapter, character_report)
        notes.append(f"已刷新角色一致性报告：{character_paths['markdown']}")
        for finding in character_report.get("findings") or []:
            severity = str(finding.get("severity") or "warn")
            if severity not in {"block", "warn", "info"}:
                severity = "warn"
            add_issue(
                issues,
                severity,
                str(finding.get("artifact") or finding.get("panel_id") or paths["character_report"].relative_to(root)),
                str(finding.get("reason") or "角色一致性 finding"),
                "comic-image" if severity in {"block", "warn"} else "comic-review",
                str(finding.get("suggested_fix") or "按角色一致性报告返修"),
                "character",
            )

    rights = (meta.get("rights") or {}) if isinstance(meta, dict) else {}
    publish_like = is_publish_like_usage(settings["合规用途"])
    demo_like = is_demo_like_usage(settings["合规用途"])
    for key, label in (("font_status", "字体权利"), ("asset_status", "素材权利")):
        if str(rights.get(key) or "").startswith("pending"):
            if publish_like:
                add_issue(
                    issues,
                    "block",
                    "_meta.json",
                    f"{label}仍是 {rights.get(key)}",
                    "comic-review",
                    "发布/商用前确认授权并更新 _meta.json",
                    "rights",
                )
            elif demo_like:
                notes.append(f"{settings['合规用途']} 用途：{label}={rights.get(key)}，仅记录，不进入发布授权流程。")
            else:
                add_issue(
                    issues,
                    "info",
                    "_meta.json",
                    f"{label}仍是 {rights.get(key)}",
                    "comic-review",
                    "发布/商用前确认授权并更新 _meta.json",
                    "rights",
                )
    if manifest.get("font_status") == "system_font_draft":
        if publish_like:
            add_issue(
                issues,
                "block",
                "排版/" + chapter + "/export_manifest.json",
                "当前使用 system_font_draft，不能当正式发布字体授权",
                "comic-compose",
                "发布前用已授权字体重新导出，或更新字体授权记录",
                "rights",
            )
        elif demo_like:
            notes.append(f"{settings['合规用途']} 用途：system_font_draft 仅作草稿嵌字字体记录，不进入发布授权流程。")
        else:
            add_issue(
                issues,
                "info",
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
            "source_semantics": display_path(root, source_semantics_path) if source_semantics_path else "",
            "layout": str(paths["layout"].relative_to(root)),
            "lettering": str(paths["lettering"].relative_to(root)),
            "manifest": str(paths["manifest"].relative_to(root)),
            "identity_report": str(paths["identity_report"].relative_to(root)),
            "style_report": str(paths["style_report"].relative_to(root)),
            "character_report": str(paths["character_report"].relative_to(root)),
            "rendered": rendered,
            "lettering_slot_qc": slot_qc,
            "qa_preview": preview,
            "contact_sheet": contact_sheet,
        },
        "raw_bubble_candidates": raw_bubble_hits,
        "accepted_raw_bubble_candidates": accepted_raw_bubble_hits,
        "style_consistency": {
            "verdict": style_report.get("verdict", "skipped") if isinstance(style_report, dict) else "skipped",
            "summary": style_report.get("summary", {}) if isinstance(style_report, dict) else {},
        },
        "character_consistency": {
            "verdict": character_report.get("verdict", "skipped") if isinstance(character_report, dict) else "skipped",
            "summary": character_report.get("summary", {}) if isinstance(character_report, dict) else {},
            "contact_sheet": character_report.get("contact_sheet", "") if isinstance(character_report, dict) else "",
        },
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
        accepted_panels = {str(hit.get("panel_id")) for hit in report.get("accepted_raw_bubble_candidates") or []}
        for hit in report["raw_bubble_candidates"]:
            status = "已签收为误报" if str(hit.get("panel_id")) in accepted_panels else "待处理"
            lines.append(f"- {hit['panel_id']}: `{hit['path']}` components={len(hit.get('components') or [])}，{status}")
    if report.get("style_consistency"):
        style = report["style_consistency"]
        lines += ["", "## 风格一致性", ""]
        lines.append(f"- 结论：{style.get('verdict')}")
        lines.append(f"- 摘要：{json.dumps(style.get('summary') or {}, ensure_ascii=False)}")
    if report.get("character_consistency"):
        character = report["character_consistency"]
        lines += ["", "## 角色一致性", ""]
        lines.append(f"- 结论：{character.get('verdict')}")
        lines.append(f"- 摘要：{json.dumps(character.get('summary') or {}, ensure_ascii=False)}")
        if character.get("contact_sheet"):
            lines.append(f"- 并排复核图：`{character.get('contact_sheet')}`")
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
