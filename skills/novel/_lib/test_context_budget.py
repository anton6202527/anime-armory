from __future__ import annotations

from context_budget import allocate_sections


def test_required_obligations_survive_and_low_priority_context_drops() -> None:
    allocated, receipt = allocate_sections([
        {"id": "facts", "text": "F" * 400, "required": True, "priority": 100, "obligations": ["continuity"]},
        {"id": "research", "text": "R" * 400, "priority": 80},
        {"id": "prediction", "text": "P" * 400, "priority": 5},
    ], max_chars=700, reserved_chars=100, minimum_slice=100)
    assert allocated["facts"] == "F" * 400
    assert allocated["research"]
    assert allocated["prediction"] == ""
    assert receipt["obligation_coverage"]["continuity"] == "covered"


def test_required_overflow_is_explicit_not_silently_clipped() -> None:
    allocated, receipt = allocate_sections([
        {"id": "knowledge", "text": "K" * 800, "required": True, "obligations": ["knowledge_state"]},
    ], max_chars=500)
    assert len(allocated["knowledge"]) == 800
    assert receipt["over_budget_due_to_required"] is True
