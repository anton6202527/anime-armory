#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Machine-readable contract for the novel-* family.

Keep workflow docs expressive, but keep shared machine contracts here:
scale bands, output formats, kind/title rules, and common derived-stage keys.
"""
from copy import deepcopy
from datetime import date


CONTRACT_VERSION = 1

ALLOWED_OUTPUT_FORMATS = ("txt", "docx", "outline")

NOVEL_DRAFT_MODES = ("极速初稿", "稳妥初稿", "商业连载", "漫剧源书")

DRAFT_WORKFLOWS = ("默认单步", "三步迭代", "边写边自检")

CHAPTER_GRANULARITY = ("逐章", "小批", "全书草稿")

AI_TEXT_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI文本")

NOVEL_PURPOSES = (
    "传统小说",
    "漫剧源书",
    "微短剧源书",
    "短读/短篇",
    "出海译制底稿",
    "自定义",
)

NOVEL_PURPOSE_ALIASES = {
    "红果": "漫剧源书",
    "红果短剧": "漫剧源书",
    "红果漫剧": "漫剧源书",
    "红果漫剧源书": "漫剧源书",
    "抖音": "漫剧源书",
    "抖音短剧": "漫剧源书",
    "抖音漫剧": "漫剧源书",
    "抖音漫剧源书": "漫剧源书",
    "短剧": "微短剧源书",
    "微短剧": "微短剧源书",
    "漫剧": "漫剧源书",
    "漫剧档": "漫剧源书",
    "传统": "传统小说",
    "传统网文": "传统小说",
    "传统连载": "传统小说",
    "网文": "传统小说",
    "长篇": "传统小说",
    "短篇": "短读/短篇",
    "短读": "短读/短篇",
    "出海": "出海译制底稿",
    "翻译": "出海译制底稿",
}

COMMERCIAL_NOVEL_PURPOSES = ("漫剧源书", "微短剧源书")

PURPOSE_SCALE_DEFAULTS = {
    "漫剧源书": "漫剧",
    "微短剧源书": "微短剧",
    "短读/短篇": "short",
}

RIGHTS_STATUS_CANONICAL = {
    "original": "original",
    "原创": "original",
    "self-owned": "user-owned",
    "user-owned": "user-owned",
    "owned": "user-owned",
    "自有": "user-owned",
    "授权": "user-declared",
    "licensed": "user-declared",
    "user-licensed": "user-declared",
    "user-declared": "user-declared",
    "public-domain": "public-domain",
    "公版": "public-domain",
    "unknown": "unknown",
    "未判定": "unknown",
    "未声明": "unknown",
    "未确认": "unknown",
}

PUBLIC_DOMAIN_LICENSE_URLS = {
    "gutenberg": "https://www.gutenberg.org/policy/license.html",
    "wikisource": "https://wikisource.org/wiki/Wikisource:Copyright_policy",
}

REGION_ALIASES = {
    "us": "US",
    "usa": "US",
    "united states": "US",
    "美国": "US",
    "cn": "CN",
    "china": "CN",
    "中国": "CN",
    "中国大陆": "CN",
    "大陆": "CN",
    "全球": "GLOBAL",
    "global": "GLOBAL",
    "worldwide": "GLOBAL",
    "跨平台": "UNSPECIFIED",
    "未定": "UNSPECIFIED",
    "": "",
}

KIND_SUFFIX = {
    "rewrite": "改写",
    "expand": "扩写",
    "condense": "精简",
    "continue": "续写",
}

SCALE_PROFILES = {
    "short": {
        "label": "短篇集",
        "target_chapters": 3,
        "words_per_chapter": [6000, 10000],
        "min_max": [5000, 15000],
        "demo": 1,
    },
    "medium": {
        "label": "网文中篇",
        "target_chapters": 20,
        "words_per_chapter": [3000, 5000],
        "min_max": [2500, 6000],
        "demo": 2,
    },
    "long": {
        "label": "网文长篇",
        "target_chapters": 40,
        "words_per_chapter": [5000, 8000],
        "min_max": [4000, 10000],
        "demo": 3,
    },
    "微短剧": {
        "label": "微短剧",
        "target_chapters": 50,
        "words_per_chapter": [1500, 2500],
        "min_max": [1200, 3000],
        "demo": 3,
    },
    "漫剧": {
        "label": "抖音漫剧/红果短剧",
        "target_chapters": 90,
        "words_per_chapter": [1000, 1500],
        "min_max": [800, 1800],
        "demo": 3,
    },
}

WORDCOUNT_BANDS_BY_TARGET = {
    (1000, 1500): [800, 1800],
    (1500, 2500): [1200, 3000],
    (3000, 5000): [2500, 6000],
    (5000, 8000): [4000, 10000],
    (6000, 10000): [5000, 15000],
}

SCALE_ALIASES = {
    "抖音漫剧": "漫剧",
    "红果短剧": "漫剧",
    "漫剧档": "漫剧",
    "短剧": "微短剧",
    "微短剧档": "微短剧",
}

SCALE_CHOICES = tuple(SCALE_PROFILES) + tuple(SCALE_ALIASES)

DERIVED_STAGE_TABLE = [
    {
        "key": "setup",
        "label": "项目骨架",
        "owner": "init_project.py",
        "gate": "deterministic",
        "on_fail": "重跑 init 或换 --out",
    },
    {
        "key": "source_model",
        "label": "吸收原作 / 建变换骨架",
        "owner": "当前 skill 主流程",
        "gate": "user-review",
        "on_fail": "回本阶段补设定/骨架",
    },
    {
        "key": "direction_spec",
        "label": "变换 spec / 方向确认",
        "owner": "当前 skill 主流程",
        "gate": "user-review",
        "on_fail": "回 source_model 或改变换目标",
    },
    {
        "key": "title",
        "label": "书名",
        "owner": "novel-title",
        "gate": "user-choice",
        "on_fail": "重跑 novel-title",
    },
    {
        "key": "outline",
        "label": "章纲",
        "owner": "novel-craft/references/outline.md",
        "gate": "user-review",
        "on_fail": "回 direction_spec 调整方向",
    },
    {
        "key": "demo",
        "label": "Demo gate",
        "owner": "当前 skill 主流程",
        "gate": "user-review + optional novel-score",
        "on_fail": "回设定/章纲/口吻卡，不批量写",
    },
    {
        "key": "draft",
        "label": "批量写章节",
        "owner": "novel-craft/scripts/draft_packets.py + 当前 skill/agent",
        "gate": "demo_gate + packet + chapter review",
        "on_fail": "就地改章节、重出任务包，或回 demo",
    },
    {
        "key": "review",
        "label": "一致性回扫",
        "owner": "novel-review",
        "gate": "mechanical + LLM review",
        "on_fail": "按报告回源头阶段",
    },
    {
        "key": "export",
        "label": "导出",
        "owner": "novel-craft/scripts/export.py",
        "gate": "deterministic",
        "on_fail": "修 _meta/章节文件后重跑 export",
    },
]

CREATE_STAGE_TABLE = [
    {
        "key": "setup",
        "label": "项目骨架",
        "owner": "novel-create/scripts/init_project.py",
        "gate": "deterministic",
        "on_fail": "重跑 init 或换 --out",
    },
    {
        "key": "blueprint",
        "label": "创作蓝图",
        "owner": "novel-create",
        "gate": "user-review",
        "on_fail": "回立项访谈补 premise/主角/爽点/冲突",
    },
    {
        "key": "setting_bible",
        "label": "设定圣经 / 角色卡 / 世界观",
        "owner": "novel-create + novel-craft/references/setting-bible.md",
        "gate": "user-review",
        "on_fail": "回创作蓝图或重建设定约束",
    },
    {
        "key": "title",
        "label": "书名",
        "owner": "novel-title",
        "gate": "user-choice",
        "on_fail": "重跑 novel-title",
    },
    {
        "key": "outline",
        "label": "章纲",
        "owner": "novel-craft/references/outline.md",
        "gate": "user-review",
        "on_fail": "回创作蓝图/设定圣经调整主线",
    },
    {
        "key": "demo",
        "label": "Demo gate",
        "owner": "novel-create",
        "gate": "user-review + optional novel-score",
        "on_fail": "回蓝图/设定/章纲/风格卡，不批量写",
    },
    {
        "key": "draft",
        "label": "批量写章节",
        "owner": "novel-craft/scripts/draft_packets.py + novel-create/agent",
        "gate": "demo_gate + packet + chapter review",
        "on_fail": "就地修章、重出任务包，或回 demo",
    },
    {
        "key": "review",
        "label": "一致性回扫",
        "owner": "novel-review",
        "gate": "mechanical + LLM review",
        "on_fail": "按报告回源头阶段",
    },
    {
        "key": "export",
        "label": "导出",
        "owner": "novel-craft/scripts/export.py",
        "gate": "deterministic",
        "on_fail": "修 _meta/章节文件后重跑 export",
    },
]

KIND_SPEC_LABEL = {
    "spinoff": "锚点/角色/世界观",
    "rewrite": "改动spec / 新设定",
    "expand": "事件骨架 / 章节映射",
    "condense": "主线骨架 / 合章计划",
    "continue": "末章状态 / 续写方向",
}

# 这些派生类沿用原作书名（续/扩/缩不另起书名），不该带 title 阶段——否则
# _进度.md 永远卡在「书名」这一未完成项上。rewrite/spinoff 仍走 novel-title。
NO_TITLE_KINDS = {"continue", "expand", "condense"}


def normalize_scale(scale):
    key = str(scale or "").strip()
    return SCALE_ALIASES.get(key, key)


def scale_profile(scale):
    key = normalize_scale(scale)
    if key not in SCALE_PROFILES:
        key = "medium"  # fallback
    return deepcopy(SCALE_PROFILES[key])


def normalize_novel_purpose(value):
    text = str(value or "").strip()
    if not text:
        return ""
    return NOVEL_PURPOSE_ALIASES.get(text, text)


def infer_novel_purpose(platform=None, scale=None, target=None):
    """Infer a reasonable project purpose from existing platform/scale fields."""
    text = " ".join(str(x or "") for x in (target, platform, scale))
    if "微短剧" in text:
        return "微短剧源书"
    if any(key in text for key in ("红果", "抖音", "漫剧")):
        return "漫剧源书"
    if "短剧" in text:
        return "微短剧源书"
    if any(key in text for key in ("short", "短篇", "短读")):
        return "短读/短篇"
    return "传统小说"


def scale_for_novel_purpose(purpose, fallback=None):
    purpose = normalize_novel_purpose(purpose)
    return PURPOSE_SCALE_DEFAULTS.get(purpose, fallback)


def words_per_chapter_for_context(purpose=None, platform=None, scale=None):
    purpose_scale = scale_for_novel_purpose(purpose)
    if purpose_scale:
        return scale_profile(purpose_scale)["words_per_chapter"]
    text = str(platform or "")
    if any(key in text for key in ("漫剧", "红果", "抖音")):
        return scale_profile("漫剧")["words_per_chapter"]
    if "短剧" in text:
        return scale_profile("微短剧")["words_per_chapter"]
    if scale:
        return scale_profile(scale)["words_per_chapter"]
    return scale_profile("medium")["words_per_chapter"]


def resolve_novel_draft_mode(explicit_mode=None, purpose=None, platform=None, scale=None, target=None, fallback="稳妥初稿"):
    if explicit_mode:
        return explicit_mode
    purpose = normalize_novel_purpose(purpose) or infer_novel_purpose(platform=platform, scale=scale, target=target)
    if purpose in COMMERCIAL_NOVEL_PURPOSES:
        return "漫剧源书"
    return fallback


def resolve_novel_draft_workflow(explicit_workflow=None, *, draft_mode=None, purpose=None, scale=None, target_chapters=None, fallback="默认单步"):
    if explicit_workflow:
        return explicit_workflow
    purpose = normalize_novel_purpose(purpose)
    try:
        chapters = int(target_chapters or 0)
    except (TypeError, ValueError):
        chapters = 0
    if (
        draft_mode in {"商业连载", "漫剧源书"}
        or purpose in COMMERCIAL_NOVEL_PURPOSES
        or normalize_scale(scale) in {"long", "长篇"}
        or chapters >= 30
    ):
        return "三步迭代"
    return fallback


def wordcount_band_for_words_per_chapter(words_per_chapter):
    """Return review min/max band for a target words-per-chapter pair.

    Exact known bands come from SCALE_PROFILES. For custom target ranges, keep
    the band broad enough to avoid forcing a dramatic beat split merely to hit
    a number: low target gets 80%, high target gets 120%.
    """
    try:
        lo, hi = [int(x) for x in words_per_chapter[:2]]
    except (TypeError, ValueError):
        return [800, 1800]
    if lo > hi:
        lo, hi = hi, lo
    known = WORDCOUNT_BANDS_BY_TARGET.get((lo, hi))
    if known:
        return list(known)
    return [max(1, int(round(lo * 0.8))), max(1, int(round(hi * 1.2)))]


def normalize_rights_status(status):
    key = str(status or "").strip()
    return RIGHTS_STATUS_CANONICAL.get(key, key or "unknown")


def normalize_region(region):
    key = str(region or "").strip()
    return REGION_ALIASES.get(key.lower(), REGION_ALIASES.get(key, key))


def parse_regions(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw = list(value)
    else:
        raw = str(value).replace("，", ",").replace("、", ",").split(",")
    out = []
    for item in raw:
        region = normalize_region(item)
        if region and region not in out:
            out.append(region)
    return out


def rights_metadata(
    rights_status,
    *,
    source_type="",
    rights_declared=False,
    source_url="",
    rights_jurisdiction=None,
    rights_basis=None,
    source_license_url=None,
    distribution_regions=None,
):
    """Return normalized rights fields for _meta.json/source_manifest.json.

    Public-domain is jurisdiction-sensitive. We record the source-side basis and
    distribution regions separately so QA/export gates can reason about gaps.
    """
    status = normalize_rights_status(rights_status)
    source_type = str(source_type or "").strip()
    regions = parse_regions(distribution_regions)
    covered_regions = []
    declared = bool(rights_declared)
    jurisdiction = str(rights_jurisdiction or "").strip()
    basis = str(rights_basis or "").strip()
    license_url = str(source_license_url or "").strip()

    if status == "original":
        jurisdiction = jurisdiction or "GLOBAL"
        basis = basis or "original_creation"
        regions = regions or ["GLOBAL"]
        covered_regions = ["GLOBAL"]
        declared = True
    elif status == "user-owned":
        jurisdiction = jurisdiction or "user-declared"
        basis = basis or "user_attested_ownership"
        regions = regions or ["GLOBAL"]
        covered_regions = ["GLOBAL"]
        declared = True
    elif status == "user-declared":
        jurisdiction = jurisdiction or "user-declared"
        basis = basis or "user_attested_authorization"
        regions = regions or ["GLOBAL"]
        covered_regions = ["GLOBAL"]
        declared = True
    elif status == "public-domain":
        if source_type == "gutenberg":
            jurisdiction = jurisdiction or "US"
            basis = basis or "Project Gutenberg public-domain claim; verify outside US"
            license_url = license_url or PUBLIC_DOMAIN_LICENSE_URLS["gutenberg"]
            covered_regions = ["US"]
        elif source_type == "wikisource":
            jurisdiction = jurisdiction or "source-site"
            basis = basis or "Wikisource page-level public-domain/free-license claim; verify target region"
            license_url = license_url or PUBLIC_DOMAIN_LICENSE_URLS["wikisource"]
        else:
            jurisdiction = jurisdiction or "declared-by-source-header"
            basis = basis or "source provenance header says public-domain; target region still needs review"
    else:
        status = "unknown"
        jurisdiction = jurisdiction or "unknown"
        basis = basis or "rights_not_established"

    requires_user_rights = status not in {"original", "user-owned", "user-declared", "public-domain"}
    requires_region_review = status == "public-domain" and "GLOBAL" not in covered_regions
    return {
        "rights_status": status,
        "rights_jurisdiction": jurisdiction,
        "rights_basis": basis,
        "source_license_url": license_url or source_url or "",
        "rights_covered_regions": covered_regions,
        "distribution_regions": regions,
        "requires_user_rights": requires_user_rights,
        "requires_region_rights_review": requires_region_review,
        "rights_declared": declared,
    }


def demo_chapters_for(target_chapters):
    if target_chapters <= 3:
        return 0
    if target_chapters <= 20:
        return 2
    return 3


def parse_outputs(value):
    outputs = [s.strip() for s in value.split(",") if s.strip()]
    unknown = sorted(set(outputs) - set(ALLOWED_OUTPUT_FORMATS))
    if unknown:
        raise ValueError(f"unknown output formats: {','.join(unknown)}")
    return outputs


def derive_title(meta):
    if meta.get("title"):
        return meta["title"]
    kind = meta.get("kind", "spinoff")
    src = meta.get("source_title") or meta.get("source")
    if kind == "spinoff" and meta.get("spinoff_character") and src:
        return f"{src}-{meta['spinoff_character']}外传"
    suffix = KIND_SUFFIX.get(kind)
    if src and suffix:
        return f"{src}-{suffix}"
    return src or "未命名"


def base_meta(kind, *, outputs, rights_status, title=None):
    rights = rights_metadata(rights_status)
    return {
        "schema_version": CONTRACT_VERSION,
        "kind": kind,
        "title": title,
        **rights,
        "outputs": list(outputs),
        "created_at": date.today().isoformat(),
    }


def stage_label(key):
    for table in (CREATE_STAGE_TABLE, DERIVED_STAGE_TABLE):
        for stage in table:
            if stage["key"] == key:
                return stage["label"]
    return key


def stage_table_for_kind(kind):
    """Return the stable stage table for a project kind."""
    return CREATE_STAGE_TABLE if kind == "create" else DERIVED_STAGE_TABLE


def stage_info(kind, key):
    """Return machine-readable owner/gate/recovery info for a stage key."""
    for stage in stage_table_for_kind(kind):
        if stage["key"] == key:
            return deepcopy(stage)
    return None


def progress_header(kind):
    return f"<!-- novel-progress-schema: {CONTRACT_VERSION}; kind: {kind} -->"


def derived_stage_markdown(kind):
    """Stable machine-readable stage checklist for derived novel projects."""
    lines = [
        progress_header(kind),
        "",
        "## 同构阶段（机器读）",
        f"<!-- novel-derived-stage-table: {CONTRACT_VERSION}; kind: {kind} -->",
    ]
    for stage in DERIVED_STAGE_TABLE:
        if stage["key"] == "title" and kind in NO_TITLE_KINDS:
            continue  # 续/扩/缩沿用原作书名，不发 title 阶段
        mark = "x" if stage["key"] == "setup" else " "
        label = stage["label"]
        if stage["key"] == "source_model" and kind in KIND_SPEC_LABEL:
            label = KIND_SPEC_LABEL[kind]
        lines.append(f"- [{mark}] {label} <!-- stage:{stage['key']} -->")
    return "\n".join(lines)


def create_stage_markdown():
    """Stable machine-readable stage checklist for original novel projects."""
    lines = [
        progress_header("create"),
        "",
        "## 原创阶段（机器读）",
        f"<!-- novel-create-stage-table: {CONTRACT_VERSION}; kind: create -->",
    ]
    for stage in CREATE_STAGE_TABLE:
        mark = "x" if stage["key"] == "setup" else " "
        lines.append(f"- [{mark}] {stage['label']} <!-- stage:{stage['key']} -->")
    return "\n".join(lines)
