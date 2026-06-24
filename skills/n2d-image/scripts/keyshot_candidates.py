#!/usr/bin/env python3
"""keyshot_candidates.py — 关键镜多候选选优计划。

高质量短剧不该让封面、开场钩、反转、爽点、多人同框、强情绪近景只抽一张就进流水线。
本脚本识别关键镜，生成候选数量、评选维度和预期落档路径；若候选 sidecar 已存在，也能给出简单排序。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_keyshot_candidate_plan"
KEY_RE = re.compile(r"(🔑|封面|首图|开场|冷开场|钩子|🪝|⚡|💥|爽点|反转|真相|觉醒|系统|升级)")
MULTI_RE = re.compile(r"(多人|同框|CHAR_[A-Za-z0-9_]+.*CHAR_[A-Za-z0-9_]+)")
CLOSE_RE = re.compile(r"(CU|ECU|MCU|近景|特写|反打|表情)")
ACTION_RE = re.compile(r"(打斗|追逐|法术|飞行|爆炸|御剑|冲刺|受击)")


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    return str(value or "")


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def storyboard(root: Path, ep: str) -> List[dict]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    clips = data.get("clips") if isinstance(data, dict) else []
    return [c for c in clips or [] if isinstance(c, dict)]


def candidate_count(tags: Sequence[str]) -> int:
    if "cover" in tags or "opening" in tags:
        return 6
    if "multi_subject" in tags:
        return 5
    if "action" in tags or "strong_emotion" in tags:
        return 4
    return 3


def classify(clip: Mapping[str, Any], idx: int) -> List[str]:
    blob = flatten(clip)
    tags: List[str] = []
    if idx == 1 or "冷开场" in blob or "开场" in blob:
        tags.append("opening")
    if "封面" in blob or "首图" in blob:
        tags.append("cover")
    if KEY_RE.search(blob):
        tags.append("hook_or_payoff")
    if MULTI_RE.search(blob):
        tags.append("multi_subject")
    if CLOSE_RE.search(blob):
        tags.append("strong_emotion")
    if ACTION_RE.search(blob):
        tags.append("action")
    return list(dict.fromkeys(tags))


def selection_criteria(tags: Sequence[str]) -> List[str]:
    base = ["角色 DNA 一致", "构图一眼读懂", "光位/色调继承本集契约", "无文字/手/脸明显硬伤"]
    if "opening" in tags:
        base.append("0-3 秒钩子强，第一眼能理解冲突")
    if "cover" in tags:
        base.append("点击动机强：人脸/冲突/反差/危险至少一项非常清楚")
    if "multi_subject" in tags:
        base.append("多人槽位不串脸，左右/前后关系清楚")
    if "action" in tags:
        base.append("动作方向、发力点、命中帧可读")
    if "strong_emotion" in tags:
        base.append("表情贴脚本情绪，脸型不因表情被重画")
    return base


def score_existing_candidates(root: Path, ep: str, clip: str) -> List[Dict[str, Any]]:
    base = root / "出图" / ep / "候选" / clip
    rows = []
    for path in sorted(glob.glob(str(base / "*.json"))):
        data = load_json(Path(path))
        if not isinstance(data, dict):
            continue
        score = 0.0
        for key in ("face_consistency", "composition", "hook_strength", "style_match", "asset_consistency"):
            try:
                score += float(data.get(key) or 0)
            except Exception:
                pass
        rows.append({"sidecar": os.path.relpath(path, root), "score": round(score, 3), "candidate": data.get("candidate") or Path(path).stem})
    return sorted(rows, key=lambda x: x["score"], reverse=True)


def build_plan(root: Path, ep: str) -> Dict[str, Any]:
    clips = storyboard(root, ep)
    keyshots: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        tags = classify(clip, idx)
        if not tags:
            continue
        cid = clip_id(clip, idx)
        n = candidate_count(tags)
        keyshots.append({
            "clip": cid,
            "tags": tags,
            "candidate_count": n,
            "candidate_dir": f"出图/{ep}/候选/{cid}/",
            "expected_candidates": [f"出图/{ep}/候选/{cid}/candidate_{i:02d}.png" for i in range(1, n + 1)],
            "selection_manifest": f"出图/{ep}/候选/{cid}/selection.json",
            "selection_criteria": selection_criteria(tags),
            "existing_scores": score_existing_candidates(root, ep, cid),
        })
    return {
        "kind": KIND,
        "episode": ep,
        "clip_count": len(clips),
        "keyshots": keyshots,
        "summary": {
            "keyshot_count": len(keyshots),
            "planned_candidates": sum(k["candidate_count"] for k in keyshots),
        },
        "notes": ["只生成候选/选优计划；真正生图仍由 n2d-image runner 执行，selection.json 记录最终入正片的候选。"],
    }


def render_md(plan: Mapping[str, Any]) -> str:
    s = plan.get("summary") or {}
    lines = [
        "# 关键镜多候选选优计划",
        "",
        f"- episode: {plan.get('episode')}",
        f"- keyshots: {s.get('keyshot_count')} ｜ planned_candidates: {s.get('planned_candidates')}",
        "",
        "| Clip | Tags | N | Candidate Dir | Criteria | Existing Best |",
        "|---|---|---:|---|---|---|",
    ]
    for k in plan.get("keyshots") or []:
        best = (k.get("existing_scores") or [{}])[0]
        best_txt = f"{best.get('candidate')}({best.get('score')})" if best.get("candidate") else "-"
        lines.append(
            f"| {k.get('clip')} | {'、'.join(k.get('tags') or [])} | {k.get('candidate_count')} | "
            f"{k.get('candidate_dir')} | {'；'.join(k.get('selection_criteria') or [])} | {best_txt} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, plan: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    out.mkdir(parents=True, exist_ok=True)
    jp = out / f"keyshot_candidate_plan_{ep}.json"
    mp = out / f"keyshot_candidate_plan_{ep}.md"
    tmp = jp.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, jp)
    tmp_md = mp.with_suffix(".md.tmp")
    tmp_md.write_text(render_md(plan), encoding="utf-8")
    os.replace(tmp_md, mp)
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 关键镜多候选选优计划")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ns.episode if ns.episode.startswith("第") else f"第{ns.episode}集"
    plan = build_plan(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, plan)
        plan["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(render_md(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
