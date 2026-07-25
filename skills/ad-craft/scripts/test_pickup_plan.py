# -*- coding: utf-8 -*-
"""补拍任务包（pickup_plan）单测。

盯三条纪律：① QC fail 逐条变任务且 blocking 排前；② 超次数任务升级为改分镜（补拍救不了
的回炉重拍）；③ advisory 底线——summary.block 恒 0，QC 报告缺失只 info 不臆造任务。
"""
import json

import pickup_plan as pp


def _write(root, rel, payload):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _write_events(root, rows):
    path = root / "生产数据" / "production_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")


def _product_qc(findings):
    return {"kind": "product_qc", "summary": {"block": 0, "warn": len(findings)}, "findings": findings}


def test_no_qc_reports_info_only(tmp_path):
    report = pp.build(tmp_path)
    assert report["summary"]["block"] == 0
    assert report["tasks"] == []
    assert any(f["code"] == "no_qc_reports" for f in report["findings"])


def test_qc_findings_become_tasks_blocking_first(tmp_path):
    _write(tmp_path, "出图/分镜/product_qc.json", _product_qc([
        {"severity": "warn", "code": "product_dhash", "shot": "镜头03", "msg": "产品 dHash 漂移"},
    ]))
    _write(tmp_path, "出视频/分镜/video_qc.json", {
        "summary": {"block": 1, "warn": 0},
        "findings": [{"severity": "block", "code": "clip_presence", "clip": "镜头01",
                      "msg": "已提交远端但尚未回收下载"}],
    })
    report = pp.build(tmp_path)
    assert report["summary"]["block"] == 0          # advisory：任务包自己不产 block
    assert report["summary"]["tasks"] == 2
    assert report["tasks"][0]["blocking"] is True   # blocking 排前
    assert "回收" in report["tasks"][0]["action"]    # clip_presence 路由到回收处置
    assert any(f["code"] == "pickup_backlog_open" for f in report["findings"])


def test_escalation_after_max_attempts(tmp_path):
    _write(tmp_path, "出图/分镜/product_qc.json", _product_qc([
        {"severity": "warn", "code": "product_dhash", "shot": "镜头02首帧", "msg": "疑产品漂移"},
    ]))
    _write_events(tmp_path, [
        {"stage": "image", "event": "generation", "generation": {"asset": "镜头02首帧", "credit_count": 3}}
        for _ in range(6)
    ])
    report = pp.build(tmp_path)
    task = next(t for t in report["tasks"] if t["subject"] == "镜头02首帧")
    assert task["escalated"] is True and "改分镜" in task["action"]
    assert any(f["code"] == "pickup_escalated" for f in report["findings"])


def test_backend_findings_route_to_override_or_redo(tmp_path):
    _write(tmp_path, "出图/分镜/product_qc.json", _product_qc([
        {"severity": "warn", "code": "image_output_backend_mismatch", "shot": "镜头05",
         "msg": "已落图来自 Dreamina 与现行后端策略冲突"},
    ]))
    report = pp.build(tmp_path)
    assert "image_backend_override" in report["tasks"][0]["action"]  # 二选一处置，不许悬置


def test_warn_only_backlog_is_info(tmp_path):
    _write(tmp_path, "出图/分镜/product_qc.json", _product_qc([
        {"severity": "warn", "code": "brand_color", "shot": "镜头01", "msg": "品牌色 ΔE 偏离"},
    ]))
    report = pp.build(tmp_path)
    assert any(f["code"] == "pickup_warn_only" and f["severity"] == "info" for f in report["findings"])
    assert not any(f["code"] == "pickup_backlog_open" for f in report["findings"])
