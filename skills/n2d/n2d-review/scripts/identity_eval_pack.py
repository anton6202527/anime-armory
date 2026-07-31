#!/usr/bin/env python3
"""Build a fail-closed identity-evaluation pack from per-view review receipts.

The writer deliberately does not run an uncalibrated face heuristic and call it
truth.  It promotes only structured pixel-review receipts that are bound to the
current character/form/tier/view/path/PNG hash.  Human signoff remains the
default.  An explicitly authorized executor visual review is accepted as a
separate, non-human evidence kind and can never masquerade as human signoff.
``production_consistency.py`` then independently rechecks the emitted artifact,
project authorization, reviewer role, and registry fingerprint.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

COMMON = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "_lib"))
if COMMON not in sys.path:
    sys.path.insert(0, COMMON)

from n2d_contract import (  # noqa: E402
    CHARACTER_LIBRARY_TIER_CORE,
    IDENTITY_EXPRESSION_REQUIRED_CRITERIA,
    IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND,
    IDENTITY_TURNAROUND_REQUIRED_CRITERIA,
    character_library_tier_for_record,
    identity_review_binding_fingerprint,
    identity_review_contract_for_view,
    identity_review_required_criteria,
    identity_reviewed_at_errors,
    identity_reviewer_appears_automated,
    required_character_library_views,
)
from image_evidence import (  # noqa: E402
    PNG_DECODED_PIXEL_FINGERPRINT_KIND,
    png_decoded_pixel_fingerprint,
    png_evidence_errors,
)


PACK_KIND = "n2d_identity_eval_pack"
PACK_VERSION = 3
VIEW_REVIEW_CONTRACTS = {
    "n2d_turnaround_view_review_v1",
    "n2d_expression_review_v1",
}
# Backward-compatible public aliases used by fixtures and external callers.
REQUIRED_CRITERIA = set(IDENTITY_TURNAROUND_REQUIRED_CRITERIA)
EXPRESSION_REQUIRED_CRITERIA = set(IDENTITY_EXPRESSION_REQUIRED_CRITERIA)
REVIEWABLE_VIEWS = tuple(required_character_library_views(CHARACTER_LIBRARY_TIER_CORE)) + (
    "turnaround",
    "expression",
)
BINDING_FINGERPRINT_KIND = IDENTITY_REVIEW_BINDING_FINGERPRINT_KIND
REVIEWABLE_NODE_STATUSES = {"ready", "registered", "review_pending", "review_failed"}


class ReceiptError(ValueError):
    """The requested pixel-review receipt is unsafe or does not bind exactly."""


def _load_json(path: str) -> Any:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _sha256(path: str) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def _png_container_errors(path: str) -> List[str]:
    # Includes ``not_valid_png_container`` plus CRC/IDAT/scanline checks.
    return png_evidence_errors(path)


def _looks_absolute_path(value: str) -> bool:
    """Recognize native plus Windows absolute paths even when running on macOS."""
    path = str(value or "").strip()
    return bool(
        os.path.isabs(path)
        or (len(path) >= 3 and path[1] == ":" and path[2] in {"/", "\\"})
        or path.startswith("\\\\")
    )


def _resolve_project_evidence_path(root: str, value: str) -> Tuple[str, str, List[str]]:
    """Return canonical project-relative path + realpath, never escaping root."""
    raw = str(value or "").strip()
    if not raw:
        return "", "", ["path_missing"]
    if "\x00" in raw:
        return "", "", ["path_invalid_nul"]
    if _looks_absolute_path(raw):
        return "", "", ["absolute_registry_evidence_path_not_allowed"]
    root_real = os.path.realpath(os.path.abspath(root))
    resolved = os.path.realpath(os.path.join(root_real, raw))
    try:
        if os.path.commonpath((root_real, resolved)) != root_real:
            return "", "", ["registry_evidence_path_outside_project_root"]
    except ValueError:
        return "", "", ["registry_evidence_path_outside_project_root"]
    normalized = os.path.relpath(resolved, root_real).replace(os.sep, "/")
    if normalized in {"", "."} or normalized == ".." or normalized.startswith("../"):
        return "", "", ["registry_evidence_path_outside_project_root"]
    return normalized, resolved, []


def _review_contract(view: str) -> str:
    return identity_review_contract_for_view(view)


def _required_criteria(view: str) -> set[str]:
    return set(identity_review_required_criteria(view))


def _reviewer_is_automated(value: str) -> bool:
    return identity_reviewer_appears_automated(value)


def _normalized_reviewed_at(value: str = "") -> str:
    reviewed_at = str(value or "").strip()
    if not reviewed_at:
        return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    try:
        parsed = dt.datetime.fromisoformat(reviewed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReceiptError("reviewed_at 必须是 ISO-8601 时间") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReceiptError("reviewed_at 必须包含时区")
    return reviewed_at


def _reviewed_at_errors(value: Any) -> List[str]:
    return list(identity_reviewed_at_errors(value))


def registry_path(root: str) -> str:
    return os.path.join(root, "出图", "共享", "identity_registry.json")


def binding_fingerprint(
    *,
    character_id: str,
    form: str,
    library_tier: str,
    view: str,
    path: str,
    png_sha256: str,
) -> str:
    return identity_review_binding_fingerprint(
        character_id=character_id,
        form=form,
        library_tier=library_tier,
        view=view,
        path=path,
        png_sha256=png_sha256,
    )


def _reference_path(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        return str(value.get("path") or "").strip()
    return ""


def executor_visual_review_authorized(root: str) -> bool:
    """Mirror n2d-image's explicit project authorization without cross-skill imports."""
    path = os.path.join(root, "_设置.md")
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return False
    return (
        "执行者实际像素目视" in text
        and ("用户明确" in text or "source=explicit_user" in text)
    )


def _review_receipt(root: str, value: Any) -> Tuple[str, Mapping[str, Any]]:
    """Select a current structured receipt while preserving its real reviewer class."""
    if not isinstance(value, Mapping):
        return "", {}
    human = value.get("human_review") if isinstance(value.get("human_review"), Mapping) else {}
    visual = value.get("visual_review") if isinstance(value.get("visual_review"), Mapping) else {}

    def accepted(review: Mapping[str, Any]) -> bool:
        return (
            str(review.get("status") or "").strip().lower() == "accepted"
            and str(review.get("verdict") or "").strip().lower() == "pass"
        )

    if accepted(human):
        return "human", human
    if accepted(visual):
        return "executor_visual", visual
    if human:
        return "human", human
    if visual:
        return "executor_visual", visual
    return "", {}


def _view_node(form: Mapping[str, Any], view: str) -> Any:
    group = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    base = atlas.get("base_views") if isinstance(atlas.get("base_views"), Mapping) else {}
    return group.get(view) if group.get(view) not in (None, "", [], {}) else base.get(view)


def _expression_nodes(form: Mapping[str, Any]) -> List[Any]:
    group = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    values: List[Any] = []
    seen: set[int] = set()

    def collect(value: Any) -> None:
        if isinstance(value, Mapping):
            marker = id(value)
            if marker in seen:
                return
            seen.add(marker)
            if _reference_path(value):
                values.append(value)
                return
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str) and value.strip():
            # A bare path remains fail-closed because it cannot carry status or
            # a bound receipt, but surfacing it yields an actionable bucket.
            values.append(value)

    for raw in (
        group.get("expressions"),
        group.get("face_anchor_refs"),
        atlas.get("expression_refs"),
        atlas.get("face_anchor_refs"),
    ):
        collect(raw)
    return values


def _review_errors(
    root: str,
    node: Any,
    *,
    character_id: str,
    form_name: str,
    tier: str,
    view: str,
) -> Tuple[List[str], str, str, str, Mapping[str, Any]]:
    raw_rel = _reference_path(node)
    review_kind, review = _review_receipt(root, node)
    errors: List[str] = []
    node_status = (
        str(node.get("status") or "").strip().lower()
        if isinstance(node, Mapping)
        else ""
    )
    # A receipt left behind on a node that has since been reset to planned must
    # not resurrect that view.  The registry node state is part of the current
    # truth, independent of the historical human-review object.
    if node_status not in {"ready", "registered"}:
        errors.append(f"registry_node_status={node_status or 'missing'}")
    if not raw_rel:
        errors.append("path_missing")
        return sorted(set(errors)), "", "", "", review
    rel, path, path_errors = _resolve_project_evidence_path(root, raw_rel)
    errors.extend(path_errors)
    if not path_errors and raw_rel.replace("\\", "/") != rel:
        errors.append("registry_evidence_path_not_canonical_project_relative")
    actual_sha = ""
    decoded_pixel_fingerprint = ""
    if not path_errors:
        actual_sha = _sha256(path)
        if not actual_sha:
            errors.append("path_not_found_or_unreadable")
        else:
            png_errors = _png_container_errors(path)
            errors.extend(png_errors)
            if not png_errors:
                decoded_pixel_fingerprint, fingerprint_errors = png_decoded_pixel_fingerprint(path)
                errors.extend(fingerprint_errors)
                if not decoded_pixel_fingerprint and not fingerprint_errors:
                    errors.append("png_pixel_fingerprint_unavailable")
    if not review:
        errors.append("structured_pixel_review_missing")
        return errors, rel, actual_sha, decoded_pixel_fingerprint, review
    if str(review.get("status") or "").strip().lower() != "accepted":
        errors.append(f"review_status={review.get('status') or 'missing'}")
    if str(review.get("verdict") or "").strip().lower() != "pass":
        errors.append(f"review_verdict={review.get('verdict') or 'missing'}")
    expected = {
        "character_id": character_id,
        "form": form_name,
        "library_tier": tier,
        "view": view,
        "path": rel,
        "png_sha256": actual_sha,
    }
    for key, expected_value in expected.items():
        if str(review.get(key) or "").strip() != str(expected_value):
            errors.append(f"{key}_mismatch")
    declared_sha = str(review.get("png_sha256") or "").strip()
    if not declared_sha:
        errors.append("png_sha256_missing")
    elif declared_sha != actual_sha:
        errors.append("png_sha256_mismatch")
    expected_binding = binding_fingerprint(
        character_id=character_id,
        form=form_name,
        library_tier=tier,
        view=view,
        path=rel,
        png_sha256=actual_sha,
    )
    if str(review.get("registry_binding_fingerprint_kind") or "") != BINDING_FINGERPRINT_KIND:
        errors.append("registry_binding_fingerprint_kind_invalid")
    if str(review.get("registry_binding_fingerprint") or "") != expected_binding:
        errors.append("registry_binding_fingerprint_mismatch")
    expected_contract = _review_contract(view)
    if str(review.get("review_contract") or "") != expected_contract:
        errors.append("review_contract_invalid_for_view")
    declared_review_kind = str(review.get("review_kind") or review_kind).strip().lower()
    if declared_review_kind != review_kind:
        errors.append("review_kind_mismatch")
    reviewer = str(review.get("reviewer") or "").strip()
    if not reviewer:
        errors.append("reviewer_missing")
    elif review_kind == "human" and _reviewer_is_automated(reviewer):
        errors.append("reviewer_appears_automated")
    if review_kind == "human":
        if review.get("human_signoff") is False:
            errors.append("human_review_cannot_disclaim_human_signoff")
    elif review_kind == "executor_visual":
        if not executor_visual_review_authorized(root):
            errors.append("executor_visual_review_not_authorized_by_project_setting")
        if str(review.get("reviewer_role") or "").strip() != "ai_visual_executor":
            errors.append("executor_visual_reviewer_role_missing_or_mismatch")
        if review.get("human_signoff") is not False:
            errors.append("executor_visual_human_signoff_must_be_false")
    else:
        errors.append("review_kind_missing_or_invalid")
    errors.extend(_reviewed_at_errors(review.get("reviewed_at")))
    criteria = {str(item) for item in (review.get("criteria") or []) if str(item)}
    if not _required_criteria(view).issubset(criteria):
        errors.append("criteria_incomplete")
    confirmation = review.get("confirmation") if isinstance(review.get("confirmation"), Mapping) else {}
    if (
        confirmation.get("kind") != "explicit_current_pixels_acceptance"
        or confirmation.get("accepted_current_pixels") is not True
    ):
        errors.append("explicit_current_pixels_confirmation_missing")
    return (
        sorted(set(errors)),
        rel or raw_rel,
        actual_sha,
        decoded_pixel_fingerprint,
        review,
    )


def _bucket_from_node(
    root: str,
    node: Any,
    *,
    character_id: str,
    form_name: str,
    tier: str,
    view: str,
) -> dict:
    errors, rel, actual_sha, decoded_pixel_fingerprint, review = _review_errors(
        root,
        node,
        character_id=character_id,
        form_name=form_name,
        tier=tier,
        view=view,
    )
    return {
        "status": "pass" if not errors else "fail",
        "evidence_kind": (
            "structured_executor_visual_review"
            if str(review.get("review_kind") or "").strip().lower() == "executor_visual"
            else "structured_human_review"
        ),
        "character_id": character_id,
        "form": form_name,
        "library_tier": tier,
        "view": view,
        "path": rel,
        "sha256": actual_sha,
        "decoded_pixel_fingerprint": decoded_pixel_fingerprint,
        "decoded_pixel_fingerprint_kind": PNG_DECODED_PIXEL_FINGERPRINT_KIND,
        "registry_binding_fingerprint": str(review.get("registry_binding_fingerprint") or ""),
        "registry_binding_fingerprint_kind": str(review.get("registry_binding_fingerprint_kind") or ""),
        "review_contract": str(review.get("review_contract") or ""),
        "reviewer": str(review.get("reviewer") or ""),
        "review_kind": str(review.get("review_kind") or "human"),
        "reviewer_role": str(review.get("reviewer_role") or ""),
        "human_signoff": review.get("human_signoff", True),
        "reviewed_at": str(review.get("reviewed_at") or ""),
        "criteria": list(review.get("criteria") or []),
        "confirmation": dict(review.get("confirmation") or {})
        if isinstance(review.get("confirmation"), Mapping)
        else {},
        "errors": errors,
    }


def _expression_bucket(
    root: str,
    form: Mapping[str, Any],
    *,
    character_id: str,
    form_name: str,
    tier: str,
) -> dict:
    candidates = _expression_nodes(form)
    evaluated = [
        _bucket_from_node(
            root,
            node,
            character_id=character_id,
            form_name=form_name,
            tier=tier,
            view="expression",
        )
        for node in candidates
    ]
    for bucket in evaluated:
        if bucket["status"] == "pass":
            return bucket
    if evaluated:
        return evaluated[0]
    return {
        "status": "fail",
        "evidence_kind": "structured_pixel_review_missing",
        "path": "",
        "sha256": "",
        "review_contract": "",
        "reviewer": "",
        "reviewed_at": "",
        "errors": ["expression_reference_or_review_missing"],
    }


def _find_exact_core_form(
    registry: Mapping[str, Any],
    *,
    character_id: str,
    form_name: str,
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    characters = registry.get("characters") if isinstance(registry.get("characters"), list) else []
    character_matches = [
        value
        for value in characters
        if isinstance(value, dict)
        and str(value.get("id") or value.get("character_id") or "").strip() == character_id
    ]
    if len(character_matches) != 1:
        if not character_matches:
            raise ReceiptError(f"identity_registry 无精确角色 `{character_id}`")
        raise ReceiptError(f"identity_registry 角色 `{character_id}` 不唯一，拒绝歧义签收")
    character = character_matches[0]
    tier = character_library_tier_for_record(character)
    if tier != CHARACTER_LIBRARY_TIER_CORE:
        raise ReceiptError(
            f"{character_id} 的人物库档位是 `{tier}`，该入口只签 core_full 多视图"
        )
    raw_forms = character.get("forms")
    forms = raw_forms if isinstance(raw_forms, list) else [character]
    form_matches = [
        value
        for value in forms
        if isinstance(value, dict)
        and (str(value.get("form") or value.get("form_name") or "default").strip() or "default")
        == form_name
    ]
    if len(form_matches) != 1:
        if not form_matches:
            raise ReceiptError(f"角色 `{character_id}` 无精确形态 `{form_name}`")
        raise ReceiptError(f"角色 `{character_id}` 的形态 `{form_name}` 不唯一，拒绝歧义签收")
    return character, form_matches[0], tier


def _mutable_expression_nodes(form: Mapping[str, Any]) -> List[Dict[str, Any]]:
    group = form.get("reference_group") if isinstance(form.get("reference_group"), Mapping) else {}
    atlas = form.get("reference_atlas") if isinstance(form.get("reference_atlas"), Mapping) else {}
    roots = (
        group.get("expressions"),
        group.get("face_anchor_refs"),
        atlas.get("expression_refs"),
        atlas.get("face_anchor_refs"),
    )
    found: List[Dict[str, Any]] = []
    seen: set[int] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            marker = id(value)
            if marker in seen:
                return
            seen.add(marker)
            if _reference_path(value):
                found.append(value)
                return
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    for root_value in roots:
        walk(root_value)
    return found


def _select_review_node(
    form: Dict[str, Any],
    *,
    view: str,
    view_path: str,
) -> Tuple[Dict[str, Any], str]:
    requested_path = str(view_path or "").strip()
    if view == "expression":
        if not requested_path:
            raise ReceiptError("expression 必须用 --view-path 指明实际看过的 PNG")
        matches = [
            node for node in _mutable_expression_nodes(form)
            if _reference_path(node) == requested_path
        ]
        if not matches:
            candidates = sorted({_reference_path(node) for node in _mutable_expression_nodes(form)})
            suffix = f"；已登记候选：{', '.join(candidates)}" if candidates else ""
            raise ReceiptError(f"expression path 未精确登记：{requested_path}{suffix}")
        if len(matches) != 1:
            raise ReceiptError(
                f"expression path `{requested_path}` 在 registry 出现 {len(matches)} 次，先去重再签收"
            )
        node = matches[0]
    else:
        raw_node = _view_node(form, view)
        if not isinstance(raw_node, dict):
            raise ReceiptError(f"{view} 必须先以结构化 registry 节点登记，不能给裸路径签收")
        node = raw_node
    rel = _reference_path(node)
    if not rel:
        raise ReceiptError(f"{view} registry 节点缺 path")
    if requested_path and requested_path != rel:
        raise ReceiptError(f"{view} path 不匹配：registry={rel}，requested={requested_path}")
    status = str(node.get("status") or "").strip().lower()
    if status == "planned":
        raise ReceiptError("registry 节点仍是 planned；旧收据或磁盘同名文件不能让计划项复活")
    if status not in REVIEWABLE_NODE_STATUSES:
        raise ReceiptError(
            f"registry 节点状态 `{status or 'missing'}` 不可人审；需 ready/registered/review_pending/review_failed"
        )
    return node, rel


def _ensure_path_not_reused_by_another_bucket(
    root: str,
    form: Mapping[str, Any],
    *,
    selected_node: Mapping[str, Any],
    selected_view: str,
    selected_path: str,
) -> None:
    selected_rel, selected_realpath, selected_errors = _resolve_project_evidence_path(root, selected_path)
    if selected_errors:
        raise ReceiptError(f"证据 path 非法：{', '.join(selected_errors)}")
    selected_sha = _sha256(selected_realpath)
    selected_pixel_fingerprint, selected_fingerprint_errors = png_decoded_pixel_fingerprint(
        selected_realpath
    )
    if selected_fingerprint_errors or not selected_pixel_fingerprint:
        details = selected_fingerprint_errors or ["png_pixel_fingerprint_unavailable"]
        raise ReceiptError(
            f"当前 PNG 不能作为可解码像素证据，无法计算解码像素指纹：{', '.join(details)}"
        )
    realpath_usages: List[str] = []
    sha_usages: List[str] = []
    pixel_fingerprint_usages: List[str] = []
    for other_view in REVIEWABLE_VIEWS:
        if other_view == "expression":
            nodes: Iterable[Any] = _mutable_expression_nodes(form)
        else:
            nodes = (_view_node(form, other_view),)
        for other_node in nodes:
            if other_node is selected_node:
                continue
            other_raw = _reference_path(other_node)
            if not other_raw:
                continue
            _other_rel, other_realpath, other_errors = _resolve_project_evidence_path(root, other_raw)
            if other_errors:
                continue
            if other_realpath == selected_realpath:
                realpath_usages.append(other_view)
            other_sha = _sha256(other_realpath)
            if selected_sha and other_sha == selected_sha:
                sha_usages.append(other_view)
            other_pixel_fingerprint, other_fingerprint_errors = png_decoded_pixel_fingerprint(
                other_realpath
            )
            if (
                not other_fingerprint_errors
                and other_pixel_fingerprint
                and other_pixel_fingerprint == selected_pixel_fingerprint
            ):
                pixel_fingerprint_usages.append(other_view)
    if realpath_usages or sha_usages or pixel_fingerprint_usages:
        details: List[str] = []
        if realpath_usages:
            details.append(f"canonical realpath 与 {','.join(sorted(set(realpath_usages)))} 重复")
        if sha_usages:
            details.append(f"current PNG SHA 与 {','.join(sorted(set(sha_usages)))} 重复")
        if pixel_fingerprint_usages:
            details.append(
                "decoded pixel fingerprint 与 "
                f"{','.join(sorted(set(pixel_fingerprint_usages)))} 重复"
            )
        raise ReceiptError(
            f"PNG `{selected_rel}` {'；'.join(details)}；不能把同一路径或同一像素签成"
            f" `{selected_view}` 与其他桶"
        )


def _write_registry_atomic(
    path: str,
    payload: Mapping[str, Any],
    *,
    expected_sha256: str,
) -> None:
    directory = os.path.dirname(path)
    mode = os.stat(path).st_mode & 0o777
    fd, tmp = tempfile.mkstemp(prefix=".identity_registry.", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        if _sha256(path) != expected_sha256:
            raise ReceiptError("identity_registry 在签收期间被其他进程修改；未覆盖，请重试")
        os.replace(tmp, path)
        try:
            directory_fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Some filesystems do not allow fsync on a directory.  The same-dir
            # os.replace above still guarantees readers never see partial JSON.
            pass
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def record_current_view_receipt(
    root: str,
    *,
    character_id: str,
    form: str,
    view: str,
    reviewer: str,
    accept_current_pixels: bool,
    view_path: str = "",
    reviewed_at: str = "",
    criteria: Optional[Iterable[str]] = None,
    note: str = "",
    review_kind: str = "human",
) -> dict:
    """Atomically record one explicit, current-pixel review receipt.

    This deliberately never creates a missing view, revives ``planned``, or
    finalizes a character form.  Human is the default.  ``executor_visual`` is
    allowed only when the project explicitly authorizes executor pixel review;
    its receipt is stored separately with ``human_signoff=false``.
    """
    if accept_current_pixels is not True:
        raise ReceiptError("缺 --accept-current-pixels；未明确看过当前像素，禁止写 pass 收据")
    character_id = str(character_id or "").strip()
    form_name = str(form or "").strip()
    view = str(view or "").strip()
    reviewer = str(reviewer or "").strip()
    normalized_review_kind = str(review_kind or "human").strip().lower()
    if not character_id or not form_name:
        raise ReceiptError("必须同时提供精确 --character-id 与 --form")
    if view not in REVIEWABLE_VIEWS:
        raise ReceiptError(f"未知 view `{view}`；可选 {', '.join(REVIEWABLE_VIEWS)}")
    if normalized_review_kind not in {"human", "executor_visual"}:
        raise ReceiptError("review_kind 只能是 human 或 executor_visual")
    if normalized_review_kind == "human" and _reviewer_is_automated(reviewer):
        raise ReceiptError("reviewer 必须是非空、非明显自动化的人工声明标识，不能是 bot/codex/agent/runner")
    if normalized_review_kind == "executor_visual" and not executor_visual_review_authorized(root):
        raise ReceiptError("项目未明确授权执行者实际像素目视，不能写 executor_visual 收据")
    when = _normalized_reviewed_at(reviewed_at)
    root = os.path.abspath(root)
    reg_path = registry_path(root)
    before_sha = _sha256(reg_path)
    registry = _load_json(reg_path)
    if not before_sha or not isinstance(registry, dict):
        raise ReceiptError("identity_registry.json 缺失、不可读或不是 JSON object")
    _character, registry_form, tier = _find_exact_core_form(
        registry,
        character_id=character_id,
        form_name=form_name,
    )
    node, rel = _select_review_node(registry_form, view=view, view_path=view_path)
    _ensure_path_not_reused_by_another_bucket(
        root,
        registry_form,
        selected_node=node,
        selected_view=view,
        selected_path=rel,
    )
    canonical_rel, png_path, path_errors = _resolve_project_evidence_path(root, rel)
    if path_errors:
        raise ReceiptError(f"证据 path 非法：{', '.join(path_errors)}")
    png_errors = _png_container_errors(png_path)
    if png_errors:
        raise ReceiptError(f"当前 PNG 不能作为可解码像素证据：{', '.join(png_errors)}")
    png_sha = _sha256(png_path)
    if not png_sha:
        raise ReceiptError("当前 PNG 不存在或不可读")
    required = _required_criteria(view)
    selected_criteria = (
        {str(value).strip() for value in criteria if str(value).strip()}
        if criteria is not None
        else set(required)
    )
    missing_criteria = sorted(required - selected_criteria)
    if missing_criteria:
        raise ReceiptError(f"criteria 未完整确认：{', '.join(missing_criteria)}")
    binding = binding_fingerprint(
        character_id=character_id,
        form=form_name,
        library_tier=tier,
        view=view,
        path=canonical_rel,
        png_sha256=png_sha,
    )
    receipt = {
        "status": "accepted",
        "verdict": "pass",
        "character_id": character_id,
        "form": form_name,
        "library_tier": tier,
        "view": view,
        "path": canonical_rel,
        "reviewer": reviewer,
        "review_kind": normalized_review_kind,
        "reviewer_role": (
            "ai_visual_executor"
            if normalized_review_kind == "executor_visual"
            else "human_creative_reviewer"
        ),
        "human_signoff": normalized_review_kind == "human",
        "reviewed_at": when,
        "png_sha256": png_sha,
        "registry_binding_fingerprint": binding,
        "registry_binding_fingerprint_kind": BINDING_FINGERPRINT_KIND,
        "review_contract": _review_contract(view),
        "criteria": sorted(selected_criteria),
        "confirmation": {
            "kind": "explicit_current_pixels_acceptance",
            "accepted_current_pixels": True,
        },
    }
    if str(note or "").strip():
        receipt["note"] = str(note).strip()
    previous_status = str(node.get("status") or "").strip().lower()
    node["status"] = "registered" if previous_status == "registered" else "ready"
    node["sha256"] = png_sha
    receipt_key = "human_review" if normalized_review_kind == "human" else "visual_review"
    node[receipt_key] = receipt
    validation_errors, _rel, validated_sha, validated_pixel_fingerprint, _review = _review_errors(
        root,
        node,
        character_id=character_id,
        form_name=form_name,
        tier=tier,
        view=view,
    )
    if validation_errors:
        raise ReceiptError(f"收据未通过 pack 自检：{', '.join(validation_errors)}")
    if (
        validated_sha != png_sha
        or not validated_pixel_fingerprint
        or _sha256(png_path) != png_sha
    ):
        raise ReceiptError("PNG 在签收过程中发生变化；未写 registry，请重新查看当前像素")
    _write_registry_atomic(reg_path, registry, expected_sha256=before_sha)
    return {
        "ok": True,
        "kind": "n2d_identity_view_review_receipt_record",
        "version": 1,
        "character_id": character_id,
        "form": form_name,
        "library_tier": tier,
        "view": view,
        "review_kind": normalized_review_kind,
        "path": canonical_rel,
        "png_sha256": png_sha,
        "registry_binding_fingerprint": binding,
        "registry_path": os.path.relpath(reg_path, root),
        "registry_sha256": _sha256(reg_path),
        "previous_node_status": previous_status,
        "node_status": str(node.get("status") or ""),
        "receipt": receipt,
    }


def build_pack(root: str) -> dict:
    reg_path = registry_path(root)
    registry = _load_json(reg_path)
    rows: List[dict] = []
    if isinstance(registry, Mapping):
        for char in registry.get("characters") or []:
            if not isinstance(char, Mapping):
                continue
            tier = character_library_tier_for_record(char)
            if tier != CHARACTER_LIBRARY_TIER_CORE:
                continue
            cid = str(char.get("id") or char.get("character_id") or "").strip()
            forms = char.get("forms") if isinstance(char.get("forms"), list) else [char]
            for form in forms:
                if not isinstance(form, Mapping):
                    continue
                form_name = str(form.get("form") or form.get("form_name") or "default").strip() or "default"
                buckets = {
                    view: _bucket_from_node(
                        root,
                        _view_node(form, view),
                        character_id=cid,
                        form_name=form_name,
                        tier=tier,
                        view=view,
                    )
                    for view in required_character_library_views(tier)
                }
                buckets["expression"] = _expression_bucket(
                    root,
                    form,
                    character_id=cid,
                    form_name=form_name,
                    tier=tier,
                )
                turnaround = _view_node(form, "turnaround")
                buckets["turnaround"] = _bucket_from_node(
                    root,
                    turnaround,
                    character_id=cid,
                    form_name=form_name,
                    tier=tier,
                    view="turnaround",
                )
                path_groups: Dict[str, List[str]] = {}
                realpath_groups: Dict[str, List[str]] = {}
                sha_groups: Dict[str, List[str]] = {}
                pixel_fingerprint_groups: Dict[str, List[str]] = {}
                for bucket_name, value in buckets.items():
                    if not isinstance(value, Mapping):
                        continue
                    bucket_path = str(value.get("path") or "").strip()
                    bucket_sha = str(value.get("sha256") or "").strip()
                    bucket_pixel_fingerprint = str(
                        value.get("decoded_pixel_fingerprint") or ""
                    ).strip()
                    if bucket_path:
                        path_groups.setdefault(bucket_path, []).append(bucket_name)
                        _normalized, bucket_realpath, path_errors = _resolve_project_evidence_path(
                            root, bucket_path
                        )
                        if not path_errors:
                            realpath_groups.setdefault(bucket_realpath, []).append(bucket_name)
                    if bucket_sha:
                        sha_groups.setdefault(bucket_sha, []).append(bucket_name)
                    if bucket_pixel_fingerprint:
                        pixel_fingerprint_groups.setdefault(
                            bucket_pixel_fingerprint, []
                        ).append(bucket_name)

                def mark_duplicate(groups: Mapping[str, List[str]], code: str) -> None:
                    for names in groups.values():
                        if len(names) < 2:
                            continue
                        for name in names:
                            value = buckets.get(name)
                            if isinstance(value, dict):
                                value.setdefault("errors", []).append(code)
                                value["errors"] = sorted(set(value["errors"]))
                                value["status"] = "fail"

                mark_duplicate(path_groups, "duplicate_path_across_buckets")
                mark_duplicate(realpath_groups, "duplicate_canonical_realpath_across_buckets")
                mark_duplicate(sha_groups, "duplicate_png_sha_across_buckets")
                mark_duplicate(
                    pixel_fingerprint_groups,
                    "duplicate_decoded_pixel_fingerprint_across_buckets",
                )
                failed = [key for key, value in buckets.items() if value.get("status") != "pass"]
                rows.append({
                    "character_id": cid,
                    "form": form_name,
                    "library_tier": tier,
                    "required_buckets": list(required_character_library_views(tier)) + ["expression", "turnaround"],
                    "buckets": buckets,
                    "verdict": "pass" if not failed else "fail",
                    "failed_buckets": failed,
                })
    return {
        "kind": PACK_KIND,
        "version": PACK_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "identity_registry_path": "出图/共享/identity_registry.json",
        "identity_registry_sha256": _sha256(reg_path),
        "rows": rows,
        "summary": {
            "core_forms": len(rows),
            "passed": sum(1 for row in rows if row["verdict"] == "pass"),
            "failed": sum(1 for row in rows if row["verdict"] != "pass"),
        },
    }


def write_pack(root: str, payload: Mapping[str, Any], output: str = "") -> str:
    path = output or os.path.join(root, "生产数据", "identity_eval_pack.json")
    if not os.path.isabs(path):
        path = os.path.join(root, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="从逐视图像素审阅收据构建核心人物 identity_eval_pack")
    parser.add_argument("root")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--record-current-view",
        action="store_true",
        help="原子记录一个核心人物当前 PNG 的显式逐视图像素审阅收据，不会 finalize 整个形态",
    )
    parser.add_argument("--character-id", default="", help="与 --record-current-view 连用：精确 CHAR_ID")
    parser.add_argument("--form", default="", help="与 --record-current-view 连用：精确形态名")
    parser.add_argument(
        "--view",
        choices=REVIEWABLE_VIEWS,
        help="与 --record-current-view 连用：五角、turnaround 或 expression",
    )
    parser.add_argument(
        "--view-path",
        "--path",
        dest="view_path",
        default="",
        help="registry 中的精确 PNG path；expression 必填，其他 view 可用于二次核对",
    )
    parser.add_argument(
        "--reviewer",
        default="",
        help="人工声明审阅者/岗位标识；只排除明显 bot/codex/agent/runner，不认证真实身份或独立性",
    )
    parser.add_argument(
        "--review-kind",
        choices=("human", "executor_visual"),
        default="human",
        help="human=人工签收；executor_visual=项目明确授权的执行者实际像素目视（不冒充人工）",
    )
    parser.add_argument("--reviewed-at", default="", help="带时区 ISO-8601；缺省写当前 UTC")
    parser.add_argument(
        "--criterion",
        action="append",
        default=None,
        help="重复提供自定义已确认 criteria；不传则使用该 review contract 的完整标准集",
    )
    parser.add_argument("--review-note", default="", help="可选人工复核说明")
    parser.add_argument(
        "--accept-current-pixels",
        action="store_true",
        help="明确确认 reviewer 已查看当前 path 对应的当前像素；缺少此旗标绝不写 pass",
    )
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    if args.record_current_view:
        try:
            payload = record_current_view_receipt(
                root,
                character_id=args.character_id,
                form=args.form,
                view=args.view or "",
                reviewer=args.reviewer,
                accept_current_pixels=args.accept_current_pixels,
                view_path=args.view_path,
                reviewed_at=args.reviewed_at,
                criteria=args.criterion,
                note=args.review_note,
                review_kind=args.review_kind,
            )
        except ReceiptError as exc:
            print(json.dumps({
                "ok": False,
                "kind": "n2d_identity_view_review_receipt_record",
                "error": str(exc),
            }, ensure_ascii=False, indent=2))
            return 2
        current_pack = build_pack(root)
        target_row = next((
            row for row in current_pack.get("rows") or []
            if row.get("character_id") == args.character_id and row.get("form") == args.form
        ), {})
        target_bucket = (target_row.get("buckets") or {}).get(args.view or "", {})
        payload["pack_consumption"] = {
            "bucket_status": target_bucket.get("status") or "missing",
            "bucket_errors": target_bucket.get("errors") or [],
            "form_verdict": target_row.get("verdict") or "missing",
        }
        if args.write:
            payload["pack_output_path"] = os.path.relpath(
                write_pack(root, current_pack, args.output),
                root,
            )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if target_bucket.get("status") == "pass" else 2
    payload = build_pack(root)
    if args.write:
        payload["output_path"] = os.path.relpath(
            write_pack(root, payload, args.output),
            root,
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not payload["summary"]["failed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
