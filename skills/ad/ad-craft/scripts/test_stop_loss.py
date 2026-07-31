# -*- coding: utf-8 -*-
"""广告生成止损审计（stop_loss）单测。

盯三条纪律：
  ① 审不是门——findings 只 warn/info，summary.block 恒 0（止损决定归人）；
  ② 空账显式 no_evidence，不静默绿灯；
  ③ submission 事件不算生成次数（提交≠产出，重抽率只数 generation）。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stop_loss as sl  # noqa: E402


def _events(root: Path, rows):
    path = root / "生产数据" / "production_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _gen(stage, asset, credits=10):
    return {"ts": "2026-07-17T00:00:00+00:00", "stage": stage, "event": "generation",
            "generation": {"asset": asset, "credit_count": credits}}


def test_empty_ledger_is_explicit_no_evidence(tmp_path):
    report = sl.build(tmp_path)
    assert report["summary"]["block"] == 0
    assert [f["code"] for f in report["findings"]] == ["no_evidence"]


def test_redraw_rate_and_worst_asset_flagged(tmp_path):
    _events(tmp_path, [
        _gen("image", "出图/S1.png"), _gen("image", "出图/S1.png"),
        _gen("image", "出图/S2.png"), _gen("image", "出图/S2.png"),
        _gen("image", "出图/S3.png"),
        # S4 抽了 5 次 > MAX_ATTEMPTS=4
        *[_gen("image", "出图/S4.png") for _ in range(5)],
    ])
    report = sl.build(tmp_path)

    codes = [f["code"] for f in report["findings"]]
    assert "redraw_rate_high" in codes      # 3/4 资产重抽 > 35%
    assert "asset_attempts_high" in codes   # S4×5 > 4
    assert report["summary"]["block"] == 0
    assert all(f["severity"] in ("warn", "info") for f in report["findings"])
    assert report["stages"]["image"]["worst_asset"]["attempts"] == 5


def test_submissions_do_not_count_as_attempts_and_credits_cap(tmp_path):
    _events(tmp_path, [
        {"ts": "t", "stage": "video", "event": "submission",
         "generation": {"asset": "出视频/C1.mp4", "credit_count": 50}},
        _gen("video", "出视频/C1.mp4", credits=50),
    ])
    report = sl.build(tmp_path)
    assert report["stages"]["video"]["worst_asset"]["attempts"] == 1  # submission 不计
    assert not [f for f in report["findings"] if f["code"] == "redraw_rate_high"]

    capped = sl.build(tmp_path, max_credits=60)  # 100 credits > 60
    assert any(f["code"] == "credits_spend_high" for f in capped["findings"])


def test_open_qc_block_while_generating_warns(tmp_path):
    _events(tmp_path, [_gen("image", "出图/S1.png")])
    qc = tmp_path / "出图" / "分镜" / "product_qc.json"
    qc.parent.mkdir(parents=True, exist_ok=True)
    qc.write_text(json.dumps({"summary": {"block": 2, "warn": 0}}), encoding="utf-8")
    report = sl.build(tmp_path)
    assert any(f["code"] == "qc_block_open" for f in report["findings"])


def test_write_report_atomic_and_strict_exit(tmp_path):
    _events(tmp_path, [_gen("image", "出图/S1.png")])
    assert sl.main([str(tmp_path), "--write"]) == 0
    assert (tmp_path / "生产数据" / "ad_stop_loss.json").is_file()
    assert (tmp_path / "生产数据" / "ad_stop_loss.md").is_file()
