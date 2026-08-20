#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan_prompts as pp  # noqa: E402
from ad_video_prompt_compiler import parse_markdown  # noqa: E402


def test_plan_writes_video_prompts_and_manifest(tmp_path):
    root = tmp_path / "项目"
    (root / "脚本").mkdir(parents=True)
    (root / "出图" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出图" / "分镜" / "图片").mkdir(parents=True)
    storyboard = {
        "clips": [{
            "shot_id": "镜头01",
            "duration": 4.2,
            "scene": "星盒界面",
            "shot": "手机特写，UI 卡片归入今日手账",
            "assets": {"PROD_STARBOX_APP": True, "BRAND_STARBOX": True},
            "product_lock": "保留星盒 UI。",
            "continuity": {"need_end_frame": True},
        }]
    }
    (root / "脚本" / "storyboard.json").write_text(json.dumps(storyboard, ensure_ascii=False), encoding="utf-8")
    (root / "出图" / "分镜" / "prompt" / "00_总览.md").write_text(
        "## 视觉一致性契约\n- 品牌色：#2E9E97\n- 光位锚：45°暖主光\n- 轴线：左到右\n",
        encoding="utf-8",
    )
    (root / "出图" / "分镜" / "图片" / "镜头01.png").write_bytes(b"png")
    (root / "出图" / "分镜" / "图片" / "镜头01_end.png").write_bytes(b"png")
    (root / "出视频" / "分镜" / "prompt").mkdir(parents=True)
    (root / "出视频" / "分镜" / "prompt" / "video_model_routes.json").write_text(
        json.dumps({"routes": [{
            "clip": "镜头01",
            "primary": "seedance",
            "fallback": ["dreamina"],
            "quality_tier": "high",
            "reason": "产品一致性",
            "duration": 4.2,
        }]}, ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = pp.plan(root)

    prompt = (root / "出视频" / "分镜" / "prompt" / "镜头01.md").read_text(encoding="utf-8")
    assert "#2E9E97" in prompt
    assert "PROD_STARBOX_APP" in prompt
    assert "身份锁定句" in prompt
    assert "镜头01_end.png" in prompt
    compiled = parse_markdown(prompt)
    assert compiled is not None
    assert compiled["kind"] == "ad_compiled_video_prompt"
    assert "产品主动作" in compiled["prompt"]
    assert "route_reason" not in compiled["prompt"]
    assert "PROD_STARBOX_APP" not in compiled["prompt"]
    assert len(compiled["prompt"]) < 650
    assert manifest["summary"] == {"clips": 1, "frames2video": 1, "image2video": 0}
    assert manifest["schema_version"] == 3
    assert manifest["render_profile"]["path"] == "生产数据/render_profile.json"
    assert manifest["jobs"][0]["render_profile"]["source_generation"]["resolution"] == "1280x720"
    assert manifest["jobs"][0]["mode"] == "frames2video"
    assert manifest["jobs"][0]["prompt_source_kind"] == "compiled_submit_prompt"
    assert manifest["jobs"][0]["submit_prompt"] == compiled["prompt"]
    assert manifest["jobs"][0]["expected_output"] == "出视频/分镜/视频/镜头01.mp4"
