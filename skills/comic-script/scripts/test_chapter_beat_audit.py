"""chapter_beat_audit 单测。运行：cd skills/comic-script/scripts && python -m pytest test_chapter_beat_audit.py"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("chapter_beat_audit.py")
spec = importlib.util.spec_from_file_location("chapter_beat_audit", SCRIPT)
ba = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ba)


def _panels(funcs):
    return [{"panel_id": f"P{i:03d}", "story_function": f} for i, f in enumerate(funcs, 1)]


def test_healthy_chapter_passes_beats():
    funcs = ["opening_hook"] + ["build"] * 12 + ["action_peak"] + ["reaction"] * 5 + ["cliffhanger"]
    findings = ba.audit_beats(_panels(funcs))
    codes = {f["code"] for f in findings}
    assert "missing_opening_hook" not in codes
    assert "weak_ending" not in codes
    assert "climax_too_early" not in codes
    assert "panel_count_below_platform_floor" not in codes  # 20 格恰达门槛


def test_flat_ending_is_must():
    funcs = ["opening_hook"] + ["build"] * 20 + ["farewell"]
    findings = ba.audit_beats(_panels(funcs))
    assert any(f["code"] == "weak_ending" and f["severity"] == "must" for f in findings)


def test_climax_too_early_warns():
    funcs = ["opening_hook", "build", "action_peak"] + ["talk"] * 16 + ["cliffhanger"]
    findings = ba.audit_beats(_panels(funcs))
    assert any(f["code"] == "climax_too_early" for f in findings)


def test_panel_count_band():
    few = ba.audit_beats(_panels(["opening_hook"] + ["build"] * 8 + ["cliffhanger"]))
    assert any(f["code"] == "panel_count_below_platform_floor" for f in few)
    many = ba.audit_beats(_panels(["opening_hook"] + ["build"] * 40 + ["action_peak"] * 20 + ["cliffhanger"]))
    assert any(f["code"] == "panel_count_above_weekly_norm" for f in many)


def test_blueprint_missing_and_valid(tmp_path):
    (tmp_path / "脚本" / "第1话").mkdir(parents=True)
    findings = ba.audit_blueprint(tmp_path)
    assert any(f["code"] == "split_blueprint_missing" for f in findings)
    (tmp_path / "脚本" / "split_blueprint.json").write_text(json.dumps({
        "chapters": [{"chapter": "第1话", "source_range": "第一回前半", "ending_hook": "虎啸"}],
    }, ensure_ascii=False), encoding="utf-8")
    assert ba.audit_blueprint(tmp_path) == []
