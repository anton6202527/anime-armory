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


def test_bound_manual_review_downgrades_precision_block_to_warn(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    write_json(root / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    report = {
        "summary": {"hard_blocks": 0, "advisory": 0},
        "qc_environment": {"precision_level": "degraded"},
    }
    import hashlib
    encoded = json.dumps(report, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    report["manual_review"] = {"accepted": True, "reviewer": "审图人",
                               "bound_report_sha256": hashlib.sha256(encoded).hexdigest()}
    write_json(root / "生产数据" / "image_qc" / "image_qc.json", report)

    out = mod.build_report(str(root))
    assert not any(f["code"] == "image_qc_precision" for f in out["findings"])
    assert any(f["code"] == "image_qc_precision_manual" for f in out["findings"])


def test_legacy_boolean_manual_review_stays_block(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    write_json(root / "分镜" / "clip_plan.json", {"clips": [{"clip_id": "Clip_01"}]})
    write_json(root / "生产数据" / "image_qc" / "image_qc.json", {
        "summary": {"hard_blocks": 0, "advisory": 0},
        "qc_environment": {"precision_level": "degraded"},
        "manual_review_accepted": True,
    })
    out = mod.build_report(str(root))
    hits = [f for f in out["findings"] if f["code"] == "image_qc_precision"]
    assert hits and "旧式布尔留痕" in hits[0]["message"]


def test_production_stats_flags_high_redraw_and_takes(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    events = root / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    # 2 资产，其中 1 个抽了 3 次 → 重画率 50% > 35%
    for asset, count in (("出图/a.png", 3), ("出图/b.png", 1)):
        for _ in range(count):
            rows.append(json.dumps({"stage": "image", "event": "generation",
                                    "generation": {"asset": asset}}, ensure_ascii=False))
    events.write_text("\n".join(rows) + "\n", encoding="utf-8")
    write_json(root / "出视频" / "jobs_manifest.json", {
        "jobs": [{"clip_id": "Clip_01", "takes": [{}, {}, {}, {}, {}]},
                 {"clip_id": "Clip_02", "takes": [{}, {}, {}]}],
    })
    findings: list[dict] = []
    mod.production_stats(findings, str(root))
    codes = {f["code"] for f in findings}
    assert "image_redraw_rate_high" in codes
    assert "takes_per_clip_high" in codes


def test_production_stats_quiet_when_healthy(tmp_path: Path) -> None:
    mod = load_module()
    root = tmp_path
    events = root / "生产数据" / "production_events.jsonl"
    events.parent.mkdir(parents=True, exist_ok=True)
    events.write_text(json.dumps({"stage": "image", "event": "generation",
                                  "generation": {"asset": "出图/a.png"}}) + "\n", encoding="utf-8")
    write_json(root / "出视频" / "jobs_manifest.json",
               {"jobs": [{"clip_id": "Clip_01", "takes": [{}]}]})
    findings: list[dict] = []
    mod.production_stats(findings, str(root))
    assert all(f["severity"] == "info" for f in findings)
    assert {f["code"] for f in findings} == {"image_redraw_rate", "takes_per_clip"}
