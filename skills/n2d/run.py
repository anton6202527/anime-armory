#!/usr/bin/env python3
"""n2d 编排器 —— 把"找前沿 → 跑确定性前置 → 停在第一个决策/花钱/合规点"收敛成一个入口。

设计契约见 docs/n2d-编排器设计.md（评审 v0.1）。核心约束：stage skill 混着"确定性脚本"
与"代理创作/花钱生成"，所以本编排器不把 stage 当 subprocess 一把梭跑完——它只**自动跑掉
确定性前置**（gate / model-router / doctor / compliance / 身份矩阵刷新），跑到第一个
「需要脑子 / 需要钱包 / 需要签字」的点就停，交回一张结构化「下一步动作卡」NextAction。

用法：
    python3 run.py next <作品根> [第N集] [--json] [--auto]

铁规对齐：VCS-free（只读文件/内容快照，不调 git）；契约单一真值（阶段图/列名/gate stage
一律读 STAGE_GRAPH/stage_of/gate.py，不复制）；选择点经设置适配层、不 branch 菜单文字；
只读/只跑确定性前置，绝不自行花钱、自行执行创作、自行换后端。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

_LIB = os.path.abspath(os.path.join(os.path.dirname(__file__), "_lib"))
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from n2d_contract import stage_for_key, stage_for_progress_column  # 契约真值（facade）
from n2d_route import normalize_episode, parse_progress, stage_of, summarize

try:
    from settings import get_setting, get_setting_spec, load_settings
except ImportError:  # pragma: no cover - 包式导入兜底
    from n2d_settings import get_setting, get_setting_spec, load_settings

SKILLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ── 阶段分类（key 来自 STAGE_GRAPH，不另立并行表，只贴标签）──────────────────
AGENT_GEN_STAGES = {"script_stage1", "script_stage2", "image_prompt", "video_prompt"}
GENERATION_STAGES = {"voice", "image", "video", "compose"}
PAID_STAGES = {"image", "video", "compose"}          # 进这些前必过合规闸门
ROUTER_STAGES = {"video_prompt", "video"}            # 出视频前置：先写模型路由表
FIRST_RUN_CHOICES = ("制作模式", "生视频模型", "生视频渠道", "基础视觉风格")
# 各生成阶段"放行前必问"的选择点（菜单随动作卡一起给，不另起一次 needs_choice）
STAGE_MENU = {
    "voice": ("配音后端", False),    # (选择点, 是否每次必问)
    "image": ("生成粒度", True),
    "video": ("生成粒度", True),
    "compose": ("BGM来源", True),
}


# ── 探针结果（decide() 的纯输入，便于测试注入）────────────────────────────────
@dataclass
class Probes:
    env_missing: Optional[str] = None            # 该阶段所需后端缺失名；None=可跑
    gate: Optional[Dict[str, Any]] = None        # {stage,blocked,return_to_stage,affected_artifacts,rerun_scope,findings_path}
    compliance_gap: Optional[bool] = None        # True=有缺口；None=未检/检不了
    pending_choices: List[str] = field(default_factory=list)  # 首跑必给但尚未显式记录的选择点
    prework: List[Dict[str, Any]] = field(default_factory=list)  # 本轮自动跑掉的确定性步骤记录


# ── 前沿解析（复用 stage_of/summarize，不重算路由）────────────────────────────
def resolve_frontier(root: str, ep: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """返回 stage_of 的 route dict（{ep,col,label,skill,cmd,note}），已成片/找不到返回 None。"""
    header, rows = parse_progress(root)
    if ep:
        ep = normalize_episode(ep)
        row = next((r for r in rows if r["_ep"] == ep), None)
        if row is None:
            return None
        route = stage_of(root, row, header)
    else:
        route = summarize(root)["first"]
    if not route or not route.get("col"):
        return None
    return route


def stage_key_of(route: Dict[str, Any]) -> Optional[str]:
    """从 route 反查 STAGE_GRAPH 的 stage key。

    特例：先出视频后配音模式下，compose 前沿会被重定向成 label='补真实配音'、skill='n2d-voice'
    （col 仍是 '成片'）——这里按 voice 处理，否则 stage_for_progress_column('成片') 会误判成 compose。
    """
    if route.get("label") == "补真实配音" or route.get("skill") == "n2d-voice" and route.get("col") == "成片":
        return "voice"
    spec = stage_for_progress_column(route["col"])
    return spec["key"] if spec else None


# ── 纯决策（全部测试覆盖；不做任何 I/O）──────────────────────────────────────
def decide(root: str, route: Dict[str, Any], stage_key: str, probes: Probes) -> Dict[str, Any]:
    spec = stage_for_key(stage_key) or {}
    frontier = {
        "ep": route.get("ep"),
        "stage_key": stage_key,
        "label": route.get("label") or spec.get("label"),
        "owner": route.get("skill") or spec.get("owner"),
    }

    def na(stop_reason: str, card: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "frontier": frontier,
            "prework": probes.prework,
            "stop_reason": stop_reason,
            "action_card": card,
            "gate": probes.gate,
            "auto_continue": stop_reason == "auto_ran",
        }

    ep = frontier["ep"]
    cmd = (spec.get("command") or "").format(root=root, ep=ep)

    # 1. env 缺失 —— 不让代理跑到花钱工位才发现
    if probes.env_missing:
        return na("env_missing", {
            "headline": f"{ep} {frontier['label']}：所需后端不可用（{probes.env_missing}）",
            "to_user": f"该阶段后端 {probes.env_missing} 探测不可用。先修复/换后端，或选占位路线后再放行。",
            "exact_command": cmd,
        })

    # 2. gate 阻断 —— 透传 gate.py 结构化字段，指向最小返工
    if probes.gate and probes.gate.get("blocked"):
        g = probes.gate
        return na("blocked_by_gate", {
            "headline": f"{ep} {frontier['label']}：gate「{g.get('stage')}」阻断",
            "to_user": f"先按 return_to_stage={g.get('return_to_stage')} 补齐再来；细节见 {g.get('findings_path')}。",
            "exact_command": cmd,
        })

    # 3. 合规缺口（仅花钱档）
    if stage_key in PAID_STAGES and probes.compliance_gap:
        return na("needs_compliance", {
            "headline": f"{ep} {frontier['label']}：合规缺口未补齐（花钱前阻断）",
            "to_user": "跑 n2d-compliance --check 补齐 evidence/profile 后再进付费 gate。绝不放行。",
            "exact_command": f"python3 skills/n2d-compliance/scripts/compliance.py {root} {ep} --check",
        })

    # 4. 首跑必给但尚未显式选过的选择点（制作模式/生视频模型/渠道/基础视觉风格）
    if probes.pending_choices:
        return na("needs_choice", {
            "headline": f"{ep} 开局必给选择包（之后沉默沿用，随时可改）",
            "to_user": "新作品首跑必须显式选一次以下选项，再继续：" + "、".join(probes.pending_choices),
            "menu": [_menu(root, cp) for cp in probes.pending_choices],
            "exact_command": cmd,
        })

    # 5. 代理创作（LLM 写剧本/分镜/出图文案）——脚手架已就绪，停下交回代理
    if stage_key in AGENT_GEN_STAGES:
        return na("needs_agent_gen", {
            "headline": f"{ep} {frontier['label']}：脚手架就绪，待代理生成",
            "to_user": f"读 {frontier['owner']} 的 prompt 包 → 调 LLM 生成 → 注入项目；完成后回写进度再 run next。",
            "exact_command": cmd,
            "writeback_after": _writeback_hint(root, ep, spec),
        })

    # 6. 花钱/重活生成 —— 停下，附该阶段"放行前必问"菜单
    if stage_key in GENERATION_STAGES:
        cp, _every = STAGE_MENU.get(stage_key, (None, False))
        card = {
            "headline": f"{ep} {frontier['label']}（花钱·不可逆，需你放行）",
            "to_user": f"确认后再生成；{frontier['label']}是最贵环节之一，放行 ≠ 安全。",
            "exact_command": cmd,
            "writeback_after": _writeback_hint(root, ep, spec),
        }
        if cp:
            card["menu"] = [_menu(root, cp)]
        return na("needs_payment_confirm", card)

    # 7. 纯确定性（当前无此类路由阶段，留给将来）
    return na("auto_ran", {"headline": f"{ep} {frontier['label']}：确定性步骤已自动完成"})


def _menu(root: str, choice_point: str) -> Dict[str, Any]:
    """选择点菜单：选项来自 SettingSpec（适配层真值），预选=设置里上次值；不 branch 菜单文字。"""
    spec = None
    try:
        spec = get_setting_spec(choice_point, "n2d")
    except Exception:
        pass
    options = list(getattr(spec, "choices", ()) or [])
    return {
        "choice_point": choice_point,
        "options": options,
        "default_preselect": get_setting(root, choice_point, None) or None,
    }


def _writeback_hint(root: str, ep: str, spec: Dict[str, Any]) -> str:
    cols = list(spec.get("progress_columns", ()))
    col = cols[0] if cols else "<列名>"
    return f"python3 skills/n2d/progress.py set {root} {ep} {col} <值>"


# ── 真实探针（subprocess/import；全部防御性，绝不让编排器崩）──────────────────
def _run(cmd: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=900)


def _parse_trailing_json(stdout: str) -> Dict[str, Any]:
    """取 stdout 末尾的 JSON 块。dashboard gate 先打 alerts、最后 json.dumps(indent=2) 多行输出，
    所以不能只看最后一行——从末尾逐行上移，找到第一个能整体解析成 dict 的后缀。"""
    lines = (stdout or "").splitlines()
    for i in range(len(lines)):
        if lines[len(lines) - 1 - i].lstrip().startswith("{"):
            try:
                obj = json.loads("\n".join(lines[len(lines) - 1 - i:]))
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
    return {}


def gather_probes(root: str, route: Dict[str, Any], stage_key: str) -> Probes:
    spec = stage_for_key(stage_key) or {}
    p = Probes()
    ep = route.get("ep")

    # doctor：能力/精度档（只探不改、不花钱）
    try:
        import doctor
        caps = doctor.collect(root)
        p.prework.append({"step": "doctor", "status": "ok",
                          "image_backend": (caps.get("image_backend") or {}).get("status"),
                          "voice": caps.get("voice")})
        img = caps.get("image_backend") or {}
        if stage_key in ("image_prompt", "image") and img.get("status") in ("down", "error", "missing"):
            p.env_missing = f"{img.get('name')}（{img.get('status')}）"
    except Exception as e:  # pragma: no cover - 环境相关
        p.prework.append({"step": "doctor", "status": "skip", "detail": str(e)[:120]})

    # model-router：出视频前置（写理论路由表），幂等
    if stage_key in ROUTER_STAGES:
        script = os.path.join(SKILLS_DIR, "n2d-model-router", "scripts", "router.py")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, root, ep, "--write"])
                p.prework.append({"step": "model_router", "status": "ok" if r.returncode == 0 else "warn"})
            except Exception as e:  # pragma: no cover
                p.prework.append({"step": "model_router", "status": "skip", "detail": str(e)[:120]})

    # gate：有 gate_stage 的阶段先过 dashboard gate（退出码 1=block）
    gate_stage = spec.get("gate_stage")
    if gate_stage:
        script = os.path.join(SKILLS_DIR, "n2d-dashboard", "scripts", "dashboard.py")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, "gate", root, ep, "--stage", gate_stage])
                out = _parse_trailing_json(r.stdout)
                blocked = r.returncode != 0
                p.gate = {"stage": gate_stage, "blocked": blocked,
                          "findings_path": out.get("findings_path"),
                          "return_to_stage": None, "affected_artifacts": [], "rerun_scope": None}
                if blocked and out.get("findings_path") and os.path.exists(out["findings_path"]):
                    _enrich_gate(p.gate, out["findings_path"])
                p.prework.append({"step": "gate", "stage": gate_stage,
                                  "status": "block" if blocked else "pass"})
            except Exception as e:  # pragma: no cover
                p.prework.append({"step": "gate", "stage": gate_stage, "status": "skip", "detail": str(e)[:120]})

    # compliance：花钱档前置检查
    if stage_key in PAID_STAGES:
        script = os.path.join(SKILLS_DIR, "n2d-compliance", "scripts", "compliance.py")
        if os.path.exists(script):
            try:
                r = _run([sys.executable, script, root, ep, "--check"])
                p.compliance_gap = (r.returncode != 0)
                p.prework.append({"step": "compliance", "status": "gap" if p.compliance_gap else "ok"})
            except Exception as e:  # pragma: no cover
                p.prework.append({"step": "compliance", "status": "skip", "detail": str(e)[:120]})

    # 首跑必给：仅在 script_stage1 前沿，挑出尚未显式记录的选择点
    if stage_key == "script_stage1":
        try:
            recorded = load_settings(root)
            p.pending_choices = [k for k in FIRST_RUN_CHOICES if k not in recorded]
        except Exception:  # pragma: no cover
            p.pending_choices = []

    return p


def _enrich_gate(gate: Dict[str, Any], findings_path: str) -> None:
    """从 gate_findings 文件取首条 finding 的回退字段（best-effort）。"""
    try:
        data = json.load(open(findings_path, encoding="utf-8"))
    except Exception:
        return
    findings = data.get("findings") if isinstance(data, dict) else None
    first = findings[0] if isinstance(findings, list) and findings else {}
    if isinstance(first, dict):
        gate["return_to_stage"] = first.get("return_to_stage") or gate.get("return_to_stage")
        gate["affected_artifacts"] = first.get("affected_artifacts") or gate.get("affected_artifacts")
        gate["rerun_scope"] = first.get("rerun_scope") or gate.get("rerun_scope")


# ── 顶层：一次步进（v1：每个路由阶段都是 stop-point，--auto 预留给将来确定性阶段）──
def next_action(root: str, ep: Optional[str] = None, auto: bool = False) -> Dict[str, Any]:
    while True:
        route = resolve_frontier(root, ep)
        if route is None:
            return {"frontier": None, "prework": [], "stop_reason": "done",
                    "action_card": {"headline": "🎉 该作品/该集已成片，无下一步"},
                    "gate": None, "auto_continue": False}
        stage_key = stage_key_of(route)
        if stage_key is None:
            return {"frontier": {"ep": route.get("ep"), "label": route.get("label")},
                    "prework": [], "stop_reason": "unknown_stage",
                    "action_card": {"headline": f"无法识别阶段：{route}"},
                    "gate": None, "auto_continue": False}
        probes = gather_probes(root, route, stage_key)
        na = decide(root, route, stage_key, probes)
        if auto and na["auto_continue"]:
            continue  # 仅当出现纯确定性阶段时才真正跨阶段推进
        return na


# ── 输出 ──────────────────────────────────────────────────────────────────────
def render_human(na: Dict[str, Any]) -> str:
    lines = []
    f = na.get("frontier") or {}
    if f.get("ep"):
        lines.append(f"前沿：{f.get('ep')} · {f.get('label')}（{f.get('owner')}）")
    for pw in na.get("prework", []):
        lines.append(f"  ✔ 前置 {pw.get('step')}: {pw.get('status')}" + (f" [{pw.get('stage')}]" if pw.get('stage') else ""))
    card = na.get("action_card") or {}
    lines.append("")
    lines.append(f"⏸ 停因：{na.get('stop_reason')}")
    lines.append(f"   {card.get('headline','')}")
    if card.get("to_user"):
        lines.append(f"   {card['to_user']}")
    for m in card.get("menu", []) or []:
        opts = " / ".join(m.get("options", []) or []) or "(见选择点文档)"
        lines.append(f"   选择点【{m['choice_point']}】：{opts}（上次：{m.get('default_preselect') or '未记录'}）")
    if card.get("exact_command"):
        lines.append(f"   命令：{card['exact_command']}")
    if card.get("writeback_after"):
        lines.append(f"   完成后回写：{card['writeback_after']}")
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    if not argv or argv[0] != "next":
        print("用法: run.py next <作品根> [第N集] [--json] [--auto]")
        return 1
    rest = argv[1:]
    as_json = "--json" in rest
    auto = "--auto" in rest
    pos = [a for a in rest if not a.startswith("--")]
    if not pos:
        print("用法: run.py next <作品根> [第N集] [--json] [--auto]")
        return 1
    root = pos[0].rstrip("/")
    ep = pos[1] if len(pos) > 1 else None
    na = next_action(root, ep, auto=auto)
    print(json.dumps(na, ensure_ascii=False, indent=2) if as_json else render_human(na))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
