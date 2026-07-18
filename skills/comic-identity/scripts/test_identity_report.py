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


def test_report_accepts_deduplicated_front_as_registered_outfit_reference(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    chapter = "第1话"
    front = root / "出图" / "共享" / "图片" / "CHAR_A__front.png"
    front.parent.mkdir(parents=True)
    front.write_bytes(PNG_1X1)
    jobs_dir = root / "出图" / chapter / "prompt"
    jobs_dir.mkdir(parents=True)
    (root / "生产数据").mkdir(parents=True)
    rel = "出图/共享/图片/CHAR_A__front.png"
    (jobs_dir / "panel_jobs.json").write_text(
        json.dumps({"jobs": [{
            "panel_id": "P001",
            "status": "planned",
            "references": [{"id": "CHAR_A", "path": rel, "view": "front"}],
            "outfit_binding": {"ref_id": "CHAR_A", "outfit_id": "OUTFIT_BASE", "registered": True},
        }]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps({"assets": {"CHAR_A": {"id": "CHAR_A", "outfits": {"OUTFIT_BASE": {
            "id": "OUTFIT_BASE", "status": "ready", "reference_images": [{"path": rel}]
        }}}}}, ensure_ascii=False),
        encoding="utf-8",
    )

    rc = identity.report(type("Args", (), {"project_root": str(root), "chapter": chapter, "write": False})())
    assert rc == 0
    report = json.loads((root / "生产数据" / f"comic_identity_report_{chapter}.json").read_text(encoding="utf-8"))
    assert report["summary"]["outfit_gap_count"] == 0
    assert report["outfit_gaps"] == {}


def test_bind_job_references_preserves_registered_outfit_reference(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    shared = root / "出图" / "共享" / "图片"
    shared.mkdir(parents=True)
    front_rel = "出图/共享/图片/CHAR_A__front.png"
    face_rel = "出图/共享/图片/CHAR_A__face.png"
    outfit_rel = "出图/共享/图片/CHAR_A__OUTFIT_TRAVEL.png"
    (root / front_rel).write_bytes(PNG_1X1)
    (root / face_rel).write_bytes(PNG_1X1)
    (root / outfit_rel).write_bytes(PNG_1X1)
    registry = {
        "assets": {
            "CHAR_A": {
                "id": "CHAR_A",
                "reference_images": [
                    {"view": "front", "path": front_rel},
                    {"view": "face", "path": face_rel},
                ],
                "outfits": {
                    "OUTFIT_TRAVEL": {
                        "id": "OUTFIT_TRAVEL",
                        "status": "ready",
                        "reference_images": [{"path": outfit_rel}],
                    }
                },
            }
        }
    }
    jobs = {
        "jobs": [
            {
                "panel_id": "P001",
                "outfit_binding": {
                    "ref_id": "CHAR_A",
                    "outfit_id": "OUTFIT_TRAVEL",
                    "registered": True,
                },
                "references": [
                    {
                        "id": "CHAR_A",
                        "role": "outfit",
                        "view": "outfit",
                        "path": face_rel,
                    }
                ],
            }
        ]
    }

    changed = identity.bind_job_references(root, jobs, registry)

    assert changed == 1
    assert jobs["jobs"][0]["references"][0]["path"] == outfit_rel
    assert jobs["jobs"][0]["references"][0]["sha256"] == identity.file_sha256(root / outfit_rel)


def test_bind_job_references_resolves_outfit_from_multi_character_binding(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    shared = root / "出图" / "共享" / "图片"
    shared.mkdir(parents=True)
    face_rel = "出图/共享/图片/CHAR_A__face.png"
    outfit_rel = "出图/共享/图片/CHAR_A__OUTFIT_TRAVEL.png"
    (root / face_rel).write_bytes(PNG_1X1)
    (root / outfit_rel).write_bytes(PNG_1X1)
    registry = {
        "assets": {
            "CHAR_A": {
                "id": "CHAR_A",
                "reference_images": [{"view": "face", "path": face_rel}],
                "outfits": {
                    "OUTFIT_TRAVEL": {
                        "id": "OUTFIT_TRAVEL",
                        "status": "ready",
                        "reference_images": [{"path": outfit_rel}],
                    }
                },
            }
        }
    }
    jobs = {
        "jobs": [
            {
                "panel_id": "P019",
                "character_bindings": [
                    {"character_id": "CHAR_A", "outfit_id": "OUTFIT_TRAVEL"},
                    {"character_id": "CHAR_B", "outfit_id": "OUTFIT_BASE"},
                ],
                "references": [
                    {
                        "id": "CHAR_A",
                        "role": "outfit",
                        "view": "outfit",
                        "path": face_rel,
                        "sha256": identity.file_sha256(root / face_rel),
                    }
                ],
            }
        ]
    }

    changed = identity.bind_job_references(root, jobs, registry)

    assert changed == 1
    assert jobs["jobs"][0]["references"][0]["path"] == outfit_rel
    assert jobs["jobs"][0]["references"][0]["sha256"] == identity.file_sha256(root / outfit_rel)


def test_bind_job_references_preserves_registered_expression_reference(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    shared = root / "出图" / "共享" / "图片"
    shared.mkdir(parents=True)
    face_rel = "出图/共享/图片/CHAR_A__face.png"
    expression_rel = "出图/共享/图片/CHAR_A__EXPR_STUNNED.png"
    (root / face_rel).write_bytes(PNG_1X1)
    (root / expression_rel).write_bytes(PNG_1X1)
    registry = {
        "assets": {
            "CHAR_A": {
                "id": "CHAR_A",
                "reference_images": [{"view": "face", "path": face_rel}],
                "expressions": {
                    "EXPR_STUNNED": {
                        "id": "EXPR_STUNNED",
                        "reference_images": [{"path": expression_rel}],
                    }
                },
            }
        }
    }
    jobs = {
        "jobs": [
            {
                "panel_id": "P001",
                "character_bindings": [
                    {"character_id": "CHAR_A", "expression_id": "EXPR_STUNNED"}
                ],
                "references": [
                    {
                        "id": "CHAR_A",
                        "role": "expression",
                        "view": "expression",
                        "contract_id": "EXPR_STUNNED",
                        "path": face_rel,
                    }
                ],
            }
        ]
    }

    changed = identity.bind_job_references(root, jobs, registry)

    assert changed == 1
    assert jobs["jobs"][0]["references"][0]["path"] == expression_rel


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
    assert registry["assets"]["CHAR_A"]["status"] == "needs_fix"
    assert registry["assets"]["CHAR_A"]["view_readiness"] == {
        "required": ["front", "three_quarter", "side", "back", "face"],
        "tier": "core_full",
        "ready": ["front"],
        "missing": ["three_quarter", "side", "back", "face"],
        "complete": False,
    }
    manifest = json.loads((root / "生产数据" / "comic_identity_views_第1话.json").read_text(encoding="utf-8"))
    assert manifest["items"][0]["status"] == "character_view_reused"
    assert manifest["items"][0]["sha256"] == identity.file_sha256(shared / "CHAR_A__front.png")


def test_views_can_generate_front_from_text_anchor(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    (root / "出图" / "共享").mkdir(parents=True)
    (root / "出图" / "共享" / "图片").mkdir(parents=True)
    (root / "设定库").mkdir(parents=True)
    style_path = root / "出图" / "共享" / "图片" / "STYLE_A__anchor.png"
    style_path.write_bytes(PNG_1X1)
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "assets": {
                    "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "anchor_path": "出图/共享/图片/STYLE_A__anchor.png",
                    },
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
    assert image_paths == [style_path]
    assert "本次没有已采纳角色图片作为附件" in prompt
    assert "它只用于继承线条、上色、明暗、材质和墨晕语言" in prompt
    assert "不得继承其中人物的脸、发型、服装" in prompt
    assert "不生成临时剧情手持物" in prompt
    registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    source = registry["assets"]["CHAR_A"]["reference_images"][0]["source"]
    assert source["kind"] == "generated_character_view_text_seed"
    assert source["anchor_kind"] == "text_prompt_seed"
    assert source["style_reference_path"] == "出图/共享/图片/STYLE_A__anchor.png"
    assert source["style_reference_sha256"] == identity.file_sha256(style_path)
    assert source["style_reference_role"] == "style_only"
    assert source["prompt_sha256"]
    assert (root / source["prompt_path"]).is_file()
    assert registry["assets"]["CHAR_A"]["status"] == "needs_fix"


def test_views_can_generate_dreamina_front_from_style_only_seed(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    style_path = root / "出图" / "共享" / "图片" / "STYLE_A__anchor.png"
    style_path.parent.mkdir(parents=True)
    style_path.write_bytes(PNG_1X1)
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "assets": {
                    "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "anchor_path": "出图/共享/图片/STYLE_A__anchor.png",
                    },
                    "CHAR_A": {
                        "id": "CHAR_A",
                        "type": "character",
                        "display_name": "甲",
                        "character_dna": "方脸，高髻，灰衣。",
                        "reference_images": [],
                        "views": {},
                    },
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls: list[tuple[Path, str]] = []

    def fake_run_dreamina_image(
        prompt: str,
        anchor: Path,
        out_path: Path,
        *,
        timeout_sec: int,
        poll_sec: int,
        model_version: str,
        resolution_type: str,
        ratio: str,
    ) -> tuple[bool, str, str]:
        calls.append((anchor, prompt))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(PNG_1X1)
        return True, "submit-char-a", ""

    monkeypatch.setattr(identity.shutil, "which", lambda name: "/usr/bin/dreamina" if name == "dreamina" else None)
    monkeypatch.setattr(identity, "run_dreamina_image", fake_run_dreamina_image)

    rc = identity.generate_views(
        type(
            "Args",
            (),
            {
                "project_root": str(root),
                "chapter": "第1话",
                "characters": "CHAR_A",
                "views": "front",
                "backend": "dreamina",
                "overwrite": False,
                "candidate_count": 0,
                "candidate_indices": "",
                "max_attempts": 1,
                "timeout_sec": 10,
                "poll_sec": 2,
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
    assert calls and calls[0][0] == style_path
    assert "本次没有已采纳角色图片作为附件" in calls[0][1]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    source = registry["assets"]["CHAR_A"]["reference_images"][0]["source"]
    assert source["anchor_kind"] == "style_only_text_prompt_seed"
    assert source["backend"] == identity.DREAMINA_CHANNEL
    assert source["model"] == "Dreamina 5.0"
    assert source["style_reference_path"] == "出图/共享/图片/STYLE_A__anchor.png"
    assert source["style_reference_role"] == "style_only"
    assert source["submit_id"] == "submit-char-a"


def test_outfits_can_generate_with_dreamina_and_keep_channel_provenance(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    front = root / "出图" / "共享" / "图片" / "CHAR_A__front.png"
    front.parent.mkdir(parents=True)
    front.write_bytes(PNG_1X1)
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "assets": {
                    "CHAR_A": {
                        "id": "CHAR_A",
                        "type": "character",
                        "display_name": "甲",
                        "character_dna": "方脸，高髻。",
                        "outfits": {
                            "OUTFIT_WINTER": {
                                "id": "OUTFIT_WINTER",
                                "wardrobe_standard": "深蓝交领冬衣，窄袖，无披风。",
                                "reference_images": [],
                            }
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls: list[tuple[Path, str]] = []

    def fake_run_dreamina_image(
        prompt: str,
        anchor: Path,
        out_path: Path,
        *,
        timeout_sec: int,
        poll_sec: int,
        model_version: str,
        resolution_type: str,
        ratio: str,
    ) -> tuple[bool, str, str]:
        calls.append((anchor, ratio))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(PNG_1X1)
        return True, "submit-outfit-a", ""

    monkeypatch.setattr(identity.shutil, "which", lambda name: "/usr/bin/dreamina" if name == "dreamina" else None)
    monkeypatch.setattr(identity, "dreamina_version", lambda: "dreamina test")
    monkeypatch.setattr(identity, "run_dreamina_image", fake_run_dreamina_image)

    rc = identity.generate_outfit_references(
        type(
            "Args",
            (),
            {
                "project_root": str(root),
                "chapter": "第1话",
                "bindings": "CHAR_A=OUTFIT_WINTER",
                "backend": "dreamina",
                "overwrite": False,
                "ratio": "3:4",
                "max_attempts": 1,
                "timeout_sec": 10,
                "poll_sec": 2,
                "model_version": "5.0",
                "resolution_type": "2k",
            },
        )()
    )

    assert rc == 0
    assert calls == [(front, "3:4")]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    source = registry["assets"]["CHAR_A"]["outfits"]["OUTFIT_WINTER"]["reference_images"][0]["source"]
    assert source["backend"] == identity.DREAMINA_CHANNEL
    assert source["model"] == "Dreamina 5.0"
    assert source["submit_id"] == "submit-outfit-a"
    assert source["identity_anchor_path"] == "出图/共享/图片/CHAR_A__front.png"
    manifest = json.loads((root / "生产数据" / "comic_identity_outfits_第1话.json").read_text(encoding="utf-8"))
    assert manifest["execution_mode"] == "dreamina_official_cli"
    assert manifest["backend"] == identity.DREAMINA_CHANNEL


def test_anchors_generate_non_character_text_anchor(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    (root / "出图" / "共享").mkdir(parents=True)
    style_path = root / "出图" / "共享" / "图片" / "STYLE_A__anchor.png"
    style_path.parent.mkdir(parents=True)
    style_path.write_bytes(PNG_1X1)
    (root / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(
            {
                "assets": {
                    "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "anchor_path": "出图/共享/图片/STYLE_A__anchor.png",
                    },
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
    assert image_paths == [style_path]
    assert "参考 ID：PROP_A" in prompt
    assert "只用于继承线条、上色、明暗、材质、色域和墨晕语言" in prompt
    registry = json.loads((root / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    asset = registry["assets"]["PROP_A"]
    assert asset["anchor_path"].endswith("PROP_A__anchor.png")
    source = asset["reference_images"][0]["source"]
    assert source["kind"] == "generated_text_anchor"
    assert source["style_reference_path"] == "出图/共享/图片/STYLE_A__anchor.png"
    assert source["style_reference_role"] == "style_only"
    assert source["prompt_sha256"]
    assert (root / source["prompt_path"]).is_file()


def test_anchors_generate_non_character_with_dreamina_style_reference(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    style_path = root / "出图" / "共享" / "图片" / "STYLE_A__anchor.png"
    style_path.parent.mkdir(parents=True)
    style_path.write_bytes(PNG_1X1)
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "assets": {
                    "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "anchor_path": "出图/共享/图片/STYLE_A__anchor.png",
                    },
                    "PROP_A": {
                        "id": "PROP_A",
                        "type": "prop",
                        "display_name": "旧木牌",
                        "prop_contract": "木牌完整，边缘磨损，不生成可读文字。",
                        "reference_images": [],
                    },
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls: list[tuple[Path, str]] = []

    def fake_run_dreamina_image(
        prompt: str,
        anchor: Path,
        out_path: Path,
        *,
        timeout_sec: int,
        poll_sec: int,
        model_version: str,
        resolution_type: str,
        ratio: str,
    ) -> tuple[bool, str, str]:
        calls.append((anchor, ratio))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(PNG_1X1)
        return True, "submit-prop-a", ""

    monkeypatch.setattr(identity.shutil, "which", lambda name: "/usr/bin/dreamina" if name == "dreamina" else None)
    monkeypatch.setattr(identity, "dreamina_version", lambda: "dreamina test")
    monkeypatch.setattr(identity, "run_dreamina_image", fake_run_dreamina_image)

    rc = identity.generate_anchors(
        type(
            "Args",
            (),
            {
                "project_root": str(root),
                "chapter": "第1话",
                "refs": "PROP_A",
                "overwrite": False,
                "candidate_count": 0,
                "backend": "dreamina",
                "ratio": "4:5",
                "max_attempts": 1,
                "timeout_sec": 10,
                "poll_sec": 2,
                "model_version": "5.0",
                "resolution_type": "2k",
            },
        )()
    )

    assert rc == 0
    assert calls == [(style_path, "3:4")]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    source = registry["assets"]["PROP_A"]["reference_images"][0]["source"]
    assert source["backend"] == identity.DREAMINA_CHANNEL
    assert source["model"] == "Dreamina 5.0"
    assert source["style_reference_path"] == "出图/共享/图片/STYLE_A__anchor.png"
    assert source["submit_id"] == "submit-prop-a"
    assert source["submitted_ratio"] == "3:4"


def test_monster_anchor_prompt_consumes_character_dna_and_does_not_force_tail() -> None:
    prompt = identity.asset_anchor_prompt(
        "MON_TIGER",
        {
            "type": "monster",
            "display_name": "虎首妖将",
            "character_dna": "直立双足人体，两条人形手臂，只有头部是虎首，无尾巴",
        },
        visual_style="国风厚涂条漫",
    )

    assert "dna_contract: 直立双足人体" in prompt
    assert "人身兽首必须保持直立双足人体结构" in prompt
    assert "尾部和标志纹理清楚" not in prompt


def test_anchor_candidate_batch_does_not_adopt_unreviewed_images(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    (root / "出图" / "共享").mkdir(parents=True)
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "assets": {
                    "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "display_name": "风格校准锚",
                        "style_contract": "低饱和矿物色、清楚线条与三值明暗。",
                        "reference_images": [],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls: list[str] = []

    def fake_run_codex_image(prompt: str, repo: Path, timeout_sec: int, image_paths: list[Path]):
        calls.append(prompt)
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
                "refs": "STYLE_A",
                "overwrite": False,
                "candidate_count": 3,
                "ratio": "4:5",
                "max_attempts": 2,
                "timeout_sec": 1,
            },
        )()
    )

    assert rc == 0
    assert len(calls) == 3
    assert all("画幅固定为 4:5" in prompt for prompt in calls)
    candidates = sorted((root / "出图" / "共享" / "candidates" / "STYLE_A" / "anchor").rglob("candidate_*.png"))
    assert len(candidates) == 3
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "anchor_path" not in registry["assets"]["STYLE_A"]
    assert registry["assets"]["STYLE_A"]["reference_images"] == []
    manifests = list((root / "生产数据").glob("comic_identity_anchor_candidates_第1话_*.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["generated"] == 3
    assert manifest["failed"] == 0
    assert manifest["adopted"] is False


def test_anchor_candidate_batch_uses_dreamina_text2image_and_records_ratio_adapter(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "项目"
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        json.dumps(
            {
                "assets": {
                    "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "display_name": "风格校准锚",
                        "style_contract": "低饱和矿物色、清楚线条与三值明暗。",
                        "reference_images": [],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, str, str, str]] = []

    def fake_run_dreamina_text_image(
        prompt: str,
        out_path: Path,
        *,
        timeout_sec: int,
        poll_sec: int,
        model_version: str,
        resolution_type: str,
        ratio: str,
    ) -> tuple[bool, str, str]:
        calls.append((prompt, model_version, resolution_type, ratio))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(PNG_1X1)
        return True, "submit-style-a", ""

    monkeypatch.setattr(identity.shutil, "which", lambda name: "/usr/bin/dreamina" if name == "dreamina" else None)
    monkeypatch.setattr(identity, "dreamina_version", lambda: "dreamina test")
    monkeypatch.setattr(identity, "run_dreamina_text_image", fake_run_dreamina_text_image)

    rc = identity.generate_anchors(
        type(
            "Args",
            (),
            {
                "project_root": str(root),
                "chapter": "第1话",
                "refs": "STYLE_A",
                "overwrite": False,
                "candidate_count": 1,
                "backend": "dreamina",
                "ratio": "4:5",
                "max_attempts": 1,
                "timeout_sec": 10,
                "poll_sec": 2,
                "model_version": "5.0",
                "resolution_type": "2k",
            },
        )()
    )

    assert rc == 0
    assert len(calls) == 1
    assert calls[0][1:] == ("5.0", "2k", "3:4")
    manifest_path = next((root / "生产数据").glob("comic_identity_anchor_candidates_第1话_*.json"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["backend"] == identity.DREAMINA_CHANNEL
    assert manifest["model"] == "Dreamina 5.0"
    assert manifest["ratio"] == "4:5"
    assert manifest["submitted_ratio"] == "3:4"
    assert manifest["items"][0]["submit_id"] == "submit-style-a"
    ledger = json.loads((root / "生产数据" / "comic_identity_attempt_ledger_第1话.json").read_text(encoding="utf-8"))
    assert ledger["attempts"][0]["backend"] == identity.DREAMINA_CHANNEL
    assert ledger["attempts"][0]["status"] == "succeeded"
    assert "anchor_path" not in json.loads(registry_path.read_text(encoding="utf-8"))["assets"]["STYLE_A"]


def test_adopt_anchor_candidate_binds_human_review_and_sha(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    registry_path = root / "出图" / "共享" / "identity_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        json.dumps({"assets": {"STYLE_A": {"id": "STYLE_A", "type": "style", "reference_images": []}}}),
        encoding="utf-8",
    )
    candidate = root / "出图" / "共享" / "candidates" / "STYLE_A" / "anchor" / "batch" / "candidate_02.png"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(PNG_1X1)

    rc = identity.adopt_anchor_candidate(
        type(
            "Args",
            (),
            {
                "project_root": str(root),
                "chapter": "第1话",
                "ref": "STYLE_A",
                "candidate": str(candidate.relative_to(root)),
                "reviewer": "甲",
                "role": "出品人",
                "reason": "采纳B",
            },
        )()
    )

    assert rc == 0
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    asset = registry["assets"]["STYLE_A"]
    adopted = root / asset["anchor_path"]
    assert adopted.read_bytes() == PNG_1X1
    assert candidate.is_file()
    source = asset["reference_images"][0]["source"]
    assert source["kind"] == "human_selected_candidate_anchor"
    assert source["reviewer"] == "甲"
    assert source["reviewer_role"] == "出品人"
    assert source["candidate_sha256"] == identity.file_sha256(candidate)
    receipt = json.loads(
        (root / "生产数据" / "comic_identity_anchor_adoption_STYLE_A.json").read_text(encoding="utf-8")
    )
    assert receipt["adopted_sha256"] == receipt["candidate_sha256"]


def test_front_candidate_batch_uses_style_only_and_does_not_register_views(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    shared = root / "出图" / "共享"
    style_path = shared / "图片" / "STYLE_A__anchor.png"
    style_path.parent.mkdir(parents=True)
    style_path.write_bytes(PNG_1X1)
    registry_path = shared / "identity_registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "assets": {
                    "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "anchor_path": "出图/共享/图片/STYLE_A__anchor.png",
                        "reference_images": [],
                    },
                    "CHAR_A": {
                        "id": "CHAR_A",
                        "type": "character",
                        "character_dna": "方脸、窄眼、中等体态",
                        "reference_images": [],
                    },
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
                "candidate_count": 3,
                "allow_text_anchor": True,
                "ratio": "3:4",
                "max_attempts": 2,
                "timeout_sec": 1,
            },
        )()
    )

    assert rc == 0
    assert len(calls) == 3
    assert all(paths == [style_path] for _, paths in calls)
    assert all("画幅固定为 3:4" in prompt for prompt, _ in calls)
    assert all("不得继承其中人物的脸、发型、服装" in prompt for prompt, _ in calls)
    candidates = sorted((shared / "candidates" / "CHAR_A" / "front").rglob("candidate_*.png"))
    assert len(candidates) == 3
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    assert "views" not in registry["assets"]["CHAR_A"]
    assert registry["assets"]["CHAR_A"]["reference_images"] == []
    manifests = list((root / "生产数据").glob("comic_identity_front_candidates_第1话_*.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["generated"] == 3
    assert manifest["failed"] == 0
    assert manifest["style_reference_role"] == "style_only"
    assert manifest["adopted"] is False


def test_front_candidate_batch_persists_interrupted_manifest(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "项目"
    style_path = root / "出图" / "共享" / "图片" / "STYLE_A__anchor.png"
    style_path.parent.mkdir(parents=True)
    style_path.write_bytes(PNG_1X1)
    registry = {"assets": {"CHAR_A": {"id": "CHAR_A", "type": "character"}}}

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(identity, "run_codex_image", interrupted)
    try:
        identity.generate_front_view_candidates(
            root=root,
            repo=tmp_path,
            registry=registry,
            characters=["CHAR_A"],
            chapter="第1话",
            candidate_count=3,
            candidate_indices=[1, 2, 3],
            max_attempts=2,
            timeout_sec=1,
            ratio="3:4",
            visual_style="测试风格",
            style_reference=style_path,
            backend_version="codex test",
        )
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("expected KeyboardInterrupt")

    manifests = list((root / "生产数据").glob("comic_identity_front_candidates_第1话_*.json"))
    assert len(manifests) == 1
    manifest = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert manifest["status"] == "interrupted"
    assert manifest["items"][0]["status"] == "character_view_candidate_interrupted"
    assert manifest["items"][0]["attempt"] == 1


def test_style_and_fx_prefixes_have_specialized_anchor_contracts() -> None:
    style_prompt = identity.asset_anchor_prompt(
        "STYLE_CLASSIC_V1",
        {
            "type": "style",
            "display_name": "古典工笔风格锚",
            "style_contract": "细线、矿物淡彩、水墨边缘。",
        },
        visual_style="新国风工笔淡彩",
    )
    fx_prompt = identity.asset_anchor_prompt(
        "FX_INK_TRANSITION",
        {
            "type": "effect",
            "display_name": "水墨转场",
            "prop_contract": "墨晕由实到虚。",
        },
        visual_style="新国风工笔淡彩",
    )

    assert identity.ref_type("STYLE_CLASSIC_V1") == "style"
    assert identity.ref_type("FX_INK_TRANSITION") == "vfx"
    assert "单幅、非叙事的漫画风格校准画" in style_prompt
    assert "不是项目角色、影视演员" in style_prompt
    assert "单一视觉特效 reference art" in fx_prompt


def test_style_anchor_prompt_does_not_inject_classical_defaults() -> None:
    prompt = identity.asset_anchor_prompt(
        "STYLE_NEON_NOIR",
        {
            "type": "style",
            "display_name": "露萅黑色科幻",
            "description": "高对比冷色几何形、硬表面和城市雨夜",
        },
        visual_style="黑色科幻图形漫画",
    )
    assert "黑色科幻图形漫画" in prompt
    assert "高对比冷色几何形" in prompt
    assert "无具体身份的古典人物" not in prompt
    assert "矿物淡彩、三值明暗和墨晕" not in prompt
    assert "不得自行假定古典" in prompt


def test_location_anchor_reserves_blocking_without_baking_in_characters() -> None:
    prompt = identity.asset_anchor_prompt(
        "LOC_SPIRIT_RIVER",
        {
            "type": "scene",
            "display_name": "灵河岸",
            "prop_contract": "三生石左后，神瑛右中。",
        },
        visual_style="新国风工笔淡彩",
    )

    assert "不出现任何具体人物、人物剪影或角色表演" in prompt
    assert "只在对应位置保留可用的空白与走位空间" in prompt


def test_single_view_contact_sheet_uses_casting_grid(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    shared = root / "出图" / "共享" / "图片"
    shared.mkdir(parents=True)
    characters = [f"CHAR_{index}" for index in range(6)]
    for character_id in characters:
        (shared / f"{character_id}__front.png").write_bytes(PNG_1X1)

    rel = identity.write_character_view_contact_sheet(root, "第1话", characters, ["front"])

    from PIL import Image

    image = Image.open(root / rel)
    assert image.width > 700
    assert image.height < 1000


def test_adopt_generated_png_archives_previous_candidate(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    dest = root / "出图" / "共享" / "图片" / "CHAR_A__front.png"
    candidate = dest.with_name(".CHAR_A__front__pending.png")
    dest.parent.mkdir(parents=True)
    old_bytes = PNG_1X1 + b"old"
    new_bytes = PNG_1X1 + b"new"
    dest.write_bytes(old_bytes)
    candidate.write_bytes(new_bytes)

    archived = identity.adopt_generated_png(
        root,
        candidate,
        dest,
        asset_id="CHAR_A",
        variant="front",
    )

    assert archived
    assert dest.read_bytes() == new_bytes
    assert (root / archived).read_bytes() == old_bytes
    assert not candidate.exists()


def test_required_views_for_tiers():
    import identity as _id
    assert _id.required_views_for({"library_tier": "named_minimal"}) == ("front", "face")
    assert _id.required_views_for({"tier": "recurring_standard"}) == ("front", "three_quarter", "face")
    assert _id.required_views_for({"library_tier": "core_full"}) == _id.REQUIRED_CHARACTER_VIEWS
    assert _id.required_views_for({}) == _id.REQUIRED_CHARACTER_VIEWS
    assert _id.required_views_for(None) == _id.REQUIRED_CHARACTER_VIEWS
    assert _id.required_views_for({"library_tier": "restricted_partial"}) == ()


def test_story_bible_notes_use_exact_stable_heading_id(tmp_path: Path) -> None:
    root = tmp_path / "项目"
    bible = root / "设定库" / "story_bible.md"
    bible.parent.mkdir(parents=True)
    bible.write_text(
        "# 故事圣经\n\n"
        "### 林冲之子 CHAR_LINCHONG\n- 不应误取\n\n"
        "### 林冲 CHAR_LIN\n- 角色DNA：豹头环眼\n\n"
        "#### 基础服装\n- 青灰圆领袍\n\n"
        "### 鲁智深 CHAR_LU\n- 角色DNA：面圆耳大\n",
        encoding="utf-8",
    )

    notes = identity.story_bible_character_notes(root, "CHAR_LIN")

    assert notes.startswith("### 林冲 CHAR_LIN")
    assert "豹头环眼" in notes
    assert "青灰圆领袍" in notes
    assert "不应误取" not in notes
    assert "面圆耳大" not in notes


def test_report_audits_monster_views_like_characters(tmp_path: Path) -> None:
    # 2026-07-17 P015 虎妖漂移回归：MON_ 必须与 CHAR_ 一样进视图完整性与 model-pack 审计。
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
                        "status": "ready",
                        "reference_input_count": 0,
                        "references": [
                            {"id": "MON_TIGER", "path": "出图/共享/图片/MON_TIGER__anchor.png"},
                        ],
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    identity.report(type("Args", (), {"project_root": str(root), "chapter": chapter, "write": False})())
    report = json.loads((root / "生产数据" / f"comic_identity_report_{chapter}.json").read_text(encoding="utf-8"))
    assert "MON_TIGER" in report["character_views"]
    assert "MON_TIGER" in report["missing_character_views"]
    assert "MON_TIGER" in report["model_pack_reports"]
