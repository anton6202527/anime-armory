#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import split_novel


def test_auto_chapter_aware_guard_detects_fragmented_chaptered_source():
    paras = []
    for i in range(1, 11):
        paras.extend([f"第{i}章 妖变", "【系统提示】", "妖魔袭来。", "她反手斩妖。"])
    fragmented = ["碎片"] * 80
    assert split_novel.should_auto_chapter_aware(fragmented, paras)


def test_auto_chapter_aware_guard_ignores_explicitly_small_non_chaptered_text():
    paras = ["荒野风声。", "妖魔袭来。", "她反手斩妖。"]
    fragmented = ["碎片"] * 80
    assert not split_novel.should_auto_chapter_aware(fragmented, paras)


def test_split_plan_v2_keeps_full_source_units_when_only_first_episode_materialized():
    root = tempfile.mkdtemp()
    paras = ["第一章", "危机逼近。", "她反击，原来另有真相！", "第二章", "次日再战。"]
    episodes = ["\n".join(paras[:3]), "\n".join(paras[3:])]
    script = Path(root) / "脚本" / "第1集"
    script.mkdir(parents=True)
    (script / "raw.txt").write_text(episodes[0], encoding="utf-8")
    source = Path(root) / "小说" / "测试.txt"
    source.parent.mkdir()
    source.write_text("\n".join(paras), encoding="utf-8")

    plan = split_novel.write_split_plan(
        root, "测试", str(source), episodes, 1,
        split_mode="test", genre_note="test", partial=True, source_paras=paras,
    )

    assert plan["schema_version"] == 2
    assert len(plan["source_units"]) == len(paras)
    assert len(plan["episodes"]) == 2
    assert plan["episodes"][0]["materialized"] is True
    assert plan["episodes"][1]["materialized"] is False
    assert plan["boundary_candidates"]
    assert plan["boundary_optimization"]["top_paths"]


def test_split_continuation_preserves_human_review_file():
    root = tempfile.mkdtemp()
    paras = ["第一章", "冲突。", "反击！", "第二章", "危机。", "真相！"]
    episodes = ["\n".join(paras[:3]), "\n".join(paras[3:])]
    source = Path(root) / "小说" / "测试.txt"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(paras), encoding="utf-8")
    split_novel.write_split_plan(
        root, "测试", str(source), episodes, 1,
        split_mode="test", genre_note="test", partial=True, source_paras=paras,
    )
    human = Path(root) / "脚本" / "_拆集复核.md"
    human.write_text("# 人工决定\n\n保留第1→2集边界。\n", encoding="utf-8")
    split_novel.write_split_plan(
        root, "测试", str(source), episodes, 2,
        split_mode="test", genre_note="test", partial=False, source_paras=paras,
    )
    assert human.read_text(encoding="utf-8") == "# 人工决定\n\n保留第1→2集边界。\n"
    assert (Path(root) / "脚本" / "_拆集机器索引.md").exists()


def test_beam_optimizer_is_global_and_dictionary_is_not_a_veto():
    paras = ["平静叙述。", "第二幕", "普通句。", "第三幕", "收束。", "尾声。"]
    paths = split_novel.optimize_boundary_paths(paras, 3, top_k=3)
    assert paths
    assert all(len(p["segment_end_positions"]) == 3 for p in paths)
    assert paths[0]["segment_end_positions"][-1] == len(paras)


def test_middle_start_plan_retains_full_source_axis_and_global_unit_ids():
    root = tempfile.mkdtemp()
    full = ["第一章", "前情。", "第二章", "当前冲突。", "当前反击！"]
    selected = full[2:]
    episodes = ["\n".join(selected)]
    source = Path(root) / "小说" / "测试.txt"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(full), encoding="utf-8")
    plan = split_novel.write_split_plan(
        root, "测试", str(source), episodes, 0,
        split_mode="middle", genre_note="test", partial=True,
        source_paras=full, selected_source_paras=selected, source_unit_offset=2,
    )
    assert len(plan["source_units"]) == 5
    assert plan["episodes"][0]["source_unit_span"]["start_source_unit_id"] == "U000003"
    assert plan["episodes"][0]["source_unit_span"]["end_source_unit_id"] == "U000005"
    assert plan["boundary_optimization"]["top_paths"][0]["segment_end_positions"][-1] == 5


def test_confirmed_development_arc_is_hashed_and_only_mapped_units_constrain_beam():
    root = tempfile.mkdtemp()
    paras = ["第一章", "铺垫。", "转折！", "第二章", "兑现。", "尾声。"]
    episodes = ["\n".join(paras[:3]), "\n".join(paras[3:])]
    source = Path(root) / "小说" / "测试.txt"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(paras), encoding="utf-8")
    dev = Path(root) / "开发包"
    dev.mkdir()
    (dev / "season_arc.json").write_text(json.dumps({
        "status": "confirmed",
        "series_promise": "查清真相",
        "front_arc": [{
            "episode": "第1集",
            "purpose": "首个转折",
            "boundary_after_source_unit_id": "U000003",
        }],
        "signature_scenes": ["第二章兑现"],
    }, ensure_ascii=False), encoding="utf-8")
    plan = split_novel.write_split_plan(
        root, "测试", str(source), episodes, 0,
        split_mode="test", genre_note="test", partial=True, source_paras=paras,
    )
    assert plan["development_arc_contract"]["status"] == "confirmed"
    assert plan["development_arc_contract"]["sha256"]
    assert plan["boundary_optimization"]["development_arc_constraints_applied"] is True
    assert "U000003" in plan["boundary_optimization"]["top_paths"][0]["boundary_after_source_units"]
