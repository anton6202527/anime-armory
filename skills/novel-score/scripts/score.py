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

_COMMON = os.path.join(SKILLS_ROOT, "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)
from settings import load_settings as _load_settings  # noqa: E402

try:
    import contract
except ImportError:
    # Fallback if contract is not reachable via path
    contract = None
try:
    from report_snapshot import snapshot_files, validate_snapshot
    from waivers import append_waiver, baseline_freshness_scope, make_waiver
except ImportError:
    append_waiver = None
    baseline_freshness_scope = None
    make_waiver = None
    snapshot_files = None
    validate_snapshot = None

DIMENSIONS = [
    ("topic_heat", "题材热度匹配"),
    ("opening_hook", "开篇黄金三章钩子"),
    ("payoff_density", "爽点密度与情绪节奏"),
    ("character_power", "人设与金手指"),
    ("plot_structure", "剧情结构与主线张力"),
    ("prose", "文学性 / 文笔"),
    ("retention", "完读 / 留存潜力"),
]

WEIGHTS = {
    "商业爽文向": {
        "topic_heat": 20,
        "opening_hook": 18,
        "payoff_density": 18,
        "character_power": 12,
        "plot_structure": 12,
        "prose": 8,
        "retention": 12,
    },
    "品质向": {
        "topic_heat": 12,
        "opening_hook": 14,
        "payoff_density": 12,
        "character_power": 14,
        "plot_structure": 18,
        "prose": 18,
        "retention": 12,
    }
}


def load_meta(root):
    path = os.path.join(root, "_meta.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_settings(root):
    """读作品根下的 _设置.md；单一真值源在 common/settings.py。"""
    return _load_settings(root)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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
    notes = baseline.get("notes") or []
    if isinstance(notes, str):
        notes = [notes]
    if any(str(note).strip() for note in notes):
        return True
    for source in baseline.get("sources") or []:
        if not isinstance(source, dict):
            continue
        status = str(source.get("status") or "").strip().lower()
        signals = source.get("signals") or []
        if status == "ok" and any(str(signal).strip() for signal in signals):
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
    if not baseline_has_effective_evidence(baseline):
        return {
            "status": "no_evidence",
            "blocking": True,
            "baseline_date": raw_date,
            "expires_after_days": expires_after,
            "expires_on": expires_on.isoformat(),
            "reason": "market baseline 没有有效证据：至少需要一个 status=ok 且 signals 非空的来源，或 notes 人工补充。",
        }
    return {
        "status": "expired" if expired else "fresh",
        "blocking": expired,
        "baseline_date": raw_date,
        "expires_after_days": expires_after,
        "expires_on": expires_on.isoformat(),
        "reason": f"market baseline 已过期：{raw_date} + {expires_after} 天 < {date.today().isoformat()}" if expired else "",
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


# ── 选题→投放→反哺选题闭环：读 n2d-feedback 写的「自有题材战绩库」做第一方题材热度先验 ──
# 与 n2d 线只在此数据文件层连接，本端自带读取逻辑，不 import 任何 n2d-* 代码。
LEDGER_REL_PATH = os.path.join("生产战绩", "genre_ledger.jsonl")


def _find_repo_root(start):
    cur = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(cur, "skills")) or os.path.isdir(os.path.join(cur, ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return os.path.abspath(start)
        cur = parent


def default_ledger_path(root):
    return os.environ.get("N2D_GENRE_LEDGER") or os.path.join(_find_repo_root(root), LEDGER_REL_PATH)


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
            # "genre_performance_record" 是跨线 wire constant（= n2d_contract.GENRE_PERFORMANCE_RECORD_KIND /
            # n2d-feedback LEDGER_KIND）。novel-* 刻意不 import n2d-*，两线只在此 JSONL 文件层连接，故此处
            # 硬写字面值——若该 kind 在 n2d 侧改名，必须同步改这里，否则题材先验反哺会静默失效。
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
        return "无（尚无自有投放战绩库；先用 n2d-feedback --emit-ledger 回灌，闭环后此处显示第一方题材热度）"
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


def load_reader_panel_signals(root):
    """读 novel-simulate 产的 评分/reader_panel_signals.json（模拟读者留存先验）。

    缺文件正常退化为 None（纯公榜 + 战绩库）。字段名与 simulate_panel.py 输出对齐：
    retention_prior / hook_strength / cliche_density_per_kchar。
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


def reader_panel_text(signals):
    if not signals:
        return ("无（尚无模拟读者信号；可先跑 novel-simulate 产 评分/reader_panel_signals.json，"
                "作为发布前虚拟试读的留存先验）")
    rp = signals.get("retention_prior")
    hook = signals.get("hook_strength")
    cliche = signals.get("cliche_density_per_kchar")
    chs = signals.get("chapters_read") or signals.get("scope") or "?"
    return (
        f"模拟读者留存先验（novel-simulate 虚拟试读，范围 {chs}）："
        f"retention_prior {rp}、钩子强度 {hook}、套路密度 {cliche}/千字。"
        "（权重序：真实投放战绩 > 本模拟信号 > 公榜泛化；仅作 retention 维度先验，不单独定生死。"
        "若 retention_prior 明显偏低且套路密度高，retention 维度下调并点明开篇疑似劝退/套路堆叠。）"
    )


ACTION_BY_DIMENSION = {
    "topic_heat": ("novel-create", "setup", "重做题材/平台定位，参考第一方战绩和公榜基准"),
    "opening_hook": ("novel-craft", "outline", "重修黄金三章钩子与首屏卖点"),
    "payoff_density": ("novel-craft", "outline", "提高每 3-5 章爽点/承诺兑现密度"),
    "character_power": ("novel-rewrite", "direction_spec", "重修主角人设、金手指边界和代价"),
    "plot_structure": ("novel-rewrite", "outline", "重构主线张力、反转点和中段压力线"),
    "prose": ("novel-review", "draft", "回到章节层做文风与表达修订"),
    "retention": ("novel-craft", "outline", "重排章末钩子、悬念间隔和完读节奏"),
}


def chapter_number_from_path(path):
    match = re.search(r"第0*(\d+)章", os.path.basename(path))
    return int(match.group(1)) if match else None


def chapter_sort_key(path):
    number = chapter_number_from_path(path)
    return (number is None, number or 0, os.path.basename(path))


def validate_assessment(assessment):
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
    return errors


def build_next_actions(verdict, processed_scores):
    if verdict == "弃稿重立":
        return [{
            "priority": "should",
            "recommended_skill": "novel-create",
            "return_to_stage": "setup",
            "action": "核心创意保留，更换题材或主线重开",
        }]

    weak_sorted = sorted(processed_scores, key=lambda s: (s["raw_score"], -s["weight"]))
    threshold = 7.5 if verdict == "大改" else (8.2 if verdict == "小改" else 7.0)
    actions = []
    for score_item in weak_sorted:
        if score_item["raw_score"] > threshold:
            continue
        skill, stage, action = ACTION_BY_DIMENSION.get(
            score_item["dimension"],
            ("novel-review", "review", "按低分维度做专项修订"),
        )
        actions.append({
            "priority": "must" if verdict in {"大改", "小改"} else "could",
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


def get_tier_verdict(total_score):
    if total_score >= 85:
        return "爆款潜力", "过", "high"
    elif total_score >= 70:
        return "合格偏上", "小改", "high"
    elif total_score >= 55:
        return "及格线下", "大改", "medium"
    else:
        return "不及格", "弃稿重立", "low"


def build_prompt(root, meta, settings, baseline, chapters, platform_mode, first_party=None, reader_panel=None, task_id="__SCORE_TASK_ID__"):
    # This function generates a prompt for the LLM to perform the assessment
    # In a real automation, this would be sent to an LLM API.

    baseline_summary = "无（请先运行 collect_market_baseline.py）"
    if baseline:
        sources = [f"- {s['platform']}: {', '.join(s.get('signals', [])[:10])}" for s in baseline.get("sources", [])]
        baseline_summary = "\n".join(sources)

    rubric_text = "（详见 novel-score/references/rubric.md）"

    prompt = f"""# 小说评分体检任务

请作为专业的小说编辑和市场专家，对以下小说内容进行深度打分。

## 项目背景
- 标题：{meta.get('title') or '未定'}
- 题材：{meta.get('genre') or '未定'}
- 目标平台：{settings.get('目标平台') or '红果/抖音 商业爽文向'}
- 评分权重档：{platform_mode}

## 市场基准（当前热榜信号 · 外部公榜）
{baseline_summary}

## 第一方题材战绩（自有投放回灌 · n2d-feedback 闭环）
{first_party_genre_text(first_party)}

## 模拟读者留存信号（novel-simulate 虚拟试读 · retention 维度先验）
{reader_panel_text(reader_panel)}

## 评估内容
{chr(10).join(f"### 第{c['num']}章 {c['title']}\n{c['content'][:1000]}..." for c in chapters)}

## 任务要求
请根据上述内容，对照评分细则（rubric.md），对以下七个维度给出 1-10 的原始分，并提供证据（原文引文）和短评。
同时检查是否有「雷点扣分项」（开篇慢热、题材退潮、主角降智、注水、三观雷、AI味、烂尾）。

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
    ... (其余6个维度)
  ],
  "deductions": [
    {{
      "item": "雷点名称",
      "points": -5,
      "reason": "..."
    }}
  ]
}}
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
    lines.append(f"| **总分** | - | - | **{total_score:.1f}** |")
    lines.append("")
    lines.append(f"- **档位**：{tier}")
    lines.append(f"- **判定**：{verdict}")
    lines.append(f"- **改写 ROI**：{roi}")
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
    ap.add_argument("--platform", default=None, help="商业爽文向 | 品质向")
    ap.add_argument("--scope", default="opening", choices=["full", "opening", "arc"])
    ap.add_argument("--mock-assessment", help="提供模拟评估 JSON 的路径，用于测试或手动注入")
    ap.add_argument("--task", default=None,
                    help="score_task.json 路径；缺省 <作品根>/评分/score_task.json")
    ap.add_argument("--json", action="store_true", help="输出机器可读报告")
    ap.add_argument("--genre-ledger", help=f"自有题材战绩库路径（n2d-feedback --emit-ledger 写）；默认 $N2D_GENRE_LEDGER 或 <repo>/{LEDGER_REL_PATH}")
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
        print("      先运行：python3 skills/novel-score/scripts/collect_market_baseline.py "
              f"\"{os.path.join(root, '评分')}\" --target-platform \"<目标平台>\" --allow-fetch-errors",
              file=sys.stderr)
        sys.exit(2)
    pending_waiver = None
    if freshness["blocking"] and args.allow_stale_baseline:
        pending_waiver = make_freshness_waiver(freshness)
    ledger_path = args.genre_ledger or default_ledger_path(root)
    first_party = summarize_first_party_genre(load_genre_ledger(ledger_path), meta.get("genre"))
    reader_panel = load_reader_panel_signals(root)

    platform_mode = args.platform or settings.get("目标平台") or "商业爽文向"
    if "品质" in platform_mode:
        platform_mode = "品质向"
    else:
        platform_mode = "商业爽文向"

    weights = WEIGHTS.get(platform_mode, WEIGHTS["商业爽文向"])

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

    source_snapshot = (
        snapshot_files(root, sample_paths, mode=f"score:{args.scope}")
        if snapshot_files else None
    )
    market_snapshot = baseline_file_snapshot(root, baseline)
    prompt = build_prompt(
        root, meta, settings, baseline, samples, platform_mode, first_party, reader_panel,
        task_id="__SCORE_TASK_ID__",
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
        print("--- LLM SCORING PROMPT ---")
        print(expected_task["assessment_prompt"])
        print("--- END PROMPT ---")
        print(f"\n[info] score_task 已写入：{task_path}")
        print("[info] 请根据上述 prompt 获取 LLM 评估 JSON，并使用 --mock-assessment 注入结果。")
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
    errors = validate_assessment(assessment)
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

    deductions = assessment.get("deductions", [])
    total_deductions = sum(d["points"] for d in deductions)
    final_score = max(0.0, total_weighted + total_deductions)
    tier, verdict, roi = get_tier_verdict(final_score)

    next_actions = build_next_actions(verdict, processed_scores)
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
        "target_platform": platform_mode,
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
            "expires_after_days": baseline.get("expires_after_days") if baseline else None,
            "freshness": freshness,
            "snapshot": task.get("market_baseline_snapshot"),
        },
        "first_party_genre": first_party,
        "genre_ledger_path": ledger_path if os.path.isfile(ledger_path) else None,
        "reader_panel_path": os.path.join(READER_PANEL_REL_PATH) if reader_panel else None,
        "scores": processed_scores,
        "deductions": deductions,
        "total_deductions": total_deductions,
        "total_score": final_score,
        "tier": tier,
        "verdict": verdict,
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

    print(f"[ok] 评分报告 JSON → {os.path.join(score_dir, 'score_report.json')}")
    print(f"[ok] 评分报告 MD   → {md_path}")
    print(f"     总分：{final_score:.1f} | 档位：{tier} | 判定：{verdict}")


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
