#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verifier_coverage 的 fail-closed 纪律测试。

锁的规矩：「适用 × 休眠 → 交付前阻断」——报告在但没真检 = 没检（机检空转必须 block）；
唯一逃生口是带人、带因、带 scope 的 degraded_qc_waiver；advisory 空转只 warn 不 block；
不适用的核验器如实入表但不产 finding。
"""
import json
import os
import time
from pathlib import Path

import verifier_coverage as vc


def _write_json(root: Path, rel: str, payload, mtime: float = None) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if mtime is not None:
        os.utime(path, (mtime, mtime))
    return path


def _by_code(report):
    out = {}
    for f in report["findings"]:
        out.setdefault(f["code"], []).append(f)
    return out


def _row(report, verifier):
    return next(r for r in report["coverage"] if r["verifier"] == verifier)


PAST = time.time() - 3600


def _seed_product_project(root: Path):
    """registry 登记 PROD_ + storyboard 绑产品镜（输入 mtime 押到过去，让侧车默认新鲜）。"""
    _write_json(root, "设定库/asset_registry.json",
                {"assets": {"PROD_bottle": {"desc": "瓶身"}}}, mtime=PAST)
    _write_json(root, "脚本/storyboard.json",
                {"shots": [{"shot_id": "镜头01", "assets": {"PROD_bottle": True}, "duration": 3},
                           {"shot_id": "镜头02", "assets": {}, "duration": 2}]}, mtime=PAST)


def _empty_run_product_qc():
    """product_qc 落了档、看似干净，但自述 product_shots=0——机检空转的标准形态。"""
    return {"kind": "ad_product_qc", "version": 2,
            "summary": {"block": 0, "warn": 0, "info": 1},
            "findings": [{"severity": "info", "shot": "-", "check": "prompt_lint",
                          "reason": "storyboard 无产品镜", "detail": {"product_shots": 0}}],
            "qc_environment": {"precision_level": "full", "pending_product_images": 0}}


def _effective_product_qc():
    return {"kind": "ad_product_qc", "version": 2,
            "summary": {"block": 0, "warn": 0, "info": 0}, "findings": [],
            "qc_environment": {"precision_level": "full", "pending_product_images": 0}}


def _valid_waiver(scope):
    return {"approved": True, "scope": scope, "reason": "打样期像素检依赖未装，人工并排复核",
            "signed_by": "导演"}


def test_empty_run_blocks(tmp_path):
    """registry 有 PROD_ 而 product_qc 自述 0 产品镜 → 空转 block（fail-closed 核心）。"""
    _seed_product_project(tmp_path)
    _write_json(tmp_path, "出图/分镜/product_qc.json", _empty_run_product_qc())

    report = vc.build(tmp_path)

    codes = _by_code(report)
    assert "verifier_empty_run" in codes
    assert codes["verifier_empty_run"][0]["severity"] == "block"
    assert _row(report, "product_qc")["status"] == "empty_run"
    assert report["summary"]["block"] >= 1


def test_pending_images_is_empty_run(tmp_path):
    _seed_product_project(tmp_path)
    payload = _effective_product_qc()
    payload["qc_environment"]["pending_product_images"] = 2
    _write_json(tmp_path, "出图/分镜/product_qc.json", payload)

    report = vc.build(tmp_path)

    assert _row(report, "product_qc")["status"] == "empty_run"


def test_valid_waiver_downgrades_to_warn_with_trace(tmp_path):
    """有效豁免（有人、有因、有 scope）把 block 降 warn，且留 waiver_active 痕。"""
    _seed_product_project(tmp_path)
    _write_json(tmp_path, "出图/分镜/product_qc.json", _empty_run_product_qc())
    _write_json(tmp_path, "合规/degraded_qc_waiver.json", _valid_waiver(["*"]))

    report = vc.build(tmp_path)

    codes = _by_code(report)
    assert codes["verifier_empty_run"][0]["severity"] == "warn"
    assert "waiver_active" in codes
    assert report["summary"]["block"] == 0


def test_invalid_waiver_is_ignored_and_reported(tmp_path):
    """缺 reason/signed_by 的豁免无效——忽略并 warn，block 照常（逃生口不允许含糊）。"""
    _seed_product_project(tmp_path)
    _write_json(tmp_path, "出图/分镜/product_qc.json", _empty_run_product_qc())
    _write_json(tmp_path, "合规/degraded_qc_waiver.json", {"approved": True, "scope": ["*"]})

    report = vc.build(tmp_path)

    codes = _by_code(report)
    assert "waiver_invalid" in codes
    assert codes["verifier_empty_run"][0]["severity"] == "block"


def test_waiver_scope_must_name_verifier(tmp_path):
    """scope 点名了别的核验器 → product_qc 的 block 不受影响。"""
    _seed_product_project(tmp_path)
    _write_json(tmp_path, "出图/分镜/product_qc.json", _empty_run_product_qc())
    _write_json(tmp_path, "合规/degraded_qc_waiver.json", _valid_waiver(["video_qc"]))

    report = vc.build(tmp_path)

    assert _by_code(report)["verifier_empty_run"][0]["severity"] == "block"


def test_not_applicable_rows_produce_no_findings(tmp_path):
    """空项目：所有核验器 not_applicable，如实入表、零 finding（没有对象不算休眠）。"""
    report = vc.build(tmp_path)

    assert report["summary"]["block"] == 0
    assert report["findings"] == []
    assert _row(report, "product_qc")["status"] == "not_applicable"
    assert _row(report, "product_qc")["applies"] is False


def test_dormant_hard_verifier_blocks(tmp_path):
    """适用（registry 有 PROD_）但 product_qc 侧车根本不存在 → dormant block。"""
    _seed_product_project(tmp_path)

    report = vc.build(tmp_path)

    codes = _by_code(report)
    assert codes["verifier_dormant"][0]["severity"] == "block"
    assert _row(report, "product_qc")["status"] == "dormant"


def test_stale_sidecar_blocks(tmp_path):
    """product_qc 早于新落的图 → stale block（干净但过期的报告不是证据）。"""
    _seed_product_project(tmp_path)
    _write_json(tmp_path, "出图/分镜/product_qc.json", _effective_product_qc(),
                mtime=time.time() - 100)
    img = tmp_path / "出图/分镜/图片/镜头01.png"
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(b"png")  # mtime = now，晚于侧车

    report = vc.build(tmp_path)

    codes = _by_code(report)
    assert any(f["verifier"] == "product_qc" for f in codes.get("verifier_stale", []))
    assert _row(report, "product_qc")["status"] == "stale"


def test_advisory_degraded_warns_never_blocks(tmp_path):
    """advisory 侧车 available=false 而输入齐备 → warn advisory_degraded，不 block。"""
    _write_json(tmp_path, "脚本/storyboard.json",
                {"shots": [{"shot_id": "镜头01", "duration": 3}]}, mtime=PAST)
    _write_json(tmp_path, "生产数据/ad_shot_variety_audit.json",
                {"kind": "ad_shot_variety_audit", "available": False,
                 "summary": {"block": 0, "warn": 1, "info": 0}, "findings": []})

    report = vc.build(tmp_path)

    codes = _by_code(report)
    hits = [f for f in codes.get("advisory_degraded", []) if f["verifier"] == "shot_variety"]
    assert hits and hits[0]["severity"] == "warn"
    assert all(f["severity"] != "block" or f["verifier"] != "shot_variety"
               for f in report["findings"])


def test_advisory_zero_shots_while_storyboard_has_shots(tmp_path):
    """advisory 报告自述审了 0 镜而 storyboard 有镜 → 空转 warn。"""
    _write_json(tmp_path, "脚本/storyboard.json",
                {"shots": [{"shot_id": "镜头01", "duration": 3}]}, mtime=PAST)
    _write_json(tmp_path, "生产数据/ad_shot_variety_audit.json",
                {"kind": "ad_shot_variety_audit", "available": True,
                 "inputs": {"shots": 0}, "summary": {"block": 0, "warn": 0, "info": 0},
                 "findings": []})

    report = vc.build(tmp_path)

    assert any(f["code"] == "advisory_degraded" and f["verifier"] == "shot_variety"
               for f in report["findings"])


def test_missing_advisory_sidecar_is_row_only(tmp_path):
    """缺席的 advisory 审计只记 dormant 行，不产 finding（gate 已有「建议先跑」info，别重复）。"""
    _write_json(tmp_path, "脚本/storyboard.json",
                {"shots": [{"shot_id": "镜头01", "duration": 3}]}, mtime=PAST)

    report = vc.build(tmp_path)

    assert _row(report, "shot_variety")["status"] == "dormant"
    assert not any(f.get("verifier") == "shot_variety" for f in report["findings"])


def test_p0_asset_all_noevidence_warns(tmp_path):
    """drift report 里 P0 资产全镜 noevidence → warn（noevidence ≠ ok）。"""
    _seed_product_project(tmp_path)
    _write_json(tmp_path, "出图/分镜/product_qc.json", _effective_product_qc())
    img = tmp_path / "出图/分镜/图片/镜头01.png"
    img.parent.mkdir(parents=True, exist_ok=True)
    img.write_bytes(b"png")
    os.utime(img, (PAST, PAST))
    _write_json(tmp_path, "生产数据/asset_consistency.json",
                {"summary": {"block": 0, "warn": 0, "info": 0}, "findings": []})
    _write_json(tmp_path, "生产数据/asset_drift_report.json",
                {"kind": "ad_asset_drift_report", "available": True,
                 "summary": {"block": 0, "warn": 0, "info": 0, "assets_tracked": 1},
                 "assets": [{"asset_id": "PROD_bottle", "critical": True,
                             "appeared_shots": ["镜头01"], "noevidence_shots": ["镜头01"],
                             "timeline": [{"shot": "镜头01", "status": "noevidence"}]}],
                 "findings": []})

    report = vc.build(tmp_path)

    assert any(f["code"] == "p0_asset_no_evidence" and f["severity"] == "warn"
               for f in report["findings"])


def test_clean_effective_project_no_block(tmp_path):
    """真跑过、够新鲜、有对象 → 0 block（账本不该在健康项目上叫）。"""
    _seed_product_project(tmp_path)
    _write_json(tmp_path, "出图/分镜/product_qc.json", _effective_product_qc())

    report = vc.build(tmp_path)

    assert report["summary"]["block"] == 0
    assert _row(report, "product_qc")["status"] == "ok"


def test_write_report_atomic(tmp_path):
    _seed_product_project(tmp_path)
    _write_json(tmp_path, "出图/分镜/product_qc.json", _effective_product_qc())
    report = vc.build(tmp_path)

    json_path, md_path = vc.write_report(tmp_path, report)

    assert json_path.is_file() and md_path.is_file()
    reloaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert reloaded["kind"] == "ad_verifier_coverage"
    assert "适用 × 休眠" in md_path.read_text(encoding="utf-8")
