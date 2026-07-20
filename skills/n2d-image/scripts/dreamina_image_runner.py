#!/usr/bin/env python3
"""Generate n2d episode images through the official Dreamina CLI.

This backend is for projects that cannot use Codex's text-only image path for
high-risk character shots.  It reuses the prompt/target/reference resolution
from ``codex_image_runner.py`` but submits real local reference images to
``dreamina image2image``.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import codex_image_runner as base


SOURCE = "skills/n2d-image/scripts/dreamina_image_runner.py"
LOG_REL = Path("生产数据") / "dreamina_image_runner.jsonl"
MAX_REFERENCES = 10
SIGNOFF_REL = Path("合规") / "image_backend_override.json"


def dreamina_image_signoff_allows(root: Path) -> bool:
    """Dreamina image spend is a signed exception; Codex image2 remains default."""
    try:
        payload = json.loads((root / SIGNOFF_REL).read_text(encoding="utf-8"))
    except Exception:
        return False
    if not isinstance(payload, dict) or payload.get("approved") is not True:
        return False
    scope = str(payload.get("scope") or payload.get("stage") or "image").lower()
    if "image" not in scope and "生图" not in scope:
        return False
    backend = str(
        payload.get("backend")
        or payload.get("canonical")
        or payload.get("image_backend")
        or ""
    ).lower()
    return "dreamina" in backend or "即梦" in backend or backend == "dreamina_official"


def require_dreamina_image_signoff(root: Path) -> None:
    if dreamina_image_signoff_allows(root):
        return
    raise RuntimeError(
        "全项目生图优先 Codex image2；n2d 的 Dreamina/即梦图片 runner 只能作为签核例外。"
        f"如确需使用，请先写 {SIGNOFF_REL.as_posix()}，包含 "
        '{"approved": true, "scope": "image", "backend": "dreamina_official", "reason": "..."}'
    )


def _field(body: str, label: str) -> str:
    m = re.search(rf"^\*\*{re.escape(label)}\*\*：([^\n]+)$", body, re.M)
    if not m:
        m = re.search(rf"^{re.escape(label)}：([^\n]+)$", body, re.M)
    return m.group(1).strip() if m else ""


def dreamina_reference_inputs(
    root: Path,
    target: base.Target,
    refs: Sequence[Path],
    episode: str,
    *,
    canonical_reset: bool = False,
) -> List[Dict[str, Any]]:
    """Describe the exact Dreamina attachments, including complete hashes."""
    role_by_path: Dict[str, tuple[str, str]] = {}
    try:
        bundle = base.reference_bundle_for_target(root, episode, target)
    except Exception:
        bundle = {}
    for item in bundle.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("kind") or item.get("role") or "reference")
        owner = str(
            item.get("owner") or item.get("character") or item.get("asset_id") or
            item.get("id") or item.get("ref") or ""
        )
        for raw in item.get("paths") or []:
            role_by_path[str(raw)] = (role, owner)

    inputs: List[Dict[str, Any]] = []
    for index, path in enumerate(refs, 1):
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = str(path)
        role, owner = role_by_path.get(rel, ("reference", path.stem))
        continuity_source = previous_continuity_source_path(root, target, episode)
        correction_source = rejected_correction_source_path(root, target)
        if not canonical_reset and index == 1 and (
            target.mode in {"midframe", "tailframe"}
            or (continuity_source is not None and path == continuity_source)
            or (correction_source is not None and path == correction_source)
        ):
            role = "source_frame"
            owner = target.clip
        inputs.append({
            "index": index,
            "role": role,
            "owner": owner,
            "actual_path": str(path),
            "rel_path": rel,
            "sha256": base.file_sha256(path),
        })
    return inputs


def build_dreamina_compiled_request(
    root: Path,
    episode: str,
    target: base.Target,
    reference_inputs: Sequence[Mapping[str, Any]],
    *,
    model_version: str = "",
    resolution_type: str = "",
    retry_guidance: str = "",
) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    if model_version:
        params["model_version"] = model_version
    if resolution_type:
        params["resolution_type"] = resolution_type
    compiled = base.compile_target_image_request(
        root,
        episode,
        target,
        reference_inputs,
        backend="dreamina",
        model=model_version,
        channel="official_cli",
        retry_guidance=retry_guidance,
        request_params_override=params,
    )
    lint = base.lint_compiled_image_prompt(compiled)
    if lint.get("errors"):
        raise ValueError("compiled Dreamina image request invalid: " + ", ".join(lint["errors"]))
    return compiled


def build_dreamina_prompt(
    root: Path,
    episode: str,
    target: base.Target,
    reference_inputs: Sequence[Mapping[str, Any]] = (),
    *,
    model_version: str = "",
    resolution_type: str = "",
    compiled_request: Optional[Mapping[str, Any]] = None,
    retry_guidance: str = "",
) -> str:
    """Return exactly the compiler text submitted to Dreamina."""
    compiled = dict(compiled_request or build_dreamina_compiled_request(
        root,
        episode,
        target,
        reference_inputs,
        model_version=model_version,
        resolution_type=resolution_type,
        retry_guidance=retry_guidance,
    ))
    return str(compiled.get("prompt") or "").strip()


def _reference_block(body: str) -> str:
    m = re.search(r"(?ms)(?:\*\*)?参考图(?:\*\*)?.*?(?=^###\s+|^\*\*导演视角八维\*\*|^##\s+|\Z)", body)
    return m.group(0) if m else ""


def select_dreamina_reference_paths(
    target: base.Target,
    bundle: Mapping[str, Any],
    paths: Sequence[Path],
    *,
    root: Path,
    source_path: Optional[Path],
) -> List[Path]:
    """Balance Dreamina's ten attachments across identities and scene evidence.

    Merely prepending every registry-only angle can let the first character's
    large view pack consume the whole backend cap.  Convert the concrete paths
    into the same role/owner rows used by the backend-neutral selector so each
    depicted identity receives a face/body anchor before extra angles, while a
    location and interacted plot asset still retain context slots.
    """
    metadata: Dict[str, tuple[str, str, int]] = {}

    def character_priority(path: Path, index: int) -> int:
        stem = path.stem.lower()
        if any(token in stem for token in ("脸部特写", "face_anchor", "face")):
            return 10
        if index == 0:
            return 20
        if any(token in stem for token in ("半身", "全身", "outfit")):
            return 30
        if any(token in stem for token in ("45度", "_侧", "侧面")):
            return 40
        if any(token in stem for token in ("表情", "expression")):
            return 45
        return 50

    for item in bundle.get("items") or []:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("kind") or item.get("role") or "reference")
        owner = str(
            item.get("owner") or item.get("character") or item.get("asset_id")
            or item.get("id") or item.get("ref") or ""
        )
        for index, rel in enumerate(item.get("paths") or []):
            path = root / str(rel)
            if role == "character":
                priority = character_priority(path, index)
            elif role == "style":
                priority = 60
            elif owner.startswith("LOC_"):
                priority = 70
            elif role == "asset":
                priority = 80
            else:
                priority = 100
            metadata.setdefault(str(path), (role, owner, priority))

    rows: List[Dict[str, Any]] = []
    seen: set[Path] = set()
    for sequence, path in enumerate(paths):
        if path in seen:
            continue
        seen.add(path)
        role, owner, priority = metadata.get(
            str(path), ("reference", path.stem, 100)
        )
        if source_path is not None and path == source_path:
            role, owner, priority = "source_frame", target.clip, 0
        rows.append({
            "role": role,
            "owner": owner,
            "priority": priority,
            "sequence": sequence,
            "_path": path,
        })
    if target.shot == "Clip_04_first":
        # The canonical CHAR_04 front/half-body cards prove the humanoid
        # topology but do not prove the unusual prone pose.  Seedream tends to
        # satisfy "tiger lying down" by collapsing it into an ordinary
        # quadruped.  Reuse the exact-hash accepted S02A pixels as a dedicated
        # pose/topology witness: they contain the same tiger-headed humanoid
        # already lying in this location.  This remains reference evidence,
        # not a continuity source, so Clip04 may still change the foreground
        # blocking and remove the broken saber.
        target_parts = Path(target.rel_path).parts
        episode_name = target_parts[1] if len(target_parts) > 1 else ""
        pose_source_rel = str(Path(target.rel_path).parent / "Clip02_first.png")
        pose_source_path = root / pose_source_rel
        pose_rel = str(
            Path("生产数据") / "reference_crops" / episode_name
            / "Clip02_tiger_prone_pose.png"
        )
        pose_path = root / pose_rel
        pose_manifest_path = pose_path.with_suffix(".json")
        pose_manifest: Mapping[str, Any] = {}
        if pose_manifest_path.is_file():
            try:
                loaded = json.loads(pose_manifest_path.read_text(encoding="utf-8"))
                pose_manifest = loaded if isinstance(loaded, Mapping) else {}
            except (OSError, json.JSONDecodeError):
                pose_manifest = {}
        crop_fresh = (
            pose_source_path.is_file()
            and pose_path.is_file()
            and str(pose_manifest.get("source") or "") == pose_source_rel
            and str(pose_manifest.get("source_sha256") or "") == base.file_sha256(pose_source_path)
            and str(pose_manifest.get("output_sha256") or "") == base.file_sha256(pose_path)
        )
        if crop_fresh and _accepted_current_hash(root, pose_source_rel):
            rows.append({
                "role": "source_frame",
                "owner": "Clip_02_tiger_prone_pose",
                "priority": 1,
                "sequence": -1,
                "_path": pose_path,
            })
    if target.shot == "Clip_02_first" and "尸场空间一次建立" in str(target.section.body or ""):
        # S02A happens before the complete hengdao enters the visual beat.  The
        # merged Clip reference bundle also contains PROP_横刀/WEAPON_01 for
        # later sub-shots; attaching it here repeatedly made the provider place
        # a complete foreground sword despite the first-frame contract.
        rows = [
            row for row in rows
            if not (
                str(row.get("role") or "") == "asset"
                and str(row.get("owner") or "") in {"PROP_横刀", "WEAPON_01"}
            )
        ]
    rows.sort(key=lambda row: (int(row["priority"]), int(row["sequence"])))
    selected = base.select_codex_reference_inputs(target, rows, MAX_REFERENCES)
    return [row["_path"] for row in selected]


def _accepted_current_hash(root: Path, rel_path: str) -> bool:
    """Whether the latest executor QA receipt accepts the exact current pixels."""
    current = root / rel_path
    if not current.is_file():
        return False
    current_sha = base.file_sha256(current)
    events = root / "生产数据" / "production_events.jsonl"
    if not events.is_file():
        return False
    latest: Optional[Mapping[str, Any]] = None
    with events.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            generation = row.get("generation") if isinstance(row, Mapping) else None
            if (
                row.get("stage") == "image"
                and row.get("event") == "qa"
                and isinstance(generation, Mapping)
                and generation.get("asset") == rel_path
            ):
                latest = row
    if not isinstance(latest, Mapping):
        return False
    generation = latest.get("generation") if isinstance(latest.get("generation"), Mapping) else {}
    meta = latest.get("meta") if isinstance(latest.get("meta"), Mapping) else {}
    return generation.get("status") == "accepted" and meta.get("artifact_sha256") == current_sha


def previous_continuity_source_path(root: Path, target: base.Target, episode: str) -> Optional[Path]:
    """Use the accepted prior Clip final frame when story state relays exactly."""
    if target.mode != "firstframe":
        return None
    beat = base.storyboard_anchor_beat(root, episode, target)
    if beat.get("faceless_insert"):
        return None
    data = base.load_json_file(root / "脚本" / episode / "storyboard.json")
    clips = [row for row in data.get("clips") or [] if isinstance(row, Mapping)]
    target_suffix = str(target.clip).replace("Clip_", "CLIP")
    current_index = next((
        index for index, row in enumerate(clips)
        if str(row.get("id") or "").upper().endswith(target_suffix.upper())
    ), -1)
    if current_index <= 0:
        return None
    current = clips[current_index]
    previous = clips[current_index - 1]
    current_cont = current.get("continuity") if isinstance(current.get("continuity"), Mapping) else {}
    previous_cont = previous.get("continuity") if isinstance(previous.get("continuity"), Mapping) else {}
    discontinuity_text = " ".join((
        str(previous_cont.get("seam_mode") or ""),
        str(previous_cont.get("transition") or ""),
        str((previous_cont.get("seam_evidence") or {}).get("reason") or "")
        if isinstance(previous_cont.get("seam_evidence"), Mapping) else "",
        str(current_cont.get("previous_start_state_note") or ""),
    ))
    if (
        "intentional_discontinuity" in discontinuity_text
        or re.search(r"时间回切|时间跳切|闪回|倒叙|回到.{0,8}前|十分钟前", discontinuity_text)
    ):
        return None
    start_state = re.sub(r"\s+", "", str(current_cont.get("start_state") or ""))
    end_state = re.sub(r"\s+", "", str(previous_cont.get("end_state") or ""))
    if not start_state or start_state != end_state:
        return None
    candidates: List[str] = []
    for key in ("tailframe_png", "endframe_png"):
        if previous_cont.get(key):
            candidates.append(str(previous_cont.get(key)))
    anchors = previous_cont.get("anchors") if isinstance(previous_cont.get("anchors"), list) else []
    for anchor in reversed(anchors):
        if isinstance(anchor, Mapping) and anchor.get("anchor_png"):
            candidates.append(str(anchor.get("anchor_png")))
    for key in ("firstframe_png",):
        if previous_cont.get(key):
            candidates.append(str(previous_cont.get(key)))
    previous_id = str(previous.get("id") or "")
    if match := re.search(r"CLIP(\d+)$", previous_id, re.I):
        candidates.append(f"出图/{episode}/图片/EP01_CLIP{int(match.group(1)):02d}.png")
    for rel in candidates:
        if _accepted_current_hash(root, rel):
            return root / rel
    return None


def rejected_correction_source_path(root: Path, target: base.Target) -> Optional[Path]:
    """Use the exact rejected pixels as source for a localized same-target fix."""
    current = root / target.rel_path
    if not current.is_file():
        return None
    if not base.latest_hash_bound_executor_visual_rejection(root, target):
        return None
    return current


def prompt_reference_paths(
    root: Path,
    target: base.Target,
    episode: str,
    *,
    canonical_reset: bool = False,
) -> List[Path]:
    paths: List[Path] = []
    seen: set[Path] = set()

    def add(rel: str) -> None:
        text = rel.strip().strip("`")
        if not text.startswith("出图/"):
            return
        path = root / text
        if path in seen or path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            return
        if not path.is_file():
            return
        seen.add(path)
        paths.append(path)

    source_path: Optional[Path] = None if canonical_reset else (
        rejected_correction_source_path(root, target)
        or previous_continuity_source_path(root, target, episode)
    )
    if source_path is not None:
        seen.add(source_path)
        paths.append(source_path)
    elif not canonical_reset and target.mode != "firstframe":
        try:
            source = root / base.target_for_shot(target.clip, target.section, episode).rel_path
            if source.is_file():
                seen.add(source)
                paths.append(source)
                source_path = source
        except Exception:
            pass

    block = _reference_block(target.section.body)
    for raw in base.backticked(block):
        add(raw)

    # Always merge the registry-resolved bundle (not only when prose is empty):
    # a hand-written 参考图 block listing any one placeholder image must NOT
    # suppress the carried-identity face anchors — that was the Dreamina-side
    # replica of the 定妆 face-drift bug. Character (carried-identity) face anchors
    # are prepended so they survive the MAX_REFERENCES cap; everything else appends.
    bundle = base.reference_bundle_for_target(root, episode, target)
    anchor_beat = base.storyboard_anchor_beat(root, episode, target)
    beat_text = f"{anchor_beat.get('desc') or ''} {anchor_beat.get('video_prompt') or ''}"
    anchor_character_filter = bool(
        anchor_beat.get("single_reaction")
        or anchor_beat.get("faceless_insert")
        or anchor_beat.get("detail_insert")
    )
    anchor_focus_ids = set(anchor_beat.get("focus_ids") or []) if anchor_character_filter else set()
    excluded_character_paths: set[Path] = set()
    face_first: List[Path] = []
    for item in bundle.get("items") or []:
        if str(item.get("kind")) != "character":
            continue
        owner = str(
            item.get("owner") or item.get("character") or item.get("id") or
            item.get("ref") or ""
        )
        owner_id = owner.split("/", 1)[0]
        if anchor_character_filter and owner_id not in anchor_focus_ids:
            for rel in item.get("paths") or []:
                excluded_character_paths.add(root / str(rel))
            continue
        for rel in item.get("paths") or []:
            p = root / str(rel)
            if p.is_file() and p not in seen and p not in face_first:
                face_first.append(p)
    # Relay/edit backends require attachment 1 to be the real source frame.
    # Face-first prioritisation must never move a face atlas into that slot.
    prefix = [source_path] if source_path is not None else []
    paths = prefix + face_first + [
        p for p in paths
        if p not in prefix and p not in face_first and p not in excluded_character_paths
    ]
    excluded_asset_paths: set[Path] = set()
    for item in bundle.get("items") or []:
        if str(item.get("kind")) == "character":
            continue
        if anchor_beat and str(item.get("kind")) == "asset":
            asset_id = str(item.get("id") or "")
            asset_type = str(item.get("type") or "").lower()
            asset_token = re.sub(r"^(?:PROP|WEAPON|VFX|OUTFIT)_", "", asset_id, flags=re.I)
            is_scene = asset_type in {"scene", "location", "loc"} or asset_id.startswith("LOC_")
            if not is_scene and asset_id not in beat_text and asset_token not in beat_text:
                for rel in item.get("paths") or []:
                    excluded_asset_paths.add(root / str(rel))
                continue
        for rel in item.get("paths") or []:
            add(str(rel))
    paths = [path for path in paths if path not in excluded_asset_paths]
    if canonical_reset:
        # A rejected target can re-enter through the registry-resolved bundle
        # even after the explicit correction source above is disabled.  That
        # silently defeats canonical reset and causes the backend to reproduce
        # the same bad pixels/composition.  Never attach the current output to
        # itself during a reset; keep the independent identity/style evidence.
        current_target = root / target.rel_path
        paths = [path for path in paths if path != current_target]
    return select_dreamina_reference_paths(
        target,
        bundle,
        paths,
        root=root,
        source_path=source_path,
    )


def submit_id_from(text: str) -> str:
    patterns = [
        r'"submit_id"\s*:\s*"([^"]+)"',
        r"submit_id\s*[=:]\s*([A-Za-z0-9._-]+)",
        r"submit id\s*[=:]\s*([A-Za-z0-9._-]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1)
    return ""


def recover_submit_id_from_saved_tasks(prompt: str) -> str:
    """Recover a paid task when the CLI submitted it but history lookup errored."""
    proc = subprocess.run(
        ["dreamina", "list_task", "--limit", "20"],
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    try:
        rows = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return ""
    if not isinstance(rows, list):
        return ""
    for row in rows:
        if not isinstance(row, Mapping) or str(row.get("prompt") or "") != prompt:
            continue
        sid = str(row.get("submit_id") or "").strip()
        if sid:
            return sid
    return ""


def image_candidates(path: Path) -> List[Path]:
    if not path.is_dir():
        return []
    candidates: List[Path] = []
    for suffix in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
        candidates.extend(path.rglob(suffix))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def materialize_png(src: Path, out_path: Path) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".png":
        shutil.copy2(src, out_path)
        return base.png_valid(out_path)
    proc = subprocess.run(
        ["sips", "-s", "format", "png", str(src), "--out", str(out_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return proc.returncode == 0 and base.png_valid(out_path)


def run_dreamina(
    target: base.Target,
    *,
    root: Path,
    episode: str,
    temp_path: Path,
    timeout_sec: Optional[float],
    poll_sec: int,
    model_version: str,
    resolution_type: str,
    refs: Optional[Sequence[Path]] = None,
    compiled_request: Optional[Mapping[str, Any]] = None,
    recover_submit_id: str = "",
) -> tuple[bool, str, str, List[Path]]:
    resolved_refs = list(refs) if refs is not None else prompt_reference_paths(root, target, episode)
    if not resolved_refs:
        return False, "", "no ready reference images resolved for Dreamina image2image", resolved_refs
    reference_inputs = dreamina_reference_inputs(root, target, resolved_refs, episode)
    retry_guidance = base.target_qc_retry_guidance(root, episode, target)
    compiled = dict(compiled_request or build_dreamina_compiled_request(
        root,
        episode,
        target,
        reference_inputs,
        model_version=model_version,
        resolution_type=resolution_type,
        retry_guidance=retry_guidance,
    ))
    prompt = build_dreamina_prompt(
        root,
        episode,
        target,
        reference_inputs,
        model_version=model_version,
        resolution_type=resolution_type,
        compiled_request=compiled,
        retry_guidance=retry_guidance,
    )
    ratio = base.aspect_ratio(root)
    download_dir = temp_path.parent / f"{temp_path.stem}_download"
    if download_dir.exists():
        shutil.rmtree(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    sid = str(recover_submit_id or "").strip()
    if not sid:
        cmd = [
            "dreamina",
            "image2image",
            "--images",
            ",".join(str(p) for p in resolved_refs),
            "--prompt",
            prompt,
            "--ratio",
            ratio,
            "--poll",
            str(max(0, min(poll_sec, int(timeout_sec or poll_sec)))),
        ]
        if model_version:
            cmd.extend(["--model_version", model_version])
        if resolution_type:
            cmd.extend(["--resolution_type", resolution_type])
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_sec,
        )
        combined = "\n".join(p for p in (proc.stdout, proc.stderr) if p)
        if proc.returncode != 0:
            if "get_history_by_ids" in combined or "ret=2008" in combined:
                sid = recover_submit_id_from_saved_tasks(prompt)
            if not sid:
                return False, "", f"dreamina image2image exit {proc.returncode}: {combined}", resolved_refs
        if not sid:
            sid = submit_id_from(combined)
        if not sid:
            return False, "", f"dreamina output did not include submit_id: {combined[:1000]}", resolved_refs
    deadline = time.monotonic() + float(timeout_sec or 900)
    qout = ""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False, sid, f"dreamina task still had no image at timeout: {qout[:1000]}", resolved_refs
        query = subprocess.run(
            ["dreamina", "query_result", "--submit_id", sid, "--download_dir", str(download_dir)],
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=remaining,
        )
        qout = "\n".join(p for p in (query.stdout, query.stderr) if p)
        if query.returncode != 0:
            return False, sid, f"dreamina query_result exit {query.returncode}: {qout}", resolved_refs
        candidates = image_candidates(download_dir)
        if candidates:
            break
        try:
            status_payload = json.loads(query.stdout or "{}")
        except json.JSONDecodeError:
            status_payload = {}
        status = str(status_payload.get("gen_status") or "").strip().lower()
        queue_status = str((status_payload.get("queue_info") or {}).get("queue_status") or "").strip().lower()
        if status in {"failed", "fail", "error", "cancelled", "canceled"} or queue_status in {
            "failed", "fail", "error", "cancelled", "canceled",
        }:
            return False, sid, f"dreamina task ended without image: {qout[:1000]}", resolved_refs
        # `querying` / `Generating` is a normal async state.  Re-query the same
        # submit id instead of declaring failure and charging for a duplicate.
        time.sleep(min(max(1, poll_sec), max(0.0, remaining)))
    if not materialize_png(candidates[0], temp_path):
        return False, sid, f"downloaded result is not a valid PNG and conversion failed: {candidates[0]}", resolved_refs
    return True, sid, "", resolved_refs


def archive_existing(root: Path, rel_path: str, task_id: str) -> Optional[Path]:
    final = root / rel_path
    if not final.exists():
        return None
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = root / "废料" / "出图" / rel_path.replace("出图/", "").rsplit("/", 1)[0] / f"dreamina_rerun_{task_id}_{stamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / final.name
    shutil.copy2(final, archive_path)
    return archive_path


def append_log(root: Path, row: dict) -> None:
    path = root / LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def record_event(
    root: Path,
    episode: str,
    target: base.Target,
    *,
    status: str,
    duration_sec: float,
    task_id: str,
    seed: str,
    temp_path: Path,
    submit_id: str,
    refs: List[Path],
    archive_path: Optional[Path],
    compiled_request: Optional[Mapping[str, Any]] = None,
    submitted_prompt: str = "",
    compiled_receipt: Optional[Path] = None,
    error: str = "",
) -> None:
    compiled = dict(compiled_request or {})
    metrics = compiled.get("metrics") if isinstance(compiled.get("metrics"), Mapping) else {}
    experiment = compiled.get("experiment") if isinstance(compiled.get("experiment"), Mapping) else {}
    prompt_sha = base.sha256_text(submitted_prompt)
    image_model = str(compiled.get("model") or "Seedream 5.0")
    channel = str(compiled.get("channel") or "Dreamina/即梦官方 CLI")
    request_params = compiled.get("request_params") if isinstance(compiled.get("request_params"), Mapping) else {}
    model_version = str(request_params.get("model_version") or image_model)
    backend_version = f"dreamina-official-cli:model-{model_version}"
    actual_inputs: List[str] = []
    ref_rows: List[Dict[str, str]] = []
    for ref in refs[:MAX_REFERENCES]:
        try:
            rel = str(ref.relative_to(root))
        except ValueError:
            rel = str(ref)
        actual_inputs.append(rel)
        ref_rows.append({"path": rel, "sha256": base.file_sha256(ref) if ref.is_file() else ""})
    reference_bundle_sha = str(compiled.get("reference_inputs_sha256") or "") or base.sha256_text(
        json.dumps(ref_rows, ensure_ascii=False, sort_keys=True)
    )
    route_hash = base.sha256_text(
        f"dreamina|{image_model}|{channel}|{target.mode}|{target.shot}|{target.rel_path}"
    )
    capability_path = root / "生产数据" / "image_backend_capabilities" / "dreamina.json"
    capability_id = (
        f"{capability_path.relative_to(root)}#{base.file_sha256(capability_path)[:12]}"
        if capability_path.is_file()
        else "dreamina-refresh-missing"
    )
    final_path = root / target.rel_path
    artifact_sha = base.optional_file_sha256(final_path) or base.optional_file_sha256(temp_path)
    settings_sha = base.optional_file_sha256(root / "_设置.md")
    identity_registry_sha = base.optional_file_sha256(root / "出图" / "共享" / "identity_registry.json")
    asset_registry_sha = base.optional_file_sha256(root / "出图" / "共享" / "asset_registry.json")
    adapter_version = f"dreamina_image_runner.py@{base.optional_file_sha256(Path(__file__))[:12]}"
    qc_version = f"image_qc.py@{base.optional_file_sha256(base.repo_root() / base.IMAGE_QC)[:12]}"
    input_fingerprint = base.sha256_text(json.dumps({
        "asset": target.rel_path,
        "mode": target.mode,
        "prompt_sha256": prompt_sha,
        "compiled_request_sha256": compiled.get("compiled_request_sha256") or "",
        "reference_bundle_sha256": reference_bundle_sha,
        "route_hash": route_hash,
        "settings_sha256": settings_sha,
        "identity_registry_sha256": identity_registry_sha,
        "asset_registry_sha256": asset_registry_sha,
        "requested_seed": seed,
    }, ensure_ascii=False, sort_keys=True))
    recipe_hash = base.sha256_text(json.dumps({
        "input_fingerprint": input_fingerprint,
        "artifact_sha256": artifact_sha,
        "backend_version": backend_version,
        "model_version": model_version,
    }, ensure_ascii=False, sort_keys=True))
    event = "redraw" if archive_path or os.environ.get("N2D_REASON") == "rerun" else "generation"
    cmd = [
        sys.executable,
        str(base.repo_root() / base.DASHBOARD),
        "record",
        str(root),
        "--episode",
        episode,
        "--stage",
        "image",
        "--event",
        event,
        "--asset",
        target.rel_path,
        "--status",
        status,
        "--provider",
        "Dreamina",
        "--duration-sec",
        f"{duration_sec:.3f}",
        "--unit",
        "credits",
        "--meta",
        f"mode=dreamina_image2image_{target.mode}",
        "--meta",
        f"task={task_id}",
        "--meta",
        f"shot={target.shot}",
        "--meta",
        f"submit_id={submit_id}",
        "--meta",
        f"requested_seed={seed}",
        "--meta",
        "effective_seed=",
        "--meta",
        "seed_effective=false",
        "--meta",
        "seed_support=unsupported_or_unknown",
        "--meta",
        "seed_strategy=fixed_pool",
        "--meta",
        f"reference_count={len(refs)}",
        "--meta",
        f"model={image_model}",
        "--meta",
        f"model_version={model_version}",
        "--meta",
        f"channel={channel}",
        "--meta",
        f"route_hash={route_hash}",
        "--meta",
        f"capability_evidence_id={capability_id}",
        "--meta",
        f"recipe_hash={recipe_hash}",
        "--meta",
        f"prompt_sha256={prompt_sha}",
        "--meta",
        f"actual_submit_prompt_sha256={prompt_sha}",
        "--meta",
        f"prompt_compiler_kind={compiled.get('kind') or ''}",
        "--meta",
        f"prompt_compiler_version={compiled.get('version') or ''}",
        "--meta",
        f"prompt_profile_version={compiled.get('profile_version') or ''}",
        "--meta",
        f"prompt_profile={compiled.get('profile') or ''}",
        "--meta",
        f"prompt_task_type={compiled.get('task_type') or ''}",
        "--meta",
        f"source_contract_sha256={compiled.get('source_contract_sha256') or ''}",
        "--meta",
        f"source_contract_text_sha256={compiled.get('source_contract_text_sha256') or ''}",
        "--meta",
        f"execution_context_sha256={compiled.get('execution_context_sha256') or ''}",
        "--meta",
        f"compiled_request_sha256={compiled.get('compiled_request_sha256') or ''}",
        "--meta",
        f"compiled_prompt_chars={metrics.get('prompt_chars') or 0}",
        "--meta",
        f"compiled_estimated_text_tokens={metrics.get('estimated_text_tokens') or 0}",
        "--meta",
        f"image_prompt_experiment_id={experiment.get('experiment_id') or ''}",
        "--meta",
        f"image_prompt_variant={experiment.get('variant') or ''}",
        "--meta",
        "compiled_request_params=" + json.dumps(compiled.get("request_params") or {}, ensure_ascii=False, sort_keys=True),
        "--meta",
        f"reference_bundle_sha256={reference_bundle_sha}",
        "--meta",
        f"backend_version={backend_version}",
        "--meta",
        f"quality_tier={request_params.get('resolution_type') or 'project_default'}",
        "--meta",
        f"actual_image_inputs={'|'.join(actual_inputs) if actual_inputs else 'none'}",
        "--meta",
        f"input_fingerprint={input_fingerprint}",
        "--meta",
        f"settings_sha256={settings_sha}",
        "--meta",
        f"identity_registry_sha256={identity_registry_sha}",
        "--meta",
        f"asset_registry_sha256={asset_registry_sha}",
        "--meta",
        f"artifact_sha256={artifact_sha}",
        "--meta",
        f"adapter_version={adapter_version}",
        "--meta",
        f"qc_version={qc_version}",
        "--meta",
        f"temp_output={temp_path}",
        "--meta",
        f"source={SOURCE}",
    ]
    for ref in refs[:MAX_REFERENCES]:
        try:
            rel = ref.relative_to(root)
        except ValueError:
            rel = ref
        cmd.extend(["--meta", f"reference={rel}"])
        if ref.is_file():
            cmd.extend(["--meta", f"reference_sha256={rel}#{base.file_sha256(ref)}"])
    if compiled_receipt:
        cmd.extend(["--meta", f"compiled_request_receipt={compiled_receipt}"])
    if target.mode == "midframe" and status == "pass":
        try:
            source_image = base.target_for_shot(target.clip, target.section, episode).rel_path
        except Exception:
            source_image = ""
        cmd.extend(["--meta", "self_check=pass", "--meta", "midframe_role=between_first_and_end"])
        if source_image:
            cmd.extend(["--meta", f"source_image={source_image}"])
    if archive_path:
        cmd.extend(["--redraw-reason", f"{task_id} Dreamina image2image 真实参考图重出 {target.shot}", "--redraw-category", "backend_migration"])
        cmd.extend(["--meta", f"archived_previous={archive_path}"])
    if error:
        cmd.extend(["--meta", f"error={error[:500]}"])
    subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def latest_recorded_status(root: Path, task_id: str, rel_path: str) -> str:
    path = root / "生产数据" / "production_events.jsonl"
    if not path.is_file():
        return ""
    status = ""
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("stage") != "image":
                continue
            generation = event.get("generation")
            meta = event.get("meta")
            if not isinstance(generation, dict) or not isinstance(meta, dict):
                continue
            if generation.get("asset") == rel_path and str(meta.get("task") or "") == task_id:
                status = str(generation.get("status") or "")
    return status.lower()


def process_target(
    root: Path,
    episode: str,
    target: base.Target,
    *,
    task_id: str,
    timeout_sec: Optional[float],
    poll_sec: int,
    model_version: str,
    resolution_type: str,
    dry_run: bool,
    force: bool,
    recover_submit_id: str = "",
    canonical_reset: bool = False,
) -> bool:
    seed = base.logical_seed(root, episode, target.shot, target.rel_path)
    final = root / target.rel_path
    temp_dir = Path(tempfile.gettempdir()) / "n2d_dreamina_image_runner" / (task_id or "manual")
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{episode}_{base.temp_token(target.shot)}_{Path(target.rel_path).stem}.png"
    previous_status = latest_recorded_status(root, task_id, target.rel_path)
    if canonical_reset and not base.latest_hash_bound_executor_visual_rejection(root, target):
        print(
            f"[fail] {target.shot}: --canonical-reset 只允许当前 PNG 的当前 hash 已有 executor_visual qa rejected 收据时使用",
            file=sys.stderr,
        )
        return False
    refs = prompt_reference_paths(root, target, episode, canonical_reset=canonical_reset)
    reference_inputs = dreamina_reference_inputs(
        root, target, refs, episode, canonical_reset=canonical_reset,
    )
    retry_guidance = base.target_qc_retry_guidance(root, episode, target)
    try:
        compiled_request = build_dreamina_compiled_request(
            root,
            episode,
            target,
            reference_inputs,
            model_version=model_version,
            resolution_type=resolution_type,
            retry_guidance=retry_guidance,
        )
    except ValueError as exc:
        print(f"[fail] {target.shot}: {exc}", file=sys.stderr)
        return False
    submitted_prompt = build_dreamina_prompt(
        root,
        episode,
        target,
        reference_inputs,
        model_version=model_version,
        resolution_type=resolution_type,
        compiled_request=compiled_request,
        retry_guidance=retry_guidance,
    )
    if dry_run:
        print(json.dumps({
            "shot": target.shot,
            "mode": target.mode,
            "target": target.rel_path,
            "references": [str(p) for p in refs],
            "reference_count": len(refs),
            "logical_seed": seed,
            "skip_existing_pass": (not force and previous_status == "pass" and base.png_valid(final)),
            "prompt_compiler": {
                "profile_version": compiled_request.get("profile_version"),
                "profile": compiled_request.get("profile"),
                "task_type": compiled_request.get("task_type"),
                "compiled_request_sha256": compiled_request.get("compiled_request_sha256"),
                "actual_submit_prompt_sha256": base.sha256_text(submitted_prompt),
                "metrics": compiled_request.get("metrics"),
                "lint": compiled_request.get("lint"),
            },
        }, ensure_ascii=False))
        return True
    if not force and previous_status == "pass" and base.png_valid(final):
        print(f"[skip] {target.shot} already has Dreamina pass record for {task_id}: {target.rel_path}")
        return True

    # Pre-spend interlock (same as the Codex backend): a plate that depicts a
    # character must attach a real face anchor, else it renders a new drifting face.
    bundle = base.reference_bundle_for_target(root, episode, target)
    attached_rel: List[str] = []
    for p in refs:
        try:
            attached_rel.append(str(p.relative_to(root)))
        except ValueError:
            attached_rel.append(str(p))
    if (
        base.carried_identity_unanchored(bundle, attached_rel)
        and os.environ.get("N2D_ALLOW_UNANCHORED_IDENTITY_PLATE") != "1"
    ):
        carried = "、".join(str(c) for c in bundle.get("carried_identity") or [])
        print(
            f"[fail] {target.shot}: 本图声明承载角色身份（carries_identity={carried}），"
            "但没有任何角色脸锚作为 Dreamina image2image 参考传入——会另画一张新脸（定妆脸漂成因）。"
            "请把承载角色的脸部特写/正面参考置 ready，或设 N2D_ALLOW_UNANCHORED_IDENTITY_PLATE=1 显式豁免。",
            file=sys.stderr,
        )
        base.log_unanchored_friction(root, episode, target.shot, bundle.get("carried_identity"), "Dreamina")
        return False

    started = time.monotonic()
    archive_path: Optional[Path] = None
    submit_id = ""
    error = ""
    ok = False
    compiled_receipt: Optional[Path] = None
    try:
        if temp_path.exists():
            temp_path.unlink()
        compiled_receipt = base.write_compiled_request_receipt(
            root,
            episode,
            target,
            compiled_request,
            submitted_prompt,
        )
        ok, submit_id, error, refs = run_dreamina(
            target,
            root=root,
            episode=episode,
            temp_path=temp_path,
            timeout_sec=timeout_sec,
            poll_sec=poll_sec,
            model_version=model_version,
            resolution_type=resolution_type,
            refs=refs,
            compiled_request=compiled_request,
            recover_submit_id=recover_submit_id,
        )
        if ok:
            archive_path = archive_existing(root, target.rel_path, task_id)
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temp_path, final)
            ok = base.png_valid(final)
            if not ok:
                error = f"moved Dreamina output is not a valid PNG: {final}"
    except subprocess.TimeoutExpired:
        error = f"dreamina timed out after {timeout_sec}s"
    except Exception as exc:  # pragma: no cover
        error = f"{type(exc).__name__}: {exc}"

    duration = time.monotonic() - started
    record_event(
        root,
        episode,
        target,
        status="pass" if ok else "fail",
        duration_sec=duration,
        task_id=task_id,
        seed=seed,
        temp_path=temp_path,
        submit_id=submit_id,
        refs=refs,
        archive_path=archive_path,
        compiled_request=compiled_request,
        submitted_prompt=submitted_prompt,
        compiled_receipt=compiled_receipt,
        error=error,
    )
    append_log(root, {
        "ts": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "episode": episode,
        "shot": target.shot,
        "mode": target.mode,
        "target": target.rel_path,
        "status": "pass" if ok else "fail",
        "duration_sec": round(duration, 3),
        "submit_id": submit_id,
        "reference_count": len(refs),
        "reference_sha256": [base.file_sha256(path) for path in refs if path.is_file()],
        "logical_seed": seed,
        "seed_effective": False,
        "prompt_compiler_kind": compiled_request.get("kind"),
        "prompt_compiler_version": compiled_request.get("version"),
        "prompt_profile_version": compiled_request.get("profile_version"),
        "prompt_profile": compiled_request.get("profile"),
        "prompt_task_type": compiled_request.get("task_type"),
        "source_contract_sha256": compiled_request.get("source_contract_sha256"),
        "execution_context_sha256": compiled_request.get("execution_context_sha256"),
        "compiled_request_sha256": compiled_request.get("compiled_request_sha256"),
        "actual_submit_prompt_sha256": base.sha256_text(submitted_prompt),
        "compiled_request_receipt": str(compiled_receipt or ""),
        "request_params": compiled_request.get("request_params") or {},
        "prompt_metrics": compiled_request.get("metrics") or {},
        "image_prompt_experiment_id": (compiled_request.get("experiment") or {}).get("experiment_id"),
        "image_prompt_variant": (compiled_request.get("experiment") or {}).get("variant"),
        "error": error[:1000],
    })
    if ok:
        print(f"[pass] {target.shot} -> {target.rel_path} ({submit_id})")
    else:
        print(f"[fail] {target.shot}: {error}", file=sys.stderr)
    return ok


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Dreamina official CLI image2image adapter for n2d image tasks")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--shots", default=os.environ.get("N2D_AFFECTED_SHOTS", ""))
    ap.add_argument(
        "--shared-targets",
        default="",
        help="comma-separated shared assets to generate; use 'all' for all shared prompt targets",
    )
    ap.add_argument("--shared-offset", type=int, default=0, help="zero-based offset into resolved shared targets")
    ap.add_argument("--max-shared-targets", type=int, help="maximum number of resolved shared targets to process")
    ap.add_argument("--max-shots", type=int)
    ap.add_argument("--timeout-sec", type=float, default=float(os.environ.get("N2D_DREAMINA_IMAGE_TIMEOUT", "900")))
    ap.add_argument("--poll-sec", type=int, default=int(os.environ.get("N2D_DREAMINA_IMAGE_POLL", "300")))
    ap.add_argument("--model-version", default=os.environ.get("N2D_DREAMINA_IMAGE_MODEL", "5.0"))
    ap.add_argument("--resolution-type", default=os.environ.get("N2D_DREAMINA_IMAGE_RESOLUTION", "2k"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stop-on-fail", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-image-qc", action="store_true")
    ap.add_argument("--skip-final-gate", action="store_true")
    ap.add_argument("--skip-preflight", action="store_true", help="skip the pre-spend image_preflight gate (logs a dashboard waiver)")
    ap.add_argument("--recover-submit-id", default="", help="download/finalize an existing Dreamina submit id without creating a new paid task")
    ap.add_argument(
        "--canonical-reset",
        action="store_true",
        help="after an exact-hash visual rejection, rebuild from canonical identity/asset refs without a rejected/continuity source frame",
    )
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    root = Path(ns.root).resolve()
    episode = base.normalize_episode(ns.episode)
    shots = base.split_csv(ns.shots)
    shared_targets = base.split_csv(ns.shared_targets)
    if not shots and not shared_targets:
        raise SystemExit("--shots/--shared-targets or N2D_AFFECTED_SHOTS is required")
    if ns.max_shots is not None:
        shots = shots[: ns.max_shots]
    if not ns.dry_run:
        try:
            require_dreamina_image_signoff(root)
        except RuntimeError as exc:
            print(f"[block] {exc}", file=sys.stderr)
            return 1

    targets: List[base.Target] = []
    if shared_targets:
        resolved_shared = base.build_shared_targets(root, shared_targets)
        start = max(ns.shared_offset, 0)
        end = start + ns.max_shared_targets if ns.max_shared_targets is not None else None
        targets.extend(resolved_shared[start:end])
    if shots:
        targets.extend(base.build_targets(root, episode, shots))
    if not targets:
        raise SystemExit("no targets resolved")
    if ns.recover_submit_id and len(targets) != 1:
        raise SystemExit("--recover-submit-id requires exactly one resolved target")
    task_id = os.environ.get("N2D_TASK_ID") or f"dreamina-{episode}"

    strict_single_review = base.strict_single_image_review_enabled(root)
    if strict_single_review and not ns.dry_run and len(targets) != 1:
        print(
            "[gate] 图片验收模式=逐张机器QC+实际目视：一次正式调用必须且只能解析 1 张图片；"
            "请传单一 --shared-targets，或把 --shots 缩到只产生一个实际 PNG 的目标。",
            file=sys.stderr,
        )
        return 1
    if strict_single_review and not ns.dry_run:
        pending_review = base.strict_pending_image_review(root, targets[0].rel_path)
        if pending_review:
            print(
                "[gate] 上一张图片尚无与当前像素 SHA 绑定的 qa/accepted 目视验收："
                f"{pending_review['asset']} ({pending_review['artifact_sha256'] or 'sha-missing'})；"
                "只能继续重抽该图，或先完成 full 机器QC、实际像素目视并记录 accepted，再生成下一张。",
                file=sys.stderr,
            )
            return 1

    # Shared style/identity/assets are paid generations too.  Their missing
    # pixels necessarily make the full episode image_preflight fail, so run the
    # narrower non-waivable compliance/rights preflight used by the Codex
    # adapter.  Clip targets still require the full image_preflight below.
    if shared_targets and not ns.dry_run and not base.run_shared_asset_preflight(root, episode):
        return 1

    # Non-waivable ordering lock shared with codex_image_runner: --skip-preflight
    # cannot spend on Clip PNGs before the episode shared library is complete.
    if shots and not ns.dry_run and not base.enforce_shared_first_interlock(root, episode, targets=targets):
        return 1
    if shots and not ns.dry_run and not base.enforce_current_episode_image_namespace(root, episode):
        return 1

    # Pre-spend interlock: 生成前先跑 image_preflight 硬闸门，block 即拒绝生成不花钱；
    # 逃生口 --skip-preflight 留痕成 dashboard waiver（与 codex_image_runner 同源）。
    if shots and not ns.dry_run:
        if ns.recover_submit_id:
            print("[gate] recovery mode uses an existing paid submit id; pre-spend image_preflight is not applicable")
        elif ns.skip_preflight:
            base.record_waiver(root, episode, "image_preflight", "skip-preflight",
                               "operator passed --skip-preflight; pre-spend image_preflight gate not run")
        elif not base.run_image_gate(root, episode, stage="image_preflight"):
            print("[gate] image_preflight blocked — refusing to spend on generation; fix upstream or pass --skip-preflight", file=sys.stderr)
            return 1

    ok_all = True
    for target in targets:
        ok = process_target(
            root,
            episode,
            target,
            task_id=task_id,
            timeout_sec=ns.timeout_sec,
            poll_sec=ns.poll_sec,
            model_version=ns.model_version,
            resolution_type=ns.resolution_type,
            dry_run=ns.dry_run,
            force=ns.force,
            recover_submit_id=ns.recover_submit_id,
            canonical_reset=ns.canonical_reset,
        )
        if ok and not ns.dry_run and not ns.skip_image_qc:
            ok = base.run_target_image_qc(root, episode, target)
        ok_all = ok_all and ok
        if ok and not ns.dry_run:
            base.sync_image_progress(root, episode)
        if not ok and ns.stop_on_fail:
            break
    if ns.skip_image_qc and shots and not ns.dry_run:
        base.record_waiver(root, episode, "image", "skip-image-qc",
                           "operator passed --skip-image-qc; per-target landed-frame QC not run")
    if ok_all and shots and not ns.dry_run:
        if ns.skip_final_gate:
            base.record_waiver(root, episode, "image", "skip-final-gate",
                               "operator passed --skip-final-gate; whole-episode image gate not run")
        elif not base.covers_all_episode_targets(root, episode, targets):
            print("[gate] image final gate deferred for partial batch; run the whole-episode image gate after all declared Clip PNGs are present")
        else:
            ok_all = base.run_image_gate(root, episode)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
