#!/usr/bin/env python3
"""G2 跨集全局记忆锚（series-level memory-sink anchor）。

2026 SOTA（StoryMem 2512.19539 / EntityMem·EntityBench 2605.15199 / Context Forcing
2602.06028）实证：跨镜身份一致性**随复现间隔急剧衰减**（EntityBench Appendix F.5 "Gap-Decay
Analysis"）；顶尖流水线不止「每镜从定妆库重注入参考」，还把**早期集的关键帧钉成全局记忆锚
（memory-sink）**，在角色长间隔再登场 / 晚集累积漂移时优先重注入，治「逐镜重注入仍随 gap 衰减」。

n2d 已有两层定妆库 + B4 复现距离加权（identity.compute_recurrence）。本模块补缺的「memory-sink」
层：为目标集逐角色判定**是否需要把最早定妆记忆锚重注入**，产可核销计划
`生产数据/memory_anchor_plan_第N集.json`，供 n2d-image/reference_planner 出图前作为高优先锚消费
（文件契约·跨 skill 不互 import，守独立性）。计划一旦声明 reinject，就必须被真实镜头逐角色消费；
缺失、陈旧或仅有聚合计数的证据会由 n2d-review 阻断。

用法：python3 memory_anchor.py <作品根> 第N集 [--json]
纯 stdlib；规划是纯函数，有 pytest 覆盖（test_memory_anchor.py）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d", "_lib"))
for _p in (SCRIPT_DIR, COMMON):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from identity import (  # noqa: E402  同 skill 内复用，独立性允许
    RECURRENCE_GAP_THRESHOLD,
    REFERENCE_FIELDS,
    episode_sort_key,
)

PLAN_KIND = "n2d_memory_anchor_plan"
VERSION = 3

# 距首登场 ≥ LATE_GAP 集即视为「晚集」——即便不是长间隔再登场，累积漂移也该把记忆锚重注入。
LATE_GAP = int(os.environ.get("N2D_MEMORY_LATE_GAP", "5") or "5")
# 单角色记忆锚最多注入几张（front 优先；避免参考预算被记忆锚挤爆逐镜变化锚）。
MAX_MEMORY_REFS = int(os.environ.get("N2D_MEMORY_MAX_REFS", "2") or "2")


def _ep_num(ep: str) -> Optional[int]:
    import re
    m = re.search(r"\d+", str(ep or ""))
    return int(m.group()) if m else None


def _has_prior_generated_pngs(root: Path, target_ep: str) -> bool:
    """Whether visual history exists and therefore requires a usable drift report."""
    target_num = _ep_num(target_ep)
    image_root = root / "出图"
    if target_num is None or not image_root.is_dir():
        return False
    for episode_dir in image_root.iterdir():
        if not episode_dir.is_dir():
            continue
        episode_num = _ep_num(episode_dir.name)
        if episode_num is None or episode_num >= target_num:
            continue
        if any(path.is_file() for path in episode_dir.rglob("*.png")):
            return True
    return False


def char_memory_anchors(registry: Mapping[str, Any]) -> Dict[str, List[str]]:
    """从 identity_registry 提每角色的「记忆锚参考」（front 优先的定妆锚路径，最多 MAX_MEMORY_REFS 张）。

    真实项目使用稳定 ``character_id/form`` 键；缺 id 的旧测试/旧表才回退 asset_key/name。"""
    out: Dict[str, List[str]] = {}
    chars = registry.get("characters") if isinstance(registry, Mapping) else None
    for char in (chars or []):
        if not isinstance(char, Mapping):
            continue
        cid = str(char.get("id") or char.get("character_id") or "").strip()
        name = str(char.get("name", "")).strip()
        for form in char.get("forms", []) or []:
            if not isinstance(form, Mapping):
                continue
            rg = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
            refs: List[str] = []
            for key in REFERENCE_FIELDS:  # front, side, back, ... —— front 居首=正脸主锚
                item = rg.get(key, "")
                if isinstance(item, Mapping):
                    # planned 不是可用记忆锚；结构化参考必须显式 ready/registered。
                    if str(item.get("status") or "").strip() not in {"ready", "registered"}:
                        rel = ""
                    else:
                        rel = str(item.get("path") or "").strip()
                else:
                    rel = str(item or "").strip()
                if rel and rel not in refs:
                    refs.append(rel)
                if len(refs) >= MAX_MEMORY_REFS:
                    break
            if not refs:
                continue
            form_name = str(form.get("form") or form.get("form_name") or "default").strip() or "default"
            key = f"{cid}/{form_name}" if cid else (str(form.get("asset_key", "")).strip() or name)
            if key and key not in out:
                out[key] = refs
        if name and name not in out:
            # 角色无 form 级 reference_group 但有 name → 记空位（让规划仍可标 reinject，参考由人补）
            out.setdefault(name, [])
    return out


def _registry_form_records(registry: Mapping[str, Any]) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    for char in (registry.get("characters") or []) if isinstance(registry, Mapping) else []:
        if not isinstance(char, Mapping):
            continue
        cid = str(char.get("id") or char.get("character_id") or "").strip()
        if not cid:
            continue
        name = str(char.get("name") or "").strip()
        forms = char.get("forms") if isinstance(char.get("forms"), list) and char.get("forms") else [char]
        for form in forms:
            if not isinstance(form, Mapping):
                continue
            form_name = str(form.get("form") or form.get("form_name") or "default").strip() or "default"
            key = f"{cid}/{form_name}"
            aliases = {
                key,
                cid,
                name,
                str(form.get("asset_key") or "").strip(),
                f"{name}/{form_name}" if name else "",
            }
            records[key] = {
                "character_id": cid,
                "form": form_name,
                "aliases": sorted(x for x in aliases if x),
                "form_record": form,
            }
    return records


def storyboard_target_appearance_resolution(
    storyboard: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> tuple[List[str], List[str]]:
    """Resolve stable form keys; ambiguous multi-form schedules fail closed."""
    records = _registry_form_records(registry)
    by_cid: Dict[str, List[str]] = {}
    alias_to_keys: Dict[str, List[str]] = {}
    for key, record in records.items():
        by_cid.setdefault(str(record["character_id"]), []).append(key)
        for alias in record["aliases"]:
            alias_to_keys.setdefault(str(alias), []).append(key)
    found: List[str] = []
    errors: List[str] = []
    clips = storyboard.get("clips") or storyboard.get("storyboard") or []
    if not isinstance(clips, list):
        return found, ["storyboard.clips must be a list"]
    for clip_index, clip in enumerate(clips, 1):
        if not isinstance(clip, Mapping):
            continue
        schedule = clip.get("entity_schedule") if isinstance(clip.get("entity_schedule"), Mapping) else {}
        raw = schedule.get("characters")
        if not isinstance(raw, list):
            raw = clip.get("character_ids") if isinstance(clip.get("character_ids"), list) else clip.get("characters")
        if not isinstance(raw, list):
            raw = []
        offscreen = {
            str(x).strip().split("/", 1)[0]
            for x in (schedule.get("offscreen_presence") or [])
            if str(x).strip()
        }
        forbidden = {
            str(x).strip().split("/", 1)[0]
            for x in (schedule.get("forbidden_presence") or [])
            if str(x).strip()
        }
        clip_blob = json.dumps(clip, ensure_ascii=False)
        for item in raw:
            if isinstance(item, Mapping):
                token = str(item.get("character_id") or item.get("id") or item.get("name") or "").strip()
                explicit_form = str(item.get("form") or item.get("form_name") or "").strip()
                if token and explicit_form:
                    token = f"{token.split('/', 1)[0]}/{explicit_form}"
            else:
                token = str(item or "").strip()
            if not token:
                continue
            base = token.split("/", 1)[0]
            if base in offscreen or base in forbidden:
                continue
            candidates = alias_to_keys.get(token, [])
            if not candidates:
                candidates = by_cid.get(base, [])
            if not candidates:
                continue
            matched = [
                key for key in candidates
                if str(records[key]["form"]) in clip_blob
                or any(alias and alias in clip_blob for alias in records[key]["aliases"] if "/" in alias)
            ]
            matched = list(dict.fromkeys(matched))
            unique_candidates = list(dict.fromkeys(candidates))
            if len(unique_candidates) > 1 and len(matched) != 1:
                clip_id = str(clip.get("clip_id") or clip.get("id") or f"clip#{clip_index}")
                errors.append(
                    f"{clip_id}:{token} has ambiguous forms: {','.join(unique_candidates)}; "
                    "bind character_id/form explicitly in entity_schedule"
                )
                continue
            chosen = matched[0] if len(matched) == 1 else unique_candidates[0]
            if chosen not in found:
                found.append(chosen)
    return found, errors


def storyboard_target_appearances(
    storyboard: Mapping[str, Any],
    registry: Mapping[str, Any],
) -> List[str]:
    """Backward-compatible appearance list; build_plan also consumes errors."""
    return storyboard_target_appearance_resolution(storyboard, registry)[0]


def memory_anchor_rows(
    characters: Mapping[str, Any],
    anchors: Mapping[str, Sequence[str]],
    target_ep: str,
    *,
    gap_threshold: int = RECURRENCE_GAP_THRESHOLD,
    late_gap: int = LATE_GAP,
    target_appearances: Optional[Sequence[str]] = None,
    aliases_by_key: Optional[Mapping[str, Sequence[str]]] = None,
) -> List[Dict[str, Any]]:
    """逐角色判定目标集是否需重注入记忆锚。纯函数·可测。

    characters：drift_report["characters"]（每角色带 episodes / recurrence / total_block）。
    anchors：char → 记忆锚参考路径（char_memory_anchors 提取）。
    触发任一即 reinject：① 目标集是长间隔再登场（gap≥gap_threshold）② 距首登场≥late_gap 集
    ③ 该角色已测出跨集漂移（total_block>0 或 recurrence.high_risk）。"""
    rows: List[Dict[str, Any]] = []
    tnum = _ep_num(target_ep)
    target_keys = list(target_appearances or [])
    if target_appearances is None:
        target_keys = [
            str(char) for char, info in (characters or {}).items()
            if isinstance(info, Mapping) and str(target_ep).strip() in (info.get("episodes") or {})
        ]
    for char in target_keys:
        info = characters.get(char) if isinstance(characters, Mapping) else None
        if not isinstance(info, Mapping):
            for alias in (aliases_by_key or {}).get(char, ()):
                candidate = characters.get(alias) if isinstance(characters, Mapping) else None
                if isinstance(candidate, Mapping):
                    info = candidate
                    break
        if not isinstance(info, Mapping):
            continue
        eps = sorted(
            (str(e).strip() for e in (info.get("episodes") or {}).keys() if str(e).strip()),
            key=episode_sort_key,
        )
        if not eps:
            continue
        first_ep = eps[0]
        rec = info.get("recurrence") if isinstance(info.get("recurrence"), Mapping) else {}
        reentries = rec.get("long_gap_reentries") if isinstance(rec.get("long_gap_reentries"), list) else []

        reasons: List[str] = []
        gap_hit = next((r for r in reentries
                        if isinstance(r, Mapping) and str(r.get("at", "")).strip() == str(target_ep).strip()
                        and int(r.get("gap", 0) or 0) >= gap_threshold), None)
        if gap_hit is None and tnum is not None:
            previous = [e for e in eps if _ep_num(e) is not None and int(_ep_num(e) or 0) < tnum]
            if previous:
                prev = previous[-1]
                gap = tnum - int(_ep_num(prev) or tnum) - 1
                if gap >= gap_threshold:
                    gap_hit = {"at": target_ep, "prev": prev, "gap": gap}
        if gap_hit:
            reasons.append(f"长间隔再登场(gap={gap_hit.get('gap')}·上次第{_ep_num(str(gap_hit.get('prev','')))}集)"
                           "·EntityBench 缺口衰减")
        fnum, target_num = _ep_num(first_ep), tnum
        if first_ep != target_ep and fnum is not None and target_num is not None and (target_num - fnum) >= late_gap:
            reasons.append(f"距首登场{target_num - fnum}集(≥{late_gap})·晚集累积漂移防护")
        if int(info.get("total_block", 0) or 0) > 0 or bool(rec.get("high_risk")):
            reasons.append("已测出跨集漂移·重锚记忆锚")

        if not reasons:
            continue
        rows.append({
            "char": char,
            "reinject": True,
            "reason": "；".join(reasons),
            "memory_sink_episode": first_ep,
            "memory_anchor_refs": list(anchors.get(char) or []),
            "recurrence": {"max_gap": rec.get("max_gap", 0), "high_risk": bool(rec.get("high_risk"))},
        })
    rows.sort(key=lambda r: str(r.get("char", "")))
    return rows


def build_plan(root: str, ep: str) -> Dict[str, Any]:
    rootp = Path(root)
    drift_path = rootp / "生产数据" / "identity_drift_report.json"
    canonical_registry_path = rootp / "出图" / "共享" / "identity_registry.json"
    drift = _load(drift_path)
    registry_path = canonical_registry_path
    registry = _load(registry_path)
    storyboard_path = rootp / "脚本" / ep / "storyboard.json"
    storyboard = _load(storyboard_path)
    notes: List[str] = []
    drift_usable = isinstance(drift, Mapping) and drift.get("available") is True
    prior_visual_history = _has_prior_generated_pngs(rootp, ep)
    if not drift_usable and prior_visual_history:
        notes.append(
            "已有早期集 PNG，但 identity_drift_report 不可用；先跑 identity.py --write，"
            "否则不能判断长间隔复现漂移。"
        )
        return {"kind": PLAN_KIND, "version": VERSION, "status": "warn", "episode": ep, "available": False,
                "source_fingerprint": {
                    "identity_drift_report_sha256": _sha256(drift_path),
                    "identity_registry_sha256": _sha256(registry_path),
                    "storyboard_sha256": _sha256(storyboard_path),
                }, "rows": [], "notes": notes}
    if not drift_usable:
        # First visual generation has no historical pixels to measure.  An
        # unavailable --skip-face skeleton is therefore a valid empty history,
        # not a reason to deadlock image preflight.  The source hash still binds
        # the plan to that exact skeleton and storyboard.
        notes.append("尚无早期集 PNG；本集按空历史建立基线，不要求不存在的跨集漂移量测。")
        drift = {"available": True, "characters": {}}
    anchors = char_memory_anchors(registry) if isinstance(registry, Mapping) else {}
    if not anchors:
        notes.append("缺 identity_registry 或无 reference_group 定妆锚——仍按出场/复现标 reinject，记忆锚参考路径留空待人补。")
    target_appearances, appearance_errors = storyboard_target_appearance_resolution(
        storyboard if isinstance(storyboard, Mapping) else {},
        registry if isinstance(registry, Mapping) else {},
    )
    if appearance_errors:
        notes.append("storyboard 多形态角色未精确绑定 character_id/form；不能猜第一种形态。")
        return {
            "kind": PLAN_KIND,
            "version": VERSION,
            "status": "warn",
            "episode": ep,
            "available": False,
            "source_fingerprint": {
                "identity_drift_report_sha256": _sha256(drift_path),
                "identity_registry_sha256": _sha256(registry_path),
                "storyboard_sha256": _sha256(storyboard_path),
            },
            "target_appearances": target_appearances,
            "errors": appearance_errors,
            "rows": [],
            "notes": notes,
        }
    records = _registry_form_records(registry if isinstance(registry, Mapping) else {})
    alias_owners: Dict[str, List[str]] = {}
    for key, record in records.items():
        for alias in record["aliases"]:
            alias_owners.setdefault(str(alias), []).append(key)
    aliases_by_key = {
        key: [
            alias for alias in record["aliases"]
            if alias == key or len(set(alias_owners.get(str(alias), []))) == 1
        ]
        for key, record in records.items()
    }
    drift_characters = drift.get("characters", {}) if isinstance(drift, Mapping) else {}
    ambiguous_history = []
    for key in target_appearances:
        for alias in records.get(key, {}).get("aliases", []):
            owners = set(alias_owners.get(str(alias), []))
            if len(owners) > 1 and isinstance(drift_characters, Mapping) and alias in drift_characters:
                ambiguous_history.append(f"{alias} -> {','.join(sorted(owners))}")
    if ambiguous_history:
        notes.append("历史 drift 仍用可映射到多个形态的旧角色名；不能把同一历史漂移静默复用给任一形态。")
        return {
            "kind": PLAN_KIND,
            "version": VERSION,
            "status": "warn",
            "episode": ep,
            "available": False,
            "source_fingerprint": {
                "identity_drift_report_sha256": _sha256(drift_path),
                "identity_registry_sha256": _sha256(registry_path),
                "storyboard_sha256": _sha256(storyboard_path),
            },
            "target_appearances": target_appearances,
            "errors": [f"ambiguous_legacy_drift_key:{item}" for item in sorted(set(ambiguous_history))],
            "rows": [],
            "notes": notes,
        }
    rows = memory_anchor_rows(
        drift_characters,
        anchors,
        ep,
        target_appearances=target_appearances,
        aliases_by_key=aliases_by_key,
    )
    if not rows:
        notes.append("本集无需重注入记忆锚（无长间隔再登场 / 晚集 / 已测漂移角色）。")
    return {"kind": PLAN_KIND, "version": VERSION, "status": "ready", "episode": ep, "available": True,
            "source_fingerprint": {
                "identity_drift_report_sha256": _sha256(drift_path),
                "identity_registry_sha256": _sha256(registry_path),
                "storyboard_sha256": _sha256(storyboard_path),
            }, "target_appearances": target_appearances, "rows": rows, "notes": notes}


def _load(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sha256(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def write_plan(root: str, ep: str, plan: Mapping[str, Any]) -> str:
    out_dir = os.path.join(root, "生产数据")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"memory_anchor_plan_{ep}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2, sort_keys=True)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    ns = ap.parse_args(argv)
    plan = build_plan(ns.root.rstrip("/"), ns.episode)
    # Always replace an older plan, including with an explicit unavailable
    # plan.  Leaving a stale ready file behind would let downstream consumers
    # inspect yesterday's evidence after today's drift check failed.
    if not ns.no_write:
        plan["path"] = write_plan(ns.root.rstrip("/"), ns.episode, plan)
    if ns.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"记忆锚规划 {ns.episode}：available={plan.get('available')}，{len(plan.get('rows', []))} 角色需重注入")
        for r in plan.get("rows", []):
            print(f"  · {r['char']}（记忆锚来自{r['memory_sink_episode']}）：{r['reason']}")
        for n in plan.get("notes", []):
            print(f"  - {n}")
    return 0  # report-only，永不非零退出


if __name__ == "__main__":
    raise SystemExit(main())
