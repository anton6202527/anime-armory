#!/usr/bin/env python3
"""Technical QA for every master/cutdown/reframe deliverable."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


_CRAFT_SCRIPTS = Path(__file__).resolve().parents[1] / "ad-craft" / "scripts"
if str(_CRAFT_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_CRAFT_SCRIPTS))
import render_profile as ad_render_profile  # noqa: E402


def seconds(value) -> float:
    m = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(m.group()) if m else 0.0


def frame_rate(value) -> float:
    raw = str(value or "0")
    if "/" in raw:
        a, b = raw.split("/", 1)
        try:
            return float(a) / float(b)
        except (ValueError, ZeroDivisionError):
            return 0.0
    return seconds(raw)


def resolution(value):
    match = re.fullmatch(r"\s*(\d+)\s*[x×]\s*(\d+)\s*", str(value or ""), re.I)
    return (int(match.group(1)), int(match.group(2))) if match else (0, 0)


def canonical_sha(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def adaptation_plan_sha(payload):
    return canonical_sha({key: value for key, value in payload.items()
                          if key not in {"generated_at", "plan_sha256"}
                          and not str(key).startswith("_")})


def adaptation_item_sha(payload):
    return canonical_sha({key: value for key, value in payload.items() if not str(key).startswith("_")})


def probe(path: Path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.is_file():
        return None
    proc = subprocess.run([ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                          capture_output=True, text=True)
    if proc.returncode:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def measure_loudness(path: Path):
    """Measure integrated LUFS and true peak from the rendered file itself."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not path.is_file():
        return None
    proc = subprocess.run([
        ffmpeg, "-hide_banner", "-nostats", "-i", str(path),
        "-af", "loudnorm=I=-24:TP=-2:LRA=7:print_format=json", "-f", "null", "-",
    ], capture_output=True, text=True)
    text = proc.stderr or ""
    matches = re.findall(r"\{[\s\S]*?\}", text)
    if not matches:
        return None
    try:
        row = json.loads(matches[-1])
        return {
            "integrated_lufs": float(row["input_i"]),
            "true_peak_db": float(row["input_tp"]),
            "lra": float(row["input_lra"]),
        }
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _sha256_file(path: Path):
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project_path(root: Path, rel: str):
    try:
        path = (root / str(rel or "")).resolve()
        path.relative_to(root.resolve())
        return path
    except (ValueError, OSError):
        return None


def placement_adaptation_findings(root: Path, item: dict):
    """Validate the current evidence bound to a schema-v5 delivery row.

    Older/manual plans that do not carry the field retain their historical QC
    behaviour.  Once a plan opts into placement adaptation, however, a blocked
    or stale decision must never be converted into a completed deliverable just
    because an MP4 happens to exist at the expected path.
    """
    if "placement_adaptation" not in item:
        if int(item.get("_delivery_plan_schema_version") or 0) >= 5:
            return [{"severity": "block", "code": "placement_adaptation_missing",
                     "msg": "schema-v5 delivery row 缺逐版位 adaptation 决策。"}]
        return []
    adaptation = item.get("placement_adaptation")
    if not isinstance(adaptation, dict):
        return [{"severity": "block", "code": "placement_adaptation_missing",
                 "msg": "交付计划缺逐版位 adaptation 决策；须重建 delivery plan。"}]
    findings = []
    if adaptation.get("status") != "approved":
        findings.append({
            "severity": "block", "code": "placement_adaptation_not_approved",
            "msg": f"{item.get('deliverable_id')} 的逐版位适配尚未批准，不能仅凭既有媒体文件通过交付 QC。",
        })
    if any(row.get("severity") == "block" for row in adaptation.get("findings") or []
           if isinstance(row, dict)):
        findings.append({
            "severity": "block", "code": "placement_adaptation_has_block",
            "msg": f"{item.get('deliverable_id')} 的适配计划仍含 block；须修复并重建交付计划。",
        })

    def check_bound_evidence(value, label="evidence"):
        if not isinstance(value, dict):
            return
        if "path" in value or "sha256" in value:
            rel = str(value.get("path") or "").strip()
            expected = str(value.get("sha256") or "").strip()
            path = (root / rel).resolve() if rel else None
            try:
                if path is not None:
                    path.relative_to(root.resolve())
            except ValueError:
                path = None
            actual = _sha256_file(path) if path is not None else None
            if not rel or not expected or actual != expected:
                findings.append({
                    "severity": "block", "code": "placement_adaptation_evidence_stale",
                    "msg": f"{item.get('deliverable_id')} 绑定的 {label} 已缺失或内容 SHA 变化；须重新评估适配并重建交付计划。",
                    "detail": {"path": rel, "expected_sha256": expected or None,
                               "actual_sha256": actual},
                })
            return
        for key, child in value.items():
            check_bound_evidence(child, f"{label}.{key}")

    check_bound_evidence(adaptation.get("evidence") or {})
    if item.get("kind") == "reframe":
        did = str(item.get("deliverable_id") or "")
        receipt_rel = f"生产数据/placement_adaptation_receipts/{did}.json"
        receipt_path = root / receipt_rel
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except Exception:
            receipt = {}
        if not isinstance(receipt, dict) or not receipt:
            findings.append({
                "severity": "block", "code": "adaptation_execution_receipt_missing",
                "msg": f"{did} 缺逐交付件 execution receipt；批准模式不能证明实际成片制作方式。",
            })
            return findings
        logical_receipt = {key: value for key, value in receipt.items()
                           if key != "receipt_sha256" and not str(key).startswith("_")}
        if (receipt.get("kind") != "ad_placement_adaptation_execution_receipt"
                or receipt.get("schema_version") != 1
                or receipt.get("receipt_sha256") != canonical_sha(logical_receipt)):
            findings.append({"severity": "block", "code": "adaptation_execution_receipt_invalid",
                             "msg": f"{did} execution receipt schema/digest 无效。"})
        if receipt.get("actual_mode") != adaptation.get("selected_mode"):
            findings.append({
                "severity": "block", "code": "adaptation_execution_mode_mismatch",
                "msg": f"{did} 实际制作模式={receipt.get('actual_mode')}，"
                       f"不等于批准模式={adaptation.get('selected_mode')}。",
            })
        try:
            disk_plan = json.loads((root / "生产数据" / "placement_adaptation.json").read_text(encoding="utf-8"))
        except Exception:
            disk_plan = {}
        disk_sha = str((disk_plan or {}).get("plan_sha256") or "")
        if (not disk_sha or disk_sha != adaptation_plan_sha(disk_plan)
                or receipt.get("adaptation_plan_sha256") != disk_sha):
            findings.append({"severity": "block", "code": "adaptation_execution_plan_stale",
                             "msg": f"{did} execution receipt 未绑定当前 adaptation plan。"})
        disk_item = next((row for row in (disk_plan or {}).get("items") or []
                          if isinstance(row, dict) and str(row.get("deliverable_id")) == did), {})
        if (not disk_item or receipt.get("adaptation_item_sha256") != adaptation_item_sha(disk_item)
                or adaptation_item_sha(adaptation) != adaptation_item_sha(disk_item)):
            findings.append({"severity": "block", "code": "adaptation_execution_item_stale",
                             "msg": f"{did} execution receipt/交付计划未绑定当前 adaptation item。"})
        profile_ref = item.get("render_profile") if isinstance(item.get("render_profile"), dict) else {}
        if receipt.get("render_profile_sha256") != profile_ref.get("sha256"):
            findings.append({"severity": "block", "code": "adaptation_execution_profile_stale",
                             "msg": f"{did} execution receipt 未绑定当前 render profile。"})
        output = receipt.get("output") if isinstance(receipt.get("output"), dict) else {}
        expected_rel = str(item.get("expected_path") or "")
        expected_path = _project_path(root, expected_rel)
        if (output.get("path") != expected_rel or not output.get("sha256") or not expected_path
                or _sha256_file(expected_path) != output.get("sha256")):
            findings.append({"severity": "block", "code": "adaptation_execution_output_stale",
                             "msg": f"{did} execution receipt 未绑定当前 expected output 像素。"})
        inputs = receipt.get("inputs") if isinstance(receipt.get("inputs"), list) else []
        if not inputs or any(not isinstance(row, dict) or not row.get("path") or not row.get("sha256")
                             or not _project_path(root, str(row.get("path")))
                             or _sha256_file(_project_path(root, str(row.get("path")))) != row.get("sha256")
                             for row in inputs):
            findings.append({"severity": "block", "code": "adaptation_execution_input_stale",
                             "msg": f"{did} execution receipt 的真实输入缺失或 SHA 已变化。"})
        if adaptation.get("selected_mode") in {"native_reedit", "native_variant"}:
            evidence = adaptation.get("evidence") if isinstance(adaptation.get("evidence"), dict) else {}
            native_sources = evidence.get("native_sources") if isinstance(evidence.get("native_sources"), list) else []
            expected_sources = {
                str(row.get("path") or ""): str(row.get("sha256") or "")
                for row in native_sources if isinstance(row, dict) and row.get("path")
            }
            actual_sources = {
                str(row.get("path") or ""): str(row.get("sha256") or "")
                for row in inputs if isinstance(row, dict) and row.get("path")
            }
            if not expected_sources:
                findings.append({
                    "severity": "block", "code": "adaptation_execution_native_sources_missing",
                    "msg": f"{did} 原生重剪/变体计划未逐镜绑定真实源素材；主片输入不能证明原生制作。",
                })
            elif any(actual_sources.get(path) != digest for path, digest in expected_sources.items()):
                findings.append({
                    "severity": "block", "code": "adaptation_execution_native_source_mismatch",
                    "msg": f"{did} execution receipt 未消费 shot plan 绑定的全部当前源素材。",
                    "detail": {"expected": expected_sources, "actual": actual_sources},
                })
    return findings


def _load_render_profile(root: Path, item: dict):
    """Load the profile bound into this delivery-plan row and verify logical SHA."""
    formal_plan = int(item.get("_delivery_plan_schema_version") or 0) >= 5
    ref = item.get("render_profile") if isinstance(item.get("render_profile"), dict) else None
    if not ref:
        if formal_plan:
            return None, [{"severity": "block", "code": "render_profile_ref_missing",
                           "msg": "schema-v5 delivery row 缺统一 render_profile ref。"}]
        return None, []  # legacy/manual plans keep their existing QC semantics
    rel = str(ref.get("path") or "生产数据/render_profile.json")
    path = _project_path(root, rel)
    if path is None:
        return None, [{"severity": "block", "code": "render_profile_path_invalid",
                       "msg": "render_profile ref 必须是作品根内相对路径。"}]
    try:
        profile = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, [{"severity": "block", "code": "render_profile_missing",
                       "msg": f"交付计划绑定的统一渲染规格不存在/不可读：{rel}"}]
    expected_sha = str(ref.get("sha256") or "")
    actual_sha = str(profile.get("profile_sha256") or "")
    findings = []
    if formal_plan:
        required_sections = ("source_generation", "master_render", "upscale", "input_sha256")
        if profile.get("kind") != "ad_render_profile" or profile.get("schema_version") != 1:
            findings.append({"severity": "block", "code": "render_profile_schema_invalid",
                             "msg": "formal delivery 要求 kind=ad_render_profile/schema_version=1。"})
        for section in required_sections:
            if not isinstance(profile.get(section), dict) or not profile.get(section):
                findings.append({"severity": "block", "code": "render_profile_structure_invalid",
                                 "msg": f"formal render_profile 缺有效 {section}。"})
        for section in ("source_generation", "master_render"):
            row = profile.get(section) if isinstance(profile.get(section), dict) else {}
            if not all(row.get(key) for key in ("width", "height", "fps", "aspect")):
                findings.append({"severity": "block", "code": "render_profile_structure_invalid",
                                 "msg": f"render_profile.{section} 缺 width/height/fps/aspect。"})
        upscale = profile.get("upscale") if isinstance(profile.get("upscale"), dict) else {}
        upscale_fields = (
            "policy", "required", "native_resolution_required", "effective_source_resolution",
            "container_resolution", "scale_factor", "quality_claim",
        )
        if any(key not in upscale or upscale.get(key) is None for key in upscale_fields):
            findings.append({"severity": "block", "code": "render_profile_structure_invalid",
                             "msg": "render_profile.upscale 缺完整策略/来源/容器/倍率/质量声明。"})
    input_hashes = profile.get("input_sha256") if isinstance(profile.get("input_sha256"), dict) else None
    if input_hashes is not None:
        logical_payload = {key: value for key, value in profile.items()
                           if key != "profile_sha256" and not str(key).startswith("_")}
        logical_sha = hashlib.sha256(json.dumps(
            logical_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        if not actual_sha or actual_sha != logical_sha:
            findings.append({
                "severity": "block", "code": "render_profile_digest_invalid",
                "msg": "render_profile 内容与其自带逻辑 SHA 不一致；文件可能被手改，须从当前输入重建。",
            })

        for rel in ("_设置.md", "需求/brief.json"):
            path = root / rel
            current = _sha256_file(path)
            if input_hashes.get(rel) != current:
                findings.append({
                    "severity": "block", "code": "render_profile_input_stale",
                    "msg": f"render_profile 未绑定当前 {rel}；设置或 brief 变化后须重建 route/job/交付计划。",
                    "detail": {"path": rel, "expected_sha256": input_hashes.get(rel),
                               "actual_sha256": current},
                })
        pack_rel = "生产数据/platform_pack.json"
        try:
            pack = json.loads((root / pack_rel).read_text(encoding="utf-8"))
            pack_payload = {key: value for key, value in pack.items() if not str(key).startswith("_")}
            current_pack = hashlib.sha256(json.dumps(
                pack_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            ).encode("utf-8")).hexdigest()
        except Exception:
            current_pack = None
        if input_hashes.get(pack_rel) != current_pack:
            findings.append({
                "severity": "block", "code": "render_profile_platform_pack_stale",
                "msg": "render_profile 未绑定当前 platform_pack；版位规格变化后须重建 route/job/交付计划。",
                "detail": {"path": pack_rel, "expected_sha256": input_hashes.get(pack_rel),
                           "actual_sha256": current_pack},
            })
    if not expected_sha or not actual_sha or expected_sha != actual_sha:
        findings.append({
            "severity": "block", "code": "render_profile_stale",
            "msg": "delivery_plan 绑定的 render_profile SHA 与当前文件不一致；设置/版位规格变化后须重建交付计划。",
        })
    if formal_plan:
        try:
            fresh_profile = ad_render_profile.compile_profile(root)
            fresh_sha = str(fresh_profile.get("profile_sha256") or "")
        except Exception:
            fresh_sha = ""
        if not fresh_sha or actual_sha != fresh_sha:
            findings.append({
                "severity": "block", "code": "render_profile_semantic_stale",
                "msg": "render_profile 虽可自洽，但与当前设置、brief 和 platform pack 实时编译语义不一致。",
                "detail": {"stored_sha256": actual_sha or None, "fresh_sha256": fresh_sha or None},
            })
    return profile, findings


def _target_dimensions(profile: dict, aspect: str):
    master = profile.get("master_render") if isinstance(profile.get("master_render"), dict) else {}
    width, height = int(master.get("width") or 0), int(master.get("height") or 0)
    if not width or not height:
        return 0, 0
    if str(master.get("aspect") or "") == str(aspect or ""):
        return width, height
    a, _, b = str(aspect or "").replace("x", ":").partition(":")
    try:
        ratio = float(a) / float(b)
    except (ValueError, ZeroDivisionError):
        return 0, 0
    short_edge = min(width, height)
    if ratio > 1:
        out = (round(short_edge * ratio), short_edge)
    elif ratio < 1:
        out = (short_edge, round(short_edge / ratio))
    else:
        out = (short_edge, short_edge)
    return tuple(v if v % 2 == 0 else v + 1 for v in out)


def _actual_clip_resolutions(root: Path):
    rows = []
    for path in sorted((root / "出视频" / "分镜" / "视频").glob("*.mp4")):
        data = probe(path) or {}
        video = next((s for s in data.get("streams") or [] if s.get("codec_type") == "video"), {})
        width, height = int(video.get("width") or 0), int(video.get("height") or 0)
        if width and height:
            fps = frame_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
            rows.append({"path": path.relative_to(root).as_posix(), "width": width, "height": height,
                         "resolution": f"{width}x{height}", "fps": fps})
    return rows


def render_profile_findings(root: Path, item: dict, width: int, height: int, fps: float):
    profile, findings = _load_render_profile(root, item)
    if not profile:
        return findings, None
    source = profile.get("source_generation") if isinstance(profile.get("source_generation"), dict) else {}
    master = profile.get("master_render") if isinstance(profile.get("master_render"), dict) else {}
    upscale = profile.get("upscale") if isinstance(profile.get("upscale"), dict) else {}
    target_w, target_h = _target_dimensions(profile, str(item.get("aspect") or master.get("aspect") or ""))
    if target_w and target_h and (width, height) != (target_w, target_h):
        findings.append({
            "severity": "block", "code": "render_profile_resolution_mismatch",
            "msg": f"实测母版容器 {width}x{height}，统一 render_profile 要求 {target_w}x{target_h}。",
        })
    target_fps = float(master.get("fps") or 0)
    if target_fps and abs(float(fps or 0) - target_fps) > 0.15:
        findings.append({
            "severity": "block", "code": "render_profile_fps_mismatch",
            "msg": f"实测 {fps:.3f}fps，统一 render_profile 要求 {target_fps:g}fps。",
        })

    clips = _actual_clip_resolutions(root)
    constraints = item.get("platform_constraints") if isinstance(item.get("platform_constraints"), list) else []
    placement_native = any(
        spec.get("native_resolution_required") is True
        or spec.get("require_native_resolution") is True
        or spec.get("upscale_forbidden") is True
        or str(spec.get("upscale_policy") or "").lower() in {
            "forbid", "forbidden", "native", "native_required", "no_upscale", "禁止放大", "原生",
        }
        for spec in constraints if isinstance(spec, dict)
    )
    native_required = bool(upscale.get("native_resolution_required")) or placement_native
    if clips:
        effective = min(clips, key=lambda row: row["width"] * row["height"])
        effective_w, effective_h = effective["width"], effective["height"]
        evidence = {"kind": "ffprobe_source_clips", "source_resolutions": clips,
                    "effective_source_resolution": effective["resolution"]}
        source_dims = (int(source.get("width") or 0), int(source.get("height") or 0))
        mismatched_dims = [row for row in clips if (row["width"], row["height"]) != source_dims]
        if source_dims != (0, 0) and mismatched_dims:
            findings.append({
                "severity": "block", "code": "observed_source_resolution_mismatch",
                "msg": f"实测生成 clip 未兑现 source_generation={source.get('resolution')}；"
                       "请求规格不能冒充回收媒体规格。",
                "detail": {"mismatched": mismatched_dims},
            })
        source_fps = float(source.get("fps") or 0)
        mismatched_fps = [row for row in clips if not row.get("fps") or abs(float(row["fps"]) - source_fps) > 0.15]
        if source_fps and mismatched_fps:
            findings.append({
                "severity": "block", "code": "observed_source_fps_mismatch",
                "msg": f"实测生成 clip FPS 未兑现 source_generation={source_fps:g}。",
                "detail": {"mismatched": mismatched_fps},
            })
    else:
        effective_w, effective_h = int(source.get("width") or 0), int(source.get("height") or 0)
        evidence = {"kind": "planned_source_generation",
                    "effective_source_resolution": source.get("effective_source_resolution") or source.get("resolution")}
        findings.append({
            "severity": "block" if native_required else "warn",
            "code": "effective_source_unverified",
            "msg": "未找到可 ffprobe 的生成 clip；计划 source_generation 不能替代有效源实测证据。",
        })

    for spec in constraints:
        if not isinstance(spec, dict):
            continue
        aspect = str(item.get("aspect") or "")
        raw_required = ((spec.get("required_resolution_by_aspect") or {}).get(aspect)
                        if isinstance(spec.get("required_resolution_by_aspect"), dict) else None)
        raw_required = raw_required or spec.get("required_resolution")
        if placement_native and not raw_required:
            raw_required = ((spec.get("min_resolution_by_aspect") or {}).get(aspect)
                            if isinstance(spec.get("min_resolution_by_aspect"), dict) else None)
            raw_required = raw_required or spec.get("min_resolution")
        parsed_required = ad_render_profile.parse_resolution(raw_required, aspect)
        req_w = int((parsed_required or {}).get("width") or 0)
        req_h = int((parsed_required or {}).get("height") or 0)
        if req_w and req_h and (effective_w < req_w or effective_h < req_h):
            findings.append({
                "severity": "block", "code": "effective_source_below_placement_requirement",
                "msg": f"有效生成源 {effective_w}x{effective_h} 低于逐版位原生要求 {req_w}x{req_h}。",
            })
        required_fps = frame_rate(spec.get("required_fps") or spec.get("source_required_fps"))
        if required_fps and clips and any(abs(float(row.get("fps") or 0) - required_fps) > 0.15 for row in clips):
            findings.append({
                "severity": "block", "code": "effective_source_fps_below_placement_requirement",
                "msg": f"有效生成源 FPS 未满足逐版位要求 {required_fps:g}。",
            })
    container_larger = bool(effective_w and effective_h and
                            (width > effective_w or height > effective_h))
    if container_larger or upscale.get("required"):
        findings.append({
            "severity": "block" if native_required else "warn",
            "code": "native_resolution_required_but_upscaled" if native_required else "container_upscale_only",
            "msg": (f"最终容器 {width}x{height} 大于有效生成源 "
                    f"{evidence.get('effective_source_resolution') or 'unknown'}；"
                    + ("该交付要求原生分辨率，容器放大不能通过。" if native_required
                       else "这是容器放大，不得宣称原生清晰度。")),
            "detail": {
                **evidence,
                "container_resolution": f"{width}x{height}",
                "policy": upscale.get("policy"),
                "authority": master.get("authority") or [],
            },
        })
    return findings, {
        "path": str((item.get("render_profile") or {}).get("path") or "生产数据/render_profile.json"),
        "sha256": profile.get("profile_sha256"),
        "target_resolution": f"{target_w}x{target_h}" if target_w and target_h else None,
        "target_fps": target_fps,
        "effective_source": evidence,
    }


def inspect_item(root: Path, item: dict):
    path = _project_path(root, str(item.get("expected_path") or ""))
    findings = []
    findings.extend(placement_adaptation_findings(root, item))
    if path is None:
        findings.append({"severity": "block", "code": "delivery_media_path_invalid",
                         "msg": "expected_path 必须是作品根内相对路径"})
        return {"deliverable_id": item.get("deliverable_id"), "path": item.get("expected_path"),
                "passed": False, "findings": findings}
    data = probe(path)
    if data is None:
        findings.append({"severity": "block", "code": "media_unreadable", "msg": f"交付件不存在或 ffprobe 不可读：{path}"})
        return {"deliverable_id": item["deliverable_id"], "path": item["expected_path"], "passed": False, "findings": findings}
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    tech = item.get("technical_profile") if isinstance(item.get("technical_profile"), dict) else None
    if item.get("placement_mapping_error"):
        findings.append({"severity": "block", "code": "placement_mapping_invalid",
                         "msg": str(item.get("placement_mapping_error"))})
    if not tech:
        findings.append({"severity": "block", "code": "technical_profile_missing",
                         "msg": "交付计划缺 contract 派生的技术母版标准"})
    delivery_profile = item.get("delivery_profile") if isinstance(item.get("delivery_profile"), dict) else None
    if (not delivery_profile or not delivery_profile.get("authority") or not delivery_profile.get("source")
            or item.get("delivery_profile_error")):
        findings.append({"severity": "block", "code": "delivery_profile_provenance_missing",
                         "msg": str(item.get("delivery_profile_error") or "响度/真峰值目标缺 authority/source")})
    actual = seconds((data.get("format") or {}).get("duration"))
    expected = seconds(item.get("duration"))
    tol = max(0.25, expected * 0.03) if expected else 0.5
    if expected and abs(actual - expected) > tol:
        findings.append({"severity": "block", "code": "duration_mismatch",
                         "msg": f"实测 {actual:.3f}s 与交付目标 {expected:.3f}s 偏差超过 {tol:.3f}s"})
    constraints = item.get("platform_constraints") if isinstance(item.get("platform_constraints"), list) else []
    silent_allowed = bool(constraints) and all(spec.get("sound_mode") == "sound_off" for spec in constraints)
    if not audio:
        if not silent_allowed:
            findings.append({"severity": "block", "code": "audio_missing", "msg": "正式广告交付件无音轨"})
        else:
            findings.append({"severity": "info", "code": "sound_off_delivery",
                             "msg": "该交付件仅映射 sound-off placement；无音轨按版位策略放行，信息须由画面/字幕完整承载"})
        loudness = None
    else:
        if tech and str(audio.get("codec_name") or "") != str(tech.get("audio_codec") or ""):
            findings.append({"severity": "block", "code": "audio_codec_mismatch",
                             "msg": f"音频 codec={audio.get('codec_name')}，母版要求 {tech.get('audio_codec')}"})
        if tech and int(audio.get("sample_rate") or 0) != int(tech.get("audio_sample_rate") or 0):
            findings.append({"severity": "block", "code": "audio_sample_rate_mismatch",
                             "msg": f"音频采样率={audio.get('sample_rate')}，母版要求 {tech.get('audio_sample_rate')}Hz"})
        loudness = measure_loudness(path)
        if loudness is None:
            findings.append({"severity": "block", "code": "loudness_unmeasured", "msg": "无法实测交付响度/真峰值"})
        elif item.get("loudness_lufs") is None or item.get("true_peak_db") is None:
            findings.append({"severity": "block", "code": "delivery_profile_missing",
                             "msg": "交付计划缺 contract 派生的响度/真峰值目标"})
        else:
            target_lufs = float(item["loudness_lufs"])
            target_tp = float(item["true_peak_db"])
            if abs(loudness["integrated_lufs"] - target_lufs) > 1.5:
                findings.append({
                    "severity": "block", "code": "loudness_mismatch",
                    "msg": f"实测 {loudness['integrated_lufs']:.2f} LUFS，目标 {target_lufs:.2f}±1.5 LUFS",
                })
            if loudness["true_peak_db"] > target_tp + 0.2:
                findings.append({
                    "severity": "block", "code": "true_peak_exceeded",
                    "msg": f"实测真峰值 {loudness['true_peak_db']:.2f} dBTP，高于上限 {target_tp:.2f} dBTP",
                })
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    if not width or not height:
        findings.append({"severity": "block", "code": "video_stream_missing", "msg": "缺有效视频流/分辨率"})
    else:
        a, _, b = str(item.get("aspect") or "").replace("x", ":").partition(":")
        try:
            target = float(a) / float(b)
            if abs(width / height - target) > 0.02:
                findings.append({"severity": "block", "code": "aspect_mismatch",
                                 "msg": f"实测 {width}x{height} 与目标比例 {item.get('aspect')} 不符"})
        except (ValueError, ZeroDivisionError):
            findings.append({"severity": "warn", "code": "aspect_unknown", "msg": "无法解析目标比例"})
    fps = frame_rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    profile_findings, profile_evidence = render_profile_findings(root, item, width, height, fps)
    findings.extend(profile_findings)
    if tech:
        if str(video.get("codec_name") or "") != str(tech.get("video_codec") or ""):
            findings.append({"severity": "block", "code": "video_codec_mismatch",
                             "msg": f"视频 codec={video.get('codec_name')}，母版要求 {tech.get('video_codec')}"})
        if str(video.get("pix_fmt") or "") != str(tech.get("pixel_format") or ""):
            findings.append({"severity": "block", "code": "pixel_format_mismatch",
                             "msg": f"pixel format={video.get('pix_fmt')}，母版要求 {tech.get('pixel_format')}"})
        if not (float(tech.get("frame_rate_min") or 0) <= fps <= float(tech.get("frame_rate_max") or 999)):
            findings.append({"severity": "block", "code": "frame_rate_mismatch",
                             "msg": f"实测 {fps:.3f}fps 超出母版范围"})
        color_fields = {
            "color_primaries": "color_primaries", "color_transfer": "color_transfer",
            "color_space": "color_space", "color_range": "color_range",
        }
        for profile_key, stream_key in color_fields.items():
            expected_color = str(tech.get(profile_key) or "")
            if expected_color and str(video.get(stream_key) or "") != expected_color:
                findings.append({
                    "severity": "block", "code": f"{profile_key}_mismatch",
                    "msg": f"{stream_key}={video.get(stream_key) or 'unspecified'}，SDR 母版要求 {expected_color}",
                })
        if tech.get("scan_type") == "progressive" and str(video.get("field_order") or "") != "progressive":
            findings.append({"severity": "block", "code": "scan_type_mismatch",
                             "msg": f"field_order={video.get('field_order') or 'unknown'}，母版要求 progressive"})
        bitrate = int(video.get("bit_rate") or (data.get("format") or {}).get("bit_rate") or 0)
        if bitrate and bitrate < int(tech.get("min_bitrate_warn") or 0):
            findings.append({"severity": "warn", "code": "bitrate_low",
                             "msg": f"实测 bitrate={bitrate}bps，低于内部/已登记平台快筛线"})
    for spec in constraints:
        platform = str(spec.get("placement_key") or (
            f"{spec.get('platform')}:{spec.get('placement')}" if spec.get("placement") else spec.get("platform")
        ) or spec.get("platform_key") or "platform")
        allowed = spec.get("allowed_aspects") or []
        if allowed and item.get("aspect") not in allowed:
            findings.append({"severity": "block", "code": "platform_aspect_mismatch",
                             "msg": f"{platform} 当前规格不含交付比例 {item.get('aspect')}"})
        minimum = (spec.get("min_resolution_by_aspect") or {}).get(item.get("aspect"))
        if not minimum and item.get("aspect") == spec.get("aspect"):
            minimum = spec.get("min_resolution")
        min_w, min_h = resolution(minimum)
        if min_w and min_h and (width < min_w or height < min_h):
            findings.append({"severity": "block", "code": "platform_resolution_below_minimum",
                             "msg": f"{platform} 实测 {width}x{height}，低于当前登记最低 {min_w}x{min_h}"})
        min_bitrate = int(spec.get("min_bitrate_bps") or 0)
        bitrate = int(video.get("bit_rate") or (data.get("format") or {}).get("bit_rate") or 0)
        if min_bitrate and bitrate and bitrate < min_bitrate:
            findings.append({"severity": "warn", "code": "platform_bitrate_below_minimum",
                             "msg": f"{platform} 实测 bitrate={bitrate}bps，低于当前登记最低 {min_bitrate}bps"})
        max_mb = float(spec.get("max_file_size_mb") or 0)
        if max_mb and path.is_file() and path.stat().st_size > max_mb * 1024 * 1024:
            findings.append({"severity": "block", "code": "platform_file_too_large",
                             "msg": f"{platform} 文件超过当前登记上限 {max_mb:g}MB"})
        min_duration = float(spec.get("min_duration_seconds") or 0)
        max_duration = float(spec.get("max_duration_seconds") or 0)
        if min_duration and actual + 0.05 < min_duration:
            findings.append({"severity": "block", "code": "placement_duration_below_minimum",
                             "msg": f"{platform} 实测 {actual:.2f}s，低于当前登记最低 {min_duration:g}s"})
        if max_duration and actual - 0.05 > max_duration:
            findings.append({"severity": "block", "code": "placement_duration_above_maximum",
                             "msg": f"{platform} 实测 {actual:.2f}s，超过当前登记上限 {max_duration:g}s"})
        eligible = float(spec.get("in_stream_eligible_min_duration_seconds") or 0)
        if eligible and actual + 0.05 < eligible:
            findings.append({"severity": "warn", "code": "placement_in_stream_ineligible",
                             "msg": f"{platform} 实测 {actual:.2f}s；低于 {eligible:g}s 时不具备当前登记的 in-stream 展示资格"})
    return {
        "deliverable_id": item["deliverable_id"], "path": item["expected_path"],
        "duration_seconds": actual, "width": width, "height": height, "fps": fps,
        "has_audio": bool(audio), "loudness": loudness,
        "render_profile": profile_evidence,
        "color": {key: video.get(key) for key in
                  ("color_primaries", "color_transfer", "color_space", "color_range", "field_order")},
        "passed": not any(f["severity"] == "block" for f in findings),
        "findings": findings,
    }


# 传统交付纪律：成片带烧录文字（字幕/法律行/CTA 板）或多语言再版时，必须同时交 **textless
# 无字版母版**（流媒体/代理行规：Netflix 口径 texted ≥30% 即须交 textless production master）——
# 否则每个语言版/修改版都要回炉重做 online，等于没交母版。
_TEXTLESS_RE = re.compile(r"textless|无字|净版|clean", re.I)


def textless_master_findings(root: Path, plan: dict):
    deliverables = plan.get("deliverables") or []
    if not deliverables:
        return []
    has_textless = any(
        _TEXTLESS_RE.search(" ".join(str(item.get(k) or "") for k in ("deliverable_id", "kind", "label", "path")))
        for item in deliverables)
    if has_textless:
        return []
    rendered_plan = {}
    try:
        rendered_plan = json.loads((root / "合规" / "rendered_text_plan.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    burned_rows = len((rendered_plan or {}).get("checks") or [])
    locales = {}
    try:
        locales = json.loads((root / "合规" / "locale_matrix.json").read_text(encoding="utf-8"))
    except Exception:
        pass
    locale_rows = (locales or {}).get("locales") or (locales or {}).get("rows") or []
    if burned_rows or len(locale_rows) > 1:
        why = []
        if burned_rows:
            why.append(f"成片计划烧录 {burned_rows} 处文字")
        if len(locale_rows) > 1:
            why.append(f"locale matrix 有 {len(locale_rows)} 个语言版")
        return [{"severity": "warn", "code": "textless_master_missing",
                 "msg": f"{'；'.join(why)}，但交付计划里没有 textless/无字版母版——"
                        "行规：带字成片必须配无字母版，否则每个语言版/改字都要回炉重做 online；"
                        "在 delivery_plan 加 textless master 交付件（id 含 textless/无字）"}]
    return []


def build_report(root: Path, plan: dict):
    schema_version = int(plan.get("schema_version") or 0)
    planned_items = [dict(item, _delivery_plan_schema_version=schema_version)
                     for item in plan.get("deliverables") or [] if isinstance(item, dict)]
    items = [inspect_item(root, item) for item in planned_items if item.get("exists")]
    findings = [dict(f, deliverable_id=item["deliverable_id"]) for item in items for f in item["findings"]]
    if schema_version >= 5:
        if plan.get("kind") != "ad_delivery_plan":
            findings.append({"severity": "block", "code": "delivery_plan_schema_invalid",
                             "msg": "formal delivery plan 必须是 kind=ad_delivery_plan/schema_version>=5。"})
        if not isinstance(plan.get("render_profile"), dict) or not (plan.get("render_profile") or {}).get("sha256"):
            findings.append({"severity": "block", "code": "delivery_plan_render_profile_missing",
                             "msg": "formal delivery plan 缺当前 render profile ref/SHA。"})
        adaptation_top = plan.get("placement_adaptation") if isinstance(plan.get("placement_adaptation"), dict) else {}
        if not adaptation_top.get("sha256"):
            findings.append({"severity": "block", "code": "delivery_plan_adaptation_digest_missing",
                             "msg": "formal delivery plan 缺 placement adaptation logical SHA。"})
    if int((plan.get("summary") or {}).get("block") or 0):
        findings.append({
            "severity": "block", "code": "delivery_plan_prerequisites_blocked",
            "msg": "delivery plan 的 render profile / placement mapping / adaptation 先决条件仍有 block。",
        })
    findings.extend(textless_master_findings(root, plan))
    media_sha = {str(item.get("deliverable_id")): _sha256_file(_project_path(root, str(item.get("expected_path") or "")))
                 for item in planned_items if item.get("expected_path")}
    execution_sha = {
        str(item.get("deliverable_id")): _sha256_file(
            root / "生产数据" / "placement_adaptation_receipts" / f"{item.get('deliverable_id')}.json"
        )
        for item in planned_items if item.get("kind") == "reframe"
    }
    adaptation_ref = plan.get("placement_adaptation") if isinstance(plan.get("placement_adaptation"), dict) else {}
    report = {
        "schema_version": 2, "kind": "ad_delivery_qc", "items": items,
        "render_profile": plan.get("render_profile"),
        "delivery_plan_sha256": canonical_sha(plan),
        "media_sha256_by_deliverable": media_sha,
        "render_profile_sha256": ((plan.get("render_profile") or {}).get("sha256")
                                  if isinstance(plan.get("render_profile"), dict) else None),
        "placement_adaptation_sha256": adaptation_ref.get("sha256"),
        "adaptation_execution_sha256_by_deliverable": execution_sha,
        "summary": {
            "block": sum(1 for f in findings if f["severity"] == "block"),
            "warn": sum(1 for f in findings if f["severity"] == "warn"),
            "passed": sum(1 for item in items if item["passed"]),
        },
        "findings": findings,
    }
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root")
    ap.add_argument("--plan", default=None)
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    plan_path = Path(ns.plan) if ns.plan else root / "合成" / "delivery_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    report = build_report(root, plan)
    out = root / "合成" / "delivery_qc.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"# delivery QC block={report['summary']['block']} passed={report['summary']['passed']}")
    return 1 if report["summary"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
