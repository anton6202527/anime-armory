#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulate_panel.py — 合成叙事探针（未校准表面信号 + LLM 定性骨架）

诚实分工（同家族 mechanical/script 哲学）：
  - 脚本只算**可复核的表面观察**：各阅读视角关注词、章尾钩子标记、4-gram 去重、套路词命中。
  - 不把这些分量加权成“留存代理/留存先验”；它们未经校准，方向也需结合正文判断。
  - 真正的叙事问题由 LLM 在交互节点按阅读视角读文本补全（报告里留占位）。
  - 另产一份机读 `评分/reader_panel_signals.json`，作为合成叙事探针供人工复核；不得冒充读者数据或自动改分。

  python3 simulate_panel.py <作品根> [--scope opening|chapter] [--chapter N]
      [--personas rookie,logic,emote,critic] [--cohort cohort.json]
      [--viewpoint '{"id":"slow_burn","name":"慢热视角","focus":"人物关系","keywords":["犹豫"]}']

无第三方库，纯标准库。
"""
import os
import re
import json
import argparse
import sys
import hashlib
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
_SKILLS = os.path.abspath(os.path.join(_HERE, "..", ".."))
_COMMON = os.path.join(_SKILLS, "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from project_io import read_chapters  # noqa: E402
from keyword_banks import (  # noqa: E402  单一定义源
    CLICHE_KW,
    EMOTION_KW,
    HOOK_MARKERS,
    LOGIC_KW,
    PAYOFF_KW,
    classify_platform,
)
from settings import get_setting  # noqa: E402
from reader_probe import build_reader_probe_snapshot  # noqa: E402

_CJK = r"一-鿿"

PERSONAS = {
    "rookie": {"name": "小白爽文党", "focus": "节奏/升级感/反杀/不憋屈",
               "kw": PAYOFF_KW,
               "probe_questions": ["目标与阻碍是否足够快地建立？", "兑现是否有铺垫与代价，而非只靠关键词？"]},
    "logic": {"name": "逻辑考据党", "focus": "设定自洽/力量体系/无降智",
              "kw": LOGIC_KW,
              "probe_questions": ["人物选择是否有可见动机与代价？", "规则是否在需要时才临时改变？"]},
    "emote": {"name": "情感/互动党", "focus": "人物弧光/CP/情感张力/金句",
              "kw": EMOTION_KW,
              "probe_questions": ["关系变化是否落实为动作、选择或误解？", "情绪是否被解释替代了表演？"]},
    "critic": {"name": "毒舌老书虫", "focus": "同质化套路/文笔/新意",
               "kw": CLICHE_KW,
               "probe_questions": ["熟悉母题是否产生了作品自己的转折？", "哪些判断必须回到具体句段而不能靠套路词命中？"]},
}

# 各档默认视角集：品质/情感向不该默认用小白爽点视角主导问题（爽点稀薄不等于叙事失效），
# 默认换成情感党+逻辑党+毒舌，rookie 仍可显式 --personas 加回。爽文向保留全人格。
DEFAULT_PERSONAS_BY_PROFILE = {
    "商业爽文向": ["rookie", "logic", "emote", "critic"],
    "品质向": ["emote", "logic", "critic"],
}

COHORT_KIND = "novel_reader_probe_cohort"
DEFAULT_COHORT_REL_PATH = os.path.join("设定", "reader_probe_cohort.json")
_MAX_COHORT_BYTES = 256 * 1024
_MAX_PERSPECTIVES = 12
_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,39}$")
_COHORT_KEYS = {"schema_version", "kind", "name", "description", "perspectives"}
_PERSPECTIVE_KEYS = {
    "id", "name", "focus", "keywords", "probe_questions", "reading_history",
    "genre_familiarity", "tolerances", "expectations",
}


class CohortConfigError(ValueError):
    """项目级合成视角配置不安全或不符合 schema。"""


def _cjk_len(s):
    return len(re.findall(f"[{_CJK}]", s))


def _surface_char_len(s):
    """中文项目用 CJK 字数；纯非中文文本退化为 Unicode 字母数字数。"""
    cjk = _cjk_len(s)
    return cjk if cjk else sum(1 for ch in s if ch.isalnum())


def list_chapters(project):
    return [(idx, text) for idx, _path, text in read_chapters(project, numbered_only=True)]


def list_chapter_records(project):
    return read_chapters(project, numbered_only=True)


def _density(text, kw):
    signal = _literal_term_signal(text, kw)
    return signal["density_per_kchar"] or 0.0


def _literal_term_signal(text, terms):
    """返回字面命中事实；不解释命中是好是坏。"""
    cleaned = []
    seen = set()
    for term in terms or []:
        term = str(term).strip()
        if term and term not in seen:
            seen.add(term)
            cleaned.append(term)
    counts = {term: text.count(term) for term in cleaned}
    matched = {term: count for term, count in counts.items() if count}
    hits = sum(counts.values())
    chars = _surface_char_len(text)
    return {
        "available": bool(cleaned),
        "literal_hits": hits,
        "density_per_kchar": round(hits / chars * 1000, 2) if chars and cleaned else None,
        "matched_terms": matched,
        "term_count": len(cleaned),
        "sampled_chars": chars,
        "interpretation": "uncalibrated_literal_surface_observation",
    }


def _hook_tail_signal(chapters):
    """汇总逐章末 160 字的标记命中，不再压成 0-1“钩子强度”。"""
    tails = [text[-160:] for _idx, text in chapters]
    literal = _literal_term_signal("\n".join(tails), HOOK_MARKERS)
    hit_chapters = 0
    for tail in tails:
        if any(tail.count(marker) for marker in HOOK_MARKERS):
            hit_chapters += 1
    return {
        "tail_window_chars": 160,
        "chapter_tails_observed": len(tails),
        "chapter_tails_with_marker_hits": hit_chapters,
        "literal_marker_hits": literal["literal_hits"],
        "density_per_kchar": literal["density_per_kchar"],
        "matched_markers": literal["matched_terms"],
        "sampled_tail_chars": literal["sampled_chars"],
        "interpretation": "marker_presence_only_not_hook_quality",
    }


def _lexical_diversity(text):
    return _lexical_surface_signal(text)["unique_cjk_4gram_ratio"]


def _lexical_surface_signal(text):
    cjk = "".join(re.findall(f"[{_CJK}]", text))
    grams = [cjk[idx:idx + 4] for idx in range(max(0, len(cjk) - 3))]
    unique = len(set(grams))
    return {
        "cjk_4gram_count": len(grams),
        "unique_cjk_4gram_count": unique,
        "unique_cjk_4gram_ratio": round(unique / len(grams), 3) if grams else 0.0,
        "interpretation": "surface_repetition_observation_not_information_density",
    }


def _bounded_text(value, field, *, required=False, limit=240):
    if value is None:
        text = ""
    elif not isinstance(value, str):
        raise CohortConfigError(f"阅读视角 {field} 必须是字符串")
    else:
        text = value.strip()
    if required and not text:
        raise CohortConfigError(f"阅读视角缺少 {field}")
    if len(text) > limit:
        raise CohortConfigError(f"阅读视角 {field} 超过 {limit} 字符")
    return text


def _bounded_string_list(value, field, *, max_items, item_limit):
    if value is None:
        return []
    if not isinstance(value, list):
        raise CohortConfigError(f"阅读视角 {field} 必须是字符串数组")
    if len(value) > max_items:
        raise CohortConfigError(f"阅读视角 {field} 最多 {max_items} 项")
    out = []
    for item in value:
        if not isinstance(item, str):
            raise CohortConfigError(f"阅读视角 {field} 的每一项都必须是字符串")
        text = _bounded_text(item, field, required=True, limit=item_limit)
        if text not in out:
            out.append(text)
    return out


def validate_perspective(raw, *, source="custom"):
    """只接受阅读偏好/经验/容忍项，不接受人口统计画像字段。"""
    if not isinstance(raw, dict):
        raise CohortConfigError("每个阅读视角必须是 JSON object")
    unexpected = sorted(set(raw) - _PERSPECTIVE_KEYS)
    if unexpected:
        raise CohortConfigError(
            "阅读视角含不允许字段：" + "、".join(unexpected)
            + "；只描述阅读偏好、题材经验、容忍项、期待机制与复核问题，不模拟人口统计身份"
        )
    pid = _bounded_text(raw.get("id"), "id", required=True, limit=40)
    if not _ID_RE.fullmatch(pid):
        raise CohortConfigError("阅读视角 id 须以英文字母开头，仅含字母、数字、_、-，最长 40")
    keywords = _bounded_string_list(raw.get("keywords"), "keywords", max_items=64, item_limit=24)
    questions = _bounded_string_list(
        raw.get("probe_questions"), "probe_questions", max_items=8, item_limit=240
    )
    return {
        "id": pid,
        "name": _bounded_text(raw.get("name"), "name", required=True, limit=80),
        "focus": _bounded_text(raw.get("focus"), "focus", required=True, limit=240),
        "keywords": keywords,
        "probe_questions": questions,
        "lens_context": {
            key: _bounded_text(raw.get(key), key, limit=240)
            for key in ("reading_history", "genre_familiarity", "tolerances", "expectations")
            if _bounded_text(raw.get(key), key, limit=240)
        },
        "source": source,
    }


def _builtin_perspective(pid):
    meta = PERSONAS[pid]
    return validate_perspective({
        "id": pid,
        "name": meta["name"],
        "focus": meta["focus"],
        "keywords": list(meta["kw"]),
        "probe_questions": list(meta.get("probe_questions") or []),
    }, source="built_in_preset")


def load_cohort(path):
    if not os.path.isfile(path):
        raise CohortConfigError(f"找不到 cohort 文件：{path}")
    if os.path.getsize(path) > _MAX_COHORT_BYTES:
        raise CohortConfigError(f"cohort 文件超过 {_MAX_COHORT_BYTES} bytes")
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        raise CohortConfigError(f"cohort JSON 无法读取：{exc}") from exc
    if not isinstance(payload, dict):
        raise CohortConfigError("cohort 顶层必须是 JSON object")
    unexpected = sorted(set(payload) - _COHORT_KEYS)
    if unexpected:
        raise CohortConfigError(
            "cohort 含不允许字段：" + "、".join(unexpected)
            + "；合成探针不接收人口统计画像或代表性声明"
        )
    if payload.get("kind") != COHORT_KIND or payload.get("schema_version") != 1:
        raise CohortConfigError(f"cohort 必须声明 kind={COHORT_KIND}、schema_version=1")
    rows = payload.get("perspectives")
    if not isinstance(rows, list) or not rows:
        raise CohortConfigError("cohort.perspectives 必须是非空数组")
    if len(rows) > _MAX_PERSPECTIVES:
        raise CohortConfigError(f"cohort 最多 {_MAX_PERSPECTIVES} 个阅读视角")
    perspectives = {}
    for row in rows:
        item = validate_perspective(row, source="custom_cohort")
        if item["id"] in perspectives:
            raise CohortConfigError(f"cohort 阅读视角 id 重复：{item['id']}")
        perspectives[item["id"]] = item
    return {
        "name": _bounded_text(payload.get("name"), "cohort.name", limit=120) or "自定义阅读视角组",
        "description": _bounded_text(payload.get("description"), "cohort.description", limit=500),
        "perspectives": perspectives,
    }


def parse_inline_viewpoint(raw):
    if len(raw) > 8192:
        raise CohortConfigError("--viewpoint JSON 超过 8192 字符")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CohortConfigError(f"--viewpoint 不是合法 JSON：{exc}") from exc
    return validate_perspective(payload, source="cli_inline")


def _safe_source(path, project, *, automatic=False):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    real_project = os.path.realpath(project)
    real_path = os.path.realpath(path)
    try:
        within_project = os.path.commonpath([real_project, real_path]) == real_project
    except ValueError:
        within_project = False
    return {
        "kind": "project_file" if within_project else "cli_file",
        "path": os.path.relpath(real_path, real_project) if within_project else None,
        "label": os.path.basename(real_path),
        "sha256": digest.hexdigest(),
        "automatic": automatic,
    }


def resolve_perspectives(project, profile, *, persona_ids=None, cohort_path=None, inline_viewpoints=None):
    """解析预设/项目 cohort/CLI 视角；显式输入不会偷偷混入平台默认视角。"""
    inline_viewpoints = inline_viewpoints or []
    explicit = persona_ids is not None or cohort_path is not None or bool(inline_viewpoints)
    perspectives = {}
    sources = []

    if persona_ids is not None:
        if not persona_ids:
            raise CohortConfigError("--personas 不能为空；不需要内置视角时请省略该参数")
        for pid in persona_ids:
            if pid not in PERSONAS:
                raise CohortConfigError(f"未知预设人格：{pid}；可选 {','.join(PERSONAS)}")
            perspectives[pid] = _builtin_perspective(pid)
        sources.append({"kind": "built_in_selection", "ids": list(persona_ids)})

    auto_path = os.path.join(project, DEFAULT_COHORT_REL_PATH)
    selected_cohort_path = cohort_path or (auto_path if not explicit and os.path.isfile(auto_path) else None)
    cohort_name = None
    cohort_description = ""
    if selected_cohort_path:
        cohort = load_cohort(selected_cohort_path)
        cohort_name = cohort["name"]
        cohort_description = cohort["description"]
        for pid, item in cohort["perspectives"].items():
            if pid in perspectives:
                raise CohortConfigError(f"阅读视角 id 与现有视角重复：{pid}")
            perspectives[pid] = item
        sources.append(_safe_source(
            selected_cohort_path, project,
            automatic=cohort_path is None and os.path.realpath(selected_cohort_path) == os.path.realpath(auto_path),
        ))

    for raw in inline_viewpoints:
        item = parse_inline_viewpoint(raw)
        if item["id"] in perspectives:
            raise CohortConfigError(f"阅读视角 id 与现有视角重复：{item['id']}")
        perspectives[item["id"]] = item
    if inline_viewpoints:
        sources.append({"kind": "cli_inline", "count": len(inline_viewpoints)})

    if len(perspectives) > _MAX_PERSPECTIVES:
        raise CohortConfigError(f"合并后最多 {_MAX_PERSPECTIVES} 个阅读视角")

    if not perspectives:
        ids = list(DEFAULT_PERSONAS_BY_PROFILE.get(profile, list(PERSONAS)))
        perspectives = {pid: _builtin_perspective(pid) for pid in ids}
        sources.append({"kind": "built_in_profile_default", "profile": profile, "ids": ids})

    return perspectives, {
        "name": cohort_name or "合成阅读视角组",
        "description": cohort_description,
        "sources": sources,
        "perspective_ids": list(perspectives),
        "synthetic_probe_only": True,
        "population_representativeness": "none",
    }


def analyze(project, scope, chapter, personas, profile="商业爽文向", *, perspective_defs=None,
            cohort_meta=None):
    records = list_chapter_records(project)
    if not records:
        if scope == "chapter":
            raise FileNotFoundError(f"找不到请求的第 {chapter} 章；chapter scope 不允许回退到其它章节")
        return None
    if scope == "opening":
        target_records = records[:3]
    else:
        target_records = [record for record in records if record[0] == chapter]
        if not target_records:
            raise FileNotFoundError(f"找不到请求的第 {chapter} 章；chapter scope 不允许回退到其它章节")
    target = [(idx, text) for idx, _path, text in target_records]
    text = "\n".join(t for _, t in target)
    source_snapshot = build_reader_probe_snapshot(
        project, scope, chapter if scope == "chapter" else None
    )

    perspective_defs = perspective_defs or {pid: _builtin_perspective(pid) for pid in personas}
    perspective_signals = {}
    for pid in personas:
        meta = perspective_defs[pid]
        perspective_signals[pid] = {
            "name": meta["name"],
            "focus": meta["focus"],
            "lens_context": meta.get("lens_context") or {},
            "probe_questions": meta.get("probe_questions") or [],
            "keyword_surface": _literal_term_signal(text, meta.get("keywords") or []),
            "source": meta.get("source") or "unknown",
        }

    return {
        "schema_version": 3,
        "kind": "novel_synthetic_reader_probe",
        "evidence_type": "synthetic_probe",
        "validation_status": "unvalidated",
        "decision_authority": "context_only",
        "numeric_score_eligible": False,
        "analysis_mode": "surface_signals_only",
        "signal_only": True,
        "qualitative_completed": False,
        "perspectives_completed": [],
        "agent_filled_at": None,
        "default_preset_profile": profile,
        "scope": scope,
        "scope_chapter": chapter if scope == "chapter" else None,
        "scope_contract": {
            "mode": scope,
            "opening_chapter_limit": 3 if scope == "opening" else None,
            "requested_chapter": chapter if scope == "chapter" else None,
        },
        "chapters_read": [idx for idx, _ in target],
        "sampled_chars": _surface_char_len(text),
        "source_snapshot": source_snapshot,
        "cohort": cohort_meta or {
            "name": "合成阅读视角组",
            "sources": [{"kind": "built_in_selection", "ids": list(personas)}],
            "perspective_ids": list(personas),
            "synthetic_probe_only": True,
            "population_representativeness": "none",
        },
        "perspectives": perspective_signals,
        "surface_signals": {
            "hook_tail_markers": _hook_tail_signal(target),
            "lexical_4gram": _lexical_surface_signal(text),
            "cliche_terms": _literal_term_signal(text, CLICHE_KW),
        },
        "aggregate_score": None,
        "aggregate_score_policy": "forbidden_unless_calibrated_against_real_reader_outcomes",
        "prohibited_inferences": [
            "retention_probability", "population_preference", "demographic_behavior",
        ],
        "note": "合成探针仅提出可复核问题；表面信号未经校准、没有统一方向，不代表真实读者或统计证据，不参与自动评分",
    }


def write_report(project, sig, personas):
    date = datetime.now().strftime("%Y-%m-%d")
    rdir = os.path.join(project, "评分")
    os.makedirs(rdir, exist_ok=True)

    # 机读合成探针（供 score/revision 展示上下文，不参与自动改分）
    sig_path = os.path.join(rdir, "reader_panel_signals.json")
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump({"date": date, **sig}, f, ensure_ascii=False, indent=2)

    # 人读报告（LLM 填定性）
    md_path = os.path.join(rdir, f"读者试读反馈_{date}.md")
    surface = sig.get("surface_signals") or {}
    hook = surface.get("hook_tail_markers") or {}
    lexical = surface.get("lexical_4gram") or {}
    cliche = surface.get("cliche_terms") or {}
    lines = [
        f"# 合成叙事探针报告 — {date}",
        "",
        f"- 范围：{sig['scope']}（第 {sig['chapters_read']} 章）",
        f"- 阅读视角组：{(sig.get('cohort') or {}).get('name') or '合成阅读视角组'}",
        f"- 完成状态：{sig.get('analysis_mode', 'surface_signals_only')}；定性补全：{sig.get('qualitative_completed', False)}",
        f"- 章尾标记表面命中：{hook.get('literal_marker_hits', 0)} 次 / {hook.get('chapter_tails_observed', 0)} 个章尾"
        f"（其中 {hook.get('chapter_tails_with_marker_hits', 0)} 个有命中；{hook.get('density_per_kchar')} / 千字）",
        f"- 4-gram 表面去重：{lexical.get('unique_cjk_4gram_count', 0)} / {lexical.get('cjk_4gram_count', 0)}"
        f"（比率 {lexical.get('unique_cjk_4gram_ratio', 0)}）",
        f"- 套路词表面命中：{cliche.get('literal_hits', 0)} 次（{cliche.get('density_per_kchar')} / 千字）",
        "",
        "> 以上是未校准的字面/结构观察，没有相加后的总分，也没有统一的“越高越好”方向。",
        "> 每个阅读视角只负责提出正文复核问题，不代表某个人群、人口统计身份、真实读者反馈或留存预测。",
        "",
    ]
    for pid in personas:
        ps = sig["perspectives"][pid]
        keyword = ps.get("keyword_surface") or {}
        lines += [
            f"## {ps['name']}（{ps['focus']}）",
            f"- 关注词表面命中：{keyword.get('literal_hits', 0)} 次（{keyword.get('density_per_kchar')} / 千字；"
            f"无关键词时此项为 unavailable，不代表缺少该叙事功能）",
        ]
        for question in ps.get("probe_questions") or []:
            lines.append(f"- 预设复核问题：{question}")
        lines += [
            "- 【AI 代理填写】正文中支持或反驳这个视角担忧的具体句段：",
            "- 【AI 代理填写】可能让阅读中断的文本证据候选（不是人群行为预测）：",
            "- 【AI 代理填写】值得保留的有效机制及理由：",
            "",
        ]
    lines += [
        "## 综合（AI 代理填写）",
        "- 多视角共同提出、且能被正文证据支持的问题：",
        "- 视角间分歧（保留分歧，不投票伪装共识）：",
        "- 待真人 beta reader / 平台数据验证的假设：",
        "",
        "--- 报告骨架完，待 AI 代理补定性 ---",
    ]
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md_path, sig_path


def main():
    p = argparse.ArgumentParser(description="合成叙事探针（未校准表面观察 + LLM 定性复核问题）")
    p.add_argument("project_path")
    p.add_argument("--scope", default="opening", choices=["opening", "chapter"])
    p.add_argument("--chapter", type=int, default=1)
    p.add_argument("--personas", default=None,
                   help="逗号分隔内置阅读视角；显式传入时不自动混入项目 cohort/平台默认视角")
    p.add_argument("--cohort", help="自定义 cohort JSON；未传且项目设定/reader_probe_cohort.json 存在时自动读取")
    p.add_argument("--viewpoint", action="append", default=[],
                   help="追加一个 JSON 阅读视角，可重复；只接受偏好/经验/容忍项/期待/问题，不接受人口统计画像")
    args = p.parse_args()

    # 读 `目标平台` 选择点（_设置.md → 全局默认 → 缺省），归一成评判档。
    profile = classify_platform(get_setting(args.project_path, "目标平台"))
    persona_ids = None
    if args.personas is not None:
        persona_ids = [x.strip() for x in args.personas.split(",") if x.strip()]
    try:
        perspective_defs, cohort_meta = resolve_perspectives(
            args.project_path,
            profile,
            persona_ids=persona_ids,
            cohort_path=args.cohort,
            inline_viewpoints=args.viewpoint,
        )
    except CohortConfigError as exc:
        p.error(str(exc))
    personas = list(perspective_defs)
    try:
        sig = analyze(
            args.project_path, args.scope, args.chapter, personas, profile,
            perspective_defs=perspective_defs, cohort_meta=cohort_meta,
        )
    except FileNotFoundError as exc:
        p.error(str(exc))
    if sig is None:
        print(f"Error: {args.project_path}/章节 下没有可读章节")
        return
    md_path, sig_path = write_report(args.project_path, sig, personas)
    surface = sig["surface_signals"]
    hook = surface["hook_tail_markers"]
    cliche = surface["cliche_terms"]
    print(f"预设档：{profile}（仅在没有自定义输入时决定内置阅读视角）")
    print(f"合成叙事探针视角：{', '.join(perspective_defs[p]['name'] for p in personas)}")
    print(f"  章尾标记命中 {hook['literal_marker_hits']} 次 · 套路词命中 {cliche['literal_hits']} 次/{sig['sampled_chars']} 字")
    print("  不生成聚合留存分；所有分量均为未校准表面观察")
    print(f"  报告骨架 → {md_path}")
    print(f"  机读探针 → {sig_path}（synthetic/context-only，不参与自动调分）")
    print("  ⚠️ 定性假设待 AI 代理补全；补全后仍需正文/真人反馈验证")


if __name__ == "__main__":
    main()
