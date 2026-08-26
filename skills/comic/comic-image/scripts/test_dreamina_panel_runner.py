from pathlib import Path
import importlib.util
import json


MODULE_PATH = Path(__file__).with_name("dreamina_panel_runner.py")
SPEC = importlib.util.spec_from_file_location("comic_dreamina_panel_runner", MODULE_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_nearest_supported_ratio() -> None:
    assert runner.nearest_supported_ratio({"width": 1296, "height": 1040}) == "4:3"
    assert runner.nearest_supported_ratio({"width": 1080, "height": 620}) == "16:9"
    assert runner.nearest_supported_ratio({"width": 1296, "height": 1232}) == "1:1"


def test_normalize_panel_outputs_exact_size(tmp_path: Path) -> None:
    from PIL import Image

    source = tmp_path / "source.png"
    target = tmp_path / "target.png"
    Image.new("RGB", (1600, 1200), (30, 40, 50)).save(source)

    result = runner.normalize_panel(source, target, {"width": 1296, "height": 1040})

    assert Image.open(target).size == (1296, 1040)
    assert result["source_size"] == {"width": 1600, "height": 1200}
    assert result["target_size"] == {"width": 1296, "height": 1040}
    assert result["upscaled"] is False
    assert result["normalization_scale"] < 1.0


def test_extra_required_view_can_be_omitted_when_subject_is_represented() -> None:
    selected = [
        {"id": "CHAR_HONG_XIN", "role": "front", "required": True},
        {"id": "STYLE_SHUIHU", "role": "style", "required": True},
    ]
    omitted = [
        {"id": "CHAR_HONG_XIN", "role": "face", "required": True},
        {"id": "PROP_SILVER_CENSER", "role": "prop", "required": True},
    ]

    assert runner.unrepresented_required_ids(selected, omitted) == {"PROP_SILVER_CENSER"}


def test_build_prompt_accepts_dreamina_compiled_job() -> None:
    submit_prompt = (
        "生成一张铺满画布的单格无字漫画画面。"
        "画面事实：黎明中的北宋宫城与紫宸殿在薄雾中显现。"
        "画风与稿层：宋画工笔淡彩、国漫写实人物、低饱和矿物色彩色完成稿。"
    )
    identity_contracts: list[dict] = []
    identity_sha = runner.hashlib.sha256(
        json.dumps(identity_contracts, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    material = {
        "submit_prompt_sha256": runner.hashlib.sha256(submit_prompt.encode("utf-8")).hexdigest(),
        "size": {"width": 1296, "height": 1040},
        "references": [],
        "character_bindings": [],
        "panel_plan_sha256": "",
        "identity_contracts_sha256": identity_sha,
    }
    execution_hash = runner.hashlib.sha256(
        json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    job = {
        "panel_id": "P001",
        "size": material["size"],
        "prompt_source_kind": "compiled_submit_prompt",
        "prompt_compiler": {
            "kind": runner.shared.COMPILER_KIND,
            "version": runner.shared.COMPILER_VERSION,
            "profile_version": "test",
            "profile": "zh_comic_reference_first",
            "backend": "dreamina",
            "language": "zh",
        },
        "submit_prompt": submit_prompt,
        "prompt": submit_prompt,
        "negative_prompt": "",
        "source_contract_sha256": "a" * 64,
        "submit_prompt_sha256": material["submit_prompt_sha256"],
        "execution_input_sha256": execution_hash,
        "execution_input": material,
        "identity_execution_contracts": identity_contracts,
        "identity_execution_contracts_sha256": identity_sha,
        "consumed_contracts": {"reference_plan": {"panel_plan_sha256": ""}},
        "references": [],
        "character_bindings": [],
    }

    prompt = runner.build_prompt(job, [], "4:3", correction="卷轴表面保持纯色，不生成任何字符。")

    assert "Dreamina" not in prompt
    assert "1296x1040" in prompt
    assert submit_prompt in prompt
    assert "卷轴表面保持纯色" in prompt

    concise = runner.build_concise_recovery_prompt(
        job,
        [],
        "4:3",
        correction="只保留一张病榻。",
        fact_override="北宋宫城在晨雾中显现。",
    )
    assert "核心画面事实：北宋宫城在晨雾中显现" in concise
    assert "只保留一张病榻" in concise
    assert len(concise) < len(prompt)


def test_reconcile_reuses_durable_submit_id_without_resubmit(tmp_path: Path) -> None:
    job = {
        "panel_id": "P001",
        "execution_input_sha256": "a" * 64,
        "source_contract_sha256": "b" * 64,
        "submit_prompt_sha256": "c" * 64,
    }
    data = {"model": runner.DREAMINA_MODEL, "channel": runner.DREAMINA_CHANNEL, "jobs": [job]}
    jobs_path = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    runner.shared.write_json(jobs_path, data)
    spend = runner.shared.spend_envelope
    scope = spend.requested_scope("第1话", ["P001"], force=False)
    envelope = spend.issue_envelope(
        tmp_path, chapter="第1话", data=data, model=runner.DREAMINA_MODEL,
        channel=runner.DREAMINA_CHANNEL, scope=scope,
        expires_at="2099-01-01T00:00:00Z", max_calls=1, max_attempts=1,
        currency="CNY", max_total="10", max_cost_per_call="10",
        approver="Wesley Chen", approval_reference="chat://comic/1",
        source_quote="批准本话这一格在十元预算内生成一次。",
    )
    envelope_path = spend.default_envelope_path(tmp_path, "第1话")
    spend.save_envelope(envelope_path, envelope)
    context = {
        "root": tmp_path, "chapter": "第1话", "force": False,
        "model": runner.DREAMINA_MODEL, "channel": runner.DREAMINA_CHANNEL,
        "envelope_path": envelope_path, "actual_cost": "8",
        "data_input_sha256": spend.panel_jobs_input_sha256(data, "第1话"),
    }
    submits: list[str] = []
    raw = tmp_path / "candidate.png"
    first = runner.recoverable_paid_submission(
        context, jobs_path=jobs_path, data=data, job=job, panel_id="P001",
        retry_round=1, raw_output=raw,
        submitter=lambda: submits.append("called") or ("provider-123", ""),
        poller=lambda _sid: ("polling", "not ready"),
    )
    assert first["status"] == "polling"
    assert submits == ["called"]
    reloaded = runner.shared.load_json(jobs_path)
    resumed_job = reloaded["jobs"][0]
    second = runner.recoverable_paid_submission(
        context, jobs_path=jobs_path, data=reloaded, job=resumed_job, panel_id="P001",
        retry_round=1, raw_output=raw,
        submitter=lambda: (_ for _ in ()).throw(AssertionError("must not resubmit")),
        poller=lambda sid: ("downloaded", "") if sid == "provider-123" else ("hard_failed", "bad id"),
    )
    assert second["status"] == "downloaded"
    assert resumed_job["provider_execution"]["state"] == "settled"
    assert resumed_job["provider_execution"]["submit_id"] == "provider-123"
    record = spend.submission_record(
        envelope_path, tmp_path,
        consumption_id=resumed_job["provider_execution"]["consumption_id"],
    )
    assert record["status"] == "settled"
    assert record["provider_state"] == "downloaded"


def test_reconcile_settles_downloaded_crash_window_without_poll_or_resubmit(tmp_path: Path) -> None:
    job = {
        "panel_id": "P001",
        "execution_input_sha256": "a" * 64,
        "source_contract_sha256": "b" * 64,
        "submit_prompt_sha256": "c" * 64,
    }
    data = {"model": runner.DREAMINA_MODEL, "channel": runner.DREAMINA_CHANNEL, "jobs": [job]}
    jobs_path = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    runner.shared.write_json(jobs_path, data)
    spend = runner.shared.spend_envelope
    scope = spend.requested_scope("第1话", ["P001"], force=False)
    envelope = spend.issue_envelope(
        tmp_path,
        chapter="第1话",
        data=data,
        model=runner.DREAMINA_MODEL,
        channel=runner.DREAMINA_CHANNEL,
        scope=scope,
        expires_at="2099-01-01T00:00:00Z",
        max_calls=1,
        max_attempts=1,
        currency="CNY",
        max_total="10",
        max_cost_per_call="10",
        approver="Wesley Chen",
        approval_reference="chat://comic/1",
        source_quote="批准本话这一格在十元预算内生成一次。",
    )
    envelope_path = spend.default_envelope_path(tmp_path, "第1话")
    spend.save_envelope(envelope_path, envelope)
    context = {
        "root": tmp_path,
        "chapter": "第1话",
        "force": False,
        "model": runner.DREAMINA_MODEL,
        "channel": runner.DREAMINA_CHANNEL,
        "envelope_path": envelope_path,
        "actual_cost": "8",
        "data_input_sha256": spend.panel_jobs_input_sha256(data, "第1话"),
    }
    consumption_id = "comic-image-crash-window"
    attempt_id = "第1话:comic-image:retry-round:1"
    spend.reserve_submission(
        envelope_path,
        tmp_path,
        stage=spend.STAGE,
        input_sha256=context["data_input_sha256"],
        model=runner.DREAMINA_MODEL,
        channel=runner.DREAMINA_CHANNEL,
        scope=scope,
        consumption_id=consumption_id,
        attempt_id=attempt_id,
    )
    spend.mark_provider_state(
        envelope_path,
        tmp_path,
        consumption_id=consumption_id,
        state="submitted",
        provider_submit_id="provider-123",
    )
    spend.mark_provider_state(
        envelope_path,
        tmp_path,
        consumption_id=consumption_id,
        state="polling",
        provider_submit_id="provider-123",
    )
    spend.mark_provider_state(
        envelope_path,
        tmp_path,
        consumption_id=consumption_id,
        state="downloaded",
        provider_submit_id="provider-123",
    )
    raw = tmp_path / "candidate.png"
    raw.write_bytes(b"downloaded provider payload")
    job["provider_execution"] = {
        "state": "polling",
        "submit_id": "provider-123",
        "consumption_id": consumption_id,
        "attempt_id": attempt_id,
        "execution_input_sha256": job["execution_input_sha256"],
        "raw_output": str(raw.relative_to(tmp_path)),
    }
    runner.shared.write_json(jobs_path, data)

    outcome = runner.recoverable_paid_submission(
        context,
        jobs_path=jobs_path,
        data=data,
        job=job,
        panel_id="P001",
        retry_round=1,
        raw_output=raw,
        submitter=lambda: (_ for _ in ()).throw(AssertionError("must not resubmit")),
        poller=lambda _sid: (_ for _ in ()).throw(AssertionError("downloaded state must not regress to polling")),
    )

    assert outcome["status"] == "downloaded"
    assert job["provider_execution"]["state"] == "settled"
    assert job["provider_execution"]["recovered_from_ledger"] is True
    record = spend.submission_record(envelope_path, tmp_path, consumption_id=consumption_id)
    assert record["status"] == "settled"
    assert record["provider_state"] == "downloaded"
