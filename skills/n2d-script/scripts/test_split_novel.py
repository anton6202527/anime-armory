#!/usr/bin/env python3
import gzip
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
    source.write_text("\r\n".join(paras), encoding="utf-8")

    plan = split_novel.write_split_plan(
        root, "测试", str(source), episodes, 1,
        split_mode="test", genre_note="test", partial=True, source_paras=paras,
        legacy_plan_v2=True,
    )

    assert plan["schema_version"] == 2
    assert len(plan["source_units"]) == len(paras)
    assert len(plan["episodes"]) == 2
    assert plan["episodes"][0]["materialized"] is True
    assert plan["episodes"][1]["materialized"] is False
    assert plan["boundary_candidates"]
    assert plan["boundary_optimization"]["top_paths"]


def test_split_plan_v3_compacts_source_axis_and_rehydrates_legacy_units():
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

    assert plan["schema_version"] == 3
    assert plan["source_units_storage"] == split_novel.COMPACT_SOURCE_UNITS_ENCODING
    assert split_novel.source_unit_count(plan) == len(paras)
    assert plan["source_units"]["count"] == len(paras)
    assert "preview" not in plan["source_units"]
    assert "sha256" not in plan["source_units"]
    hydrated = list(split_novel.iter_source_units(plan, paras))
    assert hydrated == split_novel.build_source_units(paras)
    anchors = list(split_novel.iter_arc_anchors(plan, paras))
    assert len([a for a in anchors if a.get("anchor_type") == "source_signal"]) == plan[
        "source_signal_anchor_count"
    ]
    assert plan["episodes"][0]["materialized"] is True
    assert plan["episodes"][1]["materialized"] is False
    assert plan["boundary_candidates"]
    assert plan["boundary_optimization"]["top_paths"]


def test_split_plan_v3_file_is_materially_smaller_than_verbose_v2(tmp_path):
    paras = [f"第{i // 100 + 1}章" if i % 100 == 0 else f"人物沿官道继续前行{i}。" for i in range(1000)]
    episodes = ["\n".join(paras[i:i + 100]) for i in range(0, len(paras), 100)]

    sizes = {}
    for label, legacy in (("compact", False), ("legacy", True)):
        root = tmp_path / label
        source = root / "小说" / "测试.txt"
        source.parent.mkdir(parents=True)
        source.write_text("\n".join(paras), encoding="utf-8")
        split_novel.write_split_plan(
            str(root), "测试", str(source), episodes, 0,
            split_mode="test", genre_note="test", partial=True, source_paras=paras,
            legacy_plan_v2=legacy,
        )
        sizes[label] = (root / "脚本" / "split_plan.json").stat().st_size

    assert sizes["compact"] < sizes["legacy"] * 0.25


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


def test_split_plan_schema_migration_preserves_raw_and_human_review(tmp_path):
    root = tmp_path / "作品"
    paras = ["第一章", "冲突。", "反击！", "第二章", "危机。", "真相！"]
    episodes = ["\n".join(paras[:3]), "\n".join(paras[3:])]
    source = root / "小说" / "测试.txt"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(paras), encoding="utf-8")
    raw = root / "脚本" / "第1集" / "raw.txt"
    raw.parent.mkdir(parents=True)
    raw.write_text("人工精修 raw，不得被计划存储迁移覆盖。\n", encoding="utf-8")
    human = root / "脚本" / "_拆集复核.md"
    human.write_text("# 人工决定\n\n保留第1→2集边界。\n", encoding="utf-8")
    raw_before = raw.read_bytes()
    human_before = human.read_bytes()

    for legacy, expected_schema in ((False, 3), (True, 2), (False, 3)):
        plan = split_novel.write_split_plan(
            str(root), "测试", str(source), episodes, 1,
            split_mode="test", genre_note="test", partial=True, source_paras=paras,
            legacy_plan_v2=legacy,
        )
        assert plan["schema_version"] == expected_schema
        assert raw.read_bytes() == raw_before
        assert human.read_bytes() == human_before


def test_compact_existing_plan_is_semantic_preserving_and_receipted(tmp_path):
    root = tmp_path / "作品"
    paras = ["第一章", "冲突。", "反击！", "第二章", "危机。", "真相！"]
    episodes = ["\n".join(paras[:3]), "\n".join(paras[3:])]
    source = root / "小说" / "测试.txt"
    source.parent.mkdir(parents=True)
    source.write_text("\r\n".join(paras), encoding="utf-8")
    raw = root / "脚本" / "第1集" / "raw.txt"
    raw.parent.mkdir(parents=True)
    raw.write_text("人工精修 raw。\n", encoding="utf-8")
    human = root / "脚本" / "_拆集复核.md"
    human.write_text("# 人工边界\n", encoding="utf-8")
    progress = root / "_进度.md"
    progress.write_text("# 人工进度\n", encoding="utf-8")
    legacy = split_novel.write_split_plan(
        str(root), "测试", str(source), episodes, 1,
        split_mode="test", genre_note="test", partial=True, source_paras=paras,
        legacy_plan_v2=True,
    )
    legacy_bytes = (root / "脚本" / "split_plan.json").read_bytes()
    protected_before = split_novel._protected_split_artifact_snapshot(root)

    receipt, receipt_path = split_novel.compact_existing_split_plan(
        str(root), str(source), split_novel.read_text(source)
    )
    compact = json.loads((root / "脚本" / "split_plan.json").read_text(encoding="utf-8"))

    assert compact["schema_version"] == 3
    assert list(split_novel.iter_source_units(compact, paras)) == legacy["source_units"]
    assert compact["episodes"] == legacy["episodes"]
    assert compact["boundary_candidates"] == legacy["boundary_candidates"]
    assert compact["boundary_optimization"] == legacy["boundary_optimization"]
    assert compact["estimated_total_episode_count"] == legacy["estimated_total_episode_count"]
    assert split_novel._protected_split_artifact_snapshot(root) == protected_before
    assert receipt["status"] == "pass"
    assert receipt["checks"]["production_semantics_unchanged"] is True
    assert Path(receipt_path).is_file()
    backup = root / receipt["backup"]["path"]
    with gzip.open(backup, "rb") as f:
        assert f.read() == legacy_bytes
    assert receipt["after"]["bytes"] < receipt["before"]["bytes"]


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
    assert split_novel.source_unit_count(plan) == 5
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
