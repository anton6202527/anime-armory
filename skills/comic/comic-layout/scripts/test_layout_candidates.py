from layout_candidates import score


def test_score_penalizes_bubble_overload_and_repetition():
    good = {"segments": [{"panels": [{"panel_shape": "wide", "eye_flow_entry": "top", "bubble_slots": []}, {"panel_shape": "close", "page_turn_hook": "reveal", "bubble_slots": []}]}]}
    bad = {"segments": [{"panels": [{"panel_shape": "same", "bubble_slots": [{}, {}, {}, {}, {}]}, {"panel_shape": "same", "bubble_slots": []}]}]}
    assert score(good)["total"] > score(bad)["total"]
