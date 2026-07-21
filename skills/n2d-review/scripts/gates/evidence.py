#!/usr/bin/env python3
"""gates/evidence.py — 生成证据/配方/种子事件·制作模式契约同步·进度签收族

按证据族从 gate.py 拆出的 check_ 闸（增量3）。从 gate_core 取共享基座，避免与 gate.py 循环导入；
gate.py `from gates.evidence import *` 回灌，run()/按名自省助手照常解析；成员经校验 call-graph-closed。
"""
from gate_core import *  # noqa: F401,F403
from typing import Tuple

from gate_core import (
    _artifact_exists,
    _event_asset_rel,
    _event_status_pass,
    _event_value_any,
    _final_media_exists,
    _final_media_rels,
    _load_production_events,
    _production_events_path,
    _production_mode_contract_issues,
    _recipe_event_missing_fields,
    _recipe_return_stage_for_asset,
    _seed_record_value,
)

def check_seed_event_records(root: str, ep: str) -> None:
    """If a generation tried to use a seed, the ledger must say whether it worked.

    Closed backends may not expose seed. That is acceptable only when the
    production event records `seed_effective=false` and the support state, so the
    project does not accidentally treat the output as reproducible.
    """
    path = _production_events_path(root)
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() != "image":
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        requested = _seed_record_value(event, "requested_seed")
        if not requested:
            continue
        missing = [
            key for key in ("seed_strategy", "seed_support", "seed_effective")
            if not _seed_record_value(event, key)
        ]
        if missing:
            add(WARN, "固定 Seed", f"{path}:line {idx}",
                "image 生成事件记录了 requested_seed，但缺少 " + ", ".join(missing) +
                "；支持 seed 时要记 effective_seed/seed_effective=true，不支持时要记 seed_effective=false + seed_support=unsupported_or_unknown。")
        effective = _seed_record_value(event, "seed_effective").lower()
        if effective in {"true", "1", "yes", "pass", "supported"} and not _seed_record_value(event, "effective_seed"):
            add(WARN, "固定 Seed", f"{path}:line {idx}",
                "seed_effective=true 但缺 effective_seed；无法证明实际传入的是固定 seed pool。")

def _recipe_evidence_stages_for_gate(stage: str) -> Tuple[str, ...]:
    """Return final-media families that should be audited at this gate stage.

    Image-family gates must not fail on stale/old video MP4s before the video
    rerun has a chance to create fresh events.  Likewise video preflight should
    prove image provenance before spending video budget, but video MP4 receipts
    belong to the post-video gate and later delivery gates.
    """
    stage = str(stage or "").strip()
    if stage in {"image_prompt_preflight", "image_preflight", "image"}:
        return ("image",)
    if stage in {"video_prompt_preflight", "video_preflight"}:
        return ("image",)
    return tuple(RECIPE_EVIDENCE_STAGES)


def check_generation_recipe_evidence(root: str, ep: str, stage: str) -> None:
    """Release-grade recipe evidence for each final AI-generated image/video media."""
    sev = BLOCK  # 铁律 B11（2026-06-27）：生成配方留痕 demo 也 BLOCK，不随 profile 降级。
    path = _production_events_path(root)
    audited_stages = _recipe_evidence_stages_for_gate(stage)
    latest_by_asset: Dict[str, Tuple[int, Mapping[str, Any]]] = {}
    for idx, event in enumerate(_load_production_events(root), start=1):
        if str(event.get("episode") or "").strip() != ep:
            continue
        if str(event.get("stage") or "").strip() not in audited_stages:
            continue
        if str(event.get("event") or "").strip() not in {"generation", "redraw"}:
            continue
        if not _event_status_pass(event):
            continue
        rel = _event_asset_rel(root, event)
        if rel:
            latest_by_asset[rel] = (idx, event)
    final_rels = _final_media_rels(root, ep, audited_stages)
    # A pre-spend gate may run before this episode has produced any final media.
    # In that state the ledger can legitimately contain shared-library build
    # events tagged with the episode that funded them.  Those are inputs to the
    # episode, not final episode outputs, and legacy shared events must not be
    # mistaken for missing recipe receipts on a not-yet-generated episode.
    # Once even one episode PNG/MP4 exists, `final_rels` is authoritative and
    # every landed final asset remains subject to the full recipe gate.
    if stage in {
        "image_prompt_preflight",
        "image_preflight",
        "video_prompt_preflight",
        "video_preflight",
    } and not final_rels:
        return
    targets = final_rels or sorted(latest_by_asset)
    if not targets:
        if _final_media_exists(root, ep, audited_stages):
            add(
                sev,
                "生成配方证据",
                path,
                "本集已有最终图片/视频媒体，但 production_events.jsonl 缺 image/video generation/redraw pass 记录；"
                "无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、"
                "reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。",
                return_to_stage="image",
            )
        return
    for rel in targets:
        if rel not in latest_by_asset:
            add(
                sev,
                "生成配方证据",
                path,
                f"{rel} 是本集最终媒体，但 production_events.jsonl 缺对应 image/video generation/redraw pass 记录；"
                "无法追溯 provider/model/channel/route_hash、capability_evidence_id、recipe_hash、prompt_sha256、"
                "reference_bundle_sha256、backend_version、quality_tier、actual_image_inputs 和 seed 是否真实生效。",
                return_to_stage=_recipe_return_stage_for_asset(rel),
            )
            continue
        idx, event = latest_by_asset[rel]
        missing = _recipe_event_missing_fields(event)
        if not missing:
            _warn_missing_recipe_reference_inputs(root, path, idx, rel, event)
            continue
        add(
            sev,
            "生成配方证据",
            f"{path}:line {idx}",
            f"{rel} 生成事件缺必填配方证据：{', '.join(missing)}。"
            "每个最终媒体必须记录 provider/model/channel/route_hash/capability_evidence_id/"
            "recipe_hash/prompt_sha256/reference_bundle_sha256/backend_version/quality_tier/"
            "actual_image_inputs，并在 seed 不生效时显式 seed_effective=false + seed_support。",
            return_to_stage=_recipe_return_stage_for_asset(rel),
        )


def _warn_missing_recipe_reference_inputs(root: str, path: str, idx: int, rel: str, event) -> None:
    """收据字段齐 ≠ 参考图仍在：actual_image_inputs 指向的文件被移动/删除时复现链断裂。

    gate 对「参考图是否真传」原本只有 prompt 文本代理校验；这条把收据里登记的实际输入
    与当前磁盘对账。WARN 不 BLOCK：归档清理是允许的，但漂移必须可见、不可静默。
    """
    inputs = _event_value_any(event, "actual_image_inputs")
    if not isinstance(inputs, (list, tuple)):
        return
    gone = []
    for item in inputs:
        raw = str(item.get("path") if isinstance(item, Mapping) else item or "").strip()
        if not raw or raw.startswith(("http://", "https://")):
            continue
        candidate = raw if os.path.isabs(raw) else os.path.join(root, raw)
        if not os.path.exists(candidate):
            gone.append(raw)
    if gone:
        add(
            WARN,
            "生成配方证据",
            f"{path}:line {idx}",
            f"{rel} 收据登记的实际参考输入已不在盘上：{', '.join(gone[:4])}"
            f"{' 等' if len(gone) > 4 else ''}；复现/审计链断裂——确认是显式归档清理，"
            "或恢复参考文件后重跑 gate。",
            return_to_stage=_recipe_return_stage_for_asset(rel),
        )

def check_production_mode_contract_sync(root: str, ep: str, stage: str) -> None:
    """Meta-gate: A/B/C/D production-mode docs must match executable enum values."""
    issues = _production_mode_contract_issues()
    if not issues:
        return
    add(
        BLOCK,
        "制作模式口径",
        os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "n2d", "SKILL.md")),
        "制作模式 A/B/C/D 文档与枚举不一致：" + "；".join(issues) +
        "。修正 n2d/SKILL.md、选择点文档和测试后再继续，避免把后配音误路由到配音先行。",
        return_to_stage="script_stage1",
    )

def check_progress_artifact_signoff(root: str, ep: str, cols: Iterable[str]) -> None:
    """文本×产物双签：被判 ✅ 的列，用 STAGE_GRAPH 的 output_contract/outputs 验关键产物真在磁盘。

    `require_progress` 只信 `_进度.md` 单元格 ✅，手改进度把"配音 ✅"写上但实际没产 时长清单 也放行。
    本检查把"单一真相"从纯文本升级为"文本+产物双签"：✅ 但关键产物缺 → BLOCK，回退对应阶段。
    """
    header, row = row_for(root, ep)
    if row is None:
        return
    for col in cols:
        if col not in header or not is_done(row.get(col, "")):
            continue  # 未完成的列由 require_progress 负责，这里只验已判 ✅ 的
        spec = stage_for_progress_column(col)
        if not spec:
            continue
        loc = os.path.join(root, "_进度.md")
        oc = spec.get("output_contract")
        if isinstance(oc, dict) and oc.get("any_of"):
            variants = [v for v in oc["any_of"] if isinstance(v, dict)]
            if not any(all(_artifact_exists(root, ep, a) for a in v.get("all_of", ())) for v in variants):
                labels = " 或 ".join(str(v.get("label", "")) for v in variants)
                add(BLOCK, "产物签收", loc,
                    f"{ep}「{col}」标 ✅ 但关键产物缺失（需满足其一：{labels}）——文本与产物背离，补产物或修进度",
                    return_to_stage=spec.get("return_to_stage"))
        else:
            outs = spec.get("outputs") or ()
            if outs and not any(_artifact_exists(root, ep, a) for a in outs):
                add(BLOCK, "产物签收", loc,
                    f"{ep}「{col}」标 ✅ 但「{spec.get('label')}」产物一个都不在磁盘（如 {str(outs[0]).format(ep=ep)}）"
                    f"——幻影完成，补产物或修进度", return_to_stage=spec.get("return_to_stage"))

__all__ = [
    'check_seed_event_records',
    'check_generation_recipe_evidence',
    'check_production_mode_contract_sync',
    'check_progress_artifact_signoff',
]
