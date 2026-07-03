# -*- coding: utf-8 -*-
"""minor_characters 纯函数单测。
cd skills/novel-wiki/scripts && python3 -m pytest test_minor_characters.py
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
