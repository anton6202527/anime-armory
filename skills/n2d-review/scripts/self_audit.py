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
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence


Finding = Dict[str, Any]


IMAGE_BACKEND_DOCS = (
    "skills/_偏好约定.md",
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
    path = root / "skills" / "common" / "n2d_contract.py"
    if not path.is_file():
        return None, None
    try:
        spec = importlib.util.spec_from_file_location("_n2d_self_audit_contract", path)
        if spec is None or spec.loader is None:
            return None, "无法加载 n2d_contract.py"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module, None
    except Exception as exc:  # pragma: no cover - defensive report path
        return None, str(exc)


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
        "novel2drama/**/*.md",
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
    path = root / "skills" / "novel2drama" / "progress.py"
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
    path = root / "skills" / "common" / "n2d_contract.py"
    if error:
        add(findings, "block", "生图后端白名单", rel(root, path), f"无法导入 n2d_contract.py：{error}")
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
            "从 `skills/common/n2d_contract.py` 的 APPROVED_IMAGE_BACKENDS 刷新选择点、n2d-image 说明和 review checklist；`同视频AI` 只能作为禁用/旧值迁移语境出现。",
        )
    else:
        add(findings, "info", "生图后端白名单", "skills/common/n2d_contract.py", "关键文档已覆盖 APPROVED_IMAGE_BACKENDS，且未把 `同视频AI` 当作可选后端。")


def check_large_docs(root: Path, findings: List[Finding]) -> None:
    docs = (
        (root / "skills" / "novel2drama" / "SKILL.md", 400, "长规则优先沉到 references/，SKILL.md 保持路由和关键命令。"),
        (root / "skills" / "novel2drama" / "Q&A.md", 1500, "Q&A 是沉淀库；超过阈值时再分卷或按主题拆 references。"),
    )
    for path, warn_after, suggestion_text in docs:
        if not path.is_file():
            continue
        n = len(text(path).splitlines())
        sev = "warn" if n > warn_after else "info"
        msg = f"{rel(root, path)} 当前 {n} 行。"
        suggestion = suggestion_text if sev == "warn" else ""
        add(findings, sev, "文档体量", rel(root, path), msg, suggestion)


def audit(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    findings: List[Finding] = []
    check_progress_lock(root, findings)
    check_gate_entry(root, findings)
    check_cross_cutting_coverage(root, findings)
    check_benchmark_external(root, findings)
    check_image_backend_docs(root, findings)
    check_large_docs(root, findings)
    counts = {sev: sum(1 for item in findings if item["sev"] == sev) for sev in ("block", "warn", "info")}
    return {
        "kind": "n2d_self_audit",
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "root": str(root),
        "counts": counts,
        "findings": findings,
    }


def render_markdown(report: Dict[str, Any]) -> str:
    lines = [
        "# n2d 流程自审",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 仓库：`{report['root']}`",
        f"- 统计：block {report['counts']['block']} · warn {report['counts']['warn']} · info {report['counts']['info']}",
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


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Report-only local self-audit for n2d skills")
    ap.add_argument("--root", default=str(repo_root_from_here()), help="repo root")
    ap.add_argument("--json", action="store_true", help="print JSON report")
    return ap


def main(argv: Sequence[str]) -> int:
    ns = parser().parse_args(argv)
    report = audit(Path(ns.root))
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report), end="")
    return 1 if report["counts"]["block"] else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
