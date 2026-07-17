import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asset_drift_report as adr  # noqa: E402


def make_root(tmp_path, storyboard=None, product_qc=None, asset_consistency=None, registry=None):
    root = tmp_path / "ad"
    (root / "脚本").mkdir(parents=True)
    if storyboard is not None:
        (root / "脚本" / "storyboard.json").write_text(
            json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    if registry is not None:
        (root / "设定库").mkdir(parents=True, exist_ok=True)
        (root / "设定库" / "asset_registry.json").write_text(
            json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    if product_qc is not None:
        (root / "出图" / "分镜").mkdir(parents=True, exist_ok=True)
        (root / "出图" / "分镜" / "product_qc.json").write_text(
            json.dumps(product_qc, ensure_ascii=False), encoding="utf-8")
    if asset_consistency is not None:
        (root / "生产数据").mkdir(parents=True, exist_ok=True)
        (root / "生产数据" / "asset_consistency.json").write_text(
            json.dumps(asset_consistency, ensure_ascii=False), encoding="utf-8")
    return root


def three_product_shots():
    return {"shots": [
        {"shot_id": "S1", "assets": {"PROD_CAN": True, "CHAR_HOST": True}},
        {"shot_id": "S2", "assets": {"PROD_CAN": True, "CHAR_HOST": True}},
        {"shot_id": "S3", "assets": {"PROD_CAN": True, "CHAR_HOST": True}},
    ]}


def registry_all():
    return {"products": [{"id": "PROD_CAN"}], "characters": [{"id": "CHAR_HOST"}]}


def by_id(payload, asset_id):
    return next(row for row in payload["assets"] if row["asset_id"] == asset_id)


# ── 产品资产跨镜连崩 → 高优先级建议 ────────────────────────────────────────────

def test_product_asset_repeated_drift_gets_p0_reground_recommendation(tmp_path):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 2, "warn": 0, "info": 0}, "findings": [
            {"severity": "block", "shot": "镜头02", "check": "brand_color", "reason": "ΔE 18 偏色", "detail": {}},
            {"severity": "block", "shot": "镜头03", "check": "product_dhash", "reason": "包装异图", "detail": {}},
        ]},
    )
    payload = adr.build(root)

    prod = by_id(payload, "PROD_CAN")
    assert prod["critical"] is True
    assert prod["bad_shot_count"] == 2
    assert prod["bad_shots"] == ["镜头02", "镜头03"]
    assert prod["priority"] == "P0"
    assert prod["action"] == "reground_registry"
    assert "定妆" in prod["recommendation"] and "registry" in prod["recommendation"]
    assert "整片报废风险" in prod["recommendation"]

    drift = [f for f in payload["findings"]
             if f["code"] == "asset_cross_shot_drift" and f["asset"] == "PROD_CAN"]
    assert len(drift) == 1
    assert drift[0]["severity"] == "warn"  # advisory：绝不 block
    assert drift[0]["detail"]["priority"] == "P0"
    assert drift[0]["detail"]["evidence_severity"] == "block"


def test_single_shot_drift_only_reruns_that_shot(tmp_path):
    root = make_root(
        tmp_path,
        storyboard={"shots": [
            {"shot_id": "S1", "assets": ["CHAR_HOST"]},
            {"shot_id": "S2", "assets": ["CHAR_HOST"]},
        ]},
        registry={"characters": [{"id": "CHAR_HOST"}]},
        asset_consistency={"summary": {"block": 0, "warn": 1}, "findings": [
            {"severity": "warn", "code": "cross_shot_visual_drift", "asset_id": "CHAR_HOST",
             "shot": "镜头02", "msg": "脸漂"},
        ]},
    )
    row = by_id(adr.build(root), "CHAR_HOST")
    assert row["bad_shot_count"] == 1
    assert row["priority"] == "P2"
    assert row["action"] == "rerun_shot"
    assert "先不升重资产" in row["recommendation"]


def test_non_product_multi_shot_drift_is_p1_reground(tmp_path):
    root = make_root(
        tmp_path,
        storyboard={"shots": [
            {"shot_id": "S1", "assets": ["CHAR_HOST"]},
            {"shot_id": "S2", "assets": ["CHAR_HOST"]},
        ]},
        registry={"characters": [{"id": "CHAR_HOST"}]},
        asset_consistency={"summary": {"block": 0, "warn": 2}, "findings": [
            {"severity": "warn", "code": "cross_shot_visual_drift", "asset_id": "CHAR_HOST",
             "shot": "镜头01", "msg": "脸漂"},
            {"severity": "warn", "code": "cross_shot_visual_drift", "asset_id": "CHAR_HOST",
             "shot": "镜头02", "msg": "脸漂"},
        ]},
    )
    row = by_id(adr.build(root), "CHAR_HOST")
    assert row["priority"] == "P1"
    assert row["action"] == "reground_registry"


# ── first_bad_shot 正确 ───────────────────────────────────────────────────────

def test_first_bad_shot_is_earliest_in_storyboard_order(tmp_path):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 0, "warn": 2, "info": 0}, "findings": [
            # 刻意乱序写入，报表必须按 storyboard 镜序判首崩
            {"severity": "warn", "shot": "镜头03", "check": "brand_color", "reason": "偏色", "detail": {}},
            {"severity": "warn", "shot": "镜头02", "check": "brand_color", "reason": "偏色", "detail": {}},
        ]},
    )
    prod = by_id(adr.build(root), "PROD_CAN")
    assert prod["first_bad_shot"] == "镜头02"
    assert [t["shot"] for t in prod["timeline"]] == ["镜头01", "镜头02", "镜头03"]


def test_first_bad_shot_is_none_when_clean(tmp_path):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 0, "warn": 0, "info": 3}, "findings": [
            {"severity": "info", "shot": f"镜头0{n}", "check": "brand_color",
             "reason": "ok", "detail": {}} for n in (1, 2, 3)
        ]},
    )
    prod = by_id(adr.build(root), "PROD_CAN")
    assert prod["first_bad_shot"] is None
    assert prod["bad_shot_count"] == 0
    assert prod["priority"] is None
    assert [t["status"] for t in prod["timeline"]] == ["ok", "ok", "ok"]


# ── noevidence ≠ ok ──────────────────────────────────────────────────────────

def test_no_evidence_shot_is_not_ok(tmp_path):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 0, "warn": 0, "info": 1}, "findings": [
            {"severity": "info", "shot": "镜头01", "check": "brand_color", "reason": "ok", "detail": {}},
        ]},
    )
    payload = adr.build(root)
    prod = by_id(payload, "PROD_CAN")
    status = {t["shot"]: t["status"] for t in prod["timeline"]}
    assert status["镜头01"] == "ok"
    assert status["镜头02"] == "noevidence"
    assert status["镜头03"] == "noevidence"
    # 缺证据既不算通过，也不算漂移
    assert prod["noevidence_shots"] == ["镜头02", "镜头03"]
    assert prod["bad_shot_count"] == 0
    noev = [f for f in payload["findings"]
            if f["code"] == "asset_shot_no_evidence" and f["asset"] == "PROD_CAN"]
    assert len(noev) == 1 and noev[0]["severity"] == "info"
    assert "缺证据不算通过" in noev[0]["msg"]


def test_no_upstream_reports_means_all_noevidence_not_all_ok(tmp_path):
    root = make_root(tmp_path, storyboard=three_product_shots(), registry=registry_all())
    payload = adr.build(root)
    assert payload["available"] is True
    prod = by_id(payload, "PROD_CAN")
    assert {t["status"] for t in prod["timeline"]} == {"noevidence"}
    assert payload["summary"]["shots_with_evidence"] == 0
    assert any("product_qc" in note for note in payload["notes"])


# ── 缺 storyboard 降级不崩 ────────────────────────────────────────────────────

def test_missing_storyboard_degrades_without_crashing(tmp_path):
    root = make_root(tmp_path)
    payload = adr.build(root)
    assert payload["available"] is False
    assert payload["degraded"] == "no_asset_universe"
    assert payload["assets"] == []
    assert payload["findings"] == []
    assert payload["summary"]["block"] == 0
    assert payload["notes"]


def test_malformed_storyboard_degrades_without_crashing(tmp_path):
    root = make_root(tmp_path, storyboard={"shots": "not-a-list"})
    payload = adr.build(root)
    assert payload["available"] is False
    assert payload["summary"]["assets_tracked"] == 0


def test_storyboard_without_assets_degrades(tmp_path):
    root = make_root(tmp_path, storyboard={"shots": [{"shot_id": "S1"}, {"shot_id": "S2"}]})
    payload = adr.build(root)
    assert payload["available"] is False


def test_corrupt_upstream_report_is_tolerated(tmp_path):
    root = make_root(tmp_path, storyboard=three_product_shots(), registry=registry_all())
    (root / "出图" / "分镜").mkdir(parents=True, exist_ok=True)
    (root / "出图" / "分镜" / "product_qc.json").write_text("{ broken json", encoding="utf-8")
    payload = adr.build(root)
    assert payload["available"] is True
    assert by_id(payload, "PROD_CAN")["timeline"][0]["status"] == "noevidence"


# ── registry ─────────────────────────────────────────────────────────────────

def test_registry_fallback_to_shared_dir_and_unregistered_asset_warns(tmp_path):
    root = make_root(tmp_path, storyboard=three_product_shots())
    (root / "出图" / "共享").mkdir(parents=True, exist_ok=True)
    (root / "出图" / "共享" / "asset_registry.json").write_text(
        json.dumps({"characters": [{"id": "CHAR_HOST"}]}, ensure_ascii=False), encoding="utf-8")
    payload = adr.build(root)
    assert by_id(payload, "CHAR_HOST")["registered"] is True
    assert by_id(payload, "PROD_CAN")["registered"] is False
    unreg = [f for f in payload["findings"] if f["code"] == "asset_not_in_registry"]
    assert [f["asset"] for f in unreg] == ["PROD_CAN"]
    assert "出图/共享/asset_registry.json" in payload["sources"]


# ── build() 契约形状 ─────────────────────────────────────────────────────────

def test_build_contract_shape(tmp_path):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 1, "warn": 0, "info": 0}, "findings": [
            {"severity": "block", "shot": "镜头02", "check": "logo", "reason": "logo 缺失", "detail": {}},
        ]},
    )
    payload = adr.build(root)

    assert payload["schema_version"] == 1
    assert payload["kind"] == "ad_asset_drift_report"
    assert isinstance(payload["generated_at"], str) and payload["generated_at"]
    assert payload["available"] is True
    assert isinstance(payload["assets"], list) and isinstance(payload["findings"], list)
    for key in ("block", "warn", "info"):
        assert isinstance(payload["summary"][key], int)

    for row in payload["assets"]:
        for key in ("asset_id", "timeline", "first_bad_shot", "bad_shot_count", "worst_check"):
            assert key in row
        for entry in row["timeline"]:
            assert set(entry) == {"shot", "status", "checks"}
            assert entry["status"] in {"ok", "warn", "block", "noevidence"}
            assert isinstance(entry["checks"], list)

    for item in payload["findings"]:
        assert item["severity"] in {"warn", "info"}  # 契约：绝不产 block
        assert item["msg"] and item["message"] == item["msg"]
        assert item["code"] and "asset" in item and "shot" in item

    # summary.block 恒 0：本报表是审不是门
    assert payload["summary"]["block"] == 0
    # 上游证据的 block 仍如实记录在时间线与 summary 的证据字段里
    assert by_id(payload, "PROD_CAN")["timeline"][1]["status"] == "block"
    assert payload["summary"]["assets_with_block_evidence"] >= 1


def test_findings_never_block_even_with_all_block_evidence(tmp_path):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 3, "warn": 0, "info": 0}, "findings": [
            {"severity": "block", "shot": f"镜头0{n}", "check": "brand_color",
             "reason": "崩", "detail": {}} for n in (1, 2, 3)
        ]},
    )
    payload = adr.build(root)
    assert payload["summary"]["block"] == 0
    assert all(f["severity"] != "block" for f in payload["findings"])


def test_finding_helper_downgrades_block(tmp_path):
    item = adr.finding("block", "x", "m")
    assert item["severity"] == "warn"
    assert item["msg"] == "m" and item["message"] == "m"


# ── 归位规则 ─────────────────────────────────────────────────────────────────

def test_shot_finding_attributes_to_named_asset_only(tmp_path):
    item = {"severity": "warn", "shot": "镜头01", "check": "asset_bindings",
            "reason": "PROD_CAN 未绑定参考图", "detail": {}}
    assert adr.attribute_shot_finding(item, ["PROD_CAN", "CHAR_HOST"]) == ["PROD_CAN"]


def test_shot_finding_without_named_asset_falls_back_to_critical_assets(tmp_path):
    item = {"severity": "warn", "shot": "镜头01", "check": "brand_color",
            "reason": "偏色", "detail": {}}
    assert adr.attribute_shot_finding(item, ["PROD_CAN", "CHAR_HOST"]) == ["PROD_CAN"]


def test_shot_finding_falls_back_to_all_assets_when_no_critical(tmp_path):
    item = {"severity": "warn", "shot": "镜头01", "check": "safe_area", "reason": "越界", "detail": {}}
    assert adr.attribute_shot_finding(item, ["CHAR_HOST", "LOC_STUDIO"]) == ["CHAR_HOST", "LOC_STUDIO"]


def test_asset_level_finding_without_shot_does_not_mark_shots_bad(tmp_path):
    root = make_root(
        tmp_path,
        storyboard={"shots": [
            {"shot_id": "S1", "assets": ["CHAR_HOST"]},
            {"shot_id": "S2", "assets": ["CHAR_HOST"]},
        ]},
        registry={"characters": [{"id": "CHAR_HOST"}]},
        asset_consistency={"summary": {"block": 0, "warn": 1}, "findings": [
            # asset_consistency 的跨镜 warn 不带 shot——不能据此把每一镜都判崩
            {"severity": "warn", "code": "cross_shot_visual_drift",
             "asset_id": "CHAR_HOST", "msg": "dHash 最大差 42bit"},
        ]},
    )
    row = by_id(adr.build(root), "CHAR_HOST")
    assert row["bad_shot_count"] == 0
    assert {t["status"] for t in row["timeline"]} == {"noevidence"}
    assert row["asset_checks"] and row["asset_checks"][0]["check"] == "cross_shot_visual_drift"
    assert row["worst_check"] == "cross_shot_visual_drift"


# ── CLI ──────────────────────────────────────────────────────────────────────

def test_cli_default_exit_zero_even_with_block_evidence(tmp_path, capsys):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 2, "warn": 0, "info": 0}, "findings": [
            {"severity": "block", "shot": "镜头02", "check": "brand_color", "reason": "崩", "detail": {}},
            {"severity": "block", "shot": "镜头03", "check": "brand_color", "reason": "崩", "detail": {}},
        ]},
    )
    assert adr.main([str(root)]) == 0
    assert "广告跨镜资产漂移报表" in capsys.readouterr().out


def test_cli_strict_exits_one_on_warn(tmp_path, capsys):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 0, "warn": 1, "info": 0}, "findings": [
            {"severity": "warn", "shot": "镜头02", "check": "brand_color", "reason": "偏色", "detail": {}},
        ]},
    )
    assert adr.main([str(root), "--strict", "--json"]) == 1
    capsys.readouterr()


def test_cli_strict_exits_zero_when_clean(tmp_path, capsys):
    root = make_root(
        tmp_path,
        storyboard=three_product_shots(),
        registry=registry_all(),
        product_qc={"summary": {"block": 0, "warn": 0, "info": 3}, "findings": [
            {"severity": "info", "shot": f"镜头0{n}", "check": "brand_color", "reason": "ok", "detail": {}}
            for n in (1, 2, 3)
        ]},
    )
    # 全部镜有证据且通过、资产已登记 → 无 warn/info finding
    assert adr.main([str(root), "--strict"]) == 0
    capsys.readouterr()


def test_cli_write_emits_json_and_md(tmp_path, capsys):
    root = make_root(tmp_path, storyboard=three_product_shots(), registry=registry_all())
    assert adr.main([str(root), "--write"]) == 0
    capsys.readouterr()
    out_json = root / "生产数据" / "asset_drift_report.json"
    out_md = root / "生产数据" / "asset_drift_report.md"
    assert out_json.is_file() and out_md.is_file()
    assert json.loads(out_json.read_text(encoding="utf-8"))["kind"] == "ad_asset_drift_report"
    assert "PROD_CAN" in out_md.read_text(encoding="utf-8")
    # 原子写不留 .tmp 残渣
    assert not list((root / "生产数据").glob("*.tmp"))


def test_cli_missing_root_returns_two(tmp_path, capsys):
    assert adr.main([str(tmp_path / "nope")]) == 2
    capsys.readouterr()
