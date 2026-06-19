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
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)
from n2d_contract import shared_asset_path  # noqa: E402  共享定妆目录单一真值源

DEFAULT_MARGIN = 0.08
IDENTITY_REF_RE = re.compile(r"`?(CHAR_[A-Za-z0-9_]+\*?(?:/[^`\s，；、*]+)?\*?)`?")

# ── Pillow 降级档（无 insightface 时的基础机检）────────────────────────────
# 只做四件事：图存在 / 可解码 / 分辨率达标 / 清晰度（PIL+stdlib 近似 Laplacian 方差）。
# 绝不输出假相似度——结果标 mode="pillow_fallback" + precision="insufficient_precision"，
# 让 n2d-score G1 消费端给降权分而不是整维度 insufficient_data。
PILLOW_FALLBACK_MODE = "pillow_fallback"
PILLOW_MIN_SHORT_SIDE = 512          # 分辨率达标线：短边像素
PILLOW_SHARPNESS_FLOOR = 25.0        # 清晰度地板：降采样后 Laplacian 方差经验值
PILLOW_PROBE_MAX_SIDE = 256          # 清晰度探测降采样上限（控制纯 Python 卷积成本）

# 非角色类定妆名关键词（场景/道具/特效不参与脸相似度）——与 gate.py _section_has_character_refs 同源。
_NON_CHARACTER = (
    "场景", "道具", "寝殿", "冷宫", "皇宫", "寝宫", "殿", "庭", "院", "山", "洞", "门", "廊", "道",
    "床", "榻", "托盘", "光幕", "符纹", "剑气", "法宝", "特效", "阵", "丹炉", "炉",
    "雷", "火", "云", "光效", "地标", "花田", "花单株", "米饼", "灯", "剪影",
    "铜镜", "镜框", "毒酒", "碎瓷", "瓷", "脉冲", "妖力",
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


def best_anchor_score(emb: Sequence[float], variant_embs: Sequence[Sequence[float]]) -> Optional[float]:
    """镜头脸 vs 该角色【全部定妆视图】（主/侧/背/半身…）余弦的**最大值**（P3 角度感知）。

    只比主参考(正脸)时，侧/背/大角度的同人镜余弦天然低、卡在 floor 边缘易误报 🟡。改取"对任一
    canonical 视图最像即可"：真同人换角度 → 命中对应视图 → 高分放行；真崩脸 → 对哪个视图都不像 →
    仍低分被抓。不需逐镜判角度。无可用 variant → None。纯函数·可测。"""
    vals = [cosine(emb, e) for e in variant_embs if e]
    return max(vals) if vals else None


def best_face_match(
    face_embs: Sequence[Sequence[float]],
    main_emb: Sequence[float],
    variant_embs: Sequence[Sequence[float]],
) -> Optional[Tuple[float, float, int]]:
    """多脸镜中，为目标角色选择最像其定妆组的那张脸。

    旧逻辑只取画面最大脸；双人接触镜里若受击者/反应者脸更大，会把那张脸拿去比主角，
    造成误判。这里对所有检测到的人脸逐一与目标角色多角度锚点比对，返回
    (best_of_variants, score_vs_main, face_idx)。
    """
    best: Optional[Tuple[float, float, int]] = None
    anchors = list(variant_embs or [main_emb])
    for idx, emb in enumerate(face_embs):
        sc = best_anchor_score(emb, anchors)
        if sc is None:
            continue
        sc_main = cosine(emb, main_emb)
        if best is None or sc > best[0]:
            best = (sc, sc_main, idx)
    return best


def floor_calibrated(intra_scores: Sequence[float]) -> bool:
    """定妆组是否有内部对可自标定地板（≥1 对）。单张/无对 → False：地板退回保守经验值 0.50，
    风格化漫剧脸跨图余弦常 <0.5 会系统性误报——此时标低精度，让 n2d-score 像 pillow_fallback 那样降权而非硬判。"""
    return any(s is not None for s in intra_scores)


def episode_mean(scores: Sequence[Optional[float]]) -> Optional[float]:
    """本集某角色所有镜「脸 vs 共享定妆主参考」余弦的均值（角色本集质心相对锚点的接近度）。
    无样本→None。纯函数·可测。"""
    vals = [float(s) for s in scores if s is not None]
    return round(sum(vals) / len(vals), 4) if vals else None


def cross_episode_drift(
    per_ep_mean: Sequence[Tuple[str, Optional[float]]],
    *,
    drop_warn: float = 0.08,
    drop_block: float = 0.15,
    abs_low: float = 0.45,
) -> List[dict]:
    """单角色跨集 embedding 漂移检测（治"每集各自过 floor、但整体逐集偏离锚点"的系统性漂移）。

    入参 per_ep_mean 是该角色按集**时间序**的 (集, 本集均值)；均值=本集脸 vs 共享定妆主参考的平均余弦。
    基线=首个有样本的集（建立参考的那一集）。对其后每一集：相对基线掉幅 ≥ drop_block 或本集均值 < abs_low
    → severity=high；掉幅 ≥ drop_warn → medium。返回 episode_from/to 漂移条目（对齐 voice 线结构）。
    纯数学，不依赖 insightface，可单测。"""
    entries: List[dict] = []
    seq = [(ep, float(m)) for ep, m in per_ep_mean if m is not None]
    if len(seq) < 2:
        return entries
    base_ep, base_mean = seq[0]
    for ep, m in seq[1:]:
        drop = round(base_mean - m, 4)
        below_low = m < abs_low
        if drop >= drop_block or below_low:
            sev = "high"
        elif drop >= drop_warn:
            sev = "medium"
        else:
            continue
        entries.append({
            "episode_from": base_ep, "episode_to": ep,
            "from_mean": round(base_mean, 4), "to_mean": round(m, 4),
            "drop": drop, "below_abs_low": below_low, "severity": sev,
        })
    return entries


def detect_face_swaps(face_embs: Sequence[Sequence[float]],
                      expected_char_embs: Dict[str, Sequence[float]]) -> dict:
    """同框多角色串脸检测：把每张检出的脸归到余弦最高的应在场角色，揪出"张冠李戴"。

    单脸 worst-of 只把【最大那张脸】vs 各角色各比一次取最差，测不出"A 长了 B 的五官"。这里对【所有】脸
    做分配匹配：每张脸 argmax 余弦归到一个 expected 角色，于是能抓两类同框穿帮——
      - duplicate_chars：同一角色被 ≥2 张脸认领 = 两个人都被画成同一人（串脸）；
      - missing_chars：某应在场角色没有任何脸像他 = 该角色画丢/画成了别人。
    纯数学（余弦），不依赖 insightface，可单测；embedding 抽取在 analyze 里用 insightface 喂进来。
    """
    chars = [c for c, e in expected_char_embs.items() if e]
    assignments = []
    claimed: Dict[str, int] = {}
    for i, fe in enumerate(face_embs):
        if not fe or not chars:
            continue
        best_c, best_s = None, -2.0
        for c in chars:
            s = cosine(fe, expected_char_embs[c])
            if s > best_s:
                best_c, best_s = c, s
        assignments.append({"face_idx": i, "char": best_c, "score": round(best_s, 4)})
        claimed[best_c] = claimed.get(best_c, 0) + 1
    duplicate_chars = sorted(c for c, n in claimed.items() if n >= 2)
    missing_chars = sorted(c for c in chars if claimed.get(c, 0) == 0)
    return {
        "assignments": assignments,
        "duplicate_chars": duplicate_chars,   # 串脸：多张脸都最像同一角色
        "missing_chars": missing_chars,       # 该在场角色没有脸像他
        "swap_suspected": bool(duplicate_chars and missing_chars),  # 一多一少 = 典型 A 画成 B
    }


def band(score: float, floor: float, margin: float = DEFAULT_MARGIN) -> str:
    """落档：'ok'(🟢) / 'warn'(🟡) / 'block'(🔴)。"""
    if score >= floor:
        return "ok"
    if score >= floor - margin:
        return "warn"
    return "block"


def laplacian_variance(pixels: Sequence[int], w: int, h: int) -> float:
    """灰度像素 4-邻域拉普拉斯响应方差（无 cv2 时用 PIL+stdlib 近似 cv2.Laplacian().var()）。

    纯数学、无依赖、可测；值越低越糊。图太小（<3×3）没有内点，返回 0.0。
    """
    if w < 3 or h < 3 or len(pixels) != w * h:
        return 0.0
    vals: List[float] = []
    for y in range(1, h - 1):
        base = y * w
        for x in range(1, w - 1):
            i = base + x
            vals.append(float(4 * pixels[i] - pixels[i - 1] - pixels[i + 1] - pixels[i - w] - pixels[i + w]))
    n = len(vals)
    mean = sum(vals) / n
    return sum((v - mean) ** 2 for v in vals) / n


def pillow_shot_verdict(
    decodable: bool,
    width: int = 0,
    height: int = 0,
    sharpness: Optional[float] = None,
    *,
    min_short_side: int = PILLOW_MIN_SHORT_SIDE,
    sharpness_floor: float = PILLOW_SHARPNESS_FLOOR,
) -> Tuple[str, List[str]]:
    """Pillow 降级档逐镜判定（纯函数·可测）。

    只判 可解码/分辨率/清晰度，不碰相似度：
      - 不可解码 → block（图坏了，必须重出）
      - 分辨率不达标 / 清晰度低 → warn（标给人判，降级档不武断 🔴）
      - 全过 → ok（仅指基础质量过关，不代表脸一致——precision 不足）
    """
    if not decodable:
        return "block", ["图损坏或不可解码"]
    reasons: List[str] = []
    short = min(width, height)
    if short < min_short_side:
        reasons.append(f"分辨率不足（短边 {short} < {min_short_side}）")
    if sharpness is not None and sharpness < sharpness_floor:
        reasons.append(f"清晰度偏低（laplacian_var {sharpness:.1f} < {sharpness_floor:g}，疑糊图）")
    return ("warn", reasons) if reasons else ("ok", [])


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


def _load_pillow():
    try:
        from PIL import Image  # type: ignore
        return Image
    except Exception:
        return None


def cv2_face_boxes(png: str) -> Optional[List[Tuple[int, int, int, int]]]:
    """OpenCV Haar 正脸检测 → 人脸框 [(x,y,w,h)]；无 cv2/级联/读图失败 → None（区别于 []=检测到 0 脸）。

    几何粗筛专用：**只判『有没有脸/几张脸』，绝不输出同人相似度**。风格化漫剧脸 Haar 漏检率高，
    故检测结果仅作降级档人审优先级提示（0 脸=疑崩脸/遮挡，多脸=疑串入他人），不下 verdict、不当
    block——这是 insightface 缺席、Pillow 又只能验图损坏时，介于两者之间的一层 precision=geometric 信号。
    """
    try:
        import cv2  # type: ignore
    except Exception:
        return None
    try:
        clf = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if clf.empty():
            return None
        img = cv2.imread(png)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = clf.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48))
        return [tuple(int(v) for v in f) for f in faces]
    except Exception:
        return None


def _pillow_probe(image_mod, png: str) -> Optional[Tuple[int, int, float]]:
    """读图 → (宽, 高, 清晰度)；不可解码返回 None。降采样后做纯 Python Laplacian。"""
    try:
        with image_mod.open(png) as im:
            w, h = im.size
            gray = im.convert("L")
            gray.thumbnail((PILLOW_PROBE_MAX_SIDE, PILLOW_PROBE_MAX_SIDE))
            sw, sh = gray.size
            pixels = list(gray.getdata())
        return w, h, laplacian_variance(pixels, sw, sh)
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


def _embed_all(app, png: str) -> List[List[float]]:
    """检出图中【所有】人脸的 embedding（按脸面积降序）——多人同框串脸检测用。"""
    try:
        import cv2  # type: ignore
        img = cv2.imread(png)
        if img is None:
            return []
        faces = app.get(img) or []
        faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
        return [list(map(float, f.normed_embedding)) for f in faces]
    except Exception:
        return []


# ---------- 资产发现 ----------

def is_character_asset(name: str) -> bool:
    return not any(k in name for k in _NON_CHARACTER)


def registered_character_assets(root: str) -> Set[str]:
    """identity_registry.json → registered character asset_key set."""
    path = os.path.join(root, "出图", "共享", "identity_registry.json")
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return set()
    out: Set[str] = set()
    for ch in data.get("characters") or []:
        for form in ch.get("forms") or []:
            if not isinstance(form, dict):
                continue
            asset = str(form.get("asset_key") or "").strip()
            if asset:
                out.add(asset)
    return out


def _resolve_project_path(root: str, path: str) -> str:
    """Resolve a project asset path without duplicating an already-prefixed root.

    Some callers pass paths returned by shared_asset_path(root, ...). When root
    itself is relative, glob returns values like "root/出图/共享/...", not bare
    project-relative paths. Joining those with root again produces
    "root/root/出图/共享/...", which makes existing anchors look missing.
    """
    text = str(path or "").strip()
    if not text:
        return text
    norm = os.path.normpath(text)
    if os.path.isabs(norm):
        return norm
    root_norm = os.path.normpath(str(root).rstrip(os.sep) or ".")
    if norm == root_norm or norm.startswith(root_norm + os.sep):
        return norm
    root_abs = os.path.abspath(root_norm)
    norm_abs = os.path.abspath(norm)
    if norm_abs == root_abs or norm_abs.startswith(root_abs + os.sep):
        return norm
    return os.path.join(root_norm, norm)


def discover_costume_sets(root: str) -> Dict[str, Dict[str, str]]:
    """出图共享定妆图 → {角色形态: {variant: path}}。仅角色类。

    新项目优先从 identity_registry 的 reference_group/reference_atlas 读取全套锚点，
    覆盖 45 度与脸部特写；旧项目再回退扫描文件名。
    """
    registered_sets = discover_costume_sets_from_registry(root)
    if registered_sets:
        return registered_sets
    sets: Dict[str, Dict[str, str]] = {}
    registered = registered_character_assets(root)
    for p in glob.glob(os.path.join(shared_asset_path(root, "图片"), "定妆_*.png")):
        base = os.path.basename(p)[len("定妆_"):-len(".png")]
        # 三视图/设定表/表情是人审拼版，不作脸度量基准
        if any(t in base for t in ("三视图", "设定表", "表情")):
            continue
        m = re.match(r"^(.+?)(?:_(45度|侧|半身|全身|背|脸部特写))?$", base)
        if not m:
            continue
        char, variant = m.group(1), (m.group(2) or "主")
        if registered:
            if char not in registered:
                continue
        elif not is_character_asset(char):
            continue
        sets.setdefault(char, {})[variant] = p
    return sets


def discover_costume_sets_from_registry(root: str) -> Dict[str, Dict[str, str]]:
    """identity_registry.json → face-consistency anchor sets."""
    path = os.path.join(root, "出图", "共享", "identity_registry.json")
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, Dict[str, str]] = {}
    for ch in data.get("characters") or []:
        for form in ch.get("forms") or []:
            if not isinstance(form, dict):
                continue
            asset = str(form.get("asset_key") or "").strip()
            if not asset:
                continue
            variants: Dict[str, str] = {}
            for name, rel in registry_variant_paths(form).items():
                full = _resolve_project_path(root, rel)
                if os.path.isfile(full):
                    variants[name] = full
            if variants:
                out[asset] = variants
    return out


def registry_variant_paths(form: Mapping[str, object]) -> Dict[str, str]:
    """Extract canonical face anchor paths from a character form registry entry."""
    out: Dict[str, str] = {}

    def add(name: str, raw: object) -> None:
        if isinstance(raw, str) and raw.strip():
            out.setdefault(name, raw.strip())

    ref = form.get("reference_group") if isinstance(form, dict) else {}
    if isinstance(ref, dict):
        add("主", ref.get("front"))
        add("45度", ref.get("three_quarter"))
        add("侧", ref.get("side"))
        add("背", ref.get("back"))
        add("半身", ref.get("outfit") or ref.get("half_body"))
        for item in ref.get("face_anchor_refs") or []:
            if isinstance(item, dict):
                add("脸部特写", item.get("path"))

    atlas = form.get("reference_atlas") if isinstance(form, dict) else {}
    if isinstance(atlas, dict):
        views = atlas.get("base_views") or {}
        if isinstance(views, dict):
            add("主", (views.get("front") or {}).get("path") if isinstance(views.get("front"), dict) else None)
            add("45度", (views.get("three_quarter") or {}).get("path") if isinstance(views.get("three_quarter"), dict) else None)
            add("侧", (views.get("side") or {}).get("path") if isinstance(views.get("side"), dict) else None)
            add("背", (views.get("back") or {}).get("path") if isinstance(views.get("back"), dict) else None)
            add("半身", (views.get("half_body") or {}).get("path") if isinstance(views.get("half_body"), dict) else None)
        for item in atlas.get("face_anchor_refs") or []:
            if isinstance(item, dict):
                add("脸部特写", item.get("path"))
    return out


def identity_asset_map(root: str) -> Dict[str, str]:
    """identity_registry.json → {CHAR_ID/形态: asset_key}.

    Face QC should judge the primary on-screen identity from the prompt's
    资产身份注册层 when available. Reference blocks can include background
    reaction anchors; treating every reference as the largest-face owner creates
    false hard blocks for ECU/object shots.
    """
    path = os.path.join(root, "出图", "共享", "identity_registry.json")
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for ch in data.get("characters") or []:
        cid = str(ch.get("id") or "").strip()
        forms = [f for f in (ch.get("forms") or []) if isinstance(f, dict)]
        for form in forms:
            name = str(form.get("form") or "").strip()
            asset = str(form.get("asset_key") or "").strip()
            if cid and name and asset:
                out[f"{cid}/{name}"] = asset
        if cid and len(forms) == 1:
            asset = str(forms[0].get("asset_key") or "").strip()
            if asset:
                out[cid] = asset
    return out


def primary_identity_chars(root: str, section: str) -> List[str]:
    """Prompt section 资产身份注册层 → primary asset keys.

    Falls back to reference parsing when the identity layer is absent or cannot
    be resolved, keeping older prompt formats compatible.
    """
    asset_by_ref = identity_asset_map(root)
    registered = registered_character_assets(root)
    if not asset_by_ref or "资产身份注册层" not in section:
        return []
    raw_refs = IDENTITY_REF_RE.findall(section)
    starred = [raw for raw in raw_refs if "*" in raw]
    refs: List[str] = []
    for raw in (starred or raw_refs):
        ref = normalize_identity_ref(raw)
        asset = asset_by_ref.get(ref)
        is_char = asset in registered if registered else is_character_asset(asset)
        if asset and is_char and asset not in refs:
            refs.append(asset)
    return refs


def normalize_identity_ref(ref: str) -> str:
    """Prompt identity ref → registry key, accepting `CHAR_01/常态*` and legacy `CHAR_01*/常态`."""
    return str(ref or "").strip().replace("*/", "/").rstrip("*")


def shot_character_map(root: str, ep: str) -> Dict[str, List[str]]:
    """每镜 PNG → 主检角色列表。

    新 prompt 优先取「资产身份注册层」的主身份；旧 prompt 回退取「参考图」
    行的 定妆_<角色>。这样辅助参考图/后景反应锚不会被误当成最大脸身份。
    """
    prompt = os.path.join(root, "出图", ep, "prompt", "01_分镜出图.md")
    target_lines = load_storyboard_target_lines(root, ep)
    out: Dict[str, List[str]] = {}
    if not os.path.isfile(prompt):
        return out
    text = open(prompt, encoding="utf-8").read()
    blocks = re.split(r"(?m)(?=^## )", text)
    for blk in blocks:
        head = blk.splitlines()[0] if blk.strip() else ""
        target_pngs = prompt_target_pngs(blk, ep)
        if not target_pngs:
            target_pngs = [p for p in target_lines.get(section_clip_key(head), [])]
        if not target_pngs:
            continue
        chars = primary_identity_chars(root, blk)
        if not chars:
            for ref in re.findall(r"定妆_([^`\s，。、,）)]+)", _ref_block(blk)):
                if ref.endswith(".png"):
                    ref = ref[:-4]
                ref = re.sub(r"_(45度|侧|半身|全身|背|三视图|设定表|脸部特写|表情(?:_.+)?)$", "", ref)
                if is_character_asset(ref) and ref not in chars:
                    chars.append(ref)
        if chars:
            for png in target_pngs:
                out[png] = chars
    return out


def section_clip_key(header: str) -> str:
    match = re.search(r"(?:Clip|CLIP|clip|镜头)[_\s-]*([0-9０-９]+)", str(header or ""))
    if not match:
        return ""
    raw = match.group(1).translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    return f"Clip_{int(raw):02d}"


def prompt_target_pngs(section: str, ep: str) -> List[str]:
    """Return target PNGs under 出图/<ep>/图片 mentioned in a prompt section."""
    out: List[str] = []
    seen: Set[str] = set()
    pattern = re.compile(rf"出图/{re.escape(ep)}/图片/([^`』\s，；。)）]+\.png)")
    for match in pattern.finditer(str(section or "")):
        rel = f"图片/{match.group(1)}"
        if rel not in seen:
            seen.add(rel)
            out.append(rel)
    return out


def load_storyboard_target_lines(root: str, ep: str) -> Dict[str, List[str]]:
    """storyboard.json → Clip_NN target PNGs relative to 出图/<ep>."""
    path = os.path.join(root, "脚本", ep, "storyboard.json")
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, List[str]] = {}
    for index, clip in enumerate(data.get("clips") or [], start=1):
        if not isinstance(clip, dict):
            continue
        key = storyboard_clip_key(clip, index)
        paths: List[str] = []
        first = clip.get("firstframe_png")
        if isinstance(first, str):
            paths.append(first)
        continuity = clip.get("continuity") or {}
        if isinstance(continuity, dict):
            mid = continuity.get("midframe") or {}
            if isinstance(mid, dict):
                paths.extend(p for p in (mid.get("anchor_png"), mid.get("midframe_png")) if isinstance(p, str))
            for anchor in continuity.get("anchors") or []:
                if isinstance(anchor, dict) and isinstance(anchor.get("anchor_png"), str):
                    paths.append(anchor["anchor_png"])
            if isinstance(continuity.get("endframe_png"), str):
                paths.append(continuity["endframe_png"])
        rels: List[str] = []
        seen: Set[str] = set()
        for raw in paths:
            rel = episode_image_rel(raw, ep)
            if rel and rel not in seen:
                seen.add(rel)
                rels.append(rel)
        if rels:
            out[key] = rels
    return out


def storyboard_clip_key(clip_data: Mapping[str, object], fallback_index: int) -> str:
    for field in ("clip", "id"):
        value = clip_data.get(field)
        if value is None:
            continue
        match = re.search(r"(?:Clip|CLIP|clip|镜头)[_\s-]*([0-9]+)", str(value))
        if match:
            return f"Clip_{int(match.group(1)):02d}"
    return f"Clip_{fallback_index:02d}"


def episode_image_rel(path: str, ep: str) -> str:
    text = str(path or "").strip().strip("`")
    prefix = f"出图/{ep}/"
    if text.startswith(prefix):
        return text[len(prefix):]
    if text.startswith("图片/"):
        return text
    if text.endswith(".png") and "/" not in text:
        return f"图片/{text}"
    return ""


def _ref_block(section: str) -> str:
    m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^##\s+|\Z)", section)
    return m.group(0) if m else ""


# ---------- 主流程 ----------

def pillow_fallback_analyze(root: str, ep: str, image_mod, margin: float = DEFAULT_MARGIN) -> dict:
    """无 insightface 时的 Pillow 降级档：逐镜查 图存在/可解码/分辨率/清晰度。

    available=True（有真实机检信号，G1 不再整段失明），但 mode=pillow_fallback +
    precision=insufficient_precision——消费端（n2d-score）据此给降权分；绝不输出假相似度。
    """
    result: dict = {
        "available": True,
        "mode": PILLOW_FALLBACK_MODE,
        "precision": "insufficient_precision",
        "precision_level": "degraded",  # 契约三档（n2d_contract.PRECISION_*）：有真实但低精度信号
        "margin": margin,
        "characters": {},
        "shots": [],
        "notes": [
            "未装 insightface——已降级为 Pillow 基础机检（仅查 图存在/可解码/分辨率/清晰度，"
            "不做人脸相似度、不臆造相似度分）；建议安装 insightface 提升精度，崩脸仍需人判兜底。",
        ],
    }
    smap = shot_character_map(root, ep)
    for png, chars in sorted(smap.items()):
        full = os.path.join(root, "出图", ep, png)
        if not os.path.exists(full):
            result["shots"].append({
                "png": png, "chars": chars, "verdict": "block",
                "mode": PILLOW_FALLBACK_MODE, "checks": ["分镜 PNG 不存在"],
            })
            continue
        probe = _pillow_probe(image_mod, full)
        if probe is None:
            verdict, checks = pillow_shot_verdict(False)
        else:
            w, h, sharpness = probe
            verdict, checks = pillow_shot_verdict(True, w, h, sharpness)
        result["shots"].append({
            "png": png, "chars": chars, "verdict": verdict,
            "mode": PILLOW_FALLBACK_MODE, "checks": checks,
        })
    return result


def analyze(root: str, ep: str, margin: float = DEFAULT_MARGIN) -> dict:
    sets = discover_costume_sets(root)
    app = _load_embedder()
    result: dict = {"available": app is not None, "mode": "insightface", "margin": margin,
                    "characters": {}, "shots": [], "notes": []}
    if app is None:
        image_mod = _load_pillow()
        if image_mod is not None:
            return pillow_fallback_analyze(root, ep, image_mod, margin)
        result["mode"] = None
        result["notes"].append(
            "脸部相似度度量已跳过（未装 insightface/cv2，且无 Pillow 可降级）——崩脸暂由人判清单(references/checklist.md)并排读图覆盖。")
        return result

    # 1) 每角色定妆组自标定 floor
    char_floor: Dict[str, float] = {}
    char_calibrated: Dict[str, bool] = {}
    char_main_emb: Dict[str, List[float]] = {}
    char_variant_embs: Dict[str, List[List[float]]] = {}  # P3：主+侧+背+半身… 全视图，逐镜取最像的比
    for char, variants in sets.items():
        embs = {v: _embed(app, p) for v, p in variants.items()}
        main = embs.get("主")
        intra = []
        if main is not None:
            char_main_emb[char] = main
            char_variant_embs[char] = [e for e in embs.values() if e is not None]
            for v, e in embs.items():
                if v != "主" and e is not None:
                    intra.append(cosine(main, e))
        floor = calibrate_floor(intra)
        char_floor[char] = floor
        char_calibrated[char] = floor_calibrated(intra)
        result["characters"][char] = {"floor": round(floor, 4), "intra_pairs": len(intra),
                                      "has_main": main is not None,
                                      "floor_calibrated": char_calibrated[char]}

    # 2) 每镜 vs 其角色主参考
    smap = shot_character_map(root, ep)
    char_ep_scores: Dict[str, List[float]] = {}  # 跨集 embedding 漂移用：本集每角色全镜「vs 共享定妆主参考」余弦
    for png, chars in sorted(smap.items()):
        full = os.path.join(root, "出图", ep, png)
        if not os.path.exists(full):
            continue
        face_embs = _embed_all(app, full)
        if not face_embs:
            result["shots"].append({"png": png, "verdict": "noface", "chars": chars})
            continue
        worst = None
        for c in chars:
            if c in char_main_emb:
                # 跨集漂移基线用「vs 主参考」（稳定可比，驱动 identity.py ②/⑤）；
                # P3 逐镜 verdict 用「vs 最像视图」，避免侧/背/大角度同人镜被正脸基线误判 🟡。
                match = best_face_match(face_embs, char_main_emb[c], char_variant_embs.get(c) or [char_main_emb[c]])
                if match is None:
                    continue
                sc, sc_main, face_idx = match
                char_ep_scores.setdefault(c, []).append(sc_main)
                fl = char_floor.get(c, 0.50)
                v = band(sc, fl, margin)
                row = {"char": c, "score": round(sc, 4), "floor": round(fl, 4), "verdict": v,
                       "floor_calibrated": char_calibrated.get(c, False), "face_idx": face_idx}
                if round(sc, 4) != round(sc_main, 4):
                    row["score_vs_main"] = round(sc_main, 4)
                    row["anchor"] = "best_of_variants"  # P3：本镜按最像视图判，非仅正脸
                # 地板未自标定（单张定妆）时，block/warn 标低精度——score 降权，不当硬判
                if not char_calibrated.get(c, False) and v in ("block", "warn"):
                    row["precision"] = "low_floor_uncalibrated"
                    if v == "block":
                        # 风格化漫剧脸跨图常 <0.5，地板没自标定时 0.50 回退会系统性误杀单参考角色；
                        # 降 warn 交人判（仍醒目），不当硬判 auto-return。
                        v = row["verdict"] = "warn"
                if worst is None or _sev(v) > _sev(worst["verdict"]):
                    worst = row
        if worst:
            row = {"png": png, **worst}
            # 多人同框：对所有脸做分配匹配，抓"张冠李戴"串脸（单脸 worst-of 测不出）
            present = {c: char_main_emb[c] for c in chars if c in char_main_emb}
            if len(present) >= 2:
                if len(face_embs) >= 2:
                    swap = detect_face_swaps(face_embs, present)
                    if swap["duplicate_chars"] or swap["missing_chars"]:
                        row["face_swap"] = swap
                        if swap["swap_suspected"] and _sev(row["verdict"]) < _sev("warn"):
                            row["verdict"] = "warn"  # 串脸至少 🟡，交人判
            result["shots"].append(row)
    # 本集每角色质心相对锚点的接近度（驱动 identity.py 跨集 embedding 漂移报表）
    for char, scores in char_ep_scores.items():
        rec = result["characters"].setdefault(char, {})
        rec["ep_mean_score"] = episode_mean(scores)
        rec["ep_n_shots"] = len(scores)
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
        full = _resolve_project_path(root, main)
        try:
            img = cv2.imread(full)
            if img is None:
                out["anchors"].append({"char": char, "verdict": "block", "reason": "读不到 PNG"})
                continue
            h, w = img.shape[:2]
            faces = app.get(img)
            n = int(len(faces))
            ratio = 0.0
            if n:
                f = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1]))
                ratio = float(((f.bbox[2]-f.bbox[0])*(f.bbox[3]-f.bbox[1])) / float(w*h))
            v = anchor_verdict(n, ratio, min_ratio)
            out["anchors"].append({"char": char, "faces": n, "box_ratio": round(float(ratio), 4), "verdict": v})
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
            if s.get("mode") == PILLOW_FALLBACK_MODE:
                print(f"{icon[v]} {s['png']} · {'/'.join(s.get('chars') or ['?'])} {'；'.join(s.get('checks') or [])}")
            else:
                print(f"{icon[v]} {s['png']} · {s.get('char','?')} score={s.get('score')} < floor={s.get('floor')}")
    print(f"\n崩脸 🔴 {nblock} · 共评 {len(res['shots'])} 镜")
    return 1 if nblock else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
