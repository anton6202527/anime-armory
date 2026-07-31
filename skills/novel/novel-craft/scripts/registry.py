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
        "name": "novel-observe",
        "role": "material",
        "summary": "living-material observation bank and field notes",
    },
    {
        "name": "novel-aesthetic",
        "role": "craft",
        "summary": "positive craft samples and aesthetic judgement bank",
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
        "name": "novel-edit",
        "role": "edit",
        "summary": "layered editorial assessment and revision planning",
    },
    {
        "name": "novel-score",
        "role": "qa",
        "summary": "market and quality scoring",
    },
    {
        "name": "novel-research",
        "role": "research",
        "summary": "professional evidence packets for specialist scenes",
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
        "name": "novel-feedback",
        "role": "qa",
        "summary": "real reader telemetry ingestion and drop-off summaries",
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
        "name": "novel-localize",
        "role": "localize",
        "summary": "overseas localization: glossary-locked translation + cultural adaptation",
    },
    {
        "name": "novel-settings",
        "role": "settings",
        "summary": "audit and update private project settings for novel choice points",
    },
    {
        "name": "novel-progress",
        "role": "progress",
        "summary": "read-only progress dashboard for novel projects",
    },
    {
        "name": "novel-update",
        "role": "maintenance",
        "summary": "skill content snapshot diff and minimal rework plan for novel projects",
    },
    {
        "name": "novel-dashboard",
        "role": "dashboard",
        "summary": "read-only production control dashboard for pipeline, QA, revision, batch, and release signals",
    },
    {
        "name": "novel-supervisor",
        "role": "orchestration",
        "summary": "read-only next-action recommender: 读 pipeline plan/review·QA/revision/batch/circuit 信号→输出下一步安全动作(命令+角色+handoff)；不执行·不循环·不调模型·不写正文",
    },
    {
        "name": "novel-batch",
        "role": "orchestration",
        "summary": "local file-backed batch queue for parallel review/score/dashboard tasks",
    },
]


def skill_names():
    return tuple(item["name"] for item in NOVEL_SKILLS)


def skill_by_name(name):
    for item in NOVEL_SKILLS:
        if item["name"] == name:
            return dict(item)
    return None
