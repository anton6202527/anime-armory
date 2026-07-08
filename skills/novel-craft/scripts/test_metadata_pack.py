#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import tempfile

import metadata_pack


def test_metadata_pack_passes_with_publish_fields():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "rights_status": "original", "target_platform": "KDP"}, f, ensure_ascii=False)
        args = type("Args", (), {
            "title": "",
            "subtitle": "",
            "series": "",
            "series_number": "",
            "author_name": "作者",
            "short_blurb": "她在雨夜拒婚，换来一座城的追杀。",
            "long_description": "长简介。",
            "keyword": ["拒婚", "玄幻", "女强"],
            "category": ["Fantasy"],
            "age_rating": "16+",
            "content_warning": ["暴力"],
            "target_platform": ["KDP"],
        })()
        pack = metadata_pack.build_pack(root, args)
        check = metadata_pack.check_pack(pack)
        assert check["passed"] is True
        json_path, md_path, check_path = metadata_pack.write_pack(root, pack, check)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)
        assert os.path.exists(check_path)


def test_metadata_pack_blocks_missing_blurb_and_category():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"title": "测试书", "rights_status": "original"}, f, ensure_ascii=False)
        pack = metadata_pack.build_pack(root)
        check = metadata_pack.check_pack(pack)
        ids = {item["id"] for item in check["findings"]}
        assert "METADATA-SHORT_BLURB-MISSING" in ids
        assert "METADATA-CATEGORIES-MISSING" in ids
        assert check["passed"] is False
