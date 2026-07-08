from __future__ import annotations

import json
from pathlib import Path

import production_locks as locks


def _write_release_inputs(root: Path, ep: str = "第1集") -> None:
    (root / "_设置.md").write_text("- 制作模式: 配音先行\n", encoding="utf-8")
    (root / "设定库").mkdir(parents=True)
    (root / "设定库" / "source_comprehension.json").write_text('{"status":"confirmed"}', encoding="utf-8")
    (root / "脚本" / ep).mkdir(parents=True)
    (root / "脚本" / ep / "voiceover.txt").write_text("台词", encoding="utf-8")
    (root / "脚本" / ep / "bgm.txt").write_text("BGM", encoding="utf-8")
    (root / "脚本" / ep / "storyboard.json").write_text('{"clips":[]}', encoding="utf-8")
    (root / "脚本" / ep / "镜头时长.json").write_text("{}", encoding="utf-8")
    (root / "合成" / ep / "配音").mkdir(parents=True)
    (root / "合成" / ep / "配音" / "时长清单.json").write_text("{}", encoding="utf-8")
    (root / "合成" / ep).mkdir(parents=True, exist_ok=True)
    (root / "合成" / ep / f"成片_{ep}_zh.mp4").write_bytes(b"master")
    (root / "合成" / ep / "_work").mkdir(parents=True, exist_ok=True)
    (root / "合成" / ep / "_work" / "timeline.json").write_text('{"kind":"n2d_rough_cut_timeline"}', encoding="utf-8")
    (root / "合成" / ep / "rough_cut_preview.html").write_text("<html>rough</html>", encoding="utf-8")
    (root / "出视频" / ep / "视频").mkdir(parents=True, exist_ok=True)
    (root / "出视频" / ep / "视频" / "Clip_01.mp4").write_bytes(b"video")
    (root / "出视频" / ep / "prompt").mkdir(parents=True, exist_ok=True)
    (root / "出视频" / ep / "prompt" / "video_model_routes.json").write_text('{"kind":"n2d_video_model_routes"}', encoding="utf-8")
    (root / "生产数据").mkdir(parents=True, exist_ok=True)
    (root / "生产数据" / "image_qc" / ep).mkdir(parents=True, exist_ok=True)
    (root / "生产数据" / "image_qc" / ep / f"image_qc_{ep}.json").write_text('{"kind":"n2d_image_qc","status":"pass"}', encoding="utf-8")
    (root / "生产数据" / f"video_qc_{ep}.json").write_text('{"kind":"n2d_video_qc","status":"pass"}', encoding="utf-8")
    (root / "生产数据" / f"final_timeline_probe_{ep}.json").write_text('{"kind":"n2d_final_timeline_probe","status":"pass"}', encoding="utf-8")
    (root / "生产数据" / f"script_supervisor_log_{ep}.jsonl").write_text('{"kind":"n2d_script_supervisor_log","clip_id":"Clip_01","accepted_take":true}\n', encoding="utf-8")


def test_confirmed_locks_pass_and_detect_stale_artifact(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)

    locks.scaffold(tmp_path, "1", confirmed=True, reviewer="qa")
    report = locks.check_ledger(tmp_path, "第1集")

    assert report["status"] == "pass"

    (tmp_path / "脚本" / "第1集" / "storyboard.json").write_text('{"clips":[{"id":"Clip_01"}]}', encoding="utf-8")
    stale = locks.check_ledger(tmp_path, "第1集")

    assert stale["status"] == "block"
    assert any(f["code"] == "lock_artifact_stale" for f in stale["findings"])


def test_stage_scoped_check_ignores_later_unconfirmed_locks(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)
    locks.scaffold(tmp_path, "第1集", confirmed=True, reviewer="qa")
    path = locks.lock_path(tmp_path, "第1集")
    data = json.loads(path.read_text(encoding="utf-8"))
    for lock in data["locks"]:
        if lock["lock_id"] == "delivery_lock":
            lock["status"] = "draft"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    review = locks.check_ledger(tmp_path, "第1集", stage="review")
    full = locks.check_ledger(tmp_path, "第1集")

    assert review["status"] == "pass"
    assert "delivery_lock" not in review["checked_lock_ids"]
    assert full["status"] == "block"


def test_review_lock_blocks_missing_rough_cut_artifact(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)
    locks.scaffold(tmp_path, "第1集", confirmed=True, reviewer="qa")
    (tmp_path / "合成" / "第1集" / "rough_cut_preview.html").unlink()

    report = locks.check_ledger(tmp_path, "第1集", stage="review")

    assert report["status"] == "block"
    assert any(f["code"] == "lock_required_artifact_missing" and f["lock_id"] == "rough_cut_lock" for f in report["findings"])


def test_compose_lock_blocks_missing_video_material_artifact(tmp_path: Path) -> None:
    _write_release_inputs(tmp_path)
    locks.scaffold(tmp_path, "第1集", confirmed=True, reviewer="qa")
    (tmp_path / "生产数据" / f"video_qc_第1集.json").unlink()

    report = locks.check_ledger(tmp_path, "第1集", stage="compose")

    assert report["status"] == "block"
    assert any(f["code"] == "lock_required_artifact_missing" and f["lock_id"] == "video_material_lock" for f in report["findings"])
