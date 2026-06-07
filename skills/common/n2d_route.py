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
    # 素材清单/字幕中/字幕英 也是阶段2·分镜设计(finalize_storyboard)的产物，归 n2d-script
    # 路由（与 n2d-progress/SKILL.md 路由表一致），否则它们未完成时会落出空前沿「」。
    (["分镜设计", "素材清单", "字幕中", "字幕英"], "阶段2·分镜设计", "n2d-script", "/n2d-script {root} {ep}  (配音后定稿)"),
    (["出图prompt", "出图"], "出图", "n2d-image", "/n2d-image {root} {ep}"),
    (["视频prompt", "视频"], "图生视频", "n2d-video", "/n2d-video {root} {ep}"),
    (["成片"], "合成成片", "n2d-compose", "/n2d-compose {root} {ep}"),
]

META_COLS = {"集", "字数", "序号", "#"}

# 集号兼容 ASCII / 全角数字 / 中文数字（CLAUDE.md 记载 export.py 已为同类问题踩过坑）
_FULLWIDTH = {ord("０") + i: ord("0") + i for i in range(10)}
_CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_EP_TOKEN = r"[\d０-９一二三四五六七八九十百零〇两]+"


def _cn_to_int(s: str) -> Optional[int]:
    """把 '12'/'１２'/'十二'/'二十' 解析成 int；解析不出返回 None。"""
    s = s.translate(_FULLWIDTH).strip()
    if s.isdigit():
        return int(s)
    if not s:
        return None
    total = section = 0
    for ch in s:
        if ch in ("十", "百"):
            unit = 10 if ch == "十" else 100
            section = (section or 1) * unit
            total += section
            section = 0
        elif ch in _CN_DIGIT:
            section = _CN_DIGIT[ch]
        else:
            return None
    return total + section


def cell_state(v: str) -> str:
    v = (v or "").strip()
    if v == "✅":
        return "done"
    # 显式标记"本集不适用"（如 zh-only 项目的 字幕英）→ na：算已满足，不挡完成、不进缺口
    if v in ("—", "-", "N/A", "n/a", "无", "✖", "✗", "×"):
        return "na"
    if v in ("⬜", ""):
        return "todo"
    m = re.match(r"(\d+)\s*/\s*(\d+)", v)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if b > 0 and a >= b:
            return "done"
        return "partial" if a > 0 else "todo"
    return "todo"


def is_done(v: str) -> bool:
    # na（不适用）视为已满足：完成度统计与路由都不该卡在被标记跳过的列上
    return cell_state(v) in ("done", "na")


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
        if header is None and re.match(r"^\|\s*集\s*\|", ln):
            header = [c.strip() for c in ln.split("|")[1:-1]]
            continue
        if header and re.match(r"^\|\s*第\s*" + _EP_TOKEN + r"\s*集\s*\|", ln):
            cells = [c.strip() for c in ln.split("|")[1:len(header) + 1]]
            row = dict(zip(header, cells))
            row["_ep"] = row.get("集") or cells[0]
            m = re.search(r"第\s*(" + _EP_TOKEN + r")\s*集", row["_ep"])
            num = _cn_to_int(m.group(1)) if m else None
            row["_num"] = num if num is not None else 10**9
            rows.append(row)
    if header is None:
        raise ValueError("未找到表头（| 集 | …）")
    return header, rows


def flow_columns(header: Iterable[str]) -> List[str]:
    return [h for h in header if h not in META_COLS and h != "raw"]


def manifest_path(root: str, ep: str) -> Optional[str]:
    """时长清单.json 可能落在 合成/<ep>/配音/（配音先行）或 出视频/<ep>/配音/
    （先出视频后配音模式）——两处都探，返回第一个存在的。"""
    for base in ("合成", "出视频"):
        p = os.path.join(root, base, ep, "配音", "时长清单.json")
        if os.path.isfile(p):
            return p
    return None


def voice_is_placeholder(root: str, ep: str) -> Optional[bool]:
    p = manifest_path(root, ep)
    if not p:
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

