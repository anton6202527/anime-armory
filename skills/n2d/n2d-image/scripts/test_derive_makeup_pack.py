import importlib.util
import json
import sys
from pathlib import Path

import pytest

Image = pytest.importorskip("PIL.Image")


MODULE_PATH = Path(__file__).with_name("derive_makeup_pack.py")
SPEC = importlib.util.spec_from_file_location("derive_makeup_pack", MODULE_PATH)
derive_makeup_pack = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = derive_makeup_pack
SPEC.loader.exec_module(derive_makeup_pack)


def _png(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (800, 1200)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def test_derive_project_splits_turnaround_and_front_crops(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    image_dir = root / "出图" / "共享" / "图片"
    front = image_dir / "CHAR_TEST_常态.png"
    turn = image_dir / "CHAR_TEST_常态_三视图.png"
    _png(front, (200, 30, 30))
    turn.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 1200), (0, 0, 0))
    for i, color in enumerate(((10, 10, 10), (80, 10, 10), (10, 80, 10), (10, 10, 80))):
        block = Image.new("RGB", (200, 1200), color)
        img.paste(block, (i * 200, 0))
    img.save(turn)

    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_TEST",
                        "forms": [
                            {
                                "form": "常态",
                                "asset_key": "CHAR_TEST_常态",
                                "reference_group": {
                                    "front": {"path": "出图/共享/图片/CHAR_TEST_常态.png", "status": "ready"},
                                    "three_quarter": {
                                        "path": "出图/共享/图片/CHAR_TEST_常态_45度.png",
                                        "status": "planned",
                                    },
                                    "side": {
                                        "path": "出图/共享/图片/CHAR_TEST_常态_侧.png",
                                        "status": "planned",
                                    },
                                    "back": {
                                        "path": "出图/共享/图片/CHAR_TEST_常态_背.png",
                                        "status": "planned",
                                    },
                                    "half_body": {
                                        "path": "出图/共享/图片/CHAR_TEST_常态_半身.png",
                                        "status": "planned",
                                    },
                                    "turnaround": {
                                        "path": "出图/共享/图片/CHAR_TEST_常态_三视图.png",
                                        "status": "ready",
                                    },
                                    "face_anchor_refs": [
                                        {
                                            "label": "基础脸锚",
                                            "path": "出图/共享/图片/CHAR_TEST_常态_脸部特写.png",
                                            "status": "planned",
                                        }
                                    ],
                                },
                                "reference_atlas": {
                                    "base_views": {
                                        "front": {"path": "出图/共享/图片/CHAR_TEST_常态.png", "status": "ready"},
                                        "three_quarter": {
                                            "path": "出图/共享/图片/CHAR_TEST_常态_45度.png",
                                            "status": "planned",
                                        },
                                        "side": {"path": "出图/共享/图片/CHAR_TEST_常态_侧.png", "status": "planned"},
                                        "back": {"path": "出图/共享/图片/CHAR_TEST_常态_背.png", "status": "planned"},
                                        "half_body": {
                                            "path": "出图/共享/图片/CHAR_TEST_常态_半身.png",
                                            "status": "planned",
                                        },
                                    },
                                    "face_anchor_refs": [
                                        {
                                            "label": "基础脸锚",
                                            "path": "出图/共享/图片/CHAR_TEST_常态_脸部特写.png",
                                            "status": "planned",
                                        }
                                    ],
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

    summary = derive_makeup_pack.derive_project(root, write=True, force=True)

    assert len(summary["derived"]) == 5
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    form = data["characters"][0]["forms"][0]
    rg = form["reference_group"]
    assert rg["three_quarter"]["status"] == "ready"
    assert rg["three_quarter"]["derivation"]["method"] == "turnaround_split"
    assert rg["side"]["derivation"]["source_path"] == "出图/共享/图片/CHAR_TEST_常态_三视图.png"
    assert rg["half_body"]["derivation"]["method"] == "front_crop"
    assert rg["face_anchor_refs"][0]["derivation"]["method"] == "front_crop"
    assert rg["face_anchor_refs"][0]["derivation"]["crop_box"] == [304, 132, 456, 372]
    assert rg["three_quarter"]["sha256"] == derive_makeup_pack._sha256(root / rg["three_quarter"]["path"])
    assert rg["three_quarter"]["dimensions"] == {"width": 800, "height": 1200}
    assert rg["face_anchor_refs"][0]["sha256"] == derive_makeup_pack._sha256(root / rg["face_anchor_refs"][0]["path"])
    assert form["reference_atlas"]["base_views"]["back"]["derivation"]["source_sha256"]
    for rel in (
        rg["three_quarter"]["path"],
        rg["side"]["path"],
        rg["back"]["path"],
        rg["half_body"]["path"],
    ):
        out = root / rel
        assert out.exists()
        assert Image.open(out).size == (800, 1200)
    assert Image.open(root / rg["face_anchor_refs"][0]["path"]).size == (1024, 1024)


def test_front_crop_uses_subject_bbox_for_padded_split_front(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    image_dir = root / "出图" / "共享" / "图片"
    front = image_dir / "CHAR_TEST_常态.png"
    front.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 1200), (18, 22, 26))
    # Simulate a single column split from a turnaround sheet: neutral portrait
    # background, black padding, and a small dark subject centered low in frame.
    img.paste(Image.new("RGB", (180, 1200), (175, 176, 178)), (310, 0))
    img.paste(Image.new("RGB", (70, 120), (45, 47, 49)), (365, 270))   # head
    img.paste(Image.new("RGB", (110, 610), (42, 44, 46)), (345, 390))  # body
    img.save(front)

    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_TEST",
                        "forms": [
                            {
                                "form": "常态",
                                "asset_key": "CHAR_TEST_常态",
                                "reference_group": {
                                    "front": {"path": "出图/共享/图片/CHAR_TEST_常态.png", "status": "ready"},
                                    "face_anchor_refs": [
                                        {
                                            "label": "基础脸锚",
                                            "path": "出图/共享/图片/CHAR_TEST_常态_脸部特写.png",
                                            "status": "planned",
                                        }
                                    ],
                                },
                                "reference_atlas": {"face_anchor_refs": []},
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = derive_makeup_pack.derive_project(
        root,
        write=True,
        force=True,
        asset_keys={"CHAR_TEST_常态"},
        face_anchor_only=True,
    )

    assert [item["field"] for item in summary["derived"]] == ["face_anchor_refs"]
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    face_item = data["characters"][0]["forms"][0]["reference_group"]["face_anchor_refs"][0]
    assert face_item["derivation"]["method"] == "front_crop"
    crop_box = face_item["derivation"]["crop_box"]
    assert crop_box != [304, 132, 456, 372]
    assert 245 <= crop_box[1] <= 285
    assert crop_box[3] <= 450
    out = root / face_item["path"]
    assert out.exists()
    assert Image.open(out).size == (1024, 1024)
    assert face_item["sha256"] == derive_makeup_pack._sha256(out)
    assert face_item["dimensions"] == {"width": 1024, "height": 1024}


def test_front_crop_uses_full_width_when_bright_background_touches_edge(tmp_path: Path) -> None:
    front = tmp_path / "front.png"
    img = Image.new("RGB", (800, 1200), (186, 186, 186))
    # A normal studio portrait: no black padding, light gray background, dark
    # subject in the center. The brightest column segment touches the right
    # edge, so it must not be treated as the useful portrait column.
    img.paste(Image.new("RGB", (120, 130), (42, 34, 30)), (340, 150))   # hair/head
    img.paste(Image.new("RGB", (220, 720), (70, 74, 78)), (290, 280))  # robe/body
    img.save(front)

    im = Image.open(front).convert("RGB")
    assert derive_makeup_pack._content_column_bounds(im) == (0, 799)
    crop_box = derive_makeup_pack._front_crop_box(im, "face_anchor_refs")

    assert 290 <= crop_box[0] <= 330
    assert 470 <= crop_box[2] <= 510
    assert 130 <= crop_box[1] <= 170
    assert crop_box[3] <= 380


def test_face_crop_centres_off_axis_head_on_gradient_turnaround_split(tmp_path: Path) -> None:
    front = tmp_path / "front.png"
    width, height = 529, 941
    img = Image.new("RGB", (width, height), (18, 22, 26))
    # Portrait column has a vertical gray gradient.  The person is intentionally
    # right of canvas centre and a narrow neighbour sliver touches the edge.
    for y in range(height):
        shade = 152 + round(40 * y / (height - 1))
        for x in range(98, 432):
            img.putpixel((x, y), (shade, shade, shade))
    img.paste(Image.new("RGB", (82, 135), (35, 31, 29)), (268, 65))   # head/hair
    img.paste(Image.new("RGB", (190, 610), (55, 45, 38)), (215, 200))  # body
    img.paste(Image.new("RGB", (8, 260), (48, 42, 38)), (424, 300))   # neighbour sliver
    img.save(front)

    im = Image.open(front).convert("RGB")
    crop_box = derive_makeup_pack._front_crop_box(im, "face_anchor_refs")
    crop_center = (crop_box[0] + crop_box[2]) / 2

    assert 285 <= crop_center <= 330
    assert crop_box[1] <= 70
    # Tight identity anchors should still retain the complete synthetic head,
    # without the broad shoulder area that previously diluted face-area QC.
    assert crop_box[3] >= 195


def test_landscape_reference_board_prefers_right_face_inset(tmp_path: Path) -> None:
    front = tmp_path / "animal-board.png"
    width, height = 1600, 900
    img = Image.new("RGB", (width, height), (184, 184, 184))
    # Full-body animal occupies the centre-left while a large same-source head
    # inset occupies the right. The face crop must choose the inset.
    img.paste(Image.new("RGB", (520, 620), (70, 55, 40)), (260, 160))
    img.paste(Image.new("RGB", (430, 560), (62, 48, 35)), (1120, 170))
    img.save(front)

    im = Image.open(front).convert("RGB")
    crop_box = derive_makeup_pack._front_crop_box(im, "face_anchor_refs")

    assert crop_box[0] >= 900
    assert crop_box[1] <= 170
    assert crop_box[2] >= 1500
    assert crop_box[3] >= 730
    expression_box = derive_makeup_pack._base_expression_crop_box(im)
    assert expression_box[0] >= 850
    assert expression_box[2] == width
    half = tmp_path / "half.png"
    half_box = derive_makeup_pack._save_front_crop(front, half, "half_body", (width, height))
    assert half_box[2] <= crop_box[0]
    assert Image.open(half).size == (1024, 1024)


def test_front_from_turnaround_updates_matching_reference_slot_metadata(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    image_dir = root / "出图" / "共享" / "图片"
    front = image_dir / "CHAR_TEST_常态.png"
    turn = image_dir / "CHAR_TEST_常态_三视图.png"
    _png(front, (200, 30, 30))
    turn.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 1200), (0, 0, 0))
    for i, color in enumerate(((10, 10, 10), (80, 10, 10), (10, 80, 10), (10, 10, 80))):
        block = Image.new("RGB", (200, 1200), color)
        img.paste(block, (i * 200, 0))
    img.save(turn)

    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_TEST",
                        "forms": [
                            {
                                "form": "常态",
                                "asset_key": "CHAR_TEST_常态",
                                "reference_group": {
                                    "front": {"path": "出图/共享/图片/CHAR_TEST_常态.png", "status": "ready"},
                                    "turnaround": {"path": "出图/共享/图片/CHAR_TEST_常态_三视图.png", "status": "ready"},
                                },
                                "reference_slots": [
                                    {
                                        "slot": "primary_reference",
                                        "path": "出图/共享/图片/CHAR_TEST_常态.png",
                                        "status": "ready",
                                        "sha256": "stale",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    derive_makeup_pack.derive_project(root, write=True, force=True, front_from_turnaround=True)

    data = json.loads(registry_path.read_text(encoding="utf-8"))
    form = data["characters"][0]["forms"][0]
    slot = form["reference_slots"][0]
    assert slot["sha256"] == derive_makeup_pack._sha256(root / slot["path"])
    assert slot["dimensions"] == {"width": 800, "height": 1200}


def test_front_from_turnaround_does_not_inherit_landscape_front_canvas(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "横幅正面测试"
    image_dir = root / "出图" / "共享" / "图片"
    front = image_dir / "CHAR_TEST_常态.png"
    turn = image_dir / "CHAR_TEST_常态_三视图.png"
    _png(front, (180, 180, 180), size=(1672, 941))
    turn.parent.mkdir(parents=True, exist_ok=True)
    board = Image.new("RGB", (1670, 940), (180, 180, 180))
    for index in range(5):
        board.paste(Image.new("RGB", (250, 860), (40 + index * 10, 45, 50)), (index * 334 + 42, 40))
    board.save(turn)
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({
        "characters": [{"id": "CHAR_TEST", "library_tier": "core_full", "forms": [{
            "form": "常态", "asset_key": "CHAR_TEST_常态",
            "reference_group": {
                "front": {"path": "出图/共享/图片/CHAR_TEST_常态.png", "status": "ready"},
                "turnaround": {
                    "path": "出图/共享/图片/CHAR_TEST_常态_三视图.png", "status": "ready",
                    "layout": "five_angle_v1", "column_count": 5,
                },
            },
            "reference_atlas": {"build_tier": "core_full", "base_views": {}},
        }]}],
    }, ensure_ascii=False), encoding="utf-8")

    derive_makeup_pack.derive_project(
        root, write=True, force=True, front_from_turnaround=True,
        asset_keys={"CHAR_TEST_常态"}, views={"front"},
    )

    assert Image.open(front).size == (529, 940)


def test_derive_project_splits_five_angle_turnaround_with_rear_three_quarter(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "五角测试"
    image_dir = root / "出图" / "共享" / "图片"
    image_dir.mkdir(parents=True)
    turn = image_dir / "CHAR_CORE_常态_turnaround.png"
    board = Image.new("RGB", (1000, 1000), (0, 0, 0))
    colors = ((20, 20, 20), (80, 10, 10), (10, 80, 10), (80, 80, 10), (10, 10, 80))
    for index, color in enumerate(colors):
        board.paste(Image.new("RGB", (200, 1000), color), (index * 200, 0))
    board.save(turn)
    reg_path = root / "出图" / "共享" / "identity_registry.json"
    reg_path.write_text(json.dumps({
        "characters": [{
            "id": "CHAR_CORE",
            "library_tier": "core_full",
            "forms": [{
                "form": "常态",
                "asset_key": "CHAR_CORE_常态",
                "reference_group": {
                    "turnaround": {
                        "path": "出图/共享/图片/CHAR_CORE_常态_turnaround.png",
                        "status": "ready",
                        "layout": "five_angle_v1",
                        "column_count": 5,
                        "view_order": [
                            "front", "three_quarter", "side", "rear_three_quarter", "back",
                        ],
                    },
                    "three_quarter": {"path": "出图/共享/图片/CHAR_CORE_常态_45度.png", "status": "planned"},
                    "side": {"path": "出图/共享/图片/CHAR_CORE_常态_侧.png", "status": "planned"},
                    "rear_three_quarter": {"path": "出图/共享/图片/CHAR_CORE_常态_后45度.png", "status": "planned"},
                    "back": {"path": "出图/共享/图片/CHAR_CORE_常态_背.png", "status": "planned"},
                },
                "reference_atlas": {"build_tier": "core_full", "base_views": {}},
            }],
        }]
    }, ensure_ascii=False), encoding="utf-8")

    summary = derive_makeup_pack.derive_project(
        root, write=True, force=True, views={"rear_three_quarter"}
    )

    assert [row["field"] for row in summary["derived"]] == ["rear_three_quarter"]
    assert not (image_dir / "CHAR_CORE_常态_45度.png").exists()
    summary = derive_makeup_pack.derive_project(
        root, write=True, force=True, views={"three_quarter", "side", "back"}
    )

    assert {row["field"] for row in summary["derived"]} == {"three_quarter", "side", "back"}
    form = json.loads(reg_path.read_text(encoding="utf-8"))["characters"][0]["forms"][0]
    rear = form["reference_group"]["rear_three_quarter"]
    back = form["reference_group"]["back"]
    assert rear["derivation"]["crop_box"] == [600, 0, 800, 1000]
    assert rear["derivation"]["crop_box"][0] < back["derivation"]["crop_box"][0]
    assert rear["status"] == back["status"] == "ready"
    assert Image.open(root / rear["path"]).size == (562, 1000)


def test_turnaround_split_plan_does_not_treat_new_rear_slot_as_five_column_evidence() -> None:
    form = {
        "reference_group": {
            "turnaround": {
                "path": "出图/共享/图片/legacy_turnaround.png",
                "status": "ready",
                "layout": "unknown_existing",
            },
            # Prompt-pack migration adds this planned slot to core characters,
            # including registries whose existing board still has four columns.
            "rear_three_quarter": {
                "path": "出图/共享/图片/legacy_后45度.png",
                "status": "planned",
            },
        },
        "reference_atlas": {
            "base_views": {
                "rear_three_quarter": {
                    "path": "出图/共享/图片/legacy_后45度.png",
                    "status": "planned",
                },
            },
        },
    }

    split_plan, column_count = derive_makeup_pack._turnaround_split_plan(form)

    assert column_count == 4
    assert "rear_three_quarter" not in split_plan
    assert split_plan["back"][0] == 3


def test_derive_project_can_filter_by_asset_key(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    image_dir = root / "出图" / "共享" / "图片"
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)

    forms = []
    for asset_key in ("CHAR_KEEP", "CHAR_SKIP"):
        front = image_dir / f"{asset_key}.png"
        turn = image_dir / f"{asset_key}_三视图.png"
        _png(front, (120, 60, 30))
        turn.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (800, 1200), (30, 60, 120)).save(turn)
        forms.append({
            "form": asset_key,
            "asset_key": asset_key,
            "reference_group": {
                "front": {"path": f"出图/共享/图片/{asset_key}.png", "status": "ready"},
                "turnaround": {"path": f"出图/共享/图片/{asset_key}_三视图.png", "status": "ready"},
                "three_quarter": {"path": f"出图/共享/图片/{asset_key}_45度.png", "status": "planned"},
                "side": {"path": f"出图/共享/图片/{asset_key}_侧.png", "status": "planned"},
                "back": {"path": f"出图/共享/图片/{asset_key}_背.png", "status": "planned"},
                "half_body": {"path": f"出图/共享/图片/{asset_key}_半身.png", "status": "planned"},
                "face_anchor_refs": [{"path": f"出图/共享/图片/{asset_key}_脸部特写.png", "status": "planned"}],
            },
        })

    registry_path.write_text(json.dumps({"characters": [{"id": "CHAR_01", "forms": forms}]}, ensure_ascii=False),
                             encoding="utf-8")

    summary = derive_makeup_pack.derive_project(root, write=True, force=True, asset_keys={"CHAR_KEEP"})

    assert {item["form"] for item in summary["derived"]} == {"CHAR_01/CHAR_KEEP"}
    assert (image_dir / "CHAR_KEEP_45度.png").exists()
    assert not (image_dir / "CHAR_SKIP_45度.png").exists()


def test_derive_project_face_anchor_only_does_not_overwrite_views(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    image_dir = root / "出图" / "共享" / "图片"
    front = image_dir / "CHAR_TEST_常态.png"
    turn = image_dir / "CHAR_TEST_常态_三视图.png"
    three_quarter = image_dir / "CHAR_TEST_常态_45度.png"
    half_body = image_dir / "CHAR_TEST_常态_半身.png"
    face_anchor = image_dir / "CHAR_TEST_常态_脸部特写.png"
    _png(front, (200, 30, 30))
    _png(turn, (10, 10, 10), size=(800, 1200))
    _png(three_quarter, (20, 80, 20))
    _png(half_body, (80, 20, 20))
    _png(face_anchor, (0, 0, 0))
    original_three_quarter = three_quarter.read_bytes()
    original_half_body = half_body.read_bytes()

    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_TEST",
                        "forms": [
                            {
                                "form": "常态",
                                "asset_key": "CHAR_TEST_常态",
                                "reference_group": {
                                    "front": {"path": "出图/共享/图片/CHAR_TEST_常态.png", "status": "ready"},
                                    "turnaround": {"path": "出图/共享/图片/CHAR_TEST_常态_三视图.png", "status": "ready"},
                                    "three_quarter": {
                                        "path": "出图/共享/图片/CHAR_TEST_常态_45度.png",
                                        "status": "ready",
                                    },
                                    "half_body": {
                                        "path": "出图/共享/图片/CHAR_TEST_常态_半身.png",
                                        "status": "ready",
                                    },
                                    "face_anchor_refs": [
                                        {
                                            "label": "基础脸锚",
                                            "path": "出图/共享/图片/CHAR_TEST_常态_脸部特写.png",
                                            "status": "ready",
                                            "derivation": {
                                                "method": "front_crop",
                                                "source_path": "出图/共享/图片/CHAR_TEST_常态.png",
                                                "source_sha256": "stale",
                                            },
                                        }
                                    ],
                                },
                                "reference_atlas": {"face_anchor_refs": []},
                            }
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = derive_makeup_pack.derive_project(
        root,
        write=True,
        force=True,
        asset_keys={"CHAR_TEST_常态"},
        face_anchor_only=True,
    )

    assert [item["field"] for item in summary["derived"]] == ["face_anchor_refs"]
    assert three_quarter.read_bytes() == original_three_quarter
    assert half_body.read_bytes() == original_half_body
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    form = data["characters"][0]["forms"][0]
    item = form["reference_group"]["face_anchor_refs"][0]
    assert item["derivation"]["source_sha256"] == derive_makeup_pack._sha256(front)
    assert form["reference_atlas"]["face_anchor_refs"][0]["derivation"]["source_sha256"] == derive_makeup_pack._sha256(front)


def test_derive_project_can_make_independent_base_expression_from_front(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    image_dir = root / "出图" / "共享" / "图片"
    front = image_dir / "CHAR_TIGER_常态.png"
    front.parent.mkdir(parents=True, exist_ok=True)
    plate = Image.new("RGB", (800, 1200), (210, 210, 210))
    plate.paste(Image.new("RGB", (280, 760), (120, 70, 30)), (260, 80))
    plate.paste(Image.new("RGB", (160, 180), (245, 230, 210)), (320, 100))
    plate.save(front)
    expression_rel = "出图/共享/图片/CHAR_TIGER_常态_表情_克制.png"
    face_rel = "出图/共享/图片/CHAR_TIGER_常态_脸部特写.png"

    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({
        "characters": [{"id": "CHAR_TIGER", "forms": [{
            "form": "常态", "asset_key": "CHAR_TIGER__常态",
            "reference_group": {
                "front": {"path": "出图/共享/图片/CHAR_TIGER_常态.png", "status": "ready"},
                "face_anchor_refs": [{"path": face_rel, "status": "planned"}],
                "expressions": [{"emotion": "克制", "path": expression_rel, "status": "planned"}],
            },
            "reference_atlas": {
                "face_anchor_refs": [{"path": face_rel, "status": "planned"}],
                "expression_refs": [{"emotion": "克制", "path": expression_rel, "status": "planned"}],
            },
        }]}],
    }, ensure_ascii=False), encoding="utf-8")

    # Build the tight anchor first, then the distinct head-and-shoulders neutral expression.
    derive_makeup_pack.derive_project(
        root, write=True, asset_keys={"CHAR_TIGER__常态"}, views={"face_anchor_refs"}
    )
    summary = derive_makeup_pack.derive_project(
        root, write=True, asset_keys={"CHAR_TIGER__常态"}, views={"expression"}
    )

    assert [item["method"] for item in summary["derived"]] == ["front_expression_crop"]
    expression = root / expression_rel
    face_anchor = root / face_rel
    assert expression.exists() and Image.open(expression).size == (1024, 1024)
    assert derive_makeup_pack._sha256(expression) != derive_makeup_pack._sha256(face_anchor)
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    form = data["characters"][0]["forms"][0]
    rg_item = form["reference_group"]["expressions"][0]
    atlas_item = form["reference_atlas"]["expression_refs"][0]
    assert rg_item["status"] == atlas_item["status"] == "ready"
    assert rg_item["derivation"]["source_path"].endswith("CHAR_TIGER_常态.png")
    assert rg_item["derivation"]["crop_box"] != form["reference_group"]["face_anchor_refs"][0]["derivation"]["crop_box"]


def test_force_face_anchor_does_not_overwrite_expression_sheet_alias(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    image_dir = root / "出图" / "共享" / "图片"
    front = image_dir / "CHAR_BOY_常态.png"
    expression = image_dir / "CHAR_BOY_常态_表情_六联表.png"
    _png(front, (110, 90, 70), size=(941, 1672))
    _png(expression, (30, 120, 210), size=(1672, 941))
    original_expression = expression.read_bytes()
    shared_rel = "出图/共享/图片/CHAR_BOY_常态_表情_六联表.png"

    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps({
        "characters": [{"id": "CHAR_BOY", "forms": [{
            "form": "常态", "asset_key": "CHAR_BOY__常态",
            "reference_group": {
                "front": {"path": "出图/共享/图片/CHAR_BOY_常态.png", "status": "ready"},
                "face_anchor_refs": [{"path": shared_rel, "status": "ready"}],
                "expressions": [{"emotion": "六联表", "path": shared_rel, "status": "ready"}],
            },
            "reference_atlas": {
                "face_anchor_refs": [{"path": shared_rel, "status": "ready"}],
                "expression_refs": [{"emotion": "六联表", "path": shared_rel, "status": "ready"}],
            },
        }]}],
    }, ensure_ascii=False), encoding="utf-8")

    summary = derive_makeup_pack.derive_project(
        root,
        write=True,
        force=True,
        asset_keys={"CHAR_BOY__常态"},
        face_anchor_only=True,
        views={"face_anchor_refs"},
    )

    assert expression.read_bytes() == original_expression
    assert summary["derived"][0]["path"].endswith("CHAR_BOY_常态_脸部特写.png")
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    form = data["characters"][0]["forms"][0]
    anchor = form["reference_group"]["face_anchor_refs"]
    atlas_anchor = form["reference_atlas"]["face_anchor_refs"]
    assert [item["path"] for item in anchor] == ["出图/共享/图片/CHAR_BOY_常态_脸部特写.png"]
    assert [item["path"] for item in atlas_anchor] == ["出图/共享/图片/CHAR_BOY_常态_脸部特写.png"]
    assert form["reference_group"]["expressions"][0]["path"] == shared_rel
    assert form["reference_atlas"]["expression_refs"][0]["path"] == shared_rel
    assert Image.open(root / anchor[0]["path"]).size == (1024, 1024)


def test_derive_project_can_tighten_expression_refs_without_overwriting_source(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    image_dir = root / "出图" / "共享" / "图片"
    expression = image_dir / "CHAR_TEST_表情_克制.png"
    _png(expression, (40, 120, 200), size=(900, 1200))
    original_bytes = expression.read_bytes()

    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    rel = "出图/共享/图片/CHAR_TEST_表情_克制.png"
    registry_path.write_text(
        json.dumps(
            {
                "characters": [
                    {
                        "id": "CHAR_TEST",
                        "forms": [
                            {
                                "form": "常态",
                                "asset_key": "CHAR_TEST_常态",
                                "reference_group": {
                                    "expressions": [{"emotion": "克制", "path": rel, "status": "ready"}],
                                },
                                "reference_atlas": {
                                    "expression_refs": [{"emotion": "克制", "path": rel, "status": "ready"}],
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

    summary = derive_makeup_pack.derive_project(root, write=True, tighten_expressions=True)

    assert any(item["field"] == "expressions" for item in summary["derived"])
    assert expression.read_bytes() == original_bytes
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    form = data["characters"][0]["forms"][0]
    rg_item = form["reference_group"]["expressions"][0]
    atlas_item = form["reference_atlas"]["expression_refs"][0]
    assert rg_item["path"].endswith("_脸锚裁切.png")
    assert atlas_item["path"] == rg_item["path"]
    assert rg_item["derivation"]["method"] == "expression_face_crop"
    assert rg_item["derivation"]["source_path"] == rel
    out = root / rg_item["path"]
    assert out.exists()
    assert Image.open(out).size == (1024, 1024)
