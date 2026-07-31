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


# ── P4：story_spine cut 决策驱动拆集整章剔除 ─────────────────────────────────

def _spine_cut_plan(chapters, *, mode="enforce", conflicts=None, unparsed=None):
    return {
        "kind": "n2d_spine_cut_chapter_plan",
        "source": "开发包/story_spine.json",
        "mode": mode,
        "mode_source": "_设置.md:主线剪枝=突出主线" if mode == "enforce" else "未设置（默认 advisory）",
        "status": "ok",
        "cut_chapters": {ch: ["THREAD_CUT"] for ch in chapters},
        "cut_threads": [{"id": "THREAD_CUT", "name": "旁枝", "anchored_chapters": sorted(chapters)}],
        "conflicts": conflicts or [],
        "unparsed_spans": unparsed or [],
    }


def _chaptered_paras(n_chapters=5, bodies=2):
    paras = []
    for ch in range(1, n_chapters + 1):
        paras.append(f"第{ch}章 风起")
        for i in range(bodies):
            paras.append(f"正文{ch}-{i}：危机逼近，她反手斩妖，胜负立分！")
    return paras


def test_apply_spine_chapter_cuts_enforce_removes_and_accounts():
    paras = _chaptered_paras()
    result = split_novel.apply_spine_chapter_cuts(paras, 0, _spine_cut_plan([2, 4]), apply=True)
    assert result["applied"] is True
    kept_text = "\n".join(result["kept_paras"])
    assert "第2章" not in kept_text and "第4章" not in kept_text
    assert "第3章 风起" in kept_text
    rows = {r["chapter"]: r for r in result["removed_chapters"]}
    assert set(rows) == {2, 4}
    # 每章 1 标题 + 2 正文 = 3 单元；单元号引用完整源轴
    assert rows[2]["units"] == 3 and rows[2]["first_source_unit_id"] == "U000004"
    assert rows[2]["last_source_unit_id"] == "U000006"
    assert result["removed_unit_total"] == 6
    # kept_indices 是完整轴上的 0 基索引，跳过被剔章
    assert result["kept_indices"][:4] == [0, 1, 2, 6]


def test_apply_spine_chapter_cuts_advisory_previews_without_removing():
    paras = _chaptered_paras()
    result = split_novel.apply_spine_chapter_cuts(paras, 0, _spine_cut_plan([2], mode="advisory"), apply=False)
    assert result["applied"] is False
    assert result["kept_paras"] == paras
    assert [r["chapter"] for r in result["removed_chapters"]] == [2]


def test_apply_spine_chapter_cuts_respects_window_offset():
    paras = _chaptered_paras()[3:]  # 从第2章标题开始的窗口（跳过 3 段）
    result = split_novel.apply_spine_chapter_cuts(paras, 3, _spine_cut_plan([2]), apply=True)
    rows = result["removed_chapters"]
    assert rows[0]["first_source_unit_id"] == "U000004"  # 绝对单元号不受窗口影响
    assert result["kept_indices"][0] == 6


def test_apply_spine_chapter_cuts_reports_out_of_window_chapters():
    paras = _chaptered_paras(n_chapters=3)
    result = split_novel.apply_spine_chapter_cuts(paras, 0, _spine_cut_plan([2, 9]), apply=True)
    assert result["cut_chapters_outside_window"] == [9]


def test_episode_unit_spans_with_unit_indices_marks_gaps():
    paras = _chaptered_paras(n_chapters=3)  # 9 单元；剔第2章（索引 3,4,5）
    kept_indices = [0, 1, 2, 6, 7, 8]
    kept = [paras[i] for i in kept_indices]
    episodes = ["\n".join(kept[:4]), "\n".join(kept[4:])]  # 第1集跨剔除缝
    spans = split_novel.episode_unit_spans(episodes, paras, unit_indices=kept_indices)
    assert spans[0]["start_source_unit_id"] == "U000001"
    assert spans[0]["end_source_unit_id"] == "U000007"
    assert spans[0]["mapping_exact"] is True
    assert spans[0]["contains_spine_cut_gaps"] is True and spans[0]["unit_count"] == 4
    assert spans[1]["start_source_unit_id"] == "U000008"
    assert spans[1]["mapping_exact"] is True
    assert "contains_spine_cut_gaps" not in spans[1]


def test_split_plan_records_spine_pruning_and_skips_beam_on_gaps(tmp_path):
    root = tmp_path / "work"
    paras = _chaptered_paras(n_chapters=3)
    kept_indices = [0, 1, 2, 6, 7, 8]
    kept = [paras[i] for i in kept_indices]
    episodes = ["\n".join(kept[:3]), "\n".join(kept[3:])]
    source = root / "小说" / "测试.txt"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(paras), encoding="utf-8")
    pruning = split_novel.apply_spine_chapter_cuts(paras, 0, _spine_cut_plan([2]), apply=True)

    plan = split_novel.write_split_plan(
        str(root), "测试", str(source), episodes, 2,
        split_mode="test", genre_note="test", partial=False, source_paras=paras,
        selected_source_paras=kept, unit_indices=kept_indices, spine_pruning=pruning,
    )

    sp = plan["spine_pruning"]
    assert sp["applied"] is True
    assert "kept_paras" not in sp and "kept_indices" not in sp
    assert sp["removed_chapters"][0]["chapter"] == 2
    # 源单元轴保持完整（含被剔章节），beam 因 gap 诚实跳过
    assert plan["source_units"]["count"] == len(paras)
    assert plan["boundary_optimization"]["top_paths"] == []
    assert plan["boundary_optimization"]["spine_pruning_note"]
    md = (root / "脚本" / "_拆集机器索引.md").read_text(encoding="utf-8")
    assert "主线剪枝整章剔除" in md and "第2章" in md
