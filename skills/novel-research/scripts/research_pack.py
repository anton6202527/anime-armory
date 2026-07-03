#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Professional research packet scaffolding, checks, and refresh audits.

The script does not browse the web. Agents collect evidence with realtime
search or user-provided sources, then store it here for deterministic reuse.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
INDEX_KIND = "novel_research_sources"
REPORT_KIND = "novel_research_fact_support"
REFRESH_PLAN_KIND = "novel_research_refresh_audit"

HIGH_RISK_DOMAINS = {
    "medical",
    "legal",
    "crime",
    "finance",
    "military",
    "history",
    "religion",
    "overseas",
    "technology",
    "career",
    "platform",
}

DOMAIN_KEYWORDS = {
    "medical": ("医疗", "医院", "医生", "手术", "抢救", "急诊", "药物", "用药", "诊断", "病历", "护士", "ICU", "麻醉"),
    "legal": ("法律", "律师", "法院", "法庭", "诉讼", "合同", "判决", "检察", "证据规则", "刑法", "民法"),
    "crime": ("刑侦", "侦查", "法医", "尸检", "案发", "审讯", "口供", "指纹", "DNA", "监控", "现场勘查"),
    "finance": ("金融", "股票", "基金", "债券", "投行", "并购", "财报", "审计", "期货", "外汇", "风控"),
    "military": ("军事", "军队", "战术", "武器", "弹药", "舰队", "作战", "军衔", "后勤", "情报"),
    "history": ("历史", "朝代", "年号", "制度", "科举", "官制", "礼法", "史料", "考据"),
    "religion": ("宗教", "佛教", "道教", "基督教", "伊斯兰", "神职", "教义", "寺庙", "教会"),
    "overseas": ("海外", "出海", "移民", "签证", "美国", "日本", "东南亚", "跨境", "本地化", "版权辖区"),
    "technology": ("科技", "算法", "芯片", "AI", "人工智能", "网络安全", "黑客", "数据库", "机器人", "工程"),
    "career": ("职场", "行业", "公司", "职业", "流程", "岗位", "医生", "律师", "警察", "记者", "导演", "科研"),
    "platform": ("投稿", "平台", "审核", "备案", "合规", "短剧", "漫剧", "商业连载", "出海", "发行"),
}

COMMERCIAL_SIGNALS = (
    "商业连载",
    "平台投稿",
    "投稿",
    "出海",
    "本地化",
    "改编",
    "漫剧",
    "短剧",
    "红果",
    "番茄",
    "抖音",
    "KDP",
)

DOMAIN_ALIASES = {
    "医学": "medical",
    "医疗": "medical",
    "医院": "medical",
    "法律": "legal",
    "法务": "legal",
    "刑侦": "crime",
    "刑事": "crime",
    "犯罪": "crime",
    "金融": "finance",
    "财经": "finance",
    "军事": "military",
    "军警": "military",
    "历史": "history",
    "考据": "history",
    "宗教": "religion",
    "海外": "overseas",
    "出海": "overseas",
    "本地化": "overseas",
    "科技": "technology",
    "技术": "technology",
    "AI": "technology",
    "人工智能": "technology",
    "职业": "career",
    "行业": "career",
    "平台": "platform",
    "商业": "platform",
    "投稿": "platform",
}

REQUIRED_DOMAIN_KEYS = (
    "research_required_domains",
    "required_research_domains",
    "professional_domains",
    "required_professional_domains",
    "必须专业核验领域",
    "专业资料包必需领域",
)


def today() -> str:
    return date.today().isoformat()


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def slugify(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return "untitled"
    normalized = re.sub(r"[\\/:*?\"<>|\s]+", "_", text)
    normalized = normalized.strip("._")
    return normalized[:80] or "untitled"


def index_path(root: Path) -> Path:
    return root / "资料" / "research_sources.json"


def report_path(root: Path) -> Path:
    return root / "审稿" / "research_fact_support.json"


def refresh_plan_path(root: Path) -> Path:
    return root / "资料" / "research_refresh_plan.md"


def load_index(root: Path) -> dict[str, Any]:
    payload = load_json(index_path(root), None)
    if isinstance(payload, dict):
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload.setdefault("kind", INDEX_KIND)
        payload.setdefault("packs", [])
        return payload
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": INDEX_KIND,
        "updated_at": today(),
        "packs": [],
    }


def parse_chapters(value: str | None) -> list[Any]:
    if not value:
        return []
    text = str(value).strip()
    if not text:
        return []
    if text.lower() == "all" or text == "全书":
        return ["all"]
    out: list[Any] = []
    for part in re.split(r"[,，、\s]+", text):
        if not part:
            continue
        m = re.match(r"^0*(\d+)\s*[-~至]\s*0*(\d+)$", part)
        if m:
            start, end = int(m.group(1)), int(m.group(2))
            if start > end:
                start, end = end, start
            out.append(f"{start}-{end}")
            continue
        if part.isdigit():
            out.append(int(part))
        else:
            out.append(part)
    return out


def chapter_applies(spec: Any, chapter: int | None) -> bool:
    if chapter is None:
        return True
    if spec in (None, "", []):
        return False
    if isinstance(spec, str):
        specs = [spec]
    else:
        specs = spec if isinstance(spec, list) else [spec]
    for item in specs:
        if item == "all":
            return True
        if isinstance(item, int) and item == chapter:
            return True
        text = str(item)
        if text.isdigit() and int(text) == chapter:
            return True
        m = re.match(r"^0*(\d+)\s*[-~至]\s*0*(\d+)$", text)
        if m and int(m.group(1)) <= chapter <= int(m.group(2)):
            return True
    return False


def parse_source(spec: str, idx: int) -> dict[str, Any]:
    parts = [p.strip() for p in spec.split("|")]
    while len(parts) < 6:
        parts.append("")
    title, published_date, source_type, reliability, url, notes = parts[:6]
    return {
        "id": f"SRC-{idx:03d}",
        "title": title,
        "url": url,
        "source_type": source_type or "other",
        "published_date": published_date,
        "accessed_date": today(),
        "reliability": reliability or "medium",
        "notes": notes,
    }


def parse_claim(spec: str, idx: int) -> dict[str, Any]:
    parts = [p.strip() for p in spec.split("|")]
    while len(parts) < 7:
        parts.append("")
    claim, source_ids, confidence, chapters, usage, uncertainty, forbidden_use = parts[:7]
    ids = [p.strip() for p in re.split(r"[,，、\s]+", source_ids) if p.strip()]
    return {
        "id": f"FACT-{idx:03d}",
        "claim": claim,
        "source_ids": ids,
        "confidence": confidence or "medium",
        "applicable_chapters": parse_chapters(chapters),
        "usage": usage,
        "uncertainty": uncertainty,
        "forbidden_use": forbidden_use,
    }


def pack_by_slug(index: dict[str, Any], slug: str) -> dict[str, Any] | None:
    for pack in index.get("packs", []):
        if pack.get("topic_slug") == slug:
            return pack
    return None


def render_markdown(pack: dict[str, Any]) -> str:
    lines = [
        f"# 专业资料包：{pack.get('topic') or pack.get('topic_slug')}",
        "",
        f"- 领域：{pack.get('domain', 'other')}",
        f"- 风险级别：{pack.get('risk_level', 'medium')}",
        f"- 状态：{pack.get('status', 'draft')}",
        f"- 适用章节：{fmt_chapters(pack.get('applicable_chapters'))}",
        f"- 更新日期：{pack.get('updated_at', today())}",
        f"- 有效期：{pack.get('freshness_days', 90)} 天",
        "",
        "## 写作使用边界",
        "",
        "- 只能把“证据支持事实”里的内容写成确定事实。",
        "- “不确定项”只能写成角色视角的疑问、误判或待核验，不得由旁白盖棺定论。",
        "- “禁用项”不得写成行业真相，可作为反派错误操作、谣言或影视化夸张并明确纠正。",
        "",
        "## 来源",
        "",
        "| id | 标题 | 类型 | 日期 | 访问日期 | 可信度 | URL/出处 |",
        "|---|---|---|---|---|---|---|",
    ]
    for src in pack.get("sources", []):
        lines.append(
            f"| {src.get('id','')} | {src.get('title','')} | {src.get('source_type','')} | "
            f"{src.get('published_date','')} | {src.get('accessed_date','')} | "
            f"{src.get('reliability','')} | {src.get('url','')} |"
        )
    if not pack.get("sources"):
        lines.append("| TODO | 待补来源 |  |  |  |  |  |")
    lines.extend([
        "",
        "## 证据支持事实",
        "",
        "| id | 事实 | 来源 | 可信度 | 适用章节 | 使用方式 | 不确定项 | 禁用写法 |",
        "|---|---|---|---|---|---|---|---|",
    ])
    for claim in pack.get("claims", []):
        lines.append(
            f"| {claim.get('id','')} | {claim.get('claim','')} | {','.join(claim.get('source_ids') or [])} | "
            f"{claim.get('confidence','')} | {fmt_chapters(claim.get('applicable_chapters'))} | "
            f"{claim.get('usage','')} | {claim.get('uncertainty','')} | {claim.get('forbidden_use','')} |"
        )
    if not pack.get("claims"):
        lines.append("| TODO | 待补事实 |  |  |  |  |  |  |")
    lines.extend(["", "## 不确定项", ""])
    for item in pack.get("uncertain_items") or []:
        lines.append(f"- {item}")
    if not pack.get("uncertain_items"):
        lines.append("- （暂无；遇到证据冲突或无法确认时写这里）")
    lines.extend(["", "## 禁用项", ""])
    for item in pack.get("forbidden_items") or []:
        lines.append(f"- {item}")
    if not pack.get("forbidden_items"):
        lines.append("- （暂无；行业误区、影视夸张、平台/法规风险写这里）")
    return "\n".join(lines) + "\n"


def fmt_chapters(value: Any) -> str:
    if value in (None, "", []):
        return "未填写"
    if isinstance(value, list):
        return "、".join(str(v) for v in value)
    return str(value)


def scaffold(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    root = Path(root)
    index = load_index(root)
    slug = slugify(args.topic)
    existing = pack_by_slug(index, slug)
    sources = [parse_source(spec, i + 1) for i, spec in enumerate(args.source or [])]
    claims = [parse_claim(spec, i + 1) for i, spec in enumerate(args.claim or [])]
    status = args.status or ("ready" if sources and claims else "draft")
    pack_path = f"资料/专业资料包_{slug}.md"
    pack = existing or {}
    pack.update({
        "topic": args.topic,
        "topic_slug": slug,
        "domain": args.domain,
        "risk_level": args.risk,
        "status": status,
        "pack_path": pack_path,
        "applicable_chapters": parse_chapters(args.chapters) or ["all"],
        "keywords": args.keyword or [],
        "freshness_days": args.freshness_days,
        "updated_at": today(),
        "sources": sources or pack.get("sources", []),
        "claims": claims or pack.get("claims", []),
        "uncertain_items": args.uncertain or pack.get("uncertain_items", []),
        "forbidden_items": args.forbidden or pack.get("forbidden_items", []),
    })
    if existing is None:
        index["packs"].append(pack)
    index["updated_at"] = today()
    write_json(index_path(root), index)
    write_text(root / pack_path, render_markdown(pack))
    return {"pack_path": str(root / pack_path), "index_path": str(index_path(root)), "status": status}


def read_project_text(root: Path) -> str:
    paths = [
        root / "_meta.json",
        root / "_设置.md",
        root / "设定" / "章纲.md",
        root / "设定" / "创作蓝图.md",
    ]
    chunks = []
    for path in paths:
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def read_chapter_text(root: Path, chapter: int | None) -> str:
    cdir = root / "章节"
    if not cdir.is_dir():
        return ""
    if chapter is None:
        chunks = []
        for path in sorted(cdir.glob("*.md")):
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
        return "\n".join(chunks)
    patterns = [f"第{chapter:02d}章", f"第{chapter}章"]
    for path in sorted(cdir.glob("*.md")):
        if any(p in path.name for p in patterns):
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def detect_domains(text: str) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        hits = [kw for kw in keywords if kw and kw in text]
        if hits:
            found[domain] = hits
    return found


def commercial_signal(text: str) -> list[str]:
    return [kw for kw in COMMERCIAL_SIGNALS if kw in text]


def normalize_domain(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text in HIGH_RISK_DOMAINS:
        return text
    if text.lower() in HIGH_RISK_DOMAINS:
        return text.lower()
    return DOMAIN_ALIASES.get(text) or DOMAIN_ALIASES.get(text.upper()) or text.lower()


def parse_domain_list(value: Any) -> list[str]:
    if value in (None, "", []):
        return []
    raw: list[Any]
    if isinstance(value, list):
        raw = value
    else:
        raw = re.split(r"[,，、;\s]+", str(value))
    out: list[str] = []
    for item in raw:
        domain = normalize_domain(str(item))
        if domain and domain not in out:
            out.append(domain)
    return out


def read_required_domains(root: Path) -> list[str]:
    domains: list[str] = []
    meta = load_json(root / "_meta.json", {}) or {}
    if isinstance(meta, dict):
        for key in REQUIRED_DOMAIN_KEYS:
            for item in parse_domain_list(meta.get(key)):
                if item not in domains:
                    domains.append(item)
    req = load_json(root / "资料" / "research_requirements.json", {}) or {}
    if isinstance(req, dict):
        for key in ("required_domains", "domains", "professional_domains"):
            for item in parse_domain_list(req.get(key)):
                if item not in domains:
                    domains.append(item)
    settings_path = root / "_设置.md"
    if settings_path.exists():
        text = settings_path.read_text(encoding="utf-8", errors="replace")
        for key in REQUIRED_DOMAIN_KEYS:
            pattern = re.compile(rf"{re.escape(key)}\s*[:：]\s*([^\n]+)")
            for match in pattern.finditer(text):
                for item in parse_domain_list(match.group(1)):
                    if item not in domains:
                        domains.append(item)
    return domains


def pack_matches_domain(pack: dict[str, Any], domain: str, chapter: int | None, text: str) -> bool:
    if pack.get("domain") == domain and chapter_applies(pack.get("applicable_chapters"), chapter):
        return True
    keywords = pack.get("keywords") or []
    if keywords and any(str(kw) in text for kw in keywords):
        return chapter_applies(pack.get("applicable_chapters"), chapter)
    return False


def relevant_packs(index: dict[str, Any], chapter: int | None, text: str = "") -> list[dict[str, Any]]:
    packs = []
    for pack in index.get("packs", []):
        if chapter_applies(pack.get("applicable_chapters"), chapter):
            packs.append(pack)
            continue
        keywords = pack.get("keywords") or []
        if text and keywords and any(str(kw) in text for kw in keywords):
            packs.append(pack)
    return packs


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def pack_is_high_risk(pack: dict[str, Any]) -> bool:
    risk = str(pack.get("risk_level") or "").strip().lower()
    return risk in {"high", "高", "高风险"} or pack.get("domain") in HIGH_RISK_DOMAINS


def pack_freshness(pack: dict[str, Any]) -> dict[str, Any]:
    freshness_days = safe_int(pack.get("freshness_days"), 90)
    raw_updated_at = str(pack.get("updated_at") or "").strip()
    updated_at = parse_date(raw_updated_at)
    if not updated_at:
        return {
            "updated_at": raw_updated_at,
            "freshness_days": freshness_days,
            "age_days": None,
            "days_remaining": None,
            "stale": True,
            "reason": "missing_updated_at",
        }
    age_days = (date.today() - updated_at).days
    return {
        "updated_at": updated_at.isoformat(),
        "freshness_days": freshness_days,
        "age_days": age_days,
        "days_remaining": freshness_days - age_days,
        "stale": age_days > freshness_days,
        "reason": "expired" if age_days > freshness_days else "fresh",
    }


def finding(severity: str, typ: str, message: str, *, pack: str = "", domain: str = "", evidence: str = "") -> dict[str, Any]:
    return {
        "severity": severity,
        "type": typ,
        "message": message,
        "pack": pack,
        "domain": domain,
        "evidence": evidence,
    }


def validate_pack(root: Path, pack: dict[str, Any], chapter: int | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    topic = pack.get("topic") or pack.get("topic_slug") or "unknown"
    status = pack.get("status") or "draft"
    high_risk = pack_is_high_risk(pack)
    if chapter is not None and not chapter_applies(pack.get("applicable_chapters"), chapter):
        return out
    if status != "ready":
        sev = "阻断级" if high_risk else "建议级"
        out.append(finding(sev, "pack_not_ready", f"资料包 {topic} 不是 ready：status={status}", pack=topic))
    rel = pack.get("pack_path")
    if rel and not (root / rel).exists():
        out.append(finding("阻断级", "pack_file_missing", f"资料包文件不存在：{rel}", pack=topic))
    sources = pack.get("sources") or []
    claims = pack.get("claims") or []
    if not sources:
        out.append(finding("阻断级" if high_risk else "建议级", "no_sources", f"资料包 {topic} 缺来源", pack=topic))
    if not claims:
        out.append(finding("阻断级" if high_risk else "建议级", "no_claims", f"资料包 {topic} 缺可写事实 claims", pack=topic))
    source_ids = {src.get("id") for src in sources if src.get("id")}
    for src in sources:
        sid = src.get("id") or "SRC-?"
        if not src.get("title"):
            out.append(finding("阻断级", "source_missing_title", f"{sid} 缺标题/出处名", pack=topic))
        if not (src.get("published_date") or src.get("accessed_date")):
            out.append(finding("阻断级", "source_missing_date", f"{sid} 缺发布日期或访问日期", pack=topic))
        if src.get("reliability") not in {"high", "medium", "low"}:
            out.append(finding("阻断级", "source_missing_reliability", f"{sid} 可信度必须是 high/medium/low", pack=topic))
    for claim in claims:
        cid = claim.get("id") or "FACT-?"
        ids = set(claim.get("source_ids") or [])
        if not claim.get("claim"):
            out.append(finding("阻断级", "claim_missing_text", f"{cid} 缺事实文本", pack=topic))
        if not ids:
            out.append(finding("阻断级", "claim_missing_source", f"{cid} 未绑定来源", pack=topic))
        missing = sorted(ids - source_ids)
        if missing:
            out.append(finding("阻断级", "claim_unknown_source", f"{cid} 引用未知来源：{', '.join(missing)}", pack=topic))
        if claim.get("confidence") not in {"high", "medium", "low"}:
            out.append(finding("阻断级", "claim_missing_confidence", f"{cid} 可信度必须是 high/medium/low", pack=topic))
        if not claim.get("applicable_chapters"):
            out.append(finding("建议级", "claim_missing_chapter_scope", f"{cid} 未写适用章节", pack=topic))
    freshness = pack_freshness(pack)
    freshness_days = freshness["freshness_days"]
    if freshness["reason"] == "missing_updated_at":
        sev = "阻断级" if high_risk else "建议级"
        out.append(finding(sev, "pack_missing_updated_at", f"资料包 {topic} 缺 updated_at，无法判断是否过期", pack=topic))
    elif freshness["stale"]:
        sev = "阻断级" if high_risk else "建议级"
        out.append(finding(
            sev,
            "pack_stale",
            f"资料包 {topic} 已超过 {freshness_days} 天有效期（updated_at={freshness['updated_at']}，age={freshness['age_days']} 天）",
            pack=topic,
        ))
    return out


def check_project(root: str | Path, chapter: int | None = None, *, write: bool = True) -> dict[str, Any]:
    root = Path(root)
    idx = load_index(root)
    has_index = index_path(root).exists()
    project_text = read_project_text(root)
    chapter_text = read_chapter_text(root, chapter)
    text = "\n".join([project_text, chapter_text])
    domains = detect_domains(text)
    required_domains = read_required_domains(root)
    commercial = commercial_signal(text)
    findings: list[dict[str, Any]] = []
    packs = idx.get("packs", []) if has_index else []
    for domain in required_domains:
        matched = [
            p for p in packs
            if pack_matches_domain(p, domain, chapter, text)
            or (p.get("domain") == domain and chapter_applies(p.get("applicable_chapters"), chapter))
        ]
        ready = [p for p in matched if p.get("status") == "ready"]
        if not ready:
            findings.append(finding(
                "阻断级",
                "missing_required_research_pack",
                f"项目声明 {domain} 为必须专业核验领域，但没有适用的 ready 专业资料包",
                domain=domain,
                evidence="research_required_domains",
            ))
    for domain, hits in domains.items():
        matched = [p for p in packs if pack_matches_domain(p, domain, chapter, text)]
        ready = [p for p in matched if p.get("status") == "ready"]
        if not ready:
            findings.append(finding(
                "阻断级",
                "missing_research_pack",
                f"检测到 {domain} 专业场景关键词，但没有适用的 ready 专业资料包",
                domain=domain,
                evidence="、".join(hits[:8]),
            ))
    if commercial and not has_index:
        findings.append(finding(
            "建议级",
            "commercial_research_recommended",
            "商业/平台/出海/改编项目建议建立平台规则或目标市场资料包",
            evidence="、".join(commercial[:8]),
        ))
    for pack in relevant_packs(idx, chapter, text):
        findings.extend(validate_pack(root, pack, chapter=chapter))
    blocking = sum(1 for item in findings if item.get("severity") == "阻断级")
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": REPORT_KIND,
        "generated_at": today(),
        "project_root": str(root.resolve()),
        "chapter": chapter,
        "ran": True,
        "detected_domains": domains,
        "required_domains": required_domains,
        "commercial_signals": commercial,
        "packs_checked": [
            {
                "topic": p.get("topic"),
                "domain": p.get("domain"),
                "status": p.get("status"),
                "pack_path": p.get("pack_path"),
            }
            for p in relevant_packs(idx, chapter, text)
        ],
        "total": len(findings),
        "blocking": blocking,
        "alerts": findings,
    }
    if write:
        write_json(report_path(root), report)
    return report


def md_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", " ").replace("|", "\\|").strip()


def relpath(path: str | Path, base: str | Path) -> str:
    path = Path(path)
    base = Path(base)
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def find_research_indexes(scan_root: str | Path) -> list[Path]:
    root = Path(scan_root)
    seen: dict[str, Path] = {}
    direct = index_path(root)
    if direct.exists():
        seen[str(direct.resolve())] = direct
    bases = []
    novel_root = root / "创作区" / "写小说"
    if novel_root.exists():
        bases.append(novel_root)
    bases.append(root)
    for base in bases:
        if not base.exists():
            continue
        for path in base.glob("**/资料/research_sources.json"):
            seen.setdefault(str(path.resolve()), path)
    return sorted(seen.values(), key=lambda p: str(p))


def refresh_task_for_pack(project_root: Path, pack: dict[str, Any], freshness: dict[str, Any]) -> dict[str, Any]:
    topic = pack.get("topic") or pack.get("topic_slug") or "unknown"
    domain = pack.get("domain") or "other"
    keywords = " ".join(str(k) for k in (pack.get("keywords") or [])[:5])
    query_parts = [str(topic), str(domain), keywords, "官方", "最新", "指南", "规则", today()[:4]]
    return {
        "project_root": str(project_root.resolve()),
        "topic": topic,
        "domain": domain,
        "risk_level": pack.get("risk_level") or "medium",
        "pack_path": pack.get("pack_path") or "",
        "updated_at": freshness.get("updated_at") or "",
        "freshness_days": freshness.get("freshness_days"),
        "age_days": freshness.get("age_days"),
        "reason": freshness.get("reason") or "expired",
        "suggested_query": " ".join(part for part in query_parts if str(part).strip()),
        "action": "实时深搜核验；更新 sources/claims/updated_at；不能确认的内容转入 uncertain_items/forbidden_items。",
    }


def audit_project_refresh(index_file: str | Path) -> dict[str, Any]:
    index_file = Path(index_file)
    project_root = index_file.parent.parent
    payload = load_json(index_file, {}) or {}
    packs = payload.get("packs") if isinstance(payload, dict) else []
    if not isinstance(packs, list):
        packs = []
    items = []
    tasks = []
    stale_count = 0
    blocking_count = 0
    near_expiry_count = 0
    for pack in packs:
        if not isinstance(pack, dict):
            continue
        freshness = pack_freshness(pack)
        high_risk = pack_is_high_risk(pack)
        severity = ""
        if freshness["stale"]:
            stale_count += 1
            severity = "阻断级" if high_risk else "建议级"
            if high_risk:
                blocking_count += 1
                tasks.append(refresh_task_for_pack(project_root, pack, freshness))
        elif freshness.get("days_remaining") is not None and freshness["days_remaining"] <= 14:
            near_expiry_count += 1
            severity = "临期提醒"
        item = {
            "topic": pack.get("topic") or pack.get("topic_slug") or "unknown",
            "domain": pack.get("domain") or "other",
            "risk_level": pack.get("risk_level") or "medium",
            "status": pack.get("status") or "draft",
            "pack_path": pack.get("pack_path") or "",
            "updated_at": freshness.get("updated_at") or "",
            "freshness_days": freshness.get("freshness_days"),
            "age_days": freshness.get("age_days"),
            "days_remaining": freshness.get("days_remaining"),
            "stale": freshness["stale"],
            "reason": freshness["reason"],
            "severity": severity,
            "high_risk": high_risk,
        }
        items.append(item)
    return {
        "project_root": str(project_root.resolve()),
        "index_path": str(index_file.resolve()),
        "plan_path": str(refresh_plan_path(project_root).resolve()),
        "pack_count": len(items),
        "stale_count": stale_count,
        "near_expiry_count": near_expiry_count,
        "blocking": blocking_count,
        "high_risk_tasks": tasks,
        "packs": items,
    }


def render_project_refresh_plan(report: dict[str, Any]) -> str:
    lines = [
        "# 专业资料包刷新计划",
        "",
        f"- 生成日期：{today()}",
        f"- 作品根：{report.get('project_root')}",
        f"- 来源索引：{report.get('index_path')}",
        f"- 总资料包：{report.get('pack_count', 0)}",
        f"- 已过期：{report.get('stale_count', 0)}",
        f"- 临近过期：{report.get('near_expiry_count', 0)}",
        f"- 阻断级高风险过期包：{report.get('blocking', 0)}",
        "",
        "## 需实时深搜任务清单",
        "",
    ]
    tasks = report.get("high_risk_tasks") or []
    if tasks:
        lines.extend([
            "| 主题 | 领域 | 风险 | 过期原因 | 建议检索式 | 动作 |",
            "|---|---|---|---|---|---|",
        ])
        for task in tasks:
            lines.append(
                "| "
                + " | ".join([
                    md_cell(task.get("topic")),
                    md_cell(task.get("domain")),
                    md_cell(task.get("risk_level")),
                    md_cell(task.get("reason")),
                    md_cell(task.get("suggested_query")),
                    md_cell(task.get("action")),
                ])
                + " |"
            )
    else:
        lines.append("- 暂无阻断级高风险过期资料包。")
    lines.extend([
        "",
        "## 过期或临近过期资料包",
        "",
        "| 状态 | 主题 | 领域 | 风险 | updated_at | 有效期 | age | 剩余天数 | 文件 |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    rows = [
        p for p in report.get("packs", [])
        if p.get("stale") or p.get("severity") == "临期提醒"
    ]
    if rows:
        for pack in rows:
            lines.append(
                "| "
                + " | ".join([
                    md_cell(pack.get("severity") or ("过期" if pack.get("stale") else "正常")),
                    md_cell(pack.get("topic")),
                    md_cell(pack.get("domain")),
                    md_cell(pack.get("risk_level")),
                    md_cell(pack.get("updated_at")),
                    md_cell(pack.get("freshness_days")),
                    md_cell(pack.get("age_days")),
                    md_cell(pack.get("days_remaining")),
                    md_cell(pack.get("pack_path")),
                ])
                + " |"
            )
    else:
        lines.append("| 无 |  |  |  |  |  |  |  |  |")
    lines.extend([
        "",
        "## 全部资料包 freshness",
        "",
        "| 主题 | 领域 | 风险 | 状态 | updated_at | 有效期 | age | 剩余天数 | stale |",
        "|---|---|---|---|---|---|---|---|---|",
    ])
    for pack in report.get("packs", []):
        lines.append(
            "| "
            + " | ".join([
                md_cell(pack.get("topic")),
                md_cell(pack.get("domain")),
                md_cell(pack.get("risk_level")),
                md_cell(pack.get("status")),
                md_cell(pack.get("updated_at")),
                md_cell(pack.get("freshness_days")),
                md_cell(pack.get("age_days")),
                md_cell(pack.get("days_remaining")),
                md_cell(pack.get("stale")),
            ])
            + " |"
        )
    if not report.get("packs"):
        lines.append("| 无资料包 |  |  |  |  |  |  |  |  |")
    return "\n".join(lines) + "\n"


def render_aggregate_refresh_plan(audit: dict[str, Any]) -> str:
    lines = [
        "# novel-research 全库刷新计划",
        "",
        f"- 生成日期：{today()}",
        f"- 扫描根：{audit.get('scan_root')}",
        f"- 项目数：{audit.get('project_count', 0)}",
        f"- 资料包总数：{audit.get('pack_count', 0)}",
        f"- 已过期资料包：{audit.get('stale_count', 0)}",
        f"- 阻断级高风险过期包：{audit.get('blocking', 0)}",
        "",
        "## 需实时深搜任务清单",
        "",
    ]
    tasks = audit.get("high_risk_tasks") or []
    if tasks:
        lines.extend([
            "| 项目 | 主题 | 领域 | 风险 | updated_at | 建议检索式 | 动作 |",
            "|---|---|---|---|---|---|---|",
        ])
        scan_root = Path(audit.get("scan_root") or ".")
        for task in tasks:
            lines.append(
                "| "
                + " | ".join([
                    md_cell(relpath(task.get("project_root") or "", scan_root)),
                    md_cell(task.get("topic")),
                    md_cell(task.get("domain")),
                    md_cell(task.get("risk_level")),
                    md_cell(task.get("updated_at")),
                    md_cell(task.get("suggested_query")),
                    md_cell(task.get("action")),
                ])
                + " |"
            )
    else:
        lines.append("- 暂无阻断级高风险过期资料包。")
    lines.extend([
        "",
        "## 项目汇总",
        "",
        "| 项目 | 资料包 | 已过期 | 临近过期 | 阻断 | 计划文件 |",
        "|---|---|---|---|---|---|",
    ])
    for project in audit.get("projects", []):
        scan_root = Path(audit.get("scan_root") or ".")
        lines.append(
            "| "
            + " | ".join([
                md_cell(relpath(project.get("project_root") or "", scan_root)),
                md_cell(project.get("pack_count")),
                md_cell(project.get("stale_count")),
                md_cell(project.get("near_expiry_count")),
                md_cell(project.get("blocking")),
                md_cell(relpath(project.get("plan_path") or "", scan_root)),
            ])
            + " |"
        )
    if not audit.get("projects"):
        lines.append("| 未找到 research_sources.json | 0 | 0 | 0 | 0 |  |")
    return "\n".join(lines) + "\n"


def refresh_audit(scan_root: str | Path, *, write: bool = True, aggregate_out: str | Path | None = None) -> dict[str, Any]:
    root = Path(scan_root)
    indexes = find_research_indexes(root)
    projects = [audit_project_refresh(path) for path in indexes]
    tasks = []
    for project in projects:
        tasks.extend(project.get("high_risk_tasks") or [])
    audit = {
        "schema_version": SCHEMA_VERSION,
        "kind": REFRESH_PLAN_KIND,
        "generated_at": today(),
        "scan_root": str(root.resolve()),
        "project_count": len(projects),
        "pack_count": sum(p.get("pack_count", 0) for p in projects),
        "stale_count": sum(p.get("stale_count", 0) for p in projects),
        "near_expiry_count": sum(p.get("near_expiry_count", 0) for p in projects),
        "blocking": sum(p.get("blocking", 0) for p in projects),
        "high_risk_tasks": tasks,
        "projects": projects,
        "aggregate_plan_path": "",
    }
    if write:
        for project in projects:
            write_text(Path(project["plan_path"]), render_project_refresh_plan(project))
        out_path: Path | None = None
        if aggregate_out:
            out_path = Path(aggregate_out)
        elif len(projects) != 1:
            out_path = refresh_plan_path(root)
        elif projects:
            audit["aggregate_plan_path"] = projects[0]["plan_path"]
        if out_path:
            audit["aggregate_plan_path"] = str(out_path.resolve())
            write_text(out_path, render_aggregate_refresh_plan(audit))
    return audit


def cmd_scaffold(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    result = scaffold(root, args)
    print(f"[ok] 专业资料包 → {result['pack_path']}")
    print(f"[ok] 来源索引 → {result['index_path']}")
    print(f"     status={result['status']}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = Path(args.project_root)
    if not root.is_dir():
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = check_project(root, chapter=args.chapter, write=True)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"[ok] 专业事实证据检查 → {report_path(root)}")
        print(f"     阻断：{report['blocking']} | 总问题：{report['total']}")
        for item in report["alerts"][:10]:
            print(f"  - [{item['severity']}] {item['type']}: {item['message']}")
    return 1 if report["blocking"] else 0


def cmd_refresh_audit(args: argparse.Namespace) -> int:
    root = Path(args.scan_root)
    if not root.exists():
        print(f"[err] 找不到扫描根：{root}", file=sys.stderr)
        return 2
    report = refresh_audit(root, write=not args.no_write, aggregate_out=args.aggregate_out)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        if report.get("aggregate_plan_path"):
            print(f"[ok] 全库刷新计划 → {report['aggregate_plan_path']}")
        print(
            f"     项目：{report['project_count']} | 资料包：{report['pack_count']} | "
            f"过期：{report['stale_count']} | 阻断级高风险：{report['blocking']}"
        )
        for task in report.get("high_risk_tasks", [])[:10]:
            print(f"  - [需实时深搜] {task['topic']} ({task['domain']}): {task['suggested_query']}")
    return 1 if report["blocking"] and not args.no_fail else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="novel professional research packet tools")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sc = sub.add_parser("scaffold", help="create/update a professional research packet")
    sc.add_argument("project_root")
    sc.add_argument("--topic", required=True)
    sc.add_argument("--domain", default="other")
    sc.add_argument("--chapters", default="all")
    sc.add_argument("--risk", choices=["high", "medium", "low"], default="high")
    sc.add_argument("--status", choices=["draft", "ready", "stale", "needs_review"], default=None)
    sc.add_argument("--freshness-days", type=int, default=90)
    sc.add_argument("--keyword", action="append", default=[])
    sc.add_argument("--source", action="append", default=[], help="标题|日期|类型|可信度|URL|说明")
    sc.add_argument("--claim", action="append", default=[], help="事实|来源ID|可信度|章节|使用方式|不确定项|禁用写法")
    sc.add_argument("--uncertain", action="append", default=[])
    sc.add_argument("--forbidden", action="append", default=[])
    sc.set_defaults(func=cmd_scaffold)

    ck = sub.add_parser("check", help="validate research evidence coverage")
    ck.add_argument("project_root")
    ck.add_argument("--chapter", type=int, default=None)
    ck.add_argument("--json", action="store_true")
    ck.set_defaults(func=cmd_check)

    ra = sub.add_parser("refresh-audit", help="scan research_sources.json files and write refresh plans")
    ra.add_argument("scan_root", nargs="?", default=".")
    ra.add_argument("--json", action="store_true")
    ra.add_argument("--no-write", action="store_true")
    ra.add_argument("--no-fail", action="store_true", help="return 0 even when high-risk stale packs exist")
    ra.add_argument("--aggregate-out", default=None, help="optional aggregate research_refresh_plan.md path")
    ra.set_defaults(func=cmd_refresh_audit)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
