"""cd skills/n2d-script/scripts && python -m pytest test_character_arc_ledger.py"""
import json
from pathlib import Path

import character_arc_ledger as ca


def test_is_earned_change():
    assert ca.is_earned_change([{"type": "失败"}, {"type": "转变"}])         # 先失败后转变
    assert not ca.is_earned_change([{"type": "转变"}])                       # 转变无铺垫
    assert ca.is_earned_change([{"type": "代价"}, {"type": "挣扎"}])         # 无转变里程碑→不评判
    assert ca.is_earned_change([])


def test_want_need_issue():
    assert ca.want_need_issue({"want": "复仇", "need": "放下执念"}) is None
    assert ca.want_need_issue({"want": "复仇", "need": ""}) == "missing"
    assert ca.want_need_issue({"want": "活着", "need": "活着"}) == "want_eq_need"


def test_audit_ledger_flags():
    ledger = {"characters": {
        "沈念": {"want": "复仇", "need": "", "arc_milestones": [{"type": "转变"}]},
        "柳娘子": {"want": "权力", "need": "认可", "arc_milestones": []},
    }}
    codes = {c for _s, c, _m in ca.audit_ledger(ledger)}
    assert "want_need_missing" in codes      # 沈念缺 need
    assert "unearned_change" in codes        # 沈念转变无铺垫
    assert "no_arc_registered" in codes      # 柳娘子无 arc


def test_audit_ledger_clean():
    ledger = {"characters": {
        "沈念": {"want": "复仇", "need": "放下执念",
                 "arc_milestones": [{"type": "失败"}, {"type": "挣扎"}, {"type": "转变"}]},
    }}
    findings = ca.audit_ledger(ledger)
    codes = {c for _s, c, _m in findings}
    assert "want_need_missing" not in codes
    assert "unearned_change" not in codes
    assert "no_arc_registered" not in codes


def test_scaffold_creates_ledger(tmp_path: Path):
    reg = tmp_path / "出图" / "共享" / "identity_registry.json"
    reg.parent.mkdir(parents=True)
    reg.write_text(json.dumps({"characters": [
        {"id": "CHAR_SHEN", "scope": "核心主角", "core": True},
        {"id": "CHAR_EXTRA", "scope": "路人"},
    ]}, ensure_ascii=False), encoding="utf-8")
    led = ca.scaffold(str(tmp_path))
    assert "CHAR_SHEN" in led["characters"]
    assert "CHAR_EXTRA" not in led["characters"]      # 非核心不入
    assert (tmp_path / "设定库" / "character_arc_ledger.json").exists()
