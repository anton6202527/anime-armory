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
        "claims": [{"claim": "支持整理为草稿", "evidence": "产品功能设定"}],
        "rights": {"talent": "虚构演员形象", "music": "授权曲库待定", "fonts": "系统字体占位", "assets": "demo 内不含第三方素材"},
        "deliverables": {"master_duration": "30s", "aspect": "9:16", "cutdowns": ["15s", "6s"]},
        "platforms": ["抖音", "小红书"],
    }, ensure_ascii=False), encoding="utf-8")
    (root / "创意" / "concept.md").write_text("## Big Idea\n\n把一天收进盒子。\n", encoding="utf-8")
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
