from __future__ import annotations

import json
import multiprocessing
import shutil
import subprocess
from pathlib import Path

import pytest

import loudness_conform
import media_artifact as media


def _promotion_worker(start, results, root: str, episode: str, candidate: str, canonical: str,
                      expected_sha: str, spec: dict, recipe: str, transaction_id: str) -> None:
    start.wait(timeout=10)
    result = media.promote_candidate(
        root, episode, candidate, canonical, expected_sha, spec,
        recipe_path=recipe, transaction_id=transaction_id,
    )
    results.put({"status": result.get("status"), "reason": result.get("reason")})


def _raw_program(path: Path, color: str = "blue") -> None:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg unavailable")
    path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([
        "ffmpeg", "-nostdin", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c={color}:s=160x90:r=24:d=1.2",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=1.2",
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-x264-params", "colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv",
        "-c:a", "aac", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(path),
    ], capture_output=True, text=True, check=False, timeout=60)
    assert proc.returncode == 0, proc.stderr


def _master(path: Path, color: str = "blue") -> None:
    raw = path.with_name(path.stem + ".raw.mp4")
    _raw_program(raw, color)
    result = loudness_conform.two_pass_conform(str(raw), str(path), target_lufs=-16.0)
    assert result["status"] == "pass", result


def _duration(path: Path) -> float:
    return float(media.probe_media(path)["duration_sec"])


def _recipe(path: Path, episode: str, duration: float) -> Path:
    payload = {
        "kind": media.RECIPE_KIND,
        "version": media.RECIPE_VERSION,
        "episode": episode,
        "generated_at": "2026-08-26T00:00:00+00:00",
        "picture": {"duration_sec": round(duration, 6)},
        "ordered_sources": [{
            "clip": "Clip_01",
            "source_sha256": "a" * 64,
            "edit_duration_sec": round(duration, 6),
        }],
        "duration_sec": round(duration, 6),
    }
    hash_scope = dict(payload)
    hash_scope.pop("generated_at")
    payload["recipe_sha256"] = media.canonical_json_sha(hash_scope)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_shared_validator_proves_full_decode_spec_faststart_and_loudness(tmp_path: Path) -> None:
    master = tmp_path / "master.mp4"
    _master(master)
    spec = media.default_master_spec(width=160, height=90, fps="24", target_lufs=-16.0)

    result = media.validate_media(master, spec)

    assert result["status"] == "pass"
    codes = {row["code"]: row["status"] for row in result["checks"]}
    assert codes["full_decode"] == "pass"
    assert codes["faststart"] == "pass"
    assert codes["integrated_loudness"] == "pass"
    assert result["probe"]["audio"]["sample_rate"] == 48000


def test_render_transaction_cas_preserves_previous_and_writes_current_receipt(tmp_path: Path) -> None:
    root, ep = tmp_path, "第1集"
    canonical = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    candidate = root / "合成" / ep / ".stage" / "candidate.mp4"
    _master(canonical, "red")
    _master(candidate, "green")
    old_sha = media.sha256_file(canonical)
    recipe = root / "生产数据" / "timelines" / ep / "render_recipe.json"
    _recipe(recipe, ep, _duration(candidate))
    spec = media.default_master_spec(width=160, height=90, fps="24", target_lufs=-16.0)

    result = media.promote_candidate(
        root, ep, candidate, canonical, old_sha, spec,
        recipe_path=recipe, transaction_id="tx-test",
    )

    assert result["status"] == "pass"
    assert result["previous_version"]
    assert (root / result["previous_version"]).is_file()
    current = media.current_receipt(root, ep, canonical)
    assert current["status"] == "pass"
    assert current["receipt"]["transaction_id"] == "tx-test"
    assert current["artifact_sha256"] != old_sha


def test_render_transaction_rejects_stale_expected_sha_without_overwrite(tmp_path: Path, monkeypatch) -> None:
    canonical = tmp_path / "合成" / "第1集" / "成片_第1集_zh.mp4"
    candidate = tmp_path / "candidate.mp4"
    _master(canonical, "red")
    _master(candidate, "green")
    before = media.sha256_file(canonical)
    spec = media.default_master_spec(width=160, height=90, fps="24", target_lufs=-16.0)
    monkeypatch.setattr(media, "validate_media", lambda *_args, **_kwargs: pytest.fail("stale CAS must skip decode/QC"))

    result = media.promote_candidate(tmp_path, "第1集", candidate, canonical, "stale", spec)

    assert result["status"] == "conflict"
    assert media.sha256_file(canonical) == before
    assert candidate.is_file()


def test_render_transaction_restores_previous_if_receipt_publication_fails(tmp_path: Path, monkeypatch) -> None:
    root, ep = tmp_path, "第1集"
    canonical = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    candidate = root / "合成" / ep / ".stage" / "candidate.mp4"
    _master(canonical, "red")
    _master(candidate, "green")
    old_sha = media.sha256_file(canonical)
    new_sha = media.sha256_file(candidate)
    spec = media.default_master_spec(width=160, height=90, fps="24", target_lufs=-16.0)
    recipe = _recipe(root / "生产数据" / "timelines" / ep / "render_recipe.json", ep, _duration(candidate))
    monkeypatch.setattr(media, "write_receipt", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")))

    result = media.promote_candidate(root, ep, candidate, canonical, old_sha, spec, recipe_path=recipe)

    assert result["reason"] == "promotion_failed_rolled_back"
    assert media.sha256_file(canonical) == old_sha
    assert candidate.is_file()
    assert media.sha256_file(candidate) == new_sha


def test_api_lock_serializes_competing_promotions(tmp_path: Path) -> None:
    root, ep = tmp_path, "第1集"
    canonical = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    first = root / "合成" / ep / ".stage-a" / "candidate.mp4"
    second = root / "合成" / ep / ".stage-b" / "candidate.mp4"
    _master(canonical, "red")
    _master(first, "green")
    _master(second, "blue")
    old_sha = media.sha256_file(canonical)
    candidate_shas = {media.sha256_file(first), media.sha256_file(second)}
    spec = media.default_master_spec(width=160, height=90, fps="24", target_lufs=-16.0)
    recipe = _recipe(root / "生产数据" / "timelines" / ep / "render_recipe.json", ep, _duration(first))

    ctx = multiprocessing.get_context("spawn")
    start = ctx.Event()
    results = ctx.Queue()
    workers = [
        ctx.Process(target=_promotion_worker, args=(
            start, results, str(root), ep, str(candidate), str(canonical), old_sha, spec,
            str(recipe), f"tx-{index}",
        ))
        for index, candidate in enumerate((first, second), 1)
    ]
    for worker in workers:
        worker.start()
    start.set()
    for worker in workers:
        worker.join(timeout=30)
        assert worker.exitcode == 0
    outcomes = [results.get(timeout=5), results.get(timeout=5)]

    assert sum(row["status"] == "pass" for row in outcomes) == 1
    assert all(row["status"] in {"pass", "busy", "conflict"} for row in outcomes)
    assert media.sha256_file(canonical) in candidate_shas
    assert media.current_receipt(root, ep, canonical)["status"] == "pass"
    assert not media._promotion_lock_path(canonical).exists()


def test_minimal_forged_receipt_and_non_mp4_artifact_are_rejected(tmp_path: Path) -> None:
    ep = "第1集"
    fake = tmp_path / "合成" / ep / "not-a-master.txt"
    fake.parent.mkdir(parents=True)
    fake.write_text("not media", encoding="utf-8")
    receipt = {
        "kind": media.KIND,
        "version": media.VERSION,
        "episode": ep,
        "status": "pass",
        "canonical_artifact": fake.relative_to(tmp_path).as_posix(),
        "artifact": {
            "path": fake.relative_to(tmp_path).as_posix(),
            "sha256": media.sha256_file(fake),
            "size_bytes": fake.stat().st_size,
        },
        "validation": {"status": "pass"},
    }
    media.write_receipt(tmp_path, ep, receipt)

    current = media.current_receipt(tmp_path, ep, fake)

    assert current["status"] == "block"
    assert any("validator_version" in issue for issue in current["issues"])
    assert any("not an MP4" in issue for issue in current["issues"])


def test_current_receipt_requires_complete_saved_validation_structure(tmp_path: Path) -> None:
    root, ep = tmp_path, "第1集"
    canonical = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    candidate = root / "candidate.mp4"
    _master(candidate)
    recipe = _recipe(root / "生产数据" / "timelines" / ep / "render_recipe.json", ep, _duration(candidate))
    spec = media.default_master_spec(width=160, height=90, fps="24", target_lufs=-16.0)
    assert media.promote_candidate(root, ep, candidate, canonical, "missing", spec, recipe_path=recipe)["status"] == "pass"
    receipt_file = media.receipt_path(root, ep)
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    receipt["validation"]["checks"] = [
        row for row in receipt["validation"]["checks"] if row.get("code") != "full_decode"
    ]
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    current = media.current_receipt(root, ep, canonical)

    assert current["status"] == "block"
    assert any("full_decode" in issue for issue in current["issues"])


def test_current_receipt_revalidates_current_bytes_against_embedded_spec(tmp_path: Path, monkeypatch) -> None:
    root, ep = tmp_path, "第1集"
    canonical = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    candidate = root / "candidate.mp4"
    _master(candidate)
    recipe = _recipe(root / "生产数据" / "timelines" / ep / "render_recipe.json", ep, _duration(candidate))
    spec = media.default_master_spec(width=160, height=90, fps="24", target_lufs=-16.0)
    assert media.promote_candidate(root, ep, candidate, canonical, "missing", spec, recipe_path=recipe)["status"] == "pass"
    calls = []
    monkeypatch.setattr(media, "validate_media", lambda *args, **kwargs: calls.append(args) or {"status": "block", "checks": []})

    current = media.current_receipt(root, ep, canonical)

    assert current["status"] == "block"
    assert len(calls) == 1
    assert any("revalidation" in issue for issue in current["issues"])


def test_decodable_truncated_master_is_blocked_by_recipe_duration(tmp_path: Path) -> None:
    root, ep = tmp_path, "第1集"
    canonical = root / "合成" / ep / f"成片_{ep}_zh.mp4"
    candidate = root / "candidate.mp4"
    _master(candidate)
    full_duration = _duration(candidate)
    recipe = _recipe(root / "生产数据" / "timelines" / ep / "render_recipe.json", ep, full_duration)
    spec = media.default_master_spec(width=160, height=90, fps="24", target_lufs=-16.0)
    assert media.promote_candidate(root, ep, candidate, canonical, "missing", spec, recipe_path=recipe)["status"] == "pass"

    truncated = root / "truncated.mp4"
    _raw_program(truncated, "green")
    shortened = root / "short.mp4"
    proc = subprocess.run([
        "ffmpeg", "-nostdin", "-y", "-v", "error", "-i", str(truncated), "-t", "0.55",
        "-c:v", "copy", "-c:a", "copy", "-movflags", "+faststart", str(shortened),
    ], capture_output=True, text=True, check=False, timeout=60)
    assert proc.returncode == 0, proc.stderr
    shortened.replace(canonical)
    receipt_file = media.receipt_path(root, ep)
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    receipt["artifact"]["sha256"] = media.sha256_file(canonical)
    receipt["artifact"]["size_bytes"] = canonical.stat().st_size
    receipt_file.write_text(json.dumps(receipt), encoding="utf-8")

    current = media.current_receipt(root, ep, canonical)

    assert current["status"] == "block"
    checks = {row["code"]: row["status"] for row in current["current_validation"]["checks"]}
    assert checks["full_decode"] == "pass"
    assert checks["timeline_not_truncated"] == "block"
