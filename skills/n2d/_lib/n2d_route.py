#!/usr/bin/env python3
"""Shared progress-table routing for the n2d pipeline."""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Dict, Iterable, List, Optional, Tuple

try:
    from n2d_contract import (
        PROGRESS_DONE,
        PROGRESS_ROUGH_PREFIX,
        PROGRESS_TODO,
        VOICE_KEY_FIELD,
        VOICE_KEY_PLACEHOLDER_SUFFIX,
        routing_stages,
        stage_requires_for_mode,
        stage_specs,
    )
    from n2d_settings import is_native_av, is_video_first
except ImportError:  # when imported as package-ish via sys.path parent
    from .n2d_contract import (
        PROGRESS_DONE,
        PROGRESS_ROUGH_PREFIX,
        PROGRESS_TODO,
        VOICE_KEY_FIELD,
        VOICE_KEY_PLACEHOLDER_SUFFIX,
        routing_stages,
        stage_requires_for_mode,
        stage_specs,
    )
    from .n2d_settings import is_native_av, is_video_first


# Single source of truth for routing stage order.  The tuple shape is kept for
# backward compatibility with progress.py and n2d-progress/scan.py.
STAGES = routing_stages()

# 路由用的阶段规格（只取参与路由的），带 requires/owner/command/progress_columns。
_ROUTING_SPECS = [s for s in stage_specs() if s.get("routes")]

META_COLS = {"集", "字数", "序号", "#"}

# 集号兼容 ASCII / 全角数字 / 中文数字（旧导出脚本曾踩过同类坑）
_FULLWIDTH = {ord("０") + i: ord("0") + i for i in range(10)}
_CN_DIGIT = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
             "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_EP_TOKEN = r"[\d０-９一二三四五六七八九十百零〇两]+"
EP_ROW_RE = re.compile(r"^\|\s*第\s*" + _EP_TOKEN + r"\s*集\s*\|")


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


def episode_number(value: str) -> Optional[int]:
    """从 '第12集'/'第１２集'/'第十二集'/'十二' 中取集号；解析不出返回 None。"""
    text = (value or "").strip()
    m = re.search(r"第\s*(" + _EP_TOKEN + r")\s*集", text)
    token = m.group(1) if m else re.sub(r"^\s*第|\s*集\s*$", "", text).strip()
    if not token or not re.fullmatch(_EP_TOKEN, token):
        return None
    return _cn_to_int(token)


def normalize_episode(value: str) -> str:
    """把可解析集号统一成 '第N集'，不可解析时返回去空白原值。"""
    n = episode_number(value)
    return f"第{n}集" if n is not None else (value or "").strip()


def is_rough(v: str) -> bool:
    v = (v or "").strip()
    return v.startswith(PROGRESS_ROUGH_PREFIX) or v.lower() in {"rough", "rough-timing", "rough_timing"}


def cell_state(v: str) -> str:
    v = (v or "").strip()
    if v == PROGRESS_DONE:
        return "done"
    if is_rough(v):
        return "rough"
    # 显式标记"本集不适用"（如 zh-only 项目的 字幕英）→ na：算已满足，不挡完成、不进缺口
    if v in ("—", "-", "N/A", "n/a", "无", "✖", "✗", "×"):
        return "na"
    if v in (PROGRESS_TODO, ""):
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
    return cell_state(v) in ("done", "partial", "rough")


def is_progress_satisfied(root: str, row: Dict[str, str], col: str) -> bool:
    """Mode-aware progress satisfaction for one column."""
    if is_native_av(root) and col == "配音":
        return True
    state = cell_state(row.get(col, ""))
    if col == "配音" and is_video_first(root) and state == "rough":
        return True
    return state in ("done", "na")


def is_flow_complete(root: str, row: Dict[str, str], flow: Iterable[str]) -> bool:
    """Mode-aware full-row completion used by progress scanners."""
    return all(is_progress_satisfied(root, row, c) for c in flow)


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
    content = open(p, encoding="utf-8").read()
    
    # Import markdown_parser lazily to avoid circular dependencies if any
    try:
        from markdown_parser import parse_markdown_table
    except ImportError:
        from .markdown_parser import parse_markdown_table
        
    try:
        header, raw_rows = parse_markdown_table(content, header_identifier="集")
    except ValueError as e:
        raise ValueError(str(e))
        
    rows: List[Dict[str, str]] = []
    for r in raw_rows:
        ep = r.get("集") or r.get("_pk", "")
        num = episode_number(ep)
        if num is not None:
            r["_ep"] = ep
            r["_num"] = num if num is not None else 10**9
            rows.append(r)
            
    return header, rows


def is_episode_row(line: str) -> bool:
    return bool(EP_ROW_RE.match(line))


def flow_columns(header: Iterable[str]) -> List[str]:
    return [h for h in header if h not in META_COLS and h != "raw"]


def manifest_path(root: str, ep: str) -> Optional[str]:
    """时长清单.json 一律落在 合成/<ep>/配音/（render_voice 与制作模式无关地写 合成/，
    见 2026 出视频↔合成分家）。出视频/<ep>/配音/ 为已废弃历史路径，保留防御性兜底探测
    （test_manifest_path_probes_both_bases 守护向后兼容）——两处都探，返回第一个存在的。"""
    for base in ("合成", "出视频"):
        p = os.path.join(root, base, ep, "配音", "时长清单.json")
        if os.path.isfile(p):
            return p
    return None


def _is_placeholder_voice_row(row: dict) -> bool:
    if row.get("占位"):
        return True
    voice_key = str(row.get(VOICE_KEY_FIELD) or row.get("voice_key") or "")
    # macOS say is an emergency/placeholder backend, never a registered timbre — any
    # say: voice_key is placeholder-grade regardless of marker separator (canonical
    # `say:<voice>_placeholder` and legacy `say:<voice>#placeholder` both count).
    if voice_key.startswith("say:") or voice_key.endswith(VOICE_KEY_PLACEHOLDER_SUFFIX) or "#placeholder" in voice_key:
        return True
    voice_id = str(row.get("voice_id") or "")
    return voice_id.startswith("say:")


def placeholder_indices(manifest) -> List[int]:
    """从已加载的时长清单(list) 取占位句下标（优先 idx 字段，回退序号）。
    占位判定的单一真值源——finalize/compose/fit_voice 都应走这里，别各写 `x.get('占位')`。"""
    if not isinstance(manifest, list):
        return []
    return [r.get("idx", i) for i, r in enumerate(manifest) if isinstance(r, dict) and _is_placeholder_voice_row(r)]


def placeholder_rows(manifest) -> List[dict]:
    """已加载清单里的占位句（行对象列表）。"""
    if not isinstance(manifest, list):
        return []
    return [r for r in manifest if isinstance(r, dict) and _is_placeholder_voice_row(r)]


def manifest_is_placeholder(manifest) -> bool:
    """已加载清单是否含占位句（布尔版）。"""
    return bool(placeholder_rows(manifest))


def voiceover_fingerprint(path: Optional[str]) -> str:
    """配音源指纹：voiceover.txt 非空行序列的 sha256。

    render_voice 出 时长清单 时把它记进 时长清单.meta.json，validate_timings 再比对当前
    voiceover.txt——用来抓"配音之后又改了 voiceover.txt（改词/插句/删句）导致时长清单/字幕/
    镜头时长全部过期"这条失配链。delete_shot 的强制 gate 对账只覆盖**删镜**，改词/插句覆盖不到。
    只对台词内容敏感：忽略空行与行首尾空白，避免无意义的排版改动误报。"""
    if not path or not os.path.isfile(path):
        return ""
    lines: List[str] = []
    with open(path, encoding="utf-8") as fh:
        for ln in fh:
            s = ln.strip()
            if s:
                lines.append(s)
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def voice_meta_path(root: str, ep: str) -> Optional[str]:
    """时长清单.meta.json 与 时长清单.json 同目录（合成/ 或 出视频/ 下），返回第一个存在的。"""
    for base in ("合成", "出视频"):
        p = os.path.join(root, base, ep, "配音", "时长清单.meta.json")
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
        return manifest_is_placeholder(data)
    return None


def stage_of(root: str, row: Dict[str, str], header: List[str]) -> Dict[str, Optional[str]]:
    """Return the next stage for a row, with production-mode adjustments.

    路由按 STAGE_GRAPH 顺序走，但消费每个阶段的 `requires`（跨列硬依赖）而非纯列序，
    并按 `制作模式` 调整：
      - 原生音画：配音是可选旁白层——`配音` 列视作已满足、不把 n2d-voice 当硬路由步骤，
        免得分镜/出图被"先去配音"误推卡住（说话镜由视频后端一次出同步音画）。
      - 先出视频后配音：合成前若配音仍是占位，前沿改指 n2d-voice 先补真音。
    """
    ep = row.get("_ep") or row.get("集") or ""
    def satisfied(col: str) -> bool:
        return is_progress_satisfied(root, row, col)

    native_av = is_native_av(root)
    production_mode = "原生音画" if native_av else ""

    for spec in _ROUTING_SPECS:
        skill = str(spec["owner"])
        # 原生音画：不把 配音 当硬路由步骤（避免误推 n2d-voice 卡住分镜/出图）
        if native_av and skill == "n2d-voice":
            continue
        cols = [c for c in spec.get("progress_columns", ()) if c in header]
        if not cols or all(satisfied(c) for c in cols):
            continue
        # 命中未完成阶段：其 requires（跨列硬依赖）须先满足，否则真正的前沿在更早的缺口——
        # 让外层循环按 STAGE_GRAPH 顺序先命中那个缺口阶段。
        if any(r in header and not satisfied(r) for r in stage_requires_for_mode(spec, production_mode)):
            continue
        col = next(c for c in cols if not satisfied(c))
        label, cmd = str(spec["label"]), str(spec["command"])
        if not native_av and is_video_first(root) and skill == "n2d-compose" and voice_is_placeholder(root, ep) is not False:
            return {
                "ep": ep,
                "col": col,
                "label": "补真实配音",
                "skill": "n2d-voice",
                "cmd": "n2d-voice {root} {ep}  (补真音；之后 fit_voice_to_clips + n2d-compose)",
                "note": "先出视频后配音模式：当前真实配音未确认（缺清单或仍是占位），合成前必须先补真实配音。",
            }
        return {"ep": ep, "col": col, "label": label, "skill": skill, "cmd": cmd, "note": ""}
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
