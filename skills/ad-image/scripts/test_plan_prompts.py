import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_prompts as pp  # noqa: E402


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "广告项目"
    (root / "脚本").mkdir(parents=True)
    (root / "设定库").mkdir()
    (root / "脚本" / "storyboard.json").write_text(json.dumps({
        "aspect": "9:16",
        "clips": [
            {
                "id": "C01",
                "duration": 3,
                "scene": "App 界面",
                "shot": "手机特写",
                "prompt": "Starbox app UI",
                "assets": {"PROD_APP": True, "BRAND_APP": True},
                "product_lock": "同一品牌色",
                "safe_area": {"core_in_center_4x4": True},
                "continuity": {"need_end_frame": True, "transition": "screen glow"},
            }
        ],
    }, ensure_ascii=False), encoding="utf-8")
    (root / "设定库" / "asset_registry.json").write_text(json.dumps({
        "brand": {"id": "BRAND_APP", "name": "星盒", "text_logo": "星盒", "primary_hex": "#2E9E97", "accent_hex": "#F6C85F"},
        "products": [{"id": "PROD_APP", "name": "星盒 App", "brand_id": "BRAND_APP", "type": "mobile_app"}],
    }, ensure_ascii=False), encoding="utf-8")
    return root


def test_run_writes_prompt_pack_and_jobs(tmp_path):
    root = _project(tmp_path)
    payload = pp.run(root)

    assert payload["summary"] == {"first_frames": 1, "end_frames": 1, "planned": 2}
    assert (root / "出图" / "共享" / "asset_registry.json").is_file()
    assert (root / "出图" / "共享" / "prompt" / "品牌_BRAND_APP.md").is_file()
    assert (root / "出图" / "共享" / "prompt" / "产品_PROD_APP.md").is_file()
    assert (root / "出图" / "分镜" / "prompt" / "00_总览.md").is_file()
    assert (root / "出图" / "分镜" / "prompt" / "镜头01.md").is_file()
    assert (root / "出图" / "分镜" / "prompt" / "镜头01_end.md").is_file()
    assert payload["image_route"] == {"model": "GPT Image 2", "channel": "Codex CLI"}
    assert payload["jobs"][0]["planned_model"] == "GPT Image 2"
    assert payload["jobs"][0]["planned_channel"] == "Codex CLI"


def test_shot_prompt_contains_product_qc_lint_markers(tmp_path):
    root = _project(tmp_path)
    pp.run(root)
    text = (root / "出图" / "分镜" / "prompt" / "镜头01.md").read_text(encoding="utf-8")

    assert "参考图/资产引用" in text
    assert "PROD_APP" in text
    assert "身份锁定句" in text
    assert "同一 logo" in text
    assert "不要改包装文字" in text
    assert "不要变形 logo" in text


def test_manifest_is_not_fake_generation(tmp_path):
    root = _project(tmp_path)
    payload = pp.run(root)

    assert "not faked" in payload["note"]
    assert payload["jobs"][0]["status"] == "planned"
    assert payload["jobs"][0]["expected_output"].endswith("镜头01.png")


def test_asset_regex_does_not_match_plain_product_or_brand_words():
    shot = {"prompt": "product shot with brand color but no structured ids"}

    assert pp.asset_ids(shot, pp.PROD_RE) == []
    assert pp.asset_ids(shot, pp.BRAND_RE) == []


@pytest.mark.parametrize("brand,product,pid,bid,scene", [
    ("清露", "气泡水", "PROD_QINGLU_BOTTLE", "BRAND_QINGLU", "瓶装饮料 hero"),
    ("岚途", "电动汽车", "PROD_LANTU_CAR", "BRAND_LANTU", "汽车外观 hero"),
    ("安家", "家政服务", "PROD_ANJIA_SERVICE", "BRAND_ANJIA", "服务流程演示"),
    ("云账", "财务软件", "PROD_YUNZHANG_APP", "BRAND_YUNZHANG", "App 界面 demo"),
])
def test_prompt_templates_are_industry_neutral(tmp_path, brand, product, pid, bid, scene):
    root = tmp_path / pid
    (root / "脚本").mkdir(parents=True)
    (root / "设定库").mkdir()
    (root / "脚本" / "storyboard.json").write_text(json.dumps({
        "aspect": "9:16", "shots": [{"shot_id": "S1", "duration": 3, "scene": scene,
        "assets": {pid: True, bid: True}, "safe_area": {"core_in_center_4x4": True}}],
    }, ensure_ascii=False), encoding="utf-8")
    (root / "设定库" / "asset_registry.json").write_text(json.dumps({
        "brand": {"id": bid, "name": brand, "text_logo": brand, "primary_hex": "#224466"},
        "products": [{"id": pid, "name": product, "brand_id": bid,
                      "reference_images": [f"设定库/{pid}.png"]}],
    }, ensure_ascii=False), encoding="utf-8")

    pp.run(root)
    rendered = "\n".join(p.read_text(encoding="utf-8") for p in (root / "出图").rglob("*.md"))
    assert brand in rendered and pid in rendered and bid in rendered
    assert "STARBOX" not in rendered and "Starbox" not in rendered and "星盒" not in rendered
