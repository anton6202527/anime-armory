from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).with_name("catalog.py")
SPEC = importlib.util.spec_from_file_location("artifact_catalog", SCRIPT)
catalog = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(catalog)


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_catalog_classifies_cache_and_derived_views(tmp_path: Path) -> None:
    write(tmp_path / "_进度.md", "# progress")
    write(tmp_path / "生产数据" / "score_第1集.json", "{}")
    write(tmp_path / "生产数据" / "score_第1集.md", "# score")
    write(tmp_path / "合成" / "第1集" / "_work" / "concat.mp4", "cache")
    payload = catalog.build_catalog(tmp_path, line="n2d")
    rows = {row["path"]: row for row in payload["artifacts"]}
    assert rows["生产数据/score_第1集.md"]["role"] == "view"
    assert rows["生产数据/score_第1集.md"]["derived_from"] == "生产数据/score_第1集.json"
    assert rows["合成/第1集/_work/concat.mp4"]["disposable"] is True
    assert payload["summary"]["disposable_bytes"] > 0


def test_doctor_finds_zero_voice_and_absolute_paths(tmp_path: Path) -> None:
    write(tmp_path / "_进度.md", "# progress")
    write(tmp_path / "生产数据" / "job.json", json.dumps({"root": "/Users/me/work"}))
    zero = tmp_path / "合成" / "第1集" / "配音" / "Clip1_voice.wav"
    write(zero, "")
    payload = catalog.doctor(tmp_path, line="n2d")
    codes = {row["code"] for row in payload["issues"]}
    assert payload["status"] == "block"
    assert "zero_byte_legacy_voice" in codes
    assert "persisted_absolute_path" in codes


def test_migrate_moves_durable_evidence_and_updates_references(tmp_path: Path) -> None:
    write(tmp_path / "_进度.md", "# progress")
    work = tmp_path / "合成" / "第1集" / "_work"
    write(work / "timeline.json", "{}")
    write(work / "editorial_timeline.otio", "{}")
    write(work / "animatic_timeline.otio", "{}")
    write(tmp_path / "合成" / "第1集" / "rough_cut_preview.html", "<html></html>")
    zero = tmp_path / "合成" / "第1集" / "配音" / "Clip1_voice.json"
    write(zero, "")
    write(
        tmp_path / "生产数据" / "editorial_timeline_第1集.json",
        json.dumps({"otio_path": "合成/第1集/_work/editorial_timeline.otio"}),
    )
    dry = catalog.migrate(tmp_path, line="n2d", apply=False)
    assert dry["applied"] == []
    assert (work / "timeline.json").exists()
    done = catalog.migrate(tmp_path, line="n2d", apply=True)
    assert done["status"] == "ready"
    assert (tmp_path / "生产数据" / "timelines" / "第1集" / "timeline.json").is_file()
    assert (tmp_path / "生产数据" / "views" / "rough_cut_preview_第1集.html").is_file()
    assert not zero.exists()
    sidecar = json.loads((tmp_path / "生产数据" / "editorial_timeline_第1集.json").read_text(encoding="utf-8"))
    assert sidecar["otio_path"] == "生产数据/timelines/第1集/editorial_timeline.otio"
    assert (tmp_path / "生产数据" / "artifact_catalog.json").is_file()


def test_migrate_removes_zero_voice_without_work_cache(tmp_path: Path) -> None:
    write(tmp_path / "_进度.md", "# progress")
    zero = tmp_path / "合成" / "第2集" / "配音" / "Clip9_voice.wav"
    write(zero, "")
    done = catalog.migrate(tmp_path, line="n2d", apply=True)
    assert any(row["action"] == "delete_zero_placeholder" for row in done["applied"])
    assert not zero.exists()
