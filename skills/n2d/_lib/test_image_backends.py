"""image_backends 探活 adapter 单测。

从本目录跑：
  cd skills/n2d/_lib && python3 -m pytest test_image_backends.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    mod_path = Path(__file__).with_name("image_backends.py")
    spec = importlib.util.spec_from_file_location("image_backends", mod_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


ib = _load()


def test_env_backend_missing_key_is_down():
    status, _ = ib.probe_backend("openai", env={})
    assert status == "down"


def test_env_backend_present_key_is_ok():
    status, _ = ib.probe_backend("openai", env={"OPENAI_API_KEY": "sk-x"})
    assert status == "ok"


def test_cli_ok():
    status, _ = ib.probe_backend(
        "codex", env={}, cli_runner=lambda argv, timeout: ("ok", ""))
    assert status == "ok"


def test_cli_down_can_block():
    status, detail = ib.probe_backend(
        "codex", env={}, cli_runner=lambda argv, timeout: ("down", "boom"))
    assert status == "down" and "boom" in detail


def test_cli_absent_is_unknown_not_down():
    # CLI 不在=探不了≠不可达：必须 unknown（gate 只 WARN），不能假 BLOCK
    status, _ = ib.probe_backend(
        "codex", env={}, cli_runner=lambda argv, timeout: ("unknown", "no cli"))
    assert status == "unknown"


def test_health_url_override_uses_http_and_catches_502():
    captured = {}

    def http(url, timeout):
        captured["url"] = url
        return ("down", "HTTP 502")

    status, detail = ib.probe_backend(
        "codex",
        env={"CODEX_IMAGE_BASE_URL": "http://192.168.112.83"},
        cli_runner=lambda *a, **k: ("ok", ""),  # 不该被调用
        http_runner=http,
    )
    assert status == "down" and "502" in detail
    assert captured["url"].startswith("http://192.168.112.83")


def test_none_probe_backend_is_unknown():
    status, _ = ib.probe_backend("dreamina", env={})
    assert status == "unknown"


def test_skip_flag_short_circuits_to_unknown():
    status, _ = ib.probe_backend(
        "openai", env={"N2D_SKIP_BACKEND_PROBE": "1"})  # 即使缺 key 也不 down
    assert status == "unknown"


def test_unrecognized_backend_is_unknown():
    status, _ = ib.probe_backend("某不知名后端", env={})
    assert status == "unknown"


def test_alias_normalizes_before_probe():
    # 「即梦」→ dreamina（none 探针）→ unknown
    status, _ = ib.probe_backend("即梦", env={})
    assert status == "unknown"
