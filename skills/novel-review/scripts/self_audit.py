#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local process self-audit for the novel-* skill family.

This script is report-only: it reads skill files and optional project artifacts,
then prints findings. It does not fetch network data and does not edit files.
"""
import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from glob import glob


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SKILLS = os.path.join(REPO, "skills")
CRAFT_SCRIPTS = os.path.join(SKILLS, "novel-craft", "scripts")
NOVEL_LIB = os.path.join(SKILLS, "novel", "_lib")
for _path in (NOVEL_LIB, CRAFT_SCRIPTS):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import novel_contract as contract  # noqa: E402
import registry  # noqa: E402

try:
    import friction_log  # noqa: E402  novel/_lib 生产摩擦埋点
except ImportError:
    friction_log = None


def read(relpath):
    with open(os.path.join(REPO, relpath), encoding="utf-8") as f:
        return f.read()


def rel(path):
    return os.path.relpath(path, REPO)


def actual_novel_skills():
    return {
        name for name in os.listdir(SKILLS)
        if (name == "novel" or name.startswith("novel-"))
        and os.path.isfile(os.path.join(SKILLS, name, "SKILL.md"))
    }


def referenced_novel_skills(text):
    return set(re.findall(r"`(novel(?:-[a-z-]+)?)(?:/[^`]*)?`", text))


def finding(severity, fid, title, detail, fix=None):
    return {
        "severity": severity,
        "id": fid,
        "title": title,
        "detail": detail,
        "fix": fix or "",
    }


def baseline_has_effective_evidence(baseline):
    for item in baseline.get("manual_evidence") or []:
        if not isinstance(item, dict):
            continue
        required = ("platform", "date", "source", "summary")
        if all(str(item.get(field) or "").strip() for field in required):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(item.get("date") or "")):
                return True
    for source in baseline.get("sources") or []:
        if not isinstance(source, dict):
            continue
        status = str(source.get("status") or "").strip().lower()
        signals = source.get("signals") or []
        if status == "ok" and any(str(signal).strip() for signal in signals):
            return True
    return False


def latest_market_baseline(project_root):
    files = sorted(glob(os.path.join(project_root, "评分", "market_baseline_*.json")))
    return files[-1] if files else None


def audit_market_baseline(project_root):
    if not project_root:
        return [finding(
            "info",
            "MARKET-NO-PROJECT",
            "未检查项目级市场基准",
            "未传 --project-root；本地流程自审只检查 skill 治理项。",
            "对具体作品自审时加 --project-root <创作区/写小说/项目>，脚本会检查评分基准新鲜度。",
        )]
    path = latest_market_baseline(project_root)
    if not path:
        return [finding(
            "warn",
            "MARKET-MISSING",
            "缺少市场基准",
            f"{rel(project_root)} 下没有 评分/market_baseline_*.json。",
            "运行 novel-score/scripts/collect_market_baseline.py 后再做市场/题材判断。",
        )]
    try:
        with open(path, encoding="utf-8") as f:
            baseline = json.load(f)
    except Exception as exc:
        return [finding("warn", "MARKET-INVALID", "市场基准无法读取", f"{rel(path)}: {exc}")]
    raw_date = baseline.get("baseline_date")
    try:
        base_date = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return [finding("warn", "MARKET-DATE", "市场基准日期无效", f"{rel(path)} baseline_date={raw_date!r}")]
    expires_after = int(baseline.get("expires_after_days") or 21)
    expires_on = base_date + timedelta(days=expires_after)
    out = []
    if date.today() > expires_on:
        out.append(finding(
            "warn",
            "MARKET-STALE",
            "市场基准已过期",
            f"{rel(path)}: {raw_date} + {expires_after} 天 < {date.today().isoformat()}。",
            "重新采集基准，不要沿用旧热榜做题材判断。",
        ))
    if not baseline_has_effective_evidence(baseline):
        out.append(finding(
            "warn",
            "MARKET-NO-EVIDENCE",
            "市场基准缺少有效证据",
            f"{rel(path)} 没有 status=ok 且 signals 非空的来源，也没有结构化 manual_evidence。",
            "补充有效榜单来源或 manual_evidence（platform/date/source/summary）。",
        ))
    if not out:
        out.append(finding("info", "MARKET-FRESH", "市场基准可用", f"{rel(path)} fresh until {expires_on.isoformat()}"))
    return out


def audit_optimization_signals(project_root):
    """摄入生产线埋点：评分等阶段写入 生产数据/优化信号.jsonl 的流程摩擦信号。
    每条未解决（status=open）的信号都翻成一条自审 finding，让"再次运行就触发自我优化"成闭环。
    严重度映射：block→block、warn→warn、其余→info。"""
    if not project_root:
        return []
    if friction_log is None:
        return [finding(
            "info", "FRICTION-NO-LIB", "未加载摩擦埋点库",
            "novel/_lib/friction_log 不可导入；跳过生产摩擦信号摄入。",
        )]
    signals = [s for s in friction_log.load_signals(project_root)
               if str(s.get("status") or "open") == "open"]
    if not signals:
        return [finding(
            "info", "FRICTION-NONE", "无未解决的生产摩擦信号",
            f"{rel(project_root)}/生产数据/优化信号.jsonl 无 open 信号（或文件不存在）。",
        )]
    sev_map = {"block": "block", "warn": "warn"}
    out = []
    for s in signals:
        sev = sev_map.get(str(s.get("severity") or ""), "info")
        out.append(finding(
            sev,
            f"FRICTION-{str(s.get('kind') or 'UNKNOWN').upper().replace('_', '-')}",
            f"[{s.get('skill')}] {s.get('title')}",
            str(s.get("detail") or ""),
            s.get("suggested_fix") or "",
        ))
    return out


def audit_registry():
    expected = set(registry.skill_names())
    actual = actual_novel_skills()
    out = []
    if expected != actual:
        out.append(finding(
            "block",
            "REGISTRY-MISMATCH",
            "novel registry 与磁盘 skill 不一致",
            f"registry-only={sorted(expected - actual)}; disk-only={sorted(actual - expected)}",
            "更新 novel-craft/scripts/registry.py，或同步新增/删除的 skill 目录。",
        ))
    author_refs = referenced_novel_skills(read("skills/novel/SKILL.md"))
    readme_refs = referenced_novel_skills(read("skills/README.md"))
    if author_refs != expected:
        out.append(finding(
            "block",
            "AUTHOR-ROUTE-DRIFT",
            "novel 路由表与 registry 不一致",
            f"missing={sorted(expected - author_refs)}; extra={sorted(author_refs - expected)}",
            "同步 novel/SKILL.md 路由表。",
        ))
    if readme_refs != expected:
        out.append(finding(
            "block",
            "README-ROUTE-DRIFT",
            "skills/README.md novel 索引与 registry 不一致",
            f"missing={sorted(expected - readme_refs)}; extra={sorted(readme_refs - expected)}",
            "同步 skills/README.md novel 索引。",
        ))
    if not out:
        out.append(finding("info", "REGISTRY-OK", "novel skill roster 已同步", f"{len(expected)} skills"))
    return out


def audit_progress_and_ledgers():
    progress = read("skills/novel-craft/scripts/progress.py")
    draft_packets = read("skills/novel-craft/scripts/draft_packets.py")
    reconcile = read("skills/novel-craft/scripts/reconcile_ledger.py")
    out = []
    required_progress = ("def set_stage", "progress_lock_path", "file_lock(", "atomic_write_text")
    missing = [token for token in required_progress if token not in progress]
    if missing:
        out.append(finding(
            "block",
            "PROGRESS-WRITER-MISSING",
            "_进度.md 缺少统一写入口",
            f"progress.py missing tokens: {missing}",
            "实现 progress.py set <root> <stage> done|todo，并加锁原子写（需补齐 file_lock 等缺失依赖）。",
        ))
    else:
        out.append(finding("info", "PROGRESS-WRITER-OK", "_进度.md 有加锁写入口", "progress.py set"))

    for script_name, text in (("draft_packets.py", draft_packets), ("reconcile_ledger.py", reconcile)):
        missing = [token for token in ("state_ledger.lock", "atomic_write_json", "file_lock(") if token not in text]
        if missing:
            out.append(finding(
                "block",
                f"LEDGER-SAFE-WRITE-{script_name}",
                f"{script_name} 未统一保护 state_ledger.json",
                f"missing tokens: {missing}",
                "state_ledger.json 是跨章真值源，所有写入需 lock + atomic replace。",
            ))
    if not any(item["id"].startswith("LEDGER-SAFE-WRITE") for item in out):
        out.append(finding("info", "LEDGER-SAFE-WRITE-OK", "state_ledger 写入已加锁原子化", "draft_packets + reconcile_ledger"))
    return out


def audit_batch_queue_and_docs():
    out = []
    queue_script = os.path.join(REPO, "skills/novel-craft/scripts/draft_queue.py")
    queue_test = os.path.join(REPO, "skills/novel-craft/scripts/test_draft_queue.py")
    batch_skill = os.path.join(REPO, "skills/novel-batch/SKILL.md")
    batch_queue = os.path.join(REPO, "skills/novel-batch/scripts/queue.py")
    batch_test = os.path.join(REPO, "skills/novel-batch/scripts/test_queue.py")
    craft = read("skills/novel-craft/SKILL.md")
    create = read("skills/novel-create/SKILL.md")
    if not os.path.exists(queue_script):
        out.append(finding("block", "DRAFT-QUEUE-MISSING", "缺少批量写章队列脚本", rel(queue_script)))
    if not os.path.exists(queue_test):
        out.append(finding("warn", "DRAFT-QUEUE-TEST-MISSING", "缺少 draft_queue 测试", rel(queue_test)))
    if "draft_queue.py" not in craft or "draft_queue.py" not in create:
        out.append(finding(
            "warn",
            "DRAFT-QUEUE-DOCS",
            "批量写章队列未写进关键文档",
            "novel-craft/SKILL.md 与 novel-create/SKILL.md 应提示 claim/done 流程。",
            "同步两个 SKILL.md，避免继续只用 --range 手工分配。",
        ))
    if not os.path.exists(batch_skill):
        out.append(finding("block", "NOVEL-BATCH-SKILL-MISSING", "novel-batch 缺少 SKILL.md", rel(batch_skill)))
    if not os.path.exists(batch_queue):
        out.append(finding("block", "NOVEL-BATCH-QUEUE-MISSING", "novel-batch 缺少 queue.py", rel(batch_queue)))
    else:
        text = open(batch_queue, encoding="utf-8").read()
        missing = [token for token in ("lease_expires_at", "dead_letter", "reclaim", "idempotency_key", "flock") if token not in text]
        if missing:
            out.append(finding(
                "block",
                "NOVEL-BATCH-QUEUE-WEAK",
                "novel-batch 队列缺少工业化协调能力",
                f"missing tokens: {missing}",
                "保留 claim/lease/reclaim/dead-letter/idempotent plan 的本地队列能力。",
            ))
    if not os.path.exists(batch_test):
        out.append(finding("warn", "NOVEL-BATCH-TEST-MISSING", "novel-batch 缺少队列测试", rel(batch_test)))
    if not out:
        out.append(finding("info", "DRAFT-QUEUE-OK", "批量写章队列已落地", "draft_queue.py + docs + test"))
        out.append(finding("info", "NOVEL-BATCH-OK", "novel-batch 本地批量队列已落地", "queue.py + SKILL.md + test"))
    return out


def audit_self_audit_docs():
    review = read("skills/novel-review/SKILL.md")
    reference = read("skills/novel-review/references/self_audit.md")
    out = []
    if "scripts/self_audit.py" not in review:
        out.append(finding("warn", "SELF-AUDIT-DOCS", "novel-review 未指向 self_audit.py", "SKILL.md 缺少命令入口。"))
    if "scripts/self_audit.py" not in reference:
        out.append(finding("warn", "SELF-AUDIT-REF", "self_audit reference 未指向脚本入口", "references/self_audit.md 缺少命令入口。"))
    if not out:
        out.append(finding("info", "SELF-AUDIT-OK", "流程自审已有本地脚本入口", "novel-review/scripts/self_audit.py"))
    return out


def audit_contract():
    out = []
    create_keys = [stage["key"] for stage in contract.CREATE_STAGE_TABLE]
    derived_keys = [stage["key"] for stage in contract.DERIVED_STAGE_TABLE]
    if len(create_keys) != len(set(create_keys)):
        out.append(finding("block", "CONTRACT-CREATE-DUP", "原创阶段 key 重复", str(create_keys)))
    if len(derived_keys) != len(set(derived_keys)):
        out.append(finding("block", "CONTRACT-DERIVED-DUP", "派生阶段 key 重复", str(derived_keys)))
    if not out:
        out.append(finding(
            "info",
            "CONTRACT-OK",
            "阶段契约 key 唯一",
            f"create={len(create_keys)}, derived={len(derived_keys)}",
        ))
    return out


# mock/占位实现的招牌特征：声称"待实现"却被当真接进流程，或返回伪造常量让 gate 误信。
# 治本病灶——本批审查里 graph_sentry 恒 clean、research_rag 恒 score:0.95 就是这类。
_MOCK_MARKERS = re.compile(
    r"mock for now|pending\s+(full|vector|graph)\b.*implementation|mock result|mock rag|"
    r"return\s+a\s+fake|placeholder\s+implementation",
    re.IGNORECASE,
)


def audit_mock_stubs():
    """扫 novel-* 脚本里的 mock/占位招牌，防"mock 冒充实现接进流程/gate"回潮。report-only。"""
    out = []
    flagged = []
    roots = [SKILLS]
    for skill_dir in sorted(glob(os.path.join(SKILLS, "novel*"))):
        for sub in ("scripts", "_lib", ""):
            for path in glob(os.path.join(skill_dir, sub, "*.py")):
                base = os.path.basename(path)
                if base.startswith("test_") or base == "self_audit.py":
                    continue  # 排除哨兵自身（其正则字面量含招牌词，否则自我误报）
                try:
                    text = open(path, encoding="utf-8").read()
                except Exception:
                    continue
                hit = _MOCK_MARKERS.search(text)
                if hit:
                    flagged.append((rel(path), hit.group(0)))
    if flagged:
        for path, marker in flagged:
            out.append(finding(
                "block", "MOCK-STUB-IN-FLOW",
                f"疑似 mock/占位实现：{path}",
                f"命中招牌「{marker}」。mock 不得接进流程/gate（恒定返回=静默假阴性）。",
                fix="改成真实实现，或显式 status=unimplemented/non-gating 且不返回伪造数据。",
            ))
    else:
        out.append(finding("info", "MOCK-STUB-OK", "novel 脚本无 mock 招牌残留", "graph_sentry/research_rag 已落地真实实现"))
    return out


def run_audit(project_root=None):
    findings = []
    findings.extend(audit_registry())
    findings.extend(audit_progress_and_ledgers())
    findings.extend(audit_batch_queue_and_docs())
    findings.extend(audit_self_audit_docs())
    findings.extend(audit_contract())
    findings.extend(audit_mock_stubs())
    findings.extend(audit_market_baseline(project_root))
    findings.extend(audit_optimization_signals(project_root))
    summary = {
        "block": sum(1 for item in findings if item["severity"] == "block"),
        "warn": sum(1 for item in findings if item["severity"] == "warn"),
        "info": sum(1 for item in findings if item["severity"] == "info"),
    }
    return {
        "schema_version": 1,
        "kind": "novel_process_self_audit",
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(project_root) if project_root else "",
        "summary": summary,
        "findings": findings,
    }


def print_text(report):
    print("# novel process self-audit")
    summary = report["summary"]
    print(f"[summary] block={summary['block']} warn={summary['warn']} info={summary['info']}")
    for item in report["findings"]:
        print(f"- {item['severity'].upper()} {item['id']}: {item['title']}")
        print(f"  {item['detail']}")
        if item.get("fix"):
            print(f"  fix: {item['fix']}")


def main():
    ap = argparse.ArgumentParser(description="本地静态审查 novel-* skill 家族治理项")
    ap.add_argument("--project-root", help="可选：同时检查该作品的市场基准新鲜度")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fail-on-block", action="store_true")
    args = ap.parse_args()

    report = run_audit(args.project_root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text(report)
    if args.fail_on_block and report["summary"]["block"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
