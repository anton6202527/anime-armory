#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check image-to-video inheritance for MV jobs.

The video stage should inherit identity, references, style anchors, first/end
frames, and continuity from clip_plan/image prompts. This script writes a
deterministic receipt before spending more video credits or composing.
"""
import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
MV_UTILS_PATH = os.path.join(REPO, "skills", "mv-craft", "scripts", "mv_utils.py")
MV_LIB = os.path.join(REPO, "skills", "mv", "_lib")
if MV_LIB not in sys.path:
    sys.path.insert(0, MV_LIB)
from mv_video_prompt_compiler import (  # noqa: E402
    KIND as COMPILER_KIND,
    VERSION as COMPILER_VERSION,
    lint as lint_compiled_prompt,
    normalize_backend,
    parse_markdown,
)


def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv_utils = load_mv_utils()


def text_contains_all(text, needles):
    missing = []
    for needle in needles:
        if needle and str(needle) not in text:
            missing.append(str(needle))
    return missing


def load_inputs(root):
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    jobs = mv_utils.load_json(os.path.join(root, "出视频", "jobs_manifest.json"), {}) or {}
    identity = mv_utils.load_json(os.path.join(root, "设定", "identity_registry.json"), {}) or {}
    refs = mv_utils.load_json(os.path.join(root, "分镜", "reference_plan.json"), {}) or {}
    return plan, jobs, identity, refs


def reference_lookup(reference_plan):
    return {c.get("clip_id"): c for c in reference_plan.get("clips", []) if isinstance(c, dict)}


def prompt_text(root, rel):
    if not rel:
        return ""
    return mv_utils.read_text(os.path.join(root, rel))


def check_compiled_prompt(text, take, expected_backend):
    parsed = parse_markdown(text or "")
    if not parsed:
        return [{
            "level": "block", "code": "missing_compiled_submit_prompt",
            "message": "完整 MV 合同不得直接作为模型 prompt",
        }]
    findings = []
    if parsed.get("kind") != COMPILER_KIND or parsed.get("version") != COMPILER_VERSION:
        findings.append({
            "level": "block", "code": "incompatible_prompt_compiler",
            "actual": {"kind": parsed.get("kind"), "version": parsed.get("version")},
        })
    source_hash = str(parsed.get("source_contract_sha256") or "")
    if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        findings.append({"level": "block", "code": "invalid_prompt_source_hash"})
    if expected_backend and normalize_backend(parsed.get("backend")) != normalize_backend(expected_backend):
        findings.append({
            "level": "block", "code": "prompt_backend_mismatch",
            "compiled": parsed.get("backend"), "expected": expected_backend,
        })
    for code in lint_compiled_prompt(parsed)["errors"]:
        findings.append({"level": "block", "code": "compiled_prompt_lint", "lint_code": code})
    for code in lint_compiled_prompt(parsed)["warnings"]:
        findings.append({"level": "warn", "code": "compiled_prompt_lint", "lint_code": code})
    if take.get("prompt_source_kind") != "compiled_submit_prompt":
        findings.append({"level": "block", "code": "manifest_prompt_source_kind_invalid"})
    if str(take.get("submit_prompt") or "") != str(parsed.get("prompt") or ""):
        findings.append({"level": "block", "code": "manifest_submit_prompt_mismatch"})
    if str(take.get("source_contract_sha256") or "") != source_hash:
        findings.append({"level": "block", "code": "manifest_source_contract_hash_mismatch"})
    return findings


def check_clip(root, clip, job, ref_row, identity_registry):
    cid = clip.get("clip_id")
    findings = []
    c = clip.get("continuity") or {}
    ident = clip.get("identity_contract") or {}
    required_clip_fields = [
        ("image_path", clip.get("image_path")),
        ("continuity.start_state", c.get("start_state")),
        ("continuity.action", c.get("action")),
        ("continuity.end_state", c.get("end_state")),
        ("continuity.constraints", c.get("constraints")),
        ("continuity.negative", c.get("negative")),
        ("continuity.identity_state", c.get("identity_state")),
        ("continuity.wardrobe_state", c.get("wardrobe_state")),
        ("continuity.prop_state", c.get("prop_state")),
        ("continuity.scene_topology", c.get("scene_topology")),
        ("continuity.screen_direction", c.get("screen_direction")),
        ("continuity.eyeline", c.get("eyeline")),
        ("continuity.motion_vector", c.get("motion_vector")),
        ("continuity.lighting_state", c.get("lighting_state")),
        ("identity_contract.lead_identity_anchor", ident.get("lead_identity_anchor")),
        ("shot_design.camera_movement", (clip.get("shot_design") or {}).get("camera_movement")),
        ("shot_design.lighting", (clip.get("shot_design") or {}).get("lighting")),
    ]
    for field, value in required_clip_fields:
        if value in (None, "", []):
            findings.append({"level": "block", "code": "missing_clip_contract_field", "field": field})

    image_path = clip.get("image_path")
    if image_path and not os.path.exists(os.path.join(root, image_path)):
        findings.append({"level": "block", "code": "missing_first_frame", "path": image_path})
    if clip.get("need_end_frame"):
        end_path = clip.get("end_frame_path")
        if not end_path or not os.path.exists(os.path.join(root, end_path)):
            findings.append({"level": "block", "code": "missing_end_frame", "path": end_path})

    if not job:
        findings.append({"level": "block", "code": "missing_video_job"})
        return findings

    take_prompts = []
    for take in job.get("takes", []):
        rel = take.get("prompt_path")
        take_prompts.append((take.get("take_id"), rel, prompt_text(root, rel)))
    if not take_prompts:
        findings.append({"level": "block", "code": "missing_take_prompts"})

    required_text = [
        clip.get("image_path"),
        c.get("action"),
        c.get("start_state"),
        c.get("end_state"),
        (clip.get("shot_design") or {}).get("camera_movement"),
        (clip.get("shot_design") or {}).get("lighting"),
    ]
    anchor = ident.get("lead_identity_anchor")
    if anchor:
        required_text.append(anchor.split("·")[0])
    for take_id, rel, text in take_prompts:
        if not text:
            findings.append({"level": "block", "code": "missing_prompt_file", "take_id": take_id, "path": rel})
            continue
        missing = text_contains_all(text, required_text)
        if missing:
            findings.append({
                "level": "warn",
                "code": "prompt_missing_inherited_terms",
                "take_id": take_id,
                "path": rel,
                "missing": missing[:8],
            })
        for marker in ("首帧", "continuity", "声音约束"):
            if marker not in text:
                findings.append({"level": "warn", "code": "prompt_missing_marker", "take_id": take_id, "marker": marker})
        take = next((row for row in job.get("takes", []) if row.get("take_id") == take_id), {})
        for finding in check_compiled_prompt(text, take, job.get("video_model") or job.get("backend")):
            finding.setdefault("take_id", take_id)
            finding.setdefault("path", rel)
            findings.append(finding)

    if ref_row:
        planned_refs = ref_row.get("reference_inputs") or []
        job_refs = job.get("reference_inputs") or []
        if planned_refs and not job_refs:
            findings.append({"level": "warn", "code": "job_missing_reference_inputs"})
    elif identity_registry:
        findings.append({"level": "warn", "code": "missing_reference_plan_row"})
    return findings


def build_report(root):
    plan, manifest, identity, reference_plan = load_inputs(root)
    plan_clips = plan.get("clips") or []
    jobs = {j.get("clip_id"): j for j in manifest.get("jobs", []) if isinstance(j, dict)}
    refs = reference_lookup(reference_plan)
    rows = []
    hard_blocks = 0
    warnings = 0
    for clip in plan_clips:
        cid = clip.get("clip_id")
        findings = check_clip(root, clip, jobs.get(cid), refs.get(cid), identity)
        hard_blocks += sum(1 for f in findings if f.get("level") == "block")
        warnings += sum(1 for f in findings if f.get("level") == "warn")
        rows.append({"clip_id": cid, "findings": findings, "verdict": "block" if any(f.get("level") == "block" for f in findings) else ("review" if findings else "ok")})
    input_paths = ("分镜/clip_plan.json", "出视频/jobs_manifest.json", "设定/identity_registry.json", "分镜/reference_plan.json")
    report = {
        "schema_version": 2,
        "kind": "mv_video_inherit_contract",
        "generated_at": date.today().isoformat(),
        "root": root,
        "inputs": {
            "clip_plan": "分镜/clip_plan.json",
            "jobs_manifest": "出视频/jobs_manifest.json",
            "identity_registry": "设定/identity_registry.json",
            "reference_plan": "分镜/reference_plan.json",
        },
        "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in input_paths},
        "summary": {
            "clips": len(plan_clips),
            "hard_blocks": hard_blocks,
            "warnings": warnings,
            "verdict": "block" if hard_blocks else ("review" if warnings else "ok"),
        },
        "clips": rows,
    }
    return report


def write_report(root, report):
    out_dir = os.path.join(root, "生产数据", "video_inherit_contract")
    mv_utils.write_json(os.path.join(out_dir, "inherit_contract.json"), report)
    lines = [
        "# video inherit contract",
        "",
        f"- verdict: {report['summary']['verdict']}",
        f"- clips: {report['summary']['clips']}",
        f"- hard_blocks: {report['summary']['hard_blocks']}",
        f"- warnings: {report['summary']['warnings']}",
        "",
    ]
    for row in report.get("clips", []):
        lines.append(f"## {row.get('clip_id')} · {row.get('verdict')}")
        for f in row.get("findings", []):
            lines.append(f"- {f.get('level')}: {f.get('code')} {json.dumps({k:v for k,v in f.items() if k not in {'level','code'}}, ensure_ascii=False)}")
        if not row.get("findings"):
            lines.append("- ok")
        lines.append("")
    mv_utils.write_text(os.path.join(out_dir, "inherit_contract.md"), "\n".join(lines))
    return os.path.join(out_dir, "inherit_contract.json")


def main():
    ap = argparse.ArgumentParser(description="Check MV image-to-video inheritance contract")
    ap.add_argument("project_root")
    ap.add_argument("--no-fail", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = build_report(root)
    path = write_report(root, report)
    print(f"[ok] inherit contract → {path} ({report['summary']['verdict']})")
    if report["summary"]["hard_blocks"] and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
