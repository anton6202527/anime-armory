from pathlib import Path
import importlib.util
import json


MODULE = Path(__file__).with_name("supervisor.py")
SPEC = importlib.util.spec_from_file_location("comic_supervisor_tested", MODULE)
assert SPEC and SPEC.loader
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)


def test_missing_contract_bootstraps_only_from_explicit_settings(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text(
        "- 交付介质: print_pdf\n- 交付用途: commercial\n- 目标平台: 通用\n",
        encoding="utf-8",
    )
    contract = supervisor.ensure_active_release_contract(tmp_path, "第1话")
    assert contract["medium"] == "print_pdf"
    assert contract["usage"] == "commercial"
    assert contract["release_digest"] == ""
    assert contract["settings_binding"]["sha256"] == supervisor.RELEASE.sha256_file(tmp_path / "_设置.md")
    stored = json.loads(
        (tmp_path / "生产数据" / "release_contract_第1话.json").read_text(encoding="utf-8")
    )
    assert stored == contract


def test_missing_or_invalid_delivery_setting_fails_closed(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 目标平台: 通用\n", encoding="utf-8")
    action = supervisor.decide_next_action(tmp_path, "第1话")
    assert action["action"] == "invalid_active_delivery_settings"
    assert action["hard_boundary"] is True
    assert "交付介质" in action["reason"]

    (tmp_path / "_设置.md").write_text(
        "- 交付介质: mystery\n- 交付用途: internal\n- 目标平台: 通用\n",
        encoding="utf-8",
    )
    action = supervisor.decide_next_action(tmp_path, "第1话")
    assert action["action"] == "invalid_active_delivery_settings"
    assert "mystery" in action["reason"]


def test_explicit_axis_change_reboots_pointer_without_reusing_old_digest(tmp_path: Path) -> None:
    settings = tmp_path / "_设置.md"
    settings.write_text(
        "- 交付介质: web_images\n- 交付用途: internal\n- 目标平台: 通用\n",
        encoding="utf-8",
    )
    path = tmp_path / "生产数据" / "release_contract_第1话.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({
        "kind": "comic_active_release_contract", "medium": "web_images", "usage": "internal",
        "target_platform": "通用", "release_digest": "a" * 64,
    }), encoding="utf-8")
    settings.write_text(
        "- 交付介质: print_pdf\n- 交付用途: public\n- 目标平台: 通用\n",
        encoding="utf-8",
    )
    contract = supervisor.ensure_active_release_contract(tmp_path, "第1话")
    assert contract["release_digest"] == ""
    assert contract["previous_release_digest"] == "a" * 64
    assert (contract["medium"], contract["usage"]) == ("print_pdf", "public")


def test_complete_branch_refuses_missing_or_corrupt_active_bundle(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "_设置.md").write_text(
        "- 交付介质: web_images\n- 交付用途: internal\n- 目标平台: 通用\n",
        encoding="utf-8",
    )
    report = {
        "chapter": "第1话", "medium": "web_images", "usage": "internal",
        "target_platform": "通用", "verdict": "pass", "issues": [], "artifacts": [],
    }
    digest = supervisor.RELEASE.canonical_release_digest(report)
    monkeypatch.setattr(
        supervisor.BATCH,
        "next_action",
        lambda _root, _chapter: {"status": "runnable", "action": "build_completion_verdict"},
    )
    monkeypatch.setattr(supervisor.RELEASE, "build", lambda *_args, **_kwargs: report)
    monkeypatch.setattr(
        supervisor.RELEASE,
        "build_completion_verdict",
        lambda _root, _report: {"release_digest": digest, "status": "accepted"},
    )
    completion_path = tmp_path / "生产数据" / "completion_verdict_第1话.json"
    completion_path.parent.mkdir(parents=True, exist_ok=True)
    completion_path.write_text(json.dumps({
        "kind": "comic_completion_verdict", "release_digest": digest,
        "release_inputs_fingerprint": digest, "status": "accepted",
    }), encoding="utf-8")

    missing = supervisor.decide_next_action(tmp_path, "第1话")
    assert missing["action"] == "refresh_active_release_verdict"
    assert missing["completion_current"] is False
    assert any("bundle" in issue for issue in missing["completion_issues"])

    bundle = tmp_path / "生产数据" / "releases" / "第1话" / digest / "release_verdict.json"
    bundle.parent.mkdir(parents=True, exist_ok=True)
    bundle.write_text(json.dumps(report), encoding="utf-8")
    contract_path = tmp_path / "生产数据" / "release_contract_第1话.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract.update({
        "schema_version": 3, "release_digest": digest,
        "bundle_path": str(bundle.relative_to(tmp_path)), "bundle_sha256": "0" * 64,
        "completion_path": str(completion_path.relative_to(tmp_path)),
        "completion_sha256": supervisor.RELEASE.sha256_file(completion_path),
    })
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    corrupt = supervisor.decide_next_action(tmp_path, "第1话")
    assert corrupt["action"] == "refresh_active_release_verdict"
    assert corrupt["completion_current"] is False
    assert any("bundle SHA" in issue for issue in corrupt["completion_issues"])
