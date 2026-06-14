#!/usr/bin/env python3
"""片内时序一致性机检（N2）——补 n2d-review 只查首帧 + 接缝、漏查 clip 内部漂移的盲区。

2026 行业 scene-stability 记分卡把 **身份保持 + 运动稳定** 列为核心；典型崩法是
「几秒后脸渐变 + 发际线/下颌 flicker」——这发生在**单个 clip 内部**，不是 clip 之间的接缝。

本脚本对 `出视频/第N集/视频/*.mp4` 每条 clip 抽 K 帧，量两件事：
  ① **片内身份漂移**：相邻帧人脸余弦的最小值（越低越漂）——需 insightface。
  ② **flicker / TCI**：相邻帧整幅平均亮度的绝对差均值（越大越闪）——需 Pillow，越小越稳。
缺库优雅跳过，交人判。纯数学部分（pairwise/flicker/TCI/min-cosine/band）无依赖、带 pytest。

用法：python3 temporal_consistency.py <作品根> 第N集 [--frames 6] [--id-floor 0.6] [--flicker-max 0.06] [--json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Sequence

import face_consistency as fc  # 复用 cosine

DEFAULT_FRAMES = 6          # 采样下限（floor）——短镜/无时长信息时的兜底帧数
SAMPLE_PER_SEC = 1.0        # 自适应基准：约 1 帧/秒（长镜抽更多，抓片中段渐变脸漂）
CLOSEUP_DENSITY = 1.5       # 近景镜采样加密系数（脸占画幅大，渐变更刺眼，多采几帧）
SAMPLE_CAP = 24            # 采样上限（cap）——封顶单镜 insightface 嵌入成本
CLOSEUP_MARKERS = ("ECU", "MCU", "BCU", "CU", "OTS", "反打", "特写", "近景", "过肩")  # 与 video_qc 同义
DEFAULT_ID_FLOOR = 0.60     # 相邻帧同人余弦下限（低于=片内身份漂移）
DEFAULT_FLICKER_MAX = 0.06  # 相邻帧亮度归一化绝对差均值上限（高于=闪烁）
SEAM_WARN = 18   # 尾帧 vs 下一首帧 64位dHash 距 > 此 → 接缝构图对不上（尾帧接力本应近乎同构图）
SEAM_BLOCK = 29  # 距更大 → 接力基本断（出视频会跳切）
# 色彩直方图距（dHash 是灰度结构哈希，抓不到"同构图但灯光/色温跳"的剪辑点闪光）。
# 接缝两帧本应近乎同色，故用绝对阈值（非自标定）；cosine 距 = 1 - 余弦相似度。
SEAM_COLOR_WARN = 0.12
SEAM_COLOR_BLOCK = 0.30
# 人脸身份（dHash 抓结构、色距抓灯光，二者都抓不到"同构图同色但脸被重画/微调五官"=尾帧脸漂）。
# 接缝两帧本应同人、表情/头位只在小范围内变，故用**保守**绝对阈值：正常表情/转头不会把
# arcface 余弦压到这么低，只有真·重画脸/换人才会 → 误报风险低。需 insightface（缺则静默跳过
# 交人判），另叠本集相对离群（只收紧不放松）。
SEAM_FACE_WARN_COS = 0.50   # 尾帧 vs 首帧 人脸余弦 < 此 → warn（脸偏，疑似漂）
SEAM_FACE_BLOCK_COS = 0.35  # < 此 → block（基本是另一张脸/严重漂）
HIST_BINS = 16   # 每通道直方图 bin 数（16×3=48 维，够分辨色温/明暗跳，又不过拟合噪点）


# ---------- 纯数学（无依赖 · pytest 覆盖） ----------

def pairwise_consecutive_absdiff(values: Sequence[float]) -> List[float]:
    """相邻元素绝对差序列；<2 元素返回空。"""
    return [abs(values[i + 1] - values[i]) for i in range(len(values) - 1)]


def hist_cosine_distance(h1: Sequence[float], h2: Sequence[float]) -> Optional[float]:
    """两个直方图的 cosine 距 = 1 - 余弦相似度 ∈ [0,2]；维度不等/全零 → None。纯函数·可测。"""
    if not h1 or not h2 or len(h1) != len(h2):
        return None
    dot = sum(a * b for a, b in zip(h1, h2))
    n1 = sum(a * a for a in h1) ** 0.5
    n2 = sum(b * b for b in h2) ** 0.5
    if n1 == 0 or n2 == 0:
        return None
    return max(0.0, 1.0 - dot / (n1 * n2))


def color_verdict(color_dist: Optional[float],
                  warn: float = SEAM_COLOR_WARN, block: float = SEAM_COLOR_BLOCK) -> str:
    """色彩距 → ok/warn/block。None（缺图/算不出）→ ok（不臆造，交结构哈希/人判）。纯函数。"""
    if color_dist is None:
        return "ok"
    return "block" if color_dist > block else "warn" if color_dist > warn else "ok"


def face_seam_verdict(cos: Optional[float],
                      warn_cos: float = SEAM_FACE_WARN_COS,
                      block_cos: float = SEAM_FACE_BLOCK_COS) -> Optional[str]:
    """尾帧↔首帧人脸余弦 → ok/warn/block。None（缺 insightface / 任一帧无脸）→ None（交人判，
    不臆造，也不影响结构/色彩定级）。余弦越高越同人。纯函数。"""
    if cos is None:
        return None
    if cos < block_cos:
        return "block"
    if cos < warn_cos:
        return "warn"
    return "ok"


def _worse(a: str, b: str) -> str:
    order = {"ok": 0, "warn": 1, "block": 2}
    return a if order.get(a, 0) >= order.get(b, 0) else b


def _median(vals: Sequence[float]) -> float:
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def seam_relative_floor(dists: Sequence[Optional[float]], k: float = 3.0,
                        min_count: int = 4, min_margin: float = 4.0) -> Optional[float]:
    """本集接缝 dHash 距分布的离群上界 = 中位数 + max(k×MAD, min_margin)。

    绝对阈值（SEAM_WARN/BLOCK）抓"客观上断了"的接缝；本上界抓"绝对阈值放过、
    但相对本集自身分布异常差"的接缝——只用于把 ok 收紧到 warn，**从不放松**绝对阈值。
    样本 < min_count 时分布没意义 → None（不标定）；全相同分布（MAD=0）由 min_margin 保底防零容忍。
    """
    vals = [d for d in dists if d is not None]
    if len(vals) < min_count:
        return None
    med = _median(vals)
    mad = _median([abs(v - med) for v in vals])
    return med + max(k * mad, min_margin)


def apply_relative_outlier(verdict: str, dist: Optional[float], floor: Optional[float]) -> str:
    """绝对阈值放过(ok)、但相对本集分布离群的接缝升到 warn；只升不降。纯函数。"""
    if verdict == "ok" and floor is not None and dist is not None and dist > floor:
        return "warn"
    return verdict


def flicker_index(frame_luma: Sequence[float]) -> float:
    """相邻帧平均亮度(0..1)绝对差的均值 = flicker 量；越小越稳。不足两帧→0。"""
    diffs = pairwise_consecutive_absdiff(frame_luma)
    return sum(diffs) / len(diffs) if diffs else 0.0


def temporal_consistency_index(frame_luma: Sequence[float]) -> float:
    """TCI ∈(0,1]：1/(1+flicker)，越接近 1 越稳（无闪烁=1）。"""
    return 1.0 / (1.0 + flicker_index(frame_luma))


def min_consecutive_cosine(embs: Sequence[Sequence[float]]) -> Optional[float]:
    """相邻帧人脸嵌入余弦的最小值（片内身份最差的一跳）；<2 个有效嵌入→None。"""
    vals = [fc.cosine(embs[i], embs[i + 1]) for i in range(len(embs) - 1)]
    return min(vals) if vals else None


def verdict(min_id: Optional[float], flicker: float,
            id_floor: float = DEFAULT_ID_FLOOR, flicker_max: float = DEFAULT_FLICKER_MAX) -> str:
    """综合定档：身份漂移或闪烁任一超标→升级。"""
    sev = "ok"
    if min_id is not None:
        if min_id < id_floor - 0.1:
            sev = "block"
        elif min_id < id_floor:
            sev = _max(sev, "warn")
    if flicker > flicker_max * 1.5:
        sev = "block"
    elif flicker > flicker_max:
        sev = _max(sev, "warn")
    return sev


def _max(a: str, b: str) -> str:
    order = {"ok": 1, "warn": 2, "block": 3}
    return a if order[a] >= order[b] else b


def adaptive_frame_count(duration_sec: Optional[float], *, closeup: bool = False,
                         floor: int = DEFAULT_FRAMES, per_sec: float = SAMPLE_PER_SEC,
                         cap: int = SAMPLE_CAP) -> int:
    """按 clip 时长（+近景加密）自适应采样帧数，抓「片中段才渐变」的脸漂。纯函数·可测。

    固定 6 帧对 10–60s 的长镜太稀（2026 各家 long-range 时序仍是软肋）：一条 15s 镜只看 6 帧，
    中间 2–3 秒的渐变脸漂会从采样缝里漏过去。这里 ≈1 帧/秒、近景再 ×1.5，floor 兜底短镜、
    cap 封顶单镜 insightface 成本。无时长信息（探测失败）→ 退回 floor。"""
    if not duration_sec or duration_sec <= 0:
        return floor
    rate = per_sec * (CLOSEUP_DENSITY if closeup else 1.0)
    n = int(round(duration_sec * rate))
    return max(floor, min(cap, n))


# ---------- 抽帧 + 嵌入（需 ffmpeg / Pillow / insightface） ----------

def _sample_frames(mp4: str, k: int, outdir: str) -> List[str]:
    try:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", mp4, "-vf", f"fps=1/0.001,select='not(mod(n,1))'",
             "-frames:v", str(k), os.path.join(outdir, "f_%03d.png")],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        # 退回：按时间均匀取 k 张
        try:
            dur = fc_duration(mp4)
            if not dur:
                return []
            paths = []
            for i in range(k):
                t = dur * (i + 0.5) / k
                p = os.path.join(outdir, f"t_{i:03d}.png")
                subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", mp4,
                                "-frames:v", "1", p], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(p):
                    paths.append(p)
            return paths
        except Exception:
            return []
    return sorted(glob.glob(os.path.join(outdir, "f_*.png")))


def fc_duration(mp4: str) -> Optional[float]:
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", mp4], text=True)
        return float(out.strip())
    except Exception:
        return None


def _luma(path: str) -> Optional[float]:
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("L")
        im.thumbnail((64, 64))
        px = list(im.getdata())
        return (sum(px) / len(px)) / 255.0 if px else None
    except Exception:
        return None


def _rgb_hist(path: str, bins: int = HIST_BINS) -> Optional[List[float]]:
    """归一化 RGB 直方图（每通道 bins 桶，concat 成 3×bins 维）。缺 Pillow/读图失败 → None。"""
    try:
        from PIL import Image  # type: ignore
        im = Image.open(path).convert("RGB")
        im.thumbnail((96, 96))
        chans = im.split()
        step = 256 / bins
        out: List[float] = []
        for ch in chans:
            h = [0.0] * bins
            for v in ch.getdata():
                idx = min(bins - 1, int(v / step))
                h[idx] += 1.0
            total = sum(h) or 1.0
            out.extend(x / total for x in h)
        return out
    except Exception:
        return None


def _face_emb(app, path: str) -> Optional[List[float]]:
    return fc._embed(app, path) if app else None


def _load_json(path: str) -> Optional[Any]:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def analyze_lighting_signature(path: str, signature: Dict[str, Any]) -> str:
    """光位签名是自由文本约束（如「画左前暖烛主光，画右后冷月背光」）——像素层无法与
    文本可靠对账，永远返回 "skipped" 交人判/出图侧契约把关。绝不返回 ok：
    早先的占位实现静默放行过，假通过比缺检查更危险。"""
    return "skipped"


def count_lighting_signatures(registry: Optional[Dict[str, Any]]) -> int:
    """asset_registry 里带 lighting_signature 约束的资产数。纯函数·可测。"""
    if not isinstance(registry, dict):
        return 0
    return sum(
        1 for a in registry.get("assets", [])
        if isinstance(a, dict) and (a.get("constraints") or {}).get("lighting_signature")
    )


def analyze(root: str, ep: str, frames: int = DEFAULT_FRAMES,
            id_floor: float = DEFAULT_ID_FLOOR, flicker_max: float = DEFAULT_FLICKER_MAX) -> dict:
    vids = sorted(glob.glob(os.path.join(root, "出视频", ep, "视频", "*.mp4")))
    res: dict = {"clips": [], "notes": [], "frames": frames}

    n_sig = count_lighting_signatures(_load_json(os.path.join(root, "出图", "共享", "asset_registry.json")))
    if n_sig:
        res["notes"].append(
            f"{n_sig} 个资产带 lighting_signature（自由文本光位约束）——文本签名无法像素机检，光位匹配交人判。")

    if not vids:
        res["notes"].append(f"无 clip MP4（{os.path.join(root,'出视频',ep,'视频')}）——出视频后再跑本检。")
        return res
    if not _has_ffmpeg():
        res["notes"].append("未找到 ffmpeg——片内时序机检跳过，交人判抽帧。")
        return res
    app = fc._load_embedder()  # 可能 None（缺 insightface）→ 只测 flicker
    if app is None:
        res["notes"].append("未装 insightface——仅测 flicker/TCI，身份漂移交人判。")
    closeup_map = _load_closeup_map(root, ep)  # 镜号→近景：近景镜采样加密
    for mp4 in vids:
        num = _shot_num(os.path.basename(mp4))
        dur = fc_duration(mp4)
        closeup = bool(closeup_map.get(num)) if num is not None else False
        k = adaptive_frame_count(dur, closeup=closeup, floor=frames)
        with tempfile.TemporaryDirectory() as td:
            fpaths = _sample_frames(mp4, k, td)
            lumas = [x for x in (_luma(p) for p in fpaths) if x is not None]
            embs = [e for e in (_face_emb(app, p) for p in fpaths) if e is not None] if app else []
            fl = flicker_index(lumas)
            mid = min_consecutive_cosine(embs) if len(embs) >= 2 else None
            v = verdict(mid, fl, id_floor, flicker_max)
            res["clips"].append({
                "clip": os.path.basename(mp4), "frames": len(fpaths),
                "sampled_target": k, "duration": round(dur, 2) if dur else None, "closeup": closeup,
                "min_id_cos": round(mid, 4) if mid is not None else None,
                "flicker": round(fl, 4), "tci": round(temporal_consistency_index(lumas), 4),
                "verdict": v,
            })
    return res


def _shot_num(name: str) -> Optional[int]:
    m = re.search(r"镜头(\d+)", name) or re.search(r"Clip[_]?(\d+)", name, re.I)
    return int(m.group(1)) if m else None


def _is_closeup_lens(lens: str) -> bool:
    s = str(lens or "").upper()
    return any(m.upper() in s for m in CLOSEUP_MARKERS)


def _load_closeup_map(root: str, ep: str) -> Dict[int, bool]:
    """镜号 → 是否近景镜（任一分镜 lens 命中近景档）。喂自适应采样加密。缺 storyboard → 空表。"""
    sb = _load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    out: Dict[int, bool] = {}
    if not isinstance(sb, dict):
        return out
    for clip in (sb.get("clips") or sb.get("shots") or []):
        if not isinstance(clip, dict):
            continue
        num = _shot_num(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if num is None:
            continue
        out[num] = any(_is_closeup_lens((s or {}).get("lens", "")) for s in (clip.get("shots") or []))
    return out


# ── 接缝意图（storyboard 是唯一真值源）──────────────────────────────────────
# 与 n2d-video/scripts/video_qc.py 的 seam_strictness/RELAY_TRANSITIONS 同义，两处保持同步。
RELAY_TRANSITIONS = ("接力", "relay", "seamless", "continuous")


def _is_relay_transition(transition: Any) -> bool:
    return str(transition or "").strip().lower() in RELAY_TRANSITIONS


def _declared_relay(transition: Any, need_endframe: bool) -> bool:
    """Whether this seam should be treated as a strict cross-clip relay.

    `need_endframe=true` also exists for the triframe contract: it means an end
    frame asset is required for video guidance, but an explicit hard/match/action
    cut still means the cross-clip dHash distance is informational.  If the
    storyboard omits transition intent, keep the old conservative strict mode.
    """
    text = str(transition or "").strip()
    if _is_relay_transition(text):
        return True
    if text:
        return False
    return bool(need_endframe)


def seam_strictness(intent: Optional[Dict[str, Any]]) -> str:
    """relay 声明 → strict；声明了其他切镜 → info（构图必变，只记录）；无意图 → strict。纯函数。"""
    if intent is None:
        return "strict"
    if intent.get("relay") or str(intent.get("transition") or "").strip().lower() in RELAY_TRANSITIONS:
        return "strict"
    if str(intent.get("transition") or "").strip():
        return "info"
    return "strict"


def load_seam_intents(root: str, ep: str) -> Dict[int, Dict[str, Any]]:
    """clip 序号 → storyboard 声明的接缝意图（continuity.transition + need_end_frame）。"""
    data = _load_json(os.path.join(root, "脚本", ep, "storyboard.json"))
    if not isinstance(data, dict):
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for clip in (data.get("clips") or data.get("shots") or []):
        if not isinstance(clip, dict):
            continue
        n = _shot_num(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if n is None:
            m = re.search(r"(\d+)\s*$", str(clip.get("id") or ""))
            n = int(m.group(1)) if m else None
        if n is None:
            continue
        cont = clip.get("continuity") or {}
        transition = cont.get("transition")
        need_end = bool(clip.get("need_endframe") or cont.get("need_endframe")
                        or clip.get("need_end_frame") or cont.get("need_end_frame"))
        out[n] = {"transition": cont.get("transition"),
                  # 规范字段 need_endframe（无下划线）；need_end_frame 仅旧别名兜底。
                  "relay": _declared_relay(transition, need_end)}
    return out


def _is_anchor_png_name(name: str) -> bool:
    stem = os.path.splitext(os.path.basename(name))[0]
    return stem.endswith("_mid") or re.search(r"_a\d+$", stem) is not None


def _face_cos(app, p1: Optional[str], p2: Optional[str]) -> Optional[float]:
    """两图最大人脸的 arcface 余弦；缺 embedder / 任一帧无脸 → None（交人判）。"""
    if app is None or not p1 or not p2:
        return None
    e1, e2 = fc._embed(app, p1), fc._embed(app, p2)
    if e1 is None or e2 is None:
        return None
    return fc.cosine(e1, e2)


def seam_pair_check(tail_path: str, first_path: str,
                    warn: int = SEAM_WARN, block: int = SEAM_BLOCK) -> Optional[Dict[str, Any]]:
    """单对接缝机检（前镜尾帧图 vs 后镜首帧图）：dHash 结构距 + RGB 直方图色距 → verdict。
    供 PNG 层（seam_analyze）与出视频层（n2d-video/video_qc 抽帧）共用同一套阈值与数学。
    缺 Pillow / 读图失败 → None（交人判，不臆造）。"""
    import scene_consistency as scn  # 复用 _dhash_image / hamming / _probe_pillow
    if not scn._probe_pillow():
        return None
    h1, h2 = scn._dhash_image(tail_path), scn._dhash_image(first_path)
    if h1 is None or h2 is None:
        return None
    dist = scn.hamming(h1, h2)
    struct_v = "block" if dist > block else "warn" if dist > warn else "ok"
    cdist = hist_cosine_distance(_rgb_hist(tail_path) or [], _rgb_hist(first_path) or [])
    cv = color_verdict(cdist)
    return {
        "dist": dist, "struct_verdict": struct_v,
        "color_dist": round(cdist, 4) if cdist is not None else None,
        "color_verdict": cv, "verdict": _worse(struct_v, cv),
    }


def seam_analyze(root: str, ep: str, warn: int = SEAM_WARN, block: int = SEAM_BLOCK) -> dict:
    """⑤ 接缝姿态/构图连续机检（PNG 层，出图后即可跑）——把"逐接缝人判并排读图"降成机检初筛。
    尾帧接力铁律：`镜头N_end.png` 构图 = 下一 Clip 首帧。两者 dHash 距应很小；
    距大 = 尾帧没对上下一首帧 → 出视频接缝会跳切。距小不代表姿态完美（仍需人判），但距大几乎必跳。
    两个互补指标：① dHash（灰度结构）抓构图/姿态错位；② RGB 直方图 cosine 距抓"同构图但灯光/色温
    跳"的剪辑点闪光（dHash 看不到颜色）。任一超阈即报，取较重者定级。色彩端缺 Pillow 时静默退化为纯
    dHash（不臆造）。后续可再接光流/姿态距离，但二者已覆盖跳切的主要两轴（构图 + 色彩）。"""
    import scene_consistency as scn  # 复用 _dhash_image / hamming / _probe_pillow
    res: dict = {"seams": [], "notes": []}
    d = os.path.join(root, "出图", ep, "图片")
    if not os.path.isdir(d):
        res["notes"].append(f"无 {d}——出图后再跑接缝机检。"); return res
    if not scn._probe_pillow():
        res["notes"].append("未装 Pillow——接缝机检跳过，交人判并排读图。"); return res
    tails: Dict[int, str] = {}
    firsts: Dict[int, str] = {}
    for p in glob.glob(os.path.join(d, "*.png")):
        nm = os.path.basename(p); n = _shot_num(nm)
        if n is None:
            continue
        if nm[:-4].endswith("_end"):
            tails[n] = p
        elif not _is_anchor_png_name(nm):
            firsts.setdefault(n, p)
    fnums = sorted(firsts)
    app = fc._load_embedder()  # 人脸身份比对用；None=缺 insightface（静默退化为纯构图/色彩，交人判）
    if app is None:
        res["notes"].append("未装 insightface——接缝仅测构图/色彩，尾帧脸身份漂移交人判。")
    # 两遍制：先收集全部接缝距离 → 用本集分布算离群上界（只收紧不放松）→ 再定级。
    pairs = []
    for n, tail in sorted(tails.items()):
        nxt = next((m for m in fnums if m > n), None)
        if nxt is None:
            continue
        chk = seam_pair_check(tail, firsts[nxt], warn=warn, block=block)
        if chk is None:
            continue
        intra_cos = _face_cos(app, tail, firsts.get(n))   # 尾帧 vs 本镜首帧（最直接的"尾帧脸漂"）
        cross_cos = _face_cos(app, tail, firsts[nxt])      # 尾帧 vs 接力的下一镜首帧
        pairs.append((n, tail, firsts[nxt], chk, intra_cos, cross_cos))
    rel_floor = seam_relative_floor([p[3]["dist"] for p in pairs])
    if rel_floor is not None:
        res["relative_floor"] = round(rel_floor, 1)
    # 人脸距(=1-cos)的本集相对离群上界（face 距数值小，min_margin 调小）；只把 ok 收紧到 warn。
    rel_face_floor = seam_relative_floor([1.0 - p[5] for p in pairs if p[5] is not None],
                                         min_margin=0.08)
    intents = load_seam_intents(root, ep)
    if not intents and pairs:
        res["notes"].append("storyboard 接缝意图不可用——_end.png 接力对全部按接力铁律严格判（可能误报设计切镜）。")
    res["contradictions"] = []
    for n, tail, first, chk, intra_cos, cross_cos in pairs:
        v = apply_relative_outlier(chk["verdict"], chk["dist"], rel_floor)
        intent = intents.get(n)
        strictness = seam_strictness(intent) if intents else "strict"
        # 人脸身份漂移：intra（尾帧 vs 本镜首帧）任何转场都该同人，始终比；
        # cross（尾帧 vs 下一镜首帧）只在接力(strict)时比，硬切/溶解下镜本就可能换人/换景，不比免误报。
        fv_intra = face_seam_verdict(intra_cos)
        fv_cross = face_seam_verdict(cross_cos) if strictness == "strict" else None
        face_v = None
        for fv in (fv_intra, fv_cross):
            if fv is not None:
                face_v = fv if face_v is None else _worse(face_v, fv)
        if face_v == "ok" and strictness == "strict" and cross_cos is not None:
            face_v = apply_relative_outlier("ok", 1.0 - cross_cos, rel_face_floor)
        if face_v is not None:
            v = _worse(v, face_v)
        if intents and strictness == "info":
            # 真值源矛盾：出图层有 镜头N_end.png（接力素材），storyboard 却声明非接力切镜。
            # 以 storyboard 为准——dHash 降为 info，但矛盾本身要报（两套声明必须收敛）。
            res["contradictions"].append({
                "shot": n, "tail": os.path.basename(tail),
                "transition": (intent or {}).get("transition"),
                "msg": f"镜头{n} 存在接力尾帧 _end.png，但 storyboard 声明 "
                       f"{(intent or {}).get('transition')}（非接力）——真值源矛盾，"
                       "以 storyboard 为准；请补 need_endframe 或移除 _end 尾帧",
            })
            if v != "ok":
                v = "info"
        if v != "ok":
            res["seams"].append({"tail": os.path.basename(tail), "next_first": os.path.basename(first),
                                 "dist": chk["dist"], "verdict": v,
                                 "struct_verdict": chk["struct_verdict"], "color_verdict": chk["color_verdict"],
                                 "color_dist": chk["color_dist"],
                                 "face_verdict": face_v,
                                 "intra_face_cos": round(intra_cos, 3) if intra_cos is not None else None,
                                 "cross_face_cos": round(cross_cos, 3) if cross_cos is not None else None,
                                 "transition": (intent or {}).get("transition"),
                                 "relative_outlier": v == "warn" and chk["verdict"] == "ok"})
    return res


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--frames", type=int, default=DEFAULT_FRAMES,
                    help="采样下限（floor）；实际每镜按时长自适应加密（≈1帧/秒，近景×1.5，封顶24）")
    ap.add_argument("--id-floor", type=float, default=DEFAULT_ID_FLOOR)
    ap.add_argument("--flicker-max", type=float, default=DEFAULT_FLICKER_MAX)
    ap.add_argument("--seam", action="store_true", help="改跑接缝机检（尾帧 vs 下一首帧 dHash，出图后即可）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    if ns.seam:
        res = seam_analyze(ns.root.rstrip("/"), ns.episode)
        if ns.json:
            print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
        print(f"=== 接缝姿态/构图连续机检（尾帧 vs 下一首帧·N2接力）：{ns.root} {ns.episode} ===")
        for n in res["notes"]:
            print("ℹ️ " + n)
        for c in res.get("contradictions", []):
            print(f"⚠️真值源矛盾 {c['msg']}")
        nb = 0
        for s in res["seams"]:
            if s["verdict"] == "block":
                nb += 1
            cd = s.get("color_dist")
            why = []
            if s.get("struct_verdict", "ok") != "ok":
                why.append(f"构图 dHash 距 {s['dist']}")
            if s.get("color_verdict", "ok") != "ok":
                why.append(f"色彩/灯光距 {cd}（同构图但色温/明暗跳）")
            if s.get("relative_outlier"):
                why.append(f"本集分布离群（距 {s['dist']} 超自标定上界 {res.get('relative_floor')}）")
            print(f"{'⛔接力断' if s['verdict']=='block' else '⚠️接缝偏'} {s['tail']} → {s['next_first']}："
                  f"{'；'.join(why) or f'dHash 距 {s['dist']}'}（尾帧没对上下一首帧，出视频会跳切/闪）")
        print(f"\n接缝跳切疑似 🔴 {nb} · 共查 {len(res['seams'])} 处异常接缝")
        return 1 if nb else 0
    res = analyze(ns.root.rstrip("/"), ns.episode, ns.frames, ns.id_floor, ns.flicker_max)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2)); return 0
    print(f"=== 片内时序一致性机检（身份漂移 + flicker/TCI）：{ns.root} {ns.episode} ===")
    for n in res["notes"]:
        print("ℹ️ " + n)
    nblk = 0
    icon = {"block": "⛔", "warn": "⚠️", "ok": "✅"}
    for c in res["clips"]:
        if c["verdict"] == "block":
            nblk += 1
        if c["verdict"] in ("block", "warn"):
            print(f"{icon[c['verdict']]} {c['clip']}: 帧间身份min={c['min_id_cos']} flicker={c['flicker']} "
                  f"TCI={c['tci']} 采样{c['frames']}/{c.get('sampled_target','?')}帧"
                  f"（{c.get('duration','?')}s{'·近景' if c.get('closeup') else ''}）")
    print(f"\n片内崩 🔴 {nblk} · 共评 {len(res['clips'])} clip")
    return 1 if nblk else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
