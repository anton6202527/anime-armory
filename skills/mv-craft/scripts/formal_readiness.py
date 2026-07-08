#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Assess whether an MV project is ready to be treated as a formal full MV."""
import argparse
import importlib.util
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
MV_UTILS_PATH = os.path.join(HERE, "mv_utils.py")


def load_mv_utils():
    spec = importlib.util.spec_from_file_location("mv_utils", MV_UTILS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mv_utils = load_mv_utils()


def lyric_line_count(root):
    path = os.path.join(root, "词", "lyrics.md")
    if not os.path.exists(path):
        return 0
    count = 0
    for raw in mv_utils.read_text(path).splitlines():
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            continue
        if mv_utils.SECTION_RE.match(s):
            continue
        if s.startswith("（") and s.endswith("）"):
            continue
        count += 1
    return count


def count_existing(paths, root):
    return sum(1 for rel in paths if rel and os.path.exists(os.path.join(root, rel)))


def format_reference_target(row):
    cov = row.get("coverage") or {}
    have = cov.get("existing_count", len(row.get("existing_paths") or []))
    need = cov.get("required_count", len(row.get("required_views") or []))
    return f"{row.get('target_id')}({row.get('status')},{have}/{need})"


def summarize_reference_requirements(root):
    payload = mv_utils.load_json(os.path.join(root, "设定", "reference_requirements.json"), {}) or {}
    rows = payload.get("requirements") or []
    counts = {}
    for row in rows:
        status = row.get("status") or "unknown"
        counts[status] = counts.get(status, 0) + 1
    not_ready = [r for r in rows if r.get("status") != "ready"]
    critical_missing = [r for r in not_ready if r.get("type") in {"identity", "prop", "vfx"}]
    return {
        "path": "设定/reference_requirements.json",
        "total": len(rows),
        "ready": counts.get("ready", 0),
        "partial": counts.get("partial", 0),
        "text_only": counts.get("text_only", 0),
        "planned": counts.get("planned", 0),
        "missing": len(not_ready),
        "missing_targets": [format_reference_target(r) for r in not_ready],
        "critical_missing_targets": [format_reference_target(r) for r in critical_missing],
    }


def build_formal_upgrade_plan(root, reference_summary):
    return [
        {
            "step": "1. 正式歌入库",
            "action": "替换 `歌/song.wav` 为完整定稿歌曲，并确认 `_meta.is_demo=false`、`分镜/clip_plan.json` 不再是 demo_excerpt。",
            "command": "",
        },
        {
            "step": "2. 重跑真实卡点",
            "action": "用正式整首歌重算 BPM、beats/downbeats 与段落能量。",
            "command": f'conda run -n cosyvoice python skills/mv-beat/scripts/beat_detect.py "{root}"',
        },
        {
            "step": "3. 重拆正式 timeline",
            "action": "按正式歌结构重拆 clip/timeline，不沿用 20s demo 的 5 镜头。",
            "command": f'python3 skills/mv-plan/scripts/plan_clips.py "{root}" --granularity 标准 --strategy 副歌强卡点 --visual-style 国风写意',
        },
        {
            "step": "4. 补语义镜头设计",
            "action": "让每个 clip 都有动作、景别、运镜、身份合约和参考输入。",
            "command": f'python3 skills/mv-plan/scripts/compose_prompts.py "{root}"',
        },
        {
            "step": "5. 刷新身份/资产/参考需求",
            "action": f"重建 reference pack 缺口；当前未 ready：{reference_summary.get('missing', 0)}/{reference_summary.get('total', 0)}。",
            "command": f'python3 skills/mv-craft/scripts/identity_registry.py "{root}"',
        },
        {
            "step": "6. 补正式 reference pack",
            "action": "按 `设定/reference_requirements.md` 补主角多角度、成年态、青锋剑、关键场景和剑光/VFX 参考图；补完后重跑第 5 步确认 ready。",
            "command": "",
        },
        {
            "step": "7. 出图后立即 QC",
            "action": "正式首帧/尾帧落档后先过 image_qc，再进入图生视频。",
            "command": f'python3 skills/mv-image/scripts/image_qc.py "{root}" --strict',
        },
        {
            "step": "8. 视频登记与挑版",
            "action": "为每个 clip 登记图生视频 take，按动作/身份/卡点/清晰度评分并 selected。",
            "command": f'python3 skills/mv-video/scripts/video_jobs.py "{root}"',
        },
        {
            "step": "9. 继承合约与视频 QC",
            "action": "检查首帧到视频是否继承身份/场景/道具，并抽 start/mid/end 帧看接缝与崩坏。",
            "command": f'python3 skills/mv-video/scripts/inherit_contract.py "{root}" --no-fail && python3 skills/mv-video/scripts/video_qc.py "{root}" --no-fail',
        },
        {
            "step": "10. 字幕、合成、总审",
            "action": "重做全曲卡拉 OK 字幕，合成正式成片，再跑 mv-review。",
            "command": f'bash skills/mv-compose/mv_compose.sh "{root}" 9:16 && python3 skills/mv-review/scripts/mv_check.py "{root}"',
        },
    ]


def build_report(root):
    meta = mv_utils.load_json(os.path.join(root, "_meta.json"), {}) or {}
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    jobs = mv_utils.load_json(os.path.join(root, "出视频", "jobs_manifest.json"), {}) or {}
    identity = mv_utils.load_json(os.path.join(root, "设定", "identity_registry.json"), {}) or {}
    image_qc = mv_utils.load_json(os.path.join(root, "生产数据", "image_qc", "image_qc.json"), {}) or {}
    inherit = mv_utils.load_json(os.path.join(root, "生产数据", "video_inherit_contract", "inherit_contract.json"), {}) or {}
    video_qc = mv_utils.load_json(os.path.join(root, "生产数据", "video_qc", "video_qc.json"), {}) or {}
    alignment = mv_utils.load_json(os.path.join(root, "字幕", "alignment_report.json"), {}) or {}
    reference_summary = summarize_reference_requirements(root)

    song = mv_utils.find_song(root)
    song_duration = mv_utils.audio_duration(song) if song else None
    clips = plan.get("clips") or []
    jobs_rows = jobs.get("jobs") or []
    image_paths = []
    for c in clips:
        image_paths.append(c.get("image_path"))
        if c.get("need_end_frame"):
            image_paths.append(c.get("end_frame_path"))
    selected_jobs = [j for j in jobs_rows if j.get("selected_take")]
    ready_groups = [g for g in identity.get("reference_groups", []) if g.get("status") == "ready"]
    all_groups = identity.get("reference_groups", [])

    blockers = []
    warnings = []
    next_actions = []

    if meta.get("is_demo") or plan.get("scope") == "demo_excerpt" or alignment.get("scope") == "demo_excerpt":
        blockers.append("当前项目标记为 demo_excerpt，不能作为正式整首 MV 发布。")
        next_actions.append("替换/确认正式整首歌后，清除 _meta.is_demo 或改为 false，并重跑 mv-beat + mv-plan。")
    if song_duration is None:
        blockers.append("缺正式歌/song.* 或无法读取时长。")
    elif song_duration < 90:
        blockers.append(f"当前歌长 {song_duration:.2f}s，明显不是完整 MV 歌曲。")
        next_actions.append("放入正式整首歌，保留 demo 成片作参考，不要直接扩剪。")
    if len(clips) < 12:
        blockers.append(f"clip_plan 只有 {len(clips)} 个 clip，正式 MV 通常需要更多镜头覆盖完整结构。")
        next_actions.append("正式歌入库后用精细/标准粒度重新生成 clip_plan。")
    if count_existing(image_paths, root) < len(image_paths):
        blockers.append("并非所有 clip 首帧/尾帧都已存在。")
        next_actions.append("按 reference_plan 补齐正式版首帧/尾帧，再跑 image_qc。")
    if len(selected_jobs) < len(clips):
        blockers.append(f"视频挑版未覆盖全部 clip：{len(selected_jobs)}/{len(clips)} selected。")
    if image_qc.get("summary", {}).get("verdict") == "block":
        blockers.append("image_qc 仍有 hard block。")
    if image_qc.get("summary", {}).get("degraded") and not image_qc.get("manual_review_accepted"):
        blockers.append("image_qc 降级且未人工留痕放行。")
    if inherit.get("summary", {}).get("hard_blocks"):
        blockers.append("video inherit contract 仍有 hard block。")
    if video_qc.get("summary", {}).get("hard_blocks"):
        blockers.append("video_qc 仍有 hard block。")
    if all_groups and len(ready_groups) < len(all_groups):
        warnings.append(f"身份参考组未全部 ready：{len(ready_groups)}/{len(all_groups)}。")
        next_actions.append("补成年态、手部/剑、关键场景多角度参考包。")
    if reference_summary["total"]:
        if reference_summary["missing"]:
            missing_preview = "、".join(reference_summary["missing_targets"][:8])
            warnings.append(
                f"正式 reference pack 未齐：ready {reference_summary['ready']}/{reference_summary['total']}；未 ready：{missing_preview}。"
            )
            next_actions.append("先按 设定/reference_requirements.md 补齐关键参考图，再正式批量出图/图生视频。")
        if reference_summary["critical_missing_targets"]:
            critical_preview = "、".join(reference_summary["critical_missing_targets"][:6])
            blockers.append(f"关键身份/道具/VFX 参考图未齐：{critical_preview}。")
    if alignment and alignment.get("aligned_lines", 0) < lyric_line_count(root) and alignment.get("scope") != "demo_excerpt":
        warnings.append("字幕对齐行数少于歌词行数，正式版需重新对齐全曲。")

    status = "ready" if not blockers and not warnings else ("blocked" if blockers else "review")
    command_plan = build_formal_upgrade_plan(root, reference_summary)
    return {
        "schema_version": 1,
        "kind": "mv_formal_readiness",
        "generated_at": date.today().isoformat(),
        "root": root,
        "summary": {
            "status": status,
            "blockers": len(blockers),
            "warnings": len(warnings),
            "song_duration_sec": song_duration,
            "clips": len(clips),
            "selected_jobs": len(selected_jobs),
            "lyric_lines": lyric_line_count(root),
            "reference_groups_ready": f"{len(ready_groups)}/{len(all_groups)}",
            "reference_requirements_ready": f"{reference_summary['ready']}/{reference_summary['total']}",
        },
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": next_actions,
        "reference_requirements": reference_summary,
        "formal_upgrade_plan": command_plan,
    }


def write_report(root, report):
    out_dir = os.path.join(root, "生产数据", "formal_readiness")
    mv_utils.write_json(os.path.join(out_dir, "formal_readiness.json"), report)

    def append_items(lines, title, items):
        lines.append("")
        lines.append(title)
        if items:
            lines.extend(f"- {x}" for x in items)
        else:
            lines.append("- none")

    lines = [
        "# formal readiness",
        "",
        f"- status: {report['summary']['status']}",
        f"- blockers: {report['summary']['blockers']}",
        f"- warnings: {report['summary']['warnings']}",
        f"- song_duration_sec: {report['summary']['song_duration_sec']}",
        f"- clips: {report['summary']['clips']}",
        f"- selected_jobs: {report['summary']['selected_jobs']}",
        f"- lyric_lines: {report['summary']['lyric_lines']}",
        f"- reference_groups_ready: {report['summary']['reference_groups_ready']}",
        f"- reference_requirements_ready: {report['summary']['reference_requirements_ready']}",
    ]
    append_items(lines, "## Blockers", report["blockers"])
    append_items(lines, "## Warnings", report["warnings"])
    append_items(lines, "## Next Actions", report["next_actions"])
    lines.append("")
    lines.append("## Reference Requirements")
    ref = report.get("reference_requirements") or {}
    lines.append(f"- ready: {ref.get('ready', 0)}/{ref.get('total', 0)}")
    lines.append(f"- partial: {ref.get('partial', 0)}")
    lines.append(f"- text_only: {ref.get('text_only', 0)}")
    lines.append(f"- planned: {ref.get('planned', 0)}")
    missing = ref.get("missing_targets") or []
    if missing:
        lines.append("- missing:")
        lines.extend(f"  - {x}" for x in missing)
    else:
        lines.append("- missing: none")
    lines.append("")
    lines.append("## Formal Upgrade Plan")
    for item in report.get("formal_upgrade_plan") or []:
        lines.append(f"- {item['step']}：{item['action']}")
        if item.get("command"):
            lines.append(f"  - `{item['command']}`")
    mv_utils.write_text(os.path.join(out_dir, "formal_readiness.md"), "\n".join(lines) + "\n")
    plan_lines = [
        "# formal upgrade plan",
        "",
        "用于把当前 demo excerpt 升级为正式整首 MV。先补上游真值，再重跑下游；不要直接扩剪 demo 成片。",
        "",
    ]
    for item in report.get("formal_upgrade_plan") or []:
        plan_lines.append(f"## {item['step']}")
        plan_lines.append(item["action"])
        if item.get("command"):
            plan_lines.extend(["", "```bash", item["command"], "```"])
        plan_lines.append("")
    mv_utils.write_text(os.path.join(out_dir, "formal_upgrade_plan.md"), "\n".join(plan_lines).rstrip() + "\n")
    return os.path.join(out_dir, "formal_readiness.json")


def main():
    ap = argparse.ArgumentParser(description="Assess formal full-MV readiness")
    ap.add_argument("project_root")
    ap.add_argument("--no-fail", action="store_true")
    args = ap.parse_args()

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    report = build_report(root)
    path = write_report(root, report)
    print(f"[ok] formal readiness → {path} ({report['summary']['status']})")
    if report["summary"]["status"] == "blocked" and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
