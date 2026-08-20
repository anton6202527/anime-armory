#!/usr/bin/env python3
"""Create a hash-bound MV provenance manifest and optional C2PA 2.4 asset.

The JSON provenance ledger is always useful. C2PA embedding is deliberately
fail-closed: production embedding needs an external signer and trust anchors;
the c2patool built-in test certificate is accepted only behind an explicit
development flag and is never reported as trusted.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import glob
import json
import mimetypes
import os
import shutil
import subprocess
import sys
from typing import Any
from urllib.parse import urlparse

import mv_utils


DIGITAL_SOURCE_BASE = "http://cv.iptc.org/newscodes/digitalsourcetype/"
CORE_INPUTS = (
    "_meta.json", "_设置.md", "视觉蓝图.md", "词/lyrics.md", "节拍/beatgrid.json",
    "分镜/clip_plan.json", "分镜/timeline_manifest.json", "分镜/timeline.otio",
    "分镜/semantic_prompts.json", "出视频/jobs_manifest.json",
    "设定/identity_registry.json", "设定/asset_registry.json", "分镜/reference_plan.json",
    "生产数据/image_acceptance/image_acceptance.json",
    "生产数据/image_qc/image_qc.json", "生产数据/video_inherit_contract/inherit_contract.json",
    "生产数据/video_qc/video_qc.json", "字幕/alignment_report.json", "制片/picture_lock.json",
    "生产数据/animatic/animatic.json", "生产数据/otio/otio_receipt.json",
    "生产数据/color/color_input_manifest.json", "评分/pacing_prescore.json",
    "生产数据/delivery_qc/delivery_qc.json",
    "合规/rights_manifest.json", "合规/ai_usage.json",
)
RECEIPT_GLOBS = (
    "生产数据/image_generation/*.json",
    "生产数据/provider_evidence/**/*",
    "出视频/receipts/*.json",
    "出视频/provider_evidence/**/*",
    "出视频/cut_maps/*.json",
)


def _inside(root: str, path: str) -> bool:
    try:
        project = os.path.realpath(root)
        target = os.path.realpath(path)
        return os.path.commonpath((project, target)) == project and target != project
    except ValueError:
        return False


def _required_asset(root: str, raw: str, label: str) -> str:
    path = os.path.abspath(raw if os.path.isabs(raw) else os.path.join(root, raw))
    if not _inside(root, path):
        raise ValueError(f"{label} 必须位于作品根内：{path}")
    if not os.path.isfile(path):
        raise ValueError(f"缺 {label}：{path}")
    return path


def existing_assets(root: str, final: str, master: str | None) -> list[str]:
    rows = [rel for rel in CORE_INPUTS if os.path.isfile(os.path.join(root, rel))]
    for pattern in RECEIPT_GLOBS:
        rows.extend(
            mv_utils.relpath(root, path)
            for path in sorted(glob.glob(os.path.join(root, pattern), recursive=True))
            if os.path.isfile(path)
        )
    song = mv_utils.find_song(root)
    if song:
        rows.append(mv_utils.relpath(root, song))
    for suffix in ("png", "jpg", "jpeg", "webp"):
        rows.extend(
            mv_utils.relpath(root, path)
            for path in sorted(glob.glob(
                os.path.join(root, "出图", "**", f"*.{suffix}"), recursive=True,
            ))
            if os.path.isfile(path)
        )
    rows.extend(
        mv_utils.relpath(root, path)
        for path in sorted(glob.glob(
            os.path.join(root, "出视频", "视频", "**", "*.mp4"), recursive=True,
        ))
        if os.path.isfile(path)
    )
    for path in (final, master):
        if path and os.path.isfile(path):
            rows.append(mv_utils.relpath(root, path))
    return list(dict.fromkeys(rows))


def _mime(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def _disclosure_source_type(ai_usage: dict[str, Any]) -> str:
    modes = {str(ai_usage.get("visual_mode") or ""), str(ai_usage.get("video_mode") or "")}
    if modes & {"AI-generated", "AI-assisted"}:
        return DIGITAL_SOURCE_BASE + "compositeWithTrainedAlgorithmicMedia"
    return DIGITAL_SOURCE_BASE + "composite"


def build_c2pa_manifest(
    *, root: str, final_rel: str, ingredients: list[str], ai_usage: dict[str, Any]
) -> dict[str, Any]:
    ingredient_paths = [
        rel for rel in ingredients if mv_utils.content_hash(os.path.join(root, rel))
    ]
    model_names = [
        str(value) for value in (ai_usage.get("image_model"), ai_usage.get("video_model"))
        if value and value != "未记录"
    ]
    ai_disclosure = {
        # C2PA 2.4 requires modelType; proprietary hosted generators use the
        # generic model type until vendors publish stable model identifiers.
        "modelType": "c2pa.types.model",
        "modelName": "; ".join(model_names) or "undisclosed hosted model",
        "contentProfile": {
            "humanOversightLevel": (
                "human_validated" if str(ai_usage.get("human_contribution") or "").strip()
                else "prompt_guided"
            )
        },
    }
    return {
        "claim_generator": "anime-armory-mv/2",
        "title": os.path.basename(final_rel),
        "format": _mime(final_rel),
        # c2patool turns each real path into a versioned ingredient assertion
        # and binds its bytes. Relative paths keep the sidecar portable.
        "ingredient_paths": ingredient_paths,
        "assertions": [
            {
                "label": "c2pa.actions.v2",
                "data": {"actions": [
                    {
                        "action": "c2pa.created",
                        "digitalSourceType": _disclosure_source_type(ai_usage),
                        "softwareAgent": "anime-armory-mv",
                    },
                    {"action": "c2pa.edited", "softwareAgent": "anime-armory-mv"},
                ]},
            },
            {"label": "c2pa.ai-disclosure", "data": ai_disclosure},
        ],
    }


def _status_code(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("code") or row.get("status") or "").strip()
    return str(row or "").strip()


def _validation_buckets(store: dict[str, Any]) -> dict[str, list[str]]:
    """Read both legacy ``validation_status`` and current result buckets.

    Current c2pa-rs/c2patool emits ``validation_results.activeManifest`` with
    success/informational/failure arrays.  Older readers often expose only a
    top-level ``validation_status`` list of problems.  Missing success evidence
    must never be interpreted as a successful signature or trust decision.
    """
    buckets: dict[str, list[str]] = {
        "success": [], "informational": [], "failure": [],
    }

    legacy = store.get("validation_status") or store.get("validationStatus") or []
    if isinstance(legacy, dict):
        legacy = [legacy]
    if isinstance(legacy, list):
        for row in legacy:
            code = _status_code(row)
            if code:
                # validation_status is the legacy problem list.  A rare row
                # carrying passed=true is positive evidence; everything else
                # remains fail-closed as a validation failure.
                key = "success" if isinstance(row, dict) and row.get("passed") is True else "failure"
                buckets[key].append(code)

    results = store.get("validation_results") or store.get("validationResults") or {}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                normalized = str(key).lower()
                if normalized in buckets and isinstance(child, list):
                    for row in child:
                        code = _status_code(row)
                        if code:
                            buckets[normalized].append(code)
                else:
                    walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(results)
    return {key: list(dict.fromkeys(values)) for key, values in buckets.items()}


def evaluate_validation_store(
    store: dict[str, Any], *, trust_checked: bool, test_certificate: bool
) -> dict[str, Any]:
    """Separate structural validity, signature validity, trust, and timestamp."""
    active = str(store.get("active_manifest") or store.get("activeManifest") or "")
    manifests = store.get("manifests") if isinstance(store.get("manifests"), dict) else {}
    manifest = manifests.get(active) if active else None
    if not isinstance(manifest, dict) and len(manifests) == 1:
        manifest = next(iter(manifests.values()))
    manifest = manifest if isinstance(manifest, dict) else {}
    buckets = _validation_buckets(store)
    success = [code.lower() for code in buckets["success"]]
    informational = [code.lower() for code in buckets["informational"]]
    failures = [code.lower() for code in buckets["failure"]]
    all_problems = failures + informational

    def is_signature(code: str) -> bool:
        return any(subject in code for subject in (
            "claimsignature", "signingcredential", "certificate", "signature",
        ))

    def is_timestamp(code: str) -> bool:
        return "timestamp" in code

    def is_trust(code: str) -> bool:
        return any(token in code for token in (
            "trusted", "untrusted", "nottrusted", "revoked", "expired",
        ))

    # Keep structure independent from signature/trust/TSA. Any other explicit
    # failure is structural/content validation failure and blocks the claim.
    structural_failures = [
        code for code in failures
        if not is_signature(code) and not is_timestamp(code) and not is_trust(code)
    ]
    signature_failures = [
        code for code in failures if is_signature(code) and not is_trust(code)
    ]
    trust_bad = any(
        any(token in code for token in ("untrusted", "nottrusted", "revoked", "expired"))
        for code in all_problems
        if not is_timestamp(code) and (is_signature(code) or is_trust(code))
    )
    timestamp_bad = any(
        any(token in code for token in ("untrusted", "nottrusted", "invalid", "mismatch", "expired", "revoked"))
        for code in all_problems if is_timestamp(code)
    )
    signature_info = manifest.get("signature_info") or manifest.get("signatureInfo") or {}
    signed_at = (
        signature_info.get("time") or signature_info.get("timestamp") or signature_info.get("signed_at")
    ) if isinstance(signature_info, dict) else None
    validation_state = str(
        store.get("validation_state") or store.get("validationState")
        or manifest.get("validation_state") or manifest.get("validationState") or ""
    ).strip()
    signature_evidence = any("claimsignature.validated" in code for code in success)
    trusted_evidence = (
        validation_state.lower() == "trusted"
        or any("signingcredential.trusted" in code for code in success)
    )
    timestamp_validated = any("timestamp.validated" in code for code in success)
    timestamp_trusted = bool(timestamp_validated and not timestamp_bad)
    structural_valid = bool(active and manifest) and not structural_failures
    signature_valid = bool(structural_valid and signature_evidence and not signature_failures)
    trusted = bool(
        trust_checked and signature_valid and trusted_evidence
        and not trust_bad and not test_certificate
    )
    return {
        "active_manifest": active,
        "validation_state": validation_state or None,
        "validation_success_codes": buckets["success"],
        "validation_informational_codes": buckets["informational"],
        "validation_failure_codes": buckets["failure"],
        "validation_status_codes": list(dict.fromkeys(
            buckets["success"] + buckets["informational"] + buckets["failure"]
        )),
        "structurally_valid": structural_valid,
        "signature_valid": signature_valid,
        "trust_checked": bool(trust_checked),
        "trusted": trusted,
        "signed_at": signed_at,
        "timestamp_validated": timestamp_validated,
        "timestamp_trusted": timestamp_trusted,
        # Backward-facing name retains its documented meaning: a trusted TSA
        # timestamp, not merely signature_info.time / claim signing time.
        "timestamped": timestamp_trusted,
        "signature_info": signature_info,
    }


def _run_json(command: list[str], *, cwd: str | None = None) -> tuple[int, dict[str, Any], str]:
    proc = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
    raw = (proc.stdout or "").strip()
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}
    detail = (proc.stderr or raw or "").strip()
    return proc.returncode, payload if isinstance(payload, dict) else {}, detail


def _validate_disclosure(root: str) -> tuple[str, dict[str, Any]]:
    rel = "合规/ai_usage.json"
    path = os.path.join(root, rel)
    payload = mv_utils.load_json(path, None)
    if not isinstance(payload, dict) or payload.get("kind") != "mv_ai_usage":
        raise ValueError("缺或损坏 合规/ai_usage.json；必须先完成 disclosure 阶段")
    for bound_rel, recorded in (payload.get("inputs_sha256") or {}).items():
        current = mv_utils.content_hash(os.path.join(root, str(bound_rel)))
        if not current or current != recorded:
            raise ValueError(f"AI 使用披露已过期：{bound_rel}")
    return rel, payload


def _trust_source(project_root: str, raw: str) -> tuple[dict[str, Any], str]:
    """Return a portable trust descriptor plus the executable CLI argument."""
    value = str(raw or "").strip()
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return {"kind": "url", "url": value}, value
    candidate = value if os.path.isabs(value) else os.path.join(project_root, value)
    candidate = os.path.abspath(candidate)
    if not _inside(project_root, candidate) or not os.path.isfile(candidate):
        raise ValueError(
            "--trust-anchors 必须是 http(s) 官方/组织信任列表，或已复制到作品根内的 PEM 文件"
        )
    rel = mv_utils.relpath(project_root, candidate)
    return {
        "kind": "project_file", "path": rel,
        "sha256": mv_utils.content_hash(candidate),
    }, candidate


def _embed(
    *, final: str, manifest_path: str, output: str, signer_path: str,
    identity_signer_path: str, trust_anchors: str, allow_test_certificate: bool,
    allow_no_timestamp: bool,
) -> dict[str, Any]:
    tool = shutil.which("c2patool")
    if not tool:
        raise ValueError("--embed-c2pa requested but c2patool is unavailable")
    test_certificate = not bool(signer_path)
    if test_certificate and not allow_test_certificate:
        raise ValueError("生产 C2PA 必须提供 --signer-path；内置测试证书需显式 --allow-test-certificate")
    if signer_path and not trust_anchors:
        raise ValueError("生产 C2PA 必须提供 --trust-anchors，不能把 valid 冒充 trusted")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(manifest_path)))
    trust_source: dict[str, Any] | None = None
    trust_argument = ""
    if trust_anchors:
        trust_source, trust_argument = _trust_source(project_root, trust_anchors)
    command = [tool, final, "--manifest", manifest_path, "--output", output]
    if signer_path:
        command += ["--signer-path", signer_path]
    if identity_signer_path:
        command += ["--identity-signer-path", identity_signer_path]
    # ingredient_paths are deliberately project-relative; c2patool must run
    # from the project root or it may sign a manifest with missing ingredients.
    proc = subprocess.run(command, capture_output=True, text=True, cwd=project_root)
    if proc.returncode:
        raise ValueError(f"c2patool embed failed: {(proc.stderr or proc.stdout).strip()}")
    if not os.path.isfile(output):
        raise ValueError("c2patool returned success but did not create the signed asset")

    verify_command = [tool, output]
    if trust_argument:
        verify_command += ["trust", "--trust_anchors", trust_argument]
    code, store, detail = _run_json(verify_command, cwd=project_root)
    if code:
        raise ValueError(f"c2patool verification failed: {detail}")
    verification = evaluate_validation_store(
        store, trust_checked=bool(trust_argument), test_certificate=test_certificate,
    )
    if not verification["structurally_valid"] or not verification["signature_valid"]:
        raise ValueError(f"C2PA verification did not validate: {verification['validation_status_codes']}")
    if signer_path and not verification["trusted"]:
        raise ValueError(f"C2PA signature is valid but not trusted: {verification['validation_status_codes']}")
    if signer_path and not allow_no_timestamp and not verification["timestamp_trusted"]:
        raise ValueError("生产 C2PA 缺可信时间戳；配置 signer 的 TSA，或仅在明确例外时传 --allow-no-timestamp")
    verification.update({
        "embedded": True,
        "certificate_profile": "test_untrusted" if test_certificate else "production",
        "output_sha256": mv_utils.content_hash(output),
        # Do not leak workstation-specific executable/config paths into a
        # portable delivery ledger; the signed manifest itself carries signer
        # identity, while this layer records only whether each route was used.
        "external_signer_configured": bool(signer_path),
        "identity_signer_configured": bool(identity_signer_path),
        "timestamp_exception_allowed": bool(allow_no_timestamp),
        "trust_source": trust_source,
    })
    return verification


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root")
    parser.add_argument("--final", required=True)
    parser.add_argument("--master")
    parser.add_argument("--embed-c2pa", action="store_true")
    parser.add_argument("--signer-path", default="", help="生产签名 subprocess；不要传私钥")
    parser.add_argument("--identity-signer-path", default="")
    parser.add_argument("--trust-anchors", default="", help="c2patool trust anchors 文件/URL")
    parser.add_argument("--allow-test-certificate", action="store_true", help="仅开发验证；永不记为 trusted")
    parser.add_argument("--allow-no-timestamp", action="store_true", help="生产例外，仍会明确记 timestamped=false")
    parser.add_argument("--c2pa-output", default="")
    parser.add_argument("--no-progress", action="store_true",
                        help="显式只写 provenance，不尝试完成 workflow 阶段")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    try:
        final = _required_asset(root, args.final, "final")
        master = _required_asset(root, args.master, "master") if args.master else None
        disclosure_rel, ai_usage = _validate_disclosure(root)
    except ValueError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 1

    assets = existing_assets(root, final, master)
    final_rel = mv_utils.relpath(root, final)
    master_rel = mv_utils.relpath(root, master) if master else None
    ingredients = [rel for rel in assets if rel not in {final_rel, master_rel}]
    c2pa_manifest = build_c2pa_manifest(
        root=root, final_rel=final_rel, ingredients=ingredients, ai_usage=ai_usage,
    )
    compliance_dir = os.path.join(root, "合规")
    os.makedirs(compliance_dir, exist_ok=True)
    c2pa_path = os.path.join(compliance_dir, "c2pa_manifest.json")
    mv_utils.write_json(c2pa_path, c2pa_manifest)

    c2pa_status: dict[str, Any] = {
        "requested": bool(args.embed_c2pa),
        "tool_available": bool(shutil.which("c2patool")),
        "embedded": False,
        "structurally_valid": False,
        "signature_valid": False,
        "trust_checked": False,
        "trusted": False,
        "timestamped": False,
        "timestamp_validated": False,
        "timestamp_trusted": False,
        "timestamp_exception_allowed": False,
        "trust_source": None,
        "certificate_profile": None,
        "manifest_sha256": mv_utils.content_hash(c2pa_path),
    }
    signed_output = ""
    if args.embed_c2pa:
        signed_output = os.path.abspath(args.c2pa_output or (final + ".c2pa.mp4"))
        if not _inside(root, signed_output):
            print(f"[err] C2PA output 必须位于作品根内：{signed_output}", file=sys.stderr)
            return 1
        try:
            c2pa_status.update(_embed(
                final=final, manifest_path=c2pa_path, output=signed_output,
                signer_path=args.signer_path,
                identity_signer_path=args.identity_signer_path,
                trust_anchors=args.trust_anchors,
                allow_test_certificate=args.allow_test_certificate,
                allow_no_timestamp=args.allow_no_timestamp,
            ))
            c2pa_status["output"] = mv_utils.relpath(root, signed_output)
        except ValueError as exc:
            print(f"[err] {exc}", file=sys.stderr)
            return 1

    asset_rows = [
        {"path": rel, "sha256": mv_utils.content_hash(os.path.join(root, rel)), "format": _mime(rel)}
        for rel in assets
    ]
    if signed_output:
        asset_rows.append({
            "path": mv_utils.relpath(root, signed_output),
            "sha256": mv_utils.content_hash(signed_output),
            "format": _mime(signed_output),
            "role": "c2pa_signed_delivery",
        })
    payload = {
        "schema_version": 2,
        "kind": "mv_provenance",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "complete": True,
        "assets": asset_rows,
        "relationships": {
            "final": final_rel,
            "master": master_rel,
            "ingredients": ingredients,
            "disclosure": disclosure_rel,
        },
        "inputs_sha256": {rel: mv_utils.content_hash(os.path.join(root, rel)) for rel in ingredients},
        "ai_usage": ai_usage,
        "ai_usage_sha256": mv_utils.content_hash(os.path.join(root, disclosure_rel)),
        "c2pa": c2pa_status,
    }
    out = os.path.join(compliance_dir, "provenance.json")
    mv_utils.write_json(out, payload)
    if not args.no_progress:
        try:
            import completion
            completion.mark_stage_complete(root, "provenance")
        except (ImportError, RuntimeError, ValueError) as exc:
            print(f"[err] provenance 已写入，但完成态未建立：{exc}", file=sys.stderr)
            return 1
    else:
        print("[evidence-only] --no-progress：未声明 provenance 阶段完成", file=sys.stderr)
    print(f"[ok] provenance → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
