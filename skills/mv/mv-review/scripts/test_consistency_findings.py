from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("consistency_findings.py")
    spec = importlib.util.spec_from_file_location("mv_consistency_findings", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_mv_consistency_blocks_on_degraded_image_qc_and_inherit(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    write_json(root / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    write_json(root / "生产数据" / "image_qc" / "image_qc.json", {
        "summary": {"hard_blocks": 0, "advisory": 0},
        "qc_environment": {"precision_level": "degraded"},
    })
    write_json(root / "生产数据" / "video_inherit_contract" / "inherit_contract.json", {
        "summary": {"hard_blocks": 1, "warnings": 0},
    })
    write_json(root / "生产数据" / "video_qc" / "video_qc.json", {
        "summary": {"hard_blocks": 0, "warnings": 0},
        "seams": [],
    })

    report = mod.build_report(str(root))

    assert report["kind"] == "mv_consistency_findings"
    assert report["summary"]["block"] >= 2
    assert any(f["code"] == "image_qc_precision" for f in report["findings"])


def test_bound_manual_review_cannot_release_degraded_b14(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    write_json(root / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    report = {
        "summary": {"hard_blocks": 0, "advisory": 0},
        "qc_environment": {"precision_level": "degraded"},
    }
    import hashlib
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    report["manual_review"] = {"accepted": True, "reviewer": "审图人",
                               "bound_report_sha256": hashlib.sha256(encoded).hexdigest()}
    write_json(root / "生产数据" / "image_qc" / "image_qc.json", report)

    out = mod.build_report(str(root))
    hits = [f for f in out["findings"] if f["code"] == "image_qc_precision"]
    assert hits and hits[0]["severity"] == "block"
    assert "--accept-degraded" in hits[0]["message"] and "不能放行" in hits[0]["message"]
    assert not any(f["code"] == "image_qc_precision_manual" for f in out["findings"])


def test_legacy_boolean_manual_review_stays_block(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    write_json(root / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    write_json(root / "生产数据" / "image_qc" / "image_qc.json", {
        "summary": {"hard_blocks": 0, "advisory": 0},
        "qc_environment": {"precision_level": "degraded"},
        "manual_review_accepted": True,
    })
    out = mod.build_report(str(root))
    hits = [f for f in out["findings"] if f["code"] == "image_qc_precision"]
    assert hits and "不能放行 B14" in hits[0]["message"]


def test_current_full_qc_and_authoritative_b14_ledger_are_clean(tmp_path: Path) -> None:
    mod = load_module()
    receipts = mod._load_image_receipts()
    from PIL import Image

    root = tmp_path
    asset_rel = "出图/段落/图片/Clip_001.png"
    ref_rel = "设定/reference_images/lead.png"
    prompt_rel = "出图/段落/prompt/Clip_001.md"
    (root / prompt_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / prompt_rel).write_text("身份锚点与镜头描述", encoding="utf-8")
    (root / ref_rel).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), (10, 20, 30)).save(root / ref_rel)
    write_json(root / "分镜" / "clip_plan.json", {
        "kind": "mv_clip_plan",
        "clips": [{"clip_id": "Clip_001", "image_path": asset_rel,
                   "image_prompt_path": prompt_rel}],
    })
    receipts.create_preflight(
        root, asset=asset_rel, asset_kind="auto", owner="lead:主唱", use="clip_start",
        identity_scope="contains_identity", model="local:fixture-model", channel="local",
        prompt=prompt_rel, reference_specs=[f"{ref_rel}::lead:主唱::identity_anchor"],
    )
    (root / asset_rel).parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), (40, 50, 60)).save(root / asset_rel)
    receipts.record_submission(
        root, asset=asset_rel, model="local:fixture-model", channel="local",
        prompt=prompt_rel, references=[ref_rel],
    )
    current = receipts.load_ledger(root)["assets"][asset_rel]["current"]
    qc_rel = receipts.QC_REL.as_posix()
    qc = {
        "kind": "mv_image_qc",
        "version": 3,
        "summary": {"hard_blocks": 0, "advisory": 0, "verdict": "ok"},
        "assets_sha256": {asset_rel: receipts.sha256_path(root / asset_rel)},
        "qc_environment": {"precision_level": "full"},
        "asset_integrity": {"rows": [{"asset": asset_rel, "png": asset_rel, "verdict": "ok"}]},
        "checks": {
            "face": {"available": True, "mode": "insightface",
                     "shots": [{"asset": asset_rel, "png": asset_rel, "verdict": "ok"}]},
            "palette": {"available": True,
                        "shots": [{"asset": asset_rel, "png": asset_rel, "verdict": "ok"}]},
        },
        "shot_variety": {"available": True, "findings": []},
        "lint": {"available": True, "findings": []},
        "generation_provenance": {
            "complete": True, "uniform": True, "summary": {"block": 0},
            "rows": [{
                "asset": asset_rel, "verdict": "ok",
                "b14_attempt_id": current["attempt_id"],
                "b14_preflight_sha256": current["preflight"]["receipt_sha256"],
                "b14_submission_sha256": current["submission"]["receipt_sha256"],
            }],
        },
        "prohibited_local_patch_outputs": {"outputs": []},
    }
    write_json(root / qc_rel, qc)
    result = receipts.record_postflight(
        root, asset=asset_rel, qc_report=qc_rel, reviewer="审图人",
        visual_verdict="pass", notes="逐图与当前参考并排核对后通过",
    )
    assert result["accepted"] is True

    report = mod.build_report(str(root))
    image_codes = {f["code"] for f in report["findings"] if f["dimension"] == "visual_identity"}
    assert "image_qc_clean" in image_codes
    assert not any(
        f["severity"] == "block" and f["dimension"] == "visual_identity"
        for f in report["findings"]
    )


def test_consistency_timing_blocks_old_or_pending_alignment_receipt(tmp_path: Path) -> None:
    mod = load_module()
    write_json(tmp_path / "字幕" / "alignment_report.json", {
        "kind": "mv_lyric_alignment_report",
        "schema_version": 5,
        "alignment_confidence": 0.99,
        "coverage_metric": "text_character_mapping_ratio_not_acoustic_confidence",
        "character_coverage_ratio": 1.0,
        "acceptance": {"status": "pending", "accepted": False},
    })
    findings: list[dict] = []
    mod.timing_checks(findings, str(tmp_path))
    assert any(f["severity"] == "block" and "禁止 alignment_confidence" in f["message"]
               for f in findings)
    assert any(f["severity"] == "block" and "尚未正式接受" in f["message"]
               for f in findings)


def test_consistency_timing_blocks_missing_alignment_for_formal_subtitles(tmp_path: Path) -> None:
    mod = load_module()
    write_json(tmp_path / "_meta.json", {"is_demo": False})
    (tmp_path / "_设置.md").write_text(
        "# 设置\n\n- 字幕语言：中文\n- 演唱口型：关闭\n", encoding="utf-8",
    )
    findings: list[dict] = []
    mod.timing_checks(findings, str(tmp_path))
    assert any(
        row["severity"] == "block" and row["code"] == "alignment_missing"
        for row in findings
    )


def test_production_stats_flags_high_redraw_and_takes(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    events = root / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    # 2 资产，其中 1 个抽了 3 次 → 重画率 50% > 35%
    for asset, count in (("出图/a.png", 3), ("出图/b.png", 1)):
        for _ in range(count):
            rows.append(json.dumps({"stage": "image", "event": "generation",
                                    "generation": {"asset": asset}}, ensure_ascii=False))
    events.write_text("\n".join(rows) + "\n", encoding="utf-8")
    write_json(root / "出视频" / "jobs_manifest.json", {
        "jobs": [{"clip_id": "Clip_01", "takes": [{}, {}, {}, {}, {}]},
                 {"clip_id": "Clip_02", "takes": [{}, {}, {}]}],
    })
    findings: list[dict] = []
    mod.production_stats(findings, str(root))
    codes = {f["code"] for f in findings}
    assert "image_redraw_rate_high" in codes
    assert "takes_per_clip_high" in codes


def test_drift_risk_aggregated(tmp_path: Path) -> None:
    mod = load_module()
    write_json(tmp_path / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    report = mod.build_report(str(tmp_path))
    assert any(f["code"] == "drift_risk_missing" for f in report["findings"])
    write_json(tmp_path / "生产数据" / "drift_risk" / "drift_risk.json",
               {"summary": {"high": 3, "measured_backfilled": 1}})
    report = mod.build_report(str(tmp_path))
    hit = next(f for f in report["findings"] if f["code"] == "drift_risk_high")
    assert hit["severity"] == "warn"


def test_verifier_coverage_flags_dormant_face_stack(tmp_path: Path) -> None:
    mod = load_module()
    write_json(tmp_path / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    write_json(tmp_path / "设定" / "identity_registry.json", {"lead_id": "CHAR_lead"})
    # image_qc 存在但脸检降级 Pillow、dHash 没跑 → 适用但休眠
    write_json(tmp_path / "生产数据" / "image_qc" / "image_qc.json", {
        "summary": {"hard_blocks": 0, "advisory": 0},
        "qc_environment": {"precision_level": "degraded"},
        "checks": {"face": {"available": True, "mode": "pillow_basic"},
                   "palette": {"available": True}},
        "shot_variety": {"available": False},
    })
    report = mod.build_report(str(tmp_path))
    hit = next(f for f in report["findings"] if f["code"] == "reality_verifier_dormant")
    assert hit["severity"] == "warn"
    dormant_keys = {r["key"] for r in hit["detail"]["rows"] if r["dormant"]}
    assert "image_face" in dormant_keys and "image_composition_dhash" in dormant_keys
    # video_qc 脸检真跑过 + 抽帧有样本 → 不休眠
    write_json(tmp_path / "生产数据" / "video_qc" / "video_qc.json", {
        "summary": {"hard_blocks": 0, "warnings": 0, "face_identity_mode": "insightface",
                    "frame_samples": 9},
        "seams": [],
    })
    report = mod.build_report(str(tmp_path))
    hit = next(f for f in report["findings"] if f["code"] == "reality_verifier_dormant")
    rows = {r["key"]: r for r in hit["detail"]["rows"]}
    assert rows["video_face"]["ran_fresh"] and not rows["video_face"]["dormant"]
    assert rows["video_frame_perception"]["ran_fresh"]


def test_verifier_coverage_all_active_is_info(tmp_path: Path) -> None:
    mod = load_module()
    write_json(tmp_path / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    write_json(tmp_path / "设定" / "identity_registry.json", {"lead_id": "CHAR_lead"})
    write_json(tmp_path / "生产数据" / "image_qc" / "image_qc.json", {
        "summary": {"hard_blocks": 0, "advisory": 0},
        "qc_environment": {"precision_level": "full"},
        "checks": {"face": {"available": True, "mode": "insightface"},
                   "palette": {"available": True}},
        "shot_variety": {"available": True},
    })
    report = mod.build_report(str(tmp_path))
    assert any(f["code"] == "reality_verifiers_active" for f in report["findings"])
    assert not any(f["code"] == "reality_verifier_dormant" for f in report["findings"])


def test_production_stats_quiet_when_healthy(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    events = root / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text(json.dumps({"stage": "image", "event": "generation",
                                  "generation": {"asset": "出图/a.png"}}) + "\n", encoding="utf-8")
    write_json(root / "出视频" / "jobs_manifest.json",
               {"jobs": [{"clip_id": "Clip_01", "takes": [{}]}]})
    findings: list[dict] = []
    mod.production_stats(findings, str(root))
    assert all(f["severity"] == "info" for f in findings)
    assert {f["code"] for f in findings} == {"image_redraw_rate", "takes_per_clip"}
