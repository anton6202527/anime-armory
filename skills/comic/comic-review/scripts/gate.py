#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comic production gates.

Use this as the deterministic entry guard before paid image generation and
before handing images to compose/review.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import re
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
try:
    import scene_prop_consistency
except Exception:  # pragma: no cover
    scene_prop_consistency = None
try:
    import vlm_judge
except Exception:  # pragma: no cover
    vlm_judge = None

try:
    import continuity_audit
except Exception:  # pragma: no cover
    continuity_audit = None

COMIC_LIB = Path(__file__).resolve().parents[2] / "_lib"
if str(COMIC_LIB) not in sys.path:
    sys.path.insert(0, str(COMIC_LIB))
COMIC_IMAGE_SCRIPTS = Path(__file__).resolve().parents[2] / "comic-image" / "scripts"
if str(COMIC_IMAGE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(COMIC_IMAGE_SCRIPTS))
try:
    import codex_panel_runner as panel_acceptance
except Exception:  # pragma: no cover - missing validator must fail closed in check_panel_jobs_ready
    panel_acceptance = None
try:
    from image_backend_adapter import resolve_capabilities
except Exception:  # pragma: no cover
    resolve_capabilities = None
try:
    from comic_image_prompt_compiler import (
        KIND as IMAGE_PROMPT_COMPILER_KIND,
        VERSION as IMAGE_PROMPT_COMPILER_VERSION,
        lint as lint_image_submit_prompt,
        normalize_backend as normalize_image_prompt_backend,
    )
except Exception:  # pragma: no cover
    IMAGE_PROMPT_COMPILER_KIND = ""
    IMAGE_PROMPT_COMPILER_VERSION = 0
    lint_image_submit_prompt = None
    normalize_image_prompt_backend = None
try:
    from platform_profiles import profile_for_platform, validate_manifest as validate_platform_manifest
except Exception:  # pragma: no cover
    profile_for_platform = None
    validate_platform_manifest = None
try:
    from contracts import stage_inputs_fingerprint, stable_sha256
except Exception:  # pragma: no cover
    stage_inputs_fingerprint = None
    stable_sha256 = None
try:
    from settings import PRODUCTION_PROFILE_PRESETS
except Exception:  # pragma: no cover
    PRODUCTION_PROFILE_PRESETS = {}

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
SKILLS_ROOT = Path(__file__).resolve().parents[2]

DETERMINISTIC_EVIDENCE_FAMILIES = {
    "artifact_presence",
    "deterministic",
    "deterministic_state_contract",
    "generation_recipe",
    "human_acceptance",
    "reference_presence",
    "text_contract",
}
DETERMINISTIC_FINDING_CODES = {
    "character_panel_missing",
    "character_reference_missing",
    "panel_image_missing",
    "panel_image_unreadable",
    "scene_anchor_reference_missing",
    "prop_reference_missing",
}
DETERMINISTIC_REVIEW_CATEGORIES = {
    "export",
    "identity",
    "layout",
    "lettering",
    "missing_artifact",
    "script",
    "source",
}


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
    confidence: str = "deterministic",
) -> None:
    normalized_confidence = str(confidence or "deterministic").strip().lower()
    # Design-constitution B10: a heuristic may never masquerade as a hard
    # production stop.  Deterministic contract/receipt facts remain eligible
    # for BLOCK; aesthetic, keyword and uncalibrated numeric signals do not.
    if severity == "block" and normalized_confidence in {"heuristic", "advisory", "uncalibrated"}:
        severity = "warn"
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
            "confidence": normalized_confidence,
        }
    )


def finding_confidence(item: dict[str, Any], *, category: str = "") -> str:
    """Classify evidence before allowing a hard stop.

    Missing files, hashes and declared contracts are deterministic.  Pixel
    fingerprints, embeddings, keyword/aesthetic rules and model judgements
    remain heuristic even when their source report labels them ``block``.
    """
    explicit = str(item.get("confidence") or "").strip().lower()
    if explicit:
        return explicit
    family = str(item.get("evidence_family") or "").strip()
    code = str(item.get("code") or item.get("category") or "").strip()
    if family in DETERMINISTIC_EVIDENCE_FAMILIES or code in DETERMINISTIC_FINDING_CODES:
        return "deterministic"
    if category == "review" and code in DETERMINISTIC_REVIEW_CATEGORIES:
        return "deterministic"
    return "heuristic"


def command_tail(proc: subprocess.CompletedProcess[str], limit: int = 1800) -> str:
    return ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()[-limit:]


def run_contract_command(
    root: Path,
    chapter: str,
    findings: list[dict[str, Any]],
    notes: list[str],
    *,
    script: Path,
    arguments: list[str],
    code: str,
    artifact: str,
    return_to_stage: str,
    label: str,
) -> bool:
    if not script.is_file():
        add(
            findings,
            "block",
            f"{code}_tool_missing",
            rel(root, script),
            f"{label} 校验器缺失。",
            return_to_stage,
            "恢复本线校验脚本后重跑 gate。",
        )
        return False
    proc = subprocess.run(
        [sys.executable, str(script), *arguments],
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
            code,
            artifact,
            f"{label} 未通过：{command_tail(proc) or f'exit={proc.returncode}'}",
            return_to_stage,
            f"按 {label} 输出修复并重新签收后重跑 gate。",
        )
        return False
    notes.append(f"{label}: pass")
    return True


def check_production_profile(root: Path, findings: list[dict[str, Any]]) -> None:
    profile = read_setting(root, "生产档位", "").strip()
    if not profile:
        add(
            findings,
            "warn",
            "production_profile_missing",
            "_设置.md",
            "旧项目未声明生产档位；无法确认定妆、形态继承和一致性硬闸是否为一组自洽配置。",
            "settings",
            "用 comic-settings 显式设置 短篇验证/连载标准/连载高一致性/出版交付 之一。",
        )
        return
    expected = PRODUCTION_PROFILE_PRESETS.get(profile)
    if not isinstance(expected, dict):
        add(findings, "block", "production_profile_unknown", "_设置.md", f"未知生产档位：{profile}", "settings", "用 comic-settings 选择受支持档位。")
        return
    mismatches = []
    for key, value in expected.items():
        actual = read_setting(root, key, "").strip()
        if actual != value:
            mismatches.append(f"{key}={actual or '缺失'}（应为 {value}）")
    if mismatches:
        add(
            findings,
            "block",
            "production_profile_incoherent",
            "_设置.md",
            f"生产档位={profile}，但联动设置被拆散：" + "；".join(mismatches),
            "settings",
            f"重新执行 comic-settings set <作品根> 生产档位 {profile}，或切换到符合当前目标的档位。",
        )


def find_panel_image(root: Path, chapter: str, panel_id: str) -> Path | None:
    base = root / "出图" / chapter / "panels"
    for suffix in IMAGE_EXTS:
        path = base / f"{panel_id}{suffix}"
        if path.is_file():
            return path
    matches = sorted(base.glob(f"{panel_id}.*"))
    return next((item for item in matches if item.suffix.lower() in IMAGE_EXTS), None)


def load_raw_bubble_acceptance(root: Path, chapter: str) -> dict[str, dict[str, Any]]:
    path = root / "生产数据" / f"raw_bubble_acceptance_{chapter}.json"
    data = load_json(path, {})
    accepted: dict[str, dict[str, Any]] = {}
    if not isinstance(data, dict):
        return accepted
    for item in data.get("accepted_findings") or []:
        if not isinstance(item, dict):
            continue
        panel_id = str(item.get("panel_id") or "").strip()
        code = str(item.get("code") or "raw_bubble_candidate").strip()
        if panel_id and code in {"raw_bubble_candidate", "baked_blank_bubble_candidate"}:
            recorded_sha = str(item.get("artifact_sha256") or "").strip()
            panel_path = find_panel_image(root, chapter, panel_id)
            current_sha = hashlib.sha256(panel_path.read_bytes()).hexdigest() if panel_path else ""
            accepted_by = str(item.get("accepted_by") or data.get("accepted_by") or "").strip()
            reason = str(item.get("reason") or "").strip()
            authorized = bool(recorded_sha and recorded_sha == current_sha and accepted_by and reason)
            accepted[panel_id] = {
                "status": "accepted" if authorized else "legacy_unbound_or_stale",
                "authorized": authorized,
                "accepted_by": accepted_by,
                "accepted_at": str(item.get("accepted_at") or data.get("accepted_at") or ""),
                "reason": reason,
                "evidence": str(item.get("evidence") or ""),
                "artifact_sha256": recorded_sha,
                "source": rel(root, path),
            }
    for panel_id in data.get("accepted_panels") or []:
        pid = str(panel_id).strip()
        if pid and pid not in accepted:
            accepted[pid] = {
                "status": "legacy_unbound_or_stale",
                "authorized": False,
                "accepted_by": str(data.get("accepted_by") or ""),
                "accepted_at": str(data.get("accepted_at") or ""),
                "reason": "accepted by panel list",
                "evidence": "",
                "source": rel(root, path),
            }
    return accepted


def load_panel_post_qc_acceptance(root: Path, chapter: str) -> dict[str, dict[str, Any]]:
    """Return only current two-gate acceptances from the formal panel job/receipt pair.

    Legacy ``raw_bubble_acceptance`` records are disclosure evidence, not
    authorization for a panel to become production-ready.
    """
    accepted: dict[str, dict[str, Any]] = {}
    jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    jobs = load_json(jobs_path, {})
    if panel_acceptance is None or not isinstance(jobs, dict):
        return accepted
    for job in jobs.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        panel_id = str(job.get("panel_id") or "").strip()
        status = panel_acceptance.panel_acceptance_status(root, job)
        if not panel_id or not status.get("accepted"):
            continue
        data = job.get("post_qc") if isinstance(job.get("post_qc"), dict) else {}
        manual = data.get("manual_review") if isinstance(data.get("manual_review"), dict) else {}
        path = root / "生产数据" / "panel_qc" / chapter / f"{panel_id}.json"
        accepted[panel_id] = {
            "status": "accepted",
            "accepted_by": str(manual.get("reviewed_by") or ""),
            "accepted_at": str(manual.get("reviewed_at") or manual.get("accepted_at") or ""),
            "reason": str(manual.get("reason") or ""),
            "evidence": rel(root, path),
            "source": rel(root, path),
            "artifact_sha256": str(status.get("artifact_sha256") or ""),
            "disposition": str(status.get("disposition") or ""),
        }
    return accepted


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
    for binding in panel.get("character_bindings") or []:
        if not isinstance(binding, dict):
            continue
        for key in ("character_id", "form_id", "outfit_id", "expression_id", "state_id"):
            ref_id = str(binding.get(key) or "").strip()
            if ref_id and ref_id not in ids:
                ids.append(ref_id)
    for key in ("references", "characters"):
        for raw in panel.get(key) or []:
            ref_id = str(raw).strip()
            if ref_id and ref_id not in ids:
                ids.append(ref_id)
    return ids


def panel_has_character(panel: dict[str, Any]) -> bool:
    return bool(panel.get("characters")) or any(ref_id.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_")) for ref_id in panel_reference_ids(panel))


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
VAGUE_GAZE_PATTERN = re.compile(
    r"^(?:"
    r"(?:坚定|冷静|愤怒|悲伤|惊讶)(?:的)?(?:眼神|目光)?|"
    r"(?:眼神|目光)|"
    r"(?:看|望向|凝视)?(?:着|向)?(?:正)?(?:远方|前方|某处)|"
    r"none|n/a"
    r")$",
    re.I,
)
FACE_INTEGRITY_TERMS = ("脸", "五官", "眼", "眼型", "眼距", "发际线", "发型", "头发")
BODY_INTEGRITY_TERMS = ("手", "脚", "肢体", "身体", "腿", "手臂", "完整", "道具", "武器", "接触点")


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def camera_role_allows_direct_gaze(panel: dict[str, Any]) -> bool:
    return contains_any(compact_text(panel.get("camera_role")) + " " + compact_text(panel.get("pov")), POV_CAMERA_ROLE_TERMS)


def is_vague_gaze_target(value: str) -> bool:
    clauses = [
        clause.strip().lower()
        for clause in re.split(r"[；;，,。]+", value)
        if clause.strip()
    ]
    return any(VAGUE_GAZE_PATTERN.fullmatch(clause) for clause in clauses)


def is_weak_integrity_contract(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    return not (contains_any(text, FACE_INTEGRITY_TERMS) and contains_any(text, BODY_INTEGRITY_TERMS))


def visual_scene_anchors(visual_contract: dict[str, Any]) -> dict[str, Any]:
    anchors = visual_contract.get("scene_anchors") if isinstance(visual_contract.get("scene_anchors"), dict) else {}
    return anchors if isinstance(anchors, dict) else {}


def panel_character_refs(panel: dict[str, Any]) -> list[str]:
    return [ref_id for ref_id in panel_reference_ids(panel) if ref_id.startswith(("CHAR_", "MON_", "BEAST_", "ANIMAL_"))]


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
        # Multi-character staging is required for ANY 2+ character panel, scene
        # or not: a scene-less two-shot / floating-BG emotional beat can still
        # flip who is 画左/画右 or lose the occlusion order between panels.  This
        # used to sit inside `if panel_has_scene`, so those panels escaped it.
        if panel_character_count(panel) >= 2:
            scene_contract_for_staging = scene_contract_from(visual_contract, panel_scene_anchor_id(panel)) if panel_has_scene(panel) else {}
            if not contract_value(panel, scene_contract_for_staging, "spatial_relationships", "blocking", "staging"):
                add(
                    findings,
                    "block",
                    "panel_multi_character_staging_missing",
                    artifact,
                    f"{pid} 含多个角色但缺少人物左右/前后景/遮挡或轴线关系，容易造成跨格站位和视线漂移。",
                    "script",
                    "补 spatial_relationships/blocking/staging，写清谁在画左/画右、谁在前景/后景、遮挡和关键接触点。",
                )


def layout_is_single_column(layout: dict[str, Any]) -> bool:
    if layout.get("geometry_profile") == "longstrip_single_column":
        return True
    panels = [
        panel
        for segment in layout.get("segments") or []
        if isinstance(segment, dict)
        for panel in segment.get("panels") or []
        if isinstance(panel, dict)
    ]
    if not panels:
        return False
    xs = {int(panel.get("x") or 0) for panel in panels}
    if len(xs) > 1:
        return False
    width = int((layout.get("canvas") or {}).get("width") or 0)
    if not width:
        return True
    return all(int(panel.get("w") or 0) >= int(width * 0.7) for panel in panels)


def check_format_geometry(root: Path, chapter: str, layout: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    """页漫/四格选择点 vs layout 实际几何。

    deterministic build_layout 只会产单列条漫几何；选了页漫/四格却拿着单列
    layout 出图，最终交付物必然是一条竖条。必须在付费出图前拦下，
    由人工/agent 重排 layout（页内网格、RTL、分页）后再继续。
    """
    fmt = str(layout.get("format") or read_setting(root, "漫画形态", "条漫"))
    if not any(token in fmt for token in ("页漫", "四格")):
        return
    # Schema v2 is emitted by format-specific adapters and then independently
    # validated + approved.  Trust its declared geometry profile; the old
    # x/width heuristic below is only a migration fallback for legacy layouts.
    profile = str(layout.get("geometry_profile") or "")
    workflow_status = str(layout.get("workflow_status") or "")
    approval = layout.get("approval") if isinstance(layout.get("approval"), dict) else {}
    approved_v2 = (
        int(layout.get("schema_version") or 0) >= 2
        and workflow_status == "approved"
        and str(approval.get("status") or "") == "approved"
    )
    if approved_v2:
        if "页漫" in fmt and profile in {"paged_grid_ltr", "paged_grid_rtl"}:
            return
        if "四格" in fmt and profile == "yonkoma_four_rows":
            return
        add(
            findings,
            "block",
            "format_geometry_profile_mismatch",
            f"排版/{chapter}/layout.json",
            f"已审批 schema v2 layout 的 geometry_profile={profile or '缺失'} 与漫画形态={fmt} 不匹配。",
            "layout",
            "重新选用对应形态的 comic-layout 几何适配器，并重走 review/approved。",
        )
        return
    if layout_is_single_column(layout):
        add(
            findings,
            "block",
            "format_geometry_mismatch",
            f"排版/{chapter}/layout.json",
            f"漫画形态={fmt}，但 layout 是单列条漫几何，或 schema v2 geometry_profile={profile or '缺失'} 与形态不匹配。",
            "layout",
            "用 comic-layout 的对应几何适配器重建并审批 layout，或把 漫画形态 改回 条漫。",
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
            "传统原稿流程已启用，但缺少缩略分镜/name_board；页流、翻页钩子和格子轻重缺少 name board 层证据。",
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
    outfit_gaps = report.get("outfit_gaps") if isinstance(report.get("outfit_gaps"), dict) else {}
    if outfit_gaps:
        hard_gate_on = read_setting(root, "角色一致性硬闸", "关闭").strip() in {"开启", "on", "true"}
        add(
            findings,
            "block" if hard_gate_on else "warn",
            "outfit_registry_gaps",
            "生产数据/comic_identity_report.json",
            "换装格缺服装子注册或服装参考图：" + "；".join(f"{pid}: {reason}" for pid, reason in sorted(outfit_gaps.items())[:10]),
            "identity",
            "在 registry.assets[角色].outfits 登记该服装（描述+参考图+绝不清单）后重建出图包。",
        )
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


STYLE_ANCHOR_PLACEHOLDERS = {"未指定", "无", "待定", "暂无", "无固定锚", "none", "n/a", "tbd", "-", "未定"}


def effective_style_anchor(value: str) -> str:
    text = str(value or "").strip()
    return "" if text.lower() in STYLE_ANCHOR_PLACEHOLDERS else text


def check_style_contract(root: Path, findings: list[dict[str, Any]]) -> None:
    registry = load_json(root / "出图" / "共享" / "identity_registry.json", {})
    has_registry_style = isinstance(registry, dict) and bool(registry.get("style_contract") or registry.get("visual_style"))
    assets = registry.get("assets") if isinstance(registry, dict) and isinstance(registry.get("assets"), dict) else {}
    has_style_asset = any(str(key).startswith("STYLE_") for key in assets)
    style_anchor = effective_style_anchor(read_setting(root, "风格锚", ""))
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


def check_prompt_compiler(jobs: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    artifact = f"出图/{jobs.get('chapter', '')}/prompt/panel_jobs.json"
    if lint_image_submit_prompt is None or normalize_image_prompt_backend is None:
        add(findings, "block", "prompt_compiler_unavailable", artifact, "comic image prompt compiler 不可用。", "image", "修复 skills/comic/_lib/comic_image_prompt_compiler.py。")
        return
    if jobs.get("schema_version") != 2:
        add(findings, "block", "panel_jobs_schema_legacy", artifact, "panel_jobs 不是 compiler-aware schema v2。", "image", "重跑 comic-image/scripts/build_panel_jobs.py。")
    expected_backend = f"{jobs.get('model', '')} {jobs.get('channel', '')}"
    for job in jobs.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        pid = str(job.get("panel_id") or "unknown")
        compiler = job.get("prompt_compiler") if isinstance(job.get("prompt_compiler"), dict) else {}
        payload = {
            **compiler,
            "prompt": str(job.get("submit_prompt") or ""),
            "negative_prompt": str(job.get("negative_prompt") or ""),
            "source_contract_sha256": str(job.get("source_contract_sha256") or ""),
        }
        errors: list[str] = []
        warnings: list[str] = []
        if not job.get("production_contract_prompt") or not job.get("production_negative_contract"):
            errors.append("missing_full_production_contract")
        if job.get("prompt_source_kind") != "compiled_submit_prompt":
            errors.append("prompt_source_kind_invalid")
        if compiler.get("kind") != IMAGE_PROMPT_COMPILER_KIND or compiler.get("version") != IMAGE_PROMPT_COMPILER_VERSION:
            errors.append("prompt_compiler_incompatible")
        if str(job.get("prompt") or "") != str(job.get("submit_prompt") or ""):
            errors.append("prompt_alias_mismatch")
        source_hash = str(job.get("source_contract_sha256") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
            errors.append("source_contract_hash_invalid")
        submit = str(job.get("submit_prompt") or "")
        if str(job.get("submit_prompt_sha256") or "") != hashlib.sha256(submit.encode("utf-8")).hexdigest():
            errors.append("submit_prompt_hash_mismatch")
        if normalize_image_prompt_backend(compiler.get("backend")) != normalize_image_prompt_backend(expected_backend):
            errors.append("prompt_backend_mismatch")
        lint_result = lint_image_submit_prompt(payload)
        errors.extend(lint_result["errors"])
        warnings.extend(lint_result["warnings"])
        for code in errors:
            add(findings, "block", "compiled_prompt_invalid", artifact, f"{pid}: {code}", "image", "重建 panel_jobs；不要手改 compiler 块或把完整合同当提交 prompt。")
        for code in warnings:
            add(findings, "warn", "compiled_prompt_advisory", artifact, f"{pid}: {code}", "image", "精简本格可见画面描述后重建 panel_jobs。")


def check_panel_jobs_stale(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    """用当前 panel_script/finishing/registry 重编契约，比对已落盘出图包是否陈旧。"""
    script = SKILLS_ROOT / "comic-image" / "scripts" / "build_panel_jobs.py"
    jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    if not script.is_file() or not jobs_path.is_file():
        if not script.is_file():
            notes.append("comic-image build_panel_jobs.py 不可用，跳过出图包契约陈旧检测")
        return
    proc = subprocess.run(
        [sys.executable, str(script), str(root), "--chapter", chapter, "--check"],
        stdin=subprocess.DEVNULL,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result: dict[str, Any] = {}
    for line in reversed((proc.stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                result = json.loads(line)
            except json.JSONDecodeError:
                result = {}
            break
    artifact = f"出图/{chapter}/prompt/panel_jobs.json"
    if not result or result.get("kind") != "comic_panel_jobs_check":
        add(
            findings,
            "warn",
            "panel_jobs_stale_check_failed",
            artifact,
            "出图包契约陈旧检测未能运行：" + ((proc.stderr or proc.stdout or "no output").strip()[-600:]),
            "image",
            "修复 panel_script/layout 后重跑 build_panel_jobs.py --check。",
        )
        return
    error = str(result.get("error") or "")
    if error:
        add(
            findings,
            "block",
            "panel_jobs_stale_check_error",
            artifact,
            "出图包无法按当前契约重编：" + error,
            "image",
            "修复上游产物后重跑 comic-image/scripts/build_panel_jobs.py。",
        )
        return
    stale = [str(pid) for pid in result.get("stale_panels") or []]
    missing = [str(pid) for pid in result.get("missing_panels") or []]
    shifted = [str(pid) for pid in result.get("reference_shifted_panels") or []]
    if stale:
        add(
            findings,
            "block",
            "panel_jobs_stale_contract",
            artifact,
            "这些格的落盘出图包与当前脚本/收尾/风格契约不一致（改了契约没重建出图包）：" + "、".join(stale[:20]),
            "image",
            "重跑 comic-image/scripts/build_panel_jobs.py（陈旧格自动回 planned），再重抽这些格。",
        )
    if missing:
        add(
            findings,
            "block",
            "panel_jobs_missing_panels",
            artifact,
            "当前脚本包含但出图包缺失的格：" + "、".join(missing[:20]),
            "image",
            "重跑 comic-image/scripts/build_panel_jobs.py 补齐后再出图。",
        )
    if shifted:
        notes.append("参考图集合有扩充但提交 prompt 未变的格（不阻断，由 identity report 管理重抽）：" + "、".join(shifted[:20]))


def check_panel_jobs_ready(root: Path, chapter: str, jobs: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    post_qc_acceptance = load_panel_post_qc_acceptance(root, chapter)
    raw_bubble_disclosures = load_raw_bubble_acceptance(root, chapter)
    for job in jobs.get("jobs") or []:
        if not isinstance(job, dict):
            continue
        pid = str(job.get("panel_id") or "")
        status = str(job.get("status") or "")
        panel_path = find_panel_image(root, chapter, pid)
        generated_from = str(job.get("generated_from_submit_prompt_sha256") or "")
        raw_disclosure = raw_bubble_disclosures.get(pid)
        if raw_disclosure and not raw_disclosure.get("authorized"):
            add(
                findings,
                "warn",
                "legacy_raw_bubble_acceptance_unbound",
                str(raw_disclosure.get("source") or f"生产数据/raw_bubble_acceptance_{chapter}.json"),
                f"{pid} 的 legacy raw-bubble 签收缺当前像素 SHA、具名审核人/理由，或已随重抽失效；仅作披露，不能授权 ready。",
                "review",
                "改用当前 panel_qc comparison packet 完成逐图具名签收；不要沿用 accepted_panels 列表。",
                evidence_family="human_acceptance",
            )
        if status == "ready" and generated_from and generated_from != str(job.get("submit_prompt_sha256") or ""):
            add(
                findings,
                "block",
                "panel_generated_under_stale_contract",
                str(job.get("result_path") or f"出图/{chapter}/panels/{pid}.png"),
                f"{pid} 的成图是按旧提交契约生成的（generated_from_submit_prompt_sha256 与当前 submit_prompt_sha256 不一致）。",
                "image",
                "重跑 build_panel_jobs.py 后 force 重抽该格；不要手工把旧图改回 ready。",
            )
            continue
        generated_exec = str(job.get("generated_from_execution_input_sha256") or "")
        current_exec = str(job.get("execution_input_sha256") or "")
        if status == "ready" and generated_exec and current_exec and generated_exec != current_exec:
            add(
                findings,
                "block",
                "panel_generated_under_stale_reference_contract",
                str(job.get("result_path") or f"出图/{chapter}/panels/{pid}.png"),
                f"{pid} 的成图执行输入契约已过期（generated_from_execution_input_sha256 != 当前 execution_input_sha256）："
                "提交 prompt 文本没变，但参考图内容/结构化绑定/尺寸/panel_plan 变了却没重抽该格。",
                "image",
                "重跑 build_panel_jobs.py 后 force 重抽该格；submit_prompt 文本不含参考图 SHA，只靠它判过期会漏掉换参考图的改动。",
            )
            continue
        if status == "ready":
            acceptance_status = (
                panel_acceptance.panel_acceptance_status(root, job)
                if panel_acceptance is not None
                else {"accepted": False, "reason": "panel_acceptance_validator_unavailable"}
            )
            if not acceptance_status.get("accepted"):
                add(
                    findings,
                    "block",
                    "panel_ready_without_current_acceptance",
                    str(job.get("result_path") or f"出图/{chapter}/panels/{pid}.png"),
                    f"{pid} 虽标为 ready，但逐图双闸签收无效：{acceptance_status.get('reason')}。"
                    "手改 status/manual、重抽后复用旧签收、或比较参考变化都不能授权进入合成。",
                    "image",
                    "对当前像素重跑 post-QC，查看 SHA 绑定 comparison packet，并由具名审核人重新签收。",
                    evidence_family="human_acceptance",
                )
                continue
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
            acceptance = post_qc_acceptance.get(pid)
            if acceptance:
                add(
                    findings,
                    "info",
                    "panel_post_qc_warn",
                    str(job.get("result_path") or rel(root, panel_path)),
                    f"{pid} 的落盘 post_qc=warn 已人审签收为误报：" + str(acceptance.get("reason") or "计划内亮部/雾面/叙事道具"),
                    "review",
                    "若该格重抽或构图变化，需要重新复核 panel_qc。",
                    evidence_family="human_acceptance",
                )
                findings[-1]["machine_severity"] = "warn"
                findings[-1]["manual_acceptance"] = acceptance
            else:
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


def load_reference_bundle(root: Path, chapter: str, panel_id: str) -> dict[str, Any]:
    for dirname in ("dreamina_reference_bundles", "codex_reference_bundles"):
        bundle = load_json(root / "生产数据" / dirname / chapter / f"{panel_id}.json", None)
        if isinstance(bundle, dict):
            return bundle
    return {}


def executed_reference_ids(bundle: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for record in bundle.get("references") or []:
        if not isinstance(record, dict):
            continue
        rid = str(record.get("id") or "")
        if rid:
            ids.add(rid)
        for part in record.get("parts") or []:
            if isinstance(part, dict) and part.get("id"):
                ids.add(str(part["id"]))
    return ids


def check_reference_execution(root: Path, chapter: str, jobs: dict[str, Any], findings: list[dict[str, Any]]) -> None:
    """执行保真：声明的风格锚/绑定主体必须真实进入参考通道。

    证据是 runner 落盘的 reference bundle（确定性 JSON），不是像素判断。
    历史教训：--reference-limit 调低时风格锚按优先级被静默省略（只在
    bundle omitted 里披露），整话风格随之漂移；角色一致性硬闸开启时该
    省略必须显式处理，不能只留一行披露。
    """
    hard_gate_on = read_setting(root, "角色一致性硬闸", "关闭").strip() in {"开启", "on", "true"}
    for job in jobs.get("jobs") or []:
        if not isinstance(job, dict) or str(job.get("status") or "") != "ready":
            continue
        pid = str(job.get("panel_id") or "")
        declared_style_ids = {
            str(ref.get("id") or "")
            for ref in job.get("references") or []
            if isinstance(ref, dict) and str(ref.get("id") or "").startswith("STYLE_")
        }
        bound_subjects = {
            str(binding.get("character_id") or "")
            for binding in job.get("character_bindings") or []
            if isinstance(binding, dict) and str(binding.get("character_id") or "")
        }
        if not declared_style_ids and not bound_subjects:
            continue
        bundle = load_reference_bundle(root, chapter, pid)
        if not bundle:
            continue  # 旧后端或手工采纳格：无 bundle 不虚构结论
        executed = executed_reference_ids(bundle)
        missing_style = sorted(declared_style_ids - executed)
        if missing_style:
            add(
                findings,
                "block" if hard_gate_on else "warn",
                "style_anchor_not_executed",
                f"生产数据/*reference_bundles/{chapter}/{pid}.json",
                f"{pid} 声明了风格锚 {','.join(missing_style)}，但执行参考通道未附带（被附件上限省略，仅存文字契约）。",
                "image",
                "用多视图拼板释放槽位或提高 --reference-limit 后 force 重抽该格；风格锚必须占一个物理参考槽。",
                evidence_family="reference_presence",
            )
        missing_subjects = sorted(bound_subjects - executed)
        if missing_subjects:
            add(
                findings,
                "block" if hard_gate_on else "warn",
                "subject_anchor_not_executed",
                f"生产数据/*reference_bundles/{chapter}/{pid}.json",
                f"{pid} 绑定的主体 {','.join(missing_subjects)} 没有任何真实身份锚进入执行参考通道。",
                "image",
                "补定妆参考并 force 重抽；不要在无身份锚的情况下让模型自由发挥主体形象。",
                evidence_family="reference_presence",
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
            confidence=finding_confidence(item, category=category),
        )


def check_script_stage(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    paths = check_required(root, chapter, findings, ("settings", "panel_script"))
    check_production_profile(root, findings)
    run_contract_command(
        root,
        chapter,
        findings,
        notes,
        script=SKILLS_ROOT / "comic-script" / "scripts" / "development_pack.py",
        arguments=[str(root), "check", "--strict", "--json"],
        code="development_pack_not_approved",
        artifact="开发包/signoff.json",
        return_to_stage="script",
        label="开发包严格合同",
    )
    run_contract_command(
        root,
        chapter,
        findings,
        notes,
        script=SKILLS_ROOT / "comic-script" / "scripts" / "source_semantics_gate.py",
        arguments=[str(root), "--chapter", chapter],
        code="source_trace_missing_stale_or_incomplete",
        artifact=f"脚本/{chapter}/source_semantics.json",
        return_to_stage="script",
        label="源范围/SHA/逐格 coverage 合同",
    )
    panel_script = load_json(paths["panel_script"], {})
    if isinstance(panel_script, dict):
        check_source_semantics(root, chapter, panel_script, findings)
        check_panel_visual_contract(root, chapter, panel_script, findings)
    run_continuity_contract_audit(root, chapter, findings, notes)


def check_name_stage(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    path = root / "排版" / chapter / "name_board.json"
    run_contract_command(
        root,
        chapter,
        findings,
        notes,
        script=SKILLS_ROOT / "comic-name" / "scripts" / "build_name_board.py",
        arguments=[str(root), "--chapter", chapter, "--check", "--no-progress"],
        code="name_approval_missing_or_stale",
        artifact=rel(root, path),
        return_to_stage="name",
        label="缩略分镜/name board 审批合同",
    )


def check_layout_stage(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    path = root / "排版" / chapter / "layout.json"
    passed = run_contract_command(
        root,
        chapter,
        findings,
        notes,
        script=SKILLS_ROOT / "comic-layout" / "scripts" / "build_layout.py",
        arguments=[str(root), "--chapter", chapter, "--check", "--no-progress"],
        code="layout_approval_missing_or_stale",
        artifact=rel(root, path),
        return_to_stage="layout",
        label="排版审批合同",
    )
    if passed:
        layout = load_json(path, {})
        if isinstance(layout, dict):
            check_format_geometry(root, chapter, layout, findings)


def check_finishing_stage(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    if not traditional_workflow_enabled(root):
        notes.append("传统原稿流程关闭：finishing 合同不适用")
        return
    path = root / "出图" / chapter / "finishing" / "finishing_plan.json"
    run_contract_command(
        root,
        chapter,
        findings,
        notes,
        script=SKILLS_ROOT / "comic-finishing" / "scripts" / "build_finishing_plan.py",
        arguments=[str(root), "--chapter", chapter, "--check", "--no-progress"],
        code="finishing_contract_missing_or_stale",
        artifact=rel(root, path),
        return_to_stage="finishing",
        label="原稿收尾合同",
    )


def check_identity_registry_and_model_pack(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    run_contract_command(
        root,
        chapter,
        findings,
        notes,
        script=SKILLS_ROOT / "comic-identity" / "scripts" / "registry_v2.py",
        arguments=[str(root), "check", "--json"],
        code="identity_registry_v2_invalid",
        artifact="出图/共享/identity_registry.json",
        return_to_stage="identity",
        label="角色注册表 v2",
    )
    run_contract_command(
        root,
        chapter,
        findings,
        notes,
        script=SKILLS_ROOT / "comic-identity" / "scripts" / "model_pack.py",
        arguments=[str(root), "check", "--write", "--json"],
        code="model_pack_not_signed_off",
        artifact="生产数据/comic_model_pack_report.json",
        return_to_stage="identity",
        label="角色多视图技术齐套与人审签收",
    )


def run_script(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    check_script_stage(root, chapter, findings, notes)


def run_name(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    check_script_stage(root, chapter, findings, notes)
    check_name_stage(root, chapter, findings, notes)


def run_layout(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    check_script_stage(root, chapter, findings, notes)
    check_name_stage(root, chapter, findings, notes)
    check_layout_stage(root, chapter, findings, notes)


def run_finishing(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    check_script_stage(root, chapter, findings, notes)
    check_name_stage(root, chapter, findings, notes)
    check_layout_stage(root, chapter, findings, notes)
    check_finishing_stage(root, chapter, findings, notes)


def run_image_preflight(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    check_script_stage(root, chapter, findings, notes)
    check_name_stage(root, chapter, findings, notes)
    check_layout_stage(root, chapter, findings, notes)
    check_finishing_stage(root, chapter, findings, notes)
    paths = check_required(root, chapter, findings, ("settings", "panel_script", "layout", "panel_jobs"))
    panel_script = load_json(paths["panel_script"], {})
    if isinstance(panel_script, dict):
        check_source_semantics(root, chapter, panel_script, findings)
        check_panel_visual_contract(root, chapter, panel_script, findings)
    layout = load_json(paths["layout"], {})
    if isinstance(layout, dict) and layout:
        check_format_geometry(root, chapter, layout, findings)
    jobs = load_json(paths["panel_jobs"], {})
    if isinstance(jobs, dict):
        check_backend(root, jobs, findings, notes)
        check_prompt_compiler(jobs, findings)
    if paths["panel_script"].is_file() and paths["layout"].is_file():
        check_panel_jobs_stale(root, chapter, findings, notes)
    if isinstance(panel_script, dict) and isinstance(layout, dict) and isinstance(jobs, dict):
        check_traditional_manga_contract(root, chapter, panel_script, layout, jobs, findings)
    check_identity_registry_and_model_pack(root, chapter, findings, notes)
    report = refresh_identity_report(root, chapter, findings, no_refresh=no_refresh)
    check_identity(root, report, findings)
    check_style_contract(root, findings)
    check_consistency_strategy_support(root, findings)
    run_script_advisory_audits(root, chapter, findings, notes)
    run_reference_plan_advisory(root, chapter, findings, notes)


def run_continuity_contract_audit(
    root: Path,
    chapter: str,
    findings: list[dict[str, Any]],
    notes: list[str],
) -> None:
    """Merge declared cross-chapter state facts into the production gate.

    No image or language model inference happens here.  A BLOCK means the
    project's own entry/delta/exit facts contradict one another; legacy
    chapters without the new contract remain WARN until migrated.
    """
    if continuity_audit is None:
        notes.append("continuity_audit 模块不可用，跨话状态合同跳过")
        return
    try:
        report = continuity_audit.audit(root, through_chapter=chapter)
        continuity_audit.write_report(root, report)
    except Exception as exc:
        # A crash here must not silently drop the cross-chapter state contract.
        # It is a deterministic auditor whose contradictions are BLOCK-level, so
        # a failure to run is at least a WARN the human sees — never a swallowed
        # note that lets an unaudited chapter sail through the script gate.
        add(
            findings,
            "warn",
            "continuity_audit_unavailable",
            f"脚本/{chapter}/panel_script.json",
            f"跨话状态合同审计运行失败，无法确认 entry/continuity_delta/exit 一致性（{exc}）。",
            "script",
            "修复 continuity_audit 输入（chapter_contract/panel_script 结构）后重跑 comic-review gate --stage script。",
        )
        return
    for item in report.get("findings") or []:
        severity = str(item.get("severity") or "warn")
        add(
            findings,
            severity if severity in {"block", "warn", "info"} else "warn",
            str(item.get("code") or "continuity_contract"),
            str(item.get("artifact") or f"脚本/{chapter}/panel_script.json"),
            str(item.get("reason") or "跨话状态合同不一致。"),
            "script",
            str(item.get("suggested_fix") or "修正 entry_state/continuity_delta/exit_state。"),
            evidence_family="deterministic_state_contract",
        )
    summary = report.get("summary") or {}
    notes.append(
        f"continuity_audit: chapters={summary.get('chapters', 0)} "
        f"block={summary.get('block', 0)} warn={summary.get('warn', 0)}"
    )


def run_script_advisory_audits(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    """出图前的编剧层 advisory 机检（2026-07 标准审计·report-only 起步，误报校准后再议升 block）。

    - 分话节拍：首格开场钩/末格结尾钩/高潮位/格数带/全书拆分蓝图（chapter_beat_audit·comic-script）。
    - 追更再入：N≥2 话开场前情锚是否够、中段是否冒出未交代实体（reentry_context_audit·comic-script）。
    - 实体在场：画面文本提到已登记实体但该格未绑参考、entity_schedule 必在/禁入契约（entity_presence_audit·comic-script）。
    - 反向防瞎编：读者文本/画面描述出现源文没有、也无有账登记的专名/称谓（source_fabrication_audit·comic-script）。
    - 话内冗余：台词同义反复/事实复现/旁白硬转占比/构图重复计划（redundancy_audit·本目录）。
    - 去 AI 味：自陈情绪/旁白概括情绪/动机过度解释/信息直给/集级直白率（subtext_audit·本目录）。
    机检产物落 生产数据/，findings 以 warn/info 并入本 gate（must→warn：advisory 期不阻断付费）。
    审计脚本缺失/异常时留 note 不拦——advisory 层绝不制造假 block。"""
    import subprocess
    here = Path(__file__).resolve().parent
    audits = [
        ("chapter_beat_audit", here.parent.parent / "comic-script" / "scripts" / "chapter_beat_audit.py"),
        ("setup_payoff_ledger", here.parent.parent / "comic-script" / "scripts" / "setup_payoff_ledger.py"),
        ("reentry_context_audit", here.parent.parent / "comic-script" / "scripts" / "reentry_context_audit.py"),
        ("entity_presence_audit", here.parent.parent / "comic-script" / "scripts" / "entity_presence_audit.py"),
        ("source_fabrication_audit", here.parent.parent / "comic-script" / "scripts" / "source_fabrication_audit.py"),
        ("redundancy_audit", here / "redundancy_audit.py"),
        ("subtext_audit", here / "subtext_audit.py"),
    ]
    for name, script in audits:
        if not script.is_file():
            notes.append(f"{name} 脚本缺失，advisory 机检跳过")
            continue
        try:
            proc = subprocess.run([sys.executable, str(script), str(root), chapter, "--write", "--json"],
                                  capture_output=True, text=True, timeout=120)
            payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
        except Exception as exc:
            notes.append(f"{name} 运行失败（{exc}），advisory 机检跳过")
            continue
        for item in payload.get("findings") or []:
            sev = str(item.get("severity") or "warn")
            code = str(item.get("code") or name)
            # 显式 entity_schedule 违约不属 advisory：契约是作者明写的必在/禁入清单，
            # 违约=可复算的绑定集事实（deterministic_state_contract），与 continuity
            # 状态链同级，允许 block。子串命中类（mentioned_not_bound 等）仍按启发式降档。
            explicit_contract = code in {
                "required_entity_unbound",
                "forbidden_entity_bound",
                "presence_contract_conflict",
            }
            if explicit_contract and sev in ("must", "block", "warn"):
                add(findings, "block", code,
                    f"生产数据/{payload.get('kind') or name}_{chapter}.json",
                    str(item.get("message") or ""),
                    "comic-script",
                    "按显式 entity_schedule 契约补绑定或改排程后重跑 gate。",
                    evidence_family="deterministic_state_contract")
                continue
            add(findings,
                "warn" if sev in ("must", "block", "warn") else "info",
                code,
                f"生产数据/comic_{name}_{chapter}.json" if name == "redundancy_audit" else f"生产数据/{payload.get('kind') or name}_{chapter}.json",
                str(item.get("message") or ""),
                "comic-script",
                "按机检建议回 comic-script 修分话/分格后重跑。")
        notes.append(f"{name}: must={payload.get('summary', {}).get('must', payload.get('summary', {}).get('block', 0))} "
                     f"warn={payload.get('summary', {}).get('warn', 0)}（advisory·不阻断）")


def run_panel_variety_advisory(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    """出图后的面板构图重复机检（2026-07·"太相似=重复"反向告警·advisory 不阻断）。

    一致性检查全部只抓"太不同=漂移"；一屏多格里近重复构图是漫画特有穿帮，靠本检补盲区。
    脚本缺失/异常留 note 不拦。"""
    import subprocess
    script = Path(__file__).resolve().parent / "panel_variety.py"
    if not script.is_file():
        notes.append("panel_variety 脚本缺失，构图重复机检跳过")
        return
    try:
        proc = subprocess.run([sys.executable, str(script), str(root), chapter, "--write", "--json"],
                              capture_output=True, text=True, timeout=120)
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception as exc:
        notes.append(f"panel_variety 运行失败（{exc}），构图重复机检跳过")
        return
    for item in payload.get("findings") or []:
        add(findings, "warn", str(item.get("code") or "near_duplicate_panels"),
            f"生产数据/comic_panel_variety_{chapter}.json",
            str(item.get("message") or ""),
            "comic-image",
            "换景别/机位/前景遮挡重出其一，或回 comic-script 合并格。")
    s = payload.get("summary") or {}
    notes.append(f"panel_variety: panels={s.get('panels')} 近重复对={s.get('duplicate_pairs')}（advisory·不阻断）")


def run_reference_plan_advisory(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    """校验已落盘处方与当前输入严格同源；不在 gate 中改写上游。"""
    script = SKILLS_ROOT / "comic-image" / "scripts" / "reference_planner.py"
    plan_path = root / "生产数据" / f"comic_reference_plan_{chapter}.json"
    if not script.is_file():
        add(findings, "block", "reference_planner_missing", rel(root, script), "逐格参考合同校验器缺失。", "identity", "恢复 reference_planner.py。")
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(script), str(root), chapter, "--json"],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        fresh = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception as exc:
        add(findings, "block", "reference_plan_check_failed", rel(root, plan_path), f"参考处方重算失败：{exc}", "identity", "修复登记表/绑定后重跑。")
        return
    saved = load_json(plan_path, {})
    if not isinstance(saved, dict) or not saved:
        add(findings, "block", "reference_plan_missing", rel(root, plan_path), "缺少已落盘的逐格参考处方。", "identity", "重跑 comic-image 构建 panel_jobs，同时落盘参考处方。")
        return
    for key in ("inputs_fingerprint", "plan_sha256"):
        if str(saved.get(key) or "") != str(fresh.get(key) or ""):
            add(findings, "block", "reference_plan_stale", rel(root, plan_path), f"已落盘处方的 {key} 与当前输入不一致。", "identity", "重跑 comic-image 构建参考处方和 panel_jobs。")
    for item in fresh.get("findings") or []:
        sev = str(item.get("severity") or "warn")
        add(findings,
            "block" if sev == "block" else "warn" if sev == "warn" else "info",
            str(item.get("code") or "reference_plan"),
            f"生产数据/comic_reference_plan_{chapter}.json",
            str(item.get("message") or ""),
            "identity",
            "按处方补该角色缺的视图/表情/服装参考并重建出图包。",
            confidence="deterministic" if sev == "block" else "heuristic")
    s = fresh.get("summary") or {}
    notes.append(f"reference_planner: 含角色格 {s.get('panels_with_characters')} 需处理 "
                 f"{s.get('panels_needing_action')}；处方 SHA 已校验")


def run_drift_report_advisory(root: Path, findings: list[dict[str, Any]], notes: list[str]) -> None:
    """审查阶段·跨话角色漂移汇总（2026-07·治"靠人脑记第几话开始崩"·advisory 不阻断）。

    汇总各话 character_consistency 报告成逐角色×逐话时间线，标 first_bad_chapter 与跨话反复漂移。
    单话 gate 看不见跨话累积（Gap-Decay），这里补上。block/跨话反复漂移以 info 透出（不新增阻断，
    单话该拦的漂移已由 character_consistency 在 image 阶段拦过）。脚本缺失/异常留 note 不拦。"""
    import subprocess
    script = SKILLS_ROOT / "comic-identity" / "scripts" / "drift_report.py"
    if not script.is_file():
        notes.append("drift_report 脚本缺失，跨话漂移汇总跳过")
        return
    try:
        proc = subprocess.run([sys.executable, str(script), str(root), "--write", "--json"],
                              capture_output=True, text=True, timeout=120)
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception as exc:
        notes.append(f"drift_report 运行失败（{exc}），跨话漂移汇总跳过")
        return
    for row in payload.get("characters") or []:
        if row.get("recommendation") and (row.get("warn_or_block_chapters") or row.get("block_chapters")):
            add(findings, "info", "cross_chapter_drift",
                "生产数据/comic_identity_drift_report.json",
                f"{row['char_id']} 首崩 {row.get('first_bad_chapter')}：{row['recommendation']}",
                "identity",
                "看 comic_identity_drift_report 决定补参考/补服装/补专门定妆或换后端。")
    s = payload.get("summary") or {}
    notes.append(f"drift_report: 追踪 {s.get('characters_tracked')} 角色 · 有漂移 "
                 f"{s.get('characters_with_drift')}（跨话汇总·advisory）")


def check_consistency_strategy_support(root: Path, findings: list[dict[str, Any]]) -> None:
    strategy = read_setting(root, "参考一致性策略", "共享参考图")
    if any(token in strategy for token in ("主体库", "LoRA", "lora")) and "共享参考图" not in strategy:
        add(
            findings,
            "warn",
            "consistency_strategy_unimplemented",
            "_设置.md",
            f"参考一致性策略={strategy}：漫画线暂无主体库/LoRA 执行实现，当前按共享参考图口径降级执行。",
            "identity",
            "接受降级则改回 共享参考图；坚持 LoRA 需在本线外训练，并把产出图登记为 registry 参考后照常走共享参考流程。",
        )


def check_machine_audit_liveness(root: Path, chapter: str, char_report: dict[str, Any], findings: list[dict[str, Any]], notes: list[str]) -> None:
    """机检空转显式化（2026-07-17 P015 虎妖漏放整改）。

    第1话实证：VLM 任务包生成 93 条、0 条裁决，CCIP 未装只剩色彩代理指纹，
    character_consistency 仍 verdict=pass 0 findings——四足虎放行无任何告警。
    审计引擎降级/裁决未执行必须出 finding，不准降级成 notes 静默过闸。
    """
    caps = char_report.get("capabilities") if isinstance(char_report.get("capabilities"), dict) else {}
    if vlm_judge is None:
        if not caps.get("ccip"):
            add(findings, "warn", "identity_similarity_engine_degraded", f"生产数据/comic_character_consistency_{chapter}.json", "CCIP 动漫身份 embedding 不可用，且 VLM 并排判定模块也不可用。", "review", "安装 dghs-imgutils 或恢复 VLM 并排裁决。")
        add(findings, "warn", "vlm_judge_module_missing", "skills/comic/comic-review/scripts/vlm_judge.py", "VLM 并排判定模块不可用，三轴身份机检缺失。", "review", "恢复 vlm_judge.py 后重跑 gate。")
        return
    try:
        status = vlm_judge.judge_status(root, chapter)
    except Exception as exc:  # pragma: no cover - 状态读取失败按空转告警
        add(findings, "warn", "vlm_judge_status_unreadable", f"生产数据/comic_vlm_judge_tasks_{chapter}.json", f"无法读取 VLM 裁决状态：{exc}", "review", "检查任务包/裁决文件后重跑 gate。")
        return
    task_count = int(status.get("task_count") or 0)
    verdict_count = int(status.get("verdict_count") or 0)
    if not caps.get("ccip"):
        fallback_complete = bool(task_count and verdict_count == task_count)
        add(
            findings,
            "info" if fallback_complete else "warn",
            "identity_similarity_engine_degraded",
            f"生产数据/comic_character_consistency_{chapter}.json",
            (
                "CCIP 动漫身份 embedding 不可用；VLM 三轴并排裁决已完整覆盖，已按规定完成身份轴兜底。"
                if fallback_complete
                else "CCIP 动漫身份 embedding 不可用，角色/生物相似度机检降级为色彩分布代理（同色调换脸/变形会漏报）。"
            ),
            "review",
            (
                "保留当前 VLM 裁决证据；后续环境具备 dghs-imgutils 时可补跑 CCIP。"
                if fallback_complete
                else "独立 venv 安装 dghs-imgutils 后重跑 gate；在装好前必须以 VLM 并排裁决兜底身份轴。"
            ),
            evidence_family="vlm_judge_fallback" if fallback_complete else "capability_degraded",
        )
    hard_gate_on = read_setting(root, "角色一致性硬闸", "关闭").strip() in {"开启", "on", "true"}
    by_axis = status.get("by_axis") if isinstance(status.get("by_axis"), dict) else {}
    # 无适配判定引擎兜底的轴（场景/背景/道具/生物形态）：CCIP 只覆盖角色身份 embedding，
    # 覆盖不到这些轴。这些轴一旦 0 裁决就是**完全空转**——无论 CCIP 装没装。
    # 聊斋实证：硬闸=开启、CCIP=已装，却因旧逻辑 fully_blind 要求「CCIP 未装」而只 warn，
    # 结果 background/location/prop 14+ 条 0 裁决照样过闸，「背景该是虎妖画成别的生物」漏放。
    fallback_axes = getattr(vlm_judge, "AXES_WITHOUT_DETERMINISTIC_FALLBACK",
                            ("location_identity", "background_continuity", "prop_identity"))
    blind_axes = [
        axis for axis in fallback_axes
        if int((by_axis.get(axis) or {}).get("task_count") or 0) > 0
        and int((by_axis.get(axis) or {}).get("verdict_count") or 0) == 0
    ]
    if task_count and verdict_count == 0:
        # 确定性升闸（全是可复算事实，非启发式）：一致性硬闸开启且存在任一「无引擎兜底轴」0 裁决，
        # 或角色轴在 CCIP 未装时也 0 裁决 —— 身份机检空转，必须显式裁决或显式豁免。
        char_axis_blind = hard_gate_on and not caps.get("ccip")
        must_block = hard_gate_on and (bool(blind_axes) or char_axis_blind)
        reason = f"VLM 并排判定任务包已生成 {task_count} 条但 0 条裁决——角色/生物身份、场景、背景、道具四轴机检空转，画错生物形态/画错场景/换道具这类漂移不会被拦。"
        if must_block:
            detail = "、".join(blind_axes) if blind_axes else "character_identity"
            reason += f"（角色一致性硬闸=开启：{detail} 轴无判定引擎兜底且 0 裁决，升级为 block。CCIP 覆盖不到场景/背景/道具/生物形态。）"
        add(
            findings,
            "block" if must_block else "warn",
            "vlm_judge_unadjudicated",
            str(status.get("tasks_file") or ""),
            reason,
            "review",
            f"用 vlm_adjudicate.py queue 出队、由多模态 agent 看图打分后 submit 回写 {status.get('verdict_file')}；"
            "场景/背景/道具轴无 CCIP 兜底，只能靠并排裁决。",
        )
    elif hard_gate_on and blind_axes:
        # 部分覆盖但恰好把「无引擎兜底轴」整轴漏了：角色轴有 CCIP 兜底看着覆盖过半，
        # 但场景/背景/道具轴一条没裁决，仍是这些轴完全空转。硬闸下 block。
        add(
            findings,
            "block",
            "vlm_judge_axis_blind",
            str(status.get("tasks_file") or ""),
            f"VLM 裁决覆盖 {verdict_count}/{task_count}，但 {('、'.join(blind_axes))} 轴 0 裁决——这些轴无 CCIP/指纹兜底，画错场景/背景漂移/换道具不会被拦。",
            "review",
            f"补齐上述轴的并排裁决写回 {status.get('verdict_file')} 后重跑 gate。",
        )
    elif task_count and verdict_count < task_count:
        add(
            findings,
            "warn",
            "vlm_judge_partial_coverage",
            str(status.get("tasks_file") or ""),
            f"VLM 并排判定仅覆盖 {verdict_count}/{task_count} 条任务，未裁决格仍无身份保障。",
            "review",
            f"补齐剩余裁决写回 {status.get('verdict_file')} 后重跑 gate。",
        )
    else:
        notes.append(f"vlm judge coverage: {verdict_count}/{task_count}")


def run_image(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_image_preflight(root, chapter, findings, notes, no_refresh=no_refresh)
    jobs = load_json(root / "出图" / chapter / "prompt" / "panel_jobs.json", {})
    if isinstance(jobs, dict):
        check_panel_jobs_ready(root, chapter, jobs, findings)
        check_reference_execution(root, chapter, jobs, findings)
    run_panel_variety_advisory(root, chapter, findings, notes)
    if style_consistency is None or character_consistency is None:
        add(findings, "block", "consistency_module_unavailable", "skills/comic/comic-review/scripts", f"一致性模块不可用：{IMPORT_ERROR}", "review", "修复 comic-review 模块导入。")
        return
    style_report = style_consistency.analyze(root, chapter)
    style_paths = style_consistency.write_outputs(root, chapter, style_report)
    notes.append(f"style consistency refreshed: {style_paths['markdown']}")
    merge_consistency_report(style_report, findings, category="style_consistency")
    char_report = character_consistency.analyze(root, chapter)
    char_paths = character_consistency.write_outputs(root, chapter, char_report)
    notes.append(f"character consistency refreshed: {char_paths['markdown']}")
    merge_consistency_report(char_report, findings, category="character_consistency")
    check_machine_audit_liveness(root, chapter, char_report, findings, notes)
    if scene_prop_consistency is not None:
        scene_report = scene_prop_consistency.analyze(root, chapter)
        scene_paths = scene_prop_consistency.write_outputs(root, chapter, scene_report)
        notes.append(f"scene/prop consistency refreshed: {scene_paths['markdown']}")
        merge_consistency_report(scene_report, findings, category="scene_prop_consistency")


def run_compose(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_image(root, chapter, findings, notes, no_refresh=no_refresh)
    paths = check_required(root, chapter, findings, ("lettering", "manifest"))
    run_lettering_contract_check(root, chapter, findings, notes)
    manifest = load_json(paths["manifest"], {})
    if isinstance(manifest, dict):
        if manifest.get("missing_panels"):
            add(findings, "block", "manifest_missing_panels", rel(root, paths["manifest"]), "export_manifest 仍记录缺图。", "compose", "补图并重新导出。")
        if not manifest.get("rendered"):
            add(findings, "block", "manifest_not_rendered", rel(root, paths["manifest"]), "尚未登记实际渲染导出物。", "compose", "运行 export_longstrip.py --render。")
        if paths["lettering"].is_file():
            current_lettering_sha256 = hashlib.sha256(paths["lettering"].read_bytes()).hexdigest()
            if str(manifest.get("lettering_sha256") or "") != current_lettering_sha256:
                add(
                    findings,
                    "block",
                    "manifest_lettering_stale",
                    rel(root, paths["manifest"]),
                    "export_manifest 未绑定当前 lettering.json；脚本/翻译/人工改写重建后，旧渲染物不能重新验收。",
                    "compose",
                    "按当前 lettering.json 重跑 export_longstrip.py --render，并复核导出物。",
                    evidence_family="text_contract",
                )
        check_manifest_profile(root, chapter, manifest, findings)
    run_lettering_geometry_qc(root, chapter, findings, notes)


def run_lettering_contract_check(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    """Require lettering to prove current upstream text and translation lineage."""

    script = SKILLS_ROOT / "comic-compose" / "scripts" / "lettering_contract.py"
    if not script.is_file():
        add(
            findings,
            "block",
            "lettering_contract_checker_missing",
            rel(root, script),
            "lettering 版本合同检查器缺失，无法证明脚本改动已传播到嵌字。",
            "compose",
            "恢复 comic-compose/scripts/lettering_contract.py 后重跑 gate。",
            evidence_family="text_contract",
        )
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(script), str(root), chapter, "--json", "--write"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception as exc:
        add(
            findings,
            "block",
            "lettering_contract_check_failed",
            rel(root, script),
            f"lettering 版本合同检查器运行失败：{exc}",
            "compose",
            "修复检查器或输入 JSON 后重跑 gate；不得跳过文本版本核验。",
            evidence_family="text_contract",
        )
        return
    if not isinstance(payload, dict) or not isinstance(payload.get("findings"), list):
        add(
            findings,
            "block",
            "lettering_contract_check_invalid_output",
            rel(root, script),
            "lettering 版本合同检查器未返回可解析 findings。",
            "compose",
            "修复检查器后重跑 gate。",
            evidence_family="text_contract",
        )
        return
    notes.append(
        "lettering contract: "
        f"verdict={payload.get('verdict')} block={(payload.get('summary') or {}).get('block', 0)} "
        f"warn={(payload.get('summary') or {}).get('warn', 0)}"
    )
    for item in payload.get("findings") or []:
        add(
            findings,
            str(item.get("severity") or "block"),
            str(item.get("code") or "lettering_contract"),
            str(item.get("artifact") or f"排版/{chapter}/lettering.json"),
            str(item.get("reason") or "lettering 版本合同未通过。"),
            "compose",
            str(item.get("suggested_fix") or "重跑 build_lettering.py 与 export_longstrip.py。"),
            evidence_family="text_contract",
        )


def run_lettering_geometry_qc(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str]) -> None:
    """嵌字几何 QC：槽位坐标层面的确定性检查（comic-compose lettering_qc.py）。

    越界=渲染必然裁字 → block（坐标事实，可复算）；贴边/遮挡/密度/字号 → warn。
    脚本缺失/异常留 note 不拦（advisory-runner 同款容错，不制造假 block）。
    """
    import subprocess
    script = SKILLS_ROOT / "comic-compose" / "scripts" / "lettering_qc.py"
    if not script.is_file():
        notes.append("lettering_qc 脚本缺失，嵌字几何 QC 跳过")
        return
    try:
        proc = subprocess.run(
            [sys.executable, str(script), str(root), chapter, "--json", "--write"],
            capture_output=True, text=True, timeout=120,
        )
        payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except Exception as exc:
        notes.append(f"lettering_qc 运行失败（{exc}），嵌字几何 QC 跳过")
        return
    for note in payload.get("notes") or []:
        notes.append(f"lettering_qc: {note}")
    for item in payload.get("findings") or []:
        severity = str(item.get("severity") or "warn")
        add(
            findings,
            "block" if severity == "block" and str(item.get("code")) == "lettering_out_of_canvas" else "warn",
            str(item.get("code") or "lettering_geometry"),
            f"排版/{chapter}/lettering.json",
            str(item.get("reason") or ""),
            "compose",
            str(item.get("suggested_fix") or "修正槽位几何后重跑 build_lettering.py 与导出。"),
            evidence_family="deterministic",
        )


def run_review(root: Path, chapter: str, findings: list[dict[str, Any]], notes: list[str], *, no_refresh: bool) -> None:
    run_compose(root, chapter, findings, notes, no_refresh=no_refresh)
    if review_module is None:
        add(findings, "block", "review_module_unavailable", "skills/comic/comic-review/scripts/review.py", f"review 模块不可用：{IMPORT_ERROR}", "review", "修复 review.py 后重跑 gate。")
        return
    report = review_module.review(root, chapter, refresh_qa_preview=True)
    notes.append("comic-review report refreshed in review gate")
    run_drift_report_advisory(root, findings, notes)
    for issue in report.get("issues") or []:
        issue_record = dict(issue)
        issue_record.setdefault("code", issue.get("category"))
        add(
            findings,
            str(issue.get("severity") or "warn"),
            str(issue.get("category") or "review_issue"),
            str(issue.get("artifact") or ""),
            str(issue.get("reason") or ""),
            str(issue.get("return_to") or "review"),
            str(issue.get("suggested_fix") or "按 comic-review 报告处理。"),
            evidence_family=str(issue.get("evidence_family") or issue.get("category") or "review"),
            confidence=finding_confidence(issue_record, category="review"),
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
    inputs_fingerprint = (
        stage_inputs_fingerprint(root, chapter, stage)
        if stage_inputs_fingerprint is not None
        else {"kind": "comic_inputs_fingerprint", "version": 1, "files": [], "sha256": ""}
    )
    report = {
        "schema_version": 2,
        "kind": "comic_gate",
        "project_root": ".",
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
        "inputs_fingerprint": inputs_fingerprint,
    }
    if stable_sha256 is not None:
        report["receipt_id"] = stable_sha256(
            {
                "project_root": ".",
                "chapter": chapter,
                "stage": stage,
                "inputs": inputs_fingerprint.get("sha256"),
                "verdict": report["verdict"],
                "findings": findings,
            }
        )
    return report


def write_outputs(root: Path, chapter: str, stage: str, report: dict[str, Any]) -> dict[str, str]:
    out_json = root / "生产数据" / f"comic_gate_{stage}_{chapter}.json"
    out_md = root / "生产数据" / f"comic_gate_{stage}_{chapter}.md"
    findings_path = root / "生产数据" / f"gate_findings_{stage}_{chapter}.json"
    receipt_path = root / "生产数据" / "gate_receipts" / f"{stage}_{chapter}.json"
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
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    jobs_path = root / "出图" / chapter / "prompt" / "panel_jobs.json"
    panel_jobs_sha256 = hashlib.sha256(jobs_path.read_bytes()).hexdigest() if jobs_path.is_file() else ""
    receipt_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "comic_gate_receipt",
                "receipt_id": report.get("receipt_id", ""),
                "chapter": chapter,
                "stage": stage,
                "created_at": report.get("created_at"),
                "verdict": report.get("verdict"),
                "execution_authorized": report.get("verdict") != "block",
                "inputs_fingerprint_sha256": (report.get("inputs_fingerprint") or {}).get("sha256", ""),
                "panel_jobs_sha256": panel_jobs_sha256,
                "artifacts": {
                    "panel_jobs_path": rel(root, jobs_path),
                    "panel_jobs_sha256": panel_jobs_sha256,
                },
                "report_path": rel(root, out_json),
                "report_sha256": hashlib.sha256(out_json.read_bytes()).hexdigest(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "json": rel(root, out_json),
        "markdown": rel(root, out_md),
        "findings": rel(root, findings_path),
        "receipt": rel(root, receipt_path),
    }


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
    parser.add_argument(
        "--stage",
        choices=("script", "name", "layout", "finishing", "image_preflight", "image", "compose", "review"),
        default="image_preflight",
    )
    parser.add_argument("--no-refresh", action="store_true", help="不刷新 identity report；style/character 仍按当前图片重算")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root).expanduser().resolve()
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    if args.stage == "script":
        run_script(root, args.chapter, findings, notes)
    elif args.stage == "name":
        run_name(root, args.chapter, findings, notes)
    elif args.stage == "layout":
        run_layout(root, args.chapter, findings, notes)
    elif args.stage == "finishing":
        run_finishing(root, args.chapter, findings, notes)
    elif args.stage == "image_preflight":
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
