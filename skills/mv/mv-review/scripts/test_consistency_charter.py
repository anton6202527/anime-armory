from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module():
    path = Path(__file__).with_name("consistency_charter.py")
    spec = importlib.util.spec_from_file_location("mv_consistency_charter", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_real_sources_satisfy_charter() -> None:
    """守护主测试：真实 gate.py / QC 源码必须满足全部 charter 声明。

    这条红了 = 有人（可能是未来的你）动了 load-bearing 闸——删检查/改名/新增 demo 豁免/
    削 QC 硬闸。要么恢复，要么显式改 charter 对应行并在 rationale 写明裁决。"""
    mod = load_module()
    violations = mod.audit_all()
    assert violations == [], "\n".join(f"{v['kind']} · {v['gate']}: {v['problem']}" for v in violations)


def test_detects_missing_gate_and_token() -> None:
    mod = load_module()
    source = "def _rights_errors(root, stage, meta):\n    return []\n"
    charter = {
        "_rights_errors": {"guard_tokens": ["song_rights_status"], "max_is_demo_refs": 0},
        "_gone_gate": {"guard_tokens": [], "max_is_demo_refs": 0},
    }
    violations = mod.audit_gate_source(source, charter)
    kinds = {(v["gate"], v["kind"]) for v in violations}
    assert ("_rights_errors", "guard_token_missing") in kinds
    assert ("_gone_gate", "missing_gate") in kinds


def test_detects_new_demo_gating() -> None:
    mod = load_module()
    source = (
        "def _picture_lock_errors(root, stage, meta):\n"
        "    if meta.get(\"is_demo\"):\n"
        "        return []\n"
        "    if meta.get(\"is_demo\") and stage == \"compose\":\n"
        "        return []\n"
        "    return [\"editorial_timeline_sha256\"]\n"
    )
    charter = {"_picture_lock_errors": {"guard_tokens": ["editorial_timeline_sha256"], "max_is_demo_refs": 1}}
    violations = mod.audit_gate_source(source, charter)
    assert any(v["kind"] == "demo_gating_increased" for v in violations)
    # 基线内不报
    charter["_picture_lock_errors"]["max_is_demo_refs"] = 2
    assert mod.audit_gate_source(source, charter) == []


def test_detects_unregistered_demo_gate() -> None:
    mod = load_module()
    source = (
        "def _new_sneaky_gate(root, stage, meta):\n"
        "    if meta.get(\"is_demo\"):\n"
        "        return []\n"
        "    return [\"err\"]\n"
    )
    assert mod.find_unregistered_demo_gates(source, {}) == ["_new_sneaky_gate"]
    assert mod.find_unregistered_demo_gates(source, {"_new_sneaky_gate": {}}) == []


def test_hard_qc_token_missing_detected(tmp_path: Path) -> None:
    mod = load_module()
    # 构造一个缺片段的假 skills 树
    fake = tmp_path / "mv-image" / "scripts"
    fake.mkdir(parents=True)
    (fake / "image_qc.py").write_text("HARD_CHECKS = ()\n", encoding="utf-8")
    violations = mod.audit_hard_qc(str(tmp_path))
    kinds = {v["kind"] for v in violations}
    assert "hard_qc_token_missing" in kinds or "missing_file" in kinds


def test_hard_qc_forbidden_token_detected(tmp_path: Path) -> None:
    mod = load_module()
    fake = tmp_path / "mv-video" / "scripts"
    fake.mkdir(parents=True)
    (fake / "video_jobs.py").write_text(
        'payload = {"root_rel": ".", "project_root": root}\n', encoding="utf-8"
    )
    original = mod.HARD_QC_INVARIANTS
    try:
        mod.HARD_QC_INVARIANTS = [{
            "file": "mv-video/scripts/video_jobs.py",
            "dim": "portable root",
            "tokens": ['"root_rel": "."'],
            "forbidden_tokens": ['"project_root": root'],
        }]
        violations = mod.audit_hard_qc(str(tmp_path))
    finally:
        mod.HARD_QC_INVARIANTS = original
    assert any(v["kind"] == "hard_qc_forbidden_token_present" for v in violations)
