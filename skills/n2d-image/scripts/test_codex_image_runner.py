import importlib.util
import json
import base64
import subprocess
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("codex_image_runner.py")
SPEC = importlib.util.spec_from_file_location("codex_image_runner", MODULE_PATH)
codex_image_runner = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = codex_image_runner
SPEC.loader.exec_module(codex_image_runner)


def test_format_codex_failure_keeps_stdout_and_stderr():
    proc = subprocess.CompletedProcess(["codex"], 2, stdout="jsonl api error", stderr="stderr detail")
    msg = codex_image_runner.format_codex_failure(proc)
    assert "codex exit 2" in msg
    assert "stderr=stderr detail" in msg
    assert "stdout=jsonl api error" in msg


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


def test_shared_target_skips_existing_png_without_force(tmp_path: Path, monkeypatch) -> None:
    final = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png"
    final.parent.mkdir(parents=True)
    final.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    registry = tmp_path / "出图" / "共享" / "identity_registry.json"
    registry.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_01",
                        "forms": [
                            {
                                "form": "常态",
                                "reference_group": {
                                    "front": {
                                        "path": "出图/共享/图片/定妆_沈念_常态.png",
                                        "status": "planned",
                                    }
                                },
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## CHAR_01 沈念",
        body="角色定妆",
        target_line="`出图/共享/图片/定妆_沈念_常态.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_01::定妆_沈念_常态",
        clip="CHAR_01",
        mode="shared",
        rel_path="出图/共享/图片/定妆_沈念_常态.png",
        section=section,
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("existing shared PNG should not call Codex")

    monkeypatch.setattr(codex_image_runner, "run_codex", fail_if_called)

    assert codex_image_runner.process_target(
        tmp_path,
        "第1集",
        target,
        task_id="new-task",
        timeout_sec=1,
        dry_run=False,
        force=False,
    )
    data = json.loads(registry.read_text(encoding="utf-8"))
    front = data["characters"][0]["forms"][0]["reference_group"]["front"]
    assert front["status"] == "review_pending"
    assert front["human_review"]["status"] == "pending"


def test_codex_blocks_text_only_character_split_makeup(tmp_path: Path, monkeypatch) -> None:
    section = codex_image_runner.ClipSection(
        clip="CHAR_01",
        title="## CHAR_01 沈念",
        body="角色定妆",
        target_line="`出图/共享/图片/CHAR_SHENNIAN_常态_45度.png`",
    )
    target = codex_image_runner.Target(
        shot="CHAR_01::CHAR_SHENNIAN_常态_45度",
        clip="CHAR_01",
        mode="shared",
        rel_path="出图/共享/图片/CHAR_SHENNIAN_常态_45度.png",
        section=section,
    )

    def fail_if_called(*args, **kwargs):
        raise AssertionError("text-only Codex must not generate split makeup refs")

    monkeypatch.setattr(codex_image_runner, "run_codex", fail_if_called)
    monkeypatch.delenv("N2D_ALLOW_CODEX_TEXT_MAKEUP_VARIANTS", raising=False)

    assert not codex_image_runner.process_target(
        tmp_path,
        "第1集",
        target,
        task_id="guard-test",
        timeout_sec=1,
        dry_run=False,
        force=False,
    )


def test_reference_bundle_resolves_ready_character_and_asset_refs(tmp_path: Path) -> None:
    ref = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    prop = tmp_path / "出图" / "共享" / "图片" / "定妆_毒酒瓷瓶.png"
    prop.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{
                    "form": "常态",
                    "reference_group": {
                        "front": {"path": "出图/共享/图片/定妆_沈念_常态.png", "status": "ready"}
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text(
        json.dumps({
            "assets": [{
                "id": "PROP_01",
                "type": "prop",
                "reference_group": {"primary": {"path": "出图/共享/图片/定妆_毒酒瓷瓶.png", "status": "ready"}},
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body=(
            "**资产身份注册层**：`CHAR_01/常态*` -> identity_registry.json；"
            "`PROP_01` -> asset_registry.json。\n"
            "**参考图**：角色 `CHAR_01/常态`，道具 `PROP_01`。\n"
            "角色 CU 特写，手持道具。"
        ),
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert bundle["true_image_reference_support"] is True
    assert bundle["reference_input_mode"] == "codex_exec_image_flags"
    assert {item["kind"] for item in bundle["items"]} == {"character", "asset"}
    assert any("定妆_沈念_常态.png" in p for item in bundle["items"] for p in item["paths"])
    assert any("定妆_毒酒瓷瓶.png" in p for item in bundle["items"] for p in item["paths"])

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)
    codex_image_runner.attach_reference_inputs(bundle, inputs)
    cmd = codex_image_runner.build_codex_command(tmp_path, "prompt", inputs)

    assert bundle["cli_image_input_count"] == 2
    assert len(inputs) == 2
    assert "--image" in cmd
    assert any(str(ref) in part for part in cmd)
    assert any(str(prop) in part for part in cmd)


def _write_carried_identity_fixtures(tmp_path: Path, asset: dict) -> codex_image_runner.Target:
    """Shared fixture: a locked 沈念 face anchor + a VFX asset that depicts her."""
    face = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_脸部特写.png"
    face.parent.mkdir(parents=True)
    face.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    shared = tmp_path / "出图" / "共享"
    (shared / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{
                    "form": "冷宫废妃常态",
                    "reference_group": {
                        "face_anchor_refs": [
                            {"path": "出图/共享/图片/定妆_沈念_脸部特写.png", "status": "ready"}
                        ]
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (shared / "asset_registry.json").write_text(
        json.dumps({"assets": [asset]}, ensure_ascii=False), encoding="utf-8"
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_99",
        title="## ① VFX_01 万妖血脉觉醒前兆",
        body="**目标存档**：`出图/共享/图片/定妆_万妖血脉觉醒前兆.png`\nVFX 定妆图，左腕暗金细纹。",
        target_line="`出图/共享/图片/定妆_万妖血脉觉醒前兆.png`",
    )
    target = codex_image_runner.Target(
        shot="VFX_01::定妆_万妖血脉觉醒前兆",
        clip="VFX_01",
        mode="shared",
        rel_path="出图/共享/图片/定妆_万妖血脉觉醒前兆.png",
        section=section,
    )
    setattr(target, "aliases", {"VFX_01", "万妖血脉觉醒前兆"})
    return target


def test_vfx_asset_inherits_carried_character_face_via_explicit_field(tmp_path: Path) -> None:
    target = _write_carried_identity_fixtures(tmp_path, {
        "id": "VFX_01",
        "type": "vfx",
        "name": "万妖血脉觉醒前兆",
        "carries_identity": ["CHAR_01/冷宫废妃常态"],
        "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
    })

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert bundle["carried_identity"] == ["CHAR_01/冷宫废妃常态"]
    assert any(item["kind"] == "character" and item["id"] == "CHAR_01" for item in bundle["items"])
    assert any("定妆_沈念_脸部特写.png" in p for item in bundle["items"] for p in item["paths"])

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)
    assert any(str(i.get("role")) == "character" for i in inputs)


def test_vfx_asset_infers_carried_identity_from_structure_when_field_absent(tmp_path: Path) -> None:
    # Legacy registry: no carries_identity field, but the structure text names CHAR_01.
    target = _write_carried_identity_fixtures(tmp_path, {
        "id": "VFX_01",
        "type": "vfx",
        "name": "万妖血脉觉醒前兆",
        "constraints": {"structure": "暗金细纹从 CHAR_01 左腕旧疤裂出"},
        "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
    })

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert "CHAR_01" in bundle["carried_identity"]
    assert any("定妆_沈念_脸部特写.png" in p for item in bundle["items"] for p in item["paths"])


def test_non_whitelisted_type_person_plate_infers_carried_identity(tmp_path: Path) -> None:
    # type-whitelist hole: a PROP whose type ('prop') is NOT identity-bearing, but
    # whose plate clearly renders her face (a mirror reflection), must still inherit
    # the face anchor via person-context inference.
    target = _write_carried_identity_fixtures(tmp_path, {
        "id": "PROP_09",
        "type": "prop",
        "name": "铜镜",
        "constraints": {"structure": "铜镜映出 CHAR_01 的脸，面容清冷"},
        "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
    })
    setattr(target, "aliases", {"PROP_09"})

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert "CHAR_01" in bundle["carried_identity"]
    assert any("定妆_沈念_脸部特写.png" in p for item in bundle["items"] for p in item["paths"])


def test_non_identity_asset_does_not_infer_carried_identity(tmp_path: Path) -> None:
    # A LOC plate that merely mentions a character must NOT pull a face into a room.
    target = _write_carried_identity_fixtures(tmp_path, {
        "id": "LOC_09",
        "type": "location",
        "name": "冷宫寝屋",
        "constraints": {"structure": "CHAR_01 的寝宫，空镜"},
        "reference_group": {"primary": "出图/共享/图片/定妆_万妖血脉觉醒前兆.png"},
    })
    setattr(target, "aliases", {"LOC_09", "冷宫寝屋"})

    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    assert bundle["carried_identity"] == []
    assert all(item["kind"] != "character" for item in bundle["items"])


def test_tailframe_reference_inputs_include_first_and_midframe_sources(tmp_path: Path) -> None:
    first = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    mid = tmp_path / "出图" / "第1集" / "图片" / "Clip_01_mid.png"
    end = tmp_path / "出图" / "第1集" / "图片" / "Clip_01_end.png"
    first.parent.mkdir(parents=True)
    first.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    mid.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    (tmp_path / "出图" / "共享").mkdir(parents=True)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text('{"characters":[]}', encoding="utf-8")
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="**资产身份注册层**：无人物。",
        target_line=(
            "`出图/第1集/图片/Clip_01.png` "
            "`出图/第1集/图片/Clip_01_mid.png` "
            "`出图/第1集/图片/Clip_01_end.png`"
        ),
    )
    target = codex_image_runner.Target(
        shot="Clip_01_end",
        clip="Clip_01",
        mode="tailframe",
        rel_path="出图/第1集/图片/Clip_01_end.png",
        section=section,
    )
    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert [item["rel_path"] for item in inputs] == [
        "出图/第1集/图片/Clip_01.png",
        "出图/第1集/图片/Clip_01_mid.png",
    ]
    assert {item["source"] for item in inputs} == {"same_clip_firstframe", "same_clip_anchor"}


def test_firstframe_reference_inputs_include_explicit_previous_clip_source(tmp_path: Path) -> None:
    source = tmp_path / "出图" / "第1集" / "图片" / "Clip_07.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    ref = tmp_path / "出图" / "共享" / "图片" / "CHAR_01.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({
            "characters": [{
                "id": "CHAR_01",
                "forms": [{
                    "form": "觉醒态",
                    "reference_group": {
                        "front": {"path": "出图/共享/图片/CHAR_01.png", "status": "ready"}
                    },
                }],
            }]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    write_prompt(
        tmp_path,
        "## Clip 07（EP01_CLIP07）\n"
        "**目标**：`出图/第1集/图片/Clip_07.png`\n\n"
        "## Clip 08（EP01_CLIP08）\n"
        "**目标**：`出图/第1集/图片/Clip_08.png`\n"
        "**生成方式**：image2image / 多图参考派生，以 Clip_07 成图或脸部特写为母图。\n"
        "**资产身份注册层**：`CHAR_01/觉醒态*` -> `identity_registry.json`。\n",
    )
    sections = codex_image_runner.load_sections(tmp_path, "第1集")
    section = codex_image_runner.section_for(sections, "Clip_08")
    target = codex_image_runner.target_for_shot("Clip_08", section, "第1集")
    bundle = codex_image_runner.reference_bundle_for_target(tmp_path, "第1集", target)

    inputs = codex_image_runner.codex_reference_inputs_for_target(tmp_path, "第1集", target, bundle)

    assert inputs[0]["rel_path"] == "出图/第1集/图片/Clip_07.png"
    assert inputs[0]["role"] == "source_frame"
    assert inputs[0]["source"] == "explicit_source_clip"
    assert "出图/共享/图片/CHAR_01.png" in [item["rel_path"] for item in inputs]


def test_target_image_qc_treats_pixel_outfit_as_advisory_by_default(tmp_path: Path, monkeypatch) -> None:
    target_png = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    target_png.parent.mkdir(parents=True)
    target_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "face_reference_coverage": {"missing": []},
            "checks": {
                "outfit": {"shots": [{
                    "png": "图片/Clip_01.png",
                    "verdict": "block",
                    "score": 0.49,
                    "floor": 0.69,
                }]}
            },
            "lint": {"findings": []},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    monkeypatch.setattr(codex_image_runner.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))
    monkeypatch.delenv("N2D_TARGET_QC_STRICT_PIXEL", raising=False)

    assert codex_image_runner.run_target_image_qc(tmp_path, "第1集", target)


def test_target_image_qc_can_strictly_block_pixel_outfit(tmp_path: Path, monkeypatch) -> None:
    target_png = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    target_png.parent.mkdir(parents=True)
    target_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    report = tmp_path / "生产数据" / "image_qc" / "第1集" / "image_qc_第1集.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps({
            "qc_environment": {"precision_level": "full"},
            "face_reference_coverage": {"missing": []},
            "checks": {
                "outfit": {"shots": [{
                    "png": "图片/Clip_01.png",
                    "verdict": "block",
                    "score": 0.49,
                    "floor": 0.69,
                }]}
            },
            "lint": {"findings": []},
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body="",
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    monkeypatch.setattr(codex_image_runner.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, "", ""))
    monkeypatch.setenv("N2D_TARGET_QC_STRICT_PIXEL", "1")

    assert not codex_image_runner.run_target_image_qc(tmp_path, "第1集", target)


def test_codex_high_risk_character_shot_passes_auditable_image_inputs(tmp_path: Path, monkeypatch) -> None:
    ref = tmp_path / "出图" / "共享" / "图片" / "定妆_沈念_常态.png"
    ref.parent.mkdir(parents=True)
    ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    other_ref = tmp_path / "出图" / "共享" / "图片" / "定妆_小禾_常态.png"
    other_ref.write_bytes(b"\x89PNG\r\n\x1a\n" + b"1" * 64)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({
            "characters": [
                {
                    "id": "CHAR_01",
                    "forms": [{
                        "form": "常态",
                        "reference_group": {
                            "front": {"path": "出图/共享/图片/定妆_沈念_常态.png", "status": "ready"}
                        },
                    }],
                },
                {
                    "id": "CHAR_02",
                    "forms": [{
                        "form": "常态",
                        "reference_group": {
                            "front": {"path": "出图/共享/图片/定妆_小禾_常态.png", "status": "ready"}
                        },
                    }],
                },
            ]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "出图" / "共享" / "asset_registry.json").write_text('{"assets":[]}', encoding="utf-8")
    section = codex_image_runner.ClipSection(
        clip="Clip_01",
        title="## Clip 01",
        body=(
            "**资产身份注册层**：`CHAR_01/常态*` -> identity_registry.json。\n"
            "`CHAR_01/常态` CU 面部特写，惊恐落泪。\n"
            "**尾帧专用重抽提示**：本镜不生成 `CHAR_02/常态`。"
        ),
        target_line="`出图/第1集/图片/Clip_01.png`",
    )
    target = codex_image_runner.Target(
        shot="Clip_01",
        clip="Clip_01",
        mode="firstframe",
        rel_path="出图/第1集/图片/Clip_01.png",
        section=section,
    )

    seen = {}

    def fake_run_codex(repo, prompt, timeout_sec, reference_inputs):
        seen["reference_inputs"] = list(reference_inputs)
        raw = b"\x89PNG\r\n\x1a\n" + b"2" * 64
        payload = base64.b64encode(raw).decode("ascii")
        stdout = json.dumps({"payload": {"type": "image_generation_end", "result": payload}})
        return subprocess.CompletedProcess(["codex"], 0, stdout=stdout, stderr="")

    monkeypatch.setattr(codex_image_runner, "run_codex", fake_run_codex)

    assert codex_image_runner.process_target(
        tmp_path,
        "第1集",
        target,
        task_id="risk-test",
        timeout_sec=1,
        dry_run=False,
        force=False,
    )
    assert len(seen["reference_inputs"]) == 1
    assert seen["reference_inputs"][0]["rel_path"] == "出图/共享/图片/定妆_沈念_常态.png"

    final = tmp_path / "出图" / "第1集" / "图片" / "Clip_01.png"
    assert codex_image_runner.png_valid(final)
    assert (
        tmp_path
        / "生产数据"
        / "codex_reference_bundles"
        / "第1集"
        / "Clip_01.json"
    ).is_file()
    manifest = json.loads((
        tmp_path
        / "生产数据"
        / "codex_reference_bundles"
        / "第1集"
        / "Clip_01.json"
    ).read_text(encoding="utf-8"))
    assert manifest["cli_image_input_count"] == 1
    assert manifest["cli_image_inputs"][0]["rel_path"] == "出图/共享/图片/定妆_沈念_常态.png"
