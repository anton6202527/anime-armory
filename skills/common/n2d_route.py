#!/usr/bin/env python3
"""Shared progress-table routing for the novel2drama/n2d pipeline."""
from __future__ import annotations

import json
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from n2d_settings import is_video_first
except ImportError:  # when imported as package-ish via sys.path parent
    from .n2d_settings import is_video_first


STAGES = [
    (["剧本改编", "bgm", "封面"], "阶段1·剧本改编", "n2d-script", "/n2d-script {root} {ep}"),
    (["配音"], "角色配音", "n2d-voice", "/n2d-voice {root} {ep}"),
    (["分镜设计"], "阶段2·分镜设计", "n2d-script", "/n2d-script {root} {ep}  (配音后定稿)"),
    (["出图prompt", "出图"], "出图", "n2d-image", "/n2d-image {root} {ep}"),
    (["视频prompt", "视频"], "图生视频", "n2d-video", "/n2d-video {root} {ep}"),
    (["成片"], "合成成片", "n2d-compose", "/n2d-compose {root} {ep}"),
]

META_COLS = {"集", "字数", "序号", "#"}


def cell_state(v: str) -> str:
    v = (v or "").strip()
    if v == "✅":
        return "done"
    if v in ("⬜", "", "—", "-"):
        return "todo"
    m = re.match(r"(\d+)\s*/\s*(\d+)", v)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if b > 0 and a >= b:
            return "done"
        return "partial" if a > 0 else "todo"
    return "todo"


def is_done(v: str) -> bool:
    return cell_state(v) == "done"


def is_started(v: str) -> bool:
    return cell_state(v) in ("done", "partial")


def progress_path(root: str) -> str:
    root = root.rstrip("/")
    primary = os.path.join(root, "_进度.md")
    if os.path.exists(primary):
        return primary
    return os.path.join(root, "common", "_进度.md")


def parse_progress(root: str) -> Tuple[List[str], List[Dict[str, str]]]:
    p = progress_path(root)
    if not os.path.exists(p):
        raise FileNotFoundError(p)
    lines = open(p, encoding="utf-8").read().splitlines()
    header: Optional[List[str]] = None
    rows: List[Dict[str, str]] = []
    for ln in lines:
        if ln.startswith("| 集 |"):
            header = [c.strip() for c in ln.split("|")[1:-1]]
            continue
        if header and re.match(r"^\|\s*第\d+集\s*\|", ln):
            cells = [c.strip() for c in ln.split("|")[1:len(header) + 1]]
            row = dict(zip(header, cells))
            row["_ep"] = row.get("集") or cells[0]
            n = re.search(r"\d+", row["_ep"])
            row["_num"] = int(n.group()) if n else 10**9
            rows.append(row)
    if header is None:
        raise ValueError("未找到表头（| 集 | …）")
    return header, rows


def flow_columns(header: Iterable[str]) -> List[str]:
    return [h for h in header if h not in META_COLS and h != "raw"]


def voice_is_placeholder(root: str, ep: str) -> Optional[bool]:
    p = os.path.join(root, "合成", ep, "配音", "时长清单.json")
    if not os.path.isfile(p):
        return None
    try:
        data = json.load(open(p, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if isinstance(data, list):
        return any(isinstance(x, dict) and x.get("占位") for x in data)
    return None


def stage_of(root: str, row: Dict[str, str], header: List[str]) -> Dict[str, Optional[str]]:
    """Return the next stage for a row, with production-mode adjustments."""
    ep = row.get("_ep") or row.get("集") or ""
    for cols, label, skill, cmd in STAGES:
        for col in cols:
            if col in header and not is_done(row.get(col, "")):
                note = ""
                if is_video_first(root) and skill == "n2d-compose" and voice_is_placeholder(root, ep):
                    return {
                        "ep": ep,
                        "col": col,
                        "label": "补真实配音",
                        "skill": "n2d-voice",
                        "cmd": "/n2d-voice {root} {ep}  (补真音；之后 fit_voice_to_clips + n2d-compose)",
                        "note": "先出视频后配音模式：当前配音仍是占位，合成前必须先补真实配音。",
                    }
                return {"ep": ep, "col": col, "label": label, "skill": skill, "cmd": cmd, "note": note}
    return {"ep": ep, "col": None, "label": "✅已成片", "skill": None, "cmd": None, "note": ""}


def format_route(root: str, route: Dict[str, Optional[str]]) -> str:
    ep = route.get("ep") or ""
    label = route.get("label") or ""
    cmd = route.get("cmd")
    return f"{ep}: {label}" if not cmd else f"{ep}: {label}  → {cmd.format(root=root, ep=ep)}"


def summarize(root: str) -> Dict[str, object]:
    header, rows = parse_progress(root)
    routes = [stage_of(root, r, header) for r in sorted(rows, key=lambda x: int(x.get("_num", 10**9)))]
    first = next((r for r in routes if r.get("cmd")), None)
    done = sum(1 for r in routes if not r.get("cmd"))
    bottleneck: Dict[str, int] = {}
    for r in routes:
        if r.get("cmd"):
            label = str(r["label"])
            bottleneck[label] = bottleneck.get(label, 0) + 1
    return {"header": header, "rows": rows, "routes": routes, "first": first, "done": done, "bottleneck": bottleneck}

