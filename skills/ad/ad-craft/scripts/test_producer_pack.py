import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import producer_pack as pp  # noqa: E402


def _project(tmp_path: Path, storyboard_assets=None) -> Path:
    root = tmp_path / "广告项目"
    (root / "需求").mkdir(parents=True)
    (root / "创意").mkdir()
    (root / "脚本").mkdir()
    (root / "需求" / "brief.json").write_text(json.dumps({
        "brand": "星盒",
        "product": "星盒手账 App",
        "usp": ["整理语音照片待办"],
        "audience": "学生和自由职业者",
        "key_message": "把今天稳稳收好",
        "mandatories": {"legal_lines": []},
        "claims": [{
            "id": "claim_01", "claim": "支持整理为草稿", "evidence_type": "brand_fact",
            "evidence": "产品功能设定", "evidence_file": "证据/产品功能说明.md",
            "method": "与当前产品版本逐项核对", "date": "2026-07-11",
            "territory": "中国大陆", "approved_by": "产品负责人甲",
        }],
        "rights": {
            "talent": {"status": "not_used", "territory": "全球", "media_scope": "all deliverables", "approved_by": "制片甲"},
            "music": {"status": "licensed", "evidence_file": "证据/music-license.pdf", "territory": "全球",
                      "media_scope": "paid digital ad", "validity": "2026 campaign", "valid_from": "2026-01-01",
                      "valid_until": "2026-12-31", "approved_by": "制片甲"},
            "fonts": {"status": "owned", "evidence_file": "证据/font-license.pdf", "territory": "全球",
                      "media_scope": "all deliverables", "validity": "perpetual", "approved_by": "设计甲"},
            "assets": {"status": "owned", "evidence_file": "证据/assets.md", "territory": "全球",
                       "media_scope": "all deliverables", "validity": "project-owned", "approved_by": "制片甲"},
        },
        "deliverables": {"master_duration": "30s", "aspect": "9:16", "cutdowns": ["15s", "6s"]},
        "platforms": ["抖音", "小红书"],
    }, ensure_ascii=False), encoding="utf-8")
    (root / "创意" / "concept.md").write_text("## Big Idea\n\n把一天收进盒子。\n", encoding="utf-8")
    (root / "证据").mkdir()
    (root / "证据" / "产品功能说明.md").write_text("current product capability", encoding="utf-8")
    for name in ("music-license.pdf", "font-license.pdf", "assets.md"):
        (root / "证据" / name).write_bytes(b"rights evidence")
    (root / "脚本" / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "C01", "duration": 4, "scene": "夜晚桌面", "shot": "俯拍推近", "assets": storyboard_assets or {}},
        ]
    }, ensure_ascii=False), encoding="utf-8")
    return root


def test_build_pack_flags_missing_product_and_brand_bindings(tmp_path):
    root = _project(tmp_path)
    pack = pp.build_pack(root)

    assert pack["summary"]["shots"] == 1
    codes = {row["code"] for row in pack["asset_gaps"]}
    assert "missing_product_asset_binding" in codes
    assert "missing_brand_asset_binding" in codes
    assert pack["summary"]["approval_blocks"] >= 1
    assert any(row["code"] == "approval_pending_mandatories.legal_lines" for row in pack["approval_checklist"])


def test_build_pack_accepts_structured_assets(tmp_path):
    root = _project(tmp_path, {"PROD_STARBOX_APP": True, "BRAND_STARBOX": True})
    pack = pp.build_pack(root)

    assert pack["summary"]["asset_blocks"] == 0
    assert pack["summary"]["asset_warns"] == 0
    assert pack["shot_list"][0]["asset_ids"]["product"] == ["PROD_STARBOX_APP"]
    assert pack["shot_list"][0]["asset_ids"]["brand"] == ["BRAND_STARBOX"]


def test_build_pack_does_not_treat_plain_product_brand_words_as_asset_ids(tmp_path):
    root = _project(tmp_path)
    (root / "脚本" / "storyboard.json").write_text(json.dumps({
        "clips": [
            {"id": "C01", "duration": 4, "scene": "product hero with brand color", "shot": "phone UI"},
        ]
    }, ensure_ascii=False), encoding="utf-8")

    pack = pp.build_pack(root)

    assert pack["shot_list"][0]["asset_ids"]["product"] == []
    assert pack["shot_list"][0]["asset_ids"]["brand"] == []
    assert any(row["code"] == "missing_product_asset_binding" for row in pack["asset_gaps"])


def test_build_pack_treats_pending_words_inside_rights_detail_as_pending(tmp_path):
    root = _project(tmp_path, {"PROD_STARBOX_APP": True, "BRAND_STARBOX": True})
    brief_path = root / "需求" / "brief.json"
    brief = json.loads(brief_path.read_text(encoding="utf-8"))
    brief["rights"]["music"]["valid_until"] = "待补"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False), encoding="utf-8")
    pack = pp.build_pack(root)

    assert any(row["code"] == "approval_pending_music" for row in pack["approval_checklist"])


def test_parse_settings_accepts_markdown_bullets(tmp_path):
    path = tmp_path / "_设置.md"
    path.write_text("- 发行地区: 中国大陆  # 中国大陆 | 北美\n- 交付规格: 平台默认\n", encoding="utf-8")

    settings = pp.parse_settings(path)

    assert settings["发行地区"] == "中国大陆"
    assert settings["交付规格"] == "平台默认"


def test_write_pack_outputs_json_and_md(tmp_path):
    root = _project(tmp_path, {"PROD_STARBOX_APP": True})
    pack = pp.write_pack(root)

    assert Path(pack["_json_path"]).is_file()
    assert Path(pack["_md_path"]).is_file()
    disk = json.loads(Path(pack["_json_path"]).read_text(encoding="utf-8"))
    assert disk["kind"] == pp.PACK_KIND


def test_cited_test_claim_requires_issuer_conditions_scope_and_display_source(tmp_path):
    brief = {"claims": [{
        "claim": "测试提升 20%", "evidence_type": "test_measurement", "evidence": "测试报告",
        "evidence_file": "证据/report.pdf", "method": "A/B", "date": "2026-07-01",
        "territory": "中国大陆", "approved_by": "法务甲",
    }]}
    rows = pp.claims_check(brief)
    assert rows[0]["status"] == "pending"
    assert {"source_name", "applicable_scope", "validity", "display_disclosure",
            "issuer", "issuer_qualification", "method_standard", "test_conditions", "sample"} <= set(rows[0]["missing_fields"])


def test_complete_statistical_claim_has_queryable_source_and_conditional_evidence(tmp_path):
    evidence = tmp_path / "survey.pdf"
    evidence.write_bytes(b"survey")
    brief = {"claims": [{
        "id": "claim_survey", "claim": "72% 受访者更偏好", "evidence_type": "statistics_survey",
        "evidence": "独立调研", "evidence_file": "survey.pdf", "method": "分层抽样",
        "date": "2026-07-01", "territory": "中国大陆", "approved_by": "法务甲",
        "source_name": "某独立研究机构", "source_locator": "survey.pdf",
        "applicable_scope": "18-35 岁样本", "validity": "2026Q3", "display_disclosure": "来源：某机构 2026Q2 调研",
        "statistical_method": "分层随机抽样", "sample_size": 1200, "sample_definition": "六城市 18-35 岁消费者",
        "representativeness": "按城市和年龄加权", "survey_period": "2026-04 至 2026-06",
        "bias_limitations": "不代表全体人口",
    }]}
    row = pp.claims_check(brief, tmp_path)[0]
    assert row["status"] == "approved"
    assert row["source_queryable"] is True


def test_legacy_rights_string_no_longer_counts_as_release_evidence():
    row = pp.rights_check({"rights": {"music": "授权曲库"}})
    music = next(v for v in row if v["category"] == "music")
    assert music["status"] == "pending"
    assert "structured_rights_record" in music["missing_fields"]


def test_expired_license_is_blocked(tmp_path):
    evidence = tmp_path / "license.pdf"
    evidence.write_bytes(b"license")
    rows = pp.rights_check({"rights": {"music": {
        "status": "licensed", "evidence_file": "license.pdf", "territory": "全球",
        "media_scope": "paid ad", "validity": "fixed term", "valid_from": "2020-01-01",
        "valid_until": "2020-12-31", "approved_by": "制片甲",
    }}}, tmp_path)
    music = next(v for v in rows if v["category"] == "music")
    assert "license_expired" in music["missing_fields"]
