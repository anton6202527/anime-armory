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


# ---- B1：一致性注册表脚手架 -------------------------------------------------

def character_guardrails_skeleton() -> dict:
    """空的角色护栏骨架。logic_sentry 只在 characters 非空时才有约束可查，
    空骨架本身不会误报，只是把文件摆出来供作者/对话逐步填充。"""
    return {
        "schema_version": 1,
        "kind": "novel_character_guardrails",
        "characters": {},
    }


def power_system_starter(genre: Optional[str]) -> Optional[dict]:
    """题材需要力量体系自检时返回 starter registry，否则 None（不 seed）。"""
    if not genre or not genre_needs_power_check(genre):
        return None
    return starter_registry(detect_system_type(genre))


def consistency_registry_files(genre: Optional[str] = None) -> List[Tuple[str, str]]:
    """返回应 seed 的 (相对路径, JSON 文本) 列表，调用方用自己的写盘 idiom 落盘。

    - `character_guardrails.json`：**始终** seed（与题材无关，空骨架安全）。
    - `power_system_registry.json`：仅当 `genre` 命中力量题材时 seed starter。
    """
    files: List[Tuple[str, str]] = [
        (
            "设定/character_guardrails.json",
            json.dumps(character_guardrails_skeleton(), ensure_ascii=False, indent=2),
        )
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
