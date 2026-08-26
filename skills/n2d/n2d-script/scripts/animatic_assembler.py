#!/usr/bin/env python3
"""Build a timed rough animatic preview from storyboard contracts.

The preview intentionally works before paid image generation.  If storyboard
frame images already exist it references them; otherwise it renders timed text
slates in HTML so the director/editor can inspect rhythm, seams, and readability
before expensive visual work starts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

N2D_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
from editorial_timeline import build_editorial_timeline, write_editorial_timeline  # noqa: E402


VERSION = 2
KIND = "n2d_animatic_preview"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def episode_label(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("第") and value.endswith("集"):
        return value
    return f"第{value}集"


def relpath(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return str(path)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def path_digest(root: Path, rel: str) -> str | None:
    path = root / rel
    if path.is_file():
        return file_sha256(path)
    if path.is_dir():
        h = hashlib.sha256()
        for item in sorted(p for p in path.rglob("*") if p.is_file()):
            item_rel = relpath(root, item)
            h.update(item_rel.encode("utf-8"))
            h.update(b"\0")
            h.update(file_sha256(item).encode("ascii"))
            h.update(b"\n")
        return "dir:" + h.hexdigest()
    return None


def artifact_fingerprint(root: Path, rels: Sequence[str]) -> Dict[str, Any]:
    files: Dict[str, str | None] = {}
    h = hashlib.sha256()
    for rel in sorted({str(r).replace(os.sep, "/") for r in rels}):
        digest = path_digest(root, rel)
        files[rel] = digest
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update((digest or "-").encode("ascii"))
        h.update(b"\n")
    return {"files": files, "sha": h.hexdigest()}


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    write_atomic(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def as_float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        out = float(value)
        return out if out > 0 else None
    except Exception:
        return None


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("clip_id") or clip.get("id") or clip.get("clip") or "").strip()
    if raw:
        m = re.search(r"(?:Clip|clip)[_\s-]?(\d+)", raw)
        if m:
            return f"Clip_{int(m.group(1)):02d}"
        return raw
    return f"Clip_{idx:02d}"


def duration_for(clip: Mapping[str, Any], cid: str, idx: int, durations: Mapping[str, Any]) -> Optional[float]:
    for key in (
        "duration_sec",
        "duration",
        "seconds",
        "时长",
    ):
        dur = as_float(clip.get(key))
        if dur is not None:
            return dur
    for key in (cid, str(idx), f"镜头{idx}", f"Clip_{idx:02d}"):
        dur = as_float(durations.get(key))
        if dur is not None:
            return dur
    return None


def image_candidates(root: Path, ep: str, clip: Mapping[str, Any], cid: str, idx: int) -> List[Path]:
    raw: List[str] = []
    for key in ("firstframe_png", "first_frame", "image", "image_path", "frame_path"):
        value = str(clip.get(key) or "").strip()
        if value:
            raw.append(value)
    base = root / "出图" / ep / "图片"
    if base.is_dir():
        names = {cid, cid.replace("_", ""), f"{idx:02d}", f"镜头{idx}", f"镜头{idx:02d}"}
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            stem = path.stem
            if any(token and token in stem for token in names):
                raw.append(relpath(root, path))
    out: List[Path] = []
    for item in raw:
        path = Path(item)
        if not path.is_absolute():
            path = root / path
        if path.is_file() and path not in out:
            out.append(path)
    return out


def storyboard_clips(root: Path, ep: str) -> List[Mapping[str, Any]]:
    data = load_json(root / "脚本" / ep / "storyboard.json")
    clips = data.get("clips") if isinstance(data, Mapping) else []
    return [c for c in clips or [] if isinstance(c, Mapping)]


def parse_srt(path: Path) -> List[Dict[str, Any]]:
    """Parse the small SRT subset needed by the browser preview."""
    if not path.is_file():
        return []

    def seconds(raw: str) -> float:
        hh, mm, tail = raw.strip().replace(".", ",").split(":")
        ss, ms = tail.split(",")
        return int(hh) * 3600 + int(mm) * 60 + int(ss) + int(ms) / 1000.0

    cues: List[Dict[str, Any]] = []
    for block in re.split(r"\r?\n\s*\r?\n", path.read_text(encoding="utf-8", errors="ignore").strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        timing_idx = next((i for i, line in enumerate(lines) if "-->" in line), -1)
        if timing_idx < 0 or timing_idx + 1 >= len(lines):
            continue
        try:
            start, end = [seconds(item) for item in lines[timing_idx].split("-->", 1)]
        except Exception:
            continue
        text = " ".join(lines[timing_idx + 1:]).strip()
        if text and end > start:
            cues.append({"start_sec": round(start, 3), "end_sec": round(end, 3), "text": text})
    return cues


def build_report(root: Path, ep: str) -> Dict[str, Any]:
    root = root.resolve()
    ep = episode_label(ep)
    input_rels = [
        f"脚本/{ep}/storyboard.json",
        f"脚本/{ep}/镜头时长.json",
        f"脚本/{ep}/字幕_中文.srt",
        f"合成/{ep}/配音/voice_zh.wav",
        f"出图/{ep}/图片",
    ]
    subtitle_rel = f"脚本/{ep}/字幕_中文.srt"
    audio_rel = f"合成/{ep}/配音/voice_zh.wav"
    subtitles = parse_srt(root / subtitle_rel)
    audio_ready = (root / audio_rel).is_file() and (root / audio_rel).stat().st_size > 0
    clips = storyboard_clips(root, ep)
    durations = load_json(root / "脚本" / ep / "镜头时长.json")
    durations = durations if isinstance(durations, Mapping) else {}
    timeline: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    cursor = 0.0
    for idx, clip in enumerate(clips, start=1):
        cid = clip_id(clip, idx)
        dur = duration_for(clip, cid, idx, durations)
        if dur is None:
            findings.append({"severity": "block", "code": "missing_clip_duration", "clip_id": cid, "message": f"{cid} 缺有效时长"})
            dur = 0.0
        imgs = image_candidates(root, ep, clip, cid, idx)
        continuity = clip.get("continuity") if isinstance(clip.get("continuity"), Mapping) else {}
        row = {
            "clip_id": cid,
            "index": idx,
            "start_sec": round(cursor, 3),
            "duration_sec": round(float(dur), 3),
            "end_sec": round(cursor + float(dur), 3),
            "label": str(clip.get("label") or clip.get("scene") or ""),
            "scene": str(clip.get("scene") or clip.get("location_id") or ""),
            "dramatic_function": str(clip.get("dramatic_function") or ""),
            "pacing_role": str(clip.get("pacing_role") or clip.get("runtime_priority") or ""),
            "transition": str(continuity.get("transition") or ""),
            "screen_direction": str(continuity.get("eyeline") or continuity.get("screen_direction") or ""),
            "image": relpath(root, imgs[0]) if imgs else "",
            "source": "storyboard",
        }
        timeline.append(row)
        cursor += float(dur)
    if not clips:
        findings.append({"severity": "block", "code": "missing_storyboard_clips", "message": "storyboard.json 缺 clips[]，无法生成 timed animatic。"})
    image_count = sum(1 for row in timeline if row.get("image"))
    reviewability_reasons: List[str] = []
    if not audio_ready:
        reviewability_reasons.append("缺 guide voice，无法实际听辨对白节奏")
    if not subtitles:
        reviewability_reasons.append("缺可解析中文字幕，无法核对声画/字幕时序")
    status = "block" if any(f["severity"] == "block" for f in findings) else "pass"
    return {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "generated_at": now_iso(),
        "status": status,
        "inputs": {
            "storyboard": f"脚本/{ep}/storyboard.json",
            "shot_durations": f"脚本/{ep}/镜头时长.json",
            "episode_images": f"出图/{ep}/图片",
            "guide_audio": audio_rel,
            "subtitle_zh": subtitle_rel,
        },
        "inputs_fingerprint": artifact_fingerprint(root, input_rels),
        "summary": {
            "clip_count": len(timeline),
            "image_backed_clips": image_count,
            "text_slate_clips": len(timeline) - image_count,
            "total_duration_sec": round(cursor, 3),
        },
        "timeline": timeline,
        "subtitles": subtitles,
        "reviewability": {
            "status": "ready" if not reviewability_reasons else "unmeasured",
            "audio_backed": audio_ready,
            "subtitle_backed": bool(subtitles),
            "reasons": reviewability_reasons,
        },
        "findings": findings,
        "notes": [
            "HTML 预览按 guide voice 的 currentTime 同步 storyboard 与中文字幕；缺图片时使用文字 slate。",
            "guide voice 或字幕缺失时 reviewability=unmeasured，不得把无声文字预览当成已完成 animatic 审阅。",
        ],
    }


def render_html(root: Path, payload: Mapping[str, Any]) -> str:
    ep = str(payload.get("episode") or "")
    timeline = payload.get("timeline") if isinstance(payload.get("timeline"), list) else []
    subtitles = payload.get("subtitles") if isinstance(payload.get("subtitles"), list) else []
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), Mapping) else {}
    audio_rel = str(inputs.get("guide_audio") or "")
    audio_src = f'../{html.escape(audio_rel)}' if audio_rel else ""
    cards: List[str] = []
    for row in timeline:
        if not isinstance(row, Mapping):
            continue
        cid = html.escape(str(row.get("clip_id") or "Clip"))
        dur = html.escape(str(row.get("duration_sec") or 0))
        img = str(row.get("image") or "")
        visual = ""
        if img:
            visual = f'<img src="../{html.escape(img)}" alt="{cid}">'
        else:
            visual = (
                '<div class="slate">'
                f'<strong>{cid}</strong>'
                f'<span>{html.escape(str(row.get("scene") or ""))}</span>'
                "</div>"
            )
        text = html.escape(str(row.get("dramatic_function") or row.get("label") or ""))
        pacing = html.escape(str(row.get("pacing_role") or ""))
        transition = html.escape(str(row.get("transition") or ""))
        cards.append(
            f'<section class="clip" data-duration="{dur}">{visual}'
            f'<div class="meta"><b>{cid}</b><span>{dur}s</span><span>{pacing}</span><span>{transition}</span></div>'
            f'<p>{text}</p></section>'
        )
    payload_json = html.escape(json.dumps(timeline, ensure_ascii=False))
    subtitle_json = html.escape(json.dumps(subtitles, ensure_ascii=False))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(ep)} Animatic</title>
<style>
body{{margin:0;background:#111;color:#f4f0e8;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{max-width:980px;margin:0 auto;padding:24px}}
h1{{font-size:24px;margin:0 0 16px}}
.player{{border:1px solid #333;background:#171717}}
.clip{{display:none;min-height:540px;align-items:center;justify-content:center;position:relative;overflow:hidden}}
.clip.active{{display:flex}}
.clip img{{max-width:100%;max-height:540px;object-fit:contain}}
.slate{{width:100%;height:540px;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#252525;gap:16px}}
.slate strong{{font-size:54px}}
.slate span{{font-size:22px;color:#cfc7b8}}
.meta{{position:absolute;left:0;right:0;bottom:0;background:rgba(0,0,0,.72);display:flex;gap:16px;align-items:center;padding:10px 14px;font-size:14px}}
.clip p{{position:absolute;left:14px;right:14px;top:12px;margin:0;padding:10px 12px;background:rgba(0,0,0,.62);line-height:1.5}}
.controls{{display:flex;gap:10px;align-items:center;margin:14px 0}}
.caption{{min-height:2.8em;padding:10px 14px;text-align:center;font-size:22px;background:#050505}}
audio{{width:100%;margin:12px 0}}
button{{font:inherit;padding:8px 12px;border:1px solid #555;background:#222;color:#fff}}
progress{{width:100%;height:10px}}
pre{{white-space:pre-wrap;background:#1c1c1c;padding:12px;overflow:auto}}
</style>
</head>
<body>
<main>
<h1>{html.escape(ep)} Animatic</h1>
<div class="player">{''.join(cards)}</div>
<div id="caption" class="caption"></div>
<audio id="guide-audio" controls preload="metadata" src="{audio_src}"></audio>
<div class="controls"><button id="play">Play</button><button id="pause">Pause</button><button id="prev">Prev</button><button id="next">Next</button><span id="label"></span></div>
<progress id="bar" value="0" max="1"></progress>
<script type="application/json" id="timeline">{payload_json}</script>
<script type="application/json" id="subtitles">{subtitle_json}</script>
<script>
const clips=[...document.querySelectorAll('.clip')];
const audio=document.getElementById('guide-audio');
const cues=JSON.parse(document.getElementById('subtitles').textContent||'[]');
const starts=[];let cursor=0;clips.forEach(c=>{{starts.push(cursor);cursor+=Math.max(.1,Number(c.dataset.duration||1));}});
let i=0,timer=null,manualTime=0,last=performance.now();
function show(n){{clips.forEach(c=>c.classList.remove('active'));i=Math.max(0,Math.min(clips.length-1,n));if(clips[i])clips[i].classList.add('active');}}
function currentTime(){{return Number.isFinite(audio.duration)&&audio.currentSrc ? audio.currentTime : manualTime;}}
function tick(){{
 const now=performance.now();if((!audio.currentSrc||audio.paused)&&timer)manualTime+=(now-last)/1000;last=now;
 const t=currentTime();let idx=starts.findIndex((s,j)=>t>=s&&t<(starts[j+1]??cursor));if(idx<0)idx=Math.max(0,clips.length-1);show(idx);
 const local=t-(starts[idx]||0),dur=Math.max(.1,Number(clips[idx]?.dataset.duration||1));
 document.getElementById('label').textContent=`${{idx+1}}/${{clips.length}} · ${{t.toFixed(1)}}s`;
 document.getElementById('bar').value=Math.min(1,local/dur);
 document.getElementById('caption').textContent=(cues.find(c=>t>=c.start_sec&&t<c.end_sec)||{{}}).text||'';
 if(t>=cursor){{pause();return;}}timer=requestAnimationFrame(tick);
}}
function play(){{if(timer)return;last=performance.now();if(audio.currentSrc)audio.play().catch(()=>{{}});timer=requestAnimationFrame(tick);}}
function pause(){{if(timer)cancelAnimationFrame(timer);timer=null;if(audio.currentSrc)audio.pause();}}
function seek(n){{const target=Math.max(0,Math.min(clips.length-1,n));manualTime=starts[target]||0;if(audio.currentSrc)audio.currentTime=manualTime;show(target);}}
document.getElementById('play').onclick=play;
document.getElementById('pause').onclick=pause;
document.getElementById('prev').onclick=()=>seek(i-1);
document.getElementById('next').onclick=()=>seek(i+1);
audio.ontimeupdate=()=>{{if(!timer)tick();}};
show(0);tick();
</script>
</main>
</body>
</html>
"""


def write_outputs(root: Path, ep: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    ep = episode_label(ep)
    prod = root / "生产数据"
    json_path = prod / f"animatic_{ep}.json"
    html_path = prod / f"animatic_{ep}.html"
    write_json(json_path, payload)
    write_atomic(html_path, render_html(root, payload))
    payload = dict(payload)
    payload["json_path"] = relpath(root, json_path)
    payload["preview_artifact"] = relpath(root, html_path)
    editorial = build_editorial_timeline(root, ep)
    payload["editorial_timeline"] = {
        "phase": editorial.get("phase"),
        "status": editorial.get("status"),
        "outputs": write_editorial_timeline(root, editorial),
    }
    write_json(json_path, payload)
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build n2d timed animatic preview")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    payload = build_report(root, ns.episode)
    if ns.write:
        payload = write_outputs(root, episode_label(ns.episode), payload)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"{payload['episode']} animatic: {payload['status']} clips={(payload['summary'] or {}).get('clip_count', 0)}")
        if payload.get("preview_artifact"):
            print(f"  preview: {payload['preview_artifact']}")
    return 0 if payload.get("status") != "block" else 2


if __name__ == "__main__":
    raise SystemExit(main())
