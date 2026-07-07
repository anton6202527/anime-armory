#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comic production gates.

Use this as the deterministic entry guard before paid image generation and
before handing images to compose/review.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
try:
    import style_consistency
    import character_consistency
    import review as review_module
except Exception as exc:  # pragma: no cover
    style_consistency = None
    character_consistency = None
    review_module = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
try:
    from image_backend_adapter import resolve_capabilities
except Exception:  # pragma: no cover
    resolve_capabilities = None

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
SKILLS_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def read_setting(root: Path, key: str, default: str = "") -> str:
    import re

    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in read_text(root / "_设置.md").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def add(
    findings: list[dict[str, Any]],
    severity: str,
    code: str,
    artifact: str,
    reason: str,
    return_to_stage: str,
    suggested_fix: str,
    *,
    evidence_family: str = "deterministic",
) -> None:
    findings.append(
        {
            "severity": severity,
            "dimension": "comic_gate",
            "code": code,
            "artifact": artifact,
            "reason": reason,
            "return_to_stage": return_to_stage,
            "suggested_fix": suggested_fix,
            "evidence_family": evidence_family,
        }
    )


def find_panel_image(root: Path, chapter: str, panel_id: str) -> Path | None:
    base = root / "出图" / chapter / "panels"
    for suffix in IMAGE_EXTS:
        path = base / f"{panel_id}{suffix}"
        if path.is_file():
            return path
    matches = sorted(base.glob(f"{panel_id}.*"))
    return next((item for item in matches if item.suffix.lower() in IMAGE_EXTS), None)


def refresh_identity_report(root: Path, chapter: str, findings: list[dict[str, Any]], *, no_refresh: bool) -> dict[str, Any]:
    report_path = root / "生产数据" / f"comic_identity_report_{chapter}.json"
    if not no_refresh:
        script = SKILLS_ROOT / "comic-identity" / "scripts" / "identity.py"
        proc = subprocess.run(
            [sys.executable, str(script), str(root), "--chapter", chapter, "report", "--write"],
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            add(
                findings,
                "block",
                "identity_report_refresh_failed",
                rel(root, script),
                "comic-identity report --write 运行失败：" + ((proc.stderr or proc.stdout or "").strip()[-1200:]),
                "identity",
                "修复 identity report 后重跑 gate。",
            )
            return {}
    return load_json(report_path, {})


def check_required(root: Path, chapter: str, findings: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Path]:
    paths = {
        "settings": root / "_设置.md",
        "progress": root / "_进度.md",
        "panel_script": root / "脚本" / chapter / "panel_script.json",
        "layout": root / "排版" / chapter / "layout.json",
        "panel_jobs": root / "出图" / chapter / "prompt" / "panel_jobs.json",
        "lettering": root / "排版" / chapter / "lettering.json",
        "manifest": root / "排版" / chapter / "export_manifest.json",
    }
    for key in keys:
        path = paths[key]
        if not path.is_file():
            add(
                findings,
                "block",
                f"{key}_missing",
                rel(root, path),
                "gate 必需文件缺失。",
                "script" if key == "panel_script" else "layout" if key == "layout" else "image" if key == "panel_jobs" else "compose",
                "补齐该阶段产物后重跑 gate。",
            )
    return paths


def check_identity(root: Path, report: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    summary = report.get("summary") if isinstance(report, dict) else {}
    if not isinstance(summary, dict):
        add(findings, "block", "identity_report_missing", "生产数据/comic_identity_report.json", "缺少可解析的一致性报告。", "identity", "运行 comic-identity report --write。")
        return
    if int(summary.get("missing_ref_count") or 0) > 0:
        add(findings, "block", "missing_ready_refs", "生产数据/comic_identity_report.json", "仍有共享参考图缺失。", "identity", "补齐 missing_refs 后重建出图包。")
    if int(summary.get("rerun_target_count") or 0) > 0:
        add(findings, "block", "reference_rerun_targets", "生产数据/comic_identity_report.json", "存在已 ready 但未按当前参考图重抽的 panel。", "image", "按 identity report 的 rerun_targets force 重抽。")
    level = read_setting(root, "定妆级别", "长线专门定妆")
    if level.startswith("长线") or "专门定妆" in level or "高一致性" in level:
        missing = report.get("missing_character_views") if isinstance(report, dict) else {}
        if not isinstance(missing, dict):
            add(findings, "block", "missing_character_views_unreadable", "生产数据/comic_identity_report.json", "长线定妆缺少 missing_character_views 字段。", "identity", "重新运行 comic-identity report --write。")
        else:
            blockers = {key: value for key, value in missing.items() if isinstance(value, list) and value}
            if blockers:
                reason = "；".join(f"{key} 缺 {','.join(map(str, value))}" for key, value in sorted(blockers.items()))
                add(findings, "block", "missing_character_views", "生产数据/comic_identity_report.json", "长线专门定妆未补齐：" + reason, "identity", "补 front/three_quarter/side/back/face 后重跑 gate。")


def check_style_contract(root: Path, findings: list[dict[str, Any]]) -> None:
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    has_registry_style = isinstance(registry, dict) and bool(registry.get("style_contract") or registry.get("visual_style"))
    assets = registry.get("assets") if isinstance(registry, dict) and isinstance(registry.get("assets"), dict) else {}
    has_style_asset = any(str(key).startswith("STYLE_") for key in assets)
    style_anchor = read_setting(root, "风格锚", "")
    if not style_anchor and not has_registry_style and not has_style_asset:
        add(
            findings,
            "block",
            "style_anchor_missing",
            "出图/共享/identity_registry.json",
            "缺少项目风格锚或 style_contract，正式批量出图前无法约束画风。",
            "identity",
            "登记 STYLE_ 风格资产或 registry.style_contract 后重建出图包。",
        )


def check_backend(root: Path, jobs: dict[str, Any], findings: list[dict[str, Any]], notes: list[str]) -> None:
    model = str(jobs.get("model") or read_setting(root, "生图模型", "自定义"))
    channel = str(jobs.get("channel") or read_setting(root, "生图渠道", "manual"))
    if resolve_capabilities:
        caps = resolve_capabilities(model, channel)
        notes.append(f"backend adapter: {caps.adapter_id}; reference_image_limit={caps.reference_image_limit}; persistent_subject={caps.persistent_subject}")
    pairs = {
        (str(job.get("model") or model), str(job.get("source") or channel))
        for job in jobs.get("jobs") or []
        if isinstance(job, dict)
    }
    if len(pairs) > 1:
        add(
            findings,
            "block",
            "generation_recipe_mixed",
            f"出图/{jobs.get('chapter', '')}/prompt/panel_jobs.json",
            "同一话记录了多个生图模型/渠道：" + "；".join(f"{m}/{c}" for m, c in sorted(pairs)),
            "image",
            "统一模型和渠道后重建 job 包并重抽受影响格。",
        )


def check_panel_jobs_ready(root: Path, chapter: str, jobs: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    for job in jobs.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        pid = str(job.get("panel_id") or "")
        status = str(job.get("status") or "")
        panel_path = find_panel_image(root, chapter, pid)
        post_qc = job.get("post_qc") if isinstance(job.get("post_qc"), dict) else {}
        post_verdict = str(post_qc.get("verdict") or "")
        if status == "qc_block" or post_verdict == "block":
            add(
                findings,
                "block",
                "panel_post_qc_block",
                str(job.get("result_path") or f"出图/{chapter}/panels/{pid}.png"),
                f"{pid} 的落盘 post_qc=block，不能进入合成。",
                "image",
                "查看 生产数据/panel_qc，修复参考/尺寸/空图等问题后 force 重抽该格。",
            )
            continue
        if status != "ready" or not panel_path:
            add(
                findings,
                "block",
                "panel_not_ready",
                str(job.get("result_path") or f"出图/{chapter}/panels/{pid}.png"),
                f"{pid} 还不是 ready 或图像文件缺失。",
                "image",
                "补齐该 panel 图并确保 job.status=ready。",
            )
        elif post_verdict == "warn":
            add(
                findings,
                "warn",
                "panel_post_qc_warn",
                str(job.get("result_path") or rel(root, panel_path)),
                f"{pid} 的落盘 post_qc=warn，需要人审签收或重抽。",
                "image",
                "放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。",
                evidence_family="heuristic",
            )


def merge_consistency_report(report: dict[str, Any], findings: list[dict[str, Any]], *, category: str) -> None:
    for item in report.get("findings") or []:
        severity = str(item.get("severity") or "warn")
        if severity not in {"block", "warn", "info"}:
            severity = "warn"
        add(
            findings,
            severity,
            str(item.get("code") or category),
            str(item.get("artifact") or item.get("panel_id") or ""),
            str(item.get("reason") or category),
            str(item.get("return_to_stage") or ("image" if severity in {"block", "warn"} else "review")),
            str(item.get("suggested_fix") or "按一致性报告处理。"),
            evidence_family=str(item.get("evidence_family") or category),
        )


def run_image_preflight(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    paths = check_required(root, chapter, findings, ("settings", "panel_script", "layout", "panel_jobs"))
    jobs = load_json(paths["panel_jobs"], {})
    if isinstance(jobs, dict):
        check_backend(root, jobs, findings, notes)
    report = refresh_identity_report(root, chapter, findings, no_refresh=no_refresh)
    check_identity(root, report, findings)
    check_style_contract(root, findings)


def run_image(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_image_preflight(root, chapter, findings, notes, no_refresh=no_refresh)
    jobs = load_json(root / "出图" / chapter / "prompt" / "panel_jobs.json", {})
    if isinstance(jobs, dict):
        check_panel_jobs_ready(root, chapter, jobs, findings)
    if style_consistency is None or character_consistency is None:
        add(findings, "block", "consistency_module_unavailable", "skills/comic-review/scripts", f"一致性模块不可用：{IMPORT_ERROR}", "review", "修复 comic-review 模块导入。")
        return
    style_report = style_consistency.analyze(root, chapter)
    style_paths = style_consistency.write_outputs(root, chapter, style_report)
    notes.append(f"style consistency refreshed: {style_paths['markdown']}")
    merge_consistency_report(style_report, findings, category="style_consistency")
    char_report = character_consistency.analyze(root, chapter)
    char_paths = character_consistency.write_outputs(root, chapter, char_report)
    notes.append(f"character consistency refreshed: {char_paths['markdown']}")
    merge_consistency_report(char_report, findings, category="character_consistency")


def run_compose(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_image(root, chapter, findings, notes, no_refresh=no_refresh)
    paths = check_required(root, chapter, findings, ("lettering", "manifest"))
    manifest = load_json(paths["manifest"], {})
    if isinstance(manifest, dict):
        if manifest.get("missing_panels"):
            add(findings, "block", "manifest_missing_panels", rel(root, paths["manifest"]), "export_manifest 仍记录缺图。", "compose", "补图并重新导出。")
        if not manifest.get("rendered"):
            add(findings, "block", "manifest_not_rendered", rel(root, paths["manifest"]), "尚未登记实际渲染导出物。", "compose", "运行 export_longstrip.py --render。")


def run_review(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_compose(root, chapter, findings, notes, no_refresh=no_refresh)
    if review_module is None:
        add(findings, "block", "review_module_unavailable", "skills/comic-review/scripts/review.py", f"review 模块不可用：{IMPORT_ERROR}", "review", "修复 review.py 后重跑 gate。")
        return
    report = review_module.review(root, chapter, refresh_qa_preview=True)
    notes.append("comic-review report refreshed in review gate")
    for issue in report.get("issues") or []:
        add(
            findings,
            str(issue.get("severity") or "warn"),
            str(issue.get("category") or "review_issue"),
            str(issue.get("artifact") or ""),
            str(issue.get("reason") or ""),
            str(issue.get("return_to") or "review"),
            str(issue.get("suggested_fix") or "按 comic-review 报告处理。"),
        )


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in findings:
        key = (
            str(item.get("severity") or ""),
            str(item.get("code") or ""),
            str(item.get("artifact") or ""),
            str(item.get("reason") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def make_report(root: Path, chapter: str, stage: str, findings: list[dict[str, Any]], notes: list[str]) -> dict[str, Any]:
    findings = dedupe_findings(findings)
    block_count = sum(1 for item in findings if item.get("severity") == "block")
    warn_count = sum(1 for item in findings if item.get("severity") == "warn")
    info_count = sum(1 for item in findings if item.get("severity") == "info")
    return {
        "schema_version": 1,
        "kind": "comic_gate",
        "project_root": str(root),
        "chapter": chapter,
        "stage": stage,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "verdict": "block" if block_count else "warn" if warn_count else "pass",
        "summary": {
            "finding_count": len(findings),
            "block_count": block_count,
            "warn_count": warn_count,
            "info_count": info_count,
        },
        "findings": findings,
        "notes": notes,
    }


def write_outputs(root: Path, chapter: str, stage: str, report: dict[str, Any]) -> dict[str, str]:
    out_json = root / "生产数据" / f"comic_gate_{stage}_{chapter}.json"
    out_md = root / "生产数据" / f"comic_gate_{stage}_{chapter}.md"
    findings_path = root / "生产数据" / f"gate_findings_{stage}_{chapter}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    findings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "comic_gate_findings",
                "chapter": chapter,
                "stage": stage,
                "created_at": report.get("created_at"),
                "summary": report.get("summary"),
                "findings": report.get("findings") or [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_markdown(report, out_md)
    return {"json": rel(root, out_json), "markdown": rel(root, out_md), "findings": rel(root, findings_path)}


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report.get("summary") or {}
    lines = [
        f"# 漫画 Gate — {report.get('stage')} — {report.get('chapter')}",
        "",
        f"- 生成时间：{report.get('created_at')}",
        f"- 结论：{report.get('verdict')}",
        f"- block/warn/info：{summary.get('block_count', 0)} / {summary.get('warn_count', 0)} / {summary.get('info_count', 0)}",
    ]
    notes = report.get("notes") or []
    if notes:
        lines += ["", "## 记录", ""]
        lines.extend(f"- {note}" for note in notes)
    lines += ["", "## Findings", ""]
    findings = report.get("findings") or []
    if not findings:
        lines.append("- 未发现阻断或警告。")
    else:
        lines += ["| severity | code | artifact | reason | return_to | suggested_fix |", "|---|---|---|---|---|---|"]
        for item in findings:
            row = [
                item.get("severity", ""),
                item.get("code", ""),
                item.get("artifact", ""),
                item.get("reason", ""),
                item.get("return_to_stage", ""),
                item.get("suggested_fix", ""),
            ]
            lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画生产 gate")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--stage", choices=("image_preflight", "image", "compose", "review"), default="image_preflight")
    parser.add_argument("--no-refresh", action="store_true", help="不刷新 identity report；style/character 仍按当前图片重算")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    if args.stage == "image_preflight":
        run_image_preflight(root, args.chapter, findings, notes, no_refresh=args.no_refresh)
    elif args.stage == "image":
        run_image(root, args.chapter, findings, notes, no_refresh=args.no_refresh)
    elif args.stage == "compose":
        run_compose(root, args.chapter, findings, notes, no_refresh=args.no_refresh)
    else:
        run_review(root, args.chapter, findings, notes, no_refresh=args.no_refresh)

    report = make_report(root, args.chapter, args.stage, findings, notes)
    paths = write_outputs(root, args.chapter, args.stage, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(f"[ok] {paths['json']}")
        print(f"[ok] {paths['markdown']}")
        print(f"verdict={report['verdict']} block={summary['block_count']} warn={summary['warn_count']} info={summary['info_count']}")
    return 1 if report["verdict"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
