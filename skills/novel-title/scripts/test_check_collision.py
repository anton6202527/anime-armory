#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""check_collision tests. Run: cd skills/novel-title/scripts && python -m pytest test_check_collision.py

All cases avoid network: collision signal comes from manual --hit, never from fetching --source.
"""
import importlib.util
import os
import unittest


HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("check_collision", os.path.join(HERE, "check_collision.py"))
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)


def status_of(candidate, sources=None, hits=None):
    reports, _ = cc.assess([candidate], sources or [], hits or [], timeout=1.0)
    return reports[0]["status"]


class CheckCollisionTest(unittest.TestCase):
    def test_no_input_is_unchecked_not_clear(self):
        # 关键回归：零来源零命中时不能报 clear（那是"没查"，不是"不撞名"）
        self.assertEqual(status_of("逆天小毒妃"), "unchecked")

    def test_hit_without_match_is_clear(self):
        # 给了人工命中=确实查过了；该候选没命中 → clear
        self.assertEqual(status_of("逆天小毒妃", hits=["凤还巢|凤还巢|http://x|抖音"]), "clear")

    def test_exact_hit_is_hard_collision(self):
        self.assertEqual(status_of("逆天小毒妃", hits=["逆天小毒妃|逆天小毒妃|http://x|红果"]), "hard_collision")

    def test_same_candidate_diff_title_is_soft_collision(self):
        self.assertEqual(status_of("逆天小毒妃", hits=["逆天小毒妃|凤还巢|http://x|抖音"]), "soft_collision")


if __name__ == "__main__":
    unittest.main()
