#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ad-progress/scan.py — 拍广告进度扫描器（只读）。

默认扫描 `创作区/拍广告/<项目>/_进度.md`，并兼容旧 `拍广告/<项目>/_进度.md`。
广告线不拆集：进度由阶段表 + 交付版本矩阵共同表达。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

CREATION_ROOT_DIR = "创作区"
LINE_DIR = "拍广告"
DONE = "done"
BLOCK = "block"
PARTIAL = "partial"
TODO = "todo"


def find_repo_root(start: str) -> str:
    d = os.path.abspath(start)
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, "skills")) and (
            os.path.isfile(os.path.join(d, "AGENTS.md"))
            or os.path.isfile(os.path.join(d, "CLAUDE.md"))
        ):
            return d
        d = os.path.dirname(d)
    return os.path.abspath(start)


def load_line_modules(repo_root: str):
    craft_dir = os.path.join(repo_root, "skills", "ad", "ad-craft", "scripts")
    lib_dir = os.path.join(repo_root, "skills", "ad", "_lib")
    for path in (craft_dir, lib_dir):
        if path not in sys.path:
            sys.path.insert(0, path)
    import contract  # noqa: WPS433,E402
    import progress_md  # noqa: WPS433,E402

    return contract, progress_md


def line_root_candidates(repo_root: str) -> list[str]:
    return [
        os.path.join(repo_root, CREATION_ROOT_DIR, LINE_DIR),
        os.path.join(repo_root, LINE_DIR),
    ]


def progress_root(path: str) -> str | None:
    root = os.path.abspath(path)
    if os.path.basename(root) == "_进度.md" and os.path.isfile(root):
        root = os.path.dirname(root)
    if os.path.isfile(os.path.join(root, "_进度.md")):
        return root
    return None


def collect_works(repo_root: str, targets: list[str]) -> list[tuple[str, str]]:
    works: list[tuple[str, str]] = []
    if targets:
        for target in targets:
            root = progress_root(target)
            rel = os.path.relpath(os.path.abspath(target), repo_root)
            if root is None:
                print(f"（跳过 {rel}：无 _进度.md）")
                continue
            works.append((root, os.path.relpath(root, repo_root)))
        return works

    for base in line_root_candidates(repo_root):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            root = os.path.join(base, name)
            if os.path.isfile(os.path.join(root, "_进度.md")):
                works.append((root, os.path.relpath(root, repo_root)))
    return works


def read_text(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def load_json(path: str, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return default


def parse_stage_rows(progress_md, text: str) -> list[dict[str, str]]:
    return progress_md.parse_stage_rows(
        text,
        section_keywords=("阶段进度",),
        min_cols=2,
        label_col=0,
        status_col=1,
    )


def parse_deliverables(progress_md, text: str) -> list[dict[str, str]]:
    rows = progress_md.parse_stage_rows(
        text,
        section_keywords=("交付版本矩阵",),
        min_cols=7,
        label_col=0,
        status_col=5,
    )
    return [row for row in rows if row.get("label") not in ("交付件", "---")]


def state_of(status: str) -> str:
    raw = (status or "").strip()
    low = raw.lower()
    if "✅" in raw or "[x]" in low:
        return DONE
    match = re.search(r"(\d+)\s*/\s*(\d+)", raw)
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        if total > 0 and current >= total:
            return DONE
        if current > 0:
            return PARTIAL
    if "🔴" in raw or "block" in low:
        return BLOCK
    if "⏳" in raw or "rough" in low or raw not in ("", "⬜", "[ ]"):
        return PARTIAL
    return TODO


def marker(state: str) -> str:
    return {DONE: "✅", BLOCK: "🔴", PARTIAL: "⏳", TODO: "⬜"}.get(state, "⬜")


def brief_hint(contract, root: str) -> str:
    path = os.path.join(root, "需求", "brief.json")
    if not os.path.isfile(path):
        return "brief: 缺 需求/brief.json，建议先回 ad-concept 第0步补齐客户需求"
    try:
        with open(path, encoding="utf-8") as fh:
            check = contract.brief_check(json.load(fh))
    except (OSError, json.JSONDecodeError):
        return "brief: 需求/brief.json 读取失败，请先检查 JSON 格式"
    if check["missing_required"]:
        return (
            "brief: 缺必填项 "
            + "、".join(check["missing_required"])
            + "，先让 ad-concept 第0步访谈补齐"
        )
    if check["missing_deferred"]:
        return (
            "brief: 合规项待补 "
            + "、".join(check["missing_deferred"])
            + "，不阻塞创意/脚本，但进出图/出视频/合成 gate 前必须补齐"
        )
    return ""


def _summary_counts(report: dict) -> tuple[int, int]:
    summary = report.get("summary") if isinstance(report, dict) else {}
    if not isinstance(summary, dict):
        return 0, 0
    try:
        return int(summary.get("block") or summary.get("approval_blocks") or 0), int(summary.get("warn") or 0)
    except (TypeError, ValueError):
        return 0, 0


def production_control_hints(root: str) -> list[str]:
    """横切产物摘要：producer_pack/ad_score/product_qc/video_qc。只读，不要求全存在。"""
    hints: list[str] = []
    storyboard_exists = os.path.isfile(os.path.join(root, "脚本", "storyboard.json"))
    image_exists = has_media(os.path.join(root, "出图", "分镜"), (".png", ".jpg", ".jpeg", ".webp"))
    video_exists = has_media(os.path.join(root, "出视频", "分镜", "视频"), (".mp4", ".mov", ".m4v"))

    producer = load_json(os.path.join(root, "生产数据", "producer_pack.json"))
    if producer:
        summary = producer.get("summary") or {}
        hints.append(
            "producer_pack: "
            f"shots={summary.get('shots', 0)} "
            f"approval_blocks={summary.get('approval_blocks', 0)} "
            f"asset_blocks={summary.get('asset_blocks', 0)}"
        )
    elif storyboard_exists:
        hints.append("producer_pack: 未生成；出图前建议先跑 ad-craft producer_pack 做制片前控")

    score = load_json(os.path.join(root, "评分", "ad_score.json"))
    if score:
        hints.append(
            "ad_score: "
            f"total={score.get('total_score')} tier={score.get('tier')} "
            f"first3={((score.get('dims') or {}).get('first_3s_brand_product', '-'))}"
        )
    elif storyboard_exists:
        hints.append("ad_score: 未生成；出图前建议先跑 ad-score 评前三秒/品牌/CTA")

    image_plan = load_json(os.path.join(root, "出图", "分镜", "image_jobs_manifest.json"))
    if image_plan:
        summary = image_plan.get("summary") or {}
        jobs = image_plan.get("jobs") if isinstance(image_plan.get("jobs"), list) else []
        done = 0
        for job in jobs:
            if not isinstance(job, dict):
                continue
            rel = str(job.get("expected_output") or "")
            if rel and os.path.isfile(os.path.join(root, rel)):
                done += 1
        hints.append(
            "image_jobs: "
            f"planned={summary.get('planned', len(jobs))} "
            f"first={summary.get('first_frames', '-')} "
            f"end={summary.get('end_frames', '-')} "
            f"png_done={done}/{len(jobs)}"
        )

    product_qc = load_json(os.path.join(root, "出图", "分镜", "product_qc.json"))
    if product_qc:
        block, warn = _summary_counts(product_qc)
        hints.append(f"product_qc: block={block} warn={warn}")
    elif image_exists:
        hints.append("product_qc: 已有出图但缺报告；出视频前先跑 ad-image product_qc")

    video_qc = load_json(os.path.join(root, "出视频", "分镜", "video_qc.json"))
    if video_qc:
        block, warn = _summary_counts(video_qc)
        hints.append(f"video_qc: block={block} warn={warn}")
    elif video_exists:
        hints.append("video_qc: 已有视频 clip 但缺报告；合成前先跑 ad-video video_qc")

    return hints


def acceptance_audit(root: str, states, stage_by_label) -> list[str]:
    """✅ 阶段行 ↔ 验收凭证对账（只读发现，不改状态）。

    手改 _进度.md 可绕过 progress_set 的护栏；扫描器把每个标 ✅ 的阶段行对到
    `生产数据/stage_acceptance/<stage>.json`：凭证缺失/不可读 → 「✅ 无验收凭证」，
    凭证仍有 block → 「✅ 但验收凭证 block>0」。硬拦在 ad-review M0，这里只报。
    """
    issues: list[str] = []
    for row, state in states:
        if state != DONE:
            continue
        key = str((stage_by_label.get(row["label"]) or {}).get("key") or "")
        if not key:
            continue
        rel = os.path.join("生产数据", "stage_acceptance", f"{key}.json")
        payload = load_json(os.path.join(root, rel))
        if not isinstance(payload, dict):
            issues.append(f"⚠️ {row['label']}: ✅ 无验收凭证（缺 {rel}，疑似手改 _进度.md）")
            continue
        try:
            block = int((payload.get("summary") or {}).get("block") or 0)
        except (TypeError, ValueError):
            block = -1
        if block:
            issues.append(f"⚠️ {row['label']}: ✅ 但验收凭证 {rel} 仍有 block（假完成）")
    return issues


def has_media(folder: str, suffixes: tuple[str, ...]) -> bool:
    if not os.path.isdir(folder):
        return False
    return any(name.lower().endswith(suffixes) for name in os.listdir(folder))


def report(contract, progress_md, root: str, rel: str, limit: int) -> str:
    out = [f"=== {rel} ==="]
    progress_file = os.path.join(root, "_进度.md")
    try:
        text = read_text(progress_file)
    except OSError as exc:
        out.append(f"（无可解析的进度表: {exc}）")
        return "\n".join(out)

    rows = parse_stage_rows(progress_md, text)
    if not rows:
        out.append("（_进度.md 未发现可解析的「阶段进度」表）")
        return "\n".join(out)

    stage_by_label = {str(s.get("label", "")): s for s in contract.stage_table()}
    states = [(row, state_of(row["status"])) for row in rows]
    done = sum(1 for _, state in states if state == DONE)
    out.append(f"阶段数: {len(rows)} | 完成: {done}/{len(rows)}")
    out.append("各阶段: " + " | ".join(f"{row['label']} {marker(state)}" for row, state in states))
    out.extend(acceptance_audit(root, states, stage_by_label))

    deliverables = parse_deliverables(progress_md, text)
    if deliverables:
        deliverable_states = [(row, state_of(row["status"])) for row in deliverables]
        d_done = sum(1 for _, state in deliverable_states if state == DONE)
        out.append(
            "交付件: "
            + f"{d_done}/{len(deliverables)} "
            + " | ".join(f"{row['label']} {marker(state)}" for row, state in deliverable_states[:6])
        )
        if len(deliverables) > 6:
            out.append(f"  - …另有 {len(deliverables) - 6} 个交付件")

    hint = brief_hint(contract, root)
    if hint:
        out.append(hint)
    out.extend(production_control_hints(root))

    frontier_index = next((i for i, (_, state) in enumerate(states) if state != DONE), None)
    if frontier_index is None:
        out.append("✅ 阶段进度看起来都已完成。下一步：ad-review M0 质检 + ad-craft AI/授权披露确认。")
        return "\n".join(out)

    row, state = states[frontier_index]
    meta = stage_by_label.get(row["label"], {})
    owner = meta.get("owner", "ad")
    key = meta.get("key", "")
    gate = meta.get("gate", "")
    vt = f"（当前 {row['status']}）" if row["status"] and state != TODO else ""
    out.append(f"前沿: {row['label']} {vt} → skill: {owner}")
    if gate:
        out.append(f"  gate: {gate}")
    if key in getattr(contract, "GATE_STAGES", ()):
        out.append("  ⚠️ 高风险阶段：会花钱/不可逆，正式生产前确认后端、交付规格并先跑 ad-craft gate")

    later = [item for item in states[frontier_index + 1:] if item[1] != DONE]
    if later:
        out.append("后续待办:")
        for item, item_state in later[:limit]:
            meta = stage_by_label.get(item["label"], {})
            out.append(f"  - {item['label']} {marker(item_state)} → {meta.get('owner', 'ad')}")
        if len(later) > limit:
            out.append(f"  - …另有 {len(later) - limit} 项")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="拍广告进度仪表盘（只读）")
    ap.add_argument("project_roots", nargs="*", help="可选：一个或多个广告项目根，或 _进度.md 文件")
    ap.add_argument("--root", default=None, help="仓库根；默认自动向上查找")
    ap.add_argument("--limit", type=int, default=5, help="每个项目展示的后续待办条数")
    args = ap.parse_args(argv)

    repo_root = os.path.abspath(args.root) if args.root else find_repo_root(os.path.dirname(__file__))
    contract, progress_md = load_line_modules(repo_root)
    works = collect_works(repo_root, args.project_roots)
    if not works:
        print(f"未找到任何含 _进度.md 的广告项目。线根目录：{CREATION_ROOT_DIR}/{LINE_DIR}/")
        return 0

    print("\n\n".join(report(contract, progress_md, root, rel, args.limit) for root, rel in works))
    print(f"\n--- 共 {len(works)} 条广告项目 ---")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
