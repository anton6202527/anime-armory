from finding_triage import triage


def test_routes_deterministic_uncertain_and_hard():
    result = triage({"issues": [
        {"code": "sha_mismatch"}, {"code": "style_drift"}, {"code": "rights_unverified"},
    ]})
    assert result["counts"] == {"deterministic_repair": 1, "targeted_review": 1, "receipt_bound_noop": 0, "hard_boundary": 1}
