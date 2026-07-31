"""chapter_beat_audit v2 tests."""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("chapter_beat_audit.py")
spec = importlib.util.spec_from_file_location("chapter_beat_audit", SCRIPT)
ba = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ba)


def _panels(funcs):
    return [{"panel_id": f"P{i:03d}", "story_function": function} for i, function in enumerate(funcs, 1)]


def _contract(**updates):
    data = {
        "chapter": "第1话",
        "chapter_type": "serial",
        "format_profile": "vertical_serial",
        "source_mode": "original",
        "source_spans": [],
        "reader_promise": "反击",
        "core_conflict": "救人与封锁",
        "turning_point": "旧友现身",
        "payoff": "打开出口",
        "ending_mode": "cliffhanger",
        "budget": {"unit": "panels", "soft_range": [10, 30]},
        "entry_state": {"story": "trapped"},
        "continuity_delta": [{"entity_id": "STORY_MAIN", "field": "state", "from": "trapped", "to": "escaped", "panel_id": "P001", "reason": "door opened"}],
        "exit_state": {"story": "escaped"},
        "status": "confirmed",
    }
    data.update(updates)
    return data


def test_healthy_chapter_has_no_ending_or_opening_warning():
    funcs = ["opening_hook"] + ["build"] * 12 + ["action_peak"] + ["reaction"] * 5 + ["cliffhanger"]
    findings = ba.audit_beats(_panels(funcs), contract=_contract())
    codes = {finding["code"] for finding in findings}
    assert "missing_opening_hook" not in codes
    assert "ending_mode_mismatch" not in codes


def test_flat_ending_is_heuristic_warn_not_hard_block():
    findings = ba.audit_beats(_panels(["opening_hook", "turning_point", "farewell"]), contract=_contract())
    ending = next(finding for finding in findings if finding["code"] == "ending_mode_mismatch")
    assert ending["severity"] == "warn"
    assert ending["confidence"] == "heuristic"


def test_story_function_matching_is_exact_not_substring():
    findings = ba.audit_beats(
        _panels(["opening_hookish", "build", "not_a_cliffhanger"]),
        contract=_contract(),
    )
    codes = {finding["code"] for finding in findings}
    assert "missing_opening_hook" in codes
    assert "ending_mode_mismatch" in codes


def test_yonkoma_does_not_inherit_twenty_panel_or_cliffhanger_rule():
    contract = _contract(
        chapter_type="gag",
        format_profile="yonkoma",
        ending_mode="gag_payoff",
        budget={"unit": "rows", "target": 4, "soft_range": [4, 4]},
        entry_state=None,
        continuity_delta=None,
        exit_state=None,
    )
    findings = ba.audit_beats(
        _panels(["setup", "development", "turning_point", "punchline"]),
        contract=contract,
        target_platform="快看",
    )
    codes = {finding["code"] for finding in findings}
    assert "ending_mode_mismatch" not in codes
    assert "kuaikan_submission_panel_floor" not in codes
    assert "no_climax_panel" not in codes


def test_twenty_panel_floor_only_applies_to_kuaikan_profile():
    panels = _panels(["opening_hook"] + ["build"] * 7 + ["cliffhanger"])
    generic = ba.audit_beats(panels, contract=_contract())
    kuaikan = ba.audit_beats(panels, contract=_contract(), target_platform="快看漫画")
    assert not any(finding["code"] == "kuaikan_submission_panel_floor" for finding in generic)
    assert any(finding["code"] == "kuaikan_submission_panel_floor" for finding in kuaikan)


def test_soft_budget_is_advisory_only():
    findings = ba.audit_beats(
        _panels(["opening_hook", "payoff", "cliffhanger"]),
        contract=_contract(budget={"unit": "panels", "soft_range": [20, 60]}),
    )
    budget = next(finding for finding in findings if finding["code"] == "panel_count_below_soft_budget")
    assert budget["severity"] == "warn"


def test_blueprint_missing_and_v1_are_deterministic_migration_gaps(tmp_path):
    (tmp_path / "脚本" / "第1话").mkdir(parents=True)
    assert any(finding["code"] == "split_blueprint_missing" for finding in ba.audit_blueprint(tmp_path))
    (tmp_path / "脚本" / "split_blueprint.json").write_text(json.dumps({
        "kind": "comic_split_blueprint", "version": 1,
        "chapters": [{"chapter": "第1话", "source_range": "第一回"}],
    }, ensure_ascii=False), encoding="utf-8")
    findings = ba.audit_blueprint(tmp_path)
    assert any(finding["code"] == "split_blueprint_v1_legacy" and finding["severity"] == "must" for finding in findings)


def test_valid_v2_contract_passes_blueprint_audit(tmp_path):
    (tmp_path / "脚本").mkdir(parents=True)
    (tmp_path / "脚本" / "split_blueprint.json").write_text(json.dumps({
        "kind": "comic_split_blueprint", "version": 2, "status": "confirmed",
        "chapters": [_contract()],
    }, ensure_ascii=False), encoding="utf-8")
    assert ba.audit_blueprint(tmp_path) == []
