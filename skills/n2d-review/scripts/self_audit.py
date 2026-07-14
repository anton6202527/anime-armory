#!/usr/bin/env python3
"""Local static self-audit for the n2d skill family.

This is the report-only half of `n2d-review` mode 2.  It does not fetch market
benchmarks and does not edit files; it checks that the local production
pipeline stays aligned around the current engineering guardrails.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


Finding = Dict[str, Any]


IMAGE_BACKEND_DOCS = (
    "skills/n2d/references/选择点与偏好.md",
    "skills/README.md",
    "skills/n2d-image/SKILL.md",
    "skills/n2d-review/references/checklist.md",
)

IMAGE_BACKEND_DOC_ALIASES = {
    "codex": ("Codex",),
    "openai": ("OpenAI", "gpt-image", "DALL"),
    "dreamina": ("Dreamina", "即梦"),
    "gemini": ("Nano Banana", "Gemini"),
    "seedream": ("Seedream",),
    "kling": ("Kling", "可灵"),
    "sora": ("Sora",),
}


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parents[3]


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def add(findings: List[Finding], sev: str, dim: str, loc: str, msg: str, suggestion: str = "") -> None:
    findings.append({"sev": sev, "dim": dim, "loc": loc, "msg": msg, "suggestion": suggestion})


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def load_contract(root: Path):
    path = root / "skills" / "n2d" / "_lib" / "n2d_contract.py"
    if not path.is_file():
        return None, None
    # n2d_contract.py 是 facade，内部 `from n2d_const import *` 需要 _lib 在 sys.path 上
    # （否则回退到相对导入又因无包父级失败）。与 gate.py 同源做法。
    lib_dir = str(path.parent)
    # 关键隔离：facade 的 `from n2d_const import *` 等会按模块名查 sys.modules，
    # 若同名模块已被「自审工具自身所在仓」缓存，就会顶替掉**本 root** 的 _lib，
    # 读到错的 APPROVED_IMAGE_BACKENDS（单进程跑多 root / 测试套时复现）。
    # 故先驱逐本 root _lib 同名模块、加载完再还原，保证 facade 从本 root 取符号。
    lib_modules = {p.stem for p in path.parent.glob("*.py")}
    saved = {name: sys.modules.pop(name) for name in list(sys.modules) if name in lib_modules}
    added = lib_dir not in sys.path
    if added:
        sys.path.insert(0, lib_dir)
    try:
        spec = importlib.util.spec_from_file_location("_n2d_self_audit_contract", path)
        if spec is None or spec.loader is None:
            return None, "无法加载 n2d_contract.py"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, None
    except Exception as exc:  # pragma: no cover - defensive report path
        return None, str(exc)
    finally:
        if added and sys.path and sys.path[0] == lib_dir:
            sys.path.pop(0)
        # 移除本次加载引入的本 root 同名模块，再还原外层缓存——不污染调用方。
        for name in lib_modules:
            sys.modules.pop(name, None)
        sys.modules.update(saved)


def backend_aliases(key: str, spec: Dict[str, Any]) -> Sequence[str]:
    aliases = list(IMAGE_BACKEND_DOC_ALIASES.get(key, (key,)))
    label = str(spec.get("label") or "")
    if label:
        aliases.append(label.split("/")[0].split("（")[0].split("(")[0].strip())
    return [item for item in aliases if item]


def has_any(raw: str, aliases: Sequence[str]) -> bool:
    lowered = raw.lower()
    return any(alias.lower() in lowered for alias in aliases)


def iter_docs(root: Path) -> Iterable[Path]:
    skill_root = root / "skills"
    patterns = [
        "README.md",
        "n2d/**/*.md",
        "n2d-*/**/*.md",
    ]
    seen = set()
    for pattern in patterns:
        base = root if pattern == "README.md" else skill_root
        for path in base.glob(pattern):
            if path.is_file() and path not in seen:
                seen.add(path)
                yield path


def check_gate_entry(root: Path, findings: List[Finding]) -> None:
    """Production docs should use dashboard.py gate; bare gate.py is debug/json only."""
    bare = re.compile(r"(?:python3\s+skills/)?n2d-review/scripts/gate\.py\s+[^`\n]*--stage\s+(image|video|compose|review)(?![^`\n]*--json)")
    hits = []
    for path in iter_docs(root):
        for idx, line in enumerate(text(path).splitlines(), start=1):
            if bare.search(line):
                hits.append(f"{rel(root, path)}:{idx}")
    if hits:
        add(
            findings,
            "warn",
            "gate 单入口",
            ", ".join(hits[:8]),
            f"发现 {len(hits)} 处生产文档仍推荐裸 gate.py，可能漏写 dashboard QA telemetry。",
            "改为 `python3 skills/n2d-dashboard/scripts/dashboard.py gate ...`；`gate.py --json` 只保留为调试/机器消费入口。",
        )
    else:
        add(findings, "info", "gate 单入口", "skills/", "生产文档已统一推荐 dashboard.py gate。")


def check_progress_lock(root: Path, findings: List[Finding]) -> None:
    path = root / "skills" / "n2d" / "progress.py"
    raw = text(path)
    missing = [name for name in ("progress_lock", "atomic_write_text", "os.replace") if name not in raw]
    if missing:
        add(
            findings,
            "block",
            "进度并发安全",
            rel(root, path),
            f"progress.py 缺少并发安全要素：{', '.join(missing)}。",
            "给 `_进度.md` 的 set/ensure-col 加锁内读改写 + 同目录 temp + os.replace。",
        )
    else:
        add(findings, "info", "进度并发安全", rel(root, path), "`_进度.md` 写入已具备锁和原子替换。")


def check_cross_cutting_coverage(root: Path, findings: List[Finding]) -> None:
    path = root / "skills" / "n2d-progress" / "scan.py"
    raw = text(path)
    required = ("coverage_status", "episode_coverage", '"*" in art')
    missing = [name for name in required if name not in raw]
    if missing:
        add(
            findings,
            "warn",
            "横切覆盖率",
            rel(root, path),
            f"横切就绪检查仍可能是命中即 ✅，缺少覆盖率实现标志：{', '.join(missing)}。",
            "score/review-ui/dashboard 等逐集横切产物应显示 `N/M` 覆盖，而不是整部只要命中一次就 ✅。",
        )
    else:
        add(findings, "info", "横切覆盖率", rel(root, path), "n2d-progress 已具备逐集覆盖率输出。")


def check_benchmark_external(root: Path, findings: List[Finding]) -> None:
    path = root / "skills" / "n2d-dashboard" / "references" / "industry_benchmark.json"
    if not path.is_file():
        add(
            findings,
            "warn",
            "行业基准外置",
            rel(root, path),
            "行业基准文件不存在，默认基准可能仍硬编码在 Python 常量里。",
            "把只读行业基准放入 references/industry_benchmark.json，代码只负责加载和项目覆盖。",
        )
        return
    try:
        data = json.loads(text(path))
    except json.JSONDecodeError as exc:
        add(findings, "block", "行业基准外置", rel(root, path), f"行业基准 JSON 无法解析：{exc}")
        return
    missing = [key for key in ("collected", "sources", "one_pass_rate", "redraw_rate") if key not in data]
    if missing:
        add(findings, "warn", "行业基准外置", rel(root, path), f"行业基准缺少字段：{', '.join(missing)}")
    else:
        add(findings, "info", "行业基准外置", rel(root, path), "行业基准已外置，并带采集日期/来源字段。")


def check_image_backend_docs(root: Path, findings: List[Finding]) -> None:
    contract, error = load_contract(root)
    path = root / "skills" / "n2d" / "_lib" / "n2d_contract.py"
    if error:
        # 工具自身 import 失败 ≠ 内容合规问题：用独立维度，避免把自审引擎故障伪装成生图后端 block
        add(findings, "block", "自审引擎错误", rel(root, path),
            f"无法导入 n2d_contract.py（自审工具故障，非作品问题，请修脚本环境）：{error}")
        return
    if contract is None:
        add(findings, "info", "生图后端白名单", rel(root, path), "未找到 n2d_contract.py，跳过白名单文档一致性检查。")
        return
    approved = getattr(contract, "APPROVED_IMAGE_BACKENDS", None)
    if not isinstance(approved, dict) or not approved:
        add(findings, "warn", "生图后端白名单", rel(root, path), "APPROVED_IMAGE_BACKENDS 缺失或为空。")
        return

    missing_docs = []
    forbidden_context = []
    allowed_forbidden_context = re.compile(r"(禁|阻断|旧|含糊|第三方|未授权|不得|移除|改成|忽略|拦|禁止)", re.I)
    for rel_doc in IMAGE_BACKEND_DOCS:
        doc_path = root / rel_doc
        if not doc_path.is_file():
            continue
        raw = text(doc_path)
        missing = []
        for key, spec in approved.items():
            if not has_any(raw, backend_aliases(str(key), spec)):
                missing.append(str(spec.get("label") or key))
        if missing:
            missing_docs.append(f"{rel_doc} 缺 {', '.join(missing)}")
        for idx, line in enumerate(raw.splitlines(), start=1):
            if "同视频AI" in line and not allowed_forbidden_context.search(line):
                forbidden_context.append(f"{rel_doc}:{idx}")

    if missing_docs or forbidden_context:
        locs = []
        if missing_docs:
            locs.extend(missing_docs[:4])
        if forbidden_context:
            locs.append("疑似放行同视频AI: " + ", ".join(forbidden_context[:6]))
        add(
            findings,
            "warn",
            "生图后端白名单",
            "; ".join(locs),
            "生图后端文档与 APPROVED_IMAGE_BACKENDS 不完全一致，可能重新制造后端口径分叉。",
            "从 `skills/n2d/_lib/n2d_contract.py` 的 APPROVED_IMAGE_BACKENDS 刷新选择点、n2d-image 说明和 review checklist；`同视频AI` 只能作为禁用/旧值迁移语境出现。",
        )
    else:
        add(findings, "info", "生图后端白名单", "skills/n2d/_lib/n2d_contract.py", "关键文档已覆盖 APPROVED_IMAGE_BACKENDS，且未把 `同视频AI` 当作可选后端。")


def check_large_docs(root: Path, findings: List[Finding]) -> None:
    docs = (
        (root / "skills" / "n2d" / "SKILL.md", 400, "长规则优先沉到 references/，SKILL.md 保持路由和关键命令。"),
        (root / "skills" / "n2d" / "Q&A.md", 1500, "Q&A 是沉淀库；超过阈值时再分卷或按主题拆 references。"),
    )
    for path, warn_after, suggestion_text in docs:
        if not path.is_file():
            continue
        n = len(text(path).splitlines())
        sev = "warn" if n > warn_after else "info"
        msg = f"{rel(root, path)} 当前 {n} 行。"
        suggestion = suggestion_text if sev == "warn" else ""
        add(findings, sev, "文档体量", rel(root, path), msg, suggestion)


def load_friction_module(root: Path):
    """加载 n2d_friction（纯 stdlib，无 `from n2d_const import *`，可直接按文件 spec 导入，
    无需 load_contract 的 sys.path 隔离舞蹈）。失败返回 (None, 原因)。"""
    path = root / "skills" / "n2d" / "_lib" / "n2d_friction.py"
    if not path.is_file():
        return None, "n2d_friction.py 不存在"
    try:
        spec = importlib.util.spec_from_file_location("_n2d_self_audit_friction", str(path))
        if spec is None or spec.loader is None:
            return None, "无法加载 n2d_friction.py"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)


def load_charter_module(root: Path):
    """加载 consistency_charter（同目录·纯 stdlib，clean import）。失败返回 (None, 原因)。"""
    path = root / "skills" / "n2d-review" / "scripts" / "consistency_charter.py"
    if not path.is_file():
        return None, "consistency_charter.py 不存在"
    try:
        spec = importlib.util.spec_from_file_location("_n2d_self_audit_charter", str(path))
        if spec is None or spec.loader is None:
            return None, "无法加载 consistency_charter.py"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as exc:  # pragma: no cover - defensive
        return None, str(exc)


def load_meta_audit_module(root: Path):
    """Load the independent claim/adversarial meta-audit.

    It intentionally lives in a separate module so the ordinary inventory does
    not certify its own coverage logic.  The module is stdlib-only and
    report-only; import failures are surfaced as governance warnings rather
    than hidden behind a green self-check.
    """
    path = root / "skills" / "n2d-review" / "scripts" / "meta_audit.py"
    if not path.is_file():
        return None, "meta_audit.py 不存在"
    try:
        spec = importlib.util.spec_from_file_location("_n2d_review_meta_audit", str(path))
        if spec is None or spec.loader is None:
            return None, "无法加载 meta_audit.py"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, None
    except Exception as exc:  # pragma: no cover - defensive report path
        return None, str(exc)


def check_consistency_charter(root: Path, findings: List[Finding]) -> None:
    """对照一致性不变量 charter 审 gate.py 源码：locked 闸被悄悄 profile 门控=block；
    被未披露降级的 disputed 闸 + opt-in 默认关项报出来等裁决（治"硬闸被时间维度弱化")。"""
    mod, error = load_charter_module(root)
    gate_py = root / "skills" / "n2d-review" / "scripts" / "gate.py"
    if error:
        add(findings, "info", "一致性charter", "skills/n2d-review/scripts/consistency_charter.py",
            f"charter 模块加载失败，跳过强制力审计：{error}", "")
        return
    if not gate_py.is_file():
        add(findings, "info", "一致性charter", rel(root, gate_py), "gate.py 不存在，跳过。", "")
        return
    # 多文件源码全集：gate.py + gates/*.py（按证据族拆分后 locked 闸可能迁出 gate.py，必须看全集）。
    gate_src = mod.gate_source_text(gate_py.parent)
    violations = mod.audit_source(gate_src)
    locked = mod.locked_gates()
    for v in violations:
        sev = "block" if v["kind"] in ("profile_gated", "missing_gate") else "warn"
        add(findings, sev, "一致性charter", f"gate.py:{v['gate']}", v["problem"],
            "修回无条件 BLOCK；若确为有意降级，先改 consistency_charter.py 该闸为 disputed 并留痕（别直接改 gate.py）。")
    disputed = mod.disputed_entries()
    for name, e in disputed.items():
        tag = "被未披露降级·待裁决" if e.get("review_status") == "disputed_downgrade" else "opt-in 默认关·候选升默认"
        add(findings, "warn", "一致性charter", f"gate.py:{name}",
            f"[{tag}] {e.get('dim')}：{e.get('rationale')}",
            "人裁决：要么把 may_be_profile_gated/may_be_opt_in 翻 False 并重新硬化 gate.py，要么确认保持现状并填 decided 日期。")
    if not violations:
        add(findings, "info", "一致性charter", "skills/n2d-review/scripts/consistency_charter.py",
            f"{len(locked)} 个 locked 一致性硬闸源码核对通过（无被悄悄 profile 门控），{len(disputed)} 项 disputed/opt-in 待裁决。", "")


def check_friction_backlog(root: Path, work_root: Path, findings: List[Finding]) -> None:
    """流程自审消费端：读某作品 `生产数据/优化信号.jsonl`，把现场摩擦信号逐簇并进差距清单。

    只读不写——保住 mode② "不归档自审报告" 立场（信号是 per-work 生产数据，不是自审报告）。
    每个 (skill, 信号种类) 簇产一行：loc=该改哪个 skill 哪段，suggestion=现场给的改法。
    """
    mod, error = load_friction_module(root)
    if error:
        add(findings, "info", "现场摩擦信号", "skills/n2d/_lib/n2d_friction.py",
            f"采集模块加载失败，跳过现场信号扫描：{error}", "")
        return
    records = mod.read_friction(str(work_root))
    if not records:
        add(findings, "info", "现场摩擦信号", rel(root, work_root / mod.PRODUCTION_DIRNAME),
            f"本作 `{work_root.name}` 暂无积压现场摩擦信号（生产时各 skill 未上报 `该改` 信号）。", "")
        return
    summary = mod.summarize_friction(records)
    sev_map = {"info": "info", "warn": "warn", "block": "block"}
    for c in summary["clusters"]:
        skill = c["skill"]
        loc = f"{skill}" + (f"（{c['latest_ts'][:10]}）" if c.get("latest_ts") else "")
        ev = "；证据 " + ", ".join(c["evidence"][:3]) if c.get("evidence") else ""
        msg = (f"生产现场上报 {c['count']} 条「{c['signal_kind']}」信号：{c['latest_what']}{ev}")
        suggestion = c.get("latest_proposed") or "对照证据定位到该 skill 对应阶段，过 run_all_checks 后改源头。"
        add(findings, sev_map.get(c["severity"], "warn"), "现场摩擦信号", loc, msg, suggestion)


def check_detector_inventory(root: Path, findings: List[Finding]) -> None:
    """一致性 detector 治理：跑 detector_inventory，孤儿 detector 报 warn，否则报健康 info。"""
    scripts_dir = root / "skills" / "n2d-review" / "scripts"
    loc = "skills/n2d-review/scripts/detector_inventory.py"
    inv_path = scripts_dir / "detector_inventory.py"
    if not inv_path.is_file():
        return
    try:
        spec = importlib.util.spec_from_file_location("_detector_inventory", str(inv_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        inv = mod.build_inventory(str(scripts_dir))
    except Exception as exc:  # pragma: no cover - defensive
        add(findings, "info", "detector 治理", loc, f"detector 清单跑不动：{exc}", "")
        return
    orphans = inv.get("orphans") or []
    if orphans:
        add(findings, "warn", "detector 治理", loc,
            f"{len(orphans)} 个孤儿 detector（无编排/gate/dashboard/总账/advisory/disabled/peer 治理路径）：{'、'.join(orphans)}",
            "跑 detector_inventory.py 核实，按证据判退役/合并或补接线；别让死 detector 拖维护。")
    else:
        c = inv.get("counts", {})
        add(findings, "info", "detector 治理", loc,
            f"detector 套件 {inv.get('total')} 个全部有治理路径（0 孤儿；编排 {c.get('wired', 0)}/"
            f"gate {c.get('gate', 0)}/dashboard {c.get('dashboard', 0)}/总账 {c.get('ledger', 0)}/"
            f"advisory {c.get('advisory', 0)}/disabled {c.get('disabled', 0)}/子检测 {c.get('peer', 0)}）。", "")


def check_meta_audit(
    root: Path,
    findings: List[Finding],
    *,
    fixture_paths: Sequence[Path] = (),
    evidence_paths: Sequence[Path] = (),
    run_tests: bool = False,
) -> Dict[str, Any]:
    """Run the independent five-link/adversarial audit and summarize it.

    Static meta findings are WARN at most.  They identify missing proof, not a
    deterministic defect in a production artifact, so B10 forbids turning them
    into a new hard gate.
    """
    mod, error = load_meta_audit_module(root)
    loc = "skills/n2d-review/scripts/meta_audit.py"
    if error:
        add(
            findings,
            "warn",
            "独立 meta-audit",
            loc,
            f"独立 meta-audit 未运行：{error}",
            "恢复 meta_audit.py；普通 self_audit 的 0 warn 不能替代对抗审计。",
        )
        return {
            "kind": "n2d_review_meta_audit_unavailable",
            "assurance": {
                "self_checked": {"label": "self-checked", "status": "not_run", "covered": 0, "total": 0},
                "adversarial_test_coverage": {"label": "adversarial-test-coverage", "status": "not_run", "covered": 0, "total": 0},
                "adversarially_tested": {"label": "adversarially-tested", "status": "not_run", "covered": 0, "total": 0},
                "externally_grounded": {"label": "externally-grounded", "status": "not_run", "covered": 0, "total": 0},
                "externally_calibrated": {"label": "externally-calibrated", "status": "not_run", "covered": 0, "total": 0},
                "no_blind_spot_claim_allowed": False,
                "blind_spot_statement": "独立 meta-audit 未运行；不得声称无盲区。",
            },
            "findings": [],
        }

    report = mod.audit(
        root,
        fixture_paths=[Path(p) for p in fixture_paths],
        evidence_paths=[Path(p) for p in evidence_paths],
        run_tests=run_tests,
    )
    missing_claims = []
    for claim in report.get("claims") or []:
        missing = [name for name, row in (claim.get("links") or {}).items() if row.get("status") != "covered"]
        if missing:
            missing_claims.append(f"{claim.get('id')}({','.join(missing)})")
    if missing_claims:
        add(
            findings,
            "warn",
            "声明→实现→调用→测试→反例",
            loc,
            f"{len(missing_claims)} 条关键声明的五联证据不完整：{'；'.join(missing_claims[:8])}。",
            "先补最小实现/调用链与命名明确的反例回归；静态模式只证明可追溯，不替代行为测试。",
        )
    else:
        add(
            findings,
            "info",
            "声明→实现→调用→测试→反例",
            loc,
            f"{len(report.get('claims') or [])} 条已登记关键声明的五联证据齐全。",
            "",
        )

    gaps = [probe for probe in report.get("probes") or [] if probe.get("status") != "covered"]
    if gaps:
        add(
            findings,
            "warn",
            "对抗/变形审计",
            loc,
            f"{len(gaps)} 个已知绕过类缺 guard 或反例回归："
            + "；".join(f"{p.get('id')}({','.join(p.get('missing') or [])})" for p in gaps[:8])
            + "。",
            "至少覆盖：档位自报降档、planned 伪 ready、子桶 fail 但无顶层 verdict、"
            "文档硬闸仅剩启发式 WARN、签收未绑定实际变更、structured warn 被缓存为 pass、"
            "unavailable 报告未覆写旧 ready 证据。",
        )
    else:
        add(findings, "info", "对抗/变形审计", loc,
            f"{len(report.get('probes') or [])} 个已登记对抗/变形探针均有 guard + 回归。", "")

    runtime = report.get("adversarial_runtime_receipt") or {}
    runtime_status = runtime.get("status", "not_run")
    if runtime_status in {"failed", "partial", "invalid"}:
        add(
            findings,
            "warn",
            "运行时对抗回归",
            loc,
            f"adversarially-tested={runtime_status}；静态找到测试名不算 pytest 已执行。",
            "修复失败回归或 runtime_tests 映射后重跑 `meta_audit.py --run-tests --json`。",
        )
    elif runtime_status == "complete":
        add(
            findings,
            "info",
            "运行时对抗回归",
            loc,
            f"本次已实际执行 {runtime.get('covered', 0)}/{runtime.get('total', 0)} 个已登记探针，收据已绑定当前 guard/test SHA。",
            "",
        )
    else:
        add(
            findings,
            "info",
            "运行时对抗回归",
            loc,
            "adversarially-tested=not_run；当前只有 defined-only 静态覆盖，未声称 pytest 已执行。",
            "需要运行证据时加 `--run-meta-tests`，或单跑 `meta_audit.py --run-tests --json`。",
        )

    evidence_findings = [
        row for row in report.get("findings") or []
        if row.get("dim") in {"外部证据 schema", "外部校准合同", "meta fixture"}
    ]
    if evidence_findings:
        add(
            findings,
            "warn",
            "外部证据 provenance",
            loc,
            f"外部证据/fixture 有 {len(evidence_findings)} 个 schema 或强制力映射问题："
            + "；".join(str(row.get("msg") or "") for row in evidence_findings[:4]),
            "来源 grounding 必须有 claim/source/date/confidence/implementation_mapping；"
            "校准另需 version=2 独立留出合同、盲法、预注册阈值、分层样本、裁决金标、混淆矩阵和当前 artifact SHA。",
        )
    else:
        assurance = report.get("assurance") or {}
        grounded = assurance.get("externally_grounded", {}).get("status", "not_run")
        calibrated = assurance.get("externally_calibrated", {}).get("status", "not_run")
        add(
            findings,
            "info",
            "外部证据 provenance",
            loc,
            f"外部依据状态={grounded}；独立留出校准状态={calibrated}。"
            "官方链接/论文只能提升 grounding，不能把 calibration 从 not_run 改成 complete。",
            "联网流程自审用 version=1/2 evidence 做来源映射；只有 version=2 calibrations 的完整合同可改变 externally-calibrated。",
        )
    return report


def audit(
    root: Path,
    work_root: Path | None = None,
    *,
    meta_fixture_paths: Sequence[Path] = (),
    evidence_paths: Sequence[Path] = (),
    run_meta_tests: bool = False,
) -> Dict[str, Any]:
    root = root.resolve()
    findings: List[Finding] = []
    check_progress_lock(root, findings)
    check_gate_entry(root, findings)
    check_cross_cutting_coverage(root, findings)
    check_benchmark_external(root, findings)
    check_image_backend_docs(root, findings)
    check_large_docs(root, findings)
    check_detector_inventory(root, findings)
    check_consistency_charter(root, findings)
    meta_report = check_meta_audit(
        root,
        findings,
        fixture_paths=meta_fixture_paths,
        evidence_paths=evidence_paths,
        run_tests=run_meta_tests,
    )
    if work_root is not None:
        check_friction_backlog(root, work_root.resolve(), findings)
    counts = {sev: sum(1 for item in findings if item["sev"] == sev) for sev in ("block", "warn", "info")}
    return {
        "kind": "n2d_self_audit",
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "work_root": str(work_root.resolve()) if work_root is not None else "",
        "counts": counts,
        "assurance": meta_report.get("assurance") or {},
        "meta_audit": meta_report,
        "findings": findings,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# n2d 流程自审",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 仓库：`{report['root']}`",
    ]
    if report.get("work_root"):
        lines.append(f"- 作品：`{report['work_root']}`（已并入现场摩擦信号）")
    assurance = report.get("assurance") or {}
    lines += [
        f"- 统计：block {report['counts']['block']} · warn {report['counts']['warn']} · info {report['counts']['info']}",
        "",
        "## 结论可信层级",
        "",
        "| 层级 | 状态 | 覆盖 |",
        "|---|---|---:|",
    ]
    for key in (
        "self_checked",
        "adversarial_test_coverage",
        "adversarially_tested",
        "externally_grounded",
        "externally_calibrated",
    ):
        row = assurance.get(key) or {"status": "not_run", "covered": 0, "total": 0}
        lines.append(
            f"| {row.get('label') or key} | {row.get('status')} | "
            f"{row.get('covered', 0)}/{row.get('total', 0)} |"
        )
    lines += [
        "",
        f"> {assurance.get('blind_spot_statement') or '0 warn 只代表已登记检查未发现缺口，不得表述为无盲区。'}",
        "",
        "| sev | 维度 | 位置 | 问题 | 建议 |",
        "|---|---|---|---|---|",
    ]
    for item in report["findings"]:
        lines.append(
            "| {sev} | {dim} | `{loc}` | {msg} | {suggestion} |".format(
                sev=item["sev"],
                dim=item["dim"],
                loc=item["loc"],
                msg=str(item["msg"]).replace("|", "/"),
                suggestion=str(item.get("suggestion") or "").replace("|", "/"),
            )
        )
    return "\n".join(lines) + "\n"


def _atomic_write_text(path: Path, content: str) -> None:
    """Write one UTF-8 report beside a temporary file, then replace atomically."""
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Report-only local self-audit for n2d skills")
    ap.add_argument("--root", default=str(repo_root_from_here()), help="repo root")
    ap.add_argument("--work", default="", help="作品根（创作区/制漫剧/<剧名>/）；给定时扫描其现场摩擦信号并入差距清单")
    ap.add_argument("--meta-fixture", action="append", default=[], help="独立 meta-audit JSON fixture pack（可重复）")
    ap.add_argument(
        "--run-meta-tests",
        action="store_true",
        help="实际执行 meta-audit 登记的最小 pytest 回归并输出当前 SHA 绑定收据",
    )
    ap.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="外部 grounding / 独立留出校准 JSON pack（v1 仅 grounding；v2 可含 calibrations；可重复）",
    )
    ap.add_argument("--json", action="store_true", help="print JSON report")
    ap.add_argument("--out", default="", help="atomically write the complete JSON report to PATH")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    work_root = Path(ns.work) if ns.work else None
    report = audit(
        Path(ns.root),
        work_root,
        meta_fixture_paths=[Path(p) for p in ns.meta_fixture],
        evidence_paths=[Path(p) for p in ns.evidence],
        run_meta_tests=ns.run_meta_tests,
    )
    json_report = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if ns.out:
        _atomic_write_text(Path(ns.out), json_report)
    if ns.json:
        print(json_report, end="")
    else:
        print(render_markdown(report), end="")
    return 1 if report["counts"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
