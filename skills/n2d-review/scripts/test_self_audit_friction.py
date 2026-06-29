#!/usr/bin/env python3
"""cd skills/n2d-review/scripts && python -m pytest test_self_audit_friction.py

流程自审消费现场摩擦信号的回归测试：作品 `生产数据/优化信号.jsonl` 里的信号
应逐簇并进 self_audit 差距清单（loc=该改哪个 skill、sev 透传、block 让 audit 退 1）。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).with_name("self_audit.py")
spec = importlib.util.spec_from_file_location("self_audit", SCRIPT)
self_audit = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(self_audit)

REPO_ROOT = SCRIPT.resolve().parents[3]  # …/anime-arsenal


def _write_signals(work_root: Path, records):
    d = work_root / "生产数据"
    d.mkdir(parents=True, exist_ok=True)
    with (d / "优化信号.jsonl").open("w", encoding="utf-8") as f:
        for r in records:
            base = {"kind": "n2d_friction_signal", "version": 1}
            base.update(r)
            f.write(json.dumps(base, ensure_ascii=False) + "\n")


def _friction_findings(report):
    return [f for f in report["findings"] if f["dim"] == "现场摩擦信号"]


def test_no_work_arg_skips_friction(tmp_path):
    report = self_audit.audit(REPO_ROOT)  # 不传 work → 不污染仓库级自审
    assert _friction_findings(report) == []
    assert report["work_root"] == ""


def test_empty_backlog_reports_info(tmp_path):
    report = self_audit.audit(REPO_ROOT, tmp_path)
    fr = _friction_findings(report)
    assert len(fr) == 1 and fr[0]["sev"] == "info"


def test_signals_surface_as_gap_rows(tmp_path):
    _write_signals(tmp_path, [
        {"ts": "2026-06-27T01:00:00+00:00", "skill": "n2d-voice", "signal_kind": "workaround",
         "severity": "warn", "what": "12/12 句静音占位", "episode": "第1集",
         "evidence": "合成/第1集/配音/_占位说明.md", "proposed": "缺后端早探活"},
        {"ts": "2026-06-27T02:00:00+00:00", "skill": "n2d-voice", "signal_kind": "workaround",
         "severity": "block", "what": "再次全集占位", "proposed": "修适配层"},
        {"ts": "2026-06-27T03:00:00+00:00", "skill": "n2d-image", "signal_kind": "defect",
         "severity": "warn", "what": "定妆脸漂", "proposed": "注入脸锚"},
    ])
    report = self_audit.audit(REPO_ROOT, tmp_path)
    fr = _friction_findings(report)
    # 两个簇：n2d-voice/workaround（block，2 条）+ n2d-image/defect（warn，1 条）
    assert len(fr) == 2
    voice = next(f for f in fr if f["loc"].startswith("n2d-voice"))
    assert voice["sev"] == "block"            # 簇取最高严重度
    assert "2 条" in voice["msg"]
    assert voice["suggestion"] == "修适配层"   # 最近一条的 proposed
    # block 现场信号让整体自审退出码=1（可进 CI/批量门）
    assert report["counts"]["block"] >= 1


def test_garbage_backlog_does_not_crash(tmp_path):
    d = tmp_path / "生产数据"
    d.mkdir(parents=True, exist_ok=True)
    (d / "优化信号.jsonl").write_text("not json\n{}\n", encoding="utf-8")
    report = self_audit.audit(REPO_ROOT, tmp_path)
    fr = _friction_findings(report)
    assert len(fr) == 1 and fr[0]["sev"] == "info"  # 无有效信号 → info
