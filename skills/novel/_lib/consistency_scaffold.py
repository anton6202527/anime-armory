#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一致性脚手架 — 跨 novel-* 共享的「设定文件」骨架与定位。

存在动机（接缝守护）：
- **B1**：原来只有 novel-create 的 init 会 seed `character_guardrails.json` /
  `power_system_registry.json`；spinoff/rewrite/continue/expand/condense 等派生线
  开局没有这两份注册表，于是 novel-wiki 的 power_system / logic_sentry 护栏检查在
  派生作品上**静默 no-op**——而穿越/系统流的派生恰恰最需要它们。本模块把脚手架收成
  单一真值源，create 与各派生 init 共用，避免骨架 schema 漂移。
- **B2**：create/spinoff/rewrite 写 `设定/角色卡.md`，continue/expand 却写
  `设定/人物.md`，而消费者（wiki_builder / logic_sentry / mechanical_check /
  storyworld_pressure_test / promo_gen）只认 `角色卡.md`，导致派生作品的实体播种与
  术语抽取拿到空文件。`resolve_character_card` 让所有消费者按候选顺序兜底两种命名。

纯函数 + 文件存在性判断，无副作用（写盘由调用方按自己的 idiom 完成）。
"""
from __future__ import annotations

import json
import os
import re
from typing import List, Optional, Tuple

# power_system_defs 与本模块同在 novel/_lib；调用方已把 novel/_lib 加进 sys.path。
from power_system_defs import (
    detect_system_type,
    genre_needs_power_check,
    starter_registry,
)


# ---- B2：角色卡文件命名兜底 -------------------------------------------------

# 候选顺序即优先级：create/spinoff/rewrite 用「角色卡.md」，continue/expand 用「人物.md」。
CHARACTER_CARD_NAMES: Tuple[str, ...] = ("角色卡.md", "人物.md")


def character_card_candidates(project_root: str) -> List[str]:
    """返回所有候选角色卡的绝对路径（按优先级，无论是否存在）。"""
    return [os.path.join(project_root, "设定", name) for name in CHARACTER_CARD_NAMES]


def resolve_character_card(project_root: str) -> Optional[str]:
    """返回第一个**实际存在**的角色卡路径；都不存在返回 None。

    消费者用它替代写死的 `os.path.join(project, "设定", "角色卡.md")`，从而同时认
    `角色卡.md` 与 `人物.md`。"""
    for path in character_card_candidates(project_root):
        if os.path.exists(path):
            return path
    return None


# ---- B3：角色名册（权威实体源）---------------------------------------------
#
# 存在动机：`propose_state_delta.candidate_entities` 原来靠「把 CJK 串切成全部重叠
# 2-gram 再按词频排序」盲抽实体，产出的是「不是 / 了一 / 的人」这类虚词组合，作者
# 面对一堆噪音候选就懒得填 `character_changes`——实测某 24 章项目 24/24 章的
# character_changes / relationship_changes 全空，state_ledger 因此退化成模板。
# 而项目里其实**早就有权威名册**（角色卡 + 人工确认的别名表），只是抽取侧没读。
# 本函数把「名册优先」收成单一真值源，供 craft/wiki/review 各侧共用。

_ROSTER_NAME_RE = re.compile(r"#{1,4}\s+([一-鿿·]{2,6})\s*$")
_ROSTER_FIELD_RE = re.compile(r"(?:姓名|名字|角色)[:：]\s*([一-鿿·]{2,6})")
_ROSTER_ALIAS_RE = re.compile(r"(?:别称|别名|封号|旧名|曾用名|尊称)[:：]\s*(.+)")


def load_character_roster(project_root: str) -> List[str]:
    """返回本项目**已知**的角色规范名 + 别名（去重、按长度降序）。

    两个来源合并：
      1. `设定/角色别名.json`，且仅当 `status == "confirmed"`（人工确认过才算权威；
         draft 期的建议表不参与，与 `alias_scaffold.py` 的口径一致）。
      2. 角色卡（`resolve_character_card` 兜底 `角色卡.md` / `人物.md`）里的
         标题行、`姓名:` 字段与 `别称/封号:` 列表。

    按长度降序返回，让调用方做最长匹配优先（「林贵妃」先于「林」）。
    名册为空是合法的（新项目还没写角色卡）——调用方须自行降级，不要当错误。
    """
    names: set = set()

    alias_path = os.path.join(project_root, "设定", "角色别名.json")
    try:
        with open(alias_path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and str(data.get("status") or "").strip().lower() == "confirmed":
            table = data.get("character_aliases") or data.get("aliases") or {}
            if isinstance(table, dict):
                for canonical, alias_list in table.items():
                    names.add(str(canonical).strip())
                    if isinstance(alias_list, list):
                        names.update(str(a).strip() for a in alias_list)
    except (OSError, ValueError):
        pass

    card = resolve_character_card(project_root)
    if card:
        try:
            with open(card, encoding="utf-8") as f:
                card_text = f.read()
        except OSError:
            card_text = ""
        for line in card_text.splitlines():
            stripped = line.strip()
            for regex in (_ROSTER_NAME_RE, _ROSTER_FIELD_RE):
                match = regex.search(stripped) if regex is _ROSTER_FIELD_RE else regex.match(stripped)
                if match:
                    names.add(match.group(1).strip())
            match = _ROSTER_ALIAS_RE.search(stripped)
            if match:
                for alias in re.split(r"[、，,/\s]+", match.group(1).strip()):
                    if 2 <= len(alias) <= 6:
                        names.add(alias)

    return sorted((n for n in names if n), key=lambda n: (-len(n), n))


# ---- B1：一致性注册表脚手架 -------------------------------------------------

def character_guardrails_skeleton() -> dict:
    """空的角色护栏骨架。logic_sentry 只在 characters 非空时才有约束可查，
    空骨架本身不会误报，只是把文件摆出来供作者/对话逐步填充。"""
    return {
        "schema_version": 1,
        "kind": "novel_character_guardrails",
        "characters": {},
    }


def foreshadow_ledger_skeleton(seeds: Optional[List[dict]] = None) -> dict:
    """伏笔台账骨架（与 novel-wiki/wiki_builder.py 的 seed 同 schema）。

    派生线（continue/condense 等）开局不跑 wiki_builder，于是从无伏笔台账，
    `foreshadow_ledger.analyze()` 永远 `ran:False` 静默跳过——烂尾/超期机检在最需要
    它的续写/精简上空转。

    根治：init 时用 `extract_foreshadow_candidates` 从原作启发式抽「伏笔候选」预播进
    seeds（`auto_extracted=True, confirmed=False`），让 analyze() 一开局就 `ran:True`、给
    作者一份「待确认伏笔」工作清单。**未确认候选永不升阻断、不进回收率分母**——这既保住
    foreshadow_ledger「不做正则式自动识别免得制造噪声」的原则（候选只是提示，由人 confirm/
    drop），又把「机制存在却空转」的静默失效堵上。空 seeds 仍合法（无原作可抽时）。"""
    return {
        "schema_version": 1,
        "kind": "novel_foreshadowing_ledger",
        "seeds": list(seeds or []),
    }


# 高精度伏笔「埋点」叙述标记：中文长篇里这些短语几乎总是作者在埋伏笔/留悬念。
# 刻意选窄、宁缺毋滥——抽出的只是**待人工确认的候选**（不升阻断），故偏向高准确率。
_FORESHADOW_ANCHORS: Tuple[str, ...] = (
    "此乃后话", "后话不提", "暂且不表", "暂按不表", "按下不表", "留待后文",
    "容后再表", "且听下回", "这是后话",
    "殊不知", "却不知", "浑然不知", "哪里知道", "哪里料到", "怎会想到", "未曾想到",
    "日后才", "后来才知", "后来才明白", "后来才发现", "多年以后", "多年后",
    "直到很久以后", "直到后来",
    "埋下伏笔", "埋下了", "种下了", "不祥的预感", "隐隐觉得", "隐隐有种",
    "总觉得哪里", "莫名地觉得", "命运的齿轮", "命中注定", "冥冥之中",
)

# 句子切分：中文标点 + 换行。
_SENT_SPLIT_RE = re.compile(r"[。！？!?…\n]+")
_MAX_AUTO_CANDIDATES = 30  # 候选上限，宁少毋滥——超量说明标记太泛或正文太长，留给人工补 plant。


def split_source_chapters(text: str, chapter_re) -> List[Tuple[int, str]]:
    """把原作整文按 `chapter_re`（novel_contract.CHAPTER_RE）切成 (章号, 正文) 列表。

    章号取标题里的阿拉伯数字；切不出章（无标题/单章）时整文记为第 1 章。纯函数便于单测。"""
    lines = text.splitlines()
    chapters: List[Tuple[int, List[str]]] = []
    cur_no = 0
    cur_buf: List[str] = []
    seen_title = False
    for ln in lines:
        if chapter_re.match(ln):
            if seen_title:
                chapters.append((cur_no, cur_buf))
            seen_title = True
            m = re.search(r"第\s*0*(\d+)", ln)
            cur_no = int(m.group(1)) if m else (cur_no + 1)
            cur_buf = []
        else:
            cur_buf.append(ln)
    if seen_title:
        chapters.append((cur_no, cur_buf))
    if not chapters:  # 无章节标题：整文当第 1 章
        return [(1, text)] if text.strip() else []
    return [(no, "\n".join(buf)) for no, buf in chapters]


def extract_foreshadow_candidates(
    chapters: List[Tuple[int, str]], max_candidates: int = _MAX_AUTO_CANDIDATES
) -> List[dict]:
    """启发式抽「伏笔候选」种子（**待人工确认**，非确证伏笔）。

    对每章正文按高精度叙述标记（`_FORESHADOW_ANCHORS`）命中的句子，生成一条 pending 候选：
    `auto_extracted=True, confirmed=False, expected_payoff_chapter=None`（回收窗口由人确认时
    再定）。下游 foreshadow_ledger 对未确认候选只列清单、永不升阻断、不计回收率分母。

    去重：同章同句只取一次；总量截到 max_candidates。返回的 dict 已是合法 seed 形态，
    直接塞进 ledger['seeds'] 即可。"""
    candidates: List[dict] = []
    seen: set = set()
    idx = 1
    for chap_no, body in chapters:
        if len(candidates) >= max_candidates:
            break
        for sent in _SENT_SPLIT_RE.split(body or ""):
            sent = sent.strip()
            if not sent:
                continue
            hit = next((a for a in _FORESHADOW_ANCHORS if a in sent), None)
            if not hit:
                continue
            desc = sent if len(sent) <= 60 else sent[:57] + "…"
            key = (chap_no, desc)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({
                "id": f"AUTO_{idx:03d}",
                "description": desc,
                "status": "pending",
                "planted_chapter": chap_no,
                "expected_payoff_chapter": None,
                "actual_payoff_chapter": None,
                "importance": "medium",
                "linked_entities": [],
                "evidence": None,
                "auto_extracted": True,
                "confirmed": False,
                "anchor": hit,
            })
            idx += 1
            if len(candidates) >= max_candidates:
                break
    return candidates


def power_system_starter(genre: Optional[str]) -> Optional[dict]:
    """题材需要力量体系自检时返回 starter registry，否则 None（不 seed）。"""
    if not genre or not genre_needs_power_check(genre):
        return None
    return starter_registry(detect_system_type(genre))


def consistency_registry_files(
    genre: Optional[str] = None, foreshadow_seeds: Optional[List[dict]] = None
) -> List[Tuple[str, str]]:
    """返回应 seed 的 (相对路径, JSON 文本) 列表，调用方用自己的写盘 idiom 落盘。

    - `character_guardrails.json`：**始终** seed（与题材无关，空骨架安全）。
    - `foreshadowing_ledger.json`：seed 伏笔台账；`foreshadow_seeds`（由
      `extract_foreshadow_candidates` 从原作抽的待确认候选）非空时预播进去，让 analyze()
      一开局就 `ran:True` 并给作者待确认清单（派生线最需要伏笔回收却最易空转）。
    - `power_system_registry.json`：仅当 `genre` 命中力量题材时 seed starter。
    """
    files: List[Tuple[str, str]] = [
        (
            "设定/character_guardrails.json",
            json.dumps(character_guardrails_skeleton(), ensure_ascii=False, indent=2),
        ),
        (
            "设定/foreshadowing_ledger.json",
            json.dumps(foreshadow_ledger_skeleton(foreshadow_seeds), ensure_ascii=False, indent=2),
        ),
    ]
    registry = power_system_starter(genre)
    if registry is not None:
        files.append(
            (
                "设定/power_system_registry.json",
                json.dumps(registry, ensure_ascii=False, indent=2),
            )
        )
    return files
