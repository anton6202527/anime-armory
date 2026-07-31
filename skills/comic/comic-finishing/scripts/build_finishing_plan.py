#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a manga finishing plan for ink, tone, effects, and drawn SFX."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


class FinishingError(ValueError):
    """Raised when finishing would consume missing, stale, or incomplete inputs."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def approval_subject(value: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(value)
    payload.pop("approval", None)
    payload.pop("validation", None)
    payload.pop("workflow_status", None)
    return payload


def approval_subject_sha256(value: dict[str, Any]) -> str:
    return sha256_json(approval_subject(value))


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


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


def compact_text(value: Any, *, max_len: int = 220) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value
    elif isinstance(value, list):
        text = "；".join(compact_text(item, max_len=max_len) for item in value)
    elif isinstance(value, dict):
        text = "；".join(f"{key}:{compact_text(item, max_len=max_len)}" for key, item in value.items())
    else:
        text = str(value)
    text = re.sub(r"\s+", " ", text).strip("； ")
    return text[: max_len - 1].rstrip() + "…" if len(text) > max_len else text


def rects_by_panel(layout: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rects: dict[str, dict[str, Any]] = {}
    for segment in layout.get("segments") or []:
        for panel in segment.get("panels") or []:
            pid = str(panel.get("panel_id") or "")
            if pid:
                rects[pid] = panel
    return rects


def name_panels_by_id(name_board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for page in name_board.get("pages") or []:
        for panel in page.get("panels") or []:
            pid = str(panel.get("panel_id") or "")
            if pid:
                out[pid] = panel
    return out


def weight_for(panel: dict[str, Any], name_panel: dict[str, Any], rect: dict[str, Any]) -> str:
    raw = str(panel.get("layout_weight") or name_panel.get("layout_weight") or "").lower()
    if raw in {"heavy", "medium", "compact"}:
        return raw
    # 用格高分级（宽度无关）：条漫 layout 的格高区间约 560..1500，
    # heavy 基准 960、默认 760、compact 620/680（见 comic-layout panel_height）。
    height = int(rect.get("h") or 0)
    if height >= 920:
        return "heavy"
    if 0 < height <= 700:
        return "compact"
    fn = str(panel.get("story_function") or "").lower()
    if any(token in fn for token in ("hook", "cliff", "reveal", "peak", "action", "冲击", "揭示", "高潮")):
        return "heavy"
    return "medium"


def stage_sequence(render_stage: str) -> list[str]:
    base = ["rough", "pencil", "lineart"]
    if "草稿" in render_stage or "name" in render_stage.lower():
        return ["rough_name"]
    if "铅笔" in render_stage:
        return ["rough", "pencil"]
    if "清线" in render_stage:
        return base
    if "墨线" in render_stage or "黑场" in render_stage:
        return base + ["ink_blacks"]
    if "网点" in render_stage:
        return base + ["ink_blacks", "tone", "effects"]
    return base + ["ink_blacks", "tone_or_color", "effects", "lettering_sfx"]


def default_ink_plan(panel: dict[str, Any], weight: str) -> str:
    explicit = compact_text(panel.get("ink_plan"))
    if explicit:
        return explicit
    if weight == "heavy":
        return "clear silhouette, stronger outer contour, expressive line weight; keep face, hands, feet, and key props readable"
    if weight == "compact":
        return "economical clean lineart, avoid noisy crosshatching, preserve expression and gesture"
    return "stable contour lineart with modest line-weight variation and clean readable anatomy"


def default_black_plan(panel: dict[str, Any], weight: str) -> str:
    explicit = compact_text(panel.get("black_fill_plan") or panel.get("black_plan"))
    if explicit:
        return explicit
    fn = str(panel.get("story_function") or "").lower()
    if weight == "heavy" or any(token in fn for token in ("reveal", "cliff", "peak")):
        return "assign solid blacks behind or around the focal subject to create a strong value read; avoid hiding identity features"
    return "use small black accents for depth and material separation; keep safe text areas low detail"


def default_tone_plan(panel: dict[str, Any], style: str, tone_strategy: str, weight: str) -> str:
    explicit = compact_text(panel.get("tone_plan"))
    if explicit:
        return explicit
    if "关闭" in tone_strategy:
        return "tone disabled by project setting; preserve value separation through clean line and local contrast"
    if any(token in style for token in ("黑白", "网点", "日漫", "青年", "少女")):
        density = "richer background and mood tones" if weight == "heavy" else "light material tones"
        return f"{tone_strategy}: screentone plan with {density}; skin light, clothing mid/dark, background depth separated"
    return f"{tone_strategy}: keep a grayscale/value hierarchy under color; focal subject high contrast, background lower contrast"


def default_effects_plan(panel: dict[str, Any], effects_strategy: str, weight: str) -> str:
    explicit = compact_text(panel.get("effects_plan") or panel.get("effects_hint"))
    if explicit:
        return explicit
    if "关闭" in effects_strategy:
        return "effects disabled by project setting"
    fn = str(panel.get("story_function") or "").lower()
    sfx = compact_text(panel.get("sfx"))
    if sfx or "action" in fn or "peak" in fn or "动作" in fn:
        return f"{effects_strategy}: speed/action lines following motion path, impact flash near hit point, do not cover face/hands/key props"
    if "reveal" in fn or "hook" in fn or "揭示" in fn:
        return f"{effects_strategy}: focus lines or black-field contrast toward reveal object, keep reader eye-flow unambiguous"
    if weight == "compact":
        return f"{effects_strategy}: minimal symbols only, avoid clutter"
    return f"{effects_strategy}: subtle focus or atmosphere lines only if they improve reading"


def lettering_sfx_plan(panel: dict[str, Any]) -> dict[str, str]:
    sfx = compact_text(panel.get("sfx_target") or panel.get("target_sfx") or panel.get("sfx"))
    if not sfx:
        return {"mode": "none", "integration": "no drawn SFX", "shape": ""}
    return {
        "mode": "drawn_sfx",
        "text_hint": sfx,
        "integration": "integrate with action path or impact zone; do not cover face, hands, key props, or final dialogue slots",
        "shape": "match sound quality: jagged for impact, stretched for speed, soft for ambience",
    }


def delivery_mode_for(root: Path, style: str, render_stage: str) -> str:
    explicit = read_setting(root, "交付模式", "").strip()
    if explicit:
        return explicit
    if any(token in style + render_stage for token in ("黑白", "网点", "墨线")):
        return "monochrome_print"
    if "灰阶" in style + render_stage:
        return "grayscale_digital"
    return "color_digital"


def layer_contract(render_stage: str, delivery_mode: str) -> dict[str, Any]:
    sequence = stage_sequence(render_stage)
    return {
        "delivery_mode": delivery_mode,
        "ordered_layers": [
            {"layer_id": name.upper(), "role": name, "required": True, "blend": "normal"}
            for name in sequence
        ],
        "text_separation": "dialogue/narration stay in post-lettering layers; only contracted drawn SFX may enter art layers",
        "flatten_policy": "keep logical layer manifest even when a backend returns one flattened raster",
    }


def panel_layer_items(panel: dict[str, Any], render_stage: str) -> list[dict[str, Any]]:
    pid = str(panel.get("panel_id") or "")
    return [
        {
            "item_id": f"{pid}_{layer.upper()}",
            "layer": layer,
            "role": "art" if layer not in {"effects", "lettering_sfx"} else layer,
            "mask_scope": "panel",
            "no_bake_dialogue_or_narration": True,
        }
        for layer in stage_sequence(render_stage)
    ]


def tone_items(panel: dict[str, Any], tone_plan: str, delivery_mode: str) -> list[dict[str, Any]]:
    return [
        {
            "item_id": f"{panel.get('panel_id')}_TONE_01",
            "role": "material_and_depth" if delivery_mode != "color_digital" else "grayscale_underpainting",
            "strategy": tone_plan,
            "scope": "subject/background separation",
        }
    ]


def sfx_items(panel: dict[str, Any], plan: dict[str, str]) -> list[dict[str, Any]]:
    raw = panel.get("sfx_target") or panel.get("target_sfx") or panel.get("sfx") or []
    if isinstance(raw, str):
        raw = [raw]
    if plan.get("mode") == "none":
        return []
    pid = str(panel.get("panel_id") or "")
    return [
        {
            "item_id": f"{pid}_SFX_{index:02d}",
            "content_ref": f"panel:{pid}.sfx:{index}",
            "text_hint": compact_text(item, max_len=80),
            "delivery": plan.get("mode"),
            "layer": "lettering_sfx",
            "integration": plan.get("integration", ""),
            "shape": plan.get("shape", ""),
        }
        for index, item in enumerate(raw, 1)
        if compact_text(item)
    ]


def page_value_plans(layout: dict[str, Any], panels_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for segment in layout.get("segments") or []:
        ids = [str(item.get("panel_id") or "") for item in segment.get("panels") or [] if isinstance(item, dict)]
        heavy = [pid for pid in ids if (panels_by_id.get(pid) or {}).get("layout_weight") == "heavy"]
        plans.append(
            {
                "page_or_segment_id": str(segment.get("segment_id") or ""),
                "panel_ids": ids,
                "focal_panel_ids": heavy or ids[:1],
                "value_rhythm": "alternate focal contrast and recovery beats; preserve a readable three-value hierarchy",
                "check": "thumbnail test at page/segment scale before export",
            }
        )
    return plans


def input_contract(root: Path, chapter: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    panel_path = root / "脚本" / chapter / "panel_script.json"
    name_path = root / "排版" / chapter / "name_board.json"
    layout_path = root / "排版" / chapter / "layout.json"
    missing = [str(path) for path in (panel_path, name_path, layout_path) if not path.is_file()]
    if missing:
        raise FinishingError("缺少输入：" + "、".join(missing))
    panel_script = load_json(panel_path)
    name_board = load_json(name_path)
    layout = load_json(layout_path)
    if not all(isinstance(item, dict) for item in (panel_script, name_board, layout)):
        raise FinishingError("panel_script/name_board/layout 必须是 JSON 对象")
    panels = [item for item in panel_script.get("panels") or [] if isinstance(item, dict) and item.get("panel_id")]
    if not panels:
        raise FinishingError("panel_script.panels 为空")
    ids = [str(item.get("panel_id")) for item in panels]
    if len(ids) != len(set(ids)):
        raise FinishingError("panel_script.panel_id 必须唯一")
    name_ids = [str(item.get("panel_id") or "") for page in name_board.get("pages") or [] for item in page.get("panels") or [] if isinstance(item, dict)]
    layout_ids = [str(item.get("panel_id") or "") for segment in layout.get("segments") or [] for item in segment.get("panels") or [] if isinstance(item, dict)]
    if name_ids != ids or layout_ids != ids:
        raise FinishingError("panel_script/name_board/layout 的 panel 覆盖或顺序不一致")
    if name_board.get("schema_version") != 2 or name_board.get("workflow_status") != "approved":
        raise FinishingError("name_board 必须是已签收 schema v2")
    name_approval = name_board.get("approval") if isinstance(name_board.get("approval"), dict) else {}
    if name_approval.get("status") != "approved" or name_approval.get("subject_sha256") != approval_subject_sha256(name_board):
        raise FinishingError("name_board approval SHA 不匹配")
    if not str(name_approval.get("reviewed_by") or "").strip():
        raise FinishingError("name_board approval 缺 reviewed_by")
    if not str(name_approval.get("reviewed_at") or "").strip():
        raise FinishingError("name_board approval 缺 reviewed_at")
    if layout.get("schema_version") != 2 or layout.get("workflow_status") != "approved":
        raise FinishingError("layout 必须是已校验并签收的 schema v2")
    layout_approval = layout.get("approval") if isinstance(layout.get("approval"), dict) else {}
    if layout_approval.get("status") != "approved" or layout_approval.get("subject_sha256") != approval_subject_sha256(layout):
        raise FinishingError("layout approval SHA 不匹配")
    if not str(layout_approval.get("reviewed_by") or "").strip():
        raise FinishingError("layout approval 缺 reviewed_by")
    if not str(layout_approval.get("reviewed_at") or "").strip():
        raise FinishingError("layout approval 缺 reviewed_at")
    name_upstream = name_board.get("upstream_receipt") or {}
    if name_upstream.get("panel_script_sha256") != sha256_file(panel_path) or name_upstream.get("settings_sha256") != sha256_file(root / "_设置.md"):
        raise FinishingError("name_board 上游 SHA 已过期")
    layout_upstream = layout.get("upstream_receipt") or {}
    current = {
        "panel_script_sha256": sha256_file(panel_path),
        "name_board_sha256": sha256_file(name_path),
        "settings_sha256": sha256_file(root / "_设置.md"),
    }
    if any(layout_upstream.get(key) != value for key, value in current.items()):
        raise FinishingError("layout 上游 SHA 已过期")
    return panel_script, name_board, layout


def build_finishing_plan(root: Path, chapter: str) -> dict[str, Any]:
    panel_script, name_board, layout = input_contract(root, chapter)
    rects = rects_by_panel(layout)
    name_map = name_panels_by_id(name_board)
    style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    render_stage = read_setting(root, "出图稿层", "完成稿")
    tone_strategy = read_setting(root, "网点策略", "风格驱动")
    effects_strategy = read_setting(root, "效果线策略", "剧情驱动")
    delivery_mode = delivery_mode_for(root, style, render_stage)
    panels = []
    for panel in panel_script.get("panels") or []:
        if not isinstance(panel, dict) or not panel.get("panel_id"):
            continue
        pid = str(panel.get("panel_id"))
        rect = rects.get(pid, {})
        name_panel = name_map.get(pid, {})
        weight = weight_for(panel, name_panel, rect)
        tone_plan = default_tone_plan(panel, style, tone_strategy, weight)
        sfx_plan = lettering_sfx_plan(panel)
        panels.append(
            {
                "panel_id": pid,
                "layout_weight": weight,
                "art_stage_sequence": stage_sequence(render_stage),
                "layer_items": panel_layer_items(panel, render_stage),
                "ink_plan": default_ink_plan(panel, weight),
                "black_fill_plan": default_black_plan(panel, weight),
                "tone_plan": tone_plan,
                "tone_items": tone_items(panel, tone_plan, delivery_mode),
                "value_plan": compact_text(panel.get("value_plan")) or "three-value read: focal subject, acting silhouette, background depth must remain separable in grayscale",
                "effects_plan": default_effects_plan(panel, effects_strategy, weight),
                "lettering_sfx_plan": sfx_plan,
                "sfx_items": sfx_items(panel, sfx_plan),
                "no_bake_text_contract": "dialogue and narration stay out of raw images; no blank bubbles/caption boxes/UI text/watermark/garbled text; drawn SFX only when listed in lettering_sfx_plan",
            }
        )
    if not panels:
        raise FinishingError("收尾计划 panels 为空")
    panels_by_id = {str(item.get("panel_id")): item for item in panels}
    plan = {
        "schema_version": 2,
        "kind": "comic_finishing_plan",
        "workflow_status": "validated",
        "chapter": chapter,
        "render_stage": render_stage,
        "style": style,
        "delivery_mode": delivery_mode,
        "layer_contract": layer_contract(render_stage, delivery_mode),
        "tone_strategy": tone_strategy,
        "effects_strategy": effects_strategy,
        "page_value_plans": page_value_plans(layout, panels_by_id),
        "upstream_receipt": {
            "panel_script": str(Path("脚本") / chapter / "panel_script.json"),
            "panel_script_sha256": sha256_file(root / "脚本" / chapter / "panel_script.json"),
            "name_board": str(Path("排版") / chapter / "name_board.json"),
            "name_board_sha256": sha256_file(root / "排版" / chapter / "name_board.json"),
            "layout": str(Path("排版") / chapter / "layout.json"),
            "layout_sha256": sha256_file(root / "排版" / chapter / "layout.json"),
            "settings": "_设置.md",
            "settings_sha256": sha256_file(root / "_设置.md"),
            "name_approval_subject_sha256": ((name_board.get("approval") or {}).get("subject_sha256") if isinstance(name_board.get("approval"), dict) else ""),
            "layout_approval_subject_sha256": ((layout.get("approval") or {}).get("subject_sha256") if isinstance(layout.get("approval"), dict) else ""),
        },
        "panels": panels,
    }
    errors = validate_finishing_plan(plan, panel_script, layout)
    plan["validation"] = {"status": "pass" if not errors else "fail", "errors": errors}
    if errors:
        raise FinishingError("finishing_plan 校验失败：" + "；".join(errors))
    return plan


def validate_finishing_plan(plan: dict[str, Any], panel_script: dict[str, Any], layout: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if plan.get("schema_version") != 2 or plan.get("kind") != "comic_finishing_plan":
        errors.append("需要 comic_finishing_plan schema v2")
    if plan.get("workflow_status") != "validated":
        errors.append("workflow_status 必须为 validated")
    expected = [str(item.get("panel_id")) for item in panel_script.get("panels") or [] if isinstance(item, dict) and item.get("panel_id")]
    actual = [str(item.get("panel_id") or "") for item in plan.get("panels") or [] if isinstance(item, dict)]
    if not actual or actual != expected or len(actual) != len(set(actual)):
        errors.append("finishing panels 必须唯一并完整覆盖 panel_script 顺序")
    layout_ids = [str(item.get("panel_id") or "") for segment in layout.get("segments") or [] for item in segment.get("panels") or [] if isinstance(item, dict)]
    if actual != layout_ids:
        errors.append("finishing panels 必须完整覆盖 layout")
    required = ("art_stage_sequence", "layer_items", "ink_plan", "black_fill_plan", "tone_plan", "tone_items", "value_plan", "effects_plan", "lettering_sfx_plan", "sfx_items")
    for panel in plan.get("panels") or []:
        missing = [key for key in required if key not in panel or panel.get(key) in (None, "")]
        missing.extend(key for key in ("art_stage_sequence", "layer_items", "tone_items") if not panel.get(key) and key not in missing)
        if missing:
            errors.append(f"{panel.get('panel_id')}: 缺 {','.join(missing)}")
    page_ids = [str(item.get("segment_id") or "") for item in layout.get("segments") or []]
    value_ids = [str(item.get("page_or_segment_id") or "") for item in plan.get("page_value_plans") or []]
    if value_ids != page_ids:
        errors.append("page_value_plans 必须覆盖所有 page/segment")
    if not plan.get("delivery_mode") or not plan.get("layer_contract"):
        errors.append("缺 delivery_mode/layer_contract")
    return errors


def stale_errors(root: Path, chapter: str, plan: dict[str, Any]) -> list[str]:
    receipt = plan.get("upstream_receipt") if isinstance(plan.get("upstream_receipt"), dict) else {}
    current = {
        "panel_script_sha256": sha256_file(root / "脚本" / chapter / "panel_script.json"),
        "name_board_sha256": sha256_file(root / "排版" / chapter / "name_board.json"),
        "layout_sha256": sha256_file(root / "排版" / chapter / "layout.json"),
        "settings_sha256": sha256_file(root / "_设置.md"),
    }
    return [f"finishing upstream {key} 已过期" for key, value in current.items() if receipt.get(key) != value]


def write_markdown(root: Path, chapter: str, plan: dict[str, Any]) -> Path:
    lines = [
        f"# 原稿收尾计划 — {chapter}",
        "",
        f"- 稿层：{plan.get('render_stage')}",
        f"- 风格：{plan.get('style')}",
        f"- 交付模式：{plan.get('delivery_mode')}",
        f"- 上游校验：{(plan.get('validation') or {}).get('status')}",
        f"- 网点策略：{plan.get('tone_strategy')}",
        f"- 效果线策略：{plan.get('effects_strategy')}",
        "",
        "| panel | 稿层 | 墨线/黑场 | 网点/价值 | 效果线/SFX |",
        "|---|---|---|---|---|",
    ]
    for panel in plan.get("panels") or []:
        lines.append(
            "| {panel_id} | {stage} | {ink} / {black} | {tone} / {value} | {effects} / {sfx} |".format(
                panel_id=panel.get("panel_id", ""),
                stage=",".join(map(str, panel.get("art_stage_sequence") or [])),
                ink=compact_text(panel.get("ink_plan"), max_len=70).replace("|", "/"),
                black=compact_text(panel.get("black_fill_plan"), max_len=70).replace("|", "/"),
                tone=compact_text(panel.get("tone_plan"), max_len=70).replace("|", "/"),
                value=compact_text(panel.get("value_plan"), max_len=70).replace("|", "/"),
                effects=compact_text(panel.get("effects_plan"), max_len=70).replace("|", "/"),
                sfx=compact_text(panel.get("lettering_sfx_plan"), max_len=70).replace("|", "/"),
            )
        )
    out = root / "出图" / chapter / "finishing" / "finishing_plan.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def update_progress(root: Path, chapter: str, value: str) -> None:
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
            elif headers and len(cells) >= len(headers) and cells[0] == chapter:
                for stage in ("原稿收尾", "传统收尾"):
                    if stage in headers:
                        cells[headers.index(stage)] = value
                        line = "| " + " | ".join(cells) + " |"
                        break
        out.append(line)
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成漫画传统原稿收尾计划")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--check", action="store_true", help="只读检查现有 plan 的覆盖与上游 SHA")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    out_path = root / "出图" / args.chapter / "finishing" / "finishing_plan.json"
    try:
        if args.check:
            if not out_path.is_file():
                raise FinishingError(f"缺少现有计划：{out_path}")
            panel_script, _name_board, layout = input_contract(root, args.chapter)
            plan = load_json(out_path)
            errors = validate_finishing_plan(plan, panel_script, layout) + stale_errors(root, args.chapter, plan)
            if errors:
                for error in errors:
                    print(f"[block] {error}")
                return 2
            print(f"[ok] validated/current {out_path}")
            return 0
        plan = build_finishing_plan(root, args.chapter)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        md_path = write_markdown(root, args.chapter, plan)
        if not args.no_progress:
            update_progress(root, args.chapter, "✅")
        print(f"[ok] validated {out_path}")
        print(f"[ok] {md_path}")
        return 0
    except (ValueError, OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        print(f"[block] {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
