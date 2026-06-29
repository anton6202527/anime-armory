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


def test_creative_loop_packet_declares_evaluator_optimizer(tmp_path: Path):
    packet = creative_loop.build_packet(str(tmp_path), "第1集", "video_prompt")
    steps = [item["step"] for item in packet["loop"]]
    assert steps == ["generate", "evaluate", "optimize", "finalize"]
    assert packet["action_contract"]["specialist"] == "n2d-visual-agent"
    assert any("template_contract" in rubric for item in packet["loop"] for rubric in item.get("rubric", []))
    outputs = creative_loop.write_packet(packet)
    assert Path(outputs["json"]).is_file()
