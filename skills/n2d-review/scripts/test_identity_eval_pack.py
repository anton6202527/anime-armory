import hashlib
import json
import struct
import zlib
import copy
from pathlib import Path

import pytest

import identity_eval_pack as iep
import production_consistency as pc


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _png_bytes(label: str, width: int = 512, height: int = 512) -> bytes:
    """Create a small but structurally valid, independently hashed RGB PNG."""
    color = hashlib.sha256(label.encode()).digest()[:3]
    raw = b"".join(b"\0" + color * width for _ in range(height))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _reencoded_png_bytes(label: str, width: int = 512, height: int = 512) -> bytes:
    """Same decoded RGB pixels as _png_bytes, with different PNG encoding."""
    color = hashlib.sha256(label.encode()).digest()[:3]
    row = color * width
    encoded_row = bytes(
        (value - (row[index - 3] if index >= 3 else 0)) & 0xFF
        for index, value in enumerate(row)
    )
    raw = b"".join(b"\1" + encoded_row for _ in range(height))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"tEXt", b"audit-note\0metadata changed")
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _forged_png_shell(width: int = 512, height: int = 512) -> bytes:
    """Valid signature/CRC/IHDR/IEND but deliberately no decodable pixel data."""
    def chunk(kind: bytes, payload: bytes) -> bytes:
        body = kind + payload
        return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IEND", b"")
    )


def _review(cid: str, form: str, view: str, rel: str, data: bytes) -> dict:
    sha = hashlib.sha256(data).hexdigest()
    return {
        "status": "accepted",
        "verdict": "pass",
        "character_id": cid,
        "form": form,
        "library_tier": "core_full",
        "view": view,
        "path": rel,
        "reviewer": "qa@example.test",
        "reviewed_at": "2026-07-14T10:00:00+08:00",
        "png_sha256": sha,
        "registry_binding_fingerprint": iep.binding_fingerprint(
            character_id=cid,
            form=form,
            library_tier="core_full",
            view=view,
            path=rel,
            png_sha256=sha,
        ),
        "registry_binding_fingerprint_kind": "sha256:canonical-json(char,form,tier,view,path,png_sha256)",
        "review_contract": "n2d_expression_review_v1" if view == "expression" else "n2d_turnaround_view_review_v1",
        "criteria": sorted(
            iep.EXPRESSION_REQUIRED_CRITERIA
            if view == "expression"
            else iep.REQUIRED_CRITERIA
        ),
        "confirmation": {
            "kind": "explicit_current_pixels_acceptance",
            "accepted_current_pixels": True,
        },
    }


def _executor_review(cid: str, form: str, view: str, rel: str, data: bytes) -> dict:
    review = _review(cid, form, view, rel, data)
    review.update({
        "reviewer": "Codex视觉执行者",
        "review_kind": "executor_visual",
        "reviewer_role": "ai_visual_executor",
        "human_signoff": False,
    })
    return review


def _project(root: Path) -> dict:
    cid, form = "CHAR_01", "常态"
    group = {}
    for view in (*iep.required_character_library_views("core_full"), "turnaround"):
        rel = f"出图/共享/图片/{view}.png"
        data = _png_bytes(view)
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        group[view] = {"path": rel, "status": "ready", "human_review": _review(cid, form, view, rel, data)}
    expr_rel = "出图/共享/图片/expression.png"
    expr_data = _png_bytes("expression")
    (root / expr_rel).write_bytes(expr_data)
    group["expressions"] = [{
        "path": expr_rel,
        "status": "ready",
        "human_review": _review(cid, form, "expression", expr_rel, expr_data),
    }]
    registry = {
        "characters": [{
            "id": cid,
            "scope": "贯穿全篇女主",
            "library_tier": "core_full",
            "forms": [{"form": form, "reference_group": group}],
        }],
    }
    _write_json(root / "出图" / "共享" / "identity_registry.json", registry)
    return registry


def test_build_pack_promotes_only_current_bound_review_receipts(tmp_path: Path) -> None:
    _project(tmp_path)
    pack = iep.build_pack(str(tmp_path))
    assert pack["summary"] == {"core_forms": 1, "passed": 1, "failed": 0}
    assert pack["rows"][0]["verdict"] == "pass"
    assert pack["rows"][0]["buckets"]["rear_three_quarter"]["status"] == "pass"

    iep.write_pack(str(tmp_path), pack)
    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")
    assert not [row for row in audit["findings"] if row["verdict"] == "block"]


def test_authorized_executor_visual_receipt_is_consumed_without_impersonating_human(
    tmp_path: Path,
) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["front"]
    data = (tmp_path / node["path"]).read_bytes()
    node.pop("human_review")
    node["visual_review"] = _executor_review(
        "CHAR_01", "常态", "front", node["path"], data
    )
    (tmp_path / "_设置.md").write_text(
        "- 图片验收模式：逐张机器QC+实际目视  # source=explicit_user\n"
        "- 记录：用户明确授权执行者实际像素目视\n",
        encoding="utf-8",
    )
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    pack = iep.build_pack(str(tmp_path))
    bucket = pack["rows"][0]["buckets"]["front"]
    assert pack["version"] == 3
    assert bucket["status"] == "pass"
    assert bucket["evidence_kind"] == "structured_executor_visual_review"
    assert bucket["review_kind"] == "executor_visual"
    assert bucket["human_signoff"] is False

    iep.write_pack(str(tmp_path), pack)
    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")
    assert not [row for row in audit["findings"] if row["verdict"] == "block"]


def test_executor_visual_receipt_without_explicit_project_authorization_fails(
    tmp_path: Path,
) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["front"]
    data = (tmp_path / node["path"]).read_bytes()
    node.pop("human_review")
    node["visual_review"] = _executor_review(
        "CHAR_01", "常态", "front", node["path"], data
    )
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    bucket = iep.build_pack(str(tmp_path))["rows"][0]["buckets"]["front"]

    assert bucket["status"] == "fail"
    assert "executor_visual_review_not_authorized_by_project_setting" in bucket["errors"]


def test_changed_png_invalidates_old_receipt(tmp_path: Path) -> None:
    _project(tmp_path)
    (tmp_path / "出图" / "共享" / "图片" / "rear_three_quarter.png").write_bytes(b"changed")
    pack = iep.build_pack(str(tmp_path))
    row = pack["rows"][0]
    assert row["verdict"] == "fail"
    assert "rear_three_quarter" in row["failed_buckets"]
    assert "png_sha256_mismatch" in row["buckets"]["rear_three_quarter"]["errors"]


def test_planned_or_unreviewed_view_never_counts_as_ready(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    node["status"] = "planned"
    node.pop("human_review")
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)
    pack = iep.build_pack(str(tmp_path))
    assert pack["rows"][0]["buckets"]["side"]["status"] == "fail"
    assert "structured_pixel_review_missing" in pack["rows"][0]["buckets"]["side"]["errors"]


def test_planned_view_cannot_reuse_a_stale_accepted_receipt(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    node["status"] = "planned"  # deliberately retain the old accepted receipt
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    pack = iep.build_pack(str(tmp_path))

    side = pack["rows"][0]["buckets"]["side"]
    assert side["status"] == "fail"
    assert "registry_node_status=planned" in side["errors"]


def test_plain_text_with_matching_hash_cannot_pose_as_png_evidence(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    rel = node["path"]
    fake = b"this is not an image"
    (tmp_path / rel).write_bytes(fake)
    node["human_review"] = _review("CHAR_01", "常态", "side", rel, fake)
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    pack = iep.build_pack(str(tmp_path))

    assert pack["rows"][0]["buckets"]["side"]["status"] == "fail"
    assert "not_valid_png_container" in pack["rows"][0]["buckets"]["side"]["errors"]


def test_forged_png_header_shell_with_matching_hash_cannot_pose_as_pixels(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    rel = node["path"]
    fake = _forged_png_shell()
    (tmp_path / rel).write_bytes(fake)
    node["human_review"] = _review("CHAR_01", "常态", "side", rel, fake)
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    pack = iep.build_pack(str(tmp_path))

    errors = pack["rows"][0]["buckets"]["side"]["errors"]
    assert pack["rows"][0]["buckets"]["side"]["status"] == "fail"
    assert "not_valid_png_container" in errors
    assert "png_iend_invalid" in errors


def test_same_png_cannot_be_relabelled_as_multiple_views(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    side = group["side"]
    rel = side["path"]
    data = (tmp_path / rel).read_bytes()
    group["back"] = {
        "path": rel,
        "status": "ready",
        "human_review": _review("CHAR_01", "常态", "back", rel, data),
    }
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    pack = iep.build_pack(str(tmp_path))

    assert pack["rows"][0]["verdict"] == "fail"
    assert "duplicate_path_across_buckets" in pack["rows"][0]["buckets"]["side"]["errors"]
    assert "duplicate_path_across_buckets" in pack["rows"][0]["buckets"]["back"]["errors"]


def test_producer_duplicate_png_sha_copy_cannot_pose_as_independent_view(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    side_rel = group["side"]["path"]
    copied_rel = "出图/共享/图片/back_copy.png"
    copied = (tmp_path / side_rel).read_bytes()
    (tmp_path / copied_rel).write_bytes(copied)
    group["back"] = {
        "path": copied_rel,
        "status": "ready",
        "human_review": _review("CHAR_01", "常态", "back", copied_rel, copied),
    }
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    buckets = iep.build_pack(str(tmp_path))["rows"][0]["buckets"]

    assert "duplicate_png_sha_across_buckets" in buckets["side"]["errors"]
    assert "duplicate_png_sha_across_buckets" in buckets["back"]["errors"]
    assert "duplicate_canonical_realpath_across_buckets" not in buckets["back"]["errors"]


def test_producer_reencoded_same_pixels_are_blocked_by_decoded_fingerprint(
    tmp_path: Path,
) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    side_rel = group["side"]["path"]
    reencoded_rel = "出图/共享/图片/back_reencoded.png"
    original = (tmp_path / side_rel).read_bytes()
    reencoded = _reencoded_png_bytes("side")
    assert hashlib.sha256(original).digest() != hashlib.sha256(reencoded).digest()
    (tmp_path / reencoded_rel).write_bytes(reencoded)
    group["back"] = {
        "path": reencoded_rel,
        "status": "ready",
        "human_review": _review("CHAR_01", "常态", "back", reencoded_rel, reencoded),
    }
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    buckets = iep.build_pack(str(tmp_path))["rows"][0]["buckets"]

    assert buckets["side"]["sha256"] != buckets["back"]["sha256"]
    assert (
        buckets["side"]["decoded_pixel_fingerprint"]
        == buckets["back"]["decoded_pixel_fingerprint"]
    )
    assert "duplicate_png_sha_across_buckets" not in buckets["back"]["errors"]
    assert (
        "duplicate_decoded_pixel_fingerprint_across_buckets"
        in buckets["side"]["errors"]
    )
    assert (
        "duplicate_decoded_pixel_fingerprint_across_buckets"
        in buckets["back"]["errors"]
    )


def test_producer_symlink_alias_uses_canonical_realpath_and_is_blocked(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    side_rel = group["side"]["path"]
    link_rel = "出图/共享/图片/back_symlink.png"
    (tmp_path / link_rel).symlink_to(Path(side_rel).name)
    data = (tmp_path / side_rel).read_bytes()
    # Receipt/fingerprint uses the canonical project-relative target, while the
    # registry deliberately supplies a symlink alias.
    group["back"] = {
        "path": link_rel,
        "status": "ready",
        "human_review": _review("CHAR_01", "常态", "back", side_rel, data),
    }
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    buckets = iep.build_pack(str(tmp_path))["rows"][0]["buckets"]

    assert buckets["back"]["path"] == side_rel
    assert "duplicate_canonical_realpath_across_buckets" in buckets["side"]["errors"]
    assert "duplicate_canonical_realpath_across_buckets" in buckets["back"]["errors"]
    assert "duplicate_png_sha_across_buckets" in buckets["back"]["errors"]


@pytest.mark.parametrize("mode", ["absolute", "traversal", "noncanonical"])
def test_producer_path_escape_and_absolute_registry_evidence_are_rejected(
    tmp_path: Path,
    mode: str,
) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    if mode == "absolute":
        node["path"] = str((tmp_path / "出图" / "共享" / "图片" / "side.png").resolve())
        expected = "absolute_registry_evidence_path_not_allowed"
    elif mode == "traversal":
        outside = tmp_path.parent / f"{tmp_path.name}_outside.png"
        outside.write_bytes(_png_bytes("outside"))
        node["path"] = f"../{outside.name}"
        expected = "registry_evidence_path_outside_project_root"
    else:
        node["path"] = "出图/共享/图片/../图片/side.png"
        expected = "registry_evidence_path_not_canonical_project_relative"
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    errors = iep.build_pack(str(tmp_path))["rows"][0]["buckets"]["side"]["errors"]

    assert expected in errors


def test_distinct_crop_pixels_from_same_master_remain_valid(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    for view, crop in (("side", "left_crop"), ("back", "right_crop")):
        rel = f"出图/共享/图片/{view}_derived.png"
        data = _png_bytes(f"same_master:{crop}")
        (tmp_path / rel).write_bytes(data)
        group[view] = {
            "path": rel,
            "status": "ready",
            "derivation": {"source_path": "出图/共享/图片/master.png", "crop": crop},
            "human_review": _review("CHAR_01", "常态", view, rel, data),
        }
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    pack = iep.build_pack(str(tmp_path))

    assert pack["rows"][0]["verdict"] == "pass"
    assert (
        pack["rows"][0]["buckets"]["side"]["decoded_pixel_fingerprint"]
        != pack["rows"][0]["buckets"]["back"]["decoded_pixel_fingerprint"]
    )
    iep.write_pack(str(tmp_path), pack)
    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")
    assert not [item for item in audit["findings"] if item["verdict"] == "block"]


def test_consumer_duplicate_png_sha_copy_is_independently_blocked(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    side_rel = group["side"]["path"]
    copied_rel = "出图/共享/图片/back_copy.png"
    copied = (tmp_path / side_rel).read_bytes()
    (tmp_path / copied_rel).write_bytes(copied)
    group["back"] = {
        "path": copied_rel,
        "status": "ready",
        "human_review": _review("CHAR_01", "常态", "back", copied_rel, copied),
    }
    reg_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    _write_json(reg_path, registry)
    pack = iep.build_pack(str(tmp_path))
    row = pack["rows"][0]
    row["verdict"] = "pass"
    row["failed_buckets"] = []
    for bucket in row["buckets"].values():
        bucket["status"] = "pass"
        bucket["errors"] = []
    iep.write_pack(str(tmp_path), pack)

    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")
    messages = "\n".join(item["message"] for item in audit["findings"])

    assert "duplicate_png_sha" in messages


def test_consumer_reencoded_same_pixels_are_independently_blocked(
    tmp_path: Path,
) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    side_rel = group["side"]["path"]
    reencoded_rel = "出图/共享/图片/back_reencoded.png"
    reencoded = _reencoded_png_bytes("side")
    assert hashlib.sha256((tmp_path / side_rel).read_bytes()).digest() != hashlib.sha256(
        reencoded
    ).digest()
    (tmp_path / reencoded_rel).write_bytes(reencoded)
    group["back"] = {
        "path": reencoded_rel,
        "status": "ready",
        "human_review": _review("CHAR_01", "常态", "back", reencoded_rel, reencoded),
    }
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)
    pack = iep.build_pack(str(tmp_path))
    row = pack["rows"][0]
    row["verdict"] = "pass"
    row["failed_buckets"] = []
    for bucket in row["buckets"].values():
        bucket["status"] = "pass"
        bucket["errors"] = []
    iep.write_pack(str(tmp_path), pack)

    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")
    messages = "\n".join(item["message"] for item in audit["findings"])

    assert "duplicate_png_sha" not in messages
    assert "duplicate_decoded_pixel_fingerprint" in messages


def test_consumer_symlink_alias_is_independently_blocked(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    side_rel = group["side"]["path"]
    link_rel = "出图/共享/图片/back_symlink.png"
    (tmp_path / link_rel).symlink_to(Path(side_rel).name)
    data = (tmp_path / side_rel).read_bytes()
    group["back"] = {
        "path": link_rel,
        "status": "ready",
        "human_review": _review("CHAR_01", "常态", "back", side_rel, data),
    }
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)
    pack = iep.build_pack(str(tmp_path))
    row = pack["rows"][0]
    row["verdict"] = "pass"
    row["failed_buckets"] = []
    for bucket in row["buckets"].values():
        bucket["status"] = "pass"
        bucket["errors"] = []
    iep.write_pack(str(tmp_path), pack)

    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")
    messages = "\n".join(item["message"] for item in audit["findings"])

    assert "duplicate_canonical_realpath" in messages
    assert "duplicate_png_sha" in messages


@pytest.mark.parametrize("mode", ["absolute", "traversal", "noncanonical"])
def test_consumer_path_escape_and_absolute_registry_path_are_independently_blocked(
    tmp_path: Path,
    mode: str,
) -> None:
    registry = _project(tmp_path)
    pack = iep.build_pack(str(tmp_path))
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    if mode == "absolute":
        node["path"] = str((tmp_path / "出图" / "共享" / "图片" / "side.png").resolve())
        expected = "registry_evidence_absolute_path_not_allowed"
    elif mode == "traversal":
        outside = tmp_path.parent / f"{tmp_path.name}_consumer_outside.png"
        outside.write_bytes(_png_bytes("consumer_outside"))
        node["path"] = f"../{outside.name}"
        expected = "registry_evidence_path_outside_project_root"
    else:
        node["path"] = "出图/共享/图片/../图片/side.png"
        expected = "registry_evidence_path_not_canonical_project_relative"
    reg_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    _write_json(reg_path, registry)
    pack["identity_registry_sha256"] = hashlib.sha256(reg_path.read_bytes()).hexdigest()
    iep.write_pack(str(tmp_path), pack)

    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")
    messages = "\n".join(item["message"] for item in audit["findings"])

    assert expected in messages


def test_review_contract_must_match_expression_vs_body_view(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    review = registry["characters"][0]["forms"][0]["reference_group"]["side"]["human_review"]
    review["review_contract"] = "n2d_expression_review_v1"
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    pack = iep.build_pack(str(tmp_path))

    assert "review_contract_invalid_for_view" in pack["rows"][0]["buckets"]["side"]["errors"]


def test_pack_rejects_automated_reviewer_and_incomplete_expression_criteria(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    group["front"]["human_review"]["reviewer"] = "codex-agent"
    group["expressions"][0]["human_review"]["criteria"] = []
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    buckets = iep.build_pack(str(tmp_path))["rows"][0]["buckets"]

    assert "reviewer_appears_automated" in buckets["front"]["errors"]
    assert "criteria_incomplete" in buckets["expression"]["errors"]


def test_consumer_independently_rejects_forged_human_metadata(tmp_path: Path) -> None:
    """Editing pack + registry together must not bypass the stricter producer."""
    registry = _project(tmp_path)
    pack = iep.build_pack(str(tmp_path))
    review = registry["characters"][0]["forms"][0]["reference_group"]["front"]["human_review"]
    review["reviewer"] = "codex-agent"
    review["reviewed_at"] = "2026-07-14T10:00:00"
    review["criteria"] = []
    review.pop("confirmation", None)
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    bucket = pack["rows"][0]["buckets"]["front"]
    bucket["reviewer"] = review["reviewer"]
    bucket["reviewed_at"] = review["reviewed_at"]
    bucket["criteria"] = []
    bucket.pop("confirmation", None)
    current_sha = hashlib.sha256(
        (tmp_path / "出图" / "共享" / "identity_registry.json").read_bytes()
    ).hexdigest()
    pack["identity_registry_sha256"] = current_sha
    _write_json(tmp_path / "生产数据" / "identity_eval_pack.json", pack)

    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")
    messages = "\n".join(row["message"] for row in audit["findings"])
    assert "reviewer_appears_automated" in messages
    assert "reviewed_at_timezone_missing" in messages
    assert "criteria_incomplete" in messages
    assert "explicit_current_pixels_confirmation_missing" in messages


def test_one_form_row_cannot_be_reused_for_another_form(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    second = copy.deepcopy(registry["characters"][0]["forms"][0])
    second["form"] = "战损态"
    # The malicious pack will omit this form entirely; its node contents do not
    # matter because the consumer must require an exact (character, form) row.
    registry["characters"][0]["forms"].append(second)
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)
    pack = iep.build_pack(str(tmp_path))
    pack["rows"] = [row for row in pack["rows"] if row["form"] == "常态"]
    iep.write_pack(str(tmp_path), pack)

    audit = pc.check_multiview_identity_pack(str(tmp_path), "第1集")

    assert any(
        row["verdict"] == "block" and "CHAR_01/战损态" in row["message"]
        for row in audit["findings"]
    )


def test_record_current_view_receipt_is_hash_bound_atomic_and_pack_consumable(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    node["status"] = "review_pending"
    node.pop("human_review")
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    result = iep.record_current_view_receipt(
        str(tmp_path),
        character_id="CHAR_01",
        form="常态",
        view="side",
        reviewer="张三/角色设定终审",
        reviewed_at="2026-07-14T11:30:00+08:00",
        accept_current_pixels=True,
    )

    assert result["ok"] is True
    assert result["previous_node_status"] == "review_pending"
    assert result["node_status"] == "ready"
    saved = json.loads((tmp_path / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8"))
    receipt = saved["characters"][0]["forms"][0]["reference_group"]["side"]["human_review"]
    assert receipt["reviewer"] == "张三/角色设定终审"
    assert receipt["png_sha256"] == hashlib.sha256(
        (tmp_path / receipt["path"]).read_bytes()
    ).hexdigest()
    assert receipt["registry_binding_fingerprint"] == iep.binding_fingerprint(
        character_id="CHAR_01",
        form="常态",
        library_tier="core_full",
        view="side",
        path=receipt["path"],
        png_sha256=receipt["png_sha256"],
    )
    assert receipt["review_contract"] == "n2d_turnaround_view_review_v1"
    assert set(receipt["criteria"]) >= iep.REQUIRED_CRITERIA
    assert receipt["confirmation"] == {
        "kind": "explicit_current_pixels_acceptance",
        "accepted_current_pixels": True,
    }
    bucket = iep.build_pack(str(tmp_path))["rows"][0]["buckets"]["side"]
    assert bucket["status"] == "pass"
    assert bucket["sha256"] == receipt["png_sha256"]


def test_record_authorized_executor_visual_receipt_stays_separate_from_human_signoff(
    tmp_path: Path,
) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    node["status"] = "review_pending"
    node.pop("human_review")
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)
    (tmp_path / "_设置.md").write_text(
        "- 图片验收模式：逐张机器QC+实际目视  # source=explicit_user\n"
        "- 记录：用户明确授权执行者实际像素目视\n",
        encoding="utf-8",
    )

    result = iep.record_current_view_receipt(
        str(tmp_path),
        character_id="CHAR_01",
        form="常态",
        view="side",
        reviewer="Codex视觉执行者",
        review_kind="executor_visual",
        accept_current_pixels=True,
    )

    saved = json.loads(
        (tmp_path / "出图" / "共享" / "identity_registry.json").read_text(encoding="utf-8")
    )
    saved_node = saved["characters"][0]["forms"][0]["reference_group"]["side"]
    assert "human_review" not in saved_node
    assert saved_node["visual_review"]["human_signoff"] is False
    assert saved_node["visual_review"]["reviewer_role"] == "ai_visual_executor"
    assert result["review_kind"] == "executor_visual"
    assert iep.build_pack(str(tmp_path))["rows"][0]["buckets"]["side"]["status"] == "pass"


def test_record_expression_requires_exact_path_and_writes_expression_contract(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    group = registry["characters"][0]["forms"][0]["reference_group"]
    first = group["expressions"][0]
    first.pop("human_review")
    second_rel = "出图/共享/图片/expression_angry.png"
    (tmp_path / second_rel).write_bytes(_png_bytes("expression_angry"))
    group["expressions"].append({"path": second_rel, "status": "ready"})
    reg_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    _write_json(reg_path, registry)
    before = reg_path.read_bytes()

    with pytest.raises(iep.ReceiptError, match="expression 必须用 --view-path"):
        iep.record_current_view_receipt(
            str(tmp_path),
            character_id="CHAR_01",
            form="常态",
            view="expression",
            reviewer="李四",
            accept_current_pixels=True,
        )
    assert reg_path.read_bytes() == before

    result = iep.record_current_view_receipt(
        str(tmp_path),
        character_id="CHAR_01",
        form="常态",
        view="expression",
        view_path=first["path"],
        reviewer="李四",
        accept_current_pixels=True,
    )
    receipt = result["receipt"]
    assert receipt["review_contract"] == "n2d_expression_review_v1"
    assert set(receipt["criteria"]) >= iep.EXPRESSION_REQUIRED_CRITERIA
    assert iep.build_pack(str(tmp_path))["rows"][0]["buckets"]["expression"]["status"] == "pass"


def test_record_requires_explicit_current_pixel_acceptance_and_never_mutates_on_reject(tmp_path: Path) -> None:
    _project(tmp_path)
    reg_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    before = reg_path.read_bytes()

    with pytest.raises(iep.ReceiptError, match="accept-current-pixels"):
        iep.record_current_view_receipt(
            str(tmp_path),
            character_id="CHAR_01",
            form="常态",
            view="front",
            reviewer="王五",
            accept_current_pixels=False,
        )

    assert reg_path.read_bytes() == before


@pytest.mark.parametrize("reviewer", ["bot", "qa-codex", "render_agent", "ci/runner"])
def test_record_rejects_automated_reviewer_identities_without_mutation(
    tmp_path: Path,
    reviewer: str,
) -> None:
    _project(tmp_path)
    reg_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    before = reg_path.read_bytes()

    with pytest.raises(iep.ReceiptError, match="人工声明标识"):
        iep.record_current_view_receipt(
            str(tmp_path),
            character_id="CHAR_01",
            form="常态",
            view="front",
            reviewer=reviewer,
            accept_current_pixels=True,
        )

    assert reg_path.read_bytes() == before


def test_record_never_resurrects_planned_node_even_with_old_receipt_and_png(tmp_path: Path) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    node["status"] = "planned"  # keep its old accepted review deliberately
    reg_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    _write_json(reg_path, registry)
    before = reg_path.read_bytes()

    with pytest.raises(iep.ReceiptError, match="planned"):
        iep.record_current_view_receipt(
            str(tmp_path),
            character_id="CHAR_01",
            form="常态",
            view="side",
            reviewer="赵六",
            accept_current_pixels=True,
        )

    assert reg_path.read_bytes() == before


def test_record_rejects_non_decodable_current_png_and_wrong_view_path(tmp_path: Path) -> None:
    _project(tmp_path)
    reg_path = tmp_path / "出图" / "共享" / "identity_registry.json"
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    side = registry["characters"][0]["forms"][0]["reference_group"]["side"]
    (tmp_path / side["path"]).write_bytes(b"not pixels")
    _write_json(reg_path, registry)
    before = reg_path.read_bytes()

    with pytest.raises(iep.ReceiptError, match="可解码像素证据"):
        iep.record_current_view_receipt(
            str(tmp_path),
            character_id="CHAR_01",
            form="常态",
            view="side",
            reviewer="钱七",
            accept_current_pixels=True,
        )
    assert reg_path.read_bytes() == before

    with pytest.raises(iep.ReceiptError, match="path 不匹配"):
        iep.record_current_view_receipt(
            str(tmp_path),
            character_id="CHAR_01",
            form="常态",
            view="front",
            view_path="出图/共享/图片/back.png",
            reviewer="钱七",
            accept_current_pixels=True,
        )


def test_cli_records_only_the_requested_current_view(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry = _project(tmp_path)
    node = registry["characters"][0]["forms"][0]["reference_group"]["rear_three_quarter"]
    node.pop("human_review")
    _write_json(tmp_path / "出图" / "共享" / "identity_registry.json", registry)

    rc = iep.main([
        str(tmp_path),
        "--record-current-view",
        "--character-id", "CHAR_01",
        "--form", "常态",
        "--view", "rear_three_quarter",
        "--reviewer", "角色设定组/终审A",
        "--accept-current-pixels",
        "--json",
    ])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["view"] == "rear_three_quarter"
    assert payload["pack_consumption"]["bucket_status"] == "pass"
    assert payload["pack_consumption"]["form_verdict"] == "pass"
