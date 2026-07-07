#!/usr/bin/env python3
"""Build and gate the n2d script quality handoff contract.

This is the machine-readable version of "好看": n2d-script must state what the
episode is selling, how the first seconds hook, what each clip does
dramatically, and which promises/questions downstream image/video prompts must
preserve.  The checks here are structural, not taste scoring.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

KIND = "n2d_script_quality_contract"
VERSION = 1
REQUIRED_CONSUMPTION_FIELDS = [
    "core_attraction",
    "first_3s_visual_hook",
    "retention_promise_ledger",
    "pacing_allocation",
    "clip_dramatic_function",
    "audience_question_ledger",
    "performance_cues",
]

CORE_ATTRACTION_KEYS = (
    "core_attraction",
    "core_watch_value",
    "episode_hook_contract",
    "audience_hook_contract",
    "central_viewing_contract",
    "核心看点",
    "本集核心看点",
    "本集看点",
)
FIRST_HOOK_KEYS = ("first_3s_visual_hook", "first_3s_hook", "cold_open_contract", "首屏视觉钩")
RETENTION_LEDGER_KEYS = ("retention_promise_ledger", "retention_ledger", "promise_payoff_ledger", "留存承诺账本")
DRAMATIC_KEYS = ("dramatic_function", "story_function", "story_role", "narrative_function", "戏剧功能")
AUDIENCE_EFFECT_KEYS = ("audience_effect", "viewer_effect", "emotion_target", "why_this_clip_matters", "观众效果")
SPECTACLE_FUNCTION_KEYS = ("spectacle_story_function", "action_story_function", "visual_payoff", "奇观叙事功能")

KEY_CLIP_RE = re.compile(
    r"(钩|爽|打脸|反转|高潮|真相|危机|爆点|觉醒|救场|cliff|hook|payoff|reveal|twist|signature|highlight)",
    re.I,
)
SPECTACLE_RE = re.compile(
    r"(打斗|追逐|法术|武技|飞行|腾云|御剑|御兽|坐骑|马车|载具|车流|尾随|潜入|大场景|大场面|爆发|combat|chase|flight|vehicle|spectacle)",
    re.I,
)
PACING_ALLOCATION_KEYS = ("pacing_allocation", "runtime_allocation", "screen_time_allocation", "时长分配", "节奏分配")
PACING_ROLE_KEYS = ("pacing_role", "runtime_role", "screen_time_role", "duration_role", "时长角色", "节奏角色")
RUNTIME_PRIORITY_KEYS = ("runtime_priority", "screen_time_priority", "pacing_priority", "duration_priority", "时长优先级")
COMPRESSION_PLAN_KEYS = (
    "compression_plan",
    "compact_plan",
    "compressed_delivery",
    "runtime_note",
    "duration_rationale",
    "overlength_justification",
    "pacing_exception",
    "压缩策略",
    "一笔带过策略",
    "越长理由",
)
PRIMARY_RUNTIME_RE = re.compile(
    r"(primary|highlight|hero|key|climax|payoff|twist|reveal|combat|fight|spectacle|main|"
    r"主时长|主看点|高光|核心|高潮|爽点|反转|揭示|兑现|打斗|奇观|主镜)",
    re.I,
)
COMPRESSED_RUNTIME_RE = re.compile(
    r"(compressed|summary|bridge|transition|exposition|context|reaction|atmosphere|low|minor|"
    r"一笔带过|旁白带过|压缩|桥接|过渡|解释|交代|反应|气氛|氛围|低优先|次要|弱信息)",
    re.I,
)
LONG_CLIP_REQUIRES_ROLE_SEC = 6.0
LONG_CLIP_SEC = 8.0
COMPRESSED_MAX_SEC = 4.0
SPECTACLE_SHORT_SEC = 3.0


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def ep_label(value: str) -> str:
    text = str(value or "").strip()
    if text.startswith("第") and text.endswith("集"):
        return text
    m = re.search(r"\d+", text)
    return f"第{m.group(0)}集" if m else text


def load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def stable_content_hash(contract: Mapping[str, Any]) -> str:
    payload = {
        "source_sha256": contract.get("source_sha256") or {},
        "signable_fields": contract.get("signable_fields") or {},
        "findings": contract.get("findings") or [],
        "required_consumption_fields": contract.get("required_consumption_fields") or [],
    }
    return digest(payload)


def flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return " ".join(str(k) + " " + flatten(v) for k, v in value.items())
    if isinstance(value, list):
        return " ".join(flatten(v) for v in value)
    return str(value or "")


def filled(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(filled(v) for v in value.values())
    if isinstance(value, list):
        return any(filled(v) for v in value)
    return value not in (None, "")


def pick(mapping: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, Any]:
    for key in keys:
        if key in mapping and filled(mapping.get(key)):
            return key, mapping.get(key)
    return "", None


def finding(severity: str, code: str, message: str, *, path: str = "", clip: str = "") -> Dict[str, Any]:
    row = {"severity": severity, "code": code, "message": message}
    if path:
        row["path"] = path
    if clip:
        row["clip"] = clip
    return row


def triage_paths(root: Path, ep: str) -> List[Path]:
    return [root / "脚本" / ep / "adaptation_triage.json", root / "脚本" / "adaptation_triage.json"]


def load_adaptation_triage(root: Path, ep: str) -> Tuple[Optional[Mapping[str, Any]], str]:
    for path in triage_paths(root, ep):
        data = load_json(path)
        if isinstance(data, Mapping):
            return data, str(path)
    return None, ""


def load_or_build_story_quality_pack(root: Path, ep: str, write: bool) -> Tuple[Optional[Mapping[str, Any]], str]:
    path = root / "生产数据" / f"story_quality_pack_{ep}.json"
    data = load_json(path)
    if isinstance(data, Mapping):
        return data, str(path)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import story_quality_pack  # type: ignore

        pack = story_quality_pack.build_pack(root, ep)
        if write:
            story_quality_pack.write_outputs(root, ep, pack)
        return pack, str(path)
    except Exception:
        return None, ""


def clip_id(clip: Mapping[str, Any], idx: int) -> str:
    return str(clip.get("id") or clip.get("clip_id") or clip.get("label") or f"Clip_{idx:02d}")


def key_clip(clip: Mapping[str, Any], idx: int, total: int) -> bool:
    if idx in (1, total):
        return True
    blob = " ".join(str(clip.get(k) or "") for k in ("label", "rhythm", "template", "shot_type", "description"))
    return bool(KEY_CLIP_RE.search(blob))


def spectacle_clip(clip: Mapping[str, Any]) -> bool:
    blob = " ".join(str(clip.get(k) or "") for k in ("label", "rhythm", "template", "shot_type", "description"))
    tc = clip.get("template_contract")
    if isinstance(tc, Mapping) and filled(tc):
        blob += " " + flatten(tc)
    return bool(SPECTACLE_RE.search(blob))


def clip_duration(clip: Mapping[str, Any]) -> Optional[float]:
    for key in ("duration", "duration_sec", "时长", "seconds"):
        value = clip.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            m = re.search(r"\d+(?:\.\d+)?", value)
            if m:
                return float(m.group(0))
    return None


def pick_any(mapping: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, Any]:
    for key in keys:
        if key in mapping and filled(mapping.get(key)):
            return key, mapping.get(key)
    return "", None


def has_any(mapping: Mapping[str, Any], keys: Sequence[str]) -> bool:
    return any(key in mapping and filled(mapping.get(key)) for key in keys)


def runtime_text(*values: Any) -> str:
    return " ".join(flatten(value) for value in values if filled(value))


def validate_pacing(story: Mapping[str, Any], path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    clips = [c for c in story.get("clips") or [] if isinstance(c, Mapping)]
    findings: List[Dict[str, Any]] = []
    rows: List[Dict[str, Any]] = []
    allocation_key, declared_allocation = pick_any(story, PACING_ALLOCATION_KEYS)
    if not allocation_key:
        findings.append(finding(
            "block",
            "pacing_allocation_missing",
            "storyboard 缺 pacing_allocation；必须声明哪些 Clip 吃主时长、哪些桥接/解释一笔带过，不能让下游平均分配时长。",
            path=path,
        ))

    total_duration = 0.0
    primary_duration = 0.0
    compressed_duration = 0.0
    unknown_duration = 0.0
    primary_clip_ids: List[str] = []
    compressed_clip_ids: List[str] = []

    total = len(clips)
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        duration = clip_duration(clip)
        if duration is not None:
            total_duration += duration
        role_key, role = pick_any(clip, PACING_ROLE_KEYS)
        priority_key, priority = pick_any(clip, RUNTIME_PRIORITY_KEYS)
        has_role = bool(role_key or priority_key)
        has_compression = has_any(clip, COMPRESSION_PLAN_KEYS)
        text = runtime_text(
            role,
            priority,
            clip.get("duration_policy"),
            clip.get("rhythm"),
            clip.get("label"),
            clip.get("dramatic_function"),
            clip.get("template"),
        )
        explicit_primary = bool(PRIMARY_RUNTIME_RE.search(text))
        compressed_signal = bool(COMPRESSED_RUNTIME_RE.search(text))
        compressed = compressed_signal and not explicit_primary
        is_spectacle = spectacle_clip(clip)
        is_key = key_clip(clip, idx, total)

        if duration is None:
            findings.append(finding("warn", "clip_duration_missing_for_pacing", "Clip 缺 duration，无法校验时长分配。", path=path, clip=cid))
        elif not has_role and duration >= LONG_CLIP_REQUIRES_ROLE_SEC:
            findings.append(finding(
                "block",
                "long_clip_missing_pacing_role",
                f"Clip 时长 {duration:g}s 但缺 pacing_role/runtime_priority；长镜必须说明是主看点、高光、承接还是一笔带过。",
                path=path,
                clip=cid,
            ))
        elif not has_role:
            findings.append(finding("warn", "clip_pacing_role_missing", "Clip 建议补 pacing_role/runtime_priority，避免平均分配时长。", path=path, clip=cid))

        if duration is not None and compressed and duration > COMPRESSED_MAX_SEC:
            findings.append(finding(
                "block",
                "compressed_clip_too_long_without_plan",
                f"Clip 被标为桥接/解释/反应/一笔带过，却有 {duration:g}s；非关键 Clip 必须压到 {COMPRESSED_MAX_SEC:g}s 内。若它确实承载主干/反转/打斗/兑现，请重定级为 primary/highlight 并写越长理由；不能用 compression_plan 保留低优先级长镜。",
                path=path,
                clip=cid,
            ))
        if duration is not None and duration >= LONG_CLIP_SEC and not explicit_primary:
            findings.append(finding(
                "block",
                "long_clip_without_primary_runtime",
                f"Clip 时长 {duration:g}s 但未声明主时长/高光/核心看点；越长理由不能替代 primary/highlight 重定级，长时长应优先给打斗、反转、兑现、强情绪峰等主要 Clip。",
                path=path,
                clip=cid,
            ))
        if is_spectacle and not explicit_primary and not has_compression:
            findings.append(finding(
                "warn",
                "spectacle_runtime_priority_missing",
                "打斗/追逐/法术/大场面等奇观 Clip 建议标 runtime_priority=primary/highlight；若只是过门一击，写 compression_plan 说明。",
                path=path,
                clip=cid,
            ))
        if is_spectacle and duration is not None and duration < SPECTACLE_SHORT_SEC and not has_compression:
            findings.append(finding(
                "warn",
                "spectacle_clip_too_short_without_beat",
                f"奇观 Clip 仅 {duration:g}s；若是打斗/爆发主看点，建议给足起手-命中-反应节拍；若只是一笔带过，补 compression_plan。",
                path=path,
                clip=cid,
            ))

        if duration is not None:
            if explicit_primary or (is_key and not compressed):
                primary_duration += duration
                primary_clip_ids.append(cid)
            elif compressed:
                compressed_duration += duration
                compressed_clip_ids.append(cid)
            else:
                unknown_duration += duration

        rows.append({
            "clip_id": cid,
            "duration": duration,
            "pacing_role": role,
            "runtime_priority": priority,
            "primary_runtime": explicit_primary,
            "compressed_runtime": compressed,
            "compression_plan": any(has_any(clip, (key,)) for key in COMPRESSION_PLAN_KEYS),
        })

    allocation = {
        "declared": declared_allocation if filled(declared_allocation) else {},
        "source": f"storyboard.{allocation_key}" if allocation_key else "auto_summary_needs_author_review",
        "runtime_summary": {
            "total_duration": round(total_duration, 3),
            "primary_duration": round(primary_duration, 3),
            "compressed_duration": round(compressed_duration, 3),
            "unclassified_duration": round(unknown_duration, 3),
            "primary_runtime_share": round(primary_duration / total_duration, 3) if total_duration else None,
            "compressed_runtime_share": round(compressed_duration / total_duration, 3) if total_duration else None,
            "primary_clip_ids": primary_clip_ids,
            "compressed_clip_ids": compressed_clip_ids,
        },
        "rule": "主时长优先给核心看点/爽点/打斗/反转/兑现；桥接、解释、气氛、普通反应镜必须短，不能用压缩说明保留低优先级长镜；长镜必须重定级为 primary/highlight。",
    }
    return {"pacing_allocation": allocation, "clip_pacing_roles": rows}, findings


def validate_core_fields(story: Mapping[str, Any], path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    fields: Dict[str, Any] = {}
    findings: List[Dict[str, Any]] = []

    core_key, core = pick(story, CORE_ATTRACTION_KEYS)
    if not core_key:
        findings.append(finding("block", "core_attraction_missing", "storyboard 缺本集核心看点/core_attraction；无法签收这一集到底卖什么。", path=path))
    else:
        fields["core_attraction"] = core
        core_text = flatten(core)
        if isinstance(core, Mapping):
            has_type = any(filled(core.get(k)) for k in ("category", "type", "appeal_type", "看点类型"))
            has_payoff = any(filled(core.get(k)) for k in ("why_watch", "audience_payoff", "viewer_question", "观看理由", "爽点兑现"))
            if not has_type or not has_payoff:
                findings.append(finding("warn", "core_attraction_not_signable", "核心看点建议包含 category/type + why_watch/audience_payoff，便于下游按字段消费。", path=path))
        elif len(core_text) < 12:
            findings.append(finding("warn", "core_attraction_too_short", "核心看点过短，像标签而不是可签收字段。", path=path))

    hook_key, hook = pick(story, FIRST_HOOK_KEYS)
    if not hook_key:
        findings.append(finding("block", "first_3s_visual_hook_missing", "storyboard 缺 first_3s_visual_hook；漫剧/微短剧首屏视觉钩无法交接给出图。", path=path))
    else:
        fields["first_3s_visual_hook"] = hook
        if isinstance(hook, Mapping):
            has_visual = any(filled(hook.get(k)) for k in ("visual_hook", "hook", "image", "画面", "视觉钩"))
            has_promise = any(filled(hook.get(k)) for k in ("content_promise", "promise", "viewer_question", "内容承诺", "观众问题"))
            has_silent = any(k in hook for k in ("muted_readable", "silent_readable", "静音可读"))
            if not has_visual:
                findings.append(finding("block", "first_3s_visual_missing", "first_3s_visual_hook 缺可画出来的 visual_hook/画面字段。", path=path))
            if not has_promise:
                findings.append(finding("block", "first_3s_promise_missing", "first_3s_visual_hook 缺内容承诺/观众问题字段。", path=path))
            if not has_silent:
                findings.append(finding("warn", "first_3s_silent_readable_missing", "first_3s_visual_hook 建议写 muted_readable/silent_readable，保证无声滑屏也能读懂。", path=path))

    ledger_key, ledger = pick(story, RETENTION_LEDGER_KEYS)
    if not ledger_key:
        findings.append(finding("block", "retention_promise_ledger_missing", "storyboard 缺 retention_promise_ledger；无法证明钩子、承诺和兑现链条。", path=path))
    elif not isinstance(ledger, list) or not ledger:
        findings.append(finding("block", "retention_promise_ledger_empty", "retention_promise_ledger 为空；至少要有一个承诺/悬念/兑现账。", path=path))
    else:
        fields["retention_promise_ledger"] = ledger
        for idx, row in enumerate(ledger, 1):
            if not isinstance(row, Mapping):
                findings.append(finding("warn", "retention_ledger_row_not_object", f"retention_promise_ledger 第 {idx} 项不是对象，难以签收。", path=path))
                continue
            has_promise = any(filled(row.get(k)) for k in ("promise", "hook", "question", "承诺", "悬念"))
            has_handling = any(filled(row.get(k)) for k in ("payoff", "payoff_due", "status", "handling", "兑现", "处理"))
            if not has_promise or not has_handling:
                findings.append(finding("warn", "retention_ledger_row_weak", f"retention_promise_ledger 第 {idx} 项缺 promise/question 或 payoff/status。", path=path))

    return fields, findings


def validate_adaptation(root: Path, ep: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, str]]:
    triage, path = load_adaptation_triage(root, ep)
    findings: List[Dict[str, Any]] = []
    fields: Dict[str, Any] = {}
    sources: Dict[str, str] = {}
    if not isinstance(triage, Mapping):
        findings.append(finding("block", "adaptation_triage_missing", "缺 adaptation_triage.json；小说取舍没有有账改编，不能把上游改写交给下游。"))
        return fields, findings, sources
    sources["adaptation_triage"] = path
    items = triage.get("items")
    if not isinstance(items, list) or not items:
        findings.append(finding("block", "adaptation_triage_empty", "adaptation_triage.json 缺 items[] 或为空。", path=path))
    else:
        fields["adaptation_triage"] = {
            "path": os.path.relpath(path, root),
            "items": len(items),
            "decisions": sorted({str(i.get("decision") or "") for i in items if isinstance(i, Mapping) and i.get("decision")}),
        }
    return fields, findings, sources


def validate_clips(story: Mapping[str, Any], path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    clips = [c for c in story.get("clips") or [] if isinstance(c, Mapping)]
    rows: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    if not clips:
        findings.append(finding("block", "storyboard_clips_missing", "storyboard.json 缺 clips[]；无法形成分镜交接合同。", path=path))
        return rows, findings

    total = len(clips)
    for idx, clip in enumerate(clips, 1):
        cid = clip_id(clip, idx)
        dkey, dramatic = pick(clip, DRAMATIC_KEYS)
        ekey, effect = pick(clip, AUDIENCE_EFFECT_KEYS)
        skey, spectacle_function = pick(clip, SPECTACLE_FUNCTION_KEYS)
        tc = clip.get("template_contract")
        if not filled(spectacle_function) and isinstance(tc, Mapping):
            _, spectacle_function = pick(tc, ("story_function", "narrative_function", "spectacle_story_function", "visual_payoff"))

        if not dkey:
            findings.append(finding("block", "clip_dramatic_function_missing", "Clip 缺 dramatic_function/story_function；下游只能画描述，不能拍戏剧功能。", path=path, clip=cid))
        is_key = key_clip(clip, idx, total)
        is_spectacle = spectacle_clip(clip)
        if is_key and not ekey:
            findings.append(finding("block", "key_clip_audience_effect_missing", "关键/首尾 Clip 缺 audience_effect；无法签收观众在这一镜该得到什么。", path=path, clip=cid))
        elif not ekey:
            findings.append(finding("warn", "clip_audience_effect_missing", "普通 Clip 建议补 audience_effect，便于 image/video prompt 消费。", path=path, clip=cid))
        if is_spectacle and not filled(spectacle_function):
            findings.append(finding("block", "spectacle_story_function_missing", "高动态/奇观 Clip 缺 spectacle_story_function；奇观必须服务剧情，不能只写酷炫动作。", path=path, clip=cid))

        rows.append({
            "clip_id": cid,
            "dramatic_function": dramatic,
            "audience_effect": effect,
            "spectacle_story_function": spectacle_function,
            "key_clip": is_key,
            "spectacle_clip": is_spectacle,
        })
    return rows, findings


def validate_story_quality(root: Path, ep: str, write: bool) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, str]]:
    pack, path = load_or_build_story_quality_pack(root, ep, write)
    findings: List[Dict[str, Any]] = []
    fields: Dict[str, Any] = {}
    sources: Dict[str, str] = {}
    if not isinstance(pack, Mapping):
        findings.append(finding("warn", "story_quality_pack_missing", "缺 story_quality_pack；建议先跑 story_quality_pack.py --write 生成观众问题账本和表演 cues。"))
        return fields, findings, sources
    sources["story_quality_pack"] = path
    qledger = pack.get("audience_question_ledger") if isinstance(pack.get("audience_question_ledger"), Mapping) else {}
    questions = qledger.get("questions") if isinstance(qledger, Mapping) else []
    fields["audience_question_ledger"] = qledger
    fields["performance_cues"] = pack.get("performance_prompt_cues") or []
    for row in qledger.get("findings") or []:
        if isinstance(row, Mapping) and row.get("code") == "open_questions_without_hook":
            findings.append(finding("block", "open_questions_without_hook", "本集留下观众问题，但缺集尾钩或兑现进展；先补下一集可接的断点。", path=path))
    for q in questions or []:
        if isinstance(q, Mapping) and q.get("status") == "open" and not filled(q.get("expected_next_handling")):
            findings.append(finding("block", "open_question_no_next_handling", "开放观众问题缺 expected_next_handling；无法交接给下一集/下游。", path=path))
    return fields, findings, sources


def build_contract(root: Path, ep: str, write_aux: bool = False) -> Dict[str, Any]:
    ep = ep_label(ep)
    storyboard_path = root / "脚本" / ep / "storyboard.json"
    story = load_json(storyboard_path)
    findings: List[Dict[str, Any]] = []
    signable_fields: Dict[str, Any] = {}
    sources: Dict[str, str] = {}

    if not isinstance(story, Mapping):
        findings.append(finding("block", "storyboard_missing", "缺 storyboard.json；无法构建剧本质量交接合同。", path=str(storyboard_path)))
        story = {}
    else:
        sources["storyboard"] = str(storyboard_path)
        fields, rows = validate_core_fields(story, str(storyboard_path))
        signable_fields.update(fields)
        findings.extend(rows)
        clip_rows, rows = validate_clips(story, str(storyboard_path))
        findings.extend(rows)
        pacing_fields, rows = validate_pacing(story, str(storyboard_path))
        pacing_rows_by_id = {
            str(row.get("clip_id")): row
            for row in pacing_fields.get("clip_pacing_roles") or []
            if isinstance(row, Mapping)
        }
        merged_clip_rows: List[Dict[str, Any]] = []
        for row in clip_rows:
            merged = dict(row)
            pacing_row = pacing_rows_by_id.get(str(row.get("clip_id")))
            if isinstance(pacing_row, Mapping):
                merged.update({
                    "duration": pacing_row.get("duration"),
                    "pacing_role": pacing_row.get("pacing_role"),
                    "runtime_priority": pacing_row.get("runtime_priority"),
                    "primary_runtime": pacing_row.get("primary_runtime"),
                    "compressed_runtime": pacing_row.get("compressed_runtime"),
                    "compression_plan": pacing_row.get("compression_plan"),
                })
            merged_clip_rows.append(merged)
        signable_fields["clip_dramatic_functions"] = merged_clip_rows
        signable_fields.update(pacing_fields)
        findings.extend(rows)

    fields, rows, src = validate_adaptation(root, ep)
    signable_fields.update(fields)
    sources.update(src)
    findings.extend(rows)

    fields, rows, src = validate_story_quality(root, ep, write_aux)
    signable_fields.update(fields)
    sources.update(src)
    findings.extend(rows)

    blocks = sum(1 for f in findings if f.get("severity") == "block")
    warnings = sum(1 for f in findings if f.get("severity") == "warn")
    source_sha256 = {
        name: sha256_file(Path(path))
        for name, path in sources.items()
        if path
    }
    contract = {
        "kind": KIND,
        "version": VERSION,
        "episode": ep,
        "generated_at": now_iso(),
        "status": "pass" if blocks == 0 else "block",
        "required_consumption_fields": REQUIRED_CONSUMPTION_FIELDS,
        "source_paths": {k: os.path.relpath(v, root) if os.path.isabs(v) else v for k, v in sources.items()},
        "source_sha256": source_sha256,
        "signable_fields": signable_fields,
        "findings": findings,
        "summary": {
            "status": "pass" if blocks == 0 else "block",
            "blocks": blocks,
            "warnings": warnings,
            "clips": len(signable_fields.get("clip_dramatic_functions") or []),
            "primary_runtime_share": ((signable_fields.get("pacing_allocation") or {}).get("runtime_summary") or {}).get("primary_runtime_share"),
            "compressed_runtime_share": ((signable_fields.get("pacing_allocation") or {}).get("runtime_summary") or {}).get("compressed_runtime_share"),
            "open_questions": sum(
                1
                for q in ((signable_fields.get("audience_question_ledger") or {}).get("questions") or [])
                if isinstance(q, Mapping) and q.get("status") == "open"
            ),
        },
        "notes": [
            "n2d-script 是编剧室 + 导演预演 + 制片交接合同；本文件把'好看'拆成下游必须消费的签收字段。",
            "image/video prompt 阶段必须写 script_contract_applied_第N集.json，证明这些字段已进入 prompt。",
        ],
    }
    contract["content_hash"] = stable_content_hash(contract)
    # Backward-compatible alias. New gates compare content_hash; file SHA is audit-only.
    contract["contract_hash"] = contract["content_hash"]
    return contract


def render_md(contract: Mapping[str, Any]) -> str:
    s = contract.get("summary") or {}
    fields = contract.get("signable_fields") or {}
    lines = [
        "# 剧本质量交接合同",
        "",
        f"- episode: {contract.get('episode')}",
        f"- status: {s.get('status')}",
        f"- blocks: {s.get('blocks')}",
        f"- warnings: {s.get('warnings')}",
        f"- clips: {s.get('clips')}",
        "",
        "## 可签收字段",
        "",
        f"- core_attraction: {flatten(fields.get('core_attraction'))[:180] or '-'}",
        f"- first_3s_visual_hook: {flatten(fields.get('first_3s_visual_hook'))[:180] or '-'}",
        f"- retention_promise_ledger: {len(fields.get('retention_promise_ledger') or [])}",
        f"- pacing_allocation: {flatten(fields.get('pacing_allocation'))[:180] or '-'}",
        f"- audience_question_ledger: {len((fields.get('audience_question_ledger') or {}).get('questions') or [])}",
        f"- performance_cues: {len(fields.get('performance_cues') or [])}",
        "",
        "## Clip 戏剧功能与时长角色",
        "",
        "| Clip | Duration | Pacing Role | Priority | Dramatic Function | Audience Effect | Spectacle Function |",
        "|---|---:|---|---|---|---|---|",
    ]
    for row in fields.get("clip_dramatic_functions") or []:
        if not isinstance(row, Mapping):
            continue
        lines.append(
            f"| {row.get('clip_id')} | {row.get('duration') if row.get('duration') is not None else '-'} | "
            f"{flatten(row.get('pacing_role'))[:40] or '-'} | {flatten(row.get('runtime_priority'))[:40] or '-'} | "
            f"{flatten(row.get('dramatic_function'))[:80] or '-'} | "
            f"{flatten(row.get('audience_effect'))[:80] or '-'} | {flatten(row.get('spectacle_story_function'))[:80] or '-'} |"
        )
    lines += ["", "## Findings", "", "| Severity | Code | Clip | Message |", "|---|---|---|---|"]
    for row in contract.get("findings") or []:
        if not isinstance(row, Mapping):
            continue
        lines.append(f"| {row.get('severity')} | {row.get('code')} | {row.get('clip', '-')} | {row.get('message')} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(root: Path, ep: str, contract: Mapping[str, Any]) -> Tuple[Path, Path]:
    out = root / "生产数据"
    jp = out / f"script_quality_contract_{ep}.json"
    mp = out / f"script_quality_contract_{ep}.md"
    write_atomic(jp, json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_atomic(mp, render_md(contract))
    return jp, mp


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build/gate n2d script quality handoff contract")
    ap.add_argument("root")
    ap.add_argument("episode")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()
    ep = ep_label(ns.episode)
    contract = build_contract(root, ep, write_aux=ns.write)
    if ns.write:
        jp, mp = write_outputs(root, ep, contract)
        contract["outputs"] = {"json": str(jp), "md": str(mp)}
    if ns.json:
        print(json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_md(contract))
    if ns.strict and (contract.get("summary") or {}).get("blocks", 0):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
