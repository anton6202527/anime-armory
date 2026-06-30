"""consistency_ledger 纯函数单测（无 I/O）。
cd skills/n2d-review/scripts && python -m pytest test_consistency_ledger.py
"""
import consistency_ledger as cl
import json


def test_worse_and_band_to_sev():
    assert cl.worse("warn", "ok") == "warn"
    assert cl.worse("high", "block") == "block"
    assert cl.worse("ok", "ok") == "ok"
    assert cl.band_to_sev("high") == "high"
    assert cl.band_to_sev("medium") == "medium"
    assert cl.band_to_sev("low") == "ok"
    assert cl.band_to_sev(None) == "ok"


def test_name_tokens_splits_aliases():
    assert cl.name_tokens("沈念 / 林婉儿") == ["沈念", "林婉儿"]
    assert cl.name_tokens("断魂剑") == ["断魂剑"]


def test_attribute_routes_to_detect_and_contract():
    rows = [{"id": "CHAR_01", "name_tokens": ["沈念"]},
            {"id": "PROP_01", "name_tokens": ["铜镜"]}]
    findings = [
        {"sev": "warn", "source": "detect", "text": "锚点门 沈念 box_ratio 低"},
        {"sev": "warn", "source": "contract", "text": "Clip_04 asset_handoff_dropped PROP_01(铜镜)"},
        {"sev": "block", "source": "detect", "text": "无关镜头无实体名"},  # 未归属
    ]
    st = cl.attribute(rows, findings)
    assert st["CHAR_01"]["detect"] == "warn" and st["CHAR_01"]["contract"] == "ok"
    assert st["PROP_01"]["contract"] == "warn" and st["PROP_01"]["detect"] == "ok"
    assert any("无关镜头" in u for u in st["_unattributed"])


def test_build_ledger_overall_is_worst_of_three():
    led = cl.build_ledger(
        characters=[{"id": "CHAR_01", "name": "沈念"}],
        assets=[{"id": "PROP_01", "name": "铜镜", "type": "prop"}],
        face_drift={"CHAR_01": "high"},
        asset_drift={"PROP_01": "low"},
        findings=[{"sev": "warn", "source": "contract", "text": "PROP_01 铜镜 dropped"}],
        dependency_graph={"kind": "n2d_consistency_dependency_graph", "summary": {"nodes": 2, "edges": 1}},
        discontinuity_audit={"kind": "n2d_intentional_discontinuity_audit", "status": "pass", "counts": {"accepted": 1}},
        supplemental_reports={"motion_grammar_consistency": {"kind": "x", "status": "pass", "counts": {"warn": 0}}},
    )
    by_id = {r["id"]: r for r in led["rows"]}
    # 角色：事前 high → overall high
    assert by_id["CHAR_01"]["prevent"] == "high" and by_id["CHAR_01"]["overall"] == "high"
    # 资产：契约 warn → overall warn(=medium 阶)
    assert by_id["PROP_01"]["contract"] == "warn" and by_id["PROP_01"]["overall"] == "warn"
    # 综合排序：high 排在前
    assert led["rows"][0]["id"] == "CHAR_01"
    assert led["counts"]["high"] == 1
    assert "domains" in led
    assert led["delivery_surface"]["status"] == "blocked"
    assert led["dependency_graph"]["summary"]["nodes"] == 2
    assert led["intentional_discontinuity"]["counts"]["accepted"] == 1
    assert "motion_grammar_consistency" in led["supplemental_reports"]


def test_delivery_domains_are_single_acceptance_surface():
    domains = cl.build_delivery_domains([
        {
            "sev": "block",
            "source": "gate:review",
            "dim_key": "subtitle_correctness",
            "dimension": "字幕正确性",
            "text": "英文字幕漏译",
        },
        {
            "sev": "high",
            "source": "score",
            "dim_key": "semantic_continuity",
            "dimension": "语义继承",
            "text": "score below threshold",
        },
        {
            "sev": "block",
            "source": "compliance",
            "dimension": "合规",
            "text": "缺 compliance_manifest",
        },
    ])

    by_key = {d["key"]: d for d in domains}
    assert by_key["subtitle"]["overall"] == "block"
    assert by_key["story"]["overall"] == "high"
    assert by_key["compliance"]["overall"] == "block"
    assert by_key["subtitle"]["findings"][0]["source"] == "gate:review"


def test_root_causes_group_multiple_symptoms_by_entity_anchor():
    causes = cl.build_root_causes([
        {
            "sev": "block",
            "source": "image_qc",
            "dim_key": "character_consistency",
            "dimension": "脸(G1)",
            "loc": "出图/第1集/图片/Clip_01.png",
            "text": "CHAR_01 首帧脸漂",
            "return_to_stage": "image",
        },
        {
            "sev": "warn",
            "source": "video_vlm",
            "dim_key": "multimodal_continuity",
            "dimension": "视频VLM判题(VLM1)",
            "loc": "出视频/第1集/视频/Clip_01.mp4",
            "text": "CHAR_01 看起来像另一个人",
        },
    ])

    assert len(causes) == 1
    assert causes[0]["anchor"] == "CHAR_01"
    assert causes[0]["severity"] == "block"
    assert set(causes[0]["dimensions"]) == {"脸(G1)", "视频VLM判题(VLM1)"}


def test_collect_findings_uses_full_image_qc_findings(tmp_path):
    ep = "第1集"
    report = tmp_path / "生产数据" / "image_qc" / ep / f"image_qc_{ep}.json"
    report.parent.mkdir(parents=True)
    report.write_text(json.dumps({
        "semantic_drift": {"available": True, "findings": [
            {"level": "warn", "code": "semantic_drift_low", "msg": "PROP_01 铜镜 语义漂移疑似"},
        ]},
        "checks": {},
        "lint": {"findings": []},
        "qc_environment": {"precision_level": "full"},
    }, ensure_ascii=False), encoding="utf-8")

    findings = cl.collect_findings(str(tmp_path), ep)

    assert any(f["source"] == "detect" and f["sev"] == "warn" and "PROP_01" in f["text"]
               for f in findings)
