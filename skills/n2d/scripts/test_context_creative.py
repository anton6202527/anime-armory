from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import context_pack
import creative_loop


def _work(root: Path) -> None:
    (root / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    (root / "_进度.md").write_text("| 集 | 出图prompt |\n|---|---|\n| 第1集 | ⬜ |\n", encoding="utf-8")
    ep = root / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "storyboard.json").write_text('{"kind":"storyboard","clips":[{"id":"Clip_01"}]}', encoding="utf-8")


def test_context_pack_collects_stage_files(tmp_path: Path):
    _work(tmp_path)
    pack = context_pack.build_pack(str(tmp_path), "第1集", "image_prompt")
    rels = [item["relpath"] for item in pack["files"]]
    assert "_设置.md" in rels
    assert "脚本/第1集/storyboard.json" in rels
    assert any(item["exists"] for item in pack["files"])
    outputs = context_pack.write_pack(pack)
    assert Path(outputs["json"]).is_file()
    assert Path(outputs["markdown"]).is_file()
    assert "生产数据/views/context_packs" in outputs["rel_markdown"]


def test_context_pack_settings_preview_excludes_superseded_audit_fact(tmp_path: Path):
    (tmp_path / "_设置.md").write_text(
        "# 设置\n\n"
        "- 项目规模：长篇量产  # source=source_analysis\n"
        "- 画幅：9:16  # source=project_default\n\n"
        "## 记录\n"
        "- 2026-07-14 数据校正：当前为819个唯一章节；先前口径不再作为生产事实\n"
        "- 2026-07-14 当前只推进内部开发\n"
        "- 2026-07-14 源书共830章、约565万字，按长篇量产配置一致性与打样门\n",
        encoding="utf-8",
    )

    pack = context_pack.build_pack(str(tmp_path), "第1集", "script_stage1")
    settings = pack["settings_context"]
    settings_file = next(item for item in pack["files"] if item["relpath"] == "_设置.md")

    assert settings["status"] == "ok"
    assert settings["effective_settings"]["项目规模"] == {
        "value": "长篇量产",
        "source": "source_analysis",
    }
    assert settings["authority"]["records_can_override_effective_settings"] is False
    assert settings["record_summary"]["records_seen"] == 3
    assert settings["record_summary"]["corrections_included"] == 1
    assert settings_file["preview_policy"] == "settings_region_plus_bounded_corrections"
    assert "数据校正：当前为819个唯一章节" in settings_file["preview"]
    assert "源书共830章、约565万字，按长篇量产配置一致性与打样门" not in settings_file["preview"]
    assert "当前只推进内部开发" not in settings_file["preview"]


def test_context_pack_settings_corrections_are_hard_capped(tmp_path: Path):
    records = "\n".join(
        f"- 2026-07-{14 - i:02d} 数据校正：口径 {i}" for i in range(6)
    )
    (tmp_path / "_设置.md").write_text(
        "- 制作模式: 原生音画\n\n## 记录\n" + records + "\n",
        encoding="utf-8",
    )

    pack = context_pack.build_pack(str(tmp_path), "第1集", "script_stage1")
    settings = pack["settings_context"]

    assert settings["record_summary"]["corrections_seen"] == 6
    assert settings["record_summary"]["corrections_included"] == 3
    assert [item["text"] for item in settings["recent_corrections"]] == [
        "2026-07-14 数据校正：口径 0",
        "2026-07-13 数据校正：口径 1",
        "2026-07-12 数据校正：口径 2",
    ]


def test_context_pack_settings_supports_no_record_and_legacy_dated_lines(tmp_path: Path):
    (tmp_path / "_设置.md").write_text(
        "- 制作模式: 配音先行\n"
        "- 2025-01-01 初始估计为200集\n"
        "- 2025-01-02 数据校正：现行口径为20集\n",
        encoding="utf-8",
    )

    pack = context_pack.build_pack(str(tmp_path), "第1集", "script_stage1")
    settings = pack["settings_context"]

    assert settings["effective_settings"] == {
        "制作模式": {"value": "配音先行", "source": ""},
    }
    assert settings["record_summary"]["format"] == "legacy_dated_lines"
    assert [item["text"] for item in settings["recent_corrections"]] == [
        "2025-01-02 数据校正：现行口径为20集",
    ]

    (tmp_path / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    no_records = context_pack.build_pack(str(tmp_path), "第1集", "script_stage1")["settings_context"]
    assert no_records["status"] == "ok"
    assert no_records["record_summary"]["format"] == "none"
    assert no_records["recent_corrections"] == []


def test_context_pack_settings_parse_failure_never_falls_back_to_raw_history(
    tmp_path: Path, monkeypatch,
):
    obsolete = "OBSOLETE_FACT_MUST_NOT_REACH_DOWNSTREAM"
    (tmp_path / "_设置.md").write_text(
        f"- 制作模式: 原生音画\n\n## 记录\n- 2025-01-01 {obsolete}\n",
        encoding="utf-8",
    )

    def explode(_root):
        raise RuntimeError("synthetic settings parser failure")

    monkeypatch.setattr(context_pack.project_settings, "settings_context_snapshot", explode)
    pack = context_pack.build_pack(str(tmp_path), "第1集", "script_stage1")
    settings_file = next(item for item in pack["files"] if item["relpath"] == "_设置.md")

    assert pack["settings_context"]["status"] == "parse_error"
    assert pack["settings_context"]["effective_settings"] == {}
    assert obsolete not in settings_file["preview"]
    assert "raw _设置.md history was intentionally omitted" in settings_file["preview"]


def test_context_pack_markdown_exposes_composite_genres_and_untriggered_state(tmp_path: Path):
    (tmp_path / "_设置.md").write_text("- 题材: 系统流+修仙+悬疑\n", encoding="utf-8")
    pack = context_pack.build_pack(str(tmp_path), "第1集", "script_stage1")

    markdown = context_pack.render_markdown(pack)

    assert "genre packs：chuanyue, xianxia, suspense" in markdown
    assert "genre scene activation：storyboard_missing" in markdown


def test_script_stage1_does_not_require_midstart_pack_for_first_episode(tmp_path: Path):
    (tmp_path / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text("| 集 | 剧本改编 |\n|---|---|\n| 第1集 | ⬜ |\n", encoding="utf-8")
    ep = tmp_path / "脚本" / "第1集"
    ep.mkdir(parents=True)
    (ep / "raw.txt").write_text("第一集正文", encoding="utf-8")

    pack = context_pack.build_pack(str(tmp_path), "第1集", "script_stage1")

    assert "设定库/中段开工前情资产包.md" not in [item["relpath"] for item in pack["files"]]
    assert "设定库/中段开工前情资产包.md" not in pack["missing_required_files"]


def test_script_stage1_requires_midstart_pack_for_late_episode_without_first_raw(tmp_path: Path):
    (tmp_path / "_设置.md").write_text("- 制作模式: 原生音画\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text("| 集 | 剧本改编 |\n|---|---|\n| 第48集 | ⬜ |\n", encoding="utf-8")
    ep = tmp_path / "脚本" / "第48集"
    ep.mkdir(parents=True)
    (ep / "raw.txt").write_text("中段正文", encoding="utf-8")

    pack = context_pack.build_pack(str(tmp_path), "第48集", "script_stage1")

    assert "设定库/中段开工前情资产包.md" in [item["relpath"] for item in pack["files"]]
    assert "设定库/中段开工前情资产包.md" in pack["missing_required_files"]


def test_creative_loop_packet_declares_evaluator_optimizer(tmp_path: Path):
    packet = creative_loop.build_packet(str(tmp_path), "第1集", "video_prompt")
    steps = [item["step"] for item in packet["loop"]]
    assert steps == ["generate", "evaluate", "optimize", "finalize"]
    assert packet["action_contract"]["specialist"] == "n2d-visual-agent"
    assert any("template_contract" in rubric for item in packet["loop"] for rubric in item.get("rubric", []))
    outputs = creative_loop.write_packet(packet)
    assert Path(outputs["json"]).is_file()
    assert "生产数据/views/creative_loops" in outputs["rel_markdown"]


def test_script_stage2_context_and_loop_include_director_pack(tmp_path: Path):
    _work(tmp_path)
    pack = context_pack.build_pack(str(tmp_path), "第1集", "script_stage2")
    rels = [item["relpath"] for item in pack["files"]]
    assert "脚本/第1集/director_beat_sheet.json" in rels
    packet = creative_loop.build_packet(str(tmp_path), "第1集", "script_stage2")
    assert any("P-2 导演排戏包" in rubric for item in packet["loop"] for rubric in item.get("rubric", []))
