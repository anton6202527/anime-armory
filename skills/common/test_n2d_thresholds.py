"""从本目录跑：cd skills/common && python -m pytest test_n2d_thresholds.py

告警阈值单一真值源（n2d-dashboard 写/告警、n2d-score 读通过率下限共用）。
重点覆盖历史 bug：floor 只设在 _设置.md 时也要被读到（不只 json）。
"""
import json
import os

import n2d_thresholds as t


def _work(tmp_path):
    (tmp_path / "生产数据").mkdir(parents=True, exist_ok=True)
    return str(tmp_path)


def test_defaults_when_nothing_set(tmp_path):
    cfg = t.load_thresholds(_work(tmp_path))
    assert cfg["final_pass_rate_floor"] is None
    assert cfg["qa_blockers_ceiling"] == 0          # 默认只对 QA 阻断开箱即告
    assert cfg["budget_warn_ratio"] == 0.8


def test_floor_from_settings_md_only(tmp_path):
    # 历史 bug：floor 只在 _设置.md（无 json）也要生效
    root = _work(tmp_path)
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write("- 告警通过率下限: 80%\n")
    assert t.load_thresholds(root)["final_pass_rate_floor"] == 0.8


def test_json_overrides_settings(tmp_path):
    root = _work(tmp_path)
    open(os.path.join(root, "_设置.md"), "w", encoding="utf-8").write("告警通过率下限：0.6\n")
    json.dump({"final_pass_rate_floor": 0.9},
              open(os.path.join(root, "生产数据", t.THRESHOLDS_FILE), "w", encoding="utf-8"))
    assert t.load_thresholds(root)["final_pass_rate_floor"] == 0.9   # json 优先于 _设置.md


def test_env_overrides_budget_cap(tmp_path):
    root = _work(tmp_path)
    os.environ["N2D_ALERT_BUDGET_CAP"] = "123"
    try:
        assert t.load_thresholds(root)["budget_cap"] == 123.0
    finally:
        del os.environ["N2D_ALERT_BUDGET_CAP"]


def test_parse_ratio_forms():
    assert t.parse_ratio("80%") == 0.8
    assert t.parse_ratio("0.5") == 0.5
    assert t.parse_ratio("") is None
    assert t.parse_ratio(None) is None
    assert t.parse_ratio("abc") is None


def test_benchmark_defaults_are_loaded_from_reference_file(tmp_path):
    root = _work(tmp_path)
    cfg = t.load_benchmark(root)
    assert cfg["one_pass_rate"] == 0.9
    assert cfg["redraw_rate"] == 0.1
    assert cfg["collected"] == "2026-06"
    assert cfg.get("sources")


def test_project_benchmark_json_overrides_reference(tmp_path):
    root = _work(tmp_path)
    json.dump(
        {"one_pass_rate": 0.75, "redraw_rate": 0.2, "collected": "local"},
        open(os.path.join(root, "生产数据", t.BENCHMARK_FILE), "w", encoding="utf-8"),
    )
    cfg = t.load_benchmark(root)
    assert cfg["one_pass_rate"] == 0.75
    assert cfg["redraw_rate"] == 0.2
    assert cfg["collected"] == "local"
