#!/usr/bin/env python3
"""崩脸机检（自标定余弦 · flag-band）——n2d-review 模式①「一致性(角色)」的可脚本化兜底。

为什么不用单一硬阈值 0.45：
  ArcFace 同人余弦业界经验阈值 ≈0.5–0.68（真人 LFW 0.687@99.4%，见 insightface #2239 /
  sefiks ArcFace），且**因画风/模型而异**——漫剧是风格化脸，跨图余弦整体被压低，拿一个
  写死的数字判崩脸要么误杀要么放过。正确做法：用**本作定妆组自己的内部一致性**当地板
  （同一角色 正脸 vs 侧脸/半身 本就该高度相似 → 这条线就是"同一个人"的下限），再对每个
  镜头图打分、落到 🔴/🟡/🟢 三档，而不是一刀切。

机制：
  floor_c = 角色 c 定妆组内部互相余弦的最小值（front↔侧、front↔半身…）——同一人的下限。
  对镜头图 s（属角色 c）：score = cos(emb(s), emb(主参考_c))
    score ≥ floor_c            → 🟢 放行（不比定妆组内部更散）
    floor_c-margin ≤ score < floor_c → 🟡 轻漂（人判复核）
    score < floor_c-margin     → 🔴 崩脸/角色断层（回 n2d-image 重出）
  margin 默认 0.08（经验缓冲，可 --margin 调）。

依赖 insightface（缺则优雅跳过，不静默——交还人判清单）。本文件的**纯数学部分**
（cosine / calibrate_floor / band）无依赖、有 pytest 覆盖，便于在无 GPU/无库环境验证逻辑。

用法：
  python3 face_consistency.py <作品根> 第N集 [--margin 0.08] [--json]
  # 角色→镜头归属取自 出图/第N集/prompt/01_分镜出图.md 各镜「参考图」行引用的 定妆_<角色>。
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "common"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import shared_asset_path  # noqa: E402  共享定妆目录单一真值源

DEFAULT_MARGIN = 0.08

# 非角色类定妆名关键词（场景/道具/特效不参与脸相似度）——与 gate.py _section_has_character_refs 同源。
_NON_CHARACTER = (
    "场景", "道具", "寝殿", "宫", "殿", "庭", "院", "山", "洞", "门", "廊", "道",
    "床", "榻", "托盘", "光幕", "符纹", "剑气", "法宝", "特效", "阵", "丹炉", "炉",
    "雷", "火", "云", "光效", "地标", "花田", "花单株", "米饼", "灯", "剪影",
)


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """两向量余弦相似度；任一零向量返回 0.0。"""
    if len(a) != len(b):
        raise ValueError("dim mismatch")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def calibrate_floor(intra_scores: Sequence[float], fallback: float = 0.50) -> float:
    """从定妆组内部互相余弦标定"同一人下限"。

    取最小值（最严格的一对就是同人能掉到的最低线）；定妆组只有单张（无内部对）时
    回退到 fallback（经验同人下限 ~0.50，偏保守，宁可多报 🟡 让人判）。
    """
    vals = [s for s in intra_scores if s is not None]
    if not vals:
        return fallback
    return min(vals)


def band(score: float, floor: float, margin: float = DEFAULT_MARGIN) -> str:
    """落档：'ok'(🟢) / 'warn'(🟡) / 'block'(🔴)。"""
    if score >= floor:
        return "ok"
    if score >= floor - margin:
        return "warn"
    return "block"


# ---------- 嵌入（需 insightface · 缺则 None） ----------

def _load_embedder():
    try:
        from insightface.app import FaceAnalysis  # type: ignore
    except Exception:
        return None
    try:
        app = FaceAnalysis(name="buffalo_l")
        app.prepare(ctx_id=-1, det_size=(640, 640))
        return app
    except Exception:
        return None


def _embed(app, png: str) -> Optional[List[float]]:
    try:
        import cv2  # type: ignore
        img = cv2.imread(png)
        if img is None:
            return None
        faces = app.get(img)
        if not faces:
            return None
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        return list(map(float, faces[0].normed_embedding))
    except Exception:
        return None


# ---------- 资产发现 ----------

def is_character_asset(name: str) -> bool:
    return not any(k in name for k in _NON_CHARACTER)


def discover_costume_sets(root: str) -> Dict[str, Dict[str, str]]:
    """出图/共享/图片/定妆_<角色>[ _侧/_半身/_全身 ].png → {角色: {variant: path}}。仅角色类。"""
    sets: Dict[str, Dict[str, str]] = {}
    for p in glob.glob(os.path.join(shared_asset_path(root, "图片"), "定妆_*.png")):
        base = os.path.basename(p)[len("定妆_"):-len(".png")]
        # 三视图/设定表/表情是人审拼版，不作脸度量基准
        if any(t in base for t in ("三视图", "设定表", "表情")):
            continue
        m = re.match(r"^(.+?)(?:_(侧|半身|全身|背))?$", base)
        if not m:
            continue
        char, variant = m.group(1), (m.group(2) or "主")
        if not is_character_asset(char):
            continue
        sets.setdefault(char, {})[variant] = p
    return sets


def shot_character_map(root: str, ep: str) -> Dict[str, List[str]]:
    """每镜 PNG → 引用的角色列表（取自 01_分镜出图.md「参考图」行的 定妆_<角色>）。"""
    prompt = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    out: Dict[str, List[str]] = {}
    if not os.path.isfile(prompt):
        return out
    text = open(prompt, encoding="utf-8").read()
    blocks = re.split(r"(?m)(?=^## )", text)
    for blk in blocks:
        head = blk.splitlines()[0] if blk.strip() else ""
        mt = re.search(r"出图/[^/]+/([^`』\s]+\.png)", blk)  # 目标 PNG
        if not mt:
            continue
        png = mt.group(1)
        chars = []
        for ref in re.findall(r"定妆_([^`\s，。、,）)]+)", _ref_block(blk)):
            if ref.endswith(".png"):
                ref = ref[:-4]
            ref = re.sub(r"_(侧|半身|全身|背|三视图|设定表|表情)$", "", ref)
            if is_character_asset(ref) and ref not in chars:
                chars.append(ref)
        if chars:
            out[png] = chars
    return out


def _ref_block(section: str) -> str:
    m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^##\s+|\Z)", section)
    return m.group(0) if m else ""


# ---------- 主流程 ----------

def analyze(root: str, ep: str, margin: float = DEFAULT_MARGIN) -> dict:
    sets = discover_costume_sets(root)
    app = _load_embedder()
    result: dict = {"available": app is not None, "margin": margin, "characters": {}, "shots": [], "notes": []}
    if app is None:
        result["notes"].append(
            "脸部相似度度量已跳过（未装 insightface/cv2）——崩脸暂由人判清单(references/checklist.md)并排读图覆盖。")
        return result

    # 1) 每角色定妆组自标定 floor
    char_floor: Dict[str, float] = {}
    char_main_emb: Dict[str, List[float]] = {}
    for char, variants in sets.items():
        embs = {v: _embed(app, p) for v, p in variants.items()}
        main = embs.get("主")
        intra = []
        if main is not None:
            char_main_emb[char] = main
            for v, e in embs.items():
                if v != "主" and e is not None:
                    intra.append(cosine(main, e))
        floor = calibrate_floor(intra)
        char_floor[char] = floor
        result["characters"][char] = {"floor": round(floor, 4), "intra_pairs": len(intra),
                                      "has_main": main is not None}

    # 2) 每镜 vs 其角色主参考
    smap = shot_character_map(root, ep)
    for png, chars in sorted(smap.items()):
        full = os.path.join(root, "出图", ep, png)
        if not os.path.exists(full):
            continue
        emb = _embed(app, full)
        if emb is None:
            result["shots"].append({"png": png, "verdict": "noface", "chars": chars})
            continue
        worst = None
        for c in chars:
            if c in char_main_emb:
                sc = cosine(emb, char_main_emb[c])
                fl = char_floor.get(c, 0.50)
                v = band(sc, fl, margin)
                row = {"char": c, "score": round(sc, 4), "floor": round(fl, 4), "verdict": v}
                if worst is None or _sev(v) > _sev(worst["verdict"]):
                    worst = row
        if worst:
            result["shots"].append({"png": png, **worst})
    return result


def _sev(v: str) -> int:
    return {"block": 3, "warn": 2, "ok": 1, "noface": 0}.get(v, 0)


# ---------- N3：定妆主参考自身质量门（锚点不能脏） ----------

def anchor_verdict(face_count: int, box_ratio: float, min_ratio: float = 0.06) -> str:
    """定妆主参考是否够格当锚点。锚点一脏，下游每镜继承错误。
    - face_count==0 → block（锚点没脸，没法当锁脸基准）
    - face_count>1  → block（多张脸，下游不知锁谁）
    - 0<box_ratio<min_ratio → warn（脸太小，锁脸信息不足）
    - 否则 ok"""
    if face_count == 0:
        return "block"
    if face_count > 1:
        return "block"
    if box_ratio < min_ratio:
        return "warn"
    return "ok"


def audit_anchors(root: str, min_ratio: float = 0.06) -> dict:
    """审 出图/共享/图片/定妆_<角色>.png 主参考：恰好 1 张清晰、够大的正脸。"""
    sets = discover_costume_sets(root)
    app = _load_embedder()
    out: dict = {"available": app is not None, "anchors": [], "notes": []}
    if app is None:
        out["notes"].append("锚点质量门已跳过（未装 insightface/cv2）——主参考是否单张清晰正脸暂由人判。")
        return out
    try:
        import cv2  # type: ignore
    except Exception:
        out["available"] = False
        out["notes"].append("锚点质量门已跳过（未装 cv2）。")
        return out
    for char, variants in sorted(sets.items()):
        main = variants.get("主")
        if not main:
            continue
        full = main if os.path.isabs(main) else os.path.join(root, main)
        try:
            img = cv2.imread(full)
            if img is None:
                out["anchors"].append({"char": char, "verdict": "block", "reason": "读不到 PNG"})
                continue
            h, w = img.shape[:2]
            faces = app.get(img)
            n = len(faces)
            ratio = 0.0
            if n:
                f = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
                ratio = ((f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1])) / float(w*h)
            v = anchor_verdict(n, ratio, min_ratio)
            out["anchors"].append({"char": char, "faces": n, "box_ratio": round(ratio, 4), "verdict": v})
        except Exception as e:
            out["anchors"].append({"char": char, "verdict": "warn", "reason": f"检测异常 {e}"})
    return out


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument("--audit-anchor", action="store_true", help="N3：只审定妆主参考自身质量（单张清晰正脸）")
    ap.add_argument("--cross-ep", action="store_true", help="⑦：逐集跑崩脸机检，汇总每集 🔴/🟡，找出跨集开始漂的那一集")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.cross_ep:
        import glob as _glob
        root = ns.root.rstrip("/")
        eps = sorted(os.path.basename(os.path.dirname(d))
                     for d in _glob.glob(os.path.join(root, "出图", "第*集", "图片")))
        rows = []
        for ep in eps:
            r = analyze(root, ep, ns.margin)
            if not r.get("available"):
                rows.append({"episode": ep, "skipped": True}); continue
            vs = [s.get("verdict") for s in r.get("shots", [])]
            rows.append({"episode": ep, "block": vs.count("block"), "warn": vs.count("warn"),
                         "n": sum(1 for v in vs if v != "noface")})
        out = {"root": root, "cross_ep": rows}
        if ns.json:
            print(json.dumps(out, ensure_ascii=False, indent=2)); return 0
        print(f"=== 跨集人物一致性（逐集崩脸·同一共享定妆基准）：{root} ===")
        if rows and rows[0].get("skipped"):
            print("ℹ️ 未装 insightface——跨集人物一致性逐集机检跳过，交人判（共享定妆已大部覆盖）。"); return 0
        for r in rows:
            print(f"  {r['episode']}: 🔴 {r.get('block',0)} · 🟡 {r.get('warn',0)} （评 {r.get('n',0)} 镜）")
        worst = max((r for r in rows if not r.get("skipped")), key=lambda r: r.get("block", 0), default=None)
        if worst and worst.get("block", 0) > 0:
            print(f"\n⚠️ 跨集漂移高发：{worst['episode']}（🔴 {worst['block']}）——优先回 n2d-image 查该集是否换了定妆/混了后端")
        return 1 if any(r.get("block", 0) for r in rows) else 0
    if ns.audit_anchor:
        a = audit_anchors(ns.root.rstrip("/"))
        if ns.json:
            print(json.dumps(a, ensure_ascii=False, indent=2)); return 0
        print(f"=== 定妆主参考质量门 (N3)：{ns.root} ===")
        for n in a["notes"]:
            print("ℹ️ " + n)
        nb = 0
        icon = {"block": "⛔", "warn": "⚠️", "ok": "✅"}
        for r in a["anchors"]:
            if r["verdict"] == "block":
                nb += 1
            if r["verdict"] != "ok":
                print(f"{icon.get(r['verdict'],'?')} 定妆_{r['char']}: {r.get('reason') or ('faces='+str(r.get('faces'))+' box_ratio='+str(r.get('box_ratio')))}")
        print(f"\n锚点不合格 🔴 {nb} · 共审 {len(a['anchors'])}")
        return 1 if nb else 0
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.margin)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print(f"=== 崩脸机检（自标定 flag-band · margin {res['margin']}）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    if not res["available"]:
        return 0
    for c, info in res["characters"].items():
        print(f"  角色 {c}: floor={info['floor']}（定妆组内部对 {info['intra_pairs']}）")
    icon = {"block": "⛔崩脸", "warn": "⚠️轻漂", "ok": "✅", "noface": "·无脸"}
    nblock = 0
    for s in res["shots"]:
        v = s.get("verdict", "noface")
        if v == "block":
            nblock += 1
        if v in ("block", "warn"):
            print(f"{icon[v]} {s['png']} · {s.get('char','?')} score={s.get('score')} < floor={s.get('floor')}")
    print(f"\n崩脸 🔴 {nblock} · 共评 {len(res['shots'])} 镜")
    return 1 if nblock else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
