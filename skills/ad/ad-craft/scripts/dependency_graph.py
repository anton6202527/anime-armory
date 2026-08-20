#!/usr/bin/env python3
"""Content-addressed ad artifact dependency graph and acceptance receipts.

The graph is VCS-free.  A stage receipt records the exact input and output
digests it accepted.  Changed inputs invalidate that stage; after the stage is
rerun and accepted, changed outputs naturally invalidate only their direct
downstream nodes.  Image/video nodes are per shot and compose nodes are per
deliverable, so a local asset change does not invalidate unrelated shots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import contract


KIND = "ad_artifact_dependency_graph"
RECEIPT_KIND = "ad_dependency_receipts"
SCHEMA_VERSION = 1
STAGES = ("brief", "concept", "script", "voice", "storyboard", "image", "video",
          "compose", "handoff", "review", "feedback")


def load(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def file_sha(path: Path):
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _file_token(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    return {"kind": "file", "path": rel, "sha256": file_sha(path),
            "size": path.stat().st_size if path.is_file() else None}


def _value_token(name: str, value: Any) -> dict[str, Any]:
    return {"kind": "value", "name": name, "sha256": stable_sha(value)}


def _strict_project_file_token(root: Path, name: str, value: Any) -> dict[str, Any]:
    """Hash a dynamic path only when it is confined to ``root``.

    Feedback paths come from user-authored plans and receipts.  Treating
    ``root / value`` as sufficient would allow absolute paths, ``../`` and an
    in-project symlink to make the graph read bytes outside the project.  An
    invalid reference is therefore represented by a stable value sentinel;
    its target is never opened.
    """
    raw = str(value or "").strip()
    path = Path(raw)
    reason = ""
    if not raw:
        reason = "missing"
    elif path.is_absolute():
        reason = "absolute"
    elif ".." in path.parts:
        reason = "parent_traversal"
    else:
        base = root.resolve()
        try:
            resolved = (base / path).resolve()
            resolved.relative_to(base)
        except (OSError, RuntimeError, ValueError):
            reason = "symlink_or_resolve_escape"
    if reason:
        return _value_token(
            f"invalid_project_path:{name}",
            {"path": raw, "reason": reason},
        )
    return _file_token(root, path.as_posix())


EVIDENCE_REF_KEYS = {
    "evidence_file", "status_evidence_file", "redirect_evidence_file",
    "diagnostics_evidence_file", "license_file", "basis_file", "conversion_evidence",
}


def _evidence_records(value: Any, prefix="brief"):
    """Yield evidence refs embedded in brief, including nested creator receipts."""
    if isinstance(value, Mapping):
        claimed = value.get("evidence_sha256")
        for key, child in value.items():
            name = f"{prefix}.{key}"
            if key in EVIDENCE_REF_KEYS and child:
                yield name, str(child), claimed
            elif key == "platform_safe_zone_evidence" and isinstance(child, Mapping):
                for placement, ref in child.items():
                    if ref:
                        yield f"{name}.{placement}", str(ref), ""
            else:
                yield from _evidence_records(child, name)
    elif isinstance(value, list):
        for pos, child in enumerate(value):
            yield from _evidence_records(child, f"{prefix}[{pos}]")


def _evidence_token(root: Path, name: str, ref: str, claimed: Any = ""):
    if ref.startswith(("https://", "http://", "record:", "doi:")):
        return _value_token(f"evidence:{name}", {"ref": ref, "claimed_sha256": str(claimed or "")})
    path = Path(ref)
    if path.is_absolute():
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except ValueError:
            return _value_token(f"external_evidence:{name}", {"path": str(path), "sha256": file_sha(path)})
    else:
        rel = path.as_posix()
    return _file_token(root, rel)


def brief_evidence_tokens(root: Path, brief: Mapping[str, Any]):
    tokens = []
    seen = set()
    for name, ref, claimed in _evidence_records(brief):
        key = (ref, str(claimed or ""))
        if key in seen:
            continue
        seen.add(key)
        tokens.append(_evidence_token(root, name, ref, claimed))
    return tokens


def _feedback_brief_evidence_tokens(root: Path, brief: Mapping[str, Any]):
    """Strict project-local variant of ``brief_evidence_tokens`` for feedback.

    The general production graph preserves legacy external evidence references
    as value tokens.  Feedback acceptance is a formal statistical receipt, so
    every local evidence dependency must instead pass the same traversal and
    symlink confinement rule as raw exports and media assets.
    """
    tokens = []
    seen = set()
    for name, ref, _claimed in _evidence_records(brief):
        if ref in seen:
            continue
        seen.add(ref)
        tokens.append(_strict_project_file_token(root, f"feedback_brief_evidence:{name}", ref))
    return tokens


def _feedback_inputs(root: Path, brief: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Discover the complete, project-confined analysis basis for feedback."""
    plan = load(root / "投放反馈" / "experiment_plan.json", {}) or {}
    report = load(root / "投放反馈" / "feedback_report.json", {}) or {}
    inputs = [
        _file_token(root, "需求/brief.json"),
        _file_token(root, "生产数据/campaign_readiness.json"),
        _file_token(root, "投放反馈/experiment_plan.json"),
        _file_token(root, "投放反馈/experiment_plan_validation.json"),
    ]
    inputs.extend(_feedback_brief_evidence_tokens(root, brief))

    variants = plan.get("variants") if isinstance(plan, Mapping) else []
    for pos, row in enumerate(variants or [], 1):
        if not isinstance(row, Mapping):
            inputs.append(_value_token(
                f"invalid_feedback_variant:{pos}", {"value": row, "reason": "not_object"}))
            continue
        variant_id = str(row.get("variant_id") or pos)
        inputs.append(_strict_project_file_token(
            root, f"feedback_variant_asset:{variant_id}", row.get("asset_path")))

    receipts = report.get("analysis_receipts") if isinstance(report, Mapping) else {}
    receipts = receipts if isinstance(receipts, Mapping) else {}
    raw_receipt = receipts.get("raw_source") if isinstance(receipts.get("raw_source"), Mapping) else {}
    source = report.get("source_data") if isinstance(report, Mapping) else {}
    source = source if isinstance(source, Mapping) else {}
    raw_path = raw_receipt.get("path") or source.get("path")
    inputs.append(_strict_project_file_token(root, "feedback_raw_source", raw_path))

    design_mode = str(plan.get("design_mode") or "").strip().lower() if isinstance(plan, Mapping) else ""
    if design_mode == "platform_native":
        platform = plan.get("platform_experiment") if isinstance(plan.get("platform_experiment"), Mapping) else {}
        config = platform.get("config_receipt") if isinstance(platform.get("config_receipt"), Mapping) else {}
        config_path = config.get("evidence_path") or config.get("evidence_file")
        inputs.append(_strict_project_file_token(
            root, "feedback_platform_config_evidence", config_path))

        result_rel = "投放反馈/platform_experiment_result.json"
        inputs.append(_file_token(root, result_rel))
        result = load(root / result_rel, {}) or {}
        result_path = (result.get("evidence_path") or result.get("evidence_file")) \
            if isinstance(result, Mapping) else ""
        inputs.append(_strict_project_file_token(
            root, "feedback_platform_result_evidence", result_path))
    return inputs


def brief_evidence_paths(root: Path, brief: Mapping[str, Any] | None = None):
    """Absolute local evidence paths for mtime-based legacy review checks."""
    brief = brief if isinstance(brief, Mapping) else (load(root / "需求" / "brief.json", {}) or {})
    paths = []
    seen = set()
    for _name, ref, _claimed in _evidence_records(brief):
        if ref.startswith(("https://", "http://", "record:", "doi:")):
            continue
        path = Path(ref)
        if not path.is_absolute():
            path = root / path
        value = str(path)
        if value not in seen:
            seen.add(value)
            paths.append(value)
    return paths


def _digest(tokens: Iterable[Mapping[str, Any]]) -> str:
    rows = sorted((dict(row) for row in tokens), key=lambda row: (str(row.get("path") or ""), str(row.get("name") or "")))
    return stable_sha(rows)


def _compose_receipt_value(root: Path) -> dict[str, Any]:
    """Return only compose receipts, avoiding a dependency on our own receipt file.

    The whole ``dependency_receipts.json`` cannot safely be an input token because
    accepting handoff/review mutates that same file.  A value token over the
    compose subset gives downstream stages an exact, cycle-free acceptance edge.
    """
    doc = load(root / "生产数据" / "dependency_receipts.json", {}) or {}
    receipts = doc.get("receipts") if isinstance(doc.get("receipts"), Mapping) else {}
    return {
        str(node_id): dict(row)
        for node_id, row in receipts.items()
        if str(node_id).startswith("compose:") and isinstance(row, Mapping)
    }


def _outputs(root: Path, paths: Iterable[str]):
    rows = [_file_token(root, str(path)) for path in paths if str(path)]
    return rows, _digest(rows)


def _node(root: Path, node_id: str, stage: str, inputs, outputs):
    output_rows, output_digest = _outputs(root, outputs)
    return {"node_id": node_id, "stage": stage, "inputs": list(inputs), "outputs": output_rows,
            "input_sha256": _digest(inputs), "output_sha256": output_digest,
            "missing_outputs": [row["path"] for row in output_rows if not row.get("sha256")]}


def _settings_value(root: Path, key: str):
    try:
        raw = (root / "_设置.md").read_text(encoding="utf-8")
    except OSError:
        return ""
    for line in raw.splitlines():
        m = re.match(r"\s*[-*]?\s*([^:：#]+)[:：]\s*([^#]+)", line)
        if m and m.group(1).strip() == key:
            return m.group(2).strip()
    return ""


def _shot_id(row: Mapping[str, Any], pos: int) -> str:
    return str(row.get("shot_id") or row.get("clip_id") or row.get("id") or f"S{pos:02d}")


def _shot_label(row: Mapping[str, Any], pos: int) -> str:
    sid = _shot_id(row, pos)
    match = re.search(r"\d+", sid)
    return f"镜头{int(match.group()):02d}" if match else sid


def _asset_ids(row: Mapping[str, Any]):
    raw = row.get("assets") or {}
    if isinstance(raw, Mapping):
        return [str(key) for key, used in raw.items() if used]
    return [str(value) for value in raw] if isinstance(raw, list) else []


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _asset_subtrees(value: Any, asset_id: str):
    if isinstance(value, Mapping):
        if str(value.get("id") or "") == asset_id:
            yield value
            return
        for key, child in value.items():
            if str(key) == asset_id:
                yield child
            else:
                yield from _asset_subtrees(child, asset_id)
    elif isinstance(value, list):
        for child in value:
            yield from _asset_subtrees(child, asset_id)


def _asset_refs(root: Path, registry: Mapping[str, Any], asset_ids):
    refs = []
    suffixes = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".json", ".md")
    for aid in asset_ids:
        subtrees = list(_asset_subtrees(registry, aid))
        if not subtrees:
            refs.append(_value_token(f"asset_missing:{aid}", None))
            continue
        for subtree in subtrees:
            refs.append(_value_token(f"asset_record:{aid}", subtree))
            for raw in _strings(subtree):
                text = str(raw).strip()
                if text.lower().endswith(suffixes):
                    path = Path(text)
                    try:
                        rel = path.as_posix() if not path.is_absolute() else path.relative_to(root).as_posix()
                    except ValueError:
                        refs.append(_value_token(f"external_asset_path:{aid}", text))
                        continue
                    token = _file_token(root, rel)
                    if token not in refs:
                        refs.append(token)
        refs.append(_value_token(f"asset_id:{aid}", aid))
    return refs


def _cutdown_kept(root: Path, item: Mapping[str, Any]):
    if item.get("kind") != "cutdown":
        return None
    duration = str(item.get("duration") or "")
    safe = re.sub(r"[^0-9A-Za-z_.\-\u4e00-\u9fff]+", "_", duration).strip("_")
    plan = load(root / "合成" / "cutdown" / f"plan_{safe}.json", {}) or {}
    return {str(v) for v in plan.get("kept_shots") or []} or None


def discover(root: Path) -> list[dict[str, Any]]:
    root = root.resolve()
    brief = load(root / "需求" / "brief.json", {}) or {}
    storyboard = load(root / "脚本" / "storyboard.json", {}) or {}
    registry = load(root / "出图" / "共享" / "asset_registry.json", {}) or {}
    plan = load(root / "合成" / "delivery_plan.json", {}) or {}
    shots = [row for row in (storyboard.get("shots") or storyboard.get("clips") or []) if isinstance(row, Mapping)]
    nodes = []
    nodes.append(_node(root, "brief", "brief", [_file_token(root, "需求/brief.json")], ["需求/brief.json"]))
    nodes.append(_node(root, "concept", "concept", [
        _value_token("brief_strategy", {key: brief.get(key) for key in ("brand", "product", "usp", "audience", "campaign_objective", "tone", "key_message", "mandatories")}),
    ], ["创意/concept.json", "创意/concept.md", "创意/创意脚本.md"]))
    nodes.append(_node(root, "script", "script", [
        _file_token(root, "创意/concept.json"), _file_token(root, "创意/concept.md"),
        _file_token(root, "创意/创意脚本.md"),
        _value_token("brief_script", {key: brief.get(key) for key in ("claims", "mandatories", "must_avoid", "campaign_objective")}),
    ], ["脚本/广告脚本.md", "脚本/voiceover.txt", "脚本/时间轴.json", "脚本/广告法机检报告.json"]))
    nodes.append(_node(root, "voice", "voice", [
        _file_token(root, "脚本/voiceover.txt"), _value_token("voice_backend", _settings_value(root, "配音后端")),
        # 音色注册表也是 voice 的真实输入：voice_key 由 render_voice 读它计算。
        # 无条件登记（缺失时 sha256=null 作 sentinel），改音色绑定/补建 voicemap 都会触发 stale。
        _file_token(root, "设定库/voicemap.json"),
    ], ["配音/时长清单.json", "配音/vo.wav", "配音/voice_qc.json"]))
    nodes.append(_node(root, "storyboard", "storyboard", [
        _file_token(root, "创意/concept.json"), _file_token(root, "脚本/广告脚本.md"),
        _file_token(root, "脚本/时间轴.json"),
        _file_token(root, "配音/时长清单.json"),
        _value_token("brief_storyboard", {key: brief.get(key) for key in ("claims", "mandatories", "deliverables")}),
    ], ["脚本/storyboard.json", "脚本/镜头时长.json", "脚本/字幕_zh.srt"]))
    image_by_shot = {}
    video_by_shot = {}
    for pos, shot in enumerate(shots, 1):
        sid, label = _shot_id(shot, pos), _shot_label(shot, pos)
        image_inputs = [_value_token(f"storyboard:{sid}", shot), _file_token(root, f"出图/分镜/prompt/{label}.md")]
        image_inputs.extend(_asset_refs(root, registry, _asset_ids(shot)))
        image_outputs = [f"出图/分镜/图片/{label}.png"]
        if bool((shot.get("continuity") or {}).get("need_end_frame") if isinstance(shot.get("continuity"), Mapping) else shot.get("need_end_frame")):
            image_outputs.append(f"出图/分镜/图片/{label}_end.png")
        inode = _node(root, f"image:{sid}", "image", image_inputs, image_outputs)
        nodes.append(inode); image_by_shot[sid] = inode
        video_inputs = [_value_token(f"storyboard:{sid}", shot), _file_token(root, f"出视频/分镜/prompt/{label}.md")]
        video_inputs.extend(image_outputs and [_file_token(root, rel) for rel in image_outputs])
        vnode = _node(root, f"video:{sid}", "video", video_inputs, [f"出视频/分镜/视频/{label}.mp4"])
        nodes.append(vnode); video_by_shot[sid] = vnode
    locale = load(root / "合规" / "locale_matrix.json", {}) or {}
    for item in plan.get("deliverables") or []:
        if item.get("status") == "cancelled" or not item.get("deliverable_id"):
            continue
        did = str(item["deliverable_id"])
        kept = _cutdown_kept(root, item)
        locale_map = locale.get("deliverable_locales") if isinstance(locale.get("deliverable_locales"), Mapping) else {}
        locale_rows = locale.get("locales") if isinstance(locale.get("locales"), Mapping) else {}
        mapped = locale_map.get(did) or []
        if isinstance(mapped, str):
            mapped = [mapped]
        mapped = [str(value) for value in mapped if str(value)]
        locale_slice = {"default_locale": locale.get("default_locale"), "deliverable_id": did,
                        "locales": {key: locale_rows.get(key) for key in mapped}}
        compose_inputs = [
            _value_token(f"delivery:{did}", item),
            _value_token(f"locale_contract:{did}", locale_slice),
            _file_token(root, "合成/delivery_plan.json"),
            _file_token(root, "合成/delivery_qc.json"),
            _file_token(root, "生产数据/render_profile.json"),
            _file_token(root, "生产数据/placement_adaptation.json"),
            # The exact final bytes are both a compose output and a release/QC
            # input.  Recording both edges makes post-QC media replacement stale.
            _file_token(root, str(item.get("expected_path") or "")),
        ]
        if item.get("kind") == "reframe":
            compose_inputs.append(_file_token(
                root, f"生产数据/placement_adaptation_receipts/{did}.json"))
        for sid, vnode in video_by_shot.items():
            if kept is None or sid in kept:
                compose_inputs.extend(vnode["outputs"])
        localized_paths = []
        for locale_id in mapped:
            row = locale_rows.get(locale_id) if isinstance(locale_rows.get(locale_id), Mapping) else {}
            localized_paths.extend(str(row.get(key) or "") for key in ("voiceover_path", "subtitle_path"))
        if not mapped:
            # 无 locale matrix 分支：整轨 VO 直接混进成片，重配音必须让 compose 变 stale。
            localized_paths.extend(("配音/vo.wav", "脚本/字幕_zh.srt", "脚本/字幕_en.srt"))
        localized_paths.append("合成/_work/endcard.png")
        # 无条件登记：文件缺失时 _file_token 的 sha256=null 就是 sentinel，参与 input hash。
        # 从缺到有 / 从有到缺都会改变哈希 → 触发 stale。旧收据（当年只登记存在的文件）
        # 会因 token 集合变化被判 stale_input，属预期：要求该交付件重新验收一次。
        for rel in dict.fromkeys(path for path in localized_paths if path):
            compose_inputs.append(_file_token(root, rel))
        nodes.append(_node(root, f"compose:{did}", "compose", compose_inputs, [str(item.get("expected_path") or "")]))
    handoff_inputs = [_file_token(root, "需求/brief.json"), _file_token(root, "合规/ai_usage.json"),
                      _file_token(root, "合规/locale_matrix.json"), _file_token(root, "合规/provenance_qc.json"),
                      _file_token(root, "生产数据/stage_acceptance/compose.json"),
                      _value_token("compose_dependency_receipts", _compose_receipt_value(root))]
    handoff_inputs.extend(brief_evidence_tokens(root, brief))
    handoff_inputs.extend(row for node in nodes if node["stage"] == "compose" for row in node["outputs"])
    nodes.append(_node(root, "handoff", "handoff", handoff_inputs,
                       ["生产数据/campaign_readiness.json", "合规/locale_matrix_validation.json",
                        "合规/release_variant_manifest.json", "合规/compliance_manifest.json"]))
    review_inputs = [_file_token(root, rel) for rel in (
        "生产数据/campaign_readiness.json", "合规/compliance_manifest.json",
        "合规/release_variant_manifest.json", "合成/delivery_qc.json",
        "合成/accessibility_qc.json", "合成/rendered_text_qc.json", "合成/asr_consistency.json",
        "生产数据/final_media_consistency.json", "生产数据/consistency_findings.json",
        "生产数据/stage_acceptance/compose.json", "生产数据/render_profile.json",
        "生产数据/placement_adaptation.json")]
    review_inputs.append(_value_token("compose_dependency_receipts", _compose_receipt_value(root)))
    review_inputs.extend(brief_evidence_tokens(root, brief))
    review_inputs.extend(row for node in nodes if node["stage"] == "compose" for row in node["outputs"])
    nodes.append(_node(root, "review", "review", review_inputs, ["合规/ad_review_m0.json", "合规/human_signoff.json"]))
    nodes.append(_node(root, "feedback", "feedback", _feedback_inputs(root, brief),
                       ["投放反馈/feedback_report.json"]))
    return nodes


def analyze(root: Path) -> dict[str, Any]:
    root = root.resolve()
    receipt_path = root / "生产数据" / "dependency_receipts.json"
    receipt_doc = load(receipt_path, {}) or {}
    receipts = receipt_doc.get("receipts") if isinstance(receipt_doc.get("receipts"), Mapping) else {}
    nodes = discover(root)
    stage_summary = {stage: {"current": 0, "stale": 0, "unaccepted": 0, "missing": 0} for stage in STAGES}
    for node in nodes:
        receipt = receipts.get(node["node_id"]) if isinstance(receipts, Mapping) else None
        if node["missing_outputs"]:
            status = "missing_output"
            stage_summary[node["stage"]]["missing"] += 1
        elif not isinstance(receipt, Mapping):
            status = "unaccepted"
            stage_summary[node["stage"]]["unaccepted"] += 1
        elif receipt.get("input_sha256") != node["input_sha256"]:
            status = "stale_input"
            stage_summary[node["stage"]]["stale"] += 1
        elif receipt.get("output_sha256") != node["output_sha256"]:
            status = "output_changed"
            stage_summary[node["stage"]]["stale"] += 1
        else:
            status = "current"
            stage_summary[node["stage"]]["current"] += 1
        node["status"] = status
        node["accepted_receipt"] = dict(receipt) if isinstance(receipt, Mapping) else None
    return {"schema_version": SCHEMA_VERSION, "kind": KIND, "generated_at": datetime.now(timezone.utc).isoformat(),
            "receipt_path": "生产数据/dependency_receipts.json", "nodes": nodes, "stages": stage_summary,
            "summary": {"current": sum(n["status"] == "current" for n in nodes),
                        "stale": sum(n["status"] in {"stale_input", "output_changed"} for n in nodes),
                        "unaccepted": sum(n["status"] == "unaccepted" for n in nodes),
                        "missing": sum(n["status"] == "missing_output" for n in nodes)}}


def write_graph(root: Path):
    payload = analyze(root)
    out = root.resolve() / "生产数据" / "artifact_dependency_graph.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload, out


def stage_snapshot(root: Path, stage: str) -> dict[str, Any]:
    """Deterministic dependency snapshot bound into a stage acceptance report."""
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    rows = [{
        "node_id": node["node_id"],
        "input_sha256": node["input_sha256"],
        "output_sha256": node["output_sha256"],
        "missing_outputs": list(node["missing_outputs"]),
    } for node in discover(root.resolve()) if node["stage"] == stage]
    rows.sort(key=lambda row: row["node_id"])
    return {"stage": stage, "nodes": rows, "sha256": stable_sha(rows)}


def stage_snapshot_sha256(root: Path, stage: str) -> str:
    return stage_snapshot(root, stage)["sha256"]


def _current_formal_compose_report(report: Mapping[str, Any], expected_snapshot: str) -> bool:
    findings = report.get("findings") if isinstance(report.get("findings"), list) else []
    return (
        report.get("schema_version") == 1
        and report.get("kind") == "ad_stage_acceptance"
        and report.get("contract_version") == contract.CONTRACT_VERSION
        and report.get("acceptance_version") == contract.STAGE_ACCEPTANCE_VERSION
        and report.get("stage") == "compose"
        and report.get("mode") == "formal"
        and bool((report.get("summary") or {}).get("accepted"))
        and int((report.get("summary") or {}).get("block") or 0) == 0
        and not any(isinstance(row, Mapping) and row.get("severity") == "block" for row in findings)
        and report.get("dependency_snapshot_sha256") == expected_snapshot
    )


def compose_acceptance_status(root: Path) -> dict[str, Any]:
    """Verify the formal compose report and every compose dependency receipt."""
    root = root.resolve()
    report_path = root / "生产数据" / "stage_acceptance" / "compose.json"
    report = load(report_path, {}) or {}
    expected_snapshot = stage_snapshot_sha256(root, "compose")
    report_valid = _current_formal_compose_report(report, expected_snapshot)
    analyzed = analyze(root)
    nodes = [node for node in analyzed["nodes"] if node["stage"] == "compose"]
    receipts_current = bool(nodes) and all(node.get("status") == "current" for node in nodes)
    return {
        "accepted": report_valid and receipts_current,
        "report_path": "生产数据/stage_acceptance/compose.json",
        "report_sha256": file_sha(report_path),
        "dependency_snapshot_sha256": expected_snapshot,
        "reported_dependency_snapshot_sha256": report.get("dependency_snapshot_sha256"),
        "report_valid": report_valid,
        "receipts_current": receipts_current,
        "compose_nodes": [{"node_id": node["node_id"], "status": node.get("status"),
                           "input_sha256": node["input_sha256"],
                           "output_sha256": node["output_sha256"]} for node in nodes],
        "receipt_sha256": stable_sha(_compose_receipt_value(root)),
    }


def accept_stage(root: Path, stage: str, *, allow_unchanged_output=False):
    root = root.resolve()
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    receipt_path = root / "生产数据" / "dependency_receipts.json"
    doc = load(receipt_path, {}) or {"schema_version": SCHEMA_VERSION, "kind": RECEIPT_KIND, "receipts": {}}
    receipts = doc.setdefault("receipts", {})
    selected = [node for node in discover(root) if node["stage"] == stage]
    if not selected:
        raise ValueError(f"no dependency nodes for stage {stage}")
    if stage == "compose":
        report = load(root / "生产数据" / "stage_acceptance" / "compose.json", {}) or {}
        expected_snapshot = stage_snapshot_sha256(root, "compose")
        if not _current_formal_compose_report(report, expected_snapshot):
            raise ValueError(
                "compose receipt requires current formal accepted "
                "生产数据/stage_acceptance/compose.json bound to the dependency snapshot"
            )
    for node in selected:
        if node["missing_outputs"]:
            raise ValueError(f"{node['node_id']} missing outputs: {', '.join(node['missing_outputs'])}")
        old = receipts.get(node["node_id"])
        if (isinstance(old, Mapping) and old.get("input_sha256") != node["input_sha256"] and
                old.get("output_sha256") == node["output_sha256"] and not allow_unchanged_output):
            raise ValueError(f"{node['node_id']} input changed but output did not; rerun artifact or use explicit waiver")
        receipts[node["node_id"]] = {"stage": stage, "input_sha256": node["input_sha256"],
                                     "output_sha256": node["output_sha256"],
                                     "accepted_at": datetime.now(timezone.utc).isoformat()}
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_graph(root)
    return selected


def upstream_findings(root: Path, stage: str):
    if stage not in STAGES:
        return []
    report = analyze(root)
    receipt_path = root.resolve() / "生产数据" / "dependency_receipts.json"
    if not receipt_path.is_file():
        return [{"severity": "warn" if stage == STAGES[0] else "block",
                 "code": "dependency_receipts_missing",
                 "msg": ("缺内容哈希依赖收据；brief 通过后将建立首张收据" if stage == STAGES[0]
                         else "缺上游内容哈希收据；须从 brief 起按顺序重验，不能从中段继承旧 ✅")}]
    before = set(STAGES[:STAGES.index(stage)])
    findings = []
    for node in report["nodes"]:
        if node["stage"] not in before:
            continue
        if node["status"] != "current":
            findings.append({"severity": "block", "code": "upstream_dependency_stale",
                             "msg": f"上游 {node['node_id']} dependency status={node['status']}"})
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="ad content-addressed dependency graph")
    ap.add_argument("project_root")
    ap.add_argument("--accept-stage", choices=STAGES)
    ap.add_argument("--allow-unchanged-output", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.project_root).resolve()
    if ns.accept_stage:
        accepted = accept_stage(root, ns.accept_stage, allow_unchanged_output=ns.allow_unchanged_output)
        print(f"[ok] accepted {len(accepted)} dependency node(s) for {ns.accept_stage}")
    payload, out = write_graph(root)
    print(f"# dependency current={payload['summary']['current']} stale={payload['summary']['stale']} "
          f"unaccepted={payload['summary']['unaccepted']} missing={payload['summary']['missing']}")
    print(f"[ok] {out}")
    return 1 if payload["summary"]["stale"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
