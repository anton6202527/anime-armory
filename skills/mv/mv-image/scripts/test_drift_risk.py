from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("drift_risk.py")
    spec = importlib.util.spec_from_file_location("mv_drift_risk", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def write_plan(root: Path, clips: list[dict]) -> None:
    p = root / "分镜" / "clip_plan.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"kind": "mv_clip_plan", "clips": clips}, ensure_ascii=False), encoding="utf-8")


def write_registry(root: Path, status: str = "ready", n_paths: int = 3, others: list[str] | None = None) -> None:
    p = root / "设定" / "identity_registry.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    identities = [{"id": "CHAR_lead", "display_name": "阿檀", "reference_group": "REF_lead"}]
    for i, name in enumerate(others or []):
        identities.append({"id": f"CHAR_{i}", "display_name": name, "reference_group": f"REF_{i}"})
    payload = {
        "lead_id": "CHAR_lead",
        "identities": identities,
        "reference_groups": [{"id": "REF_lead", "identity_id": "CHAR_lead", "status": status,
                              "paths": [f"出图/共享/图片/定妆_{i}.png" for i in range(n_paths)]}],
    }
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _clip(cid, **kw):
    sd = {k: kw.pop(k) for k in ("shot_size", "angle", "camera_movement", "lens_feel",
                                 "location_id", "lighting") if k in kw}
    clip = {"clip_id": cid, "shot_design": sd}
    clip.update(kw)
    return clip


def _codes(report: dict) -> set[str]:
    return {f["code"] for f in report["findings"]}


def _row(report: dict, cid: str) -> dict:
    return next(r for r in report["clips"] if r["clip_id"] == cid)


def test_high_risk_closeup_emotion_no_reference(tmp_path: Path) -> None:
    mod = load_module()
    write_registry(tmp_path)
    clips = [
        _clip("Clip_01", shot_size="全景", location_id="街道", reference_inputs=["出图/共享/图片/定妆_0.png"]),
        # 近景 + 强情绪 + 逆光 + 无参考 → 放大器叠加应到 high
        _clip("Clip_02", shot_size="特写", location_id="街道", desc="她逆光中崩溃大哭", reference_inputs=[]),
    ]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    row = _row(report, "Clip_02")
    assert {"closeup", "strong_emotion", "lighting_risk", "no_reference"} <= set(row["signals"])
    assert row["tier"] == "high"
    assert "high_drift_risk_clips" in _codes(report)
    assert report["summary"]["block"] == 0
    # 干净镜保持 low
    assert _row(report, "Clip_01")["tier"] == "low"


def test_lead_reference_base_weak_raises_all_clips(tmp_path: Path) -> None:
    mod = load_module()
    write_registry(tmp_path, status="partial", n_paths=1)
    write_plan(tmp_path, [_clip("Clip_01", shot_size="中景", location_id="A")])
    report = mod.build_report(str(tmp_path))
    assert report["lead_base"]["reason"] == "lead_reference_partial"
    assert "lead_reference_base_weak" in _codes(report)


def test_state_change_and_reentry_signals(tmp_path: Path) -> None:
    mod = load_module()
    write_registry(tmp_path)
    clips = [_clip("Clip_00", location_id="A", continuity={"identity_state": "红裙"})]
    # 换装 → state_change
    clips.append(_clip("Clip_01", location_id="A", continuity={"identity_state": "白裙"}))
    # 中间隔 6 个白裙 clip 后红裙再登场 → state_reentry
    for i in range(2, 8):
        clips.append(_clip(f"Clip_{i:02d}", location_id="A", continuity={"identity_state": "白裙"}))
    clips.append(_clip("Clip_08", location_id="A", continuity={"identity_state": "红裙"}))
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    assert "state_change" in _row(report, "Clip_01")["signals"]
    reentry = _row(report, "Clip_08")["signals"]
    assert "state_reentry" in reentry and "state_change" in reentry


def test_multi_subject_via_registry_name_and_new_location(tmp_path: Path) -> None:
    mod = load_module()
    write_registry(tmp_path, others=["少年剑客"])
    clips = [
        _clip("Clip_01", location_id="A"),
        _clip("Clip_02", location_id="B", desc="少年剑客与她并肩", reference_inputs=[]),
    ]
    write_plan(tmp_path, clips)
    report = mod.build_report(str(tmp_path))
    signals = set(_row(report, "Clip_02")["signals"])
    assert "multi_subject" in signals
    assert "new_location_no_reference" in signals


def test_measured_face_backfill_promotes_to_high(tmp_path: Path) -> None:
    mod = load_module()
    write_registry(tmp_path)
    write_plan(tmp_path, [_clip("Clip_01", shot_size="全景", location_id="A",
                                reference_inputs=["出图/共享/图片/定妆_0.png"])])
    qc = tmp_path / "生产数据" / "image_qc" / "image_qc.json"
    qc.parent.mkdir(parents=True, exist_ok=True)
    qc.write_text(json.dumps({
        "checks": {"face": {"mode": "insightface", "shots": [
            {"clip": "Clip_01", "verdict": "warn", "score": 0.31},
        ]}},
    }, ensure_ascii=False), encoding="utf-8")
    report = mod.build_report(str(tmp_path))
    row = _row(report, "Clip_01")
    assert row["tier"] == "high"
    assert "measured_face_warn" in row["signals"]
    assert "measured_face_drift_backfill" in _codes(report)


def test_degraded_face_mode_noted_not_fabricated(tmp_path: Path) -> None:
    mod = load_module()
    write_registry(tmp_path)
    write_plan(tmp_path, [_clip("Clip_01", location_id="A")])
    qc = tmp_path / "生产数据" / "image_qc" / "image_qc.json"
    qc.parent.mkdir(parents=True, exist_ok=True)
    qc.write_text(json.dumps({
        "checks": {"face": {"mode": "pillow_basic", "shots": [
            {"clip": "Clip_01", "verdict": "warn"},
        ]}},
    }, ensure_ascii=False), encoding="utf-8")
    report = mod.build_report(str(tmp_path))
    # 降级模式不回灌：warn 不臆造成实测脸漂
    assert "measured_face_drift_backfill" not in _codes(report)
    assert any("实测回灌不可用" in n for n in report["notes"])


def test_write_and_exit_zero(tmp_path: Path) -> None:
    mod = load_module()
    write_registry(tmp_path)
    write_plan(tmp_path, [_clip("Clip_01", shot_size="特写", desc="怒吼", reference_inputs=[], location_id="A")])
    rc = mod.main([str(tmp_path), "--write"])
    assert rc == 0
    payload = json.loads((tmp_path / "生产数据" / "drift_risk" / "drift_risk.json").read_text(encoding="utf-8"))
    assert payload["kind"] == "mv_drift_risk"
    assert payload["root_rel"] == "."
    assert "project_root" not in payload
    assert str(tmp_path) not in json.dumps(payload, ensure_ascii=False)
    assert payload["summary"]["block"] == 0
    assert (tmp_path / "生产数据" / "drift_risk" / "drift_risk.md").exists()
