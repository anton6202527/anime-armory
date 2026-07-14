import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("chapter_contract.py")
spec = importlib.util.spec_from_file_location("chapter_contract", SCRIPT)
cc = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(cc)


def _entry(**updates):
    data = {
        "chapter": "第一话",
        "chapter_type": "serial",
        "format_profile": "vertical_serial",
        "source_mode": "adapted",
        "source_spans": [{"source_path": "源本/story.md", "start": "第十一回", "end": "第十三回"}],
        "reader_promise": "反击",
        "core_conflict": "封锁",
        "turning_point": "旧友出现",
        "payoff": "出口打开",
        "ending_mode": "decision",
        "budget": {"unit": "panels", "soft_range": [24, 48]},
        "entry_state": {"story": "trapped"},
        "continuity_delta": [{"entity_id": "STORY_MAIN", "field": "state", "from": "trapped", "to": "escaped", "panel_id": "P001", "reason": "door opened"}],
        "exit_state": {"story": "escaped"},
        "status": "confirmed",
    }
    data.update(updates)
    return data


def test_chinese_numbers_and_chapter_normalization():
    assert cc.chinese_number_to_int("十二") == 12
    assert cc.chinese_number_to_int("一百零二") == 102
    assert cc.parse_numbered_label("第十二回 风雪") == (12, "回")
    assert cc.normalize_chapter("第一话") == "第1话"


def test_select_cross_unit_range_is_inclusive():
    text = "第一回 一\n正文一\n第二回 二\n正文二\n第三回 三\n正文三\n第四回 四\n正文四"
    selected, labels, error = cc.select_unit_range(text, "第一回", "第三回")
    assert error is None
    assert labels == ["第1回", "第2回", "第3回"]
    assert "正文一" in selected and "正文三" in selected
    assert "正文四" not in selected


def test_missing_middle_source_unit_is_deterministic_error():
    text = "第一章 一\n正文一\n第三章 三\n正文三"
    _, labels, error = cc.select_unit_range(text, "第一章", "第三章")
    assert labels == ["第1章", "第3章"]
    assert error == "source_span_units_missing"


def test_blueprint_rejects_sequence_gap_and_hard_budget():
    first = _entry()
    third = _entry(chapter="第3话", budget={"unit": "panels", "hard_min": 20})
    issues = cc.validate_blueprint({
        "kind": "comic_split_blueprint", "version": 2,
        "chapters": [first, third],
    })
    codes = {issue["code"] for issue in issues}
    assert "chapter_sequence_gap" in codes
    assert "hard_budget_forbidden" in codes


def test_serial_requires_state_triplet_but_one_shot_does_not():
    serial = _entry()
    serial.pop("exit_state")
    assert any(issue["code"] == "exit_state_missing" for issue in cc.validate_chapter_entry(serial, 0))
    standalone = _entry(
        chapter_type="one_shot", source_mode="original", source_spans=[],
        entry_state=None, continuity_delta=None, exit_state=None,
    )
    assert not any(issue["code"].endswith("_state_missing") for issue in cc.validate_chapter_entry(standalone, 0))
