from pathlib import Path
import importlib.util
import json


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
    assert {issue["category"] for issue in payload["issues"]} == {"resolution_lineage"}


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


def _reviewable_job(tmp_path: Path, monkeypatch, *, warning: bool = False, block: bool = False) -> tuple[dict, dict, Path, Path]:
    panel = tmp_path / "出图" / "第1话" / "panels" / "P001.png"
    write_png(panel)
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


def test_warn_never_auto_ready_but_named_review_can_accept(tmp_path: Path, monkeypatch) -> None:
    data, job, jobs_path, _panel = _reviewable_job(tmp_path, monkeypatch, warning=True)

    assert job["status"] == "qc_warn"
    assert not runner.panel_acceptance_status(tmp_path, job)["accepted"]
    accepted = runner.accept_panel_review(
        tmp_path, "第1话", data, jobs_path, "P001", "reviewer-a", "亮区是画内灯笼，不是空白气泡"
    )

    assert accepted["accepted"] is True
    assert job["status"] == "ready"
    assert job["post_qc"]["manual_review"]["verdict"] == "accepted_with_warnings"
    assert job["post_qc"]["manual_review"]["acknowledged_warnings"][0]["code"] == "baked_text_container"


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
    runner.accept_panel_review(tmp_path, "第1话", data, jobs_path, "P001", "reviewer-a", "逐轴复核通过")
    assert runner.panel_acceptance_status(tmp_path, job)["accepted"]

    write_png(reference, color=(20, 130, 40))
    assert runner.panel_acceptance_status(tmp_path, job)["reason"] == "comparison_input_changed"
    write_png(panel, color=(10, 10, 10))
    assert runner.panel_acceptance_status(tmp_path, job)["reason"] == "job_artifact_sha_mismatch"


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
