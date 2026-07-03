#!/usr/bin/env python3
import split_novel


def test_auto_chapter_aware_guard_detects_fragmented_chaptered_source():
    paras = []
    for i in range(1, 11):
        paras.extend([f"第{i}章 妖变", "【系统提示】", "妖魔袭来。", "她反手斩妖。"])
    fragmented = ["碎片"] * 80
    assert split_novel.should_auto_chapter_aware(fragmented, paras)


def test_auto_chapter_aware_guard_ignores_explicitly_small_non_chaptered_text():
    paras = ["荒野风声。", "妖魔袭来。", "她反手斩妖。"]
    fragmented = ["碎片"] * 80
    assert not split_novel.should_auto_chapter_aware(fragmented, paras)
