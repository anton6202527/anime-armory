#!/usr/bin/env python3
"""场景常驻陈设(set-dressing)在场检测 —— 补 LOC `scene_dna.resident_assets` 只申报、不验证的缺口。

背景（2026-06 场景轴审计）：场景定妆里 `resident_assets`（残烛/铜镜/床榻/碎梁这类 set-dressing）是
**必填字段，但此前只查「非空」**，从没人验证这些陈设真的画进了场景镜——同一房间隔几镜/几集
就可能悄悄丢了残匾、换了床榻，没有任何机检。人物/常驻 PROP 有 O3V 在场检测，场景陈设没有。

本脚本把每个 LOC 的 `resident_assets` 转成在场探针，复用 O3V 同一套开放词表后端
（`backends/presence_owlv2.py`，env `N2D_PRESENCE_BATCH_CMD`）。**判据是场景级而非逐镜**：
特写不会框到地砖，所以「某镜没拍到」不算丢——只有一个陈设在该场景**所有**被探的镜里**全部缺席**，
才判它真从这个场景消失了（warn；核心场景 block）。结果写进 `生产数据/resident_presence_<集>.json`，
由 `extended_consistency.check_object_presence_visual`（O3V）一并消费。

graceful degradation（设计律 C4）：没配检测后端时只产可复现 manifest + 一条 advisory note，
绝不凭空 block，待装好后端的环境复跑。纯逻辑（提取 + 场景级聚合）有 pytest。

用法：python3 resident_presence.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping

import scene_consistency as sc

RESIDENT_PRESENCE_KIND = "n2d_object_presence"  # 与 O3V 同 kind，便于 check_object_presence_visual 直接消费


# ── 纯逻辑（pytest 覆盖）────────────────────────────────────────────────────────

def _resident_entry(raw: Any) -> Dict[str, str]:
    """resident_assets 条目归一：兼容旧字符串和新版 {asset/name, phrase/detect_phrase}。"""
    if isinstance(raw, Mapping):
        asset = str(raw.get("asset") or raw.get("name") or raw.get("label") or raw.get("phrase") or "").strip()
        phrase = str(raw.get("phrase") or raw.get("detect_phrase") or raw.get("detect") or asset).strip()
        return {"asset": asset, "phrase": phrase}
    text = str(raw or "").strip()
    return {"asset": text, "phrase": text}


def scene_resident_assets(registry: Mapping[str, Mapping[str, Any]]) -> Dict[str, List[Dict[str, str]]]:
    """{LOC_id: [{asset, phrase}]}（纯函数·可测）。只取 LOC 资产 scene_dna.resident_assets 非空者。"""
    out: Dict[str, List[Dict[str, str]]] = {}
    for aid, asset in (registry or {}).items():
        if not str(aid).startswith("LOC_") or not isinstance(asset, dict):
            continue
        sd = asset.get("scene_dna")
        residents = (sd or {}).get("resident_assets") if isinstance(sd, dict) else None
        if isinstance(residents, (list, tuple)):
            entries = [_resident_entry(r) for r in residents]
            entries = [e for e in entries if e.get("asset") and e.get("phrase")]
            if entries:
                out[str(aid)] = entries
    return out


def aggregate_scene_findings(manifest: Mapping[str, Any], core_scenes: Iterable[str] = ()) -> List[dict]:
    """场景级聚合（纯函数·可测）：一个陈设在它所属场景**所有被探镜**里全部缺席 → 判它从该场景消失。

    读 manifest.probes（每镜 expected_assets）+ manifest.findings（后端逐镜回填的 present:False 缺席），
    产 O3V 形状的场景级 finding。后端没跑（findings 空）→ 无缺席证据 → 不产 finding（不凭空 block）。"""
    probes = manifest.get("probes") or []
    findings = manifest.get("findings") or []
    absent = {(str(f.get("shot")), str(f.get("asset")))
              for f in findings if isinstance(f, dict) and f.get("present") is False}
    scene_asset_shots: Dict[tuple, set] = defaultdict(set)
    for p in probes:
        scene = str(p.get("scene"))
        shot = str(p.get("shot"))
        for ea in p.get("expected_assets") or []:
            scene_asset_shots[(scene, str(ea.get("asset")))].add(shot)
    core = [c for c in (core_scenes or ()) if c]
    out: List[dict] = []
    for (scene, asset), shots in sorted(scene_asset_shots.items()):
        if shots and all((s, asset) in absent for s in shots):
            is_core = any(scene in c or c in scene for c in core)
            out.append({
                "shot": f"场景[{scene}]",
                "asset": asset,
                "expected": True,
                "present": False,
                "severity": "block" if is_core else "warn",
                "message": (f"登记常驻陈设「{asset}」在场景[{scene}]的 {len(shots)} 个镜中全部未检出——"
                            "该场景丢了 set-dressing（resident_assets 申报了却没画出/被换掉），"
                            "回 n2d-image 把陈设补进场景定妆，或确认是否 allowed_variations 内的合理变化。"),
            })
    return out


# ── I/O（best-effort）──────────────────────────────────────────────────────────

def build_manifest(root: str, ep: str) -> dict:
    registry = sc._load_asset_registry(root)
    residents_by_loc = scene_resident_assets(registry)
    smap = sc._scene_of_shot(root, ep)  # png -> 场景定妆 token
    probes: List[dict] = []
    for png, scene in sorted(smap.items()):
        aid = sc._match_asset_id(scene, registry)
        residents = residents_by_loc.get(aid) if aid else None
        if not residents:
            continue
        rel = os.path.join("出图", ep, png)
        if not os.path.isfile(os.path.join(root, rel)):
            continue
        probes.append({
            "shot": png,
            "scene": scene,
            "loc": aid,
            "image": rel,
            "expected_assets": [{"asset": r["asset"], "phrase": r["phrase"]} for r in residents],
        })
    return {
        "kind": RESIDENT_PRESENCE_KIND,
        "source": "resident_presence",
        "root": root,
        "episode": ep,
        "probes": probes,
        "findings": [],
    }


def _run_batch(path: str) -> bool:
    """复用 O3V 同一 batch 后端契约（N2D_PRESENCE_BATCH_CMD）：传 manifest 路径，就地回填 findings。"""
    cmd = os.environ.get("N2D_PRESENCE_BATCH_CMD", "").strip()
    if not cmd:
        return False
    try:
        subprocess.run([*cmd.split(), path], timeout=3600, check=True)
        return True
    except Exception as exc:
        print(f"[resident_presence][warn] batch 后端调用失败（忽略，保留 manifest）：{exc}", file=sys.stderr)
        return False


def _core_scenes(root: str) -> List[str]:
    try:
        from n2d_cross_episode import core_scene_names
        return core_scene_names(root)
    except Exception:
        return []


def write(root: str, ep: str) -> str:
    manifest = build_manifest(root, ep)
    path = os.path.join(root, "生产数据", f"resident_presence_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # 先落 probe-only manifest 给 batch 后端就地回填逐镜 present
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    ran = _run_batch(path)
    if ran:
        try:
            manifest = json.load(open(path, encoding="utf-8"))
        except Exception:
            pass
    manifest["detector_ran"] = ran
    # 逐镜缺席 → 场景级聚合（最终 findings）。后端没跑则给 advisory note，不产 finding。
    manifest["findings"] = aggregate_scene_findings(manifest, core_scenes=_core_scenes(root))
    if not ran:
        manifest.setdefault("notes", []).append(
            "未配置在场检测后端（N2D_PRESENCE_BATCH_CMD）；场景常驻陈设只产探针清单，"
            "陈设是否真画进场景仍由人判兜底。装好 OWLv2 后端后复跑即可机检。")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="场景常驻陈设在场检测 manifest/runner")
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
        print(json.dumps(json.load(open(path, encoding="utf-8")), ensure_ascii=False, indent=2))
        return 0
    manifest = build_manifest(root, ns.episode)
    if ns.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"probes={len(manifest['probes'])} "
              f"detector={'on' if os.environ.get('N2D_PRESENCE_BATCH_CMD') else 'off(manifest only)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
