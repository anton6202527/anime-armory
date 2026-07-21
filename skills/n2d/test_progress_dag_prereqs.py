#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G11 回归：do_set 回写「完成态 ✅」前必须满足 STAGE_GRAPH DAG 前驱（fail-closed）。

audit-dag 只能事后抓乱序；这组测试守住回写时的前移判据：上游未完成 → 拒绝置下游 ✅，
逃生口 N2D_PROGRESS_ALLOW_UNVERIFIED=1 必须留痕 waiver（code=dag_prereq_unsatisfied）。

Run: cd skills/n2d && python3 -m pytest test_progress_dag_prereqs.py
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import progress  # noqa: E402

HEADER = (
    "| 集 | 字数 | raw | 剧本改编 | bgm | 封面 | 配音 | 分镜设计 | 素材清单 | 字幕中 | 字幕英 |"
    " 奇观连续性 | 出图prompt | 出图 | 视频prompt | 视频 | 成片 | 验收 |"
)
SEP = "|---|---:|" + "---|" * 16


def write_progress(root, row_cells):
    """row_cells: raw→验收 共 16 列的值列表。"""
    line = "| 第1集 | 800 | " + " | ".join(row_cells) + " |"
    (root / "_进度.md").write_text("\n".join([HEADER, SEP, line]), encoding="utf-8")


def _cells(**overrides):
    cols = ["raw", "剧本改编", "bgm", "封面", "配音", "分镜设计", "素材清单", "字幕中",
            "字幕英", "奇观连续性", "出图prompt", "出图", "视频prompt", "视频", "成片", "验收"]
    base = {c: "⬜" for c in cols}
    base.update({"raw": "✅", "字幕英": "—", "奇观连续性": "—"})
    base.update(overrides)
    return [base[c] for c in cols]


def test_refuses_downstream_done_when_prereq_missing(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_PROGRESS_ALLOW_UNVERIFIED", raising=False)
    # 出图 ⬜ 时置 视频prompt=✅ → 乱序，必须拒绝（视频prompt 非受闸列，只有 DAG 校验拦得住）
    write_progress(tmp_path, _cells(剧本改编="✅", bgm="✅", 封面="✅", 配音="✅",
                                    分镜设计="✅", 素材清单="✅", 字幕中="✅", 出图prompt="✅"))
    with pytest.raises(SystemExit) as ei:
        progress.do_set(str(tmp_path), "第1集", "视频prompt", "✅")
    assert ei.value.code == 2


def test_partial_progress_not_blocked(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_PROGRESS_ALLOW_UNVERIFIED", raising=False)
    # 数字进度 3/9 不是完成态，不受 DAG 校验约束（付费过程中的中间回写不拦）
    write_progress(tmp_path, _cells())
    progress.do_set(str(tmp_path), "第1集", "视频prompt", "3/9")  # 不应 raise
    assert "3/9" in (tmp_path / "_进度.md").read_text(encoding="utf-8")


def test_satisfied_prereqs_allow_done(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_PROGRESS_ALLOW_UNVERIFIED", raising=False)
    # 前驱齐（含 奇观连续性=— 的 na 态）→ 出图prompt ✅ 正常放行
    write_progress(tmp_path, _cells(剧本改编="✅", bgm="✅", 封面="✅", 配音="✅",
                                    分镜设计="✅", 素材清单="✅", 字幕中="✅"))
    progress.do_set(str(tmp_path), "第1集", "出图prompt", "✅")
    assert "| ✅ | ⬜ | ⬜ |" in (tmp_path / "_进度.md").read_text(encoding="utf-8")


def test_override_writes_dag_waiver(tmp_path, monkeypatch):
    monkeypatch.setenv("N2D_PROGRESS_ALLOW_UNVERIFIED", "1")
    write_progress(tmp_path, _cells(剧本改编="✅", bgm="✅", 封面="✅", 配音="✅",
                                    分镜设计="✅", 素材清单="✅", 字幕中="✅", 出图prompt="✅"))
    progress.do_set(str(tmp_path), "第1集", "视频prompt", "✅")  # 不应 raise
    led = tmp_path / "生产数据" / "progress_unverified_waivers.jsonl"
    assert led.exists(), "DAG override 必须留痕欠债"
    rec = json.loads(led.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert rec["code"] == "dag_prereq_unsatisfied"
    assert rec["column"] == "视频prompt"


def test_clearing_cell_never_blocked(tmp_path, monkeypatch):
    monkeypatch.delenv("N2D_PROGRESS_ALLOW_UNVERIFIED", raising=False)
    # 回退/清空（⬜）永不受 DAG 校验拦截
    write_progress(tmp_path, _cells(剧本改编="✅"))
    progress.do_set(str(tmp_path), "第1集", "剧本改编", "⬜")
    assert "| 第1集 | 800 | ✅ | ⬜ |" in (tmp_path / "_进度.md").read_text(encoding="utf-8")
