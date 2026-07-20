from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).with_name("camera_reference.py")
SPEC = importlib.util.spec_from_file_location("camera_reference_under_test", MODULE_PATH)
assert SPEC and SPEC.loader
camera_reference = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(camera_reference)


class FakeResponse:
    def __init__(self, payload: bytes, url: str):
        self.payload = payload
        self.url = url
        self.offset = 0
        self.headers = {"Content-Length": str(len(payload))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def geturl(self) -> str:
        return self.url

    def read(self, size: int) -> bytes:
        chunk = self.payload[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk


def remote_move(payload: bytes) -> dict:
    digest = hashlib.sha256(payload).hexdigest()
    return {
        "id": "test_move",
        "name_zh": "测试运镜",
        "media": {
            "remote": {
                "filename": "test.webp",
                "url": f"https://assets.example.test/{digest}.webp",
                "sha256": digest,
                "bytes": len(payload),
                "content_type": "image/webp",
            }
        },
    }


def test_checked_in_manifest_has_offline_fallback_and_remote_integrity() -> None:
    result = camera_reference.self_check(camera_reference.load_manifest())
    assert result == {"ok": True, "remote_count": 23, "errors": []}


def test_resolve_move_accepts_id_and_alias() -> None:
    manifest = camera_reference.load_manifest()
    assert camera_reference.resolve_move(manifest, "dolly_in")["name_zh"] == "镜头前推"
    assert camera_reference.resolve_move(manifest, "推近")["id"] == "dolly_in"


def test_fetch_verifies_and_reuses_content_addressed_cache(tmp_path: Path) -> None:
    payload = b"small animated webp fixture"
    move = remote_move(payload)
    calls = []

    def opener(request, timeout):
        calls.append((request.full_url, timeout))
        return FakeResponse(payload, request.full_url)

    target, reused = camera_reference.fetch_animation(move, tmp_path, opener=opener)
    assert reused is False
    assert target.read_bytes() == payload
    assert target.name == f"{hashlib.sha256(payload).hexdigest()}.webp"

    second, reused = camera_reference.fetch_animation(move, tmp_path, opener=opener)
    assert second == target
    assert reused is True
    assert len(calls) == 1


def test_fetch_rejects_bad_digest_without_leaving_partial_file(tmp_path: Path) -> None:
    payload = b"actual payload"
    move = remote_move(b"different expected payload")

    def opener(request, timeout):
        return FakeResponse(payload, request.full_url)

    with pytest.raises(camera_reference.CameraReferenceError):
        camera_reference.fetch_animation(move, tmp_path, opener=opener)
    assert not list(tmp_path.rglob("*.webp"))
    assert not list(tmp_path.rglob("*.part"))

