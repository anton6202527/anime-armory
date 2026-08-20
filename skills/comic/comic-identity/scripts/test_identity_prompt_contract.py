from __future__ import annotations

import json
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("identity.py")
spec = importlib.util.spec_from_file_location("comic_identity_script", SCRIPT)
identity = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(identity)


def fake_png(path: Path, width: int = 768, height: int = 1024) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, height), (70, 90, 110)).save(path)


def accepted_source(root: Path, asset_id: str, variant: str, path: Path, *, kind: str) -> dict:
    qc = identity.write_identity_image_qc(
        root,
        "第1话",
        asset_id,
        variant,
        path,
        registration_kind=kind,
        source={"kind": "test_fixture"},
    )
    assert qc["verdict"] == "pass"
    qc["human_review"] = {
        "status": "accepted",
        "artifact_sha256": qc["artifact_sha256"],
        "comparison_inputs_sha256": qc["comparison_inputs_sha256"],
        "contact_sheet_sha256": qc["contact_sheet_sha256"],
        "reviewed_by": "test-reviewer",
        "reviewed_at": "2026-08-20T00:00:00",
        "reason": "fixture reviewed",
    }
    receipt = identity.identity_qc_path(root, asset_id, variant)
    identity.write_json(receipt, qc)
    return {
        "kind": "test_fixture",
        "per_image_acceptance": {
            "status": "accepted",
            "artifact_sha256": qc["artifact_sha256"],
            "receipt_path": identity.rel_to_root(root, receipt),
        },
    }


def test_default_wardrobe_standard_is_compiled_into_prompt_contract() -> None:
    asset = {
        "type": "character",
        "display_name": "甲",
        "default_binding": {"outfit_id": "OUTFIT_COURT"},
        "outfits": {
            "OUTFIT_COURT": {
                "wardrobe_standard": {
                    "name": "朝服",
                    "collar_neckline": "圆领",
                    "forbidden": ["明代补子"],
                }
            }
        },
    }
    contract = identity.character_asset_contract(asset)
    assert "默认服装 OUTFIT_COURT" in contract
    assert "圆领" in contract and "明代补子" in contract


def test_front_view_registers_as_default_outfit_reference(tmp_path: Path) -> None:
    front = tmp_path / "出图" / "共享" / "图片" / "CHAR_A__front.png"
    fake_png(front)
    registry = {
        "assets": {
            "CHAR_A": {
                "id": "CHAR_A",
                "type": "character",
                "library_tier": "named_minimal",
                "default_binding": {"outfit_id": "OUTFIT_BASE"},
                "outfits": {"OUTFIT_BASE": {"reference_images": [], "status": "needs_reference"}},
            }
        }
    }
    identity.register_character_view(
        registry,
        tmp_path,
        "CHAR_A",
        "front",
        front,
        source=accepted_source(tmp_path, "CHAR_A", "front", front, kind="character_view"),
    )
    outfit = registry["assets"]["CHAR_A"]["outfits"]["OUTFIT_BASE"]
    assert outfit["status"] == "ready"
    assert outfit["reference_images"][0]["path"].endswith("CHAR_A__front.png")


def test_monster_front_prompt_uses_species_anatomy_not_human_standing() -> None:
    prompt = identity.character_text_anchor_prompt(
        "MON_TIGER",
        "真实虎类体态",
        visual_style="低饱和国漫",
        asset_contract="四足兽",
    )
    assert "四足承重" in prompt
    assert "不得人立或穿衣" in prompt


def test_outfit_binding_parser_and_prompt_lock_identity() -> None:
    assert identity.parse_outfit_bindings("CHAR_A=OUTFIT_TRAVEL") == [("CHAR_A", "OUTFIT_TRAVEL")]
    prompt = identity.outfit_reference_prompt(
        "CHAR_A",
        "OUTFIT_TRAVEL",
        "四十岁官员",
        visual_style="低饱和国漫",
        identity_contract="长方脸",
        outfit_contract="灰褐交领窄袖；禁止仙侠飘带",
    )
    assert "本次只替换为指定服装" in prompt
    assert "脸型、眼型/眼距" in prompt
    assert "禁止仙侠飘带" in prompt


def test_expression_binding_parser_and_prompt_lock_identity() -> None:
    assert identity.parse_expression_bindings("CHAR_A=EXPR_TERRIFIED") == [("CHAR_A", "EXPR_TERRIFIED")]
    prompt = identity.character_expression_prompt(
        "CHAR_A",
        "EXPR_TERRIFIED",
        {"name": "惊恐失态", "emotion": "terrified", "intensity": "high"},
        "四十岁官员",
        visual_style="低饱和国漫",
        asset_contract="长方脸；窄眼；微高发际线",
    )
    assert "只改变面部肌肉" in prompt
    assert "惊恐失态" in prompt and "high" in prompt
    assert "不得换脸" in prompt and "对白气泡" in prompt


def test_target_canvas_for_ratio_expands_without_crop() -> None:
    target = identity.target_canvas_for_ratio((1024, 1536), "4:5")
    assert target[0] * 5 == target[1] * 4
    assert target[0] >= 1024 and target[1] >= 1536
    assert identity.target_canvas_for_ratio((1086, 1448), "3:4") == (1086, 1448)


def test_codex_failure_is_classified_and_manifest_safe() -> None:
    proc = identity.subprocess.CompletedProcess(
        ["codex"],
        124,
        stdout="very long prompting guide " * 1000,
        stderr="ERROR transport channel closed\nHTTP 403 Forbidden\ntimeout after 180s",
    )
    failure = identity.format_failure(proc)
    assert "class=backend_timeout" in failure
    assert "timeout after 180s" in failure
    assert "HTTP 403" not in failure
    assert len(failure) < 600


def test_codex_forbidden_is_classified_when_process_did_not_timeout() -> None:
    proc = identity.subprocess.CompletedProcess(
        ["codex"],
        1,
        stdout="",
        stderr="HTTP 403 Forbidden",
    )
    failure = identity.format_failure(proc)
    assert "class=backend_forbidden" in failure
    assert "HTTP 403 Forbidden" in failure


def test_codex_event_diagnostics_records_control_events_without_payload_content() -> None:
    stdout = "\n".join(
        [
            json.dumps({"type": "thread.started", "thread_id": "thread-test"}),
            json.dumps(
                {
                    "type": "item.started",
                    "item": {"type": "image_generation", "status": "in_progress", "result": "secret-image"},
                }
            ),
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "image_generation", "status": "completed", "result": "secret-image"},
                }
            ),
        ]
    )
    diagnostics = identity.codex_event_diagnostics(stdout, "timeout after 600s")
    assert diagnostics["json_event_count"] == 3
    assert diagnostics["image_generation_begin_seen"] is True
    assert diagnostics["image_generation_end_seen"] is True
    assert diagnostics["thread_id"] == "thread-test"
    assert diagnostics["item_type_counts"] == {
        "item.started:image_generation": 1,
        "item.completed:image_generation": 1,
    }
    assert "secret-image" not in json.dumps(diagnostics)


def test_codex_image_call_uses_empty_ephemeral_workdir_instead_of_repo(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    reference = tmp_path / "style.png"
    fake_png(reference)
    captured: dict[str, object] = {}

    def fake_subprocess_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        return identity.subprocess.CompletedProcess(cmd, 0, stdout="{}", stderr="")

    monkeypatch.setattr(identity.subprocess, "run", fake_subprocess_run)
    result = identity.run_codex_image("diagnostic prompt", repo, 30, [reference])
    assert result.returncode == 0
    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert "--ephemeral" in cmd and "--skip-git-repo-check" in cmd
    assert cmd[cmd.index("--image") + 1] == str(reference)
    workdir = Path(cmd[cmd.index("-C") + 1])
    assert workdir != repo.resolve()
    assert repo.resolve() not in workdir.parents
    assert not workdir.exists()


def test_decode_image_event_accepts_codex_exec_saved_path_item(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generated_root = tmp_path / "generated_images"
    saved = generated_root / "thread-a" / "call-a.png"
    fake_png(saved, 1254, 1254)
    monkeypatch.setattr(identity, "codex_generated_images_root", lambda: generated_root)
    stdout = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "id": "item_0",
                "type": "image_generation",
                "status": "completed",
                "saved_path": str(saved),
            },
        }
    )
    recovered = tmp_path / "recovered.png"
    assert identity.decode_image_event(stdout, recovered) is True
    assert recovered.read_bytes() == saved.read_bytes()


def test_decode_image_event_rejects_saved_path_outside_codex_image_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    generated_root = tmp_path / "generated_images"
    generated_root.mkdir()
    outside = tmp_path / "outside.png"
    fake_png(outside)
    monkeypatch.setattr(identity, "codex_generated_images_root", lambda: generated_root)
    stdout = json.dumps(
        {
            "type": "item.completed",
            "item": {
                "type": "image_generation",
                "status": "completed",
                "saved_path": str(outside),
            },
        }
    )
    assert identity.decode_image_event(stdout, tmp_path / "should-not-exist.png") is False


def test_backend_probe_persists_started_before_call_and_does_not_consume_asset_ledger(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(identity.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(identity, "codex_image_feature_status", lambda: "stable")
    monkeypatch.setattr(identity, "codex_version", lambda: "codex-cli test")

    def fake_run(prompt: str, repo: Path, timeout_sec: int, image_paths: list[Path]):
        health = identity.load_json(identity.backend_health_manifest_path(tmp_path, "第1话"))
        assert health["latest_status"] == "started"
        assert health["probes"][-1]["status"] == "started"
        assert image_paths == []
        return identity.subprocess.CompletedProcess(["codex"], 0, stdout="{}", stderr="")

    def fake_decode(stdout: str, out_path: Path) -> bool:
        fake_png(out_path, 1024, 1024)
        return True

    monkeypatch.setattr(identity, "run_codex_image", fake_run)
    monkeypatch.setattr(identity, "decode_image_event", fake_decode)
    args = identity.argparse.Namespace(
        project_root=str(tmp_path),
        chapter="第1话",
        reason="resume after circuit breaker",
        timeout_sec=30,
        external_status="operational",
        external_status_url="https://status.example.test",
        external_status_checked_at="2026-07-15T16:30:00+08:00",
    )
    assert identity.probe_backend(args) == 0
    health = identity.load_json(identity.backend_health_manifest_path(tmp_path, "第1话"))
    probe = health["probes"][-1]
    assert health["latest_status"] == "succeeded"
    assert probe["status"] == "succeeded"
    assert probe["requested_probe_mode"] == "auto"
    assert probe["probe_scope"] == "text_only"
    assert probe["asset_attempt_ledger_consumed"] is False
    assert probe["width"] == 1024 and probe["height"] == 1024
    assert not identity.generation_attempt_ledger_path(tmp_path, "第1话").exists()


def test_backend_probe_auto_matches_reference_attached_production_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    style = tmp_path / "出图" / "共享" / "图片" / "STYLE_A__anchor.png"
    fake_png(style, 1024, 1280)
    accepted_source(tmp_path, "STYLE_A", "anchor", style, kind="asset_anchor")
    identity.write_json(
        identity.registry_path(tmp_path),
        {
            "schema_version": 2,
            "kind": "comic_identity_registry",
            "assets": {
                "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "status": "ready",
                        "anchor_path": "出图/共享/图片/STYLE_A__anchor.png",
                }
            },
        },
    )
    monkeypatch.setattr(identity.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(identity, "codex_image_feature_status", lambda: "stable")
    monkeypatch.setattr(identity, "codex_version", lambda: "codex-cli test")

    def fake_run(prompt: str, repo: Path, timeout_sec: int, image_paths: list[Path]):
        assert image_paths == [style]
        assert "style-only" in prompt
        return identity.subprocess.CompletedProcess(["codex"], 0, stdout="{}", stderr="")

    def fake_decode(stdout: str, out_path: Path) -> bool:
        fake_png(out_path, 1024, 1024)
        return True

    monkeypatch.setattr(identity, "run_codex_image", fake_run)
    monkeypatch.setattr(identity, "decode_image_event", fake_decode)
    args = identity.argparse.Namespace(
        project_root=str(tmp_path),
        chapter="第1话",
        reason="match production request class",
        timeout_sec=30,
        probe_mode="auto",
        external_status="operational",
        external_status_url="https://status.example.test",
        external_status_checked_at="2026-07-15T16:30:00+08:00",
    )
    assert identity.probe_backend(args) == 0
    probe = identity.load_json(identity.backend_health_manifest_path(tmp_path, "第1话"))["probes"][-1]
    assert probe["probe_scope"] == "reference_attached"
    assert probe["reference_inputs"] == [
        {
            "path": "出图/共享/图片/STYLE_A__anchor.png",
            "sha256": identity.file_sha256(style),
            "role": "style_only",
        }
    ]


def test_backend_probe_production_character_front_profile_is_calibration_only(
    tmp_path: Path,
    monkeypatch,
) -> None:
    style = tmp_path / "出图" / "共享" / "图片" / "STYLE_A__anchor.png"
    fake_png(style, 1024, 1280)
    accepted_source(tmp_path, "STYLE_A", "anchor", style, kind="asset_anchor")
    identity.write_json(
        identity.registry_path(tmp_path),
        {
            "schema_version": 2,
            "kind": "comic_identity_registry",
            "assets": {
                "STYLE_A": {
                        "id": "STYLE_A",
                        "type": "style",
                        "status": "ready",
                        "anchor_path": "出图/共享/图片/STYLE_A__anchor.png",
                }
            },
        },
    )
    monkeypatch.setattr(identity.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(identity, "codex_image_feature_status", lambda: "stable")
    monkeypatch.setattr(identity, "codex_version", lambda: "codex-cli test")

    def fake_run(prompt: str, repo: Path, timeout_sec: int, image_paths: list[Path]):
        assert image_paths == [style]
        assert "anonymous adult male Northern Song court official" in prompt
        assert "must never be adopted into an identity registry" in prompt
        assert "Image 1 is style-only" in prompt
        return identity.subprocess.CompletedProcess(["codex"], 0, stdout="{}", stderr="")

    def fake_decode(stdout: str, out_path: Path) -> bool:
        fake_png(out_path, 1024, 1536)
        return True

    monkeypatch.setattr(identity, "run_codex_image", fake_run)
    monkeypatch.setattr(identity, "decode_image_event", fake_decode)
    args = identity.argparse.Namespace(
        project_root=str(tmp_path),
        chapter="第1话",
        reason="calibrate production latency",
        timeout_sec=600,
        probe_mode="auto",
        probe_profile="production-character-front",
        external_status="operational",
        external_status_url="https://status.example.test",
        external_status_checked_at="2026-07-15T19:30:00+08:00",
    )
    assert identity.probe_backend(args) == 0
    probe = identity.load_json(identity.backend_health_manifest_path(tmp_path, "第1话"))["probes"][-1]
    assert probe["probe_profile"] == "production-character-front"
    assert probe["production_request_class"] == "historical_character_front"
    assert probe["calibration_only"] is True
    assert probe["asset_attempt_ledger_consumed"] is False


def test_outfit_attempt_budget_survives_resume_and_migrates_v1() -> None:
    old_manifest = {
        "schema_version": 1,
        "items": [
            {
                "status": "outfit_reference_failed",
                "character_id": "CHAR_A",
                "outfit_id": "OUTFIT_TRAVEL",
            }
        ],
    }
    used, remaining = identity.outfit_remaining_attempts(
        old_manifest,
        "CHAR_A",
        "OUTFIT_TRAVEL",
        2,
    )
    assert (used, remaining) == (1, 1)

    resumed_manifest = {
        "schema_version": 2,
        "items": [
            {
                "status": "outfit_reference_failed",
                "character_id": "CHAR_A",
                "outfit_id": "OUTFIT_TRAVEL",
                "attempts_used": 2,
            }
        ],
    }
    assert identity.outfit_remaining_attempts(
        resumed_manifest,
        "CHAR_A",
        "OUTFIT_TRAVEL",
        2,
    ) == (2, 0)


def test_generation_attempt_ledger_counts_started_attempts_before_backend(tmp_path: Path) -> None:
    first_id, first_no = identity.begin_generation_attempt(
        tmp_path,
        "第1话",
        generation_kind="anchor",
        asset_id="LOC_A",
        variant="anchor",
        max_attempts_total=2,
        backend="Codex CLI",
        model="GPT Image 2",
        prompt_sha256="a" * 64,
    )
    assert first_id and first_no == 1
    identity.finish_generation_attempt(
        tmp_path,
        "第1话",
        first_id,
        status="failed",
        error="timeout",
    )
    second_id, second_no = identity.begin_generation_attempt(
        tmp_path,
        "第1话",
        generation_kind="anchor",
        asset_id="LOC_A",
        variant="anchor",
        max_attempts_total=2,
        backend="Codex CLI",
        model="GPT Image 2",
        prompt_sha256="a" * 64,
    )
    assert second_id and second_no == 2
    blocked_id, used = identity.begin_generation_attempt(
        tmp_path,
        "第1话",
        generation_kind="anchor",
        asset_id="LOC_A",
        variant="anchor",
        max_attempts_total=2,
        backend="Codex CLI",
        model="GPT Image 2",
        prompt_sha256="a" * 64,
    )
    assert blocked_id == "" and used == 2


def test_outfit_manifest_migration_survives_later_manifest_replacement(tmp_path: Path) -> None:
    legacy_manifest = {
        "schema_version": 2,
        "created_at": "2026-07-15T12:00:00",
        "max_attempts_total": 2,
        "items": [
            {
                "status": "outfit_reference_failed",
                "character_id": "CHAR_A",
                "outfit_id": "OUTFIT_TRAVEL",
                "attempts_used": 2,
            }
        ],
    }
    assert identity.migrate_outfit_attempts_from_manifest(
        tmp_path,
        "第1话",
        legacy_manifest,
        "CHAR_A",
        "OUTFIT_TRAVEL",
    ) == 2
    assert identity.migrate_outfit_attempts_from_manifest(
        tmp_path,
        "第1话",
        {},
        "CHAR_A",
        "OUTFIT_TRAVEL",
    ) == 2
    attempt_id, attempt = identity.begin_generation_attempt(
        tmp_path,
        "第1话",
        generation_kind="outfit",
        asset_id="CHAR_A",
        variant="OUTFIT_TRAVEL",
        max_attempts_total=2,
        backend="Codex CLI",
        model="GPT Image 2",
        prompt_sha256="b" * 64,
    )
    assert attempt_id == ""
    assert attempt == 2
