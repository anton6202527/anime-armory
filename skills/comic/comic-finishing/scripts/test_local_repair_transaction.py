from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw


MODULE = Path(__file__).with_name("local_repair_transaction.py")
SPEC = importlib.util.spec_from_file_location("comic_local_repair", MODULE)
assert SPEC and SPEC.loader
repair = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repair)


def make_project(root: Path) -> tuple[Path, Path, Path]:
    master = root / "出图" / "第1话" / "masters" / "P001.png"
    panel = root / "出图" / "第1话" / "panels" / "P001.png"
    mask = root / "mask.png"
    master.parent.mkdir(parents=True)
    panel.parent.mkdir(parents=True)
    Image.new("RGB", (40, 40), (20, 30, 40)).save(master)
    Image.new("RGB", (40, 40), (20, 30, 40)).save(panel)
    m = Image.new("L", (40, 40), 0)
    ImageDraw.Draw(m).rectangle((10, 10, 19, 19), fill=255)
    m.save(mask)
    jobs = {
        "jobs": [{
            "panel_id": "P001", "master_path": "出图/第1话/masters/P001.png",
            "result_path": "出图/第1话/panels/P001.png", "size": {"width": 40, "height": 40},
            "execution_input_sha256": "a" * 64, "references": [],
        }]
    }
    jobs_path = root / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs_path.parent.mkdir(parents=True)
    jobs_path.write_text(json.dumps(jobs), encoding="utf-8")
    return master, panel, mask


def test_prepare_binds_source_mask_bbox_and_prompt(tmp_path: Path) -> None:
    master, _panel, mask = make_project(tmp_path)
    receipt = repair.prepare(tmp_path, "第1话", "P001", mask, {"x": 10, "y": 10, "w": 10, "h": 10}, "修正右手")
    tx = repair.image_runner.load_json(receipt)
    assert tx["status"] == "prepared"
    assert tx["source_master_sha256"] == repair.image_runner.file_sha256(master)
    assert tx["mask_sha256"] == repair.image_runner.file_sha256(mask)
    assert tx["bbox"] == {"x": 10, "y": 10, "w": 10, "h": 10}


def test_commit_rejects_changes_outside_mask_without_overwrite(tmp_path: Path) -> None:
    master, panel, mask = make_project(tmp_path)
    before_master = repair.image_runner.file_sha256(master)
    before_panel = repair.image_runner.file_sha256(panel)
    receipt = repair.prepare(tmp_path, "第1话", "P001", mask, {"x": 10, "y": 10, "w": 10, "h": 10}, "修正右手")
    candidate = tmp_path / "bad.png"
    image = Image.open(master).copy()
    image.putpixel((0, 0), (255, 0, 0))
    image.save(candidate)
    with pytest.raises(ValueError, match="mask 外"):
        repair.commit(tmp_path, receipt, candidate)
    assert repair.image_runner.file_sha256(master) == before_master
    assert repair.image_runner.file_sha256(panel) == before_panel


def test_prepare_rejects_mask_pixels_outside_declared_bbox(tmp_path: Path) -> None:
    _master, _panel, mask = make_project(tmp_path)
    with pytest.raises(ValueError, match="bbox"):
        repair.prepare(
            tmp_path,
            "第1话",
            "P001",
            mask,
            {"x": 12, "y": 12, "w": 3, "h": 3},
            "修正右手",
        )


def test_relative_cli_paths_use_project_root_and_commit_requires_fresh_b14(tmp_path: Path, monkeypatch) -> None:
    master, panel, mask = make_project(tmp_path)
    monkeypatch.chdir(tmp_path.parent)
    monkeypatch.setattr(repair.image_runner, "likely_blank_bubble_regions", lambda _path: [])
    monkeypatch.setattr(repair.image_runner, "likely_large_edge_blank_bands", lambda _path: [])
    receipt = repair.prepare(
        tmp_path,
        "第1话",
        "P001",
        Path("mask.png"),
        {"x": 10, "y": 10, "w": 10, "h": 10},
        "修正右手，不改变其他像素",
    )
    candidate = tmp_path / "good.png"
    image = Image.open(master).copy()
    image.putpixel((12, 12), (190, 80, 60))
    image.save(candidate)

    repair.commit(tmp_path, receipt.relative_to(tmp_path), Path("good.png"))

    data = repair.image_runner.load_json(tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json")
    job = data["jobs"][0]
    tx = repair.image_runner.load_json(receipt)
    assert tx["status"] == "committed_awaiting_current_pixel_review"
    assert repair.image_runner.file_sha256(master) == job["resolution_provenance"]["native_sha256"]
    assert repair.image_runner.file_sha256(panel) == tx["current_pixel_sha256"]
    assert [item["role"] for item in job["resolution_provenance"]["derivative_chain"]] == [
        "immutable_provider_raw",
        "active_master",
        "layout_panel",
    ]
    assert job["status"] in {"awaiting_review", "qc_warn"}
    assert repair.image_runner.panel_acceptance_status(tmp_path, job)["accepted"] is False
