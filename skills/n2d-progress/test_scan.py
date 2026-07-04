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

    # 断言用稳定的 skill id + 覆盖标记，不耦合易变的中文 label（label 是契约单一真值源，
    # 改名/增删 skill 都不该让本测试变脆——它测的是“逐集 glob 产物按 N/M 计覆盖”这件事）。
    # score_第1集.json 存在 1/3 → ◐1/3；无 skill_update_plan → ○0/3（非前置、glob、0 命中）。
    assert "(n2d-score) ◐1/3" in report
    assert "(n2d-update) ○0/3" in report


def test_video_done_counts_complete_when_compose_not_opted_in(tmp_path: Path) -> None:
    (tmp_path / "_进度.md").write_text(
        "\n".join(
            [
                "| 集 | raw | 剧本改编 | 配音 | 分镜设计 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |",
                "|---|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ⬜ | ⬜ |",
            ]
        ),
        encoding="utf-8",
    )

    out: list[str] = []
    scan.report(str(tmp_path), out)
    report = "\n".join(out)

    assert "可选阶段: 合成/验收默认跳过" in report
    assert "主流程完成: 1/1" in report
    assert "前沿:" not in report


def test_one_broken_work_does_not_blank_whole_board(tmp_path, monkeypatch, capsys) -> None:
    # 仪表盘韧性：一部剧扫描抛非 OSError/ValueError 异常时，其余剧仍正常出报告，
    # 整块看板不能因一部坏剧而全空白。
    (tmp_path / "skills").mkdir()
    (tmp_path / "AGENTS.md").write_text("x", encoding="utf-8")
    line = tmp_path / "制漫剧"
    for name in ("好剧", "坏剧"):
        d = line / name
        d.mkdir(parents=True)
        (d / "_进度.md").write_text(
            "| 集 | raw | 剧本改编 |\n|---|---|---|\n| 第1集 | ✅ | ✅ |\n", encoding="utf-8"
        )

    real_report = scan.report

    def flaky_report(root, out):
        if str(root).endswith("坏剧"):
            raise RuntimeError("boom")
        real_report(root, out)

    monkeypatch.setattr(scan, "report", flaky_report)

    rc = scan.main(["--root", str(tmp_path)])
    captured = capsys.readouterr().out
    assert rc == 0
    assert "好剧" in captured                       # 正常剧仍出报告
    assert "扫描失败，跳过本剧" in captured           # 坏剧被隔离
    assert "RuntimeError: boom" in captured


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


def _progress_one_ep(tmp_path: Path) -> Path:
    progress = tmp_path / "_进度.md"
    progress.write_text(
        "\n".join(
            [
                "| 集 | raw | 剧本改编 | 配音 | 分镜设计 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 |",
                "|---|---|---|---|---|---|---|---|---|---|",
                "| 第1集 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |",
            ]
        ),
        encoding="utf-8",
    )
    return progress


def test_review_report_surfaced_with_score_verdict(tmp_path: Path) -> None:
    progress = _progress_one_ep(tmp_path)
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "score_第1集.json").write_text(
        json.dumps({"total_score": 53, "threshold": 85, "status": "fail"}, ensure_ascii=False),
        encoding="utf-8",
    )
    rep = tmp_path / "_质检_第1集.md"
    rep.write_text("# 质检报告\n\n生成时间：2026-06-13\n", encoding="utf-8")
    # 报告与评分都晚于进度 → 不应标 stale
    fresh = progress.stat().st_mtime + 10
    os.utime(rep, (fresh, fresh))
    os.utime(prod / "score_第1集.json", (fresh, fresh))

    out: list[str] = []
    scan.report(str(tmp_path), out)
    report = "\n".join(out)

    assert "质检结果:" in report
    assert "质检报告 _质检_第1集.md" in report
    assert "总分 53/85 ⚠️未过阈" in report
    assert "2026-06-13" in report
    assert "建议重审" not in report  # 未过期


def test_review_report_marked_stale_when_products_newer(tmp_path: Path) -> None:
    progress = _progress_one_ep(tmp_path)
    rep = tmp_path / "_质检_第1集.md"
    rep.write_text("生成时间：2026-06-01\n", encoding="utf-8")
    os.utime(rep, (progress.stat().st_mtime - 100, progress.stat().st_mtime - 100))

    out: list[str] = []
    scan.report(str(tmp_path), out)
    report = "\n".join(out)

    assert "质检报告 _质检_第1集.md" in report
    assert "结论可能过期，建议重审" in report


def test_score_fail_without_report_nags_for_review(tmp_path: Path) -> None:
    _progress_one_ep(tmp_path)
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "score_第1集.json").write_text(
        json.dumps({"total_score": 40, "threshold": 85, "status": "fail"}, ensure_ascii=False),
        encoding="utf-8",
    )

    out: list[str] = []
    scan.report(str(tmp_path), out)
    report = "\n".join(out)

    assert "无人审报告，建议跑 n2d-review" in report


def test_score_pass_without_report_is_quiet(tmp_path: Path) -> None:
    _progress_one_ep(tmp_path)
    prod = tmp_path / "生产数据"
    prod.mkdir()
    (prod / "score_第1集.json").write_text(
        json.dumps({"total_score": 92, "threshold": 85, "status": "pass"}, ensure_ascii=False),
        encoding="utf-8",
    )

    out: list[str] = []
    scan.report(str(tmp_path), out)
    report = "\n".join(out)

    assert "质检结果:" not in report  # pass + 无报告 → 不打扰
