#!/usr/bin/env python3
"""实体在场契约机检（entity presence·advisory）——参照同仓成熟视频线 storyboard
`entity_schedule`（required/offscreen/forbidden_presence 逐镜实体排程）的漫画重实现。

为什么存在：2026-07-17 实证（第1话 P015 虎妖画成四足普通虎、无人拦截）暴露的链条里，
脚本层的非角色实体是**自由文本**——description/art_notes 写"虎妖/断刀/荒野"，但只要
references/characters 忘绑对应 ID，出图就不带参考、事后机检也不核对该实体。现有机检：
`continuity_audit` 只查状态链、`reentry_context_audit` 只查"读者认不认识"、reference_planner
只处方**已绑定**的角色——**没有任何脚本查「画面文本提到的已登记实体，这格绑了没有」**。
视频线用 entity_schedule 三清单（必在/画外/禁入）+ video_preflight 拦缺排程；漫画数据结构化
程度够（characters[]/references[]/scene_anchor_id），一个脚本即可低误报覆盖。

两查（全 advisory·审不是门）：

  ① 提到未绑定（mentioned_not_bound·warn/info）：某格画面面文本（description/art_notes/
     location）出现 registry 已登记实体的 display_name/别名，但该格 characters、
     character_bindings、references、scene_anchor_id 都没绑它 → 出图不会附该实体参考，
     一致性裸奔。画面面命中=warn（描述写了=应该入画）；仅台词/旁白命中=info（可能只是
     口头提及、不一定入画，交人判）。STYLE_ 风格锚不是画面实体，跳过。
  ② entity_schedule 契约（渐进采用·panel 可选字段）：若某格写了
     `entity_schedule: {required_presence: [], offscreen_presence: [], forbidden_presence: []}`
     则校验：required ⊄ 绑定集 → required_entity_unbound（warn）；
     required ∩ forbidden → presence_contract_conflict（warn）；
     forbidden ∩ 绑定集 → forbidden_entity_bound（warn）。
     没写 entity_schedule 的格不报错——报告里给出 derived_schedule（由 characters+references
     派生的"必在"清单）供逐步升级到显式契约。

诚实边界（写死）：名称匹配是子串命中（中文无分词），别名要靠 registry.assets[*].aliases
人工维护；匹配不到 ≠ 实体没画错，命中 = warn 交人判。本检治"忘绑参考"，不治"绑了仍画错"
（那是 vlm_judge/character_consistency 的事，两层正交）。

用法（与本线其它 advisory 机检同签名）：
  python3 entity_presence_audit.py <作品根> 第N话 [--write] [--json] [--strict]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

VERSION = 1
KIND = "comic_entity_presence_audit"

# 画面面字段：写在这里=承诺入画。台词/旁白只是提及，单独降档 info。
VISUAL_FIELDS = ("description", "art_notes", "location")
STORY_FIELDS = ("dialogue", "narration")
# 风格锚不是画面实体；SYS_ 系统面板类通常后期嵌字，不强制逐格绑定。
SKIP_PREFIXES = ("STYLE_",)
# 生物/动物前缀：这类实体一旦"画面提到但没绑参考"，模型会自由发挥物种形态——
# 正是「背景该是虎妖却画成别的生物」的病根，比忘绑一件道具后果重。单独出码醒目化。
CREATURE_PREFIXES = ("MON_", "BEAST_", "ANIMAL_")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def normalize_chapter(value: str) -> str:
    value = str(value or "").strip()
    return value if value.startswith("第") else f"第{value}话"


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def finding(code: str, panel_id: str, message: str, *, severity: str = "warn", entity: str = "") -> Dict[str, Any]:
    return {"severity": severity, "code": code, "panel_id": panel_id, "entity": entity, "message": message}


def registry_names(root: Path) -> Dict[str, List[str]]:
    """asset_id → 可命中的名称列表（display_name/name/aliases，去重去空）。"""
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {}) or {}
    assets = registry.get("assets") if isinstance(registry.get("assets"), Mapping) else {}
    out: Dict[str, List[str]] = {}
    for aid, asset in assets.items():
        if not isinstance(asset, Mapping) or str(aid).startswith(SKIP_PREFIXES):
            continue
        names: List[str] = []
        for key in ("display_name", "name"):
            value = str(asset.get(key) or "").strip()
            if value:
                names.append(value)
        aliases = asset.get("aliases")
        if isinstance(aliases, Sequence) and not isinstance(aliases, (str, bytes)):
            names.extend(str(a).strip() for a in aliases if str(a).strip())
        # 太短的名字（单字）子串误命中率过高，直接不用。
        deduped = sorted({n for n in names if len(n) >= 2}, key=len, reverse=True)
        if deduped:
            out[str(aid)] = deduped
    return out


def panel_text(panel: Mapping[str, Any], fields: Sequence[str]) -> str:
    parts: List[str] = []
    for key in fields:
        value = panel.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, Sequence):
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, Mapping):
                    parts.append(str(item.get("text") or item.get("content") or ""))
    return "\n".join(parts)


def bound_ids(panel: Mapping[str, Any]) -> Set[str]:
    out: Set[str] = set()
    for key in ("characters", "references"):
        value = panel.get(key)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            out.update(str(item) for item in value if isinstance(item, str))
    for binding in panel.get("character_bindings") or []:
        if isinstance(binding, Mapping) and binding.get("character_id"):
            out.add(str(binding["character_id"]))
    for key in ("scene_anchor_id", "scene_family"):
        value = str(panel.get(key) or "").strip()
        if value:
            out.add(value)
    return out


def schedule_ids(value: Any) -> List[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [str(item).split("/", 1)[0] for item in value if str(item).strip()]
    return []


def check_panel(panel: Mapping[str, Any], names: Mapping[str, List[str]]) -> List[Dict[str, Any]]:
    pid = str(panel.get("panel_id") or "?")
    bound = bound_ids(panel)
    findings: List[Dict[str, Any]] = []

    visual = panel_text(panel, VISUAL_FIELDS)
    story = panel_text(panel, STORY_FIELDS)
    # ack-or-fix：panel 可写 unbound_mention_ack: {ENTITY_ID: "一句话理由"}，
    # 显式签收"提到但不入画"的决定 → 该实体降档 info（human_acceptance 同款模式）。
    # 空理由不算签收。
    acks = panel.get("unbound_mention_ack") if isinstance(panel.get("unbound_mention_ack"), Mapping) else {}
    for aid, name_list in names.items():
        if aid in bound:
            continue
        hit = next((n for n in name_list if n in visual), "")
        if hit:
            ack_reason = str(acks.get(aid) or "").strip()
            if ack_reason:
                findings.append(finding(
                    "mentioned_not_bound", pid,
                    f"{pid} 画面描述提到「{hit}」（registry 实体 {aid}）未绑定，已显式签收不入画：{ack_reason}",
                    severity="info", entity=aid,
                ))
            else:
                is_creature = str(aid).startswith(CREATURE_PREFIXES)
                findings.append(finding(
                    "creature_mentioned_not_bound" if is_creature else "mentioned_not_bound", pid,
                    f"{pid} 画面描述提到「{hit}」（registry {'生物/动物' if is_creature else '实体'} {aid}），但该格 characters/references/"
                    f"scene_anchor 都没绑它——出图不会附其定妆参考，"
                    + ("物种/形态全靠模型自由发挥（虎妖易画成普通虎、狐妖易画成狗）。" if is_creature
                       else "形态全靠模型自由发挥。")
                    + f"确认入画则补进该格 references（或 characters）；不入画则改写描述，"
                    f"或在该格写 unbound_mention_ack.{aid} 签收理由。",
                    entity=aid,
                ))
            continue
        hit = next((n for n in name_list if n in story), "")
        if hit:
            findings.append(finding(
                "mentioned_not_bound", pid,
                f"{pid} 台词/旁白提到「{hit}」（registry 实体 {aid}）但未绑定；若仅口头提及可忽略，"
                f"若要入画需补 references。",
                severity="info", entity=aid,
            ))

    schedule = panel.get("entity_schedule")
    if isinstance(schedule, Mapping):
        required = schedule_ids(schedule.get("required_presence"))
        forbidden = schedule_ids(schedule.get("forbidden_presence"))
        conflict = sorted(set(required) & set(forbidden))
        if conflict:
            findings.append(finding(
                "presence_contract_conflict", pid,
                f"{pid} entity_schedule 里 {','.join(conflict)} 同时被列为必在与禁入，契约自相矛盾。",
                entity=",".join(conflict),
            ))
        missing = sorted(set(required) - bound - set(conflict))
        if missing:
            findings.append(finding(
                "required_entity_unbound", pid,
                f"{pid} entity_schedule 要求必在的 {','.join(missing)} 没绑进 characters/references——"
                f"排程与出图输入脱节，补绑定或改排程。",
                entity=",".join(missing),
            ))
        bound_forbidden = sorted(set(forbidden) & bound - set(conflict))
        if bound_forbidden:
            findings.append(finding(
                "forbidden_entity_bound", pid,
                f"{pid} entity_schedule 禁入的 {','.join(bound_forbidden)} 却出现在绑定集里，"
                f"出图会带其参考、大概率入画。",
                entity=",".join(bound_forbidden),
            ))
    return findings


def audit(root: Path, chapter: str) -> Dict[str, Any]:
    chapter = normalize_chapter(chapter)
    script = load_json(root / "脚本" / chapter / "panel_script.json", {}) or {}
    panels = [p for p in (script.get("panels") or []) if isinstance(p, Mapping)]
    names = registry_names(root)

    findings: List[Dict[str, Any]] = []
    scheduled = 0
    derived: Dict[str, List[str]] = {}
    for panel in panels:
        findings.extend(check_panel(panel, names))
        if isinstance(panel.get("entity_schedule"), Mapping):
            scheduled += 1
        else:
            derived[str(panel.get("panel_id") or "?")] = sorted(
                i for i in bound_ids(panel) if not i.startswith(SKIP_PREFIXES)
            )

    summary = {
        "panels": len(panels),
        "registry_entities": len(names),
        "panels_with_schedule": scheduled,
        "must": 0,  # advisory·审不是门
        "warn": sum(1 for f in findings if f["severity"] == "warn"),
        "info": sum(1 for f in findings if f["severity"] == "info"),
    }
    return {
        "kind": KIND,
        "version": VERSION,
        "generated_at": now_iso(),
        "chapter": chapter,
        "summary": summary,
        "findings": findings,
        # 未写显式 entity_schedule 的格：由绑定集派生的"必在"底稿，供升级显式契约时参考。
        "derived_schedule": derived,
    }


def render_md(report: Mapping[str, Any]) -> str:
    s = report.get("summary") or {}
    lines = [
        f"# 漫画实体在场契约机检 · {report.get('chapter')}",
        "",
        f"- 格 {s.get('panels')} · registry 实体 {s.get('registry_entities')}"
        f" · 显式排程格 {s.get('panels_with_schedule')} · warn {s.get('warn')} · info {s.get('info')}",
        "", "## Findings", "",
    ]
    icon = {"warn": "⚠️", "info": "ℹ️"}
    for f in report.get("findings") or []:
        lines.append(f"- {icon.get(f['severity'], '·')} `{f['code']}` {f['message']}")
    if not report.get("findings"):
        lines.append("- ✅ 画面文本提到的已登记实体全部有绑定，无排程冲突。")
    return "\n".join(lines) + "\n"


def write_report(root: Path, report: Mapping[str, Any]) -> None:
    chapter = str(report.get("chapter") or "第1话")
    base = root / "生产数据"
    base.mkdir(parents=True, exist_ok=True)
    (base / f"{KIND}_{chapter}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (base / f"{KIND}_{chapter}.md").write_text(render_md(report), encoding="utf-8")


def adopt_derived_schedule(root: Path, chapter: str) -> int:
    """把派生"必在"清单物化为显式 entity_schedule（仅补没写的格）。

    这是显式的上游编辑：panel_script.json 变更会使下游 receipt 失效并触发重闸，
    这正是想要的效果——从"启发式提醒"升级到"确定性契约"。
    """
    chapter = normalize_chapter(chapter)
    path = root / "脚本" / chapter / "panel_script.json"
    script = load_json(path, {}) or {}
    panels = script.get("panels") or []
    adopted = 0
    for panel in panels:
        if not isinstance(panel, dict) or isinstance(panel.get("entity_schedule"), Mapping):
            continue
        required = sorted(i for i in bound_ids(panel) if not i.startswith(SKIP_PREFIXES))
        if not required:
            continue
        panel["entity_schedule"] = {
            "required_presence": required,
            "offscreen_presence": [],
            "forbidden_presence": [],
            "adopted_from": "derived_schedule",
        }
        adopted += 1
    if adopted:
        path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {chapter} 物化显式 entity_schedule：{adopted} 格（已有显式排程的格不动）")
    if adopted:
        print("[info] panel_script.json 已变更：下游 receipt 将失效，需按流程重闸。")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("chapter")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="人手排查用：有 warn 即 exit 1；正式 gate 从不用它硬拦（advisory·审不是门）")
    ap.add_argument("--adopt-derived", action="store_true",
                    help="把派生必在清单物化为显式 entity_schedule（升级到确定性契约的采用杠杆）")
    ns = ap.parse_args(argv)
    root = Path(ns.root)
    if ns.adopt_derived:
        return adopt_derived_schedule(root, ns.chapter)
    report = audit(root, ns.chapter)
    if ns.write:
        write_report(root, report)
    if ns.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_md(report), end="")
    return 1 if ns.strict and report["summary"]["warn"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
