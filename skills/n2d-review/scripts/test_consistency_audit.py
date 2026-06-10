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


def test_section_details_keep_return_scope():
    sec = ca.section_from_result(
        dim="状态百科(P1)",
        result={"alerts": [{"verdict": "warn", "shot": 3, "message": "漏写左颊新伤"}], "notes": []},
        detail_key="alerts",
        skipped=False,
        ep="第1集",
        stage="image",
        default_artifacts=("出图/第1集/prompt/01_分镜出图.md",),
    )
    assert sec["verdicts"] == ["warn"]
    assert sec["details"][0]["affected_shots"] == ["Clip_03"]
    assert "出图/第1集/prompt/01_分镜出图.md" in sec["details"][0]["affected_artifacts"]


def test_auto_return_tasks_group_details():
    sections = {
        "状态百科(P1)": {
            "return_to_stage": "image",
            "rerun_scope": "修状态锁",
            "details": [{
                "verdict": "warn",
                "message": "漏写状态",
                "affected_shots": ["Clip_03"],
                "affected_artifacts": ["出图/第1集/prompt/01_分镜出图.md"],
            }],
        }
    }
    tasks = ca.build_auto_return_tasks(sections)
    assert tasks[0]["return_to_stage"] == "image"
    assert tasks[0]["affected_shots"] == ["Clip_03"]
    assert "定位镜头：Clip_03" in tasks[0]["scope"]
