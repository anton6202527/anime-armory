from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import model_pack
import registry_v2


def fake_png(path: Path, width: int, height: int, marker: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(model_pack.PNG_SIG + b"\x00\x00\x00\rIHDR" + struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00" + marker * 16)


def registry_fixture(root: Path) -> dict:
    images = root / "出图" / "共享" / "图片"
    source_sha = hashlib.sha256(b"canonical-front-source").hexdigest()
    refs = []
    views = {}
    for index, view in enumerate(("front", "three_quarter", "side", "back", "face")):
        path = images / f"CHAR_A__{view}.png"
        fake_png(path, 512 if view == "face" else 768, 512 if view == "face" else 1024, bytes([65 + index]))
        rel = str(path.relative_to(root))
        views[view] = rel
        refs.append({
            "view": view, "path": rel, "sha256": model_pack.file_sha256(path),
            "source": {"view": view},
            "derivation": {"method": "generated_from_shared_anchor", "source_path": views.get("front", rel), "source_sha256": source_sha, "crop_box": []},
        })
    registry, _ = registry_v2.migrate_registry({
        "schema_version": 2, "kind": "comic_identity_registry",
        "assets": {"CHAR_A": {"id": "CHAR_A", "type": "character", "library_tier": "core_full", "views": views, "reference_images": refs}},
    })
    return registry


def test_core_model_pack_needs_sha_signoff_then_becomes_ready_and_stales(tmp_path: Path) -> None:
    registry = registry_fixture(tmp_path)
    before = model_pack.evaluate_character(tmp_path, registry, "CHAR_A")
    assert before["technical_block"] is False
    assert before["readiness"] == "needs_approval"
    confirmations = {key: True for key in model_pack.REQUIRED_CONFIRMATIONS}
    receipt = model_pack.create_signoff(tmp_path, registry, "CHAR_A", "editor", "并排确认五视图", confirmations)
    assert receipt["model_pack_fingerprint"] == before["model_pack_fingerprint"]
    assert model_pack.evaluate_character(tmp_path, registry, "CHAR_A")["readiness"] == "ready"

    # Any required view change invalidates the receipt automatically.
    face = tmp_path / registry["assets"]["CHAR_A"]["views"]["face"]
    fake_png(face, 512, 512, b"Z")
    stale = model_pack.evaluate_character(tmp_path, registry, "CHAR_A")
    assert stale["signoff"]["status"] == "stale"
    assert stale["readiness"] == "needs_approval"


def test_every_tier_with_required_views_needs_current_sha_signoff(tmp_path: Path) -> None:
    confirmations = {key: True for key in model_pack.REQUIRED_CONFIRMATIONS}
    for tier, required in (
        ("recurring_standard", ["front", "three_quarter", "face"]),
        ("named_minimal", ["front", "face"]),
    ):
        registry = registry_fixture(tmp_path)
        registry["assets"]["CHAR_A"]["library_tier"] = tier
        before = model_pack.evaluate_character(tmp_path, registry, "CHAR_A")
        assert before["required_views"] == required
        assert before["signoff_required"] is True
        assert before["readiness"] == "needs_approval"
        model_pack.create_signoff(tmp_path, registry, "CHAR_A", "editor", f"并排确认 {tier}", confirmations)
        assert model_pack.evaluate_character(tmp_path, registry, "CHAR_A")["readiness"] == "ready"


def test_restricted_partial_still_requires_front_anchor_and_signoff(tmp_path: Path) -> None:
    # 零必需视图曾让 restricted_partial 成为整档免检旁路（自动 ready·免签收）；
    # 最低档也必须有一张正面锚 + 当前 SHA 人审签收。
    registry = registry_fixture(tmp_path)
    registry["assets"]["CHAR_A"]["library_tier"] = "restricted_partial"
    report = model_pack.evaluate_character(tmp_path, registry, "CHAR_A")
    assert report["required_views"] == ["front"]
    assert report["signoff_required"] is True
    assert report["readiness"] == "needs_approval"
    confirmations = {key: True for key in model_pack.REQUIRED_CONFIRMATIONS}
    model_pack.create_signoff(tmp_path, registry, "CHAR_A", "editor", "并排确认受限档正面锚", confirmations)
    assert model_pack.evaluate_character(tmp_path, registry, "CHAR_A")["readiness"] == "ready"


def test_default_selection_enrolls_all_monster_tiers_like_characters() -> None:
    # named_minimal/未标档 monster 曾被默认排除（与 character 不对称），聊斋狐仆零定妆审计。
    assets = {
        "CHAR_A": {"type": "character", "library_tier": "named_minimal"},
        "MON_MINIMAL": {"type": "monster", "library_tier": "named_minimal"},
        "MON_UNTIERED": {"type": "monster"},
        "MON_OPTOUT": {"type": "monster", "model_pack_required": False},
        "LOC_X": {"type": "location"},
    }
    assert model_pack.default_selected_assets(assets) == ["CHAR_A", "MON_MINIMAL", "MON_UNTIERED"]


def test_report_summary_separates_characters_and_monsters() -> None:
    summary = model_pack.summarize_reports([
        {"character_id": "CHAR_A", "asset_type": "character", "readiness": "ready"},
        {"character_id": "MON_A", "asset_type": "monster", "readiness": "needs_fix"},
    ])
    assert summary == {
        "assets": 2,
        "characters": 1,
        "monsters": 1,
        "ready": 1,
        "needs_approval": 0,
        "needs_fix": 1,
    }


def test_1x1_and_duplicate_or_mislabelled_views_cannot_be_ready(tmp_path: Path) -> None:
    registry = registry_fixture(tmp_path)
    front = tmp_path / registry["assets"]["CHAR_A"]["views"]["front"]
    fake_png(front, 1, 1, b"X")
    report = model_pack.evaluate_character(tmp_path, registry, "CHAR_A")
    assert report["readiness"] == "needs_fix"
    assert any(item["code"] == "model_pack_view_degenerate_1x1" for item in report["findings"])

    registry = registry_fixture(tmp_path)
    registry["assets"]["CHAR_A"]["reference_images"][1]["source"]["view"] = "back"
    report = model_pack.evaluate_character(tmp_path, registry, "CHAR_A")
    assert any(item["code"] == "model_pack_source_view_mismatch" for item in report["findings"])

    side = tmp_path / registry["assets"]["CHAR_A"]["views"]["side"]
    back = tmp_path / registry["assets"]["CHAR_A"]["views"]["back"]
    back.write_bytes(side.read_bytes())
    report = model_pack.evaluate_character(tmp_path, registry, "CHAR_A")
    assert any(item["code"] == "model_pack_duplicate_view_content" for item in report["findings"])


def test_repeated_readiness_check_is_idempotent(tmp_path: Path) -> None:
    registry = registry_fixture(tmp_path)
    model_pack.apply_character_readiness(tmp_path, registry, "CHAR_A")
    first = dict(registry["assets"]["CHAR_A"]["model_pack"])
    model_pack.apply_character_readiness(tmp_path, registry, "CHAR_A")
    assert registry["assets"]["CHAR_A"]["model_pack"] == first


def test_shared_report_does_not_churn_when_only_created_at_changes(tmp_path: Path) -> None:
    path = tmp_path / "生产数据" / "comic_model_pack_report.json"
    first = {
        "kind": "comic_model_pack_report",
        "version": 1,
        "created_at": "2026-07-17T10:00:00+00:00",
        "characters": [{"character_id": "CHAR_A", "readiness": "ready"}],
        "summary": {"ready": 1},
    }
    model_pack.write_stable_report(path, first)
    first_bytes = path.read_bytes()
    second = {**first, "created_at": "2026-07-17T11:00:00+00:00"}

    result = model_pack.write_stable_report(path, second)

    assert result["created_at"] == "2026-07-17T10:00:00+00:00"
    assert path.read_bytes() == first_bytes


def test_model_pack_signoff_requires_accountable_identity_and_reason(tmp_path: Path) -> None:
    registry = registry_fixture(tmp_path)
    confirmations = {key: True for key in model_pack.REQUIRED_CONFIRMATIONS}
    model_pack.create_signoff(tmp_path, registry, "CHAR_A", "editor", "并排确认五视图", confirmations)
    path = model_pack.signoff_path(tmp_path, "CHAR_A")
    valid = json.loads(path.read_text(encoding="utf-8"))

    for field in ("reviewer", "approved_at", "reason", "character_id"):
        malformed = dict(valid)
        malformed.pop(field)
        path.write_text(json.dumps(malformed, ensure_ascii=False), encoding="utf-8")
        report = model_pack.evaluate_character(tmp_path, registry, "CHAR_A")
        assert report["signoff"]["status"] == "stale"
        assert report["readiness"] == "needs_approval"


def test_monster_default_managed_all_tiers_with_opt_out(tmp_path: Path) -> None:
    # 2026-07-17 虎妖漏管回归 + 2026-07-23 再修：monster 与 character 同标准全档默认纳管
    # （named_minimal 狐仆曾因档位排除零定妆审计）；model_pack_required=False 仍可显式退出。
    registry = registry_fixture(tmp_path)
    registry["assets"]["MON_TIGER"] = {"id": "MON_TIGER", "type": "monster", "library_tier": "recurring_standard"}
    registry["assets"]["MON_BG"] = {"id": "MON_BG", "type": "monster", "library_tier": "named_minimal"}
    registry["assets"]["MON_OPTOUT"] = {"id": "MON_OPTOUT", "type": "monster", "library_tier": "core_full", "model_pack_required": False}
    registry["assets"]["CHAR_OPTOUT"] = {"id": "CHAR_OPTOUT", "type": "character", "library_tier": "core_full", "model_pack_required": False}
    registry_file = tmp_path / "出图" / "共享" / "identity_registry.json"
    registry_file.parent.mkdir(parents=True, exist_ok=True)
    registry_file.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")

    model_pack.main([str(tmp_path), "check", "--write"])
    payload = json.loads((tmp_path / "生产数据" / "comic_model_pack_report.json").read_text(encoding="utf-8"))
    audited = {row["character_id"] for row in payload["characters"]}
    assert audited == {"CHAR_A", "MON_TIGER", "MON_BG"}
    assert payload["summary"]["monsters"] == 2


def test_build_montage_creates_labelled_contact_sheet(tmp_path: Path) -> None:
    from PIL import Image
    registry = registry_fixture(tmp_path)
    # replace fake headers with real PNGs so the montage actually stitches them
    for rel in registry["assets"]["CHAR_A"]["views"].values():
        Image.new("RGB", (256, 384), (100, 120, 140)).save(tmp_path / rel)
    result = model_pack.build_montage(tmp_path, registry, "CHAR_A")
    assert result["status"] == "ok"
    out = tmp_path / result["path"]
    assert out.is_file()
    stitched = Image.open(out)
    assert stitched.width > 256  # five views stitched horizontally into one sheet
    assert set(result["views"]) == {"front", "three_quarter", "side", "back", "face"}


def test_build_montage_tolerates_unreadable_views(tmp_path: Path) -> None:
    # fixture writes fake PNG headers (not decodable) → placeholder tiles, still ok
    registry = registry_fixture(tmp_path)
    result = model_pack.build_montage(tmp_path, registry, "CHAR_A")
    assert result["status"] == "ok"
    assert (tmp_path / result["path"]).is_file()


def test_check_attaches_montage_for_needs_approval(tmp_path: Path) -> None:
    from PIL import Image
    registry = registry_fixture(tmp_path)
    for rel in registry["assets"]["CHAR_A"]["views"].values():
        Image.new("RGB", (256, 384), (90, 90, 90)).save(tmp_path / rel)
    (tmp_path / "出图" / "共享").mkdir(parents=True, exist_ok=True)
    (tmp_path / "出图" / "共享" / "identity_registry.json").write_text(
        json.dumps(registry, ensure_ascii=False), encoding="utf-8")
    rc = model_pack.main([str(tmp_path), "check", "--characters", "CHAR_A", "--write"])
    assert rc == 1  # needs_approval
    report = json.loads((tmp_path / "生产数据" / "comic_model_pack_report.json").read_text(encoding="utf-8"))
    char = report["characters"][0]
    assert char["montage"]
    assert (tmp_path / char["montage"]).is_file()
