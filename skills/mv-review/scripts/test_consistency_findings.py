from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("consistency_findings.py")
    spec = importlib.util.spec_from_file_location("mv_consistency_findings", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_mv_consistency_blocks_on_degraded_image_qc_and_inherit(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    write_json(root / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    write_json(root / "生产数据" / "image_qc" / "image_qc.json", {
        "summary": {"hard_blocks": 0, "advisory": 0},
        "qc_environment": {"precision_level": "degraded"},
    })
    write_json(root / "生产数据" / "video_inherit_contract" / "inherit_contract.json", {
        "summary": {"hard_blocks": 1, "warnings": 0},
    })
    write_json(root / "生产数据" / "video_qc" / "video_qc.json", {
        "summary": {"hard_blocks": 0, "warnings": 0},
        "seams": [],
    })

    report = mod.build_report(str(root))

    assert report["kind"] == "mv_consistency_findings"
    assert report["summary"]["block"] >= 2
    assert any(f["code"] == "image_qc_precision" for f in report["findings"])

