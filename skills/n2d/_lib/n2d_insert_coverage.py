#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""非人物特写覆盖（insert coverage）——单一策略真值源。

治「不能时时刻刻都给人镜头」：系统面板 / 关键道具 / 物件 这类信息态桥段应给**专属 insert 特写**，
而不是永远只怼人脸。全线（n2d-script 分镜审计、preventive_contracts 早闸、n2d-review 出片 gate、
n2d-image 景别契约、genre_packs）都调本模块，**策略只在这一处裁决**，不各线复制口径。

三层主体分档（与 n2d_const 词面/模板 id 对齐）：
  · system_panel（系统面板/HUD）：required-eligible，最强档。有证据却无专属 insert → 启用档 block、仅提示档 warn。
  · prop（道具/关键物件）：required-eligible，提示档。有证据却无专属 insert → 一律 warn（不 block）。
  · environment（环境/空镜 cutaway）：只作节奏建议，**永不进配额、永不 block**（易被凑数滥用）。

触发口径 = 题材 + 证据双门控里的「证据」主门：只有本集正文/分镜文本**确有**该类信息态词（系统面板/令牌…）
才要求 insert；纯对话集不会被硬塞空镜。题材键只用于文案与轻度加权，不单独触发。

老项目宽限：`非人物特写覆盖` 选择点缺失 → 默认「仅提示」（全 warn），历史集照常出片、绝不追溯 block。

纯 stdlib·纯函数·可测：`cd skills/n2d/_lib && python -m pytest test_insert_coverage.py`
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

try:  # 单一真值源在 n2d_const；退化兜底仅供独立跑/测试桩，保持与 n2d_const 同步。
    from n2d_const import (
        SYSTEM_INSERT_TEMPLATE_IDS, PROP_INSERT_TEMPLATE_IDS,
        SYSTEM_INSERT_KEYWORDS, PROP_INSERT_KEYWORDS, ENV_CUTAWAY_KEYWORDS,
        INSERT_COVERAGE_MODE_ENFORCE, INSERT_COVERAGE_MODE_WARN, INSERT_COVERAGE_MODE_OFF,
        INSERT_COVERAGE_MODES, INSERT_COVERAGE_MODE_DEFAULT_LEGACY,
    )
except Exception:  # pragma: no cover - 独立分发兜底
    SYSTEM_INSERT_TEMPLATE_IDS = ("system_panel", "screen_insert")
    PROP_INSERT_TEMPLATE_IDS = ("object_discovery", "evidence_search")
    SYSTEM_INSERT_KEYWORDS = ("系统面板", "属性面板", "属性栏", "状态栏", "光幕", "HUD", "血条", "经验条")
    PROP_INSERT_KEYWORDS = ("令牌", "信物", "兵符", "丹药", "卷轴", "秘籍", "玉佩", "证物", "钥匙", "手机")
    ENV_CUTAWAY_KEYWORDS = ("空镜", "远山", "天色", "落叶", "烛火", "月色")
    INSERT_COVERAGE_MODE_ENFORCE = "启用"
    INSERT_COVERAGE_MODE_WARN = "仅提示"
    INSERT_COVERAGE_MODE_OFF = "关闭"
    INSERT_COVERAGE_MODES = (INSERT_COVERAGE_MODE_ENFORCE, INSERT_COVERAGE_MODE_WARN, INSERT_COVERAGE_MODE_OFF)
    INSERT_COVERAGE_MODE_DEFAULT_LEGACY = INSERT_COVERAGE_MODE_WARN

SUBJECT_SYSTEM = "system_panel"
SUBJECT_PROP = "prop"
SUBJECT_ENVIRONMENT = "environment"

# 长镜集才做「全人物」节奏兜底提醒（短集全人物属正常）。
RHYTHM_MIN_CLIPS = 6

# 紧特写档：ECU/CU/大特写/极特写/特写。**不**含 MCU/BCU/中近景/近景（暧昧档 CU 会被 MCU 子串误吞，
# 中景反应镜不该冒充物件 insert）。ASCII 走词边界，CJK 走子串。insert=在紧特写上放大信息态主体，
# 所以「已覆盖」的可信信号 = 专项模板 id ∨（紧特写 + 该类词面）；不给「中景里带过物件/瞟一眼面板」记账。
_TIGHT_CLOSE_RE = re.compile(r"(?<![A-Z])E?CU(?![A-Z])")
_TIGHT_CLOSE_CJK = ("大特写", "极特写", "特写")
# 环境空镜的额外线索（空镜可为远景，故不强求紧特写）。
_ENV_CUES = ("空镜",)

# 选择点原值 → 归一 mode（含别名）。
_MODE_ALIASES = {
    "启用": INSERT_COVERAGE_MODE_ENFORCE, "开启": INSERT_COVERAGE_MODE_ENFORCE,
    "强制": INSERT_COVERAGE_MODE_ENFORCE, "硬闸": INSERT_COVERAGE_MODE_ENFORCE, "enforce": INSERT_COVERAGE_MODE_ENFORCE,
    "仅提示": INSERT_COVERAGE_MODE_WARN, "提示": INSERT_COVERAGE_MODE_WARN, "warn": INSERT_COVERAGE_MODE_WARN,
    "仅警告": INSERT_COVERAGE_MODE_WARN, "advisory": INSERT_COVERAGE_MODE_WARN,
    "关闭": INSERT_COVERAGE_MODE_OFF, "off": INSERT_COVERAGE_MODE_OFF, "禁用": INSERT_COVERAGE_MODE_OFF, "不检": INSERT_COVERAGE_MODE_OFF,
}


def resolve_mode(value: Optional[str], *, default: str = INSERT_COVERAGE_MODE_DEFAULT_LEGACY) -> str:
    """选择点原值 → 归一 mode。缺失/不认得 → default（默认「仅提示」= 老项目宽限，绝不追溯 block）。"""
    if value is None:
        return default
    raw = str(value).strip()
    if not raw:
        return default
    if raw in INSERT_COVERAGE_MODES:
        return raw
    return _MODE_ALIASES.get(raw.lower(), _MODE_ALIASES.get(raw, default))


# ── clip 文本/景别抽取（容多 schema） ─────────────────────────────────────────

def _clip_template(clip: Mapping[str, Any]) -> str:
    tmpl = clip.get("template")
    if not tmpl:
        tc = clip.get("template_contract")
        if isinstance(tc, Mapping):
            tmpl = tc.get("template_id") or tc.get("template")
    return str(tmpl or "").strip()


def clip_text(clip: Mapping[str, Any]) -> str:
    """聚合一个 clip 的可读文本（lens/景别/描述/摘要/母题标签），供词面证据判定。不含台词以免误命中人物对白。"""
    if not isinstance(clip, Mapping):
        return ""
    parts: List[str] = []
    for key in ("desc", "description", "summary", "action", "shot_size", "lens", "景别", "rhythm", "motif_type", "motif_id"):
        val = clip.get(key)
        if isinstance(val, str):
            parts.append(val)
    cont = clip.get("continuity")
    if isinstance(cont, Mapping):
        for key in ("shot_size", "notes", "subject"):
            val = cont.get(key)
            if isinstance(val, str):
                parts.append(val)
    shots = clip.get("shots")
    if isinstance(shots, list):
        for s in shots:
            if isinstance(s, Mapping):
                for key in ("lens", "desc", "action"):
                    val = s.get(key)
                    if isinstance(val, str):
                        parts.append(val)
    parts.append(_clip_template(clip))
    return " ".join(parts)


def _is_tight_close(text: str) -> bool:
    """真·紧特写（ECU/CU/大特写/特写），排除 MCU/BCU/中近景等暧昧档。"""
    if _TIGHT_CLOSE_RE.search(text.upper()):
        return True
    return any(tok in text for tok in _TIGHT_CLOSE_CJK)


def _has_any(text: str, keywords: Sequence[str]) -> bool:
    up = text.upper()
    return any(k.upper() in up for k in keywords)


def clip_insert_subject(clip: Mapping[str, Any]) -> Optional[str]:
    """单 clip → 非人物 insert 主体档（system_panel/prop/environment）或 None（人物/其它）。

    「已覆盖」记账信号（保守，避免把中景反应镜当成 insert 而漏 block）：
      · 强信号=专项镜头模板 id（system_panel/screen_insert/object_discovery/evidence_search）；
      · 弱信号=**紧特写** + 该类主体词面（紧特写怼系统面板/令牌 = 主体是物，不是人）；
      · 环境空镜=环境词 + (紧特写 ∨ 空镜)。"""
    if not isinstance(clip, Mapping):
        return None
    tmpl = _clip_template(clip)
    if tmpl in SYSTEM_INSERT_TEMPLATE_IDS:
        return SUBJECT_SYSTEM
    if tmpl in PROP_INSERT_TEMPLATE_IDS:
        return SUBJECT_PROP
    text = clip_text(clip)
    if not text.strip():
        return None
    tight = _is_tight_close(text)
    if tight and _has_any(text, SYSTEM_INSERT_KEYWORDS):
        return SUBJECT_SYSTEM
    if tight and _has_any(text, PROP_INSERT_KEYWORDS):
        return SUBJECT_PROP
    if _has_any(text, ENV_CUTAWAY_KEYWORDS) and (tight or any(c in text for c in _ENV_CUES)):
        return SUBJECT_ENVIRONMENT
    return None


# ── 集级评估（策略裁决唯一入口） ─────────────────────────────────────────────

def episode_text(clips: Sequence[Mapping[str, Any]]) -> str:
    return " ".join(clip_text(c) for c in clips if isinstance(c, Mapping))


def _finding(code: str, severity: str, subject: str, message: str,
             clips: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    return {"code": code, "severity": severity, "subject": subject,
            "message": message, "clips": list(clips or [])}


def evaluate_episode(
    clips: Sequence[Mapping[str, Any]],
    *,
    source_text: str = "",
    genre_keys: Sequence[str] = (),
    mode: Optional[str] = None,
) -> Dict[str, Any]:
    """集级非人物特写覆盖裁决 → {mode, expect, covered, findings:[{code,severity,subject,message,clips}]}。

    纯函数·不碰 IO。severity ∈ {block, warn}；block 只在 mode=启用 且 system_panel 有证据却无 insert 时出现。"""
    mode = resolve_mode(mode)
    clips = [c for c in clips if isinstance(c, Mapping)]
    result: Dict[str, Any] = {"mode": mode, "expect": {}, "covered": {}, "findings": []}
    if mode == INSERT_COVERAGE_MODE_OFF:
        return result

    blob = (episode_text(clips) + " " + str(source_text or "")).strip()
    expect_system = _has_any(blob, SYSTEM_INSERT_KEYWORDS)
    expect_prop = _has_any(blob, PROP_INSERT_KEYWORDS)
    subjects = [clip_insert_subject(c) for c in clips]
    covered_system = SUBJECT_SYSTEM in subjects
    covered_prop = SUBJECT_PROP in subjects
    any_noncharacter = any(s in (SUBJECT_SYSTEM, SUBJECT_PROP, SUBJECT_ENVIRONMENT) for s in subjects)
    result["expect"] = {"system_panel": expect_system, "prop": expect_prop}
    result["covered"] = {"system_panel": covered_system, "prop": covered_prop, "any_noncharacter": any_noncharacter}

    findings: List[Dict[str, Any]] = []
    gen = "、".join(str(g) for g in genre_keys if g)
    gen_hint = f"（题材：{gen}）" if gen else ""

    if expect_system and not covered_system:
        sev = "block" if mode == INSERT_COVERAGE_MODE_ENFORCE else "warn"
        findings.append(_finding(
            "insert_coverage_system_panel", sev, SUBJECT_SYSTEM,
            f"本集正文/分镜出现系统面板/HUD 信息态桥段{gen_hint}，但没有一个专属系统面板 insert 特写镜"
            f"（template=system_panel/screen_insert 或近景系统面板底框）——别把系统时刻只塞进人物反应镜。"
            f"回 n2d-script 阶段2 给系统面板排一个专属 insert（AI 出锁色锁形空光幕底、文字走 overlay）。"))
    if expect_prop and not covered_prop:
        findings.append(_finding(
            "insert_coverage_prop", "warn", SUBJECT_PROP,
            f"本集出现关键道具/物件（令牌/信物/丹药/证物…）{gen_hint}，但没有专属物件 insert 特写镜"
            f"（template=object_discovery/evidence_search 或近景物件细节）——关键物件建议给一个信息态特写，"
            f"而不是永远只在人物手里带过。"))
    # 题材无关的节奏兜底：长集且全人物、零非人物 cutaway → 软提醒（不 block）。
    if not any_noncharacter and len(clips) >= RHYTHM_MIN_CLIPS and not (expect_system or expect_prop):
        findings.append(_finding(
            "insert_coverage_all_character", "warn", "rhythm", [],
            f"全集 {len(clips)} 镜全是人物取景、无任何系统/道具/环境空镜 cutaway——景别再富也全在人身上，"
            f"考虑给关键信息、物件或环境插一两个非人物特写/空镜调节奏。"))

    result["findings"] = findings
    return result


def has_blocking(result: Mapping[str, Any]) -> bool:
    return any(str(f.get("severity")) == "block" for f in result.get("findings") or [])
