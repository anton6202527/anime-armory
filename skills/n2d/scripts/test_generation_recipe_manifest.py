from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("generation_recipe_manifest.py")
spec = importlib.util.spec_from_file_location("generation_recipe_manifest", SCRIPT)
generation_recipe_manifest = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(generation_recipe_manifest)


def _event(ep: str, stage: str, asset: str) -> dict:
    return {
        "kind": "n2d_production_event",
        "version": 1,
        "ts": "2026-06-26T00:00:00+00:00",
        "episode": ep,
        "stage": stage,
        "event": "generation",
        "source": "test",
        "trace": {"trace_id": f"trace-{stage}", "span_id": "span", "idempotency_key": asset},
        "generation": {
            "asset": asset,
            "status": "pass",
            "provider": "openai",
            "model": "gpt-image-2" if stage == "image" else "seedance-2",
            "channel": "codex-cli" if stage == "image" else "dreamina-cli",
            "route_hash": "route-sha",
            "capability_evidence_id": f"{stage}-capability",
            "backend_version": "2026-06-26",
            "quality_tier": "final",
            "actual_image_inputs": ["出图/共享/图片/定妆.png"],
        },
        "meta": {
            "recipe_hash": f"recipe-{stage}",
            "prompt_sha256": f"prompt-{stage}",
            "reference_bundle_sha256": f"ref-{stage}",
            "seed_effective": False,
            "seed_support": "unsupported",
        },
    }


def _write_events(root: Path, rows: list[dict]) -> None:
    prod = root / "生产数据"
    prod.mkdir(parents=True, exist_ok=True)
    (prod / "production_events.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_generation_recipe_manifest_requires_every_final_media(tmp_path: Path) -> None:
    episode = "第1集"
    png = tmp_path / "出图" / episode / "图片" / "Clip_01.png"
    mp4 = tmp_path / "出视频" / episode / "视频" / "Clip_01.mp4"
    png.parent.mkdir(parents=True)
    mp4.parent.mkdir(parents=True)
    png.write_bytes(b"png")
    mp4.write_bytes(b"mp4")
    _write_events(tmp_path, [_event(episode, "image", f"出图/{episode}/图片/Clip_01.png")])

    payload = generation_recipe_manifest.build_manifest(tmp_path, episode)

    assert payload["status"] == "fail"
    assert any("generation_event" in item["missing_fields"] for item in payload["records"] if item["asset"].endswith(".mp4"))


def test_generation_recipe_manifest_write_check_and_hash(tmp_path: Path) -> None:
    episode = "第1集"
    png = tmp_path / "出图" / episode / "图片" / "Clip_01.png"
    mp4 = tmp_path / "出视频" / episode / "视频" / "Clip_01.mp4"
    png.parent.mkdir(parents=True)
    mp4.parent.mkdir(parents=True)
    png.write_bytes(b"png")
    mp4.write_bytes(b"mp4")
    _write_events(tmp_path, [
        _event(episode, "image", f"出图/{episode}/图片/Clip_01.png"),
        _event(episode, "video", f"出视频/{episode}/视频/Clip_01.mp4"),
    ])

    payload = generation_recipe_manifest.build_manifest(tmp_path, episode)
    generation_recipe_manifest.write_manifest(tmp_path, episode, payload)

    assert payload["status"] == "pass"
    assert generation_recipe_manifest.check_manifest(tmp_path, episode)["status"] == "pass"

    mp4.write_bytes(b"changed")
    result = generation_recipe_manifest.check_manifest(tmp_path, episode)
    assert result["status"] == "fail"
    assert any("sha256 mismatch" in item for item in result["issues"])
