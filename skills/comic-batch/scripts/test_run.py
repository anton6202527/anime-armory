from pathlib import Path
import importlib.util
import json
import sys


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


def test_traditional_off_still_keeps_name_as_required_editorial_contract(tmp_path: Path) -> None:
    (tmp_path / "_设置.md").write_text("- 传统原稿流程：关闭\n", encoding="utf-8")
    headers = list(batch.STAGES)

    stages = batch.effective_stages(tmp_path, headers)

    assert "缩略分镜" in stages
    assert "页面排版" in stages
    assert "原稿收尾" not in stages


def test_batch_stops_cleanly_at_name_draft_without_running_next_stage(tmp_path: Path, monkeypatch) -> None:
    chapter = "第1话"
    (tmp_path / "_设置.md").write_text("- 传统原稿流程：启用\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text(
        "| 话 | 源本/企划 | 漫画脚本 | 缩略分镜 | 页面排版 | 原稿收尾 | 出图包 | 出图 | 嵌字合成 | 审查 |\n"
        "|---|---|---|---|---|---|---|---|---|---|\n"
        f"| {chapter} | ✅ | ✅ | 🟡待签收 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |\n",
        encoding="utf-8",
    )
    name_path = tmp_path / "排版" / chapter / "name_board.json"
    name_path.parent.mkdir(parents=True)
    name_path.write_text(json.dumps({"workflow_status": "draft"}), encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(batch, "run_cmd", lambda cmd, cwd: calls.append(cmd) or 0)
    monkeypatch.setattr(sys, "argv", ["comic-batch", str(tmp_path), "--chapter", chapter])

    assert batch.main() == 0
    assert calls == []


def test_batch_checks_approved_artifact_before_syncing_stale_progress(tmp_path: Path, monkeypatch) -> None:
    chapter = "第1话"
    (tmp_path / "_设置.md").write_text("- 传统原稿流程：启用\n", encoding="utf-8")
    (tmp_path / "_进度.md").write_text(
        "| 话 | 源本/企划 | 漫画脚本 | 缩略分镜 | 页面排版 |\n"
        "|---|---|---|---|---|\n"
        f"| {chapter} | ✅ | ✅ | 🟡待签收 | ⬜ |\n",
        encoding="utf-8",
    )
    name_path = tmp_path / "排版" / chapter / "name_board.json"
    name_path.parent.mkdir(parents=True)
    name_path.write_text(json.dumps({"workflow_status": "approved"}), encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(batch, "run_cmd", lambda cmd, cwd: calls.append(cmd) or 0)
    monkeypatch.setattr(sys, "argv", ["comic-batch", str(tmp_path), "--chapter", chapter, "--max-steps", "1"])

    assert batch.main() == 0
    assert calls and "--check" in calls[0]
    assert "| 第1话 | ✅ | ✅ | ✅ | ⬜ |" in (tmp_path / "_进度.md").read_text(encoding="utf-8")
