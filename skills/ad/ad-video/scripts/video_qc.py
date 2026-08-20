#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad-video post-generation QC.

Runs after image-to-video clips are generated and before ad-compose.  The gate
is scoped to advertising: product/logo/brand lock, prompt handoff, route
capability, safe area, text legibility, clip presence, and seam declarations.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

CRAFT_SCRIPTS = Path(__file__).resolve().parents[2] / "ad-craft" / "scripts"
if str(CRAFT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CRAFT_SCRIPTS))
import render_profile as ad_render_profile  # noqa: E402


KIND = "ad_video_qc"
PROD_RE = re.compile(r"\bPROD_[A-Za-z0-9_]*\b")
BRAND_RE = re.compile(r"\bBRAND_[A-Za-z0-9_]*\b")
TEXT_MARKERS = ("文字", "slogan", "CTA", "cta", "legal", "法律声明", "字幕", "立即", "预约", "购买", "下载")
TEXT_LOCK = ("清晰", "可读", "不乱码", "不要乱码", "准确显示", "保留原文")
PRODUCT_LOCK_TEXT = ("同一包装", "同一 logo", "同一logo", "同一品牌色", "产品参考", "资产引用")
SEAM_MARKERS = ("接缝", "首尾", "尾帧", "首帧", "end frame", "first frame", "seam")
CAP_SUBJECT_LOCK = "subject_consistency"
# 同场景相邻镜色跳（归一化平均色距，dHash 抓结构抓不住调色/白平衡跳变）；批内混帧率容差。
SEAM_COLOR_WARN = 0.12
BATCH_FPS_TOL = 0.05


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def finding(severity: str, clip: str, check: str, reason: str, detail: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"severity": severity, "clip": clip, "check": check, "reason": reason, "detail": detail or {}}


def summarize(findings: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    out = {"block": 0, "warn": 0, "info": 0}
    for item in findings:
        sev = item.get("severity")
        if sev in out:
            out[sev] += 1
    return out


def storyboard_shots(root: Path) -> List[Mapping[str, Any]]:
    sb = load_json(root / "脚本" / "storyboard.json", {}) or {}
    raw = sb.get("shots") or sb.get("clips") or []
    return [s for s in raw if isinstance(s, Mapping)]


def clip_id(shot: Mapping[str, Any], index: int) -> str:
    raw = str(shot.get("shot_id") or shot.get("clip_id") or shot.get("id") or shot.get("clip") or "").strip()
    m = re.search(r"(\d+)", raw)
    if m:
        return f"镜头{int(m.group(1)):02d}"
    return raw or f"镜头{index:02d}"


def shot_text(shot: Mapping[str, Any]) -> str:
    parts = []
    for key in ("scene", "shot", "frame", "prompt", "desc", "description", "product_lock"):
        value = shot.get(key)
        if isinstance(value, str):
            parts.append(value)
    return " ".join(parts)


def prod_assets(shot: Mapping[str, Any]) -> Set[str]:
    ids: Set[str] = set()
    assets = shot.get("assets")
    if isinstance(assets, Mapping):
        ids.update(str(k) for k, v in assets.items() if v and PROD_RE.fullmatch(str(k)))
    elif isinstance(assets, (list, tuple)):
        ids.update(str(x) for x in assets if PROD_RE.fullmatch(str(x)))
    ids.update(PROD_RE.findall(shot_text(shot)))
    return ids


def brand_assets(shot: Mapping[str, Any]) -> Set[str]:
    ids: Set[str] = set()
    assets = shot.get("assets")
    if isinstance(assets, Mapping):
        ids.update(str(k) for k, v in assets.items() if v and BRAND_RE.fullmatch(str(k)))
    elif isinstance(assets, (list, tuple)):
        ids.update(str(x) for x in assets if BRAND_RE.fullmatch(str(x)))
    ids.update(BRAND_RE.findall(shot_text(shot)))
    return ids


def expected_video_path(root: Path, clip: str) -> Path:
    folder = root / "出视频" / "分镜" / "视频"
    candidates = [folder / f"{clip}.mp4", folder / f"{clip.replace('镜头', 'shot')}.mp4"]
    m = re.search(r"(\d+)", clip)
    if m:
        candidates.append(folder / f"Clip_{int(m.group(1)):02d}.mp4")
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def prompt_path(root: Path, clip: str) -> Path:
    folder = root / "出视频" / "分镜" / "prompt"
    m = re.search(r"(\d+)", clip)
    if m:
        n = int(m.group(1))
        for name in (f"镜头{n:02d}.md", f"镜头{n}.md", f"shot{n}.md", f"Clip_{n:02d}.md"):
            path = folder / name
            if path.exists():
                return path
    return folder / f"{clip}.md"


def route_by_clip(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出视频" / "分镜" / "prompt" / "video_model_routes.json", {}) or {}
    routes = data.get("routes") if isinstance(data, Mapping) else []
    return {str(r.get("clip")): r for r in routes if isinstance(r, Mapping)}


def video_job_by_clip(root: Path) -> Dict[str, Mapping[str, Any]]:
    data = load_json(root / "出视频" / "分镜" / "video_jobs_manifest.json", {}) or {}
    jobs = data.get("jobs") if isinstance(data, Mapping) else []
    if not isinstance(jobs, list):
        jobs = []
    return {
        str(job.get("clip") or job.get("job_id")): job
        for job in jobs
        if isinstance(job, Mapping) and (job.get("clip") or job.get("job_id"))
    }


def clip_presence_findings(root: Path, clip: str, job: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    path = expected_video_path(root, clip)
    if not path.exists():
        if job and job.get("submit_id"):
            return [finding(
                "block", clip, "clip_presence",
                "出视频 clip 已提交远端但尚未回收下载，不能进入合成。",
                {
                    "path": str(path),
                    "submit_id": job.get("submit_id"),
                    "status": job.get("status"),
                    "pending_status": job.get("pending_status"),
                },
            )]
        return [finding("block", clip, "clip_presence", "缺出视频 clip 文件，不能进入合成。", {"path": str(path)})]
    try:
        size = path.stat().st_size
    except OSError:
        size = 0
    if size <= 0:
        return [finding("block", clip, "clip_presence", "clip 文件为空，疑生成失败。", {"path": str(path), "bytes": size})]
    return []


def _probe(path: Path) -> Dict[str, Any]:
    exe = shutil.which("ffprobe")
    if not exe or not path.is_file():
        return {}
    proc = subprocess.run([exe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                          capture_output=True, text=True)
    try:
        return json.loads(proc.stdout) if proc.returncode == 0 else {}
    except json.JSONDecodeError:
        return {}


def _seconds(value: Any) -> float:
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group()) if m else 0.0


def _fps(video_stream: Mapping[str, Any]) -> Optional[float]:
    for key in ("avg_frame_rate", "r_frame_rate"):
        raw = str(video_stream.get(key) or "")
        if "/" in raw:
            num, _, den = raw.partition("/")
            try:
                if float(den) > 0:
                    return round(float(num) / float(den), 2)
            except ValueError:
                pass
        else:
            try:
                return round(float(raw), 2) if raw else None
            except ValueError:
                pass
    return None


def technical_findings(root: Path, clip: str, shot: Mapping[str, Any]) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    path = expected_video_path(root, clip)
    data = _probe(path)
    if not data:
        return [finding("block", clip, "ffprobe", "clip 无法用 ffprobe 读取，不能只凭文件非空验收")], None
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        return [finding("block", clip, "video_stream", "clip 缺有效视频流")], None
    out = []
    actual = _seconds((data.get("format") or {}).get("duration"))
    expected = _seconds(next((shot.get(k) for k in ("duration", "duration_sec", "seconds", "时长") if shot.get(k) is not None), 0))
    if expected and abs(actual - expected) > max(0.35, expected * 0.08):
        out.append(finding("block", clip, "duration", f"实测 {actual:.3f}s 与镜头目标 {expected:.3f}s 不符"))
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        out.append(finding("block", clip, "resolution", "clip 分辨率无效"))
    return out, {"fps": _fps(video), "width": width, "height": height}


def batch_consistency_findings(tech_facts: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """批内混帧率/混分辨率检查：合成会强制统一参数而静默掩盖差异，须在验收面显式抬出。"""
    out: List[Dict[str, Any]] = []
    fps_map = {c: f["fps"] for c, f in tech_facts.items() if f and f.get("fps")}
    if len(fps_map) >= 2:
        counts: Dict[float, int] = {}
        for value in fps_map.values():
            counts[value] = counts.get(value, 0) + 1
        mode = max(counts, key=lambda v: (counts[v], -v))
        odd = {c: v for c, v in fps_map.items() if abs(v - mode) > BATCH_FPS_TOL}
        if odd:
            out.append(finding(
                "warn", "-", "batch_fps_mix",
                f"批内混帧率：多数 clip 为 {mode}fps，异常 {sorted(odd)}；合成强制统一帧率会静默掩盖来源差异，先确认再进合成。",
                {"mode_fps": mode, "outliers": {c: v for c, v in sorted(odd.items())}},
            ))
    res_map = {c: (f["width"], f["height"]) for c, f in tech_facts.items()
               if f and f.get("width") and f.get("height")}
    if len(res_map) >= 2:
        counts2: Dict[tuple, int] = {}
        for value in res_map.values():
            counts2[value] = counts2.get(value, 0) + 1
        mode2 = max(counts2, key=lambda v: (counts2[v], v))
        odd2 = {c: v for c, v in res_map.items() if v != mode2}
        if odd2:
            out.append(finding(
                "warn", "-", "batch_resolution_mix",
                f"批内混分辨率：多数 clip 为 {mode2[0]}x{mode2[1]}，异常 {sorted(odd2)}；缩放统一前先确认来源与清晰度损失。",
                {"mode_resolution": list(mode2), "outliers": {c: list(v) for c, v in sorted(odd2.items())}},
            ))
    return out


def render_profile_source_findings(root: Path, tech_facts: Mapping[str, Mapping[str, Any]],
                                   jobs: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Compare every observed clip with source_generation, not with its peers."""
    path = root / "生产数据" / "render_profile.json"
    if not path.is_file():
        return []  # legacy diagnostic projects; formal stage acceptance fails closed separately
    profile = load_json(path, {}) or {}
    current = ad_render_profile.compile_profile(root)
    if (not profile.get("profile_sha256")
            or profile.get("profile_sha256") != current.get("profile_sha256")):
        return [finding("block", "-", "render_profile_source_stale",
                        "render_profile 未绑定当前设置/brief/platform pack；须先重建 route/job。")]
    source = profile.get("source_generation") if isinstance(profile.get("source_generation"), Mapping) else {}
    expected = (int(source.get("width") or 0), int(source.get("height") or 0))
    expected_fps = float(source.get("fps") or 0)
    out: List[Dict[str, Any]] = []
    if profile.get("kind") != "ad_render_profile" or not all((*expected, expected_fps)):
        return [finding("block", "-", "render_profile_source_invalid",
                        "render_profile 缺有效 source_generation，无法核对真实回收媒体。")]
    for clip, facts in tech_facts.items():
        if not facts:
            out.append(finding("block", clip, "observed_source_unverified", "clip 缺 ffprobe 实测规格。"))
            continue
        observed = (int(facts.get("width") or 0), int(facts.get("height") or 0))
        observed_fps = float(facts.get("fps") or 0)
        if observed != expected:
            out.append(finding(
                "block", clip, "observed_source_resolution_mismatch",
                f"实测 {observed[0]}x{observed[1]}，未兑现 source_generation={expected[0]}x{expected[1]}；"
                "请求值不能冒充实际输出。",
            ))
        if not observed_fps or abs(observed_fps - expected_fps) > 0.15:
            out.append(finding(
                "block", clip, "observed_source_fps_mismatch",
                f"实测 {observed_fps:g}fps，未兑现 source_generation={expected_fps:g}fps。",
            ))
        job = jobs.get(clip) if isinstance(jobs.get(clip), Mapping) else {}
        receipt = job.get("observed_output") if isinstance(job.get("observed_output"), Mapping) else {}
        if job and (int(receipt.get("width") or 0), int(receipt.get("height") or 0)) != observed:
            out.append(finding("block", clip, "observed_source_receipt_stale",
                               "job observed_output 与本次 ffprobe 结果不一致。"))
        if job and abs(float(receipt.get("fps") or 0) - observed_fps) > 0.01:
            out.append(finding("block", clip, "observed_source_receipt_stale",
                               "job observed_output FPS 与本次 ffprobe 结果不一致。"))
    return out


def _load_imaging():
    try:
        from PIL import Image, ImageDraw  # type: ignore
        return Image, ImageDraw
    except Exception:
        return None, None


def _extract_frame(video: Path, at: float, out: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([ffmpeg, "-y", "-ss", f"{max(0, at):.3f}", "-i", str(video), "-frames:v", "1", str(out)],
                          capture_output=True, text=True)
    return proc.returncode == 0 and out.is_file()


def _dhash(path: Path, Image) -> Optional[int]:
    try:
        im = Image.open(path).convert("L").resize((9, 8))
        px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
        bits = 0
        for y in range(8):
            for x in range(8):
                bits = (bits << 1) | (1 if px[y * 9 + x] < px[y * 9 + x + 1] else 0)
        return bits
    except Exception:
        return None


def _ham(a: Optional[int], b: Optional[int]) -> Optional[int]:
    return None if a is None or b is None else (a ^ b).bit_count()


def visual_sample_findings(root: Path, clip: str, shot: Mapping[str, Any], Image) -> tuple[List[Dict[str, Any]], List[Path]]:
    path = expected_video_path(root, clip)
    duration = _seconds((_probe(path).get("format") or {}).get("duration"))
    if not duration:
        return [], []
    out_dir = root / "出视频" / "分镜" / "qc_frames"
    points = {"start": min(0.05, duration / 10), "mid": duration / 2, "end": max(0, duration - 0.08)}
    frames = []
    for name, at in points.items():
        target = out_dir / f"{clip}_{name}.png"
        if _extract_frame(path, at, target):
            frames.append(target)
    out = []
    source = root / "出图" / "分镜" / "图片" / f"{clip}.png"
    if source.is_file() and frames:
        dist = _ham(_dhash(source, Image), _dhash(frames[0], Image))
        if dist is not None and dist > 24:
            out.append(finding("warn", clip, "start_frame_drift",
                               f"视频首采样与输入首帧 dHash 差 {dist}bit；启发式仅提示人工复核，不硬挡",
                               {"source": str(source), "sample": str(frames[0]), "confidence": "heuristic"}))
    if prod_assets(shot) and len(frames) >= 3:
        hashes = [_dhash(p, Image) for p in frames]
        drift = max((_ham(hashes[0], h) or 0) for h in hashes[1:])
        if drift > 26:
            out.append(finding("warn", clip, "within_clip_product_drift",
                               f"产品镜 start/mid/end 全帧 dHash 最大漂移 {drift}bit；需看 contact sheet 复核包装/Logo",
                               {"samples": [str(p) for p in frames], "confidence": "heuristic"}))
    return out, frames


def write_contact_sheet(root: Path, samples: List[Path], Image, ImageDraw) -> Optional[str]:
    if not samples:
        return None
    thumbs = []
    for path in samples:
        try:
            im = Image.open(path).convert("RGB")
            im.thumbnail((320, 180))
            thumbs.append((path, im.copy()))
        except Exception:
            pass
    if not thumbs:
        return None
    sheet = Image.new("RGB", (320 * min(3, len(thumbs)), 215 * ((len(thumbs) + 2) // 3)), "white")
    draw = ImageDraw.Draw(sheet)
    for idx, (path, im) in enumerate(thumbs):
        x, y = (idx % 3) * 320, (idx // 3) * 215
        sheet.paste(im, (x, y))
        draw.text((x + 4, y + 184), path.stem, fill="black")
    out = root / "出视频" / "分镜" / "video_qc_contact_sheet.jpg"
    sheet.save(out, quality=88)
    return str(out)


def route_findings(clip: str, shot: Mapping[str, Any], route: Optional[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    if not prod_assets(shot):
        return []
    if not route:
        return [finding("block", clip, "route_subject_lock", "产品镜缺 video_model_routes 路由记录，无法证明使用主体一致性后端。")]
    if route.get("capability") != CAP_SUBJECT_LOCK:
        return [finding("block", clip, "route_subject_lock",
                        "产品镜未路由到主体一致性能力后端，包装/logo 在 image2video 阶段高风险抖花。",
                        {"capability": route.get("capability"), "primary": route.get("primary")})]
    return []


def prompt_handoff_findings(root: Path, clip: str, shot: Mapping[str, Any]) -> List[Dict[str, Any]]:
    path = prompt_path(root, clip)
    text = read_text(path)
    out: List[Dict[str, Any]] = []
    products = prod_assets(shot)
    if products:
        if not text:
            out.append(finding("block", clip, "prompt_product_lock", "产品镜缺视频 prompt，无法继承产品身份锁。", {"path": str(path)}))
        elif not (any(pid in text for pid in products) or any(mark in text for mark in PRODUCT_LOCK_TEXT)):
            out.append(finding("block", clip, "prompt_product_lock",
                               "产品镜视频 prompt 丢失 PROD_* 或“同一包装/同一 logo/同一品牌色”锁定句。",
                               {"path": str(path), "products": sorted(products)}))
    combined = text + "\n" + shot_text(shot)
    if any(mark in combined for mark in TEXT_MARKERS) and not any(mark in combined for mark in TEXT_LOCK):
        out.append(finding("warn", clip, "text_legibility",
                           "本 clip 含品牌/UI/CTA/法律文字，但视频 prompt/storyboard 未明确文字清晰可读/不乱码。",
                           {"path": str(path)}))
    safe = shot.get("safe_area") or shot.get("安全区") or {}
    if (products or brand_assets(shot) or any(mark in combined for mark in ("CTA", "cta", "片尾", "logo"))) and not safe:
        out.append(finding("warn", clip, "safe_area",
                           "产品/品牌/CTA clip 缺构图余量声明，跨版位适配可能损失核心信息；仍须按实际 placement 模板和适配模式人审。"))
    elif isinstance(safe, Mapping) and safe.get("core_in_center_4x4") is False:
        out.append(finding("warn", clip, "safe_area",
                           "core_in_center_4x4=false：跨比例裁切风险高；中心网格不是平台安全区，最终按实际 placement 模板人审。"))
    return out


def _seam_declared(root: Path, clip: str, shot: Mapping[str, Any]) -> bool:
    transition = str(shot.get("continuity", {}).get("transition") if isinstance(shot.get("continuity"), Mapping) else shot.get("transition") or "")
    text = read_text(prompt_path(root, clip)) + "\n" + shot_text(shot)
    return bool(transition) or any(mark in text for mark in SEAM_MARKERS)


def seam_findings(root: Path, clip: str, shot: Mapping[str, Any], index: int, total: int) -> List[Dict[str, Any]]:
    if index >= total:
        return []
    if not _seam_declared(root, clip, shot):
        return [finding("warn", clip, "seam_contract",
                        "非末尾 clip 缺接缝/尾帧/transition 声明；合成时可能出现跳变。")]
    return []


def _scene_label(shot: Mapping[str, Any]) -> str:
    return str(shot.get("scene") or shot.get("场景") or "").strip()


def _avg_rgb(path: Path, Image) -> Optional[tuple]:
    try:
        with Image.open(path) as im:
            raw = im.convert("RGB").resize((16, 16)).tobytes()
        n = len(raw) // 3
        return tuple(sum(raw[i::3]) / n for i in range(3))
    except Exception:
        return None


def _color_dist(a: Optional[tuple], b: Optional[tuple]) -> Optional[float]:
    if a is None or b is None:
        return None
    return (sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5) / (255.0 * (3 ** 0.5))


def run_qc(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    findings: List[Dict[str, Any]] = []
    routes = route_by_clip(root)
    jobs = video_job_by_clip(root)
    shots = storyboard_shots(root)
    Image, ImageDraw = _load_imaging()
    all_samples: List[Path] = []
    samples_by_clip: Dict[str, List[Path]] = {}
    tech_facts: Dict[str, Optional[Dict[str, Any]]] = {}
    if not shots:
        findings.append(finding("block", "-", "storyboard", "缺 storyboard clips/shots，无法验收视频。"))
    for index, shot in enumerate(shots, start=1):
        clip = clip_id(shot, index)
        findings.extend(clip_presence_findings(root, clip, jobs.get(clip)))
        if expected_video_path(root, clip).is_file():
            tech, facts = technical_findings(root, clip, shot)
            findings.extend(tech)
            tech_facts[clip] = facts
            if Image is not None:
                sample_findings, samples = visual_sample_findings(root, clip, shot, Image)
                findings.extend(sample_findings)
                all_samples.extend(samples)
                samples_by_clip[clip] = samples
                if len(samples) < 3:
                    findings.append(finding(
                        "block", clip, "frame_sampling",
                        "未能从成片实取 start/mid/end 三帧；不能把视频一致性验收降级为只看合同。",
                        {"sample_count": len(samples)},
                    ))
        findings.extend(route_findings(clip, shot, routes.get(clip)))
        findings.extend(prompt_handoff_findings(root, clip, shot))
        findings.extend(seam_findings(root, clip, shot, index, len(shots)))
    if Image is not None:
        for index in range(len(shots) - 1):
            left = clip_id(shots[index], index + 1)
            right = clip_id(shots[index + 1], index + 2)
            left_samples = samples_by_clip.get(left) or []
            right_samples = samples_by_clip.get(right) or []
            if len(left_samples) >= 3 and right_samples:
                dist = _ham(_dhash(left_samples[-1], Image), _dhash(right_samples[0], Image))
                if dist is not None and dist > 28:
                    findings.append(finding(
                        "warn", f"{left}->{right}", "actual_seam_drift",
                        f"相邻镜头实测尾帧/首帧 dHash 差 {dist}bit；需在 contact sheet 人工确认是否为有意跳切。",
                        {"left_end": str(left_samples[-1]), "right_start": str(right_samples[0]),
                         "confidence": "heuristic"},
                    ))
                # 同场景色跳：dHash 只抓灰度结构，调色/白平衡跳变要靠平均色距抓（兄弟线同口径 0.12）。
                left_shot, right_shot = shots[index], shots[index + 1]
                if _scene_label(left_shot) == _scene_label(right_shot):
                    cdist = _color_dist(_avg_rgb(left_samples[-1], Image), _avg_rgb(right_samples[0], Image))
                    if cdist is not None and cdist > SEAM_COLOR_WARN:
                        declared = _seam_declared(root, left, left_shot)
                        findings.append(finding(
                            "info" if declared else "warn", f"{left}->{right}", "seam_color_jump",
                            f"同场景相邻镜色距 {cdist:.3f} > {SEAM_COLOR_WARN}（尾帧→首帧调色/白平衡跳变）"
                            + ("；该镜已声明转场/接缝，供合成时确认。" if declared else "；未声明转场，合成硬切会露馅，需回看或声明有意断裂。"),
                            {"color_distance": round(cdist, 4), "declared_transition": declared,
                             "confidence": "heuristic"},
                        ))
    findings.extend(batch_consistency_findings({c: f for c, f in tech_facts.items() if f}))
    findings.extend(render_profile_source_findings(
        root, {c: f for c, f in tech_facts.items() if f}, jobs,
    ))
    inheritance = load_json(root / "出视频" / "分镜" / "contract_inheritance.json")
    if not inheritance:
        findings.append(finding("warn", "-", "contract_inheritance", "缺 contract_inheritance.json，建议先跑 ad-video/scripts/inherit_contract.py。"))
    else:
        blocks = int(((inheritance.get("summary") or {}).get("block")) or 0)
        if blocks:
            findings.append(finding("block", "-", "contract_inheritance", f"契约继承仍有 block={blocks}，不能进入合成。"))
    contact_sheet = write_contact_sheet(root, all_samples, Image, ImageDraw) if Image is not None else None
    precision = "full" if shutil.which("ffmpeg") and shutil.which("ffprobe") and Image is not None else "structural"
    payload = {
        "schema_version": 1,
        "kind": KIND,
        "project_root": str(root),
        "summary": summarize(findings),
        "findings": findings,
        "qc_environment": {
            "precision_level": precision,
            "manual_review_accepted": False,
            "contact_sheet": contact_sheet,
            "note": "full=ffprobe + start/mid/end extraction + adjacent seam sampling + contact sheet; heuristic visual drift never auto-BLOCK",
        },
    }
    out = root / "出视频" / "分镜" / "video_qc.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload["_json_path"] = str(out)
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="ad-video post-generation QC")
    ap.add_argument("project_root")
    args = ap.parse_args(argv)
    payload = run_qc(Path(args.project_root))
    s = payload["summary"]
    print(f"# ad-video QC block={s['block']} warn={s['warn']} info={s['info']}")
    for item in payload["findings"]:
        icon = "🔴" if item["severity"] == "block" else ("🟡" if item["severity"] == "warn" else "ℹ️")
        print(f"{icon} [{item['clip']}/{item['check']}] {item['reason']}")
    print(f"[ok] {payload['_json_path']}")
    return 1 if s["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
