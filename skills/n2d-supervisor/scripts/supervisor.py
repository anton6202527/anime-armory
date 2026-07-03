#!/usr/bin/env python3
"""n2d supervisor: consume run.py NextAction and produce a specialist handoff plan."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILLS_DIR = SKILL_DIR.parent
N2D_DIR = SKILLS_DIR / "n2d"
N2D_LIB = N2D_DIR / "_lib"
if str(N2D_LIB) not in sys.path:
    sys.path.insert(0, str(N2D_LIB))

from n2d_action_registry import specialist_for_stage, stage_action_spec  # noqa: E402


KIND = "n2d_supervisor_plan"
VERSION = 1

# agentic production 五类失效模式的运行时护栏默认值（2026 编排前沿：幻觉级联 / 上下文丢约束 /
# 无界循环成本失控 / 工具误用 / 级联超时）。supervisor 是 advisory 规划层，这些是它发给消费 agent 的
# 必须遵守的运行时契约——边界声明之外补上「跑起来怎么不失控」。
DEFAULT_MAX_DISPATCH_ROUNDS = 6        # 同一前沿最多自动派发轮数（到顶升人审，防重试成本失控）
DEFAULT_SPECIALIST_TIMEOUT_SEC = 600   # 单 specialist 调用超时预算（防级联超时挂死整条流水）


def runtime_guardrails(dispatch: Dict[str, Any], *, round_index: int = 0,
                       max_rounds: int = DEFAULT_MAX_DISPATCH_ROUNDS,
                       specialist_timeout_sec: int = DEFAULT_SPECIALIST_TIMEOUT_SEC) -> Dict[str, Any]:
    """五类失效模式的运行时护栏（advisory 契约·纯函数·可测）。消费 agent 必须遵守。"""
    forbidden = list(dispatch.get("forbidden_operations") or [])
    human_gate = dict(dispatch.get("human_gate") or {})
    loop_exhausted = int(round_index) >= int(max_rounds)
    # 约束持久化指纹：固化当前 forbidden+human_gate，消费 agent 每轮须回带同一指纹，防上下文溢出悄悄丢约束。
    blob = json.dumps({"forbidden": forbidden, "human_gate": human_gate}, ensure_ascii=False, sort_keys=True)
    return {
        "max_dispatch_rounds": int(max_rounds),
        "round_index": int(round_index),
        "loop_budget_exhausted": loop_exhausted,                         # 无界循环→成本失控
        "specialist_timeout_seconds": int(specialist_timeout_sec),       # 级联超时隔离
        "outputs_require_gate_recheck": True,                            # 幻觉级联：产物非既定事实，须重过 gate
        "carried_constraints": {"forbidden_operations": forbidden, "human_gate": human_gate},  # 上下文丢约束
        "constraints_fingerprint": hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16],
        "tool_use_policy": "只调 run.py 声明的确定性 prework 与选定 specialist；未声明工具调用视为越界（工具误用护栏）",
        "on_exhaustion": "loop_budget_exhausted=true → 停止自动派发、升级人工决策（不得继续自动重试烧成本）",
    }


def _load_run_module():
    path = N2D_DIR / "run.py"
    spec = importlib.util.spec_from_file_location("n2d_run_for_supervisor", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _safe_slug(value: str) -> str:
    return str(value or "全集").replace("/", "_").replace(" ", "_")


def round_state_path(root: str) -> Path:
    return Path(root) / "生产数据" / "supervisor" / "round_state.json"


def _read_round_state(root: str) -> Dict[str, Any]:
    try:
        data = json.loads(round_state_path(root).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def frontier_round_key(episode: str, stage_key: str) -> str:
    """轮次计数键＝前沿身份（集×阶段）。前沿推进=新键=自动从 0 起；同前沿反复重试=同键累加。"""
    return f"{_safe_slug(episode or '全集')}::{_safe_slug(stage_key or 'unknown')}"


def resolve_effective_round(root: str, key: str, caller_round: int, *, persist: bool) -> int:
    """自管轮次，不信调用方传参（堵「驱动每轮传 --round 0 绕过循环预算」）。

    effective = max(调用方传入, 持久记录)；persist=True 时把 effective+1 写回——即便调用方恒传 0，
    持久计数仍随每次派发单调爬升直至耗尽。原子写·永不抛。"""
    state = _read_round_state(root)
    entry = state.get(key) if isinstance(state.get(key), dict) else {}
    persisted = entry.get("round")
    persisted = int(persisted) if isinstance(persisted, int) and persisted >= 0 else 0
    try:
        caller = max(0, int(caller_round))
    except (TypeError, ValueError):
        caller = 0
    effective = max(caller, persisted)
    if persist:
        state[key] = {"round": effective + 1}
        path = round_state_path(root)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f"{path.name}.tmp.{os.getpid()}")
            tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            pass
    return effective


def classify_human_gate(stop_reason: str) -> Dict[str, Any]:
    if stop_reason in {"needs_choice", "needs_payment_confirm", "needs_compliance", "needs_acceptance_signoff"}:
        return {"required": True, "reason": stop_reason}
    if stop_reason.startswith("blocked_by_") or stop_reason in {"prework_failed", "capability_evidence_required", "env_missing"}:
        return {"required": True, "reason": "repair_or_decision_required"}
    return {"required": False, "reason": ""}


def dispatch_for(next_action: Dict[str, Any]) -> Dict[str, Any]:
    frontier = next_action.get("frontier") or {}
    stage_key = str(frontier.get("stage_key") or "")
    stop_reason = str(next_action.get("stop_reason") or "")
    action = next_action.get("action_contract") or stage_action_spec(stage_key)
    specialist = (next_action.get("action_card") or {}).get("specialist") or specialist_for_stage(stage_key)
    human_gate = classify_human_gate(stop_reason)
    should_call = stop_reason in {"needs_agent_gen"} or (
        stop_reason == "needs_payment_confirm" and stage_key in {"compose", "review"}
    )
    if human_gate["required"] and stop_reason != "needs_agent_gen":
        should_call = False
    return {
        "stage_key": stage_key,
        "stop_reason": stop_reason,
        "specialist": specialist,
        "should_call_specialist": should_call,
        "human_gate": human_gate,
        "context_pack": (next_action.get("action_card") or {}).get("context_pack"),
        "creative_loop": (next_action.get("action_card") or {}).get("creative_loop"),
        "action_contract": action,
        "allowed_operations": [
            "run deterministic prework already declared by run.py",
            "read context_pack before opening full references",
            "call the selected specialist for draft/evaluation when should_call_specialist=true",
            "write supervisor plan under 生产数据/supervisor",
        ],
        "forbidden_operations": [
            "execute paid generation",
            "override compliance or gate blocks",
            "change backend without adapter evidence",
            "write _进度.md directly",
            "replace stage skill contracts",
        ],
    }


def build_plan(root: str, ep: Optional[str] = None, *, auto: bool = False,
               round_index: int = 0, max_rounds: int = DEFAULT_MAX_DISPATCH_ROUNDS,
               track_rounds: bool = False, echo_fingerprint: Optional[str] = None) -> Dict[str, Any]:
    run = _load_run_module()
    next_action = run.next_action(root, ep, auto=auto)
    dispatch = dispatch_for(next_action)
    episode = (next_action.get("frontier") or {}).get("ep") or ep or ""
    # 自管轮次：从持久状态推导有效轮数，不全信调用方传参（track_rounds=True 时还会写回 +1）。
    effective_round = resolve_effective_round(
        root, frontier_round_key(episode, dispatch.get("stage_key") or ""),
        round_index, persist=track_rounds)
    guardrails = runtime_guardrails(dispatch, round_index=effective_round, max_rounds=max_rounds)
    # 无界循环护栏：自动派发轮数到顶 → 强制停止派发、升级人审，不得继续自动重试烧成本。
    if guardrails["loop_budget_exhausted"] and dispatch.get("should_call_specialist"):
        dispatch["should_call_specialist"] = False
        dispatch["loop_escalation"] = (
            f"已达自动派发上限 {max_rounds} 轮仍未收敛 → 停止自动派发，升级人工决策（防重试成本失控）。")
    # 约束指纹回带校验：调用方声称携带的指纹若与当前不符 → 上下文丢失/篡改约束 → 停自动派发、要求重新同步。
    if echo_fingerprint is not None and str(echo_fingerprint) != guardrails["constraints_fingerprint"]:
        dispatch["should_call_specialist"] = False
        dispatch["constraints_drift"] = (
            f"回带约束指纹 {echo_fingerprint} ≠ 当前 {guardrails['constraints_fingerprint']}："
            "消费 agent 可能已丢失/篡改 forbidden 或 human_gate 约束 → 停止自动派发，重新同步约束后再继续。")
    dispatch["runtime_guardrails"] = guardrails
    return {
        "kind": KIND,
        "version": VERSION,
        "root": root,
        "episode": episode,
        "next_action": next_action,
        "dispatch": dispatch,
        "summary": {
            "stop_reason": next_action.get("stop_reason"),
            "stage_key": dispatch.get("stage_key"),
            "specialist": (dispatch.get("specialist") or {}).get("name"),
            "human_gate_required": (dispatch.get("human_gate") or {}).get("required"),
            "should_call_specialist": dispatch.get("should_call_specialist"),
            "round_index": effective_round,
            "loop_budget_exhausted": guardrails["loop_budget_exhausted"],
            "constraints_drift": bool(dispatch.get("constraints_drift")),
        },
    }


def render_markdown(plan: Dict[str, Any]) -> str:
    summary = plan.get("summary") or {}
    dispatch = plan.get("dispatch") or {}
    specialist = dispatch.get("specialist") or {}
    lines = [
        "# n2d Supervisor Plan",
        "",
        f"- 集：{plan.get('episode') or '—'}",
        f"- 阶段：{summary.get('stage_key')}",
        f"- 停因：{summary.get('stop_reason')}",
        f"- specialist：{summary.get('specialist')}",
        f"- human gate：{summary.get('human_gate_required')}",
        f"- call specialist：{summary.get('should_call_specialist')}",
        "",
        "## Specialist",
        "",
        f"- scope：{specialist.get('scope')}",
        "",
        "## Allowed",
        "",
    ]
    lines.extend(f"- {item}" for item in dispatch.get("allowed_operations") or [])
    lines.extend(["", "## Forbidden", ""])
    lines.extend(f"- {item}" for item in dispatch.get("forbidden_operations") or [])
    g = dispatch.get("runtime_guardrails") or {}
    if g:
        lines.extend(["", "## Runtime Guardrails（五类失效模式护栏）", "",
                      f"- 派发轮 {g.get('round_index')}/{g.get('max_dispatch_rounds')}　循环预算耗尽：{g.get('loop_budget_exhausted')}",
                      f"- specialist 超时预算：{g.get('specialist_timeout_seconds')}s（级联超时隔离）",
                      f"- 产物须重过 gate：{g.get('outputs_require_gate_recheck')}（防幻觉级联当既定事实）",
                      f"- 约束指纹：`{g.get('constraints_fingerprint')}`（每轮回带，防上下文丢约束）",
                      f"- 工具策略：{g.get('tool_use_policy')}"])
        if dispatch.get("loop_escalation"):
            lines.append(f"- ⚠ {dispatch['loop_escalation']}")
        if dispatch.get("constraints_drift"):
            lines.append(f"- ⚠ {dispatch['constraints_drift']}")
    context = dispatch.get("context_pack") or {}
    creative = dispatch.get("creative_loop") or {}
    lines.extend(["", "## Packs", ""])
    if context:
        lines.append(f"- context：`{context.get('relpath')}`")
    if creative:
        lines.append(f"- creative loop：`{creative.get('relpath')}`")
    lines.append("")
    return "\n".join(lines)


def write_plan(plan: Dict[str, Any]) -> Dict[str, str]:
    root = Path(str(plan["root"]))
    ep = _safe_slug(str(plan.get("episode") or "全集"))
    stage = _safe_slug(str((plan.get("summary") or {}).get("stage_key") or "unknown"))
    out_dir = root / "生产数据" / "supervisor"
    out_dir.mkdir(parents=True, exist_ok=True)
    path_json = out_dir / f"supervisor_plan_{ep}_{stage}.json"
    path_md = path_json.with_suffix(".md")
    path_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path_md.write_text(render_markdown(plan), encoding="utf-8")
    return {"json": str(path_json), "markdown": str(path_md)}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="n2d supervisor")
    sub = ap.add_subparsers(dest="cmd", required=True)
    nxt = sub.add_parser("next", help="build supervisor plan from run.py next")
    nxt.add_argument("root")
    nxt.add_argument("episode", nargs="?")
    nxt.add_argument("--auto", action="store_true")
    nxt.add_argument("--write", action="store_true")
    nxt.add_argument("--json", action="store_true")
    nxt.add_argument("--round", type=int, default=0, help="调用方自报已派发轮数（与持久计数取大，不被信任为唯一来源）")
    nxt.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_DISPATCH_ROUNDS,
                     help="自动派发轮数上限，到顶升人审")
    nxt.add_argument("--echo-fingerprint", default=None,
                     help="上一轮回带的约束指纹；与当前不符即判定上下文丢约束、停自动派发")
    nxt.add_argument("--no-track-rounds", action="store_true",
                     help="只读规划，不把本次计入持久派发轮数（默认 CLI 会自管轮次累加）")
    ns = ap.parse_args(argv)
    if ns.cmd == "next":
        plan = build_plan(ns.root.rstrip("/"), ns.episode, auto=ns.auto,
                          round_index=ns.round, max_rounds=ns.max_rounds,
                          track_rounds=not ns.no_track_rounds, echo_fingerprint=ns.echo_fingerprint)
        if ns.write:
            plan["outputs"] = write_plan(plan)
        if ns.json:
            print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(render_markdown(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
