import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("codex_image_runner.py")
SPEC = importlib.util.spec_from_file_location("codex_image_runner", MODULE_PATH)
codex_image_runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = codex_image_runner
SPEC.loader.exec_module(codex_image_runner)


def write_storyboard(root: Path) -> None:
    path = root / "脚本" / "第1集" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "clips": [
                    {
                        "id": "EP01_CLIP12",
                        "firstframe_png": "出图/第1集/图片/镜头12_炼化噬妖.png",
                        "continuity": {
                            "endframe_png": "出图/第1集/图片/镜头12_end.png",
                            "anchors": [
                                {"anchor_png": "出图/第1集/图片/镜头12_炼化噬妖_a1.png"},
                                {"anchor_png": "出图/第1集/图片/镜头12_炼化噬妖_a2.png"},
                            ],
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def write_prompt(root: Path, body: str) -> None:
    path = root / "出图" / "第1集" / "prompt" / "01_分镜出图.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def test_load_sections_falls_back_to_storyboard_targets(tmp_path: Path) -> None:
    write_storyboard(tmp_path)
    write_prompt(tmp_path, "## 镜头 12（EP01_CLIP12 · 炼化噬妖）\n正文，无目标行。\n")

    section = codex_image_runner.load_sections(tmp_path, "第1集")[0]

    assert "镜头12_炼化噬妖.png" in section.target_line
    assert "镜头12_炼化噬妖_a2.png" in section.target_line
    assert (
        codex_image_runner.target_for_shot("Clip_12", section, "第1集").rel_path
        == "出图/第1集/图片/镜头12_炼化噬妖.png"
    )
    assert (
        codex_image_runner.target_for_shot("Clip_12_a2", section, "第1集").rel_path
        == "出图/第1集/图片/镜头12_炼化噬妖_a2.png"
    )
    assert (
        codex_image_runner.target_for_shot("Clip_12_end", section, "第1集").rel_path
        == "出图/第1集/图片/镜头12_end.png"
    )


def test_explicit_prompt_target_line_wins_over_storyboard(tmp_path: Path) -> None:
    write_storyboard(tmp_path)
    write_prompt(
        tmp_path,
        "## 镜头 12（EP01_CLIP12 · 炼化噬妖）\n"
        "**目标**：`出图/第1集/图片/custom_first.png` `出图/第1集/图片/custom_end.png`\n",
    )

    section = codex_image_runner.load_sections(tmp_path, "第1集")[0]

    assert section.target_line == "`出图/第1集/图片/custom_first.png` `出图/第1集/图片/custom_end.png`"


def test_shared_targets_include_character_base_pack_and_registry_expressions(tmp_path: Path) -> None:
    prompt_dir = tmp_path / "出图" / "共享" / "prompt"
    prompt_dir.mkdir(parents=True)
    (prompt_dir / "角色定妆.md").write_text(
        "# 角色定妆 Prompt\n\n"
        "## ① CHAR_01 沈念 / 林婉儿·常态（待生成）\n"
        "**目标存档**：`出图/共享/图片/定妆_沈念_常态.png`\n"
        "**角色定妆组**：正面主参考 `定妆_沈念_常态.png`；"
        "45°参考 `定妆_沈念_常态_45度.png`；"
        "侧面参考 `定妆_沈念_常态_侧.png`；"
        "背面参考 `定妆_沈念_常态_背.png`；"
        "服装参考 `定妆_沈念_常态_半身.png`；"
        "基础脸部参考 `定妆_沈念_常态_脸部特写.png`；"
        "人审拼版 `定妆_沈念_常态_三视图.png`。\n"
        "## ② CHAR_01 沈念 / 林婉儿·觉醒态（待生成）\n"
        "**目标存档**：`出图/共享/图片/定妆_沈念_觉醒态.png`\n",
        encoding="utf-8",
    )
    (prompt_dir / "场景定妆.md").write_text("", encoding="utf-8")
    (prompt_dir / "道具定妆.md").write_text("", encoding="utf-8")
    (prompt_dir / "特效定妆.md").write_text("", encoding="utf-8")
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_01",
                        "forms": [
                            {
                                "form": "常态",
                                "reference_group": {
                                    "front": "出图/共享/图片/定妆_沈念_常态.png",
                                    "expressions": [
                                        {"emotion": "冷静", "path": "出图/共享/图片/定妆_沈念_常态_表情_冷静.png"}
                                    ],
                                },
                            },
                            {
                                "form": "觉醒态",
                                "reference_group": {"front": "出图/共享/图片/定妆_沈念_觉醒态.png"},
                            },
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    targets = codex_image_runner.load_shared_sections(tmp_path)
    by_path = {target.rel_path: target for target in targets}

    assert "出图/共享/图片/定妆_沈念_常态_45度.png" in by_path
    assert "出图/共享/图片/定妆_沈念_常态_脸部特写.png" in by_path
    assert "出图/共享/图片/定妆_沈念_常态_表情_冷静.png" in by_path
    assert "45°" in by_path["出图/共享/图片/定妆_沈念_常态_45度.png"].variant_note
    assert by_path["出图/共享/图片/定妆_沈念_觉醒态.png"].section.title.startswith("## ②")
