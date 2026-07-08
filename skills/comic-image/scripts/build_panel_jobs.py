#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 panel_script.json 与 layout.json 生成逐格出图任务包。"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
try:
    from image_backend_adapter import ImageBackendCapabilities, resolve_capabilities
except Exception:  # pragma: no cover - keep job building usable in partially-copied skill folders
    ImageBackendCapabilities = Any  # type: ignore
    resolve_capabilities = None  # type: ignore


PRESERVE_GENERATION_KEYS = {
    "status",
    "result_path",
    "source",
    "model",
    "generated_at",
    "backend_version",
    "artifact_sha256",
    "attempt",
    "reference_input_mode",
    "reference_input_count",
    "reference_manifest",
    "post_qc",
    "last_error",
}
LEGACY_MAX_REFERENCE_IMAGES_PER_JOB = 6
LEGACY_SINGLE_CHARACTER_REFERENCE_LIMIT = 4
LEGACY_MULTI_CHARACTER_REFERENCE_LIMIT = 2
REFERENCE_VIEW_PRIORITY = {
    "anchor_path": 0,
    "anchor": 0,
    "primary_path": 0,
    "face": 1,
    "front": 2,
    "three_quarter": 3,
    "side": 4,
    "back": 5,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_setting(root: Path, key: str, default: str) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def load_reference_registry(root: Path) -> dict:
    path = root / "出图" / "共享" / "identity_registry.json"
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def load_finishing_plan(root: Path, chapter: str) -> dict[str, Any]:
    path = root / "出图" / chapter / "finishing" / "finishing_plan.json"
    if not path.is_file():
        return {}
    try:
        data = load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def finishing_by_panel(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for panel in plan.get("panels") or []:
        if isinstance(panel, dict) and panel.get("panel_id"):
            out[str(panel.get("panel_id"))] = panel
    return out


def path_relative_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_reference_paths(root: Path, ref_id: str, registry: dict) -> list[dict[str, str]]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets, dict) else None
    candidates: list[tuple[str, Path]] = []
    if isinstance(asset, dict):
        for key in ("anchor_path", "primary_path", "path"):
            raw = asset.get(key)
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                candidates.append((key, path if path.is_absolute() else root / path))
        views = asset.get("views") if isinstance(asset.get("views"), dict) else {}
        for key in ("front", "three_quarter", "face", "side", "back"):
            raw = views.get(key) if isinstance(views, dict) else ""
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                candidates.append((key, path if path.is_absolute() else root / path))
        for item in asset.get("reference_images") or []:
            raw = item.get("path") if isinstance(item, dict) else item
            if isinstance(raw, str) and raw.strip():
                path = Path(raw)
                role = str(item.get("view") or item.get("role") or "reference_image") if isinstance(item, dict) else "reference_image"
                candidates.append((role, path if path.is_absolute() else root / path))
    shared = root / "出图" / "共享" / "图片"
    for suffix in ("__anchor.png", ".png", ".jpg", ".jpeg", ".webp"):
        candidates.append(("anchor", shared / f"{ref_id}{suffix}"))
    out: list[dict[str, str]] = []
    seen: set[Path] = set()
    for role, path in candidates:
        if path.is_file():
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append({"id": ref_id, "path": path_relative_to_root(root, path), "view": role})
    return out


def compact_metadata(value: Any, *, max_len: int = 460) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list):
        text = "；".join(compact_metadata(item, max_len=max_len) for item in value)
    elif isinstance(value, dict):
        items = []
        for key, item in value.items():
            item_text = compact_metadata(item, max_len=max_len)
            if item_text:
                items.append(f"{key}:{item_text}")
        text = "；".join(items)
    else:
        text = str(value).strip()
    text = re.sub(r"\s+", " ", text).strip("； ")
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def asset_contract(ref_id: str, asset: dict[str, Any]) -> str:
    label = str(asset.get("display_name") or asset.get("name") or ref_id)
    parts = [f"{ref_id}={label}"]
    for key, title in (
        ("character_dna", "角色DNA"),
        ("dna_contract", "定妆契约"),
        ("prop_contract", "道具契约"),
        ("variant_policy", "年龄/形态继承"),
        ("forbidden_inheritance", "禁继承"),
        ("style_contract", "风格契约"),
        ("notes", "备注"),
    ):
        limit = 300 if key in {"character_dna", "prop_contract"} else 180
        text = compact_metadata(asset.get(key), max_len=limit)
        if text:
            parts.append(f"{title}:{text}")
    age_variants = asset.get("age_variants")
    if isinstance(age_variants, dict) and age_variants:
        parts.append("已定义年龄形态:" + ",".join(map(str, age_variants.keys())))
    if str(asset.get("type") or "").lower() == "character" or ref_id.startswith("CHAR_"):
        parts.append("同一角色换年龄、受伤、闭关、觉醒或换装时，只允许改变年龄比例/状态/服饰层，不得换脸、换发际线、换眼型或丢失标志物")
    return "；".join(parts)


def registry_style_contract(registry: dict) -> str:
    parts: list[str] = []
    for key, limit in (("style_contract", 360), ("consistency_policy", 260), ("forbidden_inheritance", 160)):
        text = compact_metadata(registry.get(key), max_len=limit)
        if text:
            parts.append(f"{key}:{text}")
    return "；".join(parts)


def panel_reference_ids(panel: dict) -> list[str]:
    ids: list[str] = []
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw).strip()
            if ref_id and ref_id.startswith(("CHAR_", "MON_", "LOC_", "PROP_", "SYS_", "FX_", "STYLE_")) and ref_id not in ids:
                ids.append(ref_id)
    return ids


def panel_scene_anchor_id(panel: dict) -> str:
    for key in ("scene_anchor_id", "scene_id", "location_id"):
        value = str(panel.get(key) or "").strip()
        if value:
            return value
    for ref_id in panel_reference_ids(panel):
        if ref_id.startswith("LOC_"):
            return ref_id
    return ""


def scene_anchor_contract(panel_script: dict, scene_id: str) -> dict[str, Any]:
    visual_contract = panel_script.get("visual_contract") if isinstance(panel_script.get("visual_contract"), dict) else {}
    anchors = visual_contract.get("scene_anchors") if isinstance(visual_contract.get("scene_anchors"), dict) else {}
    contract = anchors.get(scene_id) if scene_id and isinstance(anchors, dict) else {}
    return contract if isinstance(contract, dict) else {}


def first_contract_value(*values: Any) -> str:
    for value in values:
        text = compact_metadata(value)
        if text:
            return text
    return ""


def panel_continuity_contract(panel: dict, panel_script: dict) -> dict[str, str]:
    scene_id = panel_scene_anchor_id(panel)
    scene_contract = scene_anchor_contract(panel_script, scene_id)
    visual_contract = panel_script.get("visual_contract") if isinstance(panel_script.get("visual_contract"), dict) else {}
    return {
        key: value
        for key, value in {
            "scene_anchor_id": scene_id,
            "spatial_layout": first_contract_value(panel.get("spatial_layout"), panel.get("scene_layout"), scene_contract.get("spatial_layout"), scene_contract.get("layout")),
            "lighting_anchor": first_contract_value(panel.get("lighting_anchor"), panel.get("light_anchor"), scene_contract.get("lighting_anchor"), scene_contract.get("light_anchor")),
            "axis_eyeline": first_contract_value(panel.get("axis_eyeline"), panel.get("axis"), scene_contract.get("axis_eyeline"), scene_contract.get("eyeline_axis")),
            "resident_assets": first_contract_value(panel.get("resident_assets"), scene_contract.get("resident_assets")),
            "gaze_target": first_contract_value(panel.get("gaze_target"), panel.get("eyeline_target")),
            "eyeline_direction": first_contract_value(panel.get("eyeline_direction"), panel.get("gaze_direction")),
            "camera_role": first_contract_value(panel.get("camera_role"), panel.get("pov")),
            "continuity_from": first_contract_value(panel.get("continuity_from"), panel.get("previous_panel")),
            "character_integrity": first_contract_value(panel.get("character_integrity"), panel.get("completeness_notes"), visual_contract.get("character_integrity_policy")),
            "spatial_relationships": first_contract_value(panel.get("spatial_relationships"), panel.get("blocking"), panel.get("staging")),
        }.items()
        if value
    }


def reference_priority(item: dict[str, str]) -> tuple[int, str]:
    view = str(item.get("view") or "")
    return (REFERENCE_VIEW_PRIORITY.get(view, 99), str(item.get("path") or ""))


def ref_kind(ref_id: str) -> str:
    if ref_id.startswith("CHAR_") or ref_id.startswith("MON_"):
        return "character"
    if ref_id.startswith("STYLE_"):
        return "style"
    return "asset"


def _cap_value(caps: Any, name: str, default: int) -> int:
    try:
        value = int(getattr(caps, name))
    except Exception:
        return default
    return max(0, value)


def panel_references(root: Path, panel: dict, registry: dict, caps: Any) -> list[dict[str, str]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for ref_id in panel_reference_ids(panel):
        resolved = resolve_reference_paths(root, str(ref_id), registry) or [{"id": str(ref_id), "path": ""}]
        grouped[ref_id] = sorted(resolved, key=reference_priority)

    character_ids = [ref_id for ref_id in grouped if ref_id.startswith("CHAR_")]
    char_limit = (
        _cap_value(caps, "single_character_reference_limit", LEGACY_SINGLE_CHARACTER_REFERENCE_LIMIT)
        if len(character_ids) <= 1
        else _cap_value(caps, "multi_character_reference_limit", LEGACY_MULTI_CHARACTER_REFERENCE_LIMIT)
    )
    non_character_limit = _cap_value(caps, "non_character_reference_limit", 1)
    style_limit = _cap_value(caps, "style_reference_limit", 1)
    max_refs = _cap_value(caps, "reference_image_limit", LEGACY_MAX_REFERENCE_IMAGES_PER_JOB)
    selected: list[dict[str, str]] = []
    deferred_groups: list[list[dict[str, str]]] = []
    for ref_id, refs in grouped.items():
        kind = ref_kind(ref_id)
        if kind == "character":
            limit = char_limit
        elif kind == "style":
            limit = style_limit
        else:
            limit = non_character_limit
        selected.extend(refs[:limit])
        if refs[limit:]:
            deferred_groups.append(list(refs[limit:]))

    while len(selected) < max_refs and any(deferred_groups):
        progressed = False
        for refs in deferred_groups:
            if len(selected) >= max_refs:
                break
            if refs:
                selected.append(refs.pop(0))
                progressed = True
        if not progressed:
            break
    if len(selected) > max_refs:
        non_char = [item for item in selected if ref_kind(str(item.get("id") or "")) != "character"]
        char = [item for item in selected if ref_kind(str(item.get("id") or "")) == "character"]
        selected = (non_char + char)[:max_refs]
    return selected


def panel_rects(layout: dict) -> dict[str, dict]:
    rects = {}
    for segment in layout.get("segments", []):
        for panel in segment.get("panels", []):
            pid = panel.get("panel_id")
            if pid:
                rects[pid] = panel
    return rects


def build_prompt(panel: dict, style: str, registry: dict, panel_script: dict, finish: dict[str, Any], render_stage: str) -> str:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    ref_ids = panel_reference_ids(panel)
    continuity = panel_continuity_contract(panel, panel_script)
    parts = [
        f"无字漫画分格画面，{style}",
        f"画面事实：{panel.get('description', '')}",
    ]
    style_contract = registry_style_contract(registry)
    if style_contract:
        parts.append("项目风格锚与一致性契约：" + style_contract)
    if panel.get("characters"):
        parts.append("角色：" + "、".join(map(str, panel.get("characters", []))))
    if panel.get("location"):
        parts.append("场景：" + str(panel.get("location")))
    if continuity:
        scene_parts = []
        for key, label in (
            ("scene_anchor_id", "场景锚"),
            ("spatial_layout", "空间布局"),
            ("lighting_anchor", "光位/光色"),
            ("axis_eyeline", "轴线/视线"),
            ("resident_assets", "常驻物件"),
            ("continuity_from", "承接上一格"),
            ("spatial_relationships", "人物站位/前后景"),
        ):
            if continuity.get(key):
                scene_parts.append(f"{label}:{continuity[key]}")
        if scene_parts:
            parts.append("场景一致性契约：" + "；".join(scene_parts))
        if continuity.get("gaze_target") or continuity.get("eyeline_direction") or continuity.get("camera_role"):
            parts.append(
                "视线/眼神契约："
                + "；".join(
                    item
                    for item in (
                        f"目标={continuity.get('gaze_target')}" if continuity.get("gaze_target") else "",
                        f"方向={continuity.get('eyeline_direction')}" if continuity.get("eyeline_direction") else "",
                        f"镜头角色={continuity.get('camera_role')}" if continuity.get("camera_role") else "",
                    )
                    if item
                )
            )
        if continuity.get("character_integrity"):
            parts.append("人物完整性契约：" + continuity["character_integrity"])
    if panel.get("art_notes"):
        parts.append("构图与表演：" + str(panel.get("art_notes")))
    finish_parts = []
    for key, label in (
        ("art_stage_sequence", "传统稿层顺序"),
        ("ink_plan", "墨线计划"),
        ("black_fill_plan", "黑场计划"),
        ("tone_plan", "网点/灰阶计划"),
        ("value_plan", "黑白灰可读性"),
        ("effects_plan", "效果线/漫符计划"),
        ("lettering_sfx_plan", "拟声词画法"),
        ("no_bake_text_contract", "无字原图契约"),
    ):
        text = compact_metadata(finish.get(key), max_len=360)
        if text:
            finish_parts.append(f"{label}:{text}")
    if finish_parts:
        parts.append(f"传统漫画原稿收尾契约（目标稿层={render_stage or '完成稿'}）：" + "；".join(finish_parts))
    if ref_ids:
        contracts = []
        for ref_id in ref_ids:
            asset = assets.get(ref_id) if isinstance(assets, dict) else None
            if isinstance(asset, dict):
                contracts.append(asset_contract(ref_id, asset))
            else:
                contracts.append(ref_id)
        parts.append("共享参考ID与不可漂移约束：" + " || ".join(contracts))
    if panel.get("dialogue") or panel.get("narration"):
        parts.append("在不挡脸、不挡手脚、不挡关键道具的位置预留低细节留白区域；不要画对白气泡、旁白框、空白文字框或任何可读文字")
    parts.append("定型参考图是最高优先级；截图里的播放按钮、搜索框、字幕、水印、平台 UI、竖排标题和可读文字都不是设定，必须排除")
    if panel.get("characters") or any(ref_id.startswith(("CHAR_", "MON_")) for ref_id in ref_ids):
        parts.append("角色必须保持同一张脸、同一眼型/眼距、发际线、发型轮廓、服装主色和标志配饰；头发、脸、手臂、手、腿、脚和关键道具必须完整可读，不能裁掉叙事需要的身体部位")
        parts.append("除非本格明确写 POV/破第四墙，角色不要直视读者镜头；眼神应锁定戏内对象、对手、道具、对白对象或下一动作目标")
    parts.append("线条清晰，主体明确，角色脸部、发型、服装、灵力纹路、标志道具和整体画风稳定，适合后期嵌字")
    return "；".join(part for part in parts if part)


def build_jobs(root: Path, chapter: str) -> dict:
    panel_script = load_json(root / "脚本" / chapter / "panel_script.json")
    layout = load_json(root / "排版" / chapter / "layout.json")
    rects = panel_rects(layout)
    model = read_setting(root, "生图模型", "自定义")
    channel = read_setting(root, "生图渠道", "manual")
    caps = resolve_capabilities(model, channel) if resolve_capabilities else None
    style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    text_language = read_setting(root, "文字语言", "中文")
    render_stage = read_setting(root, "出图稿层", "完成稿")
    registry = load_reference_registry(root)
    finishing_plan = load_finishing_plan(root, chapter)
    finishing_map = finishing_by_panel(finishing_plan)
    jobs = []
    for panel in panel_script.get("panels", []):
        pid = panel.get("panel_id")
        rect = rects.get(pid, {})
        finish = finishing_map.get(str(pid), {})
        jobs.append(
            {
                "panel_id": pid,
                "status": "planned",
                "size": {"width": int(rect.get("w", 1440)), "height": int(rect.get("h", 900))},
                "prompt": build_prompt(panel, style, registry, panel_script, finish, render_stage),
                "negative_prompt": "文字，水印，logo，乱码字，字幕，播放按钮，搜索框，播放器控件，平台 UI，竖排标题，对白气泡，空白气泡，旁白框，文字框，额外手指，畸形手，手脚混淆，把脚画成手，脸部漂移，发际线漂移，眼型漂移，眼距漂移，发型漂移，年龄形态换脸，服装漂移，标志灵纹丢失，场景布局漂移，光位漂移，常驻道具丢失，looking at viewer，eye contact with camera，front-facing portrait，selfie，低清晰度，低成本彩漫感，Q版化，过度血腥细节",
                "continuity_contract": panel_continuity_contract(panel, panel_script),
                "traditional_finish_contract": finish,
                "references": [
                    item
                    for item in panel_references(root, panel, registry, caps)
                ],
                "reference_budget": caps.to_dict() if caps else {},
                "result_path": "",
                "source": channel,
            }
        )
    return {
        "schema_version": 1,
        "kind": "comic_panel_jobs",
        "chapter": chapter,
        "model": model,
        "channel": channel,
        "backend_capabilities": caps.to_dict() if caps else {},
        "text_language": text_language,
        "render_stage": render_stage,
        "finishing_plan": str(Path("出图") / chapter / "finishing" / "finishing_plan.json") if finishing_plan else "",
        "jobs": jobs,
    }


def preserve_ready_jobs(root: Path, chapter: str, jobs: dict) -> int:
    path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    if not path.is_file():
        return 0
    try:
        existing = load_json(path)
    except (OSError, json.JSONDecodeError):
        return 0
    old_by_id = {
        str(job.get("panel_id")): job
        for job in existing.get("jobs", [])
        if isinstance(job, dict) and job.get("panel_id")
    }
    preserved = 0
    for job in jobs.get("jobs", []):
        if not isinstance(job, dict):
            continue
        old = old_by_id.get(str(job.get("panel_id")))
        if not old or old.get("status") != "ready":
            continue
        result_path = str(old.get("result_path") or "")
        if not result_path:
            continue
        result = Path(result_path)
        if not result.is_absolute():
            result = root / result
        if not result.is_file():
            continue
        for key in PRESERVE_GENERATION_KEYS:
            if key in old:
                job[key] = old[key]
        preserved += 1
    return preserved


def write_reference_index(root: Path, chapter: str, jobs: dict) -> None:
    refs: dict[str, dict[str, object]] = {}
    for job in jobs.get("jobs", []):
        for ref in job.get("references", []):
            rid = ref.get("id")
            if rid:
                item = refs.setdefault(rid, {"count": 0, "path": ""})
                item["count"] = int(item.get("count") or 0) + 1
                if ref.get("path"):
                    item["path"] = ref.get("path")
    lines = [
        f"# 共享参考任务索引 — {chapter}",
        "",
        "正式逐格出图前，先补齐这些角色、场景、道具或特效参考。",
        "",
        "| ref_id | 出现次数 | 状态 | 建议 |",
        "|---|---:|---|---|",
    ]
    for rid, item in sorted(refs.items()):
        count = int(item.get("count") or 0)
        path = str(item.get("path") or "")
        if path:
            lines.append(f"| {rid} | {count} | ✅ | `{path}` |")
        else:
            lines.append(f"| {rid} | {count} | ⬜ | 生成或放入 `出图/共享/图片/` 后回填 panel_jobs.json |")
    if not refs:
        lines.append("| （无） | 0 | - | 当前脚本未声明 references |")
    path = root / "出图" / "共享" / "prompt" / "00_索引.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_progress(root: Path, chapter: str, stage: str, value: str) -> None:
    path = root / "_进度.md"
    if not path.is_file():
        return
    lines = path.read_text(encoding="utf-8").splitlines()
    headers: list[str] = []
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
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画逐格出图任务包")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--no-progress", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    jobs = build_jobs(root, args.chapter)
    preserved = preserve_ready_jobs(root, args.chapter, jobs)
    out_path = root / "出图" / args.chapter / "prompt" / "panel_jobs.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_reference_index(root, args.chapter, jobs)
    if not args.no_progress:
        update_progress(root, args.chapter, "出图包", "✅")
    suffix = f" preserved_ready={preserved}" if preserved else ""
    print(f"[ok] {out_path}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
