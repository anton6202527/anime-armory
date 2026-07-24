# -*- coding: utf-8 -*-
"""
test for wiki_builder + logic_sentry.
Run from this directory:
    cd skills/novel-wiki/scripts && python3 -m pytest test_logic_sentry.py
"""
import os
import json
import wiki_builder
import logic_sentry


def _mk_project(tmp_path):
    proj = tmp_path / "书"
    (proj / "设定").mkdir(parents=True)
    (proj / "章节").mkdir(parents=True)
    (proj / "设定" / "角色卡.md").write_text(
        "# 角色卡\n\n## 王敦\n身份：剑修\n\n## 李慕白\n身份：宿敌\n",
        encoding="utf-8")
    (proj / "章节" / "第01章.md").write_text("王敦提剑上山，李慕白在崖边等他。", encoding="utf-8")
    (proj / "章节" / "第02章.md").write_text("一剑落下，李慕白当场身亡，尸身坠崖。", encoding="utf-8")
    return proj


def test_parse_character_names(tmp_path):
    proj = _mk_project(tmp_path)
    names = wiki_builder.parse_character_names(str(proj))
    assert "王敦" in names and "李慕白" in names


def test_build_wiki_detects_death(tmp_path):
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    assert wiki["李慕白"]["status"] == "deceased"
    assert wiki["李慕白"]["death_chapter"] == 2
    assert wiki["李慕白"].get("auto") is True
    # 王敦 仍存活
    assert wiki["王敦"]["status"] == "active"
    assert wiki["王敦"]["last_seen_chapter"] == 1


def test_flashback_not_counted_as_death(tmp_path):
    proj = tmp_path / "书2"
    (proj / "设定").mkdir(parents=True)
    (proj / "章节").mkdir(parents=True)
    (proj / "设定" / "角色卡.md").write_text("## 李慕白\n", encoding="utf-8")
    (proj / "章节" / "第01章.md").write_text("他回忆起李慕白身亡那夜的雨。", encoding="utf-8")
    wiki = wiki_builder.build_wiki(str(proj))
    # 闪回语境不应判死
    assert wiki["李慕白"]["status"] == "active"


def test_neighbor_death_not_misattributed(tmp_path):
    """'李慕白当场身亡。王敦默立' —— 王敦在死亡词附近但非他死，不得误判。"""
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    assert wiki["李慕白"]["status"] == "deceased"
    assert wiki["王敦"]["status"] == "active"   # 关键：邻近他人之死不上身


def test_deceased_reactivation_alert(tmp_path):
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    # 第3章李慕白又活动 → 仍被检出，但 B10：关键词扫正文=脆弱启发式，降为建议级·不硬阻断。
    alerts = logic_sentry.scan_chapter(wiki, "李慕白冷笑着挥剑反击。", 3)
    hit = [a for a in alerts if a["type"] == "deceased_reactivation"]
    assert hit, "复活仍应被检出为候选"
    assert hit[0]["severity"] == "建议级"
    assert hit[0]["confidence"] == "heuristic"
    assert hit[0]["downgraded_from"] == "阻断级"


def test_reactivation_suppressed_by_flashback(tmp_path):
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    alerts = logic_sentry.scan_chapter(wiki, "王敦想起李慕白当年的笑。", 3)
    assert not any(a["type"] == "deceased_reactivation" for a in alerts)


def test_no_alert_before_death_chapter(tmp_path):
    proj = _mk_project(tmp_path)
    wiki = wiki_builder.build_wiki(str(proj))
    # 死亡章(2)之前/当章不应报复活
    alerts = logic_sentry.scan_chapter(wiki, "李慕白还活着。", 1)
    assert not any(a["type"] == "deceased_reactivation" for a in alerts)


def test_discarded_item_reuse():
    wiki = {"清月剑": {"category": "item", "status": "shattered", "last_update": 5}}
    alerts = logic_sentry.scan_chapter(wiki, "他举起清月剑，再次催动剑气。", 8)
    # B10：动词邻近扫正文=脆弱启发式，检出但降为建议级（不再硬阻断 post_write）。
    hit = [a for a in alerts if a["type"] == "discarded_item_reuse"]
    assert hit and hit[0]["severity"] == "建议级" and hit[0]["confidence"] == "heuristic"
    # 仅提及不使用 → 不报
    alerts2 = logic_sentry.scan_chapter(wiki, "清月剑的碎片散落一地。", 8)
    assert not any(a["type"] == "discarded_item_reuse" for a in alerts2)


def test_rebuild_clears_stale_auto_death(tmp_path):
    """重扫时未确认的 auto 死亡先清回 active，让修正传播；人工确认状态保留。"""
    proj = _mk_project(tmp_path)
    stale = {
        "王敦": {"category": "character", "status": "deceased", "death_chapter": 2, "auto": True},
        "李慕白": {"category": "character", "status": "deceased", "auto": False, "location": "断魂崖"},
    }
    wiki = wiki_builder.build_wiki(str(proj), existing=stale)
    assert wiki["王敦"]["status"] == "active"          # 旧误报被纠正
    assert wiki["李慕白"]["status"] == "deceased"        # 人工确认保留
    assert wiki["李慕白"]["location"] == "断魂崖"          # 人工字段不丢


def test_clean_chapter_no_alerts():
    wiki = {"王敦": {"category": "character", "status": "active"}}
    assert logic_sentry.scan_chapter(wiki, "王敦继续赶路。", 10) == []


# ── NG1：数值/事实漂移（年龄）─────────────────────────────────────
def test_cjk_to_int():
    cases = {"17": 17, "十七": 17, "二十": 20, "三十五": 35, "一百": 100,
             "十": 10, "廿": 20, "九": 9, "二十八": 28}
    for tok, exp in cases.items():
        assert logic_sentry.cjk_to_int(tok) == exp, f"{tok} -> {logic_sentry.cjk_to_int(tok)}"
    assert logic_sentry.cjk_to_int("abc") is None


def test_load_numeric_anchors(tmp_path):
    proj = tmp_path / "书"
    (proj / "设定").mkdir(parents=True)
    (proj / "设定" / "角色卡.md").write_text(
        "# 角色卡\n\n## 沈念\n年龄：18\n身份：贵妃\n\n## 王敦\n年方十七\n", encoding="utf-8")
    anchors = logic_sentry.load_numeric_anchors(str(proj))
    assert anchors == {"沈念": 18, "王敦": 17}


def test_numeric_drift_flagged():
    a = {"沈念": 18}
    alerts = logic_sentry.scan_numeric_drift(a, "沈念今年十七岁了，依旧美貌。", 5)
    assert alerts and alerts[0]["type"] == "numeric_drift_age"
    assert alerts[0]["canonical_age"] == 18 and alerts[0]["found_age"] == 17


def test_numeric_drift_timeskip_exempt():
    a = {"沈念": 18}
    assert logic_sentry.scan_numeric_drift(a, "多年后，沈念已二十五岁。", 9) == []


def test_numeric_drift_consistent_no_flag():
    a = {"沈念": 18}
    assert logic_sentry.scan_numeric_drift(a, "沈念十八岁，正值芳华。", 3) == []


def test_numeric_drift_other_character_age_not_misattributed():
    # 别的角色（宫女）的年龄在锚点角色名邻句出现，不得算到锚点角色头上。
    a = {"沈念": 18}
    assert logic_sentry.scan_numeric_drift(a, "沈念走进大殿。许多宫女不过十五岁。", 3) == []


def test_numeric_drift_via_scan_chapter(tmp_path):
    # 端到端：scan_chapter 接 numeric_anchors 透传。
    wiki = {"沈念": {"category": "character", "status": "active"}}
    alerts = logic_sentry.scan_chapter(
        wiki, "沈念年方十六，却已掌权。", 7, numeric_anchors={"沈念": 18})
    assert any(a["type"] == "numeric_drift_age" for a in alerts)


def test_no_anchors_no_numeric_alerts():
    # 无年龄锚点（角色卡没声明）→ 优雅跳过，不臆造。
    assert logic_sentry.scan_numeric_drift({}, "沈念今年十七岁。", 5) == []


# ── N1 世界规则违背（阻断级）──

def test_world_rule_forbidden_after():
    world = {"major_changes": [{"event": "断剑彻底熔毁", "chapter": 40,
                                "forbidden_after": ["祭起断剑", "断剑出鞘"]}]}
    alerts = logic_sentry.scan_world_rules(world, "他祭起断剑，寒光大盛。", 55)
    assert any(a["type"] == "world_rule_violation" and a["severity"] == "阻断级" for a in alerts)


def test_world_rule_forbidden_before():
    world = {"major_changes": [{"event": "瞬移禁制被破", "chapter": 42,
                                "forbidden_before": ["瞬移"]}]}
    # 第30章就瞬移 → 用了第42章才解锁的设定
    alerts = logic_sentry.scan_world_rules(world, "他一个瞬移闪到敌后。", 30)
    assert any(a["type"] == "world_rule_violation" for a in alerts)


def test_world_rule_freetext_only_skips():
    # 只给自由文本 impact、无 forbidden_* → 不臆造，跳过
    world = {"major_changes": [{"event": "x", "impact": "禁术流出", "chapter": 10}]}
    assert logic_sentry.scan_world_rules(world, "禁术流出江湖。", 20) == []


def test_world_rule_respects_chapter_window():
    world = {"major_changes": [{"event": "e", "chapter": 40, "forbidden_after": ["断剑"]}]}
    # 第30章（早于确立章）不应被 forbidden_after 命中
    assert logic_sentry.scan_world_rules(world, "断剑在手。", 30) == []


# ── N2 关系温度计（建议级）──

def _matrix(hist, pair="沈念|王敦"):
    return {"matrix": {pair: {"temperature": hist[-1]["temperature"], "history": hist}}}


def test_relationship_flip_detected():
    m = _matrix([{"chapter": 40, "temperature": 70}, {"chapter": 48, "temperature": 20}])
    alerts = logic_sentry.scan_relationship_flips(m, "两人寻常对话，并无波澜。", 48)
    assert any(a["type"] == "relationship_flip" and a["delta"] == 50 for a in alerts)


def test_relationship_flip_exempt_by_turning_point():
    m = _matrix([{"chapter": 40, "temperature": 70}, {"chapter": 48, "temperature": 20}])
    # 本章有"背叛"重大转折 → 豁免
    assert logic_sentry.scan_relationship_flips(m, "原来是他背叛在先！", 48) == []


def test_relationship_flip_small_swing_ok():
    m = _matrix([{"chapter": 40, "temperature": 50}, {"chapter": 48, "temperature": 30}])
    assert logic_sentry.scan_relationship_flips(m, "平淡。", 48) == []


def test_relationship_flip_only_on_landing_chapter():
    m = _matrix([{"chapter": 40, "temperature": 70}, {"chapter": 48, "temperature": 20}])
    # 当前章 ≠ 最新一笔章 → 不报
    assert logic_sentry.scan_relationship_flips(m, "平淡。", 50) == []


def test_relationship_flip_no_history_skips():
    assert logic_sentry.scan_relationship_flips({"matrix": {"a|b": {"temperature": 10}}}, "x", 5) == []


# ── N2b 动态关系图（从 state_delta 增量构图 + 突变无铺垫·可阻断）──

def _graph(pair, hist):
    return {"matrix": {pair: {"history": hist, "labels": []}}}


def test_normalize_pair_order_invariant():
    assert logic_sentry._normalize_pair("乙↔甲") == logic_sentry._normalize_pair("甲↔乙")
    assert logic_sentry._normalize_pair({"a": "甲", "b": "乙"}) == ("乙", "甲")


def test_build_relationship_graph_from_state_delta(tmp_path):
    d = tmp_path / "审稿"
    d.mkdir()
    (d / "state_delta_第03章.json").write_text(json.dumps(
        {"relationship_changes": [{"pair": "甲↔乙", "temperature": 60, "label": "并肩"}]}),
        encoding="utf-8")
    (d / "state_delta_第07章.json").write_text(json.dumps(
        {"relationship_changes": [{"pair": "乙↔甲", "temperature": -50}]}), encoding="utf-8")
    g = logic_sentry.build_relationship_graph(str(tmp_path))
    key = "↔".join(logic_sentry._normalize_pair("甲↔乙"))
    hist = g["matrix"][key]["history"]
    assert [h["chapter"] for h in hist] == [3, 7]  # 跨章累积、对序归一合并
    assert hist[1]["temperature"] == -50


def test_break_blocking_on_sign_flip_without_setup():
    g = _graph("甲↔乙", [{"chapter": 3, "temperature": 60},
                         {"chapter": 7, "temperature": -60}])
    alerts = logic_sentry.detect_relationship_breaks(g, chapter_texts={7: "两人照常吃饭。"},
                                                     total_chapters=20)
    assert any(a["type"] == "relationship_break" and a["severity"] == "阻断级" for a in alerts)


def test_break_setup_in_bridge_chapter_exempts():
    g = _graph("甲↔乙", [{"chapter": 3, "temperature": 60},
                         {"chapter": 7, "temperature": -60}])
    # 铺垫落在桥接的第 5 章正文，而非跳变章 → 豁免（图驱动比逐章强在这里）
    alerts = logic_sentry.detect_relationship_breaks(
        g, chapter_texts={5: "那一夜的背叛埋下祸根。", 7: "照常。"}, total_chapters=20)
    assert alerts == []


def test_break_label_on_change_exempts():
    g = _graph("甲↔乙", [{"chapter": 3, "temperature": 60},
                         {"chapter": 7, "temperature": -60, "label": "决裂收场"}])
    assert logic_sentry.detect_relationship_breaks(g, total_chapters=20) == []


def test_break_final_chapter_downgrades_to_advisory():
    g = _graph("甲↔乙", [{"chapter": 18, "temperature": 60},
                         {"chapter": 20, "temperature": -60}])
    alerts = logic_sentry.detect_relationship_breaks(g, chapter_texts={20: "照常。"},
                                                     total_chapters=20)
    assert alerts and all(a["severity"] == "建议级" for a in alerts)  # 终章高潮豁免阻断


def test_break_small_swing_ignored():
    g = _graph("甲↔乙", [{"chapter": 3, "temperature": 50},
                         {"chapter": 7, "temperature": 25}])
    assert logic_sentry.detect_relationship_breaks(g, total_chapters=20) == []


# ── N3 张力账本 ──

def test_hook_stale_high_urgency_overdue():
    led = {"unresolved_hooks": [{"id": "h1", "question": "谁下的毒？",
                                 "introduced_in_chapter": 3, "urgency": "high"}]}
    alerts = logic_sentry.scan_tension(led, "正文。", 15)  # 15-3=12 > 10
    assert any(a["type"] == "hook_stale" and a["severity"] == "建议级" for a in alerts)


def test_hook_not_overdue_ok():
    led = {"unresolved_hooks": [{"id": "h1", "introduced_in_chapter": 3, "urgency": "high"}]}
    assert logic_sentry.scan_tension(led, "x", 10) == []  # 10-3=7 ≤ 10


def test_hook_resolved_skipped():
    led = {"unresolved_hooks": [{"id": "h1", "introduced_in_chapter": 3,
                                 "urgency": "high", "status": "resolved"}]}
    assert logic_sentry.scan_tension(led, "x", 30) == []


def test_promise_broken_is_blocking():
    led = {"reader_promises": [{"id": "p1", "promise": "初雪前杀王",
                                "deadline_event": "初雪降临"}]}
    alerts = logic_sentry.scan_tension(led, "这一夜，初雪降临，王却还活着。", 60)
    assert any(a["type"] == "promise_broken" and a["severity"] == "阻断级" for a in alerts)


def test_promise_kept_not_flagged():
    led = {"reader_promises": [{"id": "p1", "promise": "x", "deadline_event": "初雪降临",
                               "status": "fulfilled"}]}
    assert logic_sentry.scan_tension(led, "初雪降临。", 60) == []


def test_tension_fatigue_three_low():
    led = {"chapter_tension_curve": [{"chapter": 8, "tension_score": 4},
                                     {"chapter": 9, "tension_score": 3},
                                     {"chapter": 10, "tension_score": 2}]}
    alerts = logic_sentry.scan_tension(led, "x", 10)
    assert any(a["type"] == "tension_fatigue" for a in alerts)


def test_tension_fatigue_one_high_breaks_run():
    led = {"chapter_tension_curve": [{"chapter": 8, "tension_score": 4},
                                     {"chapter": 9, "tension_score": 7},
                                     {"chapter": 10, "tension_score": 2}]}
    assert logic_sentry.scan_tension(led, "x", 10) == []


def test_tension_fatigue_uses_fallback_curve_when_ledger_empty():
    # 账本 curve 为空时，用 emotional_progression 兜底曲线激活塌陷检测（此前永久 no-op）。
    fallback = [{"chapter": 8, "tension_score": 3}, {"chapter": 9, "tension_score": 2},
                {"chapter": 10, "tension_score": 1}]
    alerts = logic_sentry.scan_tension({}, "x", 10, fallback_curve=fallback)
    assert any(a["type"] == "tension_fatigue" for a in alerts)


def test_ledger_curve_wins_over_fallback():
    # 账本自身有 curve 时不被兜底覆盖。
    led = {"chapter_tension_curve": [{"chapter": 8, "tension_score": 9},
                                     {"chapter": 9, "tension_score": 8},
                                     {"chapter": 10, "tension_score": 9}]}
    fallback = [{"chapter": 8, "tension_score": 1}, {"chapter": 9, "tension_score": 1},
                {"chapter": 10, "tension_score": 1}]
    assert logic_sentry.scan_tension(led, "x", 10, fallback_curve=fallback) == []


# ── N4 角色护栏（底线/禁行）──

def test_character_hard_limit_violation_blocks():
    guardrails = {"characters": {"沈念": {"hard_limits": ["伤害无辜"]}}}
    alerts = logic_sentry.scan_character_guardrails(
        guardrails, "沈念抬手伤害无辜，以此换来胜利。", 12)
    assert any(a["type"] == "character_hard_limit_violation" and a["severity"] == "阻断级" for a in alerts)


def test_character_forbidden_action_is_advisory():
    guardrails = {"characters": {"沈念": {"forbidden_actions": ["背叛师门"]}}}
    alerts = logic_sentry.scan_character_guardrails(
        guardrails, "沈念在雨夜背叛师门，从此无法回头。", 12)
    assert any(a["type"] == "character_forbidden_action" and a["severity"] == "建议级" for a in alerts)


def test_character_guardrail_exempt_context():
    guardrails = {"characters": {"沈念": {"hard_limits": ["伤害无辜"], "allow_if_context": ["夺舍"]}}}
    assert logic_sentry.scan_character_guardrails(
        guardrails, "沈念被夺舍后伤害无辜，醒来时浑身发抖。", 12) == []


def test_character_guardrail_via_scan_chapter(tmp_path):
    proj = tmp_path / "书"
    (proj / "设定").mkdir(parents=True)
    (proj / "设定" / "character_guardrails.json").write_text(
        '{"characters":{"沈念":{"hard_limits":["伤害无辜"]}}}', encoding="utf-8")
    wiki = {"沈念": {"category": "character", "status": "active"}}
    alerts = logic_sentry.scan_chapter(
        wiki, "沈念亲手伤害无辜，殿内忽然安静。", 18, project_root=str(proj))
    hit = [a for a in alerts if a["type"] == "character_hard_limit_violation"]
    # B10：角色护栏=正文短语+名字邻近=脆弱启发式，检出但降为建议级。
    assert hit and hit[0]["severity"] == "建议级"


# ── B10 收口：确定性证据闸（伏笔台账整数比较）经 scan_chapter 仍保留阻断 ──

def test_foreshadow_overdue_stays_blocking_through_scan_chapter():
    # 确定性 finding（DETERMINISTIC_TYPES）不被降级——伏笔超期是台账整数比较·不扫正文。
    fr = {"kind": "foreshadow_report", "through_chapter": 60, "overdue": [
        {"id": "f1", "severity": "阻断级", "expected_payoff_chapter": 40,
         "description": "神秘玉佩来历", "note": "高价值伏笔已超回收窗口"}]}
    wiki = {"王敦": {"category": "character", "status": "active"}}
    alerts = logic_sentry.scan_chapter(
        wiki, "王敦继续赶路。", 60, project_root="/nonexistent", foreshadow_report=fr)
    hit = [a for a in alerts if a["type"] == "foreshadowing_overdue"]
    assert hit and hit[0]["severity"] == "阻断级"
    assert hit[0]["confidence"] == "deterministic"


def test_clean_chapter_still_clean_after_enforce():
    wiki = {"王敦": {"category": "character", "status": "active"}}
    assert logic_sentry.scan_chapter(wiki, "王敦继续赶路。", 10) == []


# ── A1/A2 经 logic_sentry.scan_structured_ledgers 进入真硬阻断闸 ──
from heuristic_gate import enforce, count_blocking


def _write_state_ledger(proj, deltas):
    (proj / "审稿").mkdir(parents=True, exist_ok=True)
    (proj / "审稿" / "state_ledger.json").write_text(
        json.dumps({"chapter_deltas": deltas}, ensure_ascii=False), encoding="utf-8")


def test_structured_lifecycle_conflict_counts_as_blocking(tmp_path):
    proj = tmp_path / "书"
    proj.mkdir()
    _write_state_ledger(proj, {
        "第2章": {"character_changes": [{"name": "王五", "event": "death"}]},
        "第6章": {"character_changes": [{"name": "王五", "event": "fights"}]},
    })
    alerts = logic_sentry.scan_structured_ledgers(str(proj))
    enforce(alerts)  # 幂等：确定性 alert 不被 B10 降级
    assert count_blocking(alerts) == 1
    assert alerts[0]["type"] == "deceased_ledger_reactivation"


def test_chapter_scoped_lifecycle_only_current_chapter(tmp_path):
    proj = tmp_path / "书"
    proj.mkdir()
    _write_state_ledger(proj, {
        "第2章": {"character_changes": [{"name": "王五", "event": "death"}]},
        "第6章": {"character_changes": [{"name": "王五", "event": "fights"}]},
    })
    assert len(logic_sentry.scan_structured_ledgers(str(proj), chapter_index=6)) == 1
    assert logic_sentry.scan_structured_ledgers(str(proj), chapter_index=3) == []


def test_world_fact_interval_conflict_blocks_in_full_pass(tmp_path):
    proj = tmp_path / "书"
    (proj / "设定").mkdir(parents=True)
    (proj / "设定" / "world_state_ledger.json").write_text(json.dumps({"major_changes": [
        {"key": "皇帝", "value": "周帝", "established_at": 1, "invalidated_at": 20},
        {"key": "皇帝", "value": "秦帝", "established_at": 10},
    ]}, ensure_ascii=False), encoding="utf-8")
    alerts = logic_sentry.scan_structured_ledgers(str(proj))   # chapter_index=None → 含世界事实
    enforce(alerts)
    assert count_blocking(alerts) == 1
    assert alerts[0]["type"] == "world_fact_interval_conflict"


def test_world_fact_skipped_in_single_chapter_pass(tmp_path):
    # 世界事实区间冲突是全局项；单章 post_write（chapter_index 给定）默认不刷
    proj = tmp_path / "书"
    (proj / "设定").mkdir(parents=True)
    (proj / "设定" / "world_state_ledger.json").write_text(json.dumps({"major_changes": [
        {"key": "皇帝", "value": "周帝", "established_at": 1, "invalidated_at": 20},
        {"key": "皇帝", "value": "秦帝", "established_at": 10},
    ]}, ensure_ascii=False), encoding="utf-8")
    assert logic_sentry.scan_structured_ledgers(str(proj), chapter_index=5) == []


# ── N4 悬念真空 ──

def test_suspense_vacuum_when_all_closed_before_window():
    # 唯一钩子第5章已解，第7-8章账面零活跃 → 真空（与张力分数无关）
    led = {"unresolved_hooks": [{"id": "h1", "introduced_in_chapter": 1,
                                 "status": "resolved", "resolved_in_chapter": 5}]}
    alerts = logic_sentry.scan_tension(led, "x", 8)
    assert any(a["type"] == "suspense_vacuum" and a["severity"] == "建议级" for a in alerts)


def test_suspense_vacuum_quiet_with_active_hook():
    led = {"unresolved_hooks": [{"id": "h1", "introduced_in_chapter": 3}]}
    assert not any(a["type"] == "suspense_vacuum"
                   for a in logic_sentry.scan_tension(led, "x", 8))


def test_suspense_vacuum_quiet_with_active_promise():
    led = {"unresolved_hooks": [{"id": "h1", "introduced_in_chapter": 1,
                                 "status": "resolved", "resolved_in_chapter": 5}],
           "reader_promises": [{"id": "p1", "promise": "夺回家主之位",
                                "introduced_in_chapter": 2}]}
    assert not any(a["type"] == "suspense_vacuum"
                   for a in logic_sentry.scan_tension(led, "x", 8))


def test_suspense_vacuum_conservative_when_close_chapter_unrecorded():
    # 已解但没记 resolved_in_chapter → 无从定位关闭点，视为一直活跃（宁漏勿误）
    led = {"unresolved_hooks": [{"id": "h1", "introduced_in_chapter": 1,
                                 "status": "resolved"}]}
    assert not any(a["type"] == "suspense_vacuum"
                   for a in logic_sentry.scan_tension(led, "x", 8))


def test_suspense_vacuum_skipped_on_empty_ledger():
    # 空账不判真空：没建账 ≠ 没悬念（建账缺失另有提示渠道）
    assert not any(a["type"] == "suspense_vacuum"
                   for a in logic_sentry.scan_tension({}, "x", 8))
