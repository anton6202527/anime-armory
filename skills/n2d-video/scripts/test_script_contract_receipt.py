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
    image_prompt_dir = root / "出图" / "第1集" / "prompt"
    prod.mkdir(parents=True)
    prompt_dir.mkdir(parents=True)
    image_prompt_dir.mkdir(parents=True)
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
    (image_prompt_dir / "01_分镜出图.md").write_text(text, encoding="utf-8")
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


def test_receipt_uses_scope_specific_evidence_for_image_prompts(tmp_path: Path) -> None:
    root = _write_case(tmp_path)

    data = SCR.update_receipt(root, "第1集", "出图", SCR.default_prompt("出图", "第1集"), "test", True)

    evidence = " ".join(data["scopes"][0]["evidence"])
    assert "出图 prompt" in evidence
    assert "逐镜出图 prompt" in evidence
    assert "视频 prompt" not in evidence


def test_write_atomic_does_not_reuse_shared_tmp_name(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    legacy_tmp = target.with_suffix(target.suffix + ".tmp")
    legacy_tmp.write_text("sentinel", encoding="utf-8")

    SCR.write_atomic(target, "updated")

    assert target.read_text(encoding="utf-8") == "updated"
    assert legacy_tmp.read_text(encoding="utf-8") == "sentinel"


def test_receipt_preserves_trace_fields_when_resigning_scope(tmp_path: Path) -> None:
    root = _write_case(tmp_path)
    app_path = root / "生产数据" / "script_contract_applied_第1集.json"
    existing = {
        "kind": SCR.APPLICATION_KIND,
        "episode": "第1集",
        "accepted": True,
        "source_trace_ids": ["SRC_ACTIVE"],
        "deferred_source_trace_ids": ["SRC_DEFERRED"],
        "source_trace_scope": {"episode": "第1集"},
        "scopes": [
            {
                "scope": "出视频",
                "prompt_path": "old.md",
                "prompt_sha256": "old",
                "source_trace_ids": ["SRC_ACTIVE"],
                "deferred_source_trace_ids": ["SRC_DEFERRED"],
            }
        ],
    }
    app_path.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

    data = SCR.update_receipt(root, "第1集", "出视频", SCR.default_prompt("出视频", "第1集"), "test", True)

    video_scope = next(row for row in data["scopes"] if row["scope"] == "出视频")
    assert video_scope["source_trace_ids"] == ["SRC_ACTIVE"]
    assert video_scope["deferred_source_trace_ids"] == ["SRC_DEFERRED"]
    assert video_scope["source_trace_scope"] == {"episode": "第1集"}
    assert any("source_trace_ids" in line for line in video_scope["evidence"])
