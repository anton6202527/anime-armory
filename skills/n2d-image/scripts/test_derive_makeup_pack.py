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
    assert form["reference_atlas"]["base_views"]["back"]["derivation"]["source_sha256"]
    for rel in (
        rg["three_quarter"]["path"],
        rg["side"]["path"],
        rg["back"]["path"],
        rg["half_body"]["path"],
        rg["face_anchor_refs"][0]["path"],
    ):
        out = root / rel
        assert out.exists()
        assert Image.open(out).size == (800, 1200)
