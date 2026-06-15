#!/usr/bin/env python3
"""跨集视觉契约一致性 —— 纯函数核心（⑦）。

集内继承 Diff（出图↔出视频）由 `n2d_contract_diff` 管，要求**逐字一致**。跨集是另一回事：
第 N 集和第 N-1 集的视觉契约**本就该不同**（场景/镜头不同），naive 文本 Diff 全是噪音。所以这里
只做两件**高精度·低噪**的事：

  1. 逐字段 side-by-side + 归一化相似度——纯信息，给人看"两集契约差在哪"，不产告警；
  2. **同名场景的方向反转**告警——只在**两集都出现的同一地点**（来自 asset_registry 的 LOC 名）
     的子句里，比对其【光位左右】与【轴线画左→画右走向】是否反转。同地点跨集光位/轴线翻 = 越轴/光跳
     穿帮。靠"地点共现"门控，避免把"第1集冷宫画左、第2集御花园画右"误报成漂移。

全部 **advisory·warn-only**，绝不 block（启发式不配当硬闸）。纯 stdlib + 复用 n2d_contract_diff 的
extract_section/parse_contract_fields/_norm。
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import VISUAL_CONTRACT_FIELDS  # noqa: E402
from n2d_contract_diff import _norm, extract_section, parse_contract_fields  # noqa: E402
from n2d_route import episode_number as _episode_number  # noqa: E402


# —— 跨集对比的「上集定位 / 地点门控」编排助手（单一真值源；CLI 包装脚本与质检 gate 共用，
#     不各自抄一份，避免「脚本能跑、gate 看不到」这类漂移）。出图总览 00_总览.md 是视觉契约的落盘处。——
def overview_rel(ep: str) -> str:
    """本集出图总览相对路径（视觉一致性契约整节就写在这里）。"""
    return os.path.join("出图", ep, "prompt", "00_总览.md")


def episodes_with_overview(root: str) -> List[str]:
    """已生成 00_总览.md 的所有集（按集号升序）。"""
    eps = {os.path.basename(os.path.dirname(os.path.dirname(p)))
           for p in glob.glob(os.path.join(root, "出图", "第*集", "prompt", "00_总览.md"))}
    return sorted(eps, key=lambda e: (_episode_number(e) if _episode_number(e) is not None else 10 ** 9, e))


def prior_episode(root: str, ep: str) -> Optional[str]:
    """ep 之前、已出 00_总览 的最近一集；无（首集 / 集号无法解析）→ None。"""
    n = _episode_number(ep)
    if n is None:
        return None
    prior = [e for e in episodes_with_overview(root)
             if (_episode_number(e) is not None and _episode_number(e) < n)]
    return prior[-1] if prior else None


def scene_names(root: str) -> List[str]:
    """asset_registry 的 LOC 场景名（跨集方向反转检测的地点门控词表）。缺/解析失败 → []。"""
    p = os.path.join(root, "出图", "共享", "asset_registry.json")
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception:
        return []
    out = set()
    for a in data.get("assets") or []:
        if isinstance(a, dict) and str(a.get("id") or "").upper().startswith("LOC"):
            name = str(a.get("name") or "").strip()
            if len(name) >= 2:
                out.add(name)
    return sorted(out)

# 方向字段（只对这两个字段做方向反转检测；其余字段跨集本就该变，不检）
LIGHT_FIELD = "场景光位锚"
AXIS_FIELD = "场景轴线视线"

_CLAUSE_SPLIT_RE = re.compile(r"[。；;\n，,]+")
# 光位左右（高精度词，避免裸"左/右"误命中）
_LIGHT_LEFT = ("左侧光", "画左光", "左光", "光从左", "左前光", "左顶光")
_LIGHT_RIGHT = ("右侧光", "画右光", "右光", "光从右", "右前光", "右顶光")
# 轴线走向：画左→画右 / 画右→画左
_AXIS_DIR_RE = re.compile(r"画([左右])[^画]{0,16}?[-=>→]+[^画]{0,8}?画([左右])")


def _clauses(text: str) -> List[str]:
    return [c.strip() for c in _CLAUSE_SPLIT_RE.split(text or "") if c.strip()]


def light_side(clause: str) -> Optional[str]:
    """子句里的光位左右：'L' / 'R' / None（两者都无或同现冲突时 None，不猜）。纯函数·可测。"""
    has_l = any(t in clause for t in _LIGHT_LEFT)
    has_r = any(t in clause for t in _LIGHT_RIGHT)
    if has_l == has_r:
        return None
    return "L" if has_l else "R"


def axis_dir(clause: str) -> Optional[Tuple[str, str]]:
    """子句里的轴线走向 ('左','右') / ('右','左')；无明确「画X→画Y」→ None。纯函数·可测。"""
    m = _AXIS_DIR_RE.search(clause or "")
    if not m:
        return None
    return (m.group(1), m.group(2))


def _scene_signatures(field_text: str, scenes: Sequence[str], extractor) -> Dict[str, set]:
    """{场景名: {该场景所有子句里 extractor 抽到的方向签名}}。只收在场景子句里抽到的。"""
    out: Dict[str, set] = {}
    for clause in _clauses(field_text):
        present = [s for s in scenes if s and s in clause]
        if not present:
            continue
        sig = extractor(clause)
        if sig is None:
            continue
        for s in present:
            out.setdefault(s, set()).add(sig)
    return out


def detect_inversions(prev_text: str, cur_text: str, scenes: Sequence[str], kind: str) -> List[Dict[str, str]]:
    """同名场景跨集方向反转告警（kind='light'|'axis'）。两集都出现该场景、且方向互为反转才报。纯函数·可测。"""
    extractor = light_side if kind == "light" else axis_dir
    prev_sig = _scene_signatures(prev_text, scenes, extractor)
    cur_sig = _scene_signatures(cur_text, scenes, extractor)
    out: List[Dict[str, str]] = []
    for scene in sorted(set(prev_sig) & set(cur_sig)):
        p_set, c_set = prev_sig[scene], cur_sig[scene]
        for p in p_set:
            for c in c_set:
                inverted = (kind == "light" and {p, c} == {"L", "R"}) or \
                           (kind == "axis" and isinstance(p, tuple) and c == (p[1], p[0]) and p[0] != p[1])
                if inverted:
                    out.append({
                        "scene": scene, "kind": kind,
                        "prev": _sig_str(p), "cur": _sig_str(c),
                        "note": (f"同场景「{scene}」跨集{'光位左右' if kind == 'light' else '轴线走向'}反转"
                                 f"（前集 {_sig_str(p)} → 本集 {_sig_str(c)}）：同一地点光位/轴线翻=越轴/光跳穿帮；"
                                 "确认是否有意（如反打/换机位），否则对齐前集。"),
                    })
    return out


def _sig_str(sig) -> str:
    if isinstance(sig, tuple):
        return f"画{sig[0]}→画{sig[1]}"
    return {"L": "左侧光", "R": "右侧光"}.get(sig, str(sig))


def field_similarity(prev_val: str, cur_val: str) -> float:
    """两集同字段归一化后字符 3-gram Jaccard 相似度（0–1，信息用·不产告警）。纯函数·可测。"""
    a, b = _norm(prev_val or ""), _norm(cur_val or "")
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    ga = {a[i:i + 3] for i in range(max(len(a) - 2, 1))}
    gb = {b[i:i + 3] for i in range(max(len(b) - 2, 1))}
    inter = len(ga & gb)
    union = len(ga | gb)
    return round(inter / union, 3) if union else 1.0


def cross_episode_diff(prev_text: str, cur_text: str, scenes: Sequence[str],
                       prev_ep: str = "", cur_ep: str = "") -> Dict[str, object]:
    """跨集契约对比：逐字段 side-by-side+相似度（信息）+ 同名场景方向反转告警（actionable·warn-only）。"""
    prev_sec, cur_sec = extract_section(prev_text), extract_section(cur_text)
    prev_fields = parse_contract_fields(prev_sec) if prev_sec is not None else {}
    cur_fields = parse_contract_fields(cur_sec) if cur_sec is not None else {}
    fields: List[Dict[str, object]] = []
    for f in VISUAL_CONTRACT_FIELDS:
        pv, cv = prev_fields.get(f, ""), cur_fields.get(f, "")
        fields.append({"field": f, "prev_text": pv, "cur_text": cv,
                       "similarity": field_similarity(pv, cv)})
    warnings: List[Dict[str, str]] = []
    warnings += detect_inversions(prev_fields.get(LIGHT_FIELD, ""), cur_fields.get(LIGHT_FIELD, ""), scenes, "light")
    warnings += detect_inversions(prev_fields.get(AXIS_FIELD, ""), cur_fields.get(AXIS_FIELD, ""), scenes, "axis")
    notes: List[str] = []
    if prev_sec is None:
        notes.append(f"前集 {prev_ep or 'N-1'} 缺「本集视觉一致性契约」整节——跨集对比降级（只列本集）")
    if cur_sec is None:
        notes.append(f"本集 {cur_ep or 'N'} 缺「本集视觉一致性契约」整节——先补 00_总览 契约")
    if not scenes:
        notes.append("无 LOC 场景名（asset_registry 缺/无场景）——方向反转检测靠地点门控，本次跳过，只给字段 side-by-side")
    return {
        "prev_episode": prev_ep, "cur_episode": cur_ep,
        "fields": fields, "warnings": warnings, "notes": notes,
        "summary": {"warnings": len(warnings),
                    "light_inversions": sum(1 for w in warnings if w["kind"] == "light"),
                    "axis_inversions": sum(1 for w in warnings if w["kind"] == "axis")},
    }
