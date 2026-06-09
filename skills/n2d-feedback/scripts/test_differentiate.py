"""从本目录跑：cd skills/n2d-feedback/scripts && python -m pytest test_differentiate.py"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("differentiate.py")
spec = importlib.util.spec_from_file_location("differentiate", SCRIPT)
diff = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(diff)


def _records():
    return [
        {"kind": "genre_performance_record", "genre": "仙侠",
         "features": {"opening_type": "cold_conflict", "cliffhanger_type": "crisis_suspend"},
         "metrics": {"follow_next_rate": 0.40, "plays": 800000}},
        {"kind": "genre_performance_record", "genre": "仙侠",
         "features": {"opening_type": "cold_conflict", "cliffhanger_type": "crisis_suspend"},
         "metrics": {"follow_next_rate": 0.38, "plays": 600000}},
        {"kind": "genre_performance_record", "genre": "仙侠",
         "features": {"opening_type": "cold_conflict", "cliffhanger_type": "resolved_clean"},
         "metrics": {"follow_next_rate": 0.15, "plays": 200000}},
        {"kind": "genre_performance_record", "genre": "都市",
         "features": {"opening_type": "reverse_flash", "cliffhanger_type": "reversal_signal"},
         "metrics": {"follow_next_rate": 0.42, "plays": 500000}},
        {"kind": "genre_performance_record", "genre": "都市",
         "features": {"opening_type": "reverse_flash", "cliffhanger_type": "reversal_signal"},
         "metrics": {"follow_next_rate": 0.40, "plays": 400000}},
    ]


def test_occupancy_counts_done_combos():
    occ = diff.occupancy(_records())
    assert occ[("仙侠", "cold_conflict", "crisis_suspend")] == 2
    assert occ[("都市", "reverse_flash", "reversal_signal")] == 2


def test_proven_values_picks_above_mean_with_samples():
    proven = diff.proven_values(_records(), "cliffhanger_type", "follow_next_rate", min_samples=2)
    assert "crisis_suspend" in proven       # 2 条、高于均值
    assert "reversal_signal" in proven       # 2 条、高
    assert "resolved_clean" not in proven    # 1 条且低于均值


def test_saturation_by_genre_from_baseline():
    sat = diff.saturation_by_genre(["仙侠", "都市"], ["仙侠", "仙侠", "仙侠", "都市"])
    assert sat["仙侠"] == 3 and sat["都市"] == 1


def test_build_candidates_prefers_proven_recomb_and_avoids_saturation():
    recs = _records()
    genres = diff.candidate_genres(recs, [])
    report = diff.build_candidates(recs, genres, metric="follow_next_rate", min_samples=2,
                                   baseline_signals=["仙侠", "仙侠", "仙侠", "都市"], top=6)
    cands = report["candidates"]
    assert cands, "应有候选"
    top = cands[0]
    # 头号候选应复用已验证轴，且不在最饱和的仙侠
    assert top["reuses_proven"]
    assert top["genre"] == "都市"
    # 已做过的组合不应作为候选
    labels = {(c["genre"], c["opening_type"], c["cliffhanger_type"]) for c in cands}
    assert ("仙侠", "cold_conflict", "crisis_suspend") not in labels


def test_empty_ledger_degrades_with_notes():
    report = diff.build_candidates([], [], metric="follow_next_rate", min_samples=2, baseline_signals=[], top=6)
    assert report["candidates"] == []
    assert report["ledger_records"] == 0
    assert any("没有候选题材" in n or "样本" in n for n in report["notes"])


def test_genres_arg_injects_unmade_demand_genre():
    recs = _records()
    genres = diff.candidate_genres(recs, ["悬疑"])  # 注入一个我们没做过的题材
    assert "悬疑" in genres
    report = diff.build_candidates(recs, genres, metric="follow_next_rate", min_samples=2,
                                   baseline_signals=[], top=20)
    # 悬疑 × 已验证轴 应出现在候选里（全新题材 + 复用有效节奏）
    assert any(c["genre"] == "悬疑" and c["reuses_proven"] for c in report["candidates"])


def test_cli_writes_output(tmp_path):
    lp = tmp_path / "genre_ledger.jsonl"
    lp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in _records()), encoding="utf-8")
    out = tmp_path / "差异化候选.md"
    rc = diff.main(["--ledger", str(lp), "--top", "5", "--out", str(out)])
    assert rc == 0 and out.is_file()
    assert "差异化选题候选" in out.read_text(encoding="utf-8")
