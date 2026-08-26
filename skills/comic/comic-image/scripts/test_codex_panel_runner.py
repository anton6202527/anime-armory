from pathlib import Path
import importlib.util
import json
import pytest


MODULE_PATH = Path(__file__).with_name("codex_panel_runner.py")
SPEC = importlib.util.spec_from_file_location("comic_codex_panel_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def write_png(path: Path, size: tuple[int, int] = (100, 100), color: tuple[int, int, int] = (40, 80, 120)) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def test_adopt_builtin_records_builtin_channel_without_mixing_recipe() -> None:
    assert runner.recorded_channel(adopt_builtin=True) == "内置 imagegen"
    assert runner.recorded_channel(adopt_builtin=False) == "Codex CLI"


def _spend_fixture(tmp_path: Path) -> tuple[dict, dict, Path]:
    data = {
        "jobs": [{
            "panel_id": "P001",
            "execution_input_sha256": "1" * 64,
            "source_contract_sha256": "2" * 64,
            "submit_prompt_sha256": "3" * 64,
        }]
    }
    envelope = runner.spend_envelope.issue_envelope(
        tmp_path,
        chapter="第1话",
        data=data,
        model=runner.CODEX_MODEL,
        channel=runner.CODEX_CHANNEL,
        scope=runner.spend_envelope.requested_scope("第1话", ["P001"], force=False),
        expires_at="2099-01-01T00:00:00Z",
        max_calls=2,
        max_attempts=1,
        currency="CNY",
        max_total="20",
        max_cost_per_call="10",
        approver="Wesley Chen",
        approval_reference="chat://budget/42",
        source_quote="我批准此范围和总额内的出图提交。",
    )
    path = runner.spend_envelope.default_envelope_path(tmp_path, "第1话")
    runner.spend_envelope.save_envelope(path, envelope)
    context = runner.prepare_spend_context(
        tmp_path,
        "第1话",
        data,
        data["jobs"],
        force=False,
        model=runner.CODEX_MODEL,
        channel=runner.CODEX_CHANNEL,
    )
    return data, context, path


def test_paid_wrapper_reserves_once_for_submit_plus_provider_polling(tmp_path: Path) -> None:
    _data, context, _path = _spend_fixture(tmp_path)
    provider_operations: list[str] = []

    def submit_and_poll() -> str:
        provider_operations.extend(["image2image", "query_result", "query_result", "download"])
        return "done"

    result, _reservation, _settlement = runner.run_paid_submission(
        context, panel_id="P001", retry_round=1, submit=submit_and_poll
    )
    ledger = runner.load_json(runner.spend_envelope.ledger_path(tmp_path))
    entry = next(iter(ledger["envelopes"].values()))
    assert result == "done"
    assert provider_operations.count("image2image") == 1
    assert len(entry["reservations"]) == 1


def test_unknown_cost_blocks_before_submit_and_does_not_consume(tmp_path: Path) -> None:
    data, context, path = _spend_fixture(tmp_path)
    # No call has been reserved yet.  Corrupting cost while recomputing the
    # digest models a human-issued but incomplete/unknown cost envelope.
    envelope = runner.load_json(path)
    envelope["cost"].pop("max_cost_per_call")
    envelope["authorization_sha256"] = runner.spend_envelope.sha256_json(
        runner.spend_envelope._authorization_material(envelope)
    )
    runner.spend_envelope.save_envelope(path, envelope)
    submitted = False

    def submit() -> None:
        nonlocal submitted
        submitted = True

    with pytest.raises(runner.spend_envelope.SpendAuthorizationError) as exc:
        runner.run_paid_submission(context, panel_id="P001", retry_round=1, submit=submit)
    assert exc.value.code == "unknown_cost"
    assert submitted is False
    assert not runner.spend_envelope.ledger_path(tmp_path).exists()


def write_current_gate_receipt(root: Path, jobs: Path, *, verdict: str = "pass") -> Path:
    chapter = "第1话"
    report = root / "生产数据" / f"comic_gate_image_preflight_{chapter}.json"
    fingerprint = runner.stage_inputs_fingerprint(root, chapter, "image_preflight")
    runner.write_json(report, {
        "kind": "comic_gate", "stage": "image_preflight", "chapter": chapter, "verdict": verdict,
        "inputs_fingerprint": fingerprint,
    })
    receipt = runner.gate_receipt_path(root, chapter)
    runner.write_json(receipt, {
        "kind": "comic_gate_receipt",
        "stage": "image_preflight",
        "chapter": chapter,
        "verdict": verdict,
        "execution_authorized": verdict != "block",
        "panel_jobs_sha256": runner.file_sha256(jobs),
        "inputs_fingerprint_sha256": fingerprint["sha256"],
        "report_path": str(report.relative_to(root)),
        "report_sha256": runner.file_sha256(report),
    })
    return receipt


def test_reference_attachment_budget_prioritizes_identity_scene_and_prop() -> None:
    records = [
        {"id": "STYLE_A", "path": "style.png"},
        {"id": "LOC_A", "path": "loc.png"},
        {"id": "CHAR_A", "path": "a.png"},
        {"id": "CHAR_B", "path": "b.png"},
        {"id": "PROP_A", "path": "prop.png"},
        {"id": "FX_A", "path": "fx.png"},
    ]

    selected, omitted = runner.select_reference_attachments(records)

    assert [record["id"] for record in selected] == ["STYLE_A", "LOC_A", "CHAR_A", "CHAR_B", "PROP_A"]
    assert [record["id"] for record in omitted] == ["FX_A"]


def test_reference_attachment_limit_three_keeps_all_required_subjects_and_scene() -> None:
    records = [
        {"id": "CHAR_A", "path": "a.png", "required": True},
        {"id": "MON_B", "path": "b.png", "required": True},
        {"id": "LOC_A", "path": "loc.png", "required": True},
        {"id": "STYLE_A", "path": "style.png", "required": False},
        {"id": "CHAR_A", "path": "a-front.png", "required": False},
    ]

    selected, omitted = runner.select_reference_attachments(records, limit=3)

    assert [record["id"] for record in selected] == ["CHAR_A", "MON_B", "LOC_A"]
    assert [record["id"] for record in omitted] == ["STYLE_A", "CHAR_A"]


def test_safety_shape_visual_prompt_preserves_plot_with_non_graphic_language() -> None:
    raw = "枯草间尸骸横陈，姜月初双手将横刀刺入裴长青胸口，血色飞溅，以妖血为墨。"
    shaped = runner.safety_shape_visual_prompt(raw)

    assert "姜月初" in shaped and "裴长青" in shaped
    assert "推向裴长青胸口" in shaped
    assert "静止无面剪影" in shaped
    assert "妖墨" in shaped
    assert "尸骸" not in shaped
    assert "刺入" not in shaped
    assert "妖血" not in shaped


def test_reference_manifest_discloses_omitted_text_only_contract(tmp_path: Path) -> None:
    used = [{"id": "CHAR_A", "path": "a.png", "abs_path": "/tmp/a.png", "sha256": "a"}]
    omitted = [{"id": "FX_A", "path": "fx.png", "abs_path": "/tmp/fx.png", "sha256": "f"}]

    path = runner.write_reference_manifest(tmp_path, "第1话", "P001", used, omitted)
    payload = runner.load_json(path)

    assert payload["reference_attachment_limit"] == 5
    assert payload["omitted_attachment_count"] == 1
    assert payload["omitted_attachments"][0]["id"] == "FX_A"
    assert "textual_contract_retained" in payload["omitted_attachments"][0]["reason"]


def test_post_qc_accepts_disclosed_tool_limit_omission(tmp_path: Path, monkeypatch) -> None:
    panel = tmp_path / "P015.png"
    write_png(panel)
    monkeypatch.setattr(runner, "likely_blank_bubble_regions", lambda _path: [])
    monkeypatch.setattr(runner, "likely_large_edge_blank_bands", lambda _path: [])
    job = {
        "panel_id": "P015",
        "size": {"width": 100, "height": 100},
        "references": [{"id": f"REF_{index}"} for index in range(6)],
    }
    used = [{"id": f"REF_{index}"} for index in range(5)]
    omitted = [{"id": "REF_5"}]

    payload = runner.post_qc_panel(tmp_path, "第1话", job, panel, used, omitted)

    assert payload["verdict"] == "pass"
    assert payload["omitted_attachment_count"] == 1
    assert payload["manual_review_required"] is True
    assert payload["artifact_sha256"] == runner.file_sha256(panel)
    assert payload["visual_review_packet"]["status"] == "ready_for_human_review"


def test_post_qc_counts_one_attachment_reused_for_multiple_semantic_roles(
    tmp_path: Path, monkeypatch
) -> None:
    panel = tmp_path / "P019.png"
    write_png(panel)
    shared_ref = tmp_path / "hong_xin_face.png"
    write_png(shared_ref, color=(120, 60, 30))
    monkeypatch.setattr(runner, "likely_blank_bubble_regions", lambda _path: [])
    monkeypatch.setattr(runner, "likely_large_edge_blank_bands", lambda _path: [])
    job = {
        "panel_id": "P019",
        "size": {"width": 100, "height": 100},
        "references": [
            {"id": "CHAR_HONG_XIN", "path": str(shared_ref), "role": "face"},
            {"id": "CHAR_HONG_XIN", "path": str(shared_ref), "role": "outfit"},
        ],
    }
    used = [{"id": "CHAR_HONG_XIN", "path": str(shared_ref), "abs_path": str(shared_ref), "role": "face"}]

    payload = runner.post_qc_panel(tmp_path, "第1话", job, panel, used, [])

    assert runner.declared_reference_attachment_count(tmp_path, job) == 1
    assert payload["verdict"] == "pass"


def test_large_edge_blank_band_detector_finds_paper_like_top_reservation(tmp_path: Path) -> None:
    from PIL import Image, ImageDraw

    panel = tmp_path / "blank_top.png"
    image = Image.new("RGB", (600, 900), (193, 190, 181))
    draw = ImageDraw.Draw(image)
    for y in range(270, 900, 12):
        draw.line((0, y, 600, 900 - (y % 100)), fill=(25 + y % 90, 35, 45), width=7)
    image.save(panel)

    candidates = runner.likely_large_edge_blank_bands(panel)

    assert any(candidate["edge"] == "top" and candidate["fraction"] >= 0.2 for candidate in candidates)


def test_large_edge_blank_band_detector_ignores_full_frame_art(tmp_path: Path) -> None:
    from PIL import Image

    panel = tmp_path / "full_frame.png"
    image = Image.new("RGB", (600, 900))
    pixels = image.load()
    for y in range(900):
        for x in range(600):
            pixels[x, y] = ((x * 17 + y * 7) % 256, (x * 5 + y * 13) % 256, (x * 11 + y * 3) % 256)
    image.save(panel)

    assert runner.likely_large_edge_blank_bands(panel) == []


def test_post_qc_blocks_max_resolution_without_native_master(tmp_path: Path, monkeypatch) -> None:
    panel = tmp_path / "P020.png"
    write_png(panel, (1200, 900))
    monkeypatch.setattr(runner, "likely_blank_bubble_regions", lambda _path: [])
    monkeypatch.setattr(runner, "likely_large_edge_blank_bands", lambda _path: [])
    job = {
        "panel_id": "P020",
        "size": {"width": 1200, "height": 900},
        "resolution_policy": "后端最高可达",
        "references": [],
    }

    payload = runner.post_qc_panel(tmp_path, "第1话", job, panel, [], [])

    assert payload["verdict"] == "block"
    assert {issue["category"] for issue in payload["issues"]} == {
        "resolution_lineage", "derivative_lineage", "master_pixel_metadata"
    }


def test_post_qc_blocks_upscaled_derivative(tmp_path: Path, monkeypatch) -> None:
    panel = tmp_path / "P021.png"
    write_png(panel, (1200, 900))
    monkeypatch.setattr(runner, "likely_blank_bubble_regions", lambda _path: [])
    monkeypatch.setattr(runner, "likely_large_edge_blank_bands", lambda _path: [])
    job = {
        "panel_id": "P021",
        "size": {"width": 1200, "height": 900},
        "resolution_policy": "后端最高可达",
        "resolution_provenance": {
            "master_path": "出图/第1话/masters/P021.png",
            "native_sha256": "a" * 64,
            "upscaled": True,
        },
        "references": [],
    }

    payload = runner.post_qc_panel(tmp_path, "第1话", job, panel, [], [])

    assert payload["verdict"] == "block"
    assert "resolution_upscale" in {issue["category"] for issue in payload["issues"]}


def test_gate_receipt_must_bind_current_panel_jobs_sha(tmp_path: Path) -> None:
    jobs = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text('{"jobs": []}\n', encoding="utf-8")
    write_current_gate_receipt(tmp_path, jobs)
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "current_pass"
    jobs.write_text('{"jobs": [{"panel_id":"P1"}]}\n', encoding="utf-8")
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "stale_or_not_passed"


def test_warn_receipt_can_authorize_when_there_are_no_blocks(tmp_path: Path) -> None:
    jobs = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text('{"jobs": []}', encoding="utf-8")
    write_current_gate_receipt(tmp_path, jobs, verdict="warn")
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "current_pass"


def test_gate_receipt_stales_when_non_job_preflight_input_changes(tmp_path: Path) -> None:
    jobs = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs.parent.mkdir(parents=True)
    jobs.write_text('{"jobs": []}', encoding="utf-8")
    settings = tmp_path / "_设置.md"
    settings.write_text("- 生产档位: 连载标准\n", encoding="utf-8")
    write_current_gate_receipt(tmp_path, jobs)
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "current_pass"
    settings.write_text("- 生产档位: 出版交付\n", encoding="utf-8")
    assert runner.validate_gate_receipt(tmp_path, "第1话", jobs)["status"] == "stale_or_not_passed"


def _reviewable_job(
    tmp_path: Path,
    monkeypatch,
    *,
    warning: bool = False,
    block: bool = False,
    color: tuple[int, int, int] = (40, 80, 120),
) -> tuple[dict, dict, Path, Path]:
    panel = tmp_path / "出图" / "第1话" / "panels" / "P001.png"
    master = tmp_path / "出图" / "第1话" / "masters" / "P001.png"
    write_png(panel, color=color)
    write_png(master, color=color)
    monkeypatch.setattr(
        runner,
        "likely_blank_bubble_regions",
        (lambda _path: [{"x": 1, "y": 1, "w": 20, "h": 20}]) if warning else (lambda _path: []),
    )
    monkeypatch.setattr(runner, "likely_large_edge_blank_bands", lambda _path: [])
    job = {
        "panel_id": "P001",
        "size": {"width": 100, "height": 100},
        "resolution_policy": "后端最高可达" if block else "按最终画布",
        "references": [],
        "result_path": str(panel.relative_to(tmp_path)),
        "master_path": str(master.relative_to(tmp_path)),
    }
    post_qc = runner.post_qc_panel(tmp_path, "第1话", job, panel, [], [])
    job.update(
        {
            "status": runner.status_after_post_qc(post_qc),
            "artifact_sha256": runner.file_sha256(panel),
            "post_qc": post_qc,
        }
    )
    data = {"jobs": [job]}
    jobs_path = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    runner.write_json(jobs_path, data)
    return data, job, jobs_path, panel


def structured_review(job: dict, reviewer: str, *, delegated: bool = False) -> str:
    packet = job["post_qc"]["visual_review_packet"]
    evidence = [
        {"path": item["path"], "sha256": item["sha256"]}
        for item in packet["comparison_inputs"]
    ]
    axes = {
        axis: {"verdict": "pass", "notes": f"{axis} current pixels checked", "evidence": evidence}
        for axis in packet["required_axes"]
    }
    return json.dumps({
        "kind": "comic_panel_visual_review",
        "artifact_sha256": job["artifact_sha256"],
        "comparison_inputs_sha256": packet["comparison_inputs_sha256"],
        "contact_sheet_sha256": packet["contact_sheet_sha256"],
        "reviewed_at": "2026-08-26T10:00:00+08:00",
        "evaluator": {"name": reviewer, "kind": "delegated_agent" if delegated else "human"},
        "axes": axes,
        "summary": "fixture structured current-pixel review",
    }, ensure_ascii=False)


def test_warn_never_auto_ready_but_named_review_can_accept(tmp_path: Path, monkeypatch) -> None:
    data, job, jobs_path, _panel = _reviewable_job(tmp_path, monkeypatch, warning=True)

    assert job["status"] == "qc_warn"
    assert not runner.panel_acceptance_status(tmp_path, job)["accepted"]
    accepted = runner.accept_panel_review(
        tmp_path, "第1话", data, jobs_path, "P001", "reviewer-a", structured_review(job, "reviewer-a")
    )

    assert accepted["accepted"] is True
    assert job["status"] == "ready"
    assert job["post_qc"]["manual_review"]["verdict"] == "accepted_with_warnings"
    assert job["post_qc"]["manual_review"]["acknowledged_warnings"][0]["code"] == "baked_text_container"


def test_key_panel_candidates_share_budget_each_pass_b14_and_auto_adopt_best(
    tmp_path: Path, monkeypatch
) -> None:
    data, job, jobs_path, panel = _reviewable_job(tmp_path, monkeypatch)
    master = tmp_path / job["master_path"]
    job.update({
        "execution_input_sha256": "1" * 64,
        "source_contract_sha256": "2" * 64,
        "submit_prompt_sha256": "3" * 64,
        "candidate_policy": {
            "enabled": True,
            "target_count": 2,
            "generation_order": "sequential_same_stage_budget_envelope",
            "each_candidate_requires_b14": True,
        },
    })
    runner.write_json(jobs_path, data)
    envelope = runner.spend_envelope.issue_envelope(
        tmp_path,
        chapter="第1话",
        data=data,
        model=runner.CODEX_MODEL,
        channel=runner.CODEX_CHANNEL,
        scope=runner.spend_envelope.requested_scope("第1话", ["P001"], force=False),
        expires_at="2099-01-01T00:00:00Z",
        max_calls=2,
        max_attempts=1,
        currency="CNY",
        max_total="20",
        max_cost_per_call="10",
        approver="Wesley Chen",
        approval_reference="chat://budget/key-panel",
        source_quote="我批准关键格在同一预算包内顺序生成两个候选。",
    )
    envelope_path = runner.spend_envelope.default_envelope_path(tmp_path, "第1话")
    runner.spend_envelope.save_envelope(envelope_path, envelope)
    context = runner.prepare_spend_context(
        tmp_path,
        "第1话",
        data,
        [job],
        force=False,
        model=runner.CODEX_MODEL,
        channel=runner.CODEX_CHANNEL,
    )

    def bind_paid_receipt() -> None:
        _result, reservation, settlement = runner.run_paid_submission(
            context, panel_id="P001", retry_round=1, submit=lambda: "generated"
        )
        job.update({
            "spend_envelope_id": context["authorization"]["envelope_id"],
            "spend_authorization_sha256": context["authorization"]["authorization_sha256"],
            "spend_consumption_id": reservation["consumption_id"],
            "spend_request_sha256": reservation["request_sha256"],
            "spend_actual_cost": settlement["actual_cost"],
            "spend_currency": reservation["currency"],
            "spend_status": settlement["status"],
        })

    bind_paid_receipt()
    first_sha = runner.file_sha256(panel)
    accepted_first = runner.accept_panel_review(
        tmp_path,
        "第1话",
        data,
        jobs_path,
        "P001",
        "reviewer-a",
        structured_review(job, "reviewer-a"),
    )
    assert accepted_first["candidate_result"]["status"] == "more_candidates_required"
    assert job["status"] == "planned"

    write_png(panel, color=(140, 55, 40))
    write_png(master, color=(140, 55, 40))
    monkeypatch.setattr(runner, "likely_blank_bubble_regions", lambda _path: [{"x": 1, "y": 1, "w": 20, "h": 20}])
    post_qc = runner.post_qc_panel(tmp_path, "第1话", job, panel, [], [])
    job.update({
        "status": runner.status_after_post_qc(post_qc),
        "artifact_sha256": runner.file_sha256(panel),
        "post_qc": post_qc,
        "result_path": str(panel.relative_to(tmp_path)),
        "master_path": str(master.relative_to(tmp_path)),
    })
    bind_paid_receipt()
    runner.write_json(jobs_path, data)
    accepted_second = runner.accept_panel_review(
        tmp_path,
        "第1话",
        data,
        jobs_path,
        "P001",
        "reviewer-a",
        structured_review(job, "reviewer-a"),
    )

    assert accepted_second["candidate_result"]["status"] == "adopted"
    assert job["status"] == "ready"
    assert runner.file_sha256(panel) == first_sha
    manifest = runner.load_json(runner.candidate_manifest_path(tmp_path, "第1话", "P001"))
    assert len(manifest["candidates"]) == 2
    assert {item["spend_receipt"]["envelope_id"] for item in manifest["candidates"]} == {
        envelope["envelope_id"]
    }
    assert all(item["spend_receipt"]["status"] == "settled" for item in manifest["candidates"])
    adoption = runner.load_json(tmp_path / "生产数据" / "panel_candidates" / "第1话" / "P001_adoption.json")
    assert adoption["candidate_id"] == manifest["candidates"][0]["candidate_id"]
    assert adoption["candidate_manifest_sha256"] == runner.hashlib.sha256(
        runner.json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    gate_path = MODULE_PATH.parents[2] / "comic-review" / "scripts" / "gate.py"
    gate_spec = importlib.util.spec_from_file_location("comic_gate_candidate_fixture", gate_path)
    assert gate_spec and gate_spec.loader
    gate_module = importlib.util.module_from_spec(gate_spec)
    gate_spec.loader.exec_module(gate_module)
    findings: list[dict] = []
    gate_module.check_panel_jobs_ready(tmp_path, "第1话", data, findings)
    assert not {
        item["code"] for item in findings
        if str(item.get("code") or "").startswith("candidate_")
    }


def test_authorized_delegate_can_accept_reversible_current_pixels(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "_设置.md").write_text(
        f"- 视觉审阅策略：{runner.delegated_visual_authorization.__globals__['POLICY']}\n",
        encoding="utf-8",
    )
    data, job, jobs_path, _panel = _reviewable_job(tmp_path, monkeypatch)
    status = runner.accept_panel_review(
        tmp_path, "第1话", data, jobs_path, "P001", "delegate:visual-agent",
        structured_review(job, "delegate:visual-agent", delegated=True),
    )
    manual = job["post_qc"]["manual_review"]
    assert status["accepted"] is True
    assert status["human_signoff"] is False
    assert manual["review_kind"] == "delegated_current_pixel_review"
    assert manual["authorization"]["stage"] == "panel_pixels"


def test_unapproved_delegate_cannot_accept_pixels(tmp_path: Path, monkeypatch) -> None:
    data, _job, jobs_path, _panel = _reviewable_job(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="not authorized"):
        runner.accept_panel_review(
            tmp_path, "第1话", data, jobs_path, "P001", "delegate:visual-agent", "reviewed"
        )


def test_deterministic_block_can_never_be_signed(tmp_path: Path, monkeypatch) -> None:
    data, job, jobs_path, _panel = _reviewable_job(tmp_path, monkeypatch, block=True)

    assert job["status"] == "qc_block"
    try:
        runner.accept_panel_review(tmp_path, "第1话", data, jobs_path, "P001", "reviewer-a", "accept")
    except ValueError as exc:
        assert "block/unverifiable" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("deterministic block must not be signable")


def test_acceptance_stales_after_pixel_or_comparison_input_changes(tmp_path: Path, monkeypatch) -> None:
    reference = tmp_path / "出图" / "共享" / "图片" / "CHAR_A__front.png"
    write_png(reference, color=(120, 30, 20))
    data, job, jobs_path, panel = _reviewable_job(tmp_path, monkeypatch)
    records = [{"id": "CHAR_A", "path": str(reference), "abs_path": str(reference), "role": "front"}]
    post_qc = runner.post_qc_panel(tmp_path, "第1话", job, panel, records, [])
    job.update({"status": "awaiting_review", "post_qc": post_qc})
    runner.write_json(jobs_path, data)
    runner.accept_panel_review(
        tmp_path, "第1话", data, jobs_path, "P001", "reviewer-a", structured_review(job, "reviewer-a")
    )
    assert runner.panel_acceptance_status(tmp_path, job)["accepted"]

    write_png(reference, color=(20, 130, 40))
    assert runner.panel_acceptance_status(tmp_path, job)["reason"] == "comparison_input_changed"
    write_png(panel, color=(10, 10, 10))
    assert runner.panel_acceptance_status(tmp_path, job)["reason"] == "job_artifact_sha_mismatch"


def test_prose_cannot_auto_confirm_all_visual_axes(tmp_path: Path, monkeypatch) -> None:
    data, _job, jobs_path, _panel = _reviewable_job(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="结构化逐轴结果"):
        runner.accept_panel_review(
            tmp_path, "第1话", data, jobs_path, "P001", "reviewer-a", "我看过了，全部通过"
        )


def test_previous_panels_are_selected_by_subject_or_scene_not_global_position(tmp_path: Path, monkeypatch) -> None:
    for pid in ("P001", "P002", "P003"):
        write_png(tmp_path / "出图" / "第1话" / "panels" / f"{pid}.png")
    jobs = [
        {"panel_id": "P001", "result_path": "出图/第1话/panels/P001.png",
         "identity_execution_contracts": [{"character_id": "CHAR_A"}],
         "continuity_contract": {"scene_anchor_id": "LOC_A"}},
        {"panel_id": "P002", "result_path": "出图/第1话/panels/P002.png",
         "identity_execution_contracts": [{"character_id": "CHAR_B"}],
         "continuity_contract": {"scene_anchor_id": "LOC_B"}},
        {"panel_id": "P003", "result_path": "出图/第1话/panels/P003.png",
         "identity_execution_contracts": [{"character_id": "CHAR_A"}],
         "continuity_contract": {"scene_anchor_id": "LOC_A", "continuity_from": "P001"}},
    ]
    monkeypatch.setattr(runner, "panel_acceptance_status", lambda _root, _job: {"accepted": True})
    selected = runner.previous_accepted_panel_paths(tmp_path, jobs, "P003")
    assert [path.stem for path in selected] == ["P001"]


def test_promotion_keeps_immutable_raw_and_pixel_metadata(tmp_path: Path) -> None:
    generated = tmp_path / "generated.png"
    write_png(generated, (120, 100))
    final = tmp_path / "出图" / "第1话" / "panels" / "P001.png"
    provenance = runner.promote_generated_artifacts(
        tmp_path, "第1话", "P001", generated, final,
        {"width": 60, "height": 50}, attempt=1, resize=True,
    )
    assert runner.png_valid(tmp_path / provenance["raw_candidate_path"])
    assert runner.png_valid(tmp_path / provenance["master_path"])
    assert runner.image_size(final) == (60, 50)
    assert [item["role"] for item in provenance["derivative_chain"]] == [
        "immutable_provider_raw", "active_master", "layout_panel"
    ]
    assert provenance["artifact_metadata"]["color_space"] == "sRGB_unprofiled"


def test_promotion_rolls_back_both_active_paths_on_partial_switch_failure(
    tmp_path: Path, monkeypatch
) -> None:
    generated = tmp_path / "generated.png"
    final = tmp_path / "出图" / "第1话" / "panels" / "P001.png"
    master = tmp_path / "出图" / "第1话" / "masters" / "P001.png"
    write_png(generated, color=(180, 40, 40))
    write_png(final, color=(20, 50, 80))
    write_png(master, color=(20, 50, 80))
    old_panel_sha = runner.file_sha256(final)
    old_master_sha = runner.file_sha256(master)
    original_replace = runner.os.replace
    failed = False

    def fail_panel_switch(source, target):
        nonlocal failed
        source_path = Path(source)
        target_path = Path(target)
        if not failed and source_path.name.endswith(".panel.png") and target_path == final:
            failed = True
            raise OSError("simulated derivative switch failure")
        return original_replace(source, target)

    monkeypatch.setattr(runner.os, "replace", fail_panel_switch)
    with pytest.raises(OSError, match="simulated"):
        runner.promote_generated_artifacts(
            tmp_path,
            "第1话",
            "P001",
            generated,
            final,
            {"width": 100, "height": 100},
            attempt=1,
            resize=True,
        )
    assert runner.file_sha256(final) == old_panel_sha
    assert runner.file_sha256(master) == old_master_sha


def test_write_json_is_atomic_and_valid(tmp_path):
    target = tmp_path / "nested" / "panel_jobs.json"
    runner.write_json(target, {"jobs": [{"panel_id": "P001", "status": "ready"}]})
    # valid JSON, trailing newline, no leftover temp files in the dir
    assert json.loads(target.read_text(encoding="utf-8"))["jobs"][0]["panel_id"] == "P001"
    leftovers = [p.name for p in target.parent.iterdir() if p.name != "panel_jobs.json"]
    assert leftovers == []


def test_write_json_overwrite_keeps_only_final(tmp_path):
    target = tmp_path / "panel_jobs.json"
    runner.write_json(target, {"v": 1})
    runner.write_json(target, {"v": 2})
    assert json.loads(target.read_text(encoding="utf-8"))["v"] == 2
    assert [p.name for p in tmp_path.iterdir()] == ["panel_jobs.json"]
