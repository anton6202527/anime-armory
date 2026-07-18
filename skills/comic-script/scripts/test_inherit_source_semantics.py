from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("inherit_source_semantics.py")
SPEC = importlib.util.spec_from_file_location("inherit_source_semantics", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _segment(segment_id: str, excerpt: str) -> dict:
    return {
        "segment_id": segment_id,
        "source_excerpt": excerpt,
        "meaning_zh": "",
        "text_target": "",
        "ambiguities": [],
        "adaptation_decision": "待定",
        "adaptation_note": "",
    }


def test_inherit_preserves_target_contract_and_resets_decisions() -> None:
    target = {
        "chapter": "第4话",
        "chapter_contract": {"sha256": "target-sha"},
        "segments": [_segment("S001", "一"), _segment("S002", "二"), _segment("S003", "三")],
    }
    source = {
        "chapter": "第3话",
        "glossary_reviewed": True,
        "ambiguity_reviewed": True,
        "proper_noun_glossary": [{"source_term": "名"}],
        "segments": [
            {**_segment("S001", "一"), "meaning_zh": "一义"},
            {**_segment("S002", "二"), "meaning_zh": "二义"},
            {**_segment("S003", "三"), "meaning_zh": "三义"},
        ],
    }

    result = MODULE.inherit(
        target,
        source,
        consume_start=2,
        consume_end=2,
        overrides={"S002": "并入"},
    )

    assert result["chapter_contract"]["sha256"] == "target-sha"
    assert [item["meaning_zh"] for item in result["segments"]] == ["一义", "二义", "三义"]
    assert [item["adaptation_decision"] for item in result["segments"]] == ["删除", "并入", "后文带出"]
    assert result["semantic_inheritance"]["preserved_target_contract"] is True
