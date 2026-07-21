# -*- coding: utf-8 -*-
"""knowledge_sentry.py 单测：账本操作幂等、结构对账、揭示超期、泄密候选、analyze 契约。"""
import json
import os

import pytest

import knowledge_sentry as ks


def _mk_project(tmp_path, chapters=None):
    root = tmp_path / "proj"
    (root / "设定").mkdir(parents=True)
    if chapters:
        cdir = root / "章节"
        cdir.mkdir()
        for idx, text in chapters.items():
            (cdir / f"第{idx:02d}章.md").write_text(f"# 第{idx}章 标题\n\n{text}", encoding="utf-8")
    return str(root)


def _base_ledger():
    data = {"kind": ks.KIND, "secrets": []}
    ks.add_secret(data, "沈念是前朝公主", importance="critical",
                  holders=[{"name": "沈念", "learned_chapter": 1}],
                  reader_knows_since=1, planned_reveal_chapter=40,
                  tell_keywords=["前朝公主"], secret_id="SECRET_001")
    return data


# ── 账本操作 ─────────────────────────────────────────────────────────────────
def test_add_learn_suspect_reveal_roundtrip(tmp_path):
    root = _mk_project(tmp_path)
    data = _base_ledger()
    ks.learn(data, "SECRET_001", "王敦", 12, how="偷听")
    ks.suspect(data, "SECRET_001", "皇帝", 22)
    ks.save_ledger(root, data)
    loaded = ks.load_ledger(root)
    s = ks.find_secret(loaded["secrets"], "SECRET_001")
    assert [h["name"] for h in s["holders"]] == ["沈念", "王敦"]
    assert s["suspects"][0]["name"] == "皇帝"
    ks.reveal(loaded, "SECRET_001", 40)
    assert ks.find_secret(loaded["secrets"], "SECRET_001")["public_since"] == 40


def test_learn_is_idempotent_and_clears_suspect():
    data = _base_ledger()
    ks.suspect(data, "SECRET_001", "王敦", 8)
    ks.learn(data, "SECRET_001", "王敦", 12)
    ks.learn(data, "SECRET_001", "王敦", 15)  # 幂等：不重复登记
    s = data["secrets"][0]
    assert sum(1 for h in s["holders"] if h["name"] == "王敦") == 1
    assert all(x["name"] != "王敦" for x in s["suspects"])


def test_suspect_rejects_existing_holder():
    data = _base_ledger()
    with pytest.raises(ValueError):
        ks.suspect(data, "SECRET_001", "沈念", 3)


def test_auto_id_skips_used():
    data = _base_ledger()
    s2 = ks.add_secret(data, "另一条秘密")
    assert s2["id"] == "SECRET_002"


# ── 结构对账 ─────────────────────────────────────────────────────────────────
def test_learned_after_public_conflict():
    data = _base_ledger()
    ks.reveal(data, "SECRET_001", 30)
    ks.learn(data, "SECRET_001", "李嬷嬷", 35)
    alerts = ks.ledger_conflicts(data["secrets"])
    kinds = [a["kind"] for a in alerts]
    assert "learned_after_public" in kinds
    assert all(a["severity"] == "建议级" for a in alerts)


def test_holder_dead_before_learned_cross_wiki():
    data = _base_ledger()
    ks.learn(data, "SECRET_001", "老仆", 20)
    alerts = ks.ledger_conflicts(data["secrets"], death_chapters={"老仆": 15})
    assert any(a["kind"] == "holder_dead_before_learned" for a in alerts)


# ── 揭示超期 ─────────────────────────────────────────────────────────────────
def test_reveal_overdue_blocking_for_critical():
    data = _base_ledger()  # planned 40, critical
    alerts = ks.reveal_overdue(data["secrets"], through_chapter=50, grace=5)
    assert alerts and alerts[0]["severity"] == "阻断级"
    assert alerts[0]["overdue_by"] == 10


def test_reveal_overdue_respects_grace_and_public():
    data = _base_ledger()
    assert ks.reveal_overdue(data["secrets"], through_chapter=44, grace=5) == []
    ks.reveal(data, "SECRET_001", 43)
    assert ks.reveal_overdue(data["secrets"], through_chapter=60, grace=5) == []


# ── 泄密候选 ─────────────────────────────────────────────────────────────────
def test_leak_candidate_before_any_anchor():
    data = {"kind": ks.KIND, "secrets": []}
    ks.add_secret(data, "李慕白是内鬼", importance="high",
                  holders=[{"name": "李慕白", "learned_chapter": 10}],
                  tell_keywords=["内鬼李慕白"], secret_id="SECRET_001")
    texts = {5: "众人议论纷纷，有人低声说内鬼李慕白早有异动。", 12: "内鬼李慕白终于露出马脚。"}
    alerts = ks.leak_candidates(data["secrets"], texts)
    assert len(alerts) == 1
    a = alerts[0]
    assert a["chapter"] == 5 and a["severity"] == "建议级" and a["confidence"] == "heuristic"


def test_leak_scan_skips_secret_without_anchor_or_keywords():
    data = {"kind": ks.KIND, "secrets": []}
    ks.add_secret(data, "无锚点秘密", tell_keywords=["天机"])  # 无 holders/reader/public
    ks.add_secret(data, "无关键词秘密", holders=[{"name": "甲", "learned_chapter": 3}])
    assert ks.leak_candidates(data["secrets"], {1: "天机不可泄露"}) == []


# ── analyze 契约 ─────────────────────────────────────────────────────────────
def test_analyze_skipped_without_ledger(tmp_path):
    root = _mk_project(tmp_path, chapters={1: "普通开局，无揭示题材。"})
    res = ks.analyze(root)
    assert res["ran"] is False and "无知情账" in res["skipped"]


def test_analyze_hints_missing_ledger_on_reveal_topic(tmp_path):
    chapters = {i: "他一直瞒着众人，马甲眼看要掉马。" for i in range(1, 4)}
    root = _mk_project(tmp_path, chapters=chapters)
    res = ks.analyze(root)
    assert res["ran"] is True
    assert res["alerts"][0]["kind"] == "knowledge_ledger_missing"
    assert res["blocking"] == 0


def test_analyze_full_report(tmp_path):
    root = _mk_project(tmp_path, chapters={
        3: "有人隐约提到前朝公主的旧事。",
        50: "风声更紧了。",
    })
    data = _base_ledger()  # 读者/沈念第1章即知 → 第3章不算泄密；planned 40 超期
    ks.save_ledger(root, data)
    res = ks.analyze(root)
    assert res["ran"] is True
    kinds = [a["kind"] for a in res["alerts"]]
    assert "reveal_overdue" in kinds
    assert "secret_leak_candidate" not in kinds
    assert res["blocking"] == 1  # critical 超期


# ── 写章包注入 ───────────────────────────────────────────────────────────────
def test_packet_section_lists_open_secrets(tmp_path):
    root = _mk_project(tmp_path)
    data = _base_ledger()
    ks.learn(data, "SECRET_001", "王敦", 12)
    data["secrets"][0]["wrong_beliefs"] = [{"name": "皇帝", "believes": "沈念是逃难孤女", "since_chapter": 1}]
    ks.save_ledger(root, data)
    sec = ks.packet_section(root, 20)
    assert "知情面提醒" in sec and "SECRET_001" in sec
    assert "王敦(第12章知)" in sec and "误信" in sec


def test_packet_section_filters_by_stage_names(tmp_path):
    root = _mk_project(tmp_path)
    data = _base_ledger()
    ks.add_secret(data, "北疆军情", holders=[{"name": "赵将军", "learned_chapter": 2}],
                  secret_id="SECRET_002")
    ks.save_ledger(root, data)
    sec = ks.packet_section(root, 20, names_on_stage=["赵将军"])
    assert "SECRET_002" in sec and "SECRET_001" not in sec


def test_packet_section_empty_after_all_public(tmp_path):
    root = _mk_project(tmp_path)
    data = _base_ledger()
    ks.reveal(data, "SECRET_001", 10)
    ks.save_ledger(root, data)
    assert ks.packet_section(root, 20) == ""
