#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create/check an A&R style song brief."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import date
from typing import Any


KIND = "song_brief"
CHECK_KIND = "song_brief_check"
REQUIRED = ("target_listener", "core_promise", "emotional_arc", "sonic_identity", "hook_strategy")


def load_json(path: str, default: Any = None) -> Any:
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def paths(root: str) -> tuple[str, str, str]:
    out_dir = os.path.join(root, "创作")
    return (
        os.path.join(out_dir, "song_brief.json"),
        os.path.join(out_dir, "song_brief.md"),
        os.path.join(out_dir, "song_brief_check.json"),
    )


def build_brief(root: str, args: argparse.Namespace) -> dict[str, Any]:
    meta = load_json(os.path.join(root, "_meta.json"), {}) or {}
    target_duration = meta.get("target_duration_seconds") or 120
    use_case = args.use_case or meta.get("use_case") or "完整Demo"
    platform = args.target_platform or meta.get("target_platform") or meta.get("publish_target") or "未定"
    short_form = any(token in f"{use_case} {platform}".lower() for token in ("抖音", "tiktok", "reels", "short", "短视频"))
    default_deadline = min(8, max(3, int(target_duration * 0.15))) if short_form else min(30, max(8, int(target_duration * 0.25)))
    return {
        "schema_version": 2,
        "kind": KIND,
        "generated_at": date.today().isoformat(),
        "project_root": os.path.abspath(root),
        "title": args.title or meta.get("title") or os.path.basename(root),
        "use_case": use_case,
        "target_platform": platform,
        "target_listener": args.target_listener or "待填写：目标听众画像",
        "core_promise": args.core_promise or meta.get("theme") or "待填写：一句话听歌承诺",
        "emotional_arc": args.emotional_arc or "verse 收住 -> pre-chorus 抬升 -> chorus 释放 -> bridge 反转/加深",
        "hook_strategy": getattr(args, "hook_strategy", "") or ("cold_open" if short_form else "progressive_arrival"),
        "hook_deadline_seconds": args.hook_deadline_seconds or default_deadline,
        "sonic_identity": args.sonic_identity or ", ".join(str(x) for x in (meta.get("genre"), meta.get("mood")) if x) or "待填写：曲风/配器/人声身份",
        "reference_boundaries": args.reference_boundaries or "只参考情绪、结构、配器方向；不得复刻旋律、歌词、标志性 riff 或声音身份。",
        "success_metrics": args.success_metric or ["hook 可复唱", "副歌记忆点明确", "目标时长内完成情绪释放"],
        "target_duration_seconds": target_duration,
    }


def check_brief(brief: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    for field in REQUIRED:
        value = brief.get(field)
        if value in ("", None) or "待填写" in str(value):
            findings.append({"id": f"BRIEF-{field.upper()}", "severity": "blocking", "message": f"{field} 未完成。"})
    try:
        deadline = int(brief.get("hook_deadline_seconds"))
        duration = int(brief.get("target_duration_seconds") or 0)
        if deadline <= 0 or (duration and deadline >= duration):
            findings.append({"id": "BRIEF-HOOK-DEADLINE", "severity": "blocking", "message": "hook 截止必须大于 0 且早于目标时长。"})
        elif duration and deadline > duration * 0.4:
            findings.append({"id": "BRIEF-HOOK-DEADLINE-LATE", "severity": "warning", "message": "hook 晚于全曲 40%；若为慢热/通谱结构，请在 hook_strategy 说明。"})
    except Exception:
        findings.append({"id": "BRIEF-HOOK-DEADLINE", "severity": "blocking", "message": "hook_deadline_seconds 必须是数字。"})
    blockers = [item for item in findings if item["severity"] == "blocking"]
    return {
        "schema_version": 1,
        "kind": CHECK_KIND,
        "generated_at": date.today().isoformat(),
        "project_root": brief.get("project_root"),
        "source_sha256": hashlib.sha256(json.dumps(brief, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "passed": not blockers,
        "blocking": len(blockers),
        "warnings": len(findings) - len(blockers),
        "findings": findings,
    }


def render_markdown(brief: dict[str, Any], check: dict[str, Any]) -> str:
    lines = [
        "# Song Brief",
        "",
        f"- 标题：{brief.get('title')}",
        f"- 用途：{brief.get('use_case')}",
        f"- 平台：{brief.get('target_platform')}",
        f"- 目标听众：{brief.get('target_listener')}",
        f"- 核心承诺：{brief.get('core_promise')}",
        f"- Hook 截止：{brief.get('hook_deadline_seconds')}s",
        f"- Hook 策略：{brief.get('hook_strategy')}",
        f"- 声音身份：{brief.get('sonic_identity')}",
        "",
        "## Emotional Arc",
        "",
        str(brief.get("emotional_arc") or ""),
        "",
        "## Reference Boundaries",
        "",
        str(brief.get("reference_boundaries") or ""),
        "",
        "## Success Metrics",
        "",
    ]
    for item in brief.get("success_metrics") or []:
        lines.append(f"- {item}")
    if check.get("findings"):
        lines.extend(["", "## Findings", ""])
        for item in check["findings"]:
            lines.append(f"- [{item['severity']}] {item['id']}: {item['message']}")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(root: str, brief: dict[str, Any], check: dict[str, Any]) -> tuple[str, str, str]:
    json_path, md_path, check_path = paths(root)
    write_json(json_path, brief)
    write_json(check_path, check)
    write_text(md_path, render_markdown(brief, check))
    return json_path, md_path, check_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="生成/检查 A&R 歌曲简报")
    ap.add_argument("project_root")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--title", default="")
    ap.add_argument("--use-case", default="")
    ap.add_argument("--target-platform", default="")
    ap.add_argument("--target-listener", default="")
    ap.add_argument("--core-promise", default="")
    ap.add_argument("--emotional-arc", default="")
    ap.add_argument("--sonic-identity", default="")
    ap.add_argument("--hook-deadline-seconds", type=int, default=None)
    ap.add_argument("--hook-strategy", default="")
    ap.add_argument("--reference-boundaries", default="")
    ap.add_argument("--success-metric", action="append", default=[])
    args = ap.parse_args(argv)
    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}")
        return 2
    existing = load_json(paths(root)[0], {}) if not any([
        args.title, args.use_case, args.target_platform, args.target_listener,
        args.core_promise, args.emotional_arc, args.sonic_identity,
        args.hook_deadline_seconds, args.hook_strategy, args.reference_boundaries, args.success_metric,
    ]) else {}
    brief = existing if isinstance(existing, dict) and existing.get("kind") == KIND else build_brief(root, args)
    check = check_brief(brief)
    if args.write:
        json_path, md_path, check_path = write_outputs(root, brief, check)
        print(f"[ok] song brief JSON → {json_path}")
        print(f"[ok] song brief MD   → {md_path}")
        print(f"[ok] song brief check→ {check_path}")
    if args.json:
        print(json.dumps({"brief": brief, "check": check}, ensure_ascii=False, indent=2))
    elif not args.write:
        print(render_markdown(brief, check))
    return 0 if check["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
