#!/usr/bin/env python3
"""同场景 batch-as-video-frames 规划（P2b·默认路径·DreamShot 思路）。

**为什么**：同一场景的一组连续分镜，与其各自独立出首帧再焊接，不如**利用视频生成模型固有的时空一致性，
把它们当作同一段隐视频的若干帧一次性生成**（2026 DreamShot storyboard synthesis / Collaborative Video
Diffusion / Ouroboros tail-latent）——同场景内角色/光照/风格天然不漂，是「同场景多镜漂移」的结构性解。

本规划器把 storyboard 里**连续同场景（同 LOC）≥2 镜**默认编成一个 `scene_coherent_batch` 作业：
共享同一场景定妆/光位锚/风格契约 + 同源种子，按一段连贯场景 pass 出这组首帧，再拆回逐镜。**默认开启**
（选择点 `同场景批量出图`=默认开），可关；关闭或单组 <2 镜则回退逐镜独立出图。

铁律：batch 只锁「场景/光/风格」一致性，**不锁人物身份**（身份仍走 identity_registry 两层定妆库 + 多人同框
空间槽位绑定）；跨场景切换（LOC 变）必断组——不同地点不该被时空一致性"焊"在一起。

纯函数（场景键/连续分组/是否成组/作业构造）无依赖、带 pytest；I/O 仅读 storyboard、写 plan。

用法：
  python3 scene_batch.py <作品根> 第N集            # 规划（默认 report-only，写 scene_batch_plan.json）
  python3 scene_batch.py <作品根> 第N集 --json
  python3 scene_batch.py <作品根> 第N集 --min-group 3   # 只把 ≥3 连续同场景镜成组
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

LOC_RE = re.compile(r"LOC_[A-Za-z0-9_]+")
DEFAULT_MIN_GROUP = 2


# ── 纯函数（无依赖·可测） ──────────────────────────────────────────────────────

def clip_scene_key(clip: Mapping[str, Any]) -> str:
    """clip 的场景标识：优先显式 LOC id（loc/location 字段或文本里的 LOC_xx），否则归一化 scene 串。
    取不到 → ""（不可成组）。纯函数·可测。"""
    for k in ("loc", "location", "scene_id", "loc_id"):
        v = str(clip.get(k) or "").strip()
        if v:
            return v.upper() if v.upper().startswith("LOC") else v
    cont = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
    blob = " ".join(str(clip.get(f) or "") for f in ("label", "scene")) + " " + \
        " ".join(str(cont.get(f) or "") for f in ("scene", "location", "loc"))
    m = LOC_RE.search(blob)
    if m:
        return m.group(0).upper()
    scene = str(clip.get("scene") or "").strip()
    return re.sub(r"\s+", "", scene)


def clip_id_of(clip: Mapping[str, Any], index: int) -> str:
    raw = str(clip.get("id") or clip.get("clip_id") or clip.get("label") or "").strip()
    m = re.search(r"(?i)clip[_\s-]*0*(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m2 = re.search(r"(\d+)", raw)
    return f"Clip_{int(m2.group(1)):02d}" if m2 else f"Clip_{index:02d}"


def group_consecutive_by_scene(clips: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """把 clips 按**连续**相同 scene_key 分组（跨场景切换断组）。纯函数·可测。

    返回 [{scene_key, members:[{clip_id, index, firstframe_png}]}]，保留原顺序。空 scene_key 各自独立成组
    （不可成组，下游 should_batch 会按 size 过滤）。"""
    groups: List[Dict[str, Any]] = []
    for i, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        key = clip_scene_key(clip)
        member = {"clip_id": clip_id_of(clip, i), "index": i,
                  "firstframe_png": str(clip.get("firstframe_png") or "")}
        if groups and groups[-1]["scene_key"] and groups[-1]["scene_key"] == key:
            groups[-1]["members"].append(member)
        else:
            groups.append({"scene_key": key, "members": [member]})
    return groups


def should_batch(group: Mapping[str, Any], min_group: int = DEFAULT_MIN_GROUP) -> bool:
    """该组是否值得 batch：有非空 scene_key 且成员数 ≥ min_group。纯函数·可测。"""
    return bool(group.get("scene_key")) and len(group.get("members") or []) >= min_group


def build_batch_job(group: Mapping[str, Any], scene_name: str = "") -> Dict[str, Any]:
    """单个 scene_coherent_batch 作业（纯字典构造·可测）。"""
    members = list(group.get("members") or [])
    return {
        "scene_key": group.get("scene_key"),
        "scene_name": scene_name or str(group.get("scene_key") or ""),
        "mode": "scene_coherent_batch",
        "clip_ids": [m["clip_id"] for m in members],
        "firstframe_pngs": [m["firstframe_png"] for m in members if m.get("firstframe_png")],
        "size": len(members),
        "shared_locks": ["scene_dna", "场景光位锚", "style_contract", "shared_seed"],
        "note": (f"同场景连续 {len(members)} 镜走时空一致性 batch（共享场景/光位/风格+同源种子，"
                 "一段连贯场景 pass 出这组首帧再拆镜）；身份仍按 identity_registry 锁，不在此 batch 内处理。"),
    }


# ── I/O ───────────────────────────────────────────────────────────────────────

def _scene_name_map(root: str) -> Dict[str, str]:
    """LOC id → 场景名（asset_registry），用于 batch job 人读。缺/失败 → {}。"""
    try:
        data = json.load(open(os.path.join(root, "出图", "共享", "asset_registry.json"), encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, str] = {}
    for a in data.get("assets") or []:
        if isinstance(a, Mapping) and str(a.get("id") or "").upper().startswith("LOC"):
            out[str(a.get("id")).upper()] = str(a.get("name") or "").strip()
    return out


def plan_episode(root: str, ep: str, min_group: int = DEFAULT_MIN_GROUP) -> Dict[str, Any]:
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    try:
        sb = json.load(open(sb_path, encoding="utf-8"))
    except Exception:
        return {"kind": "n2d_scene_batch_plan", "episode": ep, "min_group": min_group,
                "batches": [], "solo": [], "notes": [f"缺/损坏 {sb_path}——先跑 n2d-script 分镜设计。"]}
    clips = sb.get("clips") or sb.get("shots") or []
    name_map = _scene_name_map(root)
    groups = group_consecutive_by_scene(clips)
    batches: List[Dict[str, Any]] = []
    solo: List[Dict[str, Any]] = []
    for g in groups:
        if should_batch(g, min_group):
            scene_name = name_map.get(str(g["scene_key"]).upper(), "")
            batches.append(build_batch_job(g, scene_name))
        else:
            for m in g["members"]:
                solo.append({"clip_id": m["clip_id"], "scene_key": g["scene_key"],
                             "why": "场景键为空（不可门控）" if not g["scene_key"] else "同场景连续镜不足 min_group"})
    return {"kind": "n2d_scene_batch_plan", "episode": ep, "min_group": min_group,
            "batches": batches, "solo": solo,
            "batched_clips": sum(b["size"] for b in batches),
            "notes": [] if clips else ["storyboard 无 clips。"]}


def render_md(plan: Mapping[str, Any]) -> str:
    lines = [f"# 同场景 batch-as-video-frames 规划 · {plan.get('episode')}（默认路径·P2b）", "",
             f"- min_group={plan.get('min_group')} · {len(plan.get('batches') or [])} 个 batch · "
             f"{plan.get('batched_clips', 0)} 镜成组 · {len(plan.get('solo') or [])} 镜独立出",
             "- 说明：同场景连续 ≥min_group 镜默认走时空一致性 batch（共享场景/光位/风格+同源种子）；"
             "身份仍按 identity_registry 两层定妆库锁，跨场景切换必断组。", ""]
    for b in plan.get("batches") or []:
        lines.append(f"## batch「{b.get('scene_name') or b.get('scene_key')}」× {b['size']} 镜")
        lines.append(f"- clips：{ '、'.join(b['clip_ids']) }")
        lines.append(f"- 共享锁：{ '、'.join(b['shared_locks']) }")
        lines.append(f"- {b['note']}")
        lines.append("")
    if plan.get("solo"):
        lines.append("## 独立出图（不成组）")
        for s in plan["solo"]:
            lines.append(f"- {s['clip_id']}（{s['why']}）")
    for n in plan.get("notes", []):
        lines.append(f"- note: {n}")
    return "\n".join(lines) + "\n"


def write_plan(root: str, ep: str, plan: Mapping[str, Any]) -> str:
    out_dir = os.path.join(root, "出图", ep, "control")
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, "scene_batch_plan.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    open(os.path.join(out_dir, "scene_batch_plan.md"), "w", encoding="utf-8").write(render_md(plan))
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--min-group", type=int, default=DEFAULT_MIN_GROUP,
                    help=f"连续同场景多少镜才成组（默认 {DEFAULT_MIN_GROUP}）")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = os.path.abspath(os.path.expanduser(ns.root))
    plan = plan_episode(root, ns.episode, ns.min_group)
    path = write_plan(root, ns.episode, plan)
    plan["plan_path"] = path
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(f"同场景 batch 规划（{ns.episode}）：{len(plan['batches'])} 个 batch · "
          f"{plan.get('batched_clips', 0)} 镜成组 · {len(plan['solo'])} 镜独立 → {path}")
    for b in plan["batches"]:
        print(f"  batch「{b.get('scene_name') or b['scene_key']}」× {b['size']}：{'、'.join(b['clip_ids'])}")
    for n in plan["notes"]:
        print("ℹ️ " + n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
