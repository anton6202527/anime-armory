"""comic development_pack 单测。运行：cd skills/comic/comic-script/scripts && python -m pytest test_development_pack.py"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("development_pack.py")
spec = importlib.util.spec_from_file_location("comic_development_pack", SCRIPT)
dp = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(dp)


def test_scaffold_creates_but_never_overwrites(tmp_path):
    created = dp.scaffold(tmp_path, write=True)
    assert len(created) == 3
    strategy = tmp_path / "开发包" / "adaptation_strategy.json"
    strategy.write_text('{"kind":"comic_adaptation_strategy","status":"confirmed","custom":1}', encoding="utf-8")
    again = dp.scaffold(tmp_path, write=True)
    assert again == []
    assert json.loads(strategy.read_text(encoding="utf-8"))["custom"] == 1


def test_check_blocks_on_placeholder_confirmed(tmp_path):
    dp.scaffold(tmp_path, write=True)
    strategy = tmp_path / "开发包" / "adaptation_strategy.json"
    data = json.loads(strategy.read_text(encoding="utf-8"))
    data["status"] = "confirmed"
    strategy.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report = dp.check_pack(tmp_path)
    assert report["status"] == "blocked"
    assert any(g["code"] == "adaptation_strategy_placeholder_in_confirmed" for g in report["gaps"])


def _fill_confirmed(tmp_path):
    dp.scaffold(tmp_path, write=True)
    for key, path in dp.pack_files(tmp_path).items():
        if key == "signoff":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False).replace("待补", "已填内容").replace("待填", "已填")
        data = json.loads(text)
        data["status"] = "confirmed"
        if key == "split_blueprint":
            data["chapters"][0]["status"] = "confirmed"
            source_path = tmp_path / data["chapters"][0]["source_spans"][0]["source_path"]
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text("第1章\n正文", encoding="utf-8")
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_check_requires_signoff_with_current_sha(tmp_path):
    _fill_confirmed(tmp_path)
    report = dp.check_pack(tmp_path)
    assert any(g["code"] == "signoff_missing" for g in report["gaps"])
    hashes = report["file_sha256"]
    (tmp_path / "开发包" / "signoff.json").write_text(json.dumps({
        "reviewer": "编辑甲", "role": "creative", "time": "2026-07-12",
        "file_sha256": hashes}, ensure_ascii=False), encoding="utf-8")
    report2 = dp.check_pack(tmp_path)
    assert report2["status"] == "confirmed"
    strategy = tmp_path / "开发包" / "adaptation_strategy.json"
    data = json.loads(strategy.read_text(encoding="utf-8"))
    data["adaptation_boundary"] = "改了边界"
    strategy.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report3 = dp.check_pack(tmp_path)
    assert any(g["code"] == "signoff_stale_adaptation_strategy" for g in report3["gaps"])


def test_signoff_requires_time(tmp_path):
    _fill_confirmed(tmp_path)
    report = dp.check_pack(tmp_path)
    (tmp_path / "开发包" / "signoff.json").write_text(json.dumps({
        "reviewer": "编辑甲", "role": "creative", "file_sha256": report["file_sha256"],
    }, ensure_ascii=False), encoding="utf-8")
    checked = dp.check_pack(tmp_path)
    assert any(gap["code"] == "signoff_time_missing" for gap in checked["gaps"])


def test_v1_blueprint_requires_explicit_migration(tmp_path):
    _fill_confirmed(tmp_path)
    path = tmp_path / "脚本" / "split_blueprint.json"
    path.write_text(json.dumps({
        "kind": "comic_split_blueprint", "version": 1, "status": "confirmed",
        "chapters": [{"chapter": "第1话", "source_range": "第一章"}],
    }, ensure_ascii=False), encoding="utf-8")
    report = dp.check_pack(tmp_path)
    codes = {gap["code"] for gap in report["gaps"]}
    assert "split_blueprint_migration_required" in codes


def test_source_coverage_gap_requires_exception(tmp_path):
    _fill_confirmed(tmp_path)
    path = tmp_path / "脚本" / "split_blueprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    second = json.loads(json.dumps(data["chapters"][0], ensure_ascii=False))
    second.update({"chapter": "第2话", "status": "confirmed"})
    second["source_spans"][0].update({"start": "第3章", "end": "第3章"})
    data["chapters"].append(second)
    source = tmp_path / second["source_spans"][0]["source_path"]
    source.write_text("第1章\n一\n第2章\n二\n第3章\n三", encoding="utf-8")
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report = dp.check_pack(tmp_path)
    assert any(gap["code"] == "source_coverage_gap" for gap in report["gaps"])
    data["chapters"][1]["source_spans"][0]["coverage_exception"] = "第2章明确删改，理由已由编辑确认"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report2 = dp.check_pack(tmp_path)
    assert not any(gap["code"] == "source_coverage_gap" for gap in report2["gaps"])


def test_chapter_sequence_and_long_series_state_are_deterministic_gaps(tmp_path):
    _fill_confirmed(tmp_path)
    path = tmp_path / "脚本" / "split_blueprint.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    second = json.loads(json.dumps(data["chapters"][0], ensure_ascii=False))
    second["chapter"] = "第3话"
    second["source_spans"][0]["start"] = second["source_spans"][0]["end"] = "第2章"
    second.pop("exit_state")
    data["chapters"].append(second)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report = dp.check_pack(tmp_path)
    codes = {gap["code"] for gap in report["gaps"]}
    assert "chapter_sequence_gap" in codes
    assert "exit_state_missing" in codes


def _fill_with_source(tmp_path, chapters_in_source, planned_end):
    """Confirmed pack whose source has ``chapters_in_source`` 章 but plans through ``planned_end``."""
    dp.scaffold(tmp_path, write=True)
    for key, path in dp.pack_files(tmp_path).items():
        if key == "signoff":
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        data = json.loads(json.dumps(data, ensure_ascii=False).replace("待补", "已填内容").replace("待填", "已填"))
        data["status"] = "confirmed"
        if key == "split_blueprint":
            entry = data["chapters"][0]
            entry["status"] = "confirmed"
            entry["source_spans"][0]["start"] = "第1章"
            entry["source_spans"][0]["end"] = f"第{planned_end}章"
            source_path = tmp_path / entry["source_spans"][0]["source_path"]
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(
                "\n".join(f"第{index}章\n正文内容" for index in range(1, chapters_in_source + 1)),
                encoding="utf-8",
            )
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_unplanned_source_breadth_is_a_gap(tmp_path):
    """120 章的源只规划 1 章不能算通过——这正是水浒传/金瓶梅实测漏掉的那类。"""
    _fill_with_source(tmp_path, chapters_in_source=120, planned_end=1)
    report = dp.check_pack(tmp_path)
    gap = next(g for g in report["gaps"] if g["code"] == "source_coverage_incomplete")
    assert "120 章" in gap["message"]
    assert "1 章进入话次规划" in gap["message"]


def test_full_coverage_has_no_breadth_gap(tmp_path):
    _fill_with_source(tmp_path, chapters_in_source=3, planned_end=3)
    report = dp.check_pack(tmp_path)
    assert not [g for g in report["gaps"] if "coverage" in g["code"]]


def test_declared_coverage_scope_downgrades_breadth_to_warning(tmp_path):
    """首批只切一部分是合法的，但必须显式声明 planned_through + reason。"""
    _fill_with_source(tmp_path, chapters_in_source=120, planned_end=10)
    blueprint = dp.pack_files(tmp_path)["split_blueprint"]
    data = json.loads(blueprint.read_text(encoding="utf-8"))
    data["coverage_scope"] = {"planned_through": "第10章", "reason": "首批试切 10 章验证画风"}
    blueprint.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report = dp.check_pack(tmp_path)
    assert not [g for g in report["gaps"] if "coverage" in g["code"]]
    assert any(w["code"] == "source_beyond_planned_scope" for w in report["warnings"])


def test_hole_inside_declared_scope_still_blocks(tmp_path):
    """声明规划到第10章，却在范围内留洞，仍是 gap——声明不是免死金牌。"""
    _fill_with_source(tmp_path, chapters_in_source=120, planned_end=1)
    blueprint = dp.pack_files(tmp_path)["split_blueprint"]
    data = json.loads(blueprint.read_text(encoding="utf-8"))
    data["coverage_scope"] = {"planned_through": "第10章", "reason": "首批试切 10 章"}
    blueprint.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report = dp.check_pack(tmp_path)
    gap = next(g for g in report["gaps"] if g["code"] == "source_coverage_incomplete")
    assert "范围内" in gap["message"]


def test_coverage_scope_without_reason_is_a_gap(tmp_path):
    _fill_with_source(tmp_path, chapters_in_source=120, planned_end=1)
    blueprint = dp.pack_files(tmp_path)["split_blueprint"]
    data = json.loads(blueprint.read_text(encoding="utf-8"))
    data["coverage_scope"] = {"planned_through": "第1章"}
    blueprint.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report = dp.check_pack(tmp_path)
    assert any(g["code"] == "coverage_scope_reason_missing" for g in report["gaps"])


def test_source_without_unit_markers_is_not_judged(tmp_path):
    """源里没有第N章标记时无法判断广度，不能瞎报。"""
    _fill_with_source(tmp_path, chapters_in_source=5, planned_end=1)
    blueprint = dp.pack_files(tmp_path)["split_blueprint"]
    data = json.loads(blueprint.read_text(encoding="utf-8"))
    source_path = tmp_path / data["chapters"][0]["source_spans"][0]["source_path"]
    source_path.write_text("一段没有任何章节标记的散文。", encoding="utf-8")
    report = dp.check_pack(tmp_path)
    assert not [g for g in report["gaps"] if "coverage_incomplete" in g["code"]]


def test_vacuous_coverage_exception_does_not_suppress_gap():
    blueprint = {
        "chapters": [
            {"chapter": "第1话", "source_mode": "adapted",
             "source_spans": [{"source_path": "s.md", "start": "第1章", "end": "第1章"}]},
            {"chapter": "第2话", "source_mode": "adapted",
             "source_spans": [{"source_path": "s.md", "start": "第3章", "end": "第3章",
                               "coverage_exception": "x"}]},  # vacuous
        ]
    }
    codes = {i["code"] for i in dp._coverage_issues(blueprint)}
    assert "source_coverage_exception_vacuous" in codes
    assert "source_coverage_gap" in codes  # still fires — not suppressed


def test_substantive_coverage_exception_suppresses_gap():
    blueprint = {
        "chapters": [
            {"chapter": "第1话", "source_mode": "adapted",
             "source_spans": [{"source_path": "s.md", "start": "第1章", "end": "第1章"}]},
            {"chapter": "第2话", "source_mode": "adapted",
             "source_spans": [{"source_path": "s.md", "start": "第3章", "end": "第3章",
                               "coverage_exception": "第2章删改，编辑确认后文带出"}]},
        ]
    }
    codes = {i["code"] for i in dp._coverage_issues(blueprint)}
    assert "source_coverage_exception_vacuous" not in codes
    assert "source_coverage_gap" not in codes
