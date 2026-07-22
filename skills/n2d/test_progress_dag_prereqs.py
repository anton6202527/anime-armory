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


# ── 防漂移守卫：progress.py 的 DAG 表必须与契约 PROGRESS_COLUMNS 同源 ──────────
# 架构法条「不要在别处手写另一张阶段表」的机检落地：_DAG_CORE_ORDER / _DAG_PREREQS
# 是 progress.py 手维护的第三张流程列表；契约新增/改列（如当年加 奇观连续性）时，
# 若忘了同步这里，DAG 审计会静默漏掉新列。以下把「记得改两处」变成 fail-closed 不变量。
def _flow_columns_from_contract():
    from n2d_schema import PROGRESS_COLUMNS  # 契约真值源
    # PROGRESS_COLUMNS 头两列是展示列 集/字数，其余是流程列，顺序即规范顺序。
    return [c for c in PROGRESS_COLUMNS if c not in ("集", "字数")]


def test_dag_core_order_matches_contract_progress_columns():
    assert progress._DAG_CORE_ORDER == _flow_columns_from_contract(), (
        "progress._DAG_CORE_ORDER 与契约 PROGRESS_COLUMNS 的流程列漂移了；"
        "改列必须同步两处（架构法条：不要在别处手写另一张阶段表）。"
    )


def test_dag_prereqs_reference_only_known_columns_in_order():
    order = progress._DAG_CORE_ORDER
    index = {c: i for i, c in enumerate(order)}
    for col, prereqs in progress._DAG_PREREQS.items():
        assert col in index, f"_DAG_PREREQS 键「{col}」不在流程列里"
        for prereq in prereqs:
            assert prereq in index, f"「{col}」的前驱「{prereq}」不在流程列里"
            # 前驱必须严格早于目标列，否则 DAG 有环/回指
            assert index[prereq] < index[col], (
                f"「{col}」的前驱「{prereq}」排在它之后，DAG 顺序非法"
            )


# ── 并发一致性守卫：校验必须在持 progress_lock 时运行（读校验与写入对同一快照原子）──
# 修复前 _verify_gate_receipt/_verify_dag_prereqs 在锁外先跑，与锁内写入之间存在 TOCTOU：
# 并发 worker/回滚可在两者之间改上游列 → 下游 ✅ 压非法上游。此测证「校验在锁内」。
def test_dag_verification_runs_while_holding_progress_lock(tmp_path, monkeypatch):
    import contextlib
    monkeypatch.delenv("N2D_PROGRESS_ALLOW_UNVERIFIED", raising=False)
    # 分镜设计 是非受闸列（gate_receipt 直接放行），DAG 前驱=剧本改编/bgm/封面/配音，全部置 ✅ 使写入成功
    write_progress(tmp_path, _cells(剧本改编="✅", bgm="✅", 封面="✅", 配音="✅"))

    state = {"held": False, "verified_under_lock": None}
    real_lock = progress.progress_lock

    @contextlib.contextmanager
    def tracking_lock(root, *a, **k):
        with real_lock(root, *a, **k) as x:
            state["held"] = True
            try:
                yield x
            finally:
                state["held"] = False

    real_verify = progress._verify_dag_prereqs

    def spy_verify(*a, **k):
        state["verified_under_lock"] = state["held"]  # 记录校验时锁是否已持有
        return real_verify(*a, **k)

    monkeypatch.setattr(progress, "progress_lock", tracking_lock)
    monkeypatch.setattr(progress, "_verify_dag_prereqs", spy_verify)

    progress.do_set(str(tmp_path), "第1集", "分镜设计", "✅")
    assert state["verified_under_lock"] is True  # 校验发生在持锁期间（原子读-改-写）
