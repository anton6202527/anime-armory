from pathlib import Path
import importlib.util
import json


MODULE_PATH = Path(__file__).with_name("run.py")
SPEC = importlib.util.spec_from_file_location("comic_batch_run", MODULE_PATH)
assert SPEC and SPEC.loader
batch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(batch)


def test_chapter_images_ready_requires_every_job_and_file(tmp_path: Path) -> None:
    jobs_path = tmp_path / "出图" / "第1话" / "prompt" / "panel_jobs.json"
    jobs_path.parent.mkdir(parents=True)
    panel = tmp_path / "出图" / "第1话" / "panels" / "P001.png"
    panel.parent.mkdir(parents=True)
    panel.write_bytes(b"png")
    jobs_path.write_text(
        json.dumps(
            {
                "jobs": [
                    {"panel_id": "P001", "status": "ready", "result_path": "出图/第1话/panels/P001.png"},
                    {"panel_id": "P002", "status": "planned", "result_path": ""},
                ]
            }
        ),
        encoding="utf-8",
    )

    assert batch.chapter_images_ready(tmp_path, "第1话") is False

    second = tmp_path / "出图" / "第1话" / "panels" / "P002.png"
    second.write_bytes(b"png")
    payload = json.loads(jobs_path.read_text(encoding="utf-8"))
    payload["jobs"][1].update(status="ready", result_path="出图/第1话/panels/P002.png")
    jobs_path.write_text(json.dumps(payload), encoding="utf-8")

    assert batch.chapter_images_ready(tmp_path, "第1话") is True
