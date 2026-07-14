from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("doctor.py")
SPEC = importlib.util.spec_from_file_location("comic_doctor", MODULE_PATH)
assert SPEC and SPEC.loader
doctor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(doctor)


def test_doctor_never_disguises_vlm_as_full() -> None:
    report = doctor.diagnose()
    caps = {item["name"]: item for item in report["capabilities"]}
    assert caps["contract_and_sha_validation"]["status"] == "full"
    assert caps["multimodal_visual_judgement"]["status"] == "degraded"
    assert report["policy"]["uncalibrated_visual_metric"] == "warn_only"


def test_project_checks_are_explicit(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 漫画形态: 条漫\n", encoding="utf-8")
    report = doctor.diagnose(tmp_path)
    checks = {item["name"]: item["status"] for item in report["project_checks"]}
    assert checks["settings"] == "present"
    assert checks["identity_registry"] == "missing"
    assert report["project_root"] == "."
