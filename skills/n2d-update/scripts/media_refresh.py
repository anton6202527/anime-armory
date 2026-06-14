#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selective image/video refresh planner for n2d (制漫剧).

This is the `media` capability of n2d-update. The planner does not call
image/video backends and does not judge whether media is good or bad. It
produces an evidence-first refresh plan; keep/regenerate decisions must come
from gate/QC/review findings or explicit human input.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


KIND_PLAN = "skill_media_refresh_plan"
KIND_RUN = "skill_update_run"
PLAN_PREFIX = "media_refresh_plan"
RUN_LOG = "skill_update_runs.jsonl"


REUSE_POLICY = {
    "mode": "evidence_first_refresh_plan",
    "principle": "media_refresh 只生成计划，不做审片/质检判定；保留或重制结论必须来自已有 gate/QC/review findings 或显式人工输入。",
    "decision_sources": [
        "已有 gate/QC/review findings（含 severity、return_to_stage、affected_shots/artifacts 等结构化定位）",
        "审片人或用户显式点名的坏图/坏视频、可沿用目标及原因",
        "缺文件、路径不存在、manifest 无法追踪等可确定的文件完整性事实",
    ],
    "no_evidence_rule": "没有 findings 或人工判定时，media_refresh 只能列出复核步骤；不得把 target 判为坏/可用，也不得无条件排入重制。",
    "keep_if": [
        "finding 或人工判定显示身份/服装/场景/画风锚点可识别，未漂移到影响连续性",
        "finding 或人工判定显示轻微构图、表情、背景细节或审美偏差不影响下游叙事/卡点/字幕表达",
        "gate/QC 显示分辨率、画幅、安全区、时长和元数据满足本线非阻断要求",
        "review/gate 显示合规、授权（改编权/肖像/声音克隆）不存在 block",
    ],
    "regenerate_if": [
        "finding、人工判定或文件完整性事实显示目标文件缺失、路径未登记、无法被下游 manifest/job/timeline 追踪",
        "finding 或人工判定显示人物脸/核心服装/关键场景漂移，或与参考/定妆不再是同一资产",
        "gate/QC/review finding 显示视频动作、节奏、时长、接缝、首尾帧、视觉契约继承出现 block",
        "finding 显示使用了过期 prompt、后端混用或未授权逆向路径，导致本线最新 gate 不可放行",
    ],
}


DECISION_BOUNDARY = {
    "planner_role": "media_refresh 只生成选择性刷新计划和候选执行顺序，不直接判定图片/视频好坏。",
    "must_not": [
        "不得把 --image/--video/--target 传入值直接解释为坏目标",
        "不得在没有 gate/QC/review findings 或人工判定时无条件排入重制",
        "不得替代 n2d-review 或 n2d 各 gate/QC 的审片职责",
    ],
    "allowed_decision_sources": REUSE_POLICY["decision_sources"],
    "no_evidence_behavior": REUSE_POLICY["no_evidence_rule"],
}


def command_step(command: str) -> Dict[str, str]:
    return {"type": "command", "command": command}


def agent_step(instruction: str) -> Dict[str, str]:
    return {"type": "agent_step", "instruction": instruction}


def family_result(flow: List[str], steps: List[Dict[str, str]], **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "flow": flow,
        "execution_steps": steps,
        "commands": [s["command"] for s in steps if s.get("type") == "command"],
        "agent_steps": [s["instruction"] for s in steps if s.get("type") == "agent_step"],
    }
    out.update(extra)
    return out


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def production_dir(root: str) -> str:
    return os.path.join(root, "生产数据")


def split_selectors(values: Optional[Iterable[str]]) -> List[str]:
    out: List[str] = []
    for raw in values or []:
        for part in re.split(r"[,，、\s]+", str(raw or "")):
            text = part.strip()
            if text and text not in out:
                out.append(text)
    return out


def get_cascade_impacts(root: str, ep: str, image_targets: List[str]) -> Dict[str, List[str]]:
    """Check storyboard.json to see which video clips use these images as first/end/anchor frames."""
    impacts: Dict[str, List[str]] = {}  # image -> [clip_ids]
    if not image_targets:
        return impacts
        
    sb_path = os.path.join(root, "脚本", ep, "storyboard.json")
    if not os.path.isfile(sb_path):
        return impacts
        
    try:
        with open(sb_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return impacts
        
    clips = data.get("clips") or []
    if not isinstance(clips, list):
        return impacts
        
    # Standardize image targets for matching (handle base names)
    target_bases = {os.path.basename(t) for t in image_targets}
    
    for clip in clips:
        cid = clip.get("id") or clip.get("label") or "unknown"
        frames = []
        if clip.get("firstframe_png"):
            frames.append(clip["firstframe_png"])
        cont = clip.get("continuity") or {}
        if cont.get("endframe_png"):
            frames.append(cont["endframe_png"])
        for anchor in cont.get("anchors") or []:
            if anchor.get("anchor_png"):
                frames.append(anchor["anchor_png"])
                
        for frame in frames:
            f_base = os.path.basename(frame)
            if f_base in target_bases:
                img_key = next(t for t in image_targets if os.path.basename(t) == f_base)
                if img_key not in impacts:
                    impacts[img_key] = []
                if cid not in impacts[img_key]:
                    impacts[img_key].append(cid)
                    
    return impacts


def episode_number(ep: Optional[str]) -> str:
    text = str(ep or "").strip()
    if not text:
        return ""
    m = re.search(r"\d+", text)
    return m.group(0) if m else text


def quote(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def repeat_flag(flag: str, values: Iterable[str]) -> str:
    return " ".join(f"{flag} {quote(v)}" for v in values)


def n2d_plan(root: str, episode: Optional[str], image_targets: List[str], video_targets: List[str]) -> Dict[str, Any]:
    if not episode:
        raise SystemExit("n2d 媒体刷新计划需要 --episode 第N集，避免误扫全剧。")
    epn = episode_number(episode)
    steps: List[Dict[str, str]] = [
        command_step(f"python3 skills/n2d-update/scripts/update_plan.py check {quote(root)} {episode} --write-plan --regen-mode 严审刷新"),
    ]
    if image_targets:
        target_flags = repeat_flag("--affected-shot", image_targets)
        queue_cmd = (
            f"python3 skills/n2d-batch/scripts/queue.py plan {quote(root)} --episodes {epn} "
            f"--rerun-from image {target_flags} --scope \"媒体刷新·证据确认后重出图片\" "
            "--max-concurrency 1 --max-retries 1"
        )
        
        # Cascade impact detection
        impacts = get_cascade_impacts(root, episode, image_targets)
        cascade_note = ""
        if impacts:
            flattened = []
            for img, cids in impacts.items():
                flattened.append(f"{img} -> {', '.join(cids)}")
            cascade_note = f"\n  ⚠️ 级联影响预警：选中图片关联了以下视频 Clip 的首/尾/锚点帧：\n    - " + "\n    - ".join(flattened) + "\n  重出图后请务必同步复核/重制受影响的视频切片。"

        steps.extend([
            command_step(f"python3 skills/n2d-image/scripts/image_qc.py {quote(root)} {episode} --regen-list"),
            agent_step(
                "只在 image_qc/dashboard gate/n2d-review findings 或显式人工输入确认这些图片 target 不符合最新 prompt/QC/review 标准时，"
                f"才执行：`{queue_cmd}`；没有证据时保留为待复核，不排队。" + cascade_note),
            agent_step(
                "如果上一步已经排队并由 n2d-batch/对应 stage skill 实际完成图片重出，"
                f"再执行验收：`python3 skills/n2d-dashboard/scripts/dashboard.py gate {quote(root)} {episode} --stage image`；"
                "若只是生成队列计划，不能把这一步当成已验收。"),
        ])
    if video_targets:
        target_flags = repeat_flag("--affected-shot", video_targets)
        queue_cmd = (
            f"python3 skills/n2d-batch/scripts/queue.py plan {quote(root)} --episodes {epn} "
            f"--rerun-from video {target_flags} --scope \"媒体刷新·证据确认后重出视频\" "
            "--max-concurrency 1 --max-retries 1"
        )
        steps.extend([
            command_step(
                f"python3 skills/n2d-dashboard/scripts/dashboard.py gate {quote(root)} {episode} --stage video"
                "  # 预检：收集现有视频 gate/QC 证据"
            ),
            agent_step(
                "只在 video gate/QC/n2d-review findings 或显式人工输入确认这些视频 target 不符合最新 prompt/QC/review 标准时，"
                f"才执行：`{queue_cmd}`；没有证据时保留为待复核，不排队。"),
            agent_step(
                "如果上一步已经排队并由 n2d-batch/对应 stage skill 实际完成视频重出，"
                f"再执行验收：`python3 skills/n2d-dashboard/scripts/dashboard.py gate {quote(root)} {episode} --stage video`；"
                "若只是生成队列计划，不能把这一步当成已验收。"),
        ])
    flow = [
        "n2d-update: 先按最新 skill 快照生成 bounded plan，重制上界不超过本集当前阶段。",
        "n2d-image: 收集 image_qc/dashboard gate/n2d-review findings 或人工判定；media_refresh 不自行判坏。",
        "n2d-video: 收集 video gate/QC/n2d-review findings 或人工判定；只有证据确认 block 才排 video 返工。",
        "n2d-dashboard/n2d-review: 如发生重制，必须回 gate/review，确认像素一致性、接缝和合规闭环。",
    ]
    return family_result(flow, steps)


def build_plan(
    root: str,
    *,
    episode: Optional[str] = None,
    image_targets: Optional[Iterable[str]] = None,
    video_targets: Optional[Iterable[str]] = None,
    generic_targets: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    root = os.path.abspath(root)
    images = split_selectors(image_targets)
    videos = split_selectors(video_targets)
    generic = split_selectors(generic_targets)
    if generic:
        images = images + [x for x in generic if x not in images]
        videos = videos + [x for x in generic if x not in videos]

    family = n2d_plan(root, episode, images, videos)

    targets = {"images": images, "videos": videos}
    needs_media_review = bool(images or videos)
    return {
        "kind": KIND_PLAN,
        "created_at": now_iso(),
        "root": root,
        "line": "n2d",
        "episode": episode,
        "targets": targets,
        "policy": REUSE_POLICY,
        "decision_boundary": DECISION_BOUNDARY,
        "needs_media_review": needs_media_review,
        "needs_decision_evidence": needs_media_review,
        "latest_skill_flow": family["flow"],
        "execution_steps": family.get("execution_steps") or [],
        "commands": family["commands"],
        "agent_steps": family.get("agent_steps") or [],
        "notes": [
            "本计划只生成选择性刷新流程，不直接调用生图/生视频后端，也不替代审片/质检。",
            "执行前必须引用 gate/QC/review findings 或显式人工输入；未列入 targets 的图片/视频默认不动。",
            "没有证据时只推进复核步骤，不把 target 归类为坏/能用，也不无条件排入重制。",
            "如发生重制，必须回到 n2d-review/gate，不能只看生成是否成功。",
        ],
    }


def plan_paths(root: str, episode: Optional[str]) -> Tuple[str, str]:
    suffix = f"_{episode}" if episode else ""
    base = os.path.join(production_dir(root), f"{PLAN_PREFIX}{suffix}")
    return base + ".json", base + ".md"


def write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def append_run_log(root: str, plan: Dict[str, Any]) -> str:
    os.makedirs(production_dir(root), exist_ok=True)
    path = os.path.join(production_dir(root), RUN_LOG)
    entry = {
        "kind": KIND_RUN,
        "mode": "media_refresh",
        "created_at": plan["created_at"],
        "line": plan["line"],
        "episode": plan.get("episode"),
        "targets": plan.get("targets"),
        "plan_json": plan.get("plan_json"),
        "plan_md": plan.get("plan_md"),
        "needs_media_review": plan.get("needs_media_review"),
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def render_markdown(plan: Dict[str, Any]) -> str:
    lines = [
        f"# n2d 媒体选择性刷新计划 — {plan.get('episode') or '全集'}",
        "",
        f"- 作品根：`{plan['root']}`",
        f"- 集：`{plan.get('episode') or '不适用'}`",
        f"- 图片 targets：{', '.join(plan['targets']['images']) or '（无）'}",
        f"- 视频 targets：{', '.join(plan['targets']['videos']) or '（无）'}",
        f"- 原则：{plan['policy']['principle']}",
    ]

    boundary = plan.get("decision_boundary") or {}
    lines.extend(["", "## 职责边界"])
    lines.append(f"- {boundary.get('planner_role', 'media_refresh 只生成计划，不做审片/质检判定。')}")
    lines.append(f"- 无证据规则：{boundary.get('no_evidence_behavior', plan['policy'].get('no_evidence_rule', '无证据不判。'))}")
    if boundary.get("must_not"):
        lines.extend(f"- {item}" for item in boundary["must_not"])
    if plan["policy"].get("decision_sources"):
        lines.extend(["", "## 判定来源"])
        lines.extend(f"- {item}" for item in plan["policy"]["decision_sources"])

    lines.extend(["", "## 证据驱动的保留/重制标准", "", "### 可保留"])
    lines.extend(f"- {item}" for item in plan["policy"]["keep_if"])
    lines.extend(["", "### 可排重制"])
    lines.extend(f"- {item}" for item in plan["policy"]["regenerate_if"])

    lines.extend(["", "## 按最新 skill 的流程"])
    lines.extend(f"- {step}" for step in plan["latest_skill_flow"])

    if plan.get("execution_steps"):
        lines.extend(["", "## 执行顺序"])
        for idx, step in enumerate(plan["execution_steps"], start=1):
            if step.get("type") == "command":
                lines.extend([f"{idx}. shell", f"```bash\n{step['command']}\n```"])
            else:
                lines.append(f"{idx}. AI agent：{step.get('instruction', '')}")
    if plan.get("notes"):
        lines.extend(["", "## 备注"])
        lines.extend(f"- {note}" for note in plan["notes"])
    lines.append("")
    return "\n".join(lines)


def write_plan(root: str, plan: Dict[str, Any]) -> Dict[str, Any]:
    json_path, md_path = plan_paths(root, plan.get("episode"))
    plan["plan_json"] = json_path
    plan["plan_md"] = md_path
    write_json(json_path, plan)
    with open(md_path + ".tmp", "w", encoding="utf-8") as fh:
        fh.write(render_markdown(plan))
    os.replace(md_path + ".tmp", md_path)
    plan["run_log"] = append_run_log(root, plan)
    return plan


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="按 n2d 最新 gate/QC/review findings 生成选择性图片/视频刷新计划；不自行审片。")
    parser.add_argument("root", help="制漫剧/<剧名> 作品根")
    parser.add_argument("--episode", help="n2d 集号，如 第3集（必填，避免误扫全剧）")
    parser.add_argument("--image", action="append", default=[], help="候选复核/可能刷新的图片目标，可逗号分隔；不是坏图判定")
    parser.add_argument("--video", action="append", default=[], help="候选复核/可能刷新的视频目标，可逗号分隔；不是坏视频判定")
    parser.add_argument("--target", action="append", default=[], help="同时作为图片和视频目标的通用 selector")
    parser.add_argument("--write-plan", action="store_true", help="写入 生产数据/media_refresh_plan*.json/md 并追加 update runs 日志")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> int:
    plan = build_plan(
        args.root,
        episode=args.episode,
        image_targets=args.image,
        video_targets=args.video,
        generic_targets=args.target,
    )
    if args.write_plan:
        plan = write_plan(os.path.abspath(args.root), plan)
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        marker = "已生成候选计划（需证据确认）" if plan["needs_media_review"] else "无图片/视频 target"
        print(f"{plan['line']}: {marker} images={len(plan['targets']['images'])} videos={len(plan['targets']['videos'])}")
        if plan.get("plan_md"):
            print(f"  plan: {plan['plan_md']}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    return run(parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
