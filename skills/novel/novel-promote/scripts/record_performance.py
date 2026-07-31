#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""record_performance.py — 投放战绩回灌：把一部作品发布后的真实投放数据写进
仓库级「自有题材战绩库」`生产战绩/genre_ledger.jsonl`。

存在动机（闭环的写端）：
  novel-score 一直把"第一方实测题材热度（权重高于公榜）"当差异化护城河，它读
  `生产战绩/genre_ledger.jsonl` 里 `kind=="genre_performance_record"` 的行
  （见 score.py `load_genre_ledger` / `summarize_first_party_genre`）。但**全 novel 线
  从来没有任何脚本写这个文件**——消费者有 3 处、生产者 0 处，闭环在写端是断的，
  score 永远走"无自有战绩、由外部回灌"的空降级分支。本脚本补上这个生产者：投放/宣发
  环节拿到发布后真实数据后，回灌成一条 `genre_performance_record`，score 下次评同题材
  作品时就能用上第一方先验。

消费者契约（必须逐字对齐 score.py，改这里务必同改 score 的 metric_keys）：
  行 = {
    "kind": "genre_performance_record",
    "genre": <题材，与项目 _meta.genre 同词表>,
    "subgenres": [<高频套路/子题材>],
    "title": <书名>, "project": <作品根>, "release_id": <可选批次号>,
    "recorded_at": <YYYY-MM-DD>,
    "metrics": {
       "plays": <播放量，score 用作加权权重>,
       "retention_3s", "retention_15s", "completion_rate", "follow_next_rate", "roi"
    },
  }

用法：
  python3 record_performance.py <作品根> --plays 120000 --roi 1.8 \\
      --retention-3s 0.62 --retention-15s 0.41 --completion-rate 0.33 --follow-next-rate 0.28 \\
      [--genre 都市异能] [--subgenres 战神,赘婿] [--release-id 2026Q2-douyin] [--ledger <路径>]

  题材/书名默认从 <作品根>/_meta.json 读取，可用 --genre/--title 覆盖。
  战绩库路径默认 = 环境变量 NOVEL_GENRE_LEDGER，否则仓库根 生产战绩/genre_ledger.jsonl
  （与 score.py default_ledger_path 同解析，保证写读同一文件）。

测试：cd skills/novel/novel-promote/scripts && python3 -m pytest test_record_performance.py
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import sys

# 与 score.py 逐字一致的战绩库定位，确保生产者/消费者命中同一文件。
LEDGER_REL_PATH = os.path.join("生产战绩", "genre_ledger.jsonl")
RECORD_KIND = "genre_performance_record"
# 与 score.summarize_first_party_genre 的 metric_keys 对齐（plays 另作加权权重）。
METRIC_KEYS = ("plays", "retention_3s", "retention_15s", "completion_rate", "follow_next_rate", "roi")
RATE_METRIC_KEYS = {"retention_3s", "retention_15s", "completion_rate", "follow_next_rate"}


def _find_repo_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, "skills")) or os.path.isfile(os.path.join(cur, "AGENTS.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def default_ledger_path(root):
    return os.environ.get("NOVEL_GENRE_LEDGER") or os.path.join(_find_repo_root(root), LEDGER_REL_PATH)


def _load_meta(project):
    path = os.path.join(project, "_meta.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError):
        return {}


def _validate_metric(key, value):
    if value is None:
        return
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{key} 必须是有限数字")
    if key == "plays":
        if int(value) != value or int(value) < 0:
            raise ValueError("plays 必须是非负整数")
    elif key in RATE_METRIC_KEYS:
        if not (0.0 <= float(value) <= 1.0):
            raise ValueError(f"{key} 必须是 0–1 小数（例如 62% 写 0.62）")
    elif key == "roi":
        if float(value) < 0:
            raise ValueError("roi 必须为非负数")


def build_record(project, args, today=None):
    meta = _load_meta(project)
    genre = (args.genre or meta.get("genre") or "").strip()
    if not genre:
        raise ValueError(
            "缺题材：项目 _meta.json 无 genre，且未传 --genre。战绩库按题材聚合，无题材无法回灌。"
        )
    title = (args.title or meta.get("title") or os.path.basename(os.path.abspath(project))) or "待定"
    metrics = {}
    for key in METRIC_KEYS:
        value = getattr(args, key, None)
        if value is not None:
            _validate_metric(key, value)
            metrics[key] = value
    if not metrics:
        raise ValueError("没有任何投放指标（--plays/--roi/--retention-3s …）；空战绩无回灌意义。")
    record = {
        "kind": RECORD_KIND,
        "genre": genre,
        "subgenres": args.subgenres,
        "title": title,
        "project": os.path.abspath(project),
        "release_id": args.release_id,
        "recorded_at": (today or datetime.date.today()).isoformat(),
        "metrics": metrics,
    }
    return record


def append_record(ledger_path, record):
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return ledger_path


def _split_list(value):
    if not value:
        return []
    return [x.strip() for x in value.replace("，", ",").replace("、", ",").split(",") if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(description="把作品发布后真实投放数据回灌进自有题材战绩库")
    ap.add_argument("project_path", help="作品根（创作区/写小说/<书名>/）")
    ap.add_argument("--genre", default=None, help="题材；缺省读 _meta.genre")
    ap.add_argument("--title", default=None, help="书名；缺省读 _meta.title")
    ap.add_argument("--subgenres", default=None, type=_split_list,
                    help="高频套路/子题材，逗号分隔（如 战神,赘婿）")
    ap.add_argument("--release-id", dest="release_id", default=None, help="投放批次号（可选，便于溯源）")
    ap.add_argument("--ledger", default=None, help="战绩库路径；缺省 NOVEL_GENRE_LEDGER 或 仓库根/生产战绩/genre_ledger.jsonl")
    # 投放指标（与消费者契约对齐）：百分比按 0–1 小数填（如 62% → 0.62）。
    ap.add_argument("--plays", type=int, default=None, help="播放量（score 用作题材加权权重）")
    ap.add_argument("--retention-3s", dest="retention_3s", type=float, default=None, help="3 秒留存率 0–1")
    ap.add_argument("--retention-15s", dest="retention_15s", type=float, default=None, help="15 秒留存率 0–1")
    ap.add_argument("--completion-rate", dest="completion_rate", type=float, default=None, help="完播率 0–1")
    ap.add_argument("--follow-next-rate", dest="follow_next_rate", type=float, default=None, help="追更率 0–1")
    ap.add_argument("--roi", type=float, default=None, help="投放 ROI（回报/成本）")
    args = ap.parse_args(argv)

    project = os.path.abspath(args.project_path)
    if args.subgenres is None:
        args.subgenres = []
    record = build_record(project, args)
    ledger_path = args.ledger or default_ledger_path(project)
    append_record(ledger_path, record)
    print(f"[ok] 已回灌战绩 → {ledger_path}")
    print(f"     题材={record['genre']} 书名={record['title']} 指标={record['metrics']}")
    print(f"[next] novel-score 评同题材作品时会读到这条第一方先验（权重高于公榜）。")


if __name__ == "__main__":
    main()
