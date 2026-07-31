"""portfolio 聚合纯函数单测。
cd skills/n2d/n2d-dashboard/scripts && python -m pytest test_portfolio.py
"""
import portfolio as pf


def _work(name, *, eps, fin_ep, fin_min, cost, attempts=0, one_pass=0, redraw=0,
          plays=0, net=None, first=None, last=None):
    return {"name": name, "finished_episodes": fin_ep, "finished_min": fin_min,
            "first_ts": first, "last_ts": last,
            "totals": {"episode_count": eps, "generation_attempts": attempts,
                       "one_pass_count": one_pass, "redraw_count": redraw,
                       "cost_totals": cost, "release_plays": plays,
                       "release_net_totals": net or {}}}


def test_cost_summed_per_unit_across_works():
    p = pf.aggregate_portfolio([
        _work("A", eps=2, fin_ep=2, fin_min=4.0, cost={"积分": 1200, "CNY": 5.0}),
        _work("B", eps=3, fin_ep=1, fin_min=2.0, cost={"积分": 800}),
    ])
    assert p["cost_totals"] == {"积分": 2000.0, "CNY": 5.0}
    assert p["total_finished_episodes"] == 3 and p["total_finished_min"] == 6.0


def test_cost_per_finished_min_portfolio():
    p = pf.aggregate_portfolio([_work("A", eps=1, fin_ep=1, fin_min=4.0, cost={"积分": 2000})])
    assert p["cost_per_finished_min"]["积分"] == 500.0  # 2000/4


def test_weighted_one_pass_rate_not_simple_average():
    # A: 1/10, B: 9/10 → 加权 10/20=0.5（简单平均会是 0.5 也巧合，故用不等样本）
    p = pf.aggregate_portfolio([
        _work("A", eps=1, fin_ep=1, fin_min=1, cost={}, attempts=100, one_pass=10),
        _work("B", eps=1, fin_ep=1, fin_min=1, cost={}, attempts=10, one_pass=9),
    ])
    assert p["one_pass_rate"] == round(19 / 110, 4)  # 加权（19/110），非 (0.1+0.9)/2=0.5


def test_throughput_from_calendar_span():
    p = pf.aggregate_portfolio([
        _work("A", eps=4, fin_ep=4, fin_min=8, cost={}, first="2026-06-01T00:00:00", last="2026-06-05T00:00:00"),
    ])
    th = p["throughput"]
    assert th["span_days"] == 4.0
    assert th["episodes_per_day"] == 1.0          # 4 集 / 4 天
    assert th["finished_min_per_day"] == 2.0      # 8 分钟 / 4 天


def test_throughput_span_floor_avoids_astronomical_rate():
    # 同一时刻出 3 集 → 跨度地板=1小时，不算出天文吞吐
    p = pf.aggregate_portfolio([
        _work("A", eps=3, fin_ep=3, fin_min=6, cost={}, first="2026-06-01T10:00:00", last="2026-06-01T10:00:00"),
    ])
    assert p["throughput"]["span_days"] == round(1 / 24, 2)


def test_recoup_ratio_per_unit():
    p = pf.aggregate_portfolio([
        _work("A", eps=1, fin_ep=1, fin_min=1, cost={"CNY": 100}, net={"CNY": 250}),
    ])
    assert p["recoup_ratio"]["CNY"] == 2.5


def test_empty_portfolio():
    p = pf.aggregate_portfolio([])
    assert p["work_count"] == 0 and p["cost_totals"] == {} and p["throughput"]["episodes_per_day"] is None


def test_span_days_missing_endpoint():
    assert pf.span_days(None, "2026-06-01T00:00:00") is None
    assert pf.span_days("2026-06-01T00:00:00", "2026-06-02T00:00:00") == 1.0


# ── P2-2: 舰队 QA/一致性阻断 roll-up + 先动哪部排名 ──────────────────────────
def _work_q(name, *, attempts=0, one_pass=0, qa=0, qa_warn=0, cons=0, cons_warn=0, net=None):
    return {"name": name, "finished_episodes": 1, "finished_min": 2.0,
            "first_ts": None, "last_ts": None,
            "totals": {"episode_count": 1, "generation_attempts": attempts,
                       "one_pass_count": one_pass, "redraw_count": 0,
                       "cost_totals": {}, "release_plays": 0,
                       "qa_blockers": qa, "qa_warnings": qa_warn,
                       "consistency_blockers": cons, "consistency_warnings": cons_warn,
                       "release_net_totals": net or {}}}


def test_blocker_rollup_summed_across_works():
    p = pf.aggregate_portfolio([
        _work_q("A", qa=2, cons=1),
        _work_q("B", qa=3, cons=0),
    ])
    assert p["qa_blockers_total"] == 5
    assert p["consistency_blockers_total"] == 1


def test_gate_noise_rollup_and_ranking():
    p = pf.aggregate_portfolio([
        _work_q("低噪", attempts=20, qa=1, qa_warn=2, cons_warn=1),
        _work_q("高噪", attempts=10, qa=0, qa_warn=8, cons_warn=3),
    ])
    assert p["qa_warnings_total"] == 10
    assert p["consistency_warnings_total"] == 4
    assert p["gate_noise"]["warnings_per_attempt"] == round(10 / 30, 4)
    assert p["gate_noise"]["blockers_per_attempt"] == round(1 / 30, 4)
    noisy = p["rankings"]["highest_gate_noise"][0]
    assert noisy["work"] == "高噪"
    assert noisy["warnings_per_attempt"] == 0.8


def test_worst_one_pass_ranking_lowest_first():
    p = pf.aggregate_portfolio([
        _work_q("好", attempts=10, one_pass=9),   # 0.9
        _work_q("差", attempts=10, one_pass=3),   # 0.3
        _work_q("中", attempts=10, one_pass=6),   # 0.6
    ])
    assert p["rankings"]["worst_one_pass"][0]["work"] == "差"


def test_most_blockers_ranking_and_filter():
    p = pf.aggregate_portfolio([
        _work_q("清白", qa=0, cons=0),
        _work_q("重债", qa=4, cons=2),
        _work_q("轻债", qa=1, cons=0),
    ])
    mb = [r["work"] for r in p["rankings"]["most_blockers"]]
    assert mb[0] == "重债"
    assert "清白" not in mb  # 0 阻断不进榜


def test_losing_money_ranking():
    p = pf.aggregate_portfolio([
        _work_q("赚", net={"CNY": 100}),
        _work_q("亏", net={"CNY": -50}),
    ])
    assert [r["work"] for r in p["rankings"]["losing_money"]] == ["亏"]


def test_render_md_shows_qa_debt_and_rankings():
    p = pf.aggregate_portfolio([_work_q("亏剧", attempts=10, one_pass=2, qa=3, qa_warn=4, cons=1, net={"CNY": -20})])
    md = pf.render_md(p)
    assert "QA 债" in md and "Gate 噪声" in md and "在亏钱的剧" in md and "先动哪部" in md


def test_parse_ts_normalizes_mixed_timezones():
    import portfolio as pf
    # +08:00 的 08:00 == Z 的 00:00（同一瞬间）；字典序会排错，UTC 归一后相等。
    assert pf._parse_ts("2026-01-01T08:00:00+08:00") == pf._parse_ts("2026-01-01T00:00:00Z")
    # 混时区 span 不再 TypeError 且数值正确（2 天）。
    assert abs(pf.span_days("2026-01-01T00:00:00Z", "2026-01-03T08:00:00+08:00") - 2.0) < 1e-6


def test_active_days_is_backfill_robust():
    import portfolio as pf
    works = [
        {"name": "A", "finished_episodes": 3, "finished_min": 10, "totals": {},
         "first_ts": "2026-01-01T10:00:00+08:00", "last_ts": "2026-01-02T10:00:00+08:00",
         "active_dates": ["2026-01-01", "2026-01-02"]},
        {"name": "B", "finished_episodes": 2, "finished_min": 6, "totals": {},
         "first_ts": "2026-01-02T10:00:00+08:00", "last_ts": "2026-01-03T10:00:00+08:00",
         "active_dates": ["2026-01-02", "2026-01-03"]},
    ]
    th = pf.aggregate_portfolio(works)["throughput"]
    assert th["active_days"] == 3                       # 01-01/02/03 并集
    assert th["episodes_per_active_day"] == round(5 / 3, 3)
    assert th["first_event"] == "2026-01-01T10:00:00+08:00"
