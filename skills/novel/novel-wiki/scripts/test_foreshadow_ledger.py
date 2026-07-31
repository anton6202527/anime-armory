# -*- coding: utf-8 -*-
import importlib.util, os
def _fl():
    import foreshadow_ledger; return foreshadow_ledger
"""Tests for foreshadow_ledger.py — 伏笔台账确定性部分（超期判定 + 回收率）。

Run from this directory:
    cd skills/novel/novel-wiki/scripts && python3 -m pytest test_foreshadow_ledger.py
"""
import os
import json

import foreshadow_ledger as fl


# ── plant / payoff / drop 状态机 + JSON 完整性 ─────────────────────────────────
def test_plant_assigns_id_and_pending():
    data = {"kind": fl.KIND, "seeds": []}
    seed = fl.plant(data, "沈念捡到半块断剑", planted_chapter=5, expected_payoff_chapter=50)
    assert seed["id"] == "SEED_001"
    assert seed["status"] == "pending"
    assert seed["planted_chapter"] == 5
    assert seed["expected_payoff_chapter"] == 50
    assert seed["actual_payoff_chapter"] is None


def test_plant_auto_id_avoids_collision():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "a", 1, 10, seed_id="SEED_001")
    fl.plant(data, "b", 2, 12)  # auto -> should not collide
    ids = [s["id"] for s in data["seeds"]]
    assert ids == ["SEED_001", "SEED_002"]


def test_plant_rejects_duplicate_id():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "a", 1, 10, seed_id="SEED_001")
    try:
        fl.plant(data, "b", 2, 12, seed_id="SEED_001")
        assert False, "expected duplicate id to raise"
    except ValueError:
        pass


def test_plant_rejects_bad_importance():
    data = {"kind": fl.KIND, "seeds": []}
    try:
        fl.plant(data, "a", 1, 10, importance="超级重要")
        assert False
    except ValueError:
        pass


def test_payoff_sets_resolved_with_chapter_and_evidence():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "断剑", 5, 50, seed_id="SEED_001")
    seed = fl.payoff(data, "SEED_001", actual_payoff_chapter=48, evidence="断剑认主")
    assert seed["status"] == "resolved"
    assert seed["actual_payoff_chapter"] == 48
    assert seed["evidence"] == "断剑认主"


def test_payoff_partial():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "断剑", 5, 50, seed_id="SEED_001")
    seed = fl.payoff(data, "SEED_001", partial=True)
    assert seed["status"] == "partially_resolved"


def test_payoff_unknown_id_raises():
    data = {"kind": fl.KIND, "seeds": []}
    try:
        fl.payoff(data, "SEED_999")
        assert False
    except KeyError:
        pass


def test_drop_marks_dropped():
    data = {"kind": fl.KIND, "seeds": []}
    fl.plant(data, "废线索", 3, 20, seed_id="SEED_001")
    seed = fl.drop(data, "SEED_001", reason="作者弃用")
    assert seed["status"] == "dropped"
    assert seed["evidence"] == "作者弃用"


# ── 超期判定（确定性核心） ──────────────────────────────────────────────────────
def test_overdue_true_past_expected_plus_grace():
    seed = {"status": "pending", "expected_payoff_chapter": 50}
    # grace 默认 5 -> 章 56 才算超期，55 不算
    assert fl.is_overdue(seed, through_chapter=56, grace=5) is True
    assert fl.is_overdue(seed, through_chapter=55, grace=5) is False


def test_overdue_false_when_resolved():
    seed = {"status": "resolved", "expected_payoff_chapter": 10}
    assert fl.is_overdue(seed, through_chapter=100) is False


def test_overdue_false_without_expected_chapter():
    # 没有预期回收章 -> 脚本不臆测，绝不机检超期
    seed = {"status": "pending", "expected_payoff_chapter": None}
    assert fl.is_overdue(seed, through_chapter=999) is False


def test_partially_resolved_can_be_overdue():
    seed = {"status": "partially_resolved", "expected_payoff_chapter": 20}
    assert fl.is_overdue(seed, through_chapter=30, grace=5) is True


# ── 回收率（确定性核心） ────────────────────────────────────────────────────────
def test_payoff_rate_basic():
    seeds = [
        {"status": "resolved"},
        {"status": "resolved"},
        {"status": "pending"},
        {"status": "pending"},
    ]
    r = fl.payoff_rate(seeds)
    assert r["rate"] == 0.5  # 2 resolved / 4 effective
    assert r["effective_total"] == 4
    assert r["resolved"] == 2


def test_payoff_rate_dropped_excluded_from_denominator():
    seeds = [
        {"status": "resolved"},
        {"status": "pending"},
        {"status": "dropped"},  # 不进分母
    ]
    r = fl.payoff_rate(seeds)
    assert r["rate"] == 0.5  # 1 / 2 effective, dropped excluded
    assert r["dropped"] == 1
    assert r["effective_total"] == 2


def test_payoff_rate_partial_counts_half():
    seeds = [{"status": "resolved"}, {"status": "partially_resolved"}]
    r = fl.payoff_rate(seeds)
    assert r["rate"] == 0.75  # (1 + 0.5) / 2


def test_payoff_rate_none_when_no_effective():
    assert fl.payoff_rate([])["rate"] is None
    assert fl.payoff_rate([{"status": "dropped"}])["rate"] is None  # 全作废 -> 不谎报 0/0


# ── scan 聚合 + 严重度分级 ─────────────────────────────────────────────────────
def test_scan_flags_high_importance_overdue_as_blocking():
    data = {"kind": fl.KIND, "seeds": [
        {"id": "SEED_001", "description": "关键身世", "status": "pending",
         "planted_chapter": 5, "expected_payoff_chapter": 30, "importance": "critical"},
        {"id": "SEED_002", "description": "小道具", "status": "pending",
         "planted_chapter": 6, "expected_payoff_chapter": 30, "importance": "low"},
    ]}
    report = fl.scan(data, through_chapter=40, grace=5)
    assert report["overdue_count"] == 2
    assert report["blocking"] == 1  # only critical is 阻断级
    sev = {o["id"]: o["severity"] for o in report["overdue"]}
    assert sev["SEED_001"] == "阻断级"
    assert sev["SEED_002"] == "建议级"


def test_scan_no_overdue_within_window():
    data = {"kind": fl.KIND, "seeds": [
        {"id": "SEED_001", "description": "x", "status": "pending",
         "planted_chapter": 5, "expected_payoff_chapter": 50, "importance": "high"},
    ]}
    report = fl.scan(data, through_chapter=52, grace=5)
    assert report["overdue_count"] == 0


# ── round-trip 落盘 ───────────────────────────────────────────────────────────
def test_load_save_roundtrip(tmp_path):
    proj = tmp_path / "书"
    (proj / "设定").mkdir(parents=True)
    data = fl.load_ledger(str(proj))
    fl.plant(data, "断剑", 5, 50)
    fl.save_ledger(str(proj), data)
    path = os.path.join(str(proj), "设定", "foreshadowing_ledger.json")
    assert os.path.exists(path)
    with open(path, encoding="utf-8") as f:
        reloaded = json.load(f)
    assert reloaded["kind"] == fl.KIND
    assert reloaded["seeds"][0]["id"] == "SEED_001"


# ── 自动抽取的「伏笔候选」（auto_extracted/confirmed=False）行为 ──────────────────
def _candidate(seed_id="AUTO_001", planted=3):
    return {"id": seed_id, "description": "殊不知此乃后话", "status": "pending",
            "planted_chapter": planted, "expected_payoff_chapter": None,
            "actual_payoff_chapter": None, "importance": "medium",
            "linked_entities": [], "evidence": None,
            "auto_extracted": True, "confirmed": False, "anchor": "殊不知"}


def test_candidate_not_in_payoff_denominator():
    rate = fl.payoff_rate([_candidate(), _candidate("AUTO_002")])
    # 两条都是未确认候选 → 无有效伏笔，rate None，candidates 计 2
    assert rate["rate"] is None
    assert rate["effective_total"] == 0
    assert rate["candidates"] == 2


def test_candidate_never_overdue():
    cand = _candidate()
    cand["expected_payoff_chapter"] = 5  # 即便有预期回收章
    assert fl.is_overdue(cand, through_chapter=100, grace=0) is False


def test_confirmed_seed_still_counts():
    cand = _candidate()
    confirmed = dict(cand, confirmed=True, expected_payoff_chapter=5, importance="high")
    rate = fl.payoff_rate([cand, confirmed])
    assert rate["effective_total"] == 1  # 只有确认的进分母
    assert rate["candidates"] == 1
    assert fl.is_overdue(confirmed, through_chapter=100, grace=5) is True


def test_analyze_ran_true_with_only_candidates(tmp_path):
    proj = str(tmp_path)
    os.makedirs(os.path.join(proj, "设定"))
    data = {"kind": fl.KIND, "seeds": [_candidate()]}
    fl.save_ledger(proj, data)
    rep = fl.analyze(proj, through_chapter=50)
    assert rep["ran"] is True
    assert rep["candidate_count"] == 1
    assert rep["blocking"] == 0  # 候选永不阻断
    assert any(a.get("kind") == "foreshadow_candidate" for a in rep["alerts"])


def test_confirm_flips_candidate_to_real_seed():
    data = {"kind": fl.KIND, "seeds": [_candidate()]}
    seed = fl.confirm(data, "AUTO_001", expected_payoff_chapter=20, importance="high")
    assert seed["confirmed"] is True
    assert seed["expected_payoff_chapter"] == 20 and seed["importance"] == "high"
    # 确认后即进分母
    assert fl.payoff_rate(data["seeds"])["effective_total"] == 1


def test_manual_plant_is_confirmed():
    data = {"kind": fl.KIND, "seeds": []}
    seed = fl.plant(data, "手动埋点", 5, 50)
    assert seed["confirmed"] is True and seed["auto_extracted"] is False


def test_never_fired_at_finale_flags_undated_gun():
    # 已确认但从没设 expected_payoff_chapter 的伏笔：is_overdue 永远 False，
    # 终章反查必须抓住它（契诃夫之枪的反向检查）。
    fl = _fl()
    data = {"kind": fl.KIND, "seeds": [
        {"id": "SEED_001", "description": "少年袖中藏着的半枚玉佩", "status": "pending",
         "planted_chapter": 3, "expected_payoff_chapter": None, "importance": "high", "confirmed": True},
    ]}
    # 未到终章 → 不报
    assert fl.never_fired_at_finale(data["seeds"], through_chapter=40, target_chapters=90) == []
    # 抵达终章 → high 伏笔上膛未击发 = 阻断级
    hit = fl.never_fired_at_finale(data["seeds"], through_chapter=90, target_chapters=90)
    assert len(hit) == 1 and hit[0]["severity"] == "阻断级" and hit[0]["kind"] == "foreshadow_never_fired"


def test_never_fired_does_not_double_report_overdue():
    fl = _fl()
    seeds = [{"id": "SEED_002", "description": "被夺走的兵符", "status": "pending",
              "planted_chapter": 3, "expected_payoff_chapter": 10, "importance": "high", "confirmed": True}]
    # 到终章：这条已被 is_overdue 命中（10+grace<90），never_fired 不重复计
    assert fl.never_fired_at_finale(seeds, through_chapter=90, target_chapters=90) == []


def test_never_fired_ignores_resolved_and_unconfirmed():
    fl = _fl()
    seeds = [
        {"id": "S1", "status": "resolved", "planted_chapter": 3, "expected_payoff_chapter": None,
         "importance": "high", "confirmed": True},
        {"id": "S2", "status": "pending", "planted_chapter": 3, "expected_payoff_chapter": None,
         "importance": "high", "confirmed": False},  # 未确认候选
    ]
    assert fl.never_fired_at_finale(seeds, through_chapter=90, target_chapters=90) == []


def test_empty_ledger_with_mature_manuscript_reports_gap(tmp_path):
    # 空转报缺：正文 ≥10 章但台账零登记 → 显式建议级报缺（没数据≠没问题），不再安静 skipped
    import os
    d = os.path.join(str(tmp_path), "章节")
    os.makedirs(d, exist_ok=True)
    for i in range(1, 13):
        with open(os.path.join(d, f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
            f.write("正文")
    res = fl.analyze(str(tmp_path))
    assert res["ran"] is True and res["blocking"] == 0
    assert res["alerts"][0]["type"] == "foreshadow_ledger_empty"


def test_empty_ledger_short_manuscript_still_skips(tmp_path):
    import os
    d = os.path.join(str(tmp_path), "章节")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "第01章.md"), "w", encoding="utf-8") as f:
        f.write("正文")
    res = fl.analyze(str(tmp_path))
    assert res["ran"] is False


# ── 内容级信号：提醒断档 / 提及过密 / 空降回收 ────────────────────────────────
def _chapters(n, text="平平无奇的正文。"):
    return [(i, f"# 第{i}章\n{text}") for i in range(1, n + 1)]


def _silent_seed():
    return {"id": "SEED_001", "description": "沈念捡到半块断剑", "status": "pending",
            "confirmed": True, "planted_chapter": 1, "expected_payoff_chapter": 20,
            "importance": "high", "linked_entities": ["断剑"]}


def test_reminder_gap_flags_long_silent_seed():
    alerts = fl.scan_mentions([_silent_seed()], _chapters(15), through_chapter=15)
    assert len(alerts) == 1
    a = alerts[0]
    assert a["kind"] == "foreshadow_reminder_gap" and a["severity"] == "建议级"
    assert a["silent_span"] == 14  # end=min(20,15)=15，span=15-1


def test_reminder_gap_quiet_when_mentioned():
    chapters = _chapters(15)
    chapters[7] = (8, "# 第8章\n他又摸了摸袖中那截断剑。")
    assert fl.scan_mentions([_silent_seed()], chapters, through_chapter=15) == []


def test_reminder_gap_quiet_below_span_threshold():
    seed = dict(_silent_seed(), expected_payoff_chapter=8)  # span=7 < 10
    assert fl.scan_mentions([seed], _chapters(15), through_chapter=15) == []


def test_reminder_gap_skips_unconfirmed_and_resolved():
    seeds = [dict(_silent_seed(), confirmed=False),
             dict(_silent_seed(), id="SEED_002", status="resolved")]
    assert fl.scan_mentions(seeds, _chapters(15), through_chapter=15) == []


def test_reminder_gap_skips_when_no_chapters_in_window():
    # 窗口内一章都没写出来（正文只有第 1 章）→ 无从判提及，不臆测
    assert fl.scan_mentions([_silent_seed()], _chapters(1), through_chapter=15) == []


def test_overexposed_flags_dense_mentions():
    chapters = [(i, f"# 第{i}章\n断剑在鞘中嗡鸣。") for i in range(1, 16)]
    alerts = fl.scan_mentions([_silent_seed()], chapters, through_chapter=15)
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "foreshadow_overexposed"
    assert alerts[0]["severity"] == "建议级"


def test_airdrop_flags_unplanted_reveal_entity(tmp_path):
    proj = str(tmp_path)
    os.makedirs(os.path.join(proj, "章节"))
    os.makedirs(os.path.join(proj, "设定"))
    for i, body in ((1, "少年在山下砍柴。"), (2, "少年进城赶集。"),
                    (3, "血魄珠悬于祭坛之上，血魄珠红光大盛，众人拜服于血魄珠前。")):
        with open(os.path.join(proj, "章节", f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(f"# 第{i}章\n{body}")
    with open(os.path.join(proj, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({"kind": "novel_scene_cards", "scenes": [
            {"id": "SC003-01", "chapter": 3, "scene_no": 1,
             "reveal_or_payoff": "血魄珠现世认主"},
        ]}, f, ensure_ascii=False)
    chapters = [(1, "少年在山下砍柴。"), (2, "少年进城赶集。"),
                (3, "血魄珠悬于祭坛之上，血魄珠红光大盛，众人拜服于血魄珠前。")]
    alerts = fl.scan_payoff_setup(proj, chapters)
    assert len(alerts) == 1
    a = alerts[0]
    assert a["kind"] == "payoff_without_setup" and a["severity"] == "建议级"
    assert "血魄珠" in a["terms"] and a["chapter"] == 3


def test_airdrop_quiet_when_entity_planted_earlier(tmp_path):
    proj = str(tmp_path)
    os.makedirs(os.path.join(proj, "设定"))
    with open(os.path.join(proj, "设定", "scene_cards.json"), "w", encoding="utf-8") as f:
        json.dump({"scenes": [{"id": "SC003-01", "chapter": 3, "scene_no": 1,
                               "reveal_or_payoff": "血魄珠现世认主"}]}, f, ensure_ascii=False)
    chapters = [(1, "传说中的血魄珠早已失落。"), (2, "少年进城赶集。"),
                (3, "血魄珠悬于祭坛之上，血魄珠红光大盛。")]
    assert fl.scan_payoff_setup(proj, chapters) == []


def test_airdrop_quiet_without_scene_cards(tmp_path):
    assert fl.scan_payoff_setup(str(tmp_path), [(1, "正文"), (2, "正文")]) == []


def test_analyze_surfaces_content_alerts(tmp_path):
    proj = str(tmp_path)
    os.makedirs(os.path.join(proj, "章节"))
    os.makedirs(os.path.join(proj, "设定"))
    for i in range(1, 16):
        with open(os.path.join(proj, "章节", f"第{i:02d}章.md"), "w", encoding="utf-8") as f:
            f.write(f"# 第{i}章\n平平无奇的正文。")
    fl.save_ledger(proj, {"kind": fl.KIND, "seeds": [_silent_seed()]})
    rep = fl.analyze(proj)
    assert rep["ran"] is True
    assert rep["content_alert_count"] == 1
    assert any(a.get("kind") == "foreshadow_reminder_gap" for a in rep["alerts"])
    assert rep["blocking"] == 0  # 内容级信号恒不阻断
