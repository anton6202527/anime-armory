#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import storyworld_pressure_test as spt


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def test_sparse_storyworld_blocks_pre_draft():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "设定", "章纲.md"), "第 1 章 开局\n")
        report = spt.pressure_test(root)
        assert report["verdict"] == "block_pre_draft"
        assert "world_rules" in report["risk_axes"]
        assert report["next_actions"][0]["recommended_skill"] == "novel-craft"


def test_rich_storyworld_passes_or_review_only():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "设定", "角色卡.md"), """## 沈念
目标：复仇并夺回宗门。恐惧：力量失控。
## 反派
目标：夺取灵根。
## 盟友
动机：偿还旧债。
""")
        _write(os.path.join(root, "设定", "世界观.md"), "宗门分三州，有地图边界。规则：越境需代价，禁忌是血祭。")
        _write(os.path.join(root, "设定", "章纲.md"), "\n".join(
            f"第 {i} 章 冲突升级，反派制造危机，章末钩子。" for i in range(1, 7)
        ))
        _write(os.path.join(root, "设定", "时间线.md"), "开局十年前宗门覆灭。三年前主角入山。第一卷从回宗门开始，五章内揭露背叛并埋下回收窗口。")
        _write(os.path.join(root, "设定", "读者契约.md"), "核心承诺：复仇、升级、智斗与代价并行；每三章兑现一个小爽点，禁止无代价越级。")
        _write(os.path.join(root, "设定", "power_system_registry.json"), json.dumps({"levels": ["炼气", "筑基"]}, ensure_ascii=False))
        report = spt.pressure_test(root)
        assert report["verdict"] in {"pass", "pass_with_review"}
        assert "outline_pressure" not in report["risk_axes"]


def test_keyword_stuffed_shell_no_longer_passes():
    # 升级动机：旧版只查"填没填/长度够不够"，塞满关键词的空壳能全 pass。
    with tempfile.TemporaryDirectory() as root:
        # 角色卡：目标词只出现在文件头，角色块内没有任何目标 → character_agency risk
        _write(os.path.join(root, "设定", "角色卡.md"), "目标 动机 恐惧\n## 甲\n是个人。\n## 乙\n也是个人。\n## 丙\n还是个人。\n")
        # 世界观：只命中一类规则词，没有代价/限制闭环 → world_rules risk
        _write(os.path.join(root, "设定", "世界观.md"), "这个世界有规则。宗门很多。")
        # 章纲：逐章条目全是干事件，无冲突/代价/钩子 → outline_pressure risk
        _write(os.path.join(root, "设定", "章纲.md"), "\n".join(f"第 {i} 章 去了一个地方。" for i in range(1, 7)))
        # 读者契约：凑字数、无题旨/承诺/禁偏信号 → reader_contract risk
        _write(os.path.join(root, "设定", "读者契约.md"), "这本书会很好看很好看很好看很好看很好看很好看很好看很好看。")
        report = spt.pressure_test(root)
        assert report["verdict"] == "block_pre_draft"
        for axis in ("character_agency", "world_rules", "outline_pressure", "reader_contract"):
            assert axis in report["risk_axes"], axis
        assert report["check_depth"] == "structural"
        assert report["semantic_followup"]["axes_needing_semantic_review"]


def test_main_writes_artifacts():
    with tempfile.TemporaryDirectory() as root:
        _write(os.path.join(root, "设定", "章纲.md"), "第 1 章 开局\n")
        import sys
        old_argv = sys.argv
        sys.argv = ["storyworld_pressure_test.py", root]
        try:
            assert spt.main() == 0
        finally:
            sys.argv = old_argv
        assert os.path.exists(os.path.join(root, "审稿", "storyworld_pressure_test.json"))
