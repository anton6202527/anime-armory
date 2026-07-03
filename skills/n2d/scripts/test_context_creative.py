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


def test_script_stage2_context_and_loop_include_director_pack(tmp_path: Path):
    _work(tmp_path)
    pack = context_pack.build_pack(str(tmp_path), "第1集", "script_stage2")
    rels = [item["relpath"] for item in pack["files"]]
    assert "脚本/第1集/director_beat_sheet.json" in rels
    packet = creative_loop.build_packet(str(tmp_path), "第1集", "script_stage2")
    assert any("P-2 导演排戏包" in rubric for item in packet["loop"] for rubric in item.get("rubric", []))
