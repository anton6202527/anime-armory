#!/usr/bin/env python3
"""ai_label 纯函数单测。从脚本自身目录跑：
    cd skills/n2d-compose && python -m pytest test_ai_label.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai_label as al  # noqa: E402


def test_labeling_applicable_default_true():
    assert al.labeling_applicable(None) is True
    assert al.labeling_applicable({}) is True
    assert al.labeling_applicable({"applicable": True}) is True
    assert al.labeling_applicable({"applicable": False}) is False


def test_build_ai_metadata_carries_gb45438_fields():
    ai = {
        "explicit_label": {"text": "AI生成"},
        "implicit_metadata": {"service_provider_code": "SP-1", "content_id": "C-9", "spec": "GB45438-2025"},
    }
    meta = al.build_ai_metadata(ai)
    assert meta["ai_generated"] == "true"
    assert meta["synthetic_label"] == "AIGC"
    assert meta["service_provider_code"] == "SP-1"
    assert meta["content_production_id"] == "C-9"
    assert "GB45438-2025" in meta["generative_label_spec"]
    assert "service_provider=SP-1" in meta["comment"] and "content_id=C-9" in meta["comment"]


def test_build_ai_metadata_omits_blank_codes_but_still_labels():
    # 编码缺失时仍写生成合成标签/spec（标识本身不能不写），编码字段留空
    meta = al.build_ai_metadata({"implicit_metadata": {}})
    assert meta["synthetic_label"] == "AIGC"
    assert meta["service_provider_code"] == ""
    assert "service_provider=" not in meta["comment"]


def test_label_overlay_spec_scales_with_short_side():
    spec = al.label_overlay_spec({"explicit_label": {"text": "AI生成", "position": "bottom-right"}}, 1080, 1920)
    assert spec["text"] == "AI生成"
    assert spec["position"] == "bottom-right"
    assert spec["font_size"] == int(1080 * al.FONT_RATIO)   # 短边=1080
    assert spec["margin"] == int(1080 * al.MARGIN_RATIO)


def test_label_overlay_spec_defaults_text_and_position():
    spec = al.label_overlay_spec(None, 720, 1280)
    assert spec["text"] == al.DEFAULT_LABEL_TEXT
    assert spec["position"] == "bottom-right"


def test_overlay_xy_expr_four_corners():
    assert al.overlay_xy_expr("bottom-right", 20) == "W-w-20:H-h-20"
    assert al.overlay_xy_expr("top-left", 20) == "20:20"
    assert al.overlay_xy_expr("top-right", 20) == "W-w-20:20"
    assert al.overlay_xy_expr("bottom-left", 20) == "20:H-h-20"
    assert al.overlay_xy_expr("garbage", 20) == "W-w-20:H-h-20"  # 未知 → 右下兜底


def test_mark_manifest_applied_sets_done_and_applied(tmp_path):
    root = tmp_path / "制漫剧" / "剧"
    (root / "合规").mkdir(parents=True)
    manifest = {"ai_labeling": {"explicit_label": {"status": "pending"}, "implicit_metadata": {"applied": False}}}
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    assert al.mark_manifest_applied(str(root)) is True
    data = json.loads((root / "合规" / "compliance_manifest.json").read_text(encoding="utf-8"))
    assert data["ai_labeling"]["explicit_label"]["status"] == "done"
    assert data["ai_labeling"]["implicit_metadata"]["applied"] is True


def test_apply_skips_when_not_applicable(tmp_path):
    root = tmp_path / "制漫剧" / "剧"
    (root / "合规").mkdir(parents=True)
    manifest = {"ai_labeling": {"applicable": False, "notes": "纯海外按平台 AIGC 披露"}}
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    res = al.apply(str(root), "第1集", str(tmp_path / "成片.mp4"), dry_run=True)
    assert res["applied"] is False and res.get("skipped") == "applicable=false"


def test_apply_dry_run_computes_without_mutating(tmp_path):
    root = tmp_path / "制漫剧" / "剧"
    (root / "合规").mkdir(parents=True)
    manifest = {"ai_labeling": {"applicable": True,
                                "explicit_label": {"text": "AI生成", "position": "bottom-right", "status": "pending"},
                                "implicit_metadata": {"service_provider_code": "SP-1", "content_id": "C-1", "applied": False}}}
    (root / "合规" / "compliance_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    res = al.apply(str(root), "第1集", str(tmp_path / "成片.mp4"), dry_run=True)
    assert res["applied"] is False  # dry-run 不落标
    assert res["metadata"]["service_provider_code"] == "SP-1"
    # manifest 未被改动
    data = json.loads((root / "合规" / "compliance_manifest.json").read_text(encoding="utf-8"))
    assert data["ai_labeling"]["implicit_metadata"]["applied"] is False
