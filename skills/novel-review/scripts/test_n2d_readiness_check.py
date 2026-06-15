#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_n2d_readiness_check.py — 从脚本自身目录运行：
    cd skills/novel-review/scripts && python -m pytest test_n2d_readiness_check.py
"""
import json
import os
import tempfile

import n2d_readiness_check as nr


def _mk_project(chapters):
    root = tempfile.mkdtemp()
    cdir = os.path.join(root, "章节")
    os.makedirs(cdir)
    for n, text in chapters.items():
        with open(os.path.join(cdir, f"第{n:02d}章_x.md"), "w", encoding="utf-8") as f:
            f.write(f"# 第{n}章 测试\n\n{text}")
    return root


def test_asset_and_scene_extraction():
    text = "他拔出[PROP_断魂剑]走进[LOC_密室]剑气[VFX_幽冥]映在[CHAR_王敦_魔化]脸上。"
    assets, locs = nr._assets(text)
    assert "PROP_断魂剑" in assets and "LOC_密室" in assets
    assert locs == {"密室"}


def test_dialogue_ratio_counts_quotes():
    assert nr._dialogue_ratio("他说「你是谁」然后沉默") > 0
    assert nr._dialogue_ratio("他沉默地走着没有说话") == 0.0


def test_untagged_narration_chapter_flagged():
    # 一章满标签 + 对白 + 视觉词；一章纯旁白无标签无场景锚 → 后者应被标弱。
    rich = "他握紧[PROP_刀]走进[LOC_大殿]「动手」血光剑影火焰四溅" * 8
    bare = "他平静地想着许多事情时间慢慢流逝什么也没有发生" * 8
    root = _mk_project({1: rich, 2: bare})
    rows, summary = nr.flag_rows(nr.analyze(root, None))
    by_ch = {r["chapter"]: r for r in rows}
    assert by_ch[2]["asset_tags"] == 0
    assert 2 in summary["weak_chapters"]
    assert any("无资产标签" in f for f in by_ch[2]["flags"])


def test_writes_json_artifact(tmp_path):
    rich = "他握紧[PROP_刀]走进[LOC_大殿]「动手」血光剑影" * 8
    root = _mk_project({1: rich})
    out = os.path.join(root, "审稿", "n2d_readiness.json")
    import sys
    argv = sys.argv
    sys.argv = ["n2d_readiness_check.py", root]
    try:
        rc = nr.main()
    finally:
        sys.argv = argv
    assert rc == 0
    data = json.load(open(out, encoding="utf-8"))
    assert data["kind"] == "novel_n2d_readiness"
    assert data["summary"]["n_chapters"] == 1
