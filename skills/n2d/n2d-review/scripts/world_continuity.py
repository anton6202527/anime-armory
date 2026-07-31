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

from pillow_compat import pixel_data

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


def near_threshold_cold_jump(prev_row: Mapping[str, object], cur_row: Mapping[str, object],
                             night_luma: float, dusk_warmth: float) -> bool:
    """Cold gray twilight can straddle the night/day threshold by composition.

    W1 is meant to catch confident day↔night changes.  In cold gray fantasy plates,
    a close frame with more sky can land just above `night_luma` while the next
    wider frame falls just below it, even though both are the same overcast dusk.
    Downgrade only these near-threshold cold jumps to WARN; true bright day or
    deep night still blocks.
    """
    labels = {str(prev_row.get("daypart") or ""), str(cur_row.get("daypart") or "")}
    if labels != {"day", "night"}:
        return False
    try:
        pl = float(prev_row.get("luma"))  # type: ignore[arg-type]
        cl = float(cur_row.get("luma"))  # type: ignore[arg-type]
        pw = float(prev_row.get("warmth"))  # type: ignore[arg-type]
        cw = float(cur_row.get("warmth"))  # type: ignore[arg-type]
    except Exception:
        return False
    if pw >= dusk_warmth or cw >= dusk_warmth:
        return False
    high = max(pl, cl)
    low = min(pl, cl)
    return high <= night_luma + 8.0 and low >= night_luma - 16.0 and (high - low) <= 18.0


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


# ---------- W4 天气/季节 + 时间转场（声明驱动·确定性·非像素估） ----------
# daypart(W1) 已用像素估昼夜并硬挡 2 级跳；但**天气**(晴↔雨/雪)与**季节**(春↔冬)像素估不可靠，
# 且本就是作者在分镜文本/scene_dna「光色天气」里**声明**的事实——这里按声明 token 做确定性连续性，
# 同场景相邻镜/违锁出现互斥天气或换季 → 不连续。合法的时间跳跃（"三天后"/转场）由 cue 豁免。
# 这些是声明对账（不扫像素），缺声明优雅跳过（宁缺毋滥）。与 daypart 互补：W1 管昼夜亮度，W4 管天气/季节文本事实。

# 检测顺序：先长/强词（暴风雨、雷暴）再短词（雨），避免「雷雨」被先判成 rain。
_WEATHER_KW = [
    ("storm", ("暴风雨", "雷暴", "风暴", "狂风暴雨", "雷雨", "暴风雪")),
    ("snow", ("暴雪", "飞雪", "风雪", "雪花", "大雪", "下雪", "雪")),
    ("rain", ("暴雨", "细雨", "雨幕", "小雨", "大雨", "阵雨", "下雨", "雨")),
    ("fog", ("浓雾", "薄雾", "雾霭", "雾气", "雾")),
    ("overcast", ("阴沉", "阴天", "乌云", "密布", "阴云", "阴")),
    ("clear", ("万里无云", "晴朗", "艳阳", "碧空", "阳光", "晴")),
]
_PRECIP = {"rain", "snow", "storm"}

_SEASON_KW = [
    ("spring", ("初春", "暮春", "阳春", "春日", "春")),
    ("summer", ("盛夏", "酷暑", "炎夏", "夏日", "盛暑", "夏")),
    ("autumn", ("深秋", "金秋", "秋日", "秋风", "晚秋", "秋")),
    ("winter", ("寒冬", "隆冬", "严冬", "冬日", "数九", "冬")),
]

# 合法时间跳跃/转场 cue：命中则豁免天气/季节硬跳（不豁免 daypart W1·不松动既有硬闸）。
_TIME_TRANSITION_MARKERS = (
    "三天后", "次日", "翌日", "数日后", "数日之后", "几天后", "半月后", "一月后", "一年后", "十年后",
    "多年后", "数年后", "数月后", "转眼", "时光流转", "时光荏苒", "时间跳跃", "时间跳转", "时过境迁",
    "季节更替", "入冬", "入夏", "入春", "入秋", "转瞬", "光阴", "岁月", "转场", "时移",
)


def _category_of(text: str, table) -> Optional[str]:
    t = str(text or "")
    for cat, words in table:
        if any(w in t for w in words):
            return cat
    return None


def weather_of_text(text: str) -> Optional[str]:
    """声明文本 → 天气类别 clear/overcast/fog/rain/snow/storm（无 → None）。纯函数·可测。"""
    return _category_of(text, _WEATHER_KW)


def season_of_text(text: str) -> Optional[str]:
    """声明文本 → 季节 spring/summer/autumn/winter（无 → None）。纯函数·可测。"""
    return _category_of(text, _SEASON_KW)


def has_time_transition(text: str) -> bool:
    """文本是否含合法时间跳跃/转场 cue（命中则天气/季节硬跳视为有意推进·豁免）。纯函数·可测。"""
    t = str(text or "")
    return any(m in t for m in _TIME_TRANSITION_MARKERS)


def weather_band(prev_w: Optional[str], cur_w: Optional[str]) -> str:
    """同场景相邻镜/违锁天气连续性：
      同类 / 任一缺声明 → 'ok'；晴↔降水(雨/雪/暴风) 或 降水互跳(雨↔雪) → 'block'（突变无转场=穿帮）；
      其余软漂移(阴↔雾/阴↔晴/阴↔雨) → 'warn'。纯函数·可测。"""
    if not prev_w or not cur_w or prev_w == cur_w:
        return "ok"
    if (prev_w == "clear" and cur_w in _PRECIP) or (cur_w == "clear" and prev_w in _PRECIP):
        return "block"
    if prev_w in _PRECIP and cur_w in _PRECIP:
        return "block"
    return "warn"


def season_band(prev_s: Optional[str], cur_s: Optional[str]) -> str:
    """同场景相邻镜/违锁季节连续性：不同季节 → 'block'（同场景内不应换季，除非时间跳转 cue 豁免）；
    任一缺声明 / 同季 → 'ok'。纯函数·可测。"""
    if not prev_s or not cur_s or prev_s == cur_s:
        return "ok"
    return "block"


def _worst_band(*bands: str) -> str:
    order = {"ok": 0, "warn": 1, "block": 2}
    return max(bands, key=lambda b: order.get(b, 0)) if bands else "ok"


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
    def sort_key(path: str) -> tuple:
        name = os.path.basename(path)
        m = re.search(r"Clip_?(\d+)_(first|mid|end)\.png$", name, re.I)
        if m:
            phase = {"first": 0, "mid": 1, "end": 2}.get(m.group(2).lower(), 9)
            return (int(m.group(1)), phase, name)
        return (10**9, 9, name)

    patterns = [
        os.path.join(root, "出图", ep, "图片", "*.png"),
        os.path.join(root, "出图", ep, "*.png"),
    ]
    out: List[str] = []
    seen = set()
    for pattern in patterns:
        for path in sorted(glob.glob(pattern), key=sort_key):
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
        px = list(pixel_data(im))
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
        px = list(pixel_data(im))
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
        px = list(pixel_data(im))
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


def _declared_env_of_shot(root: str, ep: str) -> Dict[str, str]:
    """每镜 PNG → 该镜整块文本（用于 W4 解析声明的天气/季节/时间转场 cue）。无则空。

    与 _declared_light_of_shot 同源(01_分镜出图.md 的 `## ` 分块)，但返回整块文本——天气/季节
    可能写在 时间/天气/光线 行、场景行、台词或转场标注里，取整块更稳。缺文件优雅跳过。"""
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
        out[os.path.basename(mt.group(1))] = blk
    return out


def _locked_env(root: str, ep: str) -> Dict[str, dict]:
    """每场景 → {weather, season}（从 scene_dna 的「光色天气」/「季节」字段解析的锁定环境）。

    与 _locked_dayparts 同源(scene_dna.json)。给 W4 一个场景级 canonical 基准：某镜声明的天气/季节
    与场景锁定值互斥 → 违锁。读不到 → 空（不启用违锁校验，只走相邻镜）。"""
    out: Dict[str, dict] = {}
    candidates = [
        os.path.join(root, "出图", "共享", "scene_dna.json"),
        os.path.join(root, "出图", ep, "scene_dna.json"),
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
            season_src = str(info.get("季节") or info.get("season") or "") + lit
            env = {}
            w = weather_of_text(lit)
            s = season_of_text(season_src)
            if w:
                env["weather"] = w
            if s:
                env["season"] = s
            if env:
                out[name] = env
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
        targets = [
            os.path.basename(m)
            for m in re.findall(rf"出图/{re.escape(ep)}/图片/([^`』\s]+\.png)", blk)
        ]
        if not targets:
            mt = re.search(r"出图/[^/]+/图片/([^`』\s]+\.png)", blk)
            if not mt:
                continue
            targets = [os.path.basename(mt.group(1))]
        m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^##\s+|\Z)", blk)
        refs = m.group(0) if m else ""
        scenes = re.findall(r"场景定妆：`[^`]*定妆_([^`\s，。、,）)]+)", refs)
        if not scenes:
            scenes = re.findall(r"定妆_场景_([^`\s，。、,）)]+)", refs)
            scenes = [f"场景_{s}" for s in scenes]
        if not scenes:
            scenes = [
                s for s in re.findall(r"定妆_([^`\s，。、,）)]+)", refs)
                if s.startswith(("场景_", "LOC_"))
            ]
        if not scenes:
            scenes = re.findall(r"定妆_([^`\s，。、,）)]+)", refs)
        if scenes:
            for png in targets:
                out[png] = scenes[0]
    return out


def registered_light_dir(loc_asset: Mapping[str, object]) -> Dict[str, Optional[str]]:
    """从 LOC 资产 `constraints.lighting_signature.key_light_direction`（或 `constraints.light_anchor`）
    解析**登记的**主光方向 → {h, v}（纯函数·可测）。这是场景的 canonical 光向，此前只被 LSIG 当死字段
    跳过（LSIG 只量色相/饱和度）；现在给它一个像素核对靶。受控枚举（left_front/top/底光…），按子串判。"""
    if not isinstance(loc_asset, Mapping):
        return {"h": None, "v": None}
    cons = loc_asset.get("constraints") if isinstance(loc_asset.get("constraints"), Mapping) else {}
    sig = cons.get("lighting_signature") if isinstance(cons.get("lighting_signature"), Mapping) else {}
    raw = str(sig.get("key_light_direction") or cons.get("light_anchor") or "").lower()
    h: Optional[str] = None
    v: Optional[str] = None
    if any(k in raw for k in ("left", "画左", "左")):
        h = "left"
    elif any(k in raw for k in ("right", "画右", "右")):
        h = "right"
    if any(k in raw for k in ("top", "overhead", "顶")):
        v = "top"
    elif any(k in raw for k in ("bottom", "under", "底", "脚")):
        v = "bottom"
    return {"h": h, "v": v}


def _registered_light_of_scene(root: str) -> List[tuple]:
    """[(匹配键, {h,v})] 从 asset_registry 各 LOC 的登记主光方向。匹配键= LOC name + id 末段，
    供逐镜场景 token 子串匹配。缺登记/解析不到方向→不收。"""
    try:
        from n2d_contract import asset_registry_path  # n2d/_lib
        path = asset_registry_path(root)
    except Exception:
        path = os.path.join(root, "出图", "共享", "asset_registry.json")
    out: List[tuple] = []
    if not os.path.isfile(path):
        return out
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return out
    for asset in (data.get("assets") or []) if isinstance(data, dict) else []:
        aid = str(asset.get("id") or "") if isinstance(asset, dict) else ""
        if not aid.startswith("LOC_"):
            continue
        rd = registered_light_dir(asset)
        if rd["h"] or rd["v"]:
            for key in (str(asset.get("name") or ""), aid):
                if key:
                    out.append((key, rd))
    return out


def _match_registered_light(scene: str, registered: List[tuple]) -> Optional[Dict[str, Optional[str]]]:
    for key, rd in registered:
        if scene and (scene in key or key in scene):
            return rd
    return None


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
    declared = _declared_light_of_shot(root, ep)  # W3 光位锚自洽用（per-shot prompt 文本）
    registered_light = _registered_light_of_scene(root)  # W3b 注册 key_light_direction 像素核对（#6）
    env_text = _declared_env_of_shot(root, ep)    # W4 天气/季节/转场 cue（per-shot 整块文本·声明驱动）
    locked_env = _locked_env(root, ep)            # W4 场景级锁定天气/季节（scene_dna）
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
            "weather": weather_of_text(env_text.get(name, "")),     # W4 声明天气（无→None）
            "season": season_of_text(env_text.get(name, "")),       # W4 声明季节（无→None）
            "time_transition": has_time_transition(env_text.get(name, "")),  # 合法转场 cue（豁免天气/季节硬跳）
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
        lenv = locked_env.get(scene, {}) if scene else {}
        if lock:
            res["notes"].append(f"场景[{scene}] scene_dna 锁定时辰={lock}，违锁 2 级 → block。")
        prev = None
        prev_row = None
        prev_az = None
        prev_elev = None
        prev_w = None
        prev_s = None
        for row in rows:
            cur = row["daypart"]
            if prev is None:
                # 组首镜：无相邻前镜，仅与锁定值比对（若有锁）。
                v = continuity_band(cur, cur, lock) if lock else "ok"
            else:
                v = continuity_band(prev, cur, lock)
                if v == "block" and prev_row and near_threshold_cold_jump(prev_row, row, night_luma, dusk_warmth):
                    v = "warn"
            if v != "ok":
                item = {
                    "metric": "daypart",
                    "png": row["png"], "scene": scene or "(全集)",
                    "prev_daypart": prev, "daypart": cur,
                    "locked": lock, "verdict": v,
                }
                if prev_row and near_threshold_cold_jump(prev_row, row, night_luma, dusk_warmth):
                    item["softened"] = "near_threshold_cold_gray_twilight"
                    item["prev_luma"] = prev_row.get("luma")
                    item["luma"] = row.get("luma")
                res["shots"].append(item)
            prev = cur
            prev_row = row
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
            # W3b（#6）：实测光向 与 注册 key_light_direction 矛盾 → warn。给场景 canonical 主光方向
            # 一个像素核对靶（此前只被 LSIG 当死字段）。prompt 文本若没写也兜得住；已被上面 prompt 锚命中则不重报。
            reg_dir = _match_registered_light(scene, registered_light) if scene else None
            if reg_dir and not reason:
                reg_reason = anchor_contradiction(reg_dir, cur_az, cur_elev)
                if reg_reason:
                    res["shots"].append({
                        "metric": "light_anchor_registered",
                        "png": row["png"], "scene": scene or "(全集)",
                        "light_az": cur_az, "light_elev": cur_elev,
                        "verdict": "warn",
                        "message": f"{reg_reason}（注册 key_light_direction）——实测光向与场景登记主光方向矛盾，人核对是否光打反/锚写错。",
                    })
            # W4 天气连续性：同场景相邻镜/违锁出现互斥天气（晴↔雨雪）且无转场 cue → block（声明驱动·确定性）。
            cur_w = row.get("weather")
            if cur_w:
                wv = _worst_band(weather_band(prev_w, cur_w),
                                 weather_band(lenv.get("weather"), cur_w))
                if wv != "ok" and not row.get("time_transition"):
                    res["shots"].append({
                        "metric": "weather",
                        "png": row["png"], "scene": scene or "(全集)",
                        "prev_weather": prev_w, "weather": cur_w,
                        "locked": lenv.get("weather"), "verdict": wv,
                        "message": (f"天气 {prev_w or lenv.get('weather')}→{cur_w} 同场景内突变且无时间转场 cue"
                                    f"（晴↔雨雪等不连续；确属时间跳跃请在分镜写'三天后'等转场，或登记 intentional_discontinuity）"),
                    })
                prev_w = cur_w
            # W4 季节连续性：同场景内换季（春↔冬）且无转场 cue → block。
            cur_s = row.get("season")
            if cur_s:
                sv = _worst_band(season_band(prev_s, cur_s),
                                 season_band(lenv.get("season"), cur_s))
                if sv != "ok" and not row.get("time_transition"):
                    res["shots"].append({
                        "metric": "season",
                        "png": row["png"], "scene": scene or "(全集)",
                        "prev_season": prev_s, "season": cur_s,
                        "locked": lenv.get("season"), "verdict": sv,
                        "message": (f"季节 {prev_s or lenv.get('season')}→{cur_s} 同场景内换季且无时间转场 cue"
                                    f"（同场景不应换季；确属时间跳跃请写转场 cue 或登记 intentional_discontinuity）"),
                    })
                prev_s = cur_s
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
        entry = scenes.setdefault(scene, {"shots": [], "dayparts": {}, "light_azimuths": {}, "light_elevations": {}, "weathers": {}, "seasons": {}, "findings": []})
        entry["shots"].append(str(row.get("png") or ""))
        for field, bucket in (("daypart", "dayparts"), ("light_az", "light_azimuths"),
                              ("light_elev", "light_elevations"), ("weather", "weathers"), ("season", "seasons")):
            value = str(row.get(field) or "")
            if value:
                counts = entry[bucket]
                counts[value] = counts.get(value, 0) + 1
    for item in shots:
        scene = str(item.get("scene") or "(全集)")
        scenes.setdefault(scene, {"shots": [], "dayparts": {}, "light_azimuths": {}, "light_elevations": {}, "weathers": {}, "seasons": {}, "findings": []})
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
