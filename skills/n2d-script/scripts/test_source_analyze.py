import source_analyze


def test_extract_characters_filters_system_and_action_false_positives():
    text = """
【击杀燃灯境生物，获得道行十一万九千八百五十五年】
【当前道行：四十九万八千六百七十二年】
无数道精气，自城中妖魔尸首中飘出。
一道黑影一次次被抛向空中。
姜月初冷笑道：“老子还是你娘呢！”
李乾元低声道：“我是你爹。”
云翎大圣苦笑道：“其实他没有骗你。”
"""
    names = {item["name"] for item in source_analyze.extract_characters(text, limit=20)}

    assert "姜月初" in names
    assert "李乾元" in names
    assert "云翎大圣" in names
    assert "获得" not in names
    assert "当前" not in names
    assert "无数" not in names
    assert "一道" not in names
    assert "你爹" not in names


def test_extract_characters_filters_speech_modifier_false_positives():
    text = """
姜月初侧过头，轻声道：“无需担心。”
随后缓缓落下。
顾挽澜思索片刻，还是沉声答道：“西域妖庭底蕴不浅。”
这番话，说得还算客气。
徐骁漠然看着脚下妖群，冷声道：“随我南下。”
"""
    names = {item["name"] for item in source_analyze.extract_characters(text, limit=20)}

    assert "姜月初" in names
    assert "徐骁" in names
    assert "轻声" not in names
    assert "随后" not in names
    assert "还是" not in names
    assert "这番话" not in names
    assert "漠然" not in names


def test_extract_characters_ignores_non_speech_action_and_daoxing_fragments():
    text = """
姜月初站起身，环顾四周。
高临下地看着妖魔，少女没有说话。
【是否消耗道行：六万年】
要知道，这世道并不太平。
他顿了顿，抱拳道：“属下领命。”
魏合继续说道：“不是这样。”
试探着问道：“能走吗？”
躬身说道：“遵旨。”
忽而笑道：“来了。”
喃喃道：“不该如此。”
姜月初冷声道：“杀。”
"""
    names = {item["name"] for item in source_analyze.extract_characters(text, limit=20)}

    assert "姜月初" in names
    assert "姜月初站" not in names
    assert "高临下地" not in names
    assert "是否消耗" not in names
    assert "要知" not in names
    assert "这世" not in names
    assert "没有" not in names
    assert "他顿了顿" not in names
    assert "抱拳" not in names
    assert "魏合继续" not in names
    assert "试探着" not in names
    assert "躬身" not in names
    assert "忽而" not in names
    assert "喃喃" not in names
