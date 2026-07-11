#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a manga finishing plan for ink, tone, effects, and drawn SFX."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


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


def build_finishing_plan(root: Path, chapter: str) -> dict[str, Any]:
    panel_script = load_json(root / "脚本" / chapter / "panel_script.json", {})
    layout = load_json(root / "排版" / chapter / "layout.json", {})
    name_board = load_json(root / "排版" / chapter / "name_board.json", {})
    rects = rects_by_panel(layout if isinstance(layout, dict) else {})
    name_map = name_panels_by_id(name_board if isinstance(name_board, dict) else {})
    style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    render_stage = read_setting(root, "出图稿层", "完成稿")
    tone_strategy = read_setting(root, "网点策略", "风格驱动")
    effects_strategy = read_setting(root, "效果线策略", "剧情驱动")
    panels = []
    for panel in panel_script.get("panels") or []:
        if not isinstance(panel, dict) or not panel.get("panel_id"):
            continue
        pid = str(panel.get("panel_id"))
        rect = rects.get(pid, {})
        name_panel = name_map.get(pid, {})
        weight = weight_for(panel, name_panel, rect)
        panels.append(
            {
                "panel_id": pid,
                "layout_weight": weight,
                "art_stage_sequence": stage_sequence(render_stage),
                "ink_plan": default_ink_plan(panel, weight),
                "black_fill_plan": default_black_plan(panel, weight),
                "tone_plan": default_tone_plan(panel, style, tone_strategy, weight),
                "value_plan": compact_text(panel.get("value_plan")) or "three-value read: focal subject, acting silhouette, background depth must remain separable in grayscale",
                "effects_plan": default_effects_plan(panel, effects_strategy, weight),
                "lettering_sfx_plan": lettering_sfx_plan(panel),
                "no_bake_text_contract": "dialogue and narration stay out of raw images; no blank bubbles/caption boxes/UI text/watermark/garbled text; drawn SFX only when listed in lettering_sfx_plan",
            }
        )
    return {
        "schema_version": 1,
        "kind": "comic_finishing_plan",
        "chapter": chapter,
        "render_stage": render_stage,
        "style": style,
        "tone_strategy": tone_strategy,
        "effects_strategy": effects_strategy,
        "panels": panels,
    }


def write_markdown(root: Path, chapter: str, plan: dict[str, Any]) -> Path:
    lines = [
        f"# 原稿收尾计划 — {chapter}",
        "",
        f"- 稿层：{plan.get('render_stage')}",
        f"- 风格：{plan.get('style')}",
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
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    plan = build_finishing_plan(root, args.chapter)
    out_path = root / "出图" / args.chapter / "finishing" / "finishing_plan.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path = write_markdown(root, args.chapter, plan)
    if not args.no_progress:
        update_progress(root, args.chapter, "✅")
    print(f"[ok] {out_path}")
    print(f"[ok] {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
