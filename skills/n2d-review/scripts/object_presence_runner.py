#!/usr/bin/env python3
"""O3V 视觉级在场检测 runner —— 关掉"物件常驻只有契约文本、无视觉在场检测"的 backlog。

本脚本本身不绑定重模型：它发现每个出图镜头里**应在场的登记常驻资产**（asset_registry 里标
常驻/恒存/drift_forbidden 的 PROP/WEAPON/OUTFIT/VFX），按 LOC 配出"该帧应出现哪些对象"的 probe 清单，
写成可复现 manifest。若配置了开放词表检测器/VLM 命令（env `N2D_PRESENCE_CMD`），逐帧调它判在场，
把结果填进 `findings`，供 `extended_consistency.check_object_presence_visual`（O3V）消费。

外部命令契约（二选一，batch 优先——重模型只加载一次）：
* `N2D_PRESENCE_BATCH_CMD`（推荐）：收 `<manifest_path>`，就地把 `probes` 里 expected 但缺席的对象
  写进该文件的 `findings` 数组并覆写。模型只加载一次。见 `backends/presence_owlv2.py`。
* `N2D_PRESENCE_CMD`（逐 probe·慢）：收 `<image_path> <object_phrase>`，stdout 输出
  JSON `{"present": true|false, "confidence": 0-1}`。
缺两者则只产 manifest（present 留空），交装好后端的环境复跑。

用法：python3 object_presence_runner.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Mapping, Optional

import production_consistency as pc

OBJECT_PRESENCE_KIND = "n2d_object_presence"


def _episode_images(root: str, ep: str) -> Dict[str, str]:
    """label → 首选图片路径（出图/<集>/图片 下，按 Clip 号归并）。"""
    out: Dict[str, str] = {}
    for pat in ("png", "jpg", "jpeg", "webp"):
        for path in glob.glob(os.path.join(root, "出图", ep, "**", f"*.{pat}"), recursive=True):
            base = os.path.basename(path)
            label = pc._clip_label({"id": base}, 0)
            out.setdefault(label, path)
    return out


def _asset_phrase(asset: Mapping[str, Any]) -> str:
    for k in ("appearance", "外观", "desc", "描述", "name", "名称", "label"):
        v = asset.get(k)
        if v:
            return str(v)
    return str(asset.get("id") or "")


def build_manifest(root: str, ep: str) -> dict:
    sb, clips = pc._storyboard(root, ep)
    prompts = pc._prompt_sections(root, ep)
    persistent = pc._persistent_assets(root)
    images = _episode_images(root, ep)
    by_loc: Dict[str, List[str]] = {}
    for aid, asset in persistent.items():
        loc = str(asset.get("location") or asset.get("loc") or asset.get("scene") or "").split("/")[0].strip()
        if loc:
            by_loc.setdefault(loc, []).append(aid)

    probes: List[dict] = []
    for idx, clip in enumerate(clips, 1):
        label = pc._clip_label(clip, idx)
        text = pc._clip_text(clip, label, prompts)
        if pc._is_exempt_view(text):
            continue
        loc = pc._loc_of(clip, text)
        expected = by_loc.get(loc, [])
        if not expected:
            continue
        probes.append({
            "shot": label,
            "loc": loc,
            "image": os.path.relpath(images[label], root) if label in images else None,
            "expected_assets": [
                {"asset": aid, "phrase": _asset_phrase(persistent[aid])} for aid in expected
            ],
        })
    return {
        "kind": OBJECT_PRESENCE_KIND,
        "root": root,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "persistent_asset_count": len(persistent),
        "probes": probes,
        "findings": [],
    }


def _run_detector(cmd: str, image_abs: str, phrase: str) -> Optional[dict]:
    try:
        proc = subprocess.run([*cmd.split(), image_abs, phrase], capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            return None
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def fill_findings(root: str, manifest: dict) -> dict:
    cmd = os.environ.get("N2D_PRESENCE_CMD", "").strip()
    if not cmd:
        return manifest
    findings: List[dict] = []
    for probe in manifest.get("probes", []):
        image = probe.get("image")
        if not image:
            continue
        image_abs = image if os.path.isabs(image) else os.path.join(root, image)
        for ea in probe.get("expected_assets", []):
            verdict = _run_detector(cmd, image_abs, ea.get("phrase") or ea.get("asset"))
            if not isinstance(verdict, dict):
                continue
            present = bool(verdict.get("present"))
            if not present:
                findings.append({
                    "shot": probe["shot"], "asset": ea["asset"],
                    "expected": True, "present": False, "severity": "block",
                    "confidence": verdict.get("confidence"),
                })
    manifest["findings"] = findings
    manifest["detector"] = cmd.split()[0]
    return manifest


def _run_batch(path: str) -> bool:
    """batch adapter：传 manifest 路径，由其就地填 findings 并覆写。模型只加载一次。"""
    cmd = os.environ.get("N2D_PRESENCE_BATCH_CMD", "").strip()
    if not cmd:
        return False
    try:
        subprocess.run([*cmd.split(), path], timeout=3600, check=True)
        return True
    except Exception as exc:
        print(f"[object_presence][warn] batch 后端调用失败（忽略，保留 manifest）：{exc}", file=sys.stderr)
        return False


def write(root: str, ep: str) -> str:
    manifest = build_manifest(root, ep)
    if not os.environ.get("N2D_PRESENCE_BATCH_CMD"):
        manifest = fill_findings(root, manifest)  # 逐 probe 路径（或无后端=manifest-only）
    path = os.path.join(root, "生产数据", f"object_presence_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _run_batch(path)  # batch 后端就地填 findings 覆写
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="O3V 视觉在场检测 manifest/runner")
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
    manifest = fill_findings(root, build_manifest(root, ns.episode))
    if ns.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"probes={len(manifest['probes'])} findings={len(manifest['findings'])} "
              f"detector={'on' if os.environ.get('N2D_PRESENCE_CMD') else 'off(manifest only)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
