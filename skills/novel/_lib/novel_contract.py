#!/usr/bin/env python3
"""Machine-readable contract for the novel pipeline."""

from __future__ import annotations

import os

# ── Symbols ──────────────────────────────────────────────────────────────
PROGRESS_DONE = "✅"
PROGRESS_TODO = "⬜"
PROGRESS_ROUGH_PREFIX = "⏳"

# ── Stages ──────────────────────────────────────────────────────────────
# Defining the standard stages for the novel pipeline.
# Key: stage name in _进度.md
# Value: Metadata about the stage
NOVEL_STAGES = [
    {
        "id": "outline",
        "label": "大纲",
        "skill": "novel-create",
        "routes": True,
    },
    {
        "id": "chapter_outline",
        "label": "细纲",
        "skill": "novel-expand",
        "routes": True,
    },
    {
        "id": "draft",
        "label": "正文初稿",
        "skill": "novel-continue", # or novel-craft
        "routes": True,
    },
    {
        "id": "mechanical_review",
        "label": "机检",
        "skill": "novel-review",
        "routes": True,
    },
    {
        "id": "human_review",
        "label": "审稿",
        "skill": "novel-review",
        "routes": True,
    },
    {
        "id": "scoring",
        "label": "评分",
        "skill": "novel-score",
        "routes": True,
    },
    {
        "id": "rewrite",
        "label": "改写",
        "skill": "novel-rewrite",
        "routes": True,
    },
    {
        "id": "export",
        "label": "导出",
        "skill": "novel-craft", # export is usually in craft or a separate tool
        "routes": True,
    },
]

def routing_stages():
    """Returns the ordered list of column labels that participate in routing."""
    return [s["label"] for s in NOVEL_STAGES if s.get("routes")]

def stage_specs():
    """Returns the full stage specifications."""
    return NOVEL_STAGES

# ── novel 边界型机器产物注册表 ──────────────────────────────────────────────
NOVEL_PRODUCT_KINDS = {
    "manifest": {
        "owner": "novel (contract)",
        "path": "_meta.json",
        "layer": "contract",
        "boundary": "project_summary",
    },
    "wiki": {
        "owner": "novel-wiki",
        "path": "设定/动态百科.json",
        "layer": "setting",
        "boundary": "dynamic_facts",
    },
    "relationship_matrix": {
        "owner": "novel-wiki",
        "path": "设定/relationship_matrix.json",
        "layer": "setting",
        "boundary": "relationship_matrix",
    },
    "foreshadowing_ledger": {
        "owner": "novel-wiki",
        "path": "设定/foreshadowing_ledger.json",
        "layer": "setting",
        "boundary": "foreshadowing_seeds",
    },
    "review_report": {
        "owner": "novel-review",
        "path": "审稿/review_report.json",
        "layer": "qa",
        "boundary": "review_audit",
    },
    "score_report": {
        "owner": "novel-score",
        "path": "评分/score_report.json",
        "layer": "qa",
        "boundary": "market_score",
    },
}

# ── 章节文件命名约定 ──────────────────────────────────────────────────────────
CHAPTER_FILE_PATTERN = r"第(\d+)章" # used by project_io

# 正文里识别章节标题的单一真值源（第N章/回/节/卷，支持中文数字）。
# extract_anchors / novel-continue 等切分原文均 import 此处，勿各写一份。
import re as _re
CHAPTER_RE = _re.compile(r"^\s*第\s*[0-9零一二三四五六七八九十百千两]+\s*[章回节卷]", _re.MULTILINE)

def get_product_path(root: str, kind: str) -> str:
    if kind not in NOVEL_PRODUCT_KINDS:
        raise ValueError(f"Unknown product kind: {kind}")
    return os.path.join(root, NOVEL_PRODUCT_KINDS[kind]["path"])

# ── Default Settings ──────────────────────────────────────────────────────────
NOVEL_DEFAULTS = {
    "目标平台": "跨平台",
    "题材": "未定",
    "权利来源": "original",
    "输出格式": "txt,docx,outline",
    "小说生成模式": "稳妥初稿",
    "章节生成粒度": "逐章",
    "AI使用披露": "AI-assisted",
}

# ── Scale Profiles ────────────────────────────────────────────────────────────
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

SCALE_ALIASES = {
    "抖音漫剧": "漫剧",
    "红果短剧": "漫剧",
    "漫剧档": "漫剧",
    "短剧": "微短剧",
    "微短剧档": "微短剧",
}

SCALE_CHOICES = tuple(SCALE_PROFILES) + tuple(SCALE_ALIASES)

def normalize_scale(scale):
    key = str(scale or "").strip()
    return SCALE_ALIASES.get(key, key)

def scale_profile(scale):
    key = normalize_scale(scale)
    if key not in SCALE_PROFILES:
        return SCALE_PROFILES["medium"] # fallback
    return SCALE_PROFILES[key]

# ── Metadata Helpers ──────────────────────────────────────────────────────────
def base_meta(kind, *, outputs, rights_status, title=None):
    from datetime import date
    return {
        "schema_version": 1,
        "kind": kind,
        "title": title,
        "rights_status": rights_status,
        "outputs": list(outputs),
        "created_at": date.today().isoformat(),
    }

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

def derive_title(meta):
    if meta.get("title"): return meta["title"]
    src = meta.get("source_title") or meta.get("source") or "未命名"
    kind = meta.get("kind", "")
    KIND_MAP = {"rewrite": "改写", "expand": "扩写", "continue": "续写", "spinoff": "外传"}
    suffix = KIND_MAP.get(kind, "")
    return f"{src}-{suffix}" if suffix else src

ALLOWED_OUTPUT_FORMATS = ("txt", "docx", "outline", "n2d")

# ── 生产模式枚举（单一真值源；create/rewrite/spinoff 等 init 统一 import，勿各写一份）──
NOVEL_DRAFT_MODES = ("极速初稿", "稳妥初稿", "商业连载", "漫剧源书")
CHAPTER_GRANULARITY = ("逐章", "小批", "全书草稿")
AI_TEXT_USAGE_MODES = ("AI-generated", "AI-assisted", "未使用AI文本")


def parse_outputs(value):
    """逗号分隔的输出格式 → 列表，并对账白名单（非法格式直接报错，不静默放行）。"""
    outputs = [s.strip() for s in str(value or "").replace("，", ",").split(",") if s.strip()]
    unknown = sorted(set(outputs) - set(ALLOWED_OUTPUT_FORMATS))
    if unknown:
        raise ValueError(
            f"未知输出格式 {unknown}；允许值：{', '.join(ALLOWED_OUTPUT_FORMATS)}"
        )
    return outputs

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

# 与 novel-craft/scripts/contract.py 的同名表逐值一致（vendored，由 test_contract_sync.py 守护）。
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
    Vendored copy of novel-craft/scripts/contract.py::rights_metadata —
    test_contract_sync.py 守护两份逐值一致。
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


# ── Utility Helpers (Facade) ──────────────────────────────────────────────────
def docx_to_txt(docx_path, out_txt_path):
    """.docx 段落 → 纯文本（每段一行）。"""
    try:
        from docx import Document
    except ImportError:
        import sys
        print("[err] 缺依赖：pip install python-docx", file=sys.stderr)
        sys.exit(2)
    doc = Document(docx_path)
    with open(out_txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(p.text for p in doc.paragraphs))

def detect_rights_status(novel_txt_path, i_have_rights):
    """读 txt 头部 provenance 注释块判版权。"""
    try:
        with open(novel_txt_path, "r", encoding="utf-8") as f:
            head = f.read(2000)
    except FileNotFoundError:
        return "unknown"
    for line in head.splitlines():
        if not line.startswith("#"):
            break
        if "copyright" in line.lower():
            val = line.split(":", 1)[1].strip().lower() if ":" in line else ""
            if any(k in val for k in ("public", "公版", "gutenberg", "wikisource", "维基文库")):
                return "public-domain"
            if any(k in val for k in ("用户声明", "user-declared")):
                return "user-declared"
    return "user-declared" if i_have_rights else "unknown"

def write_project_settings(out_root, fields, *, note=None):
    from settings import write_settings
    write_settings(out_root, fields, note=note, bold_keys=True)

def demo_chapters_for(target_chapters):
    if target_chapters <= 3: return 0
    if target_chapters <= 20: return 2
    return 3

def build_progress_markdown(title: str, kind: str, chapters: int) -> str:
    """Generates the standard _进度.md content with the routing matrix."""
    header_cols = ["章节", "标题", "字数"] + routing_stages()
    header = "| " + " | ".join(header_cols) + " |"
    separator = "| " + " | ".join(["---"] * len(header_cols)) + " |"
    
    rows = []
    for i in range(1, chapters + 1):
        row = [f"第{i:02d}章", "", "0"] + [PROGRESS_TODO] * len(routing_stages())
        rows.append("| " + " | ".join(row) + " |")
        
    return f"""# 进度 — 《{title}》

## 状态总览
<!-- novel-progress-schema: 1; kind: {kind} -->

{header}
{separator}
{'\n'.join(rows)}

## 待办 / 记录
- [ ] 项目初始化 ✅
"""

import os
