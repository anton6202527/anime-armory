from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("visual_checks.py")
spec = importlib.util.spec_from_file_location("n2d_score_visual_checks", SCRIPT)
visual = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(visual)


def write_storyboard(root: Path) -> None:
    clips = [{"id": f"c{i}", "duration": 10, "continuity": {}} for i in range(1, 5)]
    path = root / "脚本" / "第1集" / "storyboard.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"episode": 1, "total_duration": 40, "clips": clips}, ensure_ascii=False), encoding="utf-8")


def write_manifest(root: Path) -> None:
    rows = [
        {"文本": "开场", "钩子": "hook"},
        {"文本": "铺垫", "钩子": ""},
        {"文本": "继续铺垫", "钩子": ""},
        {"文本": "仍然铺垫", "钩子": ""},
    ]
    path = root / "出视频" / "第1集" / "配音" / "时长清单.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def test_manifest_prefers_compose_dir(tmp_path: Path) -> None:
    old = tmp_path / "出视频" / "第1集" / "配音" / "时长清单.json"
    new = tmp_path / "合成" / "第1集" / "配音" / "时长清单.json"
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_text(json.dumps([{"文本": "旧", "钩子": ""}], ensure_ascii=False), encoding="utf-8")
    new.write_text(json.dumps([{"文本": "新", "钩子": "hook"}], ensure_ascii=False), encoding="utf-8")

    assert visual.load_manifest(str(tmp_path), "第1集")[0]["文本"] == "新"


def test_voice_candidates_prefer_compose_dir(tmp_path: Path) -> None:
    old = tmp_path / "出视频" / "第1集" / "配音" / "voice_zh.wav"
    new = tmp_path / "合成" / "第1集" / "配音" / "voice_zh.wav"
    old.parent.mkdir(parents=True)
    new.parent.mkdir(parents=True)
    old.write_bytes(b"old")
    new.write_bytes(b"new")

    candidates = visual.voice_candidates(str(tmp_path), "第1集")

    assert candidates[0] == str(new)
    assert candidates[1] == str(old)


def test_final_rhythm_density_uses_storyboard_when_final_missing(tmp_path: Path) -> None:
    write_storyboard(tmp_path)
    write_manifest(tmp_path)

    sec = visual.check_final_rhythm_density(str(tmp_path), "第1集")

    assert sec["metrics"]["shot_density_per_min"] == 6.0
    assert sec["blocks"] == 1
    assert "平均钩子间隔" in " ".join(sec["evidence"])
