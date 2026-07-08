#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import author_intent


def test_author_intent_scaffold_and_check_passes_when_core_fields_filled():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书"}, f, ensure_ascii=False)
        args = type("Args", (), {
            "title": "",
            "theme": "选择自由的代价。",
            "aftertaste": "温柔但不轻飘。",
            "non_negotiable": ["主角不能靠降智配角胜利"],
            "aesthetic_boundary": ["克制暴力"],
            "forbidden_trope": ["无代价金手指"],
            "ethical_boundary": ["不美化伤害"],
            "misreading_risk": ["读者可能误以为复仇被鼓励"],
            "comparison_title": ["样本A"],
        })()
        intent = author_intent.build_intent(root, args)
        json_path, md_path = author_intent.write_intent(root, intent)
        report = author_intent.check_intent(root)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        assert report["passed"] is True


def test_author_intent_check_blocks_missing_file():
    with tempfile.TemporaryDirectory() as root:
        report = author_intent.check_intent(root)
        assert report["passed"] is False
        assert report["blocking"] >= 1
