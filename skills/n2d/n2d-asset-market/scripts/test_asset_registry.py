from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("asset_registry.py")
spec = importlib.util.spec_from_file_location("asset_registry", SCRIPT)
asset_registry = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(asset_registry)


def test_scan_writes_content_hash_registry_with_event_links(tmp_path: Path) -> None:
    asset = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"png")
    pdir = tmp_path / "生产数据"
    pdir.mkdir()
    (pdir / "production_events.jsonl").write_text(
        json.dumps({
            "kind": "n2d_production_event",
            "version": 1,
            "ts": "2026-06-26T00:00:00+00:00",
            "episode": "第1集",
            "stage": "image",
            "event": "generation",
            "source": "unit",
            "generation": {"asset": "出图/第1集/图片/Clip_01.png", "status": "pass"},
            "cost": {"provider": "gpt-image"},
        }, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    rows = asset_registry.scan(str(tmp_path))
    asset_registry.write_registry(str(tmp_path), rows)

    assert rows[0]["stage"] == "image"
    assert rows[0]["generation_events"][0]["provider"] == "gpt-image"
    assert (pdir / "asset_registry.jsonl").is_file()
    assert asset_registry.verify(str(tmp_path))["status"] == "pass"


def test_verify_detects_content_change(tmp_path: Path) -> None:
    asset = tmp_path / "合成" / "第1集" / "成片_第1集_zh.mp4"
    asset.parent.mkdir(parents=True)
    asset.write_bytes(b"v1")
    rows = asset_registry.scan(str(tmp_path))
    asset_registry.write_registry(str(tmp_path), rows)

    asset.write_bytes(b"v2")
    result = asset_registry.verify(str(tmp_path))

    assert result["status"] == "fail"
    assert result["issues"][0]["issue"] == "sha256_mismatch"
