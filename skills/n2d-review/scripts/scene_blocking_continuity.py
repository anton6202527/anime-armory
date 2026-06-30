#!/usr/bin/env python3
"""跨镜空间站位/遮挡连续性机检（B1）——补「同场景换机位后人物站位/前后景乱跳」的盲区。

背景（2026 工业化差异点）：行业把「3D空间+时间轴」四维坐标系当跨镜一致性核心卖点——
同一场景下不同机位、多角度画面里，主演/群演/道具在**站位、遮挡关系、空间透视**上要统一。
n2d 此前锁了：① 场景**结构**唯一性（scene_consistency 单门单窗）② **同一帧内**多主体站位
防串脸（image_qc C3 blocking）③ X1 像素验越轴。但**没有**「同 LOC 各镜的站位声明是否与
注册的场景站位一致」这一**契约层**连续性检查——主角上镜在画左门口、换机位下镜跑到画右且不是
反打，脸/服装/结构机检都看不见。

真值源（不新增冗余字段·复用既有契约）：
  `storyboard.json.visual_contract.场景轴线视线.<LOC>.站位` 早已登记每个场景的人物站位
  （如「沈念居画左、柳娘子居画右后」，「…后」即后景/遮挡序）——本检测器把它当**注册布局**（locked）。
  逐镜站位声明取自 clip 的 `template_contract.blocking` / `continuity_must` / `continuity.eyeline`。
  注册布局缺失时退回「同 LOC 首镜站位」当参考（chain 模式，仅相邻一致性，不当 locked）。

定档（镜像 world_continuity 的 locked-vs-adjacent 口径）：
  本镜某具名角色站位与**注册布局**左右相反、且本镜无反打标记      → 'block'（违锁·硬跳轴/换站位）；
  与**首镜参考**（无注册布局时）左右相反、且无反打标记            → 'warn'（可能有意重新调度，交人判）；
  含反打/正反打/over-shoulder 标记                                → 'ok'（合法翻转，抑制）；
  前后景（遮挡序）相反同理：违锁 block / 链式 warn。
  只对**注册布局与本镜都出现**的具名角色判（不在注册层的「二人」「门口」等不入判，杜绝噪声）。

纯文本·无依赖（parse_blocking / blocking_band 带 pytest）。漏报优先于误报：取不到站位声明的镜跳过。

用法：python3 scene_blocking_continuity.py <作品根> 第N集 [--json]
退出码：有任一 🔴 → 1，否则 0。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

# 方位标记（画面左右）。靠后者优先级低，先扫显式「画左/画右」再扫「左侧/右侧」。
SIDE_MARKERS = [
    ("left", ("画左", "左侧", "镜左", "左前", "左后", "偏左")),
    ("right", ("画右", "右侧", "镜右", "右前", "右后", "偏右")),
    ("center", ("居中", "正中", "画面中央", "中间", "正前")),
]
# 前后景（遮挡序）标记。注：「左后/右后/左前/右前」既是方位也带前后景，两边都登记。
DEPTH_MARKERS = [
    ("front", ("前景", "近景前", "靠前", "画前", "前排", "左前", "右前", "前方")),
    ("back", ("后景", "背景", "靠后", "画后", "后排", "身后", "左后", "右后", "后方")),
]
# 站位动词（夹在角色名与方位之间，提取名字时剥掉）。
POSITION_VERBS = "居在站位于靠坐立处守"
# 所有方位/前后景标记词（用于把角色名从片段里切出来——名字止于第一个标记词）。
_ALL_MARKER_WORDS = tuple(w for _, ws in SIDE_MARKERS for w in ws) + \
                    tuple(w for _, ws in DEPTH_MARKERS for w in ws)
# 反打/合法翻转标记（出现则该镜左右翻转视为合法，抑制告警）。
REVERSE_MARKERS = ("反打", "正反打", "过肩", "over-shoulder", "over shoulder", "oss", "反拍")


# ---------- 纯文本解析（无依赖 · pytest 覆盖） ----------

def _side_of(fragment: str) -> Optional[str]:
    for side, words in SIDE_MARKERS:
        if any(w in fragment for w in words):
            return side
    return None


def _depth_of(fragment: str) -> Optional[str]:
    for depth, words in DEPTH_MARKERS:
        if any(w in fragment for w in words):
            return depth
    return None


def _name_of(fragment: str) -> Optional[str]:
    """取片段里方位/前后景词之前的角色名。方位词本身也是中文，故名字须**止于第一个标记词**，
    再剥掉站位动词。取不到→None。"""
    frag = fragment.strip()
    # 名字止于最早出现的方位/前后景标记词（画左/画右… 本身是 CJK，不能贪婪吞进名字）。
    cuts = [frag.find(w) for w in _ALL_MARKER_WORDS if w in frag]
    cut = min((c for c in cuts if c >= 0), default=-1)
    if cut < 0:
        return None
    head = frag[:cut]
    m = re.match(r"^[一-龥·]+", head)
    if not m:
        return None
    name = m.group(0)
    # 从右侧剥掉站位动词（居/在/站…），剩下的才是名字。
    while name and name[-1] in POSITION_VERBS:
        name = name[:-1]
    # 名字至少 2 字，避免把「二」「门」这类碎词当人名。
    return name if len(name) >= 2 else None


def parse_blocking(text: str) -> Dict[str, Dict[str, Optional[str]]]:
    """站位声明文本 → {角色名: {"side": left|right|center|None, "depth": front|back|None}}。
    按 、，,；;。/ 切片，每片取「名字 + 方位 + 前后景」。纯函数·可测。"""
    out: Dict[str, Dict[str, Optional[str]]] = {}
    if not text:
        return out
    for frag in re.split(r"[、，,；;。/\n]", text):
        frag = frag.strip()
        if not frag:
            continue
        side = _side_of(frag)
        depth = _depth_of(frag)
        if side is None and depth is None:
            continue
        name = _name_of(frag)
        if not name:
            continue
        cur = out.setdefault(name, {"side": None, "depth": None})
        if side and cur["side"] is None:
            cur["side"] = side
        if depth and cur["depth"] is None:
            cur["depth"] = depth
    return out


def is_reverse_shot(text: str) -> bool:
    low = (text or "").lower()
    return any(m.lower() in low for m in REVERSE_MARKERS)


def _opposite(a: Optional[str], b: Optional[str], pos: str, neg: str) -> bool:
    """a/b 是否一正一反（pos↔neg）；任一为 None 或 center 不算冲突。纯函数。"""
    return (a in (pos, neg)) and (b in (pos, neg)) and a != b


def blocking_band(ref: Dict[str, Optional[str]], cur: Dict[str, Optional[str]],
                  locked: bool, reverse_shot: bool) -> str:
    """单角色站位/遮挡序连续性定档：
      反打镜                                  → 'ok'（合法左右翻转，抑制）；
      站位左右相反 或 前后景相反               → locked? 'block' : 'warn'；
      其余                                     → 'ok'。
    纯函数·可测。"""
    if reverse_shot:
        return "ok"
    side_flip = _opposite(ref.get("side"), cur.get("side"), "left", "right")
    depth_flip = _opposite(ref.get("depth"), cur.get("depth"), "front", "back")
    if side_flip or depth_flip:
        return "block" if locked else "warn"
    return "ok"


# ---------- storyboard 读取（尽力而为） ----------

def _load_storyboard(root: str, ep: str) -> Optional[dict]:
    path = os.path.join(root, "脚本", ep, "storyboard.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _loc_of(scene: str) -> str:
    """clip.scene「冷宫寝殿/夜/内」→ LOC 名「冷宫寝殿」（与 visual_contract.场景轴线视线 键对齐）。"""
    return str(scene or "").split("/")[0].strip()


def _registered_layouts(sb: dict) -> Dict[str, str]:
    """visual_contract.场景轴线视线.<LOC>.站位 → {LOC: 站位文本}。"""
    out: Dict[str, str] = {}
    vc = (sb.get("visual_contract") or {}) if isinstance(sb, dict) else {}
    eyelines = vc.get("场景轴线视线") or {}
    if isinstance(eyelines, dict):
        for loc, info in eyelines.items():
            if isinstance(info, dict):
                pos = info.get("站位") or info.get("blocking")
                if pos:
                    out[str(loc)] = str(pos)
    return out


def _clip_blocking_text(clip: dict) -> str:
    """逐镜站位声明：template_contract.blocking + continuity_must + continuity.eyeline 合并。"""
    parts: List[str] = []
    tc = clip.get("template_contract") or {}
    if isinstance(tc, dict):
        if tc.get("blocking"):
            parts.append(str(tc["blocking"]))
        cm = tc.get("continuity_must")
        if isinstance(cm, list):
            parts.extend(str(x) for x in cm)
        elif cm:
            parts.append(str(cm))
    cont = clip.get("continuity") or {}
    if isinstance(cont, dict) and cont.get("eyeline"):
        parts.append(str(cont["eyeline"]))
    return "；".join(parts)


def _clip_label(clip: dict, idx: int) -> str:
    return str(clip.get("id") or clip.get("label") or f"Clip_{idx:02d}")


# ---------- 编排 ----------

def analyze(root: str, ep: str) -> dict:
    res: dict = {"available": False, "shots": [], "notes": []}
    sb = _load_storyboard(root, ep)
    if not sb:
        res["notes"].append("跨镜站位机检已跳过：缺 脚本/<集>/storyboard.json。")
        return res
    clips = [c for c in (sb.get("clips") or []) if isinstance(c, dict)]
    if not clips:
        res["notes"].append("storyboard 无 clips[]。")
        return res

    registered = _registered_layouts(sb)
    res["available"] = True
    if not registered:
        res["notes"].append("visual_contract.场景轴线视线 未登记 站位——退回「同场景首镜」当参考（仅相邻一致性·warn 档）。")

    # 按 LOC 分组（保序）。
    from collections import OrderedDict
    groups: "OrderedDict[str, List[tuple]]" = OrderedDict()
    for i, clip in enumerate(clips, 1):
        loc = _loc_of(clip.get("scene", ""))
        groups.setdefault(loc, []).append((i, clip))

    for loc, items in groups.items():
        locked = loc in registered
        ref_map = parse_blocking(registered[loc]) if locked else {}
        if locked:
            res["notes"].append(f"场景[{loc}] 注册站位锁定 → 违锁站位/遮挡反转判 block。")
        for idx, clip in items:
            text = _clip_blocking_text(clip)
            cur_map = parse_blocking(text)
            if not cur_map:
                continue
            if not ref_map:  # chain 模式：首个有声明的镜定为参考
                ref_map = cur_map
                continue
            rev = is_reverse_shot(text) or is_reverse_shot(json.dumps(clip.get("template_contract") or {}, ensure_ascii=False))
            for name, cur in cur_map.items():
                if name not in ref_map:
                    continue
                v = blocking_band(ref_map[name], cur, locked, rev)
                if v != "ok":
                    res["shots"].append({
                        "clip": _clip_label(clip, idx), "scene": loc or "(全集)",
                        "char": name,
                        "ref_side": ref_map[name].get("side"), "cur_side": cur.get("side"),
                        "ref_depth": ref_map[name].get("depth"), "cur_depth": cur.get("depth"),
                        "locked": locked, "verdict": v,
                        "message": (
                            f"{name} 站位/遮挡与{'注册布局' if locked else '同场景首镜'}冲突："
                            f"{ref_map[name].get('side')}/{ref_map[name].get('depth')} → "
                            f"{cur.get('side')}/{cur.get('depth')}"
                            + ("（无反打标记·疑跳轴/换左右）" if v == "block" else "（疑重新调度·交人判）")
                        ),
                    })
            if not locked:  # chain：参考随链推进（注册布局存在时始终对锁不漂）
                for name, cur in cur_map.items():
                    ref_map.setdefault(name, cur)
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 1 if any(s["verdict"] == "block" for s in res["shots"]) else 0
    print(f"=== 跨镜空间站位/遮挡连续性机检（B1）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    icon = {"block": "⛔站位违锁", "warn": "⚠️站位漂移"}
    nb = 0
    for s in res["shots"]:
        if s["verdict"] == "block":
            nb += 1
        print(f"{icon[s['verdict']]} {s['clip']} · 场景[{s['scene']}]: {s['message']}")
    print(f"\n站位违锁 🔴 {nb} · 标出 {len(res['shots'])} 镜")
    return 1 if nb else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
