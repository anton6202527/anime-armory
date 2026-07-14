#!/usr/bin/env python3
"""Independent meta-audit for ``n2d-review`` mode 2.

The ordinary self-audit checks that known files and detectors are present.  A
presence inventory can still certify its own blind spots, so this module asks a
different question: for each important production claim, can we trace the
complete chain

    declaration -> implementation -> invocation -> test -> counterexample

and do known adversarial mutations have an explicit guard *and* a regression
test?  Checks are static and report-only by default.  ``--run-tests`` is the
explicit opt-in that executes the minimum registered pytest nodeids and emits a
current-SHA runtime receipt; without it, test text is defined-only and
``adversarially-tested`` remains ``not_run``.  Neither path turns a heuristic
into a production BLOCK.

Fixture packs and external evidence packs are JSON, which keeps the audit
portable.  Fixture content itself is never executed; an explicit ``--run-tests``
may only execute registered pytest nodeids whose files resolve inside the repo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


LINKS = ("declaration", "implementation", "invocation", "test", "counterexample")
INTERNAL_LINKS = LINKS[:3]
ADVERSARIAL_LINKS = LINKS[3:]

SOURCE_KINDS = {
    "official",
    "regulation",
    "standard",
    "peer_reviewed",
    "first_party_measurement",
    "industry_report",
    "market_post",
    "vendor_marketing",
    "secondary",
}
CONFIDENCE_LEVELS = {"high", "medium", "low"}
ENFORCEMENT_LEVELS = {"block", "warn", "info", "none"}
HARD_GATE_SOURCE_KINDS = {
    "official",
    "regulation",
    "standard",
    "peer_reviewed",
    "first_party_measurement",
}
CALIBRATION_ARTIFACT_ROLES = {
    "protocol",
    "sample_manifest",
    "predictions",
    "ground_truth",
}
STRATIFIED_SAMPLING_METHODS = {
    "stratified_random",
    "stratified_systematic",
    "stratified_census",
}


# Machine-readable contract for live research used by mode 2.  Version 1 is a
# provenance/grounding pack only.  Version 2 can additionally carry independent
# held-out calibration rows.  A source link -- however authoritative -- never
# counts as calibration.  Keeping the implementation mapping in every evidence
# row prevents a market claim from floating around without saying which rule it
# is supposed to influence.
EXTERNAL_EVIDENCE_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "n2d review external evidence pack",
    "type": "object",
    "required": ["kind", "version", "evidence"],
    "properties": {
        "kind": {"const": "n2d_review_external_evidence"},
        "version": {"enum": [1, 2]},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "claim_id",
                    "claim",
                    "claim_type",
                    "source",
                    "checked_at",
                    "confidence",
                    "implementation_mapping",
                ],
                "properties": {
                    "claim_id": {"type": "string", "minLength": 1},
                    "claim": {"type": "string", "minLength": 1},
                    "claim_type": {
                        "enum": [
                            "deterministic_contract",
                            "capability",
                            "regulatory",
                            "quality_heuristic",
                            "market_observation",
                        ]
                    },
                    "source": {
                        "type": "object",
                        "required": ["title", "url", "kind"],
                        "properties": {
                            "title": {"type": "string", "minLength": 1},
                            "url": {"type": "string", "minLength": 1},
                            "kind": {"enum": sorted(SOURCE_KINDS)},
                        },
                    },
                    "checked_at": {"type": "string", "format": "date"},
                    "confidence": {"enum": sorted(CONFIDENCE_LEVELS)},
                    "implementation_mapping": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["path", "symbol", "enforcement", "rationale"],
                            "properties": {
                                "path": {"type": "string", "minLength": 1},
                                "symbol": {"type": "string", "minLength": 1},
                                "enforcement": {"enum": sorted(ENFORCEMENT_LEVELS)},
                                "rationale": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                },
            },
        },
        "calibrations": {
            "description": "version=2 only; independent held-out calibration contracts",
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "claim_id",
                    "calibration_id",
                    "evaluated_at",
                    "reviewer",
                    "held_out",
                    "blind_to_gate_result",
                    "protocol",
                    "ground_truth",
                    "results",
                    "artifacts",
                ],
                "properties": {
                    "claim_id": {"type": "string", "minLength": 1},
                    "calibration_id": {"type": "string", "minLength": 1},
                    "evaluated_at": {"type": "string", "format": "date-time"},
                    "reviewer": {
                        "type": "object",
                        "required": [
                            "reviewer_id",
                            "affiliation",
                            "independent_from_implementation",
                            "independent_from_sample_selection",
                            "conflict_of_interest",
                        ],
                        "properties": {
                            "reviewer_id": {"type": "string", "minLength": 1},
                            "affiliation": {"type": "string", "minLength": 1},
                            "independent_from_implementation": {"const": True},
                            "independent_from_sample_selection": {"const": True},
                            "conflict_of_interest": {"const": "none_declared"},
                        },
                    },
                    "held_out": {"const": True},
                    "blind_to_gate_result": {"const": True},
                    "protocol": {
                        "type": "object",
                        "required": [
                            "predeclared_at",
                            "thresholds",
                            "sampling",
                            "selection_locked_before_evaluation",
                        ],
                        "properties": {
                            "predeclared_at": {"type": "string", "format": "date-time"},
                            "selection_locked_before_evaluation": {"const": True},
                            "thresholds": {
                                "type": "object",
                                "required": ["max_fnr", "max_fpr"],
                                "properties": {
                                    "max_fnr": {"type": "number", "minimum": 0, "maximum": 1},
                                    "max_fpr": {"type": "number", "minimum": 0, "maximum": 1},
                                },
                            },
                            "sampling": {
                                "type": "object",
                                "required": [
                                    "method",
                                    "population_description",
                                    "population_size",
                                    "sample_size",
                                    "strata",
                                ],
                                "properties": {
                                    "method": {"enum": sorted(STRATIFIED_SAMPLING_METHODS)},
                                    "population_description": {"type": "string", "minLength": 1},
                                    "population_size": {"type": "integer", "minimum": 1},
                                    "sample_size": {"type": "integer", "minimum": 1},
                                    "strata": {
                                        "type": "array",
                                        "minItems": 2,
                                        "items": {
                                            "type": "object",
                                            "required": ["name", "sample_count", "selection_rule"],
                                            "properties": {
                                                "name": {"type": "string", "minLength": 1},
                                                "sample_count": {"type": "integer", "minimum": 1},
                                                "selection_rule": {"type": "string", "minLength": 1},
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                    "ground_truth": {
                        "type": "object",
                        "required": [
                            "adjudication_method",
                            "adjudicator_ids",
                            "disagreement_resolution",
                            "blind_to_gate_result",
                            "adjudicators_independent_from_implementation",
                        ],
                        "properties": {
                            "adjudication_method": {"type": "string", "minLength": 1},
                            "adjudicator_ids": {
                                "type": "array",
                                "minItems": 2,
                                "uniqueItems": True,
                                "items": {"type": "string", "minLength": 1},
                            },
                            "disagreement_resolution": {"type": "string", "minLength": 1},
                            "blind_to_gate_result": {"const": True},
                            "adjudicators_independent_from_implementation": {"const": True},
                        },
                    },
                    "results": {
                        "type": "object",
                        "required": ["confusion_matrix", "fnr", "fpr"],
                        "properties": {
                            "confusion_matrix": {
                                "type": "object",
                                "required": ["tp", "tn", "fp", "fn"],
                                "properties": {
                                    key: {"type": "integer", "minimum": 0}
                                    for key in ("tp", "tn", "fp", "fn")
                                },
                            },
                            "fnr": {"type": "number", "minimum": 0, "maximum": 1},
                            "fpr": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                    },
                    "artifacts": {
                        "type": "array",
                        "minItems": 4,
                        "items": {
                            "type": "object",
                            "required": ["role", "path", "sha256"],
                            "properties": {
                                "role": {"enum": sorted(CALIBRATION_ARTIFACT_ROLES)},
                                "path": {"type": "string", "minLength": 1},
                                "sha256": {"type": "string", "pattern": "^[0-9a-fA-F]{64}$"},
                            },
                        },
                    },
                },
            },
        },
    },
}


def _req(path: str, *patterns: str, glob: bool = False, mode: str = "any") -> Dict[str, Any]:
    return {"path": path, "glob": glob, "patterns": list(patterns), "mode": mode}


# These claims are deliberately narrow.  They are not a second production
# contract; they are audit hypotheses chosen because a superficial inventory
# can report green while the behaviour is still bypassable.
BUILTIN_CLAIMS: List[Dict[str, Any]] = [
    {
        "id": "character_tier_authority",
        "title": "人物档位真值不可由下游自报降档",
        "statement": "核心角色的权威档位必须与 manifest/bundle/atlas 对账，不能只信 build_tier。",
        "external_required": False,
        "links": {
            "declaration": [_req("docs/skill-design-principles.md", r"B7[^\n]*library_tier")],
            "implementation": [_req(
                "skills/n2d-review/scripts/gate_core.py",
                r"tier_(?:mismatch|conflict|authority)",
                r"(?:library_tier|authoritative_tier)[^\n]{0,240}build_tier",
                r"build_tier[^\n]{0,240}(?:library_tier|authoritative_tier)",
            )],
            "invocation": [_req(
                "skills/n2d-review/scripts/gate.py",
                r"check_identity_registry\(",
            )],
            "test": [_req(
                "skills/n2d-review/scripts/test_gate.py",
                r"def test_[^\n]*(?:tier_mismatch|tier_conflict|tier_downgrade)",
                r"library_tier[^\n]{0,240}build_tier",
                r"build_tier[^\n]{0,240}library_tier",
                r"def test_[^\n]*core[^\n]*self_report[^\n]*(?:minimal|standard)",
            )],
            "counterexample": [_req(
                "skills/n2d-review/scripts/test_gate.py",
                r"def test_[^\n]*(?:core[^\n]*(?:downgrade|self_report)|downgrade[^\n]*core|self_report(?:ed)?_tier)",
            )],
        },
    },
    {
        "id": "multiview_nested_failure",
        "title": "多视图子桶失败必须向顶层传播",
        "statement": "identity eval 的任一必需视角失败都必须被看见，不能只检查顶层 verdict。",
        "external_required": True,
        "links": {
            "declaration": [_req(
                "skills/n2d-review/SKILL.md",
                r"多视角身份包\(MVIEW\)[^\n]*(?:失败行|失败桶)[^\n]*阻断",
            )],
            "implementation": [_req(
                "skills/n2d-review/scripts/production_consistency.py",
                r"failed_buckets",
                r"bucket_(?:fail|verdict)",
                r"(?:bucket|view)[^\n]{0,200}(?:fail|failed|block)",
            )],
            "invocation": [_req(
                "skills/n2d-review/scripts/production_consistency.py",
                r"多视角身份包\(MVIEW\).*check_multiview_identity_pack",
            )],
            "test": [_req(
                "skills/n2d-review/scripts/test_production_consistency.py",
                r"def test_[^\n]*multiview",
            )],
            "counterexample": [_req(
                "skills/n2d-review/scripts/test_production_consistency.py",
                r"def test_[^\n]*multiview[^\n]*(?:bucket|view)[^\n]*(?:fail|missing_top_level)",
                r"(?:buckets|views)[^\n]{0,300}(?:fail|failed)[^\n]{0,300}(?:assert|block)",
            )],
        },
    },
    {
        "id": "turnaround_alignment_enforcement",
        "title": "文档硬闸与多视图对齐执行强度一致",
        "statement": (
            "文档称不得落档的三视图错位，必须由可复算硬证据或 hash 绑定逐视图收据闭环；"
            "低置信几何偏差本身仍按 B10 保持 WARN。"
        ),
        "external_required": True,
        "links": {
            "declaration": [_req(
                "skills/n2d-image/SKILL.md",
                r"低置信几何偏差保持 WARN[^\n]*(?:人工|收据声明)[^\n]*硬伤[^\n]*不得落档",
            )],
            "implementation": [_req(
                "skills/n2d-image/scripts/image_qc.py",
                r"HARD_LINT_CODES[\s\S]{0,1800}turnaround_misaligned",
                r"turnaround_misaligned[^\n]{0,220}[\"']level[\"']\s*:\s*[\"']block",
                r"[\"']level[\"']\s*:\s*[\"']block[\"'][^\n]{0,220}turnaround_misaligned",
                r"HARD_LINT_CODES[\s\S]{0,1800}turnaround_core_view_review_missing",
                r"turnaround_core_view_review_missing[^\n]{0,260}[\"']level[\"']\s*:\s*[\"']block",
            )],
            "invocation": [_req(
                "skills/n2d-image/scripts/image_qc.py",
                r"audit_turnaround_alignment\(root,\s*ep\)",
            )],
            "test": [_req(
                "skills/n2d-image/scripts/test_image_qc.py",
                r"def test_[^\n]*turnaround_alignment",
            )],
            "counterexample": [_req(
                "skills/n2d-image/scripts/test_image_qc.py",
                r"def test_[^\n]*turnaround[^\n]*(?:hard|block|misaligned|hash_bound_per_view_receipts|core_view_review_missing)",
                r"turnaround_misaligned[^\n]{0,500}(?:hard_blocks|block)",
                r"turnaround_core_view_review_missing[^\n]{0,500}(?:hard_blocks|block)",
            )],
        },
    },
    {
        "id": "boundary_change_application_receipt",
        "title": "变更型边界签收必须证明已应用",
        "statement": "move/merge/split/rewrite 不能只签 decision；必须有应用收据或变更后的绑定证据。",
        "external_required": False,
        "links": {
            "declaration": [_req(
                "skills/n2d-script/SKILL.md",
                r"boundary_review\.py check[^\n]*(?:指纹|签收)",
                r"实际取材优先级[^\n]*boundary_review",
            )],
            "implementation": [_req(
                "skills/n2d-script/scripts/boundary_review.py",
                r"MUTATING_DECISIONS",
                r"applied_receipt",
                r"previous_boundary_contract_sha256",
                r"new_left_raw_sha256",
                r"new_right_raw_sha256",
                r"source_mapping",
                mode="all",
            )],
            "invocation": [_req(
                "skills/n2d/run.py",
                r"boundary_review\.py",
                r"review_script",
            )],
            "test": [_req(
                "skills/n2d-script/scripts/test_boundary_review.py",
                r"def test_",
            )],
            "counterexample": [_req(
                "skills/n2d-script/scripts/test_boundary_review.py",
                r"def test_[^\n]*(?:unapplied|not_applied|missing_receipt|requires_applied_receipt|mutating_decision)",
                r"def test_[^\n]*(?:passes_only_after_new_sha_and_mapping|receipt[^\n]*binding|unchanged[^\n]*receipt)",
                r"move_boundary[\s\S]{0,600}(?:not result\[\"ok\"\]|missing.*receipt|unapplied)",
            )],
        },
    },
    {
        "id": "planned_reference_not_ready",
        "title": "planned 参考不得靠非空路径伪装 ready",
        "statement": "结构化参考只有显式 ready/registered 才可消费；planned 即使有路径也必须被拒绝。",
        "external_required": False,
        "links": {
            "declaration": [_req(
                "docs/skill-design-principles.md",
                r"B7[^\n]*planned[^\n]*(?:冒充|不得生成|不能)",
            )],
            "implementation": [_req(
                "skills/n2d-review/scripts/gate_core.py",
                r"def _identity_reference_item_ready",
                r"status[^\n]{0,180}READY_CHARACTER_MAKEUP_STATUSES",
                mode="all",
            )],
            "invocation": [_req(
                "skills/n2d-review/scripts/gate.py",
                r"check_identity_registry\(",
            )],
            "test": [_req(
                "skills/n2d-review/scripts/test_gate.py",
                r"def test_[^\n]*planned[^\n]*(?:reference|makeup)[^\n]*(?:blocked|fails)",
            )],
            "counterexample": [_req(
                "skills/n2d-review/scripts/test_gate.py",
                r"def test_identity_registry_planned_makeup_reference_is_blocked",
                r"[\"']status[\"']\s*:\s*[\"']planned[\"'][\s\S]{0,1000}(?:BLOCK|不能放行)",
            )],
        },
    },
    {
        "id": "multiview_evidence_freshness_binding",
        "title": "多视图证据必须绑定当前角色/形态/档位/视角与真实 PNG",
        "statement": (
            "核心角色多视图不能靠旧收据、同图换标签、复制同字节文件、软链/路径逃逸、"
            "普通文件伪 PNG 或单形态行复用放行；每个桶必须绑定作品根内规范相对路径、"
            "当前 registry 节点和 PNG 哈希，并按 (character_id, form) 精确消费。"
        ),
        "external_required": False,
        "links": {
            "declaration": [_req(
                "skills/n2d-review/SKILL.md",
                r"MVIEW[\s\S]{0,700}current PNG SHA[\s\S]{0,700}\(character_id,\s*form\)",
            )],
            "implementation": [
                _req(
                    "skills/n2d-review/scripts/identity_eval_pack.py",
                    r"registry_node_status",
                    r"not_valid_png_container",
                    r"duplicate_path_across_buckets",
                    r"def _resolve_project_evidence_path",
                    r"duplicate_canonical_realpath_across_buckets",
                    r"duplicate_png_sha_across_buckets",
                    r"registry_binding_fingerprint",
                    mode="all",
                ),
                _req(
                    "skills/n2d-review/scripts/production_consistency.py",
                    r"by_key\.get\(\(cid,\s*form_name\)\)",
                    r"not_valid_png_container",
                    r"duplicate_paths",
                    r"def _resolve_multiview_evidence_path",
                    r"duplicate_canonical_realpath",
                    r"duplicate_png_sha",
                    r"registry_node_status",
                    mode="all",
                ),
            ],
            "invocation": [
                _req(
                    "skills/n2d-review/scripts/gates/face.py",
                    r"def check_identity_eval_pack",
                ),
                _req(
                    "skills/n2d-review/scripts/gate.py",
                    r"check_identity_eval_pack\(root,\s*ep\)",
                ),
            ],
            "test": [_req(
                "skills/n2d-review/scripts/test_identity_eval_pack.py",
                r"def test_planned_view_cannot_reuse_a_stale_accepted_receipt",
                r"def test_plain_text_with_matching_hash_cannot_pose_as_png_evidence",
                r"def test_same_png_cannot_be_relabelled_as_multiple_views",
                r"def test_producer_duplicate_png_sha_copy_cannot_pose_as_independent_view",
                r"def test_producer_path_escape_and_absolute_registry_evidence_are_rejected",
                r"def test_consumer_duplicate_png_sha_copy_is_independently_blocked",
                r"def test_distinct_crop_pixels_from_same_master_remain_valid",
                r"def test_one_form_row_cannot_be_reused_for_another_form",
                mode="all",
            )],
            "counterexample": [_req(
                "skills/n2d-review/scripts/test_identity_eval_pack.py",
                r"registry_node_status=planned",
                r"not_valid_png_container",
                r"duplicate_path_across_buckets",
                r"duplicate_png_sha_across_buckets",
                r"registry_evidence_path_outside_project_root",
                r"CHAR_01/战损态",
                mode="all",
            )],
        },
    },
    {
        "id": "memory_anchor_per_key_consumption",
        "title": "跨集记忆锚必须逐角色形态真实消费",
        "statement": (
            "memory plan 的每个 reinject 角色/形态都必须在真实 clip 中消费；"
            "聚合计数、summary 自报或只消费其中一人不能放行。"
        ),
        "external_required": False,
        "links": {
            "declaration": [_req(
                "skills/n2d-identity/SKILL.md",
                r"load-bearing[\s\S]{0,500}逐角色/形态[\s\S]{0,500}聚合",
            )],
            "implementation": [_req(
                "skills/n2d-review/scripts/gates/contract.py",
                r"required_from_plan",
                r"consumed_from_clips",
                r"unconsumed",
                r"不得靠聚合数字",
                mode="all",
            )],
            "invocation": [_req(
                "skills/n2d-review/scripts/gate.py",
                r"check_reference_plan_applied\(root,\s*ep\)",
            )],
            "test": [_req(
                "skills/n2d-review/scripts/test_gate.py",
                r"def test_memory_anchor_gate_recomputes_each_required_character_not_aggregate_count",
            )],
            "counterexample": [_req(
                "skills/n2d-review/scripts/test_gate.py",
                r"CHAR_02/常态[\s\S]{0,2400}memory_anchor_refs_consumed[\s\S]{0,1600}CHAR_02/常态",
            )],
        },
    },
    {
        "id": "report_only_cache_artifact_liveness",
        "title": "report-only 缓存必须绑定仍存在的输出 sidecar",
        "statement": (
            "只有 pass 且至少一个输出 artifact 仍存在的 report-only 前置可以命中缓存；"
            "删除 sidecar 后必须重跑，warn 不得缓存。"
        ),
        "external_required": False,
        "links": {
            "declaration": [_req(
                "skills/n2d/SKILL.md",
                r"report-only[\s\S]{0,500}(?:sidecar|输出)[\s\S]{0,500}(?:删除|不存在)[\s\S]{0,500}重跑",
            )],
            "implementation": [_req(
                "skills/n2d/run.py",
                r"def _cache_artifact_paths",
                r"_cache_artifacts",
                r"o\.get\(\"status\"\) == \"pass\"",
                r"bool\(o\.get\(\"_cache_artifacts\"\)\)",
                mode="all",
            )],
            "invocation": [_req(
                "skills/n2d/run.py",
                r"_run_report_only_prework\([\s\S]{0,1800}expected_outputs\s*=",
            )],
            "test": [_req(
                "skills/n2d/test_run.py",
                r"def test_report_only_cache_rebuilds_deleted_output_path_sidecar",
                r"def test_report_only_warn_result_is_never_cached_even_with_artifact",
                mode="all",
            )],
            "counterexample": [_req(
                "skills/n2d/test_run.py",
                r"sidecar\.unlink\(\)[\s\S]{0,1000}read_text\(\) == \"2\"",
                r"warn-not-cached[\s\S]{0,1000}\.get\(\"warn\"\) is None",
                mode="all",
            )],
        },
    },
    {
        "id": "review_assurance_separation",
        "title": "n2d-review 不得用静态清单或权威链接给自己发校准证书",
        "statement": (
            "静态五联、对抗测试覆盖、真实运行收据、外部依据与独立留出校准必须分层报告；"
            "任何一层 complete 都不得被改写成无盲区或无偏。"
        ),
        "external_required": True,
        "links": {
            "declaration": [_req(
                "skills/n2d-review/SKILL.md",
                r"self-checked / adversarial-test-coverage / adversarially-tested / externally-grounded / externally-calibrated",
                r"不得说[“\"]无盲区/审查无偏/结果无偏",
                mode="all",
            )],
            "implementation": [_req(
                "skills/n2d-review/scripts/meta_audit.py",
                r'"adversarial_test_coverage"\s*:',
                r'"adversarially_tested"\s*:',
                r'"externally_grounded"\s*:',
                r'"externally_calibrated"\s*:',
                r'"no_blind_spot_claim_allowed"\s*:\s*False',
                mode="all",
            )],
            "invocation": [_req(
                "skills/n2d-review/scripts/self_audit.py",
                r"def check_meta_audit",
                r"run_tests=run_meta_tests",
                mode="all",
            )],
            "test": [_req(
                "skills/n2d-review/scripts/test_meta_audit.py",
                r"def test_run_tests_is_the_only_path_to_adversarially_tested_and_binds_current_sha",
                r"def test_official_mapping_is_grounding_but_never_link_only_calibration",
                r"def test_self_audit_embeds_assurance_and_disallows_zero_warn_overclaim",
                mode="all",
            )],
            "counterexample": [_req(
                "skills/n2d-review/scripts/test_meta_audit.py",
                r"link_only_v2[\s\S]{0,900}externally_calibrated[\s\S]{0,300}not_run",
                r"adversarially_tested[\s\S]{0,300}not_run",
                r"no_blind_spot_claim_allowed[\s\S]{0,120}False",
                mode="all",
            )],
        },
    },
    {
        "id": "chapter_boundary_semantic_contract",
        "title": "拆集必须覆盖全书轴并校验双侧语义边界",
        "statement": (
            "章节/字数只能提供候选；机器计划必须保留全书 source-unit 轴，"
            "边界放行同时检查上集收口与下集冷开，最终由可追溯人工签收决定。"
        ),
        "external_required": True,
        "links": {
            "declaration": [_req(
                "skills/n2d-script/SKILL.md",
                r"集 = 戏剧节拍单元[^\n]*≠ 章[^\n]*冲突[^\n]*钩子",
                r"split_plan\.json[^\n]*(?:source[-_]units?|规范化 source-unit 索引)[^\n]*boundary_candidates[^\n]*beam",
                r"双侧边界合同",
                mode="all",
            )],
            "implementation": [
                _req(
                    "skills/n2d-script/scripts/split_novel.py",
                    r"def build_source_units",
                    r"def build_boundary_candidates",
                    r"full_book_beam_search_v1",
                    mode="all",
                ),
                _req(
                    "skills/n2d-script/scripts/boundary_audit.py",
                    r"def boundary_pairs",
                    r"weak_next_opening",
                    r"上集收尾 \+ 下集开场",
                    mode="all",
                ),
            ],
            "invocation": [_req(
                "skills/n2d/run.py",
                r"boundary_audit\.py",
                r"boundary_review\.py",
                mode="all",
            )],
            "test": [
                _req(
                    "skills/n2d-script/scripts/test_split_novel.py",
                    r"def test_split_plan_v2_keeps_full_source_units_when_only_first_episode_materialized",
                    r"def test_split_plan_v3_compacts_source_axis_and_rehydrates_legacy_units",
                    r"def test_beam_optimizer_is_global_and_dictionary_is_not_a_veto",
                    mode="all",
                ),
                _req(
                    "skills/n2d-script/scripts/test_boundary_audit.py",
                    r"def test_two_sided_boundary_pair_flags_slow_next_opening",
                    r"def test_weak_next_opening_alone_enters_strict_gate",
                    mode="all",
                ),
            ],
            "counterexample": [
                _req(
                    "skills/n2d-script/scripts/test_split_novel.py",
                    r"only_first_episode_materialized[\s\S]{0,1800}source_units",
                    r"split_plan_v3_compacts_source_axis[\s\S]{0,2200}boundary_candidates",
                    mode="all",
                ),
                _req(
                    "skills/n2d-script/scripts/test_boundary_audit.py",
                    r"weak_next_opening_alone[\s\S]{0,1800}(?:strict_blockers|weak_next_opening)",
                ),
            ],
        },
    },
]


BUILTIN_PROBES: List[Dict[str, Any]] = [
    {
        "id": "tier_self_reported_downgrade",
        "class": "metamorphic",
        "description": "把核心角色的 atlas.build_tier 改成 named_minimal 后，权威档位对账仍应抓住降档。",
        "claim_id": "character_tier_authority",
        "guard": BUILTIN_CLAIMS[0]["links"]["implementation"],
        "regression": BUILTIN_CLAIMS[0]["links"]["counterexample"],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_gate.py::test_identity_registry_core_cannot_self_report_named_minimal",
            "skills/n2d-review/scripts/test_gate.py::test_identity_registry_tier_must_match_character_bundle_manifest_and_atlas",
        ],
    },
    {
        "id": "all_chain_collusive_tier_downgrade",
        "class": "adversarial",
        "description": "scope 与 character/bundle/manifest/atlas 四处同时伪低（含自报 restricted_partial）时，registry 外结构化 storyboard 出场下界仍须同时约束 identity gate 与 review MVIEW；无结构化索引的旧项目不得扫散文误报，offscreen/forbidden 不计可见出场。",
        "claim_id": "character_tier_authority",
        "guard": [
            _req(
                "skills/n2d-review/scripts/gate_core.py",
                r"def _storyboard_character_appearance_evidence",
                r"episode_count",
                mode="all",
            ),
            _req(
                "skills/n2d/_lib/n2d_const.py",
                r"observed_episode_count",
                r"independent_episode_count",
                r"restricted_partial_contract_valid",
                mode="all",
            ),
            _req(
                "skills/n2d-review/scripts/production_consistency.py",
                r"_storyboard_character_appearance_evidence",
                r"observed_episode_count",
                r"def _core_character_forms",
                mode="all",
            ),
        ],
        "regression": [
            _req(
                "skills/n2d-review/scripts/test_gate.py",
                r"def test_identity_registry_four_way_collusive_downgrade_blocked_by_storyboards",
                r"def test_storyboard_floor_rejects_collusive_restricted_partial_without_contract",
                r"def test_storyboard_tier_evidence_uses_structured_visible_ids_only",
                r"def test_identity_registry_legacy_without_structured_story_index_keeps_named_minimal",
                mode="all",
            ),
            _req(
                "skills/n2d-review/scripts/test_production_consistency.py",
                r"def test_multiview_promotes_named_minimal_seen_in_ten_structured_storyboards",
                r"def test_multiview_does_not_count_offscreen_or_forbidden_storyboard_mentions",
                mode="all",
            ),
        ],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_gate.py::test_identity_registry_four_way_collusive_downgrade_blocked_by_storyboards",
            "skills/n2d-review/scripts/test_gate.py::test_storyboard_floor_rejects_collusive_restricted_partial_without_contract",
            "skills/n2d-review/scripts/test_gate.py::test_storyboard_tier_evidence_uses_structured_visible_ids_only",
            "skills/n2d-review/scripts/test_gate.py::test_identity_registry_legacy_without_structured_story_index_keeps_named_minimal",
            "skills/n2d-review/scripts/test_production_consistency.py::test_multiview_promotes_named_minimal_seen_in_ten_structured_storyboards",
            "skills/n2d-review/scripts/test_production_consistency.py::test_multiview_does_not_count_offscreen_or_forbidden_storyboard_mentions",
        ],
    },
    {
        "id": "nested_fail_without_top_verdict",
        "class": "adversarial",
        "description": "移除 identity eval 顶层 verdict、只让必需 bucket=fail，仍应产生失败 finding。",
        "claim_id": "multiview_nested_failure",
        "guard": BUILTIN_CLAIMS[1]["links"]["implementation"],
        "regression": BUILTIN_CLAIMS[1]["links"]["counterexample"],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_production_consistency.py::test_multiview_bucket_fail_blocks_when_top_level_verdict_missing",
        ],
    },
    {
        "id": "hard_claim_warn_implementation",
        "class": "cross_artifact",
        "description": "文档称硬伤时，执行层必须有可复算硬证据或逐视图收据硬闸；不能只剩启发式 WARN。",
        "claim_id": "turnaround_alignment_enforcement",
        "guard": BUILTIN_CLAIMS[2]["links"]["implementation"],
        "regression": BUILTIN_CLAIMS[2]["links"]["counterexample"],
        "runtime_tests": [
            "skills/n2d-image/scripts/test_image_qc.py::test_core_turnaround_requires_hash_bound_per_view_receipts",
        ],
    },
    {
        "id": "signed_but_unapplied_review",
        "class": "adversarial",
        "description": "decision=move_boundary 但 raw 未改且无应用收据时必须拒绝通过。",
        "claim_id": "boundary_change_application_receipt",
        "guard": BUILTIN_CLAIMS[3]["links"]["implementation"],
        "regression": BUILTIN_CLAIMS[3]["links"]["counterexample"],
        "runtime_tests": [
            "skills/n2d-script/scripts/test_boundary_review.py::test_move_boundary_signed_but_not_applied_fails",
        ],
    },
    {
        "id": "receipt_not_bound_to_boundary_change",
        "class": "adversarial",
        "description": "伪造 status=applied 但未绑定改前合同、新左右 raw SHA 与 source mapping 时必须拒绝。",
        "claim_id": "boundary_change_application_receipt",
        "guard": BUILTIN_CLAIMS[3]["links"]["implementation"],
        "regression": [_req(
            "skills/n2d-script/scripts/test_boundary_review.py",
            r"def test_mutating_decision_passes_only_after_new_sha_and_mapping_receipt",
            r"previous_boundary_contract_sha256",
            r"new_left_raw_sha256",
            r"new_right_raw_sha256",
            r"source_mapping",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-script/scripts/test_boundary_review.py::test_mutating_decision_passes_only_after_new_sha_and_mapping_receipt",
        ],
    },
    {
        "id": "planned_path_truthiness",
        "class": "adversarial",
        "description": "参考项有非空 path 但 status=planned 时，不能因 dict/path truthy 被当成 ready。",
        "claim_id": "planned_reference_not_ready",
        "guard": BUILTIN_CLAIMS[4]["links"]["implementation"],
        "regression": BUILTIN_CLAIMS[4]["links"]["counterexample"],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_gate.py::test_identity_registry_planned_makeup_reference_is_blocked",
        ],
    },
    {
        "id": "planned_receipt_resurrection",
        "class": "adversarial",
        "description": "registry 节点已回退 planned 时，残留 accepted/pass 旧收据不能复活该视角。",
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [_req(
            "skills/n2d-review/scripts/identity_eval_pack.py",
            r"node_status not in \{\"ready\", \"registered\"\}",
            r"registry_node_status",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_identity_eval_pack.py",
            r"def test_planned_view_cannot_reuse_a_stale_accepted_receipt",
            r"registry_node_status=planned",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_planned_view_cannot_reuse_a_stale_accepted_receipt",
        ],
    },
    {
        "id": "non_png_hash_spoof",
        "class": "adversarial",
        "description": "普通文本即使哈希与收据一致，也不能冒充多视图 PNG 证据。",
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [_req(
            "skills/n2d-review/scripts/identity_eval_pack.py",
            r"def _png_container_errors",
            r"not_valid_png_container",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_identity_eval_pack.py",
            r"def test_plain_text_with_matching_hash_cannot_pose_as_png_evidence",
            r"not_valid_png_container",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_plain_text_with_matching_hash_cannot_pose_as_png_evidence",
        ],
    },
    {
        "id": "forged_png_shell",
        "class": "adversarial",
        "description": "只有 PNG 签名/IHDR/IEND 的空壳即使 CRC 与哈希自洽，也不能冒充可审像素。",
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [_req(
            "skills/n2d-review/scripts/image_evidence.py",
            r"png_iend_invalid",
            r"zlib\.decompressobj",
            r"png_scanline_data_incomplete",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_identity_eval_pack.py",
            r"def test_forged_png_header_shell_with_matching_hash_cannot_pose_as_pixels",
            r"png_iend_invalid",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_forged_png_header_shell_with_matching_hash_cannot_pose_as_pixels",
        ],
    },
    {
        "id": "forged_human_metadata",
        "class": "adversarial",
        "description": "攻击者同时手改 registry 与 pack 时，consumer 仍须独立拒绝自动 reviewer、无时区、缺 criteria 和缺当前像素确认。",
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [_req(
            "skills/n2d-review/scripts/production_consistency.py",
            r"reviewer_appears_automated",
            r"criteria_incomplete",
            r"explicit_current_pixels_confirmation_missing",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_identity_eval_pack.py",
            r"def test_consumer_independently_rejects_forged_human_metadata",
            r"reviewed_at_timezone_missing",
            r"explicit_current_pixels_confirmation_missing",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_consumer_independently_rejects_forged_human_metadata",
        ],
    },
    {
        "id": "same_image_multiangle_alias",
        "class": "adversarial",
        "description": "同一 PNG 路径不能换 front/side/back 标签后重复充当多个独立视角。",
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [_req(
            "skills/n2d-review/scripts/identity_eval_pack.py",
            r"duplicate_path_across_buckets",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_identity_eval_pack.py",
            r"def test_same_png_cannot_be_relabelled_as_multiple_views",
            r"duplicate_path_across_buckets",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_same_png_cannot_be_relabelled_as_multiple_views",
        ],
    },
    {
        "id": "copied_or_symlinked_pixel_alias",
        "class": "adversarial",
        "description": (
            "把同一 PNG 复制到不同文件名或用软链别名伪装多角度时，producer 与 consumer "
            "必须按 canonical realpath/current SHA 双重阻断；同源但像素不同的真实裁切仍可通过。"
        ),
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [
            _req(
                "skills/n2d-review/scripts/identity_eval_pack.py",
                r"duplicate_canonical_realpath_across_buckets",
                r"duplicate_png_sha_across_buckets",
                mode="all",
            ),
            _req(
                "skills/n2d-review/scripts/production_consistency.py",
                r"duplicate_canonical_realpath",
                r"duplicate_png_sha",
                mode="all",
            ),
        ],
        "regression": [_req(
            "skills/n2d-review/scripts/test_identity_eval_pack.py",
            r"def test_producer_duplicate_png_sha_copy_cannot_pose_as_independent_view",
            r"def test_producer_symlink_alias_uses_canonical_realpath_and_is_blocked",
            r"def test_consumer_duplicate_png_sha_copy_is_independently_blocked",
            r"def test_consumer_symlink_alias_is_independently_blocked",
            r"def test_distinct_crop_pixels_from_same_master_remain_valid",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_producer_duplicate_png_sha_copy_cannot_pose_as_independent_view",
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_producer_symlink_alias_uses_canonical_realpath_and_is_blocked",
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_consumer_duplicate_png_sha_copy_is_independently_blocked",
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_consumer_symlink_alias_is_independently_blocked",
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_distinct_crop_pixels_from_same_master_remain_valid",
        ],
    },
    {
        "id": "reencoded_same_pixels_alias",
        "class": "adversarial",
        "description": (
            "同一解码像素即使改变 PNG 压缩、filter 或 metadata 导致文件 SHA 不同，"
            "也不能伪装成独立角度；producer 与 consumer 必须在统一 RGBA 像素域独立复算。"
        ),
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [
            _req(
                "skills/n2d-review/scripts/image_evidence.py",
                r"PNG_DECODED_PIXEL_FINGERPRINT_KIND",
                r"def png_decoded_pixel_fingerprint",
                r"RGBA16",
                mode="all",
            ),
            _req(
                "skills/n2d-review/scripts/identity_eval_pack.py",
                r"duplicate_decoded_pixel_fingerprint_across_buckets",
            ),
            _req(
                "skills/n2d-review/scripts/production_consistency.py",
                r"duplicate_decoded_pixel_fingerprint",
            ),
        ],
        "regression": [
            _req(
                "skills/n2d-review/scripts/test_image_evidence.py",
                r"def test_decoded_pixel_fingerprint_ignores_compression_filter_and_metadata",
                r"def test_adam7_and_noninterlaced_encodings_share_pixel_fingerprint",
                mode="all",
            ),
            _req(
                "skills/n2d-review/scripts/test_identity_eval_pack.py",
                r"def test_producer_reencoded_same_pixels_are_blocked_by_decoded_fingerprint",
                r"def test_consumer_reencoded_same_pixels_are_independently_blocked",
                mode="all",
            ),
        ],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_image_evidence.py::test_decoded_pixel_fingerprint_ignores_compression_filter_and_metadata",
            "skills/n2d-review/scripts/test_image_evidence.py::test_adam7_and_noninterlaced_encodings_share_pixel_fingerprint",
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_producer_reencoded_same_pixels_are_blocked_by_decoded_fingerprint",
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_consumer_reencoded_same_pixels_are_independently_blocked",
        ],
    },
    {
        "id": "multiview_evidence_path_escape",
        "class": "adversarial",
        "description": (
            "绝对路径、.. 越界、软链解析出作品根或非规范别名不能作为 load-bearing 多视图证据，"
            "producer 与 consumer 必须各自复算。"
        ),
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [
            _req(
                "skills/n2d-review/scripts/identity_eval_pack.py",
                r"def _resolve_project_evidence_path",
                r"absolute_registry_evidence_path_not_allowed",
                r"registry_evidence_path_outside_project_root",
                mode="all",
            ),
            _req(
                "skills/n2d-review/scripts/production_consistency.py",
                r"def _resolve_multiview_evidence_path",
                r"absolute_path_not_allowed",
                r"path_outside_project_root",
                mode="all",
            ),
        ],
        "regression": [_req(
            "skills/n2d-review/scripts/test_identity_eval_pack.py",
            r"def test_producer_path_escape_and_absolute_registry_evidence_are_rejected",
            r"def test_consumer_path_escape_and_absolute_registry_path_are_independently_blocked",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_producer_path_escape_and_absolute_registry_evidence_are_rejected",
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_consumer_path_escape_and_absolute_registry_path_are_independently_blocked",
        ],
    },
    {
        "id": "pre_spend_registry_alias_bypass",
        "class": "cross_artifact",
        "description": (
            "即使 review pack 被手改，legacy signer/finalizer 与真正付费前 shared-first runner "
            "也必须独立拒绝路径逃逸、软链/非规范别名和复制同 SHA 的伪多视图。"
        ),
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [
            _req(
                "skills/n2d-image/scripts/image_qc.py",
                r"def _resolve_core_registry_image_path",
                r"def _core_form_path_uniqueness_issues",
                r"duplicate_png_sha_across_buckets",
                mode="all",
            ),
            _req(
                "skills/n2d-image/scripts/codex_image_runner.py",
                r"def _resolve_registry_image_path",
                r"duplicate_canonical_realpath",
                r"duplicate_png_sha",
                mode="all",
            ),
        ],
        "regression": [
            _req(
                "skills/n2d-image/scripts/test_image_qc.py",
                r"def test_legacy_signer_path_escape_symlink_and_noncanonical_are_rejected",
                r"def test_legacy_finalize_consumer_duplicate_png_sha_is_independently_blocked",
                mode="all",
            ),
            _req(
                "skills/n2d-image/scripts/test_codex_image_runner.py",
                r"def test_shared_first_pre_spend_duplicate_png_sha_blocks_copied_views",
                r"def test_shared_first_pre_spend_path_escape_symlink_and_noncanonical_are_blocked",
                mode="all",
            ),
        ],
        "runtime_tests": [
            "skills/n2d-image/scripts/test_image_qc.py::test_legacy_signer_path_escape_symlink_and_noncanonical_are_rejected",
            "skills/n2d-image/scripts/test_image_qc.py::test_legacy_finalize_consumer_duplicate_png_sha_is_independently_blocked",
            "skills/n2d-image/scripts/test_codex_image_runner.py::test_shared_first_pre_spend_duplicate_png_sha_blocks_copied_views",
            "skills/n2d-image/scripts/test_codex_image_runner.py::test_shared_first_pre_spend_path_escape_symlink_and_noncanonical_are_blocked",
        ],
    },
    {
        "id": "multiform_row_reuse",
        "class": "adversarial",
        "description": "同一角色的常态验收行不能回退复用给战损态等另一形态。",
        "claim_id": "multiview_evidence_freshness_binding",
        "guard": [_req(
            "skills/n2d-review/scripts/production_consistency.py",
            r"by_key\.get\(\(cid,\s*form_name\)\)",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_identity_eval_pack.py",
            r"def test_one_form_row_cannot_be_reused_for_another_form",
            r"CHAR_01/战损态",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_identity_eval_pack.py::test_one_form_row_cannot_be_reused_for_another_form",
        ],
    },
    {
        "id": "memory_aggregate_false_positive",
        "class": "adversarial",
        "description": "required=2 但仅一名角色在真实 clip 消费时，聚合字段不能制造假通过。",
        "claim_id": "memory_anchor_per_key_consumption",
        "guard": [_req(
            "skills/n2d-review/scripts/gates/contract.py",
            r"required_from_plan",
            r"consumed_from_clips",
            r"unconsumed",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_gate.py",
            r"def test_memory_anchor_gate_recomputes_each_required_character_not_aggregate_count",
            r"CHAR_02/常态",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_gate.py::test_memory_anchor_gate_recomputes_each_required_character_not_aggregate_count",
        ],
    },
    {
        "id": "core_partial_self_downgrade",
        "class": "metamorphic",
        "description": "核心角色仅自报 restricted_partial/no_full_face 且无 approved 合同时仍必须回到 core_full。",
        "claim_id": "character_tier_authority",
        "guard": [_req(
            "skills/n2d/_lib/n2d_const.py",
            r"def restricted_partial_contract_valid",
            r"restricted_partial_contract_valid\(record\)",
            r"group_or_crowd",
            r"inferred == CHARACTER_LIBRARY_TIER_MINIMAL",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d/_lib/test_character_library_contract.py",
            r"def test_core_cannot_self_report_restricted_partial_without_approved_contract",
            r"def test_one_off_partial_is_compatible_but_recurring_cannot_bypass_without_contract",
            r"== CHARACTER_LIBRARY_TIER_CORE",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d/_lib/test_character_library_contract.py::test_core_cannot_self_report_restricted_partial_without_approved_contract",
            "skills/n2d/_lib/test_character_library_contract.py::test_one_off_partial_is_compatible_but_recurring_cannot_bypass_without_contract",
        ],
    },
    {
        "id": "deleted_sidecar_cache_deadlock",
        "class": "adversarial",
        "description": "缓存命中后若输出 sidecar 被删除，前置必须失效并重跑，不能永久跳过重建。",
        "claim_id": "report_only_cache_artifact_liveness",
        "guard": [_req(
            "skills/n2d/run.py",
            r"def _cache_artifact_paths",
            r"_cache_artifacts",
            r"bool\(o\.get\(\"_cache_artifacts\"\)\)",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d/test_run.py",
            r"def test_report_only_cache_rebuilds_deleted_output_path_sidecar",
            r"sidecar\.unlink\(\)",
            r"read_text\(\) == \"2\"",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d/test_run.py::test_report_only_cache_rebuilds_deleted_output_path_sidecar",
            "skills/n2d/test_run.py::test_report_only_warn_result_is_never_cached_even_with_artifact",
        ],
    },
    {
        "id": "structured_warn_exit_zero_cache",
        "class": "adversarial",
        "description": (
            "report-only 子脚本即使 exit=0，只要结构化 JSON status=warn，"
            "就不得借旧 sidecar 被缓存成 pass。"
        ),
        "claim_id": "report_only_cache_artifact_liveness",
        "guard": [_req(
            "skills/n2d/run.py",
            r"def _script_result_status",
            r"detected_status\s*=\s*_script_result_status",
            r"report_status\s*=\s*[\"']pass[\"']\s*if\s*detected_status\s*==\s*[\"']pass[\"']\s*else\s*[\"']warn[\"']",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d/test_run.py",
            r"def test_report_only_exit_zero_with_structured_warn_is_not_cached",
        )],
        "runtime_tests": [
            "skills/n2d/test_run.py::test_report_only_exit_zero_with_structured_warn_is_not_cached",
        ],
    },
    {
        "id": "stale_report_resurrection",
        "class": "adversarial",
        "description": (
            "memory-anchor 本轮 unavailable/warn 时必须覆写旧 ready plan，"
            "不能因 report-only exit=0 留下昨天的可消费证据。"
        ),
        "claim_id": "report_only_cache_artifact_liveness",
        "guard": [_req(
            "skills/n2d-identity/scripts/memory_anchor.py",
            r"status[\"']?\s*:\s*[\"']warn[\"']",
            r"if not ns\.no_write:\s*[\s\S]{0,180}write_plan",
            r"Always replace an older plan",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d-identity/scripts/test_memory_anchor.py",
            r"def test_cli_overwrites_stale_ready_plan_with_explicit_unavailable_plan",
            r"current\[\"available\"\] is False",
            r"current\[\"status\"\] == \"warn\"",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-identity/scripts/test_memory_anchor.py::test_cli_overwrites_stale_ready_plan_with_explicit_unavailable_plan",
        ],
    },
    {
        "id": "static_test_text_self_certification",
        "class": "adversarial",
        "description": "测试函数名存在只能算 defined-only；未显式执行 pytest 时 adversarially-tested 必须保持 not_run。",
        "claim_id": "review_assurance_separation",
        "guard": [_req(
            "skills/n2d-review/scripts/meta_audit.py",
            r"def run_registered_adversarial_tests",
            r"if not requested",
            r'"status"\s*:\s*"not_run"',
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_meta_audit.py",
            r"def test_run_tests_is_the_only_path_to_adversarially_tested_and_binds_current_sha",
            r"adversarially_tested[\s\S]{0,300}not_run",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_meta_audit.py::test_run_tests_is_the_only_path_to_adversarially_tested_and_binds_current_sha",
        ],
    },
    {
        "id": "stdout_only_assurance_receipt_loss",
        "class": "cross_artifact",
        "description": (
            "正式验收不能只靠瞬时 stdout 或退出码；meta/self 必须能把同一份完整 JSON 原子落档，"
            "且落档不得篡改各自原有退出码语义。"
        ),
        "claim_id": "review_assurance_separation",
        "guard": [
            _req(
                "skills/n2d-review/scripts/meta_audit.py",
                r"def _atomic_write_text",
                r"os\.fsync",
                r"os\.replace",
                r"add_argument\(\"--out\"",
                mode="all",
            ),
            _req(
                "skills/n2d-review/scripts/self_audit.py",
                r"def _atomic_write_text",
                r"os\.fsync",
                r"os\.replace",
                r"add_argument\(\"--out\"",
                mode="all",
            ),
        ],
        "regression": [
            _req(
                "skills/n2d-review/scripts/test_meta_audit.py",
                r"def test_cli_out_matches_json_stdout_and_governance_findings_still_exit_zero",
            ),
            _req(
                "skills/n2d-review/scripts/test_self_audit.py",
                r"def test_cli_out_matches_json_stdout_and_preserves_block_exit",
            ),
        ],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_meta_audit.py::test_cli_out_matches_json_stdout_and_governance_findings_still_exit_zero",
            "skills/n2d-review/scripts/test_self_audit.py::test_cli_out_matches_json_stdout_and_preserves_block_exit",
        ],
    },
    {
        "id": "link_only_calibration_spoof",
        "class": "adversarial",
        "description": "把官方/论文 evidence 包版本号改成 v2，仍不能在无 held-out calibration 时制造 externally-calibrated。",
        "claim_id": "review_assurance_separation",
        "guard": [_req(
            "skills/n2d-review/scripts/meta_audit.py",
            r"calibration_attempted",
            r"calibrations",
            r"calibration_status",
            mode="all",
        )],
        "regression": [_req(
            "skills/n2d-review/scripts/test_meta_audit.py",
            r"def test_official_mapping_is_grounding_but_never_link_only_calibration",
            r"link_only_v2[\s\S]{0,900}not_run",
            mode="all",
        )],
        "runtime_tests": [
            "skills/n2d-review/scripts/test_meta_audit.py::test_official_mapping_is_grounding_but_never_link_only_calibration",
        ],
    },
    {
        "id": "partial_book_or_one_sided_boundary",
        "class": "cross_artifact",
        "description": "只物化首批集时仍须保留全书 source-unit 轴；只有强集尾但下集冷开弱时仍须进入 strict blocker。",
        "claim_id": "chapter_boundary_semantic_contract",
        "guard": [
            _req(
                "skills/n2d-script/scripts/split_novel.py",
                r"def build_source_units",
                r"full_book_beam_search_v1",
                mode="all",
            ),
            _req(
                "skills/n2d-script/scripts/boundary_audit.py",
                r"weak_next_opening",
                r"def boundary_pairs",
                mode="all",
            ),
        ],
        "regression": [
            _req(
                "skills/n2d-script/scripts/test_split_novel.py",
                r"def test_split_plan_v2_keeps_full_source_units_when_only_first_episode_materialized",
                r"def test_split_plan_v3_compacts_source_axis_and_rehydrates_legacy_units",
                mode="all",
            ),
            _req(
                "skills/n2d-script/scripts/test_boundary_audit.py",
                r"def test_weak_next_opening_alone_enters_strict_gate",
            ),
        ],
        "runtime_tests": [
            "skills/n2d-script/scripts/test_split_novel.py::test_split_plan_v2_keeps_full_source_units_when_only_first_episode_materialized",
            "skills/n2d-script/scripts/test_split_novel.py::test_split_plan_v3_compacts_source_axis_and_rehydrates_legacy_units",
            "skills/n2d-script/scripts/test_boundary_audit.py::test_weak_next_opening_alone_enters_strict_gate",
        ],
    },
]


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _files(root: Path, requirement: Mapping[str, Any]) -> List[Path]:
    raw = str(requirement.get("path") or "").strip()
    if not raw:
        return []
    if requirement.get("glob"):
        return sorted(p for p in root.glob(raw) if p.is_file())
    path = root / raw
    return [path] if path.is_file() else []


def evaluate_requirement(root: Path, requirement: Mapping[str, Any]) -> Dict[str, Any]:
    """Evaluate one safe static requirement from a built-in or JSON fixture."""
    paths = _files(root, requirement)
    patterns = [str(x) for x in requirement.get("patterns") or [] if str(x)]
    mode = str(requirement.get("mode") or "any").lower()
    matched: List[Dict[str, str]] = []
    errors: List[str] = []
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive report path
            errors.append(f"{path}: {exc}")
            continue
        if not patterns:
            matched.append({"path": path.relative_to(root).as_posix(), "pattern": "<file exists>"})
            continue
        local = []
        for pattern in patterns:
            try:
                if re.search(pattern, raw, re.I | re.M | re.S):
                    local.append(pattern)
            except re.error as exc:
                errors.append(f"invalid regex {pattern!r}: {exc}")
        ok = len(local) == len(patterns) if mode == "all" else bool(local)
        if ok:
            matched.extend({"path": path.relative_to(root).as_posix(), "pattern": p} for p in local)
    return {
        "ok": bool(matched),
        "path": str(requirement.get("path") or ""),
        "matched": matched,
        "errors": errors,
    }


def evaluate_link(root: Path, requirements: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = [evaluate_requirement(root, req) for req in requirements]
    return {
        "status": "covered" if rows and all(row["ok"] for row in rows) else "missing",
        "requirements": rows,
    }


def evaluate_claim(root: Path, claim: Mapping[str, Any]) -> Dict[str, Any]:
    raw_links = claim.get("links") if isinstance(claim.get("links"), Mapping) else {}
    links = {
        name: evaluate_link(root, raw_links.get(name) or [])
        for name in LINKS
    }
    covered = sum(1 for value in links.values() if value["status"] == "covered")
    return {
        "id": str(claim.get("id") or ""),
        "title": str(claim.get("title") or claim.get("id") or ""),
        "statement": str(claim.get("statement") or ""),
        "external_required": bool(claim.get("external_required")),
        "coverage": {"covered": covered, "total": len(LINKS), "ratio": covered / len(LINKS)},
        "links": links,
    }


def evaluate_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    guard = evaluate_link(root, probe.get("guard") or [])
    regression = evaluate_link(root, probe.get("regression") or [])
    ok = guard["status"] == "covered" and regression["status"] == "covered"
    missing = []
    if guard["status"] != "covered":
        missing.append("guard")
    if regression["status"] != "covered":
        missing.append("counterexample_regression")
    return {
        "id": str(probe.get("id") or ""),
        "class": str(probe.get("class") or "adversarial"),
        "claim_id": str(probe.get("claim_id") or ""),
        "description": str(probe.get("description") or ""),
        "status": "covered" if ok else "gap",
        "missing": missing,
        "guard": guard,
        "regression": regression,
    }


def _fixture_pack(path: Path) -> Dict[str, Any]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError("fixture pack 顶层必须是对象")
    if data.get("kind") not in {None, "n2d_review_meta_fixture_pack"}:
        raise ValueError("fixture pack kind 必须是 n2d_review_meta_fixture_pack")
    if data.get("version") not in {None, 1}:
        raise ValueError("fixture pack version 仅支持 1")
    return data


def load_fixture_packs(paths: Sequence[Path]) -> Dict[str, Any]:
    claims: List[Dict[str, Any]] = []
    probes: List[Dict[str, Any]] = []
    errors: List[str] = []
    for path in paths:
        try:
            data = _fixture_pack(path)
            claims.extend(x for x in data.get("claims") or [] if isinstance(x, dict))
            probes.extend(x for x in data.get("probes") or [] if isinstance(x, dict))
        except Exception as exc:
            errors.append(f"{path}: {exc}")
    return {"claims": claims, "probes": probes, "errors": errors}


def _valid_date(value: Any) -> bool:
    try:
        dt.date.fromisoformat(str(value))
        return True
    except (TypeError, ValueError):
        return False


def _valid_timestamp(value: Any) -> dt.datetime | None:
    """Return a timezone-aware ISO timestamp, otherwise ``None``."""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _unit_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if 0.0 <= number <= 1.0 else None


def _nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _positive_int(value: Any) -> int | None:
    number = _nonnegative_int(value)
    return number if number is not None and number > 0 else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _runtime_artifacts(root: Path, probes: Sequence[Mapping[str, Any]]) -> List[Dict[str, str]]:
    """Bind the runtime receipt to the exact guard and test files it exercised."""
    roles_by_path: Dict[Path, set[str]] = {}
    for probe in probes:
        for role, requirements in (("guard", probe.get("guard") or []), ("test", probe.get("regression") or [])):
            for requirement in requirements:
                for path in _files(root, requirement):
                    roles_by_path.setdefault(path.resolve(), set()).add(role)
        for nodeid in probe.get("runtime_tests") or []:
            rel_path = str(nodeid).split("::", 1)[0]
            candidate = (root / rel_path).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                continue
            if candidate.is_file():
                roles_by_path.setdefault(candidate, set()).add("runtime_test")
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "roles": ",".join(sorted(roles)),
            "sha256": _sha256(path),
        }
        for path, roles in sorted(roles_by_path.items(), key=lambda item: item[0].as_posix())
    ]


def run_registered_adversarial_tests(
    root: Path,
    probes: Sequence[Mapping[str, Any]],
    *,
    requested: bool,
) -> Dict[str, Any]:
    """Run explicit regression nodeids and emit a current-SHA runtime receipt.

    Merely finding a ``def test_*`` string is static coverage, never evidence
    that pytest executed.  This function is the only path that can change
    ``adversarially-tested`` away from ``not_run``.
    """
    total = len(probes)
    base: Dict[str, Any] = {
        "kind": "n2d_review_adversarial_runtime_receipt",
        "version": 1,
        "requested": requested,
        "status": "not_run",
        "covered": 0,
        "total": total,
        "nodeids": [],
        "missing_runtime_mappings": [],
        "errors": [],
        "artifact_bindings": [],
        "started_at": "",
        "finished_at": "",
        "exit_code": None,
        "stdout_tail": "",
    }
    if not requested:
        return base

    root = root.resolve()
    runnable_probes: set[str] = set()
    nodeids: List[str] = []
    for probe in probes:
        probe_id = str(probe.get("id") or "")
        raw_nodeids = probe.get("runtime_tests")
        if not isinstance(raw_nodeids, list) or not raw_nodeids:
            base["missing_runtime_mappings"].append(probe_id or "<missing-id>")
            continue
        local: List[str] = []
        for raw_nodeid in raw_nodeids:
            nodeid = str(raw_nodeid or "").strip()
            rel_path = nodeid.split("::", 1)[0]
            if not nodeid or not rel_path or Path(rel_path).is_absolute():
                base["errors"].append(f"{probe_id}: runtime nodeid 必须是本仓相对路径：{nodeid}")
                continue
            candidate = (root / rel_path).resolve()
            try:
                candidate.relative_to(root)
            except ValueError:
                base["errors"].append(f"{probe_id}: runtime nodeid 越出本仓：{nodeid}")
                continue
            if not candidate.is_file():
                base["errors"].append(f"{probe_id}: runtime test 文件不存在：{rel_path}")
                continue
            local.append(nodeid)
        if len(local) == len(raw_nodeids):
            runnable_probes.add(probe_id)
            nodeids.extend(local)

    nodeids = list(dict.fromkeys(nodeids))
    base["nodeids"] = nodeids
    base["artifact_bindings"] = _runtime_artifacts(root, probes)
    if not nodeids:
        base["status"] = "invalid"
        if not base["errors"]:
            base["errors"].append("没有可执行的已登记 runtime test nodeid")
        return base

    command = [sys.executable, "-m", "pytest", "-q", *nodeids]
    base["command"] = command
    base["started_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        combined = (completed.stdout or "") + (completed.stderr or "")
        base["exit_code"] = completed.returncode
        base["stdout_tail"] = combined[-12000:]
        if completed.returncode != 0:
            base["status"] = "failed"
        elif base["errors"] or base["missing_runtime_mappings"]:
            base["status"] = "partial"
            base["covered"] = len(runnable_probes)
        else:
            base["status"] = "complete"
            base["covered"] = total
    except subprocess.TimeoutExpired as exc:
        base["status"] = "failed"
        base["errors"].append("已登记对抗回归超过 300 秒 timeout")
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        base["stdout_tail"] = output[-12000:]
    except Exception as exc:  # pragma: no cover - environment failure
        base["status"] = "invalid"
        base["errors"].append(f"无法启动 pytest：{exc}")
    finally:
        base["finished_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    return base


def validate_evidence_entry(entry: Mapping[str, Any], known_claim_ids: set[str]) -> List[str]:
    issues: List[str] = []
    claim_id = str(entry.get("claim_id") or "").strip()
    if not claim_id:
        issues.append("缺 claim_id")
    elif claim_id not in known_claim_ids:
        issues.append(f"claim_id={claim_id} 未映射到本次五联 claim")
    if not str(entry.get("claim") or "").strip():
        issues.append("缺 claim")
    claim_type = str(entry.get("claim_type") or "").strip()
    if claim_type not in {
        "deterministic_contract", "capability", "regulatory", "quality_heuristic", "market_observation"
    }:
        issues.append("claim_type 非法")
    source = entry.get("source") if isinstance(entry.get("source"), Mapping) else {}
    source_kind = str(source.get("kind") or "").strip()
    if not str(source.get("title") or "").strip() or not str(source.get("url") or "").strip():
        issues.append("source 必须有 title + url")
    if source_kind not in SOURCE_KINDS:
        issues.append("source.kind 非法")
    if not _valid_date(entry.get("checked_at")):
        issues.append("checked_at 必须是 YYYY-MM-DD")
    confidence = str(entry.get("confidence") or "").strip()
    if confidence not in CONFIDENCE_LEVELS:
        issues.append("confidence 非法")
    mappings = entry.get("implementation_mapping")
    if not isinstance(mappings, list) or not mappings:
        issues.append("implementation_mapping 至少一项")
        mappings = []
    for index, mapping in enumerate(mappings):
        if not isinstance(mapping, Mapping):
            issues.append(f"implementation_mapping[{index}] 必须是对象")
            continue
        if not all(str(mapping.get(key) or "").strip() for key in ("path", "symbol", "rationale")):
            issues.append(f"implementation_mapping[{index}] 缺 path/symbol/rationale")
        enforcement = str(mapping.get("enforcement") or "").strip()
        if enforcement not in ENFORCEMENT_LEVELS:
            issues.append(f"implementation_mapping[{index}].enforcement 非法")
        if enforcement == "block":
            if confidence != "high":
                issues.append("BLOCK 映射必须 confidence=high")
            if source_kind not in HARD_GATE_SOURCE_KINDS:
                issues.append(f"{source_kind or 'unknown'} 来源不得直接映射 BLOCK")
            if claim_type in {"quality_heuristic", "market_observation"}:
                issues.append(f"{claim_type} 不得直接映射 BLOCK（B10）")
    return issues


def validate_calibration_entry(
    entry: Mapping[str, Any],
    known_claim_ids: set[str],
    *,
    root: Path,
) -> Dict[str, Any]:
    """Validate and independently recompute one held-out calibration contract.

    All independence/blinding fields are explicit attestations, not proof of a
    person's identity.  They are therefore necessary but never sufficient for
    a global "unbiased" claim.  Metric and artifact checks are deterministic.
    """
    issues: List[str] = []
    claim_id = str(entry.get("claim_id") or "").strip()
    calibration_id = str(entry.get("calibration_id") or "").strip()
    if not claim_id:
        issues.append("缺 claim_id")
    elif claim_id not in known_claim_ids:
        issues.append(f"claim_id={claim_id} 未映射到本次五联 claim")
    if not calibration_id:
        issues.append("缺 calibration_id")

    evaluated_at = _valid_timestamp(entry.get("evaluated_at"))
    if evaluated_at is None:
        issues.append("evaluated_at 必须是带时区 ISO date-time")
    if entry.get("held_out") is not True:
        issues.append("held_out 必须显式为 true")
    if entry.get("blind_to_gate_result") is not True:
        issues.append("blind_to_gate_result 必须显式为 true")

    reviewer = entry.get("reviewer") if isinstance(entry.get("reviewer"), Mapping) else {}
    reviewer_id = str(reviewer.get("reviewer_id") or "").strip()
    if not reviewer_id or not str(reviewer.get("affiliation") or "").strip():
        issues.append("reviewer 缺 reviewer_id/affiliation")
    if reviewer.get("independent_from_implementation") is not True:
        issues.append("reviewer.independent_from_implementation 必须为 true")
    if reviewer.get("independent_from_sample_selection") is not True:
        issues.append("reviewer.independent_from_sample_selection 必须为 true")
    if str(reviewer.get("conflict_of_interest") or "").strip() != "none_declared":
        issues.append("reviewer.conflict_of_interest 必须为 none_declared")

    protocol = entry.get("protocol") if isinstance(entry.get("protocol"), Mapping) else {}
    predeclared_at = _valid_timestamp(protocol.get("predeclared_at"))
    if predeclared_at is None:
        issues.append("protocol.predeclared_at 必须是带时区 ISO date-time")
    elif evaluated_at is not None and predeclared_at >= evaluated_at:
        issues.append("protocol.predeclared_at 必须早于 evaluated_at")
    if protocol.get("selection_locked_before_evaluation") is not True:
        issues.append("protocol.selection_locked_before_evaluation 必须为 true")

    thresholds = protocol.get("thresholds") if isinstance(protocol.get("thresholds"), Mapping) else {}
    max_fnr = _unit_number(thresholds.get("max_fnr"))
    max_fpr = _unit_number(thresholds.get("max_fpr"))
    if max_fnr is None or max_fpr is None:
        issues.append("protocol.thresholds 必须预声明 0..1 的 max_fnr/max_fpr")

    sampling = protocol.get("sampling") if isinstance(protocol.get("sampling"), Mapping) else {}
    method = str(sampling.get("method") or "").strip()
    if method not in STRATIFIED_SAMPLING_METHODS:
        issues.append("protocol.sampling.method 必须是显式分层抽样方法")
    if not str(sampling.get("population_description") or "").strip():
        issues.append("protocol.sampling 缺 population_description")
    population_size = _positive_int(sampling.get("population_size"))
    sample_size = _positive_int(sampling.get("sample_size"))
    if population_size is None or sample_size is None:
        issues.append("protocol.sampling population_size/sample_size 必须是正整数")
    elif sample_size > population_size:
        issues.append("protocol.sampling.sample_size 不得大于 population_size")
    strata = sampling.get("strata")
    stratum_total = 0
    stratum_names: List[str] = []
    if not isinstance(strata, list) or len(strata) < 2:
        issues.append("protocol.sampling.strata 至少两个分层")
    else:
        for index, stratum in enumerate(strata):
            row = stratum if isinstance(stratum, Mapping) else {}
            name = str(row.get("name") or "").strip()
            count = _positive_int(row.get("sample_count"))
            if not name or count is None or not str(row.get("selection_rule") or "").strip():
                issues.append(f"protocol.sampling.strata[{index}] 缺 name/sample_count/selection_rule")
                continue
            stratum_names.append(name)
            stratum_total += count
        if len(stratum_names) != len(set(stratum_names)):
            issues.append("protocol.sampling.strata.name 必须唯一")
        if sample_size is not None and stratum_total != sample_size:
            issues.append("各 strata.sample_count 之和必须等于 sample_size")

    ground_truth = entry.get("ground_truth") if isinstance(entry.get("ground_truth"), Mapping) else {}
    if not str(ground_truth.get("adjudication_method") or "").strip():
        issues.append("ground_truth 缺 adjudication_method")
    if not str(ground_truth.get("disagreement_resolution") or "").strip():
        issues.append("ground_truth 缺 disagreement_resolution")
    if ground_truth.get("blind_to_gate_result") is not True:
        issues.append("ground_truth.blind_to_gate_result 必须为 true")
    if ground_truth.get("adjudicators_independent_from_implementation") is not True:
        issues.append("ground_truth.adjudicators_independent_from_implementation 必须为 true")
    raw_adjudicators = ground_truth.get("adjudicator_ids")
    adjudicators = [str(item).strip() for item in raw_adjudicators] if isinstance(raw_adjudicators, list) else []
    adjudicators = [item for item in adjudicators if item]
    if len(adjudicators) < 2 or len(adjudicators) != len(set(adjudicators)):
        issues.append("ground_truth.adjudicator_ids 至少两个且必须唯一")
    if reviewer_id and reviewer_id in adjudicators:
        issues.append("独立 reviewer 不得同时充当 ground-truth adjudicator")

    results = entry.get("results") if isinstance(entry.get("results"), Mapping) else {}
    matrix = results.get("confusion_matrix") if isinstance(results.get("confusion_matrix"), Mapping) else {}
    matrix_values: Dict[str, int] = {}
    for key in ("tp", "tn", "fp", "fn"):
        number = _nonnegative_int(matrix.get(key))
        if number is None:
            issues.append(f"results.confusion_matrix.{key} 必须是非负整数")
        else:
            matrix_values[key] = number
    reported_fnr = _unit_number(results.get("fnr"))
    reported_fpr = _unit_number(results.get("fpr"))
    if reported_fnr is None or reported_fpr is None:
        issues.append("results.fnr/fpr 必须是 0..1 数值")

    computed_fnr: float | None = None
    computed_fpr: float | None = None
    if len(matrix_values) == 4:
        total = sum(matrix_values.values())
        if sample_size is not None and total != sample_size:
            issues.append("confusion matrix 总数必须等于 protocol.sample_size")
        positive = matrix_values["tp"] + matrix_values["fn"]
        negative = matrix_values["tn"] + matrix_values["fp"]
        if positive <= 0 or negative <= 0:
            issues.append("confusion matrix 必须同时含正类与负类，才能复算 FNR/FPR")
        else:
            computed_fnr = matrix_values["fn"] / positive
            computed_fpr = matrix_values["fp"] / negative
            if reported_fnr is not None and abs(reported_fnr - computed_fnr) > 1e-6:
                issues.append("results.fnr 与 confusion matrix 复算值不一致")
            if reported_fpr is not None and abs(reported_fpr - computed_fpr) > 1e-6:
                issues.append("results.fpr 与 confusion matrix 复算值不一致")

    artifacts = entry.get("artifacts")
    roles: List[str] = []
    paths: List[str] = []
    if not isinstance(artifacts, list):
        issues.append("artifacts 必须是当前本仓文件清单")
        artifacts = []
    for index, artifact in enumerate(artifacts):
        row = artifact if isinstance(artifact, Mapping) else {}
        role = str(row.get("role") or "").strip()
        rel_path = str(row.get("path") or "").strip()
        expected_sha = str(row.get("sha256") or "").strip().lower()
        if role not in CALIBRATION_ARTIFACT_ROLES:
            issues.append(f"artifacts[{index}].role 非法")
        else:
            roles.append(role)
        if not rel_path:
            issues.append(f"artifacts[{index}].path 为空")
            continue
        paths.append(rel_path)
        candidate = (root / rel_path).resolve() if not Path(rel_path).is_absolute() else Path(rel_path).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            issues.append(f"artifacts[{index}].path 必须位于当前本仓")
            continue
        if not candidate.is_file():
            issues.append(f"artifacts[{index}].path 不存在：{rel_path}")
            continue
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
            issues.append(f"artifacts[{index}].sha256 必须是 64 位十六进制")
            continue
        current_sha = _sha256(candidate)
        if current_sha != expected_sha:
            issues.append(f"artifacts[{index}] SHA 已过期：{rel_path}")
    missing_roles = CALIBRATION_ARTIFACT_ROLES - set(roles)
    if missing_roles:
        issues.append("artifacts 缺角色：" + ", ".join(sorted(missing_roles)))
    if len(roles) != len(set(roles)):
        issues.append("artifacts.role 不得重复")
    if len(paths) != len(set(paths)):
        issues.append("不同 artifact role 不得复用同一路径")

    threshold_passed = bool(
        not issues
        and computed_fnr is not None
        and computed_fpr is not None
        and max_fnr is not None
        and max_fpr is not None
        and computed_fnr <= max_fnr
        and computed_fpr <= max_fpr
    )
    valid = not issues
    return {
        "claim_id": claim_id,
        "calibration_id": calibration_id,
        "valid": valid,
        "threshold_passed": threshold_passed,
        "status": "invalid" if not valid else ("passed" if threshold_passed else "failed"),
        "issues": issues,
        "computed": {
            "fnr": computed_fnr,
            "fpr": computed_fpr,
            "max_fnr": max_fnr,
            "max_fpr": max_fpr,
        },
        "artifact_paths": paths,
    }


def validate_evidence(
    paths: Sequence[Path],
    known_claim_ids: set[str],
    *,
    root: Path | None = None,
) -> Dict[str, Any]:
    entries: List[Dict[str, Any]] = []
    calibrations: List[Dict[str, Any]] = []
    errors: List[str] = []
    calibration_errors: List[str] = []
    calibration_attempted = False
    for path in paths:
        try:
            data = _load_json(path)
        except Exception as exc:
            errors.append(f"{path}: {exc}")
            continue
        version = data.get("version") if isinstance(data, dict) else None
        if not isinstance(data, dict) or data.get("kind") != "n2d_review_external_evidence" or version not in {1, 2}:
            errors.append(f"{path}: kind/version 必须是 n2d_review_external_evidence/1 或 /2")
            continue
        evidence_rows = data.get("evidence")
        if not isinstance(evidence_rows, list):
            errors.append(f"{path}: evidence 必须是数组（可为空）")
            evidence_rows = []
        for raw in evidence_rows:
            if not isinstance(raw, dict):
                errors.append(f"{path}: evidence 行必须是对象")
                continue
            issues = validate_evidence_entry(raw, known_claim_ids)
            source = raw.get("source") if isinstance(raw.get("source"), Mapping) else {}
            if root is not None:
                for index, mapping in enumerate(raw.get("implementation_mapping") or []):
                    if not isinstance(mapping, Mapping):
                        continue
                    rel_path = str(mapping.get("path") or "").strip()
                    symbol = str(mapping.get("symbol") or "").strip()
                    if not rel_path:
                        continue
                    candidate = (root / rel_path).resolve() if not Path(rel_path).is_absolute() else Path(rel_path).resolve()
                    try:
                        candidate.relative_to(root.resolve())
                    except ValueError:
                        issues.append(f"implementation_mapping[{index}].path 必须位于本仓")
                        continue
                    if not candidate.is_file():
                        issues.append(f"implementation_mapping[{index}].path 不存在：{rel_path}")
                        continue
                    try:
                        implementation_text = candidate.read_text(encoding="utf-8")
                    except Exception as exc:  # pragma: no cover - defensive
                        issues.append(f"implementation_mapping[{index}].path 不可读：{exc}")
                        continue
                    if symbol and symbol not in implementation_text:
                        issues.append(f"implementation_mapping[{index}].symbol 未在目标文件中找到：{symbol}")
            grounding_eligible = (
                not issues
                and str(raw.get("confidence") or "") in {"high", "medium"}
                and str(source.get("kind") or "") in (HARD_GATE_SOURCE_KINDS | {"industry_report"})
                and str(raw.get("claim_type") or "") != "market_observation"
            )
            entries.append({
                "claim_id": str(raw.get("claim_id") or ""),
                "valid": not issues,
                "grounding_eligible": grounding_eligible,
                "issues": issues,
                "claim_type": raw.get("claim_type"),
                "source": source,
                "confidence": raw.get("confidence"),
                "implementation_mapping": raw.get("implementation_mapping") or [],
            })
        raw_calibrations = data.get("calibrations", [])
        if version == 1 and raw_calibrations:
            calibration_attempted = True
            calibration_errors.append(
                f"{path}: version=1 仅用于 externally-grounded；calibrations 必须升级到 version=2"
            )
            continue
        if version == 2:
            if not isinstance(raw_calibrations, list):
                calibration_attempted = True
                calibration_errors.append(f"{path}: calibrations 必须是数组")
                continue
            calibration_attempted = calibration_attempted or bool(raw_calibrations)
            if root is None and raw_calibrations:
                calibration_errors.append(f"{path}: 校准合同必须提供当前 repo root 以核验 artifact SHA")
                continue
            for raw in raw_calibrations:
                if not isinstance(raw, Mapping):
                    calibration_errors.append(f"{path}: calibration 行必须是对象")
                    continue
                calibrations.append(validate_calibration_entry(raw, known_claim_ids, root=root.resolve()))
    return {
        "entries": entries,
        "calibrations": calibrations,
        "errors": errors,
        "calibration_errors": calibration_errors,
        "calibration_attempted": calibration_attempted,
    }


def _status(covered: int, total: int, *, empty: str = "not_run") -> str:
    if total <= 0:
        return empty
    if covered == total:
        return "complete"
    if covered:
        return "partial"
    return "not_run"


def audit(
    root: Path,
    *,
    fixture_paths: Sequence[Path] = (),
    evidence_paths: Sequence[Path] = (),
    run_tests: bool = False,
) -> Dict[str, Any]:
    root = root.resolve()
    fixture = load_fixture_packs([p.resolve() for p in fixture_paths])
    raw_claims = list(BUILTIN_CLAIMS) + fixture["claims"]
    raw_probes = list(BUILTIN_PROBES) + fixture["probes"]
    claims = [evaluate_claim(root, item) for item in raw_claims]
    probes = [evaluate_probe(root, item) for item in raw_probes]
    runtime_receipt = run_registered_adversarial_tests(root, raw_probes, requested=run_tests)
    static_probe_covered = {probe["id"] for probe in probes if probe["status"] == "covered"}
    if run_tests and runtime_receipt["status"] == "complete" and len(static_probe_covered) != len(probes):
        runtime_receipt["status"] = "partial"
        runtime_receipt["covered"] = len(static_probe_covered)
        runtime_receipt["errors"].append("存在静态 guard/counterexample 链缺口，运行通过不得冒充完整对抗覆盖")
    claim_ids = {str(item.get("id") or "") for item in raw_claims if str(item.get("id") or "")}
    evidence = validate_evidence([p.resolve() for p in evidence_paths], claim_ids, root=root)

    internal_total = len(claims) * len(INTERNAL_LINKS)
    internal_covered = sum(
        1 for claim in claims for name in INTERNAL_LINKS
        if claim["links"][name]["status"] == "covered"
    )
    adversarial_coverage_total = len(claims) * len(ADVERSARIAL_LINKS) + len(probes)
    adversarial_coverage_covered = (
        sum(
            1 for claim in claims for name in ADVERSARIAL_LINKS
            if claim["links"][name]["status"] == "covered"
        )
        + sum(1 for probe in probes if probe["status"] == "covered")
    )
    external_required = {claim["id"] for claim in claims if claim["external_required"]}
    externally_grounded = {
        entry["claim_id"] for entry in evidence["entries"]
        if entry["grounding_eligible"] and entry["claim_id"] in external_required
    }
    grounding_status = _status(len(externally_grounded), len(external_required))

    calibration_rows = evidence["calibrations"]
    externally_calibrated = {
        row["claim_id"] for row in calibration_rows
        if row["valid"] and row["threshold_passed"] and row["claim_id"] in external_required
    }
    if evidence["calibration_errors"] or (evidence["calibration_attempted"] and not calibration_rows):
        calibration_status = "invalid"
    elif not calibration_rows:
        calibration_status = "not_run"
    elif any(not row["valid"] for row in calibration_rows):
        calibration_status = "invalid"
    elif any(
        row["status"] == "failed" and row["claim_id"] in external_required
        for row in calibration_rows
    ):
        calibration_status = "failed"
    elif external_required and externally_calibrated == external_required:
        calibration_status = "complete"
    else:
        calibration_status = "partial"

    findings: List[Dict[str, Any]] = []
    for claim in claims:
        missing = [name for name, value in claim["links"].items() if value["status"] != "covered"]
        if missing:
            findings.append({
                "sev": "warn",
                "dim": "声明实现五联",
                "claim_id": claim["id"],
                "msg": f"{claim['title']} 缺链：{', '.join(missing)}。",
                "confidence": "static",
            })
    for probe in probes:
        if probe["status"] != "covered":
            findings.append({
                "sev": "warn",
                "dim": "对抗/变形测试",
                "claim_id": probe["claim_id"],
                "probe_id": probe["id"],
                "msg": f"{probe['description']} 缺 {', '.join(probe['missing'])}。",
                "confidence": "static",
            })
    if run_tests and runtime_receipt["status"] != "complete":
        details = list(runtime_receipt.get("errors") or [])
        if runtime_receipt.get("missing_runtime_mappings"):
            details.append(
                "缺 runtime_tests 映射：" + ", ".join(runtime_receipt["missing_runtime_mappings"])
            )
        findings.append({
            "sev": "warn",
            "dim": "运行时对抗回归",
            "msg": (
                f"--run-tests 状态={runtime_receipt['status']}；"
                + ("；".join(details) if details else "至少一个已登记 pytest 回归未通过")
            ),
            "confidence": "runtime",
        })
    for error in fixture["errors"]:
        findings.append({"sev": "warn", "dim": "meta fixture", "msg": error, "confidence": "deterministic"})
    for error in evidence["errors"]:
        findings.append({"sev": "warn", "dim": "外部证据 schema", "msg": error, "confidence": "deterministic"})
    for error in evidence["calibration_errors"]:
        findings.append({"sev": "warn", "dim": "外部校准合同", "msg": error, "confidence": "deterministic"})
    for entry in evidence["entries"]:
        if not entry["valid"]:
            findings.append({
                "sev": "warn",
                "dim": "外部证据 schema",
                "claim_id": entry["claim_id"],
                "msg": "；".join(entry["issues"]),
                "confidence": "deterministic",
            })
    for calibration in calibration_rows:
        if not calibration["valid"]:
            findings.append({
                "sev": "warn",
                "dim": "外部校准合同",
                "claim_id": calibration["claim_id"],
                "calibration_id": calibration["calibration_id"],
                "msg": "；".join(calibration["issues"]),
                "confidence": "deterministic",
            })
        elif not calibration["threshold_passed"]:
            metrics = calibration["computed"]
            findings.append({
                "sev": "warn",
                "dim": "外部校准合同",
                "claim_id": calibration["claim_id"],
                "calibration_id": calibration["calibration_id"],
                "msg": (
                    "独立留出校准未过预声明阈值："
                    f"FNR={metrics['fnr']} (max={metrics['max_fnr']}), "
                    f"FPR={metrics['fpr']} (max={metrics['max_fpr']})。"
                ),
                "confidence": "deterministic",
            })

    assurance = {
        "self_checked": {
            "label": "self-checked",
            "status": _status(internal_covered, internal_total),
            "covered": internal_covered,
            "total": internal_total,
            "meaning": "声明、实现、调用三段静态可追溯；不等于行为已被反例击穿验证。",
        },
        "adversarially_tested": {
            "label": "adversarially-tested",
            "status": runtime_receipt["status"],
            "covered": runtime_receipt["covered"],
            "total": runtime_receipt["total"],
            "meaning": "仅由本次 --run-tests 的 pytest 运行收据成立；测试文本存在不算 tested。",
        },
        "adversarial_test_coverage": {
            "label": "adversarial-test-coverage",
            "status": _status(adversarial_coverage_covered, adversarial_coverage_total),
            "covered": adversarial_coverage_covered,
            "total": adversarial_coverage_total,
            "meaning": "静态可找到测试、反例和 guard（defined-only）；不证明 pytest 实际执行过。",
        },
        "externally_grounded": {
            "label": "externally-grounded",
            "status": grounding_status,
            "covered": len(externally_grounded),
            "total": len(external_required),
            "meaning": "外部来源已做 provenance 与实现映射；链接或论文不是留出样本校准。",
        },
        "externally_calibrated": {
            "label": "externally-calibrated",
            "status": calibration_status,
            "covered": len(externally_calibrated),
            "total": len(external_required),
            "meaning": (
                "每个外部必需 claim 都有独立审阅、held-out、盲法、预注册阈值、分层抽样、"
                "裁决金标、当前本仓 artifact SHA 与重算误差率且通过；仍不等于无偏。"
            ),
        },
        "no_blind_spot_claim_allowed": False,
        "blind_spot_statement": (
            "即使本报告 0 warn，也只表示已登记的静态链和已知反例未发现缺口；"
            "即使 externally-calibrated=complete，也不能表述为“无盲区”“审查无偏”或“结果无偏”。"
        ),
    }
    counts = {sev: sum(1 for row in findings if row["sev"] == sev) for sev in ("block", "warn", "info")}
    return {
        "kind": "n2d_review_meta_audit",
        "version": 3,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "counts": counts,
        "claims": claims,
        "probes": probes,
        "external_evidence": evidence,
        "adversarial_runtime_receipt": runtime_receipt,
        "assurance": assurance,
        "findings": findings,
    }


def render_markdown(report: Mapping[str, Any]) -> str:
    assurance = report["assurance"]
    lines = [
        "# n2d-review 独立 meta-audit",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 统计：warn {report['counts']['warn']}（本工具 report-only，不产生生产 BLOCK）",
        "",
        "| 结论层 | 状态 | 覆盖 | 含义 |",
        "|---|---|---:|---|",
    ]
    for key in (
        "self_checked",
        "adversarial_test_coverage",
        "adversarially_tested",
        "externally_grounded",
        "externally_calibrated",
    ):
        row = assurance[key]
        lines.append(
            f"| {row.get('label') or key} | {row['status']} | {row['covered']}/{row['total']} | {row['meaning']} |"
        )
    lines += ["", f"> {assurance['blind_spot_statement']}", "", "## 五联覆盖", ""]
    for claim in report["claims"]:
        states = " → ".join(
            f"{name}:{'✓' if claim['links'][name]['status'] == 'covered' else '✗'}"
            for name in LINKS
        )
        lines.append(f"- `{claim['id']}` {claim['title']}：{states}")
    lines += ["", "## 对抗/变形探针", ""]
    for probe in report["probes"]:
        lines.append(
            f"- `{probe['id']}` {probe['status']}：{probe['description']}"
            + (f"（缺 {', '.join(probe['missing'])}）" if probe["missing"] else "")
        )
    if report["findings"]:
        lines += ["", "## Findings", ""]
        for row in report["findings"]:
            lines.append(f"- [{row['sev']}] {row['dim']}：{row['msg']}")
    return "\n".join(lines) + "\n"


def _atomic_write_text(path: Path, content: str) -> None:
    """Write one UTF-8 report beside a temporary file, then replace atomically."""
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Independent five-link/adversarial meta-audit for n2d-review")
    ap.add_argument("--root", default=str(repo_root_from_here()), help="repo root")
    ap.add_argument("--fixture", action="append", default=[], help="JSON meta fixture pack (repeatable)")
    ap.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="JSON evidence pack (v1 grounding only; v2 may add held-out calibrations; repeatable)",
    )
    ap.add_argument(
        "--run-tests",
        action="store_true",
        help="execute the minimal registered pytest regressions and emit a current-SHA runtime receipt",
    )
    ap.add_argument("--print-evidence-schema", action="store_true", help="print the evidence JSON schema and exit")
    ap.add_argument("--json", action="store_true", help="print JSON report")
    ap.add_argument("--out", default="", help="atomically write the complete JSON report to PATH")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    if ns.print_evidence_schema:
        print(json.dumps(EXTERNAL_EVIDENCE_SCHEMA, ensure_ascii=False, indent=2))
        return 0
    report = audit(
        Path(ns.root),
        fixture_paths=[Path(p) for p in ns.fixture],
        evidence_paths=[Path(p) for p in ns.evidence],
        run_tests=ns.run_tests,
    )
    json_report = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if ns.out:
        _atomic_write_text(Path(ns.out), json_report)
    if ns.json:
        print(json_report, end="")
    else:
        print(render_markdown(report), end="")
    # Meta-audit findings are governance signals.  They do not become a
    # production hard gate merely because a static pattern is absent (B10).
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
