#!/usr/bin/env python3
"""Tests for script_contract_receipt.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import script_contract_receipt as SCR  # noqa: E402


def _write_case(tmp_path: Path, *, with_markers: bool = True) -> Path:
    root = tmp_path / "剧"
    prod = root / "生产数据"
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prod.mkdir(parents=True)
    prompt_dir.mkdir(parents=True)
    contract = {
        "kind": SCR.CONTRACT_KIND,
        "episode": "第1集",
        "content_hash": "stable-content",
        "required_consumption_fields": SCR.DEFAULT_FIELDS,
        "signable_fields": {
            "clip_dramatic_functions": [
                {"clip_id": "Clip_01", "dramatic_function": "提出问题", "audience_effect": "想看反击"}
            ]
        },
        "summary": {"status": "pass", "blocks": 0},
    }
    (prod / "script_quality_contract_第1集.json").write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    text = "剧本可看性合同：dramatic_function=提出问题；audience_effect=想看反击。" if with_markers else "普通视频 prompt"
    (prompt_dir / "01_clips.md").write_text(text, encoding="utf-8")
    return root


def test_receipt_records_content_hash_and_file_sha(tmp_path: Path) -> None:
    root = _write_case(tmp_path)

    data = SCR.update_receipt(root, "第1集", "出视频", SCR.default_prompt("出视频", "第1集"), "test", True)

    scope = data["scopes"][0]
    assert data["contract_content_hash"] == "stable-content"
    assert scope["contract_content_hash"] == "stable-content"
    assert data["contract_file_sha256"]
    assert scope["contract_file_sha256"] == data["contract_file_sha256"]
    assert scope["contract_sha256"] == scope["contract_file_sha256"]


def test_receipt_rejects_prompt_without_contract_markers(tmp_path: Path) -> None:
    root = _write_case(tmp_path, with_markers=False)

    with pytest.raises(SystemExit):
        SCR.update_receipt(root, "第1集", "出视频", SCR.default_prompt("出视频", "第1集"), "test", True)

    assert not (root / "生产数据" / "script_contract_applied_第1集.json").exists()
