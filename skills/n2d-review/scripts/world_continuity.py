#!/usr/bin/env python3
"""天气/时辰推进连续性机检（W1）+ 光位方向连续性（W2）——补 scene_dna/visual_contract
锁了「光色天气」「主光方向」却没人查的盲区。

2026 实战：scene_dna 能把一个场景的「光色天气」（白天/黄昏/夜/晴/雨）**锁**进契约，
但**没有任何机检校验它**——同一场景相邻两镜可以白天↔黑夜对跳、晴↔暴雨乱翻，
脸/服装/结构机检都看不见这种「时辰/天气硬跳变」。本脚本把它脚本化成可疑→人判的初筛门。

机制（诚实优先·自标定·只抓高置信硬跳）：
  逐镜从像素估两个量——平均明度 luma(0..255) 与 暖度 warmth=(平均R−平均B)归一到 −1..1。
  据此分「时辰」daypart：低明度→夜；中明度+高暖度→黄昏；高明度→白天（阈值见 daypart 默认参数，
  可调）。把 daypart 排成 夜0/黄昏1/白天2 三级（daypart_rank），用「级差」量跳变幅度：
    同一场景相邻两镜——
      2 级跳（白天↔黑夜）= 🔴 block（硬不连续，多半画错时辰）；
      1 级跳（白天→黄昏 等）= 🟡 warn（可能是有意推进，交人判）；
      同级 = ok。
  若 scene_dna 提供了 locked_label（场景锁定的光色天气），某镜与之差 2 级 → block（违锁）。

  诚实边界：风格化漫剧 + 纯像素估时辰，这是**粗筛不是裁决**——命中只作「这镜时辰/天气可疑，
  人比对相邻镜」的信号，绝不自动改图。漏报（放过软跳）比误报代价低，故只在 2 级硬跳上判 🔴。
  场景分组尽力而为：从 01_分镜出图.md 取每镜场景标签；取不到则整集当一条时间线走。

W2 光位方向（advisory）：从「最亮区域质心」估每镜主光方位（left/center/right），同场景相邻镜
主光左右硬翻转（如上镜画左顺光、下镜画右逆光）→ warn 初筛，交人比对（光位比时辰更易合理变化，只 warn）。

W3 光照物理（advisory·补 W2 只管左右的垂直盲区）：① 光照俯仰——从最亮区质心纵坐标估顶光/底光，
同场景顶光↔底光(自下而上的鬼影光)硬翻转=物理可疑 warn；② 光位锚自洽——实测主光方位/俯仰 与
出图 prompt 声明的「光位锚」方向矛盾（声明画左却实测右打光）→ warn，抓"光打反/锚写错"。

依赖 Pillow（缺则优雅跳过，交人判）。纯数学部分（daypart/daypart_rank/continuity_band/light_azimuth/light_dir_band）无依赖、带 pytest。

用法：python3 world_continuity.py <作品根> 第N集 [--night-luma 70] [--day-luma 140] [--dusk-warmth 0.06] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List, Mapping, Optional, Sequence

# 时辰分档默认阈值（self-calibrated 不到，故给文档化可调参数，画风偏暗/偏亮时可整体平移）：
DEFAULT_NIGHT_LUMA = 70.0    # 平均明度 < 此 → 倾向「夜」
DEFAULT_DAY_LUMA = 140.0     # 平均明度 ≥ 此 → 倾向「白天」
DEFAULT_DUSK_WARMTH = 0.06   # 介于夜/白天之间且 暖度 ≥ 此 → 「黄昏」（暖色压顶），否则归白天
SCENE_WORLD_LEDGER_KIND = "n2d_scene_world_ledger"


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def daypart(luma: float, warmth: float,
            night_luma: float = DEFAULT_NIGHT_LUMA, day_luma: float = DEFAULT_DAY_LUMA,
            dusk_warmth: float = DEFAULT_DUSK_WARMTH) -> str:
    """像素估时辰：luma=平均明度(0..255)，warmth=(平均R−平均B)归一(−1..1)。
      luma < night_luma                              → 'night'（整体压暗）；
      night_luma ≤ luma < day_luma 且 warmth ≥ dusk_warmth → 'dusk'（暖光压顶的黄昏/金时）；
      其余（含中明度但冷调，或 luma ≥ day_luma）       → 'day'。
    阈值均为可调参数（画风偏暗/偏亮整体平移即可）。纯函数·可测。"""
    if luma < night_luma:
        return "night"
    if luma < day_luma and warmth >= dusk_warmth:
        return "dusk"
    return "day"


def daypart_rank(label: str) -> int:
    """时辰排级：night=0 / dusk=1 / day=2；用相邻镜的级差量跳变幅度。未知标签→1（中性·不放大跳）。"""
    return {"night": 0, "dusk": 1, "day": 2}.get(label, 1)


def continuity_band(prev_label: str, cur_label: str, locked_label: Optional[str] = None) -> str:
    """同场景相邻两镜的时辰连续性定档（外加 scene_dna 锁定校验）：
      同级                         → 'ok'；
      1 级跳（如 day→dusk）         → 'warn'（可能有意推进，交人判）；
      2 级跳（白天↔黑夜）           → 'block'（硬不连续）；
      若 locked_label 给定且本镜与之差 2 级 → 'block'（违 scene_dna 锁的光色天气）。
    取「相邻跳」与「违锁」两路里较重的一档。纯函数·可测。"""
    def jump_band(a: str, b: str) -> str:
        d = abs(daypart_rank(a) - daypart_rank(b))
        if d >= 2:
            return "block"
        if d == 1:
            return "warn"
        return "ok"

    bands = [jump_band(prev_label, cur_label)]
    if locked_label is not None:
        d = abs(daypart_rank(locked_label) - daypart_rank(cur_label))
        bands.append("block" if d >= 2 else "ok")
    order = {"ok": 0, "warn": 1, "block": 2}
    return max(bands, key=lambda b: order.get(b, 0))


# ---------- 光位方向连续性（W2·补 光位锚 落了契约却没机检的盲区） ----------
# scene_dna/visual_contract 锁了「主光方向」，但 W1 只验亮度/暖度分桶、不管光从哪边来——
# 同场景上镜左侧顺光、下镜突然右侧逆光是常见漂移。这里从「最亮区域质心」估光位方位作 advisory 初筛。

DEFAULT_LIGHT_DEADZONE = 0.12  # 亮区质心 x 距画面中线 < 此（归一）→ 视作居中/顶光，不判左右


def light_azimuth(cx: float, deadzone: float = DEFAULT_LIGHT_DEADZONE) -> str:
    """最亮区域质心的归一横坐标 cx∈[0,1] → 主光方位 'left'|'center'|'right'。
    距中线 0.5 不足 deadzone 视作居中/顶光（不判左右）。纯函数·可测。"""
    if cx < 0.5 - deadzone:
        return "left"
    if cx > 0.5 + deadzone:
        return "right"
    return "center"


def light_dir_band(prev_az: str, cur_az: str) -> str:
    """同场景相邻两镜主光方位连续性（advisory·只抓左右硬翻转）：
      left↔right 硬翻转 → 'warn'（光位可疑跳，交人比对）；其余（含 center 过渡）→ 'ok'。
    光位比时辰更易因合理重新布光/运镜变化，故只 warn 不 block。纯函数·可测。"""
    if {prev_az, cur_az} == {"left", "right"}:
        return "warn"
    return "ok"


# ---------- W3 光照俯仰（顶光↔底光/鬼影光）+ 光位锚自洽（实测 vs 声明方向） ----------
# W2 只判左右（line: "只回 x；上下/顶光归 center"），明确不管**垂直**光向。本段补两块物理盲区：
#   ① 光照俯仰：顶光↔底光(自下而上的鬼影光)横跳——底光是反常/惊悚打光，跨镜翻转=物理穿帮（W2 看不到）；
#   ② 光位锚自洽：实测主光方位 与 出图 prompt 声明的「光位锚」方向矛盾（声明画左却实测右打光）。

def light_elevation(cy: float, deadzone: float = DEFAULT_LIGHT_DEADZONE) -> str:
    """最亮区域质心归一纵坐标 cy∈[0,1] → 光照俯仰 'top'|'center'|'bottom'。
    cy 小=亮区偏上=顶光；cy 大=亮区偏下=底光/脚光（自下而上的鬼影光）。距中线不足 deadzone=居中。纯函数·可测。"""
    if cy < 0.5 - deadzone:
        return "top"
    if cy > 0.5 + deadzone:
        return "bottom"
    return "center"


def light_elev_band(prev_el: str, cur_el: str) -> str:
    """同场景相邻镜光照俯仰连续性（advisory·只抓顶↔底硬翻转）：
      top↔bottom 翻转 → 'warn'（顶光↔底光鬼影光物理可疑跳）；其余 → 'ok'。纯函数·可测。"""
    if {prev_el, cur_el} == {"top", "bottom"}:
        return "warn"
    return "ok"


def declared_light_dir(text: str) -> Dict[str, Optional[str]]:
    """从「光位锚」文本解析声明的主光方向 → {'h': left|right|None, 'v': top|bottom|None}。
    逆光/侧逆等含糊词不判 h/v（返回 None）。纯函数·可测。"""
    t = str(text or "")
    h: Optional[str] = None
    v: Optional[str] = None
    if re.search(r"画左|左侧|左方|左前|左[打主]|screen[\s-]*left", t, re.I):
        h = "left"
    elif re.search(r"画右|右侧|右方|右前|右[打主]|screen[\s-]*right", t, re.I):
        h = "right"
    if re.search(r"顶光|头顶光|顶[打部]|overhead|top[\s-]*light", t, re.I):
        v = "top"
    elif re.search(r"底光|脚光|下打光|自下而上|鬼影光|under[\s-]*lit|under[\s-]*light", t, re.I):
        v = "bottom"
    return {"h": h, "v": v}


def anchor_contradiction(declared: Mapping[str, Optional[str]],
                         measured_az: Optional[str], measured_elev: Optional[str]) -> Optional[str]:
    """实测光向 与 声明光位锚 是否矛盾（advisory）。两侧同轴且相反 → 返回人读理由，否则 None。纯函数·可测。"""
    dh, dv = declared.get("h"), declared.get("v")
    if dh in ("left", "right") and measured_az in ("left", "right") and dh != measured_az:
        return f"光位锚声明主光在「{dh}」，实测最亮区却偏「{measured_az}」"
    if dv in ("top", "bottom") and measured_elev in ("top", "bottom") and dv != measured_elev:
        return f"光位锚声明「{dv}」光，实测最亮区却偏「{measured_elev}」"
    return None


# ---------- 图像（需 Pillow） ----------

def _probe_pillow() -> bool:
    try:
        import PIL  # noqa
        return True
    except Exception:
        return False


def episode_png_paths(root: str, ep: str) -> List[str]:
    """Return episode PNGs from the canonical 图片/ directory, plus legacy flat files."""
    patterns = [
        os.path.join(root, "出图", ep, "图片", "*.png"),
        os.path.join(root, "出图", ep, "*.png"),
    ]
    out: List[str] = []
    seen = set()
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            norm = os.path.normpath(path)
            if norm not in seen:
                seen.add(norm)
                out.append(path)
    return out


def _luma_warmth(path: str, size: int = 96) -> Optional[tuple]:
    """缩略图后取 (平均luma, 暖度)：luma=0.299R+0.587G+0.114B；暖度=(meanR−meanB)/255 ∈ −1..1。
    读图失败→None（不污染时间线）。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("RGB")
        im.thumbnail((size, size))
        px = list(im.getdata())
        n = len(px)
        if n == 0:
            return None
        sr = sum(p[0] for p in px)
        sg = sum(p[1] for p in px)
        sb = sum(p[2] for p in px)
        mr, mg, mb = sr / n, sg / n, sb / n
        luma = 0.299 * mr + 0.587 * mg + 0.114 * mb
        warmth = (mr - mb) / 255.0
        return (luma, warmth)
    except Exception:
        return None


def _bright_centroid(path: str, size: int = 96, top_frac: float = 0.15) -> Optional[float]:
    """取图中最亮 top_frac 像素的质心归一横坐标 cx∈[0,1]（光从哪侧来）。读图失败/全黑→None。
    只回 x（光位左右是主漂移轴；上下/顶光归 center 由 deadzone 兜）。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("L")
        im.thumbnail((size, size))
        w, h = im.size
        if w == 0 or h == 0:
            return None
        px = list(im.getdata())
        n = len(px)
        order = sorted(range(n), key=lambda i: px[i], reverse=True)
        k = max(1, int(n * top_frac))
        bright = order[:k]
        # 只统计确有亮度的像素，避免全黑图把质心摊到几何中心。
        sx = sum((i % w) for i in bright)
        return (sx / k) / max(1, w - 1)
    except Exception:
        return None


def _bright_centroid_y(path: str, size: int = 96, top_frac: float = 0.15) -> Optional[float]:
    """取图中最亮 top_frac 像素的质心归一纵坐标 cy∈[0,1]（光从上还是下来·W3 俯仰用）。读图失败/全黑→None。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("L")
        im.thumbnail((size, size))
        w, h = im.size
        if w == 0 or h == 0:
            return None
        px = list(im.getdata())
        n = len(px)
        order = sorted(range(n), key=lambda i: px[i], reverse=True)
        k = max(1, int(n * top_frac))
        sy = sum((i // w) for i in order[:k])
        return (sy / k) / max(1, h - 1)
    except Exception:
        return None


def _declared_light_of_shot(root: str, ep: str) -> Dict[str, str]:
    """每镜 PNG → 该镜「光位锚」声明文本（取 01_分镜出图.md 每块的 光位锚 行）。无则空。"""
    p = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    out: Dict[str, str] = {}
    if not os.path.isfile(p):
        return out
    try:
        text = open(p, encoding="utf-8").read()
    except Exception:
        return out
    for blk in re.split(r"(?m)(?=^## )", text):
        if not blk.strip().startswith("## "):
            continue
        mt = re.search(r"出图/[^/]+/([^`』\s]+\.png)", blk)
        if not mt:
            continue
        png = os.path.basename(mt.group(1))
        ml = re.search(r"(?m)^.*光位锚.*$", blk)
        if ml:
            out[png] = ml.group(0)
    return out


def _scene_of_shot(root: str, ep: str) -> Dict[str, str]:
    """每镜 PNG → 它引用的场景定妆名（取 01_分镜出图.md 参考图行里的 定妆_<X>）。
    取不到则空字典，上层把整集当一条时间线（场景标签 ""）。与 scene_consistency 同源解析。"""
    p = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    out: Dict[str, str] = {}
    if not os.path.isfile(p):
        return out
    try:
        text = open(p, encoding="utf-8").read()
    except Exception:
        return out
    for blk in re.split(r"(?m)(?=^## )", text):
        if not blk.strip().startswith("## "):
            continue
        mt = re.search(r"出图/[^/]+/([^`』\s]+\.png)", blk)
        if not mt:
            continue
        png = os.path.basename(mt.group(1))
        m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^##\s+|\Z)", blk)
        refs = m.group(0) if m else ""
        scenes = re.findall(r"定妆_([^`\s，。、,）)]+)", refs)
        if scenes:
            out[png] = scenes[0]
    return out


def _locked_dayparts(root: str, ep: str) -> Dict[str, str]:
    """尽力而为：从 scene_dna / 契约里读每个场景锁定的「光色天气」并映射成 daypart 标签。
    读不到（无该契约 / 字段缺失）→ 空字典（不启用违锁校验，只走相邻跳）。"""
    out: Dict[str, str] = {}
    candidates = [
        os.path.join(root, "出图", "共享", "scene_dna.json"),
        os.path.join(root, "出图", ep, "scene_dna.json"),
    ]
    kw = [
        ("night", ("夜", "深夜", "黑夜", "月", "星")),
        ("dusk", ("黄昏", "傍晚", "日暮", "夕", "暮", "金时", "晚霞", "落日")),
        ("day", ("白天", "正午", "日间", "晴", "清晨", "上午", "午后", "阳光")),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        scenes = data.get("scenes") if isinstance(data, dict) else None
        if not isinstance(scenes, dict):
            continue
        for name, info in scenes.items():
            if not isinstance(info, dict):
                continue
            lit = str(info.get("光色天气") or info.get("光色") or info.get("天气") or "")
            if not lit:
                continue
            for label, words in kw:
                if any(w in lit for w in words):
                    out[name] = label
                    break
    return out


def analyze(root: str, ep: str, night_luma: float = DEFAULT_NIGHT_LUMA,
            day_luma: float = DEFAULT_DAY_LUMA, dusk_warmth: float = DEFAULT_DUSK_WARMTH) -> dict:
    res: dict = {"available": _probe_pillow(), "shots": [], "notes": [], "timeline": []}
    if not res["available"]:
        res["notes"].append("天气/时辰连续性机检已跳过（未装 Pillow）——时辰/天气硬跳暂由人比对相邻镜。")
        return res
    pngs = episode_png_paths(root, ep)
    if not pngs:
        res["notes"].append("本集无分镜 PNG。")
        return res
    smap = _scene_of_shot(root, ep)
    locked = _locked_dayparts(root, ep)
    declared = _declared_light_of_shot(root, ep)  # W3 光位锚自洽用
    if not smap:
        res["notes"].append("未取到逐镜场景标签——整集当一条时间线走（仅查相邻镜时辰硬跳）。")

    # 逐镜估时辰，保留场景标签与文件顺序（同名分镜的拍摄顺序≈文件名序）。
    timeline: List[dict] = []
    for p in pngs:
        lw = _luma_warmth(p)
        if lw is None:
            continue
        luma, warmth = lw
        name = os.path.basename(p)
        scene = smap.get(name, "")
        cx = _bright_centroid(p)
        cy = _bright_centroid_y(p)
        timeline.append({
            "png": name, "scene": scene,
            "luma": round(luma, 1), "warmth": round(warmth, 3),
            "daypart": daypart(luma, warmth, night_luma, day_luma, dusk_warmth),
            "light_cx": None if cx is None else round(cx, 3),
            "light_az": None if cx is None else light_azimuth(cx),
            "light_cy": None if cy is None else round(cy, 3),
            "light_elev": None if cy is None else light_elevation(cy),
            "declared_light": declared.get(name, ""),
        })
    if not timeline:
        res["notes"].append("无法读图估时辰。")
        return res
    res["timeline"] = timeline

    # 按场景分组（场景标签相同视作同一时间线），组内按文件顺序走相邻连续性。
    from collections import defaultdict, OrderedDict
    groups: "OrderedDict[str, List[dict]]" = OrderedDict()
    for row in timeline:
        groups.setdefault(row["scene"], []).append(row)

    for scene, rows in groups.items():
        lock = locked.get(scene) if scene else None
        if lock:
            res["notes"].append(f"场景[{scene}] scene_dna 锁定时辰={lock}，违锁 2 级 → block。")
        prev = None
        prev_az = None
        prev_elev = None
        for row in rows:
            cur = row["daypart"]
            if prev is None:
                # 组首镜：无相邻前镜，仅与锁定值比对（若有锁）。
                v = continuity_band(cur, cur, lock) if lock else "ok"
            else:
                v = continuity_band(prev, cur, lock)
            if v != "ok":
                res["shots"].append({
                    "metric": "daypart",
                    "png": row["png"], "scene": scene or "(全集)",
                    "prev_daypart": prev, "daypart": cur,
                    "locked": lock, "verdict": v,
                })
            prev = cur
            # W2 光位方向：同场景相邻镜主光方位左右硬翻转 → warn（advisory）。
            cur_az = row.get("light_az")
            if prev_az and cur_az:
                lv = light_dir_band(prev_az, cur_az)
                if lv != "ok":
                    res["shots"].append({
                        "metric": "light_dir",
                        "png": row["png"], "scene": scene or "(全集)",
                        "prev_light_az": prev_az, "light_az": cur_az,
                        "verdict": lv,
                        "message": f"主光方位 {prev_az}→{cur_az} 硬翻转（疑光位跳·人比对相邻镜）",
                    })
            if cur_az:
                prev_az = cur_az
            # W3 光照俯仰：同场景相邻镜顶光↔底光(鬼影光)硬翻转 → warn（物理可疑·W2 不管垂直）。
            cur_elev = row.get("light_elev")
            if prev_elev and cur_elev:
                ev = light_elev_band(prev_elev, cur_elev)
                if ev != "ok":
                    res["shots"].append({
                        "metric": "light_elevation",
                        "png": row["png"], "scene": scene or "(全集)",
                        "prev_light_elev": prev_elev, "light_elev": cur_elev,
                        "verdict": ev,
                        "message": f"光照俯仰 {prev_elev}→{cur_elev} 翻转（顶光↔底光鬼影光·物理可疑，人比对相邻镜）",
                    })
            if cur_elev:
                prev_elev = cur_elev
            # W3 光位锚自洽：实测主光方位/俯仰 与 出图 prompt 声明的「光位锚」矛盾 → warn。
            reason = anchor_contradiction(declared_light_dir(row.get("declared_light", "")),
                                          cur_az, cur_elev)
            if reason:
                res["shots"].append({
                    "metric": "light_anchor",
                    "png": row["png"], "scene": scene or "(全集)",
                    "light_az": cur_az, "light_elev": cur_elev,
                    "verdict": "warn",
                    "message": f"{reason}——实测光向与声明光位锚矛盾，人核对是否光打反/写错锚。",
                })
    return res


def build_scene_world_ledger(root: str, ep: str, report: Mapping[str, object]) -> dict:
    """Build a persistent scene/world ledger from world_continuity output.

    The ledger is intentionally evidence-oriented: it records the per-shot light/daypart
    observations and groups continuity findings by scene, so later episodes can compare
    against a stable world-state surface instead of re-parsing one-off audit output.
    """
    timeline = [row for row in report.get("timeline", []) if isinstance(row, Mapping)] if isinstance(report, Mapping) else []
    shots = [row for row in report.get("shots", []) if isinstance(row, Mapping)] if isinstance(report, Mapping) else []
    scenes: Dict[str, Dict[str, object]] = {}
    for row in timeline:
        scene = str(row.get("scene") or "(全集)")
        entry = scenes.setdefault(scene, {"shots": [], "dayparts": {}, "light_azimuths": {}, "light_elevations": {}, "findings": []})
        entry["shots"].append(str(row.get("png") or ""))
        for field, bucket in (("daypart", "dayparts"), ("light_az", "light_azimuths"), ("light_elev", "light_elevations")):
            value = str(row.get(field) or "")
            if value:
                counts = entry[bucket]
                counts[value] = counts.get(value, 0) + 1
    for item in shots:
        scene = str(item.get("scene") or "(全集)")
        scenes.setdefault(scene, {"shots": [], "dayparts": {}, "light_azimuths": {}, "light_elevations": {}, "findings": []})
        scenes[scene]["findings"].append({
            "metric": item.get("metric"),
            "png": item.get("png"),
            "verdict": item.get("verdict"),
            "message": item.get("message", ""),
        })
    return {
        "kind": SCENE_WORLD_LEDGER_KIND,
        "episode": ep,
        "available": bool(report.get("available")) if isinstance(report, Mapping) else False,
        "timeline": timeline,
        "scenes": scenes,
        "summary": {
            "scene_count": len(scenes),
            "finding_count": len(shots),
            "block_count": sum(1 for item in shots if item.get("verdict") == "block"),
            "warn_count": sum(1 for item in shots if item.get("verdict") == "warn"),
        },
        "source": "n2d-review/world_continuity",
    }


def scene_world_ledger_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"scene_world_ledger_{ep}.json")


def write_scene_world_ledger(root: str, ep: str, report: Optional[Mapping[str, object]] = None) -> str:
    report = report or analyze(root, ep)
    payload = build_scene_world_ledger(root, ep, report)
    path = scene_world_ledger_path(root, ep)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--night-luma", type=float, default=DEFAULT_NIGHT_LUMA)
    ap.add_argument("--day-luma", type=float, default=DEFAULT_DAY_LUMA)
    ap.add_argument("--dusk-warmth", type=float, default=DEFAULT_DUSK_WARMTH)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--write", action="store_true", help="write 生产数据/scene_world_ledger_第N集.json")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.night_luma, ns.day_luma, ns.dusk_warmth)
    if ns.write:
        path = write_scene_world_ledger(ns.root.rstrip("/"), ns.episode, res)
        res["ledger_path"] = path
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 天气/时辰推进连续性机检（W1·同场景相邻镜时辰硬跳）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    nb = 0
    for s in res["shots"]:
        if s["verdict"] == "block":
            nb += 1
        if s.get("metric") == "light_dir":
            print(f"⚠️光位翻转 {s['png']} · 场景[{s['scene']}]: "
                  f"{s.get('prev_light_az')}→{s.get('light_az')}")
        else:
            icon = {"block": "⛔时辰硬跳", "warn": "⚠️时辰推进"}
            lk = f"·锁定{s['locked']}" if s.get("locked") else ""
            print(f"{icon[s['verdict']]} {s['png']} · 场景[{s['scene']}]{lk}: "
                  f"{s.get('prev_daypart')}→{s['daypart']}")
    print(f"\n时辰硬跳 🔴 {nb} · 标出 {len(res['shots'])} 镜（含光位方向 W2 advisory）")
    return 1 if nb else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
