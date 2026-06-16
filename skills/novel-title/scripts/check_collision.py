#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Book title collision checker.

Combines exact matches from fetched pages and manually supplied search hits.
Manual hits let an agent pass results from browser/web search without relying on
one search engine CLI.
"""
import argparse
import json
import os
import re
from datetime import date
from html.parser import HTMLParser
from urllib.request import Request, urlopen


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = re.sub(r"\s+", " ", data).strip()
        if text:
            self.parts.append(text)


def normalize(text):
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text).lower()


def fetch_parts(url, timeout):
    req = Request(url, headers={"User-Agent": "anime-armory-title-check/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read(1_000_000)
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return parser.parts


def parse_hit(value):
    parts = value.split("|", 3)
    if len(parts) < 2:
        raise argparse.ArgumentTypeError("--hit 格式：候选|命中标题[|URL|平台]")
    return {
        "candidate": parts[0].strip(),
        "title": parts[1].strip(),
        "url": parts[2].strip() if len(parts) >= 3 else "",
        "platform": parts[3].strip() if len(parts) >= 4 else "manual",
    }


def assess(candidates, sources, hits, timeout):
    reports = []
    fetched = []
    for source in sources:
        item = {"url": source, "status": "ok", "parts": []}
        try:
            item["parts"] = fetch_parts(source, timeout)
        except Exception as exc:
            item["status"] = "fetch_error"
            item["error"] = str(exc)
        fetched.append(item)

    manual_hits = [parse_hit(v) for v in hits]
    # 是否真的查了：至少一个来源抓取成功，或给了人工命中。否则 collisions 为空 ≠ 不撞名，
    # 而是「没查」——必须区分，免得零输入时把候选误报成 clear，给假的"书名不撞"信心。
    checked = any(s["status"] == "ok" for s in fetched) or bool(manual_hits)
    for candidate in candidates:
        norm = normalize(candidate)
        collisions = []
        for hit in manual_hits:
            if hit["candidate"] == candidate or normalize(hit["title"]) == norm:
                collisions.append({
                    "type": "manual",
                    "match": hit["title"],
                    "url": hit.get("url", ""),
                    "platform": hit.get("platform", "manual"),
                    "strength": "hard" if normalize(hit["title"]) == norm else "soft",
                })
        for source in fetched:
            if source["status"] != "ok":
                continue
            for part in source["parts"]:
                pnorm = normalize(part)
                if pnorm == norm or (len(norm) >= 4 and norm in pnorm):
                    collisions.append({
                        "type": "source_page",
                        "match": part,
                        "url": source["url"],
                        "platform": "source_page",
                        "strength": "hard" if pnorm == norm else "soft",
                    })
                    break
        hard = any(c["strength"] == "hard" for c in collisions)
        if hard:
            status = "hard_collision"
        elif collisions:
            status = "soft_collision"
        elif checked:
            status = "clear"
        else:
            status = "unchecked"  # 没做任何有效查重——不可视为不撞名
        reports.append({
            "candidate": candidate,
            "status": status,
            "collisions": collisions,
        })
    return reports, fetched


def main():
    ap = argparse.ArgumentParser(description="书名候选撞名检查")
    ap.add_argument("--candidate", action="append", required=True, help="候选书名，可重复")
    ap.add_argument("--source", action="append", default=[], help="要抓取检查的榜单/搜索页 URL")
    ap.add_argument("--hit", action="append", default=[], help="候选|命中标题[|URL|平台]，可重复")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args()

    reports, fetched = assess(args.candidate, args.source, args.hit, args.timeout)
    payload = {
        "schema_version": 1,
        "kind": "novel_title_collision_check",
        "generated_at": args.date,
        "candidates": reports,
        "sources": [{"url": x["url"], "status": x["status"], "error": x.get("error")} for x in fetched],
    }
    os.makedirs(args.out_dir, exist_ok=True)
    json_path = os.path.join(args.out_dir, f"书名撞名检查_{args.date}.json")
    md_path = os.path.join(args.out_dir, f"书名撞名检查_{args.date}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 书名撞名检查 — {args.date}\n\n")
        for item in reports:
            f.write(f"## {item['candidate']} — {item['status']}\n\n")
            if item["status"] == "unchecked":
                f.write("- ⚠️ 未做任何有效查重（无可用来源/命中）——**不可视为不撞名**，请补 --source 或 --hit 重查。\n\n")
                continue
            if not item["collisions"]:
                f.write("- 未发现明确撞名。\n\n")
                continue
            for c in item["collisions"]:
                f.write(f"- {c['strength']} / {c['platform']}：{c['match']} {c.get('url','')}\n")
            f.write("\n")
    print(f"[ok] title collision JSON → {json_path}")
    print(f"[ok] title collision MD   → {md_path}")


if __name__ == "__main__":
    main()
