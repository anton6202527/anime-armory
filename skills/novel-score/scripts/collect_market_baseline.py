#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect shared market baseline artifacts for novel-score and self-audit.

The script fetches public rank pages when possible and preserves fetch failures
as evidence instead of inventing trends. Agents may add manual notes from
browser/search inspection with --note.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_SOURCES = [
    ("番茄小说", "https://fanqienovel.com/rank", "web_novel_rank"),
    ("起点中文网", "https://www.qidian.com/rank/", "web_novel_rank"),
    ("晋江文学城", "https://m.jjwxc.net/rank/index", "web_novel_rank"),
]


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._in_title:
            self.title += text
        if len(text) >= 2:
            self.parts.append(text)


def fetch_text(url, timeout):
    req = Request(url, headers={"User-Agent": "anime-armory-novel-baseline/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read(2_000_000)
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return parser.title.strip(), parser.parts


def parse_source(value):
    parts = value.split("|", 2)
    if len(parts) == 2:
        platform, url = parts
        use_for = "web_novel_rank"
    elif len(parts) == 3:
        platform, url, use_for = parts
    else:
        raise argparse.ArgumentTypeError("--source 格式：平台|URL[|use_for]")
    return platform.strip(), url.strip(), use_for.strip()


def collect(args):
    sources = list(DEFAULT_SOURCES) if args.defaults else []
    sources.extend(parse_source(v) for v in args.source)
    now = datetime.now(timezone.utc).astimezone()
    result = {
        "schema_version": 1,
        "kind": "novel_market_baseline",
        "baseline_date": args.date,
        "target_platform": args.target_platform,
        "collected_at": now.isoformat(timespec="seconds"),
        "expires_after_days": args.expires_after_days,
        "sources": [],
        "notes": args.note,
    }
    for platform, url, use_for in sources:
        item = {
            "platform": platform,
            "url": url,
            "use_for": use_for,
            "collected_at": now.isoformat(timespec="seconds"),
            "status": "ok",
            "title": "",
            "signals": [],
        }
        try:
            title, parts = fetch_text(url, args.timeout)
            item["title"] = title or platform
            item["signals"] = parts[:args.max_signals]
        except (OSError, URLError, ValueError) as exc:
            item["status"] = "fetch_error"
            item["error"] = str(exc)
            if not args.allow_fetch_errors:
                result["sources"].append(item)
                raise
        result["sources"].append(item)
    return result


def write_artifacts(result, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    date_s = result["baseline_date"]
    json_path = os.path.join(out_dir, f"market_baseline_{date_s}.json")
    md_path = os.path.join(out_dir, f"题材热榜_{date_s}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 题材热榜基准 — {date_s}\n\n")
        f.write(f"- 目标平台：{result['target_platform']}\n")
        f.write(f"- 采集时间：{result['collected_at']}\n")
        f.write(f"- 过期天数：{result['expires_after_days']}\n\n")
        for source in result["sources"]:
            f.write(f"## {source['platform']}\n\n")
            f.write(f"- URL：{source['url']}\n")
            f.write(f"- 状态：{source['status']}\n")
            if source.get("title"):
                f.write(f"- 页面标题：{source['title']}\n")
            if source.get("error"):
                f.write(f"- 抓取错误：{source['error']}\n")
            signals = source.get("signals") or []
            if signals:
                f.write("\n信号摘录：\n")
                for text in signals[:20]:
                    f.write(f"- {text}\n")
            f.write("\n")
        if result["notes"]:
            f.write("## 人工补充\n\n")
            for note in result["notes"]:
                f.write(f"- {note}\n")
    return json_path, md_path


def main():
    ap = argparse.ArgumentParser(description="采集 novel-score / novel-review 共用市场基准")
    ap.add_argument("out_dir", help="通常为 <作品根>/评分")
    ap.add_argument("--target-platform", default="红果/抖音 商业爽文向")
    ap.add_argument("--date", default=datetime.now().date().isoformat())
    ap.add_argument("--expires-after-days", type=int, default=21)
    ap.add_argument("--source", action="append", default=[], help="平台|URL[|use_for]，可重复")
    ap.add_argument("--no-defaults", dest="defaults", action="store_false")
    ap.add_argument("--note", action="append", default=[], help="从浏览器/搜索人工核验到的趋势备注")
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--max-signals", type=int, default=80)
    ap.add_argument("--allow-fetch-errors", action="store_true")
    args = ap.parse_args()

    try:
        result = collect(args)
    except Exception as exc:
        print(f"[err] 市场基准采集失败：{exc}", file=sys.stderr)
        sys.exit(1)
    json_path, md_path = write_artifacts(result, os.path.abspath(args.out_dir))
    print(f"[ok] market baseline JSON → {json_path}")
    print(f"[ok] market baseline MD   → {md_path}")


if __name__ == "__main__":
    main()
