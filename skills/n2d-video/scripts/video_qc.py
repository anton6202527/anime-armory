#!/usr/bin/env python3
"""Extract frame QC artifacts for n2d video batches.

This script is intentionally local-only. It reads raw AI MP4 clips from
`出视频/<episode>/视频/`, extracts still frames for human review, probes stream
metadata, and writes stable QC reports under `生产数据/video_qc/<episode>/<batch>/`.
It never rewrites or strips audio from the formal video-stage outputs.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


CLIP_RE = re.compile(r"Clip[_\s-]*(\d+)", re.IGNORECASE)

# 同家族复用：接缝机检的阈值与数学只在 n2d-review/temporal_consistency 维护一份。
REVIEW_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "n2d-review" / "scripts"


def _load_temporal_module():
    """惰性加载 n2d-review 的 temporal_consistency；不可用时返回 None（机检降级为纯人审产物）。"""
    if str(REVIEW_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(REVIEW_SCRIPTS_DIR))
    try:
        import temporal_consistency  # noqa: PLC0415

        return temporal_consistency
    except Exception:
        return None


def seam_pairs(indices: Iterable[int]) -> List[Tuple[int, int]]:
    """相邻镜头对 (n, n+1)，仅当两端都在场。纯函数·可测。"""
    s = set(indices)
    return [(n, n + 1) for n in sorted(s) if n + 1 in s]


# 尾帧接力铁律只对"声明了接力"的接缝成立；match/hard/action cut 换机位换构图是设计，
# dHash 距大是正常剪辑——一律 strict 会把每个切镜都误报成接力断。
RELAY_TRANSITIONS = ("接力", "relay", "seamless", "continuous")


def seam_strictness(intent: Optional[Dict[str, Any]]) -> str:
    """接缝执行档位（纯函数）：relay 声明 → strict（block 拦验收）；
    声明了其他切镜方式 → info（只记录距离供人参考）；
    无 storyboard 意图 → strict（宁可误报交人判，不静默放过）。"""
    if intent is None:
        return "strict"
    if intent.get("relay") or str(intent.get("transition") or "").strip().lower() in RELAY_TRANSITIONS:
        return "strict"
    if str(intent.get("transition") or "").strip():
        return "info"
    return "strict"


def load_seam_intents(root: Path, episode: str) -> Dict[int, Dict[str, Any]]:
    """clip 序号 → storyboard 声明的接缝意图（continuity.transition + need_end_frame）。"""
    path = root / "脚本" / episode / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for clip in (data.get("clips") or data.get("shots") or []):
        if not isinstance(clip, dict):
            continue
        idx = clip_index(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if idx is None:
            match = re.search(r"(\d+)\s*$", str(clip.get("id") or ""))
            idx = int(match.group(1)) if match else None
        if idx is None:
            continue
        cont = clip.get("continuity") or {}
        out[idx] = {"transition": cont.get("transition"),
                    "relay": bool(clip.get("need_end_frame") or cont.get("need_end_frame"))}
    return out


def machine_check(payload: Dict[str, Any], context_frames: Optional[Dict[int, Dict[str, str]]] = None,
                  seam_intents: Optional[Dict[int, Dict[str, Any]]] = None) -> None:
    """就地给 QC payload 加接缝机检：前镜 end 帧 vs 后镜 start 帧（尾帧接力铁律的出视频侧验证）。

    阈值与 dHash/色距数学复用 n2d-review/temporal_consistency（单一真值源）；
    缺 Pillow / review 模块不可用时写 machine_notes 降级，不臆造分数。
    context_frames 允许调用方补入不在本批次、但在盘上存在的相邻 clip 帧（单镜验收时查两侧接缝）。
    """
    notes = payload.setdefault("machine_notes", [])
    tc = _load_temporal_module()
    if tc is None:
        notes.append("n2d-review/temporal_consistency 不可用——接缝机检跳过，交人判 contact sheet。")
        return
    frames_by_index: Dict[int, Dict[str, str]] = dict(context_frames or {})
    for item in payload.get("clips", []):
        idx = clip_index(item.get("file") or "")
        if idx is None:
            continue
        ok_frames = {f["label"]: f["path"] for f in item.get("frames", [])
                     if f.get("path") and not f.get("error") and Path(f["path"]).exists()}
        if ok_frames:
            frames_by_index[idx] = ok_frames
    seams: List[Dict[str, Any]] = []
    checked = skipped = 0
    for n, m in seam_pairs(frames_by_index):
        tail = frames_by_index[n].get("end")
        head = frames_by_index[m].get("start")
        if not tail or not head:
            continue
        chk = tc.seam_pair_check(tail, head)
        if chk is None:
            skipped += 1
            continue
        checked += 1
        intent = (seam_intents or {}).get(n)
        strictness = seam_strictness(intent)
        chk.update({"from_clip": f"Clip_{n:02d}", "to_clip": f"Clip_{m:02d}",
                    "transition": (intent or {}).get("transition"), "strictness": strictness})
        if strictness == "info" and chk["verdict"] != "ok":
            # storyboard 声明的设计切镜（match/hard/action cut）——构图必然变，距离只记录不拦。
            chk["verdict_if_relay"] = chk["verdict"]
            chk["verdict"] = "info"
        seams.append(chk)
    if skipped and not checked:
        notes.append("缺 Pillow——接缝机检跳过，交人判 contact sheet。")
    if seam_intents is None and checked:
        notes.append("storyboard 接缝意图不可用——全部接缝按接力铁律严格判（可能误报设计切镜）。")
    payload["seams"] = seams
    payload["machine_summary"] = {
        "seams_checked": checked,
        "seam_blocks": sum(1 for s in seams if s["verdict"] == "block"),
        "seam_warns": sum(1 for s in seams if s["verdict"] == "warn"),
        "seam_info": sum(1 for s in seams if s["verdict"] == "info"),
    }


# 近景景别标记：这些镜表情变化时最易"脸被表情带着重画"（五官比例随表情漂移）。
# MS/LS 等不入列（脸占比小，表情漂移不致命）。lens 串里出现任一标记即判近景。
CLOSEUP_MARKERS = ("ECU", "MCU", "BCU", "CU", "OTS", "反打", "特写", "近景", "过肩")


def is_closeup_lens(lens: str) -> bool:
    """lens 串（如 'CU 50mm 缓推' / 'MS到CU' / 'CU反打'）是否落在近景档。纯函数·可测。"""
    s = str(lens or "").upper()
    return any(m.upper() in s for m in CLOSEUP_MARKERS)


def is_closeup_shot(clip: Dict[str, Any]) -> bool:
    """storyboard clip 的任一分镜 lens 命中近景档即判近景。"""
    for shot in clip.get("shots", []) or []:
        if isinstance(shot, dict) and is_closeup_lens(shot.get("lens", "")):
            return True
    return False


def load_shot_types(root: Path, episode: str) -> Dict[int, Dict[str, Any]]:
    """clip 序号 → {closeup: bool, lens: 串}。近景判定喂片内身份漂移采样。"""
    path = root / "脚本" / episode / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for clip in (data.get("clips") or data.get("shots") or []):
        if not isinstance(clip, dict):
            continue
        idx = clip_index(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if idx is None:
            match = re.search(r"(\d+)\s*$", str(clip.get("id") or ""))
            idx = int(match.group(1)) if match else None
        if idx is None:
            continue
        lenses = "；".join(str((s or {}).get("lens", "")) for s in (clip.get("shots") or []))
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        out[idx] = {"closeup": is_closeup_shot(clip), "lens": lenses,
                    # 双帧接力镜：首尾两端帧已锚同人，大表情弧线天然大 dHash → 片内 block 豁免，不误杀。
                    "double_frame": bool(clip.get("need_end_frame") or cont.get("need_end_frame"))}
    return out


# 片内身份「重画」block 阈值：远超接缝 block（SEAM_BLOCK≈29/64）才判脸被重画。
# 取 44/64≈69% 结构差——正常表演/运镜动不到，留足余量只抓真重画，非双帧近景镜适用。
INTRA_REDRAW_BLOCK = 44


def intra_verdict(worst: int, gross: int, have_types: bool, double_frame: bool,
                  redraw_block: int = INTRA_REDRAW_BLOCK) -> str:
    """片内身份采样定级（纯函数·可测）：
      worst<=gross → ok；
      worst>redraw_block 且景别已知确为近景 且非双帧接力镜 → block（脸被重画，拒绝验收）；
      其余（gross<worst<=redraw_block，或双帧镜，或景别未知）→ warn（粗筛交人判，不误杀表演/非近景）。"""
    if worst <= gross:
        return "ok"
    if have_types and worst > redraw_block and not double_frame:
        return "block"
    return "warn"


def intra_clip_check(payload: Dict[str, Any], shot_types: Optional[Dict[int, Dict[str, Any]]] = None) -> None:
    """片内身份漂移采样（近景 CU/MCU/反打镜）：抽同一 clip 的 start/mid/end 帧两两比
    dHash 结构距 + 色距（复用 temporal_consistency 同一套数学），抓"表情变化时脸被重画"。

    设计取舍：表情运动本就带结构变化，且近景里运镜/转头也会动 dHash——所以这里是**粗筛**，
    只在"远超接缝 block 阈值"的 gross 变化报 **warn 交人判**，**永不 block**（不误杀正常表演）。
    精确同人判定（face embedding 余弦 < 身份下限）在 n2d-review/temporal_consistency.analyze
    （需 insightface，重）；video_qc 只靠 Pillow 做轻量初筛，缺料静默降级、不臆造分数。
    无 storyboard 景别时**对全部 clip 抽样**（宁可多看几镜，不静默漏近景）。"""
    notes = payload.setdefault("machine_notes", [])
    tc = _load_temporal_module()
    if tc is None:
        return  # machine_check 已记同一条降级 note，不重复
    # gross 阈值：接缝 block 阈值（SEAM_BLOCK，默认 29/64）即视为"片内脸级结构突变"。
    gross = int(getattr(tc, "SEAM_BLOCK", 29))
    intra: List[Dict[str, Any]] = []
    checked = warns = blocks = 0
    have_types = bool(shot_types)
    for item in payload.get("clips", []):
        idx = clip_index(item.get("file") or "")
        if idx is None:
            continue
        info = (shot_types or {}).get(idx) or {}
        if have_types and not info.get("closeup"):
            continue  # 有景别表时只查近景镜；无表时全查
        frames = {f["label"]: f["path"] for f in item.get("frames", [])
                  if f.get("path") and not f.get("error") and Path(f["path"]).exists()}
        ordered = [frames[l] for l in ("start", "mid", "end") if l in frames]
        if len(ordered) < 2:
            continue
        pairs: List[Dict[str, Any]] = []
        worst = 0
        for a, b in zip(ordered, ordered[1:]):
            chk = tc.seam_pair_check(a, b)
            if chk is None:
                continue
            pairs.append({"dist": chk["dist"], "color_dist": chk.get("color_dist")})
            worst = max(worst, chk["dist"])
        if not pairs:
            continue
        checked += 1
        double_frame = bool(info.get("double_frame"))
        verdict = intra_verdict(worst, gross, have_types, double_frame)
        if verdict == "ok":
            continue
        if verdict == "block":
            blocks += 1
        else:
            warns += 1
        intra.append({"clip": f"Clip_{idx:02d}", "lens": info.get("lens", ""),
                      "max_dist": worst, "verdict": verdict, "double_frame": double_frame, "pairs": pairs})
    if checked:
        payload["intra_clips"] = intra
        summary = payload.setdefault("machine_summary", {})
        summary["intra_checked"] = checked
        summary["intra_warns"] = warns
        summary["intra_blocks"] = blocks
        if not have_types:
            notes.append("storyboard 景别不可用——片内身份采样对全部 clip 抽样（可能含非近景）。")


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def video_dir(root: Path, episode: str) -> Path:
    return root / "出视频" / episode / "视频"


def clip_index(path_or_name: str) -> Optional[int]:
    match = CLIP_RE.search(Path(path_or_name).name)
    return int(match.group(1)) if match else None


def parse_clip_range(value: str) -> Tuple[int, int]:
    text = str(value or "").strip()
    match = re.fullmatch(r"(\d+)\s*[-_]\s*(\d+)", text)
    if not match:
        raise ValueError(f"invalid range: {value!r}; expected e.g. 01-05")
    start, end = int(match.group(1)), int(match.group(2))
    if start <= 0 or end < start:
        raise ValueError(f"invalid range: {value!r}")
    return start, end


def batch_label(start: int, end: int) -> str:
    return f"{start:02d}_{end:02d}"


def discover_clips(root: Path, episode: str, start: Optional[int] = None, end: Optional[int] = None) -> List[Path]:
    files = sorted(video_dir(root, episode).glob("Clip_*.mp4"), key=lambda p: (clip_index(p.name) or 10**9, p.name))
    selected: List[Path] = []
    for path in files:
        idx = clip_index(path.name)
        if idx is None:
            continue
        if start is not None and idx < start:
            continue
        if end is not None and idx > end:
            continue
        selected.append(path)
    return selected


def _run_json(cmd: Sequence[str]) -> Dict[str, Any]:
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        return {"error": proc.stderr.strip() or f"command failed: {cmd[0]} exit {proc.returncode}"}
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"error": f"invalid JSON from {cmd[0]}: {exc}", "stdout": proc.stdout}


def probe_video(path: Path) -> Dict[str, Any]:
    if shutil.which("ffprobe") is None:
        return {"path": str(path), "error": "ffprobe not found", "has_audio": None}
    data = _run_json([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,width,height,codec_name",
        "-of",
        "json",
        str(path),
    ])
    streams = data.get("streams") if isinstance(data, dict) else []
    if not isinstance(streams, list):
        streams = []
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    duration = None
    try:
        duration = float(data.get("format", {}).get("duration"))
    except (TypeError, ValueError, AttributeError):
        duration = None
    return {
        "path": str(path),
        "file": path.name,
        "clip": f"Clip_{clip_index(path.name):02d}" if clip_index(path.name) else path.stem,
        "duration_sec": duration,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "video_codec": video_stream.get("codec_name"),
        "audio_streams": [s for s in streams if s.get("codec_type") == "audio"],
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "probe_error": data.get("error"),
    }


def sample_times(duration: Optional[float]) -> List[Tuple[str, float]]:
    if duration is None or duration <= 0:
        return [("start", 0.0), ("mid", 1.0), ("end", 2.0)]
    end = max(0.0, duration - min(0.2, duration / 10.0))
    return [("start", 0.0), ("mid", duration / 2.0), ("end", end)]


def extract_frames(path: Path, frames_dir: Path, duration: Optional[float]) -> List[Dict[str, Any]]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    idx = clip_index(path.name) or 0
    outputs: List[Dict[str, Any]] = []
    if shutil.which("ffmpeg") is None:
        return [{"label": label, "time_sec": t, "error": "ffmpeg not found"} for label, t in sample_times(duration)]
    for ordinal, (label, ts) in enumerate(sample_times(duration), 1):
        out = frames_dir / f"Clip_{idx:02d}_{ordinal:02d}_{label}.jpg"
        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{ts:.3f}",
                "-i",
                str(path),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(out),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        item: Dict[str, Any] = {"label": label, "time_sec": round(ts, 3), "path": str(out)}
        if proc.returncode != 0 or not out.exists():
            item["error"] = proc.stderr.strip() or f"ffmpeg exit {proc.returncode}"
        outputs.append(item)
    return outputs


def make_contact_sheet(frame_paths: Sequence[Path], out_path: Path, thumb_width: int = 240) -> Optional[str]:
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None
    images = []
    for path in frame_paths:
        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            continue
        ratio = thumb_width / max(1, img.width)
        thumb = img.resize((thumb_width, max(1, int(img.height * ratio))))
        images.append((path.name, thumb))
    if not images:
        return None
    label_h = 22
    cols = 3
    rows = math.ceil(len(images) / cols)
    cell_w = thumb_width
    cell_h = max(img.height for _, img in images) + label_h
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (name, img) in enumerate(images):
        x = (i % cols) * cell_w
        y = (i // cols) * cell_h
        sheet.paste(img, (x, y + label_h))
        draw.text((x + 4, y + 4), name[:36], fill=(0, 0, 0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, quality=88)
    return str(out_path)


def neighbor_context_frames(root: Path, episode: str, payload: Dict[str, Any],
                            frames_dir: Path) -> Dict[int, Dict[str, str]]:
    """为不在本批次、但盘上已存在的相邻 clip 抽帧——单镜验收时也能查它两侧的接缝。"""
    present = {clip_index(i.get("file") or "") for i in payload.get("clips", [])}
    present.discard(None)
    wanted = ({n - 1 for n in present} | {n + 1 for n in present}) - present
    out: Dict[int, Dict[str, str]] = {}
    vdir = video_dir(root, episode)
    if not vdir.is_dir():
        return out
    for k in sorted(w for w in wanted if isinstance(w, int) and w > 0):
        matches = [p for p in vdir.glob(f"Clip_{k:02d}*.mp4") if "noaudio" not in p.name]
        if not matches:
            continue
        meta = probe_video(matches[0])
        frames = extract_frames(matches[0], frames_dir, meta.get("duration_sec"))
        ok = {f["label"]: f["path"] for f in frames
              if f.get("path") and not f.get("error") and Path(f["path"]).exists()}
        if ok:
            out[k] = ok
    return out


def render_markdown(payload: Dict[str, Any]) -> str:
    lines = [
        "# n2d Video QC",
        "",
        f"- episode: {payload['episode']}",
        f"- batch: {payload['batch']}",
        f"- clips: {len(payload['clips'])}",
        f"- contact_sheet: `{payload.get('contact_sheet') or 'not generated'}`",
        "",
        "| Clip | Duration | Size | Audio | Frames | Notes |",
        "|---|---:|---|---|---:|---|",
    ]
    for item in payload["clips"]:
        dur = item.get("duration_sec")
        duration = f"{dur:.3f}s" if isinstance(dur, (int, float)) else "?"
        size = f"{item.get('width') or '?'}x{item.get('height') or '?'}"
        audio = "yes" if item.get("has_audio") else ("unknown" if item.get("has_audio") is None else "no")
        frame_count = sum(1 for f in item.get("frames", []) if f.get("path") and not f.get("error"))
        notes = item.get("probe_error") or "; ".join(f.get("error", "") for f in item.get("frames", []) if f.get("error"))
        lines.append(f"| `{item.get('file')}` | {duration} | {size} | {audio} | {frame_count} | {notes or ''} |")
    summary = payload.get("machine_summary") or {}
    seams = payload.get("seams") or []
    lines.append("")
    lines.append("## Seam machine check（尾帧接力 · 前镜 end 帧 vs 后镜 start 帧）")
    lines.append("")
    if summary:
        lines.append(f"- checked: {summary.get('seams_checked', 0)}"
                     f" · block: {summary.get('seam_blocks', 0)} · warn: {summary.get('seam_warns', 0)}")
    for note in payload.get("machine_notes") or []:
        lines.append(f"- note: {note}")
    flagged = [s for s in seams if s.get("verdict") != "ok"]
    if flagged:
        lines.append("")
        lines.append("| Seam | dHash | Color dist | Verdict |")
        lines.append("|---|---:|---:|---|")
        for s in flagged:
            lines.append(f"| {s.get('from_clip')} → {s.get('to_clip')} | {s.get('dist')} "
                         f"| {s.get('color_dist') if s.get('color_dist') is not None else '-'} | {s.get('verdict')} |")
    intra = payload.get("intra_clips") or []
    if summary.get("intra_checked"):
        lines.append("")
        lines.append("## Intra-clip identity sampling（近景片内身份漂移 · start/mid/end 抽帧）")
        lines.append("")
        lines.append(f"- closeup clips checked: {summary.get('intra_checked', 0)}"
                     f" · block: {summary.get('intra_blocks', 0)} · warn: {summary.get('intra_warns', 0)}"
                     f"（warn=粗筛交人判；block=近景非双帧镜结构远超重画阈值 dHash>{INTRA_REDRAW_BLOCK}，"
                     "拒绝验收；精确同人判定走 n2d-review/temporal_consistency.analyze）")
        if intra:
            lines.append("")
            lines.append("| Clip | Lens | Max dHash | Verdict |")
            lines.append("|---|---|---:|---|")
            for s in intra:
                lines.append(f"| {s.get('clip')} | {s.get('lens') or '-'} | {s.get('max_dist')} | {s.get('verdict')} |")
    lines.append("")
    lines.append("Status: pending human review unless the batch manifest marks it accepted.")
    return "\n".join(lines) + "\n"


def run_qc(root: Path, episode: str, clips: Sequence[Path], batch: str, out_dir: Optional[Path] = None) -> Dict[str, Any]:
    if out_dir is None:
        out_dir = production_dir(root) / "video_qc" / episode / batch
    frames_dir = out_dir / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "kind": "n2d_video_qc",
        "version": 1,
        "root": str(root),
        "episode": episode,
        "batch": batch,
        "clips": [],
    }
    all_frames: List[Path] = []
    for clip in clips:
        meta = probe_video(clip)
        frames = extract_frames(clip, frames_dir, meta.get("duration_sec"))
        meta["frames"] = frames
        payload["clips"].append(meta)
        all_frames.extend(Path(f["path"]) for f in frames if f.get("path") and Path(f["path"]).exists())
    contact = make_contact_sheet(all_frames, out_dir / f"contact_sheet_{batch}.jpg")
    payload["contact_sheet"] = contact
    machine_check(payload, neighbor_context_frames(root, episode, payload, frames_dir),
                  load_seam_intents(root, episode) or None)
    intra_clip_check(payload, load_shot_types(root, episode) or None)
    json_path = out_dir / f"video_qc_{episode}_{batch}.json"
    md_path = out_dir / f"video_qc_{episode}_{batch}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    payload["json_path"] = str(json_path)
    payload["markdown_path"] = str(md_path)
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--range", dest="clip_range", help="Clip range, e.g. 01-05")
    ap.add_argument("--batch", help="Batch label override, default derived from --range or clip span")
    ap.add_argument("--clip", action="append", default=[], help="Explicit MP4 path or filename; repeatable")
    ap.add_argument("--out-dir")
    ap.add_argument("--json", action="store_true", help="Print machine-readable payload")
    ns = ap.parse_args(argv)

    root = Path(ns.root).expanduser().resolve()
    start = end = None
    if ns.clip_range:
        start, end = parse_clip_range(ns.clip_range)
    clips: List[Path] = []
    if ns.clip:
        for item in ns.clip:
            path = Path(item)
            if not path.is_absolute():
                path = video_dir(root, ns.episode) / item
            clips.append(path)
    else:
        clips = discover_clips(root, ns.episode, start, end)
    if not clips:
        print("No clips found for QC", file=sys.stderr)
        return 2
    indices = [clip_index(p.name) for p in clips if clip_index(p.name)]
    label = ns.batch or (batch_label(start, end) if start and end else batch_label(min(indices), max(indices)) if indices else "manual")
    payload = run_qc(root, ns.episode, clips, label, Path(ns.out_dir).resolve() if ns.out_dir else None)
    if ns.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(payload["markdown_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
