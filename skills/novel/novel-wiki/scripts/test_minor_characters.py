# -*- coding: utf-8 -*-
"""minor_characters 纯函数单测。
cd skills/novel/novel-wiki/scripts && python3 -m pytest test_minor_characters.py
"""
import minor_characters as mc


def test_extract_attribution_names():
    cands = mc.extract_name_candidates("赵四说道：天亮了。钱五笑道：还早。")
    assert "赵四" in cands and "钱五" in cands


def test_extract_rejects_verb_fragments():
    # 高精度核心：不得把"沈念知道""低声道""味道"误抽成名（单字 道 不算说话动词）
    cands = mc.extract_name_candidates("沈念知道这事。她低声道了一句。那汤很有味道。")
    assert "沈念知" not in cands and "低声" not in cands and "有味" not in cands


def test_extract_requires_sentence_boundary_and_speech_verb():
    # 句首/标点后的真主语 + 多字说话动词才算
    cands = mc.extract_name_candidates("殿内静极。柳嬷嬷沉声道：娘娘三思。")
    assert "柳嬷嬷" in cands


def test_extract_filters_stopwords():
    cands = mc.extract_name_candidates("他说道：走吧。那人冷笑道：等等。众人说罢散去。")
    assert "他" not in cands and "那人" not in cands and "众人" not in cands


def test_aggregate_candidates():
    per = [(1, {"赵四"}), (2, {"赵四", "钱五"}), (3, {"赵四"})]
    agg = mc.aggregate_candidates(per)
    assert agg["赵四"] == [1, 2, 3]
    assert agg["钱五"] == [2]


def test_recurring_untracked_flags_only_frequent_and_uncarded():
    agg = {"赵四": [1, 2, 3, 4], "钱五": [2], "沈念": [1, 2, 3, 5]}
    flagged = mc.recurring_untracked(agg, tracked_names={"沈念"}, min_chapters=3)
    names = [n for n, _ in flagged]
    assert "赵四" in names        # 4 章、未建卡 → 报
    assert "钱五" not in names     # 仅 1 章 → 不报
    assert "沈念" not in names     # 已在角色卡 → 不报


def test_recurring_untracked_sorted_by_frequency():
    agg = {"甲": [1, 2, 3], "乙": [1, 2, 3, 4, 5]}
    flagged = mc.recurring_untracked(agg, tracked_names=set(), min_chapters=3)
    assert flagged[0][0] == "乙"   # 出现章多的在前


def test_min_chapters_threshold():
    agg = {"丙": [1, 2]}
    assert mc.recurring_untracked(agg, set(), min_chapters=3) == []
    assert [n for n, _ in mc.recurring_untracked(agg, set(), min_chapters=2)] == ["丙"]


def test_extract_court_rank_names():
    cands = mc.extract_name_candidates("本宫替张才人退了。安美人不在，王嬷嬷垂手立着。")
    assert "张才人" in cands and "安美人" in cands and "王嬷嬷" in cands


# ── 配角失踪检测（braided-stories：重要角色长期缺席该提醒） ──────────────────

def test_build_presence_matches_any_variant():
    presence = mc.build_presence(
        [(1, "沈念入宫。"), (2, "无关。"), (3, "念妃临朝。")],
        {"沈念": {"沈念", "念妃"}})
    assert presence["沈念"] == [1, 3]


def test_absent_characters_flags_high_freq_long_absence():
    presence = {"赵四": list(range(1, 11))}   # 出场 10 章（高频）
    out = mc.absent_characters(presence, 18)  # 缺席 8 章 = 高频阈值
    assert out and out[0][0] == "赵四" and out[0][2] == 8


def test_absent_characters_low_freq_uses_relaxed_threshold():
    presence = {"钱五": [1, 2, 3, 4, 5]}      # 出场 5 章（低频）
    assert mc.absent_characters(presence, 13) == []          # 缺席 8 < 放宽阈值 15
    out = mc.absent_characters(presence, 20)                 # 缺席 15 → 报
    assert out and out[0][0] == "钱五"


def test_absent_characters_exempts_exited_and_rare():
    presence = {"赵四": list(range(1, 11)), "龙套": [1, 2]}
    out = mc.absent_characters(presence, 30, exited={"赵四"})
    assert out == []   # 已登记退场豁免；出场 2 章 < 纳入门槛不监控


def test_absent_characters_marks_open_thread_holder():
    presence = {"赵四": list(range(1, 11))}
    out = mc.absent_characters(presence, 20, open_thread_names={"赵四"})
    assert out[0][4] is True


def test_absence_alerts_end_to_end(tmp_path):
    proj = tmp_path / "书"
    (proj / "章节").mkdir(parents=True)
    texts = [(i, "赵四出手相救。" if i <= 10 else "旁人叙事。") for i in range(1, 26)]
    alerts = mc.absence_alerts(str(proj), texts, {"赵四"}, set())
    assert len(alerts) == 1
    a = alerts[0]
    assert a["type"] == "major_character_absent" and a["severity"] == "建议级"
    assert a["last_seen_chapter"] == 10 and a["absent_chapters"] == 15
    assert a["auto"] is True


def test_absence_alerts_quiet_without_chapters(tmp_path):
    assert mc.absence_alerts(str(tmp_path), [], {"赵四"}, set()) == []


# ── confusable_pairs / opening_cast_counts（第五轮：命名混淆 + 开篇过载）──────

def test_confusable_pairs_edit_distance_one():
    pairs = mc.confusable_pairs(["张青", "张清", "鲁智深"])
    assert len(pairs) == 1 and set(pairs[0][:2]) == {"张清", "张青"}


def test_confusable_pairs_same_surname_shared_given_char():
    # 编辑距离 2（规则①不触发），但同姓且名部共字"风" → 规则②命中
    pairs = mc.confusable_pairs(["李长风", "李风吟"])
    assert len(pairs) == 1 and "风" in pairs[0][2]


def test_confusable_pairs_distinct_names_clean():
    assert mc.confusable_pairs(["王敦", "贺平生", "重华", "梁画秋"]) == []


def test_confusable_pairs_substring_and_alias_exempt():
    # 互为子串（简称）不报；别名归一后同角色不报
    assert mc.confusable_pairs(["张三", "老张三"]) == []
    pairs = mc.confusable_pairs(["沈青崖", "沈青禾"], same_canonical=lambda a, b: True)
    assert pairs == []


def test_opening_cast_counts_windows():
    groups = {n: {n} for n in ("赵一", "钱二", "孙三", "李四")}
    texts = [(1, "赵一遇见钱二。"), (2, "孙三登场。"), (3, "李四路过。"), (9, "全员大战。")]
    ch1, opening = mc.opening_cast_counts(texts, groups)
    assert ch1 == 2 and opening == 4


def test_naming_alerts_end_to_end(tmp_path):
    proj = tmp_path / "书"
    (proj / "章节").mkdir(parents=True)
    texts = [(1, "张青和张清一起出场。"), (2, "张青说话。"), (3, "张清说话。")]
    alerts = mc.naming_alerts(str(proj), texts, {"张青", "张清"}, set())
    kinds = {a["type"] for a in alerts}
    assert "confusable_character_names" in kinds
    assert all(a["severity"] == "建议级" for a in alerts)


def test_naming_alerts_cast_overload(tmp_path):
    proj = tmp_path / "书"
    (proj / "章节").mkdir(parents=True)
    names = ["东方一", "西门二", "南宫三", "北堂四", "皇甫五", "尉迟六", "长孙七"]
    texts = [(1, "，".join(names) + "齐聚一堂。")]
    alerts = mc.naming_alerts(str(proj), texts, set(names), set())
    hits = [a for a in alerts if a["type"] == "opening_cast_overload"]
    assert len(hits) == 1 and hits[0]["count"] == 7 and hits[0]["chapter"] == 1
