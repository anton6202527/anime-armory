"""consistency_audit.summarize 纯函数单测（无依赖）。
cd skills/n2d-review/scripts && python -m pytest test_consistency_audit.py
"""
import consistency_audit as ca


def test_summarize_counts_and_total_block():
    sections = {
        "脸(G1)": {"skipped": False, "verdicts": ["ok", "ok", "block", "warn"]},
        "服装配色(N1)": {"skipped": False, "verdicts": ["ok", "block"]},
        "片内时序(N2)": {"skipped": True, "verdicts": []},
    }
    s = ca.summarize(sections)
    assert s["total_block"] == 2
    assert s["by_dim"]["脸(G1)"] == {"block": 1, "warn": 1, "ok": 2, "n": 4, "skipped": False}
    assert s["by_dim"]["服装配色(N1)"]["block"] == 1
    assert s["by_dim"]["片内时序(N2)"]["skipped"] is True
    assert s["by_dim"]["片内时序(N2)"]["n"] == 0


def test_summarize_empty():
    s = ca.summarize({})
    assert s["total_block"] == 0 and s["by_dim"] == {}
