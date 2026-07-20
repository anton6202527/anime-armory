#!/usr/bin/env python3
"""Resolve and optionally download one camera-movement visual reference.

The structured manifest and local contact sheet are always the primary, offline
path. Animated WebPs are optional and fetched into a user cache only when their
motion cadence needs inspection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen


LINE_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_DIR = LINE_ROOT / "references" / "运镜"
MANIFEST_PATH = REFERENCE_DIR / "manifest.json"
MAX_ASSET_BYTES = 32 * 1024 * 1024
USER_AGENT = "AnimeArmory-CameraReference/1"


class CameraReferenceError(RuntimeError):
    pass


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CameraReferenceError(f"cannot read manifest {path}: {exc}") from exc
    if not isinstance(manifest.get("moves"), list):
        raise CameraReferenceError(f"manifest has no moves array: {path}")
    return manifest


def move_terms(move: dict[str, Any]) -> set[str]:
    values = [
        move.get("id"),
        move.get("name_zh"),
        move.get("name_en"),
        *(move.get("aliases_zh") or []),
        *(move.get("aliases_en") or []),
    ]
    remote = (move.get("media") or {}).get("remote") or {}
    values.extend([remote.get("filename"), Path(str(remote.get("filename") or "")).stem])
    return {str(value).strip().casefold() for value in values if str(value or "").strip()}


def resolve_move(manifest: dict[str, Any], query: str) -> dict[str, Any]:
    needle = str(query or "").strip().casefold()
    if not needle:
        raise CameraReferenceError("camera move query is empty")
    moves = [move for move in manifest["moves"] if isinstance(move, dict)]
    exact = [move for move in moves if needle in move_terms(move)]
    if len(exact) == 1:
        return exact[0]
    partial = [move for move in moves if any(needle in term for term in move_terms(move))]
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise CameraReferenceError(f"camera move not found: {query}")
    names = ", ".join(str(move.get("id") or move.get("name_zh")) for move in partial[:8])
    raise CameraReferenceError(f"camera move query is ambiguous: {query} -> {names}")


def default_cache_dir() -> Path:
    override = os.environ.get("ANIME_ARMORY_REFERENCE_CACHE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "AnimeArmory" / "reference-assets"
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
        return base / "AnimeArmory" / "Cache" / "reference-assets"
    base = Path(os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache"))
    return base / "anime-armory" / "reference-assets"


def remote_record(move: dict[str, Any]) -> dict[str, Any]:
    media = move.get("media")
    remote = media.get("remote") if isinstance(media, dict) else None
    if not isinstance(remote, dict):
        raise CameraReferenceError(f"{move.get('id')} has no remote animation")
    url = str(remote.get("url") or "").strip()
    sha256 = str(remote.get("sha256") or "").strip().lower()
    expected_bytes = remote.get("bytes")
    if not url.startswith("https://"):
        raise CameraReferenceError(f"{move.get('id')} remote URL must use HTTPS")
    if len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
        raise CameraReferenceError(f"{move.get('id')} has invalid SHA-256")
    if not isinstance(expected_bytes, int) or expected_bytes <= 0 or expected_bytes > MAX_ASSET_BYTES:
        raise CameraReferenceError(f"{move.get('id')} has invalid byte size")
    return {**remote, "url": url, "sha256": sha256, "bytes": expected_bytes}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, remote: dict[str, Any]) -> bool:
    try:
        return path.is_file() and path.stat().st_size == remote["bytes"] and sha256_file(path) == remote["sha256"]
    except OSError:
        return False


def cached_animation_path(move: dict[str, Any], cache_dir: Path | None = None) -> Path:
    remote = remote_record(move)
    root = (cache_dir or default_cache_dir()).expanduser().resolve()
    return root / "camera-moves" / f"{remote['sha256']}.webp"


def fetch_animation(
    move: dict[str, Any],
    cache_dir: Path | None = None,
    timeout: float = 60.0,
    opener: Callable[..., Any] = urlopen,
) -> tuple[Path, bool]:
    remote = remote_record(move)
    target = cached_animation_path(move, cache_dir)
    if verify_file(target, remote):
        return target, True
    if target.exists():
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)

    request = Request(remote["url"], headers={"User-Agent": USER_AGENT, "Accept": "image/webp"})
    temporary: Path | None = None
    try:
        with opener(request, timeout=timeout) as response:
            final_url = str(response.geturl())
            if not final_url.startswith("https://"):
                raise CameraReferenceError("download redirected away from HTTPS")
            header_length = response.headers.get("Content-Length")
            if header_length and int(header_length) != remote["bytes"]:
                raise CameraReferenceError(
                    f"remote byte size changed: expected {remote['bytes']}, got {header_length}"
                )
            digest = hashlib.sha256()
            received = 0
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, prefix=f".{remote['sha256']}.", suffix=".part", delete=False
            ) as handle:
                temporary = Path(handle.name)
                while chunk := response.read(1024 * 1024):
                    received += len(chunk)
                    if received > remote["bytes"] or received > MAX_ASSET_BYTES:
                        raise CameraReferenceError("download exceeded declared byte size")
                    digest.update(chunk)
                    handle.write(chunk)
        if received != remote["bytes"]:
            raise CameraReferenceError(f"download truncated: expected {remote['bytes']}, got {received}")
        if digest.hexdigest() != remote["sha256"]:
            raise CameraReferenceError("download SHA-256 mismatch")
        temporary.replace(target)
        return target, False
    except CameraReferenceError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise CameraReferenceError(f"download failed: {exc}") from exc


def local_media_path(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = (REFERENCE_DIR / text).resolve()
    try:
        path.relative_to(REFERENCE_DIR.resolve())
    except ValueError:
        return None
    return str(path) if path.is_file() else None


def move_payload(move: dict[str, Any], cache_dir: Path | None = None) -> dict[str, Any]:
    media = move.get("media") if isinstance(move.get("media"), dict) else {}
    payload = {
        "id": move.get("id"),
        "name_zh": move.get("name_zh"),
        "name_en": move.get("name_en"),
        "risk_level": move.get("risk_level"),
        "narrative_functions": move.get("narrative_functions") or [],
        "use_when": move.get("use_when"),
        "avoid_when": move.get("avoid_when"),
        "prompt_template": move.get("prompt_template"),
        "preview_path": local_media_path(media.get("preview")),
        "contact_sheet_path": local_media_path(media.get("contact_sheet")),
        "remote": media.get("remote"),
        "cached_animation_path": None,
    }
    if isinstance(media.get("remote"), dict):
        target = cached_animation_path(move, cache_dir)
        if verify_file(target, remote_record(move)):
            payload["cached_animation_path"] = str(target)
    return payload


def self_check(manifest: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    remote_count = 0
    for move in manifest["moves"]:
        if not isinstance(move, dict) or not isinstance(move.get("media"), dict):
            continue
        media = move["media"]
        if not isinstance(media.get("remote"), dict):
            continue
        remote_count += 1
        try:
            remote_record(move)
        except CameraReferenceError as exc:
            errors.append(str(exc))
        for field in ("preview", "contact_sheet"):
            if not local_media_path(media.get(field)):
                errors.append(f"{move.get('id')} local {field} is missing")
        contact = local_media_path(media.get("contact_sheet"))
        expected_contact_sha = str(media.get("contact_sheet_sha256") or "")
        if contact and expected_contact_sha and sha256_file(Path(contact)) != expected_contact_sha:
            errors.append(f"{move.get('id')} contact sheet SHA-256 mismatch")
    if remote_count != 23:
        errors.append(f"expected 23 remote animations, found {remote_count}")
    return {"ok": not errors, "remote_count": remote_count, "errors": errors}


def add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--cache-dir", type=Path, default=None)


def emit(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return
    if isinstance(value, list):
        for item in value:
            print(f"{item['id']}: {item['name_zh']} / {item['name_en']}")
        return
    for key, item in value.items():
        print(f"{key}: {item}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List structured camera moves without network access")
    add_common_flags(list_parser)

    show_parser = subparsers.add_parser("show", help="Show local visual references and cache status")
    show_parser.add_argument("move")
    add_common_flags(show_parser)

    fetch_parser = subparsers.add_parser("fetch", help="Download one animation into the verified user cache")
    fetch_parser.add_argument("move", nargs="?")
    fetch_parser.add_argument("--all", action="store_true", help="Fetch all 23 animations (normally unnecessary)")
    fetch_parser.add_argument("--timeout", type=float, default=60.0)
    add_common_flags(fetch_parser)

    check_parser = subparsers.add_parser("self-check", help="Validate manifest and offline visual fallback")
    check_parser.add_argument("--json", action="store_true")

    args = parser.parse_args()
    manifest = load_manifest()

    if args.command == "list":
        payload = [
            {"id": move.get("id"), "name_zh": move.get("name_zh"), "name_en": move.get("name_en")}
            for move in manifest["moves"]
            if isinstance(move, dict)
        ]
        emit(payload, args.json)
        return 0

    if args.command == "self-check":
        payload = self_check(manifest)
        emit(payload, args.json)
        return 0 if payload["ok"] else 1

    if args.command == "show":
        emit(move_payload(resolve_move(manifest, args.move), args.cache_dir), args.json)
        return 0

    moves = [
        move for move in manifest["moves"]
        if isinstance(move, dict) and isinstance((move.get("media") or {}).get("remote"), dict)
    ] if args.all else [resolve_move(manifest, args.move)]
    results = []
    for move in moves:
        target, reused = fetch_animation(move, args.cache_dir, args.timeout)
        payload = move_payload(move, args.cache_dir)
        payload["download_reused"] = reused
        payload["cached_animation_path"] = str(target)
        results.append(payload)
    emit(results if args.all else results[0], args.json)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CameraReferenceError as exc:
        print(f"camera reference error: {exc}", file=sys.stderr)
        print("offline fallback remains available: manifest + local contact sheet", file=sys.stderr)
        raise SystemExit(2)

