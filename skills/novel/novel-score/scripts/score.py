#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Automated scoring engine for novel projects.

Evaluates chapters based on market-baseline and rubric.md dimensions.
Outputs score_report.json and a human-readable Markdown report.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from glob import glob

# Add parent scripts to path for contract and common imports
HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.append(os.path.join(SKILLS_ROOT, "novel-craft", "scripts"))

_COMMON = os.path.join(SKILLS_ROOT, "_lib")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from settings import load_settings as _load_settings  # noqa: E402  vendored 进 novel/_lib
from io_utils import load_meta  # noqa: E402  本线 _lib 单一真值源
from text_utils import cjk_count  # noqa: E402
from report_snapshot import (  # noqa: E402  章号/哈希纯函数走 _lib，不再本地复制
    chapter_number_from_path,
    chapter_sort_key,
    sha256_file,
)

try:
    import novel_contract as contract
except ImportError:
    # Fallback if contract is not reachable via path
    contract = None
try:
    import semantic_job
except ImportError:  # pragma: no cover - optional orchestration helper
    semantic_job = None
try:
    from report_snapshot import snapshot_files, validate_snapshot
    from waivers import append_waiver, baseline_freshness_scope, make_waiver
except ImportError:
    append_waiver = None
    baseline_freshness_scope = None
    make_waiver = None
    snapshot_files = None
    validate_snapshot = None

try:
    from friction_log import log_friction  # noqa: E402  novel/_lib 单一真值源
except ImportError:
    log_friction = None

try:
    import judge_protocol  # noqa: E402  novel/_lib 单一真值源：LLM 判官去偏协议执行层
except ImportError:  # pragma: no cover - 缺则单判官按原行为，不做 dual-judge 去偏
    judge_protocol = None

try:
    import repetition  # noqa: E402  novel/_lib 单一真值源：跨章重复率/机械文风（与 novel-review 共用）
except ImportError:  # pragma: no cover - 缺则不算 retention 重复先验，按原行为
    repetition = None

# 跨章重复率/机械文风先验的来源标签（确定性机检·喂 retention 调分）
REPETITION_PRIOR_SOURCE = "机检/跨章重复(确定性)"

DIMENSIONS = [
    ("topic_heat", "题材热度匹配"),
    ("opening_hook", "开篇黄金三章钩子"),
    ("payoff_density", "情绪兑现与阅读动力"),
    ("character_power", "人物塑造与核心机制"),
    ("plot_structure", "剧情结构与主线张力"),
    ("prose", "文学性 / 文笔"),
    ("retention", "完读 / 留存潜力"),
    # ⑧ 新颖度/想象力（2026-07 新增）：此前创意质量只有「AI味/雷同」雷点扣分（罚下限），
    # 没有正向上限评估——系统擅长"不写崩"、不擅长"写得让人惊喜"。本维评差异化记忆点、
    # 预期违背（意外但回看合理）、非模板化桥段/结局；锚点见 rubric.md ⑧。
    ("novelty", "新颖度 / 想象力"),
]

# 书名体检（附加体检项 · 不计入百分制总分）：维度沿用 novel-title 的 5 维（各 1-5 分，满分 25）。
# 这里只「体检现有书名」并在不过关时路由 novel-title；候选生成与联网撞名查重仍归 novel-title。
TITLE_CHECK_DIMENSIONS = [
    ("hook", "钩子"),
    ("platform_fit", "平台契合"),
    ("character_identity", "角色识别"),
    ("anti_collision", "抗撞名(初判)"),
    ("memorability", "可记忆性"),
]
# 总分低于此线（满分 25）或硬撞名 → needs_rename，next_actions 路由 novel-title
TITLE_RENAME_THRESHOLD = 15

# 短剧改编潜力体检（附加体检项 · 不计入百分制总分）：5 维各 1-5 分，满分 25。
# 短剧/漫剧改编是否是当前目标平台的高优先级变现路径，必须以 `评分/market_baseline_*.json`
# 和 `资料/research_sources.json` 为准；本附检只评估「这部本身可改编度」，仅在目标平台命中
# 短剧/漫剧时强制，弱则路由 novel-condense（漫剧版）。详见 SKILL.md。
ADAPTATION_CHECK_DIMENSIONS = [
    ("visual_scene", "可视化场景密度"),
    ("hook_cinematic", "强钩可镜头化"),
    ("conflict_intensity", "人物关系冲突浓度"),
    ("episodic_beat", "单元剧式节拍"),
    ("ip_freshness", "题材/人设短剧新鲜度"),
]
# 总分低于此线（满分 25）→ low_potential，next_actions 提示先走 novel-condense 出漫剧版
ADAPTATION_LOW_THRESHOLD = 15

WEIGHTS = {
    # 未指定平台时使用完全等权的中性档，避免把传统/文学小说静默套进
    # 短视频商业爽文权重。平台明确后才切到下列专用档。
    "均衡向": {dimension: 12.5 for dimension, _label in DIMENSIONS},
    "商业爽文向": {
        "topic_heat": 18,
        "opening_hook": 16,
        "payoff_density": 16,
        "character_power": 12,
        "plot_structure": 12,
        "prose": 8,
        "retention": 10,
        "novelty": 8,
    },
    "品质向": {
        "topic_heat": 10,
        "opening_hook": 12,
        "payoff_density": 10,
        "character_power": 12,
        "plot_structure": 16,
        "prose": 16,
        "retention": 12,
        "novelty": 12,
    }
}

# 平台 → 评分模式映射：品质导向平台用品质权重（prose 16/novelty 12/topic_heat 10），
# 商业爽文平台用商业权重（topic_heat 18/prose 8/novelty 8）。未知/未定平台保持均衡向。
PLATFORM_WEIGHT_MODE = {
    "晋江": "品质向",
    "起点": "品质向",
    "起点中文网": "品质向",
    "起点国际": "品质向",
    "纵横": "品质向",
    "豆瓣阅读": "品质向",
    "番茄": "商业爽文向",
    "红果": "商业爽文向",
    "七猫": "商业爽文向",
    "抖音": "商业爽文向",
    "快手": "商业爽文向",
    "书旗": "商业爽文向",
    "飞卢": "商业爽文向",
    "掌阅": "商业爽文向",
    "鲁迅文学院": "品质向",
}


def _resolve_platform_mode(raw):
    """从平台名/设置字符串解析评分模式。

    优先级：1) 显式权重档 2) 平台映射 3) 档位关键词 4) 未定/未知→均衡向。"""
    value = str(raw or "").strip()
    if value in {"商业爽文向", "品质向", "均衡向"}:
        return value
    if not value or value in {"未定", "未知", "自定义"}:
        return "均衡向"
    # 精确匹配优先
    for key, mode in PLATFORM_WEIGHT_MODE.items():
        if key in value:
            return mode
    if "商业" in value or "爽文" in value:
        return "商业爽文向"
    if "品质" in value or "文学" in value:
        return "品质向"
    if "均衡" in value:
        return "均衡向"
    return "均衡向"


SHORT_DRAMA_KEYWORDS = ("红果", "抖音", "漫剧", "短剧")

# 短剧/漫剧「平台覆盖」证据保质期：与日榜（expires_after_days，默认 21）解耦。
# 红果/抖音漫剧无公开日榜网页，平台覆盖只能靠 MAU/题材趋势/审核新规等按月·季发布的
# 行业报告——用 21 天日榜窗口卡覆盖闸会让它「永远满足不了」，逼每次评分都 stale-waiver。
# 见 collect_market_baseline.coverage_window（两处刻意分包 fork，保持一致）。
COVERAGE_EVIDENCE_MAX_AGE_DAYS = 90


def coverage_window(expires_after):
    try:
        base = int(expires_after or 0)
    except (TypeError, ValueError):
        base = 0
    return max(base, COVERAGE_EVIDENCE_MAX_AGE_DAYS)


REFERENCE_DISTRIBUTION_GLOB = os.path.join("评分", "reference_distribution*.json")
REFERENCE_ALLOWED_RIGHTS = {
    "public-domain",
    "user-owned",
    "user-declared",
    "original",
    "authorized",
    "licensed",
}


def load_settings(root):
    """读作品根下的 _设置.md；单一真值源在 skills/novel/_lib/settings.py。"""
    return _load_settings(root)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def rel_path(root, path):
    return os.path.relpath(os.path.abspath(path), os.path.abspath(root)).replace(os.sep, "/")


def find_latest_baseline(root):
    score_dir = os.path.join(root, "评分")
    files = glob(os.path.join(score_dir, "market_baseline_*.json"))
    if not files:
        return None
    files.sort(reverse=True)
    with open(files[0], encoding="utf-8") as f:
        payload = json.load(f)
    payload["_json_path_abs"] = os.path.abspath(files[0])
    baseline_date = payload.get("baseline_date")
    if baseline_date:
        payload["_md_path_abs"] = os.path.join(score_dir, f"题材热榜_{baseline_date}.md")
    return payload


def baseline_has_effective_evidence(baseline):
    """A baseline is usable only if it contains real market evidence."""
    if not isinstance(baseline, dict):
        return False
    if any(manual_evidence_valid(item) for item in baseline.get("manual_evidence") or []):
        return True
    for source in baseline.get("sources") or []:
        if not isinstance(source, dict):
            continue
        status = str(source.get("status") or "").strip().lower()
        signals = source.get("signals") or []
        if status == "ok" and any(str(signal).strip() for signal in signals):
            return True
    return False


def manual_evidence_valid(item):
    if not isinstance(item, dict):
        return False
    required = ("platform", "date", "source", "summary")
    if any(not str(item.get(field) or "").strip() for field in required):
        return False
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(item.get("date") or "")))


def _parse_evidence_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _evidence_is_fresh(raw_date, expires_after):
    evidence_date = _parse_evidence_date(raw_date)
    if evidence_date is None:
        return False
    if evidence_date > date.today():
        return False
    return date.today() <= evidence_date + timedelta(days=expires_after)


def _source_has_effective_signals(source):
    status = str(source.get("status") or "").strip().lower()
    signals = source.get("signals") or []
    return status == "ok" and any(str(signal).strip() for signal in signals)


def _source_evidence_date(source, fallback_date=None):
    return source.get("collected_at") or fallback_date


def baseline_has_fresh_effective_evidence(baseline, expires_after):
    baseline_date = (baseline or {}).get("baseline_date")
    for item in (baseline or {}).get("manual_evidence") or []:
        if manual_evidence_valid(item) and _evidence_is_fresh(item.get("date"), expires_after):
            return True
    for source in (baseline or {}).get("sources") or []:
        if isinstance(source, dict) and _source_has_effective_signals(source):
            if _evidence_is_fresh(_source_evidence_date(source, baseline_date), expires_after):
                return True
    return False


def baseline_has_short_drama_coverage(baseline, *, require_fresh=False, expires_after=21):
    target = str((baseline or {}).get("target_platform") or "")
    if not any(key in target for key in SHORT_DRAMA_KEYWORDS):
        return True
    baseline_date = (baseline or {}).get("baseline_date")
    for source in (baseline or {}).get("sources") or []:
        if not isinstance(source, dict):
            continue
        platform = str(source.get("platform") or "")
        if any(key in platform for key in SHORT_DRAMA_KEYWORDS):
            if _source_has_effective_signals(source) and (
                not require_fresh or _evidence_is_fresh(_source_evidence_date(source, baseline_date), expires_after)
            ):
                return True
    for item in (baseline or {}).get("manual_evidence") or []:
        haystack = " ".join(str(item.get(field, "")) for field in ("platform", "source", "summary"))
        if manual_evidence_valid(item) and any(key in haystack for key in SHORT_DRAMA_KEYWORDS):
            if require_fresh and not _evidence_is_fresh(item.get("date"), expires_after):
                continue
            return True
    return False


def baseline_freshness(baseline):
    if not baseline:
        return {
            "status": "missing",
            "blocking": True,
            "reason": "缺少 market_baseline_*.json；先运行 collect_market_baseline.py。",
        }
    raw_date = baseline.get("baseline_date")
    try:
        base_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return {
            "status": "invalid",
            "blocking": True,
            "reason": f"market baseline baseline_date 无效：{raw_date!r}",
        }
    expires_after = int(baseline.get("expires_after_days") or 21)
    expires_on = base_date + timedelta(days=expires_after)
    expired = date.today() > expires_on
    md_path = baseline.get("_md_path_abs")
    md_missing = bool(md_path and not os.path.exists(md_path))
    if md_missing:
        return {
            "status": "missing_md",
            "blocking": True,
            "baseline_date": raw_date,
            "expires_after_days": expires_after,
            "expires_on": expires_on.isoformat(),
            "reason": f"market baseline 缺少人读热榜文件：{md_path}",
        }
    if expired:
        return {
            "status": "expired",
            "blocking": True,
            "baseline_date": raw_date,
            "expires_after_days": expires_after,
            "expires_on": expires_on.isoformat(),
            "reason": f"market baseline 已过期：{raw_date} + {expires_after} 天 < {date.today().isoformat()}",
        }
    if not baseline_has_effective_evidence(baseline):
        return {
            "status": "no_evidence",
            "blocking": True,
            "baseline_date": raw_date,
            "expires_after_days": expires_after,
            "expires_on": expires_on.isoformat(),
            "reason": "market baseline 没有有效证据：至少需要一个 status=ok 且 signals 非空的来源，或结构化 manual_evidence。",
        }
    if not baseline_has_fresh_effective_evidence(baseline, expires_after):
        return {
            "status": "evidence_stale",
            "blocking": True,
            "baseline_date": raw_date,
            "expires_after_days": expires_after,
            "expires_on": expires_on.isoformat(),
            "reason": "market baseline 的有效证据自身已过期或缺少证据日期；请重新抓取来源或补当天/近期 manual_evidence。",
        }
    if not baseline_has_short_drama_coverage(
        baseline, require_fresh=True, expires_after=coverage_window(expires_after)
    ):
        return {
            "status": "coverage_gap",
            "blocking": True,
            "baseline_date": raw_date,
            "expires_after_days": expires_after,
            "expires_on": expires_on.isoformat(),
            "reason": "target_platform 命中 红果/抖音/漫剧/短剧，但缺这些平台的新鲜 ok 来源或结构化 manual_evidence。",
        }
    return {
        "status": "fresh",
        "blocking": False,
        "baseline_date": raw_date,
        "expires_after_days": expires_after,
        "expires_on": expires_on.isoformat(),
        "reason": "",
    }


def baseline_file_snapshot(root, baseline):
    entries = []
    if baseline:
        for field in ("_json_path_abs", "_md_path_abs"):
            path = baseline.get(field)
            if path and os.path.exists(path):
                entries.append({
                    "path": rel_path(root, path),
                    "sha256": sha256_file(path),
                    "bytes": os.path.getsize(path),
                })
    entries.sort(key=lambda item: item["path"])
    aggregate = hashlib.sha256()
    for item in entries:
        aggregate.update(item["path"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(item["sha256"].encode("ascii"))
        aggregate.update(b"\n")
    return {
        "schema_version": 1,
        "kind": "novel_market_baseline_snapshot",
        "baseline_date": baseline.get("baseline_date") if baseline else None,
        "files": entries,
        "aggregate_hash": aggregate.hexdigest(),
    }


def find_latest_reference_distribution(root):
    files = glob(os.path.join(root, REFERENCE_DISTRIBUTION_GLOB))
    if not files:
        return None
    files.sort(reverse=True)
    try:
        with open(files[0], encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") != "novel_reference_score_distribution":
        return None
    payload["_json_path_abs"] = os.path.abspath(files[0])
    return payload


def _sample_score_map(sample):
    scores = sample.get("scores") or {}
    if isinstance(scores, dict):
        return {str(k): float(v) for k, v in scores.items() if isinstance(v, (int, float))}
    if isinstance(scores, list):
        out = {}
        for item in scores:
            if isinstance(item, dict) and item.get("dimension") and isinstance(item.get("raw_score"), (int, float)):
                out[str(item["dimension"])] = float(item["raw_score"])
        return out
    return {}


def _percentile(value, population):
    values = [float(v) for v in population if isinstance(v, (int, float))]
    if value is None or not values:
        return None
    below_or_equal = sum(1 for v in values if v <= float(value))
    return round(100.0 * below_or_equal / len(values), 1)


def compute_benchmark_percentiles(root, total_score, processed_scores, distribution):
    if not distribution:
        return None
    samples = []
    skipped = []
    for sample in distribution.get("samples") or []:
        if not isinstance(sample, dict):
            continue
        rights = str(sample.get("rights_status") or "").strip()
        if rights not in REFERENCE_ALLOWED_RIGHTS:
            skipped.append({"title": sample.get("title"), "rights_status": rights or "missing"})
            continue
        if not isinstance(sample.get("total_score"), (int, float)):
            skipped.append({"title": sample.get("title"), "reason": "missing total_score"})
            continue
        samples.append(sample)
    if not samples:
        return {
            "status": "no_eligible_samples",
            "sample_count": 0,
            "skipped_samples": skipped,
            "note": "参考分布没有合规且带分数的样本。",
        }
    dimension_scores = {item["dimension"]: item["raw_score"] for item in processed_scores}
    by_dimension = {}
    for dim, _label in DIMENSIONS:
        population = []
        for sample in samples:
            value = _sample_score_map(sample).get(dim)
            if value is not None:
                population.append(value)
        pct = _percentile(dimension_scores.get(dim), population)
        if pct is not None:
            by_dimension[dim] = {"percentile": pct, "sample_count": len(population)}
    return {
        "status": "ok",
        "distribution_title": distribution.get("title") or distribution.get("name") or "reference_distribution",
        "distribution_path": rel_path(root, distribution.get("_json_path_abs"))
        if distribution.get("_json_path_abs") else None,
        "sample_count": len(samples),
        "declared_sample_count": distribution.get("sample_count"),
        "skipped_samples": skipped,
        "total_score_percentile": _percentile(total_score, [s.get("total_score") for s in samples]),
        "by_dimension": by_dimension,
        "rights_policy": "仅纳入 public-domain / user-owned / user-declared / original / authorized / licensed 参考样本。",
    }


def make_score_task_id(source_snapshot, baseline_snapshot, scope, platform_mode):
    payload = {
        "source": (source_snapshot or {}).get("aggregate_hash"),
        "baseline": (baseline_snapshot or {}).get("aggregate_hash"),
        "scope": scope,
        "platform_mode": platform_mode,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def score_task_path(root, explicit=None):
    return os.path.abspath(explicit or os.path.join(root, "评分", "score_task.json"))


def write_score_task(root, task_path, task):
    os.makedirs(os.path.dirname(task_path), exist_ok=True)
    with open(task_path, "w", encoding="utf-8") as f:
        json.dump(task, f, ensure_ascii=False, indent=2)


def build_score_task(root, *, scope, platform_mode, source_snapshot, baseline_snapshot,
                     freshness, first_party, prompt):
    task_id = make_score_task_id(source_snapshot, baseline_snapshot, scope, platform_mode)
    prompt = prompt.replace("__SCORE_TASK_ID__", task_id)
    return {
        "schema_version": 1,
        "kind": "novel_score_task",
        "score_task_id": task_id,
        "project_root": os.path.abspath(root),
        "generated_at": date.today().isoformat(),
        "target_platform": platform_mode,
        "scope": {"mode": scope, "chapter_count": len((source_snapshot or {}).get("files") or [])},
        "source_snapshot": source_snapshot,
        "market_baseline_snapshot": baseline_snapshot,
        "market_baseline_freshness": freshness,
        "first_party_genre": first_party,
        "assessment_prompt_hash": sha256_text(prompt),
        "assessment_prompt": prompt,
    }


def validate_score_task(root, task, *, scope, platform_mode, baseline_snapshot, expected_prompt_hash=None):
    if not isinstance(task, dict):
        return False, "score_task 不是 JSON object。"
    if task.get("kind") != "novel_score_task":
        return False, "score_task.kind 不是 novel_score_task。"
    if (task.get("scope") or {}).get("mode") != scope:
        return False, f"score_task scope={(task.get('scope') or {}).get('mode')!r} 与本次 --scope={scope!r} 不一致。"
    if task.get("target_platform") != platform_mode:
        return False, f"score_task target_platform={task.get('target_platform')!r} 与本次评分档={platform_mode!r} 不一致。"
    if validate_snapshot:
        ok, msg = validate_snapshot(root, task.get("source_snapshot"))
        if not ok:
            return False, f"score_task 正文快照过期：{msg}"
    task_baseline = task.get("market_baseline_snapshot") or {}
    if task_baseline.get("aggregate_hash") != baseline_snapshot.get("aggregate_hash"):
        return False, "score_task 绑定的 market baseline 文件已变化；需重新生成 score_task。"
    if expected_prompt_hash and task.get("assessment_prompt_hash") != expected_prompt_hash:
        return False, "score_task 绑定的评分 prompt 模板或内容已变化；需重新生成 score_task。"
    return True, "score_task fresh"


def make_freshness_waiver(freshness):
    waiver_scope = (
        baseline_freshness_scope(freshness)
        if baseline_freshness_scope else {
            "baseline_date": str(freshness.get("baseline_date") or ""),
            "freshness_status": str(freshness.get("status") or ""),
        }
    )
    if make_waiver:
        waiver = make_waiver(
            "score_baseline_freshness",
            reason="explicit --allow-stale-baseline during scoring",
            affected_gate="market_baseline",
            source="novel-score/scripts/score.py",
            details={"freshness": freshness},
            scope=waiver_scope,
        )
    else:
        waiver = {
            "id": f"WAIVER-SCORE-BASELINE-{date.today().isoformat()}",
            "type": "score_baseline_freshness",
            "created_at": date.today().isoformat(),
            "reason": "explicit --allow-stale-baseline during scoring",
            "affected_gate": "market_baseline",
            "source": "novel-score/scripts/score.py",
            "details": {"freshness": freshness},
            "scope": waiver_scope,
        }
    waiver["risk"] = "本次评分使用缺失、过期或无有效证据的市场基准；topic_heat 和平台判断只能作为人工豁免结果。"
    return waiver


# ── 选题→投放→反哺选题闭环：读「自有题材战绩库」做第一方题材热度先验 ──
LEDGER_REL_PATH = os.path.join("生产战绩", "genre_ledger.jsonl")


def _find_repo_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, "skills")) or os.path.isfile(os.path.join(cur, "AGENTS.md")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def default_ledger_path(root):
    return os.environ.get("NOVEL_GENRE_LEDGER") or os.path.join(_find_repo_root(root), LEDGER_REL_PATH)


def load_genre_ledger(path):
    records = []
    if not path or not os.path.isfile(path):
        return records
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec, dict) and rec.get("kind") == "genre_performance_record":
                records.append(rec)
    return records


def _norm_genre(value):
    return str(value or "").strip().lower()


def summarize_first_party_genre(records, genre, platform_mode=None):
    """按题材聚合自有投放战绩（按播放量加权）→ 第一方题材热度先验。"""
    if not records:
        return None
    target = _norm_genre(genre)
    matched = [r for r in records if target and _norm_genre(r.get("genre")) == target] if target else []
    used_genre = genre
    if not matched:
        # 题材未命中（或本书没填题材）：退回全库聚合，仅作整体水位参考。
        matched = records
        used_genre = "（全库·未匹配本书题材）"
    metric_keys = ("retention_3s", "retention_15s", "completion_rate", "follow_next_rate", "roi")
    agg = {}
    for key in metric_keys:
        num = 0.0
        wt = 0.0
        for r in matched:
            m = (r.get("metrics") or {})
            v = m.get(key)
            plays = m.get("plays") or 1
            if isinstance(v, (int, float)):
                num += float(v) * float(plays)
                wt += float(plays)
        if wt:
            agg[key] = round(num / wt, 4)
    total_plays = int(sum((r.get("metrics") or {}).get("plays") or 0 for r in matched))
    return {
        "genre": used_genre,
        "release_count": len(matched),
        "total_plays": total_plays,
        "metrics": agg,
        "subgenres": sorted({sg for r in matched for sg in (r.get("subgenres") or [])}),
    }


def first_party_genre_text(summary):
    if not summary:
        return "无（尚无自有投放战绩库；由外部投放侧回灌 生产战绩/genre_ledger.jsonl 后此处显示第一方题材热度）"
    m = summary["metrics"]
    def pct(k):
        return f"{m[k]*100:.1f}%" if k in m and m[k] is not None else "—"
    roi = f"{m['roi']:.2f}" if "roi" in m else "—"
    sub = ("；高频套路：" + "、".join(summary["subgenres"])) if summary.get("subgenres") else ""
    return (
        f"题材「{summary['genre']}」自有战绩（{summary['release_count']} 部 / {summary['total_plays']} 播放，按播放量加权）："
        f"3秒留存 {pct('retention_3s')}、15秒留存 {pct('retention_15s')}、完播 {pct('completion_rate')}、"
        f"追更 {pct('follow_next_rate')}、ROI {roi}{sub}。"
        "（第一方实测，权重高于公榜热度：本题材自有 ROI/留存若明显低于平台基准，topic_heat 应下调并提示选题代差。）"
    )


READER_PANEL_REL_PATH = os.path.join("评分", "reader_panel_signals.json")
READER_TELEMETRY_REL_PATH = os.path.join("评分", "reader_telemetry_summary.json")
AB_TAKE_RESULTS_REL_PATH = os.path.join("评分", "ab_take_results.json")


def load_reader_panel_signals(root):
    """读 novel-simulate 产的 评分/reader_panel_signals.json（合成叙事探针）。

    缺文件正常退化为 None。retention_prior 是 schema v1 兼容字段，语义仅为 retention_proxy；
    该文件不得作为真实读者证据或进入自动数值调分。
    """
    path = os.path.join(root, READER_PANEL_REL_PATH)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or "retention_prior" not in data:
        return None
    return data


def load_reader_telemetry_summary(root):
    """读 novel-feedback 产的真实读者反馈摘要。"""
    path = os.path.join(root, READER_TELEMETRY_REL_PATH)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("kind") != "novel_reader_telemetry_summary":
        return None
    return data


def load_ab_take_results(root):
    path = os.path.join(root, AB_TAKE_RESULTS_REL_PATH)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, (dict, list)) else None


def _num(value, default=None):
    if isinstance(value, (int, float)):
        return float(value)
    try:
        if value not in (None, ""):
            return float(value)
    except (TypeError, ValueError):
        pass
    return default


def summarize_ab_take_results(results):
    if not results:
        return None
    payload = results[-1] if isinstance(results, list) and results else results
    if not isinstance(payload, dict):
        return None
    uplift = _num(
        payload.get("completion_uplift")
        or payload.get("uplift_completion_rate")
        or payload.get("winner_uplift")
        or payload.get("uplift")
    )
    return {
        "kind": payload.get("kind") or "novel_ab_take_results",
        "winner": payload.get("winner") or payload.get("winning_variant") or "",
        "metric": payload.get("metric") or payload.get("primary_metric") or "completion_rate",
        "uplift": uplift,
        "confidence": payload.get("confidence") or payload.get("significance") or "",
        "sample_size": payload.get("sample_size") or payload.get("n") or "",
    }


def compute_reader_feedback_adjustment(reader_telemetry=None, reader_panel=None, ab_take_results=None,
                                       repetition_prior=None):
    components = []
    reasons = []
    sources = []
    context_only = []

    def add(points, reason, source):
        if not points:
            return
        components.append({"points": points, "reason": reason, "source": source})
        reasons.append(reason)
        if source not in sources:
            sources.append(source)

    if reader_telemetry:
        agg = reader_telemetry.get("aggregate") or {}
        completion = _num(agg.get("completion_rate"))
        drop = _num(agg.get("drop_rate"))
        if completion is not None:
            if completion >= 0.75:
                add(4, f"真实完读率 {completion:.2f} 高于强留存线", READER_TELEMETRY_REL_PATH)
            elif completion >= 0.60:
                add(2, f"真实完读率 {completion:.2f} 达到可放量线", READER_TELEMETRY_REL_PATH)
            elif completion <= 0.35:
                add(-5, f"真实完读率 {completion:.2f} 低于硬伤线", READER_TELEMETRY_REL_PATH)
            elif completion <= 0.50:
                add(-3, f"真实完读率 {completion:.2f} 偏低", READER_TELEMETRY_REL_PATH)
        if drop is not None:
            if drop >= 0.45:
                add(-4, f"真实弃读率 {drop:.2f} 过高", READER_TELEMETRY_REL_PATH)
            elif drop <= 0.15:
                add(2, f"真实弃读率 {drop:.2f} 较低", READER_TELEMETRY_REL_PATH)

    if reader_panel:
        context_only.append({
            "source": READER_PANEL_REL_PATH,
            "reason": "合成叙事探针只提出人工复核假设，不代表真实读者或统计留存，不参与数值调分",
        })

    ab_summary = summarize_ab_take_results(ab_take_results)
    if ab_summary:
        context_only.append({
            "source": AB_TAKE_RESULTS_REL_PATH,
            "reason": "A/B 摘要缺少统一实验设计与统计有效性协议，仅展示结果，不按裸 uplift 自动调分",
        })

    # 跨章重复率/机械文风先验（确定性机检）：retention 维度负向先验，prior 自身已封顶 -3。
    if repetition_prior:
        prior = repetition_prior.get("prior") or {}
        pts = float(prior.get("points") or 0)
        if pts:
            reason_bits = prior.get("reasons") or []
            add(pts, "跨章重复机检先验：" + "；".join(reason_bits[:3]), REPETITION_PRIOR_SOURCE)

    raw_points = sum(float(item["points"]) for item in components)
    capped = max(-8.0, min(8.0, raw_points))
    return {
        "points": capped,
        "raw_points": raw_points,
        "cap": 8,
        "sources": sources,
        "reasons": reasons,
        "components": components,
        "context_only": context_only,
        "ab_take_results_summary": ab_summary,
    }


def reader_telemetry_text(summary):
    if not summary:
        return ("无（尚无真实读者反馈回灌；可用 novel-feedback 导入平台后台 CSV/JSONL，"
                "真实经验数据与合成叙事探针必须分栏呈现）")
    agg = summary.get("aggregate") or {}
    weakest = summary.get("weakest_chapters") or []
    chapter_bits = []
    by_chapter = {
        item.get("chapter"): item
        for item in summary.get("chapters") or []
        if isinstance(item, dict)
    }
    for ch in weakest[:5]:
        item = by_chapter.get(ch) or {}
        chapter_bits.append(
            f"第{int(ch):02d}章 完读{item.get('completion_rate')} 弃读{item.get('drop_rate')} "
            f"flags={','.join(item.get('flags') or [])}"
        )
    weak_text = "；".join(chapter_bits) if chapter_bits else "无明显章节级掉点"
    return (
        f"真实读者反馈（novel-feedback，平台 {summary.get('platform')}，来源 {summary.get('latest_source_name')}）："
        f"记录 {summary.get('records_ingested')} 条，总开读 {agg.get('total_starts')}，"
        f"总完读率 {agg.get('completion_rate')}，总弃读率 {agg.get('drop_rate')}，"
        f"评论 {agg.get('total_comments')} 条；优先复核：{weak_text}。"
        "（真实读者反馈属于经验数据；novel-simulate 属于 synthetic/context-only 假设。"
        "两者冲突时不得用合成输出覆盖真实数据。）"
    )


def reference_distribution_text(distribution):
    if not distribution:
        return ("无（尚无合规参考分布；可用自有/授权/公版作品的 score_report 构建 "
                "评分/reference_distribution*.json，用于输出人类/参考样本百分位）")
    eligible = 0
    skipped = 0
    for sample in distribution.get("samples") or []:
        if not isinstance(sample, dict):
            continue
        rights = str(sample.get("rights_status") or "").strip()
        if rights in REFERENCE_ALLOWED_RIGHTS and isinstance(sample.get("total_score"), (int, float)):
            eligible += 1
        else:
            skipped += 1
    return (
        f"参考分布「{distribution.get('title') or distribution.get('name') or 'reference_distribution'}」："
        f"声明样本 {distribution.get('sample_count') or len(distribution.get('samples') or [])}，"
        f"合规可用样本 {eligible}，跳过 {skipped}。"
        "评分时只把它作为相对水位参照；不得纳入无授权/未知权利样本。"
    )


def reader_panel_text(signals):
    if not signals:
        return ("无（尚无合成叙事探针；可跑 novel-simulate 产 评分/reader_panel_signals.json，"
                "仅用于提出人工复核假设）")
    rp = signals.get("retention_proxy", signals.get("retention_prior"))
    hook = signals.get("hook_strength")
    cliche = signals.get("cliche_density_per_kchar")
    chs = signals.get("chapters_read") or signals.get("scope") or "?"
    mode = "signal-only" if signals.get("signal_only", True) else "qualitative-completed"
    qualitative = "已补全定性反馈" if signals.get("qualitative_completed") else "未补全定性反馈"
    return (
        f"合成叙事探针（novel-simulate，范围 {chs}，{mode}，{qualitative}）："
        f"retention_proxy {rp}、钩子标记代理 {hook}、套路关键词密度 {cliche}/千字。"
        "（这是未经外部验证的表面代理，只能提出复核问题；不得当作真实读者、真实留存或统计证据，"
        "不得自动上调/下调分数。即使补完人格心声，证据类型仍为 synthetic/context-only。）"
    )


def ab_take_results_text(results):
    summary = summarize_ab_take_results(results)
    if not summary:
        return "无（尚无 A/B take 或小流量分流结果；可由 novel-feedback 回灌 评分/ab_take_results.json）"
    uplift = summary.get("uplift")
    uplift_s = "—" if uplift is None else f"{float(uplift):.3f}"
    return (
        f"A/B take 结果：winner={summary.get('winner') or '未定'}，metric={summary.get('metric')}，"
        f"uplift={uplift_s}，confidence={summary.get('confidence') or '未填'}，"
        f"sample_size={summary.get('sample_size') or '未填'}。"
        "（裸 uplift 不足以证明因果或统计有效性；仅展示上下文，不自动调分。需另行复核随机分流、"
        "样本量、置信区间/显著性、主指标预注册和停止规则。）"
    )


def project_title(meta):
    title = str(meta.get("title") or "").strip()
    return title if title and title != "未定" else None


def load_title_collision(root, title):
    """读 novel-title 落的 设定/书名撞名检查_*.json，取最新一份里当前书名的查重结论。

    缺文件/书名未命中候选 → None（抗撞名只能凭 LLM 初判，unchecked ≠ 不撞名）。
    """
    if not title:
        return None
    files = sorted(glob(os.path.join(root, "设定", "书名撞名检查_*.json")))
    if not files:
        return None
    path = files[-1]
    try:
        with open(path, encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("kind") != "novel_title_collision_check":
        return None
    for cand in payload.get("candidates") or []:
        if isinstance(cand, dict) and str(cand.get("candidate") or "").strip() == title:
            return {
                "status": cand.get("status"),
                "path": rel_path(root, path),
                "generated_at": payload.get("generated_at"),
            }
    return None


def title_collision_text(collision):
    if not collision:
        return ("尚无联网撞名检查记录（设定/书名撞名检查_*.json 未命中当前书名）；"
                "anti_collision 只能凭常见度初判，真正查重由 novel-title 联网做。")
    return (f"已有撞名检查（{collision.get('generated_at')}，{collision.get('path')}）："
            f"status={collision.get('status')}。hard_collision 必须换名；unchecked ≠ 不撞名。")


def build_title_check(assessment_title_check, title, collision):
    """汇总报告里的书名体检块；总分低于阈值或硬撞名 → needs_rename。"""
    if not assessment_title_check or not title:
        return None
    scores = assessment_title_check.get("scores") or {}
    total = sum(float(scores.get(key) or 0) for key, _ in TITLE_CHECK_DIMENSIONS)
    needs_rename = bool(assessment_title_check.get("needs_rename")) or total < TITLE_RENAME_THRESHOLD
    if collision and collision.get("status") == "hard_collision":
        needs_rename = True
    return {
        "title": title,
        "scores": scores,
        "total": total,
        "max_total": 5 * len(TITLE_CHECK_DIMENSIONS),
        "comment": str(assessment_title_check.get("comment") or ""),
        "collision": collision or {"status": "unchecked", "path": None, "generated_at": None},
        "needs_rename": needs_rename,
    }


def is_short_drama_target(settings, meta):
    """目标平台/用途是否命中短剧/漫剧（决定是否强制短剧改编潜力附检）。"""
    hay = " ".join(str(x or "") for x in (
        (settings or {}).get("目标平台"), (settings or {}).get("小说用途"),
        (meta or {}).get("target_platform"), (meta or {}).get("purpose"), (meta or {}).get("scale"),
    ))
    return any(key in hay for key in SHORT_DRAMA_KEYWORDS)


def build_adaptation_check(assessment_adaptation):
    """汇总报告里的短剧改编潜力体检块；总分低于阈值 → low_potential（附加项·不计总分）。"""
    if not assessment_adaptation:
        return None
    scores = assessment_adaptation.get("scores") or {}
    total = sum(float(scores.get(key) or 0) for key, _ in ADAPTATION_CHECK_DIMENSIONS)
    low_potential = bool(assessment_adaptation.get("low_potential")) or total < ADAPTATION_LOW_THRESHOLD
    return {
        "scores": scores,
        "total": total,
        "max_total": 5 * len(ADAPTATION_CHECK_DIMENSIONS),
        "comment": str(assessment_adaptation.get("comment") or ""),
        "low_potential": low_potential,
    }


ACTION_BY_DIMENSION = {
    "topic_heat": ("novel-create", "setup", "重做题材/平台定位，参考第一方战绩和公榜基准"),
    "opening_hook": ("novel-craft", "outline", "重修黄金三章钩子与首屏卖点"),
    "payoff_density": ("novel-craft", "outline", "提高每 3-5 章爽点/承诺兑现密度"),
    "character_power": ("novel-rewrite", "direction_spec", "重修主角人设、金手指边界和代价"),
    "plot_structure": ("novel-rewrite", "outline", "重构主线张力、反转点和中段压力线"),
    "prose": ("novel-review", "draft", "回到章节层做文风与表达修订"),
    "retention": ("novel-craft", "outline", "重排章末钩子、悬念间隔和完读节奏"),
}

MINOR_ACTION_BY_DIMENSION = {
    "topic_heat": ("novel-promote", "positioning", "强化差异化卖点和投流标题，不重开题材"),
    "opening_hook": ("novel-craft", "opening", "微调首章前 800 字钩子和首屏文案"),
    "payoff_density": ("novel-craft", "outline", "补强低密度段落的承诺兑现点"),
    "character_power": ("novel-wiki", "power_system", "复核金手指边界、代价和升级台账"),
    "plot_structure": ("novel-review", "outline", "压缩支线并标出 12-24 集漫剧版主节点"),
    "prose": ("novel-review", "draft", "做章节级表达打磨，减少解释性旁白"),
    "retention": ("novel-review", "retention", "抽查章末钩子与中后段掉速风险"),
}


def validate_assessment(assessment, expect_title_check=False, expect_adaptation=False):
    errors = []
    if not isinstance(assessment, dict):
        return ["assessment 必须是 JSON object"]
    scores = assessment.get("scores")
    if not isinstance(scores, list):
        errors.append("scores 必须是 list")
        scores = []
    expected = {key for key, _ in DIMENSIONS}
    seen = []
    for idx, item in enumerate(scores):
        if not isinstance(item, dict):
            errors.append(f"scores[{idx}] 必须是 object")
            continue
        dim = item.get("dimension")
        seen.append(dim)
        if dim not in expected:
            errors.append(f"scores[{idx}].dimension 未知：{dim!r}")
        raw = item.get("raw_score")
        if not isinstance(raw, (int, float)) or not (1 <= float(raw) <= 10):
            errors.append(f"scores[{idx}].raw_score 必须是 1-10 数字：{raw!r}")
        for field in ("evidence", "comment", "improve_by"):
            if not str(item.get(field) or "").strip():
                errors.append(f"scores[{idx}].{field} 不能为空")
    missing = sorted(expected - set(seen))
    if missing:
        errors.append(f"缺少评分维度：{', '.join(missing)}")
    duplicates = sorted({d for d in seen if d and seen.count(d) > 1})
    if duplicates:
        errors.append(f"重复评分维度：{', '.join(duplicates)}")
    if "deductions" not in assessment:
        errors.append("缺少 deductions 字段")
    deductions = assessment.get("deductions", [])
    if not isinstance(deductions, list):
        errors.append("deductions 必须是 list")
    else:
        for idx, item in enumerate(deductions):
            if not isinstance(item, dict):
                errors.append(f"deductions[{idx}] 必须是 object")
                continue
            points = item.get("points")
            if not isinstance(points, (int, float)):
                errors.append(f"deductions[{idx}].points 必须是数字：{points!r}")
            elif points > 0:
                errors.append(f"deductions[{idx}].points 必须小于等于 0：{points!r}")
    title_check = assessment.get("title_check")
    if expect_title_check and title_check is None:
        errors.append("缺少 title_check（项目已有书名，必须做书名体检；书名未定时才可省略）")
    if title_check is not None:
        if not isinstance(title_check, dict):
            errors.append("title_check 必须是 object")
        else:
            tc_scores = title_check.get("scores")
            if not isinstance(tc_scores, dict):
                errors.append("title_check.scores 必须是 object")
                tc_scores = {}
            expected_tc = {key for key, _ in TITLE_CHECK_DIMENSIONS}
            for key in sorted(expected_tc - set(tc_scores)):
                errors.append(f"title_check.scores 缺少维度：{key}")
            for key in sorted(set(tc_scores) - expected_tc):
                errors.append(f"title_check.scores 未知维度：{key}")
            for key in expected_tc & set(tc_scores):
                value = tc_scores[key]
                if not isinstance(value, (int, float)) or not (1 <= float(value) <= 5):
                    errors.append(f"title_check.scores.{key} 必须是 1-5 数字：{value!r}")
            if not str(title_check.get("comment") or "").strip():
                errors.append("title_check.comment 不能为空")
            if not isinstance(title_check.get("needs_rename"), bool):
                errors.append("title_check.needs_rename 必须是 bool")
    adaptation = assessment.get("adaptation_check")
    if expect_adaptation and adaptation is None:
        errors.append("缺少 adaptation_check（目标平台命中短剧/漫剧，必须做短剧改编潜力体检）")
    if adaptation is not None:
        if not isinstance(adaptation, dict):
            errors.append("adaptation_check 必须是 object")
        else:
            ad_scores = adaptation.get("scores")
            if not isinstance(ad_scores, dict):
                errors.append("adaptation_check.scores 必须是 object")
                ad_scores = {}
            expected_ad = {key for key, _ in ADAPTATION_CHECK_DIMENSIONS}
            for key in sorted(expected_ad - set(ad_scores)):
                errors.append(f"adaptation_check.scores 缺少维度：{key}")
            for key in sorted(set(ad_scores) - expected_ad):
                errors.append(f"adaptation_check.scores 未知维度：{key}")
            for key in expected_ad & set(ad_scores):
                value = ad_scores[key]
                if not isinstance(value, (int, float)) or not (1 <= float(value) <= 5):
                    errors.append(f"adaptation_check.scores.{key} 必须是 1-5 数字：{value!r}")
            if not str(adaptation.get("comment") or "").strip():
                errors.append("adaptation_check.comment 不能为空")
            if not isinstance(adaptation.get("low_potential"), bool):
                errors.append("adaptation_check.low_potential 必须是 bool")
    # 可选 dual-judge 面板：{判官: {维度: 1-10}}。给了就校验形状（≥2 判官触发去偏）；
    # 不给 → 单判官按原行为，向后兼容。
    panel = assessment.get("judges_panel")
    if panel is not None:
        if not isinstance(panel, dict):
            errors.append("judges_panel 必须是 object：{判官名: {维度: 1-10}}")
        else:
            for judge, scores in panel.items():
                if not isinstance(scores, dict):
                    errors.append(f"judges_panel[{judge!r}] 必须是 object：{{维度: 1-10}}")
                    continue
                for dim, val in scores.items():
                    if dim not in expected:
                        errors.append(f"judges_panel[{judge!r}].{dim} 未知维度")
                    if not isinstance(val, (int, float)) or not (1 <= float(val) <= 10):
                        errors.append(f"judges_panel[{judge!r}].{dim} 必须是 1-10 数字：{val!r}")
    judge_families = assessment.get("judge_families")
    if judge_families is not None and not isinstance(judge_families, dict):
        errors.append("judge_families 必须是 object：{判官名: 模型家族}")
    return errors


def apply_judge_debias(assessment, processed_scores):
    """跑 judge_protocol 去偏协议（rubric z 归一 + 判官间方差→低信心），结果 advisory 注入。

    单判官（无 judges_panel 或 <2 判官）→ enabled=False，不改任何分（向后兼容）。
    多判官 → 逐维度算 mean/stdev/confidence，给 processed_scores 标 judge_confidence。
    <2 个模型家族只叫 persona_panel，整体 low confidence；≥2 家族才算 judge_panel。
    推荐 ≥3 不同模型家族；≥2 仍向后兼容。高方差维度进入 abstain_dimensions/escalation_actions。
    **绝不改 raw_score / 总分 / 判定**——
    与 judge_protocol「绝不当确定性门控」一致，只暴露判官分歧供人判（B10）。"""
    panel = (assessment or {}).get("judges_panel") or {}
    judges = [j for j, s in panel.items() if isinstance(s, dict) and s]
    if judge_protocol is None or len(judges) < 2:
        reason = ("judge_protocol 不可用" if judge_protocol is None
                  else "单判官——提供 ≥2 判官且 ≥2 模型家族的 judges_panel 才触发跨模型 judge panel")
        return {"enabled": False, "judges": judges, "low_confidence_dimensions": [],
                "abstain_dimensions": [], "escalation_actions": [],
                "method": "unavailable" if judge_protocol is None else "single_judge",
                "confidence": "none", "note": reason}
    rubric = judge_protocol.aggregate_rubric(panel)
    diversity = judge_protocol.family_diversity(judges, judge_families=(assessment or {}).get("judge_families"))
    escalations = judge_protocol.rubric_escalation_actions(rubric)
    dim_map = dict(DIMENSIONS)
    same_family_panel = int(diversity.get("families_count") or 0) < 2
    method = "persona_panel" if same_family_panel else "judge_panel"
    low_dims = []
    abstain_dims = []
    by_dim = {}
    for dim, stats in rubric.items():
        by_dim[dim] = stats
        if same_family_panel:
            decision = "abstain" if stats.get("confidence") == "low" else "review"
            item = {"dimension": dim, "dimension_label": dim_map.get(dim, dim),
                    "stdev": stats.get("stdev"), "n": stats.get("n"),
                    "decision": decision, "reason": "same_model_family"}
            low_dims.append(item)
            if decision == "abstain":
                abstain_dims.append(item)
        elif stats.get("confidence") == "low":
            item = {"dimension": dim, "dimension_label": dim_map.get(dim, dim),
                    "stdev": stats.get("stdev"), "n": stats.get("n"),
                    "decision": "abstain", "reason": "high_variance"}
            low_dims.append(item)
            abstain_dims.append(item)
    for ps in processed_scores:
        stats = by_dim.get(ps["dimension"])
        if stats:
            ps["judge_confidence"] = "low" if same_family_panel else stats.get("confidence")
            ps["judge_panel_stdev"] = stats.get("stdev")
            ps["judge_panel_n"] = stats.get("n")
            if same_family_panel:
                ps["judge_decision"] = "review"
                if stats.get("confidence") == "low":
                    ps["judge_decision"] = "abstain"
            elif stats.get("confidence") == "low":
                ps["judge_decision"] = "abstain"
    if same_family_panel:
        note = "persona_panel 已执行：判官都来自同一模型家族，整体 low confidence；只作低信心参考，不按跨模型评审采信"
        confidence = "low"
    elif low_dims:
        note = "判官高方差维度已标记为弃权/升级；不改分，但该维度结论需人审或更强跨家族判官"
        confidence = "medium"
    elif not diversity.get("meets_recommended"):
        note = "跨模型 judge panel 已执行；未满 ≥3 不同模型家族推荐标准，结论可用但建议关键稿加第三家族复核"
        confidence = "medium"
    else:
        note = "≥3 不同模型家族判官去偏已执行；判官共识良好"
        confidence = "high"
    return {
        "enabled": True,
        "method": method,
        "confidence": confidence,
        "judges": judges,
        "judges_count": len(judges),
        "family_diversity": diversity,
        "rubric": rubric,
        "low_confidence_dimensions": low_dims,
        "abstain_dimensions": abstain_dims,
        "escalation_actions": [
            {
                "dimension": item["criterion"],
                "dimension_label": dim_map.get(item["criterion"], item["criterion"]),
                "decision": item["decision"],
                "action": "人工复核该维度，或换 ≥3 个不同模型家族/更强判官重评",
                "reason": item["reason"],
            }
            for item in escalations
        ],
        "note": note,
    }


def build_next_actions(verdict, processed_scores):
    if verdict == "弃稿重立":
        return [{
            "priority": "should",
            "recommended_skill": "novel-create",
            "return_to_stage": "setup",
            "action": "核心创意保留，更换题材或主线重开",
        }]

    weak_sorted = sorted(processed_scores, key=lambda s: (s["raw_score"], -s["weight"]))
    threshold = 7.5 if verdict == "大改" else (8.0 if verdict == "小改" else 7.0)
    actions = []
    for score_item in weak_sorted:
        if score_item["raw_score"] > threshold:
            continue
        action_map = MINOR_ACTION_BY_DIMENSION if verdict == "小改" else ACTION_BY_DIMENSION
        skill, stage, action = action_map.get(score_item["dimension"],
                                              ("novel-review", "review", "按低分维度做专项修订"))
        actions.append({
            "priority": "must" if verdict == "大改" else ("should" if verdict == "小改" else "could"),
            "recommended_skill": skill,
            "return_to_stage": stage,
            "action": action,
            "dimension": score_item["dimension"],
        })
        if len(actions) >= 3:
            break

    if actions:
        return actions
    if verdict == "大改":
        return [{
            "priority": "must",
            "recommended_skill": "novel-rewrite",
            "return_to_stage": "direction_spec",
            "action": "重构主线结构或调整核心人设",
        }]
    return [{
        "priority": "could",
        "recommended_skill": "novel-review",
        "return_to_stage": "review",
        "action": "细节质检",
    }]


def build_production_decision(verdict, total_score, meta, settings):
    if verdict == "弃稿重立":
        decision = "kill"
        route = "novel-create"
        reason = "当前样本与量规提示题材/主线或市场匹配度偏低，建议由作者复核是否重立"
    elif verdict == "大改":
        decision = "revise"
        route = "novel-rewrite"
        reason = "当前样本提示结构级问题，建议批量生产前先复核或修订"
    elif verdict == "小改":
        decision = "revise"
        route = "novel-review"
        reason = "具备潜力，建议按低分维度小修"
    else:
        decision = "go"
        route = "novel-review"
        reason = "评分样本达到当前量规档位，可进入后续质检/导出复核"
    return {
        "decision": decision,
        "route": route,
        "reason": reason,
        "score": round(float(total_score), 1),
        "verdict": verdict,
        "authority": "advisory",
        "requires_human_confirmation": decision in {"revise", "kill"},
        "note": "LLM/量规分数是低置信决策辅助，不得单独阻断写作、导出或发布。",
    }


def get_tier_verdict(total_score):
    if total_score >= 85:
        return "爆款潜力", "过", "high"
    elif total_score >= 70:
        return "合格偏上", "小改", "high"
    elif total_score >= 55:
        return "及格线下", "大改", "medium"
    else:
        return "不及格", "弃稿重立", "low"


def repetition_prior_text(repetition_prior):
    """把跨章重复率机检先验折成给判官的 retention 维度提示文本（确定性·只读机检 summary）。"""
    if not repetition_prior:
        return ("无（章节不足 2 章或机检不可用；retention 维度按内容自行判读）")
    summary = repetition_prior.get("summary") or {}
    prior = repetition_prior.get("prior") or {}
    jmax = float(summary.get("adjacent_max_jaccard") or 0.0)
    cr = summary.get("compression_ratio")
    cr_txt = f"{float(cr):.0%}" if isinstance(cr, (int, float)) else "n/a"
    bits = (prior.get("reasons") or [])
    detail = "；".join(bits) if bits else "未见显著跨章重复/机械文风"
    return (
        f"跨章重复率/机械文风（确定性机检·internal-heuristic 非平台公开硬数字）：相邻章最高近重复 "
        f"{jmax:.0%}，机械开篇组 {summary.get('mechanical_opener_groups', 0)}，跨章复用整句 "
        f"{summary.get('repeated_sentences', 0)}，机械句式模板 {summary.get('sentence_opener_templates', 0)}，"
        f"句首词高频 {summary.get('sentence_start_token_groups', 0)}，短句式模板 "
        f"{summary.get('short_sentence_templates', 0)}，全书压缩比 {cr_txt}，低压缩章节 "
        f"{summary.get('low_chapter_compression_count', 0)}；先验档 {prior.get('level', 'none')}。{detail}。"
        "平台对 AI 内容做连续章节重复率/机械文风质检，高重复是弃读信号——retention 维度评分请把此"
        "作为**负向先验**纳入（机检只给信号，最终分仍以你对正文的判读为准）。"
    )


_PRESENTATION_MARKDOWN_RE = re.compile(r"^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)、]\s|>\s|```|\|)")


def presentation_bias_advisory(samples):
    """长度/格式偏好事后提示。只出 advisory，不改 raw_score/total_score。"""
    samples = samples or []
    if not samples:
        return {
            "enabled": False,
            "level": "none",
            "score_adjustment": 0,
            "raw_score_adjustment": 0,
            "reasons": [],
            "stats": {},
            "note": "无样本，未计算长度/格式中立性提示",
        }
    char_counts = [cjk_count(s.get("content") or "") for s in samples]
    nonempty_lines = 0
    md_lines = 0
    for s in samples:
        for line in (s.get("content") or "").splitlines():
            if not line.strip():
                continue
            nonempty_lines += 1
            if _PRESENTATION_MARKDOWN_RE.match(line):
                md_lines += 1
    min_chars = min(char_counts) if char_counts else 0
    max_chars = max(char_counts) if char_counts else 0
    mean_chars = sum(char_counts) / max(1, len(char_counts))
    spread = (max_chars / max(1, min_chars)) if min_chars else 0.0
    md_ratio = md_lines / max(1, nonempty_lines)
    reasons = []
    if mean_chars >= 2600:
        reasons.append("样本平均篇幅偏长：复核高分是否来自有效信息密度，而非字数带来的充实感")
    if spread >= 2.2 and len(char_counts) >= 2:
        reasons.append("样本章节长度差异大：不要把更长章节自动视为更高质量")
    if md_ratio >= 0.18:
        reasons.append("markdown/列表/引用等格式线索偏多：复核分数是否被排版可读性带偏")
    return {
        "enabled": True,
        "level": "review" if reasons else "none",
        "score_adjustment": 0,
        "raw_score_adjustment": 0,
        "reasons": reasons,
        "stats": {
            "sample_count": len(samples),
            "cjk_chars_total": sum(char_counts),
            "mean_cjk_chars": round(mean_chars, 1),
            "min_cjk_chars": min_chars,
            "max_cjk_chars": max_chars,
            "max_to_min_chapter_chars": round(spread, 2) if spread else 0.0,
            "markdown_line_ratio": round(md_ratio, 3),
        },
        "note": "advisory only：提示判官复核长度/格式偏好，不改 raw_score 或 total_score",
    }


def build_prompt(root, meta, settings, baseline, chapters, platform_mode, first_party=None,
                 reader_panel=None, reader_telemetry=None, reference_distribution=None, title_collision=None,
                 ab_take_results=None, task_id="__SCORE_TASK_ID__", expect_adaptation=False,
                 repetition_prior=None, platform_label=None):
    # This function generates a prompt for the LLM to perform the assessment
    # In a real automation, this would be sent to an LLM API.

    baseline_summary = "无（请先运行 collect_market_baseline.py）"
    if baseline:
        sources = []
        for s in baseline.get("sources", []):
            q = s.get("source_quality") or {}
            quality = f"；证据质量 {q.get('confidence')} {q.get('score')}" if q else ""
            sources.append(f"- {s['platform']}: {', '.join(s.get('signals', [])[:10])}{quality}")
        manual = [
            f"- {ev['platform']}｜{ev['date']}｜{ev['source']}：{ev['summary']}"
            + (
                f"；证据质量 {ev.get('evidence_quality', {}).get('confidence')} {ev.get('evidence_quality', {}).get('score')}"
                if ev.get("evidence_quality") else ""
            )
            for ev in baseline.get("manual_evidence") or []
            if manual_evidence_valid(ev)
        ]
        warnings = [f"- 覆盖告警：{w}" for w in baseline.get("coverage_warnings") or []]
        overall = []
        if baseline.get("evidence_quality"):
            q = baseline["evidence_quality"]
            overall.append(
                f"- 整体证据质量：{q.get('confidence')} ({q.get('score')})，"
                f"有效证据 {q.get('effective_evidence_count')} 条。"
            )
        baseline_summary = "\n".join(overall + sources + manual + warnings)

    rubric_text = "（详见 novel-score/references/rubric.md）"

    title = project_title(meta)
    if title:
        dim_list = " / ".join(f"{key}({label})" for key, label in TITLE_CHECK_DIMENSIONS)
        title_check_section = f"""## 书名体检（附加体检项 · 不计入百分制总分）
当前书名：《{title}》。请按 novel-title 的 5 维标准各打 1-5 分：{dim_list}。
- anti_collision 只做常见度初判；联网查重归 novel-title。{title_collision_text(title_collision)}
- 总分（满分 25）明显偏低、与目标平台命名习惯错位、或疑似撞名时，置 needs_rename=true。"""
        title_check_json = """,
  "title_check": {
    "scores": {"hook": 4, "platform_fit": 3, "character_identity": 3, "anti_collision": 4, "memorability": 4},
    "comment": "...",
    "needs_rename": false
  }"""
    else:
        title_check_section = """## 书名体检（附加体检项）
书名未定——不输出 title_check 字段；评分后建议用 novel-title 起名。"""
        title_check_json = ""

    if expect_adaptation:
        ad_dim_list = " / ".join(f"{key}({label})" for key, label in ADAPTATION_CHECK_DIMENSIONS)
        adaptation_section = f"""## 短剧改编潜力体检（附加体检项 · 不计入百分制总分）
目标平台命中短剧/漫剧。请评估这部本身的**短剧改编潜力**，按 5 维各打 1-5 分：{ad_dim_list}。
- 关注：可视化场景多不多、强钩能不能镜头化、人物关系冲突够不够浓、是否有单元剧式可切的节拍、题材/人设在短剧赛道是否新鲜（非已拍烂套路）。
- 总分（满分 25）明显偏低时置 low_potential=true；改编门槛在结构与冲突，不在文笔。"""
        adaptation_json = """,
  "adaptation_check": {
    "scores": {"visual_scene": 4, "hook_cinematic": 4, "conflict_intensity": 3, "episodic_beat": 3, "ip_freshness": 3},
    "comment": "...",
    "low_potential": false
  }"""
    else:
        adaptation_section = ""
        adaptation_json = ""

    prompt = f"""# 小说评分体检任务

请作为专业的小说编辑和市场专家，对以下小说内容进行深度打分。

## 项目背景
- 标题：{meta.get('title') or '未定'}
- 题材：{meta.get('genre') or '未定'}
- 目标平台：{platform_label or settings.get('目标平台') or meta.get('target_platform') or '未指定（均衡向）'}
- 评分权重档：{platform_mode}

## 市场基准（当前热榜信号 · 外部公榜）
{baseline_summary}

## 第一方题材战绩（自有投放回灌）
{first_party_genre_text(first_party)}

## 真实读者反馈（novel-feedback 回灌 · retention 维度最高优先级读端证据）
{reader_telemetry_text(reader_telemetry)}

## 合成叙事探针（novel-simulate · context-only，不参与自动调分）
{reader_panel_text(reader_panel)}

## A/B take 结果（小流量分流 · 仅展示；裸 uplift 不自动调分）
{ab_take_results_text(ab_take_results)}

## 跨章重复率/机械文风（确定性机检 · retention 维度负向先验）
{repetition_prior_text(repetition_prior)}

## 参考分布（合规样本百分位 · WebNovelBench 式相对水位）
{reference_distribution_text(reference_distribution)}

{title_check_section}
{adaptation_section}

## 评估内容
{chr(10).join(f"### 第{c['num']}章 {c['title']}\n{c['content'][:1000]}..." for c in chapters)}

## 任务要求
请根据上述内容，对照评分细则（rubric.md），对以下八个维度给出 1-10 的原始分，并提供证据（原文引文）和短评。
同时检查是否有「雷点扣分项」（开篇慢热、题材退潮、主角降智、注水、三观雷、AI味、烂尾）。

**⑧ novelty（新颖度/想象力）是正向上限维度，与雷点扣分互补**：评"这部有什么别人没有的"——
设定/金手指/题材组合的差异化记忆点、情节走向的预期违背（意外但回看合理、不靠 deus ex machina）、
非模板化的桥段与结局。全程套路复刻、每个转折都可预测、结局落回模板=低分（1-4）；
熟悉套路混搭出新切口、至少一处让老读者惊到但服气的反转=中高分（6-8）；
核心设定/叙事结构本身即记忆点、可被读者转述传播=高分（9-10）。
注意：新颖不能以牺牲连贯为代价——为怪而怪、破坏读者契约的"意外"应同时在 plot_structure 扣回。

**评分中立化须知（判官去偏·务必遵守）**：只评**内容质量本身**——情节、人物、文笔、信息密度、留存力。
- **不要**因为某段更长、字数更多、排版/markdown 更花、列表更多、标题层级更清楚、辞藻更密就给更高分；长度/篇幅相近时以内容质量为先。
- 若两个章节/版本长度相近，优先比较有效信息增量、人物选择、冲突推进、语言准确度和留存力；不要用“看起来更完整/更会排版”替代质量判断。
- 注水、铺陈过度、重复复述属于**减分**，应进 ⑦完读/留存 与雷点项扣分，绝不能因为"字多/看起来充实"而加分。
- 评分对照固定 rubric 锚点，不被呈现形式带偏（研究表明：长度与格式风格是 LLM 判官最大的残留偏差，
  而位置偏差在前沿模型已很小——故重点防长度/格式偏好，而非单纯换序）。

请输出 JSON 格式，严格遵守以下结构：
{{
  "score_task_id": "{task_id}",
  "scores": [
    {{
      "dimension": "topic_heat",
      "raw_score": 8,
      "evidence": "...",
      "comment": "...",
      "improve_by": "..."
    }},
    ... (其余7个维度)
  ],
  "deductions": [
    {{
      "item": "雷点名称",
      "points": -5,
      "reason": "..."
    }}
  ]{title_check_json}{adaptation_json}
}}

【可选·去偏增强】关键稿推荐用 ≥3 个**不同模型家族**的判官各自独立打这 8 个维度；
若当前只有 ≥2 个相互独立的判官视角（或不同模型），系统仍向后兼容接收，但会提示未满推荐标准。
请额外附 "judges_panel": {{"判官A": {{"topic_heat": 8, ...}}, "判官B": {{...}}}}（每维 1-10）。
如判官名不含模型家族，可额外附 "judge_families": {{"判官A": "openai", "判官B": "anthropic", "判官C": "google"}}。
系统会按 judge_protocol 去偏协议算判官间方差：分歧大的维度自动标「弃权/升级」、提示人工复核或换更强跨家族判官
（仅 advisory，不改你给的 scores 与总分）。单判官可省略此字段，按原行为评分。
"""
    return prompt


def generate_markdown_report(root, meta, result, total_score, tier, verdict, roi):
    date_s = date.today().isoformat()
    lines = [
        f"# 评分报告 — {meta.get('title') or '未定'}",
        "",
        "## 1. 概览",
        "",
        "| 维度 | 原始分 | 权重 | 加权得分 |",
        "|---|---|---|---|",
    ]
    for s in result["scores"]:
        lines.append(f"| {s['dimension_label']} | {s['raw_score']} | {s['weight']} | {s['weighted_score']:.1f} |")
    
    lines.append(f"| **雷点扣分** | - | - | **{result['total_deductions']}** |")
    adjustment = result.get("reader_feedback_adjustment") or {}
    if adjustment:
        lines.append(f"| **读者反馈调整** | - | - | **{float(adjustment.get('points') or 0):+.1f}** |")
    lines.append(f"| **总分** | - | - | **{total_score:.1f}** |")
    lines.append("")
    if result.get("pre_reader_feedback_score") is not None:
        lines.append(f"- **调整前基础分**：{float(result.get('pre_reader_feedback_score') or 0):.1f}")
    if adjustment and adjustment.get("reasons"):
        lines.append(f"- **读者反馈调分依据**：{'; '.join(adjustment.get('reasons') or [])}")
    lines.append(f"- **档位**：{tier}")
    lines.append(f"- **判定**：{verdict}")
    decision = result.get("production_decision") or {}
    if decision:
        lines.append(f"- **生产决策**：{decision.get('decision')} → {decision.get('route')}（{decision.get('reason')}）")
    lines.append(f"- **改写 ROI**：{roi}")
    telemetry = result.get("reader_telemetry_summary")
    if telemetry:
        agg = telemetry.get("aggregate") or {}
        lines.append(
            f"- **真实读者反馈**：完读率 {agg.get('completion_rate')} / 弃读率 {agg.get('drop_rate')}；"
            f"优先复核章节 {telemetry.get('weakest_chapters') or []}"
        )
    benchmark = result.get("benchmark_percentile")
    if benchmark and benchmark.get("status") == "ok":
        lines.append(
            f"- **参考分布百分位**：总分 P{benchmark.get('total_score_percentile')} "
            f"（样本 {benchmark.get('sample_count')}，{benchmark.get('distribution_title')}）"
        )
    lines.append("")

    rp = result.get("repetition_prior") or {}
    rp_prior = rp.get("prior") or {}
    if rp_prior and rp_prior.get("level") and rp_prior["level"] != "none":
        rp_sum = rp.get("summary") or {}
        lines.append(f"## 跨章重复率/机械文风先验（retention·确定性机检·档 {rp_prior['level']}）")
        lines.append(f"- 相邻章最高近重复 {float(rp_sum.get('adjacent_max_jaccard') or 0):.0%}；"
                     f"机械开篇组 {rp_sum.get('mechanical_opener_groups', 0)}；"
                     f"跨章复用整句 {rp_sum.get('repeated_sentences', 0)}；"
                     f"机械句式模板 {rp_sum.get('sentence_opener_templates', 0)}；"
                     f"句首词高频 {rp_sum.get('sentence_start_token_groups', 0)}；"
                     f"短句式模板 {rp_sum.get('short_sentence_templates', 0)}；"
                     f"低压缩章节 {rp_sum.get('low_chapter_compression_count', 0)}；"
                     f"retention 调分 {rp_prior.get('points', 0):+d}")
        for r in rp_prior.get("reasons", [])[:4]:
            lines.append(f"  - {r}")
        lines.append("")

    debias = result.get("judge_debias") or {}
    if debias.get("enabled"):
        low = debias.get("low_confidence_dimensions") or []
        diversity = debias.get("family_diversity") or {}
        lines.append(f"## 判官去偏（{debias.get('judges_count')} 判官 · {diversity.get('families_count', 0)} 家族）")
        if diversity and not diversity.get("meets_recommended"):
            lines.append(f"- 未满 ≥{diversity.get('recommended_min_families', 3)} 不同模型家族推荐标准；关键稿建议补第三家族复核。")
        if low:
            dims = "、".join(d["dimension_label"] for d in low)
            lines.append(f"- ⚠️ 判官分歧大、弃权/升级维度（仅供参考，未改分）：{dims}")
        else:
            lines.append("- ✅ 判官共识良好，无高方差维度")
        lines.append("")

    bias_adv = result.get("judge_bias_advisory") or {}
    if bias_adv.get("level") and bias_adv.get("level") != "none":
        lines.append("## 判官长度/格式中立性提示（advisory）")
        for r in bias_adv.get("reasons", []):
            lines.append(f"- {r}")
        stats = bias_adv.get("stats") or {}
        lines.append(
            f"- 样本均字数 {stats.get('mean_cjk_chars')}；长度 max/min {stats.get('max_to_min_chapter_chars')}；"
            f"markdown 行占比 {stats.get('markdown_line_ratio')}；本提示未改 raw_score/total_score。"
        )
        lines.append("")

    if result.get("waivers"):
        lines.append("## 显式豁免")
        for waiver in result["waivers"]:
            lines.append(
                f"- **{waiver['id']}** [{waiver['type']}] {waiver['reason']}；"
                f"影响 gate：{waiver['affected_gate']}；风险：{waiver.get('risk') or '见 details'}"
            )
        lines.append("")
    
    lines.append("## 2. 逐维分析")
    for s in result["scores"]:
        lines.append(f"### {s['dimension_label']} ({s['raw_score']}/10)")
        lines.append(f"- **短评**：{s['comment']}")
        lines.append(f"- **证据**：> {s['evidence']}")
        lines.append(f"- **改进建议**：{s['improve_by']}")
        lines.append("")

    if result["deductions"]:
        lines.append("## 3. 雷点扣分")
        for d in result["deductions"]:
            lines.append(f"- **{d['item']}** ({d['points']}分): {d['reason']}")
        lines.append("")

    tc = result.get("title_check")
    if tc:
        dim_labels = dict(TITLE_CHECK_DIMENSIONS)
        dims = "、".join(
            f"{dim_labels[key]} {tc['scores'].get(key)}/5" for key, _ in TITLE_CHECK_DIMENSIONS
        )
        lines.append("## 书名体检（附加项 · 不计入总分）")
        lines.append(f"- 当前书名：《{tc['title']}》 — **{tc['total']:.0f}/{tc['max_total']}**（{dims}）")
        lines.append(f"- 撞名状态：{tc['collision'].get('status')}"
                     + (f"（{tc['collision'].get('path')}）" if tc['collision'].get('path') else "（未联网查重，unchecked ≠ 不撞名）"))
        lines.append(f"- 短评：{tc['comment']}")
        lines.append("- 结论：" + ("**建议换名** → 交 `novel-title` 重出候选并跑撞名检查"
                                  if tc["needs_rename"] else "书名可用"))
        lines.append("")

    ac = result.get("adaptation_check")
    if ac:
        ad_labels = dict(ADAPTATION_CHECK_DIMENSIONS)
        ad_dims = "、".join(
            f"{ad_labels[key]} {ac['scores'].get(key)}/5" for key, _ in ADAPTATION_CHECK_DIMENSIONS
        )
        lines.append("## 短剧改编潜力体检（附加项 · 不计入总分）")
        lines.append(f"- 改编潜力：**{ac['total']:.0f}/{ac['max_total']}**（{ad_dims}）")
        lines.append(f"- 短评：{ac['comment']}")
        lines.append("- 结论：" + ("**改编潜力偏低** → 走短剧前先用 `novel-condense` 出漫剧版精简骨架"
                                  if ac["low_potential"] else "具备短剧改编潜力，可交后续漫剧转制流程推进"))
        lines.append("")

    lines.append("## 4. 判定 & 下一步建议")
    lines.append(f"**能不能火**：{verdict_summary(total_score, verdict)}")
    lines.append("")
    lines.append("**建议路由**：")
    for action in result.get("next_actions", []):
        lines.append(f"- [{action['priority']}] {action['recommended_skill']}: {action['action']}")

    return "\n".join(lines)


def verdict_summary(total, verdict):
    if total >= 85:
        return "具备极强爆款潜力，主线清晰爽点密集，建议直接推进。"
    elif total >= 70:
        return "素质合格，具备一定火的潜力，但需针对弱项进行精细化修整。"
    elif total >= 55:
        return "火的概率较低，存在结构性或题材性问题，需要大幅调整。"
    else:
        return "目前版本难以在市场上获得认可，建议审慎评估是否继续。"


def main():
    ap = argparse.ArgumentParser(description="小说评分自动化引擎")
    ap.add_argument("project_root")
    ap.add_argument("--file", help="指定要评分的单文件路径（如某个 take）")
    ap.add_argument("--chapter", type=int, help="指定章节号（用于定位 baseline 和 samples）")
    ap.add_argument("--platform", default=None, help="目标平台，或评分权重档：均衡向 | 商业爽文向 | 品质向")
    ap.add_argument("--scope", default="opening", choices=["full", "opening", "arc"])
    ap.add_argument("--mock-assessment", help="提供模拟评估 JSON 的路径，用于测试或手动注入")
    ap.add_argument("--task", default=None,
                    help="score_task.json 路径；缺省 <作品根>/评分/score_task.json")
    ap.add_argument("--json", action="store_true", help="输出机器可读报告")
    ap.add_argument("--genre-ledger", help=f"自有题材战绩库路径（外部投放侧回灌）；默认 $NOVEL_GENRE_LEDGER 或 <repo>/{LEDGER_REL_PATH}")
    ap.add_argument("--allow-stale-baseline", action="store_true",
                    help="允许缺失/过期/无证据市场基准，仅用于离线测试或人工明确豁免")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        sys.exit(2)

    meta = load_meta(root)
    settings = load_settings(root)
    baseline = find_latest_baseline(root)
    freshness = baseline_freshness(baseline)
    if freshness["blocking"] and not args.allow_stale_baseline:
        print(f"[err] {freshness['reason']}", file=sys.stderr)
        print("      先运行：python3 skills/novel/novel-score/scripts/collect_market_baseline.py "
              f"\"{os.path.join(root, '评分')}\" --target-platform \"<目标平台>\" --allow-fetch-errors",
              file=sys.stderr)
        sys.exit(2)
    pending_waiver = None
    if freshness["blocking"] and args.allow_stale_baseline:
        pending_waiver = make_freshness_waiver(freshness)
    ledger_path = args.genre_ledger or default_ledger_path(root)
    first_party = summarize_first_party_genre(load_genre_ledger(ledger_path), meta.get("genre"))
    reader_telemetry = load_reader_telemetry_summary(root)
    reader_panel = load_reader_panel_signals(root)
    ab_take_results = load_ab_take_results(root)
    reference_distribution = find_latest_reference_distribution(root)
    book_title = project_title(meta)
    title_collision = load_title_collision(root, book_title)
    short_drama_target = is_short_drama_target(settings, meta)

    raw_platform = args.platform or settings.get("目标平台") or meta.get("target_platform") or ""
    platform_mode = _resolve_platform_mode(raw_platform)

    weights = WEIGHTS.get(platform_mode, WEIGHTS["均衡向"])

    # Sample chapters
    samples = []
    sample_paths = []
    if args.file:
        if not os.path.exists(args.file):
            print(f"[err] 找不到文件：{args.file}", file=sys.stderr)
            sys.exit(2)
        sample_paths = [args.file]
        num = args.chapter or 0
        with open(args.file, encoding="utf-8") as f:
            content = f.read()
        title_m = re.search(r"^#\s*(?:第\d+章\s*)?(.*)", content)
        title = title_m.group(1).strip() if title_m else ""
        samples.append({"num": num, "title": title, "content": content})
    else:
        chapter_files = sorted(glob(os.path.join(root, "章节", "第*.md")), key=chapter_sort_key)
        if not chapter_files:
            print("[err] 章节/ 下没有 .md 文件", file=sys.stderr)
            sys.exit(2)
        
        if args.scope == "opening":
            sample_files = chapter_files[:3]
        else:
            sample_files = chapter_files
        sample_paths = sample_files

        for f in sample_files:
            num = chapter_number_from_path(f) or 0
            with open(f, encoding="utf-8") as fp:
                content = fp.read()
            title_m = re.search(r"^#\s*第\d+章\s*(.*)", content)
            title = title_m.group(1).strip() if title_m else ""
            samples.append({"num": num, "title": title, "content": content})

    # 跨章重复率/机械文风先验（确定性·喂 retention 维度）：用已加载章节算，<2 章或机检不可用 → None。
    repetition_prior = None
    if repetition is not None and len(samples) >= 2:
        _rep_chapters = [(s["num"], s["content"]) for s in sorted(samples, key=lambda s: s["num"])]
        _rep_findings, _rep_summary = repetition.cross_chapter_repetition(_rep_chapters)
        repetition_prior = {"summary": _rep_summary, "prior": repetition.retention_prior(_rep_summary)}

    source_snapshot = (
        snapshot_files(root, sample_paths, mode=f"score:{args.scope}")
        if snapshot_files else None
    )
    market_snapshot = baseline_file_snapshot(root, baseline)
    prompt = build_prompt(
        root, meta, settings, baseline, samples, platform_mode, first_party,
        reader_panel=reader_panel,
        reader_telemetry=reader_telemetry,
        reference_distribution=reference_distribution,
        title_collision=title_collision,
        ab_take_results=ab_take_results,
        task_id="__SCORE_TASK_ID__",
        expect_adaptation=short_drama_target,
        repetition_prior=repetition_prior,
        platform_label=raw_platform or "未指定（均衡向）",
    )
    expected_task = build_score_task(
        root,
        scope=args.scope,
        platform_mode=platform_mode,
        source_snapshot=source_snapshot,
        baseline_snapshot=market_snapshot,
        freshness=freshness,
        first_party=first_party,
        prompt=prompt,
    )
    task_path = score_task_path(root, args.task)

    if not args.mock_assessment:
        write_score_task(root, task_path, expected_task)
        job = None
        if semantic_job is not None:
            response_rel = os.path.join("评分", f"score_assessment_{expected_task['score_task_id']}.json")
            command = [
                "python3", "skills/novel/novel-score/scripts/score.py", f'"{root}"',
                "--scope", args.scope,
                "--task", f'"{task_path}"',
                "--mock-assessment", f'"{os.path.join(root, response_rel)}"',
            ]
            if args.file:
                command.extend(["--file", f'"{os.path.abspath(args.file)}"'])
            if args.chapter:
                command.extend(["--chapter", str(args.chapter)])
            if args.platform:
                command.extend(["--platform", f'"{args.platform}"'])
            job = semantic_job.create_job(
                root,
                semantic_kind="score_assessment",
                prompt=expected_task["assessment_prompt"],
                response_out=response_rel,
                required_fields=["score_task_id", "scores", "deductions"],
                schema_ref="score_assessment",
                source_snapshot=expected_task.get("source_snapshot") or {},
                complete_command=" ".join(command),
                metadata={
                    "score_task_id": expected_task["score_task_id"],
                    "score_task_path": rel_path(root, task_path),
                    "assessment_prompt_hash": expected_task["assessment_prompt_hash"],
                    "scope": args.scope,
                },
            )
        print("--- LLM SCORING PROMPT ---")
        print(expected_task["assessment_prompt"])
        print("--- END PROMPT ---")
        print(f"\n[info] score_task 已写入：{task_path}")
        if job:
            print(f"[info] 语义任务已写入：{job['job_path']}")
            print(f"[info] 让 AI 代理读取 {os.path.join(root, job['prompt_path'])}，写回 {os.path.join(root, job['response_out'])} 后执行 job 内 complete_command。")
        print("[info] 推荐由 AI 代理处理语义任务并写回评估 JSON；兼容入口仍是 --mock-assessment 注入结果。")
        return

    if not os.path.exists(task_path):
        print(f"[err] 缺少 score_task：{task_path}；请先不带 --mock-assessment 生成任务。", file=sys.stderr)
        sys.exit(2)
    with open(task_path, encoding="utf-8") as f:
        task = json.load(f)
    ok, msg = validate_score_task(
        root,
        task,
        scope=args.scope,
        platform_mode=platform_mode,
        baseline_snapshot=market_snapshot,
        expected_prompt_hash=expected_task.get("assessment_prompt_hash"),
    )
    if not ok:
        print(f"[err] {msg}", file=sys.stderr)
        sys.exit(2)

    # Process Assessment
    with open(args.mock_assessment, encoding="utf-8") as f:
        assessment = json.load(f)
    if assessment.get("score_task_id") != task.get("score_task_id"):
        print(
            "[err] assessment.score_task_id 与 score_task 不匹配；"
            "必须使用当前 score_task 对应 prompt 生成评分 JSON。",
            file=sys.stderr,
        )
        sys.exit(2)
    errors = validate_assessment(assessment, expect_title_check=bool(book_title),
                                 expect_adaptation=short_drama_target)
    if errors:
        print("[err] mock assessment 不符合 novel-score schema：", file=sys.stderr)
        for error in errors:
            print(f"      - {error}", file=sys.stderr)
        sys.exit(2)

    total_weighted = 0.0
    processed_scores = []
    dim_map = dict(DIMENSIONS)
    for s in assessment["scores"]:
        dim = s["dimension"]
        weight = weights.get(dim, 0)
        raw = s["raw_score"]
        weighted = (raw * weight) / 10.0
        total_weighted += weighted
        processed_scores.append({
            "dimension": dim,
            "dimension_label": dim_map.get(dim, dim),
            "raw_score": raw,
            "weight": weight,
            "weighted_score": weighted,
            "evidence": s.get("evidence", ""),
            "comment": s.get("comment", ""),
            "improve_by": s.get("improve_by", "")
        })

    judge_debias = apply_judge_debias(assessment, processed_scores)

    deductions = assessment.get("deductions", [])
    total_deductions = sum(d["points"] for d in deductions)
    # 扣分上限 -30：防止雷点扣分淹没基本面（加权 90 扣到 40 vs 加权 40 无扣分，
    # 总分相同但改续决策完全不同——上限让 deductions 保持尖锐信号但不让基本面不可比）
    total_deductions = max(-30, total_deductions)
    pre_reader_feedback_score = max(0.0, total_weighted + total_deductions)
    reader_feedback_adjustment = compute_reader_feedback_adjustment(
        reader_telemetry=reader_telemetry,
        reader_panel=reader_panel,
        ab_take_results=ab_take_results,
        repetition_prior=repetition_prior,
    )
    final_score = max(0.0, min(100.0, pre_reader_feedback_score + reader_feedback_adjustment["points"]))
    tier, verdict, roi = get_tier_verdict(final_score)
    benchmark_percentile = compute_benchmark_percentiles(
        root, final_score, processed_scores, reference_distribution
    )
    judge_bias_advisory = presentation_bias_advisory(samples)

    next_actions = build_next_actions(verdict, processed_scores)
    production_decision = build_production_decision(verdict, final_score, meta, settings)
    title_check = build_title_check(assessment.get("title_check"), book_title, title_collision)
    # 弃稿重立时换名无意义（novel-create 重开自带新名）；其余判定下书名不过关都值得顺手换。
    if title_check and title_check["needs_rename"] and verdict != "弃稿重立":
        next_actions.append({
            "priority": "should",
            "recommended_skill": "novel-title",
            "return_to_stage": "setup",
            "action": (f"书名体检不过关（{title_check['total']:.0f}/{title_check['max_total']}，"
                       f"撞名状态 {title_check['collision'].get('status')}）："
                       "用 novel-title 重出候选并跑联网撞名检查"),
            "dimension": "title_check",
        })
    adaptation_check = build_adaptation_check(assessment.get("adaptation_check"))
    # 短剧改编潜力偏低且非弃稿：提示先出漫剧版精简骨架，别直接拿长篇硬改编。
    if adaptation_check and adaptation_check["low_potential"] and verdict != "弃稿重立":
        next_actions.append({
            "priority": "must",
            "recommended_skill": "novel-condense",
            "return_to_stage": "setup",
            "action": (f"短剧改编潜力偏低（{adaptation_check['total']:.0f}/{adaptation_check['max_total']}）："
                       "若要走短剧/漫剧改编，先用 novel-condense 出漫剧版精简骨架"),
            "dimension": "adaptation_check",
        })
    # judge panel 去偏：同模型 persona panel 与跨模型高方差分开提示（advisory，不改分不阻断）。
    if judge_debias.get("enabled") and judge_debias.get("method") == "persona_panel":
        diversity = judge_debias.get("family_diversity") or {}
        next_actions.append({
            "priority": "should",
            "recommended_skill": "novel-score",
            "return_to_stage": "review",
            "action": (f"当前只是同模型 persona panel（{judge_debias['judges_count']} 判官/"
                       f"{diversity.get('families_count', 0)} 个模型家族），整体 low confidence；"
                       f"关键稿建议补足 ≥2 个模型家族后重评，推荐 ≥{diversity.get('recommended_min_families', 3)} 家族"),
            "dimension": "judge_debias",
        })
    elif judge_debias.get("enabled") and judge_debias.get("abstain_dimensions"):
        dims = "、".join(d["dimension_label"] for d in judge_debias["abstain_dimensions"])
        next_actions.append({
            "priority": "should",
            "recommended_skill": "novel-score",
            "return_to_stage": "review",
            "action": (f"判官分歧大（{judge_debias['judges_count']} 判官）：{dims} 维度方差超阈值，"
                       "该维度结论弃权，建议人工复核或换 ≥3 个不同模型家族/更强判官重评"),
            "dimension": "judge_debias",
        })
    elif judge_debias.get("enabled"):
        diversity = judge_debias.get("family_diversity") or {}
        if diversity and not diversity.get("meets_recommended"):
            next_actions.append({
                "priority": "could",
                "recommended_skill": "novel-score",
                "return_to_stage": "review",
                "action": (f"当前判官覆盖 {diversity.get('families_count', 0)} 个模型家族；"
                           f"关键稿建议补足 ≥{diversity.get('recommended_min_families', 3)} 家族后复核"),
                "dimension": "judge_debias",
            })
    waivers = []
    if pending_waiver:
        waivers.append(pending_waiver)
        if append_waiver:
            append_waiver(root, pending_waiver)

    # Final Payload
    report_json = {
        "schema_version": 1,
        "kind": "novel_score_report",
        "project_root": root,
        "generated_at": date.today().isoformat(),
        "target_platform": raw_platform or "未指定",
        "score_weight_profile": platform_mode,
        "score_task_id": task.get("score_task_id"),
        "score_task_path": rel_path(root, task_path),
        "assessment_prompt_hash": task.get("assessment_prompt_hash"),
        "scope": task.get("scope") or {"mode": args.scope, "chapter_count": len(samples)},
        "source_snapshot": task.get("source_snapshot"),
        "market_baseline": {
            "baseline_date": baseline.get("baseline_date") if baseline else None,
            "baseline_path": f"评分/题材热榜_{baseline.get('baseline_date')}.md" if baseline else None,
            "baseline_json_path": f"评分/market_baseline_{baseline.get('baseline_date')}.json" if baseline else None,
            "sources": baseline.get("sources", []) if baseline else [],
            "manual_evidence": baseline.get("manual_evidence", []) if baseline else [],
            "evidence_quality": baseline.get("evidence_quality") if baseline else None,
            "coverage_warnings": baseline.get("coverage_warnings", []) if baseline else [],
            "expires_after_days": baseline.get("expires_after_days") if baseline else None,
            "freshness": freshness,
            "snapshot": task.get("market_baseline_snapshot"),
        },
        "first_party_genre": first_party,
        "genre_ledger_path": ledger_path if os.path.isfile(ledger_path) else None,
        "reader_telemetry_path": READER_TELEMETRY_REL_PATH if reader_telemetry else None,
        "reader_telemetry_summary": reader_telemetry,
        "reader_panel_path": os.path.join(READER_PANEL_REL_PATH) if reader_panel else None,
        "reader_panel_signals": reader_panel,
        "ab_take_results_path": AB_TAKE_RESULTS_REL_PATH if ab_take_results else None,
        "ab_take_results_summary": summarize_ab_take_results(ab_take_results),
        "benchmark_percentile": benchmark_percentile,
        "scores": processed_scores,
        "judge_debias": judge_debias,
        "judge_bias_advisory": judge_bias_advisory,
        "repetition_prior": repetition_prior,
        "title_check": title_check,
        "adaptation_check": adaptation_check,
        "deductions": deductions,
        "total_deductions": total_deductions,
        "pre_reader_feedback_score": pre_reader_feedback_score,
        "reader_feedback_adjustment": reader_feedback_adjustment,
        "total_score": final_score,
        "tier": tier,
        "verdict": verdict,
        "production_decision": production_decision,
        "rewrite_roi": roi,
        "waivers": waivers,
        "next_actions": next_actions
    }

    # Write Files
    score_dir = os.path.join(root, "评分")
    os.makedirs(score_dir, exist_ok=True)
    
    with open(os.path.join(score_dir, "score_report.json"), "w", encoding="utf-8") as f:
        json.dump(report_json, f, ensure_ascii=False, indent=2)
    
    md_content = generate_markdown_report(root, meta, report_json, final_score, tier, verdict, roi)
    md_path = os.path.join(score_dir, f"评分报告_{date.today().isoformat()}.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Sync to take manifest if applicable
    if args.chapter and args.file:
        sync_to_take_manifest(root, args.chapter, args.file, final_score, verdict)

    # 埋点：把本次评分遇到的流程摩擦上报为优化信号，novel-review 模式②（self_audit）
    # 下次自审时摄入，无需用户重述即可继续触发自我优化。
    emit_optimization_signals(
        root,
        freshness=freshness,
        baseline=baseline,
        verdict=verdict,
        title_check=title_check,
        adaptation_check=adaptation_check,
        used_waiver=bool(pending_waiver),
    )

    print(f"[ok] 评分报告 JSON → {os.path.join(score_dir, 'score_report.json')}")
    print(f"[ok] 评分报告 MD   → {md_path}")
    print(f"     总分：{final_score:.1f} | 档位：{tier} | 判定：{verdict}")


def emit_optimization_signals(root, *, freshness, baseline, verdict,
                              title_check, adaptation_check, used_waiver):
    """Report production-time friction from this scoring run into
    生产数据/优化信号.jsonl (novel/_lib/friction_log). No-op if the logger is
    unavailable. Each signal is idempotent per signature, so re-runs don't bloat
    the log."""
    if log_friction is None:
        return
    baseline_date = str((freshness or {}).get("baseline_date") or "")
    # 1) 不得不豁免 baseline 新鲜度闸 → 流程层硬摩擦，最该被自审看见。
    if used_waiver:
        log_friction(
            root, "score_baseline_waiver", skill="novel-score", severity="block",
            title="评分时豁免了 market baseline 新鲜度闸",
            detail=(f"baseline {baseline_date} freshness={(freshness or {}).get('status')}，"
                    "用 --allow-stale-baseline 跑分。说明真实市场证据缺位或采集链路有缺口。"),
            suggested_fix=("查 collect_market_baseline.py 采集/覆盖逻辑或补 --manual-evidence；"
                           "若是某类证据被过紧的新鲜度窗口误杀，复核 score.py 的 freshness 闸。"),
            evidence={"freshness": freshness},
            key=f"{(freshness or {}).get('status')}|{baseline_date}",
        )
    # 2) 短剧/漫剧目标却仍带 coverage_warnings（覆盖只是被豁免而非真满足）。
    coverage_warnings = (baseline or {}).get("coverage_warnings") or []
    if coverage_warnings:
        log_friction(
            root, "score_coverage_gap", skill="novel-score", severity="warn",
            title="market baseline 仍存在短剧/漫剧平台覆盖缺口",
            detail="；".join(str(w) for w in coverage_warnings)[:500],
            suggested_fix=("补红果/抖音漫剧第三方榜单/行业证据为结构化 --manual-evidence；"
                           "若证据存在却被判缺口，复核 collect_market_baseline.coverage_window。"),
            evidence={"coverage_warnings": coverage_warnings},
            key=baseline_date,
        )
    # 3) 判定大改/弃稿重立 → 产线层面（题材/结构）值得自审复盘，不只是单稿改。
    if verdict in ("大改", "弃稿重立"):
        log_friction(
            root, "score_low_verdict", skill="novel-score", severity="advice",
            title=f"评分判定为「{verdict}」",
            detail=f"本稿判定 {verdict}；若同题材反复落到此判定，可能是选题/工艺层面问题。",
            suggested_fix="对照 novel-review 模式②差距清单核查题材热度与开篇工艺，再决定改稿还是改流程。",
            evidence={"verdict": verdict},
            key=verdict,
        )
    # 4) 书名体检不过关。
    if title_check and title_check.get("needs_rename"):
        log_friction(
            root, "score_needs_rename", skill="novel-score", severity="advice",
            title="书名体检不过关（needs_rename）",
            detail=f"书名分 {title_check.get('total')}/{title_check.get('max_total')}，建议 novel-title 重出候选。",
            suggested_fix="走 novel-title 重出候选并联网撞名；若反复不过关，复核 novel-title 平台命名标尺。",
            evidence={"title_check_total": title_check.get("total")},
            key=str(title_check.get("total")),
        )
    # 5) 短剧改编潜力偏低。
    if adaptation_check and adaptation_check.get("low_potential"):
        log_friction(
            root, "score_low_adaptation", skill="novel-score", severity="advice",
            title="短剧改编潜力偏低（low_potential）",
            detail=f"改编潜力分 {adaptation_check.get('total')}/{adaptation_check.get('max_total')}。",
            suggested_fix="走 novel-condense 出漫剧版精简骨架；改编门槛在结构与冲突，不在文笔。",
            evidence={"adaptation_total": adaptation_check.get("total")},
            key=str(adaptation_check.get("total")),
        )


def sync_to_take_manifest(root, chapter, file_path, score, verdict):
    manifest_path = os.path.join(root, "章节", "takes", f"第{chapter:02d}章", "takes_manifest.json")
    if not os.path.exists(manifest_path):
        return
    
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    
    file_rel = os.path.relpath(os.path.abspath(file_path), root).replace(os.sep, "/")
    updated = False
    for t in manifest.get("takes", []):
        if t.get("file_path") == file_rel:
            t["score"] = score
            t["verdict"] = verdict
            if t.get("status") == "registered":
                t["status"] = "scored"
            updated = True
            break
    
    if updated:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f"[info] 分数已同步至挑版账本：{manifest_path}")

if __name__ == "__main__":
    main()
