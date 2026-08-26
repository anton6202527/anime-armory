from __future__ import annotations

import json
import multiprocessing
import os
import sys
from pathlib import Path

from PIL import Image
import pytest


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import export_longstrip


CHAPTER = "第1话"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_project(tmp_path: Path) -> Path:
    root = tmp_path / "作品"
    panel = root / "出图" / CHAPTER / "panels" / "P001.png"
    panel.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (96, 64), (30, 60, 90)).save(panel)
    write_json(root / "排版" / CHAPTER / "layout.json", {
        "schema_version": 2,
        "geometry_profile": "longstrip_single_column",
        "canvas": {"width": 96, "height": "auto"},
        "segments": [{
            "segment_id": "SCROLL_001", "width": 96, "height": 64,
            "reading_order": ["P001"],
            "panels": [{"panel_id": "P001", "x": 0, "y": 0, "w": 96, "h": 64, "bubble_slots": []}],
        }],
    })
    (root / "_设置.md").write_text("- 导出格式: png\n- 目标平台: 通用\n- 合规用途: 自用草稿\n", encoding="utf-8")
    return root


def run_export(root: Path, monkeypatch: pytest.MonkeyPatch) -> int:
    monkeypatch.setattr(sys, "argv", [
        "export_longstrip.py", str(root), "--chapter", CHAPTER,
        "--formats", "png", "--render", "--no-lettering",
    ])
    return export_longstrip.main()


def _render_record(path: str, staged_path: Path, *, panel_ids: list[str] | None = None) -> dict:
    record = {
        "path": path,
        "format": "png",
        "size": {"width": 48, "height": 32},
        "sha256": export_longstrip.sha256_file(staged_path),
        "size_bytes": staged_path.stat().st_size,
    }
    if panel_ids is not None:
        record["panel_ids"] = panel_ids
    return record


def _concurrent_finalize_worker(
    root_raw: str,
    digest: str,
    color: tuple[int, int, int],
    barrier,
    results,
) -> None:
    root = Path(root_raw)
    chapter_dir = root / "排版" / CHAPTER
    staging = export_longstrip.begin_render_staging(chapter_dir, digest)
    staged_page = staging / "pages" / "page_001.png"
    staged_long = staging / "longstrip" / "longstrip.png"
    Image.new("RGB", (48, 32), color).save(staged_page)
    Image.new("RGB", (48, 32), color).save(staged_long)
    canonical_page = root / "排版" / CHAPTER / "pages" / "page_001.png"
    canonical_long = root / "排版" / CHAPTER / "长图" / "longstrip.png"
    manifest = {
        "chapter": CHAPTER,
        "render_digest": digest,
        "pages": [_render_record(str(canonical_page.relative_to(root)), staged_page, panel_ids=["P001"])],
        "rendered": [_render_record(str(canonical_long.relative_to(root)), staged_long)],
        "documents": [],
    }
    barrier.wait(timeout=15)
    try:
        export_longstrip.finalize_render_bundle(
            root,
            chapter_dir,
            staging,
            digest,
            manifest,
            page_dir=canonical_page.parent,
            out_dir=canonical_long.parent,
            pdf_path=root / "排版" / CHAPTER / "print" / f"{CHAPTER}.pdf",
            manifest_path=chapter_dir / "export_manifest.json",
            qc_target=None,
            activate=True,
        )
        results.put({"digest": digest, "status": "ok"})
    except BaseException as exc:  # pragma: no cover - returned to parent for assertion
        results.put({"digest": digest, "status": "error", "error": repr(exc)})


def test_successful_render_activates_digest_bundle_and_compatible_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = build_project(tmp_path)

    assert run_export(root, monkeypatch) == 0

    chapter_dir = root / "排版" / CHAPTER
    pointer = json.loads((chapter_dir / "active_render_bundle.json").read_text(encoding="utf-8"))
    manifest = json.loads((chapter_dir / "export_manifest.json").read_text(encoding="utf-8"))
    bundle = root / pointer["bundle"]
    output = root / manifest["rendered"][0]["path"]

    assert pointer["render_digest"] == manifest["render_digest"]
    assert bundle.is_dir()
    assert (bundle / "export_manifest.json").is_file()
    assert output.is_file()
    assert manifest["rendered"][0]["sha256"] == export_longstrip.sha256_file(output)
    assert manifest["render_bundle_validation"]["verdict"] == "pass"


def test_failed_rerender_preserves_previous_manifest_pointer_and_pixels(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = build_project(tmp_path)
    assert run_export(root, monkeypatch) == 0
    chapter_dir = root / "排版" / CHAPTER
    manifest_path = chapter_dir / "export_manifest.json"
    pointer_path = chapter_dir / "active_render_bundle.json"
    old_manifest = manifest_path.read_bytes()
    old_pointer = pointer_path.read_bytes()
    output_path = root / json.loads(old_manifest)["rendered"][0]["path"]
    old_pixels = output_path.read_bytes()
    Image.new("RGB", (96, 64), (180, 20, 20)).save(root / "出图" / CHAPTER / "panels" / "P001.png")

    def fail_save(*_args, **_kwargs):
        raise OSError("injected renderer failure")

    monkeypatch.setattr(export_longstrip, "save_canvas", fail_save)

    assert run_export(root, monkeypatch) == 2
    assert manifest_path.read_bytes() == old_manifest
    assert pointer_path.read_bytes() == old_pointer
    assert output_path.read_bytes() == old_pixels
    attempts = list((chapter_dir / ".render_staging").glob("*/export_manifest.json"))
    assert attempts
    attempt = json.loads(attempts[-1].read_text(encoding="utf-8"))
    assert attempt["preserved_active_bundle"] is True
    assert attempt["render_error"] == "injected renderer failure"


def test_same_digest_valid_png_tamper_is_detected_before_staging_discard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = build_project(tmp_path)
    assert run_export(root, monkeypatch) == 0
    chapter_dir = root / "排版" / CHAPTER
    pointer_path = chapter_dir / "active_render_bundle.json"
    manifest_path = chapter_dir / "export_manifest.json"
    old_pointer = pointer_path.read_bytes()
    old_manifest = manifest_path.read_bytes()
    pointer = json.loads(old_pointer)
    bundle = root / pointer["bundle"]
    bundle_manifest = json.loads((bundle / "export_manifest.json").read_text(encoding="utf-8"))
    bundle_page = bundle / "pages" / Path(bundle_manifest["pages"][0]["path"]).name
    with Image.open(bundle_page) as image:
        original_size = image.size
    Image.new("RGB", original_size, (220, 15, 35)).save(bundle_page, format="PNG")
    with Image.open(bundle_page) as image:
        image.load()
        assert image.format == "PNG"

    assert run_export(root, monkeypatch) == 2

    assert pointer_path.read_bytes() == old_pointer
    assert manifest_path.read_bytes() == old_manifest
    attempts = list((chapter_dir / ".render_staging").glob("*/export_manifest.json"))
    assert attempts, "validated reconstruction staging must not be discarded when same-digest bundle is corrupt"


def test_two_process_promotions_never_split_pointer_manifest_and_pixels(tmp_path: Path) -> None:
    root = tmp_path / "作品"
    chapter_dir = root / "排版" / CHAPTER
    chapter_dir.mkdir(parents=True)
    context = multiprocessing.get_context("fork")
    barrier = context.Barrier(2)
    results = context.Queue()
    processes = [
        context.Process(target=_concurrent_finalize_worker, args=(str(root), "a" * 64, (210, 30, 30), barrier, results)),
        context.Process(target=_concurrent_finalize_worker, args=(str(root), "b" * 64, (30, 30, 210), barrier, results)),
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    outcomes = [results.get(timeout=2), results.get(timeout=2)]
    assert all(item["status"] == "ok" for item in outcomes), outcomes

    pointer = json.loads((chapter_dir / "active_render_bundle.json").read_text(encoding="utf-8"))
    manifest = json.loads((chapter_dir / "export_manifest.json").read_text(encoding="utf-8"))
    assert pointer["render_digest"] == manifest["render_digest"]
    assert pointer["transaction_id"]
    assert export_longstrip.validate_active_render_state(root, pointer) == []
    canonical_page = root / manifest["pages"][0]["path"]
    bundle_page = root / pointer["bundle"] / "pages" / canonical_page.name
    assert canonical_page.read_bytes() == bundle_page.read_bytes()
    assert export_longstrip.sha256_file(canonical_page) == manifest["pages"][0]["sha256"]
    assert not (chapter_dir / ".render_promotion.json").exists()


def test_pointer_cas_rejects_stale_old_pointer_before_any_mirror_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = build_project(tmp_path)
    assert run_export(root, monkeypatch) == 0
    chapter_dir = root / "排版" / CHAPTER
    pointer_path = chapter_dir / "active_render_bundle.json"
    stale_snapshot = export_longstrip._path_snapshot(pointer_path)
    externally_changed = json.loads(pointer_path.read_text(encoding="utf-8"))
    externally_changed["external_revision"] = "not-this-transaction"
    write_json(pointer_path, externally_changed)
    changed_bytes = pointer_path.read_bytes()
    transaction_id = "c" * 32
    pending = export_longstrip._prepare_copy(None, pointer_path, "c" * 64, transaction_id)
    write_json(pending, {"transaction_id": transaction_id})

    with export_longstrip.chapter_render_lock(chapter_dir):
        with pytest.raises(RuntimeError, match="CAS failed"):
            export_longstrip._atomic_promote_bundle_mirrors_locked(
                root,
                chapter_dir,
                "c" * 64,
                [(pending, pointer_path)],
                pointer_path,
                transaction_id=transaction_id,
                expected_old_pointer=stale_snapshot,
                pointer_payload={"transaction_id": transaction_id},
            )

    assert pointer_path.read_bytes() == changed_bytes
    assert pending.is_file()
    assert not (chapter_dir / ".render_promotion.json").exists()


def test_recovery_rolls_back_crash_before_active_pointer_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = build_project(tmp_path)
    assert run_export(root, monkeypatch) == 0
    chapter_dir = root / "排版" / CHAPTER
    pointer_path = chapter_dir / "active_render_bundle.json"
    manifest_path = chapter_dir / "export_manifest.json"
    old_pointer = pointer_path.read_bytes()
    old_manifest = manifest_path.read_bytes()
    old_replace = os.replace

    Image.new("RGB", (96, 64), (180, 20, 20)).save(root / "出图" / CHAPTER / "panels" / "P001.png")

    def crash_before_pointer(source, target):
        if Path(target).resolve() == pointer_path.resolve():
            raise SystemExit("simulated hard stop before pointer CAS")
        return old_replace(source, target)

    original_recovery = export_longstrip._recover_interrupted_promotion_locked
    recovery_calls = 0

    def leave_journal(*args, **kwargs):
        nonlocal recovery_calls
        recovery_calls += 1
        if recovery_calls == 1:
            return original_recovery(*args, **kwargs)
        raise SystemExit("simulated process died before in-process recovery")

    with monkeypatch.context() as isolated:
        isolated.setattr(export_longstrip.os, "replace", crash_before_pointer)
        isolated.setattr(export_longstrip, "recover_interrupted_promotion", lambda *_args, **_kwargs: False)
        isolated.setattr(export_longstrip, "_recover_interrupted_promotion_locked", leave_journal)
        with pytest.raises(SystemExit):
            run_export(root, isolated)

    assert not pointer_path.exists(), "crash occurred between pointer backup and pointer CAS"
    assert (chapter_dir / ".render_promotion.json").is_file()
    assert export_longstrip.recover_interrupted_promotion(root, chapter_dir) is True

    assert pointer_path.read_bytes() == old_pointer
    assert manifest_path.read_bytes() == old_manifest
    assert not (chapter_dir / ".render_promotion.json").exists()


def test_recovery_commits_pointer_switched_transaction_after_full_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = build_project(tmp_path)
    assert run_export(root, monkeypatch) == 0
    chapter_dir = root / "排版" / CHAPTER
    pointer_path = chapter_dir / "active_render_bundle.json"
    old_pointer = pointer_path.read_bytes()
    Image.new("RGB", (96, 64), (10, 170, 80)).save(root / "出图" / CHAPTER / "panels" / "P001.png")

    def crash_during_cleanup(*_args, **_kwargs):
        raise SystemExit("simulated process died after pointer switch")

    original_recovery = export_longstrip._recover_interrupted_promotion_locked
    recovery_calls = 0

    def leave_journal(*args, **kwargs):
        nonlocal recovery_calls
        recovery_calls += 1
        if recovery_calls == 1:
            return original_recovery(*args, **kwargs)
        raise SystemExit("simulated process died before in-process recovery")

    with monkeypatch.context() as isolated:
        isolated.setattr(export_longstrip, "_cleanup_journal_entries", crash_during_cleanup)
        isolated.setattr(export_longstrip, "recover_interrupted_promotion", lambda *_args, **_kwargs: False)
        isolated.setattr(export_longstrip, "_recover_interrupted_promotion_locked", leave_journal)
        with pytest.raises(SystemExit):
            run_export(root, isolated)

    switched_pointer = pointer_path.read_bytes()
    assert switched_pointer != old_pointer
    assert (chapter_dir / ".render_promotion.json").is_file()

    assert export_longstrip.recover_interrupted_promotion(root, chapter_dir) is True

    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    assert pointer_path.read_bytes() == switched_pointer
    assert export_longstrip.validate_active_render_state(root, pointer) == []
    assert not (chapter_dir / ".render_promotion.json").exists()
