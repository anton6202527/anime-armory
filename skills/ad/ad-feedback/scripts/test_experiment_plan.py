import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import experiment_plan as ep  # noqa: E402


def _plan():
    return {
        "hypothesis": "更直接的产品钩子提升 CTR",
        "primary_kpi": "CTR", "conversion_event": "purchase", "attribution_window": "7d_click",
        "platform": "TikTok", "placement": "auction_in_feed", "audience": "prospecting-cn", "start_date": "2026-07-12",
        "end_date": "2026-08-23", "min_impressions": 5000,
        "randomization_unit": "platform_user_bucket", "decision_rule": "平台显著性结果优先；否则只作方向性读取",
        "held_constant": {"budget": "50/50", "bidding": "same", "landing_page": "same", "placement": "auction_in_feed"},
        "variants": [
            {"variant_id": "A", "hook_id": "H1", "message_id": "M1", "cta_id": "C1", "allocation": 0.5,
             "asset_path": "variants/A.mp4", "asset_sha256": "a" * 64},
            {"variant_id": "B", "hook_id": "H2", "message_id": "M1", "cta_id": "C1", "allocation": 0.5,
             "asset_path": "variants/B.mp4", "asset_sha256": "b" * 64},
        ],
    }


def test_single_variable_plan_passes():
    payload = ep.build(_plan())
    assert payload["summary"]["approved"] is True
    assert payload["changed_dimension"] == "hook_id"


def test_multi_variable_plan_blocks():
    plan = _plan()
    plan["variants"][1]["message_id"] = "M2"
    payload = ep.build(plan)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "not_single_variable" for f in payload["findings"])


def test_invalid_allocation_is_reported_not_crashed():
    plan = _plan()
    plan["variants"][1]["allocation"] = "not-a-number"
    payload = ep.build(plan)
    assert payload["summary"]["approved"] is False
    assert any(f["code"] == "allocation_not_numeric" for f in payload["findings"])


def test_variant_media_hash_must_bind_actual_file(tmp_path):
    plan = _plan()
    payload = ep.build(plan, tmp_path)
    assert any(f["code"] == "variant_asset_binding_stale" for f in payload["findings"])
