"""drift_report 单测。运行：cd skills/comic/comic-identity/scripts && python -m pytest test_drift_report.py"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("drift_report.py")
spec = importlib.util.spec_from_file_location("drift_report", SCRIPT)
dr = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(dr)


def _report(chapter, chars=None, findings=None):
    return {"chapter": chapter, "characters": chars or [], "findings": findings or []}


def test_char_status_ok_when_no_adverse_finding():
    rep = _report("第1话", chars=[{"character_id": "CHAR_A"}])
    st = dr.char_status_in_report(rep)
    assert st["CHAR_A"]["status"] == "ok"


def test_char_status_takes_worst_severity():
    rep = _report("第1话", chars=[{"character_id": "CHAR_A"}], findings=[
        {"character_id": "CHAR_A", "severity": "warn", "code": "ccip_identity_low"},
        {"character_id": "CHAR_A", "severity": "block", "code": "character_reference_missing"},
    ])
    st = dr.char_status_in_report(rep)
    assert st["CHAR_A"]["status"] == "block"
    assert "character_reference_missing" in st["CHAR_A"]["codes"]


def test_bare_names_ignored():
    rep = _report("第1话", findings=[{"character_id": "张三", "severity": "warn", "code": "x"}])
    assert dr.char_status_in_report(rep) == {}


def test_timeline_first_bad_chapter():
    reports = [
        ("第1话", _report("第1话", chars=[{"character_id": "CHAR_A"}])),
        ("第2话", _report("第2话", findings=[{"character_id": "CHAR_A", "severity": "warn", "code": "ccip_identity_low"}])),
        ("第3话", _report("第3话", findings=[{"character_id": "CHAR_A", "severity": "block", "code": "face_fingerprint_low"}])),
    ]
    tl = dr.build_timeline(reports)
    row = next(r for r in tl["characters"] if r["char_id"] == "CHAR_A")
    assert row["first_bad_chapter"] == "第2话"
    assert row["block_chapters"] == ["第3话"]
    assert row["warn_or_block_chapters"] == ["第2话", "第3话"]


def test_recommend_reference_missing_priority():
    rec = dr.recommend("CHAR_A", ["第2话"], ["character_reference_missing"])
    assert "补 anchor/front/face" in rec


def test_recommend_outfit_drift():
    rec = dr.recommend("CHAR_A", ["第2话"], ["outfit_fingerprint_low"])
    assert "服装" in rec and "outfits" in rec


def test_recommend_repeated_drift_suggests_dedicated_views():
    rec = dr.recommend("CHAR_A", ["第2话", "第4话"], ["face_fingerprint_low"])
    assert "跨 2 话反复" in rec and "专门定妆" in rec


def test_recommend_single_chapter_minimal():
    rec = dr.recommend("CHAR_A", ["第5话"], ["ccip_identity_low"])
    assert "单话漂移" in rec and "rerun_targets" in rec


def test_recommend_none_when_clean():
    assert dr.recommend("CHAR_A", [], []) is None


def test_end_to_end(tmp_path):
    root = tmp_path
    pd = root / "生产数据"
    pd.mkdir(parents=True)
    (pd / "comic_character_consistency_第1话.json").write_text(json.dumps(
        _report("第1话", chars=[{"character_id": "CHAR_A"}]), ensure_ascii=False), encoding="utf-8")
    (pd / "comic_character_consistency_第2话.json").write_text(json.dumps(
        _report("第2话", findings=[{"character_id": "CHAR_A", "severity": "block", "code": "character_reference_missing"}]),
        ensure_ascii=False), encoding="utf-8")
    report = dr.build_report(root)
    assert report["summary"]["chapters_scanned"] == 2
    assert report["summary"]["characters_with_drift"] == 1
    row = report["characters"][0]
    assert row["first_bad_chapter"] == "第2话"
    dr.main([str(root), "--write"])
    assert (pd / "comic_identity_drift_report.md").is_file()
