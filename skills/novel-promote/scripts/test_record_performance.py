#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""record_performance 回灌 ↔ score 消费 的闭环回归测试。

从脚本自身目录跑：
    cd skills/novel-promote/scripts && python3 -m pytest test_record_performance.py
"""
import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rp = _load("record_performance", os.path.join(HERE, "record_performance.py"))
score = _load("novel_score", os.path.join(REPO, "skills", "novel-score", "scripts", "score.py"))


def _ns(**kw):
    base = {
        "genre": None, "title": None, "subgenres": [], "release_id": None,
        "plays": None, "retention_3s": None, "retention_15s": None,
        "completion_rate": None, "follow_next_rate": None, "roi": None,
    }
    base.update(kw)
    return type("Args", (), base)()


class RoundTripTest(unittest.TestCase):
    def _project(self, root, genre="都市异能", title="测试书"):
        with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump({"genre": genre, "title": title}, f, ensure_ascii=False)

    def test_producer_row_is_read_by_consumer(self):
        """record_performance 写出的行必须能被 score.load_genre_ledger 识别并聚合。"""
        with tempfile.TemporaryDirectory() as root:
            self._project(root)
            ledger = os.path.join(root, "生产战绩", "genre_ledger.jsonl")
            args = _ns(plays=100000, roi=1.8, retention_3s=0.62, subgenres=["战神", "赘婿"])
            rec = rp.build_record(root, args)
            rp.append_record(ledger, rec)

            records = score.load_genre_ledger(ledger)
            self.assertEqual(len(records), 1, "score 应能读回恰好 1 条 genre_performance_record")
            summary = score.summarize_first_party_genre(records, "都市异能")
            self.assertIsNotNone(summary)
            self.assertEqual(summary["release_count"], 1)
            self.assertEqual(summary["total_plays"], 100000)
            self.assertAlmostEqual(summary["metrics"]["roi"], 1.8)
            self.assertIn("战神", summary["subgenres"])

    def test_metric_keys_match_consumer_contract(self):
        """生产者 METRIC_KEYS 必须与 score 聚合用的键集合完全一致，否则回灌的指标读不到。"""
        # score.summarize_first_party_genre 内联的 metric_keys（plays 也在其中作权重）。
        consumer_keys = {"retention_3s", "retention_15s", "completion_rate", "follow_next_rate", "roi", "plays"}
        self.assertEqual(set(rp.METRIC_KEYS), consumer_keys)

    def test_no_genre_raises(self):
        with tempfile.TemporaryDirectory() as root:
            with open(os.path.join(root, "_meta.json"), "w", encoding="utf-8") as f:
                json.dump({"title": "无题材书"}, f, ensure_ascii=False)
            with self.assertRaises(ValueError):
                rp.build_record(root, _ns(plays=10))

    def test_no_metrics_raises(self):
        with tempfile.TemporaryDirectory() as root:
            self._project(root)
            with self.assertRaises(ValueError):
                rp.build_record(root, _ns())

    def test_metric_ranges_are_validated(self):
        with tempfile.TemporaryDirectory() as root:
            self._project(root)
            bad_cases = [
                ("plays", _ns(plays=-1)),
                ("plays", _ns(plays=1.5)),
                ("retention_3s", _ns(retention_3s=62)),
                ("completion_rate", _ns(completion_rate=-0.1)),
                ("follow_next_rate", _ns(follow_next_rate=1.2)),
                ("roi", _ns(roi=-3)),
            ]
            for key, args in bad_cases:
                with self.subTest(key=key):
                    with self.assertRaises(ValueError):
                        rp.build_record(root, args)

    def test_append_accumulates(self):
        with tempfile.TemporaryDirectory() as root:
            self._project(root)
            ledger = os.path.join(root, "生产战绩", "genre_ledger.jsonl")
            rp.append_record(ledger, rp.build_record(root, _ns(plays=10, roi=1.0)))
            rp.append_record(ledger, rp.build_record(root, _ns(plays=20, roi=2.0)))
            self.assertEqual(len(score.load_genre_ledger(ledger)), 2)


if __name__ == "__main__":
    unittest.main()
