from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("consistency_findings.py")
    spec = importlib.util.spec_from_file_location("ad_consistency_findings", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_ad_consistency_aggregates_product_and_video(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    (root / "出图" / "分镜" / "图片").mkdir(parents=True)
    (root / "出图" / "分镜" / "图片" / "镜头01.png").write_bytes(b"x")
    write_json(root / "出图" / "分镜" / "product_qc.json", {
        "summary": {"block": 1, "warn": 1},
        "qc_environment": {"precision_level": "full"},
        "findings": [{"severity": "block", "shot": "镜头1", "check": "brand_color", "reason": "品牌色漂移"}],
    })
    write_json(root / "出视频" / "分镜" / "video_qc.json", {"summary": {"block": 0, "warn": 1}})
    write_json(root / "出视频" / "分镜" / "contract_inheritance.json", {"summary": {"block": 0, "warn": 0}})
    write_json(root / "脚本" / "广告法机检报告.json", {"summary": {"block": 0, "warn": 0}})
    write_json(root / "合规" / "ai_usage.json", {"visual_mode": "AI-generated"})

    report = mod.build_report(str(root))

    assert report["kind"] == "ad_consistency_findings"
    assert report["summary"]["block"] >= 1
    assert any(f["code"] == "brand_color" for f in report["findings"])

