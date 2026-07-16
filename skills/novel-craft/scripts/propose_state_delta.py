#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Draft a state_delta skeleton for one chapter.

The output is intentionally conservative: it records source fingerprints and
candidate entities/events for a human or LLM pass to confirm before merge.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date


CHAPTER_RE = re.compile(r"第0*(\d+)章")
CJK_NAME_RE = re.compile(r"[\u4e00-\u9fff·]{2,6}")
COMMON_WORDS = {
    "第一章", "第二章", "第三章", "第四章", "第五章", "正文", "忽然", "已经", "这里",
    "他们", "我们", "你们", "自己", "时候", "没有", "什么", "一个", "一样",
    "看向", "拔剑", "出现", "走进", "开口", "冷笑", "转身", "抬手",
}

# 虚词字：任一字命中即丢弃该 2-gram 候选。
#
# 为什么需要它：下面的 fallback 抽取把 >3 字的 CJK 串切成**全部重叠 2-gram**，
# 再按词频排序。中文里最高频的 2-gram 必然是虚词组合，于是 candidate_entities
# 会稳定产出「不是 / 了一 / 的人 / 上的」这类词——实测某 24 章项目全书 257 个候选里
# 词频前列是 `不是(12)、了一(9)、的人(6)`，一个真实体都没有；下游 character_changes
# 因此 24/24 章全空。COMMON_WORDS 是手工黑名单，永远追不上真实语料；改成按**字**
# 过滤才收敛。
FUNCTION_CHARS = set(
    "的了是不在有和就也都这那我你他她它一个上下来去中为以而与等被把给对从向到过着"
    "呢吗吧啊么们很再又还只能会要说道时里外前后大小多少好没相之于其所且但却把"
)
ROSTER_ALIAS_REL = "设定/角色别名.json"
ROSTER_CARD_REL = "设定/角色卡.md"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def chapter_number_from_path(path: str) -> int | None:
    match = CHAPTER_RE.search(os.path.basename(path))
    return int(match.group(1)) if match else None


def find_chapter(root: str, chapter: int) -> str | None:
    cdir = os.path.join(root, "章节")
    if not os.path.isdir(cdir):
        return None
    candidates = []
    for name in os.listdir(cdir):
        if not name.endswith(".md"):
            continue
        path = os.path.join(cdir, name)
        if chapter_number_from_path(path) == chapter:
            candidates.append(path)
    return sorted(candidates)[0] if candidates else None


def candidate_entities(text: str, roster: list[str] | None = None, limit: int = 20) -> list[str]:
    """本章的候选实体，**名册优先**。

    返回两段拼接：① 名册（`设定/角色别名.json` confirmed + 角色卡）里在本章正文实际
    出现过的角色，按出场次数排序——这段是高置信、可直接填进 character_changes 的；
    ② 名册外的 2-gram 盲抽候选，用于发现名册还没登记的新角色。

    ② 段永远是噪音大户（中文最高频 2-gram 就是虚词组合），所以既过滤 FUNCTION_CHARS
    又限量到总额的 1/4；名册非空时它只是补充，名册为空（新项目还没写角色卡）时才是
    唯一来源。调用方须把这里的输出当**提示**而非结论——manual_todo 里明写了要删误抽。
    """
    roster = roster or []
    ranked: list[str] = []

    # ① 名册命中：按本章出场次数排序。长名优先匹配，避免「林」吃掉「林贵妃」的计数。
    hits: dict[str, int] = {}
    for name in sorted(roster, key=lambda n: (-len(n), n)):
        count = text.count(name)
        if count:
            hits[name] = count
    ranked.extend(name for name, _c in sorted(hits.items(), key=lambda kv: (-kv[1], kv[0])))

    # ② 名册外盲抽：仅用于发现未登记的新实体。
    counts: dict[str, int] = {}
    for match in CJK_NAME_RE.finditer(text):
        seq = match.group(0).strip("，。！？；：、（）()《》")
        tokens = [seq] if len(seq) <= 3 else [seq[i:i + 2] for i in range(0, len(seq) - 1)]
        for token in tokens:
            if len(token) < 2 or token in COMMON_WORDS or token in hits:
                continue
            if any(ch in FUNCTION_CHARS for ch in token):
                continue
            if re.search(r"第\d+章", token):
                continue
            counts[token] = counts.get(token, 0) + 1

    discovery_cap = max(1, limit // 4) if ranked else limit
    extra = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ranked.extend(name for name, _count in extra[:discovery_cap])
    return ranked[:limit]


def build_delta(root: str, chapter: int) -> tuple[dict, str]:
    chapter_path = find_chapter(root, chapter)
    if not chapter_path:
        raise FileNotFoundError(f"找不到章节：第{chapter:02d}章")
    with open(chapter_path, encoding="utf-8") as f:
        text = f.read()
    rel = os.path.relpath(chapter_path, root).replace(os.sep, "/")
    # 字段必须与 draft_packets.py 的「状态增量模板」一致——这是本系列 state_delta 的
    # 单一 schema。reconcile_ledger.merge_delta_to_ledger 只消费 new_facts /
    # character_changes / open_threads_added / threads_resolved；其余字段是人审/下章
    # 携带上下文，会随 delta 整体存进账本 summary。键名错配会让 merge 静默写空账本，
    # 故此处刻意复用模板键，并由 test_state_delta_contract.py 守护。
    payload = {
        "schema_version": 1,
        "kind": "novel_state_delta",
        "status": "draft_suggested",
        "generated_at": date.today().isoformat(),
        "chapter": chapter,
        "chapter_file": rel,
        "source_chapter": rel,
        "source_chapter_sha256": sha256_file(chapter_path),
        "candidate_entities": candidate_entities(text),
        "new_facts": [],
        "character_changes": [],
        "relationship_changes": [],
        "open_threads_added": [],
        "threads_resolved": [],
        "reader_contract_progress": [],
        "theme_alignment": "",
        "setting_constraints_added": [],
        "next_chapter_carry": [],
        "manual_todo": [
            "把本章确定发生的状态变化写成可合并条目：new_facts（新设定事实）、"
            "character_changes（[{name,change,state_update}]）、open_threads_added / threads_resolved（线程）。",
            "candidate_entities 仅是抽取提示，挑出真正出场/有变化的角色填进 character_changes，删除误抽实体。",
            "伏笔/关系温度/能力数值变化分别落 open_threads_*、relationship_changes、character_changes.state_update。",
            "relationship_changes 每条 {pair:\"甲↔乙\", temperature:-100..100, label:\"本章关系如何变\", "
            "turning_point:true/false}——logic_sentry.build_relationship_graph 据此构动态关系图检「突变无铺垫」；"
            "label 非空或 turning_point=true 即视为有铺垫（背叛/和解/牺牲等陡转务必写明，否则机检升阻断）。",
            "确认后另存为 审稿/state_delta_第NN章.json 并跑 reconcile_ledger.py。",
        ],
    }
    return payload, chapter_path


def main() -> int:
    ap = argparse.ArgumentParser(description="生成章节 state_delta 草案")
    ap.add_argument("project_root")
    ap.add_argument("--chapter", required=True, type=int)
    ap.add_argument("--out", help="默认 审稿/state_delta_第NN章.suggested.json")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    try:
        payload, chapter_path = build_delta(root, args.chapter)
    except FileNotFoundError as exc:
        print(f"[err] {exc}", file=sys.stderr)
        return 2
    out = args.out or os.path.join(root, "审稿", f"state_delta_第{args.chapter:02d}章.suggested.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[ok] source chapter → {chapter_path}")
    print(f"[ok] suggested delta → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
