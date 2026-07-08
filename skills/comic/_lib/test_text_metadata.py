#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import text_metadata


def test_rtl_text_requires_advanced_renderer() -> None:
    meta = text_metadata.infer_language_metadata("مرحبا بالعالم", "自定义语言(ar)")
    assert meta["dir"] == "rtl"
    assert meta["line_break"] == "bidi_required"
    assert text_metadata.requires_advanced_text_layout(meta)


def test_chinese_metadata_is_ltr_cjk() -> None:
    meta = text_metadata.infer_language_metadata("你好，世界", "中文")
    assert meta["lang"] == "zh-Hans"
    assert meta["dir"] == "ltr"
    assert meta["line_break"] == "cjk"
