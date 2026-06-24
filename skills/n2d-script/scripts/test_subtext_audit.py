"""cd skills/n2d-script/scripts && python -m pytest test_subtext_audit.py"""
import subtext_audit as st


def test_self_emotion_detection():
    assert st.is_self_emotion("我好难过，真的撑不下去了")
    assert st.is_self_emotion("我真的很生气")
    assert st.is_self_emotion("我爱你")
    assert not st.is_self_emotion("把茶递过去，转身走向窗边")   # 演出，无情绪名


def test_emotional_summary_only_for_narrator():
    assert st.is_emotional_summary("旁白", "她心里一阵绝望")
    assert st.is_emotional_summary("旁白", "他感到无比愧疚")
    assert not st.is_emotional_summary("沈念", "她心里一阵绝望")   # 非旁白不判（角色可这样说别人）


def test_over_explanation_and_exposition():
    assert st.is_over_explanation("因为你当年背叛了我，所以我今天才回来复仇")
    assert st.is_exposition_dump("其实我是你失散多年的姐姐")
    assert st.is_exposition_dump("你忘了我是你的未婚夫吗")
    assert not st.is_over_explanation("我们走吧")


def test_classify_and_rate():
    assert "self_emotion" in st.classify_line("沈念", "我好害怕")
    assert st.classify_line("沈念", "她端起茶盏，没有回头") == []
    assert st.onthenose_rate(3, 12) == 0.25
    assert st.onthenose_rate(0, 0) == 0.0


def test_audit_lines_flags_and_rate():
    rows = [
        (1, "沈念", "我好难过"),
        (2, "沈念", "我真的很绝望"),
        (3, "旁白", "她感到一阵崩溃"),
        (4, "柳娘子", "因为你害了我，所以我恨你"),
        (5, "沈念", "其实我是嫡女"),
        (6, "沈念", "她放下茶盏"),       # clean
    ]
    findings = st.audit_lines(rows)
    codes = {c for _s, c, _m in findings}
    assert {"self_emotion", "emotional_summary", "over_explanation", "exposition_dump"} <= codes
    assert "onthenose_rate_high" in codes      # 大量直白行 → 直白率高
    assert all(s == "warn" for s, _c, _m in findings)


def test_clean_episode_no_findings():
    rows = [
        (1, "沈念", "她把信纸凑近烛火，看着字迹一点点卷曲"),
        (2, "柳娘子", "茶凉了，要不要换一盏"),
        (3, "沈念", "不必了"),
        (4, "旁白", "窗外的雪落了一整夜"),
        (5, "柳娘子", "明日我便启程"),
    ]
    assert st.audit_lines(rows) == []
