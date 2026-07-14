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
