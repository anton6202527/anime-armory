#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mv 单一入口编排器：把「读进度 → 跑 gate → 决定下一步」收敛成一个机器可消费的命令。

背景：此前 `_进度.md`（文档自报状态）与 `gate.py`（确定性闸）互不联动——agent 靠散文路由表
自觉选下一步，上游变化只有在下次付费阶段跑 gate 时才被动现形。本入口把两者接通：

    python3 skills/mv/run.py next <作品根> [--json]
        算生产前沿 → 对前沿阶段跑确定性 gate → 对已 done 的付费阶段做收据健康度巡检
        （hash 链失效的「假 done」主动现形）→ 输出结构化 NextAction（停因是登记制枚举）。

    python3 skills/mv/run.py impact <作品根> --clip Clip_00N [--change image|prompt|edit] [--json]
        clip 级返工级联：改一个 clip 的图/prompt/剪辑决定后，机器列出下游要重做什么、
        按什么顺序、跑什么命令——替代「gate 被动全量报错」的粗颗粒返工。

只读不写：本入口不改 `_进度.md`、不生成产物、不代跑付费阶段；付费/创作动作只给出
exact_command 与停因，由人/agent 显式执行（stop_policy 见各停因语义）。
"""
import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS = HERE
CRAFT_SCRIPTS = os.path.join(SKILLS, "mv-craft", "scripts")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    if CRAFT_SCRIPTS not in sys.path:
        sys.path.insert(0, CRAFT_SCRIPTS)
    spec.loader.exec_module(mod)
    return mod


mv_utils = _load("mv_run_utils", os.path.join(CRAFT_SCRIPTS, "mv_utils.py"))
gate = _load("mv_run_gate", os.path.join(CRAFT_SCRIPTS, "gate.py"))
contract = _load("mv_run_contract", os.path.join(CRAFT_SCRIPTS, "contract.py"))
progress = _load("mv_run_progress", os.path.join(CRAFT_SCRIPTS, "progress.py"))
completion = _load("mv_run_completion", os.path.join(CRAFT_SCRIPTS, "completion.py"))
state_contract = _load("mv_run_state_contract", os.path.join(CRAFT_SCRIPTS, "state_contract.py"))


# ── 停因登记制枚举（单一真值；na() 拒绝未登记停因，消费端 switch 不会静默漏分支）──
STOP_REASONS = frozenset({
    "missing_progress",        # 无 _进度.md/阶段表 → 先 init_project
    "state_inconsistent",      # _设置/_meta/_进度 三者不一致或阶段契约不完整
    "all_stages_done",         # 全部阶段 done → 收尾/发布
    "stale_receipts",          # 已 done 的付费阶段 hash 链失效（假 done）→ 先按 receipt_health 回流
    "blocked_by_gate",         # 前沿阶段 gate 有确定性 error → 按 errors 补前置
    "needs_user_files",        # 等用户提供文件（成品歌/歌词）
    "needs_agent_generation",  # 创作/外部生成阶段（蓝图、出图、出视频内容本身）
    "needs_human_signoff",     # 需具名人工签收（picture lock、挑版评分、发布确认）
    "ready_to_run",            # 有确定性脚本可直接执行（exact_command）
})

# stage key → (停因, exact_command 模板或裸 skill 名, 是否付费/不可逆)
STAGE_ACTIONS = {
    "setup": ("ready_to_run", 'python3 skills/mv/scripts/init_project.py "{root}"', False),
    "song_ingest": ("needs_user_files", "", False),
    "beat": ("ready_to_run",
             'conda run -n cosyvoice python skills/mv/mv-beat/scripts/beat_detect.py "{root}" '
             '--confirm-timing --reviewer <name>', False),
    "lyric_sync": ("ready_to_run",
                   'conda run -n cosyvoice python skills/mv/mv-lyric-sync/scripts/align.py "{root}"', False),
    "script": ("needs_agent_generation", "mv-script", False),
    "script_review": ("needs_agent_generation", "mv-script", False),
    "plan": ("ready_to_run", 'python3 skills/mv/mv-plan/scripts/plan_clips.py "{root}" && '
                             'python3 skills/mv/mv-craft/scripts/progress_set.py "{root}" plan', False),
    "semantic_plan": ("needs_agent_generation", "mv-plan", False),
    "pacing_check": ("ready_to_run", 'python3 skills/mv/mv-score/scripts/score_pacing.py "{root}"', False),
    "image": ("needs_agent_generation", "mv-image", True),
    "picture_lock": ("needs_human_signoff",
                     'python3 skills/mv/mv-craft/scripts/production_pack.py "{root}" && '
                     'python3 skills/mv/mv-craft/scripts/render_animatic.py "{root}" && '
                     'python3 skills/mv/mv-craft/scripts/picture_lock.py "{root}" --reviewer <name>', False),
    "video_jobs": ("ready_to_run", 'python3 skills/mv/mv-video/scripts/video_jobs.py "{root}"', True),
    "video": ("needs_human_signoff",
              'python3 skills/mv/mv-video/scripts/video_jobs.py "{root}" --register <文件> --clip <N> --take <N> '
              '[--seed <seed>] → --score … --reviewer <name> → --select …', True),
    "compose": ("ready_to_run", 'bash skills/mv/mv-compose/mv_compose.sh "{root}"', True),
    "disclosure": (
        "ready_to_run",
        'python3 skills/mv/mv-craft/scripts/ai_usage.py "{root}" '
        '--visual-mode "{visual_mode}" --video-mode "{visual_mode}" --publish-target "{platform}" '
        '--territory <CN|EU|US|逗号分隔> --realism <stylized|photorealistic|mixed> '
        '--real-person <none|authorized> --music-mode <human|AI-assisted|AI-generated> '
        '--human-contribution <具体人工贡献> --reviewer <name>',
        False,
    ),
    "provenance": (
        "ready_to_run",
        'python3 skills/mv/mv-craft/scripts/provenance.py "{root}" '
        '--final "{root}/成片_MV.mp4" --master "{root}/成片_MV_master.mov"',
        False,
    ),
    "review": (
        "needs_human_signoff",
        'python3 skills/mv/mv-review/scripts/mv_check.py "{root}" '
        '--write-receipt --reviewer <name> --notes <完整审片说明>',
        False,
    ),
    "handoff": (
        "needs_human_signoff",
        'python3 skills/mv/mv-craft/scripts/release_decision.py "{root}" '
        '--platform "{platform}" --territory <CN|EU|US|逗号分隔> --operator <name> --notes <发布核验> '
        '--platform-policy-review-status completed --platform-declaration-status <completed|not_applicable> '
        '--visible-label-status <completed|not_applicable> --music-metadata-status <completed|not_applicable> '
        '--machine-label-method <c2pa|platform_metadata|other> '
        '--platform-evidence <项目内平台披露证据> --machine-evidence <项目内机器标识证据> '
        '--submission-status uploaded '
        '--upload-receipt <项目内上传回执> --published-url <真实发布URL> && '
        'python3 skills/mv/mv-craft/scripts/completion.py complete "{root}" handoff '
        '--reviewer <name> --notes <发布确认>',
        False,
    ),
}

# 已 done 也要巡检收据健康度的付费阶段（假 done 主动现形，而非等下次付费 gate 被动报错）。
RECEIPT_HEALTH_STAGES = completion.OUTPUT_HEALTH_STAGES


def na(payload):
    """组装 NextAction 并强校验停因已登记（未登记停因=编排契约破裂，直接抛错）。"""
    reason = payload.get("stop_reason")
    if reason not in STOP_REASONS:
        raise ValueError(f"unregistered stop_reason: {reason!r}（先在 run.py STOP_REASONS 登记并补消费者分支）")
    payload.setdefault("kind", "mv_next_action")
    payload.setdefault("schema_version", 2)
    return payload


def stage_states(root):
    """_进度.md 阶段表 → [(contract_key|None, label, owner, state)]。"""
    try:
        text = progress.read_progress(root)
    except FileNotFoundError:
        return None
    rows = [row for row in progress.parse_stage_rows(text) if not progress.is_retired_external(row)]
    if not rows:
        return None
    label_to_key = {s["label"]: s["key"] for s in contract.stage_table()}
    out = []
    for row in rows:
        label = progress.clean_label(row["label"])
        out.append({
            "key": label_to_key.get(label),
            "label": row["label"],
            "owner": row["owner"],
            "state": progress.state_of(row["status"]),
        })
    return out


def compute_frontier(states):
    for row in states:
        if row["state"] == "done":
            continue
        if row["state"] == "todo" and progress.is_optional(row["label"]):
            continue
        return row
    return None


def receipt_health(root, states, frontier_key):
    """Validate completed stage outputs (not the preflight needed to start them)."""
    done_keys = {row["key"] for row in states if row["state"] == "done" and row["key"]}
    findings = []
    for stage in RECEIPT_HEALTH_STAGES:
        if stage not in done_keys or stage == frontier_key:
            continue
        health = completion.stage_health(root, stage)
        if not health["ok"]:
            findings.append({
                "stage": stage,
                "errors": health["errors"],
                "warnings": health.get("warnings") or [],
                "evidence": health.get("evidence") or {},
            })
    return findings


def build_next_action(root):
    states = stage_states(root)
    if states is None:
        return na({
            "root": root,
            "frontier": None,
            "stop_reason": "missing_progress",
            "gate": None,
            "receipt_health": [],
            "action_card": {
                "headline": "项目未初始化或 _进度.md 缺阶段表",
                "exact_command": STAGE_ACTIONS["setup"][1].format(root=root),
                "to_user": "先用 mv 总调度立项（会问 歌曲输入时序 / MV视觉风格 等选择点）。",
                "paid_or_irreversible": False,
            },
            "stages": [],
        })
    state_audit = state_contract.audit(root, STAGE_ACTIONS)
    runtime = state_audit["derived"]
    if not state_audit["ok"]:
        sync_suffix = "" if state_audit.get("settings_present") else " --bootstrap-settings-from-meta"
        return na({
            "root": root,
            "song_timing": runtime.get("song_timing"),
            "frontier": None,
            "stop_reason": "state_inconsistent",
            "gate": None,
            "receipt_health": [],
            "state_consistency": state_audit,
            "action_card": {
                "headline": "_设置.md / _meta.json / _进度.md 运行时状态不一致",
                "exact_command": (
                    'python3 skills/mv/mv-craft/scripts/state_contract.py sync "{root}"{suffix}'
                ).format(root=root, suffix=sync_suffix),
                "to_user": "先显式同步单一真值和完整阶段表；同步会保留可证明的完成态，并把受设置变更影响的下游阶段退回待办。",
                "paid_or_irreversible": False,
            },
            "stages": states,
        })
    frontier = compute_frontier(states)
    if frontier is None:
        health = receipt_health(root, states, None)
        stale = bool(health)
        return na({
            "root": root,
            "frontier": None,
            "stop_reason": "stale_receipts" if stale else "all_stages_done",
            "gate": None,
            "receipt_health": health,
            "state_consistency": state_audit,
            "action_card": {
                "headline": "已标完成的阶段存在过期/缺失收据" if stale else "全部阶段完成且完成态收据有效",
                "exact_command": "" if stale else 'python3 skills/mv/mv-craft/scripts/completion.py health "{root}" --json'.format(root=root),
                "to_user": (
                    "按 receipt_health 从最早失效阶段回流，不能把阶段表的 [x] 当成产物证据。"
                    if stale else "交付、披露、来源链、总审和具名发布确认均已绑定当前文件。"
                ),
                "paid_or_irreversible": False,
            },
            "stages": states,
        })

    key = frontier["key"]
    stop, command, paid = STAGE_ACTIONS.get(key, ("needs_agent_generation", frontier["owner"], False))
    gate_result = None
    if key:
        errors, warnings = gate.check(root, key)
        gate_result = {"stage": key, "errors": errors, "warnings": warnings}
        if errors:
            stop = "blocked_by_gate"
    # song_ingest：歌已在库则只剩回写进度，不再是等文件。
    if key == "song_ingest" and mv_utils.find_song(root):
        stop = "ready_to_run"
        command = 'python3 skills/mv/mv-craft/scripts/progress_set.py "{root}" song_ingest'
    health = receipt_health(root, states, key)
    if stop not in ("blocked_by_gate",) and health:
        stop = "stale_receipts"
    headline = {
        "blocked_by_gate": f"前沿『{frontier['label']}』被确定性 gate 拦住",
        "stale_receipts": "已完成的付费阶段 hash 链失效（假 done），先回流修复",
        "needs_user_files": "等待用户提供最终成品歌（及按需歌词）",
        "needs_agent_generation": f"前沿『{frontier['label']}』是创作/生成阶段",
        "needs_human_signoff": f"前沿『{frontier['label']}』需要具名人工签收",
        "ready_to_run": f"前沿『{frontier['label']}』可直接执行",
    }[stop]
    to_user = ""
    if stop == "blocked_by_gate":
        to_user = "按 gate.errors 逐条补前置；不要绕过 gate 直接生成正式产物。"
    elif stop == "stale_receipts":
        to_user = "上游真值变化后下游收据已失效；按 receipt_health 从最早失效阶段回流重做。"
    elif stop == "needs_agent_generation":
        to_user = f"由 agent 按 {command if not command.startswith('python3') else frontier['owner']} 的 SKILL.md 执行创作；付费生成前会再过 gate。"
    elif paid:
        to_user = "本阶段花钱/不可逆：执行前与用户确认额度与后端选择。"
    formatted_command = command
    if command:
        formatted_command = command.format(
            root=root,
            visual_mode=runtime.get("ai_visual_usage") or "AI-generated",
            platform=runtime.get("publish_target") or "未定",
        )
    return na({
        "root": root,
        "song_timing": runtime.get("song_timing"),
        "frontier": frontier,
        "stop_reason": stop,
        "gate": gate_result,
        "receipt_health": health,
        "state_consistency": state_audit,
        "action_card": {
            "headline": headline,
            "exact_command": formatted_command,
            "to_user": to_user,
            "paid_or_irreversible": paid,
        },
        "stages": states,
    })


# ── impact：clip 级返工级联（确定性静态映射 × 产物在场核对） ────────────────────

def _step(order, stage, action, command=""):
    return {"order": order, "stage": stage, "action": action, "command": command}


def build_impact(root, clip_id, change):
    """改一个 clip 的 {image|prompt|edit} 后，机器可算的下游返工清单（只列在场产物）。"""
    plan = mv_utils.load_json(os.path.join(root, "分镜", "clip_plan.json"), {}) or {}
    clip = next((c for c in plan.get("clips") or [] if isinstance(c, dict) and c.get("clip_id") == clip_id), None)
    if clip is None:
        return {"error": f"clip_plan 里没有 {clip_id}", "clips": [c.get("clip_id") for c in plan.get("clips") or []]}
    jobs = mv_utils.load_json(os.path.join(root, "出视频", "jobs_manifest.json"), {}) or {}
    job = next((j for j in jobs.get("jobs") or [] if j.get("clip_id") == clip_id), None)
    has_lock = bool((mv_utils.load_json(os.path.join(root, "制片", "picture_lock.json"), {}) or {}).get("accepted"))
    has_master = os.path.exists(os.path.join(root, "成片_MV.mp4")) or os.path.exists(os.path.join(root, "成片_MV_master.mov"))
    steps = []
    n = 0

    def add(stage, action, command=""):
        nonlocal n
        n += 1
        steps.append(_step(n, stage, action, command))

    if change == "edit":
        # 剪辑决定（切点/时长/接缝/顺序）变化 → clip_plan/编辑合同 hash 全链失效。
        add("plan", f"重跑 mv-plan（{clip_id} 的切点/时长/接缝属于编辑合同，改动会换 clip_plan hash）",
            f'python3 skills/mv/mv-plan/scripts/plan_clips.py "{root}"')
        add("plan", "重注入语义分镜并刷新收据", f'python3 skills/mv/mv-plan/scripts/compose_prompts.py "{root}"')
        add("pacing_check", "重跑节奏预检（绑定新 plan）", f'python3 skills/mv/mv-score/scripts/score_pacing.py "{root}"')
        change = "image"  # 编辑变化后按图级级联继续
        add("image", f"检查 {clip_id} 首/尾帧是否仍符合新切点；需要则重出该 clip 图")
    if change == "prompt":
        add("plan", f"改 {clip_id} 的 prompt 后重注入语义收据（semantic_prompts 绑定 clip_plan hash）",
            f'python3 skills/mv/mv-plan/scripts/compose_prompts.py "{root}"')
        add("image", f"用新 prompt 重出 {clip_id} 首帧（及 need_end_frame 时的尾帧）")
        change = "image"
    elif change == "image":
        add("image", f"重出 {clip_id} 首帧（及 need_end_frame 时的尾帧），并登记生成收据",
            f'python3 skills/mv/mv-image/scripts/record_generation.py "{root}" --asset {clip.get("image_path")} '
            "--model <模型> --channel <渠道> --prompt <prompt文件> [--reference …]")
    add("image", "重跑 image_qc（assets_sha256 收据换新，旧报告即过期）",
        f'python3 skills/mv/mv-image/scripts/image_qc.py "{root}"')
    if has_lock:
        add("picture_lock", "picture lock 绑定了该图 hash，已失效：重渲 animatic 并重新具名签收",
            f'python3 skills/mv/mv-craft/scripts/render_animatic.py "{root}" && '
            f'python3 skills/mv/mv-craft/scripts/picture_lock.py "{root}" --reviewer <name>')
    if job:
        registered = [
            t for t in job.get("takes") or []
            if t.get("submit_receipt") or t.get("video_sha256")
        ]
        if registered:
            add("video", f"{clip_id} 已登记 take 的实际 submitted_refs/controls 收据将失效：重出该 clip 视频并重新 --register",
                f'python3 skills/mv/mv-video/scripts/video_jobs.py "{root}" --register <新视频> --clip {clip_id} --take <N>')
            add("video", "重新具名评分并挑版（重登记会自动作废旧 selected）",
                f'python3 skills/mv/mv-video/scripts/video_jobs.py "{root}" --score {clip_id} --take <N> … --reviewer <name> '
                f'&& python3 skills/mv/mv-video/scripts/video_jobs.py "{root}" --select {clip_id} --take <N>')
            add("video", "重跑 inherit_contract + video_qc（含逐缝复核；语义签收绑定视频 hash，需重签）",
                f'python3 skills/mv/mv-video/scripts/inherit_contract.py "{root}" && '
                f'python3 skills/mv/mv-video/scripts/video_qc.py "{root}" --accept-semantic --reviewer <name>')
    if has_master:
        add("compose", "重合成母版/交付版并重跑色彩与 delivery QC",
            f'bash skills/mv/mv-compose/mv_compose.sh "{root}"')
        add("disclosure", "成片变化后刷新具名 AI 使用披露（按当前设置填写）",
            f'python3 skills/mv/mv-craft/scripts/ai_usage.py "{root}" --visual-mode <模式> --video-mode <模式> '
            '--publish-target <平台> --territory <法域> --human-contribution <人工贡献> --reviewer <name>')
        add("provenance", "披露后重建当前 final/master 来源链",
            f'python3 skills/mv/mv-craft/scripts/provenance.py "{root}" --final 成片_MV.mp4 --master 成片_MV_master.mov')
        add("review", "重跑总审并重新具名写 review receipt",
            f'python3 skills/mv/mv-review/scripts/mv_check.py "{root}" --write-receipt --reviewer <name> --notes <说明>')
        add("handoff", "旧 release decision / handoff receipt 已随成片变化失效；重新核平台动作和上传回执")
    return {
        "kind": "mv_clip_impact",
        "schema_version": 1,
        "root": root,
        "clip_id": clip_id,
        "change": change,
        "affected_neighbors": _neighbor_note(plan, clip_id),
        "steps": steps,
    }


def _neighbor_note(plan, clip_id):
    """接缝邻居提示：改图/改视频会影响与前后镜的接缝合同（连续镜尤甚）。"""
    clips = [c for c in plan.get("clips") or [] if isinstance(c, dict)]
    out = []
    for i, c in enumerate(clips):
        if c.get("clip_id") != clip_id:
            continue
        if i > 0:
            prev = clips[i - 1]
            seam = prev.get("seam_contract") or {}
            out.append({"clip_id": prev.get("clip_id"), "position": "prev",
                        "seam": seam.get("type") or seam,
                        "note": "上一镜出缝进入本镜；连续接缝（match_action）时其尾帧目标可能需同步重出"})
        if i + 1 < len(clips):
            seam = c.get("seam_contract") or {}
            out.append({"clip_id": clips[i + 1].get("clip_id"), "position": "next",
                        "seam": seam.get("type") or seam,
                        "note": "本镜出缝进入下一镜；本镜尾帧/末拍变化会影响该接缝签收"})
    return out


def print_next(action):
    print(f"# mv next — {os.path.basename(action['root'])}")
    frontier = action.get("frontier")
    if frontier:
        print(f"[前沿] {frontier['label']} · state={frontier['state']} · key={frontier.get('key')}")
    print(f"[停因] {action['stop_reason']} — {action['action_card']['headline']}")
    if action["action_card"].get("exact_command"):
        print(f"[命令] {action['action_card']['exact_command']}")
    if action["action_card"].get("to_user"):
        print(f"[说明] {action['action_card']['to_user']}")
    if action["action_card"].get("paid_or_irreversible"):
        print("[提醒] 本阶段花钱/不可逆，执行前确认。")
    gate_result = action.get("gate") or {}
    for msg in (action.get("state_consistency") or {}).get("errors") or []:
        print(f"  [state err] {msg}")
    for msg in gate_result.get("errors") or []:
        print(f"  [gate err] {msg}")
    for msg in (gate_result.get("warnings") or [])[:8]:
        print(f"  [gate warn] {msg}")
    for row in action.get("receipt_health") or []:
        for msg in row["errors"]:
            print(f"  [stale {row['stage']}] {msg}")


def print_impact(result):
    if result.get("error"):
        print(f"[err] {result['error']}")
        return
    print(f"# mv impact — {result['clip_id']}（change={result['change']}）")
    for step in result["steps"]:
        print(f"{step['order']}. [{step['stage']}] {step['action']}")
        if step.get("command"):
            print(f"   $ {step['command']}")
    for row in result.get("affected_neighbors") or []:
        print(f"[接缝] {row['position']}={row['clip_id']} · {row['note']}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    p_next = sub.add_parser("next", help="算前沿 + 跑 gate + 结构化停因卡（只读）")
    p_next.add_argument("project_root")
    p_next.add_argument("--json", action="store_true")
    p_impact = sub.add_parser("impact", help="clip 级返工级联（只读）")
    p_impact.add_argument("project_root")
    p_impact.add_argument("--clip", required=True, help="如 Clip_004")
    p_impact.add_argument("--change", choices=("image", "prompt", "edit"), default="image")
    p_impact.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(root):
        print(f"[err] 找不到作品根：{root}", file=sys.stderr)
        return 2
    if args.command == "next":
        action = build_next_action(root)
        if args.json:
            print(json.dumps(action, ensure_ascii=False, indent=2))
        else:
            print_next(action)
        return 0
    result = build_impact(root, args.clip.strip(), args.change)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_impact(result)
    return 0 if not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
