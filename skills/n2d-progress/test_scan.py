from __future__ import annotations

import importlib.util
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
