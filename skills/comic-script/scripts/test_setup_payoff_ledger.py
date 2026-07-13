"""setup_payoff_ledger 单测。运行：cd skills/comic-script/scripts && python -m pytest test_setup_payoff_ledger.py"""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).with_name("setup_payoff_ledger.py")
spec = importlib.util.spec_from_file_location("setup_payoff_ledger", SCRIPT)
sp = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(sp)


def _panel(pid, dialogue=None, narration="", sfx="", art_notes=""):
    return {"panel_id": pid, "dialogue": dialogue or [], "narration": narration,
            "sfx": sfx, "art_notes": art_notes}


def test_detect_explicit_setup_from_marker():
    panels = [_panel("P001", narration="他袖中露出半枚玉佩，暗藏玄机，这是一处伏笔。")]
    setups = sp.detect_setups(panels, "第1话")
    assert len(setups) == 1
    assert setups[0]["status"] == "open"
    assert setups[0]["setup_chapter"] == "第1话"
    assert setups[0]["payoff_chapter"] == ""  # 交编剧填


def test_weak_signal_is_candidate_not_open():
    panels = [_panel("P001", dialogue=[{"text": "他的真实身份到底是谁？"}])]
    setups = sp.detect_setups(panels, "第1话")
    cands = sp.detect_auto_candidates(panels, "第1话")
    assert setups == []                       # 无显式标记 → 不进 open
    assert cands and cands[0]["status"] == "candidate"


def test_placeholder_lines_ignored():
    panels = [_panel("P001", narration="待补：这里放一个伏笔")]
    assert sp.detect_setups(panels, "第1话") == []


def test_merge_never_overwrites_filled_payoff():
    existing = [{"desc": "半枚玉佩", "setup_chapter": "第1话", "payoff_chapter": "第9话", "status": "open"}]
    new = [{"desc": "半枚玉佩", "setup_chapter": "第1话", "payoff_chapter": "", "status": "open"}]
    merged = sp.merge_candidates(existing, new)
    assert len(merged) == 1
    assert merged[0]["payoff_chapter"] == "第9话"   # 已填的不被空覆盖


def test_seed_from_development_pack_normalizes_planted_status():
    strat = {"foreshadowing_ledger": [
        {"setup_id": "FSH_001", "setup": "神秘令牌", "planted_chapter": "第1话", "status": "planted"},
        {"setup_id": "FSH_002", "setup": "待补", "planted_chapter": "第2话"},  # 占位应被跳过
    ]}
    seeded = sp.seed_from_development_pack(strat)
    assert len(seeded) == 1
    assert seeded[0]["status"] == "open"            # planted → open
    assert seeded[0]["from_development_pack"] is True


def test_audit_setup_unlogged_is_must():
    detected = [{"desc": "半枚玉佩", "setup_chapter": "第1话"}]
    findings = sp.audit_chapter("第1话", detected, ledger_pairs=[])
    assert any(f["code"] == "setup_unlogged" and f["severity"] == "must" for f in findings)


def test_audit_payoff_unfilled_is_must():
    detected = [{"desc": "半枚玉佩", "setup_chapter": "第1话"}]
    ledger = [{"desc": "半枚玉佩", "setup_chapter": "第1话", "payoff_chapter": "", "status": "open"}]
    findings = sp.audit_chapter("第1话", detected, ledger)
    assert any(f["code"] == "payoff_unfilled" for f in findings)


def test_audit_payoff_overdue_warns_on_later_chapter():
    ledger = [{"desc": "半枚玉佩", "setup_chapter": "第1话", "payoff_chapter": "第3话", "status": "open"}]
    findings = sp.audit_chapter("第5话", detected=[], ledger_pairs=ledger)
    assert any(f["code"] == "payoff_overdue" and f["severity"] == "warn" for f in findings)


def test_audit_payoff_before_setup_warns():
    ledger = [{"desc": "半枚玉佩", "setup_chapter": "第5话", "payoff_chapter": "第2话", "status": "open"}]
    findings = sp.audit_chapter("第5话", detected=[], ledger_pairs=ledger)
    assert any(f["code"] == "payoff_before_setup" for f in findings)


def test_audit_done_setup_not_flagged():
    ledger = [{"desc": "半枚玉佩", "setup_chapter": "第1话", "payoff_chapter": "第3话", "status": "done"}]
    findings = sp.audit_chapter("第5话", detected=[], ledger_pairs=ledger)
    assert not any(f["code"] in ("payoff_overdue", "payoff_unfilled") for f in findings)


def test_ongoing_setup_not_unfilled():
    detected = [{"desc": "长线之谜", "setup_chapter": "第1话"}]
    ledger = [{"desc": "长线之谜", "setup_chapter": "第1话", "payoff_chapter": "", "status": "ongoing"}]
    findings = sp.audit_chapter("第1话", detected, ledger)
    assert not any(f["code"] == "payoff_unfilled" for f in findings)


def test_end_to_end_build_and_gate(tmp_path):
    root = tmp_path
    ch = root / "脚本" / "第1话"
    ch.mkdir(parents=True)
    import json
    (ch / "panel_script.json").write_text(json.dumps({"panels": [
        {"panel_id": "P001", "narration": "他袖中那半枚玉佩暗藏玄机，成谜。"},
    ]}, ensure_ascii=False), encoding="utf-8")
    rc = sp.main([str(root), "第1话", "--write", "--strict"])
    assert rc == 1                                  # 检出显式伏笔但账本未登记 → strict block
    ledger = json.loads((root / "设定库" / "setup_payoff_ledger.json").read_text(encoding="utf-8"))
    assert ledger["pairs"] and ledger["pairs"][0]["status"] == "open"
    # 填了兑现话后再审：应放行
    ledger["pairs"][0]["payoff_chapter"] = "第6话"
    (root / "设定库" / "setup_payoff_ledger.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    rc2 = sp.main([str(root), "第1话", "--strict"])
    assert rc2 == 0
