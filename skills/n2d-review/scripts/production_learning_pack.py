#!/usr/bin/env python3
"""production_learning_pack.py — n2d 交付复盘与主动学习包。

P2 目标：把人审/机审发现、包装 A/B、成片 VLM QA、生成配方缺口、series bible 补充层
汇成一个可回灌的学习侧车。它不替代 review-ui / feedback，只给后续集提供可复用的失败模式。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_production_learning_pack"
CHAR_RE = re.compile(r"\bCHAR_[A-Za-z0-9_\-\u4e00-\u9fff]+\b")
ASSET_RE = re.compile(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX)_[A-Za-z0-9_\-\u4e00-\u9fff]+\b")


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    if isinstance(value, dict):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    return str(value or "")


def storyboard(root: Path, ep: str) -> List[dict]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    clips = data.get("clips") if isinstance(data, dict) else []
    return [c for c in clips or [] if isinstance(c, dict)]


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def collect_findings(root: Path, ep: str) -> List[Dict[str, Any]]:
    prod = root / "生产数据"
    rows: List[Dict[str, Any]] = []
    patterns = [
        f"review_ui_findings_{ep}.json",
        f"gate_findings_*_{ep}.json",
        f"consistency_findings*{ep}.json",
        f"consistency_audit_{ep}.json",
    ]
    for pattern in patterns:
        for path in glob.glob(str(prod / pattern)):
            data = load_json(Path(path))
            if not isinstance(data, dict):
                continue
            raw = data.get("findings") or data.get("items") or data.get("checks") or []
            for item in raw:
                if isinstance(item, Mapping):
                    rows.append({
                        "source": os.path.relpath(path, root),
                        "severity": item.get("sev") or item.get("severity") or item.get("level") or "info",
                        "dimension": item.get("dim") or item.get("dimension") or item.get("category") or item.get("code") or "unknown",
                        "message": item.get("msg") or item.get("message") or item.get("reason") or "",
                        "clip": item.get("clip") or item.get("loc") or item.get("path"),
                    })
    return rows


def active_learning(findings: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_dim: Dict[str, Dict[str, Any]] = {}
    for item in findings:
        dim = str(item.get("dimension") or "unknown")
        row = by_dim.setdefault(dim, {"dimension": dim, "count": 0, "severities": {}, "examples": []})
        row["count"] += 1
        sev = str(item.get("severity") or "info")
        row["severities"][sev] = row["severities"].get(sev, 0) + 1
        if len(row["examples"]) < 3:
            row["examples"].append({"clip": item.get("clip"), "message": item.get("message")})
    patterns = sorted(by_dim.values(), key=lambda r: r["count"], reverse=True)
    return {
        "patterns": patterns,
        "next_prompt_rules": [
            f"{p['dimension']} 出现 {p['count']} 次：下集 prompt/gate 优先补该维度的负向约束、参考资产或 motion control。"
            for p in patterns[:8]
        ],
    }


def packaging_ab_plan(root: Path, ep: str, clips: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    keyshots = load_json(root / "生产数据" / f"keyshot_candidate_plan_{ep}.json")
    key_rows = keyshots.get("keyshots") if isinstance(keyshots, dict) else []
    opening = clip_id(clips[0], 1) if clips else ""
    cover_candidates = []
    for row in key_rows or []:
        if isinstance(row, Mapping) and ("cover" in (row.get("tags") or []) or "opening" in (row.get("tags") or [])):
            cover_candidates.append(row.get("clip"))
    if not cover_candidates and opening:
        cover_candidates.append(opening)
    variants = []
    for i, mode in enumerate(("冲突脸", "危险反差", "身份秘密", "爽点动作"), 1):
        variants.append({
            "variant_id": f"COVER_{i:02d}",
            "mode": mode,
            "source_clip": cover_candidates[(i - 1) % len(cover_candidates)] if cover_candidates else "",
            "output_path": f"封面/{ep}/cover_{i:02d}.png",
            "title_card_path": f"封面/{ep}/title_card_{i:02d}.png",
            "metrics": ["ctr", "retention_3s", "follow_next_rate"],
        })
    return {
        "kind": "n2d_packaging_ab_plan",
        "episode": ep,
        "variants": variants,
        "manifest_path": f"生产数据/packaging_ab_{ep}.json",
        "policy": "封面/标题卡与正片共享角色和风格真值；投放数据回灌到 n2d-feedback。",
    }


def vlm_qa_plan(root: Path, ep: str, clips: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    questions = []
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        blob = flatten(clip)
        chars = list(dict.fromkeys(clip.get("character_ids") or CHAR_RE.findall(blob)))
        assets = list(dict.fromkeys(ASSET_RE.findall(blob)))
        questions.append({
            "clip": cid,
            "questions": [
                f"画面中是否出现了这些角色：{'、'.join(chars) or '无明确角色'}？是否串脸/换装？",
                f"这些资产是否保持：{'、'.join(assets) or '无明确资产'}？",
                "动作因果是否可读，上一镜到本镜是否接得上？",
                "本镜是否兑现 storyboard 的剧情意图和情绪？",
            ],
            "expected_report": f"生产数据/video_vlm_qa/{ep}_{cid}.json",
        })
    return {
        "kind": "n2d_finished_video_vlm_qa_plan",
        "episode": ep,
        "clip_questions": questions,
        "runner_hint": "配置 N2D_VIDEO_VLM_CMD 后逐 clip 抽帧回答；缺后端时保留人审问题清单。",
    }


def recipe_ledger(root: Path, ep: str) -> Dict[str, Any]:
    events = []
    for pattern in ("dashboard*.json", "*events*.json", f"*recipe*{ep}.json", f"image_qc/{ep}/image_qc_{ep}.json"):
        for path in glob.glob(str(root / "生产数据" / pattern)):
            data = load_json(Path(path))
            if isinstance(data, dict):
                events.append({"path": os.path.relpath(path, root), "keys": sorted(data.keys())[:20]})
    required = {"recipe_hash", "prompt_sha256", "reference_bundle_sha256", "backend_version", "actual_image_inputs"}
    missing_by_path = []
    for event in events:
        keys = set(event.get("keys") or [])
        missing = sorted(required - keys)
        if missing:
            missing_by_path.append({"path": event["path"], "missing_top_level_or_meta": missing})
    return {
        "kind": "n2d_recipe_reproducibility_ledger",
        "episode": ep,
        "events_seen": events,
        "missing": missing_by_path,
        "policy": "最终媒体必须可追溯 model/backend/prompt/reference/seed/重试记录；缺项先补 dashboard 事件或 sidecar。",
    }


def series_bible_supplement(root: Path, ep: str) -> Dict[str, Any]:
    bible = load_json(root / "设定库" / "series_bible.json")
    sources = bible.get("truth_sources") if isinstance(bible, dict) and isinstance(bible.get("truth_sources"), Mapping) else {}
    wanted = [
        "leitmotif_registry", "ambient_map", "ui_asset_registry", "translation_glossary",
        "series_packaging", "location_spatial_memory", "scene_floorplan",
    ]
    return {
        "kind": "n2d_series_bible_supplement",
        "episode": ep,
        "series_bible": "设定库/series_bible.json" if isinstance(bible, dict) else "",
        "missing_truth_layers": [key for key in wanted if not sources.get(key)],
        "recommended_next_layers": [
            "把 packaging_ab_plan 写回 series_packaging",
            "把 review learning top patterns 写回导演节奏/series_bible",
            "把 recipe_ledger 缺口写回生产配方规范",
        ],
    }


def build_pack(root: Path, ep: str) -> Dict[str, Any]:
    ep = ep_label(ep)
    clips = storyboard(root, ep)
    findings = collect_findings(root, ep)
    learning = active_learning(findings)
    packaging = packaging_ab_plan(root, ep, clips)
    vlm = vlm_qa_plan(root, ep, clips)
    recipes = recipe_ledger(root, ep)
    supplement = series_bible_supplement(root, ep)
    return {
        "kind": KIND,
        "version": 1,
        "episode": ep,
        "summary": {
            "findings": len(findings),
            "learning_patterns": len(learning.get("patterns") or []),
            "packaging_variants": len(packaging.get("variants") or []),
            "vlm_clip_questions": len(vlm.get("clip_questions") or []),
            "recipe_sources": len(recipes.get("events_seen") or []),
        },
        "active_learning": learning,
        "packaging_ab_plan": packaging,
        "finished_video_vlm_qa": vlm,
        "recipe_ledger": recipes,
        "series_bible_supplement": supplement,
        "notes": ["P2 复盘侧车；不阻断交付，但应回灌下一集 prompt、包装和路由。"],
    }


def render_md(pack: Mapping[str, Any]) -> str:
    s = pack.get("summary") or {}
    lines = [
        "# 生产复盘学习包",
        "",
        f"- episode: {pack.get('episode')}",
        f"- findings: {s.get('findings')}",
        f"- learning_patterns: {s.get('learning_patterns')}",
        f"- packaging_variants: {s.get('packaging_variants')}",
        f"- vlm_clip_questions: {s.get('vlm_clip_questions')}",
        "",
        "## Active Learning",
        "",
        "| Dimension | Count | Examples |",
        "|---|---:|---|",
    ]
    for row in (pack.get("active_learning") or {}).get("patterns") or []:
        examples = "；".join(str(e.get("message") or "")[:80] for e in row.get("examples") or [])
        lines.append(f"| {row.get('dimension')} | {row.get('count')} | {examples or '-'} |")
    lines += ["", "## Packaging A/B", "", "| Variant | Mode | Source Clip |", "|---|---|---|"]
    for row in (pack.get("packaging_ab_plan") or {}).get("variants") or []:
        lines.append(f"| {row.get('variant_id')} | {row.get('mode')} | {row.get('source_clip')} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, pack: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    jp = out / f"production_learning_pack_{ep}.json"
    mp = out / f"production_learning_pack_{ep}.md"
    write_atomic(jp, json.dumps(pack, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(mp, render_md(pack))
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="n2d 生产复盘学习包")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ep_label(ns.episode)
    pack = build_pack(root, ep)
    if ns.write:
        jp, mp = write_outputs(root, ep, pack)
        pack["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(pack, ensure_ascii=False, indent=2))
    else:
        print(render_md(pack))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
