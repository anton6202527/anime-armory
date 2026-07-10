#!/usr/bin/env python3
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate  # noqa: E402
from comic_image_prompt_compiler import compile_prompt  # noqa: E402


def jobs_payload():
    compiled = compile_prompt({
        "panel_id": "P001",
        "backend": "GPT Image 2 Codex CLI",
        "visible_facts": "主角在雨中回头看向画右",
        "style": "黑白漫画完成稿",
        "composition": "中景，主体画左",
        "text_strategy": "不生成文字或气泡",
        "negative_elements": ["文字", "水印", "额外手指"],
    })
    submit = compiled["prompt"]
    return {
        "schema_version": 2,
        "chapter": "第1话",
        "model": "GPT Image 2",
        "channel": "Codex CLI",
        "jobs": [{
            "panel_id": "P001",
            "production_contract_prompt": "完整合同",
            "production_negative_contract": "完整负向合同",
            "prompt_source_kind": "compiled_submit_prompt",
            "prompt_compiler": {key: compiled[key] for key in ("kind", "version", "profile_version", "profile", "backend", "language")},
            "submit_prompt": submit,
            "prompt": submit,
            "negative_prompt": compiled["negative_prompt"],
            "source_contract_sha256": compiled["source_contract_sha256"],
            "submit_prompt_sha256": hashlib.sha256(submit.encode("utf-8")).hexdigest(),
        }],
    }


def test_gate_accepts_compiled_contract_split():
    findings = []
    gate.check_prompt_compiler(jobs_payload(), findings)
    assert findings == []


def test_gate_blocks_submit_prompt_drift():
    jobs = jobs_payload()
    jobs["jobs"][0]["submit_prompt"] += " drift"
    findings = []
    gate.check_prompt_compiler(jobs, findings)
    assert any(item["severity"] == "block" and "hash" in item["reason"] for item in findings)
