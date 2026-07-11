#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import base64
import json
import subprocess
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("identity.py")
    spec = importlib.util.spec_from_file_location("comic_identity_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


identity = load_module()


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_report_does_not_force_rerun_when_current_refs_expand_after_acceptance(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    chapter = "第1话"
    shared = root / "出图" / "共享" / "图片"
    jobs_dir = root / "出图" / chapter / "prompt"
    shared.mkdir(parents=True)
    jobs_dir.mkdir(parents=True)
    (root / "生产数据").mkdir(parents=True)
    (shared / "CHAR_A__front.png").write_bytes(b"front")
    (shared / "CHAR_A__side.png").write_bytes(b"side")
    (jobs_dir / "panel_jobs.json").write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "panel_id": "P001",
                        "status": "ready",
                        "reference_input_count": 1,
                        "reference_manifest": "生产数据/codex_reference_bundles/第1话/P001.json",
                        "references": [
                            {"id": "CHAR_A", "path": "出图/共享/图片/CHAR_A__front.png"},
                            {"id": "CHAR_A", "path": "出图/共享/图片/CHAR_A__side.png"},
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rc = identity.report(type("Args", (), {"project_root": str(root), "chapter": chapter, "write": False})())
    assert rc == 0
    report = json.loads((root / "生产数据" / f"comic_identity_report_{chapter}.json").read_text(encoding="utf-8"))
    assert report["rerun_targets"] == []
    panel = report["panels"][0]
    assert panel["reference_delta_after_rebind"] == 1


def _write_ready_job_with_manifest(root: Path, chapter: str, *, recorded_sha: str) -> None:
    shared = root / "出图" / "共享" / "图片"
    jobs_dir = root / "出图" / chapter / "prompt"
    manifest_dir = root / "生产数据" / "codex_reference_bundles" / chapter
    shared.mkdir(parents=True, exist_ok=True)
    jobs_dir.mkdir(parents=True, exist_ok=True)
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (shared / "CHAR_A__front.png").write_bytes(b"front-v2")
    (manifest_dir / "P001.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "comic_codex_reference_bundle",
                "chapter": chapter,
                "panel_id": "P001",
                "references": [
                    {"id": "CHAR_A", "path": "出图/共享/图片/CHAR_A__front.png", "sha256": recorded_sha}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (jobs_dir / "panel_jobs.json").write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "panel_id": "P001",
                        "status": "ready",
                        "reference_input_count": 1,
                        "reference_manifest": f"生产数据/codex_reference_bundles/{chapter}/P001.json",
                        "references": [
                            {"id": "CHAR_A", "path": "出图/共享/图片/CHAR_A__front.png"},
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_report_flags_rerun_when_generated_reference_content_changed(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    chapter = "第1话"
    stale_sha = identity.hashlib.sha256(b"front-v1").hexdigest()
    _write_ready_job_with_manifest(root, chapter, recorded_sha=stale_sha)

    rc = identity.report(type("Args", (), {"project_root": str(root), "chapter": chapter, "write": False})())
    assert rc == 0
    report = json.loads((root / "生产数据" / f"comic_identity_report_{chapter}.json").read_text(encoding="utf-8"))
    assert report["rerun_targets"] == ["P001"]
    panel = report["panels"][0]
    assert panel["stale_generated_refs"][0]["reason"] == "reference_content_changed"
    assert "changed after generation" in panel["rerun_reason"]


def test_report_keeps_ready_when_generated_reference_sha_matches(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    chapter = "第1话"
    current_sha = identity.hashlib.sha256(b"front-v2").hexdigest()
    _write_ready_job_with_manifest(root, chapter, recorded_sha=current_sha)

    rc = identity.report(type("Args", (), {"project_root": str(root), "chapter": chapter, "write": False})())
    assert rc == 0
    report = json.loads((root / "生产数据" / f"comic_identity_report_{chapter}.json").read_text(encoding="utf-8"))
    assert report["rerun_targets"] == []
    assert report["panels"][0]["stale_generated_refs"] == []


def test_report_flags_outfit_gaps(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    chapter = "第1话"
    jobs_dir = root / "出图" / chapter / "prompt"
    jobs_dir.mkdir(parents=True)
    (root / "生产数据").mkdir(parents=True)
    (jobs_dir / "panel_jobs.json").write_text(
        json.dumps(
            {
                "jobs": [
                    {
                        "panel_id": "P001",
                        "status": "planned",
                        "references": [],
                        "outfit_binding": {"ref_id": "", "outfit_id": "OUTFIT_X", "registered": False},
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    rc = identity.report(type("Args", (), {"project_root": str(root), "chapter": chapter, "write": False})())
    assert rc == 0
    report = json.loads((root / "生产数据" / f"comic_identity_report_{chapter}.json").read_text(encoding="utf-8"))
    assert report["summary"]["outfit_gap_count"] == 1
    assert "OUTFIT_X" in report["outfit_gaps"]["P001"]


def test_views_registers_existing_view_without_anchor(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    shared = root / "出图" / "共享" / "图片"
    shared.mkdir(parents=True)
    (shared / "CHAR_A__front.png").write_bytes(PNG_1X1)
    (root / "出图" / "共享").mkdir(parents=True, exist_ok=True)
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({"assets": {"CHAR_A": {"id": "CHAR_A", "type": "character", "reference_images": [], "views": {}}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(identity.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else None)
    monkeypatch.setattr(identity, "codex_version", lambda: "codex test")

    rc = identity.generate_views(
        type(
            "Args",
            (),
            {
                "project_root": str(root),
                "chapter": "第1话",
                "characters": "CHAR_A",
                "views": "front",
                "backend": "codex",
                "overwrite": False,
                "max_attempts": 1,
                "timeout_sec": 1,
                "poll_sec": 1,
                "model_version": "5.0",
                "resolution_type": "2k",
                "ratio": "3:4",
                "face_ratio": "1:1",
                "prefer_front_anchor": True,
                "allow_text_anchor": False,
            },
        )()
    )

    assert rc == 0
    registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    assert registry["assets"]["CHAR_A"]["views"]["front"].endswith("CHAR_A__front.png")


def test_views_can_generate_front_from_text_anchor(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "设定库").mkdir(parents=True)
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "assets": {
                    "CHAR_A": {
                        "id": "CHAR_A",
                        "type": "character",
                        "display_name": "甲",
                        "character_dna": "方脸，短发，灰衣。",
                        "reference_images": [],
                        "views": {},
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, list[Path]]] = []

    def fake_run_codex_image(prompt: str, repo: Path, timeout_sec: int, image_paths: list[Path]):
        calls.append((prompt, image_paths))
        return subprocess.CompletedProcess(["codex"], 0, stdout="{}", stderr="")

    def fake_decode_image_event(stdout: str, out_path: Path) -> bool:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(PNG_1X1)
        return True

    monkeypatch.setattr(identity.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else None)
    monkeypatch.setattr(identity, "codex_version", lambda: "codex test")
    monkeypatch.setattr(identity, "run_codex_image", fake_run_codex_image)
    monkeypatch.setattr(identity, "decode_image_event", fake_decode_image_event)

    rc = identity.generate_views(
        type(
            "Args",
            (),
            {
                "project_root": str(root),
                "chapter": "第1话",
                "characters": "CHAR_A",
                "views": "front",
                "backend": "codex",
                "overwrite": False,
                "max_attempts": 1,
                "timeout_sec": 1,
                "poll_sec": 1,
                "model_version": "5.0",
                "resolution_type": "2k",
                "ratio": "3:4",
                "face_ratio": "1:1",
                "prefer_front_anchor": True,
                "allow_text_anchor": True,
            },
        )()
    )

    assert rc == 0
    assert calls
    prompt, image_paths = calls[0]
    assert image_paths == []
    assert "本次没有已采纳角色图片作为附件" in prompt
    registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    source = registry["assets"]["CHAR_A"]["reference_images"][0]["source"]
    assert source["kind"] == "generated_character_view_text_seed"
    assert source["anchor_kind"] == "text_prompt_seed"


def test_anchors_generate_non_character_text_anchor(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "assets": {
                    "PROP_A": {
                        "id": "PROP_A",
                        "type": "prop",
                        "display_name": "旧木牌",
                        "prop_contract": "木牌完整，边缘磨损，不生成可读文字。",
                        "reference_images": [],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, list[Path]]] = []

    def fake_run_codex_image(prompt: str, repo: Path, timeout_sec: int, image_paths: list[Path]):
        calls.append((prompt, image_paths))
        return subprocess.CompletedProcess(["codex"], 0, stdout="{}", stderr="")

    def fake_decode_image_event(stdout: str, out_path: Path) -> bool:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(PNG_1X1)
        return True

    monkeypatch.setattr(identity.shutil, "which", lambda name: "/usr/bin/codex" if name == "codex" else None)
    monkeypatch.setattr(identity, "codex_version", lambda: "codex test")
    monkeypatch.setattr(identity, "run_codex_image", fake_run_codex_image)
    monkeypatch.setattr(identity, "decode_image_event", fake_decode_image_event)

    rc = identity.generate_anchors(
        type(
            "Args",
            (),
            {
                "project_root": str(root),
                "chapter": "第1话",
                "refs": "PROP_A",
                "overwrite": False,
                "max_attempts": 1,
                "timeout_sec": 1,
            },
        )()
    )

    assert rc == 0
    assert calls
    prompt, image_paths = calls[0]
    assert image_paths == []
    assert "参考 ID：PROP_A" in prompt
    registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    asset = registry["assets"]["PROP_A"]
    assert asset["anchor_path"].endswith("PROP_A__anchor.png")
    assert asset["reference_images"][0]["source"]["kind"] == "generated_text_anchor"
