#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""n2d source analysis.

Builds a local analysis package from the n2d project's own source text. This
keeps stage-1 scaffolding self-contained: no upstream project ledger or export
schema is required.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable, Sequence


KIND = "n2d_source_analysis"
ANALYSIS_JSON_REL = os.path.join("设定库", "source_analysis.json")
ANALYSIS_MD_REL = os.path.join("设定库", "source_analysis.md")

CHAPTER_RE = re.compile(r"^\s*第\s*([0-9零一二三四五六七八九十百千两]+)\s*[章回节卷]")
SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?；;])")
SPEECH_VERB_RE = re.compile(
    r"([一-龥]{2,4})(?:[，,、]?\s*)"
    r"(?:低声|沉声|冷声|淡淡|忽然|立刻|缓缓|咬牙|皱眉|抬头|转身|一笑|冷笑|苦笑|"
    r"问道|说道|喝道|喊道|怒道|笑道|问|说|道|喊|喝|叫|答|看着|望着|盯着|推门|拔剑|跪下|起身)"
)
TITLE_NAME_RE = re.compile(r"(?:我是|本座|老夫|贫道|臣|妾身|在下)([一-龥]{2,4})")

STOP_NAMES = {
    "第一", "第二", "第三", "这一", "那一", "所有", "众人", "他们", "她们", "你们", "我们", "自己",
    "这个", "那个", "什么", "怎么", "只是", "已经", "突然", "这里", "那里", "眼前", "身后",
    "时候", "声音", "男人", "女人", "少年", "少女", "老人", "系统", "面板", "灵气", "众弟子",
}
STOP_ENDINGS = ("时候", "声音", "眼神", "脸色", "身影", "心中", "门口", "台下", "众人", "所有")

LOCATION_SUFFIXES = (
    "殿", "宫", "楼", "阁", "城", "山", "峰", "谷", "院", "府", "堂", "厅", "门", "宗", "派",
    "村", "镇", "街", "巷", "河", "湖", "岛", "洞府", "战场", "客栈", "书房", "房间", "后院",
)
LOCATION_RE = re.compile(
    r"(?:来到|进入|走进|回到|赶到|站在|坐在|藏在|冲进|逃进|离开|穿过)"
    r"([一-龥]{2,14}(?:" + "|".join(re.escape(s) for s in LOCATION_SUFFIXES) + r"))"
)

FORESHADOW_MARKERS = (
    "伏笔", "悬念", "埋下", "未解", "成谜", "暗藏", "别有深意", "意味深长",
    "似乎另有", "不为人知", "秘密", "真相", "线索", "钥匙", "印记", "玉佩", "令牌",
)
REALM_TERMS = (
    "练气", "筑基", "金丹", "元婴", "化神", "炼虚", "合体", "大乘", "渡劫",
    "武徒", "武者", "武师", "宗师", "大宗师", "先天", "后天", "觉醒", "超凡", "神通",
)
SYSTEM_TERMS = ("系统", "面板", "属性", "等级", "经验值", "任务", "签到", "抽奖", "积分", "战力")
STATE_TERMS = (
    "受伤", "重伤", "中毒", "失明", "毁容", "断臂", "白发", "黑化", "觉醒",
    "换上", "战甲", "嫁衣", "面具", "蒙面", "破损", "血迹",
)
GENRE_SIGNALS = {
    "系统流": ("系统", "面板", "签到", "任务", "抽奖", "奖励"),
    "修仙/玄幻": ("练气", "筑基", "灵根", "宗门", "妖兽", "法宝", "丹药", "渡劫"),
    "都市异能": ("觉醒", "异能", "都市", "公司", "警局", "医院", "学校"),
    "女频情感": ("婚约", "夫人", "王爷", "侯府", "总裁", "离婚", "重逢", "心动"),
    "悬疑": ("尸体", "凶手", "线索", "证据", "案发", "真相", "监控"),
}


def read_text(path: str) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8", "utf-8-sig", "gb18030", "gbk", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def normalize_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\r?\n+", text or "") if p.strip()]


def split_sentences(text: str) -> list[str]:
    out: list[str] = []
    for para in normalize_paragraphs(text):
        out.extend(s.strip() for s in SENT_SPLIT_RE.split(para) if s.strip())
    return out


def chapter_count(text: str) -> int:
    return sum(1 for p in normalize_paragraphs(text) if CHAPTER_RE.match(p))


def clean_name(name: str) -> str:
    return re.sub(r"[，,。！？!?；;：“”\"'、\s]", "", name or "")


def valid_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 4:
        return False
    if name in STOP_NAMES:
        return False
    if any(name.endswith(s) for s in STOP_ENDINGS):
        return False
    return True


def extract_characters(text: str, limit: int = 16) -> list[dict]:
    counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = defaultdict(list)
    for sentence in split_sentences(text):
        for rx in (SPEECH_VERB_RE, TITLE_NAME_RE):
            for raw in rx.findall(sentence):
                name = clean_name(raw)
                if not valid_name(name):
                    continue
                counts[name] += 1
                if len(evidence[name]) < 3:
                    evidence[name].append(sentence[:80])
    return [
        {"name": name, "mentions": count, "evidence": evidence[name]}
        for name, count in counts.most_common(limit)
    ]


def extract_locations(text: str, limit: int = 12) -> list[dict]:
    counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = defaultdict(list)
    for sentence in split_sentences(text):
        for raw in LOCATION_RE.findall(sentence):
            loc = raw.strip("，,。！？!?；;：“”\"'、 ")
            if len(loc) < 2:
                continue
            counts[loc] += 1
            if len(evidence[loc]) < 2:
                evidence[loc].append(sentence[:80])
    return [
        {"name": name, "mentions": count, "evidence": evidence[name]}
        for name, count in counts.most_common(limit)
    ]


def extract_foreshadowing(text: str, limit: int = 20) -> list[dict]:
    candidates: list[dict] = []
    seen: set[str] = set()
    for sentence in split_sentences(text):
        if not any(marker in sentence for marker in FORESHADOW_MARKERS):
            continue
        desc = re.sub(r"\s+", "", sentence)[:60]
        if desc in seen:
            continue
        seen.add(desc)
        candidates.append({
            "id": f"SETUP_{len(candidates) + 1:03d}",
            "description": desc,
            "status": "candidate",
            "payoff_ep": "",
        })
        if len(candidates) >= limit:
            break
    return candidates


def extract_power_system(text: str) -> dict:
    realm_hits = [term for term in REALM_TERMS if term in text]
    system_hits = [term for term in SYSTEM_TERMS if term in text]
    return {
        "has_power_system_signal": bool(realm_hits or system_hits),
        "realm_terms": realm_hits,
        "system_terms": system_hits,
        "notes": "候选项来自 n2d 源文本启发式扫描；正式等级/数值规则需在阶段1精修时人工确认。",
    }


def extract_visual_state_signals(text: str, limit: int = 24) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for sentence in split_sentences(text):
        hits = [term for term in STATE_TERMS if term in sentence]
        if not hits:
            continue
        snippet = re.sub(r"\s+", "", sentence)[:70]
        if snippet in seen:
            continue
        seen.add(snippet)
        out.append({"signal": hits[0], "snippet": snippet})
        if len(out) >= limit:
            break
    return out


def infer_genres(text: str) -> list[dict]:
    scores = []
    for genre, terms in GENRE_SIGNALS.items():
        hits = [term for term in terms if term in text]
        if hits:
            scores.append({"genre": genre, "score": len(hits), "signals": hits})
    return sorted(scores, key=lambda item: item["score"], reverse=True)


def summarize_worldview(text: str, limit: int = 8) -> list[str]:
    paras = [p for p in normalize_paragraphs(text) if not CHAPTER_RE.match(p)]
    picked: list[str] = []
    signal_words = ("世界", "灵气", "王朝", "宗门", "系统", "异能", "朝堂", "都市", "末世", "学院", "大陆")
    for para in paras:
        clean = re.sub(r"\s+", "", para)
        if len(clean) > 140:
            continue
        if any(word in clean for word in signal_words) or len(picked) < 3:
            picked.append(clean[:100])
        if len(picked) >= limit:
            break
    return picked


def episode_briefs(episodes: Sequence[str], limit: int = 12) -> list[dict]:
    briefs = []
    for i, ep_text in enumerate(episodes[:limit], 1):
        clean = re.sub(r"\s+", "", ep_text or "")
        briefs.append({
            "episode": f"第{i}集",
            "chars": len(clean),
            "opening": clean[:80],
            "ending": clean[-80:],
        })
    return briefs


def analyze_source(title: str, text: str, episodes: Sequence[str] | None = None) -> dict:
    normalized = "\n".join(normalize_paragraphs(text))
    return {
        "schema_version": 1,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "title": title,
        "source": "n2d_source_text",
        "stats": {
            "characters": len(re.sub(r"\s+", "", normalized)),
            "chapters": chapter_count(normalized),
            "episode_scaffolds": len(episodes or []),
        },
        "genre_candidates": infer_genres(normalized),
        "worldview_candidates": summarize_worldview(normalized),
        "characters": extract_characters(normalized),
        "locations": extract_locations(normalized),
        "foreshadowing_candidates": extract_foreshadowing(normalized),
        "power_system": extract_power_system(normalized),
        "visual_state_signals": extract_visual_state_signals(normalized),
        "episode_briefs": episode_briefs(episodes or []),
    }


def render_character_roster(title: str, analysis: dict) -> str:
    lines = [
        f"# {title} — 角色卡总表",
        "",
        "> 本表由 n2d 源书分析预填候选；定妆前必须人工确认姓名、角色定位、视觉特征和形态变体。",
        "> 全篇首次出现即建卡，后续所有镜头严格复用。格式见 references/formats.md。",
        "",
    ]
    characters = analysis.get("characters") or []
    if not characters:
        lines += [
            "## 待建角色",
            "- 来源：源书分析未稳定识别具名角色；阶段1精修时按首现顺序补齐。",
            "- 视觉特征（脸/发/瞳/体型/服装）：（待补：定妆前必填）",
            "",
        ]
        return "\n".join(lines) + "\n"
    for item in characters:
        name = item.get("name") or "未命名"
        lines += [
            f"## {name}",
            f"- 源书命中次数：{item.get('mentions', 0)}",
            "- 角色定位：（待人工确认）",
            "- 当前状态：（待人工确认）",
            "- 视觉特征（脸/发/瞳/体型/服装）：（待补：定妆前必填）",
        ]
        evidence = item.get("evidence") or []
        if evidence:
            lines.append(f"- 首批证据：{evidence[0]}")
        lines.append("")
    return "\n".join(lines) + "\n"


def render_analysis_md(analysis: dict) -> str:
    title = analysis.get("title") or "未命名"
    stats = analysis.get("stats") or {}
    lines = [
        f"# {title} — n2d 源书分析包",
        "",
        "> 本文件由 n2d-script 从本剧源文本直接生成，只作为阶段1改编/建卡/分镜的候选资料。",
        "> 候选项必须经人工确认后，才进入角色卡、世界观、伏笔账本或力量体系规则。",
        "",
        "## 统计",
        f"- 正文字数估算：{stats.get('characters', 0)}",
        f"- 章节数：{stats.get('chapters', 0)}",
        f"- 粗切集数：{stats.get('episode_scaffolds', 0)}",
        "",
    ]
    genres = analysis.get("genre_candidates") or []
    lines.append("## 题材候选")
    if genres:
        for g in genres:
            lines.append(f"- {g['genre']}：{', '.join(g.get('signals') or [])}")
    else:
        lines.append("- （未稳定识别，阶段1人工确认）")
    lines += ["", "## 世界观候选"]
    for item in analysis.get("worldview_candidates") or ["（待阶段1补写）"]:
        lines.append(f"- {item}")
    lines += ["", "## 角色候选"]
    chars = analysis.get("characters") or []
    if chars:
        for c in chars:
            lines.append(f"- {c.get('name')}（命中 {c.get('mentions', 0)} 次）")
    else:
        lines.append("- （未稳定识别，按首现手工建卡）")
    lines += ["", "## 场景候选"]
    locs = analysis.get("locations") or []
    if locs:
        for loc in locs:
            lines.append(f"- {loc.get('name')}（命中 {loc.get('mentions', 0)} 次）")
    else:
        lines.append("- （待阶段1补写）")
    lines += ["", "## 伏笔候选"]
    setups = analysis.get("foreshadowing_candidates") or []
    if setups:
        for setup in setups:
            lines.append(f"- {setup.get('id')}：{setup.get('description')}（payoff_ep 待填）")
    else:
        lines.append("- （未检测到显式伏笔标记；精修时仍需人工登记）")
    ps = analysis.get("power_system") or {}
    lines += ["", "## 力量体系候选"]
    lines.append(f"- 等级/境界词：{', '.join(ps.get('realm_terms') or []) or '（无）'}")
    lines.append(f"- 系统/数值词：{', '.join(ps.get('system_terms') or []) or '（无）'}")
    lines.append(f"- 备注：{ps.get('notes', '')}")
    return "\n".join(lines) + "\n"


def write_analysis(root: str, title: str, text: str, episodes: Sequence[str] | None = None) -> dict:
    analysis = analyze_source(title, text, episodes)
    root_path = Path(root)
    json_path = root_path / ANALYSIS_JSON_REL
    md_path = root_path / ANALYSIS_MD_REL
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_analysis_md(analysis), encoding="utf-8")
    return analysis


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="从 n2d 源文本生成本线源书分析包")
    ap.add_argument("source_text")
    ap.add_argument("--root", required=True, help="n2d 作品根")
    ap.add_argument("--title", default=None)
    ns = ap.parse_args(argv)
    text = read_text(ns.source_text)
    title = ns.title or os.path.splitext(os.path.basename(ns.source_text))[0]
    analysis = write_analysis(ns.root, title, text)
    print(f"[ok] 已写 {ANALYSIS_JSON_REL} / {ANALYSIS_MD_REL}："
          f"角色候选 {len(analysis.get('characters') or [])}，"
          f"场景候选 {len(analysis.get('locations') or [])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
