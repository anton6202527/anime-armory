#!/usr/bin/env python3
"""场景**语义嵌入**一致性（DINOv2/CLIP）—— 给 SCNX 跨集场景漂移补一条学习型指纹。

背景（2026-06 场景轴审计）：脸有 ArcFace **embedding**；场景此前只有 10+10 bin 的 HSV 色调直方图。
色调直方图对**几何/材质/布局**是盲的——同一调色盘下把家具挪位、换了墙面材质、改了空间结构，
直方图 L1 几乎不动却已是另一个房间。`consistency_audit.py` 自己也标注「DINOv2 序列级是未来升级」。

本模块把那条升级落地：用 DINOv2（或 CLIP）给每镜出语义嵌入，按场景取均值，作为场景的**学习型指纹**，
跨集比 **cosine** 距离。它与色调直方图(SCNX-color)、结构 dHash(SCNX-struct) 是**互补**信号
（各自抓色温漂 / 布局漂 / 语义-材质漂），高成本场景轴该有的冗余。

重型依赖隔离（设计律 C4）：torch/DINOv2 不进主流程。本模块只做纯编排 + cosine 漂移判定（有 pytest），
真正的嵌入由可选 batch 后端 `backends/scene_embed_dinov2.py` 在 conda 环境出，经
env `N2D_SCENE_EMBED_BATCH_CMD` 调起，落 `生产数据/scene_embed_<集>.json`。没后端 → 返回空 →
SCNX 优雅退回色调/结构指纹（既有、已测），绝不硬失败。

用法：python3 scene_embed.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import face_consistency as fc  # 复用 cosine
import scene_consistency as sc  # 复用 _scene_of_shot / _probe 场景分组

SCENE_EMBED_KIND = "n2d_scene_embed"
# 跨集场景语义嵌入漂移阈（cosine 距离 = 1 - cos）。嵌入比色调判别力强、噪声低，故阈比色调 L1 紧。
SCENE_EMBED_DRIFT_WARN = 0.12
SCENE_EMBED_DRIFT_BLOCK = 0.22


# ── 纯逻辑（pytest 覆盖）────────────────────────────────────────────────────────

def mean_embedding(vectors: Sequence[Sequence[float]]) -> List[float]:
    """逐维均值（纯函数·可测）。空→[]；维度不一以首条为准（容错）。"""
    vs = [list(v) for v in vectors if v]
    if not vs:
        return []
    dim = len(vs[0])
    out = [0.0] * dim
    n = 0
    for v in vs:
        if len(v) != dim:
            continue
        for i in range(dim):
            out[i] += float(v[i])
        n += 1
    if n == 0:
        return []
    return [round(x / n, 6) for x in out]


def _episode_num(ep: str) -> int:
    import re
    m = re.search(r"(\d+)", str(ep))
    return int(m.group(1)) if m else 0


def scene_embed_drift_rows(means_by_ep: Mapping[str, Mapping[str, Sequence[float]]], cur_ep: str,
                           core_scenes: Iterable[str] = (),
                           warn: float = SCENE_EMBED_DRIFT_WARN,
                           block: float = SCENE_EMBED_DRIFT_BLOCK) -> List[dict]:
    """跨集场景语义嵌入漂移判定（纯函数·可测）。当前集每场景嵌入 vs 历史各集嵌入的均值基线比
    cosine 距离(1-cos)：≥warn 出行；核心场景且 ≥block → block，否则 warn。≥2 集出现该场景才比。"""
    core = [c for c in (core_scenes or ()) if c]
    cur = means_by_ep.get(cur_ep) or {}
    eps_prior = [e for e in means_by_ep if _episode_num(e) < _episode_num(cur_ep)]
    rows: List[dict] = []
    for scene, cur_vec in sorted(cur.items()):
        priors = [means_by_ep[e][scene] for e in eps_prior
                  if isinstance(means_by_ep.get(e), dict) and means_by_ep[e].get(scene)]
        if not priors or not cur_vec:
            continue
        base = mean_embedding(priors)
        if not base or len(base) != len(cur_vec):
            continue
        dist = round(1.0 - fc.cosine(list(cur_vec), base), 4)
        if dist < warn:
            continue
        is_core = any(scene in c or c in scene for c in core)
        verdict = "block" if (is_core and dist >= block) else "warn"
        rows.append({
            "verdict": verdict,
            "shot": f"场景[{scene}] 跨{len(priors) + 1}集语义",
            "msg": (f"场景[{scene}] 跨集语义嵌入漂移 cos距={dist}（DINOv2·vs 前 {len(priors)} 集基线，阈 warn={warn}"
                    f"{'·core block=' + str(block) if is_core else ''}）"
                    + ("——核心场景跨集语义硬漂：连材质/几何/布局都变样了（远超色调能测的范围），"
                       "回 n2d-image 对齐场景定妆；若为有意改建/换季按 allowed_variations 签收。"
                       if verdict == "block"
                       else "——语义指纹偏移（疑材质/结构/布局变化，非单纯色温），核对是否同一空间。")),
            "scene": scene,
            "evidence": "embedding",
        })
    return rows


# ── I/O（best-effort）──────────────────────────────────────────────────────────

def _embed_sidecar_path(root: str, ep: str) -> str:
    return os.path.join(root, "生产数据", f"scene_embed_{ep}.json")


def build_manifest(root: str, ep: str) -> dict:
    """每镜 PNG → 它引用的场景，配出待嵌入清单（可复现）。后端就地回填每镜 `embedding`。"""
    smap = sc._scene_of_shot(root, ep)
    probes: List[dict] = []
    for png, scene in sorted(smap.items()):
        rel = os.path.join("出图", ep, png)
        if os.path.isfile(os.path.join(root, rel)):
            probes.append({"shot": png, "scene": scene, "image": rel, "embedding": None})
    return {"kind": SCENE_EMBED_KIND, "root": root, "episode": ep, "probes": probes}


def _run_batch(path: str) -> bool:
    cmd = os.environ.get("N2D_SCENE_EMBED_BATCH_CMD", "").strip()
    if not cmd:
        return False
    try:
        subprocess.run([*cmd.split(), path], timeout=3600, check=True)
        return True
    except Exception as exc:
        print(f"[scene_embed][warn] batch 后端调用失败（忽略）：{exc}", file=sys.stderr)
        return False


def scene_embed_means(root: str, ep: str) -> Dict[str, List[float]]:
    """本集每场景的平均语义嵌入（读后端已回填的 scene_embed_<集>.json 逐镜 embedding，按场景取均值）。

    供 SCNX 跨集语义漂移累积。后端没跑/sidecar 缺/嵌入未回填 → 返回 {}（SCNX 退回色调/结构指纹）。"""
    path = _embed_sidecar_path(root, ep)
    if not os.path.isfile(path):
        return {}
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    groups: Dict[str, List[List[float]]] = {}
    for p in (data.get("probes") or []):
        emb = p.get("embedding")
        scene = str(p.get("scene") or "")
        if scene and isinstance(emb, list) and emb:
            groups.setdefault(scene, []).append([float(x) for x in emb])
    return {scene: mean_embedding(vs) for scene, vs in groups.items() if vs}


def write(root: str, ep: str) -> str:
    """产 manifest → 调后端就地回填逐镜 embedding。无后端则留 probe-only（embedding=None）。"""
    manifest = build_manifest(root, ep)
    path = _embed_sidecar_path(root, ep)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _run_batch(path)
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="场景语义嵌入(DINOv2) manifest/runner")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = ns.root.rstrip("/")
    if ns.write:
        path = write(root, ns.episode)
        if not ns.json:
            print(path)
            return 0
    means = scene_embed_means(root, ns.episode)
    if ns.json:
        print(json.dumps({"scenes": list(means.keys()), "dims": {s: len(v) for s, v in means.items()}},
                         ensure_ascii=False, indent=2))
    else:
        backend = "on" if os.environ.get("N2D_SCENE_EMBED_BATCH_CMD") else "off(manifest only)"
        print(f"scenes_embedded={len(means)} backend={backend}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
