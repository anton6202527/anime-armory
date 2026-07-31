#!/usr/bin/env python3
"""像素级 180°轴线/视线/眼神核验（X1·轴线视线几何）——把只机检「prompt 里写没写」升级成「图里对不对」。

为什么补这条轴：
  契约字段 `场景轴线视线` 至今只被 image_qc lint 测【prompt 文本里有没有这一行】——写了就过，
  画歪了一样过。可「越轴」（180°轴线被跨过）是连续镜头里最经典的穿帮：上一镜角色脸朝右、镜头一
  切人忽然朝左，或同一人物在屏幕上的左右位置无端跳边，观众瞬间出戏。这类几何错误纯文本永远测不到，
  必须落到像素：从每镜人脸估「他朝哪边 / 屏幕 X 在哪侧」，同场景内某镜朝向反转或主体跳边 → 标出。

机制（诚实初筛·只抓朝向反转，不下裁决）：
  从 insightface 的人脸关键点（kps 5 点：双眼/鼻/双嘴角）取**鼻尖相对双眼中点的横向偏移**，
  按瞳距归一 → 朝向 facing ∈[-1,1]：鼻偏向哪侧脸就朝哪侧（侧脸时鼻尖明显偏离眼中点）；另用
  脸框中心 X / 图宽得屏幕侧（左/中/右）。把同一角色按镜号排成序列，相邻两镜朝向**明确反转**
  （两镜都非正脸且符号相反）或**同一角色屏幕跳边** → 该镜越轴可疑。

为什么 warn-only、永不 block：
  正脸/近正脸朝向本就模糊（deadzone 内判 0，不报）；而「故意切反打镜头 / 过肩反打 / 镜头绕轴
  运动」都会合法地让朝向反转——误报率天然高。所以越轴一律 🟡（人放大看是不是真穿帮），绝不自动
  挡、绝不自动改图。漏报（放过一次越轴）代价远低于误杀一组合法反打。

依赖 insightface（缺则优雅跳过，交人判清单）。复用 face_consistency 的 shot_character_map 取每镜
主检角色。本文件的**纯数学部分**（facing_from_kps / facing_sign / screen_side / axis_break /
axis_band）无依赖、有 pytest 覆盖，便于无 GPU/无库环境验证逻辑。

用法：python3 axis_geometry.py <作品根> 第N集 [--deadzone 0.08] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import face_consistency as fc  # 复用 shot_character_map（每镜→主检角色）

DEFAULT_DEADZONE = 0.08   # |facing| < 此值 → 视作近正脸（朝向模糊），永不参与越轴判定
SIDE_DEADZONE = 0.10      # 脸框中心偏离画面中线 < 此比例 → 视作居中（不算明确左/右）


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def facing_from_kps(left_eye_x: float, right_eye_x: float, nose_x: float) -> float:
    """由人脸关键点估朝向：鼻尖相对双眼中点的横向偏移，按瞳距归一 → signed ∈[-1,1]。

    正脸时鼻尖≈双眼中点（值≈0）；转向一侧时鼻尖朝那侧偏出眼中点。约定：
      返回 < 0 → 朝屏幕左（鼻尖在眼中点左侧）；> 0 → 朝屏幕右。
    瞳距为 0（双眼重合/退化关键点，无尺度）→ 返回 0.0（不臆造朝向）。纯函数·可测。
    """
    inter_eye = abs(right_eye_x - left_eye_x)
    if inter_eye == 0.0:
        return 0.0
    eye_mid = (left_eye_x + right_eye_x) / 2.0
    val = (nose_x - eye_mid) / inter_eye
    if val < -1.0:
        return -1.0
    if val > 1.0:
        return 1.0
    return val


def facing_sign(value: float, deadzone: float = DEFAULT_DEADZONE) -> int:
    """朝向连续值 → 离散符号：-1 朝左 / +1 朝右 / 0 近正脸（模糊·永不参与越轴判定）。

    deadzone 是「正脸不算朝向」的缓冲——|value| 落在带内归 0，这一镜不会触发也不会被判越轴。
    纯函数·可测。"""
    if value <= -deadzone:
        return -1
    if value >= deadzone:
        return 1
    return 0


def screen_side(box_center_x: float, img_w: float, deadzone: float = SIDE_DEADZONE) -> int:
    """脸框中心 X 落在画面左/中/右：-1 左 / 0 中 / +1 右。

    偏离画面中线小于 img_w*deadzone → 居中（0，不算明确左/右，避免轻微构图抖动误判跳边）。
    img_w<=0（无尺度）→ 0。纯函数·可测。"""
    if img_w <= 0:
        return 0
    offset = (box_center_x - img_w / 2.0) / img_w   # ∈(-0.5,0.5)
    if offset <= -deadzone:
        return -1
    if offset >= deadzone:
        return 1
    return 0


def axis_break(prev_sign: int, prev_side: int, cur_sign: int, cur_side: int) -> bool:
    """同一角色相邻两镜是否越轴（180°轴线被跨）。两类判 True，其余 False：

      1) 朝向明确反转：prev_sign 与 cur_sign 都非 0（都不是正脸）且符号相反——人脸从朝左切成
         朝右（或反之），是教科书式越轴。正脸（任一为 0）模糊，不判。
      2) 屏幕跳边：prev_side 与 cur_side 都非 0（都明确在一侧）且相反——同一人物无端从画左跳到
         画右（或反之），缺建立镜头时即越轴的另一表征。居中（任一为 0）不判。

    任一成立即 True。两条都用「双方非 0 且相反」，把正脸/居中这种模糊态全排除，宁漏勿误。
    纯函数·可测。"""
    facing_reversed = prev_sign != 0 and cur_sign != 0 and prev_sign != cur_sign
    side_jumped = prev_side != 0 and cur_side != 0 and prev_side != cur_side
    return bool(facing_reversed or side_jumped)


def axis_band(num_breaks_for_shot: int) -> str:
    """该镜检出的越轴数 → 档。检出越轴一律 🟡 warn，永不 block。

    理由见模块 docstring：故意反打 / 过肩反打 / 绕轴运镜都会合法反转朝向，误报率高——越轴只作
    「这镜请人放大看是不是真穿帮」的提示，绝不自动挡、不自动返工。num_breaks_for_shot<=0 → ok。
    纯函数·可测。"""
    return "warn" if num_breaks_for_shot > 0 else "ok"


# ---------- 图像（需 insightface · 缺则跳过） ----------

def _shot_index(png_basename: str) -> Tuple[int, str]:
    """从 PNG 文件名解析镜号用于排序（取文件名里第一段数字）；无数字 → 落到末尾。"""
    m = re.search(r"(\d+)", os.path.basename(png_basename))
    n = int(m.group(1)) if m else 1_000_000
    return (n, os.path.basename(png_basename))


def _largest_face_geometry(app, png: str) -> Optional[Tuple[float, int]]:
    """对一张图取**面积最大的人脸**，返回 (facing_value, screen_side)；无脸/读图失败 → None。

    facing 由 kps（左眼、右眼、鼻）算；screen_side 由脸框中心 X / 图宽算。kps 缺失 → None。
    """
    try:
        import cv2  # type: ignore
    except Exception:
        return None
    try:
        img = cv2.imread(png)
        if img is None:
            return None
        h, w = img.shape[:2]
        faces = app.get(img) or []
        if not faces:
            return None
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        f = faces[0]
        kps = getattr(f, "kps", None)
        if kps is None or len(kps) < 3:
            return None
        left_eye_x = float(kps[0][0])
        right_eye_x = float(kps[1][0])
        nose_x = float(kps[2][0])
        facing = facing_from_kps(left_eye_x, right_eye_x, nose_x)
        box_cx = float((f.bbox[0] + f.bbox[2]) / 2.0)
        side = screen_side(box_cx, float(w))
        return facing, side
    except Exception:
        return None


def analyze(root: str, ep: str, deadzone: float = DEFAULT_DEADZONE) -> dict:
    app = fc._load_embedder()
    res: dict = {"available": app is not None, "deadzone": deadzone, "shots": [], "notes": []}
    if app is None:
        res["notes"].append(
            "轴线/视线几何机检已跳过（未装 insightface）——越轴(180°)暂由人判清单并排读连续镜头覆盖。")
        return res

    smap = fc.shot_character_map(root, ep)
    if not smap:
        res["notes"].append("本集无可解析的镜头→角色映射（缺 prompt/storyboard）。")
        return res

    # 每镜取最大脸的朝向+屏幕侧，按角色聚成镜号序列
    per_char: Dict[str, List[Tuple[Tuple[int, str], str, int, int]]] = {}
    for png, chars in smap.items():
        full = os.path.join(root, "出图", ep, png)
        if not os.path.exists(full):
            continue
        geom = _largest_face_geometry(app, full)
        if geom is None:
            continue
        facing_val, side = geom
        sign = facing_sign(facing_val, deadzone)
        for c in chars:
            per_char.setdefault(c, []).append((_shot_index(png), png, sign, side))

    for char, rows in per_char.items():
        rows.sort(key=lambda r: r[0])
        prev_sign: Optional[int] = None
        prev_side: Optional[int] = None
        for _, png, sign, side in rows:
            if prev_sign is not None and prev_side is not None:
                if axis_break(prev_sign, prev_side, sign, side):
                    res["shots"].append({
                        "png": os.path.basename(png), "char": char,
                        "facing": sign, "side": side, "verdict": "warn",
                    })
            prev_sign, prev_side = sign, side
    return res


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--deadzone", type=float, default=DEFAULT_DEADZONE)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.deadzone)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"=== 轴线/视线几何机检（X1·180°越轴初筛·deadzone {res['deadzone']}）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    _arrow = {-1: "←朝左", 0: "·正脸", 1: "朝右→"}
    _sidew = {-1: "画左", 0: "居中", 1: "画右"}
    for s in res["shots"]:
        print(f"⚠️ {s['png']} · {s['char']} 朝向{_arrow.get(s['facing'],'?')}/{_sidew.get(s['side'],'?')}"
              f"（疑越轴：相对上一镜同角色朝向反转或跳边，请人核是不是合法反打）")
    print(f"\n越轴疑似 🟡 {len(res['shots'])} 镜（warn-only·永不自动挡，故意反打/绕轴会误报）")
    return 0  # warn-only 检测器：永不返回非零


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
