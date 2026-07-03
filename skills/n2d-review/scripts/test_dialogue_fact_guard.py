from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("dialogue_fact_guard.py")
spec = importlib.util.spec_from_file_location("dialogue_fact_guard", SCRIPT)
dialogue_fact_guard = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(dialogue_fact_guard)


def _write_base(root: Path, *, duplicate: bool = False, drift: bool = False) -> None:
    ep_dir = root / "脚本" / "第1集"
    ep_dir.mkdir(parents=True)
    (ep_dir / "voiceover.txt").write_text(
        "\n".join([
            "[镜头1·旁白·低] 十四岁的贺平生被审问。",
            "[镜头2·张老大·中] 多大了？",
            "[镜头3·贺平生·中] 我今年十四岁。",
            "[镜头4·张老大·中] 什么灵根？",
        ]),
        encoding="utf-8",
    )
    clip2_indices = [1, 2] if duplicate else [3, 4]
    (ep_dir / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "EP01_CLIP01", "label": "上", "voiceover_indices": [1, 2]},
            {"id": "EP01_CLIP02", "label": "下", "voiceover_indices": clip2_indices},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    char_dir = root / "设定库" / "characters"
    char_dir.mkdir(parents=True)
    (char_dir / "贺平生.md").write_text(
        "# 角色卡：贺平生\n- 年龄：十四岁。\n- 身高档：少年偏矮，约155-160cm。\n- 前期状态：五行灵根觉醒。\n",
        encoding="utf-8",
    )
    prompt_dir = root / "出视频" / "第1集" / "prompt"
    prompt_dir.mkdir(parents=True)
    extra = "他说自己15岁。" if drift else "audio_intent=native_speech"
    (prompt_dir / "01_clips.md").write_text(extra, encoding="utf-8")


def test_build_contract_keeps_physical_clip_dialogue_disjoint(tmp_path: Path) -> None:
    _write_base(tmp_path)
    contract = dialogue_fact_guard.build_contract(tmp_path, "第1集")
    dialogue_fact_guard.atomic_write_json(dialogue_fact_guard.contract_path(tmp_path, "第1集"), contract)

    report = dialogue_fact_guard.validate(tmp_path, "第1集")

    assert report["summary"]["block"] == 0
    assert contract["clips"][0]["allowed_voiceover_indices"] == [1, 2]
    assert contract["clips"][1]["allowed_voiceover_indices"] == [3, 4]
    assert contract["clips"][0]["allowed_narration_indices"] == [1]
    assert contract["clips"][0]["allowed_character_dialogue_indices"] == [2]


def test_duplicate_storyboard_voiceover_indices_block(tmp_path: Path) -> None:
    _write_base(tmp_path, duplicate=True)
    report = dialogue_fact_guard.validate(tmp_path, "第1集", require_contract=False)

    assert report["summary"]["block"] >= 1
    assert any(f["code"] == "duplicate_voiceover_index" for f in report["findings"])


def test_age_fact_drift_blocks_forbidden_numbers(tmp_path: Path) -> None:
    _write_base(tmp_path, drift=True)
    contract = dialogue_fact_guard.build_contract(tmp_path, "第1集")
    dialogue_fact_guard.atomic_write_json(dialogue_fact_guard.contract_path(tmp_path, "第1集"), contract)

    report = dialogue_fact_guard.validate(tmp_path, "第1集")

    assert any(f["code"] == "age_fact_drift" for f in report["findings"])


def test_duplicate_screen_text_blocks(tmp_path: Path) -> None:
    _write_base(tmp_path)
    ep_dir = tmp_path / "脚本" / "第1集"
    storyboard = json.loads((ep_dir / "storyboard.json").read_text(encoding="utf-8"))
    storyboard["clips"][0]["screen_text_lines"] = [{"text": "十四岁 · 五行灵根", "render_policy": "compose_overlay_only"}]
    storyboard["clips"][1]["screen_text_lines"] = [{"text": "十四岁 · 五行灵根", "render_policy": "compose_overlay_only"}]
    (ep_dir / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")

    report = dialogue_fact_guard.validate(tmp_path, "第1集", require_contract=False)

    assert any(f["code"] == "duplicate_screen_text_line" for f in report["findings"])


def test_quantity_fact_drift_blocks(tmp_path: Path) -> None:
    _write_base(tmp_path)
    voiceover = tmp_path / "脚本" / "第1集" / "voiceover.txt"
    voiceover.write_text(
        voiceover.read_text(encoding="utf-8") + "\n[镜头5·旁白·中] 一天至少二十趟，第五次来到水边。\n",
        encoding="utf-8",
    )
    prompt_dir = tmp_path / "出视频" / "第1集" / "prompt"
    (prompt_dir / "01_clips.md").write_text("一天十五趟，第四次到水边。", encoding="utf-8")
    contract = dialogue_fact_guard.build_contract(tmp_path, "第1集")
    dialogue_fact_guard.atomic_write_json(dialogue_fact_guard.contract_path(tmp_path, "第1集"), contract)

    report = dialogue_fact_guard.validate(tmp_path, "第1集")

    assert any(f["code"] == "quantity_fact_drift" for f in report["findings"])


def test_prompt_suffix_lists_allowed_dialogue_and_forbidden_facts(tmp_path: Path) -> None:
    _write_base(tmp_path)
    contract = dialogue_fact_guard.build_contract(tmp_path, "第1集")
    dialogue_fact_guard.atomic_write_json(dialogue_fact_guard.contract_path(tmp_path, "第1集"), contract)

    suffix = dialogue_fact_guard.contract_prompt_suffix(tmp_path, "第1集", "Clip_02")

    assert "allowed_voiceover_indices=[3, 4]" in suffix
    assert "我今年十四岁" in suffix
    assert "15岁" in suffix


def test_prompt_suffix_lists_screen_text_overlay(tmp_path: Path) -> None:
    _write_base(tmp_path)
    ep_dir = tmp_path / "脚本" / "第1集"
    storyboard = json.loads((ep_dir / "storyboard.json").read_text(encoding="utf-8"))
    storyboard["clips"][1]["screen_text_lines"] = [{
        "text": "十四岁 · 五行灵根",
        "purpose": "静音身份钩子",
        "render_policy": "compose_overlay_only",
    }]
    (ep_dir / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    contract = dialogue_fact_guard.build_contract(tmp_path, "第1集")
    dialogue_fact_guard.atomic_write_json(dialogue_fact_guard.contract_path(tmp_path, "第1集"), contract)

    suffix = dialogue_fact_guard.contract_prompt_suffix(tmp_path, "第1集", "Clip_02")

    assert "screen_text_overlay" in suffix
    assert "十四岁 · 五行灵根" in suffix
    assert "compose_stage_only" in suffix
    assert "video_model_must_not_generate_narration_voice" in suffix
    assert "不要在视频画面里烤字" in suffix
