#!/usr/bin/env python3
"""风格归属佐证（⑤·选定风格 vs 实际渲染）——把 style_contract 选定的「风格名 + 风格禁忌」正面量到出图帧上对照。

**为什么**：`style_contract` 六字段（风格名/视觉基调/镜头与构图/光色策略/运动边界/风格禁忌）目前只有两类佐证——
  (a) **存在性**：image_preflight/image gate 缺六字段就 block；
  (b) **自洽性**：`tone_light_contract` 量色调暖冷、`shot_scale_contract` 量景别——比的是「相对一致 / 暖冷意图 vs 像素」。
**缺的是 (c) 正面「风格归属」**：这张图到底是不是你选的那个风格名、有没有踩「风格禁忌」（欧美脸漂移/插画化/
页游塑料盔甲/照片级毛孔）。选了「国漫写实」却整集漂成「插画设定图感」时，(a)(b) 都看不出来——色调可以自洽、
六字段可以写全，但风格归属错了。本模块补这一刀：以**风格锚图**（style_anchor，体现该风格该有的样子）为基准，
量本集出图帧的**风格指纹**（饱和度 / 明暗对比 / 线条边缘度）与锚对照，整集明显偏离=warn·人判。

设计上**保守**（与 tone_light_contract 同范式）：
  - 默认 **WARN·人判**（风格本就主观，宁可漏报不可误杀）；
  - 用**整集中位数**做主信号（单帧偏色不误判，整集指纹翻向才坐实）；
  - 未登记风格锚 → 风格归属不可机检，production hard block；先补风格锚再进入分镜图/视频；
  - 纯 Pillow（与 image_qc 像素机检同栈），**默认无依赖产线也能跑**；装了 VLM 后端可在上层升级成语义判定。

风格指纹三维（0–255 标度，可经 env 覆盖，应在真实渲染集按风格/后端标定）：
  N2D_STYLE_SAT_SCALE（饱和度偏离尺度，默认 55）· N2D_STYLE_CONTRAST_SCALE（对比偏离尺度，默认 65）·
  N2D_STYLE_EDGE_SCALE（线条边缘偏离尺度，默认 26）· N2D_STYLE_DEVIATION（判偏离的归一阈值，默认 1.0）。

用法：python3 style_attribution.py <作品根> <第N集> [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


STYLE_ANCHOR_REGISTRY = Path("出图") / "共享" / "style_anchor_registry.json"
STYLE_ANCHOR_READY_STATUSES = {"ready", "approved", "selected", "selected_anchor", "style_anchor", "pass", "ok"}


def _envf(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


SAT_SCALE = _envf("N2D_STYLE_SAT_SCALE", 55.0)        # |Δ饱和度中位| 超此尺度算一个单位偏离
CONTRAST_SCALE = _envf("N2D_STYLE_CONTRAST_SCALE", 65.0)  # |Δ明暗对比(p90−p10)| 尺度
EDGE_SCALE = _envf("N2D_STYLE_EDGE_SCALE", 26.0)      # |Δ线条边缘度| 尺度（cel/插画线条硬 vs 写实渐变软）
DEVIATION_THRESHOLD = _envf("N2D_STYLE_DEVIATION", 1.0)   # 归一距离≥此值=整集偏离风格锚（warn）


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def parse_style_intent(style_contract: Mapping[str, Any]) -> Dict[str, Any]:
    """storyboard.json 的 style_contract → {style_name, taboos[], anchors[]}。纯函数·可测。

    `风格禁忌` 兼容 list 或顿号/逗号分隔的字符串；`style_anchor` 兼容 str 单值或 list。"""
    sc = style_contract if isinstance(style_contract, Mapping) else {}
    name = str(sc.get("风格名") or sc.get("style_name") or "").strip()

    raw_taboo = sc.get("风格禁忌") or sc.get("taboos") or []
    if isinstance(raw_taboo, str):
        taboos = [t.strip() for t in _split_multi(raw_taboo) if t.strip()]
    elif isinstance(raw_taboo, (list, tuple)):
        taboos = [str(t).strip() for t in raw_taboo if str(t).strip()]
    else:
        taboos = []

    raw_anchor = sc.get("style_anchor") or sc.get("风格锚") or sc.get("anchors") or []
    if isinstance(raw_anchor, str):
        anchors = [raw_anchor.strip()] if raw_anchor.strip() else []
    elif isinstance(raw_anchor, (list, tuple)):
        anchors = [str(a).strip() for a in raw_anchor if str(a).strip()]
    else:
        anchors = []
    return {"style_name": name, "taboos": taboos, "anchors": anchors}


def _split_multi(text: str) -> List[str]:
    out = [text]
    for sep in ("、", "，", ",", "；", ";", "/"):
        nxt: List[str] = []
        for chunk in out:
            nxt.extend(chunk.split(sep))
        out = nxt
    return out


def _median(xs: Sequence[float]) -> Optional[float]:
    vals = sorted(float(x) for x in xs)
    n = len(vals)
    if n == 0:
        return None
    mid = n // 2
    return vals[mid] if n % 2 else (vals[mid - 1] + vals[mid]) / 2.0


def _percentile(xs: Sequence[float], q: float) -> Optional[float]:
    vals = sorted(float(x) for x in xs)
    if not vals:
        return None
    if len(vals) == 1:
        return vals[0]
    pos = q * (len(vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(vals) - 1)
    frac = pos - lo
    return vals[lo] * (1 - frac) + vals[hi] * frac


def median_fingerprint(fps: Sequence[Mapping[str, float]]) -> Optional[Dict[str, float]]:
    """多帧风格指纹 → 各维中位数（整集主信号，抗单帧异常）。纯函数·可测。"""
    if not fps:
        return None
    out: Dict[str, float] = {}
    for dim in ("sat", "contrast", "edge"):
        vals = [float(fp[dim]) for fp in fps if dim in fp and fp[dim] is not None]
        m = _median(vals)
        if m is None:
            return None
        out[dim] = round(m, 1)
    return out


def fingerprint_distance(a: Optional[Mapping[str, float]], b: Optional[Mapping[str, float]], *,
                         sat_scale: float = SAT_SCALE, contrast_scale: float = CONTRAST_SCALE,
                         edge_scale: float = EDGE_SCALE) -> Optional[float]:
    """两风格指纹的归一距离 = max(|Δ维|/该维尺度)。取 max 而非和：任一维明显翻向就坐实偏离。纯函数·可测。"""
    if not a or not b:
        return None
    scales = {"sat": sat_scale or 1.0, "contrast": contrast_scale or 1.0, "edge": edge_scale or 1.0}
    dist = 0.0
    for dim, scale in scales.items():
        if dim not in a or dim not in b:
            continue
        dist = max(dist, abs(float(a[dim]) - float(b[dim])) / scale)
    return round(dist, 3)


def _dominant_dim(a: Mapping[str, float], b: Mapping[str, float]) -> str:
    """偏离最大的那一维（给人话解释用）：饱和度 / 明暗对比 / 线条边缘。"""
    label = {"sat": "饱和度", "contrast": "明暗对比", "edge": "线条边缘度"}
    scales = {"sat": SAT_SCALE or 1.0, "contrast": CONTRAST_SCALE or 1.0, "edge": EDGE_SCALE or 1.0}
    best_dim, best = "sat", -1.0
    for dim in ("sat", "contrast", "edge"):
        if dim in a and dim in b:
            d = abs(float(a[dim]) - float(b[dim])) / scales[dim]
            if d > best:
                best_dim, best = dim, d
    return label[best_dim]


def style_findings(intent: Mapping[str, Any], anchor_fp: Optional[Mapping[str, float]],
                   episode_fp: Optional[Mapping[str, float]], n_frames: int, anchor_status: str,
                   *, deviation_threshold: float = DEVIATION_THRESHOLD,
                   worst: Optional[Tuple[str, float]] = None) -> List[Dict[str, str]]:
    """风格归属 findings（纯函数·可测）。

    缺风格锚/锚图丢失会让风格归属不可机检，按 production hard block；
    有锚后的整集指纹偏离仍是 warn·人判，避免把风格主观项过度机器化。
    """
    out: List[Dict[str, str]] = []
    name = str(intent.get("style_name") or "")
    if not name:
        return out  # 无风格名 → 由 image_preflight gate 的存在性校验负责，不在此双报
    taboos = intent.get("taboos") or []
    taboo_txt = "、".join(str(t) for t in taboos[:12]) or "（未声明）"

    if anchor_status == "missing":
        out.append({"level": "block", "code": "style_anchor_missing",
                    "msg": f"风格归属无法机检：style_contract 未登记风格锚（style_anchor）。"
                           f"请在定妆阶段出 1–2 张「{name}」风格锚图、登记进 style_contract.style_anchor，"
                           f"后续每集出图帧才能对锚做风格归属佐证；缺锚不得进入视频。"
                           f"当前只能人判：逐图核对是否踩 风格禁忌：{taboo_txt}。"})
        return out
    if anchor_status == "files_missing":
        out.append({"level": "block", "code": "style_anchor_file_missing",
                    "msg": f"风格归属无法机检：style_contract.style_anchor 已登记但锚图文件在磁盘上缺失。"
                           f"补出「{name}」风格锚图到登记路径后重跑；缺锚图不得进入视频。"
                           f"当前只能人判：核对是否踩 风格禁忌：{taboo_txt}。"})
        return out
    if anchor_fp is None or episode_fp is None or n_frames <= 0:
        return out  # 无可测帧 → analyze 已标 available False

    dist = fingerprint_distance(episode_fp, anchor_fp)
    if dist is not None and dist >= deviation_threshold:
        dim = _dominant_dim(episode_fp, anchor_fp)
        ev = (f"锚[饱和{anchor_fp.get('sat')}/对比{anchor_fp.get('contrast')}/边缘{anchor_fp.get('edge')}]"
              f" vs 本集[饱和{episode_fp.get('sat')}/对比{episode_fp.get('contrast')}/边缘{episode_fp.get('edge')}]")
        worst_txt = ""
        if worst and worst[0]:
            worst_txt = f"；最偏离镜：{os.path.basename(worst[0])}（偏离 {worst[1]:.2f}）"
        out.append({"level": "warn", "code": "style_attribution_drift",
                    "msg": f"风格归属佐证：本集 {n_frames} 帧整体风格指纹偏离风格锚（{dim}偏离最大，归一距离 {dist:.2f} ≥ "
                           f"{deviation_threshold:.2f}）——渲染可能漂出「{name}」。{ev}{worst_txt}。"
                           f"人判：是否踩 风格禁忌（{taboo_txt}）；确认漂移则回 n2d-image 重出本集偏离镜或重锚风格。"})
    return out


# ── Pillow I/O（best-effort） ──────────────────────────────────────────────────

def measure_fingerprint(abspath: str) -> Optional[Dict[str, float]]:
    """读一帧 → 风格指纹 {sat: HSV-S中位, contrast: luma(p90−p10), edge: FIND_EDGES均值}；读不到→None。best-effort。"""
    try:
        from PIL import Image, ImageFilter  # type: ignore
        with Image.open(abspath) as im:
            rgb = im.convert("RGB")
            rgb.thumbnail((96, 96))
            sat_px = list(rgb.convert("HSV").getdata())
            gray = rgb.convert("L")
            luma_px = list(gray.getdata())
            edge_px = list(gray.filter(ImageFilter.FIND_EDGES).getdata())
        if not sat_px or not luma_px:
            return None
        sat = _median([p[1] for p in sat_px])
        p90, p10 = _percentile(luma_px, 0.9), _percentile(luma_px, 0.1)
        contrast = (p90 - p10) if (p90 is not None and p10 is not None) else None
        edge = (sum(edge_px) / len(edge_px)) if edge_px else None
        if sat is None or contrast is None or edge is None:
            return None
        return {"sat": round(sat, 1), "contrast": round(contrast, 1), "edge": round(edge, 1)}
    except Exception:
        return None


def _load_style_contract(root: Path, ep: str) -> Dict[str, Any]:
    """脚本/<ep>/storyboard.json → style_contract（机器真值源，clean dict，不解析 markdown）。读不到→{}。"""
    p = Path(root) / "脚本" / ep / "storyboard.json"
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        sc = data.get("style_contract")
        return sc if isinstance(sc, dict) else {}
    except Exception:
        return {}


def _load_style_anchor_registry(root: Path) -> Dict[str, Any]:
    p = Path(root) / STYLE_ANCHOR_REGISTRY
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _registry_style_anchors(root: Path) -> List[str]:
    data = _load_style_anchor_registry(root)
    if not data:
        return []
    out: List[str] = []
    seen = set()

    def ready(status: Any) -> bool:
        text = str(status or "").strip().lower()
        return not text or text in STYLE_ANCHOR_READY_STATUSES

    def add(raw: Any, status: Any = "") -> None:
        text = str(raw or "").strip()
        if not text or Path(text).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            return
        if not ready(status):
            return
        rel = text if text.startswith("出图/") else str(Path("出图") / "共享" / "图片" / text)
        if rel not in seen:
            seen.add(rel)
            out.append(rel)

    def scan(node: Any) -> None:
        if isinstance(node, dict):
            if "path" in node:
                add(node.get("path"), node.get("status"))
                return
            for value in node.values():
                scan(value)
        elif isinstance(node, list):
            for item in node:
                scan(item)
        elif isinstance(node, str):
            add(node)

    scan(data.get("selected_anchor") or data.get("style_anchor"))
    scan(data.get("anchors"))
    return out


def _resolve_anchor_status(root: Path, anchors: Sequence[str]) -> Tuple[str, List[str]]:
    """风格锚解析：未登记→missing；登记但磁盘缺→files_missing；有存在的→ok + 存在的绝对路径列表。"""
    if not anchors:
        return "missing", []
    existing = [str((root / a)) for a in anchors if (root / a).is_file()]
    if not existing:
        return "files_missing", []
    return "ok", existing


def analyze(root: Path, ep: str) -> Dict[str, Any]:
    """image_qc 集成入口：风格锚 vs 本集出图帧的风格指纹对照 → advisory findings。

    无 style_contract / 无风格名 → available True、findings 空（存在性归 preflight gate，不双报）。
    未登记/缺失锚图 → available True，findings 出「人判清单」warn（降级，不臆造）。
    无可测帧或 Pillow 不可用 → available False（跳过）。"""
    root = Path(root)
    intent = parse_style_intent(_load_style_contract(root, ep))
    if not intent.get("anchors"):
        registry_anchors = _registry_style_anchors(root)
        if registry_anchors:
            intent = dict(intent)
            intent["anchors"] = registry_anchors
            intent["anchor_source"] = str(STYLE_ANCHOR_REGISTRY)
    if not intent.get("style_name"):
        return {"available": True, "checked": 0, "intent": intent, "findings": [],
                "notes": ["storyboard.json 无 style_contract.风格名——存在性由 image_preflight gate 负责，此处不双报。"]}

    anchor_status, anchor_paths = _resolve_anchor_status(root, intent.get("anchors") or [])
    if anchor_status != "ok":
        return {"available": True, "checked": 0, "intent": intent, "anchor_status": anchor_status,
                "findings": style_findings(intent, None, None, 0, anchor_status)}

    anchor_fps = [fp for fp in (measure_fingerprint(p) for p in anchor_paths) if fp]
    anchor_fp = median_fingerprint(anchor_fps)
    if anchor_fp is None:
        return {"available": False, "checked": 0, "intent": intent, "anchor_status": "files_missing",
                "findings": [], "notes": ["风格锚图无法读取（Pillow 不可用或文件损坏）——风格归属跳过。"]}

    png_dir = Path(root) / "出图" / ep / "图片"
    pngs = sorted(str(p) for p in png_dir.glob("*.png")) if png_dir.is_dir() else []
    shot_fps: List[Dict[str, float]] = []
    worst: Optional[Tuple[str, float]] = None
    for p in pngs:
        if os.path.basename(p) in {os.path.basename(a) for a in anchor_paths}:
            continue  # 别拿锚图自比
        fp = measure_fingerprint(p)
        if fp is None:
            continue
        shot_fps.append(fp)
        d = fingerprint_distance(fp, anchor_fp)
        if d is not None and (worst is None or d > worst[1]):
            worst = (p, d)
    if not shot_fps:
        return {"available": False, "checked": 0, "intent": intent, "anchor_status": "ok",
                "anchor_fingerprint": anchor_fp, "findings": [],
                "notes": ["本集无可测出图帧（或 Pillow 不可用）——风格归属跳过。"]}

    episode_fp = median_fingerprint(shot_fps)
    findings = style_findings(intent, anchor_fp, episode_fp, len(shot_fps), "ok", worst=worst)
    return {"available": True, "checked": len(shot_fps), "intent": intent, "anchor_status": "ok",
            "anchor_fingerprint": anchor_fp, "episode_fingerprint": episode_fp,
            "distance": fingerprint_distance(episode_fp, anchor_fp), "findings": findings}


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
        print("⏭ 风格归属佐证跳过：" + "；".join(res.get("notes", [])))
        return 0
    intent = res.get("intent", {})
    print(f"风格归属佐证（{ns.episode}）：风格名「{intent.get('style_name')}」· 锚={res.get('anchor_status')} · "
          f"测 {res.get('checked')} 帧 · 指纹距离 {res.get('distance')} · {len(res['findings'])} 条 advisory")
    for f in res["findings"]:
        print(f"  [{f['level']}] {f['msg']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
