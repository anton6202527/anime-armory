#!/usr/bin/env python3
"""Produce high-dynamic video QC evidence for n2d spectacle clips.

This is a lightweight producer.  It does not run optical flow, pose tracking,
VLM, or embedding models by itself.  It builds a deterministic evidence packet
from storyboard contracts, route/control manifests, generated media presence,
and optional external measurements.  The packet is consumed by
consistency_audit.py and can also write the existing MOT1/CAM1/S2V sidecars.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

SCRIPT_DIR = os.path.dirname(__file__)
LIB = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d", "_lib"))
if LIB not in sys.path:
    sys.path.insert(0, LIB)

from n2d_contract import (  # noqa: E402
    ACTION_CHOREOGRAPHY_SHOT_TYPES,
    SPECTACLE_QC_DIMENSIONS,
    SPECTACLE_VIDEO_QC_KIND,
    high_flow_sampling_plan,
    infer_spectacle_type,
    motion_control_inputs_for_spectacle,
    spectacle_qc_dimension_status,
)

# 动作关键新增维（本轮补的、之前流水线没有的机检）——测了别的维但这几维仍空时，单独提示。
ACTION_CRITICAL_NEW_DIMS = ("optical_flow_direction", "limb_artifact", "motion_blur_plausibility")
from video_consistency_common import existing_media, finding, load_json, rows_from  # noqa: E402


ACTION_KINDS = set(ACTION_CHOREOGRAPHY_SHOT_TYPES)
CHAR_RE = re.compile(r"\bCHAR_[A-Za-z0-9_]+\b")
ASSET_RE = re.compile(r"\b(?:LOC|PROP|WEAPON|OUTFIT|VFX|BEAST|MOUNT|VEHICLE)_[A-Za-z0-9_]+\b")


def ep_label(value: str) -> str:
    return value if value.startswith("第") else f"第{value}集"


def make_clip_id(clip: Mapping[str, Any], idx: int) -> str:
    raw = str(clip.get("clip_id") or clip.get("id") or clip.get("label") or "").strip()
    m = re.search(r"(?:Clip[_\s-]?|CLIP)(\d+)", raw, re.I)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    m = re.search(r"(\d+)", raw)
    if m:
        return f"Clip_{int(m.group(1)):02d}"
    return f"Clip_{idx:02d}"


def _flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(_flatten_text(v) for v in value.values())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return " ".join(_flatten_text(v) for v in value)
    return str(value)


def _contract_for(clip: Mapping[str, Any], kind: str) -> Dict[str, Any]:
    if kind == "large_establishing":
        for key in ("large_scene_contract", "spectacle_contract", "template_contract"):
            value = clip.get(key)
            if isinstance(value, dict):
                return dict(value)
        return {}
    value = clip.get("template_contract")
    return dict(value) if isinstance(value, dict) else {}


def _has(record: Mapping[str, Any], *keys: str) -> bool:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return True
    return False


def _text(record: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, "", [], {}):
            return _flatten_text(value).strip()
    return ""


def _clip_media(media: Sequence[str], clip_id: str) -> List[str]:
    token = clip_id.lower().replace("_", "")
    digits = re.sub(r"\D", "", clip_id)
    out = []
    for path in media:
        name = os.path.basename(path).lower().replace("_", "")
        if token in name or (digits and re.search(rf"(?:clip|镜头)?0*{re.escape(digits)}\b", name)):
            out.append(path)
    return out


def _control_manifest(root: Path, ep: str, clip_id: str) -> Dict[str, Any]:
    path = root / "出视频" / ep / "control" / clip_id / "motion_control_manifest.json"
    data = load_json(str(path))
    if isinstance(data, dict):
        data["_rel_path"] = os.path.relpath(path, root)
        return data
    return {"_rel_path": os.path.relpath(path, root), "status": "missing", "control_inputs": {}}


def _control_degrade_only(manifest: Mapping[str, Any]) -> bool:
    """Top-level degrade_only is an accepted control path, not missing evidence."""
    if str(manifest.get("status") or "").strip() != "degrade_only":
        return False
    plan = manifest.get("degrade_plan")
    return plan not in (None, "", [], {})


def _ready_controls(manifest: Mapping[str, Any]) -> List[str]:
    inputs = manifest.get("control_inputs")
    if not isinstance(inputs, Mapping):
        return []
    out = []
    for key, spec in inputs.items():
        if isinstance(spec, Mapping) and str(spec.get("status") or "") in {"ready", "not_needed"}:
            out.append(str(key))
    return sorted(out)


def _external_checks(root: Path, ep: str) -> Dict[str, Dict[str, Any]]:
    """Merge optional external measured reports by clip_id.

    Heavy runners can write any of these reports before this producer runs.  We
    only use rows with evidence_status/measurement_status measured-like values
    or explicit metrics; all other rows stay advisory.
    """
    out: Dict[str, Dict[str, Any]] = {}
    rels = (
        root / "生产数据" / f"motion_quality_{ep}.json",
        root / "生产数据" / f"camera_trajectory_probe_{ep}.json",
        root / "生产数据" / f"subject_video_consistency_{ep}.json",
        root / "生产数据" / f"temporal_consistency_{ep}.json",
        # 本轮新增维（光流方向对账/肢体畸变/运动模糊）由专门的动作-artifact runner 写入此 sidecar。
        root / "生产数据" / f"spectacle_motion_artifacts_{ep}.json",
    )
    for path in rels:
        data = load_json(str(path))
        if data is None:
            continue
        for row in rows_from(data, ("checks", "items", "results", "shots", "segments", "subjects")):
            cid = make_clip_id({"id": row.get("clip") or row.get("clip_id") or row.get("shot")}, 0)
            out.setdefault(cid, {}).update(row)
    return out


def _evidence_status(has_media: bool, external: Mapping[str, Any]) -> str:
    raw = str(external.get("evidence_status") or external.get("measurement_status") or "").strip().lower()
    if raw in {"measured", "external_report", "vlm_verified", "tracked"}:
        return raw
    if any(k in external for k in ("motion_smoothness", "trajectory_error", "subject_fidelity", "parallax_flow_score")):
        return "measured"
    return "contract_only" if has_media else "pending_video"


def build_report(root: Path, ep: str) -> Dict[str, Any]:
    storyboard = load_json(str(root / "脚本" / ep / "storyboard.json"))
    if not isinstance(storyboard, dict):
        raise FileNotFoundError(f"storyboard not found: {root / '脚本' / ep / 'storyboard.json'}")
    clips = storyboard.get("clips") or []
    if not isinstance(clips, list):
        raise ValueError("storyboard.json clips must be a list")
    media = existing_media(str(root), ep)
    external = _external_checks(root, ep)
    checks: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    for idx, clip in enumerate(clips, 1):
        if not isinstance(clip, dict):
            continue
        kind = infer_spectacle_type(clip)
        if not kind:
            continue
        clip_id = make_clip_id(clip, idx)
        contract = _contract_for(clip, kind)
        blob = json.dumps(clip, ensure_ascii=False)
        clip_media = _clip_media(media, clip_id)
        manifest = _control_manifest(root, ep, clip_id)
        ext = external.get(clip_id, {})
        evidence_status = _evidence_status(bool(clip_media), ext)
        required_controls = list(motion_control_inputs_for_spectacle(kind))
        ready_controls = _ready_controls(manifest)
        control_degrade_only = _control_degrade_only(manifest)
        missing_controls = [] if control_degrade_only else [key for key in required_controls if key not in ready_controls]
        required_evidence: List[str] = []
        if kind in ACTION_KINDS:
            required_evidence.extend(["speed_curve", "spatial_path"])
        if kind == "fight_exchange":
            required_evidence.extend(["impact_frame", "contact_map"])
        if kind == "chase":
            required_evidence.extend(["distance_curve", "screen_direction", "parallax_flow"])
        if kind == "flight":
            required_evidence.extend(["altitude_curve", "parallax_flow", "pose_lock"])
        if kind == "large_establishing":
            required_evidence.extend(["landmark_anchor", "scale_reference", "parallax_flow", "scene_layer_pack"])
        present_evidence = {
            "speed_curve": _has(contract, "speed_curve", "velocity_curve"),
            "spatial_path": _has(contract, "spatial_path", "flight_path"),
            "distance_curve": _has(contract, "distance_curve"),
            "screen_direction": _has(contract, "screen_direction"),
            "impact_frame": _has(contract, "impact_frame"),
            "contact_map": "contact_map" in ready_controls or _has(ext, "contact_map", "contact_map_verified"),
            "altitude_curve": _has(contract, "altitude_curve", "altitude_path"),
            "parallax_flow": _has(contract, "parallax_layers", "parallax_planes") or _has(ext, "parallax_flow", "parallax_flow_score"),
            "pose_lock": _has(contract, "pose_lock", "mount_or_cloud_lock"),
            "landmark_anchor": _has(contract, "landmark_anchor"),
            "scale_reference": _has(contract, "scale_reference"),
            "scene_layer_pack": _has(contract, "reuse_asset_id") or _has(ext, "scene_layer_pack"),
        }
        missing_evidence = [key for key in required_evidence if not present_evidence.get(key)]
        row = {
            "clip": clip_id,
            "spectacle_type": kind,
            "evidence_status": evidence_status,
            "media": [os.path.relpath(p, root) for p in clip_media],
            "characters": sorted(set(CHAR_RE.findall(blob))),
            "assets": sorted(set(ASSET_RE.findall(blob))),
            "required_controls": required_controls,
            "ready_controls": ready_controls,
            "missing_controls": missing_controls,
            "control_status": manifest.get("status"),
            "control_degrade_plan": manifest.get("degrade_plan") if control_degrade_only else "",
            "required_evidence": required_evidence,
            "missing_evidence": missing_evidence,
            "speed_curve": _text(contract, "speed_curve"),
            "spatial_path": _text(contract, "spatial_path", "flight_path"),
            "distance_curve": _text(contract, "distance_curve"),
            "altitude_curve": _text(contract, "altitude_curve", "altitude_path"),
            "camera_path": _text(contract, "camera_path"),
            "impact_frame": _text(contract, "impact_frame"),
            "parallax_flow": ext.get("parallax_flow") or ext.get("parallax_flow_score") or _text(contract, "parallax_layers", "parallax_planes"),
            "subject_sample_points": ["start", "mid", "end"] if CHAR_RE.search(blob) else [],
            "control_manifest": manifest.get("_rel_path"),
            # 八维成片 QC：每维 verified/unverified（external sidecar 命中 evidence_key 即 verified）。
            "qc_dimensions": spectacle_qc_dimension_status(ext),
            # 高光流帧重点采样契约：供 out-of-repo 重模型 runner 在动作峰值加密抽帧。
            "sampling_plan": high_flow_sampling_plan(kind, clip.get("duration") or 0),
        }
        row.update({k: v for k, v in ext.items() if k not in row and v not in (None, "", [], {})})
        if evidence_status in {"contract_only", "pending_video"}:
            findings.append(finding(
                "warn",
                f"{clip_id} {kind} 只有{evidence_status}证据；高动态成片需要抽帧/光流/姿态/VLM 或人工回读证明动作、路径和主体保持成立。",
                shot=clip_id,
                stage="video",
                artifacts=(f"生产数据/spectacle_video_qc_{ep}.json", row["control_manifest"]),
                evidence_status=evidence_status,
            ))
        if missing_controls and evidence_status != "pending_video":
            findings.append(finding(
                "warn",
                f"{clip_id} {kind} 缺 Motion Control ready 输入：{', '.join(missing_controls)}。",
                shot=clip_id,
                stage="video",
                artifacts=(row["control_manifest"],),
            ))
        if missing_evidence and evidence_status != "pending_video":
            findings.append(finding(
                "warn",
                f"{clip_id} {kind} 缺高动态后验证据字段：{', '.join(missing_evidence)}。",
                shot=clip_id,
                stage="video",
                artifacts=(f"生产数据/spectacle_video_qc_{ep}.json",),
            ))
        # 动作关键新维（光流方向对账/肢体畸变/运动模糊）：有成片且已测了别的维，但这几维仍空——
        # 这是过去流水线根本没有的机检，单独提示去跑动作-artifact runner（见 references/动作镜QC机检.md）。
        qc_status = row["qc_dimensions"]
        unverified_new = [d for d in ACTION_CRITICAL_NEW_DIMS if qc_status.get(d) != "verified"]
        if kind in ACTION_KINDS and clip_media and evidence_status != "pending_video" and unverified_new:
            findings.append(finding(
                "warn",
                f"{clip_id} {kind} 动作关键维未实测：{', '.join(unverified_new)}（光流方向对账/肢体畸变/运动模糊）。"
                "按 sampling_plan 在动作峰值帧加密抽帧，跑动作-artifact runner 写 "
                f"生产数据/spectacle_motion_artifacts_{ep}.json。",
                shot=clip_id,
                stage="video",
                artifacts=(f"生产数据/spectacle_video_qc_{ep}.json",),
                evidence_status=evidence_status,
            ))
        checks.append(row)
    return {
        "kind": SPECTACLE_VIDEO_QC_KIND,
        "version": 1,
        "root": str(root),
        "episode": ep,
        "checks": checks,
        "findings": findings,
        "summary": {
            "spectacle_clips": len(checks),
            "clips_with_media": sum(1 for row in checks if row.get("media")),
            "measured_clips": sum(1 for row in checks if row.get("evidence_status") in {"measured", "external_report", "vlm_verified", "tracked"}),
            "contract_only_clips": sum(1 for row in checks if row.get("evidence_status") == "contract_only"),
            "pending_video_clips": sum(1 for row in checks if row.get("evidence_status") == "pending_video"),
            "warn_findings": len([f for f in findings if f.get("verdict") == "warn"]),
            "block_findings": len([f for f in findings if f.get("verdict") == "block"]),
            "qc_dimensions": [d["key"] for d in SPECTACLE_QC_DIMENSIONS],
            "qc_dimension_verified_clips": {
                d["key"]: sum(1 for row in checks if (row.get("qc_dimensions") or {}).get(d["key"]) == "verified")
                for d in SPECTACLE_QC_DIMENSIONS
            },
        },
        "notes": [
            "This producer is standard-library only. Heavy optical-flow/pose/VLM runners should update evidence_status to measured/external_report and add numeric metrics.",
        ],
    }


def _motion_sidecar(report: Mapping[str, Any]) -> Dict[str, Any]:
    rows = []
    for row in report.get("checks") or []:
        if not isinstance(row, Mapping):
            continue
        rows.append({
            "clip": row.get("clip"),
            "high_action": row.get("spectacle_type") in ACTION_KINDS,
            "expected_motion": row.get("spectacle_type"),
            "evidence_status": row.get("evidence_status"),
            "speed_curve": row.get("speed_curve"),
            "spatial_path": row.get("spatial_path"),
            "distance_curve": row.get("distance_curve"),
            "altitude_curve": row.get("altitude_curve"),
            "impact_frame": row.get("impact_frame"),
            "parallax_flow": row.get("parallax_flow"),
            "action_completion": row.get("action_completion"),
        })
    return {"checks": rows, "generated_by": "spectacle_video_qc", "evidence_contract": "measured required for final pass"}


def _camera_sidecar(report: Mapping[str, Any]) -> Dict[str, Any]:
    rows = []
    for row in report.get("checks") or []:
        if not isinstance(row, Mapping):
            continue
        rows.append({
            "clip": row.get("clip"),
            "evidence_status": row.get("evidence_status"),
            "camera_path": row.get("camera_path"),
            "spatial_path": row.get("spatial_path"),
            "trajectory_error": row.get("trajectory_error"),
            "axis_flip": row.get("axis_flip"),
            "jitter_score": row.get("jitter_score"),
        })
    return {"checks": rows, "generated_by": "spectacle_video_qc", "evidence_contract": "measured required for final pass"}


def _subject_sidecar(report: Mapping[str, Any]) -> Dict[str, Any]:
    rows = []
    for row in report.get("checks") or []:
        if not isinstance(row, Mapping):
            continue
        for char in row.get("characters") or []:
            rows.append({
                "clip": row.get("clip"),
                "subject": char,
                "category": "character",
                "evidence_status": row.get("evidence_status"),
                "subject_fidelity": row.get("subject_fidelity"),
                "text_relevance": row.get("text_relevance"),
                "multi_subject_swap": row.get("multi_subject_swap"),
            })
    return {"checks": rows, "generated_by": "spectacle_video_qc", "evidence_contract": "measured required for final pass"}


def write_report(report: Mapping[str, Any], root: Path, ep: str, *, sidecars: bool = False) -> Dict[str, Path]:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    out = prod / f"spectacle_video_qc_{ep}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    paths: Dict[str, Path] = {"spectacle": out}
    if sidecars:
        sidecar_specs = {
            "motion": (prod / f"motion_quality_{ep}.json", _motion_sidecar(report)),
            "camera": (prod / f"camera_trajectory_probe_{ep}.json", _camera_sidecar(report)),
            "subject": (prod / f"subject_video_consistency_{ep}.json", _subject_sidecar(report)),
        }
        for key, (path, data) in sidecar_specs.items():
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            paths[key] = path
    return paths


def analyze(root: str, ep: str) -> Dict[str, Any]:
    path = Path(root) / "生产数据" / f"spectacle_video_qc_{ep}.json"
    data = load_json(str(path))
    if isinstance(data, dict):
        return {"available": True, "findings": data.get("findings") or [], "notes": data.get("notes") or [], "summary": data.get("summary") or {}}
    return {"available": False, "findings": [], "notes": ["未找到 spectacle_video_qc sidecar；高动态成片证据检查跳过。"], "summary": {}}


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="build n2d spectacle video QC evidence packet")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--write-sidecars", action="store_true", help="also write motion_quality/camera_trajectory/subject_video sidecars")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root.rstrip("/"))
    ep = ep_label(ns.episode)
    report = build_report(root, ep)
    if ns.write or ns.write_sidecars:
        paths = write_report(report, root, ep, sidecars=ns.write_sidecars)
        report["written"] = {k: str(v) for k, v in paths.items()}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report.get("summary", {}).get("block_findings") else 0


if __name__ == "__main__":
    raise SystemExit(main())
