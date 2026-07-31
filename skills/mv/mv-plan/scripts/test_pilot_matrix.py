from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("pilot_matrix.py")
    spec = importlib.util.spec_from_file_location("mv_pilot_matrix", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write_plan(root: Path, clips: list[dict]) -> None:
    p = root / "分镜" / "clip_plan.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"kind": "mv_clip_plan", "clips": clips}, ensure_ascii=False), encoding="utf-8")


def _clip(cid, **kw):
    sd = {k: kw.pop(k) for k in ("shot_size", "angle", "camera_movement", "location_id") if k in kw}
    clip = {"clip_id": cid, "shot_design": sd}
    clip.update(kw)
    return clip


def _by_reason(matrix: dict) -> dict[str, str]:
    out = {}
    for p in matrix["probes"]:
        for reason in p["reasons"]:
            out[reason] = p["clip_id"]
    return out


def test_probe_categories_selected(tmp_path: Path) -> None:
    mod = load_module()
    clips = [
        _clip("Clip_01", section="intro", location_id="A", camera_movement="固定"),
        _clip("Clip_02", section="verse", location_id="A", shot_size="特写", desc="她崩溃大哭"),
        _clip("Clip_03", section="verse", location_id="B", camera_movement="固定",
              continuity={"identity_state": "白裙"}),
        _clip("Clip_04", section="chorus", beat_role="key", location_id="B", camera_movement="环绕甩镜"),
    ]
    write_plan(tmp_path, clips)
    matrix = mod.build_matrix(str(tmp_path))
    by_reason = _by_reason(matrix)
    assert by_reason["opening_probe"] == "Clip_01"
    assert by_reason["chorus_peak_probe"] == "Clip_04"
    # 无 drift_risk 报告 → identity_probe 兜底选近景+强情绪
    assert by_reason["identity_probe"] == "Clip_02"
    assert by_reason["motion_probe"] == "Clip_04"
    assert by_reason["state_change_probe"] == "Clip_03"
    # 同镜多类合并：Clip_04 同时是 chorus_peak+motion，不重复占位
    assert len(matrix["probes"]) <= 5
    assert any("drift_risk" in n for n in matrix["notes"])


def test_drift_report_drives_identity_probe(tmp_path: Path) -> None:
    mod = load_module()
    clips = [
        _clip("Clip_01", section="verse", location_id="A"),
        _clip("Clip_02", section="verse", location_id="A"),
        _clip("Clip_03", section="verse", location_id="A"),
    ]
    write_plan(tmp_path, clips)
    dr = tmp_path / "生产数据" / "drift_risk" / "drift_risk.json"
    dr.parent.mkdir(parents=True, exist_ok=True)
    dr.write_text(json.dumps({"clips": [
        {"clip_id": "Clip_02", "tier": "high", "score": 88},
        {"clip_id": "Clip_03", "tier": "high", "score": 60},
    ]}, ensure_ascii=False), encoding="utf-8")
    matrix = mod.build_matrix(str(tmp_path))
    assert _by_reason(matrix)["identity_probe"] == "Clip_02"


def test_limit_and_opening_guaranteed(tmp_path: Path) -> None:
    mod = load_module()
    clips = [_clip(f"Clip_{i:02d}", section="chorus", beat_role="key", location_id=f"L{i}",
                   shot_size="特写", desc="嘶吼", camera_movement="环绕") for i in range(1, 9)]
    write_plan(tmp_path, clips)
    matrix = mod.build_matrix(str(tmp_path), limit=2)
    assert len(matrix["probes"]) <= 2
    assert "opening_probe" in matrix["probes"][0]["reasons"]


def test_write_and_exit_zero(tmp_path: Path) -> None:
    mod = load_module()
    write_plan(tmp_path, [_clip("Clip_01", section="intro", location_id="A")])
    rc = mod.main([str(tmp_path), "--write"])
    assert rc == 0
    payload = json.loads((tmp_path / "生产数据" / "pilot_matrix" / "pilot_matrix.json").read_text(encoding="utf-8"))
    assert payload["kind"] == "mv_pilot_matrix"
    assert payload["inputs_sha256"]["分镜/clip_plan.json"]
    assert (tmp_path / "生产数据" / "pilot_matrix" / "pilot_matrix.md").exists()


def test_missing_plan_still_reports(tmp_path: Path) -> None:
    mod = load_module()
    matrix = mod.build_matrix(str(tmp_path))
    assert matrix["probes"] == []
    assert any("clip_plan" in n for n in matrix["notes"])
