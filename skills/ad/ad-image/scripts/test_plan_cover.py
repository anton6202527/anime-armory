import importlib.util
import json
from pathlib import Path


def _load(name):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(f"adimage_{name}", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


plan_cover = _load("plan_cover")


def _project(tmp_path):
    root = tmp_path / "ad-proj"
    (root / "设定库").mkdir(parents=True)
    (root / "需求").mkdir(parents=True)
    (root / "_meta.json").write_text(
        json.dumps({"kind": "ad_project", "line": "ad", "synopsis": "元气星盒", "cover": None},
                   ensure_ascii=False), encoding="utf-8")
    (root / "需求" / "brief.json").write_text(
        json.dumps({"key_message": "一盒元气", "campaign_objective": "转化行动",
                    "usp": ["0糖", "低卡"], "mandatories": {"slogan": "元气星盒", "endcard_cta": "立即购买"}},
                   ensure_ascii=False), encoding="utf-8")
    (root / "设定库" / "asset_registry.json").write_text(
        json.dumps({"brand": {"id": "BRAND_XH", "name": "星盒", "text_logo": "STARBOX",
                              "primary_hex": "#FF6600", "reference_images": ["出图/共享/定妆_品牌.png"]},
                    "products": [{"id": "PROD_BOX", "name": "星盒",
                                  "reference_images": ["出图/共享/定妆_产品.png"]}]},
                   ensure_ascii=False), encoding="utf-8")
    return root


def test_plan_cover_writes_portrait_job_and_keeps_cover_null(tmp_path):
    root = _project(tmp_path)
    manifest = plan_cover.run(root)
    job = manifest["job"]
    assert job["aspect"] == "9:16" and job["orientation"] == "portrait"
    # C5: concrete model name + separated channel access path.
    assert job["planned_model"] == "GPT Image 2"
    assert job["planned_channel"] == "Codex CLI"
    assert manifest["image_route"] == {"model": "GPT Image 2", "channel": "Codex CLI"}
    # C4/B4: cover stays null; PNG not faked.
    assert manifest["cover_field"] is None
    assert json.loads((root / "_meta.json").read_text(encoding="utf-8"))["cover"] is None
    assert not (root / plan_cover.COVER_PNG_REL).exists()
    # product present -> image2image required with real reference inputs.
    assert job["requires_image_input"] is True
    assert job["reference_inputs"] == ["出图/共享/定妆_品牌.png", "出图/共享/定妆_产品.png"]
    assert set(job["requires_assets"]) == {"BRAND_XH", "PROD_BOX"}
    assert job["prompt_sha256"]


def test_cover_prompt_carries_identity_and_concept(tmp_path):
    root = _project(tmp_path)
    plan_cover.run(root)
    prompt = (root / plan_cover.COVER_PROMPT_REL).read_text(encoding="utf-8")
    assert "GPT Image 2" in prompt and "Codex CLI" in prompt
    assert "#FF6600" in prompt and "BRAND_XH" in prompt and "PROD_BOX" in prompt
    assert "一盒元气" in prompt  # key_message concept anchor
    assert "竖版" in prompt and "不要横版构图" in prompt
    assert "逆向" in prompt  # backend governance trace


def test_plan_cover_emits_production_event(tmp_path):
    root = _project(tmp_path)
    plan_cover.run(root)
    events = [json.loads(x) for x in
              (root / "生产数据" / "production_events.jsonl").read_text(encoding="utf-8").splitlines()]
    cover_events = [e for e in events if e["event"] == "cover_prompt_plan"]
    assert cover_events and cover_events[0]["generation"]["planned_model"] == "GPT Image 2"
