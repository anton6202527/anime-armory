#!/usr/bin/env python3
# coding: utf-8
"""cd skills/novel-wiki/scripts && python -m pytest test_graph_sentry.py"""
import json
import os
import tempfile

import graph_sentry


def _ledger(root, deltas):
    os.makedirs(os.path.join(root, "审稿"), exist_ok=True)
    with open(os.path.join(root, "审稿", "state_ledger.json"), "w", encoding="utf-8") as f:
        json.dump({"schema_version": 1, "kind": "novel_state_ledger",
                   "characters": {}, "chapter_deltas": deltas}, f, ensure_ascii=False)


def test_no_ledger_is_not_clean():
    with tempfile.TemporaryDirectory() as root:
        r = graph_sentry.check_graph_sentry(root)
        assert r["status"] == "no_ledger"  # 缺账本绝不报 clean
        assert r["blocking"] == 0 and r["report_only"] is True


def test_dead_character_reappears_flags_blocking_severity():
    with tempfile.TemporaryDirectory() as root:
        _ledger(root, {
            "chapter_02": {"character_changes": [{"name": "赵无极", "change": "被反派一掌击杀，当场陨落"}]},
            "chapter_05": {"character_changes": [{"name": "赵无极", "change": "率军杀入城中"}]},
        })
        r = graph_sentry.check_graph_sentry(root)
        assert r["status"] == "conflicts"
        a = [x for x in r["alerts"] if x["character"] == "赵无极"][0]
        assert a["exit_chapter"] == 2 and a["reappear_chapter"] == 5
        assert a["severity"] == "阻断级"
        assert r["blocking"] == 0  # report-only：发现穿帮但不硬门控


def test_revive_marker_downgrades_to_advisory():
    with tempfile.TemporaryDirectory() as root:
        _ledger(root, {
            "chapter_02": {"character_changes": [{"name": "林越", "change": "重伤身亡"}]},
            "chapter_06": {"character_changes": [{"name": "林越", "change": "夺舍重生，归来复仇"}]},
        })
        r = graph_sentry.check_graph_sentry(root)
        assert r["status"] == "advisory"
        a = [x for x in r["alerts"] if x["character"] == "林越"][0]
        assert a["severity"] == "advisory"


def test_clean_when_no_lifecycle_conflict():
    with tempfile.TemporaryDirectory() as root:
        _ledger(root, {
            "chapter_01": {"character_changes": [{"name": "苏璃", "change": "觉醒灵根"}]},
            "chapter_03": {"character_changes": [{"name": "苏璃", "change": "突破筑基"}]},
        })
        r = graph_sentry.check_graph_sentry(root)
        assert r["status"] == "clean"
        assert r["alerts"] == []


# ── A1·结构化生命周期确定性检测（B10-earned 硬闸） ──
def test_structured_event_death_then_action_is_deterministic_block():
    led = {"chapter_deltas": {
        "第3章": {"character_changes": [{"name": "王五", "event": "death", "change": "力战而亡"}]},
        "第7章": {"character_changes": [{"name": "王五", "event": "fights", "change": "挥刀杀敌"}]},
    }}
    a = graph_sentry.detect_lifecycle_conflicts(led)
    assert len(a) == 1
    assert a[0]["type"] == "deceased_ledger_reactivation"
    assert a[0]["confidence"] == "deterministic" and a[0]["severity"] == "阻断级"
    assert a[0]["entity"] == "王五" and a[0]["chapter"] == 7


def test_structured_revival_clears_conflict():
    led = {"chapter_deltas": {
        "第3章": {"character_changes": [{"name": "王五", "event": "death"}]},
        "第5章": {"character_changes": [{"name": "王五", "event": "revival"}]},
        "第7章": {"character_changes": [{"name": "王五", "event": "fights"}]},
    }}
    assert graph_sentry.detect_lifecycle_conflicts(led) == []


def test_lifecycle_chapter_filter():
    led = {"chapter_deltas": {
        "第3章": {"character_changes": [{"name": "王五", "event": "death"}]},
        "第7章": {"character_changes": [{"name": "王五", "event": "fights"}]},
    }}
    assert len(graph_sentry.detect_lifecycle_conflicts(led, chapter_index=7)) == 1
    assert graph_sentry.detect_lifecycle_conflicts(led, chapter_index=5) == []


def test_free_text_only_no_deterministic_but_keyword_advisory():
    # 无结构化 event → 确定性路径忽略；check_graph_sentry 关键词路径仍出 advisory（不双报）
    led = {"chapter_deltas": {
        "第3章": {"character_changes": [{"name": "李四", "change": "被杀身亡"}]},
        "第7章": {"character_changes": [{"name": "李四", "change": "现身大殿"}]},
    }}
    assert graph_sentry.detect_lifecycle_conflicts(led) == []
    with tempfile.TemporaryDirectory() as root:
        _ledger(root, led["chapter_deltas"])
        r = graph_sentry.check_graph_sentry(root)
        kinds = [x["type"] for x in r["alerts"]]
        assert kinds.count("character_reappears_after_exit") == 1   # 关键词 advisory 一条
        assert "deceased_ledger_reactivation" not in kinds          # 无结构化→不出确定性
        assert r["blocking"] == 0                                   # graph_sentry 自身仍 report-only


def test_check_graph_sentry_structured_not_double_reported():
    led = {"chapter_deltas": {
        "第3章": {"character_changes": [{"name": "王五", "event": "death", "change": "战死"}]},
        "第7章": {"character_changes": [{"name": "王五", "event": "fights", "change": "杀敌"}]},
    }}
    with tempfile.TemporaryDirectory() as root:
        _ledger(root, led["chapter_deltas"])
        r = graph_sentry.check_graph_sentry(root)
        kinds = [x["type"] for x in r["alerts"]]
        assert kinds.count("deceased_ledger_reactivation") == 1
        assert "character_reappears_after_exit" not in kinds        # 结构化条目不再走关键词
        assert r["deterministic_candidates"] == 1


# ── A2·世界设定原子事实有效区间确定性检测（FACTTRACK 式） ──
def test_world_fact_interval_overlap_conflict():
    world = {"major_changes": [
        {"key": "皇帝", "value": "周帝", "established_at": 1, "invalidated_at": 20},
        {"key": "皇帝", "value": "秦帝", "established_at": 10},
    ]}
    a = graph_sentry.detect_fact_interval_conflicts(world)
    assert len(a) == 1
    assert a[0]["type"] == "world_fact_interval_conflict"
    assert a[0]["confidence"] == "deterministic" and a[0]["severity"] == "阻断级"
    assert a[0]["entity"] == "皇帝"


def test_world_fact_non_overlapping_intervals_ok():
    world = {"major_changes": [
        {"key": "皇帝", "value": "周帝", "established_at": 1, "invalidated_at": 10},
        {"key": "皇帝", "value": "秦帝", "established_at": 10},   # 区间相邻不重叠 [1,10) vs [10,inf)
    ]}
    assert graph_sentry.detect_fact_interval_conflicts(world) == []


def test_world_fact_same_value_or_unstructured_ignored():
    world = {"major_changes": [
        {"key": "皇帝", "value": "周帝", "established_at": 1},
        {"key": "皇帝", "value": "周帝", "established_at": 5},     # 同值不冲突
        {"event": "天降异象", "forbidden_before": ["御剑"], "chapter": 3},  # 旧式无 key/value → 忽略
    ]}
    assert graph_sentry.detect_fact_interval_conflicts(world) == []


# ── 实体消解（别名归一）：死亡记于本名、复现记于封号 → 仍判确定性冲突 ──
def test_alias_resolution_death_under_name_reappear_under_alias():
    led = {
        "character_aliases": {"先皇": "李乾元", "孤月": "李乾元"},
        "chapter_deltas": {
            "第3章": {"character_changes": [{"name": "李乾元", "event": "death", "change": "驾崩"}]},
            "第7章": {"character_changes": [{"name": "先皇", "event": "fights", "change": "现身夺舍"}]},
        },
    }
    a = graph_sentry.detect_lifecycle_conflicts(led)
    assert len(a) == 1
    assert a[0]["type"] == "deceased_ledger_reactivation"
    assert a[0]["entity"] == "李乾元"          # 归一到规范名
    assert "别名归一" in a[0]["evidence"]


def test_alias_resolution_via_characters_list():
    led = {
        "characters": [{"name": "李乾元", "aliases": ["先皇", "孤月"]}],
        "chapter_deltas": {
            "第3章": {"character_changes": [{"name": "孤月", "event": "death"}]},
            "第9章": {"character_changes": [{"name": "李乾元", "event": "appears"}]},
        },
    }
    a = graph_sentry.detect_lifecycle_conflicts(led)
    assert len(a) == 1 and a[0]["entity"] == "李乾元"


def test_no_alias_source_is_backward_compatible():
    # 无别名表：不同名按不同角色处理（原行为），不误报
    led = {"chapter_deltas": {
        "第3章": {"character_changes": [{"name": "李乾元", "event": "death"}]},
        "第7章": {"character_changes": [{"name": "先皇", "event": "fights"}]},
    }}
    assert graph_sentry.detect_lifecycle_conflicts(led) == []


def test_build_alias_map_idempotent_and_canonical_self():
    m = graph_sentry.build_alias_map({"character_aliases": {"先皇": "李乾元"}})
    assert m["先皇"] == "李乾元" and m["李乾元"] == "李乾元"
    assert graph_sentry._canonical("先皇", m) == "李乾元"
    assert graph_sentry._canonical("无名", m) == "无名"   # 未登记原样返回
    assert graph_sentry.build_alias_map({}) == {}          # 无源 → 空 map


def test_merged_summary_wrapped_ledger_still_fires():
    # 回归：reconcile_ledger 合并后真实 chapter_deltas[key]={merged_at,summary:<delta>,verification}。
    # 此前 _iter_character_changes 裸读 character_changes → 生产台账上确定性生死闸永久 no-op。
    led = {"chapter_deltas": {
        "chapter_03": {"merged_at": "2026-07-15",
                        "summary": {"chapter": 3, "character_changes": [{"name": "王五", "event": "death", "change": "力战而亡"}]},
                        "verification": {}},
        "chapter_07": {"merged_at": "2026-07-15",
                        "summary": {"chapter": 7, "character_changes": [{"name": "王五", "event": "fights", "change": "挥刀杀敌"}]},
                        "verification": {}},
    }}
    a = graph_sentry.detect_lifecycle_conflicts(led)
    assert len(a) == 1 and a[0]["entity"] == "王五" and a[0]["severity"] == "阻断级"


def test_rolled_thin_summary_still_fires_deterministic_gate():
    # 回归：2026-07 起 rollup 把 character_changes 压成 {name,event} 精简列表（丢 change 文本）——
    # 已 rollup 的早章死亡 event 必须仍参与生死闸，否则"第3章死、第300章复活"因维护性 rollup 漏检。
    led = {"chapter_deltas": {
        "chapter_03": {"merged_at": "x",
                       "summary": {"rolled": True, "new_facts": 2,
                                   "character_changes": [{"name": "王五", "event": "death"}],
                                   "characters_touched": ["王五"]},
                       "verification": {}},
        "chapter_07": {"merged_at": "y",
                       "summary": {"chapter": 7,
                                   "character_changes": [{"name": "王五", "event": "fights", "change": "挥刀杀敌"}]},
                       "verification": {}},
    }}
    a = graph_sentry.detect_lifecycle_conflicts(led)
    assert len(a) == 1 and a[0]["type"] == "deceased_ledger_reactivation" and a[0]["entity"] == "王五"


def test_legacy_int_rolled_summary_skipped_not_crash():
    # 旧版 rollup 遗留台账：character_changes 是整数计数——不可迭代也无事件，必须跳过而非 TypeError。
    led = {"chapter_deltas": {
        "chapter_01": {"merged_at": "x",
                       "summary": {"rolled": True, "character_changes": 3, "characters_touched": ["甲"]},
                       "verification": {}},
        "chapter_07": {"summary": {"character_changes": [{"name": "王五", "event": "death"}]}},
    }}
    assert graph_sentry.detect_lifecycle_conflicts(led) == []
