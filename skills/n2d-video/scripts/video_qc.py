#!/usr/bin/env python3
"""Extract frame QC artifacts for n2d video batches.

This script is intentionally local-only. It reads raw AI MP4 clips from
`出视频/<episode>/视频/`, extracts still frames for human review, probes stream
metadata, and writes stable QC reports under `生产数据/video_qc/<episode>/<batch>/`.
Frames are version-addressed once under `生产数据/video_qc/<episode>/_frames/`;
overlapping batches reference that store instead of copying the same JPEGs.
It never rewrites or strips audio from the formal video-stage outputs.
"""
from __future__ import annotations

import argparse
import hashlib
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
N2D_LIB = Path(__file__).resolve().parents[2] / "n2d" / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))
from seam_contract import needs_end_anchor, normalize_seam_mode, requires_boundary_frame


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


# 像素同帧铁律只对 continuous_take_relay 成立。其它 seam_mode 的相邻
# 画面本就可以不同，dHash/色距仅作信息，不得阻断验收。
RELAY_TRANSITIONS = ("接力", "relay", "seamless", "continuous")  # legacy aliases


def _is_relay_transition(transition: Any) -> bool:
    return str(transition or "").strip().lower() in RELAY_TRANSITIONS


def _declared_relay(transition: Any, need_endframe: bool) -> bool:
    """Whether this seam is a strict cross-clip relay.

    In migrated legacy boards `need_endframe=true` may have meant within-shot
    guidance. Explicit hard/match/action cuts therefore keep seam distance
    informational; new boards use `end_anchor_required` for that purpose.
    """
    text = str(transition or "").strip()
    if _is_relay_transition(text):
        return True
    if text:
        return False
    return bool(need_endframe)


def seam_strictness(intent: Optional[Dict[str, Any]]) -> str:
    """Only continuous_take_relay makes cross-frame similarity blocking."""
    if intent is None:
        return "strict"
    if intent.get("model_handled"):
        return "model_handled"
    mode = normalize_seam_mode(
        intent.get("seam_mode"), intent.get("transition"),
        need_endframe=bool(intent.get("relay")),
    ).get("mode")
    if intent.get("relay") or requires_boundary_frame(mode):
        return "strict"
    if mode or str(intent.get("transition") or "").strip():
        return "info"
    return "strict"


def load_seam_intents(root: Path, episode: str) -> Dict[int, Dict[str, Any]]:
    """clip 序号 → P-3 continuity_chain 分类；storyboard 仅作 legacy fallback。"""
    chain_path = root / "脚本" / episode / "continuity_chain.json"
    try:
        chain = json.loads(chain_path.read_text(encoding="utf-8"))
    except Exception:
        chain = {}
    out: Dict[int, Dict[str, Any]] = {}
    if isinstance(chain, dict):
        for seam in chain.get("seams") or []:
            if not isinstance(seam, dict):
                continue
            if seam.get("scope") == "episode_boundary" or (
                seam.get("from_episode") and str(seam.get("from_episode")) != episode
            ):
                continue
            idx = clip_index(str(seam.get("from_clip") or ""))
            if idx is None:
                continue
            mode_info = normalize_seam_mode(seam.get("seam_mode"), seam.get("transition"))
            mode = str(mode_info.get("mode") or "")
            out[idx] = {
                "transition": seam.get("transition"),
                "seam_mode": mode,
                "seam_evidence": seam.get("seam_evidence") or {},
                "relay": requires_boundary_frame(mode),
                "source": "continuity_chain",
            }
    if not out:
        path = root / "脚本" / episode / "storyboard.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
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
            transition = cont.get("transition")
            need_end = bool(clip.get("need_endframe") or cont.get("need_endframe")
                            or clip.get("need_end_frame") or cont.get("need_end_frame"))
            mode_info = normalize_seam_mode(cont.get("seam_mode"), transition, need_endframe=need_end)
            mode = str(mode_info.get("mode") or "")
            out[idx] = {
                "transition": transition,
                "seam_mode": mode,
                "seam_evidence": cont.get("seam_evidence") or {},
                "relay": requires_boundary_frame(mode),
                "source": "storyboard" if mode_info.get("source") == "explicit" else "storyboard_legacy",
            }
    # Native multi-shot co-generation owns seams inside an activated group.  The
    # seam is still measured, but a large frame distance is informational rather
    # than proof that a first/last-frame relay failed (there was no relay).
    plan_path = root / "出视频" / episode / "prompt" / "multishot_plan.json"
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception:
        plan = {}
    handled = {str(x) for x in (plan.get("model_handled_seams") or [])} if plan.get("active") else set()
    handled_numbers = {clip_index(value) for value in handled}
    for idx, intent in out.items():
        if idx + 1 in handled_numbers:
            intent["model_handled"] = True
    return out


def machine_check(payload: Dict[str, Any], context_frames: Optional[Dict[int, Dict[str, str]]] = None,
                  seam_intents: Optional[Dict[int, Dict[str, Any]]] = None,
                  clip_scenes: Optional[Dict[int, str]] = None) -> None:
    """就地加接缝机检；只有 continuous_take_relay 的跨帧相似度会阻断。

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
        idx = item_clip_index(item)
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
                    "transition": (intent or {}).get("transition"),
                    "seam_mode": (intent or {}).get("seam_mode"),
                    "strictness": strictness})
        if strictness in {"info", "model_handled"} and chk["verdict"] != "ok":
            # 非 relay 的设计切镜允许换构图；距离只记录，不拿错标准拦验收。
            chk["verdict_if_relay"] = chk["verdict"]
            chk["verdict"] = "info"
            # 同场景软档（2026-07 实跑痛点回修·衔接不一致）：hard_cut 允许换构图，但**同一场景**
            # 相邻镜的灯光/色温应连贯——实证 EP1 全部 10 个接缝被降 info 放行，其中 3 个同场景
            # 色距 0.169-0.258 超 SEAM_COLOR_WARN(0.12)，观感即"换相机换调色"。构图距离仍 info，
            # 只对色距超标升 warn（有意断裂在 intentional_discontinuity manifest 登记后不罚）。
            if (strictness == "info" and clip_scenes
                    and clip_scenes.get(n) and clip_scenes.get(n) == clip_scenes.get(m)
                    and not (intent or {}).get("intentional_discontinuity")):
                cdist = chk.get("color_dist")
                if isinstance(cdist, (int, float)) and cdist > tc.SEAM_COLOR_WARN:
                    chk["verdict"] = "warn"
                    chk["same_scene_color_jump"] = True
        seams.append(chk)
    if skipped and not checked:
        notes.append("缺 Pillow——接缝机检跳过，交人判 contact sheet。")
    if seam_intents is None and checked:
        notes.append("continuity_chain/storyboard 接缝分类不可用——全部接缝保守按 relay 严格判，先回 P-2/P-3 补 seam_mode。")
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


def load_clip_scenes(root: Path, episode: str) -> Dict[int, str]:
    """clip 序号 → location/scene id。同场景硬切接缝的光色连贯性检查用。"""
    path = root / "脚本" / episode / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[int, str] = {}
    for clip in (data.get("clips") or data.get("shots") or []):
        if not isinstance(clip, dict):
            continue
        idx = clip_index(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if idx is None:
            continue
        scene = str(clip.get("location_id") or clip.get("scene") or "").strip()
        if scene:
            out[idx] = scene
    return out


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
                    # 镜内首尾双锚可合法承载较大表情弧；这不等于跨镜同帧接力。
                    "double_frame": needs_end_anchor(clip)}
    return out


def load_anchor_intents(root: Path, episode: str) -> Dict[int, Dict[str, Any]]:
    """clip 序号 → storyboard 中段锚帧意图。

    只读 `continuity.anchors[]` / `continuity.midframe`，给出视频后抽帧对账用：
    如果后端声称原生消费中锚，生成视频在相邻采样点不应大幅偏离该锚帧。
    """
    path = root / "脚本" / episode / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[int, Dict[str, Any]] = {}
    for i, clip in enumerate((data.get("clips") or data.get("shots") or []), 1):
        if not isinstance(clip, dict):
            continue
        idx = clip_index(str(clip.get("id") or clip.get("clip") or clip.get("shot") or ""))
        if idx is None:
            idx = i
        cont = clip.get("continuity") if isinstance(clip.get("continuity"), dict) else {}
        raw = cont.get("anchors")
        anchors: List[Dict[str, Any]] = []
        if isinstance(raw, list):
            for a in raw:
                if not isinstance(a, dict):
                    continue
                rel = str(a.get("anchor_png") or "").strip()
                at = a.get("at_sec")
                if rel and isinstance(at, (int, float)):
                    anchors.append({"anchor_png": rel, "at_sec": float(at), "use": a.get("use", "")})
        elif isinstance(cont.get("midframe"), dict):
            mid = cont["midframe"]
            rel = str(mid.get("midframe_png") or "").strip()
            at = mid.get("split_at_sec")
            if rel and isinstance(at, (int, float)):
                anchors.append({"anchor_png": rel, "at_sec": float(at), "use": "midframe"})
        if anchors:
            out[idx] = {"duration": clip.get("duration"), "anchors": anchors}
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

    设计取舍：表情运动本就带结构变化，且近景里运镜/转头也会动 dHash——所以这里是**粗筛**：
    未到重画阈值、双帧接力镜或景别未知时 warn 交人判；已知近景非双帧且远超重画阈值时 block。
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
        idx = item_clip_index(item)
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
        intra.append({
            "clip": item.get("clip") or f"Clip_{idx:02d}",
            "file": item.get("file"),
            "file_clip": item.get("file_clip"),
            "lens": info.get("lens", ""),
            "max_dist": worst,
            "verdict": verdict,
            "double_frame": double_frame,
            "pairs": pairs,
        })
    if checked:
        payload["intra_clips"] = intra
        summary = payload.setdefault("machine_summary", {})
        summary["intra_checked"] = checked
        summary["intra_warns"] = warns
        summary["intra_blocks"] = blocks
        if not have_types:
            notes.append("storyboard 景别不可用——片内身份采样对全部 clip 抽样（可能含非近景）。")


def anchor_adherence_check(payload: Dict[str, Any], root: Path,
                           anchor_intents: Optional[Dict[int, Dict[str, Any]]] = None) -> None:
    """中段锚帧消费对账：storyboard 锚帧 PNG vs 生成视频最近抽帧。

    video_qc 只抽 start/mid/end 三帧，因此这是一道轻量初筛：锚点离三采样点太远时跳过；
    能对上的采样点若与锚帧 dHash/色距大幅偏离，说明后端可能没消费中锚或中段漂移严重。
    """
    intents = anchor_intents or {}
    if not intents:
        return
    notes = payload.setdefault("machine_notes", [])
    tc = _load_temporal_module()
    if tc is None:
        return
    checks: List[Dict[str, Any]] = []
    checked = warns = blocks = skipped = 0
    for item in payload.get("clips", []):
        file_name = str(item.get("file") or "")
        # split relay part 的时间轴是局部段时间，不再直接用原 Clip 的 at_sec 对齐，避免误报。
        if "_part" in Path(file_name).stem:
            continue
        idx = item_clip_index(item)
        if idx is None or idx not in intents:
            continue
        frames = [f for f in item.get("frames", [])
                  if f.get("path") and not f.get("error") and Path(f["path"]).exists()]
        if not frames:
            continue
        duration = item.get("duration_sec")
        if not isinstance(duration, (int, float)):
            duration = intents[idx].get("duration")
        tolerance = max(0.75, float(duration or 0) * 0.22)
        for anchor in intents[idx].get("anchors") or []:
            at_sec = float(anchor.get("at_sec") or 0)
            nearest = min(frames, key=lambda f: abs(float(f.get("time_sec") or 0) - at_sec))
            delta = abs(float(nearest.get("time_sec") or 0) - at_sec)
            if delta > tolerance:
                skipped += 1
                continue
            rel = str(anchor.get("anchor_png") or "")
            anchor_path = Path(rel) if Path(rel).is_absolute() else root / rel
            if not anchor_path.is_file():
                skipped += 1
                checks.append({
                    "clip": item.get("clip") or f"Clip_{idx:02d}",
                    "file": item.get("file"),
                    "anchor_png": rel,
                    "at_sec": at_sec,
                    "sample_label": nearest.get("label"),
                    "sample_time_sec": nearest.get("time_sec"),
                    "verdict": "skip",
                    "reason": "anchor_png_missing",
                })
                continue
            chk = tc.seam_pair_check(str(anchor_path), str(nearest["path"]))
            if chk is None:
                skipped += 1
                continue
            verdict = chk.get("verdict", "warn")
            checked += 1
            if verdict == "block":
                blocks += 1
            elif verdict == "warn":
                warns += 1
            checks.append({
                "clip": item.get("clip") or f"Clip_{idx:02d}",
                "file": item.get("file"),
                "anchor_png": rel,
                "at_sec": at_sec,
                "sample_label": nearest.get("label"),
                "sample_time_sec": nearest.get("time_sec"),
                "sample_delta_sec": round(delta, 3),
                "dist": chk.get("dist"),
                "color_dist": chk.get("color_dist"),
                "verdict": verdict,
            })
    if checked or skipped:
        payload["anchor_checks"] = checks
        summary = payload.setdefault("machine_summary", {})
        summary["anchor_checked"] = checked
        summary["anchor_warns"] = warns
        summary["anchor_blocks"] = blocks
        summary["anchor_skipped"] = skipped
        if skipped:
            notes.append("部分中段锚帧离 start/mid/end 三采样点太远或 PNG 缺失，锚帧消费对账跳过；必要时加密抽帧复核。")


def production_dir(root: Path) -> Path:
    return root / "生产数据"


def video_dir(root: Path, episode: str) -> Path:
    return root / "出视频" / episode / "视频"


def clip_index(path_or_name: str) -> Optional[int]:
    match = CLIP_RE.search(Path(path_or_name).name)
    return int(match.group(1)) if match else None


def clip_label_from_index(idx: Optional[int], fallback: str) -> str:
    return f"Clip_{idx:02d}" if idx else fallback


def item_clip_index(item: Dict[str, Any]) -> Optional[int]:
    for key in ("clip", "manifest_clip", "story_clip", "file"):
        value = str(item.get(key) or "")
        idx = clip_index(value)
        if idx is not None:
            return idx
    return None


def infer_clip_keys(clips: Sequence[Path]) -> List[Optional[str]]:
    """Infer physical QC labels when no manifest labels are supplied.

    If filenames contain duplicate logical numbers, such as
    Clip01_x.mp4 + Clip01_x_mid.mp4, the filename number is only a source-image
    hint, not a physical segment id.  In that case assign labels by batch order
    so frames and QC rows do not collapse.
    """
    indices = [clip_index(p.name) for p in clips]
    numbered = [i for i in indices if i is not None]
    if numbered and len(numbered) != len(set(numbered)):
        return [f"Clip_{i:02d}" for i, _ in enumerate(clips, 1)]
    return [None for _ in clips]


def frame_prefix(path: Path, clip_label: Optional[str] = None) -> str:
    raw = clip_label or clip_label_from_index(clip_index(path.name), path.stem)
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", raw).strip("_") or "clip"
    digest = hashlib.sha1(path.name.encode("utf-8")).hexdigest()[:8]
    return f"{safe}_{digest}"


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
    files = sorted(
        (p for p in video_dir(root, episode).glob("Clip*.mp4") if "noaudio" not in p.name and "_noaudio" not in p.name),
        key=lambda p: (clip_index(p.name) or 10**9, p.name),
    )
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


def probe_video(path: Path, clip_label: Optional[str] = None) -> Dict[str, Any]:
    file_idx = clip_index(path.name)
    label_idx = clip_index(clip_label or "")
    label = clip_label or clip_label_from_index(file_idx, path.stem)
    if shutil.which("ffprobe") is None:
        return {
            "path": str(path),
            "file": path.name,
            "clip": label,
            "file_clip": clip_label_from_index(file_idx, path.stem),
            "clip_index": label_idx or file_idx,
            "error": "ffprobe not found",
            "has_audio": None,
        }
    data = _run_json([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,width,height,codec_name,avg_frame_rate",
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
        "clip": label,
        "file_clip": clip_label_from_index(file_idx, path.stem),
        "clip_index": label_idx or file_idx,
        "duration_sec": duration,
        "width": video_stream.get("width"),
        "height": video_stream.get("height"),
        "fps": _parse_fps(video_stream.get("avg_frame_rate")),
        "video_codec": video_stream.get("codec_name"),
        "audio_streams": [s for s in streams if s.get("codec_type") == "audio"],
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "probe_error": data.get("error"),
    }


def _parse_fps(value: Any) -> Optional[float]:
    """ffprobe avg_frame_rate（如 '30000/1001'）→ 浮点 fps；不可解析返回 None。"""
    text = str(value or "").strip()
    if not text or text == "0/0":
        return None
    if "/" in text:
        num, _, den = text.partition("/")
        try:
            n, d = float(num), float(den)
            return round(n / d, 3) if d else None
        except ValueError:
            return None
    try:
        return round(float(text), 3)
    except ValueError:
        return None


def delivery_consistency_check(payload: Dict[str, Any]) -> None:
    """批内交付一致性：帧率/分辨率混批此前完全没人查——混帧率片子会静默进 compose，
    被 [1/6] 的强制 fps=30 掩盖（重复帧/丢帧），混分辨率会触发隐性缩放糊边。
    以批内众数为基准，偏离者记 warn（advisory，不改 gate 口径；阻断仍归 n2d-review gate）。"""
    clips = [c for c in payload.get("clips", []) if not c.get("probe_error")]
    notes = payload.setdefault("machine_notes", [])
    summary = payload.setdefault("machine_summary", {})
    findings: List[Dict[str, Any]] = []

    def _mode(values):
        vals = [v for v in values if v is not None]
        if not vals:
            return None
        return max(set(vals), key=vals.count)

    res_mode = _mode([(c.get("width"), c.get("height")) for c in clips
                      if c.get("width") and c.get("height")])
    fps_mode = _mode([round(c["fps"]) for c in clips if isinstance(c.get("fps"), (int, float))])
    for c in clips:
        res = (c.get("width"), c.get("height"))
        if res_mode and all(res) and res != res_mode:
            findings.append({"clip": c.get("clip"), "kind": "resolution",
                             "value": f"{res[0]}x{res[1]}", "expected": f"{res_mode[0]}x{res_mode[1]}"})
        fps = c.get("fps")
        if fps_mode and isinstance(fps, (int, float)) and round(fps) != fps_mode:
            findings.append({"clip": c.get("clip"), "kind": "fps",
                             "value": fps, "expected": fps_mode})
    payload["delivery_consistency"] = {
        "resolution_mode": f"{res_mode[0]}x{res_mode[1]}" if res_mode else None,
        "fps_mode": fps_mode,
        "findings": findings,
    }
    summary["delivery_mismatch_warns"] = len(findings)
    for f in findings:
        notes.append(f"交付一致性 warn：{f['clip']} {f['kind']}={f['value']}（批内众数 {f['expected']}）——"
                     "混帧率/混分辨率进 compose 会被静默规格化掩盖，先确认该 clip 是否该重出。")


def sample_times(duration: Optional[float]) -> List[Tuple[str, float]]:
    if duration is None or duration <= 0:
        return [("start", 0.0), ("mid", 1.0), ("end", 2.0)]
    end = max(0.0, duration - min(0.2, duration / 10.0))
    return [("start", 0.0), ("mid", duration / 2.0), ("end", end)]


def source_version_key(path: Path) -> str:
    """Cheap immutable-enough key for one on-disk video version.

    Full MP4 hashing on every single-clip accept is expensive.  Size + nanosecond
    mtime changes whenever the runner replaces a formal clip, while the basename
    keeps the store inspectable.  The key is persisted only in a filename and
    never as an absolute project path.
    """
    try:
        stat = path.stat()
        raw = f"{path.name}:{stat.st_size}:{stat.st_mtime_ns}"
    except OSError:
        raw = path.name
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def extract_frames(path: Path, frames_dir: Path, duration: Optional[float],
                   clip_label: Optional[str] = None) -> List[Dict[str, Any]]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{frame_prefix(path, clip_label)}_{source_version_key(path)}"
    outputs: List[Dict[str, Any]] = []
    if shutil.which("ffmpeg") is None:
        return [{"label": label, "time_sec": t, "error": "ffmpeg not found"} for label, t in sample_times(duration)]
    for ordinal, (label, ts) in enumerate(sample_times(duration), 1):
        out = frames_dir / f"{prefix}_{ordinal:02d}_{label}.jpg"
        if out.is_file() and out.stat().st_size > 0:
            outputs.append({"label": label, "time_sec": round(ts, 3), "path": str(out), "cache_hit": True})
            continue
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


def shared_frames_dir(root: Path, episode: str) -> Path:
    return production_dir(root) / "video_qc" / episode / "_frames"


def portable_value(value: Any, root: Path) -> Any:
    """Convert persisted project-local paths to root-relative strings."""
    if isinstance(value, str):
        path = Path(value)
        if path.is_absolute():
            try:
                return path.resolve().relative_to(root.resolve()).as_posix()
            except (OSError, ValueError):
                return value
        return value
    if isinstance(value, list):
        return [portable_value(item, root) for item in value]
    if isinstance(value, dict):
        return {key: portable_value(item, root) for key, item in value.items()}
    return value


def migrate_legacy_frames(root: Path, episode: str) -> Dict[str, Any]:
    """Deduplicate old per-batch frame copies without losing report references."""
    base = production_dir(root) / "video_qc" / episode
    store = shared_frames_dir(root, episode)
    legacy = [
        path for path in sorted(base.glob("*/frames/*.jpg"))
        if path.is_file() and path.parent.parent.name != "_frames"
    ] if base.is_dir() else []
    if not legacy:
        return {"kind": "n2d_video_qc_frame_migration", "episode": episode, "moved": 0, "deduplicated": 0, "rewritten_reports": 0}
    store.mkdir(parents=True, exist_ok=True)
    replacements: Dict[str, str] = {}
    moved = deduplicated = 0
    for src in legacy:
        digest = hashlib.sha256(src.read_bytes()).hexdigest()
        dst = store / f"legacy_{digest[:20]}.jpg"
        if dst.is_file():
            src.unlink()
            deduplicated += 1
        else:
            shutil.move(str(src), str(dst))
            moved += 1
        replacements[str(src)] = dst.relative_to(root).as_posix()
        try:
            replacements[src.relative_to(root).as_posix()] = dst.relative_to(root).as_posix()
        except ValueError:
            pass
    def rewrite_value(value: Any) -> Tuple[Any, bool]:
        if isinstance(value, str):
            replacement = replacements.get(value)
            return (replacement, True) if replacement is not None else (value, False)
        if isinstance(value, list):
            changed = False
            items = []
            for item in value:
                new_item, item_changed = rewrite_value(item)
                items.append(new_item)
                changed = changed or item_changed
            return items, changed
        if isinstance(value, dict):
            changed = False
            data = {}
            for key, item in value.items():
                new_item, item_changed = rewrite_value(item)
                data[key] = new_item
                changed = changed or item_changed
            return data, changed
        return value, False

    rewritten = 0
    for report in sorted(base.glob("*/*.json")):
        try:
            data = json.loads(report.read_text(encoding="utf-8"))
        except Exception:
            continue
        data, changed = rewrite_value(data)
        if changed:
            tmp = report.with_name(f"{report.name}.tmp.{os.getpid()}")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(tmp, report)
            rewritten += 1
    for directory in sorted(base.glob("*/frames")):
        try:
            directory.rmdir()
        except OSError:
            pass
    return {
        "kind": "n2d_video_qc_frame_migration",
        "episode": episode,
        "moved": moved,
        "deduplicated": deduplicated,
        "rewritten_reports": rewritten,
        "frame_store": store.relative_to(root).as_posix(),
    }


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
    present = {item_clip_index(i) for i in payload.get("clips", [])}
    present.discard(None)
    wanted = ({n - 1 for n in present} | {n + 1 for n in present}) - present
    out: Dict[int, Dict[str, str]] = {}
    vdir = video_dir(root, episode)
    if not vdir.is_dir():
        return out
    for k in sorted(w for w in wanted if isinstance(w, int) and w > 0):
        matches = [p for p in list(vdir.glob(f"Clip_{k:02d}*.mp4")) + list(vdir.glob(f"Clip{k:02d}*.mp4"))
                   if "noaudio" not in p.name and "_noaudio" not in p.name]
        if not matches:
            continue
        clip_label = f"Clip_{k:02d}"
        meta = probe_video(matches[0], clip_label=clip_label)
        frames = extract_frames(matches[0], frames_dir, meta.get("duration_sec"), clip_label=clip_label)
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
        "| Clip | Source MP4 | Duration | Size | FPS | Audio | Frames | Notes |",
        "|---|---|---:|---|---:|---|---:|---|",
    ]
    for item in payload["clips"]:
        dur = item.get("duration_sec")
        duration = f"{dur:.3f}s" if isinstance(dur, (int, float)) else "?"
        size = f"{item.get('width') or '?'}x{item.get('height') or '?'}"
        audio = "yes" if item.get("has_audio") else ("unknown" if item.get("has_audio") is None else "no")
        frame_count = sum(1 for f in item.get("frames", []) if f.get("path") and not f.get("error"))
        notes = item.get("probe_error") or "; ".join(f.get("error", "") for f in item.get("frames", []) if f.get("error"))
        fps = item.get("fps")
        fps_text = f"{fps:g}" if isinstance(fps, (int, float)) else "?"
        lines.append(f"| {item.get('clip') or '-'} | `{item.get('file')}` | {duration} | {size} | {fps_text} | {audio} | {frame_count} | {notes or ''} |")
    summary = payload.get("machine_summary") or {}
    seams = payload.get("seams") or []
    lines.append("")
    lines.append("## Seam machine check（按 seam_mode 分类；仅 relay 同帧阻断）")
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
            lines.append("| Clip | Source MP4 | Lens | Max dHash | Verdict |")
            lines.append("|---|---|---|---:|---|")
            for s in intra:
                lines.append(f"| {s.get('clip')} | `{s.get('file') or '-'}` | {s.get('lens') or '-'} | {s.get('max_dist')} | {s.get('verdict')} |")
    anchors = payload.get("anchor_checks") or []
    if summary.get("anchor_checked") or summary.get("anchor_skipped"):
        lines.append("")
        lines.append("## Anchor adherence（中段锚帧消费对账 · storyboard anchor vs generated sample）")
        lines.append("")
        lines.append(f"- checked: {summary.get('anchor_checked', 0)}"
                     f" · block: {summary.get('anchor_blocks', 0)} · warn: {summary.get('anchor_warns', 0)}"
                     f" · skipped: {summary.get('anchor_skipped', 0)}")
        flagged = [a for a in anchors if a.get("verdict") not in ("ok", "skip")]
        if flagged:
            lines.append("")
            lines.append("| Clip | Anchor | Sample | Δs | dHash | Color dist | Verdict |")
            lines.append("|---|---|---|---:|---:|---:|---|")
            for a in flagged:
                lines.append(
                    f"| {a.get('clip')} | `{a.get('anchor_png')}` | {a.get('sample_label')}@{a.get('sample_time_sec')} "
                    f"| {a.get('sample_delta_sec')} | {a.get('dist')} | "
                    f"{a.get('color_dist') if a.get('color_dist') is not None else '-'} | {a.get('verdict')} |"
                )
    lines.append("")
    lines.append("Status: pending human review unless the batch manifest marks it accepted.")
    return "\n".join(lines) + "\n"


def run_qc(root: Path, episode: str, clips: Sequence[Path], batch: str,
           out_dir: Optional[Path] = None, clip_keys: Optional[Sequence[Optional[str]]] = None,
           force_intra_all: bool = False) -> Dict[str, Any]:
    custom_out = out_dir is not None
    if out_dir is None:
        out_dir = production_dir(root) / "video_qc" / episode / batch
    migration = migrate_legacy_frames(root, episode)
    frames_dir = (out_dir / "frames") if custom_out else shared_frames_dir(root, episode)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "kind": "n2d_video_qc",
        "version": 1,
        "root": str(root),
        "episode": episode,
        "batch": batch,
        "frame_store": str(frames_dir),
        "frame_migration": migration,
        "clips": [],
    }
    all_frames: List[Path] = []
    if clip_keys is not None and len(clip_keys) != len(clips):
        raise ValueError("clip_keys length must match clips length")
    labels = list(clip_keys) if clip_keys is not None else infer_clip_keys(clips)
    for clip, clip_label in zip(clips, labels):
        meta = probe_video(clip, clip_label=clip_label)
        frames = extract_frames(clip, frames_dir, meta.get("duration_sec"), clip_label=meta.get("clip"))
        meta["frames"] = frames
        payload["clips"].append(meta)
        all_frames.extend(Path(f["path"]) for f in frames if f.get("path") and Path(f["path"]).exists())
    contact = make_contact_sheet(all_frames, out_dir / f"contact_sheet_{batch}.jpg")
    payload["contact_sheet"] = contact
    machine_check(payload, neighbor_context_frames(root, episode, payload, frames_dir),
                  load_seam_intents(root, episode) or None,
                  load_clip_scenes(root, episode) or None)
    intra_clip_check(payload, None if force_intra_all else (load_shot_types(root, episode) or None))
    anchor_adherence_check(payload, root, load_anchor_intents(root, episode) or None)
    delivery_consistency_check(payload)
    json_path = out_dir / f"video_qc_{episode}_{batch}.json"
    if custom_out:
        md_path = out_dir / f"video_qc_{episode}_{batch}.md"
    else:
        md_path = production_dir(root) / "views" / "video_qc" / episode / f"video_qc_{episode}_{batch}.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
    persisted = portable_value(payload, root)
    persisted["root"] = "."
    json_path.write_text(json.dumps(persisted, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    ap.add_argument("--migrate-legacy-frames", action="store_true",
                    help="only consolidate old per-batch frames into the shared store")
    ap.add_argument("--json", action="store_true", help="Print machine-readable payload")
    ns = ap.parse_args(argv)

    root = Path(ns.root).expanduser().resolve()
    if ns.migrate_legacy_frames:
        payload = migrate_legacy_frames(root, ns.episode)
        if ns.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(payload.get("frame_store") or "no legacy frames")
        return 0
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
