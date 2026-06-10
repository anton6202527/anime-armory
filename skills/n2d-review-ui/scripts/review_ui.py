#!/usr/bin/env python3
"""Build a local visual review canvas for n2d episodes."""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

_COMMON = str(Path(__file__).resolve().parent.parent.parent / "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from n2d_contract import PRODUCTION_DIR, REVIEW_UI_KIND, identity_registry_path, shared_asset_path  # noqa: E402  生产数据/身份注册路径/kind 单一真值源


KIND = REVIEW_UI_KIND
VERSION = 1


from n2d_route import normalize_episode  # noqa: E402  集号单一真值源


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def safe_ep(ep: str) -> str:
    return normalize_episode(ep)


def load_json(path: Path) -> Optional[Any]:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def production_dir(root: Path) -> Path:
    return root / PRODUCTION_DIR


def output_paths(root: Path, ep: str) -> Dict[str, Path]:
    out_dir = production_dir(root)
    return {
        "dir": out_dir,
        "json": out_dir / f"review_ui_{safe_ep(ep)}.json",
        "html": out_dir / f"review_ui_{safe_ep(ep)}.html",
    }


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def media_url(path: Path, html_dir: Path) -> str:
    rel = os.path.relpath(path, html_dir).replace(os.sep, "/")
    return quote(rel, safe="/._-()[]@+,~:%")


def resolve_path(root: Path, value: Any) -> Optional[Path]:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if path.is_absolute():
        return path
    return root / path


def asset(root: Path, html_dir: Path, value: Any, *, kind: str = "file") -> Optional[Dict[str, Any]]:
    path = resolve_path(root, value)
    if not path:
        return None
    return {
        "kind": kind,
        "path": rel_to_root(root, path),
        "exists": path.is_file(),
        "url": media_url(path, html_dir),
        "name": path.name,
    }


def clip_number(value: Any, fallback: int) -> int:
    text = str(value or "")
    match = re.search(r"(?:clip|CLIP|Clip)[_\s-]?0*(\d+)", text)
    if match:
        return int(match.group(1))
    match = re.search(r"0*(\d+)", text)
    return int(match.group(1)) if match else fallback


def first_existing_glob(patterns: Sequence[str]) -> Optional[str]:
    for pattern in patterns:
        matches = sorted(glob.glob(pattern))
        if matches:
            return matches[0]
    return None


def infer_first_frame(root: Path, ep: str, clip: Dict[str, Any], number: int) -> Optional[str]:
    direct = clip.get("firstframe_png")
    if direct:
        return str(direct)
    img_dir = root / "出图" / ep / "图片"
    found = first_existing_glob([
        str(img_dir / f"Clip{number:02d}*.png"),
        str(img_dir / f"Clip_{number:02d}*.png"),
        str(img_dir / f"镜头{number}_*.png"),
    ])
    return rel_to_root(root, Path(found)) if found else None


def infer_end_frame(root: Path, ep: str, clip: Dict[str, Any], first_frame: Optional[str], number: int) -> Optional[str]:
    continuity = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
    direct = continuity.get("endframe_png") or clip.get("endframe_png")
    if direct:
        return str(direct)
    if first_frame:
        path = resolve_path(root, first_frame)
        if path:
            candidate = path.with_name(path.stem + "_end" + path.suffix)
            if candidate.is_file():
                return rel_to_root(root, candidate)
    img_dir = root / "出图" / ep / "图片"
    found = first_existing_glob([
        str(img_dir / f"Clip{number:02d}_end.png"),
        str(img_dir / f"Clip_{number:02d}_end.png"),
        str(img_dir / f"镜头{number}_end.png"),
    ])
    return rel_to_root(root, Path(found)) if found else None


def infer_video(root: Path, ep: str, clip: Dict[str, Any], number: int) -> Optional[str]:
    direct = clip.get("video_out") or clip.get("video")
    if direct:
        return str(direct)
    video_dir = root / "出视频" / ep / "视频"
    found = first_existing_glob([
        str(video_dir / f"Clip_{number:02d}*.mp4"),
        str(video_dir / f"Clip{number:02d}*.mp4"),
        str(video_dir / f"*{number:02d}*.mp4"),
    ])
    return rel_to_root(root, Path(found)) if found else None


def storyboard_path(root: Path, ep: str) -> Path:
    return root / "脚本" / ep / "storyboard.json"


def load_storyboard(root: Path, ep: str) -> Dict[str, Any]:
    data = load_json(storyboard_path(root, ep))
    return data if isinstance(data, dict) else {}


def score_path(root: Path, ep: str) -> Path:
    return production_dir(root) / f"score_{ep}.json"


def load_score(root: Path, ep: str) -> Optional[Dict[str, Any]]:
    data = load_json(score_path(root, ep))
    return data if isinstance(data, dict) else None


def load_score_inputs(root: Path, ep: str) -> Dict[str, Any]:
    base = production_dir(root) / "score_inputs"
    out: Dict[str, Any] = {}
    for name in ("consistency", "mechanical", "visual"):
        path = base / f"{ep}_{name}.json"
        data = load_json(path)
        if data is not None:
            out[name] = data
    return out


def flatten_evidence(score: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(score, dict):
        return []
    flags: List[Dict[str, Any]] = []
    for dim in score.get("dimensions", []) or []:
        if not isinstance(dim, dict):
            continue
        status = str(dim.get("status") or "info")
        severity = "block" if status == "fail" else "warn" if status in {"warn", "insufficient_data"} else "info"
        for evidence in dim.get("evidence", []) or []:
            flags.append({
                "severity": severity,
                "dimension": dim.get("label") or dim.get("key") or "QA",
                "message": str(evidence),
                "score": dim.get("score"),
                "status": status,
            })
    return flags


def score_summary(root: Path, ep: str, score: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(score, dict):
        return {"available": False}
    return {
        "available": True,
        "total_score": score.get("total_score"),
        "status": score.get("status"),
        "threshold": score.get("threshold"),
        "dimensions": score.get("dimensions", []),
        "auto_return_tasks": score.get("auto_return_tasks", []),
        "data_collection_tasks": score.get("data_collection_tasks", []),
        "path": rel_to_root(root, score_path(root, ep)),
    }


def clip_match_needles(clip: Dict[str, Any]) -> List[str]:
    """Specific substring identifiers for a clip — full id / 够长的 label / 媒体名。
    **绝不含裸编号**（编号匹配走 `clip_number_re`，带 token + 数字边界）。"""
    needles: List[str] = []
    cid = str(clip.get("id") or "").strip().lower()
    if len(cid) >= 3:
        needles.append(cid)
    label = str(clip.get("label") or "").strip().lower()
    # 跳过「Clip N」这类自动标签：与编号匹配重复，且 "clip 1" 会子串命中 "clip 10"
    if len(label) >= 4 and not re.fullmatch(r"clip\s*0*\d+", label):
        needles.append(label)
    for key in ("first_frame", "end_frame", "video"):
        media = clip.get(key) if isinstance(clip.get(key), dict) else None
        if isinstance(media, dict):
            for field in ("name", "path"):
                value = str(media.get(field) or "").strip().lower()
                if len(value) >= 5:
                    needles.append(value)
    seen: set = set()
    out: List[str] = []
    for needle in needles:
        if needle and needle not in seen:
            seen.add(needle)
            out.append(needle)
    return out


def clip_number_re(clip: Dict[str, Any]):
    """带 clip/镜头 token + 数字边界的编号匹配。

    历史 bug：裸 clip 号当子串会命中任意数字（集号/计数/metrics），整列全红=假阳性。
    且 "clip#1" 是 "clip#10" 的子串——所以必须用负向前瞻 `(?!\\d)` 卡数字边界、`0*` 容忍补零，
    让 Clip 1 只命中 clip#1/clip 1/镜头1，不再误吞 clip#10..19。"""
    try:
        n = int(clip.get("number"))
    except (TypeError, ValueError):
        return None
    return re.compile(r"(?:clip[#_\-]?\s?|镜头\s?)0*%d(?!\d)" % n, re.IGNORECASE)


def flag_matches_clip(flag: Dict[str, Any], clip: Dict[str, Any]) -> bool:
    message = flag.get("message") or ""
    text = message.lower()
    if any(needle in text for needle in clip_match_needles(clip)):
        return True
    rx = clip_number_re(clip)
    return bool(rx and rx.search(message))


def collect_clip_flags(flags: List[Dict[str, Any]], clip: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [flag for flag in flags if flag_matches_clip(flag, clip)]


def collect_global_flags(flags: List[Dict[str, Any]], clips: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for flag in flags:
        if not any(flag_matches_clip(flag, clip) for clip in clips):
            out.append(flag)
    return out


def collect_clips(root: Path, ep: str, html_dir: Path, storyboard: Dict[str, Any], flags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    raw = storyboard.get("clips") if isinstance(storyboard.get("clips"), list) else []
    if not raw:
        raw = fallback_clip_rows(root, ep)
    clips: List[Dict[str, Any]] = []
    for idx, clip_raw in enumerate(raw, 1):
        if not isinstance(clip_raw, dict):
            continue
        num = clip_number(clip_raw.get("id") or clip_raw.get("label"), idx)
        first = infer_first_frame(root, ep, clip_raw, num)
        end = infer_end_frame(root, ep, clip_raw, first, num)
        video = infer_video(root, ep, clip_raw, num)
        continuity = clip_raw.get("continuity") if isinstance(clip_raw.get("continuity"), dict) else {}
        clip = {
            "index": idx,
            "number": num,
            "id": clip_raw.get("id") or f"Clip_{num:02d}",
            "label": clip_raw.get("label") or f"Clip {num}",
            "duration": clip_raw.get("duration"),
            "scene": clip_raw.get("scene"),
            "rhythm": clip_raw.get("rhythm"),
            "template": clip_raw.get("template") or "none",
            "shots": clip_raw.get("shots") or [],
            "transition": continuity.get("transition"),
            "need_endframe": continuity.get("need_endframe"),
            "start_state": continuity.get("start_state"),
            "end_state": continuity.get("end_state"),
            "first_frame": asset(root, html_dir, first, kind="image"),
            "end_frame": asset(root, html_dir, end, kind="image"),
            "video": asset(root, html_dir, video, kind="video"),
        }
        clip["qa_flags"] = collect_clip_flags(flags, clip)
        clips.append(clip)
    return clips


def fallback_clip_rows(root: Path, ep: str) -> List[Dict[str, Any]]:
    img_dir = root / "出图" / ep / "图片"
    video_dir = root / "出视频" / ep / "视频"
    rows: List[Dict[str, Any]] = []
    image_paths = [
        path for path in sorted(img_dir.glob("*.png"))
        if not path.stem.endswith("_end") and not path.name.startswith(".")
    ]
    for idx, path in enumerate(image_paths, 1):
        num = clip_number(path.name, idx)
        rows.append({
            "id": f"Clip_{num:02d}",
            "label": path.stem,
            "firstframe_png": rel_to_root(root, path),
            "video_out": infer_video(root, ep, {}, num),
            "continuity": {"endframe_png": infer_end_frame(root, ep, {}, rel_to_root(root, path), num)},
        })
    if rows:
        return rows
    for idx, path in enumerate(sorted(video_dir.glob("*.mp4")), 1):
        num = clip_number(path.name, idx)
        rows.append({
            "id": f"Clip_{num:02d}",
            "label": path.stem,
            "video_out": rel_to_root(root, path),
        })
    return rows


def collect_seams(clips: List[Dict[str, Any]], flags: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seams: List[Dict[str, Any]] = []
    seam_flags = [flag for flag in flags if "接缝" in flag.get("message", "") or "seam" in flag.get("message", "").lower()]
    for idx, (prev, nxt) in enumerate(zip(clips, clips[1:]), 1):
        text = f"{prev.get('label')} {nxt.get('label')} {prev.get('transition')}"
        matched = [flag for flag in seam_flags if any(str(token).lower() in flag.get("message", "").lower() for token in (prev.get("label"), nxt.get("label"), prev.get("id"), nxt.get("id")) if token)]
        seams.append({
            "index": idx,
            "from": prev.get("label"),
            "to": nxt.get("label"),
            "transition": prev.get("transition"),
            "tail": prev.get("end_frame"),
            "next_first": nxt.get("first_frame"),
            "qa_flags": matched or ([] if seam_flags else []),
            "note": "" if matched else ("无接缝异常证据" if not seam_flags else "有接缝 flag，但未匹配到本接缝"),
            "context": text,
        })
    return seams


def registry_path(root: Path) -> Path:
    return Path(identity_registry_path(str(root)))


def collect_identity_refs(root: Path, html_dir: Path) -> List[Dict[str, Any]]:
    registry = load_json(registry_path(root))
    refs: List[Dict[str, Any]] = []
    if isinstance(registry, dict):
        for char in registry.get("characters", []) or []:
            if not isinstance(char, dict):
                continue
            for form in char.get("forms", []) or []:
                if not isinstance(form, dict):
                    continue
                group = form.get("reference_group") if isinstance(form.get("reference_group"), dict) else {}
                media = []
                for key, value in group.items():
                    if isinstance(value, str):
                        item = asset(root, html_dir, value, kind="image")
                        if item:
                            item["role"] = key
                            media.append(item)
                refs.append({
                    "character_id": char.get("id"),
                    "name": char.get("name"),
                    "form": form.get("form"),
                    "asset_key": form.get("asset_key"),
                    "anchor_phrase": form.get("anchor_phrase"),
                    "drift_forbidden": form.get("drift_forbidden", []),
                    "media": media,
                })
    if refs:
        return refs
    for path in sorted(Path(shared_asset_path(str(root), "图片")).glob("定妆*.png")):
        item = asset(root, html_dir, rel_to_root(root, path), kind="image")
        refs.append({"name": path.stem, "form": "fallback", "media": [item] if item else []})
    return refs


def build_manifest(root: Path, ep: str) -> Dict[str, Any]:
    ep = normalize_episode(ep)
    paths = output_paths(root, ep)
    html_dir = paths["dir"]
    storyboard = load_storyboard(root, ep)
    score = load_score(root, ep)
    score_inputs = load_score_inputs(root, ep)
    flags = flatten_evidence(score)
    clips = collect_clips(root, ep, html_dir, storyboard, flags)
    return {
        "kind": KIND,
        "version": VERSION,
        "root": str(root),
        "episode": ep,
        "generated_at": now_iso(),
        "source": {
            "storyboard": rel_to_root(root, storyboard_path(root, ep)),
            "score": rel_to_root(root, score_path(root, ep)),
            "identity_registry": rel_to_root(root, registry_path(root)),
        },
        "storyboard": {
            "title": storyboard.get("title"),
            "total_duration": storyboard.get("total_duration"),
            "timing_source": storyboard.get("timing_source"),
            "available": bool(storyboard),
        },
        "score": score_summary(root, ep, score),
        "score_inputs": score_inputs,
        "clips": clips,
        "seams": collect_seams(clips, flags),
        "identity_refs": collect_identity_refs(root, html_dir),
        "global_flags": collect_global_flags(flags, clips),
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{
  --bg:#f7f8fb; --ink:#172033; --muted:#657085; --line:#d8dee9; --panel:#ffffff;
  --red:#c7372f; --amber:#b7791f; --green:#2f855a; --blue:#2563eb; --violet:#6d5bd0;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background:var(--bg); color:var(--ink); letter-spacing:0; overflow:hidden; }}
button, select, input {{ font:inherit; }}
.topbar {{ position:fixed; inset:0 0 auto 0; height:64px; display:flex; align-items:center; gap:12px; padding:10px 16px; background:rgba(255,255,255,.94); border-bottom:1px solid var(--line); z-index:10; }}
.title {{ min-width:280px; max-width:520px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
.title strong {{ display:block; font-size:15px; }}
.title span {{ display:block; color:var(--muted); font-size:12px; margin-top:2px; }}
.toolbar {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; }}
.iconbtn {{ width:34px; height:34px; border:1px solid var(--line); background:#fff; color:var(--ink); border-radius:8px; cursor:pointer; }}
.control {{ height:34px; border:1px solid var(--line); background:#fff; border-radius:8px; padding:0 10px; min-width:132px; }}
.search {{ width:220px; }}
.viewport {{ position:fixed; inset:64px 0 0 0; overflow:hidden; background:
  linear-gradient(#e8edf5 1px, transparent 1px),
  linear-gradient(90deg, #e8edf5 1px, transparent 1px);
  background-size:40px 40px; cursor:grab;
}}
.canvas {{ position:absolute; left:0; top:0; width:5200px; min-height:2400px; transform-origin:0 0; }}
.lane {{ position:absolute; left:24px; right:24px; height:1px; border-top:1px dashed #c7d0df; }}
.lane-label {{ position:absolute; left:36px; padding:2px 8px; border:1px solid var(--line); border-radius:8px; background:#fff; color:var(--muted); font-size:12px; }}
.card {{ position:absolute; width:320px; border:1px solid var(--line); border-radius:8px; background:var(--panel); box-shadow:0 10px 22px rgba(25,35,55,.08); overflow:hidden; }}
.card.hidden {{ display:none; }}
.clip-card.focused {{ outline:3px solid var(--blue); box-shadow:0 0 0 7px rgba(37,99,235,.20); transition:box-shadow .2s; }}
.card-head {{ padding:10px 12px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; gap:8px; align-items:flex-start; }}
.card-title {{ font-weight:700; font-size:14px; line-height:1.25; overflow-wrap:anywhere; }}
.meta {{ font-size:12px; color:var(--muted); line-height:1.4; padding:8px 12px; }}
.badge {{ display:inline-flex; align-items:center; min-height:22px; padding:2px 7px; border-radius:999px; font-size:12px; border:1px solid var(--line); background:#f8fafc; color:var(--muted); white-space:nowrap; }}
.badge.block {{ color:var(--red); border-color:#f1b3ae; background:#fff1f0; }}
.badge.warn {{ color:var(--amber); border-color:#f4d39a; background:#fff8e8; }}
.badge.pass {{ color:var(--green); border-color:#9bd8b9; background:#ecfdf3; }}
.media-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:6px; padding:8px; }}
.media {{ min-height:108px; border:1px solid var(--line); border-radius:6px; overflow:hidden; background:#eef2f7; display:flex; align-items:center; justify-content:center; position:relative; }}
.media img, .media video {{ width:100%; height:100%; object-fit:cover; display:block; }}
.media video {{ min-height:120px; background:#111827; }}
.media .missing {{ padding:10px; font-size:12px; color:var(--muted); text-align:center; }}
.media-label {{ position:absolute; left:6px; top:6px; background:rgba(255,255,255,.88); border-radius:6px; padding:1px 5px; font-size:11px; color:var(--muted); }}
.flags {{ display:flex; flex-direction:column; gap:6px; padding:8px 12px 12px; }}
.flag {{ border-left:3px solid var(--line); padding:6px 8px; background:#f8fafc; border-radius:0 6px 6px 0; font-size:12px; line-height:1.35; overflow-wrap:anywhere; }}
.flag.block {{ border-left-color:var(--red); background:#fff5f5; }}
.flag.warn {{ border-left-color:var(--amber); background:#fffaf0; }}
.flag.info {{ border-left-color:var(--blue); background:#eff6ff; }}
.score-card {{ width:260px; }}
.score-num {{ font-size:44px; font-weight:800; padding:16px 14px 2px; }}
.score-dims {{ padding:8px 12px 12px; display:flex; flex-direction:column; gap:7px; }}
.dimrow {{ display:grid; grid-template-columns:1fr 42px; align-items:center; gap:8px; font-size:12px; }}
.bar {{ height:8px; background:#edf2f7; border-radius:999px; overflow:hidden; }}
.bar > span {{ display:block; height:100%; background:var(--green); }}
.bar.warn > span {{ background:var(--amber); }}
.bar.block > span {{ background:var(--red); }}
.ref-card {{ width:280px; }}
.ref-strip {{ display:flex; gap:6px; padding:8px; overflow-x:auto; }}
.ref-img {{ width:82px; height:110px; flex:0 0 auto; border:1px solid var(--line); border-radius:6px; overflow:hidden; background:#eef2f7; position:relative; }}
.ref-img img {{ width:100%; height:100%; object-fit:cover; }}
.seam-card {{ width:250px; border-style:dashed; }}
.seam-media {{ display:grid; grid-template-columns:1fr 1fr; gap:5px; padding:8px; }}
.mini {{ height:86px; border:1px solid var(--line); border-radius:6px; overflow:hidden; background:#eef2f7; display:flex; align-items:center; justify-content:center; }}
.mini img {{ width:100%; height:100%; object-fit:cover; }}
.empty {{ color:var(--muted); font-size:12px; padding:12px; }}
.help {{ position:fixed; right:12px; bottom:12px; padding:8px 10px; border:1px solid var(--line); border-radius:8px; background:rgba(255,255,255,.92); color:var(--muted); font-size:12px; z-index:11; }}
</style>
</head>
<body>
<div class="topbar">
  <div class="title"><strong id="titleText"></strong><span id="subtitleText"></span></div>
  <div class="toolbar">
    <button class="iconbtn" id="zoomOut" title="缩小">−</button>
    <button class="iconbtn" id="zoomIn" title="放大">+</button>
    <button class="iconbtn" id="resetView" title="重置视图">⌂</button>
    <select class="control" id="severityFilter" title="按 QA 严重度筛选">
      <option value="all">全部 QA</option><option value="block">只看 block</option><option value="warn">只看 warn+</option><option value="missing">只看缺素材</option>
    </select>
    <input class="control search" id="searchBox" placeholder="搜索 Clip / 场景 / flag">
  </div>
</div>
<div class="viewport" id="viewport"><div class="canvas" id="canvas"></div></div>
<div class="help">拖拽平移 · 滚轮缩放 · 空格重置</div>
<script id="manifest" type="application/json">{manifest_json}</script>
<script>
const data = JSON.parse(document.getElementById('manifest').textContent);
const canvas = document.getElementById('canvas');
const viewport = document.getElementById('viewport');
let scale = 0.86, offsetX = 12, offsetY = 8, dragging = false, sx = 0, sy = 0, ox = 0, oy = 0;
function esc(s) {{ return String(s ?? '').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}
function applyTransform() {{ canvas.style.transform = `translate(${{offsetX}}px, ${{offsetY}}px) scale(${{scale}})`; }}
function setTitle() {{
  document.getElementById('titleText').textContent = `${{data.episode}} 人审画布`;
  document.getElementById('subtitleText').textContent = `${{data.storyboard.title || data.root}} · ${{data.generated_at}}`;
}}
function severityClass(flag) {{ return flag?.severity === 'block' ? 'block' : flag?.severity === 'warn' ? 'warn' : 'info'; }}
function hasMissing(clip) {{
  return ['first_frame','end_frame','video'].some(k => clip[k] && !clip[k].exists);
}}
function hasSeverity(clip, sev) {{
  return (clip.qa_flags || []).some(f => f.severity === sev || (sev === 'warn' && (f.severity === 'warn' || f.severity === 'block')));
}}
function mediaBox(item, label, video=false) {{
  if (!item) return `<div class="media"><span class="missing">${{label}} 未登记</span></div>`;
  if (!item.exists) return `<div class="media"><span class="media-label">${{esc(label)}}</span><span class="missing">缺文件<br>${{esc(item.path)}}</span></div>`;
  return `<div class="media"><span class="media-label">${{esc(label)}}</span>${{video ? `<video src="${{item.url}}" controls preload="metadata"></video>` : `<img src="${{item.url}}" loading="lazy">`}}</div>`;
}}
function miniBox(item) {{
  if (!item || !item.exists) return `<div class="mini"><span class="empty">缺</span></div>`;
  return `<div class="mini"><img src="${{item.url}}" loading="lazy"></div>`;
}}
function flagHtml(flags) {{
  if (!flags || !flags.length) return '<div class="flags"><span class="badge pass">无匹配 QA flag</span></div>';
  return `<div class="flags">${{flags.slice(0,5).map(f => `<div class="flag ${{severityClass(f)}}"><strong>${{esc(f.dimension)}} · ${{esc(f.status)}}</strong><br>${{esc(f.message)}}</div>`).join('')}}${{flags.length > 5 ? `<div class="empty">另有 ${{flags.length - 5}} 条</div>` : ''}}</div>`;
}}
function cardStyle(x, y) {{ return `left:${{x}}px; top:${{y}}px;`; }}
function renderScore() {{
  const s = data.score || {{}};
  const dims = s.dimensions || [];
  const status = s.status === 'fail' ? 'block' : s.status === 'pass' ? 'pass' : 'warn';
  return `<section class="card score-card" style="${{cardStyle(40, 70)}}"><div class="card-head"><div class="card-title">机器分</div><span class="badge ${{status}}">${{esc(s.status || 'missing')}}</span></div>
    <div class="score-num">${{s.available ? esc(s.total_score) : '—'}}</div>
    <div class="meta">阈值：${{esc(s.threshold || '—')}} · 回流任务：${{(s.auto_return_tasks || []).length}} · 补采任务：${{(s.data_collection_tasks || []).length}}</div>
    <div class="score-dims">${{dims.map(d => `<div class="dimrow"><span>${{esc(d.label)}} · ${{esc(d.status)}}</span><strong>${{esc(d.score)}}</strong><div class="bar ${{d.status === 'fail' ? 'block' : d.status === 'pass' ? '' : 'warn'}}" style="grid-column:1 / 3"><span style="width:${{Math.max(0, Math.min(100, Number(d.score)||0))}}%"></span></div></div>`).join('')}}</div>
  </section>`;
}}
function renderRefs() {{
  let y = 390;
  return (data.identity_refs || []).map((ref, idx) => {{
    const media = (ref.media || []).map(m => `<div class="ref-img">${{m.exists ? `<img src="${{m.url}}" loading="lazy">` : `<span class="empty">缺<br>${{esc(m.role || '')}}</span>`}}</div>`).join('');
    const html = `<section class="card ref-card" data-kind="ref" style="${{cardStyle(40, y)}}"><div class="card-head"><div class="card-title">${{esc(ref.name || ref.character_id || '定妆参考')}}</div><span class="badge">${{esc(ref.form || '')}}</span></div><div class="ref-strip">${{media || '<span class="empty">无参考图</span>'}}</div><div class="meta">${{esc(ref.anchor_phrase || '')}}</div></section>`;
    y += 240;
    return html;
  }}).join('');
}}
function renderClip(clip, idx) {{
  const x = 380 + idx * 360;
  const y = 150 + (idx % 2) * 34;
  const status = (clip.qa_flags || []).some(f => f.severity === 'block') ? 'block' : (clip.qa_flags || []).some(f => f.severity === 'warn') || hasMissing(clip) ? 'warn' : 'pass';
  return `<section class="card clip-card" data-kind="clip" data-clip-id="${{esc(clip.id)}}" data-search="${{esc(JSON.stringify(clip))}}" style="${{cardStyle(x, y)}}"><div class="card-head"><div class="card-title">${{esc(clip.label)}} · ${{esc(clip.id)}}</div><span class="badge ${{status}}">${{status}}</span></div>
    <div class="meta">${{esc(clip.scene || '')}}<br>时长 ${{esc(clip.duration || '—')}}s · ${{esc(clip.rhythm || '')}} · ${{esc(clip.template || '')}}</div>
    <div class="media-grid">${{mediaBox(clip.first_frame, '首帧')}}${{mediaBox(clip.end_frame, '尾帧')}}${{mediaBox(clip.video, 'clip', true)}}</div>
    ${{flagHtml(clip.qa_flags)}}
  </section>`;
}}
function renderSeam(seam, idx) {{
  const x = 560 + idx * 360;
  const y = 690 + (idx % 2) * 22;
  const status = (seam.qa_flags || []).some(f => f.severity === 'block') ? 'block' : (seam.qa_flags || []).some(f => f.severity === 'warn') ? 'warn' : 'pass';
  return `<section class="card seam-card" data-kind="seam" data-search="${{esc(JSON.stringify(seam))}}" style="${{cardStyle(x, y)}}"><div class="card-head"><div class="card-title">接缝 ${{idx + 1}}</div><span class="badge ${{status}}">${{status}}</span></div><div class="meta">${{esc(seam.from)}} → ${{esc(seam.to)}}<br>${{esc(seam.transition || '')}}</div><div class="seam-media">${{miniBox(seam.tail)}}${{miniBox(seam.next_first)}}</div>${{flagHtml(seam.qa_flags)}}</section>`;
}}
function renderGlobalFlags() {{
  const flags = data.global_flags || [];
  return `<section class="card" data-kind="global" style="${{cardStyle(380, 70)}}"><div class="card-head"><div class="card-title">全局 QA flags</div><span class="badge ${{flags.some(f=>f.severity==='block') ? 'block' : flags.some(f=>f.severity==='warn') ? 'warn' : 'pass'}}">${{flags.length}}</span></div>${{flagHtml(flags)}}</section>`;
}}
function render() {{
  setTitle();
  canvas.innerHTML = `<div class="lane" style="top:130px"></div><div class="lane-label" style="top:118px">Clip 时间线</div><div class="lane" style="top:675px"></div><div class="lane-label" style="top:663px">接缝</div><div class="lane-label" style="top:355px">定妆参考</div>` +
    renderScore() + renderGlobalFlags() + renderRefs() + (data.clips || []).map(renderClip).join('') + (data.seams || []).map(renderSeam).join('');
  applyFilters();
}}
function applyFilters() {{
  const sev = document.getElementById('severityFilter').value;
  const q = document.getElementById('searchBox').value.toLowerCase().trim();
  document.querySelectorAll('.clip-card').forEach(el => {{
    const idx = Number([...document.querySelectorAll('.clip-card')].indexOf(el));
    const clip = data.clips[idx];
    let ok = true;
    if (sev === 'block') ok = hasSeverity(clip, 'block');
    if (sev === 'warn') ok = hasSeverity(clip, 'warn');
    if (sev === 'missing') ok = hasMissing(clip);
    if (q) ok = ok && el.dataset.search.toLowerCase().includes(q);
    el.classList.toggle('hidden', !ok);
  }});
  document.querySelectorAll('.seam-card').forEach(el => {{
    const hay = el.dataset.search.toLowerCase();
    el.classList.toggle('hidden', q && !hay.includes(q));
  }});
}}
document.getElementById('severityFilter').addEventListener('change', applyFilters);
document.getElementById('searchBox').addEventListener('input', applyFilters);
document.getElementById('zoomIn').onclick = () => {{ scale = Math.min(2.4, scale * 1.12); applyTransform(); }};
document.getElementById('zoomOut').onclick = () => {{ scale = Math.max(.25, scale / 1.12); applyTransform(); }};
document.getElementById('resetView').onclick = () => {{ scale = .86; offsetX = 12; offsetY = 8; applyTransform(); }};
viewport.addEventListener('mousedown', e => {{ dragging = true; sx = e.clientX; sy = e.clientY; ox = offsetX; oy = offsetY; viewport.style.cursor = 'grabbing'; }});
window.addEventListener('mouseup', () => {{ dragging = false; viewport.style.cursor = 'grab'; }});
window.addEventListener('mousemove', e => {{ if (!dragging) return; offsetX = ox + e.clientX - sx; offsetY = oy + e.clientY - sy; applyTransform(); }});
viewport.addEventListener('wheel', e => {{ e.preventDefault(); const factor = e.deltaY > 0 ? .92 : 1.08; scale = Math.max(.25, Math.min(2.4, scale * factor)); applyTransform(); }}, {{passive:false}});
window.addEventListener('keydown', e => {{ if (e.code === 'Space') {{ e.preventDefault(); document.getElementById('resetView').click(); }} }});
// 深链：board 点 Clip 跳来时带 #clip=<id> —— 居中并高亮该 Clip 卡（跨集深链落点）
function focusFromHash() {{
  document.querySelectorAll('.clip-card.focused').forEach(el => el.classList.remove('focused'));
  const m = (location.hash || '').match(/clip=([^&]+)/);
  if (!m) return;
  const id = decodeURIComponent(m[1]);
  const el = [...document.querySelectorAll('.clip-card')].find(e => e.dataset.clipId === id);
  if (!el) return;
  el.classList.remove('hidden');
  el.classList.add('focused');
  scale = 1;
  const left = parseFloat(el.style.left) || 0, top = parseFloat(el.style.top) || 0;
  offsetX = viewport.clientWidth / 2 - (left + el.offsetWidth / 2) * scale;
  offsetY = viewport.clientHeight / 2 - (top + el.offsetHeight / 2) * scale;
  applyTransform();
}}
window.addEventListener('hashchange', focusFromHash);
render();
focusFromHash();
</script>
</body>
</html>
"""


def render_html(manifest: Dict[str, Any]) -> str:
    title = f"{manifest.get('episode', '')} 人审画布"
    manifest_json = (
        json.dumps(manifest, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    return HTML_TEMPLATE.format(
        title=html.escape(title),
        manifest_json=manifest_json,
    )


def write_outputs(root: Path, ep: str, manifest: Dict[str, Any]) -> Dict[str, str]:
    paths = output_paths(root, ep)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    paths["json"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["html"].write_text(render_html(manifest), encoding="utf-8")
    return {key: str(value) for key, value in paths.items() if key != "dir"}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Build n2d human review UI canvas.")
    ap.add_argument("root", help="作品根, e.g. 制漫剧/剧名")
    ap.add_argument("episode", help="第N集")
    ap.add_argument("--write", action="store_true", help="write 生产数据/review_ui_第N集.html/json")
    ap.add_argument("--markdown", action="store_true", help="print a short Markdown summary when --write is used")
    return ap


def markdown_summary(manifest: Dict[str, Any], paths: Optional[Dict[str, str]] = None) -> str:
    score = manifest.get("score") or {}
    missing = 0
    for clip in manifest.get("clips", []):
        for key in ("first_frame", "end_frame", "video"):
            item = clip.get(key)
            if item and not item.get("exists"):
                missing += 1
    lines = [
        "# n2d 人审画布",
        "",
        f"- episode: {manifest.get('episode')}",
        f"- clips: {len(manifest.get('clips', []))}",
        f"- seams: {len(manifest.get('seams', []))}",
        f"- identity_refs: {len(manifest.get('identity_refs', []))}",
        f"- score: {score.get('total_score', '—')} ({score.get('status', 'missing')})",
        f"- missing_media: {missing}",
    ]
    if paths:
        lines.append(f"- html: {paths.get('html')}")
        lines.append(f"- json: {paths.get('json')}")
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root)
    ep = normalize_episode(ns.episode)
    manifest = build_manifest(root, ep)
    if ns.write:
        paths = write_outputs(root, ep, manifest)
        if ns.markdown:
            print(markdown_summary(manifest, paths))
        else:
            print(f"wrote {paths['html']}")
            print(f"wrote {paths['json']}")
    else:
        print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
