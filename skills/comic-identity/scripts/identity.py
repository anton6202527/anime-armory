#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""漫画共享定妆、引用绑定和一致性重抽计划。"""
from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import json
import re
import subprocess
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(SCRIPT_DIR))
from model_pack import apply_character_readiness, png_dimensions  # noqa: E402
from registry_v2 import migrate_registry, validate_registry  # noqa: E402


PNG_SIG = b"\x89PNG\r\n\x1a\n"
REQUIRED_CHARACTER_VIEWS = ("front", "three_quarter", "side", "back", "face")
# tier 分档必需视图（2026-07 标准审计·参照同仓成熟生产线档位模式的漫画重实现，不跨线 import）：
# 此前对所有角色一刀切要求全五视图——named_minimal 短线具名角色也被逼出侧/背，过度要求；
# 源模式的实践是档位只控生产深度、不改 DNA 真值归属。档位取 library_tier/tier（与 library.py
# default_tier 同源）；未标档按全五视图保守处理（宁多不漏，与"长线连载默认"一致）。
TIER_REQUIRED_VIEWS: dict[str, tuple[str, ...]] = {
    "core_full": ("front", "three_quarter", "side", "back", "face"),
    "recurring_standard": ("front", "three_quarter", "face"),
    "named_minimal": ("front", "face"),
    "restricted_partial": (),
}


def required_views_for(asset: Any) -> tuple[str, ...]:
    """按角色档位给出必需视图集合；未知/未标档回退全五视图（保守）。纯函数·可测。"""
    tier = ""
    if isinstance(asset, dict):
        tier = str(asset.get("library_tier") or asset.get("tier") or "").strip()
    return TIER_REQUIRED_VIEWS.get(tier, REQUIRED_CHARACTER_VIEWS)
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
VIEW_LABELS = {
    "front": "front full-body view, standing neutrally, face looking forward",
    "three_quarter": "three-quarter full-body view, body turned 45 degrees, face visible",
    "side": "clean side-profile full-body view, one side profile, body and face in profile",
    "back": "rear full-body view, back of outfit and hair clearly visible, no frontal face",
    "face": "front close-up face reference, head and shoulders, neutral expression",
}
VIEW_RATIOS = {
    "front": "3:4",
    "three_quarter": "3:4",
    "side": "3:4",
    "back": "3:4",
    "face": "1:1",
}
CODEX_MODEL = "GPT Image 2"
CODEX_CHANNEL = "Codex CLI"
CODEX_EXECUTION_MODE = "isolated_ephemeral_workdir"
DREAMINA_MODEL = "Dreamina image2image"
DREAMINA_CHANNEL = "Dreamina official CLI"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_setting(root: Path, key: str, default: str) -> str:
    path = root / "_设置.md"
    if not path.is_file():
        return default
    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def png_valid(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 64 and path.read_bytes()[:8] == PNG_SIG
    except OSError:
        return False


def image_candidates(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    candidates: list[Path] = []
    for suffix in IMAGE_EXTS:
        candidates.extend(path.rglob(f"*{suffix}"))
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def materialize_png(src: Path, out_path: Path) -> bool:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".png":
        shutil.copy2(src, out_path)
        return png_valid(out_path)
    try:
        from PIL import Image

        Image.open(src).save(out_path)
        if png_valid(out_path):
            return True
    except Exception:
        pass
    if shutil.which("sips"):
        proc = subprocess.run(
            ["sips", "-s", "format", "png", str(src), "--out", str(out_path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return proc.returncode == 0 and png_valid(out_path)
    return False


def repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / "skills").is_dir() and (parent / "创作区").is_dir():
            return parent
    return start.resolve()


def rel_to_root(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_path(root: Path, raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else root / path


def registry_path(root: Path) -> Path:
    return root / "出图" / "共享" / "identity_registry.json"


def jobs_path(root: Path, chapter: str) -> Path:
    return root / "出图" / chapter / "prompt" / "panel_jobs.json"


def load_registry(root: Path) -> dict:
    path = registry_path(root)
    if path.is_file():
        data = load_json(path)
        if isinstance(data, dict):
            migrated, _ = migrate_registry(data)
            return migrated
    return {"schema_version": 2, "kind": "comic_identity_registry", "assets": {}, "schema_meta": {}}


def codex_version() -> str:
    proc = subprocess.run(["codex", "--version"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return (proc.stdout or proc.stderr or "codex unknown").strip().splitlines()[0]


def codex_image_feature_status() -> str:
    proc = subprocess.run(
        ["codex", "features", "list"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        return "unknown"
    for line in proc.stdout.splitlines():
        fields = line.split()
        if fields and fields[0] == "image_generation":
            return fields[1] if len(fields) > 1 else "present"
    return "missing"


def image_generation_records_from_jsonl(text: str) -> list[dict[str, Any]]:
    """Normalize both rollout events and ``codex exec --json`` item events."""
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        candidates = [event.get("payload"), event.get("item"), event]
        for data in candidates:
            if not isinstance(data, dict):
                continue
            record_type = str(data.get("type") or "")
            if record_type not in {"image_generation_end", "image_generation"}:
                continue
            status = str(data.get("status") or "completed")
            if status not in {"completed", "succeeded"}:
                continue
            records.append(data)
            break
    return records


def image_payload_from_jsonl(text: str) -> str:
    payload = ""
    for data in image_generation_records_from_jsonl(text):
        result = data.get("result")
        if isinstance(result, str) and result.strip():
            payload = result.strip()
    return payload


def image_saved_path_from_jsonl(text: str) -> Path | None:
    saved_path: Path | None = None
    for data in image_generation_records_from_jsonl(text):
        value = data.get("saved_path")
        if isinstance(value, str) and value.strip():
            saved_path = Path(value).expanduser()
    return saved_path


def codex_generated_images_root() -> Path:
    return Path.home() / ".codex" / "generated_images"


def codex_thread_id(stdout: str) -> str:
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            return event["thread_id"]
    return ""


def codex_event_diagnostics(stdout: str, stderr: str) -> dict[str, Any]:
    """Summarize JSONL control events without persisting prompts or image payloads."""
    top_level_type_counts: dict[str, int] = {}
    payload_type_counts: dict[str, int] = {}
    item_type_counts: dict[str, int] = {}
    json_event_count = 0
    image_generation_begin_seen = False
    image_generation_end_seen = False
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        json_event_count += 1
        event_type = str(event.get("type") or "unknown")
        top_level_type_counts[event_type] = top_level_type_counts.get(event_type, 0) + 1
        payload = event.get("payload")
        if isinstance(payload, dict):
            payload_type = str(payload.get("type") or "unknown")
            payload_type_counts[payload_type] = payload_type_counts.get(payload_type, 0) + 1
            image_generation_begin_seen = image_generation_begin_seen or payload_type == "image_generation_begin"
            image_generation_end_seen = image_generation_end_seen or payload_type == "image_generation_end"
        item = event.get("item")
        if isinstance(item, dict):
            item_type = str(item.get("type") or "unknown")
            key = f"{event_type}:{item_type}"
            item_type_counts[key] = item_type_counts.get(key, 0) + 1
            if item_type == "image_generation":
                image_generation_begin_seen = image_generation_begin_seen or event_type == "item.started"
                status = str(item.get("status") or "")
                image_generation_end_seen = image_generation_end_seen or (
                    event_type == "item.completed" and status in {"completed", "succeeded"}
                )
    return {
        "json_event_count": json_event_count,
        "stdout_line_count": len(stdout.splitlines()),
        "stderr_line_count": len(stderr.splitlines()),
        "top_level_type_counts": top_level_type_counts,
        "payload_type_counts": payload_type_counts,
        "item_type_counts": item_type_counts,
        "image_generation_begin_seen": image_generation_begin_seen,
        "image_generation_end_seen": image_generation_end_seen,
        "thread_id": codex_thread_id(stdout),
    }


def codex_session_path(thread_id: str) -> Path | None:
    sessions = Path.home() / ".codex" / "sessions"
    if not thread_id or not sessions.is_dir():
        return None
    matches = list(sessions.glob(f"**/*{thread_id}.jsonl"))
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def write_image_payload(payload: str, out_path: Path) -> bool:
    if payload.startswith("data:"):
        payload = payload.split(",", 1)[-1]
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(raw)
    return png_valid(out_path)


def decode_image_event(stdout: str, out_path: Path) -> bool:
    payload = image_payload_from_jsonl(stdout)
    saved_path = image_saved_path_from_jsonl(stdout)
    thread_id = codex_thread_id(stdout)
    if not payload and not saved_path and thread_id:
        session = codex_session_path(thread_id)
        if session and session.is_file():
            session_text = session.read_text(encoding="utf-8", errors="ignore")
            payload = image_payload_from_jsonl(session_text)
            saved_path = image_saved_path_from_jsonl(session_text)
    if payload and write_image_payload(payload, out_path):
        return True
    if not saved_path:
        return False
    try:
        source = saved_path.resolve(strict=True)
        generated_root = codex_generated_images_root().resolve(strict=True)
    except (FileNotFoundError, OSError):
        return False
    if source == generated_root or generated_root not in source.parents or not png_valid(source):
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, out_path)
    return png_valid(out_path)


def prompt_snapshot(root: Path, chapter: str, asset_id: str, variant: str, prompt: str) -> tuple[str, str]:
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
    safe_asset = re.sub(r"[^A-Za-z0-9_.-]+", "_", asset_id).strip("_") or "asset"
    safe_variant = re.sub(r"[^A-Za-z0-9_.-]+", "_", variant).strip("_") or "prompt"
    path = root / "生产数据" / "comic_identity_prompts" / chapter / f"{safe_asset}__{safe_variant}__{stamp}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt.rstrip() + "\n", encoding="utf-8")
    return rel_to_root(root, path), hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def adopt_generated_png(
    root: Path,
    candidate: Path,
    dest: Path,
    *,
    asset_id: str,
    variant: str,
) -> str:
    """Atomically adopt a valid candidate and archive the previous accepted PNG."""
    if not png_valid(candidate):
        return ""
    archived = ""
    if png_valid(dest):
        stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
        archive = root / "出图" / "共享" / "candidates" / asset_id / variant / f"{stamp}__{file_sha256(dest)[:12]}.png"
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, archive)
        archived = rel_to_root(root, archive)
    dest.parent.mkdir(parents=True, exist_ok=True)
    candidate.replace(dest)
    return archived


def normalize_full_body_canvas(path: Path, target: tuple[int, int]) -> bool:
    """Fit a generated full-body PNG onto the adopted front canvas without cropping."""
    dims = png_dimensions(path)
    if not dims or dims == target:
        return False
    from PIL import Image, ImageOps

    with Image.open(path) as opened:
        image = opened.convert("RGB")
        fitted = ImageOps.contain(image, target, Image.Resampling.LANCZOS)
        corners = [image.getpixel((0, 0)), image.getpixel((image.width - 1, 0)), image.getpixel((0, image.height - 1)), image.getpixel((image.width - 1, image.height - 1))]
        fill = tuple(sum(px[channel] for px in corners) // len(corners) for channel in range(3))
        canvas = Image.new("RGB", target, fill)
        canvas.paste(fitted, ((target[0] - fitted.width) // 2, (target[1] - fitted.height) // 2))
        pending = path.with_name(f".{path.stem}__canvas_pending.png")
        canvas.save(pending, format="PNG")
    pending.replace(path)
    return True


def target_canvas_for_ratio(current: tuple[int, int], ratio: str) -> tuple[int, int]:
    match = re.fullmatch(r"\s*(\d+)\s*[:/]\s*(\d+)\s*", str(ratio or ""))
    if not match:
        raise ValueError(f"无效画幅比例：{ratio}")
    rw, rh = int(match.group(1)), int(match.group(2))
    if rw <= 0 or rh <= 0 or rw > 100 or rh > 100:
        raise ValueError(f"无效画幅比例：{ratio}")
    width, height = current
    if width * rh == height * rw:
        return current
    # Expand to the smallest exact-ratio canvas that can contain the source.
    # This guarantees no crop, no stretch and no subject loss.
    scale = max((width + rw - 1) // rw, (height + rh - 1) // rh)
    return rw * scale, rh * scale


def normalize_png_to_ratio(path: Path, ratio: str) -> dict[str, Any]:
    current = png_dimensions(path)
    if not current:
        return {}
    target = target_canvas_for_ratio(current, ratio)
    if target == current:
        return {}
    if not normalize_full_body_canvas(path, target):
        return {}
    return {
        "method": "contain_and_pad_no_crop",
        "ratio": ratio,
        "source_width": current[0],
        "source_height": current[1],
        "target_width": target[0],
        "target_height": target[1],
    }


def adopt_anchor_candidate(args: argparse.Namespace) -> int:
    """Adopt a human-selected shared anchor or character front candidate."""
    root = Path(args.project_root).expanduser().resolve()
    registry = load_registry(root)
    assets = registry.setdefault("assets", {})
    ref_id = str(args.ref).strip()
    if not ref_id or not isinstance(assets.get(ref_id), dict):
        raise SystemExit(f"unknown registry asset: {ref_id or '<empty>'}")
    candidate = resolve_path(root, str(args.candidate))
    asset = assets[ref_id]
    is_character_front = str(asset.get("type") or "").strip().lower() == "character"
    variant = "front" if is_character_front else "anchor"
    expected_root = (root / "出图" / "共享" / "candidates" / ref_id / variant).resolve()
    try:
        candidate.resolve().relative_to(expected_root)
    except ValueError as exc:
        raise SystemExit(f"candidate must be under {expected_root}: {candidate}") from exc
    if not png_valid(candidate):
        raise SystemExit(f"candidate is not a valid PNG: {candidate}")

    candidate_rel = rel_to_root(root, candidate)
    candidate_sha = file_sha256(candidate)
    dest = root / "出图" / "共享" / "图片" / f"{ref_id}__{variant}.png"
    pending = dest.with_name(f".{dest.stem}__adopt_pending.png")
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.unlink(missing_ok=True)
    shutil.copy2(candidate, pending)
    archived = adopt_generated_png(root, pending, dest, asset_id=ref_id, variant=variant)
    if not png_valid(dest):
        raise SystemExit(f"failed to adopt candidate: {candidate}")

    now = dt.datetime.now().isoformat(timespec="seconds")
    source: dict[str, Any] = {
        "kind": "human_selected_character_front" if is_character_front else "human_selected_candidate_anchor",
        "chapter": args.chapter,
        "candidate_path": candidate_rel,
        "candidate_sha256": candidate_sha,
        "reviewer": str(args.reviewer).strip(),
        "reviewer_role": str(args.role).strip(),
        "decision": "approved",
        "reason": str(args.reason).strip(),
        "reviewed_at": now,
        "backend": CODEX_CHANNEL,
        "model": CODEX_MODEL,
    }
    if archived:
        source["archived_previous_path"] = archived
    if is_character_front:
        register_character_view(registry, root, ref_id, "front", dest, source=source)
    else:
        register_asset_anchor(registry, root, ref_id, dest, source=source)
    write_json(registry_path(root), registry)
    row = {
        "ts": now,
        "status": "character_front_adopted" if is_character_front else "reference_anchor_adopted",
        "ref_id": ref_id,
        "path": rel_to_root(root, dest),
        "sha256": file_sha256(dest),
        **source,
    }
    append_event(root, row)
    receipt = {
        "schema_version": 1,
        "kind": "comic_character_front_adoption" if is_character_front else "comic_reference_anchor_adoption",
        "created_at": now,
        "ref_id": ref_id,
        "candidate_path": candidate_rel,
        "candidate_sha256": candidate_sha,
        "adopted_path": rel_to_root(root, dest),
        "adopted_sha256": file_sha256(dest),
        "reviewer": source["reviewer"],
        "reviewer_role": source["reviewer_role"],
        "decision": "approved",
        "reason": source["reason"],
        "backend": CODEX_CHANNEL,
        "model": CODEX_MODEL,
    }
    receipt_label = "front_adoption" if is_character_front else "anchor_adoption"
    out = root / "生产数据" / f"comic_identity_{receipt_label}_{ref_id}.json"
    write_json(out, receipt)
    print(f"[ok] adopted {ref_id}: {rel_to_root(root, dest)}", flush=True)
    print(f"[ok] adoption receipt: {out}", flush=True)
    return 0


def run_codex_image(prompt: str, repo: Path, timeout_sec: int, image_paths: list[Path]) -> subprocess.CompletedProcess[str]:
    cmd = [
        "codex",
        "exec",
        "--json",
        "--enable",
        "image_generation",
        "--ephemeral",
        "--skip-git-repo-check",
    ]
    for path in image_paths:
        cmd.extend(["--image", str(path)])
    # 生图 prompt 已携带完整合同；在空目录运行可避免嵌套 Codex 扫描作品仓库、AGENTS.md
    # 或其它生产线说明。图片输入使用绝对路径，经 --image 显式传入。
    with tempfile.TemporaryDirectory(prefix="comic-identity-codex-image-") as isolated_workdir:
        isolated_path = Path(isolated_workdir).resolve()
        if isolated_path == repo.resolve() or repo.resolve() in isolated_path.parents:
            raise RuntimeError("isolated Codex image workdir must be outside the repository")
        isolated_cmd = [*cmd, "-s", "read-only", "-C", str(isolated_path), prompt]
        try:
            return subprocess.run(
                isolated_cmd,
                stdin=subprocess.DEVNULL,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            stderr = (stderr + f"\ntimeout after {timeout_sec}s").strip()
            return subprocess.CompletedProcess(isolated_cmd, 124, stdout=stdout, stderr=stderr)


def format_failure(proc: subprocess.CompletedProcess[str]) -> str:
    stderr = (proc.stderr or "").strip()
    stdout = (proc.stdout or "").strip()
    combined = "\n".join(part for part in (stderr, stdout) if part)
    lowered = combined.lower()
    if proc.returncode == 124 or "timeout after" in stderr.lower():
        failure_class = "backend_timeout"
    elif "http 403" in lowered or "forbidden" in lowered:
        failure_class = "backend_forbidden"
    elif "http/request failed" in lowered or "transport channel closed" in lowered:
        failure_class = "backend_transport"
    elif "no valid image_generation_end" in lowered:
        failure_class = "backend_no_image"
    else:
        failure_class = "backend_error"

    diagnostic_lines: list[str] = []
    if failure_class == "backend_timeout":
        diagnostic_lines = [
            line.strip()
            for line in stderr.splitlines()
            if "timeout after" in line.lower()
        ]
        if not diagnostic_lines:
            diagnostic_lines = ["timeout"]
    for line in combined.splitlines():
        if diagnostic_lines and failure_class == "backend_timeout":
            break
        clean = line.strip()
        if not clean:
            continue
        low = clean.lower()
        if any(token in low for token in (" error ", "error:", "http 403", "forbidden", "timeout after", "transport channel closed")):
            diagnostic_lines.append(clean)
    if not diagnostic_lines and combined:
        diagnostic_lines = [combined.splitlines()[-1].strip()]
    detail = " | ".join(diagnostic_lines[-4:])
    if len(detail) > 400:
        detail = detail[-400:]
    return f"codex exit {proc.returncode}; class={failure_class}" + (f"; detail={detail}" if detail else "")


def backend_health_manifest_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / f"comic_identity_backend_health_{chapter}.json"


def backend_probe_prompt(profile: str, *, reference_attached: bool) -> tuple[str, str]:
    """Return a non-production probe prompt and the production request class it calibrates."""
    if profile == "simple":
        request_class = "simple_bitmap"
        prompt = (
            "Use case: stylized-concept\n"
            "Asset type: non-production image-backend health probe\n"
            "Primary request: Create one simple diagnostic bitmap: a centered matte white circle above a centered dark gray square on a flat light-gray background.\n"
            "Composition/framing: square canvas, large clean shapes, generous margins.\n"
            "Constraints: exactly one circle and one square; no people; no scenery; no text; no letters; no numbers; no logo; no watermark."
        )
    elif profile == "production-character-front":
        request_class = "historical_character_front"
        prompt = (
            "Use case: historical-scene\n"
            "Asset type: non-production production-latency calibration for a historical comic character front; this is not a project character and must never be adopted into an identity registry.\n"
            "Primary request: Create one polished full-body front character design of an anonymous adult male Northern Song court official, suitable for a long-running Chinese historical comic consistency pack.\n"
            "Subject: fictional and non-identifiable man aged about 45 to 55, composed bearing, balanced realistic anatomy, both hands visible and relaxed, neutral closed-mouth expression, no resemblance to a real actor or public figure.\n"
            "Wardrobe: historically plausible Northern Song official dress with a black futou, restrained solid-color round-collar robe, period-plausible belt and black boots; layered construction, collar, sleeve, hem, belt and footwear must remain clearly readable.\n"
            "Scene/backdrop: quiet neutral studio-like light background with only a faint grounding shadow; no architecture, furniture, heraldry or narrative scene.\n"
            "Style/medium: premium cinematic Chinese comic concept art with controlled ink texture, clean anatomical drawing, restrained mineral colors, believable silk and leather material separation.\n"
            "Composition/framing: exact front-facing neutral turnaround pose, entire head-to-toe silhouette visible, centered vertical 3:4 portrait, generous margin around hat, sleeves and boots, no crop.\n"
            "Lighting/mood: soft directional key light with readable three-value structure and restrained historical dignity.\n"
            "Constraints: one person only; no props; no weapons; no throne; no dragon motifs; no Ming rank badge; no Qing queue, court hat or robe; no fantasy armor; no floating fabric; no text; no letters; no numbers; no logo; no watermark; no border; no character-card labels."
        )
    else:
        raise ValueError(f"unsupported backend probe profile: {profile}")
    if reference_attached:
        prompt += (
            "\nInput images: Image 1 is style-only; inherit only its line, color, light, and material treatment."
            " Do not copy any person, face, hairstyle, garment combination, object, scene layout, pose, or composition from it."
        )
    return prompt, request_class


def probe_backend(args: argparse.Namespace) -> int:
    """执行一次不绑定正式资产的图像通道探针；不消费资产 variant 的尝试总账。"""
    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    if not shutil.which("codex"):
        raise SystemExit("codex not found in PATH")
    feature_status = codex_image_feature_status()
    if feature_status in {"missing", "removed"}:
        raise SystemExit(f"Codex image_generation feature is {feature_status}; 未发起远端探针")

    requested_probe_mode = str(getattr(args, "probe_mode", "auto") or "auto").strip()
    probe_profile = str(getattr(args, "probe_profile", "simple") or "simple").strip()
    image_paths: list[Path] = []
    reference_inputs: list[dict[str, str]] = []
    if requested_probe_mode != "text-only":
        style_reference = project_style_anchor(root, load_registry(root))
        if style_reference and png_valid(style_reference):
            image_paths.append(style_reference)
            reference_inputs.append(
                {
                    "path": rel_to_root(root, style_reference),
                    "sha256": file_sha256(style_reference),
                    "role": "style_only",
                }
            )
        elif requested_probe_mode == "reference-attached":
            raise SystemExit("reference-attached probe requires a valid adopted STYLE_ anchor; 未发起远端探针")
    probe_scope = "reference_attached" if image_paths else "text_only"

    manifest_path = backend_health_manifest_path(root, args.chapter)
    try:
        manifest = load_json(manifest_path) if manifest_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        manifest = {}
    if not isinstance(manifest, dict):
        manifest = {}
    probes = manifest.setdefault("probes", [])
    if not isinstance(probes, list):
        probes = []
        manifest["probes"] = probes

    started_at = dt.datetime.now().isoformat(timespec="microseconds")
    probe_id = hashlib.sha256(
        f"{args.chapter}|codex|{CODEX_MODEL}|{started_at}|{len(probes) + 1}".encode("utf-8")
    ).hexdigest()[:20]
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
    artifact = (
        root
        / "生产数据"
        / "backend_health"
        / f"{stamp}__gpt_image_2__codex_cli__{probe_scope}__{probe_profile}_probe.png"
    )
    prompt, production_request_class = backend_probe_prompt(
        probe_profile,
        reference_attached=bool(image_paths),
    )
    prompt_path, prompt_sha256 = prompt_snapshot(
        root,
        args.chapter,
        "BACKEND_HEALTH",
        f"probe_{probe_profile}_codex",
        prompt,
    )
    row: dict[str, Any] = {
        "probe_id": probe_id,
        "started_at": started_at,
        "status": "started",
        "reason": str(args.reason).strip(),
        "model": CODEX_MODEL,
        "access_path": CODEX_CHANNEL,
        "cli_version": codex_version(),
        "image_generation_feature": feature_status,
        "execution_mode": CODEX_EXECUTION_MODE,
        "requested_probe_mode": requested_probe_mode,
        "probe_scope": probe_scope,
        "probe_profile": probe_profile,
        "production_request_class": production_request_class,
        "calibration_only": True,
        "reference_inputs": reference_inputs,
        "timeout_sec": int(args.timeout_sec),
        "prompt_path": prompt_path,
        "prompt_sha256": prompt_sha256,
        "external_status": str(args.external_status or "").strip(),
        "external_status_url": str(args.external_status_url or "").strip(),
        "external_status_checked_at": str(args.external_status_checked_at or "").strip(),
        "asset_attempt_ledger_consumed": False,
    }
    probes.append(row)
    manifest.update(
        {
            "schema_version": 1,
            "kind": "comic_identity_backend_health",
            "chapter": args.chapter,
            "updated_at": started_at,
            "latest_status": "started",
        }
    )
    write_json(manifest_path, manifest)

    monotonic_started = time.monotonic()
    try:
        proc = run_codex_image(prompt, repo, args.timeout_sec, image_paths)
    except KeyboardInterrupt:
        row.update(
            {
                "status": "interrupted",
                "finished_at": dt.datetime.now().isoformat(timespec="microseconds"),
                "duration_sec": round(time.monotonic() - monotonic_started, 3),
                "error": "interrupted",
            }
        )
        manifest["updated_at"] = row["finished_at"]
        manifest["latest_status"] = "interrupted"
        write_json(manifest_path, manifest)
        raise

    row["finished_at"] = dt.datetime.now().isoformat(timespec="microseconds")
    row["duration_sec"] = round(time.monotonic() - monotonic_started, 3)
    row["codex_event_diagnostics"] = codex_event_diagnostics(proc.stdout or "", proc.stderr or "")
    if proc.returncode != 0:
        row.update({"status": "failed", "error": format_failure(proc)})
        manifest["latest_status"] = "failed"
        manifest["updated_at"] = row["finished_at"]
        write_json(manifest_path, manifest)
        print(f"[fail] backend health probe: {row['error']}", flush=True)
        print(f"[ok] health manifest: {manifest_path}", flush=True)
        return 1

    if not decode_image_event(proc.stdout, artifact) or not png_valid(artifact):
        artifact.unlink(missing_ok=True)
        row.update(
            {
                "status": "failed",
                "error": "codex completed but no valid image_generation_end PNG was available",
            }
        )
        manifest["latest_status"] = "failed"
        manifest["updated_at"] = row["finished_at"]
        write_json(manifest_path, manifest)
        print(f"[fail] backend health probe: {row['error']}", flush=True)
        print(f"[ok] health manifest: {manifest_path}", flush=True)
        return 1

    dimensions = png_dimensions(artifact)
    row.update(
        {
            "status": "succeeded",
            "artifact_path": rel_to_root(root, artifact),
            "artifact_sha256": file_sha256(artifact),
            "width": dimensions[0] if dimensions else 0,
            "height": dimensions[1] if dimensions else 0,
        }
    )
    manifest["latest_status"] = "succeeded"
    manifest["updated_at"] = row["finished_at"]
    write_json(manifest_path, manifest)
    print(f"[ok] backend health probe -> {artifact}", flush=True)
    print(f"[ok] health manifest: {manifest_path}", flush=True)
    return 0


def submit_id_from(text: str) -> str:
    patterns = [
        r'"submit_id"\s*:\s*"([^"]+)"',
        r"submit_id\s*[=:]\s*([A-Za-z0-9._-]+)",
        r"submit id\s*[=:]\s*([A-Za-z0-9._-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1)
    return ""


def run_dreamina_image(
    prompt: str,
    anchor: Path,
    out_path: Path,
    *,
    timeout_sec: int,
    poll_sec: int,
    model_version: str,
    resolution_type: str,
    ratio: str,
) -> tuple[bool, str, str]:
    temp_root = Path(tempfile.gettempdir()) / "comic_identity_dreamina"
    temp_root.mkdir(parents=True, exist_ok=True)
    download_dir = temp_root / f"{out_path.stem}_download"
    if download_dir.exists():
        shutil.rmtree(download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "dreamina",
        "image2image",
        "--images",
        str(anchor),
        "--prompt",
        prompt,
        "--ratio",
        ratio,
        "--poll",
        str(max(0, min(poll_sec, timeout_sec))),
    ]
    if model_version:
        cmd.extend(["--model_version", model_version])
    if resolution_type:
        cmd.extend(["--resolution_type", resolution_type])
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return False, "", f"dreamina image2image timed out after {timeout_sec}s"
    combined = "\n".join(p for p in (proc.stdout, proc.stderr) if p)
    if proc.returncode != 0:
        return False, "", f"dreamina image2image exit {proc.returncode}: {combined[-4000:]}"
    submit_id = submit_id_from(combined)
    if not submit_id:
        return False, "", f"dreamina output did not include submit_id: {combined[-2000:]}"
    try:
        query = subprocess.run(
            ["dreamina", "query_result", "--submit_id", submit_id, "--download_dir", str(download_dir)],
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        return False, submit_id, f"dreamina query_result timed out after {timeout_sec}s"
    qout = "\n".join(p for p in (query.stdout, query.stderr) if p)
    if query.returncode != 0:
        return False, submit_id, f"dreamina query_result exit {query.returncode}: {qout[-4000:]}"
    candidates = image_candidates(download_dir)
    if not candidates:
        return False, submit_id, f"dreamina query_result downloaded no image files: {qout[-2000:]}"
    if not materialize_png(candidates[0], out_path):
        return False, submit_id, f"downloaded result is not a valid image or PNG conversion failed: {candidates[0]}"
    return True, submit_id, ""


def story_bible_character_notes(root: Path, character_id: str) -> str:
    path = root / "设定库" / "story_bible.md"
    if not path.is_file():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = None
    # Stable story-bible contract: ``### 人读名称 CHAR_STABLE_ID``.  Match the
    # ID as a complete token so CHAR_LIN never consumes CHAR_LINCHONG's notes.
    heading = re.compile(
        rf"^\s*#{{3,6}}\s+.*(?<![A-Z0-9_]){re.escape(character_id)}(?![A-Z0-9_]).*$"
    )
    for idx, line in enumerate(lines):
        if heading.match(line):
            start = idx
            break
    if start is None:
        return ""
    out: list[str] = []
    for line in lines[start:start + 24]:
        if out and re.match(r"^\s*###(?!#)\s+", line):
            break
        out.append(line)
    return "\n".join(out).strip()


def compact_contract(value: Any, *, max_len: int = 640) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list):
        text = "；".join(compact_contract(item, max_len=max_len) for item in value)
    elif isinstance(value, dict):
        chunks = []
        for key, item in value.items():
            item_text = compact_contract(item, max_len=max_len)
            if item_text:
                chunks.append(f"{key}:{item_text}")
        text = "；".join(chunks)
    else:
        text = str(value).strip()
    text = re.sub(r"\s+", " ", text).strip("； ")
    if len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text


def outfit_contract_text(asset: dict[str, Any], outfit_id: str) -> str:
    outfits = asset.get("outfits") if isinstance(asset.get("outfits"), dict) else {}
    outfit = outfits.get(outfit_id) if isinstance(outfits.get(outfit_id), dict) else {}
    if not outfit:
        return ""
    return compact_contract(
        outfit.get("wardrobe_standard") or {
            "name": outfit.get("name"),
            "description": outfit.get("description"),
            "forbidden": outfit.get("forbidden"),
        },
        max_len=1500,
    )


def character_asset_contract(asset: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, label in (
        ("display_name", "名称"),
        ("character_dna", "角色DNA"),
        ("dna_contract", "定妆契约"),
        ("variant_policy", "年龄/形态继承"),
        ("transient_props", "临时剧情物（不得固化为身份）"),
        ("staging_defaults", "同框调度（不得固化为身份）"),
        ("forbidden_inheritance", "禁继承"),
        ("style_contract", "风格契约"),
        ("notes", "备注"),
    ):
        text = compact_contract(asset.get(key))
        if text:
            parts.append(f"{label}:{text}")
    age_variants = asset.get("age_variants")
    if isinstance(age_variants, dict) and age_variants:
        parts.append("已登记年龄形态:" + ",".join(map(str, age_variants.keys())))
    # A wardrobe contract is only useful if the generation prompt actually
    # consumes it.  Keep the default bound outfit compact and explicit so a
    # new front view cannot silently fall back to generic costume priors.
    if str(asset.get("type") or "character").strip().lower() == "character":
        binding = asset.get("default_binding") if isinstance(asset.get("default_binding"), dict) else {}
        outfit_id = str(binding.get("outfit_id") or "").strip()
        outfit_contract = outfit_contract_text(asset, outfit_id)
        if outfit_contract:
            parts.append(f"默认服装 {outfit_id}:{outfit_contract}")
    return "\n".join(f"- {item}" for item in parts)


def character_view_prompt(
    character_id: str,
    view: str,
    notes: str,
    *,
    visual_style: str,
    asset_contract: str = "",
    backend: str = "codex",
) -> str:
    view_label = VIEW_LABELS.get(view, view)
    is_monster = character_id.startswith("MON_")
    subject_label = "生物设定" if is_monster else "角色定妆"
    opening = (
        f"请用内置 image_generation 工具生成漫画{subject_label}专门参考图。"
        if backend == "codex"
        else f"请基于参考图生成漫画{subject_label}专门参考图。"
    )
    if view == "face" and is_monster:
        view_rules = (
            "本视图必须是生物头部与上段躯干近景：正面或严格对称可读角度，中性警觉状态，"
            "头骨比例、眼鼻口位置、额纹/鳞片或永久特征清楚；不要全身、捕食、咆哮攻击或强透视。"
        )
    elif view == "face":
        view_rules = (
            "本视图必须是头肩近景定妆：正面看镜头，中性表情，五官、发际线、发型轮廓、伤痕/污渍清楚；"
            "不要全身、不要动作戏、不要强透视。"
        )
    elif is_monster:
        view_rules = (
            f"本视图必须是单体生物的 {view} 结构参考：从头部到尾端、所有肢体或完整盘绕路径入画，"
            "保持真实物种或项目 DNA 登记的自然姿态；四足兽保持四足承重，蛇类保持连续脊柱与可读盘绕，"
            "不得人立、穿衣、增加龙角/翼/额外肢体；不得裁掉头、爪足或尾端。"
        )
    else:
        view_rules = (
            "本视图必须是单人站立全身定妆：从头顶到鞋底完整入画，脚/鞋完整可见，人物居中，直立或轻微放松站姿；"
            "不得坐、蹲、跪、弯腰、倒地、挥砍、冲刺、摆战斗 pose；不得裁掉头发、手、脚、鞋或随身武器。"
        )
    return f"""{opening}

角色 ID：{character_id}
视图：{view} / {view_label}

已附一张当前采纳的主体参考图。必须以它为最高优先级，保持同一主体 DNA、头脸/头骨结构、永久特征、体态比例和整体画风。
年龄、身高体量、服饰阶层和状态强度必须服从下面的项目定妆契约；如果契约声明本话基准形态是少年/杂役/受伤/觉醒等，不要把附件锚点的成年感或剧情动作原样继承成当前标准视图。
如果参考图来自剧情动作或受伤场面，只保留身份、服装和伤痕信息，不继承原图的坐姿、跪姿、弯腰、挥砍、镜头裁切或动态构图。
附件里的临时手持物、剧情道具、画面左右站位、注视目标和同框遮挡不属于身份；除非项目定妆契约明确登记为永久身体特征或永久佩饰，否则必须从中性多视图移除。
如果参考图来自截图，播放按钮、搜索框、字幕、水印、平台 UI、竖排标题和可读文字都不是设定，不得继承进角色设计。

角色设定摘录：
{notes or '无额外设定；以附件锚点为准。'}

项目定妆契约：
{asset_contract or '- 无登记契约；以附件锚点和角色设定为准。'}

画面要求：
1. 生成单一主体 reference art，不要场景叙事，不要其他人物/生物、气泡、文字、logo、水印。
2. 中性浅灰或低饱和纯色背景，柔和均匀光，同一主体所有视图都要像同一套 turn-around 设定图，适合后续作为漫画多视图参考图传给生图后端。
3. {view_rules}
4. 保持项目基础视觉风格：{visual_style}；定妆图要清楚、稳定、少动态夸张，不要退化成低细节彩漫、Q 版或泛化韩漫脸。
5. 不同年龄、闭关前后、受伤、觉醒、换装或境界变化都必须继承当前角色 DNA；只能改年龄比例、状态、服饰层和特效强度，不得换脸、换发际线、换眼型或丢失标志物。
6. 临时剧情手持物、左右站位和动作调度不得继承；只有定妆契约明确列为永久佩饰/身体特征的标志物才保留。
7. 不要画成现代写真、游戏 UI、角色卡边框、设计表排版、三视图拼贴或多格拼图；本次只输出这一张 {view} 视图，画面里只能有一个完整角色。
8. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
"""


def character_expression_prompt(
    character_id: str,
    expression_id: str,
    expression: dict[str, Any],
    notes: str,
    *,
    visual_style: str,
    asset_contract: str = "",
) -> str:
    """生成可独立喂给后端的表情锚；只改表演，不重画身份。"""
    name = str(expression.get("name") or expression_id).strip()
    emotion = str(expression.get("emotion") or name).strip()
    intensity = str(expression.get("intensity") or "medium").strip()
    return f"""请基于附件中已采纳的同一虚构角色脸部锚，生成一张独立的漫画表情参考图。

角色 ID：{character_id}
表情 ID：{expression_id}
表情名称：{name}
情绪：{emotion}
强度：{intensity}

身份锁定：附件是最高优先级身份真值。必须保持同一人的脸型、眼型与眼距、鼻梁、嘴型、下颌、发际线、发型轮廓、年龄、肤色和标志物；只改变面部肌肉与相应眼神，不得换脸、美型化或改变服装阶层。

角色设定摘录：
{notes or '无额外设定；以附件身份锚为准。'}

项目定妆契约：
{asset_contract or '- 无额外登记契约；以附件为准。'}

画面要求：
1. 单人头肩近景，中性浅灰或低饱和纯色背景，柔和均匀光，脸部与两侧轮廓完整。
2. 准确表现“{name}”（{emotion}, {intensity}），强度到位但不做滑稽变形；眼周、眉形、嘴角、咬肌和呼吸状态必须互相一致。
3. 保持项目基础视觉风格：{visual_style}；线条、肤色、墨色和上色层级必须与已采纳定妆同源。
4. 不要场景叙事、其他人、手持道具、对白气泡、文字、字母、数字、logo、水印、平台 UI、角色卡边框或多格拼图。
5. 只输出这一张表情锚图。
"""


def character_text_anchor_prompt(
    character_id: str,
    notes: str,
    *,
    visual_style: str,
    asset_contract: str = "",
    style_reference_attached: bool = False,
    aspect_ratio: str = "",
) -> str:
    is_monster = character_id.startswith("MON_")
    style_reference_note = (
        "已附一张项目风格锚图片。它只用于继承线条、上色、明暗、材质和墨晕语言；"
        "不得继承其中人物的脸、发型、服装、体态、姿势、构图或具体场景。"
        if style_reference_attached
        else "本次没有风格图片附件；严格按下列项目基础视觉风格执行。"
    )
    ratio_rule = f"画幅固定为 {aspect_ratio}，不得输出其他比例。" if aspect_ratio else "遵循项目登记的角色定妆画幅。"
    return f"""请用内置 image_generation 工具生成漫画角色首张专门定妆参考图。

角色 ID：{character_id}
视图：front / {VIEW_LABELS['front']}

{('本次没有已采纳主体图片作为附件。' if is_monster else '本次没有已采纳角色图片作为附件。')}必须只依据下面的项目设定生成稳定、可复用的长线 front 设定图；这张图会成为后续 three_quarter / side / back / face 视图的参考锚点。
{style_reference_note}

角色设定摘录：
{notes or '无额外设定；以项目定妆契约为准。'}

项目定妆契约：
{asset_contract or '- 无登记契约；请生成清楚、克制、可长期继承的角色标准形象。'}

画面要求：
1. 生成单一主体 reference art，不要场景叙事，不要其他人物/生物、气泡、文字、logo、水印。
2. {('单体生物正面全身结构图：完整头部、躯干、四肢/盘绕路径与尾端入画；四足兽保持四足承重，蛇类保持连续脊柱与清晰头颈，不得人立或穿衣。' if is_monster else '单人站立全身正面定妆：从头顶到鞋底完整入画，脚/鞋完整可见，人物居中，面向镜头，中性表情，直立或轻微放松站姿。')}
3. 中性浅灰或低饱和纯色背景，柔和均匀光，头脸/头骨结构、永久标志、体表材质、{('服装主形制与标志配饰、' if not is_monster else '')}体态比例必须清楚。
4. 保持项目基础视觉风格：{visual_style}；定妆图要清楚、稳定、少动态夸张，不要退化成低细节彩漫、Q 版或泛化韩漫脸。
5. {('不得捕食、扑击、咆哮攻击或摆戏剧化战斗 pose；不得裁掉头、爪足、躯干或尾端。' if is_monster else '不得坐、蹲、跪、弯腰、倒地、挥砍、冲刺、摆战斗 pose；不得裁掉头发、手、脚、鞋或永久身份佩饰。')}
6. 不生成临时剧情手持物、画面左右站位或同框调度；只有项目定妆契约明确列为永久佩饰/身体特征的标志物才可出现。
7. 不要画成现代写真、游戏 UI、角色卡边框、设计表排版、三视图拼贴或多格拼图；本次只输出这一张 front 视图，画面里只能有一个完整角色。
8. {ratio_rule}
9. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
"""


def outfit_reference_prompt(
    character_id: str,
    outfit_id: str,
    notes: str,
    *,
    visual_style: str,
    identity_contract: str,
    outfit_contract: str,
    aspect_ratio: str = "3:4",
) -> str:
    return f"""请用内置 image_generation 工具生成漫画角色的专门换装参考图。

用例：historical-scene / identity-preserve
角色 ID：{character_id}
服装 ID：{outfit_id}

已附该角色当前采纳的 front 正面定妆图。它是身份参考：脸型、眼型/眼距、发际线、发型、年龄、体态和整体画风不得改变。
本次只替换为指定服装；原 front 中的旧服装、临时手持物、动作、场景和站位不得混入新服装。

角色设定摘录：
{notes or '无额外设定。'}

角色身份契约：
{identity_contract or '- 以附件 front 为身份真值。'}

本套服装契约：
{outfit_contract or '- 缺服装契约；不得自由生成。'}

画面要求：
1. 单人站立全身正面参考，从头顶到鞋底完整入画，中性表情和站姿，手脚与鞋履不裁切。
2. 中性浅灰或低饱和纯色背景，柔和均匀光；不要场景叙事、其他人物、气泡、文字、logo 或水印。
3. 严格执行服装的层次、轮廓、领襟、开合、袖摆、带具、冠帽、鞋履、材质、色域、佩饰和禁用项；不以泛化“古装/汉服/仙侠”先验替代契约。
4. 保持项目基础视觉风格：{visual_style}。不复制影视演员脸、剧照构图或某版影视整套造型。
5. 画幅固定为 {aspect_ratio}，这是可长期复用的服装锚点，不是剧情分镜。
6. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
"""


def asset_anchor_prompt(
    ref_id: str,
    asset: dict[str, Any],
    *,
    visual_style: str,
    style_reference_attached: bool = False,
    aspect_ratio: str = "",
) -> str:
    kind = str(asset.get("type") or ref_type(ref_id)).strip().lower()
    kind = {
        "scene": "location",
        "fx": "vfx",
        "effect": "vfx",
        "style_anchor": "style",
    }.get(kind, kind)
    display_name = compact_contract(asset.get("display_name"))
    # Text-only registry bootstrap exposes a generic ``description`` before a
    # specialist has split it into style/prop/dna contracts.  Consume that
    # honest project description as a fallback instead of silently reverting
    # to a hard-coded aesthetic.
    style_contract = compact_contract(
        asset.get("style_contract") or (asset.get("description") if kind == "style" else ""),
        max_len=900,
    )
    prop_contract = compact_contract(
        asset.get("prop_contract")
        or (asset.get("description") if kind in {"monster", "location", "prop", "vfx"} else ""),
        max_len=900,
    )
    dna_contract = compact_contract(
        asset.get("dna_contract")
        or (asset.get("character_dna") if kind == "monster" else ""),
        max_len=900,
    )
    forbidden = compact_contract(asset.get("forbidden_inheritance"), max_len=900)
    style_reference_note = (
        "已附一张项目风格锚图片。它只用于继承线条、上色、明暗、材质、色域和墨晕语言；"
        "不得复制其中人物、服装、姿势、具体物件、场景布局或构图。"
        if style_reference_attached
        else "本次没有风格图片附件；严格按项目基础视觉风格与资产契约执行。"
    )
    if kind == "style":
        subject_rules = (
            "生成一张原创、单幅、非叙事的漫画风格校准画，严格服从项目基础视觉风格和 style_contract；"
            "用一名无具体身份的中性测试人物与少量契约指定的衣料、建筑/自然材质来校验线、色、光、明暗、边缘和表面语言；"
            "人物脸、手和材质要清楚可读，但不得自行假定古典、水墨、矿物淡彩、现代摄影或任何其他未登记时代/媒介。"
            "这不是项目角色、影视演员、剧情镜头、拼贴、九宫格、角色卡、设定表或多视图。"
        )
    elif kind == "monster":
        subject_rules = (
            "生成单体妖物 reference art：首先严格执行 dna_contract 登记的解剖结构与姿态；"
            "完整主体入画，该有的头、躯干、手臂/前肢、腿/后肢和永久标志必须清楚；"
            "人身兽首必须保持直立双足人体结构，不得改成四足兽；"
            "dna_contract 未登记尾巴、翅膀、额外肢体时不得自行增加；"
            "中性低饱和背景，不要血腥内脏，不要战斗叙事，不要人物。"
        )
    elif kind == "location":
        subject_rules = (
            "生成场景 reference art：清楚交代空间布局、主光方向、固定物件、入口/窗/路/桌案等轴线关系；"
            "这是可跨镜头复用的纯场景锚点，不出现任何具体人物、人物剪影或角色表演；"
            "若资产契约提到人物站位，只在对应位置保留可用的空白与走位空间，不把人物固化进场景图。"
            "不要现代物件，不要可读随机文字。"
        )
    elif kind == "prop":
        subject_rules = (
            "生成单个道具 reference art：道具完整居中，结构、材质、比例和磨损细节清楚；"
            "中性低饱和背景，不要手持动作，不要角色，不要 logo、水印或可读随机文字。"
        )
    elif kind == "vfx":
        subject_rules = (
            "生成单一视觉特效 reference art：清楚展示形状语言、边缘软硬、运动方向、颜色范围和与留白的关系；"
            "使用中性低饱和承载面，不要人物表演、完整剧情场景、游戏法阵、UI、logo、水印或可读随机文字。"
        )
    else:
        subject_rules = (
            "生成共享资产 reference art：主体完整、结构清楚、便于后续作为漫画参考图；"
            "不要额外人物、文字、logo、水印或 UI。"
        )
    ratio_rule = f"画幅固定为 {aspect_ratio}，不得输出其他比例。" if aspect_ratio else ""
    return f"""请用内置 image_generation 工具生成漫画共享参考锚点图。

参考 ID：{ref_id}
类型：{kind}
名称：{display_name or ref_id}

资产契约：
- style_contract: {style_contract or '未登记'}
- prop_contract: {prop_contract or '未登记'}
- dna_contract: {dna_contract or '未登记'}
- forbidden_inheritance: {forbidden or '未登记'}

风格参考规则：
{style_reference_note}

画面要求：
1. {subject_rules}
2. 保持项目基础视觉风格：{visual_style}；以登记的 style_contract 为时代、媒介、色域、材质和明暗唯一真值，不得将未登记的古典/水墨/矿物色、现代摄影、游戏 UI 或高饱和彩漫风偷渡进项目；线与灰阶体积应清楚可审。
3. 这是一张长期共享锚点，不是剧情分镜；构图应稳定、信息清楚、少动态夸张，适合后续作为逐格生图参考附件。
4. 如果资产是告示、榜文、门帘、银两等道具，只画图像结构，不生成可读长文或乱码文字。
5. {ratio_rule or '遵循项目登记的画幅约束。'}
6. 生成完成后只回复一句完成，不要写文件、不要搜索文件系统、不要输出 Markdown。
"""


def parse_csv(raw: str, default: tuple[str, ...]) -> list[str]:
    if not raw:
        return list(default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def character_generation_anchor(
    root: Path,
    shared_dir: Path,
    asset: dict[str, Any],
    character_id: str,
    view: str,
    *,
    prefer_front_anchor: bool,
) -> tuple[Path, str]:
    raw_anchor = str(asset.get("anchor_path") or "").strip()
    fallback = resolve_path(root, raw_anchor) if raw_anchor else shared_dir / f"{character_id}__anchor.png"
    if prefer_front_anchor and view != "front":
        front = shared_dir / f"{character_id}__front.png"
        if png_valid(front):
            return front, "front_view_anchor"
    return fallback, "registry_anchor"


def project_style_anchor(root: Path, registry: dict) -> Path | None:
    """Return a valid adopted style image without treating it as identity."""
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    preferred = read_setting(root, "风格锚", "").strip()
    style_ids: list[str] = []
    if preferred:
        style_ids.append(preferred)
    style_ids.extend(
        rid
        for rid, asset in sorted(assets.items())
        if rid not in style_ids
        and (
            rid.startswith("STYLE_")
            or (isinstance(asset, dict) and str(asset.get("type") or "").strip().lower() in {"style", "style_anchor"})
        )
    )
    for rid in style_ids:
        asset = assets.get(rid) if isinstance(assets.get(rid), dict) else {}
        for key in ("anchor_path", "primary_path", "path"):
            raw = str(asset.get(key) or "").strip()
            if raw:
                candidate = resolve_path(root, raw)
                if png_valid(candidate):
                    return candidate
        fallback = root / "出图" / "共享" / "图片" / f"{rid}__anchor.png"
        if png_valid(fallback):
            return fallback
    return None


def existing_view_source(asset: dict[str, Any], view: str) -> dict[str, Any]:
    for item in asset.get("reference_images") or []:
        if isinstance(item, dict) and item.get("view") == view and isinstance(item.get("source"), dict):
            source = dict(item["source"])
            if source.get("kind") != "existing_character_view":
                return source
    return {}


def existing_anchor_source(root: Path, asset: dict[str, Any], path: Path) -> dict[str, Any]:
    for item in asset.get("reference_images") or []:
        if not isinstance(item, dict) or not isinstance(item.get("source"), dict):
            continue
        raw = str(item.get("path") or "").strip()
        if raw and resolve_path(root, raw).resolve() == path.resolve():
            return dict(item["source"])
    if isinstance(asset.get("source"), dict):
        return dict(asset["source"])
    return {}


def latest_character_view_event(root: Path, character_id: str, view: str) -> dict[str, Any]:
    path = root / "生产数据" / "comic_image_generation.jsonl"
    if not path.is_file():
        return {}
    latest: dict[str, Any] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                row.get("status") == "character_view_ready"
                and row.get("ref_id") == character_id
                and row.get("view") == view
            ):
                latest = row
    return latest


def source_from_event(row: dict[str, Any], *, anchor_path: str, anchor_kind: str, chapter: str, view: str) -> dict[str, Any]:
    if not row:
        return {}
    source = {
        "kind": "generated_character_view",
        "backend": row.get("backend", ""),
        "model": row.get("model", ""),
        "anchor_path": row.get("anchor_path") or anchor_path,
        "anchor_kind": row.get("anchor_kind") or anchor_kind,
        "view": view,
        "chapter": chapter,
        "attempt": row.get("attempt", ""),
    }
    for key in (
        "backend_version",
        "model_version",
        "resolution_type",
        "ratio",
        "submit_id",
        "style_reference_path",
        "style_reference_sha256",
        "style_reference_role",
        "prompt_path",
        "prompt_sha256",
        "archived_previous_path",
    ):
        if row.get(key):
            source[key] = row[key]
    return source


def register_character_view(registry: dict, root: Path, character_id: str, view: str, path: Path, *, source: dict[str, Any]) -> None:
    assets = registry.setdefault("assets", {})
    asset = assets.get(character_id) if isinstance(assets.get(character_id), dict) else {}
    rel = rel_to_root(root, path)
    refs = [item for item in asset.get("reference_images", []) if not (isinstance(item, dict) and item.get("view") == view)]
    anchor_raw = str(source.get("anchor_path") or "").strip()
    anchor = resolve_path(root, anchor_raw) if anchor_raw else path
    origin_sha = file_sha256(anchor) if png_valid(anchor) else file_sha256(path)
    derivation = {
        "method": (
            "generated_from_text_seed"
            if str(source.get("anchor_kind") or "") == "text_prompt_seed"
            else "generated_from_shared_anchor"
            if str(source.get("kind") or "").startswith("generated")
            else "adopted_existing_view"
        ),
        "source_path": rel_to_root(root, anchor),
        "source_sha256": origin_sha,
        "crop_box": [],
    }
    dims = png_dimensions(path)
    refs.append(
        {
            "view": view,
            "path": rel,
            "sha256": file_sha256(path),
            "source": source,
            "derivation": derivation,
            "canvas": {"width": dims[0], "height": dims[1]} if dims else {},
            "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
    )
    views = asset.get("views") if isinstance(asset.get("views"), dict) else {}
    views[view] = rel
    # The canonical front is also the default outfit's first real visual
    # reference.  Register it once so downstream planning does not report a
    # false clothing gap after a valid front has already been adopted.
    if view == "front" and str(asset.get("type") or "character").strip().lower() == "character":
        binding = asset.get("default_binding") if isinstance(asset.get("default_binding"), dict) else {}
        outfit_id = str(binding.get("outfit_id") or "").strip()
        outfits = asset.get("outfits") if isinstance(asset.get("outfits"), dict) else {}
        outfit = outfits.get(outfit_id) if isinstance(outfits.get(outfit_id), dict) else None
        if outfit is not None:
            outfit_refs = [
                item for item in outfit.get("reference_images", [])
                if str(item.get("path") if isinstance(item, dict) else item or "").strip() != rel
            ]
            outfit_refs.append({
                "path": rel,
                "sha256": file_sha256(path),
                "view": "front",
                "source": {"kind": "default_outfit_from_character_front", "character_id": character_id},
                "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
            })
            outfit["reference_images"] = outfit_refs
            outfit["status"] = "ready"
    tier_required = required_views_for(asset)
    ready_views = [
        required_view
        for required_view in tier_required
        if isinstance(views.get(required_view), str)
        and png_valid(resolve_path(root, str(views[required_view])))
    ]
    missing_views = [required_view for required_view in tier_required if required_view not in ready_views]
    asset.update(
        {
            "id": character_id,
            "type": "character",
            "status": "partial" if missing_views else "needs_approval",
            "views": views,
            "view_readiness": {
                "required": list(tier_required),
                "tier": str(asset.get("library_tier") or asset.get("tier") or "") or "unspecified(full)",
                "ready": ready_views,
                "missing": missing_views,
                "complete": not missing_views,
            },
            "reference_images": refs,
            "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
    )
    assets[character_id] = asset
    apply_character_readiness(root, registry, character_id)


def register_outfit_reference(
    registry: dict,
    root: Path,
    character_id: str,
    outfit_id: str,
    path: Path,
    *,
    source: dict[str, Any],
) -> None:
    assets = registry.setdefault("assets", {})
    asset = assets.get(character_id) if isinstance(assets.get(character_id), dict) else {}
    outfits = asset.get("outfits") if isinstance(asset.get("outfits"), dict) else {}
    outfit = outfits.get(outfit_id) if isinstance(outfits.get(outfit_id), dict) else None
    if outfit is None:
        raise ValueError(f"registry 未登记 {character_id}/{outfit_id}")
    rel = rel_to_root(root, path)
    refs = [
        item for item in outfit.get("reference_images", [])
        if str(item.get("path") if isinstance(item, dict) else item or "").strip() != rel
    ]
    refs.append({
        "path": rel,
        "sha256": file_sha256(path),
        "view": "front",
        "source": source,
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
    })
    outfit.update({
        "reference_images": refs,
        "status": "ready",
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
    })
    outfits[outfit_id] = outfit
    asset["outfits"] = outfits
    asset["updated_at"] = dt.datetime.now().isoformat(timespec="seconds")
    assets[character_id] = asset


def register_asset_anchor(registry: dict, root: Path, ref_id: str, path: Path, *, source: dict[str, Any]) -> None:
    assets = registry.setdefault("assets", {})
    asset = assets.get(ref_id) if isinstance(assets.get(ref_id), dict) else {}
    rel = rel_to_root(root, path)
    refs = [
        item
        for item in asset.get("reference_images", [])
        if not (isinstance(item, dict) and item.get("kind") == "anchor")
    ]
    refs.append(
        {
            "kind": "anchor",
            "path": rel,
            "sha256": file_sha256(path),
            "source": source,
            "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
    )
    asset.update(
        {
            "id": ref_id,
            "type": asset.get("type") or ref_type(ref_id),
            "status": "ready",
            "anchor_path": rel,
            "primary_path": rel,
            "reference_images": refs,
            "sha256": file_sha256(path),
            "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
    )
    assets[ref_id] = asset


def write_character_view_contact_sheet(root: Path, chapter: str, characters: list[str], views: list[str]) -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return ""

    shared_dir = root / "出图" / "共享" / "图片"
    cell_w = 260
    cell_h = 360
    header_h = 34
    label_h = 28
    gap = 12
    single_view_casting = len(views) == 1 and len(characters) > 1
    if single_view_casting:
        cols = min(3, len(characters))
        rows = max(1, (len(characters) + cols - 1) // cols)
    else:
        cols = max(1, len(views))
        rows = max(1, len(characters))
    width = gap + cols * (cell_w + gap)
    height = header_h + gap + rows * (cell_h + label_h + gap)
    canvas = Image.new("RGB", (width, height), (24, 24, 24))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    if single_view_casting:
        draw.text((gap, 10), f"{views[0]} · character casting", fill=(238, 238, 238), font=font)
        cells = [
            (index // cols, index % cols, character_id, views[0])
            for index, character_id in enumerate(characters)
        ]
    else:
        for col, view in enumerate(views):
            x = gap + col * (cell_w + gap)
            draw.text((x, 10), view, fill=(238, 238, 238), font=font)
        cells = [
            (row, col, character_id, view)
            for row, character_id in enumerate(characters)
            for col, view in enumerate(views)
        ]
    for row, col, character_id, view in cells:
        y = header_h + gap + row * (cell_h + label_h + gap)
        x = gap + col * (cell_w + gap)
        image_path = shared_dir / f"{character_id}__{view}.png"
        if image_path.is_file():
            try:
                image = Image.open(image_path).convert("RGB")
                image.thumbnail((cell_w, cell_h), Image.LANCZOS)
                px = x + (cell_w - image.width) // 2
                py = y + (cell_h - image.height) // 2
                canvas.paste(image, (px, py))
            except OSError:
                draw.rectangle((x, y, x + cell_w, y + cell_h), outline=(180, 68, 68), width=2)
                draw.text((x + 8, y + 8), "invalid image", fill=(255, 180, 180), font=font)
        else:
            draw.rectangle((x, y, x + cell_w, y + cell_h), outline=(180, 68, 68), width=2)
            draw.text((x + 8, y + 8), "missing", fill=(255, 180, 180), font=font)
        draw.text((x, y + cell_h + 8), f"{character_id} {view}", fill=(238, 238, 238), font=font)
    out = root / "生产数据" / f"comic_identity_views_{chapter}_contact_sheet.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, quality=90)
    return rel_to_root(root, out)


def ref_type(ref_id: str) -> str:
    prefix = ref_id.split("_", 1)[0]
    return {
        "CHAR": "character",
        "MON": "monster",
        "LOC": "location",
        "PROP": "prop",
        "STYLE": "style",
        "FX": "vfx",
        "SYS": "system_asset",
        "VFX": "vfx",
        "OUTFIT": "outfit",
    }.get(prefix, "asset")


def parse_map(items: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--map must be REF_ID=PANEL_ID_OR_PATH, got: {item}")
        rid, src = item.split("=", 1)
        rid = rid.strip()
        src = src.strip()
        if not rid or not src:
            raise SystemExit(f"--map must be REF_ID=PANEL_ID_OR_PATH, got: {item}")
        out[rid] = src
    return out


def panel_lookup(root: Path, chapter: str, jobs: dict) -> dict[str, Path]:
    panels: dict[str, Path] = {}
    for job in jobs.get("jobs") or []:
        pid = str(job.get("panel_id") or "")
        rel = str(job.get("result_path") or "")
        if pid and rel:
            panels[pid] = resolve_path(root, rel)
        if pid and pid not in panels:
            panels[pid] = root / "出图" / chapter / "panels" / f"{pid}.png"
    return panels


def source_path(root: Path, chapter: str, panels: dict[str, Path], raw: str) -> Path:
    if raw in panels:
        return panels[raw]
    path = Path(raw)
    if not path.is_absolute():
        direct = root / path
        if direct.is_file():
            return direct
        panel = root / "出图" / chapter / "panels" / raw
        if panel.is_file():
            return panel
    return path


def resolve_reference_path(root: Path, ref_id: str, registry: dict, view: str = "") -> str:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets, dict) else None
    candidates: list[Path] = []
    if isinstance(asset, dict):
        if view:
            views = asset.get("views") if isinstance(asset.get("views"), dict) else {}
            raw_view = views.get(view) if isinstance(views, dict) else ""
            if isinstance(raw_view, str) and raw_view.strip():
                candidates.append(resolve_path(root, raw_view))
            for item in asset.get("reference_images") or []:
                if not isinstance(item, dict) or str(item.get("view") or "") != view:
                    continue
                raw = item.get("path")
                if isinstance(raw, str) and raw.strip():
                    candidates.append(resolve_path(root, raw))
        for key in ("anchor_path", "primary_path", "path"):
            raw = asset.get(key)
            if isinstance(raw, str) and raw.strip():
                candidates.append(resolve_path(root, raw))
        for item in asset.get("reference_images") or []:
            raw = item.get("path") if isinstance(item, dict) else item
            if isinstance(raw, str) and raw.strip():
                candidates.append(resolve_path(root, raw))
    shared = root / "出图" / "共享" / "图片"
    for suffix in ("__anchor.png", ".png", ".jpg", ".jpeg", ".webp"):
        candidates.append(shared / f"{ref_id}{suffix}")
    for path in candidates:
        if path.is_file():
            return rel_to_root(root, path)
    return ""


def character_view_paths(root: Path, ref_id: str, registry: dict) -> dict[str, str]:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(ref_id) if isinstance(assets, dict) else None
    found: dict[str, str] = {}
    if isinstance(asset, dict):
        for item in asset.get("reference_images") or []:
            if not isinstance(item, dict):
                continue
            view = str(item.get("view") or "").strip()
            raw = str(item.get("path") or "").strip()
            if view and raw and resolve_path(root, raw).is_file():
                found[view] = rel_to_root(root, resolve_path(root, raw))
        views = asset.get("views")
        if isinstance(views, dict):
            for view, raw in views.items():
                if isinstance(raw, str) and raw.strip() and resolve_path(root, raw).is_file():
                    found[str(view)] = rel_to_root(root, resolve_path(root, raw))
    shared = root / "出图" / "共享" / "图片"
    for view in REQUIRED_CHARACTER_VIEWS:
        for suffix in (".png", ".jpg", ".jpeg", ".webp"):
            path = shared / f"{ref_id}__{view}{suffix}"
            if path.is_file():
                found.setdefault(view, rel_to_root(root, path))
                break
    return found


def bind_job_references(root: Path, jobs: dict, registry: dict) -> int:
    changed = 0
    for job in jobs.get("jobs") or []:
        for ref in job.get("references") or []:
            if not isinstance(ref, dict):
                continue
            rid = str(ref.get("id") or "")
            if not rid:
                continue
            view = str(ref.get("view") or "")
            role = str(ref.get("role") or "")
            lookup_view = view
            if view == "outfit" or role == "outfit":
                binding = job.get("outfit_binding") if isinstance(job.get("outfit_binding"), dict) else {}
                outfit_id = str(binding.get("outfit_id") or "").strip()
                if not outfit_id or (
                    binding.get("ref_id") and str(binding.get("ref_id")) != rid
                ):
                    outfit_id = ""
                    for character_binding in job.get("character_bindings") or []:
                        if not isinstance(character_binding, dict):
                            continue
                        if str(character_binding.get("character_id") or "") != rid:
                            continue
                        outfit_id = str(character_binding.get("outfit_id") or "").strip()
                        break
                if outfit_id:
                    lookup_view = f"outfit:{outfit_id}"
            elif view == "expression" or role == "expression":
                expression_id = str(ref.get("contract_id") or "").strip()
                if not expression_id:
                    for binding in job.get("character_bindings") or []:
                        if isinstance(binding, dict) and str(binding.get("character_id") or "") == rid:
                            expression_id = str(binding.get("expression_id") or "").strip()
                            break
                if expression_id:
                    lookup_view = f"expression:{expression_id}"

            path = ""
            if lookup_view.startswith("outfit:"):
                outfit_id = lookup_view.split(":", 1)[1]
                assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
                asset = assets.get(rid) if isinstance(assets, dict) else None
                outfits = asset.get("outfits") if isinstance(asset, dict) and isinstance(asset.get("outfits"), dict) else {}
                outfit = outfits.get(outfit_id) if isinstance(outfits.get(outfit_id), dict) else {}
                for item in outfit.get("reference_images") or []:
                    raw = item.get("path") if isinstance(item, dict) else item
                    if not isinstance(raw, str) or not raw.strip():
                        continue
                    candidate = resolve_path(root, raw)
                    if candidate.is_file():
                        path = rel_to_root(root, candidate)
                        break
            elif lookup_view.startswith("expression:"):
                expression_id = lookup_view.split(":", 1)[1]
                assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
                asset = assets.get(rid) if isinstance(assets, dict) else None
                expressions = (
                    asset.get("expressions")
                    if isinstance(asset, dict) and isinstance(asset.get("expressions"), dict)
                    else {}
                )
                expression = expressions.get(expression_id) if isinstance(expressions.get(expression_id), dict) else {}
                for item in expression.get("reference_images") or []:
                    raw = item.get("path") if isinstance(item, dict) else item
                    if not isinstance(raw, str) or not raw.strip():
                        continue
                    candidate = resolve_path(root, raw)
                    if candidate.is_file():
                        path = rel_to_root(root, candidate)
                        break
            if not path and not lookup_view.startswith(("outfit:", "expression:")):
                path = resolve_reference_path(root, rid, registry, view=lookup_view)
            if path:
                current_sha = file_sha256(resolve_path(root, path))
                if ref.get("path") != path or ref.get("sha256") != current_sha:
                    ref["path"] = path
                    ref["sha256"] = current_sha
                    changed += 1
    return changed


def write_reference_index(root: Path, chapter: str, jobs: dict) -> None:
    refs: dict[str, dict[str, object]] = {}
    for job in jobs.get("jobs", []):
        for ref in job.get("references", []):
            rid = ref.get("id")
            if rid:
                item = refs.setdefault(rid, {"count": 0, "path": ""})
                item["count"] = int(item.get("count") or 0) + 1
                if ref.get("path"):
                    item["path"] = ref.get("path")
    lines = [
        f"# 共享参考任务索引 — {chapter}",
        "",
        "正式逐格出图前，先补齐这些角色、场景、道具或特效参考。",
        "",
        "| ref_id | 出现次数 | 状态 | 建议 |",
        "|---|---:|---|---|",
    ]
    for rid, item in sorted(refs.items()):
        count = int(item.get("count") or 0)
        path = str(item.get("path") or "")
        if path:
            lines.append(f"| {rid} | {count} | ✅ | `{path}` |")
        else:
            lines.append(f"| {rid} | {count} | ⬜ | 生成或放入 `出图/共享/图片/` 后回填 panel_jobs.json |")
    if not refs:
        lines.append("| （无） | 0 | - | 当前脚本未声明 references |")
    path = root / "出图" / "共享" / "prompt" / "00_索引.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_event(root: Path, row: dict[str, Any]) -> None:
    path = root / "生产数据" / "comic_image_generation.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def generation_attempt_ledger_path(root: Path, chapter: str) -> Path:
    return root / "生产数据" / f"comic_identity_attempt_ledger_{chapter}.json"


def load_generation_attempt_ledger(root: Path, chapter: str) -> dict[str, Any]:
    path = generation_attempt_ledger_path(root, chapter)
    if path.is_file():
        try:
            payload = load_json(path)
            if isinstance(payload, dict):
                payload.setdefault("schema_version", 1)
                payload.setdefault("kind", "comic_identity_generation_attempt_ledger")
                payload.setdefault("chapter", chapter)
                payload.setdefault("attempts", [])
                return payload
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema_version": 1,
        "kind": "comic_identity_generation_attempt_ledger",
        "chapter": chapter,
        "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "attempts": [],
    }


def generation_attempts_used(
    ledger: dict[str, Any],
    generation_kind: str,
    asset_id: str,
    variant: str,
) -> int:
    rows = [
        row for row in ledger.get("attempts") or []
        if isinstance(row, dict)
        and row.get("generation_kind") == generation_kind
        and row.get("asset_id") == asset_id
        and row.get("variant") == variant
    ]
    return len(rows)


def begin_generation_attempt(
    root: Path,
    chapter: str,
    *,
    generation_kind: str,
    asset_id: str,
    variant: str,
    max_attempts_total: int,
    backend: str,
    model: str,
    prompt_sha256: str,
) -> tuple[str, int]:
    """在调用付费/远端后端前持久化一次尝试；中断也会占用额度。"""
    ledger = load_generation_attempt_ledger(root, chapter)
    used = generation_attempts_used(ledger, generation_kind, asset_id, variant)
    if used >= max_attempts_total:
        return "", used
    cumulative_attempt = used + 1
    now = dt.datetime.now().isoformat(timespec="microseconds")
    attempt_id = hashlib.sha256(
        f"{chapter}|{generation_kind}|{asset_id}|{variant}|{cumulative_attempt}|{now}".encode("utf-8")
    ).hexdigest()[:20]
    row = {
        "attempt_id": attempt_id,
        "started_at": now,
        "status": "started",
        "generation_kind": generation_kind,
        "asset_id": asset_id,
        "variant": variant,
        "cumulative_attempt": cumulative_attempt,
        "max_attempts_total": max_attempts_total,
        "backend": backend,
        "model": model,
        "prompt_sha256": prompt_sha256,
    }
    ledger.setdefault("attempts", []).append(row)
    ledger["updated_at"] = now
    write_json(generation_attempt_ledger_path(root, chapter), ledger)
    return attempt_id, cumulative_attempt


def finish_generation_attempt(
    root: Path,
    chapter: str,
    attempt_id: str,
    *,
    status: str,
    error: str = "",
    artifact_path: str = "",
    artifact_sha256: str = "",
) -> None:
    if not attempt_id:
        return
    ledger = load_generation_attempt_ledger(root, chapter)
    for row in ledger.get("attempts") or []:
        if not isinstance(row, dict) or row.get("attempt_id") != attempt_id:
            continue
        row["status"] = status
        row["finished_at"] = dt.datetime.now().isoformat(timespec="microseconds")
        if error:
            row["error"] = error
        if artifact_path:
            row["artifact_path"] = artifact_path
        if artifact_sha256:
            row["artifact_sha256"] = artifact_sha256
        break
    ledger["updated_at"] = dt.datetime.now().isoformat(timespec="microseconds")
    write_json(generation_attempt_ledger_path(root, chapter), ledger)


def archive_json_before_replace(root: Path, path: Path) -> tuple[str, str]:
    if not path.is_file():
        return "", ""
    sha256 = file_sha256(path)
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
    archived = root / "生产数据" / "history" / f"{path.stem}__{stamp}.json"
    archived.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, archived)
    return rel_to_root(root, archived), sha256


def seed(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    chapter = args.chapter
    jobs = load_json(jobs_path(root, chapter))
    mapping = parse_map(args.map)
    if not mapping:
        raise SystemExit("provide at least one --map REF_ID=PANEL_ID_OR_PATH")

    registry = load_registry(root)
    assets = registry.setdefault("assets", {})
    if not isinstance(assets, dict):
        raise SystemExit("identity_registry.json assets must be an object")

    panels = panel_lookup(root, chapter, jobs)
    shared_dir = root / "出图" / "共享" / "图片"
    shared_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().isoformat(timespec="seconds")
    seeded: dict[str, str] = {}
    for rid, raw in mapping.items():
        src = source_path(root, chapter, panels, raw)
        if not png_valid(src):
            raise SystemExit(f"source for {rid} is not a valid PNG: {src}")
        dest = shared_dir / f"{rid}__anchor.png"
        if dest.exists() and not args.overwrite:
            raise SystemExit(f"{dest} already exists; pass --overwrite to replace it")
        shutil.copy2(src, dest)
        rel = rel_to_root(root, dest)
        seeded[rid] = rel
        assets[rid] = {
            **(assets.get(rid) if isinstance(assets.get(rid), dict) else {}),
            "id": rid,
            "type": ref_type(rid),
            "status": "partial" if rid.startswith(("CHAR_", "MON_")) else "ready",
            "anchor_path": rel,
            "source": {
                "kind": "accepted_panel_anchor",
                "chapter": chapter,
                "source": raw,
                "source_path": rel_to_root(root, src),
            },
            "sha256": file_sha256(dest),
            "updated_at": now,
            "notes": "Shared anchor seeded from an accepted comic panel; replace with dedicated turnaround/design-sheet art when available.",
        }
        append_event(root, {
            "ts": now,
            "status": "reference_anchor_ready",
            "ref_id": rid,
            "path": rel,
            "source": raw,
            "sha256": assets[rid]["sha256"],
        })

    write_json(registry_path(root), registry)
    changed = bind_job_references(root, jobs, registry)
    write_json(jobs_path(root, chapter), jobs)
    write_reference_index(root, chapter, jobs)
    print(f"[ok] seeded {len(seeded)} anchors; updated {changed} job references")
    return 0


def job_reference_status(root: Path, job: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    missing: list[str] = []
    valid: list[dict[str, str]] = []
    seen: set[str] = set()
    for ref in job.get("references") or []:
        if not isinstance(ref, dict):
            continue
        rid = str(ref.get("id") or "").strip()
        raw = str(ref.get("path") or "").strip()
        if not rid:
            continue
        if not raw:
            missing.append(rid)
            continue
        path = resolve_path(root, raw)
        if not path.is_file():
            missing.append(rid)
            continue
        rel = rel_to_root(root, path)
        if rel in seen:
            continue
        seen.add(rel)
        valid.append({"id": rid, "path": rel, "sha256": file_sha256(path)})
    return missing, valid


def stale_generated_references(
    root: Path,
    job: dict[str, Any],
    sha_cache: dict[str, str],
) -> list[dict[str, str]]:
    """比对生成时 reference manifest 记录的 sha256 与当前参考图内容。

    只检查生成时真实附入过的参考图：内容变化或文件消失都视为陈旧。
    生成之后新补充的参考图（扩充视图）不在此列，保持"参考扩充不强制重抽"。
    manifest 文件缺失或不可解析时跳过（旧数据没有逐格 manifest）。
    """
    manifest_rel = str(job.get("reference_manifest") or "").strip()
    if not manifest_rel or str(job.get("status") or "") != "ready":
        return []
    manifest_path = resolve_path(root, manifest_rel)
    if not manifest_path.is_file():
        return []
    try:
        manifest = load_json(manifest_path)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(manifest, dict):
        return []
    stale: list[dict[str, str]] = []
    for record in manifest.get("references") or []:
        if not isinstance(record, dict):
            continue
        recorded_sha = str(record.get("sha256") or "").strip()
        raw = str(record.get("path") or "").strip()
        if not recorded_sha or not raw:
            continue
        path = resolve_path(root, raw)
        if not path.is_file():
            stale.append({"id": str(record.get("id") or ""), "path": raw, "reason": "reference_file_missing"})
            continue
        key = str(path.resolve())
        if key not in sha_cache:
            sha_cache[key] = file_sha256(path)
        if sha_cache[key] != recorded_sha:
            stale.append({"id": str(record.get("id") or ""), "path": raw, "reason": "reference_content_changed"})
    return stale


def report_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# 漫画一致性报告 — {report['chapter']}",
        "",
        f"- 生成时间：{report['created_at']}",
        f"- reference 总数：{report['summary']['reference_count']}",
        f"- 缺失 reference：{len(report['missing_refs'])}",
        f"- 需要重抽格：{len(report['rerun_targets'])}",
        f"- registry v2 结构问题：{report.get('registry_validation', {}).get('summary', {}).get('block', 0)}",
        f"- model pack 待修/待签收：{len(report.get('model_pack_gaps') or {})}",
        "",
    ]
    if report["missing_refs"]:
        lines += ["## 缺失 Reference", "", "| ref_id | 出现格 |", "|---|---|"]
        for rid, panels in sorted(report["missing_refs"].items()):
            lines.append(f"| {rid} | {', '.join(panels)} |")
        lines.append("")
    if report["rerun_targets"]:
        lines += ["## 重抽目标", "", "| panel | reason | valid_refs |", "|---|---|---:|"]
        panels_by_id = {item["panel_id"]: item for item in report["panels"]}
        for pid in report["rerun_targets"]:
            item = panels_by_id.get(pid, {})
            lines.append(f"| {pid} | {item.get('rerun_reason', '')} | {item.get('valid_reference_count', 0)} |")
        lines += [
            "",
            "建议命令：",
            "",
            "```bash",
            "python3 skills/comic-image/scripts/codex_panel_runner.py "
            f"\"{report['project_root']}\" --chapter {report['chapter']} "
            f"--targets {','.join(report['rerun_targets'])} --force --max-attempts 3",
            "```",
            "",
        ]
    if report.get("missing_character_views"):
        lines += ["## 人物多视图缺口", "", "| character | missing views |", "|---|---|"]
        for rid, missing in sorted(report["missing_character_views"].items()):
            lines.append(f"| {rid} | {', '.join(missing)} |")
        lines.append("")
    lines += ["## 每格状态", "", "| panel | status | refs | missing | generated_with_refs |", "|---|---|---:|---|---:|"]
    for item in report["panels"]:
        lines.append(
            f"| {item['panel_id']} | {item['status']} | {item['valid_reference_count']} | "
            f"{', '.join(item['missing_refs']) or '-'} | {item['generated_reference_input_count']} |"
        )
    return "\n".join(lines) + "\n"


def report(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    chapter = args.chapter
    job_path = jobs_path(root, chapter)
    if not job_path.is_file():
        rel_job_path = rel_to_root(root, job_path)
        raise SystemExit(
            f"missing {rel_job_path}; run `python3 skills/comic-image/scripts/build_panel_jobs.py "
            f"\"{root}\" --chapter {chapter}` before `comic-identity report`"
        )
    try:
        jobs = load_json(job_path)
    except json.JSONDecodeError as exc:
        rel_job_path = rel_to_root(root, job_path)
        raise SystemExit(f"invalid JSON in {rel_job_path}: {exc}") from exc
    registry = load_registry(root)
    changed = bind_job_references(root, jobs, registry) if args.write else 0
    if args.write:
        write_json(jobs_path(root, chapter), jobs)
        write_reference_index(root, chapter, jobs)

    missing_refs: dict[str, list[str]] = {}
    refs_seen: set[str] = set()
    panels: list[dict[str, Any]] = []
    rerun_targets: list[str] = []
    outfit_gaps: dict[str, str] = {}
    reference_sha_cache: dict[str, str] = {}
    registry_assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    for job in jobs.get("jobs") or []:
        pid = str(job.get("panel_id") or "")
        missing, valid = job_reference_status(root, job)
        outfit_binding = job.get("outfit_binding") if isinstance(job.get("outfit_binding"), dict) else {}
        if outfit_binding.get("outfit_id"):
            outfit_id = str(outfit_binding.get("outfit_id"))
            if not outfit_binding.get("registered"):
                outfit_gaps[pid] = f"outfit_id={outfit_id} 未在 registry.assets[角色].outfits 登记"
            else:
                ref_id = str(outfit_binding.get("ref_id") or "")
                asset = registry_assets.get(ref_id) if isinstance(registry_assets.get(ref_id), dict) else {}
                outfits = asset.get("outfits") if isinstance(asset.get("outfits"), dict) else {}
                outfit = outfits.get(outfit_id) if isinstance(outfits.get(outfit_id), dict) else {}
                registered_paths = {
                    rel_to_root(root, resolve_path(root, str(item.get("path") or "")))
                    for item in outfit.get("reference_images") or []
                    if isinstance(item, dict)
                    and str(item.get("path") or "").strip()
                    and resolve_path(root, str(item.get("path") or "")).is_file()
                }
                valid_paths = {str(ref.get("path") or "") for ref in valid}
                attached = [
                    ref for ref in valid
                    if any(
                        str(r.get("view") or "").startswith("outfit:") and str(r.get("path")) == ref["path"]
                        for r in job.get("references") or []
                        if isinstance(r, dict)
                    )
                ]
                # 同一张 approved front/turnaround 常同时承担身份与基础服装锚。
                # 附件计划会按路径去重，因此不能只凭 outfit: 标签判缺；还需按
                # registry outfits.reference_images 与已实际附入路径复核。
                if not attached and not (registered_paths & valid_paths):
                    outfit_gaps[pid] = f"outfit_id={outfit_id} 已登记但没有可用服装参考图（补 outfits.reference_images）"
        for ref in job.get("references") or []:
            if isinstance(ref, dict) and ref.get("id"):
                refs_seen.add(str(ref.get("id")))
        for rid in missing:
            missing_refs.setdefault(rid, []).append(pid)
        generated_count = int(job.get("reference_input_count") or 0)
        stale_refs = stale_generated_references(root, job, reference_sha_cache)
        needs_rerun = False
        reason = ""
        if valid and job.get("status") == "ready" and generated_count == 0:
            needs_rerun = True
            reason = "ready panel was generated before real reference images were attached"
        elif valid and job.get("status") == "ready" and not job.get("reference_manifest"):
            needs_rerun = True
            reason = "ready panel has no reference manifest evidence"
        elif stale_refs:
            needs_rerun = True
            reason = "generated-with reference images changed after generation: " + ",".join(
                f"{item.get('id') or item.get('path')}({item.get('reason')})" for item in stale_refs
            )
        reference_delta = max(0, len(valid) - generated_count) if valid and job.get("status") == "ready" else 0
        if needs_rerun:
            rerun_targets.append(pid)
        panels.append(
            {
                "panel_id": pid,
                "status": job.get("status", ""),
                "valid_reference_count": len(valid),
                "valid_references": valid,
                "missing_refs": missing,
                "generated_reference_input_count": generated_count,
                "reference_manifest": job.get("reference_manifest", ""),
                "stale_generated_refs": stale_refs,
                "needs_rerun": needs_rerun,
                "rerun_reason": reason,
                "reference_delta_after_rebind": reference_delta,
            }
        )

    registry_assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    # 2026-07-17 实证修正：一致性审计不再只看 CHAR_。第1话 P015 虎妖被画成四足普通虎，
    # 就是因为 MON_ 不进视图完整性/model-pack/rerun 审计，registry 有定妆也没人核对出图。
    char_ids = sorted(rid for rid in refs_seen | set(registry_assets.keys()) if rid.startswith(("CHAR_", "MON_")))
    missing_character_views: dict[str, list[str]] = {}
    character_views: dict[str, dict[str, str]] = {}
    for rid in char_ids:
        views = character_view_paths(root, rid, registry)
        character_views[rid] = views
        tier_required = required_views_for(registry_assets.get(rid))
        missing = [view for view in tier_required if view not in views]
        if missing:
            missing_character_views[rid] = missing

    registry_validation = validate_registry(registry)
    model_pack_reports: dict[str, dict[str, Any]] = {}
    model_pack_gaps: dict[str, str] = {}
    for rid in char_ids:
        pack = apply_character_readiness(root, registry, rid)
        model_pack_reports[rid] = pack
        if pack.get("readiness") != "ready":
            model_pack_gaps[rid] = str(pack.get("readiness") or "unknown")
    if args.write:
        write_json(registry_path(root), registry)

    payload = {
        "schema_version": 1,
        "kind": "comic_identity_report",
        "project_root": str(root),
        "chapter": chapter,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "write_back": bool(args.write),
        "job_reference_paths_updated": changed,
        "summary": {
            "reference_count": len(refs_seen),
            "panel_count": len(panels),
            "missing_ref_count": len(missing_refs),
            "rerun_target_count": len(rerun_targets),
            "outfit_gap_count": len(outfit_gaps),
        },
        "outfit_gaps": outfit_gaps,
        "registry_validation": registry_validation,
        "model_pack_reports": model_pack_reports,
        "model_pack_gaps": model_pack_gaps,
        "missing_refs": missing_refs,
        "required_character_views": list(REQUIRED_CHARACTER_VIEWS),
        "tier_required_views": {k: list(v) for k, v in TIER_REQUIRED_VIEWS.items()},
        "character_views": character_views,
        "missing_character_views": missing_character_views,
        "rerun_targets": rerun_targets,
        "panels": panels,
    }
    out_json = root / "生产数据" / f"comic_identity_report_{chapter}.json"
    out_md = root / "生产数据" / f"comic_identity_report_{chapter}.md"
    write_json(out_json, payload)
    out_md.write_text(report_markdown(payload), encoding="utf-8")
    print(f"[ok] report: {out_json}")
    if missing_refs:
        print("[warn] missing refs: " + ", ".join(sorted(missing_refs)))
    if rerun_targets:
        print("[plan] rerun targets: " + ",".join(rerun_targets))
    else:
        print("[ok] no rerun targets")
    if missing_character_views:
        print("[warn] missing character views: " + ", ".join(f"{rid}({','.join(views)})" for rid, views in sorted(missing_character_views.items())))
    if outfit_gaps:
        print("[warn] outfit gaps: " + "; ".join(f"{pid}: {reason}" for pid, reason in sorted(outfit_gaps.items())))
    return 0


def generate_anchor_candidates(
    *,
    root: Path,
    repo: Path,
    registry: dict[str, Any],
    refs: list[str],
    chapter: str,
    candidate_count: int,
    max_attempts: int,
    timeout_sec: int,
    ratio: str,
    visual_style: str,
    backend_version: str,
) -> int:
    """Generate review candidates without adopting them into the identity registry."""
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    style_reference = project_style_anchor(root, registry)
    batch_id = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    ready_count = 0
    failed_count = 0
    items: list[dict[str, Any]] = []

    for ref_id in refs:
        asset = assets.get(ref_id) if isinstance(assets.get(ref_id), dict) else {}
        use_style_reference = bool(
            style_reference
            and png_valid(style_reference)
            and ref_id != read_setting(root, "风格锚", "").strip()
        )
        for candidate_index in range(1, candidate_count + 1):
            prompt = asset_anchor_prompt(
                ref_id,
                asset,
                visual_style=visual_style,
                style_reference_attached=use_style_reference,
                aspect_ratio=ratio,
            )
            prompt += f"\n候选批次要求：这是第 {candidate_index}/{candidate_count} 张，必须形成独立可比较的构图方案，同时严格保持同一资产契约。\n"
            prompt_path, prompt_sha256 = prompt_snapshot(
                root,
                chapter,
                ref_id,
                f"anchor_candidate_{candidate_index:02d}_codex",
                prompt,
            )
            out_dir = root / "出图" / "共享" / "candidates" / ref_id / "anchor" / batch_id
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"candidate_{candidate_index:02d}.png"
            ready = False
            last_error = ""
            for attempt in range(1, max(1, max_attempts) + 1):
                proc = run_codex_image(
                    prompt,
                    repo,
                    timeout_sec,
                    [style_reference] if use_style_reference and style_reference else [],
                )
                if proc.returncode != 0:
                    last_error = format_failure(proc)
                    print(
                        f"[retry] {ref_id} candidate {candidate_index}/{candidate_count} "
                        f"attempt {attempt}/{max_attempts}: {last_error}",
                        flush=True,
                    )
                    continue
                pending = out_dir / f".candidate_{candidate_index:02d}__pending.png"
                pending.unlink(missing_ok=True)
                if not decode_image_event(proc.stdout, pending) or not png_valid(pending):
                    last_error = "codex completed but no valid image_generation_end PNG was available"
                    print(
                        f"[retry] {ref_id} candidate {candidate_index}/{candidate_count} "
                        f"attempt {attempt}/{max_attempts}: {last_error}",
                        flush=True,
                    )
                    continue
                raw_canvas_path = ""
                canvas_normalization: dict[str, Any] = {}
                dims = png_dimensions(pending)
                if dims and target_canvas_for_ratio(dims, ratio) != dims:
                    raw = out_dir / f"raw_canvas_{candidate_index:02d}.png"
                    shutil.copy2(pending, raw)
                    raw_canvas_path = rel_to_root(root, raw)
                    canvas_normalization = normalize_png_to_ratio(pending, ratio)
                pending.replace(out_path)
                row = {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "status": "reference_anchor_candidate_ready",
                    "ref_id": ref_id,
                    "candidate_index": candidate_index,
                    "candidate_count": candidate_count,
                    "attempt": attempt,
                    "path": rel_to_root(root, out_path),
                    "sha256": file_sha256(out_path),
                    "ratio": ratio,
                    "backend": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "backend_version": backend_version,
                    "prompt_path": prompt_path,
                    "prompt_sha256": prompt_sha256,
                    "adopted": False,
                }
                if raw_canvas_path:
                    row.update({
                        "raw_canvas_path": raw_canvas_path,
                        "raw_canvas_sha256": file_sha256(resolve_path(root, raw_canvas_path)),
                        "canvas_normalization": canvas_normalization,
                    })
                if use_style_reference and style_reference:
                    row.update(
                        {
                            "style_reference_path": rel_to_root(root, style_reference),
                            "style_reference_sha256": file_sha256(style_reference),
                            "style_reference_role": "style_only",
                        }
                    )
                items.append(row)
                append_event(root, row)
                ready_count += 1
                ready = True
                print(f"[ok] {ref_id} candidate {candidate_index} -> {row['path']}", flush=True)
                break
            if not ready:
                failed_count += 1
                row = {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "status": "reference_anchor_candidate_failed",
                    "ref_id": ref_id,
                    "candidate_index": candidate_index,
                    "candidate_count": candidate_count,
                    "ratio": ratio,
                    "backend": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "error": last_error,
                    "adopted": False,
                }
                items.append(row)
                append_event(root, row)
                print(f"[fail] {ref_id} candidate {candidate_index}: {last_error}", flush=True)

    manifest = {
        "schema_version": 1,
        "kind": "comic_reference_anchor_candidate_batch",
        "chapter": chapter,
        "batch_id": batch_id,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "refs": refs,
        "candidate_count_per_ref": candidate_count,
        "ratio": ratio,
        "backend": CODEX_CHANNEL,
        "model": CODEX_MODEL,
        "execution_mode": CODEX_EXECUTION_MODE,
        "generated": ready_count,
        "failed": failed_count,
        "adopted": False,
        "items": items,
    }
    out = root / "生产数据" / f"comic_identity_anchor_candidates_{chapter}_{batch_id}.json"
    write_json(out, manifest)
    print(f"[ok] candidate manifest: {out}", flush=True)
    print(f"[summary] generated={ready_count} failed={failed_count} adopted=0", flush=True)
    return 1 if failed_count else 0


def generate_anchors(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    registry = load_registry(root)
    assets = registry.setdefault("assets", {})
    if not isinstance(assets, dict):
        raise SystemExit("identity_registry.json assets must be an object")
    default_refs = tuple(sorted(rid for rid in assets if not rid.startswith("CHAR_")))
    refs = parse_csv(args.refs, default_refs)
    if not refs:
        raise SystemExit("no non-CHAR assets found; pass --refs REF_ID")
    if not shutil.which("codex"):
        raise SystemExit("codex not found in PATH")

    shared_dir = root / "出图" / "共享" / "图片"
    shared_dir.mkdir(parents=True, exist_ok=True)
    visual_style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    codex_backend_version = codex_version()
    requested_ratio = str(getattr(args, "ratio", "4:5") or "4:5")
    candidate_count = max(0, int(getattr(args, "candidate_count", 0) or 0))
    if candidate_count:
        return generate_anchor_candidates(
            root=root,
            repo=repo,
            registry=registry,
            refs=refs,
            chapter=args.chapter,
            candidate_count=candidate_count,
            max_attempts=args.max_attempts,
            timeout_sec=args.timeout_sec,
            ratio=requested_ratio,
            visual_style=visual_style,
            backend_version=codex_backend_version,
        )
    style_reference = project_style_anchor(root, registry)
    generated = 0
    skipped = 0
    failed = 0
    manifest_items: list[dict[str, Any]] = []

    for ref_id in refs:
        asset = assets.get(ref_id) if isinstance(assets.get(ref_id), dict) else {}
        dest = shared_dir / f"{ref_id}__anchor.png"
        if png_valid(dest) and not args.overwrite:
            source = existing_anchor_source(root, asset, dest) or {
                "kind": "existing_text_anchor",
                "chapter": args.chapter,
                "backend": CODEX_CHANNEL,
                "model": CODEX_MODEL,
            }
            source = dict(source)
            dims = png_dimensions(dest)
            if dims and target_canvas_for_ratio(dims, requested_ratio) != dims:
                pending = dest.with_name(f".{dest.stem}__ratio_pending.png")
                shutil.copy2(dest, pending)
                canvas_normalization = normalize_png_to_ratio(pending, requested_ratio)
                archived = adopt_generated_png(root, pending, dest, asset_id=ref_id, variant="anchor")
                source.update({
                    "requested_ratio": requested_ratio,
                    "canvas_normalization": canvas_normalization,
                })
                if archived:
                    source["raw_canvas_path"] = archived
                    source["raw_canvas_sha256"] = file_sha256(resolve_path(root, archived))
            register_asset_anchor(registry, root, ref_id, dest, source=source)
            skipped += 1
            manifest_items.append(
                {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "status": "reference_anchor_reused",
                    "ref_id": ref_id,
                    "path": rel_to_root(root, dest),
                    "sha256": file_sha256(dest),
                    "backend": source.get("backend", ""),
                    "model": source.get("model", ""),
                    "requested_ratio": source.get("requested_ratio", requested_ratio),
                    "canvas_normalization": source.get("canvas_normalization", {}),
                }
            )
            print(f"[skip] {ref_id}: {rel_to_root(root, dest)}", flush=True)
            continue

        use_style_reference = bool(
            style_reference
            and png_valid(style_reference)
            and ref_id != read_setting(root, "风格锚", "").strip()
            and style_reference.resolve() != dest.resolve()
        )
        prompt = asset_anchor_prompt(
            ref_id,
            asset,
            visual_style=visual_style,
            style_reference_attached=use_style_reference,
            aspect_ratio=requested_ratio,
        )
        prompt_path, prompt_sha256 = prompt_snapshot(root, args.chapter, ref_id, "anchor_codex", prompt)
        ready = False
        last_error = ""
        attempts_used = 0
        while True:
            attempt_id, attempt = begin_generation_attempt(
                root,
                args.chapter,
                generation_kind="anchor",
                asset_id=ref_id,
                variant="anchor",
                max_attempts_total=args.max_attempts,
                backend=CODEX_CHANNEL,
                model=CODEX_MODEL,
                prompt_sha256=prompt_sha256,
            )
            attempts_used = attempt
            if not attempt_id:
                last_error = f"累计尝试次数已达授权上限 {attempt}/{args.max_attempts}；未发起新的生图请求"
                break
            source = {
                "kind": "generated_text_anchor",
                "chapter": args.chapter,
                "attempt": attempt,
                "attempts_used": attempt,
                "attempts_authorized": args.max_attempts,
                "backend": CODEX_CHANNEL,
                "model": CODEX_MODEL,
                "backend_version": codex_backend_version,
                "prompt_path": prompt_path,
                "prompt_sha256": prompt_sha256,
            }
            if use_style_reference and style_reference:
                source.update(
                    {
                        "style_reference_path": rel_to_root(root, style_reference),
                        "style_reference_sha256": file_sha256(style_reference),
                        "style_reference_role": "style_only",
                    }
                )
            try:
                proc = run_codex_image(prompt, repo, args.timeout_sec, [style_reference] if use_style_reference and style_reference else [])
            except KeyboardInterrupt:
                finish_generation_attempt(root, args.chapter, attempt_id, status="interrupted", error="interrupted")
                raise
            if proc.returncode != 0:
                last_error = format_failure(proc)
                finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                print(f"[retry] {ref_id} codex attempt {attempt}/{args.max_attempts}: {last_error}", flush=True)
                continue
            candidate = dest.with_name(f".{dest.stem}__pending.png")
            candidate.unlink(missing_ok=True)
            if not decode_image_event(proc.stdout, candidate):
                last_error = "codex completed but no image_generation_end payload was available"
                finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                print(f"[retry] {ref_id} codex attempt {attempt}/{args.max_attempts}: {last_error}", flush=True)
                continue
            dims = png_dimensions(candidate)
            if dims and target_canvas_for_ratio(dims, requested_ratio) != dims:
                raw_stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
                raw = root / "出图" / "共享" / "candidates" / ref_id / "anchor" / f"{raw_stamp}__raw_canvas.png"
                raw.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(candidate, raw)
                source.update({
                    "raw_canvas_path": rel_to_root(root, raw),
                    "raw_canvas_sha256": file_sha256(raw),
                    "requested_ratio": requested_ratio,
                    "canvas_normalization": normalize_png_to_ratio(candidate, requested_ratio),
                })
            archived = adopt_generated_png(root, candidate, dest, asset_id=ref_id, variant="anchor")
            if archived:
                source["archived_previous_path"] = archived
            register_asset_anchor(registry, root, ref_id, dest, source=source)
            write_json(registry_path(root), registry)
            generated += 1
            row = {
                "ts": dt.datetime.now().isoformat(timespec="seconds"),
                "status": "reference_anchor_ready",
                "ref_id": ref_id,
                "path": rel_to_root(root, dest),
                "sha256": file_sha256(dest),
                "backend": CODEX_CHANNEL,
                "model": CODEX_MODEL,
                "backend_version": codex_backend_version,
                "attempt": attempt,
                "prompt_path": prompt_path,
                "prompt_sha256": prompt_sha256,
            }
            for key in (
                "style_reference_path",
                "style_reference_sha256",
                "style_reference_role",
                "archived_previous_path",
                "raw_canvas_path",
                "raw_canvas_sha256",
                "requested_ratio",
                "canvas_normalization",
            ):
                if source.get(key):
                    row[key] = source[key]
            manifest_items.append(row)
            append_event(root, row)
            finish_generation_attempt(
                root,
                args.chapter,
                attempt_id,
                status="succeeded",
                artifact_path=rel_to_root(root, dest),
                artifact_sha256=file_sha256(dest),
            )
            print(f"[ok] {ref_id} -> {rel_to_root(root, dest)}", flush=True)
            ready = True
            break
        if not ready:
            failed += 1
            row = {
                "ts": dt.datetime.now().isoformat(timespec="seconds"),
                "status": "reference_anchor_failed",
                "ref_id": ref_id,
                "backend": CODEX_CHANNEL,
                "model": CODEX_MODEL,
                "attempts_used": attempts_used,
                "attempts_authorized": args.max_attempts,
                "error": last_error,
            }
            manifest_items.append(row)
            append_event(root, row)
            print(f"[fail] {ref_id}: {last_error}", flush=True)

    write_json(registry_path(root), registry)
    out = root / "生产数据" / f"comic_identity_anchors_{args.chapter}.json"
    previous_manifest_archive, previous_manifest_sha256 = archive_json_before_replace(root, out)
    manifest = {
        "schema_version": 2,
        "kind": "comic_reference_anchor_generation",
        "chapter": args.chapter,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "refs": refs,
        "backend": CODEX_CHANNEL,
        "model": CODEX_MODEL,
        "execution_mode": CODEX_EXECUTION_MODE,
        "max_attempts_total": args.max_attempts,
        "attempt_ledger": rel_to_root(root, generation_attempt_ledger_path(root, args.chapter)),
        "previous_manifest_archive": previous_manifest_archive,
        "previous_manifest_sha256": previous_manifest_sha256,
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "items": manifest_items,
    }
    write_json(out, manifest)
    print(f"[ok] anchor manifest: {out}", flush=True)
    print(f"[summary] generated={generated} skipped={skipped} failed={failed}", flush=True)
    return 1 if failed else 0


def generate_front_view_candidates(
    *,
    root: Path,
    repo: Path,
    registry: dict[str, Any],
    characters: list[str],
    chapter: str,
    candidate_count: int,
    candidate_indices: list[int],
    max_attempts: int,
    timeout_sec: int,
    ratio: str,
    visual_style: str,
    style_reference: Path,
    backend_version: str,
) -> int:
    """Generate front casting candidates without registering a character view."""
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    batch_id = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    generated = 0
    failed = 0
    items: list[dict[str, Any]] = []
    style_rel = rel_to_root(root, style_reference)
    style_sha = file_sha256(style_reference)
    out = root / "生产数据" / f"comic_identity_front_candidates_{chapter}_{batch_id}.json"

    def write_batch_manifest(status: str) -> None:
        write_json(
            out,
            {
                "schema_version": 1,
                "kind": "comic_character_front_candidate_batch",
                "chapter": chapter,
                "batch_id": batch_id,
                "created_at": dt.datetime.now().isoformat(timespec="seconds"),
                "status": status,
                "characters": characters,
                "view": "front",
                "candidate_count_per_character": candidate_count,
                "ratio": ratio,
                "backend": CODEX_CHANNEL,
                "model": CODEX_MODEL,
                "style_reference_path": style_rel,
                "style_reference_sha256": style_sha,
                "style_reference_role": "style_only",
                "generated": generated,
                "failed": failed,
                "adopted": False,
                "items": items,
            },
        )

    write_batch_manifest("running")

    for character_id in characters:
        asset = assets.get(character_id) if isinstance(assets.get(character_id), dict) else {}
        notes = story_bible_character_notes(root, character_id)
        asset_contract = character_asset_contract(asset)
        for candidate_index in candidate_indices:
            prompt = character_text_anchor_prompt(
                character_id,
                notes,
                visual_style=visual_style,
                asset_contract=asset_contract,
                style_reference_attached=True,
                aspect_ratio=ratio,
            )
            prompt += (
                f"\n候选批次要求：这是 {character_id} 的第 {candidate_index}/{candidate_count} 张 front 候选；"
                "脸部与服装方案应可独立比较，但不得改变登记的年龄、阶层、角色 DNA、服装主形制或禁继承项。\n"
            )
            prompt_path, prompt_sha256 = prompt_snapshot(
                root,
                chapter,
                character_id,
                f"front_candidate_{candidate_index:02d}_codex",
                prompt,
            )
            out_dir = root / "出图" / "共享" / "candidates" / character_id / "front" / batch_id
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"candidate_{candidate_index:02d}.png"
            ready = False
            last_error = ""
            for attempt in range(1, max(1, max_attempts) + 1):
                try:
                    proc = run_codex_image(prompt, repo, timeout_sec, [style_reference])
                except KeyboardInterrupt:
                    interrupted = {
                        "ts": dt.datetime.now().isoformat(timespec="seconds"),
                        "status": "character_view_candidate_interrupted",
                        "ref_id": character_id,
                        "view": "front",
                        "candidate_index": candidate_index,
                        "candidate_count": candidate_count,
                        "attempt": attempt,
                        "ratio": ratio,
                        "backend": CODEX_CHANNEL,
                        "model": CODEX_MODEL,
                        "style_reference_path": style_rel,
                        "style_reference_sha256": style_sha,
                        "style_reference_role": "style_only",
                        "error": "interrupted",
                        "adopted": False,
                    }
                    items.append(interrupted)
                    append_event(root, interrupted)
                    write_batch_manifest("interrupted")
                    raise
                if proc.returncode != 0:
                    last_error = format_failure(proc)
                    print(
                        f"[retry] {character_id} front candidate {candidate_index}/{candidate_count} "
                        f"attempt {attempt}/{max_attempts}: {last_error}",
                        flush=True,
                    )
                    continue
                pending = out_dir / f".candidate_{candidate_index:02d}__pending.png"
                pending.unlink(missing_ok=True)
                if not decode_image_event(proc.stdout, pending) or not png_valid(pending):
                    last_error = "codex completed but no valid image_generation_end PNG was available"
                    print(
                        f"[retry] {character_id} front candidate {candidate_index}/{candidate_count} "
                        f"attempt {attempt}/{max_attempts}: {last_error}",
                        flush=True,
                    )
                    continue
                pending.replace(out_path)
                row = {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "status": "character_view_candidate_ready",
                    "ref_id": character_id,
                    "view": "front",
                    "candidate_index": candidate_index,
                    "candidate_count": candidate_count,
                    "attempt": attempt,
                    "path": rel_to_root(root, out_path),
                    "sha256": file_sha256(out_path),
                    "ratio": ratio,
                    "backend": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "backend_version": backend_version,
                    "style_reference_path": style_rel,
                    "style_reference_sha256": style_sha,
                    "style_reference_role": "style_only",
                    "prompt_path": prompt_path,
                    "prompt_sha256": prompt_sha256,
                    "adopted": False,
                }
                items.append(row)
                append_event(root, row)
                generated += 1
                ready = True
                write_batch_manifest("running")
                print(f"[ok] {character_id} front candidate {candidate_index} -> {row['path']}", flush=True)
                break
            if not ready:
                failed += 1
                row = {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "status": "character_view_candidate_failed",
                    "ref_id": character_id,
                    "view": "front",
                    "candidate_index": candidate_index,
                    "candidate_count": candidate_count,
                    "ratio": ratio,
                    "backend": CODEX_CHANNEL,
                    "model": CODEX_MODEL,
                    "style_reference_path": style_rel,
                    "style_reference_sha256": style_sha,
                    "style_reference_role": "style_only",
                    "error": last_error,
                    "adopted": False,
                }
                items.append(row)
                append_event(root, row)
                write_batch_manifest("running")
                print(f"[fail] {character_id} front candidate {candidate_index}: {last_error}", flush=True)

    write_batch_manifest("complete")
    print(f"[ok] front candidate manifest: {out}", flush=True)
    print(f"[summary] generated={generated} failed={failed} adopted=0", flush=True)
    return 1 if failed else 0


def parse_outfit_bindings(raw: str) -> list[tuple[str, str]]:
    bindings: list[tuple[str, str]] = []
    for item in str(raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise SystemExit(f"--bindings 必须是 CHAR_ID=OUTFIT_ID，当前为 {item}")
        character_id, outfit_id = (part.strip() for part in item.split("=", 1))
        if not character_id.startswith("CHAR_") or not outfit_id.startswith("OUTFIT_"):
            raise SystemExit(f"--bindings 必须是 CHAR_ID=OUTFIT_ID，当前为 {item}")
        bindings.append((character_id, outfit_id))
    if not bindings:
        raise SystemExit("至少提供一个 --bindings CHAR_ID=OUTFIT_ID")
    return bindings


def parse_expression_bindings(raw: str) -> list[tuple[str, str]]:
    bindings: list[tuple[str, str]] = []
    for item in str(raw or "").split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise SystemExit(f"--bindings 必须是 CHAR_ID=EXPR_ID，当前为 {item}")
        character_id, expression_id = (part.strip() for part in item.split("=", 1))
        if not character_id.startswith("CHAR_") or not expression_id.startswith("EXPR_"):
            raise SystemExit(f"--bindings 必须是 CHAR_ID=EXPR_ID，当前为 {item}")
        bindings.append((character_id, expression_id))
    if not bindings:
        raise SystemExit("至少提供一个 --bindings CHAR_ID=EXPR_ID")
    return bindings


def register_expression_reference(
    registry: dict[str, Any],
    root: Path,
    character_id: str,
    expression_id: str,
    path: Path,
    *,
    source: dict[str, Any],
) -> None:
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    asset = assets.get(character_id) if isinstance(assets.get(character_id), dict) else None
    if asset is None:
        raise SystemExit(f"identity_registry 未登记 {character_id}")
    expressions = asset.get("expressions") if isinstance(asset.get("expressions"), dict) else {}
    expression = expressions.get(expression_id) if isinstance(expressions.get(expression_id), dict) else None
    if expression is None:
        raise SystemExit(f"identity_registry 未登记表情 {character_id}/{expression_id}")
    dims = png_dimensions(path)
    expression["reference_images"] = [
        {
            "path": rel_to_root(root, path),
            "sha256": file_sha256(path),
            "source": source,
            "canvas": {"width": dims[0], "height": dims[1]} if dims else {},
            "updated_at": dt.datetime.now().isoformat(timespec="seconds"),
        }
    ]
    expression["status"] = "ready"


def generate_expression_references(args: argparse.Namespace) -> int:
    """以已采纳 face/front 为身份锚，生成并登记结构化表情参考图。"""
    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    registry = load_registry(root)
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    bindings = parse_expression_bindings(args.bindings)
    if args.max_attempts < 1:
        raise SystemExit("--max-attempts 必须 >= 1，且表示跨恢复运行的累计总次数")

    if args.backend == "auto":
        channel = read_setting(root, "生图渠道", "")
        backend = "dreamina" if any(token in channel.lower() for token in ("dreamina", "即梦")) else "codex"
    else:
        backend = args.backend
    tool = "dreamina" if backend == "dreamina" else "codex"
    if not shutil.which(tool):
        raise SystemExit(f"项目选定的表情锚后端 {tool} 不在 PATH；不会静默切换渠道")

    visual_style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    shared_dir = root / "出图" / "共享" / "图片"
    shared_dir.mkdir(parents=True, exist_ok=True)
    generated = skipped = failed = 0
    items: list[dict[str, Any]] = []
    model = f"Dreamina {args.model_version}" if backend == "dreamina" else CODEX_MODEL
    channel = DREAMINA_CHANNEL if backend == "dreamina" else CODEX_CHANNEL

    for character_id, expression_id in bindings:
        asset = assets.get(character_id) if isinstance(assets.get(character_id), dict) else None
        if asset is None:
            raise SystemExit(f"identity_registry 未登记 {character_id}")
        expressions = asset.get("expressions") if isinstance(asset.get("expressions"), dict) else {}
        expression = expressions.get(expression_id) if isinstance(expressions.get(expression_id), dict) else None
        if expression is None:
            raise SystemExit(f"identity_registry 未登记表情 {character_id}/{expression_id}")
        face = shared_dir / f"{character_id}__face.png"
        front = shared_dir / f"{character_id}__front.png"
        anchor = face if png_valid(face) else front
        if not png_valid(anchor):
            raise SystemExit(f"{character_id} 缺可用 face/front 身份锚")
        dest = shared_dir / f"{character_id}__{expression_id}.png"
        if png_valid(dest) and not args.overwrite:
            source = {
                "kind": "existing_expression_reference",
                "character_id": character_id,
                "expression_id": expression_id,
                "identity_anchor_path": rel_to_root(root, anchor),
            }
            register_expression_reference(registry, root, character_id, expression_id, dest, source=source)
            skipped += 1
            items.append({"status": "expression_reference_reused", "character_id": character_id,
                          "expression_id": expression_id, "path": rel_to_root(root, dest),
                          "sha256": file_sha256(dest)})
            print(f"[skip] {character_id}/{expression_id}: {rel_to_root(root, dest)}", flush=True)
            continue

        prompt = character_expression_prompt(
            character_id,
            expression_id,
            expression,
            story_bible_character_notes(root, character_id),
            visual_style=visual_style,
            asset_contract=character_asset_contract(asset),
        )
        prompt_path, prompt_sha = prompt_snapshot(
            root, args.chapter, character_id, f"expression_{expression_id}_{backend}", prompt
        )
        ready = False
        last_error = ""
        attempts_used = 0
        while True:
            attempt_id, attempt = begin_generation_attempt(
                root,
                args.chapter,
                generation_kind="expression",
                asset_id=character_id,
                variant=expression_id,
                max_attempts_total=args.max_attempts,
                backend=channel,
                model=model,
                prompt_sha256=prompt_sha,
            )
            attempts_used = attempt
            if not attempt_id:
                last_error = f"累计尝试次数已达授权上限 {attempt}/{args.max_attempts}；未发起新请求"
                break
            pending = dest.with_name(f".{dest.stem}__pending.png")
            pending.unlink(missing_ok=True)
            submit_id = ""
            if backend == "dreamina":
                ok, submit_id, last_error = run_dreamina_image(
                    prompt,
                    anchor,
                    pending,
                    timeout_sec=args.timeout_sec,
                    poll_sec=args.poll_sec,
                    model_version=args.model_version,
                    resolution_type=args.resolution_type,
                    ratio=args.ratio,
                )
                if not ok:
                    finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                    print(f"[retry] {character_id}/{expression_id} {attempt}/{args.max_attempts}: {last_error}", flush=True)
                    continue
            else:
                try:
                    proc = run_codex_image(prompt, repo, args.timeout_sec, [anchor])
                except KeyboardInterrupt:
                    finish_generation_attempt(root, args.chapter, attempt_id, status="interrupted", error="interrupted")
                    raise
                if proc.returncode != 0:
                    last_error = format_failure(proc)
                    finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                    print(f"[retry] {character_id}/{expression_id} {attempt}/{args.max_attempts}: {last_error}", flush=True)
                    continue
                if not decode_image_event(proc.stdout, pending) or not png_valid(pending):
                    last_error = "codex completed but no valid image_generation PNG was available"
                    finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                    print(f"[retry] {character_id}/{expression_id} {attempt}/{args.max_attempts}: {last_error}", flush=True)
                    continue

            source: dict[str, Any] = {
                "kind": "generated_expression_reference",
                "character_id": character_id,
                "expression_id": expression_id,
                "chapter": args.chapter,
                "attempt": attempt,
                "attempts_used": attempt,
                "attempts_authorized": args.max_attempts,
                "backend": channel,
                "model": model,
                "identity_anchor_path": rel_to_root(root, anchor),
                "identity_anchor_sha256": file_sha256(anchor),
                "prompt_path": prompt_path,
                "prompt_sha256": prompt_sha,
                "ratio": args.ratio,
            }
            if backend == "dreamina":
                source.update({"model_version": args.model_version,
                               "resolution_type": args.resolution_type, "submit_id": submit_id})
            else:
                source["backend_version"] = codex_version()
            archived = adopt_generated_png(
                root, pending, dest, asset_id=character_id, variant=f"expression/{expression_id}"
            )
            if archived:
                source["archived_previous_path"] = archived
            register_expression_reference(registry, root, character_id, expression_id, dest, source=source)
            write_json(registry_path(root), registry)
            row = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
                   "status": "expression_reference_ready", "character_id": character_id,
                   "expression_id": expression_id, "path": rel_to_root(root, dest),
                   "sha256": file_sha256(dest), **source}
            items.append(row)
            append_event(root, row)
            finish_generation_attempt(
                root, args.chapter, attempt_id, status="succeeded",
                artifact_path=rel_to_root(root, dest), artifact_sha256=file_sha256(dest)
            )
            generated += 1
            ready = True
            print(f"[ok] {character_id}/{expression_id} -> {rel_to_root(root, dest)}", flush=True)
            break
        if not ready:
            failed += 1
            row = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
                   "status": "expression_reference_failed", "character_id": character_id,
                   "expression_id": expression_id, "attempts_used": attempts_used,
                   "attempts_authorized": args.max_attempts, "backend": channel,
                   "model": model, "error": last_error}
            items.append(row)
            append_event(root, row)
            print(f"[fail] {character_id}/{expression_id}: {last_error}", flush=True)

    write_json(registry_path(root), registry)
    out = root / "生产数据" / f"comic_identity_expressions_{args.chapter}.json"
    previous_manifest_archive, previous_manifest_sha256 = archive_json_before_replace(root, out)
    manifest = {
        "schema_version": 1,
        "kind": "comic_character_expression_generation",
        "chapter": args.chapter,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "bindings": [{"character_id": cid, "expression_id": eid} for cid, eid in bindings],
        "backend": channel,
        "model": model,
        "model_version": args.model_version if backend == "dreamina" else "",
        "max_attempts_total": args.max_attempts,
        "attempt_ledger": rel_to_root(root, generation_attempt_ledger_path(root, args.chapter)),
        "previous_manifest_archive": previous_manifest_archive,
        "previous_manifest_sha256": previous_manifest_sha256,
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "items": items,
    }
    write_json(out, manifest)
    print(f"[ok] expression manifest: {out}", flush=True)
    print(f"[summary] generated={generated} skipped={skipped} failed={failed}", flush=True)
    return 1 if failed else 0


def outfit_attempts_used(manifest: dict[str, Any], character_id: str, outfit_id: str) -> int:
    """读取同一换装在旧 manifest 中已实际消耗的累计尝试次数。"""
    used = 0
    for row in manifest.get("items") or []:
        if not isinstance(row, dict):
            continue
        if row.get("character_id") != character_id or row.get("outfit_id") != outfit_id:
            continue
        values = []
        for key in ("attempts_used", "cumulative_attempt", "attempt"):
            try:
                values.append(int(row.get(key) or 0))
            except (TypeError, ValueError):
                pass
        row_used = max(values, default=0)
        if row_used == 0 and str(row.get("status") or "") in {
            "outfit_reference_failed",
            "outfit_reference_ready",
        }:
            # schema v1 没有尝试计数；每条 ready/failed 至少代表真实发起过 1 次。
            row_used = 1
        used = max(used, row_used)
    return used


def outfit_remaining_attempts(
    manifest: dict[str, Any],
    character_id: str,
    outfit_id: str,
    max_attempts_total: int,
) -> tuple[int, int]:
    used = outfit_attempts_used(manifest, character_id, outfit_id)
    return used, max(0, max_attempts_total - used)


def migrate_outfit_attempts_from_manifest(
    root: Path,
    chapter: str,
    manifest: dict[str, Any],
    character_id: str,
    outfit_id: str,
) -> int:
    """把旧版单清单中的已用次数一次性迁入不可被后续批次覆盖的总账。"""
    ledger = load_generation_attempt_ledger(root, chapter)
    existing = generation_attempts_used(ledger, "outfit", character_id, outfit_id)
    if existing:
        return existing
    legacy_used = outfit_attempts_used(manifest, character_id, outfit_id)
    if legacy_used <= 0:
        return 0
    migrated_at = dt.datetime.now().isoformat(timespec="microseconds")
    source_created_at = str(manifest.get("created_at") or migrated_at)
    for attempt in range(1, legacy_used + 1):
        ledger.setdefault("attempts", []).append(
            {
                "attempt_id": f"migrated-outfit-{character_id}-{outfit_id}-{attempt:02d}",
                "started_at": source_created_at,
                "finished_at": source_created_at,
                "status": "migrated_consumed",
                "generation_kind": "outfit",
                "asset_id": character_id,
                "variant": outfit_id,
                "cumulative_attempt": attempt,
                "max_attempts_total": int(manifest.get("max_attempts_total") or legacy_used),
                "backend": str(manifest.get("backend") or CODEX_CHANNEL),
                "model": str(manifest.get("model") or CODEX_MODEL),
                "prompt_sha256": "",
                "migration_source": "comic_identity_outfits manifest",
            }
        )
    ledger["updated_at"] = migrated_at
    write_json(generation_attempt_ledger_path(root, chapter), ledger)
    return legacy_used


def generate_outfit_references(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    if not shutil.which("codex"):
        raise SystemExit("codex not found in PATH")
    registry = load_registry(root)
    assets = registry.get("assets") if isinstance(registry.get("assets"), dict) else {}
    bindings = parse_outfit_bindings(args.bindings)
    shared_dir = root / "出图" / "共享" / "图片"
    shared_dir.mkdir(parents=True, exist_ok=True)
    visual_style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    backend_version = codex_version()
    generated = 0
    skipped = 0
    failed = 0
    items: list[dict[str, Any]] = []
    out = root / "生产数据" / f"comic_identity_outfits_{args.chapter}.json"
    try:
        previous_manifest = load_json(out) if out.is_file() else {}
    except (OSError, json.JSONDecodeError):
        previous_manifest = {}
    if not isinstance(previous_manifest, dict):
        previous_manifest = {}
    if args.max_attempts < 1:
        raise SystemExit("--max-attempts 必须 >= 1，且表示跨恢复运行的累计总次数")

    for character_id, outfit_id in bindings:
        asset = assets.get(character_id) if isinstance(assets.get(character_id), dict) else None
        if asset is None:
            raise SystemExit(f"identity_registry 未登记 {character_id}")
        outfit_contract = outfit_contract_text(asset, outfit_id)
        if not outfit_contract:
            raise SystemExit(f"identity_registry 未登记可用服装契约 {character_id}/{outfit_id}")
        front = shared_dir / f"{character_id}__front.png"
        if not png_valid(front):
            raise SystemExit(f"{character_id} 缺可用 front 身份锚：{front}")
        dest = shared_dir / f"{character_id}__{outfit_id}.png"
        if png_valid(dest) and not args.overwrite:
            source = {
                "kind": "existing_outfit_reference",
                "character_id": character_id,
                "outfit_id": outfit_id,
                "identity_anchor_path": rel_to_root(root, front),
            }
            register_outfit_reference(registry, root, character_id, outfit_id, dest, source=source)
            skipped += 1
            items.append({"status": "outfit_reference_reused", "character_id": character_id,
                          "outfit_id": outfit_id, "path": rel_to_root(root, dest), "sha256": file_sha256(dest)})
            print(f"[skip] {character_id}/{outfit_id}: {rel_to_root(root, dest)}", flush=True)
            continue

        attempts_before = migrate_outfit_attempts_from_manifest(
            root,
            args.chapter,
            previous_manifest,
            character_id,
            outfit_id,
        )
        if attempts_before >= args.max_attempts:
            failed += 1
            row = {
                "ts": dt.datetime.now().isoformat(timespec="seconds"),
                "status": "outfit_reference_attempt_budget_exhausted",
                "character_id": character_id,
                "outfit_id": outfit_id,
                "attempts_used": attempts_before,
                "attempts_authorized": args.max_attempts,
                "error": "累计尝试次数已达授权上限；未发起新的生图请求",
            }
            items.append(row)
            append_event(root, row)
            print(
                f"[block] {character_id}/{outfit_id}: attempts {attempts_before}/{args.max_attempts} exhausted",
                flush=True,
            )
            continue

        identity_contract = character_asset_contract(asset)
        prompt = outfit_reference_prompt(
            character_id,
            outfit_id,
            story_bible_character_notes(root, character_id),
            visual_style=visual_style,
            identity_contract=identity_contract,
            outfit_contract=outfit_contract,
            aspect_ratio=args.ratio,
        )
        prompt_path, prompt_sha = prompt_snapshot(
            root,
            args.chapter,
            character_id,
            f"outfit_{outfit_id}_codex",
            prompt,
        )
        ready = False
        last_error = ""
        attempts_used = attempts_before
        while True:
            attempt_id, attempt = begin_generation_attempt(
                root,
                args.chapter,
                generation_kind="outfit",
                asset_id=character_id,
                variant=outfit_id,
                max_attempts_total=args.max_attempts,
                backend=CODEX_CHANNEL,
                model=CODEX_MODEL,
                prompt_sha256=prompt_sha,
            )
            attempts_used = attempt
            if not attempt_id:
                last_error = f"累计尝试次数已达授权上限 {attempt}/{args.max_attempts}；未发起新的生图请求"
                break
            try:
                proc = run_codex_image(prompt, repo, args.timeout_sec, [front])
            except KeyboardInterrupt:
                finish_generation_attempt(root, args.chapter, attempt_id, status="interrupted", error="interrupted")
                raise
            if proc.returncode != 0:
                last_error = format_failure(proc)
                finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                print(f"[retry] {character_id}/{outfit_id} attempt {attempt}/{args.max_attempts}: {last_error}", flush=True)
                continue
            pending = dest.with_name(f".{dest.stem}__pending.png")
            pending.unlink(missing_ok=True)
            if not decode_image_event(proc.stdout, pending) or not png_valid(pending):
                last_error = "codex completed but no valid image_generation_end PNG was available"
                finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                print(f"[retry] {character_id}/{outfit_id} attempt {attempt}/{args.max_attempts}: {last_error}", flush=True)
                continue
            source: dict[str, Any] = {
                "kind": "generated_outfit_reference",
                "character_id": character_id,
                "outfit_id": outfit_id,
                "chapter": args.chapter,
                "attempt": attempt,
                "backend": CODEX_CHANNEL,
                "model": CODEX_MODEL,
                "backend_version": backend_version,
                "identity_anchor_path": rel_to_root(root, front),
                "identity_anchor_sha256": file_sha256(front),
                "prompt_path": prompt_path,
                "prompt_sha256": prompt_sha,
                "ratio": args.ratio,
                "attempts_used": attempt,
                "attempts_authorized": args.max_attempts,
            }
            target_canvas = png_dimensions(front)
            if target_canvas and png_dimensions(pending) != target_canvas:
                raw_stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
                raw = root / "出图" / "共享" / "candidates" / character_id / "outfit" / outfit_id / f"{raw_stamp}__raw_canvas.png"
                raw.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(pending, raw)
                source["raw_canvas_path"] = rel_to_root(root, raw)
                source["raw_canvas_sha256"] = file_sha256(raw)
                if normalize_full_body_canvas(pending, target_canvas):
                    source["canvas_normalization"] = {
                        "method": "contain_and_pad_no_crop",
                        "target_width": target_canvas[0],
                        "target_height": target_canvas[1],
                    }
            archived = adopt_generated_png(root, pending, dest, asset_id=character_id, variant=outfit_id)
            if archived:
                source["archived_previous_path"] = archived
            register_outfit_reference(registry, root, character_id, outfit_id, dest, source=source)
            write_json(registry_path(root), registry)
            row = {
                "ts": dt.datetime.now().isoformat(timespec="seconds"),
                "status": "outfit_reference_ready",
                "character_id": character_id,
                "outfit_id": outfit_id,
                "path": rel_to_root(root, dest),
                "sha256": file_sha256(dest),
                **source,
            }
            items.append(row)
            append_event(root, row)
            generated += 1
            ready = True
            finish_generation_attempt(
                root,
                args.chapter,
                attempt_id,
                status="succeeded",
                artifact_path=rel_to_root(root, dest),
                artifact_sha256=file_sha256(dest),
            )
            print(f"[ok] {character_id}/{outfit_id} -> {rel_to_root(root, dest)}", flush=True)
            break
        if not ready:
            failed += 1
            row = {"ts": dt.datetime.now().isoformat(timespec="seconds"),
                   "status": "outfit_reference_failed", "character_id": character_id,
                   "outfit_id": outfit_id, "attempts_used": attempts_used,
                   "attempts_authorized": args.max_attempts, "error": last_error}
            items.append(row)
            append_event(root, row)
            print(f"[fail] {character_id}/{outfit_id}: {last_error}", flush=True)

    write_json(registry_path(root), registry)
    previous_manifest_archive, previous_manifest_sha256 = archive_json_before_replace(root, out)
    manifest = {
        "schema_version": 3,
        "kind": "comic_outfit_reference_generation",
        "chapter": args.chapter,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "bindings": [{"character_id": cid, "outfit_id": oid} for cid, oid in bindings],
        "backend": CODEX_CHANNEL,
        "model": CODEX_MODEL,
        "execution_mode": CODEX_EXECUTION_MODE,
        "max_attempts_total": args.max_attempts,
        "attempt_ledger": rel_to_root(root, generation_attempt_ledger_path(root, args.chapter)),
        "previous_manifest_archive": previous_manifest_archive,
        "previous_manifest_sha256": previous_manifest_sha256,
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "items": items,
    }
    write_json(out, manifest)
    print(f"[ok] outfit manifest: {out}", flush=True)
    print(f"[summary] generated={generated} skipped={skipped} failed={failed}", flush=True)
    return 1 if failed else 0


def generate_views(args: argparse.Namespace) -> int:
    root = Path(args.project_root).expanduser().resolve()
    repo = repo_root(root)
    registry = load_registry(root)
    assets = registry.setdefault("assets", {})
    if not isinstance(assets, dict):
        raise SystemExit("identity_registry.json assets must be an object")
    characters = parse_csv(args.characters, tuple(sorted(rid for rid in assets if rid.startswith(("CHAR_", "MON_")))))
    views = parse_csv(args.views, REQUIRED_CHARACTER_VIEWS)
    unknown_views = [view for view in views if view not in REQUIRED_CHARACTER_VIEWS]
    if unknown_views:
        raise SystemExit("unknown views: " + ", ".join(unknown_views))
    if not characters:
        raise SystemExit("no CHAR_/MON_ assets found; pass --characters CHAR_ID/MON_ID")
    backend_order = ["codex", "dreamina"] if args.backend == "auto" else [args.backend]
    available: list[str] = []
    for backend in backend_order:
        tool = "codex" if backend == "codex" else "dreamina"
        if shutil.which(tool):
            available.append(backend)
        elif args.backend == backend:
            raise SystemExit(f"{tool} not found in PATH")
    if not available:
        raise SystemExit("no usable image backend found; install codex or dreamina, or pass --backend explicitly")

    shared_dir = root / "出图" / "共享" / "图片"
    shared_dir.mkdir(parents=True, exist_ok=True)
    codex_backend_version = codex_version() if "codex" in available else ""
    visual_style = read_setting(root, "基础视觉风格", "彩色国漫条漫")
    style_reference = project_style_anchor(root, registry)
    candidate_count = max(0, int(getattr(args, "candidate_count", 0) or 0))
    if candidate_count:
        if views != ["front"]:
            raise SystemExit("view candidate batches currently require --views front")
        if "codex" not in available or not args.allow_text_anchor:
            raise SystemExit("front candidate batches require --backend codex --allow-text-anchor")
        if not style_reference or not png_valid(style_reference):
            raise SystemExit("front candidate batches require an adopted STYLE_ anchor")
        raw_candidate_indices = str(getattr(args, "candidate_indices", "") or "").strip()
        if raw_candidate_indices:
            try:
                candidate_indices = [int(value.strip()) for value in raw_candidate_indices.split(",") if value.strip()]
            except ValueError as exc:
                raise SystemExit("--candidate-indices must be comma-separated positive integers") from exc
            if not candidate_indices or any(value < 1 for value in candidate_indices):
                raise SystemExit("--candidate-indices must contain positive integers")
            if len(set(candidate_indices)) != len(candidate_indices):
                raise SystemExit("--candidate-indices must not contain duplicates")
        else:
            candidate_indices = list(range(1, candidate_count + 1))
        return generate_front_view_candidates(
            root=root,
            repo=repo,
            registry=registry,
            characters=characters,
            chapter=args.chapter,
            candidate_count=candidate_count,
            candidate_indices=candidate_indices,
            max_attempts=args.max_attempts,
            timeout_sec=args.timeout_sec,
            ratio=str(args.ratio or "3:4"),
            visual_style=visual_style,
            style_reference=style_reference,
            backend_version=codex_backend_version,
        )
    generated = 0
    skipped = 0
    failed = 0
    manifest_items: list[dict[str, Any]] = []

    for character_id in characters:
        asset = assets.get(character_id) if isinstance(assets.get(character_id), dict) else {}
        notes = story_bible_character_notes(root, character_id)
        asset_contract = character_asset_contract(asset)
        for view in views:
            dest = shared_dir / f"{character_id}__{view}.png"
            anchor, anchor_kind = character_generation_anchor(
                root,
                shared_dir,
                asset,
                character_id,
                view,
                prefer_front_anchor=args.prefer_front_anchor,
            )
            if png_valid(dest) and not args.overwrite:
                preserved_source = existing_view_source(asset, view)
                anchor_rel = rel_to_root(root, anchor) if png_valid(anchor) else ""
                source = preserved_source or source_from_event(
                    latest_character_view_event(root, character_id, view),
                    anchor_path=anchor_rel,
                    anchor_kind=anchor_kind,
                    chapter=args.chapter,
                    view=view,
                )
                if not source:
                    source = {
                        "kind": "existing_character_view",
                        "anchor_path": anchor_rel,
                        "anchor_kind": anchor_kind,
                        "view": view,
                        "chapter": args.chapter,
                    }
                register_character_view(
                    registry,
                    root,
                    character_id,
                    view,
                    dest,
                    source=source,
                )
                skipped += 1
                row = {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "status": "character_view_reused",
                    "ref_id": character_id,
                    "view": view,
                    "path": rel_to_root(root, dest),
                    "sha256": file_sha256(dest),
                    "anchor_path": str(source.get("anchor_path") or anchor_rel),
                    "anchor_kind": str(source.get("anchor_kind") or anchor_kind),
                    "backend": source.get("backend", ""),
                    "model": source.get("model", ""),
                    "attempt": source.get("attempt", ""),
                }
                for key in (
                    "backend_version",
                    "model_version",
                    "resolution_type",
                    "ratio",
                    "submit_id",
                    "style_reference_path",
                    "style_reference_sha256",
                    "style_reference_role",
                    "prompt_path",
                    "prompt_sha256",
                    "archived_previous_path",
                ):
                    if source.get(key):
                        row[key] = source[key]
                manifest_items.append(row)
                print(f"[skip] {character_id} {view}: {rel_to_root(root, dest)}", flush=True)
                continue
            anchor_is_valid = png_valid(anchor)
            use_text_anchor = False
            if not anchor_is_valid:
                if view == "front" and args.allow_text_anchor and "codex" in available:
                    use_text_anchor = True
                    anchor_kind = "text_prompt_seed"
                else:
                    print(f"[fail] {character_id} {view}: anchor missing or invalid: {anchor}", flush=True)
                    failed += 1
                    manifest_items.append(
                        {
                            "ts": dt.datetime.now().isoformat(timespec="seconds"),
                            "status": "character_view_failed",
                            "ref_id": character_id,
                            "view": view,
                            "anchor_path": rel_to_root(root, anchor),
                            "backend": args.backend,
                            "error": "anchor missing or invalid",
                        }
                    )
                    continue
            anchor_rel = rel_to_root(root, anchor) if anchor_is_valid else ""
            backend_candidates = ["codex"] if use_text_anchor else available
            prompt_by_backend = {
                "codex": (
                    character_text_anchor_prompt(
                        character_id,
                        notes,
                        visual_style=visual_style,
                        asset_contract=asset_contract,
                        style_reference_attached=bool(style_reference),
                    )
                    if use_text_anchor
                    else character_view_prompt(
                        character_id,
                        view,
                        notes,
                        visual_style=visual_style,
                        asset_contract=asset_contract,
                        backend="codex",
                    )
                ),
                "dreamina": character_view_prompt(
                    character_id,
                    view,
                    notes,
                    visual_style=visual_style,
                    asset_contract=asset_contract,
                    backend="dreamina",
                ),
            }
            prompt_records = {
                backend: prompt_snapshot(
                    root,
                    args.chapter,
                    character_id,
                    f"{view}_{backend}",
                    prompt_by_backend[backend],
                )
                for backend in backend_candidates
            }
            last_error = ""
            last_backend = ""
            ready = False
            attempts_used = 0
            for _cycle in range(1, max(1, args.max_attempts) + 1):
                for backend in backend_candidates:
                    last_backend = backend
                    backend_label = CODEX_CHANNEL if backend == "codex" else DREAMINA_CHANNEL
                    model_label = CODEX_MODEL if backend == "codex" else DREAMINA_MODEL
                    attempt_id, attempt = begin_generation_attempt(
                        root,
                        args.chapter,
                        generation_kind="view",
                        asset_id=character_id,
                        variant=view,
                        max_attempts_total=args.max_attempts,
                        backend=backend_label,
                        model=model_label,
                        prompt_sha256=prompt_records[backend][1],
                    )
                    attempts_used = max(attempts_used, attempt)
                    if not attempt_id:
                        last_error = f"累计尝试次数已达授权上限 {attempt}/{args.max_attempts}；未发起新的生图请求"
                        continue
                    source: dict[str, Any] = {
                        "kind": "generated_character_view_text_seed" if use_text_anchor else "generated_character_view",
                        "anchor_path": anchor_rel,
                        "anchor_kind": anchor_kind,
                        "view": view,
                        "chapter": args.chapter,
                        "attempt": attempt,
                        "attempts_used": attempt,
                        "attempts_authorized": args.max_attempts,
                        "prompt_path": prompt_records[backend][0],
                        "prompt_sha256": prompt_records[backend][1],
                    }
                    candidate = dest.with_name(f".{dest.stem}__pending.png")
                    candidate.unlink(missing_ok=True)
                    if backend == "codex":
                        source.update({"backend": CODEX_CHANNEL, "model": CODEX_MODEL, "backend_version": codex_backend_version})
                        if use_text_anchor and style_reference:
                            source.update(
                                {
                                    "style_reference_path": rel_to_root(root, style_reference),
                                    "style_reference_sha256": file_sha256(style_reference),
                                    "style_reference_role": "style_only",
                                }
                            )
                        try:
                            proc = run_codex_image(
                                prompt_by_backend["codex"],
                                repo,
                                args.timeout_sec,
                                ([style_reference] if style_reference else []) if use_text_anchor else [anchor],
                            )
                        except KeyboardInterrupt:
                            finish_generation_attempt(root, args.chapter, attempt_id, status="interrupted", error="interrupted")
                            raise
                        if proc.returncode != 0:
                            last_error = format_failure(proc)
                            finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                            print(
                                f"[retry] {character_id} {view} codex attempt {attempt}/{args.max_attempts}: {last_error}",
                                flush=True,
                            )
                            continue
                        if not decode_image_event(proc.stdout, candidate):
                            last_error = "codex completed but no image_generation_end payload was available"
                            finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                            print(
                                f"[retry] {character_id} {view} codex attempt {attempt}/{args.max_attempts}: {last_error}",
                                flush=True,
                            )
                            continue
                    else:
                        ratio = args.face_ratio if view == "face" else args.ratio
                        if not ratio:
                            ratio = VIEW_RATIOS.get(view, "3:4")
                        ok, submit_id, error = run_dreamina_image(
                            prompt_by_backend["dreamina"],
                            anchor,
                            candidate,
                            timeout_sec=args.timeout_sec,
                            poll_sec=args.poll_sec,
                            model_version=args.model_version,
                            resolution_type=args.resolution_type,
                            ratio=ratio,
                        )
                        source.update(
                            {
                                "backend": DREAMINA_CHANNEL,
                                "model": DREAMINA_MODEL,
                                "model_version": args.model_version,
                                "resolution_type": args.resolution_type,
                                "ratio": ratio,
                                "submit_id": submit_id,
                            }
                        )
                        if not ok:
                            last_error = error
                            finish_generation_attempt(root, args.chapter, attempt_id, status="failed", error=last_error)
                            print(
                                f"[retry] {character_id} {view} dreamina attempt {attempt}/{args.max_attempts}: {last_error}",
                                flush=True,
                            )
                            continue

                    if view != "face" and view != "front":
                        front_path = shared_dir / f"{character_id}__front.png"
                        target_canvas = png_dimensions(front_path)
                        if target_canvas and png_dimensions(candidate) != target_canvas:
                            raw_stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")
                            raw_path = root / "出图" / "共享" / "candidates" / character_id / view / f"{raw_stamp}__raw_canvas.png"
                            raw_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(candidate, raw_path)
                            source["raw_canvas_path"] = rel_to_root(root, raw_path)
                            source["raw_canvas_sha256"] = file_sha256(raw_path)
                            source["raw_canvas_dimensions"] = list(png_dimensions(raw_path) or ())
                            if normalize_full_body_canvas(candidate, target_canvas):
                                source["canvas_normalization"] = {
                                    "method": "contain_and_pad_no_crop",
                                    "target_width": target_canvas[0],
                                    "target_height": target_canvas[1],
                                }

                    archived = adopt_generated_png(
                        root,
                        candidate,
                        dest,
                        asset_id=character_id,
                        variant=view,
                    )
                    if archived:
                        source["archived_previous_path"] = archived
                    register_character_view(registry, root, character_id, view, dest, source=source)
                    write_json(registry_path(root), registry)
                    generated += 1
                    row = {
                        "ts": dt.datetime.now().isoformat(timespec="seconds"),
                        "status": "character_view_ready",
                        "ref_id": character_id,
                        "view": view,
                        "path": rel_to_root(root, dest),
                        "sha256": file_sha256(dest),
                        "anchor_path": anchor_rel,
                        "anchor_kind": anchor_kind,
                        "backend": source.get("backend", ""),
                        "model": source.get("model", ""),
                        "attempt": attempt,
                    }
                    for key in (
                        "backend_version",
                        "model_version",
                        "resolution_type",
                        "ratio",
                        "submit_id",
                        "style_reference_path",
                        "style_reference_sha256",
                        "style_reference_role",
                        "prompt_path",
                        "prompt_sha256",
                        "archived_previous_path",
                        "raw_canvas_path",
                        "raw_canvas_sha256",
                        "raw_canvas_dimensions",
                        "canvas_normalization",
                    ):
                        if source.get(key):
                            row[key] = source[key]
                    manifest_items.append(row)
                    append_event(root, row)
                    finish_generation_attempt(
                        root,
                        args.chapter,
                        attempt_id,
                        status="succeeded",
                        artifact_path=rel_to_root(root, dest),
                        artifact_sha256=file_sha256(dest),
                    )
                    print(f"[ok] {character_id} {view} -> {rel_to_root(root, dest)}", flush=True)
                    ready = True
                    break
                if ready:
                    break
            if not ready:
                failed += 1
                row = {
                    "ts": dt.datetime.now().isoformat(timespec="seconds"),
                    "status": "character_view_failed",
                    "ref_id": character_id,
                    "view": view,
                    "anchor_path": anchor_rel,
                    "anchor_kind": anchor_kind,
                    "backend": last_backend or args.backend,
                    "attempts_used": attempts_used,
                    "attempts_authorized": args.max_attempts,
                    "error": last_error,
                }
                manifest_items.append(row)
                append_event(root, row)
                print(f"[fail] {character_id} {view}: {last_error}", flush=True)

    write_json(registry_path(root), registry)
    contact_sheet = write_character_view_contact_sheet(root, args.chapter, characters, views)
    out = root / "生产数据" / f"comic_identity_views_{args.chapter}.json"
    previous_manifest_archive, previous_manifest_sha256 = archive_json_before_replace(root, out)
    manifest = {
        "schema_version": 2,
        "kind": "comic_character_view_generation",
        "chapter": args.chapter,
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "characters": characters,
        "views": views,
        "backend": args.backend,
        "attempted_backends": available,
        "codex_execution_mode": CODEX_EXECUTION_MODE if "codex" in available else "",
        "max_attempts_total": args.max_attempts,
        "attempt_ledger": rel_to_root(root, generation_attempt_ledger_path(root, args.chapter)),
        "previous_manifest_archive": previous_manifest_archive,
        "previous_manifest_sha256": previous_manifest_sha256,
        "contact_sheet": contact_sheet,
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
        "items": manifest_items,
    }
    write_json(out, manifest)
    print(f"[ok] view manifest: {out}", flush=True)
    print(f"[summary] generated={generated} skipped={skipped} failed={failed}", flush=True)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画共享定妆与一致性工具")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    sub = parser.add_subparsers(dest="command", required=True)

    p_probe = sub.add_parser("probe-backend", help="执行一次不占正式资产额度的图像通道健康探针")
    p_probe.add_argument("--reason", required=True, help="本次探针原因；探针不会自动循环")
    p_probe.add_argument("--timeout-sec", type=int, default=180)
    p_probe.add_argument(
        "--probe-mode",
        choices=("auto", "text-only", "reference-attached"),
        default="auto",
        help="auto 在项目有正式风格锚时自动测试参考图附件通路",
    )
    p_probe.add_argument(
        "--probe-profile",
        choices=("simple", "production-character-front"),
        default="simple",
        help="simple 仅测轻量链路；production-character-front 校准历史人物 front 的正式复杂度和时延",
    )
    p_probe.add_argument("--external-status", default="", help="已核验的官方/外部状态摘要")
    p_probe.add_argument("--external-status-url", default="", help="外部状态来源 URL")
    p_probe.add_argument("--external-status-checked-at", default="", help="外部状态核验时间")
    p_probe.set_defaults(func=probe_backend)

    p_seed = sub.add_parser("seed", help="从面板图种共享锚点")
    p_seed.add_argument("--map", action="append", default=[], help="REF_ID=PANEL_ID_OR_PATH，可重复")
    p_seed.add_argument("--overwrite", action="store_true")
    p_seed.set_defaults(func=seed)

    p_report = sub.add_parser("report", help="生成一致性报告与重抽计划")
    p_report.add_argument("--write", action="store_true", help="回填 panel_jobs.json 中可解析的 reference path")
    p_report.set_defaults(func=report)

    p_anchors = sub.add_parser("anchors", help="生成/登记非人物共享参考锚点")
    p_anchors.add_argument("--refs", default="", help="逗号分隔 REF_ID；默认 registry 中全部非 CHAR_")
    p_anchors.add_argument("--overwrite", action="store_true", help="覆盖已有 <REF_ID>__anchor.png")
    p_anchors.add_argument(
        "--candidate-count",
        type=int,
        default=0,
        help="每个 REF_ID 生成指定数量的待审候选；候选不写入正式 registry",
    )
    p_anchors.add_argument("--ratio", default="4:5", help="Codex 候选锚点画幅；默认 4:5")
    p_anchors.add_argument("--max-attempts", type=int, default=1)
    p_anchors.add_argument("--timeout-sec", type=int, default=240)
    p_anchors.set_defaults(func=generate_anchors)

    p_adopt_anchor = sub.add_parser("adopt-anchor", help="采纳已人工选中的共享锚或角色 front 候选")
    p_adopt_anchor.add_argument("--ref", required=True, help="待采纳的 REF_ID")
    p_adopt_anchor.add_argument("--candidate", required=True, help="候选 PNG 的项目内路径")
    p_adopt_anchor.add_argument("--reviewer", required=True, help="审核人")
    p_adopt_anchor.add_argument("--role", default="", help="审核角色")
    p_adopt_anchor.add_argument("--reason", default="人工选定候选", help="采纳理由")
    p_adopt_anchor.set_defaults(func=adopt_anchor_candidate)

    p_outfits = sub.add_parser("outfits", help="基于已采纳 front 生成专门换装参考")
    p_outfits.add_argument(
        "--bindings",
        required=True,
        help="逗号分隔 CHAR_ID=OUTFIT_ID，如 CHAR_A=OUTFIT_TRAVEL",
    )
    p_outfits.add_argument("--overwrite", action="store_true", help="覆盖已有服装参考")
    p_outfits.add_argument("--ratio", default="3:4", help="服装全身参考画幅")
    p_outfits.add_argument("--max-attempts", type=int, default=1)
    p_outfits.add_argument("--timeout-sec", type=int, default=240)
    p_outfits.set_defaults(func=generate_outfit_references)

    p_expressions = sub.add_parser("expressions", help="基于已采纳 face/front 生成结构化表情锚")
    p_expressions.add_argument(
        "--bindings",
        required=True,
        help="逗号分隔 CHAR_ID=EXPR_ID，如 CHAR_A=EXPR_TERRIFIED",
    )
    p_expressions.add_argument("--backend", choices=("auto", "codex", "dreamina"), default="auto",
                               help="auto 严格沿用项目已选生图渠道，不静默切换")
    p_expressions.add_argument("--overwrite", action="store_true", help="覆盖已有表情锚，旧图自动归档")
    p_expressions.add_argument("--ratio", default="1:1", help="表情头肩锚画幅")
    p_expressions.add_argument("--max-attempts", type=int, default=1,
                               help="跨恢复运行的单表情累计尝试上限")
    p_expressions.add_argument("--timeout-sec", type=int, default=600)
    p_expressions.add_argument("--poll-sec", type=int, default=600, help="Dreamina 轮询秒数")
    p_expressions.add_argument("--model-version", default="5.0", help="Dreamina image2image 模型版本")
    p_expressions.add_argument("--resolution-type", default="2k", help="Dreamina 输出规格")
    p_expressions.set_defaults(func=generate_expression_references)

    p_views = sub.add_parser("views", help="生成/登记常驻角色专门定妆多视图")
    p_views.add_argument("--characters", default="", help="逗号分隔 CHAR_/MON_ ID；默认 registry 中全部 CHAR_+MON_（生物与角色同标准定妆）")
    p_views.add_argument("--views", default="", help="逗号分隔 view；默认 front,three_quarter,side,back,face")
    p_views.add_argument("--backend", choices=("auto", "codex", "dreamina"), default="auto", help="多视图生成后端")
    p_views.add_argument("--overwrite", action="store_true", help="覆盖已有 <CHAR_ID>__<view>.png")
    p_views.add_argument(
        "--candidate-count",
        type=int,
        default=0,
        help="每个角色生成指定数量的 front 待审候选；候选不写入正式 registry",
    )
    p_views.add_argument(
        "--candidate-indices",
        default="",
        help="仅续跑指定候选序号，如 2,3；仍以 --candidate-count 记录目标总数",
    )
    p_views.add_argument("--max-attempts", type=int, default=1)
    p_views.add_argument("--timeout-sec", type=int, default=240)
    p_views.add_argument("--poll-sec", type=int, default=180, help="Dreamina 轮询秒数")
    p_views.add_argument("--model-version", default="5.0", help="Dreamina image2image 模型版本")
    p_views.add_argument("--resolution-type", default="2k", help="Dreamina 输出规格")
    p_views.add_argument("--ratio", default="3:4", help="Dreamina 全身视图画幅")
    p_views.add_argument("--face-ratio", default="1:1", help="Dreamina 头像视图画幅")
    p_views.add_argument(
        "--prefer-front-anchor",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="非 front 视图优先使用已存在的 front 定妆图作为参考锚点",
    )
    p_views.add_argument(
        "--allow-text-anchor",
        action="store_true",
        help="无现成 anchor 时允许用文字设定生成首张 front 定妆图；仅 Codex 图像通道可用",
    )
    p_views.set_defaults(func=generate_views)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
