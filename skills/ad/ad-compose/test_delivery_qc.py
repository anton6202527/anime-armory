# -*- coding: utf-8 -*-
"""delivery_qc·textless 无字版母版纪律单测。

行规：带烧录文字或多语言再版的成片必须配 textless 母版，否则每个语言版都要回炉重做 online。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import delivery_qc as dq  # noqa: E402


def _root(tmp_path, *, burned=0, locales=0):
    root = tmp_path / "ad"
    (root / "合规").mkdir(parents=True)
    if burned:
        (root / "合规" / "rendered_text_plan.json").write_text(json.dumps({
            "checks": [{"id": f"master:{i}", "text": "法律声明"} for i in range(burned)],
        }, ensure_ascii=False), encoding="utf-8")
    if locales:
        (root / "合规" / "locale_matrix.json").write_text(json.dumps({
            "locales": {f"loc{i}": {"language": f"l{i}"} for i in range(locales)},
        }, ensure_ascii=False), encoding="utf-8")
    return root


def _plan(*ids):
    return {"deliverables": [{"deliverable_id": i} for i in ids]}


def test_burned_text_without_textless_master_warns(tmp_path):
    root = _root(tmp_path, burned=3)
    findings = dq.textless_master_findings(root, _plan("master", "reframe_9x16"))

    assert len(findings) == 1
    assert findings[0]["code"] == "textless_master_missing"
    assert findings[0]["severity"] == "warn"


def test_multi_locale_without_textless_master_warns(tmp_path):
    root = _root(tmp_path, locales=3)
    assert dq.textless_master_findings(root, _plan("master"))


def test_textless_deliverable_or_no_trigger_is_quiet(tmp_path):
    root = _root(tmp_path, burned=2, locales=3)
    # 任意字段（id/kind/label/path）带 textless/无字 都算已交
    assert not dq.textless_master_findings(root, _plan("master", "master_textless"))
    assert not dq.textless_master_findings(
        root, {"deliverables": [{"deliverable_id": "m2", "label": "无字版母版"}]})

    # 没烧字 + 单语言：不要求
    quiet = _root(tmp_path / "b", locales=1)
    assert not dq.textless_master_findings(quiet, _plan("master"))
    # 空交付计划不判（其它检查管缺计划）
    assert not dq.textless_master_findings(root, {"deliverables": []})
