#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comic production gates.

Use this as the deterministic entry guard before paid image generation and
before handing images to compose/review.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
try:
    import style_consistency
    import character_consistency
    import review as review_module
except Exception as exc:  # pragma: no cover
    style_consistency = None
    character_consistency = None
    review_module = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None

COMIC_LIB = Path(__file__).resolve().parents[2] / "comic" / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
try:
    from image_backend_adapter import resolve_capabilities
except Exception:  # pragma: no cover
    resolve_capabilities = None
try:
    from platform_profiles import profile_for_platform, validate_manifest as validate_platform_manifest
except Exception:  # pragma: no cover
    profile_for_platform = None
    validate_platform_manifest = None

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
SKILLS_ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def read_setting(root: Path, key: str, default: str = "") -> str:
    import re

    pattern = re.compile(rf"^\s*-\s*{re.escape(key)}\s*[:：]\s*(.+?)\s*$")
    for line in read_text(root / "_设置.md").splitlines():
        match = pattern.match(line)
        if match:
            return match.group(1).strip()
    return default


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def add(
    findings: list[dict[str, Any]],
    severity: str,
    code: str,
    artifact: str,
    reason: str,
    return_to_stage: str,
    suggested_fix: str,
    *,
    evidence_family: str = "deterministic",
) -> None:
    findings.append(
        {
            "severity": severity,
            "dimension": "comic_gate",
            "code": code,
            "artifact": artifact,
            "reason": reason,
            "return_to_stage": return_to_stage,
            "suggested_fix": suggested_fix,
            "evidence_family": evidence_family,
        }
    )


def find_panel_image(root: Path, chapter: str, panel_id: str) -> Path | None:
    base = root / "出图" / chapter / "panels"
    for suffix in IMAGE_EXTS:
        path = base / f"{panel_id}{suffix}"
        if path.is_file():
            return path
    matches = sorted(base.glob(f"{panel_id}.*"))
    return next((item for item in matches if item.suffix.lower() in IMAGE_EXTS), None)


def refresh_identity_report(root: Path, chapter: str, findings: list[dict[str, Any]], *, no_refresh: bool) -> dict[str, Any]:
    report_path = root / "生产数据" / f"comic_identity_report_{chapter}.json"
    if not no_refresh:
        script = SKILLS_ROOT / "comic-identity" / "scripts" / "identity.py"
        proc = subprocess.run(
            [sys.executable, str(script), str(root), "--chapter", chapter, "report", "--write"],
            stdin=subprocess.DEVNULL,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode != 0:
            add(
                findings,
                "block",
                "identity_report_refresh_failed",
                rel(root, script),
                "comic-identity report --write 运行失败：" + ((proc.stderr or proc.stdout or "").strip()[-1200:]),
                "identity",
                "修复 identity report 后重跑 gate。",
            )
            return {}
    return load_json(report_path, {})


def check_required(root: Path, chapter: str, findings: list[dict[str, Any]], keys: tuple[str, ...]) -> dict[str, Path]:
    paths = {
        "settings": root / "_设置.md",
        "progress": root / "_进度.md",
        "panel_script": root / "脚本" / chapter / "panel_script.json",
        "layout": root / "排版" / chapter / "layout.json",
        "panel_jobs": root / "出图" / chapter / "prompt" / "panel_jobs.json",
        "lettering": root / "排版" / chapter / "lettering.json",
        "manifest": root / "排版" / chapter / "export_manifest.json",
    }
    for key in keys:
        path = paths[key]
        if not path.is_file():
            add(
                findings,
                "block",
                f"{key}_missing",
                rel(root, path),
                "gate 必需文件缺失。",
                "script" if key == "panel_script" else "layout" if key == "layout" else "image" if key == "panel_jobs" else "compose",
                "补齐该阶段产物后重跑 gate。",
            )
    return paths


def check_source_semantics(root: Path, chapter: str, panel_script: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    script_source_meta = panel_script.get("source_semantics") if isinstance(panel_script.get("source_semantics"), dict) else {}
    source_semantics_path = root / str(script_source_meta.get("path") or Path("脚本") / chapter / "source_semantics.json")
    source_semantics = load_json(source_semantics_path, {})
    semantics_file_exists = source_semantics_path.is_file()
    script_requires_semantics = bool(script_source_meta.get("requires_normalization"))
    if semantics_file_exists or script_requires_semantics:
        if not source_semantics:
            add(
                findings,
                "block",
                "source_semantics_missing_or_invalid",
                rel(root, source_semantics_path),
                "source_semantics 元数据存在但文件不可解析或缺失。",
                "script",
                "重新运行 source_semantics_gate.py 并修复输出文件。",
            )
            return
        if source_semantics.get("requires_normalization") and source_semantics.get("status") != "pass":
            add(
                findings,
                "block",
                "source_semantics_not_passed",
                rel(root, source_semantics_path),
                "源语义归一化 gate 未通过：" + "；".join(map(str, source_semantics.get("issues") or [])),
                "script",
                "补齐专名表、逐段释义、目标嵌字文本、歧义处理和改编取舍账后重跑 gate。",
            )
    if not (source_semantics.get("requires_normalization") or script_requires_semantics):
        return
    contract = source_semantics.get("panel_script_contract") if isinstance(source_semantics.get("panel_script_contract"), dict) else {}
    fields = contract.get("required_panel_fields_when_normalized")
    required_fields = fields if isinstance(fields, list) and all(isinstance(item, str) for item in fields) else ["source_excerpt", "meaning_zh", "text_target", "adaptation_note"]
    missing_trace: list[str] = []
    for panel in panel_script.get("panels") or []:
        if not isinstance(panel, dict):
            continue
        pid = str(panel.get("panel_id") or "unknown")
        missing = [field for field in required_fields if not str(panel.get(field) or "").strip()]
        if missing:
            missing_trace.append(f"{pid}({','.join(missing)})")
    if missing_trace:
        add(
            findings,
            "block",
            "source_semantics_panel_trace_missing",
            f"脚本/{chapter}/panel_script.json",
            "归一化源本的 panel 缺少语义追溯字段：" + "；".join(missing_trace[:20]),
            "script",
            "为每格补 source_excerpt、meaning_zh、text_target、adaptation_note 后再排版/出图。",
        )


def compact_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, list):
        text = "；".join(compact_text(item) for item in value)
    elif isinstance(value, dict):
        text = "；".join(f"{key}:{compact_text(item)}" for key, item in value.items())
    else:
        text = str(value).strip()
    return " ".join(text.split()).strip("； ")


def panel_reference_ids(panel: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw).strip()
            if ref_id and ref_id not in ids:
                ids.append(ref_id)
    return ids


def panel_has_character(panel: dict[str, Any]) -> bool:
    return bool(panel.get("characters")) or any(ref_id.startswith(("CHAR_", "MON_")) for ref_id in panel_reference_ids(panel))


def panel_scene_anchor_id(panel: dict[str, Any]) -> str:
    for key in ("scene_anchor_id", "scene_id", "location_id"):
        value = compact_text(panel.get(key))
        if value:
            return value
    for ref_id in panel_reference_ids(panel):
        if ref_id.startswith("LOC_"):
            return ref_id
    return ""


def panel_has_scene(panel: dict[str, Any]) -> bool:
    return bool(compact_text(panel.get("location")) or panel_scene_anchor_id(panel))


def visual_contract_from(panel_script: dict[str, Any]) -> dict[str, Any]:
    contract = panel_script.get("visual_contract")
    return contract if isinstance(contract, dict) else {}


def scene_contract_from(visual_contract: dict[str, Any], scene_id: str) -> dict[str, Any]:
    anchors = visual_contract.get("scene_anchors") if isinstance(visual_contract.get("scene_anchors"), dict) else {}
    contract = anchors.get(scene_id) if scene_id else {}
    return contract if isinstance(contract, dict) else {}


def contract_value(panel: dict[str, Any], scene_contract: dict[str, Any], *keys: str) -> str:
    for key in keys:
        text = compact_text(panel.get(key))
        if text:
            return text
    for key in keys:
        text = compact_text(scene_contract.get(key))
        if text:
            return text
    return ""


CAMERA_GAZE_TERMS = (
    "看镜头",
    "直视镜头",
    "看读者",
    "直视读者",
    "看观众",
    "直视观众",
    "looking at viewer",
    "eye contact with camera",
    "camera",
    "viewer",
)
POV_CAMERA_ROLE_TERMS = ("pov", "主观", "第一人称", "破第四墙", "直视镜头", "直视读者")
VAGUE_GAZE_TERMS = ("坚定", "冷静", "愤怒", "悲伤", "惊讶", "眼神", "目光", "远方", "前方", "某处", "none", "n/a")
FACE_INTEGRITY_TERMS = ("脸", "五官", "眼", "眼型", "眼距", "发际线", "发型", "头发")
BODY_INTEGRITY_TERMS = ("手", "脚", "肢体", "身体", "腿", "手臂", "完整", "道具", "武器", "接触点")


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def camera_role_allows_direct_gaze(panel: dict[str, Any]) -> bool:
    return contains_any(compact_text(panel.get("camera_role")) + " " + compact_text(panel.get("pov")), POV_CAMERA_ROLE_TERMS)


def is_vague_gaze_target(value: str) -> bool:
    text = value.strip().lower()
    if not text:
        return False
    return any(term.lower() == text or term.lower() in text for term in VAGUE_GAZE_TERMS)


def is_weak_integrity_contract(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    return not (contains_any(text, FACE_INTEGRITY_TERMS) and contains_any(text, BODY_INTEGRITY_TERMS))


def visual_scene_anchors(visual_contract: dict[str, Any]) -> dict[str, Any]:
    anchors = visual_contract.get("scene_anchors") if isinstance(visual_contract.get("scene_anchors"), dict) else {}
    return anchors if isinstance(anchors, dict) else {}


def panel_character_refs(panel: dict[str, Any]) -> list[str]:
    return [ref_id for ref_id in panel_reference_ids(panel) if ref_id.startswith(("CHAR_", "MON_"))]


def panel_character_count(panel: dict[str, Any]) -> int:
    names = {compact_text(name) for name in panel.get("characters") or [] if compact_text(name)}
    names.update(panel_character_refs(panel))
    return len(names)


def check_panel_visual_contract(root: Path, chapter: str, panel_script: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    panels = panel_script.get("panels") if isinstance(panel_script.get("panels"), list) else []
    if not panels:
        return
    visual_contract = visual_contract_from(panel_script)
    if not visual_contract:
        add(
            findings,
            "block",
            "visual_contract_missing",
            f"脚本/{chapter}/panel_script.json",
            "panel_script 缺少 visual_contract，无法锁本话风格、场景光位、轴线视线和角色完整性口径。",
            "script",
            "在 panel_script.json 顶层补 visual_contract.scene_anchors / character_integrity_policy 后重建出图包。",
        )
    scene_anchors = visual_scene_anchors(visual_contract)
    if visual_contract and not scene_anchors:
        add(
            findings,
            "block",
            "visual_scene_anchors_missing",
            f"脚本/{chapter}/panel_script.json",
            "visual_contract 缺少 scene_anchors；漫画长线场景不能只靠逐格自然语言临场发挥。",
            "script",
            "登记 LOC_ 场景锚，并写 spatial_layout / lighting_anchor / axis_eyeline / resident_assets / forbidden_drift。",
        )
    for scene_id, scene_contract in scene_anchors.items():
        if not isinstance(scene_contract, dict):
            continue
        missing_anchor = [
            key
            for key in ("spatial_layout", "lighting_anchor", "axis_eyeline")
            if not compact_text(scene_contract.get(key))
        ]
        if missing_anchor:
            add(
                findings,
                "block",
                "scene_anchor_contract_incomplete",
                f"脚本/{chapter}/panel_script.json#visual_contract.scene_anchors.{scene_id}",
                f"{scene_id} 场景锚缺少：" + ",".join(missing_anchor) + "。场景锚必须锁布局、光位和轴线视线。",
                "script",
                "补齐该 LOC_ 的 spatial_layout、lighting_anchor、axis_eyeline 后重建出图包。",
            )
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        pid = compact_text(panel.get("panel_id")) or "unknown"
        artifact = f"脚本/{chapter}/panel_script.json#{pid}"
        if panel_has_character(panel):
            missing: list[str] = []
            gaze_target = contract_value(panel, {}, "gaze_target", "eyeline_target")
            if not gaze_target:
                missing.append("gaze_target")
            if not contract_value(panel, {}, "eyeline_direction", "gaze_direction"):
                missing.append("eyeline_direction")
            integrity_contract = contract_value(panel, visual_contract, "character_integrity", "completeness_notes", "character_integrity_policy")
            if not integrity_contract:
                missing.append("character_integrity/completeness_notes")
            if missing:
                add(
                    findings,
                    "block",
                    "panel_character_contract_missing",
                    artifact,
                    f"{pid} 含角色但缺少人物一致性字段：" + ",".join(missing) + "。漫画格也必须锁脸、眼神目标和身体完整性。",
                    "script",
                    "补 gaze_target、eyeline_direction、character_integrity/completeness_notes；动作格写清不看镜头和视线锁定戏内目标。",
                )
            if gaze_target and contains_any(gaze_target, CAMERA_GAZE_TERMS) and not camera_role_allows_direct_gaze(panel):
                add(
                    findings,
                    "block",
                    "panel_camera_gaze_unjustified",
                    artifact,
                    f"{pid} 的 gaze_target 指向读者/镜头，但 camera_role 未声明 POV 或破第四墙。无理由看镜头会破坏眼神一致性。",
                    "script",
                    "把 gaze_target 改成戏内对象/对手/道具/画外声源，或明确 camera_role=POV/破第四墙 并说明叙事理由。",
                )
            elif gaze_target and is_vague_gaze_target(gaze_target):
                add(
                    findings,
                    "warn",
                    "panel_gaze_target_vague",
                    artifact,
                    f"{pid} 的 gaze_target 过泛：{gaze_target}。眼神目标应是读者能定位的戏内对象。",
                    "script",
                    "改成对话对象、对手、道具、命中点、画外声源或下一动作目标。",
                )
            if integrity_contract and is_weak_integrity_contract(integrity_contract):
                add(
                    findings,
                    "warn",
                    "panel_character_integrity_weak",
                    artifact,
                    f"{pid} 的人物完整性契约太泛，未同时覆盖脸/眼/发和手脚/身体/关键道具。",
                    "script",
                    "补脸型、眼型/眼距、发际线、发型、服装标志，以及手脚/身体/道具/接触点完整性。",
                )
        if panel_has_scene(panel):
            scene_id = panel_scene_anchor_id(panel)
            scene_contract = scene_contract_from(visual_contract, scene_id)
            missing_scene: list[str] = []
            if not scene_id:
                missing_scene.append("scene_anchor_id/LOC_")
            elif visual_contract and scene_id not in scene_anchors:
                add(
                    findings,
                    "block",
                    "panel_scene_anchor_unregistered",
                    artifact,
                    f"{pid} 使用 {scene_id}，但 visual_contract.scene_anchors 未登记该场景锚。",
                    "script",
                    "在 visual_contract.scene_anchors 登记该 LOC_，或把本格 scene_anchor_id 改成已登记场景锚。",
                )
            if not contract_value(panel, scene_contract, "spatial_layout", "scene_layout", "layout"):
                missing_scene.append("spatial_layout")
            if not contract_value(panel, scene_contract, "lighting_anchor", "light_anchor"):
                missing_scene.append("lighting_anchor")
            if not contract_value(panel, scene_contract, "axis_eyeline", "eyeline_axis", "axis"):
                missing_scene.append("axis_eyeline")
            if missing_scene:
                add(
                    findings,
                    "block",
                    "panel_scene_contract_missing",
                    artifact,
                    f"{pid} 含场景但缺少场景连续性字段：" + ",".join(missing_scene) + "。同一场景必须继承布局、光位和轴线视线。",
                    "script",
                    "补 visual_contract.scene_anchors 或逐格 scene_anchor_id/spatial_layout/lighting_anchor/axis_eyeline 后重建出图包。",
                )
            if panel_character_count(panel) >= 2 and not contract_value(panel, scene_contract, "spatial_relationships", "blocking", "staging"):
                add(
                    findings,
                    "block",
                    "panel_multi_character_staging_missing",
                    artifact,
                    f"{pid} 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。",
                    "script",
                    "补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。",
                )


def traditional_workflow_enabled(root: Path) -> bool:
    return read_setting(root, "传统原稿流程", "启用") not in {"关闭", "off", "disabled", "false", "False"}


def finishing_panel_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for panel in plan.get("panels") or []:
        if isinstance(panel, dict) and panel.get("panel_id"):
            out[str(panel.get("panel_id"))] = panel
    return out


def check_traditional_manga_contract(
    root: Path,
    chapter: str,
    panel_script: dict[str, Any],
    layout: dict[str, Any],
    jobs: dict[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    if not traditional_workflow_enabled(root):
        return
    name_path = root / "排版" / chapter / "name_board.json"
    finish_path = root / "出图" / chapter / "finishing" / "finishing_plan.json"
    name_board = load_json(name_path, {})
    finishing_plan = load_json(finish_path, {})
    if not name_board:
        add(
            findings,
            "warn",
            "name_board_missing",
            rel(root, name_path),
            "传统原稿流程已启用，但缺少缩略分镜/name_board；页流、翻页钩子和格子轻重缺少ネーム层证据。",
            "name",
            "运行 comic-name 生成 name_board.json，再重建 layout。",
            evidence_family="workflow",
        )
    manuscript = layout.get("manuscript") if isinstance(layout.get("manuscript"), dict) else {}
    if not manuscript or not manuscript.get("safe_area"):
        add(
            findings,
            "warn",
            "manuscript_safe_area_missing",
            f"排版/{chapter}/layout.json",
            "layout 缺少 manuscript.safe_area / trim_box；页漫或投稿规格下容易把关键画面、气泡或拟声词放进裁切风险区。",
            "layout",
            "重跑 comic-layout，并确认已接入 comic-name 的原稿安全框。",
            evidence_family="workflow",
        )
    finish_map = finishing_panel_map(finishing_plan if isinstance(finishing_plan, dict) else {})
    if not finishing_plan:
        add(
            findings,
            "warn",
            "finishing_plan_missing",
            rel(root, finish_path),
            "传统原稿流程已启用，但缺少墨线/黑场/网点/效果线计划，出图 prompt 只能泛泛写漫画风。",
            "finishing",
            "运行 comic-finishing 生成 finishing_plan.json 后重建出图包。",
            evidence_family="workflow",
        )
    script_ids = [str(panel.get("panel_id")) for panel in panel_script.get("panels") or [] if isinstance(panel, dict) and panel.get("panel_id")]
    missing_finish = [pid for pid in script_ids if finishing_plan and pid not in finish_map]
    if missing_finish:
        add(
            findings,
            "warn",
            "panel_finishing_contract_missing",
            rel(root, finish_path),
            "这些 panel 缺少传统原稿收尾计划：" + "、".join(missing_finish[:20]),
            "finishing",
            "重跑 comic-finishing 或手工补 panels[].ink_plan/tone_plan/effects_plan。",
            evidence_family="workflow",
        )
    missing_job_finish = [
        str(job.get("panel_id"))
        for job in jobs.get("jobs") or []
        if isinstance(job, dict) and not job.get("traditional_finish_contract")
    ]
    if finishing_plan and missing_job_finish:
        add(
            findings,
            "warn",
            "panel_job_finish_contract_not_applied",
            f"出图/{chapter}/prompt/panel_jobs.json",
            "这些 job 未注入 traditional_finish_contract：" + "、".join(missing_job_finish[:20]),
            "image",
            "重跑 comic-image/scripts/build_panel_jobs.py，让出图包消费 finishing_plan。",
            evidence_family="workflow",
        )


def check_manifest_profile(root: Path, chapter: str, manifest: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    for item in manifest.get("platform_findings") or []:
        if not isinstance(item, dict):
            continue
        add(
            findings,
            str(item.get("severity") or "warn"),
            str(item.get("code") or "platform_profile"),
            str(item.get("artifact") or f"排版/{chapter}/export_manifest.json"),
            str(item.get("reason") or ""),
            "compose",
            str(item.get("suggested_fix") or "按平台 profile 重新导出。"),
        )
    if validate_platform_manifest and profile_for_platform:
        platform = str(manifest.get("target_platform") or read_setting(root, "目标平台", "通用"))
        profile = profile_for_platform(platform)
        usage = read_setting(root, "合规用途", "自用草稿")
        for item in validate_platform_manifest(root, manifest, profile, usage):
            add(
                findings,
                str(item.get("severity") or "warn"),
                str(item.get("code") or "platform_profile"),
                str(item.get("artifact") or f"排版/{chapter}/export_manifest.json"),
                str(item.get("reason") or ""),
                "compose",
                str(item.get("suggested_fix") or "按平台 profile 重新导出。"),
            )
    text_qc = manifest.get("text_layout_qc") if isinstance(manifest.get("text_layout_qc"), dict) else {}
    unsupported = text_qc.get("unsupported_items") if isinstance(text_qc.get("unsupported_items"), list) else []
    if unsupported:
        add(
            findings,
            "block",
            "unsupported_text_layout",
            f"排版/{chapter}/lettering.json",
            "当前嵌字 renderer 不支持 RTL 或需词典分词文字：" + "；".join(str(item.get("item_id") or item) for item in unsupported[:20] if isinstance(item, dict)),
            "compose",
            "改用人工/专业排版 renderer，或改成当前 renderer 支持的目标嵌字语言后重新导出。",
        )


def check_identity(root: Path, report: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    summary = report.get("summary") if isinstance(report, dict) else {}
    if not isinstance(summary, dict):
        add(findings, "block", "identity_report_missing", "生产数据/comic_identity_report.json", "缺少可解析的一致性报告。", "identity", "运行 comic-identity report --write。")
        return
    if int(summary.get("missing_ref_count") or 0) > 0:
        add(findings, "block", "missing_ready_refs", "生产数据/comic_identity_report.json", "仍有共享参考图缺失。", "identity", "补齐 missing_refs 后重建出图包。")
    if int(summary.get("rerun_target_count") or 0) > 0:
        add(findings, "block", "reference_rerun_targets", "生产数据/comic_identity_report.json", "存在已 ready 但未按当前参考图重抽的 panel。", "image", "按 identity report 的 rerun_targets force 重抽。")
    level = read_setting(root, "定妆级别", "长线专门定妆")
    if level.startswith("长线") or "专门定妆" in level or "高一致性" in level:
        missing = report.get("missing_character_views") if isinstance(report, dict) else {}
        if not isinstance(missing, dict):
            add(findings, "block", "missing_character_views_unreadable", "生产数据/comic_identity_report.json", "长线定妆缺少 missing_character_views 字段。", "identity", "重新运行 comic-identity report --write。")
        else:
            blockers = {key: value for key, value in missing.items() if isinstance(value, list) and value}
            if blockers:
                reason = "；".join(f"{key} 缺 {','.join(map(str, value))}" for key, value in sorted(blockers.items()))
                add(findings, "block", "missing_character_views", "生产数据/comic_identity_report.json", "长线专门定妆未补齐：" + reason, "identity", "补 front/three_quarter/side/back/face 后重跑 gate。")


def check_style_contract(root: Path, findings: list[dict[str, Any]]) -> None:
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    has_registry_style = isinstance(registry, dict) and bool(registry.get("style_contract") or registry.get("visual_style"))
    assets = registry.get("assets") if isinstance(registry, dict) and isinstance(registry.get("assets"), dict) else {}
    has_style_asset = any(str(key).startswith("STYLE_") for key in assets)
    style_anchor = read_setting(root, "风格锚", "")
    if not style_anchor and not has_registry_style and not has_style_asset:
        add(
            findings,
            "block",
            "style_anchor_missing",
            "出图/共享/identity_registry.json",
            "缺少项目风格锚或 style_contract，正式批量出图前无法约束画风。",
            "identity",
            "登记 STYLE_ 风格资产或 registry.style_contract 后重建出图包。",
        )


def check_backend(root: Path, jobs: dict[str, Any], findings: list[dict[str, Any]], notes: list[str]) -> None:
    model = str(jobs.get("model") or read_setting(root, "生图模型", "自定义"))
    channel = str(jobs.get("channel") or read_setting(root, "生图渠道", "manual"))
    if resolve_capabilities:
        caps = resolve_capabilities(model, channel)
        notes.append(f"backend adapter: {caps.adapter_id}; reference_image_limit={caps.reference_image_limit}; persistent_subject={caps.persistent_subject}")
    pairs = {
        (str(job.get("model") or model), str(job.get("source") or channel))
        for job in jobs.get("jobs") or []
        if isinstance(job, dict)
    }
    if len(pairs) > 1:
        add(
            findings,
            "block",
            "generation_recipe_mixed",
            f"出图/{jobs.get('chapter', '')}/prompt/panel_jobs.json",
            "同一话记录了多个生图模型/渠道：" + "；".join(f"{m}/{c}" for m, c in sorted(pairs)),
            "image",
            "统一模型和渠道后重建 job 包并重抽受影响格。",
        )


def check_panel_jobs_ready(root: Path, chapter: str, jobs: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    for job in jobs.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        pid = str(job.get("panel_id") or "")
        status = str(job.get("status") or "")
        panel_path = find_panel_image(root, chapter, pid)
        post_qc = job.get("post_qc") if isinstance(job.get("post_qc"), dict) else {}
        post_verdict = str(post_qc.get("verdict") or "")
        if status == "qc_block" or post_verdict == "block":
            add(
                findings,
                "block",
                "panel_post_qc_block",
                str(job.get("result_path") or f"出图/{chapter}/panels/{pid}.png"),
                f"{pid} 的落盘 post_qc=block，不能进入合成。",
                "image",
                "查看 生产数据/panel_qc，修复参考/尺寸/空图等问题后 force 重抽该格。",
            )
            continue
        if status != "ready" or not panel_path:
            add(
                findings,
                "block",
                "panel_not_ready",
                str(job.get("result_path") or f"出图/{chapter}/panels/{pid}.png"),
                f"{pid} 还不是 ready 或图像文件缺失。",
                "image",
                "补齐该 panel 图并确保 job.status=ready。",
            )
        elif post_verdict == "warn":
            add(
                findings,
                "warn",
                "panel_post_qc_warn",
                str(job.get("result_path") or rel(root, panel_path)),
                f"{pid} 的落盘 post_qc=warn，需要人审签收或重抽。",
                "image",
                "放大查看 panel_qc 与原图；确认误报时在审查报告保留签收证据。",
                evidence_family="heuristic",
            )


def merge_consistency_report(report: dict[str, Any], findings: list[dict[str, Any]], *, category: str) -> None:
    for item in report.get("findings") or []:
        severity = str(item.get("severity") or "warn")
        if severity not in {"block", "warn", "info"}:
            severity = "warn"
        add(
            findings,
            severity,
            str(item.get("code") or category),
            str(item.get("artifact") or item.get("panel_id") or ""),
            str(item.get("reason") or category),
            str(item.get("return_to_stage") or ("image" if severity in {"block", "warn"} else "review")),
            str(item.get("suggested_fix") or "按一致性报告处理。"),
            evidence_family=str(item.get("evidence_family") or category),
        )


def run_image_preflight(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    paths = check_required(root, chapter, findings, ("settings", "panel_script", "layout", "panel_jobs"))
    panel_script = load_json(paths["panel_script"], {})
    if isinstance(panel_script, dict):
        check_source_semantics(root, chapter, panel_script, findings)
        check_panel_visual_contract(root, chapter, panel_script, findings)
    layout = load_json(paths["layout"], {})
    jobs = load_json(paths["panel_jobs"], {})
    if isinstance(jobs, dict):
        check_backend(root, jobs, findings, notes)
    if isinstance(panel_script, dict) and isinstance(layout, dict) and isinstance(jobs, dict):
        check_traditional_manga_contract(root, chapter, panel_script, layout, jobs, findings)
    report = refresh_identity_report(root, chapter, findings, no_refresh=no_refresh)
    check_identity(root, report, findings)
    check_style_contract(root, findings)


def run_image(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_image_preflight(root, chapter, findings, notes, no_refresh=no_refresh)
    jobs = load_json(root / "出图" / chapter / "prompt" / "panel_jobs.json", {})
    if isinstance(jobs, dict):
        check_panel_jobs_ready(root, chapter, jobs, findings)
    if style_consistency is None or character_consistency is None:
        add(findings, "block", "consistency_module_unavailable", "skills/comic-review/scripts", f"一致性模块不可用：{IMPORT_ERROR}", "review", "修复 comic-review 模块导入。")
        return
    style_report = style_consistency.analyze(root, chapter)
    style_paths = style_consistency.write_outputs(root, chapter, style_report)
    notes.append(f"style consistency refreshed: {style_paths['markdown']}")
    merge_consistency_report(style_report, findings, category="style_consistency")
    char_report = character_consistency.analyze(root, chapter)
    char_paths = character_consistency.write_outputs(root, chapter, char_report)
    notes.append(f"character consistency refreshed: {char_paths['markdown']}")
    merge_consistency_report(char_report, findings, category="character_consistency")


def run_compose(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_image(root, chapter, findings, notes, no_refresh=no_refresh)
    paths = check_required(root, chapter, findings, ("lettering", "manifest"))
    manifest = load_json(paths["manifest"], {})
    if isinstance(manifest, dict):
        if manifest.get("missing_panels"):
            add(findings, "block", "manifest_missing_panels", rel(root, paths["manifest"]), "export_manifest 仍记录缺图。", "compose", "补图并重新导出。")
        if not manifest.get("rendered"):
            add(findings, "block", "manifest_not_rendered", rel(root, paths["manifest"]), "尚未登记实际渲染导出物。", "compose", "运行 export_longstrip.py --render。")
        check_manifest_profile(root, chapter, manifest, findings)


def run_review(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_compose(root, chapter, findings, notes, no_refresh=no_refresh)
    if review_module is None:
        add(findings, "block", "review_module_unavailable", "skills/comic-review/scripts/review.py", f"review 模块不可用：{IMPORT_ERROR}", "review", "修复 review.py 后重跑 gate。")
        return
    report = review_module.review(root, chapter, refresh_qa_preview=True)
    notes.append("comic-review report refreshed in review gate")
    for issue in report.get("issues") or []:
        add(
            findings,
            str(issue.get("severity") or "warn"),
            str(issue.get("category") or "review_issue"),
            str(issue.get("artifact") or ""),
            str(issue.get("reason") or ""),
            str(issue.get("return_to") or "review"),
            str(issue.get("suggested_fix") or "按 comic-review 报告处理。"),
        )


def dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for item in findings:
        key = (
            str(item.get("severity") or ""),
            str(item.get("code") or ""),
            str(item.get("artifact") or ""),
            str(item.get("reason") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def make_report(root: Path, chapter: str, stage: str, findings: list[dict[str, Any]], notes: list[str]) -> dict[str, Any]:
    findings = dedupe_findings(findings)
    block_count = sum(1 for item in findings if item.get("severity") == "block")
    warn_count = sum(1 for item in findings if item.get("severity") == "warn")
    info_count = sum(1 for item in findings if item.get("severity") == "info")
    return {
        "schema_version": 1,
        "kind": "comic_gate",
        "project_root": str(root),
        "chapter": chapter,
        "stage": stage,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "verdict": "block" if block_count else "warn" if warn_count else "pass",
        "summary": {
            "finding_count": len(findings),
            "block_count": block_count,
            "warn_count": warn_count,
            "info_count": info_count,
        },
        "findings": findings,
        "notes": notes,
    }


def write_outputs(root: Path, chapter: str, stage: str, report: dict[str, Any]) -> dict[str, str]:
    out_json = root / "生产数据" / f"comic_gate_{stage}_{chapter}.json"
    out_md = root / "生产数据" / f"comic_gate_{stage}_{chapter}.md"
    findings_path = root / "生产数据" / f"gate_findings_{stage}_{chapter}.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    findings_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "comic_gate_findings",
                "chapter": chapter,
                "stage": stage,
                "created_at": report.get("created_at"),
                "summary": report.get("summary"),
                "findings": report.get("findings") or [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_markdown(report, out_md)
    return {"json": rel(root, out_json), "markdown": rel(root, out_md), "findings": rel(root, findings_path)}


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report.get("summary") or {}
    lines = [
        f"# 漫画 Gate — {report.get('stage')} — {report.get('chapter')}",
        "",
        f"- 生成时间：{report.get('created_at')}",
        f"- 结论：{report.get('verdict')}",
        f"- block/warn/info：{summary.get('block_count', 0)} / {summary.get('warn_count', 0)} / {summary.get('info_count', 0)}",
    ]
    notes = report.get("notes") or []
    if notes:
        lines += ["", "## 记录", ""]
        lines.extend(f"- {note}" for note in notes)
    lines += ["", "## Findings", ""]
    findings = report.get("findings") or []
    if not findings:
        lines.append("- 未发现阻断或警告。")
    else:
        lines += ["| severity | code | artifact | reason | return_to | suggested_fix |", "|---|---|---|---|---|---|"]
        for item in findings:
            row = [
                item.get("severity", ""),
                item.get("code", ""),
                item.get("artifact", ""),
                item.get("reason", ""),
                item.get("return_to_stage", ""),
                item.get("suggested_fix", ""),
            ]
            lines.append("| " + " | ".join(str(value).replace("|", "\\|").replace("\n", " ") for value in row) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="漫画生产 gate")
    parser.add_argument("project_root")
    parser.add_argument("--chapter", default="第1话")
    parser.add_argument("--stage", choices=("image_preflight", "image", "compose", "review"), default="image_preflight")
    parser.add_argument("--no-refresh", action="store_true", help="不刷新 identity report；style/character 仍按当前图片重算")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    if args.stage == "image_preflight":
        run_image_preflight(root, args.chapter, findings, notes, no_refresh=args.no_refresh)
    elif args.stage == "image":
        run_image(root, args.chapter, findings, notes, no_refresh=args.no_refresh)
    elif args.stage == "compose":
        run_compose(root, args.chapter, findings, notes, no_refresh=args.no_refresh)
    else:
        run_review(root, args.chapter, findings, notes, no_refresh=args.no_refresh)

    report = make_report(root, args.chapter, args.stage, findings, notes)
    paths = write_outputs(root, args.chapter, args.stage, report)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        summary = report["summary"]
        print(f"[ok] {paths['json']}")
        print(f"[ok] {paths['markdown']}")
        print(f"verdict={report['verdict']} block={summary['block_count']} warn={summary['warn_count']} info={summary['info_count']}")
    return 1 if report["verdict"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
