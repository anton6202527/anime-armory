#!/usr/bin/env python3
"""VAP 外观判官（VLM-Appearance）runner —— 补 ArcFace 在 insightface 降级时的盲区。

ArcFace(insightface) 测的是身份 embedding 相似度；它在无库 / 侧背脸 / 风格化时降级。VLM-Appearance
是 2026 评测里与 ArcFace 互补的一类指标：让多模态模型直接判"两张图里同一角色外观（脸型/发饰/服装/气质）
像不像同一个人"。本 runner 为每个角色配出 (定妆参考帧, 本集出场帧) 对，写成可复现 manifest；若配置了 VLM
命令（env `N2D_VLM_CMD` 或 `N2D_APPEARANCE_CMD`），逐对调它判相似度/verdict，填进 `findings`，供
`extended_consistency.check_appearance_judge`（VAP）消费。

外部命令契约（二选一，batch 优先——VLM 只加载一次）：
* `N2D_APPEARANCE_BATCH_CMD`（推荐）：收 `<manifest_path>`，就地把判定写进该文件 `findings` 并覆写。
  见 `backends/appearance_mlxvlm.py`。未显式设置时，若本机有 `n2dvlm` conda 环境且该后端存在，会自动接上。
* `N2D_APPEARANCE_CMD` / `N2D_VLM_CMD`（逐对·慢）：收 `<reference_image> <shot_image> <character_id>`，
  stdout 输出 JSON `{"similarity": 0-1, "verdict": "ok|warn|block", "message": "..."}`。
显式设置 `N2D_APPEARANCE_BATCH_CMD=off` 可关闭自动后端。缺命令则只产 manifest（不臆造分），交装好 VLM 的环境复跑。

用法：python3 appearance_judge_runner.py <作品根> 第N集 [--write] [--json]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Mapping, Optional

import production_consistency as pc

APPEARANCE_JUDGE_KIND = "n2d_appearance_judge"
SIM_WARN_FLOOR = float(os.environ.get("N2D_APPEARANCE_WARN_FLOOR", "0.7"))
SIM_BLOCK_FLOOR = float(os.environ.get("N2D_APPEARANCE_BLOCK_FLOOR", "0.5"))


def _n2dvlm_env_exists() -> bool:
    """本机是否有 n2dvlm conda 环境；只探路径，避免 runner 无故调用 conda。"""
    bases = []
    cp = os.environ.get("CONDA_PREFIX")
    if cp:
        bases += [cp, os.path.dirname(os.path.dirname(cp))]
    bases += [
        "/opt/homebrew/Caskroom/miniforge/base",
        os.path.expanduser("~/miniforge3"),
        os.path.expanduser("~/miniconda3"),
        os.path.expanduser("~/anaconda3"),
    ]
    return any(b and os.path.isdir(os.path.join(b, "envs", "n2dvlm")) for b in bases)


def _auto_appearance_batch_cmd() -> str:
    """本机默认 VAP 后端：appearance_mlxvlm.py + n2dvlm 环境都在时自动接上。"""
    adapter = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "backends", "appearance_mlxvlm.py"))
    if os.path.isfile(adapter) and _n2dvlm_env_exists():
        return f"conda run -n n2dvlm python {shlex.quote(adapter)}"
    return ""


def _appearance_batch_cmd() -> str:
    """显式 N2D_APPEARANCE_BATCH_CMD 优先；未设时尝试本机 mlx-vlm 默认。"""
    cmd = os.environ.get("N2D_APPEARANCE_BATCH_CMD", "").strip()
    if cmd.lower() in ("off", "none", "disabled", "0"):
        return ""
    return cmd or _auto_appearance_batch_cmd()


def _identity_registry(root: str) -> dict:
    for rel in (os.path.join("出图", "共享", "identity_registry.json"),
                os.path.join("出图", "common", "identity_registry.json")):
        data = pc._load_json(os.path.join(root, rel))
        if isinstance(data, dict):
            return data
    return {}


def _char_reference(root: str, entry: Mapping[str, Any]) -> Optional[str]:
    """角色定妆参考帧：reference_group 里的正面/face_anchor，或 reference_atlas 首图。"""
    for key in ("reference_group", "reference_atlas"):
        grp = entry.get(key)
        if isinstance(grp, dict):
            for sub in ("face_anchor", "正", "front", "base_views", "face_anchor_refs"):
                v = grp.get(sub)
                if isinstance(v, str) and v:
                    return v
                if isinstance(v, list) and v and isinstance(v[0], str):
                    return v[0]
                if isinstance(v, dict):
                    for vv in v.values():
                        if isinstance(vv, str) and vv:
                            return vv
    ref = entry.get("reference_png") or entry.get("reference")
    return ref if isinstance(ref, str) else None


def _episode_images(root: str, ep: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for pat in ("png", "jpg", "jpeg", "webp"):
        for path in glob.glob(os.path.join(root, "出图", ep, "**", f"*.{pat}"), recursive=True):
            label = pc._clip_label({"id": os.path.basename(path)}, 0)
            out.setdefault(label, path)
    return out


def build_manifest(root: str, ep: str) -> dict:
    reg = _identity_registry(root)
    chars = reg.get("characters") or reg.get("identities") or {}
    char_items = list(chars.items()) if isinstance(chars, dict) else [
        (str(c.get("id") or i), c) for i, c in enumerate(chars) if isinstance(c, dict)]
    images = _episode_images(root, ep)
    prompts = pc._prompt_sections(root, ep)
    sb, clips = pc._storyboard(root, ep)

    # 每角色本集出场镜头
    shots_by_char: Dict[str, List[str]] = {}
    for idx, clip in enumerate(clips, 1):
        label = pc._clip_label(clip, idx)
        text = pc._clip_text(clip, label, prompts)
        for cid in pc._char_ids(text):
            shots_by_char.setdefault(cid, []).append(label)

    pairs: List[dict] = []
    for cid, entry in char_items:
        if not isinstance(entry, dict):
            continue
        ref = _char_reference(root, entry)
        for label in shots_by_char.get(str(cid), []):
            if label in images:
                pairs.append({
                    "character": str(cid),
                    "shot": label,
                    "reference": ref,
                    "shot_image": os.path.relpath(images[label], root),
                })
    return {
        "kind": APPEARANCE_JUDGE_KIND,
        "root": root,
        "episode": ep,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "pairs": pairs,
        "findings": [],
    }


def _run_judge(cmd: str, ref_abs: str, shot_abs: str, cid: str) -> Optional[dict]:
    try:
        proc = subprocess.run([*cmd.split(), ref_abs, shot_abs, cid],
                              capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            return None
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return None


def fill_findings(root: str, manifest: dict) -> dict:
    cmd = (os.environ.get("N2D_APPEARANCE_CMD") or os.environ.get("N2D_VLM_CMD") or "").strip()
    if not cmd:
        return manifest
    findings: List[dict] = []
    for pair in manifest.get("pairs", []):
        ref, shot_img = pair.get("reference"), pair.get("shot_image")
        if not ref or not shot_img:
            continue
        ref_abs = ref if os.path.isabs(ref) else os.path.join(root, ref)
        shot_abs = shot_img if os.path.isabs(shot_img) else os.path.join(root, shot_img)
        res = _run_judge(cmd, ref_abs, shot_abs, pair["character"])
        if not isinstance(res, dict):
            continue
        verdict = str(res.get("verdict") or "").lower()
        sim = res.get("similarity")
        if verdict not in ("ok", "warn", "block") and isinstance(sim, (int, float)):
            verdict = "block" if sim < SIM_BLOCK_FLOOR else "warn" if sim < SIM_WARN_FLOOR else "ok"
        if verdict in ("warn", "block"):
            findings.append({
                "shot": pair["shot"], "character": pair["character"],
                "verdict": verdict, "similarity": sim,
                "message": res.get("message") or "外观判官判定与定妆不一致",
            })
    manifest["findings"] = findings
    manifest["judge"] = cmd.split()[0]
    return manifest


def _run_batch(path: str, cmd: str) -> bool:
    if not cmd:
        return False
    try:
        subprocess.run([*shlex.split(cmd), path], timeout=7200, check=True)
        return True
    except Exception as exc:
        print(f"[appearance_judge][warn] batch 后端调用失败（忽略，保留 manifest）：{exc}", file=sys.stderr)
        return False


def write(root: str, ep: str) -> str:
    manifest = build_manifest(root, ep)
    batch_cmd = _appearance_batch_cmd()
    if not batch_cmd:
        manifest = fill_findings(root, manifest)
    path = os.path.join(root, "生产数据", f"appearance_judge_{ep}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    _run_batch(path, batch_cmd)
    return path


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="VAP 外观判官（VLM-Appearance）manifest/runner")
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
        on = bool(os.environ.get("N2D_APPEARANCE_CMD") or os.environ.get("N2D_VLM_CMD"))
        print(f"pairs={len(manifest['pairs'])} findings={len(manifest['findings'])} "
              f"judge={'on' if on else 'off(manifest only)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
