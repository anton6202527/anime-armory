#!/usr/bin/env python3
# coding: utf-8
"""alias_scaffold.py — 角色别名表**生产侧脚手架**：从 角色卡/动态百科 抽候选别名 → 人确认入硬闸。

为什么需要：实体消解是确定性一致性闸的强制前置（arXiv 2506.05939：未消解实体→自信地漏判）。
graph_sentry 的生命周期硬闸**消费** {别名->规范名} 映射，但此前**没有生产者**——作者得手写
`character_aliases`，缺表则"死亡记在本名、复现记在封号"被硬闸悄悄漏掉。本脚手架闭合那个环：
  1) 从 设定/角色卡.md 逐角色块抽 别称/封号/旧名/曾用名/尊称（正则兜底·高置信）；
  2) 并入 设定/动态百科.json 各角色条目里的 aliases/别名；
  3) 额外扫正文做**共现/连通分量聚类**：只把簇写成 candidate_clusters 供人确认，不自动进硬闸；
  4) 写 **候选** 设定/角色别名.json（status="draft"），列出 {规范名: [别名...]} 供人核对。

**人确认才入硬闸**：自动抽取可能把两个不同角色误并（如同名封号），所以 graph_sentry.load_curated_alias_map
只在作者把 status 改成 "confirmed" 后才让该表参与确定性归一。draft 期间只是建议，不影响判定。

纯标准库·可测：cd skills/novel-wiki/scripts && python3 -m pytest test_alias_scaffold.py
"""
import os
import re
import sys
import json
import argparse
from glob import glob

_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (_HERE, os.path.join(_HERE, "..", "..", "novel", "_lib")):
    _p = os.path.abspath(_p)
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from consistency_scaffold import resolve_character_card
except Exception:  # pragma: no cover
    def resolve_character_card(project_root):
        for rel in ("设定/角色卡.md", "设定/人物.md"):
            p = os.path.join(project_root, rel)
            if os.path.isfile(p):
                return p
        return None

_CJK = r"一-鿿"
_NAME = r"[" + _CJK + r"·]{2,8}"
_ALIAS_LABEL = re.compile(r"(?:别称|别名|封号|旧名|曾用名|尊称|又称|绰号|外号|化名|人称)[:：]\s*(.+)")
_HEADING = re.compile(r"^#{1,4}\s+(" + _NAME + r")\s*$")
_NAME_FIELD = re.compile(r"(?:姓名|名字|本名|角色)[:：]\s*(" + _NAME + r")")
_MENTION_RE = re.compile(_NAME)
_TITLE_MENTION_RE = re.compile(r"[" + _CJK + r"·]{1,4}(?:贵妃|娘娘|王爷|摄政王|郡主|公主|将军|真人|师兄|师姐|先生|殿下|陛下|尊者|老祖)")
_STOP_NAMES = {
    "身份", "性格", "目标", "动机", "能力", "武器", "道具", "地点", "章节", "标题", "主角", "女主", "男主",
    "系统", "任务", "今日", "明日", "之后", "之前", "眼前", "心中", "手中", "这里", "那里", "众人", "所有人",
    "这一刻", "那一刻", "与此同时", "不由得", "忍不住", "下意识", "仿佛", "似乎",
}
_WINDOW = 120
_MIN_EDGE_COUNT = 2


def _load_json(path):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _split_aliases(raw):
    out = []
    for a in re.split(r"[、，,/\s]+", str(raw or "").strip()):
        a = a.strip("（）()。 ")
        if 2 <= len(a) <= 8 and re.fullmatch(r"[" + _CJK + r"·]+", a or ""):
            out.append(a)
    return out


def parse_card_aliases(project_root):
    """从 角色卡.md 逐块抽 {规范名: [别名...]}。规范名=最近的标题/姓名字段，别名=其块内别称类行。"""
    card = resolve_character_card(project_root)
    out = {}
    if not card or not os.path.isfile(card):
        return out
    with open(card, encoding="utf-8") as f:
        lines = f.read().splitlines()
    current = None
    for ln in lines:
        s = ln.strip()
        m = _HEADING.match(s)
        if m:
            current = m.group(1)
            out.setdefault(current, [])
            continue
        m = _NAME_FIELD.search(s)
        if m:
            current = m.group(1)
            out.setdefault(current, [])
        m = _ALIAS_LABEL.search(s)
        if m and current:
            for a in _split_aliases(m.group(1)):
                if a != current and a not in out[current]:
                    out[current].append(a)
    return {k: v for k, v in out.items() if v}  # 只留真有别名的角色


def parse_card_characters(project_root):
    """从角色卡抽规范名种子（即使没有别名也要作为共现聚类锚点）。"""
    card = resolve_character_card(project_root)
    out = []
    if not card or not os.path.isfile(card):
        return out
    with open(card, encoding="utf-8") as f:
        for ln in f:
            s = ln.strip()
            for pattern in (_HEADING, _NAME_FIELD):
                m = pattern.search(s)
                if m:
                    name = m.group(1)
                    if name not in out:
                        out.append(name)
    return out


def parse_wiki_aliases(project_root):
    """从 设定/动态百科.json 各角色条目抽 {规范名: [别名...]}（aliases/别名/also_known_as）。"""
    data = _load_json(os.path.join(project_root, "设定", "动态百科.json"))
    out = {}
    if not isinstance(data, dict):
        return out
    chars = data.get("characters")
    items = chars.items() if isinstance(chars, dict) else (
        [(c.get("name") or c.get("canonical"), c) for c in chars] if isinstance(chars, list) else [])
    for name, entry in items:
        if not name or not isinstance(entry, dict):
            continue
        al = entry.get("aliases") or entry.get("别名") or entry.get("also_known_as") or []
        aliases = _split_aliases("、".join(al)) if isinstance(al, list) else _split_aliases(al)
        aliases = [a for a in aliases if a != name]
        if aliases:
            out.setdefault(name, [])
            for a in aliases:
                if a not in out[name]:
                    out[name].append(a)
    return out


def parse_wiki_characters(project_root):
    data = _load_json(os.path.join(project_root, "设定", "动态百科.json"))
    if not isinstance(data, dict):
        return []
    chars = data.get("characters")
    if isinstance(chars, dict):
        return [str(k) for k in chars if k]
    if isinstance(chars, list):
        out = []
        for c in chars:
            if isinstance(c, dict):
                name = c.get("name") or c.get("canonical")
                if name:
                    out.append(str(name))
        return out
    return []


def character_seeds(project_root):
    seeds = []
    for name in parse_card_characters(project_root) + parse_wiki_characters(project_root):
        if name and name not in seeds:
            seeds.append(name)
    return seeds


def _chapter_number(path):
    m = re.search(r"第0*(\d+)章", os.path.basename(path))
    return int(m.group(1)) if m else 0


def _chapter_files(project_root):
    return sorted(glob(os.path.join(project_root, "章节", "第*章*.md")),
                  key=lambda p: (_chapter_number(p), os.path.basename(p)))


def _mentions(text):
    out = []
    for m in _TITLE_MENTION_RE.finditer(text or ""):
        name = m.group(0)
        if name in _STOP_NAMES:
            continue
        if name not in out:
            out.append(name)
    return out


def _name_spans(text, seeds):
    """正文 mention span：种子名精确匹配 + 称号后缀候选。避免泛 CJK 正则吞整句。"""
    spans = []
    seen = set()
    for name in sorted(set(seeds), key=len, reverse=True):
        if not name:
            continue
        for m in re.finditer(re.escape(name), text or ""):
            key = (name, m.start(), m.end())
            if key not in seen:
                seen.add(key)
                spans.append(key)
    for m in _TITLE_MENTION_RE.finditer(text or ""):
        name = m.group(0)
        if name in _STOP_NAMES:
            continue
        key = (name, m.start(), m.end())
        if key not in seen:
            seen.add(key)
            spans.append(key)
    return sorted(spans, key=lambda x: x[1])


def _snip(text, start, end, pad=28):
    lo = max(0, start - pad)
    hi = min(len(text), end + pad)
    return re.sub(r"\s+", "", text[lo:hi])


def cooccurrence_clusters(project_root, seeds=None, min_edge_count=_MIN_EDGE_COUNT):
    """正文共现连通分量候选。只写 candidate_clusters，不生成 confirmed 映射。

    规则保守：同一窗口里**恰好一个**角色卡/百科种子名 + 一个或多个未知候选名，才把未知名连到该种子。
    多个种子同窗视为场景共现，跳过，避免把不同角色误并。边出现次数不足 min_edge_count 也跳过。
    """
    seeds = seeds or character_seeds(project_root)
    seed_set = set(seeds)
    edge_counts = {}
    evidence = {}
    for path in _chapter_files(project_root):
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        spans = _name_spans(text, seed_set)
        for idx, (name, start, end) in enumerate(spans):
            lo = max(0, start - _WINDOW)
            hi = min(len(text), end + _WINDOW)
            nearby = {n for n, s, e in spans if lo <= s <= hi}
            nearby_seeds = sorted(nearby & seed_set)
            if name in seed_set or len(nearby_seeds) != 1:
                continue
            canon = nearby_seeds[0]
            key = tuple(sorted((canon, name)))
            edge_counts[key] = edge_counts.get(key, 0) + 1
            evidence.setdefault(key, [])
            if len(evidence[key]) < 3:
                evidence[key].append({
                    "chapter": _chapter_number(path),
                    "path": os.path.relpath(path, project_root),
                    "snippet": _snip(text, start, end),
                })

    graph = {}
    edge_payloads = []
    for (a, b), count in edge_counts.items():
        if count < min_edge_count:
            continue
        graph.setdefault(a, set()).add(b)
        graph.setdefault(b, set()).add(a)
        edge_payloads.append({"a": a, "b": b, "count": count, "evidence": evidence.get((a, b), [])})

    seen = set()
    clusters = []
    for node in sorted(graph):
        if node in seen:
            continue
        stack = [node]
        comp = set()
        while stack:
            cur = stack.pop()
            if cur in comp:
                continue
            comp.add(cur)
            stack.extend(graph.get(cur, set()) - comp)
        seen |= comp
        canons = sorted(comp & seed_set)
        if not canons:
            continue
        members = sorted(comp - set(canons))
        if not members:
            continue
        ev = [
            edge for edge in edge_payloads
            if edge["a"] in comp and edge["b"] in comp
        ]
        clusters.append({
            "suggested_canonical": canons[0] if len(canons) == 1 else None,
            "canonical_candidates": canons,
            "members": members,
            "source": "cooccurrence_connected_components",
            "confidence": "medium" if sum(e["count"] for e in ev) >= 3 else "low",
            "edge_count": sum(e["count"] for e in ev),
            "edges": ev,
            "note": "正文共现候选，只供人工一簇一确认；确认前不参与 graph_sentry 硬闸。",
        })
    return clusters


def build_candidate_aliases(project_root):
    """合并 角色卡 + 动态百科 候选 → {规范名: [别名...]}（去重·稳定序）+ 来源标注。"""
    merged = {}
    sources = {}
    for label, fn in (("card", parse_card_aliases), ("wiki", parse_wiki_aliases)):
        for name, aliases in fn(project_root).items():
            merged.setdefault(name, [])
            for a in aliases:
                if a not in merged[name]:
                    merged[name].append(a)
                sources.setdefault(a, label)
    return merged, sources


def scaffold(project_root, force=False):
    """写候选 设定/角色别名.json（status="draft"）。已存在且非 force → 不覆盖（保护人工确认成果）。"""
    aliases, sources = build_candidate_aliases(project_root)
    clusters = cooccurrence_clusters(project_root)
    flat = {}
    for canon, al in aliases.items():
        for a in al:
            flat[a] = canon
    out_path = os.path.join(project_root, "设定", "角色别名.json")
    existing = _load_json(out_path)
    if existing and not force:
        return {"written": False, "reason": "已存在 设定/角色别名.json（避免覆盖人工确认；--force 重建候选）",
                "path": out_path, "existing_status": existing.get("status"),
                "candidate_characters": len(aliases), "candidate_aliases": len(flat)}
    payload = {
        "schema_version": 1,
        "status": "draft",   # ← 人核对后改 "confirmed" 才参与 graph_sentry 确定性归一
        "note": ("自动从 角色卡/动态百科 抽取的**候选**别名，可能误并同名角色；请人工核对后把 status 改为 "
                 "confirmed，graph_sentry 生命周期硬闸才会用它做实体消解。"),
        "aliases": aliases,                 # {规范名: [别名...]}（graph_sentry build_alias_map 支持）
        "character_aliases": flat,          # {别名: 规范名}（最显式·同样被支持）
        "candidate_sources": sources,       # {别名: card|wiki}
        "candidate_clusters": clusters,      # 共现连通分量候选：人确认后手动并入 aliases/character_aliases
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return {"written": True, "path": out_path, "status": "draft",
            "candidate_characters": len(aliases), "candidate_aliases": len(flat)}


def main():
    ap = argparse.ArgumentParser(description="角色别名表生产侧脚手架（抽候选→人确认入硬闸）")
    ap.add_argument("project_root")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的 设定/角色别名.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    res = scaffold(os.path.abspath(args.project_root), force=args.force)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif res.get("written"):
        print(f"[ok] 候选别名表 → {res['path']}（status=draft·{res['candidate_characters']}角色/"
              f"{res['candidate_aliases']}别名）")
        print("[next] 人工核对后把 status 改为 \"confirmed\"，graph_sentry 生命周期硬闸才会用它做实体消解。")
    else:
        print(f"[skip] {res['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
