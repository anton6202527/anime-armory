#!/usr/bin/env python3
"""契约像素兜底（④·景别阶梯）——把 storyboard 声明的景别（CU/ECU vs LS/ELS）量到实际渲染帧的**脸占比**上对照。

**为什么**：契约 `景别阶梯` 此前只查 storyboard.json 里**人填的景别标签序列**（连续同标签记 WARN），
**从不看出图 PNG 的实际景别**——标 `CU 特写` 却渲染成大远景、标 `LS 远景` 却糊一张大脸占满画面，
文本层全过。脸占比是景别的强代理：特写脸大、远景脸小。本模块用人脸检测量每镜脸占比，当**清楚矛盾**于
声明景别时出 advisory。

**保守设计（避免误杀）**：
  - 只在**检到脸**时判（脸占比=None 即跳过）——`CU 铜镜`/`CU 道具` 这类无脸特写本就合法，不报；
  - 只抓两端极端矛盾：声明**特写(CU/ECU)却脸极小** → 实为远景误标；声明**远景(LS/ELS)却脸占满** → 实为近景误标；
    中景(MCU/MS)、过肩/反打这类暧昧档**不判**；
  - **WARN·人判**，宽裕阈值。依赖人脸检测（与 image_qc 崩脸机检同栈 cv2/insightface）；
    无检测器 → available False 整段跳过（不臆造），不阻断默认无依赖产线。

阈值（脸 bbox 占整图面积比，可经 env 覆盖，应按后端/风格标定）：
  N2D_SCALE_CLOSEUP_MIN（特写脸占比下限，默认 0.05）· N2D_SCALE_WIDE_MAX（远景脸占比上限，默认 0.22）。

用法：python3 shot_scale_contract.py <作品根> <第N集> [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


def _envf(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


CLOSEUP_MIN_RATIO = _envf("N2D_SCALE_CLOSEUP_MIN", 0.05)   # 声明特写但脸占比低于此 → 矛盾（实为远景）
WIDE_MAX_RATIO = _envf("N2D_SCALE_WIDE_MAX", 0.22)        # 声明远景但脸占比高于此 → 矛盾（实为近景）

CLOSEUP_CLASSES = frozenset({"ECU", "CU"})                 # 紧特写（MCU/过肩/反打等暧昧档不判，避免误杀）
WIDE_CLASSES = frozenset({"LS", "ELS"})

# token→景别分级（长词优先，CJK 子串匹配 / ASCII 词边界）。与 gate._SHOT_SCALE_MAP 同口径，本模块自带一份保持自包含。
_SCALE_MAP = sorted([
    ("大特写", "ECU"), ("极特写", "ECU"), ("ECU", "ECU"), ("BCU", "ECU"),
    ("特写", "CU"), ("近景", "CU"), ("CU", "CU"),
    ("中近景", "MCU"), ("中近", "MCU"), ("MCU", "MCU"),
    ("中景", "MS"), ("MS", "MS"),
    ("大远景", "ELS"), ("极远景", "ELS"), ("ELS", "ELS"),
    ("全景", "LS"), ("远景", "LS"), ("LS", "LS"),
], key=lambda kv: -len(kv[0]))

_CLIP_NUM_RE = re.compile(r"(?:Clip[_\-\s]?|镜头\s*)(\d+)", re.IGNORECASE)


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def scale_class_from_text(text: str) -> Optional[str]:
    """lens/景别 串 → ECU/CU/MCU/MS/LS/ELS；抽不到→None。纯函数·可测。"""
    raw = str(text or "")
    up = raw.upper()
    for tok, cls in _SCALE_MAP:
        if tok.isascii():
            if re.search(rf"(?<![A-Z]){re.escape(tok.upper())}(?![A-Z])", up):
                return cls
        elif tok in raw:
            return cls
    return None


def scale_ratio_contradiction(declared_cls: Optional[str], face_ratio: Optional[float],
                              *, closeup_min: float = CLOSEUP_MIN_RATIO,
                              wide_max: float = WIDE_MAX_RATIO) -> Optional[Dict[str, str]]:
    """声明景别 × 实测脸占比 → 矛盾信号或 None（纯函数·可测）。

    face_ratio=None（没检到脸/无检测器）→ None（无脸特写合法，不臆造）。只判两端极端矛盾。"""
    if declared_cls is None or face_ratio is None:
        return None
    if declared_cls in CLOSEUP_CLASSES and face_ratio < closeup_min:
        return {"level": "warn", "code": "shot_scale_closeup_tiny_face",
                "tag": f"declared={declared_cls} ratio={face_ratio:.3f}"}
    if declared_cls in WIDE_CLASSES and face_ratio > wide_max:
        return {"level": "warn", "code": "shot_scale_wide_big_face",
                "tag": f"declared={declared_cls} ratio={face_ratio:.3f}"}
    return None


def clip_num_of(text: str) -> Optional[int]:
    """从 clip id / png 文件名抽镜号（Clip_01 / 镜头1）；抽不到→None。纯函数·可测。"""
    m = _CLIP_NUM_RE.search(str(text or ""))
    return int(m.group(1)) if m else None


def clip_declared_scales(storyboard: Any) -> Dict[int, str]:
    """storyboard dict → {镜号: 声明景别 class}（取每 clip shots[].lens 串）。纯函数·可测。"""
    out: Dict[int, str] = {}
    clips = (storyboard or {}).get("clips") or (storyboard or {}).get("shots") or []
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        num = clip_num_of(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if num is None:
            continue
        lenses = " ".join(str((s or {}).get("lens", "")) for s in (clip.get("shots") or []))
        cls = scale_class_from_text(lenses) or scale_class_from_text(str(clip.get("label") or ""))
        if cls:
            out[num] = cls
    return out


# ── I/O（best-effort·依赖人脸检测） ───────────────────────────────────────────

def analyze(root: Path, ep: str) -> Dict[str, Any]:
    """image_qc 集成入口：storyboard 声明景别 × 出图帧实测脸占比 → 矛盾 advisory。

    无人脸检测器（cv2_face_boxes）→ available False（脸占比近似需检测器，跳过不臆造）。"""
    root = Path(root)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import image_qc  # type: ignore
        face_mod = image_qc._load_review_module("face_consistency")
        ratio_fn = image_qc._png_face_ratio_and_size
    except Exception:
        face_mod, ratio_fn = None, None
    if face_mod is None or not hasattr(face_mod, "cv2_face_boxes") or ratio_fn is None:
        return {"available": False, "checked": 0, "findings": [],
                "notes": ["人脸检测器(cv2_face_boxes)不可用——景别脸占比近似跳过（装 opencv/insightface 后复检）。"]}
    try:
        sb = json.loads((root / "脚本" / ep / "storyboard.json").read_text(encoding="utf-8"))
    except Exception:
        return {"available": True, "checked": 0, "findings": [],
                "notes": ["storyboard.json 缺失/损坏——无声明景别可对照。"]}
    declared = clip_declared_scales(sb)
    if not declared:
        return {"available": True, "checked": 0, "findings": [],
                "notes": ["storyboard 无可解析景别（CU/LS…）——跳过。"]}
    # 出图帧：镜号 → PNG 绝对路径
    png_dir = root / "出图" / ep / "图片"
    png_by_num: Dict[int, str] = {}
    if png_dir.is_dir():
        for p in sorted(png_dir.glob("*.png")):
            num = clip_num_of(p.name)
            if num is not None:
                png_by_num.setdefault(num, str(p))
    findings: List[Dict[str, str]] = []
    checked = 0
    for num, cls in sorted(declared.items()):
        if cls not in CLOSEUP_CLASSES and cls not in WIDE_CLASSES:
            continue  # 中景/暧昧档不判
        abspath = png_by_num.get(num)
        if not abspath:
            continue
        ratio, _min_dim = ratio_fn(face_mod, abspath)
        checked += 1
        sig = scale_ratio_contradiction(cls, ratio)
        if not sig:
            continue
        rel = os.path.relpath(abspath, root)
        if sig["code"] == "shot_scale_closeup_tiny_face":
            msg = (f"景别像素兜底：镜{num} 声明 {cls}(特写) 但 {rel} 实测脸占比 {ratio:.1%} < {CLOSEUP_MIN_RATIO:.0%}"
                   "——画面里脸很小，渲染更像远景而非特写。人判是否景别标签或渲染出错（特写应脸占 ≥20%）。")
        else:
            msg = (f"景别像素兜底：镜{num} 声明 {cls}(远景) 但 {rel} 实测脸占比 {ratio:.1%} > {WIDE_MAX_RATIO:.0%}"
                   "——大脸占满画面，渲染更像近景而非远景。人判是否景别标签或渲染出错。")
        findings.append({"level": sig["level"], "code": sig["code"], "msg": msg})
    return {"available": True, "checked": checked, "findings": findings}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    res = analyze(root, ns.episode)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not res.get("available"):
        print("⏭ 景别脸占比近似跳过：" + "；".join(res.get("notes", [])))
        return 0
    print(f"景别像素兜底（{ns.episode}）：判 {res['checked']} 镜 · {len(res['findings'])} 条 advisory")
    for f in res["findings"]:
        print(f"  [{f['level']}] {f['msg']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
