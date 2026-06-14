"""consistency_ledger 纯函数单测（无 I/O）。
cd skills/n2d-review/scripts && python -m pytest test_consistency_ledger.py
"""
import consistency_ledger as cl


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
    )
    by_id = {r["id"]: r for r in led["rows"]}
    # 角色：事前 high → overall high
    assert by_id["CHAR_01"]["prevent"] == "high" and by_id["CHAR_01"]["overall"] == "high"
    # 资产：契约 warn → overall warn(=medium 阶)
    assert by_id["PROP_01"]["contract"] == "warn" and by_id["PROP_01"]["overall"] == "warn"
    # 综合排序：high 排在前
    assert led["rows"][0]["id"] == "CHAR_01"
    assert led["counts"]["high"] == 1
