#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for simulate_panel.py — deterministic reader-panel signals.

Run from this directory:
    cd skills/novel/novel-simulate/scripts && python3 -m pytest test_simulate_panel.py
"""
import os
import json
import tempfile

import simulate_panel
from reader_probe import reader_probe_freshness


def _make_project(chapters):
    """chapters: dict {filename: text}. Returns temp project dir path."""
    root = tempfile.mkdtemp()
    cdir = os.path.join(root, "章节")
    os.makedirs(cdir)
    for name, text in chapters.items():
        with open(os.path.join(cdir, name), "w", encoding="utf-8") as f:
            f.write(text)
    return root


def test_density_basic():
    # 4 CJK chars, keyword "打脸" appears once -> 1 hit / 4 chars * 1000 = 250.0
    d = simulate_panel._density("打脸时刻", ["打脸"])
    assert d == 250.0


def test_density_empty_text_no_crash():
    # _cjk_len 0 -> falls back to 1, no ZeroDivisionError
    assert simulate_panel._density("", ["打脸"]) == 0.0


def test_density_increases_with_more_hits():
    low = simulate_panel._density("逆袭啊啊啊啊啊啊啊啊", ["逆袭"])
    high = simulate_panel._density("逆袭逆袭逆袭逆袭", ["逆袭"])
    assert high > low


def test_lexical_diversity_bounds():
    # All 4-grams identical -> low diversity; varied text -> higher
    repetitive = simulate_panel._lexical_diversity("一二三四" * 10)
    varied = simulate_panel._lexical_diversity(
        "春风又绿江南岸明月何时照我还故人西辞黄鹤楼烟花三月下扬州")
    assert 0.0 <= repetitive <= 1.0
    assert 0.0 <= varied <= 1.0
    assert varied > repetitive


def test_lexical_diversity_no_cjk():
    assert simulate_panel._lexical_diversity("abc def") == 0.0


def test_hook_tail_signal_reports_raw_observations():
    chapters = [
        (1, "平淡无奇的句子结束了"),
        (2, "正文" + "？但却突然竟然居然不料没想到此时" * 3),
    ]
    signal = simulate_panel._hook_tail_signal(chapters)
    assert signal["chapter_tails_observed"] == 2
    assert signal["chapter_tails_with_marker_hits"] == 1
    assert signal["literal_marker_hits"] > 0
    assert signal["density_per_kchar"] > 0
    assert "score" not in signal


def test_literal_term_signal_exposes_counts_without_direction():
    signal = simulate_panel._literal_term_signal("突然突然，仍然平静。", ["突然", "不料"])
    assert signal["literal_hits"] == 2
    assert signal["matched_terms"] == {"突然": 2}
    assert signal["interpretation"] == "uncalibrated_literal_surface_observation"


def test_analyze_schema_v3_has_components_but_no_retention_aggregate():
    root = _make_project({
        "第1章.md": "他平静地走过街道，看着远方的天空，心里想着往事。" * 5,
        "第2章.md": "夜色降临，万物归于安宁，没有任何波澜。" * 5,
        "第3章.md": "时间慢慢流逝，一切都很安静。" * 5,
    })
    sig = simulate_panel.analyze(root, "opening", 1, ["rookie", "logic", "emote", "critic"])
    assert sig is not None
    assert sig["schema_version"] == 3
    assert "retention_prior" not in sig
    assert "retention_proxy" not in sig
    assert sig["aggregate_score"] is None
    assert set(sig["surface_signals"]) == {"hook_tail_markers", "lexical_4gram", "cliche_terms"}
    assert sig["source_snapshot"]["kind"] == "novel_text_snapshot"
    assert [item["path"] for item in sig["source_snapshot"]["files"]] == [
        "章节/第1章.md", "章节/第2章.md", "章节/第3章.md",
    ]
    assert all(not os.path.isabs(item["path"]) for item in sig["source_snapshot"]["files"])
    assert reader_probe_freshness(root, sig)["status"] == "fresh"


def test_analyze_does_not_rank_bland_and_punchy_as_retention():
    bland = _make_project({
        "第1章.md": "他平静地走在路上，看着天空，心里想着往事的种种。" * 6,
        "第2章.md": "夜色降临，万物安宁，没有任何波澜起伏地过去了。" * 6,
        "第3章.md": "时间慢慢流逝，日子一天天过着，安静祥和。" * 6,
    })
    punchy = _make_project({
        "第1章.md": ("他逆袭打脸碾压突破反杀升级翻盘吊打震惊崛起无敌暴击斩杀，"
                     "局势骤然逆转！") * 6 + "突然？竟然不料没想到此时就在猛地",
        "第2章.md": ("再次逆袭打脸碾压突破反杀升级，所有人都被吊打震惊！") * 6
                    + "但却突然竟然居然不料",
        "第3章.md": ("又一轮逆袭打脸碾压突破反杀，无敌暴击斩杀崛起翻盘！") * 6
                    + "原来下一刻骤然猛地此时",
    })
    bland_sig = simulate_panel.analyze(bland, "opening", 1, list(simulate_panel.PERSONAS))
    punchy_sig = simulate_panel.analyze(punchy, "opening", 1, list(simulate_panel.PERSONAS))
    bland_hook = bland_sig["surface_signals"]["hook_tail_markers"]["literal_marker_hits"]
    punchy_hook = punchy_sig["surface_signals"]["hook_tail_markers"]["literal_marker_hits"]
    assert punchy_hook > bland_hook
    assert "retention_prior" not in bland_sig
    assert "retention_proxy" not in punchy_sig


def test_analyze_returns_none_when_no_chapters():
    root = tempfile.mkdtemp()  # no 章节 dir
    assert simulate_panel.analyze(root, "opening", 1, ["rookie"]) is None


def test_analyze_chapter_scope():
    root = _make_project({
        "第1章.md": "第一章内容逆袭打脸。",
        "第2章.md": "第二章内容碾压突破。",
    })
    sig = simulate_panel.analyze(root, "chapter", 2, ["rookie"])
    assert sig["chapters_read"] == [2]
    assert sig["scope"] == "chapter"
    assert sig["scope_chapter"] == 2
    assert [item["path"] for item in sig["source_snapshot"]["files"]] == ["章节/第2章.md"]


def test_chapter_scope_missing_is_error_not_first_chapter_fallback():
    root = _make_project({"第1章.md": "第一章内容。"})
    try:
        simulate_panel.analyze(root, "chapter", 9, ["rookie"])
    except FileNotFoundError as exc:
        assert "第 9 章" in str(exc)
        assert "不允许回退" in str(exc)
    else:
        raise AssertionError("missing chapter scope must fail")


def test_chapter_scope_empty_project_reports_exact_missing_chapter():
    root = _make_project({})
    try:
        simulate_panel.analyze(root, "chapter", 1, ["rookie"])
    except FileNotFoundError as exc:
        assert "第 1 章" in str(exc)
        assert "不允许回退" in str(exc)
    else:
        raise AssertionError("empty chapter scope must fail with the exact chapter contract")


def test_source_snapshot_becomes_stale_after_scoped_text_change():
    root = _make_project({"第1章.md": "第一版正文。"})
    sig = simulate_panel.analyze(root, "chapter", 1, ["rookie"])
    with open(os.path.join(root, "章节", "第1章.md"), "w", encoding="utf-8") as f:
        f.write("正文已经修改。")
    freshness = reader_probe_freshness(root, sig)
    assert freshness["status"] == "stale"
    assert "hash" in freshness["reason"]


def test_opening_snapshot_stale_when_new_chapter_enters_actual_scope():
    root = _make_project({"第1章.md": "一。", "第2章.md": "二。"})
    sig = simulate_panel.analyze(root, "opening", 1, ["rookie"])
    assert sig["chapters_read"] == [1, 2]
    with open(os.path.join(root, "章节", "第3章.md"), "w", encoding="utf-8") as f:
        f.write("三。")
    freshness = reader_probe_freshness(root, sig)
    assert freshness["status"] == "stale"
    assert "新增/删除章" in freshness["reason"]


def test_chapter_snapshot_stays_fresh_when_unrelated_chapter_is_added():
    root = _make_project({"第1章.md": "一。"})
    sig = simulate_panel.analyze(root, "chapter", 1, ["rookie"])
    with open(os.path.join(root, "章节", "第2章.md"), "w", encoding="utf-8") as f:
        f.write("二。")
    assert reader_probe_freshness(root, sig)["status"] == "fresh"


def test_write_report_emits_signals_json():
    root = _make_project({
        "第1章.md": "他逆袭打脸碾压突破反杀。" * 5 + "突然？竟然不料",
        "第2章.md": "再次反杀升级翻盘吊打。" * 5,
        "第3章.md": "崛起无敌暴击斩杀。" * 5,
    })
    personas = list(simulate_panel.PERSONAS)
    sig = simulate_panel.analyze(root, "opening", 1, personas)
    md_path, sig_path = simulate_panel.write_report(root, sig, personas)

    assert os.path.basename(sig_path) == "reader_panel_signals.json"
    assert os.path.exists(sig_path)
    assert os.path.exists(md_path)

    with open(sig_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "surface_signals" in data
    assert "cliche_terms" in data["surface_signals"]
    assert "retention_prior" not in data
    assert "retention_proxy" not in data
    assert data["kind"] == "novel_synthetic_reader_probe"
    assert data["evidence_type"] == "synthetic_probe"
    assert data["validation_status"] == "unvalidated"
    assert data["decision_authority"] == "context_only"
    assert data["numeric_score_eligible"] is False
    assert data["analysis_mode"] == "surface_signals_only"
    assert data["signal_only"] is True
    assert data["qualitative_completed"] is False
    assert data["perspectives_completed"] == []
    assert data["aggregate_score"] is None
    assert "date" in data
    # Perspective signals carried through.
    for pid in personas:
        assert pid in data["perspectives"]
        assert "keyword_surface" in data["perspectives"][pid]

    with open(md_path, encoding="utf-8") as f:
        report = f.read()
    assert "不生成聚合留存" not in report  # CLI wording does not leak into the report.
    assert "没有相加后的总分" in report
    assert "留存代理" not in report


def test_project_cohort_is_loaded_as_preference_lenses():
    root = _make_project({"第1章.md": "她在门前犹豫，最终还是推门。"})
    cohort_path = os.path.join(root, "设定", "reader_probe_cohort.json")
    os.makedirs(os.path.dirname(cohort_path), exist_ok=True)
    with open(cohort_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_reader_probe_cohort",
            "name": "慢热关系视角组",
            "description": "只描述阅读偏好，不声明代表任何人群。",
            "perspectives": [{
                "id": "slow_burn",
                "name": "慢热关系视角",
                "focus": "关系细微移动与未说出口的选择",
                "keywords": ["犹豫", "推门"],
                "probe_questions": ["关系变化是否落实为一个不可逆选择？"],
                "genre_familiarity": "熟悉慢热关系叙事",
                "tolerances": "可接受低事件密度，但不能接受关系静止",
            }],
        }, f, ensure_ascii=False)

    perspectives, cohort = simulate_panel.resolve_perspectives(root, "品质向")
    assert list(perspectives) == ["slow_burn"]
    assert cohort["name"] == "慢热关系视角组"
    assert cohort["population_representativeness"] == "none"
    assert cohort["sources"][0]["path"] == "设定/reader_probe_cohort.json"
    assert cohort["sources"][0]["automatic"] is True

    sig = simulate_panel.analyze(
        root, "opening", 1, list(perspectives), "品质向",
        perspective_defs=perspectives, cohort_meta=cohort,
    )
    assert sig["perspectives"]["slow_burn"]["keyword_surface"]["literal_hits"] == 2
    assert sig["cohort"]["population_representativeness"] == "none"


def test_inline_viewpoint_without_keywords_is_qualitative_only():
    root = _make_project({"第1章.md": "风从空房间穿过去。"})
    perspectives, cohort = simulate_panel.resolve_perspectives(
        root,
        "品质向",
        inline_viewpoints=[json.dumps({
            "id": "atmosphere",
            "name": "氛围视角",
            "focus": "空间与余韵",
            "probe_questions": ["空间是否参与了人物选择？"],
        }, ensure_ascii=False)],
    )
    sig = simulate_panel.analyze(
        root, "opening", 1, list(perspectives), "品质向",
        perspective_defs=perspectives, cohort_meta=cohort,
    )
    keyword = sig["perspectives"]["atmosphere"]["keyword_surface"]
    assert keyword["available"] is False
    assert keyword["density_per_kchar"] is None


def test_custom_cohort_rejects_demographic_or_unmodeled_fields():
    root = _make_project({"第1章.md": "正文"})
    cohort_path = os.path.join(root, "cohort.json")
    with open(cohort_path, "w", encoding="utf-8") as f:
        json.dump({
            "schema_version": 1,
            "kind": "novel_reader_probe_cohort",
            "perspectives": [{
                "id": "unsafe",
                "name": "伪人口画像",
                "focus": "不应接受",
                "age": 18,
            }],
        }, f, ensure_ascii=False)
    try:
        simulate_panel.load_cohort(cohort_path)
    except simulate_panel.CohortConfigError as exc:
        assert "不允许字段" in str(exc)
        assert "人口统计" in str(exc)
    else:
        raise AssertionError("demographic field should be rejected")


def test_explicit_unknown_builtin_persona_fails_instead_of_silent_fallback():
    root = _make_project({"第1章.md": "正文"})
    try:
        simulate_panel.resolve_perspectives(root, "品质向", persona_ids=["missing"])
    except simulate_panel.CohortConfigError as exc:
        assert "未知预设人格" in str(exc)
    else:
        raise AssertionError("unknown preset should fail")
