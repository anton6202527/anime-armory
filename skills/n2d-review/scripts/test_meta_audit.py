#!/usr/bin/env python3
"""Regression tests for the independent n2d-review meta-audit."""
from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("meta_audit.py")
SPEC = importlib.util.spec_from_file_location("n2d_review_meta_audit", SCRIPT)
meta = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(meta)
SELF_AUDIT_SCRIPT = Path(__file__).with_name("self_audit.py")
SELF_SPEC = importlib.util.spec_from_file_location("n2d_self_audit_with_meta", SELF_AUDIT_SCRIPT)
self_audit = importlib.util.module_from_spec(SELF_SPEC)
assert SELF_SPEC.loader is not None
SELF_SPEC.loader.exec_module(self_audit)
REPO_ROOT = SCRIPT.resolve().parents[3]


def _write(root: Path, rel: str, raw: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw, encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _vulnerable_repo(root: Path) -> None:
    """Four examples that a file/detector inventory alone would miss."""
    _write(root, "docs/skill-design-principles.md", "B7 library_tier 分档人物定妆基础包\n")
    _write(root, "skills/n2d-review/SKILL.md", "多视角身份包(MVIEW)：失败行阻断\n")
    _write(root, "skills/n2d-image/SKILL.md", "对齐不达标 = 与脸漂同级硬伤、不得落档。\n")
    _write(
        root,
        "skills/n2d-script/SKILL.md",
        "boundary_review.py check 校验签收与指纹。\n"
        "集 = 戏剧节拍单元，≠ 章；必须形成冲突→反转→钩子。\n"
        "split_plan.json 保存 source_units、boundary_candidates 与 beam。\n"
        "每条边界必须有双侧边界合同。\n",
    )
    _write(
        root,
        "skills/n2d-review/scripts/gate_core.py",
        "def required(form):\n    return form['reference_atlas'].get('build_tier')\n",
    )
    _write(root, "skills/n2d-review/scripts/gate.py", "check_identity_registry(root)\n")
    _write(
        root,
        "skills/n2d-review/scripts/production_consistency.py",
        "def check_multiview_identity_pack(row):\n"
        "    verdict = row.get('verdict')\n"
        "    return verdict in {'fail', 'block'}\n"
        "checks = {'多视角身份包(MVIEW)': check_multiview_identity_pack}\n",
    )
    _write(
        root,
        "skills/n2d-image/scripts/image_qc.py",
        "def audit_turnaround_alignment(root, ep):\n"
        "    return {'level': 'warn', 'code': 'turnaround_misaligned'}\n"
        "ta = audit_turnaround_alignment(root, ep)\n",
    )
    _write(
        root,
        "skills/n2d-script/scripts/boundary_review.py",
        "VALID_DECISIONS = {'move_boundary', 'merge_prev', 'split', 'rewrite'}\n"
        "def validate(entry): return bool(entry.get('notes'))\n",
    )
    _write(root, "skills/n2d/run.py", "review_script = 'boundary_review.py'\n")
    _write(root, "skills/n2d-review/scripts/test_gate.py", "def test_smoke(): pass\n")
    _write(
        root,
        "skills/n2d-review/scripts/test_production_consistency.py",
        "def test_multiview_smoke(): pass\n",
    )
    _write(
        root,
        "skills/n2d-image/scripts/test_image_qc.py",
        "def test_turnaround_alignment_reason(): pass\n",
    )
    _write(root, "skills/n2d-script/scripts/test_boundary_review.py", "def test_signed(): pass\n")


def test_builtin_probes_detect_known_self_certification_gaps(tmp_path: Path, capsys) -> None:
    _vulnerable_repo(tmp_path)

    report = meta.audit(tmp_path)
    gaps = {row["id"]: row for row in report["probes"]}

    assert gaps["tier_self_reported_downgrade"]["status"] == "gap"
    assert gaps["all_chain_collusive_tier_downgrade"]["status"] == "gap"
    assert gaps["nested_fail_without_top_verdict"]["status"] == "gap"
    assert gaps["hard_claim_warn_implementation"]["status"] == "gap"
    assert gaps["signed_but_unapplied_review"]["status"] == "gap"
    assert gaps["planned_path_truthiness"]["status"] == "gap"
    assert gaps["planned_receipt_resurrection"]["status"] == "gap"
    assert gaps["non_png_hash_spoof"]["status"] == "gap"
    assert gaps["forged_png_shell"]["status"] == "gap"
    assert gaps["forged_human_metadata"]["status"] == "gap"
    assert gaps["same_image_multiangle_alias"]["status"] == "gap"
    assert gaps["copied_or_symlinked_pixel_alias"]["status"] == "gap"
    assert gaps["multiview_evidence_path_escape"]["status"] == "gap"
    assert gaps["pre_spend_registry_alias_bypass"]["status"] == "gap"
    assert gaps["multiform_row_reuse"]["status"] == "gap"
    assert gaps["memory_aggregate_false_positive"]["status"] == "gap"
    assert gaps["core_partial_self_downgrade"]["status"] == "gap"
    assert gaps["deleted_sidecar_cache_deadlock"]["status"] == "gap"
    assert gaps["structured_warn_exit_zero_cache"]["status"] == "gap"
    assert gaps["stale_report_resurrection"]["status"] == "gap"
    assert gaps["static_test_text_self_certification"]["status"] == "gap"
    assert gaps["stdout_only_assurance_receipt_loss"]["status"] == "gap"
    assert gaps["link_only_calibration_spoof"]["status"] == "gap"
    assert gaps["partial_book_or_one_sided_boundary"]["status"] == "gap"
    assert "guard" in gaps["nested_fail_without_top_verdict"]["missing"]
    assert "guard" in gaps["hard_claim_warn_implementation"]["missing"]
    # Static absence is a governance WARN, not a new production BLOCK (B10).
    assert meta.main(["--root", str(tmp_path), "--json"]) == 0
    capsys.readouterr()


def test_builtin_probes_recognise_guards_plus_counterexamples(tmp_path: Path) -> None:
    _vulnerable_repo(tmp_path)
    _write(
        tmp_path,
        "skills/n2d-review/scripts/gate_core.py",
        "READY_CHARACTER_MAKEUP_STATUSES={'ready', 'registered'}\n"
        "def tier_authority(library_tier, build_tier):\n"
        "    if library_tier != build_tier: raise ValueError('tier_mismatch')\n"
        "def _identity_reference_item_ready(item):\n"
        "    return item.get('status') in READY_CHARACTER_MAKEUP_STATUSES\n"
        "def _storyboard_character_appearance_evidence(root):\n"
        "    return {'CHAR_01': {'episode_count': 10}}\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/test_gate.py",
        "def test_core_self_reported_tier_downgrade_blocks():\n"
        "    library_tier='core_full'; build_tier='named_minimal'; assert library_tier != build_tier\n"
        "def test_identity_registry_planned_makeup_reference_is_blocked():\n"
        "    item={'path':'ref.png','status':'planned'}; finding='BLOCK planned 不能放行'; assert finding\n"
        "def test_memory_anchor_gate_recomputes_each_required_character_not_aggregate_count():\n"
        "    required=['CHAR_01/常态','CHAR_02/常态']; consumed=['CHAR_01/常态']; assert 'CHAR_02/常态' not in consumed\n"
        "def test_identity_registry_four_way_collusive_downgrade_blocked_by_storyboards():\n"
        "    assert 'core_full' != 'named_minimal'\n"
        "def test_storyboard_tier_evidence_uses_structured_visible_ids_only():\n"
        "    assert 'offscreen' not in ['CHAR_01']\n"
        "def test_identity_registry_legacy_without_structured_story_index_keeps_named_minimal():\n"
        "    assert 'named_minimal'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/production_consistency.py",
        "def check_multiview_identity_pack(row):\n"
        "    def _resolve_multiview_evidence_path(): return 'absolute_path_not_allowed path_outside_project_root'\n"
        "    failed_buckets = [bucket for bucket, value in row['buckets'].items() if value.get('status') == 'fail']\n"
        "    cid='CHAR_01'; form_name='常态'; by_key={(cid, form_name): row}\n"
        "    exact = by_key.get((cid, form_name))\n"
        "    duplicate_paths=[]; duplicate_canonical_realpath=[]; duplicate_png_sha=[]\n"
        "    reviewer_appears_automated = criteria_incomplete = explicit_current_pixels_confirmation_missing = False\n"
        "    return failed_buckets, exact, duplicate_paths, duplicate_canonical_realpath, duplicate_png_sha, reviewer_appears_automated, criteria_incomplete, explicit_current_pixels_confirmation_missing\n"
        "checks = {'多视角身份包(MVIEW)': check_multiview_identity_pack}\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/test_production_consistency.py",
        "def test_multiview_bucket_fail_missing_top_level():\n"
        "    buckets={'side': {'status': 'fail'}}; assert buckets['side']['status'] == 'fail'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/identity_eval_pack.py",
        "def _png_container_errors(path): return ['not_valid_png_container']\n"
        "def _resolve_project_evidence_path(root, path):\n"
        "    return 'absolute_registry_evidence_path_not_allowed registry_evidence_path_outside_project_root'\n"
        "def review(node_status):\n"
        "    if node_status not in {\"ready\", \"registered\"}: return 'registry_node_status=planned'\n"
        "    return 'registry_binding_fingerprint duplicate_path_across_buckets duplicate_canonical_realpath_across_buckets duplicate_png_sha_across_buckets'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/test_identity_eval_pack.py",
        "def test_planned_view_cannot_reuse_a_stale_accepted_receipt():\n"
        "    assert 'registry_node_status=planned'\n"
            "def test_plain_text_with_matching_hash_cannot_pose_as_png_evidence():\n"
            "    assert 'not_valid_png_container'\n"
            "def test_forged_png_header_shell_with_matching_hash_cannot_pose_as_pixels():\n"
            "    assert 'png_iend_invalid'\n"
            "def test_consumer_independently_rejects_forged_human_metadata():\n"
            "    assert 'reviewed_at_timezone_missing' and 'explicit_current_pixels_confirmation_missing'\n"
            "def test_same_png_cannot_be_relabelled_as_multiple_views():\n"
        "    assert 'duplicate_path_across_buckets'\n"
        "def test_producer_duplicate_png_sha_copy_cannot_pose_as_independent_view():\n"
        "    assert 'duplicate_png_sha_across_buckets'\n"
        "def test_producer_symlink_alias_uses_canonical_realpath_and_is_blocked():\n"
        "    assert 'duplicate_canonical_realpath_across_buckets'\n"
        "def test_producer_path_escape_and_absolute_registry_evidence_are_rejected():\n"
        "    assert 'registry_evidence_path_outside_project_root'\n"
        "def test_consumer_duplicate_png_sha_copy_is_independently_blocked():\n"
        "    assert 'duplicate_png_sha'\n"
        "def test_consumer_symlink_alias_is_independently_blocked():\n"
        "    assert 'duplicate_canonical_realpath'\n"
        "def test_consumer_path_escape_and_absolute_registry_path_are_independently_blocked():\n"
        "    assert 'path_outside_project_root'\n"
        "def test_distinct_crop_pixels_from_same_master_remain_valid():\n"
        "    assert 'distinct pixels pass'\n"
        "def test_one_form_row_cannot_be_reused_for_another_form():\n"
        "    assert 'CHAR_01/战损态'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/gates/contract.py",
        "def check():\n"
        "    required_from_plan=['CHAR_01/常态','CHAR_02/常态']\n"
        "    consumed_from_clips={'CHAR_01/常态':['Clip_01']}\n"
        "    unconsumed=set(required_from_plan)-set(consumed_from_clips)\n"
        "    assert unconsumed, '不得靠聚合数字放行'\n",
    )
    _write(
        tmp_path,
        "skills/n2d/_lib/n2d_const.py",
        "def restricted_partial_contract_valid(record): return False\n"
        "def independent_tier(observed_episode_count):\n"
        "    independent_episode_count=max(0, observed_episode_count); return independent_episode_count\n"
        "def tier(inferred, record):\n"
        "    if inferred != CHARACTER_LIBRARY_TIER_CORE or restricted_partial_contract_valid(record): return 'partial'\n"
        "    return CHARACTER_LIBRARY_TIER_CORE\n",
    )
    _write(
        tmp_path,
        "skills/n2d/_lib/test_character_library_contract.py",
        "def test_core_cannot_self_report_restricted_partial_without_approved_contract():\n"
        "    assert tier == CHARACTER_LIBRARY_TIER_CORE\n",
    )
    _write(
        tmp_path,
        "skills/n2d/run.py",
        "review_script = 'boundary_review.py'\n"
        "boundary_script = 'boundary_audit.py'\n"
        "def _cache_artifact_paths(root, stdout): return ['sidecar.json']\n"
        "def _run_report_only_prework(expected_outputs=None):\n"
        "    o={'status':'pass','_cache_artifacts':['sidecar.json']}\n"
        "    should_cache = o.get(\"status\") == \"pass\" and bool(o.get(\"_cache_artifacts\"))\n"
        "    return should_cache, expected_outputs\n"
        "def _script_result_status(returncode, stdout): return 'warn'\n"
        "detected_status = _script_result_status(0, stdout)\n"
        "report_status = \"pass\" if detected_status == \"pass\" else \"warn\"\n",
    )
    _write(
        tmp_path,
        "skills/n2d-script/scripts/split_novel.py",
        "def build_source_units(paras): return paras\n"
        "def build_boundary_candidates(paras, spans): return spans\n"
        "METHOD='full_book_beam_search_v1'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-script/scripts/boundary_audit.py",
        "def boundary_pairs(rows): return rows\n"
        "weak_next_opening = '上集收尾 + 下集开场'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-script/scripts/test_split_novel.py",
        "def test_split_plan_v2_keeps_full_source_units_when_only_first_episode_materialized():\n"
        "    source_units=['U1','U2']; assert len(source_units) == 2\n"
        "def test_beam_optimizer_is_global_and_dictionary_is_not_a_veto():\n"
        "    assert 'full_book_beam_search_v1'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-script/scripts/test_boundary_audit.py",
        "def test_two_sided_boundary_pair_flags_slow_next_opening():\n"
        "    assert '下集开场弱'\n"
        "def test_weak_next_opening_alone_enters_strict_gate():\n"
        "    strict_blockers=['weak_next_opening']; assert strict_blockers\n",
    )
    _write(
        tmp_path,
        "skills/n2d/test_run.py",
        "def test_report_only_cache_rebuilds_deleted_output_path_sidecar():\n"
        "    sidecar.unlink(); assert count.read_text() == \"2\"\n"
        "def test_report_only_warn_result_is_never_cached_even_with_artifact():\n"
        "    cache='warn-not-cached'; assert cache.get(\"warn\") is None\n"
        "def test_report_only_exit_zero_with_structured_warn_is_not_cached():\n"
        "    returncode=0; status='warn'; assert returncode == 0 and status == 'warn'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-identity/scripts/memory_anchor.py",
        "def build_plan(): return {'available': False, 'status': 'warn'}\n"
        "# Always replace an older plan, including unavailable\n"
        "if not ns.no_write:\n"
        "    plan['path'] = write_plan(root, episode, plan)\n",
    )
    _write(
        tmp_path,
        "skills/n2d-identity/scripts/test_memory_anchor.py",
        "def test_cli_overwrites_stale_ready_plan_with_explicit_unavailable_plan():\n"
        "    current={'available': False, 'status': 'warn'}\n"
        "    assert current[\"available\"] is False\n"
        "    assert current[\"status\"] == \"warn\"\n",
    )
    _write(
        tmp_path,
        "skills/n2d-image/scripts/image_qc.py",
        "HARD_LINT_CODES = ('turnaround_misaligned',)\n"
        "def _resolve_core_registry_image_path(root, path): return 'path'\n"
        "def _core_form_path_uniqueness_issues(root, form): return ['duplicate_png_sha_across_buckets']\n"
        "def audit_turnaround_alignment(root, ep): return {}\n"
        "ta = audit_turnaround_alignment(root, ep)\n",
    )
    _write(
        tmp_path,
        "skills/n2d-image/scripts/test_image_qc.py",
        "def test_turnaround_misaligned_hard_block():\n"
        "    code='turnaround_misaligned'; hard_blocks=[code]; assert hard_blocks\n"
        "def test_legacy_signer_path_escape_symlink_and_noncanonical_are_rejected():\n"
        "    assert 'path rejected'\n"
        "def test_legacy_finalize_consumer_duplicate_png_sha_is_independently_blocked():\n"
        "    assert 'duplicate_png_sha_across_buckets'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-image/scripts/codex_image_runner.py",
        "def _resolve_registry_image_path(root, path): return 'safe'\n"
        "def pre_spend(): return 'duplicate_canonical_realpath duplicate_png_sha'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-image/scripts/test_codex_image_runner.py",
        "def test_shared_first_pre_spend_duplicate_png_sha_blocks_copied_views():\n"
        "    assert 'duplicate_png_sha'\n"
        "def test_shared_first_pre_spend_path_escape_symlink_and_noncanonical_are_blocked():\n"
        "    assert 'path rejected'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-script/scripts/boundary_review.py",
        "MUTATING_DECISIONS={'move_boundary'}\n"
        "def validate(entry):\n"
        "    applied_receipt=entry.get('applied_receipt')\n"
        "    previous_boundary_contract_sha256=applied_receipt.get('previous_boundary_contract_sha256') if applied_receipt else None\n"
        "    new_left_raw_sha256=applied_receipt.get('new_left_raw_sha256') if applied_receipt else None\n"
        "    new_right_raw_sha256=applied_receipt.get('new_right_raw_sha256') if applied_receipt else None\n"
        "    source_mapping=applied_receipt.get('source_mapping') if applied_receipt else None\n"
        "    return bool(applied_receipt and applied_receipt.get('status') == 'applied')\n",
    )
    _write(
        tmp_path,
        "skills/n2d-script/scripts/test_boundary_review.py",
        "def test_move_boundary_missing_receipt_is_unapplied():\n"
        "    entry={'decision':'move_boundary'}; assert not entry.get('applied_receipt')\n"
        "def test_mutating_decision_passes_only_after_new_sha_and_mapping_receipt():\n"
        "    receipt={'previous_boundary_contract_sha256':'old','new_left_raw_sha256':'left',"
        "'new_right_raw_sha256':'right','source_mapping':[{'from':'u1','to':'ep1'}]}; assert receipt\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/image_evidence.py",
        "import zlib\n"
        "def validate():\n"
        "    stream=zlib.decompressobj(); return 'png_iend_invalid png_scanline_data_incomplete'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/meta_audit.py",
        "import os\n"
        "def _atomic_write_text(path, content):\n"
        "    os.fsync(1); os.replace('tmp', path)\n"
        "def parser(ap): ap.add_argument(\"--out\")\n"
        "def run_registered_adversarial_tests(requested):\n"
        "    if not requested: return {\"status\": \"not_run\"}\n"
        "calibration_attempted=False; calibrations=[]; calibration_status='not_run'\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/test_meta_audit.py",
        "def test_run_tests_is_the_only_path_to_adversarially_tested_and_binds_current_sha():\n"
        "    assurance={'adversarially_tested': {'status': 'not_run'}}; assert assurance\n"
        "def test_official_mapping_is_grounding_but_never_link_only_calibration():\n"
        "    link_only_v2={'externally_calibrated': {'status': 'not_run'}}; assert link_only_v2\n"
        "def test_cli_out_matches_json_stdout_and_governance_findings_still_exit_zero():\n"
        "    assert 'same JSON and exit zero'\n"
        "no_blind_spot_claim_allowed=False\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/self_audit.py",
        "import os\n"
        "def _atomic_write_text(path, content):\n"
        "    os.fsync(1); os.replace('tmp', path)\n"
        "def parser(ap): ap.add_argument(\"--out\")\n",
    )
    _write(
        tmp_path,
        "skills/n2d-review/scripts/test_self_audit.py",
        "def test_cli_out_matches_json_stdout_and_preserves_block_exit():\n"
        "    assert 'same JSON and block exit'\n",
    )

    report = meta.audit(tmp_path)

    uncovered = [row for row in report["probes"] if row["status"] != "covered"]
    assert not uncovered, uncovered
    assert report["assurance"]["adversarial_test_coverage"]["covered"] > 0
    # Static test/guard text is defined-only.  No pytest receipt means it must
    # never be labelled adversarially-tested.
    assert report["assurance"]["adversarially_tested"]["status"] == "not_run"
    assert report["adversarial_runtime_receipt"]["requested"] is False
    # Even a completely covered registered checklist is not a proof that no
    # unknown counterexample exists.
    assert report["assurance"]["no_blind_spot_claim_allowed"] is False
    assert "不能表述" in report["assurance"]["blind_spot_statement"]


def test_run_tests_is_the_only_path_to_adversarially_tested_and_binds_current_sha(monkeypatch) -> None:
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return meta.subprocess.CompletedProcess(command, 0, stdout="17 passed\n", stderr="")

    monkeypatch.setattr(meta.subprocess, "run", fake_run)
    report = meta.audit(REPO_ROOT, run_tests=True)
    tested = report["assurance"]["adversarially_tested"]
    receipt = report["adversarial_runtime_receipt"]

    assert tested["status"] == "complete"
    assert tested["covered"] == tested["total"] == len(meta.BUILTIN_PROBES)
    assert receipt["requested"] is True
    assert receipt["exit_code"] == 0
    assert calls and calls[0][0][:4] == [meta.sys.executable, "-m", "pytest", "-q"]
    assert receipt["artifact_bindings"]
    for binding in receipt["artifact_bindings"]:
        assert _sha256(REPO_ROOT / binding["path"]) == binding["sha256"]


def test_run_tests_failure_cannot_be_reported_as_tested_complete(monkeypatch) -> None:
    monkeypatch.setattr(
        meta.subprocess,
        "run",
        lambda command, **kwargs: meta.subprocess.CompletedProcess(
            command, 1, stdout="1 failed\n", stderr="",
        ),
    )

    report = meta.audit(REPO_ROOT, run_tests=True)

    assert report["assurance"]["adversarially_tested"]["status"] == "failed"
    assert report["adversarial_runtime_receipt"]["exit_code"] == 1
    assert any(row["dim"] == "运行时对抗回归" for row in report["findings"])


def test_json_fixture_pack_is_pluggable_without_executing_code(tmp_path: Path) -> None:
    _write(tmp_path, "custom/guard.py", "def guard(): return 'safe'\n")
    _write(tmp_path, "custom/test_guard.py", "def test_mutation_is_caught(): assert True\n")
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "kind": "n2d_review_meta_fixture_pack",
                "version": 1,
                "claims": [
                    {
                        "id": "custom_claim",
                        "title": "custom",
                        "links": {
                            name: [{"path": "custom/guard.py", "patterns": ["guard"]}]
                            for name in meta.LINKS
                        },
                    }
                ],
                "probes": [
                    {
                        "id": "custom_mutation",
                        "claim_id": "custom_claim",
                        "description": "custom mutation",
                        "guard": [{"path": "custom/guard.py", "patterns": ["safe"]}],
                        "regression": [{"path": "custom/test_guard.py", "patterns": ["mutation_is_caught"]}],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = meta.audit(tmp_path, fixture_paths=[fixture])

    custom = next(row for row in report["claims"] if row["id"] == "custom_claim")
    probe = next(row for row in report["probes"] if row["id"] == "custom_mutation")
    assert custom["coverage"]["covered"] == 5
    assert probe["status"] == "covered"
    assert report["external_evidence"]["errors"] == []


def test_external_evidence_schema_rejects_market_post_hard_gate(tmp_path: Path) -> None:
    bad = tmp_path / "bad_evidence.json"
    bad.write_text(
        json.dumps(
            {
                "kind": "n2d_review_external_evidence",
                "version": 1,
                "evidence": [
                    {
                        "claim_id": "turnaround_alignment_enforcement",
                        "claim": "某市场帖说五视图更好",
                        "claim_type": "market_observation",
                        "source": {"title": "营销帖", "url": "https://example.invalid/post", "kind": "market_post"},
                        "checked_at": "2026-07-14",
                        "confidence": "low",
                        "implementation_mapping": [
                            {
                                "path": "skills/n2d-image/scripts/image_qc.py",
                                "symbol": "turnaround",
                                "enforcement": "block",
                                "rationale": "直接硬挡",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = meta.audit(tmp_path, evidence_paths=[bad])
    entry = report["external_evidence"]["entries"][0]

    assert not entry["valid"]
    assert any("不得直接映射 BLOCK" in issue for issue in entry["issues"])
    assert any("confidence=high" in issue for issue in entry["issues"])


def test_official_mapping_is_grounding_but_never_link_only_calibration(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "skills/n2d-image/scripts/image_qc.py",
        "def audit_turnaround_alignment(): pass\n",
    )
    good = tmp_path / "good_evidence.json"
    good.write_text(
        json.dumps(
            {
                "kind": "n2d_review_external_evidence",
                "version": 1,
                "evidence": [
                    {
                        "claim_id": "turnaround_alignment_enforcement",
                        "claim": "官方制作规范要求多视图同尺寸对齐",
                        "claim_type": "deterministic_contract",
                        "source": {"title": "official guide", "url": "https://example.invalid/official", "kind": "official"},
                        "checked_at": "2026-07-14",
                        "confidence": "high",
                        "implementation_mapping": [
                            {
                                "path": "skills/n2d-image/scripts/image_qc.py",
                                "symbol": "audit_turnaround_alignment",
                                "enforcement": "warn",
                                "rationale": "先作可复算几何证据与人审输入",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = meta.audit(tmp_path, evidence_paths=[good])

    entry = report["external_evidence"]["entries"][0]
    assert entry["valid"]
    assert entry["grounding_eligible"] is True
    assert report["assurance"]["externally_grounded"]["status"] == "partial"
    assert report["assurance"]["externally_calibrated"]["status"] == "not_run"
    assert report["external_evidence"]["calibrations"] == []
    assert not [row for row in report["findings"] if row["dim"] == "外部证据 schema"]

    # Merely bumping a link-only pack to v2 cannot manufacture calibration.
    v2 = json.loads(good.read_text(encoding="utf-8"))
    v2["version"] = 2
    good.write_text(json.dumps(v2, ensure_ascii=False), encoding="utf-8")
    link_only_v2 = meta.audit(tmp_path, evidence_paths=[good])
    assert link_only_v2["assurance"]["externally_grounded"]["status"] == "partial"
    assert link_only_v2["assurance"]["externally_calibrated"]["status"] == "not_run"


def test_market_observation_can_be_advisory_but_not_external_calibration(tmp_path: Path) -> None:
    _write(
        tmp_path,
        "skills/n2d-review/scripts/production_consistency.py",
        "def check_multiview_identity_pack(): pass\n",
    )
    advisory = tmp_path / "advisory_evidence.json"
    advisory.write_text(
        json.dumps(
            {
                "kind": "n2d_review_external_evidence",
                "version": 1,
                "evidence": [
                    {
                        "claim_id": "multiview_nested_failure",
                        "claim": "市场观察认为跨角度漂移常见",
                        "claim_type": "market_observation",
                        "source": {"title": "实战观察", "url": "https://example.invalid/market", "kind": "market_post"},
                        "checked_at": "2026-07-14",
                        "confidence": "low",
                        "implementation_mapping": [
                            {
                                "path": "skills/n2d-review/scripts/production_consistency.py",
                                "symbol": "check_multiview_identity_pack",
                                "enforcement": "warn",
                                "rationale": "只作为找反例的线索",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = meta.audit(tmp_path, evidence_paths=[advisory])
    entry = report["external_evidence"]["entries"][0]

    assert entry["valid"]
    assert entry["grounding_eligible"] is False
    assert report["assurance"]["externally_grounded"]["status"] == "not_run"
    assert report["assurance"]["externally_calibrated"]["status"] == "not_run"


def _calibration_artifacts(root: Path, stem: str) -> list[dict[str, str]]:
    rows = []
    for role in sorted(meta.CALIBRATION_ARTIFACT_ROLES):
        rel = f"calibration/{stem}/{role}.json"
        _write(root, rel, json.dumps({"role": role, "stem": stem}, ensure_ascii=False))
        rows.append({"role": role, "path": rel, "sha256": _sha256(root / rel)})
    return rows


def _complete_calibration(root: Path, claim_id: str, stem: str) -> dict:
    return {
        "claim_id": claim_id,
        "calibration_id": f"CAL-{stem}",
        "evaluated_at": "2026-07-14T09:00:00+08:00",
        "reviewer": {
            "reviewer_id": f"reviewer-{stem}",
            "affiliation": "independent-qc-lab",
            "independent_from_implementation": True,
            "independent_from_sample_selection": True,
            "conflict_of_interest": "none_declared",
        },
        "held_out": True,
        "blind_to_gate_result": True,
        "protocol": {
            "predeclared_at": "2026-07-13T09:00:00+08:00",
            "selection_locked_before_evaluation": True,
            "thresholds": {"max_fnr": 0.10, "max_fpr": 0.05},
            "sampling": {
                "method": "stratified_random",
                "population_description": "当前项目角色档位 × 镜头类型",
                "population_size": 1000,
                "sample_size": 100,
                "strata": [
                    {"name": "dialogue", "sample_count": 50, "selection_rule": "seeded random"},
                    {"name": "action", "sample_count": 50, "selection_rule": "seeded random"},
                ],
            },
        },
        "ground_truth": {
            "adjudication_method": "two-pass independent labels",
            "adjudicator_ids": [f"adjudicator-a-{stem}", f"adjudicator-b-{stem}"],
            "disagreement_resolution": "third adjudicator majority",
            "blind_to_gate_result": True,
            "adjudicators_independent_from_implementation": True,
        },
        "results": {
            "confusion_matrix": {"tp": 45, "tn": 48, "fp": 2, "fn": 5},
            "fnr": 0.10,
            "fpr": 0.04,
        },
        "artifacts": _calibration_artifacts(root, stem),
    }


def _write_v2_pack(path: Path, calibrations: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "kind": "n2d_review_external_evidence",
                "version": 2,
                "evidence": [],
                "calibrations": calibrations,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_calibration_missing_held_out_blind_or_independence_is_invalid(tmp_path: Path) -> None:
    calibration = _complete_calibration(
        tmp_path, "turnaround_alignment_enforcement", "missing-contract",
    )
    calibration.pop("held_out")
    calibration.pop("blind_to_gate_result")
    calibration["reviewer"].pop("independent_from_implementation")
    pack = tmp_path / "invalid_calibration.json"
    _write_v2_pack(pack, [calibration])

    report = meta.audit(tmp_path, evidence_paths=[pack])
    row = report["external_evidence"]["calibrations"][0]

    assert row["status"] == "invalid"
    assert report["assurance"]["externally_calibrated"]["status"] == "invalid"
    assert any("held_out" in issue for issue in row["issues"])
    assert any("blind_to_gate_result" in issue for issue in row["issues"])
    assert any("independent_from_implementation" in issue for issue in row["issues"])


def test_partial_and_failed_calibrations_do_not_become_complete(tmp_path: Path) -> None:
    first = _complete_calibration(tmp_path, "multiview_nested_failure", "partial-a")
    partial_pack = tmp_path / "partial.json"
    _write_v2_pack(partial_pack, [first])

    partial = meta.audit(tmp_path, evidence_paths=[partial_pack])
    assert partial["assurance"]["externally_calibrated"]["status"] == "partial"

    failed = _complete_calibration(tmp_path, "turnaround_alignment_enforcement", "failed-b")
    failed["results"] = {
        "confusion_matrix": {"tp": 40, "tn": 48, "fp": 2, "fn": 10},
        "fnr": 0.20,
        "fpr": 0.04,
    }
    failed_pack = tmp_path / "failed.json"
    _write_v2_pack(failed_pack, [first, failed])

    failed_report = meta.audit(tmp_path, evidence_paths=[failed_pack])
    assert failed_report["external_evidence"]["calibrations"][1]["status"] == "failed"
    assert failed_report["assurance"]["externally_calibrated"]["status"] == "failed"


def test_complete_calibration_requires_every_external_claim_and_current_artifact_sha(tmp_path: Path) -> None:
    calibrations = [
        _complete_calibration(tmp_path, "multiview_nested_failure", "complete-a"),
        _complete_calibration(tmp_path, "turnaround_alignment_enforcement", "complete-b"),
        _complete_calibration(tmp_path, "review_assurance_separation", "complete-c"),
        _complete_calibration(tmp_path, "chapter_boundary_semantic_contract", "complete-d"),
    ]
    pack = tmp_path / "complete.json"
    _write_v2_pack(pack, calibrations)

    report = meta.audit(tmp_path, evidence_paths=[pack])
    assurance = report["assurance"]["externally_calibrated"]

    assert assurance["status"] == "complete"
    assert assurance["covered"] == assurance["total"] == 4
    assert all(row["status"] == "passed" for row in report["external_evidence"]["calibrations"])
    assert not [row for row in report["findings"] if row["dim"] == "外部校准合同"]

    artifact = tmp_path / calibrations[0]["artifacts"][0]["path"]
    artifact.write_text("changed after calibration", encoding="utf-8")
    stale = meta.audit(tmp_path, evidence_paths=[pack])
    assert stale["assurance"]["externally_calibrated"]["status"] == "invalid"
    assert any(
        "SHA 已过期" in issue
        for issue in stale["external_evidence"]["calibrations"][0]["issues"]
    )


def test_evidence_schema_exposes_required_provenance_fields() -> None:
    item = meta.EXTERNAL_EVIDENCE_SCHEMA["properties"]["evidence"]["items"]
    assert {
        "claim_id", "claim", "source", "checked_at", "confidence", "implementation_mapping"
    } <= set(item["required"])
    assert meta.EXTERNAL_EVIDENCE_SCHEMA["properties"]["version"]["enum"] == [1, 2]
    calibration = meta.EXTERNAL_EVIDENCE_SCHEMA["properties"]["calibrations"]["items"]
    assert {"held_out", "blind_to_gate_result", "protocol", "ground_truth", "results", "artifacts"} <= set(
        calibration["required"]
    )


def test_self_audit_embeds_assurance_and_disallows_zero_warn_overclaim() -> None:
    report = self_audit.audit(REPO_ROOT)
    assurance = report["assurance"]

    assert set(("self_checked", "adversarially_tested", "externally_calibrated")) <= set(assurance)
    assert "externally_grounded" in assurance
    assert assurance["no_blind_spot_claim_allowed"] is False
    assert report["meta_audit"]["kind"] == "n2d_review_meta_audit"
    rendered = self_audit.render_markdown(report)
    assert "结论可信层级" in rendered
    assert "不能表述" in rendered
    assert "无盲区" in assurance["blind_spot_statement"]
    assert "无偏" in assurance["blind_spot_statement"]


def test_cli_out_matches_json_stdout_and_governance_findings_still_exit_zero(
    tmp_path: Path,
    capsys,
) -> None:
    _vulnerable_repo(tmp_path)
    destination = tmp_path / "audit" / "receipts" / "meta.json"

    exit_code = meta.main([
        "--root",
        str(tmp_path),
        "--json",
        "--out",
        str(destination),
    ])
    stdout = capsys.readouterr().out
    written = destination.read_text(encoding="utf-8")
    report = json.loads(written)

    assert exit_code == 0
    assert written == stdout
    assert report["kind"] == "n2d_review_meta_audit"
    assert report["root"] == str(tmp_path.resolve())
    assert report["counts"]["warn"] > 0
