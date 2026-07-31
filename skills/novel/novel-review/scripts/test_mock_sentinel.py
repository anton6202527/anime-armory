#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cd skills/novel/novel-review/scripts && python -m pytest test_mock_sentinel.py"""
import self_audit


def test_mock_marker_regex_matches_known_tells():
    assert self_audit._MOCK_MARKERS.search("Mock for now: retrieve chunks")
    assert self_audit._MOCK_MARKERS.search("Pending Vector DB Implementation")
    assert self_audit._MOCK_MARKERS.search("Pending Full Graph DB Implementation")
    assert not self_audit._MOCK_MARKERS.search("real production retrieval here")
    assert not self_audit._MOCK_MARKERS.search("实体-事件时序图，非 mock")  # 不误伤"非 mock"自述


def test_repo_has_no_mock_stub_residue():
    # 任何 novel-* 脚本回潮 mock 招牌（恒定返回/伪造数据冒充实现）都会让此测试失败。
    blocks = [f for f in self_audit.audit_mock_stubs() if f["severity"] == "block"]
    assert not blocks, [f["title"] for f in blocks]
