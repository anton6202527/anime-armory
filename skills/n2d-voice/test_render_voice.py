"""voice_text.clean_text 回归测试——锁住「气口标记 || / 钩子 emoji」清洗，
防 `。，` / `，，` 脏标点回流到 时长清单.json 文本 与字幕（治历史 bug）。
cd skills/n2d-voice && python -m pytest test_render_voice.py
（clean_text 已独立到 voice_text.py，render_voice 主流程不可安全 import 故不直接测它。）
"""
import voice_text as rv


def test_pause_after_sentence_end_no_comma():
    # 。|| → 。（不留 「。，」）
    assert rv.clean_text("走向。|| 慎重选择。") == "走向。慎重选择。"
    assert rv.clean_text("人就只能猜。|| 猜不到的，就没法要。") == "人就只能猜。猜不到的，就没法要。"


def test_pause_after_comma_collapses():
    # ，|| → ，（不留 「，，」/多余空格）
    assert rv.clean_text("谁害的我，|| 我让她十倍奉还。") == "谁害的我，我让她十倍奉还。"
    assert rv.clean_text("这条命，|| 我自己说了算。") == "这条命，我自己说了算。"


def test_pause_plain_becomes_comma():
    # 裸气口（前面无标点）→ 逗号
    assert rv.clean_text("这不是 || 我的寝室") == "这不是，我的寝室"


def test_hook_markers_stripped():
    assert rv.clean_text("这条命，我说了算。  🪝集尾") == "这条命，我说了算。"
    assert rv.clean_text("我让她十倍奉还。  💥爽点") == "我让她十倍奉还。"
    assert rv.clean_text("粗麻、霉味。  ⚡钩子") == "粗麻、霉味。"


def test_no_leading_comma_or_double_space():
    assert rv.clean_text("|| 我自己说了算。") == "我自己说了算。"
    assert rv.clean_text("甲，乙，丙") == "甲，乙，丙"   # 合法多逗号不误collapse
