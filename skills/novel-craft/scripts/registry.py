#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine-readable roster for the novel-* skill family."""


NOVEL_SKILLS = [
    {
        "name": "novel",
        "role": "dispatcher",
        "summary": "route/import/resume novel projects",
    },
    {
        "name": "novel-create",
        "role": "create",
        "summary": "cold-start original novel projects",
    },
    {
        "name": "novel-title",
        "role": "ideation",
        "summary": "title candidates and title scoring",
    },
    {
        "name": "novel-fetch",
        "role": "source",
        "summary": "fetch public-domain/source novels",
    },
    {
        "name": "novel-craft",
        "role": "shared",
        "summary": "shared contracts, gates, drafting helpers",
    },
    {
        "name": "novel-expand",
        "role": "transform",
        "summary": "expand short text into fuller chapters",
    },
    {
        "name": "novel-condense",
        "role": "transform",
        "summary": "condense long text into shorter form",
    },
    {
        "name": "novel-continue",
        "role": "transform",
        "summary": "continue after the existing ending",
    },
    {
        "name": "novel-rewrite",
        "role": "transform",
        "summary": "rewrite with changed premise/settings",
    },
    {
        "name": "novel-spinoff",
        "role": "transform",
        "summary": "locked-event side story or POV spinoff",
    },
    {
        "name": "novel-review",
        "role": "qa",
        "summary": "quality review and process self-audit",
    },
    {
        "name": "novel-score",
        "role": "qa",
        "summary": "market and quality scoring",
    },
    {
        "name": "novel-style",
        "role": "qa",
        "summary": "style fingerprint and drift checks",
    },
    {
        "name": "novel-wiki",
        "role": "qa",
        "summary": "dynamic encyclopedia and logic sentry",
    },
    {
        "name": "novel-simulate",
        "role": "qa",
        "summary": "simulated reader retention signals",
    },
    {
        "name": "novel-balance",
        "role": "qa",
        "summary": "plot heatmap and pacing balance",
    },
    {
        "name": "novel-promote",
        "role": "promotion",
        "summary": "promotion hooks and short-video scripts",
    },
    {
        "name": "novel-progress",
        "role": "progress",
        "summary": "read-only progress dashboard for novel projects",
    },
]


def skill_names():
    return tuple(item["name"] for item in NOVEL_SKILLS)


def skill_by_name(name):
    for item in NOVEL_SKILLS:
        if item["name"] == name:
            return dict(item)
    return None
