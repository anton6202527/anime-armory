#!/usr/bin/env python3
"""契约像素兜底（④·色调/光位）——把契约声明的 色调基线 / 场景光位锚 的「暖冷·明暗」意图量到实际渲染帧上对照。

**为什么**：本集视觉一致性契约把 `色调基线` / `场景光位锚` 标成 **block 级「焊进首帧像素」**，但全仓的
契约校验（`n2d_contract_diff`）只在**文本层誊抄 Diff**——出图侧写「冷青灰压暗」、视频侧誊抄对了就 pass，
**从不核对像素里到底是冷是暖、是明是暗**。这是审计点名的最大「松动」：声称焊像素、实则零像素核对。

本模块补上这一刀：解析契约里的暖/冷 + 明/暗意图，量本集出图帧的**全局暖冷(log(R/B))与亮度(luma)中位数**，
当像素**明确矛盾**于契约声明时出 advisory。设计上**保守**：
  - 默认 **WARN·人判**（色调本身模糊——冷场景里一盏暖烛特写也可能偏暖，宁可漏报不可误杀）；
  - 用**整集中位数**（不是逐帧）做主信号——单帧暖特写不会把冷基调误判成漂移，整集中位数翻向才坐实；
  - 暖/冷、明/暗都用**宽裕阈值**，只抓清楚矛盾。
纯 Pillow（与 image_qc 像素机检同栈），**默认无依赖产线也能跑**（不像 semantic_drift 需 torch）。

暖冷度量与 review 侧 color_grade_consistency **共用同一公式**（`n2d/_lib/n2d_color.warmth_log_ratio`，
log(R/B)·亮度无关），避免「同一个『暖冷』两套不可比度量」：本模块比的是**整集中位数 vs 契约意图**
（绝对·暖/冷/中性），review 比的是**每镜 vs 同场景中位**（相对·横跳）——口径一致、阈值语义不同。

阈值口径（可经 env 覆盖，应在真实渲染集按后端/风格标定）：
  N2D_TONE_WARM_MARGIN（暖冷 log(R/B) 中性区半宽，默认 0.10≈R/B 偏离 1.1×）· N2D_TONE_BRIGHT_LUMA（亮·0–255，默认 165）· N2D_TONE_DARK_LUMA（暗，默认 95）。

用法：python3 tone_light_contract.py <作品根> <第N集> [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)
from n2d_color import warmth_log_ratio  # noqa: E402  暖冷度量单一真值源（与 review color_grade 共用）


def _envf(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


WARM_COOL_MARGIN = _envf("N2D_TONE_WARM_MARGIN", 0.10)   # |log(R/B)| 超此值才判暖/冷（否则中性，不构成矛盾）
BRIGHT_LUMA = _envf("N2D_TONE_BRIGHT_LUMA", 165.0)        # luma 中位数高于此=亮
DARK_LUMA = _envf("N2D_TONE_DARK_LUMA", 95.0)            # luma 中位数低于此=暗

# 「领先 token 定基调」：契约 `色调基线` 常写「冷青灰压暗；残烛暖金只照脸」——冷在前=基调冷，暖金是点缀。
# 故按**最早出现位置**判暖/冷与明/暗的基调，不按计数（点缀词不夺基调）。
_WARM_TOKENS = ("暖", "暖金", "暖橙", "暖黄", "橙", "橘", "金黄", "琥珀", "烛光", "夕照", "暖光", "warm")
_COOL_TOKENS = ("冷", "冷青", "青灰", "冷蓝", "蓝调", "冷白", "月光", "幽蓝", "冷调", "cool")
_DARK_TOKENS = ("压暗", "压低", "暗沉", "昏暗", "幽暗", "低调", "暗调", "暗", "dim", "dark")
_BRIGHT_TOKENS = ("明亮", "高调", "通透", "明媚", "明快", "高亮", "亮调", "bright")


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def _first_hit(text: str, tokens: Sequence[str]) -> int:
    """text 中任一 token 最早出现的下标；都没有 → 一个很大的数（视作不存在）。纯函数。"""
    best = len(text) + 1
    for t in tokens:
        i = text.find(t)
        if i != -1 and i < best:
            best = i
    return best


def _kelvin_warmth(text: str) -> Optional[str]:
    """从 `3000K`/`5600K` 这类色温推暖冷：<4000=暖，>5000=冷，之间/无 → None。纯函数。"""
    import re
    hits = re.findall(r"(\d{3,5})\s*[kK]", text or "")
    temps = [int(h) for h in hits if h.isdigit()]
    temps = [t for t in temps if 1500 <= t <= 12000]
    if not temps:
        return None
    avg = sum(temps) / len(temps)
    if avg < 4000:
        return "warm"
    if avg > 5000:
        return "cool"
    return None


def parse_tone_intent(tone_text: str, light_text: str = "") -> Dict[str, Any]:
    """契约 色调基线(+光位锚) 文本 → {warmth: warm/cool/None, brightness: dark/bright/None, evidence}。纯函数·可测。

    warmth：色调基线里**领先**的暖/冷 token 定基调；色调里都没有时退到光位锚的色温(Kelvin)。
    brightness：色调基线里**领先**的明/暗 token 定基调。无信号 → None（该轴不检，避免臆造）。"""
    tone = str(tone_text or "")
    light = str(light_text or "")
    warm_i, cool_i = _first_hit(tone, _WARM_TOKENS), _first_hit(tone, _COOL_TOKENS)
    warmth: Optional[str] = None
    if warm_i < cool_i:
        warmth = "warm"
    elif cool_i < warm_i:
        warmth = "cool"
    if warmth is None:                       # 色调基线没暖冷词 → 退到色温
        warmth = _kelvin_warmth(tone) or _kelvin_warmth(light)
    dark_i, bright_i = _first_hit(tone, _DARK_TOKENS), _first_hit(tone, _BRIGHT_TOKENS)
    brightness: Optional[str] = None
    if dark_i < bright_i:
        brightness = "dark"
    elif bright_i < dark_i:
        brightness = "bright"
    return {"warmth": warmth, "brightness": brightness,
            "evidence": (tone or light).strip()[:80]}


def frame_metrics(r: float, g: float, b: float) -> Dict[str, float]:
    """一帧的 (R,G,B) 通道均值 → {warmth: log((R+1)/(B+1))(正=暖·与 review 共用 n2d_color), luma: 0.299R+0.587G+0.114B}。纯函数·可测。"""
    return {"warmth": warmth_log_ratio(r, g, b), "luma": 0.299 * float(r) + 0.587 * float(g) + 0.114 * float(b)}


def _median(xs: Sequence[float]) -> Optional[float]:
    vals = sorted(float(x) for x in xs)
    n = len(vals)
    if n == 0:
        return None
    mid = n // 2
    return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def tone_findings(intent: Mapping[str, Any], warmth_median: Optional[float], luma_median: Optional[float],
                  n_frames: int, *, warm_margin: float = WARM_COOL_MARGIN,
                  bright_luma: float = BRIGHT_LUMA, dark_luma: float = DARK_LUMA) -> List[Dict[str, str]]:
    """契约意图 × 整集像素中位数 → 矛盾 findings（纯函数·可测）。只在**清楚矛盾**时出 warn，否则空。"""
    out: List[Dict[str, str]] = []
    if warmth_median is None or luma_median is None or n_frames <= 0:
        return out
    ev = str(intent.get("evidence") or "")
    w_intent = intent.get("warmth")
    b_intent = intent.get("brightness")
    if w_intent == "warm" and warmth_median <= -warm_margin:
        out.append({"level": "warn", "code": "tone_warmth_contradiction",
                    "msg": f"色调像素兜底：契约基调=暖（{ev}），但本集 {n_frames} 帧实测整体偏冷"
                           f"（暖冷 log(R/B) 中位数 {warmth_median:.2f} ≤ −{warm_margin:.2f}）——渲染与契约暖冷相反，"
                           "人判是否整集走错色温/白平衡或契约写错。"})
    elif w_intent == "cool" and warmth_median >= warm_margin:
        out.append({"level": "warn", "code": "tone_warmth_contradiction",
                    "msg": f"色调像素兜底：契约基调=冷（{ev}），但本集 {n_frames} 帧实测整体偏暖"
                           f"（暖冷 log(R/B) 中位数 +{warmth_median:.2f} ≥ {warm_margin:.2f}）——渲染与契约暖冷相反，人判。"})
    if b_intent == "dark" and luma_median >= bright_luma:
        out.append({"level": "warn", "code": "tone_brightness_contradiction",
                    "msg": f"光位像素兜底：契约要求压暗/低调（{ev}），但本集 {n_frames} 帧实测整体偏亮"
                           f"（luma 中位数 {luma_median:.0f} ≥ {bright_luma:.0f}）——明暗与契约相反，人判。"})
    elif b_intent == "bright" and luma_median <= dark_luma:
        out.append({"level": "warn", "code": "tone_brightness_contradiction",
                    "msg": f"光位像素兜底：契约要求明亮/高调（{ev}），但本集 {n_frames} 帧实测整体偏暗"
                           f"（luma 中位数 {luma_median:.0f} ≤ {dark_luma:.0f}）——明暗与契约相反，人判。"})
    return out


# ── Pillow I/O（best-effort） ──────────────────────────────────────────────────

def measure_frame(abspath: str) -> Optional[Tuple[float, float, float]]:
    """读一帧 → (R,G,B) 通道均值（缩到 64px 加速、忽略 alpha）；读不到/损坏 → None。best-effort I/O。"""
    try:
        from PIL import Image  # type: ignore
        with Image.open(abspath) as im:
            im = im.convert("RGB")
            im.thumbnail((64, 64))
            px = list(im.getdata())
        if not px:
            return None
        n = len(px)
        r = sum(p[0] for p in px) / n
        g = sum(p[1] for p in px) / n
        b = sum(p[2] for p in px) / n
        return (r, g, b)
    except Exception:
        return None


def _read_contract_fields(root: Path, ep: str) -> Dict[str, str]:
    """出图侧 00_总览.md → {色调基线, 场景光位锚 ...}（复用 n2d_contract_diff 单一真值源解析）。读不到→{}。"""
    p = Path(root) / "出图" / ep / "prompt" / "00_总览.md"
    if not p.is_file():
        return {}
    lib = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "n2d", "_lib"))
    if lib not in sys.path:
        sys.path.insert(0, lib)
    try:
        import n2d_contract_diff as cdiff  # type: ignore
        sec = cdiff.extract_section(p.read_text(encoding="utf-8"))
        return cdiff.parse_contract_fields(sec) if sec is not None else {}
    except Exception:
        return {}


def analyze(root: Path, ep: str) -> Dict[str, Any]:
    """image_qc 集成入口：解析契约 色调/光位 意图 + 量本集帧像素中位数 → advisory findings。

    无契约/契约无暖冷明暗意图 → available True、findings 空（无可对照，不臆造）。
    无可测帧/Pillow 不可用 → available False（跳过）。"""
    fields = _read_contract_fields(Path(root), ep)
    intent = parse_tone_intent(fields.get("色调基线", ""), fields.get("场景光位锚", ""))
    if not intent.get("warmth") and not intent.get("brightness"):
        return {"available": True, "checked": 0, "intent": intent, "findings": [],
                "notes": ["契约 色调基线/光位锚 无可解析的暖冷·明暗意图——跳过像素对照（不臆造）。"]}
    png_dir = Path(root) / "出图" / ep / "图片"
    pngs = sorted(str(p) for p in png_dir.glob("*.png")) if png_dir.is_dir() else []
    warmths: List[float] = []
    lumas: List[float] = []
    for p in pngs:
        rgb = measure_frame(p)
        if rgb is None:
            continue
        m = frame_metrics(*rgb)
        warmths.append(m["warmth"])
        lumas.append(m["luma"])
    if not warmths:
        return {"available": False, "checked": 0, "intent": intent, "findings": [],
                "notes": ["本集无可测出图帧（或 Pillow 不可用）——色调/光位像素兜底跳过。"]}
    w_med, l_med = _median(warmths), _median(lumas)
    findings = tone_findings(intent, w_med, l_med, len(warmths))
    return {"available": True, "checked": len(warmths), "intent": intent,
            "warmth_median": round(w_med, 1) if w_med is not None else None,
            "luma_median": round(l_med, 1) if l_med is not None else None,
            "findings": findings}


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
        print("⏭ 色调/光位像素兜底跳过：" + "；".join(res.get("notes", [])))
        return 0
    intent = res.get("intent", {})
    print(f"色调/光位像素兜底（{ns.episode}）：契约 暖冷={intent.get('warmth')} 明暗={intent.get('brightness')} · "
          f"测 {res['checked']} 帧 · R−B中位 {res.get('warmth_median')} · luma中位 {res.get('luma_median')} · "
          f"{len(res['findings'])} 条 advisory")
    for f in res["findings"]:
        print(f"  [{f['level']}] {f['msg']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
