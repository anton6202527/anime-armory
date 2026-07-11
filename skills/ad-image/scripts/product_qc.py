#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产品落档机检 product_qc —— 拍广告线的"产品/logo/品牌色漂移"前移闸门。

广告里**产品是主角**：包装/logo/品牌色一漂，整片报废，重抽要花真钱。本脚本把
产品一致性机检前移到**刚出完一批图、还没继续出视频**的最便宜的点，让漂移在这里
被硬挡，而不是等投放前 ad-review 才发现 → 省大量返工。机检架构包含
Pillow-or-graceful-fallback、prompt-lint、summary/findings JSON、hard-block 语义，
且**自包含**：只实现广告产品一致性相关子集。

四项机检（缺料必须在报告里明示降级，不臆造通过）：
1. PROMPT-LINT（HARD BLOCK，无 Pillow 也跑）：产品镜（storyboard.assets 标 `PROD_*: true`）
   的 `出图/分镜/prompt/镜头N.md` 必须含 参考图/资产引用块 + 身份锁定句 +
   负向约束(不要改包装文字/不要变形logo)。缺任一 → block。把"绝不文生图产品"从散文落成机检。
2. brand-color ΔE（需 Pillow+numpy）：产品镜取产品区域主色 vs `visual_contract.品牌色` HEX，
   CIE76 Lab ΔE 超阈值 → block，临界 → warn。无区域信息时同时查品牌色像素证据，
   能证明品牌色在画面中存在则降级 warn，完全找不到品牌色证据才 block。
3. product dHash 离群（需 Pillow）：产品镜组内算 dHash，某图对组的最小 Hamming 距离离群
   (> 阈值) → 漂移 warn/block；没有产品 bbox/裁剪时只作复核 warn，不用整张广告画面硬挡。
4. logo 模板匹配（需 Pillow+numpy，且注册了 logo 模板时才跑）：定妆库/产品/logo.png 在产品镜中
   做归一化互相关粗匹配；明显缺失/形变 → flag。无模板则干净跳过。

退出码：summary.block>0 → 非零（供 gate 据此硬挡 spend）；否则 0。

输出（**权威 schema**，供 ad-craft/gate.py 像读 contract_inheritance.json 一样读 summary.block）：
  <作品根>/出图/分镜/product_qc.json =
  {"summary":{"block":N,"warn":N,"info":N},
   "findings":[{"severity":"block|warn|info","shot":"镜头N",
                "check":"brand_color|product_dhash|logo|prompt_lint","reason":"..","detail":{..}}, ...]}

用法：
    python3 product_qc.py <作品根>/出图/第N集 [--storyboard PATH] [--strict]
    # 位置参数是出图阶段目录（拍广告不拆集，通常是 <作品根>/出图/分镜）；
    # 兼容 <作品根>/出图/第N集 等命名。storyboard 默认 <作品根>/脚本/storyboard.json。

测试（从本目录跑）：
    cd skills/ad-image/scripts && python3 -m pytest test_product_qc.py
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ── 阈值（模块级常量，便于审计/调参） ──────────────────────────────────────────
# 品牌色 ΔE（CIE76，Lab 欧氏距离）：人眼"刚好可辨"≈2.3；广告品牌色容忍很窄。
BRAND_COLOR_DE_WARN = 6.0    # ΔE > 6：肉眼明显偏色，疑环境光染偏 → warn（临界）。
BRAND_COLOR_DE_BLOCK = 12.0  # ΔE > 12：严重偏色（换了一个颜色档）→ block，必须重抽。
# 无产品 bbox 时，不能用整张广告图的均值硬挡；改用品牌色像素证据兜底。
BRAND_COLOR_PRESENCE_DE_STRICT = 12.0
BRAND_COLOR_PRESENCE_DE_LOOSE = 20.0
BRAND_COLOR_PRESENCE_RATIO_BLOCK = 0.0005  # <0.05% 且找不到接近品牌色 → 视为基本缺品牌色。
BRAND_COLOR_PRESENCE_RATIO_WARN = 0.0020   # <0.20% → 品牌色露出偏弱，人工复核。
# product dHash（8x8=64bit）组内离群：广告同款产品跨镜应高度一致。
DHASH_OUTLIER_WARN = 12      # 与组内最近邻的 Hamming 距离 > 12（约 19%）→ 疑漂移 warn。
DHASH_OUTLIER_BLOCK = 22     # > 22（约 34%）→ 明显异图（换了包装/角度全变）→ block。
DHASH_MIN_GROUP = 3          # 组内 < 3 张时离群判定不可靠，降级为 info（不下 warn/block）。
# logo 模板匹配：归一化互相关峰值（NCC ∈ [-1,1]）。
LOGO_NCC_WARN = 0.45         # 峰值 < 0.45：logo 疑形变/缺失 → warn。
LOGO_NCC_BLOCK = 0.25        # 峰值 < 0.25：基本看不到模板 logo → block。

# 产品区域采样：若 prompt 未给区域，取整图但只采"较饱和"像素近似产品主色（避开纯背景）。
SATURATION_MIN = 0.18        # HSV 饱和度下限，低于此视为背景/灰场，剔除后再取主色。

PROD_ASSET_RE = re.compile(r"\bPROD_[A-Za-z0-9_]*\b")
BRAND_ASSET_RE = re.compile(r"\bBRAND_[A-Za-z0-9_]*\b")
HEX_RE = re.compile(r"#([0-9a-fA-F]{6})\b")
SHOT_NUM_RE = re.compile(r"镜头\s*0*(\d+)|shot\s*0*(\d+)|镜头N0*(\d+)", re.I)
PRODUCT_SEMANTIC_MARKERS = (
    "产品", "包装", "logo", "品牌", "app", "应用", "界面", "手机", "屏幕",
    "cta", "end card", "endcard", "片尾", "预约", "购买", "下载", "扫码",
)
TEXT_LEGIBILITY_MARKERS = (
    "文字", "文案", "slogan", "cta", "legal", "法律声明", "字幕", "立即", "预约",
)
TEXT_LOCK_MARKERS = (
    "清晰", "可读", "不乱码", "不要乱码", "不改文字", "不要改文字", "保留", "准确显示",
)

# prompt-lint 必备块的判定关键词（任一命中即视为"有该块"）。
REFERENCE_MARKERS = ("参考图", "资产引用", "资产身份注册", "定妆_", "image2image", "图生图", "i2i", "母图")
IDENTITY_LOCK_MARKERS = ("身份锁定句", "身份锁定", "同一款包装", "同一张脸", "同一 logo", "同一logo",
                         "同一品牌色", "同一个包装", "同一包装")
# 负向必须同时覆盖"包装文字"和"logo"两类禁改（缺一类即不合格）。
NEG_TEXT_MARKERS = ("不要改包装文字", "不改包装文字", "不要改文字", "包装文字不", "不要乱码", "不改文字")
NEG_LOGO_MARKERS = ("不要变形 logo", "不要变形logo", "不变形 logo", "不变形logo",
                    "logo 不变形", "logo不变形", "不要改 logo", "不改 logo", "不要变形标志")
PROHIBITED_LOCAL_PATCH_STRONG_TOKENS = (
    "local_product_patch", "product_patch", "logo_patch", "packaging_patch", "package_patch",
    "local_face_patch", "face_patch", "facefix", "faceswap", "face_swap", "poisson",
    "alpha_blend", "pasteback", "paste_back", "贴包装", "贴logo", "贴 logo", "贴标",
    "贴脸", "换脸", "裁脸", "本地贴图",
)
PROHIBITED_LOCAL_PATCH_OPERATION_TOKENS = (
    "patch", "paste", "blend", "clone", "swap", "overlay", "贴回", "贴入", "移植", "换",
)


# ── Pillow / numpy 优雅降级 ─────────────────────────────────────────────────────

def _load_imaging() -> Tuple[Any, Any]:
    """惰性加载 (PIL.Image, numpy)；任一不可用返回 (None, None)。与 image_qc 同哲学：
    宁可降级交人判 + 记 info，绝不让整个落档机检崩。"""
    try:
        from PIL import Image  # type: ignore
        import numpy as np  # type: ignore
        return Image, np
    except Exception:
        return None, None


# ── 路径解析 ─────────────────────────────────────────────────────────────────────

def resolve_paths(stage_dir: Path, storyboard_arg: Optional[str]) -> Dict[str, Path]:
    """从位置参数（出图阶段目录，如 <作品根>/出图/分镜 或 <作品根>/出图/第N集）解析：
    - root：作品根（stage_dir 的祖父，即 出图 的上一级）
    - prompt_dir：<stage_dir>/prompt
    - out_json：**权威落点 <作品根>/出图/分镜/product_qc.json**（无论传入哪个 stage 目录，
      都按 schema 约定写到 出图/分镜，gate 固定从那里读）
    - storyboard：--storyboard 指定，否则 <root>/脚本/storyboard.json
    - overview：<stage_dir>/prompt/00_总览.md（品牌色兜底来源）
    - logo_template：<root>/出图/共享/定妆库/产品/logo.png（不存在则后续跳过 logo 检）
    """
    stage_dir = stage_dir.resolve()
    # stage_dir 形如 .../出图/分镜；root = .../（出图 的父）
    chutu = stage_dir.parent  # 出图
    root = chutu.parent
    out_json = root / "出图" / "分镜" / "product_qc.json"
    sb = Path(storyboard_arg).resolve() if storyboard_arg else (root / "脚本" / "storyboard.json")
    # logo 模板可能落在两处常见位置，择存在者
    logo_candidates = [
        root / "出图" / "共享" / "定妆库" / "产品" / "logo.png",
        root / "出图" / "共享" / "定妆库" / "logo.png",
        root / "出图" / "共享" / "图片" / "logo.png",
    ]
    logo_template = next((p for p in logo_candidates if p.exists()), logo_candidates[0])
    return {
        "root": root,
        "stage_dir": stage_dir,
        "prompt_dir": stage_dir / "prompt",
        "out_json": out_json,
        "storyboard": sb,
        "overview": stage_dir / "prompt" / "00_总览.md",
        "logo_template": logo_template,
    }


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


# ── storyboard：产品镜识别 + 品牌色 ────────────────────────────────────────────────

def _shot_label(shot: Dict[str, Any], idx: int) -> str:
    """统一镜头标识为 `镜头N`（N 来自 id/clip_id/shot_id 里的数字，提不出用序号）。"""
    raw = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id")
              or shot.get("shot") or shot.get("clip") or "")
    m = SHOT_NUM_RE.search(raw)
    if m:
        n = next((g for g in m.groups() if g), None)
        if n:
            return f"镜头{int(n)}"
    return f"镜头{idx}"


def product_shots(storyboard: Dict[str, Any]) -> List[str]:
    """storyboard.json → 产品/品牌/UI 镜标签集。

    强规则：assets 里有 `PROD_*: true`。
    兜底规则：App/UI/包装/logo/CTA/end-card 语义镜也纳入 QC，防止未结构化绑定的产品镜逃逸。
    纯函数·可测。
    """
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    out: List[str] = []
    for i, sh in enumerate(shots, 1):
        if not isinstance(sh, dict):
            continue
        assets = sh.get("assets") or {}
        is_prod = False
        if isinstance(assets, dict):
            for k, v in assets.items():
                if PROD_ASSET_RE.fullmatch(str(k)) and bool(v):
                    is_prod = True
                    break
        elif isinstance(assets, (list, tuple)):
            is_prod = any(PROD_ASSET_RE.fullmatch(str(a)) for a in assets)
        text = " ".join(str(sh.get(k) or "") for k in (
            "scene", "shot", "frame", "prompt", "desc", "description", "product_lock", "subtitle", "vo"
        )).lower()
        if not is_prod and any(marker in text for marker in PRODUCT_SEMANTIC_MARKERS):
            is_prod = True
        if is_prod:
            out.append(_shot_label(sh, i))
    return out


def storyboard_shot_by_label(storyboard: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """`镜头N` → storyboard shot。"""
    shots = storyboard.get("shots") or storyboard.get("clips") or []
    out: Dict[str, Dict[str, Any]] = {}
    for i, sh in enumerate(shots, 1):
        if isinstance(sh, dict):
            out[_shot_label(sh, i)] = sh
    return out


def product_asset_ids(shot: Dict[str, Any]) -> List[str]:
    assets = shot.get("assets") if isinstance(shot, dict) else None
    ids = set()
    if isinstance(assets, dict):
        ids.update(str(k) for k, v in assets.items() if v and PROD_ASSET_RE.fullmatch(str(k)))
    elif isinstance(assets, (list, tuple)):
        ids.update(str(x) for x in assets if PROD_ASSET_RE.fullmatch(str(x)))
    text = " ".join(str(shot.get(k) or "") for k in ("prompt", "product_lock", "desc", "description", "shot", "scene"))
    ids.update(PROD_ASSET_RE.findall(text))
    return sorted(ids)


def brand_asset_ids(shot: Dict[str, Any]) -> List[str]:
    assets = shot.get("assets") if isinstance(shot, dict) else None
    ids = set()
    if isinstance(assets, dict):
        ids.update(str(k) for k, v in assets.items() if v and BRAND_ASSET_RE.fullmatch(str(k)))
    elif isinstance(assets, (list, tuple)):
        ids.update(str(x) for x in assets if BRAND_ASSET_RE.fullmatch(str(x)))
    text = " ".join(str(shot.get(k) or "") for k in ("prompt", "product_lock", "desc", "description", "shot", "scene"))
    ids.update(BRAND_ASSET_RE.findall(text))
    return sorted(ids)


def _flatten_registry_ids(value: Any) -> set:
    ids = set()
    if isinstance(value, dict):
        rid = str(value.get("id") or value.get("asset_id") or "").strip()
        if rid:
            ids.add(rid)
        for key, item in value.items():
            if isinstance(key, str) and (key.startswith("PROD_") or key.startswith("BRAND_")):
                ids.add(key)
            if isinstance(item, dict):
                rid = str(item.get("id") or item.get("asset_id") or "").strip()
                if rid:
                    ids.add(rid)
                ids.update(_flatten_registry_ids(item))
            elif isinstance(item, list):
                ids.update(_flatten_registry_ids(item))
    elif isinstance(value, list):
        for item in value:
            ids.update(_flatten_registry_ids(item))
    return ids


def load_asset_registry_ids(root: Path) -> set:
    """读取广告线资产 registry 中已登记的 PROD_/BRAND_ id。缺失返回空集合。"""
    candidates = [
        root / "出图" / "共享" / "asset_registry.json",
        root / "设定库" / "asset_registry.json",
        root / "设定库" / "assets.json",
    ]
    ids = set()
    for path in candidates:
        data = load_json(path)
        if data:
            ids.update(_flatten_registry_ids(data))
    return ids


def check_asset_bindings(label: str, shot: Dict[str, Any], registry_ids: set) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    prod_ids = product_asset_ids(shot)
    brand_ids = brand_asset_ids(shot)
    if not prod_ids:
        findings.append(_finding(
            "block", label, "asset_binding",
            "产品/界面/品牌镜缺结构化 `PROD_*` 资产 ID；必须先把 hero product/App/UI 包装写入 storyboard.assets 并登记定妆。",
            {"missing": "PROD_*"},
        ))
    for pid in prod_ids:
        if registry_ids and pid not in registry_ids:
            findings.append(_finding("warn", label, "asset_binding",
                                     f"产品资产 {pid} 未在 asset_registry 中找到，建议先登记 logo/品牌色/包装禁漂项。",
                                     {"asset_id": pid}))
        elif not registry_ids:
            findings.append(_finding("warn", label, "asset_binding",
                                     "未找到广告 asset_registry，产品/logo/品牌色禁漂项只能从 prompt 推断，建议先建 registry。",
                                     {"asset_id": pid, "degraded": "no_asset_registry"}))
    if not brand_ids:
        findings.append(_finding("warn", label, "asset_binding",
                                 "未绑定 `BRAND_*` 品牌资产；片尾/品牌露出建议结构化锁 logo、slogan、品牌色。",
                                 {"missing": "BRAND_*"}))
    return findings


def check_text_legibility(label: str, shot: Dict[str, Any], prompt_text: Optional[str]) -> List[Dict[str, Any]]:
    text = " ".join(str(shot.get(k) or "") for k in ("prompt", "product_lock", "shot", "scene")).lower()
    requires_text = any(marker.lower() in text for marker in TEXT_LEGIBILITY_MARKERS)
    if not requires_text:
        return []
    if prompt_text is None:
        return [_finding("block", label, "text_legibility",
                         "本镜声明品牌/UI/CTA/法律文字，但逐镜 prompt 缺失，无法锁文字可读性。",
                         {"missing_prompt": True})]
    if not any(marker in prompt_text for marker in TEXT_LOCK_MARKERS):
        return [_finding("warn", label, "text_legibility",
                         "本镜含品牌/UI/CTA/法律文字，但 prompt 未明确“文字清晰可读/不乱码/保留原文”，需补文字锁定句。",
                         {"requires_text_lock": True})]
    return []


def check_safe_area(label: str, shot: Dict[str, Any]) -> List[Dict[str, Any]]:
    safe = shot.get("safe_area") or shot.get("安全区") or {}
    text = " ".join(str(shot.get(k) or "") for k in ("prompt", "product_lock", "shot", "scene")).lower()
    high_risk = any(marker in text for marker in ("logo", "cta", "片尾", "end card", "endcard", "产品", "界面", "手机", "屏幕"))
    if not high_risk:
        return []
    if not isinstance(safe, dict) or not safe:
        return [_finding("warn", label, "safe_area",
                         "产品/logo/UI/CTA 镜缺 8x8 万能安全区声明；多比例 reframe 可能裁掉核心资产。",
                         {"missing": "safe_area"})]
    center = safe.get("core_in_center_4x4")
    if center is False:
        return [_finding("block", label, "safe_area",
                         "safe_area.core_in_center_4x4=false，核心产品/logo/CTA 不在中心安全区，必须重构图。",
                         {"core_in_center_4x4": False})]
    return []


def brand_color_hex(storyboard: Dict[str, Any], overview_text: str = "") -> Optional[str]:
    """品牌色 HEX：优先 storyboard.visual_contract.品牌色，否则从 00_总览.md 抓首个 #RRGGBB。
    返回标准化 '#rrggbb' 或 None。纯函数·可测。"""
    vc = storyboard.get("visual_contract") or {}
    raw = ""
    if isinstance(vc, dict):
        raw = str(vc.get("品牌色") or vc.get("brand_color") or "")
    m = HEX_RE.search(raw)
    if not m:
        m = HEX_RE.search(overview_text or "")
    if not m:
        return None
    return "#" + m.group(1).lower()


# ── 1) PROMPT-LINT（HARD BLOCK，无 Pillow 也跑） ──────────────────────────────────

def _shot_prompt_path(prompt_dir: Path, shot_label: str) -> Optional[Path]:
    """`镜头N` → prompt 文件。容忍 镜头N.md / 镜头0N.md / 镜头_N.md。"""
    m = re.search(r"(\d+)", shot_label)
    if not m:
        cand = prompt_dir / f"{shot_label}.md"
        return cand if cand.exists() else None
    n = int(m.group(1))
    for name in (f"镜头{n}.md", f"镜头{n:02d}.md", f"镜头_{n}.md", f"shot{n}.md", f"{shot_label}.md"):
        cand = prompt_dir / name
        if cand.exists():
            return cand
    return None


def lint_product_prompt(shot_label: str, text: Optional[str]) -> List[Dict[str, Any]]:
    """单个产品镜 prompt 的 hard-lint：缺 参考图块 / 身份锁定句 / 负向(文字+logo) → block。
    text=None（prompt 文件缺失）→ 一条 block（产品镜没 prompt = 无从锁产品）。纯函数·可测。"""
    findings: List[Dict[str, Any]] = []
    if text is None:
        findings.append(_finding("block", shot_label, "prompt_lint",
                                 "产品镜缺逐镜 prompt 文件（无从锁产品参考/品牌色/负向，纯文生图必漂）",
                                 {"missing_prompt": True}))
        return findings
    if not any(m in text for m in REFERENCE_MARKERS):
        findings.append(_finding("block", shot_label, "prompt_lint",
                                 "产品镜缺『参考图/资产引用』块（绝不文生图产品：必 image2image + 产品定妆参考）",
                                 {"missing": "reference_block"}))
    if not PROD_ASSET_RE.search(text):
        findings.append(_finding("block", shot_label, "prompt_lint",
                                 "产品镜缺结构化产品资产 ID（PROD_*）；执行端无法把本镜绑定到产品定妆/禁改清单",
                                 {"missing": "product_asset_id"}))
    if not any(m in text for m in IDENTITY_LOCK_MARKERS):
        findings.append(_finding("block", shot_label, "prompt_lint",
                                 "产品镜缺『身份锁定句』（同一款包装/同一 logo/同一品牌色——多参考后端最敏感的锁产品句）",
                                 {"missing": "identity_lock"}))
    has_neg_text = any(m in text for m in NEG_TEXT_MARKERS)
    has_neg_logo = any(m in text for m in NEG_LOGO_MARKERS)
    if not (has_neg_text and has_neg_logo):
        miss = []
        if not has_neg_text:
            miss.append("不要改包装文字")
        if not has_neg_logo:
            miss.append("不要变形 logo")
        findings.append(_finding("block", shot_label, "prompt_lint",
                                 f"产品镜负向约束不全，缺：{ '、'.join(miss) }（包装文字/logo 是 AI 生图最易崩处）",
                                 {"missing_negatives": miss}))
    return findings


# ── 颜色：HEX → Lab，CIE76 ΔE ────────────────────────────────────────────────────

def hex_to_rgb(hexstr: str) -> Tuple[int, int, int]:
    s = hexstr.lstrip("#")
    return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)


def _srgb_to_lab(rgb: Sequence[float]) -> Tuple[float, float, float]:
    """sRGB (0-255) → CIELAB (D65)。纯标准库，无需 numpy（也供无 Pillow 时的纯函数测试）。"""
    def _lin(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (_lin(rgb[0]), _lin(rgb[1]), _lin(rgb[2]))
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.0
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883

    def _f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else (7.787 * t + 16.0 / 116.0)
    fx, fy, fz = _f(x), _f(y), _f(z)
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def delta_e_cie76(rgb1: Sequence[float], rgb2: Sequence[float]) -> float:
    """两 sRGB 颜色的 CIE76 ΔE（Lab 欧氏距离）。纯函数·可测，不依赖 Pillow/numpy。"""
    l1 = _srgb_to_lab(rgb1)
    l2 = _srgb_to_lab(rgb2)
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(l1, l2)))


def _srgb_array_to_lab(arr: Any, np: Any) -> Any:
    """Vectorized sRGB array (N,3, 0-255) → CIELAB (D65)."""
    rgb = arr.astype(np.float64) / 255.0
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    r, g, b = lin[:, 0], lin[:, 1], lin[:, 2]
    x = (r * 0.4124 + g * 0.3576 + b * 0.1805) / 0.95047
    y = (r * 0.2126 + g * 0.7152 + b * 0.0722) / 1.0
    z = (r * 0.0193 + g * 0.1192 + b * 0.9505) / 1.08883
    fx = np.where(x > 0.008856, np.cbrt(x), 7.787 * x + 16.0 / 116.0)
    fy = np.where(y > 0.008856, np.cbrt(y), 7.787 * y + 16.0 / 116.0)
    fz = np.where(z > 0.008856, np.cbrt(z), 7.787 * z + 16.0 / 116.0)
    return np.stack((116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz)), axis=1)


def _delta_e_array(arr: Any, target_rgb: Sequence[float], np: Any) -> Any:
    target = np.asarray(target_rgb, dtype=np.float64).reshape(1, 3)
    lab = _srgb_array_to_lab(arr, np)
    target_lab = _srgb_array_to_lab(target, np)[0]
    return np.sqrt(((lab - target_lab) ** 2).sum(axis=1))


# ── 2) brand-color ΔE（需 Pillow+numpy） ─────────────────────────────────────────

def dominant_color(img_path: Path, Image: Any, np: Any,
                   bbox: Optional[Tuple[int, int, int, int]] = None) -> Optional[Tuple[float, float, float]]:
    """取产品区域（bbox 像素框，无则整图剔背景）的主色 RGB 均值。失败 → None。"""
    try:
        im = Image.open(str(img_path)).convert("RGB")
    except Exception:
        return None
    if bbox:
        try:
            im = im.crop(bbox)
        except Exception:
            pass
    arr = np.asarray(im, dtype=np.float64).reshape(-1, 3)
    if arr.size == 0:
        return None
    if bbox is None:
        # 无区域信息：剔除低饱和背景像素，对剩余取均值，近似产品主色。
        mx = arr.max(axis=1)
        mn = arr.min(axis=1)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
        keep = arr[sat >= SATURATION_MIN]
        if keep.shape[0] >= max(16, arr.shape[0] // 100):
            arr = keep
    mean = arr.mean(axis=0)
    return float(mean[0]), float(mean[1]), float(mean[2])


def brand_color_presence(img_path: Path, Image: Any, np: Any, brand_hex: str) -> Optional[Dict[str, Any]]:
    """Check whether the declared brand color exists in a full ad frame.

    This is intentionally different from dominant color. Lifestyle ads often have warm desks,
    hands, faces, or room light as the image dominant color while the brand/UI color occupies
    a smaller but still meaningful product region.
    """
    try:
        im = Image.open(str(img_path)).convert("RGB")
    except Exception:
        return None
    max_edge = max(im.size)
    if max_edge > 540:
        scale = 540.0 / float(max_edge)
        im = im.resize((max(1, int(im.size[0] * scale)), max(1, int(im.size[1] * scale))), Image.BILINEAR)
    arr = np.asarray(im, dtype=np.float64).reshape(-1, 3)
    if arr.size == 0:
        return None
    des = _delta_e_array(arr, hex_to_rgb(brand_hex), np)
    strict = des <= BRAND_COLOR_PRESENCE_DE_STRICT
    loose = des <= BRAND_COLOR_PRESENCE_DE_LOOSE
    min_idx = int(des.argmin())
    return {
        "pixel_count": int(arr.shape[0]),
        "min_delta_e": round(float(des[min_idx]), 2),
        "nearest_rgb": [int(c) for c in arr[min_idx].tolist()],
        "ratio_delta_e12": round(float(strict.mean()), 6),
        "ratio_delta_e20": round(float(loose.mean()), 6),
        "threshold_ratio_block": BRAND_COLOR_PRESENCE_RATIO_BLOCK,
        "threshold_ratio_warn": BRAND_COLOR_PRESENCE_RATIO_WARN,
    }


def check_brand_color(shot_label: str, img_path: Optional[Path], brand_hex: Optional[str],
                      Image: Any, np: Any,
                      bbox: Optional[Tuple[int, int, int, int]] = None) -> List[Dict[str, Any]]:
    """单产品镜的品牌色 ΔE 检。无图/无品牌色/无 Pillow → info（降级）。纯路径计算之外的像素部分。"""
    if brand_hex is None:
        return [_finding("info", shot_label, "brand_color",
                         "未声明品牌色 HEX（storyboard.visual_contract.品牌色 / 00_总览.md），跳过偏色检",
                         {"degraded": "no_brand_hex"})]
    if img_path is None or not Path(img_path).exists():
        return [_finding("info", shot_label, "brand_color",
                         "产品镜图未落档，品牌色检 pending", {"degraded": "no_image"})]
    if Image is None or np is None:
        return [_finding("info", shot_label, "brand_color",
                         "缺 Pillow/numpy，品牌色 ΔE 降级跳过（装 pillow+numpy 后重跑）",
                         {"degraded": "no_pillow"})]
    dom = dominant_color(Path(img_path), Image, np, bbox)
    if dom is None:
        return [_finding("info", shot_label, "brand_color",
                         "读图失败，品牌色检跳过", {"degraded": "read_fail"})]
    target = hex_to_rgb(brand_hex)
    de = delta_e_cie76(dom, target)
    detail = {"brand_hex": brand_hex, "sampled_rgb": [round(c, 1) for c in dom],
              "delta_e": round(de, 2), "region": "bbox" if bbox else "whole_image",
              "threshold_warn": BRAND_COLOR_DE_WARN, "threshold_block": BRAND_COLOR_DE_BLOCK}
    if bbox is None:
        presence = brand_color_presence(Path(img_path), Image, np, brand_hex)
        if presence:
            detail["presence"] = presence
            strict_ratio = float(presence.get("ratio_delta_e12") or 0.0)
            loose_ratio = float(presence.get("ratio_delta_e20") or 0.0)
            min_de = float(presence.get("min_delta_e") or 999.0)
            has_brand_evidence = (
                strict_ratio >= BRAND_COLOR_PRESENCE_RATIO_BLOCK
                or loose_ratio >= BRAND_COLOR_PRESENCE_RATIO_WARN
            )
            weak_brand_evidence = min_de <= BRAND_COLOR_PRESENCE_DE_LOOSE
            if not has_brand_evidence:
                if weak_brand_evidence:
                    return [_finding("warn", shot_label, "brand_color",
                                     f"品牌色 {brand_hex} 像素证据偏少（ΔE≤12 占比 {strict_ratio:.3%}），"
                                     "缺产品区域信息，需人工复核品牌露出是否足够", detail)]
                detail["confidence"] = "heuristic"
                return [_finding("warn", shot_label, "brand_color",
                                 f"画面中基本检不到品牌色 {brand_hex}（最小 ΔE={min_de:.1f}，"
                                 f"ΔE≤12 占比 {strict_ratio:.3%}）；无产品 ROI 时仅提示人工复核", detail)]
            if de > BRAND_COLOR_DE_WARN:
                return [_finding("warn", shot_label, "brand_color",
                                 f"整图主色偏离 {brand_hex}（ΔE={de:.1f}），但检测到品牌色像素证据；"
                                 "缺产品区域信息，按广告全图降级复核，不硬挡", detail)]
        elif de > BRAND_COLOR_DE_BLOCK:
            return [_finding("warn", shot_label, "brand_color",
                             f"整图主色偏离 {brand_hex}（ΔE={de:.1f}），但品牌色像素证据检测失败；"
                             "缺产品区域信息，降级人工复核", detail)]
    if de > BRAND_COLOR_DE_BLOCK:
        return [_finding("block", shot_label, "brand_color",
                         f"品牌色严重偏离 {brand_hex}（ΔE={de:.1f}>{BRAND_COLOR_DE_BLOCK}），整片品牌色报废，必重抽", detail)]
    if de > BRAND_COLOR_DE_WARN:
        sev = "warn"
        reason = f"品牌色偏离 {brand_hex}（ΔE={de:.1f}>{BRAND_COLOR_DE_WARN}），疑环境光染偏，人工复核"
        if bbox is None:
            reason += "；区域信息缺失，采整图主色（降级判定）"
        return [_finding(sev, shot_label, "brand_color", reason, detail)]
    if bbox is None:
        # 区域缺失但通过：降级 warn（image_qc 哲学：缺料即便看似通过也要可见为降级）。
        return [_finding("warn", shot_label, "brand_color",
                         f"品牌色 ΔE={de:.1f} 在阈内，但缺产品区域信息（采整图主色，降级判定，建议人工确认）", detail)]
    return []  # 有区域 + 在阈内 = 干净通过，不产 finding。


# ── 3) product dHash 离群（需 Pillow） ───────────────────────────────────────────

def dhash(img_path: Path, Image: Any, size: int = 8) -> Optional[int]:
    """8x8 dHash（行向相邻差），返回 64-bit 整数。失败 → None。"""
    try:
        im = Image.open(str(img_path)).convert("L").resize((size + 1, size), Image.BILINEAR)
    except Exception:
        return None
    try:
        px = list(im.get_flattened_data())  # Pillow ≥12
    except AttributeError:
        px = list(im.getdata())
    w = size + 1
    bits = 0
    for r in range(size):
        for c in range(size):
            bit = 1 if px[r * w + c] < px[r * w + c + 1] else 0
            bits = (bits << 1) | bit
    return bits


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def check_dhash_group(labels_paths: List[Tuple[str, Optional[Path]]], Image: Any, *,
                      product_region_known: bool = False) -> List[Dict[str, Any]]:
    """产品镜组内 dHash 离群：每图取与组内其它图的最小 Hamming 距离，超阈值即漂移。
    组 < DHASH_MIN_GROUP 张 → info（样本不足，不下 warn/block）。纯逻辑可测（Image 可注入）。"""
    if Image is None:
        return [_finding("info", "-", "product_dhash",
                         "缺 Pillow，产品 dHash 离群检降级跳过", {"degraded": "no_pillow"})]
    hashes: List[Tuple[str, Optional[Path], Optional[int]]] = []
    for label, p in labels_paths:
        h = dhash(Path(p), Image) if (p and Path(p).exists()) else None
        hashes.append((label, p, h))
    valid = [(lb, h) for lb, p, h in hashes if h is not None]
    if len(valid) < DHASH_MIN_GROUP:
        return [_finding("info", "-", "product_dhash",
                         f"已落档产品图 {len(valid)} 张 < {DHASH_MIN_GROUP}，组内离群判定样本不足，跳过",
                         {"degraded": "small_group", "count": len(valid)})]
    findings: List[Dict[str, Any]] = []
    for lb, h in valid:
        dists = [hamming(h, oh) for olb, oh in valid if olb != lb]
        if not dists:
            continue
        nn = min(dists)
        detail = {"min_hamming": nn, "group_size": len(valid),
                  "threshold_warn": DHASH_OUTLIER_WARN, "threshold_block": DHASH_OUTLIER_BLOCK,
                  "region": "product_bbox" if product_region_known else "whole_image"}
        if nn > DHASH_OUTLIER_BLOCK:
            if product_region_known:
                detail["confidence"] = "heuristic"
                findings.append(_finding("warn", lb, "product_dhash",
                                         f"产品 ROI 与组内最近邻差 {nn} bit (>{DHASH_OUTLIER_BLOCK})，启发式提示人工复核", detail))
            else:
                findings.append(_finding("warn", lb, "product_dhash",
                                         f"整张广告图与组内最近邻差 {nn} bit (>{DHASH_OUTLIER_BLOCK})；"
                                         "缺产品区域裁剪，不能据此判定产品漂移，降级人工复核", detail))
        elif nn > DHASH_OUTLIER_WARN:
            findings.append(_finding("warn", lb, "product_dhash",
                                     f"产品图与组内最近邻差 {nn} bit (>{DHASH_OUTLIER_WARN})，疑产品漂移，人工复核", detail))
    return findings


# ── 4) logo 模板匹配（需 Pillow+numpy，且 logo 模板已注册） ───────────────────────

def _ncc_peak(template: Any, image: Any, np: Any) -> float:
    """模板在图中的最大归一化互相关（粗匹配，定步长滑窗）。返回峰值 ∈ [-1,1]。"""
    th, tw = template.shape
    ih, iw = image.shape
    if th > ih or tw > iw:
        return -1.0
    t = template - template.mean()
    t_norm = math.sqrt(float((t * t).sum())) or 1e-6
    best = -1.0
    step = max(1, min(ih, iw) // 64)  # 粗步长，足够判 logo 在不在 + 大致完整
    for y in range(0, ih - th + 1, step):
        for x in range(0, iw - tw + 1, step):
            win = image[y:y + th, x:x + tw]
            w = win - win.mean()
            w_norm = math.sqrt(float((w * w).sum())) or 1e-6
            ncc = float((t * w).sum()) / (t_norm * w_norm)
            if ncc > best:
                best = ncc
    return best


def check_logo(shot_label: str, img_path: Optional[Path], logo_template: Path,
               Image: Any, np: Any) -> List[Dict[str, Any]]:
    """单产品镜的 logo 存在/形变粗检。仅当 logo 模板存在时调用（无模板由 caller 跳过）。"""
    if img_path is None or not Path(img_path).exists():
        return [_finding("info", shot_label, "logo",
                         "产品镜图未落档，logo 检 pending", {"degraded": "no_image"})]
    if Image is None or np is None:
        return [_finding("info", shot_label, "logo",
                         "缺 Pillow/numpy，logo 模板匹配降级跳过", {"degraded": "no_pillow"})]
    try:
        tmpl = Image.open(str(logo_template)).convert("L")
        # 模板缩到 ≤96px 边，控制粗匹配开销
        scale = min(1.0, 96.0 / max(tmpl.size))
        if scale < 1.0:
            tmpl = tmpl.resize((max(1, int(tmpl.size[0] * scale)), max(1, int(tmpl.size[1] * scale))), Image.BILINEAR)
        img = Image.open(str(img_path)).convert("L")
        iscale = min(1.0, 512.0 / max(img.size))
        if iscale < 1.0:
            img = img.resize((max(1, int(img.size[0] * iscale)), max(1, int(img.size[1] * iscale))), Image.BILINEAR)
        t_arr = np.asarray(tmpl, dtype=np.float64)
        i_arr = np.asarray(img, dtype=np.float64)
    except Exception:
        return [_finding("info", shot_label, "logo",
                         "读 logo 模板/图失败，logo 检跳过", {"degraded": "read_fail"})]
    peak = _ncc_peak(t_arr, i_arr, np)
    detail = {"ncc_peak": round(peak, 3), "threshold_warn": LOGO_NCC_WARN, "threshold_block": LOGO_NCC_BLOCK,
              "template": str(logo_template)}
    if peak < LOGO_NCC_BLOCK:
        detail["confidence"] = "heuristic"
        return [_finding("warn", shot_label, "logo",
                         f"产品镜粗模板基本检不到注册 logo（NCC={peak:.2f}<{LOGO_NCC_BLOCK}）；未做尺度/透视校准，仅提示人工复核", detail)]
    if peak < LOGO_NCC_WARN:
        return [_finding("warn", shot_label, "logo",
                         f"产品镜 logo 匹配偏弱（NCC={peak:.2f}<{LOGO_NCC_WARN}），疑形变/被遮挡，人工复核", detail)]
    return []


def _production_events_path(root: Path) -> Path:
    return root / "生产数据" / "production_events.jsonl"


def _load_production_events(root: Path) -> List[Dict[str, Any]]:
    path = _production_events_path(root)
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
    except Exception:
        return []
    return rows


def _event_mapping(event: Dict[str, Any], key: str) -> Dict[str, Any]:
    value = event.get(key)
    return value if isinstance(value, dict) else {}


def _event_asset_rel(root: Path, event: Dict[str, Any]) -> Optional[str]:
    generation = _event_mapping(event, "generation")
    asset = generation.get("asset") or event.get("asset") or event.get("path")
    if not asset:
        return None
    raw = str(asset).strip()
    if not raw:
        return None
    p = Path(raw)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(root.resolve()).as_posix()
        except Exception:
            return p.as_posix()
    return p.as_posix()


def _is_prohibited_local_patch_event(event: Dict[str, Any]) -> bool:
    generation = _event_mapping(event, "generation")
    meta = _event_mapping(event, "meta")
    cost = _event_mapping(event, "cost")
    fields = [
        event.get("provider"), event.get("source"), event.get("method"), event.get("event"),
        cost.get("provider"), cost.get("method"),
        generation.get("provider"), generation.get("method"), generation.get("redraw_reason"),
        meta.get("provider"), meta.get("method"), meta.get("tool"),
    ]
    text = " ".join(str(v) for v in fields if v is not None).lower()
    if any(token in text for token in PROHIBITED_LOCAL_PATCH_STRONG_TOKENS):
        return True
    subject_words = ("product", "logo", "packaging", "package", "face", "产品", "包装", "标志", "脸")
    return any(word in text for word in subject_words) and any(
        token in text for token in PROHIBITED_LOCAL_PATCH_OPERATION_TOKENS
    )


def check_prohibited_local_patch(root: Path, labels_paths: List[Tuple[str, Optional[Path]]]) -> List[Dict[str, Any]]:
    """Block image-stage product/logo/face paste-back artifacts used as final ad frames.

    True logo/package overlays belong in ad-compose delivery, not as a way to make an
    image-stage frame pass product QC. A later clean backend redraw event for the same
    asset naturally supersedes the old patched event because we only inspect latest rows.
    """
    latest: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    wanted: Dict[str, str] = {}
    for label, path in labels_paths:
        if not path:
            continue
        try:
            wanted[Path(path).resolve().relative_to(root.resolve()).as_posix()] = label
        except Exception:
            wanted[Path(path).as_posix()] = label
    if not wanted:
        return []
    for idx, event in enumerate(_load_production_events(root), start=1):
        stage = str(event.get("stage") or "").strip()
        if stage and stage != "image":
            continue
        ev = str(event.get("event") or "").strip()
        if ev and ev not in {"generation", "redraw", "fix", "repair"}:
            continue
        rel = _event_asset_rel(root, event)
        if rel in wanted:
            latest[rel] = (idx, event)

    findings: List[Dict[str, Any]] = []
    for rel, (line_no, event) in latest.items():
        if not _is_prohibited_local_patch_event(event):
            continue
        generation = _event_mapping(event, "generation")
        meta = _event_mapping(event, "meta")
        findings.append(_finding(
            "block", wanted.get(rel, "-"), "local_patch_prohibited",
            "生产事件账本显示该广告出图帧来自本地贴包装/logo/脸部像素修复；"
            "不得用局部贴图伪造产品一致性通过，需回 ad-image 用参考图/官方 image2image 重抽",
            {
                "event_line": line_no,
                "asset": rel,
                "provider": generation.get("provider") or event.get("provider") or event.get("source"),
                "method": meta.get("method") or generation.get("method") or event.get("method"),
            },
        ))
    return findings


# ── finding 构造 + 汇总 ──────────────────────────────────────────────────────────

def _finding(severity: str, shot: str, check: str, reason: str,
             detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """权威 finding schema：{severity, shot, check, reason, detail}。"""
    return {"severity": severity, "shot": shot, "check": check, "reason": reason, "detail": detail or {}}


def summarize(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    out = {"block": 0, "warn": 0, "info": 0}
    for f in findings:
        sev = f.get("severity")
        if sev in out:
            out[sev] += 1
    return out


# ── 落档资产路径解析（产品镜 → 已出 PNG） ─────────────────────────────────────────

def _resolve_shot_png(stage_dir: Path, shot_label: str) -> Optional[Path]:
    """`镜头N` → 已落档 PNG（首帧，排除 _end）。出图目录通常 <stage_dir>/图片 或 <stage_dir>。"""
    m = re.search(r"(\d+)", shot_label)
    if not m:
        return None
    n = int(m.group(1))
    img_dirs = [stage_dir / "图片", stage_dir]
    pats = [f"镜头{n}.png", f"镜头{n:02d}.png", f"镜头_{n}.png", f"shot{n}.png"]
    for d in img_dirs:
        if not d.exists():
            continue
        for pat in pats:
            cand = d / pat
            if cand.exists():
                return cand
        # 模糊兜底：目录内含 镜头N 且非 _end 的 png
        for cand in sorted(d.glob("*.png")):
            if cand.name.endswith("_end.png"):
                continue
            mm = re.search(r"镜头\s*0*(\d+)|shot\s*0*(\d+)", cand.stem, re.I)
            if mm and int(next(g for g in mm.groups() if g)) == n:
                return cand
    return None


# ── 主流程 ──────────────────────────────────────────────────────────────────────

def run_qc(stage_dir: Path, storyboard_arg: Optional[str] = None, strict: bool = False) -> Dict[str, Any]:
    paths = resolve_paths(stage_dir, storyboard_arg)
    Image, np = _load_imaging()
    sb = load_json(paths["storyboard"], {}) or {}
    overview_text = ""
    try:
        overview_text = paths["overview"].read_text(encoding="utf-8")
    except Exception:
        pass

    prod = product_shots(sb)
    shot_map = storyboard_shot_by_label(sb)
    registry_ids = load_asset_registry_ids(paths["root"])
    brand_hex = brand_color_hex(sb, overview_text)
    findings: List[Dict[str, Any]] = []

    if Image is None:
        findings.append(_finding("info", "-", "prompt_lint",
                                 "降级模式：缺 Pillow/numpy，仅跑 prompt-lint（品牌色/dHash/logo 像素检跳过）",
                                 {"degraded": "no_pillow", "precision": "degraded"}))

    if not prod:
        findings.append(_finding("info", "-", "prompt_lint",
                                 "storyboard 无产品镜（assets 无 PROD_* : true），产品一致性机检无对象",
                                 {"product_shots": 0}))

    # 1) PROMPT-LINT（HARD，无 Pillow 也跑）
    prompt_text_by_label: Dict[str, Optional[str]] = {}
    for label in prod:
        ppath = _shot_prompt_path(paths["prompt_dir"], label)
        text = None
        if ppath is not None:
            try:
                text = ppath.read_text(encoding="utf-8")
            except Exception:
                text = None
        prompt_text_by_label[label] = text
        findings.extend(lint_product_prompt(label, text))
        shot = shot_map.get(label, {})
        findings.extend(check_asset_bindings(label, shot, registry_ids))
        findings.extend(check_text_legibility(label, shot, text))
        findings.extend(check_safe_area(label, shot))

    # 像素三项仅在产品镜存在时跑
    if prod:
        labels_paths: List[Tuple[str, Optional[Path]]] = [
            (label, _resolve_shot_png(paths["stage_dir"], label)) for label in prod
        ]
        # 2) brand-color ΔE
        for label, p in labels_paths:
            findings.extend(check_brand_color(label, p, brand_hex, Image, np, bbox=None))
        # 3) product dHash 离群
        findings.extend(check_dhash_group(labels_paths, Image))
        # 4) logo 模板匹配（仅注册了模板时）
        if paths["logo_template"].exists():
            for label, p in labels_paths:
                findings.extend(check_logo(label, p, paths["logo_template"], Image, np))
        else:
            findings.append(_finding("info", "-", "logo",
                                     f"未注册 logo 模板（{paths['logo_template']}），logo 模板匹配跳过",
                                     {"degraded": "no_template"}))
        findings.extend(check_prohibited_local_patch(paths["root"], labels_paths))

    # strict：把 warn/info（降级）也提级为 warn 进候选重出（不动 block）。
    if strict:
        for f in findings:
            if f.get("severity") == "info" and f.get("detail", {}).get("degraded"):
                f["severity"] = "warn"
                f["reason"] = "[strict] " + f["reason"]

    precision = "full" if (Image is not None and np is not None) else "degraded"
    pending_images = [
        f for f in findings
        if f.get("detail", {}).get("degraded") == "no_image"
    ]
    payload = {
        "kind": "ad_product_qc",
        "version": 2,
        "summary": summarize(findings),
        "findings": findings,
        "qc_environment": {
            "precision_level": precision,
            "python": sys.executable,
            "missing_or_degraded": [] if precision == "full" else ["Pillow/numpy pixel checks"],
            "pending_product_images": len(pending_images),
            "manual_review_accepted": False,
            "asset_registry_ids": sorted(registry_ids),
        },
    }
    # 落档到权威路径 出图/分镜/product_qc.json
    out_json = paths["out_json"]
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload["_json_path"] = str(out_json)
    payload["_product_shots"] = prod
    payload["_brand_hex"] = brand_hex
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage_dir", help="出图阶段目录，如 <作品根>/出图/分镜（或 出图/第N集）")
    ap.add_argument("--storyboard", default=None, help="storyboard.json 路径（默认 <作品根>/脚本/storyboard.json）")
    ap.add_argument("--strict", action="store_true", help="严审刷新：降级 info 提级 warn 进候选重出")
    ns = ap.parse_args(argv)
    payload = run_qc(Path(ns.stage_dir), ns.storyboard, strict=ns.strict)
    s = payload["summary"]
    print(f"# 产品落档机检 product_qc  block={s['block']}  warn={s['warn']}  info={s['info']}")
    print(f"  落档：{payload['_json_path']}  产品镜={len(payload['_product_shots'])}  品牌色={payload['_brand_hex'] or '未声明'}")
    for f in payload["findings"]:
        mark = {"block": "🔴", "warn": "🟡", "info": "ℹ️"}.get(f["severity"], "·")
        print(f"  {mark} [{f['shot']}/{f['check']}] {f['reason']}")
    if not payload["findings"]:
        print("  ✅ 产品一致性机检通过")
    # gate 据 summary.block 硬挡 spend：block>0 → 非零退出
    return 1 if s["block"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
