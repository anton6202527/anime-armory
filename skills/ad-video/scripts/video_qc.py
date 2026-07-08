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
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set


KIND = "ad_video_qc"
PROD_RE = re.compile(r"\bPROD_[A-Za-z0-9_]*\b")
BRAND_RE = re.compile(r"\bBRAND_[A-Za-z0-9_]*\b")
TEXT_MARKERS = ("文字", "slogan", "CTA", "cta", "legal", "法律声明", "字幕", "立即", "预约", "购买", "下载")
TEXT_LOCK = ("清晰", "可读", "不乱码", "不要乱码", "准确显示", "保留原文")
PRODUCT_LOCK_TEXT = ("同一包装", "同一 logo", "同一logo", "同一品牌色", "产品参考", "资产引用")
SEAM_MARKERS = ("接缝", "首尾", "尾帧", "首帧", "end frame", "first frame", "seam")
CAP_SUBJECT_LOCK = "subject_consistency"


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
                           "产品/品牌/CTA clip 缺 8x8 安全区声明，多比例 reframe 可能裁切核心信息。"))
    elif isinstance(safe, Mapping) and safe.get("core_in_center_4x4") is False:
        out.append(finding("block", clip, "safe_area", "safe_area.core_in_center_4x4=false，核心资产不在中心安全区。"))
    return out


def seam_findings(root: Path, clip: str, shot: Mapping[str, Any], index: int, total: int) -> List[Dict[str, Any]]:
    if index >= total:
        return []
    transition = str(shot.get("continuity", {}).get("transition") if isinstance(shot.get("continuity"), Mapping) else shot.get("transition") or "")
    text = read_text(prompt_path(root, clip)) + "\n" + shot_text(shot)
    if not transition and not any(mark in text for mark in SEAM_MARKERS):
        return [finding("warn", clip, "seam_contract",
                        "非末尾 clip 缺接缝/尾帧/transition 声明；合成时可能出现跳变。")]
    return []


def run_qc(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    findings: List[Dict[str, Any]] = []
    routes = route_by_clip(root)
    jobs = video_job_by_clip(root)
    shots = storyboard_shots(root)
    if not shots:
        findings.append(finding("block", "-", "storyboard", "缺 storyboard clips/shots，无法验收视频。"))
    for index, shot in enumerate(shots, start=1):
        clip = clip_id(shot, index)
        findings.extend(clip_presence_findings(root, clip, jobs.get(clip)))
        findings.extend(route_findings(clip, shot, routes.get(clip)))
        findings.extend(prompt_handoff_findings(root, clip, shot))
        findings.extend(seam_findings(root, clip, shot, index, len(shots)))
    inheritance = load_json(root / "出视频" / "分镜" / "contract_inheritance.json")
    if not inheritance:
        findings.append(finding("warn", "-", "contract_inheritance", "缺 contract_inheritance.json，建议先跑 ad-video/scripts/inherit_contract.py。"))
    else:
        blocks = int(((inheritance.get("summary") or {}).get("block")) or 0)
        if blocks:
            findings.append(finding("block", "-", "contract_inheritance", f"契约继承仍有 block={blocks}，不能进入合成。"))
    payload = {
        "schema_version": 1,
        "kind": KIND,
        "project_root": str(root),
        "summary": summarize(findings),
        "findings": findings,
        "qc_environment": {
            "precision_level": "structural",
            "note": "baseline structural QC; pixel frame drift checks can be added with ffmpeg/Pillow later",
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
