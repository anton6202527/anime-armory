#!/usr/bin/env python3
"""MK1-V 辨识标记像素在场检测 runner —— 给文本档 MK1（marks_consistency）补"图里到底有没有这道疤/这对异瞳"。

文本档 MK1 查的是"标记有没有写进分镜/出图 prompt"；本 runner 进一步查"标记有没有真出现在生成的图里"。
本脚本不绑定重模型：它从 identity_registry 的 `identity_marks` + 本集出图 PNG，按"该镜在场角色 × 本集
应存在的标记（永久 / 已到获得集）"配出 probe 清单，写成可复现 manifest（schema 与 object_presence 对齐，
直接复用 `backends/presence_owlv2.py`）。配了开放词表检测器命令时逐帧判在场，把缺席项写进 `findings`，
供 `marks_consistency` 读 sidecar 合并（像素缺席降级按 warn——小标记/遮挡/侧脸像素证据噪声大，不硬 block）。

外部命令契约（二选一，batch 优先——重模型只加载一次）：
* `N2D_MARKS_PRESENCE_BATCH_CMD`（推荐）：收 `<manifest_path>`，就地把缺席项填进 `findings` 覆写。
  可直接指向 `python3 backends/presence_owlv2.py`（manifest 用 expected_assets/phrase 兼容 schema）。
* `N2D_MARKS_PRESENCE_CMD`（逐 probe·慢）：收 `<image_path> <phrase>`，stdout 出 JSON `{"present":bool,"confidence":0-1}`。
缺两者则只产 manifest（findings 空），交装好后端的环境复跑。

诚实边界：OWLv2 对"左腕旧疤"这类小标记/侧脸/遮挡检出噪声大，**缺席≠一定丢**，故消费端按 warn 处理。
检出词 `phrase` 优先用 mark 的 `detect_phrase`（英文最准），缺则退化用中文描述（更弱）。

用法：python3 marks_presence_runner.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import marks_consistency as mc

MARKS_PRESENCE_KIND = "n2d_marks_presence"


def _episode_images(root: str, ep: str) -> Dict[str, str]:
    """clip_id（EPxx_CLIPyy / 文件名 stem）→ 首选图片路径。按基名首段归并，优先非 _end/_a1 主帧。"""
    out: Dict[str, str] = {}
    for pat in ("png", "jpg", "jpeg", "webp"):
        for path in sorted(glob.glob(os.path.join(root, "出图", ep, "**", f"*.{pat}"), recursive=True)):
            stem = os.path.splitext(os.path.basename(path))[0]
            key = stem.split("_a")[0].split("_end")[0].split("_首")[0]
            # 主帧（无 _a1/_end 后缀）优先；已存在主帧不被衍生帧覆盖
            if key not in out or ("_" not in stem.removeprefix(key)):
                out.setdefault(key, path)
    return out


def _detect_phrase(mark: Mapping[str, Any]) -> str:
    return str(mark.get("detect_phrase") or "").strip() or mc._mark_desc(mark)


def build_manifest(root: str, ep: str) -> dict:
    rootp = root.rstrip("/")
    registry = mc._load_json(Path(rootp) / "出图" / "共享" / "identity_registry.json")
    char_marks = mc.collect_character_marks(registry or {})
    sb = mc._load_json(Path(rootp) / "脚本" / ep / "storyboard.json")
    clips = (sb or {}).get("clips") or (sb or {}).get("shots") or []
    prompt_md = ""
    try:
        prompt_md = (Path(rootp) / "出图" / ep / "prompt" / "01_分镜出图.md").read_text(encoding="utf-8")
    except Exception:
        pass
    sections = mc.split_prompt_sections(prompt_md)
    images = _episode_images(rootp, ep)
    ep_n = mc.episode_num(ep)

    probes: List[dict] = []
    for idx, clip in enumerate(clips):
        if not isinstance(clip, Mapping):
            continue
        clip_id = str(clip.get("id") or clip.get("label") or f"Clip{idx+1:02d}")
        corpus = mc.clip_storyboard_text(clip) + " " + mc.section_for_clip(str(clip.get("id") or ""), idx, sections)
        present = mc._present(corpus, char_marks)
        expected: List[dict] = []
        for entry in present:
            for mark in entry.get("marks") or []:
                acq = mark.get("acquired_ep")
                # 本集应存在：永久，或已到/过获得集
                exists_now = mark.get("persistence") != "acquired" or (
                    ep_n is not None and acq is not None and ep_n >= acq)
                if not exists_now:
                    continue
                expected.append({
                    "asset": mark.get("mark_id") or mc._mark_desc(mark),
                    "phrase": _detect_phrase(mark),
                    "char": entry.get("char_name"),
                })
        if not expected:
            continue
        img = images.get(clip_id)
        probes.append({
            "shot": clip_id,
            "image": os.path.relpath(img, rootp) if img else None,
            "expected_assets": expected,
        })
    return {
        "kind": MARKS_PRESENCE_KIND,
        "root": rootp,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "character_with_marks_count": len(char_marks),
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
    cmd = os.environ.get("N2D_MARKS_PRESENCE_CMD", "").strip()
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
            if not bool(verdict.get("present")):
                findings.append({
                    "shot": probe["shot"], "asset": ea["asset"], "char": ea.get("char"),
                    "expected": True, "present": False, "confidence": verdict.get("confidence"),
                    "message": f"检测器未在帧中检出「{ea.get('phrase')}」",
                })
    manifest["findings"] = findings
    manifest["detector"] = cmd.split()[0]
    return manifest


def _run_batch(path: str) -> bool:
    cmd = os.environ.get("N2D_MARKS_PRESENCE_BATCH_CMD", "").strip()
    if not cmd:
        return False
    try:
        subprocess.run([*cmd.split(), path], timeout=3600, check=True)
        return True
    except Exception as exc:
        print(f"[marks_presence][warn] batch 后端调用失败（忽略，保留 manifest）：{exc}", file=sys.stderr)
        return False


def write(root: str, ep: str) -> str:
    manifest = build_manifest(root, ep)
    if not os.environ.get("N2D_MARKS_PRESENCE_BATCH_CMD"):
        manifest = fill_findings(root, manifest)
    path = os.path.join(root.rstrip("/"), "生产数据", f"marks_presence_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _run_batch(path)
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="MK1-V 辨识标记像素在场 manifest/runner")
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
        on = bool(os.environ.get("N2D_MARKS_PRESENCE_CMD") or os.environ.get("N2D_MARKS_PRESENCE_BATCH_CMD"))
        print(f"probes={len(manifest['probes'])} findings={len(manifest['findings'])} "
              f"detector={'on' if on else 'off(manifest only)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
