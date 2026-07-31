#!/usr/bin/env python3
"""③ 语义漂移信号（DINO/CLIP-I）——在调色板 dHash 之上加一路语义相似度。

**为什么**：image_qc 的 发型 H1 / 服装 N1 / 场景 O2 / 道具 P2 机检走**调色板 + dHash**，项目自己标注为
「初筛、非阻断」。调色板的盲区正是最常见的服装漂——**同色但剪裁/结构变了**（月白圆领→月白交领），dHash
也抓不到布局漂。2026 身份保真评测标准：脸用 ArcFace/InsightFace，**非脸身份（服装/场景/整体）用
DINO + CLIP-I 图像级 cosine**。本模块把「资产参考 ↔ 本镜」的语义 cosine 当**第二意见**，盖在调色板之上：

  - 调色板**没报**但语义 cosine 低 → `semantic_drift_low`（warn·人判）：palette 漏掉的结构/剪裁漂移；
  - 调色板**报了**但语义 cosine 高 → `semantic_drift_lighting`（info）：疑似只是灯光/天气，人审优先级可降。

本模块自身只产 advisory 信号；但 `image_qc` 发现已登记关键场景/道具/服装/VFX 需要语义复核而本模块不可用时，
会把“语义嵌入缺席”升为 hard block，避免 palette/dHash 初筛被误当成非脸资产已通过。

依赖是 **opt-in**：full 精度 env 装 torch+transformers（DINOv2/CLIP）或 open_clip 才跑嵌入；缺则
`available=False`、整段跳过，**绝不阻断默认无依赖产线**。默认只读本地缓存，显式
`N2D_ALLOW_MODEL_DOWNLOAD=1` 才允许下载模型，避免 image_qc 被远程模型/DNS 卡死。纯函数（cosine + 判定）
有 pytest 覆盖；模型加载与逐图嵌入是 best-effort I/O。

阈值采集口径：DINOv2 同物异姿 cosine 常 ≥0.7，异物明显更低；保守取 SEMANTIC_FLOOR=0.55 起步，应在真实
渲染集上按后端/风格标定（与 n2d-review 阈值同理需 freshness 复核）。

用法：python3 semantic_drift.py <作品根> <第N集> [--json]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

# DINOv2 同物异姿 cosine 常 ≥0.7；异物/换装更低。保守起步线，需按真实渲染集标定。
# 可经 N2D_SEMANTIC_FLOOR 覆盖——换嵌入后端（如 DreamSim，cosine 尺度与 DINO 不同）时按真实渲染集重标定。
try:
    SEMANTIC_FLOOR = float(os.environ.get("N2D_SEMANTIC_FLOOR", "0.55"))
except (TypeError, ValueError):
    SEMANTIC_FLOOR = 0.55

Embedder = Callable[[str], Optional[List[float]]]


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def cosine(a: Optional[Sequence[float]], b: Optional[Sequence[float]]) -> Optional[float]:
    """两向量余弦；任一为空/零向量/长度不等 → None。纯函数·可测。"""
    if not a or not b or len(a) != len(b):
        return None
    dot = sum(float(x) * float(y) for x, y in zip(a, b))
    na = math.sqrt(sum(float(x) * float(x) for x in a))
    nb = math.sqrt(sum(float(y) * float(y) for y in b))
    if na == 0.0 or nb == 0.0:
        return None
    return dot / (na * nb)


def semantic_finding(palette_verdict: Optional[str], cos: Optional[float],
                     floor: float = SEMANTIC_FLOOR) -> Optional[Dict[str, str]]:
    """调色板结论 × 语义 cosine → advisory 信号（纯函数·可测）。

    palette_verdict ∈ {ok, info, warn, block, None}。返回 {level, code, tag} 或 None：
      - palette 未报(ok/info/None) 且 cos<floor → warn `semantic_drift_low`（palette 漏掉的结构漂）；
      - palette 报了(warn/block) 且 cos≥floor → info `semantic_drift_lighting`（疑似只灯光/天气，降优先级）；
      - 其余（两者一致）→ None，不加噪。cos=None（嵌入失败）→ None。"""
    if cos is None:
        return None
    palette_flagged = str(palette_verdict or "").lower() in ("warn", "block")
    if cos < floor and not palette_flagged:
        return {"level": "warn", "code": "semantic_drift_low", "tag": "palette_missed"}
    if cos >= floor and palette_flagged:
        return {"level": "info", "code": "semantic_drift_lighting", "tag": "palette_maybe_lighting"}
    return None


def _pairs_from_payload(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """从 image_qc payload 的 scene/multimodal 逐镜结果抽出 (kind, asset, shot_png, palette_verdict)。
    **全镜**（不止 block/warn）——因为本模块的价值正是抓 palette 没报的漂移。纯函数·可测。"""
    checks = payload.get("checks", {}) or {}
    out: List[Dict[str, Any]] = []
    for s in (checks.get("scene") or {}).get("shots", []):
        if isinstance(s, Mapping) and s.get("png"):
            out.append({"kind": "scene", "asset": str(s.get("scene") or s.get("group") or ""),
                        "png": s.get("png"), "palette_verdict": s.get("verdict")})
    for s in (checks.get("multimodal") or {}).get("shots", []):
        if isinstance(s, Mapping) and s.get("png"):
            out.append({"kind": "asset", "asset": str(s.get("asset") or s.get("group") or s.get("scene") or ""),
                        "png": s.get("png"), "palette_verdict": s.get("verdict")})
    # 服装 N1：本模块文档点名的头号用例——「同色但剪裁/结构变了」（月白圆领→月白交领）调色板抓不到。
    # outfit shot 的 asset 是角色名（非 LOC/PROP id），参考解析在 analyze 走 定妆_<角色> 兜底。
    for s in (checks.get("outfit") or {}).get("shots", []):
        if isinstance(s, Mapping) and s.get("png"):
            out.append({"kind": "outfit", "asset": str(s.get("char") or s.get("group") or ""),
                        "png": s.get("png"), "palette_verdict": s.get("verdict")})
    return out


def evaluate_pairs(pairs: Sequence[Mapping[str, Any]],
                   embed: Embedder,
                   resolve_ref: Callable[[str], Optional[str]],
                   shot_abspath: Callable[[str], str],
                   floor: float = SEMANTIC_FLOOR) -> Dict[str, Any]:
    """对 (资产参考 ↔ 本镜) 逐对算语义 cosine 并据 palette 结论产 advisory findings。

    embed: abspath→向量（None=该图嵌入失败）；resolve_ref: 资产名→参考相对路径；
    shot_abspath: 镜相对路径→绝对路径。findings=warn/info，never block。可测（注入 stub）。"""
    findings: List[Dict[str, str]] = []
    compared = 0
    cache: Dict[str, Optional[List[float]]] = {}

    def _emb(path: str) -> Optional[List[float]]:
        if path not in cache:
            cache[path] = embed(path)
        return cache[path]

    for p in pairs:
        ref_rel = resolve_ref(str(p.get("asset") or ""))
        png_rel = p.get("png")
        if not ref_rel or not png_rel:
            continue
        ref_vec = _emb(ref_rel)
        shot_vec = _emb(shot_abspath(str(png_rel)))
        cos = cosine(ref_vec, shot_vec)
        if cos is None:
            continue
        compared += 1
        sig = semantic_finding(p.get("palette_verdict"), cos, floor)
        if not sig:
            continue
        if sig["tag"] == "palette_missed":
            msg = (f"{p['kind']} 语义漂移疑似（调色板未报）：参考「{p.get('asset')}」↔ 本镜 {png_rel} "
                   f"DINO/CLIP cosine={cos:.2f} < {floor}——同色但剪裁/结构/布局可能变了（palette/dHash 抓不到），人判。")
        else:
            msg = (f"{p['kind']} 调色板报漂移但语义相符（cosine={cos:.2f} ≥ {floor}）：参考「{p.get('asset')}」↔ "
                   f"本镜 {png_rel} 疑似只是灯光/天气差异，人审优先级可降。")
        findings.append({"level": sig["level"], "code": sig["code"], "msg": msg})
    return {"available": True, "compared": compared, "floor": floor, "findings": findings}


def allow_model_download() -> bool:
    return os.environ.get("N2D_ALLOW_MODEL_DOWNLOAD", "").strip().lower() in {"1", "true", "yes", "on"}


def _dreamsim_embedder() -> Optional[Embedder]:
    """DreamSim 感知嵌入（2026 同主体判定基准·胜原始 CLIP/DINO cosine，专调"是否同一主体"）。best-effort·opt-in。
    注意：DreamSim 嵌入 cosine 尺度与 DINO 不同——用它时按真实渲染集经 `N2D_SEMANTIC_FLOOR` 重标定 floor。"""
    try:
        import torch  # type: ignore
        from PIL import Image  # type: ignore
        from dreamsim import dreamsim  # type: ignore

        if not allow_model_download():
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
        model, preprocess = dreamsim(pretrained=True)
        if hasattr(model, "eval"):
            model.eval()

        def _embed_ds(path: str) -> Optional[List[float]]:
            try:
                with Image.open(path) as im:
                    tensor = preprocess(im.convert("RGB"))
                with torch.no_grad():
                    vec = model.embed(tensor).squeeze(0)
                return [float(x) for x in vec.tolist()]
            except Exception:
                return None

        return _embed_ds
    except Exception:
        return None


# ── 嵌入后端（best-effort·opt-in） ─────────────────────────────────────────────

def load_embedder() -> Optional[Embedder]:
    """返回 abspath→向量 的嵌入器；无可用后端 → None（整段跳过，不阻断默认产线）。

    默认顺序 DINOv2（transformers facebook/dinov2-small）→ open_clip → DreamSim（最后，沿用既有 DINO floor 标定）。
    `N2D_SEMANTIC_BACKEND=dreamsim` 显式前置 DreamSim（2026 同主体判定基准，胜原始 cosine；记得按需调 N2D_SEMANTIC_FLOOR）。
    模型下载/加载在 full 精度 conda env 内做，与 image_qc 同环境（facefusion）。任何 import/加载异常 → None。"""
    if os.environ.get("N2D_SEMANTIC_BACKEND", "").strip().lower() == "dreamsim":
        return _dreamsim_embedder()
    # DINOv2 via transformers
    try:
        import torch  # type: ignore
        from PIL import Image  # type: ignore
        from transformers import AutoImageProcessor, AutoModel  # type: ignore

        name = os.environ.get("N2D_DINO_MODEL", "facebook/dinov2-small")
        local_only = not allow_model_download()
        proc = AutoImageProcessor.from_pretrained(name, use_fast=True, local_files_only=local_only)
        model = AutoModel.from_pretrained(name, local_files_only=local_only)
        model.eval()

        def _embed(path: str) -> Optional[List[float]]:
            try:
                with Image.open(path) as im:
                    inputs = proc(images=im.convert("RGB"), return_tensors="pt")
                with torch.no_grad():
                    out = model(**inputs)
                vec = out.last_hidden_state[:, 0].squeeze(0)  # CLS token
                return [float(x) for x in vec.tolist()]
            except Exception:
                return None

        return _embed
    except Exception:
        pass

    # 退 open_clip（CLIP-I 图像嵌入）——比 transformers 全栈更轻，部分环境更易装到；同样 best-effort。
    try:
        import open_clip  # type: ignore
        import torch  # type: ignore
        from PIL import Image  # type: ignore

        model_name = os.environ.get("N2D_OPENCLIP_MODEL", "ViT-B-32")
        pretrained = os.environ.get("N2D_OPENCLIP_PRETRAINED", "laion2b_s34b_b79k")
        if not allow_model_download():
            # 仅用本地缓存：缺权重时 create_model_and_transforms 会抛 → 落到 except 返回 None，不触网。
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
        model, _, preprocess = open_clip.create_model_and_transforms(model_name, pretrained=pretrained)
        model.eval()

        def _embed_oc(path: str) -> Optional[List[float]]:
            try:
                with Image.open(path) as im:
                    tensor = preprocess(im.convert("RGB")).unsqueeze(0)
                with torch.no_grad():
                    vec = model.encode_image(tensor).squeeze(0)
                return [float(x) for x in vec.tolist()]
            except Exception:
                return None

        return _embed_oc
    except Exception:
        pass

    # 退 DreamSim（默认放最后：DINO/open_clip 优先以沿用既有 floor 标定；只装了 DreamSim 时仍可用）
    return _dreamsim_embedder()


def _resolve_char_makeup_ref(root: Path, char: str) -> Optional[str]:
    """outfit/角色名 → 该角色定妆参考图绝对路径（服装语义对照用）。

    取 出图/共享/图片/定妆_<角色>*.png，优先「常态」全身定妆板；排除脸部特写/表情库
    （那些主体是脸不是衣，喂给服装语义对照会失真）。找不到→None（该 pair 安全跳过）。"""
    name = str(char or "").strip()
    if not name:
        return None
    base = Path(root) / "出图" / "共享" / "图片"
    if not base.is_dir():
        return None
    cands = [c for c in sorted(base.glob(f"定妆_{name}*.png"))
             if not any(x in c.name for x in ("脸部特写", "表情", "_脸"))]
    if not cands:
        return None
    for c in cands:
        if "常态" in c.name:
            return str(c)
    return str(cands[0])


def analyze(root: Path, ep: str, payload: Mapping[str, Any],
            embedder: Optional[Embedder] = None, floor: float = SEMANTIC_FLOOR) -> Dict[str, Any]:
    """image_qc 集成入口：从 payload 抽 (参考↔镜) 对，跑语义 cosine。embedder=None → 尝试自动加载。
    无嵌入后端 → available=False（advisory 跳过）。"""
    emb = embedder if embedder is not None else load_embedder()
    if emb is None:
        return {"available": False, "compared": 0,
                "notes": ["DINO/CLIP 嵌入后端不可用——语义漂移信号跳过（full env 装 torch+transformers 后复检）。"],
                "findings": []}
    # 复用 image_qc 的资产参考解析（与人审拼图同一份），避免两套解析口径。
    root_path = Path(root)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import image_qc  # type: ignore
        pm = image_qc._asset_primary_map(root_path)
        _asset_ref = lambda hint: image_qc._resolve_asset_ref(root_path, pm, hint)  # noqa: E731
    except Exception:
        _asset_ref = lambda hint: None  # noqa: E731

    def resolve_ref(hint: str) -> Optional[str]:
        # _resolve_asset_ref 返回 root-相对路径，绝对化后再喂 embed（embed 直开此路径，
        # 不经 shot_abspath，否则 cwd≠root 时参考图打不开、整段静默 cosine=None）。
        rel = _asset_ref(hint)
        if rel:
            return str(root_path / rel)
        # outfit/角色名 不在 asset_registry → 兜底取角色定妆图（服装结构对照）。
        return _resolve_char_makeup_ref(root_path, hint)

    shot_abspath = lambda rel: str(root_path / "出图" / ep / rel)  # noqa: E731
    pairs = _pairs_from_payload(payload)
    return evaluate_pairs(pairs, emb, resolve_ref, shot_abspath, floor)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).expanduser().resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import image_qc  # type: ignore
    payload = image_qc.run_qc(root, ns.episode)
    res = analyze(root, ns.episode, payload)
    if ns.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if not res.get("available"):
        print("⏭ 语义漂移信号跳过：" + "；".join(res.get("notes", [])))
        return 0
    print(f"语义漂移（{ns.episode}）：比对 {res['compared']} 对 · floor {res['floor']} · "
          f"{len(res['findings'])} 条 advisory")
    for f in res["findings"]:
        print(f"  [{f['level']}] {f['msg']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
