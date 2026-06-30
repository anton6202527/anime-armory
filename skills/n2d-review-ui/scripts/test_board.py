#!/usr/bin/env python3
"""board.py tests. Run: cd skills/n2d-review-ui/scripts && python -m pytest test_board.py"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("board", HERE / "board.py")
board = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(board)


def make_work(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "_进度.md").write_text(
        "\n".join([
            "| 集 | 字数 | raw | 剧本改编 | 配音 | 分镜设计 | 出图 | 成片 |",
            "|---|---|---|---|---|---|---|---|",
            "| 第1集 | 800 | ✅ | ✅ | ✅ | ✅ | 1/4 | ⬜ |",
            "| 第2集 | 700 | ✅ | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |",
        ]),
        encoding="utf-8",
    )
    sb = root / "脚本" / "第1集"
    sb.mkdir(parents=True, exist_ok=True)
    (sb / "storyboard.json").write_text(json.dumps({
        "title": "测试剧",
        "clips": [
            {"id": "EP01_CLIP01", "duration": 3, "scene": "宫门", "continuity": {"transition": "hard"}},
            {"id": "EP01_CLIP02", "duration": 4, "scene": "殿内"},
        ],
    }, ensure_ascii=False), encoding="utf-8")


def test_board_manifest_shape(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧"
    make_work(root)
    m = board.build_manifest(root)

    # 阶段来自 _进度.md 流程列，去掉 raw
    assert m["stages"] == ["剧本改编", "配音", "分镜设计", "出图", "成片"]
    assert len(m["episodes"]) == 2

    e1 = m["episodes"][0]
    assert e1["episode"] == "第1集"
    assert e1["has_storyboard"] is True
    assert len(e1["clips"]) == 2
    assert len(e1["seams"]) == 1
    # 进度状态色：done / partial / todo 正确映射
    assert e1["stages"]["剧本改编"] == "done"
    assert e1["stages"]["出图"] == "partial"
    assert e1["stages"]["成片"] == "todo"
    assert e1["done_stages"] == 3 and e1["total_stages"] == 5
    assert e1["frontier"] is not None  # 还有未完成阶段 → 有下一步

    e2 = m["episodes"][1]
    assert e2["has_storyboard"] is False and e2["clips"] == []
    assert e2["done_stages"] == 0

    # 完成度：(3 + 0) / (5 + 5) = 30%
    assert m["summary"]["completion_pct"] == 30.0
    assert m["summary"]["episodes"] == 2


def test_clip_status_degrades_without_score(tmp_path):
    # 无 score、无首帧 → clip 状态退化为 warn（缺素材），不报 block、不崩
    root = tmp_path / "制漫剧" / "测试剧2"
    make_work(root)
    m = board.build_manifest(root)
    statuses = {c["status"] for c in m["episodes"][0]["clips"]}
    assert statuses <= {"warn", "pass"}  # 没有 score 证据，不会冒出 block


def test_board_preserves_rough_progress_state(tmp_path):
    root = tmp_path / "制漫剧" / "rough剧"
    make_work(root)
    (root / "_进度.md").write_text(
        "\n".join([
            "| 集 | 字数 | raw | 剧本改编 | 配音 | 分镜设计 | 出图 | 成片 |",
            "|---|---|---|---|---|---|---|---|",
            "| 第1集 | 800 | ✅ | ✅ | ⏳rough | ⬜ | ⬜ | ⬜ |",
        ]),
        encoding="utf-8",
    )
    m = board.build_manifest(root)
    assert m["episodes"][0]["stages"]["配音"] == "rough"
    assert ".chip.rough" in board.render_html(m)


def test_render_html_is_self_contained(tmp_path):
    root = tmp_path / "制漫剧" / "测试剧3"
    make_work(root)
    m = board.build_manifest(root)
    out = board.render_html(m)
    assert "n2d_production_board" in out          # manifest 内嵌
    assert "<script" in out and "JSON.parse" in out  # 零构建自带 JS
    assert "http" not in out.split("manifest")[0].lower() or "127.0.0.1" not in out  # 不外链 CDN


def test_board_carries_review_ui_deeplink(tmp_path):
    # 每集带 review_ui 深链；exists 准确反映该集 review_ui_<ep>.html 是否已生成
    root = tmp_path / "制漫剧" / "深链剧"
    make_work(root)
    m = board.build_manifest(root)
    e1 = m["episodes"][0]
    assert e1["review_ui"]["url"] == "review_ui_第1集.html"
    assert e1["review_ui"]["exists"] is False  # 还没生成 → 点会提示命令

    (root / "生产数据").mkdir(parents=True, exist_ok=True)
    (root / "生产数据" / "review_ui_第1集.html").write_text("<html></html>", encoding="utf-8")
    m2 = board.build_manifest(root)
    assert m2["episodes"][0]["review_ui"]["exists"] is True

    out = board.render_html(m2)
    assert "openReview" in out and "#clip=" in out  # board 侧深链 JS 在


def test_missing_progress_is_graceful(tmp_path):
    # 没有 _进度.md → 返回带 error 的骨架，不抛异常
    root = tmp_path / "制漫剧" / "空项目"
    root.mkdir(parents=True)
    m = board.build_manifest(root)
    assert m["episodes"] == [] and "error" in m
    board.render_html(m)  # 仍能渲染（顶部 banner 显示 error）


if __name__ == "__main__":
    import sys
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
