#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect shared market baseline artifacts for novel-score and self-audit.

The script fetches public rank pages when possible and preserves fetch failures
as evidence instead of inventing trends. Agents may add structured manual
evidence from browser/search inspection with --manual-evidence; --note is only
a human-readable memo.
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_SOURCES = [
    ("番茄小说", "https://fanqienovel.com/rank", "web_novel_rank"),
    ("起点中文网", "https://www.qidian.com/rank/", "web_novel_rank"),
    ("晋江文学城", "https://m.jjwxc.net/rank/index", "web_novel_rank"),
]

# 红果/抖音 短剧·漫剧榜单在 App/小程序内，无可直接抓取的公开网页。
# 它们却是默认权重档（红果/抖音 商业爽文向）真正对标的平台——若静默缺席，
# 基准会"看起来覆盖了"实则没覆盖。这里放可见的占位行（status=manual_required，
# 不计入有效证据），逼采集者用 --manual-evidence / --source <第三方报告URL> 显式补齐。
MANUAL_REQUIRED_SOURCES = [
    ("红果短剧", "App/小程序内榜（无公开网页），需第三方榜单报告", "short_drama_rank"),
    ("抖音漫剧/短剧", "App 内热榜（无公开网页），需第三方榜单报告", "short_drama_rank"),
]

# target_platform 命中这些词时，要求 红果/抖音 有真实覆盖（--manual-evidence 或 --source）。
SHORT_DRAMA_KEYWORDS = ("红果", "抖音", "漫剧", "短剧")

# 短剧/漫剧「平台覆盖」证据的保质期，与日榜（expires_after_days，默认 21）解耦。
# 红果/抖音漫剧 没有公开日榜网页，平台覆盖只能靠行业报告/MAU/审核新规这类
# 结构性慢变量证据——它们天然是按月/季发布的（如 QuestMobile 月活、平台审核新规），
# 用 21 天日榜窗口卡，会让覆盖闸「永远无法用真实证据满足」，逼每次评分都 --allow-stale-baseline，
# 把硬闸退化成长期豁免。故覆盖证据另给一个更长但仍有界的窗口（一个季度），
# 既不放过两三年前的旧 factoid，也不误伤当季真实行业证据。
COVERAGE_EVIDENCE_MAX_AGE_DAYS = 90


def coverage_window(expires_after_days):
    """平台覆盖证据窗口：至少一个季度，且不短于调用方设的日榜窗口。"""
    try:
        base = int(expires_after_days or 0)
    except (TypeError, ValueError):
        base = 0
    return max(base, COVERAGE_EVIDENCE_MAX_AGE_DAYS)
SIGNAL_NOISE_RE = re.compile(
    r"("
    r"@font-face|font-family|window\.|document\.|XMLHttpRequest|"
    r"\bfunction\b|\bvar\s+|\blet\s+|\bconst\s+|"
    r"<script|</script|sdk|captcha|csrf|jQuery|ajax|"
    r"You need to enable JavaScript|url\(|data:image|"
    r"\{[^}]*:[^}]*\}|^\s*[.#][\w-]+\s*\{|"
    r"user-select|webkit|moz-|ms-|khtml-|prefers-color-scheme"
    r")",
    re.IGNORECASE,
)
MOJIBAKE_RE = re.compile(r"[\ufffd]")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        if self._in_title:
            self.title += text
        if len(text) >= 2:
            self.parts.append(text)


def fetch_text(url, timeout):
    req = Request(url, headers={"User-Agent": "anime-armory-novel-baseline/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        raw = resp.read(2_000_000)
    parser = TextExtractor()
    parser.feed(raw.decode("utf-8", errors="replace"))
    return parser.title.strip(), parser.parts


def _is_noise_signal(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if not text:
        return True
    if SIGNAL_NOISE_RE.search(text):
        return True
    if MOJIBAKE_RE.search(text):
        return True
    if len(text) > 260 and not re.search(r"[\u4e00-\u9fff]{4,}", text):
        return True
    code_marks = len(re.findall(r"[{}();=<>]", text))
    if len(text) >= 40 and code_marks / max(len(text), 1) > 0.08:
        return True
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    if chinese_chars == 0 and len(text) <= 40:
        return True
    if len(text) >= 20 and chinese_chars == 0 and code_marks:
        return True
    return False


def clean_signals(parts, max_signals):
    signals = []
    seen = set()
    for raw in parts or []:
        text = re.sub(r"\s+", " ", str(raw or "")).strip()
        if _is_noise_signal(text):
            continue
        if len(text) > 180:
            text = text[:177].rstrip() + "..."
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        signals.append(text)
        if len(signals) >= max_signals:
            break
    return signals


def parse_source(value):
    parts = value.split("|", 2)
    if len(parts) == 2:
        platform, url = parts
        use_for = "web_novel_rank"
    elif len(parts) == 3:
        platform, url, use_for = parts
    else:
        raise argparse.ArgumentTypeError("--source 格式：平台|URL[|use_for]")
    return platform.strip(), url.strip(), use_for.strip()


def parse_manual_evidence(value):
    parts = [p.strip() for p in value.split("|")]
    if len(parts) not in (4, 5):
        raise argparse.ArgumentTypeError(
            "--manual-evidence 格式：平台|日期YYYY-MM-DD|来源|结论[|URL]"
        )
    platform, date_s, source, summary = parts[:4]
    url = parts[4] if len(parts) == 5 else ""
    if not platform or not source or not summary:
        raise argparse.ArgumentTypeError("--manual-evidence 的 平台/来源/结论 不能为空")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_s):
        raise argparse.ArgumentTypeError("--manual-evidence 日期必须是 YYYY-MM-DD")
    return {
        "platform": platform,
        "date": date_s,
        "source": source,
        "summary": summary,
        "url": url,
        "status": "manual_ok",
    }


def manual_evidence_fresh(item, baseline_date, expires_after_days):
    try:
        evidence_date = datetime.strptime(str(item.get("date") or ""), "%Y-%m-%d").date()
        base_date = datetime.strptime(str(baseline_date or ""), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return False
    if evidence_date > base_date:
        return False
    return base_date <= evidence_date + timedelta(days=int(expires_after_days or 21))


def _quality_band(score):
    if score >= 0.78:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _https_bonus(url):
    return 0.08 if str(url or "").startswith("https://") else 0.0


def source_quality(item):
    """Deterministic evidence quality score, 0-1.

    The score is a confidence hint for prompt/reporting, not a truth detector.
    """
    reasons = []
    score = 0.0
    status = str(item.get("status") or "")
    signals = [str(s).strip() for s in item.get("signals") or [] if str(s).strip()]
    if status == "ok" and signals:
        score += 0.42
        reasons.append("status=ok 且 signals 非空")
        signal_score = min(0.25, len(signals) / 80.0)
        score += signal_score
        reasons.append(f"signals={len(signals)}")
        if item.get("title"):
            score += 0.08
            reasons.append("有页面标题")
        bonus = _https_bonus(item.get("url"))
        if bonus:
            score += bonus
            reasons.append("https 来源")
        if str(item.get("use_for") or "").endswith("_rank"):
            score += 0.08
            reasons.append("rank 用途匹配")
    elif status == "ok":
        reasons.append("status=ok 但 signals 为空，不计有效证据")
    elif status == "manual_required":
        reasons.append("manual_required 占位，不计有效证据")
    elif status == "fetch_error":
        reasons.append("fetch_error，不计有效证据")
    else:
        reasons.append(f"status={status or 'missing'}")
    score = min(1.0, round(score, 4))
    return {"score": score, "confidence": _quality_band(score), "reasons": reasons[:6]}


def manual_evidence_quality(item):
    reasons = []
    score = 0.0
    if item.get("status") == "manual_ok":
        score += 0.38
        reasons.append("结构化 manual_evidence")
    if item.get("url"):
        score += 0.14
        reasons.append("带 URL")
    source = str(item.get("source") or "")
    if any(key in source for key in ("官方", "平台", "榜单", "报告", "数据")):
        score += 0.16
        reasons.append("来源类型较明确")
    summary = str(item.get("summary") or "")
    if len(summary) >= 12:
        score += 0.14
        reasons.append("结论非空且有信息量")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(item.get("date") or "")):
        score += 0.10
        reasons.append("带核验日期")
    score = min(1.0, round(score, 4))
    return {"score": score, "confidence": _quality_band(score), "reasons": reasons[:6]}


def attach_evidence_quality(result):
    source_scores = []
    for source in result.get("sources") or []:
        quality = source_quality(source)
        source["source_quality"] = quality
        source_scores.append(quality["score"])
    manual_scores = []
    for item in result.get("manual_evidence") or []:
        quality = manual_evidence_quality(item)
        item["evidence_quality"] = quality
        manual_scores.append(quality["score"])
    effective_scores = [s for s in source_scores + manual_scores if s > 0]
    avg = round(sum(effective_scores) / len(effective_scores), 4) if effective_scores else 0.0
    result["evidence_quality"] = {
        "score": avg,
        "confidence": _quality_band(avg),
        "source_count": len(source_scores),
        "manual_evidence_count": len(manual_scores),
        "effective_evidence_count": len(effective_scores),
        "note": "证据质量只作为评分 prompt 的可信度提示；不替代人工核验。",
    }
    return result


def build_evidence_tasks(result):
    tasks = []
    for idx, warning in enumerate(result.get("coverage_warnings") or [], 1):
        tasks.append({
            "id": f"MARKET-EVIDENCE-{idx:03d}",
            "status": "open",
            "priority": "P1",
            "title": "补齐目标平台市场证据",
            "reason": warning,
            "target_platform": result.get("target_platform"),
            "recommended_skill": "novel-research",
            "return_to_stage": "market_baseline",
            "required_evidence": [
                "至少一条覆盖红果/抖音/漫剧/短剧的结构化人工证据：平台|日期|来源|结论|URL",
                "若用于商业蓝图，把差异化缺口和拥挤度写入 novel-research 平台市场资料包",
            ],
            "suggested_commands": [
                "python3 skills/novel-score/scripts/collect_market_baseline.py \"<作品根>/评分\" --target-platform \"<目标平台>\" --allow-fetch-errors --manual-evidence \"红果短剧|YYYY-MM-DD|第三方榜单|结论|URL\"",
                "python3 skills/novel-research/scripts/research_pack.py scaffold \"<作品根>\" --topic \"平台市场\" --domain platform --risk high --keyword \"红果\" --keyword \"抖音\"",
            ],
        })
    return tasks


def build_evidence_jobs(result):
    jobs = []
    target = result.get("target_platform") or "红果/抖音/漫剧/短剧"
    baseline_date = result.get("baseline_date")
    for idx, task in enumerate(result.get("evidence_tasks") or [], 1):
        jobs.append({
            "id": f"MARKET-SEARCH-{idx:03d}",
            "status": "open",
            "kind": "novel_market_evidence_search_job",
            "target_platform": target,
            "baseline_date": baseline_date,
            "source_task_id": task.get("id"),
            "search_queries": [
                f"{target} 热榜 榜单 报告 {baseline_date}",
                f"红果短剧 热榜 第三方榜单 报告 {baseline_date}",
                f"抖音漫剧 短剧 热榜 数据 报告 {baseline_date}",
                f"{target} 题材 趋势 短剧 漫剧 {baseline_date}",
            ],
            "required_output_schema": {
                "platform": "红果短剧/抖音漫剧/短剧等被覆盖平台",
                "date": "YYYY-MM-DD，证据核验或报告发布日期",
                "source": "官方/第三方榜单/行业报告/平台公开页等来源名称",
                "summary": "一句话趋势结论，必须可追溯到来源",
                "url": "https://...，能打开的证据链接；无公开链接时说明不可公开复核",
            },
            "manual_evidence_format": "平台|日期YYYY-MM-DD|来源|结论|URL",
            "return_command_template": (
                'python3 skills/novel-score/scripts/collect_market_baseline.py "<作品根>/评分" '
                '--target-platform "<目标平台>" --allow-fetch-errors '
                '--manual-evidence "平台|YYYY-MM-DD|来源|结论|URL"'
            ),
            "acceptance": [
                "日期未过期，且不晚于 baseline_date",
                "platform/source/summary 至少一个字段明确命中红果/抖音/漫剧/短剧",
                "summary 不得只是自由备注，必须能被 source/url 支撑",
            ],
        })
    return jobs


def collect(args):
    sources = list(DEFAULT_SOURCES) if args.defaults else []
    sources.extend(parse_source(v) for v in args.source)
    now = datetime.now(timezone.utc).astimezone()
    result = {
        "schema_version": 1,
        "kind": "novel_market_baseline",
        "baseline_date": args.date,
        "target_platform": args.target_platform,
        "collected_at": now.isoformat(timespec="seconds"),
        "expires_after_days": args.expires_after_days,
        "sources": [],
        "notes": args.note,
        "manual_evidence": [parse_manual_evidence(v) for v in getattr(args, "manual_evidence", [])],
    }
    for platform, url, use_for in sources:
        item = {
            "platform": platform,
            "url": url,
            "use_for": use_for,
            "collected_at": now.isoformat(timespec="seconds"),
            "status": "ok",
            "title": "",
            "signals": [],
        }
        try:
            title, parts = fetch_text(url, args.timeout)
            item["title"] = title or platform
            item["signals"] = clean_signals(parts, args.max_signals)
        except (OSError, URLError, ValueError) as exc:
            item["status"] = "fetch_error"
            item["error"] = str(exc)
            if not args.allow_fetch_errors:
                result["sources"].append(item)
                raise
        result["sources"].append(item)

    # 可见的人工占位行：红果/抖音 等无公开网页的短剧/漫剧榜
    if args.defaults and not args.no_manual_required:
        for platform, hint, use_for in MANUAL_REQUIRED_SOURCES:
            result["sources"].append({
                "platform": platform,
                "url": hint,
                "use_for": use_for,
                "collected_at": now.isoformat(timespec="seconds"),
                "status": "manual_required",
                "title": "",
                "signals": [],
                "note": "用 --manual-evidence 填第三方榜单结论，或 --source 平台|<第三方报告URL> 抓取；空占位不计入有效证据。",
            })

    # 覆盖告警：目标平台点名了短剧/漫剧，却没有任何来源/结构化人工证据覆盖红果·抖音
    result["coverage_warnings"] = []
    tp = args.target_platform or ""
    if any(k in tp for k in SHORT_DRAMA_KEYWORDS):
        covered_by_source = any(
            any(k in s.get("platform", "") for k in SHORT_DRAMA_KEYWORDS)
            and s.get("status") == "ok" and s.get("signals")
            for s in result["sources"]
        )
        covered_by_manual = any(
            any(k in " ".join(str(ev.get(field, "")) for field in ("platform", "source", "summary"))
                for k in SHORT_DRAMA_KEYWORDS)
            and manual_evidence_fresh(
                ev, result["baseline_date"], coverage_window(result["expires_after_days"])
            )
            for ev in result["manual_evidence"]
        )
        if not covered_by_source and not covered_by_manual:
            result["coverage_warnings"].append(
                "target_platform 命中 红果/抖音/漫剧/短剧，但无任何有效来源或 --manual-evidence 覆盖这些平台；"
                "当前基准只反映 番茄/起点/晋江 等网文公榜，对主投放平台是盲区。"
                "请补 --manual-evidence '红果短剧|YYYY-MM-DD|第三方榜单|结论|URL' "
                "或 --source '红果短剧|<第三方报告URL>'。"
            )
    result["evidence_tasks"] = build_evidence_tasks(result)
    result["evidence_jobs"] = build_evidence_jobs(result)
    attach_evidence_quality(result)
    return result


def write_artifacts(result, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    date_s = result["baseline_date"]
    json_path = os.path.join(out_dir, f"market_baseline_{date_s}.json")
    md_path = os.path.join(out_dir, f"题材热榜_{date_s}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 题材热榜基准 — {date_s}\n\n")
        f.write(f"- 目标平台：{result['target_platform']}\n")
        f.write(f"- 采集时间：{result['collected_at']}\n")
        f.write(f"- 过期天数：{result['expires_after_days']}\n\n")
        for source in result["sources"]:
            f.write(f"## {source['platform']}\n\n")
            f.write(f"- URL：{source['url']}\n")
            f.write(f"- 状态：{source['status']}\n")
            if source.get("source_quality"):
                q = source["source_quality"]
                f.write(f"- 证据质量：{q['confidence']} ({q['score']})；{'; '.join(q.get('reasons') or [])}\n")
            if source.get("title"):
                f.write(f"- 页面标题：{source['title']}\n")
            if source.get("error"):
                f.write(f"- 抓取错误：{source['error']}\n")
            signals = source.get("signals") or []
            if signals:
                f.write("\n信号摘录：\n")
                for text in signals[:20]:
                    f.write(f"- {text}\n")
            f.write("\n")
        if result["notes"]:
            f.write("## 人工补充\n\n")
            for note in result["notes"]:
                f.write(f"- {note}\n")
        if result.get("manual_evidence"):
            f.write("\n## 结构化人工证据\n\n")
            for ev in result["manual_evidence"]:
                url = f" [{ev['url']}]" if ev.get("url") else ""
                q = ev.get("evidence_quality") or {}
                suffix = f"（证据质量 {q.get('confidence')} {q.get('score')}）" if q else ""
                f.write(f"- {ev['platform']}｜{ev['date']}｜{ev['source']}{url}：{ev['summary']}{suffix}\n")
        if result.get("evidence_quality"):
            q = result["evidence_quality"]
            f.write("\n## 证据质量汇总\n\n")
            f.write(f"- 置信度：{q['confidence']} ({q['score']})\n")
            f.write(f"- 有效证据数：{q['effective_evidence_count']}\n")
        if result.get("coverage_warnings"):
            f.write("\n## ⚠️ 覆盖告警\n\n")
            for w in result["coverage_warnings"]:
                f.write(f"- {w}\n")
        if result.get("evidence_tasks"):
            f.write("\n## 待补市场证据任务\n\n")
            for task in result["evidence_tasks"]:
                f.write(f"- [{task['priority']}] {task['id']} {task['title']} → {task['recommended_skill']}\n")
                f.write(f"  - 原因：{task['reason']}\n")
                for command in task.get("suggested_commands") or []:
                    f.write(f"  - 命令：`{command}`\n")
        if result.get("evidence_jobs"):
            f.write("\n## 深搜 Evidence Jobs\n\n")
            for job in result["evidence_jobs"]:
                f.write(f"- {job['id']}：{job['target_platform']}\n")
                for query in job.get("search_queries") or []:
                    f.write(f"  - 搜索：{query}\n")
    tasks_json = os.path.join(out_dir, "market_evidence_tasks.json")
    tasks_md = os.path.join(out_dir, "市场证据待补.md")
    jobs_json = os.path.join(out_dir, "market_evidence_jobs.json")
    jobs_md = os.path.join(out_dir, "市场证据深搜任务.md")
    if result.get("evidence_tasks"):
        with open(tasks_json, "w", encoding="utf-8") as f:
            json.dump({
                "schema_version": 1,
                "kind": "novel_market_evidence_tasks",
                "baseline_date": date_s,
                "target_platform": result["target_platform"],
                "tasks": result["evidence_tasks"],
            }, f, ensure_ascii=False, indent=2)
        with open(tasks_md, "w", encoding="utf-8") as f:
            f.write(f"# 市场证据待补 — {date_s}\n\n")
            for task in result["evidence_tasks"]:
                f.write(f"## {task['id']} {task['title']}\n\n")
                f.write(f"- 优先级：{task['priority']}\n")
                f.write(f"- 推荐 skill：{task['recommended_skill']}\n")
                f.write(f"- 原因：{task['reason']}\n")
                f.write("- 需要证据：\n")
                for item in task.get("required_evidence") or []:
                    f.write(f"  - {item}\n")
                f.write("- 建议命令：\n")
                for command in task.get("suggested_commands") or []:
                    f.write(f"  - `{command}`\n")
                f.write("\n")
        if result.get("evidence_jobs"):
            with open(jobs_json, "w", encoding="utf-8") as f:
                json.dump({
                    "schema_version": 1,
                    "kind": "novel_market_evidence_jobs",
                    "baseline_date": date_s,
                    "target_platform": result["target_platform"],
                    "jobs": result["evidence_jobs"],
                }, f, ensure_ascii=False, indent=2)
            with open(jobs_md, "w", encoding="utf-8") as f:
                f.write(f"# 市场证据深搜任务 — {date_s}\n\n")
                for job in result["evidence_jobs"]:
                    f.write(f"## {job['id']} {job['target_platform']}\n\n")
                    f.write("搜索问题：\n")
                    for query in job.get("search_queries") or []:
                        f.write(f"- {query}\n")
                    f.write("\n回灌格式：\n\n")
                    f.write(f"`--manual-evidence \"{job['manual_evidence_format']}\"`\n\n")
    else:
        for stale in (tasks_json, tasks_md, jobs_json, jobs_md):
            if os.path.exists(stale):
                os.remove(stale)
    return json_path, md_path


def main():
    ap = argparse.ArgumentParser(description="采集 novel-score / novel-review 共用市场基准")
    ap.add_argument("out_dir", help="通常为 <作品根>/评分")
    ap.add_argument("--target-platform", default="红果/抖音 商业爽文向")
    ap.add_argument("--date", default=datetime.now().date().isoformat())
    ap.add_argument("--expires-after-days", type=int, default=21)
    ap.add_argument("--source", action="append", default=[], help="平台|URL[|use_for]，可重复")
    ap.add_argument("--no-defaults", dest="defaults", action="store_false")
    ap.add_argument("--no-manual-required", action="store_true",
                    help="不追加 红果/抖音 等人工占位行（默认追加以暴露覆盖缺口）")
    ap.add_argument("--note", action="append", default=[], help="从浏览器/搜索人工核验到的趋势备注")
    ap.add_argument("--manual-evidence", action="append", default=[],
                    help="结构化人工证据：平台|日期YYYY-MM-DD|来源|结论[|URL]；可重复，才计入有效证据")
    ap.add_argument("--timeout", type=float, default=8.0)
    ap.add_argument("--max-signals", type=int, default=80)
    ap.add_argument("--allow-fetch-errors", action="store_true")
    args = ap.parse_args()

    try:
        result = collect(args)
    except Exception as exc:
        print(f"[err] 市场基准采集失败：{exc}", file=sys.stderr)
        sys.exit(1)
    json_path, md_path = write_artifacts(result, os.path.abspath(args.out_dir))
    print(f"[ok] market baseline JSON → {json_path}")
    print(f"[ok] market baseline MD   → {md_path}")
    for w in result.get("coverage_warnings", []):
        print(f"[warn] {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
