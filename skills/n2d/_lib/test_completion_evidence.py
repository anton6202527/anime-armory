"""Shared builders for real, validator-backed n2d completion test evidence.

The acceptance/lineage/readiness tests exercise evidence binding rather than
media encoding itself, but their fixtures must still cross the same production
validators.  Keeping the tiny master and both completion receipts here avoids
hand-written green JSON drifting behind the production contract.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest


def write_test_master(path: Path, *, color: str = "black", duration_sec: float = 0.6) -> Path:
    """Write a tiny real H.264/AAC Rec.709, 48 kHz stereo, faststart MP4."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-nostdin", "-y", "-v", "error",
                "-f", "lavfi", "-i", f"color=c={color}:s=16x16:r=24:d={duration_sec}",
                "-f", "lavfi", "-i",
                f"sine=frequency=440:sample_rate=48000:duration={duration_sec}",
                "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited",
                "-color_primaries", "bt709", "-color_trc", "bt709",
                "-colorspace", "bt709", "-color_range", "tv",
                "-c:a", "aac", "-ar", "48000", "-ac", "2",
                "-movflags", "+faststart", str(path),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
    except FileNotFoundError:
        pytest.skip("ffmpeg unavailable")
    assert proc.returncode == 0, proc.stderr.decode("utf-8", errors="replace")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_valid_completion_receipts(
    root: Path,
    episode: str,
    master: Path,
    contract: Any,
    *,
    transaction_id: str = "completion-fixture",
) -> dict[str, Any]:
    """Create a real render recipe, MediaArtifactReceipt and watchdown receipt."""
    media = contract._media_artifact_module()
    watchdown = contract._creative_watchdown_module()
    master = master.resolve()
    master_sha = media.sha256_file(master)
    probe = media.probe_media(master)
    assert probe.get("available") is True, probe
    duration = float(probe["duration_sec"])

    recipe = root / "生产数据" / "timelines" / episode / "render_recipe.json"
    recipe_payload = {
        "kind": media.RECIPE_KIND,
        "version": media.RECIPE_VERSION,
        "episode": episode,
        "generated_at": "2026-08-20T00:00:00+00:00",
        "picture": {"duration_sec": duration},
        "ordered_sources": [
            {
                "clip": "Clip_01",
                "source_path": master.relative_to(root.resolve()).as_posix(),
                "source_sha256": master_sha,
                "edit_duration_sec": duration,
            }
        ],
        "duration_sec": duration,
    }
    hash_scope = dict(recipe_payload)
    hash_scope.pop("generated_at")
    recipe_payload["recipe_sha256"] = media.canonical_json_sha(hash_scope)
    _write_json(recipe, recipe_payload)

    loudness = media.measure_loudness(master)
    assert loudness.get("available") is True, loudness
    spec = media.default_master_spec(
        width=int(probe["video"]["width"]),
        height=int(probe["video"]["height"]),
        fps=str(probe["video"].get("fps_rational") or "24"),
        target_lufs=float(loudness["integrated_lufs"]),
    )
    receipt = media.build_receipt(
        root,
        episode,
        master,
        spec,
        recipe_path=recipe,
        transaction_id=transaction_id,
    )
    assert receipt.get("status") == "pass", receipt
    media.write_receipt(root, episode, receipt)

    watchdown_receipt = watchdown.record_watchdown(
        root,
        episode,
        master=master,
        reviewer_kind="executor_visual_audio",
        watched_duration_sec=duration,
        coverage=1.0,
        dimensions_reviewed=watchdown.DIMENSIONS,
        review_notes=("完整听看当前测试母版。",),
    )
    assert watchdown.validate_watchdown(root, episode, master)["status"] == "pass"
    return {
        "duration_sec": duration,
        "master_sha256": master_sha,
        "media_receipt": receipt,
        "watchdown_receipt": watchdown_receipt,
        "recipe_path": recipe,
    }
