import importlib.util
import json
from pathlib import Path


P = Path(__file__).with_name("wardrobe_props.py")
S = importlib.util.spec_from_file_location("wardrobe_props", P)
M = importlib.util.module_from_spec(S); S.loader.exec_module(M)


def valid_contract():
    d = M.template(); d["status"] = "confirmed"
    d["world_context"].update(era="北宋", polity_region="宋/汴京")
    d["sources"] = [
        {"id": "A", "source_type": "museum_collection"},
        {"id": "B", "source_type": "contemporary_image"},
    ]
    d["wardrobe"] = [{"character_id":"CHAR_A","outfit_id":"OUTFIT_A","name":"官服","identity_rank":"官员","layers":["袍"],"silhouette":"长袍","collar_neckline":"圆领","closure":"右衽/结构待图证","sleeves":"宽袖","waist_belt":"带","headwear":["幞头"],"footwear":["靴"],"materials":["绢"],"palette":["绛"],"permanent_accessories":[],"state_variants":[],"evidence_refs":["A","B"],"forbidden":["明清补服"],"status":"confirmed"}]
    d["props"] = [{"prop_id":"PROP_A","name":"炉","function":"持香","dimensions":"单手提","construction":"提梁+炉身","materials":["金属"],"interaction_grip":"右手提梁","production_variants":["hero","duplicate"],"evidence_refs":["A","B"],"forbidden":["随机字"],"status":"confirmed"}]
    return d


def test_strict_historical_contract_passes():
    assert M.validate(valid_contract(), strict=True) == []


def test_strict_requires_cross_evidence_and_override_audit():
    d = valid_contract(); d["sources"] = [d["sources"][0]]
    d["overrides"] = [{"scope":"服装"}]
    errors = M.validate(d, strict=True)
    assert any("至少需" in x for x in errors)
    assert any("override 缺" in x for x in errors)


def test_apply_syncs_registry_and_receipt(tmp_path):
    d = valid_contract(); M.dump(tmp_path / M.REL, d)
    M.dump(tmp_path / M.REG, {"schema_version":2,"assets":{"CHAR_A":{"outfits":{"OUTFIT_A":{"reference_images":[]}}},"PROP_A":{}}})
    receipt = M.apply(tmp_path, d)
    reg = json.loads((tmp_path / M.REG).read_text())
    assert "领襟:圆领" in reg["assets"]["CHAR_A"]["outfits"]["OUTFIT_A"]["description"]
    assert "功能:持香" in reg["assets"]["PROP_A"]["prop_contract"]
    assert receipt["changed_ids"] == ["CHAR_A/OUTFIT_A", "PROP_A"]
