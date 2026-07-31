"""Run from this directory: python3 -m pytest test_smart_suggestions.py"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import smart_suggestions as ss


def _write_events(root: Path, lines) -> None:
    d = root / "生产数据"
    d.mkdir(parents=True, exist_ok=True)
    (d / "production_events.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_registry(root: Path, characters: dict) -> None:
    d = root / "出图" / "共享"
    d.mkdir(parents=True, exist_ok=True)
    (d / "identity_registry.json").write_text(
        json.dumps({"characters": characters}, ensure_ascii=False), encoding="utf-8"
    )


def test_no_events_file_returns_empty(tmp_path):
    assert ss.get_smart_suggestions(str(tmp_path)) == []


def test_skips_malformed_jsonl_line(tmp_path, capsys):
    # 一行坏 jsonl 不得让整个建议引擎崩掉——跳过并在 stderr 提示。
    _write_events(tmp_path, [
        '{ this is not json',
        json.dumps({"qa": {"status": "info"}, "meta": {}}),
    ])
    result = ss.get_smart_suggestions(str(tmp_path))
    assert result == []  # 没有 char/backend 的事件不产建议，但绝不抛异常
    assert "跳过 1 行" in capsys.readouterr().err


def test_mode_null_does_not_crash_and_suggests_upgrade(tmp_path):
    # identity_adapters[backend].mode 显式为 null 时，不能 None.lower() 崩掉，
    # 应归一到 reference 并给出升档建议。
    events = [
        json.dumps({"qa": {"status": "block"}, "meta": {"character_id": "CHAR_01", "backend": "kling"}})
        for _ in range(3)
    ]
    _write_events(tmp_path, events)
    _write_registry(tmp_path, {
        "CHAR_01": {"name": "小妖", "identity_adapters": {"kling": {"mode": None}}},
    })
    result = ss.get_smart_suggestions(str(tmp_path))
    assert len(result) == 1
    assert result[0]["type"] == "upgrade_identity"
    assert result[0]["character_name"] == "小妖"


def test_lora_mode_suggests_switch_backend(tmp_path):
    events = [
        json.dumps({"qa": {"status": "block"}, "meta": {"character_id": "CHAR_02", "backend": "kling"}})
        for _ in range(3)
    ]
    _write_events(tmp_path, events)
    _write_registry(tmp_path, {
        "CHAR_02": {"name": "皇后", "identity_adapters": {"kling": {"mode": "lora"}}},
    })
    result = ss.get_smart_suggestions(str(tmp_path))
    assert len(result) == 1
    assert result[0]["type"] == "switch_backend"
