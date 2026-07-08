import json
import sys
from pathlib import Path

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
