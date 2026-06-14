#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import tempfile

import promo_gen


def _project():
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "章节"))
    os.makedirs(os.path.join(root, "设定"))
    with open(os.path.join(root, "设定", "角色卡.md"), "w", encoding="utf-8") as f:
        f.write("## 林澈\n\n## 沈青梧\n")
    with open(os.path.join(root, "章节", "第01章_雷火.md"), "w", encoding="utf-8") as f:
        f.write(
            "# 第一章\n\n"
            "银白雷火从林澈掌心炸开，照亮整座旧殿，沈青梧被逼到断柱之后。\n\n"
            "林澈抬头冷笑：“今日这座旧殿，谁也别想活着出去。”\n\n"
            "下一刻，雷火倒卷成阵，所有追兵同时跪倒，真相却只露出半角。"
        )
    return root


def test_promo_reads_requested_chapter_and_writes_n2d_ready():
    root = _project()
    promo_path, n2d_path = promo_gen.write_outputs(root, 1, "tiktok")

    assert os.path.exists(promo_path)
    assert os.path.exists(n2d_path)
    promo = open(promo_path, encoding="utf-8").read()
    n2d = open(n2d_path, encoding="utf-8").read()

    assert "银白雷火" in promo
    assert "今日这座旧殿" in promo
    assert "暗金汞液" not in promo
    assert "Beat 1 [0-3s]" in n2d
    assert "林澈" in n2d


def test_missing_chapter_fails_explicitly():
    root = _project()
    try:
        promo_gen.write_outputs(root, 2, "tiktok")
    except FileNotFoundError as exc:
        assert "找不到第 2 章" in str(exc)
    else:
        raise AssertionError("missing chapter should fail")
