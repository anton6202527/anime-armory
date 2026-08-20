#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Freshness ledger for volatile MV model/channel candidates.

This module is intentionally small and standard-library only. It does not
decide the "best" model; it tells the operator which candidate snapshots are
stale and where the official provenance should be checked.
"""
import argparse
import json
import os
from datetime import date, datetime


STALE_AFTER_DAYS = 90

CANDIDATE_SOURCES = {
    "video_models": {
        "snapshot": "skills/mv/references/candidate_snapshots/video_models.json",
        "description": "MV image-to-video / text-to-video model capability candidates",
        "source_urls": [
            "https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5",
            "https://ai.google.dev/gemini-api/docs/video",
            "https://ai.google.dev/gemini-api/docs/omni",
            "https://help.runwayml.com/hc/en-us/articles/46974685288467-Creating-with-Gen-4-5",
            "https://app.klingai.com/cn/quickstart/klingai-video-3-model-user-guide",
            "https://lumalabs.ai/news/introducing-ray-3-2",
        ],
    },
    "video_channels": {
        "snapshot": "skills/mv/references/candidate_snapshots/video_channels.json",
        "description": "MV video generation channels and integration modes",
        "source_urls": [
            "https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5",
            "https://ai.google.dev/gemini-api/docs/veo",
            "https://ai.google.dev/gemini-api/docs/omni",
            "https://docs.dev.runwayml.com/",
            "https://klingai.kuaishou.com/",
            "https://lumalabs.ai/",
        ],
    },
    "image_backends": {
        "snapshot": "skills/mv/references/candidate_snapshots/image_backends.json",
        "description": "MV image generation backends and consistency capabilities",
        "source_urls": [
            "https://developers.openai.com/api/docs/models/gpt-image-2",
            "https://seed.bytedance.com/en/seedream5_0_lite",
            "https://blog.google/innovation-and-ai/technology/developers-tools/gemini-3-pro-image-developers/",
        ],
    },
}


def repo_root():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def snapshot_path(key, root=None):
    item = CANDIDATE_SOURCES[key]
    base = root or repo_root()
    return os.path.join(base, item["snapshot"])


def load_snapshot(key, root=None):
    path = snapshot_path(key, root)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def age_days(snapshot, today=None):
    today = today or date.today()
    collected = parse_date(snapshot.get("collected_at"))
    if not collected:
        return None
    return (today - collected).days


def stale_report(root=None, today=None, stale_after_days=STALE_AFTER_DAYS):
    today = today or date.today()
    rows = []
    for key, source in CANDIDATE_SOURCES.items():
        snap = load_snapshot(key, root)
        age = age_days(snap, today)
        status = "missing" if not snap else "fresh"
        if age is None and snap:
            status = "unknown"
        elif age is not None and age > stale_after_days:
            status = "stale"
        rows.append({
            "key": key,
            "status": status,
            "age_days": age,
            "snapshot": source["snapshot"],
            "collected_at": snap.get("collected_at"),
            "source_urls": source["source_urls"],
        })
    return rows


def main():
    ap = argparse.ArgumentParser(description="Check MV volatile candidate freshness")
    ap.add_argument("--repo", default=repo_root())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--stale-after-days", type=int, default=STALE_AFTER_DAYS)
    args = ap.parse_args()

    rows = stale_report(args.repo, stale_after_days=args.stale_after_days)
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 1 if any(r["status"] in {"missing", "stale", "unknown"} for r in rows) else 0

    for row in rows:
        age = "unknown" if row["age_days"] is None else f"{row['age_days']}d"
        print(f"{row['status']:7s} {row['key']:14s} age={age} snapshot={row['snapshot']}")
    return 1 if any(r["status"] in {"missing", "stale", "unknown"} for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
