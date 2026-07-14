"""comic development_pack 单测。运行：cd skills/comic-script/scripts && python -m pytest test_development_pack.py"""
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
