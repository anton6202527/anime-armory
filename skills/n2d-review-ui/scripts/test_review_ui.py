from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("review_ui.py")
spec = importlib.util.spec_from_file_location("n2d_review_ui", SCRIPT)
review_ui = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(review_ui)


def write_text(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_manifest_collects_visual_review_assets(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    storyboard = {
        "episode": 1,
        "title": "测试剧_第1集",
        "total_duration": 8,
        "clips": [
            {
                "id": "EP01_CLIP01",
                "label": "Clip 1",
                "duration": 4,
                "scene": "冷宫",
                "rhythm": "爽点",
                "firstframe_png": "出图/第1集/图片/Clip01.png",
                "video_out": "出视频/第1集/视频/Clip_01.mp4",
                "continuity": {"endframe_png": "出图/第1集/图片/Clip01_end.png", "transition": "match_cut", "need_endframe": True},
            },
            {
                "id": "EP01_CLIP02",
                "label": "Clip 2",
                "duration": 4,
                "scene": "冷宫",
                "rhythm": "反打",
                "firstframe_png": "出图/第1集/图片/Clip02.png",
                "video_out": "出视频/第1集/视频/Clip_02.mp4",
                "continuity": {"transition": "hard_cut", "need_endframe": False},
            },
        ],
    }
    write_text(root / "脚本" / ep / "storyboard.json", json.dumps(storyboard, ensure_ascii=False))
    for rel in (
        "出图/第1集/图片/Clip01.png",
        "出图/第1集/图片/Clip01_end.png",
        "出图/第1集/图片/Clip02.png",
        "出视频/第1集/视频/Clip_01.mp4",
    ):
        write_text(root / rel)
    registry = {
        "kind": "n2d_asset_identity_registry",
        "characters": [{
            "id": "CHAR_A",
            "name": "沈念",
            "forms": [{
                "form": "常态",
                "anchor_phrase": "凤眼薄唇",
                "reference_group": {"front": "出图/共享/图片/定妆_沈念.png"},
                "drift_forbidden": ["face_shape"],
            }],
        }],
    }
    write_text(root / "出图" / "common" / "identity_registry.json", json.dumps(registry, ensure_ascii=False))
    write_text(root / "出图" / "common" / "图片" / "定妆_沈念.png")
    score = {
        "root": str(root),
        "episode": ep,
        "total_score": 72,
        "threshold": 85,
        "status": "fail",
        "dimensions": [{
            "label": "场景一致性",
            "status": "fail",
            "score": 50,
            "evidence": ["Clip 1 接缝 dHash 距离 30 > 22"],
        }],
        "auto_return_tasks": [{"return_to_stage": "image"}],
        "data_collection_tasks": [{"skill": "n2d-score", "action": "run_checks"}],
    }
    write_text(root / "生产数据" / f"score_{ep}.json", json.dumps(score, ensure_ascii=False))

    manifest = review_ui.build_manifest(root, ep)

    assert manifest["kind"] == "n2d_review_ui"
    assert len(manifest["clips"]) == 2
    assert manifest["clips"][0]["first_frame"]["exists"] is True
    assert manifest["clips"][0]["video"]["exists"] is True
    assert manifest["clips"][1]["video"]["exists"] is False
    assert len(manifest["seams"]) == 1
    assert manifest["identity_refs"][0]["name"] == "沈念"
    assert manifest["score"]["total_score"] == 72
    assert manifest["score"]["data_collection_tasks"][0]["action"] == "run_checks"
    assert manifest["clips"][0]["qa_flags"][0]["dimension"] == "场景一致性"


def test_write_outputs_writes_html_and_json(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "测试剧"
    ep = "第1集"
    write_text(root / "脚本" / ep / "storyboard.json", json.dumps({"episode": 1, "clips": []}, ensure_ascii=False))
    manifest = review_ui.build_manifest(root, ep)

    paths = review_ui.write_outputs(root, ep, manifest)

    html_text = Path(paths["html"]).read_text(encoding="utf-8")
    json_text = Path(paths["json"]).read_text(encoding="utf-8")
    assert "人审画布" in html_text
    manifest_line = next(line for line in html_text.splitlines() if 'id="manifest"' in line)
    assert "&quot;" not in manifest_line
    assert '"kind": "n2d_review_ui"' in json_text


def test_build_manifest_falls_back_to_media_scan(tmp_path: Path) -> None:
    root = tmp_path / "制漫剧" / "旧项目"
    ep = "第2集"
    write_text(root / "脚本" / ep / "storyboard.json", json.dumps({"episode": 2}, ensure_ascii=False))
    write_text(root / "出图" / ep / "图片" / "Clip_01.png")
    write_text(root / "出图" / ep / "图片" / "Clip_01_end.png")
    write_text(root / "出视频" / ep / "视频" / "Clip_01.mp4")

    manifest = review_ui.build_manifest(root, ep)

    assert len(manifest["clips"]) == 1
    assert manifest["clips"][0]["label"] == "Clip_01"
    assert manifest["clips"][0]["first_frame"]["exists"] is True
    assert manifest["clips"][0]["end_frame"]["exists"] is True
    assert manifest["clips"][0]["video"]["exists"] is True
