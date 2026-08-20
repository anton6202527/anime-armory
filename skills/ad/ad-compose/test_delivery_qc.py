# -*- coding: utf-8 -*-
"""delivery_qc·textless 无字版母版纪律单测。

行规：带烧录文字或多语言再版的成片必须配 textless 母版，否则每个语言版都要回炉重做 online。
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delivery_qc as dq  # noqa: E402


def test_measure_loudness_executes_ffmpeg_and_parses_metrics(tmp_path, monkeypatch):
    media = tmp_path / "master.mp4"
    media.write_bytes(b"media")
    monkeypatch.setattr(dq.shutil, "which", lambda name: "/usr/bin/ffmpeg" if name == "ffmpeg" else None)
    monkeypatch.setattr(dq.subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(
        args[0], 0, "", '{"input_i":"-16.1","input_tp":"-1.2","input_lra":"4.0"}',
    ))

    result = dq.measure_loudness(media)

    assert result == {"integrated_lufs": -16.1, "true_peak_db": -1.2, "lra": 4.0}


def test_compose_consumes_render_profile_instead_of_hardcoded_1080p30():
    text = Path(__file__).with_name("compose.sh").read_text(encoding="utf-8")
    assert "render_profile.py" in text
    assert "fps=${FPS}" in text
    assert "fps=30" not in text
    assert "--src 1920x1080" not in text
    cutdown = Path(__file__).with_name("cutdown.py").read_text(encoding="utf-8")
    assert "render_profile.json" in cutdown
    assert "fps=30" not in cutdown


def _root(tmp_path, *, burned=0, locales=0):
    root = tmp_path / "ad"
    (root / "合规").mkdir(parents=True)
    if burned:
        (root / "合规" / "rendered_text_plan.json").write_text(json.dumps({
            "checks": [{"id": f"master:{i}", "text": "法律声明"} for i in range(burned)],
        }, ensure_ascii=False), encoding="utf-8")
    if locales:
        (root / "合规" / "locale_matrix.json").write_text(json.dumps({
            "locales": {f"loc{i}": {"language": f"l{i}"} for i in range(locales)},
        }, ensure_ascii=False), encoding="utf-8")
    return root


def _plan(*ids):
    return {"deliverables": [{"deliverable_id": i} for i in ids]}


def test_burned_text_without_textless_master_warns(tmp_path):
    root = _root(tmp_path, burned=3)
    findings = dq.textless_master_findings(root, _plan("master", "reframe_9x16"))

    assert len(findings) == 1
    assert findings[0]["code"] == "textless_master_missing"
    assert findings[0]["severity"] == "warn"


def test_multi_locale_without_textless_master_warns(tmp_path):
    root = _root(tmp_path, locales=3)
    assert dq.textless_master_findings(root, _plan("master"))


def test_textless_deliverable_or_no_trigger_is_quiet(tmp_path):
    root = _root(tmp_path, burned=2, locales=3)
    # 任意字段（id/kind/label/path）带 textless/无字 都算已交
    assert not dq.textless_master_findings(root, _plan("master", "master_textless"))
    assert not dq.textless_master_findings(
        root, {"deliverables": [{"deliverable_id": "m2", "label": "无字版母版"}]})

    # 没烧字 + 单语言：不要求
    quiet = _root(tmp_path / "b", locales=1)
    assert not dq.textless_master_findings(quiet, _plan("master"))
    # 空交付计划不判（其它检查管缺计划）
    assert not dq.textless_master_findings(root, {"deliverables": []})


def _profile_root(tmp_path, *, native=False):
    root = tmp_path / "profile-ad"
    (root / "生产数据").mkdir(parents=True)
    profile = {
        "kind": "ad_render_profile",
        "profile_sha256": "profile-current",
        "source_generation": {
            "width": 1280, "height": 720, "resolution": "1280x720",
            "effective_source_resolution": "1280x720", "fps": 24, "aspect": "16:9",
        },
        "master_render": {
            "width": 1920, "height": 1080, "resolution": "1920x1080", "fps": 24,
            "aspect": "16:9", "authority": [{"source": "客户/版位规格"}],
        },
        "upscale": {
            "required": True, "policy": "forbid" if native else "warn",
            "native_resolution_required": native,
            "effective_source_resolution": "1280x720", "container_resolution": "1920x1080",
        },
    }
    (root / "生产数据" / "render_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    item = {"aspect": "16:9", "render_profile": {
        "path": "生产数据/render_profile.json", "sha256": "profile-current",
    }}
    return root, item


def test_container_upscale_is_reported_without_claiming_native_detail(tmp_path):
    root, item = _profile_root(tmp_path)

    findings, evidence = dq.render_profile_findings(root, item, 1920, 1080, 24.0)

    row = next(f for f in findings if f["code"] == "container_upscale_only")
    assert row["severity"] == "warn"
    assert row["detail"]["effective_source_resolution"] == "1280x720"
    assert evidence["target_resolution"] == "1920x1080"


def test_native_resolution_requirement_blocks_container_upscale(tmp_path):
    root, item = _profile_root(tmp_path, native=True)

    findings, _ = dq.render_profile_findings(root, item, 1920, 1080, 24.0)

    assert any(f["code"] == "native_resolution_required_but_upscaled" and f["severity"] == "block"
               for f in findings)


def test_render_profile_detects_stale_plan_and_wrong_fps(tmp_path):
    root, item = _profile_root(tmp_path)
    item["render_profile"]["sha256"] = "old-profile"

    findings, _ = dq.render_profile_findings(root, item, 1920, 1080, 30.0)
    codes = {f["code"] for f in findings}

    assert "render_profile_stale" in codes
    assert "render_profile_fps_mismatch" in codes


def test_blocked_adaptation_cannot_pass_existing_media_qc(tmp_path):
    item = {"deliverable_id": "reframe_9x16", "placement_adaptation": {
        "status": "blocked", "selected_mode": None,
        "findings": [{"severity": "block", "code": "adaptation_mode_missing"}],
    }}

    findings = dq.placement_adaptation_findings(tmp_path, item)

    assert {row["code"] for row in findings} >= {
        "placement_adaptation_not_approved", "placement_adaptation_has_block",
    }


def test_adaptation_evidence_bytes_change_makes_delivery_plan_stale(tmp_path):
    evidence = tmp_path / "证据" / "focus.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b"current-focus-plan")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    item = {"deliverable_id": "reframe_9x16", "placement_adaptation": {
        "status": "approved", "selected_mode": "mechanical_reframe", "findings": [],
        "evidence": {"focus_plan": {"path": "证据/focus.json", "sha256": digest}},
    }}
    assert not dq.placement_adaptation_findings(tmp_path, item)

    evidence.write_bytes(b"changed-after-approval")
    findings = dq.placement_adaptation_findings(tmp_path, item)

    assert any(row["code"] == "placement_adaptation_evidence_stale" for row in findings)


def test_delivery_plan_block_is_carried_into_qc_even_without_media(tmp_path):
    report = dq.build_report(tmp_path, {"summary": {"block": 1}, "deliverables": []})
    assert report["summary"]["block"] == 1
    assert report["findings"][0]["code"] == "delivery_plan_prerequisites_blocked"


def test_render_profile_rejects_tampered_payload_and_changed_inputs(tmp_path):
    root = tmp_path / "ad"
    (root / "生产数据").mkdir(parents=True)
    (root / "需求").mkdir()
    (root / "_设置.md").write_text("- 视频分辨率: 720p\n", encoding="utf-8")
    (root / "需求" / "brief.json").write_text("{}\n", encoding="utf-8")
    pack = {"schema_version": 3, "kind": "ad_platform_pack", "summary": {"block": 0}}
    (root / "生产数据" / "platform_pack.json").write_text(
        json.dumps(pack, ensure_ascii=False), encoding="utf-8")

    def file_sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def logical_sha(payload):
        return hashlib.sha256(json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()

    profile = {
        "schema_version": 1, "kind": "ad_render_profile",
        "source_generation": {"width": 1280, "height": 720, "fps": 24, "aspect": "16:9"},
        "master_render": {"width": 1280, "height": 720, "fps": 24, "aspect": "16:9"},
        "input_sha256": {
            "_设置.md": file_sha(root / "_设置.md"),
            "需求/brief.json": file_sha(root / "需求" / "brief.json"),
            "生产数据/platform_pack.json": logical_sha(pack),
        },
    }
    profile["profile_sha256"] = logical_sha(profile)
    (root / "生产数据" / "render_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    item = {"render_profile": {"path": "生产数据/render_profile.json",
                                "sha256": profile["profile_sha256"]}}
    _, findings = dq._load_render_profile(root, item)
    assert not findings

    (root / "需求" / "brief.json").write_text('{"changed": true}\n', encoding="utf-8")
    profile["master_render"]["fps"] = 30
    (root / "生产数据" / "render_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    _, findings = dq._load_render_profile(root, item)
    codes = {row["code"] for row in findings}
    assert "render_profile_digest_invalid" in codes
    assert "render_profile_input_stale" in codes


def test_schema5_missing_or_malformed_render_profile_fails_closed(tmp_path):
    item = {"_delivery_plan_schema_version": 5}
    _, findings = dq._load_render_profile(tmp_path, item)
    assert {row["code"] for row in findings} == {"render_profile_ref_missing"}

    (tmp_path / "生产数据").mkdir()
    (tmp_path / "生产数据" / "render_profile.json").write_text(
        json.dumps({"profile_sha256": "claimed"}), encoding="utf-8")
    item["render_profile"] = {"path": "生产数据/render_profile.json", "sha256": "claimed"}
    _, findings = dq._load_render_profile(tmp_path, item)
    codes = {row["code"] for row in findings}
    assert "render_profile_schema_invalid" in codes
    assert "render_profile_structure_invalid" in codes


def test_schema5_profile_self_rehash_cannot_replace_live_semantic_compile(tmp_path):
    root = tmp_path / "ad"
    (root / "需求").mkdir(parents=True)
    (root / "需求" / "brief.json").write_text("{}\n", encoding="utf-8")
    (root / "_设置.md").write_text(
        "- 出视频规格: 预算充足\n- 视频分辨率: 720p\n- 交付比例: 16:9\n",
        encoding="utf-8",
    )
    profile = dq.ad_render_profile.write_profile(root)
    stored = json.loads((root / "生产数据" / "render_profile.json").read_text(encoding="utf-8"))
    stored["source_generation"].update({"width": 640, "height": 360, "resolution": "640x360"})
    stored["master_render"].update({"width": 640, "height": 360, "resolution": "640x360"})
    stored["upscale"].update({
        "required": False, "effective_source_resolution": "640x360",
        "container_resolution": "640x360", "scale_factor": 1.0,
        "quality_claim": "native_source_sufficient",
    })
    stored["profile_sha256"] = dq.canonical_sha({
        key: value for key, value in stored.items() if key != "profile_sha256"
    })
    (root / "生产数据" / "render_profile.json").write_text(
        json.dumps(stored, ensure_ascii=False), encoding="utf-8")
    item = {
        "_delivery_plan_schema_version": 5,
        "render_profile": {"path": "生产数据/render_profile.json", "sha256": stored["profile_sha256"]},
    }

    _, findings = dq._load_render_profile(root, item)

    assert profile["profile_sha256"] != stored["profile_sha256"]
    assert "render_profile_semantic_stale" in {row["code"] for row in findings}


def test_variant_native_requirement_blocks_global_container_upscale_allowance(tmp_path, monkeypatch):
    root, item = _profile_root(tmp_path, native=False)
    item["platform_constraints"] = [{"native_resolution_required": True}]
    monkeypatch.setattr(dq, "_actual_clip_resolutions", lambda _root: [{
        "path": "出视频/分镜/视频/S1.mp4", "width": 1280, "height": 720,
        "resolution": "1280x720", "fps": 24.0,
    }])

    findings, _ = dq.render_profile_findings(root, item, 1920, 1080, 24.0)

    assert any(row["code"] == "native_resolution_required_but_upscaled"
               and row["severity"] == "block" for row in findings)


def test_required_resolution_label_is_enforced_per_placement(tmp_path, monkeypatch):
    root, item = _profile_root(tmp_path, native=False)
    item["platform_constraints"] = [{
        "native_resolution_required": True, "required_resolution": "1080p",
    }]
    monkeypatch.setattr(dq, "_actual_clip_resolutions", lambda _root: [{
        "path": "出视频/分镜/视频/S1.mp4", "width": 1280, "height": 720,
        "resolution": "1280x720", "fps": 24.0,
    }])

    findings, _ = dq.render_profile_findings(root, item, 1920, 1080, 24.0)

    assert "effective_source_below_placement_requirement" in {row["code"] for row in findings}


def test_native_delivery_blocks_when_effective_source_is_unverified(tmp_path, monkeypatch):
    root, item = _profile_root(tmp_path, native=False)
    item["platform_constraints"] = [{"native_resolution_required": True}]
    monkeypatch.setattr(dq, "_actual_clip_resolutions", lambda _root: [])

    findings, _ = dq.render_profile_findings(root, item, 1920, 1080, 24.0)

    assert any(row["code"] == "effective_source_unverified" and row["severity"] == "block"
               for row in findings)


def test_cross_ratio_delivery_requires_execution_receipt_and_rejects_mode_mismatch(tmp_path):
    root = tmp_path
    output = root / "合成" / "多比例" / "成片_9x16.mp4"
    source = root / "合成" / "成片_主片.mp4"
    output.parent.mkdir(parents=True)
    source.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b"vertical-output")
    source.write_bytes(b"master-input")
    adaptation = {
        "deliverable_id": "reframe_9x16", "kind": "reframe", "status": "approved",
        "selected_mode": "native_reedit", "findings": [], "evidence": {},
    }
    item = {
        "deliverable_id": "reframe_9x16", "kind": "reframe",
        "expected_path": "合成/多比例/成片_9x16.mp4",
        "render_profile": {"sha256": "profile-current"},
        "placement_adaptation": adaptation,
    }
    missing = dq.placement_adaptation_findings(root, item)
    assert "adaptation_execution_receipt_missing" in {row["code"] for row in missing}

    plan = {
        "schema_version": 1, "kind": "ad_placement_adaptation_plan",
        "project_root": str(root), "items": [adaptation], "summary": {"block": 0, "approved": True},
        "findings": [],
    }
    plan["plan_sha256"] = dq.adaptation_plan_sha(plan)
    (root / "生产数据").mkdir(exist_ok=True)
    (root / "生产数据" / "placement_adaptation.json").write_text(
        json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    receipt = {
        "schema_version": 1, "kind": "ad_placement_adaptation_execution_receipt",
        "deliverable_id": "reframe_9x16", "actual_mode": "mechanical_reframe",
        "selected_mode": "native_reedit", "executed_by": "测试执行人",
        "inputs": [{"path": "合成/成片_主片.mp4", "sha256": dq._sha256_file(source)}],
        "output": {"path": "合成/多比例/成片_9x16.mp4", "sha256": dq._sha256_file(output)},
        "adaptation_plan_sha256": plan["plan_sha256"],
        "adaptation_item_sha256": dq.adaptation_item_sha(adaptation),
        "render_profile_sha256": "profile-current", "note": "forged mechanical path",
    }
    receipt["receipt_sha256"] = dq.canonical_sha(receipt)
    receipt_path = root / "生产数据" / "placement_adaptation_receipts" / "reframe_9x16.json"
    receipt_path.parent.mkdir()
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")

    findings = dq.placement_adaptation_findings(root, item)
    assert "adaptation_execution_mode_mismatch" in {row["code"] for row in findings}


def test_native_execution_receipt_must_consume_shot_plan_sources(tmp_path):
    root = tmp_path
    master = root / "合成" / "成片_主片.mp4"
    output = root / "合成" / "多比例" / "成片_9x16.mp4"
    native = root / "出视频" / "分镜" / "视频" / "竖版镜头01.mp4"
    for path, data in ((master, b"master"), (output, b"vertical"), (native, b"native-shot")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    adaptation = {
        "deliverable_id": "reframe_9x16", "kind": "reframe", "status": "approved",
        "selected_mode": "native_reedit", "findings": [],
        "evidence": {"native_sources": [{
            "path": "出视频/分镜/视频/竖版镜头01.mp4", "sha256": dq._sha256_file(native),
        }]},
    }
    item = {
        "deliverable_id": "reframe_9x16", "kind": "reframe",
        "expected_path": "合成/多比例/成片_9x16.mp4",
        "render_profile": {"sha256": "profile-current"},
        "placement_adaptation": adaptation,
    }
    plan = {
        "schema_version": 1, "kind": "ad_placement_adaptation_plan",
        "project_root": str(root), "items": [adaptation],
        "summary": {"block": 0, "approved": True}, "findings": [],
    }
    plan["plan_sha256"] = dq.adaptation_plan_sha(plan)
    (root / "生产数据").mkdir(exist_ok=True)
    (root / "生产数据" / "placement_adaptation.json").write_text(
        json.dumps(plan, ensure_ascii=False), encoding="utf-8")
    receipt = {
        "schema_version": 1, "kind": "ad_placement_adaptation_execution_receipt",
        "deliverable_id": "reframe_9x16", "actual_mode": "native_reedit",
        "selected_mode": "native_reedit", "executed_by": "测试执行人",
        "inputs": [{"path": "合成/成片_主片.mp4", "sha256": dq._sha256_file(master)}],
        "output": {"path": "合成/多比例/成片_9x16.mp4", "sha256": dq._sha256_file(output)},
        "adaptation_plan_sha256": plan["plan_sha256"],
        "adaptation_item_sha256": dq.adaptation_item_sha(adaptation),
        "render_profile_sha256": "profile-current", "note": "自报原生重剪",
    }
    receipt["receipt_sha256"] = dq.canonical_sha(receipt)
    receipt_path = root / "生产数据" / "placement_adaptation_receipts" / "reframe_9x16.json"
    receipt_path.parent.mkdir()
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False), encoding="utf-8")

    findings = dq.placement_adaptation_findings(root, item)

    assert "adaptation_execution_native_source_mismatch" in {row["code"] for row in findings}
