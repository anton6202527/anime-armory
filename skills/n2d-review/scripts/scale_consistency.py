#!/usr/bin/env python3
"""角色身高/体型比例锁（R1·同框两人相对身高一致性）——补 shot_scale_contract 只测景别不测「谁比谁高」的盲区。

为什么单独一项：
  shot_scale_contract.py 只校验**单镜景别**（脸框面积=近景/中景/远景），它不关心两个同框角色
  之间的**相对身高**。但 AI 生图反复翻车的恰恰是这点——同一对人，这镜 A 比 B 高半头，下镜
  忽然 B 反超、或被画成等高。脸锁住、发型锁住、景别对了，相对身高仍能跨镜乱跳。本脚本对**同框
  ≥2 个已登记角色**的镜头，把渲染出的相对身高比和设定库登记的身高比对一对，揪出离谱的那几镜。

数据源（设定库登记，缺/坏则优雅跳过）：
  <root>/设定库/身高表.json → {"沈念": {"身高": 168, "体型": "纤细"}, "柳娘子": {"身高": 172}}
  身高单位任意但需全表一致（cm）；只取登记了身高的角色参与比对。

机制（诚实优先·只抓离谱偏差）：
  对每张含 ≥2 个**已登记**角色的镜头（角色集合取 fc.shot_character_map）：
    - 若有 insightface：检测所有人脸，**取面积最大的两张脸**的框高当各自身形比例代理，
      observed = 大/小（≥1）。
    - expected = 表里这两个角色身高的 大/小（≥1）。
    - 比对相对偏差 |observed-expected|/expected 落 ok/warn/block。

诚实边界（务必照实说，别假装精确）：
  这是**粗筛预检不是裁决**。三重不确定性叠在一起——(1) 脸框高只是身形的弱代理（透视/景别/
  机位距离都会放大缩小脸）；(2) 脸→角色身份**绑不准**（双人镜取两张最大脸，并不知道哪张是谁，
  故只能比「两人比例的量级」而非定向）；(3) 同框两人若一坐一站/一前一后景深差，比例天然失真。
  因此本门**只在比例量级离谱时报**（如表说两人约等高 ~1.0、渲染却一个头是另一个两倍），且**绝大多数
  只判 🟡 让人放大并排看**，仅在极端偏差（block_tol）才判 🔴。漏报（放过细微差）比误报代价低。
  无 insightface → available=False，整项优雅跳过交人判（脸框高度无 Pillow 廉价替代，不强凑）。

纯数学部分（expected_ratio / ratio_band）无依赖、带 pytest，便于无 GPU/无库环境验证逻辑。

用法：python3 scale_consistency.py <作品根> 第N集 [--warn-tol 0.25] [--block-tol 0.5] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

import face_consistency as fc      # shot_character_map / 资产发现（脸框检测复用 insightface 装载逻辑）

DEFAULT_WARN_TOL = 0.25            # 相对偏差 ≥ 此 → 🟡 轻度（人判并排看）
DEFAULT_BLOCK_TOL = 0.5           # 相对偏差 ≥ 此 → 🔴 离谱（一头≈另一头两倍量级）


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def expected_ratio(h_big: float, h_small: float) -> float:
    """两身高 → 较大/较小比（恒 ≥1）。自动摆正大小，不要求入参有序；
    任一身高 ≤0（缺/脏数据）→ 回退 1.0（视作无可比信息，下游 band 自然全 ok）。纯函数·可测。"""
    a, b = float(h_big), float(h_small)
    lo, hi = (a, b) if a <= b else (b, a)
    if lo <= 0:
        return 1.0
    return hi / lo


def ratio_band(observed: float, expected: float,
               warn_tol: float = DEFAULT_WARN_TOL,
               block_tol: float = DEFAULT_BLOCK_TOL) -> str:
    """渲染比 vs 登记比 → 档：'ok'/'warn'/'block'，按**相对偏差** |observed-expected|/expected。
    expected ≤0（无可比基准）→ 一律 ok（不臆判）。block_tol 优先于 warn_tol。纯函数·可测。"""
    if expected <= 0:
        return "ok"
    dev = abs(float(observed) - float(expected)) / float(expected)
    if dev >= block_tol:
        return "block"
    if dev >= warn_tol:
        return "warn"
    return "ok"


# ---------- 注册表 ----------

def load_height_table(root: str) -> Dict[str, Dict[str, object]]:
    """<root>/设定库/身高表.json → {角色: {"身高":float, "体型":str}}；缺/坏/格式不符 → {}（优雅跳过）。"""
    path = os.path.join(root, "设定库", "身高表.json")
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, Dict[str, object]] = {}
    for char, info in data.items():
        if not isinstance(info, dict):
            continue
        rec: Dict[str, object] = {}
        try:
            h = float(info.get("身高"))
        except (TypeError, ValueError):
            h = 0.0
        rec["身高"] = h
        build = info.get("体型")
        rec["体型"] = str(build) if isinstance(build, str) else ""
        out[str(char)] = rec
    return out


# ---------- 图像（需 insightface · 缺则跳过） ----------

def _two_largest_face_heights(app, png: str) -> Optional[Tuple[float, float]]:
    """检出图中所有脸，返回面积最大两张脸的**框高** (大高, 小高)；<2 张脸或读图失败 → None。"""
    try:
        import cv2  # type: ignore
        img = cv2.imread(png)
        if img is None:
            return None
        faces = app.get(img) or []
        if len(faces) < 2:
            return None
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        top2 = faces[:2]
        heights = sorted((float(f.bbox[3] - f.bbox[1]) for f in top2), reverse=True)
        return heights[0], heights[1]
    except Exception:
        return None


def analyze(root: str, ep: str,
            warn_tol: float = DEFAULT_WARN_TOL,
            block_tol: float = DEFAULT_BLOCK_TOL) -> dict:
    table = load_height_table(root)
    app = fc._load_embedder()
    res: dict = {"available": app is not None, "warn_tol": warn_tol, "block_tol": block_tol,
                 "shots": [], "notes": []}
    if app is None:
        res["notes"].append(
            "身高比例机检已跳过（未装 insightface/cv2）——同框两人相对身高漂移暂由人判并排读图覆盖。")
        return res
    if not table:
        res["notes"].append(
            "身高比例机检已跳过（设定库/身高表.json 缺失或为空）——补登记 {角色:{身高}} 后可启用同框相对身高对账。")
        return res

    smap = fc.shot_character_map(root, ep)
    for png, chars in sorted(smap.items()):
        # 仅看同框 ≥2 个**已登记身高**的角色镜
        regs = [c for c in chars if table.get(c, {}).get("身高", 0) and float(table[c]["身高"]) > 0]
        if len(regs) < 2:
            continue
        full = os.path.join(root, "出图", ep, png)
        if not os.path.exists(full):
            continue
        heights = _two_largest_face_heights(app, full)
        if heights is None:
            continue
        # 取登记身高最高/最低两人作期望比（与渲染「最大/最小两张脸」量级对齐；不定向绑身份）
        sorted_chars = sorted(regs, key=lambda c: float(table[c]["身高"]))
        c_small, c_big = sorted_chars[0], sorted_chars[-1]
        exp = expected_ratio(float(table[c_big]["身高"]), float(table[c_small]["身高"]))
        obs_big, obs_small = heights
        obs = obs_big / obs_small if obs_small > 0 else 1.0
        v = ratio_band(obs, exp, warn_tol, block_tol)
        if v != "ok":
            res["shots"].append({
                "png": png, "char_pair": [c_big, c_small],
                "observed": round(obs, 3), "expected": round(exp, 3),
                "verdict": v,
            })
    if not res["shots"]:
        res["notes"].append("未发现同框两人身高比例离谱镜（或本集无 ≥2 登记角色同框镜）。")
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--warn-tol", type=float, default=DEFAULT_WARN_TOL,
                    help="相对偏差 ≥ 此判 🟡（默认 0.25）")
    ap.add_argument("--block-tol", type=float, default=DEFAULT_BLOCK_TOL,
                    help="相对偏差 ≥ 此判 🔴（默认 0.5）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.warn_tol, ns.block_tol)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 身高/体型比例锁（R1·同框相对身高 · warn {res['warn_tol']} / block {res['block_tol']}）："
          f"{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    nblk = 0
    icon = {"block": "⛔身高离谱", "warn": "⚠️身高轻漂"}
    for s in res["shots"]:
        v = s["verdict"]
        if v == "block":
            nblk += 1
        a, b = s["char_pair"]
        print(f"{icon[v]} {s['png']} · {a}/{b} 渲染比 {s['observed']} vs 登记比 {s['expected']}")
    print(f"\n身高比例离谱 🔴 {nblk} · 共标出 {len(res['shots'])} 镜")
    return 1 if nblk else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
