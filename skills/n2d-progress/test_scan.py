from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path


SCRIPT = Path(__file__).with_name("scan.py")
spec = importlib.util.spec_from_file_location("scan", SCRIPT)
scan = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(scan)


def test_cross_cutting_glob_reports_episode_coverage(tmp_path: Path) -> None:
    (tmp_path / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | raw | 剧本改编 | 配音 | 分镜设计 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |",
                "| 第2集 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |",
                "| 第3集 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |",
            ]
        ),
        encoding="utf-8",
    )
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "score_第1集.json").write_text("{}", encoding="utf-8")

    out: list[str] = []
    scan.report(str(tmp_path), out)
    report = "\n".join(out)

    assert "自动审片评分(n2d-score) ◐1/3" in report
    assert "人审可视化(n2d-review-ui) ○0/3" in report


def test_findings_report_distinguishes_stale_from_active(tmp_path: Path) -> None:
    progress = tmp_path / "_进度.md"
    progress.write_text(
        "\n".join(
            [
                "| 集 | raw | 剧本改编 | 配音 | 分镜设计 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 1/2 | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )
    prod = tmp_path / "生产数据"
    prod.mkdir()
    old = prod / "gate_findings_image_第1集.json"
    old.write_text(
        json.dumps({"summary": {"severity": {"block": 1, "warn": 2}}, "findings": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    os.utime(old, (progress.stat().st_mtime - 10, progress.stat().st_mtime - 10))

    out: list[str] = []
    scan.report(str(tmp_path), out)
    report = "\n".join(out)

    assert "有过期 findings: block 1 / warn 2" in report
    assert "存在未解决的一致性 findings" not in report

    active = prod / "gate_findings_video_第1集.json"
    active.write_text(
        json.dumps({"findings": [{"severity": "warn", "message": "motion"}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    os.utime(active, (progress.stat().st_mtime + 10, progress.stat().st_mtime + 10))

    out = []
    scan.report(str(tmp_path), out)
    report = "\n".join(out)
    assert "当前 findings: block 0 / warn 1" in report
