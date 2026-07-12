#!/usr/bin/env python3
"""mv-image 出图落档机检 image_qc —— MV 的「出图落档一致性机检」。

MV 是单主角跨 16-64 个 clip 的脸一致性重灾区，但 mv-image 此前**没有任何机检脚本**——
视觉一致性 100% 靠 SKILL.md + references/visual_consistency.md 的散文规则。本脚本把
「主角脸是否漂、主色是否漂、锚点句是否真的拼进了 prompt」三件事在**刚出完一批图、还没继续**的
最便宜的点机检初筛，省下等 mv-review 审片才发现的返工。

**mv 线自包含**：本文件内置脸 embedding QC、Pillow 降级、prompt lint 与报告 schema，
不读取或导入其它创作系列的实现。

三类检查：
1. 主角脸漂移 G1（需 insightface · 缺则优雅降级）：
   主角共享定妆组内部互相余弦 → 自标定「同人下限」floor；本曲每个 clip 首帧/尾帧脸 vs 主角主参考，
   落 ok/warn/block 三档。**风格化 MV 脸跨图余弦整体偏低**，所以用本曲自己的定妆组做地板，不写死阈值。
   缺 insightface 时降级到 Pillow（只验 图损坏/分辨率/清晰度，绝不臆造相似度），更缺 Pillow 时整项跳过——
   都在报告里明示，永不静默报「通过」。
2. 主色漂移 palette（确定性·不需要脸栈）：每个 clip 首帧的主色调色板 vs palette_anchor 主色，
   计算最近主色距离，超阈值 → warn（MV 段落本就允许加亮/变暗，故 palette 是 advisory，不硬拦）。
3. 锚点句落地 lint（确定性·便宜）：按 clip_plan.json 逐 clip 检查其 image_prompt_path 指向的 prompt
   文件，是否真的含 visual_consistency 规定的『身份锚点 / 视觉锚点 / 禁止漂移』锚点块——
   此前没有任何东西校验锚点句有没有抄进 prompt。缺关键锚点块 → warn（提示回 mv-image 补锚点句）。

落档判定：block=主角脸崩，必须重抽；warn=人判二次；ok=放行。退出码恒 0（建议性闸门）。
mv 的『筛选宽容铁律』：只有脸/画风漂到识别不出才硬拦，主色/锚点轻微偏差是 advisory。

报告写 `生产数据/image_qc/image_qc.json`(+`.md`)，schema 由本文件维护。

用法：
  python3 image_qc.py <作品根> [--json]
  python3 image_qc.py <作品根> --no-pixel   # 只跑 prompt 锚点 lint（无 Pillow/insightface 时）

完整脸机检需 Pillow + cv2 + insightface + onnxruntime + buffalo_l。报告会写
`qc_environment.precision_level=full|degraded|none`，缺依赖时应补装重跑，不应直接进 mv-video。

测试（从本目录跑）：
  cd skills/mv-image/scripts && python3 -m pytest test_image_qc.py
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


def _sha256_path(path: Path) -> str:
    if not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_settings(root: Path) -> Dict[str, str]:
    path = root / "_设置.md"
    if not path.is_file():
        return {}
    out: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r"^\s*(?:[-*]\s*)?(?:\*\*)?([^:：*]+)(?:\*\*)?\s*[:：]\s*(.+?)\s*$", raw)
        if match:
            out[match.group(1).strip()] = re.split(r"\s+#", match.group(2), maxsplit=1)[0].strip()
    return out

# verdict 严重度；noface=图里没脸，介于 ok 与 warn。
SEVERITY = {"ok": 0, "info": 0, "noface": 1, "warn": 2, "block": 3}

DEFAULT_MARGIN = 0.08
FACE_DEGRADED_MODES = ("pillow_fallback",)
PILLOW_FALLBACK_MODE = "pillow_fallback"
PILLOW_MIN_SHORT_SIDE = 512
PILLOW_SHARPNESS_FLOOR = 25.0
PILLOW_PROBE_MAX_SIDE = 256

# 共享定妆主角图候选目录（SKILL.md 用 common/，prompt_format.md 用 共享/——两套都认）。
SHARED_IMG_DIRS = (
    ("出图", "共享", "图片"),
    ("出图", "common", "图片"),
)
# 主角定妆名变体后缀（正/侧/半身/全身/背）——同人不同角度，用来自标定 floor。
_VARIANT_RE = re.compile(r"^(.+?)(?:_(侧|半身|全身|背|正))?$")
# 非主角类定妆（场景/道具/特效不参与脸度量）。
_NON_LEAD = ("场景", "背景", "殿", "庭", "院", "山", "洞", "门", "廊", "道", "床", "街", "城",
             "光", "符", "剑气", "法宝", "特效", "雷", "火", "云", "雨", "镜", "花", "灯", "霓虹",
             "粒子", "氛围", "logo", "标")

QC_INSTALL_RECOMMENDATION = (
    "在可装重依赖的 conda env（如 facefusion）跑：python -m pip install "
    "pillow opencv-python onnxruntime insightface scikit-image；首次跑 "
    "FaceAnalysis(name='buffalo_l') 预热/下载模型。"
)


# ── 纯函数（无依赖 · pytest 覆盖） ────────────────────────────────────────────

def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """两向量余弦相似度；任一零向量返回 0.0。纯函数·可测。"""
    if len(a) != len(b):
        raise ValueError("dim mismatch")
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def calibrate_floor(intra_scores: Sequence[float], fallback: float = 0.50) -> float:
    """从主角定妆组内部互相余弦标定『同一人下限』：取最小值（最严格那对就是同人能掉到的最低线）。
    定妆组单张（无内部对）→ 回退保守经验下限。纯函数·可测。"""
    vals = [s for s in intra_scores if s is not None]
    if not vals:
        return fallback
    return min(vals)


def floor_calibrated(intra_scores: Sequence[float]) -> bool:
    """主角定妆组是否有内部对可自标定地板（≥1 对）。单张 → False（地板退回保守经验值，标低精度）。"""
    return any(s is not None for s in intra_scores)


def band(score: float, floor: float, margin: float = DEFAULT_MARGIN) -> str:
    """落档：score≥floor→ok / floor-margin≤score<floor→warn / 更低→block。纯函数·可测。"""
    if score >= floor:
        return "ok"
    if score >= floor - margin:
        return "warn"
    return "block"


def worst_verdict(verdicts: Iterable[str]) -> str:
    """一组 verdict 取最重者；空集 → ok。纯函数·可测。"""
    worst = "ok"
    for v in verdicts:
        if SEVERITY.get(v, 0) > SEVERITY.get(worst, 0):
            worst = v
    return worst


def count_verdicts(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    """数 verdict（block/warn/noface/ok）。纯函数·可测。"""
    out = {"block": 0, "warn": 0, "noface": 0, "ok": 0}
    for r in rows or []:
        v = r.get("verdict")
        if v in out:
            out[v] += 1
    return out


def laplacian_variance(pixels: Sequence[int], w: int, h: int) -> float:
    """灰度像素 4-邻域拉普拉斯响应方差（无 cv2 时近似 cv2.Laplacian().var()）。越低越糊。纯函数·可测。"""
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


def pillow_shot_verdict(decodable: bool, width: int = 0, height: int = 0,
                        sharpness: Optional[float] = None, *,
                        min_short_side: int = PILLOW_MIN_SHORT_SIDE,
                        sharpness_floor: float = PILLOW_SHARPNESS_FLOOR) -> Tuple[str, List[str]]:
    """Pillow 降级档逐图判定（只判 可解码/分辨率/清晰度，不碰相似度）。纯函数·可测。"""
    if not decodable:
        return "block", ["图损坏或不可解码"]
    reasons: List[str] = []
    short = min(width, height)
    if short < min_short_side:
        reasons.append(f"分辨率不足（短边 {short} < {min_short_side}）")
    if sharpness is not None and sharpness < sharpness_floor:
        reasons.append(f"清晰度偏低（laplacian_var {sharpness:.1f} < {sharpness_floor:g}）")
    return ("warn", reasons) if reasons else ("ok", [])


# ── palette（确定性主色漂移，不需要脸栈） ─────────────────────────────────────

# palette_anchor 里的中文主色 → RGB（覆盖 MV 常见主色；命中不了的色名跳过，不臆造）。
COLOR_NAME_RGB: Dict[str, Tuple[int, int, int]] = {
    "红": (200, 40, 40), "赤": (200, 40, 40), "绯": (210, 60, 70), "朱": (200, 50, 50),
    "橙": (230, 140, 40), "黄": (230, 200, 60), "金": (210, 175, 70),
    "绿": (60, 160, 90), "青": (60, 170, 170), "蓝": (60, 90, 200), "靛": (60, 70, 170),
    "紫": (140, 70, 180), "粉": (230, 150, 180),
    "白": (235, 235, 235), "灰": (130, 130, 130), "银": (190, 190, 195),
    "黑": (25, 25, 25), "墨": (35, 35, 40), "玄": (30, 30, 35),
    "棕": (130, 90, 60), "褐": (110, 80, 55), "米": (225, 215, 185),
}
PALETTE_DRIFT_THRESHOLD = 110.0  # 最近主色欧氏距离阈值（0-441），超过=该 clip 主色离 anchor 太远。


def parse_palette_anchor(raw: str) -> List[Tuple[int, int, int]]:
    """palette_anchor 文本 → 主色 RGB 列表。支持 `#rrggbb`、`rgb(r,g,b)` 和中文色名。纯函数·可测。"""
    text = str(raw or "")
    out: List[Tuple[int, int, int]] = []
    seen = set()

    def _add(rgb: Tuple[int, int, int]) -> None:
        key = tuple(int(max(0, min(255, c))) for c in rgb)
        if key not in seen:
            seen.add(key)
            out.append(key)

    for m in re.finditer(r"#([0-9a-fA-F]{6})", text):
        h = m.group(1)
        _add((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)))
    for m in re.finditer(r"rgb\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*\)", text, re.I):
        _add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for name, rgb in COLOR_NAME_RGB.items():
        if name in text:
            _add(rgb)
    return out


def rgb_distance(a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
    """两 RGB 欧氏距离。纯函数·可测。"""
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def nearest_anchor_distance(color: Tuple[int, int, int],
                            anchors: Sequence[Tuple[int, int, int]]) -> Optional[float]:
    """某主色到 anchor 主色集合的最近距离；anchors 空 → None。纯函数·可测。"""
    if not anchors:
        return None
    return min(rgb_distance(color, a) for a in anchors)


def palette_verdict(dominant: Sequence[Tuple[int, int, int]],
                    anchors: Sequence[Tuple[int, int, int]],
                    threshold: float = PALETTE_DRIFT_THRESHOLD) -> Tuple[str, Optional[float]]:
    """clip 主色集合 vs anchor：取每个主色的最近 anchor 距离，最小者作为「最贴近 anchor 的主色」。
    若连最贴近的主色都超阈值 → 整图主色离 anchor 太远 → warn（advisory）。返回 (verdict, 最贴近距离)。纯函数·可测。"""
    if not anchors or not dominant:
        return "ok", None
    best = None
    for c in dominant:
        d = nearest_anchor_distance(c, anchors)
        if d is not None and (best is None or d < best):
            best = d
    if best is None:
        return "ok", None
    return ("warn" if best > threshold else "ok"), round(best, 1)


# ── 锚点句落地 lint（确定性·便宜） ──────────────────────────────────────────

# visual_consistency.md 规定每张分镜 prompt 末尾固定拼的锚点块字段。
ANCHOR_FIELDS = {
    "identity": ("身份锚点", "lead_identity_anchor", "主角锚点", "锚点句"),
    "reference": ("参考输入", "reference_inputs", "参考图", "后端主体", "主体库", "LoRA"),
    "visual": ("视觉锚点", "global_style", "palette_anchor", "视觉风格"),
    "forbidden": ("禁止漂移", "forbidden_drift", "禁漂", "不可漂"),
}
# 缺哪些块算 warn（identity/forbidden 是脸/画风护栏，最该有；visual 次之）。
REQUIRED_ANCHOR_KEYS = ("identity", "reference", "visual", "forbidden")

PROHIBITED_LOCAL_PATCH_STRONG_TOKENS = (
    "local_face_patch", "face_patch", "facefix", "faceswap", "face_swap", "inswapper",
    "facefusion", "roop", "poisson", "alpha_blend", "pasteback", "paste_back",
    "贴脸", "换脸", "裁脸", "抠脸", "本地贴脸",
)
PROHIBITED_LOCAL_PATCH_OPERATION_TOKENS = (
    "patch", "paste", "blend", "clone", "swap", "修脸", "贴回", "贴入", "移植",
)


def anchor_block_presence(text: str) -> Dict[str, bool]:
    """prompt 文本 → 各锚点块是否出现。纯函数·可测。"""
    body = str(text or "")
    return {key: any(tok in body for tok in toks) for key, toks in ANCHOR_FIELDS.items()}


def lint_clip_prompt(clip_id: str, prompt_text: Optional[str]) -> List[Dict[str, str]]:
    """单 clip prompt 锚点 lint：缺锚点块 → warn。prompt 文件不存在 → warn(prompt_missing)。纯函数·可测。"""
    findings: List[Dict[str, str]] = []
    if prompt_text is None:
        findings.append({"level": "warn", "code": "prompt_missing",
                         "msg": f"{clip_id}：clip_plan 指向的出图 prompt 文件不存在——先跑 mv-plan 或补 prompt 再出图。"})
        return findings
    present = anchor_block_presence(prompt_text)
    label = {"identity": "身份锚点(lead_identity_anchor)",
             "reference": "参考输入(reference_inputs)",
             "visual": "视觉锚点(global_style/palette_anchor)",
             "forbidden": "禁止漂移(forbidden_drift)"}
    for key in REQUIRED_ANCHOR_KEYS:
        if not present.get(key):
            findings.append({"level": "warn", "code": f"missing_anchor_{key}",
                             "msg": f"{clip_id}：出图 prompt 缺『{label[key]}』锚点块——"
                                    "visual_consistency 规定每张分镜末尾必拼，缺则跨段易漂（脸/画风/主色）。"})
    return findings


def _clip_prompt_path(clip: Mapping[str, Any]) -> Optional[str]:
    p = clip.get("image_prompt_path") or clip.get("prompt_path")
    return str(p) if p else None


def load_clip_plan(root: Path) -> Optional[Dict[str, Any]]:
    """分镜/clip_plan.json → dict；缺/损坏 → None（lint 跳过，记 note）。"""
    path = root / "分镜" / "clip_plan.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_blueprint_text(root: Path) -> str:
    """视觉蓝图.md 全文（找 palette_anchor 等一致性包字段）；缺 → 空串。"""
    for name in ("视觉蓝图.md", "视觉蓝图.txt"):
        try:
            return (root / name).read_text(encoding="utf-8")
        except Exception:
            continue
    return ""


def extract_palette_anchor(root: Path) -> List[Tuple[int, int, int]]:
    """从 视觉蓝图.md（或 _设置.md）抽 palette_anchor 主色。找不到字段 → 空（palette 检查跳过）。"""
    blob = load_blueprint_text(root)
    try:
        blob += "\n" + (root / "_设置.md").read_text(encoding="utf-8")
    except Exception:
        pass
    # 优先抓 palette_anchor 所在行/块；找不到该字段就不臆测整篇颜色。
    anchors: List[Tuple[int, int, int]] = []
    for m in re.finditer(r"(?im)^.*(?:palette_anchor|主色|调色板|色板|palette).*$", blob):
        anchors.extend(parse_palette_anchor(m.group(0)))
    # 去重保序
    out: List[Tuple[int, int, int]] = []
    seen = set()
    for a in anchors:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out


def lint_prompts(root: Path) -> Dict[str, Any]:
    """按 clip_plan.json 逐 clip 跑锚点 lint。缺 plan → 记 note。"""
    res: Dict[str, Any] = {"available": True, "findings": [], "clips_linted": 0, "notes": []}
    plan = load_clip_plan(root)
    if plan is None:
        res["available"] = False
        res["notes"].append("缺 分镜/clip_plan.json——先跑 mv-plan 再 lint 锚点。")
        return res
    clips = plan.get("clips") or []
    if not clips:
        res["notes"].append("clip_plan.json 无 clips。")
    for clip in clips:
        if not isinstance(clip, dict):
            continue
        res["clips_linted"] += 1
        clip_id = str(clip.get("clip_id") or clip.get("id") or "Clip_?")
        prompt_rel = _clip_prompt_path(clip)
        prompt_text: Optional[str] = None
        if prompt_rel:
            try:
                prompt_text = (root / prompt_rel).read_text(encoding="utf-8")
            except Exception:
                prompt_text = None
        res["findings"].extend(lint_clip_prompt(clip_id, prompt_text))
    return res


# ── 像素加载（需 insightface/Pillow · 缺则降级） ──────────────────────────────

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


def _embed(app, png: str) -> Optional[List[float]]:
    """检出图中最大脸的 normed embedding；无脸/读图失败 → None。"""
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


def _pillow_probe(image_mod, png: str) -> Optional[Tuple[int, int, float]]:
    """读图 → (宽, 高, 清晰度)；不可解码 → None。"""
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


def _pillow_dominant_colors(image_mod, png: str, k: int = 4) -> List[Tuple[int, int, int]]:
    """Pillow 量化取 top-k 主色 RGB（按像素占比降序）。读图失败 → []。"""
    try:
        with image_mod.open(png) as im:
            rgb = im.convert("RGB")
            rgb.thumbnail((PILLOW_PROBE_MAX_SIDE, PILLOW_PROBE_MAX_SIDE))
            quant = rgb.quantize(colors=max(1, k * 2))
            pal = quant.getpalette() or []
            counts = quant.getcolors() or []
        counts.sort(reverse=True)
        out: List[Tuple[int, int, int]] = []
        for _, idx in counts[:k]:
            base = idx * 3
            if base + 2 < len(pal):
                out.append((pal[base], pal[base + 1], pal[base + 2]))
        return out
    except Exception:
        return []


# ── 资产发现：主角定妆 + clip 帧 ──────────────────────────────────────────────

def _shared_image_dirs(root: Path) -> List[Path]:
    return [Path(root, *parts) for parts in SHARED_IMG_DIRS]


def is_lead_asset(name: str) -> bool:
    """定妆名是否像「主角/人物」（排除场景/道具/特效/光效）。"""
    return not any(k in name for k in _NON_LEAD)


def discover_lead_costume_set(root: Path) -> Dict[str, str]:
    """共享定妆主角图组 → {variant: path}（variant: 主/侧/半身/全身/背）。

    取共享目录里第一个像主角的 `定妆_<主角>[_变体].png` 角色组（MV 单主角，取主角名出现最多的一组）。
    无法识别主角组 → {}（脸 QC 跳过，记 note）。
    """
    by_char: Dict[str, Dict[str, str]] = {}
    for d in _shared_image_dirs(root):
        for p in glob.glob(os.path.join(str(d), "定妆_*.png")):
            base = os.path.basename(p)[len("定妆_"):-len(".png")]
            if any(t in base for t in ("三视图", "设定表", "表情", "脸部特写")):
                continue
            m = _VARIANT_RE.match(base)
            if not m:
                continue
            char, variant = m.group(1), (m.group(2) or "主")
            if not is_lead_asset(char):
                continue
            by_char.setdefault(char, {})[variant] = p
    if not by_char:
        return {}
    # 单主角：选变体最多（信息最全）的那一组当主角组。
    lead = max(by_char.items(), key=lambda kv: (len(kv[1]), "主" in kv[1]))
    return lead[1]


def discover_clip_frames(root: Path) -> List[Tuple[str, str]]:
    """clip 首帧/尾帧 PNG → [(clip_id, abs_path)]，按 clip_id 排序。

    优先 clip_plan.json 的 image_path/end_frame_path（need_end_frame=true 才计尾帧）；
    缺 plan 时回退 glob `出图/段落/图片/Clip_*.png`。
    """
    plan = load_clip_plan(root)
    out: List[Tuple[str, str]] = []
    seen = set()

    def _add(cid: str, rel: Optional[str]) -> None:
        if not rel:
            return
        ap = str((root / rel).resolve())
        if ap in seen:
            return
        seen.add(ap)
        out.append((cid, ap))

    if plan is not None:
        for clip in (plan.get("clips") or []):
            if not isinstance(clip, dict):
                continue
            cid = str(clip.get("clip_id") or clip.get("id") or "Clip_?")
            _add(cid, clip.get("image_path"))
            if clip.get("need_end_frame"):
                _add(f"{cid}_end", clip.get("end_frame_path"))
    else:
        for d in (root / "出图" / "段落" / "图片",):
            for p in sorted(glob.glob(os.path.join(str(d), "Clip_*.png"))):
                cid = Path(p).stem
                _add(cid, os.path.relpath(p, str(root)))
    out.sort(key=lambda t: t[0])
    return out


# ── 像素机检（脸漂移 G1 + 主色 palette） ──────────────────────────────────────

def run_face_check(root: Path, margin: float = DEFAULT_MARGIN) -> Dict[str, Any]:
    """主角脸漂移 G1：主角定妆组自标定 floor，每个 clip 帧 vs 主角主参考落 ok/warn/block。

    insightface 可用 → mode=insightface；缺则降级 Pillow（验图损坏/分辨率/清晰度，不臆造相似度）；
    更缺 Pillow → available=False（整项跳过，交人判）。"""
    result: Dict[str, Any] = {"available": False, "mode": None, "margin": margin,
                              "lead_floor": None, "lead_calibrated": False, "shots": [], "notes": []}
    lead_set = discover_lead_costume_set(root)
    frames = discover_clip_frames(root)
    if not lead_set:
        result["notes"].append("共享定妆未找到主角定妆图（出图/共享|common/图片/定妆_<主角>.png）——脸漂移机检跳过，交人判。")
    app = _load_embedder()

    if app is not None and lead_set:
        result["available"] = True
        result["mode"] = "insightface"
        main = _embed(app, lead_set.get("主") or next(iter(lead_set.values())))
        intra: List[float] = []
        if main is not None:
            for v, p in lead_set.items():
                if v == "主":
                    continue
                e = _embed(app, p)
                if e is not None:
                    intra.append(cosine(main, e))
        floor = calibrate_floor(intra)
        calibrated = floor_calibrated(intra)
        result["lead_floor"] = round(floor, 4)
        result["lead_calibrated"] = calibrated
        result["lead_intra_pairs"] = len(intra)
        if main is None:
            result["notes"].append("主角主参考未检出脸——floor 无法标定，脸漂移降级交人判。")
        for cid, ap in frames:
            rel = os.path.relpath(ap, str(root))
            if not os.path.exists(ap):
                result["shots"].append({"clip": cid, "png": rel, "verdict": "block", "checks": ["clip PNG 不存在"]})
                continue
            if main is None:
                result["shots"].append({"clip": cid, "png": rel, "verdict": "noface", "checks": ["无主角主参考可比对"]})
                continue
            emb = _embed(app, ap)
            if emb is None:
                result["shots"].append({"clip": cid, "png": rel, "verdict": "noface"})
                continue
            sc = cosine(emb, main)
            v = band(sc, floor, margin)
            row: Dict[str, Any] = {"clip": cid, "png": rel, "score": round(sc, 4),
                                   "floor": round(floor, 4), "verdict": v, "floor_calibrated": calibrated}
            if not calibrated and v in ("block", "warn"):
                # 单张定妆：地板没自标定，风格化 MV 脸跨图常 <0.5，0.50 回退会系统性误杀 → 降 warn 交人判。
                row["precision"] = "low_floor_uncalibrated"
                if v == "block":
                    row["verdict"] = "warn"
            result["shots"].append(row)
        return result

    # 降级：Pillow 基础质量
    image_mod = _load_pillow()
    if image_mod is not None and lead_set:
        result["available"] = True
        result["mode"] = PILLOW_FALLBACK_MODE
        result["precision"] = "insufficient_precision"
        result["notes"].append(
            "未装 insightface——脸漂移降级为 Pillow 基础机检（仅查 图存在/可解码/分辨率/清晰度，"
            "不做人脸相似度、不臆造相似度分）；主角脸是否同人仍需人判兜底。")
        for cid, ap in frames:
            rel = os.path.relpath(ap, str(root))
            if not os.path.exists(ap):
                result["shots"].append({"clip": cid, "png": rel, "verdict": "block",
                                        "mode": PILLOW_FALLBACK_MODE, "checks": ["clip PNG 不存在"]})
                continue
            probe = _pillow_probe(image_mod, ap)
            if probe is None:
                v, checks = pillow_shot_verdict(False)
            else:
                w, h, sharp = probe
                v, checks = pillow_shot_verdict(True, w, h, sharp)
            result["shots"].append({"clip": cid, "png": rel, "verdict": v,
                                    "mode": PILLOW_FALLBACK_MODE, "checks": checks})
        return result

    if lead_set:
        result["notes"].append("既无 insightface 也无 Pillow——脸漂移机检整项跳过，交人判。")
    return result


def run_palette_check(root: Path, threshold: float = PALETTE_DRIFT_THRESHOLD) -> Dict[str, Any]:
    """主色漂移 palette（确定性·不需要脸栈）：每个 clip 首帧主色 vs palette_anchor，超阈值→warn。

    无 palette_anchor 或无 Pillow → available=False（跳过，记 note）。advisory：MV 段落允许加亮/变暗。"""
    result: Dict[str, Any] = {"available": False, "threshold": threshold,
                              "palette_anchor": [], "shots": [], "notes": []}
    anchors = extract_palette_anchor(root)
    if not anchors:
        result["notes"].append("视觉蓝图/设置里未找到 palette_anchor 主色——主色漂移机检跳过（不臆测主色）。")
        return result
    result["palette_anchor"] = [list(a) for a in anchors]
    image_mod = _load_pillow()
    if image_mod is None:
        result["notes"].append("未装 Pillow——主色漂移机检跳过（确定性主色提取需 Pillow）。")
        return result
    result["available"] = True
    for cid, ap in discover_clip_frames(root):
        rel = os.path.relpath(ap, str(root))
        if not os.path.exists(ap):
            result["shots"].append({"clip": cid, "png": rel, "verdict": "noface", "checks": ["clip PNG 不存在"]})
            continue
        dominant = _pillow_dominant_colors(image_mod, ap)
        v, dist = palette_verdict(dominant, anchors, threshold)
        row: Dict[str, Any] = {"clip": cid, "png": rel, "verdict": v,
                               "nearest_dist": dist, "dominant": [list(c) for c in dominant]}
        result["shots"].append(row)
    return result


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


def _event_mapping(event: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = event.get(key)
    return value if isinstance(value, Mapping) else {}


def _event_asset_rel(root: Path, event: Mapping[str, Any]) -> Optional[str]:
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


def _is_prohibited_local_patch_event(event: Mapping[str, Any]) -> bool:
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
    return ("face" in text or "脸" in text) and any(
        token in text for token in PROHIBITED_LOCAL_PATCH_OPERATION_TOKENS
    )


def prohibited_local_patch_outputs(root: Path) -> Dict[str, Any]:
    """Reject local face-paste/faceswap outputs recorded as final image artifacts.

    MV can use normal crop/color/archive work, but a clip frame whose latest image
    event says it was made by local face patching must not be treated as a clean
    image_qc pass. The fix is to regenerate the frame through the selected image
    backend with real reference inputs.
    """
    latest: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    for idx, event in enumerate(_load_production_events(root), start=1):
        stage = str(event.get("stage") or "").strip()
        if stage and stage != "image":
            continue
        ev = str(event.get("event") or "").strip()
        if ev and ev not in {"generation", "redraw", "fix", "repair"}:
            continue
        rel = _event_asset_rel(root, event)
        if not rel or not rel.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            continue
        latest[rel] = (idx, event)

    outputs: List[Dict[str, Any]] = []
    for rel, (line_no, event) in latest.items():
        if not _is_prohibited_local_patch_event(event):
            continue
        generation = _event_mapping(event, "generation")
        meta = _event_mapping(event, "meta")
        outputs.append({
            "png": rel,
            "clip": _clip_key(rel),
            "line": line_no,
            "provider": str(generation.get("provider") or event.get("provider") or event.get("source") or ""),
            "method": str(meta.get("method") or generation.get("method") or event.get("method") or ""),
            "reason": str(generation.get("redraw_reason") or event.get("reason") or ""),
            "verdict": "block",
        })
    outputs.sort(key=lambda r: (str(r.get("clip") or ""), str(r.get("png") or "")))
    return {
        "available": bool(_production_events_path(root).exists()),
        "event_path": str(_production_events_path(root)),
        "outputs": outputs,
        "summary": {"block": len(outputs), "warn": 0, "ok": 0},
    }


def generation_provenance(root: Path) -> Dict[str, Any]:
    """Audit model/channel/prompt/reference receipts for every planned frame."""
    latest: Dict[str, Tuple[int, Dict[str, Any]]] = {}
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("stage") or "") != "image":
            continue
        rel = _event_asset_rel(root, event)
        if rel:
            latest[rel] = (idx, event)
    settings = _project_settings(root)
    plan = load_clip_plan(root) or {}
    plan_by_id = {
        str(clip.get("clip_id")): clip
        for clip in plan.get("clips", []) if isinstance(clip, dict) and clip.get("clip_id")
    }
    expected_model = str(settings.get("生图模型") or "").strip()
    expected_channel = str(settings.get("生图渠道") or settings.get("生图AI") or "").strip()
    rows = []
    pairs = set()
    blocks = 0
    for cid, absolute in discover_clip_frames(root):
        rel = Path(absolute).resolve().relative_to(root.resolve()).as_posix()
        item = latest.get(rel)
        findings = []
        if not item:
            findings.append("missing_generation_event")
            model = channel = ""
        else:
            line_no, event = item
            generation = _event_mapping(event, "generation")
            model = str(generation.get("model") or event.get("model") or "").strip()
            channel = str(generation.get("channel") or generation.get("provider") or event.get("channel") or event.get("provider") or "").strip()
            if not model:
                findings.append("missing_model")
            if not channel:
                findings.append("missing_channel")
            recorded_asset_hash = str(generation.get("asset_sha256") or event.get("asset_sha256") or "")
            actual_hash = _sha256_path(root / rel)
            if not recorded_asset_hash:
                findings.append("missing_asset_sha256")
            elif recorded_asset_hash != actual_hash:
                findings.append("asset_changed_after_generation_event")
            prompt_hash = str(generation.get("source_prompt_sha256") or event.get("source_prompt_sha256") or "")
            prompt_rel = str(generation.get("source_prompt") or event.get("source_prompt") or "").strip()
            reference_rows = generation.get("reference_inputs")
            subject_rows = generation.get("subject_inputs")
            if not prompt_rel:
                findings.append("missing_source_prompt")
            if not prompt_hash:
                findings.append("missing_source_prompt_sha256")
            if prompt_rel:
                prompt_path = root / prompt_rel
                if not prompt_path.is_file():
                    findings.append("source_prompt_missing")
                elif prompt_hash and _sha256_path(prompt_path) != prompt_hash:
                    findings.append("source_prompt_changed_after_generation_event")
            if not isinstance(reference_rows, list):
                findings.append("missing_reference_inputs_receipt")
                reference_rows = []
            if not isinstance(subject_rows, list):
                subject_rows = []
            for reference in reference_rows:
                if not isinstance(reference, dict):
                    findings.append("invalid_reference_input_receipt")
                    continue
                reference_rel = str(reference.get("path") or "").strip()
                reference_hash = str(reference.get("sha256") or "").strip()
                if not reference_rel or not reference_hash:
                    findings.append("incomplete_reference_input_receipt")
                    continue
                reference_path = root / reference_rel
                if not reference_path.is_file():
                    findings.append("reference_input_missing")
                elif _sha256_path(reference_path) != reference_hash:
                    findings.append("reference_input_changed_after_generation_event")
            base_cid = cid[:-4] if cid.endswith("_end") else cid
            clip_contract = plan_by_id.get(base_cid) or {}
            required_reference_paths = set()
            required_subject_ids = set()
            for reference in clip_contract.get("reference_inputs") or []:
                if isinstance(reference, str) and reference.strip():
                    required_reference_paths.add(reference.strip())
                elif isinstance(reference, dict):
                    if str(reference.get("path") or "").strip():
                        required_reference_paths.add(str(reference.get("path")).strip())
                    subject_id = str(
                        reference.get("subject_id") or reference.get("character_id") or ""
                    ).strip()
                    if subject_id:
                        required_subject_ids.add(subject_id)
            actual_reference_paths = {
                str(reference.get("path") or "").strip()
                for reference in reference_rows if isinstance(reference, dict)
            }
            actual_subject_ids = {str(value).strip() for value in subject_rows if str(value).strip()}
            for missing_path in sorted(required_reference_paths - actual_reference_paths):
                findings.append(f"required_reference_not_submitted:{missing_path}")
            for missing_subject in sorted(required_subject_ids - actual_subject_ids):
                findings.append(f"required_subject_not_submitted:{missing_subject}")
            if model and channel:
                pairs.add((model, channel))
            if expected_model and model and model != expected_model:
                findings.append("model_differs_from_project_setting")
            if expected_channel and channel and channel != expected_channel:
                findings.append("channel_differs_from_project_setting")
        blocks += len(findings)
        rows.append({
            "clip": cid, "asset": rel, "model": model, "channel": channel,
            "source_prompt": prompt_rel if item else "",
            "reference_count": len(reference_rows) if item else 0,
            "subject_count": len(subject_rows) if item else 0,
            "event_line": item[0] if item else None, "findings": findings,
            "verdict": "block" if findings else "ok",
        })
    if len(pairs) > 1:
        blocks += 1
    return {
        "event_path": str(_production_events_path(root)),
        "expected_model": expected_model,
        "expected_channel": expected_channel,
        "model_channel_pairs": [{"model": model, "channel": channel} for model, channel in sorted(pairs)],
        "uniform": len(pairs) <= 1,
        "complete": bool(rows) and blocks == 0,
        "rows": rows,
        "summary": {"block": blocks, "ok": sum(1 for row in rows if row["verdict"] == "ok")},
    }


def run_pixel_checks(root: Path, margin: float = DEFAULT_MARGIN,
                     palette_threshold: float = PALETTE_DRIFT_THRESHOLD) -> Dict[str, Any]:
    """脸漂移 G1 + 主色 palette；每项独立 try——某项不可用只影响该项。"""
    checks: Dict[str, Any] = {}
    try:
        checks["face"] = run_face_check(root, margin)
    except Exception as exc:
        checks["face"] = {"available": False, "notes": [f"脸漂移机检失败：{exc}"]}
    try:
        checks["palette"] = run_palette_check(root, palette_threshold)
    except Exception as exc:
        checks["palette"] = {"available": False, "notes": [f"主色机检失败：{exc}"]}
    return checks


# ── 汇总（hard vs advisory）─────────────────────────────────────────────────

# HARD：主角脸崩（insightface 模式 block=真崩脸 / Pillow 模式 block=图损坏/不存在）。
# ADVISORY：主色 palette 初筛、锚点 lint、降级——汇报但不强制重抽（MV 筛选宽容）。
HARD_CHECKS = ("face",)
VISUAL_CHECK_LABELS = {"face": "主角脸漂移 G1", "palette": "主色漂移 palette"}
VISUAL_CHECK_DIMS = {"face": "character_consistency", "palette": "palette_consistency"}


def _notes_say_unavailable(res: Mapping[str, Any]) -> bool:
    notes = "；".join(str(n) for n in (res.get("notes") or []))
    return any(word in notes for word in ("不可用", "跳过", "未装", "缺依赖", "未找到"))


def unavailable_visual_checks(payload: Dict[str, Any]) -> List[str]:
    """请求了但不可用的像素检查（不算硬失败，但要让结果显示为降级而非静默 ok）。"""
    checks = payload.get("checks", {}) or {}
    out: List[str] = []
    for key in VISUAL_CHECK_LABELS:
        res = checks.get(key)
        if isinstance(res, dict) and (res.get("available") is False or _notes_say_unavailable(res)):
            out.append(key)
    return out


def summarize(payload: Dict[str, Any]) -> Dict[str, Any]:
    """汇总：hard（主角脸崩，必须重抽）vs advisory（主色/锚点/降级，人判）。"""
    hard = advisory = 0
    rows_by_check: Dict[str, Dict[str, int]] = {}
    for key in ("face", "palette"):
        res = payload.get("checks", {}).get(key) or {}
        cnt = count_verdicts(res.get("shots") or [])
        rows_by_check[key] = cnt
        if key in HARD_CHECKS:
            hard += cnt["block"]
            advisory += cnt["warn"]
        else:
            advisory += cnt["block"] + cnt["warn"]   # palette 初筛即便 block 也只人判
    lint = payload.get("lint") or {}
    l_warn = sum(1 for f in lint.get("findings", []) if f.get("level") == "warn")
    l_block = sum(1 for f in lint.get("findings", []) if f.get("level") == "block")
    rows_by_check["lint"] = {"block": l_block, "warn": l_warn, "noface": 0, "ok": 0}
    advisory += l_block + l_warn   # 锚点 lint 全 advisory（缺锚点块不硬拦，提示补）
    patch_outputs = (payload.get("prohibited_local_patch_outputs") or {}).get("outputs") or []
    if patch_outputs:
        rows_by_check["prohibited_local_patch"] = {"block": len(patch_outputs), "warn": 0, "noface": 0, "ok": 0}
        hard += len(patch_outputs)
    provenance_blocks = int(((payload.get("generation_provenance") or {}).get("summary") or {}).get("block") or 0)
    if provenance_blocks:
        if payload.get("formal_project"):
            hard += provenance_blocks
        else:
            advisory += provenance_blocks
        rows_by_check["generation_provenance"] = {
            "block": provenance_blocks if payload.get("formal_project") else 0,
            "warn": 0 if payload.get("formal_project") else provenance_blocks,
            "noface": 0,
            "ok": int(((payload.get("generation_provenance") or {}).get("summary") or {}).get("ok") or 0),
        }
    unavailable = unavailable_visual_checks(payload)
    face_mode = str((payload.get("checks", {}).get("face") or {}).get("mode") or "")
    degraded = bool(unavailable) or face_mode in FACE_DEGRADED_MODES
    return {"hard_blocks": hard, "advisory": advisory, "by_check": rows_by_check,
            "unavailable_visual_checks": unavailable, "degraded": degraded,
            "verdict": "block" if hard else ("review" if advisory or degraded else "ok")}


def qc_environment(payload: Dict[str, Any], *, with_pixel: bool = True) -> Dict[str, Any]:
    """机检能力 banner：full（脸 embedding+主色都在）/ degraded（部分不可用或脸降级）/ none。"""
    checks = payload.get("checks", {}) or {}
    unavailable = set(unavailable_visual_checks(payload))
    core = {"face", "palette"}
    face_mode = str((checks.get("face") or {}).get("mode") or "")
    degraded_face = face_mode in FACE_DEGRADED_MODES
    missing: List[str] = []
    if not with_pixel:
        level = "none"
        missing.append("pixel checks disabled by --no-pixel")
    elif core.issubset(unavailable):
        level = "none"
        missing.extend(VISUAL_CHECK_LABELS.get(k, k) for k in sorted(unavailable))
    elif unavailable or degraded_face:
        level = "degraded"
        missing.extend(VISUAL_CHECK_LABELS.get(k, k) for k in sorted(unavailable))
        if degraded_face:
            missing.append("insightface/onnxruntime/buffalo_l face embedding")
    else:
        level = "full"
    verdict = (payload.get("summary") or {}).get("verdict")
    if level == "none":
        jump_to, reason = "image_qc_setup", "像素质检不可用，不能把图片视为机检通过"
    elif level == "degraded":
        jump_to, reason = "image", "视觉质检为降级结果，正式进 mv-video 前需补依赖重跑或逐项人审确认"
    elif verdict == "block":
        jump_to, reason = "image", "image_qc 有硬阻断（主角脸崩），需修复/重抽受影响 clip 后重跑"
    elif verdict == "review":
        jump_to, reason = "video", "full image_qc 仅有非阻断初筛项（主色/锚点）；不阻断进入 mv-video"
    else:
        jump_to, reason = "video", "full QC 未见阻断"
    install = QC_INSTALL_RECOMMENDATION if level != "full" else ""
    return {
        "precision_level": level, "python": sys.executable, "face_mode": face_mode or None,
        "missing_or_degraded": sorted(set(missing)), "recommended_install": install,
        "jump_to_stage": jump_to, "jump_reason": reason,
        "user_notice": (f"MV 图片质检环境：{level}；当前解释器：{sys.executable}；"
                        f"建议安装：{install or '无需补装'}；当前应停在/回退：{jump_to}；原因：{reason}"),
    }


# ── 转 findings（mv-review / dashboard 接入用）──────────────────────────────

def _qc_finding(sev: str, dim: str, loc: Optional[str], msg: str) -> Dict[str, Any]:
    return {"sev": sev, "dim": dim, "loc": loc, "msg": msg, "return_to_stage": "image"}


def to_findings(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """image_qc payload → findings 列表。主角脸崩=block，主色/锚点=warn。纯函数·可测。"""
    out: List[Dict[str, Any]] = []
    checks = payload.get("checks", {}) or {}
    for key in unavailable_visual_checks(payload):
        res = checks.get(key) or {}
        note = "；".join(res.get("notes", [])) if isinstance(res, dict) else ""
        out.append(_qc_finding("warn", VISUAL_CHECK_DIMS.get(key, "image_qc"), None,
                               f"{VISUAL_CHECK_LABELS.get(key, key)} 未执行：{note or '视觉机检不可用'}；"
                               "本轮图片一致性为降级判定，需补依赖后重跑或人工复核。"))
    for s in (checks.get("face") or {}).get("shots", []):
        v = s.get("verdict")
        if v in ("block", "warn"):
            out.append(_qc_finding(v, "character_consistency", s.get("png"),
                                   f"主角脸漂移 G1 {v}：{s.get('png')}"
                                   f"（score={s.get('score')} floor={s.get('floor')}）"))
    for s in (checks.get("palette") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            out.append(_qc_finding("warn", "palette_consistency", s.get("png"),
                                   f"主色漂移 palette 初筛：{s.get('png')} 最近 anchor 距离 {s.get('nearest_dist')}"
                                   "（非阻断，MV 段落允许加亮/变暗）"))
    for f in (payload.get("lint", {}) or {}).get("findings", []):
        out.append(_qc_finding("warn", "anchor_prompt_lint", None, f.get("msg")))
    for row in (payload.get("prohibited_local_patch_outputs") or {}).get("outputs", []):
        out.append(_qc_finding("block", "local_patch_prohibited", row.get("png"),
                               f"生产事件账本显示该 MV 帧来自本地贴脸/换脸/混合修复：{row.get('png')} "
                               f"（line={row.get('line')} method={row.get('method')}）。"
                               "不得用本地身份像素贴回画面来通过一致性 QC，需回 mv-image 重抽。"))
    for row in (payload.get("generation_provenance") or {}).get("rows", []):
        if row.get("findings"):
            out.append(_qc_finding(
                "block" if payload.get("formal_project") else "warn",
                "image_generation_provenance", row.get("asset"),
                f"出图生成收据不完整：{row.get('asset')} · {', '.join(row.get('findings') or [])}",
            ))
    return out


# ── 重生成清单（mv-update / mv-review 消费） ──────────────────────────────────

_CLIP_RE = re.compile(r"(?:Clip[_\-\s]?)(\d+)")


def _clip_key(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    m = _CLIP_RE.search(str(name))
    if m:
        return f"Clip_{int(m.group(1)):03d}"
    return str(name).split("/")[-1] or None


def to_regen_list(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """不能用、要重抽的 clip：只收主角脸 block（崩脸）。主色/锚点 warn 不进（MV 筛选宽容）。纯函数·可测。"""
    by_clip: Dict[str, Dict[str, Any]] = {}

    def add(name: Optional[str], reason: str) -> None:
        key = _clip_key(name)
        if key is None:
            return
        d = by_clip.setdefault(key, {"clip": key, "png": None, "reasons": []})
        if name and ".png" in str(name) and not d["png"]:
            d["png"] = name
        if reason not in d["reasons"]:
            d["reasons"].append(reason)

    for s in (payload.get("checks", {}).get("face") or {}).get("shots", []):
        if s.get("verdict") == "block":
            add(s.get("png") or s.get("clip"), "主角脸崩 G1")
    for row in (payload.get("prohibited_local_patch_outputs") or {}).get("outputs", []):
        add(row.get("png") or row.get("clip"), "本地贴脸/换脸修复产物禁入")
    return sorted(by_clip.values(), key=lambda d: d["clip"])


def to_strict_regen_list(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """严审刷新候选：block/warn/降级都进候选重出清单（mv-update 用）。纯函数·可测。"""
    by_clip: Dict[str, Dict[str, Any]] = {}

    def add(name: Optional[str], reason: str) -> None:
        key = _clip_key(name)
        if key is None:
            return
        d = by_clip.setdefault(key, {"clip": key, "png": None, "reasons": []})
        if name and ".png" in str(name) and not d["png"]:
            d["png"] = name
        if reason not in d["reasons"]:
            d["reasons"].append(reason)

    checks = payload.get("checks", {}) or {}
    for s in (checks.get("face") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn", "noface"):
            add(s.get("png") or s.get("clip"), f"strict:脸/身份 {s.get('verdict')}")
    for s in (checks.get("palette") or {}).get("shots", []):
        if s.get("verdict") in ("block", "warn"):
            add(s.get("png") or s.get("clip"), f"strict:主色 {s.get('verdict')}")
    for f in (payload.get("lint", {}) or {}).get("findings", []):
        if f.get("level") in ("block", "warn"):
            add(f.get("msg"), f"strict:anchor:{f.get('code') or f.get('level')}")
    for row in (payload.get("prohibited_local_patch_outputs") or {}).get("outputs", []):
        add(row.get("png") or row.get("clip"), "strict:本地贴脸/换脸修复产物禁入")
    return sorted(by_clip.values(), key=lambda d: d["clip"])


# ── 报告落档 ──────────────────────────────────────────────────────────────────

def production_dir(root: Path) -> Path:
    return root / "生产数据"


def json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "item") and callable(value.item):
        try:
            return value.item()
        except Exception:
            pass
    return value


def run_qc(root: Path, with_pixel: bool = True, margin: float = DEFAULT_MARGIN,
           palette_threshold: float = PALETTE_DRIFT_THRESHOLD) -> Dict[str, Any]:
    meta = {}
    try:
        meta = json.loads((root / "_meta.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    payload: Dict[str, Any] = {"kind": "mv_image_qc", "version": 2, "root": str(root),
                               "formal_project": meta.get("is_demo") is False,
                               "checks": {}, "lint": {}}
    if with_pixel:
        with contextlib.redirect_stdout(sys.stderr):
            payload["checks"] = run_pixel_checks(root, margin, palette_threshold)
    payload["lint"] = lint_prompts(root)
    payload["prohibited_local_patch_outputs"] = prohibited_local_patch_outputs(root)
    payload["generation_provenance"] = generation_provenance(root)
    payload["summary"] = summarize(payload)
    payload["qc_environment"] = qc_environment(payload, with_pixel=with_pixel)
    payload = json_safe(payload)
    out_dir = production_dir(root) / "image_qc"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "image_qc.json"
    md_path = out_dir / "image_qc.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(md_path)
    return payload


def _check_line(label: str, res: Dict[str, Any], cnt: Dict[str, int]) -> str:
    if not res or res.get("available") is False:
        note = "；".join(res.get("notes", [])) if res else "未跑"
        return f"- {label}: ⏭ 跳过（{note or '不可用'}）"
    flag = "🔴" if cnt.get("block") else ("🟡" if cnt.get("warn") else "🟢")
    return f"- {label}: {flag} block {cnt.get('block', 0)} · warn {cnt.get('warn', 0)}"


def render_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    by = summary.get("by_check", {})
    checks = payload.get("checks", {})
    lines = [
        "# mv-image QC（出图落档机检）",
        "",
        f"- 总判定: **{summary.get('verdict', 'ok')}** · 硬阻断 {summary.get('hard_blocks', 0)}（主角脸崩，必须重抽）"
        f" · 非阻断初筛 {summary.get('advisory', 0)} · 视觉降级 {len(summary.get('unavailable_visual_checks') or [])}",
    ]
    env = payload.get("qc_environment", {}) or {}
    if env:
        lines.append(f"- 机检能力: **{env.get('precision_level')}** · 当前解释器: `{env.get('python')}`")
        lines.append(f"- 阶段跳转: **{env.get('jump_to_stage')}** · {env.get('jump_reason')}")
        if env.get("missing_or_degraded"):
            lines.append(f"- 缺失/降级: {', '.join(str(x) for x in env['missing_or_degraded'])}")
        if env.get("recommended_install"):
            lines.append(f"- 建议安装: {env.get('recommended_install')}")
    lines.extend([
        "",
        "## 像素机检（主角脸=硬阻断，主色=非阻断初筛）",
        _check_line("主角脸漂移 G1", checks.get("face"), by.get("face", {})),
        _check_line("主色漂移 palette", checks.get("palette"), by.get("palette", {})),
    ])
    face = checks.get("face") or {}
    if face.get("available"):
        lines.append(f"  - 主角 floor={face.get('lead_floor')} 自标定={face.get('lead_calibrated')} "
                     f"模式={face.get('mode')}")
    pal = checks.get("palette") or {}
    if pal.get("available"):
        lines.append(f"  - palette_anchor={pal.get('palette_anchor')} 阈值={pal.get('threshold')}")
    for key in ("face", "palette"):
        for n in (checks.get(key) or {}).get("notes", []):
            lines.append(f"  - note: {n}")
    lines.extend(["", "## 锚点句落地 lint（逐 clip prompt）"])
    lint = payload.get("lint", {})
    lcnt = by.get("lint", {})
    if not lint.get("available"):
        lines.append(f"- ⏭ 跳过（{'；'.join(lint.get('notes', [])) or '无 clip_plan'}）")
    else:
        flag = "🟡" if lcnt.get("warn") or lcnt.get("block") else "🟢"
        lines.append(f"- {flag} {lint.get('clips_linted', 0)} clip 已 lint · warn {lcnt.get('warn', 0)}")
        for f in lint.get("findings", []):
            lines.append(f"  - 🟡 {f.get('msg')}")
    for n in lint.get("notes", []):
        lines.append(f"- note: {n}")
    patch = payload.get("prohibited_local_patch_outputs") or {}
    patch_rows = patch.get("outputs") or []
    lines.extend(["", "## 禁用本地身份像素修复检查"])
    if patch_rows:
        lines.append(f"- 🔴 发现 {len(patch_rows)} 个本地贴脸/换脸/混合修复产物，不得进入 mv-video。")
        for row in patch_rows:
            lines.append(f"  - 🔴 {row.get('png')} · event line {row.get('line')} · method={row.get('method')}")
    else:
        event_path = patch.get("event_path")
        status = "有事件账本，未命中禁用产物" if patch.get("available") else f"无事件账本（{event_path}）"
        lines.append(f"- 🟢 {status}")
    provenance = payload.get("generation_provenance") or {}
    lines.extend(["", "## 出图签收（模型 × 渠道 × prompt × reference × asset hash）"])
    pairs = provenance.get("model_channel_pairs") or []
    if pairs:
        lines.append("- 本项目实际模型/渠道：" + "；".join(
            f"{row.get('model')} / {row.get('channel')}" for row in pairs
        ))
    else:
        lines.append("- 🔴 未找到可验证的出图模型/渠道收据。")
    for row in provenance.get("rows") or []:
        flag = "🟢" if row.get("verdict") == "ok" else "🔴"
        detail = ", ".join(str(item) for item in (row.get("findings") or [])) or "receipt fresh"
        lines.append(
            f"- {flag} {row.get('clip')} · {row.get('asset')} · "
            f"{row.get('model') or '?'} / {row.get('channel') or '?'} · "
            f"refs={row.get('reference_count', 0)} · subjects={row.get('subject_count', 0)} · {detail}"
        )
    lines.append("")
    lines.append("落档判定：**verdict=block** → 主角脸崩（崩脸/图损坏），必须重抽后重跑；"
                 "**verdict=review** → 只有主色/锚点等非阻断初筛或视觉降级时不挡 mv-video（按阶段跳转补依赖/复核）；"
                 "**verdict=ok** → 放行。主色与锚点是像素初筛/确定性 lint，非硬失败（MV 筛选宽容铁律）。")
    return "\n".join(lines) + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", help="创作区/制MV/<曲名>/ 作品根")
    ap.add_argument("--no-pixel", action="store_true", help="只跑锚点 lint，不跑像素机检")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN, help="脸漂移 flag-band 缓冲（默认 0.08）")
    ap.add_argument("--palette-threshold", type=float, default=PALETTE_DRIFT_THRESHOLD,
                    help="主色漂移最近距离阈值（默认 110）")
    ap.add_argument("--json", action="store_true", help="打印机器可读 payload")
    ap.add_argument("--findings", action="store_true", help="打印与 mv-review/gate 同形的 findings")
    ap.add_argument("--regen-list", action="store_true", help="打印「要重抽」的 clip（普通落档 QC；warn 不进）")
    ap.add_argument("--strict", action="store_true", help="严审刷新：block/warn/降级都进候选重出清单")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    if not root.is_dir():
        ap.error(f"找不到作品根：{root}")
    payload = run_qc(root, with_pixel=not ns.no_pixel, margin=ns.margin,
                     palette_threshold=ns.palette_threshold)
    regen = to_strict_regen_list(payload) if ns.strict else to_regen_list(payload)
    if ns.regen_list:
        print(json.dumps(regen, ensure_ascii=False))
    elif ns.findings:
        print(json.dumps(to_findings(payload), ensure_ascii=False))
    elif ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(payload["markdown_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
