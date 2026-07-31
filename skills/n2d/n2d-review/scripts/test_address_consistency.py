#!/usr/bin/env python3
"""address_consistency 纯函数单测。
cd skills/n2d/n2d-review/scripts && python -m pytest test_address_consistency.py
"""
import address_consistency as ac


REG = {
    "称谓": {
        "柳娘子": {"canonical": "柳姐姐", "allowed": ["柳姐姐", "柳娘子", "姐姐"], "forbidden": ["柳妹妹", "丫头"]},
        "沈念": {"canonical": "娘娘", "allowed": ["娘娘", "本宫"], "forbidden": ["小姐"]},
    },
    "口头禅": {"小禾": ["奴婢该死"]},
}
IDX = ac.build_index(REG)


def test_build_index():
    assert IDX["forbidden"]["柳妹妹"] == "柳娘子"
    assert IDX["canonical"]["沈念"] == "娘娘"
    assert IDX["catchphrase"]["奴婢该死"] == "小禾"
    assert "姐姐" in IDX["allowed"]["柳娘子"]


def test_scan_line_forbidden_is_block():
    fs = ac.scan_line("沈念", "你这丫头懂什么", IDX)
    assert any(f["verdict"] == "block" and f["word"] == "丫头" for f in fs)


def test_scan_line_clean():
    assert ac.scan_line("沈念", "柳姐姐慢走", IDX) == []


def test_scan_line_catchphrase_misassigned():
    # 小禾的口头禅由沈念念出 → warn
    fs = ac.scan_line("沈念", "奴婢该死，求娘娘开恩", IDX)
    assert any(f["verdict"] == "warn" and f["kind"] == "catchphrase_misassigned" for f in fs)


def test_scan_line_catchphrase_by_owner_ok():
    # 小禾自己念自己的口头禅 → 不报
    assert ac.scan_line("小禾", "奴婢该死", IDX) == []


def test_appellation_usage_counts():
    lines = [("甲", "柳娘子来了"), ("乙", "姐姐请坐"), ("丙", "姐姐喝茶")]
    usage = ac.appellation_usage(lines, IDX)
    assert usage["柳娘子"]["姐姐"] == 2
    assert usage["柳娘子"]["柳娘子"] == 1
    assert usage["柳娘子"]["柳姐姐"] == 0


def test_canonical_dropouts_flags_silent_replacement():
    # 柳娘子 正称「柳姐姐」0 次，变体「姐姐」出现 → warn
    lines = [("甲", "姐姐来了"), ("乙", "姐姐请坐")]
    usage = ac.appellation_usage(lines, IDX)
    drops = ac.canonical_dropouts(usage, IDX)
    assert any(d["owner"] == "柳娘子" and "姐姐" in d["variants_seen"] for d in drops)


def test_canonical_present_no_dropout():
    lines = [("甲", "柳姐姐来了")]
    usage = ac.appellation_usage(lines, IDX)
    assert ac.canonical_dropouts(usage, IDX) == []
